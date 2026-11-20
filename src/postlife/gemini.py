"""Gemini API 호출. 키는 환경변수 GEMINI_API_KEY에서만 읽는다.

- generate: 추출·분류·해설 (JSON 응답 지정 가능)
- search: 검색 그라운딩. 본문에 출처 번호를 끼워 넣어 돌려준다.
- decide: 판정 전용 모델. 선택지별 확률만 돌려준다.

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


class GeminiError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"Gemini API {status}: {message}")
        self.status = status


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
        # 분당 토큰 한도가 빠듯한 모델: 최근 60초 동안 보낸 입력 토큰(글자 수로 어림)이 이 값을 넘지 않게 기다린다
        self.tokens_per_minute = {**config.TOKENS_PER_MINUTE, **(tokens_per_minute or {})}
        self._sent: dict[str, deque] = {}           # 모델별 (보낸 시각, 어림한 토큰 수)
        self.token_waits: dict[str, float] = {}     # 모델별로 분당 토큰 한도 때문에 기다린 시간(초)의 합
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

    def _hold_for_tokens(self, model: str, body: dict | None) -> bool:
        """분당 토큰 한도가 정해진 모델이면, 최근 60초 동안 보낸 토큰에 이번 요청을 더해 한도를 넘을 때 넘지 않게 될 때까지 기다린다.

        토큰 수는 미리 알 수 없어 요청 본문의 글자 수로 어림한다(config.TOKENS_PER_CHAR). 호출 간격만 맞추면 호출 수는 한도에
        한참 못 미쳐도 긴 요청이 이어질 때 분당 토큰이 먼저 찬다(2026-11-19 판정 모델: 분당 14회에 79.98K 토큰, 한도 5만).
        기다린 뒤에는 그만큼 시간이 지난 것으로 보고 다시 재지 않는다(기다리기를 흉내만 내는 시험에서도 끝나게).
        여기서 적는 시각은 보내기 직전 시각이고, 요청이 끝나면 _finish_tokens가 끝난 시각으로 늦춘다.
        창에 이번 요청을 적었으면 참을 돌려준다.
        """
        limit = self.tokens_per_minute.get(model)
        if not limit or body is None:
            return False
        need = min(limit, int(len(json.dumps(body, ensure_ascii=False)) * config.TOKENS_PER_CHAR))
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
            try:
                message = resp.json().get("error", {}).get("message", "")
            except Exception:
                message = resp.text
            err = GeminiError(resp.status_code, message[:400])
            if resp.status_code not in retry_status or attempt >= len(waits):
                raise err
            self._sleep(waits[attempt])
            attempt += 1

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
        """questions: {문항키: {"type": "noul"|"choice"|"score", "instructions": ..., "criteria": {...}}}"""
        body = {"model": model, "input": input_text, "questions": questions}
        out = self._call(f"{BASE}/decisions", body, model)
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
