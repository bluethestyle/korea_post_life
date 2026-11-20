"""두 판독의 매핑 의견을 hum_담보매핑에 넣는 길 (scripts/apply_mapping_opinion.py, mapping.cross_check).
상품과 급부 이름은 지어낸 것이다."""
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pytest

from postlife import ids, sheets_io
from postlife.extract import mapping as M
from postlife.schema import TABS
from postlife.sheets_io import MemoryBackend, SheetStore, rows_to_values
from postlife.snapshot import KST
from postlife.validate import check_rows

ROOT = Path(__file__).resolve().parents[1]
DICTIONARY = [json.loads(l) for l in (ROOT / "data/seed/hum_표준담보사전.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()]
STD = {d["표준담보명"]: d["표준담보ID"] for d in DICTIONARY}
NOW = datetime(2026, 11, 20, 12, 0, tzinfo=KST)

_spec = importlib.util.spec_from_file_location("apply_mapping_opinion", ROOT / "scripts/apply_mapping_opinion.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

RIDER = "[갱신형][간편] 가나특약(1년50%)"          # 묶음 이름은 "가나특약"
BENEFITS = ["가나진단비(1년감액)", "다라진단비", "마바사망보험금", "사아입원비", "자차수술비", "카타통원비"]


def world():
    """상품 둘. 가나 상품(GANA_A)은 종형 둘이 같은 특약과 급부를 갖고, 다라 상품(DARA_B)은 종형 하나다."""
    variants, riders, benefits = [], [], []
    for vid, parent, org, code in (("V1", "GANA_A", "GANAORG", "GA001"), ("V2", "GANA_A", "GANAORG", "GA002"),
                                   ("W1", "DARA_B", "DARAORG", "DA001")):
        variants.append({"종형ID": vid, "모상품ID": parent, "기관코드": org, "공시상품코드": code, "공시상품명": f"상품 {vid}"})
        rid = ids.rider_id(vid, RIDER)
        riders.append({"특약ID": rid, "종형ID": vid, "특약계보키": ids.rider_lineage_key(RIDER), "담보구분": "선택특약",
                       "원시특약명": RIDER})
        benefits += [{"급부ID": ids.benefit_id(rid, b), "특약ID": rid, "원시급부명": b} for b in BENEFITS]
    return variants, riders, benefits


def opinion(no, benefit, claude, gemini, rider="가나특약"):
    return {"번호": no, "특약": rider, "급부": benefit, "claude": claude, "claude확신": "높음",
            "gemini": gemini, "gemini확신": "보통"}


OPINIONS = [
    opinion("K001", "가나진단비", "일반암 진단비", "일반암 진단비"),             # 같은 표준담보 → 자동확정
    opinion("K002", "다라진단비", "일반암 진단비", "유사암 진단비(통합)"),       # 다름 → 대기, 추천은 Claude
    opinion("K003", "마바사망보험금", M.NONE, M.NONE),                           # 둘 다 해당없음 → 대상외
    opinion("K004", "사아입원비", M.NONE, "질병 입원일당"),                      # 다름 → 대기, 추천은 제미나이
    opinion("K005", "자차수술비", "없는 담보", "질병 수술비"),                   # Claude 의견은 사전에 없음 → 대기
    # 카타통원비는 의견이 없다
]


def keyed(lines):
    return {(l["특약"], l["급부"]): l for l in lines}


def by_name(rows, vid="V1"):
    return {r["원시급부명"]: r for r in rows if r["공시상품명"] == f"상품 {vid}"}


def scope(variants, riders, benefits, parent="GANA_A"):
    vids = {v["종형ID"] for v in variants if v["모상품ID"] == parent}
    rids = {r["특약ID"] for r in riders if r["종형ID"] in vids}
    return ([v for v in variants if v["종형ID"] in vids], [r for r in riders if r["특약ID"] in rids],
            [b for b in benefits if b["특약ID"] in rids])


def test_kind_name_strips_leading_marks_and_reduction_marks_only():
    assert M.kind_name("[갱신형][간편] 가나  진단특약(1년50%)") == "가나 진단특약"
    assert M.kind_name("가나진단비 (1년 감액)(최초1회)") == "가나진단비(최초1회)"
    assert M.kind_name("가나 (180일감액) 다라수술비") == "가나 다라수술비"            # 가운데의 감액 표시도 뗀다
    assert M.kind_name("가나진단비( 1년 50% )") == "가나진단비"
    # 다른 괄호와 이름 가운데의 대괄호는 남긴다
    assert M.kind_name("가나진단비(갑상선암)[다라]") == "가나진단비(갑상선암)[다라]"
    assert M.kind_name("가나진단비(2년50%)") == "가나진단비(2년50%)"
    # 의견 파일을 만든 정규식과 같게, 맨 앞에 이어 붙은 대괄호 묶음만 뗀다
    assert M.kind_name("[갱신형] [간편] 가나") == "[간편] 가나"
    assert M.kind_name(None) == "" and M.kind_name("  가나 \t 다라 ") == "가나 다라"


def test_four_outcomes_and_rows_have_no_probability():
    variants, riders, benefits = scope(*world())
    r = M.cross_check(variants, riders, benefits, DICTIONARY, [], keyed(OPINIONS), NOW)
    assert check_rows("hum_담보매핑", r.rows) == {} and check_rows("sys_작업로그", r.logs) == {}
    rows = by_name(r.rows)
    got = {n: (row["검토상태"], row["추천표준담보ID"], row["확정표준담보ID"]) for n, row in rows.items()}
    assert got == {
        "가나진단비(1년감액)": ("자동확정", STD["일반암 진단비"], STD["일반암 진단비"]),
        "다라진단비": ("대기", STD["일반암 진단비"], None),
        "마바사망보험금": ("대상외", None, None),
        "사아입원비": ("대기", STD["질병 입원일당"], None),
        "자차수술비": ("대기", STD["질병 수술비"], None),
        "카타통원비": ("대기", None, None),
    }
    assert rows["가나진단비(1년감액)"]["추천표준담보명"] == "일반암 진단비"
    assert all(row["매핑확률"] is None and row["담당자메모"] is None for row in r.rows)
    assert len(r.rows) == 12                                  # 가나 상품의 종형 둘. 다라 상품은 고르지 않았다
    assert r.stats["자동확정"] == 2 and r.stats["대상외"] == 2 and r.stats["대기"] == 8 and r.stats["의견 없음"] == 2
    assert r.by_standard == {"일반암 진단비": 2}
    # 작업 로그: run과 같은 꼴에 호출모델만 교차 확인, 판정확률은 비운다
    assert {l["호출모델"] for l in r.logs} == {M.CROSS_CHECK} and all(l["판정확률"] is None for l in r.logs)
    steps = [(l["작업단계"], l["결과"]) for l in r.logs]
    assert steps.count(("판정", "통과")) == 2                 # 자동확정, 대상외 묶음 하나씩
    assert steps.count(("판정", "보류")) == 4 and steps.count(("사람검토이관", "보류")) == 4
    assert all(l["대상탭"] == "hum_담보매핑" for l in r.logs) and len(r.waiting) == 4


def test_names_not_in_the_dictionary_count_as_no_opinion():
    variants, riders, benefits = scope(*world())
    lines = [opinion("K001", "가나진단비", "없는 담보", "일반암 진단비"),
             opinion("K002", "다라진단비", "심혈관질환 진단비", "또 없는 담보"),     # 쓰지 않는 담보와 없는 담보
             opinion("K003", "마바사망보험금", "질병 입원일당", "없는 담보")]
    r = M.cross_check(variants, riders, benefits, DICTIONARY, [], keyed(lines), NOW)
    rows = by_name(r.rows)
    assert (rows["가나진단비(1년감액)"]["검토상태"], rows["가나진단비(1년감액)"]["추천표준담보ID"]) == ("대기", STD["일반암 진단비"])
    assert (rows["다라진단비"]["검토상태"], rows["다라진단비"]["추천표준담보ID"]) == ("대기", None)
    assert rows["마바사망보험금"]["추천표준담보ID"] == STD["질병 입원일당"]
    assert r.stats["사전에 없는 의견"] == 4
    assert [(u["번호"], u["판독"]) for u in r.unknown] == [("K001", "claude"), ("K002", "claude"), ("K002", "gemini"),
                                                          ("K003", "gemini")]
    assert "심혈관질환 진단비" in STD                          # 사전에는 있지만 사용여부가 거짓인 줄
    # 두 판독 모두 쓸 의견이 없는 다라진단비는 의견이 없는 급부와 같게 센다
    assert r.stats["의견 없음"] == 2 * 4 and r.stats["자동확정"] == 0


def test_benefits_without_opinion_wait_unless_a_row_already_exists():
    variants, riders, benefits = scope(*world())
    tail = next(b for b in benefits if b["원시급부명"] == "카타통원비")
    existing = [{"급부ID": tail["급부ID"], "공시상품명": "상품 V1", "원시특약명": RIDER, "원시급부명": "카타통원비",
                 "추천표준담보ID": STD["질병 입원일당"], "추천표준담보명": "질병 입원일당", "매핑확률": 0.91,
                 "확정표준담보ID": STD["질병 입원일당"], "검토상태": "자동확정", "담당자메모": None}]
    r = M.cross_check(variants, riders, benefits, DICTIONARY, existing, keyed(OPINIONS), NOW)
    assert tail["급부ID"] not in {row["급부ID"] for row in r.rows}         # 판정 모델이 정한 줄은 그대로 둔다
    assert r.stats["의견 없음"] == 2 and r.stats["의견 없음(기존 줄 둠)"] == 1
    other = by_name(r.rows, "V2")["카타통원비"]
    assert (other["검토상태"], other["추천표준담보ID"]) == ("대기", None)
    held = [l for l in r.logs if l["대상행ID"] == other["급부ID"]]
    assert [l["작업단계"] for l in held] == ["판정", "사람검토이관"] and "의견이 없어" in held[0]["사유"]


def sheet(monkeypatch, mapping_rows=()):
    """scripts/apply_mapping_opinion.py의 main이 시트 대신 메모리 시트를 쓰게 한다."""
    variants, riders, benefits = world()
    tabs = {"sys_상품종형": variants, "sys_특약": riders, "sys_급부": benefits, "hum_표준담보사전": DICTIONARY,
            "hum_담보매핑": list(mapping_rows)}
    backend = MemoryBackend({n: [list(TABS[n].header)] + rows_to_values(TABS[n], rows) for n, rows in tabs.items()})
    for key in ("GOOGLE_SERVICE_ACCOUNT_JSON", "SPREADSHEET_ID"):
        monkeypatch.setenv(key, "test")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(sheets_io.RestBackend, "from_env", classmethod(lambda cls: backend))
    return backend, benefits


def write_opinions(tmp_path, lines, name="opinion"):
    path = tmp_path / f"{name}.jsonl"
    path.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lines), encoding="utf-8")
    return path


def read(backend, tab):
    return SheetStore(backend).read([tab])[tab]


def test_rows_set_by_a_person_are_not_overwritten(monkeypatch, tmp_path):
    variants, riders, benefits = world()
    first = {b["원시급부명"]: b for b in benefits if b["특약ID"] == riders[0]["특약ID"]}

    def row(name, state, memo=None, std=None):
        return {"급부ID": first[name]["급부ID"], "공시상품명": "상품 V1", "원시특약명": RIDER, "원시급부명": name,
                "추천표준담보ID": std, "추천표준담보명": None, "매핑확률": None, "확정표준담보ID": std,
                "검토상태": state, "담당자메모": memo}

    people = [row("가나진단비(1년감액)", "수정", "담당자가 고침", STD["유사암 진단비(통합)"]),
              row("다라진단비", "승인 ", None, STD["일반암 진단비"]),
              row("마바사망보험금", "대상외", "대상외 확정: 범위 밖"),
              row("사아입원비", "보류")]                                  # 검토상태가 배치 값 밖
    backend, _ = sheet(monkeypatch, people)
    before = {r["급부ID"]: r for r in read(backend, "hum_담보매핑")}
    result = tmp_path / "out.json"
    assert S.main(["--opinion", str(write_opinions(tmp_path, OPINIONS)), "--products", "GANA_A",
                   "--result", str(result)]) == 0
    after = {r["급부ID"]: r for r in read(backend, "hum_담보매핑")}
    for bid, old in before.items():
        assert after[bid] == old
    body = json.loads(result.read_text(encoding="utf-8"))
    assert body["stats"]["보호되어 건너뜀"] == 4 and not {r["급부ID"] for r in body["rows"]} & set(before)
    assert len(after) == 12                                      # 가나 상품 12줄: 담당자 줄 4개와 새 줄 8개


def test_second_run_changes_nothing_and_other_products_are_untouched(monkeypatch, tmp_path, capsys):
    variants, riders, benefits = world()
    outside = next(b for b in benefits if b["특약ID"] == riders[2]["특약ID"])       # 다라 상품의 급부
    other = {"급부ID": outside["급부ID"], "공시상품명": "상품 W1", "원시특약명": RIDER, "원시급부명": outside["원시급부명"],
             "추천표준담보ID": None, "추천표준담보명": None, "매핑확률": 0.55, "확정표준담보ID": None,
             "검토상태": "대기", "담당자메모": None}
    backend, _ = sheet(monkeypatch, [other])
    path = write_opinions(tmp_path, OPINIONS)
    argv = ["--opinion", str(path), "--products=GANA_A"]
    assert S.main(argv) == 0
    once = read(backend, "hum_담보매핑")
    logs = read(backend, "sys_작업로그")
    assert len(once) == 13 and len(logs) == 10                   # 가나 상품 12줄과 다라 상품의 옛 줄
    assert next(r for r in once if r["급부ID"] == outside["급부ID"]) == other
    assert all(r["공시상품명"] != "상품 W1" for r in once if r["급부ID"] != outside["급부ID"])
    capsys.readouterr()
    assert S.main(argv) == 0
    assert read(backend, "hum_담보매핑") == once and read(backend, "sys_작업로그") == logs
    out = capsys.readouterr().out
    # 의견이 없어 첫 실행이 대기로 넣은 두 줄은 이제 있는 줄로 보고 그대로 둔다
    assert "바꿀 매핑 행이 없어" in out and '"지금과 같은 줄": 10' in out and '"의견 없음(기존 줄 둠)": 2' in out


def test_dry_run_snapshot_and_bad_inputs_do_not_write(monkeypatch, tmp_path):
    backend, _ = sheet(monkeypatch)
    path = write_opinions(tmp_path, OPINIONS)
    assert S.main(["--opinion", str(path), "--products", "GANAORG", "--dry-run"]) == 0
    assert read(backend, "hum_담보매핑") == [] and ("overwrite", "hum_담보매핑") not in backend.calls
    # 어느 종형에도 맞지 않는 값은 오타로 보고 멈춘다. 공시상품코드와 쉼표도 받는다
    assert S.main(["--opinion", str(path), "--products", "GA001,없는상품"]) == 2
    assert S.parse(["--opinion", "x", "--products", "GA001, GA002", "DA001"]).products == ["GA001", "GA002", "DA001"]
    chosen, unmatched = S.pick(world()[0], ["GA002", "DARAORG"])
    assert [v["종형ID"] for v in chosen] == ["V2", "W1"] and unmatched == []
    # 같은 묶음에 다른 의견이 두 번 나오는 파일은 읽지 않는다. 같은 의견이 되풀이되는 것은 받는다
    twice = write_opinions(tmp_path, OPINIONS + [opinion("K009", "가나진단비", "일반암 진단비", M.NONE)], "twice")
    assert S.main(["--opinion", str(twice), "--products", "GANA_A"]) == 2
    assert len(S.load_opinions(write_opinions(tmp_path, OPINIONS + [OPINIONS[0]], "repeat"))) == len(OPINIONS)
    with pytest.raises(ValueError):
        S.load_opinions(write_opinions(tmp_path, [{"번호": "K001", "특약": "가나특약", "급부": "가나진단비"}], "short"))
    assert read(backend, "hum_담보매핑") == []
    # 사본으로 돌면 --dry-run 없이도 쓰지 않는다
    snap = tmp_path / "snap"
    snap.mkdir()
    variants, riders, benefits = world()
    for name, rows in {"sys_상품종형": variants, "sys_특약": riders, "sys_급부": benefits,
                       "hum_표준담보사전": DICTIONARY, "hum_담보매핑": []}.items():
        (snap / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    result = tmp_path / "snap.json"
    assert S.main(["--opinion", str(path), "--products", "DARA_B", "--snapshot", str(snap), "--result", str(result)]) == 0
    body = json.loads(result.read_text(encoding="utf-8"))
    assert body["stats"]["대상 급부"] == 6 and body["stats"]["자동확정"] == 1 and body["unused"] == []
    assert read(backend, "hum_담보매핑") == []
