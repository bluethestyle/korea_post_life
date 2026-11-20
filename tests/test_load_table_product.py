"""표 규칙으로 읽은 급부를 교차 확인만으로 시트에 쓰는 스크립트(scripts/load_table_product.py).

조각과 대조 줄은 실제 표의 말투만 본떠 지어낸 것이다. 담보 이름도 지어냈다.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import load_table_product as L  # noqa: E402
from postlife import ids  # noqa: E402
from postlife.extract import rerun as R  # noqa: E402
from postlife.extract import table_rules as rules  # noqa: E402
from postlife.extract.table_rules import Reading  # noqa: E402
from postlife.extract.tables import Cover, Rider, write_riders  # noqa: E402
from postlife.schema import TABS  # noqa: E402
from postlife.sheets_io import MemoryBackend, SheetStore  # noqa: E402
from postlife.snapshot import KST, write_snapshot  # noqa: E402
from postlife.validate import check_rows  # noqa: E402

ORG, CODE, VARIANT = "SAMSUNGFIRE", "Z1", "1종(가나형)"
VID = ids.variant_id(ORG, CODE, VARIANT)
NOW = datetime(2026, 11, 20, 18, 0, tzinfo=KST)
LATER = datetime(2026, 11, 20, 19, 0, tzinfo=KST)
DEATH = "가나 사고로 사망한 경우"                  # 결과 파일에 실리면 안 되는 지급사유 문장
DIAGNOSIS = ("보장개시일 이후 가나로 진단 확정된 경우 (최초 1회한 지급)\n"
             "※ 가나의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난 날의 다음날임\n"
             "※ 최초 보험가입후 1년 미만에 보험금 지급사유가 발생한 경우 50% 감액 지급")


def rider(title, covers, label="선택계약", page=10):
    return Rider(title, tuple(Cover(n, r, a, page + i) for i, (n, r, a) in enumerate(covers)), page, page + len(covers) - 1, label)


RIDERS = [
    rider("[갱신형]가나 사망", [("[갱신형]가나 사망", DEATH, "가입금액")], label="기본계약"),                    # R001 같음
    rider("[갱신형]가나 진단비", [("[갱신형]가나 진단비", DIAGNOSIS, "가입금액")], page=20),                    # R002 같음
    rider("[갱신형]다라 배상책임", [("[갱신형]다라 배상책임", "다라 사고로 배상책임을 진 경우", "대인, 대물 각 1억원 한도")],
          page=30),                                                                                       # R003 확신 없음
    rider("[갱신형]마바 수술비", [("[갱신형]마바 수술비", "마바로 수술을 받은 경우(수술 1회당)", "가입금액")], page=40),  # R004 지급률이 다름
    rider("[갱신형]사아 입원비", [("[갱신형]사아 입원비", "사아로 입원한 경우", "가입금액")], page=50),            # R005 대조 자료에 없음
    # R006 같은 이름, 같은 문구, 같은 쪽의 세부보장 둘. 같은 급부ID, 같은 내용의 줄이 두 번 나온다
    Rider("[갱신형]자차 통원비", (Cover("자차 통원비", "자차로 통원한 경우", "가입금액", 60),
                              Cover("자차 통원비", "자차로 통원한 경우", "가입금액", 60)), 60, 60, "선택계약"),
]


def crossline(number, rate="100", p1="-", r1="-", wait="0", limit="-"):
    return {"번호": number, "지급률": rate, "감액1기간": p1, "감액1지급률": r1, "감액2기간": "-", "감액2지급률": "-",
            "면책": wait, "지급한도": limit, "비고": "-"}


CROSS = [
    crossline("R001-1"),
    crossline("R002-1", p1="1년", r1="50", wait="90", limit="최초 1회한"),
    crossline("R003-1", rate="-", limit="대인, 대물 각 1억원 한도"),      # 대조 자료도 비율로 적지 못한 줄
    crossline("R004-1", rate="50", limit="수술 1회당"),
    crossline("R006-1"),
    crossline("R006-2"),
]


def targets(years=20):
    return {"기관코드": ORG, "공시목록URL": "https://example.invalid/list", "상품": [{
        "모상품ID": "GANA", "개정연월": "2611", "비교역할구분": "정밀비교", "갱신유형": "갱신", "갱신주기년": years,
        "환급유형": "표준형", "납입면제적용": False,
        "종형": [{"공시상품코드": CODE, "종형명": VARIANT, "심사유형": "일반심사", "간편고지약칭": "일반"}]}]}


INDEX = [{"기관": ORG, "상품코드": CODE, "상품명": "무배당 가나 건강보험", "판매시작일": "2026-10-01", "판매종료일": None,
          "문서": "상품요약서", "쪽수": 90, "해시": "h1", "저장이름": f"samsungfire_{CODE}_상품요약서",
          "급부표": f"samsungfire_{CODE}_급부표.json"}]


@pytest.fixture
def docs(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    write_riders(folder / f"samsungfire_{CODE}_급부표.json", RIDERS)
    (folder / "index.json").write_text(json.dumps(INDEX, ensure_ascii=False), encoding="utf-8")
    return folder


def cross(tmp_path, lines=CROSS):
    """대조 자료를 JSONL로 써서 compare_table_rules.load_table로 읽는다."""
    path = tmp_path / "cross.jsonl"
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n", encoding="utf-8")
    return {CODE: L.compare.load_table(path)}


def empty_store():
    return SheetStore(MemoryBackend())


def by_name(rows):
    return {r["원시급부명"]: r for r in rows}


# ---------------------------------------------------------------------------
# 판정
# ---------------------------------------------------------------------------

SURE = [Reading("가나 진단비", percent=100.0, waiting_days=90, limit="최초 1회한")]
SAME = ["R001-1", "100", "-", "-", "-", "-", "90", "최초 1회한", "-"]


def test_sure_and_same_is_confirmed():
    assert L.reasons_of((), SURE, SAME) == []


def test_limit_only_difference_is_still_confirmed():
    other = SAME[:7] + ["연간 2회한", "-"]
    assert any(d.startswith("한도:") for d in L.compare.differences(SURE, other))
    assert L.reasons_of((), SURE, other) == []


@pytest.mark.parametrize("other, kind", [
    (["R001-1", "50", "-", "-", "-", "-", "90", "최초 1회한", "-"], "지급률"),
    (["R001-1", "100", "1년", "50", "-", "-", "90", "최초 1회한", "-"], "감액"),
    (["R001-1", "100", "-", "-", "-", "-", "0", "최초 1회한", "-"], "면책"),
])
def test_rate_cut_or_wait_difference_is_review(other, kind):
    reasons = L.reasons_of((), SURE, other)
    assert [r.split(":", 1)[0] for r in reasons] == [kind]


def test_split_difference_is_review():
    lines = [Reading("가나 진단비", target="가", waiting_days=90), Reading("가나 진단비", target="나", waiting_days=90)]
    other = ["R001-1", "100", "-", "-", "-", "-", "90", "-", "-"]
    assert [r.split(":", 1)[0] for r in L.reasons_of((), lines, other)] == ["대상 나눔"]


def test_doubt_or_missing_number_is_review():
    assert L.reasons_of((rules.D_AMOUNT,), SURE, SAME) == [rules.D_AMOUNT]
    assert L.reasons_of((), SURE, None) == [L.NO_NUMBER]
    assert L.reasons_of((), None, SAME) == [L.NO_NUMBER]


# ---------------------------------------------------------------------------
# table_rules가 적는 값: 지급기준구분과 대조 번호
# ---------------------------------------------------------------------------

def test_benefit_rows_carry_the_basis_and_the_crosscheck_number():
    riders = RIDERS[:2] + [
        rider("다 치료비(연간1회한), 다 치료비(연간1회한)(기가입자용)",
              [("다 치료비(연간1회한), 다 치료비(연간1회한)(기가입자용)", "다로 치료를 받은 경우(연간 1회한)", "가입금액")], page=70),
        rider("라 치료비", [("라 치료비 지원", "보장개시일 이후 라암 또는 마암으로 치료를 받은 경우(연간 1회한)\n"
                                       "※ 라암의 보장개시일은 최초 계약일 또는 부활(효력회복)일부터 90일이 지난 날의 다음날이며, "
                                       "마암의 보장개시일은 계약일임", "가입금액의 20%"),
                        ("라 상담비", "라로 상담을 받은 경우", "가입금액")], page=80),
    ]
    out = rules.build_rows("V1", riders, renewal_years=20)
    assert check_rows("sys_급부", out.benefits) == {} and check_rows("sys_특약", out.riders) == {}
    assert all(b["지급기준구분"] == "가입금액비율" for b in out.benefits)
    assert all(list(b) == TABS["sys_급부"].header for b in out.benefits)          # 열 순서는 스키마를 따른다
    number = {b["원시급부명"]: out.numbers[b["급부ID"]] for b in out.benefits}
    assert number["[갱신형]가나 사망"] == ("R001-1",) and number["[갱신형]가나 진단비"] == ("R002-1",)
    # 이름이 여럿인 조각은 이름마다 급부 행이 생기지만 같은 번호를 가리킨다
    assert number["다 치료비(연간1회한)"] == number["다 치료비(연간1회한)(기가입자용)"] == ("R003-1",)
    # 대상별로 나눈 줄은 같은 세부보장의 번호, 다음 세부보장은 다음 번호
    assert number["라 치료비 지원(라암)"] == number["라 치료비 지원(마암)"] == ("R004-1",) and number["라 상담비"] == ("R004-2",)
    assert set(out.numbers) == {b["급부ID"] for b in out.benefits}


def test_same_benefit_id_from_two_covers_keeps_both_numbers():
    out = rules.build_rows("V1", RIDERS[5:], renewal_years=20)
    assert len(out.benefits) == 2 and len({b["급부ID"] for b in out.benefits}) == 1
    assert out.numbers == {out.benefits[0]["급부ID"]: ("R001-1", "R001-2")}


def test_basis_value_is_checked():
    out = rules.build_rows("V1", RIDERS[:1], renewal_years=20)
    row = dict(out.benefits[0])
    for value in ("금액", "가입금액비율", None, ""):
        assert check_rows("sys_급부", [{**row, "지급기준구분": value}]) == {}, value
    assert "허용값이 아님" in check_rows("sys_급부", [{**row, "지급기준구분": "비율"}])[row["급부ID"]][0]
    old = {k: v for k, v in row.items() if k != "지급기준구분"}          # 열이 없는 옛 행도 걸리지 않는다
    assert check_rows("sys_급부", [old]) == {}


# ---------------------------------------------------------------------------
# 시트에 쓰기
# ---------------------------------------------------------------------------

def test_load_writes_rows_and_review_logs(docs, tmp_path):
    store = empty_store()
    report = L.load(store, targets(), INDEX, docs, cross(tmp_path), NOW)
    assert report.written and report.errors == {}
    data = store.read()
    benefits = by_name(data["sys_급부"])
    assert len(data["sys_상품종형"]) == 1 and len(data["sys_특약"]) == 6
    assert len(data["sys_급부"]) == 6                                       # 같은 줄 둘은 하나만 남는다
    assert any("같은 행이 두 번 나와 하나만 씀" in n for n in report.notes)
    assert all(b["지급기준구분"] == "가입금액비율" for b in data["sys_급부"])
    for tab in L.TABS_WRITTEN:
        assert check_rows(tab, data[tab]) == {}

    status = {name: report.verdicts[b["급부ID"]]["상태"] for name, b in benefits.items()}
    assert status == {"[갱신형]가나 사망": "확정", "[갱신형]가나 진단비": "확정", "자차 통원비": "확정",
                      "[갱신형]다라 배상책임": "검토", "[갱신형]마바 수술비": "검토", "[갱신형]사아 입원비": "검토"}
    assert report.verdicts[benefits["[갱신형]사아 입원비"]["급부ID"]]["사유"] == [L.NO_NUMBER]
    assert report.verdicts[benefits["[갱신형]다라 배상책임"]["급부ID"]]["사유"] == [rules.D_AMOUNT]
    assert report.verdicts[benefits["[갱신형]마바 수술비"]["급부ID"]]["사유"][0].startswith("지급률:")
    assert report.counts[VID] == {"공시상품코드": CODE, "종형명": VARIANT, "특약": 6, "급부": 6, "확정": 3, "검토": 3}

    # 검토 줄은 판정 보류와 사람검토이관을 남기고, 확정 줄은 기록하지 않는다
    review = {bid for bid, v in report.verdicts.items() if v["상태"] == "검토"}
    logs = [r for r in data["sys_작업로그"] if r["작업단계"] in R.JUDGE_STEPS]
    assert {(r["대상행ID"], r["작업단계"]) for r in logs} == {(bid, step) for bid in review for step in ("판정", "사람검토이관")}
    assert all(r["호출모델"] == "교차 확인" and r["판정확률"] is None and r["결과"] == "보류" for r in logs)
    assert all(r["대상열"] == "기준지급금액만원, 감액개월1, 면책기간일수" and r["사유"].startswith("교차 확인: ") for r in logs)
    assert check_rows("sys_작업로그", data["sys_작업로그"]) == {}
    # 화면과 재추출이 보는 검토 대기가 검토 줄과 같다
    assert R.pending_benefits(data["sys_급부"], data["sys_특약"], data["sys_상품종형"], data["sys_작업로그"]) == review
    assert R.per_variant_runs(data["sys_작업로그"]) == {NOW.isoformat(timespec="seconds")}     # 종형마다 다시 뽑았다는 기록


@pytest.mark.parametrize("lines, reason", [
    ([crossline("R006-1", rate="50") if x["번호"] == "R006-1" else x for x in CROSS], "지급률: 규칙 [100.0] / 대조 50"),
    ([crossline("R006-2", rate="50") if x["번호"] == "R006-2" else x for x in CROSS], "지급률: 규칙 [100.0] / 대조 50"),
    ([x for x in CROSS if x["번호"] != "R006-1"], L.NO_NUMBER),
    ([x for x in CROSS if x["번호"] != "R006-2"], L.NO_NUMBER),
])
def test_one_row_from_two_covers_is_checked_against_both_numbers(docs, tmp_path, lines, reason):
    # 같은 급부ID, 같은 내용으로 줄어든 두 세부보장(R006-1, R006-2)은 어느 쪽의 대조가 어긋나도 검토다
    report = L.load(empty_store(), targets(), INDEX, docs, cross(tmp_path, lines), NOW, dry_run=True)
    verdict = next(v for v in report.verdicts.values() if v["번호"] == "R006-1, R006-2")
    assert verdict["상태"] == "검토" and verdict["사유"] == [reason]
    report = L.load(empty_store(), targets(), INDEX, docs, cross(tmp_path), NOW, dry_run=True)
    assert next(v for v in report.verdicts.values() if v["번호"] == "R006-1, R006-2")["상태"] == "확정"


def test_running_twice_keeps_the_same_rows_and_rider_limits(docs, tmp_path):
    store = empty_store()
    L.load(store, targets(), INDEX, docs, cross(tmp_path), NOW)
    first = store.read()
    riders = first["sys_특약"]
    riders[0].update({"최소가입금액만원": 100.0, "최대가입금액만원": 3000.0, "합산한도기준키": "가나합산"})
    store.write_tab("sys_특약", riders)
    report = L.load(store, targets(), INDEX, docs, cross(tmp_path), LATER)
    assert report.written
    second = store.read()
    for tab in L.TABS_WRITTEN:
        assert len(second[tab]) == len(first[tab])
        assert check_rows(tab, second[tab]) == {}                         # 기본키 중복이 없다
    assert {r["급부ID"] for r in second["sys_급부"]} == {r["급부ID"] for r in first["sys_급부"]}
    kept = next(r for r in second["sys_특약"] if r["특약ID"] == riders[0]["특약ID"])
    assert (kept["최소가입금액만원"], kept["최대가입금액만원"], kept["합산한도기준키"]) == (100.0, 3000.0, "가나합산")
    review = {bid for bid, v in report.verdicts.items() if v["상태"] == "검토"}
    assert R.pending_benefits(second["sys_급부"], second["sys_특약"], second["sys_상품종형"], second["sys_작업로그"]) == review


def test_review_line_confirmed_later_is_no_longer_waiting(docs, tmp_path):
    store = empty_store()
    L.load(store, targets(), INDEX, docs, cross(tmp_path), NOW)
    data = store.read()
    stay = by_name(data["sys_급부"])["[갱신형]사아 입원비"]["급부ID"]
    assert stay in R.pending_benefits(data["sys_급부"], data["sys_특약"], data["sys_상품종형"], data["sys_작업로그"])

    report = L.load(store, targets(), INDEX, docs, cross(tmp_path, CROSS + [crossline("R005-1")]), LATER)
    assert report.verdicts[stay]["상태"] == "확정"
    data = store.read()
    pending = R.pending_benefits(data["sys_급부"], data["sys_특약"], data["sys_상품종형"], data["sys_작업로그"])
    assert stay not in pending and len(pending) == 2
    passed = [r for r in report.logs if r["대상행ID"] == stay]
    assert [(r["작업단계"], r["결과"], r["호출모델"], r["판정확률"]) for r in passed] == [("판정", "통과", "교차 확인", None)]
    # 다른 확정 줄은 이번에도 기록하지 않는다
    assert {r["대상행ID"] for r in report.logs if r["결과"] == "통과" and r["작업단계"] == "판정"} == {stay}


def test_renewal_variant_without_period_is_not_written(docs, tmp_path):
    store = empty_store()
    report = L.load(store, targets(years=None), INDEX, docs, cross(tmp_path), NOW)
    assert not report.written and set(report.errors) == {"sys_상품종형", "sys_특약"}
    assert all(store.read()[tab] == [] for tab in (*L.TABS_WRITTEN, "sys_작업로그"))


def test_dry_run_and_bad_benefit_rows(docs, tmp_path, monkeypatch):
    store = empty_store()
    report = L.load(store, targets(), INDEX, docs, cross(tmp_path), NOW, dry_run=True)
    assert not report.written and report.done == {VID} and store.read()["sys_급부"] == []
    # 급부 행 하나가 형식 검사에 걸리면 그 행만 빼고 쓴다
    real = rules.benefit_row

    def broken(rider_id, reading, role, page):
        row = real(rider_id, reading, role, page)
        return {**row, "급부역할": "모름"} if reading.name.startswith("[갱신형]마바") else row

    monkeypatch.setattr(rules, "benefit_row", broken)
    report = L.load(store, targets(), INDEX, docs, cross(tmp_path), NOW)
    assert report.written and report.errors == {}
    names = {r["원시급부명"] for r in store.read()["sys_급부"]}
    assert "[갱신형]마바 수술비" not in names and len(names) == 5
    dropped = [r for r in report.logs if r["작업단계"] == "코드대조"]
    assert len(dropped) == 1 and dropped[0]["결과"] == "반려"


def test_main_with_snapshot_writes_counts_without_table_sentences(docs, tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshot"
    write_snapshot({name: [] for name in TABS}, snapshot)
    target_file = tmp_path / "targets.json"
    target_file.write_text(json.dumps(targets(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(L, "CROSSCHECK", {CODE: tmp_path / "cross.jsonl"})
    cross(tmp_path)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    result = tmp_path / "result" / "extract.json"
    assert L.main(["--docs", str(docs), "--targets", str(target_file), "--snapshot", str(snapshot), "--result", str(result)]) == 0
    body = json.loads(result.read_text(encoding="utf-8"))
    assert body["종형"][VID]["급부"] == 6 and body["시트에 씀"] is False and body["형식 오류"] == {}
    assert {v["상태"] for v in body["verdicts"].values()} == {"확정", "검토"}
    text = result.read_text(encoding="utf-8") + summary.read_text(encoding="utf-8")
    assert f"| {CODE} | {VARIANT} | 6 | 6 | 3 | 3 |" in text
    for sentence in (DEATH, "진단 확정된 경우", "보장개시일은 최초 계약일"):
        assert sentence not in text
