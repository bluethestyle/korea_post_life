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


def test_plain_renewal_rider_takes_its_cycle_from_the_targets_file():
    block = Block("무배당 수술특약(갱신형) 2504", "■ 무배당 수술특약(갱신형) 2504", 22, 22)
    row = B.rider_row("V", block, None, plain_renewal_years=10)
    assert row["갱신여부"] is True and row["갱신주기년"] == 10 and check_rows("sys_특약", [row]) == {}
    assert check_rows("sys_특약", [B.rider_row("V", block, None)]) != {}      # 주기를 모르면 형식 검사에 걸린다


def test_period_check_ignores_words_around_the_period():
    block = Block("t", "■ t\n보험계약일부터\n1만5천원\n1년미만\n보험계약일부터 3만원 1년이상", 1, 1)
    raw = {"benefits": [{"name": "입원보험금", "target": "", "amount": "3만원", "reduced_period": "보험계약일부터 1년미만",
                         "reduced_amount": "1만5천원", "start_condition": "", "limit": "", "role": "주급부", "quote": ""}]}
    assert B.literal_problems(B.parse(block, raw, "m")) == {}
    assert B.period_token("보험계약일부터 2년 미만") == "2년미만"


def test_limit_that_copies_only_part_of_the_condition_is_flagged():
    text = ("■ 표적항암\n암보장개시일 이후에 … 받았을 때(단, 암, 갑상선암, 기타피부암 또는 대장점막내암 중 최초\n1회에 한함) 1,000만원\n"
            "보험기간 중 재해로 입원하였을 때(1일 이상 입원\n보험계약일부터\n2만원\n일수 1일당, 120일 한도)\n수술을 받았을 때 (수술 1회당) 30만원")
    flat = B.squash(text)
    assert B.limit_is_partial("최초 1회에 한함", flat)                       # "암 … 중"이 빠지면 뜻이 달라진다
    assert not B.limit_is_partial("암, 갑상선암, 기타피부암 또는 대장점막내암 중 최초 1회에 한함", flat)
    assert B.limit_is_partial("1일당, 120일 한도", flat)                     # 끼어든 금액 글자는 빼고 견준다
    assert not B.limit_is_partial("1일 이상 입원일수 1일당, 120일 한도", flat)
    assert not B.limit_is_partial("수술 1회당", flat)
    block = Block("t", text, 1, 1)
    ex = B.parse(block, {"benefits": [dict(RAW["benefits"][0], amount="1,000만원", reduced_period="", reduced_amount="",
                                           start_condition="", limit="최초 1회에 한함")]}, "m")
    assert B.literal_problems(ex) == {"암진단보험금(암)": ["지급한도일부"]}


def test_multiplier_is_kept_in_the_limit_column():
    block = Block("t", "■ 재해보장\n재해장해보험금 1,000만원 ×\n해당\n장해지급률", 1, 1)
    ex = B.parse(block, {"benefits": [{"name": "재해장해보험금", "target": "", "amount": "1,000만원", "reduced_period": "",
                                       "reduced_amount": "", "start_condition": "", "limit": "", "role": "주급부",
                                       "quote": "1,000만원 × 해당 장해지급률"}]}, "m")
    assert ex.benefits[0].amount == 1000 and ex.benefits[0].limit == "× 해당 장해지급률"
    assert B.benefit_rows("V", ex)[0]["지급횟수제한"] == "× 해당 장해지급률"


# ---------- 검토 지적 1~8 ----------

def _item(**over):
    item = {"name": "진단보험금", "target": "", "amount": "1,000만원", "reduced_period": "", "reduced_amount": "",
            "reduced2_period": "", "reduced2_amount": "", "reduction_exception": "", "start_condition": "", "limit": "",
            "role": "주급부", "quote": ""}
    item.update(over)
    return item


def test_money_with_decimal_units_hundreds_and_loose_won():
    cases = {"1.5억원": 15000, "1.2억원": 12000, "2.5천만원": 2500, "5백만원": 500, "1천5백만원": 1500, "2만5,000원": 2.5,
             "1억 2천5백만원": 12500}
    for text, want in cases.items():
        assert B.parse_money(text) == want, text
    assert B.money_token("연간 1.5억원 한도") == "1.5억원" and B.money_token("1일당 2만5,000원") == "2만5000원"
    assert B.money_token("진단시 5백만원") == "5백만원"
    # 전부터 읽던 꼴은 그대로다. 단위가 붙은 금액이 숫자와 "원"만 있는 금액보다 먼저다
    assert B.parse_money("5,000원") == 0.5 and B.parse_money("수수료 5,000원, 한도 1,000만원") == 1000
    assert B.money_token("2.5만원") == "2.5만원" and B.parse_money("37.5만원") == 37.5


def test_period_reads_the_end_of_a_range():
    cases = {"1년이상 2년미만": (24, "2년미만"), "180일초과 1년미만": (12, "1년미만"), "1년6개월미만": (18, "1년6개월미만"),
             "180일이내": (6, "180일이내"), "보험계약일부터 1년 미만": (12, "1년미만"), "1년 이상": (12, "1년")}
    for text, (months, token) in cases.items():
        assert (B.parse_months(text), B.period_token(text)) == (months, token), text
    from postlife.extract import verify as V
    assert V._span(12, "180일초과 1년미만") == "12개월 미만" and V._span(6, "180일이내") == "180일이내"


def test_limit_with_another_amount_is_not_in_the_source():
    flat = B.squash("수술을 받았을 때 (수술 1회당) 1년미만 50만원 ※ 단, 재해로 인한 수술시 100만원 1년이상 100만원 (연간 1,000만원 한도)")
    assert B.limit_in_source("재해로 인한 수술시 100만원", flat) and B.limit_in_source("연간 1,000만원 한도", flat)
    assert not B.limit_in_source("재해로 인한 수술시 500만원", flat)       # 금액만 다른 글자
    assert not B.limit_in_source("연간 5,000만원 한도", flat)
    assert not B.limit_in_source("700만원", flat) and not B.limit_in_source(",", flat)      # 금액뿐인 글자, 빈 글자
    # 원문 쪽에 끼어든 다른 칸의 글자는 전처럼 건너뛴다
    mixed = B.squash("입원하였을 때 (1일 이상 입원\n보험계약일부터\n2만원\n일수 1일당, 120일 한도)")
    assert B.limit_in_source("1일 이상 입원일수 1일당, 120일 한도", mixed)
    assert B.limit_in_source("3일 초과 입원일수 1일당, 60일 한도", B.squash("(3일 초과 입원일수 1\n2만원 1만원\n일당, 60일 한도)"))
    assert not B.limit_in_source("120일 한도", B.squash("입원 1\n2만원\n20일 한도"))      # 숫자 가운데는 가르지 않는다
    block = Block("t", "■ t\n수술 1회당 1년미만 50만원 ※ 단, 재해로 인한 수술시 100만원 1년이상 100만원", 1, 1)
    ex = B.parse(block, {"benefits": [_item(name="수술자금", amount="100만원", reduced_period="1년미만", reduced_amount="50만원",
                                            reduction_exception="재해로 인한 수술시 70만원", limit="수술 1회당")]}, "m")
    assert B.literal_problems(ex) == {"수술자금": ["감액예외"]}
    from postlife.extract import verify as V
    assert "감액예외" in V.checks(ex.benefits[0], block.text)


def test_tail_of_a_larger_number_is_not_in_the_source():
    block = Block("t", "■ t\n진단 확정시 12년미만 150만원 12년이상 1,500만원\n입원 2.5만원", 1, 1)
    ex = B.parse(block, {"benefits": [_item(amount="500만원", reduced_period="2년미만", reduced_amount="50만원"),
                                      _item(name="입원보험금", amount="5만원")]}, "m")
    assert B.literal_problems(ex) == {"진단보험금": ["기준지급금액만원", "감액지급률1", "감액개월1"], "입원보험금": ["기준지급금액만원"]}
    # 옆 칸의 숫자가 줄바꿈으로만 붙어 있는 글자는 그대로 찾는다
    near = Block("t", "■ t\n1년미만 500만원 ※ 단, 계약일부터 180\n1년미만\n일이내 수술시 250만원\n1년이상\n1,000만원", 1, 1)
    ex = B.parse(near, {"benefits": [_item(reduced_period="1년미만", reduced_amount="500만원")]}, "m")
    assert B.literal_problems(ex) == {}


def test_waiting_days_follow_the_closest_definition():
    two = {"암보장개시일": 90, "특정암보장개시일": 180}
    assert B.waiting_days_of({"start_condition": "특정암보장개시일"}, two) == (180, "")
    assert B.waiting_days_of({"start_condition": "암보장개시일"}, two) == (90, "")
    worded = {"이특약의암보장개시일": 90, "이특약의특정암보장개시일": 180}      # 정의 문장의 앞말이 이름에 붙어 읽힌 경우
    assert B.waiting_days_of({"start_condition": "특정암 보장개시일"}, worded) == (180, "")
    assert B.waiting_days_of({"start_condition": "암보장개시일"}, worded) == (90, "")
    one = {"암보장개시일": 90}
    source = B.squash("치매보장개시일 이후에 진단 확정 시 / 암보장개시일은 계약일부터 90일이 지난날의 다음날")
    days, trouble = B.waiting_days_of({"start_condition": "치매보장개시일"}, one, source)       # 원문에 따로 적힌 다른 보장개시일
    assert days == 0 and "찾지 못함" in trouble
    assert B.waiting_days_of({"start_condition": "악성종양보장개시일"}, one, source) == (90, "")   # 원문에 없는 이름은 달리 적은 것으로 본다
    assert B.waiting_days_of({"start_condition": "보장개시일"}, one, source) == (0, "")           # 이름 없는 보장개시일은 계약일


def test_waiting_definition_with_other_starting_days_and_wording():
    assert B.waiting_definitions("암보장개시일은 제1회 보험료를 받은 날부터 그 날을 포함하여 90일이 지난 날의 다음날") == {"암보장개시일": 90}
    assert B.waiting_definitions("암보장개시일(이하 같습니다)은 계약일부터 90일이 경과한 날의 다음날") == {"암보장개시일": 90}
    assert B.waiting_definitions("치매보장개시일은 책임개시일부터 그 날을 포함하여 1년이 지난 날의 다음날") == {"치매보장개시일": 365}
    assert B.waiting_definitions("암보장개시일은 갱신일로 하며, 지급사유가 1년이 경과되어 발생하더라도") == {}


def test_partial_limit_behind_a_closed_bracket_and_unit_pieces():
    flat = B.squash("진단 확정시 (단, 암(유사암 제외) 최초 1회에 한함) 1,000만원 / 수술시(수술 1회당) 30만원")
    assert B.limit_is_partial("최초 1회에 한함", flat)
    assert not B.limit_is_partial("암(유사암 제외) 최초 1회에 한함", flat) and not B.limit_is_partial("수술 1회당", flat)
    # 금액 칸에서 옮겨 온 짧은 단위("1일당")도 조각으로 센다
    block = Block("t", "■ t\n질병으로 입원하였을 때 (120일 한도) 1일당 2만원", 1, 1)
    ex = B.parse(block, {"benefits": [_item(name="입원보험금", amount="2만원", limit="120일 한도")]}, "m")
    assert ex.benefits[0].limit == "1일당, 120일 한도" and B.literal_problems(ex) == {}
    assert not B.limit_in_source("1일당, 90일 한도", B.squash(block.text))


def test_reduction_tiers_are_ordered_and_checked():
    block = Block("t", "■ t\n(가입금액 1,000만원 기준)\n1년미만 500만원 ※ 단, 계약일부터 180일이내 250만원 1년이상 1,000만원", 1, 1)
    swapped = _item(reduced_period="1년미만", reduced_amount="500만원", reduced2_period="180일이내", reduced2_amount="250만원")
    ex = B.parse(block, {"benefits": [swapped]}, "m")
    row = B.benefit_rows("V", ex)[0]
    assert ex.problems == [] and B.literal_problems(ex) == {}
    assert (row["감액개월1"], row["감액지급률1"], row["감액개월2"], row["감액지급률2"]) == (6, 0.25, 12, 0.5)
    assert ex.benefits[0].period_text == "180일이내" and ex.benefits[0].reduced2_text == "500만원"
    bad = [_item(name="가", reduced_period="180일이내", reduced_amount="250만원", reduced2_period="1년미만", reduced2_amount="1,000만원"),
           _item(name="나", reduced2_period="1년미만", reduced2_amount="500만원"),
           _item(name="다", reduced_period="1년미만", reduced_amount="250만원", reduced2_period="1년이내", reduced2_amount="500만원")]
    text = " / ".join(B.parse(block, {"benefits": bad}, "m").problems)
    assert "둘째 감액 금액이 지급액보다 작지 않음: 가" in text and "둘째 구간만 적힘: 나" in text and "기간이 같음: 다" in text


def test_limit_is_judged_for_amounts_with_notes_and_rates():
    from postlife.extract import verify as V

    source = "■ t\n생활자금 진단 확정시 매월 60만원 (최초 36개월 보증지급)\n장해보험금 1,000만원 × 해당 장해지급률"

    def benefit(**over):
        base = dict(name="생활자금", target="", amount=60.0, waiting_days=0, limit="", role="주급부", quote="", amount_text="60만원")
        base.update(over)
        return B.Benefit(**base)

    asked = V.checks(benefit(amount_text="매월 60만원", limit="최초 12개월 보증지급"), source)
    assert "지급액 칸에 '매월 60만원'" in asked["기준지급금액만원"][0]["instructions"] and "지급횟수제한" in asked
    assert "지급횟수제한" not in V.checks(benefit(amount_text="매월 60만원", limit="최초 36개월 보증지급"), source)
    rate = dict(name="장해보험금", amount=1000.0, amount_text="1,000만원")
    assert "지급횟수제한" not in V.checks(benefit(limit="× 해당 장해지급률", **rate), source)       # 곱하는 비율은 지급액 문항에서 본다
    assert "지급횟수제한" not in V.checks(benefit(limit="해당 장해지급률", **rate), "장해보험금 1,000만원 ×\n다른 칸\n해당\n장해지급률")
    asked = V.checks(benefit(limit="× 해당 장해지급률, 최초 2회한", **rate), source)
    assert "곱한 금액" in asked["기준지급금액만원"][0]["instructions"] and "지급횟수제한" in asked


def test_start_condition_is_judged_when_the_word_is_split_across_lines():
    from postlife.extract import verify as V

    b = B.Benefit(name="암진단보험금", target="", amount=100.0, waiting_days=90, limit="", role="주급부", quote="", amount_text="100만원")
    assert "면책기간일수" in V.checks(b, "암보장\n개시일 이후에 암으로 진단 확정시 100만원")
    assert "면책기간일수" not in V.checks(b, "보험기간 중 암으로 진단 확정시 100만원")


def test_multiplier_in_a_neighbouring_row_does_not_make_a_fixed_amount_a_rate():
    from postlife.extract import verify as V

    block = Block("t", "■ t\n입원보험금 60만원\n장해보험금 1,000만원 ×\n해당 장해지급률", 1, 1)
    ex = B.parse(block, {"benefits": [_item(name="입원보험금", amount="60만원", quote="60만원 1,000만원 × 해당"),
                                      _item(name="장해보험금", quote="1,000만원 × 해당 장해지급률")]}, "m")
    fixed, rate = ex.benefits
    assert fixed.limit == "" and rate.limit == "× 해당 장해지급률"
    assert "곱한 금액" not in V.checks(fixed, block.text)["기준지급금액만원"][0]["instructions"]
    assert "곱한 금액" in V.checks(rate, block.text)["기준지급금액만원"][0]["instructions"]


# ---------- 대상마다 보장개시일이 다른 급부 (지어낸 문구) ----------

MIXED = Block("무배당 가상항암치료특약 2701", """■ 무배당 가상항암치료특약 2701
(특약보험가입금액 1,000만원 기준)
지급구분 지급사유 경과기간 지급금액
보험기간 중 보장개시일(암은 암보장개시일) 이후에 1종: 10만원
‘암’, ‘기타피부암’ 또는 ‘갑상선암’으로 진단 확정되고 2종: 20만원
가상표적 1년미만
그 직접적인 치료를 목적으로 가상표적치료를 받았을 때 1종: 20만원
치료자금 (1회당) 2종: 40만원
1년이상
보험기간 중 암보장개시일 이후에 암으로 진단 확정되고 30만원
가상수술 수술을 받았을 때 (수술 1회당)
자금
주) 1. 암보장개시일은 계약일부터 그 날을 포함하여 90일이 지난날의 다음날로 합니다.""", 30, 31)


def _graded(target, start=""):
    """등급마다 한 줄. 대상을 target에 묶어 적었다."""
    return [_item(name="가상표적치료자금", target=target.format(grade), amount=f"{full}만원", reduced_period="1년미만",
                  reduced_amount=f"{cut}만원", start_condition=start, limit="1회당", quote=f"{grade}: {full}만원")
            for grade, full, cut in (("1종", 20, 10), ("2종", 40, 20))]


SURGERY = _item(name="가상수술자금", target="암", amount="30만원", start_condition="암보장개시일", limit="수술 1회당")
SPLIT = [("가상표적치료자금(암·1종)", 90), ("가상표적치료자금(기타피부암·갑상선암·1종)", 0),
         ("가상표적치료자금(암·2종)", 90), ("가상표적치료자금(기타피부암·갑상선암·2종)", 0), ("가상수술자금(암)", 90)]


def test_row_bundling_targets_with_different_start_days_is_split_by_target():
    from postlife.extract import verify as V

    # 모델이 "보장개시일(암은 암보장개시일) 이후"를 보지 못하고 대상을 묶어 한 줄로 적었다
    ex = B.parse(MIXED, {"benefits": _graded("암·기타피부암·갑상선암·{}") + [SURGERY]}, "m")
    assert ex.problems == [] and [(b.label, b.waiting_days) for b in ex.benefits] == SPLIT
    assert ex.benefits[0].split_from == "가상표적치료자금(암·기타피부암·갑상선암·1종)" and ex.benefits[-1].split_from == ""
    assert [(b.amount, b.reduced_amount, b.limit) for b in ex.benefits[:2]] == [(20, 10, "1회당")] * 2    # 나머지 값은 같다
    assert B.literal_problems(ex) == {}
    rows = B.benefit_rows("V", ex)
    assert check_rows("sys_급부", rows) == {} and len({r["급부ID"] for r in rows}) == 5
    # 면책은 코드가 문구에서 정했으므로 판정에 묻지 않는다. 나누지 않은 줄은 전처럼 묻는다
    assert "면책기간일수" not in V.checks(ex.benefits[0], MIXED.text)
    assert "면책기간일수" in V.checks(ex.benefits[-1], MIXED.text)
    # 대상을 아예 적지 않은 줄("1종")도 문구의 대상 목록으로 나눈다. 모델이 보장개시일을 모두에 붙여 적었어도 같다
    listed = Block(MIXED.title, MIXED.text + "\n2. 기타피부암과 갑상선암은 약관에서 정합니다.", 30, 31)
    for raw in (_graded("{}"), _graded("{}", "암보장개시일"), _graded("암·기타피부암·갑상선암·{}", "암보장개시일")):
        ex = B.parse(listed, {"benefits": raw + [SURGERY]}, "m")
        assert [(b.label, b.waiting_days) for b in ex.benefits] == SPLIT


def test_without_a_per_target_start_phrase_rows_stay_as_they_are():
    raw = {"benefits": _graded("암·기타피부암·갑상선암·{}") + [SURGERY]}
    for wording in ("보험기간 중 암보장개시일 이후에", "보험기간 중"):
        block = Block(MIXED.title, MIXED.text.replace("보험기간 중 보장개시일(암은 암보장개시일) 이후에", wording), 30, 31)
        ex = B.parse(block, raw, "m")
        assert [b.label for b in ex.benefits] == ["가상표적치료자금(암·기타피부암·갑상선암·1종)", "가상표적치료자금(암·기타피부암·갑상선암·2종)",
                                                  "가상수술자금(암)"]
        assert [b.waiting_days for b in ex.benefits] == [0, 0, 90] and not any(b.split_from for b in ex.benefits)
    # 문구가 있어도 그 문구가 든 표 줄에 이름이 없는 급부는 나누지 않는다
    other = _item(name="가상수술자금", target="암·기타피부암", amount="30만원", limit="수술 1회당")
    assert [b.label for b in B.parse(MIXED, {"benefits": [other]}, "m").benefits] == ["가상수술자금(암·기타피부암)"]
    # 보장개시일의 날수를 주석에서 읽지 못하면 나누지 않는다
    bare = Block(MIXED.title, MIXED.text.split("주)")[0], 30, 31)
    assert [b.label for b in B.parse(bare, raw, "m").benefits][:2] == ["가상표적치료자금(암·기타피부암·갑상선암·1종)",
                                                                       "가상표적치료자금(암·기타피부암·갑상선암·2종)"]


def test_rows_already_split_by_target_are_not_split_again():
    done = [_item(name="가상표적치료자금", target=t, amount="20만원", reduced_period="1년미만", reduced_amount="10만원",
                  start_condition=s, limit="1회당") for t, s in (("암·1종", "암보장개시일"), ("기타피부암·갑상선암·1종", ""))]
    ex = B.parse(MIXED, {"benefits": done + [SURGERY]}, "m")
    assert [(b.label, b.waiting_days) for b in ex.benefits] == [SPLIT[0], SPLIT[1], SPLIT[4]]
    assert not any(b.split_from for b in ex.benefits)
    # 대상별로 나뉜 줄 옆에 대상을 적지 않은 줄이 있으면 그 줄도 그대로 둔다(같은 급부를 모델이 이미 대상별로 나눴다)
    plain = _item(name="가상표적치료자금", target="2종", amount="40만원", reduced_period="1년미만", reduced_amount="20만원", limit="1회당")
    listed = Block(MIXED.title, MIXED.text + "\n2. 기타피부암과 갑상선암은 약관에서 정합니다.", 30, 31)
    assert [b.label for b in B.parse(listed, {"benefits": done + [plain]}, "m").benefits][-1] == "가상표적치료자금(2종)"
    # 나눈 이름이 다른 줄과 겹치면 나누지 않는다
    both = _graded("암·기타피부암·갑상선암·{}")[:1] + done[:1]
    assert [b.label for b in B.parse(MIXED, {"benefits": both}, "m").benefits] == ["가상표적치료자금(암·기타피부암·갑상선암·1종)",
                                                                                   "가상표적치료자금(암·1종)"]
    # 형식 문제가 걸린 줄은 나누지 않는다(문제가 그 줄 이름에 묶여 있어야 다시 뽑기와 제외가 맞게 돈다)
    broken = _graded("암·기타피부암·갑상선암·{}")[:1]
    broken[0]["reduced_amount"] = "30만원"
    ex = B.parse(MIXED, {"benefits": broken}, "m")
    assert [b.label for b in ex.benefits] == ["가상표적치료자금(암·기타피부암·갑상선암·1종)"] and ex.problems


def test_targets_and_listed_words_are_read_through_table_noise():
    assert B._items("암(기타피부암, 갑상선암 제외)·기타피부암 및 갑상선암·1종") == ["암(기타피부암, 갑상선암 제외)", "기타피부암", "갑상선암", "1종"]
    assert B._items("") == [] and B._items("1종") == ["1종"]
    [phrase] = B.mixed_starts(MIXED.text)
    assert (phrase.special, phrase.start) == ("암", "암보장개시일")
    assert B._listed_words(phrase, B.squash(MIXED.text)) == []          # 기타피부암·갑상선암이 문구 밖에 따로 적혀 있지 않다
    assert B._listed_words(phrase, B.squash(MIXED.text + "\n기타피부암 갑상선암")) == ["기타피부암", "갑상선암"]
    # 표가 풀리며 낱말 사이에 다른 칸 글자가 끼어든 목록
    noisy = B.MixedStart("암", "암보장개시일", "‘암(기타피부20만원암갑상선암제외)’‘기타10만원가상치료피부암’또는‘갑상선암’", ())
    assert B._listed("기타피부암", noisy) and B._listed("갑상선암", noisy) and not B._listed("대장점막내암", noisy)
    assert not B._listed("1종", noisy)                                  # 숫자가 든 낱말은 대상이 아니다
    assert B._listed_words(noisy, B.squash(MIXED.text + " 기타피부암 갑상선암")) == []      # 깨진 낱말이 있으면 읽지 않는다
    # 주석에 든 같은 꼴의 문구는 보지 않는다
    assert B.mixed_starts("■ t\n주) 1. 보장개시일(암은 암보장개시일) 이후에 ‘암’ 또는 ‘갑상선암’으로 진단 확정되면") == []


def test_row_without_targets_is_split_even_when_a_sibling_row_bundles_them():
    # 같은 급부를 모델이 등급마다 다른 꼴로 적었다: 1종은 대상 없이, 2종은 대상을 묶어서. 묶은 줄은 대상별로 나뉜 줄이 아니다
    listed = Block(MIXED.title, MIXED.text + "\n2. 기타피부암과 갑상선암은 약관에서 정합니다.", 30, 31)
    for first, second in (("{}", "암·기타피부암·갑상선암·{}"), ("암·기타피부암·갑상선암·{}", "{}")):
        raw = _graded(first)[:1] + _graded(second)[1:] + [SURGERY]
        ex = B.parse(listed, {"benefits": raw}, "m")
        assert ex.problems == [] and [(b.label, b.waiting_days) for b in ex.benefits] == SPLIT


def test_split_row_whose_id_matches_another_row_is_left_alone():
    # "기타피부암·갑상선암"과 "기타피부암 및 갑상선암"은 글자는 달라도 급부ID가 같다(ids.benefit_id가 구두점과 이음말을 뗀다)
    raw = {"benefits": [_item(name="가상표적치료자금", target=t, amount="20만원", reduced_period="1년미만", reduced_amount="10만원",
                              limit="1회당") for t in ("암·기타피부암·갑상선암", "기타피부암 및 갑상선암")]}
    ex = B.parse(MIXED, raw, "m")
    assert [b.label for b in ex.benefits] == ["가상표적치료자금(암·기타피부암·갑상선암)", "가상표적치료자금(기타피부암 및 갑상선암)"]
    assert not any(b.split_from for b in ex.benefits)
    rows = B.benefit_rows("V", ex)
    assert check_rows("sys_급부", rows) == {} and len({r["급부ID"] for r in rows}) == 2


NEIGHBOUR = Block("무배당 가상항암치료특약 2701", """■ 무배당 가상항암치료특약 2701
(특약보험가입금액 1,000만원 기준)
지급구분 지급사유 경과기간 지급금액
보험기간 중 보장개시일(암은 암보장개시일) 이후에
‘암’, ‘기타피부암’ 또는 ‘갑상선암’으로 진단 확정되고 1년미만 10만원
가상표적 그 직접적인 치료를 목적으로 가상표적치료를 받았을 때
치료자금 (1회당) 1년이상 20만원
치료 목적으로 입원하였을 때 (입원 1일당)
가상입원 1년미만 1만원
일당 1년이상 2만원
기타피부암 또는 갑상선암 제외 사유는 약관에 따릅니다
주) 1. 암보장개시일은 계약일부터 그 날을 포함하여 90일이 지난날의 다음날로 합니다.""", 30, 31)


def test_phrase_belongs_only_to_the_benefit_written_first_in_its_rows():
    # 다음 급부(가상입원일당)의 지급사유가 "보험기간", "피보험자가"로 시작하지 않아 문구가 든 표 줄에 그 이름까지 들어온다.
    # 문구는 먼저 적힌 가상표적치료자금의 것이므로 가상입원일당은 나누지 않는다
    raw = {"benefits": [
        _item(name="가상표적치료자금", target="암·기타피부암·갑상선암", amount="20만원", reduced_period="1년미만", reduced_amount="10만원",
              limit="1회당"),
        _item(name="가상입원일당", target="", amount="2만원", reduced_period="1년미만", reduced_amount="1만원", limit="입원 1일당")]}
    ex = B.parse(NEIGHBOUR, raw, "m")
    assert [(b.label, b.waiting_days, b.split_from) for b in ex.benefits] == [
        ("가상표적치료자금(암)", 90, "가상표적치료자금(암·기타피부암·갑상선암)"),
        ("가상표적치료자금(기타피부암·갑상선암)", 0, "가상표적치료자금(암·기타피부암·갑상선암)"),
        ("가상입원일당", 0, "")]
