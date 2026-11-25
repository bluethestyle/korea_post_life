"""화면에 올릴 회사(config.SITE_ORGS)로 사본을 거르는 일(src/postlife/site/orgs.py).

시트와 사본에는 회사가 하나씩 더 들어오지만 화면 자료는 목록의 회사만 싣는다. 목록 밖 회사의 종형, 특약, 급부, 가입조건,
결합 제약, 보험료, 질병코드, 매핑 행과 그 행을 가리키는 작업 로그 줄이 빠지는지, 회사와 무관한 탭과 시장 소식은 그대로인지,
"all" 이면 거르지 않는지, 명령들이 커밋되는 자리에 기본과 다른 묶음을 쓰지 않는지 본다.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from postlife import config
from postlife.schema import TABS
from postlife.site import orgs as O
from postlife.site import worklog
from postlife.site.model import Data, load
from postlife.snapshot import KST, write_snapshot

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "snapshot"


def row(tab: str, **values):
    out = {c.name: None for c in TABS[tab].columns}
    assert not set(values) - set(out), set(values) - set(out)
    out.update(values)
    return out


def company(org: str, code: str) -> dict[str, list[dict]]:
    """한 회사의 종형 하나, 주계약과 특약, 급부 둘, 매핑, 가입조건, 결합 제약, 보험료, 질병코드."""
    vid = f"{org}_{code}_aaaaaa"
    main, rider = f"{vid}_Tmain", f"{vid}_Trider"
    b1, b2 = f"{rider}_Bone", f"{rider}_Btwo"
    return {
        "sys_상품종형": [row("sys_상품종형", 종형ID=vid, 개정판ID=f"{org}_X_2610", 모상품ID=f"{org}_X", 종형계보키=f"{org}_X_K",
                          기관코드=org, 공시상품코드=code, 공시상품명=f"{org} 건강보험", 종형명="일반형", 비교역할구분="정밀비교",
                          심사유형="일반심사", 간편고지약칭="일반", 적용시작일="2026-10-01", 요약서해시=f"S{org}",
                          사업방법서해시=f"M{org}")],
        "sys_특약": [row("sys_특약", 특약ID=main, 종형ID=vid, 특약계보키="main", 담보구분="주계약", 원시특약명="주계약",
                       최대가입금액만원=3000),
                    row("sys_특약", 특약ID=rider, 종형ID=vid, 특약계보키="rider", 담보구분="선택특약", 원시특약명="암진단특약",
                        최대가입금액만원=2000)],
        "sys_급부": [row("sys_급부", 급부ID=b, 특약ID=rider, 원시급부명=name, 급부역할="주급부", 기준가입금액만원=1000,
                       기준지급금액만원=1000, 면책기간일수=0, 근거문서종류="요약서", 근거문서쪽수=3)
                    for b, name in ((b1, "암진단비"), (b2, "유사암진단비"))],
        "hum_담보매핑": [row("hum_담보매핑", 급부ID=b, 검토상태="자동확정", 확정표준담보ID="STD_CA_DX", 매핑확률=0.97)
                       for b in (b1, b2)],
        "sys_가입조건": [row("sys_가입조건", 조건행ID=f"{vid}_Cone", 종형ID=vid, 특약ID=None, 보험기간구분="90세만기",
                          납입기간구분="20년납", 최저가입나이=15, 최고가입나이=60, 구간최대가입금액만원=3000)],
        "sys_결합제약": [row("sys_결합제약", 제약ID=f"{vid}_Rone", 종형ID=vid, 기준특약ID=main, 대상특약ID=rider,
                          제약유형="최대연동", 제약수치=1, 제약단위="비율")],
        "sys_보험료예시": [row("sys_보험료예시", 보험료행ID=f"{rider}_Pone", 특약ID=rider, 가입나이=40, 성별="M",
                           기준가입금액만원=1000, 월납보험료원=12000)],
        "sys_급부질병코드": [row("sys_급부질병코드", 질병매핑ID=f"{b1}_Kone", 급부ID=b1, KCD버전="KCD-8", 시작코드="C00",
                            끝코드="C97", 포함여부="포함")],
    }


def log(lid: str, tab: str, target: str, step: str = "판정", at: str = "2026-11-20T10:00:00+09:00"):
    return row("sys_작업로그", 로그ID=lid, 실행일시=at, 작업단계=step, 대상탭=tab, 대상행ID=target, 대상열="기준지급금액만원",
               결과="보류", 사유="시험")


def tables() -> dict[str, list[dict]]:
    """우체국(EPOST)과 목록 밖 회사(MERITZ)."""
    out: dict[str, list[dict]] = {name: [] for name in TABS}
    for org, code in (("EPOST", "P1"), ("MERITZ", "M1")):
        for tab, rows in company(org, code).items():
            out[tab] += rows
    out["hum_표준담보사전"] = [row("hum_표준담보사전", 표준담보ID="STD_CA_DX", 표준담보명="암 진단비", 보장대분류="암보장",
                                 급부유형="진단", 비교기준단위만원=1000, 사용여부=True)]
    out["hum_기준값"] = [row("hum_기준값", 기준키="REVIEW_MIN", 기준분류="판정구간", 기준명="검토 하한", 수치값=0.4)]
    out["sys_시장동향"] = [row("sys_시장동향", 동향ID="TRD_MERITZ_1", 수집주차="2026-W47", 발표일자="2026-11-12",
                             기관코드="MERITZ", 분류유형="신담보출시", 핵심요약="메리츠화재가 새 담보를 냈습니다.")]
    ep, me = "EPOST_P1_aaaaaa", "MERITZ_M1_aaaaaa"
    out["sys_작업로그"] = [
        log("L1", "sys_급부", f"{ep}_Trider_Bone", "사람검토이관"),
        log("L2", "sys_급부", f"{me}_Trider_Bone", "사람검토이관"),          # 목록 밖 회사의 검토 대기
        log("L3", "hum_담보매핑", f"{me}_Trider_Btwo"),
        log("L4", "sys_가입조건", f"{me}_Cone", "사람검토이관"),
        log("L5", "sys_결합제약", f"{me}_Rone"),
        log("L6", "sys_급부", "MERITZ_M9_bbbbbb_Tx_Bgone"),                 # 사본에서 사라진 행. 접두어로 회사를 정한다
        log("L7", "sys_급부", "EPOST_P9_bbbbbb_Tx_Bgone"),
        log("L8", "sys_시장동향", "Q|MERITZ|배타적사용권"),                  # 회사 탭이 아닌 줄은 그대로
        log("L9", "sys_보험료예시", f"{me}_Trider_Pone"),
        log("L10", "sys_급부질병코드", f"{me}_Trider_Bone_Kone"),
        log("L11", "sys_특약", f"{me}_Trider"),
        log("L12", "sys_상품종형", me),
    ]
    return out


def orgs_in(out, tab, key):
    return {str(r[key]).split("_")[0] for r in out[tab]}


def test_parse():
    assert O.parse(None) == tuple(config.SITE_ORGS) == ("EPOST", "HANWHALIFE", "SAMSUNGFIRE")
    assert O.parse("all") == O.parse(" ALL ") == O.ALL
    assert O.parse("epost, meritz,EPOST") == ("EPOST", "MERITZ")
    assert O.parse(["EPOST", "MERITZ"]) == ("EPOST", "MERITZ")
    with pytest.raises(ValueError):
        O.parse(" , ")
    assert O.is_default(("SAMSUNGFIRE", "EPOST", "HANWHALIFE")) and not O.is_default(O.ALL)
    assert not O.is_default(("EPOST", "HANWHALIFE", "SAMSUNGFIRE", "MERITZ"))


def test_rows_of_orgs_outside_the_list_are_dropped():
    src = tables()
    out = O.filter_tables(src, ("EPOST",))
    keys = {"sys_상품종형": "종형ID", "sys_특약": "특약ID", "sys_급부": "급부ID", "hum_담보매핑": "급부ID",
            "sys_가입조건": "조건행ID", "sys_결합제약": "제약ID", "sys_보험료예시": "보험료행ID", "sys_급부질병코드": "질병매핑ID"}
    for tab, key in keys.items():
        assert orgs_in(out, tab, key) == {"EPOST"}, tab
        assert len(out[tab]) * 2 == len(src[tab]), tab
    # 회사와 무관한 탭과 시장 소식(목록 밖 회사의 소식이어도)은 그대로
    for tab in ("hum_표준담보사전", "hum_기준값", "hum_표준질병군", "sys_시장동향"):
        assert out[tab] == src[tab], tab
    # 작업 로그: 목록 밖 회사의 행을 가리키는 줄은 빠지고(사본에 없는 행은 접두어로), 회사 탭이 아닌 줄은 남는다
    assert [r["로그ID"] for r in out["sys_작업로그"]] == ["L1", "L7", "L8"]
    # 입력은 건드리지 않는다
    assert len(src["sys_급부"]) == 4 and len(src["sys_작업로그"]) == 12


def test_parent_decides_the_org_when_the_row_is_there():
    # 행이 사본에 있으면 ID 접두어가 아니라 부모(종형의 기관코드)를 따른다
    src = tables()
    for v in src["sys_상품종형"]:
        if v["기관코드"] == "MERITZ":
            v["기관코드"] = "EPOST"
    out = O.filter_tables(src, ("EPOST",))
    assert len(out["sys_급부"]) == 4 and len(out["hum_담보매핑"]) == 4
    assert [r["로그ID"] for r in out["sys_작업로그"]] == ["L1", "L2", "L3", "L4", "L5", "L7", "L8", "L9", "L10", "L11", "L12"]


def test_all_keeps_everything():
    src = tables()
    assert O.filter_tables(src, "all") == src
    assert O.filter_tables(src, ("EPOST", "MERITZ")) == src


def test_logs_and_mapping_of_dropped_orgs_stay_out_of_the_screen_numbers():
    src = tables()
    only = Data(O.filter_tables(src, ("EPOST",)))
    every = Data(O.filter_tables(src, "all"))
    assert set(only.mapping) == {b for b in only.benefits} and all(b.startswith("EPOST_") for b in only.mapping)
    assert set(only.pending_benefit) == {"EPOST_P1_aaaaaa_Trider_Bone"}
    assert only.pending_condition == {}
    assert set(every.pending_benefit) == {"EPOST_P1_aaaaaa_Trider_Bone", "MERITZ_M1_aaaaaa_Trider_Bone"}
    assert set(every.pending_condition) == {"MERITZ_M1_aaaaaa_Cone"}
    # 작업 내역 화면의 검토 대기 수와 전체 줄 수
    w_only, w_every = worklog.build(only)["summary"], worklog.build(every)["summary"]
    assert w_only["review"]["count"] == 1 and w_every["review"]["count"] == 3
    assert w_only["total"] == 3 and w_every["total"] == 12
    assert {v["기관코드"] for v in only.variants.values()} == {"EPOST"}


def test_load_filters_by_default_and_fixes_row_counts(tmp_path):
    snap = tmp_path / "snapshot"
    write_snapshot(tables(), snap, datetime(2026, 11, 23, 10, tzinfo=KST))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "SITE_ORGS", ("EPOST",))
        data = load(snap)
    assert {v["기관코드"] for v in data.variants.values()} == {"EPOST"}
    assert data.meta["row_counts"]["sys_급부"] == 2 and data.meta["row_counts"]["sys_작업로그"] == 3
    assert data.meta["snapshot_at"] == "2026-11-23T10:00:00+09:00"
    every = load(snap, "all")
    assert {v["기관코드"] for v in every.variants.values()} == {"EPOST", "MERITZ"}
    assert every.meta == json.loads((snap / "meta.json").read_text(encoding="utf-8"))
    assert set(load(snap, "MERITZ").variants) == {"MERITZ_M1_aaaaaa"}
    # 기본 목록(세 회사)이면 MERITZ 는 빠지고 EPOST 는 남는다
    assert {v["기관코드"] for v in load(snap).variants.values()} == {"EPOST"}


@pytest.mark.skipif(not (SNAPSHOT / "meta.json").exists(), reason="실제 사본(data/snapshot)이 없다")
def test_real_snapshot_carries_only_site_orgs_by_default():
    data = load(SNAPSHOT)
    assert {v["기관코드"] for v in data.variants.values()} <= set(config.SITE_ORGS)
    assert all(data.riders[b["특약ID"]]["종형ID"] in data.variants for b in data.benefits.values())


# 관계망 자료(proto_src/graph/build_data.py)가 회사를 거르는 일은 tests/test_graph_data.py 에서 본다
@pytest.mark.parametrize("cmd", [
    ["scripts/build_site.py", "--orgs", "all"],
    ["scripts/export_app_data.py", "--orgs", "EPOST,HANWHALIFE,SAMSUNGFIRE,MERITZ"],
    ["proto_src/graph/build_data.py", "--orgs", "all"],
])
def test_commands_refuse_to_write_other_orgs_to_committed_files(cmd):
    targets = [ROOT / "site" / "v1" / "index.html", ROOT / "site" / "index.html", *(ROOT / "proto_src" / "console4").glob("*.json"),
               ROOT / "proto_src" / "graph" / "graph.json"]
    before = {p: p.stat().st_mtime_ns for p in targets if p.exists()}
    run = subprocess.run([sys.executable, str(ROOT / cmd[0]), *cmd[1:]], cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8", timeout=120)
    assert run.returncode == 1 and "쓰지 않는다" in run.stdout, run.stdout + run.stderr
    assert {p: p.stat().st_mtime_ns for p in targets if p.exists()} == before


def test_bad_orgs_value_is_an_argument_error():
    run = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_site.py"), "--orgs", ",", "--out", "/dev/null"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert run.returncode == 2 and "--orgs" in run.stderr
