"""시사점: 기준 종형(우체국)을 맞붙는 타사 종형과 견줘 규칙으로 뽑는 파생 값(온톨로지 설계안 2판 7절, 9절).

입력은 사본을 읽은 Data다. 비교표(compare.py)가 쓰는 것을 그대로 쓴다.
- 견줄 종형: 비교역할구분이 정밀비교인 종형. 기준 종형은 그 가운데 우리 기관(EPOST)이고 판매종료일이 빈 종형이다.
- 맞붙는 종형: compare.peers가 기준 종형마다 다른 회사에서 하나씩 고른 종형.
- 보유: compare.collect가 나눈 확정 급부의 표준담보. 매핑 검토 대기 급부(추천 표준담보가 있는 줄)는 따로 둔다.
- 대표 급부: compare.cell_core가 나이 조건 없이(Cond()) 고른 줄. 조건 우열은 두 대표 급부로 견준다. compare.pick_rep은 금액을
  모르면 조건이 엄격한 줄을 고르므로, 대표 밖에 조건이 다른 줄이 몇 줄인지 시사점에 함께 적는다(대표밖조건다른줄).
- 지급액 우열: compare.verdict의 부호를 그대로 옮긴다(새로 계산하지 않는다).
- 표준담보 관계: relations.py. 빈자리, 고유, 범위 차이를 가를 때 덮임(같은 담보, 넓은 담보, 부분 담보, 없음)을 쓴다.

조건 우열(가입 한도와 무관). 판정은 기준 종형 쪽에서 적는다(나음은 기준 종형의 조건이 낫다는 뜻).
- 면책: 면책기간일수가 작은 쪽이 낫다. 면책기간일수가 빈 줄은 비교표와 같이 0일로 본다(model.benefit_view).
- 감액: 감액이 없는 쪽이 낫다. 둘 다 있으면 경과 기간을 두 쪽의 감액 경계로 잘라 구간마다 지급률(감액이 끝나면 100%)을 견주고,
  모든 구간에서 높거나 같으면 낫고, 구간마다 엇갈리면 엇갈림이다. 구간이 하나씩이면 compare.compare_reduction과 같은 판정이다
  (기간이 짧고 지급률이 높으면 나음, 한쪽은 기간이 짧고 한쪽은 지급률이 높으면 엇갈림). 구간이 둘인 줄은 비교표가 첫 구간만 보지만,
  여기서는 구간마다 견줘 모은다. 어느 쪽이든 대표 급부의 감액예외에 글이 있으면(일부 경우에만 감액) 견주지 않고 판정 보류로 둔다.
- 지급 형태: 지급횟수제한 문구에 붙인 꼬리표(pay_tags)로 견준다. 꼬리표의 종류와 숫자가 모두 같으면 같음이다.
  한쪽이 최초 1회뿐이고 다른 쪽이 되풀이 지급(연간 N회, 회당)이면서 최초 1회가 없으면 되풀이 쪽이 낫다.
  나머지 짝은 다름으로만 두고 우열에 넣지 않는다. 문구가 비었거나 꼬리표를 읽지 못한 쪽이 있으면 견주지 않고 판정 보류로 둔다.
- 금액 없는 급부(model.benefit_view의 form. 지급기준구분이 차등지급, 실손보상, 분할지급, 현물급부)가 낀 짝(2026-11-23):
  보유로는 세지만 금액 하나로 견주지 않는다. 지급 형태는 한쪽만 금액 없는 값이거나 두 쪽 값이 다르면 다름(설계 차이), 두 쪽이 같은
  금액 없는 값이면 판정 보류다. 양쪽 글은 꼬리표 대신 지급 기준으로 적는다(금액 쪽 "정액 지급", 꼬리표가 있으면 "정액 지급(최초 1회)",
  금액 없는 쪽은 값 이름). 감액은 두 판독이 읽지 않은 칸이라 판정 보류다. 면책은 그대로 견주지만 감액이 보류라 종합은 판정 보류이고,
  조건 격차는 나오지 않는다. 지급액은 비교표 부호 x(금액 자료 없음)를 그대로 쓰고 사유만 "지급 형태가 달라 금액을 견주지 않음"이다.
- 모으기(combine): 모두 같음이면 같음, 나음만 있으면 나음, 못함만 있으면 못함, 섞이면(감액 엇갈림 포함) 엇갈림.
  판정 보류가 하나라도 있으면 판정 보류다. 나머지가 같음일 때는 물론이고, 나머지에 나음이나 못함이 있어도 보류한 항목이 판정을
  뒤집을 수 있으므로 보류로 둔다. 이때 보류한 항목을 뺀 나머지만 모은 판정은 보류밖판정에 적는다. 다름은 우열에 넣지 않는다.

시사점 유형
- 빈자리: 맞붙는 종형 가운데 둘 이상(GAP_MIN)이 가진 표준담보를 기준 종형이 갖지 않고, 넓은 담보나 부분 담보로도 덮이지 않는다.
- 범위 차이: 빈자리 조건인데 기준 종형이 넓은 담보나 부분 담보(일부만 가짐 포함)로 덮는다(방향 "기준에 없음"). 또는 기준 종형만
  그 담보를 가지는데 맞붙는 종형이 넓은 담보나 부분 담보로 덮는다(방향 "기준에만 있음"). 빈자리와 고유로 세지 않는다.
- 고유: 기준 종형이 가진 담보를 맞붙는 종형 어디도 같은 담보, 넓은 담보, 부분 담보로 갖지 않는다.
- 조건 격차: 같은 담보를 가진 맞붙는 종형과 견준 조건 우열이 못함 또는 나음. 방향마다 한 건이고 걸린 비교 종형을 모은다.
- 설계 차이: 같은 담보에서 지급 형태가 다름. 걸린 비교 종형을 모은다.

검토 대기 빼기. 대기는 '없음'이 아니라 '모름'으로 본다.
- 매핑 대기: hum_담보매핑 검토상태가 대기이고 추천 표준담보가 사전에 있는 급부(compare.collect의 두 번째 값).
  추천 표준담보가 없는 대기 급부는 어느 담보에 걸리는지 몰라 빼는 데 쓰지 않는다(종형별 수는 기준 종형 결과의 추천없는대기급부).
- 작업 로그 대기: sys_작업로그의 사람검토이관(Data.pending_benefit. extract/rerun.py의 waiting_rows와 같은 규칙).
- 보유를 따지는 유형(빈자리, 고유, 범위 차이)은 대기 급부가 판정을 바꿀 수 있으면 뺀다. 매핑 대기 급부를 추천 담보로 확정했다고
  쳤을 때 덮임이나 가진 회사 수가 달라지거나, 담보를 가진 쪽의 그 담보 급부가 모두 작업 로그 대기라 가진 회사 수가 모자라면 뺀다.
- 조건을 견주는 유형(조건 격차, 설계 차이)은 두 종형 가운데 한쪽이라도 그 담보에 매핑 대기 급부나 작업 로그 대기 급부가 있으면
  그 비교 종형을 뺀다. 걸린 비교 종형이 모두 빠지면 그 시사점을 뺀 것으로 센다.

우선순위 점수(score)
    점수 = 10 × 걸린 회사 수 + 분야 가중 + 유형 가중
    걸린 회사 수: 빈자리와 범위 차이(기준에 없음)는 그 담보를 가진 맞붙는 회사 수, 고유와 범위 차이(기준에만 있음)는 맞붙는 회사 수,
                  조건 격차와 설계 차이는 시사점에 든 비교 종형의 회사 수
    분야 가중: 보장대분류가 암보장, 뇌혈관보장, 심장보장, 뇌심장보장이면 5, 아니면 0
    유형 가중: 빈자리 4, 조건 격차(못함) 3, 고유 2, 조건 격차(나음) 2, 설계 차이 1, 범위 차이 0
점수가 같으면 유형 순서(빈자리, 조건 격차, 고유, 설계 차이, 범위 차이), 비교표의 담보 순서로 줄 세운다.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from . import compare as C
from . import screen as SC
from .model import Cond, Data, HOME_ORG
from .relations import NONE as COVER_NONE, SAME as COVER_SAME, Cover, Relations, load_relations

# ---------- 이름 ----------
GAP, CONDITION, UNIQUE, DESIGN, SCOPE = "빈자리", "조건 격차", "고유", "설계 차이", "범위 차이"
TYPES = (GAP, CONDITION, UNIQUE, DESIGN, SCOPE)
MISSING_SIDE, ONLY_SIDE = "기준에 없음", "기준에만 있음"     # 범위 차이의 방향

# 판정 값. 화면 코드가 이 글자로 분기하고 세므로(tab4.src.js) 값은 그대로 둔다. 화면에 보일 이름은 terms.DISPLAY_GROUPS 의
# "판정 값"이다(나음은 우위, 못함은 열위)
SAME, BETTER, WORSE, MIXED, HOLD, DIFF = "같음", "나음", "못함", "엇갈림", "판정 보류", "다름"
VERDICTS = (SAME, BETTER, WORSE, MIXED, HOLD)

# 판정 보류와 비교 제외의 사유 글(화면에 그대로 보인다. 용어 대조표 96, 163)
WAIT, REDUCTION, PAY = "면책", "감액", "지급 형태"
HOLD_EXCEPTION = "감액이 일부 경우에만 적용"
HOLD_NO_TEXT = "지급횟수제한 문구가 없어 비교하지 않음"
HOLD_UNREAD = "지급 형태 문구를 읽지 못해 비교하지 않음"
HOLD_NO_REP = "대표 급부를 선택할 수 없음"
HOLD_FORM_CUT = "지급 형태가 달라 감액을 비교하지 않음"
HOLD_SAME_FORM_CUT = "금액 하나로 담기지 않는 지급 형태라 감액을 비교하지 않음"
HOLD_SAME_FORM = "두 쪽이 같은 지급 형태(금액 하나로 담기지 않음)라 비교하지 않음"
AMOUNT_FORM = "지급 형태가 달라 금액을 비교하지 않음"
# 검수 대기 사유의 두 종류(Holding.blockers. 용어 대조표 111, 112). 사유 글은 "{종형 이름} {종류} {n}건"이다(pending_text)
PENDING_MAPPING, PENDING_EXTRACT = "매핑 검수 대기", "추출 검수 대기"
FLAT_PAY = "정액 지급"                    # 금액 없는 급부와 견줄 때 금액 급부 쪽의 지급 형태 글
CUT_IN_SOURCE = "원문 확인"               # 금액 없는 급부의 감액 글(감액을 읽지 않았다)

GAP_MIN = 2
FOCUS_MAJORS = {"암보장", "뇌혈관보장", "심장보장", "뇌심장보장"}
FIELD_WEIGHT = 5
COMPANY_WEIGHT = 10
TYPE_WEIGHT = {(GAP, None): 4, (CONDITION, WORSE): 3, (UNIQUE, None): 2, (CONDITION, BETTER): 2, (DESIGN, None): 1,
               (SCOPE, MISSING_SIDE): 0, (SCOPE, ONLY_SIDE): 0}

# ---------- 지급 형태 꼬리표 ----------
FIRST, ANNUAL, PER_EVENT, PER_DAY, CAP, STEP, UNREAD = "최초 1회", "연간 N회", "회당", "1일당", "한도 차감", "체증", "읽지 못함"
TAG_KINDS = (FIRST, ANNUAL, PER_EVENT, PER_DAY, CAP, STEP)
REPEAT_KINDS = {ANNUAL, PER_EVENT}

_FIRST = re.compile(r"최초\s*1\s*회")
_ANNUAL = re.compile(r"(?:연간|매년|(?<![가-힣])연)\s*(?:최대\s*)?(\d+)\s*회")
_YEARLY = re.compile(r"매년")
_PER_EVENT = re.compile(r"(수술|진단|사고|내원|통원|입원|치료|의료행위)?\s*1\s*회\s*당")
_PER_ACCIDENT = re.compile(r"사고(?:일자)?\s*당\s*1\s*회")
_PER_STAY = re.compile(r"1\s*회\s*(?:의\s*)?(입원|통원)\s*당")
_PER_DAY = re.compile(r"일\s*당|1\s*일\s*1\s*회|1\s*일\s*기준")
_DAY_CAP = re.compile(r"(\d+)\s*일\s*(?:을|를)?\s*(?:최고\s*)?한도")
_DAY_FROM = re.compile(r"(\d+)\s*일\s*(초과|이상)|(\d+)\s*일\s*째")
_AMOUNT_CAP = re.compile(r"(\d[\d,.]*\s*(?:억|천만|백만|만)?\s*원)\s*(?:을|를)?\s*한도")
_TOTAL_CAP = re.compile(r"연간\s*총\s*지급액|가입금액\s*한도")
_STEP = re.compile(r"체증|할증|가입\s*후\s*\d+\s*년\s*이상")


@dataclass(frozen=True)
class Tag:
    """지급 형태 꼬리표. key는 같고 다름을 가르는 값(종류와 숫자), label은 사람이 읽는 꼴이다."""
    kind: str
    key: tuple
    label: str


def _clean(text: Any) -> str:
    return " ".join(str(text or "").split())


def pay_tags(text: Any) -> tuple[Tag, ...]:
    """지급횟수제한 문구에서 읽은 지급 형태 꼬리표. 여럿 붙을 수 있다. 빈 문구는 빈 튜플, 읽지 못한 문구는 읽지 못함 꼬리표 하나.

    - 최초 1회: "최초 1회"(최초1회한, 최초 1회에 한함)
    - 연간 N회: "연간 N회", "연 N회", "매년 N회", "연간 최대 N회". 횟수 없이 "매년"만 있으면 "매년"(N 모름)
    - 회당: "수술 1회당", "진단 1회당", "1회당", "사고(일자)당 1회", 일수 한도가 없는 "1회 입원당"
    - 1일당: "1일당", "일당", "1일 1회", "1일 기준", 또는 일수 한도("120일 한도", "180일을 최고한도로"). 시작일("3일 초과",
      "4일 이상", "181일째")과 일수 한도를 숫자로 담는다. 1일째부터는 시작일 없음과 같게 본다
    - 한도 차감: 금액 한도("5천만원을 한도로", "500만원 한도"), "연간 총 지급액", "가입금액 한도". 연간이면 앞에 연간을 붙인다
    - 체증: "체증", "할증", "가입후 N년 이상"
    """
    s = _clean(text)
    if not s:
        return ()
    found: dict[tuple, Tag] = {}

    def add(kind: str, key: tuple, label: str) -> None:
        found.setdefault((kind, *key), Tag(kind, (kind, *key), label))

    if _FIRST.search(s):
        add(FIRST, (), "최초 1회")
    counts = sorted({int(m.group(1)) for m in _ANNUAL.finditer(s)})
    for n in counts:
        add(ANNUAL, (n,), f"연간 {n}회")
    if not counts and _YEARLY.search(s):
        add(ANNUAL, (None,), "매년")

    caps = sorted({int(m.group(1)) for m in _DAY_CAP.finditer(s)})
    events = [m.group(1) or "" for m in _PER_EVENT.finditer(s)] + ["사고" for _ in _PER_ACCIDENT.finditer(s)]
    if not caps:
        events += [m.group(1) for m in _PER_STAY.finditer(s)]
    if events:
        words = ", ".join(dict.fromkeys(e for e in events if e))
        add(PER_EVENT, (), f"{words} 1회당" if words else "1회당")
    if caps or _PER_DAY.search(s):
        start = None
        m = _DAY_FROM.search(s)
        if m:
            start = int(m.group(1)) + 1 if m.group(2) == "초과" else int(m.group(1) or m.group(3))
            start = start if start > 1 else None
        detail = ([f"{start}일째부터"] if start else []) + [f"{', '.join(map(str, caps))}일 한도"] * bool(caps)
        add(PER_DAY, (start, tuple(caps)), "1일당" + (f"({', '.join(detail)})" if detail else ""))

    amounts = tuple(dict.fromkeys("".join(m.group(1).replace(",", "").split()) for m in _AMOUNT_CAP.finditer(s)))
    if amounts or _TOTAL_CAP.search(s):
        yearly = "연간" in s
        add(CAP, (yearly, amounts), ("연간 " if yearly else "") + (f"{', '.join(amounts)} 한도" if amounts else "한도"))
    if _STEP.search(s):
        add(STEP, (), "체증")

    if not found:
        return (Tag(UNREAD, (UNREAD,), UNREAD),)
    return tuple(sorted(found.values(), key=lambda t: (TAG_KINDS.index(t.kind), str(t.key))))


def tag_text(tags: Iterable[Tag]) -> str:
    tags = list(tags)
    return " + ".join(t.label for t in tags) if tags else "문구 없음"


def _frequency(tags: tuple[Tag, ...]) -> str | None:
    kinds = {t.kind for t in tags}
    if kinds == {FIRST}:
        return "first"
    if kinds & REPEAT_KINDS and FIRST not in kinds:
        return "repeat"
    return None


# ---------- 조건 우열 ----------
def _num_text(x: float) -> str:
    x = float(x)
    return str(int(x)) if x.is_integer() else f"{x:g}"


def months_text(months: Any) -> str:
    m = float(months)
    if m.is_integer() and int(m) % 12 == 0:
        return f"{int(m) // 12}년"
    return f"{_num_text(m)}개월"


def reduction_text(segs: list) -> str:
    if not segs:
        return "감액 없음"
    return ", ".join(f"{months_text(m)} {_num_text(float(r) * 100)}%" for m, r in sorted((float(m), float(r)) for m, r in segs))


def _rate_at(segs: list[tuple[float, float]], t: float) -> float:
    for months, rate in segs:
        if t < months:
            return rate
    return 1.0


def compare_wait(base: Any, other: Any) -> str:
    """면책기간일수. 작은 쪽이 낫다. 판정은 기준(base) 쪽."""
    b, o = float(base or 0), float(other or 0)
    if abs(b - o) < 1e-9:
        return SAME
    return BETTER if b < o else WORSE


def compare_reduction(base: list, other: list) -> str:
    """감액 구간 목록([[개월, 지급률], ...]). 판정은 기준(base) 쪽. 모듈 설명의 감액 규칙."""
    b = sorted((float(m), float(r)) for m, r in base or [])
    o = sorted((float(m), float(r)) for m, r in other or [])
    if b == o:
        return SAME
    if not b:
        return BETTER
    if not o:
        return WORSE
    signs = set()
    for t in sorted({0.0} | {m for m, _ in b + o}):
        rb, ro = _rate_at(b, t), _rate_at(o, t)
        if abs(rb - ro) > 1e-9:
            signs.add(BETTER if rb > ro else WORSE)
    if not signs:
        return SAME
    return signs.pop() if len(signs) == 1 else MIXED


def form_text(form: str | None, limit_text: Any) -> str:
    """금액 없는 급부와 견줄 때 한쪽의 지급 형태 글. 금액 없는 쪽은 값 이름, 금액 쪽은 "정액 지급"(꼬리표가 있으면 괄호에)."""
    if form:
        return form
    tags = [t for t in pay_tags(limit_text) if t.kind != UNREAD]
    return f"{FLAT_PAY}({tag_text(tags)})" if tags else FLAT_PAY


def compare_pay(base_text: Any, other_text: Any, base_form: str | None = None,
                other_form: str | None = None) -> dict[str, Any]:
    """지급 형태. 판정은 기준 쪽(같음, 나음, 못함, 다름, 판정 보류).

    base_form, other_form은 금액 없는 급부의 지급기준구분(model.benefit_view의 form)이다. 어느 한쪽에 있으면 꼬리표로 견주지
    않는다: 두 쪽 값이 다르면(한쪽만 있는 경우 포함) 다름, 같으면 판정 보류다.
    """
    if base_form or other_form:
        out = {"항목": PAY, "기준": form_text(base_form, base_text), "상대": form_text(other_form, other_text), "사유": None}
        if base_form == other_form:
            return {**out, "판정": HOLD, "사유": HOLD_SAME_FORM}
        return {**out, "판정": DIFF}
    tb, to = pay_tags(base_text), pay_tags(other_text)
    out = {"항목": PAY, "기준": tag_text(tb), "상대": tag_text(to), "사유": None}
    if not tb or not to:
        return {**out, "판정": HOLD, "사유": HOLD_NO_TEXT}
    if any(t.kind == UNREAD for t in tb + to):
        return {**out, "판정": HOLD, "사유": HOLD_UNREAD}
    if {t.key for t in tb} == {t.key for t in to}:
        return {**out, "판정": SAME}
    fb, fo = _frequency(tb), _frequency(to)
    if {fb, fo} == {"first", "repeat"}:
        return {**out, "판정": BETTER if fb == "repeat" else WORSE}
    return {**out, "판정": DIFF}


def combine(results: Iterable[str]) -> str:
    """항목 판정을 모은다(모듈 설명의 모으기 규칙). 다름은 넣지 않는다."""
    results = list(results)
    if HOLD in results:
        return HOLD
    ranked = {r for r in results if r in (BETTER, WORSE, MIXED)}
    if not ranked:
        return SAME
    if ranked == {BETTER}:
        return BETTER
    if ranked == {WORSE}:
        return WORSE
    return MIXED


def condition_signature(view: dict[str, Any]) -> tuple:
    """조건 우열에 쓰는 값을 모은 열쇠. 두 줄의 열쇠가 같으면 면책, 감액, 감액예외 유무, 지급 형태 꼬리표, 금액 없는 꼴이 모두 같다.

    금액 없는 꼴(form)을 넣어, 한 칸에 금액 급부와 금액 없는 급부가 함께 있으면 금액 없는 급부가 "대표 밖에 조건이 다른 줄"로 세어진다.
    금액 급부에는 form이 없어 열쇠의 끝은 None이다.
    """
    return (float(view.get("wait") or 0), tuple(sorted((float(m), float(r)) for m, r in view.get("red") or [])),
            bool(view.get("exc")), frozenset(t.key for t in pay_tags(view.get("limit"))), view.get("form"))


def compare_conditions(base: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    """두 대표 급부(model.benefit_view의 꼴)의 조건 우열. 판정은 기준(base) 쪽."""
    wait = {"항목": WAIT, "기준": f"{_num_text(base['wait'] or 0)}일", "상대": f"{_num_text(other['wait'] or 0)}일",
            "판정": compare_wait(base["wait"], other["wait"]), "사유": None}
    bf, of = base.get("form"), other.get("form")
    red = {"항목": REDUCTION, "기준": CUT_IN_SOURCE if bf else reduction_text(base["red"]),
           "상대": CUT_IN_SOURCE if of else reduction_text(other["red"]), "사유": None}
    if bf or of:              # 금액 없는 급부의 감액 칸은 비어 있지만 "감액 없음"이 아니다(읽지 않았다)
        red.update({"판정": HOLD, "사유": HOLD_SAME_FORM_CUT if bf == of else HOLD_FORM_CUT})
    elif base.get("exc") or other.get("exc"):
        red.update({"판정": HOLD, "사유": HOLD_EXCEPTION})
    else:
        red["판정"] = compare_reduction(base["red"], other["red"])
    pay = compare_pay(base.get("limit"), other.get("limit"), bf, of)
    items = [wait, red, pay]
    overall = combine(i["판정"] for i in items)
    rest = combine(i["판정"] for i in items if i["판정"] != HOLD) if overall == HOLD else None
    return {"판정": overall, "보류밖판정": rest, "지급형태": pay["판정"], "항목": items}


AMOUNT_REASON = {"x": "금액 자료 없음", "p": "검수 대기 값이 있어 비교 결과를 보류함", "q": "매핑 검수 대기 급부만 있음",
                 "u": "타사 종형이 이 나이에 가입할 수 없음", "v": "기준 종형이 이 나이에 가입할 수 없음",
                 "n": "타사 종형에 없음", "o": "기준 종형에 없음", "": "양사 미보유"}


def amount_verdict(code: str) -> dict[str, Any]:
    """compare.verdict 부호(상대 쪽)를 기준 쪽 지급액 판정으로 옮긴다. 다섯 글자 부호의 둘째 글자가 지급액이다."""
    if len(code) == 5:
        return {"비교표부호": code, "지급액": {"+": WORSE, "-": BETTER, "=": SAME}[code[1]], "사유": None}
    return {"비교표부호": code, "지급액": None, "사유": AMOUNT_REASON.get(code, code)}


# ---------- 보유 ----------
def variant_label(data: Data, vid: str) -> str:
    """사유 글에 적는 종형 이름: "한화생명 간편가입형(1년)"(회사 이름과 종형명. sales 의 _peer_name 과 같은 꼴)."""
    v = data.variants.get(vid) or {}
    return f"{data.org_name(v.get('기관코드'))} {v.get('종형명') or vid}"


def pending_text(data: Data, vid: str, kind: str, n: int) -> str:
    """검수 대기 사유 글: "한화생명 간편가입형(1년) 추출 검수 대기 6건". kind 는 PENDING_MAPPING 이나 PENDING_EXTRACT 다."""
    return f"{variant_label(data, vid)} {kind} {n}건"


class Holding:
    """한 종형의 표준담보별 급부. compare.collect를 그대로 쓴다."""

    def __init__(self, data: Data, vid: str):
        self.data, self.vid = data, vid
        self.confirmed, self.waiting, self.loose = C.collect(data, vid)
        self.has = set(self.confirmed)
        self.possible = self.has | set(self.waiting)
        self.certain = {s for s, views in self.confirmed.items() if any(v["id"] not in data.pending_benefit for v in views)}
        self._cores: dict[str, dict] = {}

    def core(self, sid: str) -> dict[str, Any]:
        if sid not in self._cores:
            self._cores[sid] = C.cell_core(self.data, self.confirmed.get(sid, []), Cond(), bool(self.waiting.get(sid)))
        return self._cores[sid]

    def rep(self, sid: str) -> dict[str, Any] | None:
        core = self.core(sid)
        return self.confirmed[sid][core["rep"]] if core.get("kind") == "ok" else None

    def rep_ids(self, sids: Iterable[str]) -> list[str]:
        return [r["id"] for r in (self.rep(s) for s in sids if s in self.confirmed) if r]

    def blockers(self, sid: str) -> list[str]:
        """이 담보의 비교를 뺄 사유. 매핑 검수 대기 급부(표준담보 매핑을 담당자가 확인하지 않음)와 추출 검수 대기 급부(작업
        로그의 사람검토이관). 사유 앞에 종형 이름을 붙인다(pending_text)."""
        out = []
        if self.waiting.get(sid):
            out.append(pending_text(self.data, self.vid, PENDING_MAPPING, len(self.waiting[sid])))
        logs = [v for v in self.confirmed.get(sid, []) if v["id"] in self.data.pending_benefit]
        if logs:
            out.append(pending_text(self.data, self.vid, PENDING_EXTRACT, len(logs)))
        return out

    def other_lines(self, sid: str, rep: dict[str, Any] | None) -> int:
        """대표 급부 밖에 조건(면책, 감액, 감액예외 유무, 지급 형태 꼬리표)이 대표와 다른 확정 급부 수. 판정에는 쓰지 않고 적기만 한다.

        compare.pick_rep은 금액을 모를 때 조건이 엄격한 줄을 대표로 고르므로, 상대 종형에 조건이 더 나은 다른 줄이 있을 수 있다.
        """
        return len(self.other_line_ids(sid, rep))

    def other_line_ids(self, sid: str, rep: dict[str, Any] | None) -> list[str]:
        """other_lines가 세는 급부의 급부ID. 영업 인사이트의 단정 주의 목록이 근거 쪽을 적을 때 쓴다."""
        if rep is None:
            return []
        sig = condition_signature(rep)
        return [v["id"] for v in self.confirmed.get(sid, []) if v["id"] != rep["id"] and condition_signature(v) != sig]


GENERAL_MAJOR = "공통보장"
COMBINED_MAJOR, COMBINED_PARTS = "뇌심장보장", ("뇌혈관보장", "심장보장")
FOCUS_KIND = re.compile(r"\[([^\[\]]+?)보장형\]")      # 종형명의 보장형 표기("[암보장형]")


def coverage_scope(data: Data, vid: str, holding: "Holding | None" = None) -> list[str] | None:
    """보장 범위 한정 종형의 비교 범위(보장대분류 목록, compare.GROUP_ORDER 차례). 종합형이면 None.

    종형명에 "[…보장형]"(공시 종형명의 보장형 표기)이 있고, 종형이 가진 표준담보(Holding.possible: 확정과 추천이 있는 매핑 대기)의 보장대분류에 공통보장이 없으면 범위 한정 종형이다.
    뇌혈관보장이나 심장보장이 있으면 둘을 함께 보장하는 뇌심장보장도 범위에 넣는다. 가진 표준담보가 없으면 None 이다."""
    if not FOCUS_KIND.search(str(data.variants[vid].get("종형명") or "")):
        return None
    h = holding if holding is not None else Holding(data, vid)
    majors = {data.std[s]["보장대분류"] for s in h.possible if s in data.std}
    if not majors or GENERAL_MAJOR in majors:
        return None
    if majors & set(COMBINED_PARTS):
        majors.add(COMBINED_MAJOR)
    return [m for m in C.GROUP_ORDER if m in majors] + sorted(m for m in majors if m not in C.GROUP_ORDER)


def _cover_key(c: Cover) -> tuple:
    return (c.kind, c.partial)


# ---------- 시사점 ----------
def score(kind: str, direction: str | None, companies: int, major: str) -> int:
    """우선순위 점수. 식은 모듈 설명에 있다."""
    return (COMPANY_WEIGHT * companies + (FIELD_WEIGHT if major in FOCUS_MAJORS else 0)
            + TYPE_WEIGHT.get((kind, direction if kind in (CONDITION, SCOPE) else None), 0))


def std_order(data: Data) -> dict[str, int]:
    """비교표(compare.build)와 같은 담보 순서. 대분류 순서, 중분류, 표준담보ID."""
    majors = C.GROUP_ORDER + [m for m in dict.fromkeys(s["보장대분류"] for s in data.std.values()) if m not in C.GROUP_ORDER]
    ranked = sorted(data.std.values(), key=lambda s: (majors.index(s["보장대분류"]), str(s["보장중분류"]), str(s["표준담보ID"])))
    return {s["표준담보ID"]: i for i, s in enumerate(ranked)}


class _Base:
    """기준 종형 하나와 맞붙는 종형을 견준다."""

    def __init__(self, data: Data, relations: Relations, base: str, peers: list[str], hold: dict[str, Holding],
                 order: dict[str, int]):
        self.data, self.rel, self.base, self.peers, self.order = data, relations, base, peers, order
        self.B = hold[base]
        self.P = [hold[p] for p in peers]
        self.insights: list[dict] = []
        self.dropped: list[dict] = []
        self.pairs = 0
        self.pair_list: list[dict] = []
        self.dropped_pairs: list[dict] = []
        self.held_pairs: list[dict] = []
        self.spread = {p: Counter() for p in peers}
        self.scope = coverage_scope(data, base, self.B)

    # ---- 이름 ----
    def org(self, vid: str) -> str:
        return self.data.org_name(self.data.variants[vid].get("기관코드"))

    def std_name(self, sid: str) -> str:
        s = self.data.std.get(sid)
        return s["표준담보명"] if s else sid

    def names(self, sids: Iterable[str]) -> list[str]:
        return [self.std_name(s) for s in sids]

    def sort_key(self, sid: str) -> tuple:
        return (self.order.get(sid, len(self.order)), sid)

    # ---- 만들기 ----
    def make(self, kind: str, direction: str | None, sid: str, peers: list[str], items: list[dict], evidence: dict,
             extra: dict, amounts: dict | None = None, removed: list[dict] | None = None) -> dict:
        s = self.data.std[sid]
        v = self.data.variants[self.base]
        orgs = list(dict.fromkeys(self.data.variants[p].get("기관코드") for p in peers))
        n = len(orgs)
        key = f"{kind}|{direction or ''}|{self.base}|{sid}"
        out = {
            "시사점ID": "INS_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12],
            "유형": kind, "방향": direction,
            "표준담보ID": sid, "표준담보명": s["표준담보명"], "보장대분류": s["보장대분류"], "보장중분류": s["보장중분류"],
            "급부유형": s["급부유형"],
            "기준종형ID": self.base, "비교종형ID": list(peers),
            "항목": items, "근거": evidence,
            "점수": score(kind, direction, n, s["보장대분류"]),
            "변수": {"담보": s["표준담보명"], "대분류": s["보장대분류"], "중분류": s["보장중분류"],
                   "기준회사": self.org(self.base), "기준종형": v.get("종형명"), "기준상품": v.get("공시상품명"),
                   "상대회사": [self.data.org_name(o) for o in orgs], "상대수": n, **extra},
        }
        if amounts is not None:
            out["지급액"] = amounts
        if removed:
            out["뺀비교종형"] = removed
        return out

    def drop(self, kind: str, direction: str | None, sid: str, peers: list[str], reasons: list[str]) -> None:
        self.dropped.append({"유형": kind, "방향": direction, "표준담보ID": sid, "표준담보명": self.std_name(sid),
                             "비교종형ID": list(peers), "사유": reasons})

    def cover_item(self, vid: str, c: Cover) -> dict[str, Any]:
        return {"종형ID": vid, "덮임": c.kind, "덮는담보": self.names(c.via), "일부만": c.partial,
                "빠진부분담보": self.names(c.missing), "좁은담보": self.names(c.narrower)}

    # ---- 기준 종형에 없는 담보: 빈자리, 범위 차이(기준에 없음) ----
    def missing_side(self) -> None:
        B = self.B
        for sid in sorted({s for h in self.P for s in h.possible} - B.has, key=self.sort_key):
            if sid not in self.data.std:
                continue
            if self.scope is not None and self.data.std[sid]["보장대분류"] not in self.scope:
                continue
            holders = [h for h in self.P if sid in h.has]
            maybe = [h for h in self.P if sid in h.possible]
            if len(maybe) < GAP_MIN:
                continue
            cov = self.rel.cover(sid, B.has)
            kind, direction = (GAP, None) if cov.kind == COVER_NONE else (SCOPE, MISSING_SIDE)
            sure = [h for h in holders if sid in h.certain]
            reasons = []
            if _cover_key(self.rel.cover(sid, B.possible)) != _cover_key(cov):
                reasons.append(f"기준 종형에 이 담보를 보장할 수 있는 {PENDING_MAPPING} 급부가 있음")
            if len(holders) < GAP_MIN:
                reasons.append(f"보유 회사 수가 {PENDING_MAPPING} 급부에 달려 있음")
            elif len(sure) < GAP_MIN:
                reasons.append(f"보유한 쪽의 이 담보 급부가 모두 {PENDING_EXTRACT}")
            if reasons:
                self.drop(kind, direction, sid, [h.vid for h in maybe], reasons)
                continue
            peers = [h.vid for h in sure]
            evidence = {"기준": B.rep_ids(cov.via if cov.held else cov.narrower),
                        "비교": {h.vid: h.rep_ids([sid]) for h in sure}}
            items = [self.cover_item(self.base, cov)]
            extra = {"가진회사": [self.org(p) for p in peers]}
            if kind == SCOPE:
                extra.update({"방향": direction, "덮임": cov.kind, "덮는담보": self.names(cov.via), "일부만": cov.partial,
                              "빠진부분담보": self.names(cov.missing)})
            else:
                extra["기준좁은담보"] = self.names(cov.narrower)
            self.insights.append(self.make(kind, direction, sid, peers, items, evidence, extra))

    # ---- 기준 종형이 가진 담보: 고유, 범위 차이(기준에만 있음), 조건 격차, 설계 차이 ----
    def held_side(self) -> None:
        B = self.B
        if not self.P:
            return
        for sid in sorted(B.has, key=self.sort_key):
            covs = {h.vid: self.rel.cover(sid, h.has) for h in self.P}
            same = [h for h in self.P if covs[h.vid].kind == COVER_SAME]
            if same:
                self.common(sid, same)
                continue
            kind, direction = (UNIQUE, None) if not any(c.held for c in covs.values()) else (SCOPE, ONLY_SIDE)
            reasons = []
            if any(_cover_key(self.rel.cover(sid, h.possible)) != _cover_key(covs[h.vid]) for h in self.P):
                reasons.append(f"비교 대상 종형에 이 담보를 보장할 수 있는 {PENDING_MAPPING} 급부가 있음")
            if sid not in B.certain:
                reasons.append(f"기준 종형의 이 담보 급부가 모두 {PENDING_EXTRACT}")
            peers = [h.vid for h in self.P]
            if reasons:
                self.drop(kind, direction, sid, peers, reasons)
                continue
            items = [self.cover_item(h.vid, covs[h.vid]) for h in self.P]
            evidence = {"기준": B.rep_ids([sid]),
                        "비교": {h.vid: h.rep_ids(covs[h.vid].via) for h in self.P if covs[h.vid].held}}
            if kind == UNIQUE:
                extra = {"없는회사": [self.org(p) for p in peers]}
            else:
                extra = {"방향": direction,
                         "덮는회사": [self.org(h.vid) for h in self.P if covs[h.vid].held],
                         "덮는담보": {self.org(h.vid): self.names(covs[h.vid].via) for h in self.P if covs[h.vid].held}}
            self.insights.append(self.make(kind, direction, sid, peers, items, evidence, extra))

    def common(self, sid: str, same: list[Holding]) -> None:
        B = self.B
        rows = []
        for h in same:
            self.pairs += 1
            rb, ro = B.rep(sid), h.rep(sid)
            if rb is None or ro is None:
                res = {"판정": HOLD, "보류밖판정": None, "지급형태": HOLD,
                       "항목": [{"항목": "대표 급부", "기준": None, "상대": None, "판정": HOLD, "사유": HOLD_NO_REP}]}
            else:
                res = compare_conditions(rb, ro)
            amount = amount_verdict(C.verdict(h.core(sid), B.core(sid)))
            if amount["비교표부호"] == "x" and ((rb and rb.get("form")) or (ro and ro.get("form"))):
                amount = {**amount, "사유": AMOUNT_FORM}
            blocked = B.blockers(sid) + h.blockers(sid)
            row = {"종형ID": h.vid, "res": res, "amount": amount, "blocked": blocked,
                   "ids": (rb["id"] if rb else None, ro["id"] if ro else None),
                   "others": {"기준": B.other_lines(sid, rb), "상대": h.other_lines(sid, ro)}}
            rows.append(row)
            pair = {"표준담보ID": sid, "표준담보명": self.std_name(sid), "비교종형ID": h.vid, "판정": res["판정"],
                    "보류밖판정": res["보류밖판정"], "지급형태": res["지급형태"]}
            self.pair_list.append({**pair, "뺌": bool(blocked)})
            if blocked:
                self.dropped_pairs.append({**pair, "사유": blocked})
            else:
                self.spread[h.vid][res["판정"]] += 1
                if res["판정"] == HOLD:
                    self.held_pairs.append({**pair, "사유": [f"{i['항목']}: {i['사유']}" for i in res["항목"] if i["판정"] == HOLD],
                                            "항목": res["항목"]})

        def emit(kind: str, direction: str | None, hit: list[dict]) -> None:
            if not hit:
                return
            kept = [r for r in hit if not r["blocked"]]
            removed = [{"종형ID": r["종형ID"], "사유": r["blocked"]} for r in hit if r["blocked"]]
            if not kept:
                self.drop(kind, direction, sid, [r["종형ID"] for r in hit], list(dict.fromkeys(x for r in hit for x in r["blocked"])))
                return
            peers = [r["종형ID"] for r in kept]
            if kind == CONDITION:
                items = [{"종형ID": r["종형ID"], **i} for r in kept for i in r["res"]["항목"] if i["판정"] != SAME]
                extra = {"방향": direction,
                         "차이": {self.org(r["종형ID"]): [f"{i['항목']} {i['기준']} 대 {i['상대']}"
                                                         for i in r["res"]["항목"] if i["판정"] != SAME] for r in kept}}
            else:
                items = [{"종형ID": r["종형ID"], **i} for r in kept for i in r["res"]["항목"] if i["항목"] == PAY]
                pay = next(i for i in kept[0]["res"]["항목"] if i["항목"] == PAY)
                extra = {"기준지급형태": pay["기준"],
                         "상대지급형태": {self.org(r["종형ID"]): next(i["상대"] for i in r["res"]["항목"] if i["항목"] == PAY)
                                     for r in kept}}
            evidence = {"기준": [kept[0]["ids"][0]] if kept[0]["ids"][0] else [],
                        "비교": {r["종형ID"]: [r["ids"][1]] if r["ids"][1] else [] for r in kept}}
            amounts = {r["종형ID"]: r["amount"] for r in kept}
            ins = self.make(kind, direction, sid, peers, items, evidence, extra, amounts, removed)
            ins["대표밖조건다른줄"] = {r["종형ID"]: r["others"] for r in kept}
            self.insights.append(ins)

        for direction in (WORSE, BETTER):
            emit(CONDITION, direction, [r for r in rows if r["res"]["판정"] == direction])
        emit(DESIGN, None, [r for r in rows if r["res"]["지급형태"] == DIFF])

    def run(self) -> dict[str, Any]:
        self.missing_side()
        self.held_side()
        type_rank = {t: i for i, t in enumerate(TYPES)}
        self.insights.sort(key=lambda x: (-x["점수"], type_rank[x["유형"]], self.sort_key(x["표준담보ID"]), str(x["방향"])))
        v = self.data.variants[self.base]
        kept = Counter(x["유형"] for x in self.insights)
        dropped = Counter(x["유형"] for x in self.dropped)
        return {
            "종형ID": self.base, "회사": self.org(self.base), "공시상품명": v.get("공시상품명"), "종형명": v.get("종형명"),
            "심사유형": v.get("심사유형"), "간편고지약칭": v.get("간편고지약칭"), "보장범위": self.scope,
            "맞붙는종형": [{"종형ID": p, "회사": self.org(p), "공시상품명": self.data.variants[p].get("공시상품명"),
                        "종형명": self.data.variants[p].get("종형명"), "심사유형": self.data.variants[p].get("심사유형"),
                        "간편고지약칭": self.data.variants[p].get("간편고지약칭")} for p in self.peers],
            "보유담보수": {vid: len(h.has) for vid, h in [(self.base, self.B)] + [(h.vid, h) for h in self.P]},
            "추천없는대기급부": {vid: len(h.loose) for vid, h in [(self.base, self.B)] + [(h.vid, h) for h in self.P]},
            "유형별": {t: kept.get(t, 0) for t in TYPES},
            "뺀수": {t: dropped.get(t, 0) for t in TYPES},
            "비교쌍": self.pairs, "뺀비교쌍": len(self.dropped_pairs), "비교쌍목록": self.pair_list,
            "조건우열분포": {p: {k: self.spread[p].get(k, 0) for k in VERDICTS} for p in self.peers},
            "시사점": self.insights, "뺀시사점": self.dropped, "뺀비교": self.dropped_pairs, "보류비교": self.held_pairs,
        }


def base_variants(data: Data) -> tuple[list[str], list[str]]:
    """(견줄 종형, 기준 종형). 견줄 종형은 정밀비교 종형에서 화면 비교에서 빼는 상품(screen.EXCLUDED_PRODUCTS)의 종형을 뺀 것이고,
    기준 종형은 그 가운데 판매 중인 우리 기관 종형이다. 초기 버전 화면(compare.build)은 이 함수를 쓰지 않는다."""
    vids = [v for v in data.variant_order if data.variants[v].get("비교역할구분") == C.COMPARE_ROLE
            and not SC.excluded(data, v)]
    bases = [v for v in vids if data.variants[v].get("기관코드") == HOME_ORG
             and data.variants[v].get("판매종료일") in (None, "")]
    return vids, bases


def order_bases(data: Data, bases: list[str], hold: dict[str, Holding] | None = None) -> list[str]:
    """기준 종형의 화면 차례. 맨 앞은 화면이 처음 여는 기준 종형(종합형 가운데 screen.default_base), 그다음 같은 상품(모상품ID)의
    다른 종합형, 그다음 다른 종합형 상품, 끝에 보장 범위 한정 종형(coverage_scope)이다. 묶음 안은 bases 차례다.
    종합형이 없으면 bases 차례 그대로다. 화면 JS 는 목록의 첫 항목을 기본값으로 쓴다."""
    hold = {} if hold is None else hold
    for b in bases:
        if b not in hold:
            hold[b] = Holding(data, b)
    limited = [b for b in bases if coverage_scope(data, b, hold[b]) is not None]
    wide = [b for b in bases if b not in limited]
    if not wide:
        return list(bases)
    first = SC.default_base(data, wide)
    same = [b for b in wide if b != first and SC.product_of(data, b) == SC.product_of(data, first)]
    return [first] + same + [b for b in wide if b != first and b not in same] + limited


def org_of_benefit(data: Data, bid: str) -> str | None:
    rider = data.riders.get(data.benefits[bid].get("특약ID"))
    variant = data.variants.get(rider["종형ID"]) if rider else None
    return variant.get("기관코드") if variant else None


def pay_tag_stats(data: Data) -> dict[str, dict[str, Any]]:
    """회사별 지급 형태 꼬리표가 붙는 비율. sys_급부의 모든 줄을 센다(종형마다 되풀이되는 줄도 따로 센다)."""
    out: dict[str, dict[str, Any]] = {}
    texts: dict[str, dict[str, bool]] = {}
    for bid, b in data.benefits.items():
        org = org_of_benefit(data, bid) or "?"
        st = out.setdefault(org, {"급부": 0, "문구있음": 0, "꼬리표붙음": 0, "읽지못함": 0, "종류별": Counter()})
        st["급부"] += 1
        tags = pay_tags(b.get("지급횟수제한"))
        if not tags:
            continue
        st["문구있음"] += 1
        read = tags[0].kind != UNREAD
        st["꼬리표붙음" if read else "읽지못함"] += 1
        for t in tags:
            if t.kind != UNREAD:
                st["종류별"][t.kind] += 1
        texts.setdefault(org, {})[_clean(b.get("지급횟수제한"))] = read
    for org, st in out.items():
        seen = texts.get(org, {})
        st["비율"] = round(st["꼬리표붙음"] / st["문구있음"], 4) if st["문구있음"] else None
        st["서로다른문구"] = len(seen)
        st["꼬리표붙은서로다른문구"] = sum(seen.values())
        st["종류별"] = {k: st["종류별"].get(k, 0) for k in TAG_KINDS}
        st["회사"] = data.org_name(org)
    return dict(sorted(out.items(), key=lambda kv: (kv[0] != HOME_ORG, kv[0])))


def analyze_pair(data: Data, base: str, peers: Iterable[str], relations: Relations | None = None,
                 hold: dict[str, Holding] | None = None) -> dict[str, Any]:
    """기준 종형 하나를 고른 맞붙는 종형(peers)과 견준 결과. analyze()의 "기준" 한 줄과 같은 꼴이다.

    compare.peers가 고른 짝이 아닌 종형과 견줄 때 쓴다(영업 인사이트의 고객군 지도에서 칸마다 열린 종형끼리 견줄 때).
    hold는 종형별 보유(Holding)를 여러 번 부를 때 다시 만들지 않게 넘기는 저장소다.
    """
    relations = load_relations() if relations is None else relations
    hold = {} if hold is None else hold
    peers = [p for p in peers if p != base]
    for vid in [base] + peers:
        if vid not in hold:
            hold[vid] = Holding(data, vid)
    return _Base(data, relations, base, peers, hold, std_order(data)).run()


def analyze(data: Data, relations: Relations | None = None, base_ids: Iterable[str] | None = None) -> dict[str, Any]:
    """기준 종형별 시사점 목록과 요약 수치.

    relations를 주지 않으면 data/seed/표준담보_관계.jsonl을 읽는다. base_ids를 주면 그 기준 종형만 본다.
    """
    relations = load_relations() if relations is None else relations
    vids, bases = base_variants(data)
    if base_ids is not None:
        wanted = set(base_ids)
        bases = [b for b in bases if b in wanted]
    order = std_order(data)
    hold: dict[str, Holding] = {}
    results = []
    for b in bases:
        peers = [p for p in C.peers(data, b, vids) if p != b]
        for vid in [b] + peers:
            if vid not in hold:
                hold[vid] = Holding(data, vid)
        results.append(_Base(data, relations, b, peers, hold, order).run())
    kept = Counter(t for r in results for t, n in r["유형별"].items() for _ in range(n))
    dropped = Counter(t for r in results for t, n in r["뺀수"].items() for _ in range(n))
    return {
        "자료시각": data.meta.get("snapshot_at"),
        "담보관계수": len(relations),
        "담보관계확인": relations.check(data.std.values()),
        "기준": results,
        "요약": {
            "기준종형수": len(results),
            "시사점수": sum(kept.values()),
            "유형별": {t: kept.get(t, 0) for t in TYPES},
            "뺀수": {t: dropped.get(t, 0) for t in TYPES},
            "비교쌍": sum(r["비교쌍"] for r in results),
            "뺀비교쌍": sum(r["뺀비교쌍"] for r in results),
            "지급형태꼬리표": pay_tag_stats(data),
        },
    }
