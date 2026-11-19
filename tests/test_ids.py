from postlife import ids


def test_normalize_ignores_spacing_width_case():
    assert ids.normalize("무배당 암진단특약 ２５０４") == ids.normalize("무배당암진단특약2504")
    assert ids.normalize("KB") == ids.normalize("kb")


def test_strip_revision():
    assert ids.strip_revision("무배당 암진단특약(갱신형) 2504") == "무배당 암진단특약(갱신형)"
    assert ids.strip_revision("무배당 암진단특약(갱신형) 2606") == "무배당 암진단특약(갱신형)"
    assert ids.strip_revision("뇌혈관질환진단특약(2404.10)") == "뇌혈관질환진단특약"
    # 간편고지 약칭(315, 325, 355)과 20년 같은 숫자는 건드리지 않는다
    assert ids.strip_revision("간편 325 20년갱신형") == "간편 325 20년갱신형"
    assert ids.revision_of("우체국통합건강보험 2504") == "2504"
    assert ids.revision_of("간편 355") is None


def test_ids_are_stable_and_distinct():
    v = ids.variant_id("EPOST", "p500130", "간편 325")
    assert v == ids.variant_id("EPOST", "P500130", "간편  325")
    assert v.startswith("EPOST_P500130_")
    r1 = ids.rider_id(v, "무배당 암진단특약(갱신형) 2606")
    r2 = ids.rider_id(v, "무배당 뇌혈관질환진단특약(갱신형) 2606")
    assert r1 != r2
    assert ids.benefit_id(r1, "암진단보험금") != ids.benefit_id(r1, "소액암진단보험금")


def test_lineage_links_revisions():
    assert ids.rider_lineage_key("무배당 암진단특약(갱신형) 2504") == ids.rider_lineage_key(
        "무배당 암진단특약(갱신형) 2606"
    )
    assert ids.revision_id("EPOST_SIMPLE", "2606") == "EPOST_SIMPLE_2606"
    key = ids.variant_lineage_key("EPOST_SIMPLE", "간편심사", "325", "갱신", None)
    assert key == "EPOST_SIMPLE|간편심사|325|갱신|미지정"


def test_dividend_marker_does_not_split_a_rider():
    # 요약서와 사업방법서가 같은 특약을 다르게 적어도 한 특약으로 이어진다
    names = ["(무)암입원수술특약", "무배당 암입원수술특약", "(무배당)암입원수술특약 2606", "무배당암입원수술특약"]
    assert len({ids.rider_lineage_key(n) for n in names}) == 1
    assert ids.rider_lineage_key("(무)암입원수술특약") != ids.rider_lineage_key("(무)암진단특약")


def test_revision_pattern_ignores_ordinary_numbers():
    assert ids.strip_revision("1004 플랜") == "1004 플랜"
    assert ids.strip_revision("3112 특약") == "3112 특약"
    assert ids.revision_of("우체국간편한건강보험 2606") == "2606"


def test_rider_lineage_survives_the_simple_type_prefix_dropped_in_2606():
    before = ids.rider_lineage_key("무배당 간편Ⅲ암진단특약(20년갱신형) 2504")
    assert before == ids.rider_lineage_key("무배당 간편Ⅱ암진단특약(20년갱신형) 2504")
    assert before == ids.rider_lineage_key("무배당 암진단특약(20년갱신형) 2606")
    # 이름 뒤의 판 번호(재해치료특약Ⅱ)는 다른 특약이므로 떼지 않는다
    assert ids.rider_lineage_key("무배당 재해치료특약Ⅱ 2504") != ids.rider_lineage_key("무배당 재해치료특약 2504")


def test_benefit_id_ignores_punctuation_the_model_varies():
    r = ids.rider_id("V", "무배당 암진단특약(20년갱신형) 2606")
    a = ids.benefit_id(r, "암진단보험금(갑상선암·기타피부암·대장점막내암·제자리암·경계성종양)")
    assert a == ids.benefit_id(r, "암진단보험금(갑상선암, 기타피부암, 대장점막내암, 제자리암 또는 경계성 종양)")
    assert a != ids.benefit_id(r, "암진단보험금(암)")
    assert ids.benefit_id(r, "수술보험금(1종)") != ids.benefit_id(r, "수술보험금(2종)")


def test_unseen_middle_dot_shapes_are_read_as_the_plain_one():
    plain = "뇌출혈·뇌경색진단특약"
    for dot in "ㆍ•‧・･⋅":
        assert ids.rider_lineage_key(plain.replace("·", dot)) == ids.rider_lineage_key(plain), dot
        assert ids.benefit_id("R", f"가나{dot}다라보험금") == ids.benefit_id("R", "가나·다라보험금"), dot
    assert ids.benefit_id("R", "가나ㆍ다라보험금") == ids.benefit_id("R", "가나, 다라보험금")
    # "∙"(U+2219)은 모으지 않는다. "·"로 적힌 이름과 "∙"로 적힌 이름이 시트에 따로 들어가 있어 모으면 그 ID가 바뀐다
    assert ids.rider_lineage_key(plain.replace("·", "∙")) != ids.rider_lineage_key(plain)
    assert ids.benefit_id("R", "가나∙다라보험금") != ids.benefit_id("R", "가나·다라보험금")


def test_ids_already_on_the_sheet_do_not_move():
    # 고치기 전에 만들어져 시트에 있는 꼴들. 값이 바뀌면 담보 매핑이 끊긴다
    assert ids.rider_lineage_key("무배당 암진단특약(20년갱신형) 2606") == "09e1800bf88a"
    assert ids.rider_lineage_key("주계약") == "207746d1505c"
    assert ids.rider_id("V", "급성심근경색증진단보장특약(고지통합)(KTA1.1) 무배당") == ids.rider_id(
        "V", "급성심근경색증진단보장특약(고지통합)(무)")


def test_trailing_dividend_mark_and_revision_inside_brackets_do_not_split_a_rider():
    assert ids.rider_lineage_key("암진단특약 무배당") == ids.rider_lineage_key("무배당 암진단특약")
    assert ids.rider_lineage_key("암진단특약(갱신형 2504)") == ids.rider_lineage_key("암진단특약(갱신형)")
    assert ids.strip_revision("암진단특약(갱신형 2504)") == "암진단특약(갱신형 )"       # 닫는 괄호를 따라 떼지 않는다
    assert ids.strip_revision("가나보험(2610.1) 8종") == "가나보험 8종" and ids.revision_of("가나보험(2610.1)") == "2610"
    assert ids.rider_lineage_key("암진단특약(2504)") == ids.rider_lineage_key("암진단특약 2504")
