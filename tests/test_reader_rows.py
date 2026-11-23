"""초기 적재 두 판독의 값 검사, 견줌, 기계 검사, 행 만들기. 자료는 모두 지어낸 것이다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import compare_readers  # noqa: E402
import split_pieces  # noqa: E402
from postlife import ids  # noqa: E402
from postlife.extract import reader_rows as RR  # noqa: E402
from postlife.extract import table_rules as T  # noqa: E402
from postlife.validate import check_rows  # noqa: E402

VID = "TEST_X1_abcdef"


def cover(name, reason, amount, page=10):
    return {"보장명": name, "지급사유": reason, "지급금액": amount, "쪽": page, "적용범위": ""}


def piece(title, covers, first=10, last=10, label="선택계약", names=None, segment=None):
    out = {"특별약관": title, "구분": label, "적용범위": "", "첫쪽": first, "끝쪽": last, "주계약": label == "기본계약",
           "특약명들": names or [title], "세부보장": covers}
    if segment is not None:
        out["형"] = segment
    return out


def pieces_file(pieces, notes=()):
    return {"형식": RR.PIECES_FORMAT, "출처": {"문서": "TEST1_가상상품_상품요약서"}, "주석": list(notes), "조각": pieces}


def reading(number, **values):
    return {**RR.DEFAULTS, "번호": number, "쪽": 10, "꼴": RR.RATIO, "지급률": 100, **values}


SAMPLE = pieces_file([
    piece("가나 진단비", [cover("가나 진단비", "가나병으로 진단 확정된 경우 (최초 1회한)",
                                 "가입금액(가입 1년 안에는 가입금액의 50%)")], label="기본계약"),
    piece("다라 수술비/갱신형 다라 수술비", [cover("다라 수술비/갱신형 다라 수술비", "다라병으로 수술을 받은 경우 (연간 3회한)",
                                                  "가입금액의 20%")], names=["다라 수술비", "갱신형 다라 수술비"]),
    piece("마바 치료비", [cover("마바 치료비", "마바병 치료(관혈)", "가입금액"),
                          cover("마바 치료비", "마바병 치료(비관혈)", "가입금액"),
                          cover("사아 입원일당", "사아병으로 입원한 경우", "1일당 가입금액(입원 30일 한도)")]),
    piece("자차 치료비", [cover("자차 치료비", "자차병 첫 치료", "가입금액"),
                          cover("자차 치료비", "자차병 재치료", "가입금액의 10%")]),
], notes=[{"쪽": 11, "형": "", "특약머리": "", "글": "주1) 가나 사고로 생긴 경우에는 감액하지 않음"}])


def views():
    return RR.load_pieces(SAMPLE)


# ---------------------------------------------------------------------------
# 꼴 검사
# ---------------------------------------------------------------------------

def test_format_accepts_a_minimal_line_and_fills_defaults():
    values, problems = RR.parse_readings({"형식": RR.FORMAT, "값": [{"번호": "R001-1", "쪽": 10, "꼴": RR.RATIO, "지급률": 100}]})
    assert problems == []
    assert values["R001-1"]["감액"] == [] and values["R001-1"]["면책일수"] == 0


def test_format_rejects_unknown_values_and_long_words():
    assert any("꼴" in p for p in RR.check_format({"번호": "R001-1", "쪽": 1, "꼴": "비율"}))
    assert any("행없음사유" in p for p in RR.check_format({"번호": "R001-1", "쪽": 1, "꼴": RR.NO_ROW}))
    assert any("정의되지 않은 칸" in p for p in RR.check_format({**reading("R001-1"), "근거문구": "가나"}))
    assert any("감액대상" in p for p in RR.check_format(reading("R001-1", 감액대상="가" * 40)))
    assert any("모름 이유" in p for p in RR.check_format({"번호": "R001-1", "쪽": 1, "꼴": RR.UNKNOWN}))
    bad_cut = reading("R001-1", 감액=[{"기간": 1, "단위": "년", "값": 50, "값기준": "만원"}])
    assert any("만원" in p for p in RR.check_format(bad_cut))


def test_parse_drops_bad_and_repeated_lines():
    data = {"형식": RR.FORMAT, "값": [reading("R001-1"), reading("R001-1"), {"번호": "x"}]}
    values, problems = RR.parse_readings(data)
    assert list(values) == ["R001-1"] and len(problems) == 2


# ---------------------------------------------------------------------------
# 견줌
# ---------------------------------------------------------------------------

def test_cut_written_two_ways_is_the_same_cut():
    a = reading("R001-1", 지급률=20, 감액=[{"기간": 1, "단위": "년", "값": 10, "값기준": "가입금액"}])
    b = reading("R001-1", 지급률=20, 감액=[{"기간": 12, "단위": "개월", "값": 50, "값기준": "보험금"}])
    assert RR.cut_steps(a) == ((12, 0.5),)
    assert RR.agreed(RR.compare_one(a, b))


def test_compare_marks_different_and_unknown_fields():
    a = reading("R001-1", 한도=[{"앞말": "연간", "수": 3, "단위": "회"}])
    b = reading("R001-1", 한도=[{"앞말": "최초", "수": 1, "단위": "회"}], 모름=[{"칸": "면책일수", "이유": "쪽에 없음"}])
    states = RR.compare_one(a, b)
    assert states["한도"] == RR.DIFF and states["면책일수"] == RR.ONE_UNKNOWN and states["지급률"] == RR.SAME
    assert RR.compare_one(None, None)["꼴"] == RR.BOTH_UNKNOWN


def test_no_row_lines_compare_the_kind_and_the_kept_fields():
    a = {**RR.DEFAULTS, "번호": "R001-1", "쪽": 1, "꼴": RR.NO_ROW, "행없음사유": "회차별지급률", "지급률": 100}
    b = {**RR.DEFAULTS, "번호": "R001-1", "쪽": 1, "꼴": RR.NO_ROW, "행없음사유": "회차별지급률"}
    assert RR.compare_one(a, b) == {"꼴": RR.SAME, "행없음사유": RR.SAME, "면책일수": RR.SAME, "보장개시일": RR.SAME,
                                    "한도": RR.SAME}
    c = {**b, "면책일수": 90, "보장개시일": "가나보장개시일", "한도": [{"앞말": "연간", "수": 1, "단위": "회"}]}
    states = RR.compare_one(b, c)
    assert states["면책일수"] == states["보장개시일"] == states["한도"] == RR.DIFF


def test_new_no_row_kinds_are_accepted():
    for kind in ("단위당단가", "조문별한도"):
        assert RR.check_format({"번호": "R001-1", "쪽": 1, "꼴": RR.NO_ROW, "행없음사유": kind}) == []


def test_targets_match_by_the_benefit_id_rule():
    a = reading("R001-1", 대상="「가나암」또는「다라암」")
    b = reading("R001-1", 대상="가나암, 다라암")
    assert RR.agreed(RR.compare_one(a, b))
    assert RR.compare_one(a, reading("R001-1", 대상="가나암"))["대상"] == RR.DIFF
    assert RR.target_text("「가나암」또는「다라암」") == "가나암 또는 다라암"
    assert any("대상" in p for p in RR.check_format(reading("R001-1", 대상="가" * 31)))


# ---------------------------------------------------------------------------
# 기계 검사
# ---------------------------------------------------------------------------

def test_numbers_must_be_written_in_the_cover():
    p = views()[0]
    c = p.covers[0]
    good = reading("R001-1", 감액=[{"기간": 1, "단위": "년", "값": 50, "값기준": "가입금액"}],
                   한도=[{"앞말": "최초", "수": 1, "단위": "회"}])
    assert RR.machine_checks(c, good, p) == ([], [])
    wrong = reading("R001-1", 감액=[{"기간": 2, "단위": "년", "값": 40, "값기준": "가입금액"}])
    problems, marks = RR.machine_checks(c, wrong, p)
    assert "숫자없음: 감액 기간 2년" in problems and "숫자없음: 감액 값 40%" in problems
    assert "남은 숫자: 50%" in marks


def test_number_boundaries_are_kept():
    c = RR.CoverView("R009-1", "가나", "가나병 (11년 이내)", "가입금액의 120%", 3)
    problems, _ = RR.machine_checks(c, reading("R009-1", 지급률=20, 감액=[{"기간": 1, "단위": "년", "값": 10, "값기준": "가입금액"}]))
    assert "숫자없음: 지급률 20%" in problems and "숫자없음: 감액 기간 1년" in problems


def test_unused_rate_is_marked_but_condition_thresholds_are_not():
    c = RR.CoverView("R009-1", "가나", "장해율이 50% 이상인 경우", "가입금액의 30%", 3)
    assert RR.machine_checks(c, reading("R009-1", 지급률=30))[1] == []
    _, marks = RR.machine_checks(c, reading("R009-1", 지급률=100))
    assert "남은 숫자: 30%" in marks


def test_leftover_numbers_come_only_from_the_amount_cell():
    # 진단 기준 수치는 지급사유 칸에 적힌다. 지급액이 아니므로 남은 숫자로 세지 않는다
    c = RR.CoverView("R009-1", "가나수치 7.0%이상", "가나수치 7.0%로 진단확정시(최초 1회한)", "가입금액", 3)
    assert RR.machine_checks(c, reading("R009-1", 한도=[{"앞말": "최초", "수": 1, "단위": "회"}])) == ([], [])


def test_unit_follows_the_amount_cell_first():
    c = RR.CoverView("R009-1", "가나 통원일당", "가나병으로 통원하였을 경우 통원1회당 지급", "1일당 가입금액", 3)
    assert RR.amount_unit(c) == "1일당"
    assert RR.machine_checks(c, reading("R009-1", 지급단위="1일당")) == ([], [])
    _, marks = RR.machine_checks(c, reading("R009-1", 지급단위="1회당"))
    assert "지급단위: 지급금액 칸의 단위는 1일당" in marks
    # 지급금액 칸에 단위가 없으면 지급사유 칸을 따른다. "1회 입원당 120일"은 한도 앞말이라 단위로 보지 않는다
    d = RR.CoverView("R009-2", "가나 입원일당", "가나병으로 입원한 경우 1일당 지급", "가입금액(1회 입원당 120일 한도)", 3)
    assert RR.amount_unit(d) is None
    assert RR.machine_checks(d, reading("R009-2", 지급단위="1일당",
                                        한도=[{"앞말": "1회입원당", "수": 120, "단위": "일"}])) == ([], [])


def test_cut_written_as_the_share_taken_away():
    c = RR.CoverView("R009-1", "가나", "가나병 ※ 1년 미만은 75% 감액 지급", "가입금액", 3)
    v = reading("R009-1", 감액=[{"기간": 1, "단위": "년", "값": 25, "값기준": "보험금"}])
    assert RR.machine_checks(c, v) == ([], [])
    assert RR.cut_steps(v) == ((12, 0.25),)


def test_cut_ranges_are_checked():
    c = RR.CoverView("R009-1", "가나", "가나", "가입금액(90일 전 가입금액의 60%, 1년 전 가입금액의 50%)", 3)
    v = reading("R009-1", 감액=[{"기간": 90, "단위": "일", "값": 60, "값기준": "가입금액"},
                                {"기간": 1, "단위": "년", "값": 50, "값기준": "가입금액"}])
    assert "범위: 두 감액 구간의 기간이 겹치거나 짧은 기간의 비율이 더 큼" in RR.machine_checks(c, v)[0]


def test_waiting_days_need_a_source():
    c = RR.CoverView("R009-1", "가나 진단비", "가나보장개시일 이후 가나병으로 진단 확정된 경우", "가입금액", 3)
    v = reading("R009-1", 면책일수=90, 보장개시일="가나보장개시일")
    assert any(p.startswith("숫자없음: 면책일수 90") for p in RR.machine_checks(c, v)[0])
    p = RR.PieceView(9, "가나 진단비", (), "", "", 3, 3, (c,), ("주1) 가나보장개시일은 계약일부터 90일이 지난 다음날",))
    assert RR.machine_checks(c, v, p)[0] == []
    page = {5: "…가나보장개시일은 계약한 날부터 90일이 지난 날…"}
    v2 = {**v, "면책근거쪽": 5}
    assert RR.machine_checks(c, v2, None, page)[0] == []
    assert any("5쪽" in x for x in RR.machine_checks(c, {**v2, "면책일수": 30}, None, page)[0])


LISTED = ("- 가나보장개시일, 다가나보장개시일, 라마 진단보장\n개시일 및 바사보장개시일은 보험나이 15세 이상인 경우 계약일부터 "
          "그날을 포함하여 90일이 지난날의 다음날로 하며, 아자보장개시일 및 차카보장개시일은 계약일부터 그날을 포함하여 "
          "1년이 지난날의 다음날로 합니다.")


def test_waiting_days_from_a_listing_sentence_pair_each_name():
    assert RR.wait_days_on_page("라마진단보장개시일", LISTED) == {90}
    assert RR.wait_days_on_page("차카보장개시일", LISTED) == {365}
    assert RR.wait_days_on_page("아자보장개시일", LISTED) == {365}
    # "다가나보장개시일" 속의 "가나보장개시일"을 따로 세지 않는다. 맨 앞 이름은 그 나열의 날수와 짝짓는다
    assert RR.wait_days_on_page("가나보장개시일", LISTED) == {90}
    assert RR.wait_days_on_page("타파보장개시일", LISTED) == set()
    pair = "※ 가나보장개시일과 사아보장개시일은 계약일부터 90일이 지난 다음날"
    assert RR.wait_days_on_page("가나보장개시일", pair) == RR.wait_days_on_page("사아보장개시일", pair) == {90}


CASE_LISTED = ("가나보장개시일, 다라 보장개시일 및 마바보장개시일의 경우 이 상품 보장개시일은 가입한 날에서 90일\n"
               "뒤로 정하고, 사아보장개시일 및 자차보장개시일의 경우 이 상품\n보장개시일은 가입한 날에서 30일 뒤로 "
               "정하며, 카타보장개시일의 경우 이 상품 보장개시일은 가입한 날에서 1년 뒤로 정한다.")


def test_waiting_days_from_a_listing_that_ends_with_the_case_phrase():
    # 나열의 마지막 이름 바로 뒤가 "의 경우 회사의 보장개시일은"이어도 그 나열의 날수와 짝짓는다
    assert RR.wait_days_on_page("가나보장개시일", CASE_LISTED) == {90}
    assert RR.wait_days_on_page("다라보장개시일", CASE_LISTED) == {90}
    assert RR.wait_days_on_page("마바보장개시일", CASE_LISTED) == {90}
    assert RR.wait_days_on_page("사아보장개시일", CASE_LISTED) == {30}
    assert RR.wait_days_on_page("자차보장개시일", CASE_LISTED) == {30}
    assert RR.wait_days_on_page("카타보장개시일", CASE_LISTED) == {365}
    assert RR.wait_days_on_page("파하보장개시일", CASE_LISTED) == set()
    c = RR.CoverView("R009-1", "카타 간병비", "카타보장개시일 이후 카타병으로 진단확정시", "가입금액", 3)
    v = reading("R009-1", 면책일수=365, 보장개시일="카타보장개시일", 면책근거쪽=9)
    assert RR.machine_checks(c, v, None, {9: CASE_LISTED})[0] == []
    assert RR.machine_checks(c, {**v, "면책일수": 90}, None, {9: CASE_LISTED})[0] != []


def test_waiting_days_from_a_waiting_table_beside_the_name():
    table = "보장명 면책기간 1년경과시점 전일 이전\n가나진단비 90일 가입금액의 50%\n다라진단비 - 가입금액의 50%\n"
    assert RR.wait_days_on_page(["가나보장개시일", "가나진단비"], table) == {90}
    assert RR.wait_days_on_page(["다라진단비"], table) == set()
    c = RR.CoverView("R009-1", "가나진단비", "가나보장개시일 이후 가나병으로 진단확정시", "가입금액", 3)
    v = reading("R009-1", 면책일수=90, 보장개시일="가나보장개시일", 면책근거쪽=4)
    # 표에는 보장개시일 이름이 없고 보장명과 날수만 있다. 보장개시일 낱말은 그 줄의 글자에 있으면 된다
    assert RR.machine_checks(c, v, None, {4: table})[0] == []
    assert RR.machine_checks(c, {**v, "면책일수": 365}, None, {4: table})[0] != []


def test_appended_remark_is_not_the_line_evidence():
    remark = "\n※ 가나보장개시일은 계약일부터 90일이 지난 다음날"
    plain = RR.CoverView("R009-1", "가나 치료비", "보험기간 중 다라병으로 치료를 받은 경우" + remark, "가입금액", 3)
    named = RR.CoverView("R009-2", "가나 치료비", "보험기간 중 가나보장개시일 이후 가나병으로 치료를 받은 경우" + remark,
                         "가입금액", 3)
    # 본문이 보장개시일을 가리키지 않는 줄은 붙은 풀이가 있어도 면책 0이 맞다
    assert RR.machine_checks(plain, reading("R009-1")) == ([], [])
    assert RR.machine_checks(plain, reading("R009-1", 면책일수=90, 보장개시일="가나보장개시일"))[0] != []
    # 본문이 보장개시일을 가리키는 줄은 풀이의 날수가 근거가 되고, 0이면 표시가 난다
    assert RR.machine_checks(named, reading("R009-2", 면책일수=90, 보장개시일="가나보장개시일")) == ([], [])
    marks = RR.machine_checks(named, reading("R009-2"))[1]
    assert any(m.startswith("지급사유 본문이 보장개시일을 가리키는데 면책일수가 0") for m in marks)
    # 줄 사이로 옮겨 온 위첨자 "※보험기간 중 …"은 뜻을 정하는 말이 없으므로 본문이다
    moved = "※보험기간 중 가나보장개시일 이후 가나병으로 진단확정시" + remark
    assert RR.split_remarks(moved) == ("※보험기간 중 가나보장개시일 이후 가나병으로 진단확정시",
                                       "※ 가나보장개시일은 계약일부터 90일이 지난 다음날")


def test_no_row_lines_still_check_waiting_days_and_limits():
    c = RR.CoverView("R009-1", "가나 치료비", "가나보장개시일 이후 가나병 치료시(연간 1회한)\n※ 가나보장개시일은 "
                     "계약일부터 90일이 지난 다음날", "진단 후 경과 연도별 해당금액", 3)
    v = {**RR.DEFAULTS, "번호": "R009-1", "쪽": 3, "꼴": RR.NO_ROW, "행없음사유": "경과기간별지급률"}
    full = {**v, "면책일수": 90, "보장개시일": "가나보장개시일", "한도": [{"앞말": "연간", "수": 1, "단위": "회"}]}
    assert RR.machine_checks(c, full) == ([], [])
    assert RR.machine_checks(c, v)[1] != []                        # 면책을 비워 두면 표시
    assert "구절없음: 한도 최초 1회" in RR.machine_checks(c, {**full, "한도": [{"앞말": "최초", "수": 1, "단위": "회"}]})[0]


def test_limit_and_unit_phrases_are_cut_from_the_text():
    p = views()[2]
    c = p.covers[2]
    assert RR.unit_phrase("1일당", c) == "1일당"
    assert RR.limit_phrase({"앞말": "없음", "수": 30, "단위": "일"}, c) == "30일 한도"
    assert RR.limit_phrase({"앞말": "연간", "수": 30, "단위": "일"}, c) is None
    problems, _ = RR.machine_checks(c, reading("R003-3", 한도=[{"앞말": "최초", "수": 1, "단위": "회"}]))
    assert "구절없음: 한도 최초 1회" in problems and "구절없음: 지급단위 " not in problems


def test_exception_clause_comes_from_the_note():
    p = RR.PieceView(9, "가나", (), "", "", 11, 11, (RR.CoverView("R009-1", "가나", "가나병 주1)", "가입금액(1년 전 가입금액의 50%)", 11),),
                     ("주1) 가나 사고로 생긴 경우에는 감액하지 않음",))
    v = reading("R009-1", 감액=[{"기간": 1, "단위": "년", "값": 50, "값기준": "가입금액"}],
                감액예외=[{"대상": "가나 사고", "자리": "주석"}])
    assert RR.exception_cell(v, p.covers[0], p) == ("가나 사고로 생긴 경우에는 감액하지 않음", [])
    missing = {**v, "감액예외": [{"대상": "재해", "자리": "주석"}]}
    assert "구절없음: 감액예외 재해" in RR.machine_checks(p.covers[0], missing, p)[0]


def test_cut_for_some_cases_moves_its_clause_to_the_exception_cell():
    c = RR.CoverView("R009-1", "가나", "가나", "가입금액(소가나는 1년 전 가입금액의 50%)", 3)
    v = reading("R009-1", 감액=[{"기간": 1, "단위": "년", "값": 50, "값기준": "가입금액"}], 감액대상="소가나")
    assert RR.exception_cell(v, c, None)[0] == "소가나는 1년 전 가입금액의 50%"


def test_same_name_covers_with_different_values_are_found():
    found = RR.same_name_splits(views(), {"R004-1": reading("R004-1"), "R004-2": reading("R004-2", 지급률=10)})
    assert found == {"R004/자차 치료비": ["R004-1", "R004-2"]}
    assert RR.same_name_unlabeled(views(), {"R004-1": reading("R004-1"), "R004-2": reading("R004-2")}) \
        == {"R004/자차 치료비": ["R004-1", "R004-2"]}


def test_same_name_covers_with_different_targets_are_not_a_split():
    values = {"R004-1": reading("R004-1", 대상="첫 치료"), "R004-2": reading("R004-2", 지급률=10, 대상="재치료")}
    assert RR.same_name_splits(views(), values) == {} and RR.same_name_unlabeled(views(), values) == {}
    same = {"R004-1": reading("R004-1", 대상="재 치료"), "R004-2": reading("R004-2", 지급률=10, 대상="재치료")}
    assert RR.same_name_unlabeled(views(), same) == {"R004/자차 치료비": ["R004-1", "R004-2"]}
    assert RR.same_name_splits(views(), same) == {"R004/자차 치료비": ["R004-1", "R004-2"]}
    c = views()[3].covers[0]
    assert "낱말없음: 대상" in RR.machine_checks(c, reading("R004-1", 대상="다른 병"))[0]


# ---------------------------------------------------------------------------
# 형과 종형
# ---------------------------------------------------------------------------

def test_segment_maps_to_variants_by_name_head():
    names = ["가형 1종 315", "가형 1종 325", "나형 1종"]
    assert RR.variants_for("가형", names) == names[:2]
    assert RR.variants_for("공통", names) == names
    assert RR.variants_for("", names) == names
    assert RR.variants_for("다형", names) == []


def test_notes_attach_by_head_page_or_marker():
    head = {"쪽": 50, "형": "가형", "특약머리": "가나 특약", "글": "주) 가"}
    page = {"쪽": 12, "형": "가형", "특약머리": "", "글": "주1) 나"}
    later = {"쪽": 40, "형": "가형", "특약머리": "", "글": "주1) 다"}
    other = {"쪽": 41, "형": "나형", "특약머리": "", "글": "주1) 라"}
    p = piece("가나 특약", [cover("가", "가나", "가입금액")], 12, 12, segment="가형")
    assert RR.note_owners(p, [head, page, later, other]) == ["주) 가", "주1) 나"]
    marked = piece("마바 특약", [cover("마", "마바 주1)", "가입금액")], 20, 20, segment="가형")
    assert RR.note_owners(marked, [head, page, later, other]) == ["주1) 다"]
    assert RR.note_owners(piece("사아 특약", [cover("사", "사아", "가입금액")], 20, 20, segment="가형"), [later]) == []


# ---------------------------------------------------------------------------
# 행 만들기
# ---------------------------------------------------------------------------

def finals():
    return {
        "R001-1": reading("R001-1", 감액=[{"기간": 1, "단위": "년", "값": 50, "값기준": "가입금액"}],
                          한도=[{"앞말": "최초", "수": 1, "단위": "회"}]),
        "R002-1": reading("R002-1", 지급률=20, 한도=[{"앞말": "연간", "수": 3, "단위": "회"}]),
        "R003-1": reading("R003-1"),
        "R003-2": reading("R003-2"),
        "R003-3": reading("R003-3", 지급단위="1일당", 한도=[{"앞말": "없음", "수": 30, "단위": "일"}]),
        "R004-1": reading("R004-1"),
        "R004-2": reading("R004-2", 지급률=10),
    }


def test_rows_follow_the_table_rule_ids_and_columns():
    built = RR.build_rows(VID, views(), finals(), renewal_years=20)
    riders = {r["원시특약명"]: r for r in built.riders}
    assert riders["가나 진단비"]["담보구분"] == "주계약"
    assert riders["갱신형 다라 수술비"]["갱신여부"] is True and riders["갱신형 다라 수술비"]["갱신주기년"] == 20
    assert riders["다라 수술비"]["갱신여부"] is False
    rows = {b["원시급부명"] + "|" + b["특약ID"][-6:]: b for b in built.benefits}
    first = next(b for b in built.benefits if b["원시급부명"] == "가나 진단비")
    expected = T.benefit_row(riders["가나 진단비"]["특약ID"],
                             T.Reading("가나 진단비", percent=100.0, steps=(T.Step(12, 0.5),), limit="최초 1회한"), "주급부", 10)
    assert first == expected
    # 이름이 여럿인 조각의 세부보장 하나는 특약 이름마다 그 이름으로 급부 행이 생긴다
    assert {b["원시급부명"] for b in built.benefits if b["기준지급금액만원"] == 20.0} == {"다라 수술비", "갱신형 다라 수술비"}
    daily = next(b for b in built.benefits if b["원시급부명"] == "사아 입원일당")
    assert daily["지급횟수제한"] == "1일당 / 30일 한도" and daily["급부역할"] == "대등복합"
    assert check_rows("sys_급부", built.benefits) == {} and check_rows("sys_특약", built.riders) == {}
    assert len(rows) == len(built.benefits)


def test_same_name_covers_share_one_row_only_when_rows_are_equal():
    built = RR.build_rows(VID, views(), finals(), renewal_years=20)
    same = [b for b in built.benefits if b["원시급부명"] == "마바 치료비"]
    assert len(same) == 1 and built.numbers[same[0]["급부ID"]] == ("R003-1", "R003-2")
    assert not [b for b in built.benefits if b["원시급부명"] == "자차 치료비"]
    assert built.skipped["R004-1"].startswith("이름이 같은 세부보장(R004-1, R004-2)의 값이 서로 다름")


def test_unrepresentable_and_unknown_lines_make_no_row():
    values = finals()
    values["R003-3"] = {**RR.DEFAULTS, "번호": "R003-3", "쪽": 10, "꼴": RR.NO_ROW, "행없음사유": "항목별금액표"}
    values["R001-1"] = reading("R001-1", 모름=[{"칸": "감액", "이유": "칸이 흐림"}])
    del values["R002-1"]
    built = RR.build_rows(VID, views(), values, renewal_years=20)
    assert built.skipped["R003-3"] == "스키마가 담지 못하는 꼴: 항목별금액표"
    assert built.skipped["R001-1"] == "모름인 칸: 감액" and built.skipped["R002-1"] == "판독 값 없음"
    names = {b["원시급부명"] for b in built.benefits}
    assert "사아 입원일당" not in names and "가나 진단비" not in names


def test_amount_lines_use_the_amount_columns():
    data = pieces_file([piece("가나 위로금", [cover("가나 위로금", "가나 사고 때 (기준 가입금액 1,000만원)", "300만원")])])
    v = {**RR.DEFAULTS, "번호": "R001-1", "쪽": 10, "꼴": RR.AMOUNT, "기준가입금액만원": 1000, "지급액만원": 300}
    built = RR.build_rows(VID, RR.load_pieces(data), {"R001-1": v})
    row = built.benefits[0]
    assert (row["기준가입금액만원"], row["기준지급금액만원"], row["지급기준구분"]) == (1000.0, 300.0, "금액")
    assert row["급부ID"] == ids.benefit_id(built.riders[0]["특약ID"], "가나 위로금")


def test_targets_name_the_rows_of_same_name_covers():
    values = finals()
    values["R004-1"] = reading("R004-1", 대상="첫 치료")
    values["R004-2"] = reading("R004-2", 지급률=10, 대상="「재치료」")
    built = RR.build_rows(VID, views(), values, renewal_years=20)
    rows = {b["원시급부명"]: b for b in built.benefits if b["원시급부명"].startswith("자차 치료비")}
    assert set(rows) == {"자차 치료비(첫 치료)", "자차 치료비(재치료)"}
    rider = rows["자차 치료비(재치료)"]["특약ID"]
    assert rows["자차 치료비(재치료)"]["급부ID"] == ids.benefit_id(rider, "자차 치료비(재치료)")
    assert rows["자차 치료비(재치료)"]["기준지급금액만원"] == 10.0
    assert built.numbers[rows["자차 치료비(첫 치료)"]["급부ID"]] == ("R004-1",)
    assert "R004-1" not in built.skipped and check_rows("sys_급부", built.benefits) == {}


def test_missing_renewal_cycle_leaves_the_renewal_rider_out():
    built = RR.build_rows(VID, views(), finals())
    assert built.skipped_riders == {"갱신형 다라 수술비": "갱신형 특약인데 갱신주기년이 없음(사람이 정할 값)"}
    assert any("갱신주기년이 없어 뺀 갱신형 특약 1개, 그 특약의 세부보장 1줄" in n for n in built.notes)
    assert {r["원시특약명"] for r in built.riders} == {"가나 진단비", "다라 수술비", "마바 치료비", "자차 치료비"}
    assert check_rows("sys_특약", built.riders) == {}
    # 주기를 특약마다 주면 그 특약만 들어오고, 다른 특약의 ID는 주기가 없을 때와 같다
    given = RR.build_rows(VID, views(), finals(), renewal_years={"갱신형 다라 수술비": 10})
    renewal = next(r for r in given.riders if r["원시특약명"] == "갱신형 다라 수술비")
    assert renewal["갱신여부"] is True and renewal["갱신주기년"] == 10
    assert {r["특약ID"] for r in built.riders} < {r["특약ID"] for r in given.riders}


def test_no_row_lines_keep_their_information():
    values = finals()
    values["R003-3"] = {**RR.DEFAULTS, "번호": "R003-3", "쪽": 10, "꼴": RR.NO_ROW, "행없음사유": "항목별금액표",
                        "한도": [{"앞말": "없음", "수": 30, "단위": "일"}]}
    built = RR.build_rows(VID, views(), values, renewal_years=20)
    assert built.no_rows["R003-3"] == {"행없음사유": "항목별금액표", "면책일수": 0, "보장개시일": "", "한도": ["30일 한도"]}


# ---------------------------------------------------------------------------
# 묶음 나누기와 견줌 도구
# ---------------------------------------------------------------------------

def long_file():
    pieces = [piece(f"특약{i}", [cover(f"보장{i}", "가나", "가입금액", p)], p, p + span)
              for i, (p, span) in enumerate([(1, 0), (1, 3), (5, 2), (8, 1), (10, 0), (30, 0), (31, 12)], 1)]
    pieces[5]["형"] = "공통"
    for p in pieces[:5] + pieces[6:]:
        p["형"] = "가형"
    return pieces_file(pieces)


def test_bundles_keep_pieces_whole_and_break_at_page_gaps():
    bundles = split_pieces.split(long_file(), "TEST1", pages=10)
    spans = [(b["쪽"], [p["조각번호"] for p in b["조각"]]) for b in bundles]
    # 1~10쪽은 10쪽 안이라 한 묶음, 30쪽은 앞과 쪽이 떨어져 새 묶음, 31~43쪽 조각은 30쪽 묶음에 붙이면 10쪽을 넘어 따로
    assert spans == [([1, 10], ["R001", "R002", "R003", "R004", "R005"]), ([30, 30], ["R006"]), ([31, 43], ["R007"])]
    assert bundles[0]["조각"][0]["세부보장"][0]["번호"] == "R001-1"
    assert set(bundles[0]["조각"][0]) == {"조각번호", "쪽", "특약명", "형", "세부보장"}
    only = split_pieces.split(long_file(), "TEST1", pages=10, segments=["공통"])
    assert [p["조각번호"] for b in only for p in b["조각"]] == ["R006"]


def test_bundle_file_reads_back_with_original_numbers():
    bundle = split_pieces.split(SAMPLE, "TEST1", pages=10)[0]
    pieces = RR.load_pieces(bundle)
    assert [c.number for p in pieces for c in p.covers] == [c.number for p in views() for c in p.covers]
    assert pieces[0].notes == ()       # 11쪽 주석은 10쪽 조각들의 쪽 범위 밖이고 주석 표시도 없다
    assert pieces[1].names == ("다라 수술비", "갱신형 다라 수술비") and pieces[0].names == ()


def test_bundle_marks_same_name_covers():
    bundle = split_pieces.split(SAMPLE, "TEST1", pages=10)[0]
    flags = {c["번호"]: c.get("이름같은줄", False) for p in bundle["조각"] for c in p["세부보장"]}
    assert [n for n, f in flags.items() if f] == ["R003-1", "R003-2", "R004-1", "R004-2"]


def test_compare_bundle_confirms_only_clean_agreement():
    bundle = split_pieces.split(SAMPLE, "TEST1", pages=10)[0]
    a = {"형식": RR.FORMAT, "판독자": "갑", "값": list(finals().values())}
    b_values = finals()
    b_values["R002-1"] = reading("R002-1", 지급률=20)          # 한도를 빠뜨린 판독
    b = {"형식": RR.FORMAT, "판독자": "을", "값": list(b_values.values())}
    result = compare_readers.compare_bundle(bundle, {"갑": a, "을": b}, ["갑", "을"])
    by = {x["번호"]: x for x in result["줄"]}
    assert by["R001-1"]["자동판정"] == RR.CONFIRMED and by["R001-1"]["판정"] == RR.CONFIRMED
    assert by["R002-1"]["자동판정"] == RR.NEEDS_JUDGE and by["R002-1"]["일치"]["한도"] == RR.DIFF
    assert by["R004-1"]["이름같은줄갈림"] and by["R004-1"]["자동판정"] == RR.NEEDS_JUDGE
    # 이름이 같은 R003-1, R003-2는 값이 같아도 대상이 비어 있어 판정필요다
    assert by["R003-1"]["대상확인필요"] and by["R003-1"]["자동판정"] == RR.NEEDS_JUDGE
    assert "모름칸" in by["R001-1"]["갑"] and "모름" not in by["R001-1"]["갑"]
    text = compare_readers.summary([result])
    assert "확정 2" in text and "R002-1" in text


def test_compare_bundle_confirms_same_name_covers_with_targets():
    bundle = split_pieces.split(SAMPLE, "TEST1", pages=10)[0]
    values = finals()
    values.update({"R003-1": reading("R003-1", 대상="관혈"), "R003-2": reading("R003-2", 대상="비관혈"),
                   "R004-1": reading("R004-1", 대상="첫 치료"), "R004-2": reading("R004-2", 지급률=10, 대상="재치료")})
    other = {**values, "R004-2": reading("R004-2", 지급률=10, 대상="「재치료」")}
    a = {"형식": RR.FORMAT, "값": list(values.values())}
    b = {"형식": RR.FORMAT, "값": list(other.values())}
    result = compare_readers.compare_bundle(bundle, {"갑": a, "을": b}, ["갑", "을"])
    by = {x["번호"]: x for x in result["줄"]}
    assert all(by[n]["자동판정"] == RR.CONFIRMED for n in ("R003-1", "R003-2", "R004-1", "R004-2"))
    # 이름이 같은 줄이 없는 세부보장에 대상을 적으면 문제다
    values["R001-1"] = {**values["R001-1"], "대상": "가나병"}
    result = compare_readers.compare_bundle(bundle, {"갑": {"형식": RR.FORMAT, "값": list(values.values())}, "을": b},
                                            ["갑", "을"])
    assert "대상: 이름이 같은 줄이 없는데 대상이 있음" in result["줄"][0]["기계검사"]["갑"]["문제"]


def test_main_reads_answer_files_named_bundle_dot_reader(tmp_path):
    import json
    bundle = split_pieces.split(SAMPLE, "TEST1", pages=10)[0]
    (tmp_path / "b.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    for name in ("갑", "을"):
        answer = {"형식": RR.FORMAT, "묶음": bundle["묶음"], "판독자": name, "값": list(finals().values())}
        (tmp_path / f"{bundle['묶음']}.{name}.json").write_text(json.dumps(answer, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "값.jsonl"
    assert compare_readers.main([str(tmp_path / "b.json"), "--answers", str(tmp_path), "--readers", "갑", "을",
                                 "--out", str(out)]) == 0
    lines = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 7 and all(x["갑"] is not None and x["을"] is not None for x in lines)


def test_bundled_covers_are_not_confirmed_even_when_both_agree():
    bundle = split_pieces.split(SAMPLE, "TEST1", pages=10)[0]
    values = finals()
    values["R001-1"] = {**values["R001-1"], "주의": ["세부보장여럿묶임"]}
    a = {"형식": RR.FORMAT, "값": list(values.values())}
    result = compare_readers.compare_bundle(bundle, {"갑": a, "을": a}, ["갑", "을"])
    assert result["줄"][0]["자동판정"] == RR.NEEDS_JUDGE and result["줄"][0]["일치"]["주의"] == RR.SAME


def test_final_readings_pick_the_judged_value():
    lines = [{"번호": "R001-1", "쪽": 10, "판정": "확정", "갑": RR.stored_value(reading("R001-1")), "을": None},
             {"번호": "R002-1", "쪽": 10, "판정": "을", "갑": None, "을": RR.stored_value(reading("R002-1", 지급률=20))},
             {"번호": "R003-1", "쪽": 10, "판정": "검토 대기", "갑": None, "을": None}]
    out = RR.final_readings(lines, "갑", "을")
    assert set(out) == {"R001-1", "R002-1"} and out["R002-1"]["지급률"] == 20
    assert RR.check_format(out["R001-1"]) == []


def test_check_file_reports_missing_numbers():
    bundle = split_pieces.split(SAMPLE, "TEST1", pages=10)[0]
    answer = {"형식": RR.FORMAT, "묶음": bundle["묶음"], "값": [reading("R001-1")]}
    problems = compare_readers.check_file(bundle, answer)
    assert len(problems) == 1 and problems[0].startswith("판독이 없는 번호 6개")


def test_check_file_reports_targets_of_same_name_covers():
    bundle = split_pieces.split(SAMPLE, "TEST1", pages=10)[0]
    values = finals()
    values["R001-1"] = {**values["R001-1"], "대상": "가나병"}
    values["R004-1"] = reading("R004-1", 대상="첫 치료")
    values["R004-2"] = reading("R004-2", 지급률=10, 대상="재치료")
    problems = compare_readers.check_file(bundle, {"형식": RR.FORMAT, "묶음": bundle["묶음"], "값": list(values.values())})
    assert problems == ["R001-1: 이름이 같은 줄이 없는데 대상이 있음",
                        "R003: 이름이 같은 줄(R003-1, R003-2)의 대상이 비었거나 서로 같음"]


# ---------------------------------------------------------------------------
# 조각 지문과 이름 보류
# ---------------------------------------------------------------------------

def test_fingerprint_ignores_spaces_but_not_letters_or_the_piece_head():
    from_pieces = {c.number: RR.cover_fingerprint(p, c) for p in views() for c in p.covers}
    assert len(set(from_pieces.values())) == len(from_pieces)
    assert all(len(x) == RR.FINGERPRINT_LENGTH for x in from_pieces.values())
    # 하나뿐인 특약명들은 적지 않은 것과 같다
    alone = pieces_file([{k: v for k, v in SAMPLE["조각"][0].items() if k != "특약명들"}], notes=SAMPLE["주석"])
    p = RR.load_pieces(alone)[0]
    assert RR.cover_fingerprint(p, p.covers[0]) == from_pieces["R001-1"]
    other_label = pieces_file([{**SAMPLE["조각"][0], "구분": "선택계약"}], notes=SAMPLE["주석"])
    p = RR.load_pieces(other_label)[0]
    assert RR.cover_fingerprint(p, p.covers[0]) != from_pieces["R001-1"]
    spaced = pieces_file([piece("가나 진단비", [cover("가나  진단비", "가나병으로 진단\n확정된 경우 (최초 1회한)",
                                                       "가입금액(가입 1년 안에는 가입금액의  50%)")], label="기본계약")],
                         notes=SAMPLE["주석"])
    p = RR.load_pieces(spaced)[0]
    assert RR.cover_fingerprint(p, p.covers[0]) == from_pieces["R001-1"]
    changed = pieces_file([piece("가나 진단비", [cover("가나 진단비", "가나병으로 진단 확정된 경우 (최초 1회한)",
                                                        "가입금액(가입 1년 안에는 가입금액의 60%)")], label="기본계약")],
                          notes=SAMPLE["주석"])
    p = RR.load_pieces(changed)[0]
    assert RR.cover_fingerprint(p, p.covers[0]) != from_pieces["R001-1"]


GLUED = pieces_file([
    # 세부보장 넷의 이름이 한 줄로 이어 붙고, 지급사유는 문단마다 대상이 하나씩이다
    piece("가나 진단비", [cover("가가종양진단비나나,다다종양진단비라라종양진단비",
                               "「가가종양」으로 진단확정되면 한 번 줌\n· 「나나,다다종양」으로 진단확정되면 한 번 줌\n"
                               "· 「라라종양」으로 진단확정되면 한 번 줌", "가입금액")]),
    # 따옴표 없이 "…으로 진단확정"만 적힌 대상
    piece("마바 전이암진단비", [cover("마바전이암사아전이암", "마바보장개시일 뒤에 마바전이암으로 진단확정되면 줌\n"
                                                         "※ 마바보장개시일은 가입 90일 뒤이고그 뒤에 사아전이암으로 진단확정되면 줌",
                                     "가입금액")]),
    # 같은 꼬리표가 되풀이되고 빈칸 없이 다음 이름이 이어진다
    piece("자차 치료비(체증형)", [cover("가가암(체증형)나나암(체증형)다다암(체증형)", "암구분별 진단 후 경과 연도별로 지급", "가입금액")]),
    # 이름 칸에 지급사유 문장
    piece("카타 진단및치료비", [cover("카타 사고로 다친 경우 해마다 한 번 지급", "카타 경증진단비", "가입금액")]),
    # 걸리면 안 되는 이름: 상위 이름과 세부 이름을 빈칸으로 이은 이름, 본형과 갱신형을 "/"로 이은 이름, 대상이 한 줄에 둘인 이름
    piece("파하 진단및치료비", [cover("파하 진단및치료비 파하진단비", "「파하」로 진단확정되면 줌\n· 파하 진단 뒤 치료", "가입금액")]),
    piece("가나 수술비/갱신형 가나 수술비", [cover("가나 수술비/갱신형 가나 수술비", "「가나」로 진단확정된 뒤 수술하면 줌",
                                                  "가입금액")], names=["가나 수술비", "갱신형 가나 수술비"]),
    piece("다라암 진단비", [cover("다라암 및 마바암 진단비", "「다라암」또는「마바암」으로 진단확정되면 줌", "가입금액")]),
    piece("사아 입원일당", [cover("사아입원일당(1일이상)(요양병원제외)", "사아로 입원한 경우(1일이상)", "1일당 가입금액")]),
])


def test_glued_and_sentence_names_are_held():
    problems = {c.number: RR.name_problem(c) for p in RR.load_pieces(GLUED) for c in p.covers}
    held = {n for n, why in problems.items() if why}
    assert held == {"R001-1", "R002-1", "R003-1", "R004-1"}
    assert problems["R004-1"].startswith(f"{RR.HOLD}: 이름 칸에 지급사유 문장")
    assert all(problems[n].startswith(f"{RR.HOLD}: 세부보장 이름 여럿이") for n in ("R001-1", "R002-1", "R003-1"))


def test_held_names_make_no_row_whatever_the_reading():
    pieces = RR.load_pieces(GLUED)
    values = {c.number: reading(c.number) for p in pieces for c in p.covers}
    built = RR.build_rows(VID, pieces, values, renewal_years=20)
    made = {n for nums in built.numbers.values() for n in nums}
    assert made == {"R005-1", "R006-1", "R007-1", "R008-1"}
    assert all(built.skipped[n].startswith(RR.HOLD) for n in ("R001-1", "R002-1", "R003-1", "R004-1"))
    # 보류한 줄도 특약 행은 남는다. 특약ID는 조각 이름으로 만든다
    assert "가나 진단비" in {r["원시특약명"] for r in built.riders}
    assert any(n.startswith("행을 만들지 않은 줄: 보류 4") for n in built.notes)
