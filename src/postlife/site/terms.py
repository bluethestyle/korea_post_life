"""화면 용어(docs/proposals/용어_대조표.md)를 자료 쪽에서 한 곳에 모은다.

1. 사용자가 2026-11-24에 승인한 이름(USER_PICKS). 대조표의 사용자 확인 8행에 답한 것과, 영업 인사이트 분류 다섯을 담보 비교 탭의
   판정 용어(우위, 열위, 미보유)에 맞춰 대조표의 권고안(40, 120~123번)을 바꾼 것이다. 이 값이 대조표보다 우선한다. 이름이 바뀌면
   이 파일의 상수만 고친다. 1번(화면 제목), 8번(관계 그래프 탭), 128번(응대 화법)은 화면 코드만 쓰는 말이지만 화면 코드 요청서가
   같은 값을 쓰도록 여기에 함께 둔다.
2. 표시 이름 표(DISPLAY_GROUPS, GRAPH_DISPLAY_GROUPS). 화면 코드가 조건문, 아이콘 맵, CSS 클래스 맵, 탭 이동의 키로 쓰는 값은
   자료에서 바꾸지 않고(대조표 적용 계획 1-1), 화면에 보일 이름만 이 표로 준다. sales.json 과 graph.json 의 "표시명"에
   구분 없이 한 맵(값 → 표시 이름)으로 싣는다(display_names, graph_display_names). 서로 다른 구분에서 같은 값이 다른 이름을
   가져야 하는 경우가 없어 평면 맵으로 충분하다. 그런 값이 생기면 flat()이 멈춘다.
   구분 이름은 사람이 읽으려고 둔 것이고 자료에는 싣지 않는다(tests/test_display_names.py 가 1-1 의 값을 모두 덮는지 본다).

이 모듈은 다른 site 모듈을 읽지 않는다(sales, console4 가 이 모듈을 읽는다). 키 값은 sales.py, insights.py, console4.py,
validate.py 의 상수와 글자가 같아야 하고, 같은지는 시험이 본다.
"""
from __future__ import annotations

# ---------- 사용자가 승인한 이름(대조표 번호, 2026-11-24) ----------
SCREEN_TITLE = "상품 비교 분석"                 # 1번 영업 분석 콘솔(화면 제목). 화면 코드만 쓴다
TAB_SUMMARY = "요약"                            # 3번 브리핑(첫 탭)
TAB_UNDERWRITING = "인수기준 비교"              # 5번 가입 관문(탭)
TAB_GRAPH = "관계 그래프"                        # 8번 관계 지도(탭, 패널 제목). 화면 코드만 쓴다
SEGMENT_TABLE = "고객군별 가입 가능 현황"         # 9번 고객군 지도(10번 고객군 지형도 같은 말로 쓴다)
NO_SIMPLE_COMPARE = "단순 비교 불가"             # 83번 단정 주의, 우열을 매기지 않음, 우열 보류
TALK_SCRIPT = "응대 화법"                        # 128번 응대 카드. 화면 코드만 쓴다

# 영업 인사이트 분류 다섯(sales.CATEGORIES 의 값 → 화면 이름). 담보 비교 탭의 판정 용어(우위, 열위, 미보유)에 맞췄다.
# 분류 제목 자리에도 이 이름을 그대로 쓴다(짧은 표기 없음)
GATE_DIFF_NAME = "인수기준 차이"                 # 40번 관문 차이
STRENGTH = "우위 담보"                           # 120번 앞세울 강점(우체국 단독 보유 담보와 조건 우위 담보)
DEFEND_NAME = "열위 담보"                        # 121번 조건 열위 방어
REVISE_NAME = "미보유 담보"                      # 122번 개정 검토 후보(우체국에 없는 담보. 상품 개정 검토의 재료다)
RELATED_NAME = "관련 담보"                       # 123번 관련 담보 안내(104번 관계 담보와 같은 말)

# 5번과 함께 바뀌는 말: "가입 관문 계산 규칙"(주석의 출처). 탭 이름의 "비교"를 "산출 규칙"으로 바꾼 형식이다
UNDERWRITING_RULE = TAB_UNDERWRITING.removesuffix(" 비교") + " 산출 규칙"

USER_PICKS = {1: SCREEN_TITLE, 3: TAB_SUMMARY, 5: TAB_UNDERWRITING, 8: TAB_GRAPH, 9: SEGMENT_TABLE,
              40: GATE_DIFF_NAME, 83: NO_SIMPLE_COMPARE, 120: STRENGTH, 121: DEFEND_NAME, 122: REVISE_NAME,
              123: RELATED_NAME, 128: TALK_SCRIPT}

# 영업 인사이트 세부 여덟 가지(sales.DETAILS 의 코드 → 화면 이름. 용어 대조표 31, 49, 123~126). 코드(G1 따위)는 화면 코드가
# 분류마다 세부를 고르고 세는 키라 화면에 글자로 내지 않는다. 화면은 이 이름만 보인다
DETAIL_NAMES = {"G1": "우체국만 가입 가능", "G2": "우체국만 가입 제한", "G3": "고지 범위 상이",
                "A1": "단독 보유 담보", "A2": "조건 우위",
                "Q1": "관련 담보 있음", "Q2": "미보유", "Q3": "조건 열위"}

# ---------- 표시 이름 표(sales.json) ----------
# 구분마다 {자료의 값: 화면에 보일 이름}. 이름이 같은 값도 그 구분의 값을 빠짐없이 적는다(화면이 한 표로 찾게).
# 괄호 안 번호는 대조표의 행이다.
DISPLAY_GROUPS: dict[str, dict[str, str]] = {
    # sales.STATE_ORDER, sales.PARTIAL. gate.json 의 상태, 지도 칸의 회사 상태, 관문.상태(23, 25, 26, 62, 63)
    "가입 가능 상태": {"열림": "가입 가능", "나이 자료 없음": "가입나이 미수집", "질문 자료 없음": "고지항목 미수집",
                  "심사로 확인": "일반심사 대상", "닫힘": "가입 제한", "일부 나이만 열림": "일부 나이만 가입 가능"},
    # sales.LABELS. 지도 칸의 라벨, 라벨별(27~30)
    "현황 표 라벨": {"우리 간편만 열림": "우체국 간편만 가입 가능", "함께 열림": "함께 가입 가능",
                "우리 간편 닫힘": "우체국 간편 가입 제한", "간편 모두 닫힘": "간편 모두 가입 제한", "자료 없음": "자료 없음"},
    # sales.HOSPITAL, sales.SURGERY_ONLY. 지도 행의 종류. 행 이름의 머리말도 이 값이다(53)
    "현황 표 행 종류": {"입원": "입원", "수술만": "통원수술"},
    # insights.VERDICTS, insights.DIFF. 비교쌍과 조건 항목의 판정(78~80, 82, 86)
    "판정 값": {"같음": "동일", "나음": "우위", "못함": "열위", "엇갈림": "우열 혼재", "판정 보류": "판정 보류", "다름": "상이"},
    # console4.PAIR_KEYS 가운데 판정 값이 아닌 것. 쌍판정의 까닭, 판정기관코드와 판정상대수의 열쇠(80, 83, 88, 89, 105, 110)
    "판정 집계": {"단정 주의": NO_SIMPLE_COMPARE, "지급 형태 다름": "지급 형태 상이", "관계 담보로 덮음": "관련 담보로 보장",
              "검토 대기": "검수 대기", "우체국에 없음": "우체국 미보유", "상대에 없음": "타사 미보유"},
    # console4.NAME_ORDER. cover.json 의 판정표.판정, 판정차례, 판정요약의 열쇠(77, 79, 83, 86, 87, 88, 90, 110)
    "판정 이름": {"우체국 나음": "우체국 우위", "우체국 못함": "우체국 열위", "같음": "동일",
              "우열을 매기지 않음": NO_SIMPLE_COMPARE, "우체국에만 있음": "우체국 단독 보유", "우체국에 없음": "우체국 미보유",
              "검토 대기": "검수 대기", "판정 보류": "판정 보류", "둘 다 없음": "양사 미보유"},
    # sales.CATEGORIES. 분류, 카드분류차례, 분류집계와 분류수의 열쇠(40, 120~123. 사용자 승인 이름)
    "영업 인사이트 분류": {"관문 차이": GATE_DIFF_NAME, "앞세울 강점": STRENGTH, "관련 담보 안내": RELATED_NAME,
                   "조건 열위 방어": DEFEND_NAME, "개정 검토 후보": REVISE_NAME},
    # sales.CODES. 포인트와 뺀포인트의 세부, 세부집계의 열쇠. 포인트에는 같은 이름을 세부이름으로도 싣는다
    "영업 인사이트 세부": DETAIL_NAMES,
    # 시트 허용값(validate.py 의 비교역할구분). 종형.비교역할(34, 35)
    "비교역할": {"관문전용": "인수기준만 수집", "직전개정시연": "직전 개정 상품"},
    # sales.TABS. 탭, 브리핑의 갈곳, 주석의 탭(3, 5). 화면 코드가 탭 이름으로 탭을 찾고(core.js 의 TAB_BY_NAME), tab3.js 가
    # 주석을 "가입 관문" 글자로 고른다
    "탭": {"브리핑": TAB_SUMMARY, "고객군과 시장": "고객군과 시장", "가입 관문": TAB_UNDERWRITING, "담보 비교": "담보 비교",
          "영업 인사이트": "영업 인사이트"},
    # sales.REVISION_KINDS. 개정변동의 담보 종류와 짝의 열쇠(136)
    "개정 종류": {"신설": "신설", "변경": "변경", "종료": "삭제"},
}

# ---------- 표시 이름 표(graph.json) ----------
GRAPH_DISPLAY_GROUPS: dict[str, dict[str, str]] = {
    # 시트 허용값. summary.종형[].비교역할, 종형 노드(34, 35)
    "비교역할": {"관문전용": "인수기준만 수집", "직전개정시연": "직전 개정 상품"},
    # hum_담보매핑 검토상태 값 가운데 대조표에 있는 것. summary.종형[].미연결사유의 열쇠(116)
    "미연결사유": {"대상외": "매핑 대상 외"},
    # 속성 이름(graph.json 의 keys). 해당(매핑) 엣지의 속성(115)
    "속성 이름": {"검토상태": "검수 상태"},
}

# 관계 그래프의 노드 종류와 엣지 종류. build_data.py 는 안쪽 이름(왼쪽)으로 자료를 만들고, graph.json 의 kinds, ekinds 에는
# 화면 이름(오른쪽)을 싣는다(화면은 종류를 번호로 다룬다. 133, 148~151, 153)
GRAPH_NODE_KIND = {"보장분야": "보장 대분류", "소식": "시장 동향"}
GRAPH_EDGE_KIND = {"해당": "매핑", "속함": "분류", "관계": "담보 관계", "일으킴": "발표"}


def flat(groups: dict[str, dict[str, str]]) -> dict[str, str]:
    """구분을 지운 한 맵. 같은 값이 구분마다 다른 이름을 가지면 ValueError(평면 맵으로 싣지 못한다)."""
    out: dict[str, str] = {}
    for group, names in groups.items():
        for value, name in names.items():
            if out.get(value, name) != name:
                raise ValueError(f"표시 이름이 구분마다 다르다: {value} ({out[value]}, {group}의 {name})")
            out[value] = name
    return out


DISPLAY = flat(DISPLAY_GROUPS)
GRAPH_DISPLAY = flat(GRAPH_DISPLAY_GROUPS)


def display_names() -> dict[str, str]:
    """sales.json 의 "표시명"(새 사전이라 받은 쪽이 고쳐도 이 표는 그대로다)."""
    return dict(DISPLAY)


def graph_display_names() -> dict[str, str]:
    """graph.json 의 "표시명"."""
    return dict(GRAPH_DISPLAY)


def name(value: str) -> str:
    """값의 표시 이름(표에 없으면 값 그대로). 자료의 문장 틀이 키 값을 문장에 적을 때 쓴다."""
    return DISPLAY.get(value, value)
