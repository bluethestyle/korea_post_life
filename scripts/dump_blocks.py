"""생명보험사 상품요약서 PDF의 급부 표(특약마다 따로 있는 작은 표)를 특약 단위 조각으로 뽑아 JSON으로 쓴다.

조각 파일의 꼴은 scripts/dump_tables.py와 같아서 scripts/split_pieces.py에 그대로 넣는다. 회사마다 절 제목, 소절,
표 머리의 꼴이 달라 --org로 고른다(blocks.LAYOUTS. 꼴과 이름 규칙은 docs/table_layouts.md).
조각에는 공시 문서의 원문 글자가 들어 있으므로 리포 밖(임시 폴더)에 쓴다.

  python scripts/dump_blocks.py <요약서.pdf> --org samsunglife --out 조각.json [--check 점검.json]
  python scripts/dump_blocks.py <요약서.pdf> --org kyobo --out <추출 단위.json> [--check 점검.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.extract import blocks, tables  # noqa: E402
from postlife.extract.segment import pages_from_text  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("pdf", type=Path, help="상품요약서 PDF")
    p.add_argument("--out", type=Path, required=True, help="조각을 쓸 JSON 파일(리포 밖)")
    p.add_argument("--org", default=blocks.SAMSUNGLIFE.name, choices=sorted(blocks.LAYOUTS), help="요약서의 꼴(회사)")
    p.add_argument("--text", type=Path, help="같은 문서의 글자 파일(쪽 구분선 포함). 주면 쪽 범위를 여기서 찾는다")
    p.add_argument("--pages", help="쪽 범위를 직접 정한다. 예: 8-88")
    p.add_argument("--check", type=Path, help="이름 점검과 따로 본 행, 수치를 쓸 JSON 파일(리포 밖)")
    args = p.parse_args(argv)
    layout = blocks.LAYOUTS[args.org]

    first = last = None
    pages = None
    if args.pages:
        first, last = (int(n) for n in args.pages.split("-"))
    elif args.text:
        pages = pages_from_text(args.text.read_text(encoding="utf-8"))
    result, source = blocks.read_pdf(args.pdf, layout, first, last, pages)
    if not result.riders:
        print(f"{source['쪽'][0]}~{source['쪽'][1]}쪽에서 급부 표를 찾지 못했습니다", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tables.write_riders(args.out, result.riders, {"문서": args.pdf.stem, **source}, result.notes)

    numbers = blocks.stats(result)
    first, last = source["쪽"]
    print(f"{first}~{last}쪽: 조각 {numbers['조각']}개, 세부보장 {numbers['세부보장']}개, 주석 {numbers['주석']}개 → {args.out}")
    print(f"주계약 조각 {numbers['주계약 조각']} (세부보장 {numbers['주계약 세부보장']})")
    print(f"이름같은 묶음 {numbers['이름같은 묶음']} (줄 {numbers['이름같은 줄']}), 지급금액 꼴 {numbers['지급금액 꼴']}")
    print(f"종 표시: 조각 {numbers['종 표시가 붙은 조각']}, 세부보장 {numbers['종 표시가 붙은 세부보장']}")
    print(f"이름 깨짐 {len(result.issues)}건 {numbers['이름 깨짐']}")
    print(f"기준 줄 {numbers['기준 줄']}")
    if numbers["같은 제목 조각"]:
        print(f"제목이 같은 조각: {numbers['같은 제목 조각']}")
    for miss in source["못 읽은 곳"]:
        print(f"  못 읽음 {miss['쪽']}쪽: {miss['이유']}")
    if args.check:
        args.check.parent.mkdir(parents=True, exist_ok=True)
        args.check.write_text(json.dumps({"수치": numbers, "이름 깨짐": result.issues, "따로 본 행": result.events,
                                          "못 읽은 곳": source["못 읽은 곳"]}, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
