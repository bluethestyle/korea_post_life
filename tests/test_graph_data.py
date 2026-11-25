"""관계망 자료(proto_src/graph/build_data.py 가 쓰는 graph.json)와 그 요약(summary).

- 화면에 올린 회사(config.SITE_ORGS)의 종형을 전부 싣고, 그 밖의 회사의 종형, 특약, 급부는 섞이지 않는가
- 요약의 수가 엣지를 따라 다시 센 수와 같은가(화면은 요약의 수를 그대로 쓴다)
- 급부가 없는 관문전용 종형은 종형 노드만, 매핑 대기 급부는 해당 엣지 없이 미연결 수로만 남는가
- 맞붙는 종형과 종형ID, 표준담보ID 가 시안 4의 sales.json, cover.json 과 같은가
- 같은 입력이면 같은 바이트이고, 커밋된 graph.json 과 graph2.html 이 사본으로 새로 만든 것과 같은가
- 스키마 개정 1단계(docs/proposals/관계그래프_재설계_검토.md 3절, 5.1절): 보유 엣지가 요약과 담보 비교의 보유 계산(Holding)과
  같은가, 개정 엣지가 개정 변동(sales.revision_summary)과 같은가, 결합제약 엣지와 가입금액연동 속성이 스냅샷 행을 빠짐없이 옮겼는가,
  담보 관계가 시드 파일과 같은가, 선별 통과 시장 동향이 sales.json 과 같은가, 특약 계보가 회사를 넘지 않는가, 지금 화면 둘이 읽는
  것(nodes 의 형식, 종류 0~6, edges 의 종류 0~5, ekinds 0~5 의 이름, keys 의 기존 번호, summary 의 기존 열쇠)이 그대로인가,
  자료가 모르는 모양이면 빌드가 멈추는가
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
from postlife.site import insights as I
from postlife.site import orgs as site_orgs
from postlife.site import sales as SL
from postlife.site import terms
from postlife.site.model import load
from postlife.snapshot import read_snapshot
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
    확정하고 하나는 매핑 대기로 둔다. 메리츠화재의 급부는 사전에 없는 담보(STD_CA_DX)로 확정한 그대로다(사전밖).
    스냅샷의 표준담보 사전은 그래프가 읽는 시드(data/seed/hum_표준담보사전.jsonl)와 같게 둔다(보유 엣지가 담보 비교의 보유
    계산과 같은지 빌드가 확인한다). 결합제약 최대연동 행에는 근거문구를 넣고(가입금액연동), 시장 동향에는 언급 담보와 언급 상품을
    적는다(그래프에 없는 ID 는 넘긴다)."""
    out = tables()
    out["hum_표준담보사전"] = G.jl(G.STD)
    for r in out["sys_결합제약"]:
        r["근거문구"] = "주계약 가입금액 이내"
    out["sys_시장동향"][0].update(관련표준담보ID="STD_CA_DX_GENERAL;STD_NOT_THERE", 관련종형ID="EPOST_P1_aaaaaa")
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


# ---------- 스키마 개정 1단계(docs/proposals/관계그래프_재설계_검토.md 3절, 5.1절) ----------
SEED_REL = ROOT / "data" / "seed" / "표준담보_관계.jsonl"
LEGACY_KINDS = ["회사", "종형", "특약", "급부", "표준담보", "보장 대분류", "시장 동향"]
LEGACY_EKINDS = ["판매", "포함", "매핑", "분류", "담보 관계", "발표"]
NEW_EKINDS = ["보유", "결합제약", "개정", "언급 담보", "언급 상품"]
# 1단계 전(2026-11-23 스냅샷)의 keys. 지금 화면 둘이 속성을 이 번호로 풀므로 번호가 바뀌면 안 된다. 새 속성은 이 뒤에 붙는다
LEGACY_KEYS = ["기관코드", "공시상품명", "종형명", "간편고지", "갱신유형", "갱신주기년", "심사유형", "환급유형", "적용시작일",
               "담보구분", "갱신여부", "최소가입금액만원", "최대가입금액만원", "기준지급액", "기준가입금액만원", "면책일수", "감액",
               "근거", "지급횟수제한", "보장대분류", "보장중분류", "급부유형", "비교기준단위만원", "핵심요약", "분류유형", "발표일자",
               "매체명", "출처URL", "판정확률", "갱신", "급부역할", "검토상태", "매핑확률", "관계", "확신_gemini", "확신_claude",
               "발표일"]
LEGACY_SUMMARY = ["회사", "종형", "표준담보별종형", "기준종형", "맞붙는종형"]
TOP = ["snapshot_at", "kinds", "ekinds", "kindLabels", "ekindLabels", "nodes", "edges", "edges2", "keys", "summary", "표시명"]
# 엣지 종류(ekinds 의 이름)마다 허용하는 (출발 노드 종류, 도착 노드 종류)(kinds 의 이름)
ENDS = {
    "판매": {("회사", "종형")}, "포함": {("종형", "특약"), ("특약", "급부")}, "매핑": {("급부", "표준담보")},
    "분류": {("표준담보", "보장 대분류")}, "담보 관계": {("표준담보", "표준담보")}, "발표": {("회사", "시장 동향")},
    "보유": {("종형", "표준담보")}, "결합제약": {("특약", "특약")}, "개정": {("종형", "종형")},
    "언급 담보": {("시장 동향", "표준담보")}, "언급 상품": {("시장 동향", "종형")},
}
PINNED_AT = "2026-11-23T16:40:16+09:00"      # 아래 건수 시험이 기준으로 삼는 스냅샷(재설계 검토 문서의 수치)


def dec(out: dict, p: dict) -> dict:
    return {out["keys"][int(k)]: v for k, v in p.items()}


def edges_of(out: dict, name: str) -> list[tuple[int, int, dict]]:
    """엣지 종류 하나의 (출발 노드 번호, 도착 노드 번호, 속성). 0~5는 edges, 6~10은 edges2 에 있다."""
    k = out["ekinds"].index(name)
    return [(s, t, dec(out, p)) for s, t, kk, p in (out["edges"] if k < 6 else out["edges2"]) if kk == k]


def props_of(out: dict, kind: str) -> dict[str, dict]:
    k = out["kinds"].index(kind)
    return {n[0]: dec(out, n[4]) for n in out["nodes"] if n[1] == k}


def jtype(v) -> str:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, list):
        return "list[" + ",".join(sorted({jtype(x) for x in v})) + "]"
    return type(v).__name__


def check_contract(out: dict) -> None:
    """지금 화면 둘이 읽는 것은 그대로이고, 새 것은 정한 자리에만 있는가."""
    assert list(out) == TOP
    assert out["kinds"] == LEGACY_KINDS
    assert out["ekinds"] == LEGACY_EKINDS + NEW_EKINDS, "ekinds 0~5의 차례와 이름은 그대로, 새 종류는 끝에 붙는다"
    assert out["kindLabels"] == terms.graph_kind_labels(out["kinds"]) == LEGACY_KINDS
    assert out["ekindLabels"] == terms.graph_edge_labels(out["ekinds"])
    assert out["ekindLabels"][7] == "특약 부가 조건" and out["ekindLabels"][:7] == out["ekinds"][:7]
    assert {e[2] for e in out["edges"]} <= set(range(6)), "edges 에는 엣지 종류 0~5만 싣는다"
    assert {e[2] for e in out["edges2"]} <= set(range(6, 11)), "새 종류는 edges2 에만 싣는다"
    nodes, kinds = out["nodes"], out["kinds"]
    for n in nodes:
        assert len(n) == 5 and isinstance(n[0], str) and n[1] in range(7) and isinstance(n[2], str), n
        assert n[3] is None or isinstance(n[3], str), n
        assert isinstance(n[4], dict) and all(int(k) < len(out["keys"]) for k in n[4]), n
    seen: dict[tuple, set[str]] = defaultdict(set)
    for name in ("edges", "edges2"):
        for s, t, k, p in out[name]:
            ek = out["ekinds"][k]
            assert (kinds[nodes[s][1]], kinds[nodes[t][1]]) in ENDS[ek], (ek, nodes[s][0], nodes[t][0])
            for key, v in dec(out, p).items():
                assert v is not None, (ek, key)
                seen[("엣지", ek, key)].add(jtype(v))
    for n in nodes:
        for key, v in dec(out, n[4]).items():
            assert v is not None, (n[0], key)
            seen[("노드", kinds[n[1]], key)].add(jtype(v))
    mixed = {k: v for k, v in seen.items() if len(v) > 1}
    assert not mixed, f"(종류, 속성)마다 자료형은 하나다: {mixed}"
    assert list(out["summary"]) == LEGACY_SUMMARY + ["특약계보"]


def test_type_label_does_not_repeat_the_type_name():
    v = lambda prod, name: {"공시상품명": prod, "종형명": name}  # noqa: E731
    assert G.type_label(v("무배당 우체국건강보험 2606 1종(간편가입315)", "1종(간편가입315)")) == "우체국건강보험 2606 1종(간편가입315)"
    assert G.type_label(v("무배당 간편보험(2607.5) 7종(해약환급금미지급형)", "7종(해약환급금 미지급형) 315·5")) == \
        "간편보험(2607.5) 7종(해약환급금미지급형) 315·5"
    assert G.type_label(v("무배당 간편보험 8종(미지급형,일반고지)", "8종(미지급형, 일반고지)")) == "간편보험 8종(미지급형,일반고지)"
    assert G.type_label(v("한화생명 시그니처 H통합보험 무배당", "간편가입형(1년)")) == "한화생명 시그니처 H통합보험 무배당 간편가입형(1년)"
    assert G.type_label(v("무배당 우체국통합건강보험 2504", "단일")) == "우체국통합건강보험 2504 단일"


def test_small_snapshot_stage1_contract(small):
    for orgs in (("EPOST",), "all"):
        check_contract(G.build(small, orgs)[0])
    out = G.build(small, ("EPOST",))[0]
    ids = [n[0] for n in out["nodes"]]
    vid, rider, b1, b2 = "EPOST_P1_aaaaaa", "EPOST_P1_aaaaaa_Trider", "EPOST_P1_aaaaaa_Trider_Bone", "EPOST_P1_aaaaaa_Trider_Btwo"
    held = [(ids[s], ids[t], p) for s, t, p in edges_of(out, "보유")]
    assert held == [(vid, "STD_CA_DX_GENERAL", {"급부수": 1, "특약수": 1, "대표급부ID": b1, "추출검수대기급부수": 1})]
    bens = props_of(out, "급부")
    assert bens[b2]["매핑상태"] == "대기" and bens[b2]["추천표준담보ID"] == "STD_CA_DX_SMALL" and "매핑상태" not in bens[b1]
    assert bens[b1]["추출검수대기항목"] == ["기준지급금액만원"]
    riders = props_of(out, "특약")
    assert riders[rider]["가입금액연동"] == "주계약 가입금액 이내" and riders[rider]["보장대분류"] == ["암보장"]
    assert riders[f"{vid}_Tmain"]["특약계보키"] == "main" and "보장대분류" not in riders[f"{vid}_Tmain"]
    assert edges_of(out, "결합제약") == []          # 최대연동은 엣지가 아니라 대상 특약의 속성이다
    orgs = props_of(out, "회사")
    assert orgs["ORG:EPOST"] == {"기관코드": "EPOST", "기관구분": "보험회사", "업권": "우체국", "비교대상": True}
    assert orgs["ORG:MERITZ"] == {"기관코드": "MERITZ", "기관구분": "보험회사", "업권": "손해보험", "비교대상": False}
    assert props_of(out, "종형")[vid]["종형계보키"] == "EPOST_X_K"
    news = props_of(out, "시장 동향")["TRD_MERITZ_1"]
    assert (news["수집주차"], news["선별상태"]) == ("2026-W47", "undecided")
    # 언급 담보와 언급 상품: 그래프에 없는 ID(STD_NOT_THERE)는 넘긴다
    assert [(ids[s], ids[t]) for s, t, _ in edges_of(out, "언급 담보")] == [("TRD_MERITZ_1", "STD_CA_DX_GENERAL")]
    assert [(ids[s], ids[t]) for s, t, _ in edges_of(out, "언급 상품")] == [("TRD_MERITZ_1", vid)]
    assert [p for _, _, p in edges_of(out, "매핑")] == [{"검토상태": "자동확정", "매핑확률": 0.97, "확정방식": "확률 산정 모델"}]
    # 두 회사의 특약계보키가 같아도(main, rider) 회사를 넘어 한 계보로 묶지 않는다
    both = G.build(small, "all")[0]
    assert both["summary"]["특약계보"] == {} and props_of(both, "회사")["ORG:MERITZ"]["비교대상"] is True


def snapshot_with(tmp_path, change) -> Path:
    t = site_tables()
    change(t)
    snap = tmp_path / "snapshot"
    write_snapshot(t, snap, datetime(2026, 11, 23, 10, tzinfo=KST))
    return snap


def test_build_stops_when_the_data_has_an_unknown_shape(tmp_path, monkeypatch):
    def cap_shape(t):
        t["sys_결합제약"][0]["제약수치"] = 2

    def cap_target(t):
        t["sys_결합제약"][0]["대상특약ID"] = "EPOST_P1_aaaaaa_Tgone"

    for name, change in (("cap_shape", cap_shape), ("cap_target", cap_target)):
        with pytest.raises(G.GraphDataError):
            G.build(snapshot_with(tmp_path / name, change), ("EPOST",))
    good = snapshot_with(tmp_path / "good", lambda t: None)
    seed = G.jl(SEED_REL)
    for name, rows in (("unknown_id", [{**seed[0], "좁은담보ID": "STD_NOT_THERE"}]),
                       ("no_confidence", [{**seed[0], "관계": "포함" if seed[0]["관계"] == "통합" else "통합"}])):
        path = tmp_path / f"{name}.jsonl"
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        monkeypatch.setattr(G, "REL_SEED", path)
        with pytest.raises(G.GraphDataError):
            G.build(good, ("EPOST",))


@pytest.fixture(scope="module")
def real_data():
    return load(SNAPSHOT)


@REAL
def test_real_schema_contract(real):
    check_contract(real)
    assert real["keys"][:len(LEGACY_KEYS)] == LEGACY_KEYS, "기존 속성의 keys 번호는 그대로다"
    assert real["표시명"] == terms.graph_display_names()


@REAL
def test_real_build_is_deterministic(real):
    assert G.dumps(G.build(SNAPSHOT)[0]) == G.dumps(real)


@REAL
def test_real_holding_edges_match_summary_and_holding(real, real_data):
    """보유 엣지가 summary.종형[].표준담보, 담보 비교의 보유 계산(insights.Holding), 엣지 경로로 센 수와 같다."""
    ids = [n[0] for n in real["nodes"]]
    held = edges_of(real, "보유")
    pairs = [(ids[s], ids[t]) for s, t, _ in held]
    assert len(pairs) == len(set(pairs))
    assert set(pairs) == {(tid, ids[i]) for tid, t in real["summary"]["종형"].items() for i in t["표준담보"]}
    EK = {name: i for i, name in enumerate(real["ekinds"])}
    kids: dict[tuple[int, int], list[int]] = defaultdict(list)
    for s, t, k, _ in real["edges"]:
        kids[(s, k)].append(t)
    path: dict[tuple[int, int], tuple[set, set]] = defaultdict(lambda: (set(), set()))
    for v, n in enumerate(real["nodes"]):
        if real["kinds"][n[1]] == "종형":
            for r in kids[(v, EK["포함"])]:
                for b in kids[(r, EK["포함"])]:
                    for sd in kids[(b, EK["매핑"])]:
                        path[(v, sd)][0].add(r)
                        path[(v, sd)][1].add(b)
    hold = {tid: I.Holding(real_data, tid) for tid in real["summary"]["종형"]}
    for tid, h in hold.items():
        assert set(h.has) == {sid for t, sid in pairs if t == tid}, tid
    for s, t, p in held:
        h, sid = hold[ids[s]], ids[t]
        views = h.confirmed[sid]
        assert p["급부수"] == len(views) == len(path[(s, t)][1]), (ids[s], sid)
        assert p["특약수"] == len({x["tid"] for x in views}) == len(path[(s, t)][0]), (ids[s], sid)
        rep = h.rep(sid)
        assert p.get("대표급부ID") == (rep["id"] if rep else None), (ids[s], sid)
        assert p.get("매핑검수대기급부수", 0) == len(h.waiting.get(sid, [])), (ids[s], sid)
        assert p.get("추출검수대기급부수", 0) == sum(x["id"] in real_data.pending_benefit for x in views), (ids[s], sid)


@REAL
def test_real_revision_edges_match_revision_changes(real, real_data):
    """개정 엣지가 개정 변동(sales.revision_summary 의 짝, sales.json 의 개정변동.짝)과 같은 비교 건, 같은 수다."""
    ids = [n[0] for n in real["nodes"]]
    got = [(ids[s], ids[t], p) for s, t, p in edges_of(real, "개정")]
    want = [(x["전"], x["후"], {k: x[k] for k in SL.REVISION_KINDS}) for x in SL.revision_summary(real_data)["짝"]]
    assert got == want
    types = props_of(real, "종형")
    for old, new, _ in got:
        assert types[old]["종형계보키"] == types[new]["종형계보키"] and types[old]["개정판ID"] != types[new]["개정판ID"]
    S = json.loads(SALES.read_text(encoding="utf-8"))
    if S["자료시각"] == real["snapshot_at"]:
        assert [(x["전"], x["후"], {k: x[k] for k in SL.REVISION_KINDS}) for x in S["개정변동"]["짝"]] == got


@REAL
def test_real_constraints_carry_every_snapshot_row(real):
    """결합제약 엣지(최대연동 밖의 유형)와 대상 특약의 가입금액연동(최대연동)을 합하면 스냅샷의 결합제약 행 전부다."""
    rows = site_orgs.filter_tables(read_snapshot(SNAPSHOT), site_orgs.parse(None))["sys_결합제약"]
    ids = [n[0] for n in real["nodes"]]
    linked = {rid: p["가입금액연동"] for rid, p in props_of(real, "특약").items() if "가입금액연동" in p}
    edges = edges_of(real, "결합제약")
    assert len(edges) + len(linked) == len(rows)
    assert linked == {r["대상특약ID"]: r["근거문구"] for r in rows if r["제약유형"] == "최대연동"}
    others = sorted((r for r in rows if r["제약유형"] != "최대연동"), key=lambda r: r["제약ID"])
    assert [(ids[s], ids[t], p["제약유형"], p.get("근거문구")) for s, t, p in edges] == \
        [(r["기준특약ID"], r["대상특약ID"], r["제약유형"], r["근거문구"]) for r in others]


@REAL
def test_real_relations_follow_the_seed_ids(real):
    """담보 관계 엣지는 시드 파일의 ID 와 관계로 만들고(좁은 담보 → 넓은 담보), 확신 값만 이중 추출 파일에서 붙인다."""
    ids = [n[0] for n in real["nodes"]]
    conf = {(r["관계"], r["넓은담보"], r["좁은담보"]): r for r in G.jl(G.REL)}
    want = []
    for r in G.jl(SEED_REL):
        c = conf[(r["관계"], r["넓은담보"], r["좁은담보"])]
        p = {"관계": r["관계"], "확신_gemini": c.get("확신_gemini"), "확신_claude": c.get("확신_claude")}
        want.append((r["좁은담보ID"], r["넓은담보ID"], {k: v for k, v in p.items() if v is not None}))
    assert [(ids[s], ids[t], p) for s, t, p in edges_of(real, "담보 관계")] == want


@REAL
def test_real_news_selection_matches_sales(real):
    """선별 통과이고 sales.json 이 보이는 수집주차인 시장 동향이 sales.json 의 시장소식과 같다."""
    news = props_of(real, "시장 동향")
    assert {p["선별상태"] for p in news.values()} <= {"passed", "below", "undecided"}
    S = json.loads(SALES.read_text(encoding="utf-8"))
    if S["자료시각"] != real["snapshot_at"]:
        pytest.skip(f"시안 4 자료({S['자료시각']})와 스냅샷({real['snapshot_at']})의 자료 시각이 다르다")
    week = S["시장소식"]["주차"]
    got = {nid for nid, p in news.items() if p["선별상태"] == "passed" and p.get("수집주차") == week}
    assert got == {x["동향ID"] for x in S["시장소식"]["소식"]}


@REAL
def test_real_rider_lineages_stay_within_one_company(real):
    nodes = real["nodes"]
    K, EK = real["kinds"].index("종형"), real["ekinds"].index("포함")
    type_of = {t: s for s, t, k, _ in real["edges"] if k == EK and nodes[s][1] == K}
    found: dict[tuple[str, str], set[int]] = defaultdict(set)
    for i, n in enumerate(nodes):
        if real["kinds"][n[1]] == "특약":
            found[(n[3], dec(real, n[4])["특약계보키"])].add(type_of[i])
    want = {key: sorted(v) for key, v in found.items() if len(v) >= 2}
    lin = real["summary"]["특약계보"]
    assert {(org, key): v for org, d in lin.items() for key, v in d.items()} == want
    assert all(nodes[i][3] == org for org, d in lin.items() for v in d.values() for i in v)


@REAL
def test_real_type_labels_do_not_repeat_the_type_name(real):
    sq = lambda s: s.replace(" ", "")  # noqa: E731
    label = {n[0]: n[2] for n in real["nodes"]}
    for nid, p in props_of(real, "종형").items():
        assert sq(label[nid]).count(sq(p["종형명"])) == 1, label[nid]
        assert label[nid].startswith(p["공시상품명"].replace("무배당 ", "")), label[nid]


@REAL
def test_real_counts_of_the_pinned_snapshot(real):
    """재설계 검토 문서(2026-11-23 스냅샷)의 수치. 스냅샷이 바뀌면 건너뛴다(위 시험들이 원천과 같은지를 계속 본다)."""
    if real["snapshot_at"] != PINNED_AT:
        pytest.skip(f"스냅샷({real['snapshot_at']})이 수치를 적은 스냅샷({PINNED_AT})과 다르다")
    assert Counter(real["ekinds"][e[2]] for e in real["edges2"]) == {"보유": 849, "결합제약": 5, "개정": 3}
    assert [(p["신설"], p["변경"], p["종료"]) for _, _, p in edges_of(real, "개정")] == [(4, 15, 4), (4, 12, 4), (4, 12, 4)]
    held = [p for _, _, p in edges_of(real, "보유")]
    assert (sum("매핑검수대기급부수" in p for p in held), sum("추출검수대기급부수" in p for p in held)) == (23, 144)
    assert all("대표급부ID" in p for p in held)
    riders, bens = props_of(real, "특약"), props_of(real, "급부")
    assert sum("가입금액연동" in p for p in riders.values()) == 74
    assert sum("보장대분류" in p for p in riders.values()) == 2743 - 718
    assert Counter(p["매핑상태"] for p in bens.values() if "매핑상태" in p) == {"대상외": 2267, "대기": 69}
    assert (sum("추천표준담보ID" in p for p in bens.values()), sum("추출검수대기항목" in p for p in bens.values())) == (69, 705)
    assert len(edges_of(real, "담보 관계")) == 32
    assert sum(len(d) for d in real["summary"]["특약계보"].values()) == 482
    assert Counter(p.get("확정방식") for _, _, p in edges_of(real, "매핑")) == {"확률 산정 모델": 2243, "교차 검증": 2036}
