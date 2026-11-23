"""초기 적재의 두 판독(교차 확인)이 판정을 마친 급부 값을, 판정 모델 없이 시트에 쓴다. 첫 회사는 메리츠화재다.

초기 적재(2026-11-20 결정)는 Gemini API와 판정 모델을 쓰지 않는다. 두 판독자(sonnet, opus)가 표 읽기(extract/tables.py)의
조각을 따로 읽고, 코드가 둘을 견주고 원문과 대조해, 메인 세션이 판정을 마친 값을 값 파일(data/crosscheck/<회사>_<공시상품코드>_
benefits_2reader.jsonl, 꼴은 data/crosscheck/README.md)에 둔다. 이 스크립트는 그 값으로 행을 만든다.

1. 대상 설정과 공시 수집 결과(index.json)로 종형 행을 만든다(variants.build). 종형 행은 모든 종형을 쓴다.
2. 정밀비교 종형마다 상품요약서 PDF에서 표를 다시 읽어 조각을 만든다(tables.py). 같은 요약서를 쓰는 종형은 한 번만 읽는다.
   조각의 형과 종형은 reader_rows.variants_for로 잇는다("공통" 조각은 그 요약서의 모든 정밀비교 종형에 든다).
3. 값 파일의 번호마다 조각 지문(reader_rows.cover_fingerprint)을 다시 읽은 조각과 맞춰 본다. 지문이 다른 줄은 쓰지 않는다.
4. reader_rows.build_rows로 특약 행과 급부 행을 만든다. 원문 구절이 들어가는 열(지급횟수제한, 감액예외)은 조각에서 잘라 쓴다.
   갱신형 특약의 갱신주기년은 대상 설정의 갱신형특약주기년이고, 갱신형특약제외에 적은 특약은 만들지 않는다.
   행없음 줄은 금액 없는 급부 행(지급기준구분 차등지급, 실손보상, 분할지급, 현물급부. 두 금액과 감액은 비움)이 되고,
   그런 급부마다 작업 로그 한 줄(작업단계 추출, 대상열 지급기준구분, 결과 통과)에 판독 사유, 번호, 내용 지문을 남긴다.
5. 쓰지 않는 줄: 판정이 "검토 대기"이거나 빈 줄, 행없음사유가 "그밖"인 행없음 줄(행없음 정보는 결과물 파일에만 둔다), 지문이
   다른 줄, 표 읽기가 이름을 잘못 낸 줄(reader_rows.name_problem의 보류), 기계 검사에 걸린 줄, 갱신형특약제외의 특약에 걸린 줄.
   사유별 수를 요약에 낸다.

관문전용 종형은 종형 행만 쓴다(특약과 급부는 정밀비교 종형에만 쓴다). 시트 쓰기와 작업 로그는 삼성화재 적재
(scripts/load_table_product.py)와 같다: 호출모델은 "교차 확인", 판정확률은 비운다. 쓰는 줄은 모두 판정을 마친 값이라 검토 기록은
남기지 않고, 시트에서 검토 대기였던 급부가 이번에 쓰이면 판정 통과를 남겨 대기 표시를 푼다. 끝에 종형마다 급부를 다시 뽑았다는
기록을 더한다(rerun.coverage_logs). 다시 돌리면 정밀비교 종형의 sys_상품종형, sys_특약, sys_급부 행과 관문전용 종형의 sys_상품종형
행을 새 행으로 바꾼다. sys_특약의 가입 한도(최소가입금액만원, 최대가입금액만원, 합산한도기준키)는 시트에 있던 값을 잇는다.

  python scripts/load_reader_product.py --docs out --result result/extract.json                 # 시트에 쓴다
  python scripts/load_reader_product.py --docs out --dry-run --result r.json --rows rows.json     # 쓰지 않고 행과 요약만 낸다
  python scripts/load_reader_product.py --docs out --snapshot data/snapshot --result r.json       # 사본을 시트 삼아 본다(쓰지 않음)

--docs는 scripts/fetch_disclosure.py --org meritz의 결과 폴더다(index.json과 <저장이름>.pdf). 시트 접속 정보가 없어도
--dry-run은 끝까지 돈다(빈 시트로 본다). --result에는 조각의 문장을 싣지 않는다. --rows(결과물)에는 만들어질 행과 행없음 줄의
정보가 들어가며, 행의 원문 구절 열(지급횟수제한, 감액예외)이 들어 있으므로 리포에 두지 않는다.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from load_table_product import _drop_bad_benefits, snapshot_store  # noqa: E402  스크립트 폴더는 실행할 때 sys.path에 들어 있다
from postlife.extract import job, tables, variants  # noqa: E402
from postlife.extract import reader_rows as RR  # noqa: E402
from postlife.extract import rerun as R  # noqa: E402
from postlife.sheets_io import MemoryBackend, SheetStore  # noqa: E402
from postlife.snapshot import KST  # noqa: E402
from postlife.validate import NO_AMOUNT_BASES, check_rows  # noqa: E402
from postlife.worklog import WorkLog  # noqa: E402

MODEL = "교차 확인"                 # sys_작업로그의 호출모델
READERS = ("sonnet", "opus")
TABS_WRITTEN = job.BENEFIT_TABS
GATE_TABS = ["sys_상품종형"]       # 관문전용 종형은 종형 행만 쓴다
TARGETS = ROOT / "data" / "targets" / "meritz.json"
CROSSCHECK = ROOT / "data" / "crosscheck"

# 쓰지 않은 줄의 사유
WAITING = "검토 대기"
CHANGED = "조각 지문이 다름"
NOT_IN_VALUES = "값 파일에 없음"
NOT_IN_PIECES = "값 파일의 번호가 다시 읽은 조각에 없음"
NO_ROW = "행없음"
EXCLUDED = "20년 갱신주기를 고를 수 없는 갱신형 특약"
NO_YEARS = "갱신주기년이 없는 갱신형 특약"


@dataclass
class Group:
    """같은 상품요약서를 쓰는 정밀비교 종형들과 그 요약서에서 다시 읽은 조각."""
    code: str                                   # 값 파일의 공시상품코드
    variants: list[variants.Variant]
    pieces: list[RR.PieceView] = field(default_factory=list)
    used: list[str] = field(default_factory=list)          # 정밀비교 종형 하나 이상에 드는 조각의 세부보장 번호(차례대로)
    reasons: dict[str, str] = field(default_factory=dict)  # 번호 → 쓰지 않은 사유
    written: set[str] = field(default_factory=set)         # 급부 행이 된 번호


@dataclass
class Loaded(job.Report):
    counts: dict[str, dict[str, Any]] = field(default_factory=dict)      # 종형ID → 줄 수
    groups: list[Group] = field(default_factory=list)
    no_rows: dict[str, dict[str, Any]] = field(default_factory=dict)     # "공시상품코드 번호" → 행없음 정보
    excluded: dict[str, list[str]] = field(default_factory=dict)         # 공시상품코드 → 갱신형특약제외로 뺀 특약명
    clashes: dict[str, list[str]] = field(default_factory=dict)          # 탭 → 겹친 ID
    dropped: dict[str, int] = field(default_factory=dict)                # 탭 → 시트에 있었는데 이번에 빠지는 행 수
    gate_done: set[str] = field(default_factory=set)
    no_amount: dict[str, str] = field(default_factory=dict)              # 금액 없는 급부ID → 작업 로그 사유(판독 사유, 번호, 내용 지문)


def value_lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_pieces(pdf: Path, layout: tables.Layout) -> tuple[list[RR.PieceView], dict[int, str]]:
    """요약서 PDF에서 급부 표를 다시 읽어 조각(번호는 조각 파일의 순번)과 쪽 글자를 돌려준다. scripts/dump_tables.py와 같은 길이다."""
    pages = tables.page_texts(pdf)
    found = tables.benefit_pages(pages, None, layout)
    read = tables.read_tables(pdf, found.first_page, found.last_page, layout)
    riders = tables.riders_from_tables(read, layout)
    data = tables.riders_to_json(riders, {"문서": pdf.stem, "쪽": [found.first_page, found.last_page]},
                                 tables.table_notes(read, layout))
    return RR.load_pieces(data), pages


def renewal_years(pieces: Sequence[RR.PieceView], years: int | None, excluded: Sequence[str]) -> dict[str, int]:
    """조각의 갱신형 특약 이름마다 갱신주기년. 갱신형특약제외에 적은 특약(빈칸 무시)과 주기가 없으면 넣지 않는다."""
    banned = {RR._squash(n) for n in excluded}
    out = {}
    for p in pieces:
        for name in p.names or (p.title,):
            if RR.is_renewal(name) and years is not None and RR._squash(name) not in banned:
                out[name] = years
    return out


def products_of(targets: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    """(공시상품코드, 종형명) → 그 종형이 든 상품 설정."""
    return {(v["공시상품코드"], v["종형명"]): product for product in targets["상품"] for v in product["종형"]}


def check_values(group: Group, lines: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """값 파일을 다시 읽은 조각과 맞춰 보고 행 만들기에 넣을 판정 값을 고른다. 쓰지 않을 줄은 group.reasons에 사유를 남긴다."""
    found = RR.covers_by_number(group.pieces)
    used = set(group.used)
    by_number = {line["번호"]: line for line in lines}
    for n in group.used:
        if n not in by_number:
            group.reasons[n] = NOT_IN_VALUES
    for n, line in by_number.items():
        if n not in found:
            group.reasons[n] = NOT_IN_PIECES
        elif n in used and RR.cover_fingerprint(*found[n]) != line.get("조각지문"):
            group.reasons[n] = CHANGED
    readings = RR.final_readings(lines, *READERS)
    for n, line in by_number.items():
        if n in used and n not in group.reasons and n not in readings:
            group.reasons[n] = WAITING
    return {n: v for n, v in readings.items() if n in used and n not in group.reasons}


def load(store: SheetStore, targets: dict[str, Any], index: list[dict[str, Any]], docs: Path,
         values: Mapping[str, Path], now: datetime, dry_run: bool = False, only: Sequence[str] | None = None,
         layout: tables.Layout = tables.MERITZ) -> Loaded:
    """values: {공시상품코드: 값 파일}. 같은 요약서를 쓰는 종형들은 그 가운데 값 파일이 있는 코드의 값 파일을 쓴다.

    급부 행의 형식 오류는 그 행만 빼고 쓴다. 상품종형이나 특약에 형식 오류나 ID 겹침이 남거나 dry_run이면 쓰지 않는다.
    """
    report = Loaded()
    found, problems = variants.build(targets, index)
    report.notes += problems
    if only:
        found = [v for v in found if v.row["공시상품코드"] in only]
    product = products_of(targets)
    sheet = store.read(["sys_특약", "sys_급부", "sys_상품종형", "sys_작업로그"])
    on_sheet = {r["특약ID"]: r for r in sheet["sys_특약"]}

    precise = [v for v in found if not v.gate_only]
    for v in found:
        if v.gate_only:
            report.rows["sys_상품종형"].append(v.row)
            report.gate_done.add(v.id)
    shared: dict[str, list[variants.Variant]] = {}
    for v in precise:
        if not (v.summary and v.summary.get("해시")):
            report.notes.append(f"{v.row['공시상품코드']} {v.row['종형명']}: 공시 수집 결과에 상품요약서가 없어 건너뜀")
            continue
        shared.setdefault(v.summary["해시"], []).append(v)

    for group_variants in shared.values():
        codes = list(dict.fromkeys(v.row["공시상품코드"] for v in group_variants))
        same_file = [e["상품코드"] for e in index if e.get("해시") == group_variants[0].summary["해시"]]
        code = next((c for c in codes + same_file if c in values and values[c].exists()), None)
        first = group_variants[0]
        if code is None:
            report.notes.append(f"{', '.join(codes)}: 값 파일이 없어 급부를 쓰지 않음")
            continue
        pdf = docs / f"{first.summary['저장이름']}.pdf"
        if not pdf.exists():
            report.notes.append(f"{', '.join(codes)}: 상품요약서 PDF({pdf.name})가 없어 급부를 쓰지 않음")
            continue
        group = Group(code, group_variants)
        group.pieces, pages = read_pieces(pdf, layout)
        names = [v.row["종형명"] for v in group_variants]
        members = {p.index: RR.variants_for(p.segment, names, layout.common) for p in group.pieces}
        group.used = [c.number for p in group.pieces if members[p.index] for c in p.covers]
        readings = check_values(group, value_lines(values[code]))
        report.groups.append(group)
        for v in group_variants:
            mine = [p for p in group.pieces if v.row["종형명"] in members[p.index]]
            settings = product[(v.row["공시상품코드"], v.row["종형명"])]
            banned = [x["특약명"] for x in settings.get("갱신형특약제외") or []]
            built = RR.build_rows(v.id, mine, readings, renewal_years(mine, v.plain_renewal_years, banned), pages)
            for r in built.riders:          # 표는 가입 한도를 모른다. 시트에 있던 값을 잇는다(job.run과 같다)
                old = on_sheet.get(r["특약ID"], {})
                r.update({c: old.get(c) for c in job.LIMIT_COLUMNS if r.get(c) is None})
            report.rows["sys_상품종형"].append(v.row)
            report.rows["sys_특약"] += built.riders
            report.rows["sys_급부"] += built.benefits
            report.no_amount.update(no_amount_reasons(built, readings, mine))
            report.done.add(v.id)
            _account(report, group, v, mine, built, banned)

    # 같은 ID로 내용까지 같은 행은 하나만 남긴다. 형식 검사보다 먼저 해야 한다. 그러지 않으면 기본키 중복으로 둘 다 빠진다
    for tab in TABS_WRITTEN:
        job._drop_repeats(tab, report)
    report.clashes = {tab: sorted(k for k, n in collections.Counter(r[key] for r in report.rows[tab]).items() if n > 1)
                      for tab, key in (("sys_상품종형", "종형ID"), ("sys_특약", "특약ID"), ("sys_급부", "급부ID"))}
    report.clashes = {t: ids for t, ids in report.clashes.items() if ids}
    _drop_bad_benefits(report, now)

    log = WorkLog(now, "sys_급부")
    for b in report.rows["sys_급부"]:       # 금액 없는 급부: 판독의 세부 사유는 시트 값이 아니라 이 기록에 남긴다
        if b["급부ID"] in report.no_amount and b.get("지급기준구분") in NO_AMOUNT_BASES:
            log.add("추출", b["급부ID"], "통과", report.no_amount[b["급부ID"]], model=MODEL, column=NO_AMOUNT_COLUMN,
                    after=b["지급기준구분"])
    by_name: dict[str, list[str]] = {}
    for g in report.groups:
        for v in g.variants:
            by_name.setdefault(v.row["공시상품명"], []).append(v.id)
    coverage = [row for name, vids in by_name.items() for row in R.coverage_logs(now, vids, name)]
    # 쓴 뒤의 시트에서 검토 대기로 보일 줄(시트에서 검토 대기였던 줄 따위)에 판정 통과를 남긴다. 화면과 재추출은 가장 나중 실행만 본다
    touched = report.done | report.gate_done
    after = [r for r in sheet["sys_상품종형"] if r["종형ID"] not in touched] + report.rows["sys_상품종형"]
    waiting = R.pending_benefits(report.rows["sys_급부"], report.rows["sys_특약"], after, sheet["sys_작업로그"] + coverage)
    for bid in sorted(waiting):
        log.add("판정", bid, "통과", "교차 확인: 두 판독이 같거나 원문 대조로 판정을 마친 값. 앞선 검토 대기를 풂", model=MODEL)
    report.logs += log.rows + coverage

    old_riders = {r["특약ID"] for r in sheet["sys_특약"] if r["종형ID"] in report.done}
    new_ids = {tab: {r[key] for r in report.rows[tab]} for tab, key in (("sys_특약", "특약ID"), ("sys_급부", "급부ID"))}
    report.dropped = {"sys_특약": len(old_riders - new_ids["sys_특약"]),
                      "sys_급부": len({r["급부ID"] for r in sheet["sys_급부"] if r["특약ID"] in old_riders} - new_ids["sys_급부"])}

    report.errors = {tab: e for tab in TABS_WRITTEN if (e := check_rows(tab, report.rows[tab]))}
    if report.clashes:
        report.notes.append(f"ID 겹침이 있어 쓰지 않음: {report.clashes}")
    if report.errors or report.clashes or not (report.done or report.gate_done) or dry_run:
        return report
    try:
        if report.done:
            store.replace_variants({t: [r for r in report.rows[t] if _variant_of(r, report) in report.done]
                                    for t in TABS_WRITTEN}, report.done, only=TABS_WRITTEN)
        if report.gate_done:
            store.replace_variants({"sys_상품종형": [r for r in report.rows["sys_상품종형"] if r["종형ID"] in report.gate_done]},
                                   report.gate_done, only=GATE_TABS)
        store.append("sys_작업로그", report.logs)
    except Exception as e:  # noqa: BLE001  읽은 결과는 호출한 쪽이 파일로 남길 수 있게 돌려준다
        report.write_error = f"{type(e).__name__}: {str(e)[:300]}"
        report.notes.append(f"시트에 쓰지 못함: {report.write_error}")
        return report
    report.written = True
    return report


NO_AMOUNT_COLUMN = "지급기준구분"


def no_amount_reasons(built: RR.Built, readings: Mapping[str, Mapping[str, Any]],
                      pieces: Sequence[RR.PieceView]) -> dict[str, str]:
    """금액 없는 급부ID → 작업 로그 사유. "판독 사유 회차별지급률, 번호 R012-3, 내용 지문 a1b2c3d4e5f6" 꼴이다.

    급부 하나에 번호가 여럿(이름과 값이 같은 줄)이면 번호마다 이어 적는다. 원문 글자는 싣지 않는다(지문만).
    """
    covers = RR.covers_by_number(pieces)
    out = {}
    for b in built.benefits:
        if b.get("지급기준구분") not in NO_AMOUNT_BASES:
            continue
        parts = []
        for n in built.numbers.get(b["급부ID"], ()):
            kind = (readings.get(n) or {}).get("행없음사유") or ""
            mark = RR.content_fingerprint(covers[n][1]) if n in covers else ""
            parts.append(f"판독 사유 {kind}, 번호 {n}, 내용 지문 {mark}")
        out[b["급부ID"]] = "; ".join(parts)
    return out


def _variant_of(row: Mapping[str, Any], report: Loaded) -> str | None:
    if "종형ID" in row:
        return row["종형ID"]
    owner = {r["특약ID"]: r["종형ID"] for r in report.rows["sys_특약"]}
    return owner.get(row.get("특약ID"))


def _account(report: Loaded, group: Group, v: variants.Variant, pieces: Sequence[RR.PieceView], built: RR.Built,
             banned: Sequence[str]) -> None:
    """한 종형의 행 수와, 그 요약서에서 쓰지 않은 줄의 사유. 사유는 줄마다 하나다(앞서 남긴 사유가 먼저다)."""
    written = {n for nums in built.numbers.values() for n in nums}
    group.written |= written
    banned_keys = {RR._squash(n) for n in banned}
    excluded = [n for n in built.skipped_riders if RR._squash(n) in banned_keys]
    if excluded:
        report.excluded.setdefault(group.code, [])
        report.excluded[group.code] += [n for n in excluded if n not in report.excluded[group.code]]
    for p in pieces:
        names = p.names or (p.title,)
        for c in p.covers:
            n = c.number
            if n in group.reasons or n in written:
                continue
            if n in built.skipped:
                why = built.skipped[n]
                group.reasons[n] = NO_ROW if why.startswith("스키마가 담지 못하는 꼴") else why
            elif all(name in built.skipped_riders for name in names):
                group.reasons[n] = EXCLUDED if all(RR._squash(x) in banned_keys for x in names) else NO_YEARS
    for n, info in built.no_rows.items():
        report.no_rows[f"{group.code} {n}"] = info
    report.counts[v.id] = {"공시상품코드": v.row["공시상품코드"], "종형명": v.row["종형명"], "특약": len(built.riders),
                           "급부": len(built.benefits), "갱신형특약제외": len(excluded)}


def reason_counts(group: Group) -> collections.Counter:
    """쓰지 않은 줄의 사유별 수. 급부 행이 된 줄(같은 줄이 다른 특약 이름으로는 행이 된 경우)은 세지 않는다."""
    kinds = collections.Counter()
    used = set(group.used)
    for n, why in group.reasons.items():
        if n in group.written or n not in used:
            continue
        kinds[why.split(":", 1)[0].split("(", 1)[0].strip()] += 1
    return kinds


def no_amount_counts(report: Loaded) -> collections.Counter:
    """쓸 급부 행 가운데 금액 없는 급부(지급기준구분이 차등지급, 실손보상, 분할지급, 현물급부)의 값별 수."""
    return collections.Counter(r["지급기준구분"] for r in report.rows["sys_급부"] if r.get("지급기준구분") in NO_AMOUNT_BASES)


def markdown(report: Loaded) -> str:
    """실행 요약. 조각의 문장은 싣지 않는다."""
    head = ["| 공시상품코드 | 종형명 | 특약 | 급부 |", "| --- | --- | --- | --- |"]
    rows = [f"| {c['공시상품코드']} | {c['종형명']} | {c['특약']} | {c['급부']} |" for c in report.counts.values()]
    total = {k: sum(c[k] for c in report.counts.values()) for k in ("특약", "급부")}
    rows.append(f"| 합계 | 정밀비교 종형 {len(report.counts)} | {total['특약']} | {total['급부']} |")
    out = f"종형 행 {len(report.rows['sys_상품종형'])} (정밀비교 {len(report.done)}, 관문전용 {len(report.gate_done)})\n\n"
    out += "\n".join(head + rows) + "\n\n"
    for g in report.groups:
        kinds = reason_counts(g)
        out += (f"{g.code} 요약서: 정밀비교 종형에 드는 세부보장 {len(g.used)}줄, 급부 행이 된 줄 {len(g.written & set(g.used))}, "
                f"쓰지 않은 줄 {sum(kinds.values())}\n")
        out += "".join(f"- {k}: {n}\n" for k, n in kinds.most_common())
        held = sorted((n for n, why in g.reasons.items() if why.startswith(RR.HOLD) and n not in g.written), key=RR._order)
        if held:
            out += f"- 보류한 줄: {', '.join(held)}\n"
        if report.excluded.get(g.code):
            out += f"- 갱신형특약제외로 뺀 특약 {len(report.excluded[g.code])}개\n"
        out += "\n"
    bases = no_amount_counts(report)
    if bases:
        out += (f"금액 없는 급부(행없음 줄이 된 행): {sum(bases.values())}행 ("
                + ", ".join(f"{k} {n}" for k, n in bases.most_common()) + ")\n")
    out += f"ID 겹침: {report.clashes or '없음'}\n"
    out += f"형식 오류: {sum(len(e) for e in report.errors.values()) if report.errors else 0}행\n"
    out += f"시트에 있었는데 이번에 빠지는 행: 특약 {report.dropped.get('sys_특약', 0)}, 급부 {report.dropped.get('sys_급부', 0)}\n"
    out += f"작업 기록: {len(report.logs)}행 (호출모델 '{MODEL}')\n"
    if report.notes:
        out += "\n주의\n" + "\n".join(f"- {n}" for n in report.notes) + "\n"
    return out


def result_of(report: Loaded) -> dict[str, Any]:
    """--result 파일. 조각의 문장은 싣지 않는다(번호, 수, 사유의 앞머리만)."""
    return {
        "종형": report.counts,
        "종형 행": len(report.rows["sys_상품종형"]), "관문전용 종형": sorted(report.gate_done),
        "쓰지 않은 줄": {g.code: dict(reason_counts(g)) for g in report.groups},
        "쓰지 않은 줄 번호": {g.code: {n: why.split(":", 1)[0] for n, why in sorted(g.reasons.items(), key=lambda x: RR._order(x[0]))
                                     if n not in g.written and n in set(g.used)} for g in report.groups},
        "금액 없는 급부": dict(no_amount_counts(report).most_common()),
        "갱신형특약제외": report.excluded, "ID 겹침": report.clashes, "형식 오류": report.errors,
        "시트에서 빠지는 행": report.dropped, "주의": report.notes, "기록 행 수": len(report.logs), "시트에 씀": report.written,
    }


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--docs", type=Path, required=True, help="fetch_disclosure.py의 결과 폴더(index.json과 요약서 PDF)")
    p.add_argument("--targets", type=Path, default=TARGETS)
    p.add_argument("--values", action="append", default=[], metavar="코드=경로",
                   help="공시상품코드의 값 파일. 비우면 data/crosscheck/<회사>_<코드>_benefits_2reader.jsonl")
    p.add_argument("--org", default=tables.MERITZ.name, choices=sorted(tables.LAYOUTS), help="요약서 급부 표의 꼴(회사)")
    p.add_argument("--only", action="extend", nargs="+", help="이 공시상품코드의 종형만 처리")
    p.add_argument("--dry-run", action="store_true", help="시트에 쓰지 않는다")
    p.add_argument("--snapshot", type=Path, help="시트 대신 이 사본 폴더를 읽는다. 시트에 쓰지 않는다")
    p.add_argument("--result", type=Path, help="종형별 줄 수와 쓰지 않은 줄의 사유를 JSON으로 남길 경로")
    p.add_argument("--rows", type=Path, help="만들어질 행과 행없음 줄의 정보를 JSON으로 남길 경로(원문 구절 열이 들어 있음)")
    return p.parse_args(argv)


def default_values(org: str, index: list[dict[str, Any]]) -> dict[str, Path]:
    codes = {e["상품코드"] for e in index}
    return {c: CROSSCHECK / f"{org}_{c}_benefits_2reader.jsonl" for c in sorted(codes)}


def main(argv: list[str] | None = None) -> int:
    args = parse(argv)
    dry_run = args.dry_run or bool(args.snapshot)
    if args.snapshot:
        store = snapshot_store(args.snapshot)
    else:
        has_sheet = bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") and os.environ.get("SPREADSHEET_ID"))
        if not has_sheet and not dry_run:
            print("시트 접속 정보가 없어 건너뜁니다. 흐름만 보려면 --dry-run이나 --snapshot을 붙이세요.")
            return 0
        if has_sheet:
            from postlife.sheets_io import RestBackend

            store = SheetStore(RestBackend.from_env())
        else:
            store = SheetStore(MemoryBackend())
    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    index = json.loads((args.docs / "index.json").read_text(encoding="utf-8"))
    values = default_values(args.org, index)
    for item in args.values:
        code, _, path = item.partition("=")
        values[code] = Path(path)
    report = load(store, targets, index, args.docs, values, datetime.now(KST), dry_run=dry_run, only=args.only,
                  layout=tables.LAYOUTS[args.org])

    text = markdown(report)
    print(text)
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result_of(report), ensure_ascii=False, indent=1), encoding="utf-8")
    if args.rows:
        args.rows.parent.mkdir(parents=True, exist_ok=True)
        args.rows.write_text(json.dumps({"행": report.rows, "작업로그": report.logs, "행없음": report.no_rows},
                                        ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 두 판독 급부 적재 (교차 확인)\n\n" + text)
    if report.write_error:
        print("시트에 쓰지 못했습니다:", report.write_error)
        return 1
    if report.errors or report.clashes:
        print("형식 검사나 ID 겹침에 걸려 시트에 쓰지 않았습니다:",
              json.dumps({"형식": report.errors, "겹침": report.clashes}, ensure_ascii=False)[:2000])
        return 1
    if not (report.done or report.gate_done):
        print("처리한 종형이 없습니다.")
        return 1
    if report.written:
        rows = report.rows
        print(f"시트에 씀: 종형 {len(rows['sys_상품종형'])}, 특약 {len(rows['sys_특약'])}, 급부 {len(rows['sys_급부'])}, "
              f"기록 {len(report.logs)}행")
    else:
        print("시트에 쓰지 않았습니다(--dry-run 또는 --snapshot).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
