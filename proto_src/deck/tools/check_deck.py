"""빌드한 덱을 브라우저로 열어 모든 장을 캡처하고, 넘침과 콘솔 오류와 외부 요청을 센다.

실행(playwright 가 든 파이썬):
    python tools/check_deck.py <out/index.html> <캡처 폴더>

1920x1080 과 1366x768 두 해상도에서 장마다 PNG 를 남긴다(<폴더>/<해상도>/NN.png).
넘침 판정: 머리와 꼬리를 뺀 요소가 본문 영역(위 140px, 아래 950px, 좌우 80px~1840px) 밖으로
나가거나, 글 상자의 내용이 상자보다 크면(scrollWidth/scrollHeight) 적는다. 표지와 마무리, 영상 장은
전체 장(0~1920, 0~1080)을 영역으로 본다.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PROBE = """
(idx) => {
  const s = document.querySelectorAll('.slide')[idx];
  const deck = document.getElementById('deck');
  const scale = deck.getBoundingClientRect().width / 1920;
  const base = s.getBoundingClientRect();
  const full = s.classList.contains('cover') || s.classList.contains('closing') || s.classList.contains('video');
  const box = full ? {l: 0, t: 0, r: 1920, b: 1080} : {l: 79, t: 139, r: 1841, b: 951};
  const out = [];
  for (const el of s.querySelectorAll('*')) {
    if (el.closest('.hd, .ft, .notes, .spine')) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    const x0 = (r.left - base.left) / scale, y0 = (r.top - base.top) / scale;
    const x1 = (r.right - base.left) / scale, y1 = (r.bottom - base.top) / scale;
    const name = el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ').join('.') : '');
    if (x0 < box.l - 1 || y0 < box.t - 1 || x1 > box.r + 1 || y1 > box.b + 1) {
      out.push({kind: 'outside', el: name, box: [Math.round(x0), Math.round(y0), Math.round(x1), Math.round(y1)], text: (el.innerText || '').slice(0, 40)});
    }
    const cs = getComputedStyle(el);
    if (['P', 'H1', 'H2', 'H3', 'LI', 'TD', 'TH', 'DIV'].includes(el.tagName) && el.children.length === 0) {
      if (el.scrollWidth > el.clientWidth + 1 || (cs.overflow !== 'visible' && el.scrollHeight > el.clientHeight + 1)) {
        out.push({kind: 'clipped', el: name, sw: el.scrollWidth, cw: el.clientWidth, text: (el.innerText || '').slice(0, 40)});
      }
    }
  }
  // 꼬리 글이 쪽 번호와 겹치는지
  const src = s.querySelector('.ft .src'), pg = s.querySelector('.ft .pg');
  if (src && pg) {
    const a = src.getBoundingClientRect(), b = pg.getBoundingClientRect();
    if (a.right > b.left - 4) out.push({kind: 'footer-overlap', text: src.innerText.slice(0, 40)});
    if (a.height / scale > 40) out.push({kind: 'footer-wrap', text: src.innerText.slice(0, 40)});
  }
  return out;
}
"""


def main(html: str, out: str) -> None:
    url = Path(html).resolve().as_uri()
    out_dir = Path(out)
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in ((1920, 1080), (1366, 768)):
            page = browser.new_page(viewport={"width": w, "height": h})
            external, errors = [], []
            page.on("request", lambda r: external.append(r.url)
                    if not r.url.startswith(("file:", "data:", "blob:")) else None)
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url + "#1")
            page.wait_for_timeout(1500)
            total = page.evaluate("document.querySelectorAll('.slide').length")
            folder = out_dir / f"{w}x{h}"
            folder.mkdir(parents=True, exist_ok=True)
            issues = {}
            for i in range(total):
                page.evaluate(f"location.hash = '#{i + 1}'")
                page.wait_for_timeout(900)
                page.screenshot(path=str(folder / f"{i + 1:02d}.png"))
                found = page.evaluate(PROBE, i)
                if found:
                    issues[i + 1] = found
            # 키보드 이동 확인
            page.evaluate("location.hash = '#1'")
            page.wait_for_timeout(300)
            page.keyboard.press("ArrowRight")
            page.keyboard.press("End")
            page.wait_for_timeout(300)
            at_end = page.evaluate("location.hash")
            page.keyboard.press("Home")
            page.keyboard.press("o")
            page.wait_for_timeout(500)
            page.screenshot(path=str(folder / "overview.png"))
            page.keyboard.press("Escape")
            page.keyboard.press("n")
            page.wait_for_timeout(200)
            page.screenshot(path=str(folder / "notes.png"))
            report[f"{w}x{h}"] = {"slides": total, "external": external, "console_errors": errors,
                                  "end_hash": at_end, "issues": issues}
            page.close()
        # 인쇄(PDF) 쪽수
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(url)
        page.wait_for_timeout(1000)
        pdf = page.pdf(prefer_css_page_size=True, print_background=True)
        (out_dir / "print.pdf").write_bytes(pdf)
        report["print_pdf_bytes"] = len(pdf)
        browser.close()
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
