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

수집 단계는 PDF를 받은 실행 안에서 글자 파일만 남기고 PDF는 버린다. 표 조각도 그 실행에서
write_riders로 JSON에 써 두면 추출 단계가 read_riders와 to_blocks로 읽는다.
"""
from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Sequence

from .segment import Block

FORMAT = "급부표조각/1"

_HEAD_WORDS = ("보장명", "지급사유", "지급금액")
_SECTION_START = re.compile(r"^□\s*보험금\s*지급사유\s*및\s*지급금액\s*$")
_SECTION_END = re.compile(r"^□\s*보험금\s*지급제한\s*사항")
_LABEL = re.compile(r"^◆\s*(.+?)\s*$")                       # 표 위의 "◆ 기본계약", "◆ 선택계약"
_ONLY = re.compile(r"\s*[*＊※]\s*([^*＊※]*?에\s*한함)\s*")       # 이름 칸에 붙은 "*7종에 한함"
# 종 번호. "7종", 그리고 번호를 이어 적은 "1, 2, 3종", "1~3종"
_VARIANT = re.compile(r"(?<!\d)(\d+(?:\s*(?:[,·ㆍ/~∼-]|및)\s*\d+)*)\s*종")
_VARIANT_STEP = re.compile(r"([~∼-])?\s*(\d+)")
# 칸 안에서 새 문단을 여는 줄. 이런 줄 앞에서는 줄을 잇지 않는다
_PARAGRAPH = re.compile(r"^(?:[※▷▶◆■□●○·∙ㆍ•*＊]|[-–]\s|주\s*\d*\)|\d+[.)]\s|\(\d+\)|[①-⑳])")
_INNER = re.compile(r"^· ([^:\n]*): (.*)$")                   # 칸 안의 작은 표를 풀어 적은 줄
_DOTS = re.compile(r"[·∙ㆍ•‧・]")
_TAGS = re.compile(r"^(?:\[[^\[\]]*\])+")                     # 이름 앞의 "[갱신형][간편]", "[건강]"


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

    @property
    def text(self) -> str:
        """모델이 읽을 글. 세부보장마다 보장명·지급사유·지급금액을 적는다."""
        head = [f"특별약관: {self.title}"]
        if self.label:
            head.append(f"구분: {self.label}")
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
        """이름 칸에 적힌 특별약관 이름들. 지급사유가 같은 특별약관 여럿을 한 행에 쉼표로 이어 적은 표가 있다."""
        return split_names(self.title)

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


def _columns(rows: Sequence[Sequence[str | None]]) -> tuple[int, int, int] | None:
    """머리행을 읽어 (머리행 수, 지급사유 칸 번호, 지급금액 칸 번호)를 알아낸다. 급부 표의 머리행이 없으면 None.

    머리행은 병합 때문에 두세 행으로 갈려 읽히기도 한다. 글자가 머리말뿐인 행을 위에서부터 머리행으로 본다.
    """
    reason = amount = None
    count = 0
    for i, row in enumerate(rows[:4]):
        cells = [squash(c) for c in row]
        if any(c and c not in _HEAD_WORDS for c in cells):
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


def table_lines(table: PageTable) -> list[Line]:
    """표 하나의 행을 역할별로 읽는다. 머리행은 건너뛴다. 급부 표가 아닌 표(머리행이 다른 표)는 빈 목록.

    보장명 칸은 지급사유 칸 왼쪽의 칸 전부다. 맨 왼쪽이 특별약관 이름이고, 나머지 가운데 글자가 있는 칸이
    세부보장 이름이다(쪽에 따라 세로선 자리가 달라 보장명 칸이 셋으로 읽히는 표가 있다).
    """
    found = _columns(table.rows)
    if found is None:
        return []
    count, reason, amount = found
    lines = []
    body = table.rows[count:]
    for i, row in enumerate(body):
        row = list(row) + [None] * (amount + 1 - len(row))
        texts = [c for c in row[reason:amount] if c is not None]
        lines.append(Line(
            page=table.page,
            rider=row[0],
            cover=_first(row[1:reason]) if reason > 1 else None,
            reason="\n".join(texts) if texts else None,
            amount=_first(row[amount:]),
            label=table.label,
            top=i == 0,
            cut=table.open_end and i == len(body) - 1,
        ))
    return lines


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


def _continues(prev: Line | None, line: Line) -> bool:
    """쪽 첫 행이 앞 쪽 마지막 행에서 이어지는 행인가(행 하나가 쪽 끝에서 잘린 경우).

    잘린 행의 뒷부분은 지급금액 칸이 비어 있다(금액은 앞 쪽에 적힌다). 지급금액 칸이 빈 쪽 첫 행 가운데
    - 이름 칸이 모두 비었거나,
    - 앞 행의 지급사유가 문장 가운데서 끊겼거나(표를 읽을 때 알아낸다),
    - 지급사유가 없거나 "※"처럼 덧붙이는 줄로 시작하거나,
    - 이름의 괄호가 앞 행에서 열린 채 끝났거나 이 행에서 닫히기만 하면
    이어지는 행으로 본다. 나머지는 병합된 지급금액 칸이 쪽을 넘어온 새 세부보장이다.
    """
    if prev is None or not line.top or prev.page == line.page or prev.label != line.label:
        return False
    named = bool((line.rider or "").strip() or (line.cover or "").strip())
    if (line.amount or "").strip():
        return not named
    if not named or prev.cut:
        return True
    reason = (line.reason or "").strip()
    if not reason or _PARAGRAPH.match(reason):
        return True
    return (_unclosed(prev.rider) > 0 or _unclosed(prev.cover) > 0
            or _unopened(line.rider) or _unopened(line.cover))


def _name_tail(prev: Line | None, line: Line) -> bool:
    """쪽 첫 행의 특별약관 칸이 앞 쪽 특별약관 이름의 꼬리이고, 행 자체는 새 세부보장인가.

    특별약관 칸은 세부보장 여러 행에 걸쳐 병합되어 있어서, 이름이 길면 칸이 쪽을 넘으며 이름이 두 쪽에 갈린다.
    그런데 앞 쪽 마지막 세부보장 행이 거기서 끝났으면 다음 쪽 첫 행은 이름과 금액이 따로 적힌 새 세부보장이다.
    이름 꼬리는 여는 괄호 없이 닫는 괄호가 먼저 나오는 토막이다("50%)"). 새 특별약관의 이름은 그렇게 시작하지 않는다.
    _continues가 이어지는 행으로 보지 않은 행에만 쓴다(세부보장 칸이 있는 행만).
    """
    return (prev is not None and line.top and prev.page != line.page and prev.label == line.label
            and bool((line.cover or "").strip()) and _unopened(line.rider))


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

    def __init__(self, label: str, name: str | None = None):
        self.label = label
        self.name: list[str] = [name] if name else []
        self.rows: list[dict[str, Any]] = []
        self.last_page = 0

    @property
    def title(self) -> str:
        return split_only(join_name("\n".join(self.name)))[0]

    def add(self, name: str | None, reason: str | None, amount: list[str], page: int) -> None:
        self.rows.append({"name": [name] if name and name.strip() else [], "reason": [reason or ""],
                          "amount": amount, "page": page})

    def close(self) -> Rider:
        """다 모은 토막을 이어 조각을 만든다. 원문에서 괄호가 빠진 이름은 여기서 짝을 맞춘다(mend_brackets)."""
        title, only = split_only(join_name("\n".join(self.name)))
        title = mend_brackets(title)
        covers = []
        for row in self.rows:
            name, cover_only = split_only(join_name("\n".join(row["name"])))
            name = mend_brackets(name)
            covers.append(Cover(name or title, join_text("\n".join(row["reason"])),
                                join_text("\n".join(row["amount"])), row["page"], cover_only))
        title = title or covers[0].name
        return Rider(title, tuple(covers), covers[0].page, max(self.last_page, covers[-1].page), self.label, only)


def group_riders(lines: Iterable[Line]) -> list[Rider]:
    """역할별로 읽은 행을 특별약관 단위로 묶는다.

    - 보장명 왼쪽 칸에 글자가 있으면 새 특별약관이다. 다만 세부보장이 딸린 행에 앞의 특별약관과 같은 이름이
      다시 적혀 있으면(쪽이 바뀐 뒤 이름을 되풀이한 표) 앞의 특별약관이 이어지는 것으로 본다.
    - 왼쪽 칸이 비고(병합 또는 쪽 넘김) 오른쪽 칸에 이름이 있으면 앞 특별약관의 다음 세부보장이다.
    - 쪽 끝에서 잘린 행의 뒷부분(_continues)은 앞 행에 칸별로 이어 붙인다. 이름 토막은 이름에, 지급사유는 지급사유에.
    - 쪽 첫 행의 왼쪽 칸이 앞 특별약관 이름의 꼬리이면(_name_tail, 병합된 칸이 쪽을 넘으며 이름이 갈린 경우)
      꼬리는 특별약관 이름에 잇고, 행은 그 특별약관의 다음 세부보장으로 본다.
    - 지급금액 칸이 병합되어 비었으면(None) 위 행의 값을 물려받는다. 특별약관이 이어지는 쪽 첫 행의
      지급금액 칸이 비었으면 병합된 칸이 쪽을 넘어온 것이므로 마찬가지로 물려받는다.
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

    for line in lines:
        rider, cover = (line.rider or "").strip(), (line.cover or "").strip()
        reason, amount = (line.reason or "").strip(), (line.amount or "").strip()
        if not (rider or cover or reason or amount):
            continue
        if current is not None and current.label != line.label:
            close()

        if current is not None and _continues(prev, line):
            last = current.rows[-1]
            if rider and _title_key(rider) != name_key(current.title):
                current.name.append(line.rider)
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
            if current is not None and _name_tail(prev, line):
                current.name.append(line.rider)     # 이름 꼬리는 앞 특별약관 이름에 잇고, 행은 그 특별약관의 다음 세부보장이다
            elif rider and not (same and cover):
                close()
                current = _Open(line.label, line.rider)
            elif current is None:
                current = _Open(line.label)         # 범위가 특별약관 가운데서 시작한 경우. 첫 세부보장 이름을 제목으로 쓴다
            inherited = line.amount is None or (not amount and line.top and bool(current.rows))
            current.add(line.cover, line.reason, list(last_amount) if inherited else [line.amount or ""], line.page)
        last_amount = current.rows[-1]["amount"]
        current.last_page = max(current.last_page, line.page)
        prev = line
    close()
    return riders


def _title_key(cell: str) -> str:
    """특별약관 이름 칸의 글자를 묶는 중인 특별약관의 제목과 견줄 수 있게 줄인다. 제목처럼 "*7종에 한함"을 떼고 견준다."""
    return name_key(split_only(join_name(cell))[0])


def riders_from_tables(tables: Iterable[PageTable]) -> list[Rider]:
    """쪽 순서로 읽은 표들을 특별약관 조각으로 바꾼다. 급부 표가 아닌 표는 건너뛴다."""
    return group_riders(line for table in tables for line in table_lines(table))


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

def riders_to_json(riders: Iterable[Rider], source: dict[str, Any] | None = None) -> dict[str, Any]:
    """조각 목록을 JSON으로 쓸 수 있는 dict로 바꾼다. source에는 문서 이름·쪽 범위처럼 출처를 적는다."""
    return {
        "형식": FORMAT,
        "출처": dict(source or {}),
        "조각": [{
            "특별약관": r.title, "구분": r.label, "적용범위": r.only, "첫쪽": r.first_page, "끝쪽": r.last_page,
            "세부보장": [{"보장명": c.name, "지급사유": c.reason, "지급금액": c.amount, "쪽": c.page, "적용범위": c.only}
                     for c in r.covers],
        } for r in riders],
    }


def riders_from_json(data: dict[str, Any]) -> list[Rider]:
    if not isinstance(data, dict) or data.get("형식") != FORMAT:
        raise ValueError("급부 표 조각 파일이 아닙니다")
    return [Rider(
        title=r["특별약관"],
        covers=tuple(Cover(c["보장명"], c["지급사유"], c["지급금액"], int(c["쪽"]), c.get("적용범위", ""))
                     for c in r["세부보장"]),
        first_page=int(r["첫쪽"]), last_page=int(r["끝쪽"]), label=r.get("구분", ""), only=r.get("적용범위", ""),
    ) for r in data["조각"]]


def write_riders(path: Path | str, riders: Iterable[Rider], source: dict[str, Any] | None = None) -> None:
    """조각 목록을 JSON 파일로 쓴다."""
    Path(path).write_text(json.dumps(riders_to_json(riders, source), ensure_ascii=False, indent=1), encoding="utf-8")


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


def benefit_ranges(pages: dict[int, str]) -> list[PageRange]:
    """쪽별 글자에서 급부 표가 있는 쪽 범위를 모두 찾는다. 종 구간마다 절이 따로 있는 요약서는 여러 개가 나온다.

    pages는 segment.pages_from_text나 page_texts가 돌려주는 {쪽 번호: 글자}다.
    """
    ranges: list[PageRange] = []
    start: int | None = None
    for n in sorted(pages):
        for line in pages[n].split("\n"):
            line = line.strip()
            if _SECTION_START.match(line):
                if start is not None:
                    ranges.append(PageRange(start, n))
                start = n
            elif start is not None and _SECTION_END.match(line):
                ranges.append(PageRange(start, n))
                start = None
    if start is not None:
        ranges.append(PageRange(start, max(pages)))
    return ranges


def benefit_pages(pages: dict[int, str], section: str | None = None) -> PageRange:
    """급부 표의 쪽 범위 하나를 고른다.

    section은 종 구간의 제목 줄이다(예: "나. 8종(일반형)"). 주면 그 줄이 적힌 쪽부터 찾아 처음 시작하는 급부 절을
    고른다. 안 주면 급부 절이 하나일 때만 돌려주고, 여럿이면 어느 구간인지 정하라고 ValueError를 낸다.
    """
    ranges = benefit_ranges(pages)
    if not ranges:
        raise ValueError("'□ 보험금 지급사유 및 지급금액' 절을 찾지 못했습니다")
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


def _border_edges(page: Any) -> tuple[list[dict], list[dict]]:
    """표의 선만 골라 (가로선, 세로선)으로 돌려준다.

    이 문서들은 표의 선을 가는 채움 사각형으로 그린다. 굵은 채움 사각형(머리행 바탕색, 글자 줄의 흰 배경)까지
    선으로 치면 글자 줄마다 행이 갈린다. 가는 것만 선으로 보고, 테두리를 그은 사각형은 네 변을 선으로 본다.
    한 줄 위에서 칸마다 토막 난 선은 이어 붙인다.
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
    for l in page.lines:
        if abs(l["top"] - l["bottom"]) <= _SNAP:
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


def _text_lines(chars: list[dict]) -> list[_TextLine]:
    """글자들을 줄로 묶는다.

    같은 높이의 글자를 한 줄로 보되, 적힌 차례대로 따라가다 왼쪽으로 되돌아가면 다른 줄로 가른다.
    칸 높이에 가려 보이지 않는 글자가 아랫줄과 같은 자리에 찍혀 있는 곳이 있어서다. 가르지 않으면 두 줄의 글자가 섞인다.
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
                if before is not None and c["x0"] - before["x1"] > 2.5 and not text.endswith(" "):
                    text += " "
                text += c["text"]
            body = re.sub(r"\s+", " ", text).strip()
            if body:
                out.append(_TextLine(level[0]["top"], body + (" " if text[-1:].isspace() else ""),
                                     max(c["x1"] for c in run if not c["text"].isspace()),
                                     run[0]["n"], run[-1]["n"], len(runs) > 1))
    return sorted(out, key=lambda l: (l.top, l.first))


def _cell_text(chars: list[dict], inner: list[Any]) -> str:
    """칸 하나의 글자. 칸 안에 작은 표가 있으면 그 자리에 "· 왼쪽 칸: 오른쪽 칸" 줄로 풀어 넣는다.

    작은 표의 마지막 칸에서 넘쳐 가려진 글자(바깥 글과 겹쳐 찍힌 줄)는 그 칸의 글 끝에 붙인다.
    """
    loose = _text_lines([c for c in chars if not any(_within([c], t.bbox) for t in inner)])
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


def _header(table: Any, chars: list[dict]) -> tuple[float, float] | None:
    """급부 표이면 (지급사유 칸의 왼쪽 좌표, 지급금액 칸의 왼쪽 좌표), 아니면 None."""
    found: dict[str, float] = {}
    for row in table.rows[:4]:
        for cell in row.cells:
            if cell is None:
                continue
            word = squash("".join(c["text"] for c in _within(chars, cell)))
            if word in _HEAD_WORDS:
                found.setdefault(word, cell[0])
    if all(w in found for w in _HEAD_WORDS) and found["지급사유"] < found["지급금액"]:
        return found["지급사유"], found["지급금액"]
    return None


def _label_above(page: Any, top: float, floor: float) -> str:
    """표 바로 위(앞 표의 아래부터)에 적힌 "◆ 기본계약" 같은 구분."""
    if top - floor < 3:
        return ""
    text = page.crop((page.bbox[0], max(floor, page.bbox[1]), page.bbox[2], top)).extract_text() or ""
    labels = [m.group(1) for m in (_LABEL.match(l.strip()) for l in text.split("\n")) if m]
    return labels[-1] if labels else ""


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


def _page_tables(page: Any, number: int, label: str) -> tuple[list[PageTable], str]:
    """한 쪽의 급부 표들과, 다음 쪽으로 넘겨줄 구분(이 쪽에서 마지막으로 본 "◆ …")."""
    h, v = _border_edges(page)
    chars = _numbered(page.chars)
    heads = [(t, columns) for t in _find(page, h, v) for columns in [_header(t, chars)] if columns]
    if not heads:
        return [], label

    def nested(e: dict) -> bool:
        """지급사유 칸 안에 든 작은 표의 선인가. 그대로 두면 바깥 표의 행이 그 선에서 갈린다.

        행을 가르는 가로선은 보장명 칸이나 지급금액 칸까지 뻗는다. 지급사유 칸 안에서 시작하고 끝나는 가로선과
        지급사유 칸 안쪽의 세로선은 작은 표의 것이다.
        """
        for t, (reason_left, amount_left) in heads:
            if e["bottom"] < t.bbox[1] - _SNAP or e["top"] > t.bbox[3] + _SNAP:
                continue
            if e["orientation"] == "h" and e["x0"] >= reason_left - _SNAP and e["x1"] <= amount_left + _SNAP:
                return True
            if e["orientation"] == "v" and reason_left + _SNAP < e["x0"] < amount_left - _SNAP:
                return True
        return False

    inner_h, inner_v = [e for e in h if nested(e)], [e for e in v if nested(e)]
    outer = [t for t, _ in heads]
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
    floor = page.bbox[1]
    for t in sorted(outer, key=lambda t: t.bbox[1]):
        columns = _header(t, chars)
        if columns is None:
            continue
        label = _label_above(page, t.bbox[1], floor) or label
        floor = t.bbox[3]
        mine = _within(_numbered(page.chars, t.bbox), t.bbox)       # 테두리에 걸친 글자까지 이 표의 글자로 본다
        open_end = _open_end(t, mine, columns, inner)
        rows = []
        for row in t.rows:
            cells: list[str | None] = []
            for cell in row.cells:
                if cell is None:
                    cells.append(None)
                    continue
                small = [s for s in inner if cell[0] <= (s.bbox[0] + s.bbox[2]) / 2 < cell[2]
                         and cell[1] <= (s.bbox[1] + s.bbox[3]) / 2 < cell[3]]
                cells.append(_cell_text(_within(mine, cell), small))
            rows.append(cells)
        tables.append(PageTable(number, rows, label, open_end))
    return tables, label


def read_tables(source: Path | str | bytes, first_page: int, last_page: int) -> list[PageTable]:
    """PDF의 쪽 범위(양 끝 포함)에서 급부 표를 읽는다. 머리행이 보장명·지급사유·지급금액인 표만 고른다."""
    tables: list[PageTable] = []
    label = ""
    with _open(source) as pdf:
        for number in range(max(first_page, 1), min(last_page, len(pdf.pages)) + 1):
            page = pdf.pages[number - 1]
            found, label = _page_tables(page, number, label)
            tables += found
            page.flush_cache()
    return tables


def riders_from_pdf(source: Path | str | bytes, first_page: int | None = None, last_page: int | None = None,
                    section: str | None = None, pages: dict[int, str] | None = None) -> list[Rider]:
    """PDF(경로 또는 bytes)에서 급부 표를 읽어 특별약관 조각으로 돌려준다.

    쪽 범위를 주지 않으면 절 제목으로 찾는다. pages(쪽별 글자)를 주면 그것으로, 안 주면 PDF에서 글자를 풀어 찾는다.
    한 요약서에 급부 절이 여러 곳이면 section에 구간 제목을 준다(benefit_pages 참고).
    """
    if first_page is None or last_page is None:
        found = benefit_pages(pages if pages is not None else page_texts(source), section)
        first_page, last_page = first_page or found.first_page, last_page or found.last_page
    return riders_from_tables(read_tables(source, first_page, last_page))


def rider_blocks_from_pdf(source: Path | str | bytes, first_page: int | None = None, last_page: int | None = None,
                          section: str | None = None, pages: dict[int, str] | None = None,
                          variant: str | None = None, max_covers: int | None = None) -> list[Block]:
    """PDF의 급부 표를 특별약관 단위 Block으로 돌려준다. segment.rider_blocks와 같은 자리에 쓴다.

    variant에 종 이름(예: "8종(일반형)")을 주면 "*7종에 한함"처럼 다른 종에만 해당하는 줄을 뺀다.
    """
    riders = riders_from_pdf(source, first_page, last_page, section, pages)
    if variant:
        riders = for_variant(riders, variant)
    return to_blocks(riders, max_covers)
