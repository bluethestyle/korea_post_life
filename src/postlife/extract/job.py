"""공시 문서 묶음 하나를 처리해 시트에 반영한다: 종형 → 특약 → 급부 → 가입조건·결합 제약, 그리고 작업 기록.

다시 뽑은 종형의 기존 행만 걷어내고 새 행으로 바꾼다. 뽑지 못한 부분은 기존 행을 그대로 둔다.
급부(상품요약서)와 가입조건(사업방법서)은 따로 돌릴 수 있다.
급부를 다시 뽑을 때는 같은 급부의 이전 급부ID를 잇고, 이번에 제외되거나 처리하지 못한 급부의 이전 확정 줄을 지킨다(rerun.py).
급부를 다시 뽑은 종형마다 그 사실을 작업 기록에 남긴다(rerun.coverage_logs). 검토 대기 표시를 종형마다 가리는 데 쓴다.

관문전용 종형(비교역할구분이 관문전용)은 급부와 가입조건 부분에서 빠지고 "관문" 부분만 처리한다: 종형 행과 주계약 행
(variants.main_row. 모델을 부르지 않는다)을 쓰고, 사업방법서의 가입나이와 가입한도 절(요약서 자격요건 절의 가입한도 포함)에서
주계약 가입조건만 뽑는다(결합제약 절은 뽑지 않는다). 다른 종형의 행은 건드리지 않으므로 parts를 "관문"만 주면 이미 뽑은
급부를 다시 뽑지 않고 관문전용 종형만 시트에 올린다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .. import config, ids
from ..schema import TABS
from ..sheets_io import SheetStore
from ..validate import check_rows
from . import benefits as B
from . import conditions as C
from . import conditions_run, pipeline, variants
from . import rerun as R
from . import verify as V
from .segment import pages_from_text

PARTS = ("급부", "가입조건", "관문")
CONDITION_TABS = ["sys_가입조건", "sys_결합제약"]
BENEFIT_TABS = ["sys_상품종형", "sys_특약", "sys_급부"]      # 급부 추출이 채우는 탭. 보험료예시·급부질병코드는 다른 단계가 채운다
LIMIT_COLUMNS = ("최소가입금액만원", "최대가입금액만원", "합산한도기준키")   # 급부 추출이 채우지 않는 sys_특약의 칸
GATE_TABS = ["sys_상품종형", "sys_특약"]                    # 관문전용 종형의 종형 행과 주계약 행
GATE_KINDS = ("가입나이", "가입한도")                       # 관문전용 종형에서 뽑는 절
_NOT_LISTED = "뽑아 둔 특약 목록에 없어 건너뜀"              # conditions.build_rows가 목록에 없는 특약 이름마다 남기는 주의의 끝


@dataclass
class Report:
    rows: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {
        "sys_상품종형": [], "sys_특약": [], "sys_급부": [], "sys_가입조건": [], "sys_결합제약": []})
    logs: list[dict[str, Any]] = field(default_factory=list)
    done: set[str] = field(default_factory=set)             # 급부까지 처리한 종형ID
    conditions_done: set[str] = field(default_factory=set)  # 가입조건을 처리한 종형ID
    gate_done: set[str] = field(default_factory=set)        # 종형 행과 주계약 행을 쓴 관문전용 종형ID
    gate_conditions_done: set[str] = field(default_factory=set)   # 주계약 가입조건까지 뽑은 관문전용 종형ID
    table: list[str] = field(default_factory=list)          # 요약서별 결과 한 줄
    conditions_table: list[str] = field(default_factory=list)
    gate_table: list[str] = field(default_factory=list)
    review: list[str] = field(default_factory=list)         # 사람이 확인할 줄
    notes: list[str] = field(default_factory=list)
    errors: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    written: bool = False
    write_error: str | None = None
    # 급부를 다시 뽑은 종형의 재추출 전후: 이은 급부ID, 지킨 이전 줄, 내용 기준 잃은 줄과 얻은 줄(scripts/dev/compare_rerun.py와 같은 기준)
    rerun: dict[str, int] = field(default_factory=dict)

    def markdown(self, calls: dict[str, int]) -> str:
        out = ""
        if self.table:
            head = ["| 상품요약서 | 종형 수 | 특약 | 급부 | 확정 | 검토 | 제외 | 재추출 | 상위 모델 |",
                    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
            out += "\n".join(head + self.table) + "\n\n"
        if self.conditions_table:
            head = ["| 사업방법서 | 종형 수 | 항목 | 확정 | 검토 | 제외 | 가입조건 행 | 결합제약 행 |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
            out += "\n".join(head + self.conditions_table) + "\n\n"
        if self.gate_table:
            head = ["| 사업방법서(관문전용) | 종형 수 | 항목 | 확정 | 검토 | 제외 | 가입조건 행 |", "| --- | --- | --- | --- | --- | --- | --- |"]
            out += "\n".join(head + self.gate_table) + "\n\n"
        if self.rerun:
            r = self.rerun
            out += (f"재추출 전후(급부): 시트에 있던 줄 {r['이전 줄']}, 이번 결과 {r['새 줄']}. "
                    f"같은 급부라 이전 급부ID를 이은 줄 {r['이은 급부ID']}, 제외되거나 처리하지 못해 지킨 이전 줄 {r['지킨 이전 줄']}. "
                    f"내용(특약, 지급액, 첫 감액, 면책) 기준으로 잃은 줄 {r['잃은 줄']}, 얻은 줄 {r['얻은 줄']}.\n\n")
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
    관문전용 종형은 "관문" 부분에서만 처리한다(_run_gate). "급부"와 "가입조건" 부분은 관문전용 종형을 보지 않는다.
    """
    report = Report()
    found, problems = variants.build(targets, index)
    report.notes += problems
    if only:
        found = [v for v in found if v.row["공시상품코드"] in only]
    gate = [v for v in found if v.gate_only] if "관문" in parts else []
    found = [v for v in found if not v.gate_only] if ("급부" in parts or "가입조건" in parts) else []
    thresholds = dict(pipeline.DEFAULT_THRESHOLDS)
    if read_thresholds:
        thresholds = pipeline.thresholds_from(store.read(["hum_기준값"])["hum_기준값"])
    budget = {"상위모델": config.EXTRACT_ESCALATIONS_PER_RUN}
    benefits_too = "급부" in parts
    sheet = store.read(["sys_특약", "sys_급부", "sys_상품종형", "sys_작업로그"] if benefits_too else ["sys_특약"])
    existing_riders = sheet["sys_특약"]
    on_sheet = {r["특약ID"]: r for r in existing_riders}
    old_benefits = sheet.get("sys_급부", [])
    pending = (R.pending_benefits(old_benefits, existing_riders, sheet["sys_상품종형"], sheet["sys_작업로그"])
               if benefits_too else set())
    tally = _Tally()
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
            pages = pages_from_text(summary_text)
            result = pipeline.run_summary(gemini, pages, [v.id for v in group], now, thresholds,
                                          years, budget=budget, plain_renewal_years=first.plain_renewal_years,
                                          variant_names={v.id: v.row["종형명"] for v in group})
            if not result.benefits:
                report.logs += result.logs
                report.notes.append(f"{name}: 급부를 뽑지 못해 기존 행을 그대로 둠")
                continue
            riders = result.riders
            for r in riders:          # 급부 추출은 가입 한도를 모른다. 시트에 있던 값을 이어받고, 아래에서 가입조건을 뽑으면 그 값으로 바꾼다
                old = on_sheet.get(r["특약ID"], {})
                r.update({c: old.get(c) for c in LIMIT_COLUMNS if r.get(c) is None})
            # 같은 급부의 이전 ID를 잇고, 이번에 제외되거나 처리하지 못한 급부의 이전 확정 줄을 지킨다
            heads = tuple(f"{v}_T" for v in group_ids)
            new_riders = {r["특약ID"] for r in riders}
            failed, failed_pages = _failed(result, new_riders)
            held, units = _held(result)
            carried = R.carry_over([r for r in old_benefits if str(r["특약ID"]).startswith(heads)], existing_riders,
                                   result.benefits, new_riders, held, failed, pending, now, units, failed_pages)
            R.rename_targets(result.logs, carried.inherited.renamed)
            riders += carried.riders
            tally.add(name, carried)
            empty = sum(1 for part in result.unprocessed if part.reason == "급부 0건")
            if empty:
                report.notes.append(f"{name}: 조각 {empty}개는 급부 0건으로 끝났는데 형식 문제가 남았거나 다시 뽑는 호출이 실패해, "
                                    "모델이 정말 급부가 없다고 본 것인지 알 수 없음. 처리하지 못한 조각으로 보고 이전 줄을 지킴")
            if failed_pages:
                report.notes.append(f"{name}: 처리하지 못한 조각 {sum(map(len, failed_pages.values()))}개는 같은 특약의 다른 조각이 처리돼, "
                                    "그 특약의 이전 줄 가운데 근거 쪽이 그 조각의 첫 쪽인 줄만 지킴")
            report.logs += result.logs + carried.logs + R.coverage_logs(now, [v.id for v in group], name)
            report.rows["sys_상품종형"] += [v.row for v in group]
            report.rows["sys_급부"] += carried.benefits
            report.done |= group_ids
            s = result.stats
            report.table.append(f"| {name} | {len(group)} | {s['처리한 조각']}/{s['조각']} | {s['급부']} | {s['확정']} | {s['검토']} "
                                f"| {s['제외']} | {s['재추출한 조각']} | {s['상위 모델 사용']} |")
            for block in result.blocks:
                unread = {b.label for b in block.extraction.unread}
                for label, status in block.status.items():
                    if status != "확정":
                        _, column, low = V.classify(block.probs.get(label, {}), thresholds)
                        left_out = "시트에 쓰지 않음, " if status == "제외" else ""
                        what = "금액을 읽지 못함" if label in unread else f"{column} {low:.2f}"
                        report.review.append(f"- {name} · {block.extraction.block.rider_name} · {label}: {left_out}{what} "
                                             f"({block.extraction.block.first_page}쪽)")
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

    if gate:
        _run_gate(gemini, report, gate, read_text, on_sheet, now, thresholds, budget)

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
    if report.done:
        heads = tuple(f"{v}_T" for v in report.done)
        tally.finish(report, [r for r in old_benefits if str(r["특약ID"]).startswith(heads)],
                     [r for r in report.rows["sys_급부"] if str(r["특약ID"]).startswith(heads)])
    report.errors = {tab: e for tab, rows in report.rows.items() if (e := check_rows(tab, rows))}
    if report.errors or not (report.done or report.conditions_done or report.gate_done) or dry_run:
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
        if report.gate_done:
            # 관문전용 종형의 종형 행과 주계약 행. 급부, 결합제약, 보험료예시 탭은 건드리지 않는다
            store.replace_variants({t: [r for r in report.rows[t] if r["종형ID"] in report.gate_done] for t in GATE_TABS},
                                   report.gate_done, only=GATE_TABS)
        if report.gate_conditions_done:
            # 가입조건을 뽑지 못한 관문전용 종형은 시트에 있던 가입조건을 그대로 둔다
            store.replace_variants({"sys_가입조건": [r for r in report.rows["sys_가입조건"]
                                                  if r["종형ID"] in report.gate_conditions_done]},
                                   report.gate_conditions_done, only=["sys_가입조건"])
        store.append("sys_작업로그", report.logs)
    except Exception as e:  # noqa: BLE001  뽑은 결과는 호출한 쪽이 파일로 남길 수 있게 돌려준다
        report.write_error = f"{type(e).__name__}: {str(e)[:300]}"
        report.notes.append(f"시트에 쓰지 못함: {report.write_error}")
        return report
    report.written = True
    return report


def _run_gate(gemini: Any, report: Report, gate: list[variants.Variant], read_text: Callable[[str], str | None],
              on_sheet: dict[str, dict[str, Any]], now: datetime, thresholds: dict[str, float], budget: dict[str, int]) -> None:
    """관문전용 종형을 처리한다. 급부를 뽑지 않는다.

    종형 행과 주계약 행(variants.main_row)은 모델 없이 만든다. 주계약 행의 가입 한도는 시트에 있던 값을 잇고, 가입한도를 뽑으면 그 값으로
    바꾼다. 같은 사업방법서를 쓰는 종형끼리 묶어 가입나이와 가입한도 절만 뽑는다(conditions_run.run의 kinds). 대상 종형은 주계약만
    두므로 특약 줄은 행으로 만들지 않고, 특약 이름마다 남는 주의는 한 줄로 줄인다.
    """
    groups: dict[str | None, list[variants.Variant]] = {}
    for v in gate:
        groups.setdefault((v.method or {}).get("해시"), []).append(v)
    for group in groups.values():
        first = group[0]
        name = f"{first.row['공시상품명']}(관문전용)"
        group_ids = {v.id for v in group}
        mains = []
        for v in group:
            main = variants.main_row(v)
            old = on_sheet.get(main["특약ID"], {})
            main.update({c: old.get(c) for c in LIMIT_COLUMNS})
            mains.append(main)
        report.rows["sys_상품종형"] += [v.row for v in group]
        report.rows["sys_특약"] += mains
        report.gate_done |= group_ids
        method_text = read_text(first.method["저장이름"]) if first.method else None
        if not method_text:
            report.notes.append(f"{name}: 사업방법서 글자 파일이 없어 가입조건을 뽑지 않음. 종형 행과 주계약 행만 씀")
            continue
        summary_text = read_text(first.summary["저장이름"]) if first.summary else None
        goals = [C.target_of(v.id, v.row["종형명"], mains) for v in group]
        got = conditions_run.run(gemini, pages_from_text(method_text), pages_from_text(summary_text) if summary_text else None,
                                 goals, now, thresholds, budget, kinds=GATE_KINDS)
        report.logs += got.logs
        skipped = [n for n in got.notes if n.endswith(_NOT_LISTED)]
        report.notes += [f"{name}: {n}" for n in got.notes if not n.endswith(_NOT_LISTED)]
        if skipped:
            report.notes.append(f"{name}: 주계약만 두는 종형이라 특약 {len(skipped)}개의 항목은 행으로 만들지 않음")
        report.review += [f"- {name} · {line[2:]}" for line in got.review]
        if not got.conditions:
            report.notes.append(f"{name}: 가입조건을 뽑지 못해 기존 행을 그대로 둠. 종형 행과 주계약 행만 씀")
            continue
        for main in mains:
            if main["특약ID"] in got.amounts:
                main["최소가입금액만원"], main["최대가입금액만원"] = got.amounts[main["특약ID"]]
        report.rows["sys_가입조건"] += got.conditions
        report.gate_conditions_done |= {r["종형ID"] for r in got.conditions} & group_ids
        missing = [v.row["종형명"] for v in group if v.id not in report.gate_conditions_done]
        if missing:
            report.notes.append(f"{name}: {', '.join(missing)}은(는) 가입조건 행이 나오지 않아 시트에 있던 가입조건을 그대로 둠")
        s = got.stats
        report.gate_table.append(f"| {name} | {len(group)} | {s['항목']} | {s['확정']} | {s['검토']} | {s['제외']} "
                                 f"| {s['가입조건 행']} |")


def _held(result: pipeline.Result) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """(이번에 "제외"로 끝난 항목이 그 조각을 실은 종형마다 냈을 행, 시트에 쓰는 항목마다 {종형ID: 이번에 계산된 급부ID}).

    조각마다 실은 종형은 pipeline.run_summary가 가린 것(BlockResult.variants)을 그대로 쓴다. 금액을 읽지 못한 항목도 제외된 항목이다.
    """
    held: list[dict[str, Any]] = []
    units: list[dict[str, str]] = []
    for done in result.blocks:
        dropped = {label for label, status in done.status.items() if status == "제외"}
        for v in done.variants:
            held += [r for r in B.benefit_rows(v, done.extraction) + B.unread_rows(v, done.extraction) if r["원시급부명"] in dropped]
        if len(done.variants) > 1:
            name = done.extraction.block.rider_name
            units += [{v: ids.benefit_id(ids.rider_id(v, name), b.label) for v in done.variants}
                      for b in done.extraction.benefits if b.label not in dropped]
    return held, units


def _failed(result: pipeline.Result, new_riders: set[str]) -> tuple[set[str], dict[str, set[int]]]:
    """(처리하지 못한 조각의 특약ID, {같은 특약의 다른 조각은 처리된 특약ID: 처리하지 못한 조각의 첫 쪽}).

    처리하지 못한 조각과 그 조각을 실을 종형은 pipeline.run_summary가 남긴다(Result.unprocessed). 이번에 특약 행이 나오지 않은
    특약은 통째로 지키고, 다른 조각에서 특약 행이 나온 특약은 근거 쪽이 그 조각의 첫 쪽인 이전 줄만 지킨다(rerun.carry_over).
    """
    whole: set[str] = set()
    pages: dict[str, set[int]] = {}
    for part in result.unprocessed:
        for v in part.variants:
            rider = ids.rider_id(v, part.block.rider_name)
            if rider in new_riders:
                pages.setdefault(rider, set()).add(part.block.first_page)
            else:
                whole.add(rider)
    return whole, pages


class _Tally:
    """요약서마다의 carry_over 결과를 모아 보고서의 주의와 재추출 전후 요약으로 낸다."""

    def __init__(self) -> None:
        self.linked: list[tuple[dict, dict]] = []
        self.roles: list[tuple[dict, dict]] = []
        self.aligned: list[tuple[dict, dict]] = []
        self.split = 0
        self.kept: list[dict] = []
        self.pending: list[dict] = []
        self.unmatched: list[str] = []

    def add(self, name: str, carried: R.Carried) -> None:
        self.linked += carried.inherited.pairs
        self.roles += carried.inherited.roles
        self.aligned += carried.inherited.aligned
        self.split += carried.inherited.split
        self.kept += carried.kept
        self.pending += carried.pending
        self.unmatched += [f"{name}: {label}" for _, label in carried.unmatched]

    def finish(self, report: Report, old: list[dict], new: list[dict]) -> None:
        lost, gained = R.content_diff(old, new)
        report.rerun = {"이전 줄": len(old), "새 줄": len(new), "이은 급부ID": len(self.linked), "지킨 이전 줄": len(self.kept),
                        "잃은 줄": sum(lost.values()), "얻은 줄": sum(gained.values())}
        if self.linked:
            before, after = self.linked[0]
            report.notes.append(f"급부 {len(self.linked)}줄은 이름의 괄호 안 표기 등이 달라졌지만 같은 급부라 이전 급부ID와 원시급부명을 씀 "
                                f"(예: '{after['원시급부명']}' → '{before['원시급부명']}')")
        if self.roles:
            before, after = self.roles[0]
            report.notes.append(f"이전 급부ID를 이은 줄 가운데 {len(self.roles)}줄은 모델이 정한 급부역할이 이전과 달라짐. 이번 값을 씀 "
                                f"(예: '{before['원시급부명']}': 이전 {before['급부역할']}, 이번 {after['급부역할']})")
        if self.aligned:
            row, fresh = self.aligned[0]
            report.notes.append(f"급부 {len(self.aligned)}줄은 그 종형의 이전 줄과 이어지지 않았지만, 같은 조각을 실은 다른 종형이 이전 "
                                f"급부ID를 이어 같은 꼬리와 원시급부명을 씀. 예전 실행의 판정 기록(첫 종형에만 있음)으로 보는 검토 대기 "
                                f"표시도 옮겨진다 (예: '{fresh['원시급부명']}' → '{row['원시급부명']}', {row['급부ID']})")
        if self.split:
            report.notes.append(f"급부 {self.split}항목은 같은 조각을 실은 종형끼리 이을 이전 급부ID의 꼬리가 갈리거나 맞출 ID가 다른 줄의 것이어서, "
                                "종형끼리 꼬리가 같도록 이전 ID를 잇지 않고 이번에 계산된 ID를 씀. 담보 매핑을 확인 필요")
        if self.kept:
            report.notes.append(f"이번에 제외되거나 처리하지 못한 급부의 이전 확정 줄 {len(self.kept)}줄을 그대로 둠. "
                                f"sys_작업로그에 '재추출 반려'로 남김 (예: {self.kept[0]['원시급부명']}, {self.kept[0]['급부ID']})")
        if self.pending:
            report.notes.append(f"제외되거나 처리하지 못한 급부 가운데 이전 줄이 검토 대기인 {len(self.pending)}줄은 되살리지 않음 "
                                f"(예: {self.pending[0]['원시급부명']})")
        if self.unmatched:
            report.notes.append(f"제외되거나 처리하지 못한 급부 {len(self.unmatched)}건은 이전 줄을 하나로 가리지 못했거나 시트에 그 특약 행이 없어 "
                                f"되살리지 않음 (예: {self.unmatched[0]})")


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
