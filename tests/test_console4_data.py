"""시안 4(proto_src/console4) 화면 자료의 규약: 실제 사본으로 만든 자료 파일의 열쇠, 형, 서로 가리키는 ID.

화면 코드(core.js, tab1~5.js)가 읽는 열쇠를 적었다. 규약은 "적어도 이 열쇠가 이 형으로 있다"이다. 열쇠가 지워지거나
형이 바뀌면(뜻이 바뀌면) 깨지고, 열쇠나 뒤 자리를 더하는 것은 통과한다. 규약은 두 자료에 똑같이 건다.
- export: scripts/export_app_data.py 와 같은 길(console4.export_texts)로 사본에서 메모리에 새로 만든 자료(내보내기 코드의 규약)
- committed: 저장소에 커밋된 자료 파일(proto_src/console4 의 sales.json, tab3.js, tab4.js, d.json 등. build 가 싣는 것)
커밋된 자료의 자료 시각이 사본과 같으면 새로 만든 것과 바이트까지 같아야 한다. 사본이 더 새것이면(주간 사본이 들어온 뒤)
그 시험만 건너뛰고 다시 만들라고 알린다. 합친 결과는 test_console4_build.py 가 본다.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from postlife.site import console4 as C4
from postlife.site import lineup
from postlife.site import sales as SA
from postlife.site.model import load

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "snapshot"
SRC = ROOT / "proto_src" / "console4"

pytestmark = pytest.mark.skipif(not (SNAPSHOT / "meta.json").exists(), reason="실제 사본(data/snapshot)이 없다")


# ---------- 규약 검사기 ----------
NUM = "num"           # int 나 float(bool 은 아님)
ANY = "any"           # 있기만 하면 된다


class Opt:
    """None 이거나 spec."""

    def __init__(self, spec):
        self.spec = spec


class Seq:
    """목록. 항목마다 spec."""

    def __init__(self, spec):
        self.spec = spec


class Map:
    """ID(또는 이름) 사전. 값마다 spec."""

    def __init__(self, spec):
        self.spec = spec


class Pos:
    """자리로 읽는 짧은 목록. 앞 자리마다 spec. 뒤에 자리를 더하는 것은 괜찮다."""

    def __init__(self, *specs):
        self.specs = specs


class One:
    """spec 여럿 가운데 하나."""

    def __init__(self, *specs):
        self.specs = specs


def check(v, spec, path: str = "$") -> list[str]:
    if spec is ANY:
        return []
    if spec is None:
        return [] if v is None else [f"{path}: null 이어야 한다({type(v).__name__})"]
    if isinstance(spec, Opt):
        return [] if v is None else check(v, spec.spec, path)
    if isinstance(spec, One):
        errs = [check(v, s, path) for s in spec.specs]
        return [] if any(not e for e in errs) else [f"{path}: 어느 꼴에도 맞지 않는다({errs[0][0]})"]
    if spec == NUM:
        ok = isinstance(v, (int, float)) and not isinstance(v, bool)
        return [] if ok else [f"{path}: 수가 아니다({type(v).__name__})"]
    if isinstance(spec, type):
        ok = isinstance(v, spec) and not (spec is int and isinstance(v, bool))
        return [] if ok else [f"{path}: {spec.__name__} 가 아니다({type(v).__name__})"]
    if isinstance(spec, dict):
        if not isinstance(v, dict):
            return [f"{path}: dict 가 아니다({type(v).__name__})"]
        errs = []
        for k, sub in spec.items():
            if k not in v:
                errs.append(f"{path}: 열쇠 {k!r} 가 없다")
            else:
                errs += check(v[k], sub, f"{path}.{k}")
        return errs
    if isinstance(spec, Seq):
        if not isinstance(v, list):
            return [f"{path}: list 가 아니다({type(v).__name__})"]
        return [e for i, x in enumerate(v) for e in check(x, spec.spec, f"{path}[{i}]")]
    if isinstance(spec, Map):
        if not isinstance(v, dict):
            return [f"{path}: dict 가 아니다({type(v).__name__})"]
        return [e for k, x in v.items() for e in check(x, spec.spec, f"{path}[{k!r}]")]
    if isinstance(spec, Pos):
        if not isinstance(v, list) or len(v) < len(spec.specs):
            return [f"{path}: 자리 {len(spec.specs)}개 이상인 list 가 아니다"]
        return [e for i, s in enumerate(spec.specs) for e in check(v[i], s, f"{path}[{i}]")]
    raise TypeError(f"모르는 spec: {spec!r}")


# ---------- sales.json (App.S) ----------
EVIDENCE = {"종형ID": str, "문서": Opt(str)}
POINT = {
    "포인트ID": str, "분류": str, "세부": str, "세부이름": str, "표준담보ID": Opt(str), "문장": str,
    "카드질문": Opt(str), "카드답": str, "머리말": int, "회사수": int, "비교종형ID": Seq(str), "근거": Seq(EVIDENCE),
    "목적": Seq(str), "구조다름": bool, "원문대조": bool, "원문대조글": Opt(str), "브리핑": bool, "점수": Opt(NUM),
    "관련기관코드": Seq(str),
}
BASE = {
    "맞붙는종형": Seq(str),
    "범위": {"상대": Seq({"종형ID": str, "머리말": int, "구조다름": bool}), "회사수": int, "머리말": int,
             "비교쌍": int, "뺀비교쌍": int, "뺀시사점": int, "문장": str},
    "관문": {"질문": str, "나이": str, "상태": str, "한도만원": Opt(NUM)},
    "포인트": Seq(str),
    "분류집계": Map(int),
    "세부집계": Map(int),
    "먼저": {"브리핑": Seq(str), "카드": Seq(str)},
    "뺀포인트": Seq({"분류": str, "세부": str, "표준담보ID": Opt(str), "비교종형ID": Seq(str), "사유": str}),
    "단정주의": Seq({"종류": str, "표준담보ID": str, "담보": str, "상대종형ID": Seq(str), "대표밖줄": dict, "문장": str,
                    "머리말": int, "근거": Seq(EVIDENCE)}),
    "개정검토": Seq({"대분류": str, "중분류": str, "담보수": int, "좁은담보만수": int,
                    "담보": Seq({"표준담보ID": str, "담보": str, "급부유형": str, "가진상대수": int, "가진상대": Seq(str),
                                 "가진종형ID": Seq(str), "우리상태": str, "좁은담보": list, "점수": Opt(NUM),
                                 "포인트ID": Opt(str)})}),
    "치료여정": {"행": Seq(str), "열": Seq(str),
                 "종형": Seq({"종형ID": str, "이름": str, "칸": Map(Map(int)), "담보": Map(Map(Seq(str))), "합계": dict})},
    "고지유형별": Seq({"열쇠": str, "기준": bool, "상대수": int, "상대코드": Seq(str), "종형수": int, "우리종형수": int,
                      "맞붙는종형수": int}),
    "보류요약": {"맞붙는종형": Seq(str), "공통담보쌍": int, "뺀쌍": int, "견준쌍": int, "사유별": dict,
                 "대분류": Seq({"대분류": str, "공통담보쌍": int, "뺀쌍": int, "견준쌍": int, "상대별": dict,
                               "기관별": Map({"공통담보쌍": int, "뺀쌍": int, "견준쌍": int})}),
                 "기관별": Map({"공통담보쌍": int, "뺀쌍": int, "견준쌍": int, "사유별": Map(int)})},
    "브리핑": Seq({"줄": str, "범위": str, "값": dict, "문장": str, "갈곳": str, "틀": Seq(str)}),
}
MAP_CELL = {
    "라벨": str, "보조": Opt(str), "닫힌사유": list, "회사": Map(str), "대표": Opt(str), "상대대표": Map(Opt(str)),
    "분류수": Map(Opt(int)), "자료없음": list, "열린종형": Map(Seq(str)), "관문기준": Opt(str), "관문포인트": Seq(str),
    "관문만수집": Seq({"기관코드": str, "종형ID": str, "이름": str, "안내": str}),
    "열린상대코드": Seq(str), "관문만열린상대코드": Seq(str), "닫힌상대코드": Seq(str), "모르는상대코드": Seq(str),
    "일부열린상대수": int, "일부열린상대코드": Seq(str), "일부열린나이": Map(Seq(Pos(int, int))), "일부나이로만열림": bool,
    "세부나이": int,
    "관문흐름": {"유형": Seq({"열쇠": str, "통과수": Seq(int), "멈춤": Map(Map(Seq(str)))}),
                 "종형": Map(Pos(int, str))},
}
SEG_MAP = {"성별": str, "갱신유형": Opt(str), "행": Seq({"종류": str, "since": Opt(NUM), "이름": str}),
           "열": Seq({"lo": int, "hi": int}), "칸": Seq(Seq(MAP_CELL)), "라벨별": Map(int),
           "고지유형": Seq({"열쇠": str, "상대수": int, "상대코드": Seq(str)}), "이력없음": Seq(MAP_CELL)}
VALUE_COUNT = Seq({"값": ANY, "상대수": int, "상대코드": Seq(str), "종형수": int})
LIMIT_STEP = {"lo": int, "hi": int, "max": Opt(NUM), "pend": ANY}
SALES = {
    "형식": int, "자료시각": str, "고지": str,
    "기준조건": {"나이": int, "성별": str, "이력": Opt(NUM)},
    "탭": Seq(str), "분류": Seq(str), "카드분류차례": Seq(str), "라벨": Seq(str),
    "목적": Seq({"이름": str, "기준": str, "값": Seq(str)}),
    "기준종형": Seq({"종형ID": str, "이름": str, "심사": str, "간편고지약칭": Opt(str), "갱신": Opt(str), "환급": Opt(str)}),
    "종형": Map({"회사": str, "기관코드": str, "종형명": str, "이름": str, "전체이름": str, "심사": str,
                 "간편고지약칭": Opt(str), "갱신": Opt(str), "환급": Opt(str), "적용시작일": Opt(str)}),
    "표준담보": Map({"이름": str, "대분류": str, "중분류": str, "급부유형": str}),
    "기준별": Map(BASE),
    "지도": {"전체": SEG_MAP, "갱신": SEG_MAP, "비갱신": SEG_MAP},
    "관문마디": {"차례": Seq(str), "전제": Seq(str), "멈춘값": Seq(str)},
    "고지유형속성": Map({"수술포함별": VALUE_COUNT, "중대질병수별": VALUE_COUNT, "가입나이별": {"M": VALUE_COUNT, "F": VALUE_COUNT}}),
    "주석": Seq({"열쇠": str, "탭": Seq(str), "글": str, "출처": str}),
    "한도표": Seq({"종형ID": str, "이름": str, "심사": str, "간편고지약칭": Opt(str), "갱신": Opt(str), "환급": Opt(str),
                  "성별같음": bool, "구간": {"M": Seq(LIMIT_STEP), "F": Seq(LIMIT_STEP)}}),
    "개정변동": {"짝": Seq({"전": str, "후": str, "신설": int, "변경": int, "종료": int}),
                 "담보": Seq({"열쇠": str, "담보": str, "종류": str, "항목": Seq(str), "종형ID": Seq(str)}),
                 "수": {"신설": int, "변경": int, "종료": int, "전체": int}, "관문변경": list, "가입나이변경": Seq(str)},
    "시장소식": {"주차": str, "건수": int, "연결": int, "분류별": Map(int), "인용안내": str,
                 "소식": Seq({"회사": str, "분류": str, "발표일자": str, "요약": str, "매체": str, "출처URL": str,
                              "출처표시": str, "주의표현": list, "인용": bool, "표준담보ID": Seq(str)})},
    "포인트": Map(POINT),
    "글": Seq(str),
    "표시명": Map(str),          # 화면 코드가 키로 쓰는 값 → 화면에 보일 이름(tests/test_display_names.py)
}

# ---------- tab3.js 의 자료 줄 (const T3) ----------
T3 = {
    "구성": {"P": Seq(str), "PB": Seq({"이름": str, "기준": str, "값": Seq(str)}),
             "S": Map(Pos(str, str, str, str)),
             "V": Map({"n": str, "m": Opt(str), "mn": Opt(str), "k": Pos(int, int, int), "K": Seq(list), "pk": Map(int),
                       "L": Opt(dict), "R": Seq(Pos(str)), "U": Seq(Pos(int)), "B": Seq(Pos(str, ANY, int)),
                       "X": Seq({"r": Seq(Pos(int, int, int)), "g": Seq(Pos(str, int, int, Opt(int))), "o": int}),
                       "C": Map(Map(Seq(Pos(int, int, int))))})},
    "관문": {"V": Seq(str), "ST": Seq(str), "Q": Seq(str), "A": Seq(str), "rule": dict,
             "I": Map({"회사": str, "이름": str, "심사": str, "질문": dict, "가입나이": {"M": ANY, "F": ANY}, "관문전용": bool,
                       "고지유형열쇠": str, "고지중대질병목록": Opt(str), "고지소견범위": Opt(str)}),
             "X": Seq({"s": Seq(Pos(int, int, int)), "라벨": str, "회사": Map(str), "닫힌사유": list}),
             "C": Map(Seq(Pos(int, int, int)))},
}

# ---------- tab4.js 첫 줄 (const CV) ----------
CV = {
    "t": str,
    "ben": Seq(Pos(str, int, str)),
    "rid": Seq(Pos(str, str)),
    "b": Map({"cols": Seq(str), "rows": Seq(Pos(str, Seq(One(int, dict)), Map(dict))), "pairs": int, "dropped": int,
              "보유기관코드": Map(Seq(str)), "판정기관코드": Map(Map(Seq(str))), "판정상대수": Map(Map(int)),
              "쌍판정": Map(Seq(Opt(Pos(str, Seq(str))))), "판정요약": Map(Map(int))}),
    "판정표": Map({"판정": str, "칩": str, "표시명": str}), "판정차례": Seq(str),
}

# ---------- d.json (const D) ----------
D = {
    "asOf": str,
    "orgs": Seq({"code": str, "name": str, "short": str, "업권": Opt(str)}),
    "lineup": Map(Pos(str)), "defaultGrade": str,
    "bands": Seq(Pos(int, int)), "stds": Seq(str),
    "std": Map({"name": str, "group": str, "mid": str, "type": str, "unit": Opt(NUM)}),
    "groups": Seq(str), "types": Seq(str), "compare": Seq(str), "pool": Seq(str),
    "variants": Map({"org": str, "product": str, "name": str, "grade": Opt(str), "uw": str, "renew": Opt(str),
                     "cycle": Opt(int), "start": Opt(str), "q": list, "ages": Seq(Pos(int, int)), "gap": Opt(dict)}),
    "riders": Map({"name": str, "kind": Opt(str), "max": Opt(NUM), "renew": ANY, "cycle": Opt(int)}),
    "benefits": Map({"tid": str, "name": str, "role": Opt(str), "base": Opt(NUM), "pay": Opt(NUM), "ratio": bool,
                     "wait": NUM, "red": list, "limit": Opt(str), "exc": Opt(str), "doc": Opt(str), "page": Opt(NUM),
                     "prob": Opt(NUM), "state": str, "pend": list}),
    "cells": Map(Map({"ids": Seq(str), "n": int})),
    "conds": Map(int),
    "payloads": Seq({"pres": Map(str), "rep": Map(Map(Pos(str, Opt(NUM), int, int))), "verd": Map(Seq(str)),
                     "ins": {"gap": Seq(str), "uniq": Seq(str), "skip": {"gap": int, "uniq": int, "diff": int},
                             "diff": Seq({"sid": str, "t": Seq(str), "worse": int, "better": int, "mixed": int,
                                          "alt": Seq(int)})}}),
}


# ---------- 자료 ----------
REGEN = "python scripts/export_app_data.py 와 python proto_src/console4/build.py 로 다시 만든다"


def unpack(texts: dict[str, str]) -> dict:
    """자료 파일 일곱의 글을 화면이 읽는 꼴(S, T3, CV, D)로 푼다."""
    t3 = json.loads(C4.tab3_data(texts["tab3.js"]))
    first = texts["tab4.js"].split("\n", 1)[0]
    assert first.startswith(C4.LINE_HEAD) and first.endswith(";"), "tab4.js 첫 줄이 const CV = {...}; 가 아니다"
    return {"texts": texts, "S": json.loads(texts["sales.json"]), "T3": t3,
            "CV": json.loads(first[len(C4.LINE_HEAD):-1]), "D": json.loads(texts["d.json"]),
            "combo": json.loads(texts["combo.json"]), "gate": json.loads(texts["gate.json"])}


def times_of(f: dict) -> dict[str, str]:
    return {"sales.json": f["S"]["자료시각"], "combo.json": f["combo"]["자료시각"], "gate.json": f["gate"]["자료시각"],
            "tab4.js": f["CV"]["t"], "d.json": f["D"]["asOf"]}


@pytest.fixture(scope="module")
def made():
    data = load(SNAPSHOT)
    out = unpack(C4.export_texts(data, SRC))
    out["data"] = data
    return out


@pytest.fixture(scope="module")
def committed():
    missing = [n for n in C4.FILES if not (SRC / n).exists()]
    if missing:
        pytest.fail(f"커밋된 자료 파일 {', '.join(missing)} 이 없다. {REGEN}")
    return unpack({n: (SRC / n).read_text(encoding="utf-8") for n in C4.FILES})


@pytest.fixture(scope="module", params=["export", "committed"])
def files(request):
    """규약을 거는 자료: 사본으로 새로 만든 것과 커밋된 파일 둘 다."""
    return request.getfixturevalue("made" if request.param == "export" else "committed")


def test_checker_allows_added_keys_and_rejects_removed_or_retyped(made):
    S = copy.deepcopy(made["S"])
    assert check(S, SALES) == []
    S["새열쇠"] = 1
    next(iter(S["포인트"].values()))["새열쇠"] = [1]
    S["기준종형"][0]["새열쇠"] = None
    assert check(S, SALES) == [], "열쇠를 더하는 것은 통과해야 한다"
    gone = copy.deepcopy(S)
    del next(iter(gone["기준별"].values()))["치료여정"]
    assert any("'치료여정' 가 없다" in e for e in check(gone, SALES))
    retyped = copy.deepcopy(S)
    next(iter(retyped["기준별"].values()))["포인트"] = "PT_x"
    assert check(retyped, SALES)
    flag = copy.deepcopy(S)
    next(iter(flag["포인트"].values()))["회사수"] = True     # bool 은 수가 아니다
    assert check(flag, SALES)
    t = [["STD_X", [0], {}, []]]
    assert check(t, Seq(Pos(str, Seq(One(int, dict)), Map(dict)))) == [] and check([["STD_X"]], Seq(Pos(str, list, dict)))


def test_files_and_hand_written_code_untouched(made):
    texts = made["texts"]
    assert set(texts) == set(C4.FILES)
    src3 = (SRC / "tab3.js").read_text(encoding="utf-8")
    a, b = src3.find(C4.MARK_A), src3.find(C4.MARK_B)
    out3 = texts["tab3.js"]
    assert out3.startswith(src3[:a + len(C4.MARK_A)]) and out3.endswith(src3[b:]), "tab3.js 의 표식 밖이 바뀌었다"
    src4 = (SRC / "tab4.src.js").read_text(encoding="utf-8")
    assert texts["tab4.js"] == C4.LINE_HEAD + texts["cover.json"] + ";\n" + src4
    # 자료 글이 script 를 닫거나 build 의 글 검사에 걸리지 않는다
    assert "</" not in C4.tab3_data(out3) and "</" not in texts["cover.json"]
    spec = importlib.util.spec_from_file_location("console4_build_for_test", SRC / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    for name in ("tab3.js", "tab4.js"):
        build.check_authored(name, texts[name])
    assert build.errors == []


def test_same_snapshot_time(made):
    t = made["data"].meta["snapshot_at"]
    assert made["S"]["자료시각"] == made["combo"]["자료시각"] == made["gate"]["자료시각"] == t
    assert made["CV"]["t"] == made["D"]["asOf"] == t


def test_committed_files_match_snapshot(made, committed):
    """커밋된 자료 파일이 커밋된 사본으로 새로 만든 것과 같은가(사본과 어긋난 자료를 페이지째 다시 합쳐 커밋하는 것을 막는다)."""
    times = times_of(committed)
    assert len(set(times.values())) == 1, f"커밋된 자료 파일의 자료 시각이 서로 다르다({times}). {REGEN}"
    t, t_snap = next(iter(times.values())), made["data"].meta["snapshot_at"]
    if t != t_snap:
        assert datetime.fromisoformat(t) < datetime.fromisoformat(t_snap), \
            f"커밋된 자료({t})가 커밋된 사본({t_snap})보다 새것이다. 커밋하지 않은 사본으로 만든 자료다. {REGEN}"
        pytest.skip(f"사본({t_snap})이 커밋된 자료({t})보다 새것이다. 화면 자료를 {REGEN}")
    stale = [n for n in C4.FILES if made["texts"][n] != committed["texts"][n]]
    assert not stale, f"커밋된 {', '.join(stale)} 가 같은 자료 시각({t})의 사본으로 새로 만든 것과 다르다. {REGEN}"


# 회사가 많을 때를 위해 더한 열쇠(2026-11-23). 세 회사 사본에서는 이 열쇠만 더해지고 나머지 열쇠의 값과 문장은 그대로여야 한다.
# 지도 열을 우리 기관의 가입나이로만 끊은 뒤(같은 날)로는 비갱신 지도의 열이 넷에서 둘로 줄었다(15세 열과 71~80세 열은 삼성화재
# 일반심사의 가입나이 16~70세가 만든 열이었다. 합친 열의 칸은 전의 16~65세 칸, 66~70세 칸과 바이트까지 같다)
ADDED_CELL = ("상대수", "열린상대수", "닫힌상대수", "모르는상대수", "관문만열린상대수",
              "열린상대코드", "관문만열린상대코드", "닫힌상대코드", "모르는상대코드",
              "일부열린상대수", "일부열린상대코드", "일부열린나이", "일부나이로만열림", "세부나이", "관문흐름")
ADDED_MAP = ("고지유형", "이력없음")
ADDED_TOP = ("관문마디", "고지유형속성")
ADDED_SCOPE = ("업권별",)
ADDED_BRIEF = ("열린상대수분포", "상대회사수", "상대보유분포", "상대보유요약", "일부열림칸수", "일부나이로만열림칸수",
               "나이자료없음회사코드", "관문차이상대코드", "구조다름회사코드")
ADDED_POINT = ("관련기관코드",)
ADDED_BASE = ("고지유형별",)
ADDED_PENDING = ("기관별",)      # 보류요약과 그 대분류 줄의 회사별 쌍 수(2026-11-23)


def without_added(S: dict) -> dict:
    S = copy.deepcopy(S)
    for k in ADDED_TOP:
        S.pop(k, None)
    for m in S["지도"].values():
        for k in ADDED_MAP:
            m.pop(k, None)
        for line in m["칸"]:
            for c in line:
                for k in ADDED_CELL:
                    c.pop(k, None)
    for p in S["포인트"].values():
        for k in ADDED_POINT:
            p.pop(k, None)
    for b in S["기준별"].values():
        for k in ADDED_BASE:
            b.pop(k, None)
        for k in ADDED_SCOPE:
            b["범위"].pop(k, None)
        for k in ADDED_PENDING:
            b["보류요약"].pop(k, None)
            for row in b["보류요약"]["대분류"]:
                row.pop(k, None)
        for line in b["브리핑"]:
            for k in ADDED_BRIEF:
                line["값"].pop(k, None)
    return S


def test_added_keys_are_the_only_change_on_three_companies(made, committed):
    """회사가 많을 때의 규칙(sales.py 의 MANY)은 세 회사 사본에서 더한 열쇠 말고는 아무것도 바꾸지 않는다.
    더한 열쇠를 뺀 sales.json 이 커밋된 것(더한 열쇠를 뺀 것)과 바이트까지 같아야 한다. 커밋된 자료가 더한 열쇠 전의 것이어도
    통과하므로, 자료를 다시 만들기 전에도 이 규칙만 따로 확인할 수 있다. 사본이 더 새것이면 건너뛴다."""
    if made["S"]["자료시각"] != committed["S"]["자료시각"]:
        pytest.skip("사본과 커밋된 자료의 자료 시각이 다르다")
    for k in ADDED_CELL:
        assert all(k in c for m in made["S"]["지도"].values() for line in m["칸"] for c in line), k
    assert C4.dumps(without_added(made["S"])) == C4.dumps(without_added(committed["S"]))
    for name in ("combo.json", "gate.json", "cover.json", "d.json", "tab3.js", "tab4.js"):
        assert made["texts"][name] == committed["texts"][name], name


def test_sales_shape(files):
    assert check(files["S"], SALES) == []


def test_sales_ids(files):
    S = files["S"]
    kinds, stds, pts = S["종형"], S["표준담보"], S["포인트"]
    bases = [b["종형ID"] for b in S["기준종형"]]
    assert bases and set(bases) <= set(kinds) and set(bases) <= set(S["기준별"])
    assert len(S["탭"]) == 5 and set(S["카드분류차례"]) == set(S["분류"])
    purposes = {p["이름"] for p in S["목적"]}
    for pid, p in pts.items():
        assert p["포인트ID"] == pid
        assert p["분류"] in S["분류"], pid
        assert p["표준담보ID"] is None or p["표준담보ID"] in stds, pid
        assert set(p["비교종형ID"]) <= set(kinds), pid
        assert all(g["종형ID"] in kinds for g in p["근거"]), pid
        assert 0 <= p["머리말"] < len(S["글"]), pid
        assert set(p["목적"]) <= purposes, pid
    for bid, b in S["기준별"].items():
        assert set(b["맞붙는종형"]) <= set(kinds), bid
        assert b["포인트"] and set(b["포인트"]) <= set(pts), bid
        assert set(b["먼저"]["브리핑"]) <= set(pts) and set(b["먼저"]["카드"]) <= set(pts), bid
        assert set(b["분류집계"]) <= set(S["분류"]), bid
        assert [x["종형ID"] for x in b["범위"]["상대"]] == b["맞붙는종형"], bid
        assert all(0 <= x["머리말"] < len(S["글"]) for x in b["범위"]["상대"]) and 0 <= b["범위"]["머리말"] < len(S["글"])
        assert all(x["표준담보ID"] in stds for x in b["단정주의"]), bid
        assert all(x["표준담보ID"] is None or x["표준담보ID"] in stds for x in b["뺀포인트"]), bid
        for g in b["개정검토"]:
            for x in g["담보"]:
                assert x["표준담보ID"] in stds and (x["포인트ID"] is None or x["포인트ID"] in pts), bid
                assert set(x["가진종형ID"]) <= set(kinds), bid
        grid = b["치료여정"]
        assert [x["종형ID"] for x in grid["종형"]] == [bid] + b["맞붙는종형"], bid
        for x in grid["종형"]:
            assert set(x["칸"]) == set(grid["행"]) and all(set(r) == set(grid["열"]) for r in x["칸"].values()), bid
            assert {s for r in x["담보"].values() for ss in r.values() for s in ss} <= set(stds), bid
        assert len(b["브리핑"]) == 5, bid
    for name, m in S["지도"].items():
        assert len(m["칸"]) == len(m["행"]) and all(len(line) == len(m["열"]) for line in m["칸"]), name
        assert set(m["라벨별"]) <= set(S["라벨"]), name
        for line in m["칸"]:
            for c in line:
                assert c["라벨"] in S["라벨"], name
                assert c["대표"] is None or c["대표"] in kinds, name
                assert set(c["관문포인트"]) <= set(pts), name
                assert {v for vs in c["열린종형"].values() for v in vs} <= set(kinds), name
                assert all(x["종형ID"] in kinds for x in c["관문만수집"]), name
    assert all(x["종형ID"] in kinds for x in S["한도표"])
    rev = S["개정변동"]
    assert all(x["후"] in kinds for x in rev["짝"])
    for x in rev["담보"]:
        assert set(x["종형ID"]) <= set(kinds), x["열쇠"]
        assert x["열쇠"] in stds or x["열쇠"].startswith("급부:"), x["열쇠"]
    news = S["시장소식"]
    assert news["건수"] == len(news["소식"]) == sum(news["분류별"].values())
    assert all(set(n["표준담보ID"]) <= set(stds) for n in news["소식"])
    assert S["고지"].strip()


def test_tab3_shape_and_ids(files):
    T, S = files["T3"], files["S"]
    assert check(T, T3) == []
    g = T["구성"]
    assert g["P"] == [p["이름"] for p in S["목적"]]
    assert list(g["V"]) == [b["종형ID"] for b in S["기준종형"]]
    assert set(g["S"]) <= set(S["표준담보"])
    for vid, v in g["V"].items():
        for x in v["X"]:
            assert all(r[0] < len(v["R"]) for r in x["r"]), vid
            assert all(s[0] in g["S"] and (s[3] is None or s[3] < len(v["B"])) for s in x["g"]), vid
        assert all(b[2] < len(v["R"]) for b in v["B"]), vid
        assert set(v["C"]) <= set(g["P"]), vid
        assert all(r[2] < len(v["X"]) and r[0] <= r[1] for per in v["C"].values() for rows in per.values() for r in rows), vid
    q = T["관문"]
    assert set(q["I"]) == set(q["V"]) and set(S["종형"]) & set(q["V"]) >= {b["종형ID"] for b in S["기준종형"]}
    for x in q["X"]:
        assert len(x["s"]) == len(q["V"])
        assert all(s[0] < len(q["ST"]) and s[1] < len(q["Q"]) and s[2] < len(q["A"]) for s in x["s"])
        assert x["라벨"] in S["라벨"]
    assert all(r[2] < len(q["X"]) for rows in q["C"].values() for r in rows)


def test_cover_shape_and_ids(files):
    V, S = files["CV"], files["S"]
    assert check(V, CV) == []
    assert list(V["b"]) == [b["종형ID"] for b in S["기준종형"]]
    assert all(b[1] < len(V["rid"]) for b in V["ben"])
    for vid, b in V["b"].items():
        assert b["cols"] == [vid] + S["기준별"][vid]["맞붙는종형"], vid
        for row in b["rows"]:
            sid, cells, prs = row[0], row[1], row[2]
            assert sid in S["표준담보"], (vid, sid)
            assert len(cells) == len(b["cols"]), (vid, sid)
            for c in cells:
                if isinstance(c, dict) and ("r" in c or "i" in c):
                    assert c["r"] is None or c["r"] < len(V["ben"]), (vid, sid)
                    assert all(i < len(V["ben"]) for i in c["i"]), (vid, sid)
            assert set(prs) <= set(b["cols"][1:]), (vid, sid)


def test_cover_carries_forms_only_for_benefits_without_amount(made):
    """금액 하나로 담기지 않는 급부(지급기준구분 차등지급 따위)가 있을 때만 cover.json 에 지급기준, 지급기준글, 금액없음글을 싣는다."""
    assert not {"지급기준", "지급기준글", "금액없음글"} & set(made["CV"])       # 세 회사 사본에는 그런 급부가 없다
    spec = importlib.util.spec_from_file_location("sales_book_for_cover_test", Path(__file__).with_name("test_site_sales.py"))
    book = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(book)
    from postlife.site import sales as SA
    from postlife.site.model import FORM_TEXT, Data
    b = book.Book()
    book.fill(b)
    b.t["hum_표준담보사전"].append(book.std("STD_CM_FORM", "공통보장", "시험 수술비", "수술"))
    b.ben(book.E1, "STD_CM_FORM", limit="수술 1회당")
    bid = b.ben(book.H1, "STD_CM_FORM", limit="연간 3회한")
    for r in b.t["sys_급부"]:
        if r["급부ID"] == bid:
            r.update({"지급기준구분": "차등지급", "기준가입금액만원": None, "기준지급금액만원": None})
    data = Data(b.t, {"snapshot_at": "2026-11-23T10:00:00+09:00"})
    sales_obj = json.loads(json.dumps(SA.export(data, relations=book.REL), ensure_ascii=False))
    cover = json.loads(C4.cover_text(C4.build_cover(data, sales_obj, book.REL)))
    assert check(cover, CV) == []
    forms = cover["지급기준"]
    assert set(forms.values()) == {"차등지급"} and len(forms) == 1
    i = int(next(iter(forms)))
    assert cover["ben"][i][3] is None and cover["ben"][i][4] is None and cover["ben"][i][7] == []
    assert cover["지급기준글"] == {"차등지급": FORM_TEXT["차등지급"]}
    assert set(cover["금액없음글"]) == {"기준", "감액", "지급액판정"}
    # 그 짝의 감액 항목은 원문 확인과 판정 보류다
    row = next(r for r in cover["b"][book.E1]["rows"] if r[0] == "STD_CM_FORM")
    items = {it[0]: it for it in row[2][book.H1]["it"]}
    assert items["감액"][2] == cover["금액없음글"]["감액"] and items["감액"][3] == "판정 보류"
    assert (items["지급 형태"][1], items["지급 형태"][2], items["지급 형태"][3]) == ("정액 지급(수술 1회당)", "차등지급", "다름")
    assert "단정 주의" in cover["b"][book.E1]["판정기관코드"]["STD_CM_FORM"]


def test_d_shape_and_ids(files):
    d, S = files["D"], files["S"]
    assert check(d, D) == []
    assert set(lineup.KEYS) <= set(d)
    codes = {o["code"] for o in d["orgs"]}
    assert {v["기관코드"] for v in S["종형"].values()} <= codes, "core.js 의 회사 짧은 이름(ORG_SHORT)이 빠진다"
    assert set(d["std"]) == set(d["stds"])
    assert set(d["compare"]) <= set(d["pool"]) <= set(d["stds"])
    assert d["defaultGrade"] in d["lineup"]
    assert {v for vs in d["lineup"].values() for v in vs if v} == set(d["variants"]) == set(d["cells"])
    assert all(v["org"] in codes for v in d["variants"].values())
    # lineup[등급][i] 는 orgs[i] 회사의 종형(고르지 못한 회사는 null)이고, 첫 자리는 우체국이다
    order = [o["code"] for o in d["orgs"]]
    for grade, vs in d["lineup"].items():
        assert len(vs) == len(order) and order[0] == "EPOST" and vs[0], grade
        assert all(v is None or (d["variants"][v]["org"] == order[i] and d["variants"][v]["grade"] == grade)
                   for i, v in enumerate(vs)), grade
    want = {f"{g}|{i}|{s}" for g in d["lineup"] for i in range(len(d["bands"])) for s in ("M", "F")}
    assert set(d["conds"]) == want and all(0 <= i < len(d["payloads"]) for i in d["conds"].values())
    for p in d["payloads"]:
        assert all(len(x) == len(d["stds"]) and set(x) <= set("nwuo") for x in p["pres"].values())
        assert all(r[0] in d["benefits"] and sid in d["pool"] for reps in p["rep"].values() for sid, r in reps.items())
        assert set(p["verd"]) == set(d["pool"])
    assert all(set(c["ids"]) <= set(d["benefits"]) for cs in d["cells"].values() for c in cs.values())
    assert all(b["tid"] in d["riders"] for b in d["benefits"].values())


# 화면 코드에서 const D 를 읽는 곳: DD.열쇠(core.js), App.D.열쇠, ctx.D.열쇠, D['열쇠']. 따옴표 안의 "D." 는 뺀다
SCREEN_JS = ["core.js", "tab1.js", "tab2.js", "tab3.js", "tab4.src.js", "tab5.js"]
D_READ = re.compile(r"""(?<![\w$'"])DD?\s*(?:\.\s*([A-Za-z_$][\w$]*)|\[\s*['"]([^'"]+)['"]\s*\])""")


def d_keys_read(text: str) -> set[str]:
    return {a or b for a, b in D_READ.findall(text)}


def test_screen_code_reads_only_d_keys_it_has(files):
    """화면 코드가 const D 에서 읽는 최상위 열쇠가 규약(D)과 d.json 에 있다. 지금 읽는 곳은 core.js 의 orgs(회사 짧은
    이름)뿐이다. 탭 2의 개정 변동 근거는 S.표준담보를, 담보 비교표와 관계 그림은 CV 를 읽는다."""
    sample = ("if (DD && Array.isArray(DD.orgs)) a = ctx.D.std[k]; b = App.D['lineup']; "
              "const c = { S, D: DD }; d = typeof D; e = 'D.no' + S.std + ODD.x")
    assert d_keys_read(sample) == {"orgs", "std", "lineup"}
    read: dict[str, list[str]] = {}
    for name in SCREEN_JS:
        text = (SRC / name).read_text(encoding="utf-8")
        if name == "tab3.js":   # 자료 줄(두 표식 사이)은 코드가 아니다
            a, b = text.find(C4.MARK_A), text.find(C4.MARK_B)
            text = text[:a] + text[b:]
        for k in d_keys_read(text):
            read.setdefault(k, []).append(name)
    assert set(read) <= set(D), f"화면 코드가 D 규약에 없는 열쇠를 읽는다: {read}. 규약(D)에 그 열쇠를 적는다"
    assert set(read) <= set(files["D"]), f"화면 코드가 읽는 D 열쇠가 d.json 에 없다: {read}"


# ---------- 회사 수와 무관한 화면을 위해 더한 값(2026-11-23) ----------
# 화면이 고른 비교 범위(상대 회사 일부)와의 교집합 크기만 세면 되게 하는 기관코드 목록과, 고지 유형 열쇠와 그 집계.
# 아래 검사기(added_value_errors)는 가상 자료(회사 20곳)로 내보낸 작업 폴더에도 그대로 건다
# (scripts/dev/build_console4_synthetic.py --work 폴더 로 남긴 자료를 unpack 해 넘긴다).
HOME = "EPOST"
CELL_CODES = {"열린상대코드": "열린상대수", "관문만열린상대코드": "관문만열린상대수", "닫힌상대코드": "닫힌상대수",
              "모르는상대코드": "모르는상대수", "일부열린상대코드": "일부열린상대수"}
PARTIAL = "일부 나이만 열림"
STOPS = ("고지 해당", "미확인", "일반심사 대상")     # 관문흐름의 멈춘 값(화면이 글자 그대로 보인다. 용어 대조표 25, 39, 91)
VERDICTS = ("나음", "같음", "못함", "엇갈림", "판정 보류", "단정 주의", "지급 형태 다름", "관계 담보로 덮음", "검토 대기",
            "우체국에 없음")
PAIR_ONLY = "상대에 없음"         # 쌍판정에만 있는 까닭(기둥 밖)
BOTH_NONE = "둘 다 없음"
# 쌍판정의 까닭마다 판정 이름과 칩(API.md "담보 비교의 쌍판정" 절). 화면은 이 표를 읽는다
PAIR_TABLE = {"나음": ("우체국 나음", "better"), "같음": ("같음", "same"), "못함": ("우체국 못함", "worse"),
              "엇갈림": ("우열을 매기지 않음", "diff"), "판정 보류": ("판정 보류", "unknown"),
              "단정 주의": ("우열을 매기지 않음", "diff"), "지급 형태 다름": ("우열을 매기지 않음", "diff"),
              "관계 담보로 덮음": ("우열을 매기지 않음", "diff"), "검토 대기": ("검토 대기", "unknown"),
              "우체국에 없음": ("우체국에 없음", "none"), PAIR_ONLY: ("우체국에만 있음", "only")}


def _flow_errors(at: str, c: dict, m: dict, S: dict, gate: dict, orgs: set) -> list[str]:
    """지도 칸의 관문흐름: 줄은 지도의 고지유형 차례, 통과수는 마디 다섯이고 늘지 않으며, 통과수 + 그 마디까지 멈춘 회사 = 상대수,
    멈춘 회사는 그 줄의 회사이고 겹치지 않는다. 전제 마디(최근 소견)에서는 일반심사와 모름 줄만 멈춘다(중대질병에서는 아무도 멈추지 않는다).
    멈춘 종형은 관문 나무의 종형이다."""
    errs: list[str] = []
    steps, premise = S["관문마디"]["차례"], S["관문마디"]["전제"]
    flow = c["관문흐름"]
    if [g["열쇠"] for g in flow["유형"]] != [g["열쇠"] for g in m["고지유형"]]:
        return [f"{at}: 관문흐름 줄이 지도의 고지유형과 다르다"]
    for meta, g in zip(m["고지유형"], flow["유형"]):
        if len(g["통과수"]) != len(steps) or not set(g["멈춤"]) <= {str(k) for k in range(len(steps))}:
            errs.append(f"{at} {g['열쇠']}: 마디 수가 {len(steps)} 가 아니다")
            continue
        seen: list[str] = []
        prev = meta["상대수"]
        for k, n in enumerate(g["통과수"]):
            here = g["멈춤"].get(str(k), {})
            if not set(here) <= set(STOPS) or any(not v or v != sorted(v) for v in here.values()):
                errs.append(f"{at} {g['열쇠']} 마디 {k}: 멈춘 값이나 목록이 규약과 다르다({here})")
            seen += [o for v in here.values() for o in v]
            if n > prev or n + len(seen) != meta["상대수"]:
                errs.append(f"{at} {g['열쇠']} 마디 {k}: 통과수 {n} 와 멈춘 회사 {len(seen)} 의 합이 상대수 {meta['상대수']} 와 다르다")
            if steps[k] in premise and here and not (k == 1 and g["열쇠"] in ("일반심사", "모름")):
                errs.append(f"{at} {g['열쇠']}: 전제 마디 {steps[k]} 에서 멈춘 회사가 있다")
            prev = n
        if len(seen) != len(set(seen)) or not set(seen) <= set(meta["상대코드"]):
            errs.append(f"{at} {g['열쇠']}: 멈춘 회사가 겹치거나 줄의 회사가 아니다")
    for vid, (k, v) in flow["종형"].items():
        if vid not in gate["종형정보"] or not 0 <= k < len(steps) or v not in STOPS:
            errs.append(f"{at}: 관문흐름 종형 {vid} {k} {v}")
    return errs
NOTICE_KEY = re.compile(r"^\d+(?:\.\d+)?·\d+(?:\.\d+)?·\d+(?:\.\d+)?$")
SECTORS = ("생명보험", "손해보험")


def _num_text(x) -> str:
    x = float(x)
    return str(int(x)) if x.is_integer() else f"{x:g}"


def _codes_ok(codes, orgs) -> bool:
    return codes == sorted(set(codes)) and set(codes) <= orgs and HOME not in codes


def added_value_errors(f: dict) -> list[str]:
    """더한 값의 규약. 목록 길이와 수가 같고, 기관코드는 orgs 에 있고 정렬되어 있고 겹치지 않으며, 열쇠는 정한 꼴이다."""
    S, D, CV, T, gate = f["S"], f["D"], f["CV"], f["T3"], f["gate"]
    errs: list[str] = []
    orgs = {o["code"] for o in D["orgs"]}
    errs += [f"orgs {o['code']}: 업권 {o['업권']!r}" for o in D["orgs"] if o["업권"] not in SECTORS + (None,)]
    kinds = S["종형"]
    # 지도 칸: 코드 목록 길이 = 수. 열린, 일부 열린, 닫힌, 모르는 목록은 겹치지 않고 합하면 칸의 우리 밖 회사 전부다.
    # 관문만 열린 회사는 열린 쪽에 든다. 일부 열린 회사마다 열리는 나이가 칸의 열 안에 있다
    for name, m in S["지도"].items():
        if len({(c["lo"], c["hi"]) for c in m["열"]}) != len(m["열"]) or \
                any(a["hi"] + 1 != b["lo"] for a, b in zip(m["열"], m["열"][1:])):
            errs.append(f"지도 {name}: 열이 이어지지 않는다")
        if any(not _codes_ok(g["상대코드"], orgs) or len(g["상대코드"]) != g["상대수"] for g in m["고지유형"]):
            errs.append(f"지도 {name}: 고지유형의 상대코드")
        if len(m["이력없음"]) != len(m["열"]):
            errs.append(f"지도 {name}: 이력없음의 수 {len(m['이력없음'])} 가 열 수 {len(m['열'])} 와 다르다")
        for ri, line in [*enumerate(m["칸"]), ("이력없음", m["이력없음"])]:
            for ci, c in enumerate(line):
                at = f"지도 {name} [{ri}][{ci}]"
                col = m["열"][ci]
                for ck, nk in CELL_CODES.items():
                    if len(c[ck]) != c[nk] or not _codes_ok(c[ck], orgs):
                        errs.append(f"{at}: {ck} {c[ck]} 와 {nk} {c[nk]}")
                four = c["열린상대코드"] + c["일부열린상대코드"] + c["닫힌상대코드"] + c["모르는상대코드"]
                if sorted(four) != sorted(o for o in c["회사"] if o != HOME) or len(four) != c["상대수"]:
                    errs.append(f"{at}: 열린, 일부 열린, 닫힌, 모르는 상대코드가 칸의 상대 회사와 다르다")
                if not set(c["관문만열린상대코드"]) <= set(c["열린상대코드"]):
                    errs.append(f"{at}: 관문만열린상대코드가 열린상대코드에 들지 않는다")
                if set(c["관문만열린상대코드"]) != {x["기관코드"] for x in c["관문만수집"]}:
                    errs.append(f"{at}: 관문만열린상대코드가 관문만수집의 회사와 다르다")
                errs += [f"{at}: 열린상대코드 {o} 의 상태가 {c['회사'][o]}" for o in c["열린상대코드"] if c["회사"][o] != "열림"]
                errs += [f"{at}: 일부열린상대코드 {o} 의 상태가 {c['회사'][o]}" for o in c["일부열린상대코드"]
                         if c["회사"][o] != PARTIAL]
                if sorted(c["일부열린나이"]) != c["일부열린상대코드"]:
                    errs.append(f"{at}: 일부열린나이의 회사가 일부열린상대코드와 다르다")
                for o, spans in c["일부열린나이"].items():
                    flat = [a for s in spans for a in s]
                    if not spans or flat != sorted(flat) or flat[0] < col["lo"] or flat[-1] > col["hi"] or \
                            (flat[0] == col["lo"] and flat[-1] == col["hi"] and len(spans) == 1):
                        errs.append(f"{at}: 일부열린나이 {o} {spans} 가 열 {col} 의 일부가 아니다")
                if c["일부나이로만열림"] != (c["열린상대수"] == 0 and c["일부열린상대수"] > 0):
                    errs.append(f"{at}: 일부나이로만열림")
                if not col["lo"] <= c["세부나이"] <= col["hi"]:
                    errs.append(f"{at}: 세부나이 {c['세부나이']} 가 열 {col} 밖이다")
                errs += _flow_errors(at, c, m, S, gate, orgs)
    # 고지유형속성: 열쇠는 관문 나무의 상대 종형 열쇠, 값마다 센 종형 수의 합은 그 열쇠의 상대 종형 수
    peer_vids: dict[str, list[str]] = {}
    for v in gate["종형"]:
        if gate["종형정보"][v]["회사"] != HOME:
            peer_vids.setdefault(gate["종형정보"][v]["고지유형열쇠"], []).append(v)
    if set(S["고지유형속성"]) != set(peer_vids):
        errs.append("고지유형속성의 열쇠가 관문 나무의 상대 종형 열쇠와 다르다")
    for key, a in S["고지유형속성"].items():
        n = len(peer_vids.get(key, []))
        firms = sorted({gate["종형정보"][v]["회사"] for v in peer_vids.get(key, [])})
        lists = [a["수술포함별"], a["중대질병수별"], a["가입나이별"]["M"], a["가입나이별"]["F"]]
        for vals in lists:
            if sum(x["종형수"] for x in vals) != n or sorted({o for x in vals for o in x["상대코드"]}) != firms or \
                    any(len(x["상대코드"]) != x["상대수"] or not _codes_ok(x["상대코드"], orgs) for x in vals):
                errs.append(f"고지유형속성 {key}: 값마다의 수가 상대 종형 {n}개, 회사 {firms} 와 맞지 않는다")
        surgery = sorted(({gate["종형정보"][v]["질문"]["surgery"] for v in peer_vids.get(key, [])}), key=str)
        if sorted((x["값"] for x in a["수술포함별"]), key=str) != surgery:
            errs.append(f"고지유형속성 {key}: 수술포함별 값이 gate.json 과 다르다")
    # 담보 비교 자료: 판정기관코드는 줄마다 있고, 판정마다 목록이 겹치지 않으며 보유기관코드를 모두 담는다. 판정상대수는 목록 길이.
    # 판정기관코드, 판정상대수, 판정요약은 쌍판정을 모은 것이고, 쌍판정은 정한 규칙대로다(_cover_pair_errors)
    for bid, b in CV["b"].items():
        for sid, per in b["판정기관코드"].items():
            codes = [o for v in per.values() for o in v]
            if len(codes) != len(set(codes)) or not set(b["보유기관코드"].get(sid, [])) <= set(codes) or \
                    not set(per) <= set(VERDICTS) or any(not v or not _codes_ok(v, orgs) for v in per.values()):
                errs.append(f"cover {bid} {sid}: 판정기관코드 {per} 와 보유기관코드 {b['보유기관코드'].get(sid)}")
            if b["판정상대수"].get(sid) != {k: len(v) for k, v in per.items()}:
                errs.append(f"cover {bid} {sid}: 판정상대수가 판정기관코드의 목록 길이와 다르다")
        if set(b["판정기관코드"]) != {r[0] for r in b["rows"]} or set(b["판정상대수"]) != set(b["판정기관코드"]):
            errs.append(f"cover {bid}: 판정기관코드의 담보가 rows 와 다르다")
        # 우리에게 확정 급부가 없는 담보는 비교쌍 판정이 없다(우체국에 없음이나 검토 대기뿐이다)
        for r in b["rows"]:
            mine = r[1][0]
            if not (isinstance(mine, dict) and mine.get("i")) and \
                    not set(b["판정기관코드"][r[0]]) <= {"우체국에 없음", "검토 대기"}:
                errs.append(f"cover {bid} {r[0]}: 우리에게 없는 담보에 비교쌍 판정이 있다")
    errs += _cover_pair_errors(CV, S)
    errs += _scope_pair_errors(CV, S)
    # 포인트: 관련기관코드 = 비교종형ID 가 속한 우리 밖 회사
    for pid, p in S["포인트"].items():
        want = sorted({kinds[v]["기관코드"] for v in p["비교종형ID"]} - {HOME})
        if p["관련기관코드"] != want or not _codes_ok(p["관련기관코드"], orgs):
            errs.append(f"포인트 {pid}: 관련기관코드 {p['관련기관코드']}, 비교종형ID 로는 {want}")
    # 담보 비교 자료: 보유기관코드는 줄마다 있고, 확정 급부가 있는 칸(i 가 비지 않음. tab4 의 has)의 상대 회사다
    for bid, b in CV["b"].items():
        own = b["보유기관코드"]
        if set(own) != {r[0] for r in b["rows"]}:
            errs.append(f"cover {bid}: 보유기관코드의 담보가 rows 와 다르다")
            continue
        for r in b["rows"]:
            want = sorted({kinds[v]["기관코드"] for v, c in zip(b["cols"][1:], r[1][1:])
                           if isinstance(c, dict) and c.get("i")} - {HOME})
            if own[r[0]] != want or not _codes_ok(own[r[0]], orgs):
                errs.append(f"cover {bid} {r[0]}: 보유기관코드 {own[r[0]]}, 칸으로는 {want}")
    # 관문: 고지유형열쇠의 꼴(gate.json 과 tab3.js 의 자료 줄이 같다), 기준별 고지유형별의 수
    info = gate["종형정보"]
    for vid, x in info.items():
        key, q = x["고지유형열쇠"], x["질문"]
        vals = [q["months"], q["hospYears"], q["majorYears"]]
        if x["심사"] == "일반심사":
            want = "일반심사"
        elif x["심사"] != "간편심사" or any(v is None for v in vals):
            want = "모름"
        else:
            want = "·".join(_num_text(v) for v in vals)
        if key != want or not (key in ("일반심사", "모름") or NOTICE_KEY.match(key)):
            errs.append(f"gate {vid}: 고지유형열쇠 {key!r}, 고지 열로는 {want!r}")
        if T["관문"]["I"].get(vid, {}).get("고지유형열쇠") != key:
            errs.append(f"tab3 {vid}: 고지유형열쇠가 gate.json 과 다르다")
    for bid, b in S["기준별"].items():
        groups = b["고지유형별"]
        keys = [g["열쇠"] for g in groups]
        if len(keys) != len(set(keys)) or [g["열쇠"] for g in groups if g["기준"]] != [info[bid]["고지유형열쇠"]]:
            errs.append(f"기준별 {bid}: 고지유형별 열쇠가 겹치거나 기준 묶음이 기준 종형의 열쇠와 다르다")
        for g in groups:
            vids = [v for v in gate["종형"] if info[v]["고지유형열쇠"] == g["열쇠"]]
            peer = [v for v in vids if info[v]["회사"] != HOME]
            same = sum(1 for v in b["맞붙는종형"] if info.get(v, {}).get("고지유형열쇠") == g["열쇠"])
            if (g["종형수"], g["우리종형수"], g["맞붙는종형수"]) != (len(peer), len(vids) - len(peer), same) or \
                    g["상대코드"] != sorted({info[v]["회사"] for v in peer}) or g["상대수"] != len(g["상대코드"]):
                errs.append(f"기준별 {bid} {g['열쇠']}: 고지유형별의 수가 gate.json 과 다르다({g})")
        if sum(g["종형수"] + g["우리종형수"] for g in groups) != len(gate["종형"]):
            errs.append(f"기준별 {bid}: 고지유형별 종형 수의 합이 관문 나무의 종형 수와 다르다")
        if sum(g["맞붙는종형수"] for g in groups) != len(b["맞붙는종형"]):
            errs.append(f"기준별 {bid}: 고지유형별 맞붙는종형수의 합이 맞붙는 종형 수와 다르다")
    errs += _notice_text_errors(gate, T)
    errs += _brief_code_errors(S, D, orgs)
    return errs


OPINION_SCOPES = ("서면", "서면과 진료기록부")


def _notice_text_errors(gate: dict, T: dict) -> list[str]:
    """관문 종형정보의 고지중대질병목록과 고지소견범위: 일반심사는 둘 다 null, 목록은 ", "로 이은 빈 항목 없는 글이고 항목 수가
    질문의 majorCount 와 같으며, 소견 범위는 서면 또는 서면과 진료기록부다. tab3.js 의 자료 줄(T3.관문.I)도 같은 값이다."""
    errs: list[str] = []
    for vid, x in gate["종형정보"].items():
        names, scope = x["고지중대질병목록"], x["고지소견범위"]
        if x["심사"] == "일반심사" and (names is not None or scope is not None):
            errs.append(f"gate {vid}: 일반심사 종형에 고지중대질병목록이나 고지소견범위가 있다")
        if names is not None:
            items = names.split(", ")
            count = x["질문"].get("majorCount")
            if not names or any(not s.strip() or s != s.strip() for s in items) or \
                    (count is not None and len(items) != count):
                errs.append(f"gate {vid}: 고지중대질병목록 {names!r} 와 질병 수 {count}")
        if scope is not None and scope not in OPINION_SCOPES:
            errs.append(f"gate {vid}: 고지소견범위 {scope!r}")
        t = T["관문"]["I"].get(vid, {})
        if (t.get("고지중대질병목록"), t.get("고지소견범위")) != (names, scope):
            errs.append(f"tab3 {vid}: 고지중대질병목록이나 고지소견범위가 gate.json 과 다르다")
    return errs


def _brief_code_errors(S: dict, D: dict, orgs: set) -> list[str]:
    """브리핑 (가)와 (다)의 기관코드 목록: 길이가 같은 줄의 수(이름 목록)와 같고, 기관코드 공통 규칙을 따르며, 정의대로다.
    관문차이상대코드는 맞붙는 상대와 견준 G3 포인트(비교종형ID 가 모두 맞붙는종형)의 회사, 구조다름회사코드는 범위.상대에서
    구조다름이 참인 상대의 회사다. 이름 목록(관문차이상대, 나이자료없음회사)은 같은 회사를 D.orgs 의 이름으로 적은 것이다."""
    errs: list[str] = []
    kinds, names = S["종형"], {o["code"]: o["name"] for o in D["orgs"]}
    for bid, b in S["기준별"].items():
        lines = {x["줄"]: x["값"] for x in b["브리핑"]}
        peers = set(b["맞붙는종형"])
        ga, da = lines["가"], lines["다"]
        no_age = ga["나이자료없음회사코드"]
        if not _codes_ok(no_age, orgs) or sorted(names[o] for o in no_age) != sorted(ga["나이자료없음회사"]):
            errs.append(f"브리핑 {bid} (가): 나이자료없음회사코드 {no_age} 와 나이자료없음회사 {ga['나이자료없음회사']}")
        gate_codes = da["관문차이상대코드"]
        want = sorted({kinds[v]["기관코드"] for pid in b["포인트"] for p in [S["포인트"][pid]]
                       if p["세부"] == "G3" and set(p["비교종형ID"]) <= peers for v in p["비교종형ID"]})
        if not _codes_ok(gate_codes, orgs) or len(gate_codes) != da["관문차이수"] or gate_codes != want or \
                sorted(names[o] for o in gate_codes) != sorted(da["관문차이상대"]):
            errs.append(f"브리핑 {bid} (다): 관문차이상대코드 {gate_codes}, 관문차이수 {da['관문차이수']}, G3 포인트로는 {want}")
        struct = da["구조다름회사코드"]
        want = sorted({kinds[r["종형ID"]]["기관코드"] for r in b["범위"]["상대"] if r["구조다름"]})
        if not _codes_ok(struct, orgs) or len(struct) != da["구조다름회사수"] or struct != want:
            errs.append(f"브리핑 {bid} (다): 구조다름회사코드 {struct}, 구조다름회사수 {da['구조다름회사수']}, 범위로는 {want}")
    return errs


def _has_cell(c) -> bool:
    return isinstance(c, dict) and bool(c.get("i"))


def _waits(c) -> bool:
    return isinstance(c, dict) and bool(c.get("w"))


def expected_pair(sid: str, cols: list, cells: list, prs: dict, notes: list, cautious: set, k: int) -> str | None:
    """쌍판정의 까닭을 API.md 의 규칙대로 다시 낸다(자료 쪽 console4.pair_verdict 와 따로 적어, 둘이 어긋나면 드러난다)."""
    base, cell, peer = cells[0], cells[k], cols[k]
    if _has_cell(cell) and _has_cell(base):
        q = prs[peer]
        if (sid, peer) in cautious:
            return "단정 주의"
        if q.get("x"):
            return "검토 대기"
        if q.get("f") == "다름" and q["v"] == "같음":
            return "지급 형태 다름"
        return q["v"]
    if _has_cell(cell):                       # 상대에게만 있다: 우리 쪽 매핑 대기만 검토 대기로 본다(뺀 시사점은 보지 않는다)
        return "검토 대기" if _waits(base) else "우체국에 없음"
    if _has_cell(base):                       # 우리에게만 있다
        if _waits(cell) or any(x.get("drop") and peer in (x.get("p") or []) for x in notes):
            return "검토 대기"
        return "관계 담보로 덮음" if isinstance(cell, dict) and cell.get("c") else PAIR_ONLY
    return "검토 대기" if _waits(base) or _waits(cell) else None


def _cover_pair_errors(CV: dict, S: dict) -> list[str]:
    """쌍판정: 담보마다 상대 차례로 하나씩이고 까닭은 규칙(expected_pair)대로다. 판정기관코드는 상대에 없음과 둘 다 없음을 뺀 쌍판정을
    까닭별로 모은 것, 판정요약은 상대 회사마다 판정 이름별 쌍 수(둘 다 없음 포함)다. 판정표는 까닭마다의 판정 이름과 칩이다."""
    errs: list[str] = []
    kinds = S["종형"]
    if {k: (v["판정"], v["칩"]) for k, v in CV["판정표"].items()} != PAIR_TABLE:
        errs.append(f"cover 판정표 {CV['판정표']}")
    if set(CV["판정차례"]) != {n for n, _ in PAIR_TABLE.values()} | {BOTH_NONE}:
        errs.append(f"cover 판정차례 {CV['판정차례']}")
    for bid, b in CV["b"].items():
        cautious = {(c["표준담보ID"], p) for c in S["기준별"][bid]["단정주의"] for p in c["상대종형ID"]}
        kind_of = {(c["표준담보ID"], p): c["종류"] for c in S["기준별"][bid]["단정주의"] for p in c["상대종형ID"]}
        peers = b["cols"][1:]
        if set(b["쌍판정"]) != {r[0] for r in b["rows"]}:
            errs.append(f"cover {bid}: 쌍판정의 담보가 rows 와 다르다")
            continue
        summary: dict[str, dict[str, int]] = {}
        for r in b["rows"]:
            sid, cells, prs, notes = r[0], r[1], r[2] or {}, (r[3] if len(r) > 3 else [])
            got = b["쌍판정"][sid]
            if len(got) != len(peers):
                errs.append(f"cover {bid} {sid}: 쌍판정 {len(got)}개, 상대 {len(peers)}곳")
                continue
            per: dict[str, list[str]] = {}
            for k, (peer, v) in enumerate(zip(peers, got), start=1):
                want = expected_pair(sid, b["cols"], cells, prs, notes, cautious, k)
                key = v[0] if v else None
                if key != want or (v is not None and (key not in PAIR_TABLE or not all(isinstance(x, str) for x in v[1]))):
                    errs.append(f"cover {bid} {sid} {peer}: 쌍판정 {v}, 규칙으로는 {want}")
                    continue
                if key == "검토 대기" and not v[1]:
                    errs.append(f"cover {bid} {sid} {peer}: 검토 대기의 사유가 비었다")
                if key == "검토 대기" and prs.get(peer, {}).get("x") and v[1] != prs[peer]["x"]:
                    errs.append(f"cover {bid} {sid} {peer}: 검토 대기 사유가 뺀 비교쌍 사유와 다르다")
                if key == "단정 주의" and v[1] != [kind_of[(sid, peer)]]:
                    errs.append(f"cover {bid} {sid} {peer}: 단정 주의 사유 {v[1]}")
                if key == "판정 보류" and v[1] != list(prs[peer].get("hs") or []):
                    errs.append(f"cover {bid} {sid} {peer}: 판정 보류 사유 {v[1]}")
                org = kinds[peer]["기관코드"]
                if key is not None and key != PAIR_ONLY:
                    per.setdefault(key, []).append(org)
                name = BOTH_NONE if key is None else PAIR_TABLE[key][0]
                summary.setdefault(org, {})
                summary[org][name] = summary[org].get(name, 0) + 1
            if b["판정기관코드"][sid] != {k: sorted(v) for k, v in per.items()}:
                errs.append(f"cover {bid} {sid}: 판정기관코드 {b['판정기관코드'][sid]} 가 쌍판정을 모은 {per} 와 다르다")
        if b["판정요약"] != summary or any(sum(x.values()) != len(b["rows"]) for x in b["판정요약"].values()):
            errs.append(f"cover {bid}: 판정요약 {b['판정요약']} 이 쌍판정을 센 {summary} 와 다르다")
    return errs


def _scope_pair_errors(CV: dict, S: dict) -> list[str]:
    """보류요약의 기관별: 맞붙는 상대의 회사 전부이고, 회사 값을 모두 더하면 전체 값(공통담보쌍, 뺀쌍, 견준쌍, 사유별)이다. 대분류 줄도
    같다. 회사 값은 cover.json 의 비교쌍 기록(rows 의 상대별 쌍, 뺀 쌍은 x 가 있는 쌍)을 그 회사로 센 수와 같다."""
    errs: list[str] = []
    kinds = S["종형"]
    for bid, base in S["기준별"].items():
        p = base["보류요약"]
        org = {v: kinds[v]["기관코드"] for v in base["맞붙는종형"]}
        codes = sorted(set(org.values()))
        by = p["기관별"]
        if list(by) != codes:
            errs.append(f"보류요약 {bid}: 기관별 열쇠 {list(by)}, 맞붙는 회사 {codes}")
            continue
        for key in ("공통담보쌍", "뺀쌍", "견준쌍"):
            if sum(x[key] for x in by.values()) != p[key]:
                errs.append(f"보류요약 {bid}: 기관별 {key} 의 합이 {p[key]} 와 다르다")
        if any(x["공통담보쌍"] != x["뺀쌍"] + x["견준쌍"] for x in by.values()):
            errs.append(f"보류요약 {bid}: 기관별 공통담보쌍이 뺀쌍과 견준쌍의 합과 다르다")
        if {k: sum(x["사유별"][k] for x in by.values()) for k in p["사유별"]} != p["사유별"]:
            errs.append(f"보류요약 {bid}: 기관별 사유별의 합이 사유별과 다르다")
        for row in p["대분류"]:
            if list(row["기관별"]) != codes or any(sum(x[key] for x in row["기관별"].values()) != row[key]
                                                for key in ("공통담보쌍", "뺀쌍", "견준쌍")):
                errs.append(f"보류요약 {bid} {row['대분류']}: 기관별의 합이 그 줄의 값과 다르다")
        # cover.json 의 비교쌍 기록으로 센 수(화면의 scopedPairs 가 세던 값)
        counted = {o: {"공통담보쌍": 0, "뺀쌍": 0} for o in codes}
        majors: dict[str, dict[str, dict[str, int]]] = {}
        for r in CV["b"][bid]["rows"]:
            major = S["표준담보"][r[0]]["대분류"]
            for peer, q in (r[2] or {}).items():
                o = org[peer]
                counted[o]["공통담보쌍"] += 1
                counted[o]["뺀쌍"] += 1 if q.get("x") else 0
                m = majors.setdefault(major, {}).setdefault(o, {"공통담보쌍": 0, "뺀쌍": 0})
                m["공통담보쌍"] += 1
                m["뺀쌍"] += 1 if q.get("x") else 0
        if {o: {"공통담보쌍": x["공통담보쌍"], "뺀쌍": x["뺀쌍"]} for o, x in by.items()} != counted:
            errs.append(f"보류요약 {bid}: 기관별 {by} 이 cover.json 의 비교쌍 기록으로 센 {counted} 와 다르다")
        for row in p["대분류"]:
            got = {o: {"공통담보쌍": x["공통담보쌍"], "뺀쌍": x["뺀쌍"]} for o, x in row["기관별"].items() if x["공통담보쌍"]}
            if got != majors.get(row["대분류"], {}):
                errs.append(f"보류요약 {bid} {row['대분류']}: 기관별이 cover.json 의 비교쌍 기록으로 센 수와 다르다")
    return errs


def test_added_values_for_any_number_of_companies(files):
    assert added_value_errors(files) == []
    sectors = {o["code"]: o["업권"] for o in files["D"]["orgs"]}
    assert sectors["HANWHALIFE"] == "생명보험" and sectors["SAMSUNGFIRE"] == "손해보험" and sectors["EPOST"] is None


def test_added_value_checker_catches_mismatch(made):
    f = {k: copy.deepcopy(made[k]) for k in ("S", "D", "CV", "T3", "gate")}
    c = f["S"]["지도"]["전체"]["칸"][0][0]
    c["닫힌상대코드"] = c["닫힌상대코드"] + ["NOPE"]
    next(iter(f["gate"]["종형정보"].values()))["고지유형열쇠"] = "3-2-5"
    next(iter(f["S"]["포인트"].values()))["관련기관코드"] = []
    errs = added_value_errors(f)
    assert any("닫힌상대코드" in e for e in errs) and any("고지유형열쇠 '3-2-5'" in e for e in errs)
    assert any("관련기관코드" in e for e in errs)
    # 일부 나이만 열린 상대, 관문흐름, 고지유형속성, 판정기관코드
    f = {k: copy.deepcopy(made[k]) for k in ("S", "D", "CV", "T3", "gate")}
    c = f["S"]["지도"]["전체"]["칸"][1][1]
    c["일부열린나이"] = {"HANWHALIFE": [[20, 80]]}
    c["관문흐름"]["유형"][0]["통과수"][0] += 1
    next(iter(f["S"]["고지유형속성"].values()))["수술포함별"][0]["종형수"] += 1
    b = next(iter(f["CV"]["b"].values()))
    sid = next(s for s, per in b["판정기관코드"].items() if per)
    b["판정기관코드"][sid] = {"나음": ["NOPE"]}
    errs = added_value_errors(f)
    assert any("일부열린나이의 회사" in e for e in errs) and any("통과수" in e for e in errs)
    assert any("고지유형속성" in e for e in errs) and any(f"{sid}: 판정기관코드" in e for e in errs)
    # 고지 질병 목록과 소견 범위, 브리핑의 기관코드 목록
    f = {k: copy.deepcopy(made[k]) for k in ("S", "D", "CV", "T3", "gate")}
    info = f["gate"]["종형정보"]
    simple = next(v for v, x in info.items() if x["고지중대질병목록"])
    info[simple]["고지중대질병목록"] += ", 새 질병"                 # 질병 수와 어긋난다(tab3 과도 다르다)
    general = next(v for v, x in info.items() if x["심사"] == "일반심사")
    info[general]["고지소견범위"] = "진료기록부"
    lines = {x["줄"]: x["값"] for x in next(b for b in f["S"]["기준별"].values()
                                         if next(y for y in b["브리핑"] if y["줄"] == "다")["값"]["관문차이수"])["브리핑"]}
    lines["다"]["관문차이상대코드"] = lines["다"]["관문차이상대코드"][:-1]
    lines["다"]["구조다름회사코드"] = ["EPOST"] + lines["다"]["구조다름회사코드"]
    lines["가"]["나이자료없음회사코드"] = ["NOPE"]
    errs = added_value_errors(f)
    assert any(f"gate {simple}: 고지중대질병목록" in e for e in errs) and any(f"tab3 {simple}" in e for e in errs)
    assert any(f"gate {general}: 일반심사" in e for e in errs) and any(f"gate {general}: 고지소견범위" in e for e in errs)
    assert any("관문차이상대코드" in e for e in errs) and any("구조다름회사코드" in e for e in errs)
    assert any("나이자료없음회사코드" in e for e in errs)


def test_notice_texts_and_cover_steps_follow_the_tables(made):
    """관문 종형정보의 고지중대질병목록과 고지소견범위는 종형 표의 값 그대로다(빈 값은 null). 담보 비교 자료의 담보마다 치료
    단계(급부유형)와 보장 분야(대분류)는 S.표준담보 에 있고 표준담보 사전의 값 그대로다(tab4.src.js 의 model 이 읽는 자리)."""
    data, gate, S, CV = made["data"], made["gate"], made["S"], made["CV"]
    for vid, x in gate["종형정보"].items():
        v = data.variants[vid]
        assert x["고지중대질병목록"] == (v.get("고지중대질병목록") or None), vid
        assert x["고지소견범위"] == (v.get("고지소견범위") or None), vid
    assert any(x["고지중대질병목록"] for x in gate["종형정보"].values())
    assert {x["고지소견범위"] for x in gate["종형정보"].values()} == {None, *OPINION_SCOPES}
    steps = S["기준별"][S["기준종형"][0]["종형ID"]]["치료여정"]["열"]
    assert steps == ["진단", "수술", "치료", "입원", "통원"]
    for bid, b in CV["b"].items():
        for r in b["rows"]:
            st, src = S["표준담보"][r[0]], data.std[r[0]]
            assert (st["급부유형"], st["대분류"]) == (src.get("급부유형"), src["보장대분류"]), (bid, r[0])
            assert st["급부유형"] and st["대분류"], (bid, r[0])   # 다섯 단계 밖의 급부유형은 화면이 기타로 둔다


def test_map_columns_and_flow_on_three_companies(made):
    """지도 열은 우리 기관의 가입나이 경계(sales.map_columns)로 끊은 구간을, 이웃 열의 결과가 같으면 합친 것이다. 칸은 행 수 x 열 수다.
    열 수와 칸 수를 숫자로 고정하지 않고 자료에서 계산한 경계와 비교한다(2026-11-25. 우체국 상품 구성이 바뀌어 스냅샷을 갱신해도
    같은 규약을 본다). 세 회사 사본에서는 일부 나이만 열린 상대가 없다(지도 열이 우리 가입나이로 끊어도 상대 상태가 열 안에서 같다).
    인수기준 단계별 통과는 가입나이, 입원·수술 고지기간, 수술 포함 여부에서 고지 해당으로, 일반심사는 필요소견에서 일반심사 대상으로
    멈춘다(우체국에 일반심사 종형이 없는 지도는 일반심사 대상 멈춤이 없다)."""
    S, data = made["S"], made["data"]
    cols = SA.map_columns(data)
    starts, ends = {a for a, _ in cols}, {b for _, b in cols}
    stops = set()
    for name, m in S["지도"].items():
        cells = [c for line in m["칸"] for c in line]
        assert len(m["칸"]) == len(m["행"]) and all(len(line) == len(m["열"]) for line in m["칸"]), name
        assert len(cells) == len(m["행"]) * len(m["열"]), name
        assert m["열"][0]["lo"] == cols[0][0] and m["열"][-1]["hi"] == cols[-1][1], name
        assert all(c["lo"] in starts and c["hi"] in ends for c in m["열"]), name
        assert all(a["hi"] + 1 == b["lo"] for a, b in zip(m["열"], m["열"][1:])), name
        assert not any(c["일부열린상대수"] or c["일부열린나이"] or c["일부나이로만열림"] for c in cells), name
        stops |= {(S["관문마디"]["차례"][k], v) for c in cells for k, v in c["관문흐름"]["종형"].values()}
    assert stops <= {("가입나이", "고지 해당"), ("입원·수술 고지기간", "고지 해당"), ("수술 포함 여부", "고지 해당"),
                     ("필요소견", "일반심사 대상")}
    assert {("가입나이", "고지 해당"), ("입원·수술 고지기간", "고지 해당"), ("수술 포함 여부", "고지 해당")} <= stops


MAP_RENEWAL = {"전체": None, "갱신": "갱신", "비갱신": "비갱신"}


def _final_pass_mismatches(f: dict, pick) -> list[tuple]:
    """지도마다 열마다 pick(지도, 열 번호)이 고른 칸의 관문흐름에서 유형마다 마지막 마디의 통과수가, gate.json 의 이력 없음 조건
    (M|-|0)의 그 칸의 세부나이에서 그 유형의 종형이 하나라도 열린 상대 회사 수와 다른 (지도, 열, 유형, 통과수, 열린 회사 수)."""
    S, gate = f["S"], f["gate"]
    info, vids = gate["종형정보"], gate["종형"]
    out = []
    for name, m in S["지도"].items():
        renewal = MAP_RENEWAL[name]
        for ci in range(len(m["열"])):
            c = pick(m, ci)
            hit = next(e for e in gate["조건"]["M|-|0"] if e["lo"] <= c["세부나이"] <= e["hi"])
            opened: dict[str, set] = {}
            for i, v in enumerate(vids):
                x = info[v]
                if x["회사"] == HOME or (renewal is not None and x["갱신"] != renewal):
                    continue
                if gate["상태"][hit["v"]["s"][i][0]] == "열림":
                    opened.setdefault(x["고지유형열쇠"], set()).add(x["회사"])
            for g in c["관문흐름"]["유형"]:
                n = len(opened.get(g["열쇠"], ()))
                if g["통과수"][-1] != n:
                    out.append((name, ci, g["열쇠"], g["통과수"][-1], n))
    return out


def test_no_history_flow_matches_the_gate_tree(files):
    """이력 없음의 관문흐름(지도의 이력없음): 유형마다 끝까지 통과한 상대 수가 관문 나무(gate.json)의 같은 조건에서 그 유형의
    종형이 열린 상대 회사 수와 같다. 지도의 "5년+" 칸(마지막 입원이 5년 전)에서는 5년보다 긴 기간을 묻는 간편 종형(한화생명
    10년형)이 닫혀 같지 않다. 화면은 이력 없음일 때 이력없음을 읽는다(core.js 의 cellOf)."""
    assert _final_pass_mismatches(files, lambda m, ci: m["이력없음"][ci]) == []

    def five(m, ci):
        last = max(r["since"] for r in m["행"])
        ri = next(i for i, r in enumerate(m["행"]) if r["종류"] == "입원" and r["since"] == last)
        return m["칸"][ri][ci]

    longer = any((x["질문"] or {}).get("hospYears") and x["질문"]["hospYears"] > 5
                 for x in files["gate"]["종형정보"].values() if x["회사"] != HOME and x["심사"] == "간편심사")
    assert bool(_final_pass_mismatches(files, five)) == longer


# ---------- 담보 비교의 쌍판정과 범위별 쌍 수(2026-11-23) ----------
def test_pair_verdict_rules_on_hand_made_cells():
    """쌍판정의 규칙(console4.pair_verdict)을 손으로 만든 칸으로 본다. 화면의 verdictOf 와 기둥 집계가 갈리던 두 경우를 고정한다.
    - 우리에게만 있고 상대가 관계 담보로 덮으면 관계 담보로 덮음(우열을 매기지 않음)이고 기둥(판정기관코드)에 든다.
    - 상대에게만 있으면 우리 쪽 매핑 대기만 검토 대기로 본다. 그 줄에 뺀 시사점(빈자리를 검토 대기로 뺀 것)이 있어도 우체국에 없음이다."""
    from types import SimpleNamespace
    sid = "STD_X"
    vids = ["B", "P1", "P2", "P3", "P4"]
    data = SimpleNamespace(variants={v: {"기관코드": f"ORG{v}"} for v in vids})
    pair = {(sid, "P1"): {"v": "같음", "h": None, "f": "다름", "x": 0}}
    mine = {"r": 0, "i": [0], "n": 1}
    cells = [mine, {"r": 1, "i": [1], "n": 1}, {"c": ["넓은 담보", ["STD_W"], False]}, 0, {"w": 1}]
    got = [C4.pair_verdict(sid, vids, cells, k, pair, {}, []) for k in range(1, 5)]
    assert got == [["지급 형태 다름", []], ["관계 담보로 덮음", []], ["상대에 없음", []], ["검토 대기", ["P4 매핑 검수 대기 1건"]]]
    # 종형 이름(labels)을 주면 사유 글에 종형ID 대신 그 이름을 적는다
    named = C4.pair_verdict(sid, vids, cells, 4, pair, {}, [], {"P4": "삼성화재 7종"})
    assert named == ["검토 대기", ["삼성화재 7종 매핑 검수 대기 1건"]]
    assert C4.verdict_codes(data, got, vids[1:]) == {"지급 형태 다름": ["ORGP1"], "관계 담보로 덮음": ["ORGP2"],
                                                    "검토 대기": ["ORGP4"]}
    assert C4.verdict_summary(data, {sid: got}, vids[1:]) == {"ORGP1": {"우열을 매기지 않음": 1}, "ORGP2": {"우열을 매기지 않음": 1},
                                                             "ORGP3": {"우체국에만 있음": 1}, "ORGP4": {"검토 대기": 1}}
    # 상대가 든 뺀 시사점(고유를 검토 대기로 뺀 것)은 검토 대기. 단정 주의는 비교쌍 판정보다 먼저다
    notes = [{"k": "고유", "d": None, "p": ["P3"], "drop": ["기준 종형의 이 담보 급부가 모두 추출 검수 대기"]}]
    assert C4.pair_verdict(sid, vids, cells, 3, pair, {}, notes) == ["검토 대기", notes[0]["drop"]]
    assert C4.pair_verdict(sid, vids, cells, 1, pair, {(sid, "P1"): "지급 형태 상이"}, []) == ["단정 주의", ["지급 형태 상이"]]
    # 상대에게만 있으면: 뺀 시사점이 있어도 우체국에 없음, 우리 쪽 매핑 대기가 있으면 검토 대기
    drop = [{"k": "범위 차이", "d": "기준에 없음", "p": ["P1"], "drop": ["보유한 쪽의 이 담보 급부가 모두 추출 검수 대기"]}]
    theirs = [{"c": ["넓은 담보", ["STD_W"], False]}, {"r": 1, "i": [1], "n": 1}]
    assert C4.pair_verdict(sid, vids[:2], theirs, 1, {}, {}, drop) == ["우체국에 없음", []]
    assert C4.pair_verdict(sid, vids[:2], [{"w": 2}, theirs[1]], 1, {}, {}, drop) == ["검토 대기", ["B 매핑 검수 대기 2건"]]
    # 둘 다 확정 급부가 없으면 매핑 대기가 있을 때만 검토 대기
    assert C4.pair_verdict(sid, vids[:2], [0, {"w": 1}], 1, {}, {}, []) == ["검토 대기", ["P1 매핑 검수 대기 1건"]]
    assert C4.pair_verdict(sid, vids[:2], [0, 0], 1, {}, {}, []) is None
    # 테스트 쪽 규칙(expected_pair)과 같다
    for k in range(1, 5):
        assert expected_pair(sid, vids, cells, {"P1": pair[(sid, "P1")]}, [], set(), k) == got[k - 1][0]


def test_added_pair_values_catch_mismatch(made):
    """쌍판정, 판정요약, 보류요약의 기관별이 어긋나면 검사기가 잡는다."""
    f = {k: copy.deepcopy(made[k]) for k in ("S", "D", "CV", "T3", "gate")}
    bid = next(iter(f["CV"]["b"]))
    b = f["CV"]["b"][bid]
    sid, i = next((s, i) for s, vs in b["쌍판정"].items() for i, v in enumerate(vs) if v and v[0] == "우체국에 없음")
    b["쌍판정"][sid][i] = ["검토 대기", ["뺀 시사점"]]                        # 화면이 만들던 판정(뺀 시사점이면 검토 대기)
    org = next(iter(b["판정요약"]))
    b["판정요약"][org]["같음"] = b["판정요약"][org].get("같음", 0) + 1
    p = f["S"]["기준별"][bid]["보류요약"]
    p["기관별"][org]["뺀쌍"] += 1
    errs = added_value_errors(f)
    assert any(f"{sid}" in e and "쌍판정" in e for e in errs), errs
    assert any("판정요약" in e for e in errs) and any("기관별 뺀쌍" in e for e in errs)


@pytest.fixture(scope="module")
def made_all():
    """사본의 모든 회사(--orgs all)로 만든 자료. 화면에 올린 회사 밖의 회사가 사본에 없으면 건너뛴다."""
    from postlife import config
    data = load(SNAPSHOT, "all")
    extra = {v.get("기관코드") for v in data.variants.values()} - set(config.SITE_ORGS)
    if not extra:
        pytest.skip("사본에 화면에 올린 회사 밖의 회사가 없다")
    out = unpack(C4.export_texts(data, SRC))
    out["data"] = data
    out["extra"] = extra
    return out


def test_all_companies_follow_the_same_contract(made_all):
    """네 회사 이상의 자료(--orgs all)에서도 규약과 더한 값의 정합성(쌍판정, 판정요약, 보류요약의 기관별 포함)이 선다.
    d.json 의 lineup 은 화면에 올린 회사 전부의 자리이고, 등급마다 회사마다 고를 수 있는 종형(정밀비교, 판매 중, 그 간편고지약칭인
    종형이 하나뿐)이면 그 종형, 아니면 null 이다."""
    f, data = made_all, made_all["data"]
    assert check(f["S"], SALES) == [] and check(f["CV"], CV) == [] and check(f["D"], D) == []
    assert added_value_errors(f) == []
    d = f["D"]
    order = [o["code"] for o in d["orgs"]]
    assert set(order) == {v.get("기관코드") for v in data.variants.values()} and f["extra"] <= set(order)
    for grade, vs in d["lineup"].items():
        for code, v in zip(order, vs):
            found = [x for x in data.variant_order if data.variants[x].get("기관코드") == code
                     and data.variants[x].get("비교역할구분") == "정밀비교" and not data.variants[x].get("판매종료일")
                     and data.variants[x].get("간편고지약칭") == grade]
            assert v == (found[0] if len(found) == 1 else None), (grade, code, found)
    if "MERITZ" in order:     # 메리츠화재 통합간편건강보험 2610 의 315, 325, 355 간편심사형
        picked = [vs[order.index("MERITZ")] for vs in d["lineup"].values()]
        assert all(picked), picked
        names = [data.variants[v]["종형명"] for v in picked]
        assert ["315" in names[0], "325" in names[1], "355" in names[2]] == [True] * 3, names
