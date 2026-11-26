"""시안 4가 `const D`로 읽는 자료(간편 3.1.5, 3.2.5, 3.5.5 세 등급 x 화면에 올린 회사 종형의 비교 자료)를 사본에서 만든다.

처음 시안(site/proto/console.html, 2026-11-20)의 자료를 만든 스크립트를 그대로 옮겼다. 그 스크립트를 그때의 사본
(2026-11-20T15:15:56+09:00)과 지금 코드로 돌린 결과가 console.html 474번 줄과 바이트까지 같은 것을 확인하고 옮겼다.
열쇠, 꼴, 계산 규칙을 바꾸지 않는다(시안 4의 core.js 가 읽는다). 2026-11-23 에 세 회사로 적어 두었던 회사와 종형을 화면에 올린
회사에서 고르게 바꿨다(세 회사 사본의 결과는 바이트까지 같다). 상대가 셋 이상이면 시사점(_insights)의 빈자리와 고유는
상대 모두를, 조건 차이는 상대 모두가 가진 담보를 본다(두 상대일 때의 규칙을 상대 수만큼 늘린 것).

- 회사는 화면에 올린 회사(사본을 읽을 때 site/orgs.py 가 config.SITE_ORGS 나 --orgs 로 거른 회사)다. 차례는 config.SITE_ORGS 의
  차례(우체국이 처음), 그 밖의 회사는 사본의 종형 차례다(company_codes).
- 종형은 간편 세 등급(GRADES)마다 회사마다 하나다(pick_lineup). 비교역할구분이 정밀비교이고 판매종료일이 비었으며 간편고지약칭이
  그 등급인 종형이 하나뿐이면 그 종형, 없거나 둘 이상이면 고르지 않고 null 로 둔다. 우체국 종형을 고를 수 없으면 멈춘다.
  우체국 종형이 한 등급에 둘 이상이면 화면 기본 상품(screen.DEFAULT_PRODUCT)의 종형을 고른다(2026-11-25).
  세 회사 사본에서는 우체국 간편한건강 2606, 한화생명 시그니처 H 간편가입형, 삼성화재 새로고침 7종의 아홉 개(2026-11-23 전에
  손으로 적어 두었던 LINEUP 과 같다)이고, 메리츠화재를 넣으면 통합간편건강보험 2610 의 315, 325, 355 간편심사형이 더해진다.
- hum_담보매핑에서 검토상태가 "자동확정"인 줄만 쓴다. 승인, 수정, 대기 줄은 표준담보에 잇지 않는다.
- 대표 급부, 최대 가입 시 지급액, 나이 구간별 가입 가능 여부는 화면 코드(compare, model)를 그대로 부른다.
- 우열은 면책과 감액만 견준다. 한화생명과 삼성화재는 특약 가입 한도 자료가 없어 지급액 자체의 우열은 가리지 않는다.
- 값을 지어내지 않는다. 자료에 없는 칸은 null 로 둔다.

시안 4에서 실제로 읽는 열쇠는 `orgs`(회사 짧은 이름, core.js)뿐이다. 탭 2의 개정 변동 근거는 sales.json 의 `표준담보`를,
담보 비교표와 관계 그림은 cover.json 을 읽는다. 나머지 열쇠는 시안 1~3의 비교 화면용이고, 모양을 지키려고 함께 싣는다.
"""
from __future__ import annotations

import json
from typing import Any

from .. import config
from . import compare as C
from . import screen as SC
from .model import HOME_ORG, MAX_AGE, Cond, Data

STATE = "자동확정"

SHORT = {"EPOST": "우체국", "HANWHALIFE": "한화생명", "SAMSUNGFIRE": "삼성화재"}
GRADES = ["3.1.5", "3.2.5", "3.5.5"]     # 심사 등급(간편고지 약칭)
DEFAULT_GRADE = "3.2.5"
# 비교 화면에 싣는 표준담보 16개. 3.2.5 세 종형 가운데 둘 이상이 자동확정 급부를 가진 것에서 암, 뇌혈관, 심장, 공통이 섞이게 골랐다.
COMPARE = [
    "STD_CA_DX_GENERAL", "STD_CA_DX_PSEUDO", "STD_CA_DX_INTEGRATED", "STD_CA_SURG", "STD_CA_TX_TARGET",
    "STD_CA_TX_CHEMORADIO", "STD_CA_TX_MAJOR",
    "STD_BR_DX_CEREBRO", "STD_BR_DX_HEMORRHAGE",
    "STD_HT_DX_AMI", "STD_HT_DX_IHD", "STD_HT_SURG",
    "STD_CM_HOSP_DISEASE", "STD_CM_HOSP_CAREGIVER", "STD_CM_SURG_GRADE", "STD_CM_SURG_INJURY",
]
GROUPS = ["암보장", "뇌혈관보장", "심장보장", "뇌심장보장", "공통보장"]
TYPES = ["진단", "수술", "치료", "입원", "통원"]
SIBLINGS = 3          # 담보 칸마다 싣는 급부 수(대표 급부들 + 나머지에서 앞의 것)
TOP = 5               # 시사점 카드마다 초점까지 열 수 있게 자료를 싣는 담보 수

KEYS = ["asOf", "orgs", "lineup", "defaultGrade", "bands", "stds", "std", "groups", "types",
        "compare", "pool", "variants", "riders", "benefits", "cells", "conds", "payloads"]


def terms(other: dict, base: dict) -> str:
    """우체국(base) 대비 경쟁사(other)의 면책, 감액. 첫 글자 종합(b 경쟁사 나음, w 경쟁사 못함, s 같음, m 엇갈림),
    이어 면책, 감액 부호(+ 경쟁사 나음, - 경쟁사 못함, = 같음, ~ 엇갈림). 판정 대기 값이 있으면 p."""
    # 부호는 compare.verdict와 같다: n 경쟁사에 없음, q 검토 대기 급부만 있음, u 경쟁사가 이 나이에 받지 않음,
    # o 우체국에 없음, v 우체국이 이 나이에 받지 않음, "" 둘 다 없음
    if other["p"] in "nw":
        if other["p"] == "w":
            return "q"
        return "" if base["p"] == "n" else "n"
    if other["p"] == "u":
        return "u"
    if base["p"] in "nw":
        return "q" if base["p"] == "w" else "o"
    if base["p"] == "u":
        return "v"
    if other["pend"] or base["pend"]:
        return "p"
    parts = [C._sign(base["wait"], other["wait"]), C.compare_reduction(other["red"], base["red"])]
    if "~" in parts or ("+" in parts and "-" in parts):
        overall = "m"
    elif "+" in parts:
        overall = "b"
    elif "-" in parts:
        overall = "w"
    else:
        overall = "s"
    return overall + "".join(parts)


def company_codes(d: Data) -> list[str]:
    """화면에 올린 회사(사본을 읽을 때 거른 회사, 곧 d 에 종형이 있는 회사)의 기관코드. config.SITE_ORGS 의 차례(우체국이 처음)이고,
    그 밖의 회사(--orgs 로 더한 회사, 가상 사본의 회사)는 사본의 종형 차례로 뒤에 붙는다."""
    present = list(dict.fromkeys(d.variants[v].get("기관코드") for v in d.variant_order))
    head = [HOME_ORG] + [c for c in config.SITE_ORGS if c != HOME_ORG]
    return [c for c in head if c in present] + [c for c in present if c not in head and c is not None]


def pick_lineup(d: Data, codes: list[str]) -> dict[str, list[str | None]]:
    """등급(GRADES)마다 회사(codes 차례)마다 종형 하나. 정밀비교이고 판매 중(판매종료일이 빈 값)이며 간편고지약칭이 그 등급인
    종형이 하나뿐일 때만 고르고, 없거나 둘 이상이면 None 이다. 우체국 종형을 고르지 못하면 멈춘다.
    우체국은 화면 비교에서 빼는 상품(screen.EXCLUDED_PRODUCTS)의 종형을 후보에서 빼고, 후보가 둘 이상이면 화면 기본 상품
    (screen.DEFAULT_PRODUCT)의 종형만 남긴다(예: 하나로OK보험 2종과 간편한건강보험 2606 2종이 모두 3.2.5)."""
    out: dict[str, list[str | None]] = {}
    for grade in GRADES:
        row: list[str | None] = []
        for code in codes:
            found = [v for v in d.variant_order if d.variants[v].get("기관코드") == code
                     and d.variants[v].get("비교역할구분") == C.COMPARE_ROLE
                     and d.variants[v].get("판매종료일") in (None, "") and d.variants[v].get("간편고지약칭") == grade]
            if code == HOME_ORG:
                found = SC.prefer_default_product(d, [v for v in found if not SC.excluded(d, v)])
            row.append(found[0] if len(found) == 1 else None)
        if row[0] is None or codes[0] != HOME_ORG:
            raise ValueError(f"사본에서 {grade} 등급의 우체국 종형을 하나로 고르지 못했다")
        out[grade] = row
    return out


def _insights(cells: dict[str, dict[str, dict]], row: list[str | None], stds: list[str]) -> dict:
    """등급 하나의 시사점. row 는 그 등급의 회사별 종형(맨 앞이 우체국, 고르지 못한 회사는 None 이라 뺀다)."""
    e, *others = [v for v in row if v]
    gap, uniq, diff = [], [], []
    skip = {"gap": 0, "uniq": 0, "diff": 0}
    for sid in stds:
        a, ps = cells[e][sid]["p"], [cells[o][sid]["p"] for o in others]
        if others and all(p == "o" for p in ps) and a in "nw":
            if a == "w":
                skip["gap"] += 1
            else:
                gap.append(sid)
        if others and a == "o" and all(p in "nw" for p in ps):
            if "w" in ps:
                skip["uniq"] += 1
            else:
                uniq.append(sid)
        if others and a == "o" and all(p == "o" for p in ps):
            ts = [terms(cells[o][sid], cells[e][sid]) for o in others]
            if "p" in ts:
                if any(cells[x][sid]["wait"] != cells[e][sid]["wait"] or cells[x][sid]["red"] != cells[e][sid]["red"] for x in others):
                    skip["diff"] += 1
                continue
            if all(t[0] == "s" for t in ts):
                continue
            # 우체국 기준: 경쟁사가 나으면(b) 우체국 불리
            worse = sum(1 for t in ts if t[0] == "b")
            better = sum(1 for t in ts if t[0] == "w")
            mixed = sum(1 for t in ts if t[0] == "m")
            diff.append({"sid": sid, "t": ts, "worse": worse, "better": better, "mixed": mixed,
                         "alt": [1 if cells[o][sid]["alt"] else 0 for o in others]})
    diff.sort(key=lambda x: (-x["worse"], -x["mixed"], -x["better"], stds.index(x["sid"])))
    return {"gap": gap, "uniq": uniq, "diff": diff, "skip": skip}


def export(d: Data) -> dict[str, Any]:
    """`const D` 의 열일곱 열쇠(KEYS)를 만든다. 등급마다 우체국 종형을 고르지 못하거나 COMPARE 의 표준담보가 사본에 없으면 멈춘다.
    lineup[등급][i] 는 orgs[i] 회사의 종형이고, 그 회사에서 고르지 못한 등급은 null 이다."""
    codes = company_codes(d)
    LINEUP = pick_lineup(d, codes)
    vids = [v for vs in LINEUP.values() for v in vs if v]
    stds = [s for s, r in d.std.items() if r.get("사용여부", True)]
    stds.sort(key=lambda s: (GROUPS.index(d.std[s]["보장대분류"]) if d.std[s]["보장대분류"] in GROUPS else 9,
                             TYPES.index(d.std[s]["급부유형"]) if d.std[s]["급부유형"] in TYPES else 9, s))
    lost = [s for s in COMPARE if s not in stds]
    if lost:
        raise ValueError(f"사용하는 표준담보에 COMPARE 담보가 없다: {lost}")

    # ---------- 나이 구간 ----------
    edges = set()
    for r in d.tables["sys_가입조건"]:
        if r["종형ID"] in vids:
            edges.add(int(r["최저가입나이"]))
            edges.add(int(r["최고가입나이"]) + 1)
    cuts = [0] + sorted(e for e in edges if 0 < e <= MAX_AGE) + [MAX_AGE + 1]
    bands = [(lo, nxt - 1) for lo, nxt in zip(cuts, cuts[1:])]

    # ---------- 종형마다 표준담보별 급부(자동확정만) ----------
    views: dict[str, dict[str, list[dict]]] = {}
    waiting: dict[str, set[str]] = {}
    for v in vids:
        confirmed, wait, _ = C.collect(d, v)
        views[v] = {s: [x for x in xs if x["state"] == STATE] for s, xs in confirmed.items()}
        views[v] = {s: xs for s, xs in views[v].items() if xs}
        waiting[v] = set(wait)

    def cell(v: str, s: str, cond: Cond) -> dict:
        xs = views[v].get(s, [])
        core = C.cell_core(d, xs, cond, waiting=s in waiting[v])
        if core["kind"] == "none":
            return {"p": "w" if core.get("waiting") else "n"}
        if core["kind"] == "unavail":
            return {"p": "u"}
        rep = xs[core["rep"]]
        # 대표 규칙은 조건이 엄격한 줄을 고른다. 같은 칸에 가입할 수 있는 급부 가운데 면책이 짧거나 감액이 나은 줄이 있으면 alt로 알린다.
        blocked = set(core.get("no", []))
        alt = any(i != core["rep"] and i not in blocked and
                  (x["wait"] < rep["wait"] or C.compare_reduction(x["red"], rep["red"]) == "+")
                  for i, x in enumerate(xs))
        return {"p": "o", "rep": rep["id"], "val": core["val"], "capPend": bool(core.get("capPend")),
                "pend": d.verdict_pending(rep), "wait": rep["wait"], "red": rep["red"], "alt": alt}

    # ---------- 조건마다 계산 ----------
    conds: dict[str, int] = {}
    payloads: list[str] = []
    pool: set[str] = set(COMPARE)
    raw: dict[str, tuple] = {}
    for grade, lineup in LINEUP.items():
        for bi, (lo, hi) in enumerate(bands):
            for sex in ("M", "F"):
                cond = Cond(age=lo, sex=sex, lo=lo, hi=hi)
                cells = {v: {sid: cell(v, sid, cond) for sid in stds} for v in lineup if v}
                ins = _insights(cells, lineup, stds)
                pool |= set(ins["gap"][:TOP]) | set(ins["uniq"][:TOP]) | {x["sid"] for x in ins["diff"][:TOP]}
                raw[f"{grade}|{bi}|{sex}"] = (grade, cells, ins)

    pool_list = [s for s in stds if s in pool]
    used_bids: dict[tuple[str, str], list[str]] = {}
    for key, (grade, cells, ins) in raw.items():
        e, *others = [v for v in LINEUP[grade] if v]       # 우체국과 그 등급의 상대 종형(고르지 못한 회사는 뺀다)
        pres = {v: "".join(cells[v][sid]["p"] for sid in stds) for v in (e, *others)}
        rep = {}
        for v in (e, *others):
            rep[v] = {}
            for sid in pool_list:
                c = cells[v][sid]
                if c["p"] == "o":
                    rep[v][sid] = [c["rep"], c["val"], 1 if c["capPend"] else 0, 1 if c["alt"] else 0]
                    used_bids.setdefault((v, sid), [])
                    if c["rep"] not in used_bids[(v, sid)]:
                        used_bids[(v, sid)].append(c["rep"])
        verd = {}
        for sid in pool_list:
            verd[sid] = [terms(cells[o][sid], cells[e][sid]) for o in others]
        payload = json.dumps({"pres": pres, "rep": rep, "verd": verd, "ins": ins}, ensure_ascii=False, sort_keys=True)
        if payload not in payloads:
            payloads.append(payload)
        conds[key] = payloads.index(payload)

    # ---------- 칸별 급부 목록과 세부 ----------
    benefits, riders, cellsout = {}, {}, {}
    for v in vids:
        cellsout[v] = {}
        for sid in pool_list:
            xs = views[v].get(sid, [])
            if not xs:
                continue
            reps = used_bids.get((v, sid), [])
            # 대표 다음에는 조건이 나은 급부(면책이 짧고 감액이 없는 줄)를 먼저 싣는다. 서랍에서 "같은 담보의 다른 급부"로 보여 준다.
            rest = [x["id"] for x in sorted(xs, key=lambda x: (x["wait"], len(x["red"]) > 0, x["role"] != "주급부",
                                                              -(x["pay"] or 0) / (x["base"] or 1), x["name"]))
                    if x["id"] not in reps]
            keep = reps + rest[:max(0, SIBLINGS - len(reps))]
            cellsout[v][sid] = {"ids": keep, "n": len(xs)}
            for x in xs:
                if x["id"] not in keep:
                    continue
                benefits[x["id"]] = {
                    "tid": x["tid"], "name": x["name"], "role": x["role"], "base": x["base"], "pay": x["pay"],
                    "ratio": x["ratio"], "wait": x["wait"], "red": x["red"], "limit": x["limit"], "exc": x["exc"],
                    "doc": x["doc"], "page": x["page"], "prob": x["prob"], "state": x["state"], "pend": x["pend"],
                }
                r = d.riders[x["tid"]]
                riders[x["tid"]] = {"name": r["원시특약명"], "kind": r["담보구분"], "max": r.get("최대가입금액만원"),
                                    "renew": r.get("갱신여부"), "cycle": r.get("갱신주기년")}

    variants = {}
    for v in vids:
        r = d.variants[v]
        main = d.main_rider(v)
        rows = d.condition_rows(main) if main else []
        variants[v] = {
            "org": r["기관코드"], "product": r["공시상품명"], "name": r["종형명"], "grade": r["간편고지약칭"],
            "uw": r["심사유형"], "renew": r["갱신유형"], "cycle": r.get("갱신주기년"), "start": r.get("적용시작일"),
            "q": [r.get("고지최근소견개월"), r.get("고지입원수술년수"), r.get("고지중대질병년수")],
            "ages": sorted({(x["최저가입나이"], x["최고가입나이"]) for x in rows}),
            "gap": d.limit_gap(v),
        }

    std_out = {s: {"name": d.std[s]["표준담보명"], "group": d.std[s]["보장대분류"], "mid": d.std[s]["보장중분류"],
                   "type": d.std[s]["급부유형"], "unit": d.std[s].get("비교기준단위만원")} for s in stds}

    # 화면(core.js)은 orgs 의 짧은 이름으로 회사를 부른다. 세 회사 밖의 회사(메리츠화재, 가상 사본의 회사 따위)의 짧은 이름은
    # 기관 이름이다. orgs 의 차례는 lineup 의 자리 차례와 같다(company_codes)
    out = {
        "asOf": d.meta.get("snapshot_at"),
        # 업권은 Data.org_sector 의 값("생명보험", "손해보험"). 업권 자료가 없는 기관(우체국)은 null 이다
        "orgs": [{"code": c, "name": d.org_name(c), "short": SHORT.get(c) or d.org_name(c), "업권": d.org_sector(c)}
                 for c in codes],
        "lineup": LINEUP, "defaultGrade": DEFAULT_GRADE,
        "bands": bands, "stds": stds, "std": std_out, "groups": GROUPS, "types": TYPES,
        "compare": COMPARE, "pool": pool_list,
        "variants": variants, "riders": riders, "benefits": benefits, "cells": cellsout,
        "conds": conds, "payloads": [json.loads(p) for p in payloads],
    }
    # 튜플(bands, ages)을 목록으로 바꿔 JSON 에서 읽은 값과 같은 꼴로 돌려준다
    return json.loads(json.dumps(out, ensure_ascii=False))
