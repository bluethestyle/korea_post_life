"""초기 적재의 두 판독(교차 확인)이 낸 값을 검사하고, 견주고, sys_특약과 sys_급부 행으로 옮긴다.

초기 적재(2026-11-20 결정)는 Gemini API와 판정 모델을 쓰지 않는다. 두 판독자(sonnet, opus)가 표 읽기
(extract/tables.py)가 낸 조각의 세부보장 한 줄마다 값을 따로 내고, 코드가 둘을 견주고 원문 글자와 대조한다.
두 판독이 같고 기계 검사를 통과하면 확정이고, 다르거나 기계 검사에 걸리면 메인 세션이 원문 쪽을 보고 판정한다.

판독 단위와 번호
    세부보장 한 줄. 번호는 조각 파일의 조각 순번(3자리, 1부터)과 세부보장 순번이다: "R012-3".
    scripts/compare_table_rules.py, table_rules.Outcome.numbers와 같은 번호다.
    판독자는 이름을 고치거나 새로 짓지 않는다. 특약ID와 급부ID는 조각에 적힌 이름으로 만든다.

판독 값(FORMAT "판독값/1")의 칸. 설명은 docs/backfill_reader_guide.md
    번호, 쪽               세부보장 번호와 값을 읽은 PDF 쪽
    꼴                     가입금액비율 | 금액 | 행없음 | 모름
    행없음사유             꼴이 행없음일 때 NO_ROW_KINDS 가운데 하나
    대상                   한 조각 안에 이름이 같은 세부보장이 여럿일 때만: 그 줄의 지급사유에 적힌 대상 낱말(30자 이하).
                           급부명은 table_rules.Reading.label처럼 "세부보장명(대상)"이 된다
    지급률                 가입금액비율: 감액이 끝난 뒤 가입금액의 몇 %인가(숫자)
    기준가입금액만원, 지급액만원   금액: 표에 적힌 기준 가입금액과 지급액(만 원)
    지급률곱               가입금액에 (장해)지급률을 곱해 지급하는가
    지급단위               "" | 1일당 | 1회당 | 1사고당
    감액                   [{기간, 단위(일|개월|년), 값, 값기준(가입금액|보험금|만원)}] 많아야 둘
    감액대상               감액이 일부 경우에만 걸리면 그 경우를 가리키는 낱말. 모두에 걸리면 ""
    감액예외               [{대상, 자리(지급사유|지급금액|주석)}] 감액하지 않는 경우
    면책일수, 보장개시일   보장개시일까지의 날수와 그 보장개시일 이름. 계약일부터 보장하면 0과 ""
    한도                   [{앞말, 수, 단위(회|일)}] 지급 횟수나 일수 한도
    주의                   NOTICE_KINDS. 행은 만들지만 스키마가 담지 못하는 정보
    모름                   [{칸, 이유}] 읽지 못한 칸
    행없음 줄도 면책일수, 보장개시일, 한도를 채우고 견준다(행은 만들지 않아도 정보는 남긴다).

원문 구절이 들어가는 시트 열(지급횟수제한, 감액예외)은 판독 값이 아니라 조각 글자에서 코드가 잘라 쓴다.
판독 값은 앞말, 횟수, 단위, 낱말만 주고, 코드는 그 구조에 맞는 구절을 그 세부보장의 글자(지급사유, 지급금액,
보장명)와 그 특약의 주석에서 찾는다. 찾지 못하면 기계 검사에 걸린다.

쓰는 법
    pieces = load_pieces(json.load(...))             # 조각 파일(급부표조각/1)이나 묶음 파일(판독묶음/1)
    a, errs = parse_readings(json.load(...))         # 판독 파일 하나
    states = compare(a, b)                           # 번호 → {칸: 같음 | 다름 | 한쪽모름 | 둘다모름}
    problems = machine_checks(cover, reading)        # 한 판독의 기계 검사
    built = build_rows(variant_id, pieces, finals, renewal_years={"갱신형 가나": 20})
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .. import ids
from . import benefits as B
from . import table_rules as T

FORMAT = "판독값/1"
BUNDLE_FORMAT = "판독묶음/1"
PIECES_FORMAT = "급부표조각/1"

RATIO, AMOUNT, NO_ROW, UNKNOWN = "가입금액비율", "금액", "행없음", "모름"
FORMS = (RATIO, AMOUNT, NO_ROW, UNKNOWN)
# 스키마의 급부 행(지급률 하나, 감액 둘, 면책 하나)으로 담을 수 없는 꼴. 행을 만들지 않고 사유를 남긴다
NO_ROW_KINDS = (
    "가입금액구간별금액표",   # 칸 안의 표가 가입금액 구간마다 다른 금액을 적는다(항목 행과 구간 열이 겹친 표도)
    "항목별금액표",           # 치료 항목마다 금액이나 지급률이 다르다(통합치료비, 통합일당)
    "회차별지급률",           # 1회차 100%, 2회차 125% …
    "경과기간별지급률",       # 진단 후 경과 연도별, 계약일부터 경과시점별(1년 전과 후 열)로 달라지는 지급률
    "단위당단가",             # 흉터 1cm당 금액처럼 길이, 면적 같은 단위마다 금액이 붙는다
    "조문별한도",             # 벌금처럼 법 조문이나 위반 종류마다 한도 금액이 다르다
    "등급별지급률",           # 손상중증도점수, 부상등급, 중증도별
    "조건별지급률",           # 간병인 사용금액 7만원 미만과 이상처럼 조건마다 지급률이 다르다
    "치료차수별지급률",       # 최초 치료와 두 번째 치료부터의 지급률이 다르다
    "약물종류개수별",         # 연간 약물종류 개수에 따라 세부보장이 갈린다
    "종구분별가입금액",       # 1-7종 수술처럼 종마다 가입금액이 따로 있다
    "실제손해액",             # 실제 비용, 손해액, 합의금을 한도 안에서 지급
    "정기분할지급",           # 매월 N년간 확정지급
    "현물급부",               # 간병인 지원, 변호사 선임처럼 돈이 아닌 급부
    "그밖",
)
UNITS = ("", "1일당", "1회당", "1사고당")
CUT_UNITS = ("일", "개월", "년")
CUT_BASES = ("가입금액", "보험금", "만원")
PLACES = ("지급사유", "지급금액", "주석")
LEADS = ("없음", "최초", "연간", "월간", "1회입원당", "1사고당", "보험기간")
LIMIT_UNITS = ("회", "일")
NOTICE_KINDS = (
    "나이별보장개시일",       # 15세 미만은 계약일부터 보장하는 것처럼 나이에 따라 보장개시일이 다르다
    "면책예외",               # 한 줄에 면책이 있는 대상과 없는 대상이 함께 나온다(상해는 면책기간이 없는 것처럼)
    "세부보장여럿묶임",       # 서로 다른 급부가 한 줄에 묶여 값이 대상별로 달라진다. 본형과 갱신형 특약 이름을 "/"로
                              # 이은 줄(값이 한 벌)은 넣지 않는다
    "현물선택",               # 돈 대신 현물(간병인 지원)을 고를 수 있다
    "지급기간중감액",         # 감액이 보험금 지급기간 동안 걸린다
    "그밖",
)
# 두 판독이 같아도 자동 확정하지 않는 주의와 행없음사유. 묶인 세부보장은 삼성화재 규칙(table_rules.D_BUNDLE)도 검토로 둔다
REVIEW_NOTICES = ("세부보장여럿묶임", "그밖")


def needs_review(v: Mapping[str, Any] | None) -> bool:
    return bool(v) and (any(n in REVIEW_NOTICES for n in v.get("주의") or []) or v.get("행없음사유") == "그밖")


FIELDS = ("꼴", "행없음사유", "대상", "지급률", "기준가입금액만원", "지급액만원", "지급률곱", "지급단위", "감액",
          "감액대상", "감액예외", "면책일수", "보장개시일", "한도", "주의")
_KEYS = set(FIELDS) | {"번호", "쪽", "모름", "면책근거쪽"}
_NUMBER = re.compile(r"^R\d{3}-\d+$")
_SHORT = 30                 # 낱말 칸의 길이 한도. 원문 문장을 옮겨 적지 못하게 한다
_REASON = 80                # 모름 이유의 길이 한도

SAME, DIFF, ONE_UNKNOWN, BOTH_UNKNOWN = "같음", "다름", "한쪽모름", "둘다모름"
CONFIRMED, NEEDS_JUDGE = "확정", "판정필요"


def number(piece_index: int, cover_index: int) -> str:
    return f"R{piece_index:03d}-{cover_index}"


# ---------------------------------------------------------------------------
# 조각과 묶음 읽기
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CoverView:
    number: str
    name: str
    reason: str
    amount: str
    page: int
    only: str = ""


@dataclass(frozen=True)
class PieceView:
    index: int                      # 조각 파일의 순번(1부터)
    title: str
    names: tuple[str, ...]          # 특약명들. 비어 있으면 title 하나
    label: str                      # 구분(기본계약, 선택계약)
    segment: str                    # 형. 형 구간이 없는 문서는 ""
    first_page: int
    last_page: int
    covers: tuple[CoverView, ...]
    notes: tuple[str, ...] = ()     # 그 특약에 걸린 주석의 글

    @property
    def number(self) -> str:
        return f"R{self.index:03d}"


def note_owners(piece: Mapping[str, Any], notes: Sequence[Mapping[str, Any]]) -> list[str]:
    """조각 파일의 "주석" 가운데 이 조각에 걸린 것의 글.

    주석에는 쪽, 형, 특약 머리가 적혀 있다. 형이 같고, 특약 머리가 적혀 있으면 그 이름이 조각의 특별약관과 같은 것,
    특약 머리가 비어 있으면 그 쪽이 조각의 쪽 범위 안에 드는 것이 그 조각의 주석이다. 그렇게 걸린 주석이 없는데
    조각의 글에 "주1)", "주)" 같은 표시가 있으면, 같은 형에서 조각의 끝쪽이나 그 뒤에 나오는 첫 주석(특약 머리 없음)을
    건다. 메리츠화재 통합간편 요약서는 형 구간의 표가 끝나는 쪽에 그 구간의 주석을 모아 적는다(예: 120쪽 표의 "주1)"을
    138쪽 주석이 푼다).
    """
    same = [n for n in notes if (n.get("형") or "") == (piece.get("형") or "")]
    out = []
    for note in same:
        head = note.get("특약머리") or ""
        if head:
            if head == piece["특별약관"]:
                out.append(note["글"])
        elif int(piece["첫쪽"]) <= int(note["쪽"]) <= int(piece["끝쪽"]):
            out.append(note["글"])
    text = "\n".join((c.get("지급사유") or "") + "\n" + (c.get("지급금액") or "") for c in piece.get("세부보장") or [])
    if not out and _NOTE_MARK.search(text):
        later = sorted((n for n in same if not n.get("특약머리") and int(n["쪽"]) >= int(piece["끝쪽"])),
                       key=lambda n: int(n["쪽"]))
        if later:
            out.append(later[0]["글"])
    return out


_NOTE_MARK = re.compile(r"주\d*\)")


def load_pieces(data: Mapping[str, Any]) -> list[PieceView]:
    """조각 파일(급부표조각/1)이나 묶음 파일(판독묶음/1)을 읽는다. 번호는 원래 조각 파일의 순번을 지킨다."""
    kind = data.get("형식") if isinstance(data, Mapping) else None
    if kind == PIECES_FORMAT:
        notes = data.get("주석") or []
        out = []
        for i, p in enumerate(data["조각"], 1):
            covers = tuple(CoverView(number(i, j), c["보장명"], c["지급사유"] or "", c["지급금액"] or "", int(c["쪽"]),
                                     c.get("적용범위") or "") for j, c in enumerate(p["세부보장"], 1))
            out.append(PieceView(i, p["특별약관"], tuple(p.get("특약명들") or ()), p.get("구분") or "", p.get("형") or "",
                                 int(p["첫쪽"]), int(p["끝쪽"]), covers, tuple(note_owners(p, notes))))
        return out
    if kind == BUNDLE_FORMAT:
        out = []
        for p in data["조각"]:
            index = int(p["조각번호"][1:])
            covers = tuple(CoverView(c["번호"], c["세부보장명"], c["지급사유"] or "", c["지급금액"] or "", int(c["쪽"]),
                                     c.get("적용범위") or "") for c in p["세부보장"])
            out.append(PieceView(index, p["특약명"], tuple(p.get("특약명들") or ()), p.get("구분") or "", p.get("형") or "",
                                 int(p["쪽"][0]), int(p["쪽"][1]), covers, tuple(p.get("주석") or ())))
        return out
    raise ValueError("조각 파일이나 묶음 파일이 아닙니다")


def covers_by_number(pieces: Iterable[PieceView]) -> dict[str, tuple[PieceView, CoverView]]:
    return {c.number: (p, c) for p in pieces for c in p.covers}


FINGERPRINT_LENGTH = 12


def cover_fingerprint(piece: PieceView, cover: CoverView) -> str:
    """세부보장 한 줄의 조각 지문. 판독자가 읽은 조각과 다시 읽은 조각이 같은지 확인하는 짧은 해시다.

    그 줄의 글자(세부보장명, 지급사유, 지급금액, 쪽, 적용범위)와 그 조각의 머리(특약명, 특약명들, 구분, 형)와 그 조각에
    걸린 주석을 빈칸을 떼고 이어 해시한다. 원문 글자는 남기지 않는다. 조각 파일(급부표조각/1)로 읽은 조각에서 만든다.
    묶음 파일에는 구분이 없어 같은 값이 나오지 않는다. 특약명들은 둘 이상일 때만 넣는다(하나뿐이면 특약명과 같다).
    """
    names = piece.names if len(piece.names) > 1 else ()
    parts = (piece.title, "/".join(names), piece.label, piece.segment, cover.name, cover.reason, cover.amount,
             str(cover.page), cover.only, "\n".join(piece.notes))
    return ids.short_hash(*(_squash(p) for p in parts), length=FINGERPRINT_LENGTH)


# ---------------------------------------------------------------------------
# 판독 값의 꼴 검사
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {
    "행없음사유": "", "대상": "", "지급률": None, "기준가입금액만원": None, "지급액만원": None, "지급률곱": False, "지급단위": "",
    "감액": [], "감액대상": "", "감액예외": [], "면책일수": 0, "보장개시일": "", "면책근거쪽": None, "한도": [],
    "주의": [], "모름": [],
}


def _num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def check_format(item: Any) -> list[str]:
    """판독 값 한 줄의 꼴 문제. 비어 있으면 통과."""
    if not isinstance(item, Mapping):
        return ["줄이 객체가 아님"]
    out: list[str] = []
    for extra in sorted(set(item) - _KEYS):
        out.append(f"정의되지 않은 칸: {extra}")
    if not isinstance(item.get("번호"), str) or not _NUMBER.match(item["번호"]):
        out.append("번호가 R000-0 꼴이 아님")
    if not _int(item.get("쪽")):
        out.append("쪽이 정수가 아님")
    v = {**DEFAULTS, **item}
    form = v.get("꼴")
    if form not in FORMS:
        out.append(f"꼴이 허용값이 아님: {form!r}")
    if form == NO_ROW and v["행없음사유"] not in NO_ROW_KINDS:
        out.append(f"행없음사유가 허용값이 아님: {v['행없음사유']!r}")
    if form != NO_ROW and v["행없음사유"]:
        out.append("행없음이 아닌데 행없음사유가 있음")
    if not isinstance(v["대상"], str) or len(v["대상"]) > _SHORT:
        out.append(f"대상이 {_SHORT}자 이하의 글이 아님")
    unknown = _unknown_fields(v)
    if form == RATIO and "지급률" not in unknown and not (_num(v["지급률"]) and v["지급률"] > 0):
        out.append("가입금액비율인데 지급률이 양수가 아님")
    if form == AMOUNT:
        for name in ("기준가입금액만원", "지급액만원"):
            if name not in unknown and not (_num(v[name]) and v[name] > 0):
                out.append(f"금액인데 {name}이 양수가 아님")
    for name in ("지급률", "기준가입금액만원", "지급액만원"):
        if v[name] is not None and not _num(v[name]):
            out.append(f"{name}이 숫자가 아님")
    if not isinstance(v["지급률곱"], bool):
        out.append("지급률곱이 참거짓이 아님")
    if v["지급단위"] not in UNITS:
        out.append(f"지급단위가 허용값이 아님: {v['지급단위']!r}")
    cuts = v["감액"]
    if not isinstance(cuts, list) or len(cuts) > 2:
        out.append("감액이 둘 이하의 목록이 아님")
    else:
        for c in cuts:
            if not isinstance(c, Mapping) or set(c) - {"기간", "단위", "값", "값기준"}:
                out.append("감액 항목의 칸이 다름")
                continue
            if not (_int(c.get("기간")) and c["기간"] > 0) or c.get("단위") not in CUT_UNITS:
                out.append("감액 기간이 양의 정수와 일, 개월, 년이 아님")
            if not (_num(c.get("값")) and c["값"] > 0) or c.get("값기준") not in CUT_BASES:
                out.append("감액 값이 양수와 가입금액, 보험금, 만원이 아님")
            elif form == RATIO and c["값기준"] == "만원":
                out.append("가입금액비율인데 감액 값기준이 만원")
            elif form == AMOUNT and c["값기준"] == "가입금액":
                out.append("금액인데 감액 값기준이 가입금액")
    if not isinstance(v["감액대상"], str) or len(v["감액대상"]) > _SHORT:
        out.append(f"감액대상이 {_SHORT}자 이하의 글이 아님")
    excepts = v["감액예외"]
    if not isinstance(excepts, list):
        out.append("감액예외가 목록이 아님")
    else:
        for e in excepts:
            if not isinstance(e, Mapping) or set(e) - {"대상", "자리"} or not isinstance(e.get("대상"), str) \
                    or not e["대상"].strip() or len(e["대상"]) > _SHORT or e.get("자리") not in PLACES:
                out.append("감액예외 항목이 {대상(짧은 낱말), 자리(지급사유, 지급금액, 주석)}가 아님")
    if not (_int(v["면책일수"]) and v["면책일수"] >= 0):
        out.append("면책일수가 0 이상의 정수가 아님")
    if not isinstance(v["보장개시일"], str) or len(v["보장개시일"]) > _SHORT:
        out.append("보장개시일이 짧은 글이 아님")
    elif _int(v["면책일수"]) and v["면책일수"] > 0 and not v["보장개시일"].strip() and "면책일수" not in unknown:
        out.append("면책일수가 있는데 보장개시일 이름이 비어 있음")
    if v["면책근거쪽"] is not None and not _int(v["면책근거쪽"]):
        out.append("면책근거쪽이 정수가 아님")
    limits = v["한도"]
    if not isinstance(limits, list):
        out.append("한도가 목록이 아님")
    else:
        for x in limits:
            if not isinstance(x, Mapping) or set(x) - {"앞말", "수", "단위"} or x.get("앞말") not in LEADS \
                    or not (_int(x.get("수")) and x["수"] > 0) or x.get("단위") not in LIMIT_UNITS:
                out.append("한도 항목이 {앞말, 수(양의 정수), 단위(회, 일)}가 아님")
    notices = v["주의"]
    if not isinstance(notices, list) or any(n not in NOTICE_KINDS for n in notices):
        out.append("주의에 허용값이 아닌 것이 있음")
    blanks = v["모름"]
    if not isinstance(blanks, list):
        out.append("모름이 목록이 아님")
    else:
        for b in blanks:
            if not isinstance(b, Mapping) or b.get("칸") not in FIELDS or not isinstance(b.get("이유"), str) \
                    or not b["이유"].strip() or len(b["이유"]) > _REASON:
                out.append(f"모름 항목이 {{칸, 이유({_REASON}자 이하)}}가 아님")
    if form == UNKNOWN and not blanks:
        out.append("꼴이 모름인데 모름 이유가 없음")
    return out


def _unknown_fields(v: Mapping[str, Any]) -> set[str]:
    if v.get("꼴") == UNKNOWN:
        return set(FIELDS)
    return {b.get("칸") for b in (v.get("모름") or []) if isinstance(b, Mapping)}


def parse_readings(data: Any) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """판독 파일 하나를 {번호: 판독 값}으로 읽는다. 꼴이 틀린 줄은 빼고 문제로 돌려준다."""
    if not isinstance(data, Mapping) or data.get("형식") != FORMAT or not isinstance(data.get("값"), list):
        return {}, [f"판독 파일의 형식이 {FORMAT}이 아니거나 값 목록이 없음"]
    out: dict[str, dict[str, Any]] = {}
    problems: list[str] = []
    for item in data["값"]:
        errs = check_format(item)
        key = item.get("번호") if isinstance(item, Mapping) else None
        if errs:
            problems.append(f"{key}: {'; '.join(errs)}")
            continue
        if key in out:
            problems.append(f"{key}: 번호가 두 번 나옴")
            continue
        out[key] = {**DEFAULTS, **item}
    return out, problems


# ---------------------------------------------------------------------------
# 값 맞추기와 두 판독 견주기
# ---------------------------------------------------------------------------

def _squash(text: str) -> str:
    return re.sub(r"\s", "", text or "")


def cut_steps(v: Mapping[str, Any]) -> tuple[tuple[int, float], ...] | None:
    """감액을 (개월, 그 기간에 받는 비율 0~1)로 바꾼다. 짧은 기간부터. 바꿀 수 없으면 None."""
    out = []
    for c in v.get("감액") or []:
        months, _ = T._months(int(c["기간"]), c["단위"])
        value = float(c["값"])
        if c["값기준"] == "보험금":
            rate = value / 100
        elif c["값기준"] == "가입금액":
            if not _num(v.get("지급률")) or not v["지급률"]:
                return None
            rate = value / float(v["지급률"])
        else:
            if not _num(v.get("지급액만원")) or not v["지급액만원"]:
                return None
            rate = value / float(v["지급액만원"])
        out.append((months, round(rate, 4)))
    return tuple(sorted(out))


def _word(text: str) -> str:
    return re.sub(r"[\s「」『』\"'“”‘’]", "", text or "")


_QUOTES = re.compile(r"[「」『』\"'“”‘’]")


def target_text(text: str) -> str:
    """대상 낱말을 급부명에 붙일 꼴로 다듬는다. 따옴표와 낫표를 떼고 빈칸을 하나로 줄인다."""
    return " ".join(_QUOTES.sub(" ", text or "").split())


def target_key(text: str) -> str:
    """대상을 견주는 열쇠. 급부ID를 만드는 다듬기(ids.benefit_id: 빈칸, 가운뎃점, 쉼표, 괄호, "또는", "및"을 뗀다)와 같다.

    두 판독의 대상이 이 열쇠로 같으면 같은 대상이고, 그 줄의 급부ID도 같다.
    """
    return ids._LOOSE.sub("", ids.normalize(target_text(text)))


def normalized(v: Mapping[str, Any]) -> dict[str, Any]:
    """칸마다 견줄 수 있는 값. 모름인 칸은 UNKNOWN."""
    unknown = _unknown_fields(v)
    out: dict[str, Any] = {
        "꼴": v.get("꼴"),
        "행없음사유": v.get("행없음사유") or "",
        "대상": target_key(v.get("대상") or ""),
        "지급률": float(v["지급률"]) if _num(v.get("지급률")) else None,
        "기준가입금액만원": float(v["기준가입금액만원"]) if _num(v.get("기준가입금액만원")) else None,
        "지급액만원": float(v["지급액만원"]) if _num(v.get("지급액만원")) else None,
        "지급률곱": bool(v.get("지급률곱")),
        "지급단위": v.get("지급단위") or "",
        "감액": cut_steps(v),
        "감액대상": _word(v.get("감액대상", "")),
        "감액예외": tuple(sorted({_word(e["대상"]) for e in v.get("감액예외") or []})),
        "면책일수": v.get("면책일수", 0),
        "보장개시일": _word(v.get("보장개시일", "")),
        "한도": tuple(sorted({(x["앞말"], x["수"], x["단위"]) for x in v.get("한도") or []})),
        "주의": tuple(sorted(set(v.get("주의") or []))),
    }
    for name in unknown:
        out[name] = UNKNOWN
    return out


NO_ROW_FIELDS = ("꼴", "행없음사유", "면책일수", "보장개시일", "한도")


def relevant(form: str) -> tuple[str, ...]:
    """꼴에 따라 견줄 칸. 행없음이면 사유와, 행을 만들지 않아도 남기는 면책일수, 보장개시일, 한도를 본다."""
    if form == NO_ROW:
        return NO_ROW_FIELDS
    if form == RATIO:
        return tuple(f for f in FIELDS if f not in ("행없음사유", "기준가입금액만원", "지급액만원"))
    if form == AMOUNT:
        return tuple(f for f in FIELDS if f not in ("행없음사유", "지급률"))
    return FIELDS


def compare_one(a: Mapping[str, Any] | None, b: Mapping[str, Any] | None) -> dict[str, str]:
    """두 판독의 칸별 상태. 한쪽에 줄이 없으면 그쪽은 모든 칸이 모름이다."""
    na = normalized(a) if a else {f: UNKNOWN for f in FIELDS}
    nb = normalized(b) if b else {f: UNKNOWN for f in FIELDS}
    forms = {na["꼴"], nb["꼴"]} - {UNKNOWN}
    names = relevant(forms.pop()) if len(forms) == 1 else FIELDS
    out = {}
    for name in names:
        x, y = na[name], nb[name]
        if x == UNKNOWN and y == UNKNOWN:
            out[name] = BOTH_UNKNOWN
        elif UNKNOWN in (x, y):
            out[name] = ONE_UNKNOWN
        else:
            out[name] = SAME if x == y else DIFF
    return out


def compare(a: Mapping[str, Mapping[str, Any]], b: Mapping[str, Mapping[str, Any]],
            numbers: Iterable[str] | None = None) -> dict[str, dict[str, str]]:
    """번호 → 칸별 상태. numbers를 주면 그 번호만, 차례대로 본다."""
    keys = list(numbers) if numbers is not None else sorted(set(a) | set(b), key=_order)
    return {k: compare_one(a.get(k), b.get(k)) for k in keys}


def _order(key: str) -> tuple[int, int]:
    head, tail = key[1:].split("-")
    return int(head), int(tail)


def agreed(states: Mapping[str, str]) -> bool:
    return all(s == SAME for s in states.values())


# ---------------------------------------------------------------------------
# 원문에서 구절 잘라 쓰기
# ---------------------------------------------------------------------------

_LEAD_RE = {
    "없음": "",
    "최초": r"최초\s*",
    "연간": r"연간\s*(?:최대\s*)?",
    "월간": r"월간\s*(?:최대\s*)?",
    "1회입원당": r"1\s*회\s*입원\s*당\s*",
    "1사고당": r"(?:1\s*)?사고\s*당\s*",
    "보험기간": r"보험기간\s*(?:중\s*)?",
}
_LIMIT_TAIL = r"(?:\s*(?:에\s*)?(?:한하여|한함|한정|한도|한))"
_UNIT_RE = {
    "1일당": r"(?:(?:입원|통원|사용|간병인\s*사용|간호·?\s*간병통합서비스\s*사용)\s*)?1\s*일\s*당",
    "1회당": r"(?:(?:수술|통원|입원)\s*)?1\s*회\s*(?:[가-힣]{1,8}\s*)?당",
    "1사고당": r"1\s*사고\s*당",
}
_TIMES_RE = re.compile(r"[×✕xX]\s*(?:해당\s*)?(?:장해\s*)?지급률")


def _texts(cover: CoverView, piece: PieceView | None, with_name: bool = True) -> list[str]:
    out = [cover.reason, cover.amount]
    if with_name:
        out.append(cover.name)
    if piece is not None:
        out += list(piece.notes)
    return [t for t in out if t]


def _tidy(text: str) -> str:
    return " ".join(text.split())


def limit_phrase(x: Mapping[str, Any], cover: CoverView, piece: PieceView | None = None) -> str | None:
    """한도 구조({앞말, 수, 단위})에 맞는 원문 구절. 지급사유, 지급금액, 보장명, 주석의 차례로 찾는다. 없으면 None.

    앞말이 "없음"이면 뒤에 한도를 뜻하는 말(한도, 한, 에 한하여)이 붙은 자리만 본다. 그러지 않으면
    "90일이 지난 다음날" 같은 다른 숫자에 걸린다. 앞에 "각각"이 붙어 있으면 함께 자른다.
    """
    lead = _LEAD_RE[x["앞말"]]
    tail = _LIMIT_TAIL if x["앞말"] == "없음" else _LIMIT_TAIL + "?"
    pattern = re.compile(rf"(?:각각\s*)?{lead}(?<![\d.]){x['수']}\s*{x['단위']}{tail}")
    for text in _texts(cover, piece):
        m = pattern.search(text)
        if m:
            return _tidy(m.group(0))
    return None


def unit_phrase(unit: str, cover: CoverView) -> str | None:
    """지급단위(1일당 따위)의 원문 구절. 지급금액, 지급사유의 차례로 찾는다."""
    if not unit:
        return ""
    pattern = re.compile(_UNIT_RE[unit])
    for text in (cover.amount, cover.reason):
        m = pattern.search(text or "")
        if m:
            return _tidy(m.group(0))
    return None


def times_phrase(cover: CoverView) -> str | None:
    """가입금액에 곱하는 지급률의 원문 구절. 곱하기 표시는 ×로 맞춘다(기존 행과 같게)."""
    for text in (cover.amount, cover.reason):
        m = _TIMES_RE.search(text or "")
        if m:
            return "× " + _tidy(m.group(0)[1:])
    return None


_CLAUSE_CUT = re.compile(r"\n|※|(?:,\s*)?단\s*,")


def _clauses(text: str) -> list[str]:
    """글을 문장 조각으로 나눈다. 줄, "※", "단,"에서 가르고, 괄호 안의 글도 따로 한 조각으로 본다."""
    parts = [text] + [text[a + 1:b - 1] for a, b in T._groups(text)]
    out = []
    for part in parts:
        for piece in _CLAUSE_CUT.split(part):
            piece = re.sub(r"^\s*주\d*\)\s*", "", piece).strip(" ,.")
            # 짝이 맞지 않는 바깥 괄호를 뗀다
            while piece.endswith(")") and piece.count(")") > piece.count("("):
                piece = piece[:-1].rstrip()
            while piece.startswith("(") and piece.count("(") > piece.count(")"):
                piece = piece[1:].lstrip()
            if piece:
                out.append(piece)
    return out


def clause_with(word: str, places: Sequence[str], cover: CoverView, piece: PieceView | None,
                needs: re.Pattern) -> str | None:
    """word(빈칸 무시)와 needs가 함께 든 가장 짧은 문장 조각. places는 찾을 자리(지급사유, 지급금액, 주석)."""
    texts = {"지급사유": [cover.reason], "지급금액": [cover.amount], "주석": list(piece.notes) if piece else []}
    key = _word(word)
    found = [c for place in places for text in texts[place] for c in _clauses(text)
             if key and key in _word(c) and needs.search(_squash(c))]
    return _tidy(min(found, key=len)) if found else None


_EXCEPT_NEED = re.compile(r"감액|면책")
_TARGET_NEED = re.compile(r"\d+(?:\.\d+)?%|감액")


def exception_cell(v: Mapping[str, Any], cover: CoverView, piece: PieceView | None) -> tuple[str, list[str]]:
    """감액예외 칸의 원문 구절과, 찾지 못한 항목.

    감액이 일부 경우에만 걸리면(감액대상) 그 감액 문장을, 감액하지 않는 경우(감액예외)는 그 문장을 옮긴다.
    삼성화재 규칙(table_rules)이 일부 경우에만 걸리는 감액 문장을 감액예외 칸에 옮기는 것과 같다.
    """
    parts, missing = [], []
    if v.get("감액대상"):
        c = clause_with(v["감액대상"], ("지급금액", "지급사유"), cover, piece, _TARGET_NEED)
        (parts if c else missing).append(c or f"감액대상 {v['감액대상']}")
    for e in v.get("감액예외") or []:
        place = (e["자리"],) if e["자리"] != "주석" else ("주석",)
        c = clause_with(e["대상"], place, cover, piece, _EXCEPT_NEED)
        if c is None and e["자리"] != "주석":       # 자리를 잘못 적었어도 다른 칸에 있으면 찾는다
            c = clause_with(e["대상"], PLACES, cover, piece, _EXCEPT_NEED)
        (parts if c else missing).append(c or f"감액예외 {e['대상']}")
    return " / ".join(dict.fromkeys(p for p in parts if p)), missing


# ---------------------------------------------------------------------------
# 기계 검사
# ---------------------------------------------------------------------------

_PERCENT = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*%(?!\s*(?:이상|미만|초과|이하))")
_WAIT_DAYS = (re.compile(r"보장개시일[^※\n]{0,60}?(\d+)(일|개월|년)"), re.compile(r"(\d+)(일|개월|년)이(?:지난|경과)"))
_PAGE_REACH = 120           # 쪽 글자에서 보장개시일 이름 뒤로 날수를 찾는 거리. 표가 풀리며 옆 칸 글자가 끼어든다
# 감액을 가리키는 말(빈칸을 뗀 글에서). 계약일부터의 기간 뒤에 "이전, 미만, 이내"가 오고 30자 안에 비율이나 금액이 붙은 말,
# "N% 감액", "감액 지급", "경과시점 전일"(표가 풀려 "전일이"에서 끊긴 꼴도). "보험금지급기간」이내"나 "사고일로부터 180일
# 이내 치료"처럼 뒤에 비율이 붙지 않는 "이내", "15세 미만"처럼 기간이 아닌 "미만", "감액기간 없음"은 걸리지 않는다
_CUT_HINT = re.compile(r"\d+(?:년|개월|일)(?:경과[가-힣]{0,6}?시점)?(?:전일)?(?:이전|미만|이내)[^%]{0,30}?"
                       r"\d+(?:\.\d+)?(?:%|만원|원)|\d+(?:일|년)미만시|\d+(?:\.\d+)?%감액|감액지급|경과(?:암진단)?시점전일")
# 한도를 가리키는 말(빈칸을 뗀 글에서). "연간 총지급액 한도"처럼 돈의 한도는 수가 붙지 않아 걸리지 않는다
_LIMIT_HINT = re.compile(r"\d+회한|\d+회에한|\d+일(?:을)?한도|최초\d+회|(?:연간|월간)\d+(?:회|일)|\d+(?:회|일)까지")
# 한도가 줄 전체가 아니라 칸 안 표의 항목마다 걸리는 행없음사유. 한도 표시를 보지 않는다
_ITEM_TABLES = ("가입금액구간별금액표", "항목별금액표")


def _fmt(x: float) -> str:
    return f"{x:g}"


def _percent_in(value: float, texts: Sequence[str]) -> bool:
    pattern = re.compile(rf"(?<![\d.]){re.escape(_fmt(value))}\s*%")
    return any(pattern.search(t) for t in texts)


def _period_in(n: int, unit: str, texts: Sequence[str]) -> bool:
    pattern = re.compile(rf"(?<![\d.]){n}\s*{unit}")
    return any(pattern.search(t) for t in texts)


def _money_in(manwon: float, texts: Sequence[str]) -> bool:
    return any(re.search(B._spaced(f), t) for f in B.amount_forms(manwon) for t in texts)


_DEFINES = re.compile(r"\d+(?:일|개월|년)이?(?:지난|경과)|보장개시일[은는]")
_PARA_HEAD = re.compile(r"^\s*(?:[※▷▶◆■□●○·∙ㆍ•․*＊]|[-–]\s|주\s*\d*\))")
_NAMED_START = re.compile(r"[가-힣A-Za-z0-9)Ⅰ-Ⅻ]보장개시일(?![은는])")


def split_remarks(reason: str) -> tuple[str, str]:
    """지급사유를 (본문, 붙은 ※ 풀이)로 가른다.

    표 읽기(tables.py)는 특약 끝의 "※ 가나보장개시일은 … 90일이 지난 다음날" 같은 풀이 행을 그 특약의 모든 줄
    지급사유 끝에 붙인다. 그래서 면책이 없는 줄에도 날수 문장이 있다. 줄 첫머리가 "※"이고 날수나 보장개시일의 뜻을
    정하는 말("N일이 지난", "보장개시일은")이 든 문단을 풀이로 본다. 위첨자 ※가 줄 사이로 옮겨 온 "※보험기간 중 …"은
    뜻을 정하는 말이 없으므로 본문에 남는다.
    """
    paragraphs: list[tuple[bool, list[str]]] = []      # (※로 연 문단인가, 줄들)
    for line in (reason or "").split("\n"):
        if line.lstrip().startswith("※"):
            paragraphs.append((True, [line]))
        elif paragraphs and paragraphs[-1][0] and line.strip() and not _PARA_HEAD.match(line):
            paragraphs[-1][1].append(line)              # 풀이 문단이 줄을 바꿔 이어진다
        else:
            paragraphs.append((False, [line]))
    body, notes = [], []
    for marked, lines in paragraphs:
        text = "\n".join(lines)
        (notes if marked and _DEFINES.search(_squash(text)) else body).append(text)
    return "\n".join(body).strip(), "\n".join(notes).strip()


def points_to_start(cover: CoverView) -> bool:
    """지급사유 본문(붙은 ※ 풀이를 뺀 글)이 보장개시일을 가리키는가."""
    return "보장개시일" in _squash(split_remarks(cover.reason)[0])


def points_to_named_start(cover: CoverView) -> bool:
    """지급사유 본문이 이름이 붙은 보장개시일(가나보장개시일)을 가리키는가. 이름 없는 "보장개시일 이후"는 계약일이다."""
    return bool(_NAMED_START.search(split_remarks(cover.reason)[0]))


def _days_found(flat: str) -> set[int]:
    return {T._days(int(n), unit) for p in _WAIT_DAYS for n, unit in p.findall(flat)}


def wait_days_in(cover: CoverView, piece: PieceView | None) -> set[int]:
    """그 세부보장의 글자와 그 특약의 주석에 보장개시일 날수로 적힌 수.

    지급사유 끝에 붙은 ※ 풀이(split_remarks)는 본문이 보장개시일을 가리킬 때만 그 줄의 근거로 센다.
    """
    body, remarks = split_remarks(cover.reason)
    parts = [body, cover.amount] + (list(piece.notes) if piece is not None else [])
    if remarks and points_to_start(cover):
        parts.append(remarks)
    return _days_found(_squash("\n".join(p for p in parts if p)))


_LIST_ITEM = 60             # 보장개시일 이름 나열에서 이름 하나의 길이 한도


def _boundary(flat: str, start: int, spaced: bool = False) -> bool:
    """flat[start:]에서 시작하는 이름이 다른 이름의 꼬리가 아닌가("유사암보장개시일" 속의 "암보장개시일"이 아닌가).

    spaced: 원문에서 이름 바로 앞이 빈칸이나 줄바꿈인가. 문장이 끝난 뒤("…합니다 가나보장개시일은")면 경계로 본다.
    """
    if start == 0 or flat.endswith(("및", "보장개시일과", "보장개시일와"), 0, start):
        return True
    if spaced and flat.endswith(("다", "다.", "음", "함"), 0, start):
        return True
    return not re.match(r"[가-힣A-Za-z0-9Ⅰ-Ⅻ(]", flat[start - 1])


def _flat_map(text: str) -> tuple[str, list[int]]:
    """빈칸을 뗀 글과, 그 글자마다 원문에서의 자리."""
    pos = [i for i, ch in enumerate(text) if not ch.isspace()]
    return "".join(text[i] for i in pos), pos


_CASE = re.compile(r"의경우.{0,20}?보장개시일[은는]")     # 나열 끝 이름 뒤의 "의 경우 (짧은 말) 보장개시일은"


def _listed_days(flat: str, end: int) -> int | None:
    """flat[end:]가 이름 나열의 나머지(", 나보장개시일 및 다보장개시일")와 "은/는"이면, 그 뒤에 처음 나오는 날수.

    나열이 "의 경우"와 짧은 말 뒤의 "보장개시일은 … N일"로 이어지면 나열의 마지막 이름(뒤에 쉼표나 "및"이 없는 이름) 바로
    뒤가 "의 경우"이므로, 그 꼴도 받는다.
    """
    tail = flat[end:end + 2000]
    case = _CASE.match(tail)
    if tail[:1] in ("은", "는"):
        stop = 1
    elif case:
        stop = case.end()
    else:
        if not tail.startswith((",", "및", "과", "와")):
            return None
        m = re.search(r"보장개시일[은는]", tail)
        if m is None:
            return None
        items = tail[1:m.end() - 1].split(",")
        if not all(x.endswith("보장개시일") and len(x) <= _LIST_ITEM for x in items):
            return None
        stop = m.end()
    m = re.search(r"(?<!\d)(\d+)(일|개월|년)", tail[stop:stop + _PAGE_REACH])
    return T._days(int(m.group(1)), m.group(2)) if m else None


def wait_days_on_page(names: str | Sequence[str], page_text: str) -> set[int]:
    """쪽 글자에서 이름과 짝지어 적힌 날수. 이름이 없으면 빈 집합.

    메리츠화재 요약서는 보장개시일의 날수를 표 밖(쪽 아래 ※ 줄, 다른 쪽)에 적기도 해서 조각에 없을 수 있다.
    판독자가 적은 면책근거쪽의 글자에서 세 가지 꼴을 본다.
    - 정의 문장: "<보장개시일 이름>은 … N일이 지난 다음날"
    - 나열 문장: "가보장개시일, 나보장개시일 및 다보장개시일은 … 90일 …, 라보장개시일은 … 1년 …". 이름마다 그 이름이 든
      나열의 "은/는" 뒤에 처음 나오는 날수와 짝짓는다. "유사암보장개시일" 속의 "암보장개시일"은 세지 않는다.
      나열 끝 이름 뒤가 "은/는"이 아니라 "의 경우"이고 짧은 말 뒤에 "보장개시일은 … N일"이 오는 나열도 같다
      ("가보장개시일 및 나보장개시일의 경우 그 보장개시일은 … 90일").
    - 표: 면책기간 표의 "<보장명> 90일"처럼 이름 바로 옆 칸에 날수가 있다(글자로 풀면 이름 바로 뒤). 표의 칸은 글자로
      풀면 앞 칸에 붙으므로, 원문에서 이름 앞이 빈칸이나 줄바꿈이면 경계로 본다.
    names에는 보장개시일 이름과 세부보장명, 특약명을 준다.
    """
    text = page_text or ""
    flat, pos = _flat_map(text)
    out: set[int] = set()
    for name in ([names] if isinstance(names, str) else names):
        key = _squash(_word(name))
        if len(key) < 3:
            continue
        for m in re.finditer(re.escape(key), flat):
            spaced = m.start() > 0 and text[pos[m.start()] - 1].isspace()
            if _boundary(flat, m.start(), spaced):
                listed = _listed_days(flat, m.end())
                if listed is not None:
                    out.add(listed)
                    continue
            if not (m.start() == 0 or spaced or _boundary(flat, m.start())):
                continue
            beside = re.match(r"(\d+)(일|개월|년)(?!\d)", flat[m.end():])
            if beside and not flat[m.end() + beside.end():].startswith(("이", "경과", "미만", "이내", "전", "후")):
                out.add(T._days(int(beside.group(1)), beside.group(2)))
    return out


def leftovers(v: Mapping[str, Any], cover: CoverView) -> list[str]:
    """지급금액 칸에 적힌 비율과 금액 가운데 판독이 쓰지 않은 것. "80%이상"처럼 조건으로 쓴 수는 뺀다.

    지급사유 칸은 보지 않는다. 진단 기준 수치(당화혈색소 7.0%)처럼 지급액이 아닌 수가 적힌다.
    """
    used_pct = set()
    if _num(v.get("지급률")):
        used_pct.add(float(v["지급률"]))
    used_money = set()
    for name in ("지급액만원", "기준가입금액만원"):
        if _num(v.get(name)):
            used_money.add(float(v[name]))
    for c in v.get("감액") or []:
        (used_money if c["값기준"] == "만원" else used_pct).add(float(c["값"]))
        if c["값기준"] == "보험금":
            used_pct.add(100 - float(c["값"]))       # "50% 감액"처럼 덜 주는 몫으로 적은 경우
    out = []
    for text in (cover.amount,):
        for m in _PERCENT.finditer(text or ""):
            value = float(m.group(1))
            if value not in used_pct:
                out.append(f"{_fmt(value)}%")
        flat = B.squash(text or "")
        for m, value in B._amounts(flat):
            after = flat[m.end():m.end() + 2]
            if value and value not in used_money and not after.startswith(("미만", "이상", "초과", "이하")):
                out.append(f"{_fmt(value)}만원")
    return list(dict.fromkeys(out))


_LIMIT_AFTER = re.compile(r"\s*\d+\s*(?:일|회)")      # "1회 입원당 180일"의 "1회 입원당"은 지급단위가 아니라 한도 앞말이다


def amount_unit(cover: CoverView) -> str | None:
    """지급금액 칸에 적힌 지급단위. 하나만 적혀 있을 때만 돌려준다. 없거나 둘 이상이면 None.

    지급단위는 지급금액 칸을 따르고, 그 칸에 단위가 없을 때만 지급사유 칸의 "1회당", "1일당"을 따른다.
    """
    found = set()
    for unit in UNITS[1:]:
        for m in re.finditer(_UNIT_RE[unit], cover.amount or ""):
            if not _LIMIT_AFTER.match(cover.amount[m.end():]):
                found.add(unit)
    return found.pop() if len(found) == 1 else None


def _check_numbers(cover: CoverView, v: Mapping[str, Any], piece: PieceView | None, unknown: set[str],
                   problems: list[str], marks: list[str]) -> None:
    """지급률, 금액, 감액의 숫자가 그 세부보장의 글자에 있는가(숫자 경계까지)와 범위."""
    form = v.get("꼴")
    texts = [cover.amount, cover.reason]
    rate = v.get("지급률")
    if form == RATIO and _num(rate) and "지급률" not in unknown:
        bare = re.search(r"가입금액", _squash(cover.amount + cover.reason))
        if not (_percent_in(rate, texts) or (rate == 100 and bare)):
            problems.append(f"숫자없음: 지급률 {_fmt(rate)}%")
    if form == AMOUNT:
        for name in ("지급액만원", "기준가입금액만원"):
            if _num(v.get(name)) and name not in unknown and not _money_in(float(v[name]), _texts(cover, piece)):
                problems.append(f"숫자없음: {name} {_fmt(v[name])}")
    if "감액" not in unknown:
        for c in v.get("감액") or []:
            if not _period_in(c["기간"], c["단위"], texts):
                problems.append(f"숫자없음: 감액 기간 {c['기간']}{c['단위']}")
            ok = _money_in(float(c["값"]), texts) if c["값기준"] == "만원" else _percent_in(float(c["값"]), texts)
            if not ok and c["값기준"] == "보험금":      # "75% 감액 지급"은 보험금의 25%를 받는다
                ok = any(re.search(rf"(?<![\d.]){re.escape(_fmt(100 - float(c['값'])))}\s*%\s*감액", t) for t in texts)
            if not ok:
                problems.append(f"숫자없음: 감액 값 {_fmt(c['값'])}{'만원' if c['값기준'] == '만원' else '%'}")
        steps = cut_steps(v)
        if steps is None:
            problems.append("범위: 감액 비율을 계산할 수 없음")
        else:
            for (months, r), c in zip(steps, sorted(v.get("감액") or [], key=lambda c: T._months(c["기간"], c["단위"])[0])):
                if not 0 < r < 1:
                    problems.append(f"범위: 감액 비율 {r:g}가 0과 1 사이가 아님")
                if not T._months(c["기간"], c["단위"])[1]:
                    problems.append(f"범위: 감액 기간 {c['기간']}{c['단위']}이 개월로 떨어지지 않음")
                if not 1 <= months <= 60:
                    problems.append(f"범위: 감액 기간 {months}개월")
            if len(steps) == 2 and not (steps[0][0] < steps[1][0] and steps[0][1] <= steps[1][1]):
                problems.append("범위: 두 감액 구간의 기간이 겹치거나 짧은 기간의 비율이 더 큼")
    if form == RATIO and _num(rate) and not 0 < rate <= 1000:
        problems.append(f"범위: 지급률 {_fmt(rate)}")


def _check_wait(cover: CoverView, v: Mapping[str, Any], piece: PieceView | None, unknown: set[str],
                pages: Mapping[int, str] | None, problems: list[str], marks: list[str]) -> None:
    """면책 일수의 근거: 그 세부보장의 글자와 그 특약의 주석, 없으면 판독자가 적은 면책근거쪽의 쪽 글자.

    지급사유 끝에 붙은 ※ 풀이는 그 줄의 근거로 보지 않는다. 그 줄에 면책이 걸리는지는 지급사유 본문이 보장개시일을
    가리키는지로 본다(split_remarks).
    """
    days = v.get("면책일수", 0)
    page = (pages or {}).get(v.get("면책근거쪽")) if v.get("면책근거쪽") is not None else None
    if "면책일수" not in unknown:
        written = wait_days_in(cover, piece)
        if days and days not in written:
            if page is None:
                where = "조각과 주석에 없고 면책근거쪽이 없음" if v.get("면책근거쪽") is None else \
                    "조각과 주석에 없고 면책근거쪽의 글자가 없음"
                problems.append(f"숫자없음: 면책일수 {days} ({where})")
            else:
                names = [v.get("보장개시일", ""), cover.name] + ([piece.title, *piece.names] if piece else [])
                if days not in wait_days_on_page([n for n in names if n], page):
                    problems.append(f"숫자없음: 면책일수 {days} ({v['면책근거쪽']}쪽에 그 이름의 날수로 없음)")
        if days > 1095:
            problems.append(f"범위: 면책일수 {days}")
        if not days and "감액및면책기간미적용" not in _squash(cover.name):
            body_days = _days_found(_squash(split_remarks(cover.reason)[0]))
            if points_to_named_start(cover) or body_days:
                shown = f" ({', '.join(map(str, sorted(written)))}일)" if written else ""
                marks.append(f"지급사유 본문이 보장개시일을 가리키는데 면책일수가 0{shown}")
            elif _NAMED_START.search(cover.amount or ""):
                marks.append("지급금액 칸이 이름이 붙은 보장개시일을 가리키는데 면책일수가 0")
    if v.get("보장개시일") and "보장개시일" not in unknown:
        here = _word("\n".join(_texts(cover, piece))) + _word(page or "")
        if _word(v["보장개시일"]) not in here:
            problems.append("낱말없음: 보장개시일")


def _check_limits(cover: CoverView, v: Mapping[str, Any], piece: PieceView | None, unknown: set[str],
                  problems: list[str]) -> None:
    if "한도" not in unknown:
        for x in v.get("한도") or []:
            if limit_phrase(x, cover, piece) is None:
                problems.append(f"구절없음: 한도 {x['앞말']} {x['수']}{x['단위']}")


MISSED, NAME_MARK = "빠진 값", "이름 표식"


def _check_missed(cover: CoverView, v: Mapping[str, Any], unknown: set[str], marks: list[str]) -> None:
    """함께 빠뜨린 값: 그 줄의 글자(지급사유 본문과 지급금액 칸)에 감액이나 한도를 가리키는 말이 있는데 그 칸이 빈 줄.

    두 판독이 같은 방식으로 빠뜨리면 견줌으로는 잡히지 않는다. 지급사유 끝에 붙은 ※ 풀이(split_remarks)는 그 특약의
    모든 줄에 붙으므로 보지 않는다. 감액은 행을 만드는 꼴(가입금액비율, 금액)만, 한도는 행없음 줄도 보되 칸 안 표의
    항목마다 한도가 걸리는 행없음(_ITEM_TABLES)은 보지 않는다. 보장개시일을 가리키는데 면책일수가 0인 줄은 _check_wait가 낸다.
    표시에는 원문 구절을 싣지 않는다(값 파일에 들어간다).
    """
    flat = _squash(split_remarks(cover.reason)[0]) + "\n" + _squash(cover.amount)
    form = v.get("꼴")
    if form in (RATIO, AMOUNT) and "감액" not in unknown and not v.get("감액") and _CUT_HINT.search(flat):
        marks.append(f"{MISSED}: 감액을 가리키는 말이 있는데 감액이 비어 있음")
    if "한도" not in unknown and not v.get("한도") and _LIMIT_HINT.search(flat) \
            and not (form == NO_ROW and v.get("행없음사유") in _ITEM_TABLES):
        marks.append(f"{MISSED}: 한도를 가리키는 말이 있는데 한도가 비어 있음")


_NAME_LIMIT = re.compile(r"(연간|최초)(\d+)회한")
_NAME_DAYS = re.compile(r"(?<!\d)(\d+)일한도")
_NAME_NO_CUT = re.compile(r"감액(?:및면책)?기간미적용|감액없음")
_NAME_NO_WAIT = re.compile(r"면책기간미적용")


def name_marks(piece: PieceView | None, cover: CoverView) -> dict[str, Any]:
    """특약명과 세부보장명(빈칸 무시)에 적힌 표식. 한도(앞말, 수, 단위), 일수 한도, 감액 없음, 면책 없음, 일당.

    세부보장명과 그 조각의 특약명을 함께 본다. 본형, 갱신형 이름을 "/"로 이은 이름에서 같은 표식이 두 번 나와도 한 번만 센다.
    """
    text = "\n".join(dict.fromkeys(_squash(n) for n in (cover.name, *((piece.title,) if piece else ())) if n))
    return {
        "한도": sorted({(m.group(1), int(m.group(2)), "회") for m in _NAME_LIMIT.finditer(text)}),
        "일수한도": sorted({int(m.group(1)) for m in _NAME_DAYS.finditer(text)}),
        "감액없음": bool(_NAME_NO_CUT.search(text)),
        "면책없음": bool(_NAME_NO_WAIT.search(text)),
        "일당": "일당" in text,
    }


def _check_name_marks(cover: CoverView, v: Mapping[str, Any], piece: PieceView | None, unknown: set[str],
                      marks: list[str]) -> None:
    """이름의 표식과 판독 값의 모순. 이름에 "연간N회한", "최초1회한", "N일한도"가 있는데 한도에 그 항목이 없거나,
    "감액기간미적용", "감액및면책기간미적용", "감액없음"이 있는데 감액이 있거나, "면책기간미적용"이 있는데 면책일수가 있거나,
    "일당"이 있는데 지급단위가 비어 있는(한 번에 주는 돈) 줄.

    일당 이름에 1회당 같은 다른 지급단위를 적은 줄은 걸지 않는다. 통원일당이 "통원 1회당"으로 주는 것처럼 칸에 그 단위가
    적혀 있고, 그 구절이 칸에 있는지는 지급단위 구절 검사가 본다. 감액과 지급단위는 행을 만드는 꼴만 본다.
    """
    marked = name_marks(piece, cover)
    form = v.get("꼴")
    if "한도" not in unknown:
        limits = {(x["앞말"], x["수"], x["단위"]) for x in v.get("한도") or []}
        for lead, n, unit in marked["한도"]:
            if (lead, n, unit) not in limits:
                marks.append(f"{NAME_MARK}: 이름에 {lead} {n}{unit} 한도가 있는데 한도에 없음")
        for n in marked["일수한도"]:
            if not any(x[1] == n and x[2] == "일" for x in limits):
                marks.append(f"{NAME_MARK}: 이름에 {n}일 한도가 있는데 한도에 없음")
    rows = form in (RATIO, AMOUNT)
    if rows and marked["감액없음"] and v.get("감액") and "감액" not in unknown:
        marks.append(f"{NAME_MARK}: 이름에 감액 미적용이 있는데 감액이 있음")
    if marked["면책없음"] and v.get("면책일수") and "면책일수" not in unknown:
        marks.append(f"{NAME_MARK}: 이름에 면책기간 미적용이 있는데 면책일수가 있음")
    if rows and marked["일당"] and not v.get("지급단위") and "지급단위" not in unknown:
        marks.append(f"{NAME_MARK}: 이름에 일당이 있는데 지급단위가 비어 있음")


def machine_checks(cover: CoverView, v: Mapping[str, Any], piece: PieceView | None = None,
                   pages: Mapping[int, str] | None = None) -> tuple[list[str], list[str]]:
    """(문제, 표시). 문제는 원문에 근거가 없거나 범위를 벗어난 값, 표시는 판독이 쓰지 않은 숫자처럼 사람이 볼 곳.

    두 판독이 같은 방식으로 틀리는 것을 잡으려는 검사다. 값이 같아도 문제나 표시가 있으면 확정하지 않는다.
    pages: {쪽 번호: 쪽 글자}. 주면 조각에 없는 면책 날수를 판독 값의 면책근거쪽 글자에서 찾는다.
    행없음 줄은 행을 만들지 않아도 남기는 칸(면책일수, 보장개시일, 한도)만 본다.
    """
    problems: list[str] = []
    marks: list[str] = []
    form = v.get("꼴")
    if form == UNKNOWN:
        return problems, marks
    unknown = _unknown_fields(v)
    if form == NO_ROW:
        _check_wait(cover, v, piece, unknown, pages, problems, marks)
        _check_limits(cover, v, piece, unknown, problems)
        _check_missed(cover, v, unknown, marks)
        _check_name_marks(cover, v, piece, unknown, marks)
        return problems, marks
    _check_numbers(cover, v, piece, unknown, problems, marks)
    _check_wait(cover, v, piece, unknown, pages, problems, marks)
    _check_limits(cover, v, piece, unknown, problems)
    _check_missed(cover, v, unknown, marks)
    _check_name_marks(cover, v, piece, unknown, marks)
    # 대상 낱말이 그 줄의 글자에 있는가(급부ID 다듬기 기준으로)
    if v.get("대상") and "대상" not in unknown:
        here = target_key(f"{cover.reason}\n{cover.amount}\n{cover.name}")
        if target_key(v["대상"]) not in here:
            problems.append("낱말없음: 대상")
    # 구절을 잘라 쓸 수 있는가
    if "지급단위" not in unknown:
        if unit_phrase(v.get("지급단위", ""), cover) is None:
            problems.append(f"구절없음: 지급단위 {v['지급단위']}")
        expected = amount_unit(cover)
        if expected and v.get("지급단위", "") != expected:
            marks.append(f"지급단위: 지급금액 칸의 단위는 {expected}")
    if v.get("지급률곱") and "지급률곱" not in unknown and times_phrase(cover) is None:
        problems.append("구절없음: 지급률곱")
    if not v.get("지급률곱") and _TIMES_RE.search(cover.amount or ""):
        marks.append("지급금액 칸에 지급률을 곱하는 표시가 있는데 지급률곱이 거짓")
    if "감액대상" not in unknown and "감액예외" not in unknown:
        _, missing = exception_cell(v, cover, piece)
        problems += [f"구절없음: {m}" for m in missing]
    # 판독이 쓰지 않은 숫자(지급금액 칸만)
    left = leftovers(v, cover)
    if left:
        marks.append(f"남은 숫자: {', '.join(left)}")
    return problems, marks


def same_name_groups(piece: PieceView) -> list[list[CoverView]]:
    """한 조각 안에서 이름(빈칸 무시)이 같은 세부보장 묶음. 둘 이상인 것만."""
    groups: dict[str, list[CoverView]] = {}
    for c in piece.covers:
        groups.setdefault(_squash(c.name), []).append(c)
    return [g for g in groups.values() if len(g) > 1]


def unresolved_targets(covers: Sequence[CoverView], readings: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """이름이 같은 줄 가운데 대상으로 서로 가려지지 않는 줄의 번호. 대상이 비었거나 다른 줄과 열쇠가 같다.

    판독이 없는 줄은 세지 않는다(따로 판독 없음으로 잡힌다).
    """
    keys = {c.number: target_key((readings.get(c.number) or {}).get("대상") or "") for c in covers
            if readings.get(c.number) is not None}
    count = Counter(keys.values())
    return [n for n, k in keys.items() if not k or count[k] > 1]


def same_name_splits(pieces: Iterable[PieceView], readings: Mapping[str, Mapping[str, Any]]) -> dict[str, list[str]]:
    """같은 조각 안에서 이름이 같은 세부보장이 서로 다른 값으로 갈리는 묶음. {조각번호/이름: [번호들]}.

    대상이 서로 다른 줄은 급부명이 "세부보장명(대상)"으로 갈리므로 갈림으로 세지 않는다. 대상으로 가려지지 않는 줄
    (unresolved_targets)끼리 값이 다를 때만 갈림이다.
    """
    out = {}
    for p in pieces:
        for covers in same_name_groups(p):
            values = [readings.get(c.number) for c in covers]
            if any(x is None for x in values):
                continue
            loose = set(unresolved_targets(covers, readings))
            rest = [readings[c.number] for c in covers if c.number in loose]
            if len({repr(sorted({k: x for k, x in normalized(v).items() if k != "대상"}.items())) for v in rest}) > 1:
                out[f"{p.number}/{covers[0].name}"] = [c.number for c in covers if c.number in loose]
    return out


def same_name_unlabeled(pieces: Iterable[PieceView], readings: Mapping[str, Mapping[str, Any]]) -> dict[str, list[str]]:
    """이름이 같은 세부보장이 있는데 대상이 비었거나 서로 같은 줄. {조각번호/이름: [번호들]}. 판정필요로 둔다."""
    out = {}
    for p in pieces:
        for covers in same_name_groups(p):
            loose = unresolved_targets(covers, readings)
            if loose:
                out[f"{p.number}/{covers[0].name}"] = loose
    return out


# ---------------------------------------------------------------------------
# 형과 종형 잇기
# ---------------------------------------------------------------------------

def variants_for(segment: str, variant_names: Sequence[str], common: str = "공통") -> list[str]:
    """조각의 형에 드는 종형 이름들.

    형 구간이 없는 문서(segment "")와 "공통" 조각은 그 요약서를 쓰는 모든 종형에 든다. 형이 적힌 조각은 종형명이
    그 형으로 시작하는 종형에만 든다(대상 설정의 종형명은 사업방법서 세목 표의 형 표기를 앞에 둔다. 예:
    "통합간편심사형 2형(…) 1종(…) 315간편심사형"은 "통합간편심사형" 조각을 쓴다).
    """
    if not segment or segment == common:
        return list(variant_names)
    key = _squash(segment)
    return [n for n in variant_names if _squash(n).startswith(key)]


# ---------------------------------------------------------------------------
# 판독 값에서 시트 행 만들기
# ---------------------------------------------------------------------------

_RENEWAL = re.compile(r"\[갱신형\]|(?<!비)갱신형")


def is_renewal(name: str) -> bool:
    """특약 이름에 갱신형 표시가 있는가. 삼성화재는 "[갱신형]", 메리츠화재는 "갱신형 …"으로 적는다."""
    return bool(_RENEWAL.search(_squash(name)))


@dataclass
class Built:
    riders: list[dict[str, Any]] = field(default_factory=list)
    benefits: list[dict[str, Any]] = field(default_factory=list)
    numbers: dict[str, tuple[str, ...]] = field(default_factory=dict)   # 급부ID → 번호들
    skipped: dict[str, str] = field(default_factory=dict)              # 번호 → 행을 만들지 않은 사유
    skipped_riders: dict[str, str] = field(default_factory=dict)       # 특약명 → 특약 행(과 그 급부 행)을 만들지 않은 사유
    no_rows: dict[str, dict[str, Any]] = field(default_factory=dict)   # 행없음 줄 번호 → 남기는 정보(사유, 면책, 한도 구절)
    notes: list[str] = field(default_factory=list)


def reading_of(v: Mapping[str, Any], cover: CoverView, piece: PieceView | None, name: str,
               target: str = "") -> T.Reading:
    """판독 값을 table_rules.Reading으로 바꾼다. 한도와 감액예외는 원문 구절로 채운다.

    target을 주면 급부명이 table_rules와 같이 "이름(대상)"이 된다(Reading.label).
    """
    steps = tuple(T.Step(m, r) for m, r in (cut_steps(v) or ()))
    parts = [unit_phrase(v.get("지급단위", ""), cover) or ""]
    if v.get("지급률곱"):
        parts.append(times_phrase(cover) or "")
    parts += [limit_phrase(x, cover, piece) or "" for x in v.get("한도") or []]
    exception, _ = exception_cell(v, cover, piece)
    return T.Reading(
        name=name,
        target=target_text(target),
        percent=float(v["지급률"]) if v.get("꼴") == RATIO else 100.0,
        steps=steps,
        waiting_days=int(v.get("면책일수") or 0),
        limit=" / ".join(dict.fromkeys(p for p in parts if p)),
        exception=exception if steps else "",
    )


HOLD = "보류"
# 이름 칸에 든 지급사유 문장의 표시. 세부보장명에는 나오지 않는 말이다
_SENTENCE_NAME = re.compile(r"지급|경우|되고|되었|확정시|로써|한하여")
_QUOTED = re.compile(r"「([^」]{2,40})」")
_DIAGNOSED = re.compile(r"(?:으로|로)\s*진단\s*확정")
_SUBJECT_HEAD = re.compile(r"(?:에|중|후|「|」|※|·)\s*")
_TAG = re.compile(r"\([^()]*\)")


def _reason_subjects(reason: str) -> list[tuple[str, int]]:
    """지급사유의 대상 낱말과 그 줄 번호. 「」 안의 말과 "…(으)로 진단확정"의 앞말(바로 앞의 "에", "중", "후" 뒤)."""
    out = []
    for k, line in enumerate((reason or "").split("\n")):
        out += [(_word(m.group(1)), k) for m in _QUOTED.finditer(line)]
        for m in _DIAGNOSED.finditer(line):
            head = line[:m.start()]
            if head.endswith("」"):
                continue
            word = _word(_SUBJECT_HEAD.split(head)[-1])
            if 2 <= len(word) <= 40:
                out.append((word, k))
    return out


def _subjects_in(part: str, reason: str) -> tuple[int, int]:
    """part(빈칸 뗀 이름)에 겹치지 않게 든 지급사유 대상 낱말의 수와, 그 낱말이 나온 지급사유 줄의 수. 긴 낱말부터 잡는다."""
    taken = [False] * len(part)
    found, lines = 0, set()
    for word, line in sorted(set(_reason_subjects(reason)), key=lambda x: -len(x[0])):
        at = part.find(word)
        while at >= 0 and any(taken[at:at + len(word)]):
            at = part.find(word, at + 1)
        if at >= 0:
            taken[at:at + len(word)] = [True] * len(word)
            found += 1
            lines.add(line)
    return found, len(lines)


def _glued_tag(part: str) -> str | None:
    """같은 괄호 꼬리표("(체증형)")가 두 번 이상 나오고, 그 가운데 하나 바로 뒤에 빈칸 없이 다른 이름이 이어지는가."""
    ends: dict[str, list[int]] = {}
    for m in _TAG.finditer(part):
        ends.setdefault(m.group(0), []).append(m.end())
    for tag, at in ends.items():
        if len(at) > 1 and any(e < len(part) and not part[e].isspace() and part[e] not in "([/" for e in at):
            return tag
    return None


def name_problem(cover: CoverView) -> str:
    """조각의 세부보장명으로 급부 행을 만들면 안 되는 사유. 괜찮으면 빈 글.

    급부ID는 이 이름으로 만들어 뒤에 고칠 수 없다(hum_담보매핑이 급부ID로 이어진다). 표 읽기가 이름을 잘못 낸 줄은 행을
    만들지 않고 보류로 남긴다. 조각 글자만 보고 정하므로 같은 문서를 다시 읽으면 같은 줄이 걸린다.
    - 이름 칸에 지급사유 문장: 이름에 "지급", "경우", "확정시" 같은 문장의 말이 있다(표 읽기에서 칸이 뒤바뀐 줄).
    - 이름 여럿이 이어 붙음: 칸 안의 여러 줄(세부보장 여럿)을 표 읽기가 한 줄로 합친 이름. "/"로 가른 이름 토막마다 본다.
      ① 지급사유의 대상 낱말(「」 안의 말, "…(으)로 진단확정"의 앞말) 둘 이상이 겹치지 않게 이름에 들어 있고, 그 낱말들이
      지급사유의 서로 다른 줄에서 나왔다(세부보장마다 지급사유 문단이 따로 있다).
      ② 같은 괄호 꼬리표가 두 번 이상 나오고 그중 하나 바로 뒤에 빈칸 없이 다른 이름이 이어진다("가암(체증형)나암(체증형)").
    """
    if _SENTENCE_NAME.search(cover.name or ""):
        return f"{HOLD}: 이름 칸에 지급사유 문장이 들어 있음(표 읽기에서 칸이 뒤바뀜)"
    for part in (cover.name or "").split("/"):
        found, lines = _subjects_in(_word(part), cover.reason)
        if (found >= 2 and lines >= 2) or _glued_tag(part):
            return f"{HOLD}: 세부보장 이름 여럿이 한 줄에 이어 붙음(표 읽기에서 칸 안의 줄이 합쳐짐)"
    return ""


def row_problem(v: Mapping[str, Any] | None, cover: CoverView, piece: PieceView,
                pages: Mapping[int, str] | None = None) -> str:
    """이 판독 값으로 행을 만들 수 없는 사유. 만들 수 있으면 빈 글."""
    if v is None:
        return "판독 값 없음"
    form = v.get("꼴")
    if form == NO_ROW:
        return f"스키마가 담지 못하는 꼴: {v.get('행없음사유')}"
    if form == UNKNOWN:
        return "모름"
    unknown = _unknown_fields(v)
    if unknown:
        return f"모름인 칸: {', '.join(sorted(unknown))}"
    if check_format(v):
        return "판독 값의 꼴이 틀림"
    problems, _ = machine_checks(cover, v, piece, pages)
    if problems:
        return f"기계 검사: {'; '.join(problems)}"
    return ""


def no_row_info(v: Mapping[str, Any], cover: CoverView, piece: PieceView | None) -> dict[str, Any]:
    """행없음 줄에서도 남기는 정보: 사유, 면책일수, 보장개시일, 한도(원문 구절)."""
    unknown = _unknown_fields(v)
    out: dict[str, Any] = {"행없음사유": v.get("행없음사유") or ""}
    for name in ("면책일수", "보장개시일"):
        out[name] = None if name in unknown else v.get(name)
    out["한도"] = None if "한도" in unknown else \
        [limit_phrase(x, cover, piece) or f"{x['앞말']} {x['수']}{x['단위']}" for x in v.get("한도") or []]
    return out


RenewalYears = int | Mapping[str, int] | None


def years_for(name: str, renewal_years: RenewalYears) -> int | None:
    """그 특약의 갱신주기년. renewal_years는 모든 갱신형 특약에 같은 값(정수)이나 {특약명: 값}(빈칸 무시로 찾는다)."""
    if renewal_years is None or isinstance(renewal_years, int):
        return renewal_years
    if name in renewal_years:
        return renewal_years[name]
    keyed = {_squash(k): x for k, x in renewal_years.items()}
    return keyed.get(_squash(name))


def build_rows(variant_id: str, pieces: Sequence[PieceView], readings: Mapping[str, Mapping[str, Any]],
               renewal_years: RenewalYears = None, pages: Mapping[int, str] | None = None) -> Built:
    """판정이 끝난 판독 값(번호 → 값)으로 sys_특약, sys_급부 행을 만든다.

    - 특약 행: 조각의 특약명들마다 하나(table_rules.build_rows와 같다). 같은 이름이 또 나오면 table_rules.id_name이
      "(선택계약)" 같은 구분을 붙인 이름으로 ID를 만든다. 담보구분은 구분이 기본계약이면 주계약이다.
    - 갱신형 특약: 이름에 갱신형 표시가 있으면 갱신여부를 참으로 하고 renewal_years(사람이 정한 값. 정수 하나나
      {특약명: 값})의 주기를 적는다. 그 특약의 주기가 없으면 특약 행과 그 급부 행을 만들지 않고 skipped_riders에 사유를
      남기고 notes에 수를 센다. 이름은 ID를 만들 이름 목록(id_name)에 그대로 넣어, 나중에 주기를 주어 다시 만들어도
      다른 특약의 ID가 바뀌지 않는다.
    - 급부 행: 가입금액비율은 table_rules.benefit_row(가입금액 100만원당 지급률), 금액은 그 행의 기준가입금액,
      기준지급금액, 지급기준구분을 판독 값으로 바꾼다. 급부ID 규칙은 table_rules와 같다(ids.benefit_id).
      이름이 여럿인 조각에 세부보장이 하나면 급부 이름을 특약 이름으로 바꿔 적는다(table_rules와 같다).
    - 행을 만들 수 없는 줄(행없음, 모름, 기계 검사에 걸린 줄)은 skipped에 사유를 남긴다. 행없음 줄은 no_rows에
      면책일수, 보장개시일, 한도 구절을 남긴다. 표 읽기가 이름을 잘못 낸 줄(name_problem)은 판독 값과 상관없이 "보류"로 남긴다.
    - 한 조각 안에 이름이 같은 세부보장이 여럿이면, 대상이 모두 있고 서로 다를 때 줄마다 "세부보장명(대상)"으로 급부
      행을 만든다(table_rules의 원시급부명 규칙). 대상으로 가려지지 않으면 삼성화재 적재(job._drop_repeats)처럼 행이
      글자까지 같을 때만 하나를 남기고 번호를 모두 단다. 값이 다르거나 그중 하나라도 행을 만들 수 없으면 그 이름의
      줄은 모두 행을 만들지 않는다.
    """
    out = Built()
    taken: set[str] = set()
    lost = 0                    # 갱신주기년이 없어 뺀 특약에 걸린 세부보장 줄 수(특약마다 센다)
    for piece in pieces:
        names = piece.names or (piece.title,)
        role = "주급부" if len(piece.covers) == 1 else "대등복합"
        problems = {c.number: name_problem(c) or row_problem(readings.get(c.number), c, piece, pages)
                    for c in piece.covers}
        for c in piece.covers:
            if problems[c.number]:
                out.skipped[c.number] = problems[c.number]
            v = readings.get(c.number)
            if v is not None and v.get("꼴") == NO_ROW:
                out.no_rows[c.number] = no_row_info(v, c, piece)
        groups: dict[str, list[CoverView]] = {}
        for c in piece.covers:
            groups.setdefault(_squash(c.name), []).append(c)
        labelled = {key: len(covers) > 1 and not unresolved_targets(covers, readings)
                    for key, covers in groups.items()}
        for name in names:
            key_name = T.id_name(name, piece.label, taken)
            renewal = is_renewal(name)
            years = years_for(name, renewal_years) if renewal else None
            if renewal and years is None:
                out.skipped_riders[name] = "갱신형 특약인데 갱신주기년이 없음(사람이 정할 값)"
                lost += len(piece.covers)
                continue
            rider = T.rider_row(variant_id, name, piece.label, years, key_name)
            if renewal:
                rider["갱신여부"] = True
                rider["갱신주기년"] = years
            out.riders.append(rider)
            for key, covers in groups.items():
                if labelled[key]:
                    for c in covers:
                        if not problems[c.number]:
                            _add(out, rider, readings[c.number], c, piece, role, c.name,
                                 readings[c.number].get("대상") or "")
                    continue
                rows = []
                for c in covers:
                    if problems[c.number]:
                        rows = []
                        break
                    label = name if len(names) > 1 and len(piece.covers) == 1 else c.name
                    rows.append((c, _row(rider, readings[c.number], c, piece, role, label)))
                if len(covers) > 1:
                    blocked = any(problems[c.number] for c in covers)
                    distinct = {repr(sorted(r.items())) for _, r in rows}
                    if blocked or len(distinct) > 1:
                        why = "그중 행을 만들 수 없는 줄이 있음" if blocked else "값이 서로 다름"
                        nums = [c.number for c in covers]
                        for n in nums:
                            out.skipped.setdefault(n, f"이름이 같은 세부보장({', '.join(nums)})의 {why}. 급부ID가 겹침")
                        continue
                for _, row in rows[:1]:
                    out.benefits.append(row)
                    bid = row["급부ID"]
                    out.numbers[bid] = tuple(dict.fromkeys(out.numbers.get(bid, ()) + tuple(x.number for x, _ in rows)))
    _drop_clashes(out)
    if out.skipped_riders:
        examples = ", ".join(list(out.skipped_riders)[:3])
        out.notes.append(f"갱신주기년이 없어 뺀 갱신형 특약 {len(out.skipped_riders)}개, 그 특약의 세부보장 {lost}줄"
                         f"(사람이 정할 값). 예: {examples}")
    kinds = Counter(why.split(":", 1)[0].split("(", 1)[0] for why in out.skipped.values())
    if kinds:
        out.notes.append("행을 만들지 않은 줄: " + ", ".join(f"{k} {n}" for k, n in kinds.most_common()))
    return out


def _row(rider: Mapping[str, Any], v: Mapping[str, Any], cover: CoverView, piece: PieceView, role: str, label: str,
         target: str = "") -> dict[str, Any]:
    row = T.benefit_row(rider["특약ID"], reading_of(v, cover, piece, label, target), role, cover.page)
    if v["꼴"] == AMOUNT:
        row.update({"기준가입금액만원": float(v["기준가입금액만원"]), "기준지급금액만원": float(v["지급액만원"]),
                    "지급기준구분": AMOUNT})
    return row


def _add(out: Built, rider: Mapping[str, Any], v: Mapping[str, Any], cover: CoverView, piece: PieceView, role: str,
         label: str, target: str) -> None:
    row = _row(rider, v, cover, piece, role, label, target)
    out.benefits.append(row)
    bid = row["급부ID"]
    out.numbers[bid] = tuple(dict.fromkeys(out.numbers.get(bid, ()) + (cover.number,)))


def _drop_clashes(out: Built) -> None:
    """조각이 달라도 급부ID가 같아지는 행(이름의 구두점만 다른 경우 따위). 글자까지 같으면 하나만, 다르면 모두 뺀다."""
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in out.benefits:
        by_id.setdefault(row["급부ID"], []).append(row)
    kept = []
    for bid, rows in by_id.items():
        if len({repr(sorted(r.items())) for r in rows}) > 1:
            for n in out.numbers.pop(bid, ()):
                out.skipped.setdefault(n, "다른 세부보장과 급부ID가 겹치고 값이 다름")
            continue
        kept.append(rows[0])
    out.benefits = kept


def final_readings(lines: Iterable[Mapping[str, Any]], a_name: str, b_name: str) -> dict[str, dict[str, Any]]:
    """견줌 결과 파일(scripts/compare_readers.py의 값 파일)의 줄에서 판정이 끝난 값을 고른다.

    판정이 "확정"이면 판독 A의 값(두 값이 같다), a_name이나 b_name이면 그 판독의 값, "수정"이면 판정값 칸의 값이다.
    판정이 비었거나 "검토 대기"인 줄은 넣지 않는다.
    """
    out = {}
    for line in lines:
        verdict = line.get("판정") or ""
        if verdict == CONFIRMED or verdict == a_name:
            value = line.get(a_name)
        elif verdict == b_name:
            value = line.get(b_name)
        elif verdict == "수정":
            value = line.get("판정값")
        else:
            continue
        if isinstance(value, Mapping):
            blanks = [{"칸": k, "이유": "값 파일에서 생략"} for k in value.get("모름칸") or []]
            out[line["번호"]] = {**DEFAULTS, **{k: v for k, v in value.items() if k in _KEYS}, "모름": blanks,
                                 "번호": line["번호"], "쪽": int(value.get("쪽") or line.get("쪽") or 0)}
    return out


def stored_value(v: Mapping[str, Any]) -> dict[str, Any]:
    """값 파일(data/crosscheck)에 적을 판독 값. 모름의 이유(판독자가 쓴 글)는 빼고 칸 이름만 남긴다."""
    out = {k: v[k] for k in ("쪽", "면책근거쪽") + FIELDS if k in v}
    out["모름칸"] = sorted({b["칸"] for b in v.get("모름") or []})
    return out
