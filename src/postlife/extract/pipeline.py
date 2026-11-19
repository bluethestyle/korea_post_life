"""상품요약서 한 건을 급부 행으로 바꾸는 전체 흐름.

추출(생성 모델) → 코드 대조 → 판정(판정 전용 모델) → 세 구간 분기 → 재추출(다른 모델) → 기록.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .. import config, ids
from ..gemini import GeminiError
from ..worklog import WorkLog
from . import benefits as B
from . import verify as V
from .segment import Block, renewal_periods, rider_blocks, rider_key, scope_matches, scope_parts

FIELD_NAMES = {"기준지급금액만원": "지급액", "감액지급률1": "감액 기간·금액(없으면 빈칸)", "면책기간일수": "보장개시일 조건(start_condition)", "지급횟수제한": "지급 한도(limit)", "감액예외": "감액 예외(reduction_exception)"}
# 2026-11-18 우체국 요약서 2건으로 맞춘 값 (docs/progress.md). 시트의 hum_기준값이 있으면 그 값을 쓴다.
DEFAULT_THRESHOLDS = {"추출검증_통과": 0.75, "추출검증_재추출": 0.40}


@dataclass
class BlockResult:
    extraction: B.Extraction
    probs: dict[str, dict[str, float]]
    status: dict[str, str]                 # 급부 이름 → 확정 / 검토 / 제외(시트에 쓰지 않음)
    retried: bool = False


@dataclass
class Result:
    riders: list[dict[str, Any]] = field(default_factory=list)
    benefits: list[dict[str, Any]] = field(default_factory=list)
    logs: list[dict[str, Any]] = field(default_factory=list)
    blocks: list[BlockResult] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


def thresholds_from(rows: list[dict[str, Any]]) -> dict[str, float]:
    out = dict(DEFAULT_THRESHOLDS)
    for r in rows:
        if r.get("기준분류") == "판정구간" and r.get("기준키") in out and r.get("수치값") is not None:
            out[r["기준키"]] = float(r["수치값"])
    return out


# 코드 대조에서 걸리면 다시 뽑게 하는 칸. "지급한도일부"는 한도 조건을 일부만 옮긴 경우다.
_AMOUNT_FIELDS = {"기준지급금액만원", "감액지급률1", "감액지급률2", "감액개월1", "감액개월2", "지급한도일부"}


@dataclass
class _Try:
    ex: B.Extraction
    probs: dict[str, dict[str, float]]
    literal: dict[str, list[str]]

    @property
    def invented(self) -> int:
        """원문에 없는 금액이나 감액 기간을 적은 줄 수. 지어낸 값일 가능성이 높다."""
        return sum(1 for fields in self.literal.values() if _AMOUNT_FIELDS & set(fields))

    def flawed(self, label: str) -> bool:
        """코드가 문제를 잡은 줄인가 (형식 문제, 원문에 없는 금액·기간)."""
        return bool(_AMOUNT_FIELDS & set(self.literal.get(label, []))) or any(label in p for p in self.ex.problems)

    def score(self, thresholds: dict[str, float]) -> tuple[int, int, float]:
        """작을수록 낫다: (틀렸다고 볼 줄 수, 사람이 볼 줄 수, -가장 낮은 판정 확률).

        틀렸다고 볼 줄: 코드가 문제를 잡았거나 판정 확률이 재추출 구간인 줄, 그리고 줄에 묶이지 않은 형식 문제.
        사람이 볼 줄: 확률이 통과 기준에 조금 못 미친 줄. 맞는 줄도 여기에 드는 일이 있어 가볍게 센다.
        이렇게 나누지 않으면, 줄 하나를 빠뜨리고 값이 틀린 결과가 "확인할 줄이 적다"는 이유로 맞는 결과를 밀어낸다.
        """
        labels = [b.label for b in self.ex.benefits]
        bands = {label: V.classify(self.probs.get(label, {}), thresholds)[0] for label in labels}
        hard = sum(1 for label in labels if self.flawed(label) or bands[label] == "재추출")
        hard += sum(1 for p in self.ex.problems if not any(label in p for label in labels))
        soft = sum(1 for label in labels if bands[label] == "검토" and not self.flawed(label))
        return (hard, soft, -V.worst(self.probs))

    def needs_retry(self, thresholds: dict[str, float]) -> bool:
        return (not self.ex.benefits) or bool(self.ex.problems) or self.invented > 0 or any(
            V.classify(self.probs.get(b.label, {}), thresholds)[0] == "재추출" for b in self.ex.benefits)

    def feedback(self, thresholds: dict[str, float]) -> list[str]:
        out = list(self.ex.problems)
        for b in self.ex.benefits:
            if "지급한도일부" in self.literal.get(b.label, []):
                out.append(f"'{b.label}' 줄의 limit이 원문 괄호 안 조건의 일부만 옮김. 괄호 안 조건을 빠짐없이 옮길 것")
            if (_AMOUNT_FIELDS - {"지급한도일부"}) & set(self.literal.get(b.label, [])):
                out.append(f"'{b.label}' 줄에 원문에 없는 금액이나 기간을 적음. 금액과 기간은 원문 글자 그대로만 옮김")
            band, name, _ = V.classify(self.probs.get(b.label, {}), thresholds)
            if band == "재추출":
                out.append(f"'{b.label}' 줄의 {FIELD_NAMES.get(name, name)}이(가) 원문과 맞지 않아 보임")
        return out


def _attempt(gemini: Any, block: Block, model: str, feedback: list[str] | None = None) -> _Try:
    ex = B.extract(gemini, block, model, feedback)
    try:
        probs = V.judge(gemini, ex, config.MODEL_DECIDE)
    except GeminiError:
        # 판정 모델이 분당 한도에 걸렸을 때 뽑은 값까지 버리지 않는다. 한 번 더 묻고, 그래도 안 되면 판정 없이(사람 검토) 넘긴다
        try:
            probs = V.judge(gemini, ex, config.MODEL_DECIDE)
        except GeminiError:
            probs = {}
    return _Try(ex, probs, B.literal_problems(ex))


def run_block(gemini: Any, block: Block, thresholds: dict[str, float], log: WorkLog, variant_id: str,
              budget: dict[str, int] | None = None) -> BlockResult | None:
    """한 특약을 처리한다. 값이 의심스러우면 다른 모델로, 그래도 안 되면 상위 모델로 다시 뽑는다.

    budget: {"상위모델": 남은 횟수}. 상위 모델은 하루 한도가 작아 한 번 실행에 쓸 횟수를 정해 둔다.
    """
    rider = ids.rider_id(variant_id, block.rider_name)
    budget = budget if budget is not None else {"상위모델": 0}
    best: _Try | None = None
    retried = False
    for step, model in enumerate((config.MODEL_EXTRACT, config.MODEL_EXTRACT_ALT, config.MODEL_SUMMARY)):
        if best is not None and not best.needs_retry(thresholds):
            break
        if model == config.MODEL_SUMMARY:
            if budget.get("상위모델", 0) <= 0:
                break
            budget["상위모델"] -= 1
        stage = "추출" if best is None else "재추출"
        try:
            got = _attempt(gemini, block, model, best.feedback(thresholds) if best else None)
        except (GeminiError, ValueError, KeyError) as e:
            log.add(stage, rider, "보류", f"호출 실패: {str(e)[:200]}", model=model)
            if model == config.MODEL_SUMMARY and "429" in str(e):
                budget["상위모델"] = 0        # 상위 모델의 하루 한도가 찼다. 남은 조각에서 헛되이 부르지 않는다
            continue
        for b in got.ex.benefits:       # 코드 대조에서 걸린 줄은 시도마다 남긴다
            if got.literal.get(b.label):
                log.add("코드대조", ids.benefit_id(rider, b.label), "보류", "원문에서 글자 그대로 확인되지 않아 판정으로 넘김",
                        model=model, column=", ".join(got.literal[b.label]))
        if best is None:
            best = got
            log.add("추출", rider, "통과", f"{block.rider_name}: 급부 {len(got.ex.benefits)}건" +
                    (f", 형식 문제 {len(got.ex.problems)}건" if got.ex.problems else ""), model=model)
            continue
        retried = True
        was, now = best.score(thresholds), got.score(thresholds)
        better = bool(got.ex.benefits) and now < was
        before, after = V.worst(best.probs), V.worst(got.probs)
        log.add("재추출", rider, "통과" if better else "반려",
                f"{block.rider_name}: 틀렸다고 볼 줄 {was[0]}건 → {now[0]}건, 사람이 볼 줄 {was[1]}건 → {now[1]}건, "
                f"가장 낮은 확률 {before:.2f} → {after:.2f}. " +
                ("다시 뽑은 값으로 바꿈" if better else "앞선 값을 유지"),
                model=model, prob=after, before=f"급부 {len(best.ex.benefits)}건", after=f"급부 {len(got.ex.benefits)}건")
        if better:
            best = got
    if best is None:
        return None
    ex, probs = best.ex, best.probs

    for b in ex.benefits:
        target = ids.benefit_id(rider, b.label)
        if not best.literal.get(b.label):
            log.add("코드대조", target, "통과", "금액과 기간이 원문에 글자 그대로 있음")

    status: dict[str, str] = {}
    for b in ex.benefits:
        target = ids.benefit_id(rider, b.label)
        band, name, low = V.classify(probs.get(b.label, {}), thresholds)
        broken = [p for p in ex.problems if b.label in p]
        if broken:
            # 값끼리 앞뒤가 안 맞는 줄(감액 금액이 지급액 이상 등)은 그대로 쓰면 틀린 값이 된다
            status[b.label] = "제외"
            log.add("판정", target, "반려", f"값이 앞뒤가 맞지 않아 시트에 쓰지 않음: {broken[0]}"[:300],
                    model=config.MODEL_DECIDE, prob=low, column=name or "기준지급금액만원")
            log.add("사람검토이관", target, "보류", f"{b.label}: 시트에 쓰지 않음. {broken[0]} (근거 {block.first_page}쪽)"[:300],
                    model=config.MODEL_DECIDE, prob=low, column=name or "기준지급금액만원")
            continue
        if band == "확정" and best.flawed(b.label):      # 판정 확률이 높아도 코드가 잡은 문제가 있으면 사람이 본다
            band, name = "검토", name or "기준지급금액만원"
        if band == "확정":
            status[b.label] = "확정"
            log.add("판정", target, "통과", model=config.MODEL_DECIDE, prob=low, column=name)
        elif band == "재추출":
            # 다시 뽑아도 재추출 구간이면 틀린 값일 가능성이 높다. 시트에 쓰지 않고 사람에게 넘긴다.
            status[b.label] = "제외"
            log.add("판정", target, "반려", f"다시 뽑아도 원문과 맞지 않아 보여 시트에 쓰지 않음: {name}",
                    model=config.MODEL_DECIDE, prob=low, column=name)
            log.add("사람검토이관", target, "보류", f"{b.label}: 시트에 쓰지 않음. {name} 확인 필요 (근거 {block.first_page}쪽)",
                    model=config.MODEL_DECIDE, prob=low, column=name)
        else:
            status[b.label] = "검토"
            log.add("판정", target, "보류", f"원문과 일치할 확률이 낮은 항목: {name}", model=config.MODEL_DECIDE, prob=low, column=name)
            log.add("사람검토이관", target, "보류", f"{b.label}: {name} 확인 필요 (근거 {block.first_page}쪽)",
                    model=config.MODEL_DECIDE, prob=low, column=name)
    return BlockResult(ex, probs, status, retried)


def run_summary(gemini: Any, pages: dict[int, str], variant_ids: list[str], now: datetime,
                thresholds: dict[str, float] | None = None, product_renewal_years: int | None = None,
                only: list[str] | None = None, budget: dict[str, int] | None = None,
                plain_renewal_years: int | None = None, variant_names: dict[str, str] | None = None) -> Result:
    """상품요약서 한 건을 처리한다. 여러 종이 한 요약서를 함께 쓰면 뽑은 값을 종마다 같은 내용으로 싣는다.

    variant_names: {종형ID: 종형명}. 조각 안의 표가 "[간편가입형]"처럼 가입유형별로 갈린 요약서에서는 이 이름으로
    부분마다 해당하는 종형을 가린다. 해당하는 종형이 없는 부분은 모델을 부르지 않고 건너뛴다.
    이름에 "(갱신형)"만 있는 특약의 주기는 요약서의 갱신형 특약 목록에서 읽고, 주기가 여럿이면 가장 짧은 것을 적는다.
    """
    thresholds = thresholds or dict(DEFAULT_THRESHOLDS)
    log = WorkLog(now, "sys_급부")
    result = Result()
    blocks = [b for b in rider_blocks(pages) if not only or any(k in b.title for k in only)]
    periods = renewal_periods(pages)
    # 상위 모델은 하루 한도가 작다. 여러 요약서를 한 번에 돌릴 때는 호출한 쪽이 넘긴 횟수를 함께 쓴다.
    budget = budget if budget is not None else {"상위모델": config.EXTRACT_ESCALATIONS_PER_RUN}
    start = budget["상위모델"]
    units = 0
    for block in blocks:
        parts = scope_parts(block) if variant_names else [("", block.text)]
        listed = periods.get(rider_key(block.rider_name))
        years = min(listed) if listed else plain_renewal_years
        with_rider: set[str] = set()
        for scope, text in parts:
            matched = [v for v in variant_ids if not scope or scope_matches(scope, (variant_names or {}).get(v, ""))]
            if not matched:
                continue
            units += 1
            part = block if len(parts) == 1 else Block(block.title, text, block.first_page, block.last_page)
            done = run_block(gemini, part, thresholds, log, matched[0], budget)
            if done is None:
                continue
            result.blocks.append(done)
            dropped = {label for label, state in done.status.items() if state == "제외"}
            for variant in matched:
                if variant not in with_rider:
                    with_rider.add(variant)
                    result.riders.append(B.rider_row(variant, block, product_renewal_years, years))
                result.benefits.extend(B.benefit_rows(variant, done.extraction, skip=dropped))
    result.logs = log.rows
    statuses = [s for b in result.blocks for s in b.status.values()]
    result.stats = {
        "조각": units, "처리한 조각": len(result.blocks),
        "급부": len(statuses), "확정": statuses.count("확정"), "검토": statuses.count("검토"), "제외": statuses.count("제외"),
        "재추출한 조각": sum(b.retried for b in result.blocks),
        "상위 모델 사용": start - budget["상위모델"],
    }
    return result
