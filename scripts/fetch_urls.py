"""주어진 주소를 받아 결과물 폴더에 저장한다. 공시실 화면 구조를 확인할 때 쓰는 점검 도구다.

환경변수 URLS에 한 줄에 하나씩 적는다.
  GET https://...
  POST https://... key=value&key2=value2
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_access import HEADERS, LegacyCipherAdapter  # noqa: E402

import requests  # noqa: E402


def main() -> int:
    out = Path("out")
    out.mkdir(exist_ok=True)
    session = requests.Session()
    session.mount("https://", LegacyCipherAdapter())
    lines = [l.strip() for l in os.environ.get("URLS", "").splitlines() if l.strip()]
    for n, line in enumerate(lines, 1):
        parts = line.split(" ", 2)
        method, url = parts[0].upper(), parts[1]
        body = parts[2] if len(parts) > 2 else None
        try:
            if method == "POST":
                headers = {**HEADERS, "X-Requested-With": "XMLHttpRequest", "Referer": url,
                           "Accept": "application/json, text/javascript, */*; q=0.01",
                           "Accept-Language": "ko-KR,ko;q=0.9",
                           "Content-Type": "application/json; charset=UTF-8" if (body or "").startswith("{") else
                           "application/x-www-form-urlencoded; charset=UTF-8"}
                r = session.post(url, data=(body or "").encode("utf-8"), headers=headers, timeout=30)
            else:
                r = session.get(url, headers=HEADERS, timeout=30)
            name = re.sub(r"[^\w.-]+", "_", url.split("//", 1)[-1])[:80]
            ext = ".pdf" if r.content[:5] == b"%PDF-" else ".txt"
            (out / f"{n:02d}_{name}{ext}").write_bytes(r.content)
            print(f"{n:02d} {method} {url} → {r.status_code}, {len(r.content):,}바이트, {r.headers.get('Content-Type', '')}")
        except Exception as e:  # noqa: BLE001
            print(f"{n:02d} {method} {url} → 실패 {type(e).__name__}: {str(e)[-100:]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
