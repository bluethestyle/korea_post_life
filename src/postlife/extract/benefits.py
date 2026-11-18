"""상품요약서의 특약 조각에서 급부를 뽑는다 (기획 6.2의 1단계와 2단계).

모델은 표에 적힌 값만 옮긴다. 감액 지급률처럼 계산으로 나오는 값은 코드가 계산하고,
숫자가 원문에 글자 그대로 있는지도 코드가 먼저 확인한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .. import ids
from .segment import Block

_TEXT = {"type": "STRING"}

# 숫자 칸을 두지 않는다. 금액·기간·보장개시일을 원문 글자로 받고 숫자는 코드가 만든다.
# (숫자 칸으로 받으면 2.5 같은 소수에서 자릿수가 끝없이 이어지거나, 값이 비는 일이 잦았다.)
SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "base_amount": _TEXT,
        "benefits": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": _TEXT, "target": _TEXT, "amount": _TEXT,
                    "reduced_period": _TEXT, "reduced_amount": _TEXT,
                    "reduced2_period": _TEXT, "reduced2_amount": _TEXT,
                    "start_condition": _TEXT, "limit": _TEXT,
                    "role": {"type": "STRING", "enum": ["주급부", "부수급부", "대등복합"]},
                    "quote": _TEXT,
                },
                "required": ["name", "target", "amount", "reduced_period", "reduced_amount", "reduced2_period",
                             "reduced2_amount", "start_condition", "limit", "role", "quote"],
            },
        },
    },
    "required": ["base_amount", "benefits"],
}

PROMPT = """아래는 보험 상품요약서에서 한 특약의 "보험금 지급사유" 부분만 잘라 낸 글입니다. 표가 글자로 풀려 있어 줄이 뒤섞여 있습니다.
이 특약이 지급하는 급부를 한 줄씩 JSON으로 옮깁니다. 표와 주석에 적힌 값만 옮기고, 적히지 않은 값은 만들지 않습니다.

줄을 나누는 기준
- 지급사유(보장 대상)와 금액이 다르면 줄을 나눕니다. 예: 암진단보험금이 암 1,000만원, 갑상선암 등 200만원이면 두 줄. 수술 1종~5종처럼 등급별 금액이 다르면 등급마다 한 줄.
- 경과기간으로는 줄을 나누지 않습니다. "1년미만 500만원 / 1년이상 1,000만원"은 한 줄이고, 1년미만 금액은 그 줄의 감액 칸에 적습니다.

칸 채우는 법
- 금액은 숫자로 바꾸지 말고 원문에 적힌 글자 그대로 옮깁니다. 예: "1,000만원", "2만5천원", "5천원". 계산해서 만든 금액은 적지 않습니다.
- base_amount: 표 위에 적힌 기준 가입금액. 예: "(특약보험가입금액 1,000만원 기준)" → "1,000만원"
- name: 표의 지급구분 이름 그대로. 여러 줄에 갈려 있으면 이어 붙입니다. 예: "암진단" + "보험금" → 암진단보험금
- target: 그 줄이 보장하는 대상을 원문 낱말로 짧게. 예: "암", "갑상선암·기타피부암·대장점막내암·제자리암·경계성종양", "관혈수술", "1종". 나눌 것이 없으면 빈 문자열.
  같은 name의 줄끼리는 target이 서로 달라야 합니다. 구분이 둘이면 함께 적습니다. 예: "암·관혈수술".
  한 지급사유에 "암보장개시일 이후에 암으로 …하였거나, 보험기간 중 갑상선암…으로 …하였을 때"처럼 조건이 다른 두 경우가 함께 적혀 있으면
  경우마다 줄을 나누고 금액은 같게 적습니다. 예: "암·관혈수술" 300만원, "갑상선암·기타피부암·대장점막내암·제자리암·경계성종양·관혈수술" 300만원.
- amount: 감액이 끝난 뒤의 지급액. "1년미만 500만원 / 1년이상 1,000만원"이면 "1,000만원". 1일당·1회당·매월·매년 금액은 그 단위 금액.
  "1,000만원 × 해당 장해지급률"처럼 비율을 곱하는 금액은 곱하기 앞의 금액만 적고, 곱하는 내용은 limit에 적습니다.
- reduced_period, reduced_amount: 계약일부터 일정 기간 안에는 덜 지급하는 경우, 그 기간과 금액을 원문 글자로 함께 적습니다.
  "1년미만 500만원"이면 "1년미만"과 "500만원", "1년미만 2만5천원"이면 "1년미만"과 "2만5천원", "2년미만 25만원"이면 "2년미만"과 "25만원".
  감액이 없으면 둘 다 빈 문자열. 한쪽만 채우지 않습니다. reduced_amount는 언제나 amount보다 작은 금액입니다.
  금액이 "1년미만"과 "1년이상" 두 칸으로 적혀 있어도 줄은 하나입니다. 1년이상 금액이 amount, 1년미만 금액이 reduced_amount입니다.
- reduced2_period, reduced2_amount: 감액 구간이 둘일 때 두 번째 구간. 없으면 둘 다 빈 문자열.
- start_condition: 지급사유 문장이 "암보장개시일 이후에", "치매보장개시일 이후에"처럼 보장개시일 뒤를 조건으로 삼는 줄에만
  그 보장개시일 이름을 적습니다. 예: "암보장개시일". 지급사유가 "보험기간 중"으로 시작하는 경우는 빈 문자열.
- limit: 지급사유 문장에 붙은 지급 횟수·한도 조건(대개 괄호 안)을 원문 그대로 빠짐없이 옮깁니다. 줄여 쓰지 않습니다.
  예: "1일 이상 입원일수 1일당, 120일 한도", "4일 이상 입원일수 1일당, 120일한도", "수술 1회당",
  "암, 갑상선암, 기타피부암 또는 대장점막내암 중 최초 1회에 한함". 맨 앞의 "단,"은 뺍니다. 없으면 빈 문자열.
- role: 특약 이름이 가리키는 대표 보장은 "주급부". 같은 특약 안에서 금액이 훨씬 작은 유사 보장(갑상선암·제자리암 등)은 "부수급부".
  성격이 다른 보장이 나란히 묶인 특약(예: 입원과 수술)은 모든 줄을 "대등복합".
- quote: 그 줄의 금액이 적힌 원문 조각을 20자 안팎으로 그대로.
- 보험금을 지급하는 내용이 없으면 benefits를 빈 배열로 둡니다.

보기 1
원문: "암보장개시일 이후에 최초의 암으로 진단이 확정되었을 때 (단, 최초 1회에 한함) 1년미만 500만원 1년이상 1,000만원 / 보험기간 중 최초의 갑상선암, 기타피부암으로 진단이 확정되었을 때 (각각 최초 1회에 한함) 1년미만 100만원 1년이상 200만원 / 주) 암보장개시일은 계약일부터 그 날을 포함하여 90일이 지난날의 다음날"
결과: 두 줄.
 1) name 암진단보험금, target 암, amount "1,000만원", reduced_period "1년미만", reduced_amount "500만원", start_condition "암보장개시일", limit "최초 1회에 한함", role 주급부
 2) name 암진단보험금, target 갑상선암·기타피부암, amount "200만원", reduced_period "1년미만", reduced_amount "100만원", start_condition "", limit "각각 최초 1회에 한함", role 부수급부

보기 2
원문: "보험기간 중 질병으로 입원하였을 때 (1일이상 입원일수 1일당, 120일 한도) 보험계약일부터 1년미만 1만5천원 보험계약일부터 1년이상 3만원"
결과: 한 줄. name 질병입원보험금, target 질병, amount "3만원", reduced_period "1년미만", reduced_amount "1만5천원", start_condition "", limit "1일이상 입원일수 1일당, 120일 한도", role 주급부

특약 이름: {title}

본문
{text}"""


@dataclass
class Benefit:
    name: str
    target: str
    amount: float
    waiting_days: int
    limit: str
    role: str
    quote: str
    reduced_months: int | None = None
    reduced_amount: float | None = None
    reduced2_months: int | None = None
    reduced2_amount: float | None = None
    amount_text: str = ""            # 원문에 적힌 글자. 코드 대조에 쓴다
    reduced_text: str = ""
    reduced2_text: str = ""
    period_text: str = ""            # 감액 기간을 적은 글자. 예: "1년미만"
    period2_text: str = ""

    @property
    def label(self) -> str:
        """원시급부명. 한 지급구분을 나눈 줄은 대상을 괄호로 붙여 구분한다."""
        return f"{self.name}({self.target})" if self.target else self.name

    def rate(self, reduced: float | None) -> float | None:
        if reduced is None or not self.amount:
            return None
        return round(reduced / self.amount, 4)


@dataclass
class Extraction:
    block: Block
    base_amount: float
    benefits: list[Benefit]
    model: str
    problems: list[str] = field(default_factory=list)


_MONEY = re.compile(r"(?:(\d+)억)?(?:(\d+)천만|(\d+)만)?(?:(\d+)천)?원")


def parse_money(text: Any) -> float | None:
    """"1,000만원", "2만5천원", "5천원", "1억5천만원" 같은 글자를 만 원 단위 숫자로. 읽을 수 없으면 None."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    for m in _MONEY.finditer(squash(str(text))):
        eok, cheonman, man, cheon = (int(g) if g else 0 for g in m.groups())
        value = eok * 10000 + cheonman * 1000 + man + cheon / 10
        if value:
            return value
    return None


def money_token(text: str) -> str:
    """금액 글자에서 돈을 적은 부분만. "2,000만 원 + 플러스적립금" → "2000만원"."""
    for m in _MONEY.finditer(squash(text or "")):
        if any(m.groups()):
            return m.group(0)
    return ""


_PERIOD = re.compile(r"(\d+)(년|개월|일)")


def parse_months(text: Any) -> int | None:
    """"1년미만", "2년 미만", "6개월미만" 같은 글자를 개월 수로."""
    if text is None or text == "":
        return None
    if isinstance(text, (int, float)):
        return int(text) or None
    m = _PERIOD.search(squash(str(text)))
    if not m:
        return None
    n = int(m.group(1))
    return n * 12 if m.group(2) == "년" else n if m.group(2) == "개월" else max(1, round(n / 30))


def period_token(text: str) -> str:
    """기간 글자에서 기간만. "보험계약일부터 1년 미만" → "1년미만". 표에서는 앞말과 기간 사이에 금액이 끼어 있기도 하다."""
    flat = squash(text or "")
    m = re.search(r"\d+(?:년|개월|일)(?:미만|이내|이하)?", flat)
    return m.group(0) if m else flat


def _text(value: Any) -> str:
    return "" if value is None or isinstance(value, (int, float)) else str(value).strip()


def waiting_days_of(item: dict[str, Any], definitions: dict[str, int]) -> tuple[int, str]:
    """(면책 날수, 문제). 모델이 적은 보장개시일 이름을 주석의 정의 문장에서 찾아 날수로 바꾼다."""
    name = squash(_text(item.get("start_condition")))
    if not name:
        return 0, ""
    for known, days in definitions.items():
        if known and (known in name or name in known):
            return days, ""
    if len(set(definitions.values())) == 1:      # 정의가 하나뿐이면 이름이 조금 달라도 그 날수로 본다
        return next(iter(definitions.values())), ""
    return 0, f"보장개시일 '{name}'의 날수를 주석에서 찾지 못함"


def parse(block: Block, raw: dict[str, Any], model: str) -> Extraction:
    benefits, problems = [], []
    definitions = waiting_definitions(block.text)
    for item in raw.get("benefits") or []:
        try:
            amount = parse_money(item["amount"])
            waiting, trouble = waiting_days_of(item, definitions)
            b = Benefit(
                name=str(item["name"]).strip(), target=str(item.get("target") or "").strip(),
                amount=amount or 0.0, waiting_days=waiting,
                limit=str(item.get("limit") or "").strip(), role=str(item.get("role") or "주급부"),
                quote=str(item.get("quote") or "").strip(),
                reduced_months=parse_months(item.get("reduced_period")),
                reduced_amount=parse_money(item.get("reduced_amount") or None),
                reduced2_months=parse_months(item.get("reduced2_period")),
                reduced2_amount=parse_money(item.get("reduced2_amount") or None),
                amount_text=_text(item["amount"]), reduced_text=_text(item.get("reduced_amount")),
                reduced2_text=_text(item.get("reduced2_amount")),
                period_text=_text(item.get("reduced_period")), period2_text=_text(item.get("reduced2_period")),
            )
            if trouble:
                problems.append(f"{trouble}: {b.label}")
            # "1,000만원 × 해당 장해지급률"처럼 비율을 곱하는 금액은 그 사실이 시트에 남도록 한도 칸에 적는다
            for text in (b.amount_text, b.quote):
                if "×" in text:
                    tail = " ".join(text.split("×", 1)[1].split())
                    if tail and squash(tail) not in squash(b.limit):
                        b.limit = f"× {tail}" + (f", {b.limit}" if b.limit else "")
                    break
        except (KeyError, TypeError, ValueError) as e:
            problems.append(f"형식 오류: {e}")
            continue
        if not b.name or b.amount <= 0:
            problems.append(f"이름이나 금액이 비어 있음: {item}")
            continue
        # 값끼리 앞뒤가 안 맞으면 다른 모델로 다시 뽑게 한다
        if (b.reduced_months is None) != (b.reduced_amount is None):
            problems.append(f"감액 기간과 감액 금액 중 하나만 적힘: {b.label}")
        if (b.reduced2_months is None) != (b.reduced2_amount is None):
            problems.append(f"둘째 감액 기간과 금액 중 하나만 적힘: {b.label}")
        if b.reduced_amount is not None and b.reduced_amount >= b.amount:
            problems.append(f"감액 금액이 지급액보다 작지 않음: {b.label}")
        benefits.append(b)
    labels = [b.label for b in benefits]
    for dup in sorted({l for l in labels if labels.count(l) > 1}):
        problems.append(f"같은 이름의 급부가 두 번 나옴: {dup}")
    base = block.base_amount or parse_money(raw.get("base_amount")) or 0.0
    return Extraction(block, base, benefits, model, problems)


def extract(gemini: Any, block: Block, model: str, feedback: list[str] | None = None) -> Extraction:
    """feedback: 앞선 추출에서 드러난 문제. 다시 뽑을 때 지시문 끝에 붙여 같은 실수를 피하게 한다."""
    prompt = PROMPT.format(title=block.title, text=block.text)
    if feedback:
        prompt += "\n\n앞선 추출에서 드러난 문제 (같은 실수를 되풀이하지 않습니다)\n" + "\n".join(f"- {f}" for f in feedback[:8])
    raw = gemini.generate(model, prompt, schema=SCHEMA)
    return parse(block, raw if isinstance(raw, dict) else {}, model)


# ---------- 코드 대조: 숫자가 원문에 글자 그대로 있는가 ----------

def amount_forms(manwon: float) -> list[str]:
    """만 원 단위 금액이 문서에 적힐 수 있는 꼴. 공백과 쉼표는 비교할 때 뗀다."""
    forms = []
    if float(manwon).is_integer():
        n = int(manwon)
        forms += [f"{n}만원", f"{n:,}만원".replace(",", "")]
        if n >= 10000 and n % 10000 == 0:
            forms.append(f"{n // 10000}억원")
        if n % 1000 == 0 and n < 10000:
            forms.append(f"{n // 1000}천만원")
    else:
        whole, frac = divmod(round(manwon * 10), 10)
        if frac:
            forms.append(f"{whole}만{frac}천원" if whole else f"{frac}천원")
        forms.append(f"{manwon}만원")
    return forms


def squash(text: str) -> str:
    return re.sub(r"[\s,]", "", text)


_START_NAME = re.compile(r"([가-힣]{0,12}보장개시일)[은는]")
_START_SPAN = re.compile(r"(\d+)(일|년|개월)이지난")


def waiting_definitions(text: str) -> dict[str, int]:
    """주석의 "○○보장개시일은 계약일부터 그 날을 포함하여 90일이 지난날의 다음날" 문장에서 이름과 날수를 읽는다.

    문장 사이에 쪽 번호나 "[부활(효력회복)일]" 같은 글자가 끼어 있어도 읽도록, 이름 뒤 60자 안에서 "N일이 지난"을 찾는다.
    """
    flat = squash(text)
    out: dict[str, int] = {}
    for m in _START_NAME.finditer(flat):
        span = _START_SPAN.search(flat[m.end():m.end() + 60])
        if span and "계약일" in flat[m.end():m.end() + span.start()]:
            n = int(span.group(1))
            name = m.group(1).split("경우")[-1]
            out.setdefault(name, n if span.group(2) == "일" else n * 365 if span.group(2) == "년" else n * 30)
    return out


_NOISE = re.compile(r"보험계약일부터|\d+억\d*천?만?원|\d+천만원|\d+만\d*천?원|\d+천원|\d+(?:년|개월)(?:미만|이상)")


def limit_is_partial(limit: str, squashed_source: str) -> bool:
    """한도 글자가 원문 괄호 안 조건의 일부만 옮긴 것인가.

    "(단, 암, 갑상선암 … 중 최초 1회에 한함)"에서 "최초 1회에 한함"만 옮기면 뜻이 달라진다.
    표가 글자로 풀리면서 괄호 안에 끼어든 다른 칸의 글자(보험계약일부터, 금액, 1년미만 등)는 빼고 견준다.
    """
    flat = squash(limit)
    at = squashed_source.find(flat)
    if at < 0:
        return False
    left = squashed_source.rfind("(", 0, at)
    right = squashed_source.find(")", at + len(flat))
    if left < 0 or right < 0 or squashed_source.rfind(")", 0, at) > left:
        return False                      # 괄호 안에 있지 않다
    inner = _NOISE.sub("", squashed_source[left + 1:right])
    inner = inner[1:] if inner.startswith("단") else inner
    return len(inner) - len(_NOISE.sub("", flat)) >= 3


def literal_problems(ex: Extraction) -> dict[str, list[str]]:
    """급부별로, 원문에서 글자 그대로 확인되지 않은 항목. 여기 걸린 항목은 판정 모델이 다시 본다.

    급부 이름은 보지 않는다. 표에서는 이름이 "암진단 / 보험금"처럼 줄이 갈려 다른 칸의 글자와 섞이므로
    글자 비교로는 가릴 수 없다. 이름이 실제로 있는지는 판정 모델이 본다.
    """
    source = squash(ex.block.text)
    out: dict[str, list[str]] = {}
    for b in ex.benefits:
        missing = []
        for label, value, text in (("기준지급금액만원", b.amount, b.amount_text), ("감액지급률1", b.reduced_amount, b.reduced_text),
                                   ("감액지급률2", b.reduced2_amount, b.reduced2_text)):
            if value is None:
                continue
            forms = [money_token(text)] if money_token(text) else amount_forms(value)   # 금액 뒤에 붙은 설명은 줄이 갈려 비교하지 않는다
            if not any(f and f in source for f in forms):
                missing.append(label)
        for label, months, text in (("감액개월1", b.reduced_months, b.period_text), ("감액개월2", b.reduced2_months, b.period2_text)):
            if months is not None and text and period_token(text) not in source:   # "2년미만"이라 적었는데 원문에 그 글자가 없다
                missing.append(label)
        if b.waiting_days and b.waiting_days not in waiting_definitions(ex.block.text).values():
            missing.append("면책기간일수")
        if b.limit and squash(b.limit) not in source:
            missing.append("지급횟수제한")
        elif b.limit and limit_is_partial(b.limit, source):
            missing.append("지급한도일부")
        if missing:
            out[b.label] = missing
    return out


# ---------- 시트 행으로 바꾸기 ----------

_RENEWAL = re.compile(r"\((\d+)년갱신형\)|\(갱신형\)")


def rider_row(variant_id: str, block: Block, product_renewal_years: int | None,
              plain_renewal_years: int | None = None) -> dict[str, Any]:
    """plain_renewal_years: 이름에 "(갱신형)"만 있고 주기가 없는 특약의 갱신 주기. 사업방법서에서 확인해 설정에 적은 값."""
    name = block.rider_name
    m = _RENEWAL.search(name)
    if block.is_main:
        renewal, years = product_renewal_years is not None, product_renewal_years
    else:
        renewal, years = bool(m), (int(m.group(1)) if m.group(1) else plain_renewal_years) if m else None
    return {
        "특약ID": ids.rider_id(variant_id, name),
        "종형ID": variant_id,
        "특약계보키": ids.rider_lineage_key(name),
        "담보구분": "주계약" if block.is_main else "선택특약",
        "원시특약명": name,
        "갱신여부": renewal,
        "갱신주기년": years,
        "최소가입금액만원": None,
        "최대가입금액만원": None,
        "합산한도기준키": None,
    }


def benefit_rows(variant_id: str, ex: Extraction, doc_kind: str = "요약서",
                 skip: set[str] | None = None) -> list[dict[str, Any]]:
    """skip: 시트에 쓰지 않을 급부 이름 (다시 뽑아도 원문과 맞지 않아 보인 줄)."""
    rider = ids.rider_id(variant_id, ex.block.rider_name)
    rows = []
    for b in ex.benefits:
        if skip and b.label in skip:
            continue
        rows.append({
            "급부ID": ids.benefit_id(rider, b.label),
            "특약ID": rider,
            "원시급부명": b.label,
            "급부역할": b.role,
            "기준가입금액만원": ex.base_amount,
            "기준지급금액만원": b.amount,
            "지급횟수제한": b.limit or None,
            "면책기간일수": b.waiting_days,
            "감액개월1": b.reduced_months if b.reduced_amount is not None else None,
            "감액지급률1": b.rate(b.reduced_amount) if b.reduced_months is not None else None,
            "감액개월2": b.reduced2_months if b.reduced2_amount is not None else None,
            "감액지급률2": b.rate(b.reduced2_amount) if b.reduced2_months is not None else None,
            "근거문서종류": doc_kind,
            "근거문서쪽수": ex.block.first_page,
        })
    return rows
