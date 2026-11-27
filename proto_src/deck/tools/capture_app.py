"""데모 화면(site/proto/console4.html)을 1920x1080 으로 캡처해 덱에 넣을 JPEG 를 만든다(장당 250KB 이하).

실행(playwright 와 Pillow 가 든 파이썬):
    python tools/capture_app.py <console4.html 경로> <assets 폴더> [--png <PNG 를 남길 폴더>]

만드는 파일(assets/<이름>.jpg):
  summary          전체 요약(첫 화면)
  tab_market       고객군과 시장 탭
  tab_gate         인수기준 비교 탭(화면 id: tab-gate)
  tab_cover        담보 비교 탭
  tab_insight      영업 인사이트 탭
  tab_graph        관계 그래프 탭(첫 화면)
  talk_preview     영업 인사이트 탭의 비교 요약지 미리 보기(A4 카드 부분만)
  cancer_surgery   담보 비교 탭에서 수술 단계의 암 수술비를 선택한 상태
화면 용어를 바꾼 뒤에는 탭 id 와 글자가 달라질 수 있으니 아래 선택자를 함께 고친다.
JPEG 는 폭 1600px 로 줄이고, 250KB 를 넘으면 품질을 낮춰 다시 쓴다.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright

WIDTH = 1600
MAX_BYTES = 250 * 1024
TABS = ("market", "gate", "cover", "insight", "graph")


def save_jpeg(png: bytes, out: Path) -> int:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    if img.width > WIDTH:
        img = img.resize((WIDTH, round(img.height * WIDTH / img.width)), Image.LANCZOS)
    for q in (84, 80, 76, 72, 68, 64, 60, 56, 52):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=False)
        if buf.tell() <= MAX_BYTES:
            break
    if buf.tell() > MAX_BYTES:
        sys.exit(f"{out.name}: 품질을 낮춰도 {buf.tell():,} 바이트(250KB 초과)")
    out.write_bytes(buf.getvalue())
    return buf.tell()


def open_home(page: Page, url: str) -> None:
    page.goto(url)
    page.wait_for_timeout(3000)


def main(html: str, out: str, png_dir: str | None) -> None:
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    pngs: dict[str, bytes] = {}
    url = Path(html).resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        external, errors = [], []
        page.on("request", lambda r: external.append(r.url)
                if not r.url.startswith(("file:", "data:", "blob:")) else None)
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        open_home(page, url)
        pngs["summary"] = page.screenshot()
        for tab in TABS:
            open_home(page, url)
            page.click(f"#tab-{tab}")
            page.wait_for_timeout(2500)
            pngs[f"tab_{tab}"] = page.screenshot()
            if tab == "insight":
                # 비교 요약지 미리 보기: 제목 글자가 든 패널(인쇄 버튼과 A4 카드가 든 가장 가까운 큰 상자).
                # 용어 교체 뒤 보이는 제목은 "비교 요약지"이고 "미리 보기"는 aria-label 에만 남아 그것부터 찾는다.
                box = page.evaluate("""() => {
                  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
                  const h = Array.from(document.querySelectorAll('[aria-label$="미리 보기"]')).find(vis)
                    || Array.from(document.querySelectorAll('*')).find(e => e.children.length === 0 && vis(e)
                    && /미리 보기$/.test((e.textContent || '').trim()));
                  if (!h) return null;
                  let el = h;
                  while (el.parentElement) {
                    const r = el.parentElement.getBoundingClientRect();
                    if (r.width > 700) break;
                    el = el.parentElement;
                    if (r.height >= 500) break;
                  }
                  const r = el.getBoundingClientRect();
                  if (r.height < 300) return null;
                  // 스크롤 상자 안에서 보이는 부분까지만(아래 꼬리말이 들어오지 않게)
                  let c = el.parentElement, bottom = Math.min(r.bottom, 1080);
                  while (c) {
                    const oy = getComputedStyle(c).overflowY;
                    if (oy !== 'visible') { bottom = Math.min(bottom, c.getBoundingClientRect().bottom); break; }
                    c = c.parentElement;
                  }
                  return {x: r.x - 8, y: r.y - 8, width: r.width + 16, height: bottom - r.y + 8};
                }""")
                if not box:
                    sys.exit("영업 인사이트 탭에서 비교 요약지 미리 보기를 찾지 못했습니다")
                pngs["talk_preview"] = page.screenshot(clip=box)
            if tab == "cover":
                page.click('[data-cv-step="수술"]')
                page.wait_for_timeout(1500)
                slot = page.locator('[data-sid="STD_CA_SURG"]').first
                if slot.count() == 0:
                    sys.exit("담보 비교 탭에서 암 수술비(STD_CA_SURG)를 찾지 못했습니다")
                slot.click()
                page.wait_for_timeout(2000)
                pngs["cancer_surgery"] = page.screenshot()
        browser.close()
    if external or errors:
        sys.exit(f"외부 요청 {external[:3]}, 콘솔 오류 {errors[:3]}")
    for name, png in pngs.items():
        if png_dir:
            Path(png_dir).mkdir(parents=True, exist_ok=True)
            (Path(png_dir) / f"{name}.png").write_bytes(png)
        size = save_jpeg(png, out_dir / f"{name}.jpg")
        print(f"{name}.jpg {size:,} 바이트")
    print(f"캡처 {len(pngs)}장: {out_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html")
    ap.add_argument("out")
    ap.add_argument("--png", default=None)
    a = ap.parse_args()
    main(a.html, a.out, a.png)
