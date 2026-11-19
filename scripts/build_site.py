"""data/snapshot의 사본으로 판단 화면(site/index.html)을 만든다.

    python scripts/build_site.py
    python scripts/build_site.py --snapshot data/snapshot --out site/index.html
    python scripts/build_site.py --previous <지난주 사본 폴더>

만든 파일은 하나뿐이고, 인터넷 없이 파일을 바로 열어도 동작한다.
--previous를 주면 화면 1에 대표 조건에서 우열 표시가 바뀐 표준담보를 싣는다(주지 않으면 그 묶음은 비교하지 않았다고 적는다).
해설 글(data/site_text/commentary.json)에서 검사에 걸려 버린 글은 "경고:"로 적는다.
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
    parser.add_argument("--previous", type=Path, default=None, help="지난주 사본 폴더(data/snapshot과 같은 꼴)")
    args = parser.parse_args()
    info = build_site(args.snapshot, args.out, previous_dir=args.previous)
    print(f"만든 파일: {info['out']} ({info['bytes'] / 1024:.0f} KB)")
    print(f"자료 기준 시각: {info['snapshot_at']} · 종형 {info['variants']}개 · 급부 {info['benefits']}줄 · 작업 기록 {info['logs']}건")
    if info["previous_at"]:
        print(f"지난주 사본: {args.previous} (자료 기준 시각 {info['previous_at']})")
    else:
        print("지난주 사본: 없음 (대표 조건의 우열 변화는 비교하지 않음)")
    for warning in info["warnings"]:
        print(f"경고: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
