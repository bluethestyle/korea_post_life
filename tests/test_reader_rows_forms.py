"""교보생명, 현대해상 판정에서 값이 맞는데 기계 검사가 원문 구절을 찾지 못해 행이 되지 않던 문구 형식.

"치료당 1회", "통원당 1회" 같은 지급단위, "× 후유장해지급률", "3백만원"처럼 백만 단위를 쓴 금액, "입원 1회당 1회 한도",
"단,"으로 이어지는 감액예외 단서 문장. 문구, 이름, 금액은 모두 지어낸 것이다(공시 문서의 문장이 아니다).
"""
from postlife.extract import reader_rows as RR


def view(reason, amount="1만원", name="가나 치료비", number="R001-1"):
    return RR.CoverView(number, name, reason, amount, 10)


def reading(**values):
    return {**RR.DEFAULTS, "번호": "R001-1", "쪽": 10, "꼴": RR.AMOUNT, "기준가입금액만원": 1, "지급액만원": 1, **values}


def ratio(**values):
    return reading(꼴=RR.RATIO, 지급률=100, 기준가입금액만원=None, 지급액만원=None, **values)


# ---------------------------------------------------------------------------
# 지급단위: "치료당 1회", "통원당 1회"
# ---------------------------------------------------------------------------

def test_unit_per_treatment_once_is_per_occurrence():
    for amount, cut in (("가나 가입금액(입원 또는 통원 치료당 1회)", "입원 또는 통원 치료당 1회"),
                        ("가나 가입금액(치료당1회)", "치료당1회"),
                        ("가나 가입금액의 20%(각각 치료당 1회)", "치료당 1회"),
                        ("가나 가입금액(각각 입원 또는 통원당 1회)", "입원 또는 통원당 1회")):
        assert RR.unit_phrase("1회당", view("가나병으로 진단 확정되고 다라치료를 받은 경우", amount)) == cut, amount
    c = view("가나병으로 진단 확정되고 다라치료를 받은 경우", "가나 가입금액(치료당 1회)")
    assert RR.machine_checks(c, ratio(지급단위="1회당")) == ([], [])
    # 지급금액 칸의 단위로도 읽는다(지급단위를 비운 값에는 표시가 붙는다)
    assert RR.amount_unit(c) == "1회당"


def test_unit_per_treatment_needs_exactly_once_and_no_limit_word():
    reason = "가나병으로 진단 확정되고 다라치료를 받은 경우"
    for amount in ("가나 가입금액(치료당 2회)",          # 두 번이면 지급단위가 아니다
                   "가나 가입금액(치료당 1회 한도)",     # 한도 구절이다
                   "가나 가입금액(치료당 1회에 한함)",
                   "가나 가입금액(치료당, 12회한)",      # "치료당"만 있고 "1회"가 없다
                   "가나 가입금액(재치료당 1회)",        # 다른 낱말의 꼬리
                   "가나 가입금액(치료당 15만원)"):
        assert RR.unit_phrase("1회당", view(reason, amount)) is None, amount
    # 찾지 못하면 지금처럼 기계 검사에 걸린다
    c = view(reason, "가나 가입금액(치료당, 12회한)")
    assert "구절없음: 지급단위 1회당" in RR.machine_checks(c, ratio(지급단위="1회당"))[0]


def test_existing_per_occurrence_units_still_read():
    for amount, cut in (("수술 1회당 10만원", "수술 1회당"), ("통원 1회당 1만원", "통원 1회당"),
                        ("회당 1만원", "회당")):
        assert RR.unit_phrase("1회당", view("가나 수술", amount)) == cut


# ---------------------------------------------------------------------------
# 지급률곱: "× 후유장해지급률"
# ---------------------------------------------------------------------------

def test_times_aftereffect_rate():
    for amount in ("가나 가입금액 × 후유장해지급률", "가나 가입금액 ×후유장해지급률(단, 첫해 50%)",
                   "가나 가입금액×후유 장해지급률"):
        c = view("가나 사고로 장해상태가 된 경우", amount)
        assert RR.times_phrase(c) is not None and RR.times_phrase(c).startswith("× 후유"), amount
        assert "구절없음: 지급률곱" not in RR.machine_checks(c, ratio(지급률곱=True))[0]
        # 지급률곱을 거짓으로 읽으면 표시가 붙는다
        assert "지급금액 칸에 지급률을 곱하는 표시가 있는데 지급률곱이 거짓" in RR.machine_checks(c, ratio())[1]
    assert RR.times_phrase(view("가나", "가입금액 × 후유장해지급률")) == "× 후유장해지급률"
    # 지급률이라는 말이 없으면 곱하는 대상이 지급률인지 알 수 없다
    assert RR.times_phrase(view("가나", "가입금액 × 후유장해")) is None
    # 기존 형식
    assert RR.times_phrase(view("가나", "가입금액 × 해당 장해지급률")) == "× 해당 장해지급률"
    assert RR.times_phrase(view("가나", "가입금액 × 지급률")) == "× 지급률"


# ---------------------------------------------------------------------------
# 금액: "3백만원"
# ---------------------------------------------------------------------------

def test_money_written_in_millions_of_won():
    c = view("가나병으로 새로 등록된 경우", "3백만원 (최초 1회에 한함)")
    assert RR._money_in(300, [c.amount])
    v = reading(기준가입금액만원=None, 지급액만원=300, 한도=[{"앞말": "최초", "수": 1, "단위": "회"}])
    assert RR.machine_checks(c, v)[0] == []
    # 다른 금액이나 더 큰 숫자의 뒷부분에는 맞추지 않는다
    assert not RR._money_in(30, [c.amount])
    assert not RR._money_in(3, [c.amount])
    assert not RR._money_in(300, ["13백만원"])
    assert not RR._money_in(300, ["3백원"])
    # 기존 형식은 그대로
    assert RR._money_in(3000, ["3천만원"]) and RR._money_in(300, ["300만원"])


# ---------------------------------------------------------------------------
# 한도: "입원 1회당 1회 한도"
# ---------------------------------------------------------------------------

def test_limit_once_per_stay_written_stay_first():
    once = {"앞말": "1회입원당", "수": 1, "단위": "회"}
    c = view("가나 치료 목적으로 2일 이상 입원하여 다라수술을 받은 경우(입원 1회당 1회 한도)", "20만원")
    assert RR.limit_phrase(once, c) == "입원 1회당 1회 한도"
    assert RR.machine_checks(c, reading(기준가입금액만원=None, 지급액만원=20, 한도=[once]))[0] == []
    # 기존 어순도 그대로
    assert RR.limit_phrase(once, view("가나 입원 시 (1회 입원당 1회 한도)")) == "1회 입원당 1회 한도"
    # 수가 다르거나 다른 낱말의 꼬리면 찾지 않는다
    assert RR.limit_phrase(once, view("가나 입원 시 (입원 1회당 2회 한도)")) is None
    assert RR.limit_phrase(once, view("가나 시 (재입원 1회당 1회 한도)")) is None
    # 지급단위 1회당 칸은 "입원 1회당 1회"를 한도로 보고 지급단위로 세지 않는다
    assert RR.amount_unit(view("가나", "입원 1회당 1회 한도 20만원")) is None


# ---------------------------------------------------------------------------
# 감액예외: "단,"으로 이어지는 단서 문장
# ---------------------------------------------------------------------------

CUT = [{"기간": 1, "단위": "년", "값": 50, "값기준": "보험금"}]


def test_exception_after_dan_joins_the_cut_sentence_before_it():
    amount = "검사 1회당3만원 (다만, 첫 가입일부터 1년 미만이면 50% 감액 지급. 단, 재해가 원인이면 100% 지급)"
    c = view("가나 검사를 받은 경우", amount)
    v = reading(기준가입금액만원=None, 지급액만원=3, 지급단위="1회당", 감액=CUT,
                감액예외=[{"대상": "재해", "자리": "지급금액"}])
    cell, missing = RR.exception_cell(v, c, None)
    assert missing == []
    assert cell == "다만, 첫 가입일부터 1년 미만이면 50% 감액 지급. 단, 재해가 원인이면 100% 지급"
    assert RR.machine_checks(c, v)[0] == []


def test_exception_clause_alone_is_still_preferred():
    # 단서 문장 안에 감액을 가리키는 말이 있으면 앞 문장을 붙이지 않는다(지금과 같다)
    amount = "1만원 (첫해 50% 지급, 단, 재해는 감액하지 않음)"
    c = view("가나 입원", amount)
    v = reading(감액=CUT, 감액예외=[{"대상": "재해", "자리": "지급금액"}])
    assert RR.exception_cell(v, c, None) == ("재해는 감액하지 않음", [])


def test_exception_after_dan_without_cut_sentence_is_still_missing():
    # 앞 문장에도 감액을 가리키는 말이 없으면 여전히 찾지 못한다
    c = view("가나 검사를 받은 경우", "3만원 (가나 검사 연 1회. 단, 재해가 원인이면 100% 지급)")
    v = reading(감액=CUT, 감액예외=[{"대상": "재해", "자리": "지급금액"}])
    assert RR.exception_cell(v, c, None)[1] == ["감액예외 재해"]
    # 대상 낱말이 단서 문장에 없고 앞 문장에만 있으면 붙이지 않는다
    c = view("가나 검사를 받은 경우", "3만원 (재해가 원인이면 100% 지급. 단, 첫해는 50% 감액)")
    v = reading(감액=CUT, 감액예외=[{"대상": "재해", "자리": "지급금액"}])
    assert RR.exception_cell(v, c, None)[1] == ["감액예외 재해"]
