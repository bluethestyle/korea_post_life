from postlife.validate import ALLOWED, check_row, check_rows
from postlife.schema import TABS


def benefit(**over):
    row = {
        "급부ID": "B1", "특약ID": "T1", "원시급부명": "암진단보험금", "급부역할": "주급부",
        "기준가입금액만원": 1000.0, "기준지급금액만원": 1000.0, "면책기간일수": 90,
        "감액개월1": 12, "감액지급률1": 0.5, "근거문서종류": "요약서", "근거문서쪽수": 3,
    }
    row.update(over)
    return row


def test_allowed_values_point_to_real_columns():
    for tab, column in ALLOWED:
        assert column in TABS[tab].header


def test_good_row_passes():
    problems = check_row("sys_급부", benefit())
    assert problems == [], problems


def test_code_catches_what_needs_no_model():
    assert any("감액지급률1" in p for p in check_row("sys_급부", benefit(감액지급률1=50)))
    assert any("함께" in p for p in check_row("sys_급부", benefit(감액지급률1=None)))
    assert any("허용값" in p for p in check_row("sys_급부", benefit(급부역할="주")))
    assert any("필수" in p for p in check_row("sys_급부", benefit(원시급부명="")))
    age = {"조건행ID": "C", "종형ID": "V", "보험기간구분": "20년", "납입기간구분": "전기납",
           "최저가입나이": 70, "최고가입나이": 15}
    assert any("최저가입나이" in p for p in check_row("sys_가입조건", age))


def test_duplicate_keys_reported():
    out = check_rows("sys_급부", [benefit(), benefit()])
    assert "기본키 중복" in out["B1"]


def variant(**over):
    row = {
        "종형ID": "V", "개정판ID": "P_2606", "모상품ID": "P", "종형계보키": "K", "기관코드": "EPOST",
        "공시상품코드": "P500130", "공시상품명": "상품", "종형명": "간편 325", "비교역할구분": "정밀비교",
        "심사유형": "간편심사", "간편고지약칭": "325", "고지최근소견개월": 3, "고지입원수술년수": 2,
        "고지중대질병년수": 5, "고지수술포함여부": False, "고지중대질병수": 6, "갱신유형": "갱신", "갱신주기년": 20, "환급유형": "순수보장형",
        "납입면제적용": False, "적용시작일": "2026-06-01", "공시목록URL": "https://example.kr",
        "요약서해시": "abc",
    }
    row.update(over)
    return row


def test_precise_comparison_variant_needs_refund_type_and_hash():
    assert check_row("sys_상품종형", variant()) == []
    for name in ("환급유형", "납입면제적용", "요약서해시"):
        assert any(name in p for p in check_row("sys_상품종형", variant(**{name: None}))), name
    # 관문 표시에만 쓰는 종형은 비워도 된다
    assert check_row("sys_상품종형", variant(비교역할구분="관문전용", 환급유형=None, 요약서해시=None)) == []


def test_disease_code_order_understands_subcodes():
    row = {"질병군코드행ID": "R", "질병군ID": "G", "질병군명": "뇌경색", "KCD버전": "KCD-9",
           "시작코드": "I63.0", "끝코드": "I63"}
    assert check_row("hum_표준질병군", row) == []
    assert any("앞섬" in p for p in check_row("hum_표준질병군", {**row, "시작코드": "I64"}))
