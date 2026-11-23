"""공시 문서 수집(scripts/fetch_disclosure.py)이 회사 열쇠로 접속 모듈을 찾는 자리.

초기 적재 회사는 여기에 한 줄씩 더한다. 회사마다 접속 모듈의 함수 꼴이 달라서(상품코드로 찾는 곳, 상품명으로 찾는
곳, 목록 한 번에 서류 경로가 다 오는 곳) 여기서 두 함수로 맞춘다.
- find(session, 상품코드, 기준일) → 그날 판매 중인 판매기간의 상품명과 서류 목록(Listed). 판매기간이 없으면 None
- download(session, Listed) → PDF 바이트

받는 서류는 kinds(기본 사업방법서와 상품요약서)뿐이다. 약관과 상품설명서는 받지 않는다.
급부 표 조각은 만들지 않는다(삼성화재 경로에만 있다).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from postlife.disclosure import meritz

KINDS = ("사업방법서", "상품요약서")


@dataclass(frozen=True)
class Listed:
    """공시 목록의 서류 한 건. handle은 접속 모듈의 서류 객체이고 download에 그대로 넘긴다."""
    code: str
    name: str
    kind: str
    file_name: str
    start: str
    end: str | None = None
    registered: str | None = None
    handle: Any = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class Source:
    key: str          # --org 값이자 저장 파일 이름의 앞머리
    org: str          # 기관코드 (postlife.config.INSTITUTIONS의 열쇠)
    label: str        # 실행 요약에 쓰는 회사 이름
    find: Callable[[Any, str, str], tuple[str, list[Listed]] | None]
    download: Callable[[Any, Listed], bytes]
    kinds: tuple[str, ...] = KINDS
    pause: float = 1.0   # 같은 공시실에 보내는 요청(목록 조회, 서류 받기) 사이의 쉬는 초

    @property
    def targets(self) -> str:
        return f"data/targets/{self.key}.json"


def _meritz_find(session: Any, code: str, on: str) -> tuple[str, list[Listed]] | None:
    """상품코드(nwPdCd)로 판매상품 탭의 판매기간을 조회해 on이 속한 기간을 고른다(요청 한 번).

    서류의 암호값(token)은 이 session에서만 쓸 수 있으므로, 같은 session으로 download를 불러야 한다.
    """
    period = meritz.pick_period(meritz.list_periods(session, code, selling=True), on)
    if period is None:
        return None
    return period.name, [Listed(code, period.name, d.kind, d.file_name, period.start, period.end,
                                period.posted or period.start, d) for d in meritz.documents_of(period, code)]


SOURCES: dict[str, Source] = {
    "meritz": Source("meritz", "MERITZ", "메리츠화재", _meritz_find, lambda s, item: meritz.download(s, item.handle)),
}
