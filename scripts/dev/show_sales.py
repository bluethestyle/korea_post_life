"""사본(data/snapshot)으로 영업 인사이트(src/postlife/site/sales.py)를 계산해 사람이 읽는 줄로 낸다.

1. 고객군 지도: 행은 고지 이력(입원, 수술만 × 마지막 입원이나 수술 시점), 열은 나이 구간. 칸마다 분류와 대표 종형, 칸의 숫자.
2. 고른 조건의 응대 포인트: 관문, 앞세울 것, 물어올 것 순으로 문장, 예상 질문, 범위 머리말, 근거를 적고, 끝에 뺀 포인트와 사유.

쓰기: .venv/bin/python scripts/dev/show_sales.py [--snapshot data/snapshot] [--age 50] [--sex M] [--grade 3.2.5]
      [--since 2] [--surgery-only] [--renewal 갱신] [--base <종형ID나 종형명에 든 글자>] [--json [파일]]
--grade X.Y.Z는 그 간편고지 약칭의 질문을 통과하는 고객으로 본다: --since가 없으면 since=Y(마지막 입원이나 수술이 Y년보다 오래됨),
--base가 없으면 기준 종형을 그 약칭의 우체국 종형으로 고른다. 기준 종형을 고르지 않으면 지도 칸의 대표 종형, 그것도 없으면
비교표의 처음 기준 종형(compare.default_base)이다. --json은 지도와 포인트 전체를 파일(없으면 표준 출력)로 쓴다.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from postlife.site import compare as C  # noqa: E402
from postlife.site import insights as I  # noqa: E402
from postlife.site import sales as S  # noqa: E402
from postlife.site.model import load  # noqa: E402

SEX = {"M": "남", "F": "여", None: "성별 없음"}


def kind_name(data, vid: str) -> str:
    return f"{data.org_name(data.variants[vid].get('기관코드'))} {data.variants[vid].get('종형명')}"


def named(data, text: str) -> str:
    """사유 글에 든 종형ID를 회사와 종형명으로 바꾼다."""
    for vid in sorted(data.variants, key=len, reverse=True):
        if vid in text:
            text = text.replace(vid, kind_name(data, vid))
    return text


def counts_text(n: dict | None) -> str:
    if n is None:
        return "숫자 없음"
    return f"고유 {n['고유']}, 빈자리 {n['빈자리']}, 못함 {n['못함']}, 나음 {n['나음']}, 대기 {n['대기']}"


def col_name(c: dict) -> str:
    return f"{c['lo']}~{c['hi']}세"


def print_map(data, m: dict) -> None:
    rows, cols = m["행"], m["열"]
    print(f"== 고객군 지도 (성별 {SEX.get(m['성별'], m['성별'])}, 갱신 유형 {m['갱신유형'] or '전체'}, "
          f"{len(rows)}행 {len(cols)}열 {len(rows) * len(cols)}칸)")
    width = max(len(r["이름"]) for r in rows)
    print(" " * (width + 2) + " | ".join(f"{col_name(c):<10}" for c in cols))
    for r, line in zip(rows, m["칸"]):
        print(f"{r['이름']:<{width}}  " + " | ".join(f"{x['분류']:<10}" for x in line))
    print("집계: " + ", ".join(f"{k} {n}" for k, n in m["집계"].items()))
    print()
    print("칸 자세히(대표 종형, 칸의 숫자, 자료 없는 회사)")
    for r, line in zip(rows, m["칸"]):
        print(f"- {r['이름']}")
        for c, x in zip(cols, line):
            if x["대표"]:
                rep = kind_name(data, x["대표"]) + " 대 " + (", ".join(kind_name(data, v) for v in x["상대대표"].values()) or "열린 상대 없음")
            else:
                rep = "우리 대표 없음"
            states = ", ".join(f"{data.org_name(o)} {s}" for o, s in x["회사"].items())
            tail = f" | 자료 없음: {', '.join(data.org_name(o) for o in x['자료없음'])}" if x["자료없음"] else ""
            note = f" | {x['안내']}" if x.get("안내") else ""
            print(f"    {col_name(c)}: {x['분류']} | {states} | {rep} | {counts_text(x['수'])}{tail}{note}")


def evidence_text(data, ev: list[dict], check: bool) -> str:
    parts = []
    for e in ev:
        page = f"{e['쪽']}쪽" if e["쪽"] is not None else "쪽 없음"
        name = data.benefits[e["급부ID"]]["원시급부명"] if e.get("급부ID") else None
        parts.append(f"{kind_name(data, e['종형ID'])} {e['문서'] or '문서 모름'} {page}" + (f" '{name}'" if name else ""))
    return "; ".join(parts) + (" (원문 대조 필요)" if check else "")


def profile_text(p: S.Profile) -> str:
    bits = [f"{p.age}세" if p.age is not None else "나이 없음", SEX.get(p.sex, p.sex)]
    if p.since is None:
        bits.append("입원, 수술 이력 없음")
    else:
        bits.append(f"{'입원 없이 수술만' if p.surgery_only else '입원'}, 마지막이 {p.since:g}년보다 오래됨")
    bits.append(f"갱신 유형 {p.renewal or '전체'}")
    return ", ".join(bits)


def print_points(data, r: dict) -> None:
    base = r["기준종형ID"]
    print(f"== 응대 포인트: 기준 {S.full_name(data, base)} [{base}]")
    print(f"조건: {profile_text(r['조건'])}")
    g = r["관문"]
    limit = f", 한도 {g['한도만원']:g}만원" if g["한도만원"] is not None else ""
    print(f"기준 종형의 관문: {g['상태']} (질문 {g['질문']}, 나이 {g['나이']}{limit})")
    gate = S.gate(data, r["조건"])
    for org, x in gate["회사"].items():
        opened = [data.variants[y["종형ID"]].get("종형명") for y in x["종형"] if y["상태"] == S.OPEN]
        print(f"  {data.org_name(org)}: {x['상태']}" + (f" (열린 종형 {', '.join(opened)})" if opened else ""))
    print(f"범위: {r['범위']['문장']}")
    print("집계: " + ", ".join(f"{c} {n}" for c, n in r["집계"].items()) + f" / 뺀 포인트 {len(r['뺀포인트'])}")
    for i, x in enumerate(r["포인트"], 1):
        score = x["점수"] if x["점수"] is not None else "-"
        flags = [f"목적 {', '.join(x['목적'])}" if x["목적"] else None, "구조 다름" if x["구조다름"] else None,
                 "브리핑 제외" if not x["브리핑"] else None]
        print(f"{i:>2}. [{x['종류']} {x['세부']} {x['세부이름']}] 점수 {score}" + "".join(f" | {f}" for f in flags if f))
        if x["질문"]:
            print(f"    예상 질문: {x['질문']}")
        print(f"    {'답' if x['질문'] else '문장'}: {x['문장']}")
        print(f"    머리말: {x['머리말']} ({x['회사수']})")
        if x.get("주의"):
            print(f"    주의: {x['주의']}")
        if x.get("좁은담보"):
            print(f"    우리 좁은 담보: {', '.join(x['좁은담보'])}")
        if x.get("꼬리표"):
            print(f"    꼬리표: {', '.join(x['꼬리표'])}")
        print(f"    근거: {evidence_text(data, x['근거'], x['원문대조'])}")
    if r["뺀포인트"]:
        print("뺀 포인트:")
        for x in r["뺀포인트"]:
            name = f" {x['표준담보명']}" if x["표준담보명"] else ""
            print(named(data, f"  - [{x['세부']} {x['세부이름']}]{name} | {x['사유']}"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path, default=ROOT / "data" / "snapshot", help="사본 폴더")
    p.add_argument("--age", type=int, help="고객 나이")
    p.add_argument("--sex", choices=("M", "F"), default="M", help="성별(지도와 포인트 모두)")
    p.add_argument("--grade", help="간편고지 약칭(예: 3.2.5). 그 질문을 통과하는 이력으로 보고, 그 약칭의 우체국 종형을 기준으로 고른다")
    p.add_argument("--since", type=float, help="마지막 입원이나 수술이 몇 년 전보다 오래됐나(0.25는 3개월). 주지 않으면 이력 없음")
    p.add_argument("--surgery-only", action="store_true", help="그 이력이 입원 없이 수술만")
    p.add_argument("--renewal", choices=("갱신", "비갱신"), help="갱신 유형 거르개(지도와 관문)")
    p.add_argument("--base", help="기준 종형(종형ID, 종형명, 공시상품명 가운데 하나에 든 글자)")
    p.add_argument("--json", nargs="?", const="-", help="지도와 포인트 전체를 JSON으로 쓸 파일(없으면 표준 출력)")
    args = p.parse_args()

    data = load(args.snapshot)
    _, bases = I.base_variants(data)
    since = args.since
    base = None
    if args.grade:
        if since is None:
            parts = args.grade.split(".")
            if len(parts) != 3 or not parts[1].isdigit():
                print(f"간편고지 약칭은 3.2.5 꼴이어야 합니다: {args.grade}", file=sys.stderr)
                return 1
            since = float(parts[1])
        graded = [b for b in bases if data.variants[b].get("간편고지약칭") == args.grade]
        base = graded[0] if graded else None
    if args.base:
        hit = [b for b in bases if any(args.base in str(data.variants[b].get(c) or "") for c in ("종형ID", "종형명", "공시상품명"))]
        if not hit:
            print(f"'{args.base}'가 든 판매 중인 우체국 종형이 없습니다.", file=sys.stderr)
            return 1
        base = hit[0]
    profile = S.Profile(age=args.age, sex=args.sex, since=since, surgery_only=args.surgery_only, renewal=args.renewal)

    analysis = I.analyze(data)
    ctx = S._Ctx(data, analysis, None)
    smap = S.segment_map(data, args.sex, args.renewal, analysis, ctx=ctx)
    if base is None:
        base = S.cell(data, profile, analysis, ctx=ctx)["대표"] or C.default_base(data, bases)
    result = S.points(data, base, profile, analysis, ctx=ctx)

    if args.json:
        text = json.dumps(S.to_json({"자료시각": data.meta.get("snapshot_at"), "지도": smap, "포인트": result}),
                          ensure_ascii=False, indent=1)
        if args.json == "-":
            print(text)
            return 0
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")

    print(f"사본 시각 {data.meta.get('snapshot_at')}, 판매 중인 우체국 기준 종형 {len(bases)}개")
    print()
    print_map(data, smap)
    print()
    print_points(data, result)
    if args.json:
        print(f"\nJSON: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
