"""영업 인사이트(site/sales.py): 가입 관문, 고객군 지도의 칸 분류, 응대 포인트의 문장 틀, 범위 머리말, 빼는 조건, 정렬.

자료는 손으로 지어낸 세 회사다. 공시 원문은 옮기지 않는다.
"""
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
    """지어낸 사본 표."""

    def __init__(self, skip=()):
        self.t = {name: [] for name in ("sys_상품종형", "sys_특약", "sys_급부", "hum_담보매핑", "hum_표준담보사전", "sys_작업로그",
                                        "sys_가입조건")}
        self.n = 0
        for vid, org, kind, uw, short, ask, renew, refund, start, ages in VARIANTS:
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
            red2=None):
        self.n += 1
        bid = f"{vid}_T_B{self.n}"
        months, rate = red or (None, None)
        months2, rate2 = red2 or (None, None)
        self.t["sys_급부"].append(row("sys_급부", 급부ID=bid, 특약ID=f"{vid}_T", 원시급부명=f"급부{self.n}", 급부역할="주급부",
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
    assert g1[0]["문장"] == (
        "입원 없이 받은 마지막 수술이 3개월~1년 전이고 최근 3개월 소견과 5년 안 중대질병에 해당하지 않으시면, "
        "우체국 1종(간편가입315)의 고지 질문에는 해당하지 않습니다. 한화생명 간편가입형(1년)과 삼성화재 7종(간편315)는 "
        "같은 기간에 입원과 수술을 묻습니다. 가입 여부는 청약 뒤 심사로 정해집니다.")
    g3 = by_code(pts, "G3")
    assert [x["비교종형ID"] for x in g3] == [[H1], [S1]]
    assert g3[0]["문장"] == ("1년 안 질문에서 우체국 1종(간편가입315)는 입원을, 한화생명 간편가입형(1년)은 입원과 수술을 묻습니다. "
                            "5년 안 중대질병 질문의 질병 수는 우체국 6개, 한화생명 7개입니다.")


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
    assert q1["세부"] == "Q1" and q1["질문"] == "한화생명이나 삼성화재에는 부분1 암이 있던데요."
    assert q1["문장"].startswith("우체국 1종(간편가입315)에는 부분1 암을 따로 주는 담보는 없고, 통합 암에서 관련 보장을 합니다.")
    wide = by_sid(pts, "STD_CM_WIDE")
    assert wide["세부"] == "Q2" and wide["좁은담보"] == ["좁은 입원"] and wide["꼬리표"] == [S.REVISION_TAG]
    q3 = by_sid(pts, "STD_BR_C")
    assert q3["질문"] == "뇌 조건은 한화생명이나 삼성화재가 조건이 다르던데요."
    assert q3["문장"] == ("맞습니다. 뇌 조건은 우체국 1종(간편가입315)가 1년까지 보험금의 50% 지급이고, 한화생명 간편가입형(1년)은 "
                         "감액 없음, 삼성화재 7종(간편315)는 감액 없음입니다. 1년이 지나면 모두 보험금 전액을 지급합니다.")
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
    assert q3["문장"] == ("맞습니다. 낮은 지급률은 우체국 1종(간편가입315)가 1년까지 보험금의 10% 지급이고, "
                         "한화생명 간편가입형(1년)은 6개월까지 보험금의 25%, 1년까지 50% 지급, 삼성화재 7종(간편315)는 감액 없음입니다. "
                         "1년이 지나면 모두 보험금 전액을 지급합니다.")
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
    brief = S.brief(pts)
    assert [x["표준담보ID"] or x["세부"] for x in brief] == ["G1", "G3", "G3", "STD_HT_ONLY", "STD_CM_TOP",
                                                          "STD_CA_GAP", "STD_BR_C", "STD_CA_P1"]
    assert [x["표준담보ID"] for x in S.brief(pts, purpose="암") if x["종류"] != S.GATE] == ["STD_CA_GAP", "STD_CA_P1"]
    # 같은 조건이면 포인트ID가 같다(analyze 결과 없이 다시 돌려도)
    assert ids == [x["포인트ID"] for x in S.points(data, E1, pts["조건"], None, REL)["포인트"]]


# ---------- 실제 사본 ----------
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
            assert x["머리말"].startswith("수집한 ") and x["근거"] and x["문장"]
            assert all(e["급부ID"] is None or e["급부ID"] not in data.pending_benefit for e in x["근거"])
