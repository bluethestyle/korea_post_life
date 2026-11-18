from postlife.extract.segment import pages_from_text, rider_blocks

TEXT = """
===== 9쪽 =====
◆ 보험금 지급사유 및 지급제한 사항
① 상품의 구성
구분 내용
② 보험금 지급사유
아래 내용은 간단히 요약 정리한 것입니다.
■ 주계약 (보험가입금액 2,000만 원 기준)
지급구분 지 급 사 유 지 급 액
사망보험금 보험기간 중 사망하였을 때 2,000만 원
9

===== 10쪽 =====
■ 무배당 암진단특약(20년갱신형) 2606
(특약보험가입금액 1,000만원 기준)
암진단보험금 500만원 1,000만원

===== 11쪽 =====
주) 1. 암보장개시일은 계약일부터 90일이 지난날의 다음날
■ 이륜자동차 운전 및 탑승중 재해 부담보 특약 2109
가입대상 이륜자동차 운전자
■ 지정대리청구서비스특약 2109
③ 일반적 보험금 지급제한 사유
■ 고지의무
"""


def test_blocks_follow_rider_headings_and_keep_pages():
    blocks = rider_blocks(pages_from_text(TEXT))
    assert [b.rider_name for b in blocks] == ["주계약", "무배당 암진단특약(20년갱신형) 2606"]
    main, cancer = blocks
    assert main.is_main and main.base_amount == 2000 and (main.first_page, main.last_page) == (9, 9)
    assert cancer.base_amount == 1000 and (cancer.first_page, cancer.last_page) == (10, 11)
    assert "90일이 지난날" in cancer.text and "고지의무" not in cancer.text


def test_non_coverage_riders_are_skipped_unless_asked():
    all_blocks = rider_blocks(pages_from_text(TEXT), include_skipped=True)
    assert len(all_blocks) == 4 and "부담보" in all_blocks[2].title


def test_missing_section_is_an_error():
    import pytest

    with pytest.raises(ValueError):
        rider_blocks({1: "보험료 산출기초"})
