"""지급횟수제한 구절 앞에 붙은 한정어를 원문에서 함께 자르는가(reader_rows.limit_phrase, _qualifier_start, 2026-11-24).

추출 모델은 한도를 {앞말, 수, 단위}로만 적는다. 코드가 원문에서 구절을 자를 때 "동일한 가나병당", "신체부위별",
"치료구분별 각각" 같은 한정어를 빠뜨리면 보험기간 전체의 한도처럼 읽힌다. 지급단위 구절(1일당, 수술 1회당)은 한정어로
잡지 않고, 길이 한도를 넘는 열거는 붙이지 않는다. 문구, 이름, 금액은 모두 지어낸 것이다(공시 문서의 문장이 아니다).
"""
from postlife.extract import reader_rows as RR
from postlife.site.insights import pay_tags


def view(reason, amount="1만원", name="가나 수술급여금", number="R001-1"):
    return RR.CoverView(number, name, reason, amount, 10)


def piece_of(cover, notes=()):
    return RR.PieceView(1, "가나특약", ("가나특약",), "선택특약", "", 10, 10, (cover,), tuple(notes))


def reading(**values):
    return {**RR.DEFAULTS, "번호": "R001-1", "쪽": 10, "꼴": RR.AMOUNT, "기준가입금액만원": 1, "지급액만원": 1, **values}


def limit(lead, n, unit="회"):
    return {"앞말": lead, "수": n, "단위": unit}


BARE1 = limit("없음", 1)
ANNUAL1 = limit("연간", 1)
ANNUAL2 = limit("연간", 2)


def test_same_thing_per_qualifier():
    c = view("가나병 치료로 수술한 때 (다만, 동일한 가나병당 1회에 한함)")
    assert RR.limit_phrase(BARE1, c) == "동일한 가나병당 1회에 한함"


def test_one_code_per_qualifier():
    c = view("가나 수술을 받은 때(1회의 입원에 한하여 보장하며, 하나의 다라코드당 연간 2회한 보장)")
    assert RR.limit_phrase(ANNUAL2, c) == "하나의 다라코드당 연간 2회한"


def test_each_of_named_kinds_per_qualifier_takes_the_named_list():
    c = view("가나 수술 시\n* 다만, “가나질환” 및 “다라질환” 각각의 질환(2종)당 보험연도 기준 연2회의 시술에 한함")
    assert RR.limit_phrase(ANNUAL2, c) == "“가나질환” 및 “다라질환” 각각의 질환(2종)당 보험연도 기준 연2회"


def test_by_part_qualifier():
    c = view("가나상해로 진단된 때(보험연도를 기준으로 신체부위별 연간 2회한)")
    # 한정어 앞의 "보험연도를 기준으로"는 한정어와 구절 사이에 끼지 않았으므로 자르지 않는다
    assert RR.limit_phrase(ANNUAL2, c) == "신체부위별 연간 2회한"


def test_by_kind_then_each_qualifier():
    c = view("가나 치료를 받은 때 수술은 수술 1회당, 그 밖의 치료는 치료구분별 각각 연간 2회한)")
    assert RR.limit_phrase(ANNUAL2, c) == "치료구분별 각각 연간 2회한"


def test_class_qualifier():
    c = view("가나 1-3종 수술 시 (종별 연간 2회한)")
    assert RR.limit_phrase(ANNUAL2, c) == "종별 연간 2회한"


def test_each_for_list_qualifier_with_policy_year_in_between():
    c = view("가나 수술 시(가나병 및 다라상해 각각에 대해 보험연도 기준 연2회한)")
    assert RR.limit_phrase(ANNUAL2, c) == "가나병 및 다라상해 각각에 대해 보험연도 기준 연2회한"


def test_single_each_qualifier():
    assert RR.limit_phrase(ANNUAL2, view("가나치료를 받은 때(단, 보험연도 기준 각 연간2회한)")) == "각 연간2회한"
    assert RR.limit_phrase(BARE1, view("가나병, 다라병으로 진단된 때(각 1회한)")) == "각 1회한"


def test_policy_year_between_qualifier_and_limit():
    c = view("가나 수술을 받은 때(동일한 가나병당 보험연도 기준 연간 2회)")
    assert RR.limit_phrase(ANNUAL2, c) == "동일한 가나병당 보험연도 기준 연간 2회"


def test_same_cause_subject_qualifier_in_rider_notes():
    c = view("가나 수술을 받은 때", "회당 1만원", name="다라보험금")
    p = piece_of(c, notes=("3. 동일한 가나병으로 인한 “다라보험금”은 보험연도 기준 연2회에 한하여 보장합니다.",))
    assert RR.limit_phrase(ANNUAL2, c, p) == "동일한 가나병으로 인한 “다라보험금”은 보험연도 기준 연2회에 한하여"


def test_same_accident_before_accident_lead():
    c = view("가나 수술 시(동일한 재해사고당 2회한)")
    assert RR.limit_phrase(limit("1사고당", 2), c) == "동일한 재해사고당 2회한"


def test_each_takes_the_named_list_in_the_same_clause():
    c = view("가나암 치료를 받은 경우(다만, “가나암” 또는 “다라암” 각각 최초 2회에 한하여 지급)")
    assert RR.limit_phrase(limit("최초", 2), c) == "“가나암” 또는 “다라암” 각각 최초 2회에 한하여"
    bare = view("가나암 치료를 받은 경우(다만, 가나암 또는 다라암 각각 1회한)")
    assert RR.limit_phrase(BARE1, bare) == "가나암 또는 다라암 각각 1회한"
    # 대상이 괄호 밖에 있거나 열거가 문장 조각의 첫머리에서 시작하지 않으면 "각각"만 자른다
    outside = view("가나암 또는 다라암으로 진단된 때 (각각 최초 2회한)")
    assert RR.limit_phrase(limit("최초", 2), outside) == "각각 최초 2회한"
    inside = view("가나 치료를 받은 경우 가나암 또는 다라암 각각 1회한")
    assert RR.limit_phrase(BARE1, inside) == "각각 1회한"


def test_payment_unit_is_not_taken_as_a_qualifier():
    c = view("가나 돌봄을 받은 경우 (가나 사용 1일당 95일 한도)", "가나 사용 1일당 1만원", name="가나 돌봄급여금")
    v = reading(지급단위="1일당", 한도=[limit("없음", 95, "일")])
    assert RR.limit_phrase(v["한도"][0], c) == "95일 한도"
    cell = RR.reading_of(v, c, None, c.name).limit
    assert cell == "사용 1일당 / 95일 한도" and cell.count("1일당") == 1
    # "각 1회당"처럼 한정어 꼴이어도 지급단위 구절이 든 말은 붙이지 않는다
    assert RR.limit_phrase(ANNUAL2, view("가나 수술 시(수술은 각 1회당 연간 2회한)")) == "연간 2회한"
    # "1회 가나수술입원당"의 "가나수술입원당"만 떼어 붙이지 않는다(한정어 앞에 수가 붙은 지급 단위)
    assert RR.limit_phrase(limit("없음", 9, "일"), view("가나 입원 시(1회 가나수술입원당 9일한도)")) == "9일한도"


def test_words_ending_in_byeol_that_are_not_qualifiers():
    assert RR.limit_phrase(ANNUAL2, view("가나 치료 시 (특별 연간 2회한)")) == "연간 2회한"


def test_glued_policy_year_and_annual_lead():
    c = view("가나 수술 시\n* 다만, 가나 수술은 하나의 다라코드당 보험연도 기준연2회에 한하여 보장")
    assert RR.limit_phrase(ANNUAL2, c) == "하나의 다라코드당 보험연도 기준연2회에 한하여"
    assert RR.machine_checks(c, reading(한도=[ANNUAL2]))[0] == []
    assert RR.limit_phrase(ANNUAL2, view("가나 치료 시(단, “가나치료금”은 보험연도 기준연 2회에 한하여 보장)")) == \
        "연 2회에 한하여"
    # 낱말 속의 "연"은 여전히 앞말이 아니다
    assert RR.limit_phrase(ANNUAL2, view("가나 수술 시 전연2회 다라")) is None


def test_long_named_list_is_left_out():
    names = ", ".join(f"“가나다라마바사{k}형”" for k in range(1, 5))
    c = view(f"가나암으로 진단된 경우(다만, {names} 또는 “아자차카타파{5}형”에 대해 각각 최초 2회의 진단에 한함)")
    assert RR.limit_phrase(limit("최초", 2), c) == "각각 최초 2회"
    assert RR._QUALIFIER_MAX == 40


def test_pay_tags_do_not_read_qualifiers():
    """화면의 지급 형태 꼬리표(insights.pay_tags)는 한정어를 읽지 않는다. 한정어를 붙여도 판정이 바뀌지 않는다."""
    for qualified, plain in (("동일한 가나병당 1회에 한함", "1회에 한함"),
                             ("치료구분별 각각 연간 2회한", "각각 연간 2회한"),
                             ("하나의 다라코드당 보험연도 기준 연2회한", "연2회한"),
                             ("동일한 재해사고당 2회한", "사고당 2회한"),
                             ("각 연간2회한", "연간2회한")):
        assert pay_tags(qualified) == pay_tags(plain), qualified
