"""사본(data/snapshot)으로 시사점(src/postlife/site/insights.py)을 계산해 사람이 읽는 줄로 낸다.

판매 중인 우체국 종형마다 맞붙는 종형, 유형별 시사점 수와 뺀 수, 조건 우열 분포를 적고, 시사점을 우선순위 순으로 한 줄에 하나씩 낸다.
줄마다 점수, 유형, 담보 이름과 분야, 상대 회사, 항목별 값, 근거 급부의 원시급부명과 문서 쪽을 적는다.
끝에 회사별 지급 형태 꼬리표가 붙는 비율과, 검토 대기로 뺀 시사점을 적는다.

쓰기: .venv/bin/python scripts/dev/show_insights.py [--snapshot data/snapshot] [--base <종형명에 든 글자>] [--json <파일>]
--base는 종형명, 공시상품명, 종형ID 가운데 하나에 그 글자가 든 기준 종형만 고른다. --json은 계산 결과 전체를 파일로 쓴다.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from postlife.site import insights as I  # noqa: E402
from postlife.site.model import load  # noqa: E402


def evidence(data, bid: str, who: str) -> str:
    b = data.benefits.get(bid)
    if b is None:
        return f"{who} {bid}(사본에 없음)"
    page = b.get("근거문서쪽수")
    where = f"{b.get('근거문서종류') or '문서 모름'} {page}쪽" if page is not None else f"{b.get('근거문서종류') or '문서 모름'} 쪽 모름"
    return f"{who} '{b.get('원시급부명')}'({where})"


def evidence_text(data, ins: dict, org) -> str:
    parts = [evidence(data, bid, "기준") for bid in ins["근거"].get("기준", [])]
    for vid, bids in ins["근거"].get("비교", {}).items():
        parts += [evidence(data, bid, org(vid)) for bid in bids]
    return "; ".join(parts) if parts else "근거 급부 없음"


def cover_text(item: dict) -> str:
    if item["덮임"] == "없음":
        narrow = f"(좁은 담보 {', '.join(item['좁은담보'])}만 가짐)" if item["좁은담보"] else ""
        return "없음" + narrow
    text = f"{item['덮임']} {', '.join(item['덮는담보'])}"
    if item["일부만"]:
        text += f"(일부만, 빠진 부분 담보 {', '.join(item['빠진부분담보'])})"
    return text


def item_text(item: dict) -> str:
    out = f"{item['항목']} {item['기준']} 대 {item['상대']}({item['판정']})"
    return out + (f"[{item['사유']}]" if item.get("사유") else "")


def amount_text(a: dict) -> str:
    if a["지급액"] is not None:
        return f"지급액 {a['지급액']}(비교표 {a['비교표부호']})"
    return f"지급액 판정 없음({a['사유']})"


def line(data, ins: dict, org) -> str:
    kind = ins["유형"] + (f"({ins['방향']})" if ins["방향"] else "")
    head = f"  [{ins['점수']:>3}] {kind} | {ins['표준담보명']} ({ins['보장대분류']}/{ins['보장중분류']})"
    v = ins["변수"]
    if ins["유형"] == I.GAP:
        body = f"{', '.join(v['가진회사'])}가 가짐"
        if v["기준좁은담보"]:
            body += f", 기준은 좁은 담보 {', '.join(v['기준좁은담보'])}만 가짐"
    elif ins["유형"] == I.SCOPE and ins["방향"] == I.MISSING_SIDE:
        body = f"{', '.join(v['가진회사'])}가 가짐, 기준은 {cover_text(ins['항목'][0])}로 덮음"
    elif ins["유형"] == I.SCOPE:
        body = "기준만 이 담보로 가짐, " + ", ".join(f"{org(it['종형ID'])} {cover_text(it)}" for it in ins["항목"])
    elif ins["유형"] == I.UNIQUE:
        body = f"{', '.join(v['없는회사'])} 모두 없음(넓은 담보, 부분 담보로도 없음)"
    else:
        chunks = []
        for vid in ins["비교종형ID"]:
            items = [i for i in ins["항목"] if i["종형ID"] == vid]
            text = f"대 {org(vid)}: " + ", ".join(item_text(i) for i in items) + f", {amount_text(ins['지급액'][vid])}"
            others = ins.get("대표밖조건다른줄", {}).get(vid, {})
            if others.get("기준") or others.get("상대"):
                text += f", 대표 밖 조건이 다른 줄 기준 {others['기준']}줄, {org(vid)} {others['상대']}줄"
            chunks.append(text)
        body = " / ".join(chunks)
    tail = ""
    if ins.get("뺀비교종형"):
        tail = " | 뺀 비교: " + ", ".join(f"{org(r['종형ID'])}({'; '.join(r['사유'])})" for r in ins["뺀비교종형"])
    return f"{head} | {body} | 근거: {evidence_text(data, ins, org)}{tail}"


def named(data, text: str) -> str:
    """사유 글에 든 종형ID를 회사와 종형명으로 바꾼다."""
    for vid in sorted(data.variants, key=len, reverse=True):
        if vid in text:
            text = text.replace(vid, f"{data.org_name(data.variants[vid].get('기관코드'))} {data.variants[vid].get('종형명')}")
    return text


def counts(d: dict) -> str:
    return ", ".join(f"{k} {n}" for k, n in d.items())


def full_name(v: dict) -> str:
    """회사, 공시상품명, 종형명. 공시상품명에 종형명이 이미 들어 있으면 한 번만 적는다."""
    product, kind = str(v.get("공시상품명") or ""), str(v.get("종형명") or "")
    return f"{v['회사']} {product}" + ("" if kind and kind in product else f" {kind}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path, default=ROOT / "data" / "snapshot", help="사본 폴더")
    p.add_argument("--base", help="기준 종형을 고르는 글자(종형명, 공시상품명, 종형ID 가운데 하나에 든 글자)")
    p.add_argument("--json", type=Path, help="계산 결과 전체를 쓸 JSON 파일")
    args = p.parse_args()

    data = load(args.snapshot)
    _, bases = I.base_variants(data)
    if args.base:
        bases = [b for b in bases if any(args.base in str(data.variants[b].get(c) or "") for c in ("종형명", "공시상품명", "종형ID"))]
        if not bases:
            print(f"'{args.base}'가 든 판매 중인 우체국 종형이 없습니다.", file=sys.stderr)
            return 1
    result = I.analyze(data, base_ids=bases)
    org = lambda vid: data.org_name(data.variants[vid].get("기관코드"))
    variant_name = lambda vid: f"{org(vid)} {data.variants[vid].get('종형명')}"

    s = result["요약"]
    print(f"사본 시각 {result['자료시각']}, 담보관계 {result['담보관계수']}줄"
          + (f", 사전과 맞지 않는 관계 {len(result['담보관계확인'])}건" if result["담보관계확인"] else ""))
    print(f"기준 종형 {s['기준종형수']}개, 시사점 {s['시사점수']}건({counts(s['유형별'])}), "
          f"뺀 시사점({counts(s['뺀수'])}), 견준 공통 담보 쌍 {s['비교쌍']}, 그 가운데 검토 대기로 뺀 쌍 {s['뺀비교쌍']}")
    for b in result["기준"]:
        print()
        print(f"== 기준 종형: {full_name(b)} [{b['종형ID']}] (보유 담보 {b['보유담보수'][b['종형ID']]}개)")
        print("맞붙는 종형: " + ", ".join(f"{full_name(p)} [{p['종형ID']}] (보유 담보 {b['보유담보수'][p['종형ID']]}개)"
                                       for p in b["맞붙는종형"]))
        print(f"시사점: {counts(b['유형별'])} / 뺀 수: {counts(b['뺀수'])} / 공통 담보 쌍 {b['비교쌍']}, 뺀 쌍 {b['뺀비교쌍']}")
        for vid, spread in b["조건우열분포"].items():
            print(f"조건 우열 분포(기준 쪽 판정, 대 {variant_name(vid)}, 뺀 쌍 제외): {counts(spread)}")
        for ins in b["시사점"]:
            print(named(data, line(data, ins, org)))
        if b["보류비교"]:
            print("  조건 우열 판정 보류(시사점으로 세지 않음):")
            for x in b["보류비교"]:
                rest = f", 보류 밖 판정 {x['보류밖판정']}" if x["보류밖판정"] else ""
                diffs = ", ".join(item_text(i) for i in x["항목"] if i["판정"] != I.SAME)
                print(f"    - {x['표준담보명']} | 대 {org(x['비교종형ID'])} | {diffs}{rest}")
        if b["뺀시사점"]:
            print("  뺀 시사점(검토 대기):")
            for x in b["뺀시사점"]:
                kind = x["유형"] + (f"({x['방향']})" if x["방향"] else "")
                print(named(data, f"    - {kind} | {x['표준담보명']} | 상대 {', '.join(org(v) for v in x['비교종형ID'])} | {'; '.join(x['사유'])}"))

    print()
    print("지급 형태 꼬리표(회사별, sys_급부 전 줄. 비율은 문구가 있는 줄 가운데 꼬리표가 붙은 줄)")
    for code, st in s["지급형태꼬리표"].items():
        ratio = f"{st['꼬리표붙음'] * 100 / st['문구있음']:.1f}%" if st["문구있음"] else "-"
        print(f"  {st['회사']}: 급부 {st['급부']}줄, 문구 있음 {st['문구있음']}, 꼬리표 붙음 {st['꼬리표붙음']}({ratio}), 읽지 못함 {st['읽지못함']}, "
              f"서로 다른 문구 {st['서로다른문구']} 가운데 꼬리표 붙음 {st['꼬리표붙은서로다른문구']} / 종류별 {counts(st['종류별'])}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nJSON: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
