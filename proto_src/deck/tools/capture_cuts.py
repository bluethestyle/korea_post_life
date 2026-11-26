"""데모 화면(site/proto/console4.html)의 작은 부분을 2배 배율로 찍어 덱의 확대 컷 JPEG 를 만든다.

실행(playwright 와 Pillow 가 든 파이썬, 리포 루트에서):
    python proto_src/deck/tools/capture_cuts.py site/proto/console4.html proto_src/deck/assets [--png <PNG 를 남길 폴더>]

만드는 파일(assets/<이름>.jpg, 16:9):
  cut_copy_button   담보 비교 탭 도구줄의 "비교표 복사" 버튼 둘레
  cut_pending_chip  암 수술비를 선택했을 때 상세 머리의 "검수 대기" 칩 둘레

캡처 조건은 화면이 처음 여는 기본값 그대로다(기준 종형과 비교 대상 타사를 바꾸지 않는다). capture_app.py 의
cancer_surgery 와 같은 조작(담보 비교 탭, 수술 단계, 암 수술비 선택)을 한다. 주간 마감 자료나 기준 종형 기본값이
바뀌면 이 명령 하나로 다시 찍고 덱을 다시 빌드한다. 암 수술비에 검수 대기 칩이 없으면(타사 비교가 모두 끝난 경우)
1로 끝난다. 그때는 15장(절차 5)의 검수 대기 칩 컷을 다른 예로 바꿔야 한다(15장의 글은 사실 자료 example_pending_case 를 따라간다).

버튼과 칩만(둘레 3px 포함) 잘라, 그 둘레의 화면 바탕색으로 채운 css 190x107px(16:9) 판의 가운데에 놓는다.
옆 버튼이나 위 줄의 글자가 반쯤 걸리지 않게 하려는 것이다. 판의 폭 190px 는 덱의 컷 폭(407px)에 놓았을 때
화면 글자(13px)가 약 28px 로 보이게 정한 값이다. 요소가 판보다 넓으면 판을 16:9 로 넓힌다(글자는 그만큼 작아진다).
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

SCALE = 2          # 2배 배율
CUT_W = 190        # 자르는 폭(css px). 높이는 16:9
MAX_BYTES = 250 * 1024


MARGIN = 3         # 요소 둘레(css px). 옆 버튼의 테두리가 들어오지 않게 작게 둔다


def clip_of(box: dict) -> dict:
    """요소 상자에 둘레를 더한 영역(css px)."""
    return {"x": box["x"] - MARGIN, "y": box["y"] - MARGIN,
            "width": box["width"] + 2 * MARGIN, "height": box["height"] + 2 * MARGIN}


def on_board(png: bytes) -> bytes:
    """잘라 낸 그림을 16:9 판의 가운데에 놓는다. 판의 색은 잘라 낸 그림의 네 모서리 색의 평균(화면 바탕색)."""
    img = Image.open(io.BytesIO(png)).convert("RGB")
    corners = [img.getpixel((0, 0)), img.getpixel((img.width - 1, 0)),
               img.getpixel((0, img.height - 1)), img.getpixel((img.width - 1, img.height - 1))]
    bg = tuple(round(sum(c[i] for c in corners) / 4) for i in range(3))
    bw = max(CUT_W * SCALE, img.width, round(img.height * 16 / 9))
    bh = round(bw * 9 / 16)
    board = Image.new("RGB", (bw, bh), bg)
    board.paste(img, ((bw - img.width) // 2, (bh - img.height) // 2))
    buf = io.BytesIO()
    board.save(buf, "PNG")
    return buf.getvalue()


def save_jpeg(png: bytes, out: Path) -> int:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    for q in (90, 86, 82, 78, 74, 70):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=False)
        if buf.tell() <= MAX_BYTES:
            break
    if buf.tell() > MAX_BYTES:
        sys.exit(f"{out.name}: 품질을 낮춰도 {buf.tell():,} 바이트(250KB 초과)")
    out.write_bytes(buf.getvalue())
    return buf.tell()


def main(html: str, out: str, png_dir: str | None) -> None:
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    url = Path(html).resolve().as_uri()
    vw, vh = 1920, 1080
    pngs: dict[str, bytes] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": vw, "height": vh}, device_scale_factor=SCALE)
        external, errors = [], []
        page.on("request", lambda r: external.append(r.url)
                if not r.url.startswith(("file:", "data:", "blob:")) else None)
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(url)
        page.wait_for_timeout(3000)
        page.click("#tab-cover")
        page.wait_for_timeout(2500)
        page.click('[data-cv-step="수술"]')
        page.wait_for_timeout(1500)
        slot = page.locator('[data-sid="STD_CA_SURG"]').first
        if slot.count() == 0:
            sys.exit("담보 비교 탭에서 암 수술비(STD_CA_SURG)를 찾지 못했습니다")
        slot.click()
        page.wait_for_timeout(2000)

        btn = page.locator("button", has_text="비교표 복사").first
        if btn.count() == 0 or not btn.is_visible():
            sys.exit("담보 비교 탭 도구줄에서 비교표 복사 버튼을 찾지 못했습니다")
        pngs["cut_copy_button"] = on_board(page.screenshot(clip=clip_of(btn.bounding_box())))

        # 상세 머리(왼쪽 패널)의 비교 결과 칩 가운데 "검수 대기"가 든 것
        chip = page.locator(".cv-bd", has_text="검수 대기").first
        if chip.count() == 0 or not chip.is_visible():
            sys.exit("암 수술비 상세 머리에 검수 대기 칩이 없습니다. 15장(절차 5)의 검수 대기 칩 컷을 다른 예로 바꿔야 합니다")
        pngs["cut_pending_chip"] = on_board(page.screenshot(clip=clip_of(chip.bounding_box())))
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
