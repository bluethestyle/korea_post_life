#!/usr/bin/env python3
"""작품설명서(proto_src/form)에 넣을 분석 화면 캡처를 다시 찍는다.

실행(playwright 와 Pillow 가 든 파이썬, 리포 루트에서):
    python proto_src/form/shoot.py                       # site/proto/console4.html → proto_src/form/assets/
    python proto_src/form/shoot.py --html <console4.html> --out <폴더>

캡처 조건은 화면이 처음 여는 기본값 그대로다(조건, 기준 종형, 비교 대상 타사를 바꾸지 않는다). 주간 마감 자료나
기준 종형 기본값이 바뀌면 이 명령 하나로 다시 찍고 작품설명서를 다시 빌드한다.

화면 해상도는 1280x720 이다(전체 캡처와 확대 컷 모두). 이 해상도에서 화면의 표가 가장 좁게 접혀, 같은 폭의 A4 에서
글자가 더 크게 보인다. 확대 컷의 영역은 DOM 요소의 boundingBox 로 구하고 고정 좌표를 쓰지 않는다.

만드는 파일(<out>/<이름>.jpg):
  summary         전체 요약(첫 화면). 모양을 보여 주는 전체 캡처(폭 1600px)
  tab_gate        인수기준 비교 탭, 전체 캡처
  tab_insight     영업 인사이트 탭, 전체 캡처
  tab_graph       관계 그래프 탭, 전체 캡처
  cancer_surgery  담보 비교 탭에서 수술 단계의 암 수술비를 선택한 상태, 전체 캡처
  talk_preview    영업 인사이트 탭의 응대 화법 A4 카드(1920x1080 화면에서 2배 배율, 카드 전체)
  cut_kpi         전체 요약의 핵심 수 네 개(수와 라벨)를 이어 붙인 띠(2배 배율)
  cut_gate        인수기준 비교 탭의 회사별 가입 가능 종형 수와 고지항목 비교 표 일부(2배 배율)
  cut_cover       담보 비교 탭에서 암 수술비를 선택했을 때의 회사별 조건 표, 표 요소만(2배 배율)
  cut_insight     영업 인사이트 탭의 문장 카드 하나(2배 배율)
  cut_talk        응대 화법 A4 카드의 위쪽 부분(2배 배율)
  cut_head_a      분석 화면 상단의 조건 줄과 버튼(2배 배율)
  cut_head_b      분석 화면 상단의 탭 여섯(2배 배율)
  cut_copy_button 담보 비교 탭 도구줄의 비교표 복사 버튼(3배 배율)
  cut_pending_chip 암 수술비 상세 머리의 검수 대기 칩(3배 배율)
인쇄한 A4 에서 전체 캡처의 글자는 읽히지 않는다. 글자가 읽혀야 하는 곳에는 확대 컷을 쓴다.
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
VW, VH = 1280, 720            # 전체 캡처와 확대 컷의 화면 해상도
BW, BH = 1920, 1080           # 응대 화법 카드 전체를 담는 큰 화면
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

def save_jpeg(png: bytes | Image.Image, out: Path, width: int | None = None) -> int:
    img = png if isinstance(png, Image.Image) else Image.open(io.BytesIO(png))
    img = img.convert("RGB")
    if width and img.width > width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    for q in (88, 84, 80, 76, 72, 68, 64, 60):
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


def open_tab(page: Page, url: str, tab: str) -> None:
    open_home(page, url)
    page.click(f"#tab-{tab}")
    page.wait_for_timeout(2500)


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


def union(boxes: list[dict]) -> dict:
    x0 = min(b["x"] for b in boxes)
    y0 = min(b["y"] for b in boxes)
    x1 = max(b["x"] + b["width"] for b in boxes)
    y1 = max(b["y"] + b["height"] for b in boxes)
    return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}


def box_of(page: Page, selector: str, nth: int = 0, scroll: bool = True, what: str = "") -> dict:
    """DOM 요소의 boundingBox. 화면 밖이면 스크롤해 들여온다. 없으면 멈춘다."""
    loc = page.locator(selector).nth(nth)
    if loc.count() == 0:
        sys.exit(f"{what or selector}: 요소를 찾지 못했습니다({selector})")
    if scroll:
        loc.scroll_into_view_if_needed()
        page.wait_for_timeout(250)
    b = loc.bounding_box()
    if not b or b["width"] <= 0 or b["height"] <= 0:
        sys.exit(f"{what or selector}: 요소가 보이지 않습니다({selector})")
    return b


def clamp(box: dict, vw: int = VW, vh: int = VH) -> dict:
    x0, y0 = max(0, box["x"]), max(0, box["y"])
    x1, y1 = min(vw, box["x"] + box["width"]), min(vh, box["y"] + box["height"])
    return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}


def stitch(images: list[Image.Image], horizontal: bool, gap: int, bg: tuple[int, int, int], rule: bool = False) -> Image.Image:
    """DOM 요소마다 자른 그림을 이어 붙인다. rule 이면 그림 사이에 가는 선을 긋는다."""
    if horizontal:
        w = sum(i.width for i in images) + gap * (len(images) - 1)
        h = max(i.height for i in images)
    else:
        w = max(i.width for i in images)
        h = sum(i.height for i in images) + gap * (len(images) - 1)
    out = Image.new("RGB", (w, h), bg)
    pos = 0
    for n, im in enumerate(images):
        if horizontal:
            out.paste(im, (pos, 0))
            pos += im.width
            if rule and n < len(images) - 1:
                for y in range(h):
                    out.putpixel((pos + gap // 2, y), (150, 158, 166))
            pos += gap
        else:
            out.paste(im, (0, pos))
            pos += im.height
            if rule and n < len(images) - 1:
                for x in range(w):
                    out.putpixel((x, pos + gap // 2), (150, 158, 166))
            pos += gap
    return out


def grab(page: Page, box: dict) -> Image.Image:
    return Image.open(io.BytesIO(page.screenshot(clip=clamp(box)))).convert("RGB")


def corner_color(im: Image.Image) -> tuple[int, int, int]:
    return im.getpixel((2, 2))


def watch(page: Page, external: list, errors: list) -> None:
    page.on("request", lambda r: external.append(r.url) if not r.url.startswith(("file:", "data:", "blob:")) else None)
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)


def cut_kpi(page: Page) -> Image.Image:
    """전체 요약의 핵심 수 네 개: 고객군과 시장, 인수기준 비교, 담보 비교, 영업 인사이트의 수와 라벨."""
    parts = []
    for tab in ("market", "gate", "cover", "insight"):
        parts.append(grab(page, pad(box_of(page, f"#tab-{tab} .hm-head", what=f"전체 요약 {tab} 수"), 6)))
    return stitch(parts, True, 30, corner_color(parts[0]), rule=True)


def cut_gate(page: Page) -> Image.Image:
    """인수기준 비교 탭의 표로 보기: 회사별 가입 가능 종형 수 셋과 고지항목 비교 표."""
    page.click("#gt-btn-tbl")
    page.wait_for_timeout(2000)
    n = page.locator(".gt-ao").count()
    if n < 3:
        sys.exit("인수기준 비교 표로 보기에서 회사별 가입 가능 종형 수(.gt-ao)를 찾지 못했습니다")
    tiles = []
    for i in range(3):
        b = box_of(page, ".gt-ao", i, what="회사별 가입 가능 종형 수")
        # 요소는 칸 폭만큼 넓어서, 안의 글자가 차지한 오른쪽 끝까지만 자른다
        w = page.evaluate("""(i) => { const el = document.querySelectorAll('.gt-ao')[i]; const r0 = el.getBoundingClientRect();           let m = 0;
          const it = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let t; while ((t = it.nextNode())) { if (!t.textContent.trim()) continue;
            const g = document.createRange(); g.selectNodeContents(t); for (const r of g.getClientRects()) m = Math.max(m, r.right); }
          return m - r0.left; }""", i)
        tiles.append(grab(page, pad({"x": b["x"], "y": b["y"], "width": min(b["width"], w), "height": b["height"]}, 5)))
    bg = corner_color(tiles[0])
    row = stitch(tiles, True, 28, bg, rule=True)
    scroll = box_of(page, "#gt-q .gt-scroll", what="고지항목 비교 표")
    head = box_of(page, "#gt-q .panel-h", scroll=False, what="고지항목 비교 머리")
    u = union([head, scroll])
    # 패널의 흰 테두리 안쪽만 자른다
    table = grab(page, {"x": u["x"] + 2, "y": u["y"] + 2, "width": u["width"] - 4, "height": u["height"] - 4})
    return stitch([row, table], False, 14, bg)


def cut_cover(page: Page) -> Image.Image:
    """암 수술비를 선택했을 때의 회사별 조건 표(상세 패널)."""
    box_of(page, ".ev-sec", what="회사별 조건 영역")
    return grab(page, pad(box_of(page, "table.cv-ct", scroll=False, what="회사별 조건 표"), 5))


def cut_insight(page: Page) -> Image.Image:
    return grab(page, pad(box_of(page, ".ins-it", 0, what="영업 인사이트 문장 카드"), 2))


def cut_talk(page: Page) -> Image.Image:
    card = box_of(page, "#insight-card", what="응대 화법 A4 카드")
    return grab(page, {"x": card["x"], "y": card["y"], "width": card["width"], "height": min(card["height"], 360, VH - card["y"] - 12)})


def cut_head(page: Page) -> tuple[Image.Image, Image.Image]:
    a = union([box_of(page, "#cond-sum-t", scroll=False, what="조건 줄"), box_of(page, "#th-cond-btns", scroll=False, what="버튼 줄")])
    strip = page.locator("#tab-gate").first.locator("xpath=..")
    b = strip.bounding_box()
    if not b:
        sys.exit("탭 줄을 찾지 못했습니다")
    return grab(page, pad(a, 8)), grab(page, b)


def shoot(html: Path, out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    url = html.resolve().as_uri()
    full: dict[str, Image.Image | bytes] = {}
    sharp: dict[str, Image.Image | bytes] = {}
    external: list[str] = []
    errors: list[str] = []

    def png(page: Page) -> Image.Image:
        return Image.open(io.BytesIO(page.screenshot())).convert("RGB")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # 전체 캡처와 확대 컷: 1280x720 화면, 2배 배율
        page = browser.new_page(viewport={"width": VW, "height": VH}, device_scale_factor=2)
        watch(page, external, errors)
        open_home(page, url)
        full["summary"] = png(page)
        sharp["cut_kpi"] = cut_kpi(page)
        for tab in ("gate", "insight", "graph"):
            open_tab(page, url, tab)
            full[f"tab_{tab}"] = png(page)
            if tab == "gate":
                sharp["cut_head_a"], sharp["cut_head_b"] = cut_head(page)
                sharp["cut_gate"] = cut_gate(page)
            if tab == "insight":
                sharp["cut_insight"] = cut_insight(page)
                sharp["cut_talk"] = cut_talk(page)
        open_cancer_surgery(page, url)
        full["cancer_surgery"] = png(page)
        sharp["cut_cover"] = cut_cover(page)
        page.close()

        # 응대 화법 카드 전체: 1920x1080 화면, 2배 배율
        page = browser.new_page(viewport={"width": BW, "height": BH}, device_scale_factor=2)
        watch(page, external, errors)
        open_tab(page, url, "insight")
        box = page.evaluate(TALK_JS)
        if not box:
            sys.exit("영업 인사이트 탭에서 응대 화법 미리 보기를 찾지 못했습니다")
        sharp["talk_preview"] = page.screenshot(clip=box)
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
    for name, img in full.items():
        sizes[name] = save_jpeg(img, out_dir / f"{name}.jpg", FULL_W)
    for name, img in sharp.items():
        sizes[name] = save_jpeg(img, out_dir / f"{name}.jpg")
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
