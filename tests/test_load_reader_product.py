"""두 판독이 판정을 마친 급부 값을 시트에 쓰는 스크립트(scripts/load_reader_product.py).

조각, 값 파일, 대상 설정은 메리츠화재 요약서의 꼴만 본떠 지어낸 것이다. 담보 이름도 지어냈다.
표 읽기(PDF)는 지어낸 조각으로 바꿔 끼운다.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import load_reader_product as L  # noqa: E402
from postlife import ids  # noqa: E402
from postlife.extract import reader_rows as RR  # noqa: E402
from postlife.extract import rerun as R  # noqa: E402
from postlife.schema import TABS  # noqa: E402
from postlife.sheets_io import MemoryBackend, SheetStore, rows_to_values  # noqa: E402
from postlife.snapshot import KST  # noqa: E402

ORG = "TESTORG"
PRECISE, GATE, OTHER = "가형 1종", "가형 2종", "나형 1종"
VID = ids.variant_id(ORG, "Z1", PRECISE)
GATE_VID = ids.variant_id(ORG, "Z1", GATE)
OTHER_VID = ids.variant_id(ORG, "Z2", OTHER)
NOW = datetime(2026, 11, 23, 18, 0, tzinfo=KST)
EARLIER = datetime(2026, 11, 22, 18, 0, tzinfo=KST)
SENTENCE = "가나병 진단이 확정되면 한 번 줌(최초 1회한)"      # 결과 파일에 실리면 안 되는 지급사유 문장
BANNED = "무배당 갱신형 다라 배상책임 특별약관"


def cover(name, reason, amount="가입금액", page=10):
    return {"보장명": name, "지급사유": reason, "지급금액": amount, "쪽": page, "적용범위": ""}


def piece(title, covers, segment, label="선택계약", names=None, page=10):
    out = {"특별약관": title, "구분": label, "적용범위": "", "첫쪽": page, "끝쪽": page, "형": segment, "세부보장": covers}
    if names:
        out["특약명들"] = names
    return out


PIECES = {"형식": RR.PIECES_FORMAT, "출처": {"문서": "test_Z1_상품요약서"}, "조각": [
    piece("가나 진단비", [cover("가나 진단비", SENTENCE)], "가형", label="기본계약"),                          # R001 확정
    piece("다라 수술비/갱신형 다라 수술비", [cover("다라 수술비/갱신형 다라 수술비", "다라병으로 수술을 받은 경우",
                                                  "가입금액의 20%")], "가형", names=["다라 수술비", "갱신형 다라 수술비"]),  # R002 opus
    piece(BANNED, [cover("다라 배상책임", "다라 사고로 배상책임을 진 경우")], "공통"),                         # R003 갱신형특약제외
    piece("마바 입원일당", [cover("마바 입원일당", "마바병으로 입원한 경우", "1일당 가입금액")], "가형"),          # R004 검토 대기
    piece("사아 치료비", [cover("사아 치료비", "사아병 치료 항목별로 지급", "항목별 금액")], "가형"),             # R005 행없음(금액 없는 급부)
    piece("자차 치료비", [cover("가가암(체증형)나나암(체증형)", "암구분별로 지급")], "가형"),                    # R006 보류
    piece("카타 진단비", [cover("카타 진단비", "카타병으로 진단확정시")], "가형"),                              # R007 지문 다름
    piece("파하 진단비", [cover("파하 진단비", "파하병으로 진단확정시")], "나형"),                              # R008 정밀비교 종형 밖
    piece("가나 통원비", [cover("가나 통원비", "가나병으로 통원한 경우(연간 30회한)", "1회당 가입금액의 10%")], "가형"),  # R009 수정
]}


def views():
    return RR.load_pieces(PIECES)


def reading(**values):
    return RR.stored_value({**RR.DEFAULTS, "쪽": 10, "꼴": RR.RATIO, "지급률": 100, **values})


def line(number, verdict, a=None, b=None, fixed=None, fingerprint=None):
    p, c = RR.covers_by_number(views())[number]
    return {"번호": number, "쪽": c.page, "특약명": p.title, "급부명": c.name, "형": p.segment,
            "조각지문": fingerprint or RR.cover_fingerprint(p, c), "sonnet": a, "opus": b if b is not None else a,
            "판정": verdict, "판정값": fixed}


VALUES = [
    line("R001-1", "확정", reading(한도=[{"앞말": "최초", "수": 1, "단위": "회"}])),
    line("R002-1", "opus", reading(지급률=10), reading(지급률=20)),
    line("R003-1", "확정", reading()),
    line("R004-1", "검토 대기", reading(지급단위="1일당"), reading()),
    line("R005-1", "확정", reading(꼴=RR.NO_ROW, 지급률=None, 행없음사유="항목별금액표")),
    line("R006-1", "확정", reading()),
    line("R007-1", "확정", reading(), fingerprint="000000000000"),
    line("R008-1", "확정", reading()),
    line("R009-1", "수정", reading(지급률=20), reading(지급률=30),
         fixed=reading(지급률=10, 지급단위="1회당", 한도=[{"앞말": "연간", "수": 30, "단위": "회"}])),
]


def targets():
    variant = {"심사유형": "간편심사", "간편고지약칭": "3.1.5", "고지최근소견개월": 3, "고지입원수술년수": 1, "고지중대질병년수": 5,
               "고지수술포함여부": True, "고지중대질병수": 2, "고지중대질병목록": "가나병, 다라병", "고지소견범위": "서면"}
    return {"기관코드": ORG, "공시목록URL": "https://example.invalid/list", "상품": [
        {"모상품ID": "GANA", "개정연월": "2611", "비교역할구분": "정밀비교", "갱신유형": "비갱신", "갱신주기년": None,
         "환급유형": "표준형", "납입면제적용": False, "갱신형특약주기년": 20,
         "갱신형특약제외": [{"특약명": BANNED, "근거": "지어낸 근거"}],
         "종형": [{"공시상품코드": "Z1", "종형명": PRECISE, **variant},
                  {"공시상품코드": "Z1", "종형명": GATE, **variant, "비교역할구분": "관문전용"},
                  {"공시상품코드": "Z2", "종형명": OTHER, "심사유형": "일반심사", "간편고지약칭": "일반", "비교역할구분": "관문전용"}]}]}


def entry(code, kind, digest):
    return {"기관": ORG, "상품코드": code, "상품명": f"무배당 가나 건강보험({code})", "판매시작일": "2026-10-31",
            "판매종료일": None, "문서": kind, "쪽수": 300, "해시": digest, "저장이름": f"test_{code}_{kind}"}


INDEX = [entry("Z1", "상품요약서", "h1"), entry("Z1", "사업방법서", "m1"),
         entry("Z2", "상품요약서", "h1"), entry("Z2", "사업방법서", "m1")]


@pytest.fixture
def docs(tmp_path, monkeypatch):
    folder = tmp_path / "out"
    folder.mkdir()
    for e in INDEX:
        (folder / f"{e['저장이름']}.pdf").write_bytes(b"%PDF-1.4 test")
    (folder / "index.json").write_text(json.dumps(INDEX, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(L, "read_pieces", lambda pdf, layout: (views(), {}))
    return folder


@pytest.fixture
def values(tmp_path):
    path = tmp_path / "values.jsonl"
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in VALUES), encoding="utf-8")
    return {"Z1": path}


def store_with(rows=None):
    data = {name: [TABS[name].header] + rows_to_values(TABS[name], r) for name, r in (rows or {}).items()}
    return SheetStore(MemoryBackend(data))


def numbers_of(report):
    return {n for g in report.groups for n in g.written}


def test_rows_are_made_for_precise_variants_and_lines_left_out_are_counted(docs, values):
    store = store_with()
    report = L.load(store, targets(), INDEX, docs, values, NOW)
    assert report.written and not report.errors and not report.clashes
    sheet = store.read(["sys_상품종형", "sys_특약", "sys_급부", "sys_작업로그"])
    assert {r["종형ID"] for r in sheet["sys_상품종형"]} == {VID, GATE_VID, OTHER_VID}
    # 특약과 급부는 정밀비교 종형에만 쓴다. 갱신형특약제외의 특약은 특약 행도 만들지 않는다
    assert {r["종형ID"] for r in sheet["sys_특약"]} == {VID}
    riders = {r["원시특약명"]: r for r in sheet["sys_특약"]}
    assert BANNED not in riders and "파하 진단비" not in riders
    assert riders["갱신형 다라 수술비"]["갱신여부"] is True and riders["갱신형 다라 수술비"]["갱신주기년"] == 20
    assert riders["가나 진단비"]["담보구분"] == "주계약"
    benefits = {r["원시급부명"]: r for r in sheet["sys_급부"]}
    assert set(benefits) == {"가나 진단비", "다라 수술비", "갱신형 다라 수술비", "가나 통원비", "사아 치료비"}
    # 행없음 줄은 금액과 감액이 빈 급부가 되고, 지급기준구분은 판독 사유를 묶은 값이다
    assert benefits["사아 치료비"]["지급기준구분"] == "차등지급"
    assert benefits["사아 치료비"]["기준가입금액만원"] is None and benefits["사아 치료비"]["기준지급금액만원"] is None
    assert benefits["다라 수술비"]["기준지급금액만원"] == 20.0                     # 판정한 판독(opus)의 값
    assert benefits["가나 통원비"]["기준지급금액만원"] == 10.0                     # 수정한 판정값
    assert benefits["가나 통원비"]["지급횟수제한"] == "1회당 / 연간 30회한"        # 원문 구절은 조각에서 잘라 쓴다
    reasons = L.reason_counts(report.groups[0])
    assert reasons == {L.WAITING: 1, RR.HOLD: 1, L.CHANGED: 1, L.EXCLUDED: 1}
    assert numbers_of(report) == {"R001-1", "R002-1", "R005-1", "R009-1"}
    assert report.excluded == {"Z1": [BANNED]}
    assert "Z1 R005-1" in report.no_rows and report.no_rows["Z1 R005-1"]["행없음사유"] == "항목별금액표"
    logs = sheet["sys_작업로그"]
    assert logs and all(r["판정확률"] in (None, "") for r in logs)
    assert not [r for r in logs if r["결과"] == "보류"]


def test_dry_run_writes_nothing(docs, values):
    store = store_with()
    report = L.load(store, targets(), INDEX, docs, values, NOW, dry_run=True)
    assert not report.written and len(report.rows["sys_급부"]) == 5
    assert [c for c in store.backend.calls if c[0] != "get"] == []


def test_existing_rows_keep_limits_gate_riders_and_waiting_marks_are_cleared(docs, values):
    built = L.load(store_with(), targets(), INDEX, docs, values, NOW, dry_run=True)
    first = next(r for r in built.rows["sys_특약"] if r["원시특약명"] == "가나 진단비")
    benefit = next(b for b in built.rows["sys_급부"] if b["특약ID"] == first["특약ID"])
    old_rider = {**first, "최소가입금액만원": 100.0, "최대가입금액만원": 3000.0}
    gate_main = {**first, "특약ID": ids.rider_id(GATE_VID, "주계약"), "종형ID": GATE_VID}
    variant = next(r for r in built.rows["sys_상품종형"] if r["종형ID"] == VID)
    waiting = {"로그ID": "LOG_old", "실행일시": EARLIER.isoformat(timespec="seconds"), "작업단계": "사람검토이관",
               "대상탭": "sys_급부", "대상행ID": benefit["급부ID"], "대상열": None, "변경전값": None, "변경후값": None,
               "호출모델": "교차 확인", "판정확률": None, "결과": "보류", "사유": "지어낸 검토 대기"}
    store = store_with({"sys_상품종형": [variant], "sys_특약": [old_rider, gate_main], "sys_급부": [benefit],
                        "sys_작업로그": [waiting]})
    report = L.load(store, targets(), INDEX, docs, values, NOW)
    assert report.written
    sheet = store.read(["sys_특약", "sys_작업로그"])
    rider = next(r for r in sheet["sys_특약"] if r["특약ID"] == first["특약ID"])
    assert (rider["최소가입금액만원"], rider["최대가입금액만원"]) == (100.0, 3000.0)
    # 관문전용 종형은 종형 행만 바꾸므로 다른 작업이 쓴 특약 행은 남는다
    assert any(r["특약ID"] == gate_main["특약ID"] for r in sheet["sys_특약"])
    passed = [r for r in sheet["sys_작업로그"] if r["대상행ID"] == benefit["급부ID"] and r["결과"] == "통과"]
    assert len(passed) == 1 and passed[0]["호출모델"] == L.MODEL


def test_only_gate_codes_write_variant_rows_only(docs, values):
    store = store_with()
    report = L.load(store, targets(), INDEX, docs, values, NOW, only=["Z2"])
    assert report.written and report.done == set() and report.gate_done == {OTHER_VID}
    sheet = store.read(["sys_상품종형", "sys_특약"])
    assert [r["종형ID"] for r in sheet["sys_상품종형"]] == [OTHER_VID] and sheet["sys_특약"] == []


def test_main_runs_a_dry_run_without_sheet_access(docs, values, tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("SPREADSHEET_ID", raising=False)
    target_file = tmp_path / "targets.json"
    target_file.write_text(json.dumps(targets(), ensure_ascii=False), encoding="utf-8")
    result, rows = tmp_path / "r" / "result.json", tmp_path / "r" / "rows.json"
    code = L.main(["--docs", str(docs), "--targets", str(target_file), "--values", f"Z1={values['Z1']}", "--dry-run",
                   "--result", str(result), "--rows", str(rows)])
    assert code == 0
    summary = json.loads(result.read_text(encoding="utf-8"))
    assert summary["시트에 씀"] is False and summary["종형 행"] == 3
    assert summary["쓰지 않은 줄"]["Z1"][L.WAITING] == 1
    assert summary["쓰지 않은 줄 번호"]["Z1"]["R006-1"] == RR.HOLD
    assert SENTENCE not in result.read_text(encoding="utf-8")
    made = json.loads(rows.read_text(encoding="utf-8"))
    assert len(made["행"]["sys_급부"]) == 5 and "Z1 R005-1" in made["행없음"]


def test_renewal_years_leave_out_banned_and_non_renewal_names():
    years = L.renewal_years(views(), 20, [BANNED.replace(" ", "")])
    assert years == {"갱신형 다라 수술비": 20}
    assert L.renewal_years(views(), None, []) == {}


def test_each_benefit_without_amount_leaves_one_extraction_log(docs, values):
    store = store_with()
    report = L.load(store, targets(), INDEX, docs, values, NOW)
    sheet = store.read(["sys_급부", "sys_작업로그"])
    target = next(r for r in sheet["sys_급부"] if r["원시급부명"] == "사아 치료비")
    logs = [r for r in sheet["sys_작업로그"] if r["작업단계"] == "추출" and r["대상열"] == "지급기준구분"]
    assert len(logs) == 1 and logs[0]["대상행ID"] == target["급부ID"]
    log = logs[0]
    assert (log["대상탭"], log["대상열"], log["변경후값"], log["결과"], log["호출모델"]) == \
        ("sys_급부", "지급기준구분", "차등지급", "통과", L.MODEL)
    p, c = RR.covers_by_number(views())["R005-1"]
    assert log["사유"] == f"판독 사유 항목별금액표, 번호 R005-1, 내용 지문 {RR.content_fingerprint(c)}"
    assert "항목별 금액" not in log["사유"]                    # 원문 글자는 싣지 않는다
    # 판정과 사람검토이관 기록이 아니므로 검토 대기로 잡히지 않는다. 종형마다 남기는 기록(rerun.coverage_logs)과도 섞이지 않는다
    assert not [r for r in sheet["sys_작업로그"] if r["대상행ID"] == target["급부ID"] and r["작업단계"] != "추출"]
    assert R.COVERED not in log["사유"]
    assert report.no_amount == {target["급부ID"]: log["사유"]}
    assert "금액 없는 급부(행없음 줄이 된 행): 1행 (차등지급 1)" in L.markdown(report)
    assert L.result_of(report)["금액 없는 급부"] == {"차등지급": 1}


def test_other_no_row_lines_are_still_left_out(docs, tmp_path):
    lines = [x if x["번호"] != "R005-1" else {**x, "sonnet": reading(꼴=RR.NO_ROW, 지급률=None, 행없음사유="그밖"),
                                              "opus": reading(꼴=RR.NO_ROW, 지급률=None, 행없음사유="그밖")}
             for x in VALUES]
    path = tmp_path / "other.jsonl"
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines), encoding="utf-8")
    report = L.load(store_with(), targets(), INDEX, docs, {"Z1": path}, NOW, dry_run=True)
    assert L.reason_counts(report.groups[0])[L.NO_ROW] == 1
    assert "사아 치료비" not in {r["원시급부명"] for r in report.rows["sys_급부"]}
    assert not [r for r in report.logs if r["대상열"] == "지급기준구분"]
