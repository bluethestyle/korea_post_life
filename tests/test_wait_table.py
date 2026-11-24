"""특약별 면책기간 표(tables.wait_table)를 칸 단위로 읽고, 특약 이름과 맞추고, 기계 검사용 줄을 만드는 부분.

현대해상 요약서는 급부 표의 지급사유에 이름 없는 "보장개시일 이후"만 적고, 특약마다 면책 날수는 요약서 뒤쪽의 면책기간 표에만
싣는다. 표는 쪽마다 두 단이고 특약 이름 칸 하나에 이름 여럿을 쉼표나 줄 바꿈으로 이어 적는다. 이름, 칸 글자, 좌표는 모두
지어낸 것이다(공시 문서의 글이 아니다).
"""
import sys
from pathlib import Path

from postlife.extract import reader_rows as RR
from postlife.extract import tables as T

HEAD = "최초계약과\n부활(효력회복)\n계약의\n면책기간"
CUT = "보험금\n감액기간"


def head_cells(x0, wait_x):
    """머리행 칸: 구분, 면책기간, 감액기간."""
    return [((x0, 80, wait_x, 140), "구 분"), ((wait_x, 80, wait_x + 45, 140), HEAD),
            ((wait_x + 45, 80, wait_x + 90, 140), CUT)]


# ---------------------------------------------------------------------------
# 면책기간 칸의 글자
# ---------------------------------------------------------------------------

def test_wait_days_text_reads_days_and_dash():
    assert T.wait_days_text("90일면책") == (90,)
    assert T.wait_days_text("90일 면책") == (90,)
    assert T.wait_days_text("90일") == (90,)
    assert T.wait_days_text("90일\n면책") == (90,)            # 좁은 칸에서 두 줄로 갈림
    assert T.wait_days_text("1년면책") == (365,)
    assert T.wait_days_text("1년 면책") == (365,)
    assert T.wait_days_text("10일면책") == (10,)
    assert T.wait_days_text("-") == (0,)
    assert T.wait_days_text("90일 면책\n-") == (90, 0)       # 대상 칸이 두 줄인 행


def test_wait_days_text_refuses_unclear_values():
    assert T.wait_days_text("5년") is None                    # 날 단위 없는 기간
    assert T.wait_days_text("5년 90일면책") is None
    assert T.wait_days_text("가나") is None


# ---------------------------------------------------------------------------
# 이름 맞추기
# ---------------------------------------------------------------------------

def test_name_spans_join_wrapped_lines_and_keep_renewal_apart():
    text = "가나진단(간편),\n가나진단(간편)(갱신\n형),다라수술(연간1\n회한)\n마바진단(간편)\n(갱신형)\n사아진단"
    got = T.wait_name_spans(text, ["가나진단(간편)", "가나진단(간편)(갱신형)", "다라수술(연간1회한)",
                                   "마바진단(간편)", "마바진단(간편)(갱신형)", "사아진단"])
    assert set(got) == {"가나진단(간편)", "가나진단(간편)(갱신형)", "다라수술(연간1회한)", "마바진단(간편)(갱신형)",
                        "사아진단"}
    # "마바진단(간편)" 다음 줄이 "(갱신형)"이라 이름이 이어진 것이다. 비갱신형 이름으로 맞추지 않는다
    assert "마바진단(간편)" not in got


def test_name_spans_start_after_line_without_closing_bracket():
    """괄호로 끝나지 않는 이름 다음 줄에서 새 이름이 시작한다."""
    got = T.wait_name_spans("가나후9대진단\n다라진단, 마바진단", ["가나후9대진단", "다라진단", "마바진단"])
    assert set(got) == {"가나후9대진단", "다라진단", "마바진단"}


def test_name_spans_do_not_start_inside_open_bracket():
    got = T.wait_name_spans("가나치료비(상급(다라\n포함))(간편)", ["포함))(간편)", "가나치료비(상급(다라포함))(간편)"])
    assert set(got) == {"가나치료비(상급(다라포함))(간편)"}


def test_name_key_ignores_spaces_and_bracket_order():
    assert T.wait_name_key("가나 치료비 (간편) (연간1회한)") == T.wait_name_key("가나치료비(연간1회한)(간편)")
    assert T.wait_name_key("가나치료비(간편)") != T.wait_name_key("가나치료비(간편)(갱신형)")
    # 괄호 짝이 맞지 않는 이름은 차례를 바꾸지 않고 빈칸만 뗀다
    assert T.wait_name_key("가나(다라(마바)(간편)") == "가나(다라(마바)(간편)"


def test_name_tokens_keep_comma_over_line_break():
    tokens, seps = T.name_tokens("가나,\n다라 /\n마바\n사아")
    assert tokens == ["가나", "다라", "마바", "사아"]
    assert seps == [",", "/", "\n"]


# ---------------------------------------------------------------------------
# 칸을 행으로
# ---------------------------------------------------------------------------

def test_rows_from_header_table_with_target_column():
    cells = head_cells(100, 260) + [
        ((100, 140, 200, 300), "가나진단(간편),\n가나진단(간편)(갱신형)"),
        ((200, 140, 260, 220), "암(가나암\n제외)"), ((260, 140, 305, 220), "90일면책"),
        ((200, 220, 260, 300), "가나암"), ((260, 220, 305, 300), "-"),
    ]
    rows = T.wait_rows_from_cells([(5, 0, (100, 80, 350, 300), cells, "")])
    assert [(r.detail, r.days) for r in rows] == [("암(가나암제외)", (90,)), ("가나암", (0,))]
    assert all(r.page == 5 and "가나진단(간편)(갱신형)" in r.names_text for r in rows)


def test_continued_table_appends_names_to_open_cell():
    """머리행 없이 다음 단 맨 위에서 이어지는 표: 면책기간 칸이 비어 있으면 앞 특약 이름 칸이 이어진 것이다."""
    first = head_cells(440, 615) + [((440, 140, 615, 500), "가나진단,\n다라진단(연간1"),
                                    ((615, 140, 660, 500), "90일면책")]
    second = [((120, 86, 295, 300), "회한),\n마바진단"), ((295, 86, 340, 300), ""),
              ((120, 300, 295, 480), "사아진단"), ((295, 300, 340, 480), "-")]
    rows = T.wait_rows_from_cells([(7, 1, (440, 80, 700, 500), first, ""), (8, 0, (120, 86, 380, 480), second, "")])
    assert [(r.page, r.days) for r in rows] == [(7, (90,)), (8, (0,))]
    assert set(T.wait_name_spans(rows[0].names_text, ["가나진단", "다라진단(연간1회한)", "마바진단", "사아진단"])) == \
        {"가나진단", "다라진단(연간1회한)", "마바진단"}


def test_continued_table_must_start_at_top_of_column():
    first = head_cells(440, 615) + [((440, 140, 615, 500), "가나진단"), ((615, 140, 660, 500), "90일면책")]
    other = [((120, 300, 295, 400), "적립이율"), ((295, 300, 340, 400), "연 2%")]
    rows = T.wait_rows_from_cells([(7, 1, (440, 80, 700, 500), first, ""), (8, 0, (120, 300, 380, 400), other, "")])
    assert len(rows) == 1


def test_names_above_small_table_are_used():
    """머리행만 있는 표 아래에 이름 줄을 가로로 적고 그 아래 형별 작은 표를 둔 꼴."""
    head = head_cells(430, 595)
    small = [((512, 180, 595, 220), "가나맞춤\n00형,05형"), ((595, 180, 644, 240), "90일면책"),
             ((512, 220, 595, 240), "그 외 종형")]
    rows = T.wait_rows_from_cells([(9, 1, (430, 80, 730, 140), head, ""),
                                   (9, 1, (512, 180, 730, 240), small, "가나입원일당(1-90일)\n다라입원일당")])
    assert len(rows) == 1
    assert rows[0].days == (90,) and "그외종형" in rows[0].detail
    assert set(T.wait_name_spans(rows[0].names_text, ["가나입원일당(1-90일)", "다라입원일당"])) == \
        {"가나입원일당(1-90일)", "다라입원일당"}


def test_benefit_table_with_wait_words_is_not_a_header():
    """급부 표의 지급사유 칸에 "면책기간", "감액기간"이 나와도 긴 칸이면 머리행이 아니다."""
    long = "가나병으로 진단 확정된 경우 면책기간 90일 이후 다라 감액기간 1년 동안 가입금액의 50%를 지급합니다"
    cells = [((100, 80, 300, 140), long), ((300, 80, 345, 140), "보험금 감액기간 안내 문구가 길게 이어지는 칸입니다 가나다라")]
    assert T.wait_rows_from_cells([(3, 0, (100, 80, 400, 140), cells, "")]) == []


# ---------------------------------------------------------------------------
# 기계 검사용 줄
# ---------------------------------------------------------------------------

def test_wait_lines_feed_machine_check():
    rows = [T.WaitRow(5, 0, "가나진단(간편),\n다라진단(간편)", "", "90일면책", (90,)),
            T.WaitRow(5, 0, "마바수술", "", "-", (0,)),
            T.WaitRow(6, 1, "사아진단(간편)", "암(가나암제외) 가나암", "90일 면책\n-", (90, 0))]
    lines = T.wait_lines(rows, ["가나진단(간편)", "다라진단(간편)", "마바수술", "사아진단(간편)", "자차진단"])
    assert lines == {5: "가나진단(간편) 90일면책\n다라진단(간편) 90일면책", 6: "사아진단(간편) 90일면책"}
    # 날수 줄 다음 줄이 "전"으로 시작해도(전이암…) 기계 검사가 날수를 읽는다
    page = "표 글자가 섞인 쪽\n" + lines[5] + "\n전이가나진단(간편) 90일면책"
    assert RR.wait_days_on_page(["가나진단(간편)"], page) == {90}
    assert RR.wait_days_on_page(["자차진단"], page) == set()


# ---------------------------------------------------------------------------
# 감액 칸(보험금 감액기간, 50% 감액지급)
# ---------------------------------------------------------------------------

def test_wait_cut_text_reads_period_and_mark():
    assert T.wait_cut_text("최초계약일\n부터\n1년미만", "○") == (1, "년")
    assert T.wait_cut_text("1년\n미만", "○") == (1, "년")
    assert T.wait_cut_text("-", "X") == ()
    assert T.wait_cut_text("-", "-") == ()
    # 기간은 있는데 X, "90일이내"(날 단위), 비율 칸이 여럿인 표("?")는 읽지 않는다
    assert T.wait_cut_text("최초계약일부터 1년미만", "X") is None
    assert T.wait_cut_text("최초계약일부터\n90일이내", "○") is None
    assert T.wait_cut_text("?", "?") is None
    assert T.WaitRow(1, 0, "가나", "", "-", (0,)).cut_period is None      # 감액 칸이 없는 표


def test_rows_read_cut_columns_and_merged_cut_cell():
    """감액 칸 하나가 대상이 다른 두 면책기간 칸에 걸쳐 병합되어 있으면 두 행 모두 같은 감액이다."""
    cells = head_cells(100, 260) + [
        ((100, 140, 200, 300), "가나치료(갱신형)"),
        ((200, 140, 260, 220), "암(가나암\n제외)"), ((260, 140, 305, 220), "90일 면책"),
        ((200, 220, 260, 300), "가나암"), ((260, 220, 305, 300), "-"),
        ((305, 140, 350, 300), "최초계약일\n부터\n1년미만"), ((350, 140, 380, 300), "○"),
    ]
    rows = T.wait_rows_from_cells([(5, 0, (100, 80, 380, 300), cells, "")])
    assert [(r.detail, r.days, r.cut_period) for r in rows] == \
        [("암(가나암제외)", (90,), (1, "년")), ("가나암", (0,), (1, "년"))]


def test_merged_wait_cell_is_split_by_cut_cells():
    """면책기간 칸 하나가 감액이 다른 두 형(간편맞춤고지 00형과 그 외 종형)에 걸쳐 병합된 작은 표는 감액 칸마다 행을 나눈다."""
    head = head_cells(430, 595)
    small = [((512, 180, 595, 220), "가나맞춤\n00형,05형"), ((595, 180, 644, 240), "90일면책"),
             ((512, 220, 595, 240), "그 외 종형"),
             ((644, 180, 690, 220), "최초계약\n일부터\n1년미만"), ((690, 180, 730, 220), "○"),
             ((644, 220, 690, 240), "-"), ((690, 220, 730, 240), "-")]
    rows = T.wait_rows_from_cells([(9, 1, (430, 80, 730, 140), head, ""),
                                   (9, 1, (512, 180, 730, 240), small, "가나입원일당(1-90일)")])
    assert [(r.detail, r.days, r.cut_period) for r in rows] == \
        [("가나맞춤00형,05형", (90,), (1, "년")), ("그외종형", (90,), ())]


def test_cut_table_with_several_ratio_columns_is_unread():
    """감액 비율 칸이 여럿인 표(10% 감액지급, 50% 감액지급)는 50% 감액지급 꼴이 아니라 읽지 않는다."""
    cells = head_cells(100, 260) + [
        ((100, 140, 260, 300), "가나치료비"), ((260, 140, 305, 300), "-"),
        ((305, 140, 350, 300), "최초계약일부터\n1년미만"), ((350, 140, 380, 300), "-"), ((380, 140, 410, 300), "○"),
    ]
    rows = T.wait_rows_from_cells([(5, 0, (100, 80, 410, 300), cells, "")])
    assert len(rows) == 1 and rows[0].cut_period is None


# ---------------------------------------------------------------------------
# 괄호 구조가 다른 이름
# ---------------------------------------------------------------------------

def test_name_spans_match_names_with_other_bracket_structure():
    text = "가나방사선(상급병원(다라포함),세기)치료(치료\n당),\n마바치료"
    names = ["가나방사선(세기)치료(상급병원(다라포함))(치료당)", "마바치료"]
    assert set(T.wait_name_spans(text, names)) == set(names)
    # 열쇠로만 맞추면 괄호 구조가 다른 이름은 찾지 못한다
    assert set(T.wait_name_spans(text, names, atoms=False)) == {"마바치료"}
    # 표 쪽 이름의 괄호 짝이 맞지 않으면 맞추지 않는다
    assert T.wait_name_spans("가나방사선(상급병원(다라포함),세기치료(치료당)", names[:1]) == {}
    # 값 파일 쪽 이름에 원문 괄호가 빠진 것도 같은 낱말이면 맞춘다
    assert set(T.wait_name_spans("마바치료(상급병원(다라포함))(치료당)", ["마바치료(상급병원(다라포함)(치료당)"])) == \
        {"마바치료(상급병원(다라포함)(치료당)"}


def test_name_atoms_need_same_words_and_one_owner():
    assert T.wait_name_atoms("가나(다라,마바)") == T.wait_name_atoms("가나(마바)(다라)")
    assert T.wait_name_atoms("가나(다라)") != T.wait_name_atoms("가나(다라)(갱신형)")
    # 같은 열쇠의 이름이 둘이면 괄호 구조로는 맞추지 않는다
    assert T.wait_name_spans("가나(다라,마바)", ["가나(마바)(다라)", "가나(다라(마바))"]) == {}
    # 두 이름을 이은 글(괄호 밖 쉼표)은 한 이름으로 보지 않는다
    assert T.wait_name_spans("가나,다라", ["가나(다라)"]) == {}


def test_wait_lines_add_cut_line_and_machine_check_reads_it():
    rows = [T.WaitRow(5, 0, "가나치료(간편)", "", "90일면책", (90,), "최초계약일부터\n1년미만", "○"),
            T.WaitRow(5, 0, "다라치료", "", "-", (0,), "-", "X")]
    lines = T.wait_lines(rows, ["가나치료(간편)", "다라치료"])
    assert lines == {5: "가나치료(간편) 90일면책\n가나치료(간편) 감액기간 1년미만 50%감액지급"}
    pages = {5: "표 글자\n" + lines[5]}
    assert RR.wait_cuts_on_pages(["가나치료(간편)"], pages) == {(1, "년")}
    assert RR.wait_cuts_on_pages(["다라치료"], pages) == set()
    cover = RR.CoverView("R001-1", "가나치료(간편)", "가나병으로 진단 확정되고 다라치료를 받은 경우", "가입금액", 10)
    piece = RR.PieceView(1, "가나치료(간편)", ("가나치료(간편)",), "선택계약", "", 10, 10, (cover,))
    value = {**RR.DEFAULTS, "번호": "R001-1", "쪽": 10, "꼴": RR.RATIO, "지급률": 100,
             "감액": [{"기간": 1, "단위": "년", "값": 50, "값기준": "보험금"}]}
    assert not RR.machine_checks(cover, value, piece, pages)[0]
    # 표 줄이 없으면 조각 글자에 감액 숫자가 없어 지금처럼 걸린다
    assert "숫자없음: 감액 기간 1년" in RR.machine_checks(cover, value, piece, {5: "표 글자"})[0]


def test_loader_adds_wait_lines_only_for_wait_table_layout():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import load_reader_product as L
    pages = {1: "가나"}
    assert L.with_wait_table(Path("없는파일.pdf"), pages, [], T.MERITZ) is pages
    assert T.HYUNDAI.wait_table and not T.MERITZ.wait_table
