"""초기 적재에서 주계약 가입조건을 읽은 두 판독 파일을 일감과 맞춰 견주고, 기계 검사를 돌리고, 커밋할 수 있는 값 파일을 쓴다.

두 판독(예: sonnet, opus)이 일감 하나(가입조건일감/1)를 따로 읽어 낸 판독 파일(가입조건판독/1)을 받는다.
종형마다 줄(성별, 보험기간, 납입기간별 최저와 최고 가입나이)과 가입한도가 같은지 보고, 기계 검사
(src/postlife/extract/reader_conditions.py)에 걸린 표를 낸다. 지시문은 docs/backfill_conditions_guide.md.

- 자동 판정 "확정": 두 판독의 줄과 한도가 모두 같고, 두 판독 모두 기계 검사의 문제와 표시가 없고, 모름이 없는 종형.
- 그 밖은 "판정필요". 메인 세션이 원문 쪽을 보고 값 파일의 판정 칸을 채운다: 확정(두 값이 같을 때), 판독 이름(그 판독의 값),
  수정(판정값 칸에 고친 값. 판독 값과 같은 꼴), 검토 대기.

값 파일(--out, JSONL)은 종형마다 한 줄이다. 두 판독의 값(숫자, 기간 글자, 표 제목의 짧은 낱말), 칸별 일치, 다른 줄, 기계 검사,
자동판정, 판정, 판정값. 원문 구절과 판독자가 쓴 모름 이유는 싣지 않는다.
--rows를 주면 판정이 끝난 종형(확정, 판독 이름, 수정)의 sys_가입조건 행을 JSONL로 쓴다.

쪽 글자는 일감의 사업방법서와 상품요약서 "글자" 경로에서 읽는다(scripts/fetch_disclosure.py가 쓴 쪽 구분 글자 파일이나 {쪽: 글자} JSON).
--method-text, --summary-text로 바꿀 수 있다.

  python scripts/compare_condition_readers.py 일감.json --check 일감.sonnet.json         # 판독 파일 하나의 꼴만 본다
  python scripts/compare_condition_readers.py 일감.json --answers 판독폴더 --readers sonnet opus --out 값.jsonl [--report 견줌.json] [--rows 행.jsonl]
  python scripts/compare_condition_readers.py 일감.json --a 일감.sonnet.json --b 일감.opus.json --out 값.jsonl
  python scripts/compare_condition_readers.py 일감.json --values 값.jsonl --readers sonnet opus --rows 행.jsonl   # 판정을 채운 값 파일로 행만 만든다
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.extract import reader_conditions as RC  # noqa: E402
from postlife.extract.segment import pages_from_text  # noqa: E402


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_pages(path: str | Path | None) -> dict[int, str] | None:
    """쪽 글자 파일을 {쪽: 글자}로. .json이면 {쪽: 글자} JSON, 아니면 fetch_disclosure.py의 쪽 구분 글자 파일. 없으면 None."""
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    if p.suffix == ".json":
        return {int(k): v for k, v in _load(p).items()}
    return pages_from_text(p.read_text(encoding="utf-8"))


def task_pages(task: Mapping[str, Any], method: Path | None = None, summary: Path | None = None) -> dict[str, dict[int, str]]:
    out = {}
    for doc, override in (("사업방법서", method), ("상품요약서", summary)):
        pages = load_pages(override or (task.get(doc) or {}).get("글자"))
        if pages:
            out[doc] = pages
    return out


def summary(results: Sequence[Mapping[str, Any]]) -> str:
    lines = [x for r in results for x in r["줄"]]
    names = results[0]["판독"] if results else ["A", "B"]
    out = [f"일감 {len(results)}, 종형 {len(lines)}"]
    by_field: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for x in lines:
        for name, state in x["일치"].items():
            by_field[name][state] += 1
    out.append("\n칸별 일치 (같음 / 다름 / 한쪽모름 / 둘다모름)")
    for name in ("줄", "한도", "근거쪽"):
        c = by_field.get(name)
        if c:
            out.append(f"- {name}: {c[RC.SAME]} / {c[RC.DIFF]} / {c[RC.ONE_UNKNOWN]} / {c[RC.BOTH_UNKNOWN]}")
    auto = collections.Counter(x["자동판정"] for x in lines)
    out.append(f"\n자동판정: 확정 {auto[RC.CONFIRMED]}, 판정필요 {auto[RC.NEEDS_JUDGE]}")
    for r in results:
        for name, problems in r["형식 문제"].items():
            for p in problems:
                out.append(f"- 형식 문제 {r['일감']} {name}: {p}")
    differ = [x for x in lines if x["자동판정"] != RC.CONFIRMED]
    if differ:
        out.append("\n판정이 필요한 종형")
        for x in differ:
            absent = [name for name in names if x[name] is None]
            fields = [f"{', '.join(absent)} 판독 없음"] if absent else \
                [f for f, s in x["일치"].items() if s != RC.SAME and f != "근거쪽"]
            unknown = [f"{name} 모름({', '.join(x[name]['모름'])})" for name in names if x[name] and x[name].get("모름")]
            checks = sorted({f"{name} {p}" for name in names for p in x["기계검사"][name]["문제"] + x["기계검사"][name]["표시"]})
            out.append(f"- {x['종형명']} ({x['종형ID']}) | 다른 칸: {', '.join(fields) or '없음'}"
                       + (f" | {'; '.join(unknown)}" if unknown else ""))
            out += [f"    다른 줄 {d}" for d in x["다른줄"][:12]]
            out += [f"    검사 {c}" for c in checks[:12]]
    return "\n".join(out)


def write_rows(task: Mapping[str, Any], lines: Sequence[Mapping[str, Any]], names: Sequence[str], path: Path) -> RC.Built:
    finals = {x["종형ID"]: RC.final_value(x, names) for x in lines}
    built = RC.build_rows(task["종형"], finals)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in built.conditions:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return built


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("task", type=Path, help="일감 파일(가입조건일감/1)")
    p.add_argument("--check", type=Path, help="판독 파일 하나의 꼴만 본다(판독자가 내기 전에 스스로 돌린다). 견주지 않는다")
    p.add_argument("--a", type=Path, help="첫째 판독 파일")
    p.add_argument("--b", type=Path, help="둘째 판독 파일")
    p.add_argument("--answers", type=Path, help="판독 파일 폴더. <일감>.<판독자>.json을 찾는다")
    p.add_argument("--readers", nargs=2, default=None, help="두 판독의 이름. 비우면 판독 파일의 판독자 칸")
    p.add_argument("--method-text", type=Path, help="사업방법서 쪽 글자(일감의 글자 경로 대신)")
    p.add_argument("--summary-text", type=Path, help="상품요약서 쪽 글자(일감의 글자 경로 대신)")
    p.add_argument("--out", type=Path, help="값 파일(JSONL). 원문 구절이 없어 커밋할 수 있다")
    p.add_argument("--report", type=Path, help="견줌 결과 전체(JSON). 리포 밖에 둔다")
    p.add_argument("--values", type=Path, help="판정을 채운 값 파일. 견주지 않고 이 파일로 --rows만 만든다")
    p.add_argument("--rows", type=Path, help="판정이 끝난 종형의 sys_가입조건 행(JSONL)")
    args = p.parse_args(argv)

    task = _load(args.task)
    problems = RC.check_task(task)
    if problems:
        print("일감 문제\n" + "\n".join(problems))
        return 1

    if args.check:
        problems = RC.check_file(task, _load(args.check))
        print("\n".join(problems) if problems else "꼴 문제 없음")
        return 1 if problems else 0

    if args.values:
        if not (args.rows and args.readers):
            p.error("--values에는 --rows와 --readers가 필요합니다")
        lines = [json.loads(x) for x in args.values.read_text(encoding="utf-8").splitlines() if x.strip()]
        built = write_rows(task, [x for x in lines if x.get("일감") == task["일감"]], args.readers, args.rows)
        print(f"행 {len(built.conditions)}개, 종형 {len(built.done)}개: {args.rows}")
        print("\n".join(built.notes))
        return 0

    if args.answers:
        if not args.readers:
            p.error("--answers에는 --readers가 필요합니다")
        files = [args.answers / f"{task['일감']}.{name}.json" for name in args.readers]
    else:
        if not (args.a and args.b):
            p.error("--a, --b를 주거나 --answers와 --readers를 주세요")
        files = [args.a, args.b]
    answers = [_load(f) if f.exists() else {} for f in files]
    names = list(args.readers or [str(x.get("판독자") or tag) for x, tag in zip(answers, ("A", "B"))])
    if names[0] == names[1]:
        names = [f"{names[0]}1", f"{names[1]}2"]
    pages = task_pages(task, args.method_text, args.summary_text)
    result = RC.compare_task(task, dict(zip(names, answers)), names, pages or None)

    print(summary([result]))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as f:
            for line in result["줄"]:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
        print(f"\n값 파일: {args.out}")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.rows:
        built = write_rows(task, result["줄"], names, args.rows)
        print(f"행 {len(built.conditions)}개(판정이 끝난 종형 {len(built.done)}개): {args.rows}")
        for note in built.notes:
            print(f"- {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
