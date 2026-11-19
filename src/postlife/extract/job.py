"""공시 문서 묶음 하나를 처리해 시트에 반영한다: 종형 → 특약 → 급부 → 가입조건·결합 제약, 그리고 작업 기록.

다시 뽑은 종형의 기존 행만 걷어내고 새 행으로 바꾼다. 뽑지 못한 부분은 기존 행을 그대로 둔다.
급부(상품요약서)와 가입조건(사업방법서)은 따로 돌릴 수 있다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .. import config, ids
from ..schema import TABS
from ..sheets_io import SheetStore
from ..validate import check_rows
from . import conditions as C
from . import conditions_run, pipeline, variants
from . import verify as V
from .segment import pages_from_text

PARTS = ("급부", "가입조건")
CONDITION_TABS = ["sys_가입조건", "sys_결합제약"]
BENEFIT_TABS = ["sys_상품종형", "sys_특약", "sys_급부"]      # 급부 추출이 채우는 탭. 보험료예시·급부질병코드는 다른 단계가 채운다
LIMIT_COLUMNS = ("최소가입금액만원", "최대가입금액만원", "합산한도기준키")   # 급부 추출이 채우지 않는 sys_특약의 칸


@dataclass
class Report:
    rows: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {
        "sys_상품종형": [], "sys_특약": [], "sys_급부": [], "sys_가입조건": [], "sys_결합제약": []})
    logs: list[dict[str, Any]] = field(default_factory=list)
    done: set[str] = field(default_factory=set)             # 급부까지 처리한 종형ID
    conditions_done: set[str] = field(default_factory=set)  # 가입조건을 처리한 종형ID
    table: list[str] = field(default_factory=list)          # 요약서별 결과 한 줄
    conditions_table: list[str] = field(default_factory=list)
    review: list[str] = field(default_factory=list)         # 사람이 확인할 줄
    notes: list[str] = field(default_factory=list)
    errors: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    written: bool = False
    write_error: str | None = None

    def markdown(self, calls: dict[str, int]) -> str:
        out = ""
        if self.table:
            head = ["| 상품요약서 | 종형 수 | 특약 | 급부 | 확정 | 검토 | 제외 | 재추출 | 상위 모델 |",
                    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
            out += "\n".join(head + self.table) + "\n\n"
        if self.conditions_table:
            head = ["| 사업방법서 | 종형 수 | 항목 | 확정 | 검토 | 제외 | 가입조건 행 | 결합제약 행 |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
            out += "\n".join(head + self.conditions_table) + "\n\n"
        out += f"모델별 호출 수: {calls}\n"
        if self.notes:
            out += "\n주의\n" + "\n".join(f"- {n}" for n in self.notes) + "\n"
        if self.review:
            out += "\n사람이 확인할 줄\n" + "\n".join(self.review) + "\n"
        return out


def run(gemini: Any, store: SheetStore, targets: dict[str, Any], index: list[dict[str, Any]],
        read_text: Callable[[str], str | None], now: datetime, only: list[str] | None = None,
        dry_run: bool = False, read_thresholds: bool = True, parts: tuple[str, ...] = PARTS) -> Report:
    """read_text: 공시 수집 결과의 저장이름을 받아 문서 글자를 돌려준다(없으면 None).

    parts에 "급부"가 없으면 시트에 있는 특약을 기준으로 가입조건만 다시 뽑는다.
    급부만 다시 뽑거나 가입조건을 뽑지 못했으면, 시트에 있던 같은 특약의 가입 한도를 새 특약 행이 이어받는다.
    """
    report = Report()
    found, problems = variants.build(targets, index)
    report.notes += problems
    if only:
        found = [v for v in found if v.row["공시상품코드"] in only]
    thresholds = dict(pipeline.DEFAULT_THRESHOLDS)
    if read_thresholds:
        thresholds = pipeline.thresholds_from(store.read(["hum_기준값"])["hum_기준값"])
    budget = {"상위모델": config.EXTRACT_ESCALATIONS_PER_RUN}
    existing_riders = store.read(["sys_특약"])["sys_특약"]
    on_sheet = {r["특약ID"]: r for r in existing_riders}
    for v in found:
        if not (v.summary and v.summary.get("해시")):
            report.notes.append(f"{v.row['공시상품코드']} {v.row['종형명']}: 공시 수집 결과에 상품요약서가 없어 건너뜀")

    for group in variants.by_summary(found):
        first = group[0]
        name = first.row["공시상품명"]
        if len({_settings(v) for v in group}) > 1:
            # 한 요약서를 쓰는 종형들은 첫 종형의 갱신 설정과 사업방법서로 함께 처리한다. 설정이 갈리면 사람이 알 수 있게 남긴다
            report.notes.append(f"{name}: 같은 요약서를 쓰는 종형들의 갱신 설정이나 사업방법서가 서로 다름. "
                                f"'{first.row['종형명']}'의 값으로 처리했으니 확인 필요")
        summary_text = read_text(first.summary["저장이름"])
        group_ids = {v.id for v in group}
        riders: list[dict[str, Any]] = []
        if "급부" in parts:
            if not summary_text:
                report.notes.append(f"{name}: 요약서 글자 파일이 없어 건너뜀")
                continue
            years = first.row["갱신주기년"] if first.row["갱신유형"] == "갱신" else None
            result = pipeline.run_summary(gemini, pages_from_text(summary_text), [v.id for v in group], now, thresholds,
                                          years, budget=budget, plain_renewal_years=first.plain_renewal_years,
                                          variant_names={v.id: v.row["종형명"] for v in group})
            report.logs += result.logs
            if not result.benefits:
                report.notes.append(f"{name}: 급부를 뽑지 못해 기존 행을 그대로 둠")
                continue
            riders = result.riders
            for r in riders:          # 급부 추출은 가입 한도를 모른다. 시트에 있던 값을 이어받고, 아래에서 가입조건을 뽑으면 그 값으로 바꾼다
                old = on_sheet.get(r["특약ID"], {})
                r.update({c: old.get(c) for c in LIMIT_COLUMNS if r.get(c) is None})
            report.rows["sys_상품종형"] += [v.row for v in group]
            report.rows["sys_급부"] += result.benefits
            report.done |= group_ids
            s = result.stats
            report.table.append(f"| {name} | {len(group)} | {s['처리한 조각']}/{s['조각']} | {s['급부']} | {s['확정']} | {s['검토']} "
                                f"| {s['제외']} | {s['재추출한 조각']} | {s['상위 모델 사용']} |")
            for block in result.blocks:
                for label, status in block.status.items():
                    if status != "확정":
                        _, column, low = V.classify(block.probs.get(label, {}), thresholds)
                        left_out = "시트에 쓰지 않음, " if status == "제외" else ""
                        report.review.append(f"- {name} · {block.extraction.block.rider_name} · {label}: {left_out}{column} "
                                             f"{low:.2f} ({block.extraction.block.first_page}쪽)")
        else:
            riders = [dict(r) for r in existing_riders if r["종형ID"] in group_ids]
            if not riders:
                report.notes.append(f"{name}: 시트에 특약이 없어 가입조건을 뽑지 않음. 급부부터 뽑아야 함")
                continue

        if "가입조건" in parts:
            method_text = read_text(first.method["저장이름"]) if first.method else None
            if not method_text:
                report.notes.append(f"{name}: 사업방법서 글자 파일이 없어 가입조건을 뽑지 않음")
            else:
                goals = [C.target_of(v.id, v.row["종형명"], riders) for v in group]
                got = conditions_run.run(gemini, pages_from_text(method_text),
                                         pages_from_text(summary_text) if summary_text else None, goals, now, thresholds, budget)
                report.logs += got.logs
                report.notes += [f"{name}: {n}" for n in got.notes]
                report.review += [f"- {name} · {line[2:]}" for line in got.review]
                if got.conditions:
                    for r in riders:
                        if r["특약ID"] in got.amounts:
                            r["최소가입금액만원"], r["최대가입금액만원"] = got.amounts[r["특약ID"]]
                    stale = [r for r in riders if r["특약ID"] not in got.amounts and r["최대가입금액만원"] is not None]
                    if stale:
                        report.notes.append(f"{name}: 특약 {len(stale)}건은 이번에 가입 한도를 읽지 못해 시트에 있던 한도를 그대로 둠 "
                                            f"(예: {stale[0]['원시특약명']})")
                    report.rows["sys_가입조건"] += got.conditions
                    report.rows["sys_결합제약"] += got.constraints
                    report.conditions_done |= group_ids
                    s = got.stats
                    report.conditions_table.append(f"| {name} | {len(group)} | {s['항목']} | {s['확정']} | {s['검토']} | {s['제외']} "
                                                   f"| {s['가입조건 행']} | {s['결합제약 행']} |")
                else:
                    report.notes.append(f"{name}: 가입조건을 뽑지 못해 기존 행을 그대로 둠")
        if "급부" in parts or group_ids & report.conditions_done:
            report.rows["sys_특약"] += riders

    # 같은 ID로 내용까지 같은 행이 두 번 나왔으면 하나만 남긴다. 내용이 다르면 어느 쪽이 맞는지 알 수 없어 아래 검사에서 걸린다.
    for tab in report.rows:
        _drop_repeats(tab, report)
    # 급부·가입조건·제약에서 형식 검사에 걸린 행은 그 행만 빼고 쓴다. 한 줄 때문에 전체를 버리지 않는다.
    key_of = {"sys_급부": "급부ID", "sys_가입조건": "조건행ID", "sys_결합제약": "제약ID"}
    for tab, key in key_of.items():
        bad = check_rows(tab, report.rows[tab])
        if bad:
            report.rows[tab] = [r for r in report.rows[tab] if r[key] not in bad]
            for row_id, reasons in bad.items():
                report.notes.append(f"{tab} {row_id}: 형식 검사에 걸려 쓰지 않음 ({'; '.join(reasons)})")
                report.logs.append({"로그ID": f"LOG_{ids.short_hash(now.isoformat(), tab, row_id, 'drop', length=14)}",
                                    "실행일시": now.isoformat(timespec="seconds"), "작업단계": "코드대조", "대상탭": tab,
                                    "대상행ID": row_id, "대상열": None, "변경전값": None, "변경후값": None, "호출모델": None,
                                    "판정확률": None, "결과": "반려", "사유": f"형식 검사에 걸려 시트에 쓰지 않음: {'; '.join(reasons)}"[:400]})
    report.errors = {tab: e for tab, rows in report.rows.items() if (e := check_rows(tab, rows))}
    if report.errors or not (report.done or report.conditions_done) or dry_run:
        return report
    try:
        if report.done:
            # 급부 추출이 채우는 탭만 바꾼다. 다른 탭까지 넘기면 그 종형의 보험료예시·급부질병코드 행이 빈 목록으로 바뀌어 지워진다
            tabs = BENEFIT_TABS
            store.replace_variants({t: [r for r in report.rows[t] if _variant_of(r, report) in report.done] for t in tabs},
                                   report.done, only=tabs)
        if report.conditions_done:
            tabs = CONDITION_TABS + ([] if "급부" in parts else ["sys_특약"])
            store.replace_variants({t: [r for r in report.rows[t] if r["종형ID"] in report.conditions_done] for t in tabs},
                                   report.conditions_done, only=tabs)
        store.append("sys_작업로그", report.logs)
    except Exception as e:  # noqa: BLE001  뽑은 결과는 호출한 쪽이 파일로 남길 수 있게 돌려준다
        report.write_error = f"{type(e).__name__}: {str(e)[:300]}"
        report.notes.append(f"시트에 쓰지 못함: {report.write_error}")
        return report
    report.written = True
    return report


def _settings(v: variants.Variant) -> tuple[Any, ...]:
    """한 요약서를 쓰는 종형끼리 같아야 하는 값: 갱신 설정과 사업방법서."""
    return (v.row["갱신유형"], v.row["갱신주기년"], v.plain_renewal_years, (v.method or {}).get("해시"))


def _drop_repeats(tab: str, report: Report) -> None:
    key = TABS[tab].key
    first: dict[Any, dict[str, Any]] = {}
    kept: list[dict[str, Any]] = []
    for row in report.rows[tab]:
        if row[key] in first and row == first[row[key]]:
            report.notes.append(f"{tab} {row[key]}: 같은 행이 두 번 나와 하나만 씀")
            continue
        first.setdefault(row[key], row)
        kept.append(row)
    report.rows[tab] = kept


def _variant_of(row: dict[str, Any], report: Report) -> str | None:
    """행이 속한 종형. 급부 행에는 종형ID가 없어 특약을 거쳐 찾는다."""
    if "종형ID" in row:
        return row["종형ID"]
    owner = {r["특약ID"]: r["종형ID"] for r in report.rows["sys_특약"]}
    return owner.get(row.get("특약ID"))
