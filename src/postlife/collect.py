"""시장 소식 수집 (판단 ⑨).

흐름: 검색(2.5 Flash Lite) → 정형화(3.5 Flash Lite) → 코드 날짜 확인 →
선별·분류(판정 모델) → 중복 병합 → sys_시장동향, sys_작업로그 기록.

기간 조건은 세 단계로 지킨다 (docs/planning.md 4.3).
1. 질의에 상대 시점을 쓰지 않고 날짜를 적어 넣는다.
2. 소식마다 발행일을 먼저 적게 하고, 불분명한 건은 빼게 한다.
3. 정형화 직후 코드가 발표일자를 확인해 구간 밖의 행을 버린다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from typing import Any, Callable

from . import config, ids
from .gemini import Gemini, GeminiError, SearchResult
from .sheets_io import SheetStore
from .snapshot import KST
from .validate import check_row

REDIRECT_HOST = "vertexaisearch.cloud.google.com"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

STRUCT_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "published_date": {"type": "STRING"},
            "org_code": {"type": "STRING"},
            "title": {"type": "STRING"},
            "summary": {"type": "STRING"},
            "media": {"type": "STRING"},
            "source_numbers": {"type": "ARRAY", "items": {"type": "INTEGER"}},
        },
        "required": ["published_date", "org_code", "title", "summary", "source_numbers"],
    },
}


@dataclass
class Candidate:
    published: str
    org: str
    title: str
    summary: str
    media: str
    url: str
    category: str = ""
    probability: float | None = None

    @property
    def text(self) -> str:
        return f"{self.title} {self.summary}"


@dataclass
class Report:
    run_at: str
    weekday: int
    window: tuple[str, str]
    queries: int = 0
    failed_queries: list[str] = field(default_factory=list)
    extracted: int = 0
    out_of_window: int = 0
    rejected: int = 0
    held: int = 0
    duplicates: int = 0
    written: list[dict[str, Any]] = field(default_factory=list)
    logs: list[dict[str, Any]] = field(default_factory=list)
    calls: dict[str, int] = field(default_factory=dict)


def week_of(d: date) -> str:
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def window(today: date, days: int = config.SEARCH_LOOKBACK_DAYS) -> tuple[date, date]:
    return today - timedelta(days=days), today


def query_key(q: config.Query) -> str:
    """질의를 가리키는 키. 요일을 넣지 않아 일요일 재수집 결과가 원래 질의에 이어진다."""
    return f"Q|{'+'.join(q.orgs)}|{'+'.join(q.topics)}"


def build_search_prompt(q: config.Query, start: date, end: date) -> str:
    names = ", ".join(config.ALL_ORGS[c] for c in q.orgs)
    topics = "\n".join(f"- {t}: {config.CATEGORIES[t]}" for t in q.topics)
    focus = f"\n특히 다음을 찾습니다: {q.focus}" if q.focus else ""
    return f"""대상: {names}
기간: {start.isoformat()}부터 {end.isoformat()}까지 발행된 기사와 보도자료만 찾습니다.{focus}

찾는 소식 (보장성 보험, 그중에서도 건강·암·뇌·심장·간편심사 보험 중심):
{topics}

제외: {config.EXCLUDED_TOPICS}.

규칙
1. 소식마다 발행일(YYYY-MM-DD)을 맨 앞에 적습니다.
2. 발행일을 확인할 수 없거나 기간 밖인 소식은 적지 않습니다.
3. 소식마다 회사명, 상품·특약 이름, 무엇이 바뀌었는지를 2~3문장으로 적습니다. 수치(가입금액, 나이, 기간)는 기사에 나온 그대로 적습니다.
4. 기사에 없는 내용을 덧붙이지 않습니다. 해당하는 소식이 없으면 "해당 기간에 확인된 소식 없음"이라고만 적습니다."""


def build_structure_prompt(result: SearchResult, q: config.Query, start: date, end: date) -> str:
    orgs = "\n".join(f"- {c}: {config.ALL_ORGS[c]}" for c in q.orgs)
    sources = "\n".join(f"[{s.index}] {s.title}" for s in result.sources) or "(출처 목록 없음)"
    return f"""아래 검색 결과에서 보험 소식을 한 건씩 뽑아 JSON 배열로 정리합니다.

기관코드 (org_code에는 이 코드만 씁니다)
{orgs}

규칙
- published_date: 본문에 적힌 발행일을 YYYY-MM-DD로 적습니다. 본문에 발행일이 없으면 그 소식은 넣지 않습니다. 날짜를 짐작해서 채우지 않습니다.
- title: 소식을 가리키는 짧은 제목.
- summary: 누가 무엇을 어떻게 바꿨는지 한 문장으로. 본문에 있는 수치는 그대로 씁니다. 본문에 없는 내용은 쓰지 않습니다.
- media: 매체명. 알 수 없으면 빈 문자열.
- source_numbers: 그 소식 문장 뒤에 붙은 대괄호 번호. 번호가 없으면 빈 배열.
- 같은 사건을 다룬 문장이 여러 개면 한 건으로 합칩니다.
- 소식이 없으면 빈 배열 []을 돌려줍니다.
- 참고: 수집 구간은 {start.isoformat()}부터 {end.isoformat()}까지입니다. 구간 밖의 소식도 발행일을 그대로 적습니다. 걸러내는 일은 뒤 단계가 합니다.

출처 목록
{sources}

검색 결과
{result.text}"""


def resolve_url(uri: str, get: Callable[..., Any] | None = None) -> str:
    """검색 그라운딩의 경유 주소를 실제 기사 주소로 푼다. 실패하면 받은 주소를 그대로 쓴다."""
    if REDIRECT_HOST not in uri:
        return uri
    try:
        if get is None:
            import requests

            get = requests.get
        resp = get(uri, allow_redirects=False, timeout=10)
        return resp.headers.get("Location") or uri
    except Exception:
        return uri


def to_candidates(
    raw: list[dict], result: SearchResult, q: config.Query, resolve: Callable[[str], str]
) -> tuple[list[Candidate], list[tuple[dict, str]]]:
    """정형화 결과를 후보로 바꾼다. 형식이 어긋난 건은 사유와 함께 따로 돌려준다."""
    by_index = {s.index: s for s in result.sources}
    good: list[Candidate] = []
    bad: list[tuple[dict, str]] = []
    for item in raw:
        published = str(item.get("published_date", "")).strip()
        org = str(item.get("org_code", "")).strip().upper()
        summary = str(item.get("summary", "")).strip()
        if not _DATE.match(published):
            bad.append((item, "발행일 형식이 아님"))
            continue
        if org not in q.orgs:
            bad.append((item, f"질의 대상이 아닌 기관: {org}"))
            continue
        if not summary:
            bad.append((item, "요약이 비어 있음"))
            continue
        source = next(
            (by_index[n] for n in item.get("source_numbers") or [] if n in by_index and by_index[n].uri),
            None,
        )
        if source is None:
            bad.append((item, "출처를 확인할 수 없음"))
            continue
        good.append(
            Candidate(
                published=published,
                org=org,
                title=str(item.get("title", "")).strip(),
                summary=summary,
                media=str(item.get("media", "")).strip() or source.title,
                url=resolve(source.uri),
            )
        )
    return good, bad


def in_window(published: str, start: date, end: date) -> bool:
    try:
        d = date.fromisoformat(published)
    except ValueError:
        return False
    return start <= d <= end


def screen_questions(topics: tuple[str, ...] | None = None) -> dict[str, dict]:
    criteria = dict(config.CATEGORIES)
    criteria[config.NOT_APPLICABLE] = (
        f"위 일곱 가지에 들지 않는 소식. {config.EXCLUDED_TOPICS} 소식도 여기에 해당"
    )
    return {
        "is_target": {
            "type": "noul",
            "instructions": (
                "이 소식이 보장성 보험(건강·암·뇌·심장·간편심사·종신·정기) 상품이나 인수 기준, "
                "또는 그에 영향을 주는 제도의 구체적인 변화를 다루면 참. "
                f"{config.EXCLUDED_TOPICS} 소식이거나 구체적인 변화가 없는 홍보성 소식이면 거짓."
            ),
        },
        "category": {
            "type": "choice",
            "instructions": "이 소식의 중심 내용에 가장 가까운 분류 하나를 고른다. 어디에도 들지 않으면 해당없음을 고른다.",
            "criteria": criteria,
        },
    }


def screen(gemini: Gemini, c: Candidate) -> tuple[float, str]:
    """선별 확률과 분류를 돌려준다."""
    text = f"기관: {config.ALL_ORGS[c.org]}\n발행일: {c.published}\n제목: {c.title}\n요약: {c.summary}"
    answers = gemini.decide(config.MODEL_DECIDE, text, screen_questions())
    target = answers["is_target"]
    return target.prob(True), str(answers["category"].value)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, ids.normalize(a), ids.normalize(b)).ratio()


def same_event(gemini: Gemini, a: str, b: str) -> float:
    answers = gemini.decide(
        config.MODEL_DECIDE,
        f"소식 A: {a}\n소식 B: {b}",
        {
            "same": {
                "type": "noul",
                "instructions": (
                    "두 소식이 같은 회사의 같은 사건(같은 상품의 같은 출시·개정·판매중지 등)을 다루면 참. "
                    "같은 회사라도 다른 상품이거나 다른 시점의 다른 조치면 거짓."
                ),
            }
        },
    )
    return answers["same"].prob(True)


def find_duplicate(
    gemini: Gemini, c: Candidate, pool: list[dict[str, Any]], threshold: float
) -> tuple[str | None, float, str]:
    """같은 기관·분류 안에서 발표일이 7일 이내로 가까운 기존 소식 가운데 같은 사건을 찾는다.

    (동향ID, 확률, 가린 주체)를 돌려준다. 주소나 글자가 거의 같으면 코드가,
    표현이 다르면 판정 모델이 가린다.
    """
    day = date.fromisoformat(c.published)
    for row in pool:
        if row["기관코드"] != c.org or row["분류유형"] != c.category:
            continue
        try:
            gap = abs((date.fromisoformat(str(row["발표일자"])) - day).days)
        except ValueError:
            continue
        if gap > 7:
            continue
        if row["출처URL"] == c.url:
            return row["동향ID"], 1.0, "코드대조"
        ratio = similarity(c.summary, str(row["핵심요약"]))
        if ratio >= 0.8:
            return row["동향ID"], ratio, "코드대조"
        prob = same_event(gemini, c.text, str(row["핵심요약"]))
        if prob >= threshold:
            return row["동향ID"], prob, "판정"
    return None, 0.0, ""


def load_thresholds(rows: list[dict[str, Any]]) -> dict[str, float]:
    out = dict(config.DEFAULT_THRESHOLDS)
    for r in rows:
        if r.get("기준분류") == "판정구간" and r.get("기준키") in out and r.get("수치값") is not None:
            out[r["기준키"]] = float(r["수치값"])
    return out


class _Logger:
    def __init__(self, now: datetime):
        self.stamp = now.isoformat(timespec="seconds")
        self.rows: list[dict[str, Any]] = []

    def add(self, step: str, target: str, result: str, reason: str = "",
            model: str = "", prob: float | None = None, column: str = "",
            before: str = "") -> None:
        row = {
            "로그ID": f"LOG_{ids.short_hash(self.stamp, step, target, str(len(self.rows)), length=14)}",
            "실행일시": self.stamp,
            "작업단계": step,
            "대상탭": "sys_시장동향",
            "대상행ID": target,
            "대상열": column or None,
            "변경전값": before or None,
            "변경후값": None,
            "호출모델": model or None,
            "판정확률": None if prob is None else round(prob, 4),
            "결과": result,
            "사유": reason or None,
        }
        self.rows.append(row)


def failed_queries(logs: list[dict[str, Any]], week: str, now: date) -> list[config.Query]:
    """이번 주에 실패한 채로 남은 질의를 찾는다. 일요일 재수집에 쓴다."""
    state: dict[str, str] = {}
    for r in sorted(logs, key=lambda r: str(r["실행일시"])):
        key = str(r.get("대상행ID", ""))
        if not key.startswith("Q|"):
            continue
        try:
            if week_of(date.fromisoformat(str(r["실행일시"])[:10])) != week:
                continue
        except ValueError:
            continue
        state[key] = str(r["결과"])
    out = []
    for key, result in state.items():
        if result == "통과":
            continue
        _, orgs, topics = key.split("|")
        match = next(
            (q for plan in config.DAILY_PLAN.values() for q in plan
             if "+".join(q.orgs) == orgs and "+".join(q.topics) == topics),
            None,
        )
        if match:
            out.append(match)
    return out


def run(
    gemini: Gemini,
    store: SheetStore,
    now: datetime | None = None,
    weekday: int | None = None,
    dry_run: bool = False,
    max_queries: int | None = None,
    resolve: Callable[[str], str] = resolve_url,
    lookback_days: int = config.SEARCH_LOOKBACK_DAYS,
) -> Report:
    now = now or datetime.now(KST)
    today = now.date()
    day = today.weekday() if weekday is None else weekday
    start, end = window(today, lookback_days)
    week = week_of(today)

    existing = store.read(["sys_시장동향", "sys_작업로그", "hum_기준값"])
    thresholds = load_thresholds(existing["hum_기준값"])
    pool = list(existing["sys_시장동향"])
    known = {r["동향ID"] for r in pool}

    queries = list(config.DAILY_PLAN[day]) or failed_queries(existing["sys_작업로그"], week, today)
    if max_queries is not None:
        queries = queries[:max_queries]

    report = Report(now.isoformat(timespec="seconds"), day, (start.isoformat(), end.isoformat()))
    log = _Logger(now)

    for q in queries:
        key = query_key(q)
        report.queries += 1
        try:
            result = gemini.search(config.MODEL_SEARCH, build_search_prompt(q, start, end))
            raw = gemini.generate(
                config.MODEL_EXTRACT, build_structure_prompt(result, q, start, end), schema=STRUCT_SCHEMA
            )
        except (GeminiError, ValueError) as e:
            report.failed_queries.append(key)
            log.add("추출", key, "보류", f"호출 실패: {e}"[:300], model=config.MODEL_SEARCH)
            continue

        candidates, bad = to_candidates(raw if isinstance(raw, list) else [], result, q, resolve)
        report.extracted += len(candidates) + len(bad)
        log.add("추출", key, "통과", f"소식 {len(candidates) + len(bad)}건, 출처 {len(result.sources)}건",
                model=config.MODEL_EXTRACT)
        for item, reason in bad:
            report.rejected += 1
            log.add("코드대조", key, "반려", f"{reason}: {str(item.get('title', ''))[:80]}")

        for c in candidates:
            if not in_window(c.published, start, end):
                report.out_of_window += 1
                log.add("코드대조", key, "반려", f"수집 구간 밖: {c.title[:80]}",
                        column="발표일자", before=c.published)
                continue
            try:
                prob, category = screen(gemini, c)
            except (GeminiError, KeyError) as e:
                report.held += 1
                log.add("판정", key, "보류", f"판정 실패({e}): {c.title[:80]}"[:300], model=config.MODEL_DECIDE)
                continue
            c.probability, c.category = prob, category
            if category not in config.CATEGORIES or prob < thresholds["기사선별_보류"]:
                report.rejected += 1
                log.add("판정", key, "반려", f"대상 아님({category}): {c.title[:80]}",
                        model=config.MODEL_DECIDE, prob=prob)
                continue
            if prob < thresholds["기사선별_통과"]:
                report.held += 1
                log.add("사람검토이관", key, "보류", f"[{category}] {c.summary[:150]} | {c.url}"[:400],
                        model=config.MODEL_DECIDE, prob=prob)
                continue

            trend = ids.trend_id(c.org, c.category, c.published, c.summary)
            try:
                dup, dup_prob, dup_by = (trend, 1.0, "코드대조") if trend in known else find_duplicate(
                    gemini, c, pool, thresholds["중복판정_동일"]
                )
            except (GeminiError, KeyError):
                dup, dup_prob, dup_by = None, 0.0, ""
            if dup:
                report.duplicates += 1
                log.add(dup_by, dup, "반려", f"중복 소식 병합: {c.title[:80]}",
                        model=config.MODEL_DECIDE if dup_by == "판정" else "", prob=dup_prob)
                continue

            row = {
                "동향ID": trend,
                "수집주차": week,
                "발표일자": c.published,
                "기관코드": c.org,
                "분류유형": c.category,
                "관련종형ID": None,
                "관련표준담보ID": None,
                "핵심요약": c.summary,
                "매체명": c.media or None,
                "출처URL": c.url,
                "수집경로": "검색",
                "판정확률": round(prob, 4),
            }
            problems = check_row("sys_시장동향", row)
            if problems:
                report.rejected += 1
                log.add("코드대조", trend, "반려", "; ".join(problems)[:300])
                continue
            pool.append(row)
            known.add(trend)
            report.written.append(row)
            log.add("판정", trend, "통과", model=config.MODEL_DECIDE, prob=prob)

    report.logs = log.rows
    report.calls = dict(gemini.calls)
    if not dry_run:
        store.append("sys_시장동향", report.written)
        store.append("sys_작업로그", report.logs)
    return report

