"""수집 대상, 요일별 계획, 모델 배정. docs/planning.md 2.2, 4.4, 6.1과 같아야 한다."""
from __future__ import annotations

from dataclasses import dataclass

# 모델 배정 (6.1)
MODEL_SEARCH = "gemini-2.5-flash-lite"       # 검색 그라운딩. 하루 20회
MODEL_EXTRACT = "gemini-3.5-flash-lite"      # 추출·분류·해설. 하루 500회
MODEL_EXTRACT_ALT = "gemini-3.1-flash-lite"  # 보조·재추출
MODEL_DECIDE = "gemini-decision-1"           # 판정 전용
MODEL_SUMMARY = "gemini-3.8-flash"           # 주간 요약 최종본. 하루 20회

SEARCH_DAILY_LIMIT = 20
SEARCH_LOOKBACK_DAYS = 14  # 요일별로 주 1회 도는 것을 감안해 2주를 훑고 중복은 병합한다

# 기관코드 → 기관명 (2.2)
LIFE = {
    "SAMSUNGLIFE": "삼성생명",
    "HANWHALIFE": "한화생명",
    "KYOBO": "교보생명",
    "SHINHANLIFE": "신한라이프",
    "NHLIFE": "NH농협생명",
    "LINA": "라이나생명",
    "TONGYANG": "동양생명",
    "HEUNGKUKLIFE": "흥국생명",
    "KDBLIFE": "KDB생명",
}
NONLIFE = {
    "SAMSUNGFIRE": "삼성화재",
    "DB": "DB손해보험",
    "HYUNDAI": "현대해상",
    "KB": "KB손해보험",
    "MERITZ": "메리츠화재",
    "HANWHAFIRE": "한화손해보험",
    "NHFIRE": "NH농협손해보험",
    "LOTTE": "롯데손해보험",
    "HEUNGKUKFIRE": "흥국화재",
}
POST = {"EPOST": "우체국보험"}
INSTITUTIONS = {**LIFE, **NONLIFE, **POST}

# 제도 변화처럼 특정 회사에 속하지 않는 소식의 기관코드
COMMON = {
    "KLIA": "생명보험협회",
    "KNIA": "손해보험협회",
    "FSC": "금융위원회",
    "FSS": "금융감독원",
    "COMMON": "업계 공통",
}
ALL_ORGS = {**INSTITUTIONS, **COMMON}

# 모으는 소식 일곱 가지 (2.2). 값은 판정 모델에 주는 설명이다.
CATEGORIES = {
    "배타적사용권": "생명보험협회나 손해보험협회 신상품심의위원회에서 배타적 사용권을 신청했거나 받았다는 소식",
    "신담보출시": "새 보험상품, 새 특약, 새 담보를 출시했다는 소식",
    "상품개정": "기존 상품의 보장 내용, 보험료, 가입나이, 특약 구성을 바꿨다는 소식",
    "판매중지": "상품이나 특약의 판매를 중단하거나 절판한다는 소식",
    "간편고지완화": "유병자·간편심사 상품의 고지 항목이나 인수 기준을 완화했다는 소식",
    "한도한시상향": "가입금액 한도를 기간을 정해 높였거나 다시 낮췄다는 소식",
    "제도변화": "금융당국 규제, 감독규정, 표준약관, 질병분류 개정처럼 여러 회사에 영향을 주는 제도 소식",
}
NOT_APPLICABLE = "해당없음"
EXCLUDED_TOPICS = "자동차보험, 퇴직연금, 변액보험, 인사, 실적, 사회공헌, 경품 행사, 광고 모델, 주가"

TOPIC_PRODUCT = ("배타적사용권", "신담보출시", "상품개정")
TOPIC_UNDERWRITING = ("판매중지", "간편고지완화", "한도한시상향")
TOPIC_ALL = TOPIC_PRODUCT + TOPIC_UNDERWRITING


@dataclass(frozen=True)
class Query:
    orgs: tuple[str, ...]      # 기관코드
    topics: tuple[str, ...]    # 분류유형
    focus: str = ""            # 공통 질의에 덧붙이는 초점


def _pairs(orgs: tuple[str, ...]) -> list[Query]:
    return [Query(orgs, TOPIC_PRODUCT), Query(orgs, TOPIC_UNDERWRITING)]


def _each(codes: list[str]) -> list[Query]:
    return [q for c in codes for q in _pairs((c,))]


# 요일(월=0)별 검색 질의 (4.4). 일요일은 실패 건 재수집과 주간 마감에 쓴다.
DAILY_PLAN: dict[int, list[Query]] = {
    0: _each(["SAMSUNGLIFE", "HANWHALIFE", "KYOBO"]),
    1: _each(["SAMSUNGFIRE", "DB", "KB"]),
    2: _each(["HYUNDAI", "MERITZ", "HANWHAFIRE"]),
    3: _pairs(("SHINHANLIFE", "NHLIFE"))
    + _pairs(("LINA", "TONGYANG"))
    + _pairs(("HEUNGKUKLIFE", "KDBLIFE")),
    4: _pairs(("NHFIRE", "LOTTE"))
    + [Query(("HEUNGKUKFIRE",), TOPIC_ALL)]
    + _pairs(("EPOST",)),
    5: [
        Query(("KLIA",), ("배타적사용권",), "생명보험협회 신상품심의위원회의 배타적 사용권 부여 결과"),
        Query(("KNIA",), ("배타적사용권",), "손해보험협회 신상품심의위원회의 배타적 사용권 부여 결과"),
        Query(("FSC", "FSS"), ("제도변화",), "건강보험·제3보험 상품, 간편심사보험, 보장 한도에 관한 금융당국의 규제·감독 방침"),
        Query(("COMMON",), ("제도변화",), "보험 표준약관 개정과 한국표준질병사인분류(KCD) 개정이 보험 상품에 주는 영향"),
        Query(("COMMON",), ("판매중지", "한도한시상향"), "보험업계 전반의 절판 마케팅과 가입 한도 경쟁"),
    ],
    6: [],
}

PLANNED_CALLS = {0: 6, 1: 6, 2: 6, 3: 6, 4: 5, 5: 5, 6: 0}

# 판정 구간 기본값. 정답셋으로 맞추기 전의 임시값이며 hum_기준값의 판정구간 행이 있으면 그 값을 쓴다.
DEFAULT_THRESHOLDS = {
    "기사선별_통과": 0.70,
    "기사선별_보류": 0.40,
    "중복판정_동일": 0.70,
}
