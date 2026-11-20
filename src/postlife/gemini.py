"""Gemini API 호출. 키는 환경변수 GEMINI_API_KEY에서만 읽는다.

- generate: 추출·분류·해설 (JSON 응답 지정 가능)
- search: 검색 그라운딩. 본문에 출처 번호를 끼워 넣어 돌려준다.
- decide: 판정 전용 모델. 선택지별 확률만 돌려준다. 응답이 알려 준 실제 입력 토큰은 분당 토큰 창과 input_tokens에 쓴다.

400 이상 응답은 GeminiError가 되고, 오류 본문의 상세(한도 종류, 다시 보낼 시각)는 info에 기록만 한다.

모델별 생성 설정(출력 상한, 사고 수준), 대기 시간, 재시도 규칙은 config.py에 두고 여기서 읽는다.
config에 없는 모델은 예전과 같은 요청을 보내고 같은 규칙으로 다시 시도한다.
"""
from __future__ import annotations

import copy
import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from . import config

BASE = "https://generativelanguage.googleapis.com/v1beta"
RETRY_STATUS = {429, 500, 502, 503, 504}
DEFAULT_MAX_OUTPUT_TOKENS = 8192

# usageMetadata의 토큰 수 이름 (API 참조의 UsageMetadata)
_USAGE_NAMES = (
    ("maxOutputTokens", "출력 상한"),
    ("promptTokenCount", "입력"),
    ("thoughtsTokenCount", "사고"),
    ("candidatesTokenCount", "답"),
    ("totalTokenCount", "합계"),
)


# 오류 응답에서 고를 값. 한도 종류와 다시 보낼 시각을 알려 주는 값만 고른다(설명, 링크, 프로젝트 번호가 든 값은 고르지 않는다)
_DETAIL_KEYS = ("reason", "retryDelay")
_VIOLATION_KEYS = ("quotaId", "quotaMetric", "quotaValue")
_MAX_ITEMS = 10            # details, violations, quotaDimensions, metadata에서 담을 항목 수의 상한
_MAX_VALUE = 200           # 값 하나의 글자 수 상한
_INFO_TEXT_MAX = 160       # GeminiError의 글에 붙이는 요약의 글자 수 상한


class GeminiError(RuntimeError):
    """Gemini 호출 오류. status는 HTTP 상태이고, 응답을 받지 못했거나 HTTP 밖의 오류면 0이다.

    info에는 오류 응답 본문의 error.code, error.status, error.details 요약과 Retry-After 머리글을 담는다(_error_info).
    기록하려는 값이다. 다시 시도할지, 얼마나 기다릴지, 하루 한도로 볼지는 info를 보지 않고 정한다.
    글(str)에는 그 요약을 상태 번호 바로 뒤에 짧게 붙이고, 요약이 비면 붙이지 않는다. 글 끝이 아니라 앞에 붙이는 것은
    기록하는 쪽이 글 앞 200자나 300자만 남기기 때문이다(mapping.run, pipeline.run_block, conditions_run, collect,
    Recording). 429 문구는 200자를 넘는 일이 많아 끝에 붙이면 기록에서 잘린다. 요약 안에서는 다시 보낼 시각을 quotaId보다
    앞에 둔다(_info_text).
    """

    def __init__(self, status: int, message: str, info: dict[str, Any] | None = None):
        self.status = status
        self.info: dict[str, Any] = dict(info or {})
        tail = _info_text(self.info, status)
        super().__init__(f"Gemini API {status}" + (f" [{tail}]" if tail else "") + f": {message}")


def _scalar(value: Any) -> Any:
    """글자나 숫자만 받는다(글자는 앞뒤 공백을 떼고 _MAX_VALUE자까지). 참·거짓, 목록, 사전, 빈 글자는 None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip()[:_MAX_VALUE]
        return value or None
    if isinstance(value, (int, float)):
        return value
    return None


def _picked(source: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}
    return {k: v for k in keys if (v := _scalar(source.get(k))) is not None}


def _scalars(source: Any, keep: Callable[[str], bool] = lambda k: True) -> dict[str, Any]:
    """사전에서 이름이 글자이고 값이 글자나 숫자인 항목을 _MAX_ITEMS개까지 고른다."""
    if not isinstance(source, dict):
        return {}
    out = {k: v for k, raw in source.items() if isinstance(k, str) and keep(k) and (v := _scalar(raw)) is not None}
    return dict(list(out.items())[:_MAX_ITEMS])


def _detail(item: Any) -> dict[str, Any]:
    """error.details의 항목 하나. "@type"의 끝 이름(type)과 reason, retryDelay, violations의 quotaId, quotaMetric,
    quotaValue, quotaDimensions, metadata 가운데 이름이 quota로 시작하는 값만 담는다."""
    if not isinstance(item, dict):
        return {}
    out: dict[str, Any] = {}
    kind = _scalar(item.get("@type"))
    if isinstance(kind, str):
        out["type"] = kind.replace("/", ".").rsplit(".", 1)[-1]   # "type.googleapis.com/google.rpc.QuotaFailure" → QuotaFailure
    out.update(_picked(item, _DETAIL_KEYS))
    metadata = _scalars(item.get("metadata"), lambda k: k.startswith("quota"))   # consumer(프로젝트 번호) 등은 뺀다
    if metadata:
        out["metadata"] = metadata
    violations = []
    raw = item.get("violations")
    for v in raw if isinstance(raw, list) else []:
        picked = _picked(v, _VIOLATION_KEYS)
        dimensions = _scalars(v.get("quotaDimensions")) if isinstance(v, dict) else {}
        if dimensions:
            picked["quotaDimensions"] = dimensions
        if picked:
            violations.append(picked)
    if violations:
        out["violations"] = violations[:_MAX_ITEMS]
    return out


def _header(resp: Any, name: str) -> Any:
    """응답 머리글 하나. requests의 머리글은 대소문자를 가리지 않고, 보통 사전이면 이름 그대로와 소문자로 찾는다."""
    headers = getattr(resp, "headers", None)
    if headers is None:
        return None
    try:
        value = headers.get(name)
        return headers.get(name.lower()) if value is None else value
    except Exception:            # 머리글이 사전 꼴이 아닌 가짜 응답
        return None


def _error_info(payload: Any, resp: Any) -> dict[str, Any]:
    """오류 응답(payload는 본문을 JSON으로 읽은 값, 읽지 못했으면 None)에서 한도 종류와 다시 보낼 시각을 알려 주는 값만 고른다.

    code, status: error.code, error.status. details: 항목마다 _detail. retry_after: Retry-After 머리글.
    본문이 JSON이 아니거나 꼴이 달라도 예외를 내지 않고, 고를 값이 없으면 빈 사전이다. 고른 값만 담으므로 API 키와 요청 본문은
    들어가지 않는다.
    근거: 판정 API와 generateContent의 429 본문 꼴(다시 보낼 시각 필드, 한도 종류 표시)은 공식 문서에 없다. Interactions API
    오류 문서에 error.code가 "rate_limit_exceeded"(분당), "quota_exceeded"(하루)로 갈린다는 것만 있고, details의
    QuotaFailure(quotaId)와 RetryInfo(retryDelay)는 게시판 글의 사례다. 그래서 동작에는 쓰지 않고 기록만 한다.
    """
    info: dict[str, Any] = {}
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        info.update(_picked(error, ("code", "status")))
        details = error.get("details")
        picked = [d for d in (_detail(x) for x in details[:_MAX_ITEMS]) if d] if isinstance(details, list) else []
        if picked:
            info["details"] = picked
    retry_after = _scalar(_header(resp, "Retry-After"))
    if retry_after is not None:
        info["retry_after"] = retry_after
    return info


def _info_text(info: dict[str, Any], status: int) -> str:
    """info를 "status=RESOURCE_EXHAUSTED, retryDelay=23s, Retry-After=23, reason=…, quotaId=…" 꼴로 줄인다.
    code는 HTTP 상태와 다를 때만 적는다.

    같은 값은 한 번만 적고, _INFO_TEXT_MAX자를 넘으면 뒤를 자른다. 다시 보낼 시각(retryDelay, Retry-After)은 짧은 값이라
    앞에 두고, 이름이 50자 안팎이고 위반 항목 수만큼 늘어나는 quotaId는 맨 뒤에 둔다. 그래야 한도 항목이 여럿인 429에서도
    잘리는 것은 뒤쪽 quotaId뿐이고 다시 보낼 시각은 글에 남는다.
    """
    parts: list[str] = []

    def add(name: str, value: Any) -> None:
        if value is not None and value != "" and f"{name}={value}" not in parts:
            parts.append(f"{name}={value}")

    if "code" in info and str(info["code"]) != str(status):
        add("code", info["code"])
    add("status", info.get("status"))
    details = [d for d in info.get("details") or [] if isinstance(d, dict)]
    for d in details:
        add("retryDelay", d.get("retryDelay"))
    add("Retry-After", info.get("retry_after"))
    for d in details:
        add("reason", d.get("reason"))
    for d in details:
        for v in d.get("violations") or []:
            if isinstance(v, dict):
                add("quotaId", v.get("quotaId"))
    text = ", ".join(parts)
    return text if len(text) <= _INFO_TEXT_MAX else text[:_INFO_TEXT_MAX - 1] + "…"


def input_tokens_report(seen: dict[str, dict[str, int]] | None) -> dict[str, dict[str, Any]]:
    """Gemini.input_tokens를 결과에 남길 꼴로 바꾼다. 모델마다 글자당 토큰 비율(입력 토큰 합 / 본문 글자 수 합,
    tokens_per_char)을 더한다. 글자 수 합이 0이면 비율은 None이다."""
    out: dict[str, dict[str, Any]] = {}
    for model, s in (seen or {}).items():
        chars = s.get("chars") or 0
        out[model] = {**s, "tokens_per_char": round((s.get("tokens") or 0) / chars, 4) if chars else None}
    return out


def usage_text(usage: dict, max_output_tokens: int | None = None) -> str:
    """토큰 사용량을 "출력 상한 32,768, 입력 1,200, 사고 30,000, 답 2,768" 꼴로 적는다."""
    values = {"maxOutputTokens": max_output_tokens, **(usage or {})}
    parts = [f"{name} {int(values[key]):,}" for key, name in _USAGE_NAMES if values.get(key) is not None]
    return ", ".join(parts) if parts else "토큰 사용량 없음"


class GeminiTruncated(GeminiError):
    """응답이 토큰 상한에 걸려 끝났다(finishReason이 MAX_TOKENS 등).

    JSON 파싱 실패와 구별되는 오류다. 같은 설정으로 다시 불러도 또 잘리므로 여기서 다시 부르지 않는다.
    GeminiError의 하위 종류라 GeminiError를 잡아 다음 단계로 넘기는 쪽은 그대로 동작한다. 상태는 0이다
    (pipeline.run_block은 상태가 429일 때만 상위 모델의 하루 한도가 찼다고 본다).
    """

    def __init__(self, finish_reason: str, usage: dict, max_output_tokens: int | None):
        self.finish_reason = finish_reason
        self.usage = dict(usage or {})
        self.max_output_tokens = max_output_tokens
        super().__init__(0, f"응답이 토큰 상한에서 잘림 (finishReason {finish_reason}, "
                            f"{usage_text(self.usage, max_output_tokens)})")


@dataclass
class Source:
    index: int
    title: str
    uri: str


@dataclass
class SearchResult:
    text: str                      # 출처 번호([1], [2])를 끼워 넣은 본문
    sources: list[Source] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)


@dataclass
class Answer:
    value: Any                     # noul이면 bool, choice면 선택지, score면 숫자
    confidence: float | None
    probabilities: dict[str, float] = field(default_factory=dict)

    def prob(self, option: Any) -> float:
        """선택지 하나의 확률. noul은 True/False, choice는 선택지 이름으로 묻는다.

        선택지가 여러 개인 문항에서 목록에 없는 선택지는 0으로 본다.
        "1 - 확신도"는 참·거짓 문항에서만 성립하므로 그때만 쓴다.
        """
        key = str(option).lower() if isinstance(option, bool) else str(option)
        for k, v in self.probabilities.items():
            if str(k).lower() == key.lower():
                return float(v)
        if self.probabilities:
            return 0.0
        if self.confidence is None:
            return 0.0
        if self.value == option:
            return float(self.confidence)
        return 1.0 - float(self.confidence) if isinstance(option, bool) else 0.0


def annotate(text: str, supports: list[dict]) -> str:
    """그라운딩 근거 구간 끝에 출처 번호를 끼워 넣는다. 구간 위치는 UTF-8 바이트 기준이다."""
    raw = text.encode("utf-8")
    marks: list[tuple[int, str]] = []
    for s in supports:
        end = (s.get("segment") or {}).get("endIndex")
        idx = s.get("groundingChunkIndices") or []
        if end is None or not idx:
            continue
        marks.append((min(int(end), len(raw)), "".join(f"[{i + 1}]" for i in idx)))
    for end, mark in sorted(marks, reverse=True):
        raw = raw[:end] + mark.encode("utf-8") + raw[end:]
    return raw.decode("utf-8", errors="ignore")


class Gemini:
    def __init__(
        self,
        api_key: str | None = None,
        post: Callable[..., Any] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = 2,
        min_interval: dict[str, float] | None = None,
        clock: Callable[[], float] = time.monotonic,
        timeout: dict[str, float] | None = None,
        retry_wait: dict[str, float | tuple[float, ...]] | None = None,
        generation: dict[str, dict[str, Any]] | None = None,
        timeout_retries: dict[str, int] | None = None,
        retry_status: dict[str, tuple[int, ...]] | None = None,
        tokens_per_minute: dict[str, int] | None = None,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise GeminiError(0, "GEMINI_API_KEY가 없습니다")
        if post is None:
            import requests

            post = requests.post
        self._post = post
        self._sleep = sleep
        self.max_retries = max_retries
        self.calls: dict[str, int] = {}     # 모델별 HTTP 요청 수. 다시 시도한 것도 하나씩 센다
        # 모델별 최소 호출 간격(초). 분당 한도를 넘지 않게 호출 사이를 띄운다.
        self.min_interval = dict(min_interval or {})
        # 아래 모델별 설정은 config 값을 깔고, 넘겨받은 값이 모델마다 덮어쓴다.
        # 부르는 쪽이 config 값을 넘기지 않아도(Gemini()만 만들어도) 상위 모델 규칙이 같게 적용된다.
        self.timeout = {**config.TIMEOUT, **(timeout or {})}              # 응답 대기 시간(초). 없으면 90초
        self.retry_wait = {**config.RETRY_WAIT, **(retry_wait or {})}     # 재시도 대기. 없으면 8초씩 늘려 기다린다
        self.generation = {**config.GENERATION, **(generation or {})}     # generationConfig에 덮어쓸 값
        self.timeout_retries = {**config.TIMEOUT_RETRIES, **(timeout_retries or {})}  # 응답 없을 때 되풀이. 없으면 1
        self.retry_status = {**config.RETRY_STATUS, **(retry_status or {})}  # 다시 시도할 상태. 없으면 RETRY_STATUS
        self.last_meta: dict[str, Any] = {}  # 마지막 generate 응답의 finishReason과 토큰 사용량
        # 분당 토큰 한도가 빠듯한 모델: 최근 60초 동안 보낸 입력 토큰이 이 값을 넘지 않게 기다린다.
        # 보내기 전에는 글자 수로 어림하고, 판정 응답이 실제 입력 토큰을 알려 주면 그 값으로 바꾼다
        self.tokens_per_minute = {**config.TOKENS_PER_MINUTE, **(tokens_per_minute or {})}
        self._sent: dict[str, deque] = {}           # 모델별 (보낸 시각, 토큰 수: 어림한 값이나 응답이 알려 준 값)
        self.token_waits: dict[str, float] = {}     # 모델별로 분당 토큰 한도 때문에 기다린 시간(초)의 합
        # 모델별로 판정 응답이 알려 준 실제 입력 토큰. {"calls": 입력 토큰 수를 읽은 응답 수, "chars": 그 요청 본문의
        # 글자 수 합, "tokens": 입력 토큰 합}. 다시 시도한 실패 시도는 세지 않는다(calls와 다르다)
        self.input_tokens: dict[str, dict[str, int]] = {}
        self._clock = clock
        self._last: dict[str, float] = {}

    def _pace(self, model: str, body: dict | None = None) -> bool:
        """호출 간격과 분당 토큰 한도를 지키게 기다린다. 분당 토큰 창에 이번 요청을 적었으면 참을 돌려준다."""
        gap = self.min_interval.get(model)
        if gap and model in self._last:
            wait = gap - (self._clock() - self._last[model])
            if wait > 0:
                self._sleep(wait)
        recorded = self._hold_for_tokens(model, body)
        self._last[model] = self._clock()
        return recorded

    @staticmethod
    def _body_chars(body: dict) -> int:
        """요청 본문의 글자 수. 분당 토큰 창의 어림과 글자당 토큰 비율은 모두 이 글자 수로 센다."""
        return len(json.dumps(body, ensure_ascii=False))

    def _tokens_per_char(self, model: str) -> float:
        """다음 요청의 토큰 수를 어림할 글자당 토큰 비율.

        판정 응답의 실제 입력 토큰을 본 모델은 지금까지 모은 비율(입력 토큰 합 / 본문 글자 수 합)을 쓴다. 1보다 크든 작든
        그대로 따른다(서버가 세는 값이다). 아직 본 응답이 없으면 config.TOKENS_PER_CHAR. 공식 문서에는 영어 기준 토큰 하나가
        약 4글자라는 것만 있고 한국어 비율은 없어, 실제 응답으로만 알 수 있다.
        """
        seen = self.input_tokens.get(model)
        if seen and seen["chars"] > 0 and seen["tokens"] > 0:
            return seen["tokens"] / seen["chars"]
        return config.TOKENS_PER_CHAR

    def _hold_for_tokens(self, model: str, body: dict | None) -> bool:
        """분당 토큰 한도가 정해진 모델이면, 최근 60초 동안 보낸 토큰에 이번 요청을 더해 한도를 넘을 때 넘지 않게 될 때까지 기다린다.

        토큰 수는 미리 알 수 없어 요청 본문의 글자 수에 글자당 토큰 비율(_tokens_per_char)을 곱해 어림하고, 한도보다 크면 한도로
        자른다. 판정 응답이 실제 입력 토큰을 알려 주면 decide가 창에 적은 이 어림값을 실제 값으로 바꾼다(_note_input_tokens).
        호출 간격만 맞추면 호출 수는 한도에 한참 못 미쳐도 긴 요청이 이어질 때 분당 토큰이 먼저 찬다(2026-11-19 판정 모델:
        분당 14회에 79.98K 토큰, 한도 5만). 공식 문서는 분당 토큰 한도가 입력 토큰을 센다고만 하고, 60초 창이 움직이는 창인지
        고정 구간인지는 적지 않았다. 여기서는 움직이는 창으로 본다.
        기다린 뒤에는 그만큼 시간이 지난 것으로 보고 다시 재지 않는다(기다리기를 흉내만 내는 시험에서도 끝나게).
        여기서 적는 시각은 보내기 직전 시각이고, 요청이 끝나면 _finish_tokens가 끝난 시각으로 늦춘다.
        창에 이번 요청을 적었으면 참을 돌려준다.
        """
        limit = self.tokens_per_minute.get(model)
        if not limit or body is None:
            return False
        need = min(limit, int(self._body_chars(body) * self._tokens_per_char(model)))
        sent = self._sent.setdefault(model, deque())
        now = self._clock()
        while sent and now - sent[0][0] >= 60:
            sent.popleft()
        used = sum(n for _, n in sent)
        wait = 0.0
        while sent and used + need > limit:      # 가장 오래된 요청부터 창에서 빠질 때까지 기다린다
            at, n = sent.popleft()
            used -= n
            wait = max(wait, 60 - (now - at))
        if wait > 0:
            self._sleep(wait)
            self.token_waits[model] = self.token_waits.get(model, 0.0) + wait
        sent.append((now + wait, need))
        return True

    def _finish_tokens(self, model: str) -> None:
        """방금 끝난 요청의 분당 토큰 창 시각을 끝난 시각으로 늦춘다(성공이든 실패든 HTTP 시도가 끝난 뒤).

        보낸 시각부터 60초를 재면, 연결과 응답 대기로 서버가 늦게 센 요청이 우리 창에서 먼저 빠져 서버의 60초 창에는 한도보다
        많이 들어갈 수 있다. 시계가 멈춘 시험에서는 적어 둔 시각(재던 시각에 기다린 시간을 더한 값)이 그대로 남는다.
        """
        sent = self._sent.get(model)
        if sent:
            at, n = sent[-1]
            sent[-1] = (max(at, self._clock()), n)

    def _note_input_tokens(self, model: str, body: dict, out: Any) -> None:
        """판정 응답의 usage.total_input_tokens를 읽어 모으고, 분당 토큰 창에 적은 방금 그 요청의 어림값을 실제 값으로 바꾼다.

        근거: 공식 문서(decisions-api)의 판정 응답에는 최상위 usage 객체가 있고 total_input_tokens가 입력 토큰 수다(출력 토큰은
        늘 0이다). 분당 토큰 한도는 입력 토큰을 센다(rate-limits). 값이 양의 정수가 아니거나 usage 꼴이 다르면 아무것도 하지 않는다.
        창의 값은 한도보다 크면 한도로 자른다(어림값과 같다). 호출은 차례로 하나씩 일어난다고 보고(_finish_tokens와 같은 가정)
        창의 마지막 항목을 방금 답을 준 시도로 본다. 다시 시도한 실패 시도의 어림값은 그대로 둔다.
        """
        usage = out.get("usage") if isinstance(out, dict) else None
        tokens = usage.get("total_input_tokens") if isinstance(usage, dict) else None
        if not isinstance(tokens, int) or isinstance(tokens, bool) or tokens <= 0:
            return
        seen = self.input_tokens.setdefault(model, {"calls": 0, "chars": 0, "tokens": 0})
        seen["calls"] += 1
        seen["chars"] += self._body_chars(body)
        seen["tokens"] += tokens
        limit = self.tokens_per_minute.get(model)
        sent = self._sent.get(model)
        if limit and sent:
            at, _ = sent[-1]
            sent[-1] = (at, min(limit, tokens))

    def _waits(self, model: str) -> list[float]:
        """다시 시도하기 전에 기다릴 시간(초) 목록. 목록 길이가 다시 시도하는 횟수다."""
        wait = self.retry_wait.get(model)
        if isinstance(wait, (list, tuple)):          # 간격을 직접 정한 모델
            return [float(w) for w in wait]
        base = 8.0 if wait is None else float(wait)
        return [base * (i + 1) for i in range(self.max_retries)]

    def _call(self, url: str, body: dict, model: str) -> dict:
        waits = self._waits(model)
        retry_status = set(self.retry_status.get(model, RETRY_STATUS))
        timeout_retries = self.timeout_retries.get(model, 1)
        timeout = self.timeout.get(model, 90)
        attempt = 0
        while True:
            recorded = self._pace(model, body)
            self.calls[model] = self.calls.get(model, 0) + 1
            try:
                resp = self._post(
                    url,
                    headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                    json=body,
                    timeout=timeout,
                )
            except (TimeoutError, ConnectionError, OSError) as e:   # requests의 시간 초과·연결 오류는 OSError의 하위 종류
                # 응답이 끊기거나 오래 걸렸다. 첫 시도부터 정해진 횟수(config.TIMEOUT_RETRIES, 없으면 1)까지만
                # 곧바로 다시 해 보고 넘긴다. 호출한 쪽이 다른 모델로 바꿔 시도한다.
                # 상위 모델은 서버가 끝까지 처리해 한도를 쓰는 것으로 보여 다시 하지 않는다.
                err = GeminiError(0, f"응답 없음: {type(e).__name__} (대기 상한 {timeout:g}초)")
                if attempt >= timeout_retries or attempt >= len(waits):
                    raise err from None
                attempt += 1
                continue
            finally:
                if recorded:            # 분당 토큰 창은 요청이 끝난 시각부터 잰다
                    self._finish_tokens(model)
            if resp.status_code < 400:
                return resp.json()
            err = self._http_error(resp)
            if resp.status_code not in retry_status or attempt >= len(waits):
                raise err
            self._sleep(waits[attempt])
            attempt += 1

    @staticmethod
    def _http_error(resp: Any) -> GeminiError:
        """400 이상 응답을 GeminiError로 바꾼다. 글에는 error.message 앞 400자를 넣고, 본문이 JSON이 아니거나 꼴이 다르면
        본문 글(resp.text)로 떨어진다. message가 글이 아니어도(None 등) 본문 글로 떨어진다. 오류 상세는 info에 담는다(_error_info)."""
        try:
            payload = resp.json()
        except Exception:
            payload = None
        try:
            message = payload.get("error", {}).get("message", "")
        except Exception:
            message = resp.text
        if not isinstance(message, str):
            message = resp.text
        return GeminiError(resp.status_code, message[:400], _error_info(payload, resp))

    @staticmethod
    def _meta(body: dict) -> dict[str, Any]:
        candidates = body.get("candidates") or [{}]
        return {"finishReason": candidates[0].get("finishReason") or "",
                "usage": dict(body.get("usageMetadata") or {})}

    @staticmethod
    def _text(body: dict) -> str:
        candidates = body.get("candidates") or []
        if not candidates:
            return ""
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts)

    def generate(
        self,
        model: str,
        prompt: str,
        schema: dict | None = None,
        temperature: float = 0.0,
        max_output_tokens: int | None = None,
    ) -> Any:
        """schema를 주면 JSON으로 받아 파싱해 돌려준다.

        모델별 생성 설정(config.GENERATION)이 있으면 그 값으로 generationConfig를 덮어쓴다(None이면 그 항목을 뺀다).
        없는 모델은 예전 요청 그대로다(temperature, maxOutputTokens 8192). max_output_tokens를 주면 그 값이 앞선다.
        응답이 토큰 상한에 걸려 끝났으면 JSON을 읽어 보기 전에 GeminiTruncated를 올린다.
        """
        gen: dict[str, Any] = {"temperature": temperature, "maxOutputTokens": DEFAULT_MAX_OUTPUT_TOKENS}
        for key, value in (self.generation.get(model) or {}).items():
            if value is None:
                gen.pop(key, None)
            else:
                gen[key] = copy.deepcopy(value)
        if max_output_tokens is not None:
            gen["maxOutputTokens"] = max_output_tokens
        if schema is not None:
            gen["responseMimeType"] = "application/json"
            gen["responseSchema"] = schema
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gen}
        self.last_meta = {}
        out = self._call(f"{BASE}/models/{model}:generateContent", body, model)
        self.last_meta = meta = self._meta(out)
        finish = meta["finishReason"]
        if finish in config.TRUNCATED_FINISH:
            raise GeminiTruncated(finish, meta["usage"], gen.get("maxOutputTokens"))
        text = self._text(out)
        if schema is None:
            return text
        try:
            return json.loads(text)
        except ValueError as e:   # 끊긴 JSON, 끝없이 이어진 숫자 등
            why = f" (finishReason {finish})" if finish and finish != "STOP" else ""
            raise GeminiError(0, f"JSON으로 읽을 수 없는 응답{why}: {str(e)[:120]}") from None

    def search(self, model: str, prompt: str) -> SearchResult:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.0},
        }
        out = self._call(f"{BASE}/models/{model}:generateContent", body, model)
        candidates = out.get("candidates") or [{}]
        meta = candidates[0].get("groundingMetadata") or {}
        sources = [
            Source(i + 1, (c.get("web") or {}).get("title", ""), (c.get("web") or {}).get("uri", ""))
            for i, c in enumerate(meta.get("groundingChunks") or [])
        ]
        text = annotate(self._text(out), meta.get("groundingSupports") or [])
        return SearchResult(text=text, sources=sources, queries=meta.get("webSearchQueries") or [])

    def decide(self, model: str, input_text: str, questions: dict[str, dict]) -> dict[str, Answer]:
        """questions: {문항키: {"type": "noul"|"choice"|"score", "instructions": ..., "criteria": {...}}}

        응답의 usage.total_input_tokens가 양의 정수면 input_tokens에 모으고, 분당 토큰 창의 어림값을 그 값으로 바꾼다
        (_note_input_tokens). 없거나 꼴이 다르면 예전처럼 어림값을 그대로 둔다.
        """
        body = {"model": model, "input": input_text, "questions": questions}
        out = self._call(f"{BASE}/decisions", body, model)
        self._note_input_tokens(model, body, out)
        answers: dict[str, Answer] = {}
        for key, a in (out.get("answers") or {}).items():
            kind = a.get("type") or questions.get(key, {}).get("type")
            value = a.get(kind)
            probabilities = dict(a.get("probabilities") or {})
            if kind == "noul" and isinstance(value, (int, float)) and not isinstance(value, bool):
                # 참·거짓 문항은 참일 확률을 숫자로 돌려준다
                probabilities = {"true": float(value), "false": 1.0 - float(value)}
                value = value >= 0.5
            answers[key] = Answer(value=value, confidence=a.get("confidence"), probabilities=probabilities)
        return answers
