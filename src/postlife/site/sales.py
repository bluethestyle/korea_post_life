"""영업 인사이트: 가입 관문과 고객군 지도, 응대 포인트(docs/proposals/영업_인사이트_흐름.md 4절).

공개 자료(상품요약서, 사업방법서)에서 계산되는 것만 다룬다. 판매 시책, 수수료, 손해율, 실적, 인수 판정은 다루지 않는다.
시사점 판정(insights.analyze)은 다시 계산하지 않고 거르고 문장으로 옮기기만 한다. 검토 대기는 "없음"이 아니라 "모름"이다.

고객 조건(Profile)
- since: 마지막 입원이나 수술이 몇 년 전보다 오래됐나(0.25는 3개월). None은 이력 없음.
- surgery_only: 그 이력이 입원 없이 수술만인가. renewal: 갱신유형 거르개(None은 전체).
- 최근 3개월 소견과 5년 안 중대질병 문항은 세 회사가 같은 기간이라 입력으로 받지 않고, 문장에 전제로 붙인다.

가입 관문(question_hit, gate)
- 간편심사 종형: 이력이 없으면 해당 없음. 수술만이고 기간 질문이 수술을 묻지 않으면(고지수술포함여부 거짓) 해당 없음.
  그 밖에는 since가 고지입원수술년수 이상이면 해당 없음, 아니면 해당. 열이 비었으면 자료 없음.
- 일반심사 종형: 이력이 없거나 since가 GENERAL_CLEAR_YEARS(5년) 이상이면 해당 없음, 아니면 심사로 확인.
- 종형 상태: 질문 해당이나 나이 불가는 닫힘, 질문 자료 없음, 심사로 확인, 나이 자료 없음(질문 해당 없음이고 가입나이 자료가
  없음), 열림. 회사 상태는 종형 상태 가운데 STATE_ORDER로 앞선 것이다.

고객군 지도(classify, cell, segment_map)
- 칸 분류는 우리 상태(U)와 "자료 있는 상대"(열림이나 닫힘. 심사로 확인은 닫힘으로 센다)로 가른다. 관문 상태이지 우열이 아니다.
- 칸의 숫자는 우리 대표 종형과 상대 대표 종형을 견준 시사점에서 센다(고유, 빈자리, 조건 못함, 조건 나음, 검토 대기로 뺀 수).
  상대 대표가 compare.peers의 짝과 다르면 insights.analyze_pair로 그 쌍을 다시 돌린다.

응대 포인트(points, render, scope)
- 세부 여덟 가지(DETAILS). 문장은 TEMPLATES의 틀에 자료 값을 끼워 만든다. 값이 비면 그 포인트를 내지 않고 뺀포인트에 적는다.
- 틀과 코드가 만든 값에 금지어(FORBIDDEN)가 들면 render가 ForbiddenWordError를 낸다. 공시 자료에서 온 이름과 조건 값
  (DATA_KEYS. 담보명 "종별 수술비(최고 종 기준)", 지급 형태 "최초 1회" 따위)은 사실을 옮긴 것이라 검사에서 뺀다.
- 근거 급부가 작업 로그 검토 대기이면 같은 종형, 같은 표준담보의 확정 급부로 바꾸고, 바꿀 급부가 없으면 포인트를 뺀다.
- 기준 종형은 판매 중인 정밀비교 우체국 종형만 받는다(points, scope가 다른 종형에 ValueError). 틀이 기준 앞에 "우체국"을 붙인다.
- 감액은 받는 비율로 적는다("1년까지 보험금의 50% 지급"). 감액지급률은 그 기간에 지급하는 비율이다.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from . import compare as C
from . import insights as I
from .model import Cond, Data, HOME_ORG, MAX_AGE, _blank
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
GENERAL_CLEAR_YEARS = 5           # 일반심사의 입원, 수술 질문을 넘는 햇수(기획 2.3절 ②. 결과는 심사가 정한다)

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
BRIEF_PER_KIND = 3
REVISION_TAG = "개정 검토"

# 목적 묶음(기획 3.3절의 추천 목적 세 가지). 화면 이름은 사용자가 정할 것(설계안 7절 4번)이라 임시 이름이다.
PURPOSES = ("암", "3대 질병", "입원과 수술")

# 설계안 4.2의 틀에 쓰지 않는 말
FORBIDDEN = ("업계", "유일", "독점", "최초", "최고", "가장", "더 좋다", "유리", "우수", "저렴", "가성비", "실속",
             "가입됩니다", "거절됩니다", "권하세요", "추천", "바꾸세요", "갈아타세요")

# {키} 또는 {키:조사}. 조사는 앞 글자의 받침으로 고른다(은/는, 이/가, 을/를, 과/와, 이나/나).
TEMPLATES = {
    "G1": "{이력}이고 최근 {소견개월}개월 소견과 {중대년수}년 안 중대질병에 해당하지 않으시면, "
          "우체국 {우리종형}의 고지 질문에는 해당하지 않습니다. {상대문장} 가입 여부는 청약 뒤 심사로 정해집니다.",
    "G1_상대": "{상대:은} 같은 기간에 {상대범위:을} 묻습니다.",
    "G1_상대_기간": "{상대:은} {상대기간}년 안의 {상대범위:을} 묻습니다.",
    "G2": "{나이}세는 우체국 {우리종형}의 가입나이({우리최저}~{우리최고}세) 밖입니다. {상대문장}",
    "G2_상대": "{상대:은} {상대최저}~{상대최고}세를 받습니다.",
    "G3": "{기간}년 안 질문에서 우체국 {우리종형:은} {우리범위:을}, {상대:은} {상대범위:을} 묻습니다. "
          "{중대년수}년 안 중대질병 질문의 질병 수는 우체국 {우리수}개, {상대회사} {상대수}개입니다.",
    "G3_범위": "{기간}년 안 질문에서 우체국 {우리종형:은} {우리범위:을}, {상대:은} {상대범위:을} 묻습니다.",
    "G3_질병수": "{중대년수}년 안 중대질병 질문의 질병 수는 우체국 {우리종형} {우리수}개, {상대} {상대수}개입니다.",
    "A1": "{담보:은} 우체국 {우리종형}에 따로 있는 담보입니다. 견준 {상대회사목록} 상품에는 같은 담보가 없습니다"
          "(넓은 담보와 부분 담보까지 확인).",
    "A1_주의": "상대의 일반 입원 담보로 같은 입원이 지급될 수 있습니다.",
    "A2": "{담보:은} 우체국 {우리종형:이} {우리조건}이고, {상대문장}입니다.",
    "조건_상대": "{상대:은} {상대조건}",
    "Q_질문": "{상대회사}에는 {담보:이} 있던데요.",
    "Q1": "우체국 {우리종형}에는 {담보:을} 따로 주는 담보는 없고, {덮는담보}에서 관련 보장을 합니다. "
          "지급 조건이 같은지는 약관으로 확인해 드리겠습니다.",
    "Q2": "우체국 {우리종형}에는 {담보}에 해당하는 담보가 없습니다.",
    "Q3_질문": "{담보:은} {상대회사:이} 조건이 다르던데요.",
    "Q3": "맞습니다. {담보:은} 우체국 {우리종형:이} {우리조건}이고, {상대문장}입니다.",
    "Q3_경과": "{경과:이} 지나면 {모두} 보험금 전액을 지급합니다.",
    "머리말": "수집한 {상품} 기준({기준일})",
    "구조": "구조 다름: 우체국 {우리구조} 대 {상대구조}",
    "회사수": "견준 {전체}개 회사 가운데 {해당}곳",
    "범위": "견준 상품은 {머리말}입니다. 공통 담보 {비교쌍}쌍 가운데 {뺀비교쌍}쌍은 검토 대기라 견주지 않았습니다.",
    "범위_모두": "견준 상품은 {머리말}입니다. 공통 담보 {비교쌍}쌍을 모두 견줬습니다.",
}
# 공시 자료에서 온 이름과 조건 값, 이미 render를 거친 문장. 금지어 검사에서 뺀다.
DATA_KEYS = {"담보", "우리종형", "상대", "상대회사", "상대회사목록", "덮는담보", "우리조건", "상대조건", "상대문장",
             "상품", "우리구조", "상대구조", "머리말"}

_SLOT = re.compile(r"\{([^{}:]+)(?::([^{}]+))?\}")
_JOSA = {"은": ("은", "는"), "는": ("은", "는"), "이": ("이", "가"), "가": ("이", "가"), "을": ("을", "를"),
         "를": ("을", "를"), "과": ("과", "와"), "와": ("과", "와"), "이나": ("이나", "나"), "나": ("이나", "나")}


class TemplateValueMissing(ValueError):
    """틀의 자리에 끼울 값이 없다. 그 포인트는 내지 않는다."""


class ForbiddenWordError(ValueError):
    """틀이나 코드가 만든 값에 금지어가 들었다."""


# ---------- 문장 ----------
def has_final(word: str) -> bool:
    """마지막 글자에 받침이 있게 읽히는지. 닫는 괄호는 건너뛰고, 숫자와 로마자는 읽는 소리로 본다."""
    s = str(word).rstrip()
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


def or_join(names: Iterable[str]) -> str:
    """"한화생명이나 삼성화재"처럼 잇는다."""
    names = [str(n) for n in names]
    if not names:
        return ""
    return "".join(josa(n, "이나") + " " for n in names[:-1]) + names[-1]


def and_join(names: Iterable[str]) -> str:
    """"한화생명 간편가입형(1년)과 삼성화재 7종"처럼 잇는다. 셋 이상이면 앞은 쉼표로 잇는다."""
    names = [str(n) for n in names]
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
    """관문을 따질 종형: 정밀비교이고 판매 중인 종형. renewal이 있으면 갱신유형이 같은 종형만."""
    return [v for v in data.variant_order
            if data.variants[v].get("비교역할구분") == C.COMPARE_ROLE and _blank(data.variants[v].get("판매종료일"))
            and (renewal is None or data.variants[v].get("갱신유형") == renewal)]


# ---------- 가입 관문 ----------
def question_hit(variant: dict, p: Profile) -> str:
    """고객 이력이 종형의 고지 질문에 걸리는지: 해당 없음, 해당, 심사로 확인, 자료 없음(모듈 설명의 규칙)."""
    uw = variant.get("심사유형")
    if uw == SIMPLE:
        if p.since is None:
            return Q_NONE
        if p.surgery_only:
            surgery = variant.get("고지수술포함여부")
            if surgery is None:
                return Q_NODATA
            if surgery is False:
                return Q_NONE
        years = variant.get("고지입원수술년수")
        if years is None:
            return Q_NODATA
        return Q_NONE if p.since >= years else Q_HIT
    if uw == GENERAL:
        return Q_NONE if p.since is None or p.since >= GENERAL_CLEAR_YEARS else Q_REVIEW
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
    """회사별, 종형별 관문 상태. 회사 상태는 종형 상태 가운데 STATE_ORDER로 앞선 것이다."""
    out: dict[str, dict[str, Any]] = {}
    for vid in targets(data, p.renewal):
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


def classify(gate_result: dict[str, Any]) -> tuple[str, list[str]]:
    """(칸 분류, 자료 없는 회사). 자료 없는 회사는 상태가 나이 자료 없음이나 질문 자료 없음인 회사다."""
    comp = gate_result["회사"]
    us = _side(comp.get(HOME_ORG, {}).get("상태"))
    others = {o: _side(g["상태"]) for o, g in comp.items() if o != HOME_ORG}
    nodata = [o for o, g in comp.items() if _side(g["상태"]) is None]
    known = [s for s in others.values() if s is not None]
    if us is None or not known:
        return NO_DATA, nodata
    if us == OPEN:
        return (BOTH_OPEN if OPEN in known else ONLY_OPEN), nodata
    return (ONLY_CLOSED if OPEN in known else ALL_CLOSED), nodata


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


def our_rep(data: Data, home: dict[str, Any] | None) -> str | None:
    """우리 대표 종형. 열린 간편심사 가운데 질문 기간이 가장 긴 것, 없으면 열린 일반심사의 첫째."""
    if not home:
        return None
    opened = [x["종형ID"] for x in home["종형"] if x["상태"] == OPEN]
    return min(opened, key=lambda v: _rank(data, v)) if opened else None


def peer_reps(ctx: _Ctx, gate_result: dict[str, Any], rep: str) -> dict[str, str]:
    """상대 회사마다 대표 종형. 열림이나 나이 자료 없음인 종형 가운데 compare.peers가 우리 대표에 고르는 종형,
    그 종형이 닫혔으면 남은 것 가운데 질문 기간이 가장 긴 것이다."""
    data = ctx.data
    preferred = ctx.default_peers(rep)
    out = {}
    for org, g in gate_result["회사"].items():
        if org == HOME_ORG:
            continue
        cands = [x["종형ID"] for x in g["종형"] if x["상태"] in (OPEN, NO_AGE)]
        if not cands:
            continue
        pick = next((v for v in preferred if v in cands), None)
        out[org] = pick or min(cands, key=lambda v: _rank(data, v))
    return out


def counts(ctx: _Ctx, base: str, peers: list[str]) -> dict[str, int]:
    """칸의 숫자. 대표끼리 견준 시사점을 응대 포인트 규칙(4.2의 거르기)으로 거른 뒤 센다."""
    key = (base, tuple(peers))
    if key not in ctx.counted:
        result = ctx.result(base, peers)
        kept, _ = insight_points(ctx, result)
        n = {c: sum(1 for x in kept if x["세부"] == c) for c in ("A1", "Q2", "Q3", "A2")}
        ctx.counted[key] = {"고유": n["A1"], "빈자리": n["Q2"], "못함": n["Q3"], "나음": n["A2"],
                            "대기": len(result["뺀시사점"])}
    return ctx.counted[key]


def cell(data: Data, p: Profile, analysis: dict | None, relations: Relations | None = None,
         ctx: _Ctx | None = None) -> dict[str, Any]:
    """지도 칸 하나. 우리 대표나 상대 대표가 없으면 숫자를 비운다(None).

    열린종형은 회사별 열린 종형ID다. 칸을 눌렀을 때 패널이 보이는 값이고, 지도의 이웃 구간을 합칠지 가를 때도 쓴다.
    """
    ctx = _ctx(data, analysis, relations, ctx)
    g = gate(data, p)
    cls, nodata = classify(g)
    rep = our_rep(data, g["회사"].get(HOME_ORG))
    reps = peer_reps(ctx, g, rep) if rep else {}
    out = {"분류": cls, "회사": {o: x["상태"] for o, x in g["회사"].items()}, "대표": rep, "상대대표": reps,
           "수": counts(ctx, rep, list(reps.values())) if rep and reps else None, "자료없음": nodata,
           "열린종형": {o: [y["종형ID"] for y in x["종형"] if y["상태"] == OPEN] for o, x in g["회사"].items()}}
    if cls == ALL_CLOSED:
        out["안내"] = ALL_CLOSED_NOTE
    return out


def since_cuts(data: Data) -> list[float]:
    """지도 행의 경계(년). 맨 앞은 최근 소견 질문의 기간(3개월), 그 뒤는 간편심사 고지입원수술년수와 일반심사 기준 햇수의 합집합."""
    vids = targets(data)
    months = [data.variants[v].get("고지최근소견개월") for v in vids if data.variants[v].get("심사유형") == SIMPLE]
    months = [m for m in months if m is not None]
    low = min(months) / 12 if months else 0.25
    years = {y for y in (_period(data.variants[v]) for v in vids) if y is not None} | {GENERAL_CLEAR_YEARS}
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
    return render("머리말", {"상품": full_name(data, vid), "기준일": data.variants[vid].get("적용시작일")})


def header(data: Data, base: str, peers: list[str]) -> tuple[str, bool]:
    """(범위 머리말, 구조 다름). 회사마다 수집한 상품과 기준일을 적고, 갱신이나 환급 구조가 다른 짝이 있으면 뒤에 붙인다."""
    text = ", ".join(source_text(data, p) for p in peers)
    diff = [p for p in peers if structure_differs(data, base, p)]
    if diff:
        text += " / " + render("구조", {"우리구조": _structure(data.variants[base]),
                                        "상대구조": "; ".join(f"{_org_name(data, p)} {_structure(data.variants[p])}" for p in diff)})
    return text, bool(diff)


def _company_count(data: Data, peers: list[str], hit: list[str]) -> str:
    orgs = list(dict.fromkeys(_org(data, p) for p in peers))
    return render("회사수", {"전체": len(orgs), "해당": len({_org(data, p) for p in hit})})


def scope(data: Data, base: str, peers: list[str], analysis: dict | None, relations: Relations | None = None,
          ctx: _Ctx | None = None) -> dict[str, Any]:
    """범위 띠: 견준 상품과 종형, 상품별 기준일, 구조 다름, 검토 대기로 뺀 쌍."""
    ctx = _ctx(data, analysis, relations, ctx)
    result = ctx.result(base, peers)

    def info(vid: str) -> dict[str, Any]:
        v = data.variants[vid]
        return {"종형ID": vid, "회사": _org_name(data, vid), "공시상품명": v.get("공시상품명"), "종형명": v.get("종형명"),
                "적용시작일": v.get("적용시작일"), "갱신유형": v.get("갱신유형"), "환급유형": v.get("환급유형")}

    rows = [{**info(p), "머리말": source_text(data, p), "구조다름": structure_differs(data, base, p)} for p in peers]
    text, _ = header(data, base, peers)
    return {
        "기준": info(base), "상대": rows, "회사수": len({_org(data, p) for p in peers}),
        "머리말": text,
        "비교쌍": result["비교쌍"], "뺀비교쌍": result["뺀비교쌍"], "뺀시사점": len(result["뺀시사점"]),
        "문장": render("범위" if result["뺀비교쌍"] else "범위_모두",
                     {"머리말": text, "비교쌍": result["비교쌍"], "뺀비교쌍": result["뺀비교쌍"]}) if peers else None,
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

    def drop(self, code: str, sid: str | None, reason: str, peers: list[str] | None = None) -> None:
        self.dropped.append({"세부": code, "세부이름": DETAILS[code][1], "표준담보ID": sid,
                             "표준담보명": self.data.std[sid]["표준담보명"] if sid in self.data.std else None,
                             "비교종형ID": list(peers or []), "사유": reason})

    def add(self, code: str, sid: str | None, template: str, values: dict, involved: list[str], evidence: list[dict],
            *, score: int | None = None, extra_key: str = "", source_check: bool = False, insight: str | None = None,
            question: tuple[str, dict] | None = None, tail: list[tuple[str, dict]] | None = None,
            brief: bool = True, **more: Any) -> None:
        try:
            sentence = render(template, values)
            for tid, vals in tail or []:
                sentence += " " + render(tid, vals)
            asked = render(*question) if question else None
            head, struct = header(self.data, self.base, involved)
        except (TemplateValueMissing, ForbiddenWordError) as e:
            reason = f"값 없음: {e}" if isinstance(e, TemplateValueMissing) else str(e)
            self.drop(code, sid, reason, involved)
            return
        std = self.data.std.get(sid) if sid else None
        self.kept.append({
            "포인트ID": point_id(code, self.base, sid, extra_key),
            "종류": DETAILS[code][0], "세부": code, "세부이름": DETAILS[code][1],
            "표준담보ID": sid, "표준담보명": std["표준담보명"] if std else None,
            "틀": template, "값": {k: _text(v) for k, v in values.items()}, "문장": sentence, "질문": asked,
            "머리말": head, "회사수": _company_count(self.data, self.peers, involved), "비교종형ID": list(involved),
            "근거": evidence, "점수": score, "목적": purposes(std), "구조다름": struct, "원문대조": source_check,
            "시사점ID": insight, "브리핑": brief, **more,
        })


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


def gate_points(ctx: _Ctx, base: str, peers: list[str], p: Profile, out: _Points) -> None:
    """관문 G1(우리만 열림), G2(우리만 닫힘), G3(질문 범위 다름)."""
    data = ctx.data
    bv = data.variants[base]
    g = gate(data, p)
    cls, nodata = classify(g)
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
            parts = [render("G1_상대" if period == _period(bv) else "G1_상대_기간",
                            {"상대": and_join(_peer_name(data, pv) for pv in group), "상대범위": rng, "상대기간": period})
                     for (rng, period), group in groups.items()]
            out.add("G1", None, "G1", {"이력": history_text(p, since_cuts(data)), "소견개월": bv.get("고지최근소견개월"),
                                       "중대년수": bv.get("고지중대질병년수"), "우리종형": _kind_name(data, base),
                                       "상대문장": " ".join(parts)},
                    closed, _gate_evidence(base, closed), extra_key=p.key(), source_check=True)

    # G2: 칸이 우리만 닫힘이고 기준 종형이 나이로 닫힘. 열린 상대 종형의 가입나이를 적는다(나이 자료 없는 회사는 뺀다).
    if p.age is not None and cls == ONLY_CLOSED and mine["나이"] == AGE_NO:
        for org in nodata:
            if org != HOME_ORG:
                out.drop("G2", None, f"나이 자료 없음: {data.org_name(org)}")
        chosen = []
        for org, x in by_org.items():
            if org == HOME_ORG:
                continue
            opened = [y["종형ID"] for y in x["종형"] if y["상태"] == OPEN]
            if opened:
                chosen.append(next((v for v in peers if v in opened), None) or min(opened, key=lambda v: _rank(data, v)))
        ours = age_span(data, base, p.sex)
        parts = []
        for pv in chosen:
            span = age_span(data, pv, p.sex)
            if span:
                parts.append(render("G2_상대", {"상대": _peer_name(data, pv), "상대최저": span[0], "상대최고": span[1]}))
        if not parts or not ours:
            out.drop("G2", None, "가입나이를 적을 수 있는 열린 상대 종형이 없음" if ours else "기준 종형 가입나이 자료 없음", chosen)
        else:
            out.add("G2", None, "G2", {"나이": p.age, "우리종형": _kind_name(data, base), "우리최저": ours[0], "우리최고": ours[1],
                                       "상대문장": " ".join(parts)},
                    chosen, _gate_evidence(base, chosen), extra_key=p.key(), source_check=True)

    # G3: 짝의 같은 기간 질문에서 수술 포함 여부나 중대질병 수가 다름. 고객 조건과 무관하다.
    if bv.get("심사유형") == SIMPLE:
        for pv in peers:
            v = data.variants[pv]
            if v.get("심사유형") != SIMPLE or _period(v) is None or _period(v) != _period(bv):
                continue
            rb, rp = _range_text(bv), _range_text(v)
            nb, np_ = bv.get("고지중대질병수"), v.get("고지중대질병수")
            range_diff = rb is not None and rp is not None and rb != rp
            count_diff = (nb is not None and np_ is not None and nb != np_
                          and bv.get("고지중대질병년수") == v.get("고지중대질병년수"))
            if not range_diff and not count_diff:
                continue
            tid = "G3" if range_diff and count_diff else ("G3_범위" if range_diff else "G3_질병수")
            out.add("G3", None, tid, {"기간": _period(bv), "우리종형": _kind_name(data, base), "우리범위": rb,
                                      "상대": _peer_name(data, pv), "상대범위": rp, "중대년수": bv.get("고지중대질병년수"),
                                      "우리수": nb, "상대회사": _org_name(data, pv), "상대수": np_},
                    [pv], _gate_evidence(base, [pv]), extra_key=pv, source_check=True)


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


def reduction_phrase(segs: list) -> str:
    """감액 구간을 받는 비율이 드러나게 적는다. "1년까지 보험금의 50% 지급", "6개월까지 보험금의 25%, 1년까지 50% 지급".

    sys_급부의 감액지급률은 그 기간에 지급하는 비율이라 "감액 1년 10%"로 쓰면 10% 감액으로 읽힌다(실제로는 90% 감액).
    지급기준구분이 가입금액비율인 급부도 있어 "가입금액의"가 아니라 "보험금의"로 쓴다. insights.reduction_text는
    비교 화면이 쓰므로 그대로 둔다.
    """
    if not segs:
        return "감액 없음"
    stages = sorted((float(m), float(r)) for m, r in segs)
    parts = [f"{I.months_text(m)}까지 {'보험금의 ' if i == 0 else ''}{I._num_text(r * 100)}%"
             for i, (m, r) in enumerate(stages)]
    return ", ".join(parts) + " 지급"


def _cond_value(view: dict[str, Any], item: str) -> str:
    if item == _WAIT:
        return f"면책 {I._num_text(view.get('wait') or 0)}일"
    if item == _RED:
        return reduction_phrase(view.get("red") or [])
    return f"지급 형태 {I.tag_text(I.pay_tags(view.get('limit')))}"


def _cond_text(view: dict[str, Any], items: list[str]) -> str:
    return ", ".join(_cond_value(view, i) for i in items)


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
                                        f"상대 {o.get('상대', 0)}줄)", [p])
            if not kept_peers:
                continue
            ins = {**ins, "근거": {"기준": ins["근거"]["기준"],
                                  "비교": {p: b for p, b in ins["근거"]["비교"].items() if p in kept_peers}}}
        evidence = _evidence(ctx, ins)
        if evidence is None:
            out.drop(code, sid, "근거 급부가 모두 검토 대기", kept_peers)
            continue

        if code == "A1":
            # 패널 주의는 입원 담보에만 단다(상대의 일반 입원 담보로 같은 입원이 지급될 수 있다)
            note = render("A1_주의", {}) if data.std[sid].get("급부유형") == "입원" else None
            out.add(code, sid, "A1", {"담보": v["담보"], "우리종형": mine, "상대회사목록": v.get("없는회사")},
                    involved, evidence, 주의=note, **common)
        elif code in ("Q1", "Q2"):
            q = ("Q_질문", {"상대회사": or_join(v.get("가진회사") or []), "담보": v["담보"]})
            if code == "Q1":
                out.add(code, sid, "Q1", {"우리종형": mine, "담보": v["담보"], "덮는담보": v.get("덮는담보")},
                        involved, evidence, question=q, **common)
            else:
                out.add(code, sid, "Q2", {"우리종형": mine, "담보": v["담보"]}, involved, evidence, question=q,
                        좁은담보=list(v.get("기준좁은담보") or []), 꼬리표=[REVISION_TAG], **common)
        else:
            base_view = data.benefit_view(ins["근거"]["기준"][0]) if ins["근거"]["기준"] else None
            peer_views = {p: data.benefit_view(ins["근거"]["비교"][p][0]) for p in kept_peers if ins["근거"]["비교"].get(p)}
            if base_view is None or len(peer_views) != len(kept_peers):
                out.drop(code, sid, "대표 급부 없음", kept_peers)
                continue
            differ = {i["항목"] for i in ins["항목"] if i.get("종형ID") in kept_peers}
            items = [i for i in _ITEM_ORDER if i in differ or (code == "A2" and i in (_WAIT, _RED))]
            parts = ", ".join(render("조건_상대", {"상대": _peer_name(data, p), "상대조건": _cond_text(peer_views[p], items)})
                              for p in kept_peers)
            values = {"담보": v["담보"], "우리종형": mine, "우리조건": _cond_text(base_view, items), "상대문장": parts}
            if code == "A2":
                # 갱신유형이 다른 짝과 견준 조건 나음은 영업 포인트 탭 본문에만 두고 브리핑과 카드에서는 뺀다(빼는 조건 4)
                brief = all(data.variants[p].get("갱신유형") == base_renewal for p in kept_peers)
                out.add(code, sid, "A2", values, kept_peers, evidence, brief=brief, **common)
            else:
                tail = None
                if differ & set(_ITEM_ORDER) == {_RED}:
                    months = [float(m) for view in [base_view, *peer_views.values()] for m, _ in view.get("red") or []]
                    if months:
                        tail = [("Q3_경과", {"경과": I.months_text(max(months)),
                                            "모두": "둘 다" if len(kept_peers) == 1 else "모두"})]
                q = ("Q3_질문", {"담보": v["담보"], "상대회사": or_join(_org_name(data, p) for p in kept_peers)})
                out.add(code, sid, "Q3", values, kept_peers, evidence, question=q, tail=tail, **common)

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
    }


def brief(result: dict[str, Any], per_kind: int = BRIEF_PER_KIND, purpose: str | None = None) -> list[dict]:
    """브리핑과 응대 카드에 싣는 포인트. 종류마다 위에서 per_kind개, 브리핑에서 빼는 포인트(구조 다름 A2)는 뺀다."""
    out = []
    for kind in KINDS:
        rows = [x for x in result["포인트"] if x["종류"] == kind and x["브리핑"]
                and (purpose is None or x["종류"] == GATE or purpose in x["목적"])]
        out += rows[:per_kind]
    return out


def to_json(value: Any) -> Any:
    """Profile을 dict로 바꿔 json.dumps에 넘길 수 있게 한다."""
    if isinstance(value, Profile):
        return asdict(value)
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    return value
