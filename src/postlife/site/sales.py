"""영업 인사이트: 가입 관문과 고객군 지도, 응대 포인트(docs/proposals/영업_인사이트_흐름.md 4절).

공개 자료(상품요약서, 사업방법서)에서 계산되는 것만 다룬다. 판매 시책, 수수료, 손해율, 실적, 인수 판정은 다루지 않는다.
시사점 판정(insights.analyze)은 다시 계산하지 않고 거르고 문장으로 옮기기만 한다. 검토 대기는 "없음"이 아니라 "모름"이다.

고객 조건(Profile)
- since: 마지막 입원이나 수술이 몇 년 전보다 오래됐나(0.25는 3개월). None은 이력 없음.
- surgery_only: 그 이력이 입원 없이 수술만인가. renewal: 갱신유형 거르개(None은 전체).
- 최근 3개월 소견과 5년 안 중대질병 문항은 세 회사가 같은 기간이라 입력으로 받지 않고, 문장에 전제로 붙인다.

가입 관문(question_hit, gate)
- 관문을 따지는 종형은 판매 중인 정밀비교 종형과 관문전용 종형이다(gate_targets). 관문전용 종형은 고지 질문과 주계약 가입나이,
  가입한도만 모았고 급부는 모으지 않았다. 대표 종형, 담보 비교와 시사점, 기준 종형, 지도 행의 경계(since_cuts)는 정밀비교 종형만
  쓴다(targets).
- 간편심사 종형: 이력이 없으면 해당 없음. 고지입원수술년수가 0이면 입원이나 수술의 기간 질문이 없는 종형이라 해당 없음(수술 여부보다
  먼저 본다. 빈칸은 자료 없음이다). 수술만이고 기간 질문이 수술을 묻지 않으면(고지수술포함여부 거짓) 해당 없음.
  그 밖에는 since가 고지입원수술년수 이상이면 해당 없음, 아니면 해당. 열이 비었으면 자료 없음.
- 일반심사 종형: 이력이 있든 없든 늘 심사로 확인이다(2026-11-20 사용자 결정). 사업방법서에 일반심사의 입원, 수술 질문을 몇 년이
  지나면 넘는다는 근거가 없어, 이력이 오래됐다고 해당 없음으로 보지 않는다. 그래서 일반심사 종형은 열림이 되지 않는다.
- 종형 상태: 질문 해당이나 나이 불가는 닫힘, 질문 자료 없음, 심사로 확인, 나이 자료 없음(질문 해당 없음이고 가입나이 자료가
  없음), 열림. 회사 상태는 종형 상태 가운데 STATE_ORDER로 앞선 것이다.

고객군 지도(classify, simple_classify, cell, segment_map)
- 칸 분류는 우리 상태(U)와 상대 상태(열림, 닫힘, 모름. 심사로 확인은 닫힘으로 센다)로 가른다. 관문 상태이지 우열이 아니다.
  열린 상대가 있으면 함께 열림이나 우리만 닫힘이다. 열린 상대가 없을 때 상태를 모르는 상대(나이 자료 없음, 질문 자료 없음)가
  하나라도 있으면 그 상대가 열려 있을 수 있어 자료 없음이고, 모두 닫혔으면 우리만 열림이나 모두 닫힘이다.
  안쪽 분류(classify)는 회사 상태(일반심사 종형 포함)로 가른 값이고, 화면의 라벨과 관문 포인트 G1, G2는 간편심사 종형만 본
  분류(simple_classify)를 따른다. 일반심사 종형은 열리지 않으므로 두 분류는 거의 같다. 우리 간편이 열리지 않은 칸에 심사로 확인인
  우리 일반심사 종형(가입나이가 맞는 것)이 있으면 보조 줄 "일반심사 확인"을 단다. 두 분류 모두 관문전용 종형까지 본 상태다.
- 칸의 숫자는 우리 대표 종형과 상대 대표 종형을 견준 시사점에서 센다(분류수: 다섯 분류 이름과 검토 대기. 관문 차이는 그 칸의
  관문 포인트 수). 대표는 열린 간편심사 종형에서 고르고, 없으면 심사로 확인인 일반심사 종형(가입나이가 맞는 것)에서 고른다
  (our_rep, peer_reps). 상대 대표가 compare.peers의 짝과 다르면 insights.analyze_pair로 그 쌍을 다시 돌린다. 대표는 정밀비교
  종형에서만 고르므로, 상대 회사에서 열린 종형이 관문전용뿐이면 칸의 관문만수집에 그 종형을 적는다(GATE_NOTE).
- 지도 행의 경계(since_cuts)는 최근 소견 질문의 기간과 정밀비교 간편심사 종형의 고지입원수술년수에서 나온다.
- 갱신유형 거르개가 있으면 칸의 회사, 대표, 관문 포인트의 짝 모두 거르개 안의 종형만 쓴다.
- 지도와 관문 탭에 늘 붙이는 주석은 NOTES(글과 출처)다. 내보내기의 "주석"에 싣는다.

응대 포인트(points, render, scope)
- 세부 여덟 가지(DETAILS). 문장은 TEMPLATES의 틀에 자료 값을 끼워 만든다. 값이 비면 그 포인트를 내지 않고 뺀포인트에 적는다.
- 틀과 코드가 만든 값에 금지어(FORBIDDEN)가 들면 render가 ForbiddenWordError를 낸다. 공시 자료에서 온 이름과 조건 값
  (DATA_KEYS. 담보명 "종별 수술비(최고 종 기준)", 지급 형태 "최초 1회" 따위)은 사실을 옮긴 것이라 검사에서 뺀다.
- 근거 급부가 작업 로그 검토 대기이면 같은 종형, 같은 표준담보의 확정 급부로 바꾸고, 바꿀 급부가 없으면 포인트를 뺀다.
- 기준 종형은 판매 중인 정밀비교 우체국 종형만 받는다(points, scope가 다른 종형에 ValueError). 틀이 기준 앞에 "우체국"을 붙인다.
- 감액은 받는 비율로 적는다("가입 뒤 1년까지 보험금의 50%를 지급합니다"). 감액지급률은 그 기간에 지급하는 비율이다. 조건 나음과
  못함(A2, Q3)은 명사 조각을 잇지 않고 쪽마다 동사 절로 적는다(condition_values). 견준 급부의 면책 기간이 모두 같고 0보다 크면
  "{담보}의 면책 기간은 두 상품 모두 90일입니다."를 앞에 적는다.
- 조사는 앞말의 받침으로 고른다(has_final). 괄호로 끝나는 말은 괄호 앞 말을 본다("2종(간편가입325)이").
- 관문 포인트(gate_points)의 G1, G2는 관문전용 종형까지 본 라벨 분류를 따른다. G1은 우리 종형의 질문과 상대 종형의 질문을 햇수로
  적는다. G2는 기준 종형이 나이로 닫힌 칸(열린 상대 종형의 가입나이를 적고, 그 나이가 우체국 일반심사 종형의 가입나이 안이면 그
  종형을 덧붙인다)과 고지 질문에 걸린 칸(열린 상대 종형의 기간 질문을 적는다)에 낸다. G3은 같은 기간 질문의 범위나 질병 수가 다른
  짝과 함께, 상대 회사가 우리 간편 종형 어느 것보다 입원과 수술 기간 질문이 짧거나 없는 종형을 팔면 그 사실을 적는다.
  짝과 견준 G3은 기간 질문의 수술 포함 여부, 중대질병 질문의 질병(수와 고지중대질병목록), 최근 소견 질문의 범위(고지소견범위)
  가운데 하나라도 다르면 낸다(scope_diff). 질병 목록이 양쪽에 다 있으면 한쪽만 묻는 질병 이름을 적는다.
  관문전용 종형을 적은 포인트는 머리말(머리말_관문)과 문장(G3_미수집)에 담보를 수집하지 않았다고 적는다.

다섯 분류와 문장 둘(합의안 4번. 이용자는 본부의 영업 기획과 분석 담당자다)
- 분류는 세부에서 정해지고 서로 겹치지 않는다(CATEGORY): 관문 차이(G1, G2, G3), 앞세울 강점(A1, A2), 관련 담보 안내(Q1),
  조건 열위 방어(Q3), 개정 검토 후보(Q2. 좁은 담보만 가진 것 포함). 지급 형태가 달라 우열을 매기지 않은 것은 조건 열위에 넣지 않고
  단정 주의 목록(caution)에 둔다.
- "문장"은 분석 문장(사실을 적는 평서문)이고, "카드질문"과 "카드답"은 응대 카드 미리 보기에서만 쓰는 창구 말투다. 관문(G2, G3)과
  앞세울 강점은 분석 문장을 카드에도 그대로 쓴다(카드질문 없음). 원문 대조가 필요한 포인트는 "원문대조글"을 단다.
  꼬리 문장(Q2_좁은, Q3_경과)은 분석 문장과 카드 답에 함께 붙는다. 입원 담보의 A1에는 주의(A1_주의)를 "주의"에 싣고 문장 끝에도 붙인다.

회사가 많을 때(비교 대상이 생명보험 10곳, 손해보험 9곳으로 늘어난다. 셋까지는 지금 문장 그대로다)
- 회사나 종형 이름을 잇는 곳(and_join, or_join에 UNIT_ORG, UNIT_KIND를 준 곳)은 넷 이상이면 "A, B, C 등 N곳"(종형은 "등 N개")으로
  줄인다. 종형마다 한 문장씩 잇던 G2(가입나이, 기간 질문), 지급 형태 다름의 상대 문장, 범위의 구조 문장은 넷 이상이면 값이 같은 것끼리
  묶어 적는다. 근거 목록, 비교종형ID, 범위의 상대는 줄이지 않는다.
- 범위 문장은 상대 회사가 넷 이상이면 상품을 다 적지 않고 업권별 회사 수와 상품 수를 적는다(scope_products_many). 포인트와 단정
  주의의 머리말(header)도 상품마다 적지 않고 회사 수, 상품 수, 기준일의 범위를 적는다. 상품마다의 머리말은 범위의 상대에 남는다.
- 지도 칸마다 상대 회사 수를 상태별로 센다(peer_tally). 브리핑 (가)의 값에 칸마다 열린 상대 수의 분포를 싣고, (라)는 상대가 넷
  이상이면 상대마다의 보유 수 대신 범위와 중앙값을 적는다.
- 화면이 고른 비교 범위(상대 회사 일부)로 다시 셀 수 있게, 지도 칸에는 센 상대의 기관코드 목록(peer_codes)을, 포인트에는 견준
  상대의 기관코드(관련기관코드)를 싣는다. 기준 종형별로 관문 나무의 종형을 고지 유형 열쇠(notice_key)로 묶은 수(notice_groups)를
  싣는다. 화면은 교집합의 크기만 세고 열림과 닫힘을 다시 판정하지 않는다.

분석 담당자용 집계(합의안 5번): 단정 주의 목록(caution), 개정 검토 목록(revision_candidates), 치료 여정 격자(journey),
한도 표(limit_steps), 보류 요약(pending_summary). 먼저 보일 것(pick, 합의안 7번), 지도 칸의 이름(cell의 라벨, 보조, 닫힌사유,
합의안 6번), 브리핑 다섯 줄(briefing, 합의안 3번), 화면용 내보내기(export)는 각 함수의 설명에 규칙을 적는다.
"""
from __future__ import annotations

import hashlib
import re
import statistics
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .. import ids
from . import compare as C
from . import eligibility
from . import insights as I
from . import revision as RV
from . import weekly
from .model import Cond, Data, HOME_ORG, MAX_AGE, SECTOR_LIFE, SECTOR_NONLIFE, _blank
from .relations import Relations, load_relations


# ---------- 고객 조건 ----------
@dataclass(frozen=True)
class Profile:
    age: int | None = None
    sex: str | None = None          # "M", "F"
    since: float | None = None      # 마지막 입원이나 수술이 몇 년 전보다 오래됐나(0.25, 1, 2, 3, 4, 5). None은 이력 없음
    surgery_only: bool = False      # 그 이력이 입원 없이 수술만인가
    renewal: str | None = None      # "갱신", "비갱신". None은 전체

    def key(self) -> str:
        return f"{self.age}|{self.sex}|{self.since}|{int(self.surgery_only)}|{self.renewal}"


# ---------- 이름 ----------
SIMPLE, GENERAL = "간편심사", "일반심사"

Q_NONE, Q_HIT, Q_REVIEW, Q_NODATA = "해당 없음", "해당", "심사로 확인", "자료 없음"
OPEN, NO_AGE, NO_QUESTION, REVIEW, CLOSED = "열림", "나이 자료 없음", "질문 자료 없음", "심사로 확인", "닫힘"
STATE_ORDER = (OPEN, NO_AGE, NO_QUESTION, REVIEW, CLOSED)
AGE_OK, AGE_NO, AGE_NODATA = "가능", "불가", "자료 없음"

ONLY_OPEN, BOTH_OPEN, ONLY_CLOSED, ALL_CLOSED, NO_DATA = "우리만 열림", "함께 열림", "우리만 닫힘", "모두 닫힘", "자료 없음"
CLASSES = (ONLY_OPEN, BOTH_OPEN, ONLY_CLOSED, ALL_CLOSED, NO_DATA)
ALL_CLOSED_NOTE = "일반심사로 확인"

HOSPITAL, SURGERY_ONLY = "입원", "수술만"

GATE, LEAD, ASK = "관문", "앞세울 것", "물어올 것"
KINDS = (GATE, LEAD, ASK)
DETAILS = {
    "G1": (GATE, "우리만 열림"), "G2": (GATE, "우리만 닫힘"), "G3": (GATE, "질문 범위 다름"),
    "A1": (LEAD, "따로 주는 담보"), "A2": (LEAD, "조건 나음"),
    "Q1": (ASK, "관련 담보 있음"), "Q2": (ASK, "없음"), "Q3": (ASK, "조건 못함"),
}
CODES = tuple(DETAILS)
REVISION_TAG = "개정 검토"

# 다섯 분류(합의안 4번). 세부에서 정해지고 서로 겹치지 않는다.
GATE_DIFF, STRENGTH, RELATED, DEFEND, REVISE = "관문 차이", "앞세울 강점", "관련 담보 안내", "조건 열위 방어", "개정 검토 후보"
CATEGORIES = (GATE_DIFF, STRENGTH, RELATED, DEFEND, REVISE)
CARD_ORDER = (GATE_DIFF, STRENGTH, DEFEND, RELATED, REVISE)      # 카드의 처음 선택(합의안 7번)
CATEGORY = {"G1": GATE_DIFF, "G2": GATE_DIFF, "G3": GATE_DIFF, "A1": STRENGTH, "A2": STRENGTH, "Q1": RELATED,
            "Q3": DEFEND, "Q2": REVISE}
SOURCE_CHECK_TEXT = "사업방법서 원문 확인 필요"
PICK_SLOTS = 8                     # 브리핑과 응대 카드의 처음 선택 수

# 목적 묶음(기획 3.3절의 추천 목적 세 가지). 화면 이름은 합의안 9번이 정했다.
PURPOSES = ("암", "3대 질병", "입원과 수술")
PURPOSE_BASIS = (
    {"이름": "암", "기준": "보장 대분류 기준", "값": ["암보장"]},
    {"이름": "3대 질병", "기준": "보장 대분류 기준", "값": sorted(I.FOCUS_MAJORS, key=lambda m: C.GROUP_ORDER.index(m))},
    {"이름": "입원과 수술", "기준": "급부유형 기준", "값": ["입원", "수술"]},
)

# 브리핑과 탭(합의안 2번, 3번)
TAB_BRIEF, TAB_MARKET, TAB_GATE, TAB_COMPARE, TAB_INSIGHT = "브리핑", "고객군과 시장", "가입 관문", "담보 비교", "영업 인사이트"
TABS = (TAB_BRIEF, TAB_MARKET, TAB_GATE, TAB_COMPARE, TAB_INSIGHT)
SCOPE_ALL, SCOPE_BASE = "전체 고객군", "선택 종형"
JOURNEY_TYPES = ("진단", "수술", "치료", "입원", "통원")
NOTICE = "공모전 시연용 화면이며 영업 자료가 아닙니다"

# 지도 칸의 이름(합의안 6번). 분류 값(CLASSES)은 안쪽 값으로 두고 화면에는 라벨을 쓴다.
LABELS = {ONLY_OPEN: "우리 간편만 열림", BOTH_OPEN: "함께 열림", ONLY_CLOSED: "우리 간편 닫힘",
          ALL_CLOSED: "간편 모두 닫힘", NO_DATA: "자료 없음"}
GENERAL_NOTE = "일반심사 확인"
CLOSED_AGE, CLOSED_QUESTION = "나이", "고지 질문"
GATE_ROLE = "관문전용"            # 관문 표시에만 쓰는 종형(고지 질문과 주계약 가입조건만 모았다)
GATE_NOTE = "관문만 수집(담보 미수집)"

# 최근 소견 질문의 "필요 소견" 범위(sys_상품종형 고지소견범위 값, validate.py의 허용값)를 G3 문장에 적는 말
OPINION_TEXT = {"서면": "진단서나 소견서 같은 서면에 적힌 소견을",
                "서면과 진료기록부": "진료기록부에 적고 설명하거나 권유한 소견까지"}

# 지도(고객군과 시장 탭)와 가입 관문 탭에 늘 붙이는 주석. 글은 고정이고 금지어 검사를 거친다(시험).
# 간편 청약 제한은 세 회사 사업방법서의 간편고지 운영 규정에서 확인했다(2026-11-20. 우체국 9~10쪽, 한화생명 8~9쪽,
# 삼성화재 97~98쪽. 우체국과 삼성화재는 직전 3개월 안의 일반심사 가입, 한화생명은 청약을 적는다).
NOTES = (
    {"열쇠": "지도전제", "탭": [TAB_MARKET],
     "글": "지도는 고지 질문 가운데 입원과 수술의 기간 질문, 그리고 가입나이만 봅니다. "
           "최근 소견과 중대질병 질문에 해당하지 않는 고객을 전제로 합니다.",
     "출처": "가입 관문 계산 규칙(영업 인사이트 흐름 설계안)"},
    {"열쇠": "간편청약제한", "탭": [TAB_MARKET, TAB_GATE],
     "글": "간편심사 상품은 일반심사 가입이 어려운 고객이 대상입니다. 직전 3개월 안에 같은 회사의 일반심사 상품에 "
           "가입했거나 청약한 고객은 간편 청약이 제한될 수 있습니다.",
     "출처": "무배당 우체국간편한건강보험(20년갱신형) 2606 사업방법서, 한화생명 시그니처 H통합보험 무배당 사업방법서, "
             "무배당 삼성화재 간편보험 새로고침(2607.5)(자동갱신형) 사업방법서의 간편고지 운영 규정"},
    {"열쇠": "수술만행", "탭": [TAB_MARKET],
     "글": "'수술만' 행은 입원 없이 받은 수술입니다. 입원을 함께 한 수술은 입원 행으로 봅니다.",
     "출처": "가입 관문 계산 규칙(영업 인사이트 흐름 설계안)"},
    {"열쇠": "일반심사", "탭": [TAB_MARKET, TAB_GATE],
     "글": "일반심사 종형은 이력과 무관하게 심사로 확인합니다.",
     "출처": "가입 관문 계산 규칙(영업 인사이트 흐름 설계안)"},
)

# 단정 주의 목록의 종류
CAUTION_OTHER, CAUTION_PAY = "조건이 다른 특약 함께 판매", "지급 형태 다름"

# 설계안 4.2의 틀에 쓰지 않는 말
FORBIDDEN = ("업계", "유일", "독점", "최초", "최고", "가장", "더 좋다", "유리", "우수", "저렴", "가성비", "실속",
             "가입됩니다", "거절됩니다", "권하세요", "추천", "바꾸세요", "갈아타세요")

# {키} 또는 {키:조사}. 조사는 앞 글자의 받침으로 고른다(은/는, 이/가, 을/를, 과/와, 이나/나).
TEMPLATES = {
    # G1은 우리 종형의 질문(우리질문. 질문_기간 틀)과 상대 종형의 질문을 햇수로 적는다
    "G1": "{이력}이고 최근 {소견개월}개월 소견과 {중대년수}년 안 중대질병에 해당하지 않으시면, "
          "우체국 {우리종형}의 고지 질문({우리질문})에는 해당하지 않습니다. {상대문장} 가입 여부는 청약 뒤 심사로 정해집니다.",
    "G1_상대_기간": "{상대:은} {상대기간}년 안의 {상대범위:을} 묻습니다.",
    "질문_기간": "{기간}년 안 {범위}",
    "질문_기간만": "기간 {기간}년",
    "G2": "{나이}세는 우체국 {우리종형}의 가입나이({우리최저}~{우리최고}세) 밖입니다. {상대문장}",
    "G2_상대": "{상대}의 가입나이는 {상대최저}~{상대최고}세입니다.",
    # 열린 상대 종형이 넷 이상이고 가입나이가 넷 이상으로 갈리면 하한과 상한의 범위만 적는다("15~18", 같으면 "15")
    "G2_상대많음": "{상대}의 가입나이 하한은 {하한}세, 상한은 {상한}세입니다.",
    # 그 나이가 우체국 일반심사 종형(심사로 확인이고 가입나이가 맞는 것. 대표 고르는 차례로 하나)의 가입나이 안이면 붙인다
    "G2_일반": "우체국에서는 일반심사 종형({일반종형}, {일반최저}~{일반최고}세)으로 심사를 받을 수 있습니다.",
    # 기준 종형이 고지 질문에 걸린 칸의 G2. 열린 상대 종형마다 기간 질문을 적는다(기간이 있으면 G1_상대_기간 틀)
    "G2_질문": "{이력}인 고객은 우체국 {우리종형}의 고지 질문에 해당합니다. {상대문장} 가입 여부는 청약 뒤 심사로 정해집니다.",
    "G2_상대_질문없음": "{상대:은} 입원과 수술의 기간 질문이 없습니다.",
    "G3": "최근 {기간}년 안의 입원과 수술 질문에서 우체국 {우리종형:은} {우리범위:을}, {상대:은} {상대범위:을} 묻습니다. "
          "{중대년수}년 안 중대질병 질문의 질병 수는 우체국 {우리수}개, {상대회사} {상대수}개입니다.",
    "G3_범위": "최근 {기간}년 안의 입원과 수술 질문에서 우체국 {우리종형:은} {우리범위:을}, {상대:은} {상대범위:을} 묻습니다.",
    "G3_질병수": "{중대년수}년 안 중대질병 질문의 질병 수는 우체국 {우리종형} {우리수}개, {상대} {상대수}개입니다.",
    # 양쪽에 고지중대질병목록이 있으면 한쪽만 묻는 질병을 괄호로 적는다(질병차이는 G3_한쪽질병을 이은 것)
    "G3_목록": "최근 {기간}년 안의 입원과 수술 질문에서 우체국 {우리종형:은} {우리범위:을}, {상대:은} {상대범위:을} 묻습니다. "
              "{중대년수}년 안 중대질병 질문의 질병 수는 우체국 {우리수}개, {상대회사} {상대수}개입니다({질병차이}).",
    "G3_질병수_목록": "{중대년수}년 안 중대질병 질문의 질병 수는 우체국 {우리종형} {우리수}개, {상대} {상대수}개입니다({질병차이}).",
    "G3_한쪽질병": "{상대회사}만 묻는 질병: {질병}",
    # 최근 소견 질문의 "필요 소견" 범위가 다르다(우리소견, 상대소견은 OPINION_TEXT의 말)
    "G3_소견": "최근 {소견개월}개월 소견 질문에서 우체국은 {우리소견}, {상대회사:은} {상대소견} 묻습니다.",
    # 상대 회사가 우리 간편 종형 어느 것보다 입원과 수술 기간 질문이 짧거나 없는 종형을 판다
    "G3_질문없음": "{상대회사:은} 입원과 수술의 기간 질문이 없는 {상대종형:을} 함께 팝니다.",
    "G3_짧은": "{상대회사:은} {상대기간}년 안의 {상대범위:을} 묻는 {상대종형:을} 함께 팝니다.",
    "G3_미수집": "이 종형은 고지 질문과 주계약 가입조건만 모았고 담보는 수집하지 않았습니다.",
    "A1": "{담보:은} 우체국 {우리종형}에 따로 있는 담보입니다. 견준 {상대회사목록} 상품에는 이 담보를 따로 주는 급부가 없습니다.",
    # 없는 회사가 넷 이상이면 상대회사목록은 "A, B, C 등 N곳"으로 줄인 이름이다(_shortened)
    "A1_많음": "{담보:은} 우체국 {우리종형}에 따로 있는 담보입니다. 견준 {상대회사목록}의 상품에는 이 담보를 따로 주는 급부가 "
             "없습니다.",
    "A1_주의": "상대의 일반 입원 담보로 같은 입원이 지급될 수 있습니다.",
    # 조건 나음(A2)과 조건 못함(Q3). 조건문은 절_* 틀로 만든 쪽마다의 절을 _connect로 이은 것이다(우리 쪽이 먼저).
    # 견준 급부의 면책 기간이 모두 같고 0보다 크면 _면책같음 틀로 그 사실을 앞에 적는다
    "A2": "{담보:은} 우체국 {우리종형:이} {조건문}.",
    "A2_면책같음": "{담보}의 면책 기간은 {상품수} 상품 모두 {면책일}일입니다. 우체국 {우리종형:은} {조건문}.",
    "조건_상대": "{상대:은} {상대조건}",
    "조건절_상대": "{상대:은} {상대절}",
    "절_면책": "면책 기간이 {면책일}일입니다",
    "절_면책없음": "면책 기간이 없습니다",
    "절_감액": "가입 뒤 {감액:을} 지급합니다",
    "절_감액없음": "감액 기간이 없습니다",
    "절_지급": "지급 형태가 {지급형태}입니다",
    "Q_질문": "{상대회사}에는 {담보:이} 있던데요.",
    "Q1": "우체국 {우리종형}에는 {담보:을} 따로 주는 담보가 없습니다. {덮는담보}의 지급 사유에 해당하면 그 담보로 지급됩니다. "
          "금액과 지급 횟수는 다를 수 있어 약관으로 확인해 드리겠습니다.",
    "Q2": "우체국 {우리종형}에는 {담보:을} 따로 주는 담보는 없습니다.",
    "Q3_질문": "{담보:은} {상대회사:이} 조건이 다르던데요.",
    "Q3": "맞습니다. {담보:은} 우체국 {우리종형:이} {조건문}.",
    "Q3_면책같음": "맞습니다. {담보}의 면책 기간은 {상품수} 상품 모두 {면책일}일입니다. 우체국 {우리종형:은} {조건문}.",
    "Q3_경과": "{경과:이} 지나면 {모두} 보험금 전액을 지급합니다.",
    "머리말": "수집한 {상품} 기준({기준일})",
    "머리말_관문": "관문만 수집한 {상품} 기준({기준일}, 담보 미수집)",
    # 상대 회사가 넷 이상이면 상품마다 적지 않는다(header. 상품마다의 머리말은 범위의 상대에 있다)
    "머리말_많음": "수집한 {상대회사수}곳의 상품 {상품수}개 기준({기준일})",
    "머리말_많음_관문": "수집한 {상대회사수}곳의 상품 {상품수}개 기준({기준일}, 그 가운데 {미수집수}개는 담보 미수집)",
    "구조": "구조 다름: 우체국 {우리구조} 대 {상대구조}",
    "회사수": "견준 {전체}개 회사 가운데 {해당}곳",
    # 범위 띠의 문장: 견준 상품(범위), 구조가 다른 상대가 있으면 갱신과 환급 구조(범위_구조), 견준 쌍(범위_대기, 범위_모두)
    "범위": "견준 상품은 {상품목록}입니다.",
    "범위_상품": "{상품}({기준일} 기준)",
    "범위_상품_관문": "{상품}({기준일} 기준, 담보 미수집)",
    # 상대 회사가 넷 이상이면 상품을 다 적지 않는다(scope_products_many. 상품 목록은 범위의 상대에 있다)
    "범위_많음": "견준 상품은 {업권나눔}의 상품 {상품수}개입니다.",
    "범위_많음_업권모름": "견준 상품은 상대 {상대회사수}곳의 상품 {상품수}개입니다.",
    "범위_미수집수": "그 가운데 {미수집수}개는 담보를 수집하지 않은 상품입니다.",
    "범위_구조": "갱신과 환급 구조는 우체국이 {우리구조}이고 {상대문장}입니다.",
    "구조_상대": "{상대:은} {상대구조}",
    "범위_대기": "공통 담보 {비교쌍}쌍 가운데 {뺀비교쌍}쌍은 검토 대기라 견주지 않았습니다.",
    "범위_모두": "공통 담보 {비교쌍}쌍을 모두 견줬습니다.",
    "범위_쌍없음": "견준 공통 담보는 없습니다.",

    # 분석 문장(본문). 위의 G1, Q1, Q2, Q3 틀은 응대 카드의 답으로 쓴다.
    "G1_분석": "{이력}이고 최근 {소견개월}개월 소견과 {중대년수}년 안 중대질병에 해당하지 않는 고객은 우체국 {우리종형}의 "
              "고지 질문({우리질문})에 해당하지 않습니다. {상대문장} 가입 여부는 청약 뒤 심사로 정해집니다.",
    "Q1_분석": "{상대회사목록}에 있는 {담보:을} 따로 주는 담보는 우체국 {우리종형}에 없습니다. "
              "{덮는담보}의 지급 사유에 해당하면 그 담보로 지급됩니다. 금액과 지급 횟수는 다를 수 있어 약관 확인이 필요합니다.",
    "Q2_분석": "{상대회사목록}에 있는 {담보:은} 우체국 {우리종형}에 없습니다.",
    "Q2_좁은": "우체국에는 이보다 좁은 {좁은담보}만 있습니다.",
    "Q3_분석": "{담보:은} 우체국 {우리종형:이} {조건문}.",
    "Q3_분석_면책같음": "{담보}의 면책 기간은 {상품수} 상품 모두 {면책일}일입니다. 우체국 {우리종형:은} {조건문}.",

    # 단정 주의 목록
    "주의_상대": "{담보:은} {상대:이} 조건이 다른 특약을 함께 팔아 우열을 단정하지 않았습니다"
               "(견준 급부 말고 조건이 다른 급부가 {상대줄}개 더 있음).",
    "주의_기준": "{담보:은} 우체국 {우리종형}에 조건이 다른 특약이 함께 있어 {상대:과} 우열을 단정하지 않았습니다"
               "(견준 급부 말고 조건이 다른 급부가 {기준줄}개 더 있음).",
    "주의_양쪽": "{담보:은} 우체국 {우리종형:과} {상대} 모두 조건이 다른 특약을 함께 팔아 우열을 단정하지 않았습니다"
               "(견준 급부 말고 조건이 다른 급부가 우체국에 {기준줄}개, {상대회사}에 {상대줄}개 더 있음).",
    # 지급차이는 지급 형태 꼬리표에서 실제로 다른 것(pay_difference: 지급 한도 일수, 지급 시작일, 둘 다, 그 밖은 지급 형태)
    "주의_지급": "{담보:은} {지급차이:이} 달라 우열을 매기지 않았습니다. 우체국 {우리종형:은} {우리지급형태}, {상대문장}입니다.",
    # 같은 상대와 면책이나 감액으로 조건 우열이 난 담보: 우열을 매기지 않은 범위를 지급 형태로 좁히고 그 포인트를 가리킨다
    "주의_지급_조건": "{담보}의 {지급차이:은} 서로 달라 우열을 매기지 않았습니다. 우체국 {우리종형:은} {우리지급형태}, "
                 "{상대문장}입니다.",
    "주의_지급_조건상대": "{상대:과} 견준 {조건항목} 조건은 {조건분류}에 따로 적었습니다.",
    "지급_상대": "{상대:은} {상대지급형태}",

    # 브리핑 다섯 줄(합의안 3번). 줄마다 한두 문장이다. 0건이면 _없음 틀로 가른다.
    # (가)는 라벨 다섯 가운데 0칸이 아닌 라벨을 모두 적는다(절목록. 칸 수의 합이 전체칸수다). 우리만과 함께는 0칸이어도 적되
    # 뒤에 0칸이 아닌 절이 있을 때만 적는다. 둘째 문장에 관문만 열린 칸과 나이 자료가 없는 상대를 이어 적는다(_connect).
    "가": "고객군 {전체칸수}칸 가운데 {절목록}입니다.",
    "가_우리만": "우리 간편만 열리는 곳은 {우리간편만열림칸수}칸({우리간편만열림요약})",
    "가_우리만_없음": "우리 간편만 열리는 곳은 없고",
    "가_함께": "함께 열리는 곳은 {함께열림칸수}칸",
    "가_함께_없음": "함께 열리는 곳은 없고",
    "가_닫힘": "우리 간편이 닫혀 일반심사로 확인할 곳은 {우리간편닫힘칸수}칸",
    "가_닫힘_일부": "우리 간편이 닫힌 곳은 {우리간편닫힘라벨칸수}칸(그 가운데 일반심사로 확인할 곳 {우리간편닫힘칸수}칸)",
    "가_닫힘_없음": "우리 간편이 닫힌 곳은 없고",
    "가_모두닫힘": "간편이 모두 닫힌 곳은 {간편모두닫힘칸수}칸",
    "가_모름": "상대 상태를 몰라 가르지 못한 곳은 {자료없음칸수}칸",
    "가_관문만": "{관문만칸수}칸은 상대 회사에서 열리는 종형이 우체국에 없는 고지 유형({관문만종형})뿐입니다.",
    "가_관문만_같은유형": "{관문만칸수}칸은 상대 회사에서 열리는 종형이 담보를 수집하지 않은 종형({관문만종형})뿐입니다.",
    "가_나이자료없음": "{나이자료없음회사:은} 가입나이 자료가 없어 지도에서 상태를 모르는 상대로 셉니다.",
    "가_자료없음": "고객군 지도를 그릴 가입조건 자료가 없습니다.",
    "나": "{절1}, {절2}",
    "나_개정": "{개정상품:을} 직전 개정과 견주어 달라진 담보는 {개정변동수}개({개정나눔})이고",
    "나_개정_없음": "{개정상품:을} 직전 개정과 견주어 달라진 담보는 없고",
    "나_개정_자료없음": "견줄 우체국 직전 개정 자료는 없고",
    "나_소식": "최근 모은 시장 소식은 {시장소식수}건(표준담보에 이어진 것 {연결소식수}건)입니다.",
    "나_소식_연결없음": "최근 모은 시장 소식은 {시장소식수}건이며 표준담보에 이어진 소식은 없습니다.",
    "나_소식_없음": "최근 모은 시장 소식은 없습니다.",
    "다": "기준 종형 우체국 {우리종형}의 {절1}, {절2}, {절3}",
    "다_상대없음": "기준 종형 우체국 {우리종형}의 {절1}, 맞붙는 상대 종형은 없습니다.",
    "다_나이": "가입나이는 {우리최저}~{우리최고}세({나이}세 기준 주계약 한도 {주계약한도만원}만원)이고",
    "다_나이_나이밖": "가입나이는 {우리최저}~{우리최고}세({나이}세는 가입나이 밖)이고",
    "다_나이_한도모름": "가입나이는 {우리최저}~{우리최고}세({나이}세 기준 주계약 한도 자료 없음)이고",
    "다_나이_나이없음": "가입나이는 {우리최저}~{우리최고}세이고",
    "다_나이없음": "가입나이 자료는 없고",
    "다_관문": "고지 질문 범위가 다른 상대는 {관문차이수}곳",
    "다_관문_없음": "고지 질문 범위가 다른 상대는 없고",
    "다_관문_일반": "일반심사 종형이라 간편 고지 질문은 견주지 않았으며",
    "다_구조": "갱신이나 환급 구조가 다른 상대는 {구조다름회사수}곳입니다.",
    "다_구조_없음": "갱신이나 환급 구조가 다른 상대는 없습니다.",
    # (라)는 두 문장이다. 첫 문장은 견준 쌍(라_범위*)과 우열을 단정하지 않은 비교(라_보류*)를 잇고(_connect), 둘째 문장은 보유
    # 수(라_보유*. 치료 여정 격자의 합이라 공통 담보 쌍 안의 수가 아니다)다
    "라": "{절1} {절2}",
    "라_범위": "공통 담보 {공통담보쌍}쌍 가운데 검토 대기 {뺀비교쌍}쌍을 빼고 {견준쌍}쌍을 견줬습니다.",
    "라_범위_대기없음": "공통 담보 {견준쌍}쌍을 모두 견줬습니다.",
    "라_범위_모두대기": "공통 담보 {뺀비교쌍}쌍이 모두 검토 대기라 견준 쌍은 없습니다.",
    "라_범위_없음": "견준 공통 담보는 없습니다.",
    "라_보유": "확정 급부 기준으로 우체국 {우리종형:이} 가진 담보는 모두 {보유수}개({보유나눔})입니다.",
    "라_보유_상대": "확정 급부 기준으로 우체국 {우리종형:이} 가진 담보는 모두 {보유수}개({보유나눔})이고, "
                 "맞붙는 상대 종형은 {상대보유나눔}입니다.",
    "라_보유_없음": "확정 급부 기준으로 우체국 {우리종형:이} 가진 담보는 없습니다.",
    "라_보유_없음_상대": "확정 급부 기준으로 우체국 {우리종형:이} 가진 담보는 없고, 맞붙는 상대 종형은 {상대보유나눔}입니다.",
    "라_상대보유": "{상대} {보유수}개",
    # 상대가 넷 이상이면 상대마다의 보유 수 대신 상대 회사 수와 보유 수의 범위, 중앙값을 적는다(상대보유요약)
    "라_보유_상대많음": "확정 급부 기준으로 우체국 {우리종형:이} 가진 담보는 모두 {보유수}개({보유나눔})이고, "
                   "상대 {상대회사수}곳의 보유 담보는 {상대보유요약}입니다.",
    "라_보유_없음_상대많음": "확정 급부 기준으로 우체국 {우리종형:이} 가진 담보는 없고, 상대 {상대회사수}곳의 보유 담보는 "
                     "{상대보유요약}입니다.",
    "라_상대보유범위": "{최소}~{최대}개(중앙값 {중앙}개)",
    "라_상대보유같음": "모두 {최소}개",
    "라_보류": "우열을 단정하지 않은 비교는 조건이 다른 특약을 함께 판매한 것 {단정보류수}건, "
              "지급 형태가 다른 것 {지급형태다름수}건입니다.",
    "라_보류_없음": "우열을 단정하지 않은 비교는 없습니다.",
    # (마)는 다섯 분류를 모두 적는다(합이 전체수). 검토 대기로 뺀 비교쌍이 있으면 _검토후 틀로 전제를 붙인다
    "마": "지금 자료에서 나온 영업 인사이트는 모두 {전체수}건으로, 관문 차이 {관문차이수}건, {절1}, 관련 담보 안내 {관련담보수}건, "
         "조건 열위 방어 {조건열위수}건, 개정 검토 후보 {개정검토수}건입니다.",
    "마_검토후": "검토를 마친 범위에서 나온 영업 인사이트는 모두 {전체수}건으로, 관문 차이 {관문차이수}건, {절1}, "
              "관련 담보 안내 {관련담보수}건, 조건 열위 방어 {조건열위수}건, 개정 검토 후보 {개정검토수}건입니다.",
    "마_강점": "앞세울 강점 {앞세울수}건({대표강점요약})",
    "마_강점_요약없음": "앞세울 강점 {앞세울수}건",
    "마_강점_없음": "앞세울 강점 0건",
    "마_없음": "지금 자료에서 나온 영업 인사이트는 없습니다.",
    "마_없음_검토후": "검토를 마친 범위에서 나온 영업 인사이트는 없습니다.",
}
# 공시 자료에서 온 이름과 조건 값, 이미 render를 거친 문장. 금지어 검사에서 뺀다.
DATA_KEYS = {"담보", "우리종형", "상대", "상대회사", "상대종형", "상대회사목록", "덮는담보", "우리조건", "상대조건", "상대문장",
             "상품", "우리구조", "상대구조", "머리말", "좁은담보", "우리지급형태", "상대지급형태", "대표강점요약",
             "절1", "절2", "절3", "절목록", "질병", "질병차이", "관문만종형", "나이자료없음회사", "개정상품", "개정전상품",
             "상대보유나눔", "우리질문", "일반종형", "조건문", "상대절", "지급형태", "상품목록", "범위"}

_SLOT = re.compile(r"\{([^{}:]+)(?::([^{}]+))?\}")
_JOSA = {"은": ("은", "는"), "는": ("은", "는"), "이": ("이", "가"), "가": ("이", "가"), "을": ("을", "를"),
         "를": ("을", "를"), "과": ("과", "와"), "와": ("과", "와"), "이나": ("이나", "나"), "나": ("이나", "나")}


class TemplateValueMissing(ValueError):
    """틀의 자리에 끼울 값이 없다. 그 포인트는 내지 않는다."""


class ForbiddenWordError(ValueError):
    """틀이나 코드가 만든 값에 금지어가 들었다."""


# ---------- 문장 ----------
def _before_paren(s: str) -> str | None:
    """")"로 끝나는 말에서 그 괄호 묶음 앞의 말(뒤 공백은 뗀다). 짝이 맞는 "("가 없으면 None."""
    depth = 0
    for i in range(len(s) - 1, -1, -1):
        if s[i] == ")":
            depth += 1
        elif s[i] == "(":
            depth -= 1
            if depth == 0:
                return s[:i].rstrip()
    return None


def has_final(word: str) -> bool:
    """마지막 글자에 받침이 있게 읽히는지. 숫자와 로마자는 읽는 소리로 본다.

    괄호로 끝나는 말은 괄호 앞 말의 받침을 따른다("2종(간편가입325)이", "유사암 진단비(통합)가". 괄호 묶음이 이어 붙으면 모두
    걷는다). 괄호 뒤에 글자가 더 있는 말("7종(해약환급금 미지급형) 315·5")은 마지막 글자를 본다. 괄호 앞에 말이 없으면 괄호 안의
    마지막 글자를 본다. 닫는 따옴표는 건너뛴다.
    """
    s = str(word).rstrip()
    while s.endswith(")"):
        head = _before_paren(s)
        if not head:
            break
        s = head
    while s and s[-1] in ")]}」』'\"’” ":
        s = s[:-1]
    if not s:
        return False
    c = s[-1]
    if "가" <= c <= "힣":
        return (ord(c) - 0xAC00) % 28 != 0
    if c.isdigit():
        return c in "013678"          # 영(십, 백, 천), 일, 삼, 육, 칠, 팔
    if c.isascii() and c.isalpha():
        return c.upper() in "LMNR"     # 엘, 엠, 엔, 알
    return False


def josa(word: str, particle: str) -> str:
    pair = _JOSA.get(particle)
    if pair is None:
        return str(word) + particle
    return str(word) + (pair[0] if has_final(word) else pair[1])


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(_text(v) for v in value)
    if isinstance(value, float):
        return I._num_text(value)
    return str(value)


def _empty(value: Any) -> bool:
    return value is None or value == "" or (isinstance(value, (list, tuple)) and not value)


def forbidden_in(text: str) -> list[str]:
    return [w for w in FORBIDDEN if w in text]


def render(template_id: str, values: dict[str, Any]) -> str:
    """틀에 값을 끼운다. 값이 비면 TemplateValueMissing, 틀이나 DATA_KEYS 밖의 값에 금지어가 들면 ForbiddenWordError."""
    tpl = TEMPLATES[template_id]
    bad = forbidden_in(_SLOT.sub(" ", tpl))
    if bad:
        raise ForbiddenWordError(f"{template_id} 틀에 금지어: {', '.join(bad)}")

    def fill(m: re.Match) -> str:
        key, particle = m.group(1), m.group(2)
        value = values.get(key)
        if _empty(value):
            raise TemplateValueMissing(key)
        text = _text(value)
        if key not in DATA_KEYS:
            hit = forbidden_in(text)
            if hit:
                raise ForbiddenWordError(f"{template_id}의 {key} 값에 금지어: {', '.join(hit)}")
        return josa(text, particle) if particle else text

    return _SLOT.sub(fill, tpl)


_FINAL_B = 17          # 받침 ㅂ의 순번(한글 음절 = 0xAC00 + (초성 × 21 + 중성) × 28 + 받침)


def _connective(clause: str) -> str:
    """"…니다"로 끝나는 절(마침표는 뗀다)을 "…고"로 바꾼다. "입니다"는 "이고", "없습니다"는 "없고", "지급합니다"는 "지급하고",
    "셉니다"는 "세고"다. 다른 꼴이면 ValueError(틀을 고칠 일이다)."""
    s = clause.rstrip().removesuffix(".")
    if not s.endswith("니다"):
        raise ValueError(f"'…니다'로 끝나지 않는 절: {clause}")
    stem = s[:-2]
    if stem.endswith("습"):
        return stem[:-1] + "고"
    c = stem[-1:]
    code = ord(c) - 0xAC00 if c else -1
    if 0 <= code < 11172 and code % 28 == _FINAL_B:
        return stem[:-1] + chr(ord(c) - _FINAL_B) + "고"
    raise ValueError(f"'…ㅂ니다'나 '…습니다'로 끝나지 않는 절: {clause}")


def _connect(clauses: list[str], sep: str = ", ") -> str:
    """render를 거친 "…니다" 절들을 한 문장으로 잇는다. 마지막 절 앞은 "…고"로 바꾼다(_connective). 마지막 절은 그대로 둔다."""
    return sep.join([_connective(c) for c in clauses[:-1]] + clauses[-1:])


# 회사나 종형 이름을 이을 때 줄이는 기준(회사가 많을 때). MANY 개 이상이면 앞의 SHOWN 개만 적고 "등 N곳"(회사), "등 N개"(종형)로
# 줄인다. 셋까지는 줄이지 않는다(세 회사 사본의 문장은 그대로다). 줄인 이름의 전체 목록은 포인트의 비교종형ID와 근거, 범위의 상대에 남는다
MANY, SHOWN = 4, 3
UNIT_ORG, UNIT_KIND = "곳", "개"
SECTOR_UNKNOWN = "업권 모름"        # 범위의 업권별에서 업권을 모르는 상대(Data.org_sector가 None)


def _shortened(names: list[str], unit: str | None) -> str | None:
    """"A, B, C 등 18곳". unit이 없거나 이름이 MANY 개보다 적으면 None(줄이지 않는다)."""
    if unit is None or len(names) < MANY:
        return None
    return f"{', '.join(names[:SHOWN])} 등 {len(names)}{unit}"


def or_join(names: Iterable[str], unit: str | None = None) -> str:
    """"한화생명이나 삼성화재"처럼 잇는다. unit(UNIT_ORG, UNIT_KIND)을 주면 넷 이상일 때 "A, B, C 등 N곳"으로 줄인다."""
    names = [str(n) for n in names]
    if not names:
        return ""
    short = _shortened(names, unit)
    if short:
        return short
    return "".join(josa(n, "이나") + " " for n in names[:-1]) + names[-1]


def and_join(names: Iterable[str], unit: str | None = None) -> str:
    """"한화생명 간편가입형(1년)과 삼성화재 7종"처럼 잇는다. 셋 이상이면 앞은 쉼표로 잇는다.
    unit(UNIT_ORG는 회사 이름, UNIT_KIND는 종형 이름)을 주면 넷 이상일 때 "A, B, C 등 N곳"("등 N개")으로 줄인다.
    표준담보 이름이나 조건 항목처럼 회사와 종형이 아닌 이름은 unit 없이 부른다(줄이지 않는다)."""
    names = [str(n) for n in names]
    short = _shortened(names, unit)
    if short:
        return short
    if len(names) < 2:
        return names[0] if names else ""
    return ", ".join(names[:-2] + [josa(names[-2], "과") + " " + names[-1]])


# ---------- 종형 ----------
def _variant(data: Data, vid: str) -> dict[str, Any]:
    return data.variants[vid]


def _org(data: Data, vid: str) -> str:
    return data.variants[vid].get("기관코드")


def _org_name(data: Data, vid: str) -> str:
    return data.org_name(_org(data, vid))


def _kind_name(data: Data, vid: str) -> str:
    return str(data.variants[vid].get("종형명") or vid)


def _peer_name(data: Data, vid: str) -> str:
    """"한화생명 간편가입형(1년)". 문장 안에서 상대 종형을 부르는 이름이다."""
    return f"{_org_name(data, vid)} {_kind_name(data, vid)}"


def _kind_rest(product: str, kind: str, least: int = 4) -> str:
    """종형명 가운데 공시상품명 끝과 겹치지 않는 나머지. 띄어쓰기는 보지 않는다.

    "…(자동갱신형) 7종(해약환급금미지급형)"과 "7종(해약환급금 미지급형) 325·5"는 "325·5"만 남긴다. least 글자보다 짧게 겹치면 겹침으로 보지 않는다.
    """
    p, k = "".join(product.split()), "".join(kind.split())
    if k and k in p:
        return ""
    for n in range(len(k) - 1, least - 1, -1):
        if p.endswith(k[:n]):
            seen = 0
            for i, ch in enumerate(kind):
                seen += not ch.isspace()
                if seen == n:
                    return kind[i + 1:].strip()
    return kind


def full_name(data: Data, vid: str) -> str:
    """회사, 공시상품명, 종형명. 공시상품명에 회사명이나 종형명이 이미 들어 있으면 한 번만 적는다. 회사명은 줄이지 않는다."""
    v = data.variants[vid]
    org, product, kind = _org_name(data, vid), str(v.get("공시상품명") or ""), str(v.get("종형명") or "")
    head = product if org in product else f"{org} {product}"
    rest = _kind_rest(product, kind)
    return head + (f" {rest}" if rest else "")


def _period(v: dict[str, Any]) -> int | None:
    return v.get("고지입원수술년수") if v.get("심사유형") == SIMPLE else None


def _range_text(v: dict[str, Any]) -> str | None:
    return {True: "입원과 수술", False: "입원"}.get(v.get("고지수술포함여부"))


def _structure(v: dict[str, Any]) -> str:
    return f"{v.get('갱신유형') or '갱신유형 모름'}, {v.get('환급유형') or '환급유형 모름'}"


def structure_differs(data: Data, base: str, peer: str) -> bool:
    b, p = data.variants[base], data.variants[peer]
    return b.get("갱신유형") != p.get("갱신유형") or b.get("환급유형") != p.get("환급유형")


def targets(data: Data, renewal: str | None = None) -> list[str]:
    """견줄 종형: 정밀비교이고 판매 중인 종형. renewal이 있으면 갱신유형이 같은 종형만. 지도 행의 경계(since_cuts)가 쓴다."""
    return _selling(data, (C.COMPARE_ROLE,), renewal)


def gate_targets(data: Data, renewal: str | None = None) -> list[str]:
    """관문을 따질 종형: targets에 판매 중인 관문전용 종형을 더한 것. gate가 쓴다."""
    return _selling(data, (C.COMPARE_ROLE, GATE_ROLE), renewal)


def _selling(data: Data, roles: tuple[str, ...], renewal: str | None) -> list[str]:
    return [v for v in data.variant_order
            if data.variants[v].get("비교역할구분") in roles and _blank(data.variants[v].get("판매종료일"))
            and (renewal is None or data.variants[v].get("갱신유형") == renewal)]


def gate_only(data: Data, vid: str) -> bool:
    """관문전용 종형인지. 급부를 모으지 않아 대표 종형이나 담보 비교에 쓰지 않는다."""
    return data.variants[vid].get("비교역할구분") == GATE_ROLE


# ---------- 가입 관문 ----------
def question_hit(variant: dict, p: Profile) -> str:
    """고객 이력이 종형의 고지 질문에 걸리는지: 해당 없음, 해당, 심사로 확인, 자료 없음(모듈 설명의 규칙)."""
    uw = variant.get("심사유형")
    if uw == SIMPLE:
        if p.since is None:
            return Q_NONE
        years = variant.get("고지입원수술년수")
        if years == 0:                    # 입원이나 수술의 기간 질문이 없는 종형(빈칸 None은 자료 없음이다)
            return Q_NONE
        if p.surgery_only:
            surgery = variant.get("고지수술포함여부")
            if surgery is None:
                return Q_NODATA
            if surgery is False:
                return Q_NONE
        if years is None:
            return Q_NODATA
        return Q_NONE if p.since >= years else Q_HIT
    if uw == GENERAL:                     # 이력이 있든 없든 심사가 정한다(모듈 설명)
        return Q_REVIEW
    return Q_NODATA


def variant_gate(data: Data, vid: str, p: Profile) -> dict[str, Any]:
    """종형 하나의 관문 상태. 나이는 model.age_limit(주계약, Cond(age, sex))로 본다."""
    q = question_hit(data.variants[vid], p)
    main = data.main_rider(vid)
    lim = data.age_limit(main, Cond(age=p.age, sex=p.sex)) if main else None
    if lim is None or lim.no_data:
        age = AGE_NODATA
    else:
        age = AGE_OK if lim.ok else AGE_NO
    if q == Q_HIT or age == AGE_NO:
        state = CLOSED
    elif q == Q_NODATA:
        state = NO_QUESTION
    elif q == Q_REVIEW:
        state = REVIEW
    elif age == AGE_NODATA:
        state = NO_AGE
    else:
        state = OPEN
    return {"종형ID": vid, "질문": q, "나이": age, "상태": state,
            "한도만원": lim.amount if lim is not None and lim.ok else None}


def gate(data: Data, p: Profile) -> dict[str, Any]:
    """회사별, 종형별 관문 상태. 회사 상태는 종형 상태 가운데 STATE_ORDER로 앞선 것이다. 관문전용 종형도 본다(gate_targets)."""
    out: dict[str, dict[str, Any]] = {}
    for vid in gate_targets(data, p.renewal):
        out.setdefault(_org(data, vid), {"상태": None, "종형": []})["종형"].append(variant_gate(data, vid, p))
    for g in out.values():
        g["상태"] = min((x["상태"] for x in g["종형"]), key=STATE_ORDER.index)
    return {"조건": p, "회사": out}


def _side(state: str | None) -> str | None:
    """칸 분류에 쓰는 쪽: 열림, 닫힘(심사로 확인 포함), 자료 없음(None)."""
    if state == OPEN:
        return OPEN
    if state in (CLOSED, REVIEW):
        return CLOSED
    return None


def _by_sides(us: str | None, others: Iterable[str | None]) -> str:
    """우리 쪽과 상대 쪽들(열림, 닫힘, 모름 None)로 칸을 가른다. 열린 상대가 없는데 모르는 상대가 있으면 자료 없음이다
    (모르는 상대가 열려 있을 수 있어 "우리만 열림"이나 "모두 닫힘"이라고 할 수 없다)."""
    others = list(others)
    known = [s for s in others if s is not None]
    if us is None or not known:
        return NO_DATA
    if OPEN in known:
        return BOTH_OPEN if us == OPEN else ONLY_CLOSED
    if len(known) < len(others):
        return NO_DATA
    return ONLY_OPEN if us == OPEN else ALL_CLOSED


def classify(gate_result: dict[str, Any]) -> tuple[str, list[str]]:
    """(칸 분류, 자료 없는 회사). 회사 상태(일반심사 종형 포함)로 가르는 안쪽 값이다. 일반심사 종형은 늘 심사로 확인(닫힘 쪽)이라
    라벨 분류(simple_classify)와 거의 같다. 자료 없는 회사는 상태가 나이 자료 없음이나 질문 자료 없음인 회사다.
    화면의 라벨은 simple_classify로 정한다."""
    comp = gate_result["회사"]
    us = _side(comp.get(HOME_ORG, {}).get("상태"))
    nodata = [o for o, g in comp.items() if _side(g["상태"]) is None]
    return _by_sides(us, (_side(g["상태"]) for o, g in comp.items() if o != HOME_ORG)), nodata


def _is_simple(data: Data, vid: str) -> bool:
    return data.variants[vid].get("심사유형") == SIMPLE


def simple_side(data: Data, company: dict[str, Any]) -> str | None:
    """회사의 간편심사 종형만 본 쪽: 열림, 닫힘, 자료 없음(None). 거르개 안에 간편심사 종형이 없으면 닫힘으로 본다
    (그 거르개에서 파는 간편 상품이 없다. 비갱신 거르개의 우체국이 그렇다)."""
    states = [x["상태"] for x in company["종형"] if _is_simple(data, x["종형ID"])]
    if not states:
        return CLOSED
    return _side(min(states, key=STATE_ORDER.index))


def simple_classify(data: Data, gate_result: dict[str, Any]) -> tuple[str, list[str]]:
    """(라벨 분류, 간편 자료 없는 회사). 라벨("우리 간편만 열림" 따위)과 관문 포인트 G1, G2가 쓰는 칸 분류다(합의안 6번).

    우리와 상대 모두 간편심사 종형만 본다. 우리 간편이 열리지 않은 칸에서 일반심사로 확인할 수 있다는 것은 보조 줄(general_note)이
    적는다. 우리 종형이 거르개 안에 하나도 없으면 자료 없음이다.
    """
    comp = gate_result["회사"]
    sides = {o: simple_side(data, g) for o, g in comp.items()}
    nodata = [o for o, s in sides.items() if s is None]
    if HOME_ORG not in comp:
        return NO_DATA, nodata
    return _by_sides(sides[HOME_ORG], (s for o, s in sides.items() if o != HOME_ORG)), nodata


# ---------- 계산 저장소 ----------
class _Ctx:
    """analyze() 결과를 다시 쓰고, 짝이 다른 쌍은 analyze_pair로 돌려 담아 둔다."""

    def __init__(self, data: Data, analysis: dict | None, relations: Relations | None):
        self.data = data
        self.rel = load_relations() if relations is None else relations
        self.vids, self.bases = I.base_variants(data)
        self.order = I.std_order(data)
        self.hold: dict[str, I.Holding] = {}
        self.results: dict[tuple, dict] = {}
        self.counted: dict[tuple, dict] = {}
        for r in (analysis or {}).get("기준", []):
            self.results[(r["종형ID"], tuple(p["종형ID"] for p in r["맞붙는종형"]))] = r

    def default_peers(self, base: str) -> list[str]:
        return [p for p in C.peers(self.data, base, self.vids) if p != base]

    def peers_within(self, base: str, renewal: str | None) -> list[str]:
        """갱신유형 거르개 안의 종형에서 compare.peers 규칙으로 고른 짝. renewal이 None이면 default_peers와 같다."""
        if renewal is None:
            return self.default_peers(base)
        vids = [v for v in self.vids if v == base or self.data.variants[v].get("갱신유형") == renewal]
        return [p for p in C.peers(self.data, base, vids) if p != base]

    def check_base(self, base: str) -> None:
        """기준 종형은 판매 중인 정밀비교 우체국 종형(insights.base_variants의 기준 종형)뿐이다.

        문장 틀이 기준 종형 앞에 "우체국"을 붙이므로, 경쟁사 종형이나 판매를 마친 종형을 받으면 틀린 문장이 나온다.
        """
        if base not in self.data.variants:
            raise ValueError(f"종형이 없음: {base}")
        if base not in self.bases:
            raise ValueError(f"기준 종형이 아님(판매 중인 정밀비교 우체국 종형만 받는다): {base}")

    def result(self, base: str, peers: Iterable[str] | None = None) -> dict[str, Any]:
        self.check_base(base)
        peers = self.default_peers(base) if peers is None else [p for p in peers if p != base]
        key = (base, tuple(peers))
        if key not in self.results:
            self.results[key] = I.analyze_pair(self.data, base, peers, self.rel, self.hold)
        return self.results[key]

    def holding(self, vid: str) -> I.Holding:
        if vid not in self.hold:
            self.hold[vid] = I.Holding(self.data, vid)
        return self.hold[vid]


def _ctx(data: Data, analysis: dict | None, relations: Relations | None, ctx: _Ctx | None) -> _Ctx:
    return ctx if ctx is not None else _Ctx(data, analysis, relations)


# ---------- 고객군 지도 ----------
def _rank(data: Data, vid: str) -> tuple:
    """대표로 고르는 순서: 질문 기간이 있는 간편심사 가운데 기간이 긴 것, 그다음 일반심사. 같으면 화면 순서."""
    period = _period(data.variants[vid])
    return (0 if period is not None else 1, -(period or 0), data.variant_order.index(vid))


def reviewable_general(data: Data, x: dict[str, Any], unknown_age: bool = False) -> bool:
    """variant_gate 결과 x가 심사로 확인인 일반심사 종형이고 가입나이가 맞는지. unknown_age이면 가입나이 자료 없음도 받는다
    (상대 대표는 나이 자료 없는 종형도 견준다)."""
    ages = (AGE_OK, AGE_NODATA) if unknown_age else (AGE_OK,)
    return (data.variants[x["종형ID"]].get("심사유형") == GENERAL and x["상태"] == REVIEW and x["나이"] in ages
            and not gate_only(data, x["종형ID"]))


def our_rep(data: Data, home: dict[str, Any] | None) -> str | None:
    """우리 대표 종형. 열린 간편심사 가운데 질문 기간이 가장 긴 것, 없으면 심사로 확인이고 가입나이가 맞는 일반심사 종형의
    첫째(일반심사 종형은 열리지 않는다). 관문전용 종형은 고르지 않는다."""
    if not home:
        return None
    opened = [x["종형ID"] for x in home["종형"] if x["상태"] == OPEN and not gate_only(data, x["종형ID"])]
    if not opened:
        opened = [x["종형ID"] for x in home["종형"] if reviewable_general(data, x)]
    return min(opened, key=lambda v: _rank(data, v)) if opened else None


def peer_reps(ctx: _Ctx, gate_result: dict[str, Any], rep: str) -> dict[str, str]:
    """상대 회사마다 대표 종형. 후보는 열림이나 나이 자료 없음인 종형이고, 우리 대표가 일반심사 종형이면 심사로 확인인 일반심사
    종형(가입나이가 맞거나 자료 없음)도 후보다(우리가 일반심사로 견주는 칸은 상대도 일반심사로 견준다). 후보 가운데
    compare.peers가 우리 대표에 고르는 종형, 그 종형이 후보에 없으면 남은 것 가운데 질문 기간이 가장 긴 것(일반심사는 간편심사
    뒤)이다. 관문전용 종형은 급부가 없어 고르지 않는다(그 회사에서 열린 종형이 관문전용뿐이면 대표가 없다)."""
    data = ctx.data
    preferred = ctx.default_peers(rep)
    general = data.variants[rep].get("심사유형") == GENERAL
    out = {}
    for org, g in gate_result["회사"].items():
        if org == HOME_ORG:
            continue
        cands = [x["종형ID"] for x in g["종형"]
                 if (x["상태"] in (OPEN, NO_AGE) and not gate_only(data, x["종형ID"]))
                 or (general and reviewable_general(data, x, unknown_age=True))]
        if not cands:
            continue
        pick = next((v for v in preferred if v in cands), None)
        out[org] = pick or min(cands, key=lambda v: _rank(data, v))
    return out


PENDING_COUNT = "검토 대기"


def _kept(ctx: _Ctx, base: str, peers: list[str]) -> dict[str, Any]:
    """대표끼리 견준 시사점을 응대 포인트 규칙(4.2의 거르기)으로 거른 포인트와 검토 대기로 뺀 시사점 수. 쌍마다 한 번만 계산한다."""
    key = (base, tuple(peers))
    if key not in ctx.counted:
        result = ctx.result(base, peers)
        kept, _ = insight_points(ctx, result)
        ctx.counted[key] = {"포인트": kept, "대기": len(result["뺀시사점"])}
    return ctx.counted[key]


def counts(ctx: _Ctx, base: str, peers: list[str]) -> dict[str, int]:
    """칸의 숫자(안쪽 값. 세부 이름 고유, 빈자리, 못함, 나음과 대기). 화면은 다섯 분류 이름의 category_counts를 쓴다."""
    k = _kept(ctx, base, peers)
    n = {c: sum(1 for x in k["포인트"] if x["세부"] == c) for c in ("A1", "Q2", "Q3", "A2")}
    return {"고유": n["A1"], "빈자리": n["Q2"], "못함": n["Q3"], "나음": n["A2"], "대기": k["대기"]}


def category_counts(ctx: _Ctx, base: str, peers: list[str]) -> dict[str, int]:
    """칸의 인사이트 수를 다섯 분류 가운데 시사점에서 오는 넷(앞세울 강점, 관련 담보 안내, 조건 열위 방어, 개정 검토 후보)과
    검토 대기로 센다. 영업 인사이트 탭의 분류집계와 같은 이름이고 같은 거르기를 거친 수다."""
    k = _kept(ctx, base, peers)
    out = {c: sum(1 for x in k["포인트"] if x["분류"] == c) for c in CATEGORIES if c != GATE_DIFF}
    return {**out, PENDING_COUNT: k["대기"]}


def cell(data: Data, p: Profile, analysis: dict | None, relations: Relations | None = None,
         ctx: _Ctx | None = None) -> dict[str, Any]:
    """지도 칸 하나. 우리 대표나 상대 대표가 없으면 숫자를 비운다(None).

    분류는 회사 상태로 가른 안쪽 값(classify)이고, 라벨은 간편심사 종형만 본 분류(simple_classify)의 화면 이름이다.
    열린종형은 회사별 열린 종형ID다(관문전용 종형 포함). 칸을 눌렀을 때 패널이 보이는 값이고, 지도의 이웃 구간을 합칠지 가를 때도 쓴다.
    분류수는 칸의 인사이트 수를 다섯 분류 이름으로 센 것이다. 관문 차이는 그 칸의 관문 포인트 수(cell_gate_points)이고,
    나머지 넷과 검토 대기는 우리 대표와 상대 대표를 견준 수(category_counts)다. 견줄 대표가 없으면 그 다섯은 None이다.
    수는 안쪽 값(counts)으로 남겨 둔다. 관문만수집은 열린 종형이 관문전용뿐인 상대 회사의 그 종형이다(gate_only_open).
    """
    ctx = _ctx(data, analysis, relations, ctx)
    g = gate(data, p)
    cls, nodata = classify(g)
    shown, _ = simple_classify(data, g)
    home = g["회사"].get(HOME_ORG)
    rep = our_rep(data, home)
    reps = peer_reps(ctx, g, rep) if rep else {}
    paired = bool(rep and reps)
    found, _ = cell_gate_points(ctx, p, g)
    insight = category_counts(ctx, rep, list(reps.values())) if paired else {}
    out = {"분류": cls, "라벨": LABELS[shown], "보조": general_note(data, home),
           "닫힌사유": closed_reasons(data, home, p.renewal),
           "회사": {o: x["상태"] for o, x in g["회사"].items()}, "대표": rep, "상대대표": reps,
           "수": counts(ctx, rep, list(reps.values())) if paired else None,
           "분류수": {GATE_DIFF: len(found), **{c: insight.get(c) for c in CATEGORIES if c != GATE_DIFF},
                    PENDING_COUNT: insight.get(PENDING_COUNT)},
           "자료없음": nodata,
           "열린종형": {o: [y["종형ID"] for y in x["종형"] if y["상태"] == OPEN] for o, x in g["회사"].items()},
           "관문만수집": gate_only_open(data, g)}
    out.update(peer_tally(out["회사"], out["관문만수집"]))
    if cls == ALL_CLOSED:
        out["안내"] = ALL_CLOSED_NOTE
    return out


PEER_TALLY = ("상대수", "열린상대수", "닫힌상대수", "모르는상대수", "관문만열린상대수")


def peer_tally(states: dict[str, str], gate_only_rows: list[dict[str, Any]]) -> dict[str, int]:
    """칸의 상대 회사 수(회사가 많을 때 화면이 이름 대신 수로 보일 값). states는 칸의 회사별 상태(cell의 "회사")다.
    열린 상대는 회사 상태가 열림, 닫힌 상대는 닫힘이나 심사로 확인, 모르는 상대는 나이 자료 없음이나 질문 자료 없음이다(_side).
    관문만 수집한 종형으로만 열린 회사(gate_only_open)는 열린 쪽에 세고, 그 수를 관문만열린상대수로 따로도 둔다."""
    sides = [_side(s) for o, s in states.items() if o != HOME_ORG]
    counts = (len(sides), sides.count(OPEN), sides.count(CLOSED), sides.count(None),
              len({y["기관코드"] for y in gate_only_rows}))
    return dict(zip(PEER_TALLY, counts))


PEER_CODES = ("열린상대코드", "관문만열린상대코드", "닫힌상대코드", "모르는상대코드")


def peer_codes(states: dict[str, str], gate_only_rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    """peer_tally가 센 상대 회사의 기관코드 목록(정렬). 화면이 고른 비교 범위(상대 회사 일부)와의 교집합 크기만 세면 되게 한다.
    목록마다 길이가 peer_tally의 열린상대수, 관문만열린상대수, 닫힌상대수, 모르는상대수와 같다(관문만열린상대코드는
    열린상대코드에도 든다)."""
    sides = {o: _side(s) for o, s in states.items() if o != HOME_ORG}
    codes = (sorted(o for o, s in sides.items() if s == OPEN), sorted({y["기관코드"] for y in gate_only_rows}),
             sorted(o for o, s in sides.items() if s == CLOSED), sorted(o for o, s in sides.items() if s is None))
    return dict(zip(PEER_CODES, codes))


def compared_orgs(data: Data, vids: Iterable[str]) -> list[str]:
    """종형 목록이 속한 상대 회사의 기관코드(우리 기관은 뺀다, 정렬). 포인트의 관련기관코드(비교종형ID)에 쓴다."""
    return sorted({_org(data, v) for v in vids} - {HOME_ORG, None})


NOTICE_UNKNOWN = "모름"


def notice_key(data: Data, vid: str) -> str:
    """종형의 고지 유형 열쇠. 일반심사 종형은 "일반심사", 간편심사 종형은 종형 표의 고지 열(고지최근소견개월,
    고지입원수술년수, 고지중대질병년수)을 가운뎃점으로 이은 "3·2·5" 꼴(입원과 수술의 기간 질문이 없는 종형은 그 열이 0이라
    가운데가 0)이다. 심사유형을 모르거나 세 열 가운데 빈 값이 있으면 "모름"이다. 같은 열쇠의 종형을 화면이 한 묶음으로 그린다."""
    v = data.variants[vid]
    kind = v.get("심사유형")
    if kind == GENERAL:
        return GENERAL
    vals = [v.get("고지최근소견개월"), v.get("고지입원수술년수"), v.get("고지중대질병년수")]
    if kind != SIMPLE or any(_blank(x) for x in vals):
        return NOTICE_UNKNOWN
    return "·".join(I._num_text(x) for x in vals)


def _notice_order(key: str) -> tuple:
    if key == GENERAL:
        return (1, ())
    if key == NOTICE_UNKNOWN:
        return (2, ())
    return (0, tuple(float(x) for x in key.split("·")))


def notice_groups(data: Data, base: str, peers: list[str]) -> list[dict[str, Any]]:
    """기준 종형별 고지 유형 집계(고지유형별). 관문 나무가 그리는 종형(gate_targets, 관문전용 포함)을 고지 유형 열쇠(notice_key)로
    묶어, 열쇠마다 상대 회사 수(상대수)와 그 기관코드(상대코드), 상대 종형 수(종형수), 우리 종형 수(우리종형수), 이 기준 종형의
    맞붙는 종형 가운데 그 열쇠인 수(맞붙는종형수)를 센다. 기준은 기준 종형의 열쇠와 같은 묶음이다. 차례는 간편 열쇠(소견 개월,
    입원수술 년수, 중대질병 년수의 작은 순), 일반심사, 모름이다."""
    groups: dict[str, dict[str, Any]] = {}

    def group(k: str) -> dict[str, Any]:
        return groups.setdefault(k, {"열쇠": k, "orgs": set(), "종형수": 0, "우리종형수": 0, "맞붙는종형수": 0})

    for v in gate_targets(data):
        g = group(notice_key(data, v))
        if _org(data, v) == HOME_ORG:
            g["우리종형수"] += 1
        else:
            g["orgs"].add(_org(data, v))
            g["종형수"] += 1
    for v in peers:
        group(notice_key(data, v))["맞붙는종형수"] += 1
    mine = notice_key(data, base)
    group(mine)
    out = []
    for k in sorted(groups, key=_notice_order):
        g = groups[k]
        orgs = sorted(o for o in g.pop("orgs") if o)
        out.append({"열쇠": k, "기준": k == mine, "상대수": len(orgs), "상대코드": orgs, **{n: g[n] for n in
                    ("종형수", "우리종형수", "맞붙는종형수")}})
    return out


def gate_only_open(data: Data, g: dict[str, Any]) -> list[dict[str, Any]]:
    """열린 종형이 관문전용 종형뿐인 상대 회사의 그 종형들. 칸의 라벨은 이 종형까지 본 상태이지만 담보는 견주지 않았다(대표가 없다).
    [{"기관코드", "종형ID", "이름", "안내"}]. 안내는 GATE_NOTE다."""
    out = []
    for org, x in g["회사"].items():
        if org == HOME_ORG:
            continue
        opened = [y["종형ID"] for y in x["종형"] if y["상태"] == OPEN]
        if opened and all(gate_only(data, v) for v in opened):
            out += [{"기관코드": org, "종형ID": v, "이름": _peer_name(data, v), "안내": GATE_NOTE} for v in opened]
    return out


def _simple_open(data: Data, home: dict[str, Any] | None) -> bool:
    return bool(home) and any(x["상태"] == OPEN and _is_simple(data, x["종형ID"]) for x in home["종형"])


def general_note(data: Data, home: dict[str, Any] | None) -> str:
    """칸의 보조 줄. 우리 간편심사 종형이 하나도 열리지 않았고 심사로 확인인 우리 일반심사 종형 가운데 가입나이가 맞는 것이
    있으면 "일반심사 확인"이다(우리 대표가 그 종형이다). 일반심사 종형이 나이로 닫혔거나 나이 자료가 없으면 적지 않는다."""
    if not home or _simple_open(data, home):
        return ""
    return GENERAL_NOTE if any(reviewable_general(data, x) for x in home["종형"]) else ""


def closed_reasons(data: Data, home: dict[str, Any] | None, renewal: str | None) -> list[str]:
    """우리 간편이 열리지 않은 까닭(우리 간편심사 종형이 하나라도 열렸으면 빈 목록. 일반심사 종형만 열린 칸은 사유를 적는다).

    거르개 안에 우리 간편심사 종형이 없으면 "{갱신유형} 간편 종형 없음"만 적는다(비갱신 거르개에서 닫히는 까닭은 나이가 아니라
    우체국에 비갱신 간편 종형이 없어서다). 있으면 간편 종형 가운데 나이로 닫힌 것이 있으면 "나이", 고지 질문에 걸린 것이 있으면
    "고지 질문"이다. 질문이나 나이 자료가 없는 종형은 닫힌 것이 아니라 모르는 것이라 적지 않는다.
    """
    if _simple_open(data, home):
        return []
    simple = [x for x in (home["종형"] if home else []) if _is_simple(data, x["종형ID"])]
    if not simple:
        return [f"{renewal} 간편 종형 없음" if renewal else "간편 종형 없음"]
    out = []
    if any(x["나이"] == AGE_NO for x in simple):
        out.append(CLOSED_AGE)
    if any(x["질문"] == Q_HIT for x in simple):
        out.append(CLOSED_QUESTION)
    return out


def since_cuts(data: Data) -> list[float]:
    """지도 행의 경계(년). 맨 앞은 최근 소견 질문의 기간(3개월), 그 뒤는 정밀비교 간편심사 종형의 고지입원수술년수의 합집합이다.
    일반심사 종형은 이력과 무관하게 심사로 확인이라 경계를 더하지 않고, 관문전용 종형의 기간도 넣지 않는다."""
    vids = targets(data)
    months = [data.variants[v].get("고지최근소견개월") for v in vids if data.variants[v].get("심사유형") == SIMPLE]
    months = [m for m in months if m is not None]
    low = min(months) / 12 if months else 0.25
    years = {y for y in (_period(data.variants[v]) for v in vids) if y is not None}
    return [low] + sorted(y for y in years if y > low)


def _years_text(y: float) -> str:
    return f"{I._num_text(y * 12)}개월" if y < 1 else f"{I._num_text(y)}년"


def span_text(since: float | None, cuts: list[float]) -> str | None:
    """"3개월~1년 전", "1~2년 전", "5년 넘게 전". since가 None이면 None."""
    if since is None:
        return None
    lower = [c for c in cuts if c <= since]
    if not lower:
        return f"{_years_text(cuts[0])} 안"
    lo = lower[-1]
    upper = [c for c in cuts if c > lo]
    if not upper:
        return f"{_years_text(lo)} 넘게 전"
    hi = upper[0]
    head = _years_text(lo)
    if lo >= 1:
        head = head[:-1]          # "1~2년"
    return f"{head}~{_years_text(hi)} 전"


def history_text(p: Profile, cuts: list[float]) -> str | None:
    span = span_text(p.since, cuts)
    if span is None:
        return None
    return f"{'입원 없이 받은 마지막 수술이' if p.surgery_only else '마지막 입원이'} {span}"


def map_rows(data: Data) -> list[dict[str, Any]]:
    cuts = since_cuts(data)
    rows = []
    for kind in (HOSPITAL, SURGERY_ONLY):
        for i, s in enumerate(cuts):
            last = i == len(cuts) - 1
            name = f"{_years_text(s)} 넘음이나 없음" if last else span_text(s, cuts)
            rows.append({"종류": kind, "since": s, "이름": f"{kind} {name}"})
    return rows


def map_columns(data: Data) -> list[tuple[int, int]]:
    """가입조건이 바뀌는 나이마다 끊은 구간. 맨 앞 경계부터 맨 뒤 경계 앞까지(가입조건이 있는 나이)만 본다."""
    edges = data.age_edges()
    return [(a, b - 1) for a, b in zip(edges, edges[1:])]


def segment_map(data: Data, sex: str, renewal: str | None, analysis: dict | None,
                relations: Relations | None = None, ctx: _Ctx | None = None) -> dict[str, Any]:
    """고객군 지도. 행은 고지 이력(종류 둘 × 시점), 열은 나이 구간(Data.age_edges)이다.

    이웃 구간의 칸이 모두 같으면(분류, 숫자, 대표, 자료 없는 회사, 열린 종형까지) 합친다. 열린 종형까지 보는 것은
    칸을 눌렀을 때 패널에 뜨는 회사별 열린 종형이 같아야 한 칸으로 볼 수 있어서다.
    """
    ctx = _ctx(data, analysis, relations, ctx)
    rows = map_rows(data)
    columns: list[dict[str, Any]] = []
    grid: list[list[dict]] = []          # 열마다 행의 칸
    for lo, hi in map_columns(data):
        col = [cell(data, Profile(age=lo, sex=sex, since=r["since"], surgery_only=r["종류"] == SURGERY_ONLY,
                                  renewal=renewal), None, ctx=ctx) for r in rows]
        if grid and grid[-1] == col:
            columns[-1]["hi"] = hi
        else:
            columns.append({"lo": lo, "hi": hi})
            grid.append(col)
    cells = [[grid[j][i] for j in range(len(columns))] for i in range(len(rows))]
    tally = {c: sum(1 for row in cells for x in row if x["분류"] == c) for c in CLASSES}
    return {"성별": sex, "갱신유형": renewal, "행": rows, "열": columns, "칸": cells, "집계": tally}


# ---------- 범위 ----------
def source_text(data: Data, vid: str) -> str:
    """회사마다 수집한 상품과 기준일. 관문전용 종형은 담보를 수집하지 않았다고 적는다(머리말_관문)."""
    return render("머리말_관문" if gate_only(data, vid) else "머리말",
                  {"상품": full_name(data, vid), "기준일": data.variants[vid].get("적용시작일")})


def header(data: Data, base: str, peers: list[str]) -> tuple[str, bool]:
    """(범위 머리말, 구조 다름). 회사마다 수집한 상품과 기준일을 적고, 갱신이나 환급 구조가 다른 짝이 있으면 뒤에 붙인다.
    상대 회사가 넷 이상이면 상품마다 적지 않고 회사 수, 상품 수와 기준일의 범위를 적는다(머리말_많음. 상품마다의 머리말은 범위의
    상대에 있다). 구조가 다른 상대가 넷 이상이면 구조가 같은 회사끼리 묶어 적는다. 셋까지는 지금 그대로다."""
    orgs = list(dict.fromkeys(_org(data, p) for p in peers))
    text = _sources_many(data, peers, orgs) if len(orgs) >= MANY else ", ".join(source_text(data, p) for p in peers)
    diff = [p for p in peers if structure_differs(data, base, p)]
    if diff:
        if len(diff) >= MANY:
            by: dict[str, list[str]] = {}
            for p in diff:
                by.setdefault(_structure(data.variants[p]), []).append(_org_name(data, p))
            theirs = "; ".join(f"{and_join(names, UNIT_ORG)} {struct}" for struct, names in by.items())
        else:
            theirs = "; ".join(f"{_org_name(data, p)} {_structure(data.variants[p])}" for p in diff)
        text += " / " + render("구조", {"우리구조": _structure(data.variants[base]), "상대구조": theirs})
    return text, bool(diff)


def _sources_many(data: Data, peers: list[str], orgs: list[str]) -> str:
    """상대 회사가 넷 이상일 때의 머리말: "수집한 19곳의 상품 19개 기준(2026-07-01~2026-10-01)". 관문전용 종형이 있으면 그 수를 적는다."""
    days = sorted({str(data.variants[p].get("적용시작일")) for p in peers if data.variants[p].get("적용시작일")})
    gated = sum(1 for p in peers if gate_only(data, p))
    values = {"상대회사수": len(orgs), "상품수": len(peers), "미수집수": gated,
              "기준일": (days[0] if len(days) == 1 else f"{days[0]}~{days[-1]}") if days else None}
    return render("머리말_많음_관문" if gated else "머리말_많음", values)


def _company_count(data: Data, peers: list[str], hit: list[str]) -> str:
    orgs = list(dict.fromkeys(_org(data, p) for p in peers))
    return render("회사수", {"전체": len(orgs), "해당": len({_org(data, p) for p in hit})})


def scope_sentence(data: Data, base: str, peers: list[str], pairs: int, pending: int) -> str | None:
    """범위 띠의 문장(두세 문장). 견준 상품과 기준일, 갱신이나 환급 구조가 다른 상대가 있으면 우리와 그 상대의 구조, 견준 공통
    담보 쌍이다. 구조가 같은 상대만 있으면 구조 문장은 뺀다. 상대가 없으면 None."""
    if not peers:
        return None
    orgs = list(dict.fromkeys(_org(data, p) for p in peers))
    if len(orgs) >= MANY:
        parts = scope_products_many(data, peers, orgs)
    else:
        names = [render("범위_상품_관문" if gate_only(data, p) else "범위_상품",
                        {"상품": full_name(data, p), "기준일": data.variants[p].get("적용시작일")}) for p in peers]
        parts = [("범위", {"상품목록": and_join(names)})]
    diff = [p for p in peers if structure_differs(data, base, p)]
    if diff:
        if len(diff) >= MANY:
            # 구조가 다른 상대가 넷 이상이면 구조가 같은 회사끼리 묶어 적는다(셋까지는 회사마다. 지금 그대로)
            by: dict[str, list[str]] = {}
            for p in diff:
                by.setdefault(_structure(data.variants[p]), []).append(_org_name(data, p))
            theirs = ", ".join(render("구조_상대", {"상대": and_join(names, UNIT_ORG), "상대구조": struct})
                               for struct, names in by.items())
        else:
            theirs = ", ".join(render("구조_상대", {"상대": _org_name(data, p), "상대구조": _structure(data.variants[p])})
                               for p in diff)
        parts.append(("범위_구조", {"우리구조": _structure(data.variants[base]), "상대문장": theirs}))
    if not pairs:
        parts.append(("범위_쌍없음", {}))
    else:
        parts.append(("범위_대기" if pending else "범위_모두", {"비교쌍": pairs, "뺀비교쌍": pending}))
    return _joined(parts[0][0], parts[0][1], parts[1:])


def scope_products_many(data: Data, peers: list[str], orgs: list[str]) -> list[tuple[str, dict]]:
    """상대 회사가 넷 이상일 때 범위 문장의 첫 문장: 상품을 다 적지 않고 업권별 회사 수와 상품 수를 적는다
    ("견준 상품은 생명보험 10곳, 손해보험 9곳의 상품 19개입니다"). 상품 목록은 범위의 상대(scope)에 그대로 있다.
    업권은 자료에 있는 값(Data.org_sector: meta.json 의 기관업권, 없으면 config 의 생명보험, 손해보험 표)만 쓴다. 업권을 모르는
    상대가 하나라도 있으면 구분을 빼고 상대 회사 수만 적는다(범위_많음_업권모름). 관문전용 종형이 있으면 그 수를 덧붙인다."""
    sectors = [data.org_sector(o) for o in orgs]
    values: dict[str, Any] = {"상대회사수": len(orgs), "상품수": len(peers)}
    if all(sectors):
        split = [f"{s} {sectors.count(s)}곳" for s in (SECTOR_LIFE, SECTOR_NONLIFE) if sectors.count(s)]
        parts = [("범위_많음", {**values, "업권나눔": ", ".join(split)})]
    else:
        parts = [("범위_많음_업권모름", values)]
    gated = sum(1 for p in peers if gate_only(data, p))
    if gated:
        parts.append(("범위_미수집수", {"미수집수": gated}))
    return parts


def scope(data: Data, base: str, peers: list[str], analysis: dict | None, relations: Relations | None = None,
          ctx: _Ctx | None = None) -> dict[str, Any]:
    """범위 띠: 견준 상품과 종형, 상품별 기준일, 구조 다름, 검토 대기로 뺀 쌍. 문장은 scope_sentence다."""
    ctx = _ctx(data, analysis, relations, ctx)
    result = ctx.result(base, peers)

    def info(vid: str) -> dict[str, Any]:
        v = data.variants[vid]
        return {"종형ID": vid, "회사": _org_name(data, vid), "공시상품명": v.get("공시상품명"), "종형명": v.get("종형명"),
                "적용시작일": v.get("적용시작일"), "갱신유형": v.get("갱신유형"), "환급유형": v.get("환급유형")}

    rows = [{**info(p), "머리말": source_text(data, p), "구조다름": structure_differs(data, base, p)} for p in peers]
    text, _ = header(data, base, peers)
    sectors = [data.org_sector(o) or SECTOR_UNKNOWN for o in dict.fromkeys(_org(data, p) for p in peers)]
    return {
        "기준": info(base), "상대": rows, "회사수": len({_org(data, p) for p in peers}),
        "업권별": {s: sectors.count(s) for s in (SECTOR_LIFE, SECTOR_NONLIFE, SECTOR_UNKNOWN) if sectors.count(s)},
        "머리말": text,
        "비교쌍": result["비교쌍"], "뺀비교쌍": result["뺀비교쌍"], "뺀시사점": len(result["뺀시사점"]),
        "문장": scope_sentence(data, base, peers, result["비교쌍"], result["뺀비교쌍"]),
    }


# ---------- 응대 포인트 ----------
def point_id(code: str, base: str, sid: str | None, extra: str = "") -> str:
    key = f"{code}|{base}|{sid or ''}|{extra}"
    return "PT_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def purposes(std: dict[str, Any] | None) -> list[str]:
    """목적 묶음. 암은 보장대분류 암보장, 3대 질병은 insights.FOCUS_MAJORS, 입원과 수술은 급부유형 입원과 수술."""
    if not std:
        return []
    out = []
    if std.get("보장대분류") == "암보장":
        out.append("암")
    if std.get("보장대분류") in I.FOCUS_MAJORS:
        out.append("3대 질병")
    if std.get("급부유형") in ("입원", "수술"):
        out.append("입원과 수술")
    return out


class _Points:
    """포인트와 뺀포인트를 모은다."""

    def __init__(self, ctx: _Ctx, base: str, peers: list[str]):
        self.ctx, self.data, self.base, self.peers = ctx, ctx.data, base, peers
        self.kept: list[dict] = []
        self.dropped: list[dict] = []

    def drop(self, code: str, sid: str | None, reason: str, peers: list[str] | None = None, **more: Any) -> None:
        self.dropped.append({"세부": code, "세부이름": DETAILS[code][1], "분류": CATEGORY[code], "표준담보ID": sid,
                             "표준담보명": self.data.std[sid]["표준담보명"] if sid in self.data.std else None,
                             "비교종형ID": list(peers or []), "사유": reason, **more})

    def add(self, code: str, sid: str | None, template: str, values: dict, involved: list[str], evidence: list[dict],
            *, score: int | None = None, extra_key: str = "", source_check: bool = False, insight: str | None = None,
            question: tuple[str, dict] | None = None, tail: list[tuple[str, dict]] | None = None,
            card: tuple[str, dict] | None = None, card_tail: list[tuple[str, dict]] | None = None,
            brief: bool = True, **more: Any) -> None:
        """포인트 하나. template과 tail은 분석 문장("문장"), card와 card_tail은 카드의 답("카드답"), question은 카드의 예상 질문이다.
        card가 없으면 카드의 답은 분석 문장과 같다. 어느 틀이든 값이 비거나 금지어가 들면 포인트를 내지 않고 뺀포인트에 적는다."""
        try:
            sentence = _joined(template, values, tail)
            answer = _joined(card[0], card[1], card_tail) if card else sentence
            asked = render(*question) if question else None
            head, struct = header(self.data, self.base, involved)
        except (TemplateValueMissing, ForbiddenWordError) as e:
            reason = f"값 없음: {e}" if isinstance(e, TemplateValueMissing) else str(e)
            self.drop(code, sid, reason, involved)
            return
        std = self.data.std.get(sid) if sid else None
        self.kept.append({
            "포인트ID": point_id(code, self.base, sid, extra_key),
            "분류": CATEGORY[code], "종류": DETAILS[code][0], "세부": code, "세부이름": DETAILS[code][1],
            "표준담보ID": sid, "표준담보명": std["표준담보명"] if std else None,
            "틀": template, "값": {k: _text(v) for k, v in values.items()},
            "문장": sentence, "카드질문": asked, "카드답": answer,
            "머리말": head, "회사수": _company_count(self.data, self.peers, involved), "비교종형ID": list(involved),
            "근거": evidence, "점수": score, "목적": purposes(std), "구조다름": struct, "원문대조": source_check,
            "원문대조글": SOURCE_CHECK_TEXT if source_check else None,
            "시사점ID": insight, "브리핑": brief, **more,
        })


def _joined(template: str, values: dict, tail: list[tuple[str, dict]] | None) -> str:
    text = render(template, values)
    for tid, vals in tail or []:
        text += " " + render(tid, vals)
    return text


def _gate_evidence(base: str, peers: list[str]) -> list[dict[str, Any]]:
    """고지 질문과 가입나이는 사업방법서에서 읽은 값이고 쪽이 없다. 원문 대조가 필요하다."""
    return [{"종형ID": v, "문서": "사업방법서", "쪽": None, "급부ID": None} for v in [base] + peers]


def age_span(data: Data, vid: str, sex: str | None) -> tuple[int, int] | None:
    """주계약에 가입할 수 있는 가장 낮은 나이와 높은 나이. 가입나이 자료가 없으면 None."""
    main = data.main_rider(vid)
    if not main or not data.condition_rows(main):
        return None
    ages = [a for a in range(MAX_AGE + 1) if data.age_limit(main, Cond(age=a, sex=sex)).ok]
    return (ages[0], ages[-1]) if ages else None


def question_text(v: dict[str, Any]) -> str | None:
    """간편심사 종형의 입원과 수술 기간 질문을 괄호 안에 적는 말: "5년 안 입원", "1년 안 입원과 수술". 기간 질문이 없으면(0년)
    "입원과 수술의 기간 질문 없음", 수술 포함 여부를 모르면 "기간 5년", 기간을 모르면 None."""
    period = _period(v)
    if period is None:
        return None
    if period == 0:
        return "입원과 수술의 기간 질문 없음"
    rng = _range_text(v)
    return render("질문_기간", {"기간": period, "범위": rng}) if rng else render("질문_기간만", {"기간": period})


def _general_tail(data: Data, home: dict[str, Any] | None, p: Profile) -> list[tuple[str, dict]] | None:
    """G2(나이)의 꼬리: 고객 나이가 우체국 일반심사 종형(심사로 확인이고 가입나이가 맞는 것. reviewable_general)의 가입나이 안이면
    그 종형 하나(대표 고르는 차례 _rank의 첫째, 곧 칸의 우리 대표)와 가입나이를 적는다. 없으면 None."""
    cands = [x["종형ID"] for x in (home or {}).get("종형", []) if reviewable_general(data, x)]
    if not cands:
        return None
    gv = min(cands, key=lambda v: _rank(data, v))
    span = age_span(data, gv, p.sex)
    if not span:
        return None
    return [("G2_일반", {"일반종형": _kind_name(data, gv), "일반최저": span[0], "일반최고": span[1]})]


def gate_points(ctx: _Ctx, base: str, peers: list[str], p: Profile, out: _Points, g: dict | None = None) -> None:
    """관문 G1(우리만 열림), G2(우리만 닫힘), G3(질문 범위 다름). G1과 G2는 지도 라벨과 같은 분류(simple_classify.
    간편심사 종형만 보고 관문전용 종형도 본다)를 따른다. g는 gate(data, p)의 결과(없으면 계산한다).

    G2는 기준 종형이 고지 질문에 걸렸으면 열린 상대 종형의 기간 질문을(G2_질문), 질문은 넘고 나이로 닫혔으면 열린 상대 종형의
    가입나이를(G2) 적는다. 열린 상대 종형은 회사마다 짝이 열렸으면 짝, 아니면 정밀비교 종형 가운데 질문 기간이 긴 것이고,
    열린 정밀비교 종형이 없을 때만 관문전용 종형이다.
    G3은 같은 기간 질문의 짝과 견준 것(scope_diff. 짝마다 하나이고 포인트ID는 짝의 종형ID로 가른다)과, 짝의 회사가 파는 더 짧은
    기간 질문 종형(shorter_questions)이다."""
    data = ctx.data
    bv = data.variants[base]
    g = g if g is not None else gate(data, p)
    cls, nodata = simple_classify(data, g)
    mine = variant_gate(data, base, p)
    by_org = {org: x for org, x in g["회사"].items()}

    # G1: 칸이 우리만 열림이고 기준 종형이 열림. 짝 가운데 고지 질문에 걸리는 종형을 적는다.
    if cls == ONLY_OPEN and mine["상태"] == OPEN and bv.get("심사유형") == SIMPLE:
        closed = [pv for pv in peers if data.variants[pv].get("심사유형") == SIMPLE
                  and question_hit(data.variants[pv], p) == Q_HIT]
        if not closed:
            out.drop("G1", None, "맞붙는 종형이 고지 질문이 아닌 까닭으로 닫힘", peers)
        else:
            groups: dict[tuple, list[str]] = {}          # 질문 범위와 기간이 같은 짝은 한 문장으로 묶는다
            for pv in closed:
                v = data.variants[pv]
                groups.setdefault((_range_text(v), _period(v)), []).append(pv)
            parts = [render("G1_상대_기간",
                            {"상대": and_join((_peer_name(data, pv) for pv in group), UNIT_KIND), "상대범위": rng,
                             "상대기간": period})
                     for (rng, period), group in groups.items()]
            values = {"이력": history_text(p, since_cuts(data)), "소견개월": bv.get("고지최근소견개월"),
                      "중대년수": bv.get("고지중대질병년수"), "우리종형": _kind_name(data, base),
                      "우리질문": question_text(bv), "상대문장": " ".join(parts)}
            out.add("G1", None, "G1_분석", values, closed, _gate_evidence(base, closed), extra_key=p.key(),
                    source_check=True, card=("G1", values))

    # 열린 상대 간편심사 종형: 회사마다 짝이 열렸으면 짝, 아니면 정밀비교 종형 가운데 질문 기간이 긴 것,
    # 열린 정밀비교 종형이 없으면 관문전용 종형 가운데 질문 기간이 긴 것
    chosen = []
    for org, x in by_org.items():
        if org == HOME_ORG:
            continue
        opened = [y["종형ID"] for y in x["종형"] if y["상태"] == OPEN and _is_simple(data, y["종형ID"])]
        if opened:
            chosen.append(next((v for v in peers if v in opened), None)
                          or min(opened, key=lambda v: (gate_only(data, v), *_rank(data, v))))

    # G2(질문): 칸이 우리 간편 닫힘이고 기준 종형이 고지 질문에 걸림. 열린 상대 간편심사 종형의 기간 질문을 적는다.
    if p.since is not None and cls == ONLY_CLOSED and mine["질문"] == Q_HIT and bv.get("심사유형") == SIMPLE:
        said = [(pv, _period_part(data, pv)) for pv in chosen]
        named = [pv for pv, part in said if part]
        if not named:
            out.drop("G2", None, "기간 질문을 적을 수 있는 열린 상대 종형이 없음", chosen)
        else:
            # 상대가 넷 이상이면 기간 질문이 같은 종형끼리 묶어 한 문장으로 적는다(셋까지는 종형마다 한 문장. 지금 그대로)
            text = (_period_groups(data, named) if len(named) >= MANY
                    else " ".join(part for _, part in said if part))
            out.add("G2", None, "G2_질문", {"이력": history_text(p, since_cuts(data)), "우리종형": _kind_name(data, base),
                                          "상대문장": text},
                    named, _gate_evidence(base, named), extra_key=p.key(), source_check=True,
                    관문만수집=any(gate_only(data, v) for v in named))

    # G2(나이): 칸이 우리 간편 닫힘이고 기준 종형이 나이로만 닫힘. 열린 상대 간편심사 종형의 가입나이를 적는다(나이 자료 없는 회사는 뺀다).
    elif p.age is not None and cls == ONLY_CLOSED and mine["나이"] == AGE_NO:
        for org in nodata:
            if org != HOME_ORG:
                out.drop("G2", None, f"나이 자료 없음: {data.org_name(org)}")
        ours = age_span(data, base, p.sex)
        parts = []
        spans: dict[tuple, list[str]] = {}
        for pv in chosen:
            span = age_span(data, pv, p.sex)
            if span:
                parts.append(render("G2_상대", {"상대": _peer_name(data, pv), "상대최저": span[0], "상대최고": span[1]}))
                spans.setdefault(span, []).append(pv)
        if len(parts) >= MANY and len(spans) <= SHOWN:
            # 상대가 넷 이상이면 가입나이가 같은 종형끼리 묶어 한 문장으로 적는다(셋까지는 종형마다 한 문장. 지금 그대로)
            parts = [render("G2_상대", {"상대": and_join((_peer_name(data, pv) for pv in group), UNIT_KIND),
                                       "상대최저": span[0], "상대최고": span[1]}) for span, group in spans.items()]
        elif len(parts) >= MANY:
            # 가입나이가 넷 이상으로 갈리면 하한과 상한의 범위만 적는다(종형마다의 가입나이는 근거의 종형으로 찾는다)
            los, his = [s[0] for s in spans], [s[1] for s in spans]
            parts = [render("G2_상대많음", {
                "상대": and_join((_peer_name(data, pv) for pv in chosen if age_span(data, pv, p.sex)), UNIT_KIND),
                "하한": _bounds(min(los), max(los)), "상한": _bounds(min(his), max(his))})]
        if not parts or not ours:
            out.drop("G2", None, "가입나이를 적을 수 있는 열린 상대 종형이 없음" if ours else "기준 종형 가입나이 자료 없음", chosen)
        else:
            named = [pv for pv in chosen if age_span(data, pv, p.sex)]
            out.add("G2", None, "G2", {"나이": p.age, "우리종형": _kind_name(data, base), "우리최저": ours[0], "우리최고": ours[1],
                                       "상대문장": " ".join(parts)},
                    chosen, _gate_evidence(base, chosen), extra_key=p.key(), source_check=True,
                    tail=_general_tail(data, by_org.get(HOME_ORG), p),
                    관문만수집=any(gate_only(data, v) for v in named))

    # G3: 짝의 같은 기간 질문에서 수술 포함 여부, 중대질병 질문의 질병, 최근 소견 질문의 범위가 다름. 고객 조건과 무관하다.
    if bv.get("심사유형") == SIMPLE:
        for pv in peers:
            v = data.variants[pv]
            if v.get("심사유형") != SIMPLE or _period(v) is None or _period(v) != _period(bv):
                continue
            diff = scope_diff(data, base, pv)
            if diff is None:
                continue
            template, values, tail, items = diff
            out.add("G3", None, template, values, [pv], _gate_evidence(base, [pv]), extra_key=pv, source_check=True,
                    tail=tail, 차이항목=items)
        shorter_questions(data, base, peers, p.renewal, out)


def disease_names(v: dict[str, Any]) -> list[str] | None:
    """고지중대질병목록을 이름 목록으로(쉼표로 나눈다). 비었으면 None."""
    raw = v.get("고지중대질병목록")
    if _blank(raw):
        return None
    names = [s.strip() for s in str(raw).split(",") if s.strip()]
    return names or None


SCOPE_ITEMS = ("기간 질문 범위", "중대질병 질문", "최근 소견 질문")      # G3의 차이항목


def scope_diff(data: Data, base: str, pv: str) -> tuple[str, dict, list, list[str]] | None:
    """같은 기간 질문의 짝(기준 종형 base, 상대 pv)에서 고지 질문 범위가 다른 곳. (주 틀, 값, 꼬리 틀, 차이항목) 또는 None.

    - 기간 질문 범위: 고지수술포함여부가 양쪽에 있고 다르다.
    - 중대질병 질문: 고지중대질병년수가 같고, 고지중대질병수가 다르거나 고지중대질병목록이 양쪽에 있고 이름이 다르다. 목록이
      양쪽에 있으면 한쪽만 묻는 질병을 괄호로 적고(G3_목록, G3_질병수_목록), 한쪽이라도 비면 지금 문장 그대로다(G3, G3_질병수).
    - 최근 소견 질문: 고지최근소견개월이 같고 고지소견범위가 양쪽에 있고 다르다(G3_소견. 앞의 차이가 있으면 꼬리로 붙인다).
    """
    bv, v = data.variants[base], data.variants[pv]
    rb, rp = _range_text(bv), _range_text(v)
    range_diff = rb is not None and rp is not None and rb != rp

    same_years = bv.get("고지중대질병년수") == v.get("고지중대질병년수")
    lb, lp = disease_names(bv), disease_names(v)
    nb = bv.get("고지중대질병수") if bv.get("고지중대질병수") is not None else (len(lb) if lb else None)
    np_ = v.get("고지중대질병수") if v.get("고지중대질병수") is not None else (len(lp) if lp else None)
    count_diff = same_years and nb is not None and np_ is not None and nb != np_
    listed = bool(same_years and lb and lp)
    ours_only = [n for n in lb if n not in lp] if listed else []
    theirs_only = [n for n in lp if n not in lb] if listed else []
    disease_diff = count_diff or bool(ours_only or theirs_only)

    ob, op = bv.get("고지소견범위"), v.get("고지소견범위")
    months = bv.get("고지최근소견개월")
    opinion_diff = (months is not None and months == v.get("고지최근소견개월") and ob in OPINION_TEXT and op in OPINION_TEXT
                    and ob != op)
    if not (range_diff or disease_diff or opinion_diff):
        return None

    company = _org_name(data, pv)
    values: dict[str, Any] = {"기간": _period(bv), "우리종형": _kind_name(data, base), "우리범위": rb,
                              "상대": _peer_name(data, pv), "상대범위": rp, "중대년수": bv.get("고지중대질병년수"),
                              "우리수": nb, "상대회사": company, "상대수": np_}
    if listed:
        parts = [render("G3_한쪽질병", {"상대회사": who, "질병": names})
                 for who, names in (("우체국", ours_only), (company, theirs_only)) if names]
        values.update({"우리질병목록": lb, "상대질병목록": lp, "우리만질병": ours_only, "상대만질병": theirs_only,
                       "질병차이": "; ".join(parts)})
    opinion = None
    if opinion_diff:
        opinion = {"소견개월": months, "우리소견": OPINION_TEXT[ob], "상대회사": company, "상대소견": OPINION_TEXT[op]}
        values.update({"소견개월": months, "우리소견범위": ob, "상대소견범위": op})

    named = bool(values.get("질병차이"))
    if range_diff and disease_diff:
        template = "G3_목록" if named else "G3"
    elif range_diff:
        template = "G3_범위"
    elif disease_diff:
        template = "G3_질병수_목록" if named else "G3_질병수"
    else:
        template = "G3_소견"
    tail = [("G3_소견", opinion)] if opinion and template != "G3_소견" else []
    if template == "G3_소견":
        values.update(opinion)
    items = [name for name, hit in zip(SCOPE_ITEMS, (range_diff, disease_diff, opinion_diff)) if hit]
    return template, {k: x for k, x in values.items() if not _empty(x)}, tail, items


def _period_part(data: Data, vid: str) -> str | None:
    """G2(질문)에서 열린 상대 종형의 기간 질문을 적는 문장. 기간 질문이 없으면(0년) 그렇다고 적는다. 값이 없으면 None."""
    v = data.variants[vid]
    period = _period(v)
    try:
        if period == 0:
            return render("G2_상대_질문없음", {"상대": _peer_name(data, vid)})
        return render("G1_상대_기간", {"상대": _peer_name(data, vid), "상대기간": period, "상대범위": _range_text(v)})
    except TemplateValueMissing:
        return None


def _bounds(lo: int, hi: int) -> str:
    """"15"(같으면) 또는 "15~18"."""
    return f"{lo}" if lo == hi else f"{lo}~{hi}"


def _period_groups(data: Data, vids: list[str]) -> str:
    """G2(질문)에서 열린 상대 종형이 넷 이상일 때: 기간 질문(기간과 범위)이 같은 종형끼리 묶어 묶음마다 한 문장으로 적는다.
    종형 이름은 and_join(UNIT_KIND)으로 잇는다. vids는 _period_part가 문장을 낸 종형이다(차례는 그대로)."""
    groups: dict[tuple, list[str]] = {}
    for vid in vids:
        v = data.variants[vid]
        groups.setdefault((_period(v), _range_text(v) if _period(v) != 0 else None), []).append(vid)
    out = []
    for (period, rng), group in groups.items():
        who = and_join((_peer_name(data, v) for v in group), UNIT_KIND)
        out.append(render("G2_상대_질문없음", {"상대": who}) if period == 0
                   else render("G1_상대_기간", {"상대": who, "상대기간": period, "상대범위": rng}))
    return " ".join(out)


def shorter_questions(data: Data, base: str, peers: list[str], renewal: str | None, out: _Points) -> None:
    """G3(질문 범위 다름)의 하나: 짝의 회사가 우리 간편심사 종형 어느 것보다 입원과 수술 기간 질문이 짧거나 없는 간편심사 종형을
    팔면 그 사실을 적는다. 짝 말고 그 회사의 판매 중인 종형(관문전용 포함. 거르개 안)을 본다. 우리 쪽 기간은 거르개 안의 판매 중인
    우체국 간편심사 종형의 기간 가운데 가장 짧은 것이다. 관문전용 종형이면 담보를 수집하지 않았다는 문장(G3_미수집)을 붙인다."""
    pool = gate_targets(data, renewal)
    ours = [_period(data.variants[v]) for v in pool if _org(data, v) == HOME_ORG and _is_simple(data, v)]
    ours = [y for y in ours if y is not None]
    if not ours:
        return
    shortest = min(ours)
    orgs = list(dict.fromkeys(_org(data, pv) for pv in peers if _org(data, pv) != HOME_ORG))
    for vid in pool:
        v = data.variants[vid]
        period = _period(v)
        if _org(data, vid) not in orgs or vid in peers or not _is_simple(data, vid) or period is None or period >= shortest:
            continue
        values = {"상대회사": _org_name(data, vid), "상대종형": _kind_name(data, vid), "상대기간": period,
                  "상대범위": _range_text(v)}
        tail = [("G3_미수집", {})] if gate_only(data, vid) else None
        out.add("G3", None, "G3_질문없음" if period == 0 else "G3_짧은", values, [vid], _gate_evidence(base, [vid]),
                extra_key=vid, source_check=True, tail=tail, 관문만수집=gate_only(data, vid))


def _evidence(ctx: _Ctx, ins: dict[str, Any]) -> list[dict[str, Any]] | None:
    """시사점 근거 급부를 [{종형ID, 문서, 쪽, 급부ID}]로. 작업 로그 대기 급부는 같은 종형, 같은 표준담보의 확정 급부로 바꾸고,
    바꿀 급부가 없으면 None(그 포인트는 내지 않는다)."""
    data = ctx.data
    pairs = [(ins["기준종형ID"], b) for b in ins["근거"].get("기준", [])]
    pairs += [(vid, b) for vid, bids in ins["근거"].get("비교", {}).items() for b in bids]
    out = []
    for vid, bid in pairs:
        if bid in data.pending_benefit:
            sid = data.benefit_view(bid)["std"]
            alt = [v["id"] for v in ctx.holding(vid).confirmed.get(sid, []) if v["id"] not in data.pending_benefit]
            if not alt:
                return None
            bid = alt[0]
        b = data.benefits[bid]
        out.append({"종형ID": vid, "문서": b.get("근거문서종류"), "쪽": b.get("근거문서쪽수"), "급부ID": bid})
    return out


_WAIT, _RED, _PAY = I.WAIT, I.REDUCTION, I.PAY
_ITEM_ORDER = (_WAIT, _RED, _PAY)
PAY_ITEM = I.PAY


def reduction_phrase(segs: list) -> str:
    """감액 구간을 받는 비율이 드러나게 적는다. "1년까지 보험금의 50% 지급", "6개월까지 보험금의 25%, 1년까지 50% 지급".

    sys_급부의 감액지급률은 그 기간에 지급하는 비율이라 "감액 1년 10%"로 쓰면 10% 감액으로 읽힌다(실제로는 90% 감액).
    지급기준구분이 가입금액비율인 급부도 있어 "가입금액의"가 아니라 "보험금의"로 쓴다. insights.reduction_text는
    비교 화면이 쓰므로 그대로 둔다.
    """
    if not segs:
        return "감액 없음"
    return reduction_stages(segs) + " 지급"


def reduction_stages(segs: list) -> str:
    """감액 구간의 받는 비율만: "1년까지 보험금의 50%", "6개월까지 보험금의 25%, 1년까지 50%"(조건문의 절_감액이 쓴다)."""
    stages = sorted((float(m), float(r)) for m, r in segs)
    return ", ".join(f"{I.months_text(m)}까지 {'보험금의 ' if i == 0 else ''}{I._num_text(r * 100)}%"
                     for i, (m, r) in enumerate(stages))


def _cond_value(view: dict[str, Any], item: str) -> str:
    if item == _WAIT:
        return f"면책 {I._num_text(view.get('wait') or 0)}일"
    if item == _RED:
        return reduction_phrase(view.get("red") or [])
    return f"지급 형태 {I.tag_text(I.pay_tags(view.get('limit')))}"


def _cond_text(view: dict[str, Any], items: list[str]) -> str:
    """조건 값을 명사 꼴로("면책 0일, 1년까지 보험금의 50% 지급"). 포인트의 값(우리조건, 상대조건)에 남긴다."""
    return ", ".join(_cond_value(view, i) for i in items)


def _item_key(view: dict[str, Any], item: str) -> Any:
    """조건 항목의 같고 다름을 가르는 값."""
    if item == _WAIT:
        return float(view.get("wait") or 0)
    if item == _RED:
        return tuple(sorted((float(m), float(r)) for m, r in view.get("red") or []))
    return frozenset(t.key for t in I.pay_tags(view.get("limit")))


def _cond_clause(view: dict[str, Any], items: list[str]) -> str:
    """한 쪽의 조건을 동사 꼴의 절로 잇는다("면책 기간이 없고 가입 뒤 1년까지 보험금의 50%를 지급합니다"). 마침표는 없다."""
    parts = []
    for item in items:
        if item == _WAIT:
            wait = view.get("wait") or 0
            parts.append(render("절_면책", {"면책일": I._num_text(wait)}) if wait else render("절_면책없음", {}))
        elif item == _RED:
            segs = view.get("red") or []
            parts.append(render("절_감액", {"감액": reduction_stages(segs)}) if segs else render("절_감액없음", {}))
        else:
            parts.append(render("절_지급", {"지급형태": I.tag_text(I.pay_tags(view.get("limit")))}))
    return _connect(parts, " ")


_COUNT_WORD = {2: "두", 3: "세", 4: "네", 5: "다섯"}


def condition_values(data: Data, base_view: dict[str, Any], peer_views: dict[str, dict], items: list[str]) -> dict[str, Any]:
    """조건 나음(A2)과 조건 못함(Q3) 문장의 값. 조건문은 우리 쪽 절과 상대마다의 절(조건절_상대)을 이은 것이다.

    - 견준 급부 모두(우리 대표와 상대 대표)에서 값이 같은 항목은 절에서 뺀다(A2가 늘 싣는 면책과 감액이 같은 경우). 다 빠지면 모두 적는다.
    - 절이 같은 상대끼리는 묶어 한 번만 적는다("한화생명 …과 삼성화재 …은 감액 기간이 없습니다").
    - 면책 기간이 모두 같고 0보다 크면 면책일과 상품수(두, 세 …)를 담는다. 틀이 "{담보}의 면책 기간은 두 상품 모두 90일입니다."를
      앞에 적는다(_면책같음 틀). 값이 다르면 면책은 위의 절에 차이로 적힌다.
    """
    views = [base_view, *peer_views.values()]
    shown = [i for i in items if len({_item_key(v, i) for v in views}) > 1] or items
    groups: dict[str, list[str]] = {}
    for p, view in peer_views.items():
        groups.setdefault(_cond_clause(view, shown), []).append(p)
    sides = [_cond_clause(base_view, shown)]
    sides += [render("조건절_상대", {"상대": and_join((_peer_name(data, p) for p in group), UNIT_KIND), "상대절": clause})
              for clause, group in groups.items()]
    out: dict[str, Any] = {"조건문": _connect(sides)}
    waits = {float(v.get("wait") or 0) for v in views}
    if len(waits) == 1 and next(iter(waits)) > 0:
        out.update({"면책일": I._num_text(next(iter(waits))), "상품수": _COUNT_WORD.get(len(views), "견준")})
    return out


SOURCE_CODE = {(I.GAP, None): "Q2", (I.UNIQUE, None): "A1", (I.SCOPE, I.MISSING_SIDE): "Q1",
               (I.CONDITION, I.BETTER): "A2", (I.CONDITION, I.WORSE): "Q3"}


def insight_points(ctx: _Ctx, result: dict[str, Any], out: _Points | None = None) -> tuple[list[dict], list[dict]]:
    """시사점을 앞세울 것(A1, A2)과 물어올 것(Q1, Q2, Q3)으로 옮긴다. 시사점 판정은 다시 계산하지 않는다."""
    data = ctx.data
    base = result["종형ID"]
    peers = [x["종형ID"] for x in result["맞붙는종형"]]
    out = out or _Points(ctx, base, peers)
    mine = _kind_name(data, base)
    base_renewal = data.variants[base].get("갱신유형")

    for ins in result["시사점"]:
        code = SOURCE_CODE.get((ins["유형"], ins["방향"]))
        if code is None:
            continue
        sid, v = ins["표준담보ID"], ins["변수"]
        common = dict(score=ins["점수"], insight=ins["시사점ID"])
        if code == "Q1" and v.get("일부만"):
            out.drop(code, sid, "부분 담보를 일부만 가짐(빠진 부분 담보 " + ", ".join(v.get("빠진부분담보") or []) + ")",
                     ins["비교종형ID"])
            continue
        involved = list(ins["비교종형ID"])
        kept_peers = involved
        if code in ("A2", "Q3"):
            others = ins.get("대표밖조건다른줄", {})
            kept_peers = [p for p in involved if not others.get(p, {}).get("기준") and not others.get(p, {}).get("상대")]
            for p in involved:
                if p not in kept_peers:
                    o = others.get(p, {})
                    out.drop(code, sid, f"대표 밖에 조건이 다른 줄이 있음({_org_name(data, p)}: 기준 {o.get('기준', 0)}줄, "
                                        f"상대 {o.get('상대', 0)}줄)", [p],
                             대표밖줄={"기준": o.get("기준", 0), "상대": o.get("상대", 0)}, 판정=ins["방향"],
                             시사점ID=ins["시사점ID"], 대표급부={"기준": (ins["근거"]["기준"] or [None])[0],
                                                          "상대": (ins["근거"]["비교"].get(p) or [None])[0]})
            if not kept_peers:
                continue
            ins = {**ins, "근거": {"기준": ins["근거"]["기준"],
                                  "비교": {p: b for p, b in ins["근거"]["비교"].items() if p in kept_peers}}}
        evidence = _evidence(ctx, ins)
        if evidence is None:
            out.drop(code, sid, "근거 급부가 모두 검토 대기", kept_peers)
            continue

        if code == "A1":
            # 입원 담보에는 주의(상대의 일반 입원 담보로 같은 입원이 지급될 수 있다)를 "주의"에 싣고 문장 끝에도 붙인다
            note = render("A1_주의", {}) if data.std[sid].get("급부유형") == "입원" else None
            # 없는 회사가 넷 이상이면 "A, B, C 등 N곳"으로 줄인다(셋까지는 지금처럼 목록을 쉼표로 잇는다)
            short = _shortened([str(n) for n in v.get("없는회사") or []], UNIT_ORG)
            out.add(code, sid, "A1_많음" if short else "A1",
                    {"담보": v["담보"], "우리종형": mine, "상대회사목록": short or v.get("없는회사")},
                    involved, evidence, tail=[("A1_주의", {})] if note else None, 주의=note, **common)
        elif code in ("Q1", "Q2"):
            q = ("Q_질문", {"상대회사": or_join(v.get("가진회사") or [], UNIT_ORG), "담보": v["담보"]})
            holders = and_join(v.get("가진회사") or [], UNIT_ORG)
            if code == "Q1":
                values = {"우리종형": mine, "담보": v["담보"], "덮는담보": and_join(v.get("덮는담보") or [])}
                out.add(code, sid, "Q1_분석", {**values, "상대회사목록": holders}, involved, evidence, question=q,
                        card=("Q1", values), **common)
            else:
                narrow = list(v.get("기준좁은담보") or [])
                values = {"우리종형": mine, "담보": v["담보"]}
                tail = [("Q2_좁은", {"우리종형": mine, "좁은담보": narrow})] if narrow else None
                out.add(code, sid, "Q2_분석", {**values, "상대회사목록": holders}, involved, evidence, question=q,
                        tail=tail, card=("Q2", values), card_tail=tail, 좁은담보=narrow, 꼬리표=[REVISION_TAG], **common)
        else:
            base_view = data.benefit_view(ins["근거"]["기준"][0]) if ins["근거"]["기준"] else None
            peer_views = {p: data.benefit_view(ins["근거"]["비교"][p][0]) for p in kept_peers if ins["근거"]["비교"].get(p)}
            if base_view is None or len(peer_views) != len(kept_peers):
                out.drop(code, sid, "대표 급부 없음", kept_peers)
                continue
            # 우열을 정한 항목만 적는다. 지급 형태가 "다름"(우열을 매기지 않음)이면 단정 주의 목록(caution)이 따로 적는다
            differ = {i["항목"] for i in ins["항목"] if i.get("종형ID") in kept_peers and i.get("판정") != I.DIFF}
            items = [i for i in _ITEM_ORDER if i in differ or (code == "A2" and i in (_WAIT, _RED))]
            parts = ", ".join(render("조건_상대", {"상대": _peer_name(data, p), "상대조건": _cond_text(peer_views[p], items)})
                              for p in kept_peers)
            # 우리조건과 상대문장(명사 꼴)은 값에 남기고, 문장은 동사 꼴의 조건문으로 쓴다(condition_values)
            values = {"담보": v["담보"], "우리종형": mine, "우리조건": _cond_text(base_view, items), "상대문장": parts,
                      **condition_values(data, base_view, peer_views, items)}
            same_wait = "면책일" in values
            if code == "A2":
                # 갱신유형이 다른 짝과 견준 조건 나음은 영업 포인트 탭 본문에만 두고 브리핑과 카드에서는 뺀다(빼는 조건 4)
                brief = all(data.variants[p].get("갱신유형") == base_renewal for p in kept_peers)
                out.add(code, sid, "A2_면책같음" if same_wait else "A2", values, kept_peers, evidence, brief=brief,
                        견준항목=items, **common)
            else:
                tail = None
                if differ & set(_ITEM_ORDER) == {_RED}:
                    months = [float(m) for view in [base_view, *peer_views.values()] for m, _ in view.get("red") or []]
                    if months:
                        tail = [("Q3_경과", {"경과": I.months_text(max(months)),
                                            "모두": "둘 다" if len(kept_peers) == 1 else "모두"})]
                q = ("Q3_질문", {"담보": v["담보"], "상대회사": or_join((_org_name(data, p) for p in kept_peers), UNIT_ORG)})
                out.add(code, sid, "Q3_분석_면책같음" if same_wait else "Q3_분석", values, kept_peers, evidence, question=q,
                        tail=tail, card=("Q3_면책같음" if same_wait else "Q3", values), card_tail=tail, 견준항목=items,
                        **common)

    # 빼는 조건 1: analyze()가 이미 뺀 시사점(매핑 대기, 작업 로그 대기)
    for x in result["뺀시사점"]:
        code = SOURCE_CODE.get((x["유형"], x["방향"]))
        if code:
            out.drop(code, x["표준담보ID"], "검토 대기: " + "; ".join(x["사유"]), x["비교종형ID"])
    # 빼는 조건 3: 조건 판정 보류(감액예외 글, 지급 형태 문구 없음). 보류한 항목을 뺀 판정이 나음이나 못함이면 적어 둔다.
    for x in result["보류비교"]:
        code = {I.BETTER: "A2", I.WORSE: "Q3"}.get(x["보류밖판정"])
        if code:
            out.drop(code, x["표준담보ID"], "조건 판정 보류: " + "; ".join(x["사유"]), [x["비교종형ID"]])
    return out.kept, out.dropped


def _sort(ctx: _Ctx, points: list[dict]) -> list[dict]:
    """관문(G1, G2, G3 순), 앞세울 것, 물어올 것. 앞세울 것과 물어올 것 안에서는 시사점 점수, 비교표의 담보 순서."""
    def key(ix: tuple[int, dict]) -> tuple:
        i, x = ix
        kind = KINDS.index(x["종류"])
        if x["종류"] == GATE:
            return (kind, CODES.index(x["세부"]), 0, 0, i)
        return (kind, 0, -(x["점수"] or 0), ctx.order.get(x["표준담보ID"], len(ctx.order)), CODES.index(x["세부"]), i)
    return [x for _, x in sorted(enumerate(points), key=key)]


def points(data: Data, base: str, p: Profile, analysis: dict | None, relations: Relations | None = None,
           ctx: _Ctx | None = None) -> dict[str, Any]:
    """기준 종형과 고객 조건의 응대 포인트. 맞붙는 종형은 compare.peers(analyze()의 짝)다."""
    ctx = _ctx(data, analysis, relations, ctx)
    result = ctx.result(base)          # 기준 종형이 아니면 ValueError(_Ctx.check_base)
    peers = [x["종형ID"] for x in result["맞붙는종형"]]
    out = _Points(ctx, base, peers)
    gate_points(ctx, base, peers, p, out)
    insight_points(ctx, result, out)
    kept = _sort(ctx, out.kept)
    return {
        "기준종형ID": base, "조건": p, "맞붙는종형": peers,
        "범위": scope(data, base, peers, None, ctx=ctx),
        "관문": variant_gate(data, base, p),
        "포인트": kept, "뺀포인트": out.dropped,
        "집계": {c: sum(1 for x in kept if x["세부"] == c) for c in CODES},
        "분류집계": {c: sum(1 for x in kept if x["분류"] == c) for c in CATEGORIES},
    }


def _score(x: dict[str, Any]) -> int:
    """점수가 없는 관문 포인트는 점수 있는 포인트 뒤로 간다."""
    return x["점수"] if x["점수"] is not None else -1


def pick(points: list[dict], slots: int = PICK_SLOTS, for_card: bool = False) -> list[dict]:
    """먼저 보일 포인트(합의안 7번). 브리핑에서 빼는 포인트(구조 다름 A2, "브리핑" 거짓)는 넣지 않는다.

    1. 세부(G1…Q3)마다 점수가 가장 높은 1건을 먼저 넣는다. 세부의 차례는 분류 차례(for_card이면 CARD_ORDER, 아니면
       CATEGORIES), 그 안에서 CODES 차례다. 자리가 세부 수보다 적으면 앞 차례의 세부가 먼저 들어간다.
    2. 남는 자리를 점수순으로 채운다. for_card이면 조건 열위 방어와 관련 담보 안내를 포함해 개정 검토 후보가 아닌 포인트를
       개정 검토 후보보다 먼저 채운다(개정 검토 후보의 점수가 늘 높아 자리를 다 차지하지 않게 하려는 것).
    3. 고른 포인트를 분류 차례, 점수, 원래 순서로 늘어놓는다.
    점수가 같으면 원래 순서(points의 순서, 곧 _sort의 비교표 담보 순서)를 따른다.
    """
    order = CARD_ORDER if for_card else CATEGORIES
    rank = {c: i for i, c in enumerate(order)}
    rows = [(i, x) for i, x in enumerate(points) if x.get("브리핑", True)]
    codes = sorted({x["세부"] for _, x in rows}, key=lambda c: (rank[CATEGORY[c]], CODES.index(c)))
    chosen: list[tuple[int, dict]] = []
    for code in codes:
        if len(chosen) >= slots:
            break
        chosen.append(max((ix for ix in rows if ix[1]["세부"] == code), key=lambda ix: (_score(ix[1]), -ix[0])))
    taken = {i for i, _ in chosen}
    rest = sorted((ix for ix in rows if ix[0] not in taken),
                  key=lambda ix: (for_card and ix[1]["분류"] == REVISE, -_score(ix[1]), ix[0]))
    chosen += rest[:max(0, slots - len(chosen))]
    return [x for _, x in sorted(chosen, key=lambda ix: (rank[ix[1]["분류"]], -_score(ix[1]), ix[0]))]


def brief(result: dict[str, Any], slots: int = PICK_SLOTS, purpose: str | None = None, for_card: bool = False) -> list[dict]:
    """브리핑(for_card 거짓)과 응대 카드(참)의 처음 선택. 목적을 주면 관문 차이와 그 목적의 포인트만 놓고 pick으로 고른다."""
    rows = [x for x in result["포인트"] if purpose is None or x["분류"] == GATE_DIFF or purpose in x["목적"]]
    return pick(rows, slots, for_card)


# ---------- 단정 주의 목록 ----------
def _std_name(data: Data, sid: str) -> str:
    s = data.std.get(sid)
    return s["표준담보명"] if s else sid


def _mark(evidence: list[dict] | None, role: str) -> list[dict]:
    return [{**e, "구분": role} for e in evidence or []]


PAY_DIFF_DAYS, PAY_DIFF_START, PAY_DIFF_BOTH, PAY_DIFF_FORM = "지급 한도 일수", "지급 시작일", "지급 시작일과 한도 일수", "지급 형태"


def pay_difference(data: Data, ins: dict[str, Any]) -> str:
    """설계 차이 시사점에서 지급 형태 꼬리표(insights.pay_tags)가 실제로 다른 것.

    양쪽 대표 급부의 꼬리표가 1일당 하나씩이고 1일당 밖의 꼬리표가 같으면 1일당의 시작일과 일수 한도를 견준다. 상대가 여럿이면
    다른 것을 모두 모은다. 한도 일수만 다르면 PAY_DIFF_DAYS, 시작일만 다르면 PAY_DIFF_START, 둘 다면 PAY_DIFF_BOTH, 그 밖은
    PAY_DIFF_FORM이다. 꼬리표는 "1일째부터"를 시작일 없음과 같게 보므로(pay_tags) 시작일이 없는 쪽을 첫날부터라고 적지 않는다.
    """
    def split(bid: str | None) -> tuple[list, set] | None:
        if not bid:
            return None
        tags = I.pay_tags(data.benefit_view(bid).get("limit"))
        return [t for t in tags if t.kind == I.PER_DAY], {t.key for t in tags if t.kind != I.PER_DAY}

    base = split((ins["근거"].get("기준") or [None])[0])
    start = days = False
    for bids in ins["근거"].get("비교", {}).values():
        peer = split((bids or [None])[0])
        if base is None or peer is None or len(base[0]) != 1 or len(peer[0]) != 1 or base[1] != peer[1]:
            return PAY_DIFF_FORM
        (_, b_start, b_caps), (_, p_start, p_caps) = base[0][0].key, peer[0][0].key
        start |= b_start != p_start
        days |= b_caps != p_caps
    if start and days:
        return PAY_DIFF_BOTH
    return PAY_DIFF_START if start else (PAY_DIFF_DAYS if days else PAY_DIFF_FORM)


def caution(data: Data, base: str, analysis: dict | None, relations: Relations | None = None, ctx: _Ctx | None = None,
            pts: dict | None = None) -> list[dict[str, Any]]:
    """단정 주의 목록(합의안 5번). 우열 문장을 내지 않은 담보를 두 종류로 모은다.

    - 조건이 다른 특약 함께 판매(CAUTION_OTHER): 조건 나음이나 못함으로 나왔지만 어느 쪽이든 대표 급부 밖에 조건이 다른 확정 급부가
      있어 A2, Q3에서 뺀 담보(뺀포인트의 대표밖줄). 상대 하나마다 한 건이다. 근거는 두 대표 급부(구분 "대표")와 대표 밖 급부
      (구분 "대표 밖")다. 대표끼리의 판정은 우열로 읽히지 않게 싣지 않는다.
    - 지급 형태 다름(CAUTION_PAY): 시사점 설계 차이. 무엇이 다른지(pay_difference: 지급 한도 일수, 지급 시작일, 둘 다, 지급 형태)를
      적고 양쪽 지급 형태(꼬리표 글)를 그대로 적는다. 근거는 두 대표 급부다.
      같은 담보, 같은 상대에 면책이나 감액으로 난 조건 우열 포인트(A2, Q3)가 있으면 문장을 "{담보}의 지급 한도 일수는 서로 달라 우열을
      매기지 않았습니다"처럼 좁히고, 그 상대와 견준 조건은 그 포인트의 분류에 따로 적었다고 덧붙인다(같은상대조건포인트). 조건 우열 문장은
      우열을 매기지 않은 지급 형태를 적지 않는다(insight_points). 한 담보에 우열 단정과 우열 보류가 함께 읽히지 않게 하려는 것이다.
    근거 급부가 작업 로그 대기이면 응대 포인트와 같이 같은 담보의 확정 급부로 바꾸고, 대표 급부를 바꿀 수 없으면 그 건은 뺀다.
    같은담보포인트는 같은 담보로 본문에 남은 포인트의 포인트ID다(다른 상대와 견준 포인트. 패널이 함께 보일 때 쓴다).
    pts는 points()의 결과(없으면 이력 없는 조건으로 돌린다. 시사점에서 오는 포인트는 고객 조건과 무관하다).
    """
    ctx = _ctx(data, analysis, relations, ctx)
    pts = pts if pts is not None else points(data, base, Profile(), None, ctx=ctx)
    mine = _kind_name(data, base)
    same_std: dict[str, list[str]] = {}
    for x in pts["포인트"]:
        if x["표준담보ID"]:
            same_std.setdefault(x["표준담보ID"], []).append(x["포인트ID"])
    out: list[dict[str, Any]] = []

    for x in pts["뺀포인트"]:
        if "대표밖줄" not in x:
            continue
        sid, peer = x["표준담보ID"], x["비교종형ID"][0]
        n_base, n_peer = x["대표밖줄"]["기준"], x["대표밖줄"]["상대"]
        reps = x["대표급부"]
        if not reps["기준"] or not reps["상대"]:
            continue
        rep_ev = _evidence(ctx, {"기준종형ID": base, "근거": {"기준": [reps["기준"]], "비교": {peer: [reps["상대"]]}}})
        if rep_ev is None:
            continue
        others = {"기준": ctx.holding(base).other_line_ids(sid, data.benefit_view(reps["기준"])),
                  "비교": {peer: ctx.holding(peer).other_line_ids(sid, data.benefit_view(reps["상대"]))}}
        other_ev = _evidence(ctx, {"기준종형ID": base, "근거": others}) or []
        seen = {e["급부ID"] for e in rep_ev}
        evidence = _mark(rep_ev, "대표") + _mark([e for e in other_ev if e["급부ID"] not in seen], "대표 밖")
        values = {"담보": _std_name(data, sid), "우리종형": mine, "상대": _peer_name(data, peer),
                  "상대회사": _org_name(data, peer), "기준줄": n_base, "상대줄": n_peer}
        tid = "주의_양쪽" if n_base and n_peer else ("주의_기준" if n_base else "주의_상대")
        out.append({"종류": CAUTION_OTHER, "표준담보ID": sid, "담보": values["담보"], "상대종형ID": [peer],
                    "대표밖줄": {peer: x["대표밖줄"]}, "문장": render(tid, values), "머리말": source_text(data, peer),
                    "근거": evidence, "시사점ID": x.get("시사점ID"), "같은담보포인트": same_std.get(sid, [])})

    result = ctx.result(base, pts["맞붙는종형"])
    for ins in result["시사점"]:
        if ins["유형"] != I.DESIGN:
            continue
        evidence = _evidence(ctx, ins)
        if evidence is None:
            continue
        v, peers = ins["변수"], list(ins["비교종형ID"])
        theirs = {p: v["상대지급형태"].get(_org_name(data, p)) for p in peers}
        if len(peers) >= MANY:
            # 상대가 넷 이상이면 지급 형태가 같은 상대끼리 묶어 적는다(셋까지는 상대마다. 지금 그대로)
            forms: dict[Any, list[str]] = {}
            for p in peers:
                forms.setdefault(theirs[p], []).append(p)
            said = ", ".join(render("지급_상대", {"상대": and_join((_peer_name(data, p) for p in group), UNIT_KIND),
                                                "상대지급형태": form}) for form, group in forms.items())
        else:
            said = ", ".join(render("지급_상대", {"상대": _peer_name(data, p), "상대지급형태": theirs[p]}) for p in peers)
        values = {"담보": v["담보"], "우리종형": mine, "우리지급형태": v["기준지급형태"], "상대문장": said,
                  "지급차이": pay_difference(data, ins)}
        # 같은 상대와 조건 우열이 난 포인트(A2, Q3)
        ranked = [x for x in pts["포인트"] if x["표준담보ID"] == ins["표준담보ID"] and x["세부"] in ("A2", "Q3")
                  and set(x["비교종형ID"]) & set(peers)]
        if ranked:
            text = render("주의_지급_조건", values)
            for x in ranked:
                text += " " + render("주의_지급_조건상대", {
                    "상대": and_join((_peer_name(data, p) for p in x["비교종형ID"] if p in peers), UNIT_KIND),
                    "조건항목": and_join(x["견준항목"]), "조건분류": x["분류"]})
        else:
            text = render("주의_지급", values)
        out.append({"종류": CAUTION_PAY, "표준담보ID": ins["표준담보ID"], "담보": v["담보"], "상대종형ID": peers,
                    "우리지급형태": v["기준지급형태"], "상대지급형태": theirs,
                    "대표밖줄": ins.get("대표밖조건다른줄", {}), "문장": text,
                    "머리말": header(data, base, peers)[0], "근거": _mark(evidence, "대표"), "점수": ins["점수"],
                    "시사점ID": ins["시사점ID"], "같은담보포인트": same_std.get(ins["표준담보ID"], []),
                    "같은상대조건포인트": [x["포인트ID"] for x in ranked]})
    return out


# ---------- 개정 검토 목록 ----------
def revision_candidates(data: Data, pts: dict[str, Any]) -> list[dict[str, Any]]:
    """개정 검토 목록(합의안 5번). 개정 검토 후보(Q2. 좁은 담보만 가진 것 포함) 포인트를 보장 중분류 단위로 접는다.

    묶음마다 대분류, 중분류, 담보 수, 좁은 담보만 가진 수와 담보 목록(담보, 가진 상대의 수와 이름, 우리 쪽 상태, 근거)이다.
    우리 쪽 상태는 "없음" 또는 "좁은 담보만: {좁은 담보}"다. 묶음과 담보의 차례는 비교표의 담보 순서(insights.std_order)다.
    검토 대기로 뺀 담보(모름)는 넣지 않는다.
    """
    order = I.std_order(data)
    groups: dict[tuple, dict[str, Any]] = {}
    for x in pts["포인트"]:
        if x["분류"] != REVISE:
            continue
        sid = x["표준담보ID"]
        s = data.std[sid]
        g = groups.setdefault((s["보장대분류"], s["보장중분류"]), {"대분류": s["보장대분류"], "중분류": s["보장중분류"],
                                                             "담보": [], "_차례": order.get(sid, len(order))})
        g["_차례"] = min(g["_차례"], order.get(sid, len(order)))
        orgs = list(dict.fromkeys(_org_name(data, p) for p in x["비교종형ID"]))
        narrow = x.get("좁은담보") or []
        g["담보"].append({"표준담보ID": sid, "담보": s["표준담보명"], "급부유형": s["급부유형"],
                         "가진상대수": len(orgs), "가진상대": orgs, "가진종형ID": list(x["비교종형ID"]),
                         "우리상태": "좁은 담보만: " + ", ".join(narrow) if narrow else "없음", "좁은담보": list(narrow),
                         "근거": x["근거"], "점수": x["점수"], "포인트ID": x["포인트ID"]})
    out = []
    for g in sorted(groups.values(), key=lambda g: g.pop("_차례")):
        g["담보"].sort(key=lambda d: order.get(d["표준담보ID"], len(order)))
        g["담보수"] = len(g["담보"])
        g["좁은담보만수"] = sum(1 for d in g["담보"] if d["좁은담보"])
        out.append(g)
    return out


# ---------- 치료 여정 격자 ----------
def _majors(data: Data) -> list[str]:
    present = list(dict.fromkeys(s["보장대분류"] for s in data.std.values()))
    return [m for m in C.GROUP_ORDER if m in present] + [m for m in present if m not in C.GROUP_ORDER]


def journey(data: Data, base: str, peers: list[str] | None = None, analysis: dict | None = None,
            relations: Relations | None = None, ctx: _Ctx | None = None) -> dict[str, Any]:
    """치료 여정 격자(합의안 5번). 행은 보장 대분류(비교표 차례), 열은 급부유형 다섯(JOURNEY_TYPES), 칸은 표준담보 보유 수다.

    보유는 insights.Holding.has(확정 매핑된 급부가 있는 표준담보)를 쓴다. 매핑 대기 급부만 있는 담보는 세지 않는다.
    종형은 기준 종형과 맞붙는 종형(peers. 없으면 compare.peers의 짝)이다. 종형마다 열 합계(합계)와 전체 수를 내고,
    다섯 밖의 급부유형은 칸에 넣지 않고 기타로 센다. 담보는 칸마다 표준담보ID 목록이다.
    """
    ctx = _ctx(data, analysis, relations, ctx)
    ctx.check_base(base)
    peers = ctx.default_peers(base) if peers is None else [p for p in peers if p != base]
    majors = _majors(data)
    order = ctx.order
    rows = []
    for vid in [base] + peers:
        held = sorted((s for s in ctx.holding(vid).has if s in data.std), key=lambda s: (order.get(s, len(order)), s))
        sids = {m: {t: [] for t in JOURNEY_TYPES} for m in majors}
        other = []
        for sid in held:
            s = data.std[sid]
            if s.get("급부유형") in JOURNEY_TYPES:
                sids[s["보장대분류"]][s["급부유형"]].append(sid)
            else:
                other.append(sid)
        cells = {m: {t: len(sids[m][t]) for t in JOURNEY_TYPES} for m in majors}
        rows.append({"종형ID": vid, "이름": _peer_name(data, vid), "칸": cells, "담보": sids,
                     "합계": {t: sum(cells[m][t] for m in majors) for t in JOURNEY_TYPES},
                     "전체": len(held), "기타": len(other)})
    return {"행": majors, "열": list(JOURNEY_TYPES), "종형": rows}


# ---------- 한도 표 ----------
def limit_steps(data: Data) -> list[dict[str, Any]]:
    """한도 표(합의안 5번). 우체국의 판매 중인 정밀비교 종형(insights.base_variants의 기준 종형)마다 주계약의 나이 구간과
    최대 가입금액(만원). eligibility.segments를 성별마다 부르고, 구간은 [{"lo", "hi", "max", "pend"}]다(pend는 그 한도를 정한
    조건행이 검토 대기인지). 성별같음이 참이면 두 성별의 구간이 같다."""
    out = []
    for vid in I.base_variants(data)[1]:
        v = data.variants[vid]
        main = data.main_rider(vid)
        seg = {s: eligibility.segments(data, main, s) if main else [] for s in ("M", "F")}
        out.append({"종형ID": vid, "이름": _kind_name(data, vid), "심사": v.get("심사유형"), "간편고지약칭": v.get("간편고지약칭"),
                    "갱신": v.get("갱신유형"), "환급": v.get("환급유형"), "주계약특약ID": main, "구간": seg,
                    "성별같음": seg["M"] == seg["F"]})
    return out


# ---------- 보류 요약 ----------
PENDING_KINDS = ("매핑 대기", "작업 로그 대기")


def pending_summary(data: Data, base: str, analysis: dict | None, relations: Relations | None = None,
                    ctx: _Ctx | None = None, peers: list[str] | None = None) -> dict[str, Any]:
    """보류 요약(합의안 5번). 기준 종형과 맞붙는 종형 사이의 공통 담보 쌍 가운데 검토 대기로 뺀 쌍을 보장 대분류별로 센다.

    분모는 insights 결과의 비교쌍목록(공통 담보 쌍 전체)이고, 뺀 쌍은 그 가운데 뺌이 참인 쌍(insights의 뺀비교)이다.
    사유별은 뺀 쌍의 사유(매핑 대기, 작업 로그 대기)마다 그 사유가 든 쌍의 수다. 한 쌍에 두 사유가 함께 들 수 있다.
    """
    ctx = _ctx(data, analysis, relations, ctx)
    result = ctx.result(base, peers)
    peer_ids = [x["종형ID"] for x in result["맞붙는종형"]]
    pairs = result["비교쌍목록"]
    rows = []
    for m in _majors(data):
        mine = [x for x in pairs if data.std[x["표준담보ID"]]["보장대분류"] == m]
        if not mine:
            continue
        dropped = [x for x in mine if x["뺌"]]
        rows.append({"대분류": m, "공통담보쌍": len(mine), "뺀쌍": len(dropped), "견준쌍": len(mine) - len(dropped),
                     "상대별": {p: sum(1 for x in dropped if x["비교종형ID"] == p) for p in peer_ids}})
    reasons = {k: sum(1 for x in result["뺀비교"] if any(k in r for r in x["사유"])) for k in PENDING_KINDS}
    return {"맞붙는종형": peer_ids, "공통담보쌍": result["비교쌍"], "뺀쌍": result["뺀비교쌍"],
            "견준쌍": result["비교쌍"] - result["뺀비교쌍"], "대분류": rows, "사유별": reasons}


# ---------- 개정 변동과 시장 소식 ----------
REVISION_KINDS = ("신설", "변경", "종료")
REVISION_PRIORITY = {"신설": 0, "종료": 1, "변경": 2}       # 짝마다 종류가 엇갈리면 앞선 것으로 센다
REVISION_FIELDS = {"pay": "지급액", "top": "최대 가입 시 지급액", "red": "감액", "wait": "면책", "limit": "지급 형태 문구",
                   "std": "표준담보", "range": "가입금액 범위", "renew": "갱신주기", "added": "급부 추가", "removed": "급부 삭제"}


def _benefit_key(data: Data, bid: str) -> tuple[str, str]:
    """개정 변동을 세는 담보 열쇠와 이름. 확정 표준담보가 있으면 그 담보, 없으면 괄호를 뗀 급부 이름이다."""
    view = data.benefit_view(bid)
    if view["std"]:
        return view["std"], data.std[view["std"]]["표준담보명"]
    name = str(view["name"])
    plain = re.sub(r"\([^()]*\)", "", name).strip() or name
    return "급부:" + RV._stem(name), plain


def _variant_keys(data: Data, vid: str) -> set[str]:
    return {_benefit_key(data, b)[0] for t in data.riders_of.get(vid, []) for b in data.benefits_of.get(t, [])}


def revision_summary(data: Data) -> dict[str, Any]:
    """우체국 직전 개정과 견준 담보 변동(브리핑 (나)와 내보내기의 개정 변동 요약). revision.diff_pair의 결과를 담보 단위로 센다.

    대상은 개정 후 종형이 우리 기관인 짝(revision.variant_pairs)이다. 담보 열쇠는 _benefit_key다.
    - 변경: 이어진 급부 쌍에서 달라진 항목이 있는 담보, 가입금액 범위나 갱신주기가 바뀐 특약의 담보, 그리고 급부가 더해지거나
      빠졌지만 그 담보가 개정 전후 종형에 모두 있는 담보.
    - 신설: 새로 생긴 급부(새 특약의 급부 포함) 가운데 개정 전 종형에 없던 담보.
    - 종료: 없어진 급부(없어진 특약의 급부 포함) 가운데 개정 후 종형에 없는 담보.
    개정 짝이 여럿이면(종형마다 짝이 있다) 담보 열쇠로 합치고, 한 담보는 신설, 종료, 변경 차례로 한 종류로만 센다.
    관문변경은 간편심사 고지 질문(eligibility.gate) 값이 바뀐 짝과 항목, 가입나이변경은 주계약 나이 구간이 바뀐 개정 후 종형이다.
    """
    pairs = [(o, n) for o, n in RV.variant_pairs(data) if data.variants[n].get("기관코드") == HOME_ORG]
    found: dict[str, dict[str, Any]] = {}
    per_pair, gates, ages = [], [], []

    def note(key: str, name: str, kind: str, field: str, new: str) -> None:
        item = found.setdefault(key, {"열쇠": key, "담보": name, "종류": kind, "항목": [], "종형ID": []})
        if REVISION_PRIORITY[kind] < REVISION_PRIORITY[item["종류"]]:
            item["종류"] = kind
        if REVISION_FIELDS[field] not in item["항목"]:
            item["항목"].append(REVISION_FIELDS[field])
        if new not in item["종형ID"]:
            item["종형ID"].append(new)

    for old, new in pairs:
        diff = RV.diff_pair(data, old, new)
        old_keys, new_keys = _variant_keys(data, old), _variant_keys(data, new)
        mine: dict[str, set[str]] = {k: set() for k in REVISION_KINDS}
        added = [b for t in diff["addedRiders"] for b in data.benefits_of.get(t, [])]
        removed = [b for t in diff["removedRiders"] for b in data.benefits_of.get(t, [])]
        for entry in diff["changes"]:
            for b in entry["benefits"]:
                key, name = _benefit_key(data, b["new"])
                for item in b["items"]:
                    note(key, name, "변경", item["field"], new)
                mine["변경"].add(key)
            for item in entry["rider"]:
                for b in data.benefits_of.get(entry["new"], []):
                    key, name = _benefit_key(data, b)
                    note(key, name, "변경", item["field"], new)
                    mine["변경"].add(key)
            added += entry["added"]
            removed += entry["removed"]
        for bid in added:
            key, name = _benefit_key(data, bid)
            kind = "변경" if key in old_keys else "신설"
            note(key, name, kind, "added", new)
            mine[kind].add(key)
        for bid in removed:
            key, name = _benefit_key(data, bid)
            kind = "변경" if key in new_keys else "종료"
            note(key, name, kind, "removed", new)
            mine[kind].add(key)
        mine["변경"] -= mine["신설"] | mine["종료"]
        per_pair.append({"전": old, "후": new, **{k: len(mine[k]) for k in REVISION_KINDS}})
        gates += [{"후": new, "항목": g["field"], "전값": g["old"], "후값": g["new"]} for g in diff["gate"] if g["old"] != g["new"]]
        if diff["ages"]["old"] != diff["ages"]["new"]:
            ages.append(new)

    order = I.std_order(data)
    items = sorted(found.values(), key=lambda x: (REVISION_KINDS.index(x["종류"]), order.get(x["열쇠"], len(order)), x["열쇠"]))
    count = {k: sum(1 for x in items if x["종류"] == k) for k in REVISION_KINDS}
    return {"짝": per_pair, "담보": items, "수": {**count, "전체": len(items)}, "관문변경": gates, "가입나이변경": ages}


NEWS_QUOTE_NOTE = "보도 내용을 요약해 옮긴 글이며 우체국의 판단이 아닙니다. 회사가 내세운 표현과 보험료 문구도 보도에 적힌 대로 두었습니다."
QUOTE_WATCH = ("보험료",)          # 금지어(FORBIDDEN) 밖에 인용 요약에서 따로 짚는 말


def quote_flags(text: Any) -> list[str]:
    """인용 요약에 든 금지어와 QUOTE_WATCH의 말(차례는 FORBIDDEN, QUOTE_WATCH 순서)."""
    s = str(text or "")
    return forbidden_in(s) + [w for w in QUOTE_WATCH if w in s]


def news_summary(data: Data) -> dict[str, Any]:
    """최근 모은 시장 소식(브리핑 (나)). weekly.news가 고른 소식(통과 기준 이상이고, 이번 주차나 가장 최근 수집주차)을 싣는다.

    표준담보에 이어진 소식은 관련표준담보ID(쉼표로 여럿 적을 수 있다)에 사전에 있는 표준담보ID가 하나라도 든 소식이다.
    요약(sys_시장동향 핵심요약)은 보도를 옮긴 글이라 문장 틀을 거치지 않고, 금지어 검사 대신 인용으로 표시한다. 소식마다
    인용(참), 출처표시("{매체} 보도 요약", 매체가 없으면 "보도 요약"), 주의표현(quote_flags. 화면이 인용 안의 단정과 보험료
    문구를 짚을 때 쓴다)을 달고, 묶음에 인용안내(NEWS_QUOTE_NOTE)를 단다. 요약 글은 바꾸지 않는다.
    """
    week = weekly.week_of(data.meta.get("snapshot_at"))
    found = weekly.news(data, week)
    rows = {t["동향ID"]: t for t in data.trends}
    items = []
    for it in found["items"]:
        t = rows.get(it["id"], {})
        stds = [s.strip() for s in str(t.get("관련표준담보ID") or "").split(",") if s.strip() in data.std]
        items.append({"동향ID": it["id"], "회사": it["orgName"], "분류": it["kind"], "발표일자": it["date"],
                      "요약": it["summary"], "매체": it["media"], "출처URL": it["url"], "표준담보ID": stds,
                      "인용": True, "출처표시": f"{it['media']} 보도 요약" if it["media"] else "보도 요약",
                      "주의표현": quote_flags(it["summary"])})
    kinds: dict[str, int] = {}
    for it in items:
        kinds[it["분류"]] = kinds.get(it["분류"], 0) + 1
    return {"주차": found["week"], "지난주차": found["fallback"], "통과기준": found["threshold"], "건수": len(items),
            "연결": sum(1 for it in items if it["표준담보ID"]), "분류별": kinds, "인용안내": NEWS_QUOTE_NOTE, "소식": items}


# ---------- 브리핑 다섯 줄 ----------
def representative_profile(data: Data) -> Profile:
    """브리핑의 대표 조건: 이력 없음, 기준값 탭의 대표 나이(REP_WEEKLY_AGE)와 첫 성별(REP_WEEKLY_SEX_1). 없으면 나이와 성별 없음."""
    age = data.setting_num("REP_WEEKLY_AGE")
    sex = data.setting_text("REP_WEEKLY_SEX_1")
    return Profile(age=int(age) if age is not None else None, sex=sex if sex in ("M", "F") else None)


def _money(value: Any) -> str:
    x = float(value)
    return f"{int(x):,}" if x.is_integer() else f"{x:,}"


def cells_of(seg: dict[str, Any], label: str) -> list[str]:
    """지도에서 라벨이 같은 칸을 "행 이름 lo~hi세"로. 한 행에서 이웃한 열은 합친다."""
    out = []
    for r, line in zip(seg["행"], seg["칸"]):
        run: list[dict] = []
        for c, x in list(zip(seg["열"], line)) + [(None, None)]:
            if x is not None and x["라벨"] == label:
                run.append(c)
                continue
            if run:
                out.append(f"{r['이름']} {run[0]['lo']}~{run[-1]['hi']}세")
                run = []
    return out


def _brief_line(line: str, scope_name: str, values: dict, sentence: str, tab: str, used: list[str], **more: Any) -> dict:
    return {"줄": line, "범위": scope_name, "값": values, "문장": sentence, "갈곳": tab, "틀": used, **more}


def no_age_companies(data: Data, renewal: str | None = None) -> list[str]:
    """지도가 보는 상대 회사(거르개 안의 관문 대상 종형) 가운데 어느 종형에도 주계약 가입나이 자료가 없는 회사의 이름."""
    has: dict[str, bool] = {}
    for vid in gate_targets(data, renewal):
        org = _org(data, vid)
        if org == HOME_ORG:
            continue
        main = data.main_rider(vid)
        has[org] = has.get(org, False) or bool(main and data.condition_rows(main))
    return [data.org_name(o) for o, ok in has.items() if not ok]


def spread(values: list[float]) -> dict[str, float] | None:
    """{"최소", "중앙", "최대"}. 중앙은 statistics.median이고 정수로 떨어지면 정수로 적는다. 값이 없으면 None."""
    if not values:
        return None
    mid = statistics.median(values)
    return {"최소": min(values), "중앙": int(mid) if float(mid).is_integer() else mid, "최대": max(values)}


def _gate_only_cells(data: Data, seg: dict[str, Any]) -> tuple[int, list[str], bool]:
    """(열린 상대 종형이 관문전용뿐인 칸의 수, 그 종형 이름, 그 종형이 모두 우리 간편 종형에 없는 기간 질문인지)."""
    cells = [x for line in seg["칸"] for x in line if x.get("관문만수집")]
    found = list(dict.fromkeys((y["종형ID"], y["이름"]) for x in cells for y in x["관문만수집"]))
    ours = {_period(data.variants[v]) for v in gate_targets(data, seg["갱신유형"])
            if _org(data, v) == HOME_ORG and _is_simple(data, v)}
    unique = all(_period(data.variants[v]) not in ours for v, _ in found)
    return len(cells), [name for _, name in found], unique


def _line_landscape(data: Data, seg: dict[str, Any]) -> dict[str, Any]:
    """(가) 고객군 지형. 라벨 다섯의 칸 수(라벨별. 합이 전체칸수)를 값에 담고 0칸이 아닌 라벨은 모두 문장에 적는다.
    우리간편닫힘칸수는 우리 간편 닫힘 칸 가운데 보조가 일반심사 확인인 칸이다(모두 그렇지 않으면 가_닫힘_일부 틀).
    관문만칸수와 관문만종형은 열린 상대 종형이 관문전용뿐인 칸(칸의 관문만수집)과 그 종형 이름이고, 나이자료없음회사는
    no_age_companies다."""
    cells = [x for line in seg["칸"] for x in line]
    labels = {lab: sum(1 for x in cells if x["라벨"] == lab) for lab in LABELS.values()}
    only, both = labels[LABELS[ONLY_OPEN]], labels[LABELS[BOTH_OPEN]]
    closed_all, all_closed, nodata = labels[LABELS[ONLY_CLOSED]], labels[LABELS[ALL_CLOSED]], labels[LABELS[NO_DATA]]
    closed = sum(1 for x in cells if x["라벨"] == LABELS[ONLY_CLOSED] and x["보조"] == GENERAL_NOTE)
    places = cells_of(seg, LABELS[ONLY_OPEN])
    summary = ", ".join(places[:2]) + (f" 외 {len(places) - 2}개 구간" if len(places) > 2 else "")
    gate_cells, gate_names, unique = _gate_only_cells(data, seg)
    no_age = no_age_companies(data, seg["갱신유형"])
    values = {"전체칸수": len(cells), "우리간편만열림칸수": only, "우리간편만열림요약": summary, "함께열림칸수": both,
              "우리간편닫힘칸수": closed, "우리간편닫힘라벨칸수": closed_all, "간편모두닫힘칸수": all_closed,
              "자료없음칸수": nodata, "라벨별": labels, "관문만칸수": gate_cells, "관문만종형": gate_names,
              "나이자료없음회사": no_age, "성별": seg["성별"], "갱신유형": seg["갱신유형"],
              "열린상대수분포": spread([x["열린상대수"] for x in cells if "열린상대수" in x])}
    if not cells:
        used = ["가_자료없음"]
        text = render("가_자료없음", {})
        return _brief_line("가", SCOPE_ALL, values, text, TAB_MARKET, used, 구역="고객군 지형")
    plan = [(only, "가_우리만", "가_우리만_없음"), (both, "가_함께", "가_함께_없음"),
            (closed_all, "가_닫힘" if closed == closed_all else "가_닫힘_일부", "가_닫힘_없음"),
            (all_closed, "가_모두닫힘", None), (nodata, "가_모름", None)]
    used = []
    for i, (n, yes, no) in enumerate(plan):
        if n:
            used.append(yes)
        elif no and any(m for m, _, _ in plan[i + 1:]):       # 0칸 절은 뒤에 0칸이 아닌 절이 있을 때만 적는다
            used.append(no)
    text = render("가", {"전체칸수": len(cells), "절목록": ", ".join(render(t, values) for t in used)})
    tails = (["가_관문만" if unique else "가_관문만_같은유형"] if gate_cells else []) + (["가_나이자료없음"] if no_age else [])
    if tails:              # 관문만 열린 칸과 나이 자료가 없는 상대는 둘째 문장 하나로 잇는다
        text += " " + _connect([render(t, {**values, "관문만종형": and_join(gate_names, UNIT_KIND),
                                           "나이자료없음회사": and_join(no_age, UNIT_ORG)})
                                for t in tails])
    return _brief_line("가", SCOPE_ALL, values, text, TAB_MARKET, used + tails, 구역="고객군 지형")


def product_names(data: Data, vids: Iterable[str]) -> str:
    """종형들의 공시상품명을 잇는다. 공시상품명이 종형명으로 끝나면(우체국은 종마다 공시상품이다) 앞부분이 같은 것끼리 묶어
    "…2606 2종(간편가입325), 3종(간편가입355)와 4종(일반가입)"처럼 적는다(and_join). 묶음이 여럿이면 묶음끼리는 쉼표로 잇는다."""
    groups: dict[str, list[str]] = {}
    for vid in dict.fromkeys(vids):
        v = data.variants[vid]
        product, kind = str(v.get("공시상품명") or ""), str(v.get("종형명") or "")
        head = product[:-len(kind)].strip() if kind and product.endswith(kind) else ""
        if head:
            groups.setdefault(head, []).append(kind)
        else:
            groups.setdefault(product or kind or vid, [])
    return ", ".join(f"{head} {and_join(kinds)}" if kinds else head for head, kinds in groups.items())


def _line_market(data: Data, rev: dict[str, Any], news: dict[str, Any]) -> dict[str, Any]:
    """(나) 개정과 시장. 개정상품은 개정 짝의 개정 후 종형의 공시상품명(product_names. 여럿이면 모두)이고, 개정전상품은 개정 전
    종형의 것이다(값에만 싣는다). 목록 열쇠에는 공시상품명을 그대로 싣는다."""
    n = rev["수"]
    split = ", ".join(f"{k} {n[k]}" for k in REVISION_KINDS if n[k])
    after = [x["후"] for x in rev["짝"] if x["후"] in data.variants]
    before = [x["전"] for x in rev["짝"] if x["전"] in data.variants]
    values = {"개정변동수": n["전체"], "개정나눔": split, **{f"개정{k}": n[k] for k in REVISION_KINDS},
              "개정짝수": len(rev["짝"]), "개정상품": product_names(data, after), "개정전상품": product_names(data, before),
              "개정상품목록": list(dict.fromkeys(str(data.variants[v].get("공시상품명")) for v in after)),
              "개정전상품목록": list(dict.fromkeys(str(data.variants[v].get("공시상품명")) for v in before)),
              "시장소식수": news["건수"], "연결소식수": news["연결"], "소식주차": news["주차"]}
    first = "나_개정_자료없음" if not rev["짝"] else ("나_개정" if n["전체"] else "나_개정_없음")
    second = "나_소식_없음" if not news["건수"] else ("나_소식" if news["연결"] else "나_소식_연결없음")
    text = render("나", {"절1": render(first, values), "절2": render(second, values)})
    return _brief_line("나", SCOPE_ALL, values, text, TAB_MARKET, [first, second], 구역="개정과 시장")


def _line_gate(data: Data, base: str, p: Profile, pts: dict[str, Any]) -> dict[str, Any]:
    """(다) 가입 관문과 한도. 관문차이수는 고지 질문 범위가 다른 상대의 수(맞붙는 상대와 견준 G3이 있는 회사 수)이고,
    관문차이상대는 그 회사 이름이다. 한도는 조건 p의 나이에서 주계약 한도다(나이가 없으면 적지 않는다).
    관문상태와 질문은 기준 종형의 variant_gate 값이다(일반심사 기준 종형은 이력과 무관하게 심사로 확인)."""
    peers = pts["맞붙는종형"]
    span = age_span(data, base, p.sex)
    g = variant_gate(data, base, p)
    # 맞붙는 상대와 견준 G3만 센다. 짝이 아닌 종형의 더 짧은 기간 질문(shorter_questions)은 관문 탭의 포인트에만 둔다
    diff_peers = [v for x in pts["포인트"] if x["세부"] == "G3" and set(x["비교종형ID"]) <= set(peers)
                  for v in x["비교종형ID"]]
    diff_orgs = list(dict.fromkeys(_org(data, v) for v in diff_peers))
    gate_diff = len(diff_orgs)
    struct = len({_org(data, x) for x in peers if structure_differs(data, base, x)})
    general = data.variants[base].get("심사유형") != SIMPLE
    values = {"우리종형": _kind_name(data, base), "우리최저": span[0] if span else None, "우리최고": span[1] if span else None,
              "나이": p.age, "주계약한도만원": _money(g["한도만원"]) if g["한도만원"] is not None else None,
              "관문차이수": gate_diff, "관문차이상대": [data.org_name(o) for o in diff_orgs], "구조다름회사수": struct,
              "심사": data.variants[base].get("심사유형"), "관문상태": g["상태"], "질문": g["질문"]}
    if span is None:
        first = "다_나이없음"
    elif p.age is None:
        first = "다_나이_나이없음"
    elif g["나이"] == AGE_NO:
        first = "다_나이_나이밖"
    else:
        first = "다_나이" if g["한도만원"] is not None else "다_나이_한도모름"
    if not peers:
        used = [first]
        text = render("다_상대없음", {"우리종형": values["우리종형"], "절1": render(first, values)})
    else:
        second = "다_관문_일반" if general else ("다_관문" if gate_diff else "다_관문_없음")
        third = "다_구조" if struct else "다_구조_없음"
        used = [first, second, third]
        text = render("다", {"우리종형": values["우리종형"], **{f"절{i}": render(t, values) for i, t in enumerate(used, 1)}})
    check = bool(gate_diff)
    return _brief_line("다", SCOPE_BASE, values, text, TAB_GATE, used, 원문대조=check,
                       원문대조글=SOURCE_CHECK_TEXT if check else None)


def _line_position(pts: dict[str, Any], grid: dict[str, Any], cautions: list[dict], mine: str) -> dict[str, Any]:
    """(라) 담보 포지션. 첫 문장은 견준 쌍(공통 담보 쌍에서 검토 대기를 뺀 것)과 우열을 단정하지 않은 비교 두 종류(조건이 다른
    특약 함께 판매 단정보류수, 지급 형태 다름 지급형태다름수)를 잇고, 둘째 문장은 기준 종형과 맞붙는 상대 종형의 보유 수(치료 여정
    격자의 줄마다 전체. 확정 급부 기준이고, 기준 종형의 다섯 급부유형 밖은 기타로 덧붙인다)다. mine은 기준 종형의 종형명이다."""
    s = pts["범위"]
    row = grid["종형"][0]
    held = row["합계"]
    compared = s["비교쌍"] - s["뺀비교쌍"]
    held_back = sum(1 for c in cautions if c["종류"] == CAUTION_OTHER)
    pay = sum(1 for c in cautions if c["종류"] == CAUTION_PAY)
    split = [f"{t} {held[t]}" for t in JOURNEY_TYPES] + ([f"기타 {row['기타']}"] if row.get("기타") else [])
    others = [{"종형ID": r.get("종형ID"), "이름": r.get("이름"), "보유수": r["전체"]} for r in grid["종형"][1:]]
    values = {"우리종형": mine, "공통담보쌍": s["비교쌍"], "견준쌍": compared, "뺀비교쌍": s["뺀비교쌍"],
              **{f"{t}수": held[t] for t in JOURNEY_TYPES}, "기타수": row.get("기타", 0), "보유수": row["전체"],
              "보유나눔": ", ".join(split), "단정보류수": held_back, "지급형태다름수": pay, "상대보유": others,
              "상대보유나눔": ", ".join(render("라_상대보유", {"상대": r["이름"], "보유수": r["보유수"]}) for r in others)}
    # 상대가 넷 이상이면 상대마다의 보유 수(상대보유나눔) 대신 범위와 중앙값을 적는다(맞붙는 상대 종형은 회사마다 하나다)
    many = len(others) >= MANY
    if many:
        dist = spread([r["보유수"] for r in others])
        values.update({"상대회사수": len(others), "상대보유분포": dist,
                       "상대보유요약": render("라_상대보유같음" if dist["최소"] == dist["최대"] else "라_상대보유범위",
                                         {"최소": dist["최소"], "최대": dist["최대"], "중앙": dist["중앙"]})})
    if not s["비교쌍"]:
        first = "라_범위_없음"
    elif not compared:
        first = "라_범위_모두대기"
    else:
        first = "라_범위" if s["뺀비교쌍"] else "라_범위_대기없음"
    second = ("라_보유" if row["전체"] else "라_보유_없음") + (("_상대많음" if many else "_상대") if others else "")
    third = "라_보류" if held_back or pay else "라_보류_없음"
    used = [first, second, third]
    # 첫 문장은 견준 쌍과 우열을 단정하지 않은 비교를 잇고, 둘째 문장은 보유 수다(틀 목록은 지금처럼 범위, 보유, 보류 차례)
    text = render("라", {"절1": _connect([render(first, values), render(third, values)]), "절2": render(second, values)})
    return _brief_line("라", SCOPE_BASE, values, text, TAB_COMPARE, used)


def _line_insight(pts: dict[str, Any]) -> dict[str, Any]:
    """(마) 영업 인사이트. 다섯 분류의 포인트 수를 모두 적고 그 합(전체수)을 앞에 적는다(관문 차이 포함). 범위에 검토 대기로 뺀
    비교쌍이나 시사점이 있으면 "검토를 마친 범위에서"라는 전제를 붙인다(_검토후 틀)."""
    n = pts["분류집계"]
    s = pts.get("범위") or {}
    pending = (s.get("뺀비교쌍") or 0) + (s.get("뺀시사점") or 0)
    strengths = [x for x in pts["포인트"] if x["분류"] == STRENGTH]
    shown = [x["표준담보명"] for x in strengths if x["브리핑"]][:2]
    summary = ", ".join(shown) + (" 등" if shown and len(strengths) > len(shown) else "")
    values = {"앞세울수": n[STRENGTH], "대표강점요약": summary, "관련담보수": n[RELATED], "조건열위수": n[DEFEND],
              "개정검토수": n[REVISE], "관문차이수": n[GATE_DIFF], "검토대기쌍": s.get("뺀비교쌍") or 0,
              "검토전제": bool(pending), "전체수": sum(n[c] for c in CATEGORIES)}
    after = "_검토후" if pending else ""
    if not any(n[c] for c in CATEGORIES):
        used = ["마_없음" + after]
        text = render(used[0], {})
    else:
        first = "마_강점_없음" if not n[STRENGTH] else ("마_강점" if summary else "마_강점_요약없음")
        used = (["마_검토후"] if pending else []) + [first]       # 틀 목록은 다른 줄처럼 절의 틀이고, 전제가 붙으면 그 틀을 앞에 둔다
        text = render("마" + after, {**values, "절1": render(first, values)})
    return _brief_line("마", SCOPE_BASE, values, text, TAB_INSIGHT, used)


def briefing(data: Data, base: str, p: Profile, analysis: dict | None, relations: Relations | None = None,
             ctx: _Ctx | None = None, seg: dict | None = None, rev: dict | None = None, news: dict | None = None,
             pts: dict | None = None, cautions: list[dict] | None = None, grid: dict | None = None) -> list[dict[str, Any]]:
    """브리핑 다섯 줄(합의안 3번). 줄의 차례는 탭 차례와 같다.

    (가) 고객군 지형: 전체 고객군 기준. seg는 segment_map(성별 남, 갱신 거르개 전체)이다. 라벨 다섯의 칸 수(합이 전체칸수)와
         관문만 열린 칸, 나이 자료가 없는 상대 회사(_line_landscape).
    (나) 개정과 시장: 전체 기준. revision_summary와 news_summary로 센다. 개정 짝의 상품 이름을 적는다.
    (다) 가입 관문과 한도: 선택 종형 기준. 관문차이수는 고지 질문 범위가 다른 상대의 수(맞붙는 상대와 견준 G3. 짝이 아닌 종형의
         더 짧은 기간 질문은 세지 않는다), 한도는 조건 p의 나이에서 주계약의 한도다.
    (라) 담보 포지션: 선택 종형 기준. 견준쌍은 공통 담보 쌍에서 검토 대기로 뺀 쌍을 뺀 수, 보유 수는 치료 여정 격자의 기준 종형과
         상대 종형 줄의 전체(확정 급부 기준. 공통 담보 쌍 안의 수가 아니라 문장을 가른다), 우열을 단정하지 않은 비교는 단정 주의
         목록의 두 종류(단정보류수, 지급형태다름수)다.
    (마) 영업 인사이트: 선택 종형 기준. 다섯 분류의 포인트 수(본문 전체. 관문 차이 포함)와 그 합, 브리핑에 싣는 앞세울 강점 가운데
         위의 두 담보 이름. 검토 대기로 뺀 비교가 있으면 "검토를 마친 범위에서"라는 전제를 붙인다.
    줄마다 {"줄", "범위", "값", "문장", "갈곳", "틀"}이다. 줄마다 한두 문장이고(여러 절은 _connect로 잇는다), 한 줄 안에서 같은 종형
    이름을 되풀이하지 않는다. 0건이면 _없음 틀로 갈라 빈 값 예외가 나지 않는다.
    값의 기존 열쇠는 지우지 않는다(시안 화면이 읽는다).
    """
    ctx = _ctx(data, analysis, relations, ctx)
    pts = pts if pts is not None else points(data, base, p, None, ctx=ctx)
    seg = seg if seg is not None else segment_map(data, "M", None, None, ctx=ctx)
    rev = rev if rev is not None else revision_summary(data)
    news = news if news is not None else news_summary(data)
    cautions = cautions if cautions is not None else caution(data, base, None, ctx=ctx, pts=pts)
    grid = grid if grid is not None else journey(data, base, pts["맞붙는종형"], ctx=ctx)
    return [_line_landscape(data, seg), _line_market(data, rev, news), _line_gate(data, base, p, pts),
            _line_position(pts, grid, cautions, _kind_name(data, base)), _line_insight(pts)]


# ---------- 지도 칸의 관문 포인트 ----------
def gate_base(data: Data, home: dict[str, Any] | None, question_closed: bool = False) -> str | None:
    """칸의 관문 포인트를 계산할 우리 종형. 열린 간편심사 종형 가운데 질문 기간이 긴 것, 없으면 고지 질문에는 해당하지 않고
    나이로만 닫힌 간편심사 종형 가운데 질문 기간이 긴 것(G2), 그것도 없으면 None이다. 일반심사 종형은 관문 포인트가 없다.
    question_closed가 참이면 마지막에 고지 질문에 걸린 간편심사 종형 가운데 질문 기간이 가장 짧은 것(G2_질문. 이력에 가장 가까이
    닿는 종형)까지 본다. 관문전용 종형은 고르지 않는다."""
    if not home:
        return None
    simple = [x for x in home["종형"] if data.variants[x["종형ID"]].get("심사유형") == SIMPLE and not gate_only(data, x["종형ID"])]
    opened = [x["종형ID"] for x in simple if x["상태"] == OPEN]
    aged = [x["종형ID"] for x in simple if x["질문"] == Q_NONE and x["나이"] == AGE_NO]
    cands = opened or aged
    if cands:
        return min(cands, key=lambda v: _rank(data, v))
    hit = [x["종형ID"] for x in simple if x["질문"] == Q_HIT] if question_closed else []
    return min(hit, key=lambda v: (_period(data.variants[v]), data.variant_order.index(v))) if hit else None


def cell_gate_points(ctx: _Ctx, p: Profile, g: dict | None = None) -> tuple[list[dict], str | None]:
    """(칸의 관문 포인트, 그 기준 종형). 맞붙는 종형은 거르개(p.renewal) 안의 종형에서 compare.peers 규칙으로 고른다
    (거르개가 없으면 응대 포인트의 짝과 같다). 칸의 숫자와 라벨이 거르개 안의 회사만 보므로 패널의 관문 포인트도 거르개 밖
    상대와 견주지 않는다. g는 gate(data, p)의 결과(없으면 계산한다).
    라벨이 우리 간편 닫힘인 칸은 고지 질문에 걸린 우리 종형까지 기준으로 본다(gate_base의 question_closed. 열린 상대가 있어 G2가 나온다)."""
    data = ctx.data
    g = g if g is not None else gate(data, p)
    home = g["회사"].get(HOME_ORG)
    base = gate_base(data, home, question_closed=simple_classify(data, g)[0] == ONLY_CLOSED)
    if base is None or base not in ctx.bases:
        return [], None
    peers = ctx.peers_within(base, p.renewal)
    out = _Points(ctx, base, peers)
    gate_points(ctx, base, peers, p, out, g)
    return _sort(ctx, out.kept), base


# ---------- 화면용 내보내기 ----------
class _Texts:
    """되풀이되는 글(머리말, 회사수)을 한 번만 싣고 번호로 가리킨다."""

    def __init__(self) -> None:
        self.items: list[str] = []
        self.index: dict[str, int] = {}

    def add(self, text: str | None) -> int | None:
        if text is None:
            return None
        if text not in self.index:
            self.index[text] = len(self.items)
            self.items.append(text)
        return self.index[text]


def _export_evidence(data: Data, ev: list[dict]) -> list[dict]:
    out = []
    for e in ev:
        row = {k: e[k] for k in ("종형ID", "문서", "쪽", "급부ID") if e.get(k) is not None}
        if e.get("급부ID"):
            row["급부명"] = data.benefits[e["급부ID"]].get("원시급부명")
        if e.get("구분"):
            row["구분"] = e["구분"]
        out.append(row)
    return out


def _export_point(data: Data, x: dict[str, Any], texts: _Texts) -> dict[str, Any]:
    out = {"포인트ID": x["포인트ID"], "분류": x["분류"], "세부": x["세부"], "세부이름": x["세부이름"], "표준담보ID": x["표준담보ID"],
           "문장": x["문장"], "카드질문": x["카드질문"], "카드답": x["카드답"],
           "머리말": texts.add(x["머리말"]), "회사수": texts.add(x["회사수"]), "비교종형ID": x["비교종형ID"],
           "근거": _export_evidence(data, x["근거"]), "점수": x["점수"], "목적": x["목적"], "구조다름": x["구조다름"],
           "원문대조": x["원문대조"], "원문대조글": x["원문대조글"], "브리핑": x["브리핑"],
           "관련기관코드": compared_orgs(data, x["비교종형ID"])}
    for key in ("주의", "좁은담보", "견준항목", "관문만수집", "차이항목"):
        if x.get(key):
            out[key] = x[key]
    return out


def _variant_info(data: Data, vid: str) -> dict[str, Any]:
    v = data.variants[vid]
    return {"회사": _org_name(data, vid), "기관코드": _org(data, vid), "종형명": v.get("종형명"), "이름": _peer_name(data, vid),
            "전체이름": full_name(data, vid), "심사": v.get("심사유형"), "간편고지약칭": v.get("간편고지약칭"),
            "갱신": v.get("갱신유형"), "환급": v.get("환급유형"), "적용시작일": v.get("적용시작일"),
            "판매종료일": v.get("판매종료일"), "비교역할": v.get("비교역할구분")}


def _export_map(ctx: _Ctx, seg: dict[str, Any], pool: dict[str, dict], texts: _Texts) -> dict[str, Any]:
    cells = []
    for r, line in zip(seg["행"], seg["칸"]):
        row = []
        for c, x in zip(seg["열"], line):
            p = Profile(age=c["lo"], sex=seg["성별"], since=r["since"], surgery_only=r["종류"] == SURGERY_ONLY,
                        renewal=seg["갱신유형"])
            found, base = cell_gate_points(ctx, p)
            for y in found:
                pool.setdefault(y["포인트ID"], _export_point(ctx.data, y, texts))
            row.append({"라벨": x["라벨"], "보조": x["보조"], "닫힌사유": x["닫힌사유"], "회사": x["회사"],
                        "대표": x["대표"], "상대대표": x["상대대표"], "분류수": x["분류수"], "자료없음": x["자료없음"],
                        "열린종형": x["열린종형"], "관문기준": base, "관문포인트": [y["포인트ID"] for y in found],
                        "관문만수집": x["관문만수집"],
                        **{k: x[k] for k in PEER_TALLY}, **peer_codes(x["회사"], x["관문만수집"])})
        cells.append(row)
    labels = {lab: sum(1 for line in cells for x in line if x["라벨"] == lab) for lab in LABELS.values()}
    return {"성별": seg["성별"], "갱신유형": seg["갱신유형"], "행": seg["행"], "열": seg["열"], "칸": cells, "라벨별": labels}


def export(data: Data, analysis: dict | None = None, relations: Relations | None = None) -> dict[str, Any]:
    """시안이 읽는 JSON(합의안 11번). json.dumps에 그대로 넘길 수 있는 값만 담는다.

    - 포인트는 "포인트"(포인트ID → 포인트)에 한 번만 싣고, 종형별 목록과 지도 칸은 포인트ID로 가리킨다.
    - 포인트의 머리말과 회사수, 범위와 단정 주의 목록의 머리말은 "글" 목록의 번호다. 개정 검토 목록의 담보는 근거 대신
      포인트ID로 그 포인트의 근거를 가리킨다.
    - 종형별 값은 대표 조건(representative_profile. 이력 없음)으로 계산한다. 시사점에서 오는 포인트는 고객 조건과 무관하다.
    - 지도는 성별 남, 갱신 거르개 전체와 갱신과 비갱신 세 장이다. 칸의 관문 포인트는 그 칸의 맨 앞 나이로 계산한다(cell_gate_points).
      칸의 인사이트 수는 다섯 분류 이름의 분류수(관문 차이는 그 칸의 관문 포인트 수)이고, 안쪽 값인 분류와 수는 싣지 않는다.
      칸의 관문만수집은 열린 종형이 관문전용뿐인 상대 회사의 그 종형이다(cell). 칸의 열린종형과 관문만수집이 가리키는 종형은
      모두 "종형"에도 싣는다(관문전용 종형은 비교역할 관문전용). 칸의 상대 수(peer_tally) 옆에 그 기관코드 목록(peer_codes)을 싣는다.
    - 포인트의 관련기관코드는 비교종형ID가 속한 상대 회사의 기관코드다(compared_orgs). 기준별의 고지유형별은 notice_groups다.
    - 포인트의 관문만수집은 관문전용 종형을 적은 관문 포인트(G2, G3)에만 참으로 싣는다. 짝과 견준 G3에는 차이항목(SCOPE_ITEMS
      가운데 다른 것)을 싣는다.
    - 시장 소식의 요약은 보도를 옮긴 인용이다(news_summary의 인용, 출처표시, 주의표현, 인용안내).
    - "주석"은 지도와 관문 탭에 늘 붙이는 고정 주석(NOTES)이다. 항목마다 열쇠, 탭, 글, 출처다.
    """
    relations = load_relations() if relations is None else relations
    analysis = I.analyze(data, relations) if analysis is None else analysis
    ctx = _Ctx(data, analysis, relations)
    texts = _Texts()
    pool: dict[str, dict] = {}
    p = representative_profile(data)
    segs = {"전체": segment_map(data, "M", None, None, ctx=ctx), "갱신": segment_map(data, "M", "갱신", None, ctx=ctx),
            "비갱신": segment_map(data, "M", "비갱신", None, ctx=ctx)}
    rev, news = revision_summary(data), news_summary(data)
    by_base: dict[str, dict] = {}
    used: set[str] = set()
    for base in ctx.bases:
        pts = points(data, base, p, None, ctx=ctx)
        peers = pts["맞붙는종형"]
        used.update([base, *peers])
        cautions = caution(data, base, None, ctx=ctx, pts=pts)
        grid = journey(data, base, peers, ctx=ctx)
        for x in pts["포인트"]:
            pool.setdefault(x["포인트ID"], _export_point(data, x, texts))
        s = pts["범위"]
        by_base[base] = {
            "맞붙는종형": peers,
            "범위": {"상대": [{"종형ID": r["종형ID"], "머리말": texts.add(r["머리말"]), "구조다름": r["구조다름"]} for r in s["상대"]],
                   "회사수": s["회사수"], "머리말": texts.add(s["머리말"]), "비교쌍": s["비교쌍"], "뺀비교쌍": s["뺀비교쌍"],
                   "뺀시사점": s["뺀시사점"], "문장": s["문장"], "업권별": s["업권별"]},
            "관문": {k: v for k, v in pts["관문"].items() if k != "종형ID"},
            "포인트": [x["포인트ID"] for x in pts["포인트"]],
            "분류집계": pts["분류집계"], "세부집계": pts["집계"],
            "먼저": {"브리핑": [x["포인트ID"] for x in brief(pts)], "카드": [x["포인트ID"] for x in brief(pts, for_card=True)]},
            "뺀포인트": [{k: x.get(k) for k in ("분류", "세부", "표준담보ID", "비교종형ID", "사유")} for x in pts["뺀포인트"]],
            "단정주의": [{**c, "머리말": texts.add(c["머리말"]), "근거": _export_evidence(data, c["근거"])} for c in cautions],
            # 개정 검토 목록의 근거는 같은 포인트의 근거와 같아 포인트ID로만 가리킨다
            "개정검토": [{**g, "담보": [{k: v for k, v in d.items() if k != "근거"} for d in g["담보"]]}
                     for g in revision_candidates(data, pts)],
            "치료여정": grid,
            "고지유형별": notice_groups(data, base, peers),
            "보류요약": pending_summary(data, base, None, ctx=ctx, peers=peers),
            "브리핑": briefing(data, base, p, None, ctx=ctx, seg=segs["전체"], rev=rev, news=news, pts=pts,
                            cautions=cautions, grid=grid),
        }
    maps = {k: _export_map(ctx, seg, pool, texts) for k, seg in segs.items()}
    for m in maps.values():
        for line in m["칸"]:
            for x in line:
                used.update(v for v in [x["대표"], x["관문기준"], *x["상대대표"].values()] if v)
                # 칸이 가리키는 종형ID는 모두 "종형"에 싣는다. 정밀비교 종형 옆에서 함께 열린 관문전용 종형은
                # 대표나 관문만수집에 들지 않아도 열린종형에 있다
                used.update(v for ids in x["열린종형"].values() for v in ids)
                used.update(y["종형ID"] for y in x["관문만수집"])
    used.update(v for x in pool.values() for v in x["비교종형ID"])
    return {
        "형식": 1, "자료시각": data.meta.get("snapshot_at"), "고지": NOTICE,
        "기준조건": {"나이": p.age, "성별": p.sex, "이력": None},
        "탭": list(TABS), "분류": list(CATEGORIES), "카드분류차례": list(CARD_ORDER), "라벨": list(LABELS.values()),
        "목적": [dict(x) for x in PURPOSE_BASIS],
        "기준종형": [{"종형ID": b, "이름": _kind_name(data, b), "심사": data.variants[b].get("심사유형"),
                   "간편고지약칭": data.variants[b].get("간편고지약칭"), "갱신": data.variants[b].get("갱신유형"),
                   "환급": data.variants[b].get("환급유형")} for b in ctx.bases],
        "종형": {v: _variant_info(data, v) for v in data.variant_order if v in used},
        "표준담보": {sid: {"이름": s["표준담보명"], "대분류": s["보장대분류"], "중분류": s["보장중분류"], "급부유형": s.get("급부유형")}
                 for sid, s in sorted(data.std.items(), key=lambda kv: ctx.order.get(kv[0], len(ctx.order)))},
        "기준별": by_base,
        "지도": maps,
        "주석": [dict(x, 탭=list(x["탭"])) for x in NOTES],
        "한도표": limit_steps(data),
        "개정변동": rev,
        "시장소식": news,
        "포인트": pool,
        "글": texts.items,
    }


def to_json(value: Any) -> Any:
    """Profile을 dict로 바꿔 json.dumps에 넘길 수 있게 한다."""
    if isinstance(value, Profile):
        return asdict(value)
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    return value
