"""GitHub Actions에서 국내 공시실·협회 사이트에 접속되는지 확인한다 (docs/planning.md 4.5).

막힌 곳이 있어도 실패로 끝내지 않는다. 결과 표를 실행 요약에 남기는 것이 목적이다.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.disclosure.http import session  # noqa: E402

TARGETS = [
    ("우체국보험", "https://epostlife.go.kr/"),
    ("우체국보험 (www)", "https://www.epostlife.go.kr/"),
    ("우체국보험 공시 목록", "https://epostlife.go.kr/ASISDM00AT.do"),
    ("생명보험협회", "https://www.klia.or.kr/"),
    ("생명보험협회 공시실", "https://pub.insure.or.kr/"),
    ("손해보험협회", "https://www.knia.or.kr/"),
    ("손해보험협회 공시실", "https://kpub.knia.or.kr/"),
    ("한화생명", "https://www.hanwhalife.com/"),
    ("삼성화재", "https://www.samsungfire.com/"),
    ("Google News RSS", "https://news.google.com/rss/search?q=%EB%B3%B4%ED%97%98+%EB%B0%B0%ED%83%80%EC%A0%81%EC%82%AC%EC%9A%A9%EA%B6%8C&hl=ko&gl=KR&ceid=KR:ko"),
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; postlife-access-check)"}


def _get(url: str, legacy: bool) -> requests.Response:
    client = session() if legacy else requests.Session()
    return client.get(url, headers=HEADERS, timeout=20, allow_redirects=True)


def check(url: str) -> tuple[str, str]:
    started = time.time()
    try:
        r = _get(url, legacy=False)
        return str(r.status_code), f"{time.time() - started:.1f}초, {len(r.content):,}바이트"
    except requests.exceptions.SSLError as first:
        try:
            r = _get(url, legacy=True)
            return str(r.status_code), f"구형 암호 방식을 허용해야 접속됨, {len(r.content):,}바이트"
        except requests.RequestException as e:
            return "접속 실패", f"{type(e).__name__}: {str(e)[-110:]}".replace("|", "/")
    except requests.RequestException as e:
        return "접속 실패", f"{type(e).__name__}: {str(e)[-110:]}".replace("|", "/")


def main() -> int:
    lines = ["| 대상 | 주소 | 결과 | 비고 |", "| --- | --- | --- | --- |"]
    for name, url in TARGETS:
        status, note = check(url)
        lines.append(f"| {name} | {url.split('?')[0]} | {status} | {note} |")
    table = "\n".join(lines)
    print(table)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 국내 사이트 접속 시험\n\n" + table + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
