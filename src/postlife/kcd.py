"""KCD 질병코드 구간 비교.

약관 분류표는 구간을 세 자리 코드로 적는다(예: I60~I63, D47). 세 자리 코드는 그 아래
세분류 전체를 뜻하므로, "I63.9"는 끝코드 "I63" 안에 들어간다. 문자열을 그대로 비교하면
"I63.9" > "I63"이라 구간 밖으로 잘못 나온다.
"""
from __future__ import annotations

import re

_CODE = re.compile(r"^([A-Z])(\d{2})(?:\.?(\d{1,2}))?$")
_LAST = "\uffff"


def normalize(code: str) -> str:
    """"c73", "D471", "D47.1"을 "C73", "D47.1", "D47.1"로 맞춘다."""
    m = _CODE.match(str(code).strip().upper())
    if not m:
        raise ValueError(f"KCD 코드 형식이 아님: {code!r}")
    letter, major, minor = m.groups()
    return f"{letter}{major}.{minor}" if minor else f"{letter}{major}"


def _low(code: str) -> str:
    return normalize(code)


def _high(code: str) -> str:
    c = normalize(code)
    return c + _LAST  # 끝코드는 그 코드로 시작하는 세분류 전체를 포함한다


def in_range(code: str, start: str, end: str) -> bool:
    return _low(start) <= normalize(code) <= _high(end)


def range_within(start: str, end: str, outer_start: str, outer_end: str) -> bool:
    """[start, end] 구간이 [outer_start, outer_end] 안에 완전히 들어가는가."""
    return _low(outer_start) <= _low(start) and _high(end) <= _high(outer_end)


def ranges_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    return _low(start_a) <= _high(end_b) and _low(start_b) <= _high(end_a)


def ordered(start: str, end: str) -> bool:
    return _low(start) <= _high(end)
