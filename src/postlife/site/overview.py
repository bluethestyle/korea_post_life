"""맨 위 안내 줄과 화면 1에 쓰는 사실 집계. 자료에 있는 것만 센다.

이번 주에 달라진 것(개정판, 시장 소식, 대표 조건의 우열 변화)은 weekly.py가 만들고 여기서 함께 싣는다.
"""
from __future__ import annotations

from typing import Any

from . import weekly
from .model import CONFIRMED_STATES, Data, EXCLUDED_STATE, HOME_ORG, WAITING_STATE


def build(data: Data, previous: Data | None = None) -> dict[str, Any]:
    orgs: dict[str, int] = {}
    for v in data.variants.values():
        orgs[v["기관코드"]] = orgs.get(v["기관코드"], 0) + 1
    # 판정확률이 있고 통과 기준 이상인 소식만 센다. 판정확률이 없는 소식은 "미판정" 건수로만 적는다.
    trends = [t for t in data.trends if weekly.news_state(data, t) == "passed"]
    by_kind: dict[str, int] = {}
    by_org: dict[str, int] = {}
    for t in trends:
        by_kind[t["분류유형"]] = by_kind.get(t["분류유형"], 0) + 1
        by_org[t["기관코드"]] = by_org.get(t["기관코드"], 0) + 1
    gaps: dict[str, dict[str, Any]] = {}
    for vid, v in data.variants.items():
        gap = data.limit_gap(vid)
        if gap:
            g = gaps.setdefault(v["기관코드"], {"code": v["기관코드"], "name": data.org_name(v["기관코드"]), "variants": 0,
                                               "riders": 0, "noMax": 0, "noAge": 0})
            g["variants"] += 1
            g["riders"] += gap["riders"]
            g["noMax"] += gap["noMax"]
            g["noAge"] += 1 if gap["noAge"] else 0
    states = [m.get("검토상태") for m in data.mapping.values()]
    revisions = {v["개정판ID"] for v in data.variants.values()}
    today = weekly.today_of(data)           # 판매 중은 대표 조건의 우열 비교와 같은 기준으로 센다(weekly.on_sale)
    return {
        "homeOrg": HOME_ORG, "homeName": data.org_name(HOME_ORG),
        "limitGaps": [gaps[c] for c in sorted(gaps, key=lambda c: (c != HOME_ORG, c))],
        "orgs": [{"code": c, "name": data.org_name(c), "variants": n} for c, n in sorted(orgs.items(), key=lambda kv: (kv[0] != HOME_ORG, kv[0]))],
        "counts": {
            "variants": len(data.variants), "onSale": sum(1 for v in data.variants.values() if weekly.on_sale(v, today)),
            "revisions": len(revisions), "riders": len(data.riders), "benefits": len(data.benefits),
            "mapped": sum(1 for s in states if s in CONFIRMED_STATES), "waiting": states.count(WAITING_STATE),
            "excluded": states.count(EXCLUDED_STATE),
            "pendingBenefits": len(data.pending_benefit), "pendingConditions": len(data.pending_condition),
            "premiums": len(data.tables.get("sys_보험료예시", [])), "diseaseCodes": len(data.tables.get("sys_급부질병코드", [])),
            "logs": len(data.logs),
        },
        **weekly.build(data, previous),
        "trends": {
            "total": len(data.trends), "shown": len(trends),
            "undecided": sum(1 for t in data.trends if weekly.news_state(data, t) == "undecided"),
            "weeks": sorted({str(t["수집주차"]) for t in trends}),
            "from": min((str(t["발표일자"]) for t in trends), default=None),
            "to": max((str(t["발표일자"]) for t in trends), default=None),
            "byKind": sorted(by_kind.items(), key=lambda kv: (-kv[1], kv[0])),
            "byOrg": sorted(((data.org_name(c), n) for c, n in by_org.items()), key=lambda kv: (-kv[1], kv[0])),
        },
    }
