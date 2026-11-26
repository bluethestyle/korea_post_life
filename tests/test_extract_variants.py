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
    # 수집 결과에 없는 상품은 만들지 않는다(INDEX에 없는 간편건강보험 2504 두 종, 더간편건강보험 2504 네 종, 하나로OK보험 2609 여덟 종)
    # 더간편건강보험은 보장형마다 상품 항목이 나뉘어 [암보장형] 두 종 다음에 [2대질병보장형] 두 종이 온다
    # 하나로OK보험은 주계약 보험기간(종신, 90세와 100세만기)과 환급유형(표준형, 50%지급형)마다 상품 항목이 나뉜다
    assert [p[:7] for p in problems] == ["P500109", "P500110", "P610196", "P610198", "P610197", "P610199",
                                         "P400084", "P400086", "P400083", "P400085", "P400088", "P400090", "P400087", "P400089"]
    rows = [v.row for v in variants]
    assert check_rows("sys_상품종형", rows) == {}
    assert len({r["종형ID"] for r in rows}) == 6
    first = rows[0]
    assert first["개정판ID"] == "EPOST_SIMPLE_2606" and first["요약서해시"] == "h26상품요약서"
    assert (first["고지입원수술년수"], first["고지수술포함여부"], first["고지중대질병수"]) == (1, False, 6)
    groups = VV.by_summary(variants)
    assert sorted(len(g) for g in groups) == [1, 1, 4]              # 2606의 네 종은 요약서 하나를 함께 쓴다


def test_hanarook_eight_variants_get_separate_lineage_keys():
    """우체국하나로OK보험 2609의 여덟 종형은 한 요약서를 함께 쓰고, 종형계보키가 모두 다르다.

    계보키에 보험기간이 없어 종신과 90세, 100세만기를 모상품ID로 나눴다. 같은 가입유형과 환급유형의 두 보험기간이 한 계보로 묶이지 않는다.
    상품명은 지어낸 것이다(상품코드와 종형명만 대상 설정에서 찾는 데 쓴다).
    """
    codes = [f"P4000{n}" for n in range(83, 91)]
    index = [entry(c, f"무배당 가나보험 2609 {c}", k, f"hok{k}", "2026-09-16") for c in codes for k in ("상품요약서", "사업방법서")]
    variants, problems = VV.build(TARGETS, index)
    mine = [v for v in variants if v.row["공시상품코드"] in codes]
    assert len(mine) == 8 and check_rows("sys_상품종형", [v.row for v in mine]) == {}
    assert len({v.row["종형계보키"] for v in mine}) == 8 and len({v.row["종형ID"] for v in mine}) == 8
    assert {v.row["모상품ID"] for v in mine} == {"EPOST_HANAROOK_WHOLE", "EPOST_HANAROOK_TERM"}
    assert [len(g) for g in VV.by_summary(mine)] == [8]
    simple = [v.row for v in mine if v.row["심사유형"] == "간편심사"]
    assert len(simple) == 4 and {r["간편고지약칭"] for r in simple} == {"3.2.5"}
    assert {(r["고지입원수술년수"], r["고지수술포함여부"], r["고지중대질병수"], r["고지소견범위"]) for r in simple} == {(2, False, 6, "서면")}
    # 정밀비교는 종신 해약환급금 50%지급형의 1종과 2종 둘이다(급부 표가 종형마다 갈리지 않아 대표 둘만 둔다).
    # 간편 3.2.5 등급에 우체국 정밀비교 종형이 둘이 된다. 등급별 대표 고르기(site/lineup.pick_lineup)는 화면 기본 상품
    # (site/screen.DEFAULT_PRODUCT, 간편한건강보험)의 종형을 고른다(tests/test_site_screen.py)
    assert [v.row["공시상품코드"] for v in mine if v.row["비교역할구분"] == "정밀비교"] == ["P400083", "P400085"]


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
        "epost": {("암, 협심증, 심근경색, 심장판막증, 간경화증, 뇌졸중증", "서면"),
                  # 더간편건강보험 2504(3.0.5)는 보장형마다 질문 2의 질병이 다르다(사업방법서 별첨2)
                  ("암, 제자리암, 간경화", "서면"), ("뇌졸중증, 급성심근경색증, 협심증", "서면")},
        "hanwha": {("암, 협심증, 심근경색, 뇌졸중증, 간경화증, 심장판막증, 투석중인 만성신장질환", "서면과 진료기록부")},
        "samsungfire": {("암, 협심증, 심근경색, 뇌졸중증, 심장판막증", "서면과 진료기록부")},
    }
