"""두 판독(Claude 에이전트와 제미나이)의 매핑 의견을 hum_담보매핑에 넣는다. 판정 모델을 부르지 않는다.

  python scripts/apply_mapping_opinion.py --opinion data/crosscheck/samsungfire_mapping_opinion_2reader.jsonl \\
      --products SAMSUNGFIRE --dry-run --result result/mapping_opinion.json
  python scripts/apply_mapping_opinion.py --opinion <파일> --products EPOST_TOTAL --snapshot data/snapshot   # 접속 정보 없이 사본으로
  python scripts/apply_mapping_opinion.py --opinion data/crosscheck/pending_mapping_opinion_2reader_20261123.jsonl \\
      --products EPOST HANWHALIFE SAMSUNGFIRE --readers opus sonnet --dry-run     # 판독 열 이름이 다른 파일

기존 상품의 초기 적재에 쓴다(2026-11-20 결정, docs/planning.md 4절). 두 의견이 같은 표준담보명이면 자동확정, 둘 다
해당없음이면 대상외, 다르면 대기다. 매핑확률은 비우고 작업 로그의 호출모델에 "교차 확인"을 적는다. 판정 규칙은
src/postlife/extract/mapping.py의 cross_check에 있다.

--products: 고를 상품의 모상품ID, 공시상품코드, 기관코드. 여럿이면 공백이나 쉼표로 나눈다. 종형의 세 열 가운데 하나라도
맞으면 그 종형의 급부를 다룬다. 어느 종형에도 맞지 않는 값이 있으면 오타로 보고 멈춘다.
의견 파일은 줄마다 {"번호", "특약", "급부", "claude", "claude확신", "gemini", "gemini확신"}이다. 특약과 급부는
mapping.kind_name으로 만든 묶음 이름이고, 확신은 읽기만 하고 판정에 쓰지 않는다. 다른 열이 더 있어도 읽지 않는다.
--readers: 두 판독의 열 이름(기본 claude gemini). 두 판독이 모두 Claude 쪽인 파일은 --readers opus sonnet처럼 준다.
앞의 열이 대기 줄의 추천에서 먼저다. 판정 규칙은 열 이름과 상관없이 같다.
판독 열의 값 "신규"(새 담보가 필요함)와 "모름"은 사전에 없는 이름이라 확정하지 않는다. 한쪽만 그렇게 적으면 대기,
둘 다 그렇게 적으면 의견이 없는 급부와 같다(매핑 행이 있으면 그대로 둔다).

담당자가 정한 행(검토상태가 승인·수정·오류인 행, 담당자메모가 "대상외 확정"으로 시작하는 대상외 행)과 검토상태가 배치 값
밖인 행은 건드리지 않는다(mapping.protected). 쓰기 직전에 시트를 다시 읽어 합친다(mapping.upsert). 담당자메모는 쓰지 않는다.
--snapshot으로 돌면 시트에 쓰지 않는다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from postlife.extract import mapping  # noqa: E402
from postlife.snapshot import KST, read_snapshot  # noqa: E402
from postlife.validate import check_rows  # noqa: E402

TABS_READ = ["sys_상품종형", "sys_특약", "sys_급부", "hum_표준담보사전", "hum_담보매핑"]
PICK_COLUMNS = ("모상품ID", "공시상품코드", "기관코드")       # --products 값을 견주는 sys_상품종형의 열
HOLD = ("신규", "모름")      # 판독 열에 적어도 확정하지 않는 값. 출력에서 사전에 없는 이름(오타)과 따로 센다


def fields(readers: tuple[str, str] = mapping.READERS) -> tuple[str, ...]:
    """의견 파일의 줄마다 있어야 하는 열."""
    return ("번호", "특약", "급부", *readers)


def _tokens(values: list[str]) -> list[str]:
    return [t for arg in values for t in re.split(r"[,\s]+", arg) if t]


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--opinion", type=Path, required=True, help="두 판독의 의견 파일 (JSON Lines)")
    p.add_argument("--products", nargs="+", required=True,
                   help="고를 상품의 모상품ID, 공시상품코드, 기관코드 (여럿이면 공백이나 쉼표로 나눈다)")
    p.add_argument("--readers", nargs="+", default=list(mapping.READERS),
                   help="두 판독의 열 이름 (기본 claude gemini. 공백이나 쉼표로 나눈다. 앞의 열이 대기 줄 추천에서 먼저다)")
    p.add_argument("--dry-run", action="store_true", help="시트에 쓰지 않는다")
    p.add_argument("--snapshot", type=Path, help="시트 대신 이 사본 폴더를 읽는다. 시트에 쓰지 않는다")
    p.add_argument("--result", type=Path)
    args = p.parse_args(argv)
    args.products = _tokens(args.products)
    if not args.products:
        p.error("--products에 고를 상품이 없습니다")
    readers = _tokens(args.readers)
    if len(readers) != 2 or readers[0] == readers[1] or set(readers) & {"번호", "특약", "급부"}:
        p.error(f"--readers에는 서로 다른 판독 열 이름 둘을 줍니다: {readers}")
    args.readers = (readers[0], readers[1])
    return args


def _key(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def load_opinions(path: Path, readers: tuple[str, str] = mapping.READERS) -> dict[tuple[str, str], dict]:
    """의견 파일을 (특약, 급부) → 줄로 읽는다. 특약과 급부는 공백만 하나로 줄여 견준다(이미 묶음 이름이므로 kind_name을
    다시 걸지 않는다). 빠진 열(번호, 특약, 급부, 두 판독 열)이 있거나, 같은 묶음에 의견이 다른 줄이 두 번 나오면 ValueError."""
    need = fields(readers)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        raise ValueError(f"의견 파일을 읽지 못했습니다: {path} ({e})") from e
    out: dict[tuple[str, str], dict] = {}
    for no, text in enumerate(lines, 1):
        if not text.strip():
            continue
        try:
            line = json.loads(text)
        except ValueError as e:
            raise ValueError(f"의견 파일 {no}째 줄이 JSON이 아닙니다 ({e})") from e
        if not isinstance(line, dict):
            raise ValueError(f"의견 파일 {no}째 줄이 객체가 아닙니다")
        missing = [f for f in need if f not in line]
        if missing or not all(isinstance(line.get(f), str) and line[f].strip() for f in ("특약", "급부")):
            raise ValueError(f"의견 파일 {no}째 줄에 빠진 열이 있습니다: {', '.join(missing) or '특약이나 급부가 비어 있음'}")
        key = (_key(line["특약"]), _key(line["급부"]))
        if key in out:
            before = out[key]
            if tuple(before.get(r) for r in readers) != tuple(line.get(r) for r in readers):
                raise ValueError(f"의견 파일에 같은 묶음의 의견이 서로 다르게 두 번 나옵니다: 번호 {before.get('번호')}, "
                                 f"{line.get('번호')}")
            continue
        out[key] = line
    return out


def pick(variants: list[dict], tokens: list[str]) -> tuple[list[dict], list[str]]:
    """(고른 종형, 어느 종형에도 맞지 않은 값)."""
    wanted = set(tokens)
    chosen = [v for v in variants if wanted & {str(v.get(c) or "") for c in PICK_COLUMNS}]
    seen = {str(v.get(c) or "") for v in chosen for c in PICK_COLUMNS}
    return chosen, [t for t in tokens if t not in seen]


def main(argv: list[str] | None = None) -> int:
    args = parse(argv)
    try:
        opinions = load_opinions(args.opinion, args.readers)
    except ValueError as e:
        print(e)
        return 2
    write = not (args.dry_run or args.snapshot)
    store = None
    if args.snapshot:
        data = read_snapshot(args.snapshot)
        missing = [t for t in TABS_READ if t not in data]
        if missing:
            print(f"사본에 없는 탭: {missing}")
            return 2
    else:
        if not all(os.environ.get(k) for k in ("GOOGLE_SERVICE_ACCOUNT_JSON", "SPREADSHEET_ID")):
            print("접속 정보가 없어 건너뜁니다.")
            return 0
        from postlife.sheets_io import RestBackend, SheetStore

        store = SheetStore(RestBackend.from_env())
        data = store.read(TABS_READ)

    variants, unmatched = pick(data["sys_상품종형"], args.products)
    if unmatched:
        print(f"어느 종형의 {', '.join(PICK_COLUMNS)}에도 맞지 않는 값: {unmatched}")
        return 2
    variant_ids = {v["종형ID"] for v in variants}
    riders = [r for r in data["sys_특약"] if r["종형ID"] in variant_ids]
    rider_ids = {r["특약ID"] for r in riders}
    benefits = [b for b in data["sys_급부"] if b["특약ID"] in rider_ids]

    result = mapping.cross_check(variants, riders, benefits, data["hum_표준담보사전"], data["hum_담보매핑"],
                                 opinions, datetime.now(KST), readers=args.readers)
    text = (f"고른 종형 {len(variants)}개 ({', '.join(sorted({v['모상품ID'] for v in variants}))}), "
            f"급부 {len(benefits)}개, 의견 파일 {args.opinion} (판독 열 {', '.join(args.readers)})\n"
            f"교차 확인 결과: {json.dumps(result.stats, ensure_ascii=False)}\n"
            f"표준담보별 자동확정: {json.dumps(result.by_standard, ensure_ascii=False)}\n")
    held = [u for u in result.unknown if u["이름"] in HOLD]
    typos = [u for u in result.unknown if u["이름"] not in HOLD]
    if held:
        text += f"신규나 모름이라 확정하지 않은 의견 {len(held)}개: " + ", ".join(
            f"{u['번호']} {u['판독']} {u['이름']}" for u in held) + "\n"
    if typos:
        text += "사전에 없는 의견: " + ", ".join(f"{u['번호']} {u['판독']} '{u['이름']}'" for u in typos) + "\n"
    if result.unused:
        text += f"고른 급부에 맞지 않은 의견 {len(result.unused)}줄: {', '.join(result.unused[:30])}" + (
            " 외" if len(result.unused) > 30 else "") + "\n"
    if result.waiting:
        text += "\n담당자 검토 대기 (이번에 쓰는 줄)\n" + "\n".join(result.waiting) + "\n"
    print(text)
    _save(args.result, {"readers": list(args.readers), "stats": result.stats, "by_standard": result.by_standard,
                        "unknown": result.unknown,
                        "unused": result.unused, "rows": result.rows, "logs": result.logs})
    _summary(text)

    errors = {**check_rows("hum_담보매핑", result.rows), **check_rows("sys_작업로그", result.logs)}
    if errors:
        print("형식 검사에 걸려 시트에 쓰지 않았습니다:", json.dumps(errors, ensure_ascii=False)[:1500])
        return 1
    if not write:
        print("시트에 쓰지 않았습니다 (" + ("사본으로 돎" if args.snapshot else "--dry-run") + ").")
        return 0
    if result.rows:
        held = mapping.upsert(store, result.rows)      # 실행 중에 담당자가 정한 행도 덮어쓰지 않는다
        store.append("sys_작업로그", result.logs)
        print(f"시트에 씀: 매핑 {len(result.rows) - held}행, 기록 {len(result.logs)}행"
              + (f" (실행 중에 담당자가 정한 행 {held}개는 쓰지 않음)" if held else ""))
    else:
        print("바꿀 매핑 행이 없어 시트에 쓰지 않았습니다.")
    return 0


def _save(path: Path | None, body: dict) -> None:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


def _summary(text: str) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 표준담보 매핑 교차 확인\n\n" + text.replace("\n", "\n\n"))


if __name__ == "__main__":
    sys.exit(main())
