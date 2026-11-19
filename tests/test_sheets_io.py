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


class FakeResp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body or {}
        self.text = "오류"

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses=None):
        self.sent = []
        self.responses = list(responses or [])

    def _next(self, method, url, **kw):
        self.sent.append((method, url.rsplit("/", 1)[-1], kw))
        return self.responses.pop(0) if self.responses else FakeResp()

    def get(self, url, **kw):
        return self._next("get", url, **kw)

    def post(self, url, **kw):
        return self._next("post", url, **kw)


def test_overwrite_writes_first_then_clears_only_the_rows_below():
    from postlife.sheets_io import RestBackend

    session = FakeSession()
    RestBackend("SHEET", session, sleep=lambda s: None).overwrite("hum_기준값", [["a", "b", "c"], [1, 2, 3]])
    assert [s[1] for s in session.sent] == ["values:batchUpdate", "values:batchClear"]
    assert session.sent[1][2]["json"]["ranges"] == ["'hum_기준값'!A3:C"]

    # 쓰기가 실패하면 지우는 요청은 나가지 않는다. 머리행과 기존 자료가 남는다.
    failing = FakeSession([FakeResp(400)])
    with pytest.raises(RuntimeError):
        RestBackend("SHEET", failing, sleep=lambda s: None).overwrite("hum_기준값", [["a"]])
    assert len(failing.sent) == 1


def test_rest_backend_retries_rate_limit():
    from postlife.sheets_io import RestBackend

    waits = []
    session = FakeSession([FakeResp(429), FakeResp(503), FakeResp(200, {"valueRanges": [{"values": [["x"]]}]})])
    out = RestBackend("SHEET", session, sleep=waits.append).get(["sys_특약"])
    assert out == {"sys_특약": [["x"]]} and waits == [5, 10]


def test_values_edited_by_hand_are_read_back_in_schema_types():
    tab = TABS["hum_기준값"]
    # 담당자가 화면에서 고치면 날짜는 일련번호로, 문자값 "325"는 숫자로 돌아온다
    values = [tab.header, ["K", "대표조건", "간편고지 약칭", "", 325, "", "", 46345]]
    back = values_to_rows(tab, values)[0]
    assert back["적용시작일"] == "2026-11-19" and back["문자값"] == "325"
    loose = values_to_rows(tab, [tab.header, ["K", "대표조건", "이름", 50, "", "", "", "2026. 11. 9"]])[0]
    assert loose["적용시작일"] == "2026-11-09" and loose["수치값"] == 50
    flags = values_to_rows(TABS["hum_표준담보사전"], [TABS["hum_표준담보사전"].header,
                                                 ["S", "암보장", "암진단", "일반암", "진단", 1000, "TRUE"]])[0]
    assert flags["사용여부"] is True


def test_mapping_merge_keeps_what_the_reviewer_decided():
    from postlife.sheets_io import merge_mapping

    def m(key, state, confirmed=None, memo=None, rec="STD_A"):
        return row("hum_담보매핑", 급부ID=key, 추천표준담보ID=rec, 확정표준담보ID=confirmed, 검토상태=state, 담당자메모=memo)

    existing = [m("B1", "승인", "STD_X"), m("B2", "대기", memo="확인 중"), m("B3", "자동확정", "STD_A"), m("B9", "수정", "STD_Z")]
    proposed = [m("B1", "자동확정", "STD_A"), m("B2", "자동확정", "STD_B", rec="STD_B"), m("B3", "대기"), m("B4", "대상외")]
    merged = {r["급부ID"]: r for r in merge_mapping(existing, proposed)}
    assert merged["B1"]["검토상태"] == "승인" and merged["B1"]["확정표준담보ID"] == "STD_X"
    assert merged["B2"]["검토상태"] == "자동확정" and merged["B2"]["담당자메모"] == "확인 중"
    assert merged["B3"]["검토상태"] == "대기"
    assert merged["B4"]["검토상태"] == "대상외" and merged["B9"]["검토상태"] == "수정"
    # 다시 돌려도 행이 늘지 않는다
    again = merge_mapping(list(merged.values()), proposed)
    assert len(again) == 5
    with pytest.raises(ValueError):
        merge_mapping([], [m("B1", "대기"), m("B1", "대기")])


def test_append_is_only_for_cumulative_tabs():
    store = SheetStore(MemoryBackend())
    with pytest.raises(ValueError):
        store.append("hum_담보매핑", [row("hum_담보매핑", 급부ID="B1")])
    store.upsert_mapping([row("hum_담보매핑", 급부ID="B1", 검토상태="대기")])
    store.upsert_mapping([row("hum_담보매핑", 급부ID="B1", 검토상태="자동확정")])
    assert [r["검토상태"] for r in store.read(["hum_담보매핑"])["hum_담보매핑"]] == ["자동확정"]


def test_overwrite_ignores_clear_beyond_the_grid():
    """새 값이 시트 마지막 행까지 차면 그 아래를 지우는 요청은 격자 밖이라 400이 온다. 쓰기는 이미 끝났으므로 넘어간다."""
    from postlife.sheets_io import RestBackend

    calls = []

    class Fake(RestBackend):
        def __init__(self):
            pass

        def _request(self, method, path, **kwargs):
            calls.append(path)
            if path == "values:batchClear":
                raise RuntimeError("Sheets API 400: Range ('sys_특약'!A1020:J) exceeds grid limits. Max rows: 1019")
            return {}

    Fake().overwrite("sys_특약", [["가", "나"], [1, 2]])
    assert calls == ["values:batchUpdate", "values:batchClear"]

    class Broken(Fake):
        def _request(self, method, path, **kwargs):
            if path == "values:batchClear":
                raise RuntimeError("Sheets API 403: 권한 없음")
            return {}

    try:
        Broken().overwrite("sys_특약", [["가"], [1]])
        assert False
    except RuntimeError:
        pass


def test_rows_given_as_a_generator_are_written():
    tab = TABS["sys_특약"]
    rows = [row("sys_특약", 특약ID="T1", 종형ID="V1"), row("sys_특약", 특약ID="T2", 종형ID="V1")]
    values = rows_to_values(tab, (r for r in rows))
    assert [v[0] for v in values] == ["T1", "T2"]
    with pytest.raises(ValueError):
        rows_to_values(tab, (r for r in [{"특약ID": "T", "없는열": 1}]))


def test_note_outside_the_header_columns_does_not_make_a_row():
    tab = TABS["sys_특약"]
    blank = [""] * len(tab.header)
    full = rows_to_values(tab, [row("sys_특약", 특약ID="T1", 종형ID="V1")])[0]
    values = [tab.header, full, blank + ["", "담당자가 옆 칸에 적어 둔 메모"], full[:2] + blank[2:] + ["메모"]]
    back = values_to_rows(tab, values)
    assert [r["특약ID"] for r in back] == ["T1", "T1"]        # 머리글 안쪽이 빈 줄은 행이 아니다. 안쪽에 값이 있는 줄은 읽는다


class FailsOnce(MemoryBackend):
    """정한 탭을 처음 덮어쓸 때 한 번 실패한다."""

    def __init__(self, tab):
        super().__init__()
        self.broken = tab

    def overwrite(self, tab, values):
        if tab == self.broken:
            self.broken = None
            raise RuntimeError("Sheets API 503")
        super().overwrite(tab, values)


def test_rerun_after_a_half_written_replace_leaves_no_orphan_rows():
    backend = FailsOnce("sys_급부")
    store = SheetStore(backend)
    for name, rows in sample().items():
        store.write_tab(name, rows) if name != "sys_급부" else MemoryBackend.overwrite(
            backend, name, [TABS[name].header] + rows_to_values(TABS[name], rows))
    # 다시 뽑았더니 V1의 특약이 다른 ID로 바뀌었다. 특약 탭까지 쓰고 급부 탭에서 실패한다
    new = {"sys_상품종형": [row("sys_상품종형", 종형ID="V1", 공시상품명="상품V1")],
           "sys_특약": [row("sys_특약", 특약ID="V1_T9", 종형ID="V1")],
           "sys_급부": [row("sys_급부", 급부ID="V1_T9_B1", 특약ID="V1_T9")]}
    tabs = ["sys_상품종형", "sys_특약", "sys_급부"]
    with pytest.raises(RuntimeError):
        store.replace_variants(new, {"V1"}, only=tabs)
    half = store.read()
    assert [r["특약ID"] for r in half["sys_특약"]] == ["V1_T9", "V2_T1"]
    assert [r["급부ID"] for r in half["sys_급부"]] == ["V1_T1_B1", "V2_T1_B1"]        # 급부 탭은 옛 행 그대로다

    # 다시 돌리면 특약 탭에서 이미 사라진 옛 특약(V1_T1)의 급부도 걷힌다
    store.replace_variants(new, {"V1"}, only=tabs)
    done = store.read()
    assert [r["급부ID"] for r in done["sys_급부"]] == ["V1_T9_B1", "V2_T1_B1"]
    # 넘기지 않은 탭은 그대로다. 다른 종형의 행은 이름이 비슷해도 건드리지 않는다
    assert [r["보험료행ID"] for r in done["sys_보험료예시"]] == ["V1_T1_P1", "V2_T1_P1"]
    other = sample()
    other["sys_급부"].append(row("sys_급부", 급부ID="V10_T1_B1", 특약ID="V10_T1"))
    merged = merge_replace(other, {}, {"V1"})
    assert [r["급부ID"] for r in merged["sys_급부"]] == ["V10_T1_B1", "V2_T1_B1"]


def test_identical_rows_left_below_a_shortened_tab_do_not_block_the_next_run():
    # 새 값을 쓴 뒤 그 아래 옛 행을 지우지 못하면, 다른 종형의 같은 행이 꼬리에 한 번 더 남는다
    existing = sample()
    existing["sys_특약"].append(dict(existing["sys_특약"][1]))                # V2_T1이 두 번
    merged = merge_replace(existing, {"sys_특약": [row("sys_특약", 특약ID="V1_T9", 종형ID="V1")]}, {"V1"})
    assert [r["특약ID"] for r in merged["sys_특약"]] == ["V1_T9", "V2_T1"]
    # 같은 ID인데 내용이 다르면 어느 쪽이 맞는지 알 수 없으므로 멈춘다
    existing["sys_특약"].append(dict(existing["sys_특약"][1], 원시특약명="다른 이름"))
    with pytest.raises(ValueError):
        merge_replace(existing, {}, {"V1"})


def test_failed_clear_says_old_rows_remain():
    from postlife.sheets_io import RestBackend

    session = FakeSession([FakeResp(200), FakeResp(403)])
    with pytest.raises(RuntimeError, match="옛 행"):
        RestBackend("SHEET", session, sleep=lambda s: None).overwrite("sys_특약", [["가"], [1]])
