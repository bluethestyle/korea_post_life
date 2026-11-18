"""공시 문서 묶음 하나를 처리해 시트에 반영한다: 종형 → 특약 → 급부, 그리고 작업 기록.

다시 뽑은 종형의 기존 행만 걷어내고 새 행으로 바꾼다. 급부를 하나도 뽑지 못한 요약서는 기존 행을 그대로 둔다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .. import config
from ..sheets_io import SheetStore
from ..validate import check_rows
from . import pipeline, variants
from . import verify as V
from .segment import pages_from_text


@dataclass
class Report:
    rows: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {"sys_상품종형": [], "sys_특약": [], "sys_급부": []})
    logs: list[dict[str, Any]] = field(default_factory=list)
    done: set[str] = field(default_factory=set)             # 처리한 종형ID
    table: list[str] = field(default_factory=list)          # 요약서별 결과 한 줄
    review: list[str] = field(default_factory=list)         # 사람이 확인할 줄
    notes: list[str] = field(default_factory=list)
    errors: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    written: bool = False

    def markdown(self, calls: dict[str, int]) -> str:
        head = ["| 상품요약서 | 종형 수 | 특약 | 급부 | 확정 | 검토 | 재추출 | 상위 모델 |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        out = "\n".join(head + self.table) + f"\n\n모델별 호출 수: {calls}\n"
        if self.notes:
            out += "\n주의\n" + "\n".join(f"- {n}" for n in self.notes) + "\n"
        if self.review:
            out += "\n사람이 확인할 줄\n" + "\n".join(self.review) + "\n"
        return out


def run(gemini: Any, store: SheetStore, targets: dict[str, Any], index: list[dict[str, Any]],
        read_text: Callable[[str], str | None], now: datetime, only: list[str] | None = None,
        dry_run: bool = False, read_thresholds: bool = True) -> Report:
    """read_text: 공시 수집 결과의 저장이름을 받아 요약서 글자를 돌려준다(없으면 None)."""
    report = Report()
    found, problems = variants.build(targets, index)
    report.notes += problems
    if only:
        found = [v for v in found if v.row["공시상품코드"] in only]
    thresholds = dict(pipeline.DEFAULT_THRESHOLDS)
    if read_thresholds:
        thresholds = pipeline.thresholds_from(store.read(["hum_기준값"])["hum_기준값"])
    budget = {"상위모델": config.EXTRACT_ESCALATIONS_PER_RUN}
    for group in variants.by_summary(found):
        first = group[0]
        name = first.row["공시상품명"]
        text = read_text(first.summary["저장이름"])
        if not text:
            report.notes.append(f"{name}: 요약서 글자 파일이 없어 건너뜀")
            continue
        years = first.row["갱신주기년"] if first.row["갱신유형"] == "갱신" else None
        result = pipeline.run_summary(gemini, pages_from_text(text), [v.id for v in group], now, thresholds, years,
                                      budget=budget)
        report.logs += result.logs
        if not result.benefits:
            report.notes.append(f"{name}: 급부를 뽑지 못해 기존 행을 그대로 둠")
            continue
        report.rows["sys_상품종형"] += [v.row for v in group]
        report.rows["sys_특약"] += result.riders
        report.rows["sys_급부"] += result.benefits
        report.done |= {v.id for v in group}
        s = result.stats
        report.table.append(f"| {name} | {len(group)} | {s['처리한 조각']}/{s['조각']} | {s['급부']} | {s['확정']} | {s['검토']} "
                            f"| {s['재추출한 조각']} | {s['상위 모델 사용']} |")
        for block in result.blocks:
            for label, status in block.status.items():
                if status == "검토":
                    _, column, low = V.classify(block.probs.get(label, {}), thresholds)
                    report.review.append(f"- {name} · {block.extraction.block.rider_name} · {label}: {column} {low:.2f} "
                                         f"({block.extraction.block.first_page}쪽)")

    report.errors = {tab: e for tab, rows in report.rows.items() if (e := check_rows(tab, rows))}
    if report.errors or not report.done or dry_run:
        return report
    store.replace_variants(report.rows, report.done)
    store.append("sys_작업로그", report.logs)
    report.written = True
    return report
