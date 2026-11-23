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


def test_disclosure_scope_columns():
    six = "암, 협심증, 심근경색, 심장판막증, 간경화증, 뇌졸중증"
    assert check_row("sys_상품종형", variant(고지중대질병목록=six, 고지소견범위="서면")) == []
    assert check_row("sys_상품종형", variant(고지중대질병목록=six, 고지소견범위="서면과 진료기록부")) == []
    assert any("허용값" in p for p in check_row("sys_상품종형", variant(고지소견범위="진료기록부")))
    # 목록과 수가 둘 다 있으면 개수가 같아야 한다. 하나만 있으면 견주지 않는다
    assert any("고지중대질병수(6)" in p for p in check_row("sys_상품종형", variant(고지중대질병목록="암, 협심증")))
    assert check_row("sys_상품종형", variant(고지중대질병목록="암, 협심증", 고지중대질병수=None)) == []
    assert check_row("sys_상품종형", variant(고지중대질병목록=None)) == []
    assert any("빈 항목" in p for p in check_row("sys_상품종형", variant(고지중대질병목록="암, , 협심증, 심근경색, 심장판막증, 간경화증")))


def test_disease_code_order_understands_subcodes():
    row = {"질병군코드행ID": "R", "질병군ID": "G", "질병군명": "뇌경색", "KCD버전": "KCD-9",
           "시작코드": "I63.0", "끝코드": "I63"}
    assert check_row("hum_표준질병군", row) == []
    assert any("앞섬" in p for p in check_row("hum_표준질병군", {**row, "시작코드": "I64"}))


def test_amounts_that_could_not_be_read_do_not_pass():
    assert any("기준가입금액만원" in p for p in check_row("sys_급부", benefit(기준가입금액만원=0.0)))
    assert any("기준지급금액만원" in p for p in check_row("sys_급부", benefit(기준지급금액만원=0)))
    assert check_row("sys_급부", benefit(기준가입금액만원=0.5, 기준지급금액만원=0.05)) == []


def no_amount(basis="차등지급", **over):
    """금액 하나로 담기지 않는 꼴의 급부. 두 금액과 감액을 비운다."""
    row = benefit(지급기준구분=basis, 지급횟수제한="최초 1회", 면책기간일수=90)
    for name in ("기준가입금액만원", "기준지급금액만원", "감액개월1", "감액지급률1"):
        row[name] = None
    row.update(over)
    return row


def test_four_no_amount_bases_are_allowed():
    from postlife.validate import NO_AMOUNT_BASES
    assert set(NO_AMOUNT_BASES) == {"차등지급", "실손보상", "분할지급", "현물급부"}
    assert set(NO_AMOUNT_BASES) < ALLOWED[("sys_급부", "지급기준구분")]
    for basis in NO_AMOUNT_BASES:
        assert check_row("sys_급부", no_amount(basis)) == [], basis
    # 판독 도구의 세부 사유는 허용 값이 아니다
    assert any("허용값" in p for p in check_row("sys_급부", no_amount("경과기간별지급률")))
    assert any("허용값" in p for p in check_row("sys_급부", no_amount("그밖")))


def test_no_amount_rows_must_leave_amounts_and_cuts_empty():
    p = check_row("sys_급부", no_amount(기준가입금액만원=100.0, 기준지급금액만원=100.0))
    assert "지급기준구분이 차등지급인데 기준가입금액만원이 있음" in p
    assert "지급기준구분이 차등지급인데 기준지급금액만원이 있음" in p
    assert check_row("sys_급부", no_amount("실손보상", 감액개월1=12, 감액지급률1=0.5)) == ["지급기준구분이 실손보상인데 감액이 있음"]
    assert check_row("sys_급부", no_amount(감액예외="재해는 감액 없음")) == ["지급기준구분이 차등지급인데 감액이 있음"]
    assert check_row("sys_급부", no_amount(감액개월2=24, 감액지급률2=0.5)) == ["지급기준구분이 차등지급인데 감액이 있음"]
    # 면책, 한도, 근거 쪽은 읽은 대로 채운다
    assert check_row("sys_급부", no_amount(면책기간일수=0, 지급횟수제한=None, 근거문서쪽수=None)) == []
    assert any("필수" in p for p in check_row("sys_급부", no_amount(면책기간일수=None)))


def test_amount_rows_still_need_both_amounts():
    for basis in (None, "", "금액", "가입금액비율"):
        for name in ("기준가입금액만원", "기준지급금액만원"):
            row = benefit(지급기준구분=basis, **{name: None})
            label = basis or "금액"
            assert f"지급기준구분이 {label}인데 {name}이 비어 있음" in check_row("sys_급부", row), (basis, name)
    row = benefit()
    row.pop("기준지급금액만원")          # 지급기준구분 열도 금액 열도 없는 행
    assert check_row("sys_급부", row) == ["지급기준구분이 금액인데 기준지급금액만원이 비어 있음"]
    ratio = benefit(지급기준구분="가입금액비율", 기준가입금액만원=100.0, 기준지급금액만원=20.0)
    assert check_row("sys_급부", ratio) == []
