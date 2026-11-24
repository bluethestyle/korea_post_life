"""상품요약서 PDF의 급부 표를 특별약관 단위 조각으로 뽑아 JSON으로 쓴다.

"보장명 | 지급사유 | 지급금액" 표 하나에 담보가 이어져 있어 글자 파일로는 자를 수 없는 요약서에 쓴다.
PDF는 저장소에 두지 않는다. 받은 자리에서 조각만 뽑아 두면 추출 단계가 tables.read_riders로 읽는다.
회사마다 절 제목과 표 위 표시의 꼴이 달라 --org로 고른다(기본은 삼성화재. 꼴의 차이는 docs/table_layouts.md).
  python scripts/dump_tables.py <요약서.pdf> --out 조각.json
  python scripts/dump_tables.py <요약서.pdf> --text <글자 파일> --variant "8종(일반형)" --out 조각.json
  python scripts/dump_tables.py <요약서.pdf> --org meritz --out 조각.json
  python scripts/dump_tables.py <요약서.pdf> --org kblife --out 조각.json
  python scripts/dump_tables.py <요약서.pdf> --org hyundai --out <추출 단위.json>
"""
from __future__ import annotations

import argparse
import collections
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.extract import tables  # noqa: E402
from postlife.extract.segment import pages_from_text  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("pdf", type=Path, help="상품요약서 PDF")
    p.add_argument("--out", type=Path, required=True, help="조각을 쓸 JSON 파일")
    p.add_argument("--org", default=tables.SAMSUNGFIRE.name, choices=sorted(tables.LAYOUTS), help="요약서의 꼴(회사)")
    p.add_argument("--text", type=Path, help="같은 문서의 글자 파일(쪽 구분선 포함). 주면 쪽 범위를 여기서 찾아 빠르다")
    p.add_argument("--section", help='급부 절이 여러 곳일 때 고를 구간의 제목 줄. 예: "나. 8종(일반형)"')
    p.add_argument("--pages", help="쪽 범위를 직접 정한다. 예: 50-118")
    p.add_argument("--variant", help='이 종에 해당하는 줄만 남긴다. 예: "8종(일반형)"')
    args = p.parse_args()
    layout = tables.LAYOUTS[args.org]

    if args.pages:
        first, last = (int(n) for n in args.pages.split("-"))
    else:
        pages = pages_from_text(args.text.read_text(encoding="utf-8")) if args.text else tables.page_texts(args.pdf)
        found = tables.benefit_pages(pages, args.section, layout)
        first, last = found.first_page, found.last_page
    misses: list[dict] = []
    read = tables.read_tables(args.pdf, first, last, layout, misses)
    riders = tables.riders_from_tables(read, layout)
    if args.variant:
        riders = tables.for_variant(riders, args.variant)
    if not riders:
        print(f"{first}~{last}쪽에서 급부 표를 찾지 못했습니다", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    source = {"문서": args.pdf.stem, "쪽": [first, last], "구간": args.section or "", "종": args.variant or ""}
    if layout is not tables.SAMSUNGFIRE:
        source["꼴"] = layout.name
        source["못 읽은 곳"] = misses
    tables.write_riders(args.out, riders, source, tables.table_notes(read, layout))
    lengths = sorted(len(r.text) for r in riders)
    print(f"{first}~{last}쪽: 조각 {len(riders)}개, 세부보장 {sum(len(r.covers) for r in riders)}개, "
          f"조각 길이 중앙값 {statistics.median(lengths):.0f}자, 최대 {lengths[-1]}자 → {args.out}")
    if layout is not tables.SAMSUNGFIRE:
        read_pages = {t.page for t in read}
        print(f"표가 읽힌 쪽 {len(read_pages)}/{last - first + 1}, "
              f"주계약 조각 {sum(bool(r.main) for r in riders)}개, "
              f"형별 조각 {dict(collections.Counter(r.segment or '-' for r in riders))}")
        for miss in misses:
            print(f"  못 읽음 {miss['쪽']}쪽: {miss['이유']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
