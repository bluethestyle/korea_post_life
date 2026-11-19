"""우체국 형식이 아닌 사업방법서·상품요약서의 절 찾기.

시험 글은 실제 문서의 제목 모양과 항목 구성만 본떠 직접 만든 것이다. 상품과 특약 이름은 지어낸 것이다.
"""
from postlife.extract import conditions as C
from postlife.extract.segment import pages_from_text

# 모양 1: 가입나이가 절 제목의 끝에 오고, 주계약만 적는 사업방법서. 가입한도 절이 없고 의무가입은 "해당 없음"이다.
METHOD_SINGLE = """
===== 3쪽 =====
(사업방법서 별지)
1. 보험종목에 관한 사항
가. 보험종목의 명칭
- 가나다통합보험 무배당
2. 보험기간, 보험료 납입기간, 보험료 납입주기 및 피보험자 가입나이
가. 보험기간, 보험료 납입기간 및 피보험자 가입나이
- 가입최저나이: 만15세
- 가입최고나이: 보험종목, 성별, 보험기간 및 보험료 납입기간별로 아래와 같음
90세만기 종신
구 분
남자 여자 남자 여자
10년납 79세 79세 80세 80세
간편가입형(1년)
20년납 69세 69세 80세 80세
1 - 1

===== 4쪽 =====
일반가입형 20년납 69세 69세 80세 80세
나. 보험료 납입주기: 월납
3. 의무가입에 관한 사항
- 해당 없음
4. 고정부가에 관한 사항
- 해당 없음
18. 기타사항
가. 보험가입금액(1구좌) : 1,000만원
나. 간편가입형에 관한 사항
1 - 2

===== 5쪽 =====
( 별첨 1 )
계약 전 알릴의무 사항[간편가입형(1년)]
"""

# 모양 2: 여러 종을 한 문서에 담고 절 안을 종별 항목으로 나눈 사업방법서. 결합 조건은 기타사항의 종별 항목에 있다.
METHOD_MULTI = """
===== 3쪽 =====
3. 보험의 목적
가. 피보험자의 신체
4. 보험기간, 보험료 납입기간, 가입나이 및 보험료 납입주기
가. 1종 및 9종
01. 건강 모듈 보장
기본 100세만기 20년납 16세~40세 월납
·[건강]상해 사망

===== 4쪽 =====
나. 11종 및 12종
01. 건강 모듈 보장
기본 100세만기 20년납 16세~45세 월납
라. 7종
01. 건강 모듈 보장
·[건강]보험료 납입면제대상 100세만기 20년납 16세~70세

===== 5쪽 =====
라. 8종
01. 건강 모듈 보장
기본 100세만기 20년납 16세~70세 월납
·[건강]상해 사망
주1) 고지유형에 따라 315·5는 [별첨2], 325·5는
[별첨3], 335·5는 [별첨4] 계약 전 알릴 의무사항을 적용함

===== 6쪽 =====
5. 의무가입에 관한 사항
- 7종
건강 모듈 보장 ∙[건강]보험료 납입면제대상 특별약관
6. 배당에 관한 사항
배당금을 지급하지 않음

===== 7쪽 =====
27. 기타사항
가. 공통사항
(1) 이 상품은 독립특별약관을 추가로 부가하여 운영할 수 있음
나. 1종 및 9종
(1) 요양 모듈 보장에 관한 사항

===== 8쪽 =====
사. 7종 및 8종
(4) 아래에 정한 특별약관의 경우 선행가입 특별약관에 가입한 경우에 한하여 가입 가능함
특별약관 선행가입 특별약관
·[건강]5대골절 진단비 ·[건강]골절 진단비

===== 9쪽 =====
[별첨1] 부가가능 독립특별약관
1. 가나다 특별약관
"""

# 요약서 모양 1: 절 번호와 제목이 두 줄로 갈려 있다.
SUMMARY_SPLIT_TITLE = """
===== 6쪽 =====
2.
보험가입자격요건
가. 보험의 종류
(1) 간편가입형(1년)
라. 가입나이(주계약)
- 가입최저나이: 만15세
마. 가입한도
~70세 300만원~1,000만원
※ 71세 이상의 가입한도는 300만원
바. 건강진단 여부
- 간편가입형의 경우 무진단으로 가입 가능
6/60

===== 7쪽 =====
3.
보험금 지급사유 및 지급제한 사항
가. 상품의 구성
"""

# 요약서 모양 2: "□ 가입자격제한" 아래가 종별 항목으로 나뉜다.
SUMMARY_BY_TYPE = """
===== 22쪽 =====
● 가입자격제한 등 상품별 특이사항
□ 가입자격제한
가나다 건강보험의 가입이 가능한 나이는 아래와 같습니다.
가. 7종(납입면제형)
기본 100세만기 20년납 16세~70세 월납
·[건강]상해 사망

===== 36쪽 =====
나. 8종(일반형)
기본 100세만기 30년납 16세~60세 월납
·[건강]상해 사망
주1) 선택계약의 보험기간은 기본계약의 보험기간 이내로 함

===== 49쪽 =====
□ 상품의 특이사항
1) 이 상품의 피보험자는 유형에 따라 가입가능함
● 보험금 지급사유, 지급금액 및 지급제한사항
"""


def test_age_heading_with_other_word_order():
    s = C.method_sections(pages_from_text(METHOD_SINGLE))
    assert set(s) == {"가입나이", "특약부가"}          # 가입한도 절은 이 문서에 없다
    age = s["가입나이"]
    assert age.text.startswith("2. 보험기간, 보험료 납입기간") and (age.first_page, age.last_page) == (3, 4)
    assert "간편가입형(1년)" in age.text and "일반가입형 20년납" in age.text and "의무가입" not in age.text
    assert s["특약부가"].text == "3. 의무가입에 관한 사항\n- 해당 없음"


def test_scope_is_ignored_when_section_has_no_items_for_it():
    plain = C.method_sections(pages_from_text(METHOD_SINGLE))
    scoped = C.method_sections(pages_from_text(METHOD_SINGLE), scope="간편가입형(1년)")
    assert scoped == plain                              # 종별 항목이 없는 문서: 그대로이고 "기타사항"도 붙지 않는다


def test_section_runs_past_zero_padded_items_and_inline_appendix_marks():
    s = C.method_sections(pages_from_text(METHOD_MULTI))
    assert set(s) == {"가입나이", "특약부가"}          # scope 없이는 기타사항을 돌려주지 않는다
    age = s["가입나이"]
    assert (age.first_page, age.last_page) == (3, 5)
    assert age.text.count("01. 건강 모듈 보장") == 4 and "[별첨4] 계약 전 알릴 의무사항을 적용함" in age.text
    assert "5. 의무가입" not in age.text
    rule = s["특약부가"]
    assert rule.text.startswith("5. 의무가입에 관한 사항") and "납입면제대상 특별약관" in rule.text
    assert "배당" not in rule.text and (rule.first_page, rule.last_page) == (6, 6)


def test_scope_keeps_only_the_items_of_that_type():
    s = C.method_sections(pages_from_text(METHOD_MULTI), scope="8종")
    age = s["가입나이"]
    assert age.text.startswith("4. 보험기간, 보험료 납입기간, 가입나이") and (age.first_page, age.last_page) == (5, 5)
    assert "라. 8종" in age.text and "16세~70세 월납" in age.text
    assert "라. 7종" not in age.text and "가. 1종" not in age.text and "납입면제대상" not in age.text
    other = s["기타사항"]
    assert (other.first_page, other.last_page) == (8, 8) and other.text.startswith("27. 기타사항\n사. 7종 및 8종")
    assert "선행가입" in other.text and "공통사항" not in other.text and "독립특별약관" not in other.text


def test_scope_does_not_match_inside_a_longer_number():
    s = C.method_sections(pages_from_text(METHOD_MULTI), scope="1종")
    assert "가. 1종 및 9종" in s["가입나이"].text and "11종" not in s["가입나이"].text
    assert (s["가입나이"].first_page, s["가입나이"].last_page) == (3, 3)
    assert s["기타사항"].text == "27. 기타사항\n나. 1종 및 9종\n(1) 요양 모듈 보장에 관한 사항"


def test_eligibility_with_number_and_title_on_separate_lines():
    e = C.eligibility_section(pages_from_text(SUMMARY_SPLIT_TITLE))
    assert e.text.startswith("보험가입자격요건") and (e.first_page, e.last_page) == (6, 6)
    assert "300만원~1,000만원" in e.text and "건강진단" not in e.text
    # 건강진단 항목이 없는 문서에서는 다음 절 제목 앞에서 끝나고, 따로 적힌 절 번호("3.")는 남지 않는다
    without = SUMMARY_SPLIT_TITLE.replace("바. 건강진단 여부\n- 간편가입형의 경우 무진단으로 가입 가능\n", "")
    e = C.eligibility_section(pages_from_text(without))
    assert "지급사유" not in e.text and e.text.split("\n")[-1] == "6/60" and e.last_page == 6


def test_eligibility_divided_by_type():
    whole = C.eligibility_section(pages_from_text(SUMMARY_BY_TYPE))
    assert whole.text.startswith("□ 가입자격제한") and (whole.first_page, whole.last_page) == (22, 36)
    assert "가. 7종(납입면제형)" in whole.text and "특이사항" not in whole.text
    one = C.eligibility_section(pages_from_text(SUMMARY_BY_TYPE), scope="8종")
    assert (one.first_page, one.last_page) == (36, 36)
    assert "나. 8종(일반형)" in one.text and "16세~60세" in one.text and "7종" not in one.text


def test_table_of_contents_lines_are_not_taken_for_section_headings():
    # 문서 앞에 목차가 있으면 절 제목과 같은 글이 점선·쪽 번호와 함께 먼저 나온다. 본문의 제목에서 절을 잡아야 한다
    contents = """
===== 1쪽 =====
목 차
1. 보험종목에 관한 사항 ·················· 3
2. 보험기간, 보험료 납입기간, 보험료 납입주기 및 피보험자 가입나이 ·········· 3
3. 의무가입에 관한 사항 .................. 4
18. 기타사항 …………… 4
"""
    plain = C.method_sections(pages_from_text(METHOD_SINGLE))
    assert C.method_sections(pages_from_text(contents + METHOD_SINGLE)) == plain
    assert plain["가입나이"].first_page == 3 and "간편가입형(1년)" in plain["가입나이"].text
    summary = "\n===== 2쪽 =====\n차 례\n□ 가입자격제한 ········ 22\n□ 상품의 특이사항 ········ 49\n" + SUMMARY_BY_TYPE
    assert C.eligibility_section(pages_from_text(summary)) == C.eligibility_section(pages_from_text(SUMMARY_BY_TYPE))
