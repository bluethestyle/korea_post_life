"""분석 화면(console4)의 비교 대상과 기본값 설정.

담당자가 정한 화면 범위를 한곳에 모은다. 시트의 행, 매핑, 검증 기록은 그대로 두고 화면 자료를 만드는 단계에서만 적용한다.
나중에 담당자 탭(hum_기준값 등)으로 옮길 때 이 모듈의 상수만 시트 값으로 바꾸면 되게 한다.

적용하는 곳
- 화면 비교에서 빼는 상품: insights.base_variants(기준 종형 목록, 담보 비교, 영업 인사이트 계산, 구성 예시, 한도 표)와
  sales._selling(고객군 지도와 인수기준 비교의 종형). 관계 그래프의 종형 노드와 시트 자료의 규모 수치(종형 수, 특약 수,
  급부 수)는 적재 자료 전체를 그대로 센다.
- 화면이 처음 여는 기준 종형: insights.order_bases(기준 종형 목록의 첫 항목. 화면 JS 는 목록의 첫 항목을 기본값으로 쓴다).
- 등급별 대표 종형(lineup.pick_lineup): 한 등급에 우리 정밀비교 판매 종형이 둘 이상이면 화면 기본 상품의 종형을 고른다.
"""
from __future__ import annotations

from .model import Data, _blank

# 화면 비교에서 빼는 상품(모상품ID).
# 2026-11-25 담당자 결정. 우체국통합건강보험 2504 는 실무자 의견(비교 상대로 알맞지 않음)에 따라 화면 비교에서 뺀다.
# 정답 대조와 첫 실행의 오류 사례가 제출 설명 문서의 검증 근거라 적재 자료와 매핑과 검증 기록은 지우지 않는다.
EXCLUDED_PRODUCTS: tuple[str, ...] = ("EPOST_TOTAL",)

# 화면 기본 상품(모상품ID). 화면이 처음 여는 기준 종형은 이 상품의 판매 중 기준 종형 가운데 간편고지약칭이
# lineup.DEFAULT_GRADE(3.2.5)인 종형이다. 종형ID 를 적지 않으므로 개정판이 나오면 새 개정판의 종형을 고른다.
# 2026-11-25 담당자 결정. 실무자 의견(간편보험의 통상적인 표준이 3.2.5)에 따라 1종(간편가입315)에서 2종(간편가입325)으로 바꿨다.
# hum_기준값 REP_WEEKLY_UW_2(주간 변화 집계의 대표 심사유형)와는 묶지 않는다. 그 값은 초기 버전 화면과 주간 변화 집계가 쓴다.
DEFAULT_PRODUCT = "EPOST_SIMPLE"


def product_of(data: Data, vid: str) -> str | None:
    return data.variants[vid].get("모상품ID")


def excluded(data: Data, vid: str) -> bool:
    """화면 비교에서 빼는 상품의 종형인지."""
    return product_of(data, vid) in EXCLUDED_PRODUCTS


def default_grade() -> str:
    from .lineup import DEFAULT_GRADE      # lineup 이 이 모듈을 읽으므로 부를 때 읽는다
    return DEFAULT_GRADE


def is_default_product(data: Data, vid: str) -> bool:
    return product_of(data, vid) == DEFAULT_PRODUCT


def default_base(data: Data, bases: list[str]) -> str | None:
    """화면이 처음 여는 기준 종형. bases(기준 종형 후보) 가운데 화면 기본 상품의 판매 중 종형으로 간편고지약칭이
    lineup.DEFAULT_GRADE 인 첫 종형, 그런 종형이 없으면 화면 기본 상품의 첫 종형, 그것도 없으면 bases 의 첫 종형이다."""
    grade = default_grade()
    mine = [v for v in bases if is_default_product(data, v) and _blank(data.variants[v].get("판매종료일"))]
    for vid in mine:
        if data.variants[vid].get("간편고지약칭") == grade:
            return vid
    return mine[0] if mine else (bases[0] if bases else None)


def prefer_default_product(data: Data, found: list[str]) -> list[str]:
    """한 등급의 우리 종형 후보가 둘 이상이면 화면 기본 상품의 종형만 남긴다(그런 종형이 없으면 후보 그대로)."""
    if len(found) <= 1:
        return found
    mine = [v for v in found if is_default_product(data, v)]
    return mine or found
