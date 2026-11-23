"""표준담보 관계 시드(data/seed/표준담보_관계.jsonl)와 덮임 네 갈래(site/relations.py)."""
import json
from pathlib import Path

import pytest

from postlife.site import relations as R

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"
PROPOSAL = ROOT / "data" / "proposals" / "표준담보_관계_두판독.jsonl"


def read(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def rel(kind, wide, narrow):
    return {"관계": kind, "넓은담보ID": wide, "넓은담보": None, "좁은담보ID": narrow, "좁은담보": None}


# ---------- 시드 ----------
def test_seed_is_the_two_readings_with_ids_from_the_dictionary():
    dictionary = read(SEED / "hum_표준담보사전.jsonl")
    seed = read(R.RELATIONS_PATH)
    assert R.RELATIONS_PATH == SEED / "표준담보_관계.jsonl"
    assert seed == R.rows_from_names(read(PROPOSAL), dictionary)
    assert len(seed) == 32
    assert all(tuple(r) == R.FIELDS for r in seed)
    assert {r["관계"] for r in seed} == {"포함", "통합"}
    relations = R.load_relations()
    assert len(relations) == 32
    assert relations.check(dictionary) == []
    # 사전에서 쓰는 담보만 잇는다
    used = {r["표준담보ID"] for r in dictionary if r["사용여부"]}
    assert {r[k] for r in seed for k in ("넓은담보ID", "좁은담보ID")} <= used


def test_name_not_in_dictionary_stops():
    dictionary = [{"표준담보ID": "STD_A", "표준담보명": "가"}]
    with pytest.raises(R.RelationError, match="사전에 없는 표준담보명: 나"):
        R.rows_from_names([{"관계": "포함", "넓은담보": "가", "좁은담보": "나"}], dictionary)
    with pytest.raises(R.RelationError, match="포함이나 통합"):
        R.rows_from_names([{"관계": "겹침", "넓은담보": "가", "좁은담보": "가"}], dictionary)


def test_loop_and_bad_rows_stop():
    with pytest.raises(R.RelationError, match="고리"):
        R.Relations([rel("포함", "A", "B"), rel("포함", "B", "C"), rel("통합", "C", "A")])
    with pytest.raises(R.RelationError):
        R.Relations([rel("포함", "A", "A")])
    with pytest.raises(R.RelationError):
        R.Relations([rel("겹침", "A", "B")])


def test_check_reports_ids_and_names_that_do_not_match_the_dictionary():
    relations = R.Relations([{"관계": "포함", "넓은담보ID": "STD_A", "넓은담보": "가", "좁은담보ID": "STD_X", "좁은담보": "엑스"},
                             {"관계": "포함", "넓은담보ID": "STD_A", "넓은담보": "다른 이름", "좁은담보ID": "STD_B", "좁은담보": "나"}])
    problems = relations.check([{"표준담보ID": "STD_A", "표준담보명": "가"}, {"표준담보ID": "STD_B", "표준담보명": "나"}])
    assert problems == ["STD_X: 사전에 없음", "STD_A: 줄의 이름 '다른 이름', 사전의 이름 '가'"]


# ---------- 따라가기 ----------
def test_include_is_followed_through_skipped_steps():
    # 뇌혈관질환 ⊃ 뇌졸중 ⊃ 뇌출혈 꼴
    r = R.Relations([rel("포함", "CEREBRO", "STROKE"), rel("포함", "STROKE", "HEMO")])
    assert r.ancestors("HEMO") == {"STROKE", "CEREBRO"}
    assert r.descendants("CEREBRO") == {"STROKE", "HEMO"}
    c = r.cover("HEMO", {"CEREBRO"})
    assert (c.kind, c.via) == (R.BROADER, ("CEREBRO",))
    assert c.held


def test_seed_chain_from_brain_heart_down_to_hemorrhage():
    dictionary = {r["표준담보명"]: r["표준담보ID"] for r in read(SEED / "hum_표준담보사전.jsonl")}
    r = R.load_relations()
    hemo, top = dictionary["뇌출혈 진단비"], dictionary["뇌·심장질환 진단비"]
    assert r.cover(hemo, {top}).kind == R.BROADER
    assert {dictionary[n] for n in ("뇌졸중 진단비", "뇌혈관질환 진단비", "뇌·심장질환 진단비")} <= r.ancestors(hemo)
    # 통합 담보를 부분 담보 둘로 채운다
    union = dictionary["항암방사선·약물치료비(통합)"]
    parts = {dictionary["항암방사선치료비"], dictionary["항암약물치료비"]}
    c = r.cover(union, parts)
    assert (c.kind, c.partial, set(c.via)) == (R.PARTS, False, parts)
    # 통합 담보를 가지면 부분 담보의 좁은 담보(표적항암약물허가치료비)까지 덮는다
    assert r.cover(dictionary["표적항암약물허가치료비"], {union}).kind == R.BROADER


# ---------- 덮임 네 갈래 ----------
@pytest.fixture()
def rels():
    return R.Relations([
        rel("통합", "U", "P1"), rel("통합", "U", "P2"), rel("통합", "U", "P3"),   # U = P1 + P2 + P3
        rel("포함", "W", "P1"),                                                  # P1은 W에도 든다
        rel("포함", "U", "S"),                                                   # U는 통합 담보이면서 S를 포함한다
        rel("포함", "BIG", "SMALL"),
    ])


def test_same(rels):
    c = rels.cover("U", {"U", "P1"})
    assert (c.kind, c.via, c.partial) == (R.SAME, ("U",), False)


def test_broader_through_include_or_union(rels):
    assert rels.cover("SMALL", {"BIG"}).kind == R.BROADER
    assert rels.cover("P2", {"U"}).via == ("U",)                       # 통합 담보를 가지면 부분 담보를 덮는다
    assert rels.cover("S", {"U"}).kind == R.BROADER                   # 같은 담보가 포함의 넓은 담보이기도 하다
    assert rels.cover("P1", {"W"}).via == ("W",)


def test_parts_all_or_some(rels):
    c = rels.cover("U", {"P1", "P2", "P3"})
    assert (c.kind, c.partial, c.missing) == (R.PARTS, False, ())
    # 부분 담보 하나(P1)는 그것을 포함하는 W로 덮인다
    c = rels.cover("U", {"W", "P2", "P3"})
    assert (c.kind, c.partial, set(c.via)) == (R.PARTS, False, {"W", "P2", "P3"})
    c = rels.cover("U", {"P2"})
    assert (c.kind, c.partial, c.missing, c.via) == (R.PARTS, True, ("P1", "P3"), ("P2",))
    assert c.held


def test_none_keeps_narrower_held(rels):
    c = rels.cover("BIG", {"SMALL"})
    assert (c.kind, c.narrower) == (R.NONE, ("SMALL",))
    assert not c.held
    # 포함 쪽 좁은 담보(S)만 있으면 통합 담보 U를 덮지 못한다
    c = rels.cover("U", {"S"})
    assert (c.kind, c.narrower) == (R.NONE, ("S",))
    assert rels.cover("X", set()).kind == R.NONE


def test_missing_file_means_no_relations(tmp_path):
    r = R.load_relations(tmp_path / "없음.jsonl")
    assert len(r) == 0
    assert r.cover("A", {"B"}).kind == R.NONE
