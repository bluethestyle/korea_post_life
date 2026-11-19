"""공시 문서의 글자를 쪽과 특약 단위로 나눈다.

약관이나 요약서를 통째로 모델에 넣지 않는다. 상품요약서의 "보험금 지급사유" 절을 찾아
"■ 특약명" 줄을 경계로 한 특약씩 잘라 넣는다. 조각마다 쪽 번호를 지녀 화면의 근거 표시에 쓴다.

절 제목과 경계 표시는 회사 이름이 아니라 문서에 적힌 모양으로 알아본다. 지금 알아보는 모양은 셋이다.

- "② 보험금 지급사유" … "③ 일반적 보험금 지급제한 사유", 특약마다 "■ 특약명"
- "나. 보험금 지급사유 및 보험급부별 보험금 지급제한 사유" … "4. 보험료 산출기초", 특약마다 "■ 특약명".
  특약 이름이 길어 두 줄로 갈리기도 하고, 조각 안에서 "[간편가입형]"처럼 가입유형별로 표가 다시 나뉜다.
  특약은 쪽을 바꿔 시작하는데, "■"가 빠진 채 이름만 적힌 머리줄도 있다
- "□ 보험금 지급사유 및 지급금액" … "□ 보험금 지급제한사항". 담보 수백 개가 "보장명 지급사유 지급금액" 표 하나에
  이어져 있고 담보 사이에 경계 표시가 없다. 절은 찾지만 특약 단위로는 자르지 못한다
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_PAGE = re.compile(r"\n?===== (\d+)쪽 =====\n")
_STARTS = (
    re.compile(r"^[②2][\s.)]*보험금\s*지급사유\s*$"),
    re.compile(r"^[가-하]\.\s*보험금\s*지급사유\s*및\s*보험급부별\s*보험금\s*지급제한"),
    re.compile(r"^□\s*보험금\s*지급사유\s*및\s*지급금액\s*$"),
)
_ENDS = (
    re.compile(r"^[③3][\s.)]*일반적\s*보험금\s*지급제한"),
    re.compile(r"^(?:\d+\.\s*)?보험료\s*산출기초"),
    re.compile(r"^□\s*보험금\s*지급제한\s*사항"),
)
_NUMBER_ONLY = re.compile(r"^\d+\.$")        # 절 번호만 따로 한 줄에 적힌 경우. 예: "4." 다음 줄에 "보험료 산출기초"
_HEAD = re.compile(r"^■\s*(.+?)\s*$")
# "■"가 빠진 머리줄. 쪽의 첫 줄에 특약 이름만 적혀 있고 바로 아래에서 표가 시작될 때만 머리줄로 본다.
# 이름에는 "(TA1.1)"처럼 숫자 사이의 점만 있다. 문장이 끝나는 점이 있으면 본문 줄이다
_BARE_HEAD = re.compile(r"^(?!.*\.(?!\d))[^■□\[(※].*특약.*무배당$")
_OPENER = re.compile(r"^(?:\(\s*기준|\[[^\[\]]*가입형[^\[\]]*\]$|□|\(\d+\)|급부명칭)")
_TABLE_HEAD = re.compile(r"^보장명\s+지급사유\s+지급금액\s*$")
# 보험금을 지급하는 특약이 아닌 것. 급부 추출 대상에서 뺀다.
_SKIP = re.compile(r"부담보\s*특약|지정대리청구|전환특약")
_BASES = (
    re.compile(r"보험가입금액\s*([\d,]+)\s*(만|억)\s*원\s*기준"),                     # (특약보험가입금액 1,000만원 기준)
    re.compile(r"기준\s*:\s*(?:보험|특약)\s*가입금액\s*([\d,]+)\s*(만|억)\s*원"),      # (기준 : 특약가입금액 1,000만원)
)
_SCOPE = re.compile(r"^\[([^\[\]]*가입형[^\[\]]*)\]$")     # [간편가입형], [일반가입형 및 건강가입형]


@dataclass(frozen=True)
class Block:
    title: str            # "■" 뒤의 이름. 예: 무배당 암진단특약(20년갱신형) 2606
    text: str             # 머리줄을 포함한 본문
    first_page: int
    last_page: int

    @property
    def is_main(self) -> bool:
        return self.title.replace(" ", "").startswith("주계약")

    @property
    def rider_name(self) -> str:
        """머리줄에 붙은 기준 문구를 뗀 이름. 예: "주계약 (보험가입금액 2,000만 원 기준)" → "주계약"."""
        return re.sub(r"\s*\(.*?기준\)\s*$", "", self.title).strip()

    @property
    def base_amount(self) -> float | None:
        """조각 앞머리에 적힌 기준 가입금액(만 원). 조각 안에 기준이 여럿이면 맨 앞의 것."""
        found = [m for m in (p.search(self.text[:400]) for p in _BASES) if m]
        if not found:
            return None
        m = min(found, key=lambda m: m.start())
        return float(m.group(1).replace(",", "")) * (10000 if m.group(2) == "억" else 1)


def pages_from_text(text: str) -> dict[int, str]:
    """scripts/fetch_disclosure.py가 저장한 글자 파일(쪽 구분선 포함)을 쪽별로 나눈다."""
    parts = _PAGE.split("\n" + text)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def _lines(pages: dict[int, str]) -> list[tuple[int, str]]:
    return [(n, line) for n in sorted(pages) for line in pages[n].split("\n")]


def _bounds(lines: list[tuple[int, str]]) -> tuple[int, int]:
    """보험금 지급사유 절의 (제목 줄, 끝 다음 줄) 위치."""
    start = next((i for i, (_, l) in enumerate(lines) if any(p.match(l.strip()) for p in _STARTS)), None)
    if start is None:
        raise ValueError("'보험금 지급사유' 절을 찾지 못했습니다")
    end = next((i for i in range(start + 1, len(lines)) if any(p.match(lines[i][1].strip()) for p in _ENDS)), len(lines))
    if end < len(lines) and end - 1 > start and _NUMBER_ONLY.match(lines[end - 1][1].strip()):
        end -= 1                # 다음 절의 번호가 제목 윗줄에 따로 적혀 있으면 그 줄도 뺀다
    return start, end


def _unclosed(text: str) -> int:
    return text.count("(") + text.count("[") - text.count(")") - text.count("]")


def _head(lines: list[tuple[int, str]], at: int, end: int) -> str | None:
    """이 줄이 특약 머리줄이면 "■"를 뗀 글자, 아니면 None."""
    line = lines[at][1].strip()
    m = _HEAD.match(line)
    if m:
        return m.group(1)
    if at + 1 < end and lines[at - 1][0] != lines[at][0] and _BARE_HEAD.match(line) and _OPENER.match(lines[at + 1][1].strip()):
        return line
    return None


def _title(lines: list[tuple[int, str]], at: int, end: int) -> str:
    """머리줄의 특약 이름. 이름이 길어 다음 줄로 넘어간 경우 이어 붙인다.

    넘어간 줄로 보는 경우는 둘이다. 괄호가 닫히지 않은 채 줄이 끝났거나("…(고지통" / "합)(KTA1.1) 무배당"),
    끝의 "무배당"이 갈렸을 때("… 무" / "배당").
    """
    title = _head(lines, at, end) or ""
    for i in range(at + 1, min(at + 3, end)):
        more = lines[i][1].strip()
        if not more or _HEAD.match(more):
            break
        if _unclosed(title) > 0 or (len(more) <= 3 and not title.endswith("무배당") and (title + more).endswith("무배당")):
            title += more
        else:
            break
    return title


def benefit_section(pages: dict[int, str]) -> Block:
    """상품요약서의 보험금 지급사유 절 전체. 제목 줄이 title이다. 절이 없으면 ValueError."""
    lines = _lines(pages)
    start, end = _bounds(lines)
    body = lines[start:end]
    return Block(body[0][1].strip(), "\n".join(l for _, l in body).strip(), body[0][0], body[-1][0])


def rider_blocks(pages: dict[int, str], include_skipped: bool = False) -> list[Block]:
    """상품요약서의 보험금 지급사유 절을 특약 단위 조각으로 나눈다."""
    lines = _lines(pages)
    start, end = _bounds(lines)
    blocks: list[Block] = []
    current: list[tuple[int, str]] = []
    at = 0

    def close() -> None:
        if not current:
            return
        title = _title(lines, at, end)
        if include_skipped or not _SKIP.search(title):
            blocks.append(Block(title, "\n".join(l for _, l in current).strip(), current[0][0], current[-1][0]))

    for i in range(start + 1, end):
        page, line = lines[i]
        if _head(lines, i, end) is not None:
            close()
            current, at = [(page, line)], i
        elif current:
            current.append((page, line))
    close()
    if not blocks and any(_TABLE_HEAD.match(l.strip()) for _, l in lines[start + 1:end]):
        raise ValueError("'보험금 지급사유' 절은 찾았지만 특약 경계(■)가 없습니다. "
                         "담보가 '보장명 지급사유 지급금액' 표 하나에 이어진 형식은 특약 단위로 자르지 못합니다")
    return blocks


def scope_parts(block: Block) -> list[tuple[str, str]]:
    """조각 안에서 가입유형별로 갈린 표를 나눈다. (가입유형 글자, 그 부분의 본문) 목록.

    "[간편가입형]", "[일반가입형 및 건강가입형]"처럼 가입유형만 적힌 줄이 경계다. 부분마다 머리줄(특약 이름)을 앞에 붙인다.
    그런 줄이 없으면 가입유형 글자가 빈 한 부분으로 돌려준다.
    """
    head: list[str] = []
    parts: list[tuple[str, list[str]]] = []
    for line in block.text.split("\n"):
        m = _SCOPE.match(line.strip())
        if m:
            parts.append((m.group(1).strip(), []))
        elif parts:
            parts[-1][1].append(line)
        else:
            head.append(line)
    if not parts:
        return [("", block.text)]
    return [(scope, "\n".join(head + body).strip()) for scope, body in parts]


_SCOPE_SPLIT = re.compile(r"\s*(?:및|,|·|/)\s*")


def scope_matches(scope: str, variant_name: str) -> bool:
    """가입유형 표시가 이 종형에 해당하는가. 표시가 비어 있으면 모든 종형에 해당한다.

    "[일반가입형 및 건강가입형]"은 "일반가입형"과 "건강가입형"에, "[간편가입형]"은 "간편가입형(1년)"처럼
    그 글자로 시작하는 종형 모두에 해당한다.
    """
    if not scope.strip():
        return True
    name = variant_name.replace(" ", "")
    return any(name.startswith(part.replace(" ", "")) for part in _SCOPE_SPLIT.split(scope.strip()) if part.strip())


_RENEWAL_LIST = re.compile(r"^[▪■□ㆍ·-]?\s*갱신형\s*특약\s*:?\s*$")
_RENEWAL_GROUP = re.compile(r"^-\s*((?:\d+\s*년만기\s*,?\s*)+)자동갱신")
_RENEWAL_ITEM = re.compile(r"^[·∙ㆍ]\s*(.+)$")
_RENEWAL_STOP = re.compile(r"^(?:[가-하]\.\s|▪|-\s)")
_PAGE_FOOT = re.compile(r"^\d+\s*/\s*\d+$")


def rider_key(name: str) -> str:
    """특약 이름을 목록과 머리줄에서 서로 맞춰 볼 수 있게 줄인다.

    목록에는 "…(갱신형)(무)", 급부 표의 머리줄에는 "…(갱신형)(TA1.1) 무배당"으로 적힌다. 끝의 표기와 빈칸,
    가운뎃점 모양 차이를 없앤다.
    """
    key = re.sub(r"\s+", "", name)
    key = re.sub(r"(?:\((?:무|K?TA[\d.]+)\))?(?:무배당)?$", "", key)
    return re.sub(r"[·∙ㆍ•]", "·", key)


def renewal_periods(pages: dict[int, str]) -> dict[str, list[int]]:
    """요약서의 "갱신형 특약" 목록에서 특약별 갱신 주기(년)를 읽는다. {rider_key(이름): [5, 10]}. 목록이 없으면 빈 dict.

    "- 10년만기, 20년만기, 30년만기 자동갱신(최대 종신)" 같은 줄 아래 "· 특약명"이 이어지는 모양을 읽는다.
    이름이 길어 다음 줄로 넘어간 것은 이어 붙인다.
    """
    out: dict[str, list[int]] = {}
    years: list[int] | None = None
    inside = False
    name: str | None = None

    def close() -> None:
        nonlocal name
        if name and years:
            out[rider_key(name)] = years
        name = None

    for _, raw in _lines(pages):
        line = raw.strip()
        if not inside:
            inside = bool(_RENEWAL_LIST.match(line))
            continue
        if not line or _PAGE_FOOT.match(line):
            continue
        group = _RENEWAL_GROUP.match(line)
        if group:
            close()
            years = [int(n) for n in re.findall(r"(\d+)\s*년만기", group.group(1))]
            continue
        item = _RENEWAL_ITEM.match(line)
        if item:
            close()
            name = item.group(1)
            continue
        if _RENEWAL_STOP.match(line):       # 다음 절이나 주기 없는 줄("- …납입면제특약: 부가대상 계약…")
            close()
            years = None
            if not line.startswith("-"):
                break
            continue
        if name is not None:
            name += line
    close()
    return out
