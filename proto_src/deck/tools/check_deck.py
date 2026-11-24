"""빌드한 덱을 브라우저로 열어 모든 장을 캡처하고, 겹침, 잘림, 작은 글자, 콘솔 오류, 외부 요청을 센다.

실행(playwright 가 든 파이썬):
    python tools/check_deck.py <out/index.html> <캡처 폴더>

1920x1080, 1366x768, 태블릿 크기 1180x820 세 해상도에서 장마다 PNG 를 남긴다(<폴더>/<해상도>/NN.png). 장마다의
점검 항목은 tools/shot.py 의 PROBE 와 같다(small 22px 미만, label 내용 글 26px 미만, overlap, overflow, clipped, outside,
태블릿 크기에서는 tiny: 창에 보이는 글자 높이 13px 미만). 이어서 키보드 이동(→, End, Home),
전체 장 보기(O), 발표자 노트(N)를 눌러 보고, 인쇄(PDF) 쪽수를 잰다.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shot import TABLET, inspect  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402


def main(html: str, out: str) -> None:
    path = Path(html)
    out_dir = Path(out)
    report = {}
    for w, h in ((1920, 1080), (1366, 768), TABLET):
        report[f"{w}x{h}"] = inspect(path, None, out_dir / f"{w}x{h}", (w, h))
    url = path.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(url + "#1")
        page.wait_for_timeout(800)
        page.keyboard.press("ArrowRight")
        page.keyboard.press("End")
        page.wait_for_timeout(300)
        report["end_hash"] = page.evaluate("location.hash")
        report["slides"] = page.evaluate("document.querySelectorAll('.slide').length")
        page.keyboard.press("Home")
        page.keyboard.press("o")
        page.wait_for_timeout(500)
        page.screenshot(path=str(out_dir / "overview.png"))
        page.keyboard.press("Escape")
        page.keyboard.press("n")
        page.wait_for_timeout(200)
        page.screenshot(path=str(out_dir / "notes.png"))
        pdf = page.pdf(prefer_css_page_size=True, print_background=True)
        (out_dir / "print.pdf").write_bytes(pdf)
        report["print_pdf_bytes"] = len(pdf)
        browser.close()
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
