"""화면에 올릴 회사로 사본을 거른다.

시트(정본)와 사본(data/snapshot)에는 회사가 하나씩 더 들어오지만, 화면은 config.SITE_ORGS 의 회사만 싣는다.
화면 자료를 만드는 길(site/model.py 의 load, scripts/build_site.py, scripts/export_app_data.py, proto_src/graph/build_data.py)은
모두 사본을 읽은 직후 filter_tables 를 거친다.

거르는 것(목록 밖 회사의 행을 뺀다)
- sys_상품종형(기관코드), sys_특약, sys_가입조건, sys_결합제약(종형ID), sys_급부, sys_보험료예시(특약ID),
  sys_급부질병코드, hum_담보매핑(급부ID). 부모 행이 사본에 있으면 부모를 따라 회사를 정하고, 없으면 ID 의 기관코드 접두어
  (ids.py: 모든 행 ID 는 "기관코드_" 로 시작한다)로 정한다.
- sys_작업로그: 대상탭이 위 탭인 줄은 대상행ID 의 회사로 거른다(가리키는 행이 사본에 없어도 접두어로 정한다). 검토 대기 수와
  작업 내역 화면에 목록 밖 회사의 줄이 섞이지 않게 한다. 그 밖의 대상탭(sys_시장동향 따위)의 줄은 그대로 둔다.
거르지 않는 것: 회사와 무관한 탭(hum_표준담보사전, hum_기준값, hum_표준질병군)과 sys_시장동향(지금도 적재하지 않은 회사의
소식을 싣는다).

orgs 값: None 이면 config.SITE_ORGS, "all" 이면 거르지 않음, 쉼표로 이은 글자나 기관코드의 묶음이면 그 회사들.
"""
from __future__ import annotations

import argparse
from typing import Any, Iterable

from .. import config

ALL = "all"
LOG_TAB = "sys_작업로그"
COMPANY_TABS = ("sys_상품종형", "sys_특약", "sys_급부", "sys_급부질병코드", "sys_가입조건", "sys_결합제약",
                "sys_보험료예시", "hum_담보매핑")


def parse(value: str | Iterable[str] | None) -> tuple[str, ...] | str:
    """--orgs 값이나 load 의 orgs 인자를 풀어 기관코드 묶음이나 ALL 로. 빈 목록은 받지 않는다."""
    if value is None:
        return tuple(config.SITE_ORGS)
    if isinstance(value, str):
        if value.strip().lower() == ALL:
            return ALL
        value = value.split(",")
    codes = tuple(dict.fromkeys(str(c).strip().upper() for c in value if str(c).strip()))
    if not codes:
        raise ValueError("화면에 올릴 회사가 비었다(--orgs all 이나 EPOST,HANWHALIFE 처럼 준다)")
    return codes


def is_default(orgs: tuple[str, ...] | str) -> bool:
    """config.SITE_ORGS 와 같은 묶음인지(순서는 보지 않는다). 커밋되는 화면 자료는 기본 묶음으로만 만든다."""
    return orgs != ALL and set(orgs) == set(config.SITE_ORGS)


def describe(orgs: tuple[str, ...] | str) -> str:
    return "사본의 모든 회사" if orgs == ALL else ", ".join(orgs)


def add_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--orgs", default=None,
                        help="화면에 올릴 회사의 기관코드(쉼표로 잇는다. all 은 사본의 모든 회사). "
                             f"주지 않으면 config.SITE_ORGS({','.join(config.SITE_ORGS)})")


def _prefix(row_id: Any) -> str:
    return str(row_id).split("_", 1)[0]


def filter_tables(tables: dict[str, list[dict[str, Any]]], orgs: str | Iterable[str] | None = None) -> dict[str, list[dict[str, Any]]]:
    """목록 밖 회사의 행을 뺀 새 표 묶음. 행 순서는 그대로 둔다. ALL 이면 표 묶음을 그대로(얕은 복사) 돌려준다."""
    orgs = parse(orgs)
    out = {name: list(rows) for name, rows in tables.items()}
    if orgs == ALL:
        return out
    keep = set(orgs)
    t = lambda name: tables.get(name, [])  # noqa: E731
    variant_org = {r["종형ID"]: r.get("기관코드") for r in t("sys_상품종형")}
    rider_parent = {r["특약ID"]: r.get("종형ID") for r in t("sys_특약")}
    benefit_parent = {r["급부ID"]: r.get("특약ID") for r in t("sys_급부")}

    def of_variant(vid: Any) -> str:
        return variant_org.get(vid) or _prefix(vid)

    def of_rider(tid: Any) -> str:
        return of_variant(rider_parent[tid]) if tid in rider_parent else _prefix(tid)

    def of_benefit(bid: Any) -> str:
        return of_rider(benefit_parent[bid]) if bid in benefit_parent else _prefix(bid)

    row_org = {
        "sys_상품종형": lambda r: of_variant(r["종형ID"]),
        "sys_특약": lambda r: of_variant(r["종형ID"]),
        "sys_가입조건": lambda r: of_variant(r["종형ID"]),
        "sys_결합제약": lambda r: of_variant(r["종형ID"]),
        "sys_급부": lambda r: of_rider(r["특약ID"]),
        "sys_보험료예시": lambda r: of_rider(r["특약ID"]),
        "sys_급부질병코드": lambda r: of_benefit(r["급부ID"]),
        "hum_담보매핑": lambda r: of_benefit(r["급부ID"]),
    }
    for name, org in row_org.items():
        if name in out:
            out[name] = [r for r in out[name] if org(r) in keep]

    # 작업 로그가 가리키는 행의 회사. 대상행ID 는 그 탭의 기본키다.
    parent_of = {"sys_가입조건": {r["조건행ID"]: r.get("종형ID") for r in t("sys_가입조건")},
                 "sys_결합제약": {r["제약ID"]: r.get("종형ID") for r in t("sys_결합제약")}}
    premium_parent = {r["보험료행ID"]: r.get("특약ID") for r in t("sys_보험료예시")}
    disease_parent = {r["질병매핑ID"]: r.get("급부ID") for r in t("sys_급부질병코드")}
    target_org = {
        "sys_상품종형": of_variant,
        "sys_특약": of_rider,
        "sys_급부": of_benefit,
        "hum_담보매핑": of_benefit,
        "sys_가입조건": lambda x: of_variant(parent_of["sys_가입조건"][x]) if x in parent_of["sys_가입조건"] else _prefix(x),
        "sys_결합제약": lambda x: of_variant(parent_of["sys_결합제약"][x]) if x in parent_of["sys_결합제약"] else _prefix(x),
        "sys_보험료예시": lambda x: of_rider(premium_parent[x]) if x in premium_parent else _prefix(x),
        "sys_급부질병코드": lambda x: of_benefit(disease_parent[x]) if x in disease_parent else _prefix(x),
    }
    if LOG_TAB in out:
        out[LOG_TAB] = [r for r in out[LOG_TAB]
                        if r.get("대상탭") not in target_org or target_org[r["대상탭"]](r.get("대상행ID")) in keep]
    return out


def filter_meta(meta: dict[str, Any], tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """meta.json 의 row_counts 를 거른 표의 행 수로 고친 사본(화면 1이 행 수를 싣는다). 열쇠와 그 순서는 그대로 둔다."""
    counts = meta.get("row_counts")
    if not isinstance(counts, dict):
        return dict(meta)
    return {**meta, "row_counts": {k: len(tables[k]) if k in tables else v for k, v in counts.items()}}
