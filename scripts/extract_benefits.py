"""상품요약서의 글자 파일에서 급부를 뽑아 검증한다. 시트에는 쓰지 않고 결과를 JSON으로 남긴다.

개발·점검용이다. 문서 수집부터 시트 기록까지 잇는 실행은 scripts/extract_product.py가 맡는다.
  GEMINI_API_KEY=... python scripts/extract_benefits.py --text <글자 파일> --variant V1 --out out.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife import config  # noqa: E402
from postlife.extract import pipeline  # noqa: E402
from postlife.extract.segment import pages_from_text  # noqa: E402
from postlife.gemini import Gemini  # noqa: E402
from postlife.snapshot import KST  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--text", type=Path, required=True)
    p.add_argument("--variant", action="append", required=True, help="종형ID. 여러 종이 한 요약서를 쓰면 여러 번 적는다")
    p.add_argument("--renewal-years", type=int, help="주계약이 갱신형이면 갱신 주기(년)")
    p.add_argument("--only", action="append", help="이름에 이 글자가 든 특약만 처리")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--swap-models", action="store_true", help="처음 추출과 재추출에 쓰는 모델을 맞바꿔 비교한다")
    args = p.parse_args()
    if args.swap_models:
        config.MODEL_EXTRACT, config.MODEL_EXTRACT_ALT = config.MODEL_EXTRACT_ALT, config.MODEL_EXTRACT

    gemini = Gemini(min_interval=config.MIN_INTERVAL, timeout=config.TIMEOUT, retry_wait=config.RETRY_WAIT)
    pages = pages_from_text(args.text.read_text(encoding="utf-8"))
    result = pipeline.run_summary(gemini, pages, args.variant, datetime.now(KST),
                                  product_renewal_years=args.renewal_years, only=args.only)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "stats": result.stats, "calls": gemini.calls, "riders": result.riders, "benefits": result.benefits,
        "logs": result.logs,
        "blocks": [{"title": b.extraction.block.title, "page": b.extraction.block.first_page,
                    "model": b.extraction.model, "retried": b.retried, "problems": b.extraction.problems,
                    "benefits": [asdict(x) for x in b.extraction.benefits], "probs": b.probs, "status": b.status}
                   for b in result.blocks],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(result.stats, gemini.calls)
    for b in result.blocks:
        for x in b.extraction.benefits:
            low = min(b.probs.get(x.label, {"-": 0}).items(), key=lambda kv: kv[1])
            print(f"  [{b.status[x.label]}] {b.extraction.block.rider_name[:22]} | {x.label[:34]} | {x.amount}만원"
                  f" | 감액 {x.reduced_months}/{x.reduced_amount} | 면책 {x.waiting_days} | {x.role} | 최저 {low[0]} {low[1]:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
