"""공시 문서의 글자를 쪽과 특약 단위로 나눈다.

약관이나 요약서를 통째로 모델에 넣지 않는다. 상품요약서의 "보험금 지급사유" 절을 찾아
"■ 특약명" 줄을 경계로 한 특약씩 잘라 넣는다. 조각마다 쪽 번호를 지녀 화면의 근거 표시에 쓴다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_PAGE = re.compile(r"\n?===== (\d+)쪽 =====\n")
_START = re.compile(r"^[②2][\s.)]*보험금\s*지급사유\s*$")
_END = re.compile(r"^[③3][\s.)]*일반적\s*보험금\s*지급제한")
_HEAD = re.compile(r"^■\s*(.+?)\s*$")
# 보험금을 지급하는 특약이 아닌 것. 급부 추출 대상에서 뺀다.
_SKIP = re.compile(r"부담보\s*특약|지정대리청구|전환특약")
_BASE = re.compile(r"보험가입금액\s*([\d,]+)\s*만\s*원\s*기준")


@dataclass(frozen=True)
class Block:
    title: str            # "■" 뒤의 이름. 예: 무배당 암진단특약(20년갱신형) 2606
    text: str             # 머리줄을 포함한 본문
    first_page: int
    last_page: int

    @property
    def is_main(self) -> bool:
        return self.title.replace(" ", "").startswith("주계약")

    @property
    def rider_name(self) -> str:
        """머리줄에 붙은 기준 문구를 뗀 이름. 예: "주계약 (보험가입금액 2,000만 원 기준)" → "주계약"."""
        return re.sub(r"\s*\(.*?기준\)\s*$", "", self.title).strip()

    @property
    def base_amount(self) -> float | None:
        m = _BASE.search(self.text[:400])
        return float(m.group(1).replace(",", "")) if m else None


def pages_from_text(text: str) -> dict[int, str]:
    """scripts/fetch_disclosure.py가 저장한 글자 파일(쪽 구분선 포함)을 쪽별로 나눈다."""
    parts = _PAGE.split("\n" + text)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def _lines(pages: dict[int, str]) -> list[tuple[int, str]]:
    return [(n, line) for n in sorted(pages) for line in pages[n].split("\n")]


def rider_blocks(pages: dict[int, str], include_skipped: bool = False) -> list[Block]:
    """상품요약서의 보험금 지급사유 절을 특약 단위 조각으로 나눈다."""
    lines = _lines(pages)
    start = next((i for i, (_, l) in enumerate(lines) if _START.match(l.strip())), None)
    if start is None:
        raise ValueError("'보험금 지급사유' 절을 찾지 못했습니다")
    end = next((i for i in range(start + 1, len(lines)) if _END.match(lines[i][1].strip())), len(lines))
    blocks: list[Block] = []
    current: list[tuple[int, str]] = []

    def close() -> None:
        if not current:
            return
        title = _HEAD.match(current[0][1].strip()).group(1)
        if include_skipped or not _SKIP.search(title):
            blocks.append(Block(title, "\n".join(l for _, l in current).strip(), current[0][0], current[-1][0]))

    for page, line in lines[start + 1:end]:
        if _HEAD.match(line.strip()):
            close()
            current = [(page, line)]
        elif current:
            current.append((page, line))
    close()
    return blocks
