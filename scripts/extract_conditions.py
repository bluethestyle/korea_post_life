"""사업방법서 글자 파일 하나로 가입조건·결합 제약 추출만 확인한다. 시트에는 쓰지 않는다 (개발·점검용).

  GEMINI_API_KEY=... python scripts/extract_conditions.py --method <사업방법서 글자> --summary <요약서 글자> \
      --benefits <extract_benefits.py 결과 JSON> --variant-name "1종(간편가입315)" --out out.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife import config  # noqa: E402
from postlife.extract import conditions as C  # noqa: E402
from postlife.extract import conditions_run, pipeline  # noqa: E402
from postlife.extract.segment import pages_from_text  # noqa: E402
from postlife.gemini import Gemini  # noqa: E402
from postlife.snapshot import KST  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--method", type=Path, required=True)
    p.add_argument("--summary", type=Path)
    p.add_argument("--benefits", type=Path, required=True, help="특약 목록을 가져올 급부 추출 결과")
    p.add_argument("--variant-name", action="append", help="종형명. 결과 JSON의 종형 순서대로 여러 번")
    p.add_argument("--code", action="append", help="결과 JSON에 종형 행이 있으면 이 공시상품코드의 종형만 쓴다")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    data = json.loads(args.benefits.read_text(encoding="utf-8"))
    riders = (data.get("rows") or {}).get("sys_특약") or data["riders"]
    variants = (data.get("rows") or {}).get("sys_상품종형") or []
    if variants and args.code:
        chosen = [v for v in variants if v["공시상품코드"] in args.code]
        targets = [C.target_of(v["종형ID"], v["종형명"], riders) for v in chosen]
    else:
        variant_ids = list(dict.fromkeys(r["종형ID"] for r in riders))
        names = args.variant_name or ["단일"] * len(variant_ids)
        targets = [C.target_of(v, n, riders) for v, n in zip(variant_ids, names)]
    gemini = Gemini(min_interval=config.MIN_INTERVAL, timeout=config.TIMEOUT, retry_wait=config.RETRY_WAIT)
    result = conditions_run.run(
        gemini, pages_from_text(args.method.read_text(encoding="utf-8")),
        pages_from_text(args.summary.read_text(encoding="utf-8")) if args.summary else None,
        targets, datetime.now(KST), dict(pipeline.DEFAULT_THRESHOLDS))
    args.out.write_text(json.dumps({
        "stats": result.stats, "calls": gemini.calls, "notes": result.notes, "review": result.review,
        "conditions": result.conditions, "constraints": result.constraints,
        "amounts": {k: list(v) for k, v in result.amounts.items()}, "logs": result.logs,
        "items": {label: [{"key": i.key, **{k: v for k, v in vars(i).items()}, "probs": shot.probs.get(i.key),
                           "literal": shot.literal.get(i.key)} for i in shot.ex.items]
                  for label, shot in result.shots.items()},
        "problems": {label: shot.ex.problems for label, shot in result.shots.items()},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(result.stats, gemini.calls)
    for n in result.notes:
        print("주의:", n)
    for r in result.review:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
