import pytest

from postlife import snapshot
from postlife.schema import TABS
from postlife.sheets_io import MemoryBackend, SheetStore, merge_replace, rows_to_values, values_to_rows


def row(tab, **values):
    base = {c: None for c in TABS[tab].header}
    base.update(values)
    return base


def sample():
    data = {n: [] for n, t in TABS.items() if t.mode == "replace"}
    for v in ("V1", "V2"):
        data["sys_상품종형"].append(row("sys_상품종형", 종형ID=v, 공시상품명=f"상품{v}"))
        data["sys_가입조건"].append(row("sys_가입조건", 조건행ID=f"{v}_C1", 종형ID=v))
        data["sys_특약"].append(row("sys_특약", 특약ID=f"{v}_T1", 종형ID=v))
        data["sys_급부"].append(row("sys_급부", 급부ID=f"{v}_T1_B1", 특약ID=f"{v}_T1"))
        data["sys_보험료예시"].append(row("sys_보험료예시", 보험료행ID=f"{v}_T1_P1", 특약ID=f"{v}_T1"))
        data["sys_결합제약"].append(row("sys_결합제약", 제약ID=f"{v}_R1", 종형ID=v))
        data["sys_급부질병코드"].append(row("sys_급부질병코드", 질병매핑ID=f"{v}_T1_B1_K1", 급부ID=f"{v}_T1_B1"))
    return data


def test_round_trip_keeps_values_as_given():
    tab = TABS["sys_상품종형"]
    rows = [row("sys_상품종형", 종형ID="V1", 간편고지약칭="3.2.5", 공시상품코드="0012", 납입면제적용=False)]
    back = values_to_rows(tab, [tab.header] + rows_to_values(tab, rows))
    assert back[0]["간편고지약칭"] == "3.2.5"
    assert back[0]["공시상품코드"] == "0012"
    assert back[0]["납입면제적용"] is False
    assert back[0]["판매종료일"] is None


def test_unknown_column_and_header_mismatch_are_rejected():
    tab = TABS["sys_특약"]
    with pytest.raises(ValueError):
        rows_to_values(tab, [{"특약ID": "T", "없는열": 1}])
    with pytest.raises(ValueError):
        values_to_rows(tab, [["특약ID", "다른열"]])


def test_replace_touches_only_the_given_variant():
    existing = sample()
    new = {
        "sys_상품종형": [row("sys_상품종형", 종형ID="V1", 공시상품명="새 이름")],
        "sys_특약": [row("sys_특약", 특약ID="V1_T9", 종형ID="V1")],
        "sys_급부": [row("sys_급부", 급부ID="V1_T9_B1", 특약ID="V1_T9")],
    }
    merged = merge_replace(existing, new, {"V1"})
    assert [r["공시상품명"] for r in merged["sys_상품종형"]] == ["새 이름", "상품V2"]
    assert [r["특약ID"] for r in merged["sys_특약"]] == ["V1_T9", "V2_T1"]
    assert [r["급부ID"] for r in merged["sys_급부"]] == ["V1_T9_B1", "V2_T1_B1"]
    # 손자 탭(급부 아래)도 V1 것만 걷힌다
    assert [r["질병매핑ID"] for r in merged["sys_급부질병코드"]] == ["V2_T1_B1_K1"]
    assert [r["보험료행ID"] for r in merged["sys_보험료예시"]] == ["V2_T1_P1"]
    assert [r["조건행ID"] for r in merged["sys_가입조건"]] == ["V2_C1"]


def test_replace_rejects_duplicate_keys():
    existing = sample()
    new = {"sys_특약": [row("sys_특약", 특약ID="V2_T1", 종형ID="V1")]}
    with pytest.raises(ValueError):
        merge_replace(existing, new, {"V1"})


def test_store_reads_once_and_appends_without_rewriting():
    backend = MemoryBackend()
    store = SheetStore(backend)
    store.read()
    assert backend.calls == [("get", ",".join(TABS))]
    with pytest.raises(ValueError):
        store.append("sys_특약", [row("sys_특약", 특약ID="T")])
    store.append("sys_작업로그", [row("sys_작업로그", 로그ID="L1")])
    assert backend.calls[-1] == ("append", "sys_작업로그")
    assert len(backend.data["sys_작업로그"]) == 2


def test_store_replace_variants_end_to_end():
    backend = MemoryBackend()
    store = SheetStore(backend)
    for name, rows in sample().items():
        store.write_tab(name, rows)
    store.replace_variants({"sys_상품종형": [row("sys_상품종형", 종형ID="V1", 공시상품명="개정")]}, {"V1"})
    data = store.read()
    assert {r["종형ID"] for r in data["sys_상품종형"]} == {"V1", "V2"}
    assert [r["특약ID"] for r in data["sys_특약"]] == ["V2_T1"]


def test_snapshot_is_order_independent(tmp_path):
    rows = sample()["sys_특약"]
    a = snapshot.to_jsonl("sys_특약", rows)
    b = snapshot.to_jsonl("sys_특약", list(reversed([dict(reversed(list(r.items()))) for r in rows])))
    assert a == b
    snapshot.write_snapshot({"sys_특약": rows}, tmp_path)
    assert snapshot.read_snapshot(tmp_path)["sys_특약"][0]["특약ID"] == "V1_T1"
    assert "snapshot_at" not in (tmp_path / "sys_특약.jsonl").read_text(encoding="utf-8")
