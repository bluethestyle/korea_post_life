"""출품작(이름은 `common.ENTRY_NAME`) 발표 시연 애니메이션 통합 진입 모듈."""

from __future__ import annotations

from part1_service import Part1ServiceScene as _Part1ServiceScene
from part2_collect_extract import Part2CollectExtractScene as _Part2CollectExtractScene
from part3_decision import Part3DecisionScene as _Part3DecisionScene
from part4_ontology_impact import Part4OntologyImpactScene as _Part4OntologyImpactScene


class Part1ServiceScene(_Part1ServiceScene):
    """서비스 목표와 운영 화면 구성 장면."""


class Part2CollectExtractScene(_Part2CollectExtractScene):
    """수집 단계와 추출 단계 장면."""


class Part3DecisionScene(_Part3DecisionScene):
    """확률 산정 모델 원리와 검증, 분류 단계 장면."""


class Part4OntologyImpactScene(_Part4OntologyImpactScene):
    """온톨로지 구조, 관계 탐색, 전후 비교 장면."""
