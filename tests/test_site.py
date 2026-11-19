"""판단 화면(src/postlife/site)의 자료 가공 시험.

앞부분은 작은 가짜 자료로 규칙을 하나씩 확인하고, 뒷부분은 data/snapshot 실제 자료로
빌드가 되는지와 만든 HTML이 외부 주소를 부르지 않는지 확인한다.
화면 4의 조합 계산은 화면(calc.js)이 하므로, node가 있으면 같은 입력을 Python과 calc.js에 넣어 결과를 맞대 본다.
HTML에는 자료를 줄여 적어 넣는다(pack.py). 줄였다 되살린 자료가 원래와 같은지도 Python과 calc.js 양쪽에서 확인한다.
"""
import json
import random
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from postlife.schema import TABS
from postlife.site import build, combo, compare, eligibility, overview, pack, revision, worklog
from postlife.site.model import BASIS_COLUMN, RATIO_BASIS, Cond, Data, is_ratio, load, pay_rate

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "snapshot"
CALC_JS = ROOT / "src" / "postlife" / "site" / "assets" / "calc.js"

NEW_A, NEW_B, OLD_A, PRIV = "EPOST_N1_aaaaaa", "EPOST_N2_bbbbbb", "EPOST_O1_cccccc", "HANWHALIFE_H1_dddddd"
TERM, PAY = "20년만기(갱신형)", "전기납"


# ---------- 가짜 자료 ----------
def row(tab: str, **values):
    """열 정의에 있는 열을 모두 가진 행. 주지 않은 열은 None."""
    out = {c.name: None for c in TABS[tab].columns}
    unknown = set(values) - set(out)
    assert not unknown, unknown
    out.update(values)
    return out


def variant(vid, org, rev, lineage, name, kind, role, uw, simple, gate, start, end, summary, method):
    months, hosp, major, surgery, count = gate
    return row("sys_상품종형", 종형ID=vid, 개정판ID=rev, 모상품ID=rev.rsplit("_", 1)[0], 종형계보키=lineage, 기관코드=org,
               공시상품코드=vid.split("_")[1], 공시상품명=name, 종형명=kind, 비교역할구분=role, 심사유형=uw, 간편고지약칭=simple,
               고지최근소견개월=months, 고지입원수술년수=hosp, 고지중대질병년수=major, 고지수술포함여부=surgery, 고지중대질병수=count,
               갱신유형="갱신", 갱신주기년=20, 환급유형="표준형", 납입면제적용=False, 적용시작일=start, 판매종료일=end,
               공시목록URL="https://example.invalid/list", 요약서해시=summary, 사업방법서해시=method)


def rider(vid, key, name, low, high, kind="선택특약"):
    return row("sys_특약", 특약ID=f"{vid}_T{key}", 종형ID=vid, 특약계보키=key, 담보구분=kind, 원시특약명=name,
               갱신여부=True, 갱신주기년=20, 최소가입금액만원=low, 최대가입금액만원=high)


def benefit(vid, key, code, name, role, pay, wait=0, reduce=None, limit="최초 1회에 한함", base=1000):
    months, rate = reduce or (None, None)
    return row("sys_급부", 급부ID=f"{vid}_T{key}_B{code}", 특약ID=f"{vid}_T{key}", 원시급부명=name, 급부역할=role,
               기준가입금액만원=base, 기준지급금액만원=pay, 지급횟수제한=limit, 면책기간일수=wait,
               감액개월1=months, 감액지급률1=rate, 근거문서종류="요약서", 근거문서쪽수=10)


def mapped(bid, state, std=None, rec=None, prob=0.95):
    return row("hum_담보매핑", 급부ID=bid, 공시상품명="-", 원시특약명="-", 원시급부명="-", 추천표준담보ID=rec or std,
               매핑확률=prob, 확정표준담보ID=std, 검토상태=state)


def condition(vid, key, low, high, amount, sex=None, term=TERM, pay=PAY):
    tid = f"{vid}_T{key}" if key else None
    return row("sys_가입조건", 조건행ID=f"{vid}_C{key or 'main'}_{term}_{pay}_{sex or ''}_{low}", 종형ID=vid, 특약ID=tid,
               보험기간구분=term, 납입기간구분=pay, 성별=sex, 최저가입나이=low, 최고가입나이=high, 구간최대가입금액만원=amount)


def rule(vid, base, target, kind, number=None, unit=None):
    return row("sys_결합제약", 제약ID=f"{vid}_R{base}_{target}_{kind}", 종형ID=vid, 기준특약ID=f"{vid}_T{base}",
               대상특약ID=f"{vid}_T{target}", 제약유형=kind, 제약수치=number, 제약단위=unit, 근거문구="시험용 문구")


def log(n, stamp, step, tab, target, result, column=None, prob=None, model=None, reason=None):
    return row("sys_작업로그", 로그ID=f"LOG_{n:03d}", 실행일시=stamp, 작업단계=step, 대상탭=tab, 대상행ID=target, 대상열=column,
               호출모델=model, 판정확률=prob, 결과=result, 사유=reason)


def std(sid, major, mid, name, kind, unit):
    return row("hum_표준담보사전", 표준담보ID=sid, 보장대분류=major, 보장중분류=mid, 표준담보명=name, 급부유형=kind,
               비교기준단위만원=unit, 사용여부=True)


def fake_tables():
    half = (12, 0.5)
    variants = [
        variant(NEW_A, "EPOST", "EPOST_X_2606", "EPOST_X|간편심사|3.2.5|갱신|표준형", "무배당 시험건강보험 2606 1종(간편가입325)",
                "1종(간편가입325)", "정밀비교", "간편심사", "3.2.5", (3, 2, 5, False, 6), "2026-06-17", None, "h2606", "m2606"),
        variant(NEW_B, "EPOST", "EPOST_X_2606", "EPOST_X|일반심사|일반|갱신|표준형", "무배당 시험건강보험 2606 2종(일반가입)",
                "2종(일반가입)", "정밀비교", "일반심사", "일반", (None, None, None, None, None), "2026-06-17", None, "h2606", "m2606"),
        variant(OLD_A, "EPOST", "EPOST_X_2504", "EPOST_X|간편심사|3.2.5|갱신|표준형", "무배당 시험건강보험 2504",
                "간편가입", "직전개정시연", "간편심사", "3.2.5", (3, 5, 5, False, 6), "2025-04-03", "2026-06-16", "h2504", "m2504"),
        variant(PRIV, "HANWHALIFE", "HANWHA_Y_2610", "HANWHA_Y|일반심사|일반|갱신|표준형", "민영 시험보험 무배당",
                "일반가입형", "정밀비교", "일반심사", "일반", (None, None, None, None, None), "2026-10-01", None, "hp", "mp"),
    ]
    riders, benefits, mapping, conditions, rules = [], [], [], [], []
    for vid in (NEW_A, NEW_B):
        riders += [rider(vid, "main", "주계약", 1000, 4000, "주계약"), rider(vid, "cancer", "무배당 암진단특약 2606", 500, 4000),
                   rider(vid, "hosp", "무배당 암입원수술특약 2606", 500, 1000), rider(vid, "nursing", "무배당 요양병원암입원특약 2606", 500, 1000),
                   rider(vid, "surg", "무배당 질병수술특약 2606", 500, 1000)]
        rows = [
            (benefit(vid, "main", "death", "재해사망보험금(재해)", "주급부", 1000, limit=None), "대상외", None, None),
            (benefit(vid, "cancer", "ca", "암진단보험금(암)", "주급부", 1000, 90, half), "자동확정", "STD_CA_DX_GENERAL", None),
            (benefit(vid, "cancer", "th", "암진단보험금(갑상선암 등)", "부수급부", 200, 0, half), "자동확정", "STD_CA_DX_PSEUDO", None),
            (benefit(vid, "hosp", "hca", "암직접치료입원보험금(암)", "주급부", 5, 90, half, "1일당, 120일 한도"), "승인", "STD_CA_HOSP", None),
            (benefit(vid, "hosp", "hth", "암직접치료입원보험금(갑상선암 등)", "부수급부", 2, 0, half, "1일당, 120일 한도"), "대기", None, "STD_CA_HOSP"),
            (benefit(vid, "hosp", "open", "암수술보험금(암·관혈수술)", "주급부", 300, 90, half, "수술 1회당"), "자동확정", "STD_CA_SURG", None),
            (benefit(vid, "hosp", "closed", "암수술보험금(암·비관혈수술)", "주급부", 100, 90, half, "수술 1회당"), "자동확정", "STD_CA_SURG", None),
            (benefit(vid, "nursing", "nca", "요양병원암입원보험금(암)", "주급부", 2, 90, half, "1일당, 60일 한도"), "자동확정", "STD_CA_HOSP_NURSING", None),
            (benefit(vid, "surg", "g1", "질병수술보험금(1종)", "주급부", 10, 0, half, "수술 1회당"), "자동확정", "STD_CM_SURG_GRADE", None),
            (benefit(vid, "surg", "g3", "질병수술보험금(3종)", "주급부", 50, 0, half, "수술 1회당"), "대기", None, "STD_CM_SURG_GRADE"),
            (benefit(vid, "surg", "g5", "질병수술보험금(5종)", "주급부", 300, 0, half, "수술 1회당"), "자동확정", "STD_CM_SURG_GRADE", None),
        ]
        for b, state, sid, rec in rows:
            benefits.append(b)
            mapping.append(mapped(b["급부ID"], state, sid, rec))
        conditions += [condition(vid, None, 20, 65, 4000), condition(vid, None, 66, 80, 2000),
                       condition(vid, "cancer", 20, 65, 4000), condition(vid, "cancer", 66, 80, 2000),
                       condition(vid, "hosp", 20, 65, 1000), condition(vid, "hosp", 66, 80, 500),
                       condition(vid, "nursing", 20, 70, 1000),
                       condition(vid, "surg", 20, 65, 1000, "M"), condition(vid, "surg", 23, 65, 1000, "F")]
        rules += [rule(vid, "main", "cancer", "최대연동", 1, "비율"), rule(vid, "main", "hosp", "최대연동", 1, "비율"),
                  rule(vid, "hosp", "nursing", "선행가입")]

    # 직전 개정판: 암진단은 한도와 감액 기간이 다르고, 집중입원특약은 개정 뒤에 없어진다
    riders += [rider(OLD_A, "main", "주계약", 1000, 4000, "주계약"), rider(OLD_A, "cancer", "무배당 간편Ⅱ암진단특약 2504", 500, 3000),
               rider(OLD_A, "hosp", "무배당 간편Ⅱ암입원수술특약 2504", 500, 1000), rider(OLD_A, "focus", "무배당 간편Ⅱ집중입원특약 2504", 500, 1000)]
    old_rows = [
        (benefit(OLD_A, "main", "death", "재해사망보험금(재해)", "주급부", 1000, limit=None), "대상외", None),
        (benefit(OLD_A, "cancer", "ca", "암진단보험금(암)", "주급부", 1000, 90, (24, 0.5)), "자동확정", "STD_CA_DX_GENERAL"),
        (benefit(OLD_A, "cancer", "th", "암진단보험금(갑상선암 등)", "부수급부", 100, 0, half), "자동확정", "STD_CA_DX_PSEUDO"),
        (benefit(OLD_A, "hosp", "hca", "암직접치료입원보험금(암)", "주급부", 5, 90, half, "3일 초과 입원일수 1일당, 120일 한도"), "자동확정", "STD_CA_HOSP"),
        (benefit(OLD_A, "hosp", "open", "암수술보험금(관혈수술)", "주급부", 300, 90, half, "수술 1회당"), "자동확정", "STD_CA_SURG"),
        (benefit(OLD_A, "hosp", "closed", "암수술보험금(비관혈수술)", "주급부", 100, 90, half, "수술 1회당"), "자동확정", "STD_CA_SURG"),
        (benefit(OLD_A, "focus", "icu", "중환자실입원보험금", "주급부", 5, limit="1일당, 60일 한도"), "대상외", None),
    ]
    for b, state, sid in old_rows:
        benefits.append(b)
        mapping.append(mapped(b["급부ID"], state, sid))
    conditions += [condition(OLD_A, None, 30, 65, 4000), condition(OLD_A, None, 66, 80, 2000), condition(OLD_A, "cancer", 30, 65, 3000)]

    # 민영사: 주계약 가입 나이가 납입기간에 따라 다르고, 특약은 가입나이 자료가 없다
    riders += [rider(PRIV, "main", "주계약", 1000, 5000, "주계약"), rider(PRIV, "pc", "암진단특약", 500, 5000)]
    b = benefit(PRIV, "pc", "ca", "암진단비", "주급부", 1000, 90)
    benefits.append(b)
    mapping.append(mapped(b["급부ID"], "자동확정", "STD_CA_DX_GENERAL"))
    conditions += [condition(PRIV, None, 15, 60, 5000, term="90세만기", pay="20년납"), condition(PRIV, None, 15, 70, 3000, term="90세만기", pay="10년납")]

    nursing_a, hosp_a, grade5_a = f"{NEW_A}_Tnursing_Bnca", f"{NEW_A}_Thosp_Bhca", f"{NEW_A}_Tsurg_Bg5"
    first, second = "2026-11-18T15:00:00+09:00", "2026-11-18T16:00:00+09:00"
    logs = [
        log(1, first, "추출", "sys_급부", f"{NEW_A}_Tcancer", "통과", model="gemini-3.5-flash-lite"),
        log(2, first, "코드대조", "sys_급부", f"{NEW_A}_Tcancer_Bca", "통과"),
        log(3, first, "판정", "sys_급부", f"{NEW_A}_Tcancer_Bca", "통과", "기준지급금액만원", 0.95, "gemini-decision-1"),
        log(4, first, "사람검토이관", "sys_급부", nursing_a, "보류", "기준지급금액만원", 0.68, "gemini-decision-1", "확인 필요"),
        log(5, first, "사람검토이관", "sys_급부", hosp_a, "보류", "감액지급률1", 0.6, "gemini-decision-1"),
        log(6, second, "판정", "sys_급부", hosp_a, "통과", "감액지급률1", 0.9, "gemini-decision-1"),      # 나중 실행에서 통과
        log(7, first, "사람검토이관", "sys_급부", grade5_a, "보류", "지급횟수제한", 0.64, "gemini-decision-1"),
        log(8, first, "사람검토이관", "sys_급부", f"{NEW_A}_Thosp_Bgone", "보류", "기준지급금액만원", 0.1, "gemini-decision-1"),  # 사본에 없는 행
        log(9, first, "사람검토이관", "sys_가입조건", f"{NEW_A}_Ccancer_{TERM}_{PAY}__66", "보류", "금액", 0.45, "gemini-decision-1"),
        log(10, first, "재추출", "sys_급부", f"{NEW_A}_Thosp", "통과", model="gemini-3.1-flash-lite", prob=0.8),
        log(11, first, "재추출", "sys_급부", f"{NEW_A}_Tsurg", "반려", model="gemini-3.8-flash", prob=0.3),
        log(12, second, "사람검토이관", "hum_담보매핑", f"{NEW_A}_Thosp_Bhth", "보류", "추천표준담보ID", 0.74, "gemini-decision-1"),
    ]
    dictionary = [
        std("STD_CA_DX_GENERAL", "암보장", "암진단", "일반암 진단비", "진단", 1000),
        std("STD_CA_DX_PSEUDO", "암보장", "암진단", "유사암 진단비(통합)", "진단", 1000),
        std("STD_CA_HOSP", "암보장", "암입원", "암 입원일당", "입원", 1),
        std("STD_CA_HOSP_NURSING", "암보장", "암입원", "암 요양병원 입원일당", "입원", 1),
        std("STD_CA_SURG", "암보장", "암수술", "암 수술비", "수술", 100),
        std("STD_CM_SURG_GRADE", "공통보장", "수술비", "종별 수술비(최고 종 기준)", "수술", 100),
        std("STD_BR_DX_STROKE", "뇌혈관보장", "뇌혈관진단", "뇌졸중 진단비", "진단", 1000),
    ]
    settings = [
        row("hum_기준값", 기준키="REP_WEEKLY_AGE", 기준분류="대표조건", 기준명="대표 연령", 수치값=50, 적용시작일="2026-11-18"),
        row("hum_기준값", 기준키="REP_WEEKLY_SEX_1", 기준분류="대표조건", 기준명="대표 성별", 문자값="M", 적용시작일="2026-11-18"),
        row("hum_기준값", 기준키="REP_WEEKLY_UW_2", 기준분류="대표조건", 기준명="대표 심사유형", 문자값="325", 적용시작일="2026-11-18"),
        row("hum_기준값", 기준키="기사선별_통과", 기준분류="판정구간", 기준명="선별 통과", 수치값=0.7, 적용시작일="2026-11-18"),
    ]
    trends = [
        row("sys_시장동향", 동향ID="TRD_1", 수집주차="2026-W47", 발표일자="2026-11-12", 기관코드="MERITZ", 분류유형="신담보출시",
            핵심요약="시험 소식", 출처URL="https://example.invalid/a", 수집경로="검색", 판정확률=0.9),
        row("sys_시장동향", 동향ID="TRD_2", 수집주차="2026-W47", 발표일자="2026-11-10", 기관코드="MERITZ", 분류유형="상품개정",
            핵심요약="확률이 낮은 소식", 출처URL="https://example.invalid/b", 수집경로="검색", 판정확률=0.5),
    ]
    return {"sys_상품종형": variants, "sys_특약": riders, "sys_급부": benefits, "hum_담보매핑": mapping, "sys_가입조건": conditions,
            "sys_결합제약": rules, "sys_작업로그": logs, "hum_표준담보사전": dictionary, "hum_기준값": settings, "sys_시장동향": trends,
            "sys_보험료예시": [], "sys_급부질병코드": [], "hum_표준질병군": []}


@pytest.fixture()
def data():
    return Data(fake_tables(), {"snapshot_at": "2026-11-18T17:00:00+09:00"})


def cond_index(conds, age, sex="M"):
    if age is None:
        return 0
    return next(i for i, c in enumerate(conds) if c.age is not None and c.lo <= age <= c.hi and c.sex == sex)


def cell_at(s3, std_id, vid, k):
    cell = next(r for r in s3["rows"] if r["id"] == std_id)["cells"][vid]
    return cell, cell["st"][cell["by"][k]]


# ---------- 대표 급부 고르기 ----------
def cand(i, role, val, pay=None, wait=0, red=None, name="급부"):
    return {"i": i, "role": role, "val": val, "pay": val if pay is None else pay, "wait": wait, "red": red or [], "name": name}


def test_대표는_주급부가_먼저다():
    assert compare.pick_rep([cand(0, "부수급부", 300), cand(1, "주급부", 100)]) == 1


def test_주급부가_없으면_금액이_가장_큰_줄이다():
    assert compare.pick_rep([cand(0, "대등복합", 100), cand(1, "대등복합", 300), cand(2, "부수급부", 50)]) == 1


def test_종별_수술비는_최고_종이_대표다():
    grades = [cand(i, "주급부", pay, name=f"{i + 1}종") for i, pay in enumerate([10, 30, 50, 100, 300])]
    assert compare.pick_rep(grades) == 4


def test_금액이_같으면_조건이_엄격한_줄이_대표다():
    assert compare.pick_rep([cand(0, "주급부", 2000, wait=0, name="갑상선암 등"), cand(1, "주급부", 2000, wait=90, name="암")]) == 1
    assert compare.pick_rep([]) is None


def test_급부의_표준담보는_확정된_매핑만_읽는다(data):
    assert data.benefit_view(f"{NEW_A}_Tcancer_Bca")["std"] == "STD_CA_DX_GENERAL"        # 자동확정
    assert data.benefit_view(f"{NEW_A}_Thosp_Bhca")["std"] == "STD_CA_HOSP"                # 승인
    waiting = data.benefit_view(f"{NEW_A}_Thosp_Bhth")
    assert waiting["std"] is None and waiting["state"] == "대기" and waiting["rec"] == "STD_CA_HOSP"
    assert data.benefit_view(f"{NEW_A}_Tmain_Bdeath")["std"] is None                       # 대상외


# ---------- 검토 대기 표시 ----------
def test_검토_대기는_같은_요약서를_쓰는_종형에도_붙는다(data):
    assert data.pending_benefit[f"{NEW_A}_Tnursing_Bnca"] == ["기준지급금액만원"]
    assert data.pending_benefit[f"{NEW_B}_Tnursing_Bnca"] == ["기준지급금액만원"]
    assert data.pending_benefit[f"{NEW_A}_Tsurg_Bg5"] == ["지급횟수제한"]


def test_나중_실행에서_통과한_급부와_사본에_없는_행은_검토_대기가_아니다(data):
    assert f"{NEW_A}_Thosp_Bhca" not in data.pending_benefit
    assert f"{NEW_A}_Thosp_Bgone" not in data.pending_benefit


def test_조건행의_검토_대기는_같은_사업방법서의_같은_구간에_붙는다(data):
    key = f"Ccancer_{TERM}_{PAY}__66"
    assert data.pending_condition[f"{NEW_A}_{key}"] == ["금액"]
    assert data.pending_condition[f"{NEW_B}_{key}"] == ["금액"]
    assert f"{NEW_A}_Ccancer_{TERM}_{PAY}__20" not in data.pending_condition
    assert data.rider_cap(f"{NEW_A}_Tcancer", Cond(age=70, sex="M")).pending is True
    assert data.rider_cap(f"{NEW_A}_Tcancer", Cond(age=50, sex="M")).pending is False


# ---------- 가입 한도와 환산 ----------
def test_환산은_기준지급금액을_가입금액에_비례시킨다():
    assert compare.scaled(3000, 2000, 2000) == 3000
    assert compare.scaled(3000, 2000, 1000) == 1500
    assert compare.scaled(5, 1000, 500) == 2.5
    assert compare.scaled(None, 1000, 500) is None and compare.scaled(5, 0, 500) is None and compare.scaled(5, 1000, None) is None


def test_나이를_고르면_그_나이의_구간_한도를_쓴다(data):
    tid = f"{NEW_A}_Tcancer"
    assert data.rider_cap(tid, Cond()).amount == 4000
    assert data.rider_cap(tid, Cond(age=50, sex="M")).amount == 4000
    assert data.rider_cap(tid, Cond(age=70, sex="M")).amount == 2000
    assert data.rider_cap(tid, Cond(age=85, sex="M")).ok is False
    assert data.rider_cap(f"{NEW_A}_Tnursing", Cond(age=75, sex="M")).ok is False         # 특약 가입나이는 70세까지


def test_성별이_있는_조건행은_그_성별에만_적용한다(data):
    tid = f"{NEW_A}_Tsurg"
    assert data.rider_cap(tid, Cond(age=21, sex="M")).ok is True
    assert data.rider_cap(tid, Cond(age=21, sex="F")).ok is False


def test_최대_가입금액은_주계약_연동을_넘지_않는다(data):
    tables = fake_tables()
    for r in tables["sys_가입조건"]:
        if r["종형ID"] == NEW_A and r["특약ID"] is None:
            r["구간최대가입금액만원"] = 1500                     # 주계약 한도를 특약보다 낮춘다
    lowered = Data(tables)
    assert lowered.rider_cap(f"{NEW_A}_Tcancer", Cond(age=50, sex="M")).amount == 1500
    assert lowered.rider_cap(f"{NEW_A}_Tsurg", Cond(age=50, sex="M")).amount == 1000   # 연동 제약이 없는 특약


def test_가입나이_자료가_없는_특약은_나이를_따지지_않는다(data):
    limit = data.rider_cap(f"{PRIV}_Tpc", Cond(age=40, sex="M"))
    assert limit.ok and limit.no_data and limit.amount == 5000
    assert data.rider_cap(f"{PRIV}_Tpc", Cond(age=80, sex="M")).ok is False                # 주계약에 가입할 수 없는 나이


# ---------- 화면 2 ----------
def test_가입_나이_구간은_한도가_같은_나이끼리_묶는다(data):
    assert eligibility.segments(data, f"{NEW_A}_Tmain", "M") == [
        {"lo": 20, "hi": 65, "max": 4000, "pend": False}, {"lo": 66, "hi": 80, "max": 2000, "pend": False}]
    assert [(s["lo"], s["hi"]) for s in eligibility.segments(data, f"{NEW_A}_Tsurg", "F")] == [(23, 65)]


def test_납입기간에_따라_가입나이가_다르면_하나라도_되는_나이를_잡는다(data):
    assert [(s["lo"], s["hi"], s["max"]) for s in eligibility.segments(data, f"{PRIV}_Tmain", "M")] == [(15, 60, 5000), (61, 70, 3000)]


def test_화면2는_고른_나이에서_가입할_수_있는_특약을_센다(data):
    conds = data.conds()
    s2 = eligibility.build(data, conds)
    assert s2["variants"][0] == NEW_A and PRIV in s2["variants"]
    x = s2["byVariant"][NEW_A]
    k = cond_index(conds, 75)
    assert x["ok"][k] is True and x["lim"][k] == 2000
    assert {r["tid"].split("_T")[1]: r["ok"][k] for r in x["riders"]} == {"cancer": True, "hosp": True, "nursing": False, "surg": False}
    assert x["ok"][cond_index(conds, 85)] is False
    assert eligibility.gate(data.variants[NEW_A]) == {"months": 3, "hospYears": 2, "surgery": False, "majorYears": 5, "majorCount": 6}


# ---------- 화면 3 ----------
def test_우열_판정은_지급액_면책_감액으로_가린다():
    base = {"val": 4000, "wait": 90, "red": [[12, 0.5]], "limit": "최초 1회에 한함"}
    assert compare.compare_terms(dict(base), base) == "s===."
    assert compare.compare_terms({**base, "val": 5000}, base) == "b+==."
    assert compare.compare_terms({**base, "val": 3000}, base) == "w-==."
    assert compare.compare_terms({**base, "wait": 0}, base) == "b=+=."
    assert compare.compare_terms({**base, "val": 3000, "red": []}, base) == "m-=+."
    assert compare.compare_terms({**base, "limit": "연 1회"}, base) == "s===L"


def test_감액은_없으면_낫고_기간이_짧고_지급률이_높을수록_낫다():
    assert compare.compare_reduction([], [[12, 0.5]]) == "+"
    assert compare.compare_reduction([[12, 0.5]], []) == "-"
    assert compare.compare_reduction([[12, 0.5]], [[24, 0.5]]) == "+"
    assert compare.compare_reduction([[12, 0.3]], [[12, 0.5]]) == "-"
    assert compare.compare_reduction([[12, 0.3]], [[24, 0.5]]) == "~"
    assert compare.compare_reduction([[12, 0.5]], [[12, 0.5]]) == "="


def test_비교표의_주된_값은_최대로_가입했을_때_지급액이다(data):
    conds = data.conds()
    s3 = compare.build(data, conds)
    assert s3["variants"] == [NEW_A, NEW_B, PRIV]            # 직전 개정판은 넣지 않고, 민영사는 코드 수정 없이 들어온다
    assert s3["bases"] == [NEW_A, NEW_B] and s3["defaultBase"] == NEW_A
    base = s3["bases"].index(NEW_A)

    cell, st = cell_at(s3, "STD_CA_DX_GENERAL", NEW_A, 0)
    assert st["vals"][st["rep"]] == 4000 and st["caps"][st["rep"]] == 4000 and st["vs"][base] == "B"
    _, st70 = cell_at(s3, "STD_CA_DX_GENERAL", NEW_A, cond_index(conds, 70))
    assert st70["vals"][st70["rep"]] == 2000
    _, st85 = cell_at(s3, "STD_CA_DX_GENERAL", NEW_A, cond_index(conds, 85))
    assert st85["kind"] == "unavail"

    _, private = cell_at(s3, "STD_CA_DX_GENERAL", PRIV, 0)
    assert private["vals"][private["rep"]] == 5000 and private["vs"][base] == "b+=+."     # 지급액 많고 감액 없음
    _, private85 = cell_at(s3, "STD_CA_DX_GENERAL", PRIV, cond_index(conds, 85))
    assert private85["vs"][base] == "u"


def test_비교표는_대표_급부를_쓰고_매핑_검토_대기는_뺀다(data):
    s3 = compare.build(data, data.conds())
    base = s3["bases"].index(NEW_A)
    surgery, st = cell_at(s3, "STD_CA_SURG", NEW_A, 0)
    assert data.benefits[surgery["lines"][st["rep"]]]["원시급부명"] == "암수술보험금(암·관혈수술)" and st["vals"][st["rep"]] == 300

    hosp, st = cell_at(s3, "STD_CA_HOSP", NEW_A, 0)
    assert hosp["lines"] == [f"{NEW_A}_Thosp_Bhca"] and hosp["wait"] == [f"{NEW_A}_Thosp_Bhth"]
    assert st["vals"] == [5]

    grade, st = cell_at(s3, "STD_CM_SURG_GRADE", NEW_B, 0)
    assert f"{NEW_B}_Tsurg_Bg3" in grade["wait"] and len(grade["lines"]) == 2
    assert data.benefits[grade["lines"][st["rep"]]]["원시급부명"] == "질병수술보험금(5종)"
    assert st["vs"][base] == "s===."                       # 지급 한도 문구만 검토 대기면 판정은 한다

    nursing, st = cell_at(s3, "STD_CA_HOSP_NURSING", NEW_B, 0)
    assert st["vs"][base] == "p"                           # 지급액이 검토 대기면 판정을 미룬다

    rows = {r["id"]: r for r in s3["rows"]}
    assert PRIV not in rows["STD_CA_SURG"]["cells"]        # 빈자리
    assert rows["STD_BR_DX_STROKE"]["any"] is False and rows["STD_BR_DX_STROKE"]["cells"] == {}
    assert [r["major"] for r in s3["rows"]] == sorted((r["major"] for r in s3["rows"]), key=["암보장", "뇌혈관보장", "심장보장", "공통보장"].index)
    assert {tuple(sorted(g["variants"])) for g in s3["waiting"]} == {(NEW_A, NEW_B)}


def test_매핑_검토_대기만_있는_칸은_빈자리로_세지_않는다():
    none, waiting = {"kind": "none"}, {"kind": "none", "waiting": True}
    ok = {"kind": "ok", "val": 1, "wait": 0, "red": [], "limit": None, "pend": False}
    assert compare.verdict(none, ok) == "n" and compare.verdict(waiting, ok) == "q"
    assert compare.verdict(ok, none) == "o" and compare.verdict(ok, waiting) == "q"
    assert compare.verdict(none, none) == ""
    assert compare.verdict({"kind": "unavail"}, ok) == "u" and compare.verdict(ok, {"kind": "unavail"}) == "v"
    assert compare.verdict({**ok, "val": None}, ok) == "x"


def test_처음_보여_줄_열은_기준과_심사_유형이_같은_종형이다(data):
    s3 = compare.build(data, data.conds())
    assert s3["peers"][NEW_B] == [NEW_B, PRIV]                 # 일반심사끼리
    assert s3["peers"][NEW_A] == [NEW_A, NEW_B, PRIV]           # 같은 심사 유형이 없으면 전부
    tables = fake_tables()
    tables["sys_상품종형"].append(variant("HANWHALIFE_H2_eeeeee", "HANWHALIFE", "HANWHA_Y_2610", "HANWHA_Y|간편심사|3.2.5|갱신|표준형",
                                      "민영 시험보험 무배당", "간편가입형(2년)", "정밀비교", "간편심사", "3.2.5", (3, 2, 5, True, 6),
                                      "2026-10-01", None, "hp", "mp"))
    more = compare.build(Data(tables), [Cond()])
    assert more["peers"][NEW_A] == [NEW_A, "HANWHALIFE_H2_eeeeee"]


def test_매핑_검토_대기_요약(data):
    s3 = compare.build(data, data.conds())
    summary = s3["waitingSummary"]
    assert summary["groups"] == len(s3["waiting"]) == 2 and summary["lines"] == 4      # 두 종형에 같은 급부가 두 가지
    assert summary["withRec"] == 2 and dict(map(tuple, summary["byRec"])) == {"STD_CA_HOSP": 1, "STD_CM_SURG_GRADE": 1}
    assert summary["byOrg"] == [{"code": "EPOST", "name": data.org_name("EPOST"), "n": 2}]


def no_limit_tables():
    """민영사 종형의 가입 한도와 가입 나이 자료를 모두 비운다(공시 문서에 한도가 없는 회사)."""
    tables = fake_tables()
    for r in tables["sys_특약"]:
        if r["종형ID"] == PRIV:
            r["최소가입금액만원"] = r["최대가입금액만원"] = None
    tables["sys_가입조건"] = [r for r in tables["sys_가입조건"] if r["종형ID"] != PRIV]
    return tables


def test_가입_한도_자료가_없는_종형은_최대_가입_금액을_만들지_않는다():
    data = Data(no_limit_tables(), {"snapshot_at": "2026-11-18T17:00:00+09:00"})
    assert data.limit_gap(PRIV) == {"riders": 2, "noMax": 2, "noAge": True} and data.limit_gap(NEW_A) is None
    conds = data.conds()
    s3 = compare.build(data, conds)
    base = s3["bases"].index(NEW_B)
    for k in (0, cond_index(conds, 50), cond_index(conds, 85)):
        _, st = cell_at(s3, "STD_CA_DX_GENERAL", PRIV, k)
        assert st["kind"] == "ok" and st["vals"] == [None] and st["caps"] == [None] and "no" not in st   # 가입 불가가 아니라 한도 자료 없음
    assert cell_at(s3, "STD_CA_DX_GENERAL", PRIV, 0)[1]["vs"][base] == "x"                              # 우열 판정은 하지 않는다
    views = build.payload(data)
    assert views["variants"][PRIV]["gap"] == {"riders": 2, "noMax": 2, "noAge": True} and views["variants"][NEW_A]["gap"] is None
    assert views["s1"]["limitGaps"] == [{"code": "HANWHALIFE", "name": data.org_name("HANWHALIFE"), "variants": 1,
                                        "riders": 2, "noMax": 2, "noAge": 1}]
    assert views["s2"]["byVariant"][PRIV]["noCond"] is True

    # 화면 4: 한도가 없으면 급부표의 기준 가입금액을 넣어 두고 그 금액으로 환산한다
    vm = combo.variant_model(data, PRIV, conds)
    assert [(r["tid"].split("_T")[1], r["ref"], r["max"], r["lim"][0]) for r in vm["riders"]] == [("main", None, None, None), ("pc", 1000, None, None)]
    rows = combo.evaluate(vm, 0, {f"{PRIV}_Tpc": 1000})["rows"]
    pay = combo.payouts(vm, {bid: data.benefit_view(bid) for bid in data.benefits}, rows)
    assert pay["groups"][0]["lines"][0]["val"] == 1000


def test_가입_한도가_있는_종형은_빈_곳_표시가_없다(data):
    assert all(data.limit_gap(v) is None for v in data.variants)
    assert overview.build(data)["limitGaps"] == []
    assert combo.variant_model(data, NEW_A, [Cond()])["riders"][1]["ref"] == 1000


def test_칸은_이_나이에_가입할_수_없는_줄을_따로_적는다():
    tables = fake_tables()
    for m in tables["hum_담보매핑"]:
        if m["급부ID"].endswith("_Tnursing_Bnca"):
            m["확정표준담보ID"] = "STD_CA_HOSP"                     # 가입 나이가 다른 두 특약의 급부를 한 표준담보에 잇는다
    data = Data(tables)
    conds = data.conds()
    s3 = compare.build(data, conds)
    cell, st = cell_at(s3, "STD_CA_HOSP", NEW_A, cond_index(conds, 75))
    assert [b.rsplit("_B", 1)[1] for b in cell["lines"]] == ["hca", "nca"]
    assert st["kind"] == "ok" and st["no"] == [1] and st["caps"] == [500, None]
    assert "no" not in cell_at(s3, "STD_CA_HOSP", NEW_A, cond_index(conds, 50))[1]


# ---------- 화면 4 ----------
def on_rows(result):
    return {r["tid"].split("_T")[1]: r["amount"] for r in result["rows"] if r["on"]}


def reasons(result, key):
    return [x["code"] for r in result["rows"] if r["tid"].endswith("_T" + key) for x in r["reasons"]]


def test_선행가입이_안_된_특약은_고를_수_없다(data):
    conds = data.conds()
    vm = combo.variant_model(data, NEW_A, conds)
    k = cond_index(conds, 50)
    alone = combo.evaluate(vm, k, {f"{NEW_A}_Tnursing": None})
    assert on_rows(alone) == {"main": 4000} and reasons(alone, "nursing") == ["need"]
    both = combo.evaluate(vm, k, {f"{NEW_A}_Tnursing": None, f"{NEW_A}_Thosp": None})
    assert on_rows(both) == {"main": 4000, "hosp": 1000, "nursing": 1000}


def test_최대연동_특약은_주계약_가입금액을_넘지_못한다(data):
    conds = data.conds()
    vm = combo.variant_model(data, NEW_A, conds)
    result = combo.evaluate(vm, cond_index(conds, 50), {f"{NEW_A}_Tmain": 1500, f"{NEW_A}_Tcancer": 3000, f"{NEW_A}_Tsurg": 700})
    assert on_rows(result) == {"main": 1500, "cancer": 1500, "surg": 700}
    cancer = next(r for r in result["rows"] if r["tid"].endswith("_Tcancer"))
    assert cancer["clamped"] is True and cancer["hi"] == 1500 and cancer["lo"] == 500


def test_가입금액은_최소와_나이_구간_한도_사이로_맞춘다(data):
    conds = data.conds()
    vm = combo.variant_model(data, NEW_A, conds)
    old = combo.evaluate(vm, cond_index(conds, 70), {f"{NEW_A}_Tcancer": 4000, f"{NEW_A}_Thosp": 100})
    assert on_rows(old) == {"main": 2000, "cancer": 2000, "hosp": 500}
    too_old = combo.evaluate(vm, cond_index(conds, 85), {f"{NEW_A}_Tcancer": None})
    assert on_rows(too_old) == {} and reasons(too_old, "main") == ["age"] and reasons(too_old, "cancer") == ["age", "main"]
    woman = combo.evaluate(vm, cond_index(conds, 21, "F"), {f"{NEW_A}_Tsurg": None})
    assert reasons(woman, "surg") == ["age"]


def test_최대로_담기는_제약_안에서_모두_최대_금액이다(data):
    conds = data.conds()
    vm = combo.variant_model(data, NEW_A, conds)
    everything = {r["tid"]: None for r in vm["riders"]}
    assert on_rows(combo.evaluate(vm, cond_index(conds, 50), everything)) == {"main": 4000, "cancer": 4000, "hosp": 1000, "nursing": 1000, "surg": 1000}
    assert on_rows(combo.evaluate(vm, cond_index(conds, 75), everything)) == {"main": 2000, "cancer": 2000, "hosp": 500}
    # 화면 3의 "최대로 가입했을 때"와 같은 금액이어야 한다
    for r in combo.evaluate(vm, cond_index(conds, 50), everything)["rows"]:
        assert r["amount"] == data.rider_cap(r["tid"], Cond(age=50, sex="M")).amount


def hand_model(rules, mins=None):
    riders = [{"tid": t, "min": (mins or {}).get(t, 100), "max": 1000, "ok": [True], "lim": [1000], "limPend": [False], "noCond": False, "benefits": []}
              for t in ("main", "a", "b")]
    return {"main": "main", "riders": riders, "rules": rules, "skipped": []}


def test_배타선택과_의무부가와_금액_조건(data):
    exclusive = hand_model([{"type": "배타선택", "base": "a", "target": "b", "num": None, "unit": None}])
    result = combo.evaluate(exclusive, 0, {"a": None, "b": None})
    assert on_rows({"rows": [{**r, "tid": "x_T" + r["tid"]} for r in result["rows"]]}) == {"main": 1000, "a": 1000}
    assert [x["code"] for r in result["rows"] if r["tid"] == "b" for x in r["reasons"]] == ["exclusive"]

    forced = combo.evaluate(hand_model([{"type": "의무부가", "base": "a", "target": "b", "num": None, "unit": None}]), 0, {"a": 300})
    b = next(r for r in forced["rows"] if r["tid"] == "b")
    assert b["on"] and b["forced"] and b["amount"] == 1000

    floor = hand_model([{"type": "선행가입", "base": "main", "target": "a", "num": 2000, "unit": "만원"}])
    assert [x["code"] for r in combo.evaluate(floor, 0, {"a": None})["rows"] if r["tid"] == "a" for x in r["reasons"]] == ["needAmount"]

    small = hand_model([{"type": "최대연동", "base": "main", "target": "a", "num": 0.5, "unit": "비율"}], mins={"a": 800})
    assert [x["code"] for r in combo.evaluate(small, 0, {"a": None})["rows"] if r["tid"] == "a" for x in r["reasons"]] == ["belowMin"]


def test_모르는_제약유형은_적용하지_않고_따로_모은다(data):
    tables = fake_tables()
    tables["sys_결합제약"].append(rule(NEW_A, "main", "surg", "새로운제약"))
    vm = combo.variant_model(Data(tables), NEW_A, [Cond()])
    assert [r["type"] for r in vm["skipped"]] == ["새로운제약"] and len(vm["rules"]) == 3


def test_실제_지급액은_가입금액에_비례하고_감액_금액을_함께_낸다(data):
    conds = data.conds()
    vm = combo.variant_model(data, NEW_A, conds)
    views = {bid: data.benefit_view(bid) for bid in data.benefits}
    rows = combo.evaluate(vm, cond_index(conds, 50), {f"{NEW_A}_Tcancer": 2000, f"{NEW_A}_Thosp": 500})["rows"]
    result = combo.payouts(vm, views, rows)
    groups = {g["std"]: g for g in result["groups"]}
    cancer = groups["STD_CA_DX_GENERAL"]["lines"][0]
    assert cancer["val"] == 2000 and cancer["reduced"] == [[12, 1000]]
    surgery = groups["STD_CA_SURG"]
    assert [l["val"] for l in surgery["lines"]] == [150, 50] and surgery["lines"][surgery["rep"]]["val"] == 150
    assert groups["STD_CA_HOSP"]["lines"][0]["val"] == 2.5
    assert "STD_CM_SURG_GRADE" not in groups                 # 고르지 않은 특약
    assert {l["bid"] for l in result["others"]} == {f"{NEW_A}_Tmain_Bdeath", f"{NEW_A}_Thosp_Bhth"}   # 대상외와 매핑 검토 대기


# ---------- 가입금액 대비 비율로 적힌 급부(삼성화재) ----------
SF = "SAMSUNGFIRE_S1_ffffff"


def ratio_tables(caps=False, epost_caps=True):
    """급부가 금액 대신 가입금액 대비 지급률로 적힌 종형을 더한다. 시트에는 기준가입금액만원 100, 기준지급금액만원 = 지급률(%)로 적는다.

    caps가 거짓이면 공시 문서에 특약 가입 한도가 없는 꼴이다. epost_caps가 거짓이면 우체국 2종(기준 종형)의 가입 한도 자료를 비운다.
    """
    tables = fake_tables()
    tables["sys_상품종형"].append(variant(SF, "SAMSUNGFIRE", "SAMSUNGFIRE_Z_2610", "SAMSUNGFIRE_Z|일반심사|일반|갱신|표준형",
                                      "무배당 시험화재 건강보험", "1종", "정밀비교", "일반심사", "일반", (None, None, None, None, None),
                                      "2026-10-01", None, "hs", "ms"))
    tables["sys_특약"] += [rider(SF, "main", "기본계약", None, 1000 if caps else None, "주계약"),
                         rider(SF, "ca", "암 진단비", None, 3000 if caps else None)]
    rows = [
        (benefit(SF, "main", "death", "상해사망", "주급부", 100, limit=None, base=100), "대상외", None),
        (benefit(SF, "ca", "ca", "암 진단비", "주급부", 100, 90, (12, 0.5), base=100), "자동확정", "STD_CA_DX_GENERAL"),
        (benefit(SF, "ca", "th", "유사암 진단비", "부수급부", 20, base=100), "자동확정", "STD_CA_DX_PSEUDO"),
    ]
    for b, state, sid in rows:
        b[BASIS_COLUMN] = RATIO_BASIS                 # 스키마에 아직 없는 선택 열이라 row()를 거치지 않고 붙인다
        tables["sys_급부"].append(b)
        tables["hum_담보매핑"].append(mapped(b["급부ID"], state, sid))
    if not epost_caps:
        for r in tables["sys_특약"]:
            if r["종형ID"] == NEW_B:
                r["최소가입금액만원"] = r["최대가입금액만원"] = None
        tables["sys_가입조건"] = [r for r in tables["sys_가입조건"] if r["종형ID"] != NEW_B]
    return tables


def test_비율_급부는_지급률을_싣고_열이_없거나_비면_금액_급부다():
    tables = ratio_tables()
    empty = next(b for b in tables["sys_급부"] if b["급부ID"] == f"{NEW_B}_Tcancer_Bca")
    empty[BASIS_COLUMN] = ""
    no_pay = next(b for b in tables["sys_급부"] if b["급부ID"] == f"{SF}_Tmain_Bdeath")
    no_pay["기준지급금액만원"] = None
    data = Data(tables)

    cancer = data.benefit_view(f"{SF}_Tca_Bca")
    assert cancer["ratio"] is True and cancer["rate"] == 100 and (cancer["base"], cancer["pay"]) == (100, 100)   # 환산에 쓰는 값은 그대로
    assert data.benefit_view(f"{SF}_Tca_Bth")["rate"] == 20
    death = data.benefit_view(f"{SF}_Tmain_Bdeath")                                      # 지급률을 모르는 비율 급부
    assert death["ratio"] is True and death["pay"] is None and death["rate"] is None
    assert BASIS_COLUMN not in data.benefits[f"{NEW_A}_Tcancer_Bca"]                       # 열이 없는 행
    for bid in (f"{NEW_A}_Tcancer_Bca", f"{NEW_B}_Tcancer_Bca"):                           # 열이 없는 행, 비어 있는 행
        view = data.benefit_view(bid)
        assert view["ratio"] is False and view["rate"] is None and (view["base"], view["pay"]) == (1000, 1000)

    for value, expected in [(None, False), ("", False), ("금액", False), ("비율", False), ("가입금액비율", True), (" 가입금액비율 ", True)]:
        assert is_ratio({BASIS_COLUMN: value}) is expected, value
    assert is_ratio({}) is False
    assert pay_rate(20, 100) == 20 and pay_rate(500, 1000) == 50 and pay_rate(0.3, 100) == 0.3 and pay_rate(2.5, 100) == 2.5
    assert pay_rate(None, 100) is None and pay_rate(5, 0) is None and pay_rate(5, None) is None

    payload = build.payload(data)
    assert payload["benefits"][f"{SF}_Tca_Bth"]["ratio"] is True and payload["benefits"][f"{NEW_A}_Tcancer_Bca"]["ratio"] is False
    assert build.read_payload(build.render(data)) == json.loads(json.dumps(payload, ensure_ascii=False))   # 줄여 적어도 그대로


def test_가입_한도가_없는_비율_급부_칸은_최대_가입_금액을_만들지_않는다():
    data = Data(ratio_tables())
    s3 = compare.build(data, data.conds())
    assert SF in s3["variants"] and SF in s3["peers"][NEW_B]
    cell, st = cell_at(s3, "STD_CA_DX_GENERAL", SF, 0)
    assert st["kind"] == "ok" and st["vals"] == [None] and st["caps"] == [None] and "no" not in st
    assert data.benefit_view(cell["lines"][st["rep"]])["rate"] == 100        # 화면은 이 줄을 "가입금액의 100%"로 적는다


def test_금액_급부와_비율_급부가_만나도_양쪽_다_최대_가입_금액이_있을_때만_판정한다():
    def verdicts(tables):
        data = Data(tables)
        s3 = compare.build(data, data.conds())
        assert s3["bases"] == [NEW_A, NEW_B]
        out = {}
        for sid in ("STD_CA_DX_GENERAL", "STD_CA_DX_PSEUDO"):
            _, st = cell_at(s3, sid, SF, 0)
            out[sid] = (st["vals"][st["rep"]], st["vs"])
        return out

    # 양쪽 다 가입 한도가 있으면 비율 급부도 한도 × 지급률로 환산해 지금 규칙대로 가린다
    # 암 진단비: 3,000만원 × 100% 대 우체국 4,000만원 / 유사암: 3,000만원 × 20% 대 우체국 800만원(감액 있음)
    both = verdicts(ratio_tables(caps=True))
    assert both == {"STD_CA_DX_GENERAL": (3000, ["w-==.", "w-==."]), "STD_CA_DX_PSEUDO": (600, ["m-=+.", "m-=+."])}
    # 비율 급부 쪽에 가입 한도가 없으면 판정하지 않는다
    assert verdicts(ratio_tables()) == {"STD_CA_DX_GENERAL": (None, ["x", "x"]), "STD_CA_DX_PSEUDO": (None, ["x", "x"])}
    # 기준 종형(금액 급부) 쪽에 가입 한도가 없어도 판정하지 않는다. 한도가 있는 다른 기준 종형과는 판정한다
    assert verdicts(ratio_tables(caps=True, epost_caps=False)) == {
        "STD_CA_DX_GENERAL": (3000, ["w-==.", "x"]), "STD_CA_DX_PSEUDO": (600, ["m-=+.", "x"])}
    # 판정은 지급기준구분과 관계없다: 같은 내용을 금액으로 적은 급부(가입 1,000만원에 1,000만원, 200만원)와 결과가 같다
    as_amount = ratio_tables(caps=True)
    for b in as_amount["sys_급부"]:
        if b.pop(BASIS_COLUMN, None):
            b["기준가입금액만원"], b["기준지급금액만원"] = 1000, b["기준지급금액만원"] * 10
    assert verdicts(as_amount) == both


def ratio_cand(i, pay, base, ratio, val=None):
    return {**cand(i, "주급부", val, pay=pay), "base": base, "ratio": ratio}


def test_최대_가입_금액을_모르면_비율_급부는_지급률로_견주어_대표를_고른다():
    # 비율 급부의 기준지급금액(지급률 100)과 금액 급부의 기준지급금액(500만원)은 단위가 달라 바로 견주지 않는다
    assert compare.pick_rep([ratio_cand(0, 500, 1000, False), ratio_cand(1, 100, 100, True)]) == 1    # 50% 대 100%
    assert compare.pick_rep([ratio_cand(0, 500, 1000, True), ratio_cand(1, 100, 100, True)]) == 1     # 비율 급부끼리도 지급률로
    # 금액 급부끼리는 지금처럼 기준지급금액으로 견주고, 최대 가입 금액을 알면 그 금액이 먼저다
    assert compare.pick_rep([ratio_cand(0, 500, 1000, False), ratio_cand(1, 300, 100, False)]) == 0
    assert compare.pick_rep([ratio_cand(0, 500, 1000, False, val=2000), ratio_cand(1, 100, 100, True, val=1000)]) == 0


def mixed_ratio_tables(pay):
    """삼성화재 암 진단비 특약(가입금액의 100%)에 금액으로 적힌 급부(가입 1,000만원에 pay만원)를 더한다."""
    tables = ratio_tables()
    b = benefit(SF, "ca", "cash", "암 진단 생활자금", "주급부", pay, base=1000)
    tables["sys_급부"].append(b)
    tables["hum_담보매핑"].append(mapped(b["급부ID"], "자동확정", "STD_CA_DX_GENERAL"))
    return tables


def test_가입_한도가_없는_칸에서_금액_급부와_비율_급부가_섞이면_지급률로_대표를_고른다():
    data = Data(mixed_ratio_tables(500))                 # 기준지급금액은 500이 100보다 크지만 지급률은 50%로 100%보다 낮다
    cell, st = cell_at(compare.build(data, data.conds()), "STD_CA_DX_GENERAL", SF, 0)
    assert st["vals"] == [None, None] and data.benefits[cell["lines"][st["rep"]]]["원시급부명"] == "암 진단비"


def test_금액_급부와_비율_급부가_섞인_특약은_금액_급부의_기준_가입금액을_처음_값으로_쓴다():
    data = Data(mixed_ratio_tables(50))                  # 대표 순서(기준지급금액 큰 순)로는 비율 급부(100)가 앞선다
    vm = combo.variant_model(data, SF, data.conds())
    assert [(r["tid"].split("_T")[1], r["ref"], r["refRatio"]) for r in vm["riders"]] == [("main", 100, True), ("ca", 1000, False)]
    assert combo.reference_benefit(data, f"{SF}_Tca") == f"{SF}_Tca_Bcash"


def test_비율_급부의_개정_전후는_지급률과_지급_기준이_달라졌을_때만_적는다():
    def view(pay, base, ratio):
        return {"pay": pay, "base": base, "ratio": ratio, "rate": pay_rate(pay, base) if ratio else None,
                "red": [], "wait": 0, "limit": None, "std": "STD_CA_DX_GENERAL"}

    def pay_items(old, new):
        return [(i["field"], i["dir"]) for i in revision.benefit_changes(old, new, None, None)]

    assert pay_items(view(50, 100, True), view(500, 1000, True)) == []              # 같은 50%를 다른 숫자로 적었을 뿐
    assert pay_items(view(50, 100, True), view(60, 100, True)) == [("pay", "+")]
    assert pay_items(view(50, 100, False), view(50, 100, True)) == [("pay", None)]  # 금액 급부가 비율 급부로 바뀜
    assert pay_items(view(50, 100, True), view(500, 1000, False)) == [("pay", None)]
    assert pay_items(view(50, 100, False), view(500, 1000, False)) == [("pay", "=")]  # 금액 급부끼리는 지금 규칙 그대로
    assert pay_items(view(50, 100, False), view(50, 100, False)) == []


SF_OLD = "SAMSUNGFIRE_S0_hhhhhh"


def ratio_revision_tables():
    """삼성화재 종형의 직전 개정판을 더한다. 암 진단비는 같은 100%를 다른 숫자(가입 1,000에 1,000)로 적었고,
    상해사망은 같은 숫자(가입 100에 100)를 금액 급부로 적었다. 유사암은 두 판이 같다."""
    tables = ratio_tables()
    tables["sys_상품종형"].append(variant(SF_OLD, "SAMSUNGFIRE", "SAMSUNGFIRE_Z_2604", "SAMSUNGFIRE_Z|일반심사|일반|갱신|표준형",
                                      "무배당 시험화재 건강보험", "1종", "직전개정시연", "일반심사", "일반", (None, None, None, None, None),
                                      "2026-04-01", "2026-09-30", "hs0", "ms0"))
    tables["sys_특약"] += [rider(SF_OLD, "main", "기본계약", None, None, "주계약"), rider(SF_OLD, "ca", "암 진단비", None, None)]
    rows = [
        (benefit(SF_OLD, "main", "death", "상해사망", "주급부", 100, limit=None, base=100), False, "대상외", None),
        (benefit(SF_OLD, "ca", "ca", "암 진단비", "주급부", 1000, 90, (12, 0.5), base=1000), True, "자동확정", "STD_CA_DX_GENERAL"),
        (benefit(SF_OLD, "ca", "th", "유사암 진단비", "부수급부", 20, base=100), True, "자동확정", "STD_CA_DX_PSEUDO"),
    ]
    for b, ratio, state, sid in rows:
        if ratio:
            b[BASIS_COLUMN] = RATIO_BASIS
        tables["sys_급부"].append(b)
        tables["hum_담보매핑"].append(mapped(b["급부ID"], state, sid))
    return tables


def test_비율_급부_종형의_개정_전후는_지급률이_같으면_지급액_변화로_적지_않는다():
    data = Data(ratio_revision_tables())
    assert (SF_OLD, SF) in revision.variant_pairs(data)
    diff = revision.diff_pair(data, SF_OLD, SF)
    items = {b["new"].rsplit("_B", 1)[1]: [(i["field"], i["dir"]) for i in b["items"]] for c in diff["changes"] for b in c["benefits"]}
    assert items == {"death": [("pay", None)]}            # 암 진단비는 같은 100%, 상해사망은 금액 급부에서 비율 급부로 바뀜


def test_조합_화면은_비율_급부도_넣은_가입금액에_지급률을_곱한다():
    data = Data(ratio_tables())
    conds = data.conds()
    vm = combo.variant_model(data, SF, conds)
    # 가입 한도가 없어 처음에 넣어 둘 금액은 급부표의 100만원이고, 그 값이 비율 급부에서 왔다는 표시가 붙는다
    assert [(r["tid"].split("_T")[1], r["ref"], r["refRatio"], r["max"], r["lim"][0]) for r in vm["riders"]] == [
        ("main", 100, True, None, None), ("ca", 100, True, None, None)]
    assert not any(r["refRatio"] for r in combo.variant_model(data, NEW_A, conds)["riders"])
    assert not any(r["refRatio"] for r in combo.variant_model(Data(no_limit_tables()), PRIV, conds)["riders"])
    views = {bid: data.benefit_view(bid) for bid in data.benefits}
    for amount in (100, 3000):
        rows = combo.evaluate(vm, 0, {f"{SF}_Tmain": 100, f"{SF}_Tca": amount})["rows"]
        result = combo.payouts(vm, views, rows)
        groups = {g["std"]: g["lines"] for g in result["groups"]}
        assert groups["STD_CA_DX_GENERAL"] == [{"bid": f"{SF}_Tca_Bca", "val": amount, "reduced": [[12, amount * 0.5]]}]
        assert groups["STD_CA_DX_PSEUDO"][0]["val"] == pytest.approx(amount * 0.2)
        assert [l["bid"] for l in result["others"]] == [f"{SF}_Tmain_Bdeath"]

    # 가입 한도가 있으면 "최대로 담기"의 지급액이 화면 3의 최대 가입 기준 금액(한도 × 지급률)과 같다
    capped = Data(ratio_tables(caps=True))
    vm = combo.variant_model(capped, SF, capped.conds())
    assert [r["ref"] for r in vm["riders"]] == [100, 100] and [r["max"] for r in vm["riders"]] == [1000, 3000]
    rows = combo.evaluate(vm, 0, {r["tid"]: None for r in vm["riders"]})["rows"]
    result = combo.payouts(vm, {bid: capped.benefit_view(bid) for bid in capped.benefits}, rows)
    s3 = compare.build(capped, capped.conds())
    for g in result["groups"]:
        _, st = cell_at(s3, g["std"], SF, 0)
        assert g["lines"][g["rep"]]["val"] == pytest.approx(st["vals"][st["rep"]])
    assert sorted(g["lines"][g["rep"]]["val"] for g in result["groups"]) == [600, 3000]


# ---------- 화면 5 ----------
def test_개정_전후는_종형계보키로_짝짓는다(data):
    assert revision.variant_pairs(data) == [(OLD_A, NEW_A)]


def test_개정_전후_차이(data):
    diff = revision.diff_pair(data, OLD_A, NEW_A)
    assert [data.riders[t]["특약계보키"] for t in diff["removedRiders"]] == ["focus"]
    assert sorted(data.riders[t]["특약계보키"] for t in diff["addedRiders"]) == ["nursing", "surg"]
    by_rider = {data.riders[c["old"]]["특약계보키"]: c for c in diff["changes"]}
    assert set(by_rider) == {"cancer", "hosp"}

    cancer = by_rider["cancer"]
    assert cancer["rider"] == [{"field": "range", "old": [500, 3000], "new": [500, 4000], "dir": None}]
    items = {b["old"].rsplit("_B", 1)[1]: {i["field"]: i for i in b["items"]} for b in cancer["benefits"]}
    assert items["ca"]["red"] == {"field": "red", "old": [[24, 0.5]], "new": [[12, 0.5]], "dir": "+"}
    assert items["ca"]["top"]["old"] == 3000 and items["ca"]["top"]["new"] == 4000 and "pay" not in items["ca"]
    assert items["th"]["pay"] == {"field": "pay", "old": [1000, 100], "new": [1000, 200], "dir": "+"}
    assert items["th"]["top"]["old"] == 300 and items["th"]["top"]["new"] == 800

    hosp = by_rider["hosp"]
    assert [(b["old"].rsplit("_B", 1)[1], [i["field"] for i in b["items"]]) for b in hosp["benefits"]] == [("hca", ["limit"])]
    assert hosp["added"] == [f"{NEW_A}_Thosp_Bhth"] and hosp["removed"] == []

    gate = {g["field"]: (g["old"], g["new"]) for g in diff["gate"]}
    assert gate["hospYears"] == (5, 2) and gate["months"] == (3, 3)
    assert diff["ages"]["old"]["M"][0]["lo"] == 30 and diff["ages"]["new"]["M"][0]["lo"] == 20


def test_이름이_달라진_급부는_비슷한_이름끼리_잇는다(data):
    old = [data.benefit_view(f"{OLD_A}_Thosp_B{c}") for c in ("hca", "open", "closed")]
    new = [data.benefit_view(f"{NEW_A}_Thosp_B{c}") for c in ("hca", "hth", "open", "closed")]
    pairs, removed, added = revision.match_benefits(old, new)
    assert {(o["name"], n["name"], how) for o, n, how in pairs} == {
        ("암직접치료입원보험금(암)", "암직접치료입원보험금(암)", "이름"),
        ("암수술보험금(관혈수술)", "암수술보험금(암·관혈수술)", "비슷한 이름"),
        ("암수술보험금(비관혈수술)", "암수술보험금(암·비관혈수술)", "비슷한 이름")}
    assert removed == [] and [n["name"] for n in added] == ["암직접치료입원보험금(갑상선암 등)"]


def test_괄호_안_설명만_바뀐_급부가_엉뚱한_급부에_이어지지_않는다():
    def view(code, name):
        return {"id": code, "name": name, "std": None}
    old = [view("o1", "재해골절보험금(재해)"), view("o2", "재해깁스치료보험금(재해)")]
    new = [view("n1", "재해화상진단보험금(재해화상)"), view("n2", "재해골절(치아파절제외)보험금(재해골절)"),
           view("n3", "재해깁스치료(부목제외)보험금(재해깁스치료)")]
    pairs, removed, added = revision.match_benefits(old, new)
    assert {(o["id"], n["id"]) for o, n, _ in pairs} == {("o1", "n2"), ("o2", "n3")}
    assert removed == [] and [n["id"] for n in added] == ["n1"]


def test_시간선은_적용시작일과_판매종료일로_그린다(data):
    timeline = revision.build(data)["timeline"]
    assert timeline["from"] == "2025-04-03" and timeline["to"] == "2026-11-18"


# ---------- 화면 6, 화면 1 ----------
def test_작업_기록_요약(data):
    s6 = worklog.build(data)
    summary = s6["summary"]
    steps = {s["step"]: s for s in summary["byStep"]}
    assert [s["step"] for s in summary["byStep"]] == ["추출", "코드대조", "판정", "재추출", "사람검토이관"]
    assert (steps["판정"]["통과"], steps["사람검토이관"]["보류"], steps["재추출"]["통과"], steps["재추출"]["반려"]) == (2, 6, 1, 1)
    assert summary["retry"]["adopted"] == 1 and summary["retry"]["kept"] == 1
    assert summary["review"]["count"] == 6 and summary["review"]["targets"] == 6
    assert sorted(summary["review"]["status"]) == sorted([
        "검토 대기", "검토 대기", "검토 대기", "나중 실행에서 다시 판정됨", "지금 사본에 없는 행", "매핑 대기"])
    assert {m["model"]: m["n"] for m in summary["byModel"]}["gemini-decision-1"] == 8
    assert summary["review"]["byStatus"] == [("검토 대기", 3), ("나중 실행에서 다시 판정됨", 1), ("매핑 대기", 1), ("지금 사본에 없는 행", 1)]
    assert len(s6["rows"]) == 12 and s6["rows"][0][s6["cols"].index("실행일시")] >= s6["rows"][-1][s6["cols"].index("실행일시")]
    assert s6["labels"][f"{NEW_A}_Tnursing_Bnca"].endswith("요양병원암입원보험금(암)")


def test_화면1은_자료에_있는_것만_센다(data):
    s1 = overview.build(data)
    assert s1["trends"]["total"] == 2 and s1["trends"]["shown"] == 1         # 통과 기준에 못 미친 소식은 내지 않는다
    assert [o["code"] for o in s1["orgs"]] == ["EPOST", "HANWHALIFE"]
    assert s1["counts"]["premiums"] == 0 and s1["counts"]["waiting"] == 4


def test_자료_글자는_script_안에서도_안전하다():
    text = build.embed_json({"사유": "</script><script>alert(1)</script> <!-- x"})
    assert "<" not in text and json.loads(text)["사유"].startswith("</script>")


# ---------- 자료 줄여 적기 ----------
def test_줄여_적은_자료는_그대로_되살아난다():
    row_a = {"id": "EPOST_X_T1_B1", "name": "암진단보험금(암)", "ok": [True] * 6, "lim": [None] * 5, "by": [0, 0, 0, 0], "few": [1, 1, 1]}
    row_b = {"id": "EPOST_X_T1_B2", "name": "암진단보험금(암)", "ok": [True, False, True, True], "lim": [4000.0] * 4, "by": [0, 1], "few": []}
    sample = {
        "rows": [row_a, row_b, dict(row_a, id="EPOST_X_T1_B3")],
        "byId": {"EPOST_X_T1_B1": row_a, "EPOST_X_T1_B2": row_b},
        "labels": {"EPOST_X_T1_B1": "시험건강보험 2606 · 무배당 암진단특약 2606 · 암진단보험금(암)",
                   "EPOST_X_T1_B2": "시험건강보험 2606 · 무배당 암진단특약 2606 · 암진단보험금(갑상선암 등)"},
        "odd": ["~물결로 시작", "~~두 번", "~0", "", " · ", "가 · ", {"~=": 1}, {"~#": [1]}, {"~@": {}}, {"~+": "x"}, {"~0": "~0"}],
        "mixed": [1, True, 1.0, "1", None], "ones": [1, 1, 1, 1], "trues": [True, True, True, True], "mixrun": [1, True, 1, True],
        "nested": [[0, 0, 0, 0], [[], {}]], "empty": {}, "text": "한 번만 나오는 글자", "~key": 1,
    }
    packed = json.loads(json.dumps(pack.pack(sample), ensure_ascii=False))
    back = pack.unpack(packed)
    assert back == sample
    assert [type(x) for x in back["mixrun"]] == [int, bool, int, bool] and back["trues"][0] is True and back["ones"][0] is not True
    assert len(json.dumps(packed, ensure_ascii=False)) < len(json.dumps(sample, ensure_ascii=False))


def test_가짜_자료로도_빌드된다(data):
    html = build.render(data)
    payload = build.read_payload(html)
    assert payload == json.loads(json.dumps(build.payload(data), ensure_ascii=False))   # 줄여 적어도 내용은 그대로다
    assert payload["variantOrder"] == [NEW_A, NEW_B, OLD_A, PRIV]
    assert payload["variants"][NEW_A]["product"] == "시험건강보험 2606" and payload["variants"][NEW_A]["kind"] == "1종(간편가입325)"
    assert payload["defaults"] == {"age": 50, "sex": "M", "maxAge": 120}
    assert payload["conds"][0] is None and payload["conds"][1]["lo"] == 0


# ---------- 실제 사본 ----------
EXTERNAL = [
    r"<script\b[^>]*\bsrc\s*=",                                    # 밖에서 불러오는 스크립트
    r"<link\b",                                                    # 스타일·글꼴 파일
    r"<(?:img|iframe|video|audio|source|embed|object|picture)\b",  # 밖에서 불러오는 그림·영상
    r"@import",
    r"url\(\s*['\"]?\s*(?:https?:)?//",
    r"\b(?:src|href|srcset|action|poster)\s*=\s*['\"]?\s*(?:https?:)?//",
    r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|importScripts|new\s+Image\b",
]


@pytest.fixture(scope="module")
def real():
    return load(SNAPSHOT)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("site") / "index.html"
    info = build.build_site(SNAPSHOT, out)
    html = out.read_text(encoding="utf-8")
    return info, html, build.read_payload(html)


def test_실제_자료로_빌드되고_외부_자원을_부르지_않는다(built):
    info, html, payload = built
    assert info["variants"] == len(payload["variants"]) > 0
    assert info["bytes"] == len(html.encode("utf-8")) < 4_000_000   # 자료가 열 배로 늘어도 한 파일 4MB를 넘기지 않는다
    for pattern in EXTERNAL:
        found = re.search(pattern, html, re.I)
        assert found is None, f"외부 자원 참조: {html[max(0, found.start() - 40):found.end() + 60]!r}"
    assert "/*__" not in html                                      # 채우지 않은 자리가 없어야 한다
    assert html.count("<script") == 3 and html.count("<style") == 1


def test_실제_자료_화면_구성(built, real):
    _, _, payload = built
    meta = json.loads((SNAPSHOT / "meta.json").read_text(encoding="utf-8"))
    assert payload["meta"]["snapshotAt"] == meta["snapshot_at"]
    assert len(payload["s6"]["rows"]) == meta["row_counts"]["sys_작업로그"]
    assert len(payload["benefits"]) == meta["row_counts"]["sys_급부"]
    roles = {v["id"]: v["role"] for v in payload["variants"].values()}
    assert all(roles[v] == "정밀비교" for v in payload["s3"]["variants"]) and payload["s3"]["variants"] == payload["s4"]["variants"]
    assert payload["s3"]["defaultBase"] in payload["s3"]["bases"]
    for pair in payload["s5"]["pairs"]:
        assert real.variants[pair["old"]]["종형계보키"] == real.variants[pair["new"]]["종형계보키"]
        assert real.variants[pair["old"]]["개정판ID"] != real.variants[pair["new"]]["개정판ID"]
    # 대기·대상외 급부는 어느 칸의 계산에도 들어가지 않는다
    for r in payload["s3"]["rows"]:
        for cell in r["cells"].values():
            assert all(payload["benefits"][b]["std"] == r["id"] for b in cell["lines"])
            assert all(payload["benefits"][b]["state"] == "대기" for b in cell["wait"])
            assert len(cell["by"]) == len(payload["conds"])
    assert payload["s1"]["counts"]["premiums"] == 0               # 보험료 자료는 없고, 화면도 보험료를 만들지 않는다


def test_실제_자료는_줄여_적어도_하나도_빠지지_않는다(built, real):
    _, html, payload = built
    full = json.loads(json.dumps(build.payload(real), ensure_ascii=False))
    assert payload == full
    raw = len(json.dumps(full, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    assert len(html.encode("utf-8")) < raw                          # 줄여 적은 HTML 전체가 원래 자료보다 작다
    # 작업 기록, 검토 대기 급부, 급부는 화면이 요약만 먼저 보여 줄 뿐 전부 실려 있다
    assert len(payload["s6"]["rows"]) == len(real.logs) == payload["s6"]["summary"]["total"]
    assert payload["s3"]["waitingSummary"]["groups"] == len(payload["s3"]["waiting"])
    waiting = {b for g in payload["s3"]["waiting"] for b in g["bids"]}
    compared = {bid for bid, b in payload["benefits"].items() if payload["riders"][b["tid"]]["vid"] in payload["s3"]["variants"]}
    assert waiting == {bid for bid in compared if payload["benefits"][bid]["state"] == "대기"}
    assert payload["s3"]["waitingSummary"]["lines"] == len(waiting)


def test_실제_자료에서_가입_한도가_없는_종형(built, real):
    _, _, payload = built
    gaps = {vid: v["gap"] for vid, v in payload["variants"].items() if v["gap"]}
    assert payload["s1"]["limitGaps"] and sum(g["variants"] for g in payload["s1"]["limitGaps"]) == len(gaps)
    for vid, gap in gaps.items():
        assert gap["riders"] == len(real.riders_of[vid]) and 0 <= gap["noMax"] <= gap["riders"]
    for vid in payload["s3"]["variants"]:
        if vid in gaps and gaps[vid]["noMax"] == gaps[vid]["riders"]:
            # 한도가 하나도 없는 종형: 어느 칸에도 최대 가입 기준 금액이 없고, 화면 4는 기준 가입금액을 넣어 둔다
            for r in payload["s3"]["rows"]:
                cell = r["cells"].get(vid)
                if cell:
                    assert all(v is None for st in cell["st"] for v in st.get("vals", []))
            assert all(r["max"] is None for r in payload["s4"]["byVariant"][vid]["riders"])
            assert any(r["ref"] for r in payload["s4"]["byVariant"][vid]["riders"])
    for base, peers in payload["s3"]["peers"].items():
        assert base in peers and set(peers) <= set(payload["s3"]["variants"])


def test_실제_자료의_지급기준구분(built, real):
    """지금 사본에는 지급기준구분 열이 없어 모두 금액 급부다. 열이 생긴 뒤에도 비율 급부가 아닌 줄은 지급률을 싣지 않는다."""
    _, _, payload = built
    for bid, b in payload["benefits"].items():
        assert b["ratio"] is is_ratio(real.benefits[bid])
        if not b["ratio"]:
            assert b["rate"] is None
    if not any(BASIS_COLUMN in b for b in real.benefits.values()):
        assert not any(b["ratio"] for b in payload["benefits"].values())
        assert not any(r["refRatio"] for vm in payload["s4"]["byVariant"].values() for r in vm["riders"])


def test_실제_자료의_칸_값은_환산식과_같다(built, real):
    _, _, payload = built
    conds = real.conds()
    checked = 0
    for r in payload["s3"]["rows"]:
        for vid, cell in r["cells"].items():
            for k in (0, cond_index(conds, 50), cond_index(conds, 70, "F")):
                st = cell["st"][cell["by"][k]]
                if st["kind"] != "ok":
                    continue
                b = real.benefits[cell["lines"][st["rep"]]]
                cap = real.rider_cap(b["특약ID"], conds[k])
                if cap.amount is None:        # 가입 한도가 공시 문서에 없는 특약(한화생명): 최대 가입 기준 금액을 만들지 않는다
                    assert st["vals"][st["rep"]] is None
                    continue
                assert st["vals"][st["rep"]] == pytest.approx(b["기준지급금액만원"] / b["기준가입금액만원"] * cap.amount)
                assert cap.amount <= real.riders[b["특약ID"]]["최대가입금액만원"]
                checked += 1
    assert checked > 50


# ---------- calc.js와 맞대기 ----------
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node가 없어 calc.js를 실행할 수 없음")
HARNESS = """
const calc = require(process.argv[1]);
let text = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', c => text += c).on('end', () => {
  const input = JSON.parse(text);
  if (input.packed) { process.stdout.write(JSON.stringify(calc.unpack(input.packed))); return; }
  const out = {money: (input.money || []).map(calc.money), percent: (input.percent || []).map(calc.percent), cases: []};
  for (const c of input.cases || []) {
    const result = calc.evaluate(input.models[c.model], c.k, c.want);
    out.cases.push({rows: result.rows, pay: calc.payouts(input.models[c.model], input.benefits, result.rows)});
  }
  process.stdout.write(JSON.stringify(out));
});
"""


def run_node(payload):
    done = subprocess.run([NODE, "-e", HARNESS, str(CALC_JS)], input=json.dumps(payload, ensure_ascii=False),
                          capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@needs_node
def test_금액_표기():
    amounts = [1000, 2.5, 0.5, 0.05, 10000, 12000, 1.5, 150, 2.5432, 0, None, 4000.0, 10000.5]
    assert run_node({"money": amounts})["money"] == [
        "1,000만원", "2만5천원", "5천원", "500원", "1억원", "1억 2,000만원", "1만5천원", "150만원", "2만5,432원", "0원", "자료 없음",
        "4,000만원", "1억 5천원"]


@needs_node
def test_지급률_표기():
    rates = [100, 20.0, 50, 2.5, 0.3, 1000, 33.333333, 0, None]
    assert run_node({"percent": rates})["percent"] == ["100%", "20%", "50%", "2.5%", "0.3%", "1,000%", "33.33%", "0%", "자료 없음"]


def cases_for(models, conds, seed=7):
    """종형마다 조건 몇 개에서: 아무것도 안 고름, 최대로 담기, 무작위 조합."""
    rng = random.Random(seed)
    picks = sorted({0, len(conds) - 1} | {rng.randrange(len(conds)) for _ in range(6)})
    cases = []
    for name, vm in models.items():
        tids = [r["tid"] for r in vm["riders"]]
        for k in picks:
            cases.append({"model": name, "k": k, "want": {}})
            cases.append({"model": name, "k": k, "want": {t: None for t in tids}})
            for _ in range(4):
                chosen = rng.sample(tids, rng.randint(1, len(tids)))
                cases.append({"model": name, "k": k, "want": {t: rng.choice([None, 100, 250, 500, 1000, 1500, 3000, 9000]) for t in chosen}})
    return cases


def assert_same_as_python(models, benefits, cases):
    got = run_node({"models": models, "benefits": benefits, "cases": cases})["cases"]
    assert len(got) == len(cases)
    for case, js in zip(cases, got):
        rows = combo.evaluate(models[case["model"]], case["k"], case["want"])["rows"]
        expected = json.loads(json.dumps({"rows": rows, "pay": combo.payouts(models[case["model"]], benefits, rows)}))
        assert js == expected, case


@needs_node
def test_calc_js는_Python_규칙과_결과가_같다_가짜_자료(data):
    conds = data.conds()
    models = {vid: combo.variant_model(data, vid, conds) for vid in (NEW_A, NEW_B, PRIV)}
    models["배타"] = hand_model([{"type": "배타선택", "base": "a", "target": "b", "num": None, "unit": None}])
    models["의무"] = hand_model([{"type": "의무부가", "base": "a", "target": "b", "num": None, "unit": None}])
    models["하한"] = hand_model([{"type": "선행가입", "base": "main", "target": "a", "num": 700, "unit": "만원"},
                               {"type": "최대연동", "base": "a", "target": "b", "num": 0.5, "unit": "비율"}], mins={"b": 300})
    for name in ("배타", "의무", "하한"):
        models[name]["riders"] = [{**r, "ok": [True] * len(conds), "lim": [1000] * len(conds)} for r in models[name]["riders"]]
    benefits = {bid: data.benefit_view(bid) for bid in data.benefits}
    assert_same_as_python(models, benefits, cases_for(models, conds))


@needs_node
def test_calc_js는_비율_급부도_Python_규칙과_결과가_같다():
    for tables in (ratio_tables(), ratio_tables(caps=True)):
        data = Data(tables)
        conds = data.conds()
        models = {vid: combo.variant_model(data, vid, conds) for vid in (SF, NEW_B)}
        benefits = {bid: data.benefit_view(bid) for bid in data.benefits}
        assert_same_as_python(models, benefits, cases_for(models, conds, seed=3))


PICK_HARNESS = """
const calc = require(process.argv[1]);
let text = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', c => text += c).on('end', () => { process.stdout.write(JSON.stringify(JSON.parse(text).map(calc.pickRep))); });
"""


@needs_node
def test_calc_js의_대표_고르기는_Python과_같다():
    rng = random.Random(5)
    pools = [[ratio_cand(0, 500, 1000, False), ratio_cand(1, 100, 100, True)], [ratio_cand(0, 500, 1000, True), ratio_cand(1, 100, 100, True)],
             [ratio_cand(0, 500, 1000, False), ratio_cand(1, 300, 100, False)]]
    for _ in range(200):
        pools.append([{**ratio_cand(i, rng.choice([None, 20, 50, 100, 500]), rng.choice([None, 0, 100, 1000]), rng.random() < 0.5,
                                    val=rng.choice([None, None, 100.0, 500.0])), "role": rng.choice(["주급부", "부수급부"]),
                       "wait": rng.choice([0, 90]), "name": f"급부{i}"} for i in range(rng.randint(1, 4))])
    done = subprocess.run([NODE, "-e", PICK_HARNESS, str(CALC_JS)], input=json.dumps(pools, ensure_ascii=False),
                          capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == [compare.pick_rep(p) for p in pools]
    data = Data(mixed_ratio_tables(500))
    models = {SF: combo.variant_model(data, SF, data.conds())}
    assert_same_as_python(models, {bid: data.benefit_view(bid) for bid in data.benefits}, cases_for(models, data.conds(), seed=9))


@needs_node
def test_calc_js는_Python_규칙과_결과가_같다_실제_자료(built):
    _, _, payload = built
    models = payload["s4"]["byVariant"]
    conds = payload["conds"]
    assert_same_as_python(models, payload["benefits"], cases_for(models, conds, seed=11))


@needs_node
def test_calc_js의_unpack은_Python과_같은_자료를_되살린다(data, real):
    odd = {"odd": ["~물결", "~~두 번", "~0", " · ", {"~=": 1}, {"~#": [1]}, {"~@": {}}, {"~+": "x"}], "run": [None] * 5, "t": [True] * 4,
           "rows": [{"a": "되풀이되는 긴 글자입니다", "b": [1, 2]}, {"a": "되풀이되는 긴 글자입니다", "b": []}]}
    for source in (odd, build.payload(data), build.payload(real)):
        full = json.loads(json.dumps(source, ensure_ascii=False))
        assert run_node({"packed": pack.pack(source)}) == full
