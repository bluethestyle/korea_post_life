import json

import pytest
import requests

from postlife import config
from postlife.gemini import Gemini, GeminiError, GeminiTruncated, usage_text


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


def test_missing_choice_is_zero_not_one_minus_confidence():
    from postlife.gemini import Answer

    # 선택지가 50개인 문항에서 1위 확신도가 낮다고 "해당없음"이 0.92가 되면 안 된다
    listed = Answer("일반암 진단비", 0.08, {"일반암 진단비": 0.08, "소액암 진단비": 0.07})
    assert listed.prob("해당없음") == 0.0
    only_confidence = Answer("일반암 진단비", 0.08, {})
    assert only_confidence.prob("해당없음") == 0.0
    assert only_confidence.prob("일반암 진단비") == 0.08
    # 참·거짓 문항에서는 1 - 확신도가 성립한다
    assert Answer(True, 0.9, {}).prob(False) == pytest.approx(0.1)


def test_calls_are_spaced_to_respect_rate_limits():
    now = [0.0]
    waits = []

    def sleep(seconds):
        waits.append(round(seconds, 2))
        now[0] += seconds

    sent = []

    def post(url, headers=None, json=None, timeout=None):
        sent.append(url)
        now[0] += 1.0   # 호출 한 번에 1초 걸린다고 가정
        return Resp(200, {"candidates": []})

    g = Gemini(api_key="k", post=post, sleep=sleep, min_interval={"m": 4.5}, clock=lambda: now[0])
    for _ in range(3):
        g.generate("m", "p")
    assert waits == [3.5, 3.5] and len(sent) == 3
    g.generate("other", "p")          # 간격을 정하지 않은 모델은 기다리지 않는다
    assert waits == [3.5, 3.5]


def test_timeout_and_broken_json_become_gemini_errors():
    import pytest
    import requests

    from postlife.gemini import Gemini, GeminiError

    def slow(*a, **k):
        raise requests.ReadTimeout("read timed out")

    g = Gemini(api_key="k", post=slow, sleep=lambda s: None)
    with pytest.raises(GeminiError, match="응답 없음"):
        g.generate("m", "p")
    assert g.calls["m"] == 2          # 한 번만 더 해 본다

    class R:
        status_code = 200

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": '{"benefits": [{"amount_manwon": 1'}]}}]}

    g = Gemini(api_key="k", post=lambda *a, **k: R(), sleep=lambda s: None)
    with pytest.raises(GeminiError, match="JSON으로 읽을 수 없는"):
        g.generate("m", "p", schema={"type": "object"})


# ---------- 모델별 생성 설정, 잘린 응답, 대기와 재시도 ----------

UPPER = config.MODEL_SUMMARY
SCHEMA = {"type": "OBJECT", "properties": {"benefits": {"type": "ARRAY"}}}


def ok(text='{"benefits": []}', finish="STOP", usage=None):
    body = {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": finish}]}
    if usage is not None:
        body["usageMetadata"] = usage
    return Resp(200, body)


def recorder(responses):
    """가짜 post. responses의 항목이 예외면 던지고, 아니면 응답으로 돌려준다. 받은 요청과 대기 시간을 남긴다."""
    sent, waits = [], []

    def post(url, headers=None, json=None, timeout=None):
        sent.append({"url": url, "json": json, "timeout": timeout})
        item = responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    return post, sent, waits


def make(responses, **kw):
    post, sent, waits = recorder(responses)
    return Gemini(api_key="k", post=post, sleep=waits.append, **kw), sent, waits


def test_upper_model_settings_go_into_request_body():
    g, sent, _ = make([ok()])
    assert g.generate(UPPER, "p", schema=SCHEMA) == {"benefits": []}
    gen = sent[0]["json"]["generationConfig"]
    want = config.GENERATION[UPPER]
    assert gen["maxOutputTokens"] == want["maxOutputTokens"]
    assert gen["thinkingConfig"] == want["thinkingConfig"]
    assert "temperature" not in gen                  # 3.6 Flash 이후 모델은 무시하므로 빼도록 정했다
    assert gen["responseMimeType"] == "application/json" and gen["responseSchema"] == SCHEMA
    assert sent[0]["timeout"] == config.TIMEOUT[UPPER]
    # 요청에 넣은 설정을 고쳐도 config 원본은 그대로다
    gen["thinkingConfig"]["thinkingLevel"] = "high"
    assert config.GENERATION[UPPER]["thinkingConfig"] != {"thinkingLevel": "high"}


def test_generation_settings_can_be_overridden_per_model_and_per_call():
    g, sent, _ = make([ok(), ok()], generation={"m": {"maxOutputTokens": 1000, "thinkingConfig": {"thinkingLevel": "medium"}}})
    g.generate("m", "p", schema=SCHEMA)
    assert sent[0]["json"]["generationConfig"] == {
        "temperature": 0.0, "maxOutputTokens": 1000, "thinkingConfig": {"thinkingLevel": "medium"},
        "responseMimeType": "application/json", "responseSchema": SCHEMA}
    g.generate("m", "p", schema=SCHEMA, max_output_tokens=2000)     # 호출할 때 준 값이 앞선다
    assert sent[1]["json"]["generationConfig"]["maxOutputTokens"] == 2000


def test_other_models_send_exactly_the_same_body_as_before():
    # 바꾸기 전 generate()가 만들던 요청 본문을 글자 그대로 적어 둔 것
    def before(prompt, schema=None):
        gen = {"temperature": 0.0, "maxOutputTokens": 8192}
        if schema is not None:
            gen["responseMimeType"] = "application/json"
            gen["responseSchema"] = schema
        return json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gen}, ensure_ascii=False)

    for model in (config.MODEL_EXTRACT, config.MODEL_EXTRACT_ALT, config.MODEL_SEARCH, "m"):
        assert model not in config.GENERATION
        g, sent, _ = make([ok(), Resp(200, {"candidates": []})])
        g.generate(model, "특약 글", schema=SCHEMA)
        g.generate(model, "특약 글")
        assert json.dumps(sent[0]["json"], ensure_ascii=False) == before("특약 글", SCHEMA)
        assert json.dumps(sent[1]["json"], ensure_ascii=False) == before("특약 글")
        assert sent[0]["timeout"] == 90


def test_truncated_response_is_a_distinct_error_and_is_not_called_again():
    usage = {"promptTokenCount": 5210, "candidatesTokenCount": 2648, "thoughtsTokenCount": 30120, "totalTokenCount": 37978}
    g, sent, waits = make([ok('{"benefits": [{"amount": "1,0', finish="MAX_TOKENS", usage=usage)])
    with pytest.raises(GeminiTruncated) as caught:
        g.generate(UPPER, "p", schema=SCHEMA)
    e = caught.value
    assert isinstance(e, GeminiError)                # 부르는 쪽의 except GeminiError가 그대로 잡는다
    assert e.finish_reason == "MAX_TOKENS" and e.usage == usage
    assert e.max_output_tokens == config.GENERATION[UPPER]["maxOutputTokens"]
    text = str(e)
    assert "MAX_TOKENS" in text and "사고 30,120" in text and "답 2,648" in text and "입력 5,210" in text
    assert f"출력 상한 {config.GENERATION[UPPER]['maxOutputTokens']:,}" in text
    assert "JSON으로 읽을 수 없는" not in text
    assert len(sent) == 1 and g.calls[UPPER] == 1 and waits == []
    assert g.last_meta == {"finishReason": "MAX_TOKENS", "usage": usage}

    # 잘렸으면 JSON이 우연히 읽혀도 받지 않는다. 글자 응답(schema 없음)도 같다
    g, sent, _ = make([ok('{"benefits": []}', finish="MAX_TOKENS"), ok("앞부분만", finish="MAX_TOKENS")])
    with pytest.raises(GeminiTruncated, match="출력 상한 8,192"):
        g.generate("m", "p", schema=SCHEMA)
    with pytest.raises(GeminiTruncated):
        g.generate("m", "p")
    assert len(sent) == 2


def test_broken_json_without_truncation_stays_a_parse_error():
    g, _, _ = make([ok('{"benefits": [', finish="STOP"), ok("", finish="RECITATION")])
    with pytest.raises(GeminiError, match="JSON으로 읽을 수 없는") as caught:
        g.generate("m", "p", schema=SCHEMA)
    assert not isinstance(caught.value, GeminiTruncated)
    with pytest.raises(GeminiError, match=r"JSON으로 읽을 수 없는 응답 \(finishReason RECITATION\)"):
        g.generate("m", "p", schema=SCHEMA)


def test_truncation_reason_shows_the_exact_token_counts():
    e = GeminiTruncated("MAX_TOKENS", {"promptTokenCount": 1_429, "thoughtsTokenCount": 30_000}, 32_768)
    assert "입력 1,429" in str(e) and "사고 30,000" in str(e) and "출력 상한 32,768" in str(e)
    assert e.status == 0 and e.usage == {"promptTokenCount": 1_429, "thoughtsTokenCount": 30_000} and e.max_output_tokens == 32_768
    assert usage_text({"promptTokenCount": 1_429}, 4_290) == "출력 상한 4,290, 입력 1,429"
    assert usage_text({}) == "토큰 사용량 없음"


def test_truncated_upper_model_call_does_not_end_the_upper_model_budget_of_the_run():
    from datetime import datetime

    from postlife.extract import pipeline as P
    from postlife.extract.segment import Block
    from postlife.worklog import WorkLog

    usage = {"promptTokenCount": 1_429, "thoughtsTokenCount": 30_000, "candidatesTokenCount": 2_000}
    g, sent, _ = make([ok('{"benefits": [', finish="MAX_TOKENS", usage=usage) for _ in range(5)])
    budget = {"상위모델": 5}
    log = WorkLog(datetime(2026, 11, 20, 14, 0), "t")
    assert P.run_block(g, Block("t", "x", 1, 1), P.DEFAULT_THRESHOLDS, log, "V1", budget) is None
    # 두 추출 모델은 출력 상한을 올려 한 번씩 더 요청하고, 상한이 이미 그 값인 상위 모델은 다시 요청하지 않는다
    assert [s["url"].split("/models/")[1].split(":")[0] for s in sent] == \
        [config.MODEL_EXTRACT, config.MODEL_EXTRACT, config.MODEL_EXTRACT_ALT, config.MODEL_EXTRACT_ALT, UPPER]
    assert budget == {"상위모델": 4}                   # 한 번 쓴 만큼만 줄고, 하루 한도가 찼다고 보지 않는다
    upper = [row for row in log.rows if row["호출모델"] == UPPER]
    assert len(upper) == 1 and "잘림" in upper[0]["사유"] and "MAX_TOKENS" in upper[0]["사유"]


def test_upper_model_timeout_is_not_repeated():
    g, sent, waits = make([requests.ReadTimeout("read timed out"), ok()])
    with pytest.raises(GeminiError, match="응답 없음: ReadTimeout") as caught:
        g.generate(UPPER, "p", schema=SCHEMA)
    assert not isinstance(caught.value, GeminiTruncated)
    assert len(sent) == 1 and g.calls[UPPER] == 1 and waits == []
    assert f"{config.TIMEOUT[UPPER]:g}초" in str(caught.value)


def test_other_models_still_retry_a_timeout_once():
    # 예전 규칙: 시간 초과는 첫 시도에서만 곧바로 한 번 더 한다. 그 뒤 503은 8초의 배수로 기다린다
    g, sent, waits = make([requests.ReadTimeout("x"), Resp(503, {"error": {"message": "바쁨"}}), ok()])
    assert g.generate("m", "p", schema=SCHEMA) == {"benefits": []}
    assert len(sent) == 3 and g.calls["m"] == 3 and waits == [16.0]

    g, sent, waits = make([Resp(503, {}), requests.ReadTimeout("x"), ok()])
    with pytest.raises(GeminiError, match="응답 없음"):
        g.generate("m", "p")
    assert len(sent) == 2 and g.calls["m"] == 2 and waits == [8.0]

    g, sent, _ = make([requests.ReadTimeout("x"), ok()], timeout_retries={"m": 0})
    with pytest.raises(GeminiError, match="응답 없음"):
        g.generate("m", "p")
    assert len(sent) == 1


def test_upper_model_retries_503_on_the_configured_schedule():
    schedule = list(config.RETRY_WAIT[UPPER])
    busy = lambda: Resp(503, {"error": {"message": "This model is currently experiencing high demand."}})

    g, sent, waits = make([busy() for _ in range(len(schedule) + 1)] + [ok()])
    with pytest.raises(GeminiError) as caught:
        g.generate(UPPER, "p", schema=SCHEMA)
    assert caught.value.status == 503
    assert waits == schedule                                   # 정한 간격대로, 정한 횟수만
    assert len(sent) == len(schedule) + 1 == g.calls[UPPER]

    g, sent, waits = make([busy(), ok()])
    assert g.generate(UPPER, "p", schema=SCHEMA) == {"benefits": []}
    assert waits == schedule[:1] and g.calls[UPPER] == 2

    # max_retries를 크게 줘도 간격을 정한 모델은 그 목록만큼만 다시 부른다
    g, sent, waits = make([busy() for _ in range(6)], max_retries=5)
    with pytest.raises(GeminiError):
        g.generate(UPPER, "p")
    assert waits == schedule and g.calls[UPPER] == len(schedule) + 1


def test_retry_schedule_and_statuses_are_set_per_model():
    g, sent, waits = make([Resp(503, {}), Resp(503, {}), Resp(503, {}), ok()], retry_wait={"m": (1.0, 2.0, 4.0)})
    assert g.generate("m", "p", schema=SCHEMA) == {"benefits": []}
    assert waits == [1.0, 2.0, 4.0] and g.calls["m"] == 4

    # 상위 모델은 504(서버가 정한 시간 안에 못 끝냄)를 되풀이하지 않는다. 다른 모델은 예전처럼 다시 한다
    g, sent, waits = make([Resp(504, {}), ok()])
    with pytest.raises(GeminiError):
        g.generate(UPPER, "p")
    assert g.calls[UPPER] == 1 and waits == []

    g, sent, waits = make([Resp(504, {}), Resp(504, {}), Resp(504, {})])
    with pytest.raises(GeminiError):
        g.generate("m", "p")
    assert g.calls["m"] == 3 and waits == [8.0, 16.0]


def test_calls_count_every_attempt_across_models():
    g, sent, _ = make([requests.ReadTimeout("x"),                      # 상위 모델: 시간 초과 1회로 끝
                       Resp(503, {}), ok(),                            # 상위 모델: 503 뒤 성공 (2회)
                       requests.ConnectionError("x"), ok(),            # 다른 모델: 연결 끊김 뒤 성공 (2회)
                       ok(finish="MAX_TOKENS")])                       # 다른 모델: 잘림 1회
    with pytest.raises(GeminiError):
        g.generate(UPPER, "p")
    g.generate(UPPER, "p", schema=SCHEMA)
    g.generate("m", "p", schema=SCHEMA)
    with pytest.raises(GeminiTruncated):
        g.generate("m", "p", schema=SCHEMA)
    assert g.calls == {UPPER: 3, "m": 3}
    assert sum(g.calls.values()) == len(sent) == 6


def test_upper_model_budget_ends_only_on_http_429_not_on_429_in_the_reason_text():
    """상위 모델의 하루 한도가 찼는지는 사유 글자가 아니라 HTTP 상태로 가린다. 사유에 429라는 글자가 있어도 상태가 다르면 남은 횟수를 지키고,
    상태가 429이면 남은 횟수를 0으로 만든다."""
    from datetime import datetime

    from postlife.extract import pipeline as P
    from postlife.extract.segment import Block
    from postlife.worklog import WorkLog

    class Failing:
        calls: dict = {}

        def __init__(self, status, message):
            self.status, self.message = status, message

        def generate(self, model, prompt, schema=None, temperature=0.0):
            raise GeminiError(self.status, self.message)

    for status, message, left in ((503, "요청 1,429건이 밀려 있음 (429 아님)", 4), (429, "한도 초과", 0)):
        budget = {"상위모델": 5}
        log = WorkLog(datetime(2026, 11, 20, 14, 0), "t")
        assert P.run_block(Failing(status, message), Block("t", "x", 1, 1), P.DEFAULT_THRESHOLDS, log, "V1", budget) is None
        assert budget == {"상위모델": left}, (status, budget)


def test_calls_wait_when_the_tokens_sent_in_the_last_minute_would_pass_the_limit():
    """분당 토큰 한도가 정해진 모델은, 최근 60초 동안 보낸 토큰(본문 글자 수로 어림)에 이번 요청을 더해 한도를 넘으면 기다린다."""
    sleeps, clock = [], [0.0]

    def post(url, headers=None, json=None, timeout=None):
        return Resp(200, {"answers": {}})

    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds

    g = Gemini(api_key="k", post=post, sleep=sleep, clock=lambda: clock[0], tokens_per_minute={"m": 2_500})
    text = "가" * 1_000                      # 본문 하나가 1,000자를 조금 넘는다
    g.decide("m", text, {})
    g.decide("m", text, {})
    assert sleeps == []                      # 두 번까지는 2,500 안
    clock[0] = 20.0
    g.decide("m", text, {})                  # 세 번째는 넘는다. 첫 요청이 60초 창에서 빠질 때까지(40초) 기다린다
    assert sleeps == [40.0] and g.token_waits == {"m": 40.0}
    clock[0] += 61.0
    g.decide("m", text, {})                  # 한참 뒤에는 기다리지 않는다
    assert sleeps == [40.0]
    g.decide("other", text, {})              # 한도를 정하지 않은 모델은 세지 않는다
    assert sleeps == [40.0]


def test_token_limit_wait_ends_even_when_sleep_does_not_move_the_clock():
    sleeps = []
    g = Gemini(api_key="k", post=lambda *a, **k: Resp(200, {"answers": {}}), sleep=sleeps.append, clock=lambda: 5.0,
               tokens_per_minute={"m": 1_500})
    for _ in range(4):
        g.decide("m", "가" * 1_000, {})
    assert len(sleeps) == 3 and all(s > 0 for s in sleeps)      # 시계가 멈춰 있어도 요청마다 한 번씩만 기다리고 끝난다


def test_decide_model_has_a_token_limit_in_config():
    assert config.TOKENS_PER_MINUTE[config.MODEL_DECIDE] < 50_000
    g = Gemini(api_key="k", post=lambda *a, **k: Resp(200, {"answers": {}}), sleep=lambda s: None)
    assert g.tokens_per_minute[config.MODEL_DECIDE] == config.TOKENS_PER_MINUTE[config.MODEL_DECIDE]


def test_token_window_counts_a_request_from_when_it_finished():
    """요청이 오래 걸리면 서버는 그 토큰을 보낸 시각보다 늦게 센다. 60초 창은 보낸 시각이 아니라 요청이 끝난 시각부터 잰다.
    실패한 시도(연결 끊김, 4xx)도 같다."""
    sleeps, clock = [], [0.0]
    replies = [requests.ConnectionError("끊김"), Resp(400, {"error": {"message": "잘못"}}), Resp(200, {"answers": {}})]

    def post(url, headers=None, json=None, timeout=None):
        clock[0] += 10.0                     # 요청 하나에 10초 걸린다
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds

    g = Gemini(api_key="k", post=post, sleep=sleep, clock=lambda: clock[0], tokens_per_minute={"m": 2_500}, max_retries=0)
    text = "가" * 1_000
    with pytest.raises(GeminiError):
        g.decide("m", text, {})              # t=0에 보내 t=10에 끝남
    with pytest.raises(GeminiError):
        g.decide("m", text, {})              # t=10에 보내 t=20에 끝남
    g.decide("m", text, {})                  # t=20: 첫 요청이 끝난 t=10에서 60초 뒤(t=70)까지 기다린다
    assert sleeps == [50.0]
