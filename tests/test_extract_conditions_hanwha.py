"""가입나이를 "가입최저나이"와 "가입최고나이 표"로 따로 적고, 여러 가입유형을 한 표에 담은 문서의 가입조건 추출.

시험 글은 실제 문서의 제목 모양과 표가 글자로 풀린 모양만 본떠 직접 만든 것이다. 상품·특약 이름과 숫자는 지어낸 것이다.
모델은 부르지 않는다. 모델이 돌려줄 법한 항목을 손으로 만들어 넣는다.
"""
from datetime import datetime

from postlife import ids
from postlife.extract import conditions as C
from postlife.extract import conditions_run as R
from postlife.extract import pipeline as P
from postlife.extract.segment import pages_from_text
from postlife.gemini import Answer
from postlife.snapshot import KST
from postlife.validate import check_rows

# 가입유형 이름은 합쳐진 칸 가운데에 적혀 있어 그 유형의 줄들 사이에 끼어 있거나("간편가입형(1년)"),
# 쪽이 넘어가는 곳에서는 줄 앞에 붙어 있다("간편가입형(10년) 10년납 …"). 쪽이 바뀌면 표 머리가 되풀이된다.
METHOD = """
===== 3쪽 =====
(사업방법서 별지)
1. 보험종목에 관한 사항
가. 보험종목의 명칭
- 가나다통합보험 무배당
2. 보험기간, 보험료 납입기간, 보험료 납입주기 및 피보험자 가입나이
가. 보험기간, 보험료 납입기간 및 피보험자 가입나이
- 가입최저나이: 만15세
- 가입최고나이: 보험종목, 성별, 보험기간 및 보험료 납입기간별로 아래와 같음
90세만기 종신
구 분
남자 여자 남자 여자
10년납 79세 79세 80세 80세
간편가입형(1년)
20년납 69세 69세 79세 80세
간편가입형(10년) 10년납 75세 75세 76세 76세
1 - 1

===== 4쪽 =====
90세만기 종신
구 분
남자 여자 남자 여자
20년납 65세 65세 76세 76세
10년납 79세 79세 80세 80세
일반가입형 20년납 69세 68세 80세 80세
나. 보험료 납입주기: 월납
3. 의무가입에 관한 사항
- 해당 없음
4. 고정부가에 관한 사항
- 해당 없음
18. 기타사항
가. 보험가입금액(1구좌) : 1,000만원
"""

# 사업방법서에 가입한도 절이 없고, 요약서 자격요건 절의 "마. 가입한도"에만 주계약 한도가 있다.
SUMMARY = """
===== 6쪽 =====
2.
보험가입자격요건
가. 보험의 종류
(1) 간편가입형(1년)
※ 주계약 간편가입형(1년)에는 특약 간편가입형(1년)만 부가
나. 보험기간
▪ 비갱신형 특약
- 90세만기, 종신(주계약 보험기간 이내)
· 가나다진단특약(고지통합)(무)

===== 7쪽 =====
마. 가입한도
▪ 주계약 :
구 분 가입 한도
간편가입형(1년)
~70세 300만원~1,000만원
주계약 간편가입형(10년)
71세~ 300만원
일반가입형
※ 그 외 특약의 가입한도는 회사가 별도로 정한 기준에 따라 적용합니다.
바. 건강진단 여부
- 간편가입형의 경우 무진단으로 가입 가능

===== 8쪽 =====
3.
보험금 지급사유 및 지급제한 사항
"""

SIMPLE, SIMPLE10, GENERAL = "간편가입형(1년)", "간편가입형(10년)", "일반가입형"
RIDER = "가나다진단특약(고지통합)(KTA1.1) 무배당"
COLUMNS = (("90세만기", "남자"), ("90세만기", "여자"), ("종신", "남자"), ("종신", "여자"))


def cells(scope, payment, tops):
    """표의 한 줄을 모델이 옮긴 모양: 칸마다 항목 하나, 나이는 가입최저나이와 그 칸의 최고나이를 이어 적는다."""
    return [{"subjects": ["주계약"], "variant_scope": scope, "contract": "구분없음", "sex": sex, "age": f"만15세~{top}세",
             "term": term, "payment": payment} for (term, sex), top in zip(COLUMNS, tops)]


AGES = {"items": cells(SIMPLE, "10년납", (79, 79, 80, 80)) + cells(SIMPLE, "20년납", (69, 69, 79, 80))
        + cells(GENERAL, "10년납", (79, 79, 80, 80)) + cells(GENERAL, "20년납", (69, 68, 80, 80))}
LIMITS = {"items": [
    {"subjects": ["주계약"], "variant_scope": "", "age": "~70세", "min": "300만원", "max": "1,000만원", "unit": ""},
    {"subjects": ["주계약"], "variant_scope": "", "age": "71세~", "min": "300만원", "max": "300만원", "unit": ""}]}
# 기간을 주계약에 맞춘다는 문장을 가입금액 연동으로 잘못 옮긴 경우
WRONG_LINK = {"items": [{"base": "주계약", "targets": [RIDER], "kind": "최대연동", "value": "주계약 보험기간 이내",
                         "quote": "90세만기, 종신(주계약 보험기간 이내)"}]}


def targets():
    def rows(variant):
        return [{"특약ID": ids.rider_id(variant, name), "종형ID": variant, "특약계보키": ids.rider_lineage_key(name),
                 "담보구분": kind, "원시특약명": name} for name, kind in (("주계약", "주계약"), (RIDER, "선택특약"))]
    every = rows("V1") + rows("VG")
    return [C.target_of("V1", SIMPLE, every), C.target_of("VG", GENERAL, every)]


def age_section(types=None):
    return C.method_sections(pages_from_text(METHOD), types=types)["가입나이"]


def main_rows(rows, variant, **want):
    return sorted((c["최저가입나이"], c["최고가입나이"], c["구간최대가입금액만원"]) for c in rows
                  if c["종형ID"] == variant and c["특약ID"] is None and all(c[k] == v for k, v in want.items()))


class FakeGemini:
    def __init__(self):
        self.prompts, self.questions = {}, []

    def generate(self, model, prompt, schema=None, temperature=0.0):
        kind = ("가입나이" if '"가입나이, 보험기간' in prompt else "가입한도" if '"보험가입금액의 한도" 절' in prompt else "결합제약")
        self.prompts.setdefault(kind, []).append(prompt)
        return {"가입나이": AGES, "가입한도": LIMITS, "결합제약": WRONG_LINK}[kind]

    def decide(self, model, text, questions):
        self.questions += [q["instructions"] for q in questions.values()]
        return {k: Answer(True, None, {"true": 0.95, "false": 0.05}) for k in questions}


def run(g):
    return R.run(g, pages_from_text(METHOD), pages_from_text(SUMMARY), targets(), datetime(2026, 11, 19, 12, 0, tzinfo=KST),
                 dict(P.DEFAULT_THRESHOLDS))


def test_table_is_read_as_row_groups_per_type():
    first, last, groups = C.row_groups(age_section().text.split("\n"))
    assert [(g.name, [pay for pay, _ in g.rows]) for g in groups] == [
        (SIMPLE, ["10년납", "20년납"]), (SIMPLE10, ["10년납", "20년납"]), (GENERAL, ["10년납", "20년납"])]
    assert groups[1].rows[1] == ("20년납", ["65세", "65세", "76세", "76세"])     # 쪽이 넘어간 뒤의 줄도 같은 묶음이다
    assert groups[2].rows[1][1] == ["69세", "68세", "80세", "80세"]             # 이름이 줄 앞에 붙은 줄
    # 이런 표가 아닌 글은 None: 줄 묶음이 하나뿐이거나 이름이 없는 묶음이 있으면 표로 보지 않는다
    assert C.row_groups(["10년납 79세 80세", "간편가입형(1년)", "20년납 69세 80세"]) is None
    assert C.row_groups(["10년납 79세 80세", "20년납 69세 80세", "10년납 79세 80세", "일반가입형", "20년납 69세 80세"]) is None
    assert C.row_groups("최초계약 20~80세 20년만기(갱신형) 전기납 월 납\n갱신계약".split("\n")) is None


def test_types_keep_only_the_row_groups_of_those_types():
    whole = age_section()
    assert (whole.first_page, whole.last_page) == (3, 4) and SIMPLE10 in whole.text
    cut = age_section([SIMPLE, GENERAL])
    assert cut.text.startswith("2. 보험기간, 보험료 납입기간") and "가입최저나이: 만15세" in cut.text
    assert SIMPLE10 not in cut.text and "75세" not in cut.text and "65세 65세 76세 76세" not in cut.text
    assert "일반가입형 20년납 69세 68세 80세 80세" in cut.text and cut.text.endswith("나. 보험료 납입주기: 월납")
    assert [g.name for g in C.row_groups(cut.text.split("\n"))[2]] == [SIMPLE, GENERAL]   # 줄인 글도 같은 방법으로 읽힌다
    one = age_section([SIMPLE])
    assert (one.first_page, one.last_page) == (3, 3) and "20년납 69세 69세 79세 80세" in one.text and "일반가입형" not in one.text
    ten = age_section([SIMPLE10])                      # "(1년)"은 "(10년)"에 걸리지 않고, 쪽이 넘어간 묶음은 두 쪽에 걸친다
    assert (ten.first_page, ten.last_page) == (3, 4) and "간편가입형(1년)" not in ten.text and "20년납 65세" in ten.text
    assert age_section(["건강가입형(6년)"]) == whole      # 표에 없는 이름이면 통째로 돌려준다
    sections = C.method_sections(pages_from_text(METHOD), types=[SIMPLE])
    assert sections["특약부가"] == C.method_sections(pages_from_text(METHOD))["특약부가"]    # 표가 없는 절은 그대로다


def test_limits_come_from_the_summary_when_the_method_document_has_none():
    assert "가입한도" not in C.method_sections(pages_from_text(METHOD))
    limit = C.eligibility_limits(pages_from_text(SUMMARY))
    assert limit.kind == "가입한도" and (limit.first_page, limit.last_page) == (7, 7)
    assert limit.text.startswith("마. 가입한도") and "71세~ 300만원" in limit.text and "건강진단" not in limit.text
    assert C.eligibility_limits(pages_from_text(SUMMARY.replace("마. 가입한도", "마. 그 밖의 사항"))) is None
    assert C.eligibility_limits(pages_from_text(METHOD)) is None


def test_age_band_written_with_a_tilde_on_one_side():
    assert C.parse_age_band("~70세") == (0, 70) and C.parse_age_band("71세~") == (71, C.MAX_AGE)
    assert C.parse_age_band("~ 70세") == (0, 70) and C.parse_age_band("66세~70세") == (66, 70)
    assert C.parse_age_band("70세") is None


def test_joined_age_is_accepted_only_where_lowest_and_highest_ages_are_written_apart():
    source = age_section().text
    assert C.split_age("만15세~79세", source) == ("만15세", "79세") and C.parse_age_range("만15세~79세") == (15, 79)
    assert C.split_age("15세~79세", source) is None            # 최저나이 글자("만15세")와 다르다
    assert C.split_age("만15세~79세", "가. 주계약\n최초계약 20~80세 20년만기 전기납") is None   # 나이를 한 줄에 적는 문서


def test_section_that_only_says_none_is_not_sent_to_the_model():
    s = C.method_sections(pages_from_text(METHOD))["특약부가"]
    assert s.text == "3. 의무가입에 관한 사항\n- 해당 없음" and C.says_none(s)
    assert not C.says_none(C.Section("특약부가", "4. 특약부가에 관한 사항\n가. 가나다진단특약(선택)", 3, 3))
    assert not C.says_none(C.Section("특약부가", "3. 의무가입에 관한 사항", 3, 3))


def test_prompt_gets_a_note_only_for_the_shape_it_is_about():
    for kind, text in (("가입나이", "2. 가입나이, 보험기간\n가. 주계약\n최초계약 20~80세 20년만기 전기납"),
                       ("가입한도", "3. 보험가입금액의 한도\n가. 주계약\n65세 이하 1,000만원~4,000만원"),
                       ("결합제약", "주) 1. 특약은 주계약 보험가입금액 이내에서 가입 가능")):
        assert C.prompt_for(kind, text) == C.PROMPTS[kind][0].replace("{text}", text)      # 그 모양이 아니면 예전 지시문 그대로
    age = C.prompt_for("가입나이", age_section([SIMPLE]).text)
    assert C.AGE_BY_MAX_NOTE in age and age.endswith("본문\n" + age_section([SIMPLE]).text)
    assert age.replace(C.AGE_BY_MAX_NOTE + "\n\n", "") == C.AGE_PROMPT.replace("{text}", age_section([SIMPLE]).text)
    limit = C.eligibility_limits(pages_from_text(SUMMARY)).text
    assert C.LIMIT_TILDE_NOTE in C.prompt_for("가입한도", limit)
    assert C.PERIOD_LINK_NOTE in C.prompt_for("결합제약", C.eligibility_section(pages_from_text(SUMMARY)).text)


def test_cells_of_the_highest_age_table_become_items():
    section = age_section([SIMPLE, GENERAL])
    ex = C.parse("가입나이", section, AGES, "m")
    assert ex.problems == [] and len(ex.items) == 16 and all(i.by_max for i in ex.items)
    # 같은 나이가 여러 칸에 나와도 칸마다 항목이 따로 남는다
    assert len({i.key for i in ex.items}) == 16
    assert sum(1 for i in ex.items if i.scope == SIMPLE and i.age_text == "만15세~80세") == 3
    assert C.literal_problems(ex) == {}
    question = C.checks("가입나이", ex.items[6])["가입나이"]["instructions"]
    assert "가입유형 '간편가입형(1년)', 보험료 납입기간 '20년납' 줄의 보험기간 '종신' 남자 칸에 적힌 나이는 '79세'" in question
    assert "가입최저나이는 '만15세'" in question


def test_bare_cell_text_and_contract_word_are_tolerated():
    section = age_section([SIMPLE, GENERAL])
    # 칸의 글자("79세")만 옮겨 오면 원문의 가입최저나이 글자를 코드가 붙인다
    bare = {"items": [dict(i, age=i["age"].split("~")[1]) for i in AGES["items"]]}
    ex = C.parse("가입나이", section, bare, "m")
    assert [i.age_text for i in ex.items] == [i["age"] for i in AGES["items"]] and C.literal_problems(ex) == {}
    # 최초계약이라고 적어 와도, 이 표에는 최초·갱신 줄 구분이 없으므로 "최초계약 줄이 둘 이상"으로 잡지 않는다
    first = C.parse("가입나이", section, {"items": [dict(i, contract="최초계약") for i in AGES["items"]]}, "m")
    assert first.problems == [] and len(first.items) == 16


def test_code_check_catches_an_age_taken_from_another_row_or_type():
    section = age_section([SIMPLE, GENERAL])

    def flaws(scope, payment, top):
        raw = {"items": [dict(cells(scope, payment, (top,))[0])]}
        return list(C.literal_problems(C.parse("가입나이", section, raw, "m")).values())

    assert flaws(SIMPLE, "20년납", 69) == []
    assert flaws(SIMPLE, "20년납", 80) == []                 # 그 줄에 있는 나이다. 어느 칸인지는 판정 문항이 본다
    assert flaws(SIMPLE, "10년납", 69) == [["묶음"]]          # 69세는 20년납 줄의 나이다
    assert flaws(SIMPLE, "20년납", 68) == [["묶음"]]          # 68세는 일반가입형 줄의 나이다
    assert flaws(GENERAL, "30년납", 80) == [["묶음", "납입기간"]]
    # 최저나이를 원문과 다르게 적으면 이어 적은 나이로 받아들이지 않는다
    off = {"items": [dict(cells(SIMPLE, "10년납", (79,))[0], age="15세~79세")]}
    assert list(C.literal_problems(C.parse("가입나이", section, off, "m")).values()) == [["묶음", "가입나이"]]


def test_rows_for_each_type_term_payment_and_sex():
    section = age_section([SIMPLE, GENERAL])
    ages = C.parse("가입나이", section, AGES, "m")
    limits = C.parse("가입한도", C.eligibility_limits(pages_from_text(SUMMARY)), LIMITS, "m")
    assert limits.problems == [] and C.literal_problems(limits) == {}
    built = C.build_rows(targets(), ages.items, limits.items, [])
    assert check_rows("sys_가입조건", built.conditions) == {} and built.constraints == [] and built.notes == []
    assert len(built.conditions) == 28 and all(c["특약ID"] is None for c in built.conditions)
    # 가입나이 구간은 한도가 바뀌는 71세에서 나뉜다
    assert main_rows(built.conditions, "V1", 보험기간구분="종신", 납입기간구분="20년납", 성별="M") == [(15, 70, 1000), (71, 79, 300)]
    assert main_rows(built.conditions, "V1", 보험기간구분="종신", 납입기간구분="20년납", 성별="F") == [(15, 70, 1000), (71, 80, 300)]
    assert main_rows(built.conditions, "V1", 보험기간구분="90세만기", 납입기간구분="20년납", 성별="M") == [(15, 69, 1000)]
    assert main_rows(built.conditions, "VG", 보험기간구분="90세만기", 납입기간구분="20년납", 성별="F") == [(15, 68, 1000)]
    assert {c["보험기간구분"] for c in built.conditions} == {"90세만기", "종신"}
    assert {c["납입기간구분"] for c in built.conditions} == {"10년납", "20년납"}
    assert {c["최저가입나이"] for c in built.conditions if c["구간최대가입금액만원"] == 1000} == {15}
    # 주계약의 최소·최대 가입금액. 특약 한도는 문서에 없으므로 만들지 않는다
    t = targets()
    assert built.amounts == {t[0].main_id: (300, 1000), t[1].main_id: (300, 1000)}


def test_type_outside_the_targets_is_skipped_with_a_note():
    raw = {"items": cells(SIMPLE10, "10년납", (75, 75, 76, 76))}
    ages = C.parse("가입나이", age_section(), raw, "m")
    built = C.build_rows(targets(), ages.items, [], [])
    assert built.conditions == [] and built.notes == ["종 구분 '간편가입형(10년)'이 어느 종형과도 맞지 않아 건너뜀"]


def test_period_link_is_not_written_as_an_amount_link():
    section = C.eligibility_section(pages_from_text(SUMMARY))
    assert C.parse("결합제약", section, WRONG_LINK, "m").items == []
    amount = {"items": [dict(WRONG_LINK["items"][0], value="주계약 보험가입금액 이내")]}
    ex = C.parse("결합제약", section, amount, "m")
    assert [i.value for i in ex.items] == [(1.0, "비율")]


def test_whole_flow_with_hand_made_model_answers():
    g = FakeGemini()
    r = run(g)
    assert check_rows("sys_가입조건", r.conditions) == {} and r.constraints == [] and r.review == [] and r.notes == []
    assert r.stats == {"항목": 18, "확정": 18, "검토": 0, "제외": 0, "가입조건 행": 28, "결합제약 행": 0}
    # 모델에는 대상 종형의 줄 묶음만 들어가고, 가입한도는 요약서에서 읽는다
    assert len(g.prompts["가입나이"]) == 1 and SIMPLE10 not in g.prompts["가입나이"][0].split("본문\n")[-1]
    limit_body = g.prompts["가입한도"][0].split("본문\n")[-1]
    assert limit_body.startswith("마. 가입한도") and "~70세 300만원~1,000만원" in limit_body and "건강진단" not in limit_body
    # "해당 없음"뿐인 의무가입 절은 모델에 보내지 않고 기록만 남긴다. 제약 지시문은 요약서 자격요건 절 한 번뿐이다
    assert len(g.prompts["결합제약"]) == 1 and "보험가입자격요건" in g.prompts["결합제약"][0]
    noted = [l for l in r.logs if l["작업단계"] == "코드대조"]
    assert len(noted) == 1 and noted[0]["대상탭"] == "sys_결합제약" and "해당 없음" in noted[0]["사유"] and "4~4쪽" in noted[0]["사유"]
    assert len(g.questions) == 18
    assert main_rows(r.conditions, "VG", 보험기간구분="종신", 납입기간구분="10년납", 성별="F") == [(15, 70, 1000), (71, 80, 300)]
    assert len({c["조건행ID"] for c in r.conditions}) == 28
