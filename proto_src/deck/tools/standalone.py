#!/usr/bin/env python3
"""발표 덱을 영상까지 넣은 단일 HTML 로 만든다(오프라인에서 파일 하나로 여는 용도).

    python proto_src/deck/tools/standalone.py --check              # → local/submission/standalone/postlife_deck.html, postlife_app.html
    python proto_src/deck/tools/standalone.py --deck <index.html> --out <파일> [--app <console4.html>] [--check]

배포용 덱(site/deck/index.html)은 영상을 media/ 폴더의 파일로 읽는다. 그래서 index.html 하나만 받으면 영상 장이
정지 화면으로만 보인다. 이 도구는 영상 파일을 base64 로 문서 끝에 넣고, 문서를 열 때 Blob 주소로 바꿔 video 에 연결한다.
video 의 src 에 data: 주소를 직접 쓰지 않는 이유는 덱이 전체 보기에서 장을 통째로 복제하기 때문이다(긴 속성이 함께 복제된다).

덱의 "데모 열기" 링크(../proto/console4.html)는 같은 폴더에 함께 복사하는 분석 화면 파일(postlife_app.html)로 바꾼다.
분석 화면은 원래 파일 하나로 열리므로 그대로 복사한다. 두 파일을 같은 폴더에 두면 링크까지 오프라인에서 동작한다.

결과 파일은 수십 MB 라 저장소에 커밋하지 않는다(local/ 아래에 쓴다).
--check 를 주면 playwright 로 열어 외부 요청이 없는지, 영상마다 길이를 읽었는지 확인한다.
"""
from __future__ import annotations

import argparse
import base64
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VIDEO_SRC = re.compile(r'(<video\b[^>]*?)\ssrc="([^"]+)"')
DEMO_HREF = 'href="../proto/console4.html"'
APP_NAME = "postlife_app.html"

LOADER = """<script>
(function () {
  function attach(v) {
    var el = document.getElementById(v.getAttribute("data-inline"));
    if (!el) { return; }
    var bin = atob(el.textContent.replace(/\\s+/g, ""));
    var buf = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) { buf[i] = bin.charCodeAt(i); }
    v.src = URL.createObjectURL(new Blob([buf], { type: el.getAttribute("data-mime") || "video/mp4" }));
    el.textContent = "";
  }
  var list = Array.prototype.slice.call(document.querySelectorAll("video[data-inline]"));
  (function next() {
    var v = list.shift();
    if (!v) { return; }
    try { attach(v); } catch (e) {}
    setTimeout(next, 0);
  })();
})();
</script>"""


def make(deck: Path, out: Path, app: Path | None = None) -> list[tuple[str, int]]:
    doc = deck.read_text(encoding="utf-8")
    if app is not None:
        if DEMO_HREF not in doc:
            raise SystemExit("덱에서 데모 링크(../proto/console4.html)를 찾지 못했습니다.")
        doc = doc.replace(DEMO_HREF, f'href="{APP_NAME}"')
    media: dict[str, str] = {}

    def repl(m: re.Match) -> str:
        src = m.group(2)
        if src.startswith(("data:", "blob:", "http:", "https:")):
            return m.group(0)
        key = media.setdefault(src, f"inline-video-{len(media) + 1}")
        return f'{m.group(1)} data-inline="{key}"'

    doc = VIDEO_SRC.sub(repl, doc)
    if not media:
        raise SystemExit("영상 태그를 찾지 못했습니다. 덱 파일을 확인하세요.")
    blocks, sizes = [], []
    for src, key in media.items():
        f = deck.parent / src
        if not f.is_file():
            raise SystemExit(f"영상 파일이 없습니다: {f}")
        raw = f.read_bytes()
        sizes.append((src, len(raw)))
        blocks.append(f'<script type="text/plain" id="{key}" data-mime="video/mp4">{base64.b64encode(raw).decode("ascii")}</script>')
    tail = "\n".join(blocks) + "\n" + LOADER + "\n"
    i = doc.rfind("</body>")
    if i < 0:
        raise SystemExit("</body> 를 찾지 못했습니다.")
    doc = doc[:i] + tail + doc[i:]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    if app is not None:
        shutil.copyfile(app, out.parent / APP_NAME)
    return sizes


def check(path: Path, expect: int) -> list[str]:
    """파일 하나만 다른 폴더에서 열었을 때처럼 확인한다: 외부 요청 0, 영상마다 길이 읽힘."""
    from playwright.sync_api import sync_playwright

    problems: list[str] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1920, "height": 1080})
        reqs: list[str] = []
        page.on("request", lambda r: reqs.append(r.url))
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(path.resolve().as_uri())
        page.wait_for_function(
            "n => Array.from(document.querySelectorAll('video[data-inline]')).filter(v => v.readyState >= 1 && v.duration > 0).length >= n",
            arg=expect, timeout=60000)
        info = page.evaluate(
            "() => Array.from(document.querySelectorAll('video[data-inline]')).map(v => ({d: v.duration, w: v.videoWidth,"
            " has: !!v.closest('.slide') && v.closest('.slide').classList.contains('has-video')}))")
        b.close()
    outside = [u for u in reqs if not u.startswith(("file:", "blob:", "data:"))]
    local_other = [u for u in reqs if u.startswith("file:") and u != path.resolve().as_uri()]
    if outside:
        problems.append(f"외부 요청 {len(outside)}건: {outside[:3]}")
    if local_other:
        problems.append(f"다른 파일 요청 {len(local_other)}건: {local_other[:3]}")
    if errors:
        problems.append(f"스크립트 오류: {errors[:3]}")
    if len(info) != expect:
        problems.append(f"영상 수 {len(info)}, 기대 {expect}")
    for n, v in enumerate(info, 1):
        if not (v["d"] and v["d"] > 0 and v["w"] and v["has"]):
            problems.append(f"영상 {n}: 길이 {v['d']}, 폭 {v['w']}, 장 표시 {v['has']}")
    doc = path.read_text(encoding="utf-8")
    for href in set(re.findall(r'<a\b[^>]*\shref="([^"#][^"]*)"', doc)):
        if not href.startswith(("http:", "https:", "mailto:")) and not (path.parent / href).is_file():
            problems.append(f"링크 대상 파일이 없습니다: {href}")
    print("영상 길이(초):", ", ".join(f"{v['d']:.0f}" for v in info))
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--deck", default=str(ROOT / "site/deck/index.html"))
    ap.add_argument("--out", default=str(ROOT / "local/submission/standalone/postlife_deck.html"))
    ap.add_argument("--app", default=str(ROOT / "site/proto/console4.html"),
                    help="함께 복사할 분석 화면(같은 폴더에 postlife_app.html 로 복사하고 덱의 데모 링크를 그 파일로 바꾼다). 빈 값이면 하지 않음")
    ap.add_argument("--check", action="store_true", help="playwright 로 열어 외부 요청과 영상 재생 준비를 확인한다")
    a = ap.parse_args()
    out = Path(a.out)
    app = Path(a.app) if a.app else None
    sizes = make(Path(a.deck), out, app)
    for src, n in sizes:
        print(f"넣은 영상 {src} {n:,} 바이트")
    print(f"{out} {out.stat().st_size:,} 바이트, 영상 {len(sizes)}개")
    if app is not None:
        print(f"{out.parent / APP_NAME} {(out.parent / APP_NAME).stat().st_size:,} 바이트(분석 화면 복사)")
    if a.check:
        problems = check(out, len(sizes))
        if problems:
            print("\n".join(problems))
            sys.exit(1)
        print("확인: 외부 요청 0, 영상 모두 재생 준비됨")


if __name__ == "__main__":
    main()
