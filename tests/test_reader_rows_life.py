"""생명보험사 시험 판독(삼성생명, KB라이프생명)에서 나온 기계 검사의 거짓 표시와 견줌 보고서의 표기.

한도 구절("연1회한", "각각 1회의 진단에 한함"), 숫자 없는 "회당", 수술은 1회당이고 수술 이외 치료에만 연간 한도가 걸리는
지급사유, 갱신계약에는 감액을 적용하지 않는다는 주석, 둘다모름 칸의 표기. 문구와 이름, 금액은 모두 지어낸 것이다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import compare_readers  # noqa: E402
from postlife.extract import reader_rows as RR  # noqa: E402


def view(reason, amount, name="가나 수술보험금", number="R001-1"):
    return RR.CoverView(number, name, reason, amount, 10)


def piece_of(cover, notes=()):
    return RR.PieceView(1, "가나특약", ("가나특약",), "선택특약", "", 10, 10, (cover,), tuple(notes))


def reading(**values):
    return {**RR.DEFAULTS, "번호": "R001-1", "쪽": 10, "꼴": RR.AMOUNT, "기준가입금액만원": 1, "지급액만원": 1, **values}


ANNUAL = {"앞말": "연간", "수": 1, "단위": "회"}


def test_short_annual_lead_and_bare_per_time_unit_are_found():
    c = view("가나 다라로 수술한 때 (해마다 연1회한)", "회당 1만원")
    assert RR.limit_phrase(ANNUAL, c) == "연1회한"
    assert RR.unit_phrase("1회당", c) == "회당"
    assert RR.machine_checks(c, reading(지급단위="1회당", 한도=[ANNUAL])) == ([], [])
    spaced = view("가나 수술 시 (연 1회에 한함)", "수술 1회당 1만원")
    assert RR.limit_phrase(ANNUAL, spaced) == "연 1회에 한함"
    assert RR.unit_phrase("1회당", spaced) == "수술 1회당"
    each = view("가나 수술 시 (치료구분별 각각연간 1회한)", "1만원")
    # 2026-11-24부터 "각각" 앞의 한정어("치료구분별")도 함께 자른다. 전에는 "각각연간 1회한"이었다
    assert RR.limit_phrase(ANNUAL, each) == "치료구분별 각각연간 1회한"


def test_annual_lead_does_not_hit_yeon_inside_a_word_or_other_counts():
    inside = view("가나 수술 시 전연1회 다라", "회당 1만원")
    assert RR.limit_phrase(ANNUAL, inside) is None
    assert "구절없음: 한도 연간 1회" in RR.machine_checks(inside, reading(지급단위="1회당", 한도=[ANNUAL]))[0]
    for amount in ("2회당 1만원", "사회당 1만원"):
        assert RR.unit_phrase("1회당", view("가나 수술 시", amount)) is None


def test_bare_limit_may_name_what_it_limits_before_the_tail():
    bare = {"앞말": "없음", "수": 1, "단위": "회"}
    c = view("가나병, 다라병으로 진단된 때 (각각 1회의 진단에 한함)", "1,000만원", name="가나 진단보험금")
    assert RR.limit_phrase(bare, c) == "각각 1회의 진단에 한함"
    v = reading(기준가입금액만원=1000, 지급액만원=1000, 한도=[bare])
    assert RR.machine_checks(c, v) == ([], [])
    # 꼬리말이 없으면 여전히 구절이 없다("1회 치료" 같은 다른 숫자에 걸리지 않는다)
    assert RR.limit_phrase(bare, view("가나 1회 치료 시", "1만원")) is None
    # 사이에 말이 낀 꼴은 끝이 한도를 뜻하는 낱말일 때만 받는다. 문장 속의 "…한 경우"에 걸리지 않는다
    for sentence in ("1회의 가나금을 지급한 경우", "최초 1회의 진단을 받은 때 한 번만 지급", "1회의 입원을 한 경우"):
        assert RR.limit_phrase(bare, view(sentence, "1만원")) is None, sentence
    assert RR.limit_phrase(bare, view("가나 치료 시(1회한)", "1만원")) == "1회한"
    assert RR.limit_phrase(bare, view("가나 치료 시 1회에 한함", "1만원")) == "1회에 한함"


SURGERY = "가나병 치료 시 (수술은 수술 1회당 지급, 수술 이외 치료는 종류별 연간 1회한)"


def test_surgery_each_time_line_is_not_marked_for_the_other_treatments_limit():
    surgery = view(SURGERY, "보험가입금액", name="수술")
    ratio = {**RR.DEFAULTS, "번호": "R001-1", "쪽": 10, "꼴": RR.RATIO, "지급률": 100}
    assert RR.machine_checks(surgery, {**ratio, "지급단위": "1회당"}) == ([], [])
    # 수술 이외 치료 줄(지급단위가 비어 있음)은 한도가 비면 그대로 표시한다
    other = view(SURGERY, "보험가입금액", name="방사선치료", number="R001-2")
    marks = RR.machine_checks(other, {**ratio, "번호": "R001-2"})[1]
    assert f"{RR.MISSED}: 한도를 가리키는 말이 있는데 한도가 비어 있음" in marks
    assert RR.machine_checks(other, {**ratio, "번호": "R001-2", "한도": [ANNUAL]}) == ([], [])
    # 수술 1회당이 없는 지급사유는 지급단위가 1회당이어도 한도 표시를 낸다
    plain = view("가나병 치료 시 (연간 1회한)", "보험가입금액 1회당", name="수술")
    assert any("한도가 비어 있음" in m for m in RR.machine_checks(plain, {**ratio, "지급단위": "1회당"})[1])


RENEWAL_NOTE = "2. 처음 계약의 가입 1년 안 감액 규정은 갱신계약에는 적용하지 않음."


def test_renewal_note_needs_a_renewal_exception_on_cut_lines():
    c = view("가나병으로 진단 확정된 경우", "1년이내: 500만원\n1년초과: 1,000만원", name="가나 진단보험금")
    p = piece_of(c, ["1. 납입면제 안내", RENEWAL_NOTE])
    cut = [{"기간": 1, "단위": "년", "값": 500, "값기준": "만원"}]
    v = reading(기준가입금액만원=1000, 지급액만원=1000, 감액=cut)
    marks = RR.machine_checks(c, v, p)[1]
    assert marks == [f"{RR.MISSED}: 주석에 갱신계약에는 감액을 적용하지 않는다는 문장이 있는데 감액예외에 갱신계약이 없음"]
    ok = {**v, "감액예외": [{"대상": "갱신계약", "자리": "주석"}]}
    assert RR.machine_checks(c, ok, p) == ([], [])
    # 주석이 없거나 감액이 없는 줄은 보지 않는다
    assert RR.machine_checks(c, v, piece_of(c, ["1. 납입면제 안내"])) == ([], [])
    flat = view("가나병으로 진단 확정된 경우", "1,000만원", name="가나 진단보험금")
    assert RR.machine_checks(flat, reading(기준가입금액만원=1000, 지급액만원=1000), piece_of(flat, [RENEWAL_NOTE])) == ([], [])


def test_target_without_its_exclusion_brackets_is_marked():
    reason = "보험기간 중 가암(나암, 다암 제외)으로 진단 확정된 경우"
    assert RR.exclusion_dropped("가암", reason)
    assert not RR.exclusion_dropped("가암(나암, 다암 제외)", reason)
    assert not RR.exclusion_dropped("가암", "가나보장개시일 이후 가암(전이포함)으로 진단 확정된 경우")
    assert RR.exclusion_dropped("가암", "가암(나암(초기) 제외) 진단 확정 후 수술 시")
    c = view(reason, "보험가입금액", name="가나 진단특약")
    ratio = {**RR.DEFAULTS, "번호": "R001-1", "쪽": 10, "꼴": RR.RATIO, "지급률": 100}
    marks = RR.machine_checks(c, {**ratio, "대상": "가암"})[1]
    assert marks == ["대상: 지급사유에서 대상 바로 뒤에 제외가 든 괄호가 이어지는데 대상에 없음"]
    assert RR.machine_checks(c, {**ratio, "대상": "가암(나암, 다암 제외)"}) == ([], [])
    # 30자가 넘어 대상을 모름으로 올린 줄은 보지 않는다
    unknown = {**ratio, "대상": "가암", "모름": [{"칸": "대상", "이유": "제외 단서까지 30자를 넘음"}]}
    assert RR.machine_checks(c, unknown) == ([], [])


def test_summary_names_both_unknown_fields_apart_from_differing_ones():
    c = {"번호": "R001-1", "쪽": 10, "급부명": "가나 진단보험금", "이름같은줄갈림": False, "대상확인필요": False,
         "자동판정": RR.NEEDS_JUDGE, "sonnet": {}, "opus": {},
         "일치": {"꼴": RR.SAME, "면책일수": RR.BOTH_UNKNOWN, "대상": RR.SAME},
         "기계검사": {"sonnet": {"문제": [], "표시": []}, "opus": {"문제": [], "표시": []}}}
    d = {**c, "번호": "R001-2", "일치": {"꼴": RR.SAME, "면책일수": RR.BOTH_UNKNOWN, "대상": RR.DIFF}}
    text = compare_readers.summary([{"묶음": "X_B01", "판독": ["sonnet", "opus"], "형식 문제": {}, "줄": [c, d]}])
    assert "- R001-1 (10쪽) 가나 진단보험금 | 다른 칸: 없음 | 둘다모름: 면책일수" in text
    assert "- R001-2 (10쪽) 가나 진단보험금 | 다른 칸: 대상 | 둘다모름: 면책일수" in text
