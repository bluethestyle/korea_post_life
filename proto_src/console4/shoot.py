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
raw_args = sys.argv[1:]
FRAMES_ONLY = False
if '--frames' in raw_args:
    raw_args.remove('--frames')
    FRAMES_ONLY = True
if '--html' in raw_args:
    hi = raw_args.index('--html')
    PAGE = Path(raw_args[hi + 1]).resolve()
    raw_args = raw_args[:hi] + raw_args[hi + 2:]
URL = PAGE.as_uri()
OUT = Path(raw_args[0]) if len(raw_args) > 0 and raw_args[0] else Path(
    str(Path(__file__).resolve().parents[2] / 'shots_console4'))
ONLY = raw_args[1] if len(raw_args) > 1 else ''
OUT.mkdir(parents=True, exist_ok=True)

SIZES = [(1920, 1080, 'w1920'), (1600, 900, 'w1600'), (1280, 800, 'w1280'), (1180, 820, 'w1180'), (380, 780, 'w380')]
B4 = 'EPOST_P500132_e9ef50'

TEXTS_JS = r"""() => {
  const out = [];
  const vw = innerWidth, vh = innerHeight;
  const evBody = document.getElementById('ev-body');
  const evClip = evBody ? evBody.getBoundingClientRect() : null;
  const tipEl = document.getElementById('hud-tip');
  const tipClip = tipEl && !tipEl.hidden ? tipEl.getBoundingClientRect() : null;
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
      if (tipClip && !tipEl.contains(el) && b.right > tipClip.left && b.left < tipClip.right && b.bottom > tipClip.top && b.top < tipClip.bottom) continue;
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
  const inScrollX = el => {
    let p = el.parentElement;
    while (p && p !== document.body && p !== d) {
      const ox = getComputedStyle(p).overflowX;
      if (ox === 'auto' || ox === 'scroll' || ox === 'hidden' || ox === 'clip') return true;
      p = p.parentElement;
    }
    return false;
  };
  document.querySelectorAll('body *').forEach(el => { const r = el.getBoundingClientRect();
    if (r.width && r.right > innerWidth + 1 && getComputedStyle(el).position !== 'fixed' && !inScrollX(el) && !el.closest('.bg,svg,.ev,.z-right,.toast,#print-root,.tabs,.rtabs'))
      bad.push((el.tagName + '.' + (typeof el.className === 'string' ? el.className : '')).slice(0, 60)); });
  return { sw: d.scrollWidth, cw: d.clientWidth, bad: bad.slice(0, 8) }; }"""

COUNTS_JS = r"""() => {
  const vw = innerWidth, vh = innerHeight;
  const zones = {
    top: { chars: 0, nodes: 0 },
    left: { chars: 0, nodes: 0 },
    center: { chars: 0, nodes: 0 },
    right: { chars: 0, nodes: 0 },
  };
  const clipBoxes = ['z-left', 'z-center', 'ev-body'].map(id => {
    const el = document.getElementById(id);
    return el ? { el, rect: el.getBoundingClientRect() } : null;
  }).filter(Boolean);
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
      if (a.tagName === 'DETAILS' && !a.open && !el.closest('summary')) { hidden = true; break; }
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
    let clippedOut = false;
    let sampleClip = null;
    for (const cb of clipBoxes) {
      if (cb.el.contains(el)) {
        sampleClip = cb.rect;
        if (b.bottom <= cb.rect.top + 2 || b.top >= cb.rect.bottom - 2) { clippedOut = true; break; }
        if (b.top < cb.rect.top || b.bottom > cb.rect.bottom) {
          const cr = document.createRange();
          const s = n.nodeValue;
          let k = 0;
          for (let i = 0; i < s.length; i++) {
            if (/\s/.test(s[i])) continue;
            cr.setStart(n, i);
            cr.setEnd(n, i + 1);
            const cbr = cr.getBoundingClientRect();
            const cy2 = cbr.top + cbr.height / 2;
            if (cy2 >= cb.rect.top && cy2 <= cb.rect.bottom && cbr.top >= 0 && cbr.bottom <= vh) k++;
          }
          if (k === 0) { clippedOut = true; break; }
          visLen = k;
        }
        break;
      }
    }
    if (clippedOut) continue;
    const sampleY = sampleClip
      ? Math.max(sampleClip.top + 2, Math.min(sampleClip.bottom - 2, b.top + Math.min(8, b.height / 2)))
      : b.top + b.height / 2;
    const cx = Math.max(0, Math.min(vw - 1, b.left + b.width / 2));
    const cy = Math.max(0, Math.min(vh - 1, sampleY));
    const hit = document.elementFromPoint(cx, cy);
    if (hit && !(hit === el || el.contains(hit) || hit.contains(el))) {
      if (hit.closest('#head,#z-right,#help-pop,#hud-tip') && !hit.closest('#z-right')?.contains(el) && !hit.closest('#head')?.contains(el)) continue;
    }
    const z = el.closest('#top-head,#cond,#scope,#rtabs') ? 'top'
      : el.closest('#z-left') ? 'left'
      : el.closest('#z-right') ? 'right'
      : el.closest('#z-center,#home-panel') ? 'center'
      : null;
    if (z) {
      zones[z].chars += visLen;
      zones[z].nodes += 1;
    }
  }
    const rtEl = document.getElementById('rtabs');
  const topH = rtEl && !rtEl.hidden ? Math.round(rtEl.getBoundingClientRect().bottom) : Math.round((document.getElementById('head') || document.body).getBoundingClientRect().bottom);
  const st = window.App ? window.App.state : { tab: 'brief', grp: {}, sel: {}, sub: {} };
  const tab = st.tab || 'brief';
  const grp = (st.grp && st.grp[tab]) || '';
  const condEl = document.getElementById('cond');
  const condOpen = !!(condEl && !condEl.hidden);
  const scopeEl = document.getElementById('scope');
  const scopeOpen = !!(scopeEl && !scopeEl.hidden);
  const dmEl = document.getElementById('data-modal');
  const modalOpen = !!(dmEl && !dmEl.hidden);
  const picked = !!(st.sel && st.sel[tab] != null);

  // 요청 27 기준: 본문 영역(#home-panel 또는 #board)의 사각 면 수, 마침표 문장 수, 글 조각 수, 안쪽 가로 스크롤 측정
  const stageEl = tab === 'brief' ? document.getElementById('home-panel') : document.getElementById('board');
  let stageNodes = 0, sentences = 0, rectSurfaces = 0, innerScrollX = 0;
  if (stageEl && !stageEl.hidden) {
    const sw = document.createTreeWalker(stageEl, NodeFilter.SHOW_TEXT);
    let sn;
    while ((sn = sw.nextNode())) {
      const txt = sn.nodeValue.trim();
      if (!txt) continue;
      const pel = sn.parentElement;
      if (!pel || pel.tagName === 'OPTION' || pel.closest('script,style,#print-root,.sr')) continue;
      let pa = pel, phid = false;
      while (pa && pa !== document.body) {
        const ps = getComputedStyle(pa);
        if (pa.hidden || ps.display === 'none' || ps.visibility === 'hidden' || +ps.opacity < 0.05) { phid = true; break; }
        if (pa.tagName === 'DETAILS' && !pa.open && !pel.closest('summary')) { phid = true; break; }
        if (pa.getAttribute && pa.getAttribute('aria-hidden') === 'true' && pa.closest('svg')) { phid = true; break; }
        pa = pa.parentElement;
      }
      if (phid) continue;
      stageNodes += 1;
      const m = txt.match(/\.(?=\s|$)/g);
      if (m) sentences += m.length;
    }
    const checkEls = [stageEl, ...stageEl.querySelectorAll('*')];
    for (const cel of checkEls) {
      if (cel.closest('svg,.flag,.gtf-ours,.vd,.tag,.scb,.cvp-bar,.cv-tick,.gr-node,.cv-flt-btn.is-on,.gr-tr-btn.is-cur,.gr-preset.is-on,.gr-search-in')) continue;
      let ca = cel, chid = false;
      while (ca && ca !== document.body) {
        const cs2 = getComputedStyle(ca);
        if (ca.hidden || cs2.display === 'none' || cs2.visibility === 'hidden' || +cs2.opacity < 0.05) { chid = true; break; }
        ca = ca.parentElement;
      }
      if (chid) continue;
      const cs = getComputedStyle(cel);
      const bg = cs.backgroundColor;
      const cr = cel.getBoundingClientRect();
      if (cr.width >= 24 && cr.height >= 20 && bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
        rectSurfaces += 1;
      }
      if ((cs.overflowX === 'auto' || cs.overflowX === 'scroll') && cel.scrollWidth > cel.clientWidth + 1) {
        innerScrollX = Math.max(innerScrollX, Math.round(cel.scrollWidth - cel.clientWidth));
      }
    }
  }
  return { vw, vh, tab, grp, topH, condOpen, scopeOpen, modalOpen, picked, stageNodes, sentences, rectSurfaces, innerScrollX, zones };
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
        pad = 10 if t['fs'] >= 26 else 0
        q = 6 if t['fs'] >= 26 else 3
        px0, py0 = max(0, x0 - pad), max(0, y0 - pad)
        px1, py1 = min(W, x1 + pad), min(H, y1 + pad)
        for yy in range(py0, py1):
            for xx in range(px0, px1):
                if pad and x0 <= xx < x1 and y0 <= yy < y1:
                    continue
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


STAGE_NODE_LIMITS = {
    'brief': 30,
    'market': 60,
    'gate': 80,
    'cover': 65,
    'graph': 70,
}


def check_budget(cnt: dict) -> list[str]:
    if not cnt:
        return []
    over = []
    tab = cnt.get('tab')
    modal_open = bool(cnt.get('modalOpen'))
    picked = bool(cnt.get('picked'))
    if tab in STAGE_NODE_LIMITS and not modal_open:
        if cnt.get('innerScrollX', 0) > 0:
            over.append(f"도형영역 안쪽가로스크롤 {cnt['innerScrollX']}px>0")
    if cnt.get('vw') != 1920 or cnt.get('vh') != 1080:
        return over
    z = cnt['zones']
    if not cnt.get('condOpen') and not cnt.get('scopeOpen') and not modal_open:
        if z['top']['chars'] > 160:
            over.append(f"위영역 글자 {z['top']['chars']}>160")
    if tab in STAGE_NODE_LIMITS and not picked and not modal_open:
        if cnt.get('rectSurfaces', 0) > 0:
            over.append(f"본문 사각면 {cnt['rectSurfaces']}>0")
        if cnt.get('sentences', 0) > 1:
            over.append(f"본문 마침표문장 {cnt['sentences']}>1")
        lim = STAGE_NODE_LIMITS[tab]
        if cnt.get('stageNodes', 0) > lim:
            over.append(f"본문 글조각 {cnt['stageNodes']}>{lim}")
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
    z_str = (
        f" | 본문(면 {cnt['rectSurfaces']}, 문장 {cnt['sentences']}, 조각 {cnt['stageNodes']}, 안쪽가로 {cnt['innerScrollX']}px)"
        f" 구역(위 {z['top']['chars']}자/{z['top']['nodes']}조각, "
        f"가운데 {z['center']['chars']}자/{z['center']['nodes']}조각, "
        f"오른 {z['right']['chars']}자/{z['right']['nodes']}조각)"
    ) if z else ''
    warn_str = f" [한도초과: {', '.join(over)}]" if over else ''
    print(f'{name}: 흰 {m.get("white_pct")}% 빨강 {m.get("red_pct")}% 최저 명암비 {m.get("min_contrast")} 본문 최저 {m.get("body_min")} 넘침 {ov["sw"] - ov["cw"]}px {ov["bad"][:2]}{z_str}{warn_str}')


LAYOUT_ANIM_JS = r"""() => {
  const BAD_PROPS = new Set([
    'all', 'width', 'height', 'min-width', 'max-width', 'min-height', 'max-height',
    'top', 'left', 'right', 'bottom', 'inset', 'inset-block', 'inset-inline',
    'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
    'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'border-width', 'border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width',
    'font-size', 'line-height', 'gap', 'column-gap', 'row-gap', 'flex', 'flex-basis', 'flex-grow',
    'grid-template-columns', 'grid-template-rows',
  ]);
  const BAD_CAMEL = new Set([
    'width', 'height', 'minWidth', 'maxWidth', 'minHeight', 'maxHeight',
    'top', 'left', 'right', 'bottom', 'inset',
    'margin', 'marginTop', 'marginRight', 'marginBottom', 'marginLeft',
    'padding', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'borderWidth', 'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
    'fontSize', 'lineHeight', 'gap', 'columnGap', 'rowGap', 'flex', 'flexBasis', 'flexGrow',
    'gridTemplateColumns', 'gridTemplateRows',
  ]);
  const sheetBad = [];
  function walkRules(rules) {
    if (!rules) return;
    for (const r of rules) {
      if (r.cssRules) walkRules(r.cssRules);
      if (r.type === 1 && r.style) {
        const tp = r.style.transitionProperty;
        const td = r.style.transitionDuration;
        if (tp && td && !/^0m?s(\s*,\s*0m?s)*$/.test(td.trim())) {
          for (const raw of tp.split(',')) {
            const p = raw.trim().toLowerCase();
            if (BAD_PROPS.has(p)) sheetBad.push({ kind: 'transition', sel: r.selectorText, prop: p });
          }
        } else if (r.cssText && /transition\s*:/.test(r.cssText)) {
          const m = r.cssText.match(/transition\s*:\s*([^;}]+)/i);
          if (m && !/^\s*(none|0m?s)\b/i.test(m[1])) {
            for (const seg of m[1].split(',')) {
              const tok = seg.trim().split(/\s+/)[0].toLowerCase();
              if (BAD_PROPS.has(tok)) sheetBad.push({ kind: 'transition-var', sel: r.selectorText, prop: tok });
            }
          }
        }
      } else if (r.type === 7 && r.cssRules) {
        for (const kf of r.cssRules) {
          if (!kf.style) continue;
          for (let i = 0; i < kf.style.length; i++) {
            const p = kf.style[i].toLowerCase();
            if (BAD_PROPS.has(p)) sheetBad.push({ kind: 'keyframes', name: r.name, prop: p });
          }
        }
      }
    }
  }
  for (const ss of document.styleSheets) {
    try { walkRules(ss.cssRules); } catch (e) { /* */ }
  }
  const animBad = [];
  if (document.getAnimations) {
    for (const a of document.getAnimations({ subtree: true })) {
      try {
        const kfs = a.effect && a.effect.getKeyframes ? a.effect.getKeyframes() : [];
        for (const kf of kfs) {
          for (const k of Object.keys(kf)) {
            if (BAD_CAMEL.has(k)) animBad.push({ anim: a.animationName || a.id || 'waapi', prop: k });
          }
        }
      } catch (e) { /* */ }
    }
  }
  return { count: sheetBad.length + animBad.length, sheet: sheetBad, active: animBad };
}"""

RAF_HOOK_JS = r"""() => {
  window.__startRaf = () => {
    const ts = [];
    let active = true;
    function tick(t) {
      ts.push(t);
      if (active) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
    window.__stopRaf = () => {
      active = false;
      const dts = [];
      for (let i = 2; i < ts.length; i++) dts.push(+(ts[i] - ts[i - 1]).toFixed(2));
      dts.sort((a, b) => a - b);
      const n = dts.length;
      return {
        frames: n,
        p50_ms: n ? dts[Math.floor(n * 0.5)] : 0,
        p95_ms: n ? dts[Math.min(n - 1, Math.floor(n * 0.95))] : 0,
        max_ms: n ? dts[n - 1] : 0,
        over_33ms: dts.filter(x => x > 33.0).length,
      };
    };
  };
}"""


async def sample_action(pg, act_coro, dur_ms=620):
    await pg.evaluate("window.__startRaf()")
    await pg.wait_for_timeout(40)
    ok = await act_coro()
    if ok is False:
        await pg.evaluate("window.__stopRaf()")
        return None
    await pg.wait_for_timeout(dur_ms)
    return await pg.evaluate("window.__stopRaf()")


async def measure_frames_once(b, cpu_rate=1) -> dict:
    ctx, pg, errs, ext = await page_for(b, 1920, 1080, skin='light', motion='on')
    # 여는 화면(boot-loader)이 끝날 때까지 대기
    await pg.wait_for_timeout(1100)
    await pg.evaluate(RAF_HOOK_JS)
    cdp = None
    if cpu_rate > 1:
        cdp = await ctx.new_cdp_session(pg)
        await cdp.send('Emulation.setCPUThrottlingRate', {'rate': cpu_rate})

    out = {}

    # 1. 탭 전환(첫 화면 -> 고객군과 시장)
    async def act_tab():
        await pg.locator('#tab-market').first.click()
    out['tab_switch'] = await sample_action(pg, act_tab, 680)

    # 2. 고객군 고리 고르기
    async def act_market_pick():
        await pg.locator('#z-center .mk-ring[data-grid-r="0"][data-grid-c="1"]').click()
        await pg.wait_for_timeout(180)
        await pg.locator('#z-center .mk-ring[data-grid-r="1"][data-grid-c="2"]').click()
    out['market_pick'] = await sample_action(pg, act_market_pick, 460)

    # 3. 읽기 영역 열고 닫기
    async def act_reading():
        await pg.keyboard.press('Escape')
        await pg.wait_for_timeout(180)
        await pg.locator('#z-center .mk-ring[data-grid-r="1"][data-grid-c="1"]').click()
    out['reading_toggle'] = await sample_action(pg, act_reading, 460)

    # 4. 가입 관문 칸 고르기
    await pg.evaluate("App.set({tab:'gate'})")
    await pg.wait_for_timeout(380)

    async def act_gate_pick():
        cells = pg.locator('#z-center .gtf-cell')
        if await cells.count() < 2:
            return False
        await cells.nth(0).click()
        await pg.wait_for_timeout(180)
        await cells.nth(min(6, (await cells.count()) - 1)).click()
    out['gate_pick'] = await sample_action(pg, act_gate_pick, 460)

    # 5. 담보 기둥 고르기
    await pg.evaluate("App.set({tab:'cover'})")
    await pg.wait_for_timeout(380)

    async def act_cover_pick():
        pils = pg.locator('#z-center .cvp-slot, #z-center .cvp-btn')
        cnt = await pils.count()
        if cnt < 2:
            return False
        await pils.nth(1).click()
        await pg.wait_for_timeout(180)
        await pils.nth(min(4, cnt - 1)).click()
    out['cover_pick'] = await sample_action(pg, act_cover_pick, 460)

    # 6. 담보 비교 단계 바꾸기(전체 띠 구간 전환)
    async def act_cover_step():
        segs = pg.locator('#z-center [data-cv-step]')
        if await segs.count() < 2:
            return False
        await segs.nth(1).click()
    out['cover_step'] = await sample_action(pg, act_cover_step, 520)

    # 7. 담보 비교 문지르기(포인터 좌우 이동)
    async def act_cover_scrub():
        stage = pg.locator('#z-center #cv-zoom-axis, #z-center #cv-pillar-axis').first
        if await stage.count() == 0:
            return False
        box = await stage.bounding_box()
        if not box:
            return False
        y = box['y'] + box['height'] * 0.55
        x0 = box['x'] + 24
        x1 = box['x'] + min(box['width'] - 24, 720)
        for k in range(12):
            xk = x0 + (x1 - x0) * (k / 11)
            await pg.mouse.move(xk, y)
            await pg.wait_for_timeout(24)
    out['cover_scrub'] = await sample_action(pg, act_cover_scrub, 260)

    # 8. 관계 지도 펼침
    await pg.evaluate("App.set({tab:'graph'})")
    await pg.wait_for_timeout(380)

    async def act_graph_expand():
        dom_btn = pg.locator('#z-center [data-gr-node^="CAT:"]').first
        if await dom_btn.count() == 0:
            return False
        await dom_btn.click()
        await pg.wait_for_timeout(260)
        std_btn = pg.locator('#z-center [data-gr-node^="STD_"]').first
        if await std_btn.count() > 0:
            await std_btn.click()
    out['graph_expand'] = await sample_action(pg, act_graph_expand, 520)

    layout_anim = await pg.evaluate(LAYOUT_ANIM_JS)
    if cdp:
        await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 1})
    await ctx.close()
    return {'metrics': out, 'layout_anim': layout_anim, 'errors': errs, 'external': ext}


async def run_frame_bench(b) -> dict:
    r1 = await measure_frames_once(b, cpu_rate=1)
    r4 = await measure_frames_once(b, cpu_rate=4)
    print('레이아웃 유발 전환/애니메이션:', r1['layout_anim']['count'], r1['layout_anim']['sheet'][:6], r1['layout_anim']['active'][:6])
    for k in r1['metrics']:
        m1 = r1['metrics'][k]
        m4 = r4['metrics'][k]
        s1 = f"p50={m1['p50_ms']}ms p95={m1['p95_ms']}ms >33ms={m1['over_33ms']}/{m1['frames']}" if m1 else '미구현'
        s4 = f"p50={m4['p50_ms']}ms p95={m4['p95_ms']}ms >33ms={m4['over_33ms']}/{m4['frames']}" if m4 else '미구현'
        print(f'  프레임 [{k}]: 보통({s1}) | CPU4배느림({s4})')
    return {
        'cpu_1x': r1['metrics'],
        'cpu_4x': r4['metrics'],
        'layout_animations': r1['layout_anim'],
    }


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
    shot_names = [
        'brief', 'market', 'market-sel', 'market-sheet', 'market-rev', 'market-base4', 'market-cond',
        'tab2', 'tab3', 'gate-sel', 'gate-table', 'tab4', 'cover-sel', 'cover-table', 'tab5', 'graph',
        'dark', 'dark-sel', 'dark-brief', 'motion', 'full', 'scroll',
    ]
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        if FRAMES_ONLY:
            report['frame_benchmark'] = await run_frame_bench(b)
            await b.close()
            (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
            print('프레임 측정 저장:', OUT / 'report.json')
            return
        if not ONLY or 'w1920' in ONLY:
            report['frame_benchmark'] = await run_frame_bench(b)
        for vw, vh, tag in SIZES:
            if ONLY and not any(ONLY in f'{tag}-{s}' for s in shot_names):
                continue
            ctx, pg, errs, ext = await page_for(b, vw, vh)
            # 1. 처음 여는 상태(가로 기준축과 다섯 묶음 기둥)
            await shot(pg, f'{tag}-brief', report)

            # 2. 고객군과 시장(네 줄 시간축 + 24개 고리 마디)
            await pg.locator('#tab-market').click()
            await pg.wait_for_timeout(240)
            await shot(pg, f'{tag}-market', report)
            await shot(pg, f'{tag}-tab2', report)

            # 고객군 고리 하나 선택 -> 오른쪽 상세(좁은 창은 아래에서 올라오는 판)
            await pg.locator('#z-center .mk-ring[data-grid-r="0"][data-grid-c="1"]').click()
            await pg.wait_for_timeout(240)
            await shot(pg, f'{tag}-market-sel', report)
            if vw < 1000:
                await shot(pg, f'{tag}-market-sheet', report)
            await pg.keyboard.press('Escape')
            await pg.wait_for_timeout(200)

            # 개정과 시장 모달 열기 후 복귀
            await pg.locator('#mk-btn-rev').click()
            await pg.wait_for_timeout(220)
            await shot(pg, f'{tag}-market-rev', report)
            await pg.keyboard.press('Escape')
            await pg.wait_for_timeout(180)

            # 기준 종형 4종으로(R11) 및 고객 조건 변경(70세, 수술만 1~2년 전)
            await pg.evaluate(f"App.set({{base:'{B4}'}})")
            await pg.wait_for_timeout(220)
            await shot(pg, f'{tag}-market-base4', report)
            await pg.evaluate("App.set({base:'EPOST_P500129_8dba92', age:70, since:1, surg:true})")
            await pg.wait_for_timeout(220)
            await shot(pg, f'{tag}-market-cond', report)
            if vw < 1000:
                await pg.mouse.move(2, 2)
                await pg.evaluate("window.scrollTo(0, 420)")
                await pg.wait_for_timeout(180)
                await shot(pg, f'{tag}-market-scroll', report)
                await pg.evaluate("window.scrollTo(0, 0)")

            # 기본 대표 조건(50세 남성, 이력 없음)으로 복귀 뒤 가입 관문, 담보 비교, 영업 인사이트, 관계 지도 측정
            await pg.evaluate("App.set({age:50, since:null, surg:false})")
            await pg.wait_for_timeout(180)

            # 3. 가입 관문, 담보 비교, 영업 인사이트, 관계 지도
            for sname, tid in [('tab3', 'gate'), ('tab4', 'cover'), ('tab5', 'insight'), ('graph', 'graph')]:
                if ONLY and sname not in ONLY and tid not in ONLY and ONLY not in tag:
                    continue
                await pg.evaluate(f"App.set({{tab:'{tid}'}})")
                await pg.wait_for_timeout(200)
                await shot(pg, f'{tag}-{sname}', report)
                if tid == 'gate':
                    await pg.locator('#z-center .gtf-cell').first.click()
                    await pg.wait_for_timeout(220)
                    await shot(pg, f'{tag}-gate-sel', report)
                    await pg.keyboard.press('Escape')
                    await pg.wait_for_timeout(180)
                    if vw == 1920:
                        await pg.locator('#gt-btn-tbl').click()
                        await pg.wait_for_timeout(240)
                        await shot(pg, f'{tag}-gate-table', report)
                        await pg.keyboard.press('Escape')
                        await pg.wait_for_timeout(180)
                elif tid == 'cover':
                    await pg.locator('#z-center .cvp-slot, #z-center .cvp-btn').nth(1).click()
                    await pg.wait_for_timeout(220)
                    await shot(pg, f'{tag}-cover-sel', report)
                    await pg.keyboard.press('Escape')
                    await pg.wait_for_timeout(180)
                    if vw == 1920:
                        await pg.locator('#cv-btn-tbl').click()
                        await pg.wait_for_timeout(240)
                        await shot(pg, f'{tag}-cover-table', report)
                        await pg.keyboard.press('Escape')
                        await pg.wait_for_timeout(180)

            await pg.evaluate("App.set({tab:'brief', age:50, since:null, surg:false})")
            await pg.wait_for_timeout(200)
            await shot(pg, f'{tag}-brief-full', report, full=True)
            report[f'{tag}-errors'] = {'console': errs, 'external': ext}
            await ctx.close()

            # 4. 짙은 스킨(고객군과 시장 3구역 + 고리 선택 + 처음 화면)
            ctx, pg, errs, ext = await page_for(b, vw, vh, skin='dark')
            await shot(pg, f'{tag}-dark-brief', report, dark=True)
            await pg.locator('#tab-market').click()
            await pg.wait_for_timeout(240)
            await shot(pg, f'{tag}-dark', report, dark=True)
            await pg.locator('#z-center .mk-ring[data-grid-r="0"][data-grid-c="1"]').click()
            await pg.wait_for_timeout(240)
            await shot(pg, f'{tag}-dark-sel', report, dark=True)
            report[f'{tag}-dark-errors'] = {'console': errs, 'external': ext}
            await ctx.close()

            # 5. 움직임 켬: 처음 화면에서 고객군과 시장 탭을 눌렀을 때 200ms / 900ms
            if vw in (1920, 380):
                ctx, pg, errs, ext = await page_for(b, vw, vh, motion='on')
                await pg.wait_for_timeout(950)
                await pg.locator('#tab-market').click()
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
