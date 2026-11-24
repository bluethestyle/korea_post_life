"""현대해상 형식(HYUNDAI)의 요약서 급부 표.

테스트 자료는 실제 표의 칸 나뉨, 병합, 쪽 넘김, 두 단 배치 모양만 본떠 손으로 만든 행 목록과 선 목록이다. 담보 이름과 문구는
지어낸 것이다. 칸 값의 뜻은 pdfplumber와 같다. None은 병합으로 따로 칸이 없는 자리, ""는 글자가 없는 칸이다.
"""
from types import SimpleNamespace

from postlife.extract import reader_rows as RR
from postlife.extract import tables
from postlife.extract.tables import (
    HYUNDAI, KBLIFE, MERITZ, SAMSUNGFIRE, PageTable, benefit_ranges, riders_from_tables, riders_to_json, split_doubled,
)

HEAD = ["구 분", "지 급 사 유", "지 급 금 액"]


def table(page, rows, head=HEAD, label="선택계약", part=0, **kw):
    rows = [head] + rows
    return PageTable(page, rows, label, part=part, labels=(label,) * len(rows), **kw)


def riders(*pages):
    return riders_from_tables(pages, HYUNDAI)


# ---------------------------------------------------------------------------
# 절, 구분 줄
# ---------------------------------------------------------------------------

PAGES = {
    106: "※ 가나다라 안내",
    107: "2. 보험금 지급사유, 지급금액 및 지급제한사항 [가나 특약]\n가. 가나다라 표",
    130: "구 분 지 급 사 유 지 급 금 액",
    168: "까지의 기간\n나. 보험금 지급제한 사항 가나다라 마바",
}


def test_section_titles_follow_the_layout():
    # 두 단의 글이 한 줄로 섞여 읽혀도 절 제목이 줄 앞에 있으면 찾는다
    assert [(r.first_page, r.last_page) for r in benefit_ranges(PAGES, HYUNDAI)] == [(107, 168)]
    assert benefit_ranges(PAGES) == [] and benefit_ranges(PAGES, MERITZ) == [] and benefit_ranges(PAGES, KBLIFE) == []


def marks(lines, state=None):
    state = state or tables._Marks()
    tables._read_marks(lines, state, HYUNDAI)
    return state


def test_bracket_lines_set_the_label():
    assert marks(["[기본계약]"]).label == "기본계약"
    assert marks(["[의무부가 특약]"]).label == "의무부가 특약"
    m = marks(["[선택계약]", "- 가나형은 다라마바를 고를 수 없음"])
    assert m.label == "선택계약"
    # 특별약관 제목이나 설명 줄 안의 대괄호는 구분이 아니다
    marks(["[무배당 가나다라보장 특별약관]", "※ 가나의 경우 담보명에서 [다라] 생략"], state=m)
    assert m.label == "선택계약"


def test_pdf_head_cells_use_the_word_gubun():
    cells, chars = [], []
    for j, word in enumerate(["구 분", "지 급 사 유", "지 급 금 액"]):
        box = (100 * j, 0, 100 * j + 90, 20)
        cells.append(box)
        chars += [{"text": ch, "at": (box[0] + 5 + k, 10)} for k, ch in enumerate(word)]
    t = SimpleNamespace(rows=[SimpleNamespace(cells=cells)])
    assert tables._header(t, chars, HYUNDAI) == (100, 200)
    assert tables._header(t, chars) is None and tables._header(t, chars, KBLIFE) is None


# ---------------------------------------------------------------------------
# 묶음 칸(맨 왼쪽의 좁은 세로쓰기 칸)
# ---------------------------------------------------------------------------

def fake(widths, rows):
    """칸 너비 목록으로 pdfplumber 표 흉내를 만든다. rows의 None 자리는 칸이 없다."""
    out = []
    for i, row in enumerate(rows):
        x, cells = 0.0, []
        for w, value in zip(widths, row):
            cells.append(None if value is None else (x, 20.0 * i, x + w, 20.0 * i + 20))
            x += w
        out.append(SimpleNamespace(cells=cells))
    return SimpleNamespace(rows=out)


def test_group_column_is_dropped_and_names_the_label():
    rows = [["구 분", None, "지 급 사 유", "지 급 금 액"],
            ["기\n본\n계\n약", "가나사망", "가나로 사망 시", "가입금액"],
            ["의\n무\n가\n입", "가나납입면제", "다라 시", "특약가입금액"],
            ["상\n해\n관\n련", "마바진단", "마바로 진단 확정 시", "특약가입금액"],
            [None, "사아수술", "사아 수술 시", "특약가입금액"]]
    m = tables._Marks()
    kept, labels = tables._group_rows(fake([18, 80, 120, 80], rows), [list(r) for r in rows], m, HYUNDAI)
    assert [r[0] for r in kept] == [None, "가나사망", "가나납입면제", "마바진단", "사아수술"]
    # 잘려 찍힌 묶음 이름("의무가입")도 알아본다. 다른 묶음은 선택계약이고, 병합된 칸은 위의 묶음을 물려받는다
    assert labels == ("", "기본계약", "의무가입특약", "선택계약", "선택계약")
    assert m.group == "상해관련"
    # 쪽 첫 행의 빈 묶음 칸은 앞 쪽의 묶음을 물려받는다
    _, again = tables._group_rows(fake([18, 80, 120, 80], rows[:1] + [["", "자차진단", "자차 시", "가입금액"]]),
                                  [list(r) for r in rows[:1]] + [["", "자차진단", "자차 시", "가입금액"]], m, HYUNDAI)
    assert again == ("", "선택계약")


def test_wide_or_horizontal_first_column_is_kept():
    rows = [["구분", "지 급 사 유", None, "지급금액"],
            ["보험료\n납입\n면제", "1종(가형)", "가나 시", "특약가입금액"]]
    m = tables._Marks(label="의무부가 특약")
    kept, labels = tables._group_rows(fake([30, 60, 150, 40], rows), [list(r) for r in rows], m, HYUNDAI)
    assert kept == rows and labels == ("의무부가 특약", "의무부가 특약")
    # 구분 줄이 없는 문서는 선택계약이다
    _, labels = tables._group_rows(fake([30, 60, 150, 40], rows), [list(r) for r in rows], tables._Marks(), HYUNDAI)
    assert labels == ("선택계약", "선택계약")


# ---------------------------------------------------------------------------
# 이름
# ---------------------------------------------------------------------------

def test_doubled_names_are_split():
    assert split_doubled("가나진단다라가나진단다라(갱신형)") == ("가나진단다라", "가나진단다라(갱신형)")
    assert split_doubled("가나수술(다라제외),가나수술(다라제외)(갱신형)") == ("가나수술(다라제외)", "가나수술(다라제외)(갱신형)")
    # 글자 사이를 벌려 맞춘 칸은 두 이름의 빈칸 자리가 다르다
    assert split_doubled("가나치료비(다라 병 원) 가나치 료 비(다라 병원)(갱신형)") == (
        "가나치료비(다라 병 원)", "가나치 료 비(다라 병원)(갱신형)")
    # 원문에서 닫는 괄호가 빠진 이름: 괄호 안이라 쉼표로 갈리지 않는다. 가르고 괄호 짝을 맞춘다
    assert split_doubled("가나수술(다라제외,마바지급,가나수술(다라제외,마바지급)(갱신형)") == (
        "가나수술(다라제외,마바지급)", "가나수술(다라제외,마바지급)(갱신형)")
    # 되풀이가 없거나 짧으면 그대로다
    assert split_doubled("가나다라진단") == ("가나다라진단",)
    assert split_doubled("가나가나진단") == ("가나가나진단",)
    assert split_doubled("가나(다라)부목치료") == ("가나(다라)부목치료",)


def test_rider_cell_with_two_names_shares_the_rows():
    page = table(108, [["가나수술(다라제외)\n가나수술(다라제외)\n(갱신형)", "가나로 수술 시", "특약가입금액"],
                       ["마바진단", "마바로 진단 시", "특약가입금액"],
                       ["마바진단(갱신형)", None, None],
                       ["4. 사아수술\n5. (자차병원)", "사아로 자차병원에서 수술 시", "가입금액"]])
    a, b, c, d = riders(page)
    assert a.title == "가나수술(다라제외), 가나수술(다라제외)(갱신형)"
    assert a.names == ("가나수술(다라제외)", "가나수술(다라제외)(갱신형)")
    # 세부보장 이름 칸이 없는 행의 세부보장 이름은 이은 제목이 아니라 갱신형 표시가 없는 특약 이름이다(급부 이름은 하나여야 한다)
    assert [x.name for x in a.covers] == ["가나수술(다라제외)"]
    # 이름 칸만 따로이고 지급사유, 지급금액 칸이 병합된 두 행은 같은 글을 쓰는 특약 둘이다
    assert (b.title, c.title) == ("마바진단", "마바진단(갱신형)")
    assert (c.covers[0].reason, c.covers[0].amount) == ("마바로 진단 시", "특약가입금액")
    # 번호 매김 흔적은 뗀다
    assert d.title == "사아수술(자차병원)" and d.names == ("사아수술(자차병원)",)
    saved = riders_to_json([a])["조각"][0]
    assert saved["특약명들"] == ["가나수술(다라제외)", "가나수술(다라제외)(갱신형)"]


def test_renewal_name_written_first_does_not_name_the_covers():
    # 갱신형 이름이 먼저 적힌 칸: 특약명들은 원문 차례 그대로이고, 세부보장 이름은 갱신형 표시가 없는 이름이다
    page = table(134, [["가나(다라)치료(갱신형),\n가나(다라)치료", "가나 치료 시", "특약가입금액"],
                       [None, "마바 치료 시", "특약가입금액의 20%"]])
    (r,) = riders(page)
    assert r.names == ("가나(다라)치료(갱신형)", "가나(다라)치료")
    assert r.title == "가나(다라)치료(갱신형), 가나(다라)치료"
    assert [c.name for c in r.covers] == ["가나(다라)치료", "가나(다라)치료"]
    # 비갱신형 이름이 먼저 적힌 칸과 같은 세부보장 이름이 된다(급부ID의 재료)
    (s,) = riders(table(134, [["가나(다라)치료,\n가나(다라)치료(갱신형)", "가나 치료 시", "특약가입금액"],
                              [None, "마바 치료 시", "특약가입금액의 20%"]]))
    assert [c.name for c in s.covers] == [c.name for c in r.covers]
    # 둘 다 갱신형이거나 둘 다 아니면 첫 이름
    assert tables.plain_name(("가나(5년갱신형)", "가나(10년갱신형)")) == "가나(5년갱신형)"
    assert tables.plain_name(("가나(1형)", "가나(2형)")) == "가나(1형)"
    assert tables.plain_name(("가나[갱신형]", "가나")) == "가나"
    assert tables.plain_name(("가나비갱신형", "가나갱신형")) == "가나비갱신형"


def test_other_layouts_keep_numbers_and_glued_names():
    page = PageTable(1, [["보장명", "지급사유", "지급금액"], ["4. 가나진단가나진단(갱신형)", "가나 시", "가입금액"]], "선택계약")
    (r,) = riders_from_tables([page], MERITZ)
    assert r.title == "4. 가나진단가나진단(갱신형)" and r.names == ("4. 가나진단가나진단(갱신형)",)


def test_plan_column_names_the_covers():
    page = table(115, [["가나통합보장", "(기본형)\n<가입금액 \n1,000만원>", "가나 진단 시", "10만원"],
                       [None, None, "가나 수술 시", "30만원"],
                       [None, "(실속형)\n<가입금액 \n500만원>", "가나 진단 시", "5만원"]],
                 head=["구 분", None, "지 급 사 유", "지 급 금 액"])
    (r,) = riders(page)
    assert [(c.name, c.amount) for c in r.covers] == [
        ("(기본형)<가입금액 1,000만원>", "10만원"), ("(기본형)<가입금액 1,000만원>", "30만원"),
        ("(실속형)<가입금액 500만원>", "5만원")]


# ---------------------------------------------------------------------------
# 두 단과 쪽 넘김
# ---------------------------------------------------------------------------

def test_left_column_row_continues_at_the_top_of_the_right_column():
    left = table(115, [["가나보장", "가나 흉터수술을 받은 ", "・가 부위 : 1㎝당 10만원"]], open_end=True)
    right = table(115, [["", "경우", "(제2항 한도)"],
                        [None, None, "・나 부위 : 1㎝당 5만원(제2항 한도)"],
                        ["다라진단", "다라 진단 시", "특약가입금액"]], part=1)
    a, b = riders(left, right)
    assert [(c.reason, c.amount, c.page) for c in a.covers] == [
        ("가나 흉터수술을 받은 경우", "・가 부위 : 1㎝당 10만원\n(제2항 한도)", 115),
        ("가나 흉터수술을 받은 경우", "・나 부위 : 1㎝당 5만원(제2항 한도)", 115)]
    assert b.title == "다라진단"
    # 같은 단 안의 다음 표 첫 행은 앞 행에 이어 붙이지 않는다(같은 쪽, 같은 단). 같은 특약의 다음 세부보장이다
    again = table(115, [["", "마바 시", "가입금액"]])
    out = riders(left, again)
    assert len(out) == 1 and len(out[0].covers) == 2


def test_rider_name_tail_without_cover_name_joins_the_title():
    page = table(115, [["가나통합보장, \n가나통합보장(", "(기본형)", "가나 진단 시", "10만원"]],
                 head=["구 분", None, "지 급 사 유", "지 급 금 액"], part=1)
    rest = table(116, [["갱신형)", "", "가나 수술 시", "30만원"],
                       [None, "(실속형)", "가나 진단 시", "5만원"]],
                 head=["구 분", None, "지 급 사 유", "지 급 금 액"])
    (r,) = riders(page, rest)
    assert r.names == ("가나통합보장", "가나통합보장(갱신형)")
    assert [(c.name, c.page) for c in r.covers] == [("(기본형)", 115), ("(기본형)", 116), ("(실속형)", 116)]


def test_per_row_labels_mark_the_main_contract():
    rows = [["가나사망", "가나로 사망 시", "가입금액"], ["가나납입면제", "다라 시", "특약가입금액"]]
    page = PageTable(37, [HEAD] + rows, "", labels=("", "기본계약", "의무가입특약"))
    a, b = riders(page)
    assert (a.label, a.main, b.label, b.main) == ("기본계약", True, "의무가입특약", False)


def test_column_of_a_table():
    page = (0, 0, 840, 595)
    assert tables._column_of((110, 86, 410, 500), page, True) == 0
    assert tables._column_of((435, 86, 730, 500), page, True) == 1
    assert tables._column_of((435, 86, 730, 500), page, False) == 0


# ---------------------------------------------------------------------------
# 표의 선
# ---------------------------------------------------------------------------

def h_edge(x0, x1, y):
    return tables._edge(x0, y, x1, y)


def v_edge(x, top, bottom):
    return tables._edge(x, top, x, bottom)


def test_side_edges_close_tables_without_outer_borders():
    # 표 하나(가로선 세 줄, 칸 경계 둘)와 그 아래 떨어진 표 하나. 양옆 테두리가 없다
    h = [h_edge(110, 404, 86), h_edge(110, 404, 100), h_edge(110, 404, 300),
         h_edge(110, 404, 330), h_edge(110, 404.8, 360)]
    v = [v_edge(234, 86, 300), v_edge(323, 86, 300), v_edge(234, 330, 360)]
    sides = {(round(e["x0"], 1), e["top"], e["bottom"]) for e in tables._side_edges(h, v)}
    assert {(110, 86, 100), (110, 100, 300), (404, 86, 100), (404, 100, 300), (110, 330, 360),
            (404, 330, 360), (404.8, 330, 360)} == sides
    # 두 표 사이(300~330)는 잇지 않는다
    assert not any(e["top"] == 300 for e in tables._side_edges(h, v))


def test_short_line_in_the_amount_column_still_meets_the_frame():
    # 지급금액 칸만 가르는 점선(611~733)과 표 전체의 가로선 사이도 잇는다(긴 선의 너비 안의 칸 경계로 본다)
    h = [h_edge(435, 733, 97), h_edge(611, 732.6, 108), h_edge(435, 733, 140)]
    v = [v_edge(512, 86, 140), v_edge(611, 86, 140)]
    sides = {(round(e["x0"], 1), e["top"]) for e in tables._side_edges(h, v)}
    assert {(733, 97), (732.6, 97), (733, 108), (732.6, 108)} <= sides


def page_of(lines=(), rects=()):
    return SimpleNamespace(lines=list(lines), rects=list(rects))


def dot(x0, top, x1, bottom):
    return {"x0": x0, "x1": x1, "top": top, "bottom": bottom}


def test_vertical_dotted_lines_are_read_only_when_asked():
    dots = [dot(170.5, 100 + 1.2 * k, 170.5, 100.48 + 1.2 * k) for k in range(20)]
    h, v = tables._border_edges(page_of(dots), dotted=True)
    assert [(e["x0"], e["top"], round(e["bottom"], 2)) for e in v] == [(170.5, 100, 123.28)] and h == []
    # 다른 회사 형식은 그대로(점 하나하나가 짧은 가로 토막이라 버려진다)
    assert tables._border_edges(page_of(dots)) == ([], [])


def test_header_fill_sides_become_vertical_lines_only_when_asked():
    fills = [{"x0": 112, "x1": 223, "top": 86, "bottom": 104, "fill": True, "stroke": False},
             {"x0": 223, "x1": 327, "top": 86, "bottom": 104, "fill": True, "stroke": False},
             {"x0": 748, "x1": 849, "top": 75, "bottom": 175, "fill": True, "stroke": False}]   # 높은 바탕은 아니다
    _, v = tables._border_edges(page_of(rects=fills), fills=True)
    assert sorted((e["x0"], e["top"], e["bottom"]) for e in v) == [(112, 86, 104), (223, 86, 104), (327, 86, 104)]
    assert tables._border_edges(page_of(rects=fills)) == ([], [])


def test_layout_flags_are_off_for_other_companies():
    for layout in (SAMSUNGFIRE, MERITZ, KBLIFE):
        assert not (layout.two_up or layout.open_sides or layout.group_column or layout.doubled_names
                    or layout.reason_rows or layout.name_tails or layout.dotted or layout.shared_whole
                    or layout.cell_fills or layout.numbered_names or layout.amount_parts or layout.spaced_names)


# ---------------------------------------------------------------------------
# 지급금액 머리 아래가 갈린 표(amount_parts)
# ---------------------------------------------------------------------------

def grid(rows):
    """칸 상자 목록으로 pdfplumber 표 흉내를 만든다. rows는 행마다 칸 상자(x0, top, x1, bottom)나 None의 목록이다."""
    out = []
    for cells in rows:
        boxes = [c for c in cells if c is not None]
        bbox = (min(c[0] for c in boxes), min(c[1] for c in boxes), max(c[2] for c in boxes), max(c[3] for c in boxes))
        out.append(SimpleNamespace(cells=list(cells), bbox=bbox))
    return SimpleNamespace(rows=out, cells=[c for r in rows for c in r if c is not None])


# 칸 자리: 이름 0~50, 지급사유 50~150, 지급금액 150~200, 감액 200~215, 한도 215~260
NAME, WHY = (0, 50), (50, 150)
MERGED = grid([
    [(0, 0, 50, 20), (50, 0, 150, 20), (150, 0, 260, 20), None, None],                           # 머리행
    [(0, 20, 50, 80), (50, 20, 150, 40), (150, 20, 200, 40), (200, 20, 215, 60), (215, 20, 260, 60)],
    [None, (50, 40, 150, 60), (150, 40, 200, 60), None, None],                                  # 감액, 한도 칸이 위에서 내려온다
    [None, (50, 60, 150, 80), (150, 60, 260, 80), None, None],                                  # 지급금액 칸이 옆으로 넓다
])
TEXTS = {(200, 20, 215, 60): "1\n년\n미\n만\n50%", (215, 20, 260, 60): "연간 총 \n100만원 한도"}


def test_merged_cut_and_limit_cells_reach_every_row_they_span():
    first = tables._amount_parts(MERGED, 1, ["가나", "다라 시", "10만원", "1\n년\n미\n만\n50%", "연간 총 \n100만원 한도"], 2, TEXTS)
    assert first == ["가나", "다라 시", "10만원\n\n1\n년\n미\n만\n50%\n\n연간 총 \n100만원 한도", None, None]
    second = tables._amount_parts(MERGED, 2, [None, "마바 시", "5만원", None, None], 2, TEXTS)
    assert second[2] == "5만원\n\n1\n년\n미\n만\n50%\n\n연간 총 \n100만원 한도" and second[3:] == [None, None]
    # 지급금액 칸이 옆으로 넓게 병합된 행은 그 칸 하나다
    assert tables._amount_parts(MERGED, 3, [None, "사아 시", "1만원", None, None], 2, TEXTS)[2:] == ["1만원", None, None]
    # 지급금액 자리가 모두 위에서 내려온 행은 그대로 둔다(위 행의 지급금액을 물려받는다)
    down = grid([[(0, 0, 50, 20), (50, 0, 150, 20), (150, 0, 200, 40), (200, 0, 260, 40)],
                 [(0, 20, 50, 40), (50, 20, 150, 40), None, None]])
    assert tables._amount_parts(down, 1, ["자차", "자차 시", None, None], 2, {}) == ["자차", "자차 시", None, None]
    # 칸이 하나뿐인 표는 그대로다
    assert tables._amount_parts(MERGED, 1, ["가", "나", "다"], 2, {}) == ["가", "나", "다"]


def test_amount_cell_split_into_name_and_formula_keeps_both():
    table = grid([[(0, 0, 50, 30), (50, 0, 150, 30), (150, 0, 180, 30), (180, 0, 260, 30)]])
    cells = ["가나환급", "가나 진단 시", "환급금", "가입금액 ×\n경과월수"]
    assert tables._amount_parts(table, 0, list(cells), 2, {})[2:] == ["환급금\n\n가입금액 ×\n경과월수", None]


def test_merged_cells_become_paragraphs_of_each_cover_amount():
    rows = [["가나치료비", "1형", "가나 수술 시", "10만원\n\n1\n년\n미\n만\n50%\n\n연간 총 \n100만원 한도"],
            [None, None, "가나 약물치료 시", "5만원\n\n1\n년\n미\n만\n50%\n\n연간 총 \n100만원 한도"]]
    (r,) = riders(table(142, rows, head=["구 분", None, "지 급 사 유", "지 급 금 액"]))
    assert [c.amount for c in r.covers] == ["10만원\n1년미만50%\n연간 총 100만원 한도", "5만원\n1년미만50%\n연간 총 100만원 한도"]


# ---------------------------------------------------------------------------
# 이름 칸의 빈칸(spaced_names), 번호 매김, 두 이름
# ---------------------------------------------------------------------------

def char(text, x0, x1, n, top=10):
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": top + 8, "n": n}


def test_name_cells_read_only_real_space_characters():
    # 양끝 맞춤으로 벌어진 글자(가, 나 사이 4pt)와 PDF에 적힌 빈칸 글자(나 뒤)
    chars = [char("가", 0, 8, 0), char("나", 12, 20, 1), char(" ", 20, 23, 2), char("다", 24, 32, 3)]
    assert [l.text for l in tables._text_lines(chars)] == ["가 나 다"]
    assert [l.text for l in tables._text_lines(chars, gaps=False)] == ["가나 다"]
    assert tables._cell_text(chars, [], gaps=False) == "가나 다"


def test_numbering_without_a_space_is_dropped_but_decimals_stay():
    page = table(127, [["4.가나수술5.(자차병원)", "가나 수술 시", "가입금액"],
                       ["가나진단(수치7.5%이상)", "가나 진단 시", "가입금액"]])
    a, b = riders(page)
    assert a.title == "가나수술(자차병원)" and b.title == "가나진단(수치7.5%이상)"


def test_slash_between_two_names_and_doubled_cover_names():
    page = table(82, [["가나치료비(다라)/ \n가나치료비(다라)(갱신형)", "가나 치료 시", "가입금액"]])
    (r,) = riders(page)
    assert r.names == ("가나치료비(다라)", "가나치료비(다라)(갱신형)") and r.covers[0].name == "가나치료비(다라)"
    rows = [["가나수술비, \n가나수술비(갱신형)", "가나수술비(다라형), \n가나수술비(다라형)(갱신형)", "가나 수술 시", "가입금액"],
            [None, "1종(마바형),2종(사아형, 자차형)", "가나 수술 시", "가입금액"]]
    (s,) = riders(table(123, rows, head=["구 분", None, "지 급 사 유", "지 급 금 액"]))
    assert [c.name for c in s.covers] == ["가나수술비(다라형)", "1종(마바형),2종(사아형, 자차형)"]
    assert tables.first_doubled("가나수술비(다라형), 가나수술비(다라형)(갱신형)") == "가나수술비(다라형)"
    assert tables.first_doubled("가나수술비(다라형)(갱신형), 가나수술비(다라형)") == "가나수술비(다라형)"
    assert tables.first_doubled("1종(마바형),2종(사아형)") == "1종(마바형),2종(사아형)"


# ---------------------------------------------------------------------------
# 이름 검사와 행 만들기(reader_rows)
# ---------------------------------------------------------------------------

def test_name_check_skips_payment_tags_and_holds_lost_brackets():
    ok = [RR.CoverView("R001-1", "가나수술(수술회당지급)", "가나 수술 시", "가입금액", 1),
          RR.CoverView("R001-2", "가나장해연금(월지급형)", "가나 장해 시", "가입금액", 1),
          RR.CoverView("R001-3", "가나진단(해약환급금 미지급형)", "가나 진단 시", "가입금액", 1)]
    assert [RR.name_problem(c) for c in ok] == ["", "", ""]
    # 지급사유 문장이 든 이름은 그대로 걸린다
    assert RR.name_problem(RR.CoverView("R001-4", "가나로 진단 시 지급", "", "", 1)).startswith(RR.HOLD)
    lost = RR.CoverView("R001-5", "가나치료비(다라병원(마바포함)", "가나 치료 시", "가입금액", 1)
    assert RR.name_problem(lost).startswith(RR.HOLD) and "괄호" in RR.name_problem(lost)
    assert RR.broken_brackets("가나)다라(") and not RR.broken_brackets("가나(다라)[마바]")


def piece_of(title, names, covers):
    return {"특별약관": title, "구분": "선택계약", "적용범위": "", "첫쪽": 1, "끝쪽": 1, "주계약": False, "특약명들": names,
            "세부보장": [{"보장명": n, "지급사유": why, "지급금액": "가입금액", "쪽": 1, "적용범위": ""} for n, why in covers]}


def test_rows_hold_a_piece_whose_rider_name_lost_a_bracket():
    names = ["가나치료비(다라병원(마바포함)", "가나치료비(다라병원(마바포함)(갱신형)"]
    data = {"형식": RR.PIECES_FORMAT, "출처": {"문서": "TEST1_가상상품_상품요약서"}, "조각": [
        piece_of(", ".join(names), names, [("1형", "가나로 치료를 받은 경우")]),
        piece_of("사아진단, 사아진단(갱신형)", ["사아진단", "사아진단(갱신형)"],
                 [("사아진단", "사아로 진단 확정된 경우"), ("사아진단", "자차로 진단 확정된 경우")])]}
    values = {n: {**RR.DEFAULTS, "번호": n, "쪽": 1, "꼴": RR.RATIO, "지급률": 100} for n in ("R001-1", "R002-1", "R002-2")}
    values["R002-1"]["대상"], values["R002-2"]["대상"] = "사아", "자차"
    built = RR.build_rows("TEST_X1_abcdef", RR.load_pieces(data), values, renewal_years=20)
    assert [r["원시특약명"] for r in built.riders] == ["사아진단", "사아진단(갱신형)"]
    assert built.skipped["R001-1"].startswith(RR.HOLD) and "괄호" in built.skipped["R001-1"]
    assert not built.skipped_riders
    # 두 특약 이름이 한 칸에 적힌 추출 단위: 세부보장 이름(갱신형 표시가 없는 특약 이름)과 대상으로 두 특약에 급부 행이 하나씩 생긴다
    assert sorted(b["원시급부명"] for b in built.benefits) == ["사아진단(사아)", "사아진단(사아)", "사아진단(자차)", "사아진단(자차)"]
    assert len({b["급부ID"] for b in built.benefits}) == 4
