"""사업방법서에서 가입조건(가입나이·보험기간·납입기간·가입금액 한도)과 특약 결합 제약을 뽑는다.

급부 추출과 같은 원칙을 따른다. 모델에는 해당 절만 잘라 넣고, 나이·기간·금액은 원문 글자로 받아
숫자는 코드가 만든다. 문서에 적히지 않은 조건은 만들지 않는다.

- 가입나이 절  → 주계약·특약별 가입나이, 보험기간, 납입기간 (최초계약만 쓴다. 갱신계약 나이는 새 청약 판단에 쓰지 않는다)
- 가입한도 절  → 나이 구간별 가입금액 한도. sys_가입조건의 구간최대가입금액과 sys_특약의 최소·최대 가입금액이 된다
- 특약부가 절과 요약서의 자격요건 절 → 특약 사이의 제약 (선행가입, 최대연동 등)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .. import ids
from .benefits import money_token, parse_money, squash
from .segment import _lines

# ---------- 절 찾기 ----------

_HEADS = {
    "가입나이": re.compile(r"^\d+\.\s*가입나이"),
    "가입한도": re.compile(r"^\d+\.\s*보험가입금액의?\s*한도"),
    "특약부가": re.compile(r"^\d+\.\s*특약\s*부가"),
}
_NEXT = re.compile(r"^\d+\.\s*[가-힣]")
_ELIGIBLE = re.compile(r"^[②2][\s.)]*보험가입\s*자격요건")
_ELIGIBLE_END = re.compile(r"^■\s*건강진단|^◆|^①\s*상품의\s*구성")


@dataclass(frozen=True)
class Section:
    kind: str
    text: str
    first_page: int
    last_page: int


def _cut(lines: list[tuple[int, str]], start: int, end: int, kind: str) -> Section:
    body = lines[start:end]
    return Section(kind, "\n".join(l for _, l in body).strip(), body[0][0], body[-1][0])


def method_sections(pages: dict[int, str]) -> dict[str, Section]:
    """사업방법서에서 가입나이·가입한도·특약부가 절을 찾는다. 없는 절은 빠진다."""
    lines = _lines(pages)
    out: dict[str, Section] = {}
    for kind, head in _HEADS.items():
        start = next((i for i, (_, l) in enumerate(lines) if head.match(l.strip())), None)
        if start is None:
            continue
        end = next((i for i in range(start + 1, len(lines)) if _NEXT.match(lines[i][1].strip())), len(lines))
        out[kind] = _cut(lines, start, end, kind)
    return out


def eligibility_section(pages: dict[int, str]) -> Section | None:
    """상품요약서의 "보험가입 자격요건" 절. 주석에 특약 사이의 제약이 적혀 있다."""
    lines = _lines(pages)
    start = next((i for i, (_, l) in enumerate(lines) if _ELIGIBLE.match(l.strip())), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if _ELIGIBLE_END.match(lines[i][1].strip())), len(lines))
    return _cut(lines, start, end, "자격요건")


# ---------- 모델에 주는 형식과 지시문 ----------

_TEXT = {"type": "STRING"}
_NAMES = {"type": "ARRAY", "items": _TEXT}


def _schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {"type": "OBJECT", "required": ["items"], "properties": {"items": {
        "type": "ARRAY", "items": {"type": "OBJECT", "properties": properties, "required": list(properties)}}}}


AGE_SCHEMA = _schema({"subjects": _NAMES, "variant_scope": _TEXT,
                      "contract": {"type": "STRING", "enum": ["최초계약", "갱신계약", "구분없음"]},
                      "sex": {"type": "STRING", "enum": ["남자", "여자", "구분없음"]},
                      "age": _TEXT, "term": _TEXT, "payment": _TEXT})
LIMIT_SCHEMA = _schema({"subjects": _NAMES, "variant_scope": _TEXT, "age": _TEXT, "min": _TEXT, "max": _TEXT, "unit": _TEXT})
CONSTRAINT_SCHEMA = _schema({"base": _TEXT, "targets": _NAMES,
                             "kind": {"type": "STRING", "enum": ["선행가입", "최대연동", "의무부가", "배타선택"]},
                             "value": _TEXT, "quote": _TEXT})

_COMMON = """표가 글자로 풀려 있어 줄이 뒤섞여 있습니다. 원문에 적힌 내용만 옮기고, 적히지 않은 것은 만들지 않습니다.
나이·기간·금액은 숫자로 바꾸지 말고 원문 글자 그대로 적습니다.
주계약이나 특약의 이름은 원문 그대로 적습니다. 여러 줄에 갈려 있으면 이어 붙입니다.
상품 이름(예: "무배당 ○○건강보험(20년갱신형) 2606")이나 "주계약"이 가리키는 것은 "주계약"이라고 적습니다."""

AGE_PROMPT = """아래는 보험 사업방법서의 "가입나이, 보험기간, 보험료 납입기간" 절입니다.
""" + _COMMON + """

표의 가입나이 줄 하나를 항목 하나로 옮깁니다.
- subjects: 그 표가 적용되는 주계약·특약 이름 전부 (표 위 "가.", "나." 항목에 나열된 이름)
- variant_scope: 표 바로 위에 "- 1종(간편가입315), 2종(간편가입325), 3종(간편가입355)"처럼 종 구분이 적혀 있으면 그 글자 그대로. 없으면 빈 문자열
- contract: "최초계약" 줄이면 "최초계약", "갱신계약" 줄이면 "갱신계약". 그런 구분이 없는 표면 "구분없음"
  한 표에서 최초계약 줄은 하나뿐이고(성별로 나뉘면 성별마다 하나), 그 뒤에 이어지는 나이 줄은 모두 갱신계약입니다.
  "갱신계약"이라는 글자는 합쳐진 칸 가운데에 적혀 있어, 글자로 풀면 갱신계약의 첫 나이 줄보다 아래에 나타납니다
- sex: 가입나이 칸이 남자·여자로 나뉘어 있으면 성별마다 항목을 따로 만들고 "남자" 또는 "여자". 나뉘어 있지 않으면 "구분없음"
- age: 가입나이 글자 그대로. 예: "20~80세", "만15~50세"
- term: 그 줄의 보험기간 글자 그대로. 예: "20년만기(갱신형)", "90,95,100세만기", "10년"
  여러 가입나이 줄이 보험기간 칸 하나를 함께 쓰면 줄마다 같은 보험기간을 적습니다
- payment: 그 줄의 보험료 납입기간 글자 그대로. 예: "전기납", "5,10,15,20,30년납"
  납입주기(월납)는 적지 않습니다

특약은 주계약과 같다는 주석만 있고 표가 없는 특약은, 주계약이 든 표의 subjects에 함께 적혀 있으면 그대로 두고 따로 만들지 않습니다.

본문
{text}"""

LIMIT_PROMPT = """아래는 보험 사업방법서의 "보험가입금액의 한도" 절입니다.
""" + _COMMON + """

한도 한 줄을 항목 하나로 옮깁니다.
- subjects: 그 한도가 적용되는 주계약·특약 이름 전부
- variant_scope: 한도가 종별로 나뉘어 적혀 있으면(표의 "구 분" 칸에 "1종(간편가입)", "2종(일반가입)"처럼) 그 종 글자 그대로.
  나뉘어 있지 않으면 빈 문자열. 종마다 한도가 다르면 종마다 항목을 따로 만듭니다
- age: 한도가 나이 구간별로 적혀 있으면 그 구간 글자 그대로. 예: "65세 이하", "66세~70세", "71세 이상"
  나이 구분 없이 적힌 기본 한도는 빈 문자열. "※ 단, 가입 당시 61세 이상인 경우 …"처럼 덧붙은 한도는 "61세 이상"으로 항목을 따로 만듭니다
- min, max: 한도의 아래쪽과 위쪽 금액. 예: "1,000만원~4,000만원"이면 "1,000만원"과 "4,000만원". "500만원(고정)"이면 둘 다 "500만원"
- unit: 가입단위 글자 그대로. 예: "500만원 단위". 없으면 빈 문자열

여러 계약의 가입금액을 합산한다는 문장처럼 금액이 없는 줄은 옮기지 않습니다.

본문
{text}"""

CONSTRAINT_PROMPT = """아래는 보험 문서에서 특약을 부가하는 조건이 적힌 부분입니다.
""" + _COMMON + """

특약과 특약, 또는 주계약과 특약 사이의 제약만 옮깁니다.
- kind
  "선행가입": 어떤 특약(base)에 가입해야만 다른 특약(targets)을 부가할 수 있음. 예: "A특약은 B특약을 가입하는 경우에 한하여 부가" → base B, targets [A]
  "최대연동": 특약(targets)의 가입금액이 주계약 등(base)의 가입금액 이내로 묶임. 예: "특약은 주계약 보험가입금액 이내에서 가입 가능" → base 주계약
  "의무부가": base에 가입하면 targets를 반드시 부가해야 함
  "배타선택": base와 targets를 함께 가입할 수 없음
- base: 기준이 되는 주계약·특약 이름
- targets: 제약을 받는 특약 이름 전부. "특약은 …"처럼 이름 없이 적혀 있으면 그 주석이 달린 표의 특약 이름들을 적습니다
- value: 금액이나 비율 조건이 있으면 원문 글자 그대로. 예: "주계약 보험가입금액 이내". 없으면 빈 문자열
- quote: 근거가 되는 원문 문장을 80자 안에서 그대로

다음은 특약 사이의 제약이 아니므로 옮기지 않습니다: "(선택)"이라고만 적힌 선택특약 목록, 같은 종의 주계약에만 부가할 수 있다는 문장,
종끼리의 중복가입 가능 여부, 여러 계약의 가입금액 합산, 나이에 따른 가입금액 한도.

본문
{text}"""


# ---------- 글자를 숫자로 ----------

_AGE = re.compile(r"(\d+)\s*세?\s*[~∼\-]\s*(\d+)\s*세")
_BAND_LE = re.compile(r"(\d+)세이하")
_BAND_GE = re.compile(r"(\d+)세이상")
_LIST = re.compile(r"^(\d+(?:,\d+)+)(\D.*)$")
MAX_AGE = 999


def parse_age_range(text: str) -> tuple[int, int] | None:
    """"20~80세", "만15~50세" → (20, 80), (15, 50). "만25~(주계약 만기나이-1)세"처럼 숫자로 끝나지 않으면 None."""
    m = _AGE.search(str(text or "").replace(" ", ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def parse_age_band(text: str) -> tuple[int, int] | None:
    """"65세 이하" → (0, 65), "66세 이상" → (66, 999), "66세~70세" → (66, 70). 빈 글자는 None(기본 한도)."""
    flat = str(text or "").replace(" ", "")
    if not flat:
        return None
    both = parse_age_range(flat)
    if both:
        return both
    lo, hi = _BAND_GE.search(flat), _BAND_LE.search(flat)
    if lo and hi:
        return int(lo.group(1)), int(hi.group(1))
    if hi:
        return 0, int(hi.group(1))
    if lo:
        return int(lo.group(1)), MAX_AGE
    return None


def expand(text: str) -> list[str]:
    """"90,95,100세만기" → ["90세만기", "95세만기", "100세만기"]. 나열이 아니면 그대로 하나."""
    flat = str(text or "").replace(" ", "")
    m = _LIST.match(flat)
    if not m:
        return [flat] if flat else []
    return [f"{n}{m.group(2)}" for n in m.group(1).split(",")]


def is_main(name: str) -> bool:
    """주계약을 가리키는 이름인가. 사업방법서는 주계약을 상품 이름으로 적는다. 특약 이름에는 늘 "특약"이 들어 있다."""
    flat = ids.normalize(name)
    return flat == "주계약" or ("특약" not in flat and "보험" in flat)


def _same(a: str, b: str) -> bool:
    return ids.normalize(a) == ids.normalize(b)


def _in(text: str, source: str) -> bool:
    return ids.normalize(text).replace(",", "") in ids.normalize(source).replace(",", "")


# ---------- 추출 결과 ----------

@dataclass
class AgeItem:
    subjects: list[str]
    scope: str
    contract: str
    sex: str                      # "", "M", "F"
    age_text: str
    term_text: str
    payment_text: str

    @property
    def ages(self) -> tuple[int, int] | None:
        return parse_age_range(self.age_text)

    @property
    def key(self) -> str:
        return "|".join([self.subjects[0] if self.subjects else "", self.scope, self.contract, self.sex, self.age_text])


@dataclass
class LimitItem:
    subjects: list[str]
    age_text: str
    min_text: str
    max_text: str
    unit_text: str
    scope: str = ""               # 한도가 종별로 다를 때의 종 구분

    @property
    def band(self) -> tuple[int, int] | None:
        return parse_age_band(self.age_text)

    @property
    def low(self) -> float | None:
        return parse_money(self.min_text or None)

    @property
    def high(self) -> float | None:
        return parse_money(self.max_text or None)

    @property
    def key(self) -> str:
        return "|".join([self.subjects[0] if self.subjects else "", self.scope, self.age_text])


@dataclass
class ConstraintItem:
    base: str
    targets: list[str]
    kind: str
    value_text: str
    quote: str

    @property
    def key(self) -> str:
        return "|".join([self.kind, self.base, self.targets[0] if self.targets else ""])

    @property
    def value(self) -> tuple[float | None, str | None]:
        """(제약수치, 제약단위). "주계약 보험가입금액 이내"는 주계약의 100%로 적는다."""
        flat = squash(self.value_text)
        pct = re.search(r"(\d+(?:\.\d+)?)%", flat)
        if pct:
            return float(pct.group(1)) / 100, "비율"
        if money_token(flat):
            return parse_money(flat), "만원"
        if self.kind == "최대연동" and ("이내" in flat or "이하" in flat or "한도" in flat):
            return 1.0, "비율"
        return None, None


@dataclass
class Extracted:
    kind: str                     # 가입나이 / 가입한도 / 결합제약
    section: Section
    items: list[Any]
    model: str
    problems: list[str] = field(default_factory=list)


_SEX = {"남자": "M", "여자": "F"}


def _names(value: Any) -> list[str]:
    return [str(v).strip() for v in (value or []) if str(v).strip()]


def parse(kind: str, section: Section, raw: dict[str, Any], model: str) -> Extracted:
    out = Extracted(kind, section, [], model)
    seen: set[str] = set()
    for row in (raw or {}).get("items") or []:
        try:
            if kind == "가입나이":
                item: Any = AgeItem(_names(row["subjects"]), str(row.get("variant_scope") or "").strip(),
                                    "" if row.get("contract") in (None, "구분없음") else str(row["contract"]),
                                    _SEX.get(str(row.get("sex")), ""), str(row["age"]).strip(),
                                    str(row["term"]).strip(), str(row["payment"]).strip())
                if not item.subjects or not item.term_text or not item.payment_text:
                    out.problems.append(f"대상이나 기간이 비어 있음: {item.key}")
                    continue
                if item.contract == "갱신계약":      # 새 청약 판단에 쓰지 않는다
                    continue
                if item.ages is None:
                    out.problems.append(f"가입나이를 숫자로 읽을 수 없음: {item.key}")
                    continue
                if item.ages and item.ages[0] > item.ages[1]:
                    out.problems.append(f"최저 나이가 최고 나이보다 큼: {item.key}")
                    continue
            elif kind == "가입한도":
                item = LimitItem(_names(row["subjects"]), str(row.get("age") or "").strip(), str(row["min"]).strip(),
                                 str(row["max"]).strip(), str(row.get("unit") or "").strip(),
                                 str(row.get("variant_scope") or "").strip())
                if not item.subjects or item.low is None or item.high is None:
                    out.problems.append(f"대상이나 금액이 비어 있음: {item.key}")
                    continue
                if item.low > item.high:
                    out.problems.append(f"아래쪽 한도가 위쪽보다 큼: {item.key}")
                    continue
                if item.age_text and item.band is None:
                    out.problems.append(f"나이 구간을 읽을 수 없음: {item.key}")
                    continue
            else:
                base, names = str(row["base"]).strip(), _names(row["targets"])
                if not base or not names:
                    out.problems.append(f"기준이나 대상이 비어 있음: {row.get('kind')}|{base}")
                    continue
                # 대상마다 항목을 따로 만든다. 묶어서 판정하면 잘못 끼어든 대상을 가려내지 못한다.
                for name in names:
                    one = ConstraintItem(base, [name], str(row["kind"]), str(row.get("value") or "").strip(),
                                         str(row.get("quote") or "").strip())
                    if one.key not in seen and not _same(name, base):
                        seen.add(one.key)
                        out.items.append(one)
                continue
        except (KeyError, TypeError, ValueError) as e:
            out.problems.append(f"형식 오류: {e}")
            continue
        if item.key in seen:
            out.problems.append(f"같은 항목이 두 번 나옴: {item.key}")
            continue
        seen.add(item.key)
        out.items.append(item)
    if kind == "가입나이":
        firsts: dict[tuple[str, str, str], list[str]] = {}
        for item in out.items:
            if item.contract == "최초계약":
                for name in item.subjects:
                    firsts.setdefault((ids.normalize(name), item.scope.replace(" ", ""), item.sex), []).append(item.key)
        for keys in firsts.values():
            for key in keys[1:] if len(set(keys)) > 1 else []:
                message = f"같은 대상에 최초계약 나이 줄이 둘 이상임(뒤의 줄은 갱신계약일 수 있음): {key}"
                if message not in out.problems:
                    out.problems.append(message)
    return out


PROMPTS = {"가입나이": (AGE_PROMPT, AGE_SCHEMA), "가입한도": (LIMIT_PROMPT, LIMIT_SCHEMA),
           "결합제약": (CONSTRAINT_PROMPT, CONSTRAINT_SCHEMA)}


def extract(gemini: Any, kind: str, section: Section, model: str, feedback: list[str] | None = None) -> Extracted:
    template, schema = PROMPTS[kind]
    prompt = template.replace("{text}", section.text)
    if feedback:
        prompt += "\n\n앞선 추출에서 드러난 문제 (같은 실수를 되풀이하지 않습니다)\n" + "\n".join(f"- {f}" for f in feedback[:8])
    raw = gemini.generate(model, prompt, schema=schema)
    return parse(kind, section, raw if isinstance(raw, dict) else {}, model)


# ---------- 코드 대조 ----------

_GROUP = re.compile(r"^[가-힣]\.\s")


def groups(text: str) -> list[str]:
    """절을 "가.", "나." 항목 단위로 나눈다. 항목마다 대상 이름과 표가 함께 들어 있다."""
    out: list[list[str]] = []
    for line in text.split("\n"):
        if _GROUP.match(line.strip()) or not out:
            out.append([])
        out[-1].append(line)
    return ["\n".join(g) for g in out]


def literal_problems(ex: Extracted) -> dict[str, list[str]]:
    """항목별로 원문에서 글자 그대로 확인되지 않은 칸.

    가입나이·가입한도는 대상 이름과 값이 같은 "가.", "나." 항목 안에 함께 있는지도 본다("묶음").
    이름과 값이 각각 원문에 있어도 서로 다른 항목의 것이면 잘못 묶은 것이다.
    """
    source = ex.section.text
    parts = groups(source)
    out: dict[str, list[str]] = {}
    for item in ex.items:
        missing: list[str] = []
        if ex.kind in ("가입나이", "가입한도") and len(parts) > 1:
            values = ([item.age_text, item.term_text, item.payment_text] if ex.kind == "가입나이"
                      else [item.age_text, item.scope])
            tokens = [money_token(t) for t in (item.min_text, item.max_text)] if ex.kind == "가입한도" else []

            def holds(part: str) -> bool:
                return (all(_in(n, part) or (is_main(n) and "주계약" in part) for n in item.subjects)
                        and all(_in(v, part) for v in values if v) and all(t in squash(part) for t in tokens if t))

            if not any(holds(part) for part in parts):
                missing.append("묶음")
        names = item.subjects if ex.kind != "결합제약" else [item.base, *item.targets]
        if any(not is_main(n) and not _in(n, source) for n in names if n):
            missing.append("이름")
        if ex.kind == "가입나이":
            if not _in(item.age_text, source):
                missing.append("가입나이")
            if not _in(item.term_text, source):
                missing.append("보험기간")
            if not _in(item.payment_text, source):
                missing.append("납입기간")
        elif ex.kind == "가입한도":
            if item.age_text and not _in(item.age_text, source):
                missing.append("나이구간")
            for text in (item.min_text, item.max_text):
                if money_token(text) not in squash(source):
                    missing.append("금액")
                    break
        if missing:
            out[item.key] = missing
    return out


# ---------- 판정 문항 ----------

def _statement(claim: str) -> dict:
    return {"type": "noul", "instructions": "다음 진술이 원문과 일치하면 참, 원문과 다르거나 원문에 근거가 없으면 거짓. "
                                            "원문은 표가 글자로 풀린 것이라 줄이 뒤섞여 있고, 낱말이 여러 줄에 갈려 있어도 "
                                            f"같은 칸의 글자면 이어서 읽는다. 진술: {claim}"}


def _who(names: list[str]) -> str:
    return f"'{names[0]}'" + (f" 등 {len(names)}개" if len(names) > 1 else "")


def checks(kind: str, item: Any) -> dict[str, dict]:
    """항목 하나를 판정 문항으로. 모두 참이어야 맞는 추출이다."""
    if kind == "가입나이":
        scope = f"{item.scope}의 " if item.scope else ""
        contract = f"{item.contract} " if item.contract else ""
        sex = {"M": "남자 ", "F": "여자 "}.get(item.sex, "")
        table = f"{_who(item.subjects)}에 적용되는 {scope}표"
        age = (f"{table}에서 {contract}{sex}가입나이는 '{item.age_text}'이다" if item.contract
               else f"{table}에 {sex}가입나이 '{item.age_text}' 줄이 있다")
        return {
            "가입나이": _statement(age),
            "보험기간": _statement(f"{table}에서 {contract}{sex}가입나이 '{item.age_text}' 줄의 보험기간은 "
                               f"'{item.term_text}'이고 보험료 납입기간은 '{item.payment_text}'이다 "
                               "(여러 줄이 한 칸을 함께 쓰면 그 칸의 값이 각 줄에 적용된다)"),
        }
    if kind == "가입한도":
        when = f"가입 당시 나이가 {item.age_text}인 경우의" if item.age_text else "나이 조건 없이 적힌 기본"
        if item.scope:
            when = f"{item.scope}에서 {when}"
        amount = (f"{item.min_text}(고정)" if item.low == item.high else f"{item.min_text}에서 {item.max_text}까지")
        return {"금액": _statement(f"{_who(item.subjects)}의 {when} 보험가입금액 한도는 {amount}이다")}
    target = f"'{item.targets[0]}'"
    claim = {
        "선행가입": f"{target}은(는) '{item.base}'을(를) 가입한 경우에만 부가할 수 있다",
        "최대연동": f"{target}의 보험가입금액은 '{item.base}'의 보험가입금액을 넘을 수 없다",
        "의무부가": f"'{item.base}'에 가입하면 {target}을(를) 반드시 부가해야 한다",
        "배타선택": f"'{item.base}'과(와) {target}은(는) 함께 가입할 수 없다",
    }[item.kind]
    return {"제약": _statement(f"원문에 따르면 {claim}")}


def judge(gemini: Any, ex: Extracted, model: str) -> dict[str, dict[str, float]]:
    """항목별·칸별로 추출값이 원문과 일치할 확률."""
    questions: dict[str, dict] = {}
    index: dict[str, tuple[str, str]] = {}
    for i, item in enumerate(ex.items):
        for j, (name, question) in enumerate(checks(ex.kind, item).items()):
            questions[f"q{i}_{j}"] = question
            index[f"q{i}_{j}"] = (item.key, name)
    out: dict[str, dict[str, float]] = {item.key: {} for item in ex.items}
    keys = list(questions)
    for start in range(0, len(keys), 30):          # 문항이 많으면 나눠 묻는다
        chunk = {k: questions[k] for k in keys[start:start + 30]}
        answers = gemini.decide(model, ex.section.text, chunk)
        for k, a in answers.items():
            if k in index:
                key, name = index[k]
                out[key][name] = a.prob(True)
    return out


# ---------- 시트 행으로 바꾸기 ----------

@dataclass
class Target:
    """한 종형에서 이름으로 특약을 찾기 위한 정보."""
    variant_id: str
    variant_name: str                       # 종형명. 예: 1종(간편가입315)
    riders: dict[str, str]                  # 특약계보키 → 특약ID
    main_id: str | None                     # 주계약의 특약ID

    def rider(self, name: str) -> tuple[bool, str | None]:
        """(찾았는가, 특약ID). 주계약은 (True, None)."""
        if is_main(name):
            return True, None
        key = ids.rider_lineage_key(name)
        return (True, self.riders[key]) if key in self.riders else (False, None)


def target_of(variant_id: str, variant_name: str, rider_rows: list[dict[str, Any]]) -> Target:
    mine = [r for r in rider_rows if r["종형ID"] == variant_id]
    return Target(variant_id, variant_name, {r["특약계보키"]: r["특약ID"] for r in mine if r["담보구분"] != "주계약"},
                  next((r["특약ID"] for r in mine if r["담보구분"] == "주계약"), None))


def _applies(scope: str, target: Target, everyone: list[Target]) -> bool | None:
    """종 구분이 이 종형을 가리키는가. 구분이 있는데 어느 종형과도 맞지 않으면 None."""
    flat = scope.replace(" ", "")
    if not flat:
        return True
    hits = [t for t in everyone if t.variant_name.replace(" ", "") in flat]
    if not hits:
        return None
    return target in hits


def _limit_at(age: int, limits: list[LimitItem]) -> LimitItem | None:
    banded = [l for l in limits if l.band and l.band[0] <= age <= l.band[1]]
    if banded:
        return min(banded, key=lambda l: l.band[1] - l.band[0])
    return next((l for l in limits if l.band is None), None)


def _split(lo: int, hi: int, limits: list[LimitItem]) -> list[tuple[int, int, LimitItem | None]]:
    """가입나이 구간을 한도가 바뀌는 나이에서 나눈다."""
    cuts = {lo}
    for l in limits:
        if l.band:
            for edge in (l.band[0], l.band[1] + 1):
                if lo < edge <= hi:
                    cuts.add(edge)
    starts = sorted(cuts)
    return [(s, (starts[i + 1] - 1) if i + 1 < len(starts) else hi, _limit_at(s, limits)) for i, s in enumerate(starts)]


@dataclass
class Built:
    conditions: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    amounts: dict[str, tuple[float, float]] = field(default_factory=dict)     # 특약ID → (최소, 최대 가입금액)
    notes: list[str] = field(default_factory=list)
    origin: dict[str, list[str]] = field(default_factory=dict)                # 행 ID → 그 행을 만든 항목 키


def build_rows(targets: list[Target], ages: list[AgeItem], limits: list[LimitItem],
               constraints: list[ConstraintItem]) -> Built:
    out = Built()
    unknown: set[str] = set()

    def limits_for(target: Target, rider_id: str | None) -> list[LimitItem]:
        found = []
        for l in limits:
            if not _applies(l.scope, target, targets):
                continue
            for name in l.subjects:
                ok, rid = target.rider(name)
                if ok and rid == rider_id:
                    found.append(l)
                    break
        return found

    for target in targets:
        seen: set[str] = set()
        for item in ages:
            if item.contract == "갱신계약" or item.ages is None:
                continue
            applies = _applies(item.scope, target, targets)
            if applies is None:
                out.notes.append(f"종 구분 '{item.scope}'이 어느 종형과도 맞지 않아 건너뜀")
                continue
            if not applies:
                continue
            for name in item.subjects:
                ok, rider_id = target.rider(name)
                if not ok:
                    unknown.add(name)
                    continue
                mine = limits_for(target, rider_id)
                for term in expand(item.term_text):
                    for payment in expand(item.payment_text):
                        for lo, hi, limit in _split(*item.ages, mine):
                            row_id = ids.condition_id(target.variant_id, term, payment, rider_id or "", item.sex, f"{lo}-{hi}")
                            if row_id in seen:
                                continue
                            seen.add(row_id)
                            out.conditions.append({
                                "조건행ID": row_id, "종형ID": target.variant_id, "특약ID": rider_id,
                                "보험기간구분": term, "납입기간구분": payment, "성별": item.sex or None,
                                "최저가입나이": lo, "최고가입나이": hi,
                                "구간최대가입금액만원": limit.high if limit else None,
                            })
                            out.origin[row_id] = [item.key] + ([limit.key] if limit else [])
        for l in limits:
            applies = _applies(l.scope, target, targets)
            if applies is None:
                out.notes.append(f"종 구분 '{l.scope}'이 어느 종형과도 맞지 않아 건너뜀")
            if not applies:
                continue
            for name in l.subjects:
                ok, rider_id = target.rider(name)
                if not ok:
                    unknown.add(name)
                    continue
                rid = rider_id or target.main_id
                if rid is None:
                    continue
                low, high = out.amounts.get(rid, (l.low, l.high))
                out.amounts[rid] = (min(low, l.low), max(high, l.high))
        for c in constraints:
            ok, base_id = target.rider(c.base)
            base_id = base_id or target.main_id
            if not ok or base_id is None:
                unknown.add(c.base)
                continue
            value, unit = c.value
            for name in c.targets:
                ok, rider_id = target.rider(name)
                if not ok or rider_id is None:
                    if not ok:
                        unknown.add(name)
                    continue
                row_id = ids.constraint_id(target.variant_id, base_id, rider_id, c.kind)
                if row_id in out.origin:
                    continue
                out.constraints.append({
                    "제약ID": row_id, "종형ID": target.variant_id, "기준특약ID": base_id, "대상특약ID": rider_id,
                    "제약유형": c.kind, "제약수치": value, "제약단위": unit, "근거문구": c.quote[:200] or None,
                })
                out.origin[row_id] = [c.key]
    out.notes = list(dict.fromkeys(out.notes))
    for name in sorted(unknown):
        out.notes.append(f"'{name}'은(는) 뽑아 둔 특약 목록에 없어 건너뜀")
    return out
