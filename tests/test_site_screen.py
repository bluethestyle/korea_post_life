"""화면 비교 대상과 기본값(site/screen.py), 보장 범위 한정 종형(insights.coverage_scope)의 비교 범위, 기준 종형 차례(insights.order_bases),
등급별 대표 종형(lineup.pick_lineup)의 우리 종형 고르기. 자료는 손으로 지어낸 회사다(test_site_sales 의 Book). 공시 원문은 옮기지 않는다.
"""
import pytest

from postlife.site import console4 as C4
from postlife.site import insights as I
from postlife.site import lineup
from postlife.site import sales as S
from postlife.site import screen as SC
from postlife.site.model import Data

from test_site_sales import E1, E5, EG, H1, HG, NAMES, REL, S1, Book, fill, row, std

E2, ET, EO = "EPOST_E2_aaaaaa", "EPOST_ET_aaaaaa", "EPOST_EO_aaaaaa"
EC, EB = "EPOST_EC_aaaaaa", "EPOST_EB_aaaaaa"
H0 = "HANWHALIFE_H0_bbbbbb"
ASK305 = (3, 0, 5, False, 3)
EXTRA = [
    (E2, "EPOST", "2종(간편가입325)", "간편심사", "3.2.5", (3, 2, 5, False, 6), "갱신", "표준형", "2026-06-17", [(20, 80)]),
    (ET, "EPOST", "단일", "일반심사", "일반", (None,) * 5, "비갱신", "표준형", "2025-04-03", [(15, 65)]),
    (EO, "EPOST", "2종(간편가입)", "간편심사", "3.2.5", (3, 2, 5, False, 6), "비갱신", "표준형", "2026-09-16", [(15, 70)]),
    (EC, "EPOST", "1종(간편가입)[암보장형]", "간편심사", "3.0.5", ASK305, "갱신", "표준형", "2025-04-03", [(30, 80)]),
    (EB, "EPOST", "1종(간편가입)[2대질병보장형]", "간편심사", "3.0.5", ASK305, "갱신", "표준형", "2025-04-03", [(30, 80)]),
    (H0, "HANWHALIFE", "간편가입형(0년)", "간편심사", "3.0.5", ASK305, "비갱신", "표준형", "2026-10-01", [(15, 80)]),
]
PRODUCT = {E1: "EPOST_SIMPLE", E5: "EPOST_SIMPLE", EG: "EPOST_SIMPLE", E2: "EPOST_SIMPLE", ET: "EPOST_TOTAL",
           EO: "EPOST_HANAROOK_WHOLE", EC: "EPOST_MORESIMPLE_CANCER", EB: "EPOST_MORESIMPLE_2CI"}
TITLE = {"EPOST_SIMPLE": "무배당 우체국간편한건강보험(20년갱신형) 2606", "EPOST_TOTAL": "무배당 우체국통합건강보험 2504",
         "EPOST_HANAROOK_WHOLE": "무배당 우체국하나로OK보험 2609",
         "EPOST_MORESIMPLE_CANCER": "무배당 우체국더간편건강보험(갱신형) 2504",
         "EPOST_MORESIMPLE_2CI": "무배당 우체국더간편건강보험(갱신형) 2504"}


def make(extra=EXTRA, setting=None, wide_limited=False) -> Data:
    """Book 에 화면 구성 변경을 흉내 낸 종형을 더한 자료. H0 은 관문전용(인수기준만 수집)이다."""
    b = Book(extra=extra)
    fill(b)
    b.t["hum_표준담보사전"].append(std("STD_CV_X", "뇌심장보장", "뇌심장 시험", "진단"))
    for r in b.t["sys_상품종형"]:
        vid = r["종형ID"]
        if vid in PRODUCT:
            r["모상품ID"] = PRODUCT[vid]
            r["공시상품명"] = f"{TITLE[PRODUCT[vid]]} {r['종형명']}"
        if vid == H0:
            r["비교역할구분"] = "관문전용"
    vids = {r["종형ID"] for r in b.t["sys_상품종형"]}
    if EC in vids:
        b.ben(EC, "STD_CA_B"); b.ben(EC, "STD_CA_U")                      # 암보장만
        if wide_limited:
            b.ben(EC, "STD_CM_WIDE")                                      # 공통보장 담보가 있으면 종합형
    if EB in vids:
        b.ben(EB, "STD_BR_C"); b.ben(EB, "STD_HT_ONLY")                   # 뇌혈관보장, 심장보장만
    if E2 in vids:
        b.ben(E2, "STD_CA_B"); b.ben(E2, "STD_CM_WIDE")
    if EO in vids:
        b.ben(EO, "STD_CM_WIDE")
    b.peers("STD_CV_X")                                                   # 타사만 가진 뇌심장보장 담보
    if setting:
        b.t["hum_기준값"] = [row("hum_기준값", 기준키=k, 문자값=v) for k, v in setting.items()]
    return Data(b.t)


@pytest.fixture(scope="module")
def data():
    return make()


# ---------- 보장 범위 판정 ----------
def test_coverage_scope_by_bracket_and_majors(data):
    assert I.coverage_scope(data, EC) == ["암보장"]
    assert I.coverage_scope(data, EB) == ["뇌혈관보장", "심장보장", "뇌심장보장"]      # 둘 가운데 하나라도 있으면 뇌심장보장도
    assert I.coverage_scope(data, E1) is None                                       # 종형명에 [..보장형] 표기가 없으면 종합형
    assert I.coverage_scope(make(wide_limited=True), EC) is None                     # 공통보장 담보가 있으면 종합형
    bare = make(extra=[x for x in EXTRA if x[0] != EB])
    assert I.coverage_scope(bare, EC) == ["암보장"]


# ---------- 화면 비교에서 빼는 상품 ----------
def test_excluded_product_is_left_out_of_the_screen_only(data):
    assert ET in data.variants                                                      # 적재 자료에는 남는다
    vids, bases = I.base_variants(data)
    assert ET not in vids and ET not in bases
    assert ET not in S.targets(data) and ET not in S.gate_targets(data)
    out = S.export(data, I.analyze(data, REL), REL)
    assert ET not in [b["종형ID"] for b in out["기준종형"]] and ET not in out["기준별"]
    assert all(ET not in m["칸"][0][0]["관문흐름"]["종형"] for m in out["지도"].values())
    assert ET not in [r["종형ID"] for r in I.analyze(data, REL)["기준"]]
    assert ET not in C4.build_combo(data)["종형"]


# ---------- 기준 종형 차례 ----------
def test_base_order_puts_the_default_first_and_limited_last(data):
    ctx = S._Ctx(data, None, REL)
    assert ctx.bases[0] == E2                                                       # 화면 기본 상품의 3.2.5
    assert ctx.bases[1:4] == [E1, E5, EG]                                           # 같은 상품의 다른 종형
    assert ctx.bases[4] == EO                                                       # 다른 종합형 상품
    assert set(ctx.bases[5:]) == {EC, EB}                                           # 보장 범위 한정 상품이 끝
    assert len(ctx.bases) == len(set(ctx.bases)) == len(I.base_variants(data)[1])
    assert [b["종형ID"] for b in S.export(data, None, REL)["기준종형"]] == ctx.bases


def test_default_base_does_not_follow_the_weekly_setting():
    d = make(setting={"REP_WEEKLY_UW_2": "315"})
    assert S._Ctx(d, None, REL).bases[0] == E2                                      # 주간 변화 집계 값(315)과 묶지 않는다
    assert SC.default_base(d, [E1, E5]) == E1                                       # 기본 상품의 3.2.5 가 없으면 첫 종형
    no325 = make(extra=[x for x in EXTRA if x[0] != E2])
    assert S._Ctx(no325, None, REL).bases[0] == E1


def test_combo_follows_the_base_order(data):
    assert list(C4.build_combo(data)["종형"]) == S._Ctx(data, None, REL).bases      # 구성 예시도 기준 종형 차례


# ---------- 등급별 대표 종형 ----------
def test_pick_lineup_prefers_the_default_product_when_two_home_variants_share_a_grade(data):
    lu = lineup.pick_lineup(data, lineup.company_codes(data))
    assert lu["3.2.5"][0] == E2                                                     # EO(하나로OK 흉내)도 3.2.5
    assert lu["3.1.5"][0] == E1 and lu["3.5.5"][0] == E5
    assert SC.prefer_default_product(data, [EO]) == [EO]
    assert SC.prefer_default_product(data, [EO, E2]) == [E2]


# ---------- 보장 범위 한정 기준 종형의 비교 ----------
def test_limited_base_compares_only_inside_its_scope(data):
    analysis = I.analyze(data, REL)
    res = {r["종형ID"]: r for r in analysis["기준"]}
    for base in (EC, EB):
        scope = I.coverage_scope(data, base)
        assert res[base]["보장범위"] == scope
        for x in res[base]["시사점"]:
            sid = x.get("표준담보ID")
            if sid in data.std:
                assert data.std[sid]["보장대분류"] in scope, (base, sid)
        grid = S.journey(data, base, ctx=S._Ctx(data, analysis, REL))
        assert grid["행"] == [m for m in grid["행"] if m in scope] and grid["행"]
    wide = res[E2]
    assert wide["보장범위"] is None
    assert any(data.std[x["표준담보ID"]]["보장대분류"] == "공통보장" for x in wide["시사점"] if x.get("표준담보ID") in data.std)


def test_limited_base_cover_rows_stay_in_scope(data):
    analysis = I.analyze(data, REL)
    sales_obj = S.export(data, analysis, REL)
    cover = C4.build_cover(data, sales_obj, REL, analysis)
    for base in (EC, EB):
        scope = I.coverage_scope(data, base)
        majors = {data.std[r[0]]["보장대분류"] for r in cover["b"][base]["rows"]}
        assert majors and majors <= set(scope), (base, majors)
    assert "공통보장" in {data.std[r[0]]["보장대분류"] for r in cover["b"][E2]["rows"]}


def test_scope_note_and_labels(data):
    analysis = I.analyze(data, REL)
    out = S.export(data, analysis, REL)
    rows = {b["종형ID"]: b for b in out["기준종형"]}
    assert rows[EC]["상품약칭"] == "더간편건강보험 2504" and rows[E2]["상품약칭"] == "간편한건강보험 2606"
    assert rows[EC]["표시이름"] == "더간편건강보험 2504 1종(간편가입)[암보장형]"
    assert rows[EC]["전용표시"] == rows[EB]["전용표시"] == "암, 2대질병 전용 상품"   # 모상품ID 가 달라도 상품약칭으로 묶는다
    assert rows[EC]["보장범위"] == ["암보장"]
    assert "암보장 담보만 비교했습니다" in rows[EC]["범위안내"]
    assert "보장 범위 밖 담보" in rows[EC]["범위안내"]
    assert "인수기준만 수집" in rows[EC]["범위안내"] and "한화생명 간편가입형(0년)" in rows[EC]["범위안내"]
    assert rows[E2]["보장범위"] is None and rows[E2]["전용표시"] is None and rows[E2]["범위안내"] is None
    line = {x["줄"]: x for x in out["기준별"][EC]["브리핑"]}["라"]
    assert line["틀"][:3] == ["라_범위한정", "라_범위밖", "라_가까운유형"]
    assert line["문장"].startswith(rows[EC]["범위안내"])
    assert not any(t.startswith(("라_범위한정", "라_범위밖", "라_가까운유형"))
                   for t in {x["줄"]: x for x in out["기준별"][E2]["브리핑"]}["라"]["틀"])
    assert S.forbidden_in(rows[EC]["범위안내"]) == []


def test_limited_only_cells_match_the_landscape_count(data):
    out = S.export(data, I.analyze(data, REL), REL)
    for m in out["지도"].values():
        for line in m["칸"]:
            for c in line:
                for v in c.get("우리전용만") or []:
                    assert I.coverage_scope(data, v) is not None
    for base, b in out["기준별"].items():
        ga = {x["줄"]: x for x in b["브리핑"]}["가"]
        if "가_전용만" in ga["틀"]:
            assert ga["값"]["전용만칸수"] > 0


def test_product_short_names():
    d = make()
    assert S.product_short(d, E2) == "간편한건강보험 2606" and S.product_short(d, ET) == "통합건강보험 2504"
    for r in d.variants.values():                    # 공시상품명이 종형명으로 끝나지 않는 꼴(하나로OK보험 공시실 목록)
        if r["종형ID"] == EO:
            r["공시상품명"] = "무배당 우체국하나로OK보험(해약환급금50%지급형) 2609 2종(간편가입)(종신)"
            r["종형명"] = "2종(간편가입)[해약환급금50%지급형, 종신]"
    assert S.product_short(d, EO) == "하나로OK보험 2609"
