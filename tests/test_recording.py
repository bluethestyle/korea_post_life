"""모델 응답 남기기(postlife.recording): 지시문은 남기지 않고 응답만 차례로 남긴다."""
import json

import pytest

from postlife.gemini import Answer
from postlife.recording import Recording


class Fake:
    def __init__(self):
        self.calls = {"m": 3}
        self.last_meta = {"finishReason": "STOP", "usage": {"promptTokenCount": 10}}

    def generate(self, model, prompt, schema=None, temperature=0.0):
        if "실패" in prompt:
            raise RuntimeError("호출 실패")
        return {"benefits": [{"name": "가나보험금"}]}

    def decide(self, model, input_text, questions):
        return {k: Answer(value=True, confidence=0.9, probabilities={"true": 0.9, "false": 0.1}) for k in questions}


def test_responses_are_recorded_in_order_without_the_prompt_text(tmp_path):
    g = Recording(Fake())
    assert g.generate("m", "원문 글자가 든 긴 지시문", schema={}) == {"benefits": [{"name": "가나보험금"}]}
    answers = g.decide("d", "특약 본문", {"q2": {}, "q1": {}})
    assert answers["q1"].value is True
    with pytest.raises(RuntimeError):
        g.generate("m", "실패하는 지시문")
    assert g.calls == {"m": 3}                                   # 감싼 객체의 속성은 그대로 보인다

    kinds = [(r["kind"], r["model"]) for r in g.records]
    assert kinds == [("generate", "m"), ("decide", "d"), ("generate", "m")]
    first, second, third = g.records
    assert first["response"] == {"benefits": [{"name": "가나보험금"}]} and first["prompt_chars"] == len("원문 글자가 든 긴 지시문")
    assert first["meta"]["finishReason"] == "STOP"
    assert second["questions"] == ["q1", "q2"] and second["answers"]["q1"]["probabilities"] == {"true": 0.9, "false": 0.1}
    assert "error" in third and "response" not in third

    path = tmp_path / "out" / "model_outputs.jsonl"
    assert g.dump(path) == 3
    text = path.read_text(encoding="utf-8")
    assert "원문 글자가 든 긴 지시문" not in text and "특약 본문" not in text and "실패하는 지시문" not in text
    assert [json.loads(l)["kind"] for l in text.splitlines()] == ["generate", "decide", "generate"]
