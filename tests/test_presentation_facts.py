"""발표 영상의 사실 자료(presentation_animation/facts.json)와 그것을 만드는 스크립트(scripts/export_presentation_facts.py).

- 커밋된 facts.json 은 같은 사본, 같은 화면 자료, 같은 문서로 다시 만든 것과 바이트까지 같아야 한다. 주간 사본이 들어와 사본이
  더 새것이면(화면 자료나 facts.json 을 아직 다시 만들지 않았으면) 그 비교만 건너뛰고 다시 만들라고 알린다.
- 문서에서 옮긴 항목은 문서 경로가 있고, 그 절에 근거 문구가 글자 그대로 있어야 한다.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "snapshot"
FACTS = ROOT / "presentation_animation" / "facts.json"
SALES = ROOT / "proto_src" / "console4" / "sales.json"

spec = importlib.util.spec_from_file_location("export_presentation_facts", ROOT / "scripts" / "export_presentation_facts.py")
epf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(epf)

REGEN = "python scripts/export_app_data.py 다음 python scripts/export_presentation_facts.py 로 다시 만든다"


def _committed() -> dict:
    return json.loads(FACTS.read_text(encoding="utf-8"))


def _snapshot_at() -> str:
    return json.loads((SNAPSHOT / "meta.json").read_text(encoding="utf-8"))["snapshot_at"]


@pytest.mark.skipif(not (SNAPSHOT / "meta.json").exists(), reason="실제 사본(data/snapshot)이 없다")
def test_committed_facts_match_regenerated():
    t = _snapshot_at()
    screen_t = json.loads(SALES.read_text(encoding="utf-8")).get("자료시각")
    committed_t = _committed().get("snapshot_at")
    if screen_t != t or committed_t != t:
        pytest.skip(f"사본({t})과 화면 자료({screen_t}), 사실 자료({committed_t})의 시각이 다르다. {REGEN}")
    assert FACTS.read_text(encoding="utf-8") == epf.render(epf.build(ROOT)), f"facts.json 이 사본과 다르다. {REGEN}"


@pytest.mark.skipif(not (SNAPSHOT / "meta.json").exists(), reason="실제 사본(data/snapshot)이 없다")
def test_same_inputs_give_same_bytes():
    if json.loads(SALES.read_text(encoding="utf-8")).get("자료시각") != _snapshot_at():
        pytest.skip(f"화면 자료가 사본과 다른 시각이다. {REGEN}")
    assert epf.render(epf.build(ROOT)) == epf.render(epf.build(ROOT))


def test_document_sources_exist_and_quotes_are_in_their_section():
    docs = [(k, f["source"]) for k, f in _committed()["facts"].items() if f["source"]["kind"] == "document"]
    assert docs, "문서에서 옮긴 항목이 없다"
    for key, src in docs:
        path = ROOT / src["path"]
        assert path.exists(), f"{key}: 문서 {src['path']} 가 없다"
        assert src["quotes"], f"{key}: 근거 문구가 없다"
        assert epf.missing_quotes(ROOT, src["path"], src["section"], tuple(src["quotes"])) == [], \
            f"{key}: {src['path']} '{src['section']}' 절에 근거 문구가 없다"


def test_every_fact_has_value_label_as_of_and_source():
    data = _committed()
    assert data["format"] == epf.FORMAT
    for key, f in data["facts"].items():
        assert re.fullmatch(r"[a-z][a-z0-9_]*", key), key
        assert {"value", "label", "as_of", "source"} <= set(f), key
        assert f["label"] and re.fullmatch(r"\d{4}-\d{2}-\d{2}", f["as_of"]), key
        kind = f["source"]["kind"]
        assert kind in {"snapshot", "config", "schema", "seed", "code", "screen_data", "document", "manual", "repo", "derived"}, key
        if kind in {"snapshot", "config", "schema", "seed", "code", "screen_data", "repo"}:
            assert (ROOT / f["source"]["file"]).exists(), f"{key}: {f['source']['file']} 가 없다"
        if kind == "manual":
            assert f.get("note"), f"{key}: 손으로 적은 값은 다시 세는 방법을 note 에 적는다"
        if kind == "derived":
            assert f["source"]["from"] and set(f["source"]["from"]) <= set(data["facts"]), f"{key}: 계산의 바탕 열쇠가 없다"


def test_deck_example_facts_agree_with_the_count_keys():
    """발표 덱이 쓰는 예(암 수술비, 6개월 전 입원, 관계 그래프)가 같은 자료의 다른 열쇠와 어긋나지 않는다."""
    facts = {k: f["value"] for k, f in _committed()["facts"].items()}
    nodes = facts["graph_nodes_by_kind"]
    assert nodes["급부"] == facts["benefit_count_site"]
    assert nodes["표준담보"] == facts["standard_coverage_in_use"]
    assert facts["graph_edges_by_kind"]["담보 관계"] == facts["coverage_relation_count"]
    assert facts["graph_edges_by_kind"]["매핑"] == facts["mapping_status_site"]["자동확정"]
    rel = facts["coverage_relation_examples"]
    assert {k: sum(len(g["narrow"]) for g in v) for k, v in rel.items()} == facts["coverage_relations_by_kind"]
    cancer = facts["example_cancer_surgery"]
    assert list(cancer["orgs"]) == facts["site_orgs"]
    assert cancer["missing_treatment_both_peers"]["count"] == len(cancer["missing_treatment_both_peers"]["names"])
    assert facts["example_cancer_surgery_names"] == {o: v["benefit"] for o, v in cancer["orgs"].items()}
    gate = facts["example_gate_6months"]
    assert gate["age"] == facts["reference_condition"]["age"]
    assert set(gate["cell"]["orgs"]) == set(facts["site_orgs"])
    routes = facts["mapping_auto_confirm_by_route"]
    for scope in routes.values():
        assert scope["decision_model"] + scope["cross_check"] == scope["total"]
    assert routes["site"]["total"] == facts["mapping_status_site"]["자동확정"]
    assert sum(facts["sales_insight_by_category_display"].values()) == facts["sales_insight_count"]
    assert set(facts["sales_insight_category_names"]) == set(facts["sales_insight_categories"])
    assert sum(facts["commits_by_date"].values()) == facts["commit_count"]
    assert sum(facts["commits_by_author"].values()) == facts["commit_count"]
    assert facts["project_days"]["days"] == len(facts["commits_by_date"])


def test_no_local_paths_or_secrets():
    text = FACTS.read_text(encoding="utf-8")
    for bad in ("/home/", "/data/projects", "/tmp/", ":\\\\", "local/", "SPREADSHEET", "GEMINI_API_KEY", "SERVICE_ACCOUNT"):
        assert bad not in text, bad


def test_missing_quote_stops_the_build(tmp_path, monkeypatch):
    doc = tmp_path / "docs" / "x.md"
    doc.parent.mkdir()
    doc.write_text("# 제목\n\n## 1. 가\n\n값은 3입니다.\n\n## 2. 나\n\n값은 4입니다.\n", encoding="utf-8")
    ok = ("k", 3, "값", "2026-11-23", "docs/x.md", "1. 가", ("값은 3입니다.",), None)
    monkeypatch.setattr(epf, "DOC_FACTS", [ok])
    assert epf.doc_facts(tmp_path)["k"]["value"] == 3
    # 다른 절에만 있는 문구는 근거가 되지 않는다
    monkeypatch.setattr(epf, "DOC_FACTS", [("k", 4, "값", "2026-11-23", "docs/x.md", "1. 가", ("값은 4입니다.",), None)])
    with pytest.raises(epf.FactsError, match="근거 문구가 없다"):
        epf.doc_facts(tmp_path)
    monkeypatch.setattr(epf, "DOC_FACTS", [("k", 3, "값", "2026-11-23", "docs/x.md", "3. 다", ("값은 3입니다.",), None)])
    with pytest.raises(epf.FactsError, match="절 제목"):
        epf.doc_facts(tmp_path)


def test_segment_map_grid_counts_match_the_count_keys():
    """칸마다의 값(segment_map_grid)을 센 수가 브리핑에서 옮긴 칸 수 열쇠와 같아야 한다(영상의 지도 그림과 푸터가 어긋나지 않게)."""
    from postlife.site.sales import GENERAL_NOTE, LABELS

    facts = _committed()["facts"]
    grid = facts["segment_map_grid"]["value"]
    assert [r["row"] for r in grid] == facts["segment_map_rows"]["value"]
    for r in grid:
        assert [c["column"] for c in r["cells"]] == facts["segment_map_columns"]["value"], r["row"]
    cells = [c for r in grid for c in r["cells"]]
    labels = facts["segment_map_labels"]["value"]
    assert set(labels) == set(LABELS.values())
    assert {c["label"] for c in cells} <= set(labels)

    def count(label: str) -> int:
        return sum(1 for c in cells if c["label"] == label)

    only_open, both_open, only_closed, all_closed, no_data = LABELS.values()
    assert len(cells) == facts["segment_map_cell_count"]["value"]
    assert count(both_open) == facts["segment_map_open_together_cells"]["value"]
    assert count(only_open) == facts["segment_map_ours_only_open_cells"]["value"]
    closed_general = sum(1 for c in cells if c["label"] == only_closed and c["sub"] == GENERAL_NOTE)
    assert closed_general == facts["segment_map_ours_closed_cells"]["value"]
    assert sum(1 for c in cells if c["gate_only"]) == facts["segment_map_gate_only_cells"]["value"]
    base = facts["briefing_by_base_variant"]["value"][facts["default_base_variant"]["value"]["name"]]["segment_map"]
    assert count(all_closed) == base["all_closed"]
    assert count(no_data) == base["no_data"]


def test_relation_covered_reads_only_cells_without_held_or_pending_benefits():
    sales = {"기준종형": [{"종형ID": "B"}], "표준담보": {k: {"이름": f"{k} 이름"} for k in ("A", "C", "D", "E", "W")}}
    cover = {"b": {"B": {"cols": ["B", "P"], "rows": [
        ["A", [{"c": ["넓은 담보", ["W"], False]}, 0], {}],                                     # 관계 담보로만 덮음
        ["C", [{"r": 0, "i": [0], "n": 1, "c": ["넓은 담보", ["W"], False]}, 0], {}],           # 확정 급부가 있으면 세지 않음
        ["D", [{"r": None, "i": [], "n": 0, "w": 1, "c": ["부분 담보", ["W"], True]}, 0], {}],  # 매핑 대기가 있으면 세지 않음
        ["E", [0, {"r": 1, "i": [1], "n": 1}], {}],                                             # 없음
    ]}}}
    value = epf.cover_facts(sales, cover, "2026-11-23")["relation_covered_coverages"]["value"]
    assert value == {"count": 1, "items": [{"id": "A", "name": "A 이름", "kind": "넓은 담보", "via": ["W 이름"], "partial": False}]}
    cover["b"]["B"]["cols"] = ["P", "B"]
    with pytest.raises(epf.FactsError, match="첫 열"):
        epf.cover_facts(sales, cover, "2026-11-23")
