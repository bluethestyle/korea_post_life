import json
import math
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from postlife import ids
from postlife.extract import mapping as M
from postlife.gemini import Answer
from postlife.schema import TABS
from postlife.sheets_io import MemoryBackend, SheetStore, merge_mapping, rows_to_values
from postlife.snapshot import KST
from postlife.validate import check_rows

ROOT = Path(__file__).resolve().parents[1]
DICTIONARY = [json.loads(l) for l in (ROOT / "data/seed/hum_표준담보사전.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()]
NOW = datetime(2026, 11, 18, 17, 0, tzinfo=KST)


def world():
    variants = [{"종형ID": v, "공시상품명": f"상품 {v}"} for v in ("V1", "V2")]
    riders, benefits = [], []
    for v in ("V1", "V2"):
        for name, kind, rows in (("주계약", "주계약", ["재해사망보험금"]),
                                 ("무배당 암진단특약(20년갱신형) 2606", "선택특약", ["암진단보험금(암)", "암진단보험금(갑상선암·기타피부암)"])):
            rid = ids.rider_id(v, name)
            riders.append({"특약ID": rid, "종형ID": v, "특약계보키": ids.rider_lineage_key(name), "담보구분": kind, "원시특약명": name})
            benefits += [{"급부ID": ids.benefit_id(rid, b), "특약ID": rid, "원시급부명": b} for b in rows]
    return variants, riders, benefits


class FakeGemini:
    def __init__(self):
        self.asked = []

    def decide(self, model, text, questions):
        out = {}
        for key, q in questions.items():
            name = q["instructions"].split("'")[1]          # 지시문은 "급부 '<이름>'에 …"로 시작한다
            self.asked.append(name)
            if "재해사망" in name:
                probs = {M.NONE: 0.97, "일반암 진단비": 0.01}
            elif "갑상선암" in name:
                probs = {"유사암 진단비(통합)": 0.62, "갑상선암 진단비": 0.30, M.NONE: 0.02}        # 기준 0.80에 못 미친다
            else:
                probs = {"일반암 진단비": 0.99, M.NONE: 0.0}
            out[key] = Answer(max(probs, key=probs.get), None, probs)
        return out


def test_each_distinct_benefit_is_asked_once_and_written_for_every_variant():
    variants, riders, benefits = world()
    g = FakeGemini()
    r = M.run(g, variants, riders, benefits, DICTIONARY, [], NOW)
    assert len(g.asked) == 3 and len(r.rows) == 6            # 종형 둘이 같은 급부를 가진다
    assert check_rows("hum_담보매핑", r.rows) == {}
    by = {(row["공시상품명"], row["원시급부명"]): row for row in r.rows}
    cancer = by[("상품 V1", "암진단보험금(암)")]
    assert (cancer["검토상태"], cancer["확정표준담보ID"], cancer["매핑확률"]) == ("자동확정", "STD_CA_DX_GENERAL", 0.99)
    death = by[("상품 V2", "재해사망보험금")]
    assert death["검토상태"] == "대상외" and death["추천표준담보ID"] is None and death["확정표준담보ID"] is None
    small = by[("상품 V1", "암진단보험금(갑상선암·기타피부암)")]
    assert small["검토상태"] == "대기" and small["추천표준담보ID"] == "STD_CA_DX_PSEUDO" and small["확정표준담보ID"] is None
    assert r.stats == {"물은 급부": 3, "행": 6, "자동확정": 2, "대상외": 2, "대기": 2, "건너뜀(이미 있음)": 0, "다시 물은 행": 0}
    assert len(r.waiting) == 1 and "0.62" in r.waiting[0]
    steps = {(l["작업단계"], l["결과"]) for l in r.logs}
    assert steps == {("판정", "통과"), ("판정", "보류"), ("사람검토이관", "보류")}


def test_existing_rows_are_not_asked_again_and_reviewed_rows_survive():
    variants, riders, benefits = world()
    first = M.run(FakeGemini(), variants, riders, benefits, DICTIONARY, [], NOW)
    sheet = merge_mapping([], first.rows)
    waiting = next(r for r in sheet if r["검토상태"] == "대기")
    waiting.update({"검토상태": "수정", "확정표준담보ID": "STD_CA_DX_THYROID", "담당자메모": "갑상선암으로 본다"})

    g = FakeGemini()
    again = M.run(g, variants, riders, benefits, DICTIONARY, sheet, NOW)
    assert g.asked == [] and again.rows == [] and again.stats["건너뜀(이미 있음)"] == 6

    # 다시 묻더라도 담당자가 고친 행은 묻지도 바꾸지도 않는다
    g = FakeGemini()
    redo = M.run(g, variants, riders, benefits, DICTIONARY, sheet, NOW, remap=M.Remap(states=frozenset(M.REMAP_STATES)))
    assert len(g.asked) == 3 and waiting["급부ID"] not in {r["급부ID"] for r in redo.rows}
    assert redo.stats["다시 물은 행"] == 5                  # 6행 가운데 담당자가 고친 1행만 뺀다
    merged = merge_mapping(sheet, redo.rows)
    kept = next(r for r in merged if r["급부ID"] == waiting["급부ID"])
    assert (kept["검토상태"], kept["확정표준담보ID"], kept["담당자메모"]) == ("수정", "STD_CA_DX_THYROID", "갑상선암으로 본다")


def test_options_come_from_the_dictionary_and_thresholds_from_the_sheet():
    options = M.criteria(DICTIONARY + [{"표준담보명": "안 쓰는 담보", "보장대분류": "x", "보장중분류": "y", "급부유형": "진단", "사용여부": False}])
    # 사전 77개 가운데 사용하지 않는 심혈관질환 진단비를 빼고 해당없음을 더한다
    assert M.NONE in options and "일반암 진단비" in options and "안 쓰는 담보" not in options and len(options) == 77
    assert "심혈관질환 진단비" not in options and "뇌·심장질환 주요치료비" in options
    t = M.thresholds_from([{"기준키": "담보매핑_자동확정", "기준분류": "판정구간", "수치값": 0.8}])
    assert t == {"담보매핑_자동확정": 0.8, "담보매핑_대상외": 0.9}
    pick = M.decide(Answer("일반암 진단비", None, {"일반암 진단비": 0.85, M.NONE: 0.1}), options, t)
    assert pick.state == "자동확정" and M.decide(Answer(M.NONE, None, {M.NONE: 0.7}), options, t).state == "대기"
    assert M.DEFAULT_THRESHOLDS["담보매핑_자동확정"] == 0.80


def test_rule_sentences_name_only_dictionary_entries_in_use():
    used = [d["표준담보명"] for d in DICTIONARY if d.get("사용여부") is not False]
    quoted = re.findall(r"'([^']+)'", M.RULES)
    assert len(quoted) > 20
    # 따옴표 안은 선택지 이름 그대로여야 한다. 확장 전부터 있던 유사암 문장의 두 이름만 여러 담보를 묶어 부른다
    family = {"유사암", "소액암·유사암"}
    assert [q for q in quoted if q not in used and q not in family] == []
    assert all(any(f in name for name in used) for f in family)


def test_prune_drops_rows_of_vanished_benefits_but_keeps_reviewed_ones():
    rows = [{"급부ID": "a", "검토상태": "자동확정"}, {"급부ID": "b", "검토상태": "대기"}, {"급부ID": "c", "검토상태": "수정"},
            {"급부ID": "d", "검토상태": "대상외", "담당자메모": "대상외 확정: 검사비는 범위 밖"},
            {"급부ID": "e", "검토상태": "대상외", "담당자메모": "다음 확장 후보"}, {"급부ID": "f", "검토상태": "승인 "}]
    kept, removed, orphans = M.prune(rows, {"a"})
    assert [r["급부ID"] for r in kept] == ["a", "c", "d", "f"] and removed == 2
    assert [r["급부ID"] for r in orphans] == ["c", "d", "f"]


# ---------- 다시 묻기: 어느 상태를 다시 묻고 어느 상태를 두는가 ----------
STATE_ROWS = {          # 원시급부명: (지금 검토상태, 담당자메모)
    "대기 급부": ("대기", None),
    "메모 있는 대기 급부": ("대기", "원문 확인 필요"),
    "자동확정 급부": ("자동확정", None),
    "1인실 입원급여금": ("자동확정", None),
    "대상외 급부": ("대상외", None),
    "응급실내원 진료비": ("대상외", None),
    "메모 있는 대상외 급부": ("대상외", "다음 확장 후보"),
    "확정 대상외 응급실 급부": ("대상외", "대상외 확정: 845줄 결정"),
    "승인 급부": ("승인", None),
    "수정 1인실 급부": ("수정", None),
    "오류 급부": ("오류", None),
    "상태를 잘못 적은 급부": ("승인 ", None),
}


def state_world():
    variants = [{"종형ID": "V1", "공시상품명": "상품 V1"}]
    name = "무배당 시험특약 2606"
    rid = ids.rider_id("V1", name)
    riders = [{"특약ID": rid, "종형ID": "V1", "특약계보키": ids.rider_lineage_key(name), "담보구분": "선택특약", "원시특약명": name}]
    benefits = [{"급부ID": ids.benefit_id(rid, b), "특약ID": rid, "원시급부명": b} for b in list(STATE_ROWS) + ["새 급부"]]
    existing = []
    for b in benefits:
        if b["원시급부명"] in STATE_ROWS:
            state, memo = STATE_ROWS[b["원시급부명"]]
            confirmed = "STD_CM_HOSP_TERTIARY" if state in ("자동확정", "승인", "수정") else None
            existing.append({"급부ID": b["급부ID"], "공시상품명": "상품 V1", "원시특약명": name, "원시급부명": b["원시급부명"],
                             "추천표준담보ID": confirmed, "추천표준담보명": None, "매핑확률": 0.95, "확정표준담보ID": confirmed,
                             "검토상태": state, "담당자메모": memo})
    return variants, riders, benefits, existing


def asked_with(remap):
    variants, riders, benefits, existing = state_world()
    g = FakeGemini()
    result = M.run(g, variants, riders, benefits, DICTIONARY, existing, NOW, remap=remap)
    return set(g.asked), result, existing


NEVER = {"확정 대상외 응급실 급부", "승인 급부", "수정 1인실 급부", "오류 급부", "상태를 잘못 적은 급부"}


def test_remap_by_default_asks_new_and_waiting_rows_only():
    assert asked_with(False)[0] == {"새 급부"}
    asked, result, _ = asked_with(True)
    assert asked == {"새 급부", "대기 급부", "메모 있는 대기 급부"}
    assert result.stats["다시 물은 행"] == 2 and result.stats["건너뜀(이미 있음)"] == len(STATE_ROWS) - 2
    assert asked_with(M.Remap())[0] == asked


def test_remap_match_adds_confirmed_and_excluded_rows_by_benefit_name():
    asked, _, _ = asked_with(M.Remap(match="1인실|응급실"))
    assert asked == {"새 급부", "대기 급부", "메모 있는 대기 급부", "1인실 입원급여금", "응급실내원 진료비"}
    assert not asked & NEVER                 # 수정한 1인실 행과 확정한 대상외 응급실 행은 이름이 맞아도 묻지 않는다


def test_remap_states_choose_which_states_to_ask_again():
    asked = asked_with(M.Remap(states=frozenset({"대상외"})))[0]
    assert asked == {"새 급부", "대상외 급부", "응급실내원 진료비", "메모 있는 대상외 급부"}
    everything = asked_with(M.Remap(states=frozenset(M.REMAP_STATES)))[0]
    assert everything == {"새 급부"} | set(STATE_ROWS) - NEVER
    with pytest.raises(ValueError):
        M.Remap(states=frozenset({"승인"}))
    with pytest.raises(ValueError, match="정규식"):
        M.Remap(match="(1인실")


def test_settled_rows_survive_merge_and_remapped_rows_keep_their_memo():
    asked, result, existing = asked_with(M.Remap(states=frozenset(M.REMAP_STATES)))
    merged = {r["원시급부명"]: r for r in merge_mapping(existing, result.rows)}
    before = {r["원시급부명"]: r for r in existing}
    for name in NEVER:
        assert merged[name] == before[name]
    assert merged["메모 있는 대기 급부"]["담당자메모"] == "원문 확인 필요"
    assert merged["메모 있는 대기 급부"]["매핑확률"] == 0.99 and merged["새 급부"]["검토상태"] == "자동확정"
    assert [r for r in existing if M.settled(r)] == [before[n] for n in STATE_ROWS if n in NEVER - {"상태를 잘못 적은 급부"}]


def test_rows_settled_while_the_batch_runs_are_not_overwritten():
    # 매핑이 도는 동안 담당자가 대기 행 둘을 대상외 확정과 승인으로 바꿨다. 쓰기 직전에 시트를 다시 읽어 지킨다
    variants, riders, benefits, existing = state_world()
    result = M.run(FakeGemini(), variants, riders, benefits, DICTIONARY, existing, NOW, remap=True)
    assert {r["원시급부명"] for r in result.rows} == {"새 급부", "대기 급부", "메모 있는 대기 급부"}
    tab = TABS["hum_담보매핑"]
    edited = {"대기 급부": {"검토상태": "대상외", "담당자메모": "대상외 확정: 실행 중 결정"},
              "메모 있는 대기 급부": {"검토상태": "승인"}}
    sheet = [{**r, **edited.get(r["원시급부명"], {})} for r in existing]
    store = SheetStore(MemoryBackend({"hum_담보매핑": [list(tab.header)] + rows_to_values(tab, sheet)}))
    before = {r["원시급부명"]: r for r in store.read(["hum_담보매핑"])["hum_담보매핑"]}
    assert M.upsert(store, result.rows) == 2
    after = {r["원시급부명"]: r for r in store.read(["hum_담보매핑"])["hum_담보매핑"]}
    assert after["대기 급부"] == before["대기 급부"] and after["메모 있는 대기 급부"] == before["메모 있는 대기 급부"]
    assert after["대기 급부"]["검토상태"] == "대상외"
    assert after["새 급부"]["검토상태"] == "자동확정" and len(after) == len(sheet) + 1
    # 메모 머리말이 없는 대상외 행은 배치 값이라 새 추천으로 바꾼다 (sheets_io.merge_mapping과 같다)
    plain = [{**r, "검토상태": "대상외"} if r["원시급부명"] == "대기 급부" else r for r in existing]
    merged = {r["원시급부명"]: r for r in M.merge(plain, result.rows)}
    assert merged["대기 급부"]["검토상태"] == "자동확정"


def test_plan_counts_questions_and_calls_without_asking():
    variants, riders, benefits, existing = state_world()
    p = M.plan(riders, benefits, DICTIONARY, existing, M.Remap(match="1인실|응급실"))
    assert p["처음 묻는 급부"] == 1 and p["다시 묻는 급부"] == {"대기": 2, "대상외": 1, "자동확정": 1}
    assert p["문항"] == 5 and p["호출"] == math.ceil(5 / M.BATCH) and p["선택지"] == 77
    assert p["호출당 입력 글자 최대"] >= p["호출당 입력 글자 평균"] > 0
    g = FakeGemini()
    M.run(g, variants, riders, benefits, DICTIONARY, existing, NOW, remap=M.Remap(match="1인실|응급실"))
    assert len(g.asked) == p["문항"]


# ---------- 사전 seed를 시트 탭에 올리기 ----------
def std(sid, name, unit=100.0, used=True, major="공통보장", mid="수술비", kind="수술"):
    return {"표준담보ID": sid, "보장대분류": major, "보장중분류": mid, "표준담보명": name, "급부유형": kind,
            "비교기준단위만원": unit, "사용여부": used}


def test_sync_adds_rows_and_switches_flags_only():
    base = [std("STD_A", "가 수술비"), std("STD_B", "나 수술비"), std("STD_C", "다 수술비"), std("STD_D", "라 수술비")]
    # 사본 뒤에 담당자가 시트에서 B의 단위를 고치고 D의 사용여부를 껐다. 시트는 단위를 1000으로 돌려준다
    sheet = [std("STD_A", "가 수술비", unit=100), std("STD_B", "나 수술비", unit=1000), std("STD_C", "다 수술비"),
             std("STD_D", "라 수술비", used=False)]
    seed = [std("STD_A", "가 수술비 바꾼 이름"), std("STD_B", "나 수술비"), std("STD_C", "다 수술비", used=False),
            std("STD_D", "라 수술비"), std("STD_E", "마 수술비")]
    plan = M.sync_dictionary(sheet, seed, base)
    assert plan.added == ["STD_E"] and plan.switched == [("STD_C", True, False)] and plan.blocked == []
    assert [r["표준담보ID"] for r in plan.rows] == ["STD_A", "STD_B", "STD_C", "STD_D", "STD_E"]
    assert plan.rows[:2] == sheet[:2] and plan.rows[3] == sheet[3]           # 이름 변경, 담당자가 고친 단위와 사용여부는 그대로
    assert plan.rows[2] == {**sheet[2], "사용여부": False}
    assert any("STD_B 비교기준단위만원" in d for d in plan.drift) and any("STD_D 사용여부" in d for d in plan.drift)
    assert any(k.startswith("STD_A 표준담보명") for k in plan.kept)
    # 한 번 더 돌려도 바뀌는 것이 없다
    again = M.sync_dictionary(plan.rows, seed, base)
    assert not again.changed and again.rows == plan.rows


def test_sync_blocks_a_new_row_whose_name_is_taken_and_never_deletes():
    base = [std("STD_A", "가 수술비"), std("STD_B", "나 수술비")]
    seed = [std("STD_A", "가 수술비"), std("STD_X", "나 수술비")]         # B가 seed에서 빠지고 X가 B의 이름을 쓴다
    plan = M.sync_dictionary(base, seed, base)
    assert plan.added == [] and plan.blocked and [r["표준담보ID"] for r in plan.rows] == ["STD_A", "STD_B"]
    assert any("STD_B" in k and "지우지 않음" in k for k in plan.kept)


def test_sync_through_the_sheet_store_leaves_other_rows_as_they_were():
    tab = TABS["hum_표준담보사전"]
    snapshot = [json.loads(l) for l in (ROOT / "data/snapshot/hum_표준담보사전.jsonl").read_text(encoding="utf-8").splitlines() if l]
    old_seed = [r for r in DICTIONARY if r["표준담보ID"] in {s["표준담보ID"] for s in snapshot}]
    sheet_rows = [{**r, "사용여부": True} for r in old_seed]                  # 확장 전 시트: 52행, 모두 사용
    backend = MemoryBackend({"hum_표준담보사전": [list(tab.header)] + rows_to_values(tab, sheet_rows)})
    before = [list(r) for r in backend.data["hum_표준담보사전"]]
    store = SheetStore(backend)

    plan = M.sync_dictionary(store.read(["hum_표준담보사전"])["hum_표준담보사전"], DICTIONARY, sheet_rows)
    assert len(plan.added) == len(DICTIONARY) - len(sheet_rows) and plan.switched == [("STD_HT_DX_CARDIO", True, False)]
    store.write_tab("hum_표준담보사전", plan.rows)
    after = backend.data["hum_표준담보사전"]
    flag = tab.header.index("사용여부")
    cardio = next(i for i, r in enumerate(before) if r[0] == "STD_HT_DX_CARDIO")
    assert len(after) == len(before) + len(plan.added)
    for i, row in enumerate(before):
        assert after[i] == (row if i != cardio else row[:flag] + [False] + row[flag + 1:])
    assert [r[0] for r in after[len(before):]] == plan.added
    assert {r["표준담보ID"]: r for r in store.read(["hum_표준담보사전"])["hum_표준담보사전"]} == \
        {r["표준담보ID"]: r for r in DICTIONARY}


def test_script_plan_runs_offline_on_the_snapshot():
    script = ROOT / "scripts/map_benefits.py"
    out = subprocess.run([sys.executable, str(script), "--plan", "--snapshot", str(ROOT / "data/snapshot"), "--sync-dictionary",
                          "--prune", "--remap", "--remap-match", "1인실|응급실"], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "표준담보 사전:" in out.stdout and "물을 양:" in out.stdout
    bad = subprocess.run([sys.executable, str(script), "--plan", "--snapshot", str(ROOT / "data/snapshot"), "--remap-states", "승인"],
                         capture_output=True, text=True, timeout=120)
    assert bad.returncode == 2 and "다시 묻기 인자" in bad.stdout
    regex = subprocess.run([sys.executable, str(script), "--plan", "--snapshot", str(ROOT / "data/snapshot"), "--remap-match", "(1인실"],
                           capture_output=True, text=True, timeout=120)
    assert regex.returncode == 2 and "다시 묻기 인자" in regex.stdout and "Traceback" not in regex.stderr


def test_script_call_interval_follows_chars_per_minute():
    """판정 모델의 분당 토큰 한도 때문에 호출 간격을 분당 입력 글자 수 상한으로 정한다. 상한을 낮추면 간격이 그만큼 늘어난다."""
    script = ROOT / "scripts/map_benefits.py"

    def planned(*extra):
        out = subprocess.run([sys.executable, str(script), "--plan", "--snapshot", str(ROOT / "data/snapshot"), *extra],
                             capture_output=True, text=True, timeout=120)
        assert out.returncode == 0, out.stdout + out.stderr
        line = next(l for l in out.stdout.splitlines() if l.startswith("물을 양:"))
        return json.loads(line.split(":", 1)[1])

    base, slow = planned(), planned("--chars-per-minute", "24000")
    assert base["호출 간격(초)"] >= 7.0
    assert slow["호출 간격(초)"] == round(60.0 * slow["호출당 입력 글자 최대"] / 24000, 1)
    assert slow["호출 간격(초)"] > base["호출 간격(초)"]
    bad = subprocess.run([sys.executable, str(script), "--plan", "--snapshot", str(ROOT / "data/snapshot"), "--chars-per-minute", "0"],
                         capture_output=True, text=True, timeout=120)
    assert bad.returncode == 2
