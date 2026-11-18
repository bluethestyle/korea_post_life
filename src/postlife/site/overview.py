"""맨 위 안내 줄과 화면 1(자리만 둠)에 쓰는 사실 집계. 자료에 있는 것만 센다."""
from __future__ import annotations

from typing import Any

from .model import CONFIRMED_STATES, Data, EXCLUDED_STATE, HOME_ORG, WAITING_STATE, _blank


def build(data: Data) -> dict[str, Any]:
    orgs: dict[str, int] = {}
    for v in data.variants.values():
        orgs[v["기관코드"]] = orgs.get(v["기관코드"], 0) + 1
    passed = data.setting_num("기사선별_통과")
    trends = [t for t in data.trends if passed is None or t.get("판정확률") is None or t["판정확률"] >= passed]
    by_kind: dict[str, int] = {}
    by_org: dict[str, int] = {}
    for t in trends:
        by_kind[t["분류유형"]] = by_kind.get(t["분류유형"], 0) + 1
        by_org[t["기관코드"]] = by_org.get(t["기관코드"], 0) + 1
    states = [m.get("검토상태") for m in data.mapping.values()]
    revisions = {v["개정판ID"] for v in data.variants.values()}
    return {
        "homeOrg": HOME_ORG, "homeName": data.org_name(HOME_ORG),
        "orgs": [{"code": c, "name": data.org_name(c), "variants": n} for c, n in sorted(orgs.items(), key=lambda kv: (kv[0] != HOME_ORG, kv[0]))],
        "counts": {
            "variants": len(data.variants), "onSale": sum(1 for v in data.variants.values() if _blank(v.get("판매종료일"))),
            "revisions": len(revisions), "riders": len(data.riders), "benefits": len(data.benefits),
            "mapped": sum(1 for s in states if s in CONFIRMED_STATES), "waiting": states.count(WAITING_STATE),
            "excluded": states.count(EXCLUDED_STATE),
            "pendingBenefits": len(data.pending_benefit), "pendingConditions": len(data.pending_condition),
            "premiums": len(data.tables.get("sys_보험료예시", [])), "diseaseCodes": len(data.tables.get("sys_급부질병코드", [])),
            "logs": len(data.logs),
        },
        "trends": {
            "total": len(data.trends), "shown": len(trends),
            "weeks": sorted({str(t["수집주차"]) for t in trends}),
            "from": min((str(t["발표일자"]) for t in trends), default=None),
            "to": max((str(t["발표일자"]) for t in trends), default=None),
            "byKind": sorted(by_kind.items(), key=lambda kv: (-kv[1], kv[0])),
            "byOrg": sorted(((data.org_name(c), n) for c, n in by_org.items()), key=lambda kv: (-kv[1], kv[0])),
        },
    }
