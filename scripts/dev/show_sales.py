"""사본(data/snapshot)으로 영업 인사이트(src/postlife/site/sales.py)를 계산해 사람이 읽는 줄로 낸다.

1. 고객군 지도: 행은 고지 이력(입원, 수술만 × 마지막 입원이나 수술 시점), 열은 나이 구간. 칸마다 라벨, 보조, 닫힌 사유, 대표 종형, 칸의 숫자.
2. 고른 조건의 영업 인사이트: 다섯 분류와 세부, 분석 문장, 카드 문답, 범위 머리말, 근거를 적고, 끝에 뺀 포인트와 사유.

쓰기: .venv/bin/python scripts/dev/show_sales.py [--snapshot data/snapshot] [--age 50] [--sex M] [--grade 3.2.5]
      [--since 2] [--surgery-only] [--renewal 갱신] [--base <종형ID나 종형명에 든 글자>] [--json [파일]]
      [--brief] [--caution] [--revision] [--journey] [--limits] [--pending]
--grade X.Y.Z는 그 간편고지 약칭의 질문을 통과하는 고객으로 본다: --since가 없으면 since=Y(마지막 입원이나 수술이 Y년보다 오래됨),
--base가 없으면 기준 종형을 그 약칭의 우체국 종형으로 고른다. 기준 종형을 고르지 않으면 지도 칸의 대표 종형, 그것도 없으면
비교표의 처음 기준 종형(compare.default_base)이다. --json은 지도와 포인트 전체를 파일(없으면 표준 출력)로 쓴다.

분석 담당자용 보기(하나라도 주면 지도와 포인트 대신 고른 보기만 낸다. 기준 종형은 위와 같이 고른다)
--brief     브리핑 다섯 줄. 나이와 이력을 주지 않으면 기준값 탭의 대표 조건(이력 없음)으로 본다
--caution   단정 주의 목록(조건이 다른 특약 함께 판매, 지급 형태 다름)
--revision  개정 검토 목록(보장 중분류로 접음)과 우체국 직전 개정 변동
--journey   치료 여정 격자(보장 대분류 × 급부유형 다섯, 기준 종형과 맞붙는 종형)
--limits    우체국 판매 중 종형의 나이 구간별 주계약 최대 가입금액 표
--pending   검토 대기로 뺀 비교쌍의 보장 대분류별 요약
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


def counts_text(n: dict) -> str:
    """칸의 분류수(다섯 분류와 검토 대기). 견줄 대표가 없어 비운 값(None)은 적지 않는다."""
    shown = [f"{k} {v}" for k, v in n.items() if v is not None]
    tail = "" if n.get(S.STRENGTH) is not None else " (견줄 대표 없음)"
    return ", ".join(shown) + tail


def col_name(c: dict) -> str:
    return f"{c['lo']}~{c['hi']}세"


def print_map(data, m: dict) -> None:
    rows, cols = m["행"], m["열"]
    print(f"== 고객군 지도 (성별 {SEX.get(m['성별'], m['성별'])}, 갱신 유형 {m['갱신유형'] or '전체'}, "
          f"{len(rows)}행 {len(cols)}열 {len(rows) * len(cols)}칸)")
    width = max(len(r["이름"]) for r in rows)
    print(" " * (width + 2) + " | ".join(f"{col_name(c):<10}" for c in cols))
    for r, line in zip(rows, m["칸"]):
        print(f"{r['이름']:<{width}}  " + " | ".join(f"{x['라벨']:<10}" for x in line))
    print("집계: " + ", ".join(f"{S.LABELS[k]} {n}" for k, n in m["집계"].items()))
    print()
    print("칸 자세히(라벨과 보조, 닫힌 사유, 대표 종형, 칸의 숫자, 자료 없는 회사)")
    for r, line in zip(rows, m["칸"]):
        print(f"- {r['이름']}")
        for c, x in zip(cols, line):
            if x["대표"]:
                rep = kind_name(data, x["대표"]) + " 대 " + (", ".join(kind_name(data, v) for v in x["상대대표"].values()) or "열린 상대 없음")
            else:
                rep = "우리 대표 없음"
            states = ", ".join(f"{data.org_name(o)} {s}" for o, s in x["회사"].items())
            tail = f" | 자료 없음: {', '.join(data.org_name(o) for o in x['자료없음'])}" if x["자료없음"] else ""
            label = x["라벨"] + (f"({x['보조']})" if x["보조"] else "")
            reasons = f" | 닫힌 사유: {', '.join(x['닫힌사유'])}" if x["닫힌사유"] else ""
            gated = x.get("관문만수집") or []
            gated = (" | 열린 상대가 관문전용뿐: " + ", ".join(f"{y['이름']}({y['안내']})" for y in gated)) if gated else ""
            print(f"    {col_name(c)}: {label}{reasons} | {states} | {rep} | {counts_text(x['분류수'])}{tail}{gated}")


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
    print("분류: " + ", ".join(f"{c} {n}" for c, n in r["분류집계"].items()))
    print("세부: " + ", ".join(f"{c} {n}" for c, n in r["집계"].items()) + f" / 뺀 포인트 {len(r['뺀포인트'])}")
    for i, x in enumerate(r["포인트"], 1):
        score = x["점수"] if x["점수"] is not None else "-"
        flags = [f"목적 {', '.join(x['목적'])}" if x["목적"] else None, "구조 다름" if x["구조다름"] else None,
                 "브리핑 제외" if not x["브리핑"] else None, x["원문대조글"]]
        print(f"{i:>2}. [{x['분류']} {x['세부']} {x['세부이름']}] 점수 {score}" + "".join(f" | {f}" for f in flags if f))
        print(f"    문장: {x['문장']}")
        if x["카드질문"]:
            print(f"    카드 질문: {x['카드질문']}")
        if x["카드답"] != x["문장"]:
            print(f"    카드 답: {x['카드답']}")
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


# ---------- 분석 담당자용 보기 ----------
def print_brief(lines: list[dict]) -> None:
    print("== 브리핑 다섯 줄")
    for x in lines:
        check = f" [{x['원문대조글']}]" if x.get("원문대조글") else ""
        print(f"({x['줄']}) [{x['범위']}] → {x['갈곳']}{' ' + x['구역'] if x.get('구역') else ''}{check}")
        print(f"    {x['문장']}")


def print_caution(data, items: list[dict]) -> None:
    print(f"== 단정 주의 목록 {len(items)}건 (" + ", ".join(
        f"{k} {sum(1 for x in items if x['종류'] == k)}" for k in (S.CAUTION_OTHER, S.CAUTION_PAY)) + ")")
    for i, x in enumerate(items, 1):
        print(f"{i:>2}. [{x['종류']}] {x['문장']}")
        print(f"    머리말: {x['머리말']}")
        print(f"    근거: " + "; ".join(f"{kind_name(data, e['종형ID'])} {e['문서']} {e['쪽']}쪽({e['구분']})" for e in x["근거"]))


def print_revision(data, groups: list[dict], rev: dict) -> None:
    total = sum(g["담보수"] for g in groups)
    print(f"== 개정 검토 목록: 보장 중분류 {len(groups)}묶음, 담보 {total}개")
    for g in groups:
        print(f"- {g['대분류']} / {g['중분류']}: {g['담보수']}개(좁은 담보만 {g['좁은담보만수']})")
        for d in g["담보"]:
            pages = ", ".join(f"{kind_name(data, e['종형ID'])} {e['쪽']}쪽" for e in d["근거"])
            print(f"    {d['담보']} | 가진 상대 {d['가진상대수']}곳({', '.join(d['가진상대'])}) | 우리 {d['우리상태']} | {pages}")
    n = rev["수"]
    print()
    print(f"== 우체국 직전 개정 변동: 담보 {n['전체']}건(신설 {n['신설']}, 변경 {n['변경']}, 종료 {n['종료']}), 짝 {len(rev['짝'])}개")
    for x in rev["담보"]:
        print(f"  {x['종류']} {x['담보']} ({', '.join(x['항목'])}) 종형 {len(x['종형ID'])}개")


def print_journey(grid: dict) -> None:
    cols = grid["열"]
    print("== 치료 여정 격자(표준담보 보유 수)")
    for r in grid["종형"]:
        print(f"- {r['이름']} (전체 {r['전체']}, 기타 {r['기타']})")
        print("    " + f"{'':<8}" + "".join(f"{c:>5}" for c in cols))
        for m in grid["행"]:
            print("    " + f"{m:<8}" + "".join(f"{r['칸'][m][c]:>5}" for c in cols))
        print("    " + f"{'합계':<8}" + "".join(f"{r['합계'][c]:>5}" for c in cols))


def print_limits(rows: list[dict]) -> None:
    print("== 나이 구간별 주계약 최대 가입금액(만원)")
    for r in rows:
        segs = ", ".join(f"{s['lo']}~{s['hi']}세 {s['max']:g}" + (" (검토 대기)" if s["pend"] else "")
                         if s["max"] is not None else f"{s['lo']}~{s['hi']}세 금액 없음" for s in r["구간"]["M"])
        print(f"- {r['이름']} [{r['심사']}, {r['갱신']}]{'' if r['성별같음'] else ' (성별에 따라 다름. 남 기준)'}: {segs}")


def print_pending(data, s: dict) -> None:
    print(f"== 보류 요약: 공통 담보 {s['공통담보쌍']}쌍 가운데 검토 대기 {s['뺀쌍']}쌍 "
          f"(매핑 대기 {s['사유별']['매핑 대기']}, 작업 로그 대기 {s['사유별']['작업 로그 대기']})")
    for r in s["대분류"]:
        per = ", ".join(f"{kind_name(data, p)} {n}" for p, n in r["상대별"].items())
        print(f"  {r['대분류']}: 공통 {r['공통담보쌍']}, 뺀 {r['뺀쌍']}, 견준 {r['견준쌍']} (뺀 쌍의 상대별: {per})")


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
    p.add_argument("--brief", action="store_true", help="브리핑 다섯 줄")
    p.add_argument("--caution", action="store_true", help="단정 주의 목록")
    p.add_argument("--revision", action="store_true", help="개정 검토 목록과 직전 개정 변동")
    p.add_argument("--journey", action="store_true", help="치료 여정 격자")
    p.add_argument("--limits", action="store_true", help="나이 구간별 주계약 최대 가입금액 표")
    p.add_argument("--pending", action="store_true", help="검토 대기로 뺀 비교쌍 요약")
    args = p.parse_args()
    views = args.brief or args.caution or args.revision or args.journey or args.limits or args.pending

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
    if base not in bases:          # 지도 칸의 대표가 판매를 마친 종형일 수는 없지만, 기준 종형이 아니면 처음 기준 종형으로 본다
        base = C.default_base(data, bases)

    if views:
        if args.age is None and since is None:
            profile = S.representative_profile(data)
        result = S.points(data, base, profile, analysis, ctx=ctx)
        print(f"사본 시각 {data.meta.get('snapshot_at')}, 기준 {S.full_name(data, base)} [{base}], 조건 {profile_text(profile)}")
        cautions = S.caution(data, base, None, ctx=ctx, pts=result)
        grid = S.journey(data, base, result["맞붙는종형"], ctx=ctx)
        blocks = []
        if args.brief:
            # (가)는 전체 고객군 기준(성별 남, 갱신 거르개 전체)이라 --sex, --renewal과 무관하게 briefing이 지도를 그린다
            blocks.append(lambda: print_brief(S.briefing(data, base, profile, None, ctx=ctx, pts=result, cautions=cautions,
                                                         grid=grid)))
        if args.caution:
            blocks.append(lambda: print_caution(data, cautions))
        if args.revision:
            blocks.append(lambda: print_revision(data, S.revision_candidates(data, result), S.revision_summary(data)))
        if args.journey:
            blocks.append(lambda: print_journey(grid))
        if args.limits:
            blocks.append(lambda: print_limits(S.limit_steps(data)))
        if args.pending:
            blocks.append(lambda: print_pending(data, S.pending_summary(data, base, None, ctx=ctx)))
        for block in blocks:
            print()
            block()
        return 0
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
