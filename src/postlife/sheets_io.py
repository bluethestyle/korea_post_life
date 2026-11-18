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
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterable, Protocol

from .schema import TABS, Tab

Row = dict[str, Any]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
API = "https://sheets.googleapis.com/v4/spreadsheets"
RETRY_STATUS = {429, 500, 502, 503, 504}
RETRIES = 3
HUMAN_REVIEWED = {"승인", "수정", "오류"}   # 담당자가 손댄 매핑 행. 배치는 읽기만 한다.
_EPOCH = date(1899, 12, 30)                  # 시트 날짜 일련번호의 기준일
_LOOSE_DATE = re.compile(r"^(\d{4})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})\.?$")


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

    def __init__(self, spreadsheet_id: str, session: Any, sleep: Callable[[float], None] = time.sleep):
        self.spreadsheet_id = spreadsheet_id
        self.session = session
        self.sleep = sleep

    @classmethod
    def from_env(cls) -> "RestBackend":
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        return cls(os.environ["SPREADSHEET_ID"], AuthorizedSession(creds))

    def _url(self, suffix: str) -> str:
        return f"{API}/{self.spreadsheet_id}/{suffix}"

    def _request(self, method: str, suffix: str, **kwargs: Any) -> dict:
        """429와 5xx는 간격을 늘려 가며 다시 시도한다."""
        for attempt in range(RETRIES + 1):
            resp = getattr(self.session, method)(self._url(suffix), **kwargs)
            if resp.status_code < 400:
                return resp.json()
            if resp.status_code not in RETRY_STATUS or attempt == RETRIES:
                raise RuntimeError(f"Sheets API {resp.status_code}: {resp.text[:500]}")
            self.sleep(5 * 2 ** attempt)
        raise AssertionError("도달하지 않음")

    def get(self, tabs: list[str]) -> dict[str, list[list[Any]]]:
        params = [("ranges", f"'{t}'") for t in tabs]
        params += [("valueRenderOption", "UNFORMATTED_VALUE"), ("majorDimension", "ROWS")]
        body = self._request("get", "values:batchGet", params=params)
        ranges = body.get("valueRanges", [])
        return {t: vr.get("values", []) for t, vr in zip(tabs, ranges)}

    def overwrite(self, tab: str, values: list[list[Any]]) -> None:
        """새 값을 먼저 쓰고, 그 아래 남은 행만 지운다.

        먼저 비우고 쓰면 쓰기가 실패했을 때 머리행과 기존 자료가 사라진다.
        """
        self._request(
            "post",
            "values:batchUpdate",
            json={"valueInputOption": "RAW", "data": [{"range": f"'{tab}'!A1", "values": values}]},
        )
        last = _column_letter(max(len(r) for r in values))
        self._request(
            "post", "values:batchClear", json={"ranges": [f"'{tab}'!A{len(values) + 1}:{last}"]}
        )

    def append(self, tab: str, values: list[list[Any]]) -> None:
        self._request(
            "post",
            f"values/'{tab}'!A1:append",
            params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
            json={"values": values},
        )


def _column_letter(n: int) -> str:
    """1 → A, 26 → Z, 27 → AA."""
    out = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def _to_cell(value: Any) -> Any:
    return "" if value is None else value


def _from_cell(value: Any, kind: str = "str") -> Any:
    """시트에서 읽은 값을 열 정의의 자료형에 맞춘다.

    담당자가 화면에서 직접 고친 칸은 시트가 날짜·숫자로 바꿔 저장한다.
    날짜는 일련번호로, 숫자처럼 보이는 문자열은 숫자로 돌아오므로 여기서 되돌린다.
    """
    if value == "" or value is None:
        return None
    number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "date":
        if number:
            return (_EPOCH + timedelta(days=int(value))).isoformat()
        m = _LOOSE_DATE.match(str(value).strip())
        if m:
            return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    elif kind == "datetime":
        if number:
            moment = datetime(1899, 12, 30) + timedelta(days=float(value))
            return moment.replace(microsecond=0).isoformat() + "+09:00"
    elif kind == "str":
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if number:
            return str(int(value)) if float(value).is_integer() else str(value)
    elif kind == "int":
        if isinstance(value, float) and value.is_integer():
            return int(value)
    elif kind == "bool":
        if isinstance(value, str) and value.strip().upper() in ("TRUE", "FALSE"):
            return value.strip().upper() == "TRUE"
    return value


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
        rows.append({c.name: _from_cell(v, c.type) for c, v in zip(tab.columns, padded)})
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


def merge_mapping(existing: list[Row], proposed: list[Row]) -> list[Row]:
    """hum_담보매핑에 배치의 새 추천을 합친다 (docs/planning.md 5.4).

    - 담당자가 손댄 행(검토상태가 승인·수정·오류)은 그대로 둔다.
    - 그 밖의 행은 새 추천으로 바꾸되 담당자메모는 지키고, 새 급부는 추가한다.
    - 이번에 추천이 오지 않은 기존 행은 지우지 않는다.
    """
    tab = TABS["hum_담보매핑"]
    keys = [r[tab.key] for r in proposed]
    dup = {k for k in keys if keys.count(k) > 1}
    if dup:
        raise ValueError(f"hum_담보매핑: 추천에 급부ID 중복 {sorted(dup)[:5]}")
    merged = {r[tab.key]: dict(r) for r in existing}
    for new in proposed:
        old = merged.get(new[tab.key])
        if old is not None and old.get("검토상태") in HUMAN_REVIEWED:
            continue
        row = dict(new)
        if old is not None and old.get("담당자메모"):
            row["담당자메모"] = old["담당자메모"]
        merged[new[tab.key]] = row
    return sorted(merged.values(), key=lambda r: str(r[tab.key]))


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
        if tab.mode != "append":
            raise ValueError(f"{name}은 덧붙이는 탭이 아닙니다")
        if rows:
            self.backend.append(name, rows_to_values(tab, rows))

    def replace_variants(self, new: dict[str, list[Row]], variant_ids: set[str]) -> None:
        """지정한 종형을 다시 추출한 결과로 바꾼다. 다른 상품의 행은 그대로 둔다."""
        replace_tabs = [n for n, t in TABS.items() if t.mode == "replace"]
        merged = merge_replace(self.read(replace_tabs), new, variant_ids)
        for name in replace_tabs:
            self.write_tab(name, merged[name])

    def upsert_mapping(self, proposed: list[Row]) -> None:
        """담보 매핑 추천을 반영한다. 담당자가 확정한 행은 건드리지 않는다."""
        existing = self.read(["hum_담보매핑"])["hum_담보매핑"]
        self.write_tab("hum_담보매핑", merge_mapping(existing, proposed))
