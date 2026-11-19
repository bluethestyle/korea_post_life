"""사업방법서에서 가입조건(가입나이·보험기간·납입기간·가입금액 한도)과 특약 결합 제약을 뽑는다.

급부 추출과 같은 원칙을 따른다. 모델에는 해당 절만 잘라 넣고, 나이·기간·금액은 원문 글자로 받아
숫자는 코드가 만든다. 문서에 적히지 않은 조건은 만들지 않는다.

- 가입나이 절  → 주계약·특약별 가입나이, 보험기간, 납입기간 (최초계약만 쓴다. 갱신계약 나이는 새 청약 판단에 쓰지 않는다)
- 가입한도 절  → 나이 구간별 가입금액 한도. sys_가입조건의 구간최대가입금액과 sys_특약의 최소·최대 가입금액이 된다
- 특약부가 절과 요약서의 자격요건 절 → 특약 사이의 제약 (선행가입, 최대연동 등)

가입나이를 "가입최저나이"와 "가입최고나이 표"로 따로 적는 문서도 있다. 이 표는 가입유형(종)마다 납입기간 줄이 묶여 있고
칸마다 최고나이만 적혀 있다. 이런 문서는 대상 가입유형의 줄 묶음만 남겨 모델에 넣고, 최저·최고나이를 이어 적은 글자로 받는다.
가입한도 절이 사업방법서에 없으면 요약서 자격요건 절의 "가입한도" 항목에서 읽는다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from .. import ids
from .benefits import money_token, parse_money, squash
from .segment import _lines

# ---------- 절 찾기 ----------
#
# 절 제목은 회사 이름이 아니라 문서에 적힌 모양으로 알아본다. 제목 모양을 여러 개 두고 먼저 맞는 줄을 쓴다.
# - 가입나이: "2. 가입나이, 보험기간, …" / "2. 보험기간, 보험료 납입기간, … 및 피보험자 가입나이" / "4. 보험기간, …, 가입나이 및 …"
# - 특약부가: "4. 특약부가에 관한 사항" / "5. 의무가입에 관한 사항"
# - 자격요건(요약서): "② 보험가입 자격요건" / "2."와 "보험가입자격요건"이 두 줄로 갈린 제목 / "□ 가입자격제한"

_HEADS = {
    "가입나이": re.compile(r"^\d+\.\s*(?:가입나이|보험기간\s*,[^.]*가입나이)"),
    "가입한도": re.compile(r"^\d+\.\s*보험가입금액의?\s*한도"),
    "특약부가": re.compile(r"^\d+\.\s*(?:특약\s*부가|의무\s*가입에\s*관한)"),
}
_OTHER = re.compile(r"^\d+\.\s*기타\s*사항")
_NEXT = re.compile(r"^(\d+)\.\s*[가-힣]")
# (제목, 절이 끝나는 줄) 짝. 제목이 맞은 모양의 끝 표시만 쓴다
_ELIGIBLE = (
    (re.compile(r"^[②2][\s.)]*보험가입\s*자격요건"), re.compile(r"^■\s*건강진단|^◆|^①\s*상품의\s*구성")),
    (re.compile(r"^보험가입\s*자격\s*요건\s*$"), re.compile(r"^[가-하]\.\s*건강진단\s*여부|^보험금\s*지급사유\s*및\s*지급제한")),
    (re.compile(r"^□\s*가입자격\s*제한\s*$"), re.compile(r"^□|^●")),
)
_NUMBER_ONLY = re.compile(r"^\d+\.$")
_ITEM = re.compile(r"^([가-하])\.\s")
# 본문이 끝나고 별첨이 시작되는 줄. 예: "[별첨1] 부가가능 독립특별약관", "( 별첨 2 )". 본문 속의 "[별첨3], 335·5는 …"은 아니다
_APPENDIX = re.compile(r"^[\[(<]\s*별첨\s*[\d\-]*\s*[\])>]\s*[가-힣A-Za-z ]{0,30}$")


@dataclass(frozen=True)
class Section:
    kind: str
    text: str
    first_page: int
    last_page: int


def _cut(lines: list[tuple[int, str]], start: int, end: int, kind: str) -> Section:
    body = lines[start:end]
    return Section(kind, "\n".join(l for _, l in body).strip(), body[0][0], body[-1][0])


def _span(lines: list[tuple[int, str]], head: re.Pattern[str]) -> tuple[int, int] | None:
    """제목이 head에 맞는 절의 (제목 줄, 끝 다음 줄). 절은 번호가 더 큰 다음 제목이나 별첨 앞에서 끝난다.

    번호가 0으로 시작하는 줄("01. 건강 모듈 보장")과 번호가 절 번호보다 크지 않은 줄은 절 안의 항목으로 보고 지나간다.
    """
    start = next((i for i, (_, l) in enumerate(lines) if head.match(l.strip())), None)
    if start is None:
        return None
    number = int(_NEXT.match(lines[start][1].strip()).group(1))
    for i in range(start + 1, len(lines)):
        line = lines[i][1].strip()
        m = _NEXT.match(line)
        if (m and not m.group(1).startswith("0") and int(m.group(1)) > number) or _APPENDIX.match(line):
            return start, i
    return start, len(lines)


def _names_scope(line: str, scope: str) -> bool:
    """항목 제목이 그 종(가입유형)을 가리키는가. "1종"이 "11종"에 걸리지 않게 앞 글자가 숫자인 경우는 뺀다."""
    return re.search(r"(?<!\d)" + re.escape(scope.replace(" ", "")), line.replace(" ", "")) is not None


# 맨 앞 칸(가입유형)이 여러 줄에 걸쳐 합쳐진 표. 가입최고나이 표가 이 모양이다.
# 글자로 풀면 납입기간 줄("10년납 79세 79세 80세 80세")이 이어지고, 가입유형 이름은 그 유형의 줄들 사이에 한 줄로 끼어 있거나
# ("간편가입형(1년)") 줄 앞에 붙어 있다("일반가입형 20년납 69세 …"). 납입기간이 다시 작아지는 줄부터 다음 가입유형이다.
_PAY_ROW = re.compile(r"^(.*?)\s*(\d+)\s*년납((?:\s+\d+\s*세)+)\s*$")
_PAGE_MARK = re.compile(r"^\d+\s*[-/]\s*\d+$")          # 쪽 번호. 예: "1 - 2", "14/567"
_AGE_CELL = re.compile(r"\d+\s*세")


@dataclass
class RowGroup:
    """표에서 한 가입유형에 딸린 줄 묶음."""
    name: str                               # 가입유형 이름. 예: 간편가입형(1년)
    start: int                              # 묶음의 첫 줄 번호
    end: int                                # 묶음의 끝 다음 줄 번호
    rows: list[tuple[str, list[str]]]       # (납입기간, 그 줄의 나이 칸들). 예: ("10년납", ["79세", "79세", "80세", "80세"])


def row_groups(texts: Sequence[str]) -> tuple[int, int, list[RowGroup]] | None:
    """줄 목록에서 가입유형별 줄 묶음 표를 찾는다. (표의 첫 줄 번호, 끝 다음 줄 번호, 묶음들).

    묶음이 둘 이상이고 묶음마다 이름이 꼭 하나씩 잡힐 때만 돌려준다. 그렇지 않으면 이 모양의 표가 아니라고 보고 None.
    표 위에 있던 줄(표 머리)이 쪽이 넘어가며 되풀이된 것과 쪽 번호는 이름으로 치지 않는다.
    """
    marks = [i for i, t in enumerate(texts) if _PAY_ROW.match(t.strip())]
    if len(marks) < 2:
        return None
    first, last = marks[0], marks[-1] + 1
    above = {t.strip() for t in texts[:first]}
    groups: list[RowGroup] = []
    names: list[set[str]] = []
    before = 0
    for i in range(first, last):
        line = texts[i].strip()
        m = _PAY_ROW.match(line)
        if m:
            years = int(m.group(2))
            if not groups or years <= before:
                if groups:
                    groups[-1].end = i
                groups.append(RowGroup("", i, last, []))
                names.append(set())
            before = years
            groups[-1].rows.append((f"{years}년납", [c.replace(" ", "") for c in _AGE_CELL.findall(m.group(3))]))
            name = m.group(1).strip()
        else:
            name = "" if _PAGE_MARK.match(line) or line in above else line
        if name:
            names[-1].add(name)
    if len(groups) < 2 or any(len(n) != 1 for n in names):
        return None
    for group, found in zip(groups, names):
        group.name = next(iter(found))
    return first, last, groups


def _keep_row_groups(kind: str, lines: list[tuple[int, str]], start: int, end: int, types: Sequence[str]) -> Section | None:
    """절 안의 표가 가입유형별 줄 묶음이면 types의 묶음만 남긴다. 표 위아래의 줄은 그대로 둔다. 쪽 번호는 남긴 묶음의 것.

    그런 표가 아니거나 types의 묶음이 하나도 없으면 None.
    """
    found = row_groups([l for _, l in lines[start:end]])
    if found is None:
        return None
    first, last, groups = found
    kept = [x for g in groups if any(_names_scope(g.name, t) for t in types) for x in lines[start + g.start:start + g.end]]
    if not kept:
        return None
    text = "\n".join(l for _, l in lines[start:start + first] + kept + lines[start + last:end]).strip()
    return Section(kind, text, kept[0][0], kept[-1][0])


def _section(kind: str, lines: list[tuple[int, str]], start: int, end: int, scope: str | None,
             whole: bool = True, types: Sequence[str] | None = None) -> Section | None:
    """절이 "가. 1종, 9종 및 11종", "라. 8종"처럼 종별 항목으로 나뉘어 있으면 scope의 항목만 남긴다.

    남기는 것은 절 제목부터 첫 항목 앞까지의 줄과 scope를 이름에 가진 항목이다. 쪽 번호는 남긴 항목의 것을 적는다.
    scope가 없거나 scope를 가진 항목이 없으면 절을 통째로 돌려준다(whole이 거짓이면 None).
    항목 제목은 "가.", "나." 순서로 나오는 줄만 본다(같은 글자가 되풀이되는 것은 받아들인다). 본문 속의 "가. …" 줄에 끊기지 않게 하기 위함이다.
    types: 절을 통째로 돌려줄 때, 절 안의 표가 가입유형별 줄 묶음이면 이 이름들의 묶음만 남긴다(_keep_row_groups).
    """
    heads: list[int] = []
    last = ""
    for i in range(start + 1, end) if scope else ():
        m = _ITEM.match(lines[i][1].strip())
        if m and m.group(1) >= last:
            heads.append(i)
            last = m.group(1)
    if not scope or not any(_names_scope(lines[i][1], scope) for i in heads):
        if not whole:
            return None
        return (_keep_row_groups(kind, lines, start, end, types) if types else None) or _cut(lines, start, end, kind)
    kept: list[tuple[int, str]] = []
    for n, i in enumerate(heads):
        if _names_scope(lines[i][1], scope):
            kept += lines[i:heads[n + 1] if n + 1 < len(heads) else end]
    text = "\n".join(l for _, l in lines[start:heads[0]] + kept).strip()
    return Section(kind, text, kept[0][0], kept[-1][0])


def method_sections(pages: dict[int, str], scope: str | None = None,
                    types: Sequence[str] | None = None) -> dict[str, Section]:
    """사업방법서에서 가입나이·가입한도·특약부가 절을 찾는다. 없는 절은 빠진다.

    scope: 여러 종을 한 문서에 담아 절 안을 "가. 1종, 9종 및 11종", "라. 8종"처럼 종별 항목으로 나눈 문서에서,
    남길 항목의 이름(항목 제목에 적힌 글자. 예: "8종", "간편고지"). 그 이름의 항목이 없는 절은 통째로 돌려준다.
    scope를 준 경우, "기타사항" 절에 그 종의 항목이 있으면 "기타사항"으로 함께 돌려준다.
    이런 문서는 특약 사이의 동시가입·선행가입·가입금액 연동 조건을 기타사항의 종별 항목에 적는다.

    types: 여러 가입유형을 한 표에 담은 문서(가입최고나이 표)에서 남길 가입유형 이름들. 예: ["간편가입형(1년)", "일반가입형"].
    표가 가입유형별 줄 묶음으로 되어 있으면 그 이름의 묶음만 남긴다. 그런 표가 없는 절은 그대로다.
    """
    lines = _lines(pages)
    out: dict[str, Section] = {}
    for kind, head in _HEADS.items():
        span = _span(lines, head)
        if span:
            out[kind] = _section(kind, lines, *span, scope, types=types)
    span = _span(lines, _OTHER) if scope else None
    other = _section("기타사항", lines, *span, scope, whole=False) if span else None
    if other:
        out["기타사항"] = other
    return out


def _eligible_span(lines: list[tuple[int, str]]) -> tuple[int, int] | None:
    """자격요건 절의 (제목 줄, 끝 다음 줄)."""
    found = next(((i, stop) for i, (_, l) in enumerate(lines) for head, stop in _ELIGIBLE if head.match(l.strip())), None)
    if found is None:
        return None
    start, stop = found
    end = next((i for i in range(start + 1, len(lines)) if stop.match(lines[i][1].strip())), len(lines))
    if end < len(lines) and end - 1 > start and _NUMBER_ONLY.match(lines[end - 1][1].strip()):
        end -= 1                # 다음 절의 번호가 제목 윗줄에 따로 적혀 있으면 그 줄도 뺀다
    return start, end


def eligibility_section(pages: dict[int, str], scope: str | None = None,
                        types: Sequence[str] | None = None) -> Section | None:
    """상품요약서의 "보험가입 자격요건"("가입자격제한") 절. 주석에 특약 사이의 제약이 적혀 있다.

    scope: 절이 "가. 7종(납입면제형)", "나. 8종(일반형)"처럼 종별 항목으로 나뉜 문서에서 남길 항목의 이름.
    types: 절 안의 가입나이 표가 가입유형별 줄 묶음일 때 남길 가입유형 이름들(method_sections와 같다).
    """
    lines = _lines(pages)
    span = _eligible_span(lines)
    return _section("자격요건", lines, *span, scope, types=types) if span else None


_LIMIT_ITEM = re.compile(r"^([가-하])\.\s*가입\s*한도\s*$")


def eligibility_limits(pages: dict[int, str]) -> Section | None:
    """상품요약서 자격요건 절 안의 "마. 가입한도" 항목. 없으면 None.

    사업방법서에 "보험가입금액의 한도" 절이 없는 문서는 주계약의 가입한도를 여기에만 적는다.
    """
    lines = _lines(pages)
    span = _eligible_span(lines)
    if span is None:
        return None
    start = next((i for i in range(span[0] + 1, span[1]) if _LIMIT_ITEM.match(lines[i][1].strip())), None)
    if start is None:
        return None
    letter = _LIMIT_ITEM.match(lines[start][1].strip()).group(1)
    end = next((i for i in range(start + 1, span[1])
                if (m := _ITEM.match(lines[i][1].strip())) and m.group(1) > letter), span[1])
    return _cut(lines, start, end, "가입한도")


_NONE = re.compile(r"^[-–·∙]?\s*해당\s*(?:사항\s*)?없음\.?$")


def says_none(section: Section) -> bool:
    """절이 제목 아래에 "해당 없음"만 적고 있는가. 이런 절은 옮길 것이 없으므로 모델을 부르지 않는다."""
    body = [l.strip() for l in section.text.split("\n")[1:] if l.strip()]
    return bool(body) and all(_NONE.match(l) for l in body)


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


# 문서 모양에 따라 덧붙이는 문장. 본문에 그 모양이 있을 때만 "본문" 앞에 붙인다.
# 그 모양이 없는 문서에는 붙지 않으므로, 지금까지 쓰던 지시문은 한 글자도 달라지지 않는다.

_BY_MAX_AGE = re.compile(r"가입\s*최고\s*나이")
_MIN_AGE = re.compile(r"가입\s*최저\s*나이\s*[:：]?\s*((?:만\s*)?\d+\s*세)")
_TILDE_BAND = re.compile(r"(?m)^\s*[~∼]\s*\d+\s*세|\d+\s*세\s*[~∼](?=\s|$)")
_PERIOD_LINK = re.compile(r"(?:보험기간|납입기간)\s*이내")

AGE_BY_MAX_NOTE = """이 본문은 가입나이를 "가입최저나이" 한 줄과 "가입최고나이" 표로 따로 적은 모양입니다. 이 모양에서는 아래와 같이 옮깁니다.
- 가입최고나이 표의 칸 하나를 항목 하나로 옮깁니다. "10년납 79세 79세 80세 80세" 줄은 표 머리에 적힌 순서대로
  (예: 90세만기 남자, 90세만기 여자, 종신 남자, 종신 여자) 항목 네 개가 됩니다
- age: 가입최저나이 글자와 그 칸의 가입최고나이 글자를 "~"로 이어 적습니다. 가입최저나이가 "만15세"이고 칸이 "79세"이면 "만15세~79세"
- term: 그 칸이 놓인 보험기간 글자(예: "90세만기", "종신"). payment: 그 줄 앞에 적힌 납입기간 글자(예: "10년납")
- variant_scope: 그 줄이 속한 가입유형 이름(예: "간편가입형(1년)").
  가입유형 이름은 여러 줄에 걸친 칸 가운데에 적혀 있어, 글자로 풀면 그 유형의 납입기간 줄들 사이에 한 줄로 끼어 있거나
  줄 앞에 붙어 있습니다("일반가입형 20년납 69세 …"). 납입기간이 다시 작아지는 줄(30년납 다음의 10년납)부터 다음 가입유형입니다
- subjects: 상품 전체에 적용되는 표이므로 ["주계약"]. contract는 "구분없음"
- 쪽이 넘어가며 되풀이된 표 머리("구 분", "남자 여자 남자 여자")와 쪽 번호는 옮기지 않습니다"""

LIMIT_TILDE_NOTE = """이 본문은 나이 구간을 "~70세", "71세~"처럼 물결표로 적은 모양입니다. age에는 그 글자 그대로 적습니다.
금액이 하나만 적힌 줄(예: "71세~ 300만원")은 min과 max에 같은 금액을 적습니다.
가입유형 이름이 여럿 나열되어 있고 한도는 가입유형 구분 없이 한 번만 적혀 있으면, 가입유형마다 나누지 않고 variant_scope를 빈 문자열로 둡니다.
표의 줄과 같은 내용을 되풀이한 주석(예: "※ 71세 이상의 가입한도는 300만원")은 따로 옮기지 않습니다."""

PERIOD_LINK_NOTE = """"(주계약 보험기간 이내)", "(주계약 납입기간 이내)"처럼 특약의 보험기간·납입기간을 주계약에 맞춘다는 문장은
가입금액에 대한 제약이 아니므로 옮기지 않습니다."""

_NOTES = {"가입나이": ((_BY_MAX_AGE, AGE_BY_MAX_NOTE),), "가입한도": ((_TILDE_BAND, LIMIT_TILDE_NOTE),),
          "결합제약": ((_PERIOD_LINK, PERIOD_LINK_NOTE),)}


# ---------- 글자를 숫자로 ----------

_AGE = re.compile(r"(\d+)\s*세?\s*[~∼\-]\s*(\d+)\s*세")
_BAND_LE = re.compile(r"(\d+)세이하")
_BAND_GE = re.compile(r"(\d+)세이상")
_BAND_UPTO = re.compile(r"^[~∼](\d+)세$")        # "~70세"
_BAND_FROM = re.compile(r"^(\d+)세[~∼]$")        # "71세~"
_LIST = re.compile(r"^(\d+(?:,\d+)+)(\D.*)$")
_TILDE = re.compile(r"[~∼]")
MAX_AGE = 999


def parse_age_range(text: str) -> tuple[int, int] | None:
    """"20~80세", "만15~50세" → (20, 80), (15, 50). "만25~(주계약 만기나이-1)세"처럼 숫자로 끝나지 않으면 None."""
    m = _AGE.search(str(text or "").replace(" ", ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def parse_age_band(text: str) -> tuple[int, int] | None:
    """"65세 이하" → (0, 65), "66세 이상" → (66, 999), "66세~70세" → (66, 70). 빈 글자는 None(기본 한도).

    물결표를 한쪽에만 쓴 "~70세" → (0, 70), "71세~" → (71, 999)도 읽는다.
    """
    flat = str(text or "").replace(" ", "")
    if not flat:
        return None
    both = parse_age_range(flat)
    if both:
        return both
    upto, since = _BAND_UPTO.match(flat), _BAND_FROM.match(flat)
    if upto:
        return 0, int(upto.group(1))
    if since:
        return int(since.group(1)), MAX_AGE
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


def split_age(text: str, source: str) -> tuple[str, str] | None:
    """가입최저나이와 가입최고나이를 따로 적은 문서에서 둘을 "~"로 이어 적은 나이면 (최저 글자, 최고 글자). 아니면 None.

    "만15세~79세"는 원문에 그 글자로 없다. 원문에 "가입최저나이: 만15세"와 가입최고나이 표가 있고
    앞쪽이 그 최저나이 글자와 같으며 뒤쪽이 "79세" 모양일 때만 이어 적은 것으로 본다.
    """
    low = _MIN_AGE.search(source)
    parts = [p.strip() for p in _TILDE.split(str(text or ""))]
    if not low or not _BY_MAX_AGE.search(source) or len(parts) != 2:
        return None
    if ids.normalize(parts[0]) != ids.normalize(low.group(1)) or not re.fullmatch(r"\d+세", ids.normalize(parts[1])):
        return None
    return parts[0], parts[1]


def join_age(text: str, source: str) -> str:
    """가입최고나이 표의 칸 글자("79세")만 옮겨 온 나이에 원문의 가입최저나이 글자를 붙인다("만15세~79세"). 그 밖에는 그대로."""
    low = _MIN_AGE.search(source)
    if low and _BY_MAX_AGE.search(source) and re.fullmatch(r"\d+세", ids.normalize(text)):
        return f"{low.group(1).strip()}~{text}"
    return text


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
    by_max: bool = False          # 가입최고나이 표의 칸에서 온 항목인가. 나이는 "만15세~79세"처럼 최저·최고를 이어 적은 글자다

    @property
    def ages(self) -> tuple[int, int] | None:
        return parse_age_range(self.age_text)

    @property
    def key(self) -> str:
        parts = [self.subjects[0] if self.subjects else "", self.scope, self.contract, self.sex, self.age_text]
        # 가입최고나이 표는 보험기간·납입기간이 달라도 같은 나이가 여러 칸에 나오므로 칸까지 적어야 항목이 구분된다
        return "|".join(parts + [self.term_text, self.payment_text] if self.by_max else parts)


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
    def period_only(self) -> bool:
        """"주계약 보험기간 이내"처럼 금액이 아니라 기간만 맞춘다는 최대연동인가."""
        flat = squash(self.value_text)
        return self.kind == "최대연동" and "기간" in flat and "금액" not in flat

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
                age = join_age(str(row["age"]).strip(), section.text)
                item: Any = AgeItem(_names(row["subjects"]), str(row.get("variant_scope") or "").strip(),
                                    "" if row.get("contract") in (None, "구분없음") else str(row["contract"]),
                                    _SEX.get(str(row.get("sex")), ""), age,
                                    str(row["term"]).strip(), str(row["payment"]).strip(),
                                    split_age(age, section.text) is not None)
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
                    if one.period_only:                 # 기간을 맞춘다는 조건은 담을 칸이 없다. 가입금액 연동으로 적지 않는다
                        continue
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
            if item.contract == "최초계약" and not item.by_max:       # 가입최고나이 표에는 최초·갱신 줄 구분이 없다
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


def prompt_for(kind: str, text: str) -> str:
    """절 글자를 넣은 지시문. 본문이 _NOTES의 모양이면 그 모양에 맞는 문장을 "본문" 앞에 덧붙인다."""
    template = PROMPTS[kind][0]
    notes = "".join(note + "\n\n" for shape, note in _NOTES[kind] if shape.search(text))
    head, tail = template.rsplit("본문\n{text}", 1)
    return head + notes + "본문\n" + text + tail


def extract(gemini: Any, kind: str, section: Section, model: str, feedback: list[str] | None = None) -> Extracted:
    schema = PROMPTS[kind][1]
    prompt = prompt_for(kind, section.text)
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
    table = row_groups(source.split("\n")) if ex.kind == "가입나이" else None
    out: dict[str, list[str]] = {}
    for item in ex.items:
        missing: list[str] = []
        pair = split_age(item.age_text, source) if ex.kind == "가입나이" and item.by_max else None
        by_max = pair is not None
        if by_max:
            # 가입최고나이 표: 그 가입유형의 줄 묶음에서, 그 납입기간 줄에 그 최고나이가 적혀 있어야 한다.
            # 보험기간·성별 칸까지 맞는지는 판정 문항이 본다. 표를 줄 묶음으로 읽지 못한 문서는 전부 판정 문항에 맡긴다
            top = ids.normalize(pair[1])
            mine = [g for g in table[2] if not item.scope or ids.normalize(g.name) in ids.normalize(item.scope)] if table else []
            pays = expand(item.payment_text)
            if table and not (pays and all(any(pay == p and top in cells for g in mine for pay, cells in g.rows) for p in pays)):
                missing.append("묶음")
        elif ex.kind in ("가입나이", "가입한도") and len(parts) > 1:
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
            if not by_max and not _in(item.age_text, source):
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
    if kind == "가입나이" and item.by_max:
        low, top = (p.strip() for p in _TILDE.split(item.age_text))
        where = (f"가입유형 '{item.scope}', " if item.scope else "") + f"보험료 납입기간 '{item.payment_text}' 줄의 "
        column = f"보험기간 '{item.term_text}'" + {"M": " 남자", "F": " 여자"}.get(item.sex, "")
        return {"가입나이": _statement(f"가입최고나이 표에서 {where}{column} 칸에 적힌 나이는 '{top}'이고, "
                                    f"가입최저나이는 '{low}'이다 (가입유형 이름은 그 유형의 납입기간 줄들 사이에 끼어 있거나 "
                                    "줄 앞에 붙어 있고, 한 줄의 나이는 표 머리에 적힌 순서대로 놓여 있다)")}
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
