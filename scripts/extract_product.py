"""공시 문서에서 종형·특약·급부를 뽑아 검증하고 시트에 쓴다. GitHub Actions에서 fetch_disclosure.py 다음에 실행한다.

  python scripts/fetch_disclosure.py --out out
  python scripts/extract_product.py --docs out --targets data/targets/epost.json

시트 없이 흐름만 확인하려면 --dry-run. 특정 상품만 다시 뽑으려면 --only P500129 (공시상품코드, 여러 번 가능).
다시 뽑은 종형의 기존 행만 걷어내고 새 행으로 바꾸며, 다른 상품의 행은 건드리지 않는다.
관문전용 종형(대상 설정의 비교역할구분)만 올리려면 --parts 관문. 급부를 뽑지 않고 종형 행, 주계약 행, 주계약 가입조건만 쓴다.
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
from postlife.extract import job  # noqa: E402
from postlife.gemini import Gemini, input_tokens_report  # noqa: E402
from postlife.recording import Recording  # noqa: E402
from postlife.sheets_io import MemoryBackend, RestBackend, SheetStore  # noqa: E402
from postlife.snapshot import KST  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--docs", type=Path, required=True, help="fetch_disclosure.py의 결과 폴더")
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--only", action="append", help="이 공시상품코드의 종형만 처리")
    p.add_argument("--dry-run", action="store_true", help="시트에 쓰지 않는다")
    p.add_argument("--parts", default="급부,가입조건,관문",
                   help="돌릴 부분. 급부(요약서), 가입조건(사업방법서), 관문(관문전용 종형의 종형 행과 주계약 가입조건). 쉼표로 구분")
    p.add_argument("--result", type=Path, help="뽑은 행과 기록을 JSON으로 남길 경로")
    args = p.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY가 없어 건너뜁니다.")
        return 0
    has_sheet = bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") and os.environ.get("SPREADSHEET_ID"))
    if not has_sheet and not args.dry_run:
        print("시트 접속 정보가 없어 건너뜁니다. 흐름만 보려면 --dry-run을 붙이세요.")
        return 0
    store = SheetStore(RestBackend.from_env() if has_sheet else MemoryBackend())

    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    index = json.loads((args.docs / "index.json").read_text(encoding="utf-8"))

    def read_text(stem: str) -> str | None:
        path = args.docs / f"{stem}.txt"
        return path.read_text(encoding="utf-8") if path.exists() else None

    # 모델 응답을 결과물에 함께 남긴다. 고친 코드를 모델을 다시 부르지 않고 같은 응답으로 돌려 볼 수 있다
    gemini = Recording(Gemini(min_interval=config.MIN_INTERVAL, timeout=config.TIMEOUT, retry_wait=config.RETRY_WAIT))
    report = job.run(gemini, store, targets, index, read_text, datetime.now(KST), only=args.only,
                     dry_run=args.dry_run, read_thresholds=has_sheet,
                     parts=tuple(x.strip() for x in args.parts.split(",") if x.strip()))
    text = report.markdown(gemini.calls)
    print(text)
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps({"rows": report.rows, "logs": report.logs, "errors": report.errors,
                                           "rerun": getattr(report, "rerun", None), "notes": report.notes,
                                           "calls": gemini.calls, "token_waits": getattr(gemini, "token_waits", {}),
                                           # 판정 응답이 알려 준 실제 입력 토큰 합과 글자당 토큰 비율(모델별)
                                           "input_tokens": input_tokens_report(getattr(gemini, "input_tokens", None))},
                                          ensure_ascii=False, indent=1), encoding="utf-8")
        gemini.dump(args.result.with_name("model_outputs.jsonl"))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 추출·검증\n\n" + text)
    if report.write_error:
        print("시트에 쓰지 못했습니다. 뽑은 행은 결과 파일에 남겼습니다:", report.write_error)
        return 1
    if report.errors:
        print("형식 검사에 걸려 시트에 쓰지 않았습니다:", json.dumps(report.errors, ensure_ascii=False)[:2000])
        return 1
    gate_done = getattr(report, "gate_done", None)
    if not (report.done or report.conditions_done or gate_done):
        print("처리한 종형이 없습니다.")
        return 1
    if report.written:
        rows = report.rows
        print(f"시트에 씀: 종형 {len(rows['sys_상품종형'])}, 특약 {len(rows['sys_특약'])}, 급부 {len(rows['sys_급부'])}, "
              f"가입조건 {len(rows['sys_가입조건'])}, 결합제약 {len(rows['sys_결합제약'])}, 기록 {len(report.logs)}행"
              + (f" (관문전용 종형 {len(gate_done)}개, 그 가운데 가입조건까지 {len(report.gate_conditions_done)}개)"
                 if gate_done else ""))
    else:
        print("--dry-run: 시트에 쓰지 않았습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
