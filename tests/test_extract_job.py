"""job.run을 가짜 시트·가짜 모델로 끝까지 돌려, 다시 뽑지 않은 자료가 시트에서 사라지지 않는지 본다."""
import json
from datetime import datetime
from pathlib import Path

from postlife import ids
from postlife.extract import job
from postlife.extract import rerun as R
from postlife.gemini import Answer, GeminiError
from postlife.schema import TABS
from postlife.sheets_io import MemoryBackend, SheetStore
from postlife.site.model import Data
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


# ---- 다시 뽑기: 급부ID 잇기와 이전 확정 줄 지키기 ----

RERUN_SUMMARY = """
===== 5쪽 =====
② 보험금 지급사유
■ 주계약
(보험가입금액 1,000만원 기준)
재해사망보험금 1,000만원
■ 무배당 가나입원특약(20년갱신형) 2606
(특약보험가입금액 1,000만원 기준)
가나입원보험금 질병 3만원 재해 2만원
가나수술보험금 100만원
■ 무배당 다라진단특약(20년갱신형) 2606
(특약보험가입금액 1,000만원 기준)
다라진단보험금 1,000만원
③ 일반적 보험금 지급제한 사유
"""
LATER = datetime(2026, 11, 26, 16, 0, tzinfo=KST)


def item(name, amount, target="", role="주급부"):
    return {"name": name, "target": target, "amount": amount, "reduced_period": "", "reduced_amount": "",
            "reduced2_period": "", "reduced2_amount": "", "start_condition": "", "limit": "", "role": role, "quote": ""}


BASE = {"주계약": [item("재해사망보험금", "1,000만원")],
        "가나입원": [item("가나입원보험금", "3만원", "질병"), item("가나수술보험금", "100만원", role="부수급부")],
        "다라진단": [item("다라진단보험금", "1,000만원")]}


class Scripted:
    """특약 이름에 든 글자마다 돌려줄 급부를 정해 둔 가짜 모델.

    low: {급부 이름: 판정 확률}. 그 급부를 묻는 문항은 이 확률을 받는다(0.40 미만이면 재추출 구간, 0.40~0.75는 검토 구간).
    fail: 이 글자가 든 특약은 추출 호출이 늘 실패한다.
    """

    def __init__(self, benefits=None, low=None, fail=()):
        self.benefits, self.low, self.fail = {**BASE, **(benefits or {})}, low or {}, fail

    def generate(self, model, prompt, schema=None, temperature=0.0):
        title = prompt.split("특약 이름: ", 1)[1].split("\n", 1)[0]
        if any(key in title for key in self.fail):
            raise GeminiError(503, "high demand")
        found = next(items for key, items in self.benefits.items() if key in title)
        return {"base_amount": "1,000만원", "benefits": found}

    def decide(self, model, input_text, questions):
        out = {}
        for key, q in questions.items():
            p = next((p for name, p in self.low.items() if f"'{name}'" in q["instructions"]), 0.97)
            out[key] = Answer(True, None, {"true": p, "false": 1 - p})
        return out


def rerun_store(gemini=None):
    """요약서를 한 번 뽑아 쓴 시트. 기본은 모든 급부가 확정이다."""
    store = SheetStore(MemoryBackend())
    first = job.run(gemini or Scripted(), store, TARGETS, INDEX, {"yoyak": RERUN_SUMMARY}.get, NOW, read_thresholds=False,
                    parts=("급부",))
    assert first.written and first.errors == {} and len(store.read(["sys_급부"])["sys_급부"]) >= 8
    return store


def again(store, gemini, **kw):
    return job.run(gemini, store, TARGETS, INDEX, {"yoyak": RERUN_SUMMARY}.get, LATER, read_thresholds=False,
                   parts=kw.pop("parts", ("급부",)), **kw)


def benefits_named(store, word):
    return sorted((r for r in store.read(["sys_급부"])["sys_급부"] if word in r["원시급부명"]), key=lambda r: r["급부ID"])


def test_benefit_whose_target_wording_changed_keeps_its_id_and_mapping():
    store = rerun_store()
    before = benefits_named(store, "가나입원")
    assert {r["원시급부명"] for r in before} == {"가나입원보험금(질병)"} and len(before) == 2
    store.write_tab("hum_담보매핑", [{"급부ID": r["급부ID"], "공시상품명": "가나", "원시특약명": "가나입원특약",
                                    "원시급부명": r["원시급부명"], "검토상태": "자동확정"} for r in before])

    report = again(store, Scripted({"가나입원": [item("가나입원보험금", "3만원", "질병 입원"), item("가나수술보험금", "100만원")]}))
    assert report.written and report.errors == {}
    after = benefits_named(store, "가나입원")
    assert [r["급부ID"] for r in after] == [r["급부ID"] for r in before]          # 괄호 안 표기만 달라 이전 ID를 이었다
    assert {r["원시급부명"] for r in after} == {"가나입원보험금(질병)"}              # 원시급부명도 이전 것
    mapped = {m["급부ID"] for m in store.read(["hum_담보매핑"])["hum_담보매핑"]}
    assert mapped <= {r["급부ID"] for r in store.read(["sys_급부"])["sys_급부"]}  # 매핑이 끊기지 않는다
    # 이번 실행의 판정 기록도 이어받은 ID를 가리킨다. 새로 계산된 ID는 시트 어디에도 없다
    fresh = {ids.benefit_id(r["특약ID"], "가나입원보험금(질병 입원)") for r in after}
    logs = store.read(["sys_작업로그"])["sys_작업로그"]
    assert not any(l["대상행ID"] in fresh for l in logs)
    assert any(l["대상행ID"] in {r["급부ID"] for r in after} and l["작업단계"] == "판정" and l["실행일시"].startswith("2026-11-26")
               for l in logs)
    # 가나수술보험금은 모델이 역할을 주급부로 바꿨지만 ID가 그대로인 줄이라 이번 값을 쓴다
    assert {r["급부역할"] for r in benefits_named(store, "가나수술")} == {"주급부"}
    assert report.rerun["이은 급부ID"] == 2 and report.rerun["지킨 이전 줄"] == 0
    assert report.rerun["잃은 줄"] == 0 and report.rerun["얻은 줄"] == 0
    assert "같은 급부라 이전 급부ID를 이은 줄 2" in report.markdown({})
    assert any("이전 급부ID와 원시급부명을 씀" in n and "'가나입원보험금(질병 입원)' → '가나입원보험금(질병)'" in n for n in report.notes)


def test_linked_row_takes_the_role_of_this_run_and_the_change_is_noted():
    # 한 특약 안의 급부역할은 서로 맞물려 정해진다. 이은 줄만 이전 역할로 두면 이전 실행과 이번 실행의 역할이 섞이므로 이번 값을 쓴다
    store = rerun_store()
    report = again(store, Scripted({"가나입원": [item("가나입원보험금", "3만원", "질병 입원", role="대등복합"),
                                               item("가나수술보험금", "100만원", role="부수급부")]}))
    assert {r["급부역할"] for r in benefits_named(store, "가나입원")} == {"대등복합"}
    assert any("급부역할이 이전과 달라짐. 이번 값을 씀" in n and "2줄" in n and "이전 주급부, 이번 대등복합" in n
               for n in report.notes)


def test_changed_amount_is_not_linked():
    store = rerun_store()
    before = {r["급부ID"] for r in benefits_named(store, "가나입원")}
    report = again(store, Scripted({"가나입원": [item("가나입원보험금", "2만원", "질병 입원"), item("가나수술보험금", "100만원")]}))
    after = benefits_named(store, "가나입원")
    assert before.isdisjoint(r["급부ID"] for r in after)                        # 금액이 달라 같은 급부로 보지 않는다
    assert {r["원시급부명"] for r in after} == {"가나입원보험금(질병 입원)"}
    assert report.rerun["이은 급부ID"] == 0 and report.rerun["잃은 줄"] == 2 and report.rerun["얻은 줄"] == 2


def test_two_candidates_on_each_side_are_not_linked():
    two = {"가나입원": [item("가나입원보험금", "3만원", "질병"), item("가나입원보험금", "3만원", "재해"), item("가나수술보험금", "100만원")]}
    store = rerun_store(Scripted(two))
    before = {r["급부ID"] for r in benefits_named(store, "가나입원")}
    assert len(before) == 4
    report = again(store, Scripted({"가나입원": [item("가나입원보험금", "3만원", "질병 입원"), item("가나입원보험금", "3만원", "재해 입원"),
                                               item("가나수술보험금", "100만원")]}))
    after = {r["급부ID"] for r in benefits_named(store, "가나입원")}
    assert len(after) == 4 and before.isdisjoint(after)                         # 어느 줄이 어느 줄인지 알 수 없어 잇지 않는다
    assert report.rerun["이은 급부ID"] == 0


def test_confirmed_row_of_an_excluded_benefit_is_kept_and_logged():
    store = rerun_store()
    before = benefits_named(store, "가나수술")
    report = again(store, Scripted(low={"가나수술보험금": 0.1}))               # 세 모델 모두 재추출 구간이라 "제외"로 끝난다
    assert report.written and report.errors == {}
    assert benefits_named(store, "가나수술") == before                          # 이전 확정 줄이 값 그대로 남았다
    kept = [l for l in store.read(["sys_작업로그"])["sys_작업로그"] if R.KEPT_ROW in str(l["사유"])]
    assert sorted(l["대상행ID"] for l in kept) == [r["급부ID"] for r in before]
    assert all((l["작업단계"], l["결과"], l["대상탭"]) == ("재추출", "반려", "sys_급부") for l in kept)
    assert all("제외됨" in l["사유"] and "100만원" in l["사유"] for l in kept)
    assert report.rerun["지킨 이전 줄"] == 2 and report.rerun["잃은 줄"] == 0
    assert any("이전 확정 줄 2줄을 그대로 둠" in n for n in report.notes)


def test_row_waiting_for_review_is_not_revived():
    store = rerun_store(Scripted(low={"가나수술보험금": 0.6}))                 # 처음부터 검토 대기로 들어간 줄
    assert len(benefits_named(store, "가나수술")) == 2
    report = again(store, Scripted(low={"가나수술보험금": 0.1}))
    assert report.written and benefits_named(store, "가나수술") == []
    assert report.rerun["지킨 이전 줄"] == 0
    assert any("검토 대기인 2줄은 되살리지 않음" in n for n in report.notes)


def test_benefit_missing_from_model_output_is_not_revived():
    store = rerun_store()
    report = again(store, Scripted({"가나입원": [item("가나입원보험금", "3만원", "질병")]}))   # 개정돼 없어졌을 수 있는 급부
    assert report.written and benefits_named(store, "가나수술") == []
    assert report.rerun["지킨 이전 줄"] == 0 and report.rerun["잃은 줄"] == 2
    assert not any(R.KEPT_ROW in str(l["사유"]) for l in report.logs)


def test_rider_whose_calls_all_failed_keeps_its_rows():
    store = rerun_store()
    riders = sorted((r for r in store.read(["sys_특약"])["sys_특약"] if "다라진단" in r["원시특약명"]), key=lambda r: r["특약ID"])
    before = benefits_named(store, "다라진단")
    report = again(store, Scripted(fail=("다라진단",)))
    assert report.written and report.errors == {}
    assert sorted((r for r in store.read(["sys_특약"])["sys_특약"] if "다라진단" in r["원시특약명"]),
                  key=lambda r: r["특약ID"]) == riders                         # 특약 행도 사라지지 않는다
    assert benefits_named(store, "다라진단") == before
    logs = [l for l in store.read(["sys_작업로그"])["sys_작업로그"] if l["작업단계"] == "재추출" and l["결과"] == "반려"]
    assert {l["대상행ID"] for l in logs if l["대상탭"] == "sys_특약"} == {r["특약ID"] for r in riders}
    assert {l["대상행ID"] for l in logs if l["대상탭"] == "sys_급부"} == {r["급부ID"] for r in before}
    assert report.rerun["지킨 이전 줄"] == 2 and not any("가리지 못해" in n for n in report.notes)


def test_dry_run_links_and_keeps_without_writing():
    store = rerun_store()
    sheet = store.read()
    calls = len(store.backend.calls)
    report = again(store, Scripted({"가나입원": [item("가나입원보험금", "3만원", "질병 입원"), item("가나수술보험금", "100만원")]},
                                   low={"가나수술보험금": 0.1}), dry_run=True)
    assert not report.written and all(kind == "get" for kind, _ in store.backend.calls[calls:])
    assert store.read() == sheet
    # 쓸 행에는 이은 ID와 지킨 이전 줄이 들어 있어, 급부ID가 시트와 같다
    assert {r["급부ID"] for r in report.rows["sys_급부"]} == {r["급부ID"] for r in sheet["sys_급부"]}
    assert report.rerun["이은 급부ID"] == 2 and report.rerun["지킨 이전 줄"] == 2


class ByTarget(Scripted):
    """판정 확률을 급부 이름과 대상 표기로 정하는 가짜 모델. low: {(급부 이름, 대상): 확률}."""

    def decide(self, model, input_text, questions):
        out = {}
        for key, q in questions.items():
            p = next((p for (name, target), p in self.low.items()
                      if f"'{name}'" in q["instructions"] and f"'{target}'" in q["instructions"]), 0.97)
            out[key] = Answer(True, None, {"true": p, "false": 1 - p})
        return out


def test_old_row_of_an_excluded_benefit_is_not_given_to_its_sibling():
    store = rerun_store()                                      # 시트: 가나입원보험금(질병) 3만원 (종형 2개)
    before = benefits_named(store, "가나입원")
    # 이전과 같은 이름의 항목은 제외되고, 괄호 앞부분과 금액이 같은 새 항목(재해)이 함께 나왔다
    report = again(store, ByTarget({"가나입원": [item("가나입원보험금", "3만원", "질병"), item("가나입원보험금", "3만원", "재해"),
                                               item("가나수술보험금", "100만원")]}, low={("가나입원보험금", "질병"): 0.1}))
    assert report.written and report.errors == {}
    after = benefits_named(store, "가나입원")
    assert [r for r in after if r["원시급부명"] == "가나입원보험금(질병)"] == before   # 이전 확정 줄이 그대로 남았다
    disaster = [r for r in after if r["원시급부명"] == "가나입원보험금(재해)"]
    assert len(disaster) == 2 and {r["급부ID"] for r in disaster}.isdisjoint(r["급부ID"] for r in before)
    assert report.rerun["이은 급부ID"] == 0 and report.rerun["지킨 이전 줄"] == 2 and report.rerun["얻은 줄"] == 2


def test_exact_old_row_of_an_excluded_benefit_is_kept_before_linking_by_amount():
    store = rerun_store(Scripted({"가나입원": [item("가나입원보험금", "3만원", "질병"), item("가나수술보험금", "100만원", "재해")]}))
    before = benefits_named(store, "가나수술")
    later = ByTarget({"가나입원": [item("가나입원보험금", "3만원", "질병"), item("가나수술보험금", "100만원", "재해"),
                                 dict(item("가나수술보험금", "100만원", "질병"), limit="최초 1회")]},
                     low={("가나수술보험금", "재해"): 0.1})
    report = again(store, later)
    after = benefits_named(store, "가나수술")
    assert [r for r in after if r["원시급부명"] == "가나수술보험금(재해)"] == before   # 질병 줄의 값이 재해 이름과 ID로 들어가지 않는다
    assert {r["지급횟수제한"] for r in after if r["원시급부명"] == "가나수술보험금(질병)"} == {"최초 1회"}
    assert report.rerun["이은 급부ID"] == 0 and report.rerun["지킨 이전 줄"] == 2


def test_kept_row_survives_the_same_exclusion_again():
    store = rerun_store()
    before = benefits_named(store, "가나수술")
    first = again(store, Scripted(low={"가나수술보험금": 0.1}))
    assert benefits_named(store, "가나수술") == before and first.rerun["지킨 이전 줄"] == 2
    # 같은 문서는 같은 제외가 또 나오기 쉽다. 앞 실행이 지킨 줄은 그 실행의 판정 기록으로 검토 대기가 되지 않는다
    second = job.run(Scripted(low={"가나수술보험금": 0.1}), store, TARGETS, INDEX, {"yoyak": RERUN_SUMMARY}.get,
                     datetime(2026, 12, 3, 16, 0, tzinfo=KST), read_thresholds=False, parts=("급부",))
    assert second.written and benefits_named(store, "가나수술") == before
    assert second.rerun["지킨 이전 줄"] == 2 and not any("검토 대기인" in n for n in second.notes)
    # 지킨 줄을 그 뒤 실행이 검토 구간으로 다시 썼으면 그때는 검토 대기다
    sheet = store.read()
    assert not {r["급부ID"] for r in before} & R.pending_benefits(sheet["sys_급부"], sheet["sys_특약"], sheet["sys_상품종형"],
                                                                 sheet["sys_작업로그"])
    job.run(Scripted(low={"가나수술보험금": 0.6}), store, TARGETS, INDEX, {"yoyak": RERUN_SUMMARY}.get,
            datetime(2026, 12, 10, 16, 0, tzinfo=KST), read_thresholds=False, parts=("급부",))
    sheet = store.read()
    assert {r["급부ID"] for r in before} <= R.pending_benefits(sheet["sys_급부"], sheet["sys_특약"], sheet["sys_상품종형"],
                                                               sheet["sys_작업로그"])


SCOPED_TARGETS = {"기관코드": "EPOST", "공시목록URL": "https://example.invalid/list", "상품": [
    {"모상품ID": "EPOST_GANA", "개정연월": "2606", "비교역할구분": "관문전용", "갱신유형": "갱신", "갱신주기년": 20,
     "환급유형": "표준형", "납입면제적용": False,
     "종형": [{"공시상품코드": "X1", "종형명": "간편가입형", "심사유형": "일반심사", "간편고지약칭": "일반"},
              {"공시상품코드": "X2", "종형명": "일반가입형", "심사유형": "일반심사", "간편고지약칭": "일반"}]}]}
SCOPED_INDEX = [{"기관": "EPOST", "상품코드": code, "상품명": "무배당 가나보험 2606", "판매시작일": "2026-06-17", "판매종료일": None,
                 "문서": "상품요약서", "해시": "same", "저장이름": "yoyak", "쪽수": 9} for code in ("X1", "X2")]
SCOPED_SUMMARY = """
===== 5쪽 =====
② 보험금 지급사유
■ 주계약
(보험가입금액 1,000만원 기준)
재해사망보험금 1,000만원
■ 무배당 가나입원특약(20년갱신형) 2606
[간편가입형]
(특약보험가입금액 1,000만원 기준) 간편 표
가나입원보험금 3만원
가나수술보험금 100만원
[일반가입형]
(특약보험가입금액 1,000만원 기준) 일반 표
가나입원보험금 3만원
가나수술보험금 100만원
③ 일반적 보험금 지급제한 사유
"""


class Scoped:
    """가입유형별로 갈린 표마다 돌려줄 급부를 정하는 가짜 모델. general: 일반가입형 표에서 가나수술보험금을 뽑는가."""

    def __init__(self, general=True, low=None):
        self.general, self.low = general, low or {}

    def generate(self, model, prompt, schema=None, temperature=0.0):
        if "가나입원" not in prompt.split("특약 이름: ", 1)[1].split("\n", 1)[0]:
            return {"base_amount": "1,000만원", "benefits": [item("재해사망보험금", "1,000만원")]}
        found = [item("가나입원보험금", "3만원")]
        if "간편 표" in prompt or self.general:
            found.append(item("가나수술보험금", "100만원", role="부수급부"))
        return {"base_amount": "1,000만원", "benefits": found}

    def decide(self, model, input_text, questions):
        out = {}
        for key, q in questions.items():
            p = next((p for name, p in self.low.items() if f"'{name}'" in q["instructions"]), 0.97)
            out[key] = Answer(True, None, {"true": p, "false": 1 - p})
        return out


def test_exclusion_in_one_table_does_not_revive_another_variants_row():
    store = SheetStore(MemoryBackend())
    first = job.run(Scoped(), store, SCOPED_TARGETS, SCOPED_INDEX, {"yoyak": SCOPED_SUMMARY}.get, NOW, read_thresholds=False,
                    parts=("급부",))
    assert first.written and len(benefits_named(store, "가나수술")) == 2
    simple = {r["특약ID"] for r in store.read(["sys_특약"])["sys_특약"] if r["종형ID"].startswith("EPOST_X1_")}   # 간편가입형
    # 간편가입형 표의 가나수술보험금은 제외되고, 일반가입형 표에서는 모델이 그 급부를 아예 뽑지 않았다
    report = job.run(Scoped(general=False, low={"가나수술보험금": 0.1}), store, SCOPED_TARGETS, SCOPED_INDEX,
                     {"yoyak": SCOPED_SUMMARY}.get, LATER, read_thresholds=False, parts=("급부",))
    assert report.written and report.errors == {}
    after = benefits_named(store, "가나수술")
    assert len(after) == 1 and after[0]["특약ID"] in simple                    # 간편가입형의 이전 확정 줄만 남는다
    assert report.rerun["지킨 이전 줄"] == 1 and report.rerun["잃은 줄"] == 1
    assert not any("어느 종형에 실렸는지" in n for n in report.notes)            # 조각마다 실린 종형을 가렸다


def test_scope_guess_that_disagrees_with_the_rows_is_not_trusted(monkeypatch):
    store = rerun_store()
    scopes = job._scopes
    # 조각마다 실린 종형을 가리는 규칙이 파이프라인과 갈렸다고 치고, 한 조각을 첫 종형에만 실린 것으로 잘못 가린다
    monkeypatch.setattr(job, "_scopes", lambda pages, group, result: [
        [group[0].id] if i == 1 else m for i, m in enumerate(scopes(pages, group, result))])
    report = again(store, Scripted(low={"가나수술보험금": 0.1}))
    assert report.rerun["지킨 이전 줄"] == 2                                   # 모든 종형의 것으로 보고 지킨다
    assert any("조각 3개는 어느 종형에 실렸는지 가리지 못해" in n for n in report.notes)


def test_variants_sharing_a_summary_keep_the_same_id_tail():
    store = SheetStore(MemoryBackend())
    job.run(Scripted(), store, TARGETS, INDEX, {"yoyak": RERUN_SUMMARY}.get, NOW, read_thresholds=False, parts=("급부",),
            only=["P500129"])                                                  # 1종만 먼저 시트에 있다
    old = benefits_named(store, "가나입원")
    assert len(old) == 1
    # 두 종형을 함께 다시 뽑는다. 대상 표기가 바뀌고 가나입원보험금은 검토 구간이다. 판정 기록은 1종의 행에만 남는다
    report = again(store, Scripted({"가나입원": [item("가나입원보험금", "3만원", "질병 입원"), item("가나수술보험금", "100만원")]},
                                   low={"가나입원보험금": 0.6}))
    assert report.written and report.errors == {}
    after = benefits_named(store, "가나입원")
    owner = {r["특약ID"]: r["종형ID"] for r in store.read(["sys_특약"])["sys_특약"]}
    tails = {r["급부ID"][len(owner[r["특약ID"]]):] for r in after}
    assert len(after) == 2 and tails == {old[0]["급부ID"][len(owner[old[0]["특약ID"]]):]}   # 두 종형이 이어받은 꼬리를 함께 쓴다
    assert {r["원시급부명"] for r in after} == {"가나입원보험금(질병)"}
    assert {r["급부ID"] for r in after} <= set(Data(store.read()).pending_benefit)   # 화면이 두 종형 모두 검토 대기로 보인다
    assert report.rerun["이은 급부ID"] == 1
    assert any("같은 꼬리" in n for n in report.notes)


def test_run_without_benefits_is_untouched():
    store = rerun_store()
    sheet = store.read()
    calls = len(store.backend.calls)
    report = again(store, Scripted(low={"가나수술보험금": 0.1}), parts=("가입조건",))
    assert not report.written and report.rerun == {} and "재추출 전후" not in report.markdown({})
    assert store.read() == sheet
    assert [tabs for _, tabs in store.backend.calls[calls:-1]] == ["sys_특약"]   # 급부와 작업로그를 읽지 않는다
