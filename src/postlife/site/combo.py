"""화면 4: 특약 조합과 담보별 실제 지급액.

가입금액은 사용자가 화면에서 직접 고르므로 조합 계산은 화면(assets/calc.js)이 한다.
이 모듈은 (1) 화면에 넘길 종형별 조합 자료를 만들고 (2) 같은 계산 규칙을 Python으로도 갖고 있다.
시험(tests/test_site.py)이 같은 입력을 양쪽에 넣어 결과가 같은지 본다. 규칙을 고치면 calc.js도 함께 고친다.

제약 규칙
- 주계약에 가입할 수 없으면 특약도 가입할 수 없다.
- 선행가입: 기준특약에 가입해야 대상특약을 고를 수 있다. 수치(만원)가 있으면 기준특약 가입금액이 그 이상이어야 한다.
- 최대연동: 대상특약 가입금액 ≤ 기준특약 가입금액 × 제약수치(단위가 만원이면 그 금액).
- 배타선택: 기준특약에 가입하면 대상특약을 고를 수 없다.
- 의무부가: 기준특약에 가입하면 대상특약이 함께 붙는다.
- 가입금액은 특약의 최소 가입금액과 나이 구간 한도 사이에서만 고를 수 있다.
"""
from __future__ import annotations

from typing import Any

from .compare import COMPARE_ROLE, pick_rep, scaled
from .model import Cond, Data, is_ratio

KNOWN_RULES = {"선행가입", "최대연동", "배타선택", "의무부가"}


# ---------- 화면에 넘길 자료 ----------
def variant_model(data: Data, vid: str, conds: list[Cond]) -> dict[str, Any]:
    """refRatio는 ref가 비율 급부의 기준가입금액인지다. 그 금액(관례로 100만원)은 지급률을 적으려고 둔 값이라
    공시 문서의 기준 가입금액이 아니므로, 화면은 처음 넣어 두는 금액을 "계산용 예시 금액"이라고 밝힌다."""
    riders = []
    for tid in data.riders_of.get(vid, []):
        r = data.riders[tid]
        limits = [data.age_limit(tid, c) for c in conds]
        ref_bid = reference_benefit(data, tid)
        riders.append({
            "tid": tid, "min": r.get("최소가입금액만원"), "max": r.get("최대가입금액만원"),
            "ref": data.benefits[ref_bid]["기준가입금액만원"] if ref_bid else None,
            "refRatio": bool(ref_bid and is_ratio(data.benefits[ref_bid])),
            "ok": [l.ok for l in limits],
            "lim": [l.amount if l.ok else None for l in limits],
            "limPend": [l.pending for l in limits],
            "noCond": not data.condition_rows(tid),
            "benefits": list(data.benefits_of.get(tid, [])),
        })
    known = {r["tid"] for r in riders}
    rules, skipped = [], []
    for c in data.constraints_of.get(vid, []):
        rule = {"type": c["제약유형"], "base": c["기준특약ID"], "target": c["대상특약ID"],
                "num": c.get("제약수치"), "unit": c.get("제약단위"), "text": c.get("근거문구")}
        if rule["type"] in KNOWN_RULES and rule["base"] in known and rule["target"] in known and rule["base"] != rule["target"]:
            rules.append(rule)
        else:
            skipped.append(rule)
    return {"main": data.main_rider(vid), "riders": riders, "rules": rules, "skipped": skipped}


def reference_benefit(data: Data, tid: str) -> str | None:
    """급부표가 기준으로 삼은 가입금액(ref)을 가진 급부. ref는 가입 한도 자료가 없는 특약을 고를 때 화면이 처음에 넣어 두는 금액이다.

    계산 규칙(evaluate)은 이 값을 쓰지 않는다. 급부마다 기준이 다르면 대표 순서(주급부, 금액 큰 순)의 첫 줄을 따른다.
    금액 급부와 비율 급부가 섞인 특약은 금액 급부의 줄을 먼저 쓴다. 비율 급부의 기준가입금액(관례로 100)은 지급률을 적으려고 둔 값이라
    공시 문서의 기준 가입금액이 아니고, 대표 순서의 "금액"도 비율 급부에서는 지급률 숫자라 금액과 견줄 수 없기 때문이다.
    금액 급부에 기준가입금액이 없을 때만 비율 급부의 줄을 쓰고, 화면은 그 금액을 계산용 예시 금액이라고 밝힌다(refRatio).
    """
    found = [bid for bid in data.benefits_of.get(tid, []) if data.benefits[bid].get("기준가입금액만원")]
    return next((bid for bid in found if not is_ratio(data.benefits[bid])), found[0] if found else None)


def build(data: Data, conds: list[Cond]) -> dict[str, Any]:
    vids = [v for v in data.variant_order if data.variants[v].get("비교역할구분") == COMPARE_ROLE]
    return {"variants": vids, "byVariant": {vid: variant_model(data, vid, conds) for vid in vids}}


# ---------- 계산 규칙 (calc.js의 evaluate, payouts와 같아야 한다) ----------
def _ceiling(rule: dict, base_amount: float | None) -> float | None:
    if rule.get("num") is None:
        return base_amount
    if rule.get("unit") == "만원":
        return float(rule["num"])
    return None if base_amount is None else base_amount * float(rule["num"])


def evaluate(vm: dict[str, Any], k: int, want: dict[str, float | None]) -> dict[str, Any]:
    """고른 조합에 제약을 적용한다.

    vm: variant_model의 결과, k: 조건 번호, want: {특약ID: 원하는 가입금액}. 금액이 None이면 고를 수 있는 최대.
    주계약은 want에 없어도 가입한 것으로 본다.
    돌려주는 값: {"rows": [{tid, on, amount, lo, hi, reasons, forced, clamped}]}.
    reasons가 비어 있지 않으면 고를 수 없는 특약이다.
    """
    order = [r["tid"] for r in vm["riders"]]
    by_id = {r["tid"]: r for r in vm["riders"]}
    main = vm.get("main")
    selected = {t for t in want if t in by_id} | ({main} if main in by_id else set())
    amounts: dict[str, float | None] = {}
    rows: list[dict[str, Any]] = []
    for _ in range(len(order) + 3):
        new_selected: set[str] = set()
        new_amounts: dict[str, float | None] = {}
        rows = []
        done: set[str] = set()

        def is_on(tid: str) -> bool:
            return tid in new_selected if tid in done else tid in selected

        def amount_of(tid: str) -> float | None:
            return new_amounts.get(tid) if tid in done else amounts.get(tid)

        for tid in order:
            r = by_id[tid]
            lo = r.get("min") or 0
            hi = r["lim"][k]
            reasons: list[dict[str, Any]] = []
            forced = False
            if not r["ok"][k]:
                reasons.append({"code": "age"})
            if tid != main and (main is None or not is_on(main)):
                reasons.append({"code": "main"})
            for rule in vm["rules"]:
                if rule["target"] != tid:
                    continue
                base = rule["base"]
                if rule["type"] == "선행가입":
                    if not is_on(base):
                        if base != main:               # 주계약이 기준이면 위의 "main" 사유와 같은 말이다
                            reasons.append({"code": "need", "base": base})
                    elif rule.get("num") is not None and rule.get("unit") == "만원" and (amount_of(base) or 0) < rule["num"]:
                        reasons.append({"code": "needAmount", "base": base, "num": rule["num"]})
                elif rule["type"] == "최대연동":
                    if not is_on(base):
                        if base != main:
                            reasons.append({"code": "need", "base": base})
                    else:
                        top = _ceiling(rule, amount_of(base))
                        if top is not None and (hi is None or top < hi):
                            hi = top
                elif rule["type"] == "배타선택":
                    if is_on(base):
                        reasons.append({"code": "exclusive", "base": base})
                elif rule["type"] == "의무부가":
                    if is_on(base):
                        forced = True
            if not reasons and hi is not None and lo > hi:
                reasons.append({"code": "belowMin", "hi": hi})
            on = not reasons and (tid == main or tid in want or forced)
            amount = None
            clamped = False
            if on:
                asked = want.get(tid)
                amount = asked if asked is not None else (hi if hi is not None else (r.get("max") if r.get("max") is not None else lo))
                if hi is not None and amount > hi:
                    amount = hi
                if amount < lo:
                    amount = lo
                clamped = asked is not None and amount != asked
                new_selected.add(tid)
                new_amounts[tid] = amount
            done.add(tid)
            rows.append({"tid": tid, "on": on, "amount": amount, "lo": lo, "hi": hi,
                         "reasons": reasons, "forced": forced and on, "clamped": clamped})
        if new_selected == selected and new_amounts == amounts:
            break
        selected, amounts = new_selected, new_amounts
    return {"rows": rows}


def payouts(vm: dict[str, Any], benefits: dict[str, dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """가입한 특약의 급부를 가입금액에 비례해 환산하고 표준담보별로 묶는다.

    한 표준담보에 줄이 여럿이면 더하지 않고 대표 줄을 고른다(원인이 다른 급부를 더하면 과장되기 때문).
    돌려주는 값: {"groups": [{std, rep, lines}], "others": [표준담보에 이어지지 않은 급부]}.
    lines의 각 줄은 {bid, val, reduced}이고 reduced는 [[개월, 감액 기간의 지급액], ...].
    """
    by_id = {r["tid"]: r for r in vm["riders"]}
    groups: dict[str, list[dict[str, Any]]] = {}
    others: list[dict[str, Any]] = []
    for row in rows:
        if not row["on"]:
            continue
        for bid in by_id[row["tid"]]["benefits"]:
            b = benefits[bid]
            val = scaled(b.get("pay"), b.get("base"), row["amount"])
            line = {"bid": bid, "val": val,
                    "reduced": [[m, None if val is None else val * rate] for m, rate in b.get("red") or []]}
            if b.get("std"):
                groups.setdefault(b["std"], []).append(line)
            else:
                others.append(line)
    out = []
    for std, lines in groups.items():
        cands = [{"i": i, "role": benefits[l["bid"]]["role"], "val": l["val"], "pay": benefits[l["bid"]].get("pay"),
                  "base": benefits[l["bid"]].get("base"), "ratio": benefits[l["bid"]].get("ratio"),
                  "wait": benefits[l["bid"]].get("wait"), "red": benefits[l["bid"]].get("red"),
                  "name": benefits[l["bid"]]["name"]} for i, l in enumerate(lines)]
        out.append({"std": std, "rep": pick_rep(cands), "lines": lines})
    return {"groups": out, "others": others}
