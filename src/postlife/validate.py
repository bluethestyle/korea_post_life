"""시트에 쓰기 전에 행을 점검한다. 글자 그대로 확인되는 것은 코드가 먼저 본다."""
from __future__ import annotations

import re
from typing import Any

from . import kcd
from .schema import TABS

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")

ALLOWED: dict[tuple[str, str], set[str]] = {
    ("sys_상품종형", "비교역할구분"): {"정밀비교", "관문전용", "직전개정시연"},
    ("sys_상품종형", "심사유형"): {"일반심사", "간편심사"},
    ("sys_상품종형", "갱신유형"): {"비갱신", "갱신"},
    ("sys_특약", "담보구분"): {"주계약", "의무특약", "선택특약"},
    ("sys_급부", "급부역할"): {"주급부", "부수급부", "대등복합"},
    ("sys_보험료예시", "성별"): {"M", "F"},
    ("sys_보험료예시", "출처구분"): {"요약서", "계산기"},
    ("sys_결합제약", "제약유형"): {"의무부가", "배타선택", "최대연동", "선행가입"},
    ("sys_결합제약", "제약단위"): {"비율", "만원", "건수"},
    ("sys_급부질병코드", "포함여부"): {"Y", "N"},
    ("sys_시장동향", "분류유형"): {
        "배타적사용권", "신담보출시", "상품개정", "판매중지",
        "간편고지완화", "한도한시상향", "제도변화",
    },
    ("sys_시장동향", "수집경로"): {"검색", "RSS", "게시판"},
    ("sys_작업로그", "작업단계"): {"추출", "코드대조", "판정", "재추출", "사람검토이관"},
    ("sys_작업로그", "결과"): {"통과", "반려", "보류"},
    ("hum_표준담보사전", "급부유형"): {"진단", "수술", "입원", "통원", "치료"},
    ("hum_담보매핑", "검토상태"): {"자동확정", "대기", "승인", "수정", "오류", "대상외"},
    ("hum_기준값", "기준분류"): {"법정한도", "색상기준", "판정구간", "대표조건", "표시문구"},
}


def _type_ok(value: Any, kind: str) -> bool:
    if kind == "str":
        return isinstance(value, str)
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "date":
        return isinstance(value, str) and bool(_DATE.match(value))
    if kind == "datetime":
        return isinstance(value, str) and bool(_DATETIME.match(value))
    return False


def check_row(tab_name: str, row: dict[str, Any]) -> list[str]:
    """문제 목록을 돌려준다. 비어 있으면 통과."""
    tab = TABS[tab_name]
    problems: list[str] = []
    for extra in set(row) - set(tab.header):
        problems.append(f"정의되지 않은 열: {extra}")
    for col in tab.columns:
        value = row.get(col.name)
        if value is None or value == "":
            if col.required:
                problems.append(f"필수 열이 비어 있음: {col.name}")
            continue
        if not _type_ok(value, col.type):
            problems.append(f"자료형이 다름: {col.name}={value!r} (기대 {col.type})")
            continue
        allowed = ALLOWED.get((tab_name, col.name))
        if allowed and value not in allowed:
            problems.append(f"허용값이 아님: {col.name}={value!r}")
    problems.extend(_logic(tab_name, row))
    return problems


def _logic(tab_name: str, row: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if tab_name == "sys_가입조건":
        lo, hi = row.get("최저가입나이"), row.get("최고가입나이")
        if isinstance(lo, int) and isinstance(hi, int) and lo > hi:
            out.append(f"최저가입나이({lo})가 최고가입나이({hi})보다 큼")
    if tab_name == "sys_상품종형":
        if row.get("심사유형") == "간편심사" and row.get("고지최근소견개월") in (None, ""):
            out.append("간편심사인데 고지 요건이 비어 있음")
        if row.get("갱신유형") == "갱신" and row.get("갱신주기년") in (None, ""):
            out.append("갱신형인데 갱신주기년이 비어 있음")
        start, end = row.get("적용시작일"), row.get("판매종료일")
        if start and end and str(end) < str(start):
            out.append("판매종료일이 적용시작일보다 앞섬")
        if row.get("비교역할구분") == "정밀비교":
            # 관문 표시에만 쓰는 종형 때문에 선택 열로 둔 값이지만, 정밀 비교에서는 색상 규칙에 필요하다
            for name in ("환급유형", "납입면제적용", "요약서해시"):
                if row.get(name) in (None, ""):
                    out.append(f"정밀비교 종형인데 {name}이(가) 비어 있음")
    if tab_name == "sys_특약":
        if row.get("갱신여부") is True and row.get("갱신주기년") in (None, ""):
            out.append("갱신형 특약인데 갱신주기년이 비어 있음")
    if tab_name == "sys_급부":
        for n in ("1", "2"):
            rate = row.get(f"감액지급률{n}")
            if isinstance(rate, (int, float)) and not 0 < rate < 1:
                out.append(f"감액지급률{n}은 0과 1 사이여야 함: {rate}")
            if (row.get(f"감액개월{n}") in (None, "")) != (rate in (None, "")):
                out.append(f"감액개월{n}과 감액지급률{n}은 함께 있어야 함")
        if isinstance(row.get("면책기간일수"), int) and row["면책기간일수"] < 0:
            out.append("면책기간일수가 음수")
    if tab_name == "sys_결합제약":
        if row.get("제약수치") not in (None, "") and row.get("제약단위") in (None, ""):
            out.append("제약수치가 있는데 제약단위가 비어 있음")
    if tab_name in ("sys_급부질병코드", "hum_표준질병군"):
        s, e = row.get("시작코드"), row.get("끝코드")
        if isinstance(s, str) and isinstance(e, str):
            try:
                if not kcd.ordered(s, e):
                    out.append(f"끝코드({e})가 시작코드({s})보다 앞섬")
            except ValueError as err:
                out.append(str(err))
    if tab_name == "sys_보험료예시":
        if isinstance(row.get("월납보험료원"), int) and row["월납보험료원"] <= 0:
            out.append("월납보험료원이 0 이하")
    return out


def check_rows(tab_name: str, rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    """기본키별 문제 목록. 문제 없는 행은 들어가지 않는다."""
    tab = TABS[tab_name]
    result: dict[str, list[str]] = {}
    seen: set[str] = set()
    for row in rows:
        key = str(row.get(tab.key))
        problems = check_row(tab_name, row)
        if key in seen:
            problems.append("기본키 중복")
        seen.add(key)
        if problems:
            result[key] = problems
    return result
