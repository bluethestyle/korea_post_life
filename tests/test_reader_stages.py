"""한 특약 안에 계약 단계마다 표가 따로 있는 생명보험사 요약서(교보생명)를 이중 추출로 읽고 적재하는 길.

읽을 계약 단계 고르기(reader_rows.for_stages), 배치 나누기의 --stage(scripts/split_pieces.py), 적재의 읽을단계
(scripts/load_reader_product.py). 테스트 자료는 교보생명 요약서의 구조(세부보장 적용범위의 단계 이름, "■ 단계" 주석)만 본떠
지어낸 것이다. 특약과 담보 이름, 문구, 금액은 지어냈다.
"""
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

from postlife import ids
from postlife.extract import reader_rows as RR
from postlife.sheets_io import MemoryBackend, SheetStore
from postlife.snapshot import KST

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import load_reader_product as L  # noqa: E402

_SPLIT = importlib.util.spec_from_file_location("split_pieces_stages", ROOT / "scripts" / "split_pieces.py")
split_pieces = importlib.util.module_from_spec(_SPLIT)
_SPLIT.loader.exec_module(split_pieces)

NOW = datetime(2026, 11, 24, 18, 0, tzinfo=KST)
STAGES = ["최초계약", "보장형 계약"]


def cover(name, reason, amount, only="", page=10):
    return {"보장명": name, "지급사유": reason, "지급금액": amount, "쪽": page, "적용범위": only}


def piece(title, covers, label="선택특약", page=10, main=False):
    return {"특별약관": title, "구분": label, "적용범위": "", "첫쪽": page, "끝쪽": page + 1, "주계약": main,
            "세부보장": covers}


def note(head, text, page=10):
    return {"쪽": page, "형": "", "특약머리": head, "글": text}


GANA = "무배당 가나수술특약(갱신형)"
MABA = "무배당 마바진단특약LH(무해약형)"
PIECES = {"형식": RR.PIECES_FORMAT, "출처": {"문서": "test_K1_상품요약서", "꼴": "kyobo"}, "주석": [
    note(GANA, "■ 최초계약"),
    note(GANA, "(기준 : 가나특약 가입금액 500만원)"),
    note(GANA, "(주)\n1. 가나 수술의 1년 미만 감액은 갱신 뒤에는 쓰지 않음."),
    note(GANA, "■ 갱신계약", 11),
    note(GANA, "※ 갱신 뒤에는 수술마다 따로 갱신함.", 11),
    note(MABA, "■ 보장형 계약", 12),
    note(MABA, "■ 연장전환형 계약", 13),
], "조각": [
    piece("주계약", [cover("가나 사망보험금", "사망시", "보험가입금액 100%")], label="기본계약", main=True, page=9),
    piece(GANA, [                                                                              # R002
        cover("가나 수술보험금", "가나 수술시", "100만원 (가입 1년 안이면 절반)", "최초계약"),
        cover("다라 수술보험금", "다라 수술시", "50만원", "최초계약"),
        cover("가나 수술보험금", "가나 수술시", "100만원", "갱신계약", 11),
        cover("다라 수술보험금", "다라 수술시", "50만원", "갱신계약", 11),
    ]),
    piece(MABA, [                                                                              # R003
        cover("마바 진단보험금", "마바 진단시", "[1년이상] 300만원 [1년미만] 150만원", "보장형 계약", 12),
        cover("마바 진단보험금", "마바 진단시", "300만원", "연장전환형 계약", 13),
    ], page=12),
    piece("무배당 사아입원특약", [cover("사아 입원보험금", "사아 입원시", "1일당 3만원")], page=14),   # R004
    piece("무배당 자차특약(갱신형)", [cover("자차 보험금", "자차시", "10만원", "갱신계약", 16)], page=16),  # R005
]}
KEPT = ["R001-1", "R002-1", "R002-2", "R003-1", "R004-1"]
OUT = ["R002-3", "R002-4", "R003-2", "R005-1"]


# ---------------------------------------------------------------------------
# 읽을 계약 단계 고르기
# ---------------------------------------------------------------------------

def test_stage_of_tells_contract_stages_from_kind_marks():
    view = lambda only: RR.CoverView("R001-1", "가", "나", "다", 1, only)       # noqa: E731
    assert RR.stage_of(view("최초계약")) == "최초계약"
    assert RR.stage_of(view("보장형 계약")) == "보장형 계약"
    assert RR.stage_of(view("1종,2종")) == "" and RR.stage_of(view("")) == ""


def test_for_stages_drops_other_stage_lines_and_keeps_numbers_texts_and_notes():
    views = RR.load_pieces(PIECES)
    kept, lines, whole = RR.for_stages(views, STAGES)
    assert [c.number for p in kept for c in p.covers] == KEPT
    assert lines == OUT and whole == [5]                    # 갱신계약 줄만 있는 추출 단위는 통째로 빠진다
    before = RR.covers_by_number(views)
    for p in kept:
        for c in p.covers:
            assert c == before[c.number][1]                # 글자와 적용범위는 그대로
    gana = next(p for p in kept if p.title == GANA)
    assert "■ 갱신계약" in gana.notes and any("갱신 뒤에는" in n for n in gana.notes)    # 주석은 그대로 남는다
    # 이름이 같은 줄이 단계로만 갈렸으므로 빼고 나면 이름 같은 줄이 없다
    assert not any(RR.same_name_groups(p) for p in kept)
    # 빈칸은 보지 않는다. 단계를 주지 않으면 아무것도 빼지 않는다
    assert RR.for_stages(views, ["최초 계약", "보장형계약"])[1] == OUT
    assert RR.for_stages(views, []) == (list(views), [], [])
    # 종 표시 적용범위(삼성생명)는 단계가 아니다
    kinds = RR.load_pieces({**PIECES, "조각": [piece("가", [cover("가", "나", "다", "1종,2종")])]})
    assert RR.for_stages(kinds, STAGES)[1] == []


# ---------------------------------------------------------------------------
# 배치 나누기 --stage
# ---------------------------------------------------------------------------

def test_split_with_stage_drops_lines_keeps_notes_and_names_the_stages():
    dropped = split_pieces.Dropped()
    [bundle] = split_pieces.split(PIECES, "K1", stages=STAGES, dropped=dropped)
    assert bundle["읽을단계"] == STAGES and "읽을종" not in bundle
    assert [p["조각번호"] for p in bundle["조각"]] == ["R001", "R002", "R003", "R004"]
    assert [c["번호"] for p in bundle["조각"] for c in p["세부보장"]] == KEPT
    assert bundle["세부보장수"] == 5
    assert dropped.pieces == ["R005"] and dropped.covers == OUT
    gana = bundle["조각"][1]
    assert [c["적용범위"] for c in gana["세부보장"]] == ["최초계약", "최초계약"]
    assert "■ 갱신계약" in gana["주석"] and not any(c.get("이름같은줄") for c in gana["세부보장"])
    # 배치로 읽어도 같은 줄이다(교차 검증이 쓰는 추출 단위)
    assert [c.number for p in RR.load_pieces(bundle) for c in p.covers] == KEPT
    # 단계를 주지 않으면 전과 같다: 단계로 갈린 같은 이름 줄에 이름같은줄이 붙는다
    [plain] = split_pieces.split(PIECES, "K1")
    assert plain == split_pieces.split(PIECES, "K1", stages=[])[0]
    assert "읽을단계" not in plain and plain["세부보장수"] == 9
    assert [c.get("이름같은줄", False) for c in plain["조각"][1]["세부보장"]] == [True, True, True, True]


def test_split_script_writes_the_stage_in_the_index_and_without_it_is_unchanged(tmp_path, capsys):
    src = tmp_path / "pieces.json"
    src.write_text(json.dumps(PIECES, ensure_ascii=False), encoding="utf-8")
    assert split_pieces.main([str(src), "--out", str(tmp_path / "a"), "--name", "K1", "--stage", "최초계약",
                              "--stage", "보장형 계약"]) == 0
    printed = capsys.readouterr().out
    assert "읽을 단계 최초계약, 보장형 계약: 뺀 조각 1, 뺀 세부보장 4" in printed
    index = json.loads((tmp_path / "a" / "K1_index.json").read_text(encoding="utf-8"))
    assert index[-1] == {"읽을단계": STAGES, "뺀 조각": ["R005"], "뺀 세부보장": OUT}
    assert split_pieces.main([str(src), "--out", str(tmp_path / "b"), "--name", "K1"]) == 0
    index_b = json.loads((tmp_path / "b" / "K1_index.json").read_text(encoding="utf-8"))
    assert [set(x) for x in index_b] == [{"파일", "묶음", "쪽", "조각수", "세부보장수"}]
    assert "읽을 단계" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 적재
# ---------------------------------------------------------------------------

ORG = "TESTSTAGE"
PRECISE, GATE = "가나형/355", "가나형/335"
VID = ids.variant_id(ORG, "K1", PRECISE)
INDEX = [{"기관": ORG, "상품코드": "K1", "상품명": "가나 건강보험(K1)", "판매시작일": "2026-08-26", "판매종료일": None,
          "문서": kind, "쪽수": 80, "해시": f"h-{kind}", "저장이름": f"test_K1_{kind}"} for kind in ("상품요약서", "사업방법서")]


def targets(stages=True):
    precise = {"공시상품코드": "K1", "종형명": PRECISE, "심사유형": "간편심사", "간편고지약칭": "3.5.5"}
    if stages:
        precise["읽을단계"] = list(STAGES)
    return {"기관코드": ORG, "공시목록URL": "https://example.invalid/list", "상품": [
        {"모상품ID": "TESTSTAGE_GANA", "개정연월": "2608", "비교역할구분": "정밀비교", "갱신유형": "비갱신", "갱신주기년": None,
         "환급유형": "표준형", "납입면제적용": True, "갱신형특약주기년": 20,
         "종형": [precise, {"공시상품코드": "K1", "종형명": GATE, "심사유형": "간편심사", "간편고지약칭": "3.3.5",
                            "비교역할구분": "관문전용"}]}]}


def run_load(tmp_path, monkeypatch, stages=True):
    folder = tmp_path / "out"
    folder.mkdir(exist_ok=True)
    for e in INDEX:
        (folder / f"{e['저장이름']}.pdf").write_bytes(b"%PDF-1.4 test")
    monkeypatch.setattr(L, "read_pieces", lambda pdf, layout: (RR.load_pieces(PIECES), {}))
    raw = RR.covers_by_number(RR.load_pieces(PIECES))
    value = RR.stored_value({**RR.DEFAULTS, "쪽": 10, "꼴": RR.NO_ROW, "행없음사유": "항목별금액표"})
    lines = []
    for n in KEPT:                       # 배치에 든 줄만 검증 결과 파일에 있다(배치 나누기가 --stage로 뺀 줄은 없다)
        p, c = raw[n]
        lines.append({"번호": n, "쪽": c.page, "특약명": p.title, "급부명": c.name, "조각지문": RR.cover_fingerprint(p, c),
                      "sonnet": value, "opus": value, "판정": "확정", "판정값": None})
    path = tmp_path / "values.jsonl"
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines), encoding="utf-8")
    return L.load(SheetStore(MemoryBackend()), targets(stages), INDEX, folder, {"K1": path}, NOW, dry_run=True,
                  layout=L.LAYOUTS["kyobo"])


def test_load_uses_the_read_stages_only_and_counts_lines_left_out(tmp_path, monkeypatch):
    report = run_load(tmp_path, monkeypatch)
    [group] = report.groups
    assert group.stages == {PRECISE: STAGES}
    assert group.out_of_stage == OUT and group.out_of_kind == []
    assert group.used == KEPT and not group.reasons
    assert {r["종형ID"] for r in report.rows["sys_특약"]} == {VID}
    assert len(report.rows["sys_급부"]) == 5
    assert "읽을 계약 단계(보장형 계약, 최초계약)가 아니어서 뺀 세부보장: 4줄" in L.markdown(report)
    result = L.result_of(report)
    assert result["읽을 단계가 아니어서 뺀 줄"] == {"K1": 4} and "읽을 종이 아니어서 뺀 줄" not in result


def test_without_read_stages_the_same_name_first_contract_lines_are_lost(tmp_path, monkeypatch):
    """읽을단계가 없으면 배치에서 뺀 갱신계약 줄이 검증 결과 파일에 없어, 이름이 같은 최초계약 줄까지 행을 만들지 못한다.
    적재도 배치 나누기와 같은 줄을 빼야 하는 까닭이다."""
    report = run_load(tmp_path, monkeypatch, stages=False)
    [group] = report.groups
    assert group.stages == {} and group.out_of_stage == []
    assert {n for n, why in group.reasons.items() if why == L.NOT_IN_VALUES} == {"R002-3", "R002-4", "R003-2", "R005-1"}
    assert len(report.rows["sys_급부"]) == 2             # 주계약과 사아 입원만 남는다
    assert "읽을 단계가 아니어서 뺀 줄" not in L.result_of(report)
