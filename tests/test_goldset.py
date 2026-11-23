import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "goldset" / "epost_goldset.jsonl"
FIELDS = ["번호", "영역", "상품과종", "특약급부명", "질문", "정답", "근거문서", "쪽수", "근거문구", "검수"]

_spec = importlib.util.spec_from_file_location("score_goldset", ROOT / "scripts/score_goldset.py")
sg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sg)


def test_goldset_shape():
    rows = [json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines() if l]
    assert len(rows) == 85 and len({r["번호"] for r in rows}) == 85
    assert all(list(r) == FIELDS and all(r[f] for f in FIELDS) for r in rows)
    assert Counter(r["영역"] for r in rows) == {"가입조건": 20, "보장금액·면책·감액": 30, "보험료": 25, "결합 제약": 10}
    # 문서에 없는 내용을 묻는 표본: 모델이 빈값으로 답하는지 보기 위함
    assert sum(r["정답"] == "문서에 없음" for r in rows) == 9


def test_every_goldset_reads_the_same_way():
    """채점 스크립트는 회사마다 같은 열과 숫자 번호를 전제로 읽는다(--gold, --numbers)."""
    files = sorted((ROOT / "data" / "goldset").glob("*.jsonl"))
    assert len(files) >= 4
    for path in files:
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert all(list(r) == FIELDS for r in rows), path.name
        numbers = [int(r["번호"]) for r in rows]
        assert len(set(numbers)) == len(numbers), path.name
    assert sg.GOLD == GOLD                                            # 기본 정답셋은 그대로 우체국


# ---- 지어낸 정답셋과 결과로 새 인자(--gold, --numbers, --area)와 종형 범위를 지킨다 ----

_PRODUCT = "가상생명 연습통합보험"


def _item(number, area, scope, name, answer, question="지어낸 질문"):
    return {"번호": str(number), "영역": area, "상품과종": f"{_PRODUCT} · {scope}", "특약급부명": name, "질문": question,
            "정답": answer, "근거문서": "상품요약서", "쪽수": "1", "근거문구": "지어낸 문구", "검수": "지어낸 예"}


def _benefit(rider, name, pay, limit="최초 1회한", wait=0, cut=(None, None)):
    return {"특약ID": rider, "원시급부명": name, "기준가입금액만원": 1000.0, "기준지급금액만원": pay, "지급횟수제한": limit,
            "면책기간일수": wait, "감액개월1": cut[0], "감액지급률1": cut[1], "감액개월2": None, "감액지급률2": None}


def _result(tmp_path):
    """간편가입형(1년)과 일반가입형 두 종형. 진단자금은 간편가입형에만 1년 미만 50% 감액이 있다."""
    types = [{"종형ID": "J1", "공시상품명": _PRODUCT, "종형명": "간편가입형(1년)"},
             {"종형ID": "J2", "공시상품명": _PRODUCT, "종형명": "일반가입형"},
             {"종형ID": "X1", "공시상품명": "가상생명 다른보험", "종형명": "단일"}]
    riders, benefits, conds = [], [], []
    for j in ("J1", "J2"):
        riders += [
            {"특약ID": f"{j}M", "종형ID": j, "원시특약명": "주계약", "담보구분": "주계약", "최소가입금액만원": 300.0, "최대가입금액만원": 1000.0},
            {"특약ID": f"{j}A", "종형ID": j, "원시특약명": "가상진단특약(KTA1.1) 무배당", "담보구분": "특약", "최소가입금액만원": None, "최대가입금액만원": None},
            {"특약ID": f"{j}B", "종형ID": j, "원시특약명": "가상다빈도특약(갱신형) 무배당", "담보구분": "특약", "최소가입금액만원": None, "최대가입금액만원": None},
            {"특약ID": f"{j}C", "종형ID": j, "원시특약명": "가상입원특약(1-30일) 무배당", "담보구분": "특약", "최소가입금액만원": None, "최대가입금액만원": None},
        ]
        benefits += [
            _benefit(f"{j}A", "가상진단자금(가상질환)", 1000.0, wait=90, cut=(12, 0.5) if j == "J1" else (None, None)),
            _benefit(f"{j}B", "디스크진단자금(디스크)", 10.0, cut=(24, 0.5)),
            _benefit(f"{j}C", "입원급여금(질병·재해)", 1.0, limit="1회 입원당 30일 한도", cut=(12, 0.5)),
        ]
        conds += [{"조건행ID": f"{j}-{i}", "종형ID": j, "특약ID": None, "보험기간구분": term, "납입기간구분": pay, "성별": sex,
                   "최저가입나이": low, "최고가입나이": high, "구간최대가입금액만원": top}
                  for i, (term, pay, sex, low, high, top) in enumerate([
                      ("90세만기", "10년납", "M", 15, 70, 1000.0), ("90세만기", "10년납", "M", 71, 79, 300.0),
                      ("종신", "20년납", "F", 15, 70, 1000.0), ("종신", "20년납", "F", 71, 80, 300.0)])]
    path = tmp_path / "result.json"
    rows = {"sys_상품종형": types, "sys_특약": riders, "sys_급부": benefits, "sys_가입조건": conds}
    path.write_text(json.dumps({"rows": rows}, ensure_ascii=False), encoding="utf-8")
    return path


_DIAG = "가상진단특약(KTA1.1) 무배당 · 가상진단자금"
_EASY = "간편가입형(0·1·2·3·4·5·10년)"
_ALL = "13개 가입유형 공통"
_GOLD_ITEMS = [
    _item(301, "보장금액·면책·감액", _EASY, _DIAG, "500만원"),
    _item(302, "보장금액·면책·감액", _ALL, _DIAG, "500만원"),
    _item(303, "보장금액·면책·감액", "일반가입형, 건강가입형(6~10년)", _DIAG, "1,000만원"),
    _item(304, "보장금액·면책·감액", "간편가입형(10년)", _DIAG, "500만원"),
    _item(305, "보장금액·면책·감액", _ALL, _DIAG, "최초 1회한"),
    _item(306, "보장금액·면책·감액", _ALL, "가상다빈도특약(갱신형) 무배당 · 디스크진단자금", "2년미만"),
    _item(307, "보장금액·면책·감액", _ALL, "가상다빈도특약(갱신형) 무배당 · 디스크진단자금", "1년미만"),
    _item(308, "보장금액·면책·감액", _ALL, "가상입원특약(1-30일) 무배당 · 입원급여금", "입원1일당 5,000원"),
    _item(309, "보장금액·면책·감액", _ALL, _DIAG, "계약일로부터 그날을 포함하여 90일이 지난 날의 다음 날"),
    _item(310, "보장금액·면책·감액", _ALL, _DIAG, "약관에서 정한 날"),
    _item(401, "가입조건", "간편가입형(1년)", "주계약", "79세", "주계약을 90세만기, 10년납으로 가입할 때 남자 피보험자의 가입최고나이는?"),
    _item(402, "가입조건", "간편가입형(1년)", "주계약", "80세", "주계약을 90세만기, 10년납으로 가입할 때 남자 피보험자의 가입최고나이는?"),
    _item(403, "가입조건", "전 가입유형 공통", "주계약", "만15세", "주계약의 피보험자 가입최저나이는?"),
    _item(404, "가입조건", "전 가입유형 공통", "주계약", "300만원~1,000만원", "피보험자 나이가 70세 이하일 때 주계약의 가입한도는?"),
    _item(405, "가입조건", "전 가입유형 공통", "주계약", "500만원", "피보험자 나이가 71세 이상일 때 주계약의 가입한도는?"),
    _item(406, "가입조건", "전 가입유형 공통", "가상진단특약(KTA1.1) 무배당", "만15세", "이 특약의 가입최저나이는?"),
    _item(407, "가입조건", "전 가입유형 공통", "주계약", "문서에 없음", "주계약을 80세만기로 가입할 때 가입나이는?"),
    _item(408, "가입조건", "전 가입유형 공통", "주계약", "월납", "이 상품의 보험료 납입주기는?"),
]


@pytest.fixture
def scored(tmp_path, capsys):
    gold = tmp_path / "gold.jsonl"
    gold.write_text("\n".join(json.dumps(i, ensure_ascii=False) for i in _GOLD_ITEMS) + "\n", encoding="utf-8")
    result = _result(tmp_path)

    def run(*args):
        assert sg.main(["--gold", str(gold), "--result", f"연습통합보험={result}", *args]) == 0
        lines = capsys.readouterr().out.splitlines()
        return {int(l.split()[0]): l for l in lines[:-1]}, lines[-1]
    return run


def _verdict(line):
    return line.split(" | ")[0].split(" ", 1)[1]


def test_numbers_pick_only_that_range(scored):
    lines, tally = scored("--numbers", "301-303,305")
    assert sorted(lines) == [301, 302, 303, 305]
    assert tally == str({"일치": 3, "불일치": 1})


def test_scope_scores_each_type_in_range(scored):
    lines, _ = scored("--numbers", "301-304")
    assert _verdict(lines[301]) == "일치"                           # 간편가입형만: 1년 미만 500만원이 있다
    assert _verdict(lines[302]) == "불일치" and "일반가입형" in lines[302]   # 공통인데 일반가입형에는 감액이 없다
    assert _verdict(lines[303]) == "일치"
    assert _verdict(lines[304]) == "대상 없음"                       # 간편가입형(10년)은 결과에 없다


def test_answers_without_money_are_checked(scored):
    lines, _ = scored("--numbers", "305-310")
    assert _verdict(lines[305]) == "일치" and "지급횟수제한" in lines[305]
    assert _verdict(lines[306]) == "일치" and "감액 24개월" in lines[306]
    assert _verdict(lines[307]) == "불일치"
    assert _verdict(lines[308]) == "일치" and "0.5" in lines[308]    # 원으로만 적힌 금액
    assert _verdict(lines[309]) == "일치" and "면책 90일" in lines[309]
    assert _verdict(lines[310]) == "직접 확인"                       # 맞춰 볼 값이 없으면 일치로 치지 않는다


def test_condition_area_checks_main_contract_age_and_limit(scored):
    lines, _ = scored("--area", "가입조건")
    assert sorted(lines) == list(range(401, 409))                   # 가입조건 영역만
    assert _verdict(lines[401]) == "일치"
    assert _verdict(lines[402]) == "불일치" and "79" in lines[402]
    assert _verdict(lines[403]) == "일치" and "종형 2개 모두" in lines[403]
    assert _verdict(lines[404]) == "일치" and "최저 300만원" in lines[404]
    assert _verdict(lines[405]) == "불일치"
    assert _verdict(lines[406]) == "직접 확인"                       # 특약의 가입조건은 채점하지 않는다
    assert _verdict(lines[407]) == "일치"                            # 80세만기 행이 없다
    assert _verdict(lines[408]) == "직접 확인"


def test_bad_arguments_stop(scored):
    with pytest.raises(SystemExit):
        scored("--numbers", "삼백")
    with pytest.raises(SystemExit):
        scored("--area", "보험료")


def test_reversed_numbers_stop_instead_of_scoring_everything(scored):
    """거꾸로 적은 범위(305-301)가 빈 묶음이 되어 번호 거름이 꺼지고 영역 전체를 채점하던 결함."""
    with pytest.raises(SystemExit):
        scored("--numbers", "305-301")
    with pytest.raises(SystemExit):
        scored("--numbers", "301,305-301")
    with pytest.raises(argparse.ArgumentTypeError):
        sg.parse_numbers("114-101")
    assert sg.parse_numbers("101-103,120") == {101, 102, 103, 120}


def test_result_without_that_product_is_not_scored(tmp_path, scored, capsys):
    """결과에 --result 글자가 든 상품이 없으면 빈 특약으로 채점하지 않고 "대상 없음"으로 둔다.

    고치기 전 스크립트는 종형 없는 빈 특약으로 채점해, 남의 상품 결과로도 "문서에 없음" 항목을 일치로 냈다.
    """
    scored("--numbers", "301")                                       # 정답셋 파일을 만든다
    rows = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))["rows"]
    rows["sys_상품종형"] = [t for t in rows["sys_상품종형"] if t["종형ID"] == "X1"]   # 다른 상품만 남긴다
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"rows": rows}, ensure_ascii=False), encoding="utf-8")
    assert sg.main(["--gold", str(tmp_path / "gold.jsonl"), "--result", f"연습통합보험={other}", "--numbers", "301,310"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3 and all(_verdict(l) == "대상 없음" and l.endswith("| 결과에 이 상품의 종형이 없음") for l in lines[:2])
    assert lines[-1] == str({"대상 없음": 2})


def test_scope_names():
    assert sg.scope_names("13개 가입유형 공통") is None and sg.scope_names("전 가입유형 공통") is None
    assert sg.scope_names("간편가입형(0·1·2·3·4·5·10년)") == {f"간편가입형({n}년)" for n in (0, 1, 2, 3, 4, 5, 10)}
    assert sg.scope_names("일반가입형, 건강가입형(6~10년)") == {"일반가입형"} | {f"건강가입형({n}년)" for n in range(6, 11)}


def test_pick_types_without_scope_mark():
    """"상품 · 범위" 꼴이 아닌 정답셋(우체국, 삼성화재): 이름, 번호 범위, 첫 종형 순서로 고른다."""
    types = [{"종형ID": f"T{n}", "종형명": name} for n, name in enumerate(["1종(간편가입)", "2종(간편가입)", "3종(일반가입)"], 1)]
    assert [t["종형ID"] for t in sg.pick_types("가상보험 2600 3종(일반가입)", types)] == ["T3"]
    assert [t["종형ID"] for t in sg.pick_types("가상보험 2600 1~2종 공통", types)] == ["T1", "T2"]
    assert [t["종형ID"] for t in sg.pick_types("가상보험 2600 (단일종)", types)] == ["T1"]


def test_benefit_without_amount_does_not_stop_scoring():
    """금액 하나로 담기지 않는 급부(지급기준구분 차등지급 따위)는 두 금액이 비어 있다. 채점이 멈추지 않고 금액 모음에서 건너뛴다."""
    rider = {"특약ID": "T1", "원시특약명": "가나특약"}
    plain = _benefit("T1", "가나보험금", 1000.0)
    empty = {**_benefit("T1", "가나보험금(차등)", None), "기준가입금액만원": None, "지급기준구분": "차등지급"}
    item = _item(1, "보장금액·면책·감액", "단일", "가나특약 · 가나보험금", "1,000만원")
    assert sg.score(item, [rider], [plain, empty])[0] == "일치"
    assert sg.score(item, [rider], [empty])[0] == "불일치"
