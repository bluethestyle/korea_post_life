"""시트의 급부를 표준담보 사전에 잇는다 (hum_담보매핑). 이미 행이 있는 급부는 건너뛴다.

  python scripts/map_benefits.py                     # 매핑 행이 없는 새 급부만
  python scripts/map_benefits.py --remap             # 새 급부에 더해 검토상태가 대기인 행을 다시 묻는다
  python scripts/map_benefits.py --remap-states 대기,자동확정,대상외   # 고른 상태의 행을 모두 다시 묻는다
  python scripts/map_benefits.py --remap-match '1인실|응급실'          # 대기 행에 더해 원시급부명이 맞는 자동확정·대상외 행도
  python scripts/map_benefits.py --sync-dictionary   # 먼저 data/seed의 표준담보 사전을 시트 탭에 올린다 (추가와 사용여부만)
  python scripts/map_benefits.py --plan ...          # 시트에 쓰지 않고 판정 모델도 부르지 않는다. 바뀔 것과 호출 수만 보인다
  python scripts/map_benefits.py --plan --snapshot data/snapshot ...   # 접속 정보 없이 사본으로 어림한다
  python scripts/map_benefits.py --dry-run --result out.json

담당자가 정한 행(검토상태가 승인·수정·오류인 행, 담당자메모가 "대상외 확정"으로 시작하는 대상외 행)은 어느 경우에도
다시 묻지 않고, --prune에서도 지우지 않는다(src/postlife/extract/mapping.py의 settled). 쓰기 직전에 시트를 다시 읽어
매핑이 도는 동안 담당자가 정한 행도 덮어쓰지 않는다(mapping.upsert).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from postlife import config  # noqa: E402
from postlife.extract import mapping  # noqa: E402
from postlife.snapshot import KST, read_snapshot  # noqa: E402
from postlife.validate import check_rows  # noqa: E402

TABS_READ = ["sys_상품종형", "sys_특약", "sys_급부", "hum_표준담보사전", "hum_담보매핑", "hum_기준값"]
SEED = ROOT / "data" / "seed" / "hum_표준담보사전.jsonl"
SNAPSHOT = ROOT / "data" / "snapshot"
# 판정 모델의 분당 토큰 한도(5만) 때문에 호출 사이를 띄운다. 토큰 수는 미리 알 수 없어 입력 글자 수로 잰다.
# 2026-11-19 사용량 화면에서 판정 모델의 분당 토큰 최고값이 79.98K로 한도 5만을 넘은 것이 보였다. 그날 4문항 7초 간격의
# 한화 매핑은 호출 하나가 약 1만 200자, 분당 약 8만 7천 자였다(docs/progress.md "표준담보 매핑"). 실패 기록은 없었지만
# 한도를 넘긴 채 다시 시도로 넘어간 것일 수 있어, 한글 한 글자를 토큰 하나로 보고 분당 글자 수를 한도 아래로 둔다.
# 실제 실행에서 다시 시도가 없으면(결과의 모델별 호출 수가 계획한 호출 수와 같으면) --chars-per-minute 로 올릴 수 있다.
BASE_INTERVAL = 7.0
SAFE_CHARS_PER_MINUTE = 48_000


def decide_interval(chars_per_call: int, per_minute: int = SAFE_CHARS_PER_MINUTE) -> float:
    """호출 하나의 입력 글자 수와 분당 글자 수 상한으로 판정 모델 호출 간격(초)을 정한다. 7초보다 짧게 잡지는 않는다."""
    return max(BASE_INTERVAL, round(60.0 * chars_per_call / per_minute, 1))


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--remap", action="store_true", help="새 급부에 더해 이미 행이 있는 급부도 다시 묻는다 (기본은 대기 행만)")
    p.add_argument("--remap-states", help="다시 물을 검토상태를 쉼표로 (대기, 자동확정, 대상외). 주면 --remap을 켠다")
    p.add_argument("--remap-match", help="원시급부명이 이 정규식에 맞는 자동확정·대상외 행도 다시 묻는다. 주면 --remap을 켠다")
    p.add_argument("--sync-dictionary", action="store_true",
                   help="매핑 전에 data/seed의 표준담보 사전을 시트 탭에 올린다 (행 추가와 사용여부 변경만)")
    p.add_argument("--dry-run", action="store_true", help="시트에 쓰지 않는다")
    p.add_argument("--chars-per-minute", type=int, default=SAFE_CHARS_PER_MINUTE,
                   help=f"판정 모델에 분당 보낼 입력 글자 수 상한 (기본 {SAFE_CHARS_PER_MINUTE}). 호출 간격을 이 값으로 정한다")
    p.add_argument("--plan", action="store_true", help="시트에 쓰지 않고 판정 모델도 부르지 않는다. 바뀔 것과 호출 수만 보인다")
    p.add_argument("--snapshot", type=Path, help="--plan과 함께: 시트 대신 이 사본 폴더를 읽는다")
    p.add_argument("--prune", action="store_true", help="시트에 더는 없는 급부의 매핑 행을 걷어낸다 (담당자가 정한 행은 남김)")
    p.add_argument("--result", type=Path)
    args = p.parse_args(argv)
    if args.snapshot and not args.plan:
        p.error("--snapshot은 --plan과 함께만 씁니다")
    if args.chars_per_minute <= 0:
        p.error("--chars-per-minute 는 0보다 커야 합니다")
    return args


def remap_rule(args: argparse.Namespace) -> mapping.Remap | None:
    if not (args.remap or args.remap_states or args.remap_match):
        return None
    states = ([s.strip() for s in args.remap_states.split(",") if s.strip()] if args.remap_states
              else mapping.DEFAULT_REMAP_STATES)
    return mapping.Remap(states=frozenset(states), match=args.remap_match or None)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main(argv: list[str] | None = None) -> int:
    args = parse(argv)
    try:
        rule = remap_rule(args)
    except ValueError as e:     # 고를 수 없는 검토상태, 틀린 정규식
        print(f"다시 묻기 인자가 잘못됐습니다: {e}")
        return 2
    write = not (args.dry_run or args.plan)
    store = None
    if args.snapshot:
        data = read_snapshot(args.snapshot)
        missing = [t for t in TABS_READ if t not in data]
        if missing:
            print(f"사본에 없는 탭: {missing}")
            return 2
    else:
        need = ["GOOGLE_SERVICE_ACCOUNT_JSON", "SPREADSHEET_ID"] + ([] if args.plan else ["GEMINI_API_KEY"])
        if not all(os.environ.get(k) for k in need):
            print("접속 정보가 없어 건너뜁니다.")
            return 0
        from postlife.sheets_io import RestBackend, SheetStore

        store = SheetStore(RestBackend.from_env())
        data = store.read(TABS_READ)
    report: dict = {}
    text = ""

    if args.sync_dictionary:
        sync = mapping.sync_dictionary(data["hum_표준담보사전"], load_jsonl(SEED),
                                       read_snapshot(SNAPSHOT).get("hum_표준담보사전", []))
        print(sync.report())
        text += sync.report() + "\n\n"
        report["dictionary"] = {"added": sync.added, "switched": sync.switched, "drift": sync.drift,
                                "kept": sync.kept, "blocked": sync.blocked}
        if sync.blocked:
            print("사전에 풀어야 할 문제가 있어 시트에 쓰지 않고 멈춥니다.")
            _save(args.result, report)
            return 1
        if sync.changed and write:
            store.write_tab("hum_표준담보사전", sync.rows)
            after = store.read(["hum_표준담보사전"])["hum_표준담보사전"]
            if len(after) != len(sync.rows) or any(not all(mapping.same_value(a.get(c), b.get(c)) for c in a)
                                                   for a, b in zip(sync.rows, after)):
                print("사전 탭을 다시 읽어 보니 쓴 값과 달라 매핑을 하지 않고 멈춥니다.")
                return 1
            print(f"시트에 씀: 표준담보 사전 {len(sync.added)}행 추가, 사용여부 {len(sync.switched)}행 변경")
        data["hum_표준담보사전"] = sync.rows        # 이번 매핑은 새 사전으로 묻는다

    existing = data["hum_담보매핑"]
    if args.prune:
        existing, pruned, orphans = mapping.prune(existing, {b["급부ID"] for b in data["sys_급부"]})
        line = f"급부가 없어진 매핑 행 {pruned}개를 걷어냄" + (
            f", 담당자가 정한 행과 검토상태가 배치 값이 아닌 행 {len(orphans)}개는 남김" if orphans else "")
        print(line)
        text += line + "\n"
        if pruned and write:
            store.write_tab("hum_담보매핑", existing)

    estimate = mapping.plan(data["sys_특약"], data["sys_급부"], data["hum_표준담보사전"], existing, rule)
    interval = decide_interval(estimate["호출당 입력 글자 최대"], args.chars_per_minute)
    estimate["호출 간격(초)"] = interval
    estimate["걸리는 시간 어림(분)"] = round(estimate["호출"] * interval / 60, 1)
    line = f"물을 양: {json.dumps(estimate, ensure_ascii=False)}"
    print(line)
    text += line + "\n"
    report["plan"] = estimate
    if args.plan:
        _save(args.result, report)
        _summary(text)
        return 0

    from postlife.gemini import Gemini

    gemini = Gemini(min_interval={**config.MIN_INTERVAL, config.MODEL_DECIDE: interval}, timeout=config.TIMEOUT, max_retries=3)
    result = mapping.run(gemini, data["sys_상품종형"], data["sys_특약"], data["sys_급부"], data["hum_표준담보사전"],
                         existing, datetime.now(KST), mapping.thresholds_from(data["hum_기준값"]), remap=rule)
    outcome = f"매핑 결과: {result.stats}\n모델별 호출 수: {gemini.calls}\n"
    if result.waiting:
        outcome += "\n담당자 검토 대기\n" + "\n".join(result.waiting) + "\n"
    print(outcome)
    text += outcome
    _save(args.result, {**report, "stats": result.stats, "rows": result.rows, "logs": result.logs})
    _summary(text)
    errors = check_rows("hum_담보매핑", result.rows)
    if errors:
        print("형식 검사에 걸려 시트에 쓰지 않았습니다:", json.dumps(errors, ensure_ascii=False)[:1500])
        return 1
    if not write or not result.rows:
        return 0
    held = mapping.upsert(store, result.rows)      # 실행 중에 담당자가 정한 행도 덮어쓰지 않는다
    store.append("sys_작업로그", result.logs)
    print(f"시트에 씀: 매핑 {len(result.rows) - held}행, 기록 {len(result.logs)}행"
          + (f" (실행 중에 담당자가 정한 행 {held}개는 쓰지 않음)" if held else ""))
    return 0


def _save(path: Path | None, body: dict) -> None:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


def _summary(text: str) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 표준담보 매핑\n\n" + text.replace("\n", "\n\n", 2))


if __name__ == "__main__":
    sys.exit(main())
