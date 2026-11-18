import pytest

from postlife.gemini import Gemini, GeminiError


class Resp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


def client(responses):
    sent = []

    def post(url, headers=None, json=None, timeout=None):
        sent.append({"url": url, "headers": headers, "json": json})
        return responses.pop(0)

    return Gemini(api_key="test-key", post=post, sleep=lambda s: None), sent


# 2026-11-18에 실제로 받은 응답의 형태
DECISION = {
    "answers": {
        "category": {
            "confidence": 0.88,
            "choice": "상품개정",
            "probabilities": {"상품개정": 0.88, "신담보출시": 0.08, "해당없음": 0.02},
            "type": "choice",
        },
        "is_target": {"confidence": 0.795, "noul": 0.795, "type": "noul"},
    },
    "usage": {"total_output_tokens": 0},
}


def test_decide_reads_noul_as_probability_of_true():
    g, sent = client([Resp(200, DECISION)])
    answers = g.decide("gemini-decision-1", "입력", {"is_target": {"type": "noul"}, "category": {"type": "choice"}})
    assert answers["is_target"].value is True
    assert answers["is_target"].prob(True) == pytest.approx(0.795)
    assert answers["is_target"].prob(False) == pytest.approx(0.205)
    assert answers["category"].value == "상품개정"
    assert answers["category"].prob("해당없음") == pytest.approx(0.02)
    assert sent[0]["url"].endswith("/v1beta/decisions")
    # 키는 주소가 아니라 헤더로만 보낸다
    assert "test-key" not in sent[0]["url"] and sent[0]["headers"]["x-goog-api-key"] == "test-key"


def test_search_attaches_source_numbers():
    body = {
        "candidates": [
            {
                "content": {"parts": [{"text": "가나다."}]},
                "groundingMetadata": {
                    "groundingChunks": [{"web": {"title": "news.kr", "uri": "https://x/1"}}],
                    "groundingSupports": [{"segment": {"endIndex": 10}, "groundingChunkIndices": [0]}],
                    "webSearchQueries": ["질의"],
                },
            }
        ]
    }
    g, sent = client([Resp(200, body)])
    result = g.search("gemini-2.5-flash-lite", "질문")
    assert result.text == "가나다.[1]"
    assert result.sources[0].uri == "https://x/1" and result.sources[0].index == 1
    assert sent[0]["json"]["tools"] == [{"google_search": {}}]


def test_generate_parses_json_when_schema_given():
    g, sent = client([Resp(200, {"candidates": [{"content": {"parts": [{"text": '[{"a": 1}]'}]}}]})])
    assert g.generate("m", "p", schema={"type": "ARRAY"}) == [{"a": 1}]
    assert sent[0]["json"]["generationConfig"]["responseMimeType"] == "application/json"


def test_retries_on_rate_limit_then_gives_up_on_bad_request():
    g, sent = client([Resp(429, {"error": {"message": "한도"}}), Resp(200, {"candidates": []})])
    assert g.generate("m", "p") == ""
    assert g.calls["m"] == 2

    g, sent = client([Resp(400, {"error": {"message": "잘못된 요청"}})])
    with pytest.raises(GeminiError):
        g.generate("m", "p")
    assert len(sent) == 1


def test_missing_key_is_an_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(GeminiError):
        Gemini()
