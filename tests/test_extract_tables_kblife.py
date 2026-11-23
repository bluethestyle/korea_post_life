"""KB라이프생명 꼴(KBLIFE)의 요약서 급부 표.

시험 자료는 실제 표의 칸 나뉨, 병합, 쪽 넘김 모양만 본떠 손으로 만든 행 목록이다. 담보 이름과 문구는 지어낸 것이다.
칸 값의 뜻은 pdfplumber와 같다. None은 병합으로 따로 칸이 없는 자리, ""는 글자가 없는 칸이다.
"""
from types import SimpleNamespace

from postlife.extract import tables
from postlife.extract.tables import KBLIFE, MERITZ, SAMSUNGFIRE, PageTable, benefit_ranges, riders_from_tables

HEAD = ["특약명", "지급사유", "지급금액"]
SPLIT = ["특약명", "지급사유", None, "지급금액"]       # 지급사유 칸이 설명 칸과 치료 이름 칸으로 갈린 표


def table(page, rows, head=HEAD, label="선택특약", segment="간편심사형", **kw):
    return PageTable(page, [head] + rows, label, segment=segment, **kw)


def riders(*pages):
    return riders_from_tables(pages, KBLIFE)


# ---------------------------------------------------------------------------
# 절, 형 구간, 구분, 머리행
# ---------------------------------------------------------------------------

PAGES = {
    11: "주1) 가나 특약은 다라세까지",
    12: "2. 보험금 지급사유 및 보험금 지급제한 사유\n가. 간편심사형(3.5.5), 간편심사형(3.3.5)\n1) 주계약\n급부명 지급사유 지급금액",
    25: "나. 일반심사형\n1) 주계약\n급부명 지급사유 지급금액",
    37: "특약명 지급사유 지급금액",
    38: "3. 일반적인 보험금 지급제한 사유\n• 가나",
}


def test_section_titles_follow_the_layout():
    assert [(r.first_page, r.last_page) for r in benefit_ranges(PAGES, KBLIFE)] == [(12, 38)]
    assert benefit_ranges(PAGES) == [] and benefit_ranges(PAGES, MERITZ) == []


def marks(lines, state=None, layout=KBLIFE):
    state = state or tables._Marks()
    tables._read_marks(lines, state, layout)
    return state


def test_segment_lines_and_numbered_labels_set_the_marks():
    m = marks(["2. 보험금 지급사유 및 보험금 지급제한 사유", "가. 간편심사형(3.5.5), 간편심사형(3.3.5)", "1) 주계약"])
    assert (m.segment, m.label, m.heading) == ("간편심사형", "주계약", "")
    marks(["2) 선택특약"], state=m)
    assert (m.segment, m.label) == ("간편심사형", "선택특약")
    # 새 형 구간에서는 구분이 다시 적힐 때까지 비운다
    marks(["나. 일반심사형"], state=m)
    assert (m.segment, m.label, m.segments) == ("일반심사형", "", ["간편심사형", "일반심사형"])
    marks(["1) 주계약"], state=m)
    assert m.label == "주계약"
    # 주석 줄과 다른 번호 줄은 표시가 아니다
    marks(["주1) 가나 특약은 갱신형", "1) 가나 다라 마바 사아"], state=m)
    assert m.label == "주계약"
    # 다른 회사 꼴은 이 줄들을 읽지 않는다
    other = marks(["가. 간편심사형(3.5.5)", "1) 주계약"], layout=SAMSUNGFIRE)
    assert (other.segment, other.label) == ("", "")


def test_head_rows_name_the_first_column_rider_or_benefit():
    main = table(12, [["사망보험금", "가나로 사망시", "가입금액"]], head=["급부명", "지급사유", "지급금액"], label="주계약")
    rest = table(12, [["가나진단특약", "가나로 진단시", "가입금액"]])
    out = riders(main, rest)
    assert [(r.title, r.label, r.main, r.segment) for r in out] == [
        ("사망보험금", "주계약", True, "간편심사형"), ("가나진단특약", "선택특약", False, "간편심사형")]
    # 삼성화재 꼴은 이 머리행을 급부 표로 보지 않는다
    assert riders_from_tables([rest]) == []


def fake_table(words):
    """_header가 읽는 꼴의 표. 칸마다 글자 하나씩 자리를 준다."""
    cells, chars = [], []
    for j, word in enumerate(words):
        box = (100 * j, 0, 100 * j + 90, 20)
        cells.append(box)
        chars += [{"text": ch, "at": (box[0] + 5 + k, 10)} for k, ch in enumerate(word)]
    return SimpleNamespace(rows=[SimpleNamespace(cells=cells)]), chars


def test_pdf_head_cells_are_found_by_the_layout_words():
    t, chars = fake_table(["특약명", "지급사유", "지급금액"])
    assert tables._header(t, chars, KBLIFE) == (100, 200)
    assert tables._header(t, chars) is None and tables._header(t, chars, MERITZ) is None
    t, chars = fake_table(["보장명", "지급사유", "지급금액"])
    assert tables._header(t, chars) == (100, 200) and tables._header(t, chars, KBLIFE) is None


# ---------------------------------------------------------------------------
# 특약 이름 칸 하나가 여러 행에 걸친 표
# ---------------------------------------------------------------------------

def test_rows_under_a_merged_rider_cell_are_covers_of_that_rider_across_pages():
    first = table(12, [["가나통합진단특약", "가나 1로 진단 확정 시 (최초 1회한) ", "가입금액 \n(1년미만 50%) "],
                       [None, "가나 2로 진단 확정 시 (최초 1회한) ", None]], open_end=True)
    # 다음 쪽 첫 행은 특약 이름 칸과 지급금액 칸이 쪽을 넘어온 빈 칸이다. 앞 쪽 마지막 줄이 칸을 꽉 채웠어도
    # 괄호로 끝났으므로 잘린 행이 아니다
    rest = table(13, [["", "가나 3으로 진단 확정 시 (최초 1회한) ", ""],
                      [None, "가나 4로 진단 확정 시 (최초 1회한) ", None],
                      ["다라수술특약", "다라 수술 시 (수술 1회당) ", "가입금액"]])
    a, b = riders(first, rest)
    assert a.title == "가나통합진단특약" and (a.first_page, a.last_page) == (12, 13)
    assert [(c.name, c.reason, c.page) for c in a.covers] == [
        ("가나통합진단특약", "가나 1로 진단 확정 시 (최초 1회한)", 12), ("가나통합진단특약", "가나 2로 진단 확정 시 (최초 1회한)", 12),
        ("가나통합진단특약", "가나 3으로 진단 확정 시 (최초 1회한)", 13), ("가나통합진단특약", "가나 4로 진단 확정 시 (최초 1회한)", 13)]
    assert {c.amount for c in a.covers} == {"가입금액 (1년미만 50%)"}
    assert b.title == "다라수술특약" and len(b.covers) == 1


def test_cut_rows_join_their_tail_on_the_next_page():
    page = table(20, [["마바수술특약", "마바로 진단 확정 후 관혈수술을 받은 경우 ", "가입금액 "],
                      ["사아진단특약", "사아로 진단 확정 시 (최초 1회한) ", "가입금액 \n(90일 미만 10%, \n90일 ~ 1년미만 "]])
    rest = table(21, [["", "", "50%) "],                                   # 지급금액 글의 뒷부분
                      ["자차입원특약", "자차로 입원한 경우 ", "가입금액 "]])
    before = table(30, [["카타수술특약", "카타로 진단 확정 후 수술을 받은 경우 ", "가입금액 "]])
    after = table(31, [["", "(단, 두 수술을 함께 받으면 하나만 지급) ", "(1년미만 50%) "],  # "("로 시작하는 단서
                       [None, "카타로 진단 확정 후 다른 수술을 받은 경우 ", "가입금액의 20% "]])
    out = riders(page, rest, before, after)
    assert [len(r.covers) for r in out] == [1, 1, 1, 2]
    assert out[1].covers[0].amount == "가입금액 (90일 미만 10%, 90일 ~ 1년미만 50%)"
    first, second = out[3].covers
    assert first.reason == "카타로 진단 확정 후 수술을 받은 경우 (단, 두 수술을 함께 받으면 하나만 지급)"
    assert first.amount == "가입금액 (1년미만 50%)"
    assert (second.reason, second.amount, second.page) == ("카타로 진단 확정 후 다른 수술을 받은 경우", "가입금액의 20%", 31)


def test_split_reason_column_gives_treatment_names_and_shares_merged_cells_across_pages():
    page = table(19, [["가나주요치료Plus특약", "가나로 진단 확정되고 치료를 직접적인 ", "가나 수술 ", "가입금액 \n(90일 미만 10%, "],
                      [None, None, "가나 \n약물치료 ", None]], head=SPLIT)
    # 앞 쪽 마지막 행이 잘렸다. 설명 칸과 지급금액 칸은 병합된 채 이어지고, 치료 이름 칸에는 새 이름이 적혀 있다
    rest = table(20, [["", "목적으로 치료 시 ", "가나 방사선치료 ", "1년미만 50%) "],
                      [None, None, "가나 중환자실치료 ", "가입금액의 50% "],
                      ["다라진단특약", "다라로 진단 확정 시 ", None, "가입금액"]], head=SPLIT)
    a, b = riders(page, rest)
    whole = "가나로 진단 확정되고 치료를 직접적인 목적으로 치료 시"
    assert [(c.name, c.reason, c.amount, c.page) for c in a.covers] == [
        ("가나 수술", whole, "가입금액 (90일 미만 10%, 1년미만 50%)", 19),
        ("가나 약물치료", whole, "가입금액 (90일 미만 10%, 1년미만 50%)", 19),
        ("가나 방사선치료", whole, "가입금액 (90일 미만 10%, 1년미만 50%)", 20),
        ("가나 중환자실치료", whole, "가입금액의 50%", 20)]
    assert [(c.name, c.reason) for c in b.covers] == [("다라진단특약", "다라로 진단 확정 시")]


def test_rider_name_tail_on_the_next_page_joins_the_title():
    page = table(14, [["(간편)가나 \n(다라 포함) \n마바(사아 및 ", "가나로 진단 확정되고 지급기간 이내에 마바 치료를 받은 ", "가입금액 "]],
                 open_end=True)
    rest = table(15, [["자차 제외) \n치료특약 ", "", ""], ["(간편)카타특약", "카타 시 ", "가입금액"]])
    a, b = riders(page, rest)
    assert a.title == "(간편)가나 (다라 포함) 마바(사아 및 자차 제외) 치료특약" and len(a.covers) == 1
    assert b.title == "(간편)카타특약"


def test_same_document_gives_same_pieces_twice():
    page = table(12, [["가나통합진단특약", "가나 1로 진단 시 ", "가입금액"], [None, "가나 2로 진단 시 ", None]])
    rest = table(13, [["", "가나 3으로 진단 시 ", ""]])
    assert riders(page, rest) == riders(page, rest)


# ---------------------------------------------------------------------------
# 표의 선
# ---------------------------------------------------------------------------

def v_edge(x, top, bottom):
    return tables._edge(x, top, x, bottom)


def test_frame_caps_close_the_table_where_its_vertical_lines_end_together():
    # 특약 이름 칸(10~100)과 지급금액 칸(300~400)이 쪽 끝(500)까지 병합되어 그 자리에 가로선이 없는 표
    v = [v_edge(10, 50, 500), v_edge(100, 50, 500.4), v_edge(300, 50, 500.4), v_edge(400, 50, 500),
         v_edge(200, 260, 500.3)]           # 지급사유 칸을 가르는 선. 표 가운데서 시작한다
    caps = tables._frame_caps(v)
    assert sorted((e["top"], e["x0"], e["x1"]) for e in caps) == [(50, 10, 400), (500, 10, 400)]
    # 표 너비를 덮지 못하는 선 묶음에는 더하지 않는다
    assert tables._frame_caps([v_edge(10, 50, 500), v_edge(100, 60, 200), v_edge(400, 70, 300)]) == []
