"""가상 사본(회사 20곳)으로 시안 4를 합친다. 회사 수에 매이지 않는 화면을 시험하는 자료다.

쓰기: python scripts/dev/build_console4_synthetic.py [--snapshot data/snapshot] [--synthetic out/synthetic_snapshot]
      [--out out/console4_synthetic.html] [--life 9] [--nonlife 8] [--work 폴더]

한 명령으로 세 단계를 돈다(단계마다 걸린 시간과 자료 크기를 찍는다).
1. 가상 사본을 만든다(scripts/dev/make_synthetic_snapshot.py. 우체국, 한화생명, 삼성화재에 가상 생명보험사와 손해보험사를 더한다).
2. proto_src/console4 를 작업 폴더에 복사하고, 그 안에 가상 사본의 화면 자료를 내보낸다(scripts/export_app_data.py 와 같은 계산.
   손으로 쓴 코드는 proto_src/console4 에서 읽는다). proto_src/console4 의 원본과 자료는 건드리지 않는다.
3. 작업 폴더의 원본과 자료를 build.py 로 합친다(--src). 맨 위 고지 줄 옆에 "가상 자료(화면 배치 시험용, 실제 회사 자료 아님)"를
   끼운다(--banner. tpl.html 은 고치지 않는다).

출력은 out/ 아래(저장소에 커밋하지 않는다)에 쓰고 site/ 아래에는 쓰지 않는다(공개 배포되면 안 된다).
--work 를 주면 작업 폴더를 지우지 않고 남긴다(자료 파일 크기를 볼 때). 작업 폴더가 이미 있으면 비었거나 이 명령이 만든
작업 폴더(표식 파일 .console4_synthetic_work)일 때만 지우고 다시 만든다. 그 밖의 폴더(--work data 따위)는 지우지 않고 멈춘다.
모델 호출, 시트 쓰기는 하지 않는다.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "proto_src" / "console4"
NOTICE = "가상 자료(화면 배치 시험용, 실제 회사 자료 아님)"
DATA_FILES = ["sales.json", "combo.json", "gate.json", "cover.json", "d.json", "tab3.js", "tab4.js"]
WORK_MARK = ".console4_synthetic_work"   # 이 명령이 만든 작업 폴더의 표식. 표식이 없는 폴더는 지우지 않는다


def run(step: str, cmd: list[str]) -> float:
    t0 = time.time()
    p = subprocess.run(cmd, cwd=ROOT)
    dt = time.time() - t0
    if p.returncode != 0:
        raise SystemExit(f"{step} 단계가 멈췄다(끝 코드 {p.returncode})")
    print(f"[{step}] {dt:.1f}초", flush=True)
    return dt


def under_site(path: Path) -> bool:
    site = (ROOT / "site").resolve()
    p = path.resolve()
    return p == site or site in p.parents


def work_refusal(work: Path) -> str | None:
    """--work 로 받은 폴더를 지우고 다시 만들 수 없는 까닭. 없거나 빈 폴더, 이 명령이 만든 작업 폴더(WORK_MARK 가 있다)이면
    None. 그 밖의 폴더를 지우면 저장소 자료(--work data, --work proto_src/console4)를 통째로 날리므로 막는다."""
    if not work.exists() and not work.is_symlink():
        return None
    if work.is_symlink() or not work.is_dir():
        return f"작업 폴더 {work} 는 폴더가 아니다"
    if not any(work.iterdir()) or (work / WORK_MARK).is_file():
        return None
    return f"작업 폴더 {work} 는 이 명령이 만든 작업 폴더가 아니라서(표식 {WORK_MARK} 가 없다) 지우지 않는다"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, default=ROOT / "data" / "snapshot", help="본뜰 실제 사본")
    ap.add_argument("--synthetic", type=Path, default=ROOT / "out" / "synthetic_snapshot", help="가상 사본을 쓸 폴더")
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "console4_synthetic.html", help="합친 화면")
    ap.add_argument("--life", type=int, default=9)
    ap.add_argument("--nonlife", type=int, default=8)
    ap.add_argument("--work", type=Path, help="작업 폴더(주면 남긴다)")
    args = ap.parse_args()
    # 단계마다 저장소 뿌리에서 돌리므로 경로는 지금 폴더 기준으로 먼저 푼다
    args.snapshot, args.synthetic, args.out = args.snapshot.resolve(), args.synthetic.resolve(), args.out.resolve()
    args.work = args.work.resolve() if args.work else None
    for p in (args.out, args.synthetic, *([args.work] if args.work else [])):
        if under_site(p):
            print(f"site/ 아래에는 쓰지 않는다(공개 배포되는 폴더다): {p}")
            return 1
    if args.work:
        refusal = work_refusal(args.work)
        if refusal:
            print(refusal)
            return 1
        if args.work == args.synthetic or args.work in args.synthetic.parents or args.synthetic in args.work.parents:
            print(f"작업 폴더와 가상 사본 폴더가 겹친다: {args.work}, {args.synthetic}")
            return 1
    py = sys.executable
    run("가상 사본", [py, str(ROOT / "scripts/dev/make_synthetic_snapshot.py"), "--snapshot", str(args.snapshot),
                    "--out", str(args.synthetic), "--life", str(args.life), "--nonlife", str(args.nonlife)])
    tmp = None
    if args.work:
        work = args.work
        refusal = work_refusal(work)   # 가상 사본을 만드는 사이에 바뀌었을 때를 위해 지우기 바로 전에 다시 본다
        if refusal:
            print(refusal)
            return 1
        if work.exists():
            shutil.rmtree(work)
    else:
        tmp = tempfile.TemporaryDirectory(prefix="console4_synthetic_")
        work = Path(tmp.name) / "console4"
    try:
        shutil.copytree(SRC, work, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (work / WORK_MARK).write_text("scripts/dev/build_console4_synthetic.py 가 만든 작업 폴더\n", encoding="utf-8")
        run("화면 자료", [py, str(ROOT / "scripts/export_app_data.py"), "--snapshot", str(args.synthetic), "--out", str(work)])
        args.out.parent.mkdir(parents=True, exist_ok=True)
        run("합치기", [py, str(SRC / "build.py"), str(args.out), "--src", str(work), "--banner", NOTICE])
        sizes = {n: (work / n).stat().st_size for n in DATA_FILES}
        print("자료 크기: " + ", ".join(f"{n} {s:,}" for n, s in sizes.items()) + f", 합친 화면 {args.out.stat().st_size:,}바이트")
        if args.work:
            print(f"작업 폴더를 남겼다: {work}")
    finally:
        if tmp is not None:
            tmp.cleanup()
    print(f"썼다: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
