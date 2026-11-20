from datetime import datetime

from postlife import config
from postlife.extract import pipeline as P
from postlife.extract import verify as V
from postlife.extract.segment import pages_from_text
from postlife.gemini import Answer, GeminiError
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
    assert r.stats == {"조각": 2, "처리한 조각": 2, "급부": 2, "확정": 2, "검토": 0, "제외": 0, "재추출한 조각": 1, "상위 모델 사용": 0}
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


def test_value_still_wrong_after_retry_is_left_out_and_handed_to_a_person():
    r = run(FakeGemini(retry_fixes=False))
    assert r.stats["제외"] == 1 and r.stats["확정"] == 1 and r.stats["검토"] == 0
    assert sorted({row["기준지급금액만원"] for row in r.benefits}) == [2]      # 틀린 3,000만원은 시트에 가지 않는다
    assert len(r.riders) == 4                                              # 특약 행은 남는다
    review = [l for l in r.logs if l["작업단계"] == "사람검토이관"]
    # 요약서를 함께 쓰는 종형마다 그 종형의 급부ID로 남긴다
    assert sorted(l["대상행ID"].split("_T")[0] for l in review) == ["V1", "V2"]
    assert all("시트에 쓰지 않음" in l["사유"] and "10쪽" in l["사유"] for l in review)
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
    assert config.MODEL_SUMMARY not in g.calls and r.stats["제외"] == 1


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


def test_row_with_contradictory_values_is_left_out():
    class Broken(FakeGemini):
        def generate(self, model, prompt, schema=None, temperature=0.0):
            if "재해입원특약" in prompt.split("본문")[0]:
                return GOOD["재해입원"]
            # 어느 모델로 뽑아도 감액 금액이 지급액과 같다
            return {"base_amount": "1,000만원", "benefits": [dict(GOOD["암진단"]["benefits"][0], reduced_amount="1,000만원")]}

    r = run(Broken())
    assert r.stats["제외"] == 1 and sorted({row["기준지급금액만원"] for row in r.benefits}) == [2]
    assert check_rows("sys_급부", r.benefits) == {}
    assert any("앞뒤가 맞지 않아" in str(l["사유"]) for l in r.logs)


def test_limit_check_tolerates_text_from_other_columns():
    from postlife.extract import benefits as B

    flat = B.squash("입원하였을 때(1일 이상 입원\n보험계약일부터\n2만원\n일수 1일당, 120일 한도)")
    assert B.limit_in_source("1일 이상 입원일수 1일당, 120일 한도", flat)
    assert not B.limit_in_source("4일 이상 입원일수 1일당, 120일 한도", flat)


def test_problem_of_a_longer_name_does_not_exclude_the_shorter_name():
    from postlife.extract import benefits as B
    from postlife.extract.segment import Block

    # 급부 이름이 다른 급부 이름의 일부인 경우. 문제는 "암진단보험금(1종)" 줄에만 있다
    plain, typed = B.Benefit("암진단보험금", "", 1000, 0, "", "주급부", ""), B.Benefit("암진단보험금", "1종", 1000, 0, "", "주급부", "")
    t = P._Try(B.Extraction(Block("t", "x", 1, 1), 0, [plain, typed], "m", [f"감액 금액이 지급액보다 작지 않음: {typed.label}"]),
               {b.label: {"기준지급금액만원": 0.9} for b in (plain, typed)}, {})
    assert t.flawed(typed.label) and not t.flawed(plain.label)
    assert t.broken(plain.label) == [] and t.score(P.DEFAULT_THRESHOLDS)[0] == 1
    # 이름이 같은 줄이 두 번 나온 문제는 그 이름의 줄에 그대로 걸린다
    twice = P._Try(B.Extraction(Block("t", "x", 1, 1), 0, [plain, plain], "m", [f"같은 이름의 급부가 두 번 나옴: {plain.label}"]), {}, {})
    assert twice.flawed(plain.label)

    class Mixed(FakeGemini):
        def generate(self, model, prompt, schema=None, temperature=0.0):
            if "재해입원특약" in prompt.split("본문")[0]:
                return GOOD["재해입원"]
            good = GOOD["암진단"]["benefits"][0]
            return {"base_amount": "1,000만원", "benefits": [good, dict(good, target="1종", reduced_amount="1,000만원")]}

    r = run(Mixed())
    cancer = next(b for b in r.blocks if "암진단" in b.extraction.block.title)
    assert cancer.status == {"암진단보험금": "확정", "암진단보험금(1종)": "제외"}
    assert sorted({row["원시급부명"] for row in r.benefits}) == ["암진단보험금", "재해입원보험금"]


def test_problem_of_an_item_that_made_no_row_does_not_exclude_a_good_row():
    from postlife.extract import benefits as B
    from postlife.extract.segment import Block

    # 줄을 만들지 못한 항목("덤사망보험금", 금액 칸에 금액이 없음)의 문제 문구에 맞게 뽑은 급부의 이름("사망보험금")이 글자로 들어 있다
    good = B.Benefit("사망보험금", "", 2000, 0, "", "주급부", "")
    problem = "이름이나 금액이 비어 있음: {'name': '덤사망보험금', 'amount': '덤보험금'}"
    t = P._Try(B.Extraction(Block("t", "x", 1, 1), 0, [good], "m", [problem]), {good.label: {"기준지급금액만원": 0.9}}, {})
    assert not t.flawed(good.label) and t.broken(good.label) == []
    assert t.score(P.DEFAULT_THRESHOLDS)[0] == 1      # 줄에 묶이지 않은 문제로 한 건 센다 (다시 뽑아 볼 이유는 된다)

    class Extra(FakeGemini):
        def generate(self, model, prompt, schema=None, temperature=0.0):
            if "재해입원특약" in prompt.split("본문")[0]:
                return GOOD["재해입원"]
            first = GOOD["암진단"]["benefits"][0]
            return {"base_amount": "1,000만원", "benefits": [first, dict(first, name="덤" + first["name"], amount="덤보험금")]}

    r = run(Extra())
    cancer = next(b for b in r.blocks if "암진단" in b.extraction.block.title)
    # 금액을 읽지 못한 항목은 시트에 쓰지 않는 제외 항목으로 남는다(다시 뽑을 때 그 급부의 이전 줄을 지킨다)
    assert cancer.status == {"암진단보험금": "확정", "덤암진단보험금": "제외"}
    assert [b.label for b in cancer.extraction.unread] == ["덤암진단보험금"]
    assert {row["원시급부명"] for row in r.benefits} == {"암진단보험금", "재해입원보험금"}


def test_retry_with_rows_replaces_an_empty_first_result():
    from postlife.extract import benefits as B
    from postlife.extract.segment import Block

    block, t = Block("t", "x", 1, 1), P.DEFAULT_THRESHOLDS
    rows = [B.Benefit(f"급부{i}", "", 100, 0, "", "주급부", "") for i in range(5)]
    empty = P._Try(B.Extraction(block, 0, [], "m1", []), {}, {})
    found = P._Try(B.Extraction(block, 0, rows, "m2", []),
                   {r.label: {"기준지급금액만원": 0.9 if i else 0.7} for i, r in enumerate(rows)}, {})
    assert not found.score(t) < empty.score(t)          # 점수만 보면 한 줄도 못 뽑은 쪽이 낫게 나온다
    assert found.beats(empty, t) and not empty.beats(found, t) and not empty.beats(empty, t)

    class EmptyFirst(FakeGemini):
        def generate(self, model, prompt, schema=None, temperature=0.0):
            if model == config.MODEL_EXTRACT and "암진단특약" in prompt.split("본문")[0]:
                return {"base_amount": "1,000만원", "benefits": []}
            return super().generate(model, prompt, schema, temperature)

    r = run(EmptyFirst(first_wrong=False))
    assert r.stats["확정"] == 2 and sorted({row["기준지급금액만원"] for row in r.benefits}) == [2, 1000]
    retry = next(l for l in r.logs if l["작업단계"] == "재추출")
    assert (retry["결과"], retry["변경전값"], retry["변경후값"]) == ("통과", "급부 0건", "급부 1건")


def test_result_without_a_verdict_does_not_replace_a_judged_one():
    from postlife.extract import benefits as B
    from postlife.extract.segment import Block
    from postlife.gemini import GeminiError

    block, t = Block("t", "x", 1, 1), P.DEFAULT_THRESHOLDS
    rows = [B.Benefit(f"급부{i}", "", 100, 0, "", "주급부", "") for i in range(3)]
    judged = P._Try(B.Extraction(block, 0, rows, "m1", []), {r.label: {"기준지급금액만원": 0.9 if i else 0.1} for i, r in enumerate(rows)}, {})
    unjudged = P._Try(B.Extraction(block, 0, rows, "m2", []), {}, {})
    assert unjudged.score(t) < judged.score(t)          # 점수만 보면 판정을 못 받은 쪽이 낫게 나온다
    assert not unjudged.beats(judged, t) and judged.beats(unjudged, t)
    assert not unjudged.beats(unjudged, t)              # 둘 다 판정이 없으면 점수로 견준다

    class JudgeFailsOnRetry(FakeGemini):
        """보조 모델로 다시 뽑은 결과를 판정할 때만 판정 모델이 한도에 걸린다."""
        last = None

        def generate(self, model, prompt, schema=None, temperature=0.0):
            if "암진단특약" in prompt.split("본문")[0]:
                self.last = model
            return super().generate(model, prompt, schema, temperature)

        def decide(self, model, input_text, questions):
            if "암진단특약" in input_text and self.last == config.MODEL_EXTRACT_ALT:
                raise GeminiError(429, "한도")
            return super().decide(model, input_text, questions)

    # 판정을 받지 못한 결과가 채택되면 상위 모델을 부르지 않고 끝난다. 판정을 받은 앞선 결과를 두고 상위 모델까지 간다
    g = JudgeFailsOnRetry(upper_fixes=True)
    r = run(g)
    assert g.calls[config.MODEL_SUMMARY] == 1 and r.stats["확정"] == 2 and r.stats["상위 모델 사용"] == 1
    kept = [l for l in r.logs if l["작업단계"] == "재추출" and l["호출모델"] == config.MODEL_EXTRACT_ALT]
    assert kept[0]["결과"] == "반려"

    class JudgeAlwaysFails(FakeGemini):
        def decide(self, model, input_text, questions):
            raise GeminiError(429, "한도")

    # 판정을 한 번도 받지 못했으면 뽑은 값은 버리지 않고 사람 검토로 넘긴다
    r = run(JudgeAlwaysFails(first_wrong=False))
    assert r.stats["검토"] == 2 and r.stats["제외"] == 0 and len(r.benefits) == 4


def test_row_split_by_target_is_logged_and_its_start_is_not_judged():
    # 지어낸 문구. 표적 치료자금은 "보장개시일(암은 암보장개시일) 이후"로 암만 90일, 수술자금은 모든 대상이 암보장개시일 뒤
    text = """
===== 30쪽 =====
② 보험금 지급사유
■ 무배당 가상항암치료특약 2701
(특약보험가입금액 1,000만원 기준)
지급구분 지급사유 지급금액
보험기간 중 보장개시일(암은 암보장개시일) 이후에
‘암’ 또는 ‘갑상선암’으로 진단 확정되고 1년미만 10만원
가상표적 그 치료를 목적으로 가상표적치료를 받았을 때
치료자금 (1회당) 1년이상 20만원
보험기간 중 암보장개시일 이후에 암으로 수술을 받았을 때 30만원
가상수술자금 (수술 1회당)
주) 1. 암보장개시일은 계약일부터 그 날을 포함하여 90일이 지난날의 다음날로 합니다.
③ 일반적 보험금 지급제한 사유
"""
    rows = {"base_amount": "1,000만원", "benefits": [
        {"name": "가상표적치료자금", "target": "암·갑상선암", "amount": "20만원", "reduced_period": "1년미만", "reduced_amount": "10만원",
         "start_condition": "", "limit": "1회당", "role": "주급부", "quote": "20만원"},
        {"name": "가상수술자금", "target": "암", "amount": "30만원", "start_condition": "암보장개시일", "limit": "수술 1회당",
         "role": "주급부", "quote": "30만원"}]}

    class Split(FakeGemini):
        def __init__(self):
            super().__init__()
            self.asked = []

        def generate(self, model, prompt, schema=None, temperature=0.0):
            self.calls[model] = self.calls.get(model, 0) + 1
            return rows

        def decide(self, model, input_text, questions):
            self.asked += [q["instructions"] for q in questions.values() if q["type"] == "choice"]
            return {k: (Answer(V.AFTER_START, None, {V.AFTER_START: 0.95, V.FROM_DAY_ONE: 0.05}) if q["type"] == "choice"
                        else Answer(True, None, {"true": 0.95, "false": 0.05})) for k, q in questions.items()}

    g = Split()
    r = P.run_summary(g, pages_from_text(text), ["V1"], datetime(2026, 11, 20, 9, 0, tzinfo=KST))
    assert check_rows("sys_급부", r.benefits) == {} and check_rows("sys_작업로그", r.logs) == {}
    assert sorted((row["원시급부명"], row["면책기간일수"]) for row in r.benefits) == [
        ("가상수술자금(암)", 90), ("가상표적치료자금(갑상선암)", 0), ("가상표적치료자금(암)", 90)]
    assert r.stats["확정"] == 3 and r.stats["재추출한 조각"] == 0 and g.calls == {config.MODEL_EXTRACT: 1}     # 다시 뽑지 않는다
    # 나눈 줄의 면책은 판정에 묻지 않는다. 나누지 않은 수술자금 줄만 묻는다
    assert len(g.asked) == 1 and "가상수술자금" in g.asked[0]
    split = [l for l in r.logs if l["작업단계"] == "코드대조" and l["변경전값"] == "가상표적치료자금(암·갑상선암)"]
    assert sorted(l["변경후값"] for l in split) == ["가상표적치료자금(갑상선암)", "가상표적치료자금(암)"]
    assert all("대상별로 나눔" in l["사유"] and l["대상열"] == "면책기간일수" for l in split)


SCOPED = """
===== 12쪽 =====
② 보험금 지급사유
■ 무배당 암진단특약(20년갱신형) 2606
[간편가입형]
(특약보험가입금액 1,000만원 기준) 간편 표
암진단 보험금 최초 1회에 한함 1년미만 500만원 1년이상 1,000만원
[일반가입형]
(특약보험가입금액 1,000만원 기준) 일반 표
암진단 보험금 최초 1회에 한함 1년미만 500만원 1년이상 1,000만원
주) 암보장개시일은 계약일부터 그 날을 포함하여 90일이 지난날의 다음날
③ 일반적 보험금 지급제한 사유
"""
SCOPED_NAMES = {"V1": "간편가입형(1년)", "V2": "간편가입형(5년)", "V3": "일반가입형"}


def test_variants_of_each_part_and_unprocessed_parts_are_kept_in_the_result():
    class FailsOnPlain(FakeGemini):
        def generate(self, model, prompt, schema=None, temperature=0.0):
            if "일반 표" in prompt:
                raise GeminiError(503, "high demand")
            return GOOD["암진단"]

    r = P.run_summary(FailsOnPlain(), pages_from_text(SCOPED), list(SCOPED_NAMES), datetime(2026, 11, 20, 9, 0, tzinfo=KST),
                      variant_names=SCOPED_NAMES)
    assert [b.variants for b in r.blocks] == [["V1", "V2"]]
    assert [(u.variants, u.reason, u.block.first_page) for u in r.unprocessed] == [(["V3"], "호출 실패", 12)]
    assert r.stats["조각"] == 2 and r.stats["처리한 조각"] == 1
    # 판정 기록은 그 부분을 실은 종형마다 남는다
    judged = sorted(l["대상행ID"].split("_T")[0] for l in r.logs if l["작업단계"] == "판정")
    assert judged == ["V1", "V2"]


def test_empty_result_is_unprocessed_unless_every_attempt_agrees_without_problems():
    def empty_then(error=None, problem=False):
        class G(FakeGemini):
            def generate(self, model, prompt, schema=None, temperature=0.0):
                if "재해입원특약" in prompt.split("본문")[0]:
                    return GOOD["재해입원"]
                if model != config.MODEL_EXTRACT and error:
                    raise error
                return {"base_amount": "1,000만원", "benefits": [{"name": "암진단보험금", "amount": "금액 미상"}] if problem else []}
        return G()

    for g, reason in ((empty_then(GeminiError(503, "high demand")), "급부 0건"), (empty_then(problem=True), "급부 0건"),
                      (empty_then(), None)):
        r = run(g)
        cancer = [u for u in r.unprocessed if "암진단" in u.block.title]
        if reason:
            assert [u.reason for u in cancer] == [reason] and len(r.riders) == 2       # 그 특약 행도 내지 않는다
            assert any(l["작업단계"] == "추출" and "급부 0건으로 끝났고" in str(l["사유"]) for l in r.logs)
        else:
            assert not cancer and len(r.riders) == 4                                    # 모든 시도가 문제 없이 빈 목록이면 급부가 없는 특약이다


def test_rider_split_over_several_blocks_gets_one_rider_row():
    text = TEXT.replace("③ 일반적", "■ 무배당 암진단특약(20년갱신형) 2606\n(특약보험가입금액 1,000만원 기준)\n"
                        "암진단 보험금 최초 1회에 한함 1년미만 500만원 1년이상 1,000만원\n③ 일반적")
    r = P.run_summary(FakeGemini(first_wrong=False), pages_from_text(text), ["V1", "V2"],
                      datetime(2026, 11, 18, 14, 0, tzinfo=KST), product_renewal_years=20)
    assert r.stats["조각"] == 3 and len(r.blocks) == 3
    assert len(r.riders) == 4 and len({row["특약ID"] for row in r.riders}) == 4      # 특약 2개 × 종형 2개
    assert check_rows("sys_특약", r.riders) == {}
