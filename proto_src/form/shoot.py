#!/usr/bin/env python3
"""작품설명서(proto_src/form)에 넣을 분석 화면 캡처를 다시 찍는다.

실행(playwright 와 Pillow 가 든 파이썬, 리포 루트에서):
    python proto_src/form/shoot.py                       # site/proto/console4.html → proto_src/form/assets/
    python proto_src/form/shoot.py --html <console4.html> --out <폴더>

캡처 조건은 화면이 처음 여는 기본값 그대로다(조건, 기준 종형, 비교 대상 타사를 바꾸지 않는다). 주간 마감 자료나
기준 종형 기본값이 바뀌면 이 명령 하나로 다시 찍고 작품설명서를 다시 빌드한다.

만드는 파일(<out>/<이름>.jpg):
  summary         전체 요약(첫 화면), 1920x1080 화면을 폭 1600px 로
  tab_gate        인수기준 비교 탭
  tab_insight     영업 인사이트 탭
  tab_graph       관계 그래프 탭
  cancer_surgery  담보 비교 탭에서 수술 단계의 암 수술비를 선택한 상태
  talk_preview    영업 인사이트 탭의 응대 화법 A4 카드(2배 배율)
  head_gate       인수기준 비교 탭의 머리(제목, 조건 줄과 버튼, 탭 여섯)를 2배 배율로 자른 띠
  cut_copy_button 담보 비교 탭 도구줄의 비교표 복사 버튼(3배 배율)
  cut_pending_chip 암 수술비 상세 머리의 검수 대기 칩(3배 배율)
인쇄한 A4 에서 화면의 작은 글자는 다 읽히지 않는다. 배율을 올려 찍는 것은 PDF 를 확대했을 때 글자가 선명하게
보이게 하려는 것이고, 작품설명서는 캡처 옆에 번호와 설명 글을 따로 둔다.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VW, VH = 1920, 1080
FULL_W = 1600
MAX_BYTES = 300 * 1024

TALK_JS = """() => {
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
  let c = el.parentElement, bottom = Math.min(r.bottom, 1080);
  while (c) {
    const oy = getComputedStyle(c).overflowY;
    if (oy !== 'visible') { bottom = Math.min(bottom, c.getBoundingClientRect().bottom); break; }
    c = c.parentElement;
  }
  return {x: r.x - 8, y: r.y - 8, width: r.width + 16, height: bottom - r.y + 8};
}"""

def save_jpeg(png: bytes, out: Path, width: int | None = None) -> int:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    if width and img.width > width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    for q in (86, 82, 78, 74, 70, 66, 62):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=False)
        if buf.tell() <= MAX_BYTES:
            break
    if buf.tell() > MAX_BYTES:
        sys.exit(f"{out.name}: 품질을 낮춰도 {buf.tell():,} 바이트({MAX_BYTES // 1024}KB 초과)")
    out.write_bytes(buf.getvalue())
    return buf.tell()


def open_home(page: Page, url: str) -> None:
    page.goto(url)
    page.wait_for_timeout(3000)


def open_cancer_surgery(page: Page, url: str) -> None:
    open_home(page, url)
    page.click("#tab-cover")
    page.wait_for_timeout(2500)
    page.click('[data-cv-step="수술"]')
    page.wait_for_timeout(1500)
    slot = page.locator('[data-sid="STD_CA_SURG"]').first
    if slot.count() == 0:
        sys.exit("담보 비교 탭에서 암 수술비(STD_CA_SURG)를 찾지 못했습니다")
    slot.click()
    page.wait_for_timeout(2000)


def pad(box: dict, m: float) -> dict:
    return {"x": box["x"] - m, "y": box["y"] - m, "width": box["width"] + 2 * m, "height": box["height"] + 2 * m}


def watch(page: Page, external: list, errors: list) -> None:
    page.on("request", lambda r: external.append(r.url) if not r.url.startswith(("file:", "data:", "blob:")) else None)
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)


def shoot(html: Path, out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    url = html.resolve().as_uri()
    full: dict[str, bytes] = {}
    sharp: dict[str, bytes] = {}
    external: list[str] = []
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # 1배: 화면 전체(알아보기용 썸네일)
        page = browser.new_page(viewport={"width": VW, "height": VH})
        watch(page, external, errors)
        open_home(page, url)
        full["summary"] = page.screenshot()
        for tab in ("gate", "insight", "graph"):
            open_home(page, url)
            page.click(f"#tab-{tab}")
            page.wait_for_timeout(2500)
            full[f"tab_{tab}"] = page.screenshot()
        open_cancer_surgery(page, url)
        full["cancer_surgery"] = page.screenshot()
        page.close()

        # 2배: 응대 화법 카드, 인수기준 비교 탭 머리
        page = browser.new_page(viewport={"width": VW, "height": VH}, device_scale_factor=2)
        watch(page, external, errors)
        open_home(page, url)
        page.click("#tab-insight")
        page.wait_for_timeout(2500)
        box = page.evaluate(TALK_JS)
        if not box:
            sys.exit("영업 인사이트 탭에서 응대 화법 미리 보기를 찾지 못했습니다")
        sharp["talk_preview"] = page.screenshot(clip=box)
        open_home(page, url)
        page.click("#tab-gate")
        page.wait_for_timeout(2500)
        sharp["head_gate"] = page.screenshot(clip={"x": 40, "y": 28, "width": VW - 80, "height": 178})
        page.close()

        # 3배: 비교표 복사 버튼, 검수 대기 칩
        page = browser.new_page(viewport={"width": VW, "height": VH}, device_scale_factor=3)
        watch(page, external, errors)
        open_cancer_surgery(page, url)
        btn = page.locator("button", has_text="비교표 복사").first
        if btn.count() == 0 or not btn.is_visible():
            sys.exit("담보 비교 탭 도구줄에서 비교표 복사 버튼을 찾지 못했습니다")
        sharp["cut_copy_button"] = page.screenshot(clip=pad(btn.bounding_box(), 6))
        chip = page.locator(".cv-bd", has_text="검수 대기").first
        if chip.count() == 0 or not chip.is_visible():
            sys.exit("암 수술비 상세 머리에 검수 대기 칩이 없습니다. 작품설명서의 원문 확인 단계 그림을 다른 예로 바꿔야 합니다")
        sharp["cut_pending_chip"] = page.screenshot(clip=pad(chip.bounding_box(), 6))
        page.close()
        browser.close()
    if external or errors:
        sys.exit(f"외부 요청 {external[:3]}, 콘솔 오류 {errors[:3]}")
    sizes = {}
    for name, png in full.items():
        sizes[name] = save_jpeg(png, out_dir / f"{name}.jpg", FULL_W)
    for name, png in sharp.items():
        sizes[name] = save_jpeg(png, out_dir / f"{name}.jpg")
    return sizes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", default=str(ROOT / "site" / "proto" / "console4.html"))
    ap.add_argument("--out", default=str(HERE / "assets"))
    a = ap.parse_args()
    sizes = shoot(Path(a.html), Path(a.out))
    for name, size in sizes.items():
        print(f"{name}.jpg {size:,} 바이트")
    print(f"캡처 {len(sizes)}장: {a.out}")


if __name__ == "__main__":
    main()
