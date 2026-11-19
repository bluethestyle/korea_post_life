"""급부 표의 행을 특별약관 단위 조각으로 묶기.

시험 자료는 실제 표의 칸 나뉨과 쪽 넘김 모양만 본떠 손으로 만든 행 목록이다. 담보 이름과 문구는 지어낸 것이다.
칸 값의 뜻은 pdfplumber와 같다. None은 병합으로 따로 칸이 없는 자리, ""는 글자가 없는 칸이다.
"""
import json
from types import SimpleNamespace

import pytest

from postlife.extract import tables
from postlife.extract.segment import Block, pages_from_text
from postlife.extract.tables import (
    Cover, Line, PageTable, Rider, applies_to, benefit_pages, benefit_ranges, for_variant, group_riders,
    join_name, join_text, name_key, read_riders, riders_from_json, riders_from_tables, riders_to_json, split_names,
    split_only, squash, table_lines, to_blocks, write_riders,
)

# 머리행은 병합 때문에 세 행으로 갈려 읽힌다. 보장명 칸이 하나인 표와 둘로 갈린 표
HEAD3 = [["보장명", "", "지급금액"], [None, "지급사유", None], [None, "", None]]
HEAD4 = [["보장명", None, "", "지급금액"], [None, None, "지급사유", None], [None, None, "", None]]


def table(page, rows, label="선택계약", open_end=False):
    head = HEAD3 if len(rows[0]) == 3 else HEAD4
    return PageTable(page, head + rows, label, open_end)


# ---------------------------------------------------------------------------
# 칸 글자 잇기
# ---------------------------------------------------------------------------

def test_name_broken_inside_a_word_is_joined_without_space():
    # 줄 끝에 빈칸이 없으면 낱말 가운데서 바뀐 줄이다
    assert join_name("[갱신\n형][간편]\n가나 다라\n마바 수술\n비(1년 감\n액)") == "[갱신형][간편]가나 다라마바 수술비(1년 감액)"


def test_name_broken_between_words_keeps_one_space():
    assert join_name("가나 종합병원 \n입원일당(1일이상) ") == "가나 종합병원 입원일당(1일이상)"


def test_name_drops_trailing_comma_and_space_after_leading_tags():
    assert join_name("가나 진단비(다라 제외), ") == "가나 진단비(다라 제외)"
    assert join_name("[갱신형] \n[간편] \n가나 진단비 \n(1년50%) ") == "[갱신형][간편]가나 진단비 (1년50%)"
    assert join_name(None) == "" and join_name("  \n ") == ""


def test_text_lines_are_joined_into_paragraphs():
    cell = ("보험기간 중 가나다라마\n바사로 진단 확정된 경우 \n(최초 1회한 지급) \n"
            "※ 가나의 보장개시일은 계약일부터 90\n일이 지난날의 다음날임 \n※ 다라는 마바, 사아임 ")
    assert join_text(cell) == ("보험기간 중 가나다라마바사로 진단 확정된 경우 (최초 1회한 지급)\n"
                               "※ 가나의 보장개시일은 계약일부터 90일이 지난날의 다음날임\n"
                               "※ 다라는 마바, 사아임")


def test_amount_lines_keep_list_items_apart():
    assert join_text("- 가나 : \n가입금액의 \n20% \n- 가나 외 \n: \n가입금액의 \n100% ") == \
        "- 가나 : 가입금액의 20%\n- 가나 외 : 가입금액의 100%"
    assert join_text("▷비관혈수\n술 \n: 가입금액 \n▷관혈수술 \n: 가입금액 ") == "▷비관혈수술 : 가입금액\n▷관혈수술 : 가입금액"
    assert join_text("가입금액 \n※ 단, 가나, 다라는 \n가입금액의 20% ") == "가입금액\n※ 단, 가나, 다라는 가입금액의 20%"


def test_blank_line_starts_a_new_paragraph():
    assert join_text("가나 수술을 받은 경우 \n\n· 관혈: 다라 \n\n마바 사아 ") == "가나 수술을 받은 경우\n· 관혈: 다라\n마바 사아"


def test_name_key_ignores_tags_spaces_and_dot_shapes():
    assert name_key("[건강]가나∙다라 진단비(1년50%)") == name_key("가나·다라 진단비 (1년50%),")
    assert name_key("[갱신형][간편]가나 진단비") == "가나진단비"
    assert squash("가 나\nㆍ다") == "가나·다"


def test_names_written_together_in_one_cell_are_split():
    title = "[갱신형][간편]가나 치료비(진단 후 10년, 연간1회한)(1년50%), [갱신형][간편]가나 치료비(진단 후 10년, 연간1회한)(기가입자용)"
    assert split_names(title) == ("[갱신형][간편]가나 치료비(진단 후 10년, 연간1회한)(1년50%)",
                                  "[갱신형][간편]가나 치료비(진단 후 10년, 연간1회한)(기가입자용)")
    # 쉼표가 빠진 채 대괄호 표시가 새로 시작해도 가른다
    assert split_names("[갱신형]가나 치료비(1년50%) [갱신형]다라 치료비(1년50%)") == \
        ("[갱신형]가나 치료비(1년50%)", "[갱신형]다라 치료비(1년50%)")
    # 쉼표 앞이 닫는 괄호가 아니면 이름 하나다
    assert split_names("가나, 다라 양성종양 진단비(연간1회한)") == ("가나, 다라 양성종양 진단비(연간1회한)",)


# ---------------------------------------------------------------------------
# 행을 역할별로 읽기
# ---------------------------------------------------------------------------

def test_header_rows_are_skipped_and_columns_are_found():
    lines = table_lines(table(10, [
        ["가나 수술비", "가나 입원 수술비", "가나로 입원하여 수술을 받은 경우", "가입금액"],
        [None, "가나 통원 수술비", "가나로 통원하여 수술을 받은 경우", "가입금액"],
    ]))
    assert [(l.rider, l.cover, l.amount, l.top) for l in lines] == [
        ("가나 수술비", "가나 입원 수술비", "가입금액", True), (None, "가나 통원 수술비", "가입금액", False)]
    assert all(l.page == 10 and l.label == "선택계약" for l in lines)


def test_single_name_column_has_no_cover_cell():
    (line,) = table_lines(table(10, [["가나 진단비", "가나로 진단 확정된 경우", "가입금액"]]))
    assert (line.rider, line.cover, line.reason) == ("가나 진단비", None, "가나로 진단 확정된 경우")


def test_table_with_other_header_is_not_a_benefit_table():
    assert table_lines(PageTable(10, [["유형", "피보험자"], ["1형", "남자"]])) == []
    assert table_lines(PageTable(10, [["보장명", "지급제한사항"], ["가나 진단비", "다라"]])) == []


def test_cover_name_is_found_in_whichever_name_column_holds_it():
    # 한 쪽 안에서 보장명 칸의 세로선 자리가 달라 보장명 칸이 셋으로 읽히는 표
    head = [["보장명", None, None, "", "지급금액"], [None, None, None, "지급사유", None]]
    lines = table_lines(PageTable(10, head + [
        ["가나 진단비", "가나(중복) 진단비", None, "사유1", "가입금액"],
        ["다라 진단비", None, None, "사유2", "가입금액"],
        ["마바 진단비", None, "마바(위) 진단비", "사유3", "해당 세부보장의 가입금액"],
        [None, None, "마바(간) 진단비", "사유4", None],
    ]))
    assert [(l.rider, l.cover) for l in lines] == [
        ("가나 진단비", "가나(중복) 진단비"), ("다라 진단비", None), ("마바 진단비", "마바(위) 진단비"), (None, "마바(간) 진단비")]
    assert lines[3].amount is None


def test_reason_split_into_several_cells_is_read_as_one():
    head = [["보장명", "", None, "지급금액"], [None, "지급사유", None, None]]
    (line,) = table_lines(PageTable(10, head + [["가나 수술비", "가나 수술을 받은 경우", "다라 목록", "가입금액"]]))
    assert line.reason == "가나 수술을 받은 경우\n다라 목록" and line.amount == "가입금액"


# ---------------------------------------------------------------------------
# 특별약관 단위로 묶기
# ---------------------------------------------------------------------------

def test_each_named_row_is_a_rider_and_merged_rows_are_its_covers():
    riders = riders_from_tables([table(10, [
        ["가나 진단비", None, "가나로 진단 확정된 경우", "가입금액"],
        ["다라 입원·통원 \n수술비(1년 감액) ", "다라 통원 수술비\n(외래) ", "통원하여 수술을 받은 경우", "가입금액"],
        [None, "다라 입원 수술비\n(당일입원 제외) ", "입원하여 수술을 받은 경우", "가입금액의 50%"],
        ["마바 진단비, ", None, "마바로 진단 확정된 경우", "가입금액"],
    ])])
    assert [r.title for r in riders] == ["가나 진단비", "다라 입원·통원 수술비(1년 감액)", "마바 진단비"]
    assert [[c.name for c in r.covers] for r in riders] == [
        ["가나 진단비"], ["다라 통원 수술비(외래)", "다라 입원 수술비(당일입원 제외)"], ["마바 진단비"]]
    assert [c.amount for c in riders[1].covers] == ["가입금액", "가입금액의 50%"]
    assert all((r.first_page, r.last_page, r.label) == (10, 10, "선택계약") for r in riders)


def test_merged_amount_cell_is_filled_down():
    (rider,) = riders_from_tables([table(10, [
        ["가나 통합 진단비", "가나(위) 진단비", "사유1", "해당 \n세부보장의 \n가입금액 "],
        [None, "가나(간) 진단비", "사유2", None],
        [None, "가나(폐) 진단비", "사유3", None],
    ])])
    assert [c.amount for c in rider.covers] == ["해당 세부보장의 가입금액"] * 3


def test_rider_continues_on_next_page_with_its_name_repeated():
    # 쪽이 바뀌면 특별약관 이름이 다시 적히고, 병합된 지급금액 칸은 빈 채로 넘어온다
    riders = riders_from_tables([
        table(10, [["가나 통합 \n진단비 ", "가나(위) 진단비", "보장개시일 이후 가나(위)로 진단 확정된 경우", "해당 세부보장의 가입금액"],
                   [None, "가나(간) 진단비", "보장개시일 이후 가나(간)으로 진단 확정된 경우", None]]),
        table(11, [["가나 통합 \n진단비 ", "가나(폐) 진단비", "보장개시일 이후 가나(폐)로 진단 확정된 경우", ""],
                   [None, "가나(뇌) 진단비", "보장개시일 이후 가나(뇌)로 진단 확정된 경우", None],
                   ["다라 진단비", None, "다라로 진단 확정된 경우", "가입금액"]]),
    ])
    assert [r.title for r in riders] == ["가나 통합 진단비", "다라 진단비"]
    first = riders[0]
    assert [(c.name, c.page) for c in first.covers] == [
        ("가나(위) 진단비", 10), ("가나(간) 진단비", 10), ("가나(폐) 진단비", 11), ("가나(뇌) 진단비", 11)]
    assert {c.amount for c in first.covers} == {"해당 세부보장의 가입금액"}
    assert (first.first_page, first.last_page) == (10, 11)


def test_rider_continues_on_next_page_with_empty_name_cell():
    # 쪽 첫 행의 특별약관 칸이 비어 있고 세부보장 이름이 새로 나오면 앞 특별약관의 다음 세부보장이다.
    # 같은 쪽 아래에서 특별약관 이름이 다시 적혀도 같은 특별약관이다
    riders = riders_from_tables([
        table(10, [["[갱신형][간편]\n가나 수술비 ", "[갱신형][간편]가나 수술비(5대)", "5대 수술을 받은 경우", "가입금액"]]),
        table(11, [["", "[갱신형][간편]가나 수술비(22대)", "22대 수술을 받은 경우", "가입금액"],
                   ["[갱신형][간편]\n가나 수술비 ", "[갱신형][간편]가나 수술비(3대)", "3대 수술을 받은 경우", "가입금액"],
                   [None, "[갱신형][간편]가나 수술비(19대)", "19대 수술을 받은 경우", "가입금액"]]),
    ])
    assert len(riders) == 1 and riders[0].title == "[갱신형][간편]가나 수술비"
    assert [c.name.rsplit("(", 1)[1] for c in riders[0].covers] == ["5대)", "22대)", "3대)", "19대)"]


def test_merged_amount_carried_over_the_page_break_is_inherited():
    # 쪽 첫 행이 새 세부보장인데 지급금액 칸이 비었으면 앞 쪽에서 병합된 칸이 넘어온 것이다
    (rider,) = riders_from_tables([
        table(10, [["가나 치료비(급여)", "가나 치료비(뇌)(급여)", "보험기간 중 뇌 치료를 받은 경우(최초 1회한 지급)", "가입금액"]]),
        table(11, [["", "가나 치료비(심장)(급여)", "보험기간 중 심장 치료를 받은 경우(최초 1회한 지급)", ""]]),
    ])
    assert [(c.name, c.amount) for c in rider.covers] == [
        ("가나 치료비(뇌)(급여)", "가입금액"), ("가나 치료비(심장)(급여)", "가입금액")]


def test_row_cut_at_page_end_is_joined_cell_by_cell():
    # 행 하나가 쪽 끝에서 잘려 이름과 지급사유가 두 쪽에 나뉘어 적혔다. 앞 표의 open_end가 그 사실을 알려 준다
    riders = riders_from_tables([
        table(10, [["[갱신\n형][간편]\n가나병원 ", "[갱신\n형][간편]\n가나병원 ", "보장개시일 이후 다라로 진단확정되고, 가나병원에서\n치료를 받은 경우 각 치료행위별 ", "가입금액 "]],
              open_end=True),
        table(11, [["다라 치\n료비Ⅱ(1년\n50%) ", "다라(마바\n제외) \n치료비Ⅱ ", "연간 1회에 한하여 가입금액 지급 \n※ 다라의 보장개시일은 계약일임 ", ""],
                   [None, "[갱신\n형][간편]\n가나병원 \n마바 치료비Ⅱ ", "보장개시일 이후 마바로 진단확정된 경우", "가입금액 "]]),
    ])
    (rider,) = riders
    assert rider.title == "[갱신형][간편]가나병원 다라 치료비Ⅱ(1년50%)"
    assert [c.name for c in rider.covers] == ["[갱신형][간편]가나병원 다라(마바제외) 치료비Ⅱ", "[갱신형][간편]가나병원 마바 치료비Ⅱ"]
    assert rider.covers[0].reason == ("보장개시일 이후 다라로 진단확정되고, 가나병원에서치료를 받은 경우 각 치료행위별 연간 1회에 한하여 가입금액 지급\n"
                                      "※ 다라의 보장개시일은 계약일임")
    assert rider.covers[0].amount == "가입금액" and (rider.covers[0].page, rider.last_page) == (10, 11)


def test_cut_row_is_recognised_without_open_end_flag():
    # 이름의 괄호가 앞 쪽에서 열린 채 끝났거나, 넘어온 행에 지급사유가 없거나 "※"로 시작하면 이어지는 행이다
    riders = riders_from_tables([
        table(10, [["가나 일당", "가나 통원일당(연간\n10회한)(1", "가나로 통원한 경우 \n※ 1년 미만은 50% 감액 지급 ", "가입금액"]]),
        table(11, [["", "년50%) ", "", ""],
                   [None, "다라 통원일당(1", "다라로 통원한 경우", "가입금액"]]),
        table(12, [["", "년감액) ", "※ 180일 미만은 가입금액의 10% 지급 ", ""],
                   ["마바 수술비 (1년", None, "마바 수술을 받은 경우", "가입금액"]]),
        table(13, [["감액) ", None, "※ 1년 미만은 가입금액의 50% 지급", ""]]),
    ])
    assert [r.title for r in riders] == ["가나 일당", "마바 수술비 (1년감액)"]
    assert [c.name for c in riders[0].covers] == ["가나 통원일당(연간10회한)(1년50%)", "다라 통원일당(1년감액)"]
    assert riders[0].covers[1].reason == "다라로 통원한 경우\n※ 180일 미만은 가입금액의 10% 지급"
    assert riders[1].covers[0].reason == "마바 수술을 받은 경우\n※ 1년 미만은 가입금액의 50% 지급"
    assert (riders[0].last_page, riders[1].first_page, riders[1].last_page) == (12, 12, 13)


def test_nameless_row_at_page_top_continues_the_previous_cover():
    riders = riders_from_tables([
        table(10, [["가나 진단비", "가나로 진단 확정된 경우 \n※ 가나의 보장개시일은 계약일임 ", "가입금액"]]),
        table(11, [["", "※ 1년 미만은 50% 감액 지급 ", ""], ["다라 진단비", "다라로 진단 확정된 경우", "가입금액"]]),
    ])
    assert [r.title for r in riders] == ["가나 진단비", "다라 진단비"]
    assert riders[0].covers[0].reason.endswith("계약일임\n※ 1년 미만은 50% 감액 지급")
    assert (riders[0].first_page, riders[0].last_page) == (10, 11)


def test_inner_table_cut_at_page_end_is_merged_into_one_line():
    # 지급사유 칸 안의 작은 표는 "· 이름: 내용" 줄로 풀려 온다. 쪽 끝에서 잘린 두 토막을 한 줄로 합친다
    (rider,) = riders_from_tables([
        table(10, [["가나 수술비", "62대질병으로 수술을 받은 경우 \n\n· 62대생활: 다라, 마바, 사아 \n", "가입금액"]]),
        table(11, [["", "\n· 질병: 질환, 자차 \n\n※ 1년 미만은 50% 감액 지급 ", ""]]),
    ])
    assert rider.covers[0].reason == ("62대질병으로 수술을 받은 경우\n· 62대생활질병: 다라, 마바, 사아 질환, 자차\n"
                                      "※ 1년 미만은 50% 감액 지급")


def test_same_name_under_another_label_is_another_rider():
    riders = riders_from_tables([
        table(10, [["가나 사망", "가나로 사망한 경우", "가입금액"]], label="기본계약"),
        table(10, [["가나 사망", "가나로 사망한 경우", "가입금액"], ["다라 진단비", "다라", "가입금액"]]),
    ])
    assert [(r.title, r.label) for r in riders] == [("가나 사망", "기본계약"), ("가나 사망", "선택계약"), ("다라 진단비", "선택계약")]


def test_same_name_without_cover_is_not_merged():
    # 세부보장이 없는 행에 같은 이름이 또 나오면 별개의 행이다(지급금액이 따로 적혀 있다)
    riders = riders_from_tables([table(10, [["가나 진단비", "가나1", "가입금액"], ["가나 진단비", "가나2", "가입금액의 50%"]])])
    assert [(r.title, r.covers[0].amount) for r in riders] == [("가나 진단비", "가입금액"), ("가나 진단비", "가입금액의 50%")]


def test_empty_rows_are_ignored_and_range_may_start_inside_a_rider():
    riders = riders_from_tables([table(11, [
        ["", "", "", ""],
        ["", "가나(간) 진단비", "가나(간)으로 진단 확정된 경우", "가입금액"],
        [None, "가나(폐) 진단비", "가나(폐)로 진단 확정된 경우", "가입금액"],
    ])])
    assert len(riders) == 1 and riders[0].title == "가나(간) 진단비" and len(riders[0].covers) == 2


def test_scope_mark_on_a_name_is_taken_off():
    assert split_only("가나 납입면제대상 *7종에 한함") == ("가나 납입면제대상", "7종에 한함")
    riders = riders_from_tables([table(10, [
        ["가나 납입면제대상 \n*7종에 한함 ", "가나로 납입면제사유가 발생한 경우", "가입금액"],
        ["다라 진단비", "다라로 진단 확정된 경우", "가입금액"],
    ])])
    assert (riders[0].title, riders[0].only) == ("가나 납입면제대상", "7종에 한함")
    assert "적용 범위: 7종에 한함" in riders[0].text
    assert applies_to("7종에 한함", "7종(납입면제형)") and not applies_to("7종에 한함", "8종(일반형)")
    assert not applies_to("7종에 한함", "17종") and applies_to("", "8종(일반형)") and applies_to("여성에 한함", "8종")
    assert [r.title for r in for_variant(riders, "8종(일반형)")] == ["다라 진단비"]
    assert len(for_variant(riders, "7종(납입면제형)")) == 2


def test_for_variant_drops_only_the_covers_of_other_variants():
    rider = Rider("가나 수술비", (Cover("가나 입원 수술비", "입원", "가입금액", 10, "3종에 한함"),
                              Cover("가나 통원 수술비", "통원", "가입금액", 10)), 10, 10)
    (kept,) = for_variant([rider], "1종(납입면제형)")
    assert [c.name for c in kept.covers] == ["가나 통원 수술비"]
    assert for_variant([rider], "3종")[0] is rider


def test_group_riders_accepts_hand_made_lines():
    riders = group_riders([
        Line(10, "가나 진단비", None, "가나로 진단 확정된 경우", "가입금액", cut=True),
        Line(11, "", None, "(최초 1회한 지급)", "", top=True),
    ])
    assert riders[0].covers[0].reason == "가나로 진단 확정된 경우(최초 1회한 지급)"


# ---------------------------------------------------------------------------
# 조각의 글과 Block
# ---------------------------------------------------------------------------

RIDER = Rider("가나 입원·통원 수술비", (
    Cover("가나 통원 수술비", "통원하여 수술을 받은 경우\n※ 60일 미만은 10% 지급", "가입금액", 10),
    Cover("가나 입원 수술비", "입원하여 수술을 받은 경우", "가입금액", 10),
    Cover("가나 특정 수술비", "특정 수술을 받은 경우", "가입금액의 20%", 11),
), 10, 11, "선택계약")


def test_rider_text_lists_every_cover_with_name_reason_and_amount():
    assert RIDER.text == (
        "특별약관: 가나 입원·통원 수술비\n구분: 선택계약\n세부보장 3개\n\n"
        "[1] 보장명: 가나 통원 수술비\n지급사유: 통원하여 수술을 받은 경우\n※ 60일 미만은 10% 지급\n지급금액: 가입금액\n\n"
        "[2] 보장명: 가나 입원 수술비\n지급사유: 입원하여 수술을 받은 경우\n지급금액: 가입금액\n\n"
        "[3] 보장명: 가나 특정 수술비\n지급사유: 특정 수술을 받은 경우\n지급금액: 가입금액의 20%")


def test_blocks_carry_title_and_page_range():
    (block,) = to_blocks([RIDER])
    assert isinstance(block, Block)
    assert (block.title, block.first_page, block.last_page) == ("가나 입원·통원 수술비", 10, 11)
    assert block.text == RIDER.text and block.rider_name == "가나 입원·통원 수술비" and not block.is_main


def test_large_rider_can_be_split_into_blocks_of_a_few_covers():
    first, second = to_blocks([RIDER], max_covers=2)
    assert first.title == second.title == "가나 입원·통원 수술비"
    assert "세부보장 2개" in first.text and "가나 특정 수술비" not in first.text
    assert "세부보장 1개" in second.text and "[1] 보장명: 가나 특정 수술비" in second.text
    assert (first.first_page, first.last_page, second.first_page, second.last_page) == (10, 11, 11, 11)
    assert len(to_blocks([RIDER], max_covers=3)) == 1


# ---------------------------------------------------------------------------
# JSON 쓰기·읽기
# ---------------------------------------------------------------------------

def test_riders_survive_a_json_round_trip(tmp_path):
    only = Rider("다라 납입면제대상", (Cover("다라 납입면제대상", "사유", "가입금액", 12, ""),), 12, 12, "선택계약", "7종에 한함")
    path = tmp_path / "조각.json"
    write_riders(path, [RIDER, only], {"문서": "가나보험 상품요약서", "쪽": [10, 12]})
    assert read_riders(path) == [RIDER, only]
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["형식"] == tables.FORMAT and saved["출처"] == {"문서": "가나보험 상품요약서", "쪽": [10, 12]}
    assert saved["조각"][0]["세부보장"][0] == {
        "보장명": "가나 통원 수술비", "지급사유": "통원하여 수술을 받은 경우\n※ 60일 미만은 10% 지급",
        "지급금액": "가입금액", "쪽": 10, "적용범위": ""}
    assert [b.title for b in to_blocks(read_riders(path))] == ["가나 입원·통원 수술비", "다라 납입면제대상"]


def test_other_json_is_refused():
    with pytest.raises(ValueError):
        riders_from_json({"조각": []})
    with pytest.raises(ValueError):
        riders_from_json([])
    assert riders_from_json(riders_to_json([])) == []


# ---------------------------------------------------------------------------
# 쪽 범위 찾기
# ---------------------------------------------------------------------------

TEXT = """
===== 3쪽 =====
□ 가입자격제한
가. 7종(납입면제형)
가입나이 표
나. 8종(일반형)
가입나이 표

===== 5쪽 =====
● 보험금 지급사유, 지급금액 및 지급제한사항
□ 보험금 지급사유 및 지급금액
◆ 기본계약
보장명 지급사유 지급금액
가나 사망 가나로 사망한 경우 가입금액

===== 6쪽 =====
보장명 지급사유 지급금액
다라 진단비 다라로 진단 확정된 경우 가입금액

===== 7쪽 =====
보장명 지급사유 지급금액
마바 진단비 마바로 진단 확정된 경우 가입금액
□ 보험금 지급제한사항
1) 회사는 다음의 경우 보험금을 지급하지 않습니다.

===== 8쪽 =====
□ 보험료 구성
"""

# 종 구간마다 급부 절이 따로 있는 요약서
TWO = TEXT.replace("===== 3쪽 =====", "===== 3쪽 =====\n1. 1종(가나형)") + """
===== 9쪽 =====
2. 2종(다라형)
□ 가입자격제한

===== 11쪽 =====
□ 보험금 지급사유 및 지급금액
보장명 지급사유 지급금액
사아 진단비 사아로 진단 확정된 경우 가입금액

===== 12쪽 =====
□ 보험금 지급제한사항
"""


def test_benefit_pages_run_from_section_title_to_the_page_of_the_next_title():
    pages = pages_from_text(TEXT)
    assert [(r.first_page, r.last_page) for r in benefit_ranges(pages)] == [(5, 7)]
    assert benefit_pages(pages) == benefit_ranges(pages)[0]
    # 구간 제목을 주면 그 줄이 적힌 쪽부터 찾는다. 급부 절이 구간마다 따로 있지 않아도 뒤에 처음 나오는 절을 고른다
    assert benefit_pages(pages, "나. 8종(일반형)").first_page == 5


def test_section_title_picks_one_of_several_benefit_sections():
    pages = pages_from_text(TWO)
    assert [(r.first_page, r.last_page) for r in benefit_ranges(pages)] == [(5, 7), (11, 12)]
    assert (benefit_pages(pages, "2. 2종(다라형)").first_page, benefit_pages(pages, "1. 1종 (가나형)").first_page) == (11, 5)
    with pytest.raises(ValueError, match="2곳"):
        benefit_pages(pages)
    with pytest.raises(ValueError, match="찾지 못했습니다"):
        benefit_pages(pages, "3. 3종(마바형)")


def test_missing_section_is_an_error():
    with pytest.raises(ValueError):
        benefit_pages({1: "□ 보험료 구성\n보장명 지급사유 지급금액"})
    assert benefit_ranges({1: "□ 보험금 지급사유 및 지급금액\n보장명 지급사유 지급금액", 2: "끝"}) == [tables.PageRange(1, 2)]


# ---------------------------------------------------------------------------
# 선과 글자 읽기 가운데 pdfplumber 없이 돌아가는 부분
# ---------------------------------------------------------------------------

def rect(x0, top, x1, bottom):
    return {"x0": x0, "x1": x1, "top": top, "bottom": bottom}


def char(text, x0, top=100.0, width=9.0):
    return {"text": text, "x0": x0, "x1": x0 + width, "top": top, "bottom": top + 9.0}


def typed(text, x0=10.0, top=100.0):
    """한 줄을 왼쪽부터 찍은 글자들. 빈칸은 반각이다."""
    out = []
    for ch in text:
        width = 4.5 if ch == " " else 9.0
        out.append(char(ch, x0, top, width))
        x0 += width
    return out


def test_only_thin_rectangles_count_as_table_lines():
    # 표의 선은 가는 채움 사각형이고 칸마다 토막 나 있다. 굵은 사각형(칸 바탕색, 글자 줄의 배경)은 선이 아니다
    page = SimpleNamespace(lines=[], rects=[
        rect(40, 100, 160, 100.5), rect(160, 100, 160.5, 100.5), rect(160.5, 100, 400, 100.5),    # 한 줄 위의 가로선 토막
        rect(40, 100.5, 40.5, 300), rect(160, 100.5, 160.5, 300),                                 # 세로선
        rect(41, 120, 159, 133.4),                                                                # 글자 줄의 흰 배경
        rect(40, 60, 400, 82),                                                                    # 머리행 바탕색
        rect(200, 200, 201, 200.4),                                                               # 점처럼 짧은 토막
    ])
    h, v = tables._border_edges(page)
    assert [(round(e["x0"]), round(e["x1"]), round(e["top"], 2)) for e in h] == [(40, 400, 100.25)]
    assert sorted((round(e["x0"], 2), round(e["top"], 1), round(e["bottom"], 1)) for e in v) == [
        (40.25, 100.5, 300.0), (160.25, 100.5, 300.0)]
    assert all(e["orientation"] == "h" for e in h) and all(e["orientation"] == "v" for e in v)


def test_trailing_space_marks_a_line_ended_between_words():
    chars = tables._numbered(typed("가나 다라 ", top=100) + typed("마바", top=113) + typed("사아", top=126))
    lines = tables._text_lines(chars)
    assert [l.text for l in lines] == ["가나 다라 ", "마바", "사아"]
    assert join_name("\n".join(l.text for l in lines)) == "가나 다라 마바사아"
    assert [l.shared for l in lines] == [False, False, False]


def test_hanging_space_and_comma_stay_in_the_cell_of_the_previous_character():
    # 꽉 찬 줄 끝의 빈칸과 쉼표는 칸 오른쪽 경계(x=46) 밖에 찍힌다
    chars = tables._numbered(typed("가나다라,", x0=10) + [char(" ", 60, width=4.5)] + typed("마바", x0=70))
    cell = tables._within(chars, (0, 90, 46, 120))
    assert "".join(c["text"] for c in cell) == "가나다라, "
    assert [l.text for l in tables._text_lines(cell)] == ["가나다라, "]


def test_text_printed_over_another_line_is_kept_apart():
    # 칸 높이에 가려진 글자가 아랫줄과 같은 자리에 찍혀 있다. 적힌 차례로 갈라 읽는다
    chars = tables._numbered(typed("가나다라", x0=30) + typed("마바 사아자차", x0=10))
    lines = tables._text_lines(chars)
    assert [l.text for l in lines] == ["가나다라", "마바 사아자차"]
    assert all(l.shared for l in lines) and lines[0].last < lines[1].first
