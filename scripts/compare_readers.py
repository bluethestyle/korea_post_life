"""초기 적재의 두 판독 파일을 묶음의 조각과 맞춰 견주고, 기계 검사를 돌리고, 커밋할 수 있는 값 파일을 쓴다.

두 판독(예: sonnet, opus)이 묶음 하나(scripts/split_pieces.py의 결과)를 따로 읽어 낸 판독 파일(판독값/1)을 받는다.
칸마다 같음, 다름, 한쪽모름, 둘다모름을 세고, 어긋난 줄과 기계 검사(src/postlife/extract/reader_rows.py)에 걸린 줄을 낸다.

- 자동 판정 "확정": 두 판독의 꼴이 맞고, 견줄 칸이 모두 같고, 두 판독 모두 기계 검사의 문제와 표시가 없고, 같은 조각에서
  이름이 같은 세부보장이 서로 다른 값으로 갈리지 않고, 주의에 "세부보장여럿묶임"이나 "그밖"이 없고 행없음사유가 "그밖"이
  아닌 줄. 행없음끼리 사유와 면책일수, 보장개시일, 한도가 같은 줄도 확정(행을 만들지 않음)이다.
- 같은 조각에 이름이 같은 세부보장이 여럿이면 판독마다 줄의 "대상"이 모두 있고 서로 달라야 한다. 대상이 비었거나
  서로 같으면 판정필요다(급부명 "세부보장명(대상)"이 겹친다). 대상이 서로 다른 줄은 값이 달라도 갈림으로 세지 않는다.
- 그 밖은 "판정필요". 메인 세션이 원문 쪽을 보고 값 파일의 판정 칸을 채운다: 확정(두 값이 같을 때), 판독 이름(그 판독의 값),
  수정(판정값 칸에 고친 값), 검토 대기.

값 파일(--out, JSONL)은 data/crosscheck/에 둘 꼴이다. 줄마다 번호, 쪽, 특약명, 급부명, 두 판독의 값, 칸별 일치, 기계 검사,
자동판정, 판정, 판정값. 판독 값은 구조(숫자, 낱말, 허용값)만 담고 원문 구절과 판독자가 쓴 모름 이유는 싣지 않는다.

  python scripts/compare_readers.py 묶음.json --a 묶음.sonnet.json --b 묶음.opus.json --out 값.jsonl [--report 견줌.json] [--page-text 쪽글자.json]
  python scripts/compare_readers.py 묶음폴더/6AFLT_B*.json --answers 판독폴더 --readers sonnet opus --out 값.jsonl
    (--answers 폴더에서는 묶음마다 <묶음>.<판독자>.json을 찾는다)
  python scripts/compare_readers.py 묶음.json --check 묶음.sonnet.json     # 판독 파일 하나의 꼴만 본다
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.extract import reader_rows as RR  # noqa: E402

MISSING = "판독 없음"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_bundle(bundle: Mapping[str, Any], answers: Mapping[str, Any], names: Sequence[str],
                   pages: Mapping[int, str] | None = None) -> dict[str, Any]:
    """묶음 하나와 판독 둘({판독 이름: 판독 파일 내용})을 견준다. pages는 {쪽: 쪽 글자}(면책근거쪽 확인용)."""
    a_name, b_name = names
    pieces = RR.load_pieces(bundle)
    found = RR.covers_by_number(pieces)
    order = [c.number for p in pieces for c in p.covers]
    parsed, errors = {}, {}
    for name in names:
        values, problems = RR.parse_readings(answers[name])
        extra = sorted(set(values) - set(found), key=RR._order)
        if extra:
            problems.append(f"묶음에 없는 번호: {', '.join(extra[:10])}{' …' if len(extra) > 10 else ''}")
            values = {k: v for k, v in values.items() if k in found}
        absent = [n for n in order if n not in values]
        if absent:
            problems.append(f"판독이 없는 번호 {len(absent)}개: {', '.join(absent[:10])}{' …' if len(absent) > 10 else ''}")
        parsed[name], errors[name] = values, problems
    a, b = parsed[a_name], parsed[b_name]
    states = RR.compare(a, b, order)
    splits = {name: RR.same_name_splits(pieces, parsed[name]) for name in names}
    split_numbers = {n for s in splits.values() for nums in s.values() for n in nums}
    unlabeled = {name: RR.same_name_unlabeled(pieces, parsed[name]) for name in names}
    unlabeled_numbers = {n for s in unlabeled.values() for nums in s.values() for n in nums}
    grouped = {c.number for p in pieces for g in RR.same_name_groups(p) for c in g}
    lines = []
    for n in order:
        piece, cover = found[n]
        checks = {}
        for name in names:
            v = parsed[name].get(n)
            problems, marks = RR.machine_checks(cover, v, piece, pages) if v else ([MISSING], [])
            if v and v.get("대상") and n not in grouped:
                problems.append("대상: 이름이 같은 줄이 없는데 대상이 있음")
            checks[name] = {"문제": problems, "표시": marks}
        same = RR.agreed(states[n]) and n in a and n in b
        clean = all(not checks[x]["문제"] and not checks[x]["표시"] for x in names)
        odd = any(RR.needs_review(parsed[x].get(n)) for x in names)
        loose = n in split_numbers or n in unlabeled_numbers
        auto = RR.CONFIRMED if same and clean and not odd and not loose else RR.NEEDS_JUDGE
        lines.append({
            "번호": n, "쪽": cover.page, "특약명": piece.title, "급부명": cover.name,
            **({"형": piece.segment} if piece.segment else {}),
            a_name: RR.stored_value(a[n]) if n in a else None,
            b_name: RR.stored_value(b[n]) if n in b else None,
            "일치": states[n],
            "기계검사": checks,
            "이름같은줄갈림": n in split_numbers,
            "대상확인필요": n in unlabeled_numbers,
            "자동판정": auto,
            "판정": RR.CONFIRMED if auto == RR.CONFIRMED else "",
            "판정값": None,
        })
    return {"묶음": bundle.get("묶음"), "판독": list(names), "형식 문제": errors, "이름같은줄갈림": splits,
            "대상확인필요": unlabeled, "줄": lines}


def check_file(bundle: Mapping[str, Any], answer: Any) -> list[str]:
    """판독 파일 하나의 꼴 문제, 빠지거나 남는 번호, 이름이 같은 줄의 대상.

    기계 검사는 돌리지 않는다(판독자가 값을 검사에 맞추지 않게). 대상은 조각의 이름만 보고 정해지는 꼴이라 여기서 본다.
    """
    pieces = RR.load_pieces(bundle)
    order = [c.number for piece in pieces for c in piece.covers]
    values, problems = RR.parse_readings(answer)
    grouped = {c.number for p in pieces for g in RR.same_name_groups(p) for c in g}
    for n in order:
        v = values.get(n)
        if v and v.get("대상") and n not in grouped:
            problems.append(f"{n}: 이름이 같은 줄이 없는데 대상이 있음")
    for key, nums in RR.same_name_unlabeled(pieces, values).items():
        problems.append(f"{key.split('/', 1)[0]}: 이름이 같은 줄({', '.join(nums)})의 대상이 비었거나 서로 같음")
    if isinstance(answer, Mapping) and answer.get("묶음") != bundle.get("묶음"):
        problems.append(f"묶음 이름이 다름: {answer.get('묶음')!r}")
    absent = [n for n in order if n not in values]
    extra = sorted(set(values) - set(order), key=RR._order)
    if absent:
        problems.append(f"판독이 없는 번호 {len(absent)}개: {', '.join(absent)}")
    if extra:
        problems.append(f"묶음에 없는 번호: {', '.join(extra)}")
    return problems


def summary(results: Sequence[Mapping[str, Any]]) -> str:
    lines = [x for r in results for x in r["줄"]]
    names = results[0]["판독"] if results else ["A", "B"]
    out = [f"묶음 {len(results)}, 세부보장 {len(lines)}"]
    by_field: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for x in lines:
        for field, state in x["일치"].items():
            by_field[field][state] += 1
    out.append("\n칸별 일치 (같음 / 다름 / 한쪽모름 / 둘다모름)")
    for field in RR.FIELDS:
        c = by_field.get(field)
        if c:
            out.append(f"- {field}: {c[RR.SAME]} / {c[RR.DIFF]} / {c[RR.ONE_UNKNOWN]} / {c[RR.BOTH_UNKNOWN]}")
    auto = collections.Counter(x["자동판정"] for x in lines)
    forms = collections.Counter((x[names[0]] or {}).get("꼴") for x in lines if x["자동판정"] == RR.CONFIRMED)
    out.append(f"\n자동판정: 확정 {auto[RR.CONFIRMED]} (꼴별 {dict(forms)}), 판정필요 {auto[RR.NEEDS_JUDGE]}")
    for r in results:
        for name, problems in r["형식 문제"].items():
            for p in problems:
                out.append(f"- 형식 문제 {r['묶음']} {name}: {p}")
    differ = [x for x in lines if x["자동판정"] != RR.CONFIRMED]
    if differ:
        out.append("\n판정이 필요한 줄")
        for x in differ:
            absent = [name for name in names if x[name] is None]
            fields = [f"{', '.join(absent)} 판독 없음"] if absent else [f for f, s in x["일치"].items() if s != RR.SAME]
            checks = [f"{name} {p}" for name in names for p in x["기계검사"][name]["문제"] + x["기계검사"][name]["표시"]]
            tail = checks + (["이름 같은 줄이 갈림"] if x["이름같은줄갈림"] else []) \
                + (["이름 같은 줄의 대상이 비었거나 같음"] if x.get("대상확인필요") else [])
            out.append(f"- {x['번호']} ({x['쪽']}쪽) {x['급부명'][:40]} | 다른 칸: {', '.join(fields) or '없음'}"
                       + (f" | 검사: {'; '.join(tail)}" if tail else ""))
    kinds = collections.Counter(p.split(":", 1)[0] for x in lines for name in names for p in x["기계검사"][name]["문제"])
    marks = collections.Counter(p.split(":", 1)[0].split(" (", 1)[0] for x in lines for name in names
                                for p in x["기계검사"][name]["표시"])
    if kinds or marks:
        out.append("\n기계 검사(두 판독을 합쳐 센 수)")
        out += [f"- 문제 {k}: {n}" for k, n in kinds.most_common()]
        out += [f"- 표시 {k}: {n}" for k, n in marks.most_common()]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("bundles", type=Path, nargs="+", help="split_pieces.py가 쓴 묶음 파일")
    p.add_argument("--a", type=Path, help="첫째 판독 파일(묶음이 하나일 때)")
    p.add_argument("--b", type=Path, help="둘째 판독 파일(묶음이 하나일 때)")
    p.add_argument("--answers", type=Path, help="판독 파일 폴더. 묶음마다 <묶음>.<판독자>.json을 찾는다")
    p.add_argument("--readers", nargs=2, default=None, help="두 판독의 이름. 비우면 판독 파일의 판독자 칸")
    p.add_argument("--page-text", type=Path, help="쪽별 글자 JSON({쪽: 글자}, tables.page_texts). 조각에 없는 면책 날수를 판독의 면책근거쪽에서 찾는다")
    p.add_argument("--out", type=Path, help="값 파일(JSONL). data/crosscheck/에 둘 꼴")
    p.add_argument("--report", type=Path, help="견줌 결과 전체(JSON). 원문을 싣지 않지만 리포 밖에 둔다")
    p.add_argument("--check", type=Path, help="판독 파일 하나의 꼴만 본다(판독자가 내기 전에 스스로 돌린다). 견주지 않는다")
    args = p.parse_args(argv)

    if args.check:
        if len(args.bundles) != 1:
            p.error("--check에는 묶음 하나를 주세요")
        problems = check_file(_load(args.bundles[0]), _load(args.check))
        print("\n".join(problems) if problems else "꼴 문제 없음")
        return 1 if problems else 0

    pages = {int(k): v for k, v in _load(args.page_text).items()} if args.page_text else None
    results = []
    for path in args.bundles:
        bundle = _load(path)
        if args.answers:
            if not args.readers:
                p.error("--answers에는 --readers가 필요합니다")
            files = [args.answers / f"{bundle['묶음']}.{name}.json" for name in args.readers]
        else:
            if len(args.bundles) != 1 or not (args.a and args.b):
                p.error("묶음이 하나일 때 --a, --b를 주거나 --answers와 --readers를 주세요")
            files = [args.a, args.b]
        answers = [_load(f) if f.exists() else {} for f in files]
        names = args.readers or [str(x.get("판독자") or tag) for x, tag in zip(answers, ("A", "B"))]
        if names[0] == names[1]:
            names = [f"{names[0]}1", f"{names[1]}2"]
        results.append(compare_bundle(bundle, dict(zip(names, answers)), names, pages))

    print(summary(results))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as f:
            for r in results:
                for line in r["줄"]:
                    f.write(json.dumps(line, ensure_ascii=False) + "\n")
        print(f"\n값 파일: {args.out}")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
