"""scripts/sync_variant_attrs.py: 설정의 고지 열만 시트의 기존 종형 행에 맞추고, 다른 칸, 다른 행, 다른 탭은 그대로 두는지 본다.

시트는 메모리로 흉내 낸다(MemoryBackend). 종형 행은 저장소의 대상 설정으로 배치와 같은 식(variants.build)으로 만든다.
"""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

from postlife.extract import variants as VV
from postlife.schema import TABS
from postlife.sheets_io import MemoryBackend, rows_to_values

ROOT = Path(__file__).resolve().parents[1]
TAB = "sys_상품종형"
HEADER = TABS[TAB].header
NEW = ("고지중대질병목록", "고지소견범위")
ORGS = ("epost", "hanwha", "samsungfire")
OTHER = "OTHERORG_X1_000000"          # 설정에 없는 종형
LEFT_OUT = "간편가입형(10년)"           # 시트에 아직 없는 종형


def load_script():
    spec = importlib.util.spec_from_file_location("sync_variant_attrs", ROOT / "scripts/sync_variant_attrs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = load_script()


def targets(org):
    return json.loads((ROOT / f"data/targets/{org}.json").read_text(encoding="utf-8"))


def built_rows():
    rows = []
    for org in ORGS:
        t = targets(org)
        codes = {v["공시상품코드"] for p in t["상품"] for v in p["종형"]}
        index = [{"기관": t["기관코드"], "상품코드": c, "상품명": f"시험 {c}", "판매시작일": "2026-01-01", "판매종료일": None,
                  "문서": "상품요약서", "해시": f"h{c}", "저장이름": c, "쪽수": 1} for c in codes]
        found, problems = VV.build(t, index)
        assert problems == []
        rows += [v.row for v in found]
    return rows


def sheet():
    """열을 막 넣은 뒤의 시트: 새 두 열은 빈칸이고, 한화생명 간편가입형(10년)은 아직 시트에 없다.

    배치가 쓰지 않은 꼴의 칸(날짜 일련번호, 글자로 적힌 TRUE, 머리행 밖 메모)과 설정에 없는 종형의 행을 넣어, 그 칸들이 한 글자도
    바뀌지 않는지 본다."""
    rows = [dict(r, **{c: None for c in NEW}) for r in built_rows() if r["종형명"] != LEFT_OUT]
    other = dict(rows[0], 종형ID=OTHER, 기관코드="OTHERORG", 공시상품코드="X1", 고지중대질병목록="가, 나", 고지중대질병수=2,
                 고지소견범위="서면")
    values = [list(HEADER)] + rows_to_values(TABS[TAB], rows + [other])
    start, waiver = HEADER.index("적용시작일"), HEADER.index("납입면제적용")
    values[1][start] = 46023                    # 담당자가 고쳐 시트가 날짜로 바꿔 둔 칸 (2026-01-01)
    values[2][waiver] = "TRUE"
    values[3] = values[3] + ["메모"]
    while values[4] and values[4][-1] == "":    # 끝의 빈칸을 돌려주지 않는 시트의 꼴
        values[4].pop()
    riders = [TABS["sys_특약"].header, ["T1", rows[0]["종형ID"], "K", "주계약", "주계약", False, "", "", "", ""]]
    return {TAB: values, "sys_특약": riders}


def by_id(values):
    key = HEADER.index("종형ID")
    return {r[key]: r for r in values[1:]}


def run(backend, *args, tmp_path=None):
    argv = list(args)
    if tmp_path is not None:
        argv += ["--result", str(tmp_path / "result.json")]
    return S.main(argv, backend)


def test_only_the_disclosure_cells_of_listed_variants_change(tmp_path):
    before = sheet()
    backend = MemoryBackend(copy.deepcopy(before))
    assert run(backend, tmp_path=tmp_path) == 0
    after = backend.data
    assert after["sys_특약"] == before["sys_특약"]                                 # 다른 탭은 그대로
    assert [c for c in backend.calls if c[0] == "overwrite"] == [("overwrite", TAB)]
    old, new = by_id(before[TAB]), by_id(after[TAB])
    assert list(new) == list(old)                                                  # 행 순서와 수가 같고 새 종형은 만들지 않는다
    assert new[OTHER] == old[OTHER]                                                # 설정에 없는 종형은 그대로
    want = {}
    for org in ORGS:
        want.update(VV.attributes(targets(org)))
    at = {c: HEADER.index(c) for c in VV.OPTIONAL}
    changed = 0
    for vid, row in new.items():
        if vid == OTHER:
            continue
        for column, i in at.items():
            value = want[vid][column]
            assert row[i] == ("" if value is None else value), (vid, column)
        # 고지 열 밖의 칸은 시트에서 읽은 값 그대로다(날짜 일련번호, 글자 TRUE, 메모, 짧은 행 포함)
        rest = [v for i, v in enumerate(old[vid]) if i not in at.values()]
        assert [v for i, v in enumerate(row) if i not in at.values()][:len(rest)] == rest, vid
        assert all(v == "" for v in row[len(old[vid]):]), vid
        changed += any(row[i] != (old[vid][i] if i < len(old[vid]) else "") for i in at.values())
    assert changed == sum(1 for v in want.values() if v["고지중대질병목록"]) - 1   # 간편심사 종형마다 (시트에 없는 하나 빼고)
    body = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert body["시트에 씀"] is True and {c["열"] for c in body["바꾼 칸"]} == set(NEW)
    assert body["시트에 없는 종형"] == [vid for vid in want if vid not in old]
    assert len(body["시트에 없는 종형"]) == 1
    # 다시 돌리면 바꿀 칸이 없어 쓰지 않는다
    calls = len(backend.calls)
    assert run(backend) == 0
    assert [c for c in backend.calls[calls:] if c[0] == "overwrite"] == []


def test_dry_run_does_not_write(tmp_path):
    before = sheet()
    backend = MemoryBackend(copy.deepcopy(before))
    assert run(backend, "--dry-run", tmp_path=tmp_path) == 0
    assert {k: backend.data[k] for k in before} == before and not [c for c in backend.calls if c[0] == "overwrite"]
    body = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert body["시트에 씀"] is False and body["바꾼 칸"]


def test_org_option_limits_the_rows():
    before = sheet()
    backend = MemoryBackend(copy.deepcopy(before))
    assert run(backend, "--org", "hanwha") == 0
    old, new = by_id(before[TAB]), by_id(backend.data[TAB])
    differ = {vid for vid in new if new[vid] != old[vid]}
    assert differ and all(vid.startswith("HANWHALIFE_") for vid in differ)


def test_stops_before_the_columns_are_on_the_sheet():
    before = sheet()
    keep = [i for i, c in enumerate(HEADER) if c not in NEW]
    narrow = {TAB: [[r[i] for i in keep if i < len(r)] for r in before[TAB]]}
    backend = MemoryBackend(copy.deepcopy(narrow))
    assert run(backend) == 1
    assert backend.data[TAB] == narrow[TAB] and not [c for c in backend.calls if c[0] == "overwrite"]


def test_a_bad_value_in_the_settings_is_not_written(monkeypatch):
    before = sheet()
    backend = MemoryBackend(copy.deepcopy(before))
    real = VV.attributes

    def broken(t):
        out = real(t)
        for attrs in out.values():
            if attrs["고지소견범위"]:
                attrs["고지소견범위"] = "진료기록부"          # 허용값이 아님
        return out

    monkeypatch.setattr(S.variants, "attributes", broken)
    assert run(backend) == 1
    assert {k: backend.data[k] for k in before} == before and not [c for c in backend.calls if c[0] == "overwrite"]


def test_plan_refuses_a_variant_listed_twice_on_the_sheet():
    values = sheet()[TAB]
    values.append(list(values[1]))
    with pytest.raises(ValueError):
        S.plan(values, S.wanted([targets(o) for o in ORGS]))
