"""우체국보험 공시실의 상품 목록에서 비교 대상 상품의 코드와 이름을 찾아 보여 준다.

기획 문서 11장의 "상품 코드와 종 구성 대조"를 돕는 일회성 확인 도구다. 아무것도 저장하지 않는다.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_access import _get  # noqa: E402

URL = "https://epostlife.go.kr/ASISDM00AT.do"
NAMES = ["통합건강보험", "간편한건강보험", "하나로OK"]
CODE = re.compile(r"P\d{6}")


def main() -> int:
    r = _get(URL, legacy=True)
    r.encoding = r.apparent_encoding or r.encoding
    page = r.text
    print(f"상태 {r.status_code}, 글자 수 {len(page):,}, 인코딩 {r.encoding}")
    print("상품 코드 형태(P+숫자 6자리) 개수:", len(set(CODE.findall(page))))
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    text = re.sub(r"\s+", " ", text)
    for name in NAMES:
        print(f"\n== {name} ==")
        seen = set()
        for m in re.finditer(name, page):
            chunk = page[max(0, m.start() - 400): m.end() + 400]
            codes = sorted(set(CODE.findall(chunk)))
            label = html.unescape(re.sub(r"<[^>]+>", " ", page[max(0, m.start() - 60): m.end() + 60]))
            label = re.sub(r"\s+", " ", label).strip()
            key = (label, tuple(codes))
            if key in seen:
                continue
            seen.add(key)
            print(f"- {label} | 주변 코드: {', '.join(codes) or '없음'}")
        if not seen:
            print("- 목록에서 찾지 못함")
    return 0


if __name__ == "__main__":
    sys.exit(main())
