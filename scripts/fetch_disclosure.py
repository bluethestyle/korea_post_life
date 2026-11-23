"""비교 대상 상품의 공시 문서를 받아 글자를 뽑는다. GitHub Actions에서 실행한다.

원본 PDF와 뽑은 글자는 저장소에 올리지 않는다. 실행 결과물(artifact)로만 잠시 보관한다.

삼성화재(--org samsungfire)는 상품요약서의 급부 표 조각(samsungfire_<공시상품코드>_급부표.json)도 함께 만든다.
급부가 표 하나에 이어져 있어 글자 파일로는 담보 경계를 자를 수 없기 때문이다. 급부 절이 여러 곳인 요약서는
대상 설정의 종형에 "급부구간"(구간 제목 줄. 예: "나. 8종(일반형)")을 적어 고른다. 절이 한 곳이면 적지 않는다.

초기 적재 회사(--org meritz 등, postlife.disclosure.sources에 이은 회사)는 대상 설정(data/targets/<회사>.json)의
공시상품코드마다 사업방법서와 상품요약서만 받고, 항목마다 파일 전체의 sha256을 더 적는다. 급부 표 조각은 만들지 않는다.
회사마다 공시상품코드 자리의 값(상품코드, 게시 번호, 상품명)과 공시상품명이 필요한지는 sources.SOURCES에 적었다.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.disclosure import epost, hanwha, samsungfire, sources  # noqa: E402
from postlife.disclosure.http import session  # noqa: E402
from postlife.extract import tables  # noqa: E402
from postlife.extract.segment import pages_from_text  # noqa: E402
from postlife.snapshot import KST  # noqa: E402

# 우체국 비교 대상. 이름에 이 글자가 들어간 상품을 목록에서 찾는다.
EPOST_NAMES = ["우체국통합건강보험 2504", "우체국간편한건강보험(20년갱신형) 2606"]
# 개정 전후 비교 시연용 직전 개정판 후보를 판매중지 목록에서 찾을 때 쓰는 글자
EPOST_PREVIOUS = ["우체국간편건강보험"]
# 삼성화재에서 받는 서류. 약관과 상품설명서는 받지 않는다.
SAMSUNGFIRE_KINDS = ("사업방법서", "상품요약서")
# 초기 적재 회사의 요청 사이 쉬기. 시험에서 바꿔 끼운다
pause = time.sleep


def pdf_pages(data: bytes) -> list[str]:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def save(out: Path, stem: str, data: bytes) -> dict:
    pages = pdf_pages(data)
    (out / f"{stem}.pdf").write_bytes(data)
    (out / f"{stem}.txt").write_text(
        "\n".join(f"\n===== {i + 1}쪽 =====\n{t}" for i, t in enumerate(pages)), encoding="utf-8")
    return {"쪽수": len(pages), "해시": hashlib.sha256(data).hexdigest()[:16], "저장이름": stem}


def fetch_hanwha(s, out: Path, targets: Path, list_only: bool) -> tuple[list[dict], list[str]]:
    """설정 파일(data/targets/hanwha.json)에 적힌 공시 상품번호의 요약서와 사업방법서를 받는다. 약관은 받지 않는다."""
    codes = sorted({v["공시상품코드"] for product in json.loads(targets.read_text(encoding="utf-8"))["상품"]
                    for v in product["종형"]})
    names = {x.code: x.name for x in hanwha.list_products(s, selling=True)}
    index, rows = [], []
    for code in codes:
        name = names.get(code, "")
        if not name:
            rows.append(f"| {code} | (판매상품 목록에 없음) | | | | |")
            continue
        for doc in hanwha.list_documents(s, code):
            if doc.kind == "약관":
                continue
            entry = {"기관": "HANWHALIFE", "상품코드": code, "상품명": name, "판매시작일": doc.start,
                     "판매종료일": doc.end, "문서": doc.kind, "파일": doc.file_name, "등록일": doc.start}
            if list_only:
                rows.append(f"| {code} | {name} | {doc.kind} | {doc.file_name} | | |")
                continue
            try:
                data = hanwha.download(s, doc)
                saved = save(out, f"hanwha_{code}_{doc.kind}", data)
            except Exception as e:  # noqa: BLE001
                print(f"  실패 {code} {doc.kind}: {e}"[:400])
                rows.append(f"| {code} | {name} | {doc.kind} | {doc.file_name} | 실패: {type(e).__name__} | |")
                continue
            index.append({**entry, **saved})
            rows.append(f"| {code} | {name} | {doc.kind} | {doc.file_name} | {saved['쪽수']} | {len(data):,} |")
    return index, rows


def save_riders(out: Path, name: str, stem: str, data: bytes, variants: list[dict]) -> dict:
    """상품요약서 PDF의 급부 표를 특별약관 단위 조각으로 잘라 JSON(name)으로 쓰고, 목록 항목에 더할 값을 돌려준다.

    stem은 방금 저장한 요약서의 저장이름이다. 급부 절의 쪽 범위는 그 글자 파일에서 찾는다.
    variants는 이 요약서를 쓰는 종형들(대상 설정의 항목)이다. 종형명으로 그 종에 해당하는 줄만 남긴다.
    한 공시상품코드에 종형이 여럿이어도 표는 하나만 쓰므로, 종형마다 남는 줄이 같지 않으면 만들지 않는다.
    급부구간도 종형마다 같아야 한다. 일부 종형에만 적혀 있으면 다른 것으로 본다(모두 비어 있으면 구간 없이 찾는다).
    """
    names = list(dict.fromkeys(v["종형명"] for v in variants))
    sections = list(dict.fromkeys(v.get("급부구간") or "" for v in variants))
    if len(sections) > 1:
        raise ValueError(f"같은 공시상품코드의 종형에 급부구간이 다르게 적혀 있습니다: {sections}")
    section = sections[0] or None
    found = tables.benefit_pages(pages_from_text((out / f"{stem}.txt").read_text(encoding="utf-8")), section)
    first, last = found.first_page, found.last_page
    riders = tables.riders_from_pdf(data, first, last)
    kept = tables.for_variant(riders, names[0])
    if any(tables.for_variant(riders, n) != kept for n in names[1:]):
        raise ValueError(f"같은 공시상품코드의 종형끼리 해당하는 줄이 달라 표 하나로 쓸 수 없습니다: {names}")
    if not kept:
        raise ValueError(f"{first}~{last}쪽에서 급부 표를 찾지 못했습니다")
    tables.write_riders(out / name, kept, {"문서": stem, "쪽": [first, last], "구간": section or "",
                                           "종": ", ".join(names)})
    return {"급부표": name, "급부표조각수": len(kept), "급부표세부보장수": sum(len(r.covers) for r in kept),
            "급부표쪽": [first, last]}


def fetch_samsungfire(s, out: Path, targets: Path,
                      list_only: bool) -> tuple[list[dict], list[str], dict[str, list[str]]]:
    """설정 파일(data/targets/samsungfire.json)에 적힌 공시상품코드의 사업방법서와 상품요약서를 받는다.

    약관과 상품설명서는 받지 않는다. 상품 목록은 한 번만 요청한다(전 상품의 서류 경로가 함께 온다).
    코드마다 지금 판매 중인 판매기간의 서류를 고르고, 상품요약서는 급부 표 조각도 만든다.
    받기 전에 그 코드의 이전 급부 표 조각 파일을 지운다. 이번에 만들지 못한 표가 폴더에 남지 않게 하려는 것이다.
    세 번째 값은 공시상품코드마다 갖추지 못한 것(사업방법서, 상품요약서, 급부표 가운데)이다. 다 갖춘 코드는 빠진다.
    """
    variants: dict[str, list[dict]] = {}
    for product in json.loads(targets.read_text(encoding="utf-8"))["상품"]:
        for v in product["종형"]:
            variants.setdefault(v["공시상품코드"], []).append(v)
    codes = sorted(variants)
    selling = samsungfire.list_products(s, selling=True)
    index, rows = [], []
    for code in codes:
        if not list_only:
            (out / f"samsungfire_{code}_급부표.json").unlink(missing_ok=True)
        periods = [x for x in selling if x.code == code and x.jong == "0"]
        if not periods:
            rows.append(f"| {code} | (판매상품 목록에 없음) | | | | |")
            continue
        product = max(periods, key=lambda x: x.start)      # 판매 중인 기간이 겹쳐 오면 가장 최근 것
        docs = {doc.kind: doc for doc in samsungfire.parse_documents(code, [product])}
        for kind in SAMSUNGFIRE_KINDS:
            doc = docs.get(kind)
            if doc is None:
                rows.append(f"| {code} | {product.name} | {kind} | (공시 목록에 서류 경로 없음) | | |")
                continue
            entry = {"기관": "SAMSUNGFIRE", "상품코드": code, "상품명": product.name, "판매시작일": product.start,
                     "판매종료일": product.end, "문서": doc.kind, "파일": doc.file_name, "등록일": doc.registered}
            if list_only:
                rows.append(f"| {code} | {product.name} | {doc.kind} | {doc.file_name} | | |")
                continue
            try:
                data = samsungfire.download(s, doc)
                saved = save(out, f"samsungfire_{code}_{doc.kind}", data)
            except Exception as e:  # noqa: BLE001
                print(f"  실패 {code} {doc.kind}: {e}"[:400])
                rows.append(f"| {code} | {product.name} | {doc.kind} | {doc.file_name} | 실패: {type(e).__name__} | |")
                continue
            rows.append(f"| {code} | {product.name} | {doc.kind} | {doc.file_name} | {saved['쪽수']} | {len(data):,} |")
            if doc.kind == "상품요약서":
                table = f"samsungfire_{code}_급부표.json"
                try:
                    made = save_riders(out, table, saved["저장이름"], data, variants[code])
                except Exception as e:  # noqa: BLE001
                    # 표를 만들지 못해도 받은 문서는 목록에 남긴다
                    print(f"  실패 {code} 급부표: {e}"[:400])
                    rows.append(f"| {code} | {product.name} | 급부표 | {table} | 실패: {type(e).__name__} | |")
                else:
                    saved = {**saved, **made}
                    first, last = made["급부표쪽"]
                    rows.append(f"| {code} | {product.name} | 급부표 | {table} | {first}~{last} | "
                                f"조각 {made['급부표조각수']}, 세부보장 {made['급부표세부보장수']} |")
            index.append({**entry, **saved})
    missing = {}
    for code in codes:
        mine = [e for e in index if e["상품코드"] == code]
        have = {e["문서"] for e in mine} | {"급부표" for e in mine if e.get("급부표")}
        lack = [k for k in (*SAMSUNGFIRE_KINDS, "급부표") if k not in have]
        if lack and not list_only:
            missing[code] = lack
    return index, rows, missing


def fetch_source(src: sources.Source, s, out: Path, targets: Path, list_only: bool,
                 on: str) -> tuple[list[dict], list[str], dict[str, list[str]]]:
    """초기 적재 회사(postlife.disclosure.sources에 이은 회사)의 대상 코드마다 사업방법서와 상품요약서를 받는다.

    대상 설정 파일의 공시상품코드마다 on(기준일)에 판매 중인 판매기간을 고른다. 같은 세션으로 목록과 서류를 받고,
    요청 사이에 src.pause초 쉰다. 항목은 다른 회사와 같은 열쇠에 파일 전체의 sha256을 더한다.
    세 번째 값은 공시상품코드마다 받지 못한 서류다. 다 받은 코드는 빠진다.
    종형에 "공시상품명"이 있으면 상품을 찾는 데 쓰도록 find에 넘긴다(상품명으로만 찾을 수 있는 회사가 있다).
    같은 공시상품코드의 종형끼리 공시상품명이 다르면 그 코드는 받지 않는다.
    """
    names: dict[str, set[str]] = {}
    for product in json.loads(targets.read_text(encoding="utf-8"))["상품"]:
        for v in product["종형"]:
            names.setdefault(v["공시상품코드"], set()).update([v["공시상품명"]] if v.get("공시상품명") else [])
    codes = sorted(names)
    index, rows, asked = [], [], False

    def wait():
        nonlocal asked
        if asked and src.pause > 0:
            pause(src.pause)
        asked = True

    for code in codes:
        if len(names[code]) > 1:
            rows.append(f"| {code} | | 공시상품명이 종형마다 다름 | {', '.join(sorted(names[code]))} | | | |")
            continue
        wait()
        try:
            found = src.find(s, code, on, next(iter(names[code]), None))
        except Exception as e:  # noqa: BLE001
            print(f"  실패 {code} 서류 목록: {e}"[:400])
            rows.append(f"| {code} | | 서류 목록 실패 | {type(e).__name__} | | | |")
            continue
        if found is None:
            rows.append(f"| {code} | (판매상품 목록에 없음) | | | | | |")
            continue
        name, docs = found
        docs = {d.kind: d for d in docs}
        for kind in src.kinds:
            doc = docs.get(kind)
            if doc is None:
                rows.append(f"| {code} | {name} | {kind} | (공시 목록에 서류 경로 없음) | | | |")
                continue
            entry = {"기관": src.org, "상품코드": code, "상품명": name, "판매시작일": doc.start, "판매종료일": doc.end,
                     "문서": kind, "파일": doc.file_name, "등록일": doc.registered}
            if list_only:
                rows.append(f"| {code} | {name} | {kind} | {doc.file_name} | | | |")
                continue
            wait()
            try:
                data = src.download(s, doc)
                saved = save(out, f"{src.key}_{code}_{kind}", data)
            except Exception as e:  # noqa: BLE001
                print(f"  실패 {code} {kind}: {e}"[:400])
                rows.append(f"| {code} | {name} | {kind} | {doc.file_name} | 실패: {type(e).__name__} | | |")
                continue
            digest = hashlib.sha256(data).hexdigest()
            index.append({**entry, **saved, "sha256": digest})
            rows.append(f"| {code} | {name} | {kind} | {doc.file_name} | {saved['쪽수']} | {len(data):,} | {digest} |")
    missing = {}
    if not list_only:
        for code in codes:
            have = {e["문서"] for e in index if e["상품코드"] == code}
            lack = [k for k in src.kinds if k not in have]
            if lack:
                missing[code] = lack
    return index, rows, missing


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("out"))
    p.add_argument("--list-only", action="store_true")
    p.add_argument("--org", default="epost", choices=["epost", "hanwha", "samsungfire", *sources.SOURCES],
                   help="받을 회사")
    p.add_argument("--targets", type=Path,
                   help="추출 대상 설정. 안 주면 삼성화재는 data/targets/samsungfire.json, 초기 적재 회사는 "
                        "data/targets/<회사>.json(예: meritz.json), 그 밖에는 data/targets/hanwha.json")
    args = p.parse_args()
    if args.targets is None:
        if args.org in sources.SOURCES:
            args.targets = Path(sources.SOURCES[args.org].targets)
        else:
            args.targets = Path("data/targets/samsungfire.json" if args.org == "samsungfire" else "data/targets/hanwha.json")
    args.out.mkdir(parents=True, exist_ok=True)
    s = session()
    today = datetime.now(KST).date().isoformat()
    head = ["| 상품코드 | 상품명 | 문서 | 파일 | 쪽수 | 크기 |", "| --- | --- | --- | --- | --- | --- |"]

    if args.org in sources.SOURCES:
        src = sources.SOURCES[args.org]
        index, rows, missing = fetch_source(src, s, args.out, args.targets, args.list_only, today)
        (args.out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
        table = "\n".join(["| 상품코드 | 상품명 | 문서 | 파일 | 쪽수 | 크기 | sha256 |",
                           "| --- | --- | --- | --- | --- | --- | --- |"] + rows)
        if missing:
            table += "\n\n갖추지 못한 상품: " + ", ".join(f"{code}({', '.join(lack)})" for code, lack in missing.items())
        print(table)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write(f"## 공시 문서 수집 ({src.label})\n\n" + table + "\n")
        # 대상 코드 가운데 사업방법서나 상품요약서가 하나라도 빠진 것이 있으면 실패로 끝낸다
        return 0 if args.list_only or (index and not missing) else 1

    if args.org == "hanwha":
        index, rows = fetch_hanwha(s, args.out, args.targets, args.list_only)
        (args.out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
        table = "\n".join(head + rows)
        print(table)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write("## 공시 문서 수집 (한화생명)\n\n" + table + "\n")
        return 0 if index or args.list_only else 1

    if args.org == "samsungfire":
        index, rows, missing = fetch_samsungfire(s, args.out, args.targets, args.list_only)
        (args.out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
        table = "\n".join(head + rows)
        if missing:
            table += "\n\n갖추지 못한 상품: " + ", ".join(f"{code}({', '.join(lack)})" for code, lack in missing.items())
        print(table)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write("## 공시 문서 수집 (삼성화재)\n\n" + table + "\n")
        # 대상 코드 가운데 사업방법서, 상품요약서, 급부표 중 하나라도 빠진 것이 있으면 실패로 끝낸다.
        # 받은 문서와 목록은 위에서 이미 남겼다
        return 0 if args.list_only or (index and not missing) else 1

    selling = epost.list_products(s, selling=True)
    stopped = epost.list_products(s, selling=False)
    (args.out / "epost_products.json").write_text(
        json.dumps({"판매중": [asdict(x) for x in selling], "판매중지": [asdict(x) for x in stopped]},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"우체국 판매중 {len(selling)}개, 판매중지 {len(stopped)}개")

    targets = [(x, today) for x in selling if any(n in x.name for n in EPOST_NAMES) and "플러스보험기간" not in x.name]
    previous = [x for x in stopped if any(n in x.name for n in EPOST_PREVIOUS)]
    for x in previous:
        print(f"  직전 개정판 후보: {x.code} {x.name} ({x.start} ~ {x.end})")
    targets += [(x, x.end or today) for x in previous if "2504" in x.name or "2409" in x.name]

    rows = ["| 상품코드 | 상품명 | 문서 | 파일 | 쪽수 | 크기 |", "| --- | --- | --- | --- | --- | --- |"]
    index, done = [], {}
    for product, on in targets:
        try:
            docs = epost.list_documents(s, product.code, on)
        except Exception as e:  # noqa: BLE001
            rows.append(f"| {product.code} | {product.name} | 서류 목록 실패 | {type(e).__name__} | | |")
            continue
        for doc in docs:
            entry = {"기관": "EPOST", "상품코드": product.code, "상품명": product.name, "판매시작일": product.start,
                     "판매종료일": product.end, "문서": doc.kind, "파일": doc.file_name, "등록일": doc.registered}
            if doc.path in done:           # 여러 종이 한 파일을 함께 쓴다
                index.append({**entry, **done[doc.path]})
                continue
            if args.list_only:
                rows.append(f"| {product.code} | {product.name} | {doc.kind} | {doc.file_name} | | |")
                continue
            try:
                data = epost.download(s, doc)
                pages = pdf_pages(data)
            except Exception as e:  # noqa: BLE001
                print(f"  실패 {product.code} {doc.kind}: {e}"[:400])
                rows.append(f"| {product.code} | {product.name} | {doc.kind} | {doc.file_name} | 실패: {type(e).__name__} | |")
                continue
            stem = doc.file_name.rsplit(".", 1)[0]
            (args.out / f"{stem}.pdf").write_bytes(data)
            (args.out / f"{stem}.txt").write_text(
                "\n".join(f"\n===== {i + 1}쪽 =====\n{t}" for i, t in enumerate(pages)), encoding="utf-8")
            done[doc.path] = {"쪽수": len(pages), "해시": hashlib.sha256(data).hexdigest()[:16], "저장이름": stem}
            index.append({**entry, **done[doc.path]})
            rows.append(f"| {product.code} | {product.name} | {doc.kind} | {doc.file_name} | {len(pages)} | {len(data):,} |")

    (args.out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    table = "\n".join(rows)
    print(table)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 공시 문서 수집 (우체국보험)\n\n" + table + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
