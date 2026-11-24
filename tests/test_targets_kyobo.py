"""교보생명 추출 대상 설정(data/targets/kyobo.json)을 종형 만들기, 급부 적재, 수집 스크립트가 그대로 받는지 본다.

네트워크 없이 돈다. 공시실 응답(상품 목록 행, 서류 목록, 내려받은 파일)은 지어낸 가짜로 바꿔 끼운다. 가짜 행의 상품명과 파일
이름은 지어낸 것이고, 공시상품코드만 설정의 값이다.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from postlife.disclosure import kyobo, sources
from postlife.extract import reader_rows as RR
from postlife.extract import variants as VV
from postlife.validate import check_rows

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data/targets/kyobo.json"
TARGETS = json.loads(PATH.read_text(encoding="utf-8"))
STAGES = ["최초계약", "보장형 계약"]
ROLES = {"무해약환급금형": "정밀비교", "무해약환급금형/305": "관문전용", "무해약환급금형/315": "관문전용",
         "무해약환급금형/325": "정밀비교", "무해약환급금형/335": "관문전용", "무해약환급금형/345": "관문전용",
         "무해약환급금형/355": "정밀비교"}

_spec = importlib.util.spec_from_file_location("fetch_disclosure_kyobo", ROOT / "scripts/fetch_disclosure.py")
fd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fd)


def codes():
    return sorted({v["공시상품코드"] for p in TARGETS["상품"] for v in p["종형"]})


def fake_index():
    return [{"기관": TARGETS["기관코드"], "상품코드": c, "상품명": f"가나건강보험 {c}", "판매시작일": "2026-08-26",
             "판매종료일": None, "문서": kind, "해시": f"h{c}{kind}", "저장이름": f"kyobo_{c}_{kind}", "쪽수": 1}
            for c in codes() for kind in ("상품요약서", "사업방법서")]


def snapshot_variants():
    path = ROOT / "data/snapshot/sys_상품종형.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# 종형 만들기
# ---------------------------------------------------------------------------

def test_kyobo_targets_build_seven_variants_with_distinct_ids_not_on_the_snapshot():
    found, problems = VV.build(TARGETS, fake_index())
    assert problems == [] and len(found) == 7
    assert len({v.id for v in found}) == 7 and len({v.row["종형계보키"] for v in found}) == 7
    assert {v.row["종형명"]: v.row["비교역할구분"] for v in found} == ROLES
    assert {v.row["모상품ID"] for v in found} == {"KYOBO_MYPLAN_HEALTH", "KYOBO_SIMPLE_MYPLAN_HEALTH"}
    assert codes() == ["1001031", "1001042"]
    assert check_rows("sys_상품종형", [v.row for v in found]) == {}
    # 스냅샷의 종형과 ID, 계보키가 겹치지 않는다
    snap = snapshot_variants()
    for column in ("종형ID", "종형계보키", "개정판ID"):
        assert not {v.row[column] for v in found} & {r[column] for r in snap}, column
    assert VV.attributes(TARGETS) == {v.id: {k: v.row[k] for k in VV.OPTIONAL} for v in found}
    assert all(v.plain_renewal_years == 20 for v in found)


def test_kyobo_targets_read_stages_renewal_exclusions_and_disclosure_columns():
    products = TARGETS["상품"]
    assert [p["갱신형특약주기년"] for p in products] == [20, 20]
    assert [len(p["갱신형특약제외"]) for p in products] == [21, 16]
    assert all(p["납입면제적용"] is True and p["갱신유형"] == "비갱신" for p in products)
    for p in products:
        names = [x["특약명"] for x in p["갱신형특약제외"]]
        assert len({RR._squash(n) for n in names}) == len(names) and all(RR.is_renewal(n) for n in names)
        for v in p["종형"]:
            precise = (v.get("비교역할구분") or p["비교역할구분"]) == "정밀비교"
            assert (v.get("읽을단계") == STAGES) == precise, v["종형명"]
            assert "읽을종" not in v
            if v["심사유형"] == "간편심사":
                listed = v["고지중대질병목록"].split(", ")
                assert len(listed) == v["고지중대질병수"] == 6 and v["고지소견범위"] == "서면"
                assert v["고지입원수술년수"] == int(v["간편고지약칭"].split(".")[1])


def test_load_script_reads_the_stages_from_the_targets():
    sys.path.insert(0, str(ROOT / "scripts"))
    import load_reader_product as L

    stages = L.stages_of(TARGETS)
    assert stages == {("1001031", "무해약환급금형"): STAGES, ("1001042", "무해약환급금형/325"): STAGES,
                      ("1001042", "무해약환급금형/355"): STAGES}
    assert L.kinds_of(TARGETS) == {}
    assert "kyobo" in L.LAYOUTS


# ---------------------------------------------------------------------------
# 수집 스크립트(--org kyobo): 가짜 공시실로 대상 설정을 읽고, 받은 결과를 종형 만들기가 받는다
# ---------------------------------------------------------------------------

def ky_rows():
    def row(seq, code, name, addon=False):
        return kyobo.Product(seq, code, name, True, "PAMS04", "02", "2026-08-26", addon, {})
    return [row("1", "1001031", "가나플랜건강보험Ⅱ"), row("2", "1001031", "가나플랜건강보험 중도부가특약", True),
            row("3", "1001042", "가나간편플랜건강보험Ⅱ"), row("4", "1001032", "가나플랜건강보험Ⅱ(통신)")]


def ky_docs(product):
    return [kyobo.Document(product.seq, "9", kind, f"KEY_{product.seq}_{kind}", f"{product.name} {kind}.pdf",
                           "2026-08-26", None, product.name) for kind in ("상품요약서", "약관", "사업방법서")]


@pytest.fixture
def bench(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(sources, "pause", lambda s: None)
    monkeypatch.setattr(fd, "pause", lambda s: None)
    monkeypatch.setattr(fd, "session", lambda: object())
    monkeypatch.setattr(fd, "pdf_pages", lambda data: ["첫 쪽", "둘째 쪽"])
    asked = {"search": [], "docs": [], "get": []}
    monkeypatch.setattr(kyobo, "search_products",
                        lambda s, kw, selling: asked["search"].append((kw, selling)) or ky_rows())
    monkeypatch.setattr(kyobo, "list_documents", lambda s, p, on: asked["docs"].append(p.seq) or ky_docs(p))
    monkeypatch.setattr(kyobo, "download",
                        lambda s, doc: asked["get"].append(doc.file_name) or b"%PDF-1.7\n" + doc.file_name.encode())
    out = tmp_path / "out"

    def run(*argv):
        monkeypatch.setattr(sys, "argv", ["fetch_disclosure.py", "--org", "kyobo", "--out", str(out),
                                          "--targets", str(PATH), *argv])
        return fd.main()

    return {"run": run, "asked": asked, "out": out}


def test_fetch_list_only_reads_the_kyobo_targets(bench, capsys):
    assert bench["run"]("--list-only") == 0
    printed = capsys.readouterr().out
    for code, name in (("1001031", "가나플랜건강보험Ⅱ"), ("1001042", "가나간편플랜건강보험Ⅱ")):
        for kind in ("사업방법서", "상품요약서"):
            assert f"| {code} | {name} | {kind} | {name} {kind}.pdf | | | |" in printed
    assert "약관" not in printed                     # 교보생명은 약관을 받지 않는다
    assert bench["asked"]["get"] == [] and bench["asked"]["docs"] == ["1", "3"]   # 중도부가특약 행은 고르지 않는다
    assert json.loads((bench["out"] / "index.json").read_text(encoding="utf-8")) == []


def test_fetched_index_feeds_the_variants_of_the_kyobo_targets(bench):
    assert bench["run"]() == 0
    index = json.loads((bench["out"] / "index.json").read_text(encoding="utf-8"))
    assert sorted((e["상품코드"], e["문서"]) for e in index) == [
        ("1001031", "사업방법서"), ("1001031", "상품요약서"), ("1001042", "사업방법서"), ("1001042", "상품요약서")]
    assert {e["저장이름"] for e in index} == {f"kyobo_{c}_{k}" for c in codes() for k in ("사업방법서", "상품요약서")}
    found, problems = VV.build(TARGETS, index)
    assert problems == [] and len(found) == 7
    assert all(v.summary and v.summary["해시"] for v in found)
    assert {v.row["공시상품명"] for v in found} == {"가나플랜건강보험Ⅱ", "가나간편플랜건강보험Ⅱ"}
