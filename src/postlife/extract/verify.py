"""추출값을 판정 전용 모델로 원문과 대조한다 (기획 6.2의 3~5단계).

판정 모델은 글을 쓰지 않고 "이 값이 원문과 일치하는가"에 확률만 매긴다.
해석 규칙은 문항에 적는다 (6.3). 구간 경계는 hum_기준값의 판정구간 행에서 읽는다.
"""
from __future__ import annotations

from typing import Any

from .benefits import Benefit, Extraction, limit_in_source, money_token, period_token, plain_start_in, squash, waiting_definitions

RULES = (
    "원문은 표가 글자로 풀린 것이라 줄이 뒤섞여 있다. 낱말이 여러 줄에 갈려 있어도 같은 칸의 글자면 이어서 읽는다. "
    "'계약일부터 그 날을 포함하여 90일이 지난날의 다음날'은 기다리는 기간 90일로, '1년이 지난 날의 다음날'은 365일로 본다. "
    "'1년미만 500만원, 1년이상 1,000만원'은 계약 후 12개월 미만 감액 500만원, 이후 지급액 1,000만원으로 본다. "
    "1만5천원은 1.5만원이다. "
    "'1년미만 500만원 ※ 단, 계약일부터 180일이내 …시 250만원'은 180일 이내 250만원, 그 뒤 1년 미만 500만원으로 본다. "
    "지급금액 칸의 '※ 단, 재해로 인한 …시 금액'은 원인에 따른 감액 예외이므로, 지급액과 감액 금액을 볼 때는 따지지 않는다."
)


def _money(v: float) -> str:
    return f"{int(v):,}만원" if float(v).is_integer() else f"{v}만원"


def _span(months: int, text: str) -> str:
    """감액 기간을 문항에 적는 말. 날수로 적힌 기간("180일이내")은 개월로 바꾸지 않고 원문 글자로 묻는다."""
    token = period_token(text)
    return token if "일" in token else f"{months}개월 미만"


AFTER_START, FROM_DAY_ONE = "보장개시일 조건 있음", "보장개시일 조건 없음"


def checks(b: Benefit, source: str) -> dict[str, tuple[dict, Any]]:
    """급부 한 줄을 판정 문항으로 바꾼다. 값은 (문항, 추출값이 맞다면 골라져야 하는 답).

    - 지급액과 감액: 따로 묻는다. 한 진술에 묶으면 한쪽이 맞을 때 틀린 쪽까지 높은 확률을 받는 일이 있었다.
      지급액 진술은 줄이 없으면 거짓이 되므로 줄이 실제로 있는지도 함께 가려진다.
    - 면책기간: 날수는 코드가 주석의 보장개시일 정의 문장에서 확인한다. 여기서는 그 줄의 지급사유가
      "○○보장개시일 이후"라는 조건이 들어 있는지 없는지를 고르게 한다. 원문에 보장개시일 문구가 없으면 묻지 않는다.
      (참·거짓으로 물으면 맞는 줄도 0.5~0.8에 머물렀고, 둘 중 고르게 하면 대부분 0.95를 넘었다.)
    - 지급한도: 적은 글자가 원문에 그대로 있으면 코드 확인으로 끝내고, 없을 때만 묻는다.
    """
    who = f"지급구분 '{b.name}'" + (f"에서 '{b.target}'을 보장하는 줄" if b.target else "")

    def statement(claim: str) -> dict:
        return {"type": "noul", "instructions": "다음 진술이 원문과 일치하면 참, 원문과 다르거나 원문에 근거가 없으면 거짓. "
                                                f"진술: {claim}. 읽는 규칙: {RULES}"}

    out: dict[str, tuple[dict, Any]] = {}
    reduced = b.reduced_amount is not None and b.reduced_months is not None
    extra = squash(b.amount_text).replace(money_token(b.amount_text), "")
    if "×" in b.quote or "×" in b.limit or "×" in b.amount_text or "지급률" in b.limit:
        formula = True
        out["기준지급금액만원"] = (statement(f"원문 표에 {who}이 있고, 그 지급액은 {_money(b.amount)}에 해당 지급률을 곱한 금액이다"), True)
    elif extra and not reduced:
        # "2,000만 원 + 플러스적립금", "매월 60만 원 (최초 36개월 보증지급)"처럼 금액에 설명이 붙은 칸은 적힌 글자를 묻는다
        formula = True
        out["기준지급금액만원"] = (statement(f"원문 표에 {who}이 있고, 지급액 칸에 '{b.amount_text}'(이)라고 적혀 있다 "
                                       "(줄이 갈려 있어도 같은 칸이면 이어 읽는다)"), True)
    else:
        formula = False
        late = " (경과기간에 따라 금액이 나뉘어 있으면 가장 늦은 구간의 금액을 지급액으로 본다)"
        out["기준지급금액만원"] = (statement(f"원문 표에 {who}이 있고, 그 지급액은 {_money(b.amount)}이다{late}"), True)
    if reduced:
        times = "에 해당 지급률을 곱한 금액" if formula else ""       # "500만원 × 해당 장해지급률"로 적힌 감액
        cut = f"계약일부터 {_span(b.reduced_months, b.period_text)}에는 {_money(b.reduced_amount)}{times}"
        if b.reduced2_amount is not None and b.reduced2_months is not None:
            cut += f", {_span(b.reduced2_months, b.period2_text)}에는 {_money(b.reduced2_amount)}{times}"
        out["감액지급률1"] = (statement(f"{who}은 {cut}을 지급한다"), True)
    else:
        out["감액지급률1"] = (statement(f"{who}의 지급액은 한 가지 금액만 적혀 있고, 계약일부터 1년 미만·2년 미만 같은 "
                                    "경과기간에 따라 나뉘어 있지 않다"), True)
    if b.exception and not limit_in_source(b.exception, squash(source)):
        out["감액예외"] = (statement(f"{who}에는 '{b.exception}'(이)라는 감액 예외가 표나 주석에 적혀 있다 "
                                 "(줄이 갈려 있어도 같은 칸이나 같은 문장이면 이어 읽는다)"), True)
    if "보장개시일" in source:
        case = f"'{b.target}'에 해당하는 경우" if b.target else "경우"
        out["면책기간일수"] = ({
            "type": "choice",
            "instructions": f"'{b.name}'의 지급사유 가운데 {case}에 '○○보장개시일 이후'라는 조건이 들어 있는가? "
                            "한 칸에 두 경우가 '…하였거나, 보험기간 중 …'처럼 이어져 있으면 해당하는 쪽 문장만 본다. "
                            "'보험기간 중 암보장개시일 이후에'처럼 두 말이 함께 있으면 조건이 있는 것이다.",
            "criteria": ({AFTER_START: "그 경우의 지급사유에 '암보장개시일', '요로결석보장개시일'처럼 앞에 이름이 붙은 "
                                       "'○○보장개시일 이후'라는 조건이 적용된다",
                          FROM_DAY_ONE: "그 경우의 지급사유 문장에 보장개시일이라는 말이 없거나, 앞에 이름이 붙지 않은 '보장개시일 이후'만 "
                                        "적용된다 ('보장개시일(암은 암보장개시일) 이후'에서 암이 아닌 경우는 여기에 든다)"}
                         if plain_start_in(source) else
                         {AFTER_START: "그 경우의 지급사유 문장에 '○○보장개시일 이후'라는 말이 들어 있다",
                          FROM_DAY_ONE: "그 경우의 지급사유 문장에 보장개시일이라는 말이 없다"}),
        }, AFTER_START if b.waiting_days else FROM_DAY_ONE)
    if b.limit and not formula and not limit_in_source(b.limit, squash(source)):
        out["지급횟수제한"] = (statement(f"{who}의 지급 횟수·한도 조건은 '{b.limit}'이고, 원문에 적힌 조건에서 빠진 말이 없다"), True)
    return out


def questions(ex: Extraction) -> tuple[dict[str, dict], dict[str, tuple[str, str, Any]]]:
    """판정 문항과, 문항 키 → (급부 이름, 항목, 맞다면 골라져야 하는 답) 대응."""
    qs: dict[str, dict] = {}
    index: dict[str, tuple[str, str, Any]] = {}
    for i, b in enumerate(ex.benefits):
        for j, (name, (question, expect)) in enumerate(checks(b, ex.block.text).items()):
            key = f"b{i}_{j}"
            qs[key] = question
            index[key] = (b.label, name, expect)
    return qs, index


def judge(gemini: Any, ex: Extraction, model: str) -> dict[str, dict[str, float]]:
    """급부별·항목별로 추출값이 원문과 일치할 확률."""
    if not ex.benefits:
        return {}
    qs, index = questions(ex)
    answers = gemini.decide(model, f"특약 이름: {ex.block.title}\n\n{ex.block.text}", qs)
    out: dict[str, dict[str, float]] = {b.label: {} for b in ex.benefits}
    for key, (label, name, expect) in index.items():
        if key in answers:
            out[label][name] = answers[key].prob(expect)
    return out


def classify(probs: dict[str, float], thresholds: dict[str, float]) -> tuple[str, str, float]:
    """(구간, 가장 낮은 항목, 그 확률). 구간은 확정 / 검토 / 재추출."""
    if not probs:
        return "검토", "", 0.0
    name, low = min(probs.items(), key=lambda kv: kv[1])
    if low >= thresholds["추출검증_통과"]:
        return "확정", name, low
    if low < thresholds["추출검증_재추출"]:
        return "재추출", name, low
    return "검토", name, low


def worst(result: dict[str, dict[str, float]]) -> float:
    """조각 전체에서 가장 낮은 확률. 재추출 전후를 비교할 때 쓴다."""
    values = [p for fields in result.values() for p in fields.values()]
    return min(values) if values else 0.0
