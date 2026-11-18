from datetime import datetime

from postlife import config
from postlife.extract import pipeline as P
from postlife.extract import verify as V
from postlife.extract.segment import pages_from_text
from postlife.gemini import Answer
from postlife.snapshot import KST
from postlife.validate import check_rows

TEXT = """
===== 10쪽 =====
② 보험금 지급사유
■ 무배당 암진단특약(20년갱신형) 2606
(특약보험가입금액 1,000만원 기준)
암진단 보험금 최초 1회에 한함 1년미만 500만원 1년이상 1,000만원
주) 암보장개시일은 계약일부터 그 날을 포함하여 90일이 지난날의 다음날
■ 무배당 첫날부터재해입원특약(20년갱신형) 2606
(특약보험가입금액 1,000만원 기준)
재해입원보험금 1일당 120일 한도 2만원
③ 일반적 보험금 지급제한 사유
"""
GOOD = {"암진단": {"base_amount": "1,000만원", "benefits": [
            {"name": "암진단보험금", "target": "", "amount": "1,000만원", "reduced_period": "1년미만", "reduced_amount": "500만원",
             "start_condition": "암보장개시일", "limit": "최초 1회에 한함", "role": "주급부", "quote": "1년이상 1,000만원"}]},
        "재해입원": {"base_amount": "1,000만원", "benefits": [
            {"name": "재해입원보험금", "target": "", "amount": "2만원", "start_condition": "", "limit": "1일당 120일 한도",
             "role": "주급부", "quote": "2만원"}]}}
WRONG = {"base_amount": "1,000만원", "benefits": [dict(GOOD["암진단"]["benefits"][0], amount="3,000만원")]}


class FakeGemini:
    """첫 모델은 암진단 금액을 틀리게 뽑고, 판정 모델이 그것을 잡아낸다."""

    def __init__(self, first_wrong=True, retry_fixes=True, upper_fixes=False):
        self.first_wrong, self.retry_fixes, self.upper_fixes = first_wrong, retry_fixes, upper_fixes
        self.prompts = []
        self.calls = {}

    def generate(self, model, prompt, schema=None, temperature=0.0):
        self.calls[model] = self.calls.get(model, 0) + 1
        if "재해입원특약" in prompt.split("본문")[0]:
            return GOOD["재해입원"]
        self.prompts.append((model, prompt))
        if model == config.MODEL_SUMMARY:
            return GOOD["암진단"] if self.upper_fixes else WRONG
        wrong = self.first_wrong if model == config.MODEL_EXTRACT else not self.retry_fixes
        return WRONG if wrong else GOOD["암진단"]

    def decide(self, model, input_text, questions):
        self.calls[model] = self.calls.get(model, 0) + 1
        out = {}
        for key, q in questions.items():
            if q["type"] == "choice":      # 암 줄은 보장개시일 이후, 다른 줄은 보험기간 중으로 시작한다
                after = "암진단" in q["instructions"]
                out[key] = Answer(V.AFTER_START if after else V.FROM_DAY_ONE, None,
                                  {V.AFTER_START: 0.96 if after else 0.04, V.FROM_DAY_ONE: 0.04 if after else 0.96})
                continue
            bad = "3,000만원" in q["instructions"]
            out[key] = Answer(not bad, None, {"true": 0.05 if bad else 0.97, "false": 0.95 if bad else 0.03})
        return out


def run(g):
    return P.run_summary(g, pages_from_text(TEXT), ["V1", "V2"], datetime(2026, 11, 18, 14, 0, tzinfo=KST),
                         product_renewal_years=20)


def test_wrong_value_is_caught_reextracted_and_logged():
    g = FakeGemini()
    r = run(g)
    assert r.stats == {"조각": 2, "처리한 조각": 2, "급부": 2, "확정": 2, "검토": 0, "재추출한 조각": 1, "상위 모델 사용": 0}
    assert g.calls[config.MODEL_EXTRACT] == 2 and g.calls[config.MODEL_EXTRACT_ALT] == 1
    amounts = sorted({row["기준지급금액만원"] for row in r.benefits})
    assert amounts == [2, 1000]                      # 틀린 3000은 남지 않는다
    steps = [(l["작업단계"], l["결과"]) for l in r.logs]
    assert ("코드대조", "보류") in steps and ("재추출", "통과") in steps and ("판정", "통과") in steps
    retry = next(l for l in r.logs if l["작업단계"] == "재추출")
    assert "0.05 → 0.96" in retry["사유"] or "0.05 → 0.97" in retry["사유"] and retry["호출모델"] == config.MODEL_EXTRACT_ALT
    assert check_rows("sys_작업로그", r.logs) == {}


def test_rows_are_repeated_for_each_variant_sharing_the_document():
    r = run(FakeGemini(first_wrong=False))
    assert len(r.riders) == 4 and len(r.benefits) == 4 and r.stats["재추출한 조각"] == 0
    assert check_rows("sys_특약", r.riders) == {} and check_rows("sys_급부", r.benefits) == {}
    assert {row["종형ID"] for row in r.riders} == {"V1", "V2"}
    rider_ids = {row["특약ID"] for row in r.riders}
    assert {row["특약ID"] for row in r.benefits} == rider_ids


def test_value_still_wrong_after_retry_goes_to_human_review():
    r = run(FakeGemini(retry_fixes=False))
    assert r.stats["검토"] == 1 and r.stats["확정"] == 1
    review = [l for l in r.logs if l["작업단계"] == "사람검토이관"]
    assert len(review) == 1 and "기준지급금액만원" in review[0]["사유"] and "10쪽" in review[0]["사유"]
    assert ("재추출", "반려") in [(l["작업단계"], l["결과"]) for l in r.logs]


def test_upper_model_is_the_last_resort_and_gets_the_earlier_problems():
    g = FakeGemini(retry_fixes=False, upper_fixes=True)
    r = run(g)
    assert r.stats["확정"] == 2 and r.stats["상위 모델 사용"] == 1
    assert g.calls[config.MODEL_SUMMARY] == 1
    upper_prompt = [p for m, p in g.prompts if m == config.MODEL_SUMMARY][0]
    assert "앞선 추출에서 드러난 문제" in upper_prompt and "원문에 없는 금액이나 기간" in upper_prompt
    assert sorted({row["기준지급금액만원"] for row in r.benefits}) == [2, 1000]


def test_upper_model_budget_is_respected(monkeypatch):
    monkeypatch.setattr(config, "EXTRACT_ESCALATIONS_PER_RUN", 0)
    g = FakeGemini(retry_fixes=False, upper_fixes=True)
    r = run(g)
    assert config.MODEL_SUMMARY not in g.calls and r.stats["검토"] == 1


def test_thresholds_can_come_from_the_sheet():
    rows = [{"기준키": "추출검증_통과", "기준분류": "판정구간", "수치값": 0.99}]
    assert P.thresholds_from(rows)["추출검증_통과"] == 0.99
    assert P.thresholds_from([])["추출검증_재추출"] == 0.40


def test_questions_split_what_code_and_model_check():
    from postlife.extract import benefits as B
    from postlife.extract import verify as V
    from postlife.extract.segment import Block

    note = "암보장개시일은 계약일부터 그 날을 포함하여 90일이 지난날의 다음날"
    b = B.Benefit("암진단보험금", "암", 1000, 90, "최초 1회에 한함", "주급부", "", reduced_months=12, reduced_amount=500)
    d = V.checks(b, note)
    assert "그 지급액은 1,000만원이다" in d["기준지급금액만원"][0]["instructions"]
    assert "12개월 미만에는 500만원을 지급한다" in d["감액지급률1"][0]["instructions"]        # 지급액과 감액은 따로 묻는다
    assert d["면책기간일수"][0]["type"] == "choice" and d["면책기간일수"][1] == V.AFTER_START
    assert "지급횟수제한" in d            # 원문에 그 글자가 없으니 판정에 묻는다
    assert "지급횟수제한" not in V.checks(b, note + " 최초 1회에 한함")
    none = B.Benefit("재해입원보험금", "", 2, 0, "", "주급부", "")
    # 원문에 보장개시일 문구가 없으면 면책은 묻지 않는다
    assert list(V.checks(none, "재해로 입원하였을 때")) == ["기준지급금액만원", "감액지급률1"]
    assert "나뉘어 있지 않다" in V.checks(none, "재해로 입원하였을 때")["감액지급률1"][0]["instructions"]
    # 문구가 있는데 0으로 적었으면 "보험기간 중"이 골라져야 맞다
    assert V.checks(none, "암보장개시일 이후에")["면책기간일수"][1] == V.FROM_DAY_ONE
    ex = B.Extraction(Block("t", "암보장개시일 이후에", 1, 1), 1000, [none], "m")

    class G:
        def decide(self, model, text, qs):
            return {k: (Answer(V.FROM_DAY_ONE, None, {V.AFTER_START: 0.2, V.FROM_DAY_ONE: 0.8}) if q["type"] == "choice"
                        else Answer(True, None, {"true": 0.9, "false": 0.1})) for k, q in qs.items()}

    assert V.judge(G(), ex, "d")["재해입원보험금"] == {"기준지급금액만원": 0.9, "감액지급률1": 0.9, "면책기간일수": 0.8}


def test_job_writes_only_the_reextracted_variants_and_appends_logs():
    import json
    from pathlib import Path

    from postlife.extract import job
    from postlife.schema import TABS
    from postlife.sheets_io import MemoryBackend, SheetStore

    targets = json.loads((Path(__file__).resolve().parents[1] / "data/targets/epost.json").read_text(encoding="utf-8"))
    index = [{"기관": "EPOST", "상품코드": code, "상품명": f"무배당 우체국간편한건강보험(20년갱신형) 2606 {name}",
              "판매시작일": "2026-06-17", "판매종료일": None, "문서": "상품요약서", "해시": "h1", "저장이름": "yoyak", "쪽수": 40}
             for code, name in (("P500129", "1종(간편가입315)"), ("P500130", "2종(간편가입325)"))]
    store = SheetStore(MemoryBackend())
    for name, tab in TABS.items():
        store.write_tab(name, [])
    other = {"종형ID": "HANWHA_X_1", "특약ID": "R_other", "특약계보키": "k", "담보구분": "선택특약", "원시특약명": "다른 회사 특약",
             "갱신여부": False, "갱신주기년": None, "최소가입금액만원": None, "최대가입금액만원": None, "합산한도기준키": None}
    store.write_tab("sys_특약", [other])

    now = datetime(2026, 11, 18, 15, 0, tzinfo=KST)
    report = job.run(FakeGemini(), store, targets, index, lambda stem: TEXT if stem == "yoyak" else None, now,
                     read_thresholds=False)
    assert report.written and report.errors == {} and len(report.done) == 2
    data = store.read()
    assert len(data["sys_상품종형"]) == 2 and {r["간편고지약칭"] for r in data["sys_상품종형"]} == {"3.1.5", "3.2.5"}
    assert len(data["sys_특약"]) == 1 + 2 * 2 and any(r["특약ID"] == "R_other" for r in data["sys_특약"])
    assert len(data["sys_급부"]) == 2 * 2 and len(data["sys_작업로그"]) == len(report.logs) > 0
    assert any("공시 수집 결과에 없음" in n for n in report.notes)       # 설정에는 있으나 받지 못한 상품

    # 한 번 더 돌려도 행이 늘지 않는다 (같은 ID로 바꿔 쓴다)
    job.run(FakeGemini(), store, targets, index, lambda stem: TEXT, now, read_thresholds=False)
    again = store.read()
    assert len(again["sys_급부"]) == 4 and len(again["sys_특약"]) == 5

    # 시험 실행은 시트를 건드리지 않는다
    dry = job.run(FakeGemini(), SheetStore(MemoryBackend()), targets, index, lambda stem: TEXT, now, dry_run=True,
                  read_thresholds=False)
    assert not dry.written and len(dry.rows["sys_급부"]) == 4


def test_retry_is_judged_by_likely_wrong_rows_before_rows_to_review():
    from postlife.extract import benefits as B
    from postlife.extract.segment import Block

    block = Block("t", "x", 1, 1)
    rows = [B.Benefit("생활자금", t, 100, 0, "", "주급부", "") for t in ("100%", "80%", "50%")]
    t = P.DEFAULT_THRESHOLDS
    # 맞게 뽑았지만 세 줄 모두 통과 기준에 조금 못 미친 결과
    right = P._Try(B.Extraction(block, 0, rows, "m3", []), {r.label: {"기준지급금액만원": 0.6} for r in rows}, {})
    # 한 줄을 빠뜨리고 한 줄의 확률이 바닥인 결과
    wrong = P._Try(B.Extraction(block, 0, rows[:2], "m2", []),
                   {rows[0].label: {"기준지급금액만원": 0.71}, rows[1].label: {"기준지급금액만원": 0.07}}, {})
    assert right.score(t) < wrong.score(t)
    # 형식 문제가 있던 결과보다는 문제 없는 쪽이 낫다
    flawed = P._Try(B.Extraction(block, 0, rows, "m1", [f"감액 기간과 감액 금액 중 하나만 적힘: {rows[0].label}"]),
                    {r.label: {"기준지급금액만원": 0.9} for r in rows}, {})
    assert right.score(t) < flawed.score(t)
