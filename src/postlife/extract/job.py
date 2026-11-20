"""공시 문서 묶음 하나를 처리해 시트에 반영한다: 종형 → 특약 → 급부 → 가입조건·결합 제약, 그리고 작업 기록.

다시 뽑은 종형의 기존 행만 걷어내고 새 행으로 바꾼다. 뽑지 못한 부분은 기존 행을 그대로 둔다.
급부(상품요약서)와 가입조건(사업방법서)은 따로 돌릴 수 있다.
급부를 다시 뽑을 때는 같은 급부의 이전 급부ID를 잇고, 이번에 제외되거나 처리하지 못한 급부의 이전 확정 줄을 지킨다(rerun.py).
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
from .segment import pages_from_text, rider_blocks, scope_fit, scope_parts

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
            failed, unknown = _failed(result, group_ids, new_riders)
            held, units, unscoped = _held(pages, group, result)
            carried = R.carry_over([r for r in old_benefits if str(r["특약ID"]).startswith(heads)], existing_riders,
                                   result.benefits, new_riders, held, failed, pending, now, units)
            R.rename_targets(result.logs, carried.inherited.renamed)
            riders += carried.riders
            tally.add(name, carried)
            if unknown:
                report.notes.append(f"{name}: 처리하지 못한 조각 {unknown}개는 어느 특약의 것인지 가리지 못해 이전 줄을 지키지 않음")
            if unscoped:
                report.notes.append(f"{name}: 조각 {unscoped}개는 어느 종형에 실렸는지 가리지 못해, 제외된 항목을 요약서를 "
                                    "함께 쓰는 모든 종형의 것으로 보고 이전 줄을 지킴. 종형끼리 급부ID 꼬리도 맞추지 않음")
            report.logs += result.logs + carried.logs
            report.rows["sys_상품종형"] += [v.row for v in group]
            report.rows["sys_급부"] += carried.benefits
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
    if report.done:
        heads = tuple(f"{v}_T" for v in report.done)
        tally.finish(report, [r for r in old_benefits if str(r["특약ID"]).startswith(heads)],
                     [r for r in report.rows["sys_급부"] if str(r["특약ID"]).startswith(heads)])
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


def _scopes(pages: dict[int, str], group: list[variants.Variant], result: pipeline.Result) -> list[list[str] | None]:
    """result.blocks마다 그 조각의 급부가 실린 종형ID. 맞추지 못한 조각은 None.

    조각의 결과에는 어느 종형에 실렸는지가 없다. 가입유형별로 표가 갈린 요약서("[간편가입형]", "[일반가입형]")에서는
    부분마다 실린 종형이 달라서, pipeline.run_summary가 부분마다 종형을 고르는 규칙을 그대로 따라 다시 가린다.
    결과는 처리한 부분만 순서대로 남으므로(호출이 끝내 실패한 부분은 빠진다) 같은 순서로 걸으며 제목, 본문, 첫 쪽으로 맞춘다.
    """
    order = [v.id for v in group]
    names = {v.id: v.row["종형명"] for v in group}
    parts: list[tuple[tuple[str, str, int], list[str]]] = []
    for block in rider_blocks(pages):
        split = scope_parts(block)
        best = {v: max(scope_fit(scope, names[v]) for scope, _ in split) for v in order}
        for scope, text in split:
            matched = [v for v in order if best[v] and scope_fit(scope, names[v]) == best[v]]
            if matched:
                parts.append(((block.title, text if len(split) > 1 else block.text, block.first_page), matched))
    out: list[list[str] | None] = []
    at = 0
    for done in result.blocks:
        b = done.extraction.block
        key = (b.title, b.text, b.first_page)
        found = next((i for i in range(at, len(parts)) if parts[i][0] == key), None)
        if found is None:
            out.append(None)
            continue
        out.append(parts[found][1])
        at = found + 1
    return out


def _held(pages: dict[int, str], group: list[variants.Variant],
          result: pipeline.Result) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    """(이번에 "제외"로 끝난 항목이 그 조각을 실은 종형마다 냈을 행, 시트에 쓰는 항목마다 {종형ID: 이번에 계산된 급부ID},
    어느 종형에 실렸는지 가리지 못한 조각 수).

    가리지 못한 조각은 제외된 항목을 요약서를 함께 쓰는 모든 종형의 것으로 보고, 묶음은 만들지 않는다.
    가린 결과로 셈한 급부 행이 이번 결과의 급부 행과 다르면(있어야 할 행이 없거나 어느 조각에서도 나올 수 없는 행이 있으면)
    가린 것을 믿지 않고 모든 조각을 가리지 못한 것으로 본다.
    """
    order = [v.id for v in group]

    def build(scopes: list[list[str] | None]) -> tuple[list[dict[str, Any]], list[dict[str, str]], set[str]]:
        held: list[dict[str, Any]] = []
        units: list[dict[str, str]] = []
        possible: set[str] = set()          # 가린 결과로 셈한, 이번 결과에 나올 수 있는 급부ID
        for done, matched in zip(result.blocks, scopes):
            dropped = {label for label, status in done.status.items() if status == "제외"}
            rows = {v: B.benefit_rows(v, done.extraction) for v in (matched or order)}
            held += [r for v in rows for r in rows[v] if r["원시급부명"] in dropped]
            possible |= {r["급부ID"] for v in rows for r in rows[v] if r["원시급부명"] not in dropped}
            if matched:
                for i, b in enumerate(done.extraction.benefits):
                    if b.label not in dropped:
                        units.append({v: rows[v][i]["급부ID"] for v in matched})
        return held, units, possible

    scopes = _scopes(pages, group, result)
    held, units, possible = build(scopes)
    written = {r["급부ID"] for r in result.benefits}
    if {fresh for unit in units for fresh in unit.values()} - written or written - possible:
        scopes = [None] * len(result.blocks)
        held, units, _ = build(scopes)
    return held, units, scopes.count(None)


def _failed(result: pipeline.Result, group_ids: set[str], new_riders: set[str]) -> tuple[set[str], int]:
    """(호출이 끝내 실패해 처리하지 못한 조각의 특약ID, 그 가운데 어느 특약인지 가리지 못한 조각 수).

    조각 결과에는 실패한 조각이 남지 않아 작업 기록으로 찾는다. 시도마다 "호출 실패" 기록이 남고, 한 번이라도 성공하면
    "추출 통과" 기록이 남는다. 기록은 그 조각이 실린 첫 종형의 특약ID에 붙으므로, 같은 요약서의 다른 종형 가운데
    이번에 그 특약 행이 나오지 않은 종형에도 넓힌다. 같은 특약의 다른 조각이 처리된 경우는 가리지 못해 수로만 센다.
    """
    tried = {r["대상행ID"] for r in result.logs if str(r.get("사유") or "").startswith("호출 실패")}
    passed = {r["대상행ID"] for r in result.logs if r.get("작업단계") == "추출" and r.get("결과") == "통과"}
    out: set[str] = set()
    for rider in tried - passed:
        for v in group_ids:
            if rider.startswith(f"{v}_T"):
                suffix = rider[len(v):]
                out |= {u + suffix for u in group_ids if u + suffix not in new_riders}
    unknown = result.stats.get("조각", 0) - result.stats.get("처리한 조각", 0) - len(tried - passed)
    return out, max(unknown, 0)


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
                                f"급부ID를 이어 같은 꼬리와 원시급부명을 씀. 판정 기록이 첫 종형에만 남아도 검토 대기 표시가 옮겨진다 "
                                f"(예: '{fresh['원시급부명']}' → '{row['원시급부명']}', {row['급부ID']})")
        if self.split:
            report.notes.append(f"급부 {self.split}항목은 같은 조각을 실은 종형끼리 이을 이전 급부ID의 꼬리가 갈리거나 맞출 ID가 이미 쓰여, "
                                "검토 대기 표시가 옮겨지도록 이전 ID를 잇지 않고 이번에 계산된 ID를 씀. 담보 매핑을 확인 필요")
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
