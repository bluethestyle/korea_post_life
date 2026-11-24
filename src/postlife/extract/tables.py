"""상품요약서의 급부 표를 PDF에서 직접 읽어 특별약관 단위 조각으로 자른다.

"□ 보험금 지급사유 및 지급금액" 절이 "보장명 | 지급사유 | 지급금액" 표 하나로 이어지는 요약서가 있다.
담보 수백 개가 경계 표시 없이 이어져서, 글자로 풀면 어디서 담보가 바뀌는지 알 수 없다
(segment.rider_blocks가 ValueError를 낸다). 이런 문서는 표의 선을 읽어 행과 칸을 되살린 다음 자른다.

표는 이렇게 생겼다.

- 보장명 칸이 둘로 갈리기도 한다. 왼쪽 칸이 특별약관 이름, 오른쪽 칸이 세부보장 이름이다.
  왼쪽 칸은 세부보장 여러 행에 걸쳐 병합되어 있다. 갈리지 않은 행은 특별약관 하나에 세부보장이 하나다.
- 표는 쪽을 넘어 이어지고 쪽마다 머리행(보장명·지급사유·지급금액)이 다시 나온다.
  행 하나가 쪽 끝에서 잘려 이름과 지급사유가 두 쪽에 나뉘어 적히기도 한다.
- 지급금액 칸이 세부보장 여러 행에 걸쳐 병합되어 있기도 하다.
- 지급사유 칸 안에 작은 표(질병 목록 등)가 들어 있기도 하다.

이 파일은 두 부분이다. 앞부분은 PDF 없이 돌아간다(행 목록 → 조각, JSON 쓰기·읽기, 쪽 범위 찾기).
뒷부분만 pdfplumber를 쓴다(표의 선과 글자 읽기).

회사마다 다른 것(급부 절의 제목, 표 위 구분 줄의 꼴, 머리행의 말, 한 칸에 이어 적은 이름을 가르는 규칙, 머리행 없이
이어지는 표, 쪽을 넘는 병합 칸, 한 쪽에 두 단으로 실린 표, 양옆 테두리가 없는 표)은
Layout에 모았다. 함수마다 layout을 받고, 주지 않으면 삼성화재(SAMSUNGFIRE)다. 회사별 차이는 docs/table_layouts.md에 적었다.

수집 단계는 PDF를 받은 실행 안에서 글자 파일만 남기고 PDF는 버린다. 표 조각도 그 실행에서
write_riders로 JSON에 써 두면 추출 단계가 read_riders와 to_blocks로 읽는다.
"""
from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Sequence

from .segment import Block

FORMAT = "급부표조각/1"

_HEAD_WORDS = ("보장명", "지급사유", "지급금액")
_SECTION_START = re.compile(r"^□\s*보험금\s*지급사유\s*및\s*지급금액\s*$")
_SECTION_END = re.compile(r"^□\s*보험금\s*지급제한\s*사항")
_LABEL = re.compile(r"^◆\s*(.+?)\s*$")                       # 표 위의 "◆ 기본계약", "◆ 선택계약"


@dataclass(frozen=True)
class Layout:
    """회사마다 다른 상품요약서 급부 표의 꼴.

    표 자체(보장명, 지급사유, 지급금액 머리행과 칸 병합, 쪽 넘김)는 회사가 달라도 같고, 다른 것은 아래뿐이다.
    기본값은 삼성화재의 꼴이고, 기본값으로 읽은 결과는 이 설정을 만들기 전과 글자 하나 다르지 않아야 한다.
    """
    name: str
    section_start: re.Pattern = _SECTION_START  # 급부 절의 시작 줄
    section_end: re.Pattern = _SECTION_END      # 급부 절 다음 절의 시작 줄
    section_title: str = "□ 보험금 지급사유 및 지급금액"   # 오류 글에 적을 절 제목
    label: re.Pattern = _LABEL                  # 표 위의 구분 줄. group(1)이 구분 글자다
    heading: re.Pattern | None = None           # 표 위의 "< … >" 줄. group(1)이 안의 글자다
    rider_word: str = ""                        # 구분 줄이나 "< … >" 줄에 이 말이 있으면 특약 하나의 세부 표를 여는 머리다
    slash_names: bool = False                   # 한 칸에 이어 적은 특약 이름을 "/"로 가른다(아니면 쉼표, split_names)
    nested: bool = False                        # 보장명 칸이 셋 이상으로 갈린 표에서 가운데 단의 이름을 세부보장 이름 앞에 잇는다
    notes: bool = False                         # 표 너비를 다 차지한 행("주1) …", "※ …")을 조각이 아닌 주석으로 뗀다
    headless: bool = False                      # 머리행 없이 앞 쪽 표가 이어지는 표를 칸 자리로 알아보고 읽는다
    trailing: bool = False                      # 쪽의 마지막 표 아래에 적힌 구분 줄과 머리 줄도 다음 쪽으로 넘긴다
    # 병합된 칸을 더 읽는다: 위 행과 병합된 지급사유 칸은 위 행의 글을 물려받고, 지급금액 칸까지 넓게 병합된 지급사유 칸
    # (지급사유 칸 안의 작은 표가 지급금액 자리까지 차지한 행)은 지급금액을 위 행에서 물려받지 않는다
    merged: bool = False
    main_label: str = ""                        # 이 구분의 조각에 주계약 표시를 단다. 비우면 표시를 달지 않는다
    common: str = "공통"                         # 형 구간이 있는 문서에서 형이 적히지 않은 특약 머리의 형
    name_heads: tuple[str, ...] = ("보장명",)    # 머리행에서 보장명 칸에 적히는 말. 이 가운데 하나와 지급사유, 지급금액이 있으면 급부 표다
    segment_line: re.Pattern | None = None      # 표 위에서 형 구간을 여는 줄. group(1)이 형이다("가. 간편심사형(…)" → "간편심사형")
    # 세부보장 이름 칸 없이 특약 이름 칸 하나가 지급사유 여러 행에 걸쳐 병합된 표. 쪽 첫 행의 이름 칸이 비어 있으면
    # 앞 행이 잘린 표시(_cut_tail)가 있을 때만 앞 행에 이어 붙이고, 나머지는 같은 특약의 다음 세부보장으로 읽는다
    unnamed_rows: bool = False
    inner_tables: bool = True                   # 지급사유 칸 안의 작은 표를 찾는다. False면 지급사유 칸 안의 선도 모두 행과 칸을 가르는 선이다
    close_frame: bool = False                   # 표의 세로선들이 함께 끝나는 자리에 가로선을 더한다(쪽을 넘는 병합 칸은 쪽 끝에 아래 선이 없다)
    # 주계약 조각의 특별약관 이름. 주계약 표의 이름 칸이 급부명(세부보장 이름)인 요약서는 표에 계약 이름이 없어 이 이름을 쓴다.
    # 세부보장 이름은 이름 칸의 글자 그대로다. 비우면 이름 칸의 글자가 특별약관 이름이다
    main_title: str = ""
    two_up: bool = False                        # 쪽 하나에 표가 두 단이다. 왼쪽 단을 위에서 아래로 읽고 오른쪽 단을 읽는다
    open_sides: bool = False                    # 표 양옆에 테두리가 없다. 가로선 끝 자리에 세로선을 더한다(_side_edges)
    # 맨 왼쪽의 좁은 칸에 묶음 이름("상해관련보장", "기본계약")을 한 글자씩 세로로 적은 표. 그 칸을 떼고, 그 글이
    # group_labels 가운데 하나면 그 행의 구분으로, 아니면 group_other를 구분으로 쓴다
    group_column: bool = False
    group_labels: tuple[str, ...] = ()
    group_other: str = ""
    doubled_names: bool = False                 # 한 칸에 줄만 바꿔 이어 적은 두 이름("가나진단", "가나진단(갱신형)")을 가른다
    # 지급사유 자리(지급사유 머리 아래) 너비를 다 차지한 가로선을 작은 표의 선이 아니라 행을 가르는 선으로 본다.
    # 지급사유 머리 아래가 이름 칸("2종(납입면제형)")과 지급사유 칸으로 갈린 표의 행 경계가 그런 선이다
    reason_rows: bool = False
    # 쪽 첫 행의 특약 이름 칸에 앞 쪽 특약 이름의 꼬리("갱신형)")만 적힌 행은 세부보장 이름 칸이 비어도 꼬리를 앞 특약 이름에
    # 잇고, 행은 그 특약의 다음 세부보장으로 본다(이름 칸 오른쪽 단은 위의 이름을 물려받는다)
    name_tails: bool = False
    dotted: bool = False                        # 세로 점선도 칸 경계로 읽는다(_border_edges)
    # 위 행과 병합된 지급사유 칸은 위 행이 쪽을 넘으며 이어 붙인 글 전체를 물려받는다(unnamed_rows도 같게 한다)
    shared_whole: bool = False
    cell_fills: bool = False                    # 머리행 칸 바탕색 사각형의 양 변도 칸 경계로 읽는다(_border_edges)
    # 이름에 남은 번호 매김("1. ", "5. ")을 뗀다. 숫자 뒤 마침표 다음에 빈칸이 있을 때만(spaced_names이면 빈칸이 없어도)
    numbered_names: bool = False
    # 지급금액 머리 아래가 여러 칸으로 갈린 표. 행마다 그 칸들의 글을 모두 지급금액으로 읽는다(_amount_parts). 여러 행에 걸쳐
    # 병합된 오른쪽 칸(감액, 한도)은 병합 범위의 행마다 붙이고, 칸 안의 작은 표(이름 칸과 산식 칸)는 두 칸을 다 읽는다
    amount_parts: bool = False
    # 지급사유 칸 왼쪽의 이름 칸들은 PDF에 적힌 빈칸 글자만 빈칸으로 읽는다. 좁은 이름 칸을 양끝 맞춤으로 채운 줄은 글자 사이가
    # 벌어져 있을 뿐 빈칸 글자가 없다("하 이 클"). 벌어진 자리에 빈칸을 넣으면 같은 이름이 줄 바꿈 자리에 따라 빈칸만 달리 읽힌다
    spaced_names: bool = False
    # 요약서 뒤쪽에 특약별 면책기간 표("최초계약과 부활(효력회복)계약의 면책기간" 칸)가 따로 있다. 급부 표의 지급사유는 이름 없는
    # "보장개시일 이후"만 적고 날수는 이 표에만 있다(현대해상). 적재의 기계 검사가 이 표를 칸 단위로 읽어 날수를 대조한다(wait_table)
    wait_table: bool = False


# 삼성화재: "□ 보험금 지급사유 및 지급금액" 절, "◆ 기본계약" 구분, 쉼표로 이은 이름
SAMSUNGFIRE = Layout("samsungfire")

# 메리츠화재: "(1) 보험금지급사유 및 지급금액" 절. 구분 표시(❍)는 글자로 풀면 "m"이 된다("m 기본계약").
# 특약 하나의 세부보장을 따로 적은 표 위에는 "m 무배당 … 특별약관2610"이나 "< 무배당 … 특별약관2610(일반심사형) >"가,
# 형(심사 유형)마다 표를 따로 둔 요약서에는 형 구간 앞에 "< 무배당 메리츠 …(통합간편심사형) >"가 적혀 있다.
# 지급사유와 지급금액이 같은 특약은 이름을 "/"로 이어 한 칸에 적는다("가나 진단비/갱신형 가나 진단비").
MERITZ = Layout(
    "meritz",
    section_start=re.compile(r"^\(1\)\s*보험금\s*지급사유\s*및\s*지급금액\s*$"),
    section_end=re.compile(r"^\(2\)\s*보험금\s*지급제한\s*사항"),
    section_title="(1) 보험금지급사유 및 지급금액",
    label=re.compile(r"^[m❍○◆]\s+(.+?)\s*$"),
    heading=re.compile(r"^[<＜]\s*(.+?)\s*[>＞]$"),
    rider_word="특별약관",
    slash_names=True, nested=True, notes=True, headless=True, trailing=True, merged=True,
    main_label="기본계약",
)

# KB라이프생명: "2. 보험금 지급사유 및 보험금 지급제한 사유" 절(다음 절은 "3. 일반적인 보험금 지급제한 사유").
# 절 안에서 "가. 간편심사형(3.5.5), 간편심사형(3.3.5)", "나. 일반심사형" 줄이 형 구간을 열고, 구간마다 "1) 주계약",
# "2) 선택특약" 줄 아래에 표가 있다. 칸은 셋이고 머리행의 첫 칸이 "급부명"(주계약)이나 "특약명"(선택특약)이다.
# 주계약 표의 이름 칸은 급부명이라 주계약 조각의 특별약관 이름은 "주계약"으로 둔다(main_title. 세부보장 이름은 급부명).
# 세부보장 이름 칸이 없어 특약 이름 칸 하나가 지급사유 여러 행에 걸쳐 병합되고, 그 칸과 지급금액 칸이 쪽을 넘어 이어진다
# (쪽 끝에 그 칸들의 아래 선이 없다). 지급사유 칸 안의 가로선은 작은 표가 아니라 행을 가르는 선이다. "주요치료Plus" 특약은
# 지급사유 칸이 설명 칸과 치료 이름 칸으로 갈리고, 치료 이름 칸이 행마다 따로, 설명 칸과 지급금액 칸은 여러 행에 걸쳐 병합된다.
KBLIFE = Layout(
    "kblife",
    section_start=re.compile(r"^\d+\.\s*보험금\s*지급사유\s*및\s*보험금\s*지급제한\s*사유\s*$"),
    section_end=re.compile(r"^\d+\.\s*일반적인\s*보험금\s*지급제한\s*사유"),
    section_title="2. 보험금 지급사유 및 보험금 지급제한 사유",
    label=re.compile(r"^\d+\)\s*(주계약|\S*특약)\s*$"),
    segment_line=re.compile(r"^[가-하]\.\s*([가-힣]*심사형)(?![가-힣])"),
    name_heads=("특약명", "급부명"),
    nested=True, trailing=True, merged=True, unnamed_rows=True, inner_tables=False, close_frame=True,
    main_label="주계약", main_title="주계약",
)

# 현대해상: "2. 보험금 지급사유, 지급금액 및 지급제한사항" 절의 첫 소절(지급사유와 지급금액 표. 다음 소절은 "나. 보험금
# 지급제한 사항"). 쪽마다 표가 두 단(왼쪽, 오른쪽)으로 실리고 단마다 머리행("구 분 | 지 급 사 유 | 지 급 금 액")이 다시 나온다. 표 양옆에
# 테두리가 없다. 표 위에 "[기본계약]", "[의무부가 특약]", "[선택계약]" 줄이 있고, 맨 왼쪽 좁은 칸에 묶음 이름("상해관련보장",
# 간편심사 요약서는 "기본계약", "의무가입특약"도)을 세로로 적는다. 특약 이름 칸 하나에 이름 둘("가나진단", "가나진단(갱신형)")을
# 쉼표나 줄 바꿈으로 이어 적고 지급사유, 지급금액은 함께 쓴다. 이름 칸 오른쪽에 묶음(경증상해진단)이나 플랜((기본형)) 칸이 더 있다.
HYUNDAI = Layout(
    "hyundai",
    section_start=re.compile(r"^\d+\.\s*보험금\s*지급사유\s*,\s*지급금액\s*및\s*지급제한\s*사항"),
    section_end=re.compile(r"^(?:.*\s)?나\.\s*보험금\s*지급제한\s*사항"),
    section_title="2. 보험금 지급사유, 지급금액 및 지급제한사항",
    label=re.compile(r"^\[\s*([^\[\]]*(?:계약|특약))\s*\]\s*$"),
    name_heads=("구분",),
    nested=True, trailing=True, merged=True,
    main_label="기본계약",
    two_up=True, open_sides=True, group_column=True,
    group_labels=("기본계약", "의무가입특약", "의무부가특약"), group_other="선택계약",
    doubled_names=True, reason_rows=True, name_tails=True, dotted=True, shared_whole=True,
    cell_fills=True, numbered_names=True, amount_parts=True, spaced_names=True, wait_table=True,
)

LAYOUTS = {layout.name: layout for layout in (SAMSUNGFIRE, MERITZ, KBLIFE, HYUNDAI)}
_ONLY = re.compile(r"\s*[*＊※]\s*([^*＊※]*?에\s*한함)\s*")       # 이름 칸에 붙은 "*7종에 한함"
# 종 번호. "7종", 그리고 번호를 이어 적은 "1, 2, 3종", "1~3종"
_VARIANT = re.compile(r"(?<!\d)(\d+(?:\s*(?:[,·ㆍ/~∼-]|및)\s*\d+)*)\s*종")
_VARIANT_STEP = re.compile(r"([~∼-])?\s*(\d+)")
# 칸 안에서 새 문단을 여는 줄. 이런 줄 앞에서는 줄을 잇지 않는다
_PARAGRAPH = re.compile(r"^(?:[※▷▶◆■□●○·∙ㆍ•*＊]|[-–]\s|주\s*\d*\)|\d+[.)]\s|\(\d+\)|[①-⑳])")
_INNER = re.compile(r"^· ([^:\n]*): (.*)$")                   # 칸 안의 작은 표를 풀어 적은 줄
_DOTS = re.compile(r"[·∙ㆍ•‧・]")
_TAGS = re.compile(r"^(?:\[[^\[\]]*\])+")                     # 이름 앞의 "[갱신형][간편]", "[건강]"
_NUMBERED = re.compile(r"(?<![\d.])\d{1,2}\.\s+")                # 이름 칸에 남은 번호 매김("4. 가나수술5. (다라)"). Layout.numbered_names
# Layout.spaced_names인 표의 번호 매김. 번호 뒤가 빈칸 글자 없이 벌어져 있을 뿐이라 빈칸 없이도 뗀다("7.5%"처럼 숫자가 이어지면 그대로 둔다)
_NUMBERED_TIGHT = re.compile(r"(?<![\d.])\d{1,2}\.(?![\d.])\s*")


def squash(text: str | None) -> str:
    """빈칸과 줄바꿈을 없애고 가운뎃점 모양을 하나로 맞춘다. 글자 대조에 쓴다."""
    return _DOTS.sub("·", re.sub(r"\s+", "", text or ""))


def name_key(name: str) -> str:
    """담보 이름을 서로 맞춰 볼 수 있게 줄인다.

    같은 담보가 가입 화면이나 정답셋에는 "[건강]암 진단비(유사암 제외)"로, 급부 표에는 "암 진단비(유사암 제외),"로
    적힌다. 앞의 대괄호 표시, 빈칸, 가운뎃점 모양, 끝의 쉼표 차이를 없앤다.
    """
    return _TAGS.sub("", squash(name)).rstrip(",")


# ---------------------------------------------------------------------------
# 표의 행 → 특별약관 조각 (PDF 없이 돌아가는 부분)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PageTable:
    """한 쪽에서 읽은 표 하나.

    rows는 행마다 칸의 글자를 왼쪽부터 담은 목록이다. 칸 값의 뜻은 pdfplumber의 Table.extract()와 같다.
    None은 옆이나 위 칸과 병합되어 따로 칸이 없는 자리, ""는 칸은 있는데 글자가 없는 자리다.
    칸 안의 줄바꿈은 "\\n"이고, 낱말이 끝나는 자리에서 줄이 바뀌었으면 줄 끝에 빈칸이 남아 있다.
    """
    page: int
    rows: Sequence[Sequence[str | None]]
    label: str = ""             # 표 바로 위에 적힌 구분. 예: "기본계약", "선택계약"
    open_end: bool = False      # 마지막 행의 지급사유가 문장 가운데서 끊겼는가(다음 쪽 첫 행으로 이어진다)
    segment: str = ""           # 형 구간. 예: "통합간편심사형". 형마다 표를 따로 둔 요약서에만 있다
    heading: str = ""           # 특약 하나의 세부 표이면 그 특약 이름(표 위 머리 줄). 행은 모두 이 특약의 세부보장이다
    head: tuple[int, int, int] | None = None    # (머리행 수, 지급사유 칸 번호, 지급금액 칸 번호). 머리행 없이 이어진 표만 적는다
    part: int = 0               # 쪽 안의 단(Layout.two_up. 0 왼쪽, 1 오른쪽). 왼쪽 단의 표가 같은 쪽 오른쪽 단으로 이어진다
    labels: tuple[str, ...] = ()    # 행마다의 구분(Layout.group_column). 비어 있으면 모든 행이 label이다


@dataclass(frozen=True)
class Line:
    """표의 한 행을 역할별로 읽은 것. 칸 값은 PageTable과 같은 뜻이다."""
    page: int
    rider: str | None           # 보장명 왼쪽 칸(특별약관 이름)
    cover: str | None           # 보장명 오른쪽 칸(세부보장 이름). 칸이 갈리지 않았으면 None
    reason: str | None
    amount: str | None
    label: str = ""
    top: bool = False           # 그 표에서 머리행 바로 다음 행인가
    cut: bool = False           # 쪽 끝에서 잘린 행인가
    # Layout.nested일 때 보장명 칸들(특약 칸 오른쪽, 특약 머리가 있는 표는 맨 왼쪽부터)의 글자.
    # None은 위 행과 병합되어 위의 이름을 물려받는 자리, ""는 이름이 없는 자리다. cover는 이 가운데 마지막 이름이다
    levels: tuple[str | None, ...] = ()
    segment: str = ""
    heading: str = ""
    remark: bool = False        # 특약 전체에 붙는 "※" 설명 행. 그 특약의 세부보장마다 지급사유 끝에 붙인다
    shared: bool = False        # 지급사유 칸이 위 행과 병합되어 위 행의 글을 물려받았다(Layout.merged)
    part: int = 0               # 쪽 안의 단(PageTable.part)


@dataclass(frozen=True)
class Cover:
    """세부보장 한 줄."""
    name: str
    reason: str
    amount: str
    page: int                   # 이 줄이 시작하는 쪽
    only: str = ""              # 이름 칸에 붙은 적용 범위. 예: "7종에 한함"


@dataclass(frozen=True)
class Rider:
    """특별약관 하나와 그 세부보장들."""
    title: str
    covers: tuple[Cover, ...]
    first_page: int
    last_page: int
    label: str = ""             # "기본계약", "선택계약"
    only: str = ""              # 특별약관 이름 칸에 붙은 적용 범위
    segment: str = ""           # 형 구간(형마다 표를 따로 둔 요약서만). 형이 적히지 않은 특약 머리의 표는 Layout.common
    main: bool | None = None    # 주계약(기본계약)인가. Layout.main_label이 없는 회사는 None
    parts: tuple[str, ...] = () # 이름 칸에 적힌 특약 이름들. 비어 있으면 title을 쉼표 규칙(split_names)으로 가른다

    @property
    def text(self) -> str:
        """모델이 읽을 글. 세부보장마다 보장명·지급사유·지급금액을 적는다."""
        head = [f"특별약관: {self.title}"]
        if self.label:
            head.append(f"구분: {self.label}")
        if self.segment:
            head.append(f"형: {self.segment}")
        if self.main is not None:
            head.append(f"주계약: {'예' if self.main else '아니오'}")
        if self.only:
            head.append(f"적용 범위: {self.only}")
        head.append(f"세부보장 {len(self.covers)}개")
        parts = ["\n".join(head)]
        for i, c in enumerate(self.covers, 1):
            rows = [f"[{i}] 보장명: {c.name}"]
            if c.only:
                rows.append(f"적용 범위: {c.only}")
            rows += [f"지급사유: {c.reason}", f"지급금액: {c.amount}"]
            parts.append("\n".join(rows))
        return "\n\n".join(parts)

    @property
    def names(self) -> tuple[str, ...]:
        """이름 칸에 적힌 특별약관 이름들. 지급사유가 같은 특별약관 여럿을 한 행에 쉼표로("/"로 잇는 회사도 있다) 이어 적은 표가 있다."""
        return self.parts or split_names(self.title)

    def to_block(self) -> Block:
        return Block(self.title, self.text, self.first_page, self.last_page)


def join_name(cell: str | None) -> str:
    """여러 줄에 갈린 이름을 한 줄로 잇는다.

    좁은 칸에서는 "[갱신\\n형][간편]\\n암 다빈치\\n로봇 수술\\n비"처럼 낱말 가운데서 줄이 바뀐다.
    줄 끝에 빈칸이 남아 있으면 낱말 사이에서 바뀐 것이므로 한 칸 띄우고, 없으면 붙여 쓴다.
    이름 앞 대괄호 표시에 붙은 빈칸과 끝에 남은 쉼표는 뗀다(표에 "암 진단비(유사암 제외),"로 적힌 행이 있다).
    """
    out = ""
    for line in (cell or "").split("\n"):
        if line.strip():
            out += line.lstrip()
    out = re.sub(r"\s+", " ", out).strip().rstrip(",").strip()
    return re.sub(r"^(?:\[[^\[\]]*\]\s*)+", lambda m: re.sub(r"\s+", "", m.group()), out)


def join_text(cell: str | None) -> str:
    """지급사유·지급금액 칸의 글을 문단 단위로 잇는다.

    칸 너비 때문에 바뀐 줄은 잇고("…급성심근경\\n색증으로" → "…급성심근경색증으로"),
    "※", "-", "▷"처럼 새 문단을 여는 줄과 빈 줄 다음 줄은 줄을 바꾼 채로 둔다.
    """
    paragraphs: list[str] = []
    fresh = True
    for line in (cell or "").split("\n"):
        if not line.strip():
            fresh = True
            continue
        if fresh or not paragraphs or _PARAGRAPH.match(line.strip()):
            paragraphs.append(line.lstrip())
        else:
            paragraphs[-1] += line.lstrip()
        fresh = False
    return "\n".join(re.sub(r"[ \t]+", " ", p).strip() for p in paragraphs)


def split_names(title: str) -> tuple[str, ...]:
    """한 칸에 이어 적힌 이름을 가른다.

    "가 치료비(연간1회한), 가 치료비(연간1회한)(기가입자용)"처럼 괄호 밖의 쉼표에서 가른다. 쉼표 앞이 닫는 괄호로
    끝날 때만 가른다("위·십이지장, 대장 양성종양 진단비"는 이름 하나다). 쉼표 없이 "…(1년50%) [갱신형]…"처럼
    닫는 괄호 뒤에 대괄호 표시가 새로 시작해도 가른다.
    """
    names: list[str] = []
    depth, start = 0, 0
    for i, ch in enumerate(title):
        if ch in "([":
            if ch == "[" and depth == 0 and title[start:i].rstrip().endswith(")"):
                names.append(title[start:i])
                start = i
            depth += 1
        elif ch in ")]":
            depth = max(depth - 1, 0)
        elif ch == "," and depth == 0 and title[start:i].rstrip().endswith(")"):
            names.append(title[start:i])
            start = i + 1
    names.append(title[start:])
    return tuple(n.strip() for n in names if n.strip())


def tidy_slash(name: str) -> str:
    """"/"로 이은 이름에서 "/" 앞뒤 빈칸을 없앤다. "가나 진단비/ 갱신형 가나 진단비" → "가나 진단비/갱신형 가나 진단비"."""
    return re.sub(r"\s*/\s*", "/", name)


def split_slash(title: str) -> tuple[str, ...]:
    """괄호 밖의 "/"에서 이름을 가른다. "가나 사망/갱신형 가나 사망" → 둘, "(다라용/마바용)가나 사망"은 하나."""
    names: list[str] = []
    depth, start = 0, 0
    for i, ch in enumerate(title):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(depth - 1, 0)
        elif ch == "/" and depth == 0:
            names.append(title[start:i])
            start = i + 1
    names.append(title[start:])
    return tuple(n.strip() for n in names if n.strip())


def split_doubled(title: str) -> tuple[str, ...]:
    """한 칸에 이어 적은 이름들을 가른다(Layout.doubled_names). 쉼표로 가른 다음(split_names), 이름이 앞부분을 그대로
    되풀이하면 되풀이가 시작하는 자리에서 가른다. "가나진단다라가나진단다라(갱신형)" → "가나진단다라", "가나진단다라(갱신형)".

    줄만 바꿔 이어 적은 두 이름은 글자로 풀면 붙어 버린다. 둘째 이름은 첫째 이름에 "(갱신형)" 같은 표시를 더한 형태라
    첫째 이름이 그대로 두 번 나온다. 빈칸은 비교하지 않는다(글자 사이를 벌려 맞춘 칸은 두 이름의 빈칸 자리가 다르다).
    되풀이되는 앞부분은 네 글자 이상이고, 가장 짧은 앞부분에서 가른다. 원문에서 닫는 괄호가 빠진 이름도 그대로 되풀이되므로
    괄호가 하나 열린 앞부분까지 가르고, 가른 이름마다 괄호 짝을 맞춘다(mend_brackets). 괄호 안이라 split_names가 가르지 않은
    쉼표("가나(다라,가나(다라)(갱신형)")와 두 이름 사이에 적힌 "/"("가나진단/ 가나진단(갱신형)")는 앞 이름의 끝으로 보고 뗀다.
    """
    out: list[str] = []
    for name in split_names(title):
        rest, pieces = name, []
        while True:
            at = [i for i, ch in enumerate(rest) if not ch.isspace()]
            bare = "".join(rest[i] for i in at)
            cut = next((at[k] for k in range(4, len(bare) // 2 + 1)
                        if bare[k:].startswith(bare[:k].rstrip(",/")) and _unclosed(bare[:k]) in (0, 1)), None)
            if cut is None:
                break
            pieces.append(rest[:cut].strip().rstrip(",/").strip())
            rest = rest[cut:]
        pieces.append(rest.strip())
        out += [mend_brackets(p) for p in pieces] if len(pieces) > 1 else pieces
    return tuple(n for n in out if n)


_RENEWAL_MARK = re.compile(r"\[갱신형\]|(?<!비)갱신형")      # reader_rows.is_renewal과 같은 기준(빈칸을 지운 글자에서 찾음)


def plain_name(names: Sequence[str]) -> str:
    """한 칸에 함께 적힌 비갱신형과 갱신형 이름 가운데 세부보장 이름으로 쓸 이름(Layout.doubled_names).

    원문에 적힌 차례와 관계없이 갱신형 표시가 없는 이름을 쓴다("가나진단(갱신형)", "가나진단" → "가나진단"). 이 이름이 급부 이름이
    되고 급부ID의 재료가 되므로, 갱신형 이름이 먼저 적힌 행도 비갱신형 이름이 먼저 적힌 행과 같은 이름을 내야 한다.
    모두 갱신형이거나 모두 갱신형이 아니면 첫 이름이다.
    """
    plain = [n for n in names if not _RENEWAL_MARK.search(squash(n))]
    return plain[0] if plain and len(plain) < len(names) else names[0]


def first_doubled(name: str) -> str:
    """한 칸에 이어 적은 두 이름("가나진단", "가나진단(갱신형)")이면 그 가운데 갱신형 표시가 없는 이름(plain_name),
    아니면 이름 그대로(Layout.doubled_names).

    세부보장 이름 칸에도 비갱신형과 갱신형의 세부보장 이름을 함께 적은 행이 있다. 세부보장 이름은 하나여야 하므로(급부 이름이
    된다) 이름 하나만 쓴다. 두 이름은 가장 짧은 이름이 나머지 이름의 앞부분일 때 같은 이름의 두 표기로 본다. 갱신형 이름이 먼저
    적혀도("가나진단(갱신형), 가나진단") 같다. 쉼표로 이은 다른 이름들("1종(가나), 2종(다라)")은 앞부분이 같지 않으므로 그대로 둔다.
    """
    parts = split_doubled(name)
    if len(parts) < 2:
        return name
    keys = [squash(p) for p in parts]
    head = min(keys, key=len).rstrip(")")
    return plain_name(parts) if all(k.startswith(head) for k in keys) else name


def mend_brackets(name: str) -> str:
    """원문에서 소괄호 하나가 빠진 이름의 짝을 맞춘다. 빠진 자리가 분명한 두 경우만 고친다.

    - 마지막 괄호 묶음이 닫히지 않은 채 이름이 끝나면 끝에서 닫는다. "가나 치료비(1년감액" → "가나 치료비(1년감액)"
    - 여는 괄호 없이 닫는 괄호가 나오고 그 앞에 닫힌 괄호 묶음이 있으면, 그 묶음 바로 뒤에서 연다.
      "가나 수술비(다라 제외) 마바 제외)(1년50%)" → "가나 수술비(다라 제외) (마바 제외)(1년50%)"
    가운데 묶음이 닫히지 않았거나, 앞에 괄호 묶음이 없거나, 앞 묶음과 닫는 괄호 사이에 글자가 없는 것처럼
    자리를 정할 수 없으면 그대로 둔다.
    대괄호 표시("[갱신형]")는 건드리지 않는다. 쪽을 넘어 갈린 이름은 다 이은 다음에 쓴다(이을 토막이 남은 이름을 닫으면 안 된다).
    """
    out, opened, after = name, [], None        # 열린 "("의 자리들, 마지막으로 닫힌 묶음 바로 뒤 자리
    i = 0
    while i < len(out):
        if out[i] == "(":
            opened.append(i)
        elif out[i] == ")":
            if opened:
                opened.pop()
            elif after is not None and out[after:i].strip():
                at = after + len(out[after:i]) - len(out[after:i].lstrip())
                out = out[:at] + "(" + out[at:]
                i += 1
            else:
                return name
            if not opened:
                after = i + 1
        i += 1
    if len(opened) == 1 and opened[0] == out.rfind("("):
        out += ")"
    return out


def split_only(name: str) -> tuple[str, str]:
    """이름에 붙은 적용 범위 표시를 뗀다. "보험료 납입면제대상 *7종에 한함" → ("보험료 납입면제대상", "7종에 한함")."""
    m = _ONLY.search(name)
    if not m:
        return name, ""
    return (name[:m.start()] + " " + name[m.end():]).strip(), re.sub(r"\s+", " ", m.group(1)).strip()


def _head_words(layout: Layout) -> tuple[str, ...]:
    """머리행에 적히는 말. 보장명 칸의 말(Layout.name_heads)과 지급사유, 지급금액."""
    return (*layout.name_heads, *_HEAD_WORDS[1:])


def _columns(rows: Sequence[Sequence[str | None]], layout: Layout = SAMSUNGFIRE) -> tuple[int, int, int] | None:
    """머리행을 읽어 (머리행 수, 지급사유 칸 번호, 지급금액 칸 번호)를 알아낸다. 급부 표의 머리행이 없으면 None.

    머리행은 병합 때문에 두세 행으로 갈려 읽히기도 한다. 글자가 머리말뿐인 행을 위에서부터 머리행으로 본다.
    """
    words = _head_words(layout)
    reason = amount = None
    count = 0
    for i, row in enumerate(rows[:4]):
        cells = [squash(c) for c in row]
        if any(c and c not in words for c in cells):
            break
        count = i + 1
        for j, c in enumerate(cells):
            if c == "지급사유":
                reason = j
            elif c == "지급금액":
                amount = j
    if reason is None or amount is None or not 0 < reason < amount:
        return None
    return count, reason, amount


def _first(cells: Sequence[str | None]) -> str | None:
    """병합으로 빈 자리(None)를 건너뛰고 처음 나오는 칸. 글자가 있는 칸을 먼저 고른다."""
    filled = [c for c in cells if c is not None]
    return next((c for c in filled if c.strip()), filled[0] if filled else None)


def is_note_row(row: Sequence[str | None]) -> bool:
    """표 너비를 다 차지한 행인가. 맨 왼쪽 칸에만 글자가 있고 나머지는 모두 병합된 자리(None)다. "주1) …", "※ …" 같은 주석이다.

    지급금액 자리는 ""일 수 있다(Layout.merged가 넓게 병합된 칸 오른쪽의 지급금액 자리를 ""로 둔다).
    """
    return (len(row) >= 3 and bool((row[0] or "").strip()) and all(c is None for c in row[1:-1])
            and row[-1] in (None, ""))


def _levels(cells: Sequence[str | None], top: bool, blank: bool) -> tuple[str | None, ...]:
    """보장명 칸들을 단별로 읽는다. 위 행과 병합된 자리는 None(위의 이름을 물려받는다), 이름이 없는 자리는 "".

    None은 위 행과 병합된 자리일 수도, 왼쪽 칸과 병합된 자리일 수도 있다. 왼쪽 칸이 모두 비어 있을 때만 위 행과
    병합된 것으로 본다(왼쪽에 이름이 있으면 그 이름 칸이 옆으로 넓게 병합된 것이다). 표의 첫 행에서 빈 칸("")은
    앞 쪽에서 병합된 칸이 쪽을 넘어온 자리라 마찬가지로 물려받는다. blank는 이 칸들 왼쪽(특약 칸)이 비었는가.
    """
    out: list[str | None] = []
    for c in cells:
        if c is not None and c.strip():
            out.append(c)
            blank = False
        elif c is None or top:
            out.append(None if blank else "")
        else:
            out.append("")
    return tuple(out)


def _remark(cells: Sequence[str | None]) -> str | None:
    """특약 칸이 병합된(비거나 None) 행에서 처음 적힌 칸이 "※"로 시작하고 그 뒤로 적힌 칸이 없으면 그 글.

    세부보장 행들 아래에 "※ 가나보장개시일은 …"처럼 그 특약 전체에 붙는 설명을 적은 행이다(Layout.merged).
    """
    if (cells[0] or "").strip():
        return None
    filled = [c for c in cells[1:] if c is not None and c.strip()]
    return filled[0] if len(filled) == 1 and filled[0].strip().startswith("※") else None


def table_lines(table: PageTable, layout: Layout = SAMSUNGFIRE) -> list[Line]:
    """표 하나의 행을 역할별로 읽는다. 머리행은 건너뛴다. 급부 표가 아닌 표(머리행이 다른 표)는 빈 목록.

    보장명 칸은 지급사유 칸 왼쪽의 칸 전부다. 맨 왼쪽이 특별약관 이름이고, 나머지 가운데 글자가 있는 칸이
    세부보장 이름이다(쪽에 따라 세로선 자리가 달라 보장명 칸이 셋으로 읽히는 표가 있다).

    Layout.nested이면 가운데 칸들을 단별로 levels에 담는다(특약 > 묶음 > 세부보장처럼 보장명 칸이 셋인 표).
    특약 머리가 있는 표(heading)는 맨 왼쪽 칸도 특약 이름이 아니라 세부보장 이름의 단이다.
    Layout.merged이면 지급사유 머리 아래 칸이 여럿으로 갈린 표에서 글이 가장 많은 칸만 지급사유로 읽고, 나머지 칸
    ("특정소액암" 같은 세부보장 이름, "자가용운전자형", "4주미만 진단시" 같은 조건)은 세부보장 이름의 단으로 levels 끝에 붙인다.
    Layout.notes이면 표 너비를 다 차지한 주석 행 가운데 "※"로 시작하는 행은 그 특약에 붙는 설명(remark)으로,
    나머지("주1) …")는 건너뛴다(table_notes가 따로 모은다).
    """
    found = table.head or _columns(table.rows, layout)
    if found is None:
        return []
    count, reason, amount = found
    lines = []
    body = [list(row) + [None] * (amount + 1 - len(row)) for row in table.rows[count:]]
    said: dict[int, str] = {}           # 지급사유 칸에 마지막으로 적힌 글. Layout.merged
    main = _main_reason(body, reason, amount)
    for i, row in enumerate(body):
        top = i == 0
        label = table.labels[count + i] if table.labels else table.label
        if layout.notes and is_note_row(row):
            if (row[0] or "").strip().startswith("※"):
                lines.append(Line(table.page, None, None, row[0], "", label, top, False,
                                  segment=table.segment, heading=table.heading, remark=True, part=table.part))
            continue
        if layout.merged and row[amount] == "" and _remark(row[:amount]) is not None:
            lines.append(Line(table.page, None, None, _remark(row[:amount]), "", label, top, False,
                              segment=table.segment, heading=table.heading, remark=True, part=table.part))
            continue
        texts = [c for c in row[reason:amount] if c is not None]
        extra: tuple[str | None, ...] = ()
        if layout.merged:
            texts, extra = _reason_cells(row[reason:amount], main - reason, said, top)
        rider, cover, levels = row[0], _first(row[1:reason]) if reason > 1 else None, ()
        if layout.nested:
            if table.heading:
                rider, levels = None, _levels(row[:reason], top, True)
            else:
                tail = layout.name_tails and top and _unopened(row[0])     # 앞 쪽 특약 이름의 꼬리만 적힌 칸
                levels = _levels(row[1:reason], top, (not (row[0] or "").strip() and (row[0] is None or top)) or tail)
            levels += extra
            cover = next((c for c in reversed(levels) if c), None)
        lines.append(Line(
            page=table.page,
            rider=rider,
            cover=cover,
            reason="\n".join(texts) if texts else None,
            amount=_first(row[amount:]),
            label=label,
            top=top,
            cut=table.open_end and i == len(body) - 1,
            levels=levels,
            segment=table.segment,
            heading=table.heading,
            shared=layout.merged and not top and bool(texts) and all(c is None for c in row[reason:main + 1]),
            part=table.part,
        ))
    return lines


def _main_reason(body: Sequence[Sequence[str | None]], reason: int, amount: int) -> int:
    """지급사유 머리 아래 칸이 여럿으로 갈린 표에서 지급사유 글이 든 칸의 번호. 글이 가장 많은 칸이다.

    지급사유 칸들이 모두 따로 있는 행(옆으로 병합되지 않은 행)의 글만 센다. 옆으로 넓게 병합된 칸의 글은 맨 왼쪽 칸
    번호로 읽히기 때문이다. 그런 행이 없으면 모든 행의 글을 센다.
    """
    if amount - reason < 2 or not body:
        return reason
    split = [r for r in body if all(c is not None for c in r[reason:amount])] or list(body)
    return max(range(reason, amount), key=lambda j: (sum(len(r[j] or "") for r in split), -j))


def _reason_cells(cells: Sequence[str | None], main: int, said: dict[int, str],
                  top: bool) -> tuple[list[str], tuple[str | None, ...]]:
    """지급사유 머리 아래 칸들을 (지급사유 글, 세부보장 이름의 단들)로 읽는다(Layout.merged).

    main은 지급사유 글이 든 칸(표에서 글이 가장 많은 칸)이다. 나머지 칸은 이름의 단이다. 칸이 하나뿐이면 그 칸이 지급사유다.
    - 위 행과 병합된 칸(None, 왼쪽 칸들도 모두 None)은 지급사유이면 위 행의 글을 물려받고(said), 이름이면 None(물려받음)이다.
    - 왼쪽 칸에 글이 있는데 None인 자리는 왼쪽 칸이 옆으로 넓게 병합된 자리다. 지급사유 칸이 그렇게 비었으면
      지급사유 칸까지 덮은 왼쪽 칸의 글이 지급사유다(그 칸은 이름의 단에서 뺀다).
    """
    names: list[str | None] = []
    text: str | None = None
    blank, wide = True, None
    for j, c in enumerate(cells):
        vertical = c is None and blank and not top
        if j == main:
            if c is not None:
                text = said[main] = c
            elif vertical and main in said:
                text = said[main]
            elif not vertical:
                wide = max((k for k in range(j) if cells[k] is not None), default=None)
            names.append("")
        elif c is not None:
            names.append(c if c.strip() else "")
        else:
            names.append(None if vertical or (top and blank) else "")
        if c is not None:
            blank = False
    if wide is not None:
        text, names[wide] = cells[wide], ""
        said[main] = text or ""
    names = [v for k, v in enumerate(names) if k != main]
    return ([text] if text is not None else []), tuple(names)


def table_notes(tables: Iterable[PageTable], layout: Layout = SAMSUNGFIRE) -> list[dict[str, Any]]:
    """급부 표 안의 주석 행(표 너비를 다 차지한 "주1) …")을 쪽, 형, 특약 머리와 함께 모은다. Layout.notes인 회사만.

    "※"로 시작하는 행은 바로 위 특약의 세부보장에 붙이므로(table_lines의 remark) 여기에 넣지 않는다.
    """
    out: list[dict[str, Any]] = []
    if not layout.notes:
        return out
    for table in tables:
        found = table.head or _columns(table.rows, layout)
        if found is None:
            continue
        for row in table.rows[found[0]:]:
            if is_note_row(row) and not (row[0] or "").strip().startswith("※"):
                out.append({"쪽": table.page, "형": table.segment, "특약머리": table.heading, "글": join_text(row[0])})
    return out


def _unclosed(text: str | None) -> int:
    text = text or ""
    return text.count("(") + text.count("[") - text.count(")") - text.count("]")


def _unopened(text: str | None) -> bool:
    """여는 괄호 없이 닫는 괄호가 먼저 나오는가. 앞 쪽에서 잘려 넘어온 이름 토막이 그렇다("년50%)")."""
    depth = 0
    for ch in text or "":
        depth += ch in "(["
        depth -= ch in ")]"
        if depth < 0:
            return True
    return False


def _cut_tail(prev: Line, line: Line) -> bool:
    """특약 이름 칸이 빈 쪽 첫 행이 앞 쪽 마지막 행의 잘린 뒷부분인가(Layout.unnamed_rows).

    세부보장 이름 칸이 없는 표에서는 이름 칸이 빈 쪽 첫 행이 대개 같은 특약의 다음 행이다(병합된 특약 이름 칸이 쪽을 넘었다).
    아래 표시가 있을 때만 잘린 행으로 본다.
    - 앞 행의 지급사유 마지막 줄이 칸 너비를 꽉 채웠고(표를 읽을 때 알아낸다) 닫는 괄호나 마침표로 끝나지 않았다.
      "(최초 1회한)"처럼 괄호로 끝난 한 줄짜리 지급사유는 칸을 꽉 채워도 문장이 끝난 것이다.
    - 이 행의 지급사유가 비었거나 "("로 시작한다(앞 문장에 붙는 단서).
    - 이 행의 지급금액이 "("로 시작하거나 여는 괄호 없이 닫는 괄호가 나온다(금액 글의 뒷부분).
    - 앞 행의 지급사유나 지급금액이 괄호가 열린 채 끝났다.
    """
    reason, amount = (line.reason or "").strip(), (line.amount or "").strip()
    cut = prev.cut and not (prev.reason or "").rstrip().endswith((")", "."))
    return (cut or not reason or reason.startswith("(") or amount.startswith("(") or _unopened(amount)
            or _unclosed(prev.reason) > 0 or _unclosed(prev.amount) > 0)


def _continues(prev: Line | None, line: Line, unnamed: bool = False) -> bool:
    """쪽 첫 행이 앞 쪽 마지막 행에서 이어지는 행인가(행 하나가 쪽 끝에서 잘린 경우).

    잘린 행의 뒷부분은 지급금액 칸이 비어 있다(금액은 앞 쪽에 적힌다). 지급금액 칸이 빈 쪽 첫 행 가운데
    - 이름 칸이 모두 비었거나,
    - 앞 행의 지급사유가 문장 가운데서 끊겼거나(표를 읽을 때 알아낸다),
    - 지급사유가 없거나 "※"처럼 덧붙이는 줄로 시작하거나,
    - 이름의 괄호가 앞 행에서 열린 채 끝났거나 이 행에서 닫히기만 하면
    이어지는 행으로 본다. 나머지는 병합된 지급금액 칸이 쪽을 넘어온 새 세부보장이다.
    unnamed(Layout.unnamed_rows)이면 특약 이름 칸이 빈 행은 _cut_tail로 가린다.
    """
    if prev is None or not line.top or (prev.page, prev.part) == (line.page, line.part) or prev.label != line.label:
        return False
    named = bool((line.rider or "").strip() or (line.cover or "").strip())
    if unnamed and not (line.rider or "").strip():
        return _cut_tail(prev, line)
    if (line.amount or "").strip():
        return not named
    if not named or prev.cut:
        return True
    reason = (line.reason or "").strip()
    if not reason or _PARAGRAPH.match(reason):
        return True
    return (_unclosed(prev.rider) > 0 or _unclosed(prev.cover) > 0
            or _unopened(line.rider) or _unopened(line.cover))


def _name_tail(prev: Line | None, line: Line, bare: bool = False) -> bool:
    """쪽 첫 행의 특별약관 칸이 앞 쪽 특별약관 이름의 꼬리이고, 행 자체는 새 세부보장인가.

    특별약관 칸은 세부보장 여러 행에 걸쳐 병합되어 있어서, 이름이 길면 칸이 쪽을 넘으며 이름이 두 쪽에 갈린다.
    그런데 앞 쪽 마지막 세부보장 행이 거기서 끝났으면 다음 쪽 첫 행은 이름과 금액이 따로 적힌 새 세부보장이다.
    이름 꼬리는 여는 괄호 없이 닫는 괄호가 먼저 나오는 토막이다("50%)"). 새 특별약관의 이름은 그렇게 시작하지 않는다.
    _continues가 이어지는 행으로 보지 않은 행에만 쓴다(세부보장 칸이 있는 행만). bare(Layout.name_tails)이면 세부보장 칸이
    비어 위 행의 이름을 물려받는 행도 본다.
    """
    return (prev is not None and line.top and (prev.page, prev.part) != (line.page, line.part) and prev.label == line.label
            and (bare or bool((line.cover or "").strip())) and _unopened(line.rider))


def _append_reason(parts: list[str], more: str) -> None:
    """이어지는 행의 지급사유를 붙인다. 칸 안의 작은 표가 쪽 끝에서 잘렸으면 두 토막을 한 줄로 합친다."""
    before = _INNER.match(parts[-1].rstrip("\n").split("\n")[-1]) if parts else None
    lines = more.lstrip("\n").split("\n")
    after = _INNER.match(lines[0])
    if before and after:
        kept = parts[-1].rstrip("\n").split("\n")[:-1]
        merged = f"· {before.group(1)}{after.group(1)}: {before.group(2)}{after.group(2)}"
        parts[-1] = "\n".join(kept + [merged] + lines[1:])
    else:
        parts.append(more)


class _Open:
    """묶는 중인 특별약관. 쪽을 넘어 갈린 토막을 모아 두었다가 닫을 때 잇는다."""

    def __init__(self, label: str, name: str | None = None, layout: Layout = SAMSUNGFIRE,
                 segment: str = "", heading: str = ""):
        self.label = label
        self.name: list[str] = [name] if name else []
        self.rows: list[dict[str, Any]] = []
        self.last_page = 0
        self.layout = layout
        self.segment = segment
        self.heading = heading
        self.levels: dict[int, str] = {}        # 단별로 마지막에 적힌 이름. 병합된 자리가 물려받는다(Layout.nested)

    @property
    def title(self) -> str:
        return split_only(join_name("\n".join(self.name)))[0]

    def add(self, name: str | None, reason: str | None, amount: list[str], page: int,
            around: tuple[Sequence[str], Sequence[str]] = ((), ())) -> None:
        self.rows.append({"name": [name] if name and name.strip() else [], "reason": [reason or ""],
                          "amount": amount, "page": page, "prefix": list(around[0]), "suffix": list(around[1])})

    def around(self, levels: Sequence[str | None]) -> tuple[list[str], list[str]]:
        """세부보장 이름 앞뒤에 이을 다른 단의 이름들. 병합된 자리(None)는 위 행에서 물려받고, 적힌 자리는 기억해 둔다.

        마지막으로 이름이 적힌 단이 세부보장 이름이고(Line.cover), 그보다 왼쪽 단들은 앞에, 오른쪽 단들(위 행에서
        물려받은 조건 칸)은 뒤에 붙는다. 적힌 이름이 없는 행(세부보장 칸까지 위 행과 병합된 행)은 물려받은 이름 전부가 앞에 붙는다.
        """
        resolved = []
        for k, value in enumerate(levels):
            if value is None:
                value = self.levels.get(k, "")
            else:
                self.levels = {j: v for j, v in self.levels.items() if j < k}
                self.levels[k] = value
            resolved.append(value)
        leaf = max((k for k, v in enumerate(levels) if v), default=len(levels))
        return [v for v in resolved[:leaf] if v.strip()], [v for v in resolved[leaf + 1:] if v.strip()]

    def _tidy(self, name: str) -> str:
        name = tidy_slash(name) if self.layout.slash_names else name
        if self.layout.numbered_names:
            numbered = _NUMBERED_TIGHT if self.layout.spaced_names else _NUMBERED
            name = re.sub(r"\s+", " ", numbered.sub("", name)).strip()
        return name

    def close(self) -> Rider:
        """다 모은 토막을 이어 추출 단위를 만든다. 원문에서 괄호가 빠진 이름은 여기서 짝을 맞춘다(mend_brackets).

        Layout.doubled_names이면 이름 칸에 적힌 두 이름을 특약명들로 가르고, 세부보장 이름 칸이 없는 행의 세부보장 이름은
        특약명들을 이은 제목이 아니라 갱신형 표시가 없는 특약 이름으로 둔다(plain_name. 원문에 적힌 차례와 관계없다).
        세부보장 이름 칸에 적힌 두 이름도 그 가운데 하나만 쓴다(first_doubled).
        """
        title, only = split_only(join_name("\n".join(self.name)))
        title = mend_brackets(self._tidy(title))
        doubled = split_doubled(title) if self.layout.doubled_names else ()
        if len(doubled) > 1:
            title = ", ".join(doubled)      # 원문은 줄만 바꿔 이었다. 쉼표 하나와 빈칸으로 잇는다
        first = plain_name(doubled) if len(doubled) > 1 else title
        single = first_doubled if self.layout.doubled_names else (lambda n: n)
        covers = []
        for row in self.rows:
            name, cover_only = split_only(join_name("\n".join(row["name"])))
            name = single(mend_brackets(self._tidy(name)))
            if row["prefix"] or row["suffix"]:
                tidy = [single(mend_brackets(self._tidy(join_name(p)))) for p in row["prefix"]]
                tidy += [name] + [single(mend_brackets(self._tidy(join_name(p)))) for p in row["suffix"]]
                name = " ".join(p for p in tidy if p)
            covers.append(Cover(name or first, join_text("\n".join(row["reason"])),
                                join_text("\n".join(row["amount"])), row["page"], cover_only))
        title = title or covers[0].name
        main = self.label == self.layout.main_label if self.layout.main_label else None
        if main and self.layout.main_title:
            title = self.layout.main_title          # 이름 칸은 급부명이다. 세부보장 이름으로만 쓴다
        parts = split_slash(title) if self.layout.slash_names else doubled
        return Rider(title, tuple(covers), covers[0].page, max(self.last_page, covers[-1].page), self.label, only,
                     self.segment, main, parts)


def _merged_run(rows: Sequence[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """끝에서부터 마지막 행과 같은 값(지급사유나 지급금액)이 이어지는 행들. 병합된 칸 하나를 함께 쓰는 행들이다."""
    run = [rows[-1]]
    for row in reversed(rows[:-1]):
        if row[key] != rows[-1][key]:
            break
        run.append(row)
    return run


def _join_cut(current: _Open, line: Line) -> None:
    """쪽 끝에서 잘린 행의 뒷부분을 잇는다(Layout.unnamed_rows).

    지급사유 칸과 지급금액 칸은 여러 행에 걸쳐 병합되어 있기도 하다. 잘린 글의 뒷부분은 그 칸을 함께 쓰는 행 모두에 잇는다.
    지급금액 글은 문단을 가르지 않고 앞 글에 바로 잇는다(금액 글 하나가 쪽 끝에서 잘린 것이다).
    세부보장 이름 단(지급사유 칸이 갈려 생긴 치료 이름 칸)에 새 이름이 적혀 있으면 그 병합 칸들을 함께 쓰는 새 세부보장이다.
    """
    rows = current.rows
    last = rows[-1]
    reason, amount, cover = (line.reason or "").strip(), (line.amount or "").strip(), (line.cover or "").strip()
    by_reason, by_amount = _merged_run(rows, "reason"), _merged_run(rows, "amount")
    if reason:
        for row in by_reason:
            _append_reason(row["reason"], line.reason)
    if amount:
        for row in by_amount:
            row["amount"] = row["amount"] + [line.amount] if "".join(row["amount"]).strip() else [line.amount]
    if cover and line.levels and not _unopened(cover):
        current.add(line.cover, None, list(last["amount"]), line.page, current.around(line.levels))
        rows[-1]["reason"] = list(last["reason"])
    elif cover:
        last["name"].append(line.cover)


def group_riders(lines: Iterable[Line], layout: Layout = SAMSUNGFIRE) -> list[Rider]:
    """역할별로 읽은 행을 특별약관 단위로 묶는다.

    - 보장명 왼쪽 칸에 글자가 있으면 새 특별약관이다. 다만 세부보장이 딸린 행에 앞의 특별약관과 같은 이름이
      다시 적혀 있으면(쪽이 바뀐 뒤 이름을 되풀이한 표) 앞의 특별약관이 이어지는 것으로 본다.
    - 왼쪽 칸이 비고(병합 또는 쪽 넘김) 오른쪽 칸에 이름이 있으면 앞 특별약관의 다음 세부보장이다.
    - 쪽 끝에서 잘린 행의 뒷부분(_continues)은 앞 행에 칸별로 이어 붙인다. 이름 토막은 이름에, 지급사유는 지급사유에.
    - 쪽 첫 행의 왼쪽 칸이 앞 특별약관 이름의 꼬리이면(_name_tail, 병합된 칸이 쪽을 넘으며 이름이 갈린 경우)
      꼬리는 특별약관 이름에 잇고, 행은 그 특별약관의 다음 세부보장으로 본다.
    - 지급금액 칸이 병합되어 비었으면(None) 위 행의 값을 물려받는다. 특별약관이 이어지는 쪽 첫 행의
      지급금액 칸이 비었으면 병합된 칸이 쪽을 넘어온 것이므로 마찬가지로 물려받는다.
    - 구분, 형 구간, 특약 머리가 바뀌면 묶던 특별약관을 닫는다. 특약 머리가 있는 표의 행은 모두 그 특약의 세부보장이다.
    - Layout.nested이면 보장명 칸의 다른 단 이름(_Open.around)을 세부보장 이름 앞뒤에 빈칸 하나를 두고 잇는다.
    """
    riders: list[Rider] = []
    current: _Open | None = None
    prev: Line | None = None
    last_amount: list[str] = []             # 바로 앞 행의 지급금액 칸

    def close() -> None:
        nonlocal current
        if current is not None and current.rows:
            riders.append(current.close())
        current = None

    def start(name: str | None) -> _Open:
        return _Open(line.label, name, layout, line.segment, line.heading)

    for line in lines:
        if line.remark:
            if current is not None and current.label == line.label and current.heading == line.heading:
                for row in current.rows:
                    row["reason"].append("\n" + (line.reason or ""))      # 빈 줄을 두어 새 문단으로 붙인다
            continue
        rider, cover = (line.rider or "").strip(), (line.cover or "").strip()
        reason, amount = (line.reason or "").strip(), (line.amount or "").strip()
        if not (rider or cover or reason or amount):
            continue
        if current is not None and (current.label != line.label or current.segment != line.segment
                                    or current.heading != line.heading):
            close()

        if current is not None and _continues(prev, line, layout.unnamed_rows):
            last = current.rows[-1]
            if rider and _title_key(rider) != name_key(current.title):
                current.name.append(line.rider)
            if layout.unnamed_rows:
                _join_cut(current, line)
            else:
                if cover:
                    last["name"].append(line.cover)
                if reason:
                    _append_reason(last["reason"], line.reason)
                if amount and not "".join(last["amount"]).strip():
                    last["amount"] = [line.amount]
                elif amount:
                    last["amount"] += ["", line.amount]         # 두 쪽에 다 금액이 적힌 경우. 문단을 갈라 둘 다 남긴다
        else:
            same = current is not None and rider and _title_key(rider) == name_key(current.title)
            if current is not None and _name_tail(prev, line, layout.name_tails):
                current.name.append(line.rider)     # 이름 꼬리는 앞 특별약관 이름에 잇고, 행은 그 특별약관의 다음 세부보장이다
            elif rider and not (same and cover):
                close()
                current = start(line.rider)
            elif current is None:
                # 특약 머리가 있는 표는 머리가 특별약관 이름이다. 그 밖에는 범위가 특별약관 가운데서 시작한 경우라
                # 첫 세부보장 이름을 제목으로 쓴다
                current = start(line.heading or None)
            inherited = line.amount is None or (not amount and line.top and bool(current.rows))
            # 병합된 지급사유 칸이 쪽을 넘었으면 표 하나 안에서 물려받은 글은 뒷부분뿐이다. 앞 행이 이어 붙인 글 전체를 물려받는다
            above = (list(current.rows[-1]["reason"]) if (layout.unnamed_rows or layout.shared_whole) and line.shared
                     and current.rows else None)
            current.add(line.cover, line.reason, list(last_amount) if inherited else [line.amount or ""], line.page,
                        current.around(line.levels) if line.levels else ((), ()))
            if above is not None:
                current.rows[-1]["reason"] = above
        last_amount = current.rows[-1]["amount"]
        current.last_page = max(current.last_page, line.page)
        prev = line
    close()
    return riders


def _title_key(cell: str) -> str:
    """특별약관 이름 칸의 글자를 묶는 중인 특별약관의 제목과 견줄 수 있게 줄인다. 제목처럼 "*7종에 한함"을 떼고 견준다."""
    return name_key(split_only(join_name(cell))[0])


def riders_from_tables(tables: Iterable[PageTable], layout: Layout = SAMSUNGFIRE) -> list[Rider]:
    """쪽 순서로 읽은 표들을 특별약관 조각으로 바꾼다. 급부 표가 아닌 표는 건너뛴다."""
    return group_riders((line for table in tables for line in table_lines(table, layout)), layout)


def applies_to(only: str, variant_name: str) -> bool:
    """적용 범위 표시가 이 종에 해당하는가. 표시가 없으면 모든 종에 해당한다.

    "7종에 한함"은 "7종(납입면제형)"에 해당하고 "8종(일반형)"에는 해당하지 않는다.
    종 번호가 없는 표시는 가릴 수 없으므로 해당하는 것으로 둔다.
    """
    wanted = variant_numbers(only)
    return not wanted or bool(wanted & variant_numbers(variant_name))


def variant_numbers(text: str) -> set[int]:
    """글에 적힌 종 번호들. "7종" → {7}, "1, 2, 3종" → {1, 2, 3}, "1~3종" → {1, 2, 3}, "6종, 7종 및 8종" → {6, 7, 8}."""
    out: set[int] = set()
    for run in _VARIANT.findall(text):
        last = None
        for sign, digits in _VARIANT_STEP.findall(run):
            n = int(digits)
            # "1~3"은 사이의 번호까지. 앞뒤가 뒤집혔거나 터무니없이 넓으면 범위로 보지 않고 적힌 번호만 넣는다
            out |= set(range(last, n + 1)) if sign and last is not None and 0 < n - last <= 30 else {n}
            last = n
    return out


def for_variant(riders: Iterable[Rider], variant_name: str) -> list[Rider]:
    """한 요약서가 여러 종을 함께 다룰 때, 이 종에 해당하는 특별약관과 세부보장만 남긴다."""
    out = []
    for r in riders:
        if not applies_to(r.only, variant_name):
            continue
        covers = tuple(c for c in r.covers if applies_to(c.only, variant_name))
        if covers:
            out.append(r if len(covers) == len(r.covers) else replace(r, covers=covers))
    return out


def to_blocks(riders: Iterable[Rider], max_covers: int | None = None) -> list[Block]:
    """특별약관 조각을 추출 단계가 쓰는 Block으로 바꾼다.

    max_covers를 주면 세부보장이 그보다 많은 특별약관을 여러 Block으로 나눈다. 나뉜 Block은 제목이 같고,
    쪽 범위는 그 Block에 든 세부보장의 것이다.
    """
    blocks = []
    for r in riders:
        if not max_covers or len(r.covers) <= max_covers:
            blocks.append(r.to_block())
            continue
        for i in range(0, len(r.covers), max_covers):
            part = r.covers[i:i + max_covers]
            rest = r.covers[i + max_covers:]
            last = rest[0].page if rest else r.last_page        # 다음 세부보장이 시작하는 쪽까지 이어질 수 있다
            blocks.append(replace(r, covers=part, first_page=part[0].page, last_page=max(part[-1].page, last)).to_block())
    return blocks


# ---------------------------------------------------------------------------
# JSON 쓰기·읽기
# ---------------------------------------------------------------------------

def _piece(r: Rider) -> dict[str, Any]:
    out: dict[str, Any] = {"특별약관": r.title, "구분": r.label, "적용범위": r.only, "첫쪽": r.first_page, "끝쪽": r.last_page}
    # 회사에 따라 생기는 값은 있을 때만 적는다(삼성화재 조각 파일의 꼴은 그대로다)
    if r.segment:
        out["형"] = r.segment
    if r.main is not None:
        out["주계약"] = r.main
    if r.parts:
        out["특약명들"] = list(r.parts)
    out["세부보장"] = [{"보장명": c.name, "지급사유": c.reason, "지급금액": c.amount, "쪽": c.page, "적용범위": c.only}
                   for c in r.covers]
    return out


def riders_to_json(riders: Iterable[Rider], source: dict[str, Any] | None = None,
                   notes: Sequence[dict[str, Any]] = ()) -> dict[str, Any]:
    """조각 목록을 JSON으로 쓸 수 있는 dict로 바꾼다. source에는 문서 이름·쪽 범위처럼 출처를 적는다.

    notes는 표 안의 주석 행(table_notes)이다. 있을 때만 "주석"으로 적는다. 조각으로 읽을 때는 쓰지 않는다.
    """
    out: dict[str, Any] = {"형식": FORMAT, "출처": dict(source or {})}
    if notes:
        out["주석"] = list(notes)
    out["조각"] = [_piece(r) for r in riders]
    return out


def riders_from_json(data: dict[str, Any]) -> list[Rider]:
    if not isinstance(data, dict) or data.get("형식") != FORMAT:
        raise ValueError("급부 표 조각 파일이 아닙니다")
    return [Rider(
        title=r["특별약관"],
        covers=tuple(Cover(c["보장명"], c["지급사유"], c["지급금액"], int(c["쪽"]), c.get("적용범위", ""))
                     for c in r["세부보장"]),
        first_page=int(r["첫쪽"]), last_page=int(r["끝쪽"]), label=r.get("구분", ""), only=r.get("적용범위", ""),
        segment=r.get("형", ""), main=r.get("주계약"), parts=tuple(r.get("특약명들", ())),
    ) for r in data["조각"]]


def write_riders(path: Path | str, riders: Iterable[Rider], source: dict[str, Any] | None = None,
                 notes: Sequence[dict[str, Any]] = ()) -> None:
    """조각 목록을 JSON 파일로 쓴다."""
    Path(path).write_text(json.dumps(riders_to_json(riders, source, notes), ensure_ascii=False, indent=1), encoding="utf-8")


def read_riders(path: Path | str) -> list[Rider]:
    """write_riders로 쓴 파일을 읽는다."""
    return riders_from_json(json.loads(Path(path).read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# 급부 표가 있는 쪽 범위 찾기
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PageRange:
    first_page: int             # "□ 보험금 지급사유 및 지급금액"이 적힌 쪽
    last_page: int              # "□ 보험금 지급제한사항"이 적힌 쪽. 표가 그 쪽 위쪽까지 이어질 수 있어 포함한다


def benefit_ranges(pages: dict[int, str], layout: Layout = SAMSUNGFIRE) -> list[PageRange]:
    """쪽별 글자에서 급부 표가 있는 쪽 범위를 모두 찾는다. 종 구간마다 절이 따로 있는 요약서는 여러 개가 나온다.

    pages는 segment.pages_from_text나 page_texts가 돌려주는 {쪽 번호: 글자}다. 절 제목의 꼴은 layout이 정한다.
    """
    ranges: list[PageRange] = []
    start: int | None = None
    for n in sorted(pages):
        for line in pages[n].split("\n"):
            line = line.strip()
            if layout.section_start.match(line):
                if start is not None:
                    ranges.append(PageRange(start, n))
                start = n
            elif start is not None and layout.section_end.match(line):
                ranges.append(PageRange(start, n))
                start = None
    if start is not None:
        ranges.append(PageRange(start, max(pages)))
    return ranges


def benefit_pages(pages: dict[int, str], section: str | None = None, layout: Layout = SAMSUNGFIRE) -> PageRange:
    """급부 표의 쪽 범위 하나를 고른다.

    section은 종 구간의 제목 줄이다(예: "나. 8종(일반형)"). 주면 그 줄이 적힌 쪽부터 찾아 처음 시작하는 급부 절을
    고른다. 안 주면 급부 절이 하나일 때만 돌려주고, 여럿이면 어느 구간인지 정하라고 ValueError를 낸다.
    """
    ranges = benefit_ranges(pages, layout)
    if not ranges:
        raise ValueError(f"'{layout.section_title}' 절을 찾지 못했습니다")
    if section is None:
        if len(ranges) > 1:
            found = ", ".join(f"{r.first_page}~{r.last_page}쪽" for r in ranges)
            raise ValueError(f"급부 절이 {len(ranges)}곳입니다({found}). 구간 제목(section)을 정해 주세요")
        return ranges[0]
    wanted = squash(section)
    at = next((n for n in sorted(pages) if any(squash(l) == wanted for l in pages[n].split("\n"))), None)
    if at is None:
        raise ValueError(f"구간 제목 {section!r}을(를) 찾지 못했습니다")
    for r in ranges:
        if r.first_page >= at:
            return r
    raise ValueError(f"구간 제목 {section!r} 뒤에 급부 절이 없습니다")


# ---------------------------------------------------------------------------
# PDF에서 표 읽기 (pdfplumber를 쓰는 부분)
# ---------------------------------------------------------------------------

_THIN = 2.0          # 이보다 가는 사각형은 표의 선이다. 굵은 사각형은 칸 바탕색이나 글자 줄의 배경이다
_SNAP = 1.5          # 같은 선, 같은 자리로 볼 좌표 차이


def _open(source: Path | str | bytes):
    import pdfplumber

    return pdfplumber.open(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else str(source))


def page_texts(source: Path | str | bytes) -> dict[int, str]:
    """PDF의 쪽별 글자. 글자 파일이 없을 때 benefit_ranges에 넣는다."""
    with _open(source) as pdf:
        return {i: page.extract_text() or "" for i, page in enumerate(pdf.pages, 1)}


def _edge(x0: float, top: float, x1: float, bottom: float) -> dict[str, Any]:
    return {"x0": x0, "x1": x1, "top": top, "bottom": bottom, "width": x1 - x0, "height": bottom - top,
            "orientation": "h" if top == bottom else "v", "object_type": "rect_edge"}


def _border_edges(page: Any, dotted: bool = False, fills: bool = False) -> tuple[list[dict], list[dict]]:
    """표의 선만 골라 (가로선, 세로선)으로 돌려준다.

    이 문서들은 표의 선을 가는 채움 사각형으로 그린다. 굵은 채움 사각형(머리행 바탕색, 글자 줄의 흰 배경)까지
    선으로 치면 글자 줄마다 행이 갈린다. 가는 것만 선으로 보고, 테두리를 그은 사각형은 네 변을 선으로 본다.
    한 줄 위에서 칸마다 토막 난 선은 이어 붙인다.
    dotted(Layout.dotted)이면 점선의 점(가로세로 모두 짧은 선 토막)을 더 긴 쪽의 방향으로 본다. 세로 점선의 점은 높이만
    조금 있어 그대로 두면 가로선 토막으로 읽혀 버려진다.
    fills(Layout.cell_fills)이면 높이가 25pt 이하인 바탕색 사각형(머리행 칸의 바탕)의 왼쪽, 오른쪽 변도 세로선으로 본다.
    머리행 칸 사이에 선 없이 바탕색만 칸마다 칠한 표가 있다.
    """
    raw: list[tuple[str, float, float, float]] = []            # (방향, 선이 놓인 좌표, 시작, 끝)
    for r in page.rects:
        w, h = r["x1"] - r["x0"], r["bottom"] - r["top"]
        if min(w, h) <= _THIN:
            if w >= h:
                raw.append(("h", (r["top"] + r["bottom"]) / 2, r["x0"], r["x1"]))
            else:
                raw.append(("v", (r["x0"] + r["x1"]) / 2, r["top"], r["bottom"]))
        elif r.get("stroke") and r.get("linewidth"):
            raw += [("h", r["top"], r["x0"], r["x1"]), ("h", r["bottom"], r["x0"], r["x1"]),
                    ("v", r["x0"], r["top"], r["bottom"]), ("v", r["x1"], r["top"], r["bottom"])]
        elif fills and r.get("fill") and h <= 25 and w >= 10:
            raw += [("v", r["x0"], r["top"], r["bottom"]), ("v", r["x1"], r["top"], r["bottom"])]
    for l in page.lines:
        if dotted and abs(l["x0"] - l["x1"]) < abs(l["top"] - l["bottom"]) <= _SNAP:
            raw.append(("v", (l["x0"] + l["x1"]) / 2, l["top"], l["bottom"]))
        elif abs(l["top"] - l["bottom"]) <= _SNAP:
            raw.append(("h", (l["top"] + l["bottom"]) / 2, l["x0"], l["x1"]))
        elif abs(l["x0"] - l["x1"]) <= _SNAP:
            raw.append(("v", (l["x0"] + l["x1"]) / 2, l["top"], l["bottom"]))

    def joined(kind: str) -> list[tuple[float, float, float]]:
        groups: list[list[tuple[float, float, float]]] = []     # 놓인 좌표가 같은 토막끼리
        for at, a, b in sorted((at, a, b) for k, at, a, b in raw if k == kind):
            if groups and at - groups[-1][0][0] <= _SNAP:
                groups[-1].append((at, a, b))
            else:
                groups.append([(at, a, b)])
        out: list[list[float]] = []
        for group in groups:
            line: list[float] | None = None
            for _, a, b in sorted(group, key=lambda p: p[1]):
                if line is not None and a <= line[2] + _SNAP:
                    line[2] = max(line[2], b)
                else:
                    line = [group[0][0], a, b]
                    out.append(line)
        return [(at, a, b) for at, a, b in out if b - a >= 3]

    return ([_edge(a, at, b, at) for at, a, b in joined("h")],
            [_edge(at, a, at, b) for at, a, b in joined("v")])


def _frame_caps(v: list[dict]) -> list[dict]:
    """세로선들이 함께 시작하거나 끝나는 높이에 그 세로선들을 잇는 가로선(Layout.close_frame).

    쪽을 넘어 이어지는 병합 칸(특약 이름 칸, 지급금액 칸)은 쪽 끝에 아래 선이 그어져 있지 않다. 그대로 두면 칸이 닫히지
    않아 표를 찾을 때 그 칸의 글자를 잃는다. 같은 높이에서 끝나는 세로선들이 쪽의 세로선 전체 너비의 대부분을 덮을 때만
    (표 테두리가 끝나는 자리) 가로선을 더한다. 이미 선이 있는 자리에 더해도 표는 달라지지 않는다.
    """
    if len(v) < 2:
        return []
    width = max(e["x0"] for e in v) - min(e["x0"] for e in v)
    out = []
    for key in ("top", "bottom"):
        groups: list[list[tuple[float, float]]] = []
        for y, x in sorted((e[key], e["x0"]) for e in v):
            if groups and y - groups[-1][0][0] <= _SNAP:
                groups[-1].append((y, x))
            else:
                groups.append([(y, x)])
        for group in groups:
            xs = [x for _, x in group]
            if len(group) >= 2 and max(xs) - min(xs) >= 0.9 * width:
                out.append(_edge(min(xs), group[0][0], max(xs), group[0][0]))
    return out


def _side_edges(h: list[dict], v: list[dict]) -> list[dict]:
    """표 양옆에 테두리가 없는 표의 왼쪽, 오른쪽 세로선(Layout.open_sides).

    행을 가르는 가로선은 표 양 끝까지 그어져 있다. 끝 자리가 같은 가로선 둘 사이를 두 선이 걸친 너비 안의 세로선(칸 경계)이
    다 덮고 있으면 두 선은 한 표의 행이므로, 끝 자리에 두 선을 잇는 세로선을 더한다(지급금액 칸만 가르는 점선처럼 한쪽 선이
    짧아도 긴 선의 너비 안에서 찾는다). 표와 표 사이(앞 표의 아래 선과 다음 표의 위 선 사이)는 칸 경계가 덮지 않아
    잇지 않는다. 이미 선이 있는 자리에 더해도 표는 달라지지 않는다.
    """
    out = []
    for key in ("x0", "x1"):
        groups: list[list[dict]] = []
        for e in sorted(h, key=lambda e: (e[key], e["top"])):
            if groups and abs(e[key] - groups[-1][-1][key]) <= 2 * _SNAP:
                groups[-1].append(e)
            else:
                groups.append([e])
        for group in groups:
            group.sort(key=lambda e: e["top"])
            for a, b in zip(group, group[1:]):
                if b["top"] - a["top"] <= _SNAP:
                    continue
                left, right = min(a["x0"], b["x0"]) + _SNAP, max(a["x1"], b["x1"]) - _SNAP
                if any(left < e["x0"] < right and e["top"] <= a["top"] + _SNAP and e["bottom"] >= b["top"] - _SNAP
                       for e in v):
                    # 끝 자리가 조금씩 어긋난 두 선(머리행 선이 1~2pt 짧다)은 두 자리에 다 세운다. 표를 찾을 때 한 자리로 모인다
                    out += [_edge(x, a["top"], x, b["top"]) for x in sorted({a[key], b[key]})]
    return out


def _find(page: Any, h: list[dict], v: list[dict]) -> list[Any]:
    if len(h) < 2 or len(v) < 2:
        return []
    return page.find_tables({"vertical_strategy": "explicit", "horizontal_strategy": "explicit",
                             "explicit_vertical_lines": v, "explicit_horizontal_lines": h,
                             "snap_tolerance": _SNAP, "join_tolerance": _SNAP, "intersection_tolerance": 2})


def _within(chars: list[dict], bbox: Sequence[float]) -> list[dict]:
    """이 상자에 든 글자. 글자의 자리("at")가 상자 안에 있는가로 가린다."""
    return [c for c in chars if bbox[0] <= c["at"][0] < bbox[2] and bbox[1] <= c["at"][1] < bbox[3]]


def _numbered(chars: list[dict], frame: Sequence[float] | None = None) -> list[dict]:
    """글자마다 PDF에 적힌 차례("n")와 칸을 가릴 때 쓸 자리("at")를 붙인다.

    자리는 글자의 가운데다. 다만 줄 끝에 매달린 빈칸과 쉼표·마침표는 바로 앞 글자의 자리를 물려받는다.
    꽉 찬 줄의 끝 빈칸과 문장부호는 칸 경계 밖에 놓이기도 해서, 제 자리로 칸을 고르면 옆 칸으로 가거나 빠진다.
    빈칸이 빠지면 낱말 사이에서 바뀐 줄까지 붙여 쓰게 된다.

    frame(표의 테두리 상자)을 주면 표 왼쪽이나 오른쪽 테두리에 걸쳐 찍힌 글자의 자리를 테두리 안쪽으로 옮긴다.
    가운데 맞춘 이름이 칸보다 넓으면 줄 첫 글자나 끝 글자가 표 바깥 테두리를 넘어 찍힌다(넘은 부분은 잘려 보이지 않는다).
    글자의 가운데가 테두리 밖이라도 글자가 테두리에 걸쳐 있으면 맨 바깥 칸의 글자다. 테두리에 닿지 않은 표 밖 글자는 그대로 둔다.
    """
    out = []
    prev: dict | None = None
    for n, c in enumerate(chars):
        at = ((c["x0"] + c["x1"]) / 2, (c["top"] + c["bottom"]) / 2)
        if frame is not None and frame[1] <= at[1] < frame[3]:
            if at[0] < frame[0] < c["x1"]:
                at = (frame[0], at[1])
            elif c["x0"] < frame[2] <= at[0]:
                at = (frame[2] - _SNAP, at[1])
        hanging = c["text"].isspace() or c["text"] in ",."
        if hanging and prev is not None and abs(c["top"] - prev["top"]) <= 3 and c["x0"] >= prev["x0"]:
            at = prev["at"]
        c = {**c, "n": n, "at": at}
        if not c["text"].isspace():
            prev = c
        out.append(c)
    return out


@dataclass(frozen=True)
class _TextLine:
    top: float
    text: str               # 낱말 사이에서 끝난 줄은 끝에 빈칸이 남아 있다
    right: float            # 글자가 끝나는 오른쪽 좌표
    first: int              # 첫 글자와 끝 글자의 차례
    last: int
    shared: bool            # 같은 높이에 다른 줄이 겹쳐 찍혀 있는가


def _text_lines(chars: list[dict], gaps: bool = True) -> list[_TextLine]:
    """글자들을 줄로 묶는다.

    같은 높이의 글자를 한 줄로 보되, 적힌 차례대로 따라가다 왼쪽으로 되돌아가면 다른 줄로 가른다.
    칸 높이에 가려 보이지 않는 글자가 아랫줄과 같은 자리에 찍혀 있는 곳이 있어서다. 가르지 않으면 두 줄의 글자가 섞인다.
    gaps이면 글자 사이가 2.5pt보다 벌어진 자리에 빈칸을 넣는다. 아니면 PDF에 적힌 빈칸 글자만 빈칸이다(Layout.spaced_names).
    """
    levels: list[list[dict]] = []
    for c in sorted(chars, key=lambda c: ((c["top"] + c["bottom"]) / 2, c["x0"])):
        mid = (c["top"] + c["bottom"]) / 2
        if levels and abs(mid - (levels[-1][0]["top"] + levels[-1][0]["bottom"]) / 2) <= 3:
            levels[-1].append(c)
        else:
            levels.append([c])
    out = []
    for level in levels:
        runs: list[list[dict]] = []
        for c in sorted(level, key=lambda c: c["n"]):
            if runs and c["x0"] >= runs[-1][-1]["x0"] - 1:
                runs[-1].append(c)
            else:
                runs.append([c])
        for run in runs:
            ordered = sorted(run, key=lambda c: c["x0"])
            text = ""
            for before, c in zip([None] + ordered[:-1], ordered):
                if gaps and before is not None and c["x0"] - before["x1"] > 2.5 and not text.endswith(" "):
                    text += " "
                text += c["text"]
            body = re.sub(r"\s+", " ", text).strip()
            if body:
                out.append(_TextLine(level[0]["top"], body + (" " if text[-1:].isspace() else ""),
                                     max(c["x1"] for c in run if not c["text"].isspace()),
                                     run[0]["n"], run[-1]["n"], len(runs) > 1))
    return sorted(out, key=lambda l: (l.top, l.first))


def _cell_text(chars: list[dict], inner: list[Any], gaps: bool = True) -> str:
    """칸 하나의 글자. 칸 안에 작은 표가 있으면 그 자리에 "· 왼쪽 칸: 오른쪽 칸" 줄로 풀어 넣는다.

    작은 표의 마지막 칸에서 넘쳐 가려진 글자(바깥 글과 겹쳐 찍힌 줄)는 그 칸의 글 끝에 붙인다.
    gaps가 거짓이면 작은 표 밖의 글은 PDF에 적힌 빈칸 글자만 빈칸으로 읽는다(_text_lines).
    """
    loose = _text_lines([c for c in chars if not any(_within([c], t.bbox) for t in inner)], gaps)
    pieces: list[tuple[float, int, str]] = []
    for t in inner:
        rows = []
        for row in t.rows:
            cells = [_within(chars, cell) for cell in row.cells if cell is not None]
            rows.append([(max((c["n"] for c in cell), default=-1), [l.text for l in _text_lines(cell)]) for cell in cells])
        if rows and rows[-1]:
            end, texts = rows[-1][-1]
            spill = next((l for l in loose if l.shared and 0 < l.first - end <= 3), None)
            if spill is not None:
                texts.append(spill.text)
                loose.remove(spill)
        lines = []
        for row in rows:
            cells = [join_text("\n".join(texts)).replace("\n", " ") for _, texts in row]
            cells = [c for c in cells if c]
            if len(cells) > 1:
                lines.append(f"· {cells[0].replace(' ', '')}: {' '.join(cells[1:])}")
            elif cells:
                lines.append(f"· {cells[0]}")
        if lines:
            first = min((c["n"] for c in _within(chars, t.bbox)), default=0)
            pieces.append((t.bbox[1], first, "\n" + "\n".join(lines) + "\n"))      # 앞뒤 빈 줄로 문단을 끊는다
    pieces += [(l.top, l.first, l.text) for l in loose]
    return "\n".join(text for _, _, text in sorted(pieces))


def _header(table: Any, chars: list[dict], layout: Layout = SAMSUNGFIRE) -> tuple[float, float] | None:
    """급부 표이면 (지급사유 칸의 왼쪽 좌표, 지급금액 칸의 왼쪽 좌표), 아니면 None.

    머리행에 보장명 칸의 말(Layout.name_heads 가운데 하나), 지급사유, 지급금액이 모두 있어야 한다.
    """
    words = _head_words(layout)
    found: dict[str, float] = {}
    for row in table.rows[:4]:
        for cell in row.cells:
            if cell is None:
                continue
            word = squash("".join(c["text"] for c in _within(chars, cell)))
            if word in words:
                found.setdefault(word, cell[0])
    if (any(w in found for w in layout.name_heads) and all(w in found for w in _HEAD_WORDS[1:])
            and found["지급사유"] < found["지급금액"]):
        return found["지급사유"], found["지급금액"]
    return None


@dataclass
class _Marks:
    """표 위에 적힌 표시들. 쪽을 넘어 다음 표로 이어진다."""
    label: str = ""             # 구분("기본계약", "선택계약")
    segment: str = ""           # 지금 표들의 형
    product: str = ""           # 마지막으로 본 형 구간 머리의 형
    segments: list[str] = field(default_factory=list)       # 이 문서에서 본 형들
    heading: str = ""           # 특약 머리. 비어 있으면 보통 표다
    # 마지막으로 읽은 급부 표의 (지급사유 칸 왼쪽, 지급금액 칸 왼쪽, 표 왼쪽, 표 오른쪽). 머리행 없이 이어진 표를 알아볼 때 쓴다
    frame: tuple[float, float, float, float] | None = None
    group: str = ""             # 마지막으로 읽은 묶음 칸의 글(Layout.group_column). 쪽 첫 행의 빈 묶음 칸이 물려받는다


def _marks(page: Any, top: float, floor: float, span: tuple[float, float] | None = None) -> list[str]:
    """표 바로 위(앞 표의 아래부터)에 적힌 줄들. span(왼쪽, 오른쪽)을 주면 그 단 안의 글자만 읽는다(Layout.two_up)."""
    if top - floor < 3:
        return []
    left, right = span or (page.bbox[0], page.bbox[2])
    text = page.crop((left, max(floor, page.bbox[1]), right, top)).extract_text() or ""
    return text.split("\n")


def _group_rows(table: Any, rows: list[list[str | None]], marks: _Marks,
                layout: Layout) -> tuple[list[list[str | None]], tuple[str, ...]]:
    """맨 왼쪽의 묶음 칸(Layout.group_column)을 떼고 행마다 구분을 정한다. 묶음 칸이 없는 표는 칸을 그대로 두고, 구분은
    표 위 구분 줄의 구분(없으면 Layout.group_other)이다.

    묶음 칸은 너비가 25pt보다 좁고, 글이 있으면 줄마다 한 글자다(세로쓰기). 묶음 이름이 Layout.group_labels 가운데 하나
    (한쪽이 다른 쪽의 앞부분이면 같다고 본다. 병합된 칸이 쪽을 넘으면 이름이 잘려 찍힌다)면 그것이 구분이고, 다른 이름이면
    Layout.group_other, 이름이 없으면 표 위 구분 줄의 구분이다. 위 행과 병합된 칸(None)과 쪽 첫 행의 빈 칸은 앞의 이름을 물려받는다.
    """
    found = _columns(rows, layout)
    count = found[0] if found else 0
    body = [(cells, i) for i, cells in enumerate(table.rows[count:], count)
            if cells.cells and cells.cells[0] is not None]
    plain = (rows, (marks.label or layout.group_other,) * len(rows))
    if not body or len(rows[0]) < 4:
        return plain
    for cells, i in body:
        x0, _, x1, _ = cells.cells[0]
        lines = [l.strip() for l in (rows[i][0] or "").split("\n") if l.strip()]
        if x1 - x0 >= 25 or any(len(l) > 1 for l in lines):
            return plain
    labels: list[str] = [marks.label] * count
    for row in rows[count:]:
        text = squash(row[0])
        if text:
            marks.group = text
        group = marks.group
        known = next((l for l in layout.group_labels if len(group) >= 2
                      and (squash(l).startswith(group) or group.startswith(squash(l)))), None)
        labels.append(known or (layout.group_other if group else marks.label))
    return [row[1:] for row in rows], tuple(labels)


def _rider_heading(text: str, marks: _Marks, layout: Layout) -> None:
    """특약 머리. 형 구간이 있는 문서에서는 머리의 "(…형)"으로 형을 고르고, 형이 적히지 않았으면 Layout.common이다."""
    marks.heading = text
    if marks.segments:
        key = squash(text)
        marks.segment = next((s for s in marks.segments if f"({squash(s)})" in key), layout.common)
    else:
        marks.segment = marks.product


def _read_marks(lines: Iterable[str], marks: _Marks, layout: Layout) -> None:
    """표 위 줄들을 차례로 읽어 구분, 형, 특약 머리를 바꾼다.

    - 구분 줄(삼성화재 "◆ 기본계약", 메리츠화재 "m 기본계약")은 구분을 바꾸고 특약 머리를 끝낸다.
      구분 줄에 Layout.rider_word("특별약관")가 있으면 구분이 아니라 특약 머리다("m 무배당 … 특별약관2610").
    - "< … >" 줄은 Layout.rider_word가 있으면 특약 머리, 없으면 형 구간 머리다. 형은 끝 괄호 안 글자다
      ("< 무배당 가나보험(다라형) >" → "다라형"). 두 줄로 갈려 적혔으면 ">"가 나올 때까지 잇는다.
    - Layout.segment_line에 맞는 줄(KB라이프생명 "가. 간편심사형(3.5.5), 간편심사형(3.3.5)")은 형 구간을 열고
      구분과 특약 머리를 비운다. 형은 group(1)이다("간편심사형").
    """
    buffer = ""
    for raw in lines:
        line = raw.strip()
        found = layout.segment_line.match(line) if layout.segment_line is not None else None
        if found:
            # 형 구간 줄("가. 간편심사형(3.5.5), 간편심사형(3.3.5)"). 구분과 특약 머리는 새 구간에서 다시 적힌다
            marks.product = marks.segment = found.group(1)
            if marks.product not in marks.segments:
                marks.segments.append(marks.product)
            marks.label = marks.heading = ""
            continue
        if layout.heading is not None and (buffer or line[:1] in "<＜"):
            buffer = f"{buffer} {line}".strip()
            if not buffer.endswith((">", "＞")) and len(buffer) < 300:
                continue
            line, buffer = buffer, ""
            m = layout.heading.match(line)
            if m:
                text = re.sub(r"\s+", " ", m.group(1))
                if layout.rider_word and layout.rider_word in text:
                    _rider_heading(text, marks, layout)
                else:
                    found = re.search(r"\(([^()]*)\)\s*$", text)
                    marks.product = marks.segment = found.group(1) if found else text
                    if marks.product not in marks.segments:
                        marks.segments.append(marks.product)
                    marks.heading = ""
                continue
        m = layout.label.match(line)
        if m:
            text = re.sub(r"\s+", " ", m.group(1))
            if layout.rider_word and layout.rider_word in text:
                _rider_heading(text, marks, layout)
            else:
                marks.label, marks.heading, marks.segment = text, "", marks.product


def _column_numbers(table: Any, columns: tuple[float, float]) -> tuple[int, int] | None:
    """칸 자리(지급사유 칸 왼쪽, 지급금액 칸 왼쪽)로 찾은 (지급사유 칸 번호, 지급금액 칸 번호)."""
    def number(x: float) -> int | None:
        return min((j for row in table.rows for j, cell in enumerate(row.cells)
                    if cell is not None and abs(cell[0] - x) <= 2 * _SNAP), default=None)
    reason, amount = number(columns[0]), number(columns[1])
    return (reason, amount) if reason is not None and amount is not None and 0 < reason < amount else None


def _continued(table: Any, marks: _Marks, layout: Layout) -> tuple[float, float] | None:
    """머리행 없이 앞 쪽 급부 표가 이어지는 표이면 (지급사유 칸 왼쪽, 지급금액 칸 왼쪽). Layout.headless인 회사만.

    표의 양 끝과 지급사유, 지급금액 칸의 자리가 마지막으로 읽은 급부 표와 같으면 이어지는 표로 본다.
    """
    if not layout.headless or marks.frame is None:
        return None
    reason_left, amount_left, left, right = marks.frame
    if abs(table.bbox[0] - left) > 3 or abs(table.bbox[2] - right) > 3:
        return None
    return (reason_left, amount_left) if _column_numbers(table, (reason_left, amount_left)) else None


def _open_end(table: Any, chars: list[dict], columns: tuple[float, float], inner: list[Any]) -> bool:
    """표의 마지막 행에서 지급사유의 마지막 줄이 칸 너비를 꽉 채웠는가. 그렇다면 문장이 다음 쪽으로 이어진다.

    낱말 가운데서 바뀐 줄은 칸 너비를 꽉 채워 오른쪽 끝이 가지런하고, 문단이 끝나는 줄은 대개 그보다 짧다.
    지급사유 칸의 줄들에서 가장 흔한 오른쪽 끝을 꽉 찬 줄의 끝으로 본다(그런 줄이 둘도 없으면 판단하지 않는다).
    """
    reason_left, amount_left = columns
    rights: list[float] = []
    last = None
    rows = table.rows
    for i, row in enumerate(rows):
        for cell in row.cells:
            if cell is None or not reason_left - _SNAP <= cell[0] < amount_left - _SNAP:
                continue
            lines = _text_lines([c for c in _within(chars, cell) if not any(_within([c], t.bbox) for t in inner)])
            rights += [l.right for l in lines]
            if i == len(rows) - 1:
                last = lines[-1].right if lines else None
    counts: dict[int, int] = {}
    for right in rights:
        counts[round(right)] = counts.get(round(right), 0) + 1
    if last is None or not counts:
        return False
    margin = max(counts, key=lambda k: (counts[k], k))
    return counts[margin] >= 2 and last >= margin - _SNAP


def _covering(table: Any, i: int, j: int) -> tuple[float, float, float, float] | None:
    """i행 j칸 자리(병합되어 칸이 없는 자리)를 덮은 칸. 같은 행의 왼쪽 칸이거나 위 행에서 내려온 칸이다."""
    lefts = [r.cells[j][0] for r in table.rows if j < len(r.cells) and r.cells[j] is not None]
    if not lefts:
        return None
    x, y = lefts[0] + 2 * _SNAP, table.rows[i].bbox[1] + _SNAP
    return next((c for c in table.cells if c[0] <= x < c[2] and c[1] <= y < c[3]), None)


def _amount_parts(table: Any, i: int, cells: list[str | None], amount: int,
                  texts: dict[tuple, str]) -> list[str | None]:
    """지급금액 머리 아래가 여러 칸으로 갈린 행의 그 칸들을 지급금액 칸 하나로 모은다(Layout.amount_parts).

    지급금액 칸 오른쪽에 감액("1년미만 50%")이나 한도("연간 총 지급금액 … 한도") 칸이 여러 행에 걸쳐 병합되어 있거나,
    지급금액 칸 안이 이름 칸과 산식 칸으로 갈린 표가 있다. 칸마다 글을 왼쪽부터 빈 줄을 두고 잇는다(문단이 갈린다).
    위 행에서 병합되어 내려온 칸은 그 칸의 글(texts)을 쓰고, 같은 행의 왼쪽 칸이 옆으로 넓게 병합된 자리는 건너뛴다.
    지급금액 자리가 모두 위 행에서 내려온 행은 그대로 둔다(지급금액을 위 행에서 물려받는다). 모은 다음 오른쪽 칸들은 None이다.
    """
    if len(cells) <= amount + 1:
        return cells
    top = table.rows[i].bbox[1]
    parts: list[str] = []
    own = False
    seen: set[tuple] = set()
    for j in range(amount, len(cells)):
        if cells[j] is not None:
            parts.append(cells[j] or "")
            own = True
            continue
        cover = _covering(table, i, j)
        if cover is not None and cover not in seen and cover[1] < top - _SNAP:
            seen.add(cover)
            parts.append(texts.get(cover, ""))
    if not own:
        return cells
    return cells[:amount] + ["\n\n".join(p for p in parts if p.strip())] + [None] * (len(cells) - amount - 1)


def _column_of(bbox: Sequence[float], page_bbox: Sequence[float], two_up: bool) -> int:
    """표가 쪽의 어느 단에 있는가(Layout.two_up). 표의 가운데가 쪽 가운데보다 왼쪽이면 0, 아니면 1. 두 단이 아니면 0."""
    return int(two_up and (bbox[0] + bbox[2]) / 2 >= (page_bbox[0] + page_bbox[2]) / 2)


def _page_tables(page: Any, number: int, marks: _Marks, layout: Layout = SAMSUNGFIRE,
                 misses: list[dict[str, Any]] | None = None) -> list[PageTable]:
    """한 쪽의 급부 표들. marks(표 위 표시)는 이 쪽에서 본 것으로 바꿔 다음 쪽으로 넘긴다.

    misses를 주면 급부 표로 읽지 못한 표(머리행이 없고 앞 표와 칸 자리도 다른 표)를 쪽 번호와 함께 적는다.
    Layout.two_up이면 쪽을 왼쪽 단과 오른쪽 단으로 나눠 단마다 위에서 아래로 읽는다(표의 가운데가 쪽 가운데의 어느 쪽인가로 가른다).
    """
    h, v = _border_edges(page, layout.dotted, layout.cell_fills)
    if layout.close_frame:
        h = h + _frame_caps(v)
    if layout.open_sides:
        v = v + _side_edges(h, v)
    chars = _numbered(page.chars)
    found = _find(page, h, v)
    mid = (page.bbox[0] + page.bbox[2]) / 2
    parts = (0, 1) if layout.two_up else (0,)

    def side(t: Any) -> int:
        return _column_of(t.bbox, page.bbox, layout.two_up)

    def span(part: int) -> tuple[float, float] | None:
        if not layout.two_up:
            return None
        return (page.bbox[0], mid) if part == 0 else (mid, page.bbox[2])

    heads = [(t, columns) for t in found for columns in [_header(t, chars, layout) or _continued(t, marks, layout)] if columns]
    if not heads:
        if layout.trailing:
            for part in parts:
                _read_marks(_marks(page, page.bbox[3], page.bbox[1], span(part)), marks, layout)
        return []

    def splits(e: dict, reason_left: float, amount_left: float) -> bool:
        """지급사유 칸을 세로로 갈라 칸을 하나 더 만드는 선인가(Layout.merged). 위아래 끝이 모두 행을 가르는 가로선
        (지급사유 칸 왼쪽 경계나 그 왼쪽에서 시작해 지급금액 칸까지 뻗는 선)에 닿는다. 작은 표의 세로선은 작은 표의
        가로선에 닿는다."""
        rows = [o["top"] for o in h if o["x0"] <= reason_left + _SNAP and o["x1"] >= amount_left - _SNAP]
        return (any(abs(e["top"] - y) <= _SNAP for y in rows) and any(abs(e["bottom"] - y) <= _SNAP for y in rows))

    def nested(e: dict) -> bool:
        """지급사유 칸 안에 든 작은 표의 선인가. 그대로 두면 바깥 표의 행이 그 선에서 갈린다.

        행을 가르는 가로선은 보장명 칸이나 지급금액 칸까지 뻗는다. 지급사유 칸 안에서 시작하고 끝나는 가로선과
        지급사유 칸 안쪽의 세로선은 작은 표의 것이다.
        """
        for t, (reason_left, amount_left) in heads:
            if e["bottom"] < t.bbox[1] - _SNAP or e["top"] > t.bbox[3] + _SNAP:
                continue
            if e["orientation"] == "h" and e["x0"] >= reason_left - _SNAP and e["x1"] <= amount_left + _SNAP:
                # 지급사유 머리 아래가 이름 칸과 지급사유 칸으로 갈린 표에서 지급사유 자리 너비를 다 차지한 가로선은 행을 가른다
                return not (layout.reason_rows and abs(e["x0"] - reason_left) <= _SNAP
                            and abs(e["x1"] - amount_left) <= _SNAP)
            if e["orientation"] == "v" and reason_left + _SNAP < e["x0"] < amount_left - _SNAP:
                return not (layout.merged and splits(e, reason_left, amount_left))
            # 지급금액 자리까지 차지한 작은 표(Layout.merged): 지급사유 칸 안쪽에서 시작해 표 오른쪽 테두리에 닿지 않는
            # 가로선, 지급사유 칸 안쪽부터 오른쪽 테두리 사이에 있는 세로선(지급금액 칸 경계는 빼고)
            right = t.bbox[2] - _SNAP
            if layout.merged and e["orientation"] == "h" and reason_left + _SNAP < e["x0"] and e["x1"] < right:
                return True
            if (layout.merged and e["orientation"] == "v" and reason_left + _SNAP < e["x0"] < right
                    and abs(e["x0"] - amount_left) > _SNAP):
                return not splits(e, reason_left, amount_left)
        return False

    inner_h, inner_v = ([e for e in h if nested(e)], [e for e in v if nested(e)]) if layout.inner_tables else ([], [])
    outer = found if misses is not None else [t for t, _ in heads]     # 읽지 못한 표를 적을 때는 다른 표도 훑는다
    inner: list[Any] = []
    if inner_h or inner_v:
        outer_h = [e for e in h if not nested(e)]
        outer = _find(page, outer_h, [e for e in v if not nested(e)])
        # 작은 표는 바깥 표와 선을 같이 쓰기도 한다. 지급사유 칸 너비를 다 차지하면 양옆 선을,
        # 쪽 끝에서 잘리면 바깥 행의 위아래 선을 같이 쓴다. 그 선을 보태서 작은 표를 찾는다
        sides, caps = [], []
        for t, (reason_left, amount_left) in heads:
            sides += [_edge(x, t.bbox[1], x, t.bbox[3]) for x in (reason_left, amount_left)]
            for e in inner_v:
                caps += [_edge(reason_left, o["top"], amount_left, o["top"]) for o in outer_h
                         if o["x0"] - _SNAP <= e["x0"] <= o["x1"] + _SNAP and t.bbox[1] - _SNAP <= o["top"] <= t.bbox[3] + _SNAP
                         and min(abs(o["top"] - e["top"]), abs(o["top"] - e["bottom"])) <= _SNAP]
        inner = _find(page, inner_h + caps, inner_v + sides)

    tables = []
    for part in parts:
        floor = page.bbox[1]
        for t in sorted((t for t in outer if side(t) == part), key=lambda t: t.bbox[1]):
            columns, head = _header(t, chars, layout), None
            numbers = _column_numbers(t, columns) if columns else None
            if columns is None:
                columns = _continued(t, marks, layout)
                numbers = _column_numbers(t, columns) if columns else None
                if numbers is None:
                    if misses is not None and _within(chars, t.bbox):
                        misses.append({"쪽": number, "이유": f"머리행이 없고 앞 급부 표와 칸 자리가 다른 표(위쪽 {t.bbox[1]:.0f}pt)"})
                    continue
                head = (0, *numbers)
            _read_marks(_marks(page, t.bbox[1], floor, span(part)), marks, layout)
            floor = t.bbox[3]
            mine = _within(_numbered(page.chars, t.bbox), t.bbox)       # 테두리에 걸친 글자까지 이 표의 글자로 본다
            open_end = _open_end(t, mine, columns, inner)
            rows = []
            texts: dict[tuple, str] = {}        # 칸 자리마다 읽은 글. 병합되어 아래 행까지 덮은 칸을 Layout.amount_parts가 찾는다
            for i, row in enumerate(t.rows):
                cells: list[str | None] = []
                for cell in row.cells:
                    if cell is None:
                        cells.append(None)
                        continue
                    small = [s for s in inner if cell[0] <= (s.bbox[0] + s.bbox[2]) / 2 < cell[2]
                             and cell[1] <= (s.bbox[1] + s.bbox[3]) / 2 < cell[3]]
                    named = layout.spaced_names and cell[2] <= columns[0] + _SNAP      # 지급사유 칸 왼쪽의 이름 칸
                    cells.append(_cell_text(_within(mine, cell), small, not named))
                    texts[cell] = cells[-1]
                if layout.merged and numbers and numbers[1] < len(cells) and cells[numbers[1]] is None and any(
                        c is not None and c[0] < columns[1] - _SNAP < columns[1] + _SNAP < c[2] for c in row.cells[:numbers[1]]):
                    cells[numbers[1]] = ""      # 지급사유 칸이 지급금액 자리까지 넓게 병합된 행. 위 행의 지급금액을 물려받지 않는다
                if layout.amount_parts and numbers:
                    cells = _amount_parts(t, i, cells, numbers[1], texts)
                rows.append(cells)
            labels: tuple[str, ...] = ()
            if layout.group_column:
                rows, labels = _group_rows(t, rows, marks, layout)
            tables.append(PageTable(number, rows, marks.label, open_end, marks.segment, marks.heading, head,
                                    part=part, labels=labels))
            marks.frame = (columns[0], columns[1], t.bbox[0], t.bbox[2])
        if layout.trailing:
            _read_marks(_marks(page, page.bbox[3], floor, span(part)), marks, layout)
    return tables


def read_tables(source: Path | str | bytes, first_page: int, last_page: int, layout: Layout = SAMSUNGFIRE,
                misses: list[dict[str, Any]] | None = None) -> list[PageTable]:
    """PDF의 쪽 범위(양 끝 포함)에서 급부 표를 읽는다. 머리행이 보장명·지급사유·지급금액인 표만 고른다.

    Layout.headless인 회사는 머리행 없이 앞 쪽 표가 이어지는 표도 읽는다. misses를 주면 급부 표를 하나도 찾지 못한 쪽과
    읽지 못한 표를 {"쪽", "이유"}로 적는다.
    """
    tables: list[PageTable] = []
    marks = _Marks()
    with _open(source) as pdf:
        for number in range(max(first_page, 1), min(last_page, len(pdf.pages)) + 1):
            page = pdf.pages[number - 1]
            found = _page_tables(page, number, marks, layout, misses)
            if misses is not None and not found:
                misses.append({"쪽": number, "이유": "급부 표를 찾지 못함"})
            tables += found
            page.flush_cache()
    return tables


def riders_from_pdf(source: Path | str | bytes, first_page: int | None = None, last_page: int | None = None,
                    section: str | None = None, pages: dict[int, str] | None = None,
                    layout: Layout = SAMSUNGFIRE) -> list[Rider]:
    """PDF(경로 또는 bytes)에서 급부 표를 읽어 특별약관 조각으로 돌려준다.

    쪽 범위를 주지 않으면 절 제목으로 찾는다. pages(쪽별 글자)를 주면 그것으로, 안 주면 PDF에서 글자를 풀어 찾는다.
    한 요약서에 급부 절이 여러 곳이면 section에 구간 제목을 준다(benefit_pages 참고).
    """
    if first_page is None or last_page is None:
        found = benefit_pages(pages if pages is not None else page_texts(source), section, layout)
        first_page, last_page = first_page or found.first_page, last_page or found.last_page
    return riders_from_tables(read_tables(source, first_page, last_page, layout), layout)


def rider_blocks_from_pdf(source: Path | str | bytes, first_page: int | None = None, last_page: int | None = None,
                          section: str | None = None, pages: dict[int, str] | None = None,
                          variant: str | None = None, max_covers: int | None = None,
                          layout: Layout = SAMSUNGFIRE) -> list[Block]:
    """PDF의 급부 표를 특별약관 단위 Block으로 돌려준다. segment.rider_blocks와 같은 자리에 쓴다.

    variant에 종 이름(예: "8종(일반형)")을 주면 "*7종에 한함"처럼 다른 종에만 해당하는 줄을 뺀다.
    """
    riders = riders_from_pdf(source, first_page, last_page, section, pages, layout)
    if variant:
        riders = for_variant(riders, variant)
    return to_blocks(riders, max_covers)


# ---------------------------------------------------------------------------
# 특약별 면책기간 표(Layout.wait_table)
# ---------------------------------------------------------------------------
# 현대해상 요약서는 "나. 보험금 지급제한 사항" 뒤에 "구 분 | 최초계약과 부활(효력회복)계약의 면책기간 | 보험금 감액기간 및
# 감액지급" 표를 싣는다. 급부 표의 지급사유는 이름 없는 "보장개시일 이후"만 적고, 특약마다 면책 날수는 이 표에만 있다.
# 표는 쪽마다 두 단이고, 특약 이름 칸 하나에 이름 여럿을 쉼표나 줄 바꿈으로 이어 적는다. 이름 칸과 면책기간 칸 사이에
# 대상 칸(암(유사암 제외), 유사암 따위)이나 세부보장 칸이 더 있는 행이 있고, 그러면 면책기간 칸이 대상마다 갈린다.
# 병합된 칸은 쪽이나 단을 넘어 이어진다(이어지는 표에는 머리행이 없고 면책기간 칸이 비어 있다).

_WAIT_HEAD = "면책기간"
_WAIT_VALUE = re.compile(r"(\d+)(?:(일)(?:면책)?|(개월|년)면책)")     # "90일", "90일면책", "1년면책". 날 단위 없는 "5년"은 읽지 않는다
_CONTINUE_TOP = 120     # 머리행 없이 이어지는 표는 단의 맨 위(쪽 위에서 이만큼 안)에서 시작한다
_NAME_SEPS = re.compile(r"(,|/|\n)")


@dataclass(frozen=True)
class WaitRow:
    """면책기간 표의 한 칸(특약 이름 칸 하나와 그 옆 면책기간 칸 하나).

    names_text는 특약 이름 칸의 글자(쪽이나 단을 넘어 이어진 칸은 줄을 바꿔 이어 붙인 것), detail은 이름 칸과 면책기간 칸
    사이 칸의 글자(대상이나 세부보장. 없으면 ""), wait는 면책기간 칸의 글자다. days는 wait를 줄마다 읽은 날수("-"는 0)이고,
    읽지 못한 줄이 있으면 None이다. cut과 half는 면책기간 칸 오른쪽의 "보험금 감액기간" 칸과 "50% 감액지급" 칸의 글자다
    (병합된 칸은 걸치는 행마다 같은 글자. 없으면 "").
    """
    page: int
    part: int
    names_text: str
    detail: str
    wait: str
    days: tuple[int, ...] | None
    cut: str = ""
    half: str = ""

    @property
    def cut_period(self) -> tuple[int, str] | tuple[()] | None:
        """감액기간 칸과 50% 감액지급 칸을 읽은 감액(wait_cut_text)."""
        return wait_cut_text(self.cut, self.half)


_CUT_PERIOD = re.compile(r"(?:최초계약일?부터)?(\d+)(년|개월)미만")
_MARK_YES = ("○", "◯", "O", "o", "〇")
_MARK_NO = ("X", "x", "×", "-", "–", "−")


def wait_cut_text(cut: str, half: str) -> tuple[int, str] | tuple[()] | None:
    """면책기간 표의 감액 두 칸을 읽는다. 감액기간 칸이 "최초계약일부터 1년미만"(또는 "1년 미만")이고 50% 감액지급 칸이 "○"면
    (1, "년")처럼 (기간, 단위), 감액기간 칸이 "-"이고 50% 감액지급 칸이 "X"나 "-"면 감액 없음(()), 그 밖의 꼴이나 두 칸이 서로
    맞지 않으면(기간은 있는데 "X") None."""
    flat_cut, flat_half = squash(cut), squash(half)
    if flat_cut in ("-", "–", "−") and flat_half in _MARK_NO:
        return ()
    m = _CUT_PERIOD.fullmatch(flat_cut)
    if m and flat_half in _MARK_YES:
        return int(m.group(1)), m.group(2)
    return None


def wait_days_text(text: str) -> tuple[int, ...] | None:
    """면책기간 칸의 글자를 줄마다 날수로. "90일면책", "90일 면책", "1년면책", "10일면책" → 날수, "-" → 0. 빈 줄은 건너뛴다.
    "5년 90일면책"처럼 꼴을 읽지 못한 줄이 하나라도 있으면 None."""
    out: list[int] = []
    # 좁은 칸에서 "90일"과 "면책"이 두 줄로 갈린 것은 한 줄로 잇는다
    for line in re.sub(r"\n\s*면\s*책", "면책", text or "").split("\n"):
        flat = squash(line)
        if not flat:
            continue
        if flat in ("-", "–", "−"):
            out.append(0)
            continue
        m = _WAIT_VALUE.fullmatch(flat)
        if not m:
            return None
        n, unit = int(m.group(1)), m.group(2) or m.group(3)
        out.append(n * 365 if unit == "년" else n * 30 if unit == "개월" else n)
    return tuple(out)


@dataclass
class _WaitGroup:
    page: int
    part: int
    names: list[str]
    rows: list[tuple[str, str, str, str]]   # (대상 칸 글자, 면책기간 칸 글자, 감액기간 칸 글자, 50% 감액지급 칸 글자)


def _overlap(a: Sequence[float], b: Sequence[float]) -> float:
    return min(a[3], b[3]) - max(a[1], b[1])


# (쪽, 단, 표 상자, [(칸 상자, 칸 글자)], 표 위 글자). 표 위 글자는 같은 단에서 앞 표의 아래(없으면 쪽 위)부터 이 표의 위까지의 글자
WaitCells = tuple[int, int, Sequence[float], Sequence[tuple[Sequence[float], str]], str]


def _wait_subrows(band: Sequence[float], wbox: Sequence[float], wtext: str,
                  details: Sequence[tuple[Sequence[float], str]],
                  rights: Sequence[tuple[Sequence[float], str]]) -> list[tuple[str, str, str, str]]:
    """면책기간 칸 하나의 (대상 칸 글자, 면책기간 칸 글자, 감액기간 칸 글자, 50% 감액지급 칸 글자) 행들.

    감액 두 칸은 면책기간 칸과 위아래로 겹치는 오른쪽 칸을 왼쪽 열부터 읽는다(감액기간 열, 50% 감액지급 열). 감액 칸이
    여러 면책기간 칸에 걸쳐 병합되어 있으면 그 칸마다 같은 글자를 짝짓는다. 거꾸로 면책기간 칸 하나가 감액기간 칸 여럿에
    걸쳐 병합되어 있으면(간편맞춤고지 형별 작은 표: "00형, 05형 …"과 "그 외 종형"이 면책은 같고 감액만 다르다) 감액기간 칸마다
    행을 나누고, 대상 칸도 그 감액기간 칸과 겹치는 것만 짝짓는다.
    """
    side = sorted((c for c in rights if _overlap(wbox, c[0]) > _SNAP), key=lambda c: (c[0][0], c[0][1]))
    columns: list[list[tuple[Sequence[float], str]]] = []
    for c in side:
        if columns and c[0][0] - columns[-1][0][0][0] <= 2 * _SNAP:
            columns[-1].append(c)
        else:
            columns.append([c])
    if len(columns) > 2:
        # 감액 비율 칸이 여럿인 표(가입금액 10%, 50%, 100% 지급)는 50% 감액지급 꼴이 아니다. 감액 칸을 읽지 못한 것으로 둔다
        return [(" ".join(squash(d[1]) for d in sorted((d for d in details if _overlap(band, d[0]) > _SNAP),
                                                        key=lambda d: (d[0][0], d[0][1]))),
                 wtext, "?", "?")]
    cut_cells = columns[0] if columns else []
    bands = [band] if len(cut_cells) <= 1 else \
        [(0, max(band[1], c[0][1]), 0, min(band[3], c[0][3])) for c in cut_cells]

    def text_in(cells: Sequence[tuple[Sequence[float], str]], area: Sequence[float]) -> str:
        return "\n".join(t for b, t in cells if _overlap(area, b) > _SNAP)

    out = []
    for sub in bands:
        found = sorted((d for d in details if _overlap(sub, d[0]) > _SNAP), key=lambda d: (d[0][0], d[0][1]))
        cut = text_in(cut_cells, sub) if len(cut_cells) > 1 else (cut_cells[0][1] if cut_cells else "")
        half = text_in(columns[1], sub) if len(columns) > 1 else ""
        out.append((" ".join(squash(d[1]) for d in found), wtext, cut, half))
    return out


def wait_rows_from_cells(tables: Iterable[WaitCells]) -> list[WaitRow]:
    """면책기간 표의 칸들을 행으로 읽는다(PDF 없이 돌아가는 부분).

    tables: 읽는 차례(쪽, 단, 위에서 아래)대로 WaitCells. 상자는 (x0, top, x1, bottom).
    - 머리행에 "면책기간" 칸이 있는 표: 그 칸의 왼쪽 끝이 면책기간 칸 자리다. 표의 왼쪽 끝에서 시작하는 칸이 특약 이름 칸,
      그 사이에서 시작하는 칸이 대상 칸이다. 머리행 아래의 칸만 읽는다.
    - 머리행이 없고 같은 단에서 머리행 표 뒤에 오는 표: 머리행의 면책기간 칸과 같은 자리(쪽 위 좌표)의 칸이 면책기간 칸이고,
      머리행 표의 왼쪽 끝에서 시작하는 칸이 이름 칸이다. 이름 칸이 없는 행은 이름을 표 위에 가로로 적은 꼴이라(이름 줄 아래에
      간편맞춤고지 형별 작은 표가 오는 행) 표 위 글자를 이름으로 쓴다.
    - 머리행이 없는 단의 첫 표이고 단의 맨 위(_CONTINUE_TOP)에서 시작하는 표: 앞 머리행의 면책기간 칸과 같은 자리(표 왼쪽
      끝에서 같은 거리)에 칸이 있으면 이어지는 표로 본다.
      맨 위 이름 칸 옆의 면책기간 칸이 모두 비어 있으면 앞 칸이 이어진 것이라 앞 특약 이름 칸에 글자를 잇는다.
    그 밖의 표는 읽지 않는다. 면책기간 칸 하나마다 그 칸과 위아래로 겹치는 이름 칸, 대상 칸의 글자를 짝짓는다.
    """
    groups: list[_WaitGroup] = []
    offset: float | None = None        # 마지막 머리행에서 면책기간 칸이 표 왼쪽 끝에서 떨어진 거리
    here: tuple[int, int, float, float] | None = None   # 마지막으로 읽은 표의 (쪽, 단, 이름 칸 x, 면책기간 칸 x)
    seen_parts: set[tuple[int, int]] = set()
    for page, part, box, cells, above in tables:
        first_in_part = (page, part) not in seen_parts
        seen_parts.add((page, part))
        head = next((c for c in cells if _wait_head_cell(c[1])), None) if _wait_head(cells) else None
        continued = False
        if head is not None:
            offset = head[0][0] - box[0]
            body = [c for c in cells if c[0][1] >= head[0][3] - _SNAP]
            name_x, wait_x = box[0], head[0][0]
        elif here is not None and here[:2] == (page, part):
            body = list(cells)
            name_x, wait_x = here[2], here[3]
        elif offset is not None and first_in_part and box[1] <= _CONTINUE_TOP:
            body = list(cells)
            name_x, wait_x = box[0], box[0] + offset
            continued = True
        else:
            continue
        waits = sorted((c for c in body if abs(c[0][0] - wait_x) <= 2 * _SNAP), key=lambda c: c[0][1])
        if head is not None:
            here = (page, part, name_x, wait_x)      # 머리행만 있는 표 아래에 본문 표가 따로 오기도 한다
        if not waits:
            if continued:
                offset = None
            continue
        here = (page, part, name_x, wait_x)
        names = sorted((c for c in body if abs(c[0][0] - name_x) <= 2 * _SNAP and squash(c[1])), key=lambda c: c[0][1])
        details = [c for c in body if name_x + 2 * _SNAP < c[0][0] < wait_x - 2 * _SNAP]
        rights = [c for c in body if c[0][0] > wait_x + 2 * _SNAP]      # 감액기간 칸, 50% 감액지급 칸
        loose = [w for w in waits if not any(_overlap(n[0], w[0]) > _SNAP for n in names)]
        if loose and squash(above) and head is None and not continued:
            names = sorted(names + [((name_x, min(w[0][1] for w in loose), wait_x, max(w[0][3] for w in loose)), above)],
                           key=lambda c: c[0][1])
        for i, (nbox, ntext) in enumerate(names):
            mine = [w for w in waits if _overlap(nbox, w[0]) > _SNAP]
            if continued and i == 0 and groups and all(not squash(w[1]) for w in mine):
                groups[-1].names.append(ntext)
                continue
            rows = []
            for wbox, wtext in mine:
                band = (0, max(nbox[1], wbox[1]), 0, min(nbox[3], wbox[3]))
                rows.extend(_wait_subrows(band, wbox, wtext, details, rights))
            groups.append(_WaitGroup(page, part, [ntext], rows))
    out = []
    for g in groups:
        text = "\n".join(g.names)
        for detail, wait, cut, half in g.rows:
            out.append(WaitRow(g.page, g.part, text, detail, wait, wait_days_text(wait), cut, half))
    return out


def _wait_page_tables(pdf: Any, number: int) -> list[WaitCells]:
    page = pdf.pages[number - 1]
    h, v = _border_edges(page)
    v = v + _side_edges(h, v)
    mid = (page.bbox[0] + page.bbox[2]) / 2
    found = sorted(_find(page, h, v), key=lambda t: (_column_of(t.bbox, page.bbox, True), t.bbox[1]))
    tables = []
    floor = {0: page.bbox[1], 1: page.bbox[1]}
    for t in found:
        part = _column_of(t.bbox, page.bbox, True)
        left, right = (page.bbox[0], mid) if part == 0 else (mid, page.bbox[2])
        above = ""
        if t.bbox[1] - floor[part] > 2 * _SNAP:
            above = page.crop((left, floor[part], right, t.bbox[1])).extract_text() or ""
        floor[part] = max(floor[part], t.bbox[3])
        cells = [(tuple(c), page.crop(c).extract_text() or "") for row in t.rows for c in row.cells if c]
        tables.append((number, part, tuple(t.bbox), cells, above))
    page.flush_cache()
    return tables


_HEAD_CELL = 40         # 머리 칸 글자 수 한도. 급부 표의 지급사유 칸에도 "면책기간", "감액기간"이 나온다


def _wait_head_cell(text: str) -> bool:
    flat = squash(text)
    return _WAIT_HEAD in flat and len(flat) <= _HEAD_CELL


def _wait_head(cells: Sequence[tuple[Sequence[float], str]]) -> bool:
    """면책기간 표의 머리행이 있는 표인가: 짧은 칸 하나에 "면책기간", 다른 짧은 칸에 "감액기간"이 있다."""
    flat = [squash(text) for _, text in cells]
    return (any(_wait_head_cell(t) for t in flat)
            and any("감액기간" in t and len(t) <= _HEAD_CELL and _WAIT_HEAD not in t for t in flat))


def wait_table(source: Path | str | bytes, pages: dict[int, str] | None = None) -> list[WaitRow]:
    """요약서 PDF에서 특약별 면책기간 표(Layout.wait_table)를 읽는다.

    쪽 글자(pages)에 "면책기"나 "부활(효력"이 든 쪽에서 머리행("면책기간" 칸과 "감액" 칸)이 있는 표를 찾고, 머리행이 있는
    첫 쪽부터 마지막 쪽의 다음 쪽까지 읽는다(머리행 없이 이어지는 쪽이 사이에 있다. 두 단 쪽 글자는 왼쪽 단과 오른쪽 단의 줄이
    섞여 머리 글자가 갈리기도 한다). 표 양옆에 테두리가 없어(Layout.open_sides) 가로선 끝 자리에 세로선을 더해 칸을 찾는다.
    쪽을 두 단으로 나눠 단마다 위에서 아래로 읽는다. 칸의 글자는 칸 상자로 자른 글자(pdfplumber crop)다.
    """
    texts = pages if pages is not None else page_texts(source)
    candidates = sorted(p for p, t in texts.items() if "면책기" in squash(t) or "부활(효력" in squash(t))
    found: dict[int, list[WaitCells]] = {}
    with _open(source) as pdf:
        heads = []
        for number in candidates:
            if 0 < number <= len(pdf.pages):
                found[number] = _wait_page_tables(pdf, number)
                if any(_wait_head(t[3]) for t in found[number]):
                    heads.append(number)
        if not heads:
            return []
        for number in range(heads[0], min(heads[-1] + 1, len(pdf.pages)) + 1):
            if number not in found:
                found[number] = _wait_page_tables(pdf, number)
        ordered = [t for number in range(heads[0], min(heads[-1] + 1, len(pdf.pages)) + 1) for t in found[number]]
    return wait_rows_from_cells(ordered)


def name_tokens(text: str) -> tuple[list[str], list[str]]:
    """특약 이름 칸의 글자를 쉼표, 빗금, 줄 바꿈마다 자른 토막(빈칸을 뗀 글)과 토막 사이의 구분("," "/" "\\n").
    이름 안의 쉼표와 줄 바꿈 자리에서도 자르므로 이름 하나가 이어진 토막 여럿일 수 있다(wait_name_spans가 다시 잇는다).
    토막 사이에 구분이 여럿이면(쉼표 뒤 줄 바꿈) 쉼표나 빗금을 남긴다."""
    parts = _NAME_SEPS.split(text or "")
    tokens: list[str] = []
    seps: list[str] = []
    pending = ""
    for i, part in enumerate(parts):
        if i % 2:
            if pending not in (",", "/"):
                pending = part
            continue
        flat = squash(part)
        if not flat:
            continue
        if tokens:
            seps.append(pending or "\n")
        tokens.append(flat)
        pending = ""
    return tokens, seps


def _top_groups(flat: str) -> tuple[str, list[str]] | None:
    """이름을 괄호 밖 글자와 맨 바깥 괄호 묶음들로 가른다. 괄호 짝이 맞지 않으면 None."""
    stem, groups, depth, start = "", [], 0, 0
    for i, ch in enumerate(flat):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return None
            if depth == 0:
                groups.append(flat[start:i + 1])
        elif depth == 0:
            stem += ch
    return (stem, groups) if depth == 0 else None


def wait_name_key(name: str) -> str:
    """면책기간 표의 이름과 급부 표의 특약 이름을 맞춰 보는 열쇠.

    빈칸과 줄 바꿈을 없애고(squash. 가운뎃점 모양도 맞춘다), 전각 괄호를 반각으로 바꾸고, 끝의 쉼표를 뗀다. 괄호 짝이 맞는
    이름은 괄호 밖 글자 뒤에 맨 바깥 괄호 묶음을 차례와 상관없이(정렬해) 붙인다. 면책기간 표는 같은 특약의 괄호 묶음 차례를
    급부 표와 다르게 적기도 한다("가나(간편)(연간1회한)"와 "가나(연간1회한)(간편)").
    """
    flat = squash(name).replace("（", "(").replace("）", ")").rstrip(",")
    split = _top_groups(flat)
    if split is None or not split[1]:
        return flat
    stem, groups = split
    return stem + "".join(sorted(groups))


_ATOM_SPLIT = re.compile(r"[(),]")


def _top_comma(text: str) -> bool:
    """괄호 밖에 쉼표가 있는가(이름 둘을 이은 글인가)."""
    depth = 0
    for ch in text:
        if ch in "(（":
            depth += 1
        elif ch in ")）":
            depth -= 1
        elif ch == "," and depth <= 0:
            return True
    return False


def wait_name_atoms(name: str) -> str:
    """괄호 구조가 다른 이름을 맞춰 보는 열쇠: 괄호와 쉼표로 자른 낱말들을 정렬해 이은 글.

    면책기간 표는 같은 특약의 괄호 묶음을 다르게 싸기도 하고("가나(상급종합병원(국립암센터포함),세기조절)치료"와
    "가나(세기조절)치료(상급종합병원(국립암센터포함))"), 급부 표 쪽 이름에 원문 괄호가 빠지기도 한다
    ("가나(상급종합병원(국립암센터포함)(치료당)"). 낱말과 그 수가 모두 같으면 같은 이름으로 본다.
    """
    flat = squash(name).replace("（", "(").replace("）", ")").rstrip(",")
    return "|".join(sorted(x for x in _ATOM_SPLIT.split(flat) if x))


def wait_name_spans(text: str, names: Iterable[str], most: int = 8,
                    atoms: bool = True) -> dict[str, list[tuple[int, int]]]:
    """특약 이름 칸의 글자에서 찾은 names의 이름과 그 토막 범위(시작, 끝+1. name_tokens의 토막 순번).

    이어진 토막을 구분과 함께 이어 붙여(줄 바꿈은 빈 글, 쉼표와 빗금은 그 글자) 이름의 열쇠(wait_name_key)와 같으면 그 이름이다.
    atoms가 참이면 열쇠가 맞지 않는 토막 이음도 괄호 구조만 다른 이름(wait_name_atoms가 같음)이면 그 이름으로 본다. 단 names
    안에서 그 열쇠를 가진 이름이 하나뿐이고 이어 붙인 글의 괄호가 닫혀 있을 때만이다.
    줄 바꿈 자리는 이름 사이일 수도, 이름 가운데일 수도 있다. 이름 첫머리는 칸의 첫 토막이거나, 앞 구분이 쉼표나 빗금이거나,
    앞 구분이 줄 바꿈이고 이 토막이 괄호로 시작하지 않으며 앞 토막이 ")"로 끝나거나 앞 토막 안의 괄호가 닫혀 있는 자리다
    ("가나진단" 다음 줄의 "다라진단"). 이름 끝은 칸의 끝 토막이거나,
    뒤 구분이 쉼표나 빗금이거나, 뒤 구분이 줄 바꿈이고 이어 붙인 글의 괄호가 닫혀 있으며 뒤 토막이 괄호로 시작하지 않는
    자리다(이름 뒤 줄의 "(갱신형)"은 이름이 이어진 것이다).
    """
    tokens, seps = name_tokens(text)
    names = list(names)
    keys = {wait_name_key(n): n for n in names if wait_name_key(n)}
    loose: dict[str, str | None] = {}
    if atoms:
        for n in dict.fromkeys(names):
            a = wait_name_atoms(n)
            if a:
                loose[a] = n if a not in loose else None      # 같은 열쇠의 이름이 둘 이상이면 쓰지 않는다
    out: dict[str, list[tuple[int, int]]] = {}

    def closed(s: str) -> bool:
        return s.count("(") == s.count(")")

    for i in range(len(tokens)):
        if i and seps[i - 1] == "\n" and (tokens[i].startswith(("(", ")"))
                                          or not (tokens[i - 1].endswith(")") or closed(tokens[i - 1]))):
            continue
        joined = ""
        for j in range(i, min(len(tokens), i + most)):
            joined += ("" if j == i or seps[j - 1] == "\n" else seps[j - 1]) + tokens[j]
            if j + 1 < len(tokens) and seps[j] == "\n" and (tokens[j + 1].startswith(("(", ")")) or not closed(joined)):
                continue
            key = wait_name_key(joined)
            if key in keys:
                out.setdefault(keys[key], []).append((i, j + 1))
            elif atoms and closed(joined) and not _top_comma(joined) and loose.get(wait_name_atoms(joined)):
                out.setdefault(loose[wait_name_atoms(joined)], []).append((i, j + 1))
    return out


def wait_lines(rows: Iterable[WaitRow], names: Iterable[str]) -> dict[int, str]:
    """면책기간 표에서 names의 이름마다 "<이름> <N>일면책" 줄을 쪽별로 만든다(면책이 있는 날수만, 같은 줄은 한 번).

    두 단으로 실린 표를 쪽 글자로 풀면 왼쪽 단과 오른쪽 단의 줄이 섞이고 이름이 여러 줄로 갈려, 이름 바로 옆의 날수를 찾는
    기계 검사(reader_rows.wait_days_on_page)가 표를 읽지 못한다. 적재가 이 줄을 그 쪽 글자 뒤에 붙여 기계 검사에 준다.
    감액기간 칸과 50% 감액지급 칸에 감액이 있는 행(WaitRow.cut_period)은 "<이름> 감액기간 <N>년미만 50%감액지급" 줄도
    만든다(reader_rows.wait_cuts_on_pages가 감액의 숫자를 이 줄에서 대조한다).
    """
    names = list(dict.fromkeys(names))
    out: dict[int, list[str]] = {}
    for row in rows:
        cut = row.cut_period
        if not row.days and not cut:
            continue
        for name in wait_name_spans(row.names_text, names):
            for d in sorted(set(row.days or ())):
                line = f"{name} {d}일면책"     # 날수 바로 뒤에 다음 줄 첫 글자("전이암…")가 붙어 "전"으로 읽히지 않게 한다
                if d and line not in out.setdefault(row.page, []):
                    out[row.page].append(line)
            if cut:
                line = f"{name} {WAIT_CUT_WORD} {cut[0]}{cut[1]}미만 50%감액지급"
                if line not in out.setdefault(row.page, []):
                    out[row.page].append(line)
    return {p: "\n".join(lines) for p, lines in out.items() if lines}


WAIT_CUT_WORD = "감액기간"
