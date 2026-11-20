"""가입유형별로 표가 갈린 요약서(한화생명 형식)를 종형에 맞게 나눠 싣는지, 그리고 그 형식에서 쓰는 읽기 규칙."""
from datetime import datetime

from postlife import ids
from postlife.extract import benefits as B
from postlife.extract import pipeline as P
from postlife.extract import verify as V
from postlife.extract.segment import pages_from_text, renewal_periods, rider_key, scope_matches
from postlife.gemini import Answer
from postlife.snapshot import KST
from postlife.validate import check_rows

TEXT = """
===== 11쪽 =====
▪ 갱신형 특약 :
- 5년만기, 10년만기 자동갱신(최대 종신)
· 고지혈증보장특약(진단및약물치료)(고지통합)(갱신형)(무)
- 10년만기, 20년만기, 30년만기 자동갱신(최대 종신)
· 계속받는 비급여(급여 전액본인부담 포함) 항암약물·방사선통합치료보장특약(1천만원한도)(고지
통합)(갱신형)(무)
· 뇌혈관질환진단보장특약(고지통합)(갱신형)(무)
11/567
===== 12쪽 =====
· 암진단보장특약(고지통합)(갱신형)(무)
- 50%질병장해보험료납입면제특약(고지통합)(갱신형)(무): 부가대상 계약의 납입기간과 동일
다. 보험료 납입기간 및 납입주기
· 여기는 목록이 아님(갱신형)(무)
===== 24쪽 =====
나. 보험금 지급사유 및 보험급부별 보험금 지급제한 사유
■ 급성심근경색증진단보장특약(고지통합)(KTA1.1) 무배당
[간편가입형]
(기준 : 특약가입금액 1,000만원)
급부명칭 지급사유 지급금액
급성심근경색증 진단자금 최초 1회한 1년미만 500만원 1년이상 1,000만원
[일반가입형 및 건강가입형]
(기준 : 특약가입금액 1,000만원)
급부명칭 지급사유 지급금액
급성심근경색증 진단자금 최초 1회한 1,000만원
■ 뇌혈관질환진단보장특약(고지통합)(갱신형)(TA1.1) 무배당
(기준 : 특약가입금액 1,000만원)
급부명칭 지급사유 지급금액
뇌혈관질환 진단자금 최초 1회한 1년미만 500만원 1년이상 1,000만원
4. 보험료 산출기초
"""
NAMES = {"V1": "간편가입형(1년)", "V5": "간편가입형(5년)", "VG": "일반가입형"}


def row(name, reduced):
    item = {"name": name, "target": "", "amount": "1,000만원", "start_condition": "", "limit": "최초 1회한",
            "role": "주급부", "quote": "1,000만원"}
    if reduced:
        item.update(reduced_period="1년미만", reduced_amount="500만원")
    return {"base_amount": "1,000만원", "benefits": [item]}


class FakeGemini:
    def __init__(self):
        self.texts = []

    def generate(self, model, prompt, schema=None, temperature=0.0):
        body = prompt.split("특약 이름:")[-1]
        self.texts.append(body)
        if "뇌혈관질환" in body:
            return row("뇌혈관질환 진단자금", True)
        return row("급성심근경색증 진단자금", "1년미만" in body)

    def decide(self, model, input_text, questions):
        return {k: (Answer(V.FROM_DAY_ONE, None, {V.FROM_DAY_ONE: 0.97, V.AFTER_START: 0.03}) if q["type"] == "choice"
                    else Answer(True, None, {"true": 0.97, "false": 0.03})) for k, q in questions.items()}


def run(variant_names):
    g = FakeGemini()
    r = P.run_summary(g, pages_from_text(TEXT), list(variant_names), datetime(2026, 11, 19, 10, 0, tzinfo=KST),
                      variant_names=variant_names)
    return g, r


def test_scope_matches_by_prefix_and_joined_names():
    assert scope_matches("간편가입형", "간편가입형(5년)")
    assert scope_matches("일반가입형 및 건강가입형", "일반가입형")
    assert scope_matches("일반가입형 및 건강가입형", "건강가입형(6년)")
    assert not scope_matches("일반가입형 및 건강가입형", "간편가입형(1년)")
    assert scope_matches("", "무엇이든")


def test_each_variant_gets_the_table_of_its_own_scope():
    g, r = run(NAMES)
    assert r.stats["조각"] == 3 and r.stats["처리한 조각"] == 3      # 급성심근경색 2부분 + 뇌혈관 1조각
    rider = {v: ids.rider_id(v, "급성심근경색증진단보장특약(고지통합)(KTA1.1) 무배당") for v in NAMES}
    cut = {b["특약ID"]: b["감액지급률1"] for b in r.benefits if b["특약ID"] in rider.values()}
    assert cut == {rider["V1"]: 0.5, rider["V5"]: 0.5, rider["VG"]: None}
    assert len(r.riders) == 6 and len({x["특약ID"] for x in r.riders}) == 6      # 종형마다 특약 행은 한 번씩
    assert check_rows("sys_특약", r.riders) == {} and check_rows("sys_급부", r.benefits) == {}
    # 부분마다 머리줄은 붙고, 다른 가입유형의 표는 섞이지 않는다
    simple = next(t for t in g.texts if "급성심근경색증" in t and "1년미만" in t)
    assert "[일반가입형" not in simple and "급성심근경색증진단보장특약" in simple


def test_part_without_matching_variant_is_not_sent_to_the_model():
    g, r = run({"V1": "간편가입형(1년)"})
    assert r.stats["조각"] == 2
    assert not any("급성심근경색증" in t and "1년미만" not in t for t in g.texts)


def test_renewal_years_come_from_the_list_and_take_the_shortest():
    periods = renewal_periods(pages_from_text(TEXT))
    assert periods[rider_key("뇌혈관질환진단보장특약(고지통합)(갱신형)(TA1.1) 무배당")] == [10, 20, 30]
    assert periods[rider_key("고지혈증보장특약(진단및약물치료)(고지통합)(갱신형)(KTA1.1) 무배당")] == [5, 10]
    long_name = "계속받는 비급여(급여 전액본인부담 포함) 항암약물·방사선통합치료보장특약(1천만원한도)(고지통합)(갱신형)(TA1.1) 무배당"
    assert periods[rider_key(long_name)] == [10, 20, 30]                       # 두 줄로 갈린 이름
    assert rider_key("암진단보장특약(고지통합)(갱신형)(무)") in periods         # 쪽이 바뀌어도 이어 읽는다
    assert not any("납입면제" in k or "목록이아님" in k for k in periods)
    _, r = run(NAMES)
    brain = next(x for x in r.riders if "뇌혈관" in x["원시특약명"])
    assert (brain["갱신여부"], brain["갱신주기년"]) == (True, 10)


def test_without_variant_names_blocks_are_not_split():
    g = FakeGemini()
    r = P.run_summary(g, pages_from_text(TEXT), ["V1"], datetime(2026, 11, 19, 10, 0, tzinfo=KST))
    assert r.stats["조각"] == 2


def test_plain_won_amounts_are_read():
    assert B.parse_money("입원1일당 5,000원") == 0.5
    assert B.parse_money("1,000만원") == 1000 and B.parse_money("2만5천원") == 2.5
    assert B.money_token("입원1일당 5,000원") == "5000원"
    assert "5000원" in B.amount_forms(0.5)


def test_day_based_period_is_asked_in_source_words():
    b = B.Benefit(name="암다빈치로봇수술자금", target="암", amount=1000.0, waiting_days=None, limit="최초 1회한", role="주급부",
                  quote="", reduced_months=6, reduced_amount=250.0, reduced2_months=12, reduced2_amount=500.0,
                  amount_text="1,000만원", reduced_text="250만원", reduced2_text="500만원",
                  period_text="180일이내", period2_text="1년미만")
    q = V.checks(b, "원문")["감액지급률1"][0]["instructions"]
    assert "180일이내에는 250만원" in q and "12개월 미만에는 500만원" in q


def test_lineage_key_ignores_trailing_rate_code():
    a = ids.rider_lineage_key("80+암진단보장특약(고지통합)(KTA1.1) 무배당")
    assert a == ids.rider_lineage_key("80+암진단보장특약(고지통합)(TA1.2) 무배당")
    assert a != ids.rider_lineage_key("80+암진단보장특약(고지통합)(갱신형)(TA1.2) 무배당")


def test_reduction_exception_is_kept_only_with_a_reduction_and_checked_against_source():
    from postlife.extract.segment import Block
    text = ("■ 수술보장특약(고지통합)(TA1.1) 무배당\n(기준 : 특약가입금액 100만원)\n급부명칭 지급사유 지급금액\n경과기간\n"
            "수술자금 수술을 받았을 경우(수술 1회당) 1년미만 50만원\n※ 단, 재해로 인한 수술시 100만원\n1년이상 100만원\n"
            "입원자금 입원하였을 경우 3만원")
    raw = {"base_amount": "100만원", "benefits": [
        {"name": "수술자금", "target": "", "amount": "100만원", "reduced_period": "1년미만", "reduced_amount": "50만원",
         "reduction_exception": "※ 단, 재해로 인한 수술시 100만원", "start_condition": "", "limit": "수술 1회당", "role": "주급부", "quote": ""},
        {"name": "입원자금", "target": "", "amount": "3만원", "reduction_exception": "재해로 인한 입원시 3만원",
         "start_condition": "", "limit": "", "role": "주급부", "quote": ""}]}
    ex = B.parse(Block("수술보장특약(고지통합)(TA1.1) 무배당", text, 1, 1), raw, "m")
    surgery, stay = ex.benefits
    assert surgery.exception == "재해로 인한 수술시 100만원" and stay.exception == ""     # 감액이 없는 줄에는 남기지 않는다
    assert "감액예외" not in B.literal_problems(ex).get(surgery.label, [])
    rows = B.benefit_rows("V1", ex)
    assert [r["감액예외"] for r in rows] == ["재해로 인한 수술시 100만원", None]
    assert check_rows("sys_급부", rows) == {}
    surgery.exception = "질병으로 인한 수술시 100만원"                                    # 원문에 없는 예외
    assert "감액예외" in B.literal_problems(ex)[surgery.label]
    assert "감액예외" in V.checks(surgery, text)


def test_add_column_widens_rows_once():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("add_column", Path(__file__).resolve().parents[1] / "scripts/add_column.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    header = ["가", "나", "새", "다"]
    assert mod.widen([["가", "나", "다"], [1, 2, 3], [4]], header, "새") == [header, [1, 2, "", 3], [4, "", "", ""]]
    assert mod.widen([header, [1, 2, "", 3]], header, "새") is None
    try:
        mod.widen([["가", "다"]], header, "새")
        assert False
    except ValueError:
        pass


def _add_column_module():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("add_column", Path(__file__).resolve().parents[1] / "scripts/add_column.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_add_column_widens_several_columns_at_once():
    import pytest
    mod = _add_column_module()
    header = ["가", "새1", "나", "새2", "다"]
    old = [["가", "나", "다"], [1, 2, 3], [4], [5, 6, 7, "메모"]]
    assert mod.widen(old, header, ["새1", "새2"]) == [header, [1, "", 2, "", 3], [4, "", "", "", ""],
                                                      [5, "", 6, "", 7, "메모"]]           # 머리행 밖 메모는 끝에 그대로
    # 한 열만 먼저 들어가 있으면 빠진 열만 넣는다. 모두 들어가 있으면 None
    assert mod.widen([["가", "새1", "나", "다"], [1, "x", 2, 3]], header, ["새1", "새2"]) == [header, [1, "x", 2, "", 3]]
    assert mod.widen([header, [1, "", 2, "", 3]], header, ["새1", "새2"]) is None
    for values, columns in (([["가", "나"]], ["새1", "새2"]),          # 머리행이 예상과 다름
                            ([["가", "나", "다"]], ["새1"]),            # 새2도 빠져 있는데 새1만 넣으라 함
                            ([["가", "나", "다"]], ["새1", "없는열"])):   # 스키마에 없는 열
        with pytest.raises(ValueError):
            mod.widen(values, header, columns)
    assert mod.split_columns(["고지중대질병목록,고지소견범위", "고지소견범위", " 감액예외 "]) == ["고지중대질병목록", "고지소견범위",
                                                                                         "감액예외"]


def test_add_column_main_puts_the_two_disclosure_columns_into_the_variant_tab():
    from postlife.schema import TABS
    from postlife.sheets_io import MemoryBackend

    mod = _add_column_module()
    tab = "sys_상품종형"
    new_cols = ("고지중대질병목록", "고지소견범위")
    old_header = [c for c in TABS[tab].header if c not in new_cols]
    row = [f"v{i}" for i in range(len(old_header))]
    backend = MemoryBackend({tab: [old_header, row]})
    assert mod.main(["--tab", tab, "--column", "고지중대질병목록", "--column", "고지소견범위"], backend) == 0
    values = backend.data[tab]
    assert values[0] == TABS[tab].header
    at = [values[0].index(c) for c in new_cols]
    assert [values[1][i] for i in at] == ["", ""]
    assert [v for i, v in enumerate(values[1]) if i not in at] == row                # 다른 칸은 그대로다
    assert mod.main(["--tab", tab, "--column=고지중대질병목록,고지소견범위"], backend) == 0  # 두 번째는 아무것도 하지 않는다
    assert [c for c in backend.calls if c[0] == "overwrite"] == [("overwrite", tab)]
    assert mod.main(["--tab", "sys_급부", "--column", "고지소견범위"], MemoryBackend()) == 1   # 다른 탭의 열이면 멈춘다


def test_variant_reads_only_the_most_specific_scope_in_a_block():
    from postlife.extract.segment import scope_fit

    assert scope_fit("간편가입형", "간편가입형(1년)") == 5 and scope_fit("간편가입형(1년)", "간편가입형(1년)") == 9
    assert scope_fit("일반가입형 및 건강가입형", "간편가입형(1년)") == 0 and scope_fit("", "무엇이든") == 1
    text = TEXT.replace("[일반가입형 및 건강가입형]", "[간편가입형(5년)]")
    g, r = run({"V1": "간편가입형(1년)", "V5": "간편가입형(5년)"})
    assert r.stats["조각"] == 2                               # 원래 글에서는 두 종형이 [간편가입형] 표 하나를 함께 읽는다
    g = FakeGemini()
    r = P.run_summary(g, pages_from_text(text), ["V1", "V5"], datetime(2026, 11, 19, 10, 0, tzinfo=KST),
                      variant_names={"V1": "간편가입형(1년)", "V5": "간편가입형(5년)"})
    rider = {v: ids.rider_id(v, "급성심근경색증진단보장특약(고지통합)(KTA1.1) 무배당") for v in ("V1", "V5")}
    cut = [(b["특약ID"], b["감액지급률1"]) for b in r.benefits if b["특약ID"] in rider.values()]
    # "간편가입형(5년)" 종형은 [간편가입형]과 [간편가입형(5년)] 가운데 꼭 맞는 표만 읽는다. 둘 다 읽으면 급부ID가 겹친다
    assert sorted(cut) == sorted([(rider["V1"], 0.5), (rider["V5"], None)])
    assert check_rows("sys_급부", r.benefits) == {}
