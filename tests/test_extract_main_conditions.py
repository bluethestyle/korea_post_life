"""시트에 이미 있는 종형의 주계약 가입조건만 뽑는 부분(job.MAIN_PART. 삼성화재)과 기본계약 표 자르기(conditions.main_section).

시험 글은 삼성화재 사업방법서의 절과 항목 제목 모양, 가입나이 표가 글자로 풀린 모양("기본"과 "계약"이 두 줄로 갈리고, 다음 계약의
첫 줄이 그 계약 이름보다 먼저 나옴)만 본떠 직접 만든 것이다. 상품과 계약 이름, 나이와 기간은 지어낸 것이다.
모델은 부르지 않는다. 모델이 돌려줄 법한 답을 손으로 만들어 넣는다.
"""
from dataclasses import replace
from datetime import datetime

from postlife import ids
from postlife.extract import conditions as C
from postlife.extract import job
from postlife.extract import variants as VV
from postlife.extract.segment import pages_from_text
from postlife.gemini import Answer
from postlife.schema import TABS
from postlife.sheets_io import MemoryBackend, SheetStore
from postlife.site import sales as S
from postlife.site.model import Cond, Data
from postlife.snapshot import KST
from postlife.validate import check_rows

NOW = datetime(2026, 11, 23, 10, 0, tzinfo=KST)
ORG = "GANAFIRE"

# 모양 1: 가입나이 절이 고지유형("가. 간편고지", "나. 일반고지")으로 나뉘고, 그 안에 최초계약과 갱신계약 표가 따로 있다
RENEW = """
===== 2쪽 =====
3. 보험의 목적
가. 피보험자의 신체
4. 보험기간, 보험료 납입기간, 가입나이 및 보험료 납입주기
가. 간편고지
(1) 최초계약
보험 보험료 보험료
구 분 가입나이
기간 납입기간 납입주기
25년 전기납 만17세~66세
기본 18년 전기납 만17세~77세
·[갱신형][간편]가나 사망 월납
계약 12년 전기납 만17세~83세
6년 전기납 22세~88세
25년 전기납 만17세~44세
18년 전기납 만17세~55세
·[갱신형][간편]다라 사망(1년50%)
12년 전기납 만17세~61세
6년 전기납 22세~66세
선택
·[갱신형][간편]마바 진단비(1년50%) 월납
계약

===== 3쪽 =====
(2) 갱신계약
보험 보험료 갱신종 보험료
구 분 갱신나이
기간 납입기간 료나이 납입주기
25년 전기납 41세~66세
기본 18년 전기납 33세~77세
·[갱신형][간편]가나 사망 99세 월납
계약 12년 전기납 31세~83세
주1) 선택계약의 보험기간은 기본계약의 보험기간과 동일하게 함
나. 일반고지
(1) 최초계약
보험 보험료 보험료
구 분 가입나이
기간 납입기간 납입주기
25년 전기납 만17세~64세

===== 4쪽 =====
기본 18년 전기납 만17세~75세
·[갱신형]가나 사망 월납
계약 12년 전기납 만17세~81세
6년 전기납 22세~86세
25년 전기납 만17세~42세
·[갱신형]다라 사망(1년50%)
5. 의무가입에 관한 사항(1종에 한함)
가. 아래에 정한 특별약관을 의무가입해야 함
"""

# 모양 2: 가입나이 절이 종("가. 1종 및 9종", "라. 8종")으로 나뉘고, 납입기간 여러 줄이 가입나이 칸 하나를 함께 쓴다
MODULE = """
===== 7쪽 =====
4. 보험기간, 보험료 납입기간, 가입나이 및 보험료 납입주기
가. 1종 및 9종
01. 건강 모듈 보장
기본 100세만기 20년납 16세~41세 월납
·[건강]가나 사망
라. 8종
01. 건강 모듈 보장
보험 보험료 가입 보험료
구 분
기간 납입기간 나이 납입주기
7년납
12년납
16세~68세
기본 100세만기 17년납
·[건강]가나 사망 월납
계약 90세만기 22년납
27년납 16세~63세
7년납
12년납
16세~68세
·[건강]사아 후유장해(80%이상)
주1) 선택계약의 가입나이는 기본계약의 가입나이 이내로 함

===== 8쪽 =====
5. 의무가입에 관한 사항
- 해당 없음
"""

TARGETS = {"기관코드": ORG, "공시목록URL": "https://example.invalid/list", "상품": [
    {"모상품ID": "GANA_RENEW", "개정연월": "2607", "비교역할구분": "정밀비교", "갱신유형": "갱신", "갱신주기년": 18,
     "환급유형": "해약환급금 미지급형", "납입면제적용": False,
     "종형": [{"공시상품코드": "R7", "종형명": "7종(미지급형) 315·5", "심사유형": "간편심사", "간편고지약칭": "3.1.5"},
              {"공시상품코드": "R7", "종형명": "7종(미지급형) 355·5", "심사유형": "간편심사", "간편고지약칭": "3.5.5"},
              {"공시상품코드": "R8", "종형명": "8종(미지급형,일반고지)", "심사유형": "일반심사", "간편고지약칭": "일반"}]},
    {"모상품ID": "GANA_MODULE", "개정연월": "2610", "비교역할구분": "정밀비교", "갱신유형": "비갱신", "갱신주기년": None,
     "환급유형": "표준형", "납입면제적용": False,
     "종형": [{"공시상품코드": "M8", "종형명": "8종(일반형)", "심사유형": "일반심사", "간편고지약칭": "일반"}]}]}


def entries(code, name, method_hash, method_stem):
    doc = {"기관": ORG, "상품코드": code, "상품명": name, "판매시작일": "2026-07-01", "판매종료일": None, "쪽수": 9}
    return [dict(doc, 문서="상품요약서", 해시=f"y{code}", 저장이름=f"yoyak_{code}"),
            dict(doc, 문서="사업방법서", 해시=method_hash, 저장이름=method_stem)]


# 새로고침처럼 7종과 8종의 사업방법서는 같은 파일을 두 코드로 받는다(해시가 같다)
INDEX = (entries("R7", "가나 간편보험 7종", "hr", "saeop_R7") + entries("R8", "가나 간편보험 8종", "hr", "saeop_R8")
         + entries("M8", "가나 건강보험 8종", "hm", "saeop_M8"))
TEXTS = {"saeop_R7": RENEW, "saeop_R8": RENEW, "saeop_M8": MODULE}


def vid(code, name):
    return ids.variant_id(ORG, code, name)


S315, S355, R8, M8 = (vid("R7", "7종(미지급형) 315·5"), vid("R7", "7종(미지급형) 355·5"), vid("R8", "8종(미지급형,일반고지)"),
                      vid("M8", "8종(일반형)"))
# 급부 표에서 읽은 주계약 이름. 건강 모듈 상품은 사업방법서의 "[건강]" 표시 없이 읽혀 있다
MAIN_NAMES = {S315: "[갱신형][간편]가나 사망", S355: "[갱신형][간편]가나 사망", R8: "[갱신형]가나 사망", M8: "가나 사망"}


def rider(v, name, kind):
    years = 18 if v != M8 else None
    return {"특약ID": ids.rider_id(v, name), "종형ID": v, "특약계보키": ids.rider_lineage_key(name), "담보구분": kind,
            "원시특약명": name, "갱신여부": years is not None, "갱신주기년": years, "최소가입금액만원": None,
            "최대가입금액만원": None, "합산한도기준키": None}


def sheet_store():
    """급부를 표 규칙으로 적재해 둔 시트. 다른 회사의 가입조건 행과, 지난번에 쓴 이 회사의 낡은 가입조건 행이 하나 있다."""
    store = SheetStore(MemoryBackend())
    for name in TABS:
        store.write_tab(name, [])
    found, problems = VV.build(TARGETS, INDEX)
    assert problems == []
    riders = []
    for v in found:
        riders += [rider(v.id, MAIN_NAMES[v.id], "주계약"), rider(v.id, "다라 사망", "선택특약")]
    benefit = {"급부ID": ids.benefit_id(riders[0]["특약ID"], "사망보험금"), "특약ID": riders[0]["특약ID"], "원시급부명": "사망보험금",
               "급부역할": "주급부", "기준가입금액만원": 1000, "기준지급금액만원": 1000, "지급기준구분": None, "지급횟수제한": None,
               "면책기간일수": None, "감액개월1": None, "감액지급률1": None, "감액개월2": None, "감액지급률2": None,
               "감액예외": None, "근거문서종류": "상품요약서", "근거문서쪽수": 3}
    other = {"조건행ID": "EPOSTX_C1", "종형ID": "EPOSTX", "특약ID": None, "보험기간구분": "20년만기", "납입기간구분": "전기납",
             "성별": None, "최저가입나이": 15, "최고가입나이": 80, "구간최대가입금액만원": 4000}
    stale = {"조건행ID": f"{R8}_Cstale", "종형ID": R8, "특약ID": None, "보험기간구분": "18년", "납입기간구분": "전기납", "성별": None,
             "최저가입나이": 1, "최고가입나이": 2, "구간최대가입금액만원": None}
    store.write_tab("sys_상품종형", [v.row for v in found])
    store.write_tab("sys_특약", riders)
    store.write_tab("sys_급부", [benefit])
    store.write_tab("sys_가입조건", [other, stale])
    return store


def item(name, term, payment, age):
    return {"subjects": [name], "variant_scope": "", "contract": "구분없음", "sex": "구분없음", "age": age, "term": term,
            "payment": payment}


SIMPLE = [("25년", "만17세~66세"), ("18년", "만17세~77세"), ("12년", "만17세~83세"), ("6년", "22세~88세")]
GENERAL = [("25년", "만17세~64세"), ("18년", "만17세~75세"), ("12년", "만17세~81세"), ("6년", "22세~86세")]
HEALTH = ([(t, p, "16세~68세") for t in ("100세만기", "90세만기") for p in ("7년납", "12년납", "17년납", "22년납")]
          + [(t, "27년납", "16세~63세") for t in ("100세만기", "90세만기")])


class Fake:
    """프롬프트로 무엇을 묻는지 가려 답한다. 종류별 호출 수와 모델에 넣은 본문을 남긴다."""

    def __init__(self):
        self.calls = {"가입나이": 0, "가입한도": 0, "결합제약": 0, "급부": 0, "판정": 0}
        self.bodies = []

    def generate(self, model, prompt, schema=None, temperature=0.0):
        if '"가입나이, 보험기간' in prompt:
            kind = "가입나이"
        elif '"보험가입금액의 한도" 절' in prompt:
            kind = "가입한도"
        elif "특약을 부가하는 조건" in prompt:
            kind = "결합제약"
        else:
            kind = "급부"
        self.calls[kind] += 1
        body = prompt.rsplit("본문\n", 1)[1]
        self.bodies.append(body)
        if kind != "가입나이":
            return {"items": []}
        if "[건강]가나 사망" in body:
            return {"items": [item("[건강]가나 사망", t, p, a) for t, p, a in HEALTH]}
        if "[간편]가나 사망" in body:
            return {"items": [item("[갱신형][간편]가나 사망 월납", t, "전기납", a) for t, a in SIMPLE]}   # 이름에 납입주기가 붙어도 된다
        return {"items": [item("기본계약", t, "전기납", a) for t, a in GENERAL]}

    def decide(self, model, text, questions):
        self.calls["판정"] += 1
        return {k: Answer(True, None, {"true": 0.97, "false": 0.03}) for k in questions}


def pages(text):
    return pages_from_text(text)


# ---------- 기본계약 표 자르기 ----------
def test_main_section_keeps_only_the_main_rows_of_the_scoped_item():
    simple = C.main_section(pages(RENEW), "간편고지")
    assert (simple.first_page, simple.last_page) == (2, 2)
    lines = simple.text.split("\n")
    assert lines[0] == "보험 보험료 보험료" and lines[-1] == "6년 전기납 22세~88세"
    assert "·[갱신형][간편]가나 사망 월납" in lines and "만17세~44세" not in simple.text   # 다음 계약의 첫 줄은 이름보다 먼저 나와도 뺀다
    assert "다라" not in simple.text and "최초계약" not in simple.text and "갱신" not in simple.text.replace("[갱신형]", "")
    general = C.main_section(pages(RENEW), "일반고지")
    assert (general.first_page, general.last_page) == (3, 4)                     # 쪽이 넘어간 표의 쪽 번호
    assert "만17세~64세" in general.text and "22세~86세" in general.text and "만17세~42세" not in general.text
    assert C.main_section(pages(RENEW), "8종") is None                             # 종별 항목이 있는데 그 이름이 없다
    health = C.main_section(pages(MODULE), "8종")
    assert health.text.split("\n")[3] == "7년납" and health.text.endswith("27년납 16세~63세")
    assert "사아" not in health.text and "16세~41세" not in health.text and health.first_page == 7
    assert C.main_name(health) == "[건강]가나 사망" and C.main_name(simple) == "[갱신형][간편]가나 사망"
    # 한 줄짜리 기본계약 줄도 기본계약 표다
    first = C.main_section(pages(MODULE), "1종")
    assert first.text == "기본 100세만기 20년납 16세~41세 월납\n·[건강]가나 사망"
    # 칸이 갈리지 않고 "기본계약"으로 적힌 줄도 기본계약 표다
    whole = C.main_section(pages(MODULE.replace("기본 100세만기 20년납", "기본계약 100세만기 20년납")), "1종")
    assert whole.text.startswith("기본계약 100세만기") and C.AGE_MAIN_NOTE in C.prompt_for("가입나이", whole.text)


def test_main_section_is_none_without_a_main_table():
    plain = "\n===== 3쪽 =====\n2. 가입나이, 보험기간\n가. 주계약\n최초계약 20~80세 20년만기 전기납\n3. 보험가입금액의 한도\n"
    assert C.main_section(pages(plain)) is None
    assert C.main_section(pages(plain), "주계약") is None


def test_age_items_and_scope_names():
    assert C.age_items(pages(RENEW)) == ["가. 간편고지", "나. 일반고지"]
    assert C.age_items(pages(MODULE)) == ["가. 1종 및 9종", "라. 8종"]
    found = {v.id: v for v in VV.build(TARGETS, INDEX)[0]}
    assert job.scopes_of(found[S315]) == ["7종", "간편고지"] and job.scopes_of(found[M8]) == ["8종", "일반고지"]


def test_main_table_gets_its_own_note_and_other_shapes_keep_the_old_prompt():
    text = C.main_section(pages(RENEW), "간편고지").text
    prompt = C.prompt_for("가입나이", text)
    assert C.AGE_MAIN_NOTE in prompt and prompt.endswith("본문\n" + text)
    assert prompt.replace(C.AGE_MAIN_NOTE + "\n\n", "") == C.AGE_PROMPT.replace("{text}", text)
    old = "2. 가입나이, 보험기간\n가. 주계약\n최초계약 20~80세 20년만기 전기납"
    assert C.prompt_for("가입나이", old) == C.AGE_PROMPT.replace("{text}", old)


def test_main_names_and_aliases_point_to_the_main_rider():
    t = C.target_of(M8, "8종(일반형)", [rider(M8, "가나 사망", "주계약"), rider(M8, "다라 사망", "선택특약")])
    assert t.rider("가나 사망") == (True, None) and t.rider("가나 사망 월납") == (True, None)
    assert t.rider("기본계약") == (True, None) and t.rider("다라 사망") == (True, ids.rider_id(M8, "다라 사망"))
    assert t.rider("[건강]가나 사망") == (False, None)                           # 기본계약 표의 이름은 conditions_run이 더한다
    assert C.is_main("기본계약") and not C.is_main("기본계약 보험료 납입면제대상 특약")


# ---------- 배치 ----------
def test_main_part_writes_only_main_conditions_and_leaves_other_rows_alone():
    store = sheet_store()
    before = store.read()
    fake = Fake()
    report = job.run(fake, store, TARGETS, INDEX, TEXTS.get, NOW, read_thresholds=False, parts=(job.MAIN_PART,))
    assert report.written and report.errors == {}
    # 같은 사업방법서라도 고지유형 항목이 다르면 따로 뽑는다: 간편고지(7종 둘), 일반고지(8종), 건강 모듈 상품 8종
    assert fake.calls == {"가입나이": 3, "가입한도": 0, "결합제약": 0, "급부": 0, "판정": 3}
    assert all(len(b) < 200 for b in fake.bodies)                                 # 기본계약 표만 넣는다
    assert report.main_done == {S315, S355, R8, M8} and not (report.done or report.conditions_done or report.gate_done)
    after = store.read()
    for tab in TABS:
        if tab not in ("sys_가입조건", "sys_작업로그"):
            assert after[tab] == before[tab], tab                               # 종형, 특약, 급부, 결합제약은 그대로다
    assert after["sys_작업로그"][:len(before["sys_작업로그"])] == before["sys_작업로그"]
    assert len(after["sys_작업로그"]) > len(before["sys_작업로그"])
    rows = after["sys_가입조건"]
    assert [r for r in rows if r["종형ID"] == "EPOSTX"] == [before["sys_가입조건"][0]]   # 다른 회사 행은 그대로
    assert not any(r["조건행ID"].endswith("_Cstale") for r in rows)                 # 다시 뽑은 종형의 낡은 행은 걷어낸다
    mine = [r for r in rows if r["종형ID"] != "EPOSTX"]
    assert check_rows("sys_가입조건", mine) == {} and all(r["특약ID"] is None for r in mine)
    # 갱신 주기 18년으로 정한 종형은 보험기간 18년 줄만 쓴다
    got = {v: sorted((r["보험기간구분"], r["납입기간구분"], r["최저가입나이"], r["최고가입나이"]) for r in mine if r["종형ID"] == v)
           for v in (S315, S355, R8)}
    assert got == {S315: [("18년", "전기납", 17, 77)], S355: [("18년", "전기납", 17, 77)], R8: [("18년", "전기납", 17, 75)]}
    assert any("보험기간이 그 주기와 다른 행 6개는 쓰지 않음" in n for n in report.notes)
    # 비갱신 종형은 보험기간과 납입기간마다 행을 쓴다. 조건행ID는 ids.condition_id 식 그대로다
    health = {r["조건행ID"]: r for r in mine if r["종형ID"] == M8}
    assert len(health) == 10
    assert health[ids.condition_id(M8, "90세만기", "27년납", "", "", "16-63")]["최고가입나이"] == 63
    assert health[ids.condition_id(M8, "100세만기", "7년납", "", "", "16-68")]["최저가입나이"] == 16
    assert any("가입한도 절을 찾지 못함" in n for n in report.notes)
    # 관문 계산이 시트의 주계약 행으로 가입나이를 찾는다
    data = Data(after)
    main = data.main_rider(R8)
    assert main == ids.rider_id(R8, "[갱신형]가나 사망")
    assert data.age_limit(main, Cond(age=75, sex="M")).ok and not data.age_limit(main, Cond(age=76, sex="M")).ok
    assert data.limit_gap(R8)["noAge"] is False
    assert S.variant_gate(data, R8, S.Profile(age=40, sex="M", since=0.25))["상태"] != S.NO_AGE
    # 다시 돌려도 같은 조건행ID가 나온다
    again = job.run(Fake(), store, TARGETS, INDEX, TEXTS.get, NOW, read_thresholds=False, parts=(job.MAIN_PART,))
    assert again.written
    assert sorted(r["조건행ID"] for r in store.read()["sys_가입조건"]) == sorted(r["조건행ID"] for r in rows)


def test_dry_run_and_main_part_is_not_a_default_part():
    store = sheet_store()
    before = store.read()
    report = job.run(Fake(), store, TARGETS, INDEX, TEXTS.get, NOW, read_thresholds=False, parts=(job.MAIN_PART,), dry_run=True)
    assert not report.written and report.main_done and report.rows["sys_가입조건"]
    assert store.read() == before
    assert job.MAIN_PART not in job.PARTS


def test_missing_method_text_or_main_rider_or_item_skips_without_calls():
    store = sheet_store()
    before = store.read()
    fake = Fake()
    report = job.run(fake, store, TARGETS, INDEX, {}.get, NOW, read_thresholds=False, parts=(job.MAIN_PART,))
    assert fake.calls["가입나이"] == 0 and not report.main_done and not report.written
    assert sum("사업방법서 글자 파일이 없어" in n for n in report.notes) == 4
    assert store.read() == before
    # 주계약 행이 시트에 없는 종형(급부를 아직 적재하지 않음)과 종별 항목을 찾지 못한 종형은 건너뛴다
    store.write_tab("sys_특약", [r for r in before["sys_특약"] if r["종형ID"] != M8])
    odd = {**TEXTS, "saeop_R8": RENEW.replace("나. 일반고지", "나. 표준고지")}
    fake = Fake()
    report = job.run(fake, store, TARGETS, INDEX, odd.get, NOW, read_thresholds=False, parts=(job.MAIN_PART,))
    assert report.main_done == {S315, S355} and fake.calls["가입나이"] == 1
    assert any("8종(일반형): 시트에 주계약 행이 없어" in n for n in report.notes)
    assert any("8종(미지급형,일반고지): 가입나이 절의 종별 항목" in n for n in report.notes)
    assert [r for r in store.read()["sys_가입조건"] if r["종형ID"] == R8] == [before["sys_가입조건"][1]]   # 시트에 있던 행 그대로


class Stripped(Fake):
    """기본계약 표의 계약 이름에서 대괄호 표시를 빼고 옮기는 모델. 실행 45092778802에서 본 꼴이다("[건강]상해 사망"을
    "건강상해 사망"으로, "[갱신형]상해 사망"을 "상해 사망"으로 옮겼다). 같은 본문을 다시 물으면 줄을 절반만 돌려준다.

    extra: 건강 모듈 표에서 함께 돌려줄 항목. 기본계약 표에 다른 계약의 줄이 섞여 든 경우를 본뜬다.
    """

    def __init__(self, extra=()):
        super().__init__()
        self.extra = list(extra)
        self.asked = {}

    def generate(self, model, prompt, schema=None, temperature=0.0):
        out = super().generate(model, prompt, schema, temperature)
        body = self.bodies[-1]
        if '"가입나이, 보험기간' not in prompt:
            return out
        self.asked[body] = self.asked.get(body, 0) + 1
        if "[건강]가나 사망" in body:
            rows = [item("건강가나 사망", t, p, a) for t, p, a in HEALTH]
            return {"items": (rows if self.asked[body] == 1 else rows[::2]) + self.extra}
        if "[갱신형]가나 사망" in body:
            return {"items": [item("가나 사망", t, "전기납", a) for t, a in GENERAL]}
        return out


def test_main_table_names_without_brackets_still_point_to_the_main_rider():
    store = sheet_store()
    fake = Stripped()
    report = job.run(fake, store, TARGETS, INDEX, TEXTS.get, NOW, read_thresholds=False, parts=(job.MAIN_PART,))
    assert report.written and report.errors == {}
    assert report.main_done == {S315, S355, R8, M8}
    assert not any("특약" in n and "행으로 만들지 않음" in n for n in report.notes)
    # 이름이 원문 글자와 조금 달라도 주계약 이름과 겹치면 원문 대조에 걸리지 않는다. 다시 뽑지 않아 줄을 절반만 돌려준 답으로 바뀌지 않는다
    assert fake.calls["가입나이"] == 3
    mine = [r for r in store.read()["sys_가입조건"] if r["종형ID"] in (R8, M8)]
    assert all(r["특약ID"] is None for r in mine)
    assert sorted((r["보험기간구분"], r["납입기간구분"], r["최저가입나이"], r["최고가입나이"]) for r in mine if r["종형ID"] == R8) \
        == [("18년", "전기납", 17, 75)]
    health = {(r["보험기간구분"], r["납입기간구분"]): (r["최저가입나이"], r["최고가입나이"]) for r in mine if r["종형ID"] == M8}
    assert health == {(t, p): tuple(int(x) for x in a.replace("세", "").split("~")) for t, p, a in HEALTH}


def test_other_contract_lines_in_the_main_table_are_still_left_out():
    store = sheet_store()
    extra = [item("다라 사망", "80세만기", "10년납", "20세~50세"), item("가나 사망 특약", "80세만기", "11년납", "20세~50세")]
    report = job.run(Stripped(extra), store, TARGETS, INDEX, TEXTS.get, NOW, read_thresholds=False, parts=(job.MAIN_PART,))
    assert report.written and M8 in report.main_done
    rows = [r for r in store.read()["sys_가입조건"] if r["종형ID"] == M8]
    assert len(rows) == 10 and not any(r["보험기간구분"] == "80세만기" for r in rows)
    assert any("주계약 가입조건만 뽑으므로 특약 2개의 항목은 행으로 만들지 않음" in n for n in report.notes)


def test_near_main_names_only_count_for_the_main_table():
    t = C.target_of(M8, "8종(일반형)", [rider(M8, "가나 사망", "주계약")])
    # 기본계약 표만 넣지 않은 경로(우체국, 한화생명의 가입조건)는 이름을 느슨하게 맞추지 않는다
    assert t.near_names == frozenset() and t.rider("건강가나 사망", near=True) == (False, None)
    loose = replace(t, near_names=frozenset({"가나 사망", "[건강]가나 사망"}))
    assert loose.rider("건강가나 사망", near=True) == (True, None)                 # 대괄호를 뺀 이름
    assert loose.rider("[건강] 가나 사망 월납", near=True) == (True, None)
    assert loose.rider("사망", near=True) == (True, None)                         # 주계약 이름에 포함되는 이름
    assert loose.rider("건강가나 사망", near=False) == (False, None)               # 가입한도와 결합제약 항목은 그대로
    for other in ("다라 사망", "가나 사망 특약", "가나 사망 특별약관", "", "[]·"):
        assert loose.rider(other, near=True) == (False, None), other
    assert C.near_main("상해 사망", ["[갱신형]상해 사망"]) and C.near_main("건강상해 사망", ["[건강]상해 사망", "상해 사망"])
    assert not C.near_main("질병 사망", ["[갱신형]상해 사망"]) and not C.near_main("상해 사망", [])


def test_without_a_main_table_the_age_section_is_not_sent():
    store = sheet_store()
    fake = Fake()
    flat = {k: v.replace("기본 ", "주 ") for k, v in TEXTS.items()}
    report = job.run(fake, store, TARGETS, INDEX, flat.get, NOW, read_thresholds=False, parts=(job.MAIN_PART,))
    assert fake.calls["가입나이"] == 0 and not report.main_done
    assert any("기본계약 표를 찾지 못해 가입나이를 뽑지 않음" in n for n in report.notes)
    assert not any("가입나이 절을 찾지 못함" in n for n in report.notes)
