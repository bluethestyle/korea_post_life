"""공시 문서 수집 스크립트의 초기 적재 회사 경로(--org meritz 등, postlife.disclosure.sources).

네트워크와 pdfplumber 없이 돈다. 메리츠화재 공시실은 응답의 꼴만 본뜬 가짜 세션으로 바꾸고, 접속 모듈(meritz.py)의
요청 만들기와 응답 읽기는 실제 코드가 돈다. 상품코드, 상품명, 파일 경로, 암호값은 지어낸 것이다.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from postlife.config import INSTITUTIONS
from postlife.disclosure import meritz, sources

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("fetch_disclosure_src", ROOT / "scripts/fetch_disclosure.py")
fd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fd)

A, B, GONE = "9ZZAA", "9ZZBB", "9ZZXX"
NAME_A, NAME_B = "무배당 가나보장보험2610", "무배당 다라간편보험2610(간편심사형)"
OK = {"prcesResultDivCd": "0", "encryDivCd": "0"}


def period_row(seq, name, start, end="-", files=(1, 2, 3), tag=""):
    r = {"ntbdDtlSeq": seq, "ttlNm": name, "putupStDdTm": start, "putupEdDdTm": end, "bgnDt": start}
    for n in files:
        r[f"file{n}"] = f"/cu/zz/{seq}{n}{tag}U.pdf"
        r[f"file{n}#[E]"] = f"tok-{seq}-{n}"
    return r


# 상품코드별 판매기간 목록. A는 닫힌 지난 기간과 열린 지금 기간, B는 열린 기간 하나, GONE은 판매기간이 없다
PERIODS = {
    A: [period_row(500, NAME_A.replace("2610", "2607"), "20260701", "20261030"), period_row(510, NAME_A, "20261031")],
    B: [period_row(520, NAME_B, "20261031")],
    GONE: [],
}


class Reply:
    encoding = None

    def __init__(self, content=b"", payload=None, ctype="application/json"):
        self.content, self.payload, self.headers = content, payload, {"Content-Type": ctype}

    def raise_for_status(self):
        pass

    def json(self):
        if self.payload is None:
            raise ValueError("JSON이 아님")
        return self.payload


class FakeMeritz:
    """json.smart 조회에는 상품코드별 판매기간을, 내려받기 확인에는 빈 resultMsg를, 내려받기에는 암호값을 적은 PDF를 준다.

    blocked에 든 암호값은 방화벽 차단 화면(상태 200, text/html)이 온다.
    """

    def __init__(self, periods=PERIODS, blocked=()):
        self.periods, self.blocked = periods, set(blocked)
        self.asked, self.checked, self.got = [], [], []

    def post(self, url, data=None, headers=None, timeout=None):
        if url.startswith(meritz.SERVICE):
            sent = json.loads(data)
            code = sent["body"]["nwPdCd"]
            self.asked.append((sent["header"]["rcvmsgSrvId"].rsplit(".", 1)[-1], sent["body"]["notfYn"], code))
            return Reply(payload={"msg": {}, "header": OK, "body": {"salPdList": self.periods.get(code, [])}})
        assert url == meritz.DOWNLOAD
        self.checked.append(data["path"])
        if data["path"] in self.blocked:
            return Reply(b"<center><h2>blocked</h2></center>", ctype="text/html")
        return Reply(payload={"resultMsg": ""})

    def get(self, url, params=None, headers=None, timeout=None):
        assert url == meritz.DOWNLOAD and params["check"] == "N"
        self.got.append(params["path"])
        return Reply(pdf(params["path"]), ctype="application/octet-stream")


def pdf(token):
    return b"%PDF-1.7\n" + token.encode()


def write_targets(folder, codes=(A, B), name="targets.json"):
    target = folder / name
    target.parent.mkdir(parents=True, exist_ok=True)
    products = [{"모상품ID": f"X_{c}", "종형": [{"공시상품코드": c, "종형명": "1종"}]} for c in codes]
    target.write_text(json.dumps({"기관코드": "MERITZ", "상품": products}, ensure_ascii=False), encoding="utf-8")
    return target


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fd, "pdf_pages", lambda data: ["첫 쪽", "둘째 쪽"])
    waits = []
    monkeypatch.setattr(fd, "pause", waits.append)
    state = {"waits": waits, "out": tmp_path / "out"}

    def go(*argv, session=None, targets=None, org="meritz"):
        state["session"] = session or FakeMeritz()
        monkeypatch.setattr(fd, "session", lambda: state["session"])
        args = ["fetch_disclosure.py", "--org", org, "--out", str(state["out"])]
        if targets is not False:
            args += ["--targets", str(targets or write_targets(tmp_path))]
        monkeypatch.setattr(sys, "argv", args + list(argv))
        return fd.main()

    state["go"] = go
    state["index"] = lambda: json.loads((state["out"] / "index.json").read_text(encoding="utf-8"))
    return state


# ---------------------------------------------------------------------------
# 회사 열쇠와 접속 모듈을 잇는 자리
# ---------------------------------------------------------------------------

def test_registry_keys_are_cli_choices_and_known_institutions():
    assert "meritz" in sources.SOURCES
    for key, src in sources.SOURCES.items():
        # 기관코드가 아직 config에 없는 회사는 sources.PENDING_ORGS의 임시 열쇠를 쓴다
        assert src.key == key and (src.org in INSTITUTIONS or src.org in sources.PENDING_ORGS)
        assert src.targets == f"data/targets/{key}.json"
        assert src.kinds == ("사업방법서", "상품요약서") and src.pause > 0
    # 기존 세 회사의 열쇠와 겹치지 않는다
    assert not {"epost", "hanwha", "samsungfire"} & set(sources.SOURCES)


def test_workflow_offers_every_registered_company():
    text = (ROOT / ".github/workflows/fetch-disclosure.yml").read_text(encoding="utf-8")
    options = next(line for line in text.splitlines() if line.strip().startswith("options:"))
    assert all(key in options for key in ("epost", "hanwha", "samsungfire", *sources.SOURCES))


# ---------------------------------------------------------------------------
# 메리츠화재: 무엇을 받는가
# ---------------------------------------------------------------------------

def test_meritz_fetches_method_and_summary_of_the_open_period(run):
    assert run["go"]() == 0
    s = run["session"]
    # 상품코드마다 판매상품 탭으로 한 번 조회한다
    assert s.asked == [("retrieveSalPdListForCdNm", "Y", A), ("retrieveSalPdListForCdNm", "Y", B)]
    # 지금 판매 중인 기간(510, 520)의 사업방법서(file2)와 상품요약서(file3)만, 목록과 같은 세션의 암호값으로 받는다
    want = ["tok-510-2", "tok-510-3", "tok-520-2", "tok-520-3"]
    assert s.checked == want and s.got == want
    assert sorted(p.name for p in run["out"].iterdir()) == sorted(
        ["index.json"] + [f"meritz_{c}_{k}.{ext}" for c in (A, B) for k in ("사업방법서", "상품요약서") for ext in ("pdf", "txt")])
    assert (run["out"] / f"meritz_{A}_상품요약서.pdf").read_bytes() == pdf("tok-510-3")
    # 요청(조회 둘, 내려받기 넷) 사이마다 쉰다. 첫 요청 앞에서는 쉬지 않는다
    assert run["waits"] == [sources.SOURCES["meritz"].pause] * 5


def test_meritz_index_has_the_shared_keys_and_a_full_sha256(run, capsys):
    run["go"]()
    index = run["index"]()
    assert [(e["상품코드"], e["문서"]) for e in index] == [(A, "사업방법서"), (A, "상품요약서"), (B, "사업방법서"), (B, "상품요약서")]
    data = pdf("tok-510-2")
    assert index[0] == {
        "기관": "MERITZ", "상품코드": A, "상품명": NAME_A, "판매시작일": "2026-10-31", "판매종료일": None,
        "문서": "사업방법서", "파일": "5102U.pdf", "등록일": "2026-10-31", "쪽수": 2,
        "해시": hashlib.sha256(data).hexdigest()[:16], "저장이름": f"meritz_{A}_사업방법서",
        "sha256": hashlib.sha256(data).hexdigest()}
    printed = capsys.readouterr().out.splitlines()
    assert printed[:2] == ["| 상품코드 | 상품명 | 문서 | 파일 | 쪽수 | 크기 | sha256 |",
                           "| --- | --- | --- | --- | --- | --- | --- |"]
    assert printed[2] == f"| {A} | {NAME_A} | 사업방법서 | 5102U.pdf | 2 | {len(data):,} | {hashlib.sha256(data).hexdigest()} |"


def test_meritz_list_only_downloads_nothing(run, capsys):
    assert run["go"]("--list-only") == 0
    assert run["session"].checked == [] and run["session"].got == []
    assert run["index"]() == [] and [p.name for p in run["out"].iterdir()] == ["index.json"]
    printed = capsys.readouterr().out
    assert f"| {B} | {NAME_B} | 상품요약서 | 5203U.pdf | | | |" in printed
    assert "5101U" not in printed and "500" not in printed          # 약관과 지난 판매기간의 서류


def test_meritz_code_without_a_selling_period_fails_but_the_rest_is_kept(run, tmp_path, capsys):
    assert run["go"](targets=write_targets(tmp_path, (A, B, GONE))) == 1
    assert {e["상품코드"] for e in run["index"]()} == {A, B}
    printed = capsys.readouterr().out
    assert f"| {GONE} | (판매상품 목록에 없음) | | | | | |" in printed
    assert printed.splitlines()[-1] == f"갖추지 못한 상품: {GONE}(사업방법서, 상품요약서)"
    assert run["go"]("--list-only", targets=write_targets(tmp_path, (A, B, GONE))) == 0


def test_meritz_blocked_download_does_not_stop_the_rest(run, capsys):
    assert run["go"](session=FakeMeritz(blocked=["tok-510-2"])) == 1
    assert len(run["session"].checked) == 4 and len(run["session"].got) == 3
    assert [(e["상품코드"], e["문서"]) for e in run["index"]()] == [(A, "상품요약서"), (B, "사업방법서"), (B, "상품요약서")]
    printed = capsys.readouterr().out
    assert f"| {A} | {NAME_A} | 사업방법서 | 5102U.pdf | 실패: ValueError | | |" in printed
    assert printed.splitlines()[-1] == f"갖추지 못한 상품: {A}(사업방법서)"
    assert not (run["out"] / f"meritz_{A}_사업방법서.pdf").exists()


def test_meritz_period_without_a_summary_is_reported(run):
    periods = {**PERIODS, B: [period_row(520, NAME_B, "20261031", files=(1, 2))]}
    assert run["go"](session=FakeMeritz(periods)) == 1
    assert [(e["상품코드"], e["문서"]) for e in run["index"]()] == [(A, "사업방법서"), (A, "상품요약서"), (B, "사업방법서")]


def test_meritz_targets_default_and_step_summary(run, tmp_path, monkeypatch):
    write_targets(tmp_path, (B,), "data/targets/meritz.json")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    assert run["go"](targets=False) == 0
    assert {e["상품코드"] for e in run["index"]()} == {B}
    lines = (tmp_path / "summary.md").read_text(encoding="utf-8").split("\n")
    assert lines[:3] == ["## 공시 문서 수집 (메리츠화재)", "", "| 상품코드 | 상품명 | 문서 | 파일 | 쪽수 | 크기 | sha256 |"]


def test_other_companies_do_not_go_through_the_registry(run, monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(fd, "fetch_source", lambda *a: called.append(a))
    monkeypatch.setattr(fd, "fetch_samsungfire", lambda *a: ([], [], {}))
    assert run["go"]("--list-only", org="samsungfire") == 0 and called == []
