"""주어진 주소를 받아 결과물 폴더에 저장한다. 공시실 화면 구조를 확인할 때 쓰는 점검 도구다.

환경변수 URLS에 한 줄에 하나씩 적는다. 한 번의 실행 안에서는 쿠키가 이어진다.
  GET https://...
  POST https://... key=value&key2=value2        (본문이 { 로 시작하면 JSON으로 보낸다)
  H 이름: 값                                     (이후 요청에 붙일 머리말. 값이 비면 지운다)
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.disclosure.http import session as make_session  # noqa: E402


def main() -> int:
    out = Path("out")
    out.mkdir(exist_ok=True)
    session = make_session()
    extra: dict[str, str] = {}
    lines = [l.strip() for l in os.environ.get("URLS", "").splitlines() if l.strip()]
    n = 0
    for line in lines:
        if line.startswith("H "):
            name, _, value = line[2:].partition(":")
            if value.strip():
                extra[name.strip()] = value.strip()
            else:
                extra.pop(name.strip(), None)
            continue
        n += 1
        parts = line.split(" ", 2)
        method, url = parts[0].upper(), parts[1]
        body = parts[2] if len(parts) > 2 else None
        try:
            if method == "POST":
                headers = {"X-Requested-With": "XMLHttpRequest", "Referer": url,
                           "Accept": "application/json, text/javascript, */*; q=0.01",
                           "Content-Type": "application/json; charset=UTF-8" if (body or "").startswith("{") else
                           "application/x-www-form-urlencoded; charset=UTF-8", **extra}
                r = session.post(url, data=(body or "").encode("utf-8"), headers=headers, timeout=120)
            else:
                r = session.get(url, headers=extra, timeout=120)
            name = re.sub(r"[^\w.-]+", "_", url.split("//", 1)[-1])[:80]
            start = r.content[:2048].find(b"%PDF-")
            ext = ".pdf" if start >= 0 else ".txt"
            (out / f"{n:02d}_{name}{ext}").write_bytes(r.content[start:] if start >= 0 else r.content)
            print(f"{n:02d} {method} {url} → {r.status_code}, {len(r.content):,}바이트, {r.headers.get('Content-Type', '')}"
                  f"{', 쿠키 ' + ','.join(session.cookies.keys()) if session.cookies else ''}")
        except Exception as e:  # noqa: BLE001
            print(f"{n:02d} {method} {url} → 실패 {type(e).__name__}: {str(e)[-100:]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
