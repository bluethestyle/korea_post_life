"""상품요약서의 특약 조각에서 급부를 뽑는다 (기획 6.2의 1단계와 2단계).

모델은 표에 적힌 값만 옮긴다. 감액 지급률처럼 계산으로 나오는 값은 코드가 계산하고,
숫자가 원문에 글자 그대로 있는지도 코드가 먼저 확인한다.
"""
from __future__ import annotations

import bisect
import re
from collections import Counter
from dataclasses import dataclass, field, replace
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
                    "reduced2_period": _TEXT, "reduced2_amount": _TEXT, "reduction_exception": _TEXT,
                    "start_condition": _TEXT, "limit": _TEXT,
                    "role": {"type": "STRING", "enum": ["주급부", "부수급부", "대등복합"]},
                    "quote": _TEXT,
                },
                "required": ["name", "target", "amount", "reduced_period", "reduced_amount", "reduced2_period",
                             "reduced2_amount", "reduction_exception", "start_condition", "limit", "role", "quote"],
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
  특약 안에 "□ 보장형 계약", "□ 연장형 계약"처럼 계약 구분마다 표가 따로 있으면 표마다 줄을 나누고, target 앞에 그 구분을 적습니다.
  예: "보장형 계약·암", "연장형 계약·암".
- amount: 감액이 끝난 뒤의 지급액. "1년미만 500만원 / 1년이상 1,000만원"이면 "1,000만원". 1일당·1회당·매월·매년 금액은 그 단위 금액.
  "1,000만원 × 해당 장해지급률"처럼 비율을 곱하는 금액은 곱하기 앞의 금액만 적고, 곱하는 내용은 limit에 적습니다.
- reduced_period, reduced_amount: 계약일부터 일정 기간 안에는 덜 지급하는 경우, 그 기간과 금액을 원문 글자로 함께 적습니다.
  "1년미만 500만원"이면 "1년미만"과 "500만원", "1년미만 2만5천원"이면 "1년미만"과 "2만5천원", "2년미만 25만원"이면 "2년미만"과 "25만원".
  감액이 없으면 둘 다 빈 문자열. 한쪽만 채우지 않습니다. reduced_amount는 언제나 amount보다 작은 금액입니다.
  금액이 "1년미만"과 "1년이상" 두 칸으로 적혀 있어도 줄은 하나입니다. 1년이상 금액이 amount, 1년미만 금액이 reduced_amount입니다.
- reduced2_period, reduced2_amount: 감액 구간이 둘일 때 두 번째 구간. 없으면 둘 다 빈 문자열.
  "1년미만 500만원 ※ 단, 계약일부터 180일이내 …시 250만원"처럼 더 짧은 기간의 금액이 따로 적혀 있으면 감액 구간이 둘입니다.
  짧은 기간을 reduced에("180일이내", "250만원"), 긴 기간을 reduced2에("1년미만", "500만원") 적습니다.
- reduction_exception: 감액이 있는 줄에 "이런 경우에는 감액하지 않는다"는 예외가 적혀 있으면 그 문구를 원문 글자 그대로 옮깁니다.
  지급금액 칸에 붙은 "※ 단, 재해로 인한 수술시 100만원"이면 "재해로 인한 수술시 100만원"("※ 단,"은 뺍니다).
  주석에 "재해를 직접적인 원인으로 …한 경우에는 경과기간 1년 미만의 보험금 감액은 적용하지 않습니다"처럼 적혀 있으면
  그 주석이 가리키는 줄에 그 문장을 옮깁니다. 예외가 있어도 줄은 나누지 않습니다. 감액이 없거나 예외가 없으면 빈 문자열.
- start_condition: 지급사유 문장이 "암보장개시일 이후에", "치매보장개시일 이후에"처럼 보장개시일 뒤를 조건으로 삼는 줄에만
  그 보장개시일 이름을 적습니다. 예: "암보장개시일". 지급사유가 "보험기간 중"으로 시작하는 경우는 빈 문자열.
  이름 없이 "보장개시일 이후"라고만 적힌 줄은 빈 문자열입니다(그 보장개시일은 계약일입니다).
  "보장개시일(암은 암보장개시일) 이후에 암, 기타피부암 또는 갑상선암으로 …"처럼 한 문장에 묶여 있으면
  암 줄(start_condition "암보장개시일")과 그 밖의 줄(빈 문자열)로 나눕니다.
- limit: 지급사유 문장에 붙은 지급 횟수·한도 조건(대개 괄호 안)을 원문 그대로 빠짐없이 옮깁니다. 줄여 쓰지 않습니다.
  예: "1일 이상 입원일수 1일당, 120일 한도", "4일 이상 입원일수 1일당, 120일한도", "수술 1회당",
  "암, 갑상선암, 기타피부암 또는 대장점막내암 중 최초 1회에 한함". 맨 앞의 "단,"은 뺍니다. 없으면 빈 문자열.
  지급사유에 조건이 없고 주석에만 한도가 적혀 있으면 주석의 그 문장을 글자 그대로 옮깁니다. 위 보기의 말투로 바꿔 쓰지 않습니다.
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

보기 3
원문: "보험기간 중 피보험자가 질병 또는 재해의 치료를 직접적인 목적으로 수술을 받았을 경우 (수술 1회당) 경과기간 1년미만 50만원 ※ 단, 재해로 인한 수술시 100만원 1년이상 100만원"
결과: 한 줄. name 수술자금, target "", amount "100만원", reduced_period "1년미만", reduced_amount "50만원", reduction_exception "재해로 인한 수술시 100만원", start_condition "", limit "수술 1회당", role 주급부
(질병과 재해로 줄을 나누지 않습니다.)

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
    exception: str = ""              # 감액하지 않는 예외 문구. 감액이 없는 줄에는 비운다
    split_from: str = ""             # 코드가 대상별로 나눈 줄이면 나누기 전의 원시급부명. 이 줄의 면책은 코드가 원문 문구로 정했다

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


_NUM = r"\d+(?:\.\d+)?"
# 억·천만·백만·만·천·백과 그 뒤의 낱돈("2만5,000원")까지 한 덩어리로 읽는다. 숫자 가운데("1.5억원"의 "5억원")에서는 시작하지 않는다
_AMOUNT = re.compile(
    rf"(?<!\d)(?<!\d\.)(?:({_NUM})억)?(?:(?:({_NUM})천)?(?:(\d+)백)?({_NUM})?만)?(?:({_NUM})천)?(?:(\d+)백)?(\d+)?원")
_WON = re.compile(r"(?<![\d억만천])(\d+)원")      # "5,000원"처럼 단위 없이 원으로만 적힌 금액


def _amounts(flat: str):
    """(찾은 자리, 만 원 단위 값). 단위 글자 없이 숫자와 "원"만 있는 자리는 건너뛴다(그런 금액은 _WON으로 맨 나중에 본다)."""
    for m in _AMOUNT.finditer(flat):
        if not any(m.groups()[:6]):
            continue
        eok, cheonman, baekman, man, cheon, baek, won = (float(g) if g else 0 for g in m.groups())
        value = eok * 10000 + cheonman * 1000 + baekman * 100 + man + cheon / 10 + baek / 100 + won / 10000
        yield m, round(value, 6) if "." in m.group(0) else value      # 1.1억 = 11000.000000000002 같은 꼬리를 뗀다


def parse_money(text: Any) -> float | None:
    """"1,000만원", "2만5천원", "5천원", "1억5천만원", "2.5만원", "1.2억원", "5백만원", "2만5,000원", "5,000원" 같은 글자를 만 원 단위 숫자로.

    읽을 수 없으면 None.
    """
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    for _, value in _amounts(squash(str(text))):
        if value:
            return float(value)
    m = _WON.search(squash(str(text)))
    if m and int(m.group(1)):
        return int(m.group(1)) / 10000
    return None


def money_token(text: str) -> str:
    """금액 글자에서 돈을 적은 부분만. "2,000만 원 + 플러스적립금" → "2000만원"."""
    for m, _ in _amounts(squash(text or "")):
        return m.group(0)
    m = _WON.search(squash(text or ""))
    return m.group(0) if m else ""


_PERIOD = re.compile(r"(?:(\d+)년(?:(\d+)개월)?|(\d+)개월|(\d+)일)(미만|이내|이하)?")


def _period(flat: str) -> re.Match | None:
    """감액 구간의 끝을 적은 기간. "1년이상 2년미만"은 "2년미만", "180일초과 1년미만"은 "1년미만".

    끝을 나타내는 말(미만·이내·이하)이 붙은 기간이 없으면 처음 나온 기간을 쓴다.
    """
    found = list(_PERIOD.finditer(flat))
    return next((m for m in found if m.group(5)), found[0] if found else None)


def parse_months(text: Any) -> int | None:
    """"1년미만", "2년 미만", "6개월미만", "1년6개월미만" 같은 글자를 개월 수로."""
    if text is None or text == "":
        return None
    if isinstance(text, (int, float)):
        return int(text) or None
    m = _period(squash(str(text)))
    if not m:
        return None
    years, extra, months, days = m.group(1, 2, 3, 4)
    if years is not None:
        return int(years) * 12 + int(extra or 0)
    return int(months) if months is not None else max(1, round(int(days) / 30))


def period_token(text: str) -> str:
    """기간 글자에서 기간만. "보험계약일부터 1년 미만" → "1년미만". 표에서는 앞말과 기간 사이에 금액이 끼어 있기도 하다."""
    flat = squash(text or "")
    m = _period(flat)
    return m.group(0) if m else flat


_UNIT = re.compile(r"((?:입원|통원|수술|사용)?1(?:일|회)당)$")
_TIMES = re.compile(r"^×((?:해당)?[가-힣]{0,6}지급률)")


def _with_cell_notes(limit: str, amount_text: str, flat_source: str) -> str:
    """지급금액 칸에 금액과 함께 적힌 단위("입원 1일당 2만원")와 곱하는 비율("1,000만원 × 해당 장해지급률")을 한도 칸에 남긴다.

    모델이 금액만 옮기고 이 말을 빠뜨리면 "하루에 2만원"인지 "한 번에 2만원"인지, 정액인지 비율인지가 시트에서 사라진다.
    원문에서 그 금액 글자 바로 앞·뒤에 붙어 있을 때만 옮긴다. 같은 금액이 여러 번 나오면 모든 자리에서 같아야 한다.
    """
    token = money_token(amount_text)
    if not token:
        return limit
    spots = [m.start() for m in re.finditer(re.escape(token), flat_source)]
    if not spots:
        return limit
    have = squash(limit)
    units = {(_UNIT.search(flat_source[max(0, at - 6):at]) or [None, None])[1] for at in spots}
    if len(units) == 1 and None not in units:
        unit = units.pop()
        if unit not in have and unit[-3:] not in have:
            spaced = unit.replace("1", " 1").strip() if unit[0] != "1" else unit
            limit = f"{spaced}, {limit}" if limit else spaced
    times = {(_TIMES.match(flat_source[at + len(token):at + len(token) + 14]) or [None, None])[1] for at in spots}
    if len(times) == 1 and None not in times and "×" not in limit:
        tail = times.pop().replace("해당", "해당 ")
        limit = f"× {tail}" + (f", {limit}" if limit else "")
    return limit


def _spaced(token: str) -> str:
    """빈칸·쉼표를 뗀 글자(token)를 원문에서 찾는 정규식. 글자 사이의 빈칸·쉼표는 무시한다.

    숫자로 시작하면 더 큰 숫자의 뒷부분("1,500만원"·"2.5만원" 안의 "500만원"·"5만원")에서는 찾지 않는다.
    """
    head = r"(?<!\d)(?<!\d[.,])" if token[:1].isdigit() else ""
    return head + r"[\s,]*".join(map(re.escape, token))


def _multiplier(amount_text: str, quote: str) -> str:
    """금액에 곱하는 말. "1,000만원 × 해당 장해지급률" → "해당 장해지급률". 없으면 빈 글자.

    quote에는 옆줄의 글자가 섞여 들기도 하므로, 이 줄의 금액 바로 뒤에 "×"가 붙어 있을 때만 본다.
    """
    if "×" in amount_text:
        return " ".join(amount_text.split("×", 1)[1].split())
    token = money_token(amount_text)
    m = re.search(_spaced(token) + r"\s*×", quote) if token else None
    return " ".join(quote[m.end():].split()) if m else ""


def _exception(value: Any) -> str:
    """감액 예외 문구. 앞의 "※", "단,"과 줄바꿈을 정리한다."""
    text = " ".join(str(value or "").split())
    return re.sub(r"^(?:※\s*)?(?:단\s*,\s*)?", "", text).strip()


def _text(value: Any) -> str:
    return "" if value is None or isinstance(value, (int, float)) else str(value).strip()


def _same_tail(a: str, b: str) -> int:
    """두 글자의 끝에서부터 같은 글자 수."""
    n = 0
    while n < min(len(a), len(b)) and a[-1 - n] == b[-1 - n]:
        n += 1
    return n


def waiting_days_of(item: dict[str, Any], definitions: dict[str, int], flat_source: str = "") -> tuple[int, str]:
    """(면책 날수, 문제). 모델이 적은 보장개시일 이름을 주석의 정의 문장에서 찾아 날수로 바꾼다.

    flat_source: 빈칸을 뗀 조각 글. 주면, 정의와 맞지 않는 이름이 원문에 따로 적혀 있는지 본다.
    """
    name = re.sub(r"[’‘'\"“”]", "", squash(_text(item.get("start_condition"))))
    if not name or name == "보장개시일":      # 이름 없는 "보장개시일"은 계약일부터 보장한다. "암보장개시일"의 일부로 보지 않는다
        return 0, ""
    related = [known for known in definitions if known and (known in name or name in known)]
    if related:
        # 정의가 여럿이면 이름이 가장 가깝게 맞는 것(끝에서부터 같은 글자가 많고, 길이가 비슷한 것).
        # "특정암보장개시일"을 "암보장개시일"의 날수로 읽지 않는다
        return definitions[min(related, key=lambda known: (-_same_tail(known, name), abs(len(known) - len(name))))], ""
    # 정의가 하나뿐이면 이름이 조금 달라도 그 날수로 본다. 다만 그 이름이 원문에 따로 적혀 있으면 다른 보장개시일이므로 넘겨짚지 않는다
    if len(set(definitions.values())) == 1 and not (name.endswith("보장개시일") and name in flat_source):
        return next(iter(definitions.values())), ""
    return 0, f"보장개시일 '{name}'의 날수를 주석에서 찾지 못함"


def parse(block: Block, raw: dict[str, Any], model: str) -> Extraction:
    benefits, problems = [], []
    definitions = waiting_definitions(block.text)
    flat_source = squash(block.text)
    for item in raw.get("benefits") or []:
        try:
            amount = parse_money(item["amount"])
            waiting, trouble = waiting_days_of(item, definitions, flat_source)
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
                exception=_exception(item.get("reduction_exception")),
            )
            if None not in (b.reduced_months, b.reduced_amount, b.reduced2_months, b.reduced2_amount) \
                    and b.reduced_months > b.reduced2_months:
                # 짧은 기간을 첫째 칸에 둔다. 모델이 두 구간을 바꿔 적어도 시트에는 같은 순서로 들어간다
                b.reduced_months, b.reduced2_months = b.reduced2_months, b.reduced_months
                b.reduced_amount, b.reduced2_amount = b.reduced2_amount, b.reduced_amount
                b.reduced_text, b.reduced2_text = b.reduced2_text, b.reduced_text
                b.period_text, b.period2_text = b.period2_text, b.period_text
            if b.reduced_amount is None:
                b.exception = ""
            if trouble:
                problems.append(f"{trouble}: {b.label}")
            # "1,000만원 × 해당 장해지급률"처럼 비율을 곱하는 금액은 그 사실이 시트에 남도록 한도 칸에 적는다
            tail = _multiplier(b.amount_text, b.quote)
            if tail and squash(tail) not in squash(b.limit):
                b.limit = f"× {tail}" + (f", {b.limit}" if b.limit else "")
            b.limit = _with_cell_notes(b.limit, b.amount_text, flat_source)
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
        if b.reduced2_amount is not None and b.reduced2_amount >= b.amount:
            problems.append(f"둘째 감액 금액이 지급액보다 작지 않음: {b.label}")
        if b.reduced_months is None and b.reduced_amount is None and (b.reduced2_months, b.reduced2_amount) != (None, None):
            problems.append(f"첫째 감액 구간 없이 둘째 구간만 적힘: {b.label}")
        if b.reduced_months is not None and b.reduced_months == b.reduced2_months:
            problems.append(f"두 감액 구간의 기간이 같음: {b.label}")
        benefits.append(b)
    benefits = split_by_start(benefits, block.text, definitions, problems)
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
        if float(manwon * 10000).is_integer():
            forms.append(f"{int(manwon * 10000)}원")
    return forms


def squash(text: str) -> str:
    return re.sub(r"[\s,]", "", text)


# '요로결석보장개시일'은 … 처럼 따옴표로 싼 이름도, 암보장개시일(이하 같습니다)은 … 처럼 괄호 말이 붙은 이름도 읽는다
_START_NAME = re.compile(r"([가-힣]{0,12}보장개시일)[’'”\"]?(?:\(이하[^()]{0,20}\))?[은는]")
_PLAIN_START = re.compile(r"(?<![가-힣’‘'\"“”])보장개시일\s*(?:\(|이후)")     # 이름 없이 "보장개시일 이후", "보장개시일(암은 암보장개시일) 이후"


_START_SPAN = re.compile(r"(\d+)(일|년|개월)이(?:지난|경과한)")
_START_FROM = ("계약일", "제1회보험료를받은날", "책임개시일")      # 날수를 세기 시작하는 날
_TABLE_START = re.compile(r"지급사유\s+지급금액")


def plain_start_in(text: str) -> bool:
    """표의 지급사유에 이름 없는 "보장개시일 이후"가 쓰였는가. 그 보장개시일은 계약일이라 기다리는 기간이 없다.

    주석("주)" 뒤)에 나오는 "최초계약의 보장개시일 이후"는 세지 않는다. 한 조각에 표가 여럿이면 표마다 주석 앞까지만 본다.
    빈칸을 떼지 않은 글에서 본다. 떼면 "중 보장개시일"의 앞말이 이름처럼 붙는다.
    """
    return any(_PLAIN_START.search(body) for body in _table_bodies(text))


def _table_bodies(text: str) -> list[str]:
    """조각에서 표 부분만. 주석("주)" 뒤)은 빼고, 한 조각에 표가 여럿이면 다음 표의 머리줄 뒤부터 다시 넣는다."""
    parts = text.split("주)")
    bodies = [parts[0]]
    for part in parts[1:]:
        m = _TABLE_START.search(part)
        if m:
            bodies.append(part[m.end():])
    return bodies


def waiting_definitions(text: str) -> dict[str, int]:
    """주석의 "○○보장개시일은 계약일부터 그 날을 포함하여 90일이 지난날의 다음날" 문장에서 이름과 날수를 읽는다.

    "제1회 보험료를 받은 날부터", "책임개시일부터"로 세는 문장과 "90일이 경과한 날"이라고 적은 문장도 같은 뜻으로 읽는다.

    문장 사이에 쪽 번호나 "[부활(효력회복)일]" 같은 글자가 끼어 있어도 읽도록, 이름 뒤 60자 안에서 "N일이 지난"을 찾는다.
    """
    flat = squash(text)
    out: dict[str, int] = {}
    for m in _START_NAME.finditer(flat):
        span = _START_SPAN.search(flat[m.end():m.end() + 60])
        if span and any(day in flat[m.end():m.end() + span.start()] for day in _START_FROM):
            n = int(span.group(1))
            name = m.group(1).split("경우")[-1]
            out.setdefault(name, n if span.group(2) == "일" else n * 365 if span.group(2) == "년" else n * 30)
    return out


# ---------- 대상마다 보장개시일이 다른 급부 ----------

# "보장개시일(암은 암보장개시일) 이후에 암, 기타피부암 또는 갑상선암으로 …": 괄호 안의 대상(암)만 이름 붙은 보장개시일을 쓰고
# 나머지 대상은 계약일부터 보장한다. 빈칸과 쉼표를 뗀 글에서 찾는다. 셋째 묶음은 "이후에" 뒤에 적힌 대상 목록이다
_MIXED_START = re.compile(r"보장개시일\((.{1,60}?)[은는]([가-힣]{0,15}보장개시일)\)이후에?(.{0,160}?)으?로")
_NEXT_ROW = re.compile(r"보장개시일|피보험자가|^\s*보험기간")      # 다음 지급사유가 시작하는 줄
_ROW_REACH = 20                                                  # 문구 뒤로 급부 이름을 찾는 줄 수의 상한
_QUOTE = re.compile(r"[‘’'\"“”]")
_TARGET_SEP = re.compile(r"\s*[·,/ㆍ∙•]\s*|\s+(?:및|또는)\s+")
_DISEASE = re.compile(r"(?:암|종양)$")


@dataclass(frozen=True)
class MixedStart:
    """'보장개시일(암은 암보장개시일) 이후' 꼴의 문구 하나."""
    special: str               # 괄호 안의 대상. 예: "암"
    start: str                 # 그 대상에 붙는 보장개시일. 예: "암보장개시일"
    listed: str                # "이후에" 뒤에 적힌 대상 목록(빈칸과 쉼표를 뗀 글). 표가 풀리며 다른 칸 글자가 끼어 있기도 하다
    lines: tuple[str, ...]     # 문구가 든 표 줄. 급부 이름이 여기 적혀 있어야 그 급부의 문구로 본다


def mixed_starts(text: str) -> list[MixedStart]:
    """표의 지급사유에서 대상마다 보장개시일이 다른 문구를 찾는다. 주석은 보지 않는다."""
    out = []
    for body in _table_bodies(text):
        lines = body.split("\n")
        flats = [squash(line) for line in lines]
        starts, at = [], 0
        for flat in flats:
            starts.append(at)
            at += len(flat)
        for m in _MIXED_START.finditer("".join(flats)):
            head = re.match(r"[가-힣]+", _QUOTE.sub("", m.group(1)))
            if not head:
                continue
            first = bisect.bisect_right(starts, m.start()) - 1
            last = bisect.bisect_right(starts, m.end() - 1) - 1
            stop = last + 1
            # 표가 풀리면 이름 칸의 글자가 지급사유 줄 사이에 끼어 있다. 다음 지급사유가 시작하는 줄 앞까지 본다
            while stop < len(lines) and stop - last <= _ROW_REACH and not _NEXT_ROW.search(lines[stop]):
                stop += 1
            out.append(MixedStart(head.group(0), m.group(2), m.group(3), tuple(lines[first:stop])))
    return out


def _written_from(name: str, lines: tuple[str, ...]) -> int | None:
    """급부 이름이 이 줄들에 적혀 있으면 첫 조각이 놓인 줄의 번호, 없으면 None.

    표가 글자로 풀리면 이름 칸의 글자가 여러 줄의 앞머리에 조각으로 놓인다("표적항암" / … / "약물허가치료자금" / … / "(주사제)").
    줄 앞머리의 낱말을 차례로 이어 붙여 이름이 되면 적혀 있다고 본다.
    """
    want, at, first = squash(name), 0, None
    for n, line in enumerate(lines):
        words = line.split()
        for k in range(len(words), 0, -1):
            piece = squash(" ".join(words[:k]))
            if piece and want.startswith(piece, at):
                first = n if first is None else first
                at += len(piece)
                break
        if want and at == len(want):
            return first
    return None


def _owners(phrase: MixedStart, names: set[str]) -> set[str]:
    """문구의 주인인 급부 이름. 문구가 든 표 줄에 적힌 이름 가운데 가장 먼저 적힌 것.

    다음 급부의 지급사유가 "보험기간", "피보험자가"로 시작하지 않으면 문구가 든 표 줄에 그 급부의 이름 칸까지 들어온다.
    한 문구는 한 급부의 지급사유이므로 뒤에 적힌 이름은 그 문구의 급부로 보지 않는다.
    """
    at = {name: n for name in names if (n := _written_from(name, phrase.lines)) is not None}
    if not at:
        return set()
    first = min(at.values())
    return {name for name, n in at.items() if n == first}


def _items(target: str) -> list[str]:
    """대상 글을 낱낱의 대상으로 가른다. 괄호 안의 쉼표("암(기타피부암, 갑상선암 제외)")에서는 가르지 않는다."""
    items, begin = [], 0
    for m in _TARGET_SEP.finditer(target):
        head = target[:m.start()]
        if head.count("(") + head.count("[") == head.count(")") + head.count("]"):
            items.append(target[begin:m.start()])
            begin = m.end()
    items.append(target[begin:])
    return [item.strip() for item in items if item.strip()]


def _base(item: str) -> str:
    """대상 낱말에서 괄호 앞부분. "암(기타피부암, 갑상선암 제외)" → "암"."""
    return squash(_QUOTE.sub("", item)).split("(")[0]


def _listed(item: str, phrase: MixedStart) -> bool:
    """대상 낱말이 문구의 대상 목록에 있는가. 숫자가 든 낱말("1종")은 대상이 아니다.

    표가 풀리며 낱말 사이에 다른 칸 글자가 끼어든 경우("기타100만원치료자금Ⅱ피부암")도 찾는다. 끼어든 글자는 모두 합쳐 15자까지 본다.
    """
    word = _base(item)
    if not word or re.search(r"\d", item):
        return False
    if word in phrase.listed:
        return True
    if len(word) < 2:
        return False
    gapped = re.compile(".{0,15}?".join(map(re.escape, word)))
    return any((m := gapped.match(phrase.listed, at)) and len(m.group(0)) <= len(word) + 15
               for at in range(len(phrase.listed)) if phrase.listed[at] == word[0])


def _listed_words(phrase: MixedStart, flat_source: str) -> list[str]:
    """문구의 대상 목록에서 괄호 안의 대상을 뺀 나머지. 예: ["기타피부암", "갑상선암"].

    따옴표로 싼 낱말만 읽는다. 표가 풀리며 다른 칸 글자가 끼어 낱말이 깨졌으면(원문의 다른 자리에 그 낱말이 없으면) 빈 목록.
    """
    marks = _QUOTE.findall(phrase.listed)
    if not marks or len(marks) % 2:
        return []
    rest = flat_source.replace(phrase.listed, "", 1)
    words = []
    for word in _QUOTE.split(phrase.listed)[1::2]:
        if word.startswith(phrase.special):         # 괄호 안의 대상. 뒤에 다른 칸 글자가 붙어 있을 수 있다
            continue
        if not re.fullmatch(r"[가-힣]{2,}", word) or word not in rest:
            return []
        words.append(word)
    return words


def _sort_targets(items: list[str], phrase: MixedStart) -> tuple[list[str], list[str], list[str]]:
    """대상 낱말을 (괄호 안의 대상, 문구에 적힌 나머지 대상, 문구에 없는 병명)으로 가른다. 등급("1종") 같은 낱말은 어디에도 들지 않는다."""
    named = [i for i in items if _base(i) == phrase.special]
    others = [i for i in items if i not in named and _listed(i, phrase)]
    unknown = [i for i in items if i not in named and i not in others and _DISEASE.search(_base(i))]
    return named, others, unknown


def _by_target(target: str, phrase: MixedStart) -> bool:
    """대상별로 나뉜 줄인가. 문구의 대상을 적었되, 괄호 안의 대상과 나머지 대상을 한 줄에 묶어 적은 줄(나눌 줄)은 아니다."""
    named, others, unknown = _sort_targets(_items(target), phrase)
    return bool(named or others) and not (len(named) == 1 and others and not unknown)


def _split(b: Benefit, siblings: list[Benefit], phrases: list[tuple[MixedStart, set[str]]], definitions: dict[str, int],
           flat_source: str) -> list[Benefit] | None:
    """급부 한 줄을 (괄호 안 대상의 줄, 나머지 대상의 줄)로 나눈다. 나눌 까닭이 없으면 None. phrases는 (문구, 그 문구의 주인 이름)."""
    items = _items(b.target)
    for phrase, owners in phrases:
        if b.name not in owners:
            continue
        days, trouble = waiting_days_of({"start_condition": phrase.start}, definitions, flat_source)
        if trouble or not days:
            continue
        named, others, unknown = _sort_targets(items, phrase)
        if unknown:             # 문구에 없는 대상이 섞여 있으면 어느 쪽인지 모른다
            continue
        if len(named) == 1 and others:
            # 대상을 묶어 적은 줄. 예: "암·기타피부암·갑상선암·1종" → "암·1종", "기타피부암·갑상선암·1종"
            first, rest = [i for i in items if i not in others], [i for i in items if i not in named]
        elif not named and not others and not any(_by_target(s.target, phrase) for s in siblings):
            # 대상을 적지 않은 줄. 예: "1종" → "암·1종", "기타피부암·갑상선암·1종". 같은 급부의 다른 줄이 대상별로 나뉘어 있으면 손대지 않는다.
            # 다른 줄이 대상을 묶어 적었으면(그 줄도 나눌 줄이다) 이 줄도 나눈다
            words = _listed_words(phrase, flat_source)
            if not words:
                continue
            first, rest = [phrase.special] + items, words + items
        else:
            continue
        return [replace(b, target="·".join(first), waiting_days=days, split_from=b.label),
                replace(b, target="·".join(rest), waiting_days=0, split_from=b.label)]
    return None


def split_by_start(benefits: list[Benefit], text: str, definitions: dict[str, int], problems: list[str]) -> list[Benefit]:
    """대상마다 보장개시일이 다른 급부가 한 줄로 묶여 오면 대상별 줄로 나누고 면책을 따로 매긴다.

    원문이 "보장개시일(암은 암보장개시일) 이후에 암, 기타피부암 또는 갑상선암으로 …"이면 암은 암보장개시일의 날수,
    기타피부암·갑상선암은 0일이다. 지시문에 나누라고 적어 두었지만, 등급(1종~5종)으로도 나뉘는 급부에서 모델이
    "암·기타피부암·갑상선암·1종"이나 "1종"처럼 대상을 묶은 줄 하나로 적는 일이 있었다(한화 요약서 78쪽, 81쪽).

    나누는 경우는 급부 이름이 그 문구가 든 표 줄에 맨 먼저 적혀 있고, 그 줄의 대상이 문구의 대상을 묶어 적었거나 대상을 적지 않았을 때뿐이다.
    이미 대상별로 나뉘어 온 줄, 형식 문제가 걸린 줄, 나누면 다른 줄과 급부ID가 겹치는 줄은 그대로 둔다.
    급부ID는 이름의 구두점과 이음말을 떼고 만들므로("기타피부암·갑상선암"과 "기타피부암 및 갑상선암"이 같다) 겹침도 ID로 본다.
    """
    phrases = mixed_starts(text)
    if not phrases:
        return benefits
    flat_source = squash(text)
    names = {b.name for b in benefits}
    owned = [(phrase, _owners(phrase, names)) for phrase in phrases]

    def key(label: str) -> str:
        return ids.benefit_id("", label)        # 한 조각은 한 특약이므로 특약 부분은 비워도 된다

    taken = Counter(key(b.label) for b in benefits)
    out: list[Benefit] = []
    for b in benefits:
        parts = None
        if not any(p.endswith(f": {b.label}") for p in problems):
            parts = _split(b, [o for o in benefits if o is not b and o.name == b.name], owned, definitions, flat_source)
        made = {key(x.label) for x in parts} if parts else set()
        rest = taken - Counter([key(b.label)])
        if parts and len(made) == 2 and not any(k in rest for k in made):
            out += parts
            taken = rest + Counter(made)
        else:
            out.append(b)
    return out


_NOISE = re.compile(r"보험계약일부터|\d+억\d*천?만?원|\d+천만원|\d+(?:\.\d+)?만\d*천?원|\d+천원|\d+원|\d+(?:년|개월)(?:미만|이상)")


def _in_source(flat: str, squashed_source: str) -> bool:
    """빈칸을 뗀 글자(flat)가 원문에 있는가. 원문 쪽에 끼어든 다른 칸의 글자(금액, 1년미만 등)만 건너뛴다.

    flat에 든 금액·기간은 건너뛰지 않는다. 한도나 감액 예외에 적은 금액이 원문과 다르면 없는 것으로 본다.
    """
    if not flat:
        return False
    if flat in squashed_source:
        return True
    gap = f"(?:{_NOISE.pattern})*"
    pattern = re.escape(flat[0])
    for before, c in zip(flat, flat[1:]):
        # 숫자 가운데는 가르지 않는다. "12만원 20일 한도"를 "120일 한도"로 읽지 않는다
        pattern += ("" if before.isdigit() and c.isdigit() else gap) + re.escape(c)
    return re.search(pattern, squashed_source) is not None


def limit_in_source(limit: str, squashed_source: str) -> bool:
    """한도 글자가 원문에 그대로 있는가. 표가 풀리며 사이에 끼어든 다른 칸의 글자(금액, 1년미만 등)는 빼고 견준다."""
    if _in_source(squash(limit), squashed_source):
        return True
    # "1일 1회한, 연간 최대 30회 한도"처럼 지급사유의 조건과 주석의 한도를 쉼표로 이은 글자는 조각마다 본다.
    # 짧은 조각은 어디에나 있어 보지 않지만, 금액 칸에서 옮겨 온 단위("1일당", "수술 1회당")는 조각으로 센다
    pieces = [squash(x) for x in limit.split(",") if len(squash(x)) >= 4 or _UNIT.fullmatch(squash(x))]
    return len(pieces) >= 2 and all(_in_source(x, squashed_source) for x in pieces)


_REACH = 120      # 감싸는 괄호를 찾는 거리. 짝이 맞지 않는 괄호("1)", "주1)") 때문에 먼 괄호까지 가지 않게 한다


def _enclosing(src: str, start: int, end: int) -> tuple[int, int]:
    """src[start:end]를 감싸는 괄호의 (여는 자리, 닫는 자리). 감싸는 괄호가 없으면 (-1, -1).

    앞에 "(유사암 제외)"처럼 닫힌 괄호가 끼어 있어도 그 바깥의 여는 괄호를 찾는다.
    """
    left, depth = -1, 0
    for i in range(start - 1, max(-1, start - 1 - _REACH), -1):
        if src[i] == ")":
            depth += 1
        elif src[i] == "(":
            if depth == 0:
                left = i
                break
            depth -= 1
    if left < 0:
        return -1, -1
    depth = 0
    for i in range(end, min(len(src), end + _REACH)):
        if src[i] == "(":
            depth += 1
        elif src[i] == ")":
            if depth == 0:
                return left, i
            depth -= 1
    return -1, -1


def limit_is_partial(limit: str, squashed_source: str) -> bool:
    """한도 글자가 원문 괄호 안 조건의 일부만 옮긴 것인가.

    "(단, 암, 갑상선암 … 중 최초 1회에 한함)"에서 "최초 1회에 한함"만 옮기면 뜻이 달라진다.
    표가 글자로 풀리면서 괄호 안에 끼어든 다른 칸의 글자(보험계약일부터, 금액, 1년미만 등)는 빼고 견준다.
    같은 글자가 여러 급부에 나오므로 모든 자리를 보고, 괄호를 꽉 채운 자리가 하나라도 있으면 일부가 아니다.
    """
    src = _NOISE.sub("", squashed_source)
    flat = _NOISE.sub("", squash(limit))
    if not flat:
        return False
    seen = False
    at = src.find(flat)
    while at >= 0:
        left, right = _enclosing(src, at, at + len(flat))
        if left >= 0 and right >= 0:      # 괄호 안에 있다
            seen = True
            inner = src[left + 1:right]
            inner = inner[1:] if inner.startswith("단") else inner
            if len(inner) - len(flat) < 3:
                return False
        at = src.find(flat, at + 1)
    return seen


def literal_problems(ex: Extraction) -> dict[str, list[str]]:
    """급부별로, 원문에서 글자 그대로 확인되지 않은 항목. 여기 걸린 항목은 판정 모델이 다시 본다.

    급부 이름은 보지 않는다. 표에서는 이름이 "암진단 / 보험금"처럼 줄이 갈려 다른 칸의 글자와 섞이므로
    글자 비교로는 가릴 수 없다. 이름이 실제로 있는지는 판정 모델이 본다.
    """
    source = squash(ex.block.text)

    def written(token: str) -> bool:      # 빈칸을 떼지 않은 글에서 본다. 떼면 옆 칸의 숫자가 붙어("180" + "1년미만") 숫자 경계를 볼 수 없다
        return bool(token) and re.search(_spaced(token), ex.block.text) is not None

    out: dict[str, list[str]] = {}
    for b in ex.benefits:
        missing = []
        for label, value, text in (("기준지급금액만원", b.amount, b.amount_text), ("감액지급률1", b.reduced_amount, b.reduced_text),
                                   ("감액지급률2", b.reduced2_amount, b.reduced2_text)):
            if value is None:
                continue
            forms = [money_token(text)] if money_token(text) else amount_forms(value)   # 금액 뒤에 붙은 설명은 줄이 갈려 비교하지 않는다
            if not any(written(f) for f in forms):
                missing.append(label)
        for label, months, text in (("감액개월1", b.reduced_months, b.period_text), ("감액개월2", b.reduced2_months, b.period2_text)):
            if months is not None and text and not written(period_token(text)):   # "2년미만"이라 적었는데 원문에 그 글자가 없다
                missing.append(label)
        if b.waiting_days and b.waiting_days not in waiting_definitions(ex.block.text).values():
            missing.append("면책기간일수")
        if b.exception and not limit_in_source(b.exception, source):
            missing.append("감액예외")
        if b.limit and not limit_in_source(b.limit, source):
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
            "감액예외": b.exception or None,
            "근거문서종류": doc_kind,
            "근거문서쪽수": ex.block.first_page,
        })
    return rows
