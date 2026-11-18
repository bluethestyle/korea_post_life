"""비교 대상 상품의 공시 문서를 받아 글자를 뽑는다. GitHub Actions에서 실행한다.

원본 PDF와 뽑은 글자는 저장소에 올리지 않는다. 실행 결과물(artifact)로만 잠시 보관한다.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.disclosure import epost  # noqa: E402
from postlife.disclosure.http import session  # noqa: E402
from postlife.snapshot import KST  # noqa: E402

# 우체국 비교 대상. 이름에 이 글자가 들어간 상품을 목록에서 찾는다.
EPOST_NAMES = ["우체국통합건강보험 2504", "우체국간편한건강보험(20년갱신형) 2606"]
# 개정 전후 비교 시연용 직전 개정판 후보를 판매중지 목록에서 찾을 때 쓰는 글자
EPOST_PREVIOUS = ["우체국간편건강보험"]


def pdf_pages(data: bytes) -> list[str]:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("out"))
    p.add_argument("--list-only", action="store_true")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    s = session()
    today = datetime.now(KST).date().isoformat()

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
