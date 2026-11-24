"""KB라이프생명 요약서를 두 판독으로 읽고 적재하는 길.

한 요약서를 형(간편심사형, 일반심사형)마다 다른 공시상품코드가 함께 쓰고, 간편심사형 구간은 정밀비교 종형(3.5.5)과 관문전용
종형(3.3.5)이 함께 쓴다. 세부보장 이름 칸이 없어 한 특약의 여러 행이 이름이 같은 줄이 되고 대상으로 갈린다. 주계약 표의 이름 칸은
급부명이라 주계약 조각의 특약 이름은 "주계약"이다. 시험 자료는 이 꼴만 본떠 지어낸 것이다(특약과 담보 이름, 문구, 금액).
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from postlife import ids
from postlife.extract import reader_rows as RR
from postlife.extract import tables as T
from postlife.sheets_io import MemoryBackend, SheetStore
from postlife.snapshot import KST

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import load_reader_product as L  # noqa: E402

NOW = datetime(2026, 11, 23, 18, 0, tzinfo=KST)
ORG = "TESTLIFE"
SIMPLE, SIMPLE_GATE, GENERAL = "간편심사형(3.5.5)(가형)", "간편심사형(3.3.5)(가형)", "일반심사형(가형)"


def cover(name, reason, amount, page=10):
    return {"보장명": name, "지급사유": reason, "지급금액": amount, "쪽": page, "적용범위": ""}


def piece(title, covers, segment, label="선택특약", page=10):
    return {"특별약관": title, "구분": label, "적용범위": "", "형": segment, "첫쪽": page, "끝쪽": page,
            "주계약": label == "주계약", "세부보장": covers}


CANCERS = ["가암", "나암(전이포함)", "다암 및 라암"]
PIECES = {"형식": RR.PIECES_FORMAT, "출처": {"문서": "test_K1_상품요약서", "꼴": "kblife"}, "주석": [], "조각": [
    piece("주계약", [cover("사망보험금", "보험기간 중 사망 시", "보험가입금액")], "간편심사형", label="주계약"),   # R001
    piece("(간편)가나통합진단특약", [                                                                         # R002
        cover("(간편)가나통합진단특약", f"가나보장개시일(60일) 이후 {c}으로 진단되면 (처음 한 번만)",
              "보험가입금액 (3년미만 가입금액의 30%)") for c in CANCERS], "간편심사형"),
    piece("(간편)마바보장(적립액 미지급형)특약", [cover("(간편)마바보장(적립액 미지급형)특약",
                                                       "보험기간 중 마바 상태 시 (최초 1회한)", "보험가입금액")],
          "간편심사형"),                                                                                     # R003
    piece("주계약", [cover("사망보험금", "보험기간 중 사망 시", "보험가입금액")], "일반심사형", label="주계약", page=20),
    piece("가나통합진단특약", [
        cover("가나통합진단특약", f"가나보장개시일(60일) 이후 {c}으로 진단되면 (처음 한 번만)", "보험가입금액", page=20)
        for c in CANCERS], "일반심사형", page=20),                                                         # R005
]}


def test_kblife_main_piece_is_named_main_and_keeps_the_benefit_name():
    assert T.KBLIFE.main_title == "주계약" and T.KBLIFE.main_label == "주계약"
    assert T.MERITZ.main_title == "" and T.SAMSUNGFIRE.main_title == ""      # 다른 회사의 조각은 그대로


def test_main_flag_makes_the_main_rider_and_same_name_lines_split_by_target():
    pieces = [p for p in RR.load_pieces(PIECES) if p.segment == "간편심사형"]
    assert pieces[0].main is True and pieces[1].main is False
    readings = {}
    for p in pieces:
        for c in p.covers:
            readings[c.number] = {**RR.DEFAULTS, "번호": c.number, "쪽": c.page, "꼴": RR.NO_ROW,
                                  "행없음사유": "항목별금액표", "모름": []}
    for c, target in zip(pieces[1].covers, CANCERS):
        readings[c.number]["대상"] = target
    built = RR.build_rows("V1", pieces, readings)
    assert [(r["원시특약명"], r["담보구분"]) for r in built.riders] == [
        ("주계약", "주계약"), ("(간편)가나통합진단특약", "선택특약"), ("(간편)마바보장(적립액 미지급형)특약", "선택특약")]
    assert built.riders[0]["특약ID"] == ids.rider_id("V1", "주계약")
    names = [b["원시급부명"] for b in built.benefits]
    assert names == ["사망보험금"] + [f"(간편)가나통합진단특약({c})" for c in CANCERS] + \
        ["(간편)마바보장(적립액 미지급형)특약"]
    assert len({b["급부ID"] for b in built.benefits}) == 5 and not built.skipped


def test_refund_type_in_a_rider_name_is_not_a_sentence():
    ok = RR.CoverView("R001-1", "(간편)마바보장(적립액 미지급형)특약", "마바 상태 시", "보험가입금액", 10)
    bad = RR.CoverView("R001-2", "가나 진단 시 지급", "가나 진단 시", "보험가입금액", 10)
    assert RR.name_problem(ok) == ""
    assert RR.name_problem(bad).startswith(RR.HOLD)


def targets():
    simple = {"심사유형": "간편심사", "간편고지약칭": "3.5.5"}
    return {"기관코드": ORG, "공시목록URL": "https://example.invalid/list", "상품": [
        {"모상품ID": "TESTLIFE_GANA", "개정연월": "2610", "비교역할구분": "정밀비교", "갱신유형": "비갱신", "갱신주기년": None,
         "환급유형": "표준형", "납입면제적용": False, "갱신형특약주기년": 20,
         "종형": [{"공시상품코드": "K1", "종형명": SIMPLE, **simple},
                  {"공시상품코드": "K3", "종형명": SIMPLE_GATE, "심사유형": "간편심사", "간편고지약칭": "3.3.5",
                   "비교역할구분": "관문전용"},
                  {"공시상품코드": "K5", "종형명": GENERAL, "심사유형": "일반심사", "간편고지약칭": "일반"}]}]}


# 세 코드가 같은 요약서와 사업방법서를 쓴다(해시가 같다)
INDEX = [{"기관": ORG, "상품코드": code, "상품명": f"가나 건강보험({code})", "판매시작일": "2026-10-01", "판매종료일": None,
          "문서": kind, "쪽수": 46, "해시": f"h-{kind}", "저장이름": f"test_{code}_{kind}"}
         for code in ("K1", "K3", "K5") for kind in ("상품요약서", "사업방법서")]


def _values(path, numbers, raw, value, **change):
    lines = []
    for n in numbers:
        p, c = raw[n]
        lines.append({"번호": n, "쪽": c.page, "특약명": p.title, "급부명": c.name, "조각지문": RR.cover_fingerprint(p, c),
                      "sonnet": value, "opus": value, "판정": "확정", "판정값": None, **change.get(n, {})})
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines), encoding="utf-8")
    return path


def test_load_joins_the_value_files_of_codes_sharing_one_summary(tmp_path, monkeypatch):
    folder = tmp_path / "out"
    folder.mkdir()
    for e in INDEX:
        (folder / f"{e['저장이름']}.pdf").write_bytes(b"%PDF-1.4 test")
    monkeypatch.setattr(L, "read_pieces", lambda pdf, layout: (RR.load_pieces(PIECES), {}))
    raw = RR.covers_by_number(RR.load_pieces(PIECES))
    value = RR.stored_value({**RR.DEFAULTS, "쪽": 10, "꼴": RR.NO_ROW, "행없음사유": "항목별금액표"})
    targeted = {f"R{i:03d}-{j}": {"sonnet": {**value, "대상": c}, "opus": {**value, "대상": c}}
                for i in (2, 5) for j, c in enumerate(CANCERS, 1)}
    simple = _values(tmp_path / "k1.jsonl", ["R001-1", "R002-1", "R002-2", "R002-3", "R003-1"], raw, value, **targeted)
    general = _values(tmp_path / "k5.jsonl", ["R004-1", "R005-1", "R005-2", "R005-3"], raw, value, **targeted)
    vids = {name: ids.variant_id(ORG, code, name) for code, name in (("K1", SIMPLE), ("K3", SIMPLE_GATE), ("K5", GENERAL))}

    report = L.load(SheetStore(MemoryBackend()), targets(), INDEX, folder, {"K1": simple, "K5": general}, NOW,
                    dry_run=True, layout=L.LAYOUTS["kblife"])
    [group] = report.groups
    assert group.code == "K1+K5" and not group.reasons
    # 간편심사형 조각은 정밀비교 종형(3.5.5)에만, 일반심사형 조각은 일반심사형 종형에만 행이 된다. 관문전용(3.3.5)은 종형 행뿐
    assert report.done == {vids[SIMPLE], vids[GENERAL]} and report.gate_done == {vids[SIMPLE_GATE]}
    by_variant = {}
    for r in report.rows["sys_특약"]:
        by_variant.setdefault(r["종형ID"], []).append(r["원시특약명"])
    assert by_variant == {vids[SIMPLE]: ["주계약", "(간편)가나통합진단특약", "(간편)마바보장(적립액 미지급형)특약"],
                          vids[GENERAL]: ["주계약", "가나통합진단특약"]}
    assert len(report.rows["sys_급부"]) == 9 and not report.clashes

    # 한쪽 값 파일만 있으면 그 형의 줄만 쓰고 나머지는 값 파일에 없음
    report = L.load(SheetStore(MemoryBackend()), targets(), INDEX, folder, {"K1": simple}, NOW, dry_run=True,
                    layout=L.LAYOUTS["kblife"])
    [group] = report.groups
    assert group.code == "K1"
    assert {n for n, why in group.reasons.items() if why == L.NOT_IN_VALUES} == {"R004-1", "R005-1", "R005-2", "R005-3"}

    # 같은 번호가 두 값 파일에 서로 다르게 있으면 그 번호는 쓰지 않는다
    clash = _values(tmp_path / "k5b.jsonl", ["R001-1"], raw, {**value, "행없음사유": "그밖"})
    lines, clashing = L.merged_lines([simple, clash])
    assert clashing == {"R001-1"} and "R001-1" not in {x["번호"] for x in lines}
    report = L.load(SheetStore(MemoryBackend()), targets(), INDEX, folder, {"K1": simple, "K5": clash}, NOW,
                    dry_run=True, layout=L.LAYOUTS["kblife"])
    assert report.groups[0].reasons["R001-1"] == L.CLASH
