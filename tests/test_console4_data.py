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
                 "대분류": Seq({"대분류": str, "공통담보쌍": int, "뺀쌍": int, "견준쌍": int, "상대별": dict})},
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
           "고지유형": Seq({"열쇠": str, "상대수": int, "상대코드": Seq(str)})}
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
                       "고지유형열쇠": str}),
             "X": Seq({"s": Seq(Pos(int, int, int)), "라벨": str, "회사": Map(str), "닫힌사유": list}),
             "C": Map(Seq(Pos(int, int, int)))},
}

# ---------- tab4.js 첫 줄 (const CV) ----------
CV = {
    "t": str,
    "ben": Seq(Pos(str, int, str)),
    "rid": Seq(Pos(str, str)),
    "b": Map({"cols": Seq(str), "rows": Seq(Pos(str, Seq(One(int, dict)), Map(dict))), "pairs": int, "dropped": int,
              "보유기관코드": Map(Seq(str)), "판정기관코드": Map(Map(Seq(str))), "판정상대수": Map(Map(int))}),
}

# ---------- d.json (const D) ----------
D = {
    "asOf": str,
    "orgs": Seq({"code": str, "name": str, "short": str, "업권": Opt(str)}),
    "lineup": Map(Pos(str, str, str)), "defaultGrade": str,
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
ADDED_MAP = ("고지유형",)
ADDED_TOP = ("관문마디", "고지유형속성")
ADDED_SCOPE = ("업권별",)
ADDED_BRIEF = ("열린상대수분포", "상대회사수", "상대보유분포", "상대보유요약", "일부열림칸수", "일부나이로만열림칸수")
ADDED_POINT = ("관련기관코드",)
ADDED_BASE = ("고지유형별",)


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


def test_d_shape_and_ids(files):
    d, S = files["D"], files["S"]
    assert check(d, D) == []
    assert set(lineup.KEYS) <= set(d)
    codes = {o["code"] for o in d["orgs"]}
    assert {v["기관코드"] for v in S["종형"].values()} <= codes, "core.js 의 회사 짧은 이름(ORG_SHORT)이 빠진다"
    assert set(d["std"]) == set(d["stds"])
    assert set(d["compare"]) <= set(d["pool"]) <= set(d["stds"])
    assert d["defaultGrade"] in d["lineup"]
    assert {v for vs in d["lineup"].values() for v in vs} == set(d["variants"]) == set(d["cells"])
    assert all(v["org"] in codes for v in d["variants"].values())
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
STOPS = ("걸림", "모름", "심사로 확인")
VERDICTS = ("나음", "같음", "못함", "엇갈림", "판정 보류", "단정 주의", "검토 대기", "우체국에 없음")


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
        for ri, line in enumerate(m["칸"]):
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
    # 담보 비교 자료: 판정기관코드는 줄마다 있고, 판정마다 목록이 겹치지 않으며 합하면 그 담보의 보유기관코드다. 판정상대수는 목록 길이
    for bid, b in CV["b"].items():
        for sid, per in b["판정기관코드"].items():
            codes = [o for v in per.values() for o in v]
            if sorted(codes) != b["보유기관코드"].get(sid) or not set(per) <= set(VERDICTS) or \
                    any(not v or not _codes_ok(v, orgs) for v in per.values()):
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


def test_map_columns_and_flow_on_three_companies(made):
    """세 회사 사본: 일부 나이만 열린 상대가 없고(지도 열이 우리 가입나이로 끊어도 상대 상태가 열 안에서 같다), 지도마다 칸이 24개다.
    가입 관문 흐름은 실제로 가입나이, 입원과 수술의 기간, 수술 포함 여부에서 걸리고, 일반심사는 최근 소견에서 심사로 확인이다."""
    S = made["S"]
    stops = set()
    for name, m in S["지도"].items():
        cells = [c for line in m["칸"] for c in line]
        assert len(m["열"]) == 2 and len(cells) == 24, name
        assert not any(c["일부열린상대수"] or c["일부열린나이"] or c["일부나이로만열림"] for c in cells), name
        stops |= {(S["관문마디"]["차례"][k], v) for c in cells for k, v in c["관문흐름"]["종형"].values()}
    assert stops == {("가입나이", "걸림"), ("입원과 수술의 기간", "걸림"), ("수술 포함 여부", "걸림"), ("최근 소견", "심사로 확인")}
    assert [m["열"] for m in S["지도"].values()] == [[{"lo": 15, "hi": 19}, {"lo": 20, "hi": 80}]] * 2 + [
        [{"lo": 15, "hi": 65}, {"lo": 66, "hi": 80}]]
