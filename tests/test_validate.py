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
