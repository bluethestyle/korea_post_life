"""시트 정본을 data/snapshot/에 주간 사본으로 뜬다. 비밀값이 없으면 건너뛴다."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from postlife.sheets_io import RestBackend, SheetStore  # noqa: E402
from postlife.snapshot import write_snapshot  # noqa: E402


def main() -> int:
    if not (os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") and os.environ.get("SPREADSHEET_ID")):
        print("시트 접속 정보가 없어 건너뜁니다.")
        return 0
    data = SheetStore(RestBackend.from_env()).read()
    meta = write_snapshot(data, ROOT / "data" / "snapshot")
    for name, count in meta["row_counts"].items():
        print(f"{name}: {count}행")
    return 0


if __name__ == "__main__":
    sys.exit(main())
