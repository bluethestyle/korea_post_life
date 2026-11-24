"""공시 문서 수집의 현대해상 연결(postlife.disclosure.sources의 hyundai)과 현대해상 대상 설정.

네트워크 없이 돈다. 접속 모듈의 검색과 내려받기 함수를 지어낸 행을 돌려주는 가짜로 바꿔 끼우고, sources가 그 행에서 대상
상품의 판매기간과 서류를 어떻게 고르는지만 본다. 응답을 읽는 일은 test_disclosure_hyundai.py가 본다.
상품명, 대표코드, 첨부 ID, 파일 이름은 지어낸 것이다(data/targets/hyundai.json을 읽는 테스트만 실제 설정을 본다).

공시상품코드 자리에는 목록 행의 대표코드(repInsCd)를 쓰고, 행은 종형의 공시상품명(목록 상품명에서 개정 표시를 뗀 이름)으로
고른다(2026-11-24 결정). 종형ID는 "HYUNDAI_<대표코드>_<종형명 해시>"다.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

from postlife import ids
from postlife.config import INSTITUTIONS, TREND_INSTITUTIONS
from postlife.disclosure import hyundai, sources
from postlife.extract import variants as VV
from postlife.validate import check_rows

ROOT = Path(__file__).resolve().parents[1]
ON = "2026-11-24"
CODE = "999Z"
NAME = "무배당현대해상가나다보험(갑) 1종(가형), 2종(나형)"     # 목록 상품명에서 개정 표시를 뗀 이름


def product(name, start, end=None, tag="A", selling=True, rep=CODE):
    return hyundai.Product(name, start, end, selling, "0302", rep,
                           {"약관": f"{tag}-C", "사업방법서": f"{tag}-M", "상품요약서": f"{tag}-S"})


ROWS = [
    product("무배당현대해상가나다보험(갑)(Hi2610) 1종(가형), 2종(나형)", "2026-10-21", tag="N"),
    product("무배당현대해상가나다보험(갑)(Hi2610) 3종(다형)", "2026-10-21", tag="X"),
    product("무배당현대해상하이콜가나다보험(갑)(Hi2610) 1종(가형), 2종(나형)", "2026-10-21", tag="H"),
    product("무배당현대해상가나다보험(갑)(Hi2607) 1종(가형), 2종(나형)", "2026-08-01", "2026-10-20",
            tag="P", selling=False),
    # 지난 개정의 상품명은 회사 이름이 없고 쉼표 뒤 빈칸이 없다
    product("무배당가나다보험(갑)(Hi2401) 1종(가형),2종(나형)", "2024-01-01", "2024-02-29",
            tag="O", selling=False),
    # 대표코드가 다른 판매기간 행(개정 중에 대표코드가 바뀐 적이 있다)
    product("무배당현대해상가나다보험(갑)(Hi2508) 1종(가형), 2종(나형)", "2025-09-01", "2025-11-13",
            tag="Q", selling=False, rep="998Y"),
]


@pytest.fixture
def rests(monkeypatch):
    got = []
    monkeypatch.setattr(sources, "pause", got.append)
    return got


@pytest.fixture
def searched(monkeypatch):
    asked = []
    monkeypatch.setattr(hyundai, "search_products", lambda s, keyword, on=None: asked.append(keyword) or
                        [p for p in ROWS if keyword in p.name])
    return asked


def find(code, name=None, on=ON):
    return sources.SOURCES["hyundai"].find(object(), code, on, name)


def test_registered_with_a_known_org_code():
    src = sources.SOURCES["hyundai"]
    assert src.org == "HYUNDAI" and src.org in INSTITUTIONS and src.org in TREND_INSTITUTIONS
    assert src.targets == "data/targets/hyundai.json" and "대표코드" in src.lookup and src.pause > 0


def test_series_name_drops_dividend_company_and_revision():
    assert hyundai.series_name(ROWS[0].name) == "가나다보험(갑) 1종(가형), 2종(나형)"
    assert hyundai.series_name("\t(무)현대해상라마바보험(Hi2607) 1종(가형)") == "라마바보험 1종(가형)"
    assert hyundai.same_series(ROWS[4].name, NAME) and hyundai.same_series(ROWS[3].name, NAME)
    assert not hyundai.same_series(ROWS[1].name, NAME) and not hyundai.same_series(ROWS[2].name, NAME)
    assert hyundai.keyword_of(NAME) == "가나다보험"
    # 괄호 없는 이름은 목록에서 이름 뒤에 개정 표시가 끼므로 빈칸 앞까지만 검색한다
    assert hyundai.keyword_of("(무)라마바보험 1종(가형)") == "라마바보험"
    assert hyundai.is_rep_code("131A") and hyundai.is_rep_code(" 11F0 ") and not hyundai.is_rep_code(NAME)


def test_finds_the_open_period_by_rep_code_and_product_name(searched, rests):
    name, docs = find(CODE, NAME)
    assert name == ROWS[0].name and searched == ["가나다보험"]
    assert [(d.kind, d.file_name, d.start, d.end) for d in docs] == [
        ("약관", "N-C.pdf", "2026-10-21", None), ("사업방법서", "N-M.pdf", "2026-10-21", None),
        ("상품요약서", "N-S.pdf", "2026-10-21", None)]
    assert all(d.code == CODE for d in docs)
    # 지난 날짜는 그날의 판매기간(지난 개정판). 공시상품명에 개정 표시가 남아 있어도 같은 상품이다
    assert find(CODE, NAME, on="2026-09-01")[0] == ROWS[3].name
    assert find(CODE, ROWS[0].name, on="2024-02-01")[1][0].file_name == "O-C.pdf"
    # 대표코드가 같아도 종 구성과 판매채널 상품이 다른 행은 공시상품명으로 가른다
    assert find(CODE, "무배당현대해상가나다보험(갑) 3종(다형)")[0] == ROWS[1].name
    assert find(CODE, "무배당현대해상하이콜가나다보험(갑) 1종(가형), 2종(나형)")[0] == ROWS[2].name
    # 대표코드가 다른 판매기간은 그 코드로만 찾는다
    assert find(CODE, NAME, on="2025-10-01") is None and find("998Y", NAME, on="2025-10-01")[0] == ROWS[5].name
    assert find("888Y", NAME) is None and rests == []


def test_code_must_be_a_rep_code_with_a_product_name(searched):
    with pytest.raises(ValueError, match="공시상품명"):
        find(CODE)
    with pytest.raises(ValueError, match="대표코드"):
        find("가나다보험(갑) 1종(일반형)", NAME)
    assert searched == []


def test_overlapping_periods_pick_the_latest_start_and_refuse_twins():
    rows = [product("가나(Hi2508) 1종", "2025-04-01", "2025-12-31", tag="A"),
            product("가나(Hi2504) 1종", "2025-09-01", "2025-11-13", tag="B")]
    assert hyundai.pick_period(rows, "2025-10-01").files["상품요약서"] == "B-S"
    assert hyundai.pick_period(rows, "2025-05-01").files["상품요약서"] == "A-S"
    assert hyundai.pick_period(rows, "2026-01-01") is None
    twins = [product("가나(Hi2601) 1종", "2026-01-01", tag="C"), product("가나(Hi2601) 1종", "2026-01-01", tag="D")]
    with pytest.raises(ValueError, match="서류가 서로 다름"):
        hyundai.pick_period(twins, "2026-02-01")
    # 같은 서류를 가리키는 두 행은 고를 수 있다
    assert hyundai.pick_period(twins[:1] * 2, "2026-02-01") is not None


def test_download_rests_between_the_two_requests(monkeypatch, searched, rests):
    asked = []
    monkeypatch.setattr(hyundai, "file_info", lambda s, doc: asked.append(("정보", doc.apnfl_id)) or
                        hyundai.FileInfo(doc.apnfl_id, "/data/202611", "20261102", "pdf"))
    monkeypatch.setattr(hyundai, "fetch", lambda s, info: asked.append(("파일", info.apnfl_id)) or b"%PDF-1.7\n")
    _, docs = find(CODE, NAME)
    summary = next(d for d in docs if d.kind == "상품요약서")
    assert sources.SOURCES["hyundai"].download(object(), summary) == b"%PDF-1.7\n"
    assert asked == [("정보", "N-S"), ("파일", "N-S")] and rests == [sources.GAP]


_spec = importlib.util.spec_from_file_location("fetch_disclosure_hyundai", ROOT / "scripts/fetch_disclosure.py")
fd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fd)

TARGETS = {
    "기관코드": "HYUNDAI", "공시목록URL": hyundai.LIST_PAGE,
    "상품": [{"모상품ID": "HYUNDAI_GANADA_SE", "개정연월": "2610", "비교역할구분": "정밀비교", "갱신유형": "비갱신",
              "갱신주기년": None, "환급유형": "표준형", "납입면제적용": False, "갱신형특약주기년": 20,
              "종형": [{"공시상품코드": CODE, "공시상품명": NAME, "종형명": "1종(가형)", "심사유형": "일반심사",
                        "간편고지약칭": "일반"},
                       {"공시상품코드": CODE, "공시상품명": NAME, "종형명": "2종(나형)", "심사유형": "일반심사",
                        "간편고지약칭": "일반", "비교역할구분": "관문전용"}]}],
}


def test_script_saves_under_the_rep_code_and_variants_take_it_as_the_id(tmp_path, monkeypatch, searched, rests):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(fd, "pdf_pages", lambda data: ["첫 쪽"])
    monkeypatch.setattr(fd, "pause", lambda s: None)
    monkeypatch.setattr(fd, "session", lambda: object())
    monkeypatch.setattr(hyundai, "file_info", lambda s, doc: hyundai.FileInfo(doc.apnfl_id, "/d", doc.apnfl_id, "pdf"))
    monkeypatch.setattr(hyundai, "fetch", lambda s, info: b"%PDF-1.7\n" + info.apnfl_id.encode())
    target = tmp_path / "t.json"
    target.write_text(json.dumps(TARGETS, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "out"
    # 기준일은 오늘이다. 지어낸 지금 판매기간(2026-10-21~)은 끝나는 날이 없다
    monkeypatch.setattr(sys, "argv", ["fetch_disclosure.py", "--org", "hyundai", "--out", str(out), "--targets", str(target)])
    assert fd.main() == 0
    assert searched == ["가나다보험"]          # 종형 둘이 같은 대표코드와 공시상품명이라 한 번만 찾는다
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert [(e["기관"], e["상품코드"], e["상품명"], e["문서"], e["파일"]) for e in index] == [
        ("HYUNDAI", CODE, ROWS[0].name, "사업방법서", "N-M.pdf"), ("HYUNDAI", CODE, ROWS[0].name, "상품요약서", "N-S.pdf")]
    assert (out / f"hyundai_{CODE}_상품요약서.pdf").read_bytes().endswith(b"N-S")
    assert (out / f"hyundai_{CODE}_사업방법서.pdf").exists()
    # 이 색인으로 만든 종형 행: 종형ID는 대표코드를 쓰고, 공시상품명은 그날 판매기간의 목록 상품명이다
    variants, problems = VV.build(TARGETS, index)
    assert problems == [] and [v.id for v in variants] == [ids.variant_id("HYUNDAI", CODE, "1종(가형)"),
                                                           ids.variant_id("HYUNDAI", CODE, "2종(나형)")]
    assert all(re.fullmatch(r"HYUNDAI_999Z_[0-9a-f]{6}", v.id) for v in variants)
    assert {v.row["공시상품명"] for v in variants} == {ROWS[0].name}
    assert check_rows("sys_상품종형", [v.row for v in variants]) == {}


# ---------------------------------------------------------------------------
# 실제 대상 설정(data/targets/hyundai.json)
# ---------------------------------------------------------------------------

REAL = json.loads((ROOT / "data/targets/hyundai.json").read_text(encoding="utf-8"))


def fake_index(targets):
    """설정의 공시상품코드마다 사업방법서와 상품요약서가 받아진 것처럼 꾸민 수집 색인."""
    names = {v["공시상품코드"]: v["공시상품명"] for p in targets["상품"] for v in p["종형"]}
    return [{"기관": "HYUNDAI", "상품코드": code, "상품명": name,
             "판매시작일": "2026-10-21", "판매종료일": None, "문서": kind, "해시": f"h{code}{kind}",
             "저장이름": f"hyundai_{code}_{kind}", "쪽수": 1}
            for code, name in names.items() for kind in ("사업방법서", "상품요약서")]


def test_real_targets_use_rep_codes_with_one_product_name_per_code():
    names: dict[str, set[str]] = {}
    for p in REAL["상품"]:
        for v in p["종형"]:
            assert hyundai.is_rep_code(v["공시상품코드"]) and v["공시상품명"], v["종형명"]
            assert not re.search(r"\(\s*Hi\s*\d{4}\s*\)", v["공시상품명"]), v["공시상품명"]     # 개정 표시를 뗀 이름
            names.setdefault(v["공시상품코드"], set()).add(v["공시상품명"])
    assert sorted(names) == ["11F0", "131A"] and all(len(n) == 1 for n in names.values())
    assert {p["모상품ID"] for p in REAL["상품"]} == {"HYUNDAI_PERFECT_PLUS_SE", "HYUNDAI_NAESAMEN_3N_SIMPLE_SE"}


def test_real_targets_make_distinct_variant_ids_and_lineage_keys():
    variants, problems = VV.build(REAL, fake_index(REAL))
    rows = [v.row for v in variants]
    assert problems == [] and len(rows) == 21
    assert check_rows("sys_상품종형", rows) == {}
    assert len({r["종형ID"] for r in rows}) == 21 and len({r["종형계보키"] for r in rows}) == 21
    assert all(re.fullmatch(r"HYUNDAI_(131A|11F0)_[0-9a-f]{6}", r["종형ID"]) for r in rows)
    precise = sorted((r["모상품ID"], r["간편고지약칭"]) for r in rows if r["비교역할구분"] == "정밀비교")
    assert precise == [("HYUNDAI_NAESAMEN_3N_SIMPLE_SE", "3.5.5"), ("HYUNDAI_PERFECT_PLUS_SE", "일반")]
    assert VV.attributes(REAL).keys() == {r["종형ID"] for r in rows}
    # 스냅샷의 다른 회사 종형과 ID, 계보키가 겹치지 않는다
    snapshot = [json.loads(line) for line in (ROOT / "data/snapshot/sys_상품종형.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()]
    assert not {r["종형ID"] for r in rows} & {s["종형ID"] for s in snapshot}
    assert not {r["종형계보키"] for r in rows} & {s["종형계보키"] for s in snapshot}
