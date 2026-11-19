"""급부 표의 세부보장을 코드 규칙으로 읽기.

시험 문구는 실제 표의 말투만 본떠 손으로 짧게 만든 것이다. 담보 이름은 지어냈다.
"""
import pytest

from postlife.extract import table_rules as rules
from postlife.extract.table_rules import Step, build_rows, read_amount, read_cover
from postlife.extract.tables import Cover, Rider
from postlife.validate import check_rows

START90 = "※ 가의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난 날의 다음날임"
CUT_1Y = "※ 최초 보험가입후 1년 미만에 보험금 지급사유가 발생한 경우 50% 감액 지급"


def one(name, reason, amount="가입금액"):
    lines = read_cover(name, reason, amount)
    assert len(lines) == 1
    return lines[0]


def kinds(reading):
    return {rules.doubt_kind(d) for d in reading.doubts}


# ---------------------------------------------------------------------------
# 지급금액 칸
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text, percent", [
    ("가입금액", 100),
    ("가입금액의 20%", 20),
    ("가입금액의 100%", 100),
    ("해당 세부보장의 가입금액", 100),
    ("특별약관 보험가입금액의 20%", 20),
    ("▷비관혈수술 : 가입금액\n▷관혈수술 : 가입금액", 100),      # 대상마다 적었지만 값이 같다
])
def test_amount_as_percent(text, percent):
    assert read_amount(text).percent == percent


@pytest.mark.parametrize("text", [
    "가입후 20년 미만 시 가입금액의 100%를 지급하고 가입후 20년 이상 시 가입금액의 200%",
    "가입금액을 매 5년마다 10%씩 정액 할증한 금액",
    "가입금액의 100%를 5년마다 10%씩 정액할증 한 금액",
])
def test_growing_amount_keeps_base_and_text(text):
    pay = read_amount(text)
    assert pay.percent == 100 and pay.growth == text
    r = one("(체증형)가 일당", "가로 입원한 경우 (180일을 한도로 입원 1일당 일당지급)", text)
    assert r.sure and r.percent == 100 and r.note == text


@pytest.mark.parametrize("text", [
    "대인, 대물 각 1억원 한도\n※ 1사고당 자기부담금 : 대인 없음, 대물 20만원",
    "「수술회차별 체증 금액」",
    "가입금액 한도",
    "5,000만원 한도",
    "1종, 2종 : 해당 세부보장의 가입금액의 100% 3종 : 해당 세부보장의 가입금액의 150%",
])
def test_amount_that_is_not_a_ratio_is_doubted(text):
    r = one("가 보장", "가 사고가 발생한 경우", text)
    assert r.percent is None and rules.D_AMOUNT in r.doubts
    assert " ".join(text.split()) in r.note        # 원문이 남는다


def test_amount_exception_and_by_target_lines():
    pay = read_amount("가입금액\n※ 단, 나암, 다암은 가입금액의 20%")
    assert pay.rest == 100 and pay.by == ((("나암", "다암"), 20.0),)
    pay = read_amount("- 나암 : 가입금액의 20%\n- 나암 외 : 가입금액의 100%")
    assert pay.by == ((("나암",), 20.0), (("나암 외",), 100.0))


# ---------------------------------------------------------------------------
# 감액
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("note, steps", [
    (CUT_1Y, [(12, 0.5)]),
    ("※ 최초 보험가입후 1년미만에 보험금 지급 사유가 발생한 경우 50% 감액 지급함", [(12, 0.5)]),
    ("※ 보험가입후 1년 미만에 보험금 지급사유가 발생한 경우 50% 감액지급", [(12, 0.5)]),
    ("※ 최초 보험가입후 90일 미만에 보험금 지급사유가 발생한 경우 50% 감액 지급", [(3, 0.5)]),
    ("※ 최초 보험가입후 180일 미만에 보험금 지급사유가 발생한 경우 가입금액의 75% 감액 지급(25%지급), "
     "1년 미만에 보험금 지급사유가 발생한 경우 50% 감액 지급함", [(6, 0.25), (12, 0.5)]),
    ("※ 최초 보험가입후 180일 미만에 보험금 지급사유가 발생한 경우 가입금액의 10% 지급, "
     "1년 미만(180일미만 제외)에 보험금 지급사유가 발생한 경우 가입금액의 50% 지급", [(6, 0.1), (12, 0.5)]),
    ("※ 최초 보험가입후 60일 미만에 보험금 지급사유가 발생한 경우 가입금액의 90% 감액 지급(10%지급), "
     "1년 미만에 보험금 지급사유가 발생한 경우 50% 감액 지급", [(2, 0.1), (12, 0.5)]),
    ("※ 최초 보험가입후 180일 미만에 보험금 지급사유가 발생한 경우 가입금액의 10%지급, 181이상~1년 미만에 보험금 지급사유가 "
     "발생한 경우 가입금액의 50%지급, 1년이상 지나고 보험금 지급사유가 발생한 경우 가입금액의 100%지급", [(6, 0.1), (12, 0.5)]),
    ("※ 보장개시일부터 최초 보험가입후 1년 미만에 보험금 지급사유가 발생한 경우 50% 감액 지급", [(12, 0.5)]),
    ("※ 최초 보험가입후 1년 미만에 보험금 지급기간 중 보험금 지급사유 발생시 50% 감액 지급", [(12, 0.5)]),
])
def test_reduction_shapes(note, steps):
    r = one("가 진단비", "보험기간 중 가로 진단 확정된 경우 (최초 1회한 지급)\n" + note)
    assert r.sure, r.doubts
    assert [(s.months, s.rate) for s in r.steps] == steps
    assert r.evidence["감액"] == note[1:].strip()


def test_reduction_keeps_period_text():
    r = one("가 진단비", "보험기간 중 가로 진단 확정된 경우\n※ 최초 보험가입후 180일 미만에 보험금 지급사유가 발생한 경우 "
                      "가입금액의 10% 지급, 1년미만(180일미만 제외)에 보험금 지급사유가 발생한 경우 가입금액의 50% 지급")
    assert r.steps == (Step(6, 0.1, "180일 미만"), Step(12, 0.5, "1년 미만"))


def test_reduction_only_for_one_cause_goes_to_exception():
    note = "※ 최초 보험가입후 1년 미만에 질병으로 인한 보험금 지급사유가 발생한 경우 50% 감액 지급"
    r = one("가 등록보장", "보험기간 중 상해 또는 질병으로 가 대상으로 등록된 경우(연간1회한 지급)\n" + note)
    assert r.sure and [(s.months, s.rate) for s in r.steps] == [(12, 0.5)]
    assert r.exception == note[1:].strip() and r.limit == "연간1회한 지급"


def test_reduction_by_target_splits_lines():
    reason = ("보험기간 중 가질환, 나질환, 다질환으로 수술을 받은 경우 가입금액 지급(수술 1회당)\n"
              "※ 가질환 및 나질환은 최초 보험가입후 180일 미만에 보험금 지급사유가 발생한 경우 가입금액의 10% 지급, "
              "1년 미만(180일미만 제외)에 보험금 지급사유가 발생한 경우 가입금액의 50% 지급\n"
              "※ 다질환의 경우 1년 미만에 보험금 지급사유가 발생한 경우 가입금액의 50% 지급")
    a, b = read_cover("3대질환 수술비(1년감액)", reason, "가입금액")
    assert (a.target, [(s.months, s.rate) for s in a.steps]) == ("가질환·나질환", [(6, 0.1), (12, 0.5)])
    assert (b.target, [(s.months, s.rate) for s in b.steps]) == ("다질환", [(12, 0.5)])
    assert a.label == "3대질환 수술비(1년감액)(가질환·나질환)" and a.sure and b.sure
    assert a.limit == b.limit == "수술 1회당"


@pytest.mark.parametrize("note", [
    # 감액을 따지는 기준이 지급사유 발생 시점이 아니라 진단 시점이다
    "※ 최초 보험가입후 1년 미만에 가로 진단 확정되고 보험금 지급기간 중 보험금 지급사유가 발생한 경우 50% 감액 지급",
    "※ 최초 보험가입후 1년 미만에 가, 나 또는 다로 진단 확정되고 가 보험금 지급기간 중 보험금 지급사유 발생시 50% 감액 지급",
    "※ 최초 보험가입후 1년미만에 보험금 지급사유가 발생한 경우 50% 감액 지급(최초 입원일 기준)",
    "※ 갱신계약은 최초 보험가입후 1년 미만에 보험금 지급사유가 발생한 경우 50% 감액 지급",
])
def test_reduction_with_extra_condition_is_doubted_but_read(note):
    r = one("가 치료비", "보험기간 중 가로 치료를 받은 경우(연간 1회한)\n" + note)
    assert [(s.months, s.rate) for s in r.steps] == [(12, 0.5)]
    assert kinds(r) & {rules.D_CUT_ODD, rules.D_SPLIT}


@pytest.mark.parametrize("note", [
    "※ 가입 초기에는 보험금을 감액하여 지급함",
    "※ 최초 보험가입후 2년 이내에 보험금 지급사유가 발생한 경우 보험금의 절반을 지급",
    "※ 최초 보험가입후 100일 미만에 보험금 지급사유가 발생한 경우 50% 감액 지급",       # 개월로 딱 떨어지지 않는다
    "※ 최초 보험가입후 1년 미만에 보험금 지급사유가 발생한 경우 60% 감액 지급(50%지급)",   # 두 숫자가 맞지 않는다
])
def test_unreadable_reduction_is_doubted(note):
    r = one("가 치료비", "보험기간 중 가로 치료를 받은 경우\n" + note)
    assert kinds(r) & {rules.D_CUT, rules.D_UNREAD}


# ---------------------------------------------------------------------------
# 면책
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("note, days", [
    (START90, 90),
    ("※ 「가(급여)」의 보장개시일은 최초 계약일 또는 부활(효력회 복)일부터 90일 이 지난날의 다음날임", 90),     # 낱말 가운데 빈칸이 끼었다
    ("※ 이 특별약관의 보장개시일은 최초계약일 또는 부활(효력회복)일부터 90일이 지난날의 다음날임", 90),
    ("※ 가 진단비의 보장개시일은 최초 계약일 또는 부활(효력회복)일로부터 30일이 지난 날의 다음날임", 30),
    ("※ 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 1년이 지난날의 다음날임.", 365),
    ("※ 가의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 5년이 지난 날의 다음날임", 1825),
    ("※ 가의 보장개시일은 계약일임", 0),
    ("※ 가, 나 또는 다의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 10일이 지난 날의 다음날임", 10),
])
def test_waiting_days(note, days):
    r = one("가 진단비", "보장개시일 이후 가로 진단 확정된 경우\n" + note)
    assert r.sure, r.doubts
    assert r.waiting_days == days and r.evidence["면책"] == note[1:].strip()


def test_no_start_sentence_means_no_waiting():
    r = one("가 사망", "가 사고로 사망한 경우")
    assert r.sure and r.waiting_days == 0 and r.limit == "" and "면책" not in r.evidence


def test_waiting_by_target_splits_lines():
    reason = ("보장개시일 이후 가암, 나암 또는 다암으로 수술을 받은 경우(수술 1회당 지급)\n"
              "※ 가암의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난 날의 다음날이며, 나암, 다암의 보장개시일은 계약일임\n"
              + CUT_1Y)
    a, b = read_cover("암 수술비", reason, "가입금액")
    assert (a.label, a.waiting_days) == ("암 수술비(가암)", 90)
    assert (b.label, b.waiting_days) == ("암 수술비(나암·다암)", 0)
    assert a.sure and b.sure
    assert a.steps == b.steps == (Step(12, 0.5, "1년 미만"),)       # 대상을 가리지 않는 감액은 두 줄 모두에 붙는다


def test_waiting_in_two_sentences_splits_lines():
    reason = ("보장개시일 이후 가암 또는 가제자리암으로 수술을 받은 경우(최초 1회한)\n" + START90.replace("가의", "가암의")
              + "\n※ 가제자리암의 보장개시일은 계약일임")
    a, b = read_cover("가 수술비", reason, "가입금액")
    assert [(a.target, a.waiting_days), (b.target, b.waiting_days)] == [("가암", 90), ("가제자리암", 0)]


def test_amount_exception_follows_the_waiting_targets():
    reason = ("보장개시일 이후 가암, 나암 또는 다암으로 치료를 받은 경우(각각 연간 1회한 지급)\n"
              "※ 가암의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난 날의 다음날이며, 나암 및 다암의 보장개시일은 계약일임")
    a, b = read_cover("가 치료비", reason, "가입금액\n※ 단, 나암, 다암은 가입금액의 20%")
    assert (a.target, a.waiting_days, a.percent) == ("가암", 90, 100)
    assert (b.target, b.waiting_days, b.percent) == ("나암·다암", 0, 20)
    assert a.sure and b.sure


def test_injury_exception_splits_into_disease_and_injury():
    reason = ("보장개시일 이후 상해 및 질병으로 「가」로 진단 확정된 경우(최초 1회한 지급)\n"
              "※ 「가」의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난 날의 다음날임"
              "(단, 상해로 인해 「가」로 진단 확정된 경우 보험계약일을 보장개시일(책임개시일)로 함)\n"
              "※ 최초 보험가입후 1년 미만에 질병으로 인한 보험금 지급사유가 발생한 경우 50% 감액 지급")
    a, b = read_cover("가 진단비(1년50%)", reason, "가입금액의 60%")
    assert (a.target, a.waiting_days, a.percent, [(s.months, s.rate) for s in a.steps]) == ("질병", 90, 60, [(12, 0.5)])
    assert (b.target, b.waiting_days, b.percent, b.steps) == ("상해", 0, 60, ())      # 질병에만 걸리는 감액은 상해 줄에 붙지 않는다
    assert a.sure and b.sure and not a.exception


@pytest.mark.parametrize("note", [
    "※ 「두 번째 가」의 보장개시일은 「첫 번째 가」의 진단확정일부터 그날을 포함하여 1년이 지난날의 다음날임",
    "※ 재진단 가의 보장개시일\n1. 첫 번째 : 최초 진단확정일부터 1년이 지난 날의 다음날임",
    "※ 가의 보장개시일은 약관에서 정한 날임",
])
def test_unreadable_start_is_doubted(note):
    r = one("가 진단비", "보장개시일 이후 가로 진단 확정된 경우\n" + note)
    assert rules.D_WAIT in r.doubts and r.waiting_days == 0
    assert note[1:].strip().split("\n")[0] in r.evidence["읽지 못한 보장개시일 문장"]


def test_start_mentioned_without_definition_is_doubted():
    r = one("가 진단비", "보장개시일 이후 가로 진단 확정된 경우(최초 1회한)")
    assert kinds(r) == {rules.D_WAIT} and r.waiting_days == 0


def test_start_for_cancer_only_while_body_covers_similar_cancers():
    r = one("암 치료비", "보장개시일 이후 암, 기타피부암 또는 갑상선암으로 치료를 받은 경우\n"
                      "※ 암의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난 날의 다음날임")
    assert kinds(r) == {rules.D_WAIT}
    ok = one("암 치료비", "보장개시일 이후 암(기타피부암 및 갑상선암 제외)으로 치료를 받은 경우\n"
                       "※ 암의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난 날의 다음날임")
    assert ok.sure and ok.waiting_days == 90


def test_targets_that_do_not_line_up_stay_on_one_line():
    reason = ("보장개시일 이후 가, 나, 다로 등록된 경우(각각 최초 1회한 지급)\n"
              "※ 최초 보험가입후 1년미만에 다로 보험금 지급사유가 발생한 경우 50% 감액 지급\n"
              "※ 가에 대한 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난날의 다음날이며, "
              "나 및 다에 대한 보장개시일은 보험계약일 또는 부활(효력회복)일임")
    r = one("가 진단비", reason, "- 다 : 가입금액의 20%\n- 다 외 : 가입금액의 100%")
    assert rules.D_SPLIT in r.doubts
    assert (r.waiting_days, r.percent) == (90, 100)                 # 가장 긴 면책, 가장 큰 지급률
    assert "다 : 가입금액의 20%" in r.note and "다로 보험금 지급사유" in r.exception


# ---------------------------------------------------------------------------
# 지급 한도
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reason, limit", [
    ("가로 진단 확정된 경우 (최초 1회한 지급)", "최초 1회한 지급"),
    ("가로 진단 확정된 경우 가입금액 지급(연간 1회한)", "연간 1회한"),
    ("가로 입원한 경우 (90일을 한도로 1일째 입원일부터 입원 1일당 일당 지급)", "90일을 한도로 1일째 입원일부터 입원 1일당 일당 지급"),
    ("가(급여)로 치료를 받은 경우 1일 1회, 연간 3회에 한하여 가입금액 지급", "1일 1회, 연간 3회에 한하여"),
    ("가로 통원한 경우 통원1회당 가입금액 지급(1일 1회한, 연간 10회한 지급)", "통원1회당 / 1일 1회한, 연간 10회한 지급"),
    ("가로 181일이상 입원한 경우 181일째 입원일로부터 가입금액 지급(지급일수는 185일 한도)", "181일째 입원일로부터 / 지급일수는 185일 한도"),
    ("가(요양병원 제외)로 수술을 받은 경우\n※ 1회의 입원당 1회의 「수술」에 한하여 보장", "1회의 입원당 1회의 「수술」에 한하여 보장"),
    ("가로 치료를 받은 경우(연간 1회한)\n※ 연간 총 지급액은 1억원을 한도로 함", "연간 1회한 / 연간 총 지급액은 1억원을 한도로 함"),
    ("가로 수술을 받은 경우(수술 1회당)\n※ 단, 같은 수술을 2회 이상 받은 경우에는 하나의 수술비만 지 급",
     "수술 1회당 / 단, 같은 수술을 2회 이상 받은 경우에는 하나의 수술비만 지 급"),
    ("가로 치료를 받은 경우 가입금액 지급 가 치료와 나 치료는 각각 연간 1회한으로 지급함 가 치료는 다를 말함",
     "가 치료와 나 치료는 각각 연간 1회한으로 지급함"),
])
def test_limits(reason, limit):
    r = one("가 보장", reason)
    assert r.sure, r.doubts
    assert r.limit == limit and r.evidence["한도"] == limit


def test_plain_notes_do_not_touch_values():
    r = one("가 수술비", "보험기간 중 가로 수술을 받은 경우(수술 1회당 지급)\n※ 가는 나, 다 및 라임\n※「당일입원」이라 함은 같은 날 퇴원한 입원을 말함\n"
                      "※ 마의 절제술은 보험금 지급사유에서 제외됨\n· 바: 사, 아\n※ 세부내용은 약관 참조")
    assert r.sure and r.limit == "수술 1회당 지급" and r.note == ""


def test_unknown_note_is_doubted_and_kept():
    r = one("가 수술비", "가 사고로 수술을 받은 경우\n※ 안면부 1cm당 3만원 지급", "500만원 한도")
    assert kinds(r) == {rules.D_AMOUNT, rules.D_UNREAD}
    assert r.note == "500만원 한도 / 안면부 1cm당 3만원 지급"


@pytest.mark.parametrize("reason", [
    "가로 치료를 받은 경우 각 치료행위별로 각각의 지급방식에 따라 약관에서 정한 금액을 지급",
    "가로 진단 확정된 경우 6개월 경과시점부터 2년간 매월 가입금액 지급(최초 1회한)",
    "가로 입원한 경우 가입금액을 질병 입원일당으로 지급 간병인을 지원받기를 원할 경우 간병인을 지원하며 입원일당은 지급하지 않음(합계는 180일 한도)",
])
def test_other_payment_basis_in_reason_is_doubted(reason):
    r = one("가 치료비", reason)
    assert kinds(r) == {rules.D_BASIS} and r.percent == 100 and r.note


def test_bundle_of_covers_in_one_line_is_doubted():
    r = one("가 1~2종 수술비", "이 보장은 가 수술비(1종)(동일사고당1회한) 및 가 수술비(2종)(동일사고당1회한) 총 2개 세부보장으로 구성되어 있음 "
                           "보험기간 중 1~2종 수술을 받은 경우 가입금액 지급(동일사고당 1회한)", "해당 세부보장의 가입금액")
    assert kinds(r) == {rules.D_BUNDLE}
    assert r.limit == "동일사고당 1회한" and r.note == "총 2개 세부보장으로 구성되어 있음"


@pytest.mark.parametrize("name, reason", [
    ("가 진단비(1년50%)", "보험기간 중 가로 진단 확정된 경우"),
    ("가 진단비(1년감액)", "보험기간 중 가로 진단 확정된 경우"),
    ("가 진단비(90일50%)", "보험기간 중 가로 진단 확정된 경우\n" + CUT_1Y),
    ("가(30일면책) 진단비", "보장개시일 이후 가로 진단 확정된 경우\n" + START90),
])
def test_name_marks_must_agree_with_values(name, reason):
    assert kinds(one(name, reason)) == {rules.D_NAME}


def test_name_marks_that_agree():
    r = one("가(90일면책) 진단비(1년50%)", "보장개시일 이후 가로 진단 확정된 경우 (최초 1회한 지급)\n" + START90 + "\n" + CUT_1Y)
    assert r.sure and (r.waiting_days, r.steps[0].months, r.steps[0].rate) == (90, 12, 0.5)


def test_body_broken_before_a_middle_dot_is_joined():
    r = one("통합 가 진단비", "보장개시일 이후 「통합 가(나\n·다 및 라)」로 진단확정된 경우 (최초 1회한)\n"
                         "※ 「통합 가(나·다 및 라)」의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난날의 다음날임")
    assert r.sure and r.waiting_days == 90 and r.limit == "최초 1회한"


# ---------------------------------------------------------------------------
# 시트 행
# ---------------------------------------------------------------------------

def rider(title, covers, label="선택계약", page=10):
    return Rider(title, tuple(Cover(n, r, a, page + i) for i, (n, r, a) in enumerate(covers)), page, page + len(covers) - 1, label)


RIDERS = [
    rider("가 사망", [("가 사망", "가 사고로 사망한 경우", "가입금액")], label="기본계약"),
    rider("가 사망", [("가 사망", "가 사고로 사망한 경우", "가입금액")]),
    rider("[갱신형][간편]나 진단비(1년50%)", [
        ("나 진단비(1년50%)", "보장개시일 이후 나로 진단 확정된 경우 (최초 1회한 지급)\n" + START90.replace("가의", "나의") + "\n" + CUT_1Y, "가입금액"),
        ("나 치료비 지원", "보장개시일 이후 나암 또는 다암으로 치료를 받은 경우(연간 1회한)\n"
         "※ 나암의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난 날의 다음날이며, 다암의 보장개시일은 계약일임", "가입금액의 20%"),
    ], page=20),
    rider("다 치료비(연간1회한), 다 치료비(연간1회한)(기가입자용)",
          [("다 치료비(연간1회한), 다 치료비(연간1회한)(기가입자용)", "다로 치료를 받은 경우(연간 1회한)", "가입금액")], page=30),
    rider("라 배상책임", [("라 배상책임", "라 사고로 배상책임을 진 경우", "대인, 대물 각 1억원 한도")], page=40),
    rider("(체증형)마 일당", [("(체증형)마 일당", "마로 입원한 경우(180일을 한도로 입원1일당 일당지급)", "가입금액을 매5년마다 10%씩 정액 할증한 금액")], page=50),
    rider("바 등록보장(1년50%)", [("바 등록보장(1년50%)", "상해 또는 질병으로 바에 등록된 경우(연간1회한 지급)\n"
                                              "※ 최초 보험가입후 1년 미만에 질병으로 인한 보험금 지급사유가 발생한 경우 50% 감액 지급", "가입금액")], page=60),
]


def test_rows_pass_the_format_check():
    out = build_rows("V1", RIDERS, renewal_years=20)
    assert check_rows("sys_특약", out.riders) == {}
    assert check_rows("sys_급부", out.benefits) == {}
    assert len(out.riders) == 8 and len(out.benefits) == 10        # 이름이 둘인 조각은 특약 둘, 대상별로 나눈 세부보장은 급부 둘


def test_rider_rows():
    out = build_rows("V1", RIDERS, renewal_years=20)
    by_name = {}
    for r in out.riders:
        by_name.setdefault(r["원시특약명"], []).append(r)
    main, extra = by_name["가 사망"]
    assert (main["담보구분"], extra["담보구분"]) == ("주계약", "선택특약")
    assert main["특약ID"] != extra["특약ID"]                         # 같은 이름이 기본계약과 선택계약에 있어도 ID가 갈린다
    renewal = by_name["[갱신형][간편]나 진단비(1년50%)"][0]
    assert (renewal["갱신여부"], renewal["갱신주기년"]) == (True, 20)
    assert (main["갱신여부"], main["갱신주기년"]) == (False, None)
    assert set(by_name) >= {"다 치료비(연간1회한)", "다 치료비(연간1회한)(기가입자용)"}
    assert all(r["종형ID"] == "V1" for r in out.riders)


def test_renewal_years_must_be_given_for_renewal_riders():
    out = build_rows("V1", RIDERS, renewal_years=None)
    problems = check_rows("sys_특약", out.riders)
    assert len(problems) == 1 and "갱신주기년" in next(iter(problems.values()))[0]


def test_benefit_rows():
    out = build_rows("V1", RIDERS, renewal_years=20)
    rows = {r["원시급부명"]: r for r in out.benefits if r["특약ID"] != out.riders[1]["특약ID"]}
    plain = rows["가 사망"]
    assert (plain["급부역할"], plain["기준가입금액만원"], plain["기준지급금액만원"], plain["면책기간일수"]) == ("주급부", 100, 100, 0)
    assert (plain["지급횟수제한"], plain["감액개월1"], plain["감액예외"], plain["근거문서종류"], plain["근거문서쪽수"]) == (None, None, None, "요약서", 10)

    cut = rows["나 진단비(1년50%)"]
    assert (cut["급부역할"], cut["면책기간일수"], cut["감액개월1"], cut["감액지급률1"], cut["감액개월2"]) == ("대등복합", 90, 12, 0.5, None)
    assert (cut["지급횟수제한"], cut["근거문서쪽수"]) == ("최초 1회한 지급", 20)

    a, b = rows["나 치료비 지원(나암)"], rows["나 치료비 지원(다암)"]
    assert (a["기준지급금액만원"], a["면책기간일수"], b["기준지급금액만원"], b["면책기간일수"]) == (20, 90, 20, 0)
    assert a["급부ID"] != b["급부ID"] and a["근거문서쪽수"] == b["근거문서쪽수"] == 21

    assert rows["다 치료비(연간1회한)"]["특약ID"] != rows["다 치료비(연간1회한)(기가입자용)"]["특약ID"]

    odd = rows["라 배상책임"]
    assert (odd["기준지급금액만원"], odd["지급횟수제한"]) == (100, "대인, 대물 각 1억원 한도")
    assert out.doubts[odd["급부ID"]] == (rules.D_AMOUNT,)

    growing = rows["(체증형)마 일당"]
    assert growing["기준지급금액만원"] == 100
    assert growing["지급횟수제한"] == "180일을 한도로 입원1일당 일당지급 / 가입금액을 매5년마다 10%씩 정액 할증한 금액"

    cause = rows["바 등록보장(1년50%)"]
    assert (cause["감액개월1"], cause["감액지급률1"]) == (12, 0.5)
    assert cause["감액예외"] == "최초 보험가입후 1년 미만에 질병으로 인한 보험금 지급사유가 발생한 경우 50% 감액 지급"

    assert set(out.doubts) == {odd["급부ID"]}                       # 나머지 줄은 규칙이 확신한다
    assert set(out.readings) == {r["급부ID"] for r in out.benefits}
    assert out.readings[cut["급부ID"]].evidence["감액"].startswith("최초 보험가입후 1년 미만")


def test_id_name_separates_repeated_rider_names():
    taken: set[str] = set()
    assert rules.id_name("가 사망", "기본계약", taken) == "가 사망"
    assert rules.id_name("가 사망", "선택계약", taken) == "가 사망(선택계약)"
    assert rules.id_name("가 사망", "선택계약", taken) == "가 사망(선택계약 2)"
    assert rules.id_name("나 사망", "선택계약", taken) == "나 사망"
