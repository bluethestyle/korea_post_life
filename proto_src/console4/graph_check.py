"""관계 그래프 탭 담보별 연결의 측정 스크립트(요청 38의 12절).

쓰기:
  python proto_src/console4/graph_check.py [--html site/proto/console4.html] [--sizes 1920x1080,1600x900,1366x768,1280x800]
                                           [--out shots_console4/graph_check.json] [--cpu4]

하는 일:
  1) 기대값을 화면 코드(tab6.js)가 아니라 자료에서 따로 계산한다. 페이지의 graph-data JSON 원자료(보유 엣지, 회사 노드의 업권)와
     담보 비교 탭의 판정 원자료(App.cover.rawB 의 cols, rows, 쌍판정과 App.cover.rawMeta 의 판정표)만 읽는다.
     기준 종형 다섯 x 비교 범위 셋(전체, 생명보험, 손해보험)의 그룹 구성, 담보별 보유 구분(data-gr-cls)과 표시(data-gr-mark),
     판정 필터 다섯의 강조 수.
  2) 화면 값은 3.13절의 data 속성과 요소 좌표로 읽어 대조하고, 레이아웃 지표(겹침, 간격, 그룹 원 밖 노드, 그룹 원 사이 간격,
     여백, 번들 엣지 교차, 직각 엣지, 라벨 겹침과 영역 밖, 라벨 글자 크기, 담보 이름 라벨 수, 결정성, 그룹 안 구역 차례와
     최근접 이웃 일치, 선택 전후 이동, 기관코드 노출, 콘솔 오류, 외부 요청)를 잰다.
  3) 결과를 JSON 파일로 쓴다. 조건 변경은 다른 탭과 같은 경로(App.set 의 base, peerScope)로 한다.
"""
from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import math
import re
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
DOM_ORDER = ['암보장', '뇌혈관보장', '뇌심장보장', '심장보장', '공통보장']
SCOPES = ['all', 'life', 'nonlife']

# 기대값: 자료에서 따로 계산한다(tab6.js 의 함수를 부르지 않는다)
EXPECT_JS = r"""
(args) => {
  const [base, scope] = args;
  const raw = JSON.parse(document.getElementById('graph-data').textContent);
  const NK = Object.fromEntries(raw.kinds.map((n, i) => [n, i]));
  const EK = Object.fromEntries(raw.ekinds.map((n, i) => [n, i]));
  const key = k => raw.keys[+k];
  const props = p => { const o = {}; for (const [k, v] of Object.entries(p || {})) o[key(k)] = v; return o; };
  const nodes = raw.nodes;
  const idx = new Map(nodes.map((n, i) => [n[0], i]));
  const sector = {};
  nodes.forEach(n => { if (n[1] === NK['회사']) sector[n[3]] = props(n[4])['업권'] || ''; });
  const inScope = code => scope === 'all' || (scope === 'life' ? sector[code] === '생명보험' : sector[code] === '손해보험');
  const peersRaw = raw.summary['맞붙는종형'][base] || [];
  const types = [base].concat(peersRaw.filter(id => inScope(nodes[idx.get(id)][3])));
  const codes = types.map(id => nodes[idx.get(id)][3]);
  const tIdx = new Map(types.map((id, s) => [idx.get(id), s]));
  const held = new Map();   // 표준담보 번호 -> [{slot, p}]
  (raw.edges2 || []).forEach(e => {
    if (e[2] !== EK['보유'] || !tIdx.has(e[0])) return;
    if (!held.has(e[1])) held.set(e[1], []);
    held.get(e[1]).push({ slot: tIdx.get(e[0]), p: props(e[3]) });
  });
  const B = App.cover.rawB(base);
  const table = App.cover.rawMeta().table;
  const rows = new Map(((B && B.rows) || []).map(r => [r[0], r]));
  const cols = (B && B.cols) || [];
  const peerKs = [];
  for (let k = 1; k < cols.length; k++) { const ni = idx.get(cols[k]); if (ni != null && inScope(nodes[ni][3])) peerKs.push(k); }
  const out = { types, codes, stds: {}, groups: {}, filters: { win: 0, lose: 0, diff: 0, wait: 0, rel: 0 }, marks: { sole: 0, 'peer-rel': 0, 'ours-wide': 0, 'ours-part': 0, wait: 0 } };
  const stdIds = Array.from(held.keys()).sort((a, b) => a - b);
  stdIds.forEach(si => {
    const hs = held.get(si).sort((a, b) => a.slot - b.slot);
    const slots = hs.map(h => h.slot);
    const ours = slots[0] === 0;
    const kp = slots.length - (ours ? 1 : 0);
    const cls = ours && kp === 0 ? 'only' : ours ? 'shared' : 'peer';
    const gkey = slots.map(s => codes[s]).join(',');
    out.groups[gkey] = (out.groups[gkey] || 0) + 1;
    const sid = nodes[si][0];
    const row = rows.get(sid);
    const marks = [];
    const hits = [];
    if (row) {
      const causes = peerKs.map(k => { const pv = B['쌍판정'] && B['쌍판정'][sid] ? B['쌍판정'][sid][k - 1] : null; return pv ? pv[0] : null; }).filter(Boolean);
      const oc = row[1][0];
      const oursRel = oc && typeof oc === 'object' && !(oc.i && oc.i.length) && oc.c ? oc.c : null;
      if (cls === 'only') marks.push(causes.includes('관계 담보로 덮음') ? 'peer-rel' : 'sole');
      if (cls === 'peer' && oursRel && oursRel[0] === '넓은 담보') marks.push('ours-wide');
      if (cls === 'peer' && oursRel && oursRel[0] === '부분 담보') marks.push('ours-part');
      const wait = hs.some(h => (+h.p['매핑검수대기급부수'] || 0) > 0 || (+h.p['추출검수대기급부수'] || 0) > 0);
      if (wait) marks.push('wait');
      if (causes.includes('나음')) hits.push('win');
      if (causes.includes('못함')) hits.push('lose');
      if (causes.some(c => table[c] && table[c]['칩'] === 'diff')) hits.push('diff');
      if (causes.includes('검토 대기') || wait) hits.push('wait');
      if (causes.includes('관계 담보로 덮음') || oursRel) hits.push('rel');
    }
    marks.forEach(m => { out.marks[m] += 1; });
    hits.forEach(h => { out.filters[h] += 1; });
    const p = props(nodes[si][4]);
    out.stds[sid] = { cls, group: gkey, mark: marks.join(' '), dom: p['보장대분류'] || '', order: si };
  });
  return out;
}
"""

# 화면 값: data 속성과 요소 좌표
SCREEN_JS = r"""
() => {
  const svg = document.getElementById('gr-net-svg');
  if (!svg) return null;
  const sr = svg.getBoundingClientRect();
  const tr = el => { const m = /translate\(([-\d.]+)[ ,]+([-\d.]+)\)/.exec(el.getAttribute('transform') || ''); return m ? [+m[1], +m[2]] : [NaN, NaN]; };
  const nodes = Array.from(svg.querySelectorAll('.gr-n')).map(el => { const [x, y] = tr(el); return { id: el.dataset.grId, kind: el.dataset.grKind, r: +el.dataset.grR, group: el.dataset.grGroup, cls: el.dataset.grCls, mark: el.dataset.grMark || '', x, y }; });
  const anchors = Array.from(svg.querySelectorAll('.gr-a')).map(el => { const [x, y] = tr(el); return { id: el.dataset.grId, kind: el.dataset.grKind, r: +el.dataset.grR, x, y }; });
  const groups = Array.from(svg.querySelectorAll('.gr-g')).map(el => ({ key: el.dataset.grGroup, count: +el.dataset.grCount, x: +el.getAttribute('cx'), y: +el.getAttribute('cy'), R: +el.getAttribute('r') }));
  const edges = Array.from(svg.querySelectorAll('.gr-l-edges > *, .gr-l-hot > *')).map(el => ({ tag: el.tagName.toLowerCase(), d: el.getAttribute('d') || '', ekind: el.dataset.grEkind, bundle: el.dataset.grBundle === '1', s: el.dataset.grS, t: el.dataset.grT,
    x1: +el.getAttribute('x1'), y1: +el.getAttribute('y1'), x2: +el.getAttribute('x2'), y2: +el.getAttribute('y2') }));
  const labels = Array.from(svg.querySelectorAll('[data-gr-lb]')).map(el => {
    const texts = el.tagName.toLowerCase() === 'text' ? [el] : Array.from(el.querySelectorAll('text'));
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    texts.forEach(tx => { const r = tx.getBoundingClientRect(); x0 = Math.min(x0, r.left - sr.left); y0 = Math.min(y0, r.top - sr.top); x1 = Math.max(x1, r.right - sr.left); y1 = Math.max(y1, r.bottom - sr.top); });
    const bb = texts.map(tx => tx.getBBox()).reduce((a, b) => ({ x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), r: Math.max(a.r, b.x + b.width), b: Math.max(a.b, b.y + b.height) }), { x: Infinity, y: Infinity, r: -Infinity, b: -Infinity });
    const fs = Math.min(...texts.map(tx => parseFloat(getComputedStyle(tx).fontSize)));
    return { type: el.dataset.grLb, for: el.dataset.grFor || el.dataset.grGlabel || '', box: [bb.x, bb.y, bb.r, bb.b], fs, text: texts.map(t => t.textContent).join(' | ') };
  });
  const flt = Array.from(document.querySelectorAll('[data-gr-filter^="f:"]')).map(b => ({ id: b.dataset.grFilter.slice(2), label: b.querySelector('span').textContent, n: +(b.querySelector('.num') || {}).textContent }));
  return { W: +svg.getAttribute('width'), H: +svg.getAttribute('height'), k: +svg.dataset.grK, ms: +svg.dataset.grMs, nodes, anchors, groups, edges, labels, flt };
}
"""

ORG_TEXT_JS = r"""
() => {
  const raw = JSON.parse(document.getElementById('graph-data').textContent);
  const NK = Object.fromEntries(raw.kinds.map((n, i) => [n, i]));
  const orgs = raw.nodes.filter(n => n[1] === NK['회사']).map(n => [n[3], n[2]]);
  const roots = ['#z-left', '#z-center', '#z-right'].map(s => document.querySelector(s)).filter(Boolean);
  const texts = [];
  roots.forEach(root => {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) { if (n.parentElement && !n.parentElement.closest('.gr-ids') && n.parentElement.getClientRects().length) texts.push(n.textContent); }
    root.querySelectorAll('[aria-label],[title]').forEach(el => { if (!el.closest('.gr-ids')) { texts.push(el.getAttribute('aria-label') || ''); texts.push(el.getAttribute('title') || ''); } });
  });
  const hits = [];
  orgs.forEach(([code, name]) => {
    const re = new RegExp('(^|[^A-Za-z0-9_])' + code + '(?![A-Za-z0-9_])');
    texts.forEach(tx => { if (re.test(tx.split(name).join(''))) hits.push([code, tx.slice(0, 60)]); });
  });
  return hits;
}
"""


def seg_cross(a, b):
    (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b
    def orient(ax, ay, bx, by, cx, cy):
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    d1 = orient(x3, y3, x4, y4, x1, y1)
    d2 = orient(x3, y3, x4, y4, x2, y2)
    d3 = orient(x1, y1, x2, y2, x3, y3)
    d4 = orient(x1, y1, x2, y2, x4, y4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def rect_overlap(a, b, tol=0.5):
    return a[0] < b[2] - tol and b[0] < a[2] - tol and a[1] < b[3] - tol and b[1] < a[3] - tol


def rect_circle(b, x, y, r, tol=0.5):
    cx = min(max(x, b[0]), b[2])
    cy = min(max(y, b[1]), b[3])
    return (cx - x) ** 2 + (cy - y) ** 2 < (r - tol) ** 2


def layout_metrics(sc: dict) -> dict:
    W, H, k = sc['W'], sc['H'], sc['k']
    gap_req = 3 if k < 1 else 4
    nodes, groups, anchors = sc['nodes'], sc['groups'], sc['anchors']
    gmap = {g['key']: g for g in groups}
    overlap = 0
    min_gap = math.inf
    for a, b in itertools.combinations(nodes, 2):
        d = math.hypot(a['x'] - b['x'], a['y'] - b['y']) - a['r'] - b['r']
        min_gap = min(min_gap, d)
        if d < 0:
            overlap += 1
    gap_bad = sum(1 for a, b in itertools.combinations(nodes, 2)
                  if math.hypot(a['x'] - b['x'], a['y'] - b['y']) - a['r'] - b['r'] < gap_req - 0.01)
    outside = sum(1 for n in nodes if n['group'] in gmap and
                  math.hypot(n['x'] - gmap[n['group']]['x'], n['y'] - gmap[n['group']]['y']) + n['r'] > gmap[n['group']]['R'] + 0.01)
    gmin = math.inf
    for a, b in itertools.combinations(groups, 2):
        gmin = min(gmin, math.hypot(a['x'] - b['x'], a['y'] - b['y']) - a['R'] - b['R'])
    margin_bad = sum(1 for n in nodes if n['x'] - n['r'] < 20 - 0.01 or n['y'] - n['r'] < 20 - 0.01
                     or n['x'] + n['r'] > W - 20 + 0.01 or n['y'] + n['r'] > H - 20 + 0.01)
    bundles = [e for e in sc['edges'] if e['bundle']]
    cross = 0
    for a, b in itertools.combinations(bundles, 2):
        if a['s'] == b['s'] or a['t'] == b['t']:
            continue
        if seg_cross((a['x1'], a['y1'], a['x2'], a['y2']), (b['x1'], b['y1'], b['x2'], b['y2'])):
            cross += 1
    ortho = sum(1 for e in sc['edges'] if not (e['tag'] == 'line' or (e['tag'] == 'path' and re.fullmatch(r'\s*M[^MLQCAHVZ]+[LQ][^MLQCAHVZ]+', e['d'] or ''))))
    labels = sc['labels']
    lab_overlap = sum(1 for a, b in itertools.combinations(labels, 2) if rect_overlap(a['box'], b['box']))
    circles = [(n['x'], n['y'], n['r'], n['id']) for n in nodes] + [(a['x'], a['y'], a['r'], a['id']) for a in anchors]
    lab_node = 0
    for lb in labels:
        for x, y, r, nid in circles:
            if rect_circle(lb['box'], x, y, r):
                lab_node += 1
    lab_out = sum(1 for lb in labels if lb['box'][0] < -0.5 or lb['box'][1] < -0.5 or lb['box'][2] > W + 0.5 or lb['box'][3] > H + 0.5)
    fs_min = min((lb['fs'] for lb in labels), default=0)
    n_anchor_lb = sum(1 for lb in labels if lb['type'] == 'anchor')
    n_group_lb = sum(1 for lb in labels if lb['type'] in ('group', 'badge'))
    n_badge = sum(1 for lb in labels if lb['type'] == 'badge')
    n_std_lb = sum(1 for lb in labels if lb['type'] == 'std')
    return {
        'W': W, 'H': H, 'k': k, 'nodes': len(nodes), 'groups': len(groups), 'bundles': len(bundles),
        'node_overlap': overlap, 'node_min_gap': round(min_gap, 2), 'node_gap_req': gap_req, 'node_gap_violations': gap_bad,
        'outside_group': outside, 'group_min_gap': round(gmin, 2), 'margin_violations': margin_bad,
        'bundle_crossings': cross, 'orthogonal_edges': ortho,
        'label_overlap': lab_overlap, 'label_node_overlap': lab_node, 'label_outside': lab_out, 'label_font_min': fs_min,
        'anchor_labels': n_anchor_lb, 'group_labels': n_group_lb, 'group_badges': n_badge,
        'std_labels': n_std_lb, 'layout_ms': sc['ms'],
    }


def intra_group(sc: dict, exp: dict) -> dict:
    """12절 10번: 구역 차례 위반(담보 4개 이상 그룹)과 최근접 이웃 일치(담보 3개 이상 그룹)."""
    gmap = {g['key']: g for g in sc['groups']}
    by = {}
    for n in sc['nodes']:
        by.setdefault(n['group'], []).append(n)
    viol = 0
    agree = total = 0
    for key, mem in by.items():
        g = gmap[key]
        dom = lambda n: exp['stds'][n['id']]['dom']
        if len(mem) >= 4:
            angs = {}
            for d in set(dom(n) for n in mem):
                pts = [n for n in mem if dom(n) == d]
                mx = sum(n['x'] for n in pts) / len(pts) - g['x']
                my = sum(n['y'] for n in pts) / len(pts) - g['y']
                angs[d] = (math.degrees(math.atan2(mx, -my)) + 360) % 360
            seen = sorted(angs, key=lambda d: angs[d])
            ref = [d for d in DOM_ORDER if d in angs] + sorted(d for d in angs if d not in DOM_ORDER)
            rots = [ref[i:] + ref[:i] for i in range(len(ref))]
            if seen not in rots:
                viol += 1
        if len(mem) >= 3:
            for n in mem:
                best = min((m for m in mem if m is not n),
                           key=lambda m: (round(math.hypot(m['x'] - n['x'], m['y'] - n['y']), 6), exp['stds'][m['id']]['order']))
                total += 1
                agree += dom(best) == dom(n)
    return {'zone_order_violations': viol, 'nn_agreement': round(agree / total, 3) if total else None, 'nn_measured': total}


def compare(sc: dict, exp: dict) -> dict:
    scr = {n['id']: n for n in sc['nodes']}
    mism = []
    for sid, e in exp['stds'].items():
        s = scr.get(sid)
        if not s:
            mism.append([sid, 'missing'])
            continue
        if s['cls'] != e['cls'] or s['mark'] != e['mark'] or s['group'] != e['group']:
            mism.append([sid, {'screen': [s['cls'], s['mark'], s['group']], 'expect': [e['cls'], e['mark'], e['group']]}])
    extra = [sid for sid in scr if sid not in exp['stds']]
    gscr = {g['key']: g['count'] for g in sc['groups']}
    ginside = {}
    for n in sc['nodes']:
        ginside[n['group']] = ginside.get(n['group'], 0) + 1
    glabel_counts = {}
    for lb in sc['labels']:
        if lb['type'] in ('group', 'badge'):
            m = re.search(r'담보 (\d+)개', lb['text']) or re.search(r'^(\d+)$', lb['text'])
            glabel_counts[lb['for']] = int(m.group(1)) if m else None
    fscr = {f['id']: f['n'] for f in sc['flt']}
    return {
        'std_mismatch': mism, 'std_extra': extra,
        'groups_expect': exp['groups'], 'groups_count_attr': gscr, 'groups_inside': ginside, 'groups_label': glabel_counts,
        'groups_ok': exp['groups'] == gscr == ginside and all(glabel_counts.get(k) == v for k, v in exp['groups'].items()),
        'marks_expect': exp['marks'],
        'filters_expect': exp['filters'], 'filters_button': fscr,
    }


async def set_cond(pg, base, scope):
    await pg.evaluate("(a) => App.set({ base: a[0], peerScope: a[1] })", [base, scope])
    await pg.wait_for_timeout(250)
    await pg.wait_for_function("() => !!document.getElementById('gr-net-svg')", timeout=8000)
    await pg.wait_for_timeout(150)


async def filter_counts(pg):
    out = {}
    for fid in ['win', 'lose', 'diff', 'wait', 'rel']:
        btn = pg.locator(f'[data-gr-filter="f:{fid}"]')
        await btn.click()
        await pg.wait_for_timeout(60)
        out[fid] = await pg.evaluate("() => document.querySelectorAll('#gr-net-svg .gr-n.is-on').length")
        await btn.click()
        await pg.wait_for_timeout(30)
    return out


def coords(sc):
    return sorted([(n['id'], round(n['x'], 2), round(n['y'], 2)) for n in sc['nodes']] +
                  [(g['key'], round(g['x'], 2), round(g['y'], 2), round(g['R'], 2)) for g in sc['groups']])


async def run(args):
    url = Path(args.html).resolve().as_uri() + '#t=graph'
    sizes = [tuple(int(v) for v in s.split('x')) for s in args.sizes.split(',')]
    result = {'html': str(Path(args.html)), 'sizes': {}, 'data': {}, 'checks': {}}
    async with async_playwright() as p:
        br = await p.chromium.launch()
        for (vw, vh) in sizes:
            pg = await br.new_page(viewport={'width': vw, 'height': vh})
            errs, ext = [], []
            pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('request', lambda r: ext.append(r.url) if not r.url.startswith(('file:', 'data:', 'blob:')) else None)
            await pg.goto(url)
            await pg.wait_for_function("() => !!document.getElementById('gr-net-svg')", timeout=10000)
            await pg.wait_for_timeout(600)
            bases = await pg.evaluate("() => Object.keys(App.S['기준별'])")
            names = await pg.evaluate("() => Object.fromEntries(Object.entries(App.S['기준별']).map(([k, v]) => [k, (App.txt.vinfo(k) || {})['종형명'] || k]))")
            per = {}
            scopes = SCOPES if (vw, vh) == sizes[0] else ['all']
            for scope in scopes:
                for b in bases:
                    await set_cond(pg, b, scope)
                    sc = await pg.evaluate(SCREEN_JS)
                    exp = await pg.evaluate(EXPECT_JS, [b, scope])
                    item = {'name': names.get(b, b), 'layout': layout_metrics(sc), 'data': compare(sc, exp)}
                    item['data']['filters_highlight'] = await filter_counts(pg)
                    item['intra'] = intra_group(sc, exp)
                    per[f'{scope}|{b}'] = item
            # 결정성: 같은 조건으로 새로고침 두 번, 조건을 바꿨다 돌아오기
            await set_cond(pg, bases[0], 'all')
            first = coords(await pg.evaluate(SCREEN_JS))
            await set_cond(pg, bases[-1], 'life')
            await set_cond(pg, bases[0], 'all')
            back = coords(await pg.evaluate(SCREEN_JS))
            reloads = []
            for _ in range(2):
                await pg.reload()
                await pg.wait_for_function("() => !!document.getElementById('gr-net-svg')", timeout=10000)
                await pg.wait_for_timeout(500)
                reloads.append(coords(await pg.evaluate(SCREEN_JS)))
            def maxdiff(a, b):
                if len(a) != len(b):
                    return math.inf
                return max((max(abs(x - y) for x, y in zip(p[1:], q[1:])) for p, q in zip(a, b) if p[0] == q[0]), default=0)
            det = {'reload_max_diff': maxdiff(first, reloads[0]), 'reload2_max_diff': maxdiff(reloads[0], reloads[1]),
                   'cond_back_max_diff': maxdiff(first, back)}
            # 선택 전후: 기존 노드 이동, 그래프 영역 크기
            before = await pg.evaluate(SCREEN_JS)
            surg_id = await pg.evaluate("() => { const el = Array.from(document.querySelectorAll('#gr-net-svg .gr-n')).find(e => e.dataset.tipTitle === '암 수술비'); return el ? el.dataset.grId : ''; }")
            target = next((n for n in before['nodes'] if n['id'] == surg_id), None) or before['nodes'][0]
            await pg.evaluate("(id) => { const el = document.querySelector(`#gr-net-svg .gr-n[data-gr-id=\"${id}\"]`); const r = el.getBoundingClientRect(); el.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 })); }", target['id'])
            await pg.wait_for_timeout(500)
            after = await pg.evaluate(SCREEN_JS)
            amap = {n['id']: n for n in after['nodes']}
            sel = {'target': target['id'], 'max_move': max(math.hypot(n['x'] - amap[n['id']]['x'], n['y'] - amap[n['id']]['y']) for n in before['nodes']),
                   'area_change': [after['W'] - before['W'], after['H'] - before['H']],
                   'panel_open': await pg.evaluate("() => document.getElementById('z-right').classList.contains('is-picked')")}
            org_hits = await pg.evaluate(ORG_TEXT_JS)
            await pg.keyboard.press('Escape')
            await pg.wait_for_timeout(300)
            hscroll = await pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
            math_random = await pg.evaluate("() => (document.documentElement.outerHTML.match(/Math\\.random/g) || []).length")
            result['sizes'][f'{vw}x{vh}'] = {'states': per, 'determinism': det, 'selection': sel, 'org_code_text': org_hits,
                                             'console_errors': errs, 'external_requests': ext, 'hscroll': hscroll,
                                             'math_random_in_html': math_random}
            await pg.close()
        if args.cpu4:
            pg = await br.new_page(viewport={'width': sizes[0][0], 'height': sizes[0][1]})
            cdp = await pg.context.new_cdp_session(pg)
            await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
            await pg.goto(url)
            await pg.wait_for_function("() => !!document.getElementById('gr-net-svg')", timeout=20000)
            await pg.wait_for_timeout(4000)
            bases = await pg.evaluate("() => Object.keys(App.S['기준별'])")
            ms = {}
            for scope in SCOPES:
                for b in bases:
                    await set_cond(pg, b, scope)
                    ms[f'{scope}|{b}'] = await pg.evaluate("() => +document.getElementById('gr-net-svg').dataset.grMs")
            result['cpu4_layout_ms'] = ms
            await pg.close()
        await br.close()
    # 요약 판정
    summ = {}
    for size, r in result['sizes'].items():
        for key, it in r['states'].items():
            L, D = it['layout'], it['data']
            fails = []
            if L['node_overlap']: fails.append('node_overlap')
            if L['node_gap_violations']: fails.append('node_gap')
            if L['outside_group']: fails.append('outside_group')
            if L['group_min_gap'] < 14 - 0.01: fails.append('group_gap')
            if L['margin_violations']: fails.append('margin')
            if L['bundle_crossings']: fails.append('bundle_crossings')
            if L['orthogonal_edges']: fails.append('orthogonal')
            if L['label_overlap'] or L['label_node_overlap'] or L['label_outside']: fails.append('labels')
            if L['label_font_min'] < 13: fails.append('label_font')
            if D['std_mismatch'] or D['std_extra']: fails.append('std_mismatch')
            if not D['groups_ok']: fails.append('groups')
            if D['filters_expect'] != D['filters_button'] or D['filters_expect'] != D['filters_highlight']: fails.append('filters')
            summ[f'{size}|{key}'] = fails
    result['summary_fails'] = {k: v for k, v in summ.items() if v}
    result['summary_states'] = len(summ)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"상태 {len(summ)}개, 실패 {len(result['summary_fails'])}개 -> {args.out}")
    for k, v in result['summary_fails'].items():
        print(' ', k, v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--html', default=str(ROOT / 'site/proto/console4.html'))
    ap.add_argument('--sizes', default='1920x1080,1600x900,1366x768,1280x800')
    ap.add_argument('--out', default=str(ROOT / 'shots_console4/graph_check.json'))
    ap.add_argument('--cpu4', action='store_true', help='CPU 4배 느림에서 조건마다 레이아웃 계산 시간을 잰다')
    asyncio.run(run(ap.parse_args()))


if __name__ == '__main__':
    main()
