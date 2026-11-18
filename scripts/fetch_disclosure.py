"""공시 문서를 받아 글자를 뽑는다. GitHub Actions에서 실행한다.

원본 PDF와 뽑은 글자는 저장소에 올리지 않는다. 실행 결과물(artifact)로만 잠시 보관한다.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_access import _get  # noqa: E402

EPOST = "https://www.epostlife.go.kr"
EPOST_PDF = EPOST + "/resources/js/biz/ip/gs/pdf/{kind}_{code}_{ym}.pdf"

# (이름, 상품코드, 개정연월). 코드는 검토 과정에서 제시된 값이라 받아 보고 확인한다.
EPOST_TARGETS = [
    ("우체국통합건강보험 2504", "P400069", "202504"),
    ("우체국간편한건강보험 2606", "P500129", "202606"),
    ("우체국간편한건강보험 2606", "P500130", "202606"),
    ("우체국간편한건강보험 2606", "P500131", "202606"),
    ("우체국간편한건강보험 2606", "P500132", "202606"),
]
KINDS = {"yoyak": "상품요약서", "YAK": "약관", "saup": "사업방법서", "SAUP": "사업방법서", "bang": "사업방법서"}


def fetch(url: str):
    try:
        r = _get(url, legacy=True)
        return r.status_code, r.headers.get("Content-Type", ""), r.content
    except Exception as e:  # noqa: BLE001
        return 0, type(e).__name__, b""


def pdf_text(data: bytes) -> tuple[int, list[str]]:
    import pdfplumber

    pages = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return len(pages), pages


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("out"))
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = ["| 상품 | 코드 | 문서 | 상태 | 크기 | 쪽수 | 첫 줄 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    index = []

    for name, code, ym in EPOST_TARGETS:
        # 상품 안내 화면에서 문서 주소를 찾아본다
        status, ctype, body = fetch(f"{EPOST}/IGDRDM00AT.do?gdsCd={code}")
        page = body.decode("utf-8", errors="ignore")
        links = sorted(set(re.findall(r"[\w./-]+\.pdf", page)))
        title = re.search(r"<title>(.*?)</title>", page, re.S)
        print(f"[{code}] 안내 화면 {status}, {len(page):,}자, 제목={title.group(1).strip() if title else ''}, pdf 주소 {links[:10]}")
        for hit in re.finditer(r"(약관|상품요약서|사업방법서)", page):
            around = re.sub(r"\s+", " ", page[max(0, hit.start() - 200): hit.end() + 200])
            print("   주변:", around[:400])
            break

        for kind, label in KINDS.items():
            url = EPOST_PDF.format(kind=kind, code=code, ym=ym)
            status, ctype, body = fetch(url)
            is_pdf = body[:5] == b"%PDF-"
            n, first = "", ""
            if is_pdf:
                try:
                    count, pages = pdf_text(body)
                    n = str(count)
                    first = re.sub(r"\s+", " ", " ".join(pages[:1]))[:80].replace("|", "/")
                    stem = f"EPOST_{code}_{ym}_{kind}"
                    (args.out / f"{stem}.pdf").write_bytes(body)
                    (args.out / f"{stem}.txt").write_text(
                        "\n".join(f"\n===== {i + 1}쪽 =====\n{t}" for i, t in enumerate(pages)), encoding="utf-8"
                    )
                    index.append({"기관": "EPOST", "상품": name, "코드": code, "개정연월": ym, "문서": label,
                                  "주소": url, "쪽수": count, "해시": hashlib.sha256(body).hexdigest()[:16]})
                except Exception as e:  # noqa: BLE001
                    first = f"글자 추출 실패: {type(e).__name__}"
            rows.append(f"| {name} | {code} | {label}({kind}) | {status if is_pdf else str(status) + ' (PDF 아님)'} | {len(body):,} | {n} | {first} |")

    (args.out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    table = "\n".join(rows)
    print(table)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 공시 문서 수집\n\n" + table + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
