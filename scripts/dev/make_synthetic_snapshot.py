"""가상 사본: 비교 회사가 19곳(우체국과 상대 18곳)으로 늘어도 계산과 화면이 견디는지 시험하는 자료를 만든다.

쓰기: python scripts/dev/make_synthetic_snapshot.py [--snapshot data/snapshot] [--out out/synthetic_snapshot]
      [--life 9] [--nonlife 8]

- 우체국, 한화생명, 삼성화재 행은 그대로 둔다. 한화생명을 본떠 가상 생명보험사(--life, 기본 9곳), 삼성화재를 본떠 가상
  손해보험사(--nonlife, 기본 8곳)를 더한다. 기본값이면 상대가 생명보험 10곳과 손해보험 9곳, 모두 19곳이다(docs/planning.md
  2.1 의 정밀 비교 대상 수. 우체국을 더하면 20곳).
- 가상 회사는 기관코드 SYNLIFE01, SYNFIRE01 따위이고 이름은 "가상생명 01", "가상화재 01" 따위다. 공시상품명의 회사 이름과
  상품 이름도 "가상"이 든 이름으로 바꾼다. 실제 회사 이름은 쓰지 않는다(다 만든 뒤 검사한다).
- ID 는 본뜬 회사의 기관코드 접두어만 가상 회사의 것으로 바꾼다(종형ID, 특약ID, 급부ID, 조건행ID, 제약ID, 개정판ID, 모상품ID,
  종형계보키). 급부 → 특약 → 종형, 매핑 → 급부, 가입조건과 결합제약 → 종형과 특약이 그대로 이어진다.
  요약서해시, 사업방법서해시, 약관별표해시도 회사마다 바꿔 본뜬 회사의 작업 로그(검토 대기)가 옮겨 붙지 않게 한다.
- 회사마다 조금씩 다르게 만든다. 난수 씨앗은 기관코드에서 정해 늘 같은 결과가 나온다. 값은 사본에 이미 있는 값에서만 고른다.
  - 특약(계보키)과 급부를 뺀다. 회사마다 비율 r(10~40%)을 정해 특약은 r/2, 남은 급부는 r/2 를 뺀다(급부로 치면 약 r).
    주계약은 빼지 않는다. 같은 회사의 종형끼리는 같은 특약과 급부를 뺀다.
  - 간편 종형의 고지 유형: 회사마다 가장 긴 입원수술 기간(그보다 긴 간편 종형을 뺀다)과, 생명보험이면 0년 유형을 둘지 정한다.
    고지수술포함여부, 고지중대질병 수와 목록, 고지소견범위를 사본에 있는 값 가운데서 회사마다 고른다.
  - 면책과 감액: 회사마다 비율 q(10~30%)의 급부(계보로 같은 급부)에서 면책기간일수와 감액 열을, 사본에서 같은 확정 표준담보를
    가진 급부들에 있는 값 가운데 하나로 바꾼다.
  - 가입나이: 회사마다 -3~3세(0 제외)를 골라 가입조건 행의 최저, 최고 가입나이를 함께 옮긴다. 사본의 가장 낮은 최저 나이와
    가장 높은 최고 나이 밖으로 나가지 않게 자른다.
- 작업 로그는 화면 크기만 키우므로 가상 회사 것은 만들지 않는다(가상 회사에는 작업 로그 검토 대기가 없다).
- meta.json 에 가상자료 표시, 기관이름(가상 회사 이름 표), 기관업권(생명보험, 손해보험)을 싣는다. 화면과 문장은 이 이름 표를 먼저
  읽는다(site/model.py 의 Data.org_name, Data.org_sector).
- 다 만든 뒤 validate.check_rows 로 탭마다 점검하고, 탭 사이 이음이 끊기지 않았는지 본다. 문제가 있으면 쓰지 않고 멈춘다.

출력 폴더는 저장소에 커밋하지 않는다(.gitignore 의 out/). 공개 배포되는 site/ 아래에 쓰지 않는다.
출력 폴더가 이미 있으면 비었거나 이 도구가 쓴 가상 사본(meta.json 의 가상자료 표시와 탭 파일만 든 폴더)일 때만 그 파일을
지우고 다시 쓴다. 그 밖의 폴더(--out data 따위)는 지우지 않고 멈춘다.
모델 호출, 시트 쓰기는 하지 않는다. 입력 사본은 읽기만 한다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from postlife import config  # noqa: E402
from postlife.schema import TABS  # noqa: E402
from postlife.snapshot import read_snapshot, to_jsonl  # noqa: E402
from postlife.validate import check_rows  # noqa: E402

LIFE_SRC, NONLIFE_SRC = "HANWHALIFE", "SAMSUNGFIRE"
LIFE, NONLIFE = "생명보험", "손해보험"
NOTICE = "가상 자료(화면 배치 시험용, 실제 회사 자료 아님)"
FAKE_URL = "가상 자료(공시 주소 없음)"
# 공시상품명에서 바꾸는 상품 이름(회사 이름은 따로 바꾼다)
BRANDS = {"시그니처 H통합보험": "가상통합보험", "간편보험 새로고침": "가상간편보험", "건강보험 THE FIT 파트너": "가상건강보험"}
# 기관코드 접두어를 바꾸는 열(탭마다)
ID_COLUMNS = {
    "sys_상품종형": ("종형ID", "개정판ID", "모상품ID", "종형계보키"),
    "sys_특약": ("특약ID", "종형ID"),
    "sys_급부": ("급부ID", "특약ID"),
    "hum_담보매핑": ("급부ID",),
    "sys_가입조건": ("조건행ID", "종형ID", "특약ID"),
    "sys_결합제약": ("제약ID", "종형ID", "기준특약ID", "대상특약ID"),
}
HASH_COLUMNS = ("요약서해시", "사업방법서해시", "약관별표해시")
WAIT_RED = ("면책기간일수", "감액개월1", "감액지급률1", "감액개월2", "감액지급률2")
CONFIRMED = {"자동확정", "승인", "수정"}


def companies(n_life: int, n_nonlife: int) -> list[dict]:
    out = [{"code": f"SYNLIFE{i:02d}", "name": f"가상생명 {i:02d}", "sector": LIFE, "src": LIFE_SRC} for i in range(1, n_life + 1)]
    out += [{"code": f"SYNFIRE{i:02d}", "name": f"가상화재 {i:02d}", "sector": NONLIFE, "src": NONLIFE_SRC}
            for i in range(1, n_nonlife + 1)]
    return out


def rng_of(code: str) -> random.Random:
    return random.Random(int.from_bytes(hashlib.sha256(code.encode("utf-8")).digest()[:8], "big"))


def swap_prefix(value, src: str, dst: str):
    if isinstance(value, str) and value.startswith(src + "_"):
        return dst + value[len(src):]
    return value


def org_of_id(value: str) -> str:
    return str(value).split("_", 1)[0]


class Source:
    """입력 사본에서 본뜰 회사의 행과 값의 범위."""

    def __init__(self, tables: dict[str, list[dict]]):
        self.t = tables
        self.variants = {r["종형ID"]: r for r in tables["sys_상품종형"]}
        self.riders = {r["특약ID"]: r for r in tables["sys_특약"]}
        self.mapping = {r["급부ID"]: r for r in tables["hum_담보매핑"]}
        cond = tables["sys_가입조건"]
        self.age_lo = min(r["최저가입나이"] for r in cond)
        self.age_hi = max(r["최고가입나이"] for r in cond)
        # 같은 확정 표준담보를 가진 급부들에 있는 (면책, 감액) 값
        self.terms: dict[str, list[tuple]] = defaultdict(list)
        for b in tables["sys_급부"]:
            m = self.mapping.get(b["급부ID"])
            if m and m.get("검토상태") in CONFIRMED and m.get("확정표준담보ID"):
                key = tuple(b.get(c) for c in WAIT_RED)
                if key not in self.terms[m["확정표준담보ID"]]:
                    self.terms[m["확정표준담보ID"]].append(key)
        simple = [v for v in tables["sys_상품종형"] if v.get("심사유형") == "간편심사"]
        self.surgery = sorted({v["고지수술포함여부"] for v in simple if v.get("고지수술포함여부") is not None})
        self.opinion = sorted({v["고지소견범위"] for v in simple if v.get("고지소견범위")})
        self.diseases = sorted({(v["고지중대질병수"], v["고지중대질병목록"]) for v in simple
                                if v.get("고지중대질병수") is not None and v.get("고지중대질병목록")})


def build_company(src: Source, comp: dict) -> dict[str, list[dict]]:
    """본뜬 회사(comp["src"])의 행을 가상 회사의 행으로 옮긴다. 회사마다 다르게 고친다(모듈 설명)."""
    rng = rng_of(comp["code"])
    org, code = comp["src"], comp["code"]
    real_name = config.INSTITUTIONS[org]
    t = src.t
    variants = [v for v in t["sys_상품종형"] if v["기관코드"] == org]

    # 고지 유형: 가장 긴 입원수술 기간과 0년 유형
    years = sorted({v["고지입원수술년수"] for v in variants if v.get("심사유형") == "간편심사" and v.get("고지입원수술년수")})
    cap = rng.choice([y for y in years if y >= 3] or years)
    keep_zero = comp["sector"] == NONLIFE or rng.random() < 0.5
    lowest = min(years)
    floor = lowest if comp["sector"] == LIFE or rng.random() < 0.6 else min(y for y in years if y > lowest)

    def kept(v: dict) -> bool:
        if v.get("심사유형") != "간편심사":
            return True
        y = v.get("고지입원수술년수")
        if y == 0:
            return keep_zero
        return y is None or floor <= y <= cap

    variants = [v for v in variants if kept(v)]
    vids = {v["종형ID"] for v in variants}
    surgery = rng.choice(src.surgery) if src.surgery else None
    opinion = rng.choice(src.opinion) if src.opinion else None
    disease = rng.choice(src.diseases) if src.diseases else None

    # 특약(계보키)과 급부 빼기
    rate = rng.uniform(0.10, 0.40)
    riders = [r for r in t["sys_특약"] if r["종형ID"] in vids]
    lineages = sorted({r["특약계보키"] for r in riders if r["담보구분"] != "주계약"})
    dropped_lineages = {k for k in lineages if rng.random() < rate / 2}
    riders = [r for r in riders if r["특약계보키"] not in dropped_lineages]
    tids = {r["특약ID"]: r for r in riders}
    benefits = [b for b in t["sys_급부"] if b["특약ID"] in tids]

    def ben_key(b: dict) -> tuple:
        return (tids[b["특약ID"]]["특약계보키"], b["급부ID"][len(b["특약ID"]):])

    keys = sorted({ben_key(b) for b in benefits})
    dropped_keys = {k for k in keys if rng.random() < rate / 2}
    benefits = [b for b in benefits if ben_key(b) not in dropped_keys]

    # 면책과 감액 바꾸기(같은 표준담보에 있는 값 가운데)
    swap = rng.uniform(0.10, 0.30)
    changes: dict[tuple, tuple] = {}
    for k in sorted({ben_key(b) for b in benefits}):
        changes[k] = rng.random() < swap
    new_terms: dict[tuple, tuple] = {}
    out_benefits = []
    for b in benefits:
        b = dict(b)
        m = src.mapping.get(b["급부ID"])
        sid = m.get("확정표준담보ID") if m and m.get("검토상태") in CONFIRMED else None
        k = ben_key(b)
        if changes.get(k) and sid and len(src.terms.get(sid, [])) > 1 and not b.get("감액예외"):
            if k not in new_terms:
                new_terms[k] = rng.choice(src.terms[sid])
            b.update(dict(zip(WAIT_RED, new_terms[k])))
        out_benefits.append(b)
    bids = {b["급부ID"] for b in out_benefits}

    # 가입나이 옮기기
    shift = rng.choice([-3, -2, -1, 1, 2, 3])
    conds = []
    for c in t["sys_가입조건"]:
        if c["종형ID"] not in vids or (c.get("특약ID") and c["특약ID"] not in tids):
            continue
        c = dict(c)
        lo = min(max(c["최저가입나이"] + shift, src.age_lo), src.age_hi)
        hi = min(max(c["최고가입나이"] + shift, src.age_lo), src.age_hi)
        if lo > hi:
            continue
        c["최저가입나이"], c["최고가입나이"] = lo, hi
        conds.append(c)
    rules = [r for r in t["sys_결합제약"] if r["종형ID"] in vids and r["기준특약ID"] in tids and r["대상특약ID"] in tids]

    def product(name: str) -> str:
        name = str(name).replace(real_name, comp["name"])
        for a, b in BRANDS.items():
            name = name.replace(a, b)
        return name if comp["name"] in name else f"{comp['name']} {name}"

    out_variants = []
    for v in variants:
        v = dict(v)
        v["기관코드"] = code
        v["공시상품명"] = product(v["공시상품명"])
        v["공시목록URL"] = FAKE_URL
        for col in HASH_COLUMNS:
            if v.get(col):
                v[col] = hashlib.sha256(f"{code}|{v[col]}".encode("utf-8")).hexdigest()[:len(str(v[col]))]
        if v.get("심사유형") == "간편심사":
            if v.get("고지수술포함여부") is not None and surgery is not None:
                v["고지수술포함여부"] = surgery
            if opinion:
                v["고지소견범위"] = opinion
            if disease and v.get("고지중대질병수") is not None:
                v["고지중대질병수"], v["고지중대질병목록"] = disease
        out_variants.append(v)
    names = {v["종형ID"]: v["공시상품명"] for v in out_variants}
    mapping = []
    for b in out_benefits:
        m = src.mapping.get(b["급부ID"])
        if m:
            m = dict(m)
            vid = tids[b["특약ID"]]["종형ID"]
            m["공시상품명"] = names[vid]
            mapping.append(m)
    rows = {"sys_상품종형": out_variants, "sys_특약": riders, "sys_급부": out_benefits, "hum_담보매핑": mapping,
            "sys_가입조건": conds, "sys_결합제약": rules}
    for tab, cols in ID_COLUMNS.items():
        rows[tab] = [{**r, **{c: swap_prefix(r.get(c), org, code) for c in cols}} for r in rows[tab]]
    comp["변화"] = {"뺀특약계보": len(dropped_lineages), "특약계보": len(lineages), "급부": len(bids),
                  "본뜬급부": sum(1 for b in t["sys_급부"] if src.riders.get(b["특약ID"], {}).get("종형ID") in
                                {v["종형ID"] for v in t["sys_상품종형"] if v["기관코드"] == org}),
                  "빼는비율": round(rate, 3), "면책감액바꾼급부": sum(1 for b in out_benefits if ben_key(b) in new_terms),
                  "가장긴기간": cap, "가장짧은기간": floor, "0년유형": keep_zero and 0 in [v.get("고지입원수술년수") for v in variants],
                  "수술포함": surgery, "소견범위": opinion, "중대질병수": disease[0] if disease else None, "나이옮김": shift,
                  "종형": len(out_variants)}
    return rows


def links(tables: dict[str, list[dict]]) -> list[str]:
    """탭 사이 이음이 끊긴 곳."""
    bad = []
    vids = {r["종형ID"] for r in tables["sys_상품종형"]}
    tids = {r["특약ID"]: r["종형ID"] for r in tables["sys_특약"]}
    bids = {r["급부ID"] for r in tables["sys_급부"]}
    conds = {r["조건행ID"] for r in tables["sys_가입조건"]}
    rules = {r["제약ID"] for r in tables["sys_결합제약"]}
    bad += [f"특약 {t}: 종형 {v} 없음" for t, v in tids.items() if v not in vids]
    bad += [f"급부 {r['급부ID']}: 특약 없음" for r in tables["sys_급부"] if r["특약ID"] not in tids]
    bad += [f"매핑 {r['급부ID']}: 급부 없음" for r in tables["hum_담보매핑"] if r["급부ID"] not in bids]
    for r in tables["sys_가입조건"]:
        if r["종형ID"] not in vids or (r.get("특약ID") and tids.get(r["특약ID"]) != r["종형ID"]):
            bad.append(f"가입조건 {r['조건행ID']}: 종형이나 특약이 맞지 않음")
    for r in tables["sys_결합제약"]:
        if r["종형ID"] not in vids or tids.get(r["기준특약ID"]) != r["종형ID"] or tids.get(r["대상특약ID"]) != r["종형ID"]:
            bad.append(f"결합제약 {r['제약ID']}: 종형이나 특약이 맞지 않음")
    for r in tables.get("sys_작업로그", []):
        target, tab = r.get("대상행ID"), r.get("대상탭")
        pool = {"sys_급부": bids, "hum_담보매핑": bids, "sys_가입조건": conds, "sys_결합제약": rules}.get(tab)
        if pool is not None and target and org_of_id(target).startswith("SYN"):
            bad.append(f"작업로그 {r['로그ID']}: 가상 회사 행을 가리킴")
    for tab, cols in ID_COLUMNS.items():
        for r in tables[tab]:
            for c in cols:
                if r.get(c) and tab != "sys_상품종형" and c != "종형계보키":
                    owner = org_of_id(r[c])
                    vid_owner = org_of_id(r.get("종형ID") or tids.get(r.get("특약ID"), "") or r[c])
                    if owner != vid_owner:
                        bad.append(f"{tab} {c}={r[c]}: 접두어가 종형과 다름")
    return bad


def real_names_left(rows: list[dict]) -> list[str]:
    """가상 회사 행에 남은 실제 회사 이름과 상품 이름."""
    words = list(config.ALL_ORGS.values()) + list(BRANDS) + ["한화", "삼성", "hanwha", "samsung"]
    hits = []
    for r in rows:
        for k, v in r.items():
            if isinstance(v, str) and any(w.lower() in v.lower() for w in words):
                hits.append(f"{k}={v[:80]}")
    return hits


def out_refusal(out: Path) -> str | None:
    """out 에 쓸 수 없는 까닭. 없거나 빈 폴더, 이 도구가 쓴 가상 사본(meta.json 의 가상자료 표시가 NOTICE 이고 탭 파일과
    meta.json 만 든 폴더)이면 None. 그 밖의 폴더를 지우면 저장소 자료(--out data, --out .)를 통째로 날리므로 막는다."""
    if not out.exists() and not out.is_symlink():
        return None
    if out.is_symlink() or not out.is_dir():
        return f"{out} 는 폴더가 아니다"
    entries = list(out.iterdir())
    if not entries:
        return None
    ours = {f"{t}.jsonl" for t in TABS} | {"meta.json"}
    others = sorted(e.name for e in entries if e.name not in ours or e.is_symlink() or not e.is_file())
    why = f"{out} 는 이 도구가 쓴 가상 사본 폴더가 아니라서 지우지 않는다"
    if others:
        return f"{why}(가상 사본에 없는 것: {', '.join(others[:5])}{' 등' if len(others) > 5 else ''})"
    try:
        marked = json.loads((out / "meta.json").read_text(encoding="utf-8")).get("가상자료") == NOTICE
    except (OSError, ValueError, AttributeError):
        marked = False
    return None if marked else f"{why}(meta.json 에 가상자료 표시가 없다)"


def clear_out(out: Path) -> None:
    """out_refusal 을 통과한 out 을 비운다(이 도구가 쓴 파일만 지운다)."""
    if out.exists():
        for e in out.iterdir():
            e.unlink()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path, default=ROOT / "data" / "snapshot", help="입력 사본 폴더")
    p.add_argument("--out", type=Path, default=ROOT / "out" / "synthetic_snapshot", help="쓸 폴더")
    p.add_argument("--life", type=int, default=9, help="더할 가상 생명보험사 수")
    p.add_argument("--nonlife", type=int, default=8, help="더할 가상 손해보험사 수")
    args = p.parse_args()
    if args.out.resolve() == args.snapshot.resolve():
        print("입력 사본 폴더에는 쓰지 않는다")
        return 1
    if (ROOT / "site").resolve() in [args.out.resolve(), *args.out.resolve().parents]:
        print("site/ 아래에는 쓰지 않는다(공개 배포되는 폴더다)")
        return 1
    refusal = out_refusal(args.out)
    if refusal:
        print(refusal)
        return 1
    tables = read_snapshot(args.snapshot)
    meta = json.loads((args.snapshot / "meta.json").read_text(encoding="utf-8"))
    src = Source(tables)
    comps = companies(args.life, args.nonlife)
    out = {name: list(rows) for name, rows in tables.items()}
    added: dict[str, list[dict]] = defaultdict(list)
    for comp in comps:
        for tab, rows in build_company(src, comp).items():
            out[tab].extend(rows)
            added[tab].extend(rows)

    problems = []
    for tab, rows in out.items():
        found = check_rows(tab, rows)
        problems += [f"{tab} {k}: {'; '.join(v)}" for k, v in list(found.items())[:5]]
    problems += links(out)[:20]
    problems += [f"실제 이름: {x}" for x in real_names_left([r for rows in added.values() for r in rows])[:10]]
    if problems:
        for x in problems:
            print("문제:", x)
        print(f"문제 {len(problems)}건. 쓰지 않았다.")
        return 1

    refusal = out_refusal(args.out)   # 만드는 사이에 바뀌었을 때를 위해 지우기 바로 전에 다시 본다
    if refusal:
        print(refusal)
        return 1
    clear_out(args.out)
    args.out.mkdir(parents=True, exist_ok=True)
    for tab in TABS:
        if tab in out:
            (args.out / f"{tab}.jsonl").write_text(to_jsonl(tab, out[tab]), encoding="utf-8")
    new_meta = {"snapshot_at": meta.get("snapshot_at"), "row_counts": {t: len(out[t]) for t in sorted(out)},
                "가상자료": NOTICE, "원본행수": meta.get("row_counts"),
                "기관이름": {c["code"]: c["name"] for c in comps},
                "기관업권": {c["code"]: c["sector"] for c in comps}}
    text = json.dumps(new_meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    (args.out / "meta.json").write_text(text, encoding="utf-8")
    size = sum(f.stat().st_size for f in args.out.iterdir())
    print(f"썼다: {args.out} ({size:,}바이트). 회사 {len({v['기관코드'] for v in out['sys_상품종형']})}곳"
          f"(가상 생명보험 {args.life}곳, 가상 손해보험 {args.nonlife}곳)")
    for t in ("sys_상품종형", "sys_특약", "sys_급부", "hum_담보매핑", "sys_가입조건", "sys_결합제약"):
        print(f"  {t}: {len(tables[t]):,} → {len(out[t]):,}")
    for c in comps:
        x = c["변화"]
        print(f"  {c['code']} {c['name']}: 종형 {x['종형']}, 간편 기간 {x['가장짧은기간']}~{x['가장긴기간']}년"
              f"{', 0년 유형' if x['0년유형'] else ''}, 뺀 특약 {x['뺀특약계보']}/{x['특약계보']}계보, 급부 {x['급부']:,}"
              f"(본뜬 회사 {x['본뜬급부']:,}), 면책 감액 바꾼 급부 {x['면책감액바꾼급부']:,}, 수술포함 {x['수술포함']}, "
              f"소견 {x['소견범위']}, 중대질병 {x['중대질병수']}개, 나이 {x['나이옮김']:+d}세")
    return 0


if __name__ == "__main__":
    sys.exit(main())
