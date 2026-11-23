"""site/index.html을 file://로 열어 폭 380px·1280px에서 탭마다 확인한다.

    python3 scripts/dev/check_site_browser.py site/index.html <스크린숏 폴더>

- 콘솔 error, 페이지 오류, 외부로 나가는 요청이 없는지
- 가로로 화면을 벗어나는 요소가 없는지(표의 가로 스크롤 영역 안쪽은 제외)
- 글자가 잘린 요소, 세로로 찌그러진 칸, 서로 겹친 글자가 없는지
- 처음 높이가 한도(380px 폭 12,000px, 1280px 폭 8,000px)를 넘지 않는지
- 접어 둔 목록을 펼친 상태, 거르기·찾기·쪽 넘기기를 쓴 상태에서도 위 문제가 없는지
- 화면 3: 처음 보이는 비교 종형 열이 회사마다 하나인지, 비교표를 "모두 보기"로 펼친 상태에서도 위 문제가 없고 표준담보가 한 줄도 빠지지 않는지
- 화면 4: 종형마다 특약을 모두 담고 결과 막대와 표를 "모두 보기"로 펼친 상태에서도 위 문제가 없고 표준담보가 한 줄도 빠지지 않는지,
  단추를 키보드(Enter, Space)로 펼치고 접을 수 있는지
- 탭마다 해설 결론이 있고, 해설을 펼쳐도 위 문제가 없으며, 끼우지 못한 {변수} 자리가 보이지 않는지
- 화면 1의 접힌 묶음을 펼친 상태
- 응대 카드: 기본 상태와 줄이 가장 많이 차는 상태(우체국 통합건강보험 2504 대 한화 일반가입형, 전체 분야)에서
  미리 보기와 인쇄용 한 장에 넘침, 잘림, 겹침이 없는지, 인쇄 매체로 만든 A4 PDF가 한 쪽인지
- 탭별·상태별 화면 사진 저장
"""
import json
import logging
import re
import sys
from pathlib import Path

import pdfplumber
from playwright.sync_api import sync_playwright

logging.getLogger("pdfminer").setLevel(logging.ERROR)     # 글꼴 정보 경고는 쪽 수 확인과 관계없다

SITE = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
TABS = ["s1", "s2", "s3", "s4", "s5", "s6"]
LIMIT = {380: 12000, 1280: 8000}          # 펼치기 전 화면 높이 한도
HEIGHT = "document.documentElement.scrollHeight"
PRINT_HEIGHT_MM = 297 - 2 * 10           # A4 세로에서 위아래 여백(app.css의 @page)을 뺀 높이
PX_PER_MM = 96 / 25.4
SLOTS_JS = "() => [...document.querySelectorAll('.comment, .sheet')].filter(e => /[{}]/.test(e.innerText)).length"

OVERFLOW_JS = """
() => {
  const vw = document.documentElement.clientWidth;
  const out = [];
  const inScroll = el => el.closest('.scroll') !== null;
  if (document.documentElement.scrollWidth > vw + 1) out.push({kind: 'page', sw: document.documentElement.scrollWidth, vw});
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('dialog:not([open])')) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (!inScroll(el) && (r.right > vw + 1 || r.left < -1)) {
      out.push({kind: 'outside', tag: el.tagName, cls: el.className, left: Math.round(r.left), right: Math.round(r.right), text: (el.textContent || '').slice(0, 40)});
    }
    const cs = getComputedStyle(el);
    const clips = ['hidden', 'clip'].includes(cs.overflowX) || ['hidden', 'clip'].includes(cs.overflowY) || cs.textOverflow === 'ellipsis';
    if (clips && el.tagName !== 'SELECT' && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1) && (el.textContent || '').trim()) {
      out.push({kind: 'clipped', tag: el.tagName, cls: el.className, text: (el.textContent || '').slice(0, 40)});
    }
  }
  // 표 칸 안에서 옆 칸으로 삐져나온 글자(가로 스크롤 영역 안쪽도 본다)
  for (const cell of document.querySelectorAll('.scroll td, .scroll th')) {
    const c = cell.getBoundingClientRect();
    if (c.width === 0) continue;
    for (const el of cell.querySelectorAll('*')) {
      const r = el.getBoundingClientRect();
      if (r.width && (r.right > c.right + 1 || r.left < c.left - 1)) {
        out.push({kind: 'spill', tag: el.tagName, cls: el.className, over: Math.round(r.right - c.right), text: (el.textContent || '').slice(0, 40)});
        break;
      }
    }
  }
  // 글자가 한두 자씩 세로로 찌그러진 칸
  for (const el of document.querySelectorAll('td, th, button, label, li, p, span, dd, dt')) {
    if (el.closest('dialog:not([open])')) continue;
    const text = (el.textContent || '').trim();
    const r = el.getBoundingClientRect();
    if (text.length >= 5 && r.width > 0 && r.width < 34 && r.height > 60) {
      out.push({kind: 'crushed', tag: el.tagName, cls: el.className, w: Math.round(r.width), text: text.slice(0, 30)});
    }
  }
  return out.slice(0, 20);
}
"""

# 글자끼리 겹치는지: 같은 부모 안에서 글자를 가진 요소 상자가 서로 겹치면 잡는다
OVERLAP_JS = """
() => {
  const out = [];
  const leaves = [...document.querySelectorAll('#main *, header *, nav *, #condbar *')].filter(el => {
    if (el.children.length) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && (el.textContent || '').trim() && !['OPTION'].includes(el.tagName)
      && !el.closest('.agebar') && !el.closest('.ttrack');
  });
  const byParent = new Map();
  for (const el of leaves) {
    const key = el.parentElement;
    if (!byParent.has(key)) byParent.set(key, []);
    byParent.get(key).push(el);
  }
  for (const group of byParent.values()) {
    for (let i = 0; i < group.length; i++) for (let j = i + 1; j < group.length; j++) {
      const a = group[i].getBoundingClientRect(), b = group[j].getBoundingClientRect();
      const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const hgt = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (w > 2 && hgt > 2) out.push({a: group[i].textContent.slice(0, 30), b: group[j].textContent.slice(0, 30), cls: group[i].parentElement.className});
    }
  }
  return out.slice(0, 20);
}
"""


# 응대 카드 한 장 안에서: 한 장 밖으로 나간 요소, 잘린 글자, 칸 밖으로 삐진 글자, 겹친 글자와 묶음, 끼우지 못한 변수 자리
CARD_JS = """
(sel) => {
  const root = document.querySelector(sel);
  if (!root) return [{kind: 'card missing', sel}];
  const out = [];
  const box = root.getBoundingClientRect();
  const text = el => (el.textContent || '').trim().slice(0, 40);
  for (const el of root.querySelectorAll('*')) {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    if (r.right > box.right + 1 || r.left < box.left - 1 || r.bottom > box.bottom + 1) out.push({kind: 'card outside', tag: el.tagName, text: text(el)});
    const cs = getComputedStyle(el);
    const clips = ['hidden', 'clip'].includes(cs.overflowX) || ['hidden', 'clip'].includes(cs.overflowY) || cs.textOverflow === 'ellipsis';
    if (clips && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1) && text(el)) out.push({kind: 'card clipped', tag: el.tagName, text: text(el)});
  }
  for (const cell of root.querySelectorAll('td, th')) {
    const c = cell.getBoundingClientRect();
    for (const el of cell.querySelectorAll('*')) {
      const r = el.getBoundingClientRect();
      if (r.width && (r.right > c.right + 1 || r.left < c.left - 1)) { out.push({kind: 'card spill', text: text(el)}); break; }
    }
  }
  const leaves = [...root.querySelectorAll('*')].filter(el => !el.children.length && text(el) && el.getBoundingClientRect().width > 0);
  const byParent = new Map();
  for (const el of leaves) { if (!byParent.has(el.parentElement)) byParent.set(el.parentElement, []); byParent.get(el.parentElement).push(el); }
  for (const group of byParent.values()) {
    for (let i = 0; i < group.length; i++) for (let j = i + 1; j < group.length; j++) {
      const a = group[i].getBoundingClientRect(), b = group[j].getBoundingClientRect();
      if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 2 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 2) out.push({kind: 'card overlap', a: text(group[i]), b: text(group[j])});
    }
  }
  const kids = [...root.children].filter(el => el.getBoundingClientRect().height > 0);
  for (let i = 0; i + 1 < kids.length; i++) {
    const a = kids[i].getBoundingClientRect(), b = kids[i + 1].getBoundingClientRect();
    if (b.top < a.bottom - 1) out.push({kind: 'card blocks overlap', a: kids[i].className || kids[i].tagName, b: kids[i + 1].className || kids[i + 1].tagName});
  }
  if (/[{}]/.test(root.innerText)) out.push({kind: 'card unfilled slot'});
  return out.slice(0, 20);
}
"""


class Run:
    def __init__(self, page, width, problems):
        self.page, self.width, self.problems, self.counts = page, width, problems, {}

    def look(self, label, shot=None, limit=None):
        """지금 상태에서 넘침·잘림·겹침을 세고, 필요하면 사진을 찍고 높이 한도를 본다."""
        page = self.page
        over = page.evaluate(OVERFLOW_JS)
        lap = page.evaluate(OVERLAP_JS)
        height = page.evaluate(HEIGHT)
        if shot:
            page.screenshot(path=str(OUT / f"{shot}_{self.width}.png"), full_page=True)
        self.counts[label] = (len(over), len(lap), height)
        slots = page.evaluate(SLOTS_JS)
        if slots:
            self.problems.append((self.width, label, {"kind": "unfilled slot", "blocks": slots}))
        note = ""
        if limit is not None and height > limit:
            note = f"  ← 한도 {limit}px 초과"
            self.problems.append((self.width, label, {"kind": "too tall", "height": height, "limit": limit}))
        print(f"[{self.width}px] {label}: 벗어남·잘림 {len(over)}건, 겹침 {len(lap)}건, 높이 {height}px{note}")
        self.problems += [(self.width, label, o) for o in over + lap]
        return height

    def typing(self, key, text):
        """찾기 상자에 한 글자씩 쳐 넣는다. 치는 동안 입력 상자가 다시 만들어지면(한글 입력이 끊김) 문제로 적는다."""
        box = self.page.locator(f'[data-key="{key}"]')
        box.click()
        self.page.evaluate("key => { window.__box = document.querySelector('[data-key=\"' + key + '\"]'); }", key)
        box.press_sequentially(text)
        same = self.page.evaluate("key => document.activeElement === window.__box && window.__box.isConnected && window.__box.value", key)
        if same != text:
            self.problems.append((self.width, f"찾기 {key}", {"kind": "input replaced", "value": same}))

    def rows(self, selector):
        return self.page.locator(selector).count()

    def show_all(self, prefix, label):
        """접혀 있는 "모두 보기" 단추(data-key가 prefix로 시작)를 모두 눌러 펼치고, 누른 단추의 data-key를 돌려준다."""
        keys = self.page.eval_on_selector_all(f'[data-key^="{prefix}"][aria-expanded="false"]', "els => els.map(e => e.dataset.key)")
        for key in keys:
            self.page.click(f'[data-key="{key}"]')
            if self.page.get_attribute(f'[data-key="{key}"]', "aria-expanded") != "true":
                self.problems.append((self.width, label, {"kind": "not expanded", "key": key}))
        return keys

    def fold_back(self, keys, label):
        for key in keys:
            self.page.click(f'[data-key="{key}"]')
            if self.page.get_attribute(f'[data-key="{key}"]', "aria-expanded") != "false":
                self.problems.append((self.width, label, {"kind": "not folded", "key": key}))

    def s4_all_shown(self, label):
        """화면 4 결과를 펼친 상태에서 표준담보가 막대와 표에 하나도 빠지지 않았는지 본다(구획 제목의 표준담보 수와 견준다)."""
        head = self.page.locator("#screen-s4 section.block > h3", has_text="표준담보별 실제 지급액").inner_text()
        found = re.search(r"표준담보 (\d+)개", head)
        if not found:
            return
        total = int(found.group(1))
        shown = (self.rows("#s4-bars .barrow"), self.rows("#s4-pay tbody tr"))
        if shown != (total, total):
            self.problems.append((self.width, label, {"kind": "rows hidden after expand", "total": total, "bars": shown[0], "table": shown[1]}))

    def s3_all_shown(self, label):
        """화면 3 비교표를 펼친 상태에서 표준담보가 한 줄도 빠지지 않았는지 본다(표 위 줄의 표준담보 수와 견준다)."""
        found = re.search(r"표준담보 (\d+)개", self.page.locator("#screen-s3 .list-body > p.pager").first.inner_text())
        if not found:
            return
        shown = self.rows("table.cmp tbody th[scope=row]")
        if shown != int(found.group(1)):
            self.problems.append((self.width, label, {"kind": "rows hidden after expand", "total": int(found.group(1)), "table": shown}))

    def card(self, label, pages):
        """열려 있는 응대 카드를 본다: 미리 보기, 인쇄 매체의 한 장(높이 한도), A4 PDF 쪽 수."""
        page, width = self.page, self.width
        page.wait_for_selector("#card[open] .sheet")
        found = page.evaluate(CARD_JS, "#card-body .sheet")
        page.screenshot(path=str(OUT / f"card_{label}_{width}.png"))
        page.emulate_media(media="print")
        found += page.evaluate(CARD_JS, "#print-card .sheet")
        shown = page.evaluate("""() => ({main: getComputedStyle(document.getElementById('main')).display,
            dialog: getComputedStyle(document.getElementById('card')).display,
            card: getComputedStyle(document.getElementById('print-card')).display,
            height: document.querySelector('#print-card .sheet').getBoundingClientRect().height,
            rows: document.querySelector('#print-card .sheet').dataset.rows})""")
        page.emulate_media(media="null")         # 흉내를 끈다. page.pdf는 인쇄 매체로 만든다
        height_mm = shown["height"] / PX_PER_MM
        if shown["main"] != "none" or shown["dialog"] != "none" or shown["card"] == "none":
            found.append({"kind": "print shows more than the card", **shown})
        if height_mm > PRINT_HEIGHT_MM:
            found.append({"kind": "card taller than A4", "mm": round(height_mm, 1)})
        pdf = OUT / f"card_{label}_{width}.pdf"
        page.pdf(path=str(pdf), format="A4", print_background=True)
        with pdfplumber.open(pdf) as doc:
            count = len(doc.pages)
            first = doc.pages[0].extract_text() or ""
        if count != 1:
            found.append({"kind": "card pdf pages", "pages": count})
        if "배포" not in first or "심사 결과" not in first.replace("\n", " "):
            found.append({"kind": "card pdf text", "head": first[:60]})
        pages.append((width, label, count))
        print(f"[{width}px] 응대 카드 {label}: PDF {count}쪽, 인쇄 높이 {height_mm:.0f}mm / {PRINT_HEIGHT_MM}mm, "
              f"비교표 상한 {shown['rows']}행, 넘침·잘림·겹침 {len(found)}건")
        self.problems += [(width, f"card {label}", f) for f in found]


def check_width(browser, width, problems, pages):
    context = browser.new_context(viewport={"width": width, "height": 900}, device_scale_factor=1, offline=True)
    page = context.new_page()
    errors, requests = [], []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: requests.append(r.url) if not r.url.startswith("file://") and not r.url.startswith("data:") else None)
    page.goto(SITE.as_uri())
    run = Run(page, width, problems)

    # ---- 처음 상태: 탭마다 높이 한도, 해설 결론, 해설 펼침 ----
    for tab in TABS:
        page.click(f"#tab-{tab}")
        page.wait_for_selector(f"#screen-{tab}")
        run.look(f"{tab} 처음", shot=tab, limit=LIMIT[width])
        assert page.locator("#main .comment .conclusion").count() == 1, f"{tab}에 해설 결론이 없음"
        page.click(f'[data-key="fold-cm-{tab}"]')
        assert page.locator(f"#main details.fold[open] dl.kv").count() >= 1, f"{tab} 해설을 펼치지 못함"
        run.look(f"{tab} 해설 펼침", shot=f"{tab}_comment")
        page.click(f'[data-key="fold-cm-{tab}"]')

    # ---- 화면 1: 묶음 셋과 접힌 곳 ----
    page.click("#tab-s1")
    text = page.inner_text("#main")
    assert "코드가 집계한 요약" in text and "이번 주차 시장 소식" in text and "우열 표시가 바뀐 표준담보" in text, "화면 1 묶음이 빠짐"
    assert "보험료 자료가 없습니다" in text, "화면 1의 늘 보이는 유의 줄이 없음"
    for i in range(page.locator('#main details:not([open]) > summary').count()):
        page.locator('#main details:not([open]) > summary').first.click()
    assert page.locator("#main .tiles .tile").count() >= 5, "들어 있는 자료 타일이 펼쳐지지 않음"
    run.look("s1 접힌 곳 모두 펼침", shot="s1_open")

    # ---- 화면 2: 나이, 회사 거르기, 판매 종료 포함 ----
    page.click("#tab-s2")
    for age in ("85", "", "70"):
        page.fill("#age", age)
        run.look(f"s2 나이 {age or '없음'}", limit=LIMIT[width])
    orgs = page.locator('[data-key^="s2-org-"]')
    for i in range(orgs.count()):
        orgs.nth(i).click()
        run.look(f"s2 회사 {i}", shot=f"s2_org{i}" if i == orgs.count() - 1 else None, limit=LIMIT[width])
    if orgs.count():
        orgs.nth(0).click()
    if page.locator('[data-key="s2-ended"]').count():
        page.click('[data-key="s2-ended"]')
        run.look("s2 판매 종료 포함", shot="s2_all", limit=LIMIT[width])
    for i in range(page.locator('#main details > summary').count()):
        page.locator('#main details > summary').nth(i).click()
    run.look("s2 접힌 곳 모두 펼침", shot="s2_open")

    # ---- 화면 3 ----
    page.click("#tab-s3")
    page.fill("#age", "50")
    # 기준 종형 바꾸기(상품 → 종형). 처음에는 기준 종형과, 다른 회사마다 맞붙는 종형 하나씩만 열로 나온다
    kinds = '[data-key^="s3-base-"]:not([data-key*="-rev-"]):not([data-key*="-org-"])'
    for r in range(max(1, page.locator('[data-key^="s3-base-rev-"]').count())):
        if page.locator('[data-key^="s3-base-rev-"]').count():
            page.locator('[data-key^="s3-base-rev-"]').nth(r).click()
        for i in range(max(1, page.locator(kinds).count())):
            if page.locator(kinds).count():
                page.locator(kinds).nth(i).click()
            shown = run.rows("table.cmp thead th") - 1
            assert 1 <= shown <= 4, f"처음 보이는 종형 열이 너무 많음: {shown}"
            # 체크된 종형(=열)은 회사마다 하나다. 종형ID의 앞 조각이 기관코드다
            picked = page.eval_on_selector_all('[data-key^="s3-col-"]:checked', "els => els.map(e => e.dataset.key.slice(7))")
            orgs = [v.split("_")[0] for v in picked]
            if len(picked) != shown or len(orgs) != len(set(orgs)):
                problems.append((width, "s3 처음 열", {"kind": "default columns not one per company", "shown": shown, "picked": picked}))
            run.look(f"s3 기준 {page.locator('.picked strong').inner_text()} ({shown}열)", limit=LIMIT[width])
    if page.locator('[data-key^="s3-base-rev-"]').count():
        page.locator('[data-key^="s3-base-rev-"]').first.click()
    cols_default = run.rows("table.cmp thead th") - 1
    # 보장 분야 하나씩, 전체
    majors = page.locator('[data-key^="s3-major-"]')
    for i in range(majors.count()):
        majors.nth(i).click()
        last = i == majors.count() - 1
        run.look(f"s3 보장 분야 {majors.nth(i).inner_text()}", shot="s3_major_all" if last else None)
    # 비교표는 표준담보가 많으면 앞의 몇 줄만 그린다. 전체 분야를 "모두 보기"로 펼친 상태에서도 문제가 없고 한 줄도 빠지지 않는지 본다
    keys = run.show_all("s3-more-", "s3 전체 분야")
    if keys:
        run.look("s3 전체 분야·표 모두 펼침", shot="s3_major_all_open")
        run.s3_all_shown("s3 전체 분야")
        run.fold_back(keys, "s3 전체 분야")
    # 모든 종형을 열로(표도 모두 펼쳐 모든 칸을 본다)
    page.click('[data-key="s3-cols-all"]')
    all_cols = run.rows("table.cmp thead th") - 1
    assert all_cols > cols_default, "모든 종형 보기가 열을 늘리지 않음"
    run.look(f"s3 모든 종형({all_cols}열)·전체 분야", shot="s3_allcols")
    keys = run.show_all("s3-more-", "s3 모든 종형")
    if keys:
        run.look(f"s3 모든 종형({all_cols}열)·전체 분야·표 모두 펼침", shot="s3_allcols_open")
        run.s3_all_shown("s3 모든 종형")
    page.evaluate("() => { const b = document.querySelector('.scroll:has(table.cmp)'); b.scrollLeft = 500; b.scrollIntoView(); }")
    page.screenshot(path=str(OUT / f"s3_allcols_scrolled_{width}.png"))
    run.look("s3 모든 종형·옆으로 민 상태")
    page.evaluate("() => { document.querySelector('.scroll:has(table.cmp)').scrollLeft = 0; }")
    run.fold_back(keys, "s3 모든 종형")
    page.click('[data-key="s3-cols-peers"]')
    assert run.rows("table.cmp thead th") - 1 == cols_default
    majors.nth(0).click()
    # 이름 찾기, 차이만 보기
    run.typing("s3-q", "수술")
    found = run.rows("table.cmp tbody th[scope=row]")
    assert found > 0 and all("수술" in t for t in page.locator("table.cmp tbody th[scope=row]").all_inner_texts()), "표준담보 찾기 결과가 다름"
    run.look(f"s3 표준담보 찾기 '수술' {found}개", shot="s3_search")
    page.fill('[data-key="s3-q"]', "없는이름")
    assert "조건에 맞는 표준담보가 없습니다" in page.inner_text("#main")
    page.fill('[data-key="s3-q"]', "")
    for value in ("diff", "gap", "hold", ""):
        page.select_option('[data-key="s3-diff"]', value)
        run.look(f"s3 보기 {value or '모든 담보'}")
    if page.locator('[data-key="s3-empty"]').count():
        page.click('[data-key="s3-empty"]')
        run.look("s3 빈 표준담보 포함")
        page.click('[data-key="s3-empty"]')
    for age in ("85", "", "70"):
        page.fill("#age", age)
        run.look(f"s3 나이 {age or '없음'}", shot=f"s3_age{age or 'none'}", limit=LIMIT[width])
    page.fill("#age", "50")
    # 매핑 검토 대기 목록: 펼치기, 거르기, 찾기, 쪽 넘기기
    page.click('[data-key="fold-s3-wait"]')
    run.look("s3 검토 대기 목록 펼침", shot="s3_wait_open")
    assert 0 < run.rows("#main details.fold[open] table tbody tr") <= 20
    if page.locator('[data-key="s3-wait-top-next"]').count():
        page.click('[data-key="s3-wait-bottom-next"]')
        assert "2 /" in page.locator("#main details.fold[open] .pager").first.inner_text()
        run.look("s3 검토 대기 2쪽")
    if page.locator('[data-key="s3-wait-org"]').count():
        page.select_option('[data-key="s3-wait-org"]', index=1)
        run.look("s3 검토 대기 회사 거르기")
        page.select_option('[data-key="s3-wait-org"]', "")
    page.select_option('[data-key="s3-wait-rec"]', "-")
    assert all("추천 없음" in t for t in page.locator("#main details.fold[open] table tbody tr").all_inner_texts())
    run.look("s3 검토 대기 추천 없음만")
    page.select_option('[data-key="s3-wait-rec"]', "")
    run.typing("s3-wait-q", "수술")
    texts = page.locator("#main details.fold[open] table tbody tr").all_inner_texts()
    assert texts and all("수술" in t for t in texts), "검토 대기 찾기 결과가 다름"
    run.look("s3 검토 대기 찾기 '수술'", shot="s3_wait_search")
    page.locator('#main details.fold[open] table .btn').first.click()
    page.wait_for_selector("dialog[open]")
    assert "매핑 검토 대기" in page.inner_text("#detail-body")
    run.look("s3 검토 대기 근거 창")
    page.click("#detail-close")
    page.fill('[data-key="s3-wait-q"]', "")
    tops = page.locator('[data-key^="s3-wait-top-"]')
    if tops.count():
        tops.first.click()
        run.look("s3 추천 표준담보 단추로 거르기")
        page.select_option('[data-key="s3-wait-rec"]', "")
    page.click('[data-key="fold-s3-wait"]')
    # 근거 창: 대표 급부가 맨 위, 가입 한도 자료가 없는 종형은 그 사실을 적는다
    page.click(".cellbtn")
    page.wait_for_selector("dialog[open]")
    assert "대표" in page.locator("#detail-body .ev").first.inner_text(), "근거 창의 첫 줄이 대표 급부가 아님"
    over = page.evaluate(OVERFLOW_JS)
    page.screenshot(path=str(OUT / f"s3_detail_{width}.png"))
    print(f"[{width}px] 근거 창: 벗어남·잘림 {len(over)}건")
    run.problems += [(width, "detail", o) for o in over]
    page.click("#detail-close")
    # 금액 하나로 담기지 않는 급부(지급기준구분 차등지급 따위)의 칸은 금액 대신 값 이름을 적는다. 그런 칸이 없는 자료에서는 건너뛴다
    form_cells = page.locator(".cellbtn:has(.main.noamt)")
    if form_cells.count():
        cell_text = form_cells.first.inner_text()
        assert any(f in cell_text for f in ("차등지급", "실손보상", "분할지급", "현물급부")), cell_text
        assert "금액 하나로 적을 수 없는 급부" in cell_text and "감액 없음" not in cell_text, cell_text
        form_cells.first.click()
        page.wait_for_selector("dialog[open]")
        body = page.inner_text("#detail-body")
        assert "원문에서 확인" in body, "금액 없는 급부의 근거 창에 감액을 원문에서 확인하라는 글이 없음"
        over = page.evaluate(OVERFLOW_JS)
        page.screenshot(path=str(OUT / f"s3_detail_form_{width}.png"))
        print(f"[{width}px] 근거 창(금액 없는 급부): 벗어남·잘림 {len(over)}건")
        run.problems += [(width, "detail form", o) for o in over]
        page.click("#detail-close")
    soft = page.locator(".cellbtn:has(.main.soft):not(:has(.main.noamt))")
    if soft.count():
        cell_text = soft.first.inner_text()
        assert "기준 가입" in cell_text and "자료 없음" in cell_text, cell_text
        soft.first.click()
        page.wait_for_selector("dialog[open]")
        body = page.inner_text("#detail-body")
        assert "가입 한도" in body and "이 나이에는 가입할 수 없음" not in body, "가입 한도 자료가 없는 줄을 가입 불가로 적음"
        over = page.evaluate(OVERFLOW_JS)
        page.screenshot(path=str(OUT / f"s3_detail_nocap_{width}.png"))
        print(f"[{width}px] 근거 창(가입 한도 자료 없음): 벗어남·잘림 {len(over)}건")
        run.problems += [(width, "detail nocap", o) for o in over]
        page.click("#detail-close")
    else:
        print(f"[{width}px] 가입 한도 자료가 없는 칸이 처음 화면에 없음")

    # ---- 응대 카드 ----
    page.fill("#age", "")
    assert page.locator('[data-key="s3-card"]').is_disabled(), "나이가 없는데 응대 카드 단추가 켜짐"
    page.fill("#age", "50")
    page.click('[data-key="s3-cols-peers"]') if page.locator('[data-key="s3-cols-peers"]').count() else None
    page.click('[data-key="s3-card"]')
    run.card("기본", pages)
    peers = page.locator('[data-key^="card-peer-"]')
    if peers.count() > 1:
        peers.nth(1).click()
        run.card("비교 종형 바꿈", pages)
    page.click("#card-close")
    assert not page.evaluate("document.body.classList.contains('card-print')"), "카드를 닫아도 인쇄가 카드로 남음"
    # 줄이 가장 많이 차는 상태: 우체국 통합건강보험 2504 대 한화 일반가입형, 전체 분야
    total = page.locator('[data-key^="s3-base-rev-"]', has_text="통합건강보험")
    if total.count():
        total.first.click()
        page.click('[data-key="s3-major-*"]')
        page.click('[data-key="s3-card"]')
        page.wait_for_selector("#card[open] .sheet")
        # 카드가 처음 고르는 비교 종형은 판정할 수 있는 담보가 있는 열이다(한도 미공시인 한화는 아님). 한화 일반가입형을 직접 고른다
        hanwha = page.locator('[data-key^="card-peer-"]', has_text="일반가입형")
        if hanwha.count():
            hanwha.first.click()
        title = page.inner_text("#card-body .sheet .c-pair")
        assert "통합건강보험" in title and "일반가입형" in title, f"카드의 두 종형이 다름: {title}"
        body_rows = page.locator("#card-body .sheet table.c-cmp tbody tr").count()
        assert 0 < body_rows <= 12, f"카드 비교표 본문이 {body_rows}행"
        run.card("통합2504 대 한화 일반가입형 전체 분야", pages)
        page.click("#card-close")
        page.locator('[data-key^="s3-base-rev-"]').first.click()
    else:
        problems.append((width, "card", {"kind": "통합건강보험 기준 종형을 찾지 못함"}))

    # ---- 화면 4 ----
    page.click("#tab-s4")
    page.click('[data-key="s4-max"]')
    run.look("s4 최대로 담기", shot="s4_max", limit=LIMIT[width])
    names = page.eval_on_selector_all(".rider .rname", "els => els.map(e => e.textContent)")
    base = next(i for i, n in enumerate(names) if "암입원수술" in n)
    dependent = next(i for i, n in enumerate(names) if "요양병원암입원" in n)
    page.locator(".rider input[type=checkbox]").nth(base).uncheck()
    row = page.locator(".rider").nth(dependent)
    assert row.locator("input[type=checkbox]").is_disabled() and "가입해야 부가할 수 있음" in row.inner_text(), "선행가입 제약이 걸리지 않음"
    page.locator(".rider input[type=checkbox]").nth(base).check()
    main = page.locator(".rider").nth(0).locator("input.amount")
    main.fill("1000")
    main.press("Tab")
    amounts = [float(v) for v in page.eval_on_selector_all("input.amount", "els => els.map(e => e.value)")]
    names = page.eval_on_selector_all(".rider:has(input.amount) .rname", "els => els.map(e => e.textContent)")
    linked = [a for n, a in zip(names, amounts) if "암진단" in n or "뇌출혈진단" in n]
    assert linked and all(a <= 1000 for a in linked), f"최대연동 제약이 걸리지 않음: {linked}"
    run.look("s4 주계약 1,000만원", shot="s4_main1000")
    for age in ("85", "", "70"):
        page.fill("#age", age)
        run.look(f"s4 나이 {age or '없음'}")
    page.fill("#age", "50")
    # 종형 고르기: 회사마다, 상품마다, 종형마다 처음 상태와 모두 담은 상태
    tallest = 0
    for o in range(max(1, page.locator('[data-key^="s4-variant-org-"]').count())):
        if page.locator('[data-key^="s4-variant-org-"]').count():
            page.locator('[data-key^="s4-variant-org-"]').nth(o).click()
        for r in range(max(1, page.locator('[data-key^="s4-variant-rev-"]').count())):
            if page.locator('[data-key^="s4-variant-rev-"]').count():
                page.locator('[data-key^="s4-variant-rev-"]').nth(r).click()
            kinds = '[data-key^="s4-variant-"]:not([data-key*="-org-"]):not([data-key*="-rev-"])'
            for kind in range(max(1, page.locator(kinds).count())):
                if page.locator(kinds).count():
                    page.locator(kinds).nth(kind).click()
                label = page.locator(".picked strong").inner_text()
                first = run.look(f"s4 {label} 처음", limit=LIMIT[width])
                page.click('[data-key="s4-max"]')
                filled = run.look(f"s4 {label} 모두 담음", limit=LIMIT[width])
                tallest = max(tallest, first, filled)
                # 결과 막대와 표를 모두 펼친 상태(높이 한도는 펼치기 전에만 본다). 다음 종형으로 넘어가기 전에 다시 접는다
                keys = run.show_all("s4-more-", f"s4 {label}")
                if keys:
                    run.look(f"s4 {label} 모두 담음·결과 모두 펼침")
                    run.s4_all_shown(f"s4 {label}")
                    run.fold_back(keys, f"s4 {label}")
    print(f"[{width}px] s4 종형별 최대 높이 {tallest}px(결과를 펼치기 전)")
    # 마지막 종형(특약이 가장 많은 회사)에서 목록 다루기
    total = page.locator("#main .list .pager").first.inner_text()
    run.look("s4 특약 많은 종형 모두 담음", shot="s4_big")
    keys = run.show_all("s4-more-", "s4 특약 많은 종형")
    run.look("s4 특약 많은 종형 결과 모두 펼침", shot="s4_big_open")
    run.s4_all_shown("s4 특약 많은 종형")
    run.fold_back(keys, "s4 특약 많은 종형")
    # 키보드로 펼치고 접는다(Enter로 펼치고 Space로 접는다). 다시 그려도 초점이 단추에 남아야 한다
    more = '[data-key="s4-more-pay"]'
    if page.locator(more).count():
        page.focus(more)
        page.keyboard.press("Enter")
        opened = page.get_attribute(more, "aria-expanded")
        focused = page.evaluate("() => document.activeElement && document.activeElement.dataset.key")
        page.keyboard.press("Space")
        closed = page.get_attribute(more, "aria-expanded")
        if (opened, focused, closed) != ("true", "s4-more-pay", "false"):
            problems.append((width, "s4 키보드", {"kind": "keyboard toggle", "opened": opened, "focused": focused, "closed": closed}))
    notice = page.locator("#main p.notice")
    if notice.count():
        assert "가입 한도" in notice.first.inner_text()
        amounts = [float(v) for v in page.eval_on_selector_all("input.amount", "els => els.map(e => e.value)")]
        assert amounts and all(a > 0 for a in amounts), "가입 한도 자료가 없는 특약의 가입금액이 0으로 들어감"
        bars = page.locator(".barval:not(.soft)").all_inner_texts()
        assert bars and not all(t.strip() == "0원" for t in bars), "지급액이 모두 0원"
    if page.locator('[data-key="s4-list-top-next"]').count():
        page.click('[data-key="s4-list-bottom-next"]')
        assert "2 /" in page.locator("#main .list .pager").first.inner_text()
        run.look("s4 특약 목록 2쪽", shot="s4_page2")
    run.typing("s4-q", "암진단")
    names = page.eval_on_selector_all(".rider .rname", "els => els.map(e => e.textContent)")
    assert names and all("암진단" in n.replace(" ", "") for n in names), f"특약 찾기 결과가 다름: {names[:3]}"
    run.look(f"s4 특약 찾기 '암진단' {len(names)}개", shot="s4_search")
    page.fill('[data-key="s4-q"]', "")
    page.click('[data-key="s4-clear"]')
    page.locator(".rider input[type=checkbox]:not(:disabled)").nth(1).check()
    page.click('[data-key="s4-picked"]')
    picked = run.rows(".rider")
    assert picked == 2, f"고른 특약만 보기에 {picked}개가 보임(주계약과 특약 1개여야 함)"
    run.look("s4 고른 특약만 보기", shot="s4_picked")
    page.click('[data-key="s4-picked"]')
    page.click('[data-key="s4-max"]')
    if page.locator('[data-key="fold-s4-others"]').count():
        page.click('[data-key="fold-s4-others"]')
        assert 0 < run.rows("#main details.fold[open] table tbody tr") <= 20
        run.look("s4 표준담보 밖 급부 펼침", shot="s4_others")
        if page.locator('[data-key="s4-others-bottom-next"]').count():
            page.click('[data-key="s4-others-bottom-next"]')
            run.look("s4 표준담보 밖 급부 2쪽")
        page.fill('[data-key="s4-others-q"]', "사망")
        run.look("s4 표준담보 밖 급부 찾기")
        page.fill('[data-key="s4-others-q"]', "")
        page.click('[data-key="fold-s4-others"]')
    if page.locator('.btn[data-key^="ev-"]').count():
        page.locator('.btn[data-key^="ev-"]').first.click()
        page.wait_for_selector("dialog[open]")
        run.problems += [(width, "s4 근거 창", o) for o in page.evaluate(OVERFLOW_JS)]
        page.click("#detail-close")
    print(f"[{width}px] s4 특약 목록: {total}")

    # ---- 화면 5: 짝마다 ----
    page.click("#tab-s5")
    for i in range(page.locator('[data-key^="s5-pair-"]').count()):
        page.locator('[data-key^="s5-pair-"]').nth(i).click()
        run.look(f"s5 짝 {i}", limit=LIMIT[width])

    # ---- 화면 6 ----
    page.click("#tab-s6")
    assert 0 < run.rows("#main .list table.log tbody tr") <= 20
    page.click('[data-key="s6-log-bottom-next"]')
    assert "2 /" in page.locator("#main .list .pager").last.inner_text()
    run.look("s6 전체 기록 2쪽")
    page.select_option('[data-key="s6-step"]', "사람검토이관")
    shown = run.rows("#main .list table.log tbody tr")
    assert 0 < shown <= 20, f"사람검토이관 기록 수가 다름: {shown}"
    assert all("사람검토이관" in t for t in page.locator("#main .list table.log tbody tr").all_inner_texts())
    run.look("s6 작업단계 거르기", shot="s6_step")
    page.select_option('[data-key="s6-step"]', "")
    page.select_option('[data-key="s6-result"]', "반려")
    run.look("s6 결과 반려만")
    page.select_option('[data-key="s6-result"]', "")
    run.typing("s6-q", "암진단")
    texts = page.locator("#main .list table.log tbody tr").all_inner_texts()
    assert texts and all("암진단" in t.replace(" ", "") for t in texts), "작업 기록 찾기 결과가 다름"
    run.look("s6 기록 찾기 '암진단'", shot="s6_search")
    page.fill('[data-key="s6-q"]', "없는글자zz")
    assert "조건에 맞는 기록이 없습니다" in page.inner_text("#main")
    page.fill('[data-key="s6-q"]', "")
    page.click('[data-key="fold-s6-review"]')
    assert 0 < run.rows("#main details.fold[open] table tbody tr") <= 20
    run.look("s6 사람 검토 목록 펼침", shot="s6_review_open")
    if page.locator('[data-key="s6-review-bottom-next"]').count():
        page.click('[data-key="s6-review-bottom-next"]')
        run.look("s6 사람 검토 목록 2쪽")
    page.select_option('[data-key="s6-review-status"]', index=2)
    run.look("s6 사람 검토 상태 거르기", shot="s6_review_status")
    page.select_option('[data-key="s6-review-status"]', "")
    run.typing("s6-review-q", "수술")
    run.look("s6 사람 검토 찾기 '수술'")
    page.fill('[data-key="s6-review-q"]', "")
    page.select_option('[data-key="s6-review-tab"]', index=1)
    run.look("s6 사람 검토 대상탭 거르기")

    print(f"[{width}px] 콘솔 오류 {len(errors)}건, 외부 요청 {len(requests)}건")
    run.problems += [(width, "console", e) for e in errors] + [(width, "request", r) for r in requests]
    context.close()


def main() -> int:
    problems, pages = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (380, 1280):
            try:
                check_width(browser, width, problems, pages)
            except Exception as error:          # 중간에 멈춰도 그때까지 찾은 문제는 보여 준다
                problems.append((width, "점검 중단", repr(error)[:300]))
        browser.close()
    print(f"파일 크기 {SITE.stat().st_size:,}바이트")
    print("응대 카드 PDF 쪽 수: " + (", ".join(f"[{w}px] {label} {n}쪽" for w, label, n in pages) or "만들지 못함"))
    # 같은 문제가 여러 상태에서 되풀이되면 한 줄로 묶어 보여 준다
    seen = {}
    for width, label, what in problems:
        key = (width, json.dumps(what, ensure_ascii=False, sort_keys=True))
        seen.setdefault(key, []).append(label)
    for (width, what), labels in seen.items():
        print(f"문제 [{width}px] {len(labels)}번 ({labels[0]} 등):", what)
    print(f"문제 {len(problems)}건({len(seen)}가지)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
