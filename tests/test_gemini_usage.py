"""판정 응답의 실제 입력 토큰으로 분당 토큰 창을 맞추는 일과, 오류 응답의 상세를 GeminiError에 남기는 일.

모델 API는 부르지 않는다. tests/test_gemini.py처럼 가짜 post, sleep, clock을 넘긴다.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from requests.structures import CaseInsensitiveDict

from postlife import config, gemini as gemini_api, ids, sheets_io
from postlife.gemini import Gemini, GeminiError, GeminiTruncated, input_tokens_report
from postlife.recording import Recording

ROOT = Path(__file__).resolve().parents[1]
KEY = "secret-key-123"


class Resp:
    def __init__(self, status, body, headers=None, text=None):
        self.status_code = status
        self._body = body
        self.text = str(body) if text is None else text
        if headers is not None:
            self.headers = headers

    def json(self):
        if isinstance(self._body, BaseException):
            raise self._body
        return self._body


class NotJson(Resp):
    def __init__(self, status, text, headers=None):
        super().__init__(status, ValueError("Expecting value"), headers, text)


def answered(tokens=None, usage=None):
    body = {"answers": {}}
    if usage is not None:
        body["usage"] = usage
    elif tokens is not None:
        body["usage"] = {"total_input_tokens": tokens, "input_tokens_by_modality": [{"modality": "text", "tokens": tokens}],
                         "total_output_tokens": 0, "total_tokens": tokens}
    return Resp(200, body)


def chars(model, text, questions=None):
    """decide가 보내는 본문의 글자 수. 분당 토큰 창의 어림과 같은 셈이다."""
    return len(json.dumps({"model": model, "input": text, "questions": questions or {}}, ensure_ascii=False))


def paced(replies, limit=2_500, **kw):
    """시계를 손으로 움직이는 Gemini. post는 시간을 쓰지 않는다. replies의 항목을 차례로 돌려주고, 예외면 던진다."""
    sleeps, clock = [], [0.0]

    def post(url, headers=None, json=None, timeout=None):
        item = replies.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds

    g = Gemini(api_key=KEY, post=post, sleep=sleep, clock=lambda: clock[0], tokens_per_minute={"m": limit}, **kw)
    return g, sleeps, clock


TEXT = "가" * 1_000
C1 = chars("m", TEXT)


# ---------- (가) 판정 응답의 실제 입력 토큰 ----------

def test_smaller_actual_tokens_shorten_the_wait():
    # 바꾸기 전과 같은 흐름: 어림(글자 수)으로는 세 번째 요청이 한도를 넘어 40초 기다린다
    g, sleeps, clock = paced([answered(), answered(), answered()])
    g.decide("m", TEXT, {})
    g.decide("m", TEXT, {})
    clock[0] = 20.0
    g.decide("m", TEXT, {})
    assert sleeps == [40.0] and g.input_tokens == {}

    # 응답이 실제 입력 토큰을 300이라고 알려 주면 창에 300씩 남고, 다음 어림도 그 비율(1보다 작다)로 낸다
    g, sleeps, clock = paced([answered(300), answered(300), answered(300)])
    g.decide("m", TEXT, {})
    g.decide("m", TEXT, {})
    clock[0] = 20.0
    g.decide("m", TEXT, {})
    assert sleeps == [] and g.token_waits == {}
    assert g.input_tokens == {"m": {"calls": 3, "chars": 3 * C1, "tokens": 900}}


def test_larger_actual_tokens_lengthen_the_wait():
    # 바꾸기 전에는 두 요청(어림 약 1,040씩)이 2,500 안에 들어 기다리지 않았다
    g, sleeps, clock = paced([answered(), answered()])
    g.decide("m", TEXT, {})
    clock[0] = 20.0
    g.decide("m", TEXT, {})
    assert sleeps == []

    # 실제가 2,000이면 창에 2,000이 남고 다음 요청도 2,000으로 어림해 한도를 넘는다. 첫 요청이 빠질 때까지(40초) 기다린다
    g, sleeps, clock = paced([answered(2_000), answered(2_000)])
    g.decide("m", TEXT, {})
    clock[0] = 20.0
    g.decide("m", TEXT, {})
    assert sleeps == [40.0] and g.token_waits == {"m": 40.0}


def test_the_window_keeps_the_actual_count_of_the_request_just_answered():
    # 다음 요청이 아주 작아 비율만으로는 차이가 나지 않게 해, 창에 남은 값이 어림에서 실제로 바뀐 것만 본다
    small = chars("m", "")
    nxt = int(small * 2_000 / C1)
    limit = 2_050
    assert C1 + nxt <= limit < 2_000 + nxt          # 창에 어림(C1)이 남았다면 기다리지 않는다
    g, sleeps, clock = paced([answered(2_000), answered()], limit=limit)
    g.decide("m", TEXT, {})
    clock[0] = 20.0
    g.decide("m", "", {})
    assert sleeps == [40.0]


def test_the_observed_ratio_is_used_for_the_next_estimate():
    # 첫 응답이 글자당 2토큰을 알려 준다. 그 요청이 창에서 빠진 뒤에도 비율은 남아, usage가 없는 응답 뒤의 어림에도 쓰인다
    g, sleeps, clock = paced([answered(2 * C1), answered(), answered()])
    g.decide("m", TEXT, {})
    clock[0] = 100.0
    g.decide("m", TEXT, {})                  # 창이 비어 있다. 어림 2 × C1
    assert sleeps == []
    g.decide("m", TEXT, {})                  # 2 × C1 두 개는 2,500을 넘는다 (바꾸기 전에는 C1 두 개라 넘지 않았다)
    assert sleeps == [60.0]
    assert g.input_tokens == {"m": {"calls": 1, "chars": C1, "tokens": 2 * C1}}


def test_actual_tokens_above_the_limit_are_cut_to_the_limit_in_the_window():
    g, sleeps, clock = paced([answered(10_000), answered()])
    g.decide("m", TEXT, {})
    assert [n for _, n in g._sent["m"]] == [2_500]          # 창에는 한도까지만 적는다 (어림도 그렇게 자른다)
    assert g.input_tokens["m"]["tokens"] == 10_000          # 모은 수치는 응답이 알려 준 값 그대로다
    clock[0] = 10.0
    g.decide("m", TEXT, {})                                  # 다음 어림도 한도로 잘려, 한 번만 기다리고 끝난다
    assert sleeps == [50.0]


@pytest.mark.parametrize("usage", [
    {"total_output_tokens": 0},                       # 2026-11-18에 받은 응답의 꼴 (tests/test_gemini.py의 DECISION)
    {"total_input_tokens": 0}, {"total_input_tokens": -3}, {"total_input_tokens": "100"},
    {"total_input_tokens": 100.0}, {"total_input_tokens": True}, {"total_input_tokens": None},
    {"input_tokens_by_modality": [{"modality": "text", "tokens": 100}]},
    "100", [100], 100,
])
def test_missing_or_odd_usage_behaves_exactly_as_before(usage):
    g, sleeps, clock = paced([answered(usage=usage) for _ in range(3)])
    g.decide("m", TEXT, {})
    g.decide("m", TEXT, {})
    clock[0] = 20.0
    g.decide("m", TEXT, {})
    assert sleeps == [40.0] and g.token_waits == {"m": 40.0} and g.input_tokens == {}
    assert [n for _, n in g._sent["m"]] == [C1, C1]          # 첫 요청은 기다리는 동안 창에서 빠졌고, 남은 값은 어림 그대로다


def test_collected_numbers_count_answered_requests_and_skip_failed_attempts():
    # 429 한 번 뒤 성공: 창에는 두 시도가 남고, 실제 값으로 바뀌는 것은 답을 준 마지막 시도뿐이다
    g, sleeps, clock = paced([answered(300), Resp(429, {"error": {"message": "한도"}}), answered(700), answered()],
                             limit=1_000_000)
    g.decide("m", TEXT, {})
    g.decide("m", TEXT, {})
    g.decide("m", TEXT, {})
    assert g.calls == {"m": 4} and sleeps == [8.0]           # 다시 시도 규칙은 그대로다
    after_first = int(C1 * (300 / C1))                        # 둘째 요청의 두 시도는 첫 응답의 비율로 어림한다
    assert [n for _, n in g._sent["m"]] == [300, after_first, 700, int(C1 * (1_000 / (2 * C1)))]
    assert g.input_tokens == {"m": {"calls": 2, "chars": 2 * C1, "tokens": 1_000}}

    # 분당 토큰 한도가 없는 모델도 모으기만 하고 기다리지 않는다. generate와 search는 모으지 않는다
    ok = {"candidates": [{"content": {"parts": [{"text": "x"}]}}], "usageMetadata": {"promptTokenCount": 99}}
    g, sleeps, clock = paced([answered(50), Resp(200, ok), Resp(200, ok)])
    g.decide("other", "가", {})
    g.generate("other", "가")
    g.search("other", "가")
    assert sleeps == [] and "other" not in g._sent
    assert g.input_tokens == {"other": {"calls": 1, "chars": chars("other", "가"), "tokens": 50}}


def test_report_adds_the_ratio_and_recording_shows_the_numbers():
    g, _, _ = paced([answered(500)])
    wrapped = Recording(g)
    wrapped.decide("m", TEXT, {})
    assert wrapped.input_tokens is g.input_tokens                  # 감싼 객체에서도 같은 값이 보인다
    assert input_tokens_report(wrapped.input_tokens) == {
        "m": {"calls": 1, "chars": C1, "tokens": 500, "tokens_per_char": round(500 / C1, 4)}}
    assert input_tokens_report({}) == {} and input_tokens_report(None) == {}
    assert input_tokens_report({"m": {"calls": 0, "chars": 0, "tokens": 0}})["m"]["tokens_per_char"] is None


# ---------- (가) 스크립트가 남기는 수치 ----------

def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_gemini(tokens):
    """스크립트가 만드는 Gemini 대신 끼울 공장. 진짜 Gemini에 가짜 post를 넘긴다. 판정 응답은 모든 문항을 '해당없음'으로 답한다."""
    def post(url, headers=None, json=None, timeout=None):
        answers = {k: {"type": "choice", "choice": "해당없음", "probabilities": {"해당없음": 0.97}} for k in json["questions"]}
        return Resp(200, {"answers": answers, "usage": {"total_input_tokens": tokens}})

    made = []

    def factory(**kw):
        g = Gemini(api_key=KEY, post=post, sleep=lambda s: None, clock=lambda: 0.0, **kw)
        made.append(g)
        return g

    return factory, made


def test_map_script_prints_the_decide_model_input_tokens(monkeypatch, capsys):
    from postlife.schema import TABS
    from postlife.sheets_io import MemoryBackend, rows_to_values

    S = _load("map_benefits")
    dictionary = [json.loads(l) for l in (ROOT / "data/seed/hum_표준담보사전.jsonl").read_text(encoding="utf-8").splitlines()
                  if l.strip()]
    rid = ids.rider_id("V1", "주계약")
    tabs = {"sys_상품종형": [{"종형ID": "V1", "공시상품명": "상품 V1"}],
            "sys_특약": [{"특약ID": rid, "종형ID": "V1", "특약계보키": ids.rider_lineage_key("주계약"), "담보구분": "주계약",
                         "원시특약명": "주계약"}],
            "sys_급부": [{"급부ID": ids.benefit_id(rid, "재해사망보험금"), "특약ID": rid, "원시급부명": "재해사망보험금"}],
            "hum_표준담보사전": dictionary, "hum_담보매핑": []}
    backend = MemoryBackend({n: [list(TABS[n].header)] + rows_to_values(TABS[n], rows) for n, rows in tabs.items()})
    for key in ("GOOGLE_SERVICE_ACCOUNT_JSON", "SPREADSHEET_ID", "GEMINI_API_KEY"):
        monkeypatch.setenv(key, "test")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(sheets_io.RestBackend, "from_env", classmethod(lambda cls: backend))
    factory, made = _fake_gemini(4_000)
    monkeypatch.setattr(S, "Gemini", factory)

    assert S.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    (g,) = made
    seen = g.input_tokens[config.MODEL_DECIDE]
    assert seen["calls"] == g.calls[config.MODEL_DECIDE] == 1 and seen["tokens"] == 4_000
    line = next(l for l in out.splitlines() if l.startswith("판정 모델 입력 토큰:"))
    assert json.loads(line.split(":", 1)[1]) == {**seen, "tokens_per_char": round(4_000 / seen["chars"], 4)}
    assert out.index("모델별 호출 수:") < out.index("판정 모델 입력 토큰:")


def test_extract_script_saves_input_tokens_next_to_calls(monkeypatch, tmp_path):
    E = _load("extract_product")
    factory, made = _fake_gemini(1_200)

    def run(gemini, store, targets, index, read_text, now, **kw):
        gemini.decide(config.MODEL_DECIDE, "가" * 2_000, {"q": {"type": "noul"}})
        return SimpleNamespace(rows={}, logs=[], errors=[], notes=[], write_error=None, done=1, conditions_done=0,
                               written=False, markdown=lambda calls: f"모델별 호출 수: {calls}\n")

    monkeypatch.setattr(E, "Gemini", factory)
    monkeypatch.setattr(E, "job", SimpleNamespace(run=run))
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    for key in ("GOOGLE_SERVICE_ACCOUNT_JSON", "SPREADSHEET_ID", "GITHUB_STEP_SUMMARY"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.json").write_text("{}", encoding="utf-8")
    (tmp_path / "targets.json").write_text("[]", encoding="utf-8")
    result = tmp_path / "out" / "result.json"
    monkeypatch.setattr("sys.argv", ["extract_product.py", "--docs", str(tmp_path / "docs"), "--targets",
                                     str(tmp_path / "targets.json"), "--dry-run", "--result", str(result)])
    assert E.main() == 0
    body = json.loads(result.read_text(encoding="utf-8"))
    width = chars(config.MODEL_DECIDE, "가" * 2_000, {"q": {"type": "noul"}})
    assert body["calls"] == {config.MODEL_DECIDE: 1} and body["token_waits"] == {}
    assert body["input_tokens"] == {config.MODEL_DECIDE: {"calls": 1, "chars": width, "tokens": 1_200,
                                                          "tokens_per_char": round(1_200 / width, 4)}}


# ---------- (나) 오류 응답의 상세 ----------

UPPER = config.MODEL_SUMMARY
QUOTA_ID = "GenerateContentInputTokensPerModelPerMinute-FreeTier"
LONG = ("You exceeded your current quota, please check your plan and billing details. For more information on this error, "
        "head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: "
        "https://ai.dev/usage?tab=rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/"
        "generate_content_free_tier_input_token_count, limit: 50000\nPlease retry in 23.5s.")
# 게시판 글에 올라온 429 본문의 꼴(공식 문서에 없는 꼴이다). 프로젝트 번호가 든 값(consumer)과 설명, 링크는 남기지 않아야 한다
DETAILED = {"error": {
    "code": 429, "message": LONG, "status": "RESOURCE_EXHAUSTED",
    "details": [
        {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
         "violations": [{"quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_input_token_count",
                         "quotaId": QUOTA_ID, "quotaDimensions": {"location": "global", "model": "gemini-decision-1"},
                         "quotaValue": "50000", "subject": "project:123456789", "description": "긴 설명"}]},
        {"@type": "type.googleapis.com/google.rpc.Help", "links": [{"description": "Learn more", "url": "https://x"}]},
        {"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "RATE_LIMIT_EXCEEDED",
         "metadata": {"consumer": "projects/123456789", "quota_limit_value": "50000"}},
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "23s"},
    ]}}
DETAILED_INFO = {
    "code": 429, "status": "RESOURCE_EXHAUSTED",
    "details": [
        {"type": "QuotaFailure", "violations": [{
            "quotaId": QUOTA_ID, "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_input_token_count",
            "quotaValue": "50000", "quotaDimensions": {"location": "global", "model": "gemini-decision-1"}}]},
        {"type": "Help"},
        {"type": "ErrorInfo", "reason": "RATE_LIMIT_EXCEEDED", "metadata": {"quota_limit_value": "50000"}},
        {"type": "RetryInfo", "retryDelay": "23s"},
    ]}


def failing(replies, **kw):
    sent, waits = [], []

    def post(url, headers=None, json=None, timeout=None):
        sent.append(json)
        return replies.pop(0)

    return Gemini(api_key=KEY, post=post, sleep=waits.append, **kw), sent, waits


def raised(replies, model="m", **kw):
    g, sent, waits = failing(replies, **kw)
    with pytest.raises(GeminiError) as caught:
        g.generate(model, "지시문 원문")
    return caught.value, g, waits


def test_a_429_with_details_keeps_the_quota_and_retry_values():
    e, g, waits = raised([Resp(429, DETAILED) for _ in range(3)])
    assert e.status == 429 and e.info == DETAILED_INFO
    tail = f"[status=RESOURCE_EXHAUSTED, retryDelay=23s, reason=RATE_LIMIT_EXCEEDED, quotaId={QUOTA_ID}]"
    assert str(e) == f"Gemini API 429 {tail}: {LONG[:400]}"
    # 기록하는 쪽은 글 앞 200자만 남긴다(mapping.run, pipeline.run_block). 요약이 그 안에 든다
    assert tail in str(e)[:200]
    text = str(e) + json.dumps(e.info, ensure_ascii=False)
    for secret in (KEY, "지시문 원문", "123456789", "Learn more", "긴 설명"):
        assert secret not in text
    assert waits == [8.0, 16.0] and g.calls == {"m": 3}       # 다시 시도 횟수와 기다림은 그대로다


def test_a_429_without_details_and_with_only_a_message():
    e, _, _ = raised([Resp(429, {"error": {"code": 429, "message": "한도", "status": "RESOURCE_EXHAUSTED"}})], max_retries=0)
    assert e.info == {"code": 429, "status": "RESOURCE_EXHAUSTED"}
    assert str(e) == "Gemini API 429 [status=RESOURCE_EXHAUSTED]: 한도"
    # 상세가 없으면 바꾸기 전 글 그대로다
    e, _, _ = raised([Resp(429, {"error": {"message": "한도"}})], max_retries=0)
    assert e.info == {} and str(e) == "Gemini API 429: 한도"
    e, _, _ = raised([Resp(503, {})], max_retries=0)
    assert e.info == {} and str(e) == "Gemini API 503: "
    # Interactions API 문서의 꼴: error.code가 글자다. HTTP 상태와 다르니 글에도 적는다
    e, _, _ = raised([Resp(429, {"error": {"code": "rate_limit_exceeded", "message": "분당 한도"}})], max_retries=0)
    assert e.info == {"code": "rate_limit_exceeded"} and str(e) == "Gemini API 429 [code=rate_limit_exceeded]: 분당 한도"


def test_a_body_that_is_not_json_or_has_another_shape_falls_back_to_the_text():
    html = "<html><body>429 Too Many Requests</body></html>"
    e, g, waits = raised([NotJson(429, html) for _ in range(3)])
    assert e.info == {} and str(e) == f"Gemini API 429: {html}"
    assert waits == [8.0, 16.0] and g.calls == {"m": 3}
    for body in ([1, 2], {"error": "문자열 오류"}, {"error": {"message": None}}, {"error": {"message": 5}},
                 {"error": {"message": "x", "details": "목록 아님"}},
                 {"error": {"message": "x", "details": ["글자", 3, None, {"@type": 7, "violations": "목록 아님"}]}},
                 {"error": {"message": "x", "code": {"중첩": 1}, "status": ["목록"]}}):
        e, _, _ = raised([Resp(400, body)])
        assert e.status == 400
        assert isinstance(e.info, dict) and "details" not in e.info and "code" not in e.info and "status" not in e.info
    e, _, _ = raised([Resp(400, {"error": {"message": None}})])
    assert str(e) == "Gemini API 400: {'error': {'message': None}}"       # 글이 아닌 message는 본문 글로 떨어진다
    e, _, _ = raised([Resp(400, {"error": "문자열 오류"})])
    assert str(e) == "Gemini API 400: {'error': '문자열 오류'}"              # 바꾸기 전과 같다


def test_the_retry_after_header_is_kept():
    e, _, _ = raised([NotJson(429, "busy", headers={"Retry-After": "30"})], max_retries=0)
    assert e.info == {"retry_after": "30"} and str(e) == "Gemini API 429 [Retry-After=30]: busy"
    lower = CaseInsensitiveDict({"retry-after": "12"})
    e, _, _ = raised([Resp(429, {"error": {"code": 429, "message": "m", "status": "RESOURCE_EXHAUSTED"}}, headers=lower)],
                     max_retries=0)
    assert e.info == {"code": 429, "status": "RESOURCE_EXHAUSTED", "retry_after": "12"}
    assert str(e) == "Gemini API 429 [status=RESOURCE_EXHAUSTED, Retry-After=12]: m"
    e, _, _ = raised([NotJson(429, "busy", headers={"Content-Type": "text/html"})], max_retries=0)
    assert e.info == {}


def test_retry_rules_do_not_look_at_the_details():
    # 상위 모델: 정한 간격대로 다시 하고, 400은 다시 하지 않는다. 상세가 있어도 같다
    schedule = list(config.RETRY_WAIT[UPPER])
    e, g, waits = raised([Resp(429, DETAILED) for _ in range(len(schedule) + 1)], model=UPPER)
    assert e.status == 429 and waits == schedule and g.calls == {UPPER: len(schedule) + 1}
    e, g, waits = raised([Resp(400, DETAILED)], model=UPPER)
    assert waits == [] and g.calls == {UPPER: 1}
    # 상세가 있는 429 뒤에 성공하면 예전처럼 답을 돌려준다
    g, sent, waits = failing([Resp(429, DETAILED), Resp(200, {"candidates": []})])
    assert g.generate("m", "p") == "" and waits == [8.0] and len(sent) == 2
    # 하루 한도는 여전히 HTTP 상태로만 가린다 (pipeline.run_block의 getattr(e, "status"))
    assert GeminiError(429, "x", {"status": "다른 값"}).status == 429


def test_long_details_are_cut_in_the_text_but_kept_in_info():
    many = {"error": {"code": 429, "message": "m", "status": "RESOURCE_EXHAUSTED", "details": [
        {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
         "violations": [{"quotaId": f"Quota{i:02d}PerMinutePerProjectPerModel-FreeTier"} for i in range(12)]}]}}
    e, _, _ = raised([Resp(429, many)], max_retries=0)
    head = str(e).split("]: ", 1)[0]
    assert len(head) <= len("Gemini API 429 [") + gemini_api._INFO_TEXT_MAX and head.endswith("…")
    assert len(e.info["details"][0]["violations"]) == 10                   # 항목은 열 개까지만 담는다


def test_the_retry_time_stays_in_the_text_when_several_quotas_are_named():
    # 한도 항목이 둘이면 quotaId 두 개만으로 요약이 160자를 넘는다. 다시 보낼 시각은 앞에 두어 잘리지 않고, 잘리는 것은 뒤쪽 quotaId다
    per_minute = "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"
    two = {"error": {"code": 429, "message": "You exceeded your current quota.", "status": "RESOURCE_EXHAUSTED", "details": [
        {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{"quotaId": per_minute}, {"quotaId": QUOTA_ID}]},
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "23s"}]}}
    e, _, _ = raised([Resp(429, two, headers={"Retry-After": "23"})], max_retries=0)
    head, message = str(e).split("]: ", 1)
    assert head.startswith(f"Gemini API 429 [status=RESOURCE_EXHAUSTED, retryDelay=23s, Retry-After=23, quotaId={per_minute}, "
                           "quotaId=Generate") and head.endswith("…")
    assert len(head) == len("Gemini API 429 [") + gemini_api._INFO_TEXT_MAX and message == "You exceeded your current quota."
    assert "retryDelay=23s" in str(e)[:200] and "Retry-After=23" in str(e)[:200]     # 글 앞 200자만 남기는 기록에도 든다
    assert e.info["details"][0]["violations"] == [{"quotaId": per_minute}, {"quotaId": QUOTA_ID}]   # info에는 잘리지 않고 남는다

    # 한도 항목이 열 개를 넘어도 다시 보낼 시각과 reason은 요약 앞쪽에 남는다
    many = {"error": {"code": 429, "message": "m", "status": "RESOURCE_EXHAUSTED", "details": [
        {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
         "violations": [{"quotaId": f"Quota{i:02d}PerMinutePerProjectPerModel-FreeTier"} for i in range(12)]},
        {"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "RATE_LIMIT_EXCEEDED"},
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "59s"}]}}
    e, _, _ = raised([Resp(429, many)], max_retries=0)
    assert str(e).startswith("Gemini API 429 [status=RESOURCE_EXHAUSTED, retryDelay=59s, reason=RATE_LIMIT_EXCEEDED, quotaId=Quota00")


def test_other_errors_keep_their_text():
    assert str(GeminiError(503, "high demand")) == "Gemini API 503: high demand"
    assert GeminiError(503, "high demand").info == {}
    t = GeminiTruncated("MAX_TOKENS", {"promptTokenCount": 1}, 10)
    assert t.info == {} and str(t).startswith("Gemini API 0: 응답이 토큰 상한에서 잘림")
