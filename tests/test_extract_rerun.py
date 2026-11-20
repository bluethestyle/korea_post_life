"""재추출 전후 견주기(extract/rerun.py): 같은 급부의 ID 잇기, 이전 확정 줄 고르기, 내용 기준 비교."""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from postlife import ids
from postlife.extract import rerun as R
from postlife.site.model import Data
from postlife.snapshot import KST, read_snapshot

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 26, 16, 0, tzinfo=KST)
RIDER = "X_V1_T0001"


def row(name, pay=100, base=1000, months=None, rate=None, wait=0, role="주급부", rider=RIDER, **kw):
    return {"급부ID": ids.benefit_id(rider, name), "특약ID": rider, "원시급부명": name, "급부역할": role,
            "기준가입금액만원": base, "기준지급금액만원": pay, "지급횟수제한": None, "면책기간일수": wait,
            "감액개월1": months, "감액지급률1": rate, "감액개월2": None, "감액지급률2": None, "감액예외": None,
            "근거문서종류": "요약서", "근거문서쪽수": 3, **kw}


def test_stem_ignores_spacing_like_the_benefit_id():
    assert R.stem("가나 진단자금(가나병)") == R.stem("가나진단자금(가나병(수치 6.5% 이상))") == "가나진단자금"
    linked = R.inherit_ids([row("가나진단자금(가나병)")], [row("가나 진단자금(가나병(수치 6.5% 이상))")])
    assert [r["급부ID"] for r in linked.rows] == [ids.benefit_id(RIDER, "가나진단자금(가나병)")]


def test_reductions_and_base_amount_are_part_of_the_same_benefit():
    old = [row("가나자금(질병)", months=12, rate=0.5)]
    assert R.inherit_ids(old, [row("가나자금(질병 입원)", months=12, rate=0.5)]).pairs
    assert not R.inherit_ids(old, [row("가나자금(질병 입원)", months=24, rate=0.5)]).pairs
    assert not R.inherit_ids(old, [row("가나자금(질병 입원)", months=12, rate=0.5, base=500)]).pairs
    assert not R.inherit_ids(old, [row("가나자금(질병 입원)", months=12, rate=0.5, rider="X_V1_T0002")]).pairs
    # 면책은 이번 값을 쓴다. 재추출이 면책을 바로잡은 줄도 매핑이 이어져야 한다
    got = R.inherit_ids(old, [row("가나자금(질병 입원)", months=12, rate=0.5, wait=90)])
    assert got.rows[0]["면책기간일수"] == 90 and got.rows[0]["원시급부명"] == "가나자금(질병)"


def test_an_old_id_is_never_given_to_two_rows():
    old = [row("가나자금(질병)")]
    same_id_new_value = row("가나자금(질병)", pay=200)          # 같은 ID가 이번 결과에 이미 있다
    renamed = row("가나자금(질병 입원)")                          # 이전 줄과 내용이 같은 새 이름
    got = R.inherit_ids(old, [same_id_new_value, renamed])
    assert not got.pairs and [r["급부ID"] for r in got.rows] == [same_id_new_value["급부ID"], renamed["급부ID"]]
    # 이번 결과에 같은 ID가 두 번 나온 줄도 잇지 않는다
    twice = [row("가나자금(질병 입원)"), row("가나자금(질병 입원)", wait=90)]
    assert not R.inherit_ids(old, twice).pairs


def test_content_diff_counts_lines_not_ids():
    old = [row("가(1)"), row("가(2)"), row("나", pay=50)]
    new = [row("가(3)"), row("나", pay=50, months=12, rate=0.5)]
    lost, gained = R.content_diff(old, new)
    assert sum(lost.values()) == 2 and sum(gained.values()) == 1
    lost, gained = R.content_diff(old, new, R.loose_key)
    assert sum(lost.values()) == 1 and sum(gained.values()) == 0


def test_excluded_name_is_matched_only_when_one_old_row_fits():
    old = [row("장해자금(100%)", pay=200), row("장해자금(80%~100%미만)", pay=100), row("사망자금(재해)", pay=1000)]
    held = [row("장해자금(합산 50%~80%미만)", pay=50), row("사망자금(재해사고)", pay=900), row("새자금(질병)", pay=10)]
    got = R.carry_over(old, [{"특약ID": RIDER, "종형ID": "X_V1", "원시특약명": "가나특약"}], [], {RIDER}, held, set(), set(), NOW)
    assert [r["원시급부명"] for r in got.kept] == ["사망자금(재해)"]          # 괄호 앞부분이 하나씩만 맞는 줄
    assert got.unmatched == [(RIDER, "장해자금(합산 50%~80%미만)")]          # 이전 줄 둘 가운데 어느 것인지 모른다
    assert len(got.logs) == 1 and got.logs[0]["대상행ID"] == old[2]["급부ID"] and R.KEPT_ROW in got.logs[0]["사유"]


def test_excluded_item_holds_its_old_row_before_any_sibling():
    rider = [{"특약ID": RIDER, "종형ID": "X_V1", "원시특약명": "가나특약"}]
    old = [row("가나자금(질병)")]
    # 같은 ID의 이전 줄은 제외된 항목의 것이다. 괄호 앞부분과 금액이 같은 형제 항목에 잇지 않는다
    got = R.carry_over(old, rider, [row("가나자금(재해)")], {RIDER}, [row("가나자금(질병)")], set(), set(), NOW)
    assert [r["원시급부명"] for r in got.benefits] == ["가나자금(재해)", "가나자금(질병)"] and not got.inherited.pairs
    assert got.kept == old
    # 이름이 바뀐 채 제외된 항목이 같은 급부의 기준으로 이전 줄과 맞으면 그 줄도 제외된 항목의 것이다
    got = R.carry_over(old, rider, [], {RIDER}, [row("가나자금(질병 입원)")], set(), set(), NOW)
    assert got.kept == old and got.inherited.claimed == [(old[0], row("가나자금(질병 입원)"))]
    # 제외된 항목과 다른 항목이 함께 같은 급부의 기준에 맞으면 어느 쪽인지 모른다. 잇지 않고, 괄호 앞부분으로 제외된 항목에 붙인다
    got = R.carry_over(old, rider, [row("가나자금(재해)")], {RIDER}, [row("가나자금(질병 입원)")], set(), set(), NOW)
    assert not got.inherited.pairs and got.kept == old
    # 제외된 항목이 가리키는 이전 줄이 없으면(처음 나온 급부) 형제 항목은 그대로 잇는다
    got = R.carry_over(old, rider, [row("가나자금(질병 입원)")], {RIDER}, [row("다라자금", pay=7)], set(), set(), NOW)
    assert [r["급부ID"] for r in got.benefits] == [old[0]["급부ID"]] and not got.kept


def test_rows_of_one_unit_share_the_id_tail():
    a, b = "X_V1_T0001", "X_V2_T0001"
    old = [row("가나자금(질병)", rider=a)]
    new = [row("가나자금(질병 입원)", rider=a), row("가나자금(질병 입원)", rider=b)]
    unit = {"X_V1": new[0]["급부ID"], "X_V2": new[1]["급부ID"]}
    got = R.inherit_ids(old, new, units=[unit])
    assert [r["급부ID"] for r in got.rows] == [old[0]["급부ID"], ids.benefit_id(b, "가나자금(질병)")]
    assert {r["원시급부명"] for r in got.rows} == {"가나자금(질병)"} and len(got.pairs) == 1 and len(got.aligned) == 1
    assert got.renamed == {new[0]["급부ID"]: old[0]["급부ID"], new[1]["급부ID"]: ids.benefit_id(b, "가나자금(질병)")}
    # 종형마다 이전 ID의 꼬리가 다르면 어느 꼬리로도 맞출 수 없다. 잇지 않고 둘 다 이번에 계산된 ID를 쓴다
    old2 = old + [row("가나자금(질병 입원 치료)", rider=b)]
    got = R.inherit_ids(old2, new, units=[unit])
    assert [r["급부ID"] for r in got.rows] == [r["급부ID"] for r in new] and got.split == 1 and not got.pairs
    # 묶음이 없으면 종형마다 따로 잇는다(scripts/dev/compare_rerun.py)
    assert len(R.inherit_ids(old2, new).pairs) == 2


def test_kept_row_whose_rider_is_gone_brings_the_rider_back():
    rider = {"특약ID": RIDER, "종형ID": "X_V1", "특약계보키": "k", "담보구분": "선택특약", "원시특약명": "가나특약",
             "갱신여부": False, "갱신주기년": None, "최소가입금액만원": 500, "최대가입금액만원": 3000, "합산한도기준키": None}
    old = [row("가나자금"), row("다라자금", pay=50)]
    got = R.carry_over(old, [rider], [], set(), {}, {RIDER}, {old[1]["급부ID"]}, NOW)
    assert got.riders == [rider] and [r["급부ID"] for r in got.kept] == [old[0]["급부ID"]]
    assert [r["급부ID"] for r in got.pending] == [old[1]["급부ID"]]          # 검토 대기 줄은 되살리지 않는다
    assert [(l["대상탭"], l["작업단계"], l["결과"]) for l in got.logs] == [("sys_특약", "재추출", "반려"), ("sys_급부", "재추출", "반려")]
    # 특약 행을 찾을 수 없으면 급부만 둘 수 없다
    orphan = R.carry_over(old, [], [], set(), {}, {RIDER}, set(), NOW)
    assert not orphan.kept and not orphan.riders and len(orphan.unmatched) == 2


def test_pending_rule_follows_the_latest_run_and_the_shared_summary():
    def log(target, step, when):
        return {"대상탭": "sys_급부", "대상행ID": target, "작업단계": step, "실행일시": when, "결과": "보류"}

    a, b, c = (row("가나자금", rider=f"X_V{n}_T1") for n in (1, 2, 3))
    tables = {"sys_급부": [a, b, c],
              "sys_특약": [{"특약ID": f"X_V{n}_T1", "종형ID": f"X_V{n}", "담보구분": "선택특약", "원시특약명": "가나특약"} for n in (1, 2, 3)],
              "sys_상품종형": [{"종형ID": "X_V1", "요약서해시": "h"}, {"종형ID": "X_V2", "요약서해시": "h"}, {"종형ID": "X_V3", "요약서해시": "g"}],
              "sys_작업로그": [log(a["급부ID"], "사람검토이관", "2026-11-19T17:00:00+09:00")]}
    pending = R.pending_benefits(tables["sys_급부"], tables["sys_특약"], tables["sys_상품종형"], tables["sys_작업로그"])
    assert pending == {a["급부ID"], b["급부ID"]}                                # 같은 요약서를 쓰는 종형에 옮긴다
    assert pending == set(Data(tables).pending_benefit)
    tables["sys_작업로그"].append(log(a["급부ID"], "판정", "2026-11-26T17:00:00+09:00"))     # 나중 실행이 다시 판정했다
    assert R.pending_benefits(tables["sys_급부"], tables["sys_특약"], tables["sys_상품종형"], tables["sys_작업로그"]) == set()


def test_pending_rule_matches_the_screen_on_the_snapshot():
    data = read_snapshot(ROOT / "data/snapshot")
    mine = R.pending_benefits(data["sys_급부"], data["sys_특약"], data["sys_상품종형"], data["sys_작업로그"])
    assert mine == set(Data(data).pending_benefit)


def test_compare_rerun_script_uses_the_same_counts(tmp_path):
    old = [row("가나자금(질병)", rider="ORG_V1_T1"), row("다라자금", pay=50, rider="ORG_V1_T1")]
    new = [row("가나자금(질병 입원)", rider="ORG_V1_T1"), row("마바자금", pay=70, rider="ORG_V1_T1")]
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "sys_급부.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in old), encoding="utf-8")
    (snap / "sys_특약.jsonl").write_text(json.dumps({"특약ID": "ORG_V1_T1", "종형ID": "ORG_V1"}), encoding="utf-8")
    result = tmp_path / "extract.json"
    result.write_text(json.dumps({"rows": {"sys_급부": new, "sys_특약": [{"특약ID": "ORG_V1_T1", "종형ID": "ORG_V1"}]},
                                  "logs": [], "errors": {}}, ensure_ascii=False), encoding="utf-8")
    out = subprocess.run([sys.executable, str(ROOT / "scripts/dev/compare_rerun.py"), str(result), "ORG", "--snapshot", str(snap)],
                         capture_output=True, text=True, check=True).stdout
    assert "이전 급부ID를 이을 수 있는 줄 1" in out
    assert "기준 잃은 줄 1 얻은 줄 1" in out
    diff = json.loads((tmp_path / "extract.json.diff.json").read_text(encoding="utf-8"))
    assert diff["lost"] == [["ORG_V1_T1", 50.0, None, None, 0.0, 1]] and diff["gained"] == [["ORG_V1_T1", 70.0, None, None, 0.0, 1]]
