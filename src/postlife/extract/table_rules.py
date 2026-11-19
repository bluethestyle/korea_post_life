"""급부 표의 문구가 규칙적인 요약서에서, 모델 없이 코드 규칙만으로 급부를 읽는다.

tables.py가 PDF의 급부 표를 특별약관(조각)·세부보장 단위로 정리해 두면, 이 파일이 세부보장마다
지급률·감액·면책·지급 한도를 읽어 sys_특약·sys_급부 행으로 바꾼다. 삼성화재 요약서가 이런 문서다.
지급금액 칸은 대개 "가입금액"이고, 감액·면책·한도는 지급사유 칸에 "※" 줄과 괄호로 적혀 있다.

    ※ 최초 보험가입후 1년 미만에 보험금 지급사유가 발생한 경우 50% 감액 지급      → 12개월 미만 0.5
    ※ … 180일 미만에 … 가입금액의 10% 지급, 1년 미만(180일미만 제외)에 … 50% 지급   → 6개월 미만 0.1, 12개월 미만 0.5
    ※ 암의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난날의 다음날임 → 면책 90일
    … 진단 확정된 경우 (최초 1회한 지급)                                        → 한도 "최초 1회한 지급"

금액이 아니라 비율로 적힌 표이므로 행에는 가입금액 100만원당 지급액을 적는다
(기준가입금액만원 100, 기준지급금액만원 = 지급률). 20%면 20이다.

규칙은 아는 꼴만 읽는다. 감액 문장이 있는데 꼴이 낯설거나, 보장개시일 문장에서 날수를 읽지 못했거나,
대상마다 값이 다른데 줄로 나누지 못했거나, 지급금액이 비율이 아니면 그 줄에 "확신 없음" 사유를 붙인다.
사유가 붙은 줄은 판정 모델이나 사람이 다시 본다. 읽은 값마다 근거 문장을 함께 돌려준다.

쓰는 법

    readings = read_cover("암 진단비", "보장개시일 이후 … (최초 1회한 지급)\\n※ 암의 보장개시일은 …", "가입금액")
    out = build_rows(variant_id, tables.read_riders("조각.json"), renewal_years=20)
    out.riders, out.benefits        # sys_특약, sys_급부 행
    out.doubts                      # 급부ID → 확신 없음 사유
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Sequence

from .. import ids
from .tables import Rider

BASE_AMOUNT = 100.0          # 기준가입금액만원. 지급률(%)이 그대로 기준지급금액만원이 된다
DOC_KIND = "요약서"

# 확신 없음 사유. 뒤에 ": 자세한 내용"이 붙기도 한다. 분포를 셀 때는 doubt_kind로 앞부분만 본다
D_AMOUNT = "지급금액이 가입금액의 비율이 아님"
D_BASIS = "지급사유에 다른 지급 기준이 적힘"
D_CUT = "감액 문장을 읽지 못함"
D_CUT_ODD = "감액 조건이 표준 꼴과 다름"
D_WAIT = "보장개시일 문장을 읽지 못함"
D_SPLIT = "대상별로 값이 다른데 줄로 나누지 못함"
D_NAME = "이름의 표시와 읽은 값이 다름"
D_UNREAD = "읽지 못한 조건 문구가 있음"
D_BUNDLE = "한 줄에 세부보장 여럿이 묶여 있음"


def doubt_kind(doubt: str) -> str:
    """사유에서 자세한 내용을 뗀 앞부분."""
    return doubt.split(":", 1)[0]


@dataclass(frozen=True)
class Step:
    """감액 구간 하나. "180일 미만 10% 지급"이면 months 6, rate 0.1."""
    months: int
    rate: float                 # 그 기간 안에 받는 비율(0~1). "50% 감액"이면 0.5, "75% 감액"이면 0.25
    period: str = ""            # 원문에 적힌 기간. 예: "180일 미만"


@dataclass(frozen=True)
class Reading:
    """세부보장 한 줄에서 읽은 값. 대상에 따라 면책·감액·지급률이 다르면 대상마다 한 줄이다."""
    name: str                               # 보장명
    target: str = ""                        # 대상별로 나눈 줄의 대상. 예: "기타피부암·갑상선암". 나누지 않았으면 빈 문자열
    percent: float | None = 100.0           # 감액이 끝난 뒤의 지급률(%). 비율로 읽을 수 없으면 None
    steps: tuple[Step, ...] = ()            # 감액 구간. 짧은 기간부터, 많아야 둘
    waiting_days: int = 0                   # 면책 날수. 보장개시일이 계약일이면 0
    limit: str = ""                         # 지급 한도 문구(원문). 여럿이면 " / "로 잇는다
    exception: str = ""                     # 감액이 일부 경우에만 걸릴 때 그 감액 문장(원문)
    note: str = ""                          # 금액 예외·비고(원문). 체증 문구, 비율이 아닌 지급금액 등
    evidence: dict[str, str] = field(default_factory=dict)      # 칸 이름 → 그 값을 읽은 근거 문장
    doubts: tuple[str, ...] = ()            # 확신 없음 사유. 비어 있으면 규칙이 확신하는 줄이다

    @property
    def label(self) -> str:
        """원시급부명. 대상별로 나눈 줄은 이름 뒤에 대상을 괄호로 붙인다."""
        return f"{self.name}({self.target})" if self.target else self.name

    @property
    def sure(self) -> bool:
        return not self.doubts


# ---------------------------------------------------------------------------
# 글자 다듬기
# ---------------------------------------------------------------------------

_SPACES = re.compile(r"[ \t\u00a0]+")
_DOTS = re.compile(r"[∙ㆍ•‧・]")
_OPEN, _CLOSE = "(「", ")」"
_INNER = re.compile(r"·\s[^:\n]*:")          # 칸 안의 작은 표를 풀어 적은 줄. tables.py가 "· 이름: 값"으로 적는다


def _clean(text: str | None) -> str:
    """빈칸을 하나로 줄이고 가운뎃점 모양을 맞춘다. 줄바꿈은 둔다."""
    return "\n".join(_SPACES.sub(" ", _DOTS.sub("·", line)).strip() for line in (text or "").split("\n")).strip()


def _flat(text: str) -> tuple[str, list[int]]:
    """빈칸을 모두 뗀 글과, 그 글자마다 원래 글에서의 자리.

    표에서는 "효력회 복", "지난 날"처럼 낱말 가운데 빈칸이 끼어든다. 꼴은 빈칸을 뗀 글에서 찾고,
    대상 이름처럼 띄어쓰기가 필요한 글자는 자리를 되짚어 원래 글에서 꺼낸다.
    """
    chars, at = [], []
    for i, ch in enumerate(text):
        if not ch.isspace():
            chars.append(ch)
            at.append(i)
    return "".join(chars), at


def _slice(text: str, at: list[int], start: int, end: int) -> str:
    """빈칸을 뗀 글의 [start, end) 구간을 원래 글에서 꺼낸다."""
    return text[at[start]:at[end - 1] + 1].strip() if end > start else ""


def _groups(text: str) -> list[tuple[int, int]]:
    """맨 바깥 괄호 묶음의 자리 [(여는 괄호, 닫는 괄호 다음)]. 닫히지 않은 괄호는 글 끝까지로 본다."""
    out, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            if depth == 0:
                out.append((start, i + 1))
    if depth:
        out.append((start, len(text)))
    return out


def _mask(text: str) -> str:
    """괄호 묶음을 같은 길이의 빈 글자로 가린다. 괄호 밖의 글만 볼 때 쓴다."""
    chars = list(text)
    for start, end in _groups(text):
        chars[start:end] = "\x00" * (end - start)
    return "".join(chars)


def _items(text: str) -> tuple[str, ...]:
    """"기타피부암, 갑상선암 및 제자리암" → ("기타피부암", "갑상선암", "제자리암"). 괄호·낫표 안에서는 가르지 않는다."""
    parts, depth, start, i = [], 0, 0, 0
    while i < len(text):
        ch = text[i]
        if ch in _OPEN:
            depth += 1
        elif ch in _CLOSE:
            depth = max(depth - 1, 0)
        elif depth == 0:
            cut = 1 if ch == "," else next((len(w) for w in (" 및 ", " 또는 ") if text.startswith(w, i)), 0)
            if cut:
                parts.append(text[start:i])
                start = i = i + cut
                continue
        i += 1
    parts.append(text[start:])
    return tuple(p for p in (_bare(x) for x in parts) if p)


def _bare(text: str) -> str:
    """앞뒤 빈칸과 이름 전체를 싼 낫표를 뗀다."""
    text = text.strip()
    while len(text) >= 2 and text[0] == "「" and text[-1] == "」" and "「" not in text[1:-1]:
        text = text[1:-1].strip()
    return text


def _unique(texts: Iterable[str]) -> list[str]:
    """띄어쓰기만 다른 글은 먼저 나온 것 하나만 남긴다."""
    seen: dict[str, str] = {}
    for text in texts:
        seen.setdefault(re.sub(r"\s", "", text), text)
    return list(seen.values())


def _key(items: Iterable[str]) -> frozenset[str]:
    """대상 묶음을 서로 맞춰 볼 수 있게 줄인 것."""
    return frozenset(re.sub(r"[\s「」]", "", x) for x in items)


def _target(items: Sequence[str]) -> str:
    return "·".join(items)


def _paragraphs(reason: str) -> tuple[str, list[str]]:
    """지급사유 칸을 본문과 "※" 문단들로 나눈다.

    "※" 다음 줄이 "1. …"처럼 이어지면 그 문단에 붙인다. "· 이름: 값" 줄은 칸 안의 작은 표(낱말 풀이)를 풀어 적은
    것이라 어디에 있든 따로 한 문단으로 둔다. 본문이 "(간\\n·담낭…"처럼 가운뎃점 앞에서 줄이 바뀌었으면 붙여 잇는다.
    """
    body, notes = "", []
    for line in _clean(reason).split("\n"):
        if not line:
            continue
        if line.startswith("※"):
            notes.append(line[1:].strip())
        elif _INNER.match(line):
            notes.append(line)
        elif notes:
            notes[-1] += "\n" + line
        else:
            body += line if not body or (line.startswith("·") and not line.startswith("· ")) else " " + line
    return body, notes


# ---------------------------------------------------------------------------
# 지급금액 칸
# ---------------------------------------------------------------------------

_RATE = re.compile(r"(?:해당세부보장의|특별약관보험)?가입금액(?:의(\d+(?:\.\d+)?)%)?")
_GROWTH = (
    re.compile(r"가입후\d+년미만시가입금액의100%를지급하고가입후\d+년이상시가입금액의\d+%"),
    re.compile(r"가입금액(?:의100%)?[을를]매?\d+년마다\d+%씩정액할증한금액"),
)
_BY_TARGET = re.compile(r"^[-▷]\s*(.+?)\s*:\s*(.+)$")
_EXCEPT = re.compile(r"^※\s*단,\s*(.+?)[은는]\s+(.+)$")


@dataclass(frozen=True)
class _Pay:
    percent: float | None = None            # 모든 대상에 같은 지급률. 비율이 아니면 None
    growth: str = ""                        # 기간에 따라 늘어나는 금액 문구(원문)
    by: tuple[tuple[tuple[str, ...], float], ...] = ()     # 대상별 지급률. ((대상들, 지급률), …)
    rest: float | None = None               # "단, ○○은 20%" 꼴에서 그 밖의 대상이 받는 지급률
    raw: str = ""


def _percent(text: str) -> float | None:
    m = _RATE.fullmatch(re.sub(r"\s", "", text))
    return float(m.group(1) or 100) if m else None


def read_amount(amount: str) -> _Pay:
    """지급금액 칸을 읽는다. "가입금액"은 100, "가입금액의 20%"는 20."""
    lines = [x for x in _clean(amount).split("\n") if x]
    raw = " ".join(lines)
    flat = re.sub(r"\s", "", raw)
    if len(lines) == 1 and _percent(raw) is not None:
        return _Pay(percent=_percent(raw), raw=raw)
    if any(p.fullmatch(flat) for p in _GROWTH):
        return _Pay(percent=100.0, growth=raw, raw=raw)
    # "가입금액" 아래에 "※ 단, 기타피부암, 갑상선암은 가입금액의 20%"가 붙은 꼴
    if len(lines) >= 2 and _percent(lines[0]) is not None:
        found = [_EXCEPT.match(x) for x in lines[1:]]
        rates = [_percent(m.group(2)) if m else None for m in found]
        if all(r is not None for r in rates):
            by = tuple((_items(m.group(1)), r) for m, r in zip(found, rates))
            return _Pay(by=by, rest=_percent(lines[0]), raw=raw)
    # "- 유사암 : 가입금액의 20%" / "▷관혈수술 : 가입금액"처럼 대상마다 한 줄씩 적은 꼴
    found = [_BY_TARGET.match(x) for x in lines]
    rates = [_percent(m.group(2)) if m else None for m in found]
    if lines and all(r is not None for r in rates):
        if len(set(rates)) == 1:
            return _Pay(percent=rates[0], raw=raw)
        return _Pay(by=tuple((_items(m.group(1)), r) for m, r in zip(found, rates)), raw=raw)
    return _Pay(raw=raw)


# ---------------------------------------------------------------------------
# 감액 문장
# ---------------------------------------------------------------------------

# 빈칸을 뗀 글에서 찾는다. "1년미만(180일미만제외)에보험금지급사유가발생한경우가입금액의50%지급"
# "181이상~1년 미만에 …"처럼 구간의 아래쪽 끝을 함께 적기도 한다
_STEP = re.compile(
    r"(?:\d+일?이상~)?(?P<n>\d+)(?P<unit>일|개월|년)미만(?:\(\d+일미만제외\))?에(?P<cond>(?:(?!미만).)*?)(?:이|가)?(?:발생한경우|발생시)"
    r"(?:가입금액의)?(?P<pct>\d+)%(?P<kind>감액지급|지급)(?:\((?P<paid>\d+)%지급\))?"
)
# 감액 구간 뒤에 덧붙인 "1년이상 지나고 보험금 지급사유가 발생한 경우 가입금액의 100%지급". 감액이 끝난 뒤를 적은 말이라 값은 없다
_FULL_AFTER = re.compile(r",(?P<n>\d+)(?P<unit>일|개월|년)이상지나고보험금지급사유가발생한경우가입금액의100%지급")
_CUT_SIGN = re.compile(r"감액|미만[^,]*에.*\d+%지급")
_PLAIN_COND = re.compile(r"(?:보험금지급기간중)?보험금지급사유")
_CAUSE_COND = re.compile(r"(?P<who>.+?)(?:으로|로)인한보험금지급사유")       # "질병으로 인한 보험금 지급사유"
_TARGET_COND = re.compile(r"(?P<who>.+?)(?:으로|로)보험금지급사유")          # "유사암으로 보험금 지급사유"
_LEAD_TARGET = re.compile(r"(?P<who>.+?)(?:의경우|은|는)")


@dataclass(frozen=True)
class _Cut:
    """감액 문장 하나를 읽은 것."""
    steps: tuple[Step, ...]
    source: str
    who: tuple[str, ...] = ()       # 이 감액이 걸리는 대상이나 원인. 모두에게 걸리면 빈 튜플
    led: bool = False               # 대상이 문장 앞에 적혔는가("뇌질환 및 심질환은 …"). 이런 문장이 여럿이면 대상별 줄로 나눈다
    cause: bool = False             # who가 "질병으로 인한"처럼 원인인가
    doubts: tuple[str, ...] = ()


def _months(n: int, unit: str) -> tuple[int, bool]:
    """(개월 수, 딱 떨어지는가). 180일은 6, 90일은 3, 1년은 12."""
    if unit == "년":
        return n * 12, True
    if unit == "개월":
        return n, True
    return max(1, round(n / 30)), n % 30 == 0


def read_cut(note: str) -> _Cut | None:
    """"※" 문단 하나가 감액 문장이면 읽는다. 감액 문장이 아니면 None."""
    flat, at = _flat(note)
    found = list(_STEP.finditer(flat))
    if not found:
        return _Cut((), note, doubts=(D_CUT,)) if _CUT_SIGN.search(flat) else None
    doubts: list[str] = []
    steps: list[Step] = []
    who: tuple[str, ...] = ()
    led = cause = False
    # 문장 앞머리. "최초 보험가입후"만 있으면 모두에게 걸리는 감액이고, "뇌질환 및 심질환은 …"이면 그 대상에만 걸린다
    # "보장개시일부터 최초 보험가입후 1년 미만에"도 가입 후 1년이 기준이다(보장개시일 전에는 어차피 지급하지 않는다)
    lead = re.sub(r"(?:보장개시일부터)?(?:최초)?보험가입후$", "", flat[:found[0].start()])
    if lead:
        m = _LEAD_TARGET.fullmatch(lead)
        if m:
            who, led = _items(_slice(note, at, m.start("who"), m.end("who"))), True
        else:
            doubts.append(f"{D_CUT_ODD}: 문장 앞의 \"{_slice(note, at, 0, len(lead))}\"")
    for i, m in enumerate(found):
        between = flat[found[i - 1].end():m.start()] if i else ""
        if i and between.lstrip("함") != ",":
            doubts.append(D_CUT)
        months, exact = _months(int(m.group("n")), m.group("unit"))
        pct = int(m.group("pct"))
        paid = 100 - pct if m.group("kind") == "감액지급" else pct
        if m.group("paid") and int(m.group("paid")) != paid:
            doubts.append(f"{D_CUT}: 감액률과 괄호 안 지급률이 맞지 않음")
        if not exact:
            doubts.append(f"{D_CUT}: {m.group('n')}{m.group('unit')}을 개월로 바꿀 수 없음")
        if not 0 < paid < 100:
            doubts.append(D_CUT)
            continue
        period = _slice(note, at, m.start("n"), m.start("n") + len(m.group("n") + m.group("unit")) + 2)
        steps.append(Step(months, paid / 100, re.sub(r"(\d+\S)\s*미만", r"\1 미만", period)))
        cond = m.group("cond")
        if _PLAIN_COND.fullmatch(cond):
            continue
        narrowed = _CAUSE_COND.fullmatch(cond) or _TARGET_COND.fullmatch(cond)
        if narrowed and "진단확정" not in cond and not who:
            who = _items(_slice(note, at, m.start("cond") + narrowed.start("who"), m.start("cond") + narrowed.end("who")))
            cause = bool(_CAUSE_COND.fullmatch(cond))
        else:
            # "1년 미만에 뇌졸중으로 진단 확정되고 보험금 지급기간 중 …"처럼 감액을 따지는 기준이 지급사유 발생 시점이 아니다
            doubts.append(f"{D_CUT_ODD}: \"{_slice(note, at, m.start('cond'), m.end('cond'))}\"")
    tail = flat[found[-1].end():]
    after = _FULL_AFTER.fullmatch(tail)
    if after and steps and _months(int(after.group("n")), after.group("unit"))[0] == max(s.months for s in steps):
        tail = ""
    if tail not in ("", "함", "함.", "."):
        doubts.append(f"{D_CUT_ODD}: 문장 끝의 \"{_slice(note, at, found[-1].end(), len(flat))}\"")
    steps.sort(key=lambda s: s.months)
    if len(steps) > 2 or len({s.months for s in steps}) != len(steps):
        doubts.append(f"{D_CUT}: 감액 구간이 셋 이상이거나 기간이 겹침")
    return _Cut(tuple(steps[:2]), note, who, led, cause, tuple(dict.fromkeys(doubts)))


# ---------------------------------------------------------------------------
# 보장개시일 문장
# ---------------------------------------------------------------------------

_START = re.compile(
    r"(?P<who>.*?)보장개시일은"
    r"(?:(?:최초)?계약일또는부활\(효력회복\)일(?:로)?부터(?P<n>\d+)(?P<unit>일|개월|년)이지난날의다음날"
    r"|(?P<zero>(?:보험)?계약일(?:또는부활\(효력회복\)일)?))"
    r"(?:이며,|이고,|임\.?|암$|$)"
)
# "(단, 상해로 인해 「추간판장애」로 진단 확정된 경우 보험계약일을 보장개시일(책임개시일)로 함)"
_INJURY = re.compile(r"\(단,상해로인(?:해|한).*보험계약일을보장개시일\(책임개시일\)로함\)?")
_GENERIC_WHO = re.compile(r"^(?:이\s*특별약관)?$")


@dataclass(frozen=True)
class _Wait:
    who: tuple[str, ...]        # 이 보장개시일이 걸리는 대상. "보장개시일은 …"처럼 대상이 없으면 빈 튜플
    days: int
    source: str


def _days(n: int, unit: str) -> int:
    return n * 365 if unit == "년" else n * 30 if unit == "개월" else n


def read_waits(note: str) -> list[_Wait] | None:
    """보장개시일을 적은 "※" 문단에서 (대상, 면책 날수)를 읽는다. 꼴을 읽지 못하면 None."""
    flat, at = _flat(note)
    out: list[_Wait] = []
    pos = 0
    while pos < len(flat):
        m = _START.match(flat, pos)
        if not m:
            break
        who = re.sub(r"\s*(?:의|에\s*대한)$", "", _slice(note, at, m.start("who"), m.end("who")))
        days = 0 if m.group("zero") else _days(int(m.group("n")), m.group("unit"))
        out.append(_Wait(() if _GENERIC_WHO.match(who) else _items(who), days, note))
        pos = m.end()
    rest = flat[pos:]
    if not out or (rest and not _INJURY.fullmatch(rest)):
        return None
    if rest:
        # 질병은 앞에서 읽은 날수만큼 기다리고 상해는 계약일부터 보장한다
        if len(out) != 1:
            return None
        return [_Wait(("질병",), out[0].days, note), _Wait(("상해",), 0, note)]
    return out


# ---------------------------------------------------------------------------
# 지급 한도
# ---------------------------------------------------------------------------

_LIMIT_WORD = re.compile(r"한하여|한도|\d\s*회\s*한|\d\s*(?:회|일)\s*당|에\s*한함")
# 괄호 없이 문장 끝에 적힌 한도. "… 받은 경우 1일 1회, 연간 3회에 한하여 가입금액 지급"
_TAIL_LIMITS = (
    re.compile(r"(?:각 ?치료행위 ?별 ?)?(?:1일 ?\d+회, ?)?연간 ?\d+회에 한하여"),
    re.compile(r"(?:통원|내원|입원|수술) ?1(?:회|일)당"),
    re.compile(r"\d+일째 입원일로부터"),
)
# "… 경우" 뒤에 적혀도 지급금액 칸과 다를 것이 없는 말(빈칸을 뗀 글). 이 밖의 말이 있으면 지급 기준이 따로 있는 것으로 본다
_PLAIN_TAIL = re.compile(
    r"(?:에는)?(?:각치료행위별로각각의지급방식에따라)?가입금액을?(?:(?:상해|질병)입원일당(?:으로)?)?지급(?:함)?"
    r"|가입금액을매\d+년마다\d+%씩정액할증한금액을지급|"
)
_SENTENCE_END = re.compile(r"(?:(?<=지급)|(?<=지급함)|(?<=말함)|(?<=않음)) (?=[^\x00])")
_SIMPLE_LIMIT_SENTENCE = re.compile(r"(?:연간|최초) ?\d+회한으로 지급함$")
_PAY_WORD = re.compile(r"지급|한도|한하여|감액|면책")
# "이 보장은 가 수술비(1종)(동일사고당1회한), … 총 5개 세부보장으로 구성되어 있음". 세부보장마다 가입금액이 따로 있다
_BUNDLE = re.compile(r"^이 보장은 .*?(총 ?\d+개 세부보장으로 구성되어 있음)\s*")
# "※" 문단을 가르는 낱말. 표에서는 "지 급"처럼 낱말 가운데 빈칸이 끼어들기도 해서 빈칸을 뗀 글에서 찾는다
_NOTE_LIMIT = re.compile(r"한하여|한도|\d회한|\d회당|만지급|대해서만지급|수술로간주|보장이소멸|보험금지급기간이란")
# 표의 값에 영향이 없는 "※" 문단: 낱말 풀이, 약관 참조, 보장 제외 안내
_NOTE_PLAIN = re.compile(
    r"말함\.?$|[가-힣」)]임\.?$|약관참조$|제외(?:됨|함|합니다)?\.?$|보장하지않음\.?$|담보입니다\.?$|수있습니다\.?$|적용함\.?$|경우에만보장합니다\.?$"
)


def _body_limits(body: str) -> tuple[list[str], list[str], str]:
    """본문에서 (한도 문구들, 확신 없음 사유들, 지급 기준 문구)를 읽는다.

    본문의 첫 문장은 "… 한 경우 [지급 방식] (한도)" 꼴이다. 한도는 괄호 안이나 "경우" 뒤에 적힌다.
    "경우" 뒤에 "가입금액 지급" 말고 다른 말이 있거나("약관에서 정한 금액을 지급", "2년간 매월 가입금액 지급"),
    둘째 문장부터 지급을 다시 말하면("간병인을 지원받기를 원할 경우 … 입원일당은 지급하지 않음")
    지급금액 칸만으로는 지급액을 알 수 없으므로 확신 없음으로 표시하고 그 문구를 돌려준다.
    """
    limits: list[str] = []
    doubts: list[str] = []
    basis: list[str] = []
    bundle = _BUNDLE.match(body)
    if bundle:
        body = body[bundle.end():]
        doubts.append(D_BUNDLE)
        basis.append(bundle.group(1))
    masked = _mask(body)
    ends = [m.start() for m in _SENTENCE_END.finditer(masked)]
    spans = list(zip([0] + [e + 1 for e in ends], ends + [len(body)]))
    groups = [(a, body[a + 1:b].rstrip(")").strip()) for a, b in _groups(body)]

    start, end = spans[0]
    at = masked.rfind("경우", start, end)
    tail = masked[at + 2:end].replace("\x00", " ") if at >= 0 else ""
    limits += [text for _, text in sorted((m.start(), m.group(0)) for p in _TAIL_LIMITS for m in p.finditer(tail))]
    for pattern in _TAIL_LIMITS:
        tail = pattern.sub(" ", tail)
    limits += [inner for a, inner in groups if a < end and _LIMIT_WORD.search(inner)]
    if not _PLAIN_TAIL.fullmatch(re.sub(r"\s", "", tail)):
        doubts.append(D_BASIS)
        basis.append(" ".join(tail.split()))

    for start, end in spans[1:]:
        sentence = body[start:end].strip()
        inner = [text for a, text in groups if start <= a < end and _LIMIT_WORD.search(text)]
        if _SIMPLE_LIMIT_SENTENCE.search(sentence):
            limits.append(sentence)
        elif inner or _PAY_WORD.search(masked[start:end]):
            doubts.append(D_BASIS)
            limits += inner
            basis.append(sentence)
    return limits, list(dict.fromkeys(doubts)), " ".join(basis)


# ---------------------------------------------------------------------------
# 세부보장 한 줄 읽기
# ---------------------------------------------------------------------------

_NAME_STEP = re.compile(r"(\d+)(일|년)\s*(\d+)%")           # 이름의 "(1년50%)", "(90일50%)", "(60일10%형)"
_NAME_CUT = re.compile(r"\d+\s*년\s*감액")                  # 이름의 "(1년감액)"
_NAME_WAIT = re.compile(r"(\d+)일\s*면책")                  # 이름의 "(30일면책)"
_SIMILAR_CANCERS = ("유사암", "기타피부암", "갑상선암", "대장점막내암", "제자리암", "경계성종양")


@dataclass
class _Row:
    """대상별 줄 하나를 만드는 동안 쓰는 값."""
    who: tuple[str, ...]
    days: int = 0
    percent: float | None = 100.0
    steps: tuple[Step, ...] = ()
    exception: str = ""
    sources: dict[str, str] = field(default_factory=dict)


def _split_rows(waits: list[_Wait], cuts: list[_Cut], pay: _Pay) -> list[_Row] | None:
    """대상에 따라 면책·감액·지급률이 다르면 대상별 줄로 나눈다. 나눌 것이 없으면 한 줄, 나누지 못하면 None.

    면책이 갈리면 보장개시일 문장의 대상이, 아니면 감액 문장의 대상이, 아니면 지급금액 칸의 대상이 줄을 정한다.
    다른 칸의 대상은 그 줄들 가운데 하나와 같은 묶음이어야 값을 붙일 수 있다. 묶음이 어긋나면 나누지 않는다.
    """
    by_wait = len({w.days for w in waits}) > 1
    by_cut = len(cuts) > 1
    days = waits[0].days if waits else 0
    wait_source = "\n".join(dict.fromkeys(w.source for w in waits))
    if not (by_wait or by_cut or pay.by):
        row = _Row((), days, pay.percent)
        if waits:
            row.sources["면책"] = wait_source
        if cuts:
            row.steps, row.sources["감액"] = cuts[0].steps, cuts[0].source
            if cuts[0].who:      # "질병으로 인한 …"처럼 일부 경우에만 감액한다. 줄은 그대로 두고 문장을 감액예외에 옮긴다
                row.exception = cuts[0].source
        return [row]

    # 1) 줄을 정한다
    if by_wait:
        if by_cut or any(not w.who for w in waits):
            return None
        rows = [_Row(w.who, w.days, sources={"면책": w.source}) for w in waits]
    elif by_cut:
        if not all(c.led and c.who for c in cuts):
            return None
        rows = [_Row(c.who, days, steps=c.steps, sources={"감액": c.source}) for c in cuts]
    else:
        rows = [_Row(who, days, percent) for who, percent in pay.by]
        if pay.rest is not None:
            if len(pay.by) != 1:
                return None
            rows.insert(0, _Row((_target(pay.by[0][0]) + " 외",), days, pay.rest))
    if not by_wait and waits:
        for row in rows:
            row.sources["면책"] = wait_source
    find = {_key(r.who): r for r in rows}
    if len(find) != len(rows):
        return None

    # 2) 감액 문장이 하나면 모든 줄에, 대상이 적혀 있으면 그 대상의 줄에만 붙인다
    if cuts and not by_cut:
        cut = cuts[0]
        if cut.who and _key(cut.who) not in find:
            return None
        for row in ([find[_key(cut.who)]] if cut.who else rows):
            row.steps, row.sources["감액"] = cut.steps, cut.source

    # 3) 지급률
    if by_wait or by_cut:
        given = {_key(who): percent for who, percent in pay.by}
        if any(k not in find for k in given) or (pay.by and pay.rest is None and len(given) != len(rows)):
            return None
        for key, row in find.items():
            row.percent = given.get(key, pay.rest) if pay.by else pay.percent
    if pay.by:
        for row in rows:
            row.sources["지급률"] = pay.raw
    return rows


def read_cover(name: str, reason: str, amount: str) -> list[Reading]:
    """세부보장 하나(보장명·지급사유·지급금액)를 읽는다.

    대개 한 줄을 돌려준다. 대상에 따라 면책·감액·지급률이 다르면 대상마다 한 줄씩 돌려주고,
    줄 이름(label) 뒤에 대상이 괄호로 붙는다. 규칙이 확신하지 못하면 doubts에 사유를 적는다.
    """
    name = " ".join((name or "").split())
    body, notes = _paragraphs(reason)
    doubts: list[str] = []
    evidence: dict[str, str] = {}

    pay = read_amount(amount)
    cuts: list[_Cut] = []
    waits: list[_Wait] = []
    limits, body_doubts, basis = _body_limits(body)
    doubts += body_doubts
    asides: list[str] = []
    for note in notes:
        cut = read_cut(note)
        if cut is not None:
            cuts.append(cut)
            doubts += cut.doubts
            continue
        if "보장개시일" in re.sub(r"\s", "", note):
            found = read_waits(note)
            if found is None:
                doubts.append(D_WAIT)
                evidence["읽지 못한 보장개시일 문장"] = (evidence.get("읽지 못한 보장개시일 문장", "") + "\n" + note).strip()
            else:
                waits += found
            continue
        flat = re.sub(r"\s", "", note)
        if _NOTE_LIMIT.search(flat):
            limits.append(note)
        elif not (_INNER.match(note) or _NOTE_PLAIN.search(flat)):
            # 어느 꼴에도 들지 않는 문단. "안면부 1cm당 30만원 … 지급"처럼 지급액을 따로 정한 문장일 수 있다.
            # 원문을 한도 칸에 남기고 사람이 보게 한다
            doubts.append(f"{D_UNREAD}: \"{note}\"")
            asides.append(note)
    cuts = [c for c in cuts if c.steps]

    note_parts = [x for x in (pay.growth, basis) if x]
    if pay.percent is None and not pay.by:
        doubts.append(D_AMOUNT)
        note_parts.insert(0, pay.raw)
    note_parts += asides
    rows = _split_rows(waits, cuts, pay)
    if rows is None:
        # 나누지 못했다. 한 줄로 두고 가장 긴 면책과 가장 큰 지급률을 적는다. 원문은 한도·감액예외 칸에 남는다
        doubts.append(D_SPLIT)
        rates = [p for _, p in pay.by] + ([pay.rest] if pay.rest is not None else [])
        row = _Row((), max((w.days for w in waits), default=0), max(rates) if rates else pay.percent,
                   cuts[0].steps if cuts else ())
        if waits:
            row.sources["면책"] = "\n".join(dict.fromkeys(w.source for w in waits))
        if cuts:
            row.sources["감액"] = "\n".join(c.source for c in cuts)
            if len(cuts) > 1 or cuts[0].who:
                row.exception = row.sources["감액"]
        if pay.by:
            note_parts.insert(0, pay.raw)
        rows = [row]

    elif len(rows) == 1 and rows[0].exception and not cuts[0].cause:
        # "질병으로 인한 …"은 상해에는 감액이 없다는 뜻이라 감액예외 칸으로 충분하다. "유사암으로 …", "가질환은 …"처럼
        # 일부 대상에만 걸리는 감액은 줄을 나눠야 맞는데 나눌 짝이 없다
        doubts.append(D_SPLIT)

    # 이름에 적힌 표시("(1년50%)", "(30일면책)")와 읽은 값이 맞는지 본다
    all_steps = {(s.months, s.rate) for r in rows for s in r.steps}
    for m in _NAME_STEP.finditer(name):
        months, _ = _months(int(m.group(1)), m.group(2))
        if (months, int(m.group(3)) / 100) not in all_steps:
            doubts.append(f"{D_NAME}: 이름의 \"{m.group(0)}\"")
    if _NAME_CUT.search(name) and not all_steps:
        doubts.append(f"{D_NAME}: 이름에 감액 표시가 있는데 감액 문장이 없음")
    for m in _NAME_WAIT.finditer(name):
        if int(m.group(1)) not in {r.days for r in rows}:
            doubts.append(f"{D_NAME}: 이름의 \"{m.group(0)}\"")
    # 본문은 "보장개시일 이후"라는데 날수를 적은 문장이 없다
    if "보장개시일" in re.sub(r"\s", "", body) and not waits and D_WAIT not in doubts:
        doubts.append(f"{D_WAIT}: 날수를 적은 문장이 없음")
    # 보장개시일 문장은 "암의 보장개시일" 하나뿐인데 본문은 유사암도 함께 보장한다. 유사암의 보장개시일은 알 수 없다
    if len(waits) == 1 and waits[0].days and _key(waits[0].who) == _key(("암",)):
        outside = _mask(body).replace("\x00", "")
        unsaid = [w for w in _SIMILAR_CANCERS if w in outside]
        if unsaid:
            doubts.append(f"{D_WAIT}: 본문의 {_target(unsaid)}에 대한 보장개시일이 적혀 있지 않음")

    limit = " / ".join(_unique(limits))
    note_text = " / ".join(dict.fromkeys(note_parts))
    if limit:
        evidence["한도"] = limit
    if note_text:
        evidence["비고"] = note_text
    out = []
    for row in rows:
        proof = dict(evidence)
        proof.setdefault("지급률", pay.raw)
        proof.update(row.sources)
        if row.exception:
            proof["감액예외"] = row.exception
        out.append(Reading(
            name=name, target=_target(row.who), percent=row.percent, steps=row.steps, waiting_days=row.days,
            limit=limit, exception=row.exception, note=note_text, evidence=proof,
            doubts=tuple(dict.fromkeys(doubts)),
        ))
    return out


# ---------------------------------------------------------------------------
# 시트 행으로 바꾸기
# ---------------------------------------------------------------------------

RENEWAL_TAG = "[갱신형]"
MAIN_LABEL = "기본계약"


@dataclass(frozen=True)
class Outcome:
    riders: list[dict[str, Any]]                # sys_특약 행
    benefits: list[dict[str, Any]]              # sys_급부 행
    readings: dict[str, Reading]                # 급부ID → 읽은 값과 근거
    doubts: dict[str, tuple[str, ...]]          # 급부ID → 확신 없음 사유. 확신하는 줄은 들어가지 않는다


def read_rider(rider: Rider) -> list[list[Reading]]:
    """특별약관 하나의 세부보장을 차례로 읽는다. 세부보장마다 줄 목록 하나."""
    return [read_cover(c.name, c.reason, c.amount) for c in rider.covers]


def id_name(name: str, label: str, taken: set[str]) -> str:
    """특약ID를 만들 이름. 같은 이름의 특별약관이 또 나오면 뒤에 나온 쪽에 구분을 붙인다.

    "상해 사망"이 기본계약에도 선택계약에도 있는 요약서가 있다. 이름만으로 ID를 만들면 둘이 겹친다.
    먼저 나온 쪽은 이름 그대로, 뒤에 나온 쪽은 "상해 사망(선택계약)"으로 ID를 만든다. taken에는 이미 쓴 이름이 쌓인다.
    """
    key, n = name, 1
    while key in taken:
        key = f"{name}({label or '중복'})" if n == 1 else f"{name}({label or '중복'} {n})"
        n += 1
    taken.add(key)
    return key


def rider_row(variant_id: str, name: str, label: str, renewal_years: int | None, key_name: str | None = None) -> dict[str, Any]:
    """sys_특약 행 하나. key_name은 ID를 만들 이름(id_name의 결과)."""
    renewal = RENEWAL_TAG in name.replace(" ", "")
    key_name = key_name or name
    return {
        "특약ID": ids.rider_id(variant_id, key_name),
        "종형ID": variant_id,
        "특약계보키": ids.rider_lineage_key(key_name),
        "담보구분": "주계약" if label == MAIN_LABEL else "선택특약",
        "원시특약명": name,
        "갱신여부": renewal,
        "갱신주기년": renewal_years if renewal else None,
        "최소가입금액만원": None,
        "최대가입금액만원": None,
        "합산한도기준키": None,
    }


def limit_cell(reading: Reading) -> str | None:
    """지급횟수제한 칸. 한도 문구에 체증 문구나 비율이 아닌 지급금액 원문을 덧붙인다(스키마에 따로 적을 칸이 없다)."""
    parts = [x for x in (reading.limit, reading.note) if x]
    return " / ".join(parts) or None


def benefit_row(rider_id: str, reading: Reading, role: str, page: int) -> dict[str, Any]:
    """sys_급부 행 하나. 비율로 읽지 못한 지급금액은 100으로 두고 원문을 지급횟수제한 칸에 남긴다."""
    label = reading.label
    steps = list(reading.steps) + [None, None]
    return {
        "급부ID": ids.benefit_id(rider_id, label),
        "특약ID": rider_id,
        "원시급부명": label,
        "급부역할": role,
        "기준가입금액만원": BASE_AMOUNT,
        "기준지급금액만원": float(reading.percent) if reading.percent is not None else BASE_AMOUNT,
        "지급횟수제한": limit_cell(reading),
        "면책기간일수": reading.waiting_days,
        "감액개월1": steps[0].months if steps[0] else None,
        "감액지급률1": steps[0].rate if steps[0] else None,
        "감액개월2": steps[1].months if steps[1] else None,
        "감액지급률2": steps[1].rate if steps[1] else None,
        "감액예외": reading.exception or None,
        "근거문서종류": DOC_KIND,
        "근거문서쪽수": page,
    }


def build_rows(variant_id: str, riders: Iterable[Rider], renewal_years: int | None) -> Outcome:
    """특별약관 조각들을 sys_특약·sys_급부 행으로 바꾼다.

    renewal_years: 이름에 "[갱신형]"이 붙은 특별약관의 갱신 주기(년). 요약서의 급부 표에는 주기가 없으므로
    사업방법서에서 확인한 값을 넘긴다. None을 넘기면 갱신형 특약 행이 형식 검사(check_rows)에 걸린다.

    한 칸에 이름이 여럿 적힌 조각("가 치료비, 가 치료비(기가입자용)")은 이름마다 특약 행을 만들고 급부 행도 따로 만든다.
    급부역할은 세부보장이 하나면 "주급부", 여럿이면 "대등복합"이다.
    """
    rider_rows: list[dict[str, Any]] = []
    benefit_rows: list[dict[str, Any]] = []
    readings: dict[str, Reading] = {}
    doubts: dict[str, tuple[str, ...]] = {}
    taken: set[str] = set()
    for rider in riders:
        covers = read_rider(rider)
        role = "주급부" if len(rider.covers) == 1 else "대등복합"
        names = rider.names or (rider.title,)
        for name in names:
            key_name = id_name(name, rider.label, taken)
            row = rider_row(variant_id, name, rider.label, renewal_years, key_name)
            rider_rows.append(row)
            for cover, lines in zip(rider.covers, covers):
                for reading in lines:
                    # 이름이 여럿인 조각의 세부보장 이름은 그 이름들을 이어 적은 것이다. 특약 이름으로 바꿔 적는다
                    if len(names) > 1 and len(rider.covers) == 1:
                        reading = replace(reading, name=name)
                    out = benefit_row(row["특약ID"], reading, role, cover.page)
                    benefit_rows.append(out)
                    readings[out["급부ID"]] = reading
                    if reading.doubts:
                        doubts[out["급부ID"]] = reading.doubts
    return Outcome(rider_rows, benefit_rows, readings, doubts)
