"""공개 주소의 루트(site/index.html)는 분석 화면, 발표 덱, 관계 그래프 화면, 초기 버전으로 가는 안내 화면이다.

안내 화면의 링크가 모두 site/ 안의 실제 파일을 가리키는지, 밖에서 불러오는 자원이 없는지, 초기 버전의 판단 화면이
site/v1/index.html 에 있고 scripts/build_site.py 의 기본 출력이 그 자리인지 본다.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
LANDING = SITE / "index.html"
V1 = SITE / "v1" / "index.html"


def _html() -> str:
    return LANDING.read_text(encoding="utf-8")


def test_landing_links_point_to_existing_pages():
    hrefs = re.findall(r'<a\b[^>]*\shref="([^"]+)"', _html())
    local = [h for h in hrefs if not re.match(r"^[a-z]+:", h)]
    assert {"proto/console4.html", "deck/index.html", "proto/graph2.html", "v1/index.html"} <= set(local)
    for h in local:
        assert (SITE / h.split("#")[0]).is_file(), h
    # 분석 화면이 첫 링크다(먼저 보이게)
    assert local[0] == "proto/console4.html"


def test_landing_loads_nothing_from_outside():
    html = _html()
    outside = re.findall(
        r"""<(?:script|img|iframe|link|source|video|audio|embed|object)\b[^>]*\s(?:src|href|data)\s*=\s*["']?(?:https?:)?//"""
        r"""|url\(\s*["']?(?:https?:)?//|@import""", html, flags=re.I)
    assert outside == []
    assert "<script" not in html.lower()


def test_initial_version_moved_to_v1():
    assert V1.is_file()
    assert "<title>우체국보험 상품·청약 판단 지원</title>" in V1.read_text(encoding="utf-8")[:4000]
    run = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_site.py"), "--help"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert run.returncode == 0
    src = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    assert 'default=ROOT / "site" / "v1" / "index.html"' in src
