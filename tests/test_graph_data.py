"""관계망 자료(proto_src/graph/build_data.py 가 쓰는 graph.json)와 그 요약(summary).

- 화면에 올린 회사(config.SITE_ORGS)의 종형을 전부 싣고, 그 밖의 회사의 종형, 특약, 급부는 섞이지 않는가
- 요약의 수가 엣지를 따라 다시 센 수와 같은가(화면은 요약의 수를 그대로 쓴다)
- 급부가 없는 관문전용 종형은 종형 노드만, 매핑 대기 급부는 해당 엣지 없이 미연결 수로만 남는가
- 맞붙는 종형과 종형ID, 표준담보ID 가 시안 4의 sales.json, cover.json 과 같은가
- 같은 입력이면 같은 바이트이고, 커밋된 graph.json 과 graph2.html 이 사본으로 새로 만든 것과 같은가
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import pytest

from postlife import config
from postlife.site import compare as C
from postlife.site.model import load
from postlife.snapshot import KST, write_snapshot
from test_site_orgs import row, tables

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "snapshot"
GRAPH = ROOT / "proto_src" / "graph" / "graph.json"
PAGE = ROOT / "site" / "proto" / "graph2.html"
SALES = ROOT / "proto_src" / "console4" / "sales.json"
COVER = ROOT / "proto_src" / "console4" / "cover.json"
REGEN = "python proto_src/graph/build_data.py && python proto_src/graph/build.py 로 다시 만든다"
REAL = pytest.mark.skipif(not (SNAPSHOT / "meta.json").exists(), reason="실제 사본(data/snapshot)이 없다")


def graph_module():
    path = ROOT / "proto_src" / "graph" / "build_data.py"
    spec = importlib.util.spec_from_file_location("graph_build_data", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = graph_module()


def recount(out: dict) -> dict[str, dict]:
    """요약과 견줄 수를 엣지에서 다시 센다(build_data.summarize 를 쓰지 않는다). 종류 이름은 graph.json 에 실린 화면 이름이다
    (엣지 속함은 분류, 해당은 매핑. 용어 대조표 148~151)."""
    K = {name: i for i, name in enumerate(out["kinds"])}
    EK = {name: i for i, name in enumerate(out["ekinds"])}
    nodes = out["nodes"]
    kids: dict[tuple[int, int], list[int]] = defaultdict(list)
    cat: dict[int, str] = {}
    for s, t, k, _ in out["edges"]:
        kids[(s, k)].append(t)
        if k == EK["분류"]:
            cat[s] = nodes[t][0]
    res = {}
    for i, n in enumerate(nodes):
        if n[1] != K["종형"]:
            continue
        riders = [r for r in kids[(i, EK["포함"])] if nodes[r][1] == K["특약"]]
        bens = [b for r in riders for b in kids[(r, EK["포함"])] if nodes[b][1] == K["급부"]]
        linked = [b for b in bens if kids[(b, EK["매핑"])]]
        stds = sorted({s for b in bens for s in kids[(b, EK["매핑"])]})
        res[n[0]] = {"노드": i, "특약수": len(riders), "급부수": len(bens), "표준담보": stds,
                     "보장분야별": dict(Counter(cat[s] for s in stds)), "미연결급부": len(bens) - len(linked)}
    return res


def check_summary(out: dict) -> None:
    """요약의 수가 엣지를 따라 다시 센 수와 같은가."""
    s, nodes = out["summary"], out["nodes"]
    again = recount(out)
    assert list(s["종형"]) == list(again), "요약의 종형이 종형 노드와 다르다(차례도 노드 차례)"
    cat_order = [n[0] for n in nodes if out["kinds"][n[1]] == "보장 대분류"]
    for tid, t in s["종형"].items():
        r = again[tid]
        assert nodes[t["노드"]][0] == tid
        for k in ("노드", "특약수", "급부수", "표준담보", "미연결급부"):
            assert t[k] == r[k], (tid, k, t[k], r[k])
        assert t["보장분야별"] == r["보장분야별"], tid
        assert list(t["보장분야별"]) == [c for c in cat_order if c in t["보장분야별"]], "보장분야별은 보장분야 노드 차례"
        assert sum(t["보장분야별"].values()) == len(t["표준담보"])
        assert sum(t["미연결사유"].values()) == t["미연결급부"] and all(v > 0 for v in t["미연결사유"].values())
        assert all(out["kinds"][nodes[i][1]] == "표준담보" for i in t["표준담보"])
    std_ids = [n[0] for n in nodes if out["kinds"][n[1]] == "표준담보"]
    assert list(s["표준담보별종형"]) == std_ids
    idx = {n[0]: i for i, n in enumerate(nodes)}
    for sid, holders in s["표준담보별종형"].items():
        want = sorted(t["노드"] for t in s["종형"].values() if idx[sid] in t["표준담보"])
        assert holders == want, sid


def site_tables() -> dict[str, list[dict]]:
    """우체국(EPOST)과 목록 밖 회사(MERITZ). 우체국에 급부가 없는 관문전용 종형을 더하고, 우체국 급부 하나는 사전의 담보로
    확정하고 하나는 매핑 대기로 둔다. 메리츠화재의 급부는 사전에 없는 담보(STD_CA_DX)로 확정한 그대로다(사전밖)."""
    out = tables()
    gate = "EPOST_P2_aaaaaa"
    out["sys_상품종형"].append(row("sys_상품종형", 종형ID=gate, 개정판ID="EPOST_X_2610", 모상품ID="EPOST_X",
                                 종형계보키="EPOST_X_G", 기관코드="EPOST", 공시상품코드="P2", 공시상품명="EPOST 건강보험",
                                 종형명="간편형", 비교역할구분="관문전용", 심사유형="간편심사", 간편고지약칭="3.2.5",
                                 적용시작일="2026-10-01", 요약서해시="SG", 사업방법서해시="MG"))
    out["sys_특약"].append(row("sys_특약", 특약ID=f"{gate}_Tmain", 종형ID=gate, 특약계보키="main", 담보구분="주계약",
                             원시특약명="주계약", 최대가입금액만원=3000))
    for m in out["hum_담보매핑"]:
        if m["급부ID"] == "EPOST_P1_aaaaaa_Trider_Bone":
            m["확정표준담보ID"] = "STD_CA_DX_GENERAL"
        elif m["급부ID"] == "EPOST_P1_aaaaaa_Trider_Btwo":
            m.update(검토상태="대기", 확정표준담보ID=None, 추천표준담보ID="STD_CA_DX_SMALL")
    return out


@pytest.fixture(scope="module")
def small(tmp_path_factory):
    snap = tmp_path_factory.mktemp("graph") / "snapshot"
    write_snapshot(site_tables(), snap, datetime(2026, 11, 23, 10, tzinfo=KST))
    return snap


def org_of(out: dict, kind: str) -> set[str]:
    return {n[3] for n in out["nodes"] if out["kinds"][n[1]] == kind}


def test_small_snapshot_carries_every_type_of_the_picked_orgs(small):
    out, _, _ = G.build(small, ("EPOST",))
    check_summary(out)
    s = out["summary"]
    assert s["회사"] == ["EPOST"]
    assert set(s["종형"]) == {"EPOST_P1_aaaaaa", "EPOST_P2_aaaaaa"}
    assert org_of(out, "종형") == org_of(out, "특약") == org_of(out, "급부") == {"EPOST"}
    # 목록 밖 회사(MERITZ)는 시장 소식의 회사 노드로만 남는다(소식은 거르지 않는다)
    ids = [n[0] for n in out["nodes"]]
    meritz = ids.index("ORG:MERITZ")
    assert {out["ekinds"][e[2]] for e in out["edges"] if meritz in (e[0], e[1])} == {"발표"}
    assert not any(i.startswith("MERITZ_") for i in ids)
    # 급부가 없는 관문전용 종형은 종형 노드와 판매 엣지뿐이다
    gate = s["종형"]["EPOST_P2_aaaaaa"]
    assert gate == {"노드": gate["노드"], "심사유형": "간편심사", "비교역할": "관문전용", "특약수": 0, "급부수": 0,
                    "표준담보": [], "보장분야별": {}, "미연결급부": 0, "미연결사유": {}}
    assert [out["ekinds"][e[2]] for e in out["edges"] if gate["노드"] in (e[0], e[1])] == ["판매"]
    assert "EPOST_P2_aaaaaa_Tmain" not in ids
    # 확정 급부 하나는 해당 엣지로, 매핑 대기 급부 하나는 엣지 없이 미연결 수로
    p1 = s["종형"]["EPOST_P1_aaaaaa"]
    assert (p1["특약수"], p1["급부수"], p1["미연결급부"], p1["미연결사유"]) == (2, 2, 1, {"대기": 1})
    assert [ids[i] for i in p1["표준담보"]] == ["STD_CA_DX_GENERAL"]
    assert p1["보장분야별"] == {"CAT:암보장": 1}
    assert s["표준담보별종형"]["STD_CA_DX_GENERAL"] == [p1["노드"]] and s["표준담보별종형"]["STD_CA_DX_SMALL"] == []
    assert s["기준종형"] == ["EPOST_P1_aaaaaa"] and s["맞붙는종형"] == {"EPOST_P1_aaaaaa": []}


def test_small_snapshot_with_all_orgs(small):
    out, _, _ = G.build(small, "all")
    check_summary(out)
    s = out["summary"]
    assert s["회사"] == ["EPOST", "MERITZ"] and org_of(out, "급부") == {"EPOST", "MERITZ"}
    m = s["종형"]["MERITZ_M1_aaaaaa"]
    assert (m["급부수"], m["미연결급부"], m["미연결사유"], m["표준담보"]) == (2, 2, {"사전밖": 2}, [])
    assert s["맞붙는종형"] == {"EPOST_P1_aaaaaa": ["MERITZ_M1_aaaaaa"]}


def test_same_input_same_bytes(small):
    for orgs in (("EPOST",), "all"):
        assert G.dumps(G.build(small, orgs)[0]) == G.dumps(G.build(small, orgs)[0])


# ---------- 실제 사본 ----------
@pytest.fixture(scope="module")
def real():
    out, _, _ = G.build(SNAPSHOT)
    return out


@REAL
def test_real_summary_follows_edges(real):
    check_summary(real)


@REAL
def test_real_graph_carries_every_type_of_site_orgs_only(real):
    data = load(SNAPSHOT)            # 기본(config.SITE_ORGS)으로 거른 사본
    s = real["summary"]
    assert set(s["회사"]) == set(config.SITE_ORGS)
    assert list(s["종형"]) == data.variant_order, "화면에 올린 회사의 종형 전부를 화면의 종형 차례로 싣는다"
    for kind in ("종형", "특약", "급부"):
        assert org_of(real, kind) <= set(config.SITE_ORGS), kind
    others = {n[3] for n in real["nodes"] if real["kinds"][n[1]] == "회사"} - set(config.SITE_ORGS)
    other_ix = {i for i, n in enumerate(real["nodes"]) if real["kinds"][n[1]] == "회사" and n[3] in others}
    assert {real["ekinds"][e[2]] for e in real["edges"] if e[0] in other_ix or e[1] in other_ix} <= {"발표"}
    # 급부가 없는 관문전용 종형은 특약도 싣지 않는다
    for vid, t in s["종형"].items():
        if t["비교역할"] == "관문전용" and not t["급부수"]:
            assert t["특약수"] == 0, vid


@REAL
def test_real_summary_matches_comparison_holding(real):
    """종형마다 가진 표준담보와 매핑 대기 급부 수가 담보 비교(compare.collect)가 보는 것과 같다."""
    data = load(SNAPSHOT)
    ids = [n[0] for n in real["nodes"]]
    for vid, t in real["summary"]["종형"].items():
        confirmed, waiting, loose = C.collect(data, vid)
        assert {ids[i] for i in t["표준담보"]} == set(confirmed), vid
        assert t["미연결사유"].get("대기", 0) == sum(len(v) for v in waiting.values()) + len(loose), vid


@REAL
def test_real_keys_match_console4_files(real):
    """맞붙는 종형이 sales.json 의 값과 같고, sales.json 과 cover.json 의 종형ID, 표준담보ID 가 그래프의 노드 ID 와 같은 글자다."""
    S = json.loads(SALES.read_text(encoding="utf-8"))
    CV = json.loads(COVER.read_text(encoding="utf-8"))
    if S["자료시각"] != real["snapshot_at"]:
        pytest.skip(f"시안 4 자료({S['자료시각']})와 사본({real['snapshot_at']})의 자료 시각이 다르다")
    s = real["summary"]
    assert s["기준종형"] == [x["종형ID"] for x in S["기준종형"]]
    assert s["맞붙는종형"] == {b: S["기준별"][b]["맞붙는종형"] for b in S["기준별"]}
    type_keys = set(S["종형"]) | set(S["기준별"]) | set(CV["b"]) | {c for v in CV["b"].values() for c in v["cols"]}
    assert type_keys <= set(s["종형"])
    std_nodes = set(s["표준담보별종형"])
    assert {r[0] for v in CV["b"].values() for r in v["rows"]} <= std_nodes
    unused = {r["표준담보ID"] for r in G.jl(G.STD) if not r.get("사용여부")}
    assert set(S["표준담보"]) - std_nodes <= unused, "sales.json 에만 있는 표준담보는 사용여부가 거짓인 담보뿐이다"


@REAL
def test_committed_graph_and_page_match_snapshot(real, tmp_path):
    """커밋된 graph.json 과 graph2.html 이 커밋된 사본으로 새로 만든 것과 같은가."""
    committed = GRAPH.read_text(encoding="utf-8")
    t, t_snap = json.loads(committed)["snapshot_at"], real["snapshot_at"]
    if t != t_snap:
        assert datetime.fromisoformat(t) < datetime.fromisoformat(t_snap), \
            f"커밋된 graph.json({t})이 커밋된 사본({t_snap})보다 새것이다. {REGEN}"
        pytest.skip(f"사본({t_snap})이 커밋된 graph.json({t})보다 새것이다. {REGEN}")
    assert committed == G.dumps(real), f"커밋된 graph.json 이 같은 자료 시각의 사본으로 새로 만든 것과 다르다. {REGEN}"
    page = tmp_path / "graph2.html"
    run = subprocess.run([sys.executable, str(ROOT / "proto_src" / "graph" / "build.py"), str(page)], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    assert page.read_bytes() == PAGE.read_bytes(), f"커밋된 site/proto/graph2.html 이 tpl.html 과 graph.json 을 합친 것과 다르다. {REGEN}"
