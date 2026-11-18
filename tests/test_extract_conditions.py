from datetime import datetime

from postlife import config
from postlife.extract import conditions as C
from postlife.extract import conditions_run as R
from postlife.extract import pipeline as P
from postlife.extract.segment import pages_from_text
from postlife.gemini import Answer
from postlife.snapshot import KST
from postlife.validate import check_rows

METHOD = """
===== 2쪽 =====
1. 보험상품의 명칭
가. 무배당 우체국간편한건강보험(20년갱신형) 2606
2. 가입나이, 보험기간, 보험료 납입기간 및 보험료 납입주기
가. 무배당 우체국간편한건강보험(20년갱신형) 2606, 무배당 암진단특약(20년갱신형) 2606
- 1종(간편가입315)
최초계약 20~80세 20년만기(갱신형)
40~80세 20년만기(갱신형) 전기납 월 납
갱신계약
81~99세 100세만기
- 4종(일반가입)
최초계약 만15~80세 20년만기(갱신형) 전기납 월 납
나. 무배당 요양병원암입원특약(20년갱신형) 2606
가입나이 남자 여자
최초계약 20~80세 23~80세 20년만기(갱신형) 전기납
===== 3쪽 =====
3. 보험가입금액의 한도
가. 주계약
65세 이하 1,000만원~4,000만원 500만원 단위
66세 이상 1,000만원~2,000만원
나. 무배당 암진단특약(20년갱신형) 2606 : 500만원~4,000만원
※ 단, 피보험자가 가입 당시 71세 이상인 경우 500만원(고정)
4. 특약부가에 관한 사항
가. 무배당 암진단특약(20년갱신형) 2606(선택), 무배당 요양병원암입원특약(20년갱신형) 2606(선택)
나. 무배당 요양병원암입원특약(20년갱신형) 2606은 무배당 암진단특약(20년갱신형) 2606을 가입하는 경우에 한하여 부가할 수 있습니다.
5. 배당에 관한 사항
배당금이 없습니다.
"""
SUMMARY = """
===== 3쪽 =====
② 보험가입 자격요건
o 특약
- 무배당 암진단특약(20년갱신형) 2606
주) 1. 특약은 주계약 보험가입금액 이내에서 가입 가능
■ 건강진단 여부 : 전건 무진단
② 보험금 지급사유
"""
MAIN, CANCER, NURSING = "무배당 우체국간편한건강보험(20년갱신형) 2606", "무배당 암진단특약(20년갱신형) 2606", "무배당 요양병원암입원특약(20년갱신형) 2606"
AGES = {"items": [
    {"subjects": [MAIN, CANCER], "variant_scope": "- 1종(간편가입315)", "contract": "최초계약", "sex": "구분없음",
     "age": "20~80세", "term": "20년만기(갱신형)", "payment": "전기납"},
    {"subjects": [MAIN, CANCER], "variant_scope": "- 1종(간편가입315)", "contract": "갱신계약", "sex": "구분없음",
     "age": "40~80세", "term": "20년만기(갱신형)", "payment": "전기납"},
    {"subjects": [MAIN, CANCER], "variant_scope": "- 4종(일반가입)", "contract": "최초계약", "sex": "구분없음",
     "age": "만15~80세", "term": "20년만기(갱신형)", "payment": "전기납"},
    {"subjects": [NURSING], "variant_scope": "", "contract": "최초계약", "sex": "남자", "age": "20~80세",
     "term": "20년만기(갱신형)", "payment": "전기납"},
    {"subjects": [NURSING], "variant_scope": "", "contract": "최초계약", "sex": "여자", "age": "23~80세",
     "term": "20년만기(갱신형)", "payment": "전기납"},
]}
LIMITS = {"items": [
    {"subjects": ["주계약"], "age": "65세 이하", "min": "1,000만원", "max": "4,000만원", "unit": "500만원 단위"},
    {"subjects": ["주계약"], "age": "66세 이상", "min": "1,000만원", "max": "2,000만원", "unit": ""},
    {"subjects": [CANCER], "age": "", "min": "500만원", "max": "4,000만원", "unit": ""},
    {"subjects": [CANCER], "age": "71세 이상", "min": "500만원", "max": "500만원", "unit": ""},
]}
RULES = {"items": [{"base": CANCER, "targets": [NURSING], "kind": "선행가입", "value": "",
                    "quote": "무배당 요양병원암입원특약(20년갱신형) 2606은 무배당 암진단특약(20년갱신형) 2606을 가입하는 경우에 한하여 부가"}]}
LINK = {"items": [{"base": "주계약", "targets": [CANCER], "kind": "최대연동", "value": "주계약 보험가입금액 이내",
                   "quote": "특약은 주계약 보험가입금액 이내에서 가입 가능"}]}


def riders(variant):
    def row(name, kind):
        from postlife import ids
        return {"특약ID": ids.rider_id(variant, name), "종형ID": variant, "특약계보키": ids.rider_lineage_key(name),
                "담보구분": kind, "원시특약명": name}
    return [row("주계약", "주계약"), row(CANCER, "선택특약"), row(NURSING, "선택특약")]


class FakeGemini:
    def __init__(self, low=None):
        self.low, self.calls = low, {}

    def generate(self, model, prompt, schema=None, temperature=0.0):
        self.calls[model] = self.calls.get(model, 0) + 1
        if '"가입나이, 보험기간' in prompt:
            return AGES
        if '"보험가입금액의 한도" 절' in prompt:
            return LIMITS
        return LINK if "자격요건" in prompt else RULES

    def decide(self, model, text, questions):
        return {k: Answer(True, None, {"true": 0.5 if self.low and self.low in q["instructions"] else 0.95, "false": 0.05})
                for k, q in questions.items()}


def targets():
    rows = riders("V1") + riders("V4")
    return [C.target_of("V1", "1종(간편가입315)", rows), C.target_of("V4", "4종(일반가입)", rows)], rows


def run(g):
    t, _ = targets()
    return R.run(g, pages_from_text(METHOD), pages_from_text(SUMMARY), t, datetime(2026, 11, 18, 17, 0, tzinfo=KST),
                 dict(P.DEFAULT_THRESHOLDS))


def test_sections_are_cut_from_the_method_document():
    s = C.method_sections(pages_from_text(METHOD))
    assert set(s) == {"가입나이", "가입한도", "특약부가"}
    assert s["가입나이"].text.startswith("2. 가입나이") and "3. 보험가입금액" not in s["가입나이"].text
    assert (s["가입한도"].first_page, s["특약부가"].last_page) == (3, 3) and "배당금" not in s["특약부가"].text
    e = C.eligibility_section(pages_from_text(SUMMARY))
    assert "이내에서 가입 가능" in e.text and "건강진단" not in e.text


def test_text_is_turned_into_numbers_by_code():
    assert C.parse_age_range("만15~50세") == (15, 50) and C.parse_age_range("만25~(주계약 만기나이-1)세") is None
    assert C.parse_age_band("65세 이하") == (0, 65) and C.parse_age_band("66세~70세") == (66, 70)
    assert C.parse_age_band("61세 이상") == (61, C.MAX_AGE) and C.parse_age_band("") is None
    assert C.expand("90,95,100세만기") == ["90세만기", "95세만기", "100세만기"] and C.expand("전기납") == ["전기납"]
    assert C.is_main(MAIN) and C.is_main("주계약") and not C.is_main(CANCER)


def test_rows_split_ages_where_the_limit_changes():
    r = run(FakeGemini())
    assert check_rows("sys_가입조건", r.conditions) == {} and check_rows("sys_결합제약", r.constraints) == {}
    v1 = [c for c in r.conditions if c["종형ID"] == "V1"]
    common = sorted((c["최저가입나이"], c["최고가입나이"], c["구간최대가입금액만원"]) for c in v1 if c["특약ID"] is None)
    assert common == [(20, 65, 4000), (66, 80, 2000)]                 # 주계약: 66세부터 한도가 준다
    cancer = sorted((c["최저가입나이"], c["최고가입나이"], c["구간최대가입금액만원"]) for c in v1 if c["특약ID"] and "성별" in c
                    and c["성별"] is None)
    assert cancer == [(20, 70, 4000), (71, 80, 500)]                  # 기본 한도와 "71세 이상" 단서
    sexes = {(c["성별"], c["최저가입나이"]) for c in v1 if c["성별"]}
    assert sexes == {("M", 20), ("F", 23)}                            # 성별로 나이가 다른 특약
    v4 = [c for c in r.conditions if c["종형ID"] == "V4" and c["특약ID"] is None]
    assert min(c["최저가입나이"] for c in v4) == 15                    # 종 구분에 맞는 표만 쓴다
    assert not any(c["최저가입나이"] == 40 for c in r.conditions)      # 갱신계약 나이는 쓰지 않는다
    assert len({c["조건행ID"] for c in r.conditions}) == len(r.conditions)


def test_constraints_and_amount_ranges():
    r = run(FakeGemini())
    kinds = sorted((c["제약유형"], c["제약수치"], c["제약단위"]) for c in r.constraints if c["종형ID"] == "V1")
    assert kinds == [("선행가입", None, None), ("최대연동", 1.0, "비율")]
    link = next(c for c in r.constraints if c["제약유형"] == "최대연동" and c["종형ID"] == "V1")
    t, _ = targets()
    assert link["기준특약ID"] == t[0].main_id and "이내에서" in link["근거문구"]
    assert r.amounts[t[0].main_id] == (1000, 4000) and r.amounts[t[0].riders[next(iter(t[0].riders))]] == (500, 4000)
    assert r.stats["검토"] == 0 and r.review == []


def test_doubtful_item_goes_to_review_and_is_logged():
    g = FakeGemini(low="23~80세")
    r = run(g)
    assert r.stats["검토"] == 1 and "23~80세" in r.review[0]
    steps = [(l["작업단계"], l["결과"], l["대상탭"]) for l in r.logs]
    assert ("사람검토이관", "보류", "sys_가입조건") in steps and ("판정", "통과", "sys_결합제약") in steps
    assert len(r.conditions) > 0                                       # 검토 줄도 행은 쓰고 기록으로 표시한다


def test_code_check_flags_names_and_values_not_in_the_source():
    section = C.method_sections(pages_from_text(METHOD))["가입한도"]
    raw = {"items": [{"subjects": ["무배당 뇌출혈진단특약(20년갱신형) 2606"], "age": "65세 이하", "min": "1,000만원",
                      "max": "3,000만원", "unit": ""}]}
    ex = C.parse("가입한도", section, raw, "m")
    assert list(C.literal_problems(ex).values()) == [["묶음", "이름", "금액"]]
    # 이름과 금액이 각각 원문에 있어도 서로 다른 항목("가."와 "나.")의 것이면 잘못 묶은 것이다
    mixed = C.parse("가입한도", section, {"items": [{"subjects": [CANCER], "age": "65세 이하", "min": "1,000만원",
                                                   "max": "4,000만원", "unit": ""}]}, "m")
    assert list(C.literal_problems(mixed).values()) == [["묶음"]]
    bad = C.parse("가입한도", section, {"items": [{"subjects": ["주계약"], "age": "", "min": "4,000만원", "max": "1,000만원", "unit": ""}]}, "m")
    assert bad.items == [] and "아래쪽 한도가 위쪽보다 큼" in bad.problems[0]


def test_unknown_rider_names_are_skipped_with_a_note():
    t, _ = targets()
    ages = C.parse("가입나이", C.method_sections(pages_from_text(METHOD))["가입나이"], {"items": [
        {"subjects": ["이륜자동차 운전 및 탑승중 재해 부담보 특약 2109"], "variant_scope": "", "contract": "구분없음",
         "sex": "구분없음", "age": "20~80세", "term": "20년만기(갱신형)", "payment": "전기납"}]}, "m")
    built = C.build_rows(t, ages.items, [], [])
    assert built.conditions == [] and "뽑아 둔 특약 목록에 없어" in built.notes[0]


def test_constraint_targets_are_judged_one_by_one():
    section = C.Section("결합제약", "특약은 주계약 보험가입금액 이내에서 가입 가능", 3, 3)
    ex = C.parse("결합제약", section, {"items": [{"base": "주계약", "targets": [CANCER, NURSING], "kind": "최대연동",
                                              "value": "주계약 보험가입금액 이내", "quote": "특약은 주계약 보험가입금액 이내"}]}, "m")
    assert [i.targets for i in ex.items] == [[CANCER], [NURSING]]

    class G:
        def decide(self, model, text, questions):       # 요양병원암입원특약은 원문에 근거가 없다고 답한다
            return {k: Answer(True, None, {"true": 0.2 if "요양병원" in q["instructions"] else 0.96, "false": 0.5})
                    for k, q in questions.items()}

    probs = C.judge(G(), ex, "d")
    assert probs[ex.items[0].key]["제약"] == 0.96 and probs[ex.items[1].key]["제약"] == 0.2


def test_second_first_contract_row_is_flagged():
    section = C.method_sections(pages_from_text(METHOD))["가입나이"]
    raw = {"items": [dict(AGES["items"][0]), dict(AGES["items"][1], contract="최초계약")]}
    ex = C.parse("가입나이", section, raw, "m")
    assert any("최초계약 나이 줄이 둘 이상" in p for p in ex.problems)


def test_limits_can_differ_by_variant():
    t, _ = targets()
    section = C.Section("가입한도", "나. 무배당 암진단특약(20년갱신형) 2606\n1종(간편가입315) 500만원~3,000만원\n4종(일반가입) 500만원~4,000만원", 4, 4)
    limits = C.parse("가입한도", section, {"items": [
        {"subjects": [CANCER], "variant_scope": "1종(간편가입315)", "age": "", "min": "500만원", "max": "3,000만원", "unit": ""},
        {"subjects": [CANCER], "variant_scope": "4종(일반가입)", "age": "", "min": "500만원", "max": "4,000만원", "unit": ""}]}, "m")
    assert limits.problems == [] and len(limits.items) == 2
    ages = C.parse("가입나이", C.method_sections(pages_from_text(METHOD))["가입나이"], AGES, "m")
    built = C.build_rows(t, ages.items, limits.items, [])
    top = {c["종형ID"]: c["구간최대가입금액만원"] for c in built.conditions if c["특약ID"] and c["성별"] is None}
    assert top == {"V1": 3000, "V4": 4000}
    assert built.amounts[t[0].riders[next(iter(t[0].riders))]] == (500, 3000)


FULL_SUMMARY = SUMMARY.replace("② 보험금 지급사유", """② 보험금 지급사유
■ 주계약
(보험가입금액 1,000만원 기준)
재해사망보험금 1,000만원
■ 무배당 암진단특약(20년갱신형) 2606
(특약보험가입금액 1,000만원 기준)
암진단보험금 1,000만원
■ 무배당 요양병원암입원특약(20년갱신형) 2606
(특약보험가입금액 1,000만원 기준)
요양병원암입원보험금 1,000만원
③ 일반적 보험금 지급제한 사유""")


class BothGemini(FakeGemini):
    """급부 지시문에는 급부를, 가입조건 지시문에는 가입조건을 돌려준다."""

    def generate(self, model, prompt, schema=None, temperature=0.0):
        if "보험금 지급사유" in prompt.split("칸 채우는 법")[0]:
            self.calls[model] = self.calls.get(model, 0) + 1
            return {"base_amount": "1,000만원", "benefits": [
                {"name": "보험금", "target": "", "amount": "1,000만원", "reduced_period": "", "reduced_amount": "",
                 "reduced2_period": "", "reduced2_amount": "", "start_condition": "", "limit": "", "role": "주급부", "quote": ""}]}
        return super().generate(model, prompt, schema, temperature)


def test_job_writes_conditions_and_can_rerun_them_alone():
    import json
    from pathlib import Path

    from postlife.extract import job
    from postlife.schema import TABS
    from postlife.sheets_io import MemoryBackend, SheetStore

    targets_file = json.loads((Path(__file__).resolve().parents[1] / "data/targets/epost.json").read_text(encoding="utf-8"))
    index = [{"기관": "EPOST", "상품코드": code, "상품명": f"무배당 우체국간편한건강보험(20년갱신형) 2606 {name}",
              "판매시작일": "2026-06-17", "판매종료일": None, "문서": kind, "해시": f"h{kind}", "저장이름": stem, "쪽수": 10}
             for code, name in (("P500129", "1종(간편가입315)"), ("P500132", "4종(일반가입)"))
             for kind, stem in (("상품요약서", "yoyak"), ("사업방법서", "saeop"))]
    texts = {"yoyak": FULL_SUMMARY, "saeop": METHOD}
    store = SheetStore(MemoryBackend())
    for name in TABS:
        store.write_tab(name, [])
    now = datetime(2026, 11, 18, 17, 0, tzinfo=KST)

    report = job.run(BothGemini(), store, targets_file, index, texts.get, now, read_thresholds=False)
    assert report.written and report.errors == {} and len(report.conditions_done) == 2
    data = store.read()
    assert len(data["sys_상품종형"]) == 2 and len(data["sys_특약"]) == 6 and len(data["sys_급부"]) == 6
    assert len(data["sys_가입조건"]) == len(report.rows["sys_가입조건"]) > 0
    assert {c["제약유형"] for c in data["sys_결합제약"]} == {"선행가입", "최대연동"}
    cancer = [r for r in data["sys_특약"] if "암진단" in r["원시특약명"]]
    assert all((r["최소가입금액만원"], r["최대가입금액만원"]) == (500, 4000) for r in cancer)
    assert {l["대상탭"] for l in data["sys_작업로그"]} == {"sys_급부", "sys_가입조건", "sys_결합제약"}
    before = {tab: len(rows) for tab, rows in data.items()}

    # 가입조건만 다시 돌리면 급부는 그대로이고 가입조건 행은 같은 ID로 바뀐다
    again = job.run(BothGemini(), store, targets_file, index, texts.get, now, read_thresholds=False, parts=("가입조건",))
    assert again.written and not again.done and len(again.conditions_done) == 2
    after = store.read()
    for tab in ("sys_상품종형", "sys_특약", "sys_급부", "sys_가입조건", "sys_결합제약"):
        assert len(after[tab]) == before[tab], tab
    assert {b["급부ID"] for b in after["sys_급부"]} == {b["급부ID"] for b in data["sys_급부"]}

    # 특약이 없는 시트에서 가입조건만 돌리면 아무것도 쓰지 않는다
    empty = SheetStore(MemoryBackend())
    for name in TABS:
        empty.write_tab(name, [])
    none = job.run(BothGemini(), empty, targets_file, index, texts.get, now, read_thresholds=False, parts=("가입조건",))
    assert not none.written and any("급부부터 뽑아야" in n for n in none.notes)


def test_item_that_still_looks_wrong_is_left_out_of_the_sheet():
    class Low(FakeGemini):
        def decide(self, model, text, questions):
            return {k: Answer(True, None, {"true": 0.1 if "23~80세" in q["instructions"] else 0.95, "false": 0.5})
                    for k, q in questions.items()}

    r = run(Low())
    assert r.stats["제외"] == 1 and not any(c["성별"] == "F" for c in r.conditions)
    assert any("시트에 쓰지 않음" in line for line in r.review)
    assert any(l["작업단계"] == "판정" and l["결과"] == "반려" for l in r.logs)
