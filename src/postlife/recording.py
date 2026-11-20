"""모델 응답을 실행 결과물에 남긴다.

추출 코드를 고친 뒤 모델을 다시 부르지 않고 같은 응답으로 돌려 보려는 것이다(하루 한도가 있어 다시 부르기 어렵다).
지시문에는 공시 문서의 원문 글자가 들어 있으므로 남기지 않고, 어느 호출인지 맞춰 볼 해시와 길이만 남긴다.
응답은 모델이 옮겨 적은 값(급부 이름, 금액 글자 등)과 판정 확률이다.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class Recording:
    """Gemini 객체를 감싸 generate와 decide의 응답을 차례로 모은다. 그 밖의 속성(calls 등)은 감싼 객체의 것을 그대로 보여 준다."""

    def __init__(self, inner: Any):
        self._inner = inner
        self.records: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def generate(self, model: str, prompt: str, schema: dict | None = None, *args: Any, **kwargs: Any) -> Any:
        entry: dict[str, Any] = {"kind": "generate", "model": model, "prompt_sha": _sha(prompt), "prompt_chars": len(prompt)}
        self.records.append(entry)
        try:
            out = self._inner.generate(model, prompt, schema, *args, **kwargs)
        except Exception as e:
            entry["error"] = f"{type(e).__name__}: {str(e)[:300]}"
            raise
        entry["response"] = out
        meta = getattr(self._inner, "last_meta", None)
        if meta:
            entry["meta"] = dict(meta)
        return out

    def decide(self, model: str, input_text: str, questions: dict[str, dict]) -> Any:
        entry: dict[str, Any] = {"kind": "decide", "model": model, "input_sha": _sha(input_text),
                                 "input_chars": len(input_text), "questions": sorted(questions)}
        self.records.append(entry)
        try:
            answers = self._inner.decide(model, input_text, questions)
        except Exception as e:
            entry["error"] = f"{type(e).__name__}: {str(e)[:300]}"
            raise
        entry["answers"] = {key: {"value": getattr(a, "value", None), "confidence": getattr(a, "confidence", None),
                                  "probabilities": dict(getattr(a, "probabilities", None) or {})}
                            for key, a in answers.items()}
        return answers

    def dump(self, path: Path) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for r in self.records:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        return len(self.records)
