"""삼성생명, KB라이프생명 판정에서 값이 맞는데 기계 검사가 원문 구절을 찾지 못해 행이 되지 않던 꼴.

한도 앞말과 숫자 사이의 "사용일수", "N년(N회) 최고한도", 면책근거쪽의 "이 계약의 …보장개시일은", "동일한 보험금"과 "삭감"으로
적힌 감액예외, 다음 줄로 넘어간 "원" 없는 금액, 세부보장명에만 있는 지급단위, 주석의 "동일한 사고 … 1회에 한하여",
약관 쪽을 가리키는 지급단위근거, 견줌 도구의 조각지문. 문구, 이름, 금액은 모두 지어낸 것이다(공시 문서의 문장이 아니다).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import compare_readers  # noqa: E402
import load_reader_product as L  # noqa: E402
from postlife.disclosure import sources  # noqa: E402
from postlife.extract import reader_rows as RR  # noqa: E402


def view(reason, amount="1만원", name="가나 간병급여금", number="R001-1"):
    return RR.CoverView(number, name, reason, amount, 10)


def piece_of(cover, notes=(), title="가나특약"):
    return RR.PieceView(1, title, (title,), "선택특약", "", 10, 10, (cover,), tuple(notes))


def reading(**values):
    return {**RR.DEFAULTS, "번호": "R001-1", "쪽": 10, "꼴": RR.AMOUNT, "기준가입금액만원": 1, "지급액만원": 1, **values}


STAY = {"앞말": "1회입원당", "수": 95, "단위": "일"}


def test_stay_limit_may_name_the_counted_days_between_lead_and_number():
    for text, cut in (("가나 돌봄 하루 몫 (1회 입원당 사용일수 95일 한도)", "1회 입원당 사용일수 95일 한도"),
                      ("다라 이용 시 (1회 입원당 사용일수는95일한도)", "1회 입원당 사용일수는95일한도"),
                      ("마바 입원 시 (1회 입원당 지급일수 95일 한도)", "1회 입원당 지급일수 95일 한도"),
                      ("사아 입원 시 (1회 입원당 95일 한도)", "1회 입원당 95일 한도")):
        assert RR.limit_phrase(STAY, view(text)) == cut, text
    # 수가 다르거나 앞말이 없으면 여전히 찾지 못한다
    assert RR.limit_phrase(STAY, view("가나 입원 시 (1회 입원당 사용일수 60일 한도)")) is None
    assert RR.limit_phrase(STAY, view("가나 돌봄 사용일수 95일 넘게 머문 때")) is None
    c = view("가나 돌봄 1일당 몫, 1회 입원당 사용일수 95일 한도", "1일당 1만원")
    assert RR.machine_checks(c, reading(지급단위="1일당", 한도=[STAY])) == ([], [])


def test_bare_limit_in_brackets_after_a_period_with_top_limit():
    bare = {"앞말": "없음", "수": 12, "단위": "회"}
    c = view("가나상태로 판정되고 매년 살아 있을 경우 (단, 12년(12회) 최고한도로 지급)", "매년 1만원 (최대 12년)")
    assert RR.limit_phrase(bare, c) == "12년(12회) 최고한도"
    assert RR.limit_phrase(bare, view("가나 진단 시 (12회 최고한도)")) == "12회 최고한도"
    # 한도를 뜻하는 말이 없거나 괄호 안 수가 다르면 걸리지 않는다
    assert RR.limit_phrase(bare, view("가나상태로 판정되고 12년(12회) 나누어 지급")) is None
    assert RR.limit_phrase(bare, view("가나상태로 판정되면 12년(10회) 최고한도로 지급")) is None


def test_wait_days_on_page_take_a_name_right_after_contract_or_rider_of():
    page = "3. 이 계약의 가나보장개시일은 가입일에서 90일이 흐른 뒤 첫 날이다."
    assert RR.wait_days_on_page("가나보장개시일", page) == {90}
    rider = "4. 이 특약의 가나보장개시일은 처음 가입이면 가입일에서 90일 뒤로 한다."
    assert RR.wait_days_on_page("가나보장개시일", rider) == {90}
    # 다른 이름의 꼬리("다라가나보장개시일")는 여전히 세지 않는다
    other = "3. 이 계약의 다라가나보장개시일은 가입일에서 90일이 흐른 뒤 첫 날이다."
    assert RR.wait_days_on_page("가나보장개시일", other) == set()
    c = RR.CoverView("R009-1", "가나 진단비", "가나보장개시일 이후 가나병으로 진단 확정된 경우", "1,000만원", 3)
    v = reading(면책일수=90, 보장개시일="가나보장개시일", 면책근거쪽=8, 기준가입금액만원=1000, 지급액만원=1000)
    assert RR.machine_checks(c, v, None, {8: page})[0] == []
    assert RR.machine_checks(c, {**v, "면책일수": 30}, None, {8: page})[0] != []


def test_exception_sentences_written_as_same_payment_or_cut_word():
    same = "가나병으로 수술 시\n※ 단, 가입 첫해라도 재해가 원인이면 둘째 해와 동일한 보험금을 지급"
    c = view(same, "1년이내: 5만원\n1년초과: 10만원", name="가나 수술보험금")
    v = reading(기준가입금액만원=10, 지급액만원=10, 감액=[{"기간": 1, "단위": "년", "값": 5, "값기준": "만원"}],
                감액예외=[{"대상": "재해", "자리": "지급사유"}])
    cell, missing = RR.exception_cell(v, c, None)
    assert missing == [] and "동일한 보험금을 지급" in cell
    cut = view("가나병으로 머물 때\n※ 단, 재해는 첫해에도 삭감하지 않음", "1만원")
    assert RR.exception_cell(reading(감액예외=[{"대상": "재해", "자리": "지급사유"}]), cut, None)[1] == []
    # 대상 낱말만 있고 감액하지 않는다는 말이 없는 문장은 받지 않는다
    plain = view("가나병으로 머물 때\n※ 단, 재해가 원인이면 가나금을 줌", "1만원")
    assert RR.exception_cell(reading(감액예외=[{"대상": "재해", "자리": "지급사유"}]), plain, None)[1] == ["감액예외 재해"]


def test_bare_ten_thousand_amount_followed_by_the_next_line():
    c = view("가나 시술 때", "1년 안: 0.5만\n1년 뒤: 1만", name="가나 시술금")
    v = reading(감액=[{"기간": 1, "단위": "년", "값": 0.5, "값기준": "만원"}])
    assert RR.machine_checks(c, v)[0] == []
    # 같은 줄에서 숫자가 이어지면 여전히 금액으로 보지 않는다
    assert not RR._money_in(5, ["첫해: 5만 10회"])
    assert RR._money_in(5, ["첫해: 5만\n10회"])


def test_unit_written_only_in_the_benefit_name_and_same_accident_limit_in_a_note():
    name = "가나돌봄금[다라돌봄] 마바돌봄(사아센터) (사고 1회당)"
    c = view('재해로 "다라돌봄"을 받은 때', "1,000만원", name=name)
    note = "3. 「마바돌봄」은 동일한 재해사고로 여러 번 받은 그런 경우에도 1회에 한하여 준다."
    p = piece_of(c, (note,))
    accident = {"앞말": "1사고당", "수": 1, "단위": "회"}
    assert RR.unit_phrase("1사고당", c) == "사고 1회당"
    assert RR.limit_phrase(accident, c, p).endswith("1회에 한하여")
    v = reading(기준가입금액만원=1000, 지급액만원=1000, 지급단위="1사고당", 한도=[accident])
    assert RR.machine_checks(c, v, p) == ([], [])
    # 이름에 없고 주석에 다른 말이면 여전히 걸린다
    bare = view('재해로 "다라돌봄"을 받은 때', "1,000만원", name="가나돌봄금")
    other = piece_of(bare, ("3. 다라돌봄을 여러 번 받으면 한 번 몫만 준다.",))
    problems = RR.machine_checks(bare, v, other)[0]
    assert "구절없음: 지급단위 1사고당" in problems and "구절없음: 한도 1사고당 1회" in problems


TERMS = ("가나머묾(1일이상 95일한도) 특별약관\n제1조 [주는 때]\n가나 머묾금 가나병으로 머문 때 1일당\n"
         "가입금액 그대로\n(1회 입원당 95일까지)\n")
INNER = "큰병원가나머묾(1일이상 95일한도) 특별약관\n제1조 [주는 때]\n1일당 가입금액 그대로\n"
BEFORE = "1일당 가입금액 그대로\n(앞 특약 조항의 표)\n가나머묾(1일이상 95일한도) 특별약관\n제1조 …\n"


def stay_line(**extra):
    c = view("가나병으로 머문 때 (1회 입원당 95일 한도)", "보험가입금액",
             name="(간편)가나머묾(1일이상 95일한도)특약")
    p = piece_of(c, title="(간편)가나머묾(1일이상 95일한도)특약")
    v = reading(꼴=RR.RATIO, 지급률=100, 기준가입금액만원=None, 지급액만원=None, 지급단위="1일당", 한도=[STAY], **extra)
    return c, p, v


def test_unit_basis_on_a_terms_page_needs_the_rider_title_at_line_start():
    c, p, v = stay_line()
    assert "구절없음: 지급단위 1일당" in RR.machine_checks(c, v, p)[0]
    based = {**v, "지급단위근거": {"문서": "약관", "쪽": 7}}
    assert RR.check_format(based) == []
    assert RR.machine_checks(c, based, p, None, {"약관": {7: TERMS}})[0] == []
    assert RR.unit_basis(based, c, p, {"약관": {7: TERMS}}) == "1일당"
    # 다른 특약 이름 속의 이름, 제목 앞의 구절, 다른 쪽, 문서 없음은 받지 않는다
    for docs in ({"약관": {7: INNER}}, {"약관": {7: BEFORE}}, {"약관": {8: TERMS}}, None):
        problems = RR.machine_checks(c, based, p, None, docs)[0]
        assert any(x.startswith("구절없음: 지급단위 1일당") for x in problems), docs
    assert any("약관 7쪽" in x for x in RR.machine_checks(c, based, p, None, None)[0])
    for bad in ({"문서": "약관"}, {"문서": "설명서", "쪽": 7}, {"문서": "약관", "쪽": 0}, 7):
        assert RR.check_format({**v, "지급단위근거": bad}) != [], bad


def test_rows_from_a_terms_basis_carry_the_unit_phrase():
    c, p, v = stay_line(지급단위근거={"문서": "약관", "쪽": 7})
    built = RR.build_rows("V1", [p], {"R001-1": v}, None, {}, {"약관": {7: TERMS}})
    assert not built.skipped and built.benefits[0]["지급횟수제한"] == "1일당 / 1회 입원당 95일 한도"
    missing = RR.build_rows("V1", [p], {"R001-1": v}, None, {}, None)
    assert missing.skipped["R001-1"].startswith("기계 검사: 구절없음: 지급단위 1일당")
    # 값 파일의 판정값에서 읽어도 근거가 남는다
    stored = RR.stored_value(v)
    assert stored["지급단위근거"] == {"문서": "약관", "쪽": 7}
    line = {"번호": "R001-1", "쪽": 10, "판정": "수정", "판정값": stored}
    assert RR.final_readings([line], "sonnet", "opus")["R001-1"]["지급단위근거"] == {"문서": "약관", "쪽": 7}


def test_loader_reads_only_the_pointed_pages_of_the_terms(tmp_path, monkeypatch):
    index = [{"상품코드": "Z1", "문서": "상품요약서", "저장이름": "z_요약서"}, {"상품코드": "Z2", "문서": "약관", "저장이름": "z_약관"}]
    (tmp_path / "z_약관.pdf").write_bytes(b"%PDF-1.4 test")
    asked = []
    monkeypatch.setattr(L, "page_subset", lambda pdf, numbers: asked.append((pdf.name, sorted(numbers))) or
                        {n: f"쪽 {n}" for n in numbers})
    readings = {"R001-1": {"지급단위근거": {"문서": "약관", "쪽": 7}}, "R002-1": {"지급단위근거": {"문서": "약관", "쪽": 9}},
                "R003-1": {"지급단위근거": {"문서": "상품요약서", "쪽": 3}}, "R004-1": {}}
    pages, notes = L.basis_pages(index, ["Z1", "Z2"], readings, tmp_path)
    assert pages == {"약관": {7: "쪽 7", 9: "쪽 9"}} and notes == [] and asked == [("z_약관.pdf", [7, 9])]
    pages, notes = L.basis_pages(index, ["Z1"], readings, tmp_path)
    assert pages == {} and len(notes) == 1 and "약관" in notes[0]


def test_kblife_collects_terms_as_an_optional_document():
    src = sources.SOURCES["kblife"]
    assert src.kinds == ("사업방법서", "상품요약서") and src.optional == ("약관",)
    assert all(s.optional == () for k, s in sources.SOURCES.items() if k != "kblife")


BUNDLE_PIECES = {"형식": RR.PIECES_FORMAT, "출처": {"문서": "test"}, "조각": [
    {"특별약관": "가나특약", "구분": "선택계약", "적용범위": "", "첫쪽": 10, "끝쪽": 10, "형": "",
     "세부보장": [{"보장명": "가나 진단비", "지급사유": "가나병으로 진단확정시", "지급금액": "가입금액", "쪽": 10, "적용범위": ""}]}]}


def test_compare_writes_the_fingerprint_of_the_original_piece(tmp_path):
    bundle = {"형식": RR.BUNDLE_FORMAT, "묶음": "T_B01", "조각": [
        {"조각번호": "R001", "특약명": "가나특약", "구분": "선택계약", "형": "", "쪽": [10, 10], "주석": [],
         "세부보장": [{"번호": "R001-1", "세부보장명": "가나 진단비", "지급사유": "가나병으로 진단확정시", "지급금액": "가입금액",
                      "쪽": 10}]}]}
    answer = {"형식": RR.FORMAT, "묶음": "T_B01", "값": [{"번호": "R001-1", "쪽": 10, "꼴": RR.RATIO, "지급률": 100}]}
    for name in ("sonnet", "opus"):
        (tmp_path / f"T_B01.{name}.json").write_text(json.dumps({**answer, "판독자": name}, ensure_ascii=False))
    (tmp_path / "b.json").write_text(json.dumps(bundle, ensure_ascii=False))
    (tmp_path / "p.json").write_text(json.dumps(BUNDLE_PIECES, ensure_ascii=False))
    out = tmp_path / "v.jsonl"
    assert compare_readers.main([str(tmp_path / "b.json"), "--answers", str(tmp_path), "--readers", "sonnet", "opus",
                                 "--pieces", str(tmp_path / "p.json"), "--out", str(out)]) == 0
    line = json.loads(out.read_text().splitlines()[0])
    p, c = RR.covers_by_number(RR.load_pieces(BUNDLE_PIECES))["R001-1"]
    assert line["조각지문"] == RR.cover_fingerprint(p, c)
    assert list(line)[:5] == ["번호", "쪽", "특약명", "급부명", "조각지문"]
    # 조각 파일의 이름이 묶음과 다르면 값 파일을 쓰지 않는다
    other = json.loads(json.dumps(BUNDLE_PIECES))
    other["조각"][0]["세부보장"][0]["보장명"] = "다라 진단비"
    (tmp_path / "q.json").write_text(json.dumps(other, ensure_ascii=False))
    with pytest.raises(SystemExit):
        compare_readers.main([str(tmp_path / "b.json"), "--answers", str(tmp_path), "--readers", "sonnet", "opus",
                              "--pieces", str(tmp_path / "q.json"), "--out", str(tmp_path / "w.jsonl")])
    assert not (tmp_path / "w.jsonl").exists()
