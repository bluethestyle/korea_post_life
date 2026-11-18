"""Gemini API 호출. 키는 환경변수 GEMINI_API_KEY에서만 읽는다.

- generate: 추출·분류·해설 (JSON 응답 지정 가능)
- search: 검색 그라운딩. 본문에 출처 번호를 끼워 넣어 돌려준다.
- decide: 판정 전용 모델. 선택지별 확률만 돌려준다.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

BASE = "https://generativelanguage.googleapis.com/v1beta"
RETRY_STATUS = {429, 500, 502, 503, 504}


class GeminiError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"Gemini API {status}: {message}")
        self.status = status


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
        """선택지 하나의 확률. noul은 True/False, choice는 선택지 이름으로 묻는다."""
        key = str(option).lower() if isinstance(option, bool) else str(option)
        for k, v in self.probabilities.items():
            if str(k).lower() == key.lower():
                return float(v)
        if self.confidence is not None:
            return float(self.confidence) if self.value == option else 1.0 - float(self.confidence)
        return 0.0


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
        self.calls: dict[str, int] = {}

    def _call(self, url: str, body: dict, model: str) -> dict:
        last: GeminiError | None = None
        for attempt in range(self.max_retries + 1):
            self.calls[model] = self.calls.get(model, 0) + 1
            resp = self._post(
                url,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=body,
                timeout=120,
            )
            if resp.status_code < 400:
                return resp.json()
            try:
                message = resp.json().get("error", {}).get("message", "")
            except Exception:
                message = resp.text
            last = GeminiError(resp.status_code, message[:400])
            if resp.status_code not in RETRY_STATUS or attempt == self.max_retries:
                break
            self._sleep(8 * (attempt + 1))
        assert last is not None
        raise last

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
    ) -> Any:
        """schema를 주면 JSON으로 받아 파싱해 돌려준다."""
        config: dict[str, Any] = {"temperature": temperature}
        if schema is not None:
            config["responseMimeType"] = "application/json"
            config["responseSchema"] = schema
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config}
        out = self._call(f"{BASE}/models/{model}:generateContent", body, model)
        text = self._text(out)
        if schema is None:
            return text
        return json.loads(text)

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
