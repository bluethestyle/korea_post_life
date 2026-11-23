"""회사별 표 꼴(Layout). 메리츠화재 요약서처럼 표 위 표시와 이름 적는 법이 삼성화재와 다른 표.

시험 자료는 실제 표의 칸 나뉨, 병합, 쪽 넘김 모양만 본떠 손으로 만든 행 목록이다. 담보 이름과 문구는 지어낸 것이다.
칸 값의 뜻은 pdfplumber와 같다. None은 병합으로 따로 칸이 없는 자리, ""는 글자가 없는 칸이다.
"""
import json

import pytest

from postlife.extract import tables
from postlife.extract.tables import (
    MERITZ, SAMSUNGFIRE, Cover, PageTable, Rider, benefit_pages, benefit_ranges, is_note_row, read_riders,
    riders_from_tables, riders_to_json, split_slash, table_lines, table_notes, tidy_slash, write_riders,
)

HEAD = ["보장명", "지급사유", "지급금액"]


def table(page, rows, head=HEAD, label="선택계약", **kw):
    return PageTable(page, [head] + rows, label, **kw)


def riders(*pages):
    return riders_from_tables(pages, MERITZ)


# ---------------------------------------------------------------------------
# 절 찾기와 이름 가르기
# ---------------------------------------------------------------------------

PAGES = {
    3: "1. 가입자격\n(1) 보험가입자격제한",
    5: "2. 보험금 지급사유, 지급금액 및 지급제한사항\n(1) 보험금지급사유 및 지급금액\nm 기본계약\n보장명 지급사유 지급금액",
    6: "보장명 지급사유 지급금액\n가나 진단비",
    7: "다라 진단비\n(2) 보험금 지급제한 사항\n가. 회사는",
}


def test_section_titles_follow_the_layout():
    assert [(r.first_page, r.last_page) for r in benefit_ranges(PAGES, MERITZ)] == [(5, 7)]
    assert benefit_pages(PAGES, layout=MERITZ).first_page == 5
    assert benefit_ranges(PAGES) == []          # 삼성화재 꼴로는 이 절을 찾지 않는다
    with pytest.raises(ValueError, match="□ 보험금 지급사유"):
        benefit_pages(PAGES)


def test_slash_splits_names_only_outside_brackets():
    assert split_slash("가나 사망/가나 사망추가/갱신형 가나 사망") == ("가나 사망", "가나 사망추가", "갱신형 가나 사망")
    assert split_slash("(다라용/마바용)가나 상해사망") == ("(다라용/마바용)가나 상해사망",)
    assert split_slash("가나 진단비(1-5종, 연간1회한)/갱신형 가나 진단비(1~5종, 연간1회한)") == (
        "가나 진단비(1-5종, 연간1회한)", "갱신형 가나 진단비(1~5종, 연간1회한)")
    assert tidy_slash("가나 진단비/ 갱신형 가나 진단비") == "가나 진단비/갱신형 가나 진단비"


def test_names_joined_by_slash_become_parts_and_title_drops_spaces_around_slash():
    [r] = riders(table(5, [["가나 진단비/ \n갱신형 가나 \n진단비", "가나로 진단확정시", "가입금액"]]))
    assert r.title == "가나 진단비/갱신형 가나 진단비"
    assert r.names == ("가나 진단비", "갱신형 가나 진단비")
    assert r.covers[0].name == "가나 진단비/갱신형 가나 진단비"
    # 삼성화재 꼴은 "/"로 가르지 않는다
    [s] = riders_from_tables([table(5, [["가나 진단비/갱신형 가나 진단비", "사유", "가입금액"]])])
    assert s.names == ("가나 진단비/갱신형 가나 진단비",) and s.parts == ()


def test_same_document_gives_same_names_twice():
    page = table(5, [["가나 \n진단비(1년\n50%)/ 갱신형 가나 진단비(1년50%)", "사유", "가입금액"],
                     ["다라 입원일당(1일이 \n상 180일한도)", "사유", "1일당 가입금액"]])
    assert riders(page) == riders(page)
    assert [r.title for r in riders(page)] == ["가나 진단비(1년50%)/갱신형 가나 진단비(1년50%)",
                                               "다라 입원일당(1일이 상 180일한도)"]


# ---------------------------------------------------------------------------
# 구분, 형, 특약 머리
# ---------------------------------------------------------------------------

def test_main_contract_and_segment_come_from_the_marks_above_the_table():
    base = table(5, [["가나 후유장해", "사유", "가입금액"]], label="기본계약", segment="가형")
    rest = table(5, [["다라 사망", "사유", "가입금액"]], label="선택계약", segment="가형")
    other = table(9, [["다라 사망", "사유", "가입금액"]], label="선택계약", segment="나형")
    out = riders(base, rest, other)
    assert [(r.title, r.label, r.main, r.segment) for r in out] == [
        ("가나 후유장해", "기본계약", True, "가형"), ("다라 사망", "선택계약", False, "가형"),
        ("다라 사망", "선택계약", False, "나형")]
    # 삼성화재 꼴은 주계약 표시를 달지 않는다
    assert riders_from_tables([base])[0].main is None


def test_rider_heading_makes_every_row_a_cover_of_that_rider():
    heading = "무배당 가나 다라보장 특별약관2610(가형)"
    first = table(20, [["가나 입원일당(1일이상)", "가나로 입원시", "1일당 가입금액"],
                       ["가나 입원일당(31일이상)", "가나로 31일 이상 입원시", "1일당 가입금액"]],
                  segment="가형", heading=heading)
    # 다음 쪽에서 머리행 없이 이어진 표(head로 칸 번호를 준다)
    rest = PageTable(21, [["다라 수술비", "다라 수술시", "가입금액"]], "선택계약", segment="가형", heading=heading,
                     head=(0, 1, 2))
    [r] = riders(first, rest)
    assert r.title == heading and (r.first_page, r.last_page) == (20, 21)
    assert [c.name for c in r.covers] == ["가나 입원일당(1일이상)", "가나 입원일당(31일이상)", "다라 수술비"]


def test_rider_heading_table_with_split_name_cells_joins_group_and_cover():
    heading = "무배당 가나진단비보장 특별약관2610"
    page = table(30, [["가나진단비", None, "가나로 진단시", "가입금액"],
                      ["통합 \n가나진단비", "소액가나", "소액가나로 진단시", "가입금액"],
                      [None, "특정가나", "특정가나로 진단시", "가입금액"]],
                 head=["보장명", None, "지급사유", "지급금액"], heading=heading)
    # 다음 쪽 첫 행은 묶음 칸이 쪽을 넘어온 빈 칸이다
    rest = table(31, [["", "고액가나", "고액가나로 진단시", "가입금액"]], head=["보장명", None, "지급사유", "지급금액"],
                 heading=heading)
    [r] = riders(page, rest)
    assert [c.name for c in r.covers] == ["가나진단비", "통합 가나진단비 소액가나", "통합 가나진단비 특정가나",
                                          "통합 가나진단비 고액가나"]


def test_three_name_columns_keep_the_middle_level():
    head = ["보장명", None, None, "지급사유", "지급금액"]
    page = table(40, [["26종 가나\n치료비", "가\n나\n치\n료", "다라암", "다라암 치료시", "가입금액"],
                      [None, None, "마바암", "마바암 치료시", "가입금액"],
                      [None, "사\n아\n치\n료", "다라암", "다라암 사아치료시", "가입금액"]], head=head)
    [r] = riders(page)
    assert r.title == "26종 가나치료비"
    assert [c.name for c in r.covers] == ["가나치료 다라암", "가나치료 마바암", "사아치료 다라암"]


def test_split_reason_columns_turn_short_cells_into_cover_names():
    # 지급사유 머리 아래가 "조건 | 지급사유 | 진단 구간"으로 갈린 표. 글이 가장 많은 칸이 지급사유다
    head = ["보장명", "지급사유", None, None, "지급금액"]
    page = table(50, [["가나 지원금", "자가용", "보험기간 중 가나 사고로 피해자에게 상해를 입혀 합의한 경우 지급", "4주미만", "100만원"],
                      [None, None, None, "4주이상", "300만원"],
                      [None, "영업용", "보험기간 중 영업 중 가나 사고로 피해자에게 상해를 입혀 합의한 경우 지급", "4주미만", "50만원"],
                      ["다라 벌금", "보험기간 중 다라 벌금형이 확정된 경우", None, None, "500만원 한도"]], head=head)
    [a, b] = riders(page)
    assert [(c.name, c.amount) for c in a.covers] == [("자가용 4주미만", "100만원"), ("자가용 4주이상", "300만원"),
                                                     ("영업용 4주미만", "50만원")]
    assert a.covers[1].reason == a.covers[0].reason                 # 병합된 지급사유는 위 행에서 물려받는다
    assert "영업 중" in a.covers[2].reason
    assert b.covers[0].name == "다라 벌금" and b.covers[0].reason == "보험기간 중 다라 벌금형이 확정된 경우"


def test_note_rows_are_kept_apart_and_remarks_join_the_rider_above():
    page = table(60, [["가나 진단비", "가나로 진단시※", "가입금액"],
                      [None, "다라로 진단시※", "가입금액의 20%"],
                      ["※ 가나보장개시일은 계약일부터 90일이 지난 다음날", None, None],
                      ["주1) 마바로 인한 경우 감액기간 없음", None, ""]], segment="가형")
    [r] = riders(page)
    assert [c.name for c in r.covers] == ["가나 진단비", "가나 진단비"]
    assert all(c.reason.endswith("※ 가나보장개시일은 계약일부터 90일이 지난 다음날") for c in r.covers)
    assert table_notes([page], MERITZ) == [{"쪽": 60, "형": "가형", "특약머리": "", "글": "주1) 마바로 인한 경우 감액기간 없음"}]
    assert table_notes([page]) == []            # 삼성화재 꼴은 주석을 따로 떼지 않는다
    assert is_note_row(["주) 가나", None, ""]) and not is_note_row(["가나", "", "가입금액"])


def test_remark_row_inside_the_reason_columns_joins_the_rider_above():
    head = ["보장명", "지급사유", None, "지급금액"]
    page = table(70, [["가나 치료비", "소액가나", "소액가나로 치료시※", "가입금액"],
                      [None, "고액가나", "고액가나로 치료시※", "가입금액"],
                      [None, "※ 가나보장개시일은 계약일부터 90일이 지난 다음날", None, ""]], head=head)
    [r] = riders(page)
    assert [c.name for c in r.covers] == ["소액가나", "고액가나"]
    assert r.covers[1].reason == "고액가나로 치료시※\n※ 가나보장개시일은 계약일부터 90일이 지난 다음날"


# ---------------------------------------------------------------------------
# 표 위 표시 읽기
# ---------------------------------------------------------------------------

def marks(lines, layout=MERITZ, state=None):
    state = state or tables._Marks()
    tables._read_marks(lines, state, layout)
    return state


def test_marks_above_tables_set_label_segment_and_rider_heading():
    m = marks(["< 무배당 가나보험2610(가형) >", "m 기본계약"])
    assert (m.label, m.segment, m.heading) == ("기본계약", "가형", "")
    marks(["< 무배당 가나보험2610(나형) >", "m 선택계약"], state=m)
    assert (m.label, m.segment, m.segments) == ("선택계약", "나형", ["가형", "나형"])
    # 특약 머리. 형은 머리의 괄호에서 고르고, 형이 적히지 않았으면 공통이다
    marks(["< 무배당 다라보장 특별약관2610(가형)(감액미적용) >"], state=m)
    assert (m.label, m.segment, m.heading) == ("선택계약", "가형", "무배당 다라보장 특별약관2610(가형)(감액미적용)")
    marks(["< 무배당 마바보장 특별약관2610 >"], state=m)
    assert (m.segment, m.heading) == ("공통", "무배당 마바보장 특별약관2610")
    # 구분 줄이 오면 특약 머리가 끝나고 형은 형 구간 머리의 것으로 돌아간다
    marks(["m 선택계약"], state=m)
    assert (m.segment, m.heading) == ("나형", "")


def test_rider_heading_in_a_label_line_and_wrapped_heading():
    m = marks(["m 무배당 가나 다라보장 특별약관2610"])
    assert (m.heading, m.segment) == ("무배당 가나 다라보장 특별약관2610", "")      # 형 구간이 없는 문서
    m = marks(["< 무배당 가나보험2610", "(가형) >"])
    assert m.segment == "가형"


def test_samsungfire_layout_reads_only_its_own_marks():
    m = marks(["m 기본계약", "◆ 선택계약", "< 무배당 가나보험(가형) >"], SAMSUNGFIRE)
    assert (m.label, m.segment, m.heading) == ("선택계약", "", "")


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def test_layout_values_survive_a_json_round_trip_and_are_left_out_when_unset(tmp_path):
    meritz = Rider("가나 사망/갱신형 가나 사망", (Cover("가나 사망/갱신형 가나 사망", "사유", "가입금액", 5),), 5, 5,
                   "기본계약", "", "가형", True, ("가나 사망", "갱신형 가나 사망"))
    plain = Rider("다라 진단비", (Cover("다라 진단비", "사유", "가입금액", 6),), 6, 6, "선택계약")
    path = tmp_path / "조각.json"
    note = {"쪽": 6, "형": "가형", "특약머리": "", "글": "주1) 가나"}
    write_riders(path, [meritz, plain], {"문서": "가나보험"}, [note])
    assert read_riders(path) == [meritz, plain]
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["주석"] == [note]
    assert {k: saved["조각"][0][k] for k in ("형", "주계약", "특약명들")} == {
        "형": "가형", "주계약": True, "특약명들": ["가나 사망", "갱신형 가나 사망"]}
    assert not {"형", "주계약", "특약명들"} & set(saved["조각"][1])
    assert "주석" not in riders_to_json([plain])
    assert "형: 가형" in meritz.text and "주계약: 예" in meritz.text and "형:" not in plain.text


def test_layouts_are_listed_by_name():
    assert tables.LAYOUTS == {"samsungfire": SAMSUNGFIRE, "meritz": MERITZ, "kblife": tables.KBLIFE}
    # 보장명 칸이 하나인 표: 삼성화재 꼴은 세부보장 칸이 없고, 메리츠화재 꼴도 이름의 단이 없다
    assert table_lines(table(1, [["가나", "사유", "가입금액"]]))[0].cover is None
    assert table_lines(table(1, [["가나", "사유", "가입금액"]]), MERITZ)[0].levels == ()
