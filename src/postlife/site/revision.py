"""화면 5: 개정 전후 비교(기본형).

종형은 종형계보키, 특약은 특약계보키가 같은 것끼리 잇는다(기획 5.3, 8장).
급부는 계보키가 없어 이름으로 잇는다: 같은 이름을 먼저 짝짓고, 남은 줄은 괄호 안 설명을 뗀 이름이 비슷한 것끼리 짝짓는다.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from .. import ids
from . import eligibility
from .compare import _sign, compare_reduction, scaled
from .model import Cond, Data, MAIN_KIND, _blank

SIMILAR_STEM = 0.75     # 괄호를 뗀 이름이 이만큼 비슷해야 같은 급부 후보로 본다
_PAREN = re.compile(r"\([^()]*\)")


def _stem(name: str) -> str:
    """괄호 안 설명을 뗀 급부 이름. "재해골절(치아파절제외)보험금(재해골절)" → "재해골절보험금"."""
    text = str(name)
    while _PAREN.search(text):
        text = _PAREN.sub("", text)
    return ids.normalize(text) or ids.normalize(name)


def variant_pairs(data: Data) -> list[tuple[str, str]]:
    """같은 계보의 종형을 적용시작일 순으로 놓고 이웃한 개정판끼리 (개정 전, 개정 후)로 짝짓는다."""
    lineages: dict[str, list[str]] = {}
    for vid, v in data.variants.items():
        if not _blank(v.get("종형계보키")):
            lineages.setdefault(v["종형계보키"], []).append(vid)
    out = []
    for vids in lineages.values():
        vids.sort(key=lambda v: (str(data.variants[v].get("적용시작일")), str(data.variants[v].get("개정판ID"))))
        for old, new in zip(vids, vids[1:]):
            if data.variants[old].get("개정판ID") != data.variants[new].get("개정판ID"):
                out.append((old, new))
    order = {vid: i for i, vid in enumerate(data.variant_order)}
    return sorted(out, key=lambda p: order[p[1]])


def match_benefits(old: list[dict], new: list[dict]) -> tuple[list[tuple[dict, dict, str]], list[dict], list[dict]]:
    """(이어진 급부 [(전, 후, 이은 방법)], 없어진 급부, 새로 생긴 급부)."""
    pairs: list[tuple[dict, dict, str]] = []
    left = list(new)
    rest = []
    for o in old:
        same = next((n for n in left if ids.normalize(n["name"]) == ids.normalize(o["name"])), None)
        if same is not None:
            left.remove(same)
            pairs.append((o, same, "이름"))
        else:
            rest.append(o)
    # 남은 줄은 괄호를 뗀 이름이 비슷한 것끼리 후보로 삼고, 그 안에서 전체 이름이 가장 비슷한 것부터 짝짓는다.
    # 괄호 안 설명만 고쳐 쓴 급부("…보험금(재해)" → "…보험금(재해골절)")가 엉뚱한 급부에 이어지지 않게 하기 위함이다.
    scored = []
    for o in rest:
        for n in left:
            if o["std"] and n["std"] and o["std"] != n["std"]:
                continue
            stem = SequenceMatcher(None, _stem(o["name"]), _stem(n["name"])).ratio()
            if stem >= SIMILAR_STEM:
                whole = SequenceMatcher(None, ids.normalize(o["name"]), ids.normalize(n["name"])).ratio()
                scored.append(((stem, whole), o["id"], n["id"], o, n))
    used_old: set[str] = set()
    used_new: set[str] = set()
    for _, _, _, o, n in sorted(scored, key=lambda s: (-s[0][0], -s[0][1], s[1], s[2])):
        if o["id"] in used_old or n["id"] in used_new:
            continue
        used_old.add(o["id"])
        used_new.add(n["id"])
        pairs.append((o, n, "비슷한 이름"))
    removed = [o for o in rest if o["id"] not in used_old]
    added = [n for n in left if n["id"] not in used_new]
    return pairs, removed, added


def benefit_changes(o: dict, n: dict, top_old: float | None, top_new: float | None) -> list[dict[str, Any]]:
    """급부 한 쌍에서 달라진 항목. dir은 개정 후가 나아졌으면 "+", 못해졌으면 "-", 엇갈리면 "~", 가릴 수 없으면 None.

    지급액(pay)은 지급 기준에 따라 견준다. 금액 급부끼리는 (기준지급금액, 기준가입금액)이 다르면 달라진 것이다.
    가입금액 대비 비율로 적힌 급부끼리는 지급률이 다를 때만 달라진 것이다(같은 50%를 100에 50, 1,000에 500으로 적은 것은 같다).
    금액 급부가 비율 급부로(또는 그 반대로) 바뀌면 숫자가 같아도 달라진 것으로 적고, 가입금액당 지급액이 같으면 방향은 None이다.
    금액 하나로 담기지 않는 급부(form)는 그 값이 다르면(금액 급부에서 바뀐 경우 포함) 지급액이 달라진 것이고 방향은 None이다.
    이때 지급액 항목에 forms([개정 전 값, 개정 후 값])를 싣는다. 감액은 금액 없는 쪽이 읽지 않은 칸이라 달라져도 방향은 None이다.
    두 쪽이 같은 금액 없는 값이면 지급률 표가 바뀌었어도 여기서는 알아보지 못한다(작업 로그의 내용 지문으로 볼 일. 나중에 더한다).
    """
    items: list[dict[str, Any]] = []
    unit_old, unit_new = scaled(o["pay"], o["base"], 1), scaled(n["pay"], n["base"], 1)
    ratio_old, ratio_new = bool(o.get("ratio")), bool(n.get("ratio"))
    form_old, form_new = o.get("form"), n.get("form")
    if form_old != form_new:
        pay_changed = True
    elif ratio_old != ratio_new:
        pay_changed = True
    elif ratio_old:
        pay_changed = o.get("rate") != n.get("rate")
    else:
        pay_changed = (o["pay"], o["base"]) != (n["pay"], n["base"])
    if pay_changed:
        direction = _sign(unit_new, unit_old) if unit_old is not None and unit_new is not None else None
        if (ratio_old != ratio_new and direction == "=") or form_old != form_new:
            direction = None
        item = {"field": "pay", "old": [o["base"], o["pay"]], "new": [n["base"], n["pay"]], "dir": direction}
        if form_old or form_new:
            item["forms"] = [form_old, form_new]
        items.append(item)
    if top_old != top_new:
        direction = _sign(top_new, top_old) if top_old is not None and top_new is not None else None
        items.append({"field": "top", "old": top_old, "new": top_new, "dir": direction})
    if o["red"] != n["red"]:
        direction = compare_reduction(n["red"], o["red"]) if not (form_old or form_new) else None
        items.append({"field": "red", "old": o["red"], "new": n["red"], "dir": direction})
    if o["wait"] != n["wait"]:
        items.append({"field": "wait", "old": o["wait"], "new": n["wait"], "dir": _sign(o["wait"], n["wait"])})
    if "".join(str(o["limit"] or "").split()) != "".join(str(n["limit"] or "").split()):
        items.append({"field": "limit", "old": o["limit"], "new": n["limit"], "dir": None})
    if o["std"] != n["std"]:
        items.append({"field": "std", "old": o["std"], "new": n["std"], "dir": None})
    return items


def rider_changes(o: dict, n: dict) -> list[dict[str, Any]]:
    items = []
    old_range, new_range = [o.get("최소가입금액만원"), o.get("최대가입금액만원")], [n.get("최소가입금액만원"), n.get("최대가입금액만원")]
    if old_range != new_range:
        items.append({"field": "range", "old": old_range, "new": new_range, "dir": None})
    old_renew = o.get("갱신주기년") if o.get("갱신여부") else 0
    new_renew = n.get("갱신주기년") if n.get("갱신여부") else 0
    if old_renew != new_renew:
        items.append({"field": "renew", "old": old_renew, "new": new_renew, "dir": None})
    return items


def diff_pair(data: Data, old_vid: str, new_vid: str) -> dict[str, Any]:
    none = Cond()
    old_by_key = {data.riders[t]["특약계보키"]: t for t in data.riders_of.get(old_vid, [])}
    new_by_key = {data.riders[t]["특약계보키"]: t for t in data.riders_of.get(new_vid, [])}
    changes: list[dict[str, Any]] = []
    same_riders = 0
    for key, old_tid in old_by_key.items():
        new_tid = new_by_key.get(key)
        if new_tid is None:
            continue
        entry: dict[str, Any] = {"old": old_tid, "new": new_tid, "rider": rider_changes(data.riders[old_tid], data.riders[new_tid]),
                                 "benefits": [], "removed": [], "added": []}
        old_views = [data.benefit_view(b) for b in data.benefits_of.get(old_tid, [])]
        new_views = [data.benefit_view(b) for b in data.benefits_of.get(new_tid, [])]
        pairs, removed, added = match_benefits(old_views, new_views)
        cap_old, cap_new = data.rider_cap(old_tid, none), data.rider_cap(new_tid, none)
        for o, n, how in pairs:
            top_old = scaled(o["pay"], o["base"], cap_old.amount)     # 개정 전 특약을 최대로 가입했을 때의 지급액
            top_new = scaled(n["pay"], n["base"], cap_new.amount)
            items = benefit_changes(o, n, top_old, top_new)
            if items:
                entry["benefits"].append({"old": o["id"], "new": n["id"], "how": how, "items": items,
                                          "top": [top_old, top_new]})
        entry["removed"] = [o["id"] for o in removed]
        entry["added"] = [n["id"] for n in added]
        if entry["rider"] or entry["benefits"] or entry["removed"] or entry["added"]:
            changes.append(entry)
        else:
            same_riders += 1

    old_v, new_v = data.variants[old_vid], data.variants[new_vid]
    labels = eligibility.gate(old_v).keys()
    gate_old, gate_new = eligibility.gate(old_v), eligibility.gate(new_v)
    old_main, new_main = data.main_rider(old_vid), data.main_rider(new_vid)
    ages_old = {s: eligibility.segments(data, old_main, s) if old_main else [] for s in ("M", "F")}
    ages_new = {s: eligibility.segments(data, new_main, s) if new_main else [] for s in ("M", "F")}
    return {
        "old": old_vid, "new": new_vid,
        "changes": changes,
        "sameRiders": same_riders,
        "removedRiders": [t for k, t in old_by_key.items() if k not in new_by_key and data.riders[t]["담보구분"] != MAIN_KIND],
        "addedRiders": [t for k, t in new_by_key.items() if k not in old_by_key and data.riders[t]["담보구분"] != MAIN_KIND],
        "gate": [{"field": f, "old": gate_old[f], "new": gate_new[f]} for f in labels],
        "uw": {"old": [old_v.get("심사유형"), old_v.get("간편고지약칭")], "new": [new_v.get("심사유형"), new_v.get("간편고지약칭")]},
        "ages": {"old": ages_old, "new": ages_new},
    }


def build(data: Data) -> dict[str, Any]:
    starts = [str(v["적용시작일"]) for v in data.variants.values() if not _blank(v.get("적용시작일"))]
    ends = [str(v["판매종료일"]) for v in data.variants.values() if not _blank(v.get("판매종료일"))]
    today = str(data.meta.get("snapshot_at") or "")[:10]
    return {
        "pairs": [diff_pair(data, old, new) for old, new in variant_pairs(data)],
        "timeline": {"from": min(starts) if starts else None, "to": max(ends + ([today] if today else []) + starts) if starts else None,
                     "today": today or None, "variants": list(data.variant_order)},
    }
