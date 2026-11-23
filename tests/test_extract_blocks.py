"""생명보험사 요약서의 특약별 작은 표(blocks.py).

시험 자료는 삼성생명 요약서의 꼴(소절 제목, 기준 줄, "특약명 | 지급사유 | 지급금액" 작은 표, "□ 이름" 줄, "㈜" 풀이 문단,
머리행 없이 이어지는 표)만 본떠 손으로 만든 것이다. 특약과 담보 이름, 문구는 지어낸 것이다.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from postlife.extract import blocks as B
from postlife.extract import reader_rows as RR
from postlife.extract import tables as T
from postlife.extract.blocks import Row, Table, Text

_SPLIT = importlib.util.spec_from_file_location(
    "split_pieces", Path(__file__).resolve().parents[1] / "scripts" / "split_pieces.py")
split_pieces = importlib.util.module_from_spec(_SPLIT)
_SPLIT.loader.exec_module(split_pieces)


def head(*lines, page=1):
    return [Text(page, line) for line in lines]


def run(*items):
    flat = []
    for item in items:
        flat += item if isinstance(item, list) else [item]
    return B.pieces(flat)


MAIN = head("2. 보험금 지급사유", "가. 주계약", "(기준 : 주보험 보험가입금액)")
RIDERS = head("나. 선택특약", "※ 각 선택특약의 보험기간은 주계약과 다를 수 있습니다.")


# ---------------------------------------------------------------------------
# 소절과 특약
# ---------------------------------------------------------------------------

def test_main_part_table_names_covers_and_marks_main():
    result = run(MAIN, Table(1, (
        Row(1, "가나\n사망보험금", "피보험자가 사망하였을 경우", (("", "보험가입금액 100%"),)),
        Row(1, "다라입원\n보험금", "[1종, 2종]\n입원하였을 경우", (("", "2만원"),)),
        Row(1, None, "[3종]\n4일이상 입원하였을 경우", (("", "2만원"),)),
    ), mode="급부"))
    [r] = result.riders
    assert (r.title, r.label, r.main) == ("주계약", "기본계약", True)
    assert [c.name for c in r.covers] == ["가나사망보험금", "다라입원보험금", "다라입원보험금"]
    assert [c.only for c in r.covers] == ["", "1종,2종", "3종"]        # 지급사유 첫머리의 종 표시를 뗀다
    assert r.covers[1].reason == "입원하였을 경우"
    assert result.notes[0] == {"쪽": 1, "형": "", "특약머리": "주계약", "글": "(기준 : 주보험 보험가입금액)"}


def test_sub_heads_in_main_part_become_their_own_pieces():
    result = run(MAIN, Table(1, (Row(1, "가나보험금", "사망시", (("", "100%"),)),), mode="급부"),
                 head("나. 가나보장플랜", "① 가나사망보장플랜", "(가나보장플랜 보험가입금액 1,000万)", page=2),
                 Table(2, (Row(2, "가나사망보험금", "사망시", (("", "1,000만원"),)),), mode="급부"))
    assert [(r.title, r.label, r.main) for r in result.riders] == [
        ("주계약", "기본계약", True), ("가나사망보장플랜", "기본계약", True)]


def test_rider_table_reads_names_from_box_lines_and_scope_from_title():
    result = run(MAIN, RIDERS, head("[기준 : 특약보험가입금액 1,000만원]"), Table(1, (
        Row(1, "가나진단특약C\n(무배당,저해약\n환급금형)\n[1,2,3종]",
            "□ 가나 진단보험금\n피보험자가 「가나」로\n진단 확정되었을 때(최초1회한)",
            (("1년이내", "[1종,2종]\n1,000만원\n[3종]\n500만원"), ("1년초과", "1,000만원"))),
        Row(1, None, "□[3종]다라 진단보험금\n「다라」로 진단 확정시", (("1년이내", "500만원"),)),
    )))
    r = result.riders[0]
    assert (r.title, r.only, r.label, r.main) == ("가나진단특약C(무배당,저해약환급금형)", "1,2,3종", "선택특약", False)
    assert [c.name for c in r.covers] == ["가나 진단보험금", "다라 진단보험금"]
    assert r.covers[0].reason == "피보험자가 「가나」로진단 확정되었을 때(최초1회한)"
    assert r.covers[0].amount == "1년이내: [1종,2종] 1,000만원 [3종] 500만원\n1년초과: 1,000만원"
    assert r.covers[1].only == "3종"
    assert result.notes[0]["글"] == "[기준 : 특약보험가입금액 1,000만원]"
    assert result.notes[0]["특약머리"] == r.title


def test_group_rows_give_names_to_rows_below_and_dash_lines_add_sub_names():
    result = run(MAIN, RIDERS, Table(1, (
        Row(1, "가나관련질환진단특약", "□ 통합가나진단보험금", (("1년이내", ""), ("1년초과", ""))),
        Row(1, None, "- 다라 진단보험금\n피보험자가 「다라」로 진단 확정시", (("1년이내", "250만원"), ("1년초과", "500만원"))),
        Row(1, None, "- 마바 진단보험금\n「마바」로 진단 확정시", (("1년이내", "125만원"), ("1년초과", "250만원"))),
        Row(1, None, "□ 가나암 진단보험금", ()),
        Row(1, None, "「가나암 보장개시일」 이후 「위암」으로 진단 확정", (("", "1,000만원"),)),
        Row(1, None, "「가나암 보장개시일」 이후 「간암」으로 진단 확정", (("", "1,000만원"),)),
        Row(1, None, "□ 사라 치료보험금", ()),
        Row(1, None, "- 가나를 1회이상 받은 경우 (최초 1회한)", (("", "500만원"),)),     # 문장이라 하위 이름이 아니다
    )))
    names = [c.name for c in result.riders[0].covers]
    assert names == ["통합가나진단보험금 다라 진단보험금", "통합가나진단보험금 마바 진단보험금",
                     "가나암 진단보험금", "가나암 진단보험금", "사라 치료보험금"]
    assert result.riders[0].covers[-1].reason == "- 가나를 1회이상 받은 경우 (최초 1회한)"
    assert B.stats(result)["이름같은 묶음"] == 1 and B.stats(result)["이름같은 줄"] == 2


def test_box_row_with_reason_but_no_amount_is_a_condition_for_rows_below():
    result = run(MAIN, RIDERS, Table(1, (
        Row(1, "가나치료특약", "□ 가나치료보험금\n「가나」의 치료를 받은 경우", (("1년이내", ""),)),
        Row(1, None, "\"가나 연도\"가 1차년도인 경우", (("1년이내", "300만원"),)),
        Row(1, None, "\"가나 연도\"가 2차년도인 경우", (("1년이내", "200만원"),)),
        Row(1, None, "□ 다라치료보험금\n「다라」의 치료를 받은 경우", (("1년이내", ""),)),
    )))
    covers = result.riders[0].covers
    assert [c.name for c in covers] == ["가나치료보험금"] * 2 + ["다라치료보험금"]
    assert covers[0].reason == "「가나」의 치료를 받은 경우\n\"가나 연도\"가 1차년도인 경우"
    assert covers[1].amount == "1년이내: 200만원"
    assert (covers[2].reason, covers[2].amount) == ("「다라」의 치료를 받은 경우", "")   # 물려받는 행이 없으면 그대로 남긴다


def test_rider_whose_name_is_printed_on_the_next_page_gets_it_from_the_continued_table():
    result = run(MAIN, RIDERS,
                 Table(1, (Row(1, "가나특약", "□ 가나보험금\n가나시", (("", "10만원"),)),)),
                 Table(2, (Row(2, "", "□ 다라보험금\n다라시", (("", "5만원"),)),)),              # 이름 칸이 빈 새 표
                 Table(3, (Row(3, "다라통합특약\n[1,2,3종]", "□ 다라보험금\n다라시 2", (("", "6만원"),)),),
                       headless=True))
    assert [(r.title, r.only, len(r.covers), r.first_page, r.last_page) for r in result.riders] == [
        ("가나특약", "", 1, 1, 1), ("다라통합특약", "1,2,3종", 2, 2, 3)]


def test_continued_table_without_name_column_keeps_the_rider_and_joins_a_cut_row():
    result = run(MAIN, RIDERS,
                 Table(1, (Row(1, "가나특약", "□ 가나보험금\n피보험자가 가나로", (("", "10만원"),)),)),
                 Table(2, (Row(2, None, "진단 확정시", ()),
                           Row(2, None, "□ 다라보험금\n다라시", (("", "5만원"),))), headless=True))
    [r] = result.riders
    assert [c.reason for c in r.covers] == ["피보험자가 가나로\n진단 확정시", "다라시"]
    assert r.last_page == 2
    assert any("잘린 행" in e["이유"] for e in result.events)


# ---------------------------------------------------------------------------
# 이름 다듬기
# ---------------------------------------------------------------------------

def test_wrapped_box_names_are_joined_only_for_name_pieces():
    def name(*lines):
        return B._name_lines(list(lines))[0]
    assert T.join_name(name("가나치료보장보험", "금", "피보험자가")) == "가나치료보장보험금"
    assert T.join_name(name("가나치료비(종합병원이상)보", "험금[가나 치료(검사)]", "피보험자가")) == \
        "가나치료비(종합병원이상)보험금[가나 치료(검사)]"
    assert T.join_name(name("가나치료비보험금_다라마", "바치료(검사)", "피보험자가")) == "가나치료비보험금_다라마바치료(검사)"
    assert T.join_name(name("가나특정치료", "(수술)보험금(다라 제외)", "간편고지형: 피보험자가")) == \
        "가나특정치료(수술)보험금(다라 제외)"
    assert T.join_name(name("가나보험금", "(단, 다라는 제외)")) == "가나보험금"            # "(단, …)"은 지급사유
    assert T.join_name(name("가나보험금", "(최초 진단 확정된 경우에 한함)")) == "가나보험금"   # 문장의 말이 든 괄호
    assert T.join_name(name("가나(다라", "마바)보험금", "사아")) == "가나(다라마바)보험금"   # 괄호가 닫힐 때까지


def test_clean_name_splits_trailing_variant_scope_and_mends_brackets():
    assert B.clean_name("가나특약C\n(무배당,\n저해약환급금형)\n[1,2,3종]") == ("가나특약C(무배당,저해약환급금형)", "1,2,3종")
    assert B.clean_name("가나특약[다라ㆍ마바]특약C(무배당") == ("가나특약[다라ㆍ마바]특약C(무배당)", "")
    assert B.clean_name("가나특약 [1종, 2종]") == ("가나특약", "1종,2종")


def test_amount_lines_join_with_spaces_only_between_items():
    assert B.join_amount("[1종,2종]\n1,000만원\n[3종]\n500만원") == "[1종,2종] 1,000만원 [3종] 500만원"
    assert B.join_amount("250/375/500만\n원") == "250/375/500만원"
    assert B.join_amount("1,000/2,500/\n2,500만원") == "1,000/2,500/2,500만원"
    assert B.join_amount("1종 5만원\n2종 10만원") == "1종 5만원 2종 10만원"
    assert B.join_amount("500만원\n(최대10년간,\n연간 1회 한\n도)") == "500만원 (최대10년간,연간 1회 한도)"
    assert B.amount_text((("90일이내, 1년이내", "25만원"), ("1년초과", "50만원"), ("x", ""))) == \
        "90일이내, 1년이내: 25만원\n1년초과: 50만원"


def test_name_check_counts_broken_brackets_sentences_and_glued_names():
    assert B.name_faults("가나 진단보험금(최초1회한") == ["괄호가 안 닫힘"]
    assert B.name_faults("가나보험금다라보험금") == ["두 이름이 붙음"]
    assert B.name_faults("가나보험금 피보험자가 진단 확정시") == ["이름에 문장이 섞임"]
    assert B.name_faults("가나치료비(종합병원이상)보험금[가나 치료(검사)]") == []
    rider = T.Rider("가나특약(무배당", (T.Cover("통합가나보험금 다라 진단보험금", "다라로 진단시", "10만원", 1),
                                    T.Cover("가나보험금□다라보험금", "", "", 1)), 1, 1)
    issues = B.check_names([rider])
    assert [(i["번호"], i["문제"]) for i in issues] == [
        ("R001", "특약 이름: 괄호가 안 닫힘"), ("R001-2", "두 이름이 붙음")]


# ---------------------------------------------------------------------------
# 풀이 문단과 조각 파일
# ---------------------------------------------------------------------------

def test_notes_below_a_table_go_to_its_riders_and_stop_at_the_next_section():
    result = run(MAIN, RIDERS,
                 head("[기준 : 특약보험가입금액 100만원]"),
                 Table(1, (Row(1, "가나특약", "□ 가나보험금\n가나시", (("", "10만원"),)),)),
                 head("㈜ 1. 보험료 납입기간 중 가나가", "되면 납입을 면제합니다.", "- 1 -", page=1),
                 head("2. 가나는 다라를 받은 뒤의", "첫 날부터 지급합니다.", page=2),
                 head("3. 일반적인 보험금 지급제한사항", "가. 회사는 다음 중 어느 하나로", page=2))
    [r] = result.riders
    texts = [n["글"] for n in result.notes if n["특약머리"] == r.title]
    assert texts == ["[기준 : 특약보험가입금액 100만원]",
                     "㈜ 1. 보험료 납입기간 중 가나가되면 납입을 면제합니다.\n2. 가나는 다라를 받은 뒤의첫 날부터 지급합니다."]
    assert B.stats(result)["기준 줄"] == {"[기준:특약보험가입금액100만원]": 1}


def test_pieces_file_feeds_split_pieces_and_reader_rows_unchanged(tmp_path):
    items = [*MAIN, Table(1, (Row(1, "가나보험금", "사망시", (("", "100%"),)),), mode="급부"),
             *RIDERS, Table(2, (Row(2, "다라특약[1,2,3종]", "□ 다라보험금\n다라시", (("", "10만원"),)),
                                Row(2, None, "□ 다라보험금\n다라 재발시", (("", "5만원"),)))),
             Text(2, "㈜ 1. 다라는 1회만 지급합니다.")]
    files = []
    for k in range(2):                      # 같은 차례를 두 번 읽으면 조각 파일이 바이트까지 같다
        result = B.pieces(items)
        path = tmp_path / f"pieces{k}.json"
        T.write_riders(path, result.riders, {"문서": "가나_요약서", "꼴": "samsunglife"}, result.notes)
        files.append(path.read_bytes())
    assert files[0] == files[1]
    data = json.loads(files[0])
    assert [p["주계약"] for p in data["조각"]] == [True, False]
    assert data["조각"][1]["적용범위"] == "1,2,3종"
    [bundle] = split_pieces.split(data, "가나")
    piece = bundle["조각"][1]
    assert piece["주석"] == ["㈜ 1. 다라는 1회만 지급합니다."]
    assert [c.get("이름같은줄", False) for c in piece["세부보장"]] == [True, True]
    views = RR.load_pieces(data)
    assert [c.number for c in views[1].covers] == ["R002-1", "R002-2"]
    assert views[0].notes == ("(기준 : 주보험 보험가입금액)",)


# ---------------------------------------------------------------------------
# 표의 선으로 칸 읽기 (pdfplumber 없이 선과 글자를 지어내 본다)
# ---------------------------------------------------------------------------

def chars(text, x, y, start=0):
    out = []
    for i, ch in enumerate(text):
        x0 = x + 6 * i
        out.append({"text": ch, "x0": x0, "x1": x0 + 6, "top": y, "bottom": y + 8, "n": start + i,
                    "at": (x0 + 3, y + 4)})
    return out


def hline(y, x0, x1):
    return {"x0": x0, "x1": x1, "top": y, "bottom": y, "orientation": "h"}


def vline(x, y0, y1):
    return {"x0": x, "x1": x, "top": y0, "bottom": y1, "orientation": "v"}


def test_rows_follow_cell_lines_for_merged_name_and_amount_cells():
    # 이름 칸(0~100)은 두 행에 걸쳐 병합, 지급사유(100~300), 지급금액은 300~400 | 400~500 두 하위 칸.
    # 첫 행의 지급금액은 두 하위 칸이 옆으로 병합, 둘째·셋째 행의 둘째 하위 칸은 위아래로 병합.
    h = [hline(100, 0, 500), hline(140, 100, 400), hline(180, 0, 400), hline(220, 0, 500)]
    v = [vline(0, 100, 220), vline(100, 100, 220), vline(300, 100, 220), vline(500, 100, 220), vline(400, 140, 220)]
    cs =(chars("가나특약", 10, 110, 0) + chars("□ 가나보험금", 110, 110, 10) + chars("10만원", 320, 110, 20)
          + chars("□ 다라보험금", 110, 150, 30) + chars("5만원", 320, 150, 40) + chars("7만원", 420, 160, 45)
          + chars("다라특약", 10, 190, 50) + chars("□ 마바보험금", 110, 190, 60) + chars("3만원", 320, 190, 70))
    cols = B._Columns(0, 100, (300, 400, 500), ("1년이내", "1년초과"), "특약")
    t = SimpleNamespace(bbox=(0, 100, 500, 220))
    rows = B._rows(t, cs, h, v, cols, 100, 100, 5)
    assert [r.name for r in rows] == ["가나특약", None, "다라특약"]
    assert [r.reason for r in rows] == ["□ 가나보험금", "□ 다라보험금", "□ 마바보험금"]
    assert rows[0].amounts == (("1년이내, 1년초과", "10만원"),)
    assert rows[1].amounts == (("1년이내", "5만원"), ("1년초과", "7만원"))
    assert rows[2].amounts == (("1년이내", "3만원"), ("1년초과", "7만원"))        # 위아래로 병합된 칸은 물려받는다


def test_header_finds_sub_columns_and_their_labels():
    cells = {
        "head": [(0, 0, 100, 40), (100, 0, 300, 40), (300, 0, 500, 20)],
        "sub": [(300, 20, 400, 40), (400, 20, 500, 40)],
    }
    cs = (chars("특약명", 10, 10, 0) + chars("지급사유", 110, 10, 5) + chars("지급금액", 310, 5, 10)
          + chars("1년이내", 310, 25, 20) + chars("1년초과", 410, 25, 30))
    t = SimpleNamespace(
        bbox=(0, 0, 500, 200),
        rows=[SimpleNamespace(cells=cells["head"] + [None], bbox=(0, 0, 500, 20)),
              SimpleNamespace(cells=[None, None] + cells["sub"], bbox=(0, 20, 500, 40))],
        cells=cells["head"] + cells["sub"])
    cols, body_top, amount_top = B._header(t, cs, [], B.SAMSUNGLIFE, None)
    assert (cols.reason, cols.subs, cols.labels, cols.mode) == (100, (300.0, 400.0, 500), ("1년이내", "1년초과"), "특약")
    assert (body_top, amount_top) == (40, 40)
    # 하위 칸 머리 없이 세로선만 있으면 칸 차례를 머리로 쓴다
    t2 = SimpleNamespace(bbox=(0, 0, 500, 200), rows=[SimpleNamespace(cells=cells["head"], bbox=(0, 0, 500, 20))],
                         cells=cells["head"])
    cols2, _, _ = B._header(t2, cs[:20], [vline(400, 20, 200)], B.SAMSUNGLIFE, None)
    assert (cols2.subs, cols2.labels) == ((300, 400, 500), ("하위 칸 1", "하위 칸 2"))
