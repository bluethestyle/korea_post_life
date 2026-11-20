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


ORGS = ("epost", "hanwha", "samsungfire")


def real_targets(org):
    return json.loads((ROOT / f"data/targets/{org}.json").read_text(encoding="utf-8"))


def test_disclosure_scope_columns_ride_on_variant_rows():
    """고지중대질병목록, 고지소견범위가 종형 행에 실리고, 다른 열과 종형ID는 그대로다."""
    variants, _ = VV.build(TARGETS, INDEX)
    rows = {v.row["공시상품코드"]: v.row for v in variants}
    assert rows["P500129"]["고지중대질병목록"] == "암, 협심증, 심근경색, 심장판막증, 간경화증, 뇌졸중증"
    assert rows["P500129"]["고지소견범위"] == "서면"
    assert rows["P500132"]["고지중대질병목록"] is None and rows["P500132"]["고지소견범위"] is None   # 일반심사는 비운다
    assert check_rows("sys_상품종형", list(rows.values())) == {}
    # 설정에서 두 값을 지워도 종형ID와 다른 열은 같다
    plain = json.loads(json.dumps(TARGETS))
    for product in plain["상품"]:
        for v in product["종형"]:
            v.pop("고지중대질병목록", None)
            v.pop("고지소견범위", None)
    again = {v.row["공시상품코드"]: v.row for v in VV.build(plain, INDEX)[0]}
    assert again.keys() == rows.keys()
    for code, row in rows.items():
        assert again[code] == {**row, "고지중대질병목록": None, "고지소견범위": None}, code


def test_attributes_match_the_rows_build_makes():
    for org in ORGS:
        targets = real_targets(org)
        attrs = VV.attributes(targets)
        codes = {v["공시상품코드"] for p in targets["상품"] for v in p["종형"]}
        index = [{"기관": targets["기관코드"], "상품코드": c, "상품명": "시험", "판매시작일": "2026-01-01", "판매종료일": None,
                  "문서": "상품요약서", "해시": f"h{c}", "저장이름": c, "쪽수": 1} for c in codes]
        found, problems = VV.build(targets, index)
        assert problems == [] and len(found) == len(attrs), org
        for v in found:
            assert attrs[v.id] == {k: v.row[k] for k in VV.OPTIONAL}, v.id


def test_real_targets_fill_both_columns_for_every_simple_variant():
    """간편심사 종형은 두 열이 모두 있고, 질병 수가 고지중대질병수와 같다. 일반심사 종형은 비어 있다."""
    seen = {}
    for org in ORGS:
        for product in real_targets(org)["상품"]:
            for v in product["종형"]:
                names, scope = v.get("고지중대질병목록"), v.get("고지소견범위")
                if v["심사유형"] == "간편심사":
                    assert names and scope in ("서면", "서면과 진료기록부"), v["종형명"]
                    assert len(names.split(", ")) == v["고지중대질병수"] and "(" not in names, v["종형명"]
                    seen.setdefault(org, set()).add((names, scope))
                else:
                    assert names is None and scope is None, v["종형명"]
    assert seen == {
        "epost": {("암, 협심증, 심근경색, 심장판막증, 간경화증, 뇌졸중증", "서면")},
        "hanwha": {("암, 협심증, 심근경색, 뇌졸중증, 간경화증, 심장판막증, 투석중인 만성신장질환", "서면과 진료기록부")},
        "samsungfire": {("암, 협심증, 심근경색, 뇌졸중증, 심장판막증", "서면과 진료기록부")},
    }
