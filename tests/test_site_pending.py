"""화면의 검토 대기 표시(site/model.py의 Data._pending)를 종형마다 가리는 규칙. 재추출(extract/rerun.py)과 같은 규칙이다."""
from datetime import datetime

from postlife import ids
from postlife.extract import rerun as R
from postlife.site.model import Data

R0, R1 = "2026-11-19T17:00:00+09:00", "2026-11-26T17:00:00+09:00"
NAME = "가나수술보험금"


def bid(v):
    return ids.benefit_id(f"X_V{v}_T1", NAME)


def log(v, step, when, column="기준지급금액만원"):
    return {"로그ID": f"L{v}{step}{when}", "대상탭": "sys_급부", "대상행ID": bid(v), "작업단계": step, "실행일시": when,
            "결과": "보류", "대상열": column, "사유": None}


def covered(v, when):
    """그 실행이 이 종형의 급부를 다시 뽑아 판정 기록을 종형마다 남겼다는 기록."""
    return R.coverage_logs(datetime.fromisoformat(when), [f"X_V{v}"], "가나보험")[0]


def tables(logs, on_sheet=(1, 2, 3)):
    return {"sys_급부": [{"급부ID": bid(v), "특약ID": f"X_V{v}_T1", "원시급부명": NAME, "급부역할": "주급부", "기준지급금액만원": 100}
                        for v in on_sheet],
            "sys_특약": [{"특약ID": f"X_V{v}_T1", "종형ID": f"X_V{v}", "담보구분": "선택특약", "원시특약명": "가나특약"} for v in (1, 2, 3)],
            "sys_상품종형": [{"종형ID": f"X_V{v}", "요약서해시": "h"} for v in (1, 2, 3)],
            "sys_작업로그": logs}


def pending(t):
    shown = Data(t).pending_benefit
    assert set(shown) == R.pending_benefits(t["sys_급부"], t["sys_특약"], t["sys_상품종형"], t["sys_작업로그"])
    return {b: cols for b, cols in shown.items()}


def test_row_with_its_own_verdict_keeps_it():
    # 가입유형별로 표가 갈려 1종(일반가입형 표)은 확정, 2종(간편가입형 표의 첫 종형)은 검토로 판정됐다. 3종은 기록이 없다(예전 실행)
    t = tables([log(1, "판정", R0), log(2, "판정", R0), log(2, "사람검토이관", R0)])
    assert pending(t) == {bid(2): ["기준지급금액만원"], bid(3): ["기준지급금액만원"]}


def test_row_without_its_own_verdict_follows_the_latest_one_of_the_same_benefit():
    # 1종의 줄은 다시 뽑으며 시트에서 없어졌지만 그 기록은 2종, 3종에 옮긴다
    t = tables([log(1, "판정", R0), log(1, "사람검토이관", R0)], on_sheet=(2, 3))
    assert set(pending(t)) == {bid(2), bid(3)}
    # 다른 종형의 더 나중 판정이 있으면 그것을 본다. 3종은 자기 기록(확정)을 본다
    t["sys_작업로그"] += [log(3, "판정", R1)]
    assert pending(t) == {}
    t["sys_작업로그"] += [log(3, "사람검토이관", R1)]
    assert set(pending(t)) == {bid(2), bid(3)}


def test_run_that_did_not_redo_a_variant_does_not_change_it():
    # 예전 실행(R0)은 1종에만 기록을 남겼다. 나중 실행(R1)은 1종만 다시 뽑아 확정했다(종형마다 기록을 남긴 실행)
    t = tables([log(1, "판정", R0), log(1, "사람검토이관", R0), log(1, "판정", R1), covered(1, R1)])
    assert set(pending(t)) == {bid(2), bid(3)}
    # 그 실행이 2종도 다시 뽑았는데 2종의 이 줄에 그 실행의 기록이 없으면, 그 줄은 그 실행이 쓰지 않고 지킨 이전 줄이다.
    # 다른 종형에 남은 그 실행의 판정으로 바꾸지 않는다
    t["sys_작업로그"].append(covered(2, R1))
    assert set(pending(t)) == {bid(2), bid(3)}
    # 종형마다 기록을 남긴 실행은 2종의 줄에도 자기 기록을 남긴다. 그때는 그 기록을 본다
    t["sys_작업로그"].append(log(2, "판정", R1))
    assert set(pending(t)) == {bid(3)}


def test_columns_of_the_review_come_with_the_flag():
    t = tables([log(1, "판정", R0), log(1, "사람검토이관", R0, "감액개월1, 면책기간일수")])
    assert pending(t) == {b: ["감액개월1", "면책기간일수"] for b in (bid(1), bid(2), bid(3))}
