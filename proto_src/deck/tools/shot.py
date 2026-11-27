"""장 몇 개만 빌드해 1920x1080 PNG 로 찍고, 겹침, 잘림, 작은 글자를 센다.

실행(playwright 가 든 파이썬, 작업 폴더의 deck 에서):
    python tools/shot.py 7 12-14 --content-dir content --facts ../facts.json --out-dir shots
    python tools/shot.py all --content-dir samples --out-dir shots_samples       # 폴더의 장 전부
    python tools/shot.py 7 --html out/index.html --out-dir shots                 # 빌드하지 않고 있는 HTML 을 찍음

- 장 번호는 쉼표나 공백으로 여럿, 범위(12-14), all 을 받는다. --html 을 주지 않으면 build.py 로 그 장들만 빌드한다
  (--content-dir, --facts, --refs, --deck 은 build.py 와 같다. 결과는 <out-dir>/index.html).
- 장마다 <out-dir>/NN.png 를 쓰고, 문제를 장마다 적는다. 문제가 하나라도 있으면 1로 끝난다.
- --size 로 창 크기를 바꾼다(기본 1920x1080. 태블릿 점검은 --size 1180x820).
  글자 크기 기준(2026-11-24 상향, 1920x1080 무대 기준): 내용을 전하는 글 26px 이상, 보조 글 22px 이상.
  small      글자 크기가 22px 미만(어느 글이든)
  label      내용을 전하는 글이 26px 미만(아래 AUX 의 보조 글 클래스 안이면 22px 까지 허용)
  tiny       창에 보이는 글자 높이(글자 크기 x 무대 배율)가 13px 미만(태블릿 크기 1180x820 에서 보는 기준)
  overlap    글자 상자 둘이 겹침(조상과 자손 사이는 빼고)
  overflow   부품 상자(.blk) 밖으로 그림이나 글자가 나감
  clipped    잘림(스크롤 크기가 상자보다 큼)
  outside    본문 요소가 무대의 본문 영역(머리 아래, 꼬리말 위) 밖으로 나감
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

# 글자 크기 기준(1920x1080 무대의 px). COMPONENTS.md 1.4절, tpl.html 머리 주석과 같다
SMALL_PX = 22          # 이보다 작은 글자는 슬라이드 안에 두지 않는다
LABEL_PX = 26          # 내용을 전하는 글(본문 라벨, 표의 값, 도해의 라벨, 요점)의 하한
TABLET = (1180, 820)   # 태블릿 점검 크기. 여기서 창에 보이는 글자 높이가 MIN_VISIBLE_PX 아래면 tiny
MIN_VISIBLE_PX = 13
# 보조 글로 치는 클래스(22px 까지 허용). tpl.html 의 CSS 에서 22~25px 로 둔 클래스는 모두 여기에 있어야 한다
AUX = (".ax, .c14, .gl, .ft, .fn, .hd, .cb, .notes, .c9-leg, .c9-li, .c9-gn, .c7.mini, .pb, .bd-um, .c8-tag, .c8-tick, .c8-src, "
       ".c19, .c12-lb i, .c12-mk, .c12-zk, .c5-k, .c5-hd, .c5-tag, .c5-note, .c3-note, .c9-note, .c10-sc, .c11-sc, .c11-lg, "
       ".c11-t span, .c16-todo, .c16-hd, .c15-todo b, .c15-todo.sm, .todo-i b, .c2t, .badge, .cm .l, .c1-n, .c3-num, .pill, .org, "
       ".c6-chip, .vchip, .lk-l, .qt-cite, .qt-gist, .svgb .aux")

PROBE = """
(arg) => {
  const no = arg.no, minvis = arg.minvis;
  const s = document.querySelector('.slide[data-no="' + no + '"]');
  if (!s) return [{kind: 'missing'}];
  const deck = document.getElementById('deck');
  const scale = deck.getBoundingClientRect().width / 1920;
  const base = s.getBoundingClientRect();
  const R = (el) => { const r = el.getBoundingClientRect(); return {x0: (r.left - base.left) / scale, y0: (r.top - base.top) / scale,
                       x1: (r.right - base.left) / scale, y1: (r.bottom - base.top) / scale}; };
  // 보조 글(22px 까지 허용): 축 눈금, 꼬리말과 쪽 번호, 각주, 용어 풀이, 칩과 배지, 범례, 작은 회색 한 줄(note, scope)
  const AUX = AUX_SELECTORS;
  const out = [];
  const name = (el) => el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/).join('.') : '');
  const txt = (el) => (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 30);
  // 글자를 직접 가진 요소
  const texts = [];
  for (const el of s.querySelectorAll('*')) {
    if (el.closest('.notes')) continue;
    const own = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own) continue;
    const r = R(el);
    if (r.x1 - r.x0 < 1 || r.y1 - r.y0 < 1) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs < SMALL_PX) out.push({kind: 'small', el: name(el), px: fs, text: txt(el)});
    else if (fs < LABEL_PX && !el.closest(AUX)) out.push({kind: 'label', el: name(el), px: fs, text: txt(el)});
    // svg 안의 글자는 viewBox 배율까지 곱한 크기로 본다(인라인 그림 블록)
    let vis = fs * scale;
    const svg = el.closest('svg');
    if (svg && svg.getAttribute('viewBox')) {
      const vb = svg.viewBox.baseVal, sr = svg.getBoundingClientRect();
      if (vb && vb.width && vb.height) {
        const k = Math.min(sr.width / vb.width, sr.height / vb.height);
        vis = fs * k;
        if (vis / scale < SMALL_PX - 0.01) out.push({kind: 'small', el: name(el), px: Math.round(vis / scale * 10) / 10, text: txt(el)});
      }
    }
    if (minvis && vis < minvis) out.push({kind: 'tiny', el: name(el), px: Math.round(vis * 10) / 10, text: txt(el)});
    if (el.tagName !== 'text') texts.push({el, r});
    const cs = getComputedStyle(el);
    if (cs.overflow !== 'visible' && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1))
      out.push({kind: 'clipped', el: name(el), sw: el.scrollWidth, cw: el.clientWidth, sh: el.scrollHeight, ch: el.clientHeight, text: txt(el)});
  }
  // 글자 상자 겹침: 줄 단위 상자(getClientRects)로 본다
  const lines = texts.map(t => {
    const rng = document.createRange(); rng.selectNodeContents(t.el);
    const rs = Array.from(rng.getClientRects()).filter(r => r.width > 1 && r.height > 1).map(r => ({
      x0: (r.left - base.left) / scale, y0: (r.top - base.top) / scale, x1: (r.right - base.left) / scale, y1: (r.bottom - base.top) / scale}));
    return {el: t.el, rs};
  });
  for (let i = 0; i < lines.length; i++) for (let j = i + 1; j < lines.length; j++) {
    const a = lines[i], b = lines[j];
    if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
    let hit = false;
    for (const p of a.rs) { for (const q of b.rs) {
      const w = Math.min(p.x1, q.x1) - Math.max(p.x0, q.x0), h = Math.min(p.y1, q.y1) - Math.max(p.y0, q.y0);
      if (w > 3 && h > 3) { hit = true; break; } } if (hit) break; }
    if (hit) out.push({kind: 'overlap', a: txt(a.el), b: txt(b.el)});
  }
  // 부품 상자 밖으로 나감
  for (const blk of s.querySelectorAll('.blk')) {
    const b = R(blk);
    let u = null;
    for (const el of blk.querySelectorAll('*')) {
      if (el.tagName === 'svg' && el.closest('.blk') === blk && getComputedStyle(el).overflow === 'visible' && el.children.length) {
        // overflow 가 보이는 svg 는 안의 도형으로 본다
      }
      const r = R(el);
      if (r.x1 - r.x0 < 1 && r.y1 - r.y0 < 1) continue;
      if (['svg', 'defs', 'symbol', 'use', 'marker', 'pattern'].includes(el.tagName.toLowerCase()) && el.tagName.toLowerCase() === 'svg') {
        // svg 자체 크기는 상자에 맞춰 두었으니 넘으면 그대로 센다
      }
      if (r.x0 < b.x0 - 2 || r.y0 < b.y0 - 2 || r.x1 > b.x1 + 2 || r.y1 > b.y1 + 2) {
        out.push({kind: 'overflow', el: name(el), blk: [Math.round(b.x0), Math.round(b.y0), Math.round(b.x1), Math.round(b.y1)],
                  box: [Math.round(r.x0), Math.round(r.y0), Math.round(r.x1), Math.round(r.y1)], text: txt(el)});
        break;
      }
    }
  }
  // 무대의 본문 영역(표지와 영상 장은 무대 전체)
  const full = s.classList.contains('cover') || s.classList.contains('video');
  const box = full ? {x0: 0, y0: 0, x1: 1920, y1: 1080} : {x0: 79, y0: 108, x1: 1841, y1: 992};
  for (const el of s.querySelectorAll('.dg *, .pts *, .gl *, .hl')) {
    const r = R(el);
    if (r.x1 - r.x0 < 1 && r.y1 - r.y0 < 1) continue;
    if (r.x0 < box.x0 - 1 || r.y0 < box.y0 - 1 || r.x1 > box.x1 + 1 || r.y1 > box.y1 + 1) {
      out.push({kind: 'outside', el: name(el), box: [Math.round(r.x0), Math.round(r.y0), Math.round(r.x1), Math.round(r.y1)], text: txt(el)});
      break;
    }
  }
  // 헤드라인과 도해 영역, 도해 영역과 요점 띠
  const hl = s.querySelector('.hl, .vhead'), dg = s.querySelector('.dg');
  if (hl && dg) {
    const a = R(hl);
    let top = 1e9;
    for (const el of dg.querySelectorAll('*')) { const r = R(el); if (r.y1 - r.y0 > 1) top = Math.min(top, r.y0); }
    if (a.y1 > top + 2) out.push({kind: 'overlap', a: 'headline', b: 'diagram', y: [Math.round(a.y1), Math.round(top)]});
  }
  return out;
}
""".replace("AUX_SELECTORS", json.dumps(AUX)).replace("SMALL_PX", str(SMALL_PX)).replace("LABEL_PX", str(LABEL_PX))

# 사진은 최종 상태를 찍는다. 장 안의 등장 애니메이션(블록의 build 순서 포함)은 끈다
NO_ANIM = ".slide .dg, .slide .pts, .slide .blk { animation: none !important; }"


def parse_numbers(args: list[str]) -> list[int] | None:
    if not args or args == ["all"]:
        return None
    out: list[int] = []
    for a in args:
        for chunk in a.replace(" ", ",").split(","):
            if not chunk:
                continue
            if "-" in chunk:
                x, y = chunk.split("-", 1)
                out.extend(range(int(x), int(y) + 1))
            else:
                out.append(int(chunk))
    return sorted(set(out))


def inspect(html: Path, numbers: list[int] | None, out_dir: Path, size: tuple[int, int] = (1920, 1080),
            shoot: bool = True) -> dict:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"issues": {}, "external": [], "console_errors": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": size[0], "height": size[1]})
        page.on("request", lambda r: report["external"].append(r.url)
                if not r.url.startswith(("file:", "data:", "blob:")) else None)
        page.on("console", lambda m: report["console_errors"].append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: report["console_errors"].append(str(e)))
        page.goto(html.resolve().as_uri())
        page.add_style_tag(content=NO_ANIM)
        page.wait_for_timeout(1200)
        minvis = MIN_VISIBLE_PX if tuple(size) == TABLET else 0
        # 키보드 안내(#help)와 하단 이동 막대(#deck-nav)는 사진에는 넣지 않는다
        page.evaluate("['help','deck-nav'].forEach(id => { var el = document.getElementById(id); if (el) el.classList.add('off'); });")
        present =page.evaluate("Array.from(document.querySelectorAll('.slide')).map(s => +s.dataset.no)")
        nos = [n for n in (numbers or present) if n in present]
        missing = [n for n in (numbers or []) if n not in present]
        if missing:
            report["missing"] = missing
        for n in nos:
            idx = present.index(n) + 1
            page.evaluate(f"location.hash = '#{idx}'")
            page.wait_for_timeout(700)
            if shoot:
                page.screenshot(path=str(out_dir / f"{n:02d}.png"))
            found = page.evaluate(PROBE, {"no": n, "minvis": minvis})
            if found:
                report["issues"][n] = found
        browser.close()
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("numbers", nargs="*", help="장 번호(7 12-14 또는 all)")
    ap.add_argument("--html", default=None, help="이미 빌드한 HTML(주면 빌드하지 않는다)")
    ap.add_argument("--content-dir", default=str(HERE / "content"))
    ap.add_argument("--deck", default=None)
    ap.add_argument("--facts", default=None)
    ap.add_argument("--refs", default=None)
    ap.add_argument("--assets", action="append", default=None)
    ap.add_argument("--out-dir", default="shots")
    ap.add_argument("--size", default="1920x1080", help="창 크기(예: 1366x768, 태블릿 1180x820)")
    a = ap.parse_args()
    size = tuple(int(x) for x in a.size.lower().split("x"))
    nums = parse_numbers(a.numbers)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if a.html:
        html = Path(a.html)
    else:
        html = out_dir / "index.html"
        cmd = [sys.executable, str(HERE / "build.py"), "--content-dir", a.content_dir, "--out", str(html),
               "--used", str(out_dir / "facts_used.json")]
        for opt in ("deck", "facts", "refs"):
            if getattr(a, opt):
                cmd += [f"--{opt}", getattr(a, opt)]
        for d in a.assets or []:
            cmd += ["--assets", d]
        if nums:
            cmd += ["--only", ",".join(map(str, nums))]
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode:
            print(r.stderr.strip(), file=sys.stderr)
            raise SystemExit(r.returncode)
    rep = inspect(html, nums, out_dir, size)
    bad = sum(len(v) for v in rep["issues"].values()) + len(rep["external"]) + len(rep["console_errors"])
    for n, found in rep["issues"].items():
        print(f"[{n:02d}] 문제 {len(found)}건")
        for f in found[:12]:
            print("   ", json.dumps(f, ensure_ascii=False))
    if rep["external"] or rep["console_errors"]:
        print("외부 요청:", rep["external"][:3], "콘솔 오류:", rep["console_errors"][:3])
    print(f"PNG: {out_dir}  문제 {bad}건")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
