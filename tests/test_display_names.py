"""화면 용어 1단계(데이터 쪽)의 규약(docs/proposals/용어_대조표.md 적용 계획 1-1, 1-2).

- 화면 코드가 조건문, 아이콘 맵, CSS 클래스 맵, 탭 이동의 키로 쓰는 값은 글자 그대로 남는다(값을 바꾸면 화면의 판정 색, 아이콘,
  집계가 깨진다). 아래 KEPT 의 글자는 화면 코드(proto_src/console4, proto_src/graph)에 적힌 글자와 같아야 한다.
- 표시 이름 표(sales.json 과 graph.json 의 "표시명")가 그 값을 모두 덮고, 판정표의 항목마다 표시명이 있다.
- 대조표 교체 행의 지금 용어 가운데 데이터에서 바꾸기로 한 말이 다시 만든 자료 파일의 화면용 글자에 다시 들어오지 않는다.
  키로 남긴 값(KEPT)과 그 값이 머리말인 지도 행 이름은 허용 목록으로 뺀다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from postlife.site import console4 as C4
from postlife.site import insights as I
from postlife.site import sales as S
from postlife.site import terms
from postlife.validate import ALLOWED

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "proto_src" / "console4"
GRAPH = ROOT / "proto_src" / "graph" / "graph.json"
GRAPH_BUILD = ROOT / "proto_src" / "graph" / "build_data.py"

# ---------- 키로 남기는 값(1-1). 화면 코드가 이 글자로 분기한다 ----------
KEPT = {
    "가입 가능 상태": ("열림", "나이 자료 없음", "질문 자료 없음", "심사로 확인", "닫힘", "일부 나이만 열림"),
    "현황 표 라벨": ("우리 간편만 열림", "함께 열림", "우리 간편 닫힘", "간편 모두 닫힘", "자료 없음"),
    "현황 표 행 종류": ("입원", "수술만"),
    "판정 값": ("같음", "나음", "못함", "엇갈림", "판정 보류", "다름"),
    "판정 집계": ("나음", "같음", "못함", "엇갈림", "판정 보류", "단정 주의", "지급 형태 다름", "관계 담보로 덮음", "검토 대기",
              "우체국에 없음", "상대에 없음"),
    "판정 이름": ("우체국 나음", "우체국 못함", "같음", "우열을 매기지 않음", "우체국에만 있음", "우체국에 없음", "검토 대기",
              "판정 보류", "둘 다 없음"),
    "영업 인사이트 분류": ("관문 차이", "앞세울 강점", "관련 담보 안내", "조건 열위 방어", "개정 검토 후보"),
    "영업 인사이트 세부": ("G1", "G2", "G3", "A1", "A2", "Q1", "Q2", "Q3"),
    "비교역할": ("관문전용", "직전개정시연"),
    "탭": ("브리핑", "고객군과 시장", "가입 관문", "담보 비교", "영업 인사이트"),
    "개정 종류": ("신설", "변경", "종료"),
}
GRAPH_KEPT = ("관문전용", "직전개정시연", "대상외", "검토상태")
# 화면 이름이 바뀌는 값과 그 이름(대조표의 확정안. 사용자가 2026-11-24에 승인한 이름이 대조표보다 우선한다)
RENAMED = {
    "열림": "가입 가능", "닫힘": "가입 제한", "심사로 확인": "일반심사 대상", "나이 자료 없음": "가입나이 미수집",
    "질문 자료 없음": "고지항목 미수집", "일부 나이만 열림": "일부 나이만 가입 가능",
    "우리 간편만 열림": "우체국 간편만 가입 가능", "함께 열림": "함께 가입 가능", "우리 간편 닫힘": "우체국 간편 가입 제한",
    "간편 모두 닫힘": "간편 모두 가입 제한", "수술만": "통원수술",
    "같음": "동일", "나음": "우위", "못함": "열위", "엇갈림": "우열 혼재", "다름": "상이",
    "단정 주의": "단순 비교 불가", "지급 형태 다름": "지급 형태 상이", "관계 담보로 덮음": "관련 담보로 보장", "검토 대기": "검수 대기",
    "우체국에 없음": "우체국 미보유", "상대에 없음": "타사 미보유",
    "우체국 나음": "우체국 우위", "우체국 못함": "우체국 열위", "우열을 매기지 않음": "단순 비교 불가",
    "우체국에만 있음": "우체국 단독 보유", "둘 다 없음": "양사 미보유",
    "관문 차이": "인수기준 차이", "앞세울 강점": "우위 담보", "조건 열위 방어": "열위 담보", "개정 검토 후보": "미보유 담보",
    "관련 담보 안내": "관련 담보",
    "G1": "우체국만 가입 가능", "G2": "우체국만 가입 제한", "G3": "고지 범위 상이", "A1": "단독 보유 담보", "A2": "조건 우위",
    "Q1": "관련 담보 있음", "Q2": "미보유", "Q3": "조건 열위",
    "관문전용": "인수기준만 수집", "직전개정시연": "직전 개정 상품", "브리핑": "전체 요약", "가입 관문": "인수기준 비교", "종료": "삭제",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def committed():
    """커밋된 자료 파일(scripts/export_app_data.py, proto_src/graph/build_data.py 가 다시 만든 것)."""
    first = (SRC / "tab4.js").read_text(encoding="utf-8").split("\n", 1)[0]
    return {"sales.json": _load(SRC / "sales.json"), "gate.json": _load(SRC / "gate.json"),
            "combo.json": _load(SRC / "combo.json"), "cover.json": _load(SRC / "cover.json"),
            "d.json": _load(SRC / "d.json"), "graph.json": _load(GRAPH),
            "tab4.js": json.loads(first[len(C4.LINE_HEAD):-1])}


# ---------- 키 값은 그대로다 ----------
def test_key_values_stay_as_the_screen_code_reads_them():
    assert S.STATE_ORDER + (S.PARTIAL,) == KEPT["가입 가능 상태"]
    assert tuple(S.LABELS.values()) == KEPT["현황 표 라벨"]
    assert (S.HOSPITAL, S.SURGERY_ONLY) == KEPT["현황 표 행 종류"]
    assert (I.SAME, I.BETTER, I.WORSE, I.MIXED, I.HOLD, I.DIFF) == KEPT["판정 값"]
    assert tuple(C4.PAIR_KEYS) == KEPT["판정 집계"]
    assert tuple(C4.NAME_ORDER) == KEPT["판정 이름"] and C4.BOTH_NONE == "둘 다 없음"
    assert set(C4.VERDICT_NAME.values()) | {C4.BOTH_NONE} == set(KEPT["판정 이름"])
    assert S.CATEGORIES == KEPT["영업 인사이트 분류"] and set(S.CARD_ORDER) == set(S.CATEGORIES)
    assert S.CODES == KEPT["영업 인사이트 세부"] and set(S.CATEGORY) == set(S.CODES)
    assert S.GATE_ROLE == "관문전용" and set(KEPT["비교역할"]) <= ALLOWED[("sys_상품종형", "비교역할구분")]
    assert S.TABS == KEPT["탭"]
    assert S.REVISION_KINDS == KEPT["개정 종류"] and S.PENDING_COUNT == "검토 대기"
    # 관계 그래프: 비교역할과 미연결사유는 시트 값, 속성 이름은 시트 열 이름이다
    assert "대상외" in ALLOWED[("hum_담보매핑", "검토상태")]
    graph_src = GRAPH_BUILD.read_text(encoding="utf-8")
    assert "GATE_ONLY = '관문전용'" in graph_src and "'대상외'" in graph_src and "검토상태=" in graph_src


def test_committed_data_still_carries_the_key_values(committed):
    s, gate, cv = committed["sales.json"], committed["gate.json"], committed["tab4.js"]
    assert tuple(s["탭"]) == KEPT["탭"] and tuple(s["분류"]) == KEPT["영업 인사이트 분류"]
    assert tuple(s["라벨"]) == KEPT["현황 표 라벨"]
    assert tuple(gate["상태"]) == KEPT["가입 가능 상태"][:5]
    assert all(x["갈곳"] in KEPT["탭"] for b in s["기준별"].values() for x in b["브리핑"])
    assert all(set(n["탭"]) <= set(KEPT["탭"]) for n in s["주석"])
    assert {r["종류"] for m in s["지도"].values() for r in m["행"]} == set(KEPT["현황 표 행 종류"])
    # 행 이름은 종류 값이 머리말이다(화면 코드가 떼어 조회 조건의 선택지와 열 머리로 쓴다)
    assert all(r["이름"].startswith(r["종류"] + " ") for m in s["지도"].values() for r in m["행"])
    assert all(set(c["분류수"]) == set(KEPT["영업 인사이트 분류"]) | {"검토 대기"}
               for m in s["지도"].values() for line in m["칸"] for c in line)
    assert tuple(cv["판정차례"]) == KEPT["판정 이름"] and tuple(cv["판정표"]) == KEPT["판정 집계"]
    assert {k: v["판정"] for k, v in cv["판정표"].items()} == C4.VERDICT_NAME
    assert set(s["개정변동"]["수"]) == set(KEPT["개정 종류"]) | {"전체"}


# ---------- 표시 이름 표 ----------
def test_display_table_covers_every_key_value(committed):
    flat = terms.display_names()
    for group, values in KEPT.items():
        missing = [v for v in values if v not in flat]
        assert not missing, (group, missing)
    assert set(terms.DISPLAY_GROUPS) >= set(KEPT)
    for value, name in RENAMED.items():
        assert flat.get(value, terms.GRAPH_DISPLAY.get(value)) == name, value
    # 자료에 그대로 실린다(평면 맵. 같은 값이 구분마다 다른 이름을 가지는 경우가 없다)
    assert committed["sales.json"]["표시명"] == flat
    assert committed["graph.json"]["표시명"] == terms.graph_display_names()
    assert set(GRAPH_KEPT) <= set(committed["graph.json"]["표시명"])
    assert all(isinstance(v, str) and v for v in flat.values())


def test_flat_map_refuses_a_value_with_two_names():
    with pytest.raises(ValueError):
        terms.flat({"가": {"열림": "가입 가능"}, "나": {"열림": "가능"}})
    assert terms.flat({"가": {"열림": "가입 가능"}, "나": {"열림": "가입 가능"}}) == {"열림": "가입 가능"}


def test_verdict_table_entries_carry_the_new_name(committed):
    for data in (committed["cover.json"], committed["tab4.js"]):
        for key, entry in data["판정표"].items():
            assert entry["표시명"] == terms.DISPLAY[entry["판정"]], key
    names = [terms.DISPLAY[n] for n in committed["cover.json"]["판정차례"]]
    assert names == ["우체국 우위", "우체국 열위", "동일", "단순 비교 불가", "우체국 단독 보유", "우체국 미보유", "검수 대기",
                     "판정 보류", "양사 미보유"]


def test_detail_codes_reach_the_screen_only_as_names(committed):
    """세부 코드(G1 따위)는 키다. 화면에 보일 이름은 표시명과 포인트의 세부이름에 있고, 이름에는 코드가 들지 않는다."""
    s = committed["sales.json"]
    assert {c: s["표시명"][c] for c in S.CODES} == terms.DETAIL_NAMES == {c: S.DETAILS[c][1] for c in S.CODES}
    assert s["포인트"] and all(p["세부이름"] == s["표시명"][p["세부"]] for p in s["포인트"].values())
    assert all(x["세부"] in s["표시명"] for b in s["기준별"].values() for x in b["뺀포인트"])
    assert all(set(b["세부집계"]) <= set(S.CODES) for b in s["기준별"].values())
    assert not any(re.search(r"[GAQ]\d", v) for v in s["표시명"].values())


def test_graph_kinds_are_exported_with_screen_names(committed):
    g = committed["graph.json"]
    assert g["kinds"] == g["kindLabels"] == ["회사", "종형", "특약", "급부", "표준담보", "보장 대분류", "시장 동향"]
    # 0~5는 2026-11-24 용어 교체로 화면 이름이 된 글자 그대로다. 6~10은 스키마 개정 1단계에서 끝에 붙인 종류이고,
    # 자료 이름(ekinds)과 화면 이름(ekindLabels)이 다른 것은 결합제약(특약 부가 조건, 대조표 68)뿐이다
    assert g["ekinds"][:6] == g["ekindLabels"][:6] == ["판매", "포함", "매핑", "분류", "담보 관계", "발표"]
    assert g["ekinds"][6:] == ["보유", "결합제약", "개정", "언급 담보", "언급 상품"]
    assert g["ekindLabels"][6:] == ["보유", "특약 부가 조건", "개정", "언급 담보", "언급 상품"]


def test_user_picks_are_set_in_one_place():
    """사용자가 승인한 이름은 terms 에서만 정한다(이름이 바뀌면 이 값만 바꾸고 자료를 다시 만든다)."""
    assert set(terms.USER_PICKS) == {1, 3, 5, 8, 9, 40, 83, 120, 121, 122, 123, 128}
    assert terms.USER_PICKS == {1: "상품-영업 분석", 3: "전체 요약", 5: "인수기준 비교", 8: "관계 그래프", 9: "고객군별 가입 가능 현황",
                                40: "인수기준 차이", 83: "단순 비교 불가", 120: "우위 담보", 121: "열위 담보",
                                122: "미보유 담보", 123: "관련 담보", 128: "비교 요약지"}
    d = terms.DISPLAY
    assert d["브리핑"] == terms.TAB_SUMMARY and d["가입 관문"] == terms.TAB_UNDERWRITING
    assert d["단정 주의"] == d["우열을 매기지 않음"] == terms.NO_SIMPLE_COMPARE and d["앞세울 강점"] == terms.STRENGTH
    assert [d[c] for c in S.CATEGORIES] == [terms.GATE_DIFF_NAME, terms.STRENGTH, terms.RELATED_NAME, terms.DEFEND_NAME,
                                            terms.REVISE_NAME]
    assert S.AREA_SEGMENT == terms.SEGMENT_TABLE and terms.SEGMENT_TABLE in S.NOTES[0]["글"]
    assert terms.UNDERWRITING_RULE in S.NOTES[0]["출처"]
    assert all(terms.STRENGTH in S.TEMPLATES[t] for t in ("마_강점", "마_강점_요약없음", "마_강점_없음"))


# ---------- 바꾼 지금 용어가 자료에 다시 들어오지 않는다 ----------
# 대조표 교체 행 가운데 데이터에서 바꾼 말(괄호 안은 행 번호). 같은 글자가 키로 남은 값(KEPT)에 들면 그 값 전체가 같을 때만 허용한다
OLD_TERMS = [
    (r"브리핑", "3"), (r"가입 관문|관문", "5, 22, 33, 40"), (r"고객군 지도|고객군 지형|지도는|지도에서|지도를", "9, 10"),
    (r"(?<!상품 )개정과 시장", "11"),
    (r"열림|닫힘|닫힌|열린|열리는|닫혀|닫히", "23, 24, 27~31"), (r"심사로 확인|일반심사 확인", "25"),
    (r"질문", "42, 47, 48, 50"), (r"최근 소견", "46"), (r"묻습니다|묻는|묻지", "51"), (r"수술만", "53, 54"),
    (r"마지막 입원|마지막 수술", "56"), (r"넘음|넘게", "58"), (r"\d+(?:년|개월) 안", "59"),
    (r"나이 자료 없음", "62"), (r"가입나이(?:\([^)]*\))? 밖", "64"), (r"주계약 한도", "67"), (r"(?<!해약)환급 구조", "74"),
    (r"구조 다름", "75"), (r"(?:조건|우체국) (?:나음|못함)", "77, 78, 125"), (r"남녀 같음", "79"),
    (r"지급 형태 다름|다름", "80"), (r"엇갈림", "82"), (r"단정|우열을 매기지", "83, 84"), (r"특약 함께 판매|함께 팔|팝니다|팔아", "85, 189"),
    (r"우체국에만 있음|우체국만 가진", "87"), (r"우체국에 없음|우체국에 없는 담보", "88"), (r"상대에 없음", "89"),
    (r"둘 다 없음", "90"), (r"맞붙는", "92"), (r"상대", "93"), (r"우리", "95"), (r"견주|견준|견줄|견줬", "96"),
    (r"\d+쌍|쌍을|쌍은|쌍이|견준 쌍", "97"), (r"선택 종형", "98"), (r"관계 담보|덮음|덮습니다|덮일|덮는", "104, 105"),
    (r"지급 사유|면책 기간|감액 기간", "106"), (r"검토 대기", "110"), (r"매핑 대기|작업 로그", "111, 112"),
    (r"뺀 |빼고|뺐", "114"), (r"앞세울", "120"), (r"열위 방어", "121"), (r"개정 검토 후보", "122"),
    (r"따로 주는|따로 있는", "124, 191"), (r"시장 소식|소식은|소식이", "133"), (r"종료 \d", "136"),
    (r"일으킴|속함|보장분야", "148~153"), (r"이어진|이어지지", "176"), (r"\d+곳", "185"), (r"\d+칸", "186"), (r"\d+줄", "187"),
    (r"모은|모았", "190"), (r"청약 뒤|정해집니다", "193"), (r"무관하게", "194"), (r"고지 유형", "43"), (r"걸림", "39"),
    (r"멈춤|멈춘", "39"), (r"응대 카드|관계 지도|영업 분석 콘솔", "1, 8, 128"),
]
OLD = re.compile("|".join(f"(?:{p})" for p, _ in OLD_TERMS))
# 키 값(KEPT)과 시트 값. 값 전체가 이 글자이면 허용한다
ALLOWED_VALUES = {v for values in KEPT.values() for v in values} | set(GRAPH_KEPT)
# 화면에 그대로 보이지 않거나 원문을 옮긴 값의 열쇠: 틀 ID, 주석과 개정 담보의 열쇠, 보도 요약과 주소, 급부명(원문)
SKIP_KEYS = {"틀", "열쇠", "요약", "출처URL", "급부명", "limit", "exc"}


def _display_strings(name: str, obj) -> list[tuple[str, str]]:
    """자료 파일 하나의 화면용 글자(경로, 값). 관계 그래프는 원문을 옮긴 노드와 엣지를 빼고 종류 이름과 표시명, 요약만 본다."""
    if name == "graph.json":
        obj = {"kinds": obj["kinds"], "ekinds": obj["ekinds"], "kindLabels": obj["kindLabels"],
               "ekindLabels": obj["ekindLabels"], "표시명": list(obj["표시명"].values()), "summary": obj["summary"]}
    out: list[tuple[str, str]] = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k not in SKIP_KEYS:
                    walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
        elif isinstance(o, str):
            out.append((path, o))

    walk(obj, "$")
    return out


def _allowed(path: str, value: str) -> bool:
    if value in ALLOWED_VALUES:
        return True
    # 지도 행 이름의 머리말은 행 종류 값이다(화면 코드가 떼어 쓴다). 머리말을 뗀 나머지는 검사한다
    if re.search(r"\.지도\.[^.]+\.행\[\d+\]\.이름$", path) and value.startswith(f"{S.SURGERY_ONLY} "):
        return not OLD.search(value[len(S.SURGERY_ONLY) + 1:])
    return False


@pytest.mark.parametrize("name", ["sales.json", "gate.json", "combo.json", "cover.json", "d.json", "graph.json"])
def test_replaced_terms_do_not_come_back_in_regenerated_data(committed, name):
    hits = [(p, v) for p, v in _display_strings(name, committed[name]) if OLD.search(v) and not _allowed(p, v)]
    assert not hits, f"{name}: 대조표에서 바꾼 말이 남았다 {len(hits)}곳, 처음 {hits[:5]}"


def test_old_term_check_catches_a_reintroduced_word(committed):
    """검사가 실제로 잡는지: 문장에 지금 용어를 넣으면 걸리고, 키 값 자체와 지도 행 이름의 머리말은 걸리지 않는다."""
    s = json.loads(json.dumps(committed["sales.json"]))
    first = next(iter(s["기준별"].values()))["브리핑"][0]
    first["문장"] = "고객군 18칸 가운데 우리 간편만 열리는 곳은 없습니다."
    hits = [(p, v) for p, v in _display_strings("sales.json", s) if OLD.search(v) and not _allowed(p, v)]
    assert [v for _, v in hits] == [first["문장"]]
    assert _allowed("$.지도.전체.행[6].이름", "수술만 1~2년 전") and not _allowed("$.지도.전체.행[6].이름", "수술만 1~2년 안")
    assert _allowed("$.x", "우리 간편만 열림") and not _allowed("$.x", "우리 간편만 열림 2칸")
