"""시안 4 합친 결과 검사: proto_src/console4 의 원본과 자료를 build.py 로 다시 합치면 커밋된 site/proto/console4.html 과
바이트까지 같아야 한다. 합친 파일에 외부 요청이 없고, noindex 메타와 고지가 있어야 한다.

원본이나 자료(scripts/export_app_data.py 로 만든 파일)를 고치고 합친 파일을 다시 만들지 않았으면 이 시험이 깨진다.
build 는 tab4.src.js 가 아니라 tab4.js(cover.json + tab4.src.js)를 싣는다. tab4.src.js 만 고치고 다시 합치지 않으면
build 가 멈추고, 커밋된 tab4.js 가 두 원본을 합친 것과 다르면 아래 시험이 깨진다.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from postlife.site import console4 as C4

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "proto_src" / "console4"
PAGE = ROOT / "site" / "proto" / "console4.html"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("console4") / "console4.html"
    run = subprocess.run([sys.executable, str(SRC / "build.py"), str(out)], cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8")
    assert run.returncode == 0, f"build.py 가 멈췄다:\n{run.stdout}\n{run.stderr}"
    assert "오류" not in run.stdout, run.stdout
    return out.read_text(encoding="utf-8")


def test_rebuild_matches_committed_page(built):
    committed = PAGE.read_text(encoding="utf-8")
    if built != committed:
        a, b = built.split("\n"), committed.split("\n")
        diff = [i + 1 for i, (x, y) in enumerate(zip(a, b)) if x != y][:5]
        pytest.fail(f"다시 합친 결과가 커밋된 {PAGE.relative_to(ROOT)} 와 다르다(줄 수 {len(a)} 대 {len(b)}, 다른 줄 {diff}). "
                    "python scripts/export_app_data.py 와 python proto_src/console4/build.py 로 다시 만든다")
    assert built.encode("utf-8") == PAGE.read_bytes()


def test_no_external_requests(built):
    # 화면에 실린 자료(JSON)는 글자일 뿐이라 뺀다(소식의 출처 주소가 들어 있다). pages.yml 의 검사와 같은 규칙
    html = re.sub(r'<script id="sales-data" type="application/json">.*?</script>', "", built, flags=re.S)
    outside = re.findall(
        r"""<(?:script|img|iframe|link|source|video|audio|embed|object)\b[^>]*\s(?:src|href|data)\s*=\s*["']?(?:https?:)?//[^\s"'>]+"""
        r"""|url\(\s*["']?(?:https?:)?//[^)\s]+|@import\s+[^;]+""", html, flags=re.I)
    assert outside == []
    assert not re.search(r"<link\b", html, flags=re.I)
    assert not re.search(r"""<script\b[^>]*\ssrc\s*=""", html, flags=re.I), "바깥 스크립트 파일을 부른다"


def test_noindex_and_notice(built):
    assert '<meta name="robots" content="noindex, nofollow">' in built
    m = re.search(r'<script id="sales-data" type="application/json">(.*?)</script>', built, flags=re.S)
    assert m, "sales-data 가 없다"
    notice = json.loads(m.group(1).replace("<\\/", "</").replace("<\\!--", "<!--"))["고지"]
    assert notice.strip(), "sales.json 의 고지가 비었다"
    # 머리 띠와 바닥글의 고지 자리(화면이 열릴 때 core.js 가 sales.json 의 고지로 채운다)
    for el in ("notice-t", "foot-notice"):
        hit = re.search(rf'id="{el}">([^<]*)<', built)
        assert hit and hit.group(1).strip(), f"#{el} 고지 자리가 없거나 비었다"


def test_committed_tab4_is_assembled_from_sources():
    # 화면에 들어가는 것은 tab4.js 다. 손으로 고치는 tab4.src.js 와 자료 cover.json 을 합친 것이어야 한다
    tab4, cover, src = ((SRC / n).read_text(encoding="utf-8") for n in ("tab4.js", "cover.json", "tab4.src.js"))
    assert tab4 == C4.assemble_tab4(cover, src), \
        "tab4.js 가 cover.json 과 tab4.src.js 를 합친 것과 다르다. python proto_src/console4/gen_cover.py --assemble 뒤 build.py 로 다시 합친다"


def test_build_stops_when_tab4_src_changed_without_assemble(tmp_path):
    # 원본 폴더를 복사해 tab4.src.js 만 고친다(글꼴은 복사하지 않는다. 글꼴이 없으면 build 는 경고만 한다)
    work = tmp_path / "proto_src" / "console4"
    shutil.copytree(SRC, work, ignore=shutil.ignore_patterns("__pycache__"))
    p = work / "tab4.src.js"
    p.write_text(p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    out = tmp_path / "out.html"
    run = subprocess.run([sys.executable, str(work / "build.py"), str(out)], cwd=tmp_path, capture_output=True, text=True,
                         encoding="utf-8")
    assert run.returncode != 0, run.stdout
    assert "오류: tab4.js 가 cover.json 과 tab4.src.js 를 합친 것과 다르다" in run.stdout, run.stdout
    assert not out.exists(), "멈췄는데 합친 파일을 썼다"


BANNER = "가상 자료(화면 배치 시험용, 실제 회사 자료 아님)"
NOTICE_FIT = ' style="min-width:0;overflow:hidden;text-overflow:ellipsis"'   # build.py 의 NOTICE_FIT


@pytest.fixture(scope="module")
def bannered(tmp_path_factory):
    # --src 는 원본과 자료를 그 폴더에서 읽고(이 폴더는 건드리지 않는다), --banner 는 맨 위 고지 줄과 창 제목에 글을 끼운다.
    # tpl.html 은 고치지 않는다. 가상 자료 화면(scripts/dev/build_console4_synthetic.py)이 쓴다
    tmp = tmp_path_factory.mktemp("banner")
    work = tmp / "work"
    shutil.copytree(SRC, work, ignore=shutil.ignore_patterns("__pycache__"))
    out = tmp / "banner.html"
    run = subprocess.run([sys.executable, str(SRC / "build.py"), str(out), "--src", str(work), "--banner", BANNER],
                         cwd=tmp, capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stdout + run.stderr
    return out


def test_build_reads_another_folder_and_adds_a_banner(bannered, built):
    page = bannered.read_text(encoding="utf-8")
    # 끼운 글은 고지 글 바로 앞에 줄어들지 않게(flex:none) 들어가고, 고지 글은 넘치면 줄임표로 줄어든다
    assert re.search(r'<span id="banner-t"[^>]*flex:none[^>]*>' + re.escape(BANNER)
                     + '</span><span id="notice-t"' + re.escape(NOTICE_FIT) + ">", page)
    assert f"<title>[{BANNER}] " in page
    # 끼운 글을 빼면 보통으로 합친 결과와 같다(같은 원본과 자료를 읽었다)
    plain = (re.sub(r'<span id="banner-t"[^>]*>[^<]*</span>', "", page).replace(f"[{BANNER}] ", "", 1)
             .replace('<span id="notice-t"' + NOTICE_FIT + ">", '<span id="notice-t">', 1))
    assert plain == built


@pytest.mark.parametrize("width", [380, 1280, 1920])
def test_banner_is_fully_visible(bannered, width):
    # 가상 자료 띠는 어느 폭에서나 다 보여야 한다. 고지 줄(.notice .nt)은 한 줄에 넘치는 것을 잘라서, 고지 글 뒤에 끼우면
    # 380px 에서 "가상 자료(화면 배..."까지만 보였다(2026-11-23 점검). 좁으면 고지 글 쪽이 줄임표로 줄어든다
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            chromium = p.chromium.launch()
        except Exception as error:          # 브라우저 파일이 없는 환경
            pytest.skip(f"chromium을 띄우지 못함: {error}")
        try:
            page = chromium.new_page(viewport={"width": width, "height": 800})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(bannered.as_uri())
            page.evaluate("document.fonts.ready")
            box = page.evaluate("""() => {
                const r = el => el.getBoundingClientRect();
                const b = document.getElementById('banner-t'), n = document.getElementById('notice-t');
                const nt = b.parentElement;
                return {b: [r(b).left, r(b).right], nt: [r(nt).left, r(nt).right], clipped: b.scrollWidth > b.clientWidth,
                        text: b.textContent, n_over: n.scrollWidth > n.clientWidth,
                        n_ellipsis: getComputedStyle(n).textOverflow, n_text: n.textContent};
            }""")
        finally:
            chromium.close()
    assert errors == []
    assert box["text"] == BANNER and not box["clipped"]
    assert box["nt"][0] - 0.5 <= box["b"][0] and box["b"][1] <= box["nt"][1] + 0.5, box
    assert box["n_text"].strip() and box["n_ellipsis"] == "ellipsis"
    if width >= 1280:
        assert not box["n_over"], f"{width}px 에서 고지 글이 줄었다"


def test_data_lines_present(built):
    # const D(d.json), const CV(tab4.js 첫 줄), const T3(tab3.js 자료 줄)가 한 번씩 실린다
    assert built.count("<script>const D = {") == 1
    assert built.count("const CV = {") == 1
    assert built.count("/*__T3DATA_BEGIN__*/") == 1
