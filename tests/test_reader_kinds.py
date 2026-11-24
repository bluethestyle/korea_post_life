"""한 급부 표 안에 종별 값이 함께 있는 생명보험사 요약서(삼성생명)를 두 판독으로 읽고 적재하는 길.

읽을 종 고르기(reader_rows.for_kind), 묶음 나누기의 --kind(scripts/split_pieces.py), 적재의 읽을종(scripts/load_reader_product.py),
고르는 플랜의 특약 행(blocks.py), 이름 검사와 금액 검사의 생명보험사 꼴. 시험 자료는 삼성생명 요약서의 꼴만 본떠 지어낸 것이다.
특약과 담보 이름, 문구, 금액은 지어냈다.
"""
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

from postlife import ids
from postlife.extract import blocks as B
from postlife.extract import reader_rows as RR
from postlife.extract import tables as T
from postlife.extract.blocks import Row, Table, Text
from postlife.sheets_io import MemoryBackend, SheetStore
from postlife.snapshot import KST

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import load_reader_product as L  # noqa: E402

_SPLIT = importlib.util.spec_from_file_location("split_pieces", ROOT / "scripts" / "split_pieces.py")
split_pieces = importlib.util.module_from_spec(_SPLIT)
_SPLIT.loader.exec_module(split_pieces)

NOW = datetime(2026, 11, 23, 18, 0, tzinfo=KST)


def cover(name, reason, amount, only="", page=10):
    return {"보장명": name, "지급사유": reason, "지급금액": amount, "쪽": page, "적용범위": only}


def piece(title, covers, only="", label="선택특약", page=10, main=False):
    return {"특별약관": title, "구분": label, "적용범위": only, "첫쪽": page, "끝쪽": page, "주계약": main,
            "세부보장": covers}


PIECES = {"형식": RR.PIECES_FORMAT, "출처": {"문서": "test_Y1_상품요약서", "꼴": "samsunglife"}, "주석": [
    {"쪽": 10, "형": "", "특약머리": "가나진단특약C", "글": "[기준 : 가나 가입금액 800만원]"},
], "조각": [
    piece("주계약", [cover("가나사망보험금", "사망시", "가입금액 100%")], label="기본계약", main=True),
    piece("가나진단특약C", [                                                                  # R002
        cover("가나 진단보험금", "「가나병」 진단시(최초1회한)",
              "1년이내: [1종,2종] 800만원 [3종] 400만원\n1년초과: 800만원"),
        cover("다라 입원보험금", "입원하였을 경우", "2만원", only="1종,2종"),
        cover("다라 입원보험금", "4일이상 입원하였을 경우", "2만원", only="3종"),
    ], only="1,2,3종"),
    piece("마바치료특약U", [                                                                  # R003
        cover("마바 수술보험금", "[1/3종(가형)] : 마바병으로 수술시[2/4종(나형)] : 「마바보장개시일」"
                               " 뒤 마바병으로 수술시\n* 연간 1회한", "1년이내: 50만원\n1년초과: 100만원"),
        cover("마바 복합보험금", "[1/3종(가형)] : 마바 치료시", "100만원"),
        cover("마바 복합보험금", "[2/4종(나형)] : 「마바보장개시일」 뒤 마바 치료시", "100만원"),
    ]),
    piece("사아간병특약", [cover("사아 간병보험금", "사아 상태가 되었을 때", "월 50만원")], only="1종,2종"),   # R004
]}


# ---------------------------------------------------------------------------
# 읽을 종 고르기
# ---------------------------------------------------------------------------

def test_scope_kinds_reads_variant_marks():
    assert RR.scope_kinds("1,2,3종") == {1, 2, 3}
    assert RR.scope_kinds("1종,2종") == {1, 2}
    assert RR.scope_kinds("1/3종(가형)") == {1, 3}
    assert RR.scope_kinds("1~3종") == {1, 2, 3}
    assert RR.scope_kinds("") == frozenset()
    assert RR.kind_number("2종") == 2
    with pytest.raises(ValueError):
        RR.kind_number("2종(나형)")


def test_kind_text_keeps_only_the_read_variant_segments():
    amount = "1년이내: [1종,2종] 800만원 [3종] 400만원\n1년초과: 800만원"
    assert RR.kind_text(amount, 2) == "1년이내: 800만원\n1년초과: 800만원"
    assert RR.kind_text(amount, 3) == "1년이내: 400만원\n1년초과: 800만원"
    reason = "[1/3종(가형)] : 가나 수술시[2/4종(나형)] : 「가나보장개시일」 뒤 수술시\n* 연간 1회한"
    assert RR.kind_text(reason, 3) == "가나 수술시\n* 연간 1회한"
    # 문장 속의 종 이야기와 이름 토막은 종 표시가 아니다
    assert RR.kind_text("가입금액 전액 [단, 3종(가형)은 절반]", 2) == "가입금액 전액 [단, 3종(가형)은 절반]"
    assert RR.kind_text("[가나 수술(1-3종수술)]", 2) == "[가나 수술(1-3종수술)]"


def test_for_kind_drops_other_variant_pieces_and_lines_and_keeps_numbers():
    views = RR.load_pieces(PIECES)
    kept, lines, whole = RR.for_kind(views, "3종")
    assert whole == [4]                                       # 1종, 2종만 파는 특약
    assert lines == ["R002-2", "R003-3", "R004-1"]
    numbers = [c.number for p in kept for c in p.covers]
    assert numbers == ["R001-1", "R002-1", "R002-3", "R003-1", "R003-2"]
    covers = RR.covers_by_number(kept)
    assert covers["R002-1"][1].amount == "1년이내: 400만원\n1년초과: 800만원"
    assert "마바보장개시일" not in covers["R003-1"][1].reason
    kept2, lines2, whole2 = RR.for_kind(views, "2종")
    assert (lines2, whole2) == (["R002-3", "R003-2"], [])
    # 조각 지문은 원래 조각으로 만든다. 적용범위가 없는 조각의 지문은 이 칸이 생기기 전과 같다
    p, c = RR.covers_by_number(views)["R003-1"]
    names = ()
    old = ids.short_hash(*(RR._squash(x) for x in (p.title, "/".join(names), p.label, p.segment, c.name, c.reason,
                                                   c.amount, str(c.page), c.only, "\n".join(p.notes))),
                         length=RR.FINGERPRINT_LENGTH)
    assert RR.cover_fingerprint(p, c) == old
    p2, c2 = RR.covers_by_number(views)["R002-1"]
    assert RR.cover_fingerprint(p2, c2) != RR.cover_fingerprint(RR.PieceView(**{**p2.__dict__, "only": ""}), c2)


def test_same_subcolumns_is_not_a_cut_hint_but_merged_periods_inside_are():
    assert RR.same_subcolumns("1년이내: 800만원\n1년초과: 800만원")
    assert RR.same_subcolumns("1년이내, 1년초과: 10만원")
    assert not RR.same_subcolumns("1년이내: 400만원\n1년초과: 800만원")
    assert not RR.same_subcolumns("1년이내, 1년초과: 90일이내: 10만원 1년초과: 100만원")
    assert not RR.same_subcolumns("1,000만원")
    view = RR.CoverView("R001-1", "가나 진단보험금", "가나병 진단시", "1년이내: 800만원\n1년초과: 800만원", 10)
    value = {**RR.DEFAULTS, "꼴": RR.AMOUNT, "기준가입금액만원": 800, "지급액만원": 800, "번호": "R001-1", "쪽": 10}
    _, marks = RR.machine_checks(view, value)
    assert not any(m.startswith(RR.MISSED) for m in marks)
    view2 = RR.CoverView("R001-1", "가나 진단보험금", "가나병 진단시", "1년이내: 400만원\n1년초과: 800만원", 10)
    _, marks2 = RR.machine_checks(view2, value)
    assert any(m.startswith(RR.MISSED) for m in marks2)


def test_money_lists_and_bare_man_are_found():
    note = ["[기준 : 가나 가입금액 400/200/1,200만원]"]
    assert all(RR._money_in(v, note) for v in (400, 200, 1200))
    assert not RR._money_in(25, note)
    assert RR._money_in(2000, ["(가나플랜 가입금액 2,000万)"])
    assert RR._money_in(0.5, ["1년이내: 0.5만"]) and RR._money_in(1, ["1년초과: 1만"])
    assert not RR._money_in(1, ["1만5천원"])


# ---------------------------------------------------------------------------
# 이름 검사
# ---------------------------------------------------------------------------

def test_sub_name_in_brackets_repeating_a_tag_is_not_glued():
    reason = "「다라병」 진단 뒤 \"가나(다라) 사아 치료\"를 받은 때"
    ok = RR.CoverView("R001-1", "가나(다라)사아치료비(마바병원)보험금[가나(다라) 사아 치료(주요)]", reason, "", 1)
    assert RR.name_problem(ok) == ""
    glued = RR.CoverView("R001-2", "가암(체증형)나암(체증형)", "암구분별로 지급", "", 1)
    assert RR.name_problem(glued).startswith(RR.HOLD)
    glued2 = RR.CoverView("R001-3", "가암(체증형)[x]나암(체증형)", "암구분별로 지급", "", 1)
    assert RR.name_problem(glued2).startswith(RR.HOLD)


# ---------------------------------------------------------------------------
# 묶음 나누기 --kind
# ---------------------------------------------------------------------------

def test_split_with_kind_drops_lines_keeps_numbers_and_names_the_kind():
    dropped = split_pieces.Dropped()
    [bundle] = split_pieces.split(PIECES, "Y1", kind="3종", dropped=dropped)
    assert bundle["읽을종"] == "3종"
    assert [p["조각번호"] for p in bundle["조각"]] == ["R001", "R002", "R003"]
    assert [c["번호"] for p in bundle["조각"] for c in p["세부보장"]] == ["R001-1", "R002-1", "R002-3", "R003-1", "R003-2"]
    assert bundle["세부보장수"] == 5
    assert bundle["조각"][1]["적용범위"] == "1,2,3종"
    # 다른 종의 줄이 빠지면 이름이 같은 줄이 아니게 된다
    assert not any(c.get("이름같은줄") for p in bundle["조각"] for c in p["세부보장"])
    assert dropped.pieces == ["R004"] and dropped.covers == ["R002-2", "R003-3", "R004-1"]
    # 묶음으로 읽어도 같은 줄과 같은 글자다(견줌이 쓰는 조각)
    views = RR.load_pieces(bundle)
    assert [c.number for p in views for c in p.covers] == ["R001-1", "R002-1", "R002-3", "R003-1", "R003-2"]
    [plain] = split_pieces.split(PIECES, "Y1")
    assert "읽을종" not in plain and plain["세부보장수"] == 8
    assert "적용범위" not in plain["조각"][1]


# ---------------------------------------------------------------------------
# 고르는 플랜
# ---------------------------------------------------------------------------

def test_chosen_plans_become_their_own_riders_and_the_main_row_stays_one():
    items = [Text(1, "2. 보험금 지급사유"), Text(1, "가. 주계약"), Text(1, "(기준 : 가나 가입금액)"),
             Table(1, (Row(1, "가나사망보험금", "사망시", (("", "가입금액 100%"),)),), mode="급부"),
             Text(2, "나. 플러스보장플랜"), Text(2, "① 다라사망보장플랜"), Text(2, "(다라플랜 가입금액 2,000万)"),
             Table(2, (Row(2, "다라사망보험금", "사망시", (("", "2,000만원"),)),), mode="급부"),
             Text(3, "② 마바치아보장플랜"),
             Table(3, (Row(3, "마바치료보험금", "치료시", (("", "25만원"),)),), mode="급부")]
    result = B.pieces(items)
    assert [(r.title, r.label, r.main) for r in result.riders] == [
        ("주계약", "기본계약", True), ("다라사망보장플랜", B.PLAN_LABEL, False), ("마바치아보장플랜", B.PLAN_LABEL, False)]
    data = T.riders_to_json(result.riders, {"문서": "가나_요약서"}, result.notes)
    built = RR.build_rows("V1", RR.load_pieces(data), {})
    assert [(r["원시특약명"], r["담보구분"]) for r in built.riders] == [
        ("주계약", "주계약"), ("다라사망보장플랜", "선택특약"), ("마바치아보장플랜", "선택특약")]
    assert built.riders[0]["특약ID"] == ids.rider_id("V1", "주계약")


# ---------------------------------------------------------------------------
# 적재
# ---------------------------------------------------------------------------

ORG = "TESTLIFE"
PRECISE, GATE = "3종 2형(가형 3.5.5)", "4종(나형)"
VID = ids.variant_id(ORG, "Y1", PRECISE)


def targets():
    variant = {"심사유형": "간편심사", "간편고지약칭": "3.5.5"}
    return {"기관코드": ORG, "공시목록URL": "https://example.invalid/list", "상품": [
        {"모상품ID": "TESTLIFE_GANA", "개정연월": "2611", "비교역할구분": "정밀비교", "갱신유형": "갱신", "갱신주기년": 20,
         "환급유형": "표준형", "납입면제적용": True, "갱신형특약주기년": 20,
         "종형": [{"공시상품코드": "Y1", "종형명": PRECISE, **variant, "읽을종": "3종"},
                  {"공시상품코드": "Y1", "종형명": GATE, "심사유형": "일반심사", "간편고지약칭": "일반",
                   "비교역할구분": "관문전용"}]}]}


INDEX = [{"기관": ORG, "상품코드": "Y1", "상품명": "가나 건강보험(Y1)", "판매시작일": "2026-11-02", "판매종료일": None,
          "문서": kind, "쪽수": 80, "해시": f"h-{kind}", "저장이름": f"test_Y1_{kind}"} for kind in ("상품요약서", "사업방법서")]


def test_load_uses_the_read_variant_only_and_counts_lines_left_out(tmp_path, monkeypatch):
    folder = tmp_path / "out"
    folder.mkdir()
    for e in INDEX:
        (folder / f"{e['저장이름']}.pdf").write_bytes(b"%PDF-1.4 test")
    monkeypatch.setattr(L, "read_pieces", lambda pdf, layout: (RR.load_pieces(PIECES), {}))
    raw = RR.covers_by_number(RR.load_pieces(PIECES))
    value = RR.stored_value({**RR.DEFAULTS, "쪽": 10, "꼴": RR.NO_ROW, "행없음사유": "항목별금액표"})
    lines = []
    for n in ("R001-1", "R002-1", "R002-3", "R003-1", "R003-2"):
        p, c = raw[n]
        lines.append({"번호": n, "쪽": 10, "특약명": p.title, "급부명": c.name, "조각지문": RR.cover_fingerprint(p, c),
                      "sonnet": value, "opus": value, "판정": "확정", "판정값": None})
    path = tmp_path / "values.jsonl"
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines), encoding="utf-8")
    report = L.load(SheetStore(MemoryBackend()), targets(), INDEX, folder, {"Y1": path}, NOW, dry_run=True,
                    layout=L.LAYOUTS["samsunglife"])
    [group] = report.groups
    assert group.out_of_kind == ["R002-2", "R003-3", "R004-1"]
    assert group.used == ["R001-1", "R002-1", "R002-3", "R003-1", "R003-2"]
    assert not group.reasons                                   # 값 파일에 없는 줄이나 지문이 다른 줄이 없다
    assert {r["종형ID"] for r in report.rows["sys_특약"]} == {VID}
    main = [r for r in report.rows["sys_특약"] if r["담보구분"] == "주계약"]
    assert [(r["원시특약명"], r["갱신여부"], r["갱신주기년"]) for r in main] == [("주계약", True, 20)]
    assert len(report.rows["sys_급부"]) == 5
    assert "읽을 종(3종)이 아니어서 뺀 세부보장: 3줄" in L.markdown(report)
    assert L.result_of(report)["읽을 종이 아니어서 뺀 줄"] == {"Y1": 3}
