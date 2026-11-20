"""흐름도 쪽을 찍는다. 돌리기(저장소 루트에서): python proto_src/flow/shoot.py <사진 폴더> [접두어]  (playwright가 있어야 한다)

1280x800, 1180x820, 1024x768 은 흐름도(장면 고르기와 그림)가 한 화면에 드는지, 넘치면 몇 px 인지 잰다.
380x780 은 가로 넘침, 잘린 글자, 40px 보다 작은 단추를 본다.
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

SRC = (pathlib.Path(__file__).resolve().parents[2] / 'site/proto/flow.html').as_uri()
out = sys.argv[1].rstrip('/') + '/'
pre = sys.argv[2] if len(sys.argv) > 2 else 'v2'
SIZES = ((1280, 800), (1180, 820), (1024, 768), (380, 780))


def check(pg, tag):
    r = pg.evaluate("""() => {
      const de = document.documentElement;
      const over = [...document.querySelectorAll('body *')].filter(el => {
        const r = el.getBoundingClientRect(); return r.width && (r.right > de.clientWidth + 0.5 || r.left < -0.5);
      }).filter(el => !el.closest('.route,.stops')).slice(0, 5).map(el => el.className || el.tagName);
      const clipped = [...document.querySelectorAll('.tc-b p, .tc-b li, .cl li, .its li, .st, .pb, .btn, .bdg, .tn, .vf, .w5 .tx, .ct td, .rules p, .nl li, .lgd p, .pr a, .rs, .ok')].filter(el => el.offsetParent && el.scrollWidth > el.clientWidth + 1).slice(0, 6).map(el => el.textContent.trim().slice(0, 20));
      const small = [...document.querySelectorAll('button, a')].filter(el => { const r = el.getBoundingClientRect(); return r.width && r.height && (r.height < 39.5 || r.width < 39.5) && getComputedStyle(el).visibility !== 'hidden'; }).slice(0, 6).map(el => (el.textContent.trim() || el.getAttribute('aria-label') || el.className).slice(0, 20) + ' ' + Math.round(el.getBoundingClientRect().width) + 'x' + Math.round(el.getBoundingClientRect().height));
      /* 표지끼리 겹침 */
      const mk = [...document.querySelectorAll('.mkb')].map(el => el.getBoundingClientRect());
      let mkOver = 0; for (let i = 0; i < mk.length; i++) for (let j = i + 1; j < mk.length; j++) { const a = mk[i], b = mk[j]; if (a.left < b.right - 2 && b.left < a.right - 2 && a.top < b.bottom - 2 && b.top < a.bottom - 2) mkOver++; }
      const flow = document.querySelector('#flow .pn').getBoundingClientRect();
      const dia = document.querySelector('.dia').getBoundingClientRect();
      const row = document.querySelector('.row').getBoundingClientRect();
      const det = document.querySelector('.dock') ? document.querySelector('.dock').getBoundingClientRect() : null;
      return {scrollW: de.scrollWidth, clientW: de.clientWidth, vh: innerHeight, over, clipped, small, mkOver,
        flowBottom: Math.round(flow.bottom), diaBottom: Math.round(dia.bottom), rowH: Math.round(row.height), dockH: det ? Math.round(det.height) : null, docH: de.scrollHeight};
    }""")
    print(tag, r)
    return r


with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in SIZES:
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1, has_touch=(w < 1000))
        pg = ctx.new_page()
        errs, reqs = [], []
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('request', lambda r: reqs.append(r.url) if not r.url.startswith(('file:', 'data:')) else None)
        pg.goto(SRC)
        pg.wait_for_timeout(700)
        fonts = pg.evaluate("[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family+' '+f.weight)")
        meta = pg.evaluate("document.querySelector('meta[name=robots]') && document.querySelector('meta[name=robots]').content")
        print(w, 'errors', errs, 'external', reqs, 'robots', meta, 'fonts', sorted(set(fonts)))
        check(pg, f'{w}x{h} start')
        pg.screenshot(path=f'{out}{pre}-{w}-a1.png')
        if w >= 1000:
            pg.click('.mkb[data-i="1"]'); pg.wait_for_timeout(250)
            pg.screenshot(path=f'{out}{pre}-{w}-a2.png')
            pg.click('#steps .st[data-i="5"]'); pg.wait_for_timeout(250)
            pg.screenshot(path=f'{out}{pre}-{w}-a6.png')
            pg.click('[data-path="B"]'); pg.wait_for_timeout(350)
            pg.click('#steps .st[data-i="4"]'); pg.wait_for_timeout(250)
            check(pg, f'{w}x{h} B5')
            pg.screenshot(path=f'{out}{pre}-{w}-b5.png')
            pg.click('[data-path="C"]'); pg.wait_for_timeout(350)
            pg.click('.mkb[data-i="2"]'); pg.wait_for_timeout(250)
            pg.screenshot(path=f'{out}{pre}-{w}-c3.png')
            # 키보드: 장면 묶음에서 오른쪽 화살표(장면 3 → 1), 걸음 묶음에서 아래 화살표 두 번
            pg.focus('#paths [aria-checked="true"]'); pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(200)
            pg.focus('#steps [aria-checked="true"]'); pg.keyboard.press('ArrowDown'); pg.keyboard.press('ArrowDown'); pg.wait_for_timeout(250)
            st = pg.evaluate("[document.querySelector('#paths [aria-checked=true]').dataset.path, document.querySelector('#steps [aria-checked=true]').dataset.i, document.activeElement.className, document.querySelector('#live').textContent]")
            print('keyboard', st)
            pg.screenshot(path=f'{out}{pre}-{w}-kbd.png')
            if w == 1280:
                pg.click('[data-path="A"]'); pg.wait_for_timeout(200)
                pg.screenshot(path=f'{out}{pre}-{w}-full.png', full_page=True)
                pg.click('#wtg [data-w="v"]'); pg.wait_for_timeout(150)
                pg.locator('#brief').screenshot(path=f'{out}{pre}-{w}-brief-v.png')
                pg.click('#flt [data-f="user"]'); pg.wait_for_timeout(150)
                print('user filter rows', pg.evaluate("[...document.querySelectorAll('#ctb tr')].filter(t=>!t.hidden).length"), pg.evaluate("document.querySelector('#ccount').textContent"))
                pg.locator('#changes').screenshot(path=f'{out}{pre}-{w}-chg.png')
        else:
            pg.screenshot(path=f'{out}{pre}-{w}-full.png', full_page=True)
            pg.locator('.mkb[data-i="1"]').tap(); pg.wait_for_timeout(350)
            pg.screenshot(path=f'{out}{pre}-{w}-a2sheet.png')
            pg.locator('#shTog').tap(); pg.wait_for_timeout(200)
            pg.locator('[data-path="B"]').tap(); pg.wait_for_timeout(350)
            pg.screenshot(path=f'{out}{pre}-{w}-b1.png', full_page=True)
            pg.locator('.mkb[data-i="4"]').tap(); pg.wait_for_timeout(350)
            pg.screenshot(path=f'{out}{pre}-{w}-b5sheet.png')
            pg.locator('#shTog').tap(); pg.wait_for_timeout(200)
            check(pg, f'{w}x{h} B')
            pg.locator('#changes').scroll_into_view_if_needed()
            pg.locator('#flt [data-f="keep"]').tap(); pg.wait_for_timeout(150)
            pg.locator('#changes').screenshot(path=f'{out}{pre}-{w}-chg.png')
            check(pg, f'{w}x{h} end')
        ctx.close()
    b.close()
