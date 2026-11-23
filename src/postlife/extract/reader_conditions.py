"""초기 적재의 두 판독이 낸 주계약 가입조건을 검사하고, 견주고, sys_가입조건 행으로 옮긴다.

급부 쪽(reader_rows.py)과 같은 방식이다. 두 판독자(sonnet, opus)가 사업방법서의 가입나이 표를 따로 읽어 값을 내고,
코드가 둘을 견주고 그 쪽의 글자와 대조한다. 두 판독이 같고 기계 검사를 통과한 종형만 확정이고, 나머지는 메인 세션이
원문 쪽을 보고 판정한다. 범위는 주계약뿐이다(특약별 가입조건과 결합 제약은 읽지 않는다).

일감(TASK_FORMAT "가입조건일감/1")
    일감 이름, 기관코드, 사업방법서와 상품요약서의 PDF 경로와 쪽 글자 파일 경로, 볼 쪽 범위와 쪽 안내, 종형 목록.
    종형마다 종형ID와 그 ID를 만드는 값(공시상품코드, 종형명. data/targets 그대로).

판독 값(FORMAT "가입조건판독/1"). 설명은 docs/backfill_conditions_guide.md
    표      판독자가 읽은 가입나이 표 목록. 여러 종형이 표 하나를 함께 쓰면 표는 한 번만 적는다.
            표, 근거쪽, 근거낱말   표 이름(판독자가 붙인 짧은 이름), 표 제목이 있는 쪽, 그 표가 이 종형의 것이라고 본 낱말
            줄      [{쪽, 성별, 보험기간, 납입기간, 최저나이, 최고나이, 최고나이식}] 주계약의 가입나이 줄
            한도없음, 한도   주계약 가입한도가 문서에 적혀 있지 않으면 true와 []. 적혀 있으면 false와
                             [{쪽, 문서, 최저나이, 최고나이, 보험기간, 납입기간, 최저금액만원, 최고금액만원}]
            모름    [{칸(표|줄|한도), 이유}]
    종형    [{종형ID, 표, 모름}] 일감의 종형마다 그 종형이 쓰는 표 이름. 표를 고르지 못하면 표는 ""이고 모름에 이유

원문 구절을 옮겨 적는 칸은 없다. 근거낱말은 표 제목에서 뽑은 짧은 낱말(20자 이하, 다섯 개 이하)이다.
근거낱말은 근거쪽 글자에 있어야 하고(machine_checks), 종형명과도 맞아야 한다(title_marks: "2형"처럼 형이나 종 번호를 적은
낱말이 종형명에 없으면 두 판독이 같아도 확정하지 않는다). 종형마다 맞는 표를 고르는 것이 가장 중요하기 때문이다.
가입나이가 "20세~(76-납입기간)세"처럼 식으로 적혀 있으면 판독자가 계산한 최고나이와 그 식("76-납입기간")을 함께 적고,
코드가 식의 숫자가 그 쪽에 있는지와 계산이 맞는지를 본다.

행은 conditions.build_rows로 만든다(조건행ID 규칙 그대로). 주계약 행이므로 특약ID는 비운다.

쓰는 법
    task = json.load(...)                                     # 일감
    tables, links, errs = parse_reading(json.load(...))       # 판독 파일 하나
    result = compare_task(task, {"sonnet": a, "opus": b}, ["sonnet", "opus"], pages)
    built = build_rows(task["종형"], finals)                  # finals: 종형ID → 확정된 표 값
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .. import ids
from . import benefits as B
from . import conditions as C

FORMAT = "가입조건판독/1"
TASK_FORMAT = "가입조건일감/1"

SEXES = ("구분없음", "남자", "여자")
DOCS = ("사업방법서", "상품요약서")
UNKNOWN_FIELDS = ("표", "줄", "한도")
MAIN_NAME = "주계약"

_TERM = re.compile(r"^(?:\d+세만기|\d+년만기|\d+년|종신)$")
_PAY = re.compile(r"^(?:\d+년납|\d+세납|전기납|일시납)$")
_FORMULA = re.compile(r"^(\d+)-(납입기간|보험기간)$")
_SHORT = 20                 # 근거낱말 하나의 길이 한도. 원문 문장을 옮겨 적지 못하게 한다
_WORDS = 5                  # 근거낱말 수 한도
_NAME = 10                  # 표 이름 길이 한도
_REASON = 80                # 모름 이유의 길이 한도

SAME, DIFF, ONE_UNKNOWN, BOTH_UNKNOWN = "같음", "다름", "한쪽모름", "둘다모름"
CONFIRMED, NEEDS_JUDGE = "확정", "판정필요"
UNKNOWN = "모름"

TABLE_KEYS = {"표", "근거쪽", "근거낱말", "줄", "한도없음", "한도", "모름"}
LINE_KEYS = {"쪽", "성별", "보험기간", "납입기간", "최저나이", "최고나이", "최고나이식"}
LIMIT_KEYS = {"쪽", "문서", "최저나이", "최고나이", "보험기간", "납입기간", "최저금액만원", "최고금액만원"}
LINK_KEYS = {"종형ID", "표", "모름"}


# ---------------------------------------------------------------------------
# 일감
# ---------------------------------------------------------------------------

def variant_entries(targets: Mapping[str, Any], codes: Iterable[str]) -> list[dict[str, Any]]:
    """대상 설정(data/targets)에서 공시상품코드가 codes인 종형을 일감의 종형 목록으로. 종형ID는 variants.build와 같은 규칙이다."""
    org = targets["기관코드"]
    wanted = list(codes)
    out = []
    for product in targets["상품"]:
        for v in product["종형"]:
            if v["공시상품코드"] in wanted:
                out.append({
                    "종형ID": ids.variant_id(org, v["공시상품코드"], v["종형명"]),
                    "공시상품코드": v["공시상품코드"],
                    "종형명": v["종형명"],
                    "심사유형": v["심사유형"],
                    "간편고지약칭": v["간편고지약칭"],
                    "비교역할구분": v.get("비교역할구분") or product["비교역할구분"],
                    "환급유형": product.get("환급유형"),
                })
    out.sort(key=lambda e: wanted.index(e["공시상품코드"]))
    return out


def check_task(task: Any) -> list[str]:
    """일감 파일의 꼴 문제."""
    if not isinstance(task, Mapping) or task.get("형식") != TASK_FORMAT:
        return [f"일감의 형식이 {TASK_FORMAT}이 아님"]
    out = []
    if not task.get("일감"):
        out.append("일감 이름이 없음")
    variants = task.get("종형")
    if not isinstance(variants, list) or not variants:
        out.append("종형 목록이 없음")
    else:
        org = task.get("기관코드")
        for v in variants:
            if v.get("종형ID") != ids.variant_id(str(org), str(v.get("공시상품코드")), str(v.get("종형명"))):
                out.append(f"종형ID가 기관코드, 공시상품코드, 종형명으로 만든 값과 다름: {v.get('종형ID')}")
    span = task.get("쪽범위")
    if not (isinstance(span, list) and len(span) == 2 and all(_int(x) for x in span) and span[0] <= span[1]):
        out.append("쪽범위가 [첫쪽, 끝쪽]이 아님")
    return out


# ---------------------------------------------------------------------------
# 꼴 검사
# ---------------------------------------------------------------------------

def _num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _unknowns(items: Any, allowed: Sequence[str]) -> list[str]:
    if not isinstance(items, list):
        return ["모름이 목록이 아님"]
    out = []
    for b in items:
        if not isinstance(b, Mapping) or set(b) - {"칸", "이유"} or b.get("칸") not in allowed \
                or not isinstance(b.get("이유"), str) or not b["이유"].strip() or len(b["이유"]) > _REASON:
            out.append(f"모름 항목이 {{칸({', '.join(allowed)}), 이유({_REASON}자 이하)}}가 아님")
    return out


def line_key(line: Mapping[str, Any]) -> tuple[str, str, str]:
    """줄을 가르는 열쇠: (성별, 보험기간, 납입기간). 기간 글자는 빈칸과 전각을 맞춘다."""
    return (str(line.get("성별")), ids.normalize(line.get("보험기간") or ""), ids.normalize(line.get("납입기간") or ""))


def check_line(line: Any) -> list[str]:
    if not isinstance(line, Mapping):
        return ["줄이 객체가 아님"]
    out = [f"정의되지 않은 칸: {k}" for k in sorted(set(line) - LINE_KEYS)]
    if not _int(line.get("쪽")):
        out.append("쪽이 정수가 아님")
    if line.get("성별") not in SEXES:
        out.append(f"성별이 허용값이 아님: {line.get('성별')!r}")
    if not isinstance(line.get("보험기간"), str) or not _TERM.match(ids.normalize(line["보험기간"])):
        out.append(f"보험기간이 '80세만기', '20년만기', '20년', '종신' 꼴이 아님: {line.get('보험기간')!r}")
    if not isinstance(line.get("납입기간"), str) or not _PAY.match(ids.normalize(line["납입기간"])):
        out.append(f"납입기간이 '20년납', '60세납', '전기납', '일시납' 꼴이 아님: {line.get('납입기간')!r}")
    for name in ("최저나이", "최고나이"):
        if not (_int(line.get(name)) and 0 <= line[name] < 150):
            out.append(f"{name}가 0 이상의 정수가 아님")
    formula = line.get("최고나이식", "")
    if not isinstance(formula, str) or (formula and not _FORMULA.match(ids.normalize(formula))):
        out.append(f"최고나이식이 '' 또는 '76-납입기간', '80-보험기간' 꼴이 아님: {formula!r}")
    return out


def check_limit(limit: Any) -> list[str]:
    if not isinstance(limit, Mapping):
        return ["한도 항목이 객체가 아님"]
    out = [f"한도의 정의되지 않은 칸: {k}" for k in sorted(set(limit) - LIMIT_KEYS)]
    if not _int(limit.get("쪽")):
        out.append("한도의 쪽이 정수가 아님")
    if limit.get("문서") not in DOCS:
        out.append(f"한도의 문서가 허용값이 아님: {limit.get('문서')!r}")
    if not (_int(limit.get("최저나이")) and limit["최저나이"] >= 0):
        out.append("한도의 최저나이가 0 이상의 정수가 아님")
    top = limit.get("최고나이")
    if top is not None and not (_int(top) and top >= 0):
        out.append("한도의 최고나이가 정수나 null이 아님")
    for name, pattern in (("보험기간", _TERM), ("납입기간", _PAY)):
        value = limit.get(name, "")
        if not isinstance(value, str) or (value and not pattern.match(ids.normalize(value))):
            out.append(f"한도의 {name}이 '' 또는 기간 꼴이 아님: {value!r}")
    low, high = limit.get("최저금액만원"), limit.get("최고금액만원")
    if low is not None and not (_num(low) and low > 0):
        out.append("한도의 최저금액만원이 양수나 null이 아님")
    if not (_num(high) and high > 0):
        out.append("한도의 최고금액만원이 양수가 아님")
    return out


def check_table(table: Any) -> list[str]:
    """표 하나의 꼴 문제(줄과 한도 포함)."""
    if not isinstance(table, Mapping):
        return ["표가 객체가 아님"]
    out = [f"정의되지 않은 칸: {k}" for k in sorted(set(table) - TABLE_KEYS)]
    name = table.get("표")
    if not isinstance(name, str) or not name.strip() or len(name) > _NAME:
        out.append(f"표 이름이 {_NAME}자 이하의 글이 아님")
    blanks = table.get("모름", [])
    out += _unknowns(blanks, UNKNOWN_FIELDS)
    unknown = {b.get("칸") for b in blanks if isinstance(b, Mapping)} if isinstance(blanks, list) else set()
    if not _int(table.get("근거쪽")):
        out.append("근거쪽이 정수가 아님")
    words = table.get("근거낱말")
    if not isinstance(words, list) or not (1 <= len(words) <= _WORDS) \
            or any(not isinstance(w, str) or not w.strip() or len(w) > _SHORT for w in words):
        out.append(f"근거낱말이 {_SHORT}자 이하 낱말 1~{_WORDS}개의 목록이 아님")
    lines = table.get("줄")
    if not isinstance(lines, list):
        out.append("줄이 목록이 아님")
    else:
        seen: set[tuple[str, str, str]] = set()
        for i, line in enumerate(lines, 1):
            errs = check_line(line)
            out += [f"줄 {i}: {e}" for e in errs]
            if not errs:
                key = line_key(line)
                if key in seen:
                    out.append(f"줄 {i}: 성별, 보험기간, 납입기간이 같은 줄이 두 번 나옴")
                seen.add(key)
        if not lines and "줄" not in unknown and "표" not in unknown:
            out.append("줄이 비었는데 모름에 줄이나 표의 이유가 없음")
        sexes = {line.get("성별") for line in lines if isinstance(line, Mapping)}
        if "구분없음" in sexes and sexes & {"남자", "여자"}:
            out.append("성별 구분없음 줄과 남자, 여자 줄이 한 표에 섞여 있음")
    none = table.get("한도없음")
    limits = table.get("한도")
    if not isinstance(none, bool):
        out.append("한도없음이 참거짓이 아님")
    if not isinstance(limits, list):
        out.append("한도가 목록이 아님")
    else:
        for i, limit in enumerate(limits, 1):
            out += [f"한도 {i}: {e}" for e in check_limit(limit)]
        if none is True and limits:
            out.append("한도없음이 참인데 한도가 있음")
        if none is False and not limits and "한도" not in unknown:
            out.append("한도없음이 거짓인데 한도가 비었고 모름에 한도의 이유가 없음")
    return out


def parse_reading(data: Any) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    """판독 파일 하나를 ({표 이름: 표}, {종형ID: 종형 줄}, 문제)로 읽는다. 꼴이 틀린 표는 빼고 문제로 돌려준다."""
    if not isinstance(data, Mapping) or data.get("형식") != FORMAT \
            or not isinstance(data.get("표"), list) or not isinstance(data.get("종형"), list):
        return {}, {}, [f"판독 파일의 형식이 {FORMAT}이 아니거나 표, 종형 목록이 없음"]
    problems: list[str] = []
    tables: dict[str, dict[str, Any]] = {}
    for table in data["표"]:
        errs = check_table(table)
        name = table.get("표") if isinstance(table, Mapping) else None
        if errs:
            problems.append(f"표 {name}: {'; '.join(errs)}")
            continue
        if name in tables:
            problems.append(f"표 {name}: 이름이 두 번 나옴")
            continue
        tables[name] = {"모름": [], **table}
    links: dict[str, dict[str, Any]] = {}
    for link in data["종형"]:
        if not isinstance(link, Mapping) or set(link) - LINK_KEYS or not isinstance(link.get("종형ID"), str) \
                or not isinstance(link.get("표", ""), str):
            problems.append(f"종형 줄이 {{종형ID, 표, 모름}}이 아님: {link!r}"[:200])
            continue
        vid = link["종형ID"]
        errs = _unknowns(link.get("모름", []), UNKNOWN_FIELDS)
        if errs:
            problems.append(f"종형 {vid}: {'; '.join(errs)}")
            continue
        if vid in links:
            problems.append(f"종형 {vid}: 두 번 나옴")
            continue
        entry = {"표": "", "모름": [], **link}
        if entry["표"] and entry["표"] not in tables and not any(p.startswith(f"표 {entry['표']}:") for p in problems):
            problems.append(f"종형 {vid}: 표 '{entry['표']}'이 표 목록에 없음")
        if not entry["표"] and not entry["모름"]:
            problems.append(f"종형 {vid}: 표가 비었는데 모름에 이유가 없음")
        links[vid] = entry
    return tables, links, problems


def check_file(task: Mapping[str, Any], answer: Any) -> list[str]:
    """판독 파일 하나의 꼴 문제, 빠지거나 남는 종형, 쓰지 않은 표. 기계 검사는 돌리지 않는다(판독자가 값을 검사에 맞추지 않게)."""
    tables, links, problems = parse_reading(answer)
    if isinstance(answer, Mapping) and answer.get("일감") != task.get("일감"):
        problems.append(f"일감 이름이 다름: {answer.get('일감')!r}")
    order = [v["종형ID"] for v in task.get("종형") or []]
    absent = [v for v in order if v not in links]
    extra = [v for v in links if v not in order]
    if absent:
        problems.append(f"판독이 없는 종형 {len(absent)}개: {', '.join(absent)}")
    if extra:
        problems.append(f"일감에 없는 종형: {', '.join(extra)}")
    used = {link["표"] for link in links.values()}
    idle = [name for name in tables if name not in used]
    if idle:
        problems.append(f"어느 종형도 쓰지 않는 표: {', '.join(idle)}")
    return problems


# ---------------------------------------------------------------------------
# 값 맞추기와 견주기
# ---------------------------------------------------------------------------

def _unknown_of(table: Mapping[str, Any] | None, link: Mapping[str, Any] | None) -> set[str]:
    out = {b.get("칸") for b in (link or {}).get("모름") or []}
    out |= {b.get("칸") for b in (table or {}).get("모름") or []}
    if not table or "표" in out:
        out |= set(UNKNOWN_FIELDS)
    return out


def _limit_tuple(x: Mapping[str, Any]) -> tuple[Any, ...]:
    low = x.get("최저금액만원")
    return (x["최저나이"], x.get("최고나이"), ids.normalize(x.get("보험기간") or ""), ids.normalize(x.get("납입기간") or ""),
            float(low) if low is not None else None, float(x["최고금액만원"]))


def normalized(table: Mapping[str, Any] | None, link: Mapping[str, Any] | None) -> dict[str, Any]:
    """종형 하나의 견줄 값. 줄은 {열쇠: (최저나이, 최고나이)}, 한도는 (한도없음, 한도 묶음). 모름인 칸은 UNKNOWN."""
    unknown = _unknown_of(table, link)
    lines = {line_key(x): (x["최저나이"], x["최고나이"]) for x in (table or {}).get("줄") or []}
    limits = (bool((table or {}).get("한도없음")), tuple(sorted(map(_limit_tuple, (table or {}).get("한도") or []),
                                                               key=repr)))
    return {"줄": UNKNOWN if "줄" in unknown else lines, "한도": UNKNOWN if "한도" in unknown else limits}


def compare_one(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, str]:
    """두 판독의 칸별 상태. a, b는 normalized의 결과."""
    out = {}
    for name in ("줄", "한도"):
        x, y = a[name], b[name]
        if x == UNKNOWN and y == UNKNOWN:
            out[name] = BOTH_UNKNOWN
        elif UNKNOWN in (x, y):
            out[name] = ONE_UNKNOWN
        else:
            out[name] = SAME if x == y else DIFF
    return out


def line_differences(a: Mapping[str, Any], b: Mapping[str, Any]) -> list[str]:
    """두 판독의 줄이 어디서 갈리는가. 열쇠가 한쪽에만 있는 줄과 나이가 다른 줄."""
    if UNKNOWN in (a["줄"], b["줄"]):
        return []
    out = []
    for key in sorted(set(a["줄"]) | set(b["줄"])):
        label = "/".join(key)
        x, y = a["줄"].get(key), b["줄"].get(key)
        if x is None or y is None:
            out.append(f"{label}: 한쪽에만 있음")
        elif x != y:
            out.append(f"{label}: {x[0]}~{x[1]}세와 {y[0]}~{y[1]}세")
    return out


# ---------------------------------------------------------------------------
# 기계 검사
# ---------------------------------------------------------------------------

_DASH = re.compile("[‐-―−－]")


def _flat(text: str) -> str:
    """쪽 글자를 견주기 좋게: 전각을 맞추고, 줄표를 "-"로, 빈칸과 쉼표를 뗀다."""
    return re.sub(r"[\s,]", "", _DASH.sub("-", unicodedata.normalize("NFKC", text or "")))


def _age_in(age: int, text: str) -> bool:
    return re.search(rf"(?<!\d){age}세", _flat(text)) is not None


def _years(term: str, pay: str, ref: str) -> int | None:
    """식이 빼는 기간의 햇수. 납입기간이 "전기납"이면 보험기간의 햇수(N년만기, N년)를 쓴다."""
    term, pay = ids.normalize(term), ids.normalize(pay)
    by_term = re.fullmatch(r"(\d+)년(?:만기)?", term)
    if ref == "보험기간":
        return int(by_term.group(1)) if by_term else None
    m = re.fullmatch(r"(\d+)년납", pay)
    if m:
        return int(m.group(1))
    return int(by_term.group(1)) if pay == "전기납" and by_term else None


def formula_value(line: Mapping[str, Any]) -> int | None:
    """최고나이식으로 계산한 최고나이. 식이 없거나 기간의 햇수를 읽지 못하면 None."""
    m = _FORMULA.match(ids.normalize(line.get("최고나이식") or ""))
    if not m:
        return None
    years = _years(line["보험기간"], line["납입기간"], m.group(2))
    return int(m.group(1)) - years if years is not None else None


def _money_in(manwon: float, text: str) -> bool:
    return any(abs(value - manwon) < 1e-6 for _, value in B._amounts(_flat(text)))


def machine_checks(table: Mapping[str, Any], pages: Mapping[str, Mapping[int, str]] | None,
                   span: Sequence[int] | None = None) -> tuple[list[str], list[str]]:
    """표 하나의 (문제, 표시). 둘 다 비어야 자동 확정된다.

    문제: 근거낱말과 나이, 기간, 금액의 글자가 그 쪽에 없거나, 최고나이식의 숫자가 쪽에 없거나 계산이 틀리거나,
    최저나이가 최고나이보다 크거나, "N세만기"인데 최고나이가 N 이상이거나, 한도 나이 구간이 겹치는 것.
    표시: 값을 읽은 쪽이 일감의 쪽 범위 밖이거나 근거쪽보다 앞인 것, 근거쪽부터 값을 읽은 쪽까지 "기본계약"이나 "주계약" 글자가 없는 것.
    pages: {문서: {쪽: 글자}}. 줄은 사업방법서의 쪽이고, 한도는 그 항목의 문서다. 글자가 없으면 검사하지 못한 것을 문제로 남긴다.
    """
    problems: list[str] = []
    marks: list[str] = []
    method = (pages or {}).get("사업방법서") or {}

    def page(doc: str, n: int) -> str | None:
        text = ((pages or {}).get(doc) or {}).get(n)
        if text is None:
            message = f"글자: {doc} {n}쪽 글자가 없어 대조하지 못함"
            if message not in problems:
                problems.append(message)
        return text

    head = table["근거쪽"]
    text = page("사업방법서", head)
    if text is not None:
        flat = _flat(text)
        for word in table["근거낱말"]:
            if _flat(word) not in flat:
                problems.append(f"근거: 근거낱말 '{word}'이 {head}쪽에 없음")
    lines = table.get("줄") or []
    for line in lines:
        label = "/".join(line_key(line))
        lo, hi, n = line["최저나이"], line["최고나이"], line["쪽"]
        if lo > hi:
            problems.append(f"나이: {label} 최저나이 {lo}세가 최고나이 {hi}세보다 큼")
        end = re.fullmatch(r"(\d+)세만기", ids.normalize(line["보험기간"]))
        if end and hi >= int(end.group(1)):
            problems.append(f"나이: {label} 최고나이 {hi}세가 만기 나이 이상임")
        if span and not (span[0] <= n <= span[1]):
            marks.append(f"쪽: {label} 값을 읽은 {n}쪽이 일감의 쪽 범위 밖")
        if n < head:
            marks.append(f"쪽: {label} 값을 읽은 {n}쪽이 근거쪽 {head}쪽보다 앞")
        text = page("사업방법서", n)
        if text is None:
            continue
        flat = _flat(text)
        if not _age_in(lo, text):
            problems.append(f"나이: {label} 최저나이 {lo}세가 {n}쪽에 없음")
        formula = ids.normalize(line.get("최고나이식") or "")
        if formula:
            base, ref = _FORMULA.match(formula).groups()
            if re.search(rf"(?<!\d){base}-{ref[:1]}", flat) is None:
                problems.append(f"식: {label} 최고나이식의 '{base}-{ref[:1]}…'이 {n}쪽에 없음")
            value = formula_value(line)
            if value is None:
                problems.append(f"식: {label} 식이 빼는 {ref}의 햇수를 읽을 수 없음")
            elif value != hi:
                problems.append(f"식: {label} 최고나이 {hi}세가 식으로 계산한 {value}세와 다름")
        elif not _age_in(hi, text):
            problems.append(f"나이: {label} 최고나이 {hi}세가 {n}쪽에 없음")
        for name in ("보험기간", "납입기간"):
            if _flat(line[name]) not in flat:
                problems.append(f"기간: {label} {name} '{line[name]}'이 {n}쪽에 없음")
    if lines and method:
        last = max(line["쪽"] for line in lines)
        if not any(re.search(r"기본계약|주계약", method.get(n) or "") for n in range(min(head, last), max(head, last) + 1)):
            marks.append(f"기본계약: {head}~{last}쪽에 '기본계약'이나 '주계약' 글자가 없음")
    limits = table.get("한도") or []
    for i, x in enumerate(limits, 1):
        label = f"한도 {i}"
        low, high = x.get("최저금액만원"), x["최고금액만원"]
        if low is not None and low > high:
            problems.append(f"한도: {label} 최저금액이 최고금액보다 큼")
        if x.get("최고나이") is not None and x["최저나이"] > x["최고나이"]:
            problems.append(f"한도: {label} 나이 구간의 아래가 위보다 큼")
        text = page(x["문서"], x["쪽"])
        if text is None:
            continue
        for amount in (low, high):
            if amount is not None and not _money_in(float(amount), text):
                problems.append(f"한도: {label} 금액 {amount}만원이 {x['문서']} {x['쪽']}쪽에 없음")
        for age in (x["최저나이"], x.get("최고나이")):
            if age and not _age_in(age, text):
                problems.append(f"한도: {label} 나이 {age}세가 {x['문서']} {x['쪽']}쪽에 없음")
        for name in ("보험기간", "납입기간"):
            if x.get(name) and _flat(x[name]) not in _flat(text):
                problems.append(f"한도: {label} {name} '{x[name]}'이 {x['문서']} {x['쪽']}쪽에 없음")
    for i, x in enumerate(limits):
        for y in limits[i + 1:]:
            same_scope = all(ids.normalize(x.get(k) or "") == ids.normalize(y.get(k) or "") for k in ("보험기간", "납입기간"))
            x_hi = x["최고나이"] if x.get("최고나이") is not None else C.MAX_AGE
            y_hi = y["최고나이"] if y.get("최고나이") is not None else C.MAX_AGE
            if same_scope and x["최저나이"] <= y_hi and y["최저나이"] <= x_hi:
                problems.append("한도: 기간이 같은 한도의 나이 구간이 겹침")
    return problems, marks


_TYPE_WORD = re.compile(r"\d+[형종]")


def title_marks(table: Mapping[str, Any], variant_name: str) -> list[str]:
    """표가 이 종형의 것인지 근거낱말과 종형명으로 본다. 종형명에 든 근거낱말이 하나도 없거나,
    "2형", "1종"처럼 형과 종 번호를 적은 근거낱말이 종형명에 없으면 표시한다(다른 형의 표를 고른 것일 수 있다)."""
    name = _flat(variant_name)
    words = [_flat(w) for w in table.get("근거낱말") or []]
    out = []
    if words and not any(w in name for w in words):
        out.append("근거: 근거낱말이 종형명에 하나도 없음")
    out += [f"근거: 근거낱말 '{w}'의 형이나 종 번호가 종형명에 없음" for w in words
            if _TYPE_WORD.search(w) and not all(t in name for t in _TYPE_WORD.findall(w))]
    return out


# ---------------------------------------------------------------------------
# 일감 하나 견주기
# ---------------------------------------------------------------------------

def stored_value(table: Mapping[str, Any] | None, link: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """값 파일에 싣는 종형 하나의 판독 값. 원문 구절과 모름 이유는 싣지 않는다(모름은 칸 이름만)."""
    if link is None:
        return None
    unknown = sorted(c for c in _unknown_of(table, link) if c)
    if table is None:
        return {"표": link.get("표") or "", "모름": unknown}
    return {
        "표": table["표"], "근거쪽": table["근거쪽"], "근거낱말": list(table["근거낱말"]),
        "줄": sorted(({k: x.get(k, "") for k in ("쪽", "성별", "보험기간", "납입기간", "최저나이", "최고나이", "최고나이식")}
                     for x in table["줄"]), key=lambda x: (line_key(x), x["쪽"])),
        "한도없음": table["한도없음"],
        "한도": [{"최고나이": None, "보험기간": "", "납입기간": "", "최저금액만원": None, **x} for x in table["한도"]],
        "모름": unknown,
    }


def compare_task(task: Mapping[str, Any], answers: Mapping[str, Any], names: Sequence[str],
                 pages: Mapping[str, Mapping[int, str]] | None = None) -> dict[str, Any]:
    """일감 하나와 판독 둘({판독 이름: 판독 파일 내용})을 견준다. pages는 {문서: {쪽: 글자}}."""
    a_name, b_name = names
    parsed: dict[str, tuple[dict, dict]] = {}
    errors: dict[str, list[str]] = {}
    for name in names:
        tables, links, problems = parse_reading(answers.get(name))
        problems += [p for p in check_file(task, answers.get(name)) if p not in problems
                     and not p.startswith("판독 파일의 형식")]
        parsed[name], errors[name] = (tables, links), problems
    span = task.get("쪽범위")
    checked: dict[tuple[str, str], tuple[list[str], list[str]]] = {}
    lines = []
    for v in task["종형"]:
        vid = v["종형ID"]
        values, checks, chosen = {}, {}, {}
        for name in names:
            tables, links = parsed[name]
            link = links.get(vid)
            table = tables.get(link["표"]) if link and link.get("표") else None
            chosen[name] = (table, link)
            values[name] = normalized(table, link) if link else {"줄": UNKNOWN, "한도": UNKNOWN}
            if table is not None:
                key = (name, table["표"])
                if key not in checked:
                    checked[key] = machine_checks(table, pages, span)
                problems, marks = checked[key]
                marks = marks + title_marks(table, v.get("종형명") or "")
            else:
                problems, marks = ([] if link else ["판독 없음"]), []
            checks[name] = {"문제": list(problems), "표시": list(marks)}
        states = compare_one(values[a_name], values[b_name])
        head = {name: (chosen[name][0] or {}).get("근거쪽") for name in names}
        same = all(s == SAME for s in states.values())
        clean = all(not checks[x]["문제"] and not checks[x]["표시"] for x in names)
        unknown = any(_unknown_of(*chosen[x]) for x in names)
        auto = CONFIRMED if same and clean and not unknown else NEEDS_JUDGE
        lines.append({
            "일감": task.get("일감"), "종형ID": vid, "공시상품코드": v.get("공시상품코드"), "종형명": v.get("종형명"),
            a_name: stored_value(*chosen[a_name]) if chosen[a_name][1] else None,
            b_name: stored_value(*chosen[b_name]) if chosen[b_name][1] else None,
            "일치": {**states, "근거쪽": SAME if head[a_name] == head[b_name] and head[a_name] is not None else DIFF},
            "다른줄": line_differences(values[a_name], values[b_name]),
            "기계검사": checks,
            "자동판정": auto,
            "판정": CONFIRMED if auto == CONFIRMED else "",
            "판정값": None,
        })
    return {"일감": task.get("일감"), "판독": list(names), "형식 문제": errors, "줄": lines}


def final_value(line: Mapping[str, Any], names: Sequence[str]) -> dict[str, Any] | None:
    """값 파일의 종형 한 줄에서 행을 만들 값. 판정이 확정이면 첫째 판독, 판독 이름이면 그 판독, 수정이면 판정값. 그 밖은 None."""
    verdict = line.get("판정") or ""
    if verdict == CONFIRMED:
        return line.get(names[0])
    if verdict in names:
        return line.get(verdict)
    if verdict == "수정":
        return line.get("판정값")
    return None


# ---------------------------------------------------------------------------
# 행 만들기
# ---------------------------------------------------------------------------

_SEX_CODE = {"남자": "M", "여자": "F", "구분없음": ""}


@dataclass
class Built:
    conditions: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    done: list[str] = field(default_factory=list)          # 행을 만든 종형ID


def _money_text(manwon: float) -> str:
    return f"{int(manwon) if float(manwon).is_integer() else manwon}만원"


def _band_text(lo: int, hi: int | None) -> str:
    return f"{lo}세 이상" if hi is None else f"{lo}세~{hi}세"


def _scope_fits(limit: Mapping[str, Any], line: Mapping[str, Any]) -> bool:
    return all(not limit.get(k) or ids.normalize(limit[k]) == ids.normalize(line[k]) for k in ("보험기간", "납입기간"))


def build_rows(variants: Sequence[Mapping[str, Any]], finals: Mapping[str, Mapping[str, Any] | None]) -> Built:
    """종형마다 확정된 값(stored_value 꼴: 줄, 한도)으로 sys_가입조건 행을 만든다. 주계약 행이라 특약ID는 비운다.

    행과 조건행ID는 conditions.build_rows가 만든다(나이 구간에 따라 한도가 갈리면 한도가 바뀌는 나이에서 행을 나눈다).
    한도는 보험기간, 납입기간이 비었거나 그 줄과 같은 것만 그 줄에 건다. 값이 없거나 줄이 없는 종형은 행을 만들지 않고 남긴다.
    """
    out = Built()
    for v in variants:
        vid = v["종형ID"]
        value = finals.get(vid)
        if not value or not value.get("줄"):
            out.notes.append(f"{vid}: 확정된 가입나이 줄이 없어 행을 만들지 않음")
            continue
        target = C.Target(vid, v.get("종형명") or "", {}, ids.rider_id(vid, MAIN_NAME))
        seen: set[str] = set()
        for line in value["줄"]:
            item = C.AgeItem([MAIN_NAME], "", "", _SEX_CODE[line["성별"]], f"{line['최저나이']}~{line['최고나이']}세",
                             ids.normalize(line["보험기간"]), ids.normalize(line["납입기간"]))
            limits = [C.LimitItem([MAIN_NAME], _band_text(x["최저나이"], x.get("최고나이")),
                                  _money_text(x.get("최저금액만원") or x["최고금액만원"]), _money_text(x["최고금액만원"]), "")
                      for x in value.get("한도") or [] if _scope_fits(x, line)]
            got = C.build_rows([target], [item], limits, [])
            out.notes += [f"{vid}: {n}" for n in got.notes]
            for row in got.conditions:
                if row["조건행ID"] not in seen:
                    seen.add(row["조건행ID"])
                    out.conditions.append(row)
        out.done.append(vid)
    out.notes = list(dict.fromkeys(out.notes))
    return out
