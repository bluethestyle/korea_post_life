"""시안 4 사진 찍기와 잰 값.

쓰기: python proto_src/console4/shoot.py [사진 폴더] [거르개]
      사진 폴더 기본값: <저장소>/shots_console4
      거르개를 주면 사진 이름에 그 글자가 든 것만 찍는다(예: w1920, brief-sel, dark).

찍는 것: 1920x1080, 1600x900, 1280x800, 1180x820, 380x780 에서 탭과 상태별 사진.
잰 값(report.json): 흰 면 넓이 비율(세 채널 모두 240 이상), 빨강 넓이 비율, 글자 명암비(글자 칸의 가장 흔한 바탕색과
계산된 글자색), 가로 넘침, 콘솔 오류, 외부 요청.
"""
from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

PAGE = Path(__file__).resolve().parents[2] / 'site/proto/console4.html'
URL = PAGE.as_uri()
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else Path(
    str(Path(__file__).resolve().parents[2] / 'shots_console4'))
ONLY = sys.argv[2] if len(sys.argv) > 2 else ''
OUT.mkdir(parents=True, exist_ok=True)

SIZES = [(1920, 1080, 'w1920'), (1600, 900, 'w1600'), (1280, 800, 'w1280'), (1180, 820, 'w1180'), (380, 780, 'w380')]
B4 = 'EPOST_P500132_e9ef50'

TEXTS_JS = r"""() => {
  const out = [];
  const vw = innerWidth, vh = innerHeight;
  const evBody = document.getElementById('ev-body');
  const evClip = evBody ? evBody.getBoundingClientRect() : null;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    if (!n.nodeValue.trim()) continue;
    const el = n.parentElement;
    if (!el || el.closest('svg,script,style,#print-root,.sr')) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) continue;
    let a = el, hidden = false;
    while (a) { const s = getComputedStyle(a); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity < 0.05) { hidden = true; break; } a = a.parentElement; }
    if (hidden) continue;
    const r = document.createRange(); r.selectNodeContents(n);
    for (const b of r.getClientRects()) {
      if (b.width < 4 || b.height < 6) continue;
      if (b.bottom <= 0 || b.right <= 0 || b.top >= vh || b.left >= vw) continue;
      if (evBody && evBody.contains(el) && evClip && (b.top < evClip.top - 1 || b.bottom > evClip.bottom + 1)) continue;
      // 위 띠나 아래 판에 가린 글자는 재지 않는다
      const cx = Math.min(vw - 1, b.left + b.width / 2);
      const own = y => { const h = document.elementFromPoint(cx, Math.max(0, Math.min(vh - 1, y))); return h && (h === el || el.contains(h) || h.contains(el)); };
      if (!own(b.top + 2) || !own(b.top + b.height / 2) || !own(b.bottom - 2)) continue;
      out.push({ t: n.nodeValue.trim().slice(0, 40), x: b.left, y: b.top, w: b.width, h: b.height,
        c: cs.color, fs: parseFloat(cs.fontSize), fw: +cs.fontWeight || 400, cls: (el.className && el.className.baseVal === undefined ? el.className : '') });
    }
  }
  return out;
}"""

OVER_JS = r"""() => { const d = document.documentElement; const bad = [];
  document.querySelectorAll('body *').forEach(el => { const r = el.getBoundingClientRect();
    if (r.width && r.right > innerWidth + 1 && getComputedStyle(el).position !== 'fixed' && !el.closest('.bg,svg,.ev,.toast,#print-root,.tabs'))
      bad.push((el.tagName + '.' + (typeof el.className === 'string' ? el.className : '')).slice(0, 60)); });
  return { sw: d.scrollWidth, cw: d.clientWidth, bad: bad.slice(0, 8) }; }"""

COUNTS_JS = r"""() => {
  const vw = innerWidth, vh = innerHeight;
  const zones = { top: { chars: 0, nodes: 0 }, main: { chars: 0, nodes: 0 }, ev: { chars: 0, nodes: 0 } };
  const evBody = document.getElementById('ev-body');
  const evClip = evBody ? evBody.getBoundingClientRect() : null;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    const raw = n.nodeValue.replace(/\s+/g, '');
    if (!raw) continue;
    const el = n.parentElement;
    if (!el || el.tagName === 'OPTION' || el.closest('script,style,#print-root,.sr')) continue;
    let a = el, hidden = false;
    while (a) {
      const s = getComputedStyle(a);
      if (a.hidden || s.display === 'none' || s.visibility === 'hidden' || +s.opacity < 0.05) { hidden = true; break; }
      if (a.getAttribute && a.getAttribute('aria-hidden') === 'true' && a.closest('svg')) { hidden = true; break; }
      a = a.parentElement;
    }
    if (hidden) continue;
    const r = document.createRange();
    r.selectNodeContents(n);
    const b = r.getBoundingClientRect();
    if (b.width < 1 || b.height < 1) continue;
    if (b.bottom <= 0 || b.right <= 0 || b.top >= vh || b.left >= vw) continue;
    let visLen = raw.length;
    if (evBody && evBody.contains(el) && evClip) {
      if (b.bottom <= evClip.top + 2 || b.top >= evClip.bottom - 2) continue;
      if (b.top < evClip.top || b.bottom > evClip.bottom) {
        // 스크롤 창 경계에 걸친 글 노드는 실제로 창 안에 그려진 글자만 센다
        const cr = document.createRange();
        const s = n.nodeValue;
        let k = 0;
        for (let i = 0; i < s.length; i++) {
          if (/\s/.test(s[i])) continue;
          cr.setStart(n, i);
          cr.setEnd(n, i + 1);
          const cb = cr.getBoundingClientRect();
          const cy2 = cb.top + cb.height / 2;
          if (cy2 >= evClip.top && cy2 <= evClip.bottom && cb.top >= 0 && cb.bottom <= vh) k++;
        }
        if (k === 0) continue;
        visLen = k;
      }
    }
    const sampleY = (evBody && evBody.contains(el) && evClip)
      ? Math.max(evClip.top + 2, Math.min(evClip.bottom - 2, b.top + Math.min(8, b.height / 2)))
      : b.top + b.height / 2;
    const cx = Math.max(0, Math.min(vw - 1, b.left + b.width / 2));
    const cy = Math.max(0, Math.min(vh - 1, sampleY));
    const hit = document.elementFromPoint(cx, cy);
    if (hit && !(hit === el || el.contains(hit) || hit.contains(el))) {
      // 고정 위 띠나 아래 판에 가려진 글자는 제외
      if (hit.closest('#head,#ev,#help-pop,#hud-tip') && !hit.closest('#ev')?.contains(el) && !hit.closest('#head')?.contains(el)) continue;
    }
    const z = el.closest('#head,#cond,#scope') ? 'top' : el.closest('#ev') ? 'ev' : el.closest('#main') ? 'main' : null;
    if (z) {
      zones[z].chars += visLen;
      zones[z].nodes += 1;
    }
  }
  const condEl = document.getElementById('cond');
  const headEl = document.getElementById('head');
  const topH = condEl ? Math.round(condEl.getBoundingClientRect().bottom) : (headEl ? Math.round(headEl.getBoundingClientRect().bottom) : 0);
  const st = window.App ? window.App.state : { tab: 'brief', sel: {}, sub: {} };
  const tab = st.tab || 'brief';
  const layer = (st.sub && st.sub[tab]) ? 3 : (st.sel && st.sel[tab]) ? 2 : 1;
  const condOpen = !!(condEl && condEl.classList.contains('open'));
  const scopeEl = document.getElementById('scope');
  const scopeOpen = !!(scopeEl && !scopeEl.hidden);
  return { vw, vh, tab, layer, topH, condOpen, scopeOpen, zones };
}"""


def lum(rgb):
    def ch(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def parse_color(s):
    s = s.strip()
    if s.startswith('rgb'):
        parts = s[s.index('(') + 1:s.index(')')].replace('/', ',').split(',')
        vals = [float(p) for p in parts if p.strip()]
        r, g, b = vals[:3]
        a = vals[3] if len(vals) > 3 else 1.0
        return (r, g, b, a)
    return (0, 0, 0, 1)


def measure(png: Path, texts: list[dict], dark: bool) -> dict:
    im = Image.open(png).convert('RGB')
    W, H = im.size
    px = im.load()
    total = W * H
    white = red = 0
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            r, g, b = px[x, y]
            if min(r, g, b) >= 240:
                white += 1
            if r >= 110 and r - g >= 60 and r - b >= 60:
                red += 1
    sampled = (H // 2 + H % 2) * (W // 2 + W % 2)
    res = {'white_pct': round(white / sampled * 100, 2) if not dark else None, 'red_pct': round(red / sampled * 100, 2)}
    worst = []
    for t in texts:
        x0, y0 = max(0, int(t['x'])), max(0, int(t['y']))
        x1, y1 = min(W, int(t['x'] + t['w'])), min(H, int(t['y'] + t['h']))
        if x1 - x0 < 3 or y1 - y0 < 3:
            continue
        cnt = Counter()
        pad = 4 if t['fs'] >= 28 else 0
        q = 6 if t['fs'] >= 28 else 3
        px0, py0 = max(0, x0 - pad), max(0, y0 - pad)
        px1, py1 = min(W, x1 + pad), min(H, y1 + pad)
        for yy in range(py0, py1):
            for xx in range(px0, px1):
                r, g, b = px[xx, yy]
                cnt[(r // q * q, g // q * q, b // q * q)] += 1
        bg = cnt.most_common(1)[0][0]
        fr, fg, fb, fa = parse_color(t['c'])
        fgc = (fr * fa + bg[0] * (1 - fa), fg * fa + bg[1] * (1 - fa), fb * fa + bg[2] * (1 - fa))
        cr = contrast(fgc, bg)
        large = t['fs'] >= 24 or (t['fs'] >= 18.66 and t['fw'] >= 600)
        need = 3.0 if large else 4.5
        worst.append({'t': t['t'], 'cr': round(cr, 2), 'fs': t['fs'], 'fw': t['fw'], 'bg': '#%02X%02X%02X' % bg, 'need': need, 'cls': t['cls']})
    worst.sort(key=lambda z: z['cr'])
    res['min_contrast'] = worst[0]['cr'] if worst else None
    res['low'] = [w for w in worst if w['cr'] < w['need']][:12]
    res['lowest5'] = worst[:5]
    body = [w for w in worst if w['fs'] >= 14 and w['fs'] < 18 and w['fw'] < 600]
    res['body_min'] = body[0]['cr'] if body else None
    res['body_low'] = [w for w in body if w['cr'] < 7][:10]
    return res


def check_budget(cnt: dict) -> list[str]:
    if not cnt or cnt.get('vw') != 1920 or cnt.get('vh') != 1080:
        return []
    z = cnt['zones']
    over = []
    if not cnt.get('condOpen') and not cnt.get('scopeOpen'):
        if z['top']['chars'] > 120:
            over.append(f"위영역 글자 {z['top']['chars']}>120")
        if cnt.get('topH', 0) > 130:
            over.append(f"위영역 높이 {cnt['topH']}px>130px")
    # 1단계에서는 브리핑 탭에 1~3층 본문/기둥 한도를 검사한다(2~3단계에서 나머지 탭 확장)
    if cnt.get('tab') == 'brief':
        lv = cnt.get('layer', 1)
        if lv == 1:
            if z['main']['chars'] > 250:
                over.append(f"1층 본문 글자 {z['main']['chars']}>250")
            if z['main']['nodes'] > 40:
                over.append(f"1층 본문 조각 {z['main']['nodes']}>40")
        else:
            if z['main']['chars'] > 400:
                over.append(f"2층 본문 글자 {z['main']['chars']}>400")
        if z['ev']['chars'] > 300:
            over.append(f"근거기둥 글자 {z['ev']['chars']}>300")
    return over


async def shot(pg, name, report, dark=False, full=False):
    if ONLY and ONLY not in name:
        return
    p = OUT / f'{name}.png'
    await pg.wait_for_timeout(120)
    await pg.screenshot(path=str(p), full_page=full)
    texts = await pg.evaluate(TEXTS_JS)
    ov = await pg.evaluate(OVER_JS)
    cnt = await pg.evaluate(COUNTS_JS) if not full else None
    over = check_budget(cnt) if cnt else []
    tb = {**cnt, 'over_limits': over} if cnt else {}
    m = measure(p, texts, dark) if not full else {}
    report[name] = {'overflow': ov, 'text_budget': tb, **m}
    z = cnt['zones'] if cnt else None
    z_str = f" | 글자(위 {z['top']['chars']}/{z['top']['nodes']}조각, 본문 {z['main']['chars']}/{z['main']['nodes']}조각, 기둥 {z['ev']['chars']}/{z['ev']['nodes']}조각)" if z else ''
    warn_str = f" [한도초과: {', '.join(over)}]" if over else ''
    print(f'{name}: 흰 {m.get("white_pct")}% 빨강 {m.get("red_pct")}% 최저 명암비 {m.get("min_contrast")} 본문 최저 {m.get("body_min")} 넘침 {ov["sw"] - ov["cw"]}px {ov["bad"][:2]}{z_str}{warn_str}')


async def page_for(b, vw, vh, skin='light', motion='off', hash_=''):
    ctx = await b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=1)
    await ctx.add_init_script(f"try{{localStorage.setItem('postlife-c4-skin','{skin}');localStorage.setItem('postlife-c4-motion','{motion}')}}catch(e){{}}")
    pg = await ctx.new_page()
    errs, ext = [], []
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('request', lambda r: ext.append(r.url) if not (r.url.startswith('file:') or r.url.startswith('data:')) else None)
    await pg.goto(URL + hash_)
    await pg.wait_for_timeout(500)
    return ctx, pg, errs, ext


async def run():
    report = {}
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        for vw, vh, tag in SIZES:
            if ONLY and not any(ONLY in f'{tag}-{s}' for s in ['brief', 'brief-sel', 'brief-l3', 'brief-base4', 'brief-cond', 'brief-kpi2', 'brief-kpi3', 'dark', 'tab2', 'tab3', 'tab4', 'tab5', 'motion', 'full', 'sheet', 'scroll']):
                continue
            ctx, pg, errs, ext = await page_for(b, vw, vh)
            await shot(pg, f'{tag}-brief', report)
            # 줄 (다) 고르기
            await pg.locator('#view-brief .brow[data-pick="다"] .lrow-hit').click()
            await pg.wait_for_timeout(300)
            await shot(pg, f'{tag}-brief-sel', report)
            if vw < 1000:
                await shot(pg, f'{tag}-brief-sheet', report)
                await pg.keyboard.press('Escape')
                await pg.wait_for_timeout(300)
            else:
                await pg.keyboard.press('Escape')
                await pg.wait_for_timeout(200)
            # 2층 시각화(고객군 지형 24칸 격자 -> 3층 칸 선택 -> 담보 포지션 5단계)
            if await pg.locator('#view-brief .kpi[data-i="1"]').count():
                for i, nm in [(1, 'brief-kpi2'), (2, 'brief-kpi3')]:
                    await pg.locator(f'#view-brief .kpi[data-i="{i}"]').click()
                    await pg.wait_for_timeout(250)
                    await shot(pg, f'{tag}-{nm}', report)
                await pg.locator('#view-brief .kpi[data-i="0"]').click()
            else:
                await pg.locator('#view-brief .brow[data-pick="가"] .lrow-hit').click()
                await pg.wait_for_timeout(250)
                await shot(pg, f'{tag}-brief-kpi2', report)
                await pg.locator('#view-brief [data-sub-pick="seg:0-1"]').click()
                await pg.wait_for_timeout(250)
                await shot(pg, f'{tag}-brief-l3', report)
                if vw < 1000:
                    await pg.keyboard.press('Escape')
                    await pg.wait_for_timeout(180)
                await pg.locator('#view-brief .brow[data-pick="라"] .lrow-hit').click()
                await pg.wait_for_timeout(250)
                await shot(pg, f'{tag}-brief-kpi3', report)
                await pg.keyboard.press('Escape')
                await pg.wait_for_timeout(200)
            # 기준 종형 4종으로(R11)
            await pg.evaluate(f"App.set({{base:'{B4}'}})")
            await pg.wait_for_timeout(300)
            await shot(pg, f'{tag}-brief-base4', report)
            # 조건 바꾸기: 70세, 수술만 1~2년 전
            await pg.evaluate("App.set({base:'EPOST_P500129_8dba92', age:70, since:1, surg:true})")
            await pg.wait_for_timeout(300)
            await shot(pg, f'{tag}-brief-cond', report)
            if vw < 1000:
                await pg.evaluate("window.scrollTo(0, 900)")
                await pg.wait_for_timeout(200)
                await shot(pg, f'{tag}-brief-scroll', report)
            # 탭 2~5 자리
            for i, tid in [(2, 'market'), (3, 'gate'), (4, 'cover'), (5, 'insight')]:
                if ONLY and f'tab{i}' not in ONLY and ONLY not in tag:
                    continue
                await pg.evaluate(f"App.set({{tab:'{tid}'}})")
                await pg.wait_for_timeout(150)
                await shot(pg, f'{tag}-tab{i}', report)
            await pg.evaluate("App.set({tab:'brief', age:50, since:null, surg:false})")
            await pg.wait_for_timeout(200)
            await shot(pg, f'{tag}-brief-full', report, full=True)
            report[f'{tag}-errors'] = {'console': errs, 'external': ext}
            await ctx.close()
            # 짙은 스킨
            ctx, pg, errs, ext = await page_for(b, vw, vh, skin='dark')
            await shot(pg, f'{tag}-dark', report, dark=True)
            await pg.locator('#view-brief .brow[data-pick="라"] .lrow-hit').click()
            await pg.wait_for_timeout(300)
            await shot(pg, f'{tag}-dark-sel', report, dark=True)
            report[f'{tag}-dark-errors'] = {'console': errs, 'external': ext}
            await ctx.close()
            # 움직임 켬: 처음 300ms 와 탭을 옮긴 뒤 200ms
            if vw in (1920, 380):
                ctx, pg, errs, ext = await page_for(b, vw, vh, motion='on')
                await pg.goto(URL + '#t=gate')
                await pg.wait_for_timeout(300)
                await pg.locator('#tab-brief').click()
                await pg.wait_for_timeout(200)
                await shot(pg, f'{tag}-motion200', report)
                await pg.wait_for_timeout(700)
                await shot(pg, f'{tag}-motion900', report)
                await ctx.close()
        await b.close()
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    errs = {k: v for k, v in report.items() if k.endswith('errors') and (v['console'] or v['external'])}
    print('오류와 외부 요청:', json.dumps(errs, ensure_ascii=False)[:1500] if errs else '없음')
    print('사진 폴더:', OUT)


asyncio.run(run())
