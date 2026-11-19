"""우체국 형식이 아닌 상품요약서의 "보험금 지급사유" 절 자르기.

시험 글은 실제 문서의 제목·경계 표시 모양만 본떠 직접 만든 것이다. 상품과 특약 이름은 지어낸 것이다.
"""
import pytest

from postlife.extract.segment import benefit_section, pages_from_text, rider_blocks, scope_parts

# 모양 1: "나. 보험금 지급사유 및 보험급부별 …" 아래 "■ 특약명". 이름이 두 줄로 갈리고, 조각 안이 가입유형별로 다시 나뉜다.
MARKED = """
===== 23쪽 =====
3.
보험금 지급사유 및 지급제한 사항
가. 상품의 구성
주계약 가나다통합보험 무배당 주계약
+ 급여 스텐트삽입술 보장특약(연1회)(고지통합)(갱신형)(TA3.1) 무배당
나. 보험금 지급사유 및 보험급부별 보험금 지급제한 사유
아래 내용은 간단히 요약 정리한 것입니다.
23/60

===== 24쪽 =====
■ 주계약
[간편가입형]
(기준 : 보험가입금액 1,000만원)
급부명칭 지급사유 지급금액
경과기간
사망보험금 보험기간 중 피보험자가 사망하였을 경우 1년미만 500만원
1년이상 1,000만원
[일반가입형 및 건강가입형]
(기준 : 보험가입금액 1,000만원)
급부명칭 지급사유 지급금액
사망보험금 보험기간 중 피보험자가 사망하였을 경우 1,000만원
24/60

===== 25쪽 =====
■ 계속받는 비급여(급여 전액본인부담 포함) 항암치료보장특약 (1천만원한도)(고지통
합)(KTA1.1) 무배당
(기준 : 특약가입금액 1억원)
급부명칭 지급사유 지급금액
항암치료자금 암보장개시일 이후에 항암치료를 받았을 경우 1,000만원
주) 1. 이 특약의 암보장개시일은 계약일부터 그 날을 포함하여 90일이 지난 날의 다음 날로 합니다.
25/60

===== 26쪽 =====
2. 지급금액의 경과기간은 보험계약일부터 치료일까지의 경과기간입니다.
■ 급여 스텐트삽입술 보장특약(연1회)(고지통합)(갱신형)(TA3.1) 무
배당
(기준: 특약가입금액 100만원)
스텐트삽입술자금 보험기간 중 스텐트삽입술을 받았을 경우 1회당 100만원
26/60

===== 27쪽 =====
4.
보험료 산출기초
가. 보장부분 적용이율
■ 적용이율 안내
"""

# 모양 2: "□ 보험금 지급사유 및 지급금액" 아래 담보가 표 하나에 이어진다. 담보 사이에 경계 표시가 없다.
TABLE = """
===== 50쪽 =====
● 보험금 지급사유, 지급금액 및 지급제한사항
□ 보험금 지급사유 및 지급금액
◆ 기본계약
보장명 지급사유 지급금액
상해 사망 상해사고로 사망한 경우 가입금액
◆ 선택계약
보장명 지급사유 지급금액
보장개시일 이후 약관에 정한 암으로 진단 확정된 경우
암 진단비(유사암 제외) ※ 암의 보장개시일은 최초 계약일 또는 부활(효력회복) 가입금액
일부터 90일이 지난날의 다음날임

===== 51쪽 =====
보장명 지급사유 지급금액
보험기간 중 유사암으로 진단 확정된 경우
유사암 진단비(1년50%) ※ 최초 보험가입후 1년 미만에 보험금 지급사유가 발생 가입금액
한 경우 가입금액의 50% 지급

===== 52쪽 =====
□ 보험금 지급제한사항
1) 회사는 제1회 보험료를 받은 때부터 보장을 합니다.
"""


def test_marked_format_is_cut_at_rider_headings():
    blocks = rider_blocks(pages_from_text(MARKED))
    assert [b.title for b in blocks] == [
        "주계약",
        "계속받는 비급여(급여 전액본인부담 포함) 항암치료보장특약 (1천만원한도)(고지통합)(KTA1.1) 무배당",
        "급여 스텐트삽입술 보장특약(연1회)(고지통합)(갱신형)(TA3.1) 무배당",
    ]
    main, cancer, stent = blocks
    assert main.is_main and (main.first_page, main.last_page) == (24, 24)
    assert (cancer.first_page, cancer.last_page) == (25, 26) and "경과기간입니다" in cancer.text
    assert (stent.first_page, stent.last_page) == (26, 26)
    # 절은 다음 절 제목("4." / "보험료 산출기초") 앞에서 끝난다. 번호만 적힌 줄도 남지 않는다
    assert "산출기초" not in stent.text and not stent.text.rstrip().endswith("4.")
    assert "상품의 구성" not in main.text


def test_base_amount_is_read_in_both_notations():
    main, cancer, stent = rider_blocks(pages_from_text(MARKED))
    assert (main.base_amount, cancer.base_amount, stent.base_amount) == (1000, 10000, 100)


def test_block_is_split_by_enrolment_type():
    main, cancer, _ = rider_blocks(pages_from_text(MARKED))
    parts = scope_parts(main)
    assert [scope for scope, _ in parts] == ["간편가입형", "일반가입형 및 건강가입형"]
    simple, general = (text for _, text in parts)
    assert simple.startswith("■ 주계약") and general.startswith("■ 주계약")
    assert "1년미만 500만원" in simple and "1년미만" not in general
    assert scope_parts(cancer) == [("", cancer.text)]


def test_heading_without_marker_at_page_top_starts_a_block():
    # 쪽 첫 줄에 "■" 없이 특약 이름만 있고 바로 아래에서 표가 시작되면 머리줄이다. 본문에 나온 특약 이름은 머리줄이 아니다
    bare = MARKED.replace("\n===== 27쪽 =====\n", """
===== 27쪽 =====
가나다수술보장특약(최초1회한)(고지통합)(갱신형)(TA1.1) 무배당
(1) 가나다 관혈수술자금
(기준 : 특약가입금액 1,000만원)
수술자금 보험기간 중 수술을 받았을 경우 1,000만원
주) 1. 이 특약은 다음 특약과 함께 가입할 수 있습니다.
급여 스텐트삽입술 보장특약(연1회)(고지통합)(갱신형)(TA3.1) 무배당
27/60

===== 28쪽 =====
이 특약의 보험료 납입을 면제하여 드립니다. 다만 가나다특약(고지통합) 무배당
(기준 : 특약가입금액 1,000만원)은 제외합니다.
28/60

===== 29쪽 =====
""")
    blocks = rider_blocks(pages_from_text(bare))
    assert len(blocks) == 4 and blocks[3].title == "가나다수술보장특약(최초1회한)(고지통합)(갱신형)(TA1.1) 무배당"
    assert (blocks[3].first_page, blocks[3].last_page) == (27, 28) and blocks[3].base_amount == 1000
    assert "가나다" not in blocks[2].text and "산출기초" not in blocks[3].text


def test_table_format_section_is_found_but_not_cut():
    pages = pages_from_text(TABLE)
    section = benefit_section(pages)
    assert section.title == "□ 보험금 지급사유 및 지급금액" and (section.first_page, section.last_page) == (50, 51)
    assert "유사암 진단비(1년50%)" in section.text and "지급제한사항" not in section.text
    with pytest.raises(ValueError, match="특약 경계"):
        rider_blocks(pages)


def test_section_of_marked_format_spans_all_riders():
    section = benefit_section(pages_from_text(MARKED))
    assert (section.first_page, section.last_page) == (23, 26) and section.title.startswith("나. 보험금 지급사유")


def test_table_of_contents_lines_are_not_taken_as_the_section():
    toc = """
===== 1쪽 =====
목 차
가. 상품의 구성 ······ 3
나. 보험금 지급사유 및 보험급부별 보험금 지급제한 사유 ······ 5
4. 보험료 산출기초 ······ 9
===== 5쪽 =====
나. 보험금 지급사유 및 보험급부별 보험금 지급제한 사유
■ 가나보장특약(고지통합)(TA1.1) 무배당
(기준 : 특약가입금액 1,000만원)
급부명칭 지급사유 지급금액
가나자금 가나로 진단되었을 경우 1,000만원
4.
보험료 산출기초
"""
    pages = pages_from_text(toc)
    assert benefit_section(pages).first_page == 5
    blocks = rider_blocks(pages)
    assert [b.title for b in blocks] == ["가나보장특약(고지통합)(TA1.1) 무배당"] and "산출기초" not in blocks[0].text
    # 쪽 번호만 빈칸 뒤에 붙은 목차 줄도 건너뛴다
    assert benefit_section(pages_from_text(toc.replace(" ······ ", " "))).first_page == 5


def test_renewal_list_reads_short_period_lines_notes_and_leading_dividend_marks():
    from postlife.extract.segment import renewal_periods, rider_key

    text = """
===== 3쪽 =====
▪ 갱신형 특약 :
- 10년, 20년만기 자동갱신(최대 종신)
· (무)가나진단특약(갱신형)
· 다라수술특약(갱신형)(무)
※ 갱신할 때 보험료가 오를 수 있습니다. 자세한 내용은
약관을 참조하시기 바랍니다.
- 5년만기 자동갱신
· 마바입원특약(갱신형)(무)
주) 최대 100세까지 갱신합니다.
다. 보험료 납입기간
"""
    periods = renewal_periods(pages_from_text(text))
    assert len(periods) == 3
    assert periods[rider_key("다라수술특약(갱신형)(TA1.1) 무배당")] == [10, 20]      # 앞 숫자에 "만기"를 줄여 쓴 줄
    assert periods[rider_key("마바입원특약(갱신형)(TA1.1) 무배당")] == [5]           # 주석 뒤의 묶음도 읽고, 주석은 이름에 붙지 않는다
    assert periods[rider_key("무배당 가나진단특약(갱신형)")] == [10, 20]             # 목록은 "(무)…", 머리줄은 "무배당 …"
