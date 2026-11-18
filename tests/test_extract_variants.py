import json
from pathlib import Path

from postlife.extract import variants as VV
from postlife.validate import check_rows

ROOT = Path(__file__).resolve().parents[1]
TARGETS = json.loads((ROOT / "data/targets/epost.json").read_text(encoding="utf-8"))


def entry(code, name, kind, digest, start="2026-06-17", end=None):
    return {"기관": "EPOST", "상품코드": code, "상품명": name, "판매시작일": start, "판매종료일": end,
            "문서": kind, "해시": digest, "저장이름": f"{kind}_{digest}", "쪽수": 40}


INDEX = (
    [entry(c, f"무배당 우체국간편한건강보험(20년갱신형) 2606 {n}", k, f"h26{k}")
     for c, n in (("P500129", "1종(간편가입315)"), ("P500130", "2종(간편가입325)"), ("P500131", "3종(간편가입355)"),
                  ("P500132", "4종(일반가입)")) for k in ("상품요약서", "사업방법서", "약관")]
    + [entry("P400069", "무배당 우체국통합건강보험 2504", k, f"h25{k}", "2025-04-03") for k in ("상품요약서", "사업방법서", "약관")]
    + [entry("P500108", "무배당 우체국간편건강보험(355)(20년갱신형) 2504", "상품요약서", "h355", "2025-04-03", "2026-06-16")]
)


def test_variant_rows_follow_schema_and_group_by_summary_file():
    variants, problems = VV.build(TARGETS, INDEX)
    assert [p[:7] for p in problems] == ["P500109", "P500110"]        # 수집 결과에 없는 상품은 만들지 않는다
    rows = [v.row for v in variants]
    assert check_rows("sys_상품종형", rows) == {}
    assert len({r["종형ID"] for r in rows}) == 6
    first = rows[0]
    assert first["개정판ID"] == "EPOST_SIMPLE_2606" and first["요약서해시"] == "h26상품요약서"
    assert (first["고지입원수술년수"], first["고지수술포함여부"], first["고지중대질병수"]) == (1, False, 6)
    groups = VV.by_summary(variants)
    assert sorted(len(g) for g in groups) == [1, 1, 4]              # 2606의 네 종은 요약서 하나를 함께 쓴다


def test_previous_revision_links_to_current_by_lineage_key():
    variants, _ = VV.build(TARGETS, INDEX)
    keys = {v.row["공시상품코드"]: v.row["종형계보키"] for v in variants}
    assert keys["P500108"] == keys["P500131"]                         # 개정 전 355 ↔ 개정 후 3종(355)
    assert keys["P500108"] != keys["P500129"]
