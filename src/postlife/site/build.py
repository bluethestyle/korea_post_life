"""사본 자료를 가공해 파일 하나짜리 HTML을 만든다. 외부 주소를 하나도 부르지 않는다."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import ids
from . import card, combo, commentary, compare, eligibility, overview, pack, revision, worklog
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
        "gap": data.limit_gap(vid),
    }


def rider_view(data: Data, tid: str) -> dict[str, Any]:
    r = data.riders[tid]
    return {
        "id": tid, "vid": r["종형ID"], "name": r["원시특약명"], "kind": r["담보구분"], "main": r["담보구분"] == MAIN_KIND,
        "renew": bool(r.get("갱신여부")), "renewYears": r.get("갱신주기년"),
        "min": r.get("최소가입금액만원"), "max": r.get("최대가입금액만원"),
    }


def payload(data: Data, previous: Data | None = None, texts: dict[str, Any] | None = None) -> dict[str, Any]:
    """화면에 싣는 자료 전부. previous는 지난주 사본(화면 1의 우열 변화), texts는 검사를 마친 해설 글(없으면 기본 파일을 읽는다)."""
    conds = data.conds()
    if texts is None:
        texts = commentary.load()[0]
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
        "commentary": {"texts": texts, "s3Margin": data.setting_num("COMMENT_S3_MARGIN", 0)},
        "card": card.build(data),
        "s1": overview.build(data, previous),
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


def render(data: Data, previous: Data | None = None, texts: dict[str, Any] | None = None) -> str:
    """자료는 pack으로 줄여 적어 넣는다(내용은 그대로이고, 화면이 열릴 때 calc.js의 unpack이 되살린다)."""
    html = (ASSETS / "template.html").read_text(encoding="utf-8")
    parts = {
        "/*__CSS__*/": (ASSETS / "app.css").read_text(encoding="utf-8"),
        "/*__CALC__*/": (ASSETS / "calc.js").read_text(encoding="utf-8"),
        "/*__APP__*/": (ASSETS / "app.js").read_text(encoding="utf-8"),
        "/*__DATA__*/": embed_json(pack.pack(payload(data, previous, texts))),
    }
    for mark, text in parts.items():
        if html.count(mark) != 1:
            raise ValueError(f"틀 파일에 {mark} 자리가 하나가 아닙니다")
        if "</script" in text.lower() or "</style" in text.lower():
            raise ValueError(f"{mark}에 넣을 내용에 닫는 태그가 들어 있습니다")
        html = html.replace(mark, text)
    return html


def read_payload(html: str) -> dict[str, Any]:
    """만든 HTML에서 자료를 꺼내 원래 모양으로 되살린다. 시험과 점검에 쓴다."""
    start = html.index('<script type="application/json" id="data">') + len('<script type="application/json" id="data">')
    return pack.unpack(json.loads(html[start:html.index("</script>", start)]))


def build_site(snapshot_dir: Path, out_path: Path, previous_dir: Path | None = None,
               commentary_path: Path | None = None) -> dict[str, Any]:
    """previous_dir를 주면 지난주 사본과 견줘 화면 1에 대표 조건의 우열 변화를 싣는다. 해설 글에서 버린 글은 warnings에 남긴다."""
    data = load(snapshot_dir)
    previous = None
    if previous_dir is not None:
        if not Path(previous_dir).is_dir():
            raise FileNotFoundError(f"지난주 사본 폴더가 없습니다: {previous_dir}")
        previous = load(previous_dir)
    texts, warnings = commentary.load(commentary_path)
    html = render(data, previous, texts)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return {"out": str(out_path), "bytes": len(html.encode("utf-8")), "variants": len(data.variants),
            "benefits": len(data.benefits), "logs": len(data.logs), "snapshot_at": data.meta.get("snapshot_at"),
            "previous_at": previous.meta.get("snapshot_at") if previous else None, "warnings": warnings}
