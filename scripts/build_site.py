"""data/snapshot의 사본으로 판단 화면(site/index.html)을 만든다.

    python scripts/build_site.py
    python scripts/build_site.py --snapshot data/snapshot --out site/index.html

만든 파일은 하나뿐이고, 인터넷 없이 파일을 바로 열어도 동작한다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from postlife.site.build import build_site  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="사본 자료로 판단 화면 HTML을 만든다")
    parser.add_argument("--snapshot", type=Path, default=ROOT / "data" / "snapshot")
    parser.add_argument("--out", type=Path, default=ROOT / "site" / "index.html")
    args = parser.parse_args()
    info = build_site(args.snapshot, args.out)
    print(f"만든 파일: {info['out']} ({info['bytes'] / 1024:.0f} KB)")
    print(f"자료 기준 시각: {info['snapshot_at']} · 종형 {info['variants']}개 · 급부 {info['benefits']}줄 · 작업 기록 {info['logs']}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
