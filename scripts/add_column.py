"""스키마에 열을 더했을 때 시트의 머리행과 기존 행에 빈칸을 끼워 넣는다. 한 번만 실행한다.

  python scripts/add_column.py --tab sys_급부 --column 감액예외

시트의 머리행이 "새 스키마에서 그 열만 뺀 것"과 같을 때만 고친다. 이미 들어가 있으면 아무것도 하지 않는다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.schema import TABS  # noqa: E402
from postlife.sheets_io import RestBackend  # noqa: E402


def widen(values: list[list], header: list[str], column: str) -> list[list] | None:
    """머리행에 column을 끼운 새 값. 이미 들어가 있으면 None. 머리행이 예상과 다르면 ValueError."""
    have = [str(h) for h in values[0]] if values else []
    if have == header:
        return None
    at = header.index(column)
    if have != header[:at] + header[at + 1:]:
        raise ValueError(f"머리행이 예상과 다릅니다. 시트={have}")
    out = [list(header)]
    for row in values[1:]:
        row = list(row) + [""] * (len(have) - len(row))
        out.append(row[:at] + [""] + row[at:])
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tab", required=True)
    p.add_argument("--column", required=True)
    args = p.parse_args()
    backend = RestBackend.from_env()
    new = widen(backend.get([args.tab])[args.tab], list(TABS[args.tab].header), args.column)
    if new is None:
        print(f"{args.tab}: 이미 {args.column} 열이 있습니다.")
        return 0
    backend.overwrite(args.tab, new)
    print(f"{args.tab}: {args.column} 열을 넣었습니다. 행 {len(new) - 1}개.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
