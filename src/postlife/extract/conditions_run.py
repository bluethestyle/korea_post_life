"""가입조건·결합 제약 추출의 전체 흐름: 절 찾기 → 추출 → 코드 대조 → 판정 → 재추출 → 행 만들기."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .. import config
from ..gemini import GeminiError
from ..worklog import WorkLog
from . import conditions as C
from . import verify as V

TAB_OF = {"가입나이": "sys_가입조건", "가입한도": "sys_가입조건", "결합제약": "sys_결합제약"}


def _about(problem: str, key: str) -> bool:
    """문제 문장이 그 항목의 것인가. conditions.parse가 적는 문제는 "…: 항목 키"로 끝난다.

    키가 문장 어딘가에 들어 있는지만 보면, 이름이 더 긴 다른 항목의 문제("…: 가특약(1종)")가 "가특약" 항목의 것으로 잡힌다.
    """
    return problem.endswith(f": {key}")


@dataclass
class _Shot:
    ex: C.Extracted
    probs: dict[str, dict[str, float]]
    literal: dict[str, list[str]]

    def flawed(self, key: str) -> bool:
        return bool(self.literal.get(key)) or any(_about(p, key) for p in self.ex.problems)

    def band(self, key: str, thresholds: dict[str, float]) -> tuple[str, str, float]:
        return V.classify(self.probs.get(key, {}), thresholds)

    def score(self, thresholds: dict[str, float]) -> tuple[int, int, float]:
        """작을수록 낫다. 급부 추출과 같은 기준: (틀렸다고 볼 항목 수, 사람이 볼 항목 수, -가장 낮은 확률)."""
        keys = [i.key for i in self.ex.items]
        bands = {k: self.band(k, thresholds)[0] for k in keys}
        hard = sum(1 for k in keys if self.flawed(k) or bands[k] == "재추출")
        hard += sum(1 for p in self.ex.problems if not any(_about(p, k) for k in keys))
        soft = sum(1 for k in keys if bands[k] == "검토" and not self.flawed(k))
        return (hard, soft, -V.worst(self.probs))

    @property
    def empty(self) -> bool:
        """가입나이·가입한도 절에서 항목이 하나도 없는가. 이 절들에는 줄이 적어도 하나 있으므로 0건은 잘못 뽑은 것이다.

        결합제약은 옮길 제약이 없는 절도 있어 0건이 맞는 답일 수 있다.
        """
        return not self.ex.items and self.ex.kind != "결합제약"

    def needs_retry(self, thresholds: dict[str, float]) -> bool:
        return self.empty or self.score(thresholds)[0] > 0

    def feedback(self, thresholds: dict[str, float]) -> list[str]:
        out = list(self.ex.problems)
        for item in self.ex.items:
            if self.literal.get(item.key):
                out.append(f"'{item.key}' 항목의 {', '.join(self.literal[item.key])}이(가) 원문에 그 글자로 없음. 원문 글자 그대로만 옮김")
            band, name, _ = self.band(item.key, thresholds)
            if band == "재추출":
                out.append(f"'{item.key}' 항목의 {name}이(가) 원문과 맞지 않아 보임")
        return out


def run_section(gemini: Any, kind: str, section: C.Section, thresholds: dict[str, float], log: WorkLog,
                target: str, budget: dict[str, int]) -> _Shot | None:
    """한 절을 뽑는다. 값이 의심스러우면 다른 모델로, 그래도 안 되면 상위 모델로 다시 뽑아 더 나은 쪽을 쓴다."""
    best: _Shot | None = None
    for model in (config.MODEL_EXTRACT, config.MODEL_EXTRACT_ALT, config.MODEL_SUMMARY):
        if best is not None and not best.needs_retry(thresholds):
            break
        if model == config.MODEL_SUMMARY:
            if budget.get("상위모델", 0) <= 0:
                break
            budget["상위모델"] -= 1
        stage = "추출" if best is None else "재추출"
        try:
            ex = C.extract(gemini, kind, section, model, best.feedback(thresholds) if best else None)
            got = _Shot(ex, C.judge(gemini, ex, config.MODEL_DECIDE) if ex.items else {}, C.literal_problems(ex))
        except (GeminiError, ValueError, KeyError) as e:
            log.add(stage, target, "보류", f"{kind} 절 호출 실패: {str(e)[:200]}", model=model)
            continue
        if best is None:
            best = got
            log.add("추출", target, "통과", f"{kind} 절({section.first_page}~{section.last_page}쪽): 항목 {len(ex.items)}건" +
                    (f", 형식 문제 {len(ex.problems)}건" if ex.problems else ""), model=model)
            continue
        was, now = best.score(thresholds), got.score(thresholds)
        better = bool(got.ex.items) and (best.empty or now < was)
        log.add("재추출", target, "통과" if better else "반려",
                f"{kind} 절: 틀렸다고 볼 항목 {was[0]}건 → {now[0]}건, 사람이 볼 항목 {was[1]}건 → {now[1]}건. " +
                ("다시 뽑은 값으로 바꿈" if better else "앞선 값을 유지"), model=model, prob=V.worst(got.probs),
                before=f"항목 {len(best.ex.items)}건", after=f"항목 {len(got.ex.items)}건")
        if better:
            best = got
    return best


@dataclass
class Result:
    conditions: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    amounts: dict[str, tuple[float, float]] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    review: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    shots: dict[str, _Shot] = field(default_factory=dict)


KINDS = ("가입나이", "가입한도", "결합제약")


def run(gemini: Any, method_pages: dict[int, str], summary_pages: dict[int, str] | None, targets: list[C.Target],
        now: datetime, thresholds: dict[str, float], budget: dict[str, int] | None = None,
        kinds: tuple[str, ...] = KINDS) -> Result:
    """사업방법서 한 건(과 그 요약서의 자격요건 절)을 처리한다. targets는 이 문서를 함께 쓰는 종형들.

    kinds: 뽑을 절의 종류. 관문전용 종형은 주계약만 두므로 가입나이와 가입한도만 뽑는다(결합제약 절은 모델을 부르지 않는다).
    """
    budget = budget if budget is not None else {"상위모델": 0}
    result = Result()
    # 여러 가입유형을 한 표에 담은 문서(가입최고나이 표)는 대상 종형의 줄 묶음만 남긴다. 그런 표가 없는 문서는 절이 그대로다
    sections = C.method_sections(method_pages, types=[t.variant_name for t in targets])
    anchor = targets[0].variant_id
    logs = {tab: WorkLog(now, tab) for tab in ("sys_가입조건", "sys_결합제약")}

    jobs: list[tuple[str, str, C.Section]] = []
    # 사업방법서에 가입한도 절이 없으면 요약서 자격요건 절의 "가입한도" 항목에서 읽는다
    summary_limits = C.eligibility_limits(summary_pages) if summary_pages and "가입한도" not in sections else None
    for kind in ("가입나이", "가입한도"):
        if kind not in kinds:
            continue
        if kind in sections:
            jobs.append((kind, kind, sections[kind]))
        elif kind == "가입한도" and summary_limits:
            jobs.append((kind, "가입한도(요약서)", summary_limits))
        else:
            result.notes.append(f"사업방법서에서 {kind} 절을 찾지 못함")
    # 제약은 사업방법서의 가입한도·특약부가 절과 요약서의 자격요건 절에 흩어져 있다
    rule_parts = [sections[k] for k in ("가입한도", "특약부가") if k in sections] if "결합제약" in kinds else []
    if rule_parts and all(C.says_none(s) for s in rule_parts):
        # "해당 없음"만 적힌 절은 옮길 것이 없다. 모델을 부르지 않고, 절을 확인했다는 기록만 남긴다
        pages = f"{rule_parts[0].first_page}~{rule_parts[-1].last_page}쪽"
        logs["sys_결합제약"].add("코드대조", f"{anchor}:결합제약(사업방법서)", "통과",
                              f"사업방법서의 의무가입 절({pages})에 '해당 없음'이라고만 적혀 있어 옮길 제약이 없음")
        rule_parts = []
    if rule_parts:
        jobs.append(("결합제약", "결합제약(사업방법서)", C.Section(
            "결합제약", "\n".join(s.text for s in rule_parts), rule_parts[0].first_page, rule_parts[-1].last_page)))
    eligible = C.eligibility_section(summary_pages) if summary_pages and "결합제약" in kinds else None
    if eligible:
        jobs.append(("결합제약", "결합제약(요약서)", C.Section("결합제약", eligible.text, eligible.first_page, eligible.last_page)))

    items: dict[str, list[Any]] = {"가입나이": [], "가입한도": [], "결합제약": []}
    dropped: list[tuple[str, Any, str, str, float]] = []      # (종류, 항목, 절 이름, 칸, 확률)
    status: dict[str, tuple[str, str, float, int]] = {}           # 항목 키 → (구간, 칸, 확률, 쪽)
    for kind, label, section in jobs:
        log = logs[TAB_OF[kind]]
        shot = run_section(gemini, kind, section, thresholds, log, f"{anchor}:{label}", budget)
        if shot is None:
            result.notes.append(f"{label} 절을 뽑지 못함")
            continue
        result.shots[label] = shot
        if shot.empty:
            result.notes.append(f"{label} 절에서 항목을 하나도 뽑지 못함")
        for item in shot.ex.items:
            band, name, low = shot.band(item.key, thresholds)
            if band == "확정" and shot.flawed(item.key):
                band, name = "검토", ", ".join(shot.literal.get(item.key, [])) or name
            # 같은 항목이 두 절(사업방법서와 요약서)에서 나오기도 한다. 한쪽이라도 행으로 만들면 그쪽 판정을 남긴다:
            # 행으로 만든 것들 가운데서는 검토가 확정을 덮고, 재추출은 행으로 만든 쪽의 판정을 덮지 않는다
            old = status.get(item.key)
            if old is None or old[0] == "재추출" or band == "검토":
                status[item.key] = (band, name, low, section.first_page)
            if band != "재추출":          # 다시 뽑아도 재추출 구간인 항목은 행으로 만들지 않는다
                items[kind].append(item)
            else:
                dropped.append((kind, item, label, name, low))
    # 한 절에서는 재추출 구간이었지만 다른 절에서 뽑은 같은 항목으로 행을 만든 것은 "시트에 쓰지 않음"이 아니다
    shadowed = [d for d in dropped if status[d[1].key][0] != "재추출"]
    dropped = [d for d in dropped if status[d[1].key][0] == "재추출"]

    built = C.build_rows(targets, items["가입나이"], items["가입한도"], items["결합제약"])
    result.conditions, result.constraints, result.amounts = built.conditions, built.constraints, built.amounts
    result.notes += built.notes

    # 항목마다 판정 결과를 남긴다. 대상행ID는 그 항목이 만든 첫 행.
    first_row: dict[str, str] = {}
    for row_id, keys in built.origin.items():
        for key in keys:
            first_row.setdefault(key, row_id)
    for kind in items:
        log = logs[TAB_OF[kind]]
        for item in items[kind]:
            band, name, low, page = status[item.key]
            target = first_row.get(item.key, f"{anchor}:{item.key}"[:120])
            if band == "확정":
                log.add("판정", target, "통과", f"{kind}: {item.key}"[:200], model=config.MODEL_DECIDE, prob=low, column=name)
            else:
                log.add("판정", target, "반려" if band == "재추출" else "보류", f"{kind}: {item.key} — {name} 확인 필요"[:300],
                        model=config.MODEL_DECIDE, prob=low, column=name)
                log.add("사람검토이관", target, "보류", f"{kind} {item.key}: {name} 확인 필요 (근거 {page}쪽)"[:300],
                        model=config.MODEL_DECIDE, prob=low, column=name)
                result.review.append(f"- {kind} · {item.key}: {name} {low:.2f} ({page}쪽)")
    for kind, item, label, name, low in shadowed:
        logs[TAB_OF[kind]].add("판정", first_row.get(item.key, f"{anchor}:{item.key}"[:120]), "반려",
                               f"{kind}: {item.key} — {label} 절에서는 원문과 맞지 않아 보임. 다른 절에서 뽑은 같은 항목으로 시트에 씀"[:300],
                               model=config.MODEL_DECIDE, prob=low, column=name)
    for kind, item, _, _, _ in dropped:
        band, name, low, page = status[item.key]
        target = f"{anchor}:{item.key}"[:120]
        logs[TAB_OF[kind]].add("판정", target, "반려", f"{kind}: {item.key} — 다시 뽑아도 원문과 맞지 않아 보여 시트에 쓰지 않음"[:300],
                               model=config.MODEL_DECIDE, prob=low, column=name)
        logs[TAB_OF[kind]].add("사람검토이관", target, "보류", f"{kind} {item.key}: 시트에 쓰지 않음. {name} 확인 필요 (근거 {page}쪽)"[:300],
                               model=config.MODEL_DECIDE, prob=low, column=name)
        result.review.append(f"- {kind} · {item.key}: 시트에 쓰지 않음, {name} {low:.2f} ({page}쪽)")
    result.logs = logs["sys_가입조건"].rows + logs["sys_결합제약"].rows
    bands = [s[0] for s in status.values()]
    result.stats = {"항목": len(bands), "확정": bands.count("확정"), "검토": bands.count("검토"), "제외": bands.count("재추출"),
                    "가입조건 행": len(result.conditions), "결합제약 행": len(result.constraints)}
    return result
