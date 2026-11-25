"""수집 대상, 요일별 계획, 모델 배정. docs/planning.md 2.2, 4.4, 6.1과 같아야 한다."""
from __future__ import annotations

from dataclasses import dataclass

# 모델 배정 (6.1)
MODEL_SEARCH = "gemini-2.5-flash-lite"       # 검색 그라운딩. 하루 20회
MODEL_EXTRACT = "gemini-3.5-flash-lite"      # 추출·분류·해설. 하루 500회
MODEL_EXTRACT_ALT = "gemini-3.1-flash-lite"  # 보조·재추출
MODEL_DECIDE = "gemini-decision-1"           # 판정 전용
MODEL_SUMMARY = "gemini-3.8-flash"           # 주간 요약 최종본, 추출이 두 번 어긋난 특약의 마지막 재추출. 하루 20회
EXTRACT_ESCALATIONS_PER_RUN = 12           # 한 번 실행에서 상위 모델로 다시 뽑는 횟수 상한 (하루 20회 가운데 주간 요약 몫을 남긴다)

# 분당 한도(6.1)에 맞춘 모델별 최소 호출 간격(초). 여유를 조금 둔다.
MIN_INTERVAL = {
    MODEL_SEARCH: 7.0,        # 분당 10회
    MODEL_EXTRACT: 4.5,       # 분당 15회
    MODEL_EXTRACT_ALT: 4.5,   # 분당 15회
    MODEL_DECIDE: 0.5,        # 분당 200회
    MODEL_SUMMARY: 13.0,      # 분당 5회
}

SEARCH_DAILY_LIMIT = 20
MAX_QUERIES_PER_RUN = 6    # 질의마다 최대 3회 시도해도 하루 검색 한도 안에 들어오는 수
SEARCH_LOOKBACK_DAYS = 14  # 요일별로 주 1회 도는 것을 감안해 2주를 훑고 중복은 병합한다

# 기관코드 → 기관명 (2.2). 동향 수집 대상 생명보험사
TREND_LIFE = {
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
# 정밀 비교에만 들어가는 생명보험사. 동향 수집 19곳(2.2) 밖이라 요일별 질의(DAILY_PLAN)와 소식의 귀속 대상
# (TREND_INSTITUTIONS)에는 들지 않는다. 기관 이름(INSTITUTIONS)과 업권(LIFE)을 풀 때만 쓴다(2026-11-23)
COMPARE_ONLY_LIFE = {
    "KBLIFE": "KB라이프생명",
    "MIRAEASSET": "미래에셋생명",
    "METLIFE": "메트라이프생명",
}
LIFE = {**TREND_LIFE, **COMPARE_ONLY_LIFE}
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
TREND_INSTITUTIONS = {**TREND_LIFE, **NONLIFE, **POST}   # 동향 수집 대상 19곳. 협회·공통 소식을 귀속시킬 수 있는 회사
INSTITUTIONS = {**LIFE, **NONLIFE, **POST}               # 기관코드 → 기관명. 정밀 비교에만 들어가는 회사까지

# 제도 변화처럼 특정 회사에 속하지 않는 소식의 기관코드
COMMON = {
    "KLIA": "생명보험협회",
    "KNIA": "손해보험협회",
    "FSC": "금융위원회",
    "FSS": "금융감독원",
    "COMMON": "업계 공통",
}
ALL_ORGS = {**INSTITUTIONS, **COMMON}

# 화면에 올릴 회사(기관코드). 시트와 사본(data/snapshot)에는 회사가 하나씩 더 들어오지만, 화면 자료(site/v1/index.html,
# proto_src/console4 의 자료, proto_src/graph/graph.json)는 이 목록의 회사만 싣는다(site/orgs.py 가 사본을 읽는 자리에서 거른다).
# 화면이 새 회사를 받을 준비가 되면 여기에 더한다. 시험용으로 다른 회사를 실어 보려면 화면 자료를 만드는 명령에 --orgs 를 준다.
SITE_ORGS = ("EPOST", "HANWHALIFE", "SAMSUNGFIRE")

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
# 사람의 건강·생명 보장과 무관한 종목. 기획 2.2의 제외 목록에는 없지만 첫 수집에서 섞여 들어와 뺀다.
EXCLUDED_LINES = "반려동물(펫)보험, 여행자보험, 화재·배상책임보험"

TOPIC_PRODUCT = ("배타적사용권", "신담보출시", "상품개정")
TOPIC_UNDERWRITING = ("판매중지", "간편고지완화", "한도한시상향")
TOPIC_ALL = TOPIC_PRODUCT + TOPIC_UNDERWRITING


@dataclass(frozen=True)
class Query:
    orgs: tuple[str, ...]      # 기관코드
    topics: tuple[str, ...]    # 분류유형
    focus: str = ""            # 공통 질의에 덧붙이는 초점
    any_org: bool = False      # 참이면 소식을 19개 기관 가운데 실제 회사에 귀속시킨다


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
        Query(("KLIA",), ("배타적사용권",), "생명보험협회 신상품심의위원회의 배타적 사용권 부여 결과", any_org=True),
        Query(("KNIA",), ("배타적사용권",), "손해보험협회 신상품심의위원회의 배타적 사용권 부여 결과", any_org=True),
        Query(("FSC", "FSS"), ("제도변화",), "건강보험·제3보험 상품, 간편심사보험, 보장 한도에 관한 금융당국의 규제·감독 방침"),
        Query(("COMMON",), ("제도변화",), "보험 표준약관 개정과 한국표준질병사인분류(KCD) 개정이 보험 상품에 주는 영향"),
        Query(("COMMON",), ("판매중지", "한도한시상향"), "보험업계 전반의 절판 마케팅과 가입 한도 경쟁", any_org=True),
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

# ---------- 모델별 호출 설정 ----------
# 여기에 없는 모델은 예전과 같은 요청과 재시도를 쓴다(gemini.py의 기본값).
# 상위 모델 값은 2026-11-19에 Gemini API 공식 문서(ai.google.dev가 넘겨 주는 aistudio.google.com/docs)를 보고 정했다.
# 근거 문서: models/gemini-3.8-flash, whats-new-gemini-3.8, thinking(generateContent판), api-reference/generate-content,
# api-errors(generateContent판), troubleshooting.

# generationConfig에 덮어쓸 값. None이면 그 항목을 요청에서 뺀다.
GENERATION = {
    MODEL_SUMMARY: {
        # 문서의 출력 상한은 65,536이고, 사고 토큰도 이 상한 안에 든다("including thought tokens").
        # 예전 8,192는 기본 사고(medium)와 답 JSON이 나눠 써서 JSON이 중간에 끊긴 적이 있다.
        # 65,536이 아니라 절반으로 둔 것은, 답이 끝없이 이어질 때 아래 대기 시간보다 먼저 MAX_TOKENS로 끝나기를 바란 판단이다
        # (이 모델의 출력 속도는 문서로 확인하지 못했다).
        "maxOutputTokens": 32768,
        # 3.8은 low, medium(기본), high만 받는다. minimal은 오류이고 사고를 끌 수 없다.
        # low는 문서에서 "Fewest tokens, lowest latency". 11-19 실행의 상위 모델 실패 8건 중 5건이 시간 초과였다.
        # low와 medium의 추출 품질 차이는 확인하지 못했다. scripts/dev/try_upper_model.py --level 로 견줘 볼 수 있다.
        "thinkingConfig": {"thinkingLevel": "low"},
        # 3.6 Flash 이후 모델은 temperature를 "silently ignored"하고, 문서는 요청에서 지우라고 한다.
        "temperature": None,
    },
}

# 응답이 토큰 상한에 걸려 잘렸다고 보는 finishReason. MAX_TOKENS는 API 참조에 있는 값이다.
# CONTINUATION("per-request token limit"에 닿아 이어 받아야 함)은 문서가 Gemini 4를 두고 설명한 값인데,
# 3.8에서 오는지 확인하지 못해 같이 잘림으로 본다.
TRUNCATED_FINISH = ("MAX_TOKENS", "CONTINUATION")

# 응답 대기 시간(초). 없으면 90초.
# 상위 모델은 240초에서 끊은 일이 11-19 실행에서 5건 있었고, 그때마다 한 번 더 불러 240초를 두 번 기다렸다.
# 이제 시간 초과 뒤 되풀이하지 않으므로(아래 TIMEOUT_RETRIES), 예전 최악의 경우(240초 두 번)와 같은 480초를 한 번에 기다린다.
# 실행 전체의 최악 시간은 예전과 같다(EXTRACT_ESCALATIONS_PER_RUN 12회 × 480초). 504 오류에 대한 문서 권고도
# "Set a larger 'timeout'"이다.
TIMEOUT = {MODEL_SUMMARY: 480.0}

# 시간 초과나 연결 끊김으로 응답을 받지 못했을 때 같은 호출을 다시 하는 횟수. 없으면 1(첫 시도에서만 한 번 더).
# 상위 모델은 서버가 끝까지 처리해 하루 한도(20회)를 쓰는 것으로 보여(사용량 화면에 호출과 토큰이 잡힘) 되풀이하지 않는다.
TIMEOUT_RETRIES = {MODEL_SUMMARY: 0}

# 재시도 대기(초). 숫자 하나면 그 값의 1배, 2배, ... 를 max_retries번 기다린다(없으면 8초씩 늘림).
# 목록이면 그 간격대로 목록 길이만큼만 다시 부른다.
# 상위 모델: 문서는 503(UNAVAILABLE)에 지수적으로 늘리는 대기를 권하고, 공식 SDK의 최대 대기가 60초다.
# 지금 쓰던 30초, 60초가 그 안에 있어 그대로 둔다. 11-19의 503 세 건은 이 간격으로도 모두 실패했는데,
# 더 오래 기다릴 근거는 문서에 없고, 남은 상위 모델 횟수는 다음 특약에서 다시 쓰인다.
RETRY_WAIT = {MODEL_SUMMARY: (30.0, 60.0)}

# 분당 토큰 한도가 빠듯한 모델. 최근 60초 동안 보낸 입력 토큰(글자 수로 어림)이 이 값을 넘지 않게 호출 전에 기다린다.
# 판정 모델의 한도는 분당 5만 토큰이다. 호출 간격(MIN_INTERVAL)만으로는 못 지킨다: 2026-11-19 사용량 화면에서
# 분당 호출은 14회(한도 200회)인데 분당 토큰 최고값이 79.98K였다. 실패 기록은 없었지만 한도를 넘긴 채 다시 시도로
# 넘어간 것일 수 있어 한도에 여유 10%를 두고 지킨다.
TOKENS_PER_MINUTE = {MODEL_DECIDE: 45_000}
# 요청 본문의 글자 하나를 토큰 몇 개로 어림할지. 한글이 섞인 JSON 본문의 실제 비율은 재 보지 못해 넉넉하게 1로 둔다.
TOKENS_PER_CHAR = 1.0

# 다시 시도할 HTTP 상태. 없으면 gemini.RETRY_STATUS(429, 500, 502, 503, 504).
# 상위 모델은 504를 빼었다. 문서상 504는 서버가 정한 시간 안에 처리를 못 끝낸 것("unable to finish processing
# within the deadline")이라 같은 요청을 되풀이하면 시간과 한도만 더 쓴다.
RETRY_STATUS = {MODEL_SUMMARY: (429, 500, 502, 503)}
