"""한 요약서가 보장형마다 다른 주계약과 특약을 담는 문서(우체국더간편건강보험 2504 형식)를 종형에 맞게 싣는지.

표 안에 가입유형 구분 줄이 없어 scope_parts로는 가르지 못한다. 종형마다 설정의 추출대상특약으로 실을 조각을 고른다.
가입조건 쪽에서는 종형명 끝의 보장형 표시("[가형]")와 특약 이름 끝의 종 표시("… 1종(간편가입)")를 다룬다.
글자는 형식만 본떴고 상품명, 특약명, 금액은 지어낸 것이다.
"""
import json
from datetime import datetime
from pathlib import Path

from postlife import ids
from postlife.extract import conditions as C
from postlife.extract import job
from postlife.extract import pipeline as P
from postlife.extract import variants as VV
from postlife.extract import verify as V
from postlife.extract.segment import pages_from_text, rider_blocks
from postlife.gemini import Answer
from postlife.schema import TABS
from postlife.sheets_io import MemoryBackend, SheetStore
from postlife.snapshot import KST
from postlife.validate import check_rows

ROOT = Path(__file__).resolve().parents[1]

TEXT = """
===== 8쪽 =====
◆ 보험금 지급사유 및 지급제한 사항
② 보험금 지급사유
■ 주계약 (가형) (보험가입금액 1,000만원 기준)
지급구분 지 급 사 유 지 급 액
가질환진단보험금 최초 1회에 한함 1,000만원
건강관리자금 보험기간이 끝날 때까지 살아 있을 때 50만원
■ 주계약 (나형) (보험가입금액 1,000만원 기준)
지급구분 지 급 사 유 지 급 액
나질환진단보험금 최초 1회에 한함 1,000만원
건강관리자금 보험기간이 끝날 때까지 살아 있을 때 50만원
===== 9쪽 =====
■ 무배당 가질환진단특약(갱신형) 2504
(특약보험가입금액 1,000만원 기준)
지급구분 지 급 사 유 지 급 액
가질환진단보험금 최초 1회에 한함 1,000만원
■ 무배당 나질환진단특약(갱신형) 2504
(특약보험가입금액 1,000만원 기준)
지급구분 지 급 사 유 지 급 액
나질환진단보험금 최초 1회에 한함 1,000만원
■ 무배당 나질환입원특약(갱신형) 2504
(특약보험가입금액 1,000만원 기준)
지급구분 지 급 사 유 지 급 액
나질환입원보험금 1일당 2만원
③ 일반적 보험금 지급제한 사유
"""
NAMES = {"VA1": "1종(간편가입)[가형]", "VB1": "1종(간편가입)[나형]", "VA2": "2종(일반가입)[가형]"}
RIDERS = {"VA1": ("주계약 (가형)", "가질환진단특약"), "VB1": ("주계약 (나형)", "나질환진단특약", "나질환입원특약"),
          "VA2": ("주계약(가형)", "가질환진단특약")}


class FakeGemini:
    def __init__(self):
        self.texts = []

    def generate(self, model, prompt, schema=None, temperature=0.0):
        body = prompt.split("특약 이름:")[-1]
        self.texts.append(body)
        rows = [("가질환진단보험금", "1,000만원"), ("나질환진단보험금", "1,000만원"), ("건강관리자금", "50만원"),
                ("나질환입원보험금", "2만원")]
        return {"base_amount": "1,000만원", "benefits": [
            {"name": n, "target": "", "amount": a, "start_condition": "", "limit": "", "role": "주급부", "quote": a}
            for n, a in rows if n in body]}

    def decide(self, model, input_text, questions):
        return {k: (Answer(V.FROM_DAY_ONE, None, {V.FROM_DAY_ONE: 0.97, V.AFTER_START: 0.03}) if q["type"] == "choice"
                    else Answer(True, None, {"true": 0.97, "false": 0.03})) for k, q in questions.items()}


def run(riders):
    g = FakeGemini()
    r = P.run_summary(g, pages_from_text(TEXT), list(NAMES), datetime(2026, 11, 25, 10, 0, tzinfo=KST), None, 15,
                      plain_renewal_years=15, variant_names=NAMES, variant_riders=riders)
    return g, r


def riders_of(r, vid):
    return sorted(x["원시특약명"] for x in r.riders if x["종형ID"] == vid)


def test_both_main_blocks_share_the_rider_name():
    """두 주계약 조각의 이름이 모두 "주계약"이라, 가르지 않으면 한 종형에 주계약이 둘 실린다."""
    mains = [b for b in rider_blocks(pages_from_text(TEXT)) if b.is_main]
    assert [b.rider_name for b in mains] == ["주계약", "주계약"]


def test_each_variant_gets_only_the_blocks_listed_for_it():
    g, r = run(RIDERS)
    assert riders_of(r, "VA1") == riders_of(r, "VA2") == ["무배당 가질환진단특약(갱신형) 2504", "주계약"]
    assert riders_of(r, "VB1") == ["무배당 나질환입원특약(갱신형) 2504", "무배당 나질환진단특약(갱신형) 2504", "주계약"]
    assert len({x["특약ID"] for x in r.riders}) == len(r.riders) == 7
    assert len({b["급부ID"] for b in r.benefits}) == len(r.benefits)
    assert check_rows("sys_특약", r.riders) == {} and check_rows("sys_급부", r.benefits) == {}
    main = {x["종형ID"]: x["특약ID"] for x in r.riders if x["담보구분"] == "주계약"}
    got = {vid: sorted(b["원시급부명"] for b in r.benefits if b["특약ID"] == rid) for vid, rid in main.items()}
    assert got == {"VA1": ["가질환진단보험금", "건강관리자금"], "VA2": ["가질환진단보험금", "건강관리자금"],
                   "VB1": ["건강관리자금", "나질환진단보험금"]}
    # 조각마다 한 번만 부른다. 같은 보장형의 1종과 2종은 한 번 뽑은 값을 함께 싣는다
    assert r.stats["조각"] == 5 and len(g.texts) == 5


def test_block_that_no_variant_carries_is_not_sent_to_the_model():
    g, r = run({"VA1": RIDERS["VA1"], "VB1": ("주계약 (나형)",), "VA2": RIDERS["VA2"]})
    assert r.stats["조각"] == 3 and not any("나질환입원" in t or "나질환진단특약" in t for t in g.texts)


def test_without_rider_lists_every_block_goes_to_every_variant():
    """추출대상특약을 적지 않은 종형(다른 상품 전부)은 전과 같다."""
    _, r = run(None)
    assert all(len(riders_of(r, v)) == 4 for v in NAMES)        # 주계약 행은 첫 조각 것 하나만 남는다
    assert P.carries(rider_blocks(pages_from_text(TEXT))[0], ())


def test_variant_scope_ignores_the_cover_type_mark_of_the_variant_name():
    every = [C.Target(v, n, {}, None) for v, n in NAMES.items()]

    def applies(scope):
        return [C._applies(scope, t, every) for t in every]

    assert applies("1종(간편가입)") == [True, True, False]
    assert applies("2종 (일반가입)") == [False, False, True]
    assert applies("1종(간편가입)[가형, 나형]") == [True, True, False]
    assert applies("1종(간편가입)[가형]") == [True, False, False]      # 보장형까지 적혀 있으면 그 종형만
    assert applies("3종(간편가입)") == [None, None, None]
    assert applies("") == [True, True, True]


def test_rider_name_with_a_kind_mark_is_found_only_for_that_kind():
    rider = "무배당 가질환진단특약(갱신형) 2504"
    key = ids.rider_lineage_key(rider)
    one = C.Target("VA1", "1종(간편가입)[가형]", {key: "VA1_T1"}, None)
    two = C.Target("VA2", "2종(일반가입)[가형]", {key: "VA2_T1"}, None)
    assert one.rider(f"{rider} 1종(간편가입)") == (True, "VA1_T1")
    assert two.rider(f"{rider} 1종(간편가입)") == (False, None)            # 다른 종의 표시면 떼지 않는다
    assert two.rider(f"{rider} 2종(일반가입)") == (True, "VA2_T1")
    both = f"{rider}[1종(간편가입), 2종(일반가입)]"
    assert one.rider(both) == (True, "VA1_T1") and two.rider(both) == (True, "VA2_T1")
    assert one.rider("(무)가질환진단특약(갱신형) 2504") == (True, "VA1_T1")
    assert one.rider("무배당 없는특약 2504 1종(간편가입)") == (False, None)


def test_rider_lists_in_the_real_targets_name_one_main_contract_each():
    """대상 설정의 추출대상특약은 종형마다 주계약 하나를 적고, 같은 요약서를 쓰는 종형끼리 목록이 겹치지 않거나 같다."""
    for org in ("epost", "hanwha", "samsungfire"):
        targets = json.loads((ROOT / f"data/targets/{org}.json").read_text(encoding="utf-8"))
        for product in targets["상품"]:
            lists = [tuple(v["추출대상특약"]) for v in product["종형"] if v.get("추출대상특약")]
            for heads in lists:
                assert sum(h.replace(" ", "").startswith("주계약") for h in heads) == 1, (org, heads)
            for a in lists:
                for b in lists:
                    assert a == b or not set(a) & set(b), (org, a, b)


def test_variant_carries_its_rider_list_but_the_sheet_row_does_not():
    targets = json.loads((ROOT / "data/targets/epost.json").read_text(encoding="utf-8"))
    codes = {v["공시상품코드"] for p in targets["상품"] for v in p["종형"]}
    index = [{"기관": "EPOST", "상품코드": c, "상품명": "시험", "판매시작일": "2025-04-03", "판매종료일": None,
              "문서": "상품요약서", "해시": "h", "저장이름": "s", "쪽수": 1} for c in codes]
    found = {v.row["공시상품코드"]: v for v in VV.build(targets, index)[0]}
    assert found["P610196"].riders[0] == "주계약 (암보장형)" and found["P610197"].riders[0] == "주계약 (2대질병보장형)"
    assert found["P500129"].riders == ()
    assert all("추출대상특약" not in v.row for v in found.values())
    assert check_rows("sys_상품종형", [v.row for v in found.values()]) == {}


def test_new_cover_types_get_their_own_lineage_and_one_summary_group():
    """보장형마다 모상품ID를 나눠 같은 종의 두 보장형이 다른 계보가 되고, 한 요약서를 쓰는 네 종형은 상품 항목이 둘이어도 한 그룹이다."""
    targets = json.loads((ROOT / "data/targets/epost.json").read_text(encoding="utf-8"))
    codes = {v["공시상품코드"] for p in targets["상품"] for v in p["종형"]}
    new = {"P610196", "P610197", "P610198", "P610199"}
    index = [{"기관": "EPOST", "상품코드": c, "상품명": "시험", "판매시작일": "2025-04-03", "판매종료일": None,
              "문서": "상품요약서", "해시": "same" if c in new else c, "저장이름": "s", "쪽수": 1} for c in codes]
    found = VV.build(targets, index)[0]
    rows = {v.row["공시상품코드"]: v.row for v in found}
    keys = [rows[c]["종형계보키"] for c in sorted(new)]
    assert len(set(keys)) == 4
    assert not set(keys) & {r["종형계보키"] for c, r in rows.items() if c not in new}
    # 스냅샷과 견주기: 적재 전에는 새 종형이 스냅샷에 없고, 적재 뒤에는 스냅샷의 행이 여기서 만든 행과 종형계보키, 모상품ID 가 같다.
    # 어느 쪽이든 새 계보키는 다른 종형의 계보키와 겹치지 않는다(2026-11-25. 스냅샷 갱신 뒤에도 통과하게 바꿈)
    snapshot = [json.loads(line) for line in
                (ROOT / "data/snapshot/sys_상품종형.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {r["종형ID"]: r for r in snapshot}
    new_ids = {rows[c]["종형ID"] for c in new}
    for c in new:
        had = by_id.get(rows[c]["종형ID"])
        if had is not None:
            assert (had["종형계보키"], had["모상품ID"]) == (rows[c]["종형계보키"], rows[c]["모상품ID"]), c
    assert not set(keys) & {r["종형계보키"] for r in snapshot if r["종형ID"] not in new_ids}
    assert {rows[c]["모상품ID"] for c in ("P610196", "P610198")} == {"EPOST_MORESIMPLE_CANCER"}
    assert {rows[c]["모상품ID"] for c in ("P610197", "P610199")} == {"EPOST_MORESIMPLE_2CI"}
    groups = [sorted(v.row["공시상품코드"] for v in g) for g in VV.by_summary(found)]
    assert sorted(new) in groups and sum(len(g) for g in groups) == len(found)


TWO_PRODUCTS = {"기관코드": "EPOST", "공시목록URL": "https://example.invalid/list", "상품": [
    {"모상품ID": f"EPOST_GANA_{cover}", "개정연월": "2504", "비교역할구분": "정밀비교", "갱신유형": "갱신", "갱신주기년": 15,
     "환급유형": "표준형", "납입면제적용": False, "갱신형특약주기년": 15,
     "종형": [{"공시상품코드": f"X{cover}1", "종형명": f"1종(간편가입)[{cover}형]", "심사유형": "간편심사", "간편고지약칭": "3.0.5",
               "고지최근소견개월": 3, "고지입원수술년수": 0, "고지중대질병년수": 5, "고지수술포함여부": None, "고지중대질병수": 1,
               "고지중대질병목록": f"{cover}질환", "고지소견범위": "서면", "추출대상특약": list(heads)},
              {"공시상품코드": f"X{cover}2", "종형명": f"2종(일반가입)[{cover}형]", "심사유형": "일반심사", "간편고지약칭": "일반",
               "추출대상특약": list(heads)}]}
    for cover, heads in (("가", RIDERS["VA1"]), ("나", RIDERS["VB1"]))]}


def test_two_product_entries_sharing_a_summary_are_extracted_once_and_split_by_variant():
    """보장형마다 상품 항목을 나눠도 요약서 파일로 묶어 한 번만 뽑고, 조각은 종형마다 추출대상특약으로 가른다."""
    index = [{"기관": "EPOST", "상품코드": v["공시상품코드"], "상품명": f"무배당 가나보험(갱신형) 2504 {v['종형명']}",
              "판매시작일": "2025-04-03", "판매종료일": None, "문서": "상품요약서", "해시": "same", "저장이름": "yoyak", "쪽수": 9}
             for p in TWO_PRODUCTS["상품"] for v in p["종형"]]
    store = SheetStore(MemoryBackend())
    for name in TABS:
        store.write_tab(name, [])
    g = FakeGemini()
    report = job.run(g, store, TWO_PRODUCTS, index, {"yoyak": TEXT}.get, datetime(2026, 11, 25, 10, 0, tzinfo=KST),
                     read_thresholds=False, parts=("급부",))
    assert report.written and report.errors == {} and len(report.done) == 4
    assert len(report.table) == 1 and len(g.texts) == 5                  # 요약서 하나를 한 번만, 조각마다 한 번씩 뽑는다
    assert not any("서로 다름" in n for n in report.notes)
    sheet = store.read()
    parent = {r["종형ID"]: r["모상품ID"] for r in sheet["sys_상품종형"]}
    names: dict[str, set[str]] = {}
    for r in sheet["sys_특약"]:
        names.setdefault(parent[r["종형ID"]], set()).add(r["원시특약명"])
    assert names == {"EPOST_GANA_가": {"무배당 가질환진단특약(갱신형) 2504", "주계약"},
                     "EPOST_GANA_나": {"무배당 나질환입원특약(갱신형) 2504", "무배당 나질환진단특약(갱신형) 2504", "주계약"}}
    assert len(sheet["sys_특약"]) == 2 * 2 + 2 * 3
    assert len({r["종형계보키"] for r in sheet["sys_상품종형"]}) == 4
    assert {r["개정판ID"] for r in sheet["sys_상품종형"]} == {"EPOST_GANA_가_2504", "EPOST_GANA_나_2504"}
