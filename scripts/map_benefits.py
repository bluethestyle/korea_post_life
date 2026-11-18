"""시트의 급부를 표준담보 사전에 잇는다 (hum_담보매핑). 이미 행이 있는 급부는 건너뛴다.

  python scripts/map_benefits.py            # 새 급부만
  python scripts/map_benefits.py --remap    # 담당자가 손대지 않은 행을 모두 다시 묻는다
  python scripts/map_benefits.py --dry-run --result out.json
담당자가 승인·수정·오류로 표시한 행은 어느 경우에도 건드리지 않는다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife import config  # noqa: E402
from postlife.extract import mapping  # noqa: E402
from postlife.gemini import Gemini  # noqa: E402
from postlife.sheets_io import RestBackend, SheetStore  # noqa: E402
from postlife.snapshot import KST  # noqa: E402
from postlife.validate import check_rows  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--remap", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="시트에 쓰지 않는다")
    p.add_argument("--prune", action="store_true", help="시트에 더는 없는 급부의 매핑 행을 걷어낸다 (담당자가 손댄 행은 남김)")
    p.add_argument("--result", type=Path)
    args = p.parse_args()
    if not (os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") and os.environ.get("SPREADSHEET_ID")):
        print("접속 정보가 없어 건너뜁니다.")
        return 0
    store = SheetStore(RestBackend.from_env())
    data = store.read(["sys_상품종형", "sys_특약", "sys_급부", "hum_표준담보사전", "hum_담보매핑", "hum_기준값"])
    existing = data["hum_담보매핑"]
    pruned = 0
    if args.prune:
        existing, pruned, orphans = mapping.prune(existing, {b["급부ID"] for b in data["sys_급부"]})
        print(f"급부가 없어진 매핑 행 {pruned}개를 걷어냄" + (f", 담당자가 손댄 행 {len(orphans)}개는 남김" if orphans else ""))
        if pruned and not args.dry_run:
            store.write_tab("hum_담보매핑", existing)
    # 판정 모델의 분당 토큰 한도 때문에 호출 사이를 띄운다
    gemini = Gemini(min_interval={**config.MIN_INTERVAL, config.MODEL_DECIDE: 7.0}, timeout=config.TIMEOUT, max_retries=3)
    result = mapping.run(gemini, data["sys_상품종형"], data["sys_특약"], data["sys_급부"], data["hum_표준담보사전"],
                         existing, datetime.now(KST), mapping.thresholds_from(data["hum_기준값"]), remap=args.remap)
    text = f"매핑 결과: {result.stats}\n모델별 호출 수: {gemini.calls}\n"
    if result.waiting:
        text += "\n담당자 검토 대기\n" + "\n".join(result.waiting) + "\n"
    print(text)
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps({"stats": result.stats, "rows": result.rows, "logs": result.logs},
                                          ensure_ascii=False, indent=1), encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 표준담보 매핑\n\n" + text.replace("\n", "\n\n", 2))
    errors = check_rows("hum_담보매핑", result.rows)
    if errors:
        print("형식 검사에 걸려 시트에 쓰지 않았습니다:", json.dumps(errors, ensure_ascii=False)[:1500])
        return 1
    if args.dry_run or not result.rows:
        return 0
    store.upsert_mapping(result.rows)
    store.append("sys_작업로그", result.logs)
    print(f"시트에 씀: 매핑 {len(result.rows)}행, 기록 {len(result.logs)}행")
    return 0


if __name__ == "__main__":
    sys.exit(main())
