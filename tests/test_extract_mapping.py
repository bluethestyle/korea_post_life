import json
from datetime import datetime
from pathlib import Path

from postlife import ids
from postlife.extract import mapping as M
from postlife.gemini import Answer
from postlife.sheets_io import merge_mapping
from postlife.snapshot import KST
from postlife.validate import check_rows

DICTIONARY = [json.loads(l) for l in (Path(__file__).resolve().parents[1] / "data/seed/hum_표준담보사전.jsonl")
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
    assert r.stats == {"물은 급부": 3, "행": 6, "자동확정": 2, "대상외": 2, "대기": 2, "건너뜀(이미 있음)": 0}
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

    # 다시 묻더라도 담당자가 고친 행은 그대로다
    redo = M.run(FakeGemini(), variants, riders, benefits, DICTIONARY, sheet, NOW, remap=True)
    merged = merge_mapping(sheet, redo.rows)
    kept = next(r for r in merged if r["급부ID"] == waiting["급부ID"])
    assert (kept["검토상태"], kept["확정표준담보ID"], kept["담당자메모"]) == ("수정", "STD_CA_DX_THYROID", "갑상선암으로 본다")


def test_options_come_from_the_dictionary_and_thresholds_from_the_sheet():
    options = M.criteria(DICTIONARY + [{"표준담보명": "안 쓰는 담보", "보장대분류": "x", "보장중분류": "y", "급부유형": "진단", "사용여부": False}])
    assert M.NONE in options and "일반암 진단비" in options and "안 쓰는 담보" not in options and len(options) == 53
    t = M.thresholds_from([{"기준키": "담보매핑_자동확정", "기준분류": "판정구간", "수치값": 0.8}])
    assert t == {"담보매핑_자동확정": 0.8, "담보매핑_대상외": 0.9}
    pick = M.decide(Answer("일반암 진단비", None, {"일반암 진단비": 0.85, M.NONE: 0.1}), options, t)
    assert pick.state == "자동확정" and M.decide(Answer(M.NONE, None, {M.NONE: 0.7}), options, t).state == "대기"
    assert M.DEFAULT_THRESHOLDS["담보매핑_자동확정"] == 0.80
