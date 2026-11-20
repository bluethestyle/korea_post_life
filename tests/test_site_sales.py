"""영업 인사이트(site/sales.py): 가입 관문, 고객군 지도의 칸 분류와 이름, 영업 인사이트의 다섯 분류와 문장 둘, 범위 머리말,
빼는 조건, 정렬, 먼저 보일 것, 분석 담당자용 집계(단정 주의, 개정 검토, 치료 여정, 한도 표, 보류 요약), 브리핑, 내보내기.

자료는 손으로 지어낸 세 회사다. 공시 원문은 옮기지 않는다.
"""
import json
from pathlib import Path

import pytest

from postlife.schema import TABS
from postlife.site import compare as C
from postlife.site import insights as I
from postlife.site import sales as S
from postlife.site.model import Data, load
from postlife.site.relations import Relations

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "snapshot"
STAMP = "2026-11-20T10:00:00+09:00"

E1, E5, EG = "EPOST_E1_aaaaaa", "EPOST_E5_aaaaaa", "EPOST_EG_aaaaaa"
H1, HG = "HANWHALIFE_H1_bbbbbb", "HANWHALIFE_HG_bbbbbb"
S1, SA, SB = "SAMSUNGFIRE_S1_cccccc", "SAMSUNGFIRE_SA_cccccc", "SAMSUNGFIRE_SB_cccccc"
UNPAID = "해약환급금 미지급형"

# 종형ID, 기관, 종형명, 심사유형, 간편고지약칭, (소견개월, 입원수술년수, 중대질병년수, 수술포함, 중대질병수), 갱신, 환급, 시작일, 가입나이
VARIANTS = [
    (E1, "EPOST", "1종(간편가입315)", "간편심사", "3.1.5", (3, 1, 5, False, 6), "갱신", "표준형", "2026-06-17", [(20, 80)]),
    (E5, "EPOST", "3종(간편가입355)", "간편심사", "3.5.5", (3, 5, 5, False, 6), "갱신", "표준형", "2026-06-17", [(20, 80)]),
    (EG, "EPOST", "4종(일반가입)", "일반심사", "일반", (None,) * 5, "갱신", "표준형", "2026-06-17", [(15, 65)]),
    (H1, "HANWHALIFE", "간편가입형(1년)", "간편심사", "3.1.5", (3, 1, 5, True, 7), "비갱신", UNPAID, "2026-10-01",
     [(15, 60), (61, 80)]),
    (HG, "HANWHALIFE", "일반가입형", "일반심사", "일반", (None,) * 5, "비갱신", UNPAID, "2026-10-01", [(15, 80)]),
    (S1, "SAMSUNGFIRE", "7종(간편315)", "간편심사", "3.1.5", (3, 1, 5, True, 5), "갱신", UNPAID, "2026-07-01", []),
    (SA, "SAMSUNGFIRE", "8종(일반형)", "일반심사", "일반", (None,) * 5, "비갱신", "표준형", "2026-07-01", []),
    (SB, "SAMSUNGFIRE", "9종(미지급형,일반고지)", "일반심사", "일반", (None,) * 5, "갱신", UNPAID, "2026-07-01", []),
]


def row(tab, **values):
    out = {c.name: None for c in TABS[tab].columns}
    assert not set(values) - set(out), set(values) - set(out)
    out.update(values)
    return out


def std(sid, major, name, kind="진단"):
    return row("hum_표준담보사전", 표준담보ID=sid, 보장대분류=major, 보장중분류=major[:-2] + "시험", 표준담보명=name, 급부유형=kind,
               비교기준단위만원=1000, 사용여부=True)


class Book:
    """지어낸 사본 표. extra는 VARIANTS와 같은 꼴의 종형을 더한다."""

    def __init__(self, skip=(), extra=()):
        self.t = {name: [] for name in ("sys_상품종형", "sys_특약", "sys_급부", "hum_담보매핑", "hum_표준담보사전", "sys_작업로그",
                                        "sys_가입조건")}
        self.n = 0
        for vid, org, kind, uw, short, ask, renew, refund, start, ages in VARIANTS + list(extra):
            if vid in skip:
                continue
            months, years, major_years, surgery, major_n = ask
            self.t["sys_상품종형"].append(row(
                "sys_상품종형", 종형ID=vid, 기관코드=org, 공시상품명="시험건강보험", 종형명=kind, 비교역할구분="정밀비교", 심사유형=uw,
                간편고지약칭=short, 고지최근소견개월=months, 고지입원수술년수=years, 고지중대질병년수=major_years,
                고지수술포함여부=surgery, 고지중대질병수=major_n, 갱신유형=renew, 환급유형=refund, 적용시작일=start,
                요약서해시=f"h{vid}", 사업방법서해시=f"m{vid}"))
            self.t["sys_특약"].append(row("sys_특약", 특약ID=f"{vid}_M", 종형ID=vid, 특약계보키="M", 담보구분="주계약",
                                      원시특약명="주계약", 최대가입금액만원=4000))
            self.t["sys_특약"].append(row("sys_특약", 특약ID=f"{vid}_T", 종형ID=vid, 특약계보키="T", 담보구분="선택특약",
                                      원시특약명="시험특약", 최대가입금액만원=1000))
            for i, (lo, hi) in enumerate(ages):
                self.t["sys_가입조건"].append(row("sys_가입조건", 조건행ID=f"{vid}_C{i}", 종형ID=vid, 보험기간구분="20년",
                                              납입기간구분="20년", 최저가입나이=lo, 최고가입나이=hi, 구간최대가입금액만원=4000 - i))

    def ben(self, vid, sid, wait=0, red=None, limit="최초 1회한", exc=None, state="자동확정", pay=1000, logged=False,
            red2=None, name=None):
        self.n += 1
        bid = f"{vid}_T_B{self.n}"
        months, rate = red or (None, None)
        months2, rate2 = red2 or (None, None)
        self.t["sys_급부"].append(row("sys_급부", 급부ID=bid, 특약ID=f"{vid}_T", 원시급부명=name or f"급부{self.n}", 급부역할="주급부",
                                   기준가입금액만원=1000, 기준지급금액만원=pay, 면책기간일수=wait, 감액개월1=months, 감액지급률1=rate,
                                   감액개월2=months2, 감액지급률2=rate2,
                                   감액예외=exc, 지급횟수제한=limit, 근거문서종류="요약서", 근거문서쪽수=self.n))
        confirmed = state in ("자동확정", "승인", "수정")
        self.t["hum_담보매핑"].append(row("hum_담보매핑", 급부ID=bid, 검토상태=state, 추천표준담보ID=sid,
                                       확정표준담보ID=sid if confirmed else None, 매핑확률=0.9))
        if logged:
            self.t["sys_작업로그"].append(row("sys_작업로그", 로그ID=f"L{self.n}", 실행일시=STAMP, 작업단계="사람검토이관",
                                          대상탭="sys_급부", 대상행ID=bid, 대상열="면책기간일수", 결과="보류"))
        return bid

    def peers(self, sid, **kw):
        return [self.ben(H1, sid, **kw), self.ben(S1, sid, **kw)]


REL = Relations([
    {"관계": "통합", "넓은담보ID": "STD_CA_U", "넓은담보": None, "좁은담보ID": "STD_CA_P1", "좁은담보": None},
    {"관계": "통합", "넓은담보ID": "STD_CA_U", "넓은담보": None, "좁은담보ID": "STD_CA_P2", "좁은담보": None},
    {"관계": "포함", "넓은담보ID": "STD_CM_WIDE", "넓은담보": None, "좁은담보ID": "STD_CM_NARROW", "좁은담보": None},
])

NAMES = {
    "STD_CA_GAP": ("암보장", "암 빈자리", "진단"), "STD_CM_WIDE": ("공통보장", "넓은 입원", "입원"),
    "STD_CM_NARROW": ("공통보장", "좁은 입원", "입원"), "STD_CA_U": ("암보장", "통합 암", "치료"),
    "STD_CA_P1": ("암보장", "부분1 암", "치료"), "STD_CA_P2": ("암보장", "부분2 암", "치료"),
    "STD_HT_ONLY": ("심장보장", "심장 입원", "입원"), "STD_CM_TOP": ("공통보장", "종별 수술비(최고 종 기준)", "수술"),
    "STD_BR_C": ("뇌혈관보장", "뇌 조건", "진단"), "STD_CA_B": ("암보장", "암 나음", "진단"),
    "STD_CM_D": ("공통보장", "면책 못함", "진단"), "STD_CM_PEND": ("공통보장", "대기 빈자리", "진단"),
    "STD_CA_H": ("암보장", "감액 예외", "진단"), "STD_CM_SWAP": ("공통보장", "근거 바꿈", "진단"),
}


def fill(b: Book) -> dict:
    b.t["hum_표준담보사전"] = [std(sid, *v) for sid, v in NAMES.items()]
    ids = {}
    b.peers("STD_CA_GAP")                                                  # Q2
    b.ben(E1, "STD_CM_NARROW"); b.peers("STD_CM_WIDE")                     # Q2, 우리는 좁은 담보만
    b.ben(E1, "STD_CA_U"); b.peers("STD_CA_P1")                            # Q1: 우리 통합 담보가 넓은 담보로 덮음
    b.ben(E1, "STD_HT_ONLY")                                               # A1(입원, 주의)
    b.ben(E1, "STD_CM_TOP")                                                # A1(이름에 "최고"가 든 자료 값)
    b.ben(E1, "STD_BR_C", red=(12, 0.5)); b.peers("STD_BR_C")              # Q3 둘, 감액이 끝나면 전액
    b.ben(E1, "STD_CA_B"); b.ben(H1, "STD_CA_B", red=(12, 0.5))            # A2: 한화생명과는 깨끗한 나음(갱신유형 다름)
    b.ben(S1, "STD_CA_B", wait=90); b.ben(S1, "STD_CA_B", red=(12, 0.5))   # 삼성화재는 대표 밖에 조건이 다른 줄 1
    b.ben(E1, "STD_CM_D", wait=90)                                         # Q3: 삼성화재만, 대표 밖 다른 줄이 있어 뺌
    b.ben(S1, "STD_CM_D", pay=2000); b.ben(S1, "STD_CM_D", limit="연간 1회한")
    b.peers("STD_CM_PEND"); b.ben(E1, "STD_CM_PEND", state="대기")        # 매핑 대기 → 뺌
    b.ben(E1, "STD_CA_H", red=(12, 0.5), exc="갱신계약은 감액하지 않음"); b.peers("STD_CA_H", wait=90)   # 판정 보류
    ids["swap_logged"] = b.ben(H1, "STD_CM_SWAP", pay=2000, logged=True)  # 대표가 작업 로그 대기
    ids["swap_ok"] = b.ben(H1, "STD_CM_SWAP")
    b.ben(S1, "STD_CM_SWAP")
    return ids


@pytest.fixture()
def book():
    b = Book()
    b.ids = fill(b)
    return b


@pytest.fixture()
def data(book):
    return Data(book.t)


@pytest.fixture()
def analysis(data):
    return I.analyze(data, REL)


def P(**kw):
    return S.Profile(**kw)


# ---------- 짝 고르기 ----------
def test_peers_prefer_the_same_renewal_then_refund(data):
    vids = I.base_variants(data)[0]
    assert C.peers(data, EG, vids) == [EG, HG, SB]          # 같은 일반심사 가운데 갱신유형이 같은 9종(첫째인 8종이 아니라)
    assert C.peers(data, E1, vids) == [E1, H1, S1]
    without = Data(Book(skip=(SB,)).t)                        # 갱신유형이 같은 후보가 없으면 지금처럼 첫째
    assert C.peers(without, EG, I.base_variants(without)[0]) == [EG, HG, SA]


def test_analyze_pair_is_the_same_as_analyze_for_the_same_peers(data, analysis):
    base = next(b for b in analysis["기준"] if b["종형ID"] == E1)
    pair = I.analyze_pair(data, E1, [H1, S1], REL)
    assert pair["시사점"] == base["시사점"] and pair["뺀시사점"] == base["뺀시사점"]
    one = I.analyze_pair(data, E1, [H1], REL)                 # 상대가 하나면 빈자리 기준(GAP_MIN 2)에 못 미친다
    assert one["유형별"][I.GAP] == 0


# ---------- 가입 관문 ----------
@pytest.mark.parametrize("vid, profile, hit", [
    (E1, P(), S.Q_NONE),
    (E1, P(since=0.25), S.Q_HIT),
    (E1, P(since=0.99), S.Q_HIT),
    (E1, P(since=1), S.Q_NONE),                                # 기간과 같으면 질문 밖
    (E1, P(since=0.25, surgery_only=True), S.Q_NONE),          # 우체국 간편은 기간 질문이 입원만 묻는다
    (H1, P(since=0.25, surgery_only=True), S.Q_HIT),
    (E5, P(since=4), S.Q_HIT),
    (EG, P(since=4), S.Q_REVIEW),
    (EG, P(since=5), S.Q_NONE),
    (EG, P(), S.Q_NONE),
])
def test_question_hit(data, vid, profile, hit):
    assert S.question_hit(data.variants[vid], profile) == hit


def test_question_hit_without_the_columns_is_no_data():
    v = {"심사유형": "간편심사", "고지입원수술년수": None, "고지수술포함여부": None}
    assert S.question_hit(v, P(since=1)) == S.Q_NODATA
    assert S.question_hit(v, P(since=1, surgery_only=True)) == S.Q_NODATA
    assert S.question_hit(v, P()) == S.Q_NONE


def test_gate_states_and_company_order(data):
    g = S.gate(data, P(age=30, since=1))
    by = {x["종형ID"]: x for c in g["회사"].values() for x in c["종형"]}
    assert by[E1]["상태"] == S.OPEN and by[E1]["한도만원"] == 4000
    assert by[E5]["상태"] == S.CLOSED and by[EG]["상태"] == S.REVIEW
    assert by[S1]["상태"] == S.NO_AGE and by[S1]["나이"] == S.AGE_NODATA
    assert {o: c["상태"] for o, c in g["회사"].items()} == {"EPOST": S.OPEN, "HANWHALIFE": S.OPEN, "SAMSUNGFIRE": S.NO_AGE}
    assert S.gate(data, P(age=17, since=1))["회사"]["EPOST"]["상태"] == S.REVIEW     # 간편은 나이로 닫히고 일반은 심사로 확인
    only = S.gate(data, P(age=30, renewal="비갱신"))["회사"]
    assert set(only) == {"HANWHALIFE", "SAMSUNGFIRE"} and [x["종형ID"] for x in only["SAMSUNGFIRE"]["종형"]] == [SA]


@pytest.mark.parametrize("profile, cls, nodata", [
    (P(age=30, since=0.25, surgery_only=True), S.ONLY_OPEN, []),
    (P(age=30, since=0.25), S.ALL_CLOSED, []),
    (P(age=30, since=1), S.BOTH_OPEN, ["SAMSUNGFIRE"]),
    (P(age=17, since=1), S.ONLY_CLOSED, ["SAMSUNGFIRE"]),
    (P(age=19), S.BOTH_OPEN, ["SAMSUNGFIRE"]),
    (P(age=30, since=1, renewal="갱신"), S.NO_DATA, ["SAMSUNGFIRE"]),   # 갱신형 상대는 삼성화재뿐이고 나이 자료가 없다
    (P(age=30, since=1, renewal="비갱신"), S.NO_DATA, []),           # 우리 비갱신 종형이 없다(자료가 없는 것과는 다르다)
])
def test_cell_classification_boundaries(data, analysis, profile, cls, nodata):
    out = S.cell(data, profile, analysis, REL)
    assert (out["분류"], out["자료없음"]) == (cls, nodata)
    assert ("안내" in out) == (cls == S.ALL_CLOSED)


def test_cell_representatives_and_counts(data, analysis):
    out = S.cell(data, P(age=30, since=1), analysis, REL)
    assert out["대표"] == E1 and out["상대대표"] == {"HANWHALIFE": H1, "SAMSUNGFIRE": S1}   # 나이 자료 없는 상대도 견준다
    assert out["수"] == {"고유": 2, "빈자리": 3, "못함": 1, "나음": 1, "대기": 1}
    # 간편이 모두 열리면 질문 기간이 가장 긴 종형이 대표다
    assert S.cell(data, P(age=30), analysis, REL)["대표"] == E5
    # 간편이 나이로 닫히면 열린 일반심사 종형이 대표이고, 상대는 바로잡은 짝이다
    young = S.cell(data, P(age=19), analysis, REL)
    assert young["대표"] == EG and young["상대대표"] == {"HANWHALIFE": HG, "SAMSUNGFIRE": SB}
    # 열린 상대가 없으면 숫자를 비운다
    lone = S.cell(data, P(age=30, since=0.25, surgery_only=True), analysis, REL)
    assert lone["대표"] == E5 and lone["상대대표"] == {} and lone["수"] is None
    assert S.cell(data, P(age=17, since=1), analysis, REL)["수"] is None


def test_segment_map_rows_columns_and_merging(data, analysis):
    m = S.segment_map(data, "M", None, analysis, REL)
    assert [r["이름"] for r in m["행"]] == ["입원 3개월~1년 전", "입원 1~5년 전", "입원 5년 넘음이나 없음",
                                          "수술만 3개월~1년 전", "수술만 1~5년 전", "수술만 5년 넘음이나 없음"]
    # 20~60과 61~65는 한도만 달라 합치고, 66~80은 우리 일반심사 종형이 닫혀 열린 종형이 달라 따로 둔다
    assert m["열"] == [{"lo": 15, "hi": 19}, {"lo": 20, "hi": 65}, {"lo": 66, "hi": 80}]
    grid = [[x["분류"] for x in line] for line in m["칸"]]
    assert grid == [
        [S.ALL_CLOSED] * 3,
        [S.ONLY_CLOSED, S.BOTH_OPEN, S.BOTH_OPEN],
        [S.BOTH_OPEN] * 3,
        [S.ALL_CLOSED, S.ONLY_OPEN, S.ONLY_OPEN],
        [S.ONLY_CLOSED, S.BOTH_OPEN, S.BOTH_OPEN],
        [S.BOTH_OPEN] * 3,
    ]
    assert m["집계"] == {S.ONLY_OPEN: 2, S.BOTH_OPEN: 10, S.ONLY_CLOSED: 2, S.ALL_CLOSED: 4, S.NO_DATA: 0}
    assert m["칸"][1][1]["자료없음"] == ["SAMSUNGFIRE"]


# ---------- 문장 틀 ----------
def test_render_fills_values_and_particles():
    assert S.render("Q2", {"우리종형": "1종", "담보": "암 진단비"}) == "우체국 1종에는 암 진단비에 해당하는 담보가 없습니다."
    assert S.render("조건_상대", {"상대": "한화생명 간편가입형(1년)", "상대조건": "감액 없음"}) == "한화생명 간편가입형(1년)은 감액 없음"
    assert S.render("조건_상대", {"상대": "삼성화재 7종 315·5", "상대조건": "감액 없음"}) == "삼성화재 7종 315·5는 감액 없음"
    assert S.render("Q_질문", {"상대회사": S.or_join(["한화생명", "삼성화재"]), "담보": "부정맥 진단비"}) == \
        "한화생명이나 삼성화재에는 부정맥 진단비가 있던데요."
    assert S.and_join(["가", "나", "다"]) == "가, 나와 다"


@pytest.mark.parametrize("word, final", [("간편가입형(1년)", True), ("1종(간편가입315)", False), ("단일", True),
                                         ("삼성화재", False), ("10", True), ("50%", False), ("THE FIT", False)])
def test_has_final(word, final):
    assert S.has_final(word) == final


def test_render_refuses_missing_values():
    with pytest.raises(S.TemplateValueMissing):
        S.render("Q2", {"우리종형": "1종", "담보": ""})
    with pytest.raises(S.TemplateValueMissing):
        S.render("Q2", {"우리종형": "1종"})
    assert S.render("Q2", {"우리종형": 0, "담보": "암"}).startswith("우체국 0에는")   # 0은 빈 값이 아니다


def test_render_refuses_forbidden_words(monkeypatch):
    for tid, tpl in S.TEMPLATES.items():
        assert S.forbidden_in(S._SLOT.sub(" ", tpl)) == [], tid
    with pytest.raises(S.ForbiddenWordError):
        S.render("G1", {"이력": "업계 최초로 마지막 입원이 1~2년 전", "소견개월": 3, "중대년수": 5, "우리종형": "1종",
                        "상대문장": "가."})
    monkeypatch.setitem(S.TEMPLATES, "시험", "{담보:은} 가장 좋은 담보입니다.")
    with pytest.raises(S.ForbiddenWordError):
        S.render("시험", {"담보": "암"})
    # 자료에서 온 이름은 사실을 옮긴 것이라 검사하지 않는다
    assert S.render("Q2", {"우리종형": "1종", "담보": "종별 수술비(최고 종 기준)"}).endswith("해당하는 담보가 없습니다.")


# ---------- 응대 포인트 ----------
@pytest.fixture()
def pts(data, analysis):
    return S.points(data, E1, P(age=30, since=0.25, surgery_only=True), analysis, REL)


def by_code(result, code):
    return [x for x in result["포인트"] if x["세부"] == code]


def by_sid(result, sid):
    hit = [x for x in result["포인트"] if x["표준담보ID"] == sid]
    assert len(hit) == 1, sid
    return hit[0]


def test_gate_points_only_open(pts):
    g1 = by_code(pts, "G1")
    assert len(g1) == 1 and g1[0]["원문대조"] and g1[0]["근거"][0] == {"종형ID": E1, "문서": "사업방법서", "쪽": None, "급부ID": None}
    assert g1[0]["원문대조글"] == "사업방법서 원문 확인 필요"
    # 본문은 분석 문장, 카드의 답은 고객에게 하는 말이다
    assert g1[0]["문장"] == (
        "입원 없이 받은 마지막 수술이 3개월~1년 전이고 최근 3개월 소견과 5년 안 중대질병에 해당하지 않는 고객은 "
        "우체국 1종(간편가입315)의 고지 질문에 해당하지 않습니다. 한화생명 간편가입형(1년)과 삼성화재 7종(간편315)는 "
        "같은 기간에 입원과 수술을 묻습니다. 가입 여부는 청약 뒤 심사로 정해집니다.")
    assert g1[0]["카드질문"] is None and g1[0]["카드답"] == (
        "입원 없이 받은 마지막 수술이 3개월~1년 전이고 최근 3개월 소견과 5년 안 중대질병에 해당하지 않으시면, "
        "우체국 1종(간편가입315)의 고지 질문에는 해당하지 않습니다. 한화생명 간편가입형(1년)과 삼성화재 7종(간편315)는 "
        "같은 기간에 입원과 수술을 묻습니다. 가입 여부는 청약 뒤 심사로 정해집니다.")
    g3 = by_code(pts, "G3")
    assert [x["비교종형ID"] for x in g3] == [[H1], [S1]]
    assert g3[0]["문장"] == ("1년 안 질문에서 우체국 1종(간편가입315)는 입원을, 한화생명 간편가입형(1년)은 입원과 수술을 묻습니다. "
                            "5년 안 중대질병 질문의 질병 수는 우체국 6개, 한화생명 7개입니다.")
    assert g3[0]["카드답"] == g3[0]["문장"] and g3[0]["원문대조글"] == "사업방법서 원문 확인 필요"


def test_gate_point_only_closed_leaves_out_companies_without_age_data(data, analysis):
    r = S.points(data, E1, P(age=17, since=1), analysis, REL)
    g2 = by_code(r, "G2")
    assert len(g2) == 1 and not by_code(r, "G1")
    assert g2[0]["문장"] == "17세는 우체국 1종(간편가입315)의 가입나이(20~80세) 밖입니다. 한화생명 간편가입형(1년)은 15~80세를 받습니다."
    assert {"세부": "G2", "사유": "나이 자료 없음: 삼성화재"}.items() <= next(x for x in r["뺀포인트"] if x["세부"] == "G2").items()
    # 일반심사 기준 종형에는 고지 질문 포인트가 없다
    assert not any(x["종류"] == S.GATE for x in S.points(data, EG, P(age=30, since=0.25, surgery_only=True), analysis, REL)["포인트"])


def test_lead_points(pts):
    a1 = by_sid(pts, "STD_HT_ONLY")
    assert a1["세부"] == "A1" and a1["주의"] == S.TEMPLATES["A1_주의"]
    assert a1["문장"] == ("심장 입원은 우체국 1종(간편가입315)에 따로 있는 담보입니다. 견준 한화생명, 삼성화재 상품에는 같은 담보가 "
                         "없습니다(넓은 담보와 부분 담보까지 확인).")
    assert a1["목적"] == ["3대 질병", "입원과 수술"] and a1["회사수"] == "견준 2개 회사 가운데 2곳"
    top = by_sid(pts, "STD_CM_TOP")                                 # 담보명에 "최고"가 들어도 자료 값이라 낸다
    assert top["세부"] == "A1" and top["주의"] is None
    a2 = by_sid(pts, "STD_CA_B")
    assert a2["세부"] == "A2" and a2["비교종형ID"] == [H1] and a2["구조다름"] and a2["브리핑"] is False
    assert a2["문장"] == ("암 나음은 우체국 1종(간편가입315)가 면책 0일, 감액 없음이고, 한화생명 간편가입형(1년)은 면책 0일, "
                         "1년까지 보험금의 50% 지급입니다.")


def test_ask_points(pts, book):
    q1 = by_sid(pts, "STD_CA_P1")
    assert q1["세부"] == "Q1" and q1["분류"] == S.RELATED and q1["카드질문"] == "한화생명이나 삼성화재에는 부분1 암이 있던데요."
    assert q1["카드답"].startswith("우체국 1종(간편가입315)에는 부분1 암을 따로 주는 담보는 없고, 통합 암에서 관련 보장을 합니다.")
    assert q1["문장"] == ("한화생명과 삼성화재에 있는 부분1 암은 우체국 1종(간편가입315)에 따로 없고, 우체국의 통합 암이 관련 보장을 "
                         "합니다. 지급 조건이 같은지는 약관 확인이 필요합니다.")
    wide = by_sid(pts, "STD_CM_WIDE")
    assert wide["세부"] == "Q2" and wide["좁은담보"] == ["좁은 입원"] and wide["꼬리표"] == [S.REVISION_TAG]
    assert wide["문장"] == ("한화생명과 삼성화재에 있는 넓은 입원은 우체국 1종(간편가입315)에 없습니다. "
                           "우체국 1종(간편가입315)에는 이보다 좁은 좁은 입원만 있습니다.")
    assert wide["카드답"] == "우체국 1종(간편가입315)에는 넓은 입원에 해당하는 담보가 없습니다."
    q3 = by_sid(pts, "STD_BR_C")
    assert q3["분류"] == S.DEFEND and q3["카드질문"] == "뇌 조건은 한화생명이나 삼성화재가 조건이 다르던데요."
    assert q3["카드답"] == ("맞습니다. 뇌 조건은 우체국 1종(간편가입315)가 1년까지 보험금의 50% 지급이고, 한화생명 간편가입형(1년)은 "
                          "감액 없음, 삼성화재 7종(간편315)는 감액 없음입니다. 1년이 지나면 모두 보험금 전액을 지급합니다.")
    assert q3["문장"] == q3["카드답"].removeprefix("맞습니다. ")
    # 대표가 작업 로그 대기인 근거는 같은 담보의 확정 급부로 바꾼다
    swap = by_sid(pts, "STD_CM_SWAP")
    assert book.ids["swap_ok"] in [e["급부ID"] for e in swap["근거"]]
    assert book.ids["swap_logged"] not in [e["급부ID"] for e in swap["근거"]]
    assert all(e["문서"] == "요약서" and isinstance(e["쪽"], int) for e in swap["근거"])


def test_dropped_points_have_reasons(pts):
    dropped = {(x["세부"], x["표준담보ID"]): x["사유"] for x in pts["뺀포인트"]}
    assert dropped[("A2", "STD_CA_B")].startswith("대표 밖에 조건이 다른 줄이 있음(삼성화재")
    assert dropped[("Q3", "STD_CM_D")].startswith("대표 밖에 조건이 다른 줄이 있음(삼성화재")
    assert dropped[("Q2", "STD_CM_PEND")].startswith("검토 대기:")
    assert dropped[("A2", "STD_CA_H")].startswith("조건 판정 보류: 감액")
    kept = {x["표준담보ID"] for x in pts["포인트"]}
    assert not kept & {"STD_CM_D", "STD_CM_PEND", "STD_CA_H"}


def test_header_names_every_peer_and_structure(pts):
    q2 = by_sid(pts, "STD_CA_GAP")
    assert q2["머리말"] == ("수집한 한화생명 시험건강보험 간편가입형(1년) 기준(2026-10-01), "
                           "수집한 삼성화재 시험건강보험 7종(간편315) 기준(2026-07-01) / 구조 다름: 우체국 갱신, 표준형 대 "
                           f"한화생명 비갱신, {UNPAID}; 삼성화재 갱신, {UNPAID}")
    assert all(x["머리말"].startswith("수집한 ") for x in pts["포인트"])
    s = pts["범위"]
    assert [r["구조다름"] for r in s["상대"]] == [True, True] and s["회사수"] == 2
    assert s["문장"].endswith("공통 담보 7쌍을 모두 견줬습니다.") and s["뺀비교쌍"] == 0


def test_points_and_scope_take_only_selling_home_variants(data, analysis):
    # 기준 종형은 판매 중인 정밀비교 우체국 종형뿐이다. 경쟁사 종형을 기준으로 받으면 그 앞에 "우체국"을 붙여 틀린 문장을 낸다.
    for vid in (H1, HG, S1, SA):
        with pytest.raises(ValueError, match="기준 종형"):
            S.points(data, vid, P(age=30), analysis, REL)
        with pytest.raises(ValueError, match="기준 종형"):
            S.scope(data, vid, [E1], analysis, REL)
    with pytest.raises(ValueError, match="종형이 없음"):
        S.points(data, "EPOST_NONE_000000", P(age=30), analysis, REL)
    # 판매를 마친 우체국 종형도 받지 않는다
    b = Book()
    fill(b)
    next(v for v in b.t["sys_상품종형"] if v["종형ID"] == E5)["판매종료일"] = "2026-09-30"
    ended = Data(b.t)
    with pytest.raises(ValueError, match="기준 종형"):
        S.points(ended, E5, P(age=30), None, REL)
    assert S.points(ended, E1, P(age=30), None, REL)["기준종형ID"] == E1
    # 지도 칸은 우리 대표를 판매 중인 종형에서만 고르므로 그대로 돈다
    assert S.cell(ended, P(age=30), None, REL)["대표"] == E1


@pytest.mark.parametrize("segs, text", [
    ([], "감액 없음"),
    ([[12, 0.5]], "1년까지 보험금의 50% 지급"),
    ([[12, 0.1]], "1년까지 보험금의 10% 지급"),          # 10%는 받는 비율이다(90% 감액)
    ([[12, 0.5], [6, 0.25]], "6개월까지 보험금의 25%, 1년까지 50% 지급"),
    ([[2, 0.1], [12, 0.5]], "2개월까지 보험금의 10%, 1년까지 50% 지급"),
])
def test_reduction_wording_says_the_paid_rate(segs, text):
    assert S._cond_value({"red": segs}, I.REDUCTION) == text


def test_reduction_sentence_with_low_paid_rates():
    # 지급률이 50%가 아닌 급부(10%, 25%에서 50%로 오르는 두 단계)가 조건 못함 문장에 들어가도 받는 비율로 읽힌다
    b = Book()
    fill(b)
    b.t["hum_표준담보사전"].append(std("STD_CM_LOW", "공통보장", "낮은 지급률"))
    b.ben(E1, "STD_CM_LOW", red=(12, 0.1))
    b.ben(H1, "STD_CM_LOW", red=(6, 0.25), red2=(12, 0.5))
    b.ben(S1, "STD_CM_LOW")
    d = Data(b.t)
    r = S.points(d, E1, P(age=30, since=1), None, REL)
    q3 = by_sid(r, "STD_CM_LOW")
    assert q3["세부"] == "Q3"
    assert q3["카드답"] == ("맞습니다. 낮은 지급률은 우체국 1종(간편가입315)가 1년까지 보험금의 10% 지급이고, "
                          "한화생명 간편가입형(1년)은 6개월까지 보험금의 25%, 1년까지 50% 지급, 삼성화재 7종(간편315)는 감액 없음입니다. "
                          "1년이 지나면 모두 보험금 전액을 지급합니다.")
    assert q3["문장"] == q3["카드답"].removeprefix("맞습니다. ")
    assert "감액 1년 10%" not in q3["문장"] and "감액 6개월 25%" not in q3["문장"]


def test_order_ids_and_brief(pts, data):
    codes = [x["세부"] for x in pts["포인트"]]
    assert codes[:3] == ["G1", "G3", "G3"]
    lead = [x["표준담보ID"] for x in pts["포인트"] if x["종류"] == S.LEAD]
    assert lead == ["STD_CA_B", "STD_HT_ONLY", "STD_CM_TOP"]       # 점수 27, 27(담보 순서), 22
    ask = [x["표준담보ID"] for x in pts["포인트"] if x["종류"] == S.ASK]
    assert ask == ["STD_CA_GAP", "STD_BR_C", "STD_CA_P1", "STD_CM_SWAP", "STD_CM_WIDE"]   # 29, 28, 25, 24, 24
    ids = [x["포인트ID"] for x in pts["포인트"]]
    assert len(set(ids)) == len(ids) and all(i.startswith("PT_") and len(i) == 15 for i in ids)
    assert pts["집계"] == {"G1": 1, "G2": 0, "G3": 2, "A1": 2, "A2": 1, "Q1": 1, "Q2": 3, "Q3": 1}
    # 브리핑: 세부마다 1건(G1, G3, A1, Q1, Q3, Q2) 뒤 남는 두 자리를 점수순(Q2 24, 24)으로. 구조 다름 A2(STD_CA_B)는 뺀다
    brief = S.brief(pts)
    assert [x["표준담보ID"] or x["세부"] for x in brief] == ["G1", "G3", "STD_HT_ONLY", "STD_CA_P1", "STD_BR_C",
                                                          "STD_CA_GAP", "STD_CM_SWAP", "STD_CM_WIDE"]
    # 카드: 남는 자리를 개정 검토 후보가 아닌 포인트(A1 22, 두 번째 G3)로 먼저 채우고, 조건 열위를 관련 담보 안내 앞에 둔다
    card = S.brief(pts, for_card=True)
    assert [x["표준담보ID"] or x["세부"] for x in card] == ["G1", "G3", "G3", "STD_HT_ONLY", "STD_CM_TOP", "STD_BR_C",
                                                         "STD_CA_P1", "STD_CA_GAP"]
    assert [x["표준담보ID"] for x in S.brief(pts, purpose="암") if x["분류"] != S.GATE_DIFF] == ["STD_CA_P1", "STD_CA_GAP"]
    # 같은 조건이면 포인트ID가 같다(analyze 결과 없이 다시 돌려도)
    assert ids == [x["포인트ID"] for x in S.points(data, E1, pts["조건"], None, REL)["포인트"]]


# ---------- 다섯 분류와 문장 둘 ----------
def test_categories_do_not_overlap(pts, data, analysis):
    assert set(S.CATEGORY) == set(S.CODES) and set(S.CATEGORY.values()) == set(S.CATEGORIES)
    assert set(S.CARD_ORDER) == set(S.CATEGORIES)
    for r in (pts, S.points(data, E1, P(age=17, since=1), analysis, REL), S.points(data, EG, P(age=30), analysis, REL)):
        assert all(x["분류"] == S.CATEGORY[x["세부"]] for x in r["포인트"])
        assert sum(r["분류집계"].values()) == len(r["포인트"])
        # 한 담보는 한 분류에만 든다(관문 포인트는 담보가 없다)
        sids = [x["표준담보ID"] for x in r["포인트"] if x["표준담보ID"]]
        assert len(sids) == len(set(sids))
    assert pts["분류집계"] == {S.GATE_DIFF: 3, S.STRENGTH: 3, S.RELATED: 1, S.DEFEND: 1, S.REVISE: 3}
    # 뺀 포인트에도 분류가 붙는다
    assert all(x["분류"] == S.CATEGORY[x["세부"]] for x in pts["뺀포인트"])


def test_analysis_sentence_and_card_are_separate(pts):
    talk = ("있던데요", "맞습니다", "드리겠습니다", "않으시면")
    for x in pts["포인트"]:
        assert x["문장"] and x["카드답"]
        assert not any(w in x["문장"] for w in talk), x["문장"]          # 본문은 창구 말투를 쓰지 않는다
        if x["세부"] in ("Q1", "Q2", "Q3"):
            assert x["카드질문"] and x["카드답"] != x["문장"]
        elif x["세부"] == "G1":
            assert x["카드질문"] is None and "않으시면" in x["카드답"]
        else:                                                              # G2, G3, A1, A2는 분석 문장을 카드에도 쓴다
            assert x["카드질문"] is None and x["카드답"] == x["문장"]
        assert (x["원문대조글"] == S.SOURCE_CHECK_TEXT) == x["원문대조"] == (x["분류"] == S.GATE_DIFF)


# ---------- 단정 주의 목록 ----------
def design_book():
    """한화생명과 지급 형태만 다른 담보(1일당, 일수 한도가 다름)를 더한 자료."""
    b = Book()
    fill(b)
    b.t["hum_표준담보사전"].append(std("STD_CM_DAY", "공통보장", "시험 입원일당", "입원"))
    b.ben(E1, "STD_CM_DAY", limit="1일당 120일 한도")
    b.ben(H1, "STD_CM_DAY", limit="1일당 180일 한도")
    return b


def test_caution_lists_two_kinds():
    data = Data(design_book().t)
    analysis = I.analyze(data, REL)
    r = S.points(data, E1, P(age=30), analysis, REL)
    items = S.caution(data, E1, analysis, REL, pts=r)
    other = [x for x in items if x["종류"] == S.CAUTION_OTHER]
    pay = [x for x in items if x["종류"] == S.CAUTION_PAY]
    # (가) 상대가 대표 급부 밖에 조건이 다른 줄을 가져 A2, Q3에서 뺀 담보. 상대 하나마다 한 건
    assert [(x["표준담보ID"], x["상대종형ID"]) for x in other] == [("STD_CA_B", [S1]), ("STD_CM_D", [S1])]
    ca_b = other[0]
    assert ca_b["문장"] == ("암 나음은 삼성화재 7종(간편315)가 조건이 다른 특약을 함께 팔아 우열을 단정하지 않았습니다"
                           "(대표 급부 밖에 조건이 다른 급부 1개).")
    assert [e["구분"] for e in ca_b["근거"]] == ["대표", "대표", "대표 밖"]
    assert [e["종형ID"] for e in ca_b["근거"]] == [E1, S1, S1] and all(isinstance(e["쪽"], int) for e in ca_b["근거"])
    assert ca_b["대표밖줄"] == {S1: {"기준": 0, "상대": 1}}
    # 같은 담보를 한화생명과 견준 조건 나음은 본문에 남고, 패널이 함께 보일 수 있게 포인트ID를 단다
    assert ca_b["같은담보포인트"] == [by_sid(r, "STD_CA_B")["포인트ID"]]
    assert "판정" not in ca_b and "세부" not in ca_b                       # 대표끼리의 판정은 싣지 않는다
    # (나) 지급 형태가 달라 우열을 매기지 않은 담보. 양쪽 지급 형태를 그대로 적는다
    assert [x["표준담보ID"] for x in pay] == ["STD_CM_DAY"]
    assert pay[0]["문장"] == ("시험 입원일당은 지급 형태가 달라 우열을 매기지 않았습니다. 우체국 1종(간편가입315)는 "
                             "1일당(120일 한도), 한화생명 간편가입형(1년)은 1일당(180일 한도)입니다.")
    assert pay[0]["우리지급형태"] == "1일당(120일 한도)" and pay[0]["상대지급형태"] == {H1: "1일당(180일 한도)"}
    assert [e["종형ID"] for e in pay[0]["근거"]] == [E1, H1]
    # 지급 형태 다름은 조건 열위로 세지 않는다
    assert "STD_CM_DAY" not in {x["표준담보ID"] for x in r["포인트"]}
    # 검토 대기로 뺀 것(모름)은 단정 주의가 아니다
    assert not {"STD_CM_PEND", "STD_CA_H"} & {x["표준담보ID"] for x in items}
    assert pay[0]["같은상대조건포인트"] == []


def test_condition_gap_and_pay_form_on_the_same_pair_do_not_contradict():
    """같은 담보, 같은 상대에서 감액은 못하고 지급 형태는 다른 경우(점검 결함 5).

    조건 열위 문장에는 우열을 매기지 않은 지급 형태를 적지 않고, 단정 주의 문장은 지급 형태로만 범위를 좁혀 조건 열위 항목을 가리킨다.
    """
    b = Book()
    fill(b)
    b.t["hum_표준담보사전"].append(std("STD_CM_DAY", "공통보장", "시험 입원일당", "입원"))
    b.ben(E1, "STD_CM_DAY", red=(12, 0.5), limit="1일당 120일 한도")
    b.ben(H1, "STD_CM_DAY", limit="1일당 180일 한도")
    data = Data(b.t)
    r = S.points(data, E1, P(age=30), None, REL)
    q3 = by_sid(r, "STD_CM_DAY")
    assert (q3["세부"], q3["분류"], q3["비교종형ID"]) == ("Q3", S.DEFEND, [H1])
    assert q3["문장"] == ("시험 입원일당은 우체국 1종(간편가입315)가 1년까지 보험금의 50% 지급이고, 한화생명 간편가입형(1년)은 "
                         "감액 없음입니다. 1년이 지나면 둘 다 보험금 전액을 지급합니다.")
    assert "지급 형태" not in q3["카드답"] and q3["견준항목"] == ["감액"]
    pay = [x for x in S.caution(data, E1, None, REL, pts=r) if x["종류"] == S.CAUTION_PAY]
    assert [x["표준담보ID"] for x in pay] == ["STD_CM_DAY"]
    assert pay[0]["문장"] == ("시험 입원일당의 지급 형태는 서로 달라 우열을 매기지 않았습니다. 우체국 1종(간편가입315)는 "
                             "1일당(120일 한도), 한화생명 간편가입형(1년)은 1일당(180일 한도)입니다. "
                             "한화생명 간편가입형(1년)과 견준 감액 조건은 조건 열위 방어에 따로 적었습니다.")
    assert pay[0]["같은상대조건포인트"] == [q3["포인트ID"]]


# ---------- 개정 검토 목록 ----------
def test_revision_candidates_fold_by_middle_class(pts, data):
    groups = S.revision_candidates(data, pts)
    assert [(g["대분류"], g["중분류"], g["담보수"], g["좁은담보만수"]) for g in groups] == [
        ("암보장", "암시험", 1, 0), ("공통보장", "공통시험", 2, 1)]
    swap, wide = groups[1]["담보"]
    assert (swap["표준담보ID"], wide["표준담보ID"]) == ("STD_CM_SWAP", "STD_CM_WIDE")
    assert wide["우리상태"] == "좁은 담보만: 좁은 입원" and swap["우리상태"] == "없음"
    assert wide["가진상대수"] == 2 and wide["가진상대"] == ["한화생명", "삼성화재"] and wide["가진종형ID"] == [H1, S1]
    # 근거는 우리 좁은 담보와 상대가 가진 담보의 쪽이다
    assert [e["종형ID"] for e in wide["근거"]] == [E1, H1, S1] and all(e["쪽"] for e in wide["근거"])
    assert sum(g["담보수"] for g in groups) == pts["분류집계"][S.REVISE]


# ---------- 치료 여정 격자 ----------
def test_journey_counts_confirmed_holdings(data, analysis):
    grid = S.journey(data, E1, None, analysis, REL)
    assert grid["행"] == ["암보장", "뇌혈관보장", "심장보장", "공통보장"] and grid["열"] == list(S.JOURNEY_TYPES)
    ours, hanwha, samsung = grid["종형"]
    assert (ours["종형ID"], hanwha["종형ID"], samsung["종형ID"]) == (E1, H1, S1)
    assert ours["칸"]["암보장"] == {"진단": 2, "수술": 0, "치료": 1, "입원": 0, "통원": 0}
    assert ours["칸"]["공통보장"] == {"진단": 1, "수술": 1, "치료": 0, "입원": 1, "통원": 0}
    assert ours["합계"] == {"진단": 4, "수술": 1, "치료": 1, "입원": 2, "통원": 0} and ours["전체"] == 8
    # 매핑 대기 급부만 있는 담보(STD_CM_PEND)는 세지 않는다
    assert "STD_CM_PEND" not in ours["담보"]["공통보장"]["진단"]
    assert hanwha["합계"] == {"진단": 6, "수술": 0, "치료": 1, "입원": 1, "통원": 0}
    assert sum(hanwha["합계"].values()) == hanwha["전체"]


# ---------- 한도 표 ----------
def test_limit_steps_for_selling_home_variants():
    b = Book()
    fill(b)
    # 우체국 1종의 가입조건을 두 구간(한도 다름)으로 나눈다
    b.t["sys_가입조건"] = [r for r in b.t["sys_가입조건"] if r["종형ID"] != E1] + [
        row("sys_가입조건", 조건행ID=f"{E1}_D0", 종형ID=E1, 보험기간구분="20년", 납입기간구분="20년", 최저가입나이=20,
            최고가입나이=65, 구간최대가입금액만원=4000),
        row("sys_가입조건", 조건행ID=f"{E1}_D1", 종형ID=E1, 보험기간구분="20년", 납입기간구분="20년", 최저가입나이=66,
            최고가입나이=80, 구간최대가입금액만원=2000)]
    rows = S.limit_steps(Data(b.t))
    assert [r["종형ID"] for r in rows] == [E1, E5, EG]
    one = rows[0]
    assert one["이름"] == "1종(간편가입315)" and one["심사"] == "간편심사" and one["성별같음"]
    assert one["구간"]["M"] == [{"lo": 20, "hi": 65, "max": 4000, "pend": False}, {"lo": 66, "hi": 80, "max": 2000, "pend": False}]
    assert rows[2]["구간"]["M"] == [{"lo": 15, "hi": 65, "max": 4000, "pend": False}]


# ---------- 보류 요약 ----------
def test_pending_summary_by_major_class():
    b = Book()
    fill(b)
    b.ben(E1, "STD_BR_C", state="대기")          # 우리 쪽 매핑 대기: 뇌 조건의 두 쌍을 뺀다
    b.ben(H1, "STD_CA_B", logged=True)            # 한화생명 쪽 작업 로그 대기: 암 나음의 한 쌍을 뺀다
    data = Data(b.t)
    s = S.pending_summary(data, E1, None, REL)
    assert (s["공통담보쌍"], s["뺀쌍"], s["견준쌍"]) == (7, 3, 4)
    assert s["대분류"] == [
        {"대분류": "암보장", "공통담보쌍": 4, "뺀쌍": 1, "견준쌍": 3, "상대별": {H1: 1, S1: 0}},
        {"대분류": "뇌혈관보장", "공통담보쌍": 2, "뺀쌍": 2, "견준쌍": 0, "상대별": {H1: 1, S1: 1}},
        {"대분류": "공통보장", "공통담보쌍": 1, "뺀쌍": 0, "견준쌍": 1, "상대별": {H1: 0, S1: 0}},
    ]
    assert s["사유별"] == {"매핑 대기": 2, "작업 로그 대기": 1}
    assert sum(r["공통담보쌍"] for r in s["대분류"]) == s["공통담보쌍"]
    # 브리핑 (라)는 견준 쌍(공통 담보에서 검토 대기를 뺀 것)과 기준 종형 전체의 보유 수를 두 문장으로 가른다(점검 결함 2)
    line = S.briefing(data, E1, P(age=30), None, REL)[3]
    assert line["문장"].startswith("공통 담보 7쌍 가운데 검토 대기 3쌍을 빼고 4쌍을 견줬습니다. "
                                 "우체국 1종(간편가입315)가 가진 담보는 모두 8개(진단 4, 수술 1, 치료 1, 입원 2, 통원 0)이고, ")
    assert (line["값"]["공통담보쌍"], line["값"]["뺀비교쌍"], line["값"]["견준쌍"]) == (7, 3, 4)


# ---------- 먼저 보일 것 ----------
def fake(code, score, sid, brief=True):
    return {"세부": code, "분류": S.CATEGORY[code], "점수": score, "표준담보ID": sid, "브리핑": brief}


def test_pick_puts_one_per_detail_first_then_fills_by_score():
    rows = [fake("Q2", 29, "a"), fake("Q2", 28, "b"), fake("Q3", 20, "c"), fake("Q1", 19, "d"), fake("Q3", 18, "e"),
            fake("A2", 40, "z", brief=False)]
    # 세부마다 1건(Q1 d, Q3 c, Q2 a) 뒤 남는 한 자리는 점수순(Q2 b). 브리핑에서 빼는 포인트(z)는 넣지 않는다
    assert [x["표준담보ID"] for x in S.pick(rows, 4)] == ["d", "c", "a", "b"]
    # 카드는 조건 열위와 관련 담보 안내를 개정 검토 후보보다 먼저 채우고 앞에 둔다
    assert [x["표준담보ID"] for x in S.pick(rows, 4, for_card=True)] == ["c", "e", "d", "a"]
    # 자리가 세부 수보다 적으면 앞 차례의 세부가 먼저 들어간다
    assert [x["표준담보ID"] for x in S.pick(rows, 2)] == ["d", "c"]
    assert [x["표준담보ID"] for x in S.pick(rows, 2, for_card=True)] == ["c", "d"]
    assert S.pick([], 4) == [] and len(S.pick(rows, 10)) == 5


def test_pick_on_points_keeps_one_of_each_detail(pts):
    picked = S.pick(pts["포인트"], 6)
    assert sorted(x["세부"] for x in picked) == sorted(["G1", "G3", "A1", "Q1", "Q3", "Q2"])
    assert [x["세부"] for x in S.pick(pts["포인트"], 3)] == ["G1", "G3", "A1"]


# ---------- 지도 칸의 이름 ----------
EN = "EPOST_EN_aaaaaa"
NONRENEW_GENERAL = (EN, "EPOST", "단일", "일반심사", "일반", (None,) * 5, "비갱신", "표준형", "2026-06-17", [(15, 65)])


def test_map_cell_labels_notes_and_closed_reasons(data, analysis):
    m = S.segment_map(data, "M", None, analysis, REL)
    cells = m["칸"]
    label = [[x["라벨"] for x in line] for line in cells]
    assert label[0] == ["간편 모두 닫힘"] * 3 and label[3] == ["간편 모두 닫힘", "우리 간편만 열림", "우리 간편만 열림"]
    assert label[1] == ["우리 간편 닫힘", "함께 열림", "함께 열림"]
    # 라벨은 간편심사 종형만 본다. 15~19세 이력 없음 칸만 안쪽 분류(함께 열림. 일반심사 4종이 열림)와 라벨이 갈린다
    split = [(i, j) for i, line in enumerate(cells) for j, x in enumerate(line) if x["라벨"] != S.LABELS[x["분류"]]]
    assert split == [(2, 0), (5, 0)] and label[2][0] == label[5][0] == "우리 간편 닫힘"
    # 15~19세 입원 3개월~1년 전: 우리 간편은 나이와 고지 질문으로 닫히고 4종(일반)이 심사로 확인
    assert (cells[0][0]["보조"], cells[0][0]["닫힌사유"]) == ("일반심사 확인", ["나이", "고지 질문"])
    assert (cells[0][1]["보조"], cells[0][1]["닫힌사유"]) == ("일반심사 확인", ["고지 질문"])
    # 66~80세는 4종(15~65세)도 나이로 닫혀 일반심사로 확인할 수 없다
    assert (cells[0][2]["보조"], cells[0][2]["닫힌사유"]) == ("", ["고지 질문"])
    # 15~19세 입원 1~5년 전: 1종은 질문을 넘지만 나이로 닫히고, 3종은 질문에 걸린다
    assert (cells[1][0]["보조"], cells[1][0]["닫힌사유"]) == ("일반심사 확인", ["나이", "고지 질문"])
    # 열린 칸에는 보조와 닫힌 사유가 없다(우열 판정어도 없다)
    for x in (cells[3][1], cells[2][1]):
        assert (x["보조"], x["닫힌사유"]) == ("", [])
    assert not any(w in x["라벨"] for line in cells for x in line for w in ("나음", "못함", "유리", "불리"))


def test_nonrenewal_filter_closes_for_lack_of_a_simple_variant(data, analysis):
    # 우리 비갱신 종형이 없으면 자료 없음이고, 닫힌 까닭은 비갱신 간편 종형이 없어서다
    out = S.cell(data, P(age=30, since=1, renewal="비갱신"), analysis, REL)
    assert (out["라벨"], out["보조"], out["닫힌사유"]) == ("자료 없음", "", ["비갱신 간편 종형 없음"])
    # 우리 비갱신 일반심사 종형(단일)이 있으면: 이력이 있는 칸은 우리 간편 닫힘이고 일반심사로 확인, 닫힌 까닭은 나이가 아니다
    d = Data(Book(extra=[NONRENEW_GENERAL]).t)
    m = S.segment_map(d, "M", "비갱신", None, REL)
    assert m["열"] == [{"lo": 15, "hi": 65}, {"lo": 66, "hi": 80}]
    hist = m["칸"][1]                                    # 입원 1~5년 전
    assert [(x["라벨"], x["보조"], x["닫힌사유"]) for x in hist] == [
        ("우리 간편 닫힘", "일반심사 확인", ["비갱신 간편 종형 없음"]),
        ("우리 간편 닫힘", "", ["비갱신 간편 종형 없음"])]          # 66세부터는 단일도 나이로 닫히지만 사유는 같다
    # 이력 없는 칸도 우리 비갱신 간편 종형이 없어 우리 간편 닫힘이다(일반심사 단일만 열린다. 점검 결함 1)
    assert (m["칸"][2][0]["라벨"], m["칸"][2][0]["보조"], m["칸"][2][0]["닫힌사유"]) == (
        "우리 간편 닫힘", "일반심사 확인", ["비갱신 간편 종형 없음"])


def test_map_label_reads_only_simple_variants(data, analysis):
    """우리 간편이 닫히고 일반심사 종형만 열린 칸은 함께 열림이 아니라 우리 간편 닫힘이다(점검 결함 1).

    15~19세 이력 없음: 우리 간편(20세부터)은 나이로 닫히고 일반심사 4종(15~65세)만 열린다. 안쪽 분류는 회사 상태로 보아 함께 열림이다.
    """
    out = S.cell(data, P(age=17), analysis, REL)
    assert out["분류"] == S.BOTH_OPEN
    assert (out["라벨"], out["보조"], out["닫힌사유"]) == ("우리 간편 닫힘", "일반심사 확인", ["나이"])
    # 우리 비갱신 일반심사 종형(단일)만 열린 칸: 닫힌 까닭은 비갱신 간편 종형이 없어서다
    d = Data(Book(extra=[NONRENEW_GENERAL]).t)
    x = S.cell(d, P(age=30, renewal="비갱신"), None, REL)
    assert (x["라벨"], x["보조"], x["닫힌사유"]) == ("우리 간편 닫힘", "일반심사 확인", ["비갱신 간편 종형 없음"])
    # 지도 세 장의 모든 칸(합친 열은 양 끝 나이): 자료 없음이 아니면 우리 간편이 열린 칸만 열림 라벨이고,
    # 우리 간편이 열리지 않은 칸은 모두 닫힌 사유가 있다
    opened = (S.LABELS[S.ONLY_OPEN], S.LABELS[S.BOTH_OPEN])
    for renewal in (None, "갱신", "비갱신"):
        m = S.segment_map(d, "M", renewal, None, REL)
        for r, line in zip(m["행"], m["칸"]):
            for c, x in zip(m["열"], line):
                for age in (c["lo"], c["hi"]):
                    p = P(age=age, sex="M", since=r["since"], surgery_only=r["종류"] == S.SURGERY_ONLY, renewal=renewal)
                    home = S.gate(d, p)["회사"].get("EPOST")
                    simple_open = bool(home) and any(
                        y["상태"] == S.OPEN and d.variants[y["종형ID"]]["심사유형"] == S.SIMPLE for y in home["종형"])
                    if x["라벨"] != S.LABELS[S.NO_DATA]:
                        assert (x["라벨"] in opened) == simple_open, (renewal, r["이름"], c, x["라벨"])
                    assert bool(x["닫힌사유"]) != simple_open, (renewal, r["이름"], c, x["닫힌사유"])


def test_cell_gate_points_stay_inside_the_renewal_filter(data, analysis):
    """갱신 거르개 지도 칸의 관문 포인트는 거르개 안의 상대와만 견준다(점검 결함 3)."""
    ctx = S._Ctx(data, analysis, REL)
    m = S.segment_map(data, "M", "갱신", None, ctx=ctx)
    seen = 0
    for r in m["행"]:
        for c in m["열"]:
            p = P(age=c["lo"], sex="M", since=r["since"], surgery_only=r["종류"] == S.SURGERY_ONLY, renewal="갱신")
            found, _ = S.cell_gate_points(ctx, p)
            for x in found:
                seen += 1
                assert all(data.variants[v]["갱신유형"] == "갱신" for v in x["비교종형ID"]), x["문장"]
    assert seen
    # 우리 간편만 열린 칸의 G1은 거르개 안의 삼성화재만 적는다(비갱신 한화생명은 적지 않는다)
    found, base = S.cell_gate_points(ctx, P(age=30, sex="M", since=0.25, surgery_only=True, renewal="갱신"))
    g1 = [x for x in found if x["세부"] == "G1"]
    assert base == E5 and len(g1) == 1 and g1[0]["비교종형ID"] == [S1] and "한화생명" not in g1[0]["문장"]
    # 거르개가 없으면 지금처럼 기준 종형의 짝(한화생명, 삼성화재)과 견준다
    found, _ = S.cell_gate_points(ctx, P(age=30, sex="M", since=0.25, surgery_only=True))
    assert next(x for x in found if x["세부"] == "G1")["비교종형ID"] == [H1, S1]


def test_cell_counts_use_the_five_categories(data, analysis):
    """칸의 인사이트 수는 다섯 분류 이름으로 낸다. 관문 차이는 그 칸의 관문 포인트 수다(점검 결함 4)."""
    ctx = S._Ctx(data, analysis, REL)
    p = P(age=30, since=1)
    out = S.cell(data, p, None, ctx=ctx)
    assert list(out["분류수"]) == [*S.CATEGORIES, S.PENDING_COUNT]
    # 대표(1종)와 상대 대표가 1종의 짝과 같으므로 1종의 분류집계와 같다
    assert (out["대표"], list(out["상대대표"].values())) == (E1, [H1, S1])
    assert {c: out["분류수"][c] for c in S.CATEGORIES} == S.points(data, E1, p, None, ctx=ctx)["분류집계"]
    assert out["분류수"][S.GATE_DIFF] == len(S.cell_gate_points(ctx, p)[0]) == 2
    assert out["분류수"][S.PENDING_COUNT] == out["수"]["대기"]
    # 견줄 상대가 없는 칸도 관문 차이는 센다. 시사점에서 오는 수는 비운다(None)
    lone = S.cell(data, P(age=30, since=0.25, surgery_only=True), None, ctx=ctx)
    assert lone["수"] is None and lone["분류수"][S.GATE_DIFF] == 1
    assert all(lone["분류수"][c] is None for c in (S.STRENGTH, S.RELATED, S.DEFEND, S.REVISE, S.PENDING_COUNT))


# ---------- 브리핑 다섯 줄 ----------
def test_briefing_five_lines(data, analysis):
    lines = S.briefing(data, E1, P(age=30), analysis, REL)
    assert [x["줄"] for x in lines] == ["가", "나", "다", "라", "마"]
    assert [x["범위"] for x in lines] == [S.SCOPE_ALL, S.SCOPE_ALL, S.SCOPE_BASE, S.SCOPE_BASE, S.SCOPE_BASE]
    assert [x["갈곳"] for x in lines] == [S.TAB_MARKET, S.TAB_MARKET, S.TAB_GATE, S.TAB_COMPARE, S.TAB_INSIGHT]
    text = {x["줄"]: x["문장"] for x in lines}
    # 15~19세 이력 없음 두 칸은 일반심사 4종만 열려 함께 열림이 아니라 우리 간편 닫힘으로 센다(점검 결함 1)
    assert text["가"] == ("고객군 18칸 가운데 우리 간편만 열리는 곳은 2칸(수술만 3개월~1년 전 20~80세), 함께 열리는 곳은 8칸, "
                         "우리 간편이 닫혀 일반심사로 확인할 곳은 4칸입니다.")
    assert text["나"] == "견줄 우체국 직전 개정 자료는 없고, 최근 모은 시장 소식은 없습니다."
    assert text["다"] == ("기준 종형 우체국 1종(간편가입315)의 가입나이는 20~80세(지금 조건의 주계약 한도 4,000만원)이고, "
                         "맞붙는 상대와 고지 질문이 다른 곳은 2건, 갱신이나 환급 구조가 다른 상대는 2곳입니다.")
    assert lines[2]["원문대조글"] == S.SOURCE_CHECK_TEXT
    # 견준 쌍과 보유 수를 두 문장으로 가른다. 보유 수는 공통 담보 쌍 안이 아니라 기준 종형 전체다(점검 결함 2)
    assert text["라"] == ("공통 담보 7쌍을 모두 견줬습니다. 우체국 1종(간편가입315)가 가진 담보는 모두 8개(진단 4, 수술 1, 치료 1, "
                         "입원 2, 통원 0)이고, 상대가 조건이 다른 특약을 함께 팔아 우열을 단정하지 않은 비교는 2건입니다.")
    assert lines[3]["값"]["보유수"] == 8 and lines[3]["값"]["진단수"] == 4
    assert text["마"] == ("지금 기준에서 앞세울 강점 3건(심장 입원, 종별 수술비(최고 종 기준) 등), 관련 담보 안내 1건, "
                         "조건 열위 방어 1건, 개정 검토 후보 3건이 나왔습니다.")
    assert lines[0]["값"]["라벨별"]["간편 모두 닫힘"] == 4


def test_briefing_zero_cases_do_not_raise():
    # 상대가 없고 급부도 없는 자료: 0건 틀로 가른다
    d = Data(Book(skip=(H1, HG, S1, SA, SB)).t)
    text = {x["줄"]: x["문장"] for x in S.briefing(d, E1, P(age=30), None, REL)}
    assert text["가"] == ("고객군 18칸 가운데 우리 간편만 열리는 곳은 없고, 함께 열리는 곳은 없고, "
                         "우리 간편이 닫혀 일반심사로 확인할 곳은 없습니다.")
    assert text["다"] == ("기준 종형 우체국 1종(간편가입315)의 가입나이는 20~80세(지금 조건의 주계약 한도 4,000만원)이고, "
                         "맞붙는 상대 종형은 없습니다.")
    assert text["라"] == ("견준 공통 담보는 없습니다. 우체국 1종(간편가입315)가 가진 담보는 없고, "
                         "상대가 조건이 다른 특약을 함께 팔아 우열을 단정하지 않은 비교는 없습니다.")
    assert text["마"] == "지금 기준에서 나온 영업 인사이트는 없습니다."
    # 나이 밖, 일반심사 기준 종형, 가입조건 자료 없음
    full = Data(Book().t)
    assert S.briefing(full, E1, P(age=17), None, REL)[2]["문장"].startswith(
        "기준 종형 우체국 1종(간편가입315)의 가입나이는 20~80세(지금 조건의 17세는 가입나이 밖)이고")
    assert "일반심사 종형이라 간편 고지 질문은 견주지 않았고" in S.briefing(full, EG, P(age=30), None, REL)[2]["문장"]
    b = Book(skip=(H1, HG, S1, SA, SB))
    b.t["sys_가입조건"] = []
    bare = {x["줄"]: x["문장"] for x in S.briefing(Data(b.t), E1, P(age=30), None, REL)}
    assert bare["가"] == "고객군 지도를 그릴 가입조건 자료가 없습니다."
    assert bare["다"].startswith("기준 종형 우체국 1종(간편가입315)의 가입나이 자료는 없고")
    # 공통 담보가 모두 검토 대기일 때
    held = S._line_position({"범위": {"비교쌍": 3, "뺀비교쌍": 3}},
                            {"종형": [{"합계": dict.fromkeys(S.JOURNEY_TYPES, 1), "전체": 6, "기타": 1}]}, [], "1종")
    assert held["문장"] == ("공통 담보 3쌍이 모두 검토 대기라 견준 쌍은 없습니다. 우체국 1종이 가진 담보는 모두 6개(진단 1, 수술 1, "
                           "치료 1, 입원 1, 통원 1, 기타 1)이고, 상대가 조건이 다른 특약을 함께 팔아 우열을 단정하지 않은 비교는 없습니다.")
    # 앞세울 강점만 없을 때
    only = S._line_insight({"분류집계": {S.GATE_DIFF: 0, S.STRENGTH: 0, S.RELATED: 2, S.DEFEND: 0, S.REVISE: 1}, "포인트": []})
    assert only["문장"] == "지금 기준에서 앞세울 강점은 없고, 관련 담보 안내 2건, 조건 열위 방어 0건, 개정 검토 후보 1건이 나왔습니다."


def revision_book(summaries=("시험 소식", "시험 소식"), media=(None, None)):
    """직전 개정판(EO)과 지금 개정판(E1)이 있는 우체국 자료, 시장 소식 둘(핵심요약과 매체명은 summaries, media)."""
    eo = ("EPOST_EO_aaaaaa", "EPOST", "1종(간편가입315)", "간편심사", "3.1.5", (3, 1, 5, False, 6), "갱신", "표준형",
          "2025-04-01", [(20, 80)])
    b = Book(skip=(E5, EG, HG, SA, SB), extra=[eo])
    b.t["hum_표준담보사전"] = [std(sid, *v) for sid, v in NAMES.items()]
    for v in b.t["sys_상품종형"]:
        if v["종형ID"] in (E1, eo[0]):
            v.update(종형계보키="EPOST_L|간편심사|3.1.5", 개정판ID="R2" if v["종형ID"] == E1 else "R1")
        if v["종형ID"] == eo[0]:
            v["판매종료일"] = "2026-06-16"
    b.ben(E1, "STD_CM_TOP", pay=1000, name="수술급부")
    b.ben(eo[0], "STD_CM_TOP", pay=500, name="수술급부")           # 변경(지급액)
    b.ben(E1, "STD_CA_GAP", name="새급부")                          # 신설
    b.ben(eo[0], "STD_HT_ONLY", name="옛급부")                      # 종료
    b.t["hum_기준값"] = [row("hum_기준값", 기준키="기사선별_통과", 수치값=0.7)]
    b.t["sys_시장동향"] = [
        row("sys_시장동향", 동향ID=f"T{i}", 수집주차="2026-W47", 발표일자="2026-11-18", 기관코드="HANWHALIFE", 분류유형="신담보출시",
            관련표준담보ID=sid, 핵심요약=summaries[i], 매체명=media[i], 출처URL=f"https://example.invalid/{i}", 수집경로="시험",
            판정확률=0.9)
        for i, sid in enumerate(["STD_CM_TOP", None])]
    return Data(b.t, {"snapshot_at": STAMP})


def test_revision_summary_and_market_line():
    data = revision_book()
    rev = S.revision_summary(data)
    assert rev["수"] == {"신설": 1, "변경": 1, "종료": 1, "전체": 3}
    assert [(x["종류"], x["열쇠"], x["항목"]) for x in rev["담보"]] == [
        ("신설", "STD_CA_GAP", ["급부 추가"]), ("변경", "STD_CM_TOP", ["지급액", "최대 가입 시 지급액"]),
        ("종료", "STD_HT_ONLY", ["급부 삭제"])]
    assert rev["짝"] == [{"전": "EPOST_EO_aaaaaa", "후": E1, "신설": 1, "변경": 1, "종료": 1}]
    news = S.news_summary(data)
    assert (news["건수"], news["연결"], news["주차"]) == (2, 1, "2026-W47")
    line = S.briefing(data, E1, P(age=30), None, REL)[1]
    assert line["문장"] == ("우체국 직전 개정과 견주어 달라진 담보는 3건(신설 1, 변경 1, 종료 1)이고, "
                           "최근 모은 시장 소식은 2건(표준담보에 이어진 것 1건)입니다.")
    assert (line["범위"], line["구역"]) == (S.SCOPE_ALL, "개정과 시장")


def test_news_summaries_are_marked_as_quotes():
    """시장 소식 요약은 보도를 옮긴 글이라 금지어 검사 대신 인용으로 표시한다(점검 결함 6). 문구는 지어낸 것이다."""
    data = revision_book(summaries=("시험사가 업계 최초로 시험 특약을 내놓았다", "시험사가 보험료를 낮춘 시험 상품을 냈다"),
                         media=("시험일보", None))
    news = S.news_summary(data)
    assert news["인용안내"] == S.NEWS_QUOTE_NOTE and not S.forbidden_in(S.NEWS_QUOTE_NOTE)
    by_url = {it["출처URL"]: it for it in news["소식"]}
    first, second = by_url["https://example.invalid/0"], by_url["https://example.invalid/1"]
    assert all(it["인용"] is True for it in news["소식"])
    assert (first["출처표시"], first["주의표현"]) == ("시험일보 보도 요약", ["업계", "최초"])
    assert (second["출처표시"], second["주의표현"]) == ("보도 요약", ["보험료"])
    # 요약은 바꾸지 않고 그대로 싣는다
    assert first["요약"] == "시험사가 업계 최초로 시험 특약을 내놓았다"
    out = S.export(data, None, REL)
    assert out["시장소식"]["인용안내"] == S.NEWS_QUOTE_NOTE
    assert all(it["인용"] for it in out["시장소식"]["소식"])


# ---------- 내보내기 ----------
def data_strings(data):
    """금지어 검사에서 뺄 자료 값: 표준담보명, 회사명, 공시상품명, 종형명, 급부명, 지급 형태 꼬리표."""
    out = {s["표준담보명"] for s in data.std.values()}
    for vid, v in data.variants.items():
        out |= {data.org_name(v["기관코드"]), str(v.get("공시상품명") or ""), str(v.get("종형명") or ""), S.full_name(data, vid)}
    for b in data.benefits.values():
        out.add(str(b.get("원시급부명") or ""))
        out |= {t.label for t in I.pay_tags(b.get("지급횟수제한"))}
    return sorted((s for s in out if s), key=len, reverse=True)


def generated_texts(out):
    """내보내기에서 코드가 만든 글: 포인트의 문장과 카드 문답, 브리핑, 단정 주의, 범위.

    시장 소식의 요약(시장소식.소식[].요약)은 보도를 옮긴 글이라 여기서 세지 않는다. 인용 표시와 주의표현이 붙는지는
    quote_misses로 따로 본다.
    """
    for x in out["포인트"].values():
        yield from (t for t in (x["문장"], x["카드질문"], x["카드답"]) if t)
    for b in out["기준별"].values():
        yield from (x["문장"] for x in b["브리핑"])
        yield from (x["문장"] for x in b["단정주의"])
        if b["범위"]["문장"]:
            yield b["범위"]["문장"]
    yield from out["글"]
    yield out["시장소식"]["인용안내"]


def forbidden_hits(data, out):
    names = data_strings(data)
    hits = []
    for text in generated_texts(out):
        rest = text
        for name in names:
            rest = rest.replace(name, " ")
        hits += [(w, text) for w in S.forbidden_in(rest)]
    return hits


def quote_misses(out):
    """시장 소식 가운데 인용 표시가 없거나, 요약에 든 금지어와 보험료 글이 주의표현에 빠진 것."""
    misses = []
    for it in out["시장소식"]["소식"]:
        text = str(it["요약"] or "")
        want = S.forbidden_in(text) + (["보험료"] if "보험료" in text else [])
        if it.get("인용") is not True or not it.get("출처표시") or it.get("주의표현") != want:
            misses.append(it["동향ID"])
    return misses


def test_export_shape_and_no_forbidden_words(data, analysis):
    out = S.export(data, analysis, REL)
    json.dumps(out, ensure_ascii=False)                    # 그대로 JSON으로 쓸 수 있다
    assert {"자료시각", "고지", "기준종형", "종형", "표준담보", "기준별", "지도", "한도표", "개정변동", "시장소식", "포인트", "글"} <= set(out)
    assert out["고지"] == "공모전 시연용 화면이며 영업 자료가 아닙니다"
    assert [b["종형ID"] for b in out["기준종형"]] == [E1, E5, EG]
    assert {k: out["기준종형"][0][k] for k in ("이름", "심사", "갱신", "환급")} == {
        "이름": "1종(간편가입315)", "심사": "간편심사", "갱신": "갱신", "환급": "표준형"}
    for vid, b in out["기준별"].items():
        assert {"맞붙는종형", "범위", "포인트", "뺀포인트", "단정주의", "개정검토", "치료여정", "보류요약", "브리핑", "먼저"} <= set(b)
        assert [x["줄"] for x in b["브리핑"]] == ["가", "나", "다", "라", "마"]
        assert all(p in out["포인트"] for p in b["포인트"] + b["먼저"]["브리핑"] + b["먼저"]["카드"])
        assert set(b["먼저"]["카드"]) <= set(b["포인트"])
        assert all(d["포인트ID"] in out["포인트"] for g in b["개정검토"] for d in g["담보"])
        assert all(isinstance(c["머리말"], int) and c["머리말"] < len(out["글"]) for c in b["단정주의"])
    for x in out["포인트"].values():
        assert {"분류", "세부", "문장", "카드질문", "카드답", "머리말", "근거", "점수", "목적", "구조다름", "원문대조"} <= set(x)
        assert out["글"][x["머리말"]].startswith("수집한 ")
        assert all(v in out["종형"] for v in x["비교종형ID"])
    assert set(out["지도"]) == {"전체", "갱신", "비갱신"}
    whole = out["지도"]["전체"]
    assert sum(whole["라벨별"].values()) == len(whole["행"]) * len(whole["열"]) == 18
    for line in whole["칸"]:
        for c in line:
            assert {"라벨", "보조", "닫힌사유", "회사", "대표", "상대대표", "분류수", "자료없음", "관문포인트"} <= set(c)
            assert all(p in out["포인트"] for p in c["관문포인트"])
            # 칸의 인사이트 수는 다섯 분류 이름이고, 관문 차이는 그 칸의 관문 포인트 수다(점검 결함 4)
            assert list(c["분류수"]) == [*S.CATEGORIES, S.PENDING_COUNT]
            assert c["분류수"][S.GATE_DIFF] == len(c["관문포인트"])
    # 수술만 3개월~1년 전 20~65세(우리 간편만 열림): 그 칸의 관문 포인트에 G1이 있다
    only = whole["칸"][3][1]
    assert only["라벨"] == "우리 간편만 열림" and "G1" in [out["포인트"][p]["세부"] for p in only["관문포인트"]]
    # 입원 1~5년 전 15~19세(우리 간편 닫힘): 나이로만 닫힌 1종을 기준으로 G2를 낸다
    young = whole["칸"][1][0]
    assert young["관문기준"] == E1 and "G2" in [out["포인트"][p]["세부"] for p in young["관문포인트"]]
    # 같은 포인트는 한 번만 싣는다(G3는 종형 목록과 여러 칸에서 같은 포인트ID다)
    assert len(out["글"]) == len(set(out["글"]))
    assert forbidden_hits(data, out) == []


# ---------- 관문전용 종형과 모르는 상대 ----------
HZ = "HANWHALIFE_HZ_bbbbbb"
ZERO_YEAR = (HZ, "HANWHALIFE", "간편가입형(0년)", "간편심사", "3.0.5", (3, 0, 5, None, 7), "비갱신", UNPAID, "2026-10-01",
             [(15, 60), (61, 80)])


def gate_book():
    """한화생명에 입원과 수술의 기간 질문이 없는 관문전용 종형(간편가입형(0년))을 더한 자료. 급부는 모으지 않았다."""
    b = Book(extra=[ZERO_YEAR])
    next(v for v in b.t["sys_상품종형"] if v["종형ID"] == HZ)["비교역할구분"] = S.GATE_ROLE
    b.t["sys_특약"] = [r for r in b.t["sys_특약"] if r["특약ID"] != f"{HZ}_T"]      # 주계약 행만 있다
    fill(b)
    return b


@pytest.fixture()
def gated():
    return Data(gate_book().t)


@pytest.mark.parametrize("profile", [P(since=0.25), P(since=4), P(since=0.25, surgery_only=True)])
def test_question_hit_without_a_period_question(gated, profile):
    # 고지입원수술년수 0은 기간 질문이 없다는 뜻이라 이력이 있어도 해당 없음이다(수술 여부를 따지기 전에 본다)
    assert S.question_hit(gated.variants[HZ], profile) == S.Q_NONE
    blank = {**gated.variants[HZ], "고지입원수술년수": None}
    assert S.question_hit(blank, profile) == S.Q_NODATA                    # 빈칸은 지금처럼 자료 없음이다


@pytest.mark.parametrize("us, others, cls", [
    (S.OPEN, [S.CLOSED, None], S.NO_DATA),          # 모르는 상대가 열려 있을 수 있다
    (S.CLOSED, [S.CLOSED, None], S.NO_DATA),
    (S.OPEN, [None], S.NO_DATA),
    (S.OPEN, [S.OPEN, None], S.BOTH_OPEN),          # 열린 상대가 있으면 모르는 상대와 무관하다
    (S.CLOSED, [S.OPEN, None], S.ONLY_CLOSED),
    (S.OPEN, [S.CLOSED, S.CLOSED], S.ONLY_OPEN),
    (S.CLOSED, [S.CLOSED], S.ALL_CLOSED),
    (None, [S.OPEN], S.NO_DATA),
])
def test_unknown_peer_keeps_only_open_and_all_closed_out(us, others, cls):
    assert S._by_sides(us, others) == cls


def test_cell_with_an_unknown_peer_and_no_open_peer_is_no_data():
    # 한화생명 간편 종형이 없으면(일반심사만 있어 간편은 닫힘), 삼성화재 간편(나이 자료 없음)만 모르는 상대로 남는다
    d = Data(Book(skip=(H1,)).t)
    out = S.cell(d, P(age=30, since=1), None, REL)
    assert out["라벨"] == S.LABELS[S.NO_DATA] and out["자료없음"] == ["SAMSUNGFIRE"]
    assert "SAMSUNGFIRE" in S.simple_classify(d, S.gate(d, P(age=30, since=1)))[1]


def test_gate_only_variant_is_in_the_gate_but_not_in_reps_or_map_rows(gated, data):
    assert HZ in S.gate_targets(gated) and HZ not in S.targets(gated)
    assert S.since_cuts(gated) == S.since_cuts(data)                       # 0년이 지도 행의 경계에 끼지 않는다
    m = S.segment_map(gated, "M", None, None, REL)
    plain = S.segment_map(data, "M", None, None, REL)
    assert m["행"] == plain["행"] and len(m["행"]) == 6 and m["열"] == plain["열"]
    for line in m["칸"]:
        for x in line:
            assert x["대표"] != HZ and HZ not in x["상대대표"].values()
    assert HZ not in I.base_variants(gated)[0] and HZ not in C.peers(gated, E1, I.base_variants(gated)[0])


def test_cell_open_only_through_a_gate_only_variant(gated, data):
    # 입원 3개월~1년 전: 우리 간편과 한화생명 1년, 삼성화재 315는 질문에 걸리고 한화생명 0년만 열린다
    before = S.cell(data, P(age=30, since=0.25), None, REL)
    out = S.cell(gated, P(age=30, since=0.25), None, REL)
    assert before["라벨"] == S.LABELS[S.ALL_CLOSED] and out["라벨"] == S.LABELS[S.ONLY_CLOSED]
    assert out["관문만수집"] == [{"기관코드": "HANWHALIFE", "종형ID": HZ, "이름": "한화생명 간편가입형(0년)",
                                "안내": "관문만 수집(담보 미수집)"}]
    assert out["열린종형"]["HANWHALIFE"] == [HZ] and out["대표"] is None and out["수"] is None
    # 수술만 3개월~1년 전: 우리만 열렸던 칸이 함께 열림이 되지만, 한화생명과는 담보를 견주지 않는다(대표가 없다)
    lone = S.cell(gated, P(age=30, since=0.25, surgery_only=True), None, REL)
    assert lone["라벨"] == S.LABELS[S.BOTH_OPEN] and lone["대표"] == E5 and lone["상대대표"] == {} and lone["수"] is None
    assert [y["종형ID"] for y in lone["관문만수집"]] == [HZ]
    # 정밀비교 종형도 열린 회사에는 적지 않는다
    assert S.cell(gated, P(age=30, since=1), None, REL)["관문만수집"] == []


def test_gate_points_name_the_gate_only_variant(gated):
    ctx = S._Ctx(gated, None, REL)
    found, base = S.cell_gate_points(ctx, P(age=30, sex="M", since=0.25))
    g2 = [x for x in found if x["세부"] == "G2"]
    assert base == E1 and len(g2) == 1 and g2[0]["비교종형ID"] == [HZ] and g2[0]["관문만수집"] is True
    assert g2[0]["문장"] == ("마지막 입원이 3개월~1년 전인 고객은 우체국 1종(간편가입315)의 고지 질문에 해당합니다. "
                            "한화생명 간편가입형(0년)은 입원과 수술의 기간 질문이 없습니다. 가입 여부는 청약 뒤 심사로 정해집니다.")
    assert g2[0]["머리말"].startswith("관문만 수집한 한화생명 시험건강보험 간편가입형(0년) 기준(2026-10-01, 담보 미수집)")
    # 나이로 닫힌 칸: 한화생명에서 열린 종형이 0년뿐이면 그 가입나이를 적는다
    found, base = S.cell_gate_points(ctx, P(age=17, sex="M", since=0.5, surgery_only=True))
    g2 = next(x for x in found if x["세부"] == "G2")
    assert base == E5 and g2["문장"] == ("17세는 우체국 3종(간편가입355)의 가입나이(20~80세) 밖입니다. "
                                        "한화생명 간편가입형(0년)은 15~80세를 받습니다.")
    # 간편이 모두 닫힌 칸은 지금처럼 관문 기준이 없다
    plain = S._Ctx(Data(Book().t), None, REL)
    assert S.cell_gate_points(plain, P(age=30, sex="M", since=0.25)) == ([], None)


def test_shorter_question_of_a_peer_company_is_a_g3_point(gated, data):
    r = S.points(gated, E1, P(age=30), None, REL)
    g3 = [x for x in r["포인트"] if x["세부"] == "G3"]
    short = [x for x in g3 if x["비교종형ID"] == [HZ]]
    assert len(short) == 1 and short[0]["관문만수집"] is True and short[0]["분류"] == S.GATE_DIFF
    assert short[0]["문장"] == ("한화생명은 입원과 수술의 기간 질문이 없는 간편가입형(0년)을 함께 팝니다. "
                               "이 종형은 고지 질문과 주계약 가입조건만 모았고 담보는 수집하지 않았습니다.")
    assert short[0]["머리말"].startswith("관문만 수집한 ")
    assert [x["비교종형ID"] for x in g3 if x not in short] == [x["비교종형ID"] for x in by_code(
        S.points(data, E1, P(age=30), None, REL), "G3")]                   # 짝과 견준 G3은 그대로다
    # 브리핑 (다)의 관문차이수는 맞붙는 상대와 견준 G3만 센다
    line = S.briefing(gated, E1, P(age=30), None, REL)[2]
    assert line["값"]["관문차이수"] == 2 and "고지 질문이 다른 곳은 2건" in line["문장"]
    # 짝의 기간이 더 짧지 않으면(우리 1년, 3.0.5만 짧다) 다른 종형은 적지 않는다
    assert not [x for x in by_code(S.points(data, E1, P(age=30), None, REL), "G3") if x.get("관문만수집")]


def test_new_gate_sentences_pass_the_forbidden_word_check(gated):
    for tid in ("G2_질문", "G2_상대_질문없음", "G3_질문없음", "G3_짧은", "G3_미수집", "머리말_관문"):
        assert S.forbidden_in(S._SLOT.sub(" ", S.TEMPLATES[tid])) == [], tid
    assert S.render("G3_짧은", {"상대회사": "한화생명", "상대기간": 1, "상대범위": "입원과 수술", "상대종형": "간편가입형(1년)"}) == \
        "한화생명은 1년 안의 입원과 수술을 묻는 간편가입형(1년)을 함께 팝니다."
    with pytest.raises(S.ForbiddenWordError):
        S.render("G2_질문", {"이력": "업계 최초로 마지막 입원이 3개월~1년 전", "우리종형": "1종", "상대문장": "가."})
    out = S.export(gated, None, REL)
    assert forbidden_hits(gated, out) == []
    texts = [x["문장"] for x in out["포인트"].values() if x.get("관문만수집")]
    assert texts and all(S.forbidden_in(t) == [] for t in texts)


def test_export_keeps_gate_only_variants_out_of_the_bases(gated):
    out = S.export(gated, None, REL)
    assert [b["종형ID"] for b in out["기준종형"]] == [E1, E5, EG]
    assert all(HZ not in b["맞붙는종형"] for b in out["기준별"].values())
    assert out["종형"][HZ]["비교역할"] == "관문전용"
    cells = [x for m in out["지도"].values() for line in m["칸"] for x in line]
    assert all("관문만수집" in x for x in cells) and any(x["관문만수집"] for x in cells)
    assert all(y["종형ID"] in out["종형"] for x in cells for y in x["관문만수집"])
    assert all(out["글"][x["머리말"]].startswith(("수집한 ", "관문만 수집한 ")) for x in out["포인트"].values())


def test_export_lists_every_open_variant_of_a_cell():
    # 정밀비교 종형 옆에서만 열리는 관문전용 종형(질문 기간 3년)도 칸의 열린종형에 있으므로 "종형"에 실려야 한다(점검 결함)
    three = ("HANWHALIFE_H3_bbbbbb", "HANWHALIFE", "간편가입형(3년)", "간편심사", "3.3.5", (3, 3, 5, True, 7), "비갱신", UNPAID,
             "2026-10-01", [(15, 60), (61, 80)])
    b = Book(extra=[ZERO_YEAR, three])
    for v in b.t["sys_상품종형"]:
        if v["종형ID"] in (HZ, three[0]):
            v["비교역할구분"] = S.GATE_ROLE
    b.t["sys_특약"] = [r for r in b.t["sys_특약"] if r["특약ID"] not in (f"{HZ}_T", f"{three[0]}_T")]
    fill(b)
    d = Data(b.t)
    out = S.export(d, None, REL)
    cells = [x for m in out["지도"].values() for line in m["칸"] for x in line]
    opened = {v for x in cells for ids in x["열린종형"].values() for v in ids}
    assert three[0] in opened and three[0] not in {y["종형ID"] for x in cells for y in x["관문만수집"]}
    assert opened <= set(out["종형"]), opened - set(out["종형"])
    assert out["종형"][three[0]]["비교역할"] == S.GATE_ROLE


def test_briefing_first_line_without_our_only_open_cells(gated):
    seg = S.segment_map(gated, "M", None, None, REL)
    line = S.briefing(gated, E1, P(age=30), None, REL, seg=seg)[0]
    assert line["값"]["우리간편만열림칸수"] == 0 and line["틀"][0] == "가_우리만_없음"
    labels = line["값"]["라벨별"]
    assert line["문장"] == (f"고객군 18칸 가운데 우리 간편만 열리는 곳은 없고, 함께 열리는 곳은 {labels['함께 열림']}칸, "
                           f"우리 간편이 닫혀 일반심사로 확인할 곳은 {line['값']['우리간편닫힘칸수']}칸입니다.")


# ---------- 실제 사본 ----------
@pytest.mark.skipif(not (SNAPSHOT / "sys_급부.jsonl").exists(), reason="사본 없음")
def test_real_snapshot_export_runs():
    data = load(SNAPSHOT)
    out = S.export(data)
    size = len(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    assert size < 600 * 1024, size
    assert forbidden_hits(data, out) == []
    assert quote_misses(out) == []
    for b in out["기준별"].values():
        assert [x["줄"] for x in b["브리핑"]] == ["가", "나", "다", "라", "마"] and all(x["문장"] for x in b["브리핑"])
        assert all(out["포인트"][p]["분류"] in S.CATEGORIES for p in b["포인트"])
        # 지급 형태 다름과 조건 우열이 같은 담보, 같은 상대에 함께 있으면 조건 문장에 지급 형태를 적지 않고 주의 문장이 그 포인트를 가리킨다
        for c in b["단정주의"]:
            if c["종류"] != S.CAUTION_PAY:
                continue
            for pid in c["같은상대조건포인트"]:
                assert S.PAY_ITEM not in out["포인트"][pid]["견준항목"] and "따로 적었습니다" in c["문장"]
    for key, m in out["지도"].items():
        for line in m["칸"]:
            for x in line:
                # 열림 라벨 칸에는 우리 간편 종형이 열려 있다(점검 결함 1)
                simple = [v for v in x["열린종형"].get("EPOST", []) if out["종형"][v]["심사"] == S.SIMPLE]
                assert (x["라벨"] in (S.LABELS[S.ONLY_OPEN], S.LABELS[S.BOTH_OPEN])) <= bool(simple)
                assert bool(simple) or x["닫힌사유"], (key, x)
                # 거르개 지도의 관문 포인트는 거르개 안의 상대와만 견준다(점검 결함 3)
                if m["갱신유형"]:
                    assert all(out["종형"][v]["갱신"] == m["갱신유형"] for p in x["관문포인트"]
                               for v in out["포인트"][p]["비교종형ID"])


@pytest.mark.skipif(not (SNAPSHOT / "sys_급부.jsonl").exists(), reason="사본 없음")
def test_real_snapshot_runs():
    data = load(SNAPSHOT)
    analysis = I.analyze(data)
    m = S.segment_map(data, "M", None, analysis)
    assert sum(m["집계"].values()) == len(m["행"]) * len(m["열"]) and len(m["행"]) >= 2
    vids = I.base_variants(data)[0]
    for b in analysis["기준"]:
        base = data.variants[b["종형ID"]]
        for p in b["맞붙는종형"]:
            peer = data.variants[p["종형ID"]]
            # 같은 등급에 갱신유형이 같은 후보가 있었으면 그 후보를 골랐다
            same = [v for v in vids if data.variants[v]["기관코드"] == peer["기관코드"]
                    and C._uw_key(data.variants[v]) == C._uw_key(base) and data.variants[v].get("갱신유형") == base.get("갱신유형")]
            if same and C._uw_key(peer) == C._uw_key(base):
                assert peer.get("갱신유형") == base.get("갱신유형"), (b["종형ID"], p["종형ID"])
        r = S.points(data, b["종형ID"], S.Profile(age=50, sex="M", since=2), analysis)
        for x in r["포인트"]:
            # 관문전용 종형을 적은 관문 포인트는 머리말이 "관문만 수집한"으로 시작할 수 있다(담보 미수집)
            assert x["머리말"].startswith(("수집한 ", "관문만 수집한 ")) and x["근거"] and x["문장"]
            assert not x.get("관문만수집") or "관문만 수집한 " in x["머리말"]
            assert all(e["급부ID"] is None or e["급부ID"] not in data.pending_benefit for e in x["근거"])
