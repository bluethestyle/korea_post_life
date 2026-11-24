"""두 판독이 판정을 마친 주계약 가입조건을 시트에 쓰는 스크립트(scripts/load_reader_conditions.py).

사업방법서 쪽 글자, 요약서 조각, 값 파일, 대상 설정은 메리츠화재 문서의 꼴만 본떠 지어낸 것이다. 계약 이름도 지어냈다.
PDF 읽기(쪽 글자와 표 조각)는 지어낸 자료로 바꿔 끼운다.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import load_reader_conditions as LC  # noqa: E402
import load_reader_product as L  # noqa: E402
from postlife import ids  # noqa: E402
from postlife.extract import reader_conditions as RC  # noqa: E402
from postlife.extract import reader_rows as RR  # noqa: E402
from postlife.extract import variants  # noqa: E402
from postlife.schema import TABS  # noqa: E402
from postlife.sheets_io import MemoryBackend, SheetStore, rows_to_values  # noqa: E402
from postlife.snapshot import KST  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ORG = "TESTORG"
PRECISE, GATE, OTHER = "가형 1종", "가형 2종", "나형 1종"
VID = ids.variant_id(ORG, "Z1", PRECISE)
GATE_VID = ids.variant_id(ORG, "Z1", GATE)
OTHER_VID = ids.variant_id(ORG, "Z2", OTHER)
MAIN_NAME = "가나상해사망"                       # 요약서 기본계약 표의 이름(지어냄)
MAIN_ID = ids.rider_id(VID, MAIN_NAME)
GATE_MAIN_ID = ids.rider_id(GATE_VID, "주계약")
NOW = datetime(2026, 11, 23, 18, 0, tzinfo=KST)

PAGES = {
    2: "2. 보험종목의 구성\n가형 1종 가형 2종\n",
    3: "4. 보험기간, 보험료 납입기간, 보험가입나이\n<가형> 3종 기준\n"
       "가 ·기본계약(가나상해사망보장) 80세만기 20년납 15세∼60세 월납\n90세만기 20년납 15세∼65세\n",
}


def cover(name, reason, amount="가입금액", page=10):
    return {"보장명": name, "지급사유": reason, "지급금액": amount, "쪽": page, "적용범위": ""}


def piece(title, covers, segment, label="선택계약"):
    return {"특별약관": title, "구분": label, "적용범위": "", "첫쪽": 10, "끝쪽": 10, "형": segment, "세부보장": covers}


PIECES = {"형식": RR.PIECES_FORMAT, "출처": {"문서": "test_Z1_상품요약서"}, "조각": [
    piece(MAIN_NAME, [cover(MAIN_NAME, "상해로 사망한 경우")], "가형", label="기본계약"),
    piece("다라 수술비", [cover("다라 수술비", "다라병으로 수술을 받은 경우")], "가형"),
]}


def table(words=("가형",), top=65):
    return {"표": "가형", "근거쪽": 3, "근거낱말": list(words),
            "줄": [{"쪽": 3, "성별": "구분없음", "보험기간": "80세만기", "납입기간": "20년납", "최저나이": 15, "최고나이": 60,
                    "최고나이식": ""},
                   {"쪽": 3, "성별": "구분없음", "보험기간": "90세만기", "납입기간": "20년납", "최저나이": 15, "최고나이": top,
                    "최고나이식": ""}],
            "한도없음": True, "한도": [], "모름": []}


def line(vid, name, value, verdict="확정", marks=()):
    checks = {"문제": [], "표시": list(marks)}
    return {"일감": "Z1_MAIN", "종형ID": vid, "공시상품코드": "Z1", "종형명": name, "사업방법서해시": "m1", "쪽범위": [3, 3],
            "sonnet": value, "opus": value, "일치": {"줄": "같음", "한도": "같음", "근거쪽": "같음"}, "다른줄": [],
            "기계검사": {"sonnet": checks, "opus": checks}, "자동판정": "확정" if verdict == "확정" and not marks else "판정필요",
            "판정": verdict, "판정값": None}


def targets():
    variant = {"심사유형": "간편심사", "간편고지약칭": "3.1.5", "고지최근소견개월": 3, "고지입원수술년수": 1, "고지중대질병년수": 5,
               "고지수술포함여부": True, "고지중대질병수": 2, "고지중대질병목록": "가나병, 다라병", "고지소견범위": "서면"}
    return {"기관코드": ORG, "공시목록URL": "https://example.invalid/list", "상품": [
        {"모상품ID": "GANA", "개정연월": "2611", "비교역할구분": "정밀비교", "갱신유형": "비갱신", "갱신주기년": None,
         "환급유형": "표준형", "납입면제적용": False, "갱신형특약주기년": 20, "갱신형특약제외": [],
         "종형": [{"공시상품코드": "Z1", "종형명": PRECISE, **variant},
                  {"공시상품코드": "Z1", "종형명": GATE, **variant, "비교역할구분": "관문전용"}]}]}


def entry(code, kind, digest):
    return {"기관": ORG, "상품코드": code, "상품명": f"무배당 가나 건강보험({code})", "판매시작일": "2026-10-31",
            "판매종료일": None, "문서": kind, "쪽수": 300, "해시": digest, "저장이름": f"test_{code}_{kind}"}


INDEX = [entry("Z1", "상품요약서", "h1"), entry("Z1", "사업방법서", "m1")]


@pytest.fixture
def docs(tmp_path, monkeypatch):
    folder = tmp_path / "out"
    folder.mkdir()
    for e in INDEX:
        (folder / f"{e['저장이름']}.pdf").write_bytes(b"%PDF-1.4 test")
    (folder / "index.json").write_text(json.dumps(INDEX, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(L, "read_pieces", lambda pdf, layout: (RR.load_pieces(PIECES), {}))
    monkeypatch.setattr(LC, "read_pages", lambda docs, stem, wanted: {n: PAGES[n] for n in wanted if n in PAGES})
    return folder


def values_file(tmp_path, lines):
    path = tmp_path / "values.jsonl"
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines), encoding="utf-8")
    return path


def both(**kw):
    return [line(VID, PRECISE, table(**kw)), line(GATE_VID, GATE, table(**kw))]


def store_with(rows=None):
    data = {name: [TABS[name].header] + rows_to_values(TABS[name], r) for name, r in (rows or {}).items()}
    return SheetStore(MemoryBackend(data))


def read(store):
    return store.read(["sys_상품종형", "sys_특약", "sys_가입조건", "sys_작업로그"])


def test_empty_sheet_gets_conditions_and_the_main_rows_the_screen_needs(docs, tmp_path):
    store = store_with()
    report = LC.load(store, targets(), INDEX, docs, values_file(tmp_path, both()), NOW)
    assert report.written and not report.errors and not report.clashes and not report.skipped
    sheet = read(store)
    conds = sheet["sys_가입조건"]
    assert len(conds) == 4 and {r["종형ID"] for r in conds} == {VID, GATE_VID}
    assert all(r["특약ID"] is None for r in conds)          # 주계약 행
    assert {(r["보험기간구분"], r["최고가입나이"]) for r in conds if r["종형ID"] == GATE_VID} == {("80세만기", 60), ("90세만기", 65)}
    mains = {r["종형ID"]: r for r in sheet["sys_특약"]}
    # 관문전용은 job._run_gate와 같은 행, 정밀비교는 급부 적재(요약서 기본계약 표)와 같은 특약ID
    assert mains[GATE_VID] == variants.main_row(next(v for v in variants.build(targets(), INDEX)[0] if v.id == GATE_VID))
    assert mains[GATE_VID]["특약ID"] == GATE_MAIN_ID
    assert mains[VID]["특약ID"] == MAIN_ID and mains[VID]["담보구분"] == "주계약"
    assert {r["종형ID"] for r in sheet["sys_상품종형"]} == {VID, GATE_VID}
    logs = sheet["sys_작업로그"]
    assert len(logs) == 4 and {(x["작업단계"], x["결과"], x["호출모델"], x["판정확률"]) for x in logs} == {("판정", "통과", "교차 확인", None)}
    assert {x["대상행ID"] for x in logs} == {r["조건행ID"] for r in conds}


def test_precise_main_id_is_the_one_the_benefit_loader_writes(docs, tmp_path):
    variant = next(v for v in variants.build(targets(), INDEX)[0] if v.id == VID)
    pieces = RR.load_pieces(PIECES)
    built = RR.build_rows(VID, pieces, {}, None, {})
    expected = next(r for r in built.riders if r["담보구분"] == "주계약")
    report = LC.load(store_with(), targets(), INDEX, docs, values_file(tmp_path, both()), NOW, dry_run=True)
    assert not report.written
    assert next(r for r in report.new_mains if r["종형ID"] == variant.id) == expected
    assert report.counts[VID]["사업방법서 기본계약"] == "가나상해사망보장"


def test_existing_riders_stay_and_only_main_condition_rows_are_replaced(docs, tmp_path):
    found = {v.id: v for v in variants.build(targets(), INDEX)[0]}
    riders = [{"특약ID": MAIN_ID, "종형ID": VID, "특약계보키": ids.rider_lineage_key(MAIN_NAME), "담보구분": "주계약",
               "원시특약명": MAIN_NAME, "갱신여부": False, "갱신주기년": None, "최소가입금액만원": 100.0,
               "최대가입금액만원": 1000.0, "합산한도기준키": None},
              {"특약ID": ids.rider_id(VID, "다라 수술비"), "종형ID": VID, "특약계보키": ids.rider_lineage_key("다라 수술비"),
               "담보구분": "선택특약", "원시특약명": "다라 수술비", "갱신여부": False, "갱신주기년": None,
               "최소가입금액만원": None, "최대가입금액만원": None, "합산한도기준키": None}]
    old_main = {"조건행ID": ids.condition_id(VID, "80세만기", "20년납", "", "", "15-55"), "종형ID": VID, "특약ID": None,
                "보험기간구분": "80세만기", "납입기간구분": "20년납", "성별": None, "최저가입나이": 15, "최고가입나이": 55,
                "구간최대가입금액만원": None}
    rider_cond = {**old_main, "조건행ID": ids.condition_id(VID, "80세만기", "20년납", riders[1]["특약ID"], "", "15-50"),
                  "특약ID": riders[1]["특약ID"], "최고가입나이": 50}
    other = {**old_main, "조건행ID": ids.condition_id(OTHER_VID, "80세만기", "20년납", "", "", "15-55"), "종형ID": OTHER_VID}
    store = store_with({"sys_상품종형": [found[VID].row, found[GATE_VID].row], "sys_특약": riders,
                        "sys_가입조건": [old_main, rider_cond, other]})
    report = LC.load(store, targets(), INDEX, docs, values_file(tmp_path, both()), NOW)
    assert report.written and report.dropped == 1 and len(report.kept) == 1
    assert [r["특약ID"] for r in report.new_mains] == [GATE_MAIN_ID] and not report.new_variants
    sheet = read(store)
    assert sorted(r["특약ID"] for r in sheet["sys_특약"] if r["종형ID"] == VID) == sorted(r["특약ID"] for r in riders)
    assert next(r for r in sheet["sys_특약"] if r["특약ID"] == MAIN_ID)["최대가입금액만원"] == 1000.0
    ids_now = {r["조건행ID"] for r in sheet["sys_가입조건"]}
    assert old_main["조건행ID"] not in ids_now
    assert {rider_cond["조건행ID"], other["조건행ID"]} <= ids_now
    assert len(sheet["sys_가입조건"]) == 4 + 2


def test_a_value_the_page_does_not_back_is_not_written(docs, tmp_path):
    lines = [line(VID, PRECISE, table()), line(GATE_VID, GATE, table(top=66))]      # 66세는 그 쪽에 없다
    store = store_with()
    report = LC.load(store, targets(), INDEX, docs, values_file(tmp_path, lines), NOW)
    assert report.written and report.done == {VID}
    assert report.skipped[GATE_VID].startswith(LC.CHECK) and "66세" in report.skipped[GATE_VID]
    sheet = read(store)
    assert {r["종형ID"] for r in sheet["sys_가입조건"]} == {VID}
    assert {r["종형ID"] for r in sheet["sys_특약"]} == {VID}       # 쓰지 않은 종형의 주계약 행도 쓰지 않는다
    assert any(x["작업단계"] == "코드대조" and x["결과"] == "반려" and x["대상행ID"] == GATE_VID for x in sheet["sys_작업로그"])


def test_a_new_mark_stops_the_variant_but_a_mark_seen_at_judging_does_not(docs, tmp_path):
    words = ("가형", "3종")          # 3종은 종형명에 없어 title_marks가 표시한다
    mark = RC.title_marks(table(words=words), PRECISE)
    assert mark
    lines = [line(VID, PRECISE, table(words=words), verdict="sonnet", marks=mark),
             line(GATE_VID, GATE, table(words=words))]
    report = LC.load(store_with(), targets(), INDEX, docs, values_file(tmp_path, lines), NOW, dry_run=True)
    assert VID in report.done
    assert report.skipped[GATE_VID].startswith(LC.NEW_MARK)


def test_main_row_with_another_name_is_not_used(docs, tmp_path):
    found = {v.id: v for v in variants.build(targets(), INDEX)[0]}
    rider = {"특약ID": ids.rider_id(VID, "마바상해후유장해"), "종형ID": VID, "특약계보키": ids.rider_lineage_key("마바상해후유장해"),
             "담보구분": "주계약", "원시특약명": "마바상해후유장해", "갱신여부": False, "갱신주기년": None,
             "최소가입금액만원": None, "최대가입금액만원": None, "합산한도기준키": None}
    store = store_with({"sys_상품종형": [found[VID].row], "sys_특약": [rider]})
    report = LC.load(store, targets(), INDEX, docs, values_file(tmp_path, both()), NOW, dry_run=True)
    assert report.skipped[VID].startswith(LC.NAME)
    assert report.done == {GATE_VID}


def test_waiting_or_missing_values_write_nothing(docs, tmp_path):
    lines = [line(VID, PRECISE, table(), verdict="검토 대기")]
    store = store_with()
    report = LC.load(store, targets(), INDEX, docs, values_file(tmp_path, lines), NOW)
    assert not report.written and not report.done
    assert report.skipped[VID].startswith(LC.WAITING) and report.skipped[GATE_VID] == LC.NO_VALUE
    assert read(store)["sys_가입조건"] == []


def test_dry_run_runs_to_the_end_without_sheet_credentials(docs, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("SPREADSHEET_ID", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    tpath = tmp_path / "targets.json"
    tpath.write_text(json.dumps(targets(), ensure_ascii=False), encoding="utf-8")
    result, rows = tmp_path / "r.json", tmp_path / "rows.json"
    code = LC.main(["--docs", str(docs), "--targets", str(tpath), "--values", str(values_file(tmp_path, both())),
                    "--dry-run", "--result", str(result), "--rows", str(rows)])
    assert code == 0
    out = json.loads(result.read_text(encoding="utf-8"))
    assert out["가입조건 행"] == 4 and out["새 주계약 행"] == [MAIN_ID, GATE_MAIN_ID] and not out["시트에 씀"]
    made = json.loads(rows.read_text(encoding="utf-8"))
    assert len(made["행"]["sys_가입조건"]) == 4 and len(made["작업로그"]) == 4
    assert "상해로 사망한 경우" not in result.read_text(encoding="utf-8") + rows.read_text(encoding="utf-8")
    assert "시트에 쓰지 않았습니다" in capsys.readouterr().out


def test_seed_rows_stand_in_for_the_benefit_load(docs, tmp_path):
    found = {v.id: v for v in variants.build(targets(), INDEX)[0]}
    main = RR.build_rows(VID, RR.load_pieces(PIECES), {}, None, {}).riders[0]
    seed = tmp_path / "benefit_rows.json"
    seed.write_text(json.dumps({"행": {"sys_상품종형": [found[VID].row, found[GATE_VID].row], "sys_특약": [main],
                                      "sys_급부": []}}, ensure_ascii=False), encoding="utf-8")
    store = store_with()
    LC.seed(store, seed)
    report = LC.load(store, targets(), INDEX, docs, values_file(tmp_path, both()), NOW, dry_run=True)
    assert [r["특약ID"] for r in report.new_mains] == [GATE_MAIN_ID] and not report.new_variants
    assert report.counts[VID]["주계약 행"] == "시트에 있음"


def test_method_main_name_reads_the_balanced_parentheses():
    pages = {3: "가 ·기본계약(가나(다라)보장) 80세만기 20년납 0세∼70세 월납", 4: "·기본계약(닫히지 않음"}
    assert LC.method_main_name(pages, 3, 3) == "가나(다라)보장"
    assert LC.method_main_name(pages, 4, 4) is None
    assert LC.method_main_name({5: "기본계약 표 없음"}, 5, 5) is None
    assert LC.names_match("주계약", None)
    assert LC.names_match("가나(다라)", "가나(다라)보장") and not LC.names_match("마바", "가나(다라)보장")


def test_method_main_name_reads_the_name_after_the_main_label_at_line_start():
    """현대해상 간편심사 상품 형식: 표의 구분 열에 "기본계약"과 담보 이름이 한 줄로 나온다(문구는 지어냄)."""
    pages = {3: "구 분 보험기간 가입나이\n90세/95세/ 10/15/20/\n기본계약 가나상해(간편가입) 20/25/30년납 (보험기간-납입\n"
                "100세만기 25/30년납\n기간)세\n나) 의무 특약\n"}
    assert LC.method_main_name(pages, 3, 3) == "가나상해(간편가입)"
    assert LC.method_main_name({3: "기본계약 가나상해(간편가입 20년납\n"}, 3, 3) is None      # 괄호가 닫히지 않음
    # 메리츠화재 형식이 먼저다: 그 줄이 있으면 다른 형식은 보지 않는다
    both_kinds = {3: "가 ·기본계약(마바보장) 80세만기\n기본계약 가나상해 20년납\n"}
    assert LC.method_main_name(both_kinds, 3, 3) == "마바보장"


HEADED = ("5. 가입나이 표\n가. 가형\n1) 가형 가입나이\n가) 기본계약\n"
          "보험료\n구 분 보험기간 가입나이\n납입기간\n80세만기 20년납 만15세 ~ (80-납입기간)세\n15년납 만15세 ~\n"
          "가나사망 90세만기\n20년납 MIN(83-납입기간,65)세\n가나후유장해\n25년납 만15세 ~\n100세만기 30년납 MIN(88-납입기간,65)세\n"
          "나) 의무 특약\n구 분 보험기간 가입나이\n다라면제 전기납 만15 ~ 70세\n")


def test_method_main_name_reads_the_names_in_the_main_table_under_the_heading():
    """현대해상 일반심사 상품 형식: "가) 기본계약" 소제목 아래 표의 구분 열에 담보 이름이 적히고, 표 읽기 글자에서는 이름이
    보험기간, 납입기간, 나이 글자와 섞여 나온다. 그 글자를 지우고 남은 이름을 표에 나온 순서대로 쉼표로 잇는다(문구는 지어냄)."""
    assert LC.method_main_name({2: HEADED}, 2, 2) == "가나사망, 가나후유장해"
    assert LC.main_names("가나사망, 가나후유장해") == ["가나사망", "가나후유장해"]
    # 이름도 기간도 아닌 글자가 남으면(표 밖 문구가 섞임) 읽지 않는다
    assert LC.method_main_name({2: HEADED.replace("가나후유장해\n", "가나후유장해 ※ 가입금액 1천만원\n")}, 2, 2) is None
    # 소제목 아래 표가 그 쪽에서 끝나지 않으면(다음 소제목이 없음) 읽지 않는다
    assert LC.method_main_name({2: HEADED.split("나) 의무 특약")[0]}, 2, 2) is None
    # 이름이 하나도 남지 않으면 None
    assert LC.method_main_name({2: "가) 기본계약\n구 분 보험기간 가입나이\n80세만기 20년납 만15세 ~ 60세\n나) 선택계약\n"}, 2, 2) is None


def test_two_main_covers_sharing_one_age_table_take_the_first_main_row(docs, tmp_path, monkeypatch):
    """기본계약 담보 둘(요약서 기본계약 표의 행 둘)이 사업방법서의 가입나이 표 하나를 함께 쓰면, 요약서 표 순서의 첫 행을 주계약
    행으로 쓴다(화면의 main_rider와 급부 적재 뒤 시트의 첫 주계약 행과 같은 행)."""
    second = "가나후유장해"
    pieces = {**PIECES, "조각": [
        piece("가나사망", [cover("가나사망", "상해로 사망한 경우")], "가형", label="기본계약"),
        piece(second, [cover(second, "상해로 후유장해가 남은 경우")], "가형", label="기본계약"),
        PIECES["조각"][1]]}
    page = ("<가형>\n가) 기본계약\n구 분 보험기간 가입나이\n납입기간\n80세만기 20년납 15세∼60세\n가나사망 90세만기\n"
            "20년납 15세∼65세\n가나후유장해\n나) 의무 특약\n다라면제 전기납 15세∼70세\n")
    monkeypatch.setattr(L, "read_pieces", lambda pdf, layout: (RR.load_pieces(pieces), {}))
    monkeypatch.setattr(LC, "read_pages", lambda docs, stem, wanted: {n: page for n in wanted if n == 3})
    report = LC.load(store_with(), targets(), INDEX, docs, values_file(tmp_path, both()), NOW, dry_run=True)
    assert VID in report.done and not report.skipped
    main = next(r for r in report.new_mains if r["종형ID"] == VID)
    assert main["원시특약명"] == "가나사망" and main["특약ID"] == ids.rider_id(VID, "가나사망")
    assert report.counts[VID]["사업방법서 기본계약"] == "가나사망, 가나후유장해"
    assert report.counts[VID]["가입조건"] == 2


def test_two_main_rows_with_one_name_on_the_method_page_still_stop(docs, tmp_path, monkeypatch):
    """사업방법서 표에 이름이 하나뿐인데 요약서 주계약 행 둘이 그 이름에 걸리면 어느 행인지 정하지 못하므로 쓰지 않는다."""
    pieces = {**PIECES, "조각": [
        piece("가나사망", [cover("가나사망", "상해로 사망한 경우")], "가형", label="기본계약"),
        piece("가나사망(갱신형)", [cover("가나사망(갱신형)", "상해로 사망한 경우")], "가형", label="기본계약")]}
    page = "<가형>\n가 ·기본계약(가나사망) 80세만기 20년납 15세∼60세\n90세만기 20년납 15세∼65세\n"
    monkeypatch.setattr(L, "read_pieces", lambda pdf, layout: (RR.load_pieces(pieces), {}))
    monkeypatch.setattr(LC, "read_pages", lambda docs, stem, wanted: {n: page for n in wanted if n == 3})
    report = LC.load(store_with(), targets(), INDEX, docs, values_file(tmp_path, both()), NOW, dry_run=True)
    assert report.skipped[VID].startswith(LC.NO_MAIN) and "2개" in report.skipped[VID]


def test_read_pages_falls_back_to_the_saved_text(tmp_path):
    (tmp_path / "x.txt").write_text("\n===== 1쪽 =====\n첫 쪽\n\n===== 2쪽 =====\n둘째 쪽", encoding="utf-8")
    assert LC.read_pages(tmp_path, "x", [2, 9]) == {2: "둘째 쪽"}
    assert LC.read_pages(tmp_path, "없음", [1]) == {}


def test_committed_meritz_value_file_covers_every_target_variant():
    """커밋한 값 파일의 종형이 대상 설정의 종형 열다섯과 같고, 판정이 끝난 값으로 행이 만들어진다(문서는 읽지 않는다)."""
    targets_ = json.loads((ROOT / "data/targets/meritz.json").read_text(encoding="utf-8"))
    wanted = {ids.variant_id(targets_["기관코드"], v["공시상품코드"], v["종형명"]): v["종형명"]
              for p in targets_["상품"] for v in p["종형"]}
    lines = LC.value_lines(ROOT / "data/crosscheck/meritz_main_conditions_2reader.jsonl")
    assert {x["종형ID"]: x["종형명"] for x in lines} == wanted and len(lines) == len(wanted)
    finals = {x["종형ID"]: RC.final_value(x, LC.READERS) for x in lines}
    assert all(v and v["줄"] for v in finals.values())
    assert all(not RC.check_line(row) for v in finals.values() for row in v["줄"])
    built = RC.build_rows([{"종형ID": x["종형ID"], "종형명": x["종형명"]} for x in lines], finals)
    assert len(built.done) == len(wanted) and len(built.conditions) == 102
