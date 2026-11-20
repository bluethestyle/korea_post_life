"""화면 3: 표준담보별 비교표.

칸의 주된 값은 "그 특약을 최대로 가입했을 때 받는 금액"이다.
    급부의 기준지급금액 ÷ 기준가입금액 × 특약의 최대 가입금액(나이를 고르면 그 나이의 한도)
우열은 보장 조건(지급액, 면책기간, 감액)만으로 가린다. 보험료는 쓰지 않는다.
"""
from __future__ import annotations

import json
from typing import Any

from .model import Cond, Data, HOME_ORG, Limit, WAITING_STATE, _blank

# 사전에 없는 대분류는 뒤에 나온 순서대로 붙는다. 뇌심장보장은 뇌혈관과 심장을 한 급부로 함께 보장하는 담보
# (docs/proposals/표준담보사전_확장안.md 9절 2번)
GROUP_ORDER = ["암보장", "뇌혈관보장", "심장보장", "뇌심장보장", "공통보장"]
COMPARE_ROLE = "정밀비교"
MAIN_ROLE = "주급부"


# ---------- 환산 ----------
def scaled(pay: float | None, base: float | None, amount: float | None) -> float | None:
    """가입금액이 amount일 때의 지급액. 기준지급금액 ÷ 기준가입금액 × 가입금액."""
    if pay is None or not base or amount is None:
        return None
    return pay / base * amount


# ---------- 대표 급부 ----------
def pick_rep(cands: list[dict[str, Any]]) -> int | None:
    """한 표준담보에 이어진 급부 가운데 대표 줄의 번호(cands 안의 "i")를 고른다.

    1. 급부역할이 주급부인 줄이 있으면 그 가운데서, 없으면 전체에서 고른다.
    2. 금액(val)이 가장 큰 줄. 종별 수술비는 이 규칙으로 최고 종이 대표가 된다.
    3. 금액이 같거나 모르면(가입 한도 자료가 없는 줄) 기준지급금액이 큰 줄, 그래도 같으면 조건이 더 엄격한 줄(면책이 긴 줄, 감액이 있는 줄).
       좋은 조건을 대표로 내세워 실제보다 유리하게 보이는 일을 막기 위함이다.
       다만 가입금액 대비 비율로 적힌 급부(ratio)가 끼어 있으면, 그 기준지급금액은 지급률 숫자라 금액과 바로 견줄 수 없다.
       그때는 모든 줄을 기준가입금액 대비 지급률(기준지급금액 ÷ 기준가입금액)로 견준다. 금액 급부끼리는 기준지급금액으로 견준다.
    """
    if not cands:
        return None
    pool = [c for c in cands if c.get("role") == MAIN_ROLE] or cands
    by_rate = any(c.get("ratio") for c in pool)

    def second(c: dict[str, Any]) -> float:
        pay = c.get("pay")
        if not by_rate:
            return pay or 0
        return pay / c["base"] if pay is not None and c.get("base") else 0

    best = sorted(pool, key=lambda c: (-(c["val"] if c.get("val") is not None else -1.0), -second(c),
                                       -(c.get("wait") or 0), 0 if c.get("red") else 1, str(c.get("name"))))[0]
    return best["i"]


# ---------- 우열 ----------
def _sign(other: float, base: float) -> str:
    if abs(other - base) < 1e-9:
        return "="
    return "+" if other > base else "-"


def compare_reduction(other: list, base: list) -> str:
    """감액 조건 비교. 감액이 없으면 낫고, 기간이 짧을수록·지급률이 높을수록 낫다. 엇갈리면 "~"."""
    other, base = [list(x) for x in other or []], [list(x) for x in base or []]
    if other == base:
        return "="
    if not other:
        return "+"
    if not base:
        return "-"
    (mo, ro), (mb, rb) = other[0], base[0]
    marks = {_sign(mb, mo), _sign(ro, rb)} - {"="}
    if marks == {"+"}:
        return "+"
    if marks == {"-"}:
        return "-"
    return "~"


def compare_terms(other: dict[str, Any], base: dict[str, Any]) -> str:
    """기준(base) 대비 other의 보장 조건. 첫 글자가 종합, 이어서 지급액·면책·감액, 끝은 지급 한도 문구가 다른지.

    종합: b 나음, s 같음, w 못함, m 엇갈림
    """
    parts = [_sign(other["val"], base["val"]), _sign(base["wait"], other["wait"]),
             compare_reduction(other["red"], base["red"])]
    if "~" in parts or ("+" in parts and "-" in parts):
        overall = "m"
    elif "+" in parts:
        overall = "b"
    elif "-" in parts:
        overall = "w"
    else:
        overall = "s"
    wording = "L" if _squash(other.get("limit")) != _squash(base.get("limit")) else "."
    return overall + "".join(parts) + wording


def _squash(text: Any) -> str:
    return "".join(str(text or "").split())


def verdict(other: dict[str, Any], base: dict[str, Any]) -> str:
    """칸 둘의 판정 부호.

    "" 둘 다 없음 / n 이 종형에 없음(빈자리) / o 기준 종형에 없음 / q 매핑 검토 대기 급부만 있어 비교에서 뺌 /
    u 이 나이에 가입할 수 없음 / v 기준 종형이 이 나이에 가입할 수 없음 /
    p 검토 대기 값이 있어 판정을 미룸 / x 금액 자료 없음 / 그 밖에는 compare_terms의 부호
    """
    if other["kind"] == "none":
        if other.get("waiting"):
            return "q"
        return "" if base["kind"] == "none" and not base.get("waiting") else "n"
    if other["kind"] == "unavail":
        return "u"
    if base["kind"] == "none":
        return "q" if base.get("waiting") else "o"
    if base["kind"] == "unavail":
        return "v"
    if other["pend"] or base["pend"]:
        return "p"
    if other["val"] is None or base["val"] is None:
        return "x"
    return compare_terms(other, base)


# ---------- 칸 ----------
def collect(data: Data, vid: str) -> tuple[dict[str, list[dict]], dict[str, list[dict]], list[dict]]:
    """종형의 급부를 표준담보별로 나눈다: (확정, 추천만 있는 검토 대기, 추천도 없는 검토 대기)."""
    confirmed: dict[str, list[dict]] = {}
    waiting: dict[str, list[dict]] = {}
    loose: list[dict] = []
    for tid in data.riders_of.get(vid, []):
        for bid in data.benefits_of.get(tid, []):
            view = data.benefit_view(bid)
            if view["std"]:
                confirmed.setdefault(view["std"], []).append(view)
            elif view["state"] == WAITING_STATE:
                if view["rec"] in data.std:
                    waiting.setdefault(view["rec"], []).append(view)
                else:
                    loose.append(view)
    return confirmed, waiting, loose


def cell_core(data: Data, views: list[dict], cond: Cond, waiting: bool = False) -> dict[str, Any]:
    """한 조건에서 칸의 값. kind: none(확정 급부 없음) / unavail(이 나이에 가입할 수 없음) / ok.

    waiting은 이 칸에 매핑 검토 대기 급부가 있는지. 확정 급부가 없을 때 빈자리와 구분하는 데 쓴다.
    caps의 None은 두 가지다: 이 나이에 가입할 수 없는 줄(no에 번호를 적음)이거나, 가입은 되는데 가입 한도 자료가 없는 줄.
    """
    if not views:
        return {"kind": "none", "waiting": waiting}
    caps: list[Limit] = [data.rider_cap(v["tid"], cond) for v in views]
    vals = [scaled(v["pay"], v["base"], c.amount) if c.ok else None for v, c in zip(views, caps)]
    cands = [{"i": i, "role": v["role"], "val": vals[i], "pay": v["pay"], "base": v["base"], "ratio": v["ratio"],
              "wait": v["wait"], "red": v["red"], "name": v["name"]}
             for i, v in enumerate(views) if caps[i].ok]
    rep = pick_rep(cands)
    if rep is None:
        return {"kind": "unavail", "vals": vals, "caps": [None] * len(views)}
    view = views[rep]
    blocked = [i for i, c in enumerate(caps) if not c.ok]
    return {
        **({"no": blocked} if blocked else {}),
        "kind": "ok", "rep": rep, "vals": vals, "caps": [c.amount if c.ok else None for c in caps],
        "val": vals[rep], "wait": view["wait"], "red": view["red"], "limit": view["limit"],
        "pend": data.verdict_pending(view) or caps[rep].pending,
        "capPend": caps[rep].pending,
    }


def default_base(data: Data, bases: list[str]) -> str | None:
    """기준 열의 처음 값. 기준값 탭의 대표 심사유형(간편고지 약칭)에 맞는 종형, 없으면 첫 종형."""
    wanted = "".join(c for c in data.setting_text("REP_WEEKLY_UW_2") if c.isdigit())
    for vid in bases:
        if wanted and "".join(c for c in str(data.variants[vid].get("간편고지약칭")) if c.isdigit()) == wanted:
            return vid
    return bases[0] if bases else None


def build(data: Data, conds: list[Cond]) -> dict[str, Any]:
    vids = [v for v in data.variant_order if data.variants[v].get("비교역할구분") == COMPARE_ROLE]
    bases = [v for v in vids if data.variants[v].get("기관코드") == HOME_ORG] or list(vids)
    parts = {vid: collect(data, vid) for vid in vids}

    used = [s for s in data.std.values() if s.get("사용여부", True)]
    majors = GROUP_ORDER + [m for m in dict.fromkeys(s["보장대분류"] for s in used) if m not in GROUP_ORDER]
    used.sort(key=lambda s: (majors.index(s["보장대분류"]), str(s["보장중분류"]), str(s["표준담보ID"])))

    rows = []
    for s in used:
        sid = s["표준담보ID"]
        views = {vid: parts[vid][0].get(sid, []) for vid in vids}
        waits = {vid: parts[vid][1].get(sid, []) for vid in vids}
        cells: dict[str, Any] = {}
        tables: dict[str, tuple[list, list]] = {vid: ([], []) for vid in vids}
        for cond in conds:
            cores = {vid: cell_core(data, views[vid], cond, bool(waits[vid])) for vid in vids}
            for vid in vids:
                core = cores[vid]
                state = {k: core[k] for k in ("kind", "rep", "vals", "caps", "capPend", "no") if k in core}
                state["vs"] = ["B" if b == vid else verdict(core, cores[b]) for b in bases]
                key = json.dumps(state, ensure_ascii=False, sort_keys=True)
                states, index = tables[vid]
                if key not in states:
                    states.append(key)
                index.append(states.index(key))
        for vid in vids:
            if not views[vid] and not waits[vid]:
                continue
            states, index = tables[vid]
            cells[vid] = {
                "lines": [v["id"] for v in views[vid]],
                "wait": [v["id"] for v in waits[vid]],
                "st": [json.loads(x) for x in states],
                "by": index,
            }
        rows.append({
            "id": sid, "name": s["표준담보명"], "major": s["보장대분류"], "mid": s["보장중분류"],
            "type": s["급부유형"], "unit": s["비교기준단위만원"], "cells": cells,
            "any": any(views[vid] for vid in vids),
        })

    waiting = waiting_groups(data, vids, parts)
    return {
        "variants": vids, "bases": bases, "defaultBase": default_base(data, bases),
        "peers": {b: peers(data, b, vids) for b in bases},
        "rows": rows, "waiting": waiting, "waitingSummary": waiting_summary(data, waiting),
    }


def _uw_key(variant: dict, exact: bool = True) -> tuple:
    digits = "".join(c for c in str(variant.get("간편고지약칭") or "") if c.isdigit())
    return (variant.get("심사유형"), digits if exact else "")


def peers(data: Data, base: str, vids: list[str]) -> list[str]:
    """기준 종형과 나란히 놓고 볼 종형. 비교표가 처음에 보여 주는 열이다(나머지 종형은 화면에서 체크해 더한다).

    기준 종형과 맞붙는 종형을 다른 회사마다 하나씩 고른다. 심사 등급이 같은 종형(간편심사는 간편고지 약칭이 같은 것,
    일반심사는 일반심사끼리) 가운데 첫째, 그런 종형이 그 회사에 없으면 심사 유형(일반, 간편)이 같은 종형 가운데 첫째다.
    그것도 없으면 그 회사는 고르지 않는다. 기준 종형의 회사는 기준 종형이 그 몫이다. 순서는 vids(화면의 종형 순서)를 따른다.
    회사와 종형이 늘어도 표가 옆으로 길어지지 않게 하려는 것이고, 우열 판정에는 쓰지 않는다.
    """
    home = data.variants[base].get("기관코드")
    picked = {base}
    for org in dict.fromkeys(data.variants[v].get("기관코드") for v in vids):
        if org == home:
            continue
        mine = [v for v in vids if data.variants[v].get("기관코드") == org]
        for exact in (True, False):
            same = [v for v in mine if _uw_key(data.variants[v], exact) == _uw_key(data.variants[base], exact)]
            if same:
                picked.add(same[0])
                break
    return [v for v in vids if v in picked]


def waiting_summary(data: Data, groups: list[dict[str, Any]]) -> dict[str, Any]:
    """매핑 검토 대기 급부의 분포. 화면은 이 요약을 먼저 보여 주고 목록은 접어 둔다."""
    by_rec: dict[Any, int] = {}
    by_org: dict[str, int] = {}
    for g in groups:
        by_rec[g["rec"]] = by_rec.get(g["rec"], 0) + 1
        org = data.variants[g["variants"][0]]["기관코드"]
        by_org[org] = by_org.get(org, 0) + 1
    return {
        "groups": len(groups), "lines": sum(len(g["bids"]) for g in groups),
        "withRec": sum(n for rec, n in by_rec.items() if rec is not None),
        "byRec": [[rec, n] for rec, n in sorted(by_rec.items(), key=lambda kv: (kv[0] is None, -kv[1], str(kv[0])))],
        "byOrg": [{"code": c, "name": data.org_name(c), "n": n} for c, n in sorted(by_org.items(), key=lambda kv: (kv[0] != HOME_ORG, -kv[1], kv[0]))],
    }


def waiting_groups(data: Data, vids: list[str], parts: dict[str, tuple]) -> list[dict[str, Any]]:
    """매핑 검토를 기다리는 급부. 같은 특약의 같은 급부가 종형마다 되풀이되므로 한 줄로 묶는다."""
    groups: dict[tuple, dict[str, Any]] = {}
    for vid in vids:
        _, waiting, loose = parts[vid]
        for view in [v for views in waiting.values() for v in views] + loose:
            rider = data.riders[view["tid"]]
            key = (rider["특약계보키"], view["name"], view["rec"])
            group = groups.setdefault(key, {"bids": [], "variants": [], "rec": view["rec"] if not _blank(view["rec"]) else None})
            group["bids"].append(view["id"])
            group["variants"].append(vid)
    return sorted(groups.values(), key=lambda g: (str(g["rec"]), g["bids"][0]))
