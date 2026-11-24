"""가상 사본(scripts/dev/make_synthetic_snapshot.py): 회사가 많을 때의 화면과 계산을 시험하는 자료.

실제 사본으로 가상 회사 둘(생명보험 하나, 손해보험 하나)을 더해 본다. 실제 회사 행은 그대로이고, 가상 회사의 이름은 한눈에
가짜이며 실제 회사 이름이 남지 않고, 탭 사이 이음이 끊기지 않고, 같은 입력이면 같은 결과가 나오는지 본다.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from postlife import config
from postlife.snapshot import read_snapshot
from postlife.site import sales as S
from postlife.site.model import load
from postlife.validate import check_rows

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "snapshot"
SCRIPT = ROOT / "scripts" / "dev" / "make_synthetic_snapshot.py"
SYN = ("SYNLIFE01", "SYNFIRE01")
ID_TABS = {"sys_상품종형": "종형ID", "sys_특약": "특약ID", "sys_급부": "급부ID", "hum_담보매핑": "급부ID",
           "sys_가입조건": "조건행ID", "sys_결합제약": "제약ID"}

pytestmark = pytest.mark.skipif(not (SNAPSHOT / "meta.json").exists(), reason="실제 사본(data/snapshot)이 없다")


def make(out: Path) -> None:
    run = subprocess.run([sys.executable, str(SCRIPT), "--out", str(out), "--life", "1", "--nonlife", "1"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stdout + run.stderr


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    out = tmp_path_factory.mktemp("synthetic") / "snap"
    make(out)
    return out


def is_syn(value) -> bool:
    return str(value).split("_", 1)[0] in SYN


def test_real_rows_are_untouched_and_names_are_fake(made):
    src, out = read_snapshot(SNAPSHOT), read_snapshot(made)
    for tab, rows in src.items():
        key = ID_TABS.get(tab)
        real = [r for r in out[tab] if not (key and is_syn(r[key]))]
        dump = lambda rs: sorted(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rs)  # noqa: E731
        assert dump(real) == dump(rows), tab
    meta = json.loads((made / "meta.json").read_text(encoding="utf-8"))
    assert meta["기관이름"] == {"SYNLIFE01": "가상생명 01", "SYNFIRE01": "가상화재 01"}
    assert meta["기관업권"] == {"SYNLIFE01": "생명보험", "SYNFIRE01": "손해보험"}
    assert meta["snapshot_at"] == json.loads((SNAPSHOT / "meta.json").read_text(encoding="utf-8"))["snapshot_at"]
    syn_variants = [v for v in out["sys_상품종형"] if v["기관코드"] in SYN]
    assert {v["기관코드"] for v in syn_variants} == set(SYN)
    assert all("가상" in v["공시상품명"] for v in syn_variants)
    words = list(config.ALL_ORGS.values()) + ["한화", "삼성", "시그니처", "새로고침", "THE FIT", "http"]
    for tab, key in ID_TABS.items():
        for r in out[tab]:
            if is_syn(r[key]):
                hit = [f"{k}={v}" for k, v in r.items() if isinstance(v, str) and any(w in v for w in words)]
                assert not hit, (tab, hit)
    assert not [r for r in out["sys_작업로그"] if is_syn(r.get("대상행ID") or "")]


def test_links_validation_and_variation(made):
    out = read_snapshot(made)
    for tab, rows in out.items():
        assert check_rows(tab, rows) == {}, tab
    vids = {v["종형ID"]: v for v in out["sys_상품종형"]}
    tids = {r["특약ID"]: r for r in out["sys_특약"]}
    bids = {b["급부ID"]: b for b in out["sys_급부"]}
    assert all(r["종형ID"] in vids for r in tids.values())
    assert all(b["특약ID"] in tids for b in bids.values())
    assert all(m["급부ID"] in bids for m in out["hum_담보매핑"])
    for c in out["sys_가입조건"]:
        assert c["종형ID"] in vids and (not c.get("특약ID") or tids[c["특약ID"]]["종형ID"] == c["종형ID"])
    # 가상 회사는 본뜬 회사보다 급부가 적고(10~40%를 뺀다), 같은 회사의 행은 같은 접두어다
    src = read_snapshot(SNAPSHOT)
    count = lambda rows, org: sum(1 for b in rows if b["급부ID"].startswith(org + "_"))  # noqa: E731
    for syn, org in (("SYNLIFE01", "HANWHALIFE"), ("SYNFIRE01", "SAMSUNGFIRE")):
        assert 0 < count(out["sys_급부"], syn) < count(src["sys_급부"], org)
        assert all(tids[b["특약ID"]]["종형ID"].startswith(syn + "_") for b in bids.values() if b["급부ID"].startswith(syn + "_"))


def test_same_input_gives_the_same_snapshot(made, tmp_path):
    again = tmp_path / "again"
    make(again)
    for f in sorted(made.iterdir()):
        assert (again / f.name).read_bytes() == f.read_bytes(), f.name


def test_names_reach_the_sentences(made):
    # 가상 사본은 사본의 모든 회사를 싣는다. 여기서는 화면에 올릴 회사와 가상 회사만 본다(사본에 새 회사가 들어와도 같은 규칙을 탄다)
    data = load(made, orgs=(*config.SITE_ORGS, *SYN))
    assert data.org_name("SYNLIFE01") == "가상생명 01" and data.org_sector("SYNFIRE01") == "손해보험"
    base = S.I.base_variants(data)[1][0]
    pts = S.points(data, base, S.Profile(), None)
    orgs = {data.variants[p]["기관코드"] for p in pts["맞붙는종형"]}
    assert orgs == {"HANWHALIFE", "SAMSUNGFIRE", *SYN}                    # 상대 넷: 회사가 많을 때의 규칙을 탄다
    assert pts["범위"]["문장"].startswith("비교한 상품은 생명보험 2개사, 손해보험 2개사의 상품 4개입니다.")
    assert pts["범위"]["업권별"] == {"생명보험": 2, "손해보험": 2}


BUILD = ROOT / "scripts" / "dev" / "build_console4_synthetic.py"


def tool(path: Path):
    """scripts/dev 의 스크립트를 모듈로 읽는다(꾸러미가 아니라 이름으로 import 하지 못한다)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_out_folder_is_wiped_only_when_this_tool_wrote_it(made, tmp_path):
    # --out data 로 돌리면 data/ 전체(crosscheck, goldset, snapshot 따위)를 지우고 가상 사본만 남기던 것을 막는다(2026-11-23 점검)
    keep = tmp_path / "data"
    (keep / "goldset").mkdir(parents=True)
    (keep / "goldset" / "a.jsonl").write_text("{}\n", encoding="utf-8")
    (keep / "meta.json").write_text('{"snapshot_at": "x"}\n', encoding="utf-8")
    run = subprocess.run([sys.executable, str(SCRIPT), "--out", str(keep), "--life", "1", "--nonlife", "1"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 1 and "지우지 않는다" in run.stdout, run.stdout + run.stderr
    assert sorted(p.name for p in keep.iterdir()) == ["goldset", "meta.json"] and (keep / "goldset" / "a.jsonl").exists()

    mod = tool(SCRIPT)
    assert mod.out_refusal(tmp_path / "없는 폴더") is None
    (tmp_path / "빈 폴더").mkdir()
    assert mod.out_refusal(tmp_path / "빈 폴더") is None
    assert mod.out_refusal(made) is None                                  # 이 도구가 쓴 가상 사본은 다시 쓴다
    assert mod.out_refusal(SNAPSHOT) and "가상자료 표시가 없다" in mod.out_refusal(SNAPSHOT)   # 실제 사본(탭 파일만 있다)
    assert mod.out_refusal(ROOT / "data") and mod.out_refusal(ROOT)
    assert mod.out_refusal(made / "meta.json")                            # 폴더가 아니다
    # 가상 사본이어도 다른 파일이 섞였으면 지우지 않는다
    mixed = tmp_path / "mixed"
    mixed.mkdir()
    for f in made.iterdir():
        (mixed / f.name).write_bytes(f.read_bytes())
    assert mod.out_refusal(mixed) is None
    (mixed / "memo.txt").write_text("x", encoding="utf-8")
    assert "memo.txt" in mod.out_refusal(mixed)


def test_rewriting_a_synthetic_folder_works(made, tmp_path):
    again = tmp_path / "again"
    make(again)
    make(again)                                                           # 이 도구가 쓴 폴더면 지우고 다시 쓴다
    assert sorted(p.name for p in again.iterdir()) == sorted(p.name for p in made.iterdir())


def test_work_folder_is_wiped_only_when_the_build_made_it(tmp_path):
    keep = tmp_path / "keep"
    keep.mkdir()
    (keep / "a.txt").write_text("x", encoding="utf-8")
    # 거절은 가상 사본을 만들기 전에 한다. 거절하지 않으면 tmp_path 아래에만 쓴다(저장소 out/ 에 쓰지 않게 경로를 다 준다)
    run = subprocess.run([sys.executable, str(BUILD), "--work", str(keep), "--synthetic", str(tmp_path / "syn"),
                          "--out", str(tmp_path / "page.html"), "--life", "1", "--nonlife", "1"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert run.returncode == 1 and "지우지 않는다" in run.stdout, run.stdout + run.stderr
    assert [p.name for p in keep.iterdir()] == ["a.txt"] and not (tmp_path / "syn").exists()

    mod = tool(BUILD)
    assert mod.work_refusal(tmp_path / "없는 폴더") is None
    (tmp_path / "빈 폴더").mkdir()
    assert mod.work_refusal(tmp_path / "빈 폴더") is None
    assert mod.work_refusal(ROOT / "data") and mod.work_refusal(ROOT / "proto_src" / "console4")
    (keep / mod.WORK_MARK).write_text("", encoding="utf-8")
    assert mod.work_refusal(keep) is None                                 # 이 명령이 만든 작업 폴더(표식이 있다)
    assert mod.work_refusal(keep / "a.txt")                               # 폴더가 아니다
