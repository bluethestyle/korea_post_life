"""시사점(site/insights.py): 지급 형태 꼬리표, 조건 우열, 시사점 네 유형과 범위 차이, 검토 대기 빼기."""
import itertools
from pathlib import Path

import pytest

from postlife.schema import TABS
from postlife.site import compare as C
from postlife.site import insights as I
from postlife.site.model import Data, load
from postlife.site.relations import Relations
from postlife.validate import NO_AMOUNT_BASES, check_rows

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "snapshot"


# ---------- 지급 형태 꼬리표 ----------
def labels(text):
    return [t.label for t in I.pay_tags(text)]


@pytest.mark.parametrize("text, expected", [
    ("최초 1회한", ["최초 1회"]),
    ("최초1회한 지급", ["최초 1회"]),
    ("암, 갑상선암, 기타피부암 또는 대장점막내암 중 최초 1회에 한함", ["최초 1회"]),
    ("연간 1회한", ["연간 1회"]),
    ("연 1회한", ["연간 1회"]),
    ("최초 진단확정일로부터 최대 10년간, 매년 1회를 한도로 지급(최대 10회 지급)", ["연간 1회"]),
    ("매년, 10년", ["매년"]),
    ("수술 1회당", ["수술 1회당"]),
    ("1회당", ["1회당"]),
    ("재해 사고일자당 1회한", ["사고 1회당"]),
    ("1일 이상 입원일수 1일당, 120일 한도", ["1일당(120일 한도)"]),
    ("3일 초과 입원일수 1일당, 60일 한도", ["1일당(4일째부터, 60일 한도)"]),
    ("1회 입원당 30일을 최고 한도로 합니다.", ["1일당(30일 한도)"]),
    ("30일을 한도로 입원1일당 일당 지급", ["1일당(30일 한도)"]),
    ("간병인 사용 1일 기준", ["1일당"]),
    ("1회당, 1일 1회한, 연간 30회한", ["연간 30회", "1회당", "1일당"]),
    ("연간 총 지급액은 5천만원을 한도로 함 / 각 치료행위별로 각각의 지급방식에 따라 약관에서 정한 금액을 지급", ["연간 5천만원 한도"]),
    ("500만원 한도 / 안면부 1cm당 14만원", ["500만원 한도"]),
    ("「수술회차별 체증 금액」 / 매 회당 30%씩 체증한 금액을 말함(최대 5회)", ["체증"]),
    ("해당 장해지급률", ["읽지 못함"]),
    ("", []),
    (None, []),
])
def test_pay_tags(text, expected):
    assert labels(text) == expected


def test_same_kind_with_different_event_word_is_the_same_form():
    assert {t.key for t in I.pay_tags("수술 1회당")} == {t.key for t in I.pay_tags("1회당 지급")}
    assert {t.key for t in I.pay_tags("4일 이상 입원일수 1일당, 120일한도")} == {t.key for t in I.pay_tags("3일 초과 1일당, 120일 한도")}


@pytest.mark.parametrize("base, other, verdict", [
    ("수술 1회당", "1회당", I.SAME),
    ("최초 1회한", "연간 1회한", I.WORSE),          # 기준이 최초 1회, 상대가 되풀이 지급
    ("수술 1회당", "최초 1회한", I.BETTER),
    ("수술 1회당", "연간 1회한", I.DIFF),           # 회당과 연간 1회는 우열을 매기지 않는다
    ("연간 1회한", "연간 3회한", I.DIFF),
    ("1일당, 120일 한도", "180일을 한도로 입원1일당", I.DIFF),
    ("최초 1회한", "최초 1회한, 연간 5천만원을 한도로", I.DIFF),
    ("해당 장해지급률", "최초 1회한", I.HOLD),
    ("", "최초 1회한", I.HOLD),
])
def test_compare_pay(base, other, verdict):
    out = I.compare_pay(base, other)
    assert out["판정"] == verdict
    assert out["항목"] == I.PAY
    if verdict == I.HOLD:
        assert out["사유"] in (I.HOLD_UNREAD, I.HOLD_NO_TEXT)


# ---------- 면책과 감액 ----------
def test_wait_shorter_is_better():
    assert I.compare_wait(90, 0) == I.WORSE
    assert I.compare_wait(0, 90) == I.BETTER
    assert I.compare_wait(None, 0) == I.SAME


@pytest.mark.parametrize("base, other, verdict", [
    ([], [], I.SAME),
    ([], [[12, 0.5]], I.BETTER),
    ([[12, 0.5]], [], I.WORSE),
    ([[6, 0.5]], [[12, 0.5]], I.BETTER),            # 기간이 짧다
    ([[12, 0.75]], [[12, 0.5]], I.BETTER),          # 지급률이 높다
    ([[6, 0.25]], [[12, 0.5]], I.MIXED),            # 기간은 짧고 지급률은 낮다
    ([[12, 0.5]], [[6, 0.1], [12, 0.5]], I.BETTER),  # 구간이 둘: 앞 6개월은 기준이 높고 뒤 6개월은 같다
    ([[6, 0.1], [24, 0.5]], [[12, 0.5]], I.WORSE),   # 앞 6개월 낮고, 6~12개월 같고, 12~24개월 낮다
    ([[6, 0.1], [12, 0.75]], [[12, 0.5]], I.MIXED),  # 앞 6개월은 낮고 뒤 6개월은 높다
])
def test_compare_reduction(base, other, verdict):
    assert I.compare_reduction(base, other) == verdict


def test_single_segment_reduction_agrees_with_the_comparison_table():
    # compare.compare_reduction(other, base)는 상대 쪽 부호다
    flip = {"+": I.WORSE, "-": I.BETTER, "=": I.SAME, "~": I.MIXED}
    segs = [[]] + [[[m, r]] for m, r in itertools.product((6, 12, 24), (0.25, 0.5, 0.75))]
    for base, other in itertools.product(segs, segs):
        assert I.compare_reduction(base, other) == flip[C.compare_reduction(other, base)], (base, other)


def view(wait=0, red=None, limit="최초 1회한", exc=None):
    return {"wait": wait, "red": red or [], "limit": limit, "exc": exc}


def test_reduction_exception_holds_the_reduction_and_the_whole_verdict():
    out = I.compare_conditions(view(red=[[12, 0.5]], exc="갱신계약의 경우 감액 적용 안 함"), view())
    red = next(i for i in out["항목"] if i["항목"] == I.REDUCTION)
    assert (red["판정"], red["사유"]) == (I.HOLD, I.HOLD_EXCEPTION)
    assert (out["판정"], out["보류밖판정"]) == (I.HOLD, I.SAME)
    # 보류가 있으면 나머지에 나음이 있어도 보류로 두고, 나머지만 모은 판정을 따로 적는다
    out = I.compare_conditions(view(wait=0, red=[[12, 0.5]], exc="재해는 감액 없음"), view(wait=90))
    assert (out["판정"], out["보류밖판정"]) == (I.HOLD, I.BETTER)


@pytest.mark.parametrize("results, verdict", [
    ([I.SAME, I.SAME, I.SAME], I.SAME),
    ([I.BETTER, I.SAME, I.DIFF], I.BETTER),
    ([I.WORSE, I.SAME, I.SAME], I.WORSE),
    ([I.WORSE, I.BETTER, I.SAME], I.MIXED),
    ([I.SAME, I.MIXED, I.SAME], I.MIXED),
    ([I.SAME, I.SAME, I.HOLD], I.HOLD),
    ([I.WORSE, I.SAME, I.HOLD], I.HOLD),
    ([I.SAME, I.SAME, I.DIFF], I.SAME),
])
def test_combine(results, verdict):
    assert I.combine(results) == verdict


def test_conditions_report_values():
    out = I.compare_conditions(view(wait=90, red=[[12, 0.5]], limit="수술 1회당"), view(wait=0, limit="연간 1회한"))
    assert [(i["항목"], i["기준"], i["상대"], i["판정"]) for i in out["항목"]] == [
        ("면책", "90일", "0일", I.WORSE), ("감액", "1년 50%", "감액 없음", I.WORSE), ("지급 형태", "수술 1회당", "연간 1회", I.DIFF)]
    assert (out["판정"], out["지급형태"]) == (I.WORSE, I.DIFF)


def test_amount_verdict_is_the_comparison_table_code_turned_to_the_base_side():
    assert I.amount_verdict("b+==.")["지급액"] == I.WORSE
    assert I.amount_verdict("w-==L")["지급액"] == I.BETTER
    assert I.amount_verdict("x") == {"비교표부호": "x", "지급액": None, "사유": "금액 자료 없음"}


def test_score_formula():
    assert I.score(I.GAP, None, 2, "암보장") == 29
    assert I.score(I.CONDITION, I.WORSE, 1, "공통보장") == 13
    assert I.score(I.CONDITION, I.BETTER, 2, "심장보장") == 27
    assert I.score(I.SCOPE, I.MISSING_SIDE, 2, "뇌혈관보장") == 25


# ---------- 지어낸 세 회사 ----------
BASE, OLD, HW, SS = "EPOST_T1_aaaaaa", "EPOST_T0_eeeeee", "HANWHALIFE_T2_bbbbbb", "SAMSUNGFIRE_T3_cccccc"
STAMP = "2026-11-20T10:00:00+09:00"


def row(tab, **values):
    out = {c.name: None for c in TABS[tab].columns}
    assert not set(values) - set(out), set(values) - set(out)
    out.update(values)
    return out


def std(sid, major, name):
    return row("hum_표준담보사전", 표준담보ID=sid, 보장대분류=major, 보장중분류=major[:-2] + "시험", 표준담보명=name, 급부유형="진단",
               비교기준단위만원=1000, 사용여부=True)


class Book:
    """지어낸 사본 표를 쌓는다."""

    def __init__(self):
        self.t = {name: [] for name in ("sys_상품종형", "sys_특약", "sys_급부", "hum_담보매핑", "hum_표준담보사전", "sys_작업로그")}
        self.n = 0
        for vid, org, end in ((BASE, "EPOST", None), (OLD, "EPOST", "2026-06-16"), (HW, "HANWHALIFE", None), (SS, "SAMSUNGFIRE", None)):
            self.t["sys_상품종형"].append(row("sys_상품종형", 종형ID=vid, 기관코드=org, 공시상품명=f"{org} 시험보험", 종형명="간편가입325",
                                          비교역할구분="정밀비교", 심사유형="간편심사", 간편고지약칭="3.2.5", 적용시작일="2026-01-01",
                                          판매종료일=end, 요약서해시=f"h{vid}", 사업방법서해시=f"m{vid}"))
            self.t["sys_특약"].append(row("sys_특약", 특약ID=f"{vid}_T", 종형ID=vid, 특약계보키="T", 담보구분="선택특약",
                                      원시특약명="시험특약", 최대가입금액만원=1000))

    def ben(self, vid, sid, wait=0, red=None, limit="최초 1회한", exc=None, state="자동확정", pay=1000, logged=False, basis=None):
        """basis: 지급기준구분. 금액 없는 값(차등지급 따위)이면 두 금액과 감액을 비운다."""
        self.n += 1
        bid = f"{vid}_T_B{self.n}"
        months, rate = red or (None, None)
        base = 1000
        if basis in NO_AMOUNT_BASES:
            base = pay = months = rate = exc = None
        self.t["sys_급부"].append(row("sys_급부", 급부ID=bid, 특약ID=f"{vid}_T", 원시급부명=f"{sid} 급부{self.n}", 급부역할="주급부",
                                   기준가입금액만원=base, 기준지급금액만원=pay, 지급기준구분=basis, 면책기간일수=wait,
                                   감액개월1=months, 감액지급률1=rate,
                                   감액예외=exc, 지급횟수제한=limit, 근거문서종류="요약서", 근거문서쪽수=self.n))
        confirmed = state in ("자동확정", "승인", "수정")
        self.t["hum_담보매핑"].append(row("hum_담보매핑", 급부ID=bid, 검토상태=state, 추천표준담보ID=sid,
                                       확정표준담보ID=sid if confirmed else None, 매핑확률=0.9))
        if logged:
            self.t["sys_작업로그"].append(row("sys_작업로그", 로그ID=f"L{self.n}", 실행일시=STAMP, 작업단계="사람검토이관",
                                          대상탭="sys_급부", 대상행ID=bid, 대상열="면책기간일수", 결과="보류"))
        return bid

    def peers(self, sid, **kw):
        return [self.ben(HW, sid, **kw), self.ben(SS, sid, **kw)]


REL = Relations([
    {"관계": "통합", "넓은담보ID": "STD_CA_U", "넓은담보": None, "좁은담보ID": "STD_CA_P1", "좁은담보": None},
    {"관계": "통합", "넓은담보ID": "STD_CA_U", "넓은담보": None, "좁은담보ID": "STD_CA_P2", "좁은담보": None},
    {"관계": "통합", "넓은담보ID": "STD_CA_U2", "넓은담보": None, "좁은담보ID": "STD_CA_Q1", "좁은담보": None},
    {"관계": "통합", "넓은담보ID": "STD_CA_U2", "넓은담보": None, "좁은담보ID": "STD_CA_Q2", "좁은담보": None},
    {"관계": "포함", "넓은담보ID": "STD_BR_WIDE", "넓은담보": None, "좁은담보ID": "STD_BR_NARROW", "좁은담보": None},
])


@pytest.fixture()
def book():
    b = Book()
    names = {"STD_CA_GAP": "암 빈자리", "STD_CA_GAP2": "암 대기 빈자리", "STD_CM_ONE": "한 곳만", "STD_CM_GAP3": "대기로 둘",
             "STD_CM_GAP4": "로그 대기 보유", "STD_CA_U": "통합", "STD_CA_P1": "부분1", "STD_CA_P2": "부분2", "STD_CA_U2": "통합2",
             "STD_CA_Q1": "부분Q1", "STD_CA_Q2": "부분Q2", "STD_BR_WIDE": "넓은 뇌", "STD_BR_NARROW": "좁은 뇌",
             "STD_HT_ONLY": "우리만", "STD_CM_C1": "면책 격차", "STD_CA_C2": "지급 형태 나음", "STD_CA_C3": "지급 형태 다름",
             "STD_CA_C4": "감액 예외", "STD_CM_C5": "한쪽 로그 대기", "STD_CM_C6": "양쪽 매핑 대기"}
    major = {"CA": "암보장", "CM": "공통보장", "BR": "뇌혈관보장", "HT": "심장보장"}
    b.t["hum_표준담보사전"] = [std(sid, major[sid.split("_")[1]], name) for sid, name in names.items()]
    b.peers("STD_CA_GAP")                                          # 빈자리
    b.peers("STD_CA_GAP2"); b.ben(BASE, "STD_CA_GAP2", state="대기")  # 기준 쪽 매핑 대기 → 뺌
    b.ben(HW, "STD_CM_ONE")                                         # 한 곳만 가져 빈자리가 아님
    b.ben(HW, "STD_CM_GAP3"); b.ben(SS, "STD_CM_GAP3", state="대기")  # 가진 회사 수가 매핑 대기에 달림 → 뺌
    b.ben(HW, "STD_CM_GAP4"); b.ben(SS, "STD_CM_GAP4", logged=True)  # 한 곳은 급부가 모두 작업 로그 대기 → 뺌
    b.ben(BASE, "STD_CA_U"); b.peers("STD_CA_P1")                   # 범위 차이(기준에 없음): 기준이 통합 담보로 덮음
    b.ben(BASE, "STD_CA_Q1"); b.peers("STD_CA_U2")                  # 범위 차이(기준에 없음): 부분 담보 일부만
    b.ben(BASE, "STD_BR_NARROW"); b.peers("STD_BR_WIDE")            # 넓은 뇌는 빈자리, 좁은 뇌는 범위 차이(기준에만 있음)
    b.ben(BASE, "STD_HT_ONLY")                                      # 고유
    b.ben(BASE, "STD_CM_C1", wait=90); b.peers("STD_CM_C1", wait=0, pay=2000)  # 조건 격차(못함), 지급액도 못함
    b.ben(BASE, "STD_CA_C2", limit="수술 1회당"); b.ben(HW, "STD_CA_C2", limit="최초 1회한"); b.ben(SS, "STD_CA_C2", limit="1회당")
    b.ben(BASE, "STD_CA_C3", limit="수술 1회당"); b.ben(HW, "STD_CA_C3", limit="연간 1회한"); b.ben(SS, "STD_CA_C3", limit="수술 1회당")
    b.ben(BASE, "STD_CA_C4", red=(12, 0.5), exc="갱신계약은 감액하지 않음"); b.peers("STD_CA_C4")  # 판정 보류
    b.ben(BASE, "STD_CM_C5", wait=90); b.ben(HW, "STD_CM_C5", logged=True); b.ben(SS, "STD_CM_C5")
    b.ben(BASE, "STD_CM_C6", wait=90); b.peers("STD_CM_C6")
    b.ben(HW, "STD_CM_C6", state="대기"); b.ben(SS, "STD_CM_C6", state="대기")
    b.ben(OLD, "STD_CM_C1")                                         # 판매가 끝난 종형은 기준이 아니다
    return b


@pytest.fixture()
def result(book):
    return I.analyze(Data(book.t), REL)


def find(base, kind, sid, direction=None):
    hit = [x for x in base["시사점"] if x["유형"] == kind and x["표준담보ID"] == sid and x["방향"] == direction]
    assert len(hit) <= 1
    return hit[0] if hit else None


def kinds(base, sid):
    return sorted((x["유형"], x["방향"] or "") for x in base["시사점"] if x["표준담보ID"] == sid)


def test_only_selling_home_variants_are_bases_and_peers_come_from_compare(result):
    assert [b["종형ID"] for b in result["기준"]] == [BASE]
    assert [p["종형ID"] for p in result["기준"][0]["맞붙는종형"]] == [HW, SS]


def test_gap_and_scope_are_told_apart(result):
    base = result["기준"][0]
    gap = find(base, I.GAP, "STD_CA_GAP")
    assert gap["비교종형ID"] == [HW, SS] and gap["점수"] == 29 and gap["근거"]["기준"] == []
    assert set(gap["근거"]["비교"]) == {HW, SS}
    assert kinds(base, "STD_CM_ONE") == []
    # 기준이 통합 담보로 덮는 부분 담보는 빈자리가 아니라 범위 차이다
    assert kinds(base, "STD_CA_P1") == [(I.SCOPE, I.MISSING_SIDE)]
    scope = find(base, I.SCOPE, "STD_CA_P1", I.MISSING_SIDE)
    assert scope["항목"][0]["덮임"] == "넓은 담보" and scope["항목"][0]["덮는담보"] == ["통합"]
    # 부분 담보를 일부만 가지면 범위 차이로 적고 빠진 부분 담보를 적는다
    part = find(base, I.SCOPE, "STD_CA_U2", I.MISSING_SIDE)
    assert (part["항목"][0]["덮임"], part["항목"][0]["일부만"], part["항목"][0]["빠진부분담보"]) == ("부분 담보", True, ["부분Q2"])
    # 좁은 담보만 가지면 넓은 담보는 빈자리이고, 좁은 담보는 상대가 넓은 담보로 덮으므로 고유가 아니다
    wide = find(base, I.GAP, "STD_BR_WIDE")
    assert wide["변수"]["기준좁은담보"] == ["좁은 뇌"] and len(wide["근거"]["기준"]) == 1
    assert kinds(base, "STD_BR_NARROW") == [(I.SCOPE, I.ONLY_SIDE)]
    assert kinds(base, "STD_HT_ONLY") == [(I.UNIQUE, "")]
    assert find(base, I.UNIQUE, "STD_HT_ONLY")["점수"] == 27
    # 기준만 가진 통합 담보를 상대가 부분 담보 일부로 덮고, 기준만 가진 부분 담보를 상대가 통합 담보로 덮는다
    only_u = find(base, I.SCOPE, "STD_CA_U", I.ONLY_SIDE)
    assert [(i["덮임"], i["일부만"], i["빠진부분담보"]) for i in only_u["항목"]] == [("부분 담보", True, ["부분2"])] * 2
    only_q1 = find(base, I.SCOPE, "STD_CA_Q1", I.ONLY_SIDE)
    assert only_q1["변수"]["덮는담보"] == {"한화생명": ["통합2"], "삼성화재": ["통합2"]}


def test_condition_gap_and_design_difference(result):
    base = result["기준"][0]
    worse = find(base, I.CONDITION, "STD_CM_C1", I.WORSE)
    assert worse["비교종형ID"] == [HW, SS]
    assert [(i["종형ID"], i["항목"], i["기준"], i["상대"]) for i in worse["항목"]] == [(HW, "면책", "90일", "0일"), (SS, "면책", "90일", "0일")]
    assert worse["변수"]["차이"] == {"한화생명": ["면책 90일 대 0일"], "삼성화재": ["면책 90일 대 0일"]}
    assert worse["지급액"][HW]["지급액"] == I.WORSE            # 지급액 우열은 비교표 부호를 옮긴 것
    assert worse["지급액"][HW]["비교표부호"][0] == "b"
    # 최초 1회 대 회당은 회당 쪽이 낫다. 같은 회당인 삼성화재와는 같음이라 시사점이 없다
    better = find(base, I.CONDITION, "STD_CA_C2", I.BETTER)
    assert better["비교종형ID"] == [HW]
    assert kinds(base, "STD_CA_C2") == [(I.CONDITION, I.BETTER)]
    # 회당 대 연간 1회는 우열 없이 설계 차이
    assert kinds(base, "STD_CA_C3") == [(I.DESIGN, "")]
    design = find(base, I.DESIGN, "STD_CA_C3")
    assert design["변수"]["상대지급형태"] == {"한화생명": "연간 1회"}


def test_held_verdict_is_not_an_insight(result):
    base = result["기준"][0]
    assert kinds(base, "STD_CA_C4") == []
    held = [x for x in base["보류비교"] if x["표준담보ID"] == "STD_CA_C4"]
    assert len(held) == 2 and all(x["사유"] == [f"감액: {I.HOLD_EXCEPTION}"] for x in held)
    assert base["조건우열분포"][HW][I.HOLD] == 1


def test_pending_rows_are_left_out_and_counted(result):
    base = result["기준"][0]
    for sid in ("STD_CA_GAP2", "STD_CM_GAP3", "STD_CM_GAP4", "STD_CM_C6"):
        assert kinds(base, sid) == [], sid
    dropped = {(x["유형"], x["표준담보ID"]): x["사유"] for x in base["뺀시사점"]}
    assert dropped == {
        (I.GAP, "STD_CA_GAP2"): ["기준 종형에 이 담보로 덮일 수 있는 매핑 대기 급부가 있음"],
        (I.GAP, "STD_CM_GAP3"): ["가진 회사 수가 매핑 대기 급부에 달림"],
        (I.GAP, "STD_CM_GAP4"): ["가진 쪽의 이 담보 급부가 모두 작업 로그 검토 대기"],
        (I.CONDITION, "STD_CM_C6"): [f"{HW} 매핑 대기 1줄", f"{SS} 매핑 대기 1줄"],
    }
    assert base["뺀수"] == {I.GAP: 3, I.CONDITION: 1, I.UNIQUE: 0, I.DESIGN: 0, I.SCOPE: 0}
    # 한쪽만 작업 로그 대기면 그 비교 종형만 빼고 시사점은 남긴다
    c5 = find(base, I.CONDITION, "STD_CM_C5", I.WORSE)
    assert c5["비교종형ID"] == [SS]
    assert c5["뺀비교종형"] == [{"종형ID": HW, "사유": [f"{HW} 작업 로그 대기 1줄"]}]
    assert base["뺀비교쌍"] == 3


def test_summary_counts_and_order(result):
    base = result["기준"][0]
    assert base["유형별"] == {I.GAP: 2, I.CONDITION: 3, I.UNIQUE: 1, I.DESIGN: 1, I.SCOPE: 5}
    assert result["요약"]["유형별"] == base["유형별"]
    assert result["요약"]["시사점수"] == 12
    scores = [x["점수"] for x in base["시사점"]]
    assert scores == sorted(scores, reverse=True)
    assert base["시사점"][0]["유형"] == I.GAP
    ids = [x["시사점ID"] for x in base["시사점"]]
    assert len(ids) == len(set(ids))
    tags = result["요약"]["지급형태꼬리표"]
    assert tags["EPOST"]["문구있음"] == tags["EPOST"]["급부"] and tags["EPOST"]["비율"] == 1.0


# ---------- 실제 사본 ----------
@pytest.mark.skipif(not (SNAPSHOT / "sys_급부.jsonl").exists(), reason="사본 없음")
def test_real_snapshot_runs_and_holds_together():
    data = load(SNAPSHOT)
    result = I.analyze(data)
    s = result["요약"]
    assert s["기준종형수"] > 0 and s["시사점수"] > 0 and s["비교쌍"] > 0
    assert all(s["유형별"][t] > 0 for t in (I.GAP, I.CONDITION, I.DESIGN, I.SCOPE))
    assert result["담보관계수"] > 0 and result["담보관계확인"] == []
    assert {"EPOST", "HANWHALIFE", "SAMSUNGFIRE"} <= set(s["지급형태꼬리표"])
    assert all(st["비율"] and st["비율"] > 0 for st in s["지급형태꼬리표"].values() if st["문구있음"])
    for b in result["기준"]:
        assert data.variants[b["종형ID"]]["기관코드"] == "EPOST"
        own = set(C.collect(data, b["종형ID"])[0])
        peers = {p["종형ID"] for p in b["맞붙는종형"]}
        for ins in b["시사점"]:
            assert set(ins["비교종형ID"]) <= peers
            bids = ins["근거"]["기준"] + [x for v in ins["근거"]["비교"].values() for x in v]
            assert bids and all(x in data.benefits for x in bids)
            if ins["유형"] == I.GAP:
                assert ins["표준담보ID"] not in own
            if ins["유형"] in (I.UNIQUE, I.CONDITION, I.DESIGN):
                assert ins["표준담보ID"] in own


# ---------- 금액 하나로 담기지 않는 급부(지급기준구분 차등지급 따위) ----------
def form_book():
    b = Book()
    names = {"STD_CA_F1": "금액 없는 상대", "STD_CA_F2": "감액 견줌", "STD_CA_F3": "같은 꼴", "STD_CA_F4": "대표 밖"}
    b.t["hum_표준담보사전"] = [std(sid, "암보장", name) for sid, name in names.items()]
    b.ben(BASE, "STD_CA_F1", limit="수술 1회당"); b.ben(HW, "STD_CA_F1", wait=90, limit="연간 3회한", basis="차등지급")
    b.ben(BASE, "STD_CA_F2", red=(12, 0.5)); b.ben(HW, "STD_CA_F2", basis="실손보상")
    b.ben(BASE, "STD_CA_F3", basis="차등지급"); b.ben(HW, "STD_CA_F3", basis="차등지급")
    b.ben(BASE, "STD_CA_F4"); b.ben(HW, "STD_CA_F4"); b.ben(HW, "STD_CA_F4", basis="분할지급")
    assert check_rows("sys_급부", b.t["sys_급부"]) == {}
    return b


def test_benefit_view_carries_form_only_on_benefits_without_amount():
    data = Data(form_book().t)
    views = [data.benefit_view(bid) for bid in data.benefits]
    forms = [v for v in views if "form" in v]
    assert {v["form"] for v in forms} == {"차등지급", "실손보상", "분할지급"}
    assert all(v["base"] is None and v["pay"] is None and v["red"] == [] and v["exc"] is None for v in forms)
    assert all("form" not in v for v in views if v["pay"] is not None)


def test_benefit_without_amount_is_held_not_unique_and_its_pair_is_a_design_difference():
    result = I.analyze(Data(form_book().t), REL)["기준"][0]
    assert result["맞붙는종형"][0]["종형ID"] == HW
    # 상대가 금액 없는 급부로만 가진 담보도 보유다. 고유가 아니다
    assert kinds(result, "STD_CA_F1") == [(I.DESIGN, "")]
    pair = next(p for p in result["비교쌍목록"] if p["표준담보ID"] == "STD_CA_F1")
    assert (pair["판정"], pair["지급형태"]) == (I.HOLD, I.DIFF)
    held = next(x for x in result["보류비교"] if x["표준담보ID"] == "STD_CA_F1")
    items = {i["항목"]: i for i in held["항목"]}
    assert (items[I.REDUCTION]["판정"], items[I.REDUCTION]["사유"]) == (I.HOLD, I.HOLD_FORM_CUT)
    assert (items[I.REDUCTION]["기준"], items[I.REDUCTION]["상대"]) == ("감액 없음", I.CUT_IN_SOURCE)
    assert (items[I.PAY]["기준"], items[I.PAY]["상대"]) == ("정액 지급(수술 1회당)", "차등지급")
    assert items[I.WAIT]["판정"] == I.BETTER                # 면책은 그대로 견준다
    design = find(result, I.DESIGN, "STD_CA_F1")
    assert design["변수"]["기준지급형태"] == "정액 지급(수술 1회당)" and design["변수"]["상대지급형태"] == {"한화생명": "차등지급"}
    assert design["지급액"][HW] == {"비교표부호": "x", "지급액": None, "사유": I.AMOUNT_FORM}


def test_empty_cut_of_a_benefit_without_amount_is_not_read_as_no_cut():
    result = I.analyze(Data(form_book().t), REL)["기준"][0]
    # 기준은 1년 50% 감액, 상대는 감액 칸이 빈 실손보상. 감액 없음으로 견주면 조건 못함이 나온다
    assert (I.CONDITION, I.WORSE) not in kinds(result, "STD_CA_F2")
    assert kinds(result, "STD_CA_F2") == [(I.DESIGN, "")]
    assert next(p for p in result["비교쌍목록"] if p["표준담보ID"] == "STD_CA_F2")["판정"] == I.HOLD
    assert not [x for x in result["시사점"] if x["유형"] == I.CONDITION]


def test_same_form_on_both_sides_is_held_not_a_design_difference():
    result = I.analyze(Data(form_book().t), REL)["기준"][0]
    assert kinds(result, "STD_CA_F3") == []
    held = next(x for x in result["보류비교"] if x["표준담보ID"] == "STD_CA_F3")
    items = {i["항목"]: i for i in held["항목"]}
    assert (items[I.PAY]["판정"], items[I.PAY]["사유"]) == (I.HOLD, I.HOLD_SAME_FORM)
    assert (items[I.REDUCTION]["판정"], items[I.REDUCTION]["사유"]) == (I.HOLD, I.HOLD_SAME_FORM_CUT)


def test_benefit_without_amount_beside_the_representative_counts_as_an_other_line():
    data = Data(form_book().t)
    result = I.analyze(data, REL)["기준"][0]
    hold = I.Holding(data, HW)
    rep = hold.rep("STD_CA_F4")
    assert "form" not in rep                                 # 금액 급부가 대표다
    assert hold.other_lines("STD_CA_F4", rep) == 1
    pair = next(p for p in result["비교쌍목록"] if p["표준담보ID"] == "STD_CA_F4")
    assert pair["판정"] == I.SAME and kinds(result, "STD_CA_F4") == []
    assert I.condition_signature(rep)[-1] is None


def test_compare_pay_with_forms():
    assert I.compare_pay("최초 1회한", None, None, "현물급부")["판정"] == I.DIFF
    assert I.compare_pay(None, None, "분할지급", "현물급부")["판정"] == I.DIFF
    out = I.compare_pay("해당 장해지급률", "연간 1회한", None, "차등지급")
    assert (out["기준"], out["상대"], out["판정"]) == ("정액 지급", "차등지급", I.DIFF)
    # 금액 급부끼리는 지금과 같다
    assert I.compare_pay("최초 1회한", "연간 1회한") == I.compare_pay("최초 1회한", "연간 1회한", None, None)
