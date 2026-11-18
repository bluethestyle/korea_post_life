"""시장 소식 수집 실행.

비밀값이 없으면 아무것도 하지 않고 끝낸다(저장소를 처음 만든 직후에도 예약 실행이 실패하지 않게).
  GEMINI_API_KEY                Gemini API 키
  GOOGLE_SERVICE_ACCOUNT_JSON   서비스 계정 키(JSON 전체)
  SPREADSHEET_ID                정본 시트 ID

시트 없이 흐름만 확인하려면: python scripts/collect_trends.py --dry-run --max-queries 1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife import collect  # noqa: E402
from postlife.gemini import Gemini  # noqa: E402
from postlife.sheets_io import MemoryBackend, RestBackend, SheetStore  # noqa: E402
from postlife.snapshot import KST  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="시트에 쓰지 않는다")
    p.add_argument("--weekday", type=int, choices=range(7), help="월=0. 지정하지 않으면 오늘(한국 시간)")
    p.add_argument("--max-queries", type=int, help="검색 질의 수 상한")
    p.add_argument("--lookback-days", type=int, help="수집 구간 길이. 처음 자료를 채울 때만 넓힌다")
    p.add_argument("--report", type=Path, help="실행 결과를 JSON으로 저장할 경로")
    args = p.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY가 없어 건너뜁니다.")
        return 0
    has_sheet = bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") and os.environ.get("SPREADSHEET_ID"))
    if has_sheet:
        backend = RestBackend.from_env()
    elif args.dry_run:
        backend = MemoryBackend()
    else:
        print("시트 접속 정보가 없어 건너뜁니다. 흐름만 보려면 --dry-run을 붙이세요.")
        return 0

    report = collect.run(
        Gemini(),
        SheetStore(backend),
        now=datetime.now(KST),
        weekday=args.weekday,
        dry_run=args.dry_run,
        max_queries=args.max_queries,
        **({"lookback_days": args.lookback_days} if args.lookback_days else {}),
    )
    print(f"수집 구간 {report.window[0]} ~ {report.window[1]}, 질의 {report.queries}건"
          f"(실패 {len(report.failed_queries)}건)")
    print(f"추출 {report.extracted}건 → 구간 밖 {report.out_of_window}, 반려 {report.rejected}, "
          f"중복 {report.duplicates}, 기록 {len(report.written)}(그중 검토 대기 {report.held})")
    print("모델별 호출 수:", report.calls)
    for row in report.written:
        print(f"- {row['발표일자']} [{row['기관코드']}/{row['분류유형']}] {row['핵심요약'][:60]} ({row['판정확률']})")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if report.queries and len(report.failed_queries) == report.queries else 0


if __name__ == "__main__":
    sys.exit(main())
