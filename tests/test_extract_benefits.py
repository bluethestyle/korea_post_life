from postlife.extract import benefits as B
from postlife.extract.segment import Block
from postlife.validate import check_rows

BLOCK = Block(
    "무배당 암진단특약(20년갱신형) 2606",
    """■ 무배당 암진단특약(20년갱신형) 2606
(특약보험가입금액 1,000만원 기준)
지급구분 지 급 사 유 지 급 액
암보장개시일 이후에 최초의 암으로 진단이 확정되었을 때 보험계약일부터 1년미만 500만원
암진단 (단, 최초 1회에 한함) 1년이상 1,000만원
보험금 갑상선암, 기타피부암 ... 각각 최초 1회에 한함 1년미만 100만원 1년이상 200만원
주) 암보장개시일은 계약일부터 그 날을 포함하여 90일이 지난날의 다음날로 하며""",
    10, 11,
)
RAW = {
    "base_amount": "1,000만원",
    "benefits": [
        {"name": "암진단보험금", "target": "암", "amount": "1,000만원", "reduced_period": "1년미만",
         "reduced_amount": "500만원", "reduced2_period": "", "reduced2_amount": "",
         "start_condition": "암보장개시일", "limit": "최초 1회에 한함", "role": "주급부", "quote": "1년이상 1,000만원"},
        {"name": "암진단보험금", "target": "갑상선암·기타피부암", "amount": "200만원", "reduced_period": "1년미만",
         "reduced_amount": "100만원", "start_condition": "", "limit": "각각 최초 1회에 한함", "role": "부수급부",
         "quote": "1년이상 200만원"},
    ],
}


def test_rows_follow_schema_and_rate_is_computed_by_code():
    ex = B.parse(BLOCK, RAW, "m")
    assert ex.problems == [] and ex.base_amount == 1000
    rows = B.benefit_rows("EPOST_P500130_abc", ex)
    assert check_rows("sys_급부", rows) == {}
    first = rows[0]
    assert first["원시급부명"] == "암진단보험금(암)" and first["기준지급금액만원"] == 1000
    assert (first["감액개월1"], first["감액지급률1"], first["면책기간일수"]) == (12, 0.5, 90)
    assert rows[1]["급부역할"] == "부수급부" and rows[1]["면책기간일수"] == 0
    assert first["근거문서쪽수"] == 10 and first["급부ID"] != rows[1]["급부ID"]
    rider = B.rider_row("EPOST_P500130_abc", BLOCK, 20)
    assert check_rows("sys_특약", [rider]) == {}
    assert rider["갱신여부"] is True and rider["갱신주기년"] == 20 and rider["담보구분"] == "선택특약"
    assert first["특약ID"] == rider["특약ID"]


def test_amount_forms_cover_how_documents_write_money():
    assert "1000만원" in B.amount_forms(1000) and "1천만원" in B.amount_forms(1000)
    assert B.amount_forms(1.5)[0] == "1만5천원" and B.amount_forms(0.5)[0] == "5천원"
    assert "1억원" in B.amount_forms(10000)


def test_code_check_passes_what_is_literally_in_the_source():
    ex = B.parse(BLOCK, RAW, "m")
    assert B.literal_problems(ex) == {}


def test_code_check_flags_values_not_in_the_source():
    wrong = {"base_amount": "1,000만원", "benefits": [dict(RAW["benefits"][0], amount="3,000만원")]}
    problems = B.literal_problems(B.parse(BLOCK, wrong, "m"))
    assert problems == {"암진단보험금(암)": ["기준지급금액만원"]}


def test_start_condition_is_turned_into_days_by_code():
    ex = B.parse(BLOCK, RAW, "m")
    assert [b.waiting_days for b in ex.benefits] == [90, 0]
    # 주석에 정의가 없는 보장개시일을 적으면 날수를 지어내지 않고 문제로 남긴다
    bare = Block("t", "치매보장개시일 이후에 진단 확정 시 100만원", 1, 1)
    ex = B.parse(bare, {"benefits": [dict(RAW["benefits"][0], amount="100만원", reduced_period="", reduced_amount="",
                                          start_condition="치매보장개시일")]}, "m")
    assert ex.benefits[0].waiting_days == 0 and "날수를 주석에서 찾지 못함" in ex.problems[0]
    assert B.parse_months("2년 미만") == 24 and B.parse_months("6개월미만") == 6 and B.parse_months("") is None


def test_malformed_and_duplicate_items_are_reported():
    raw = {"benefits": [{"name": "", "amount": "10만원"}, RAW["benefits"][0], RAW["benefits"][0], {"name": "x"}]}
    ex = B.parse(BLOCK, raw, "m")
    assert len(ex.benefits) == 2 and len(ex.problems) == 3


def test_main_contract_and_plain_renewal_riders():
    main = Block("주계약 (보험가입금액 2,000만 원 기준)", "■ 주계약 (보험가입금액 2,000만 원 기준)\n사망보험금", 7, 7)
    assert B.rider_row("V", main, None)["갱신여부"] is False and B.rider_row("V", main, None)["담보구분"] == "주계약"
    plain = Block("무배당 수술특약(갱신형) 2504", "■ 무배당 수술특약(갱신형) 2504", 22, 22)
    row = B.rider_row("V", plain, None)
    assert row["갱신여부"] is True and row["갱신주기년"] is None


def test_inconsistent_values_are_flagged_for_retry():
    from postlife.extract import benefits as B
    from postlife.extract.segment import Block

    raw = {"benefits": [
        {"name": "암직접치료입원보험금", "target": "암", "amount": "5만원", "reduced_period": "1년미만"},
        {"name": "질병입원보험금", "target": "", "amount": "금액 미상"},
        {"name": "암수술보험금", "target": "암", "amount": "300만원", "reduced_period": "1년미만", "reduced_amount": "300만원"},
    ]}
    ex = B.parse(Block("t", "x", 1, 1), raw, "m")
    text = " / ".join(ex.problems)
    assert "하나만 적힘" in text and "금액이 비어 있음" in text and "작지 않음" in text


def test_waiting_days_are_read_from_the_definition_sentence():
    from postlife.extract import benefits as B

    text = ("2. 암보장개시일은 최초계약의 경우 계약일부터 그 날을 포함\n하여 90일이 지난날의 다음날로 하며\n"
            "3. 치매보장개시일은 계약일부터 그 날을 포함하여 1년이 지난 날의 다음날")
    assert B.waiting_definitions(text) == {"암보장개시일": 90, "치매보장개시일": 365}


def test_money_text_is_parsed_by_code():
    from postlife.extract.benefits import parse_money

    cases = {"1,000만원": 1000, "2만5천원": 2.5, "5천원": 0.5, "1억원": 10000, "1억5천만원": 15000, "3천만원": 3000,
             "1,000만원 × 해당 장해지급률": 1000, "매월 60만 원": 60, "2,000만 원 + 플러스적립금": 2000}
    for text, want in cases.items():
        assert parse_money(text) == want, text
    assert parse_money("해당 없음") is None and parse_money(None) is None


def test_waiting_definition_survives_page_numbers_and_brackets():
    from postlife.extract.benefits import waiting_definitions

    assert waiting_definitions("암보장개시일은 최초계약의 경우 계약일부터 그 날을 포\n15\n함하여 90일이 지난날의 다음날") == {"암보장개시일": 90}
    assert waiting_definitions("특정파킨슨병보장개시일은 계약일[부활(효력회복)일]부터 그 날을 포함하여 1년이 지난 날의 다음날로 합니다."
                               " 다만 재해로 발생한 경우 치매보장개시일은 계약일[부활(효력회복)일]로 합니다.") == {"특정파킨슨병보장개시일": 365}


def test_text_after_the_amount_does_not_break_the_code_check():
    block = Block("주계약", "■ 주계약\n2,000만 원\n사망보험금 보험기간 중 사망하였을 때\n+ 플러스적립금", 7, 7)
    raw = {"benefits": [{"name": "사망보험금", "target": "", "amount": "2,000만 원 + 플러스적립금", "reduced_period": "",
                         "reduced_amount": "", "start_condition": "", "limit": "", "role": "주급부", "quote": ""}]}
    ex = B.parse(block, raw, "m")
    assert ex.benefits[0].amount == 2000 and B.literal_problems(ex) == {}
    from postlife.extract import verify as V
    claim = V.checks(ex.benefits[0], block.text)["기준지급금액만원"][0]["instructions"]
    assert "지급액 칸에 '2,000만 원 + 플러스적립금'" in claim


def test_reduction_period_not_in_the_source_is_flagged_by_code():
    wrong = {"benefits": [dict(RAW["benefits"][0], reduced_period="2년미만")]}
    ex = B.parse(BLOCK, wrong, "m")
    assert ex.benefits[0].reduced_months == 24
    assert B.literal_problems(ex) == {"암진단보험금(암)": ["감액개월1"]}
