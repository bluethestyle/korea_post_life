"""공시 문서 수집 스크립트(scripts/fetch_disclosure.py): 삼성화재 수집과, 우체국과 한화 호출이 전과 같은지.

네트워크와 pdfplumber 없이 돈다. PDF에서 글자를 뽑는 자리(pdf_pages)와 표의 선을 읽는 자리(tables.read_tables)만
손으로 만든 값으로 바꿔 끼운다. 쪽 범위 찾기, 조각 묶기, 종 거르기, JSON 쓰기는 실제 코드가 돈다.
공시 응답은 꼴만 본떴다. 상품코드, 상품명, 담보 이름, 문구는 지어낸 것이다.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from postlife.disclosure import epost, hanwha, samsungfire
from postlife.extract import tables, variants
from postlife.extract.segment import pages_from_text
from postlife.extract.tables import PageTable

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("fetch_disclosure", ROOT / "scripts/fetch_disclosure.py")
fd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fd)

A, B, OTHER, GONE = "ZZA000010", "ZZB000020", "ZZC000030", "ZZD000040"
NAME_A, NAME_B = "무배당 가나 건강보험(2610.1)(일반형)", "무배당 다라 간편보험(2607.5) 7종(마바형)"


def row(code, name, start, end="99991231", files=(1, 2, 3), jong="0", **more):
    return {"prdName": name, "prdGun": "장기", "prdGb": "건강", "saleChannel": "대면", "prdCode": code, "jongGb": jong,
            "saleStDt": start, "saleEnDt": end,
            **{f"prdfilename{n}": f"/publication/pdf/{code}_{jong}_{start}_file{n}.pdf" for n in files}, **more}


def listing(rows):
    return {"responseMessage": {"header": {"tranId": "VH.HDIF0103", "resultCode": "0000"},
                                "body": {"result": "S", "data": {"list": rows}}}}


LIST = listing([
    row(A, NAME_A, "20261012", files=(1, 2, 3, 4)),                       # 약관, 사업방법서, 상품요약서, 상품설명서
    row(A, "무배당 가나 건강보험(2608.9)(일반형)", "20260818", "20261011"),      # 같은 코드의 지난 판매기간
    row(B, "무배당 다라 간편보험(2604.1) 7종(마바형)", "20260401"),               # 종료일이 열린 채 남은 앞 기간
    row(B, NAME_B, "20260701"),
    row(OTHER, "무배당 사아 운전자보험(2610.1)", "20261012"),                  # 대상이 아닌 상품
    row(GONE, "무배당 자차 건강보험(2504.1)", "20250401", displayGb="2"),      # 판매중지 탭에 고정된 상품
])
# 한 코드에 종형이 여럿이어도 종 번호가 같으면 표 하나를 함께 쓴다
TARGETS = [
    {"모상품ID": "X_A", "종형": [{"공시상품코드": A, "종형명": "8종(일반형)"}]},
    {"모상품ID": "X_B", "종형": [{"공시상품코드": B, "종형명": "7종(마바형) 315·5"},
                               {"공시상품코드": B, "종형명": "7종(마바형) 325·5"}]},
]
METHOD_PAGES = ["가나 사업방법서\n1. 보험종목의 명칭", "2. 보험기간"]
SUMMARY_PAGES = [
    "가나 상품요약서\n□ 가입자격제한\n가. 7종(마바형)\n나. 8종(일반형)",
    "□ 보험금 지급사유 및 지급금액\n◆ 기본계약\n보장명 지급사유 지급금액\n가나 진단비 가나로 진단 확정된 경우 가입금액",
    "보장명 지급사유 지급금액\n마바 납입면제대상 마바로 납입면제사유가 발생한 경우\n□ 보험금 지급제한사항",
    "□ 보험료 구성",
]
# 종 구간마다 급부 절이 따로 있는 요약서
TWO_SECTIONS = ["1. 1종(가나형)", "□ 보험금 지급사유 및 지급금액\n보장명 지급사유 지급금액", "□ 보험금 지급제한사항",
                "2. 2종(다라형)\n□ 가입자격제한", "□ 보험금 지급사유 및 지급금액\n보장명 지급사유 지급금액",
                "□ 보험금 지급제한사항"]
HEAD = [["보장명", None, "", "지급금액"], [None, None, "지급사유", None], [None, None, "", None]]
TABLES = [
    PageTable(2, HEAD + [
        ["가나 진단비", None, "가나로 진단 확정된 경우", "가입금액"],
        ["다라 수술비", "다라 관혈 수술비", "다라로 관혈수술을 받은 경우", "가입금액"],
        [None, "다라 비관혈 수술비 \n*7종에 한함 ", "다라로 비관혈수술을 받은 경우", "가입금액의 20%"],
    ], "기본계약"),
    PageTable(3, HEAD + [
        ["마바 납입면제대상 \n*7종에 한함 ", None, "마바로 납입면제사유가 발생한 경우", "보험료 납입면제"],
    ], "선택계약"),
]


def path(code, start, n):
    return f"/publication/pdf/{code}_0_{start}_file{n}.pdf"


def pdf(doc_path):
    return b"%PDF-1.7\n" + doc_path.encode()


class Reply:
    encoding = None

    def __init__(self, content=b"", payload=None):
        self.content, self.payload = content, payload
        self.headers = {"Content-Type": "application/pdf" if content.startswith(b"%PDF") else "text/html"}

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    """목록 요청에는 payload를, 서류 요청에는 경로를 적어 넣은 가짜 PDF를 돌려준다. broken에 든 경로는 안내 화면이 온다."""

    def __init__(self, payload=LIST, broken=()):
        self.payload, self.broken = payload, set(broken)
        self.posts, self.gets = [], []

    def post(self, url, **kw):
        self.posts.append(url)
        return Reply(payload=self.payload)

    def get(self, url, **kw):
        doc_path = url.removeprefix(samsungfire.BASE)
        self.gets.append(doc_path)
        return Reply(b"<html>none</html>" if doc_path in self.broken else pdf(doc_path))


def write_targets(folder, products=TARGETS, name="targets.json"):
    target = folder / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"기관코드": "SAMSUNGFIRE", "상품": products}, ensure_ascii=False), encoding="utf-8")
    return target


@pytest.fixture
def bench(tmp_path, monkeypatch):
    """가짜 접속과 가짜 PDF 읽기를 끼워 main()을 돌린다. 작업 폴더는 빈 임시 폴더다."""
    b = SimpleNamespace(pages={"file2": METHOD_PAGES, "file3": SUMMARY_PAGES}, tables=TABLES, read=[],
                        out=tmp_path / "out", session=None)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)      # CI의 실행 요약에 시험 출력이 섞이지 않게 한다
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fd, "pdf_pages", lambda data: b.pages[data.decode().rsplit("_", 1)[-1][:5]])

    def read_tables(source, first, last):
        b.read.append((source, first, last))
        return [t for t in b.tables if first <= t.page <= last]

    monkeypatch.setattr(tables, "read_tables", read_tables)

    def run(*argv, session=None, targets=None):
        b.session = session or FakeSession()
        monkeypatch.setattr(fd, "session", lambda: b.session)
        monkeypatch.setattr(sys, "argv", ["fetch_disclosure.py", "--org", "samsungfire", "--out", str(b.out),
                                          "--targets", str(targets or write_targets(tmp_path)), *argv])
        return fd.main()

    b.run = run
    b.index = lambda: json.loads((b.out / "index.json").read_text(encoding="utf-8"))
    return b


# ---------------------------------------------------------------------------
# 삼성화재: 무엇을 받는가
# ---------------------------------------------------------------------------

def test_only_target_codes_are_fetched_and_terms_are_skipped(bench):
    assert bench.run() == 0
    # 목록은 한 번만 요청한다
    assert bench.session.posts == ["https://www.samsungfire.com/vh/data/VH.HDIF0103.do"]
    # 대상 코드의 지금 판매 중인 기간에서 사업방법서(file2)와 상품요약서(file3)만. 약관(file1)과 상품설명서(file4)는 받지 않는다.
    # 판매 중인 기간이 둘로 오면 개시일이 늦은 쪽을 고른다
    assert bench.session.gets == [path(A, "20261012", 2), path(A, "20261012", 3),
                                  path(B, "20260701", 2), path(B, "20260701", 3)]
    assert sorted(p.name for p in bench.out.iterdir()) == sorted(
        ["index.json"] + [f"samsungfire_{code}_{kind}" for code in (A, B)
                          for kind in ("사업방법서.pdf", "사업방법서.txt", "상품요약서.pdf", "상품요약서.txt", "급부표.json")])


def test_codes_of_several_variants_are_fetched_once(bench):
    bench.run()
    assert [e["상품코드"] for e in bench.index()].count(B) == 2       # 종형이 둘이어도 문서는 한 벌


def test_list_only_downloads_nothing(bench, capsys):
    assert bench.run("--list-only") == 0
    assert len(bench.session.posts) == 1 and bench.session.gets == []
    assert bench.index() == [] and [p.name for p in bench.out.iterdir()] == ["index.json"]
    printed = capsys.readouterr().out
    assert f"| {A} | {NAME_A} | 사업방법서 | {A}_0_20261012_file2.pdf | | |" in printed
    assert f"| {B} | {NAME_B} | 상품요약서 | {B}_0_20260701_file3.pdf | | |" in printed
    assert "file1" not in printed and "file4" not in printed and OTHER not in printed
    assert "20260818" not in printed and "20260401" not in printed          # 지난 판매기간의 서류


def test_old_style_jong_rows_of_a_target_code_are_not_picked(bench):
    # 옛 상품처럼 같은 코드에 종 구분 1이 붙은 판매기간이 판매개시일이 더 늦게 섞여 와도 종 구분 0의 기간을 고른다
    rows = [row(A, NAME_A, "20261012", files=(1, 2, 3, 4)), row(A, "무배당 가나 건강보험(구형 1종)", "20261101", jong="1"),
            row(B, NAME_B, "20260701")]
    assert bench.run(session=FakeSession(listing(rows))) == 0
    assert bench.session.gets == [path(A, "20261012", 2), path(A, "20261012", 3),
                                  path(B, "20260701", 2), path(B, "20260701", 3)]
    assert {(e["상품명"], e["판매시작일"]) for e in bench.index() if e["상품코드"] == A} == {(NAME_A, "2026-10-12")}


def test_code_missing_from_the_selling_list_fails_but_the_rest_is_kept(bench, tmp_path, capsys):
    gone = [{"모상품ID": "X_D", "종형": [{"공시상품코드": GONE, "종형명": "8종(일반형)"}]}]
    assert bench.run(targets=write_targets(tmp_path, TARGETS + gone)) == 1
    assert {e["상품코드"] for e in bench.index()} == {A, B}
    printed = capsys.readouterr().out
    assert f"| {GONE} | (판매상품 목록에 없음) | | | | |" in printed
    assert printed.splitlines()[-1] == f"갖추지 못한 상품: {GONE}(사업방법서, 상품요약서, 급부표)"
    # 내려받지 않는 --list-only는 목록만 보여 주고 성공으로 끝난다
    assert bench.run("--list-only", targets=write_targets(tmp_path, TARGETS + gone)) == 0


# ---------------------------------------------------------------------------
# 삼성화재: 저장하는 것
# ---------------------------------------------------------------------------

def run_hanwha(bench, monkeypatch, tmp_path, *argv):
    """가짜 한화 공시실로 한화 경로를 돌린다. 대상 설정은 작업 폴더의 data/targets/hanwha.json이다."""
    docs = [hanwha.Document("9001", kind, f"가나 통합보험_{kind}_20261001.pdf", "2026-10-01", None)
            for kind in ("상품요약서", "사업방법서", "약관")]
    monkeypatch.setattr(hanwha, "list_products", lambda s, selling=True: [
        hanwha.Product("9001", "가나 통합보험 무배당", True, "개인 보장성")])
    monkeypatch.setattr(hanwha, "list_documents", lambda s, code: docs if code == "9001" else [])
    monkeypatch.setattr(hanwha, "download", lambda s, doc: b"%PDF-1.7\n" + doc.kind.encode())
    monkeypatch.setattr(fd, "pdf_pages", lambda data: ["첫 쪽", "둘째 쪽"])
    monkeypatch.setattr(fd, "session", lambda: object())
    write_targets(tmp_path, [{"종형": [{"공시상품코드": "9001"}, {"공시상품코드": "9001"}, {"공시상품코드": "9002"}]}],
                  "data/targets/hanwha.json")
    monkeypatch.setattr(sys, "argv", ["fetch_disclosure.py", *argv])
    return fd.main()


def test_index_entries_have_the_same_shape_as_hanwha(bench, monkeypatch, tmp_path):
    assert bench.run() == 0
    index = bench.index()
    assert [(e["상품코드"], e["문서"]) for e in index] == [(A, "사업방법서"), (A, "상품요약서"), (B, "사업방법서"), (B, "상품요약서")]
    data = pdf(path(A, "20261012", 2))
    assert index[0] == {
        "기관": "SAMSUNGFIRE", "상품코드": A, "상품명": NAME_A, "판매시작일": "2026-10-12", "판매종료일": None,
        "문서": "사업방법서", "파일": f"{A}_0_20261012_file2.pdf", "등록일": "2026-10-12",
        "쪽수": 2, "해시": hashlib.sha256(data).hexdigest()[:16], "저장이름": f"samsungfire_{A}_사업방법서"}
    # PDF는 받은 그대로, 글자 파일은 쪽 구분선과 함께
    assert (bench.out / f"samsungfire_{A}_사업방법서.pdf").read_bytes() == data
    text = (bench.out / f"samsungfire_{A}_사업방법서.txt").read_text(encoding="utf-8")
    assert text == "\n===== 1쪽 =====\n가나 사업방법서\n1. 보험종목의 명칭\n\n===== 2쪽 =====\n2. 보험기간"
    assert sorted(pages_from_text((bench.out / f"samsungfire_{B}_상품요약서.txt").read_text(encoding="utf-8"))) == [1, 2, 3, 4]
    # 요약서 항목에는 표 조각의 파일 이름, 조각 수, 세부보장 수, 쪽 범위가 더 붙는다
    assert {k: v for k, v in index[1].items() if k not in index[0]} == {
        "급부표": f"samsungfire_{A}_급부표.json", "급부표조각수": 2, "급부표세부보장수": 2, "급부표쪽": [2, 3]}
    assert (index[3]["급부표조각수"], index[3]["급부표세부보장수"]) == (3, 4)

    # 한화 항목과 열쇠가 같다
    assert run_hanwha(bench, monkeypatch, tmp_path, "--out", str(tmp_path / "h"), "--org", "hanwha") == 0
    like = json.loads((tmp_path / "h/index.json").read_text(encoding="utf-8"))
    assert list(like[0]) == list(index[0])


def test_step_summary_gets_a_table_like_the_other_companies(bench, monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    bench.run()
    lines = (tmp_path / "summary.md").read_text(encoding="utf-8").split("\n")
    assert lines[:4] == ["## 공시 문서 수집 (삼성화재)", "", "| 상품코드 | 상품명 | 문서 | 파일 | 쪽수 | 크기 |",
                         "| --- | --- | --- | --- | --- | --- |"]
    size = len(pdf(path(A, "20261012", 3)))
    assert lines[4:7] == [
        f"| {A} | {NAME_A} | 사업방법서 | {A}_0_20261012_file2.pdf | 2 | {size:,} |",
        f"| {A} | {NAME_A} | 상품요약서 | {A}_0_20261012_file3.pdf | 4 | {size:,} |",
        f"| {A} | {NAME_A} | 급부표 | samsungfire_{A}_급부표.json | 2~3 | 조각 2, 세부보장 2 |"]


def test_one_failed_document_does_not_stop_the_rest(bench, capsys):
    # 사업방법서 하나가 PDF가 아닌 응답으로 와도 나머지 셋을 받는다. 표 조각은 다 만들었어도 서류가 빠졌으므로 실패다
    assert bench.run(session=FakeSession(broken=[path(A, "20261012", 2)])) == 1
    assert len(bench.session.gets) == 4
    assert [(e["상품코드"], e["문서"]) for e in bench.index()] == [(A, "상품요약서"), (B, "사업방법서"), (B, "상품요약서")]
    printed = capsys.readouterr().out
    assert f"| {A} | {NAME_A} | 사업방법서 | {A}_0_20261012_file2.pdf | 실패: ValueError | |" in printed
    assert printed.splitlines()[-1] == f"갖추지 못한 상품: {A}(사업방법서)"
    assert not (bench.out / f"samsungfire_{A}_사업방법서.pdf").exists()
    assert (bench.out / f"samsungfire_{A}_급부표.json").exists()


@pytest.mark.parametrize("n, other, missing", [(2, "상품요약서", "사업방법서"), (3, "사업방법서", "상품요약서, 급부표")])
def test_document_without_a_path_in_the_listing_fails_but_the_rest_is_fetched(bench, capsys, n, other, missing):
    # 공시 목록에서 대상 코드의 서류 경로(prdfilenameN)가 빈 값으로 온 경우
    rows = [row(A, NAME_A, "20261012", files=(1, 2, 3, 4), **{f"prdfilename{n}": ""}), row(B, NAME_B, "20260701")]
    assert bench.run(session=FakeSession(listing(rows))) == 1
    assert bench.session.gets == [path(A, "20261012", 5 - n), path(B, "20260701", 2), path(B, "20260701", 3)]
    assert [(e["상품코드"], e["문서"]) for e in bench.index()] == [(A, other), (B, "사업방법서"), (B, "상품요약서")]
    printed = capsys.readouterr().out
    assert f"| {A} | {NAME_A} | {samsungfire.DOC_KINDS[n]} | (공시 목록에 서류 경로 없음) | | |" in printed
    assert printed.splitlines()[-1] == f"갖추지 못한 상품: {A}({missing})"
    # 내려받지 않는 --list-only는 지금처럼 성공으로 끝난다
    assert bench.run("--list-only", session=FakeSession(listing(rows))) == 0


def test_failed_summary_leaves_its_code_without_a_table(bench):
    assert bench.run(session=FakeSession(broken=[path(A, "20261012", 3)])) == 1
    assert [(e["상품코드"], e["문서"]) for e in bench.index()] == [(A, "사업방법서"), (B, "사업방법서"), (B, "상품요약서")]
    assert (bench.out / f"samsungfire_{B}_급부표.json").exists()


def test_rerun_into_the_same_folder_drops_tables_it_did_not_make_again(bench, tmp_path):
    assert bench.run() == 0 and (bench.out / f"samsungfire_{A}_급부표.json").exists()
    # 목록만 보는 실행은 이전 표를 지우지 않는다
    assert bench.run("--list-only") == 0 and (bench.out / f"samsungfire_{A}_급부표.json").exists()
    # 지금은 판매 목록에 없는 코드의 표가 그보다 앞선 실행에서 남아 있다고 친다
    (bench.out / f"samsungfire_{GONE}_급부표.json").write_text("{}", encoding="utf-8")
    gone = [{"종형": [{"공시상품코드": GONE, "종형명": "8종(일반형)"}]}]
    assert bench.run(session=FakeSession(broken=[path(A, "20261012", 3)]), targets=write_targets(tmp_path, TARGETS + gone)) == 1
    assert [e.get("급부표") for e in bench.index()] == [None, None, f"samsungfire_{B}_급부표.json"]
    assert sorted(p.name for p in bench.out.glob("*급부표.json")) == [f"samsungfire_{B}_급부표.json"]


# ---------------------------------------------------------------------------
# 삼성화재: 급부 표 조각
# ---------------------------------------------------------------------------

def test_table_json_is_read_back_and_filtered_by_variant(bench):
    bench.run()
    # 표는 받은 PDF에서, 글자 파일에서 찾은 급부 절의 쪽 범위만 읽는다
    assert bench.read == [(pdf(path(A, "20261012", 3)), 2, 3), (pdf(path(B, "20260701", 3)), 2, 3)]

    eight = tables.read_riders(bench.out / f"samsungfire_{A}_급부표.json")
    assert [(r.title, r.label, [c.name for c in r.covers]) for r in eight] == [
        ("가나 진단비", "기본계약", ["가나 진단비"]), ("다라 수술비", "기본계약", ["다라 관혈 수술비"])]   # "7종에 한함"은 빠진다
    seven = tables.read_riders(bench.out / f"samsungfire_{B}_급부표.json")
    assert [(r.title, r.only, [(c.name, c.only) for c in r.covers]) for r in seven] == [
        ("가나 진단비", "", [("가나 진단비", "")]),
        ("다라 수술비", "", [("다라 관혈 수술비", ""), ("다라 비관혈 수술비", "7종에 한함")]),
        ("마바 납입면제대상", "7종에 한함", [("마바 납입면제대상", "")])]
    assert seven == tables.for_variant(tables.riders_from_tables(TABLES), "7종(마바형) 325·5")
    assert (seven[2].first_page, seven[2].covers[0].reason, seven[2].covers[0].amount) == (
        3, "마바로 납입면제사유가 발생한 경우", "보험료 납입면제")

    source = json.loads((bench.out / f"samsungfire_{B}_급부표.json").read_text(encoding="utf-8"))["출처"]
    assert source == {"문서": f"samsungfire_{B}_상품요약서", "쪽": [2, 3], "구간": "",
                      "종": "7종(마바형) 315·5, 7종(마바형) 325·5"}


def test_table_failure_keeps_documents_and_index_but_exits_nonzero(bench, capsys):
    bench.pages["file3"] = ["가나 상품요약서", "□ 보험료 구성"]           # 급부 절이 없는 요약서
    assert bench.run() == 1
    index = bench.index()
    assert [(e["상품코드"], e["문서"], e["쪽수"]) for e in index] == [
        (A, "사업방법서", 2), (A, "상품요약서", 2), (B, "사업방법서", 2), (B, "상품요약서", 2)]
    assert not any("급부표" in e for e in index)
    assert (bench.out / f"samsungfire_{A}_상품요약서.pdf").exists() and not list(bench.out.glob("*급부표.json"))
    printed = capsys.readouterr().out
    assert f"| {A} | {NAME_A} | 급부표 | samsungfire_{A}_급부표.json | 실패: ValueError | |" in printed
    assert printed.splitlines()[-1] == f"갖추지 못한 상품: {A}(급부표), {B}(급부표)"


def test_one_missing_table_is_enough_to_fail(bench, monkeypatch):
    def read_tables(source, first, last):
        if B.encode() in source:
            raise RuntimeError("표의 선을 읽지 못함")
        return TABLES

    monkeypatch.setattr(tables, "read_tables", read_tables)
    assert bench.run() == 1
    assert ["급부표" in e for e in bench.index()] == [False, True, False, False]
    assert len(tables.read_riders(bench.out / f"samsungfire_{A}_급부표.json")) == 2


def test_empty_table_is_a_failure(bench):
    bench.tables = []               # 급부 절은 있는데 급부 표를 하나도 읽지 못함
    assert bench.run() == 1 and len(bench.index()) == 4


def test_section_title_in_targets_picks_one_of_several_benefit_sections(bench, tmp_path):
    bench.pages["file3"] = TWO_SECTIONS
    bench.tables = [PageTable(5, HEAD + [["사아 진단비", None, "사아로 진단 확정된 경우", "가입금액"]], "기본계약")]
    products = [{"종형": [{"공시상품코드": A, "종형명": "2종(다라형)"}]}]
    # 급부 절이 두 곳인데 구간 제목이 없으면 고르지 못한다
    assert bench.run(targets=write_targets(tmp_path, products)) == 1 and bench.read == []
    products[0]["종형"][0]["급부구간"] = "2. 2종(다라형)"
    assert bench.run(targets=write_targets(tmp_path, products)) == 0
    assert [(first, last) for _, first, last in bench.read] == [(5, 6)]
    table = json.loads((bench.out / f"samsungfire_{A}_급부표.json").read_text(encoding="utf-8"))
    assert table["출처"]["구간"] == "2. 2종(다라형)" and bench.index()[1]["급부표쪽"] == [5, 6]
    # 한 코드의 종형에 구간 제목이 서로 다르게 적혀 있으면 표를 만들지 않는다
    products[0]["종형"].append({"공시상품코드": A, "종형명": "2종(다라형) 둘째", "급부구간": "1. 1종(가나형)"})
    assert bench.run(targets=write_targets(tmp_path, products)) == 1


def test_section_title_on_only_some_variants_of_a_code_is_a_mismatch(bench, tmp_path, capsys):
    bench.pages["file3"] = TWO_SECTIONS
    bench.tables = [PageTable(5, HEAD + [["사아 진단비", None, "사아로 진단 확정된 경우", "가입금액"]], "기본계약")]
    # 한 종형에만 구간 제목이 있고 다른 종형은 비어 있으면, 적힌 구간의 표를 모든 종형에 쓰지 않는다
    products = [{"종형": [{"공시상품코드": A, "종형명": "2종(다라형)", "급부구간": "2. 2종(다라형)"},
                         {"공시상품코드": A, "종형명": "2종(다라형) 둘째", "급부구간": ""}]}]
    assert bench.run(targets=write_targets(tmp_path, products)) == 1
    assert bench.read == [] and not list(bench.out.glob("*급부표.json"))
    printed = capsys.readouterr().out
    assert f"| {A} | {NAME_A} | 급부표 | samsungfire_{A}_급부표.json | 실패: ValueError | |" in printed
    assert "급부구간이 다르게 적혀 있습니다" in printed
    # 열쇠가 아예 없는 종형도 빈 값과 같다
    del products[0]["종형"][1]["급부구간"]
    assert bench.run(targets=write_targets(tmp_path, products)) == 1 and bench.read == []


def test_variants_of_one_code_must_keep_the_same_lines(bench, tmp_path):
    products = [{"종형": [{"공시상품코드": A, "종형명": "7종(마바형)"}, {"공시상품코드": A, "종형명": "8종(일반형)"}]}]
    assert bench.run(targets=write_targets(tmp_path, products)) == 1
    assert len(bench.index()) == 2 and not list(bench.out.glob("*급부표.json"))


def test_real_targets_file_gives_one_table_per_code_and_variants_accept_the_index(bench):
    """저장소의 대상 설정(data/targets/samsungfire.json)으로 수집한 결과를 종형 만들기가 그대로 받는다."""
    real = ROOT / "data/targets/samsungfire.json"
    targets = json.loads(real.read_text(encoding="utf-8"))
    codes = sorted({v["공시상품코드"] for product in targets["상품"] for v in product["종형"]})
    session = FakeSession(listing([row(code, f"무배당 가나 보험 {i}", "20261012") for i, code in enumerate(codes)]))
    assert bench.run(session=session, targets=real) == 0
    index = bench.index()
    assert [e["상품코드"] for e in index if "급부표" in e] == codes
    found, problems = variants.build(targets, index)
    assert problems == [] and len(found) == sum(len(product["종형"]) for product in targets["상품"])
    assert all(v.summary["급부표"] == f"samsungfire_{v.row['공시상품코드']}_급부표.json" and v.method for v in found)
    assert all(v.row["요약서해시"] and v.row["사업방법서해시"] and v.row["적용시작일"] == "2026-10-12" for v in found)


# ---------------------------------------------------------------------------
# --targets 기본값과 기존 호출
# ---------------------------------------------------------------------------

def test_targets_default_follows_the_company(bench, monkeypatch, tmp_path):
    # --org samsungfire는 작업 폴더의 data/targets/samsungfire.json을 읽는다
    write_targets(tmp_path, TARGETS[:1], "data/targets/samsungfire.json")
    monkeypatch.setattr(fd, "session", FakeSession)
    monkeypatch.setattr(sys, "argv", ["fetch_disclosure.py", "--out", "out", "--org", "samsungfire"])
    assert fd.main() == 0
    assert {e["상품코드"] for e in bench.index()} == {A}
    # --targets를 직접 주면 그 파일을 읽는다
    other = write_targets(tmp_path, TARGETS[1:], "other.json")
    monkeypatch.setattr(sys, "argv", ["fetch_disclosure.py", "--out", "out", "--org", "samsungfire", "--targets", str(other)])
    assert fd.main() == 0
    assert {e["상품코드"] for e in bench.index()} == {B}


def test_hanwha_calls_are_unchanged(bench, monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(fd, "fetch_samsungfire", lambda *a: called.append(a))
    # 기본 대상 설정은 전과 같이 data/targets/hanwha.json이다
    assert run_hanwha(bench, monkeypatch, tmp_path, "--out", "out", "--org", "hanwha") == 0
    data = b"%PDF-1.7\n" + "상품요약서".encode()
    assert bench.index() == [
        {"기관": "HANWHALIFE", "상품코드": "9001", "상품명": "가나 통합보험 무배당", "판매시작일": "2026-10-01",
         "판매종료일": None, "문서": kind, "파일": f"가나 통합보험_{kind}_20261001.pdf", "등록일": "2026-10-01",
         "쪽수": 2, "해시": hashlib.sha256(b"%PDF-1.7\n" + kind.encode()).hexdigest()[:16], "저장이름": f"hanwha_9001_{kind}"}
        for kind in ("상품요약서", "사업방법서")]
    assert sorted(p.name for p in bench.out.iterdir()) == [
        "hanwha_9001_사업방법서.pdf", "hanwha_9001_사업방법서.txt", "hanwha_9001_상품요약서.pdf", "hanwha_9001_상품요약서.txt",
        "index.json"]
    assert (bench.out / "hanwha_9001_상품요약서.pdf").read_bytes() == data
    # 한화는 표 조각을 만들지 않는다
    assert bench.read == [] and called == []

    # --targets를 직접 준 호출
    other = write_targets(tmp_path, [{"종형": [{"공시상품코드": "9002"}]}], "other.json")
    assert run_hanwha(bench, monkeypatch, tmp_path, "--out", "out", "--org", "hanwha", "--targets", str(other)) == 1
    assert bench.index() == []
    assert run_hanwha(bench, monkeypatch, tmp_path, "--out", "out", "--org", "hanwha", "--targets", str(other),
                      "--list-only") == 0


@pytest.mark.parametrize("argv", [[], ["--out", "out", "--org", "epost"]])
def test_epost_calls_are_unchanged(bench, monkeypatch, tmp_path, argv):
    products = [epost.Product("P900001", "무배당 우체국통합건강보험 2504 가나형", "2025-04-03", None),
                epost.Product("P900002", "무배당 우체국다라보험 2601", "2026-01-02", None)]       # 비교 대상이 아닌 상품
    asked = []

    def list_documents(s, code, on):
        asked.append(code)
        return [epost.Document(code, "상품요약서", f"yoyak_{code}.pdf", f"/dat_docs/04/yoyak_{code}.pdf", "2025-04-01")]

    monkeypatch.setattr(epost, "list_products", lambda s, selling=True: products if selling else [])
    monkeypatch.setattr(epost, "list_documents", list_documents)
    monkeypatch.setattr(epost, "download", lambda s, doc: b"%PDF-1.7\n" + doc.path.encode())
    monkeypatch.setattr(fd, "pdf_pages", lambda data: ["첫 쪽"])
    monkeypatch.setattr(fd, "session", lambda: object())
    called = []
    monkeypatch.setattr(fd, "fetch_hanwha", lambda *a: called.append(a))
    monkeypatch.setattr(fd, "fetch_samsungfire", lambda *a: called.append(a))
    monkeypatch.setattr(sys, "argv", ["fetch_disclosure.py", *argv])
    assert fd.main() == 0
    # 인자 없이 부르면 우체국을 작업 폴더의 out에 받는다. 대상 설정 파일은 읽지 않는다
    assert called == [] and asked == ["P900001"] and not (tmp_path / "data").exists()
    data = b"%PDF-1.7\n/dat_docs/04/yoyak_P900001.pdf"
    assert json.loads((tmp_path / "out/index.json").read_text(encoding="utf-8")) == [
        {"기관": "EPOST", "상품코드": "P900001", "상품명": "무배당 우체국통합건강보험 2504 가나형", "판매시작일": "2025-04-03",
         "판매종료일": None, "문서": "상품요약서", "파일": "yoyak_P900001.pdf", "등록일": "2025-04-01",
         "쪽수": 1, "해시": hashlib.sha256(data).hexdigest()[:16], "저장이름": "yoyak_P900001"}]
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        "epost_products.json", "index.json", "yoyak_P900001.pdf", "yoyak_P900001.txt"]
    assert (tmp_path / "out/yoyak_P900001.txt").read_text(encoding="utf-8") == "\n===== 1쪽 =====\n첫 쪽"
