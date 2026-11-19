"""급부 표를 코드 규칙으로 읽은 결과(table_rules)를, 다른 모델이 따로 구조화한 표와 줄마다 견준다.

대조 표는 두 꼴을 읽는다. 번호는 조각 파일의 특별약관 순번(3자리)과 세부보장 순번이다.
- JSONL: 줄마다 {"번호": "R001-1", "지급률", "감액1기간", "감액1지급률", "감액2기간", "감액2지급률", "면책", "지급한도", "비고"}
  (data/crosscheck/samsungfire_fit8_benefits_gemini.jsonl이 이 꼴이다)
- JSON: {"R001-1": [번호, 지급률(%), 감액1 기간, 감액1 지급률(%), 감액2 기간, 감액2 지급률(%), 면책(일), 지급 한도, 비고], …}
대조 표가 없으면 규칙 결과와 "확신 없음" 사유의 분포만 낸다.

  python scripts/compare_table_rules.py 조각.json --against data/crosscheck/samsungfire_fit8_benefits_gemini.jsonl
  python scripts/compare_table_rules.py 조각.json --doubts          # 확신 없음 줄을 사유와 함께 본다
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.extract import table_rules, tables  # noqa: E402
from postlife.extract.table_rules import Reading  # noqa: E402

_LOOSE = re.compile(r"[\s·∙ㆍ,、「」()\[\]/]|^단,|또는|및|지급|함$")


def loose(text: str) -> str:
    """구두점·이음말·빈칸 차이를 없앤 글자. 한도 문구를 견줄 때 쓴다."""
    return _LOOSE.sub("", re.sub(r"\s", "", text or ""))


def months_of(period: str) -> int | None:
    m = re.search(r"(\d+)\s*(일|개월|년)", period or "")
    if not m:
        return None
    n = int(m.group(1))
    return n * 12 if m.group(2) == "년" else n if m.group(2) == "개월" else round(n / 30)


def days_in(cell: str) -> set[int]:
    """면책 칸에 적힌 날수들. "암 90 / 기타피부암·갑상선암 0" → {90, 0}, "1년" → {365}."""
    return {int(n) * (365 if unit == "년" else 1) for n, unit in re.findall(r"(?<![\d~])(\d+)\s*(년|일)?(?![\d%])", cell or "")}


_COLUMNS = ("번호", "지급률", "감액1기간", "감액1지급률", "감액2기간", "감액2지급률", "면책", "지급한도", "비고")


def load_table(path: Path) -> dict[str, list[str]]:
    """대조 표를 {번호: [아홉 칸]}으로 읽는다."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        return {r["번호"]: [str(r.get(c, "")) for c in _COLUMNS] for r in rows}
    return {key: [str(v) for v in row] for key, row in json.loads(text).items()}


def differences(lines: list[Reading], other: list[str]) -> list[str]:
    """한 세부보장에서 규칙이 읽은 줄들과 대조 표의 한 줄이 어긋나는 곳."""
    _, rate, p1, r1, p2, r2, wait, limit, note = (other + [""] * 9)[:9]
    out = []
    # 지급률: 대상별로 나눈 줄은 가장 큰 값이 대조 표의 지급률이고, 나머지는 비고에 "N%"로 적혀 있어야 한다
    percents = sorted({x.percent for x in lines if x.percent is not None}, reverse=True)
    if rate.strip().isdigit():
        if not percents or percents[0] != float(rate):
            out.append(f"지급률: 규칙 {percents or '비율 아님'} / 대조 {rate}")
        for extra in percents[1:]:
            if f"{extra:g}%" not in note:
                out.append(f"지급률: 규칙의 대상별 {extra:g}%가 대조 표 비고에 없음")
    elif percents and not all(x.doubts for x in lines):
        out.append(f"지급률: 규칙 {percents} / 대조 \"{rate}\"")
    # 감액: 대상별로 나눈 줄의 구간을 모아 견준다
    mine = sorted({(s.months, round(s.rate * 100)) for x in lines for s in x.steps})
    theirs = sorted((months_of(p), int(r)) for p, r in ((p1, r1), (p2, r2)) if p.strip() not in ("", "-") and r.strip().isdigit())
    if mine != theirs:
        out.append(f"감액: 규칙 {mine} / 대조 {theirs}")
    # 면책
    if {x.waiting_days for x in lines} != days_in(wait):
        out.append(f"면책: 규칙 {sorted({x.waiting_days for x in lines})} / 대조 \"{wait}\"")
    # 대조 표가 "1년 미만(질병)"처럼 적은 줄은 규칙이 감액예외 칸에 원문을 옮긴 줄과 같은 뜻이다
    split_mine, split_theirs = len(lines) > 1, "/" in wait or ("(" in p1 and not lines[0].exception)
    if split_mine != split_theirs and not (split_mine and len(percents) > 1):
        out.append(f"대상 나눔: 규칙 {[x.target for x in lines] if split_mine else '한 줄'} / 대조 \"{wait}\" \"{p1}\"")
    # 한도: 대조 표의 한도가 규칙의 한도 안에 있어야 하고, 규칙에만 있는 문구는 대조 표의 비고에라도 있어야 한다
    mine_limit = loose(lines[0].limit + lines[0].note)
    for piece in (limit if limit.strip() != "-" else "").split(" / "):
        if piece.strip() and loose(piece) not in mine_limit:
            out.append(f"한도: 대조 표의 \"{piece.strip()}\"가 규칙 결과에 없음")
    # 대조 표는 "※" 문단을 줄여 적기도 한다. 글자가 그대로 없으면 그 문구의 횟수·기간("2회", "10년")이 모두 있는지 본다
    theirs_text = loose(limit + note)
    for piece in lines[0].limit.split(" / "):
        counts = re.findall(r"\d+(?:\.\d+)?\s*(?:회|일|년|억|천만|만)", piece)
        if piece.strip() and loose(piece) not in theirs_text and not (counts and all(loose(c) in theirs_text for c in counts)):
            out.append(f"한도: 규칙의 \"{piece.strip()[:60]}\"가 대조 표에 없음")
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("riders", type=Path, help="tables.write_riders로 쓴 조각 JSON")
    p.add_argument("--against", type=Path, help="대조 표 JSON")
    p.add_argument("--doubts", action="store_true", help="확신 없음 줄을 사유와 함께 낸다")
    p.add_argument("--all", action="store_true", help="규칙이 읽은 줄을 모두 낸다")
    args = p.parse_args()

    riders = tables.read_riders(args.riders)
    other = load_table(args.against) if args.against else {}
    kinds: collections.Counter[str] = collections.Counter()
    covers = unsure = same = differ_sure = differ_unsure = missing = 0
    for i, rider in enumerate(riders, 1):
        for j, (cover, lines) in enumerate(zip(rider.covers, table_rules.read_rider(rider)), 1):
            key = f"R{i:03d}-{j}"
            covers += 1
            doubts = lines[0].doubts
            unsure += bool(doubts)
            kinds.update({table_rules.doubt_kind(d) for d in doubts})
            head = f"{key} ({cover.page}쪽) {cover.name[:40]}"
            if args.all or (args.doubts and doubts):
                for x in lines:
                    steps = ", ".join(f"{s.months}개월 {s.rate:g}" for s in x.steps) or "-"
                    print(f"{head} | {x.target or '-'} | 지급률 {x.percent} | 감액 {steps} | 면책 {x.waiting_days} | 한도 {x.limit or '-'}")
                for d in doubts:
                    print(f"    확신 없음: {d}")
            if not other:
                continue
            if key not in other:
                missing += 1
                print(f"{head} | 대조 표에 없음")
                continue
            found = differences(lines, other[key])
            if not found:
                same += 1
                continue
            differ_unsure += bool(doubts)
            differ_sure += not doubts
            print(f"{head} | {'확신 없음' if doubts else '확신'}")
            for line in found:
                print(f"    {line}")
    print(f"세부보장 {covers}줄, 확신 없음 {unsure}줄")
    for kind, n in kinds.most_common():
        print(f"  {n:4d}  {kind}")
    if other:
        print(f"대조: 같은 줄 {same}, 다른 줄 {differ_sure + differ_unsure}(확신한 줄 {differ_sure}, 확신 없음 줄 {differ_unsure}), 대조 표에 없는 줄 {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
