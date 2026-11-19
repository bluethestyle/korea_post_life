"""job.run을 가짜 시트·가짜 모델로 끝까지 돌려, 다시 뽑지 않은 자료가 시트에서 사라지지 않는지 본다."""
import json
from datetime import datetime
from pathlib import Path

from postlife.extract import job
from postlife.gemini import Answer
from postlife.schema import TABS
from postlife.sheets_io import MemoryBackend, SheetStore
from postlife.snapshot import KST

SUMMARY = """
===== 5쪽 =====
② 보험금 지급사유
■ 주계약
(보험가입금액 1,000만원 기준)
재해사망보험금 1,000만원
■ 무배당 가나입원특약(20년갱신형) 2606
(특약보험가입금액 1,000만원 기준)
가나입원보험금 1,000만원
③ 일반적 보험금 지급제한 사유
"""
NOW = datetime(2026, 11, 19, 16, 0, tzinfo=KST)
TARGETS = json.loads((Path(__file__).resolve().parents[1] / "data/targets/epost.json").read_text(encoding="utf-8"))
INDEX = [{"기관": "EPOST", "상품코드": code, "상품명": f"무배당 우체국간편한건강보험(20년갱신형) 2606 {name}",
          "판매시작일": "2026-06-17", "판매종료일": None, "문서": "상품요약서", "해시": "h1", "저장이름": "yoyak", "쪽수": 9}
         for code, name in (("P500129", "1종(간편가입315)"), ("P500130", "2종(간편가입325)"))]


class Gemini:
    """어느 조각에나 급부 한 줄을 돌려주고, 판정은 모두 맞다고 답한다."""

    def __init__(self, benefit="보험금"):
        self.benefit = benefit

    def generate(self, model, prompt, schema=None, temperature=0.0):
        return {"base_amount": "1,000만원", "benefits": [
            {"name": self.benefit, "target": "", "amount": "1,000만원", "reduced_period": "", "reduced_amount": "",
             "reduced2_period": "", "reduced2_amount": "", "start_condition": "", "limit": "", "role": "주급부", "quote": ""}]}

    def decide(self, model, input_text, questions):
        return {k: Answer(True, None, {"true": 0.97, "false": 0.03}) for k in questions}


def filled_store():
    """급부를 한 번 뽑아 쓴 뒤, 가입조건·보험료·질병코드 단계가 채웠을 값을 손으로 넣은 시트."""
    store = SheetStore(MemoryBackend())
    for name in TABS:
        store.write_tab(name, [])
    first = job.run(Gemini(), store, TARGETS, INDEX, {"yoyak": SUMMARY}.get, NOW, read_thresholds=False, parts=("급부",))
    assert first.written and len(first.done) == 2
    data = store.read()
    for r in data["sys_특약"]:
        if r["담보구분"] != "주계약":
            r["최소가입금액만원"], r["최대가입금액만원"], r["합산한도기준키"] = 500, 3000, "입원합산"
    store.write_tab("sys_특약", data["sys_특약"])
    rider, benefit = data["sys_특약"][0], data["sys_급부"][0]
    store.write_tab("sys_가입조건", [{"조건행ID": f"{rider['종형ID']}_C1", "종형ID": rider["종형ID"], "특약ID": None,
                                   "보험기간구분": "20년만기", "납입기간구분": "전기납", "성별": None, "최저가입나이": 20,
                                   "최고가입나이": 80, "구간최대가입금액만원": None}])
    store.write_tab("sys_보험료예시", [{"보험료행ID": f"{rider['특약ID']}_P1", "특약ID": rider["특약ID"], "가입나이": 40, "성별": "M",
                                    "보험기간구분": "20년만기", "납입기간구분": "전기납", "기준가입금액만원": 1000,
                                    "월납보험료원": 12000, "출처구분": "요약서"}])
    store.write_tab("sys_급부질병코드", [{"질병매핑ID": f"{benefit['급부ID']}_K1", "급부ID": benefit["급부ID"], "KCD버전": "8",
                                     "시작코드": "C00", "끝코드": "C97", "포함여부": "Y", "별표명": None}])
    return store


def limits(store):
    return {r["특약ID"]: (r["최소가입금액만원"], r["최대가입금액만원"], r["합산한도기준키"]) for r in store.read(["sys_특약"])["sys_특약"]}


def test_rerunning_benefits_alone_keeps_rider_limits_and_other_tabs():
    store = filled_store()
    before = store.read()
    assert sum(1 for v in limits(store).values() if v == (500, 3000, "입원합산")) == 2

    report = job.run(Gemini("입원보험금"), store, TARGETS, INDEX, {"yoyak": SUMMARY}.get, NOW, read_thresholds=False,
                     parts=("급부",))
    assert report.written and report.errors == {}
    after = store.read()
    assert {r["원시급부명"] for r in after["sys_급부"]} == {"입원보험금"}        # 급부는 새로 뽑은 값으로 바뀌었다
    assert limits(store) == {r["특약ID"]: (r["최소가입금액만원"], r["최대가입금액만원"], r["합산한도기준키"]) for r in before["sys_특약"]}
    for tab in ("sys_가입조건", "sys_보험료예시", "sys_급부질병코드"):               # 급부 추출이 채우지 않는 탭은 그대로다
        assert after[tab] == before[tab] and len(after[tab]) == 1, tab


def test_limits_survive_when_conditions_cannot_be_extracted():
    store = filled_store()
    before = limits(store)
    # 급부와 가입조건을 함께 돌렸지만 사업방법서가 없어 가입조건을 뽑지 못한 경우
    report = job.run(Gemini(), store, TARGETS, INDEX, {"yoyak": SUMMARY}.get, NOW, read_thresholds=False)
    assert report.written and not report.conditions_done
    assert any("사업방법서 글자 파일이 없어" in n for n in report.notes)
    assert limits(store) == before and len(store.read(["sys_가입조건"])["sys_가입조건"]) == 1


def test_dry_run_reports_inherited_limits_without_writing():
    store = filled_store()
    calls = len(store.backend.calls)
    dry = job.run(Gemini(), store, TARGETS, INDEX, {"yoyak": SUMMARY}.get, NOW, read_thresholds=False, parts=("급부",),
                  dry_run=True)
    assert not dry.written and sum(1 for r in dry.rows["sys_특약"] if r["최대가입금액만원"] == 3000) == 2
    assert all(kind == "get" for kind, _ in store.backend.calls[calls:])


def test_variants_sharing_a_summary_with_different_settings_are_reported():
    targets = {"기관코드": "EPOST", "공시목록URL": "https://example.invalid/list", "상품": [
        {"모상품ID": "EPOST_GANA", "개정연월": "2606", "비교역할구분": "관문전용", "갱신유형": "갱신", "갱신주기년": 20,
         "환급유형": "표준형", "납입면제적용": False,
         "종형": [{"공시상품코드": "X1", "종형명": "1종", "심사유형": "일반심사", "간편고지약칭": "일반"}]},
        {"모상품ID": "EPOST_DARA", "개정연월": "2606", "비교역할구분": "관문전용", "갱신유형": "비갱신", "갱신주기년": None,
         "환급유형": "표준형", "납입면제적용": False,
         "종형": [{"공시상품코드": "X2", "종형명": "2종", "심사유형": "일반심사", "간편고지약칭": "일반"},
                  {"공시상품코드": "X3", "종형명": "3종", "심사유형": "일반심사", "간편고지약칭": "일반"}]}]}
    doc = {"기관": "EPOST", "상품명": "무배당 가나보험 2606", "판매시작일": "2026-06-17", "판매종료일": None, "쪽수": 9}
    index = [dict(doc, 상품코드="X1", 문서="상품요약서", 해시="same", 저장이름="yoyak"),
             dict(doc, 상품코드="X2", 문서="상품요약서", 해시="same", 저장이름="yoyak"),
             dict(doc, 상품코드="X3", 문서="사업방법서", 해시="m3", 저장이름="saeop")]       # 3종은 요약서를 받지 못했다
    store = SheetStore(MemoryBackend())
    report = job.run(Gemini(), store, targets, index, {"yoyak": SUMMARY}.get, NOW, read_thresholds=False, parts=("급부",),
                     dry_run=True)
    assert len(report.done) == 2                                                # 설정이 갈려도 건너뛰지는 않는다
    assert any("갱신 설정이나 사업방법서가 서로 다름" in n and "'1종'" in n for n in report.notes)
    assert any(n.startswith("X3 3종") and "상품요약서가 없어" in n for n in report.notes)
    # 설정이 같은 묶음에는 그런 말이 붙지 않는다
    same = job.run(Gemini(), filled_store(), TARGETS, INDEX, {"yoyak": SUMMARY}.get, NOW, read_thresholds=False,
                   parts=("급부",), dry_run=True)
    assert not any("서로 다름" in n or "상품요약서가 없어" in n for n in same.notes)


def test_row_repeated_with_the_same_content_is_written_once():
    report = job.Report()
    a = {"급부ID": "B1", "특약ID": "T1", "원시급부명": "가나보험금", "기준지급금액만원": 100}
    report.rows["sys_급부"] = [a, dict(a), {**a, "급부ID": "B2"}, {**a, "급부ID": "B2", "기준지급금액만원": 200}]
    job._drop_repeats("sys_급부", report)
    # 내용까지 같은 B1은 하나만 남는다. 내용이 다른 B2는 어느 쪽이 맞는지 알 수 없어 둘 다 남겨 중복 검사에 걸리게 한다
    assert [r["급부ID"] for r in report.rows["sys_급부"]] == ["B1", "B2", "B2"]
    assert any("B1" in n and "하나만 씀" in n for n in report.notes) and not any("B2" in n for n in report.notes)


def test_same_benefit_extracted_twice_does_not_lose_the_row():
    # 같은 특약 머리줄이 두 번 나와 같은 급부가 두 번 뽑힌 요약서. 고치기 전에는 겹친 급부를 둘 다 버렸다
    twice = SUMMARY.replace("③ 일반적", "■ 무배당 가나입원특약(20년갱신형) 2606\n(특약보험가입금액 1,000만원 기준)\n"
                            "가나입원보험금 1,000만원\n③ 일반적")
    store = SheetStore(MemoryBackend())
    report = job.run(Gemini(), store, TARGETS, INDEX, {"yoyak": twice}.get, NOW, read_thresholds=False, parts=("급부",))
    assert report.written and report.errors == {}
    data = store.read()
    assert len(data["sys_특약"]) == 4 and len(data["sys_급부"]) == 4            # 종형 2개 × (주계약, 특약) × 급부 1줄
    assert sum("하나만 씀" in n for n in report.notes) == 2
