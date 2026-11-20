"""스키마에 열을 더했을 때 시트의 머리행과 기존 행에 빈칸을 끼워 넣는다. 한 번만 실행한다.

  python scripts/add_column.py --tab sys_급부 --column 감액예외
  python scripts/add_column.py --tab sys_상품종형 --column 고지중대질병목록,고지소견범위   # 여러 열을 한 번에

--column은 여러 번 주거나 쉼표(또는 공백)로 이어 줄 수 있다. 시트의 머리행이 "새 스키마에서 넣을 열들만 뺀 것"과 같을 때만
고친다. 넣을 열 가운데 이미 들어가 있는 열은 그대로 두고 빠진 열만 넣는다. 모두 들어가 있으면 아무것도 하지 않는다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.schema import TABS  # noqa: E402


def widen(values: list[list], header: list[str], columns: str | Sequence[str]) -> list[list] | None:
    """머리행에 columns를 끼운 새 값. 이미 모두 들어가 있으면 None.

    스키마에 없는 열 이름이거나, 시트 머리행이 "스키마에서 빠진 열만 뺀 것"과 다르면 ValueError.
    머리행 밖 칸에 적힌 메모는 행 끝에 그대로 둔다.
    """
    columns = [columns] if isinstance(columns, str) else list(columns)
    unknown = [c for c in columns if c not in header]
    if unknown or not columns:
        raise ValueError(f"스키마에 없는 열 이름: {unknown or '(없음)'}")
    have = [str(h) for h in values[0]] if values else []
    missing = [c for c in columns if c not in have]
    if not missing and have == header:
        return None
    expected = [h for h in header if h not in missing]
    if have != expected:
        raise ValueError(f"머리행이 예상과 다릅니다. 시트={have}")
    at = {name: i for i, name in enumerate(have)}
    out = [list(header)]
    for row in values[1:]:
        row = list(row) + [""] * (len(have) - len(row))
        out.append([row[at[h]] if h in at else "" for h in header] + row[len(have):])
    return out


def split_columns(raw: list[str]) -> list[str]:
    """--column 값들을 쉼표와 공백으로 나눈다. 같은 이름은 한 번만 남긴다."""
    out: list[str] = []
    for arg in raw:
        for name in re.split(r"[,\s]+", arg):
            if name and name not in out:
                out.append(name)
    return out


def main(argv: list[str] | None = None, backend: Any = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tab", required=True)
    p.add_argument("--column", action="append", required=True,
                   help="넣을 열 이름. 여러 번 주거나 쉼표로 이어 준다")
    args = p.parse_args(argv)
    if args.tab not in TABS:
        print(f"스키마에 없는 탭: {args.tab}")
        return 2
    columns = split_columns(args.column)
    if backend is None:
        from postlife.sheets_io import RestBackend
        backend = RestBackend.from_env()
    values = backend.get([args.tab])[args.tab]
    try:
        new = widen(values, list(TABS[args.tab].header), columns)
    except ValueError as e:
        print(f"{args.tab}: {e}")
        return 1
    if new is None:
        print(f"{args.tab}: 이미 {', '.join(columns)} 열이 있습니다.")
        return 0
    have = {str(h) for h in values[0]} if values else set()
    added = [c for c in columns if c not in have]
    backend.overwrite(args.tab, new)
    kept = [c for c in columns if c in have]
    print(f"{args.tab}: {', '.join(added)} 열을 넣었습니다. 행 {len(new) - 1}개."
          + (f" 이미 있던 {', '.join(kept)} 열은 그대로 둠." if kept else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
