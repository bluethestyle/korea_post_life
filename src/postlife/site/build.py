"""사본 자료를 가공해 파일 하나짜리 HTML을 만든다. 외부 주소를 하나도 부르지 않는다."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import ids
from . import combo, compare, eligibility, overview, revision, worklog
from .model import Data, HOME_ORG, MAIN_KIND, MAX_AGE, _blank, load

ASSETS = Path(__file__).parent / "assets"


def variant_view(data: Data, vid: str) -> dict[str, Any]:
    v = data.variants[vid]
    product = ids.strip_dividend(str(v["공시상품명"])).strip()
    kind = str(v["종형명"])
    siblings = sum(1 for o in data.variants.values() if o["개정판ID"] == v["개정판ID"])
    if product.endswith(kind):
        product = product[: -len(kind)].strip()
    elif siblings == 1:
        kind = ""                        # 종이 하나뿐인 상품은 종형명("단일")을 따로 적지 않는다
    return {
        "id": vid, "org": v["기관코드"], "orgName": data.org_name(v["기관코드"]),
        "product": product, "kind": kind, "fullName": v["공시상품명"],
        "role": v.get("비교역할구분"), "rev": v.get("개정판ID"), "code": v.get("공시상품코드"),
        "uw": v.get("심사유형"), "simple": v.get("간편고지약칭"), "gate": eligibility.gate(v),
        "renew": v.get("갱신유형"), "renewYears": v.get("갱신주기년"),
        "refund": v.get("환급유형"), "waiver": v.get("납입면제적용"),
        "start": v.get("적용시작일"), "end": v.get("판매종료일") if not _blank(v.get("판매종료일")) else None,
        "url": v.get("공시목록URL"), "summaryHash": v.get("요약서해시"),
    }


def rider_view(data: Data, tid: str) -> dict[str, Any]:
    r = data.riders[tid]
    return {
        "id": tid, "vid": r["종형ID"], "name": r["원시특약명"], "kind": r["담보구분"], "main": r["담보구분"] == MAIN_KIND,
        "renew": bool(r.get("갱신여부")), "renewYears": r.get("갱신주기년"),
        "min": r.get("최소가입금액만원"), "max": r.get("최대가입금액만원"),
    }


def payload(data: Data) -> dict[str, Any]:
    conds = data.conds()
    age = data.setting_num("REP_WEEKLY_AGE")
    sex = data.setting_text("REP_WEEKLY_SEX_1", "M")
    return {
        "meta": {"snapshotAt": data.meta.get("snapshot_at"), "rowCounts": data.meta.get("row_counts", {})},
        "conds": [None if c.age is None else {"lo": c.lo, "hi": c.hi, "sex": c.sex} for c in conds],
        "defaults": {"age": int(age) if age is not None else None, "sex": sex if sex in ("M", "F") else "M", "maxAge": MAX_AGE},
        "texts": {"gateGeneral": data.setting_text("TEXT_GATE_GENERAL"), "uwNotice": data.setting_text("TEXT_UNDERWRITING_NOTICE"),
                  "composite": data.setting_text("TEXT_COMPOSITE", "복합")},
        "variants": {vid: variant_view(data, vid) for vid in data.variant_order},
        "variantOrder": list(data.variant_order),
        "riders": {tid: rider_view(data, tid) for tid in data.riders},
        "benefits": {bid: data.benefit_view(bid) for bid in data.benefits},
        "std": {sid: {"id": sid, "name": s["표준담보명"], "major": s["보장대분류"], "mid": s["보장중분류"],
                      "type": s["급부유형"], "unit": s["비교기준단위만원"]} for sid, s in data.std.items()},
        "s1": overview.build(data),
        "s2": eligibility.build(data, conds),
        "s3": compare.build(data, conds),
        "s4": combo.build(data, conds),
        "s5": revision.build(data),
        "s6": worklog.build(data),
    }


def embed_json(obj: Any) -> str:
    """<script> 안에 넣어도 안전한 JSON 글자. "<"를 바꿔 "</script>"나 "<!--"가 문서 구조를 깨지 못하게 한다."""
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return text.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def render(data: Data) -> str:
    html = (ASSETS / "template.html").read_text(encoding="utf-8")
    parts = {
        "/*__CSS__*/": (ASSETS / "app.css").read_text(encoding="utf-8"),
        "/*__CALC__*/": (ASSETS / "calc.js").read_text(encoding="utf-8"),
        "/*__APP__*/": (ASSETS / "app.js").read_text(encoding="utf-8"),
        "/*__DATA__*/": embed_json(payload(data)),
    }
    for mark, text in parts.items():
        if html.count(mark) != 1:
            raise ValueError(f"틀 파일에 {mark} 자리가 하나가 아닙니다")
        if "</script" in text.lower() or "</style" in text.lower():
            raise ValueError(f"{mark}에 넣을 내용에 닫는 태그가 들어 있습니다")
        html = html.replace(mark, text)
    return html


def build_site(snapshot_dir: Path, out_path: Path) -> dict[str, Any]:
    data = load(snapshot_dir)
    html = render(data)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return {"out": str(out_path), "bytes": len(html.encode("utf-8")), "variants": len(data.variants),
            "benefits": len(data.benefits), "logs": len(data.logs), "snapshot_at": data.meta.get("snapshot_at")}
