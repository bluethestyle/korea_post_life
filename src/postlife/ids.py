"""다시 추출해도 바뀌지 않는 ID를 만든다.

일련번호를 쓰지 않는다. 같은 문서를 다시 추출하면 같은 ID가 나와야
담당자가 검토한 행(hum_담보매핑)과의 연결이 끊기지 않는다.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

# 상품명·특약명에 붙는 개정 표기. 예: "2504", "(2404.10)", "2608.9"
_REVISION = re.compile(r"\(?(?<!\d)(2\d)(0[1-9]|1[0-2])(?:\.\d+)?(?!\d)\)?")
# 문서마다 다르게 적는 배당 표기. 요약서는 "(무)", 사업방법서는 "무배당"으로 적는 일이 흔하다.
_DIVIDEND = re.compile(r"^\s*(?:\(\s*무배당\s*\)|\(\s*무\s*\)|무배당)\s*")
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    """전각·반각, 공백, 대소문자 차이를 없앤다."""
    text = unicodedata.normalize("NFKC", str(text))
    return _SPACES.sub("", text).lower()


def strip_revision(name: str) -> str:
    """이름에서 개정 연월 표기를 뗀다. 개정 전후의 같은 특약을 잇는 데 쓴다."""
    return _SPACES.sub(" ", _REVISION.sub(" ", str(name))).strip()


def revision_of(name: str) -> str | None:
    """이름에 들어 있는 개정 연월(YYMM)을 꺼낸다. 없으면 None."""
    m = _REVISION.search(str(name))
    return f"{m.group(1)}{m.group(2)}" if m else None


def short_hash(*parts: str, length: int = 10) -> str:
    joined = "|".join(normalize(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:length]


def revision_id(parent_product_id: str, revision: str) -> str:
    """개정판ID. 한 개정판 안의 종마다 공시상품코드가 달라도 하나로 묶인다."""
    return f"{parent_product_id}_{revision}"


def variant_id(org_code: str, disclosure_code: str, variant_name: str) -> str:
    """종형ID."""
    return f"{org_code}_{normalize(disclosure_code).upper()}_{short_hash(variant_name, length=6)}"


def variant_lineage_key(
    parent_product_id: str,
    underwriting: str,
    simple_code: str,
    renewal: str,
    refund: str | None,
) -> str:
    """종형계보키. 개정 전후의 같은 종형을 잇는다."""
    return "|".join(
        [parent_product_id, underwriting, simple_code, renewal, refund or "미지정"]
    )


def strip_dividend(name: str) -> str:
    """이름 앞의 "무배당", "(무)", "(무배당)"을 뗀다."""
    return _DIVIDEND.sub("", str(name))


# 우체국 간편보험은 2504판까지 특약 이름 앞에 가입유형 표시("간편Ⅱ", "간편Ⅲ")를 붙였고 2606판에서 뗐다
_SIMPLE_TYPE = re.compile(r"^간편\s*(?:[ⅠⅡⅢ]|I{1,3})(?=[가-힣])")


def rider_lineage_key(raw_rider_name: str) -> str:
    """특약계보키. 배당 표기, 개정 연월, 이름 앞의 간편 가입유형 표시를 뗀 이름으로 만든다.

    같은 특약을 요약서는 "(무)암진단특약", 사업방법서는 "무배당 암진단특약 2606"으로 적어도
    같은 키가 나와야 보험료와 결합 제약이 한 특약에 붙는다.
    """
    return short_hash(_SIMPLE_TYPE.sub("", strip_revision(strip_dividend(raw_rider_name)).strip()), length=12)


def rider_id(variant: str, raw_rider_name: str) -> str:
    return f"{variant}_T{rider_lineage_key(raw_rider_name)}"


def benefit_id(rider: str, raw_benefit_name: str) -> str:
    return f"{rider}_B{short_hash(raw_benefit_name, length=8)}"


def condition_id(variant: str, term: str, payment: str, rider: str = "", sex: str = "") -> str:
    return f"{variant}_C{short_hash(term, payment, rider, sex, length=8)}"


def premium_id(rider: str, age: int, sex: str, term: str, payment: str, source: str) -> str:
    return f"{rider}_P{short_hash(str(age), sex, term, payment, source, length=8)}"


def constraint_id(variant: str, base_rider: str, target_rider: str, kind: str) -> str:
    return f"{variant}_R{short_hash(base_rider, target_rider, kind, length=8)}"


def disease_map_id(benefit: str, start: str, end: str, included: str) -> str:
    return f"{benefit}_K{short_hash(start, end, included, length=8)}"


def trend_id(org_code: str, category: str, published: str, summary: str) -> str:
    return f"TRD_{org_code}_{short_hash(category, published, summary, length=12)}"
