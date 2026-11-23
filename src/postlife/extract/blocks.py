"""생명보험사 상품요약서의 급부 표를 특약 단위 조각으로 자른다.

손해보험사 요약서(tables.py)는 "보장명 | 지급사유 | 지급금액" 표 하나가 쪽을 넘어 이어진다. 생명보험사 요약서는 대부분
꼴이 다르다. 급부 절이 "가. 주계약", "나. 선택특약" 같은 소절로 나뉘고, 특약마다 기준 줄("[기준 : 특약보험가입금액 1,000만원]")과
작은 표 하나, 그 아래 "㈜ 1. …" 풀이 문단이 따로 있다. 작은 표는 이렇게 생겼다(삼성생명).

- 주계약 표는 "급부명 | 지급사유 | 지급금액"이다. 급부명 칸이 세부보장 이름이다.
- 특약 표는 "특약명 | 지급사유 | 지급금액"이다. 특약명 칸은 세부보장 여러 행에 걸쳐 병합되어 있고, 세부보장 이름은
  지급사유 칸 첫머리의 "□ 이름" 줄이다. "□ 이름"만 적힌 행은 묶음 이름이고, 그 아래 행들은 그 이름을 물려받거나
  "- 하위 이름" 줄로 하위 보장을 적는다.
- 지급금액 칸 아래에 "1년이내 | 1년초과", "90일이내 | 1년이내 | 1년초과" 같은 하위 칸이 있다. 하위 칸끼리 옆으로,
  위아래 행끼리 병합되어 있기도 하다.
- 지급사유 칸 첫머리의 "[1종,2종]", 특약명 끝의 "[1,2,3종]"은 그 줄이나 특약이 걸리는 종이다(적용범위로 뗀다).
- 표가 쪽을 넘으면 다음 쪽 표는 머리행이 없고, 특약명 칸이 빠진 채 지급사유 칸부터 시작하기도 한다.

조각의 꼴은 tables.py와 같다(tables.Rider, tables.write_riders). 그래서 scripts/split_pieces.py와 reader_rows가 그대로 읽는다.
값(지급률, 감액, 면책)은 읽지 않는다. 조각과 이름의 뼈대만 낸다.

이 파일은 두 부분이다. 앞부분(pieces)은 PDF 없이 돌아간다. 쪽마다 읽은 "표 밖 글 줄"(Text)과 "표"(Table)의 차례를 받아
조각과 주석을 만든다. 뒷부분(read_events)만 pdfplumber로 표의 선과 글자를 읽는다. 회사마다 다른 것은 LifeLayout에 모았다.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from . import reader_rows as RR
from . import tables as T

FORMAT = T.FORMAT
UNLABELED = "하위 칸"         # 머리 없는 지급금액 하위 칸의 머리 앞말(LifeLayout.unlabeled의 기본값)


@dataclass(frozen=True)
class Part:
    """급부 절 안의 소절. "가. 주계약", "나. 선택특약"."""
    pattern: re.Pattern         # 소절 제목 줄
    label: str                  # 조각의 구분. 주계약은 "기본계약"이어야 뒤 단계가 담보구분을 주계약으로 적는다
    main: bool                  # 주계약 소절인가
    rider: str = ""             # 이 소절 표의 특약 이름(급부명 표처럼 특약명 칸이 없는 표). 비우면 하위 제목 줄이 정한다


@dataclass(frozen=True)
class LifeLayout:
    """회사마다 다른 생명보험사 요약서 급부 절의 꼴."""
    name: str
    section_start: re.Pattern               # 급부 절의 시작 줄
    section_end: re.Pattern                 # 급부 절 다음 절의 시작 줄
    section_title: str
    parts: tuple[Part, ...]
    sub_head: re.Pattern | None = None      # 소절 안 하위 제목 줄(특약 이름). group(1)이 이름이다. 예: "① 플러스사망보장플랜"
    rider_words: tuple[str, ...] = ("특약명",)      # 머리행의 이 말 칸은 특약 이름 칸이다
    cover_words: tuple[str, ...] = ("급부명",)      # 머리행의 이 말 칸은 세부보장 이름 칸이다
    reason_word: str = "지급사유"
    amount_word: str = "지급금액"           # 머리행에서 이 말이 든 칸("연간 한도별 지급금액 (…기준)"도 된다)
    cover_mark: re.Pattern = re.compile(r"^□\s*")           # 지급사유 칸에서 세부보장 이름을 여는 표시
    sub_mark: re.Pattern = re.compile(r"^[-–]\s*")          # 묶음 이름 아래 하위 보장 이름을 여는 표시
    base: re.Pattern = re.compile(r"^[\[(（][^\[\]()（）]*(?:기준|가입금액)[^\[\]()（）]*[\])）]$")   # 표 위 기준 줄
    note_start: re.Pattern = re.compile(r"^(?:㈜|주\s*\d*\s*\)|※)")        # 표 아래 풀이 문단의 첫 줄
    footer: re.Pattern = re.compile(r"^-\s*\d+\s*-$")      # 쪽 번호 줄
    top_margin: float = 0.0                 # 이보다 위에 찍힌 표 밖 글자는 읽지 않는다(병합된 칸의 글자가 쪽 위로 넘어가 가려진 것)
    unlabeled: str = UNLABELED               # 머리 없이 세로선으로만 갈린 지급금액 하위 칸의 머리("하위 칸 1", "하위 칸 2")


# 삼성생명: "2. 보험금 지급사유" ~ "3. 일반적인 보험금 지급제한사항". "가. 주계약"(급부명 표), "나. 플러스보장플랜"(주계약의
# 플랜. "① 플러스사망보장플랜"마다 급부명 표), "나. 선택특약"(특약명 표).
SAMSUNGLIFE = LifeLayout(
    "samsunglife",
    section_start=re.compile(r"^\d+\.\s*보험금\s*지급사유\s*$"),
    section_end=re.compile(r"^\d+\.\s*일반적인\s*보험금\s*지급제한"),
    section_title="2. 보험금 지급사유",
    parts=(
        Part(re.compile(r"^[가-하]\.\s*주계약\s*$"), "기본계약", True, "주계약"),
        Part(re.compile(r"^[가-하]\.\s*플러스보장플랜\s*$"), "기본계약", True),
        Part(re.compile(r"^[가-하]\.\s*선택특약\s*$"), "선택특약", False),
    ),
    sub_head=re.compile(r"^[①-⑳]\s*(\S.*?플랜)\s*$"),
    top_margin=50.0,
)

LAYOUTS = {layout.name: layout for layout in (SAMSUNGLIFE,)}

# 종 표시. "[1종,2종]", "[1,2종]", "[3종]", "[1, 2, 3종]"
_SCOPE_BODY = r"(?:\d+\s*종?\s*[,·/~]\s*)*\d+\s*종"
_SCOPE_LINE = re.compile(rf"^\[\s*({_SCOPE_BODY})\s*\]$")
_SCOPE_HEAD = re.compile(rf"^\[\s*({_SCOPE_BODY})\s*\]\s*")
_SCOPE_TAIL = re.compile(rf"\s*\[\s*({_SCOPE_BODY})\s*\]\s*$")
# 하위 보장 이름으로 보지 않는 말(지급사유 문장의 말). reader_rows.name_problem의 표시에 문장 끝말을 더했다
_SENTENCE = re.compile(r"지급|경우|되고|되었|확정시|로써|한하여|피보험자|하였|받은|받는|하는|된\s|때")
_QUOTE_START = re.compile(r"^[\"“”「『'‘]")
_ENDINGS = re.compile(r"(?:보험금|급여금|지원금)")
_SPACES = re.compile(r"\s+")


def scope_text(found: str) -> str:
    """종 표시의 글자에서 빈칸을 뗀다. "1종, 2종" → "1종,2종"."""
    return _SPACES.sub("", found)


def clean_name(text: str) -> tuple[str, str]:
    """이름 칸의 글자를 (이름, 적용범위)로 다듬는다.

    줄을 잇고(tables.join_name), 끝의 종 표시("[1,2,3종]")를 떼어 적용범위로 두고, 빈칸을 하나로 줄이고,
    괄호가 하나 빠진 것을 맞춘다(tables.mend_brackets).
    """
    name = T.join_name(text)
    only = ""
    m = _SCOPE_TAIL.search(name)
    if m:
        name, only = name[:m.start()], scope_text(m.group(1))
    name = _SPACES.sub(" ", name).strip()
    return T.mend_brackets(name), only


# ---------------------------------------------------------------------------
# 쪽에서 읽은 것 → 조각 (PDF 없이 돌아가는 부분)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Text:
    """표 밖에 적힌 글 한 줄."""
    page: int
    text: str


@dataclass(frozen=True)
class Row:
    """작은 표의 한 행. 지급사유 칸 하나가 한 행이다.

    name은 이름 칸(특약명 칸이나 급부명 칸)의 글이다. None은 위 행과 같은 칸(병합)이거나 이름 칸이 없는 표다.
    reason은 지급사유 칸의 글(줄마다 "\\n")이다. amounts는 지급금액 하위 칸별 (머리, 글)이다. 하위 칸이 없으면 머리는 "".
    옆으로 병합된 하위 칸은 머리를 ", "로 이어 한 번만 적는다.
    """
    page: int
    name: str | None
    reason: str
    amounts: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Table:
    """작은 표 하나. mode는 이름 칸의 뜻("특약" 또는 "급부")이다."""
    page: int
    rows: tuple[Row, ...]
    mode: str = "특약"
    headless: bool = False      # 머리행 없이 앞 쪽 표에서 이어진 표
    head: str = ""              # 지급금액 머리 칸에 "지급금액" 말고 더 적힌 글. 예: "연간 한도별 지급금액 (5,000만원 기준)"


@dataclass
class Result:
    riders: list[T.Rider]
    notes: list[dict[str, Any]]
    issues: list[dict[str, Any]] = field(default_factory=list)     # 이름 깨짐 점검(check_names)
    events: list[dict[str, Any]] = field(default_factory=list)     # 조각 만들기에서 따로 본 행(쪽, 이유)


_SPACED_NEXT = re.compile(r"^[\[\-–:※□·]")
_SPACED_PREV = re.compile(r"(?:\]|원|%)$")


def join_amount(text: str) -> str:
    """지급금액 칸의 줄을 한 줄로 잇는다.

    좁은 칸이라 낱말 가운데서 줄이 바뀐다("연간 1회 한" / "도)"). 그래서 붙여 쓰되, 다음 줄이 종 표시나 항목 표시
    ("[3종]", "- …", ": 7만원")로 시작하거나 앞 줄이 "]", "원", "%"로 끝나면 빈칸 하나를 둔다
    ("[1종,2종] 1,000만원 [3종] 500만원", "1종 5만원 2종 10만원"). "500만" / "원"처럼 단위가 갈린 것은 붙인다.
    """
    out = ""
    for line in (l.strip() for l in (text or "").split("\n")):
        if not line:
            continue
        if out and (_SPACED_NEXT.match(line) or _SPACED_PREV.search(out)):
            out += " "
        out += line
    return _SPACES.sub(" ", out).strip()


def amount_text(amounts: Sequence[tuple[str, str]]) -> str:
    """하위 칸별 지급금액을 한 글로 잇는다. 머리가 있으면 "머리: 글" 줄로 적고, 글이 빈 칸은 뺀다."""
    out = []
    for head, text in amounts:
        text = join_amount(text)
        if not text:
            continue
        out.append(f"{head}: {text}" if head else text)
    return "\n".join(out)


# 세부보장 이름이 줄 끝에서 갈린 꼴. "…보장보험" / "금", "…(종합병원이상)보" / "험금[…]", "…치료보장" / "보험금"
_WRAP_ALONE = re.compile(r"^(?:보험금|급여금|지원금|험금|금)(?:\[[^\[\]]*\]|\([^()]*\))*$")
_WRAP_PAIRS = ((re.compile(r"보$"), re.compile(r"^험금")), (re.compile(r"(?:보험|급여|지원)$"), re.compile(r"^금")))


_TAG_LINE = re.compile(r"^\((?!단\s*[,，])[^()]*\)")      # 이름 뒤에 붙는 괄호 토막 줄. "(단, …)"은 지급사유다
_OPEN_PART = re.compile(r"_[^_()\[\]]*$")                   # "…보험금_주요순"처럼 "_" 뒤 토막이 괄호로 닫히지 않음


def _wrapped(name: str, line: str) -> bool:
    """다음 줄이 앞 줄 세부보장 이름의 뒷토막인가.

    - "금", "보험금", "험금[…]"처럼 이름 끝말이 갈린 줄
    - "(수술)보험금(…)", "(연간복합치료횟수1회이상)"처럼 괄호로 시작하는 짧은 토막(문장의 말이 없을 때)
    - 앞 줄이 "…보험금_주요순"처럼 "_" 뒤 토막이 끝나지 않은 채 끝났을 때 이어지는 줄(문장의 말이 없을 때)
    """
    if _WRAP_ALONE.match(line):
        return True
    if any(a.search(name) and b.match(line) for a, b in _WRAP_PAIRS):
        return True
    if _SENTENCE.search(line) or len(line) > 40:
        return False
    if _TAG_LINE.match(line) and T._unclosed(line) == 0:
        return True
    return bool(_OPEN_PART.search(name))


def _name_lines(lines: list[str]) -> tuple[str, list[str]]:
    """첫 줄부터 이름을 읽는다. 괄호가 닫히지 않은 동안, 또는 다음 줄이 이름의 뒷토막("금", "험금[…]")이면
    다음 줄(두 줄까지)을 잇는다. (이름 글, 나머지 줄)."""
    taken = [lines[0]]
    i = 1
    while i < len(lines) and i <= 2:
        joined = T.join_name("\n".join(taken))
        if T._unclosed(joined) <= 0 and not _wrapped(joined, lines[i]):
            break
        taken.append(lines[i])
        i += 1
    return "\n".join(taken), lines[i:]


@dataclass
class _Cover:
    name: str
    reason: list[str]           # 문단들(join_text를 거친 글)
    amount: str
    page: int
    only: str = ""


def _paragraph(lines: Sequence[str]) -> str:
    return T.join_text("\n".join(lines))


@dataclass
class _Rider:
    title: str
    only: str
    label: str
    main: bool
    covers: list[_Cover] = field(default_factory=list)
    last_page: int = 0


class _Builder:
    """쪽 순서로 글 줄과 표를 받아 조각을 만든다."""

    def __init__(self, layout: LifeLayout):
        self.layout = layout
        self.riders: list[_Rider] = []
        self.current: _Rider | None = None
        self.part: Part | None = None
        self.sub = ""               # 하위 제목 줄의 특약 이름
        self.base: list[tuple[int, str]] = []      # 다음 표의 특약에 걸 기준 줄
        self.group = ""             # 묶음 이름("□ 이름"만 적힌 행)
        self.pure = False           # 마지막 "□ 이름"이 묶음 행이었는가(하위 보장 이름을 읽는다)
        self.after_table = False    # 마지막에 본 것이 표인가(그 아래 글이 풀이 문단이다)
        self.table_riders: list[_Rider] = []      # 마지막 표에서 다룬 특약들
        self.note: list[str] | None = None
        self.note_page = 0
        self._pending: list[tuple[_Rider, int, str]] = []     # (특약, 쪽, 글). 특약 이름이 다 정해진 뒤 머리를 단다
        self.events: list[dict[str, Any]] = []
        self.held: tuple[str, str, Row, str] | None = None     # 지급금액이 빈 묶음 행(이름, 지급사유, 행, 적용범위)
        self.held_used = False
        self.ended = False          # 급부 절 다음 절의 제목 줄을 보았다. 그 뒤는 읽지 않는다

    # -- 표 밖 글 --------------------------------------------------------
    def text(self, line: Text) -> None:
        t = line.text.strip()
        if self.ended or not t or self.layout.footer.match(t):
            return
        if self.layout.section_end.match(t):
            self._close_note()
            self.ended = True
            return
        part = next((p for p in self.layout.parts if p.pattern.match(t)), None)
        if part is not None:
            self._close_note()
            self.part, self.sub, self.base = part, "", []
            self.after_table = False
            return
        if self.layout.sub_head is not None:
            m = self.layout.sub_head.match(t)
            if m and self.part is not None:
                self._close_note()
                self.sub, self.base = _SPACES.sub(" ", m.group(1)).strip(), []
                self.after_table = False
                return
        if self.layout.base.match(t):
            self._close_note()
            self.base.append((line.page, t))
            self.after_table = False
            return
        if self.note is not None:
            self.note.append(t)
            return
        if self.after_table and self.layout.note_start.match(t):
            self.note, self.note_page = [t], line.page
            return

    def _close_note(self) -> None:
        if self.note:
            text = T.join_text("\n".join(self.note))
            for r in self.table_riders:
                self._pending.append((r, self.note_page, text))
        self.note = None

    # -- 표 ----------------------------------------------------------------
    def table(self, table: Table) -> None:
        self._close_note()
        if self.ended:
            return
        if self.part is None:
            self.events.append({"쪽": table.page, "이유": "소절 제목(주계약, 선택특약) 앞의 표라 읽지 않음"})
            return
        self.table_riders = []
        if table.head and not table.headless:
            self.base.append((table.page, table.head))
        for i, row in enumerate(table.rows):
            if table.mode == "급부":
                self._cover_row(table, i, row)
            else:
                self._rider_row(table, i, row)
        self.after_table = True

    def _start(self, title: str, only: str, page: int) -> _Rider:
        self._flush_group()
        part = self.part
        assert part is not None
        r = _Rider(title, only, part.label, part.main, last_page=page)
        self.riders.append(r)
        for p, text in self.base:
            self._pending.append((r, p, text))
        self.base = []
        self.current = r
        self.group, self.pure = "", False
        return r

    def _touch(self, r: _Rider, page: int) -> None:
        r.last_page = max(r.last_page, page)
        if r not in self.table_riders:
            self.table_riders.append(r)

    def _add(self, r: _Rider, name: str, reason: list[str], row: Row, only: str = "") -> None:
        paragraphs = [_paragraph(reason)] if reason else []
        if self.held is not None:
            paragraphs = [self.held[1]] + paragraphs        # 묶음 행의 지급사유(그 아래 세부보장 모두에 걸리는 조건)
            self.held_used = True
        r.covers.append(_Cover(name, [p for p in paragraphs if p], amount_text(row.amounts), row.page, only))
        self._touch(r, row.page)

    def _flush_group(self) -> None:
        """지급사유가 있는데 지급금액이 빈 묶음 행 가운데, 이름을 물려받는 행이 뒤따르지 않은 것은 세부보장 하나로 남긴다."""
        held, self.held = self.held, None
        if held is not None and not self.held_used and self.current is not None:
            name, reason, row, only = held[0], held[1], held[2], held[3]
            self.current.covers.append(_Cover(name, [reason], amount_text(row.amounts), row.page, only))
            self._touch(self.current, row.page)
        self.held_used = False

    def _continuation(self, table: Table, i: int, row: Row, lines: list[str]) -> bool:
        """머리행 없이 이어진 표의 첫 행이 앞 쪽 마지막 행의 잘린 뒷부분인가. 이름 칸과 지급금액이 비었고, 지급사유가
        세부보장 이름이나 종 표시, 대상 표시("[")로 시작하지 않는다."""
        if not (table.headless and i == 0 and self.current is not None and self.current.covers):
            return False
        if (row.name or "").strip() or amount_text(row.amounts):
            return False
        first = lines[0] if lines else ""
        return bool(first) and not (self.layout.cover_mark.match(first) or self.layout.sub_mark.match(first)
                                    or first.startswith("["))

    def _scope(self, lines: list[str]) -> tuple[str, list[str]]:
        """지급사유 첫머리의 종 표시 줄("[1종,2종]")을 뗀다."""
        if lines:
            m = _SCOPE_LINE.match(lines[0].strip())
            if m:
                return scope_text(m.group(1)), lines[1:]
        return "", lines

    def _rider_for(self, table: Table, i: int, row: Row) -> _Rider:
        """이 행의 특약. 이름 칸에 새 이름이 적혀 있으면 새 특약을 연다.

        - 머리행이 있는 표는 새 특약의 표다. 첫 행의 이름 칸이 비었으면(병합된 이름 칸의 글자가 다음 쪽에 찍힌 경우)
          이름 없는 특약을 열고, 이어진 표에서 이름이 나오면 그 이름을 단다.
        - 이름이 묶는 중인 특약과 같으면(이어진 표나 머리행을 되풀이한 표) 그 특약이 이어진다.
        """
        name = (row.name or "").strip()
        title, only = clean_name(row.name or "") if name else ("", "")
        current = self.current
        same = current is not None and bool(title) and T.name_key(title) == T.name_key(current.title)
        if i == 0 and not table.headless and not same:
            return self._start(title, only, row.page)
        if not title or same:
            return current if current is not None else self._start("", "", row.page)
        assert current is not None
        if not current.title:
            current.title, current.only = title, only       # 이름 칸이 뒤에서야 나온 특약
            return current
        if table.headless:
            self.events.append({"쪽": row.page, "이유": f"이어진 표에서 특약 이름이 바뀜: {title}"})
        return self._start(title, only, row.page)

    def _rider_row(self, table: Table, i: int, row: Row) -> None:
        lines = [l.strip() for l in row.reason.split("\n") if l.strip()]
        if self._continuation(table, i, row, lines):
            r = self.current
            assert r is not None
            r.covers[-1].reason.append(_paragraph(lines))
            self._touch(r, row.page)
            self.events.append({"쪽": row.page, "이유": "앞 쪽에서 잘린 행의 뒷부분을 앞 세부보장에 이음"})
            return
        r = self._rider_for(table, i, row)
        if not lines:
            if amount_text(row.amounts) and r.covers:
                last = r.covers[-1]
                last.amount = "\n".join(x for x in (last.amount, amount_text(row.amounts)) if x)
                self._touch(r, row.page)
                self.events.append({"쪽": row.page, "이유": "지급사유 없이 지급금액만 있는 행을 앞 세부보장에 이음"})
            return
        only, lines = self._scope(lines)
        if lines and self.layout.cover_mark.match(lines[0]):
            self._flush_group()
            head, rest = _name_lines([self.layout.cover_mark.sub("", lines[0])] + lines[1:])
            m = _SCOPE_HEAD.match(head.strip())
            if m:
                only = only or scope_text(m.group(1))
                head = head.strip()[m.end():]
            cover, _ = clean_name(head)
            if not rest:
                self.group, self.pure = cover, True       # "□ 이름"만 적힌 묶음 행
                if amount_text(row.amounts):
                    self.events.append({"쪽": row.page, "이유": f"묶음 행에 지급금액이 있음(세부보장으로 보지 않음): {cover}"})
                return
            if not amount_text(row.amounts):
                # 지급금액이 빈 "□ 이름 + 지급사유" 행. 아래 행들이 이름을 물려받으면 이 지급사유는 그 행들 모두의 조건이다
                self.group, self.pure = cover, True
                self.held, self.held_used = (cover, _paragraph(rest), row, only), False
                return
            self.group, self.pure = cover, False
            self._add(r, cover, rest, row, only)
            return
        if self.pure and lines and self.layout.sub_mark.match(lines[0]):
            head, rest = _name_lines([self.layout.sub_mark.sub("", lines[0])] + lines[1:])
            sub, _ = clean_name(head)
            if sub and not _SENTENCE.search(sub) and not _QUOTE_START.match(sub) and len(sub) <= 60:
                self._add(r, f"{self.group} {sub}", rest, row, only)
                return
        self._add(r, self.group, lines, row, only)

    def _cover_row(self, table: Table, i: int, row: Row) -> None:
        part = self.part
        assert part is not None
        title = self.sub or part.rider
        lines = [l.strip() for l in row.reason.split("\n") if l.strip()]
        if self._continuation(table, i, row, lines):
            r = self.current
            assert r is not None
            r.covers[-1].reason.append(_paragraph(lines))
            self._touch(r, row.page)
            self.events.append({"쪽": row.page, "이유": "앞 쪽에서 잘린 행의 뒷부분을 앞 세부보장에 이음"})
            return
        if self.current is None or self.current.title != title or self.current.label != part.label:
            self._start(title, "", row.page)
        r = self.current
        assert r is not None
        if not lines and not amount_text(row.amounts):
            return
        only, lines = self._scope(lines)
        if (row.name or "").strip():
            name, name_only = clean_name(row.name or "")
            self.group = name
            only = only or name_only
        self._add(r, self.group, lines, row, only)

    # -- 마무리 ------------------------------------------------------------
    def finish(self) -> Result:
        self._close_note()
        self._flush_group()
        riders: list[T.Rider] = []
        kept: dict[int, T.Rider] = {}
        for r in self.riders:
            if not r.covers:
                continue
            covers = tuple(T.Cover(c.name or r.title, "\n".join(c.reason), c.amount, c.page, c.only)
                           for c in r.covers)
            if not r.title:
                self.events.append({"쪽": covers[0].page, "이유": f"특약 이름 칸을 읽지 못해 첫 세부보장 이름을 제목으로 씀: {covers[0].name}"})
            title = r.title or covers[0].name
            covers = tuple(c if c.name else T.Cover(title, c.reason, c.amount, c.page, c.only) for c in covers)
            rider = T.Rider(title, covers, covers[0].page, max(r.last_page, covers[-1].page), r.label, r.only,
                            "", r.main)
            riders.append(rider)
            kept[id(r)] = rider
        notes = [{"쪽": page, "형": "", "특약머리": kept[id(r)].title, "글": text}
                 for r, page, text in self._pending if id(r) in kept and text]
        return Result(riders, notes, check_names(riders), self.events)


def pieces(items: Iterable[Text | Table], layout: LifeLayout = SAMSUNGLIFE) -> Result:
    """쪽 순서로 읽은 표 밖 글 줄과 표에서 조각과 주석을 만든다."""
    b = _Builder(layout)
    for item in items:
        if isinstance(item, Table):
            b.table(item)
        else:
            b.text(item)
    return b.finish()


# ---------------------------------------------------------------------------
# 이름 점검
# ---------------------------------------------------------------------------

def name_faults(name: str) -> list[str]:
    """이름 하나의 깨짐. 괄호가 안 닫힘, 두 이름이 붙음, 이름에 문장이 섞임."""
    out = []
    if T._unclosed(name) != 0 or T._unopened(name):
        out.append("괄호가 안 닫힘")
    if name.count("□") or len(_ENDINGS.findall(re.sub(r"\[[^\[\]]*\]|\([^()]*\)", "", name))) >= 2:
        out.append("두 이름이 붙음")
    if re.search(r"지급|경우|되고|되었|확정시|로써|한하여|피보험자", name):
        out.append("이름에 문장이 섞임")
    return out


def check_names(riders: Sequence[T.Rider]) -> list[dict[str, Any]]:
    """특약 이름과 세부보장 이름의 깨짐을 모은다. 세부보장 이름은 reader_rows.name_problem(뒤 단계가 행을 보류하는 검사)도 본다.

    묶음 이름과 하위 이름을 빈칸 하나로 이은 세부보장 이름("통합가나진단보험금 가나 진단보험금")은 끝말("보험금")이 둘인 것이
    정상이다. 그래서 빈칸이 든 이름은 끝말 수로는 붙은 이름으로 세지 않는다("□"가 들어 있으면 센다).
    """
    out: list[dict[str, Any]] = []
    for i, r in enumerate(riders, 1):
        for fault in name_faults(r.title):
            out.append({"번호": f"R{i:03d}", "쪽": r.first_page, "이름": r.title, "문제": f"특약 이름: {fault}"})
        for j, c in enumerate(r.covers, 1):
            faults = name_faults(c.name)
            if " " in c.name and "두 이름이 붙음" in faults and not c.name.count("□"):
                faults.remove("두 이름이 붙음")
            problem = RR.name_problem(RR.CoverView(RR.number(i, j), c.name, c.reason, c.amount, c.page, c.only))
            if problem:
                faults.append(problem)
            for fault in faults:
                out.append({"번호": RR.number(i, j), "쪽": c.page, "이름": c.name, "문제": fault})
    return out


def amount_kind(text: str) -> str:
    """지급금액 글의 어림 꼴. 가입금액 비율(%, 가입금액, 지급률), 금액(만원, 원), 그 밖."""
    flat = _SPACES.sub("", text)
    if re.search(r"%|가입금액|지급률|약정보험료", flat):
        return "비율"
    if re.search(r"\d\s*(?:만|원|万)", flat):
        return "금액"
    return "그 밖"


def stats(result: Result) -> dict[str, Any]:
    """조각 수, 세부보장 수, 주계약 조각, 이름이 같은 세부보장 묶음 수, 지급금액 꼴의 분포, 이름 깨짐 수."""
    riders = result.riders
    same_groups = same_lines = 0
    for r in riders:
        counts = Counter(T.squash(c.name) for c in r.covers)
        dup = [n for n in counts.values() if n > 1]
        same_groups += len(dup)
        same_lines += sum(dup)
    kinds = Counter(amount_kind(c.amount) for r in riders for c in r.covers)
    faults = Counter(i["문제"].split(":")[0] if i["문제"].startswith("보류") else i["문제"] for i in result.issues)
    return {
        "조각": len(riders),
        "세부보장": sum(len(r.covers) for r in riders),
        "주계약 조각": [r.title for r in riders if r.main],
        "주계약 세부보장": sum(len(r.covers) for r in riders if r.main),
        "종 표시가 붙은 조각": sum(1 for r in riders if r.only),
        "종 표시가 붙은 세부보장": sum(1 for r in riders for c in r.covers if c.only),
        "이름같은 묶음": same_groups,
        "이름같은 줄": same_lines,
        "머리 없는 하위 칸 세부보장": sum(1 for r in riders for c in r.covers if f"{UNLABELED} 1:" in c.amount),
        "지급금액 꼴": dict(sorted(kinds.items())),
        "이름 깨짐": dict(sorted(faults.items())),
        "주석": len(result.notes),
        "기준 줄": dict(sorted(Counter(_SPACES.sub("", n["글"]) for n in result.notes
                                    if n["글"][:1] in "[(（" and "기준" in n["글"]).items())),
        "같은 제목 조각": sorted(t for t, n in Counter(r.title for r in riders).items() if n > 1),
    }


# ---------------------------------------------------------------------------
# PDF에서 읽기 (pdfplumber를 쓰는 부분)
# ---------------------------------------------------------------------------

_SNAP = T._SNAP
_LABEL = re.compile(r"이내|초과|경과|기간\s*중|확정\s*시|이후|이전|미만|이상")
_MONEY = re.compile(r"\d[\d,.]*\s*(?:만|원|万|%)")


@dataclass(frozen=True)
class _Columns:
    """작은 표의 칸 자리."""
    left: float                 # 이름 칸 왼쪽(표 왼쪽)
    reason: float               # 지급사유 칸 왼쪽
    subs: tuple[float, ...]     # 지급금액 하위 칸의 왼쪽들과 표 오른쪽
    labels: tuple[str, ...]     # 하위 칸 머리. 하위 칸이 하나면 ("",)
    mode: str                   # "특약" 또는 "급부"
    head: str = ""              # 지급금액 머리 칸의 덧글

    @property
    def right(self) -> float:
        return self.subs[-1]


def _chars_in(chars: list[dict], x0: float, x1: float, y0: float, y1: float) -> list[dict]:
    return [c for c in chars if x0 <= c["at"][0] < x1 and y0 <= c["at"][1] < y1]


def _lines_in(chars: list[dict], x0: float, x1: float, y0: float, y1: float) -> list[str]:
    return [l.text for l in T._text_lines(_chars_in(chars, x0, x1, y0, y1))]


def _cell_words(chars: list[dict], row: Any) -> list[tuple[Sequence[float], str]]:
    return [(cell, T.squash("".join(c["text"] for c in T._within(chars, cell)))) for cell in row.cells if cell is not None]


def _label(lines: Sequence[str]) -> str:
    """하위 칸 머리 글. 첫 줄 뒤는 빈칸 하나, 그 뒤 줄은 붙여 쓴다(좁은 칸이라 낱말 가운데서 줄이 바뀐다).
    "1년이내" / "최초 암진단확" / "정시" → "1년이내 최초 암진단확정시"."""
    lines = [l.strip() for l in lines if l.strip()]
    return (lines[0] + (" " + "".join(lines[1:]) if lines[1:] else "")) if lines else ""


def _header(t: Any, chars: list[dict], v: list[dict], layout: LifeLayout,
            part: Part | None) -> tuple[_Columns, float, float] | None:
    """머리행이 있는 표이면 (칸 자리, 본문 시작 높이, 지급금액 본문 시작 높이)."""
    rows = list(t.rows)
    for k, row in enumerate(rows[:2]):
        words = _cell_words(chars, row)
        reason = next((c for c, w in words if w == layout.reason_word), None)
        amount = next(((c, w) for c, w in words if layout.amount_word in w), None)
        if reason is None or amount is None or not reason[0] < amount[0][0]:
            continue
        mode = ""
        for c, w in words:
            if w in layout.rider_words:
                mode = "특약"
            elif w in layout.cover_words:
                mode = "급부"
        if not mode:
            mode = "급부" if part is not None and part.main and part.rider else "특약"
        acell, aword = amount
        head = ""
        if aword != layout.amount_word:
            head = " ".join(_lines_in(chars, acell[0], acell[2], acell[1], acell[3]))
        body_top = reason[3]
        # 지급금액 머리 아래의 하위 칸 머리 행들(1년이내 | 1년초과)
        subs_rows: list[list[Sequence[float]]] = []
        for row2 in rows[k + 1:k + 4]:
            cells = [c for c in t.cells if abs(c[1] - row2.bbox[1]) <= _SNAP and c[0] >= acell[0] - _SNAP]
            texts = [" ".join(_lines_in(chars, c[0], c[2], c[1], c[3])) for c in cells]
            if not cells or not all(x and _LABEL.search(x) and not _MONEY.search(x) for x in texts):
                break
            subs_rows.append(cells)
        if subs_rows:
            xs = sorted({round(c[0], 1) for cells in subs_rows for c in cells})
            subs = tuple(xs) + (t.bbox[2],)
            labels = []
            for a, b in zip(subs, subs[1:]):
                parts = [_label(_lines_in(chars, c[0], c[2], c[1], c[3])) for cells in subs_rows for c in cells
                         if abs(c[0] - a) <= _SNAP or (c[0] < a - _SNAP and c[2] > b - _SNAP)]
                labels.append(_SPACES.sub(" ", " ".join(parts)).strip())
            amount_top = max(c[3] for c in subs_rows[-1])
        else:
            amount_top = acell[3]
            # 하위 칸 머리 없이 세로선만 있는 표. 머리 대신 칸 차례를 적는다
            inner = sorted({round(e["x0"], 1) for e in v if acell[0] + 2 * _SNAP < e["x0"] < t.bbox[2] - 2 * _SNAP
                            and e["top"] <= amount_top + 2 * _SNAP and e["bottom"] > amount_top + 5})
            subs = (acell[0], *inner, t.bbox[2])
            labels = [""] if not inner else [f"{layout.unlabeled} {n}" for n in range(1, len(subs))]
        return _Columns(t.bbox[0], reason[0], subs, tuple(labels), mode, head), body_top, amount_top
    return None


def _continued(t: Any, v: list[dict], prev: _Columns | None) -> _Columns | None:
    """머리행 없이 앞 표에서 이어진 표이면 앞 표의 칸 자리. 표 오른쪽이 같고, 왼쪽이 앞 표의 왼쪽이나 지급사유 칸
    왼쪽이고, 지급금액 칸 왼쪽 자리에 세로선이 있어야 한다."""
    if prev is None or abs(t.bbox[2] - prev.right) > 3:
        return None
    if abs(t.bbox[0] - prev.left) > 3 and abs(t.bbox[0] - prev.reason) > 3:
        return None
    if not any(abs(e["x0"] - prev.subs[0]) <= _SNAP and e["top"] < t.bbox[3] and e["bottom"] > t.bbox[1] for e in v):
        return None
    return prev


def _spans(h: list[dict], xa: float, xb: float, top: float, bottom: float) -> list[tuple[float, float]]:
    """칸 하나(xa~xb)의 위아래 경계로 나눈 구간들. 칸 너비를 다 가로지르는 가로선만 경계로 본다."""
    ys = [top, bottom] + [e["top"] for e in h if e["x0"] <= xa + _SNAP and e["x1"] >= xb - _SNAP
                          and top - _SNAP <= e["top"] <= bottom + _SNAP]
    cuts: list[float] = []
    for y in sorted(ys):
        if not cuts or y - cuts[-1] > _SNAP:
            cuts.append(y)
    return [(a, b) for a, b in zip(cuts, cuts[1:]) if b - a > 2]


def _has_v(v: list[dict], x: float, y: float) -> bool:
    return any(abs(e["x0"] - x) <= _SNAP and e["top"] - _SNAP <= y <= e["bottom"] + _SNAP for e in v)


def _rows(t: Any, chars: list[dict], h: list[dict], v: list[dict], cols: _Columns, body_top: float,
          amount_top: float, page: int) -> list[Row]:
    top, bottom = t.bbox[1], t.bbox[3]
    has_name = abs(t.bbox[0] - cols.left) <= 3
    bands = [b for b in _spans(h, cols.reason, cols.subs[0], top, bottom) if b[0] >= body_top - _SNAP]
    if has_name:
        names = [b for b in _spans(h, cols.left, cols.reason, top, bottom) if b[1] > body_top + _SNAP]
        names = [(max(a, body_top), b) for a, b in names]
    else:
        names = [(top, bottom)]
    subs = [[b for b in _spans(h, a, z, top, bottom) if b[0] >= amount_top - _SNAP]
            for a, z in zip(cols.subs, cols.subs[1:])]
    out = []
    last_name: tuple[float, float] | None = None
    for band in bands:
        mid = (band[0] + band[1]) / 2
        reason = "\n".join(_lines_in(chars, cols.reason, cols.subs[0], band[0], band[1]))
        name_band = next((b for b in names if b[0] - _SNAP <= mid <= b[1] + _SNAP), None)
        name: str | None = None
        if name_band is not None and name_band != last_name:
            name = "\n".join(_lines_in(chars, cols.left, cols.reason, name_band[0], name_band[1]))
            last_name = name_band
        amounts: list[tuple[str, str]] = []
        k = 0
        while k < len(subs):
            texts = []
            end = k + 1
            for cell in subs[k]:
                cmid = (cell[0] + cell[1]) / 2
                if not (band[0] <= cmid < band[1] or cell[0] <= mid < cell[1]):
                    continue
                if k > 0 and not _has_v(v, cols.subs[k], cmid):
                    continue            # 왼쪽 하위 칸과 옆으로 병합된 칸. 왼쪽에서 읽었다
                stop = k + 1
                while stop < len(subs) and not _has_v(v, cols.subs[stop], cmid):
                    stop += 1           # 오른쪽 하위 칸과 옆으로 병합된 칸
                end = max(end, stop)
                texts.append("\n".join(_lines_in(chars, cols.subs[k], cols.subs[stop], cell[0], cell[1])))
            if texts:
                amounts.append((", ".join(x for x in cols.labels[k:end] if x), "\n".join(texts)))
            k = end
        out.append(Row(page, name, reason, tuple(amounts)))
    return out


def page_items(page: Any, number: int, layout: LifeLayout, state: dict[str, Any],
               misses: list[dict[str, Any]]) -> list[Text | Table]:
    """한 쪽의 표 밖 글 줄과 표를 위에서부터 차례로 돌려준다. state는 쪽을 넘어 이어지는 것(앞 표의 칸 자리, 소절)."""
    h, v = T._border_edges(page)
    chars = T._numbered(page.chars)
    found = sorted(T._find(page, h, v), key=lambda t: (t.bbox[1], t.bbox[0]))
    placed: list[tuple[float, int, Text | Table]] = []
    regions: list[tuple[float, float, float, float]] = []
    for t in found:
        got = _header(t, chars, v, layout, state.get("part"))
        headless = got is None
        if got is None:
            cols = _continued(t, v, state.get("cols"))
            if cols is None:
                if _chars_in(chars, *t.bbox[0::2], *t.bbox[1::2]):
                    misses.append({"쪽": number, "이유": f"머리행이 없고 앞 급부 표와 칸 자리가 다른 표(위쪽 {t.bbox[1]:.0f}pt)"})
                continue
            body_top = amount_top = t.bbox[1]
        else:
            cols, body_top, amount_top = got
        state["cols"] = cols
        mine = _chars_in(T._numbered(page.chars, t.bbox), min(cols.left, t.bbox[0]), t.bbox[2] + _SNAP,
                         t.bbox[1], t.bbox[3])
        rows = _rows(t, mine, h, v, cols, body_top, amount_top, number)
        placed.append((t.bbox[1], 1, Table(number, tuple(rows), cols.mode, headless, "" if headless else cols.head)))
        regions.append((min(cols.left, t.bbox[0]) - _SNAP, t.bbox[1] - _SNAP, t.bbox[2] + _SNAP, t.bbox[3] + _SNAP))
    loose = [c for c in chars if not any(r[0] <= c["at"][0] < r[2] and r[1] <= c["at"][1] < r[3] for r in regions)]
    for line in T._text_lines(loose):
        if line.top < layout.top_margin:
            continue
        placed.append((line.top, 0, Text(number, line.text.strip())))
        part = next((p for p in layout.parts if p.pattern.match(line.text.strip())), None)
        if part is not None:
            state["part"] = part
    placed.sort(key=lambda x: (x[0], x[1]))
    # state["part"]는 머리행에 이름 칸의 말(특약명, 급부명)이 없는 표의 이름 칸 뜻을 정할 때만 쓴다. 표를 먼저 읽으므로
    # 이 쪽에서 본 소절 제목은 다음 쪽 표부터 쓰인다
    return [item for _, _, item in placed]


def read_events(source: Path | str | bytes, first_page: int, last_page: int, layout: LifeLayout = SAMSUNGLIFE,
                misses: list[dict[str, Any]] | None = None) -> list[Text | Table]:
    """PDF의 쪽 범위(양 끝 포함)에서 표 밖 글 줄과 작은 표를 차례로 읽는다.

    misses를 주면 읽지 못한 표와 표가 없는 쪽을 {"쪽", "이유"}로 적는다. 표가 없는 쪽은 그 쪽에 무엇이 있는지 이유에 적는다.
    """
    misses = misses if misses is not None else []
    items: list[Text | Table] = []
    state: dict[str, Any] = {}
    with T._open(source) as pdf:
        for number in range(max(first_page, 1), min(last_page, len(pdf.pages)) + 1):
            page = pdf.pages[number - 1]
            got = page_items(page, number, layout, state, misses)
            if not any(isinstance(x, Table) for x in got):
                texts = [x.text for x in got if isinstance(x, Text)]
                if any(layout.section_end.match(x) for x in texts):
                    why = "급부 표 없음(풀이 문단 끝과 다음 절이 시작하는 쪽)"
                elif texts:
                    why = "급부 표 없음(앞 표의 풀이 문단이 이어지는 쪽)"
                else:
                    why = "급부 표도 글도 없음"
                misses.append({"쪽": number, "이유": why})
            items += got
            page.flush_cache()
    return items


def section_range(pages: dict[int, str], layout: LifeLayout = SAMSUNGLIFE) -> T.PageRange:
    """쪽별 글자에서 급부 절의 쪽 범위. 절이 하나여야 한다."""
    proxy = T.Layout(layout.name, section_start=layout.section_start, section_end=layout.section_end,
                     section_title=layout.section_title)
    return T.benefit_pages(pages, layout=proxy)


def read_pdf(source: Path | str | bytes, layout: LifeLayout = SAMSUNGLIFE, first_page: int | None = None,
             last_page: int | None = None, pages: dict[int, str] | None = None) -> tuple[Result, dict[str, Any]]:
    """PDF에서 급부 절을 찾아 조각을 만든다. (결과, 출처). 출처에는 쪽 범위, 꼴, 못 읽은 곳을 적는다."""
    if first_page is None or last_page is None:
        found = section_range(pages if pages is not None else T.page_texts(source), layout)
        first_page, last_page = first_page or found.first_page, last_page or found.last_page
    misses: list[dict[str, Any]] = []
    result = pieces(read_events(source, first_page, last_page, layout, misses), layout)
    source_info = {"쪽": [first_page, last_page], "구간": "", "종": "", "꼴": layout.name, "못 읽은 곳": misses}
    return result, source_info
