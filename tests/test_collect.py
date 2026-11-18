from datetime import date, datetime

from postlife import collect, config
from postlife.gemini import Answer, GeminiError, SearchResult, Source, annotate
from postlife.schema import TABS
from postlife.sheets_io import MemoryBackend, SheetStore
from postlife.snapshot import KST
from postlife.validate import check_rows

NOW = datetime(2026, 11, 16, 6, 10, tzinfo=KST)  # 월요일


class FakeGemini:
    """질의마다 정해 둔 답을 돌려준다. 실제 호출은 없다."""

    def __init__(self, items, screens=None, same=0.1, fail_search=False, url="https://example-news.kr/a1"):
        self.items = items
        self.url = url
        self.screens = screens or {}
        self.same = same
        self.fail_search = fail_search
        self.calls = {}
        self.prompts = []

    def _count(self, model):
        self.calls[model] = self.calls.get(model, 0) + 1

    def search(self, model, prompt):
        self._count(model)
        self.prompts.append(prompt)
        if self.fail_search:
            raise GeminiError(429, "한도 초과")
        return SearchResult(
            text="2026-11-10 한화생명이 ... [1]",
            sources=[Source(1, "example-news.kr", self.url)],
        )

    def generate(self, model, prompt, schema=None, temperature=0.0):
        self._count(model)
        return list(self.items)

    def decide(self, model, input_text, questions):
        self._count(model)
        if "same" in questions:
            return {"same": Answer(self.same >= 0.5, None, {"true": self.same, "false": 1 - self.same})}
        for title, (prob, category) in self.screens.items():
            if title in input_text:
                break
        else:
            prob, category = 0.95, "신담보출시"
        return {
            "is_target": Answer(prob >= 0.5, None, {"true": prob, "false": 1 - prob}),
            "category": Answer(category, 0.9, {category: 0.9}),
        }


def item(title, published="2026-11-10", org="SAMSUNGLIFE", summary=None, sources=(1,)):
    return {
        "published_date": published,
        "org_code": org,
        "title": title,
        "summary": summary or f"{title}을 출시했다.",
        "media": "",
        "source_numbers": list(sources),
    }


def run(gemini, backend=None, **kw):
    store = SheetStore(backend or MemoryBackend())
    kw.setdefault("max_queries", 1)
    return collect.run(gemini, store, now=NOW, resolve=lambda u: u, **kw), store


def test_plan_matches_planning_doc():
    assert {d: len(q) for d, q in config.DAILY_PLAN.items()} == config.PLANNED_CALLS
    covered = {c for plan in config.DAILY_PLAN.values() for q in plan for c in q.orgs}
    assert set(config.INSTITUTIONS) <= covered
    assert len(config.INSTITUTIONS) == 19
    # 재시도(질의당 최대 3회)를 다 써도 하루 검색 한도를 넘지 않는다
    assert max(config.PLANNED_CALLS.values()) * 3 <= config.SEARCH_DAILY_LIMIT


def test_search_prompt_states_dates_not_relative_terms():
    q = config.DAILY_PLAN[0][0]
    prompt = collect.build_search_prompt(q, date(2026, 11, 2), date(2026, 11, 16))
    assert "2026-11-02" in prompt and "2026-11-16" in prompt
    for word in ("최근", "이번 주", "지난주", "한 달"):
        assert word not in prompt


def test_annotate_uses_byte_offsets():
    text = "가나다. 라마바."
    end = len("가나다.".encode("utf-8"))
    out = annotate(text, [{"segment": {"endIndex": end}, "groundingChunkIndices": [0, 2]}])
    assert out == "가나다.[1][3] 라마바."


def test_week_label():
    assert collect.week_of(date(2026, 11, 18)) == "2026-W47"


def test_out_of_window_items_are_dropped_by_code():
    g = FakeGemini([item("새 암보험"), item("7월 소식", published="2026-07-03")])
    report, store = run(g)
    assert [r["핵심요약"] for r in report.written] == ["새 암보험을 출시했다."]
    assert report.out_of_window == 1
    # 구간 밖 기사는 판정 모델까지 가지 않는다
    assert g.calls[config.MODEL_DECIDE] == 1
    assert any(l["대상열"] == "발표일자" and l["변경전값"] == "2026-07-03" for l in report.logs)


def test_rows_written_follow_schema_and_log_everything():
    g = FakeGemini([item("새 암보험")])
    report, store = run(g)
    data = store.read(["sys_시장동향", "sys_작업로그"])
    assert len(data["sys_시장동향"]) == 1 and data["sys_시장동향"][0]["수집주차"] == "2026-W47"
    assert check_rows("sys_시장동향", data["sys_시장동향"]) == {}
    assert check_rows("sys_작업로그", data["sys_작업로그"]) == {}
    assert set(data["sys_작업로그"][0]) == set(TABS["sys_작업로그"].header)


def test_screening_three_way_split():
    g = FakeGemini(
        [item("새 암보험"), item("사회공헌 행사"), item("애매한 소식")],
        screens={"사회공헌 행사": (0.05, "해당없음"), "애매한 소식": (0.55, "상품개정")},
    )
    report, _ = run(g)
    assert len(report.written) == 1 and report.rejected == 1 and report.held == 1
    held = [l for l in report.logs if l["작업단계"] == "사람검토이관"]
    assert held and held[0]["결과"] == "보류" and "example-news.kr" in held[0]["사유"]


def test_items_without_source_or_wrong_org_are_rejected():
    g = FakeGemini([item("출처 없음", sources=()), item("다른 회사", org="KYOBO"), item("날짜 없음", published="11월 초")])
    report, _ = run(g)
    assert report.written == [] and report.rejected == 3
    assert config.MODEL_DECIDE not in g.calls


def test_duplicates_are_merged_within_run_and_against_sheet():
    same = item("새 암보험", summary="삼성생명이 새 암보험을 출시했다.")
    near = item("암보험 신상품", summary="삼성생명이 새 암보험을 출시하였다")
    report, store = run(FakeGemini([same, near]))
    assert len(report.written) == 1 and report.duplicates == 1

    # 다음 실행에서 표현이 달라도 판정 모델이 같은 사건이라 하면 합친다
    other = item("신규 암 보장 상품", summary="암 치료비를 보장하는 신상품을 내놨다.", published="2026-11-12")
    again, _ = run(FakeGemini([other], same=0.9, url="https://other-news.kr/b2"), backend=store.backend)
    assert again.written == [] and again.duplicates == 1
    assert again.logs[-1]["작업단계"] == "판정"
    different, _ = run(FakeGemini([other], same=0.1, url="https://other-news.kr/b2"), backend=store.backend)
    assert len(different.written) == 1
    # 같은 기사 주소면 묻지 않고 합친다
    same_url, _ = run(FakeGemini([other], same=0.1), backend=store.backend)
    assert same_url.duplicates == 1 and same_url.logs[-1]["작업단계"] == "코드대조"


def test_failed_query_is_logged_and_retried_on_sunday():
    backend = MemoryBackend()
    report, store = run(FakeGemini([], fail_search=True), backend=backend)
    assert report.failed_queries and report.logs[0]["결과"] == "보류"

    sunday = datetime(2026, 11, 22, 6, 10, tzinfo=KST)
    g = FakeGemini([item("새 암보험", published="2026-11-20")])
    retry = collect.run(g, SheetStore(backend), now=sunday, resolve=lambda u: u)
    assert retry.queries == 1 and len(retry.written) == 1
    # 성공하면 다음 재수집 대상에서 빠진다
    logs = SheetStore(backend).read(["sys_작업로그"])["sys_작업로그"]
    assert collect.failed_queries(logs, "2026-W47", sunday.date()) == []


def test_dry_run_writes_nothing():
    backend = MemoryBackend()
    report, _ = run(FakeGemini([item("새 암보험")]), backend=backend, dry_run=True)
    assert len(report.written) == 1
    assert len(backend.data["sys_시장동향"]) == 1  # 머리행만


def test_thresholds_come_from_sheet_when_present():
    rows = [{"기준키": "기사선별_통과", "기준분류": "판정구간", "수치값": 0.9}]
    assert collect.load_thresholds(rows)["기사선별_통과"] == 0.9
    assert collect.load_thresholds([])["기사선별_통과"] == config.DEFAULT_THRESHOLDS["기사선별_통과"]
