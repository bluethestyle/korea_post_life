"""관문전용 종형: 종형 값이 상품 값보다 앞서고, 배치가 급부를 뽑지 않고 종형 행, 주계약 행, 주계약 가입조건만 쓰는지 본다.

시험 글은 사업방법서와 요약서의 제목 모양과 표가 글자로 풀린 모양만 본떠 직접 만든 것이다. 상품 이름과 숫자는 지어낸 것이다.
모델은 부르지 않는다. 모델이 돌려줄 법한 답을 손으로 만들어 넣는다.
"""
import json
from datetime import datetime
from pathlib import Path

import pytest

from postlife import ids
from postlife.extract import job
from postlife.extract import variants as VV
from postlife.gemini import Answer
from postlife.schema import TABS
from postlife.sheets_io import MemoryBackend, SheetStore
from postlife.site import sales as S
from postlife.site.model import Cond, Data
from postlife.snapshot import KST
from postlife.validate import check_rows

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 20, 16, 0, tzinfo=KST)
ZERO, ONE = "간편가입형(0년)", "간편가입형(1년)"

TARGETS = {"기관코드": "HANWHALIFE", "공시목록URL": "https://example.invalid/list", "상품": [
    {"모상품ID": "GANA_H", "개정연월": "2610", "비교역할구분": "정밀비교", "갱신유형": "비갱신", "갱신주기년": None,
     "환급유형": "해약환급금 미지급형", "납입면제적용": True,
     "종형": [
         {"공시상품코드": "X1", "종형명": ONE, "심사유형": "간편심사", "간편고지약칭": "3.1.5", "고지최근소견개월": 3,
          "고지입원수술년수": 1, "고지중대질병년수": 5, "고지수술포함여부": True, "고지중대질병수": 7},
         {"공시상품코드": "X1", "종형명": ZERO, "비교역할구분": "관문전용", "심사유형": "간편심사", "간편고지약칭": "3.0.5",
          "고지최근소견개월": 3, "고지입원수술년수": 0, "고지중대질병년수": 5, "고지수술포함여부": None, "고지중대질병수": 7}]}]}
DOC = {"기관": "HANWHALIFE", "상품코드": "X1", "상품명": "가나 통합보험 무배당", "판매시작일": "2026-10-01", "판매종료일": None,
       "쪽수": 9}
INDEX = [dict(DOC, 문서="상품요약서", 해시="hy", 저장이름="yoyak"), dict(DOC, 문서="사업방법서", 해시="hm", 저장이름="saeop")]

METHOD = """
===== 3쪽 =====
2. 보험기간, 보험료 납입기간, 보험료 납입주기 및 피보험자 가입나이
가. 보험기간, 보험료 납입기간 및 피보험자 가입나이
- 가입최저나이: 만15세
- 가입최고나이: 보험종목, 성별, 보험기간 및 보험료 납입기간별로 아래와 같음
90세만기 종신
구 분
남자 여자 남자 여자
10년납 79세 79세 80세 80세
간편가입형(0년)
20년납 69세 69세 80세 80세
10년납 79세 79세 80세 80세
간편가입형(1년)
20년납 69세 69세 80세 80세
※ 가나특약은 주계약과 같은 나이로 가입
나. 보험료 납입주기: 월납
3. 의무가입에 관한 사항
- 해당 없음
"""

SUMMARY = """
===== 5쪽 =====
② 보험금 지급사유
■ 주계약
(보험가입금액 1,000만원 기준)
재해사망보험금 1,000만원
③ 일반적 보험금 지급제한 사유

===== 6쪽 =====
2.
보험가입자격요건
가. 보험의 종류
(1) 간편가입형(0년)

===== 7쪽 =====
마. 가입한도
▪ 주계약 :
구 분 가입 한도
간편가입형(0년)
~70세 300만원~1,000만원
주계약 간편가입형(1년)
71세~ 300만원
※ 그 외 특약의 가입한도는 회사가 별도로 정한 기준에 따라 적용합니다.
바. 건강진단 여부
- 무진단으로 가입 가능
"""
TEXTS = {"yoyak": SUMMARY, "saeop": METHOD}
COLUMNS = (("90세만기", "남자"), ("90세만기", "여자"), ("종신", "남자"), ("종신", "여자"))


def cells(scope, payment, tops):
    return [{"subjects": ["주계약"], "variant_scope": scope, "contract": "구분없음", "sex": sex, "age": f"만15세~{top}세",
             "term": term, "payment": payment} for (term, sex), top in zip(COLUMNS, tops)]


AGES = {"items": cells(ZERO, "10년납", (79, 79, 80, 80)) + cells(ZERO, "20년납", (69, 69, 80, 80))
        + [{"subjects": ["가나특약"], "variant_scope": ZERO, "contract": "구분없음", "sex": "남자", "age": "만15세~79세",
            "term": "90세만기", "payment": "10년납"}]}        # 대상에 없는 특약 줄은 행으로 만들지 않는다
LIMITS = {"items": [
    {"subjects": ["주계약"], "variant_scope": "", "age": "~70세", "min": "300만원", "max": "1,000만원", "unit": ""},
    {"subjects": ["주계약"], "variant_scope": "", "age": "71세~", "min": "300만원", "max": "300만원", "unit": ""}]}
BENEFIT = {"base_amount": "1,000만원", "benefits": [
    {"name": "재해사망보험금", "target": "", "amount": "1,000만원", "reduced_period": "", "reduced_amount": "",
     "reduced2_period": "", "reduced2_amount": "", "start_condition": "", "limit": "", "role": "주급부", "quote": ""}]}


class Fake:
    """프롬프트로 무엇을 묻는지 가려 답한다. 종류별 호출 수를 센다."""

    def __init__(self):
        self.calls = {"급부": 0, "가입나이": 0, "가입한도": 0, "결합제약": 0, "판정": 0}

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
        return {"가입나이": AGES, "가입한도": LIMITS, "결합제약": {"items": []}, "급부": BENEFIT}[kind]

    def decide(self, model, text, questions):
        self.calls["판정"] += 1
        return {k: Answer(True, None, {"true": 0.97, "false": 0.03}) for k in questions}


def empty_store():
    store = SheetStore(MemoryBackend())
    for name in TABS:
        store.write_tab(name, [])
    return store


def vid(name):
    return ids.variant_id("HANWHALIFE", "X1", name)


# ---------- 종형 행 ----------
def test_variant_role_overrides_the_product_role_and_leaves_other_rows_alone():
    found, problems = VV.build(TARGETS, INDEX)
    assert problems == []
    rows = {v.row["종형명"]: v.row for v in found}
    assert rows[ZERO]["비교역할구분"] == "관문전용" and rows[ONE]["비교역할구분"] == "정밀비교"
    assert [v.gate_only for v in found] == [False, True]
    assert rows[ZERO]["고지입원수술년수"] == 0 and rows[ZERO]["고지수술포함여부"] is None
    assert check_rows("sys_상품종형", list(rows.values())) == {}
    # 종형에 값이 없으면 상품의 값을 쓴다: 종형의 값을 지운 설정은 관문전용 종형만 다른 행이 된다
    plain = json.loads(json.dumps(TARGETS))
    del plain["상품"][0]["종형"][1]["비교역할구분"]
    again = {v.row["종형명"]: v.row for v in VV.build(plain, INDEX)[0]}
    assert again[ONE] == rows[ONE] and again[ZERO] == {**rows[ZERO], "비교역할구분": "정밀비교"}


@pytest.mark.skipif(not (ROOT / "data/snapshot/sys_상품종형.jsonl").exists(), reason="사본 없음")
def test_real_targets_keep_the_rows_of_the_variants_already_on_the_sheet():
    """저장소의 한화생명 설정으로 만든 종형 행 가운데 사본에 있는 종형은 사본의 행과 글자 하나 다르지 않다.

    관문전용 네 종형이 시트에 올라간 뒤의 사본에서도 같은 검사가 그대로 돈다(그때는 네 종형의 행도 사본과 견준다)."""
    targets = json.loads((ROOT / "data/targets/hanwha.json").read_text(encoding="utf-8"))
    snap = [json.loads(line) for line in (ROOT / "data/snapshot/sys_상품종형.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    sheet = {r["종형ID"]: r for r in snap if r["기관코드"] == "HANWHALIFE"}
    one = sheet[vid_of(targets, ONE)]
    index = [{"기관": "HANWHALIFE", "상품코드": "2597", "상품명": one["공시상품명"], "판매시작일": one["적용시작일"],
              "판매종료일": one["판매종료일"], "문서": kind, "해시": one[column], "저장이름": kind, "쪽수": 30}
             for kind, column in (("상품요약서", "요약서해시"), ("사업방법서", "사업방법서해시"))]
    found, problems = VV.build(targets, index)
    assert problems == []
    made = {v.id: v.row for v in found}
    assert set(sheet) <= set(made)
    for key, row in sheet.items():
        assert made[key] == row, key
    gates = [v for v in found if v.gate_only]
    assert [v.row["종형명"] for v in gates] == ["간편가입형(0년)", "간편가입형(3년)", "간편가입형(4년)", "간편가입형(10년)"]
    assert [(v.row["간편고지약칭"], v.row["고지입원수술년수"]) for v in gates] == [("3.0.5", 0), ("3.3.5", 3), ("3.4.5", 4),
                                                                              ("3.10.5", 10)]
    assert not {v.id for v in gates} & {v.id for v in found if not v.gate_only}     # 새 종형ID는 기존 종형ID와 겹치지 않는다
    assert {v.id for v in found if not v.gate_only} <= set(sheet)                   # 기존 네 종형은 사본에 있다
    assert check_rows("sys_상품종형", [v.row for v in gates]) == {}


def vid_of(targets, name):
    return ids.variant_id(targets["기관코드"], "2597", name)


def test_main_row_has_the_shape_of_the_extracted_main_row():
    v = next(x for x in VV.build(TARGETS, INDEX)[0] if x.gate_only)
    row = VV.main_row(v)
    assert row["특약ID"] == ids.rider_id(v.id, "주계약") and row["담보구분"] == "주계약" and row["갱신여부"] is False
    assert set(row) == set(TABS["sys_특약"].header) and check_rows("sys_특약", [row]) == {}


# ---------- 배치 ----------
def test_gate_part_writes_variant_main_and_ages_without_benefit_calls():
    store = empty_store()
    first = job.run(Fake(), store, TARGETS, INDEX, TEXTS.get, NOW, read_thresholds=False, parts=("급부",))
    assert first.done == {vid(ONE)} and not first.gate_done                # 급부 부분은 관문전용 종형을 보지 않는다
    before = store.read()
    assert {r["종형ID"] for r in before["sys_상품종형"]} == {vid(ONE)}

    fake = Fake()
    report = job.run(fake, store, TARGETS, INDEX, TEXTS.get, NOW, read_thresholds=False, parts=("관문",))
    assert report.written and report.errors == {}
    assert fake.calls["급부"] == 0 and fake.calls["결합제약"] == 0          # 급부와 결합제약 절은 모델을 부르지 않는다
    assert fake.calls["가입나이"] == 1 and fake.calls["가입한도"] == 1 and fake.calls["판정"] == 2
    assert report.gate_done == report.gate_conditions_done == {vid(ZERO)} and not report.done
    after = store.read()
    zero = next(r for r in after["sys_상품종형"] if r["종형ID"] == vid(ZERO))
    assert zero["비교역할구분"] == "관문전용" and zero["고지입원수술년수"] == 0
    main = next(r for r in after["sys_특약"] if r["종형ID"] == vid(ZERO))
    assert (main["담보구분"], main["최소가입금액만원"], main["최대가입금액만원"]) == ("주계약", 300, 1000)
    assert len([r for r in after["sys_특약"] if r["종형ID"] == vid(ZERO)]) == 1
    rows = [r for r in after["sys_가입조건"] if r["종형ID"] == vid(ZERO)]
    assert rows and all(r["특약ID"] is None for r in rows)
    assert sorted({(r["최저가입나이"], r["최고가입나이"], r["구간최대가입금액만원"]) for r in rows
                   if (r["보험기간구분"], r["납입기간구분"], r["성별"]) == ("90세만기", "10년납", "M")}) == [(15, 70, 1000),
                                                                                                (71, 79, 300)]
    assert any("주계약만 두는 종형이라 특약 1개" in n for n in report.notes)
    # 다른 종형의 행은 그대로다(급부 탭에는 종형ID 열이 없어 통째로 견준다)
    for tab in ("sys_상품종형", "sys_특약", "sys_급부", "sys_가입조건", "sys_결합제약", "sys_보험료예시"):
        assert [r for r in after[tab] if r.get("종형ID") != vid(ZERO)] == before[tab], tab
    # 관문 계산이 주계약 행으로 가입나이를 찾는다
    data = Data(after)
    assert data.main_rider(vid(ZERO)) == main["특약ID"]
    assert data.age_limit(main["특약ID"], Cond(age=75, sex="M")).ok and not data.age_limit(main["특약ID"], Cond(age=81, sex="M")).ok
    assert S.variant_gate(data, vid(ZERO), S.Profile(age=40, sex="M", since=0.25))["상태"] == S.OPEN


def test_default_parts_run_benefits_and_the_gate_and_rerun_keeps_ids():
    store = empty_store()
    fake = Fake()
    report = job.run(fake, store, TARGETS, INDEX, TEXTS.get, NOW, read_thresholds=False)
    assert job.PARTS == ("급부", "가입조건", "관문")
    assert report.done == {vid(ONE)} and report.gate_done == {vid(ZERO)}
    assert fake.calls["급부"] == 1                                         # 관문전용 종형 몫의 급부 호출은 없다
    first = store.read()
    again = job.run(Fake(), store, TARGETS, INDEX, TEXTS.get, NOW, read_thresholds=False, parts=("관문",))
    assert again.written
    second = store.read()
    for tab in ("sys_상품종형", "sys_특약", "sys_가입조건"):
        assert sorted(r[TABS[tab].key] for r in second[tab]) == sorted(r[TABS[tab].key] for r in first[tab]), tab


def test_gate_without_a_method_document_writes_only_the_variant_and_main_rows():
    store = empty_store()
    report = job.run(Fake(), store, TARGETS, INDEX, {"yoyak": SUMMARY}.get, NOW, read_thresholds=False, parts=("관문",))
    assert report.written and report.gate_done == {vid(ZERO)} and not report.gate_conditions_done
    assert any("사업방법서 글자 파일이 없어" in n for n in report.notes)
    after = store.read()
    assert [r["종형ID"] for r in after["sys_특약"]] == [vid(ZERO)] and after["sys_가입조건"] == []


def test_gate_part_does_nothing_for_targets_without_gate_variants():
    targets = json.loads(json.dumps(TARGETS))
    targets["상품"][0]["종형"] = targets["상품"][0]["종형"][:1]
    report = job.run(Fake(), empty_store(), targets, INDEX, TEXTS.get, NOW, read_thresholds=False, parts=("관문",))
    assert not (report.done or report.conditions_done or report.gate_done) and not report.written


def test_script_default_parts_match_the_job():
    text = (ROOT / "scripts/extract_product.py").read_text(encoding="utf-8")
    assert f'default="{",".join(job.PARTS)}"' in text
