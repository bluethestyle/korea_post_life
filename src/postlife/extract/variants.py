"""추출 대상 설정(data/targets)과 공시 수집 결과를 묶어 sys_상품종형 행을 만든다.

심사유형·고지 요건처럼 사람이 문서에서 확인해 적은 값은 설정에서, 상품명·판매 기간·파일 해시는 공시 수집 결과에서 가져온다.
비교역할구분은 종형에 적혀 있으면 그 값을, 없으면 상품의 값을 쓴다. 관문전용 종형은 배치가 급부를 뽑지 않는다(job.run).

종형의 "추출대상특약"(선택)은 요약서 보험금 지급사유 절의 조각 가운데 이 종형에 실을 조각의 머리줄 글자 목록이다.
한 요약서가 보장형마다 다른 주계약과 특약을 담는데 표 안에 가입유형 구분 줄이 없는 문서(우체국더간편건강보험 2504.
주계약 (암보장형)에는 암 특약 둘만, 주계약 (2대질병보장형)에는 2대질병 특약 여섯만 붙는다)에서 쓴다. 적지 않으면 모든 조각을 싣는다.
시트 행에는 들어가지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .. import ids

DOC_HASH = {"상품요약서": "요약서해시", "사업방법서": "사업방법서해시", "약관": "약관별표해시"}
# 종형마다 사업방법서의 고지 질문에서 읽어 설정에 적는 열. 시트의 기존 행은 scripts/sync_variant_attrs.py가 이 열만 맞춘다
OPTIONAL = ("고지최근소견개월", "고지입원수술년수", "고지중대질병년수", "고지수술포함여부", "고지중대질병수",
            "고지중대질병목록", "고지소견범위")
GATE_ROLE = "관문전용"      # 관문 표시에만 쓰는 종형. 급부를 뽑지 않고 종형 행과 주계약 가입나이, 가입한도만 쓴다


@dataclass
class Variant:
    row: dict[str, Any]            # sys_상품종형 한 행
    summary: dict[str, Any] | None  # 공시 수집 목록의 상품요약서 항목 (저장이름·해시·쪽수)
    plain_renewal_years: int | None = None   # 이름에 "(갱신형)"만 있는 특약의 갱신 주기
    method: dict[str, Any] | None = None     # 공시 수집 목록의 사업방법서 항목
    riders: tuple[str, ...] = ()             # 설정의 추출대상특약. 비어 있으면 요약서의 모든 조각을 싣는다

    @property
    def id(self) -> str:
        return self.row["종형ID"]

    @property
    def gate_only(self) -> bool:
        return self.row["비교역할구분"] == GATE_ROLE


def build(targets: dict[str, Any], index: list[dict[str, Any]]) -> tuple[list[Variant], list[str]]:
    """(종형 목록, 문제). 공시 수집 결과에 없는 상품은 종형을 만들지 않고 문제로 남긴다."""
    org = targets["기관코드"]
    docs: dict[str, dict[str, dict[str, Any]]] = {}
    for entry in index:
        if entry.get("기관") == org:
            docs.setdefault(entry["상품코드"], {})[entry["문서"]] = entry
    out: list[Variant] = []
    problems: list[str] = []
    for product in targets["상품"]:
        for v in product["종형"]:
            code = v["공시상품코드"]
            found = docs.get(code)
            if not found:
                problems.append(f"{code} {v['종형명']}: 공시 수집 결과에 없음")
                continue
            any_doc = next(iter(found.values()))
            row = {
                "종형ID": ids.variant_id(org, code, v["종형명"]),
                "개정판ID": ids.revision_id(product["모상품ID"], product["개정연월"]),
                "모상품ID": product["모상품ID"],
                "종형계보키": ids.variant_lineage_key(product["모상품ID"], v["심사유형"], v["간편고지약칭"],
                                                 product["갱신유형"], product.get("환급유형")),
                "기관코드": org,
                "공시상품코드": code,
                "공시상품명": any_doc["상품명"],
                "종형명": v["종형명"],
                "비교역할구분": v.get("비교역할구분") or product["비교역할구분"],
                "심사유형": v["심사유형"],
                "간편고지약칭": v["간편고지약칭"],
                **asked(v),
                "갱신유형": product["갱신유형"],
                "갱신주기년": product.get("갱신주기년"),
                "환급유형": product.get("환급유형"),
                "납입면제적용": product.get("납입면제적용"),
                "적용시작일": any_doc.get("판매시작일"),
                "판매종료일": any_doc.get("판매종료일"),
                "공시목록URL": targets["공시목록URL"],
                **{column: (found.get(kind) or {}).get("해시") for kind, column in DOC_HASH.items()},
            }
            out.append(Variant(row, found.get("상품요약서"), product.get("갱신형특약주기년"), found.get("사업방법서"),
                               tuple(v.get("추출대상특약") or ())))
    return out, problems


def asked(v: dict[str, Any]) -> dict[str, Any]:
    """설정의 종형 하나에 적힌 고지 열(OPTIONAL). 적지 않은 열은 None."""
    return {k: v.get(k) for k in OPTIONAL}


def attributes(targets: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """종형ID → 설정에 적힌 고지 열. 공시 수집 결과 없이 설정만으로 만들고, 종형ID와 값은 build가 만드는 행과 같다."""
    org = targets["기관코드"]
    return {ids.variant_id(org, v["공시상품코드"], v["종형명"]): asked(v)
            for product in targets["상품"] for v in product["종형"]}


MAIN_NAME = "주계약"


def main_row(v: Variant) -> dict[str, Any]:
    """관문전용 종형의 주계약 특약 행. 급부 추출이 만드는 주계약 행(benefits.rider_row)과 같은 꼴이고 가입 한도는 비워 둔다.

    관문 계산(site/model.py의 main_rider, age_limit)이 주계약 행으로 가입나이를 찾으므로, 급부를 뽑지 않는 종형에도 이 행을 쓴다.
    """
    years = v.row["갱신주기년"] if v.row["갱신유형"] == "갱신" else None
    return {
        "특약ID": ids.rider_id(v.id, MAIN_NAME),
        "종형ID": v.id,
        "특약계보키": ids.rider_lineage_key(MAIN_NAME),
        "담보구분": "주계약",
        "원시특약명": MAIN_NAME,
        "갱신여부": years is not None,
        "갱신주기년": years,
        "최소가입금액만원": None,
        "최대가입금액만원": None,
        "합산한도기준키": None,
    }


def by_summary(variants: list[Variant]) -> list[list[Variant]]:
    """같은 상품요약서 파일을 쓰는 종끼리 묶는다. 한 파일은 한 번만 추출한다."""
    groups: dict[str, list[Variant]] = {}
    for v in variants:
        if v.summary and v.summary.get("해시"):
            groups.setdefault(v.summary["해시"], []).append(v)
    return list(groups.values())
