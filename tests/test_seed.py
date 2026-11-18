"""시트에 넣은 기초 자료 초안(data/seed)이 열 정의와 맞는지 확인한다."""
import json
from pathlib import Path

from postlife import config
from postlife.validate import check_rows

SEED = Path(__file__).resolve().parents[1] / "data" / "seed"


def load(tab):
    return [json.loads(l) for l in (SEED / f"{tab}.jsonl").read_text(encoding="utf-8").splitlines() if l]


def test_seed_rows_follow_schema():
    for tab in ("hum_표준담보사전", "hum_표준질병군", "hum_기준값"):
        assert check_rows(tab, load(tab)) == {}, tab


def test_dictionary_size_and_units():
    rows = load("hum_표준담보사전")
    assert 40 <= len(rows) <= 60
    units = {r["급부유형"]: r["비교기준단위만원"] for r in rows if r["급부유형"] in ("진단", "수술", "입원")}
    assert units == {"진단": 1000.0, "수술": 100.0, "입원": 1.0}


def test_thresholds_used_by_code_exist_in_seed():
    keys = {r["기준키"] for r in load("hum_기준값") if r["기준분류"] == "판정구간"}
    assert set(config.DEFAULT_THRESHOLDS) <= keys


def test_disease_ranges_are_ordered():
    for r in load("hum_표준질병군"):
        assert r["시작코드"] <= r["끝코드"]
