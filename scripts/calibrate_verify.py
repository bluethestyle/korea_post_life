"""판정 구간 경계(추출검증_통과·추출검증_재추출)를 실제 문서로 맞춘다.

사람이 원문과 대조해 맞다고 확인한 추출 결과를 넣으면, 값을 일부러 틀리게 바꾼 줄을 함께 만들어
판정 모델에 묻고, 맞는 값과 틀린 값이 받은 확률을 나란히 보여 준다. 시트에는 쓰지 않는다.

  GEMINI_API_KEY=... python scripts/calibrate_verify.py --pair <글자 파일> <extract_benefits.py 결과 JSON> --out out.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife import config  # noqa: E402
from postlife.extract import verify as V  # noqa: E402
from postlife.extract.benefits import Benefit, Extraction  # noqa: E402
from postlife.extract.segment import pages_from_text, rider_blocks  # noqa: E402
from postlife.gemini import Gemini  # noqa: E402


def wrong_versions(b: Benefit, siblings: list[Benefit]) -> dict[str, Benefit]:
    """한 줄을 틀리게 바꾼 여러 꼴. 이름은 무엇을 틀리게 했는지. 숫자를 바꾼 칸의 원문 글자는 지운다."""
    out: dict[str, Benefit] = {}
    if b.reduced_amount is not None:
        out["감액 누락"] = replace(b, reduced_months=None, reduced_amount=None, reduced_text="")
        out["감액과 지급액 뒤바뀜"] = replace(b, amount=b.reduced_amount, reduced_months=None, reduced_amount=None,
                                      amount_text="", reduced_text="")
        out["감액 기간 다름"] = replace(b, reduced_months=(b.reduced_months or 12) * 2)
    else:
        out["없는 감액 추가"] = replace(b, reduced_months=12, reduced_amount=b.amount / 2)
    out["금액 두 배"] = replace(b, amount=b.amount * 2, amount_text="", reduced_text="",
                              reduced_amount=None if b.reduced_amount is None else b.reduced_amount * 2)
    other = next((s for s in siblings if s.amount != b.amount), None)
    if other is not None:
        out["다른 줄의 금액"] = replace(b, amount=other.amount, reduced_months=other.reduced_months,
                                   reduced_amount=other.reduced_amount, amount_text="", reduced_text="")
    out["면책 뒤집음"] = replace(b, waiting_days=0 if b.waiting_days else 90)
    return out


def record(block, b: Benefit, probs: dict[str, float], right: bool, kind: str = "") -> dict:
    """한 줄의 결과. 확률은 항목 가운데 가장 낮은 값이다. 실제 분기(확정·검토·재추출)가 이 값으로 정해진다."""
    field, low = min(probs.items(), key=lambda kv: kv[1])
    return {"특약": block.rider_name, "급부": b.label, "맞는 값": right, "바꾼 내용": kind, "확률": low,
            "가장 낮은 항목": field, "항목별": probs}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pair", nargs=2, action="append", required=True, metavar=("TEXT", "RESULT"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--only", action="append", help="이름에 이 글자가 든 특약만")
    args = p.parse_args()

    # 판정 모델은 분당 토큰 한도가 있어 호출 사이를 띄운다
    gemini = Gemini(min_interval={**config.MIN_INTERVAL, config.MODEL_DECIDE: 2.5})
    records: list[dict] = []
    for text_path, result_path in args.pair:
        blocks = {b.title: b for b in rider_blocks(pages_from_text(Path(text_path).read_text(encoding="utf-8")))}
        for item in json.loads(Path(result_path).read_text(encoding="utf-8"))["blocks"]:
            if args.only and not any(k in item["title"] for k in args.only):
                continue
            block = blocks[item["title"]]
            rows = [Benefit(**x) for x in item["benefits"]]
            right = V.judge(gemini, Extraction(block, 0, rows, "확인된 값"), config.MODEL_DECIDE)
            records += [record(block, b, right[b.label], True) for b in rows if right.get(b.label)]
            for kind in sorted({k for b in rows for k in wrong_versions(b, rows)}):
                subset = [c for c in (wrong_versions(b, rows).get(kind) for b in rows) if c is not None]
                if kind == "면책 뒤집음" and "보장개시일" not in block.text:
                    continue          # 원문에 보장개시일이 없으면 면책은 코드가 가린다
                got = V.judge(gemini, Extraction(block, 0, subset, "틀리게 바꾼 값"), config.MODEL_DECIDE)
                records += [record(block, c, got[c.label], False, kind) for c in subset if got.get(c.label)]
            print(f"{block.rider_name[:30]}: 누적 {len(records)}건", flush=True)

    args.out.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    print(gemini.calls)
    return 0


if __name__ == "__main__":
    sys.exit(main())
