"""응답이 출력 상한에서 잘렸을 때 같은 모델로 상한을 올려 한 번 더 요청하는지 (가입조건 절, 급부 조각).

가입조건 쪽은 실제 Gemini 객체에 가짜 post를 물려 HTTP 요청 본문(지시문, generationConfig)까지 본다.
판정 모델은 가짜로 둔다. 상품 이름과 특약 이름은 지어낸 것이다.
"""
import copy
import json
from datetime import datetime

from postlife import config
from postlife.extract import conditions as C
from postlife.extract import conditions_run as R
from postlife.extract import pipeline as P
from postlife.extract import verify as V
from postlife.extract.segment import pages_from_text
from postlife.gemini import Answer, Gemini, GeminiTruncated, truncation_retry_limit
from postlife.recording import Recording
from postlife.snapshot import KST
from postlife.validate import check_rows
from postlife.worklog import WorkLog

RAISED = config.TRUNCATION_RETRY_MAX_OUTPUT_TOKENS
SECTION = C.Section("가입나이", "2. 가입나이\n최초계약 20~70세 10년만기 전기납", 2, 2)
AGES = {"items": [{"subjects": ["주계약"], "variant_scope": "", "contract": "최초계약", "sex": "구분없음",
                   "age": "20~70세", "term": "10년만기", "payment": "전기납"}]}
USAGE = {"promptTokenCount": 2_491, "candidatesTokenCount": 8_176, "totalTokenCount": 10_667}


class Resp:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, str(body)
        self.headers = {}

    def json(self):
        return self._body


def ok(text):
    return Resp(200, {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]})


def cut():
    """출력 상한에서 잘린 응답 (2026-11-25 하나로OK보험 시험 추출의 토큰 수)."""
    return Resp(200, {"candidates": [{"content": {"parts": [{"text": '{"items": [{"subjects": ["주'}]},
                                      "finishReason": "MAX_TOKENS"}], "usageMetadata": dict(USAGE)})


class Hybrid:
    """generate는 실제 Gemini 객체가 가짜 post로 보내고, decide는 모든 문항에 높은 확률을 준다."""

    def __init__(self, responses):
        self.sent = []

        def post(url, headers=None, json=None, timeout=None):
            self.sent.append({"model": url.split("/models/")[1].split(":")[0], "json": copy.deepcopy(json)})
            return responses.pop(0)

        self.real = Gemini(api_key="k", post=post, sleep=lambda s: None)

    @property
    def calls(self):
        return self.real.calls

    def generate(self, *args, **kwargs):
        return self.real.generate(*args, **kwargs)

    def decide(self, model, text, questions):
        return {k: Answer(True, None, {"true": 0.95, "false": 0.05}) for k in questions}


def section_run(g, budget=0):
    log = WorkLog(datetime(2026, 11, 25, 17, 0, tzinfo=KST), "sys_가입조건")
    shot = R.run_section(g, "가입나이", SECTION, dict(P.DEFAULT_THRESHOLDS), log, "V1:가입나이", {"상위모델": budget})
    return shot, log.rows


def before_body():
    """이번 수정 전에 추출 모델로 보내던 요청 본문 그대로."""
    return {"contents": [{"parts": [{"text": C.prompt_for("가입나이", SECTION.text)}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 8192, "responseMimeType": "application/json",
                                 "responseSchema": C.PROMPTS["가입나이"][1]}}


def test_request_without_truncation_is_unchanged():
    g = Hybrid([ok(json.dumps(AGES))])
    shot, logs = section_run(g)
    assert len(shot.ex.items) == 1
    assert len(g.sent) == 1 and g.calls == {config.MODEL_EXTRACT: 1}
    assert json.dumps(g.sent[0]["json"], ensure_ascii=False, sort_keys=True) == \
        json.dumps(before_body(), ensure_ascii=False, sort_keys=True)
    assert [(l["작업단계"], l["결과"]) for l in logs] == [("추출", "통과")]
    assert not any("출력 상한" in l["사유"] for l in logs)


def test_truncated_section_is_requested_again_with_a_raised_limit_on_the_same_model():
    g = Hybrid([cut(), ok(json.dumps(AGES))])
    shot, logs = section_run(g)
    assert len(shot.ex.items) == 1 and shot.ex.model == config.MODEL_EXTRACT
    assert [s["model"] for s in g.sent] == [config.MODEL_EXTRACT, config.MODEL_EXTRACT]
    first, second = (s["json"] for s in g.sent)
    assert first == before_body()                                  # 첫 요청은 예전과 같다
    assert second["contents"] == first["contents"]                 # 지시문은 그대로, 상한만 올린다
    assert second["generationConfig"] == dict(first["generationConfig"], maxOutputTokens=RAISED)
    assert g.calls == {config.MODEL_EXTRACT: 2}                    # 다시 요청한 호출도 호출 수에 든다
    assert [(l["작업단계"], l["결과"], l["호출모델"]) for l in logs] == \
        [("추출", "보류", config.MODEL_EXTRACT), ("추출", "통과", config.MODEL_EXTRACT)]
    assert f"출력 상한 {RAISED:,}로 올려 같은 모델로 다시 요청" in logs[0]["사유"] and "MAX_TOKENS" in logs[0]["사유"]
    assert f"출력 상한 {RAISED:,}로 다시 요청한 답" in logs[1]["사유"]
    assert check_rows("sys_작업로그", logs) == {}


def test_truncated_again_goes_to_the_next_model():
    g = Hybrid([cut(), cut(), ok(json.dumps(AGES))])
    shot, logs = section_run(g)
    assert shot.ex.model == config.MODEL_EXTRACT_ALT and len(shot.ex.items) == 1
    assert [(s["model"], s["json"]["generationConfig"]["maxOutputTokens"]) for s in g.sent] == \
        [(config.MODEL_EXTRACT, 8192), (config.MODEL_EXTRACT, RAISED), (config.MODEL_EXTRACT_ALT, 8192)]
    assert g.calls == {config.MODEL_EXTRACT: 2, config.MODEL_EXTRACT_ALT: 1}
    assert [(l["작업단계"], l["결과"], l["호출모델"]) for l in logs] == \
        [("추출", "보류", config.MODEL_EXTRACT), ("추출", "보류", config.MODEL_EXTRACT), ("추출", "통과", config.MODEL_EXTRACT_ALT)]
    assert f"호출 실패(출력 상한 {RAISED:,}로 올려 다시 요청한 뒤)" in logs[1]["사유"] and f"출력 상한 {RAISED:,}" in logs[1]["사유"]
    assert "다시 요청한 답" not in logs[2]["사유"]


def test_rejected_raised_limit_goes_to_the_next_model_as_before():
    # 모델이 올린 상한을 받아들이지 않아 400이 오면 다시 시도하지 않고 다음 모델로 넘어간다
    bad = Resp(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "maxOutputTokens is too large"}})
    g = Hybrid([cut(), bad, ok(json.dumps(AGES))])
    shot, logs = section_run(g)
    assert shot.ex.model == config.MODEL_EXTRACT_ALT
    assert [s["model"] for s in g.sent] == [config.MODEL_EXTRACT, config.MODEL_EXTRACT, config.MODEL_EXTRACT_ALT]
    assert "400" in logs[1]["사유"] and "다시 요청한 뒤" in logs[1]["사유"]


def test_upper_model_is_not_requested_again_and_each_model_retries_once():
    g = Hybrid([cut() for _ in range(5)])
    budget = {"상위모델": 3}
    log = WorkLog(datetime(2026, 11, 25, 17, 0, tzinfo=KST), "sys_가입조건")
    assert R.run_section(g, "가입나이", SECTION, dict(P.DEFAULT_THRESHOLDS), log, "V1:가입나이", budget) is None
    assert [(s["model"], s["json"]["generationConfig"]["maxOutputTokens"]) for s in g.sent] == \
        [(config.MODEL_EXTRACT, 8192), (config.MODEL_EXTRACT, RAISED), (config.MODEL_EXTRACT_ALT, 8192),
         (config.MODEL_EXTRACT_ALT, RAISED), (config.MODEL_SUMMARY, config.GENERATION[config.MODEL_SUMMARY]["maxOutputTokens"])]
    assert budget == {"상위모델": 2}                 # 상위 모델은 한 번만 쓴다
    assert len(log.rows) == 5 and all(l["결과"] == "보류" for l in log.rows)


def test_retry_limit_only_for_truncation_below_the_raised_limit():
    assert truncation_retry_limit(GeminiTruncated("MAX_TOKENS", {}, 8192)) == RAISED
    assert truncation_retry_limit(GeminiTruncated("MAX_TOKENS", {}, RAISED)) is None
    assert truncation_retry_limit(GeminiTruncated("MAX_TOKENS", {}, None)) == RAISED
    assert truncation_retry_limit(ValueError("x")) is None
    assert RAISED == config.GENERATION[config.MODEL_SUMMARY]["maxOutputTokens"]


def test_recording_keeps_the_raised_limit():
    g = Hybrid([ok(json.dumps(AGES)), ok(json.dumps(AGES))])
    rec = Recording(g)
    rec.generate(config.MODEL_EXTRACT, "p", {"type": "OBJECT"})
    rec.generate(config.MODEL_EXTRACT, "p", {"type": "OBJECT"}, max_output_tokens=RAISED)
    assert "max_output_tokens" not in rec.records[0] and rec.records[1]["max_output_tokens"] == RAISED


# ---------- 급부 조각 ----------

TEXT = """
===== 10쪽 =====
② 보험금 지급사유
■ 무배당 가상진단특약(20년갱신형) 2699
(특약보험가입금액 1,000만원 기준)
가상진단보험금 최초 1회에 한함 1,000만원
■ 무배당 가상입원특약(20년갱신형) 2699
(특약보험가입금액 1,000만원 기준)
가상입원보험금 1일당 120일 한도 2만원
③ 일반적 보험금 지급제한 사유
"""
GOOD = {"진단": {"base_amount": "1,000만원", "benefits": [
            {"name": "가상진단보험금", "target": "", "amount": "1,000만원", "start_condition": "", "limit": "최초 1회에 한함",
             "role": "주급부", "quote": "1,000만원"}]},
        "입원": {"base_amount": "1,000만원", "benefits": [
            {"name": "가상입원보험금", "target": "", "amount": "2만원", "start_condition": "", "limit": "1일당 120일 한도",
             "role": "주급부", "quote": "2만원"}]}}


class CutBenefits:
    """진단특약 조각은 출력 상한을 주지 않은 요청이면 잘리고, 올린 상한을 주면 답한다. cut_raised면 올려도 잘린다."""

    def __init__(self, cut_raised=False):
        self.cut_raised, self.calls, self.requests = cut_raised, {}, []

    def generate(self, model, prompt, schema=None, temperature=0.0, max_output_tokens=None):
        self.calls[model] = self.calls.get(model, 0) + 1
        diag = "가상진단특약" in prompt.split("본문")[0]
        self.requests.append((model, "진단" if diag else "입원", max_output_tokens))
        if diag and (max_output_tokens is None or self.cut_raised) and model == config.MODEL_EXTRACT:
            raise GeminiTruncated("MAX_TOKENS", dict(USAGE), max_output_tokens or 8192)
        return GOOD["진단" if diag else "입원"]

    def decide(self, model, input_text, questions):
        out = {}
        for key, q in questions.items():
            if q["type"] == "choice":
                out[key] = Answer(V.FROM_DAY_ONE, None, {V.AFTER_START: 0.03, V.FROM_DAY_ONE: 0.97})
            else:
                out[key] = Answer(True, None, {"true": 0.97, "false": 0.03})
        return out


def summary_run(g):
    return P.run_summary(g, pages_from_text(TEXT), ["V1"], datetime(2026, 11, 25, 17, 0, tzinfo=KST), product_renewal_years=20)


def test_truncated_benefit_block_is_requested_again_on_the_same_model():
    g = CutBenefits()
    r = summary_run(g)
    assert sorted(row["기준지급금액만원"] for row in r.benefits) == [2, 1000]
    assert g.requests[:2] == [(config.MODEL_EXTRACT, "진단", None), (config.MODEL_EXTRACT, "진단", RAISED)]
    assert (config.MODEL_EXTRACT, "입원", None) in g.requests          # 잘리지 않은 조각은 상한 없이 한 번만
    assert len(g.requests) == 3 and g.calls == {config.MODEL_EXTRACT: 3}
    held = [l for l in r.logs if l["결과"] == "보류" and "출력 상한" in (l["사유"] or "")]
    assert len(held) == 1 and f"출력 상한 {RAISED:,}로 올려 같은 모델로 다시 요청" in held[0]["사유"]
    passed = [l for l in r.logs if l["작업단계"] == "추출" and l["결과"] == "통과" and "가상진단" in (l["사유"] or "")]
    assert len(passed) == 1 and f"출력 상한 {RAISED:,}로 다시 요청한 답" in passed[0]["사유"]
    assert r.stats["재추출한 조각"] == 0 and check_rows("sys_작업로그", r.logs) == {}


def test_benefit_block_truncated_again_goes_to_the_next_model():
    g = CutBenefits(cut_raised=True)
    r = summary_run(g)
    assert sorted(row["기준지급금액만원"] for row in r.benefits) == [2, 1000]
    diag = [(m, limit) for m, part, limit in g.requests if part == "진단"]
    assert diag == [(config.MODEL_EXTRACT, None), (config.MODEL_EXTRACT, RAISED), (config.MODEL_EXTRACT_ALT, None)]
    failed = [l for l in r.logs if f"호출 실패(출력 상한 {RAISED:,}로 올려 다시 요청한 뒤)" in (l["사유"] or "")]
    assert len(failed) == 1 and failed[0]["호출모델"] == config.MODEL_EXTRACT
