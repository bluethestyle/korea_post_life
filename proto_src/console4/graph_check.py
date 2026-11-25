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
    // 타사 4개사 이상은 보유 타사 수 구간(8.1): n 타사 수, k 보유 타사 수, h = n/2 올림
    const nP = types.length - 1, h = Math.ceil(nP / 2);
    const bin = nP <= 3 ? null : ours ? (kp === 0 ? 'only' : kp === nP ? 'all' : kp >= h ? 'many' : 'few')
      : (kp === nP ? 'p-all' : kp >= h ? 'p-many' : kp >= 2 ? 'p-few' : 'p-one');
    const gkey = bin ? 'bin:' + bin : slots.map(s => codes[s]).join(',');
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
  const nodes = Array.from(svg.querySelectorAll('.gr-l-nodes > .gr-n')).map(el => { const [x, y] = tr(el); return { id: el.dataset.grId, kind: el.dataset.grKind, r: +el.dataset.grR, group: el.dataset.grGroup, cls: el.dataset.grCls, mark: el.dataset.grMark || '', x, y }; });
  const anchors = Array.from(svg.querySelectorAll('.gr-l-anchors > .gr-a')).map(el => { const [x, y] = tr(el); return { id: el.dataset.grId, kind: el.dataset.grKind, r: +el.dataset.grR, x, y }; });
  const groups = Array.from(svg.querySelectorAll('.gr-l-groups > .gr-g')).map(el => ({ key: el.dataset.grGroup, count: +el.dataset.grCount, x: +el.getAttribute('cx'), y: +el.getAttribute('cy'), R: +el.getAttribute('r') }));
  const edges = Array.from(svg.querySelectorAll('.gr-l-edges > *, .gr-l-hot > *')).map(el => ({ tag: el.tagName.toLowerCase(), d: el.getAttribute('d') || '', ekind: el.dataset.grEkind, bundle: el.dataset.grBundle === '1', s: el.dataset.grS, t: el.dataset.grT,
    x1: +el.getAttribute('x1'), y1: +el.getAttribute('y1'), x2: +el.getAttribute('x2'), y2: +el.getAttribute('y2') }));
  const labels = Array.from(svg.querySelectorAll('[data-gr-lb]')).filter(el => !el.closest('.gr-l-ghost')).map(el => {
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
    // 회사 이름 안에 든 글자(KB손해보험, KB라이프생명의 KB)는 뺀다: 모든 회사 이름을 지운 뒤 찾는다
    const strip = tx => orgs.reduce((s, o) => s.split(o[1]).join(' '), tx);
    texts.forEach(tx => { if (re.test(strip(tx))) hits.push([code, tx.slice(0, 60)]); });
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


def seg_rect(x1, y1, x2, y2, b):
    t0, t1 = 0.0, 1.0
    dx, dy = x2 - x1, y2 - y1
    for p_, q_ in ((-dx, x1 - b[0]), (dx, b[2] - x1), (-dy, y1 - b[1]), (dy, b[3] - y1)):
        if abs(p_) < 1e-9:
            if q_ < 0:
                return False
            continue
        r = q_ / p_
        if p_ < 0:
            if r > t1:
                return False
            t0 = max(t0, r)
        else:
            if r < t0:
                return False
            t1 = min(t1, r)
    return t0 <= t1


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
    lab_node_detail = []
    for lb in labels:
        for x, y, r, nid in circles:
            if rect_circle(lb['box'], x, y, r):
                lab_node += 1
                lab_node_detail.append([lb['type'], lb['text'][:30], nid])
    lab_out = sum(1 for lb in labels if lb['box'][0] < -0.5 or lb['box'][1] < -0.5 or lb['box'][2] > W + 0.5 or lb['box'][3] > H + 0.5)
    fs_min = min((lb['fs'] for lb in labels), default=0)
    n_anchor_lb = sum(1 for lb in labels if lb['type'] == 'anchor')
    n_group_lb = sum(1 for lb in labels if lb['type'] in ('group', 'badge'))
    n_badge = sum(1 for lb in labels if lb['type'] == 'badge')
    n_std_lb = sum(1 for lb in labels if lb['type'] == 'std')
    # 담보 이름 라벨이 번들 엣지 선분 위에 얹힌 수(3.9, 4단계에서 더함)
    lab_on_bundle = sum(1 for lb in labels if lb['type'] == 'std' for e in bundles
                        if seg_rect(e['x1'], e['y1'], e['x2'], e['y2'], lb['box']))
    return {
        'W': W, 'H': H, 'k': k, 'nodes': len(nodes), 'groups': len(groups), 'bundles': len(bundles),
        'node_overlap': overlap, 'node_min_gap': round(min_gap, 2), 'node_gap_req': gap_req, 'node_gap_violations': gap_bad,
        'outside_group': outside, 'group_min_gap': round(gmin, 2), 'margin_violations': margin_bad,
        'bundle_crossings': cross, 'orthogonal_edges': ortho,
        'label_overlap': lab_overlap, 'label_node_overlap': lab_node, 'label_node_detail': lab_node_detail[:10], 'label_outside': lab_out, 'label_font_min': fs_min,
        'anchor_labels': n_anchor_lb, 'group_labels': n_group_lb, 'group_badges': n_badge,
        'std_labels': n_std_lb, 'std_label_on_bundle': lab_on_bundle, 'layout_ms': sc['ms'],
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


# ---------- 4단계 측정: 선택 펼침(12절 11번), 조건을 바꿀 때 이동(13번), 트랜지션(16번), 근거 2단계 경로(5.3) ----------
EXP_JS = r"""
() => {
  const svg = document.getElementById('gr-net-svg');
  const tr = el => { const m = /translate\(([-\d.]+)[ ,]+([-\d.]+)\)/.exec(el.getAttribute('transform') || ''); return m ? [+m[1], +m[2]] : [NaN, NaN]; };
  const xs = Array.from(svg.querySelectorAll('.gr-l-exp .gr-x')).map(el => { const [x, y] = tr(el); return { id: el.dataset.grId, kind: el.dataset.grKind, r: +el.dataset.grR, x, y }; });
  const fixed = Array.from(svg.querySelectorAll('.gr-n')).map(el => { const [x, y] = tr(el); const c = el.querySelector('.gr-n-c').getBoundingClientRect(); return { id: el.dataset.grId, x, y, r: c.width / 2, big: el.classList.contains('is-big') }; })
    .concat(Array.from(svg.querySelectorAll('.gr-a')).map(el => { const [x, y] = tr(el); return { id: el.dataset.grId, x, y, r: +el.dataset.grR, big: true }; }));
  const edges = Array.from(svg.querySelectorAll('.gr-l-xe line')).map(el => ({ ekind: el.dataset.grEkind, s: el.dataset.grS, t: el.dataset.grT,
    x1: +el.getAttribute('x1'), y1: +el.getAttribute('y1'), x2: +el.getAttribute('x2'), y2: +el.getAttribute('y2') }));
  const attrsOk = xs.every(n => n.id && n.kind && n.r > 0) && edges.every(e => e.ekind && e.s && e.t);
  return { xs, fixed, edges, attrsOk };
}
"""

SAMPLE_JS = r"""
(args) => new Promise(resolve => {
  const [cond, ms] = args;
  const pos = () => {
    const svg = document.getElementById('gr-net-svg');
    const out = {};
    if (!svg) return out;
    const sr = svg.getBoundingClientRect();
    svg.querySelectorAll('.gr-n').forEach(el => {
      if (el.closest('.gr-l-ghost')) return;
      const r = el.querySelector('.gr-n-c').getBoundingClientRect();
      out[el.dataset.grId] = [r.left - sr.left + r.width / 2, r.top - sr.top + r.height / 2];
    });
    return out;
  };
  const frames = [{ t: 0, p: pos() }];
  const t0 = performance.now();
  App.set(cond);
  const tick = () => {
    const t = performance.now() - t0;
    frames.push({ t, p: pos() });
    if (t < ms) requestAnimationFrame(tick); else resolve(frames);
  };
  requestAnimationFrame(tick);
})
"""


# 담보 선택의 요약 노드: 보유 회사(종형)마다 하나, "특약 N, 급부 M" 이 원자료에서 따로 센 값과 상세 패널의 회사별 수와 같은지(2차 개선)
# 기대값은 원자료의 포함, 매핑 엣지로 센다(종형 -> 특약 -> 급부 -> 매핑된 표준담보). 검수 대기 수는 보유 엣지 속성에서 읽는다
SUM_JS = r"""
(args) => {
  const [base, scope, sid] = args;
  const raw = JSON.parse(document.getElementById('graph-data').textContent);
  const NK = Object.fromEntries(raw.kinds.map((n, i) => [n, i])), EK = Object.fromEntries(raw.ekinds.map((n, i) => [n, i]));
  const key = k => raw.keys[+k];
  const props = p => { const o = {}; for (const [k, v] of Object.entries(p || {})) o[key(k)] = v; return o; };
  const nodes = raw.nodes, idx = new Map(nodes.map((n, i) => [n[0], i]));
  const sector = {};
  nodes.forEach(n => { if (n[1] === NK['회사']) sector[n[3]] = props(n[4])['업권'] || ''; });
  const inScope = code => scope === 'all' || (scope === 'life' ? sector[code] === '생명보험' : sector[code] === '손해보험');
  const types = [base].concat((raw.summary['맞붙는종형'][base] || []).filter(id => inScope(nodes[idx.get(id)][3])));
  const si = idx.get(sid);
  const E = raw.edges.concat(raw.edges2 || []);
  const inc = new Map(), mapped = new Set();
  E.forEach(e => {
    if (e[2] === EK['포함']) { if (!inc.has(e[0])) inc.set(e[0], []); inc.get(e[0]).push(e[1]); }
    if (e[2] === EK['매핑'] && e[1] === si && nodes[e[0]][1] === NK['급부']) mapped.add(e[0]);
  });
  const held = new Map();
  (raw.edges2 || []).forEach(e => { if (e[2] === EK['보유'] && e[1] === si) held.set(e[0], props(e[3])); });
  const expect = [];
  types.forEach((vid, slot) => {
    const vi = idx.get(vid);
    if (!held.has(vi)) return;
    const rs = new Set(), bs = new Set();
    (inc.get(vi) || []).filter(x => nodes[x][1] === NK['특약']).forEach(ri => (inc.get(ri) || []).forEach(b => { if (mapped.has(b)) { rs.add(ri); bs.add(b); } }));
    const hp = held.get(vi);
    expect.push({ slot, vid, r: rs.size, b: bs.size, wm: +(hp['매핑검수대기급부수'] || 0), we: +(hp['추출검수대기급부수'] || 0) });
  });
  const svg = document.getElementById('gr-net-svg');
  const screen = Array.from(svg.querySelectorAll('.gr-l-exp .gr-x-sum')).map(el => {
    const lb = svg.querySelector(`.gr-l-exp [data-gr-lb="exp"][data-gr-for="${CSS.escape(el.dataset.grId)}"]`);
    return { slot: +el.dataset.grSlot, vid: el.dataset.grVid, r: +el.dataset.grSumR, b: +el.dataset.grSumB, title: el.dataset.tipTitle,
      lines: lb ? Array.from(lb.querySelectorAll('tspan')).map(t => t.textContent) : null };
  }).sort((a, b) => a.slot - b.slot);
  const panel = Array.from(document.querySelectorAll('#z-right .ev-body dl.kv')).slice(0, 1).flatMap(dl => Array.from(dl.querySelectorAll('dt')).map(dt => ({ org: dt.textContent.trim(), dd: (dt.nextElementSibling || {}).textContent || '' })));
  const edges = Array.from(svg.querySelectorAll('.gr-l-xe line.gr-e-sum')).map(el => [el.dataset.grS, el.dataset.grT]);
  return { expect, screen, panel, edges, sumIds: Array.from(svg.querySelectorAll('.gr-l-exp .gr-x-sum')).map(el => el.dataset.grId) };
}
"""


def sum_check(d, std_id):
    """요약 노드 대조. 틀린 항목 목록을 돌려준다(빈 목록이면 통과)"""
    bad = []
    ex, sc = d['expect'], d['screen']
    if [e['vid'] for e in ex] != [s['vid'] for s in sc]:
        bad.append(['companies', [e['vid'] for e in ex], [s['vid'] for s in sc]])
    if len(d['panel']) != len(sc):
        bad.append(['panel_rows', len(d['panel']), len(sc)])
    for e, s, pn in itertools.zip_longest(ex, sc, d['panel']):
        if not e or not s:
            continue
        want = [f"특약 {e['r']:,}, 급부 {e['b']:,}"]
        wait = ([f"매핑 검수 대기 급부 {e['wm']:,}"] if e['wm'] else []) + ([f"추출 검수 대기 급부 {e['we']:,}"] if e['we'] else [])
        if wait:
            want.append(', '.join(wait))
        if (s['r'], s['b']) != (e['r'], e['b']):
            bad.append(['count', e['vid'], [e['r'], e['b']], [s['r'], s['b']]])
        if s['lines'] != want:
            bad.append(['label', e['vid'], want, s['lines']])
        if pn and (not pn['dd'].startswith(want[0]) or not s['title'].startswith(pn['org'] + ' ')):
            bad.append(['panel', e['vid'], pn, want[0], s['title']])
    # 굵은 선: 요약 노드마다 앵커와 요약 노드, 요약 노드와 담보 둘
    want_e = sorted([[e['vid'], 'SUM:' + e['vid']] for e in ex] + [['SUM:' + e['vid'], std_id] for e in ex])
    if sorted(d['edges']) != want_e:
        bad.append(['edges', len(d['edges']), len(want_e)])
    return bad


def cross_count(edges):
    c = 0
    for a, b in itertools.combinations(edges, 2):
        if {a['s'], a['t']} & {b['s'], b['t']}:
            continue
        if seg_cross((a['x1'], a['y1'], a['x2'], a['y2']), (b['x1'], b['y1'], b['x2'], b['y2'])):
            c += 1
    return c


def trans_metrics(frames):
    first, last = frames[0]['p'], frames[-1]['p']
    per = []
    for nid, p0 in first.items():
        if nid not in last:
            continue
        p1 = last[nid]
        D = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        if D < 1:
            continue
        seq = [(f['t'], f['p'][nid]) for f in frames if nid in f['p']]
        steps = [math.hypot(b[1][0] - a[1][0], b[1][1] - a[1][1]) for a, b in zip(seq, seq[1:])]
        path = sum(steps)
        p100 = next((pp for t, pp in seq if t >= 100), seq[-1][1])
        prog100 = math.hypot(p100[0] - p0[0], p100[1] - p0[1]) / D
        per.append({'id': nid, 'D': round(D, 1), 'max_step_ratio': round(max(steps) / D, 4), 'prog100': round(prog100, 4),
                    'path_ratio': round(path / D, 4), 'one_frame': max(steps) >= 0.99 * D,
                    'moving_frames': sum(1 for s_ in steps if s_ > 0.01)})
    if not per:
        return {'moving_nodes': 0}
    return {'moving_nodes': len(per), 'max_step_ratio': max(x['max_step_ratio'] for x in per), 'max_prog100': max(x['prog100'] for x in per),
            'max_path_ratio': max(x['path_ratio'] for x in per), 'one_frame_moves': sum(1 for x in per if x['one_frame']),
            'frames': len(frames), 'min_moving_frames': min(x['moving_frames'] for x in per)}


def base_ids(bases, names):
    def find(pat):
        return next((b for b in bases if re.search(pat, names.get(b, ''))), None)
    b1, b2, b3, b4 = find('1종'), find('2종'), find('3종'), find('4종')
    bt = next((b for b in bases if b not in (b1, b2, b3, b4)), None)
    return b1, b2, b3, b4, bt


async def stage4_sel(pg, bases, names):
    # 11번: 선택 상태(기준 1종, 비교 범위 전체)
    b1 = base_ids(bases, names)[0]
    await set_cond(pg, b1, 'all')
    sel = {}
    for nm in ['암 수술비', '일반암 진단비', '종별 수술비(최고 종 기준)']:
        before = await pg.evaluate(SCREEN_JS)
        ok = await pg.evaluate("""(nm) => { const el = Array.from(document.querySelectorAll('#gr-net-svg .gr-n')).find(e => e.dataset.tipTitle === nm); if (!el) return false; const r = el.querySelector('.gr-n-c').getBoundingClientRect(); el.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 })); return el.dataset.grId; }""", nm)
        await pg.wait_for_timeout(700)
        after = await pg.evaluate(SCREEN_JS)
        ex = await pg.evaluate(EXP_JS)
        sd = await pg.evaluate(SUM_JS, [b1, 'all', ok]) if ok else {'expect': [], 'screen': [], 'panel': [], 'edges': [], 'sumIds': []}
        amap = {n['id']: n for n in after['nodes']}
        move = max(math.hypot(n['x'] - amap[n['id']]['x'], n['y'] - amap[n['id']]['y']) for n in before['nodes'])
        ov = 0
        min_gap = math.inf
        xs = ex['xs']
        for a, b in itertools.combinations(xs, 2):
            d = math.hypot(a['x'] - b['x'], a['y'] - b['y']) - a['r'] - b['r']
            min_gap = min(min_gap, d)
            ov += d < -0.01
        for a in xs:
            for f in ex['fixed']:
                d = math.hypot(a['x'] - f['x'], a['y'] - f['y']) - a['r'] - f['r']
                min_gap = min(min_gap, d)
                ov += d < -0.01
        sel[nm] = {'clicked': ok, 'max_move': round(move, 3), 'area_change': [after['W'] - before['W'], after['H'] - before['H']],
                   'exp_nodes': len(xs), 'exp_kinds': {k: sum(1 for x in xs if x['kind'] == k) for k in sorted({x['kind'] for x in xs})},
                   'exp_edges': len(ex['edges']), 'exp_overlap': ov, 'exp_min_gap': round(min_gap, 2),
                   'exp_crossings': cross_count(ex['edges']), 'attrs_ok': ex['attrsOk'],
                   'exp_node_label_overlap': sum(1 for a in xs for lb in after['labels'] if lb['type'] in ('anchor', 'group', 'badge', 'exp') and rect_circle(lb['box'], a['x'], a['y'], a['r'])),
                   'exp_label_overlap': sum(1 for a, b in itertools.combinations([lb for lb in after['labels'] if lb['type'] in ('anchor', 'group', 'badge', 'exp')], 2) if rect_overlap(a['box'], b['box'])),
                   'exp_labels': [lb['text'] for lb in after['labels'] if lb['type'] == 'exp'],
                   # 요약 노드마다 라벨이 있는지, 수가 원자료와 상세 패널과 같은지, 낱낱의 특약과 급부 노드가 없는지
                   'sum_nodes': len(sd['screen']), 'sum_expect': len(sd['expect']),
                   'sum_label_missing': [s_['vid'] for s_ in sd['screen'] if not s_['lines']],
                   'sum_mismatch': sum_check(sd, ok) if ok else ['not clicked'],
                   'exp_other_kinds': sorted({x['kind'] for x in xs} - {'summary'})}
    await pg.keyboard.press('Escape')
    await pg.wait_for_timeout(300)
    return sel


async def stage4(pg, bases, names):
    out = {}
    b1, b2, b3, b4, bt = base_ids(bases, names)
    out['bases'] = {'1': b1, '2': b2, '3': b3, '4': b4, 'unified': bt}
    out['selection'] = await stage4_sel(pg, bases, names)
    # 13번: 조건을 바꿀 때 이동(그룹 키가 같은 담보)
    co = {}
    for b in [b1, b2, b3, b4, bt]:
        await set_cond(pg, b, 'all')
        await pg.wait_for_timeout(600)
        sc = await pg.evaluate(SCREEN_JS)
        co[b] = {n['id']: (n['x'], n['y'], n['group']) for n in sc['nodes']}

    def diff(a, b, same_group):
        ds = [math.hypot(co[a][k][0] - co[b][k][0], co[a][k][1] - co[b][k][1]) for k in co[a] if k in co[b] and (not same_group or co[a][k][2] == co[b][k][2])]
        return (max(ds) if ds else 0, sum(ds) / len(ds) if ds else 0, len(ds))
    m123 = max(diff(a, b, False)[0] for a, b in itertools.combinations([b1, b2, b3], 2))
    pairs = {f'{names[a]}|{names[b]}': round(diff(a, b, True)[1], 2) for a, b in itertools.combinations([b1, b2, b3, b4, bt], 2)}
    out['cond_move'] = {'max_123_all_nodes': round(m123, 3), 'mean_3_4_all_nodes': round(diff(b3, b4, False)[1], 3),
                        'mean_4_unified_same_group': round(diff(b4, bt, True)[1], 2), 'same_group_pairs': pairs,
                        'max_pair_same_group_mean': max(pairs.values()),
                        'mean_all_pairs_same_group': round(sum(pairs.values()) / len(pairs), 2)}
    # 16번: 트랜지션 표본(requestAnimationFrame 마다 getBoundingClientRect)
    tr_ = {}
    for motion in ['on', 'calm', 'off']:
        await pg.evaluate("(m) => App.set({ motion: m })", motion)
        await set_cond(pg, b4, 'all')
        await pg.wait_for_timeout(700)
        fr = await pg.evaluate(SAMPLE_JS, [{'base': bt, 'peerScope': 'all'}, 900])
        tr_[f'{motion}|4->unified'] = trans_metrics(fr)
        await pg.wait_for_timeout(300)
        await set_cond(pg, b1, 'all')
        await pg.wait_for_timeout(700)
        fr = await pg.evaluate(SAMPLE_JS, [{'base': b1, 'peerScope': 'life'}, 900])
        tr_[f'{motion}|all->life'] = trans_metrics(fr)
        await pg.wait_for_timeout(300)
    await pg.evaluate("() => App.set({ motion: 'on' })")
    out['transition'] = tr_
    # 5.3 근거 2단계 경로: 관련 담보 표시가 붙은 담보를 호버해 담보 관계 엣지 가운데 그 담보에 닿지 않는 엣지가 있는 담보를 센다
    ev = {}
    for b in [b1, b2, b3, b4, bt]:
        await set_cond(pg, b, 'all')
        await pg.wait_for_timeout(400)
        ev[names[b]] = await pg.evaluate("""async () => {
          const svg = document.getElementById('gr-net-svg');
          const els = Array.from(svg.querySelectorAll('.gr-n')).filter(el => /ours-wide|ours-part|peer-rel/.test(el.dataset.grMark));
          let two = 0; const names = []; let twoPeer = 0; const peerNames = [];
          for (const el of els) {
            const r = el.querySelector('.gr-n-c').getBoundingClientRect();
            el.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2, pointerType: 'mouse' }));
            await new Promise(res => requestAnimationFrame(res));
            const id = el.dataset.grId;
            const rel = Array.from(svg.querySelectorAll('.gr-l-hot .gr-e-rel'));
            if (rel.some(l => l.dataset.grS !== id && l.dataset.grT !== id)) {
              // 5.3 표의 '근거 2단계 경로'는 ours-wide, ours-part 64행의 수. peer-rel 은 따로 적는다
              if (/ours-wide|ours-part/.test(el.dataset.grMark)) { two++; names.push(el.dataset.tipTitle); } else { twoPeer++; peerNames.push(el.dataset.tipTitle); }
            }
          }
          document.body.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, clientX: 2, clientY: 2, pointerType: 'mouse' }));
          return { marked: els.length, two_step: two, names, two_step_peer_rel: twoPeer, peer_rel_names: peerNames };
        }""")
    out['evidence_two_step'] = ev
    return out



# ---------------------------------------------------------------- 5, 6단계: 종형 구성(6절)과 시장 동향(7절), 12절 1, 14, 15, 22번
ALT_JS = r"""
() => {
  const svg = document.querySelector('#gr-vt-svg, #gr-mk-svg');
  if (!svg) return null;
  const tr = el => { const m = /translate\(([-\d.]+)[ ,]+([-\d.]+)\)/.exec(el.getAttribute('transform') || ''); return m ? [+m[1], +m[2]] : [0, 0]; };
  const nodes = Array.from(svg.querySelectorAll('.gr-l-nodes > .gr-v')).map(el => { const [x, y] = tr(el); return { id: el.dataset.grId, kind: el.dataset.grKind, x, y, r: +el.dataset.grR, org: el.dataset.grOrg || '', state: el.dataset.grState || '' }; });
  const edges = [];
  svg.querySelectorAll('.gr-l-edges .gr-e').forEach(el => {
    let pts;
    if (el.tagName === 'line') pts = [[+el.getAttribute('x1'), +el.getAttribute('y1')], [+el.getAttribute('x2'), +el.getAttribute('y2')]];
    else {
      const v = (el.getAttribute('d') || '').match(/-?[\d.]+/g).map(Number);
      const [x0, y0, cx, cy, x1, y1] = v; pts = [];
      for (let i = 0; i <= 16; i++) { const u = i / 16; pts.push([(1 - u) * (1 - u) * x0 + 2 * (1 - u) * u * cx + u * u * x1, (1 - u) * (1 - u) * y0 + 2 * (1 - u) * u * cy + u * u * y1]); }
    }
    edges.push({ s: el.dataset.grS, t: el.dataset.grT, k: el.dataset.grEkind, pts, quad: el.tagName !== 'line', d: el.getAttribute('d') || '' });
  });
  const labels = Array.from(svg.querySelectorAll('.gr-l-labels [data-gr-lbox]')).map(el => {
    const bb = el.getBBox();
    return { type: el.dataset.grLb, for: el.dataset.grFor || '', box: el.dataset.grLbox.split(',').map(Number), bbox: [bb.x, bb.y, bb.x + bb.width, bb.y + bb.height],
      text: el.textContent, body: (el.querySelector('.gr-vlb-b') || {}).textContent || '', suffix: ((el.querySelector('.gr-vlb-rn') || {}).textContent || '').trim(),
      font: parseFloat(getComputedStyle(el).fontSize), more: el.dataset.grMore != null ? +el.dataset.grMore : null };
  });
  const bx = svg.querySelector('.gr-vbox');
  let box = null, unmapped = null, varId = '';
  if (bx) { const [x, y] = tr(bx); const r = bx.querySelector('rect'); box = [x + +r.getAttribute('x'), y + +r.getAttribute('y'), x + +r.getAttribute('x') + +r.getAttribute('width'), y + +r.getAttribute('y') + +r.getAttribute('height')]; unmapped = bx.dataset.grUnmapped != null ? +bx.dataset.grUnmapped : null; varId = bx.dataset.grId; }
  const host = svg.parentElement;
  return { view: svg.id, W: +svg.getAttribute('width'), H: +svg.getAttribute('height'), hostH: host.clientHeight, hscroll: host.scrollWidth - host.clientWidth,
    nodes, edges, labels, box, unmapped, varId };
}
"""

# 원자료(graph.json)에서 따로 세는 기대값: 종형의 특약, 급부, 매핑된 급부, 특약 갱신여부
VT_EXPECT_JS = r"""
(vid) => {
  const raw = JSON.parse(document.getElementById('graph-data').textContent);
  const NK = Object.fromEntries(raw.kinds.map((n, i) => [n, i])), EK = Object.fromEntries(raw.ekinds.map((n, i) => [n, i]));
  const keys = raw.keys;
  const prop = (n, k) => { const p = n[4] || {}; const j = keys.indexOf(k); return p[j]; };
  const E = raw.edges.concat(raw.edges2 || []);
  const vi = raw.nodes.findIndex(n => n[0] === vid);
  const riders = E.filter(e => e[2] === EK['포함'] && e[0] === vi && raw.nodes[e[1]][1] === NK['특약']).map(e => e[1]);
  const rs = new Set(riders);
  const bens = Array.from(new Set(E.filter(e => e[2] === EK['포함'] && rs.has(e[0]) && raw.nodes[e[1]][1] === NK['급부']).map(e => e[1])));
  const mapped = new Set(E.filter(e => e[2] === EK['매핑'] && raw.nodes[e[0]][1] === NK['급부']).map(e => e[0]));
  const renew = {};
  riders.forEach(r => { renew[raw.nodes[r][0]] = prop(raw.nodes[r], '갱신여부') || ''; });
  const vs = raw.summary && raw.summary['종형'] && raw.summary['종형'][vid];
  return { riders: riders.map(r => raw.nodes[r][0]), bens: bens.map(b => raw.nodes[b][0]), mappedBens: bens.filter(b => mapped.has(b)).map(b => raw.nodes[b][0]),
    unmappedBens: bens.filter(b => !mapped.has(b)).length, summaryUnmapped: vs ? vs['미연결급부'] : null, renew };
}
"""

MK_EXPECT_JS = r"""
() => {
  const raw = JSON.parse(document.getElementById('graph-data').textContent);
  const NK = Object.fromEntries(raw.kinds.map((n, i) => [n, i]));
  const keys = raw.keys;
  const prop = (n, k) => { const p = n[4] || {}; return p[keys.indexOf(k)]; };
  const news = raw.nodes.filter(n => n[1] === NK['시장 동향']);
  return { sales: (App.S['시장소식']['소식'] || []).map(x => x['동향ID']), passed: news.filter(n => prop(n, '선별상태') === 'passed').length, all: news.length,
    below: news.filter(n => prop(n, '선별상태') === 'below').map(n => [n[0], prop(n, '판정확률')]) };
}
"""

RENEW_NAME = {'갱신': '(갱신형)', '비갱신': '(비갱신형)'}


def alt_layout(sc):
    nodes, edges, labels = sc['nodes'], sc['edges'], sc['labels']
    ov = 0
    for a, b in itertools.combinations(nodes, 2):
        if math.hypot(a['x'] - b['x'], a['y'] - b['y']) < a['r'] + b['r'] - 0.01:
            ov += 1
    box_ov = sum(1 for n in nodes if sc['box'] and rect_circle(sc['box'], n['x'], n['y'], n['r']))
    cross = 0
    for a, b in itertools.combinations(edges, 2):
        if {a['s'], a['t']} & {b['s'], b['t']}:
            continue
        for i in range(len(a['pts']) - 1):
            hit = False
            for j in range(len(b['pts']) - 1):
                if seg_cross((*a['pts'][i], *a['pts'][i + 1]), (*b['pts'][j], *b['pts'][j + 1])):
                    cross += 1
                    hit = True
                    break
            if hit:
                break
    lb = [x for x in labels]
    lab_ov = sum(1 for a, b in itertools.combinations(lb, 2) if rect_overlap(a['box'], b['box']))
    lab_node = sum(1 for a in lb for n in nodes if a['for'] != n['id'] and rect_circle(a['box'], n['x'], n['y'], n['r']))
    lab_box = sum(1 for a in lb if sc['box'] and rect_overlap(a['box'], sc['box']))
    lab_out = sum(1 for a in lb if a['box'][0] < 0 or a['box'][1] < 0 or a['box'][2] > sc['W'] or a['box'][3] > sc['H'])
    bbox_out = sum(1 for a in lb if a['bbox'][2] > a['box'][2] + 1.5 or a['bbox'][0] < a['box'][0] - 1.5)
    orth = sum(1 for e in edges if e['quad'] and not re.fullmatch(r'M[-\d.]+,[-\d.]+ Q[-\d.]+,[-\d.]+ [-\d.]+,[-\d.]+', e['d']))
    node_out = sum(1 for n in nodes if n['x'] - n['r'] < 0 or n['y'] - n['r'] < 0 or n['x'] + n['r'] > sc['W'] or n['y'] + n['r'] > sc['H'])
    return {'nodes': len(nodes), 'edges': len(edges), 'node_overlap': ov, 'node_box_overlap': box_ov, 'crossings': cross,
            'label_overlap': lab_ov, 'label_node_overlap': lab_node, 'label_box_overlap': lab_box, 'label_outside': lab_out,
            'label_text_wider_than_box': bbox_out, 'label_font_min': min([a['font'] for a in lb] or [13]), 'orthogonal_edges': orth,
            'node_outside': node_out, 'hscroll': sc['hscroll']}


def vt_check(sc, exp):
    ids = {n['id'] for n in sc['nodes']}
    shown_r = [r for r in exp['riders'] if r in ids]
    shown_b = [b for b in exp['bens'] if b in ids]
    badge = sum(l['more'] or 0 for l in sc['labels'] if l['type'] == 'badge')
    hidden_mapped = len([b for b in exp['mappedBens'] if b not in ids])
    rl = [l for l in sc['labels'] if l['type'] == 'rider']
    renew_bad = [l['for'] for l in rl if l['suffix'] != RENEW_NAME.get(exp['renew'].get(l['for'], ''), '') or not l['text'].endswith(l['suffix'])]
    return {'riders': f"{len(shown_r)}/{len(exp['riders'])}", 'bens': f"{len(shown_b)}/{len(exp['bens'])}",
            'riders_all_shown': len(shown_r) == len(exp['riders']), 'bens_all_shown': len(shown_b) == len(exp['bens']),
            'badge_sum': badge, 'hidden_mapped_bens': hidden_mapped, 'badge_ok': badge == hidden_mapped,
            'box_unmapped': sc['unmapped'], 'raw_unmapped_bens': exp['unmappedBens'], 'summary_unmapped': exp['summaryUnmapped'],
            'unmapped_ok': sc['unmapped'] == exp['unmappedBens'], 'rider_labels': len(rl), 'rider_label_renew_bad': renew_bad,
            'extra_kinds': sorted({n['kind'] for n in sc['nodes']} - {'특약', '급부', '표준담보'})}


async def wait_alt(pg, sel):
    await pg.wait_for_function(f"() => !!document.querySelector('{sel}')", timeout=8000)
    await pg.wait_for_timeout(250)
    await pg.wait_for_function("() => !document.querySelector('.gr-l-ghost > *')", timeout=8000)
    await pg.wait_for_timeout(250)


async def open_node(pg, node_id):
    await pg.evaluate("(id) => { const raw = JSON.parse(document.getElementById('graph-data').textContent); const i = raw.nodes.findIndex(n => n[0] === id); const b = document.createElement('button'); b.dataset.grSelIdx = String(i); document.getElementById('z-left').appendChild(b); b.click(); b.remove(); }", node_id)


def static_check():
    src = (ROOT / 'proto_src/console4/tab6.js').read_text(encoding='utf-8')
    gone = ['COL_KINDS', 'COL_OF_KIND', 'drawOrthogonalEdges', 'columnCountText', 'renderVariantRiderColHTML', 'expandDomainStep', 'expandStdStep',
            'neighborGroupsOf', 'expandNeighborGroup', 'syncVariantDownstream', 'varStdPaths', 'varDomStds', 'matchedVariants', 'stdOwnershipClass',
            'buildCoverStdColumns', 'RIDER_GRP_ORDER', 'riderGroupRank', 'lineStyleLabel', 'state.cols', 'batches', 'varLimits', 'varMores']
    css = (ROOT / 'proto_src/console4/tab6.css').read_text(encoding='utf-8')
    return {'kind_number_compare': re.findall(r'\.k\s*===\s*\d|\bek:\s*\d|\.ek\s*===\s*\d', src), 'math_random': src.count('Math.random'),
            'removed_names_left': [n for n in gone if re.search(r'\b' + re.escape(n) + r'\b', src)],
            'css_left': [s for s in ['.gr-col-bar', '.gr-cols-grid', '.gr-col{', '.gr-c-', '.gr-node', '.gr-vpath'] if s in css]}


async def alt_checks(pg, b1):
    out = {}
    names = await pg.evaluate("() => { const raw = JSON.parse(document.getElementById('graph-data').textContent); return raw.nodes.filter(n => n[2].includes('간편가입형(1년)') && n[3] === 'HANWHALIFE').map(n => n[0]); }")
    # 앞 측정의 Esc 로 다른 탭에 가 있을 수 있으므로 관계 그래프 탭으로 돌아온다
    await pg.evaluate("() => { if (App.state.tab !== 'graph') App.go('graph'); }")
    await pg.wait_for_timeout(600)
    await set_cond(pg, b1, 'all')
    await pg.evaluate("(s) => document.querySelector(s).click()", '[data-gr-preset="cover"]')
    await wait_alt(pg, '#gr-net-svg')
    out['org_code_text_cover'] = await pg.evaluate(ORG_TEXT_JS)
    # 14번: 종형 구성
    await pg.evaluate("(s) => document.querySelector(s).click()", '[data-gr-preset="variant"]')
    await wait_alt(pg, '#gr-vt-svg')
    for vid in [b1] + names[:1]:
        if vid != b1:
            await open_node(pg, vid)
            await wait_alt(pg, '#gr-vt-svg')
        sc = await pg.evaluate(ALT_JS)
        exp = await pg.evaluate(VT_EXPECT_JS, vid)
        out[f'variant|{vid}'] = {'layout': alt_layout(sc), 'data': vt_check(sc, exp), 'org_code_text': await pg.evaluate(ORG_TEXT_JS)}
    # 15번: 시장 동향
    await pg.evaluate("(s) => document.querySelector(s).click()", '[data-gr-preset="news"]')
    await wait_alt(pg, '#gr-mk-svg')
    mexp = await pg.evaluate(MK_EXPECT_JS)
    mk = {}
    for f in ['week', 'allweek', 'all']:
        await pg.evaluate("(s) => document.querySelector(s).click()", f'[data-gr-nf="{f}"]')
        await wait_alt(pg, '#gr-mk-svg')
        sc = await pg.evaluate(ALT_JS)
        news = [n for n in sc['nodes'] if n['kind'] == '시장 동향']
        orgs = {n['id'] for n in sc['nodes'] if n['kind'] == '회사'}
        nmap = {n['id']: n for n in news}
        cross_group = sum(1 for e in sc['edges'] if not (e['t'] in nmap and nmap[e['t']]['org'] == e['s']))
        btn = await pg.evaluate(f"() => +document.querySelector('[data-gr-nf=\"{f}\"] .num').textContent.replace(/,/g, '')")
        mk[f] = {'layout': alt_layout(sc), 'news': len(news), 'button_count': btn, 'orgs': len(orgs),
                 'var_or_std_nodes': sum(1 for n in sc['nodes'] if n['kind'] in ('종형', '표준담보')), 'edges_between_groups': cross_group,
                 'below_shown': [n['id'] for n in news if n['state'] == 'below'], 'svg_h': sc['H'], 'host_h': sc['hostH']}
        if f == 'week':
            mk[f]['same_as_sales'] = sorted(n['id'] for n in news) == sorted(mexp['sales'])
            mk[f]['org_code_text'] = await pg.evaluate(ORG_TEXT_JS)
    mk['expect'] = {'sales': len(mexp['sales']), 'passed': mexp['passed'], 'all': mexp['all'], 'below': mexp['below']}
    out['news'] = mk
    await pg.evaluate("(s) => document.querySelector(s).click()", '[data-gr-preset="cover"]')
    await wait_alt(pg, '#gr-net-svg')
    return out


def alt_fails(a):
    f = []
    for k, v in a.items():
        if not k.startswith('variant|'):
            continue
        L, D = v['layout'], v['data']
        one = k.endswith('_8dba92') or D['riders_all_shown'] and D['bens_all_shown']
        lim = 25 if one else 70
        if L['node_overlap'] or L['node_box_overlap']: f.append(k + ':overlap')
        if L['crossings'] > lim: f.append(k + f":crossings>{lim}")
        if L['label_overlap'] or L['label_node_overlap'] or L['label_box_overlap'] or L['label_outside'] or L['label_font_min'] < 13: f.append(k + ':labels')
        if L['orthogonal_edges'] or L['node_outside'] or L['hscroll'] > 0: f.append(k + ':layout')
        if not D['badge_ok'] or not D['unmapped_ok'] or D['rider_label_renew_bad'] or D['extra_kinds']: f.append(k + ':data')
        if v['org_code_text']: f.append(k + ':org_code')
    n = a.get('news', {})
    e = n.get('expect', {})
    for fk, want in (('week', e.get('sales')), ('allweek', e.get('passed')), ('all', e.get('all'))):
        m = n.get(fk)
        if not m:
            f.append('news:' + fk)
            continue
        L = m['layout']
        if m['news'] != want or m['button_count'] != want or m['var_or_std_nodes'] or m['edges_between_groups']: f.append('news:' + fk + ':data')
        if L['node_overlap'] or L['label_overlap'] or L['label_node_overlap'] or L['label_font_min'] < 13 or L['hscroll'] > 0: f.append('news:' + fk + ':layout')
    if n.get('week') and (not n['week'].get('same_as_sales') or n['week'].get('org_code_text')): f.append('news:week:sales_or_org_code')
    if n.get('all') and sorted(n['all']['below_shown']) != sorted(x[0] for x in e.get('below', [])): f.append('news:all:below')
    if a.get('org_code_text_cover'): f.append('cover:org_code')
    st = a.get('static', {})
    if st.get('kind_number_compare') or st.get('math_random') or st.get('removed_names_left') or st.get('css_left'): f.append('static')
    return f

async def set_cond(pg, base, scope):
    await pg.evaluate("(a) => App.set({ base: a[0], peerScope: a[1] })", [base, scope])
    await pg.wait_for_timeout(250)
    await pg.wait_for_function("() => !!document.getElementById('gr-net-svg')", timeout=8000)
    # 위치 트랜지션(4.9)이 끝나 사라지는 노드가 빠지고 새 라벨이 나타날 때까지 기다린다
    await pg.wait_for_function("() => !document.querySelector('#gr-net-svg .gr-l-ghost > *')", timeout=8000)
    await pg.wait_for_timeout(250)


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
            st4 = None
            if not args.no_stage4:
                await pg.keyboard.press('Escape')
                await pg.wait_for_timeout(300)
                st4 = await stage4(pg, bases, names) if (vw, vh) == sizes[0] else {'selection': await stage4_sel(pg, bases, names)}
            await pg.keyboard.press('Escape')
            await pg.wait_for_timeout(300)
            if (vw, vh) == sizes[0] and not args.no_alt:
                try:
                    alt = await alt_checks(pg, base_ids(bases, names)[0])
                except Exception as ex:  # 측정이 멈추면 그때의 콘솔 오류와 화면 상태를 남긴다
                    alt = {'error': str(ex)[:300], 'console_errors_so_far': errs[:10],
                           'state': await pg.evaluate("() => [document.querySelector('[data-gr-preset].is-on')?.dataset.grPreset, !!document.getElementById('gr-vt-svg'), !!document.getElementById('gr-net-svg'), document.querySelector('#gr-net')?.clientWidth, document.querySelector('#gr-net')?.clientHeight, (document.querySelector('#z-center')||{}).innerHTML?.slice(0, 200)]")}
                alt['static'] = static_check()
                result['alt'] = alt
            # 세 보기 측정은 4단계, 5, 6단계 측정이 끝난 뒤에 한다(보기를 오가면 담보별 연결의 배치 캐시와 선택 상태가 바뀌므로)
            if args.org_views and (vw, vh) == sizes[0]:
                # 22번: 세 보기(담보별 연결, 종형 구성, 시장 동향)의 기관코드 글자. 다른 자료(3개사, 가상 20개사)에서도 잰다
                views = {'cover': org_hits}
                # 앞 측정의 Esc 로 다른 탭에 가 있을 수 있으므로 관계 그래프 탭으로 돌아온다(alt_checks 와 같은 방식)
                await pg.evaluate("() => { if (App.state.tab !== 'graph') App.go('graph'); }")
                await pg.wait_for_timeout(600)
                await set_cond(pg, bases[0], 'all')
                for pre, sel_ in (('variant', '#gr-vt-svg'), ('news', '#gr-mk-svg')):
                    await pg.evaluate("(s) => document.querySelector(s).click()", f'[data-gr-preset="{pre}"]')
                    await wait_alt(pg, sel_)
                    views[pre] = await pg.evaluate(ORG_TEXT_JS)
                    if pre == 'news':
                        await pg.evaluate("(s) => document.querySelector(s).click()", '[data-gr-nf="all"]')
                        await wait_alt(pg, sel_)
                        views['news_all'] = await pg.evaluate(ORG_TEXT_JS)
                await pg.evaluate("(s) => document.querySelector(s).click()", '[data-gr-preset="cover"]')
                await wait_alt(pg, '#gr-net-svg')
                org_hits = views
            hscroll = await pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
            math_random = await pg.evaluate("() => (document.documentElement.outerHTML.match(/Math\\.random/g) || []).length")
            result['sizes'][f'{vw}x{vh}'] = {'states': per, 'determinism': det, 'selection': sel, 'org_code_text': org_hits,
                                             'console_errors': errs, 'external_requests': ext, 'hscroll': hscroll,
                                             'math_random_in_html': math_random, 'stage4': st4}
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
    for size, r in result['sizes'].items():
        st4 = r.get('stage4')
        if not st4:
            continue
        f4 = []
        s1, s2, s3 = (st4['selection'].get(k, {}) for k in ('암 수술비', '일반암 진단비', '종별 수술비(최고 종 기준)'))
        for nm, sv, lim in (('surgery', s1, 2), ('general', s2, 1), ('type_surgery', s3, 2)):
            if not sv.get('sum_expect') or sv.get('sum_nodes') != sv.get('sum_expect') or sv.get('sum_label_missing') or sv.get('sum_mismatch') or sv.get('exp_other_kinds'):
                f4.append('summary_' + nm)
            # 교차 상한(암 수술비 2, 일반암 진단비 1)은 1920x1080 기준. 다른 해상도는 값만 적는다
            first = size == next(iter(result['sizes']))
            if not sv.get('clicked') or sv['max_move'] > 0.5 or sv['area_change'] != [0, 0] or sv['exp_overlap'] or (first and sv['exp_crossings'] > lim) or not sv['attrs_ok'] or sv['exp_node_label_overlap'] or sv['exp_label_overlap']:
                f4.append('selection_' + nm)
        cm = st4.get('cond_move')
        if cm and (cm['max_123_all_nodes'] > 0.5 or cm['mean_3_4_all_nodes'] > 4 or cm['mean_4_unified_same_group'] > 20):
            f4.append('cond_move')
        # 13번의 넷째 기준은 다섯 종형의 모든 조합의 평균 8px 이하로 읽는다(같은 절의 4종과 통합 20px, 계산값 10.8px 와 맞추려면).
        # 조합별 최댓값(max_pair_same_group_mean)은 참고값으로 함께 적는다
        if cm and cm['mean_all_pairs_same_group'] > 8:
            f4.append('cond_move_all_pairs_8px')
        for k, v in st4.get('transition', {}).items():
            if not v.get('moving_nodes'):
                f4.append('transition_none:' + k)
                continue
            if k.startswith('on|') and (v['max_step_ratio'] > 0.12 or v['max_prog100'] > 0.5 or v['max_path_ratio'] > 1.05 or v['one_frame_moves']):
                f4.append('transition:' + k)
            if k.startswith('calm|') and (v['max_step_ratio'] > 0.20 or v['max_path_ratio'] > 1.05 or v['one_frame_moves']):
                f4.append('transition:' + k)
            if k.startswith('off|') and v['one_frame_moves'] != v['moving_nodes']:
                f4.append('transition:' + k)
        for nm, v in st4.get('evidence_two_step', {}).items():
            if v['two_step'] != (2 if re.search('[1-4]종', nm) else 3):
                f4.append('evidence:' + nm)
        summ[f'{size}|stage4'] = f4
    for key, fails in list(summ.items()):
        size, _, rest = key.partition('|')
        it = result['sizes'].get(size, {}).get('states', {}).get(rest)
        if it and it['layout'].get('std_label_on_bundle'):
            fails.append('std_label_on_bundle')
    if 'alt' in result:
        summ['alt'] = alt_fails(result['alt']) + (['alt_error'] if 'error' in result['alt'] else [])
    result['summary_fails'] = {k: v for k, v in summ.items() if v}
    result['summary_states'] = len(summ)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"상태 {len(summ)}개, 실패 {len(result['summary_fails'])}개 -> {args.out}")
    for k, v in result['summary_fails'].items():
        print(' ', k, v)


async def alt_run(args):
    url = Path(args.html).resolve().as_uri() + '#t=graph'
    vw, vh = [int(v) for v in args.sizes.split(',')[0].split('x')]
    async with async_playwright() as p:
        br = await p.chromium.launch()
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
        alt = await alt_checks(pg, base_ids(bases, names)[0])
        alt['static'] = static_check()
        alt['console_errors'] = errs
        alt['external_requests'] = ext
        await br.close()
    fails = alt_fails(alt) + (['console_errors'] if errs else []) + (['external_requests'] if ext else [])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({'alt': alt, 'fails': fails}, ensure_ascii=False, indent=1), encoding='utf-8')
    print('실패', fails)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--html', default=str(ROOT / 'site/proto/console4.html'))
    ap.add_argument('--sizes', default='1920x1080,1600x900,1366x768,1280x800')
    ap.add_argument('--out', default=str(ROOT / 'shots_console4/graph_check.json'))
    ap.add_argument('--no-stage4', action='store_true', help='4단계 측정(선택 펼침, 조건 이동, 트랜지션, 근거 경로)을 건너뛴다')
    ap.add_argument('--no-alt', action='store_true', help='5, 6단계 측정(종형 구성, 시장 동향)을 건너뛴다')
    ap.add_argument('--alt-only', action='store_true', help='5, 6단계 측정만 1920x1080 에서 한다')
    ap.add_argument('--org-views', action='store_true', help='첫 해상도에서 세 보기의 기관코드 글자를 잰다(12절 22번)')
    ap.add_argument('--cpu4', action='store_true', help='CPU 4배 느림에서 조건마다 레이아웃 계산 시간을 잰다')
    args = ap.parse_args()
    asyncio.run(alt_run(args) if args.alt_only else run(args))


if __name__ == '__main__':
    main()
