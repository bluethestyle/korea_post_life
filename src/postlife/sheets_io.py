"""구글 시트 정본 읽기·쓰기.

규칙 (docs/planning.md 5.4)
- 쓸 때는 RAW, 읽을 때는 서식 없는 값으로 받는다.
- 행 단위로 호출하지 않고 탭 단위로 한꺼번에 처리한다.
- 상품 하나만 다시 추출할 때 그 종형의 행만 걷어내고 새 행을 합친다.
- 누적 탭은 다시 쓰지 않고 끝에 덧붙인다.
"""
from __future__ import annotations

import json
import os
from typing import Any, Iterable, Protocol

from .schema import TABS, Tab

Row = dict[str, Any]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
API = "https://sheets.googleapis.com/v4/spreadsheets"


class Backend(Protocol):
    def get(self, tabs: list[str]) -> dict[str, list[list[Any]]]: ...
    def overwrite(self, tab: str, values: list[list[Any]]) -> None: ...
    def append(self, tab: str, values: list[list[Any]]) -> None: ...


class MemoryBackend:
    """시험용. 시트를 메모리에 흉내 낸다."""

    def __init__(self, data: dict[str, list[list[Any]]] | None = None):
        self.data = {name: [list(tab.header)] for name, tab in TABS.items()}
        for name, values in (data or {}).items():
            self.data[name] = [list(r) for r in values]
        self.calls: list[tuple[str, str]] = []

    def get(self, tabs: list[str]) -> dict[str, list[list[Any]]]:
        self.calls.append(("get", ",".join(tabs)))
        return {t: [list(r) for r in self.data[t]] for t in tabs}

    def overwrite(self, tab: str, values: list[list[Any]]) -> None:
        self.calls.append(("overwrite", tab))
        self.data[tab] = [list(r) for r in values]

    def append(self, tab: str, values: list[list[Any]]) -> None:
        self.calls.append(("append", tab))
        self.data[tab].extend(list(r) for r in values)


class RestBackend:
    """서비스 계정으로 Sheets API를 호출한다."""

    def __init__(self, spreadsheet_id: str, session: Any):
        self.spreadsheet_id = spreadsheet_id
        self.session = session

    @classmethod
    def from_env(cls) -> "RestBackend":
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        return cls(os.environ["SPREADSHEET_ID"], AuthorizedSession(creds))

    def _url(self, suffix: str) -> str:
        return f"{API}/{self.spreadsheet_id}/{suffix}"

    def _check(self, resp: Any) -> dict:
        if resp.status_code >= 400:
            raise RuntimeError(f"Sheets API {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    def get(self, tabs: list[str]) -> dict[str, list[list[Any]]]:
        params = [("ranges", f"'{t}'") for t in tabs]
        params += [("valueRenderOption", "UNFORMATTED_VALUE"), ("majorDimension", "ROWS")]
        body = self._check(self.session.get(self._url("values:batchGet"), params=params))
        ranges = body.get("valueRanges", [])
        return {t: vr.get("values", []) for t, vr in zip(tabs, ranges)}

    def overwrite(self, tab: str, values: list[list[Any]]) -> None:
        self._check(self.session.post(self._url("values:batchClear"), json={"ranges": [f"'{tab}'"]}))
        self._check(
            self.session.post(
                self._url("values:batchUpdate"),
                json={
                    "valueInputOption": "RAW",
                    "data": [{"range": f"'{tab}'!A1", "values": values}],
                },
            )
        )

    def append(self, tab: str, values: list[list[Any]]) -> None:
        self._check(
            self.session.post(
                self._url(f"values/'{tab}'!A1:append"),
                params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                json={"values": values},
            )
        )


def _to_cell(value: Any) -> Any:
    return "" if value is None else value


def _from_cell(value: Any) -> Any:
    return None if value == "" else value


def rows_to_values(tab: Tab, rows: Iterable[Row]) -> list[list[Any]]:
    unknown = {k for r in rows for k in r} - set(tab.header) if rows else set()
    if unknown:
        raise ValueError(f"{tab.name}: 정의되지 않은 열 {sorted(unknown)}")
    return [[_to_cell(r.get(c)) for c in tab.header] for r in rows]


def values_to_rows(tab: Tab, values: list[list[Any]]) -> list[Row]:
    if not values:
        return []
    header = [str(h) for h in values[0]]
    if header != tab.header:
        raise ValueError(f"{tab.name}: 머리행이 정의와 다릅니다. 시트={header}")
    rows = []
    for raw in values[1:]:
        if not any(v != "" for v in raw):
            continue
        padded = list(raw) + [""] * (len(header) - len(raw))
        rows.append({h: _from_cell(v) for h, v in zip(header, padded)})
    return rows


def merge_replace(
    existing: dict[str, list[Row]], new: dict[str, list[Row]], variant_ids: set[str]
) -> dict[str, list[Row]]:
    """지정한 종형의 기존 행만 걷어내고 새 행을 합친다.

    하위 탭에는 종형ID 열이 없으므로 종형ID → 특약ID → 급부ID 사슬로 찾는다.
    existing에는 replace 탭 전체가 들어 있어야 한다.
    """
    replace_tabs = [n for n, t in TABS.items() if t.mode == "replace"]
    missing = [n for n in replace_tabs if n not in existing]
    if missing:
        raise ValueError(f"기존 데이터에 빠진 탭: {missing}")

    old_riders = {r["특약ID"] for r in existing["sys_특약"] if r["종형ID"] in variant_ids}
    old_benefits = {r["급부ID"] for r in existing["sys_급부"] if r["특약ID"] in old_riders}
    owned = {"종형ID": variant_ids, "특약ID": old_riders, "급부ID": old_benefits}

    merged: dict[str, list[Row]] = {}
    for name in replace_tabs:
        tab = TABS[name]
        kept = [r for r in existing[name] if r[tab.parent] not in owned[tab.parent]]
        added = list(new.get(name, []))
        keys = [r[tab.key] for r in kept + added]
        dup = {k for k in keys if keys.count(k) > 1}
        if dup:
            raise ValueError(f"{name}: 기본키 중복 {sorted(dup)[:5]}")
        merged[name] = sorted(kept + added, key=lambda r: str(r[tab.key]))
    return merged


class SheetStore:
    def __init__(self, backend: Backend):
        self.backend = backend

    def read(self, tabs: list[str] | None = None) -> dict[str, list[Row]]:
        names = tabs or list(TABS)
        raw = self.backend.get(names)
        return {n: values_to_rows(TABS[n], raw.get(n, [])) for n in names}

    def write_tab(self, name: str, rows: list[Row]) -> None:
        tab = TABS[name]
        self.backend.overwrite(name, [tab.header] + rows_to_values(tab, rows))

    def append(self, name: str, rows: list[Row]) -> None:
        tab = TABS[name]
        if tab.mode != "append" and name != "hum_담보매핑":
            raise ValueError(f"{name}은 덧붙이는 탭이 아닙니다")
        if rows:
            self.backend.append(name, rows_to_values(tab, rows))

    def replace_variants(self, new: dict[str, list[Row]], variant_ids: set[str]) -> None:
        """지정한 종형을 다시 추출한 결과로 바꾼다. 다른 상품의 행은 그대로 둔다."""
        replace_tabs = [n for n, t in TABS.items() if t.mode == "replace"]
        merged = merge_replace(self.read(replace_tabs), new, variant_ids)
        for name in replace_tabs:
            self.write_tab(name, merged[name])
