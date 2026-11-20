"""급부 표의 문구가 규칙적인 요약서(삼성화재)에서 표 규칙으로 읽은 급부를, 판정 모델 없이 교차 확인만으로 시트에 쓴다.

기존 상품의 초기 적재에 쓴다(2026-11-20 결정). 서로 다른 두 판독이 같으면 확정한다.
- 첫째 판독: 표 추출기(src/postlife/extract/tables.py)가 만든 조각을 문구 규칙(src/postlife/extract/table_rules.py)으로 읽은 값.
- 둘째 판독: 제미나이가 같은 표를 따로 구조화한 대조 자료(data/crosscheck/samsungfire_*_benefits_gemini.jsonl).
규칙이 확신하고(확신 없음 사유가 없고) 대조 자료와 지급률, 감액, 면책, 대상 나눔이 같으면 확정이다. 지급 한도 문구만 다른 줄도
확정으로 본다. 대조 자료는 한도를 줄여 적거나 "※" 문장의 한도를 적지 않기도 한다(data/crosscheck/README.md).
그 밖의 줄(확신 없음, 대조 자료와 다름, 대조 자료에 번호 없음)은 검토로 두되 시트에는 쓴다.

검토 줄은 급부ID마다 sys_작업로그에 판정 보류와 사람검토이관 보류를 남겨 화면과 재추출이 검토 대기로 본다.
호출모델은 "교차 확인"이고 판정확률은 비운다. 확정 줄은 기록하지 않는다(화면 파일 크기 한도 때문이다). 다만 시트에서
검토 대기였던 급부가 이번에 확정되면 판정 통과를 남겨 대기 표시를 푼다. 끝에 종형마다 급부를 다시 뽑았다는 기록을 더한다
(rerun.coverage_logs).

다시 돌리면 그 종형의 sys_상품종형, sys_특약, sys_급부 행을 새 행으로 바꾼다. sys_특약의 가입 한도(최소가입금액만원,
최대가입금액만원, 합산한도기준키)는 시트에 있던 값을 잇는다. 보험료예시, 급부질병코드, 가입조건, 결합제약 탭은 건드리지 않는다.

  python scripts/load_table_product.py --docs out --result result/extract.json             # 시트에 쓴다
  python scripts/load_table_product.py --docs out --dry-run --result result/extract.json   # 쓰지 않고 흐름만 본다
  python scripts/load_table_product.py --docs out --snapshot data/snapshot --result r.json # 접속 정보 없이 사본을 시트 삼아 본다(쓰지 않음)

--docs는 scripts/fetch_disclosure.py --org samsungfire의 결과 폴더다(index.json과 samsungfire_<공시상품코드>_급부표.json).
결과 파일과 실행 요약에는 표 조각의 문장을 싣지 않는다. 종형별 줄 수, 형식 오류, 급부ID마다의 판정과 사유만 싣는다.
사유에는 규칙의 확신 없음 문구와 대조 차이 문구가 들어간다.
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
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import compare_table_rules as compare  # noqa: E402  스크립트 폴더는 실행할 때 sys.path에 들어 있다
from postlife import ids  # noqa: E402
from postlife.extract import job, table_rules, tables, variants  # noqa: E402
from postlife.extract import rerun as R  # noqa: E402
from postlife.extract.table_rules import Reading  # noqa: E402
from postlife.schema import TABS  # noqa: E402
from postlife.sheets_io import MemoryBackend, SheetStore, rows_to_values  # noqa: E402
from postlife.snapshot import KST, read_snapshot  # noqa: E402
from postlife.validate import check_rows  # noqa: E402
from postlife.worklog import WorkLog  # noqa: E402

MODEL = "교차 확인"                 # sys_작업로그의 호출모델
# 검토 줄의 대상열. 화면(src/postlife/site/model.py의 VERDICT_COLUMNS)은 이 열이 검토 대기이면 우열 판정을 미룬다
COLUMNS = "기준지급금액만원, 감액개월1, 면책기간일수"
NO_NUMBER = "대조 자료에 번호 없음"
CONFIRMED, REVIEW = "확정", "검토"
TABS_WRITTEN = job.BENEFIT_TABS
TARGETS = ROOT / "data" / "targets" / "samsungfire.json"
# 공시상품코드 → 대조 자료. 번호는 표 추출기가 그 코드의 요약서에서 낸 조각 순번과 세부보장 순번이다
CROSSCHECK = {
    "ZPB446030": ROOT / "data" / "crosscheck" / "samsungfire_fit8_benefits_gemini.jsonl",      # THE FIT 파트너 8종
    "ZPB357050": ROOT / "data" / "crosscheck" / "samsungfire_refresh_benefits_gemini.jsonl",   # 새로고침 7종
    "ZPB358050": ROOT / "data" / "crosscheck" / "samsungfire_refresh8_benefits_gemini.jsonl",  # 새로고침 8종
}


@dataclass
class Loaded(job.Report):
    # 급부ID → {"번호", "상태", "사유"}. 번호는 대조한 번호를 쉼표로 이은 것이다(보통 하나)
    verdicts: dict[str, dict[str, Any]] = field(default_factory=dict)
    counts: dict[str, dict[str, Any]] = field(default_factory=dict)     # 종형ID → 줄 수


def reasons_of(doubts: Sequence[str], lines: list[Reading] | None, other: list[str] | None) -> list[str]:
    """급부 줄 하나를 검토로 둘 사유. 비어 있으면 확정이다.

    doubts: 규칙의 확신 없음 사유. lines: 그 세부보장에서 규칙이 읽은 줄 모두(대상별로 나눈 줄 포함).
    other: 대조 자료의 그 번호 줄(compare_table_rules.load_table의 값). 없으면 None.
    대조 차이(compare_table_rules.differences) 가운데 지급 한도("한도:")는 사유로 치지 않는다.
    """
    out = list(doubts)
    if lines is None or other is None:
        out.append(NO_NUMBER)
    else:
        out += [d for d in compare.differences(lines, other) if not d.startswith("한도:")]
    return out


def load(store: SheetStore, targets: dict[str, Any], index: list[dict[str, Any]], docs: Path,
         crosscheck: dict[str, dict[str, list[str]]], now: datetime, dry_run: bool = False,
         only: Sequence[str] | None = None) -> Loaded:
    """종형마다 표 조각을 규칙으로 읽고 교차 확인으로 판정해 시트에 쓴다.

    crosscheck: {공시상품코드: {번호: 대조 줄}}. 대조 자료가 없는 코드는 모든 줄이 검토다.
    급부 행의 형식 오류는 그 행만 빼고 쓴다. 상품종형이나 특약에 형식 오류가 남거나 dry_run이면 쓰지 않는다.
    """
    report = Loaded()
    found, problems = variants.build(targets, index)
    report.notes += problems
    if only:
        found = [v for v in found if v.row["공시상품코드"] in only]
    sheet = store.read(["sys_특약", "sys_급부", "sys_상품종형", "sys_작업로그"])
    on_sheet = {r["특약ID"]: r for r in sheet["sys_특약"]}
    pieces: dict[str, list[tables.Rider]] = {}
    lines_of: dict[str, dict[str, list[Reading]]] = {}          # 공시상품코드 → {번호: 규칙이 읽은 줄}
    made: dict[str, tuple[variants.Variant, table_rules.Outcome]] = {}
    for v in found:
        code = v.row["공시상품코드"]
        piece = (v.summary or {}).get("급부표")
        if not piece or not (docs / piece).exists():
            report.notes.append(f"{code} {v.row['종형명']}: 급부 표 조각 파일이 없어 건너뜀")
            continue
        if code not in pieces:
            pieces[code] = tables.read_riders(docs / piece)
            # 번호는 scripts/compare_table_rules.py와 같게 조각 순번(1부터)과 세부보장 순번으로 붙인다
            lines_of[code] = {f"R{i:03d}-{j}": lines for i, rider in enumerate(pieces[code], 1)
                              for j, lines in enumerate(table_rules.read_rider(rider), 1)}
            if code not in crosscheck:
                report.notes.append(f"{code}: 대조 자료가 없어 모든 줄을 검토로 둠")
        years = v.row["갱신주기년"] if v.row["갱신유형"] == "갱신" else None
        out = table_rules.build_rows(v.id, pieces[code], years)
        for r in out.riders:          # 표는 가입 한도를 모른다. 시트에 있던 값을 잇는다(job.run과 같다)
            old = on_sheet.get(r["특약ID"], {})
            r.update({c: old.get(c) for c in job.LIMIT_COLUMNS if r.get(c) is None})
        report.rows["sys_상품종형"].append(v.row)
        report.rows["sys_특약"] += out.riders
        report.rows["sys_급부"] += out.benefits
        report.done.add(v.id)
        made[v.id] = (v, out)

    # 같은 ID로 내용까지 같은 행은 하나만 남긴다. 형식 검사보다 먼저 해야 한다. 그러지 않으면 기본키 중복으로 둘 다 빠진다
    for tab in TABS_WRITTEN:
        job._drop_repeats(tab, report)
    _drop_bad_benefits(report, now)

    owner = {r["특약ID"]: r["종형ID"] for r in report.rows["sys_특약"]}
    log = WorkLog(now, "sys_급부")
    review: set[str] = set()
    for b in report.rows["sys_급부"]:
        bid = b["급부ID"]
        v, out = made[owner[b["특약ID"]]]
        code = v.row["공시상품코드"]
        numbers = out.numbers.get(bid) or (None,)
        # 같은 급부ID, 같은 내용으로 줄어든 세부보장이 여럿이면 번호마다 대조한다. 어느 하나라도 어긋나면 검토다
        reasons = list(dict.fromkeys(
            r for n in numbers
            for r in reasons_of(out.doubts.get(bid, ()), lines_of[code].get(n), crosscheck.get(code, {}).get(n))))
        report.verdicts[bid] = {"번호": ", ".join(n for n in numbers if n) or None,
                                "상태": REVIEW if reasons else CONFIRMED, "사유": reasons}
        if reasons:
            review.add(bid)
            tail = f" (근거 {b['근거문서쪽수']}쪽)"            # 사유가 400자에서 잘려도 근거 쪽은 남게 한다
            why = f"교차 확인: {'; '.join(reasons)}"[:400 - len(tail)] + tail
            log.add("판정", bid, "보류", why, model=MODEL, column=COLUMNS)
            log.add("사람검토이관", bid, "보류", why, model=MODEL, column=COLUMNS)

    by_name: dict[str, list[str]] = {}
    for vid, (v, _) in made.items():
        by_name.setdefault(v.row["공시상품명"], []).append(vid)
    coverage = [row for name, vids in by_name.items() for row in R.coverage_logs(now, vids, name)]
    # 쓴 뒤의 시트에서 검토 대기로 보일 확정 줄(시트에서 검토 대기였던 줄, 같은 요약서를 쓰는 다른 종형의 옛 기록이 옮겨 오는 줄)
    # 에 판정 통과를 남긴다. 화면과 재추출은 가장 나중 실행의 기록만 본다
    after = [r for r in sheet["sys_상품종형"] if r["종형ID"] not in report.done] + report.rows["sys_상품종형"]
    waiting = R.pending_benefits(report.rows["sys_급부"], report.rows["sys_특약"], after, sheet["sys_작업로그"] + log.rows + coverage)
    for bid in sorted(waiting - review):
        log.add("판정", bid, "통과", "교차 확인: 표 규칙과 대조 자료가 같음. 앞선 검토 대기를 풂", model=MODEL)
    report.logs += log.rows + coverage

    for vid, (v, _) in made.items():
        riders = {r["특약ID"] for r in report.rows["sys_특약"] if r["종형ID"] == vid}
        mine = [b["급부ID"] for b in report.rows["sys_급부"] if b["특약ID"] in riders]
        unsure = sum(bid in review for bid in mine)
        report.counts[vid] = {"공시상품코드": v.row["공시상품코드"], "종형명": v.row["종형명"], "특약": len(riders),
                              "급부": len(mine), CONFIRMED: len(mine) - unsure, REVIEW: unsure}

    report.errors = {tab: e for tab in TABS_WRITTEN if (e := check_rows(tab, report.rows[tab]))}
    if report.errors or not report.done or dry_run:
        return report
    try:
        store.replace_variants({t: report.rows[t] for t in TABS_WRITTEN}, report.done, only=TABS_WRITTEN)
        store.append("sys_작업로그", report.logs)
    except Exception as e:  # noqa: BLE001  읽은 결과는 호출한 쪽이 파일로 남길 수 있게 돌려준다
        report.write_error = f"{type(e).__name__}: {str(e)[:300]}"
        report.notes.append(f"시트에 쓰지 못함: {report.write_error}")
        return report
    report.written = True
    return report


def _drop_bad_benefits(report: Loaded, now: datetime) -> None:
    """형식 검사에 걸린 급부 행은 그 행만 빼고 코드대조 반려 기록을 남긴다(job.run과 같다)."""
    bad = check_rows("sys_급부", report.rows["sys_급부"])
    if not bad:
        return
    report.rows["sys_급부"] = [r for r in report.rows["sys_급부"] if r["급부ID"] not in bad]
    for row_id, reasons in bad.items():
        report.notes.append(f"sys_급부 {row_id}: 형식 검사에 걸려 쓰지 않음 ({'; '.join(reasons)})")
        report.logs.append({"로그ID": f"LOG_{ids.short_hash(now.isoformat(), 'sys_급부', row_id, 'drop', length=14)}",
                            "실행일시": now.isoformat(timespec="seconds"), "작업단계": "코드대조", "대상탭": "sys_급부",
                            "대상행ID": row_id, "대상열": None, "변경전값": None, "변경후값": None, "호출모델": None,
                            "판정확률": None, "결과": "반려", "사유": f"형식 검사에 걸려 시트에 쓰지 않음: {'; '.join(reasons)}"[:400]})


def snapshot_store(folder: Path) -> SheetStore:
    """사본(data/snapshot)을 메모리 시트에 올린다. 사본에 없는 열은 빈칸이 된다."""
    data = read_snapshot(folder)
    return SheetStore(MemoryBackend({name: [TABS[name].header] + rows_to_values(TABS[name], rows) for name, rows in data.items()}))


def markdown(report: Loaded) -> str:
    """실행 요약. 표 조각의 문장은 싣지 않는다."""
    head = ["| 공시상품코드 | 종형명 | 특약 | 급부 | 확정 | 검토 |", "| --- | --- | --- | --- | --- | --- |"]
    rows = [f"| {c['공시상품코드']} | {c['종형명']} | {c['특약']} | {c['급부']} | {c[CONFIRMED]} | {c[REVIEW]} |"
            for c in report.counts.values()]
    total = {k: sum(c[k] for c in report.counts.values()) for k in ("특약", "급부", CONFIRMED, REVIEW)}
    rows.append(f"| 합계 | 종형 {len(report.counts)} | {total['특약']} | {total['급부']} | {total[CONFIRMED]} | {total[REVIEW]} |")
    out = "\n".join(head + rows) + "\n\n"
    kinds = collections.Counter(reason.split(":", 1)[0] for v in report.verdicts.values() for reason in set(v["사유"]))
    if kinds:
        out += "검토 사유별 급부 줄 수(한 줄에 사유가 여럿일 수 있음)\n" + "\n".join(f"- {k}: {n}" for k, n in kinds.most_common()) + "\n\n"
    out += f"형식 오류: {sum(len(e) for e in report.errors.values()) if report.errors else 0}행\n"
    out += f"작업 기록: {len(report.logs)}행 (호출모델 '{MODEL}')\n"
    if report.notes:
        out += "\n주의\n" + "\n".join(f"- {n}" for n in report.notes) + "\n"
    return out


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--docs", type=Path, required=True, help="fetch_disclosure.py --org samsungfire의 결과 폴더")
    p.add_argument("--targets", type=Path, default=TARGETS)
    p.add_argument("--only", action="extend", nargs="+", help="이 공시상품코드의 종형만 처리")
    p.add_argument("--dry-run", action="store_true", help="시트에 쓰지 않는다")
    p.add_argument("--snapshot", type=Path, help="시트 대신 이 사본 폴더를 읽는다. 시트에 쓰지 않는다")
    p.add_argument("--result", type=Path, help="종형별 줄 수와 판정을 JSON으로 남길 경로")
    return p.parse_args(argv)


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
    crosscheck = {code: compare.load_table(path) for code, path in CROSSCHECK.items() if path.exists()}
    report = load(store, targets, index, args.docs, crosscheck, datetime.now(KST), dry_run=dry_run, only=args.only)

    text = markdown(report)
    print(text)
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps({"종형": report.counts, "형식 오류": report.errors, "주의": report.notes,
                                           "기록 행 수": len(report.logs), "시트에 씀": report.written,
                                           "verdicts": report.verdicts}, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 표 규칙 적재 (교차 확인)\n\n" + text)
    if report.write_error:
        print("시트에 쓰지 못했습니다:", report.write_error)
        return 1
    if report.errors:
        print("형식 검사에 걸려 시트에 쓰지 않았습니다:", json.dumps(report.errors, ensure_ascii=False)[:2000])
        return 1
    if not report.done:
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
