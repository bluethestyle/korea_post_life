"""화면 2: 가입 적격과 간편심사 고지 관문.

나이·보험기간·납입기간·한도까지만 다룬다. 병력으로 인수 여부를 가리지 않는다.
"""
from __future__ import annotations

from typing import Any

from .model import Cond, Data, MAIN_KIND, MAX_AGE, _blank


def _ages(rows: list[dict]) -> range:
    if not rows:
        return range(0)
    return range(min(r["최저가입나이"] for r in rows), max(r["최고가입나이"] for r in rows) + 1)


def segments(data: Data, tid: str, sex: str) -> list[dict[str, Any]]:
    """가입할 수 있는 나이를 최대 가입금액이 같은 구간으로 묶는다.

    보험기간·납입기간에 따라 가입나이가 다르면 그 가운데 하나라도 되는 나이를 가입 가능으로 본다.
    """
    rows = data.condition_rows(tid)
    out: list[dict[str, Any]] = []
    for age in _ages(rows):
        limit = data.age_limit(tid, Cond(age=age, sex=sex))
        if not limit.ok:
            continue
        last = out[-1] if out else None
        if last and last["hi"] == age - 1 and last["max"] == limit.amount and last["pend"] == limit.pending:
            last["hi"] = age
        else:
            out.append({"lo": age, "hi": age, "max": limit.amount, "pend": limit.pending})
    return out


def period_table(data: Data, tid: str) -> list[dict[str, Any]]:
    """보험기간·납입기간(·성별) 조합마다 가입나이 구간과 한도."""
    groups: dict[tuple, list[dict]] = {}
    for r in data.condition_rows(tid):
        groups.setdefault((str(r["보험기간구분"]), str(r["납입기간구분"]), r.get("성별") or ""), []).append(r)
    out = []
    for (term, pay, sex), rows in sorted(groups.items(), key=lambda kv: (_number(kv[0][0]), _number(kv[0][1]), kv[0])):
        ranges = [{"lo": r["최저가입나이"], "hi": r["최고가입나이"], "max": r.get("구간최대가입금액만원"),
                   "pend": data.pending_condition.get(r["조건행ID"], [])}
                  for r in sorted(rows, key=lambda r: r["최저가입나이"])]
        out.append({"term": term, "pay": pay, "sex": sex or None, "ranges": ranges})
    return out


def _number(text: str) -> int:
    digits = "".join(c for c in text if c.isdigit())
    return int(digits) if digits else 10 ** 6


def gate(variant: dict) -> dict[str, Any]:
    """간편심사 고지 질문. 값이 없으면 None으로 두고 화면이 "자료 없음"으로 적는다."""
    return {
        "months": variant.get("고지최근소견개월"),
        "hospYears": variant.get("고지입원수술년수"),
        "surgery": variant.get("고지수술포함여부"),
        "majorYears": variant.get("고지중대질병년수"),
        "majorCount": variant.get("고지중대질병수"),
    }


def build(data: Data, conds: list[Cond]) -> dict[str, Any]:
    by_variant = {}
    top_age = 100
    for vid in data.variant_order:
        main = data.main_rider(vid)
        riders = []
        for tid in data.riders_of.get(vid, []):
            if data.riders[tid]["담보구분"] == MAIN_KIND:
                continue
            seg = {sex: segments(data, tid, sex) for sex in ("M", "F")}
            riders.append({
                "tid": tid,
                "seg": seg,
                "ok": [data.rider_cap(tid, c).ok for c in conds],
                "noCond": not data.condition_rows(tid),
            })
        seg = {sex: segments(data, main, sex) for sex in ("M", "F")} if main else {"M": [], "F": []}
        for s in seg.values():
            top_age = max([top_age] + [x["hi"] for x in s])
        limits = [data.age_limit(main, c) for c in conds] if main else []
        by_variant[vid] = {
            "main": main,
            "seg": seg,
            "noCond": not (main and data.condition_rows(main)),
            "ok": [l.ok for l in limits],
            "lim": [l.amount if l.ok else None for l in limits],
            "periods": period_table(data, main) if main else [],
            "riders": riders,
        }
    return {
        "variants": list(data.variant_order),
        "byVariant": by_variant,
        "axisMax": min(MAX_AGE, -(-top_age // 10) * 10),
        "hasSexRows": data.has_sex_rows(),
    }
