"""데모 화면(console4.html)을 1920x1080 으로 캡처해 덱에 넣을 사진 넷을 만든다.

실행(playwright 가 든 파이썬):
    python tools/capture_app.py <console4.html 경로> <저장 폴더>

만드는 파일: first.png(첫 화면), market.png(고객군과 시장 탭),
cover.png(담보 비교 탭), graph.png(관계 그래프 탭에서 암보장, 일반암 진단비 선택).
화면 용어를 바꾼 뒤에는 탭과 노드 이름이 달라질 수 있으니 아래 선택자를 함께 고친다.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main(html: str, out: str) -> None:
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        external, errors = [], []
        page.on("request", lambda r: external.append(r.url)
                if not r.url.startswith(("file:", "data:", "blob:")) else None)
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(Path(html).resolve().as_uri())
        page.wait_for_timeout(3000)
        page.screenshot(path=str(out_dir / "first.png"))
        page.click("#tab-market")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(out_dir / "market.png"))
        page.click("#tab-cover")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(out_dir / "cover.png"))
        page.click("#tab-graph")
        page.wait_for_timeout(2500)
        page.locator("span.gn-t", has_text="암보장").first.click()
        page.wait_for_timeout(2000)
        target = page.locator("text=일반암 진단비")
        visible = [i for i in range(target.count()) if target.nth(i).is_visible()]
        if not visible:
            sys.exit("관계 그래프에서 '일반암 진단비'를 찾지 못했습니다")
        target.nth(visible[0]).click()
        page.wait_for_timeout(2500)
        page.screenshot(path=str(out_dir / "graph.png"))
        browser.close()
    if external or errors:
        sys.exit(f"외부 요청 {external[:3]}, 콘솔 오류 {errors[:3]}")
    print("캡처 4장:", out_dir)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
