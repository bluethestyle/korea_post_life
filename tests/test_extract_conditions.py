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


# ---------- 검토 지적(9·10·14~17·19)에서 나온 경우 ----------

def test_bands_written_with_under_and_over():
    assert C.parse_age_band("61세 이상 70세 미만") == (61, 69) and C.parse_age_band("50세 초과 65세 이하") == (51, 65)
    assert C.parse_age_band("65세 미만") == (0, 64) and C.parse_age_band("70세 초과") == (71, C.MAX_AGE)
    assert C.parse_age_band("66세~70세 미만") == (66, 69)
    assert C.parse_age_band("만71세~") == (71, C.MAX_AGE) and C.parse_age_band("~만70세") == (0, 70)
    # 경계로 읽지 못한 나이가 남으면 틀린 구간을 내지 않고 None
    assert C.parse_age_band("61세 이상 (일부는 66세 이상)") is None and C.parse_age_band("61세 이상 70세") is None
    limits = C.parse("가입한도", C.Section("가입한도", "가. 주계약\n61세 이상 (일부는 66세 이상) 100만원", 3, 3), {"items": [
        {"subjects": ["주계약"], "age": "61세 이상 (일부는 66세 이상)", "min": "100만원", "max": "100만원", "unit": ""}]}, "m")
    assert not limits.items and "나이 구간을 읽을 수 없음" in limits.problems[0]


def test_age_range_without_the_age_word():
    assert C.parse_age_range("15~80") == (15, 80) and C.parse_age_range("만15~80") == (15, 80)
    assert C.parse_age_range("1~10년") is None and C.parse_age_range("2~3인실") is None      # 나이가 아닌 범위는 읽지 않는다


def test_period_lists_are_split_piece_by_piece():
    assert C.expand("10,20,30년납,전기납") == ["10년납", "20년납", "30년납", "전기납"]
    assert C.expand("10년납, 20년납") == ["10년납", "20년납"] and C.expand("종신, 90세만기") == ["종신", "90세만기"]
    assert C.expand("5,10,15,20,30년납") == ["5년납", "10년납", "15년납", "20년납", "30년납"]
    assert C.expand("10,20년만기(갱신형, 비갱신형)") == ["10년만기(갱신형,비갱신형)", "20년만기(갱신형,비갱신형)"]
    # 기간 나열로 보이지 않으면 나누지 않는다
    assert C.expand("20년만기(갱신형)") == ["20년만기(갱신형)"] and C.expand("10년만기, 최대 100세") == ["10년만기,최대100세"]
    assert C.expand("10,20") == ["10,20"] and C.expand("") == []


def test_rows_with_the_same_age_and_different_periods_are_both_kept():
    section = C.Section("가입나이", "2. 가입나이\n가. 주계약\n최초계약 20~70세 10년만기 전기납\n최초계약 20~70세 20년만기 전기납", 2, 2)
    row = {"subjects": ["주계약"], "variant_scope": "", "contract": "최초계약", "sex": "구분없음", "age": "20~70세", "payment": "전기납"}
    ex = C.parse("가입나이", section, {"items": [dict(row, term="10년만기"), dict(row, term="20년만기"), dict(row, term="20년만기")]}, "m")
    assert [i.term_text for i in ex.items] == ["10년만기", "20년만기"]
    # 앞 항목의 키는 그대로이고, 기간만 다른 뒤 항목은 키에 기간까지 적는다. 기간까지 같은 세 번째 줄만 중복이다
    assert [i.key for i in ex.items] == ["주계약||최초계약||20~70세", "주계약||최초계약||20~70세|20년만기|전기납"]
    assert ex.problems == ["같은 항목이 두 번 나옴: 주계약||최초계약||20~70세|20년만기|전기납"]
    probs = C.judge(FakeGemini(), ex, "d")
    assert set(probs) == {i.key for i in ex.items} and all(len(p) == 2 for p in probs.values())
    built = C.build_rows([C.Target("V1", "단일", {}, "V1_M")], ex.items, [], [])
    assert sorted(c["보험기간구분"] for c in built.conditions) == ["10년만기", "20년만기"]
    # 나이가 다른 두 번째 최초계약 줄은 지금처럼 갱신계약일 수 있다고 표시한다
    other = C.parse("가입나이", section, {"items": [dict(row, term="10년만기"), dict(row, term="20년만기", age="20~60세")]}, "m")
    assert len(other.items) == 2 and any("최초계약 나이 줄이 둘 이상" in p for p in other.problems)


def test_same_limit_given_twice_for_different_subjects_is_merged():
    section = C.Section("가입한도", "나. 가특약, 나특약, 다특약 : 500만원~1,000만원", 3, 3)
    one = {"subjects": ["가특약", "나특약"], "age": "", "min": "500만원", "max": "1,000만원", "unit": ""}
    merged = C.parse("가입한도", section, {"items": [one, dict(one, subjects=["가특약", "다특약"])]}, "m")
    assert [i.subjects for i in merged.items] == [["가특약", "나특약", "다특약"]] and merged.problems == []
    # 금액이 다르면 어느 쪽이 맞는지 알 수 없으므로 합치지 않고 문제로 남긴다
    clash = C.parse("가입한도", section, {"items": [one, dict(one, subjects=["가특약", "다특약"], max="2,000만원")]}, "m")
    assert [i.subjects for i in clash.items] == [["가특약", "나특약"]] and clash.problems == ["같은 항목이 두 번 나옴: 가특약||"]


def test_rider_with_premium_in_its_name_is_not_the_main_contract():
    waiver, extra = "[건강]보험료 납입면제대상", "어린이보험 추가보장"
    assert not C.is_main(waiver) and not C.is_main("보험금 선지급 제도성 특별약관") and not C.is_main("보험기간")
    assert C.is_main("가나다통합보험 무배당") and C.is_main("무배당 가나다건강보험(325)(20년갱신형) 2504")
    from postlife import ids
    rows = riders("V1") + [{"특약ID": f"V1_{n}", "종형ID": "V1", "특약계보키": ids.rider_lineage_key(name), "담보구분": "선택특약",
                            "원시특약명": name} for n, name in enumerate((waiver, extra))]
    t = C.target_of("V1", "1종", rows)
    assert t.rider(waiver) == (True, "V1_0") and t.rider(MAIN) == (True, None) and t.rider("주계약") == (True, None)
    assert t.rider(extra) == (True, "V1_1")              # 뽑아 둔 특약 목록에 있는 이름은 "보험"이 들어 있어도 특약이다
    built = C.build_rows([t], [], [], [C.ConstraintItem(CANCER, [waiver], "선행가입", "", "납입면제대상은 암진단특약에 가입한 경우에 한함")])
    assert [(c["기준특약ID"], c["대상특약ID"]) for c in built.constraints] == [(t.rider(CANCER)[1], "V1_0")]
    # 제약을 받는 쪽이 주계약이면 행으로 만들 수 없다. 조용히 버리지 않고 적어 둔다
    built = C.build_rows([t], [], [], [C.ConstraintItem(CANCER, ["주계약"], "의무부가", "", "")])
    assert built.constraints == [] and any("주계약이라 건너뜀" in n for n in built.notes)


def test_variant_scope_is_matched_on_whole_names():
    def applies(scope, names):
        every = [C.Target(n, n, {}, None) for n in names]
        return [C._applies(scope, t, every) for t in every]

    assert applies("11종", ["1종", "11종"]) == [False, True] and applies("1종, 11종", ["1종", "11종"]) == [True, True]
    assert applies("가나형(1년)", ["가나형", "가나형(1년)"]) == [False, True]
    assert applies("가나형, 가나형(1년)", ["가나형", "가나형(1년)"]) == [True, True]
    # 종 번호만 적은 구분은 번호가 같은 종형을 가리킨다. 괄호 속 이름까지 적혀 있는데 다르면 맞추지 않는다
    names = ["7종(면제형) 가", "7종(면제형) 나", "8종(일반형)"]
    assert applies("8종", names) == [False, False, True] and applies("1종, 7종 및 18종", names) == [True, True, False]
    assert applies("8종(다른형)", names) == [None, None, None] and applies("9종", names) == [None, None, None]
    assert applies("", names) == [True, True, True]


def test_link_values_written_as_multiples_and_fractions():
    def value(text):
        return C.ConstraintItem("주계약", [CANCER], "최대연동", text, "").value

    assert value("주계약 보험가입금액의 2배 이내") == (2.0, "비율") and value("주계약 보험가입금액의 1.5배 한도") == (1.5, "비율")
    assert value("주계약 보험가입금액의 1/2 이내") == (0.5, "비율") and value("주계약 보험가입금액의 2분의 1 이내") == (0.5, "비율")
    assert value("주계약 보험가입금액 이내") == (1.0, "비율") and value("주계약의 200% 이내") == (2.0, "비율")
    assert value("1,000만원 이내") == (1000.0, "만원") and value("") == (None, None)


def test_figure_of_a_constraint_must_be_written_in_the_source():
    section = C.Section("결합제약", f"{CANCER}은 주계약 보험가입금액의 80% 이내에서 가입 가능", 3, 3)

    def missing(value):
        ex = C.parse("결합제약", section, {"items": [{"base": "주계약", "targets": [CANCER], "kind": "최대연동", "value": value,
                                                  "quote": "주계약 보험가입금액의 80% 이내"}]}, "m")
        return list(C.literal_problems(ex).values())

    assert missing("주계약 보험가입금액의 80% 이내") == [] and missing("주계약 보험가입금액 이내") == []
    assert missing("주계약 보험가입금액의 50% 이내") == [["수치"]] and missing("주계약 보험가입금액의 2배 이내") == [["수치"]]


def test_main_contract_written_as_the_product_name_in_the_item_heading():
    section = C.method_sections(pages_from_text(METHOD))["가입나이"]
    # 원문의 "가." 항목은 상품 이름으로 시작하고 "주계약"이라는 글자는 없다. 모델은 지시문대로 "주계약"이라고 적는다
    ex = C.parse("가입나이", section, {"items": [dict(AGES["items"][0], subjects=["주계약", CANCER])]}, "m")
    assert C.literal_problems(ex) == {}
    # 다른 항목("나.")의 나이를 주계약에 붙이면 여전히 잘못 묶은 것으로 잡는다
    wrong = C.parse("가입나이", section, {"items": [dict(AGES["items"][4], subjects=["주계약"])]}, "m")
    assert list(C.literal_problems(wrong).values()) == [["묶음"]]


def test_problem_of_another_item_is_not_pinned_on_an_item_with_a_shorter_key():
    section = C.Section("가입나이", "2. 가입나이\n최초계약 20~70세 10년만기 전기납", 2, 2)
    item = C.AgeItem(["주계약"], "", "최초계약", "", "20~70세", "10년만기", "전기납")
    good = {item.key: {"가입나이": 0.95, "보험기간": 0.95}}
    th = dict(P.DEFAULT_THRESHOLDS)
    # 읽지 못해 버린 다른 줄의 키가 이 항목의 키로 시작한다
    other = R._Shot(C.Extracted("가입나이", section, [item], "m", [f"가입나이를 숫자로 읽을 수 없음: {item.key} (일부 60세)"]), good, {})
    assert not other.flawed(item.key) and other.score(th)[:2] == (1, 0)        # 항목은 멀쩡하고, 문제는 따로 한 건으로 센다
    own = R._Shot(C.Extracted("가입나이", section, [item], "m", [f"같은 항목이 두 번 나옴: {item.key}"]), good, {})
    assert own.flawed(item.key) and own.score(th)[:2] == (1, 0)


class Sequence(FakeGemini):
    """가입나이 절의 답을 차례로 돌려준다."""

    def __init__(self, answers, prob=0.95):
        super().__init__()
        self.answers, self.prob = list(answers), prob

    def generate(self, model, prompt, schema=None, temperature=0.0):
        self.calls[model] = self.calls.get(model, 0) + 1
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]

    def decide(self, model, text, questions):
        return {k: Answer(True, None, {"true": self.prob, "false": 0.05}) for k in questions}


def section_run(g, kind, section):
    from postlife.worklog import WorkLog
    log = WorkLog(datetime(2026, 11, 18, 17, 0, tzinfo=KST), "sys_가입조건")
    return R.run_section(g, kind, section, dict(P.DEFAULT_THRESHOLDS), log, "V1:" + kind, {"상위모델": 0}), log.rows


def test_empty_answer_for_an_age_section_is_retried_and_replaced():
    section = C.method_sections(pages_from_text(METHOD))["가입나이"]
    # 첫 답이 0건이고 다시 뽑은 답에 사람이 볼 항목(0.6)이 있어도 다시 뽑은 쪽을 쓴다
    g = Sequence([{"items": []}, AGES], prob=0.6)
    shot, logs = section_run(g, "가입나이", section)
    assert sum(g.calls.values()) == 2 and len(shot.ex.items) == 4
    assert [(l["작업단계"], l["결과"]) for l in logs] == [("추출", "통과"), ("재추출", "통과")]
    # 제약 절은 옮길 것이 없으면 0건이 맞는 답이다. 다시 뽑지 않는다
    g = Sequence([{"items": []}])
    shot, _ = section_run(g, "결합제약", C.Section("결합제약", "특약은 선택하여 부가할 수 있음", 3, 3))
    assert sum(g.calls.values()) == 1 and shot.ex.items == []


def test_age_section_that_stays_empty_is_noted():
    class Nothing(FakeGemini):
        def generate(self, model, prompt, schema=None, temperature=0.0):
            self.calls[model] = self.calls.get(model, 0) + 1
            return {"items": []} if '"가입나이, 보험기간' in prompt else super().generate(model, prompt, schema)

    g = Nothing()
    r = run(g)
    assert g.calls[config.MODEL_EXTRACT_ALT] == 1 and any("가입나이 절에서 항목을 하나도 뽑지 못함" in n for n in r.notes)
    assert r.conditions == []


SUMMARY_RULE = SUMMARY.replace("주) 1. 특약은", f"주) 1. {NURSING}은 {CANCER}을 가입하는 경우에 한하여 부가\n2. 특약은")


class OneSided(FakeGemini):
    """같은 제약을 사업방법서 절과 요약서 절에서 모두 돌려주고, 한쪽 절에서만 판정을 낮게 준다."""

    def __init__(self, low_in):
        super().__init__()
        self.low_in = low_in

    def generate(self, model, prompt, schema=None, temperature=0.0):
        kind = "가입나이" if '"가입나이, 보험기간' in prompt else "가입한도" if '"보험가입금액의 한도" 절' in prompt else "결합제약"
        return {"가입나이": AGES, "가입한도": LIMITS, "결합제약": RULES}[kind]

    def decide(self, model, text, questions):
        low = self.low_in in text and "경우에만 부가" in str(questions)
        return {k: Answer(True, None, {"true": 0.1 if low else 0.95, "false": 0.05}) for k in questions}


def test_item_written_from_one_section_is_not_reported_as_left_out():
    t, _ = targets()
    for low_in in ("② 보험가입 자격요건", "4. 특약부가에 관한 사항"):          # 요약서 쪽만 낮을 때, 사업방법서 쪽만 낮을 때
        r = R.run(OneSided(low_in), pages_from_text(METHOD), pages_from_text(SUMMARY_RULE), t,
                  datetime(2026, 11, 18, 17, 0, tzinfo=KST), dict(P.DEFAULT_THRESHOLDS))
        assert len(r.constraints) == 2 and {c["제약유형"] for c in r.constraints} == {"선행가입"}      # 두 종형에 한 줄씩 쓴다
        assert r.stats["제외"] == 0 and r.stats["확정"] == r.stats["항목"]
        assert not any("시트에 쓰지 않음" in line for line in r.review)
        rule = [l for l in r.logs if l["대상탭"] == "sys_결합제약" and l["작업단계"] == "판정"]
        assert [(l["결과"], l["대상행ID"] == r.constraints[0]["제약ID"]) for l in rule] == [("통과", True), ("반려", True)]
        assert "다른 절에서 뽑은 같은 항목으로 시트에 씀" in rule[1]["사유"] and rule[1]["판정확률"] == 0.1
    # 두 절 모두 낮으면 지금처럼 쓰지 않고 그렇게 적는다
    r = R.run(OneSided("특약"), pages_from_text(METHOD), pages_from_text(SUMMARY_RULE), t,
              datetime(2026, 11, 18, 17, 0, tzinfo=KST), dict(P.DEFAULT_THRESHOLDS))
    assert r.constraints == [] and r.stats["제외"] == 1 and sum("시트에 쓰지 않음" in line for line in r.review) == 2
