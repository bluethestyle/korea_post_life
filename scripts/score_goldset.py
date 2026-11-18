"""뽑은 급부를 정답셋(data/goldset)의 "보장금액·면책·감액" 항목과 맞춰 본다.

정답은 문장으로 적혀 있어, 정답 문장 속의 금액·날수가 뽑은 행에 있는지를 본다.
기계로 가릴 수 없는 항목(여러 급부를 더한 금액 등)은 "직접 확인"으로 남긴다.

  python scripts/score_goldset.py --result 간편한건강보험=<결과 JSON> --result 통합건강보험=<결과 JSON>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.extract.benefits import _MONEY, squash  # noqa: E402

GOLD = Path(__file__).resolve().parents[1] / "data/goldset/epost_goldset.jsonl"


def money_values(text: str) -> list[float]:
    out = []
    for m in _MONEY.finditer(squash(text)):
        eok, cheonman, man, cheon = (int(g) if g else 0 for g in m.groups())
        value = eok * 10000 + cheonman * 1000 + man + cheon / 10
        if value:
            out.append(value)
    return out


def norm(text: str) -> str:
    return re.sub(r"[\s·ⅡⅢII]", "", text)


def score(item: dict, riders: list[dict], benefits: list[dict]) -> tuple[str, str]:
    # 급부 이름에 가운뎃점이 든 경우(항암방사선·약물치료보험금)를 위해 특약 이름은 " · " 앞까지만 본다
    head, _, tail = item["특약급부명"].partition(" · ")
    names = [n.strip() for n in tail.split(",")] if tail else [head.strip()]
    rider_ids = {r["특약ID"] for r in riders if norm(r["원시특약명"]) == norm(head)} if tail else {r["특약ID"] for r in riders}
    rows = [b for b in benefits if b["특약ID"] in rider_ids and any(norm(b["원시급부명"]).startswith(norm(n)) for n in names)]
    if item["정답"].strip() == "문서에 없음":
        return ("일치", "해당 급부를 뽑지 않음") if not rows else ("불일치", f"문서에 없는 급부를 {len(rows)}줄 뽑음")
    if not rows:
        return "불일치", "해당 급부를 찾지 못함"
    have: set[float] = set()
    for b in rows:
        have.add(float(b["기준지급금액만원"]))
        for rate in (b.get("감액지급률1"), b.get("감액지급률2")):
            if rate is not None:
                have.add(round(float(b["기준지급금액만원"]) * float(rate), 4))
    wanted = money_values(item["정답"])
    missing = [w for w in wanted if w not in have]
    derived = [w for w in missing if any(abs(a + b - w) < 1e-6 for a in have for b in have)]
    missing = [w for w in missing if w not in derived]
    notes = []
    answer = squash(item["정답"])
    if "90일이지난" in answer and not any(b["면책기간일수"] == 90 for b in rows):
        missing.append("면책 90일")
    if "1년이지난" in answer and not any(b["면책기간일수"] == 365 for b in rows):
        missing.append("면책 365일")
    for days in re.findall(r"(\d+)일한도", answer):
        if not any(f"{days}일" in squash(str(b.get("지급횟수제한") or "")) for b in rows):
            notes.append(f"{days}일 한도가 지급횟수제한 칸에 없음")
    if "감액없음" in answer and any(b.get("감액지급률1") is not None for b in rows):
        missing.append("감액 없음")
    if missing:
        return "불일치", f"뽑은 행에 없는 값: {missing}"
    if derived or notes:
        return "직접 확인", "; ".join(([f"더해서 나오는 금액 {derived}"] if derived else []) + notes)
    return "일치", f"금액 {sorted(set(wanted))}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--result", action="append", required=True, metavar="상품명에 든 글자=결과 JSON")
    p.add_argument("--area", default="보장금액·면책·감액")
    args = p.parse_args()
    results = {}
    for pair in args.result:
        key, path = pair.split("=", 1)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        rows = data.get("rows") or {"sys_특약": data["riders"], "sys_급부": data["benefits"]}
        results[key] = (rows["sys_특약"], rows["sys_급부"])
    tally: dict[str, int] = {}
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item["영역"] != args.area:
            continue
        key = next((k for k in results if k in squash(item["상품과종"])), None)
        if key is None:
            continue
        verdict, why = score(item, *results[key])
        tally[verdict] = tally.get(verdict, 0) + 1
        print(f"{item['번호']:>3} {verdict} | {item['특약급부명'][:44]} | {why}")
    print(tally)
    return 0


if __name__ == "__main__":
    sys.exit(main())
