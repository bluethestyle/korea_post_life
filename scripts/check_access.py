"""GitHub Actions에서 국내 공시실·협회 사이트에 접속되는지 확인한다 (docs/planning.md 4.5).

막힌 곳이 있어도 실패로 끝내지 않는다. 결과 표를 실행 요약에 남기는 것이 목적이다.
"""
from __future__ import annotations

import os
import sys
import time

import requests

TARGETS = [
    ("우체국보험", "https://www.epostlife.go.kr/"),
    ("생명보험협회", "https://www.klia.or.kr/"),
    ("생명보험협회 공시실", "https://pub.insure.or.kr/"),
    ("손해보험협회", "https://www.knia.or.kr/"),
    ("손해보험협회 공시실", "https://kpub.knia.or.kr/"),
    ("한화생명", "https://www.hanwhalife.com/"),
    ("삼성화재", "https://www.samsungfire.com/"),
    ("Google News RSS", "https://news.google.com/rss/search?q=%EB%B3%B4%ED%97%98+%EB%B0%B0%ED%83%80%EC%A0%81%EC%82%AC%EC%9A%A9%EA%B6%8C&hl=ko&gl=KR&ceid=KR:ko"),
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; postlife-access-check)"}


def check(url: str) -> tuple[str, str]:
    started = time.time()
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        return str(r.status_code), f"{time.time() - started:.1f}초, {len(r.content):,}바이트"
    except requests.RequestException as e:
        return "접속 실패", type(e).__name__


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
