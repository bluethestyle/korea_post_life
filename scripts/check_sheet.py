"""시트를 읽기만 해서 (1) 탭마다 머리글이 스키마와 같은지, (2) 내용이 저장소의 사본(data/snapshot)과 어디가 다른지 본다.

머리글 한 칸이 바뀌면 시트를 읽는 모든 실행이 처음 걸린 한 곳만 알리고 멈춘다. 이 점검은 어긋난 칸을 모두 알려 준다.
시트에 쓰지 않는다. 사본을 뜬 뒤 배치나 담당자가 바꾼 행도 "다른 행"으로 나오므로, 실수로 바뀐 칸을 찾는 실마리로 쓴다.

  python scripts/check_sheet.py            # GOOGLE_SERVICE_ACCOUNT_JSON, SPREADSHEET_ID 가 있어야 한다
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from postlife.schema import TABS  # noqa: E402
from postlife.sheets_io import values_to_rows  # noqa: E402
from postlife.snapshot import read_snapshot  # noqa: E402

SHOW = 12       # 탭마다 보여 줄 다른 칸 수


def same(a: Any, b: Any) -> bool:
    if a in ("", None) and b in ("", None):
        return True
    numbers = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (a, b))
    return float(a) == float(b) if numbers else a == b


def inspect(raw: dict[str, list[list[Any]]], snapshot: dict[str, list[dict[str, Any]]]) -> tuple[list[str], bool]:
    """(보고 줄, 머리글이 모두 맞는지). raw 는 탭마다 시트의 값(첫 행이 머리글)."""
    lines: list[str] = []
    headers_ok = True
    for name, tab in TABS.items():
        values = raw.get(name)
        if values is None:
            lines.append(f"- {name}: 시트에 탭이 없음")
            headers_ok = False
            continue
        if not values:
            lines.append(f"- {name}: 빈 탭 (머리글 없음)")
            headers_ok = False
            continue
        header = [str(h) for h in values[0]]
        wrong = [f"{i + 1}번째 칸 '{got}' (스키마는 '{want}')"
                 for i, (got, want) in enumerate(zip(header, tab.header)) if got != want]
        if len(header) != len(tab.header):
            wrong.append(f"칸 수 {len(header)} (스키마는 {len(tab.header)})")
        if wrong:
            headers_ok = False
            lines.append(f"- {name}: 머리글이 다름: " + "; ".join(wrong))
        if len(header) < len(tab.header):
            continue        # 칸이 모자라면 내용을 자리로 맞춰 읽을 수 없다
        # 머리글 글자가 달라도 내용은 자리로 맞춰 읽어 사본과 견준다
        rows = values_to_rows(tab, [tab.header] + [r[:len(tab.header)] for r in values[1:]])
        key = tab.key
        now = {r[key]: r for r in rows}
        old = {r[key]: r for r in snapshot.get(name, [])}
        added, removed = sorted(set(now) - set(old), key=str), sorted(set(old) - set(now), key=str)
        cells = [(k, c, old[k].get(c), now[k].get(c)) for k in now.keys() & old.keys() for c in tab.header
                 if not same(old[k].get(c), now[k].get(c))]
        state = "머리글 맞음" if not wrong else "머리글 다름"
        lines.append(f"- {name}: {state}, 시트 {len(rows)}행, 사본 {len(old)}행, 시트에만 {len(added)}행, 사본에만 {len(removed)}행, "
                     f"값이 다른 칸 {len(cells)}개")
        if len(now) != len(rows):
            lines.append(f"  - 같은 {key} 가 두 번 나오는 행이 {len(rows) - len(now)}개 있음")
        for k, c, before, after in sorted(cells, key=lambda x: (str(x[0]), x[1]))[:SHOW]:
            lines.append(f"  - {k} · {c}: 사본 {before!r} → 시트 {after!r}")
        if len(cells) > SHOW:
            lines.append(f"  - … 그 밖에 {len(cells) - SHOW}칸")
        for label, ids in (("시트에만", added), ("사본에만", removed)):
            if ids:
                lines.append(f"  - {label}: {', '.join(str(i) for i in ids[:5])}" + (f" … 모두 {len(ids)}행" if len(ids) > 5 else ""))
    return lines, headers_ok


def main() -> int:
    if not (os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") and os.environ.get("SPREADSHEET_ID")):
        print("접속 정보가 없어 건너뜁니다.")
        return 0
    from postlife.sheets_io import RestBackend

    raw = RestBackend.from_env().get(list(TABS))
    lines, headers_ok = inspect(raw, read_snapshot(ROOT / "data" / "snapshot"))
    text = ("머리글은 모든 탭이 스키마와 같습니다.\n" if headers_ok else "머리글이 스키마와 다른 탭이 있습니다. 시트를 읽는 실행은 이 상태에서 멈춥니다.\n")
    text += "\n".join(lines) + "\n"
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 시트 점검 (읽기만 함)\n\n" + text)
    return 0 if headers_ok else 1


if __name__ == "__main__":
    sys.exit(main())
