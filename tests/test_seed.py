"""시트에 넣은 기초 자료 초안(data/seed)이 열 정의와 맞는지 확인한다."""
import itertools
import json
from pathlib import Path

from postlife import config
from postlife.site.compare import GROUP_ORDER
from postlife.validate import check_rows

SEED = Path(__file__).resolve().parents[1] / "data" / "seed"

# 비교 기준 단위(만원). 진단 1,000, 수술 100, 입원과 통원 1(기획 3.3). 치료비는 100이고, 허가치료비(표적, 면역, 양성자)와
# 주요치료비는 1,000이다(docs/progress.md "구현하면서 정한 것" 11번). 항암호르몬약물허가치료비는 확장안 9절 10번대로 100이다.
UNITS = {"진단": 1000.0, "수술": 100.0, "입원": 1.0, "통원": 1.0}
TREATMENT_HIGH = ("주요치료비", "표적항암약물허가치료비", "면역항암약물허가치료비", "항암양성자·중입자방사선치료비")
# 확장안(docs/proposals/표준담보사전_확장안.md) 13절 2번이 정한 예외: 1일 1회 정액으로 주는 일당 꼴만 담아 1만 원
UNIT_EXCEPTIONS = {"STD_CV_TX_REHAB": 1.0}
# ID 규칙 STD_대분류_유형_세부의 대분류 머리
ID_HEAD = {"암보장": "STD_CA_", "뇌혈관보장": "STD_BR_", "심장보장": "STD_HT_", "뇌심장보장": "STD_CV_", "공통보장": "STD_CM_"}


def load(tab):
    return [json.loads(l) for l in (SEED / f"{tab}.jsonl").read_text(encoding="utf-8").splitlines() if l]


def test_seed_rows_follow_schema():
    for tab in ("hum_표준담보사전", "hum_표준질병군", "hum_기준값"):
        assert check_rows(tab, load(tab)) == {}, tab


def expected_unit(row):
    if row["표준담보ID"] in UNIT_EXCEPTIONS:
        return UNIT_EXCEPTIONS[row["표준담보ID"]]
    if row["급부유형"] == "치료":
        return 1000.0 if row["표준담보명"].endswith(TREATMENT_HIGH) else 100.0
    return UNITS[row["급부유형"]]


def test_dictionary_size_and_units():
    rows = load("hum_표준담보사전")
    assert 40 <= len(rows) <= 100                    # 상한은 확장안 9절 3번
    wrong = {r["표준담보ID"]: r["비교기준단위만원"] for r in rows if r["비교기준단위만원"] != expected_unit(r)}
    assert wrong == {}
    assert all(r["급부유형"] == "치료" for r in rows if r["표준담보ID"] in UNIT_EXCEPTIONS)


def test_dictionary_groups_ids_and_names():
    rows = load("hum_표준담보사전")
    # 화면 3은 GROUP_ORDER 순서로 대분류를 보인다. 뇌심장보장은 심장보장 다음이다(확장안 9절 2번)
    assert {r["보장대분류"] for r in rows} <= set(GROUP_ORDER)
    assert GROUP_ORDER.index("뇌심장보장") == GROUP_ORDER.index("심장보장") + 1
    assert [k for k, _ in itertools.groupby(r["보장대분류"] for r in rows)] == [g for g in GROUP_ORDER if g in ID_HEAD]
    assert [r["표준담보ID"] for r in rows if not r["표준담보ID"].startswith(ID_HEAD[r["보장대분류"]])] == []
    # 판정 문항은 표준담보명을 선택지 이름으로 쓰므로 이름이 겹치면 답을 사전 행으로 되돌릴 수 없다
    names = [r["표준담보명"] for r in rows]
    assert len(names) == len(set(names))
    # 심혈관질환 진단비는 이름을 두고 쓰지 않는다(확장안 9절 15번)
    assert {r["표준담보ID"]: r["사용여부"] for r in rows}["STD_HT_DX_CARDIO"] is False


def test_thresholds_used_by_code_exist_in_seed():
    keys = {r["기준키"] for r in load("hum_기준값") if r["기준분류"] == "판정구간"}
    assert set(config.DEFAULT_THRESHOLDS) <= keys


def test_disease_ranges_are_ordered():
    for r in load("hum_표준질병군"):
        assert r["시작코드"] <= r["끝코드"]
