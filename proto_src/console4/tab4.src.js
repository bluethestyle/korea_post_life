/* 탭 4 담보 비교: 안개 위 전폭 가로 기준축(66% 지점, 치료 단계 다섯 구간) + 담보별 판정 적층 기둥 + 아래 읽기 띠.
   치료 여정 격자, 단정 주의, 보류 요약, 담보 비교표와 표 복사는 모두 [표로 보기] 전체 창에 가림 없이 싣는다.
   이 파일은 tab4.src.js 이고, tab4.js 는 gen_cover.py --assemble 이 자료 한 줄(const CV)을 앞에 붙여 만든다. */
const { ui, txt } = App;
const { esc, fmt } = ui;
const t = (k, v) => App.t(k, v);
const S = App.S;
const STEPS = (Object.values(S['기준별'] || {})[0] && Object.values(S['기준별'] || {})[0]['치료여정'] && Object.values(S['기준별'] || {})[0]['치료여정']['열']) || [];
const ROMAN = { 'Ⅰ': 'I', 'Ⅱ': 'II', 'Ⅲ': 'III', 'Ⅳ': 'IV', 'Ⅴ': 'V' };
const fixG = s => String(s == null ? '' : s).replace(/[ⅠⅡⅢⅣⅤ]/g, m => ROMAN[m]);
const nf = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 });
const N = n => nf.format(n);

ui.registerLegend('cover', 'legendVerdictTitle', () => `<p class="note" style="margin:0 0 8px">${esc(t('cvLgIntro'))}</p><dl class="legend">
    <dt>${ui.verdict('better')}</dt><dd>${esc(t('cvLgBetter'))}</dd>
    <dt>${ui.verdict('only')}</dt><dd>${esc(t('cvLgOnly'))}</dd>
    <dt><i class="cq m-both" aria-hidden="true"></i></dt><dd>${esc(t('cvLgNeutral'))}</dd>
    <dt>${ui.verdict('worse')}</dt><dd>${esc(t('cvLgWorse'))}</dd>
    <dt>${ui.verdict('unknown')}</dt><dd>${esc(t('cvLgUnknown'))}</dd>
    <dt>${ui.verdict('none')}</dt><dd>${esc(t('cvLgNone'))}</dd>
    <dt>${ui.flagText(App.t('flagShort'))}</dt><dd>${esc(App.t('lgFlag'))}</dd>
  </dl>`);

// ---------- 이름 ----------
const vinfo = v => S['종형'][v] || {};
const orgOf = v => vinfo(v)['기관코드'] || String(v).split('_')[0];
const orgN = v => txt.orgShort(orgOf(v));
const kindN = v => vinfo(v)['종형명'] || v;
const fullN = v => vinfo(v)['이름'] || v;
const std = sid => S['표준담보'][sid] || { '이름': sid };
const stdN = sid => std(sid)['이름'] || sid;
const VID_RE = /\b[A-Z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+\b/g;
const reasonText = list => [...new Set((Array.isArray(list) ? list : [list]).map(x => String(x).replace(VID_RE, m => fullN(m))))].join(', ');

// ---------- 급부와 특약(CV 의 번호) 및 금액 없는 급부 규약 ----------
function ben(i) {
  const b = CV && CV.ben[i];
  return b ? { i, name: fixG(b[0]), rid: b[1], role: b[2], pay: b[3], base: b[4], ratio: !!b[5], wait: b[6] || 0, red: b[7] || [],
    limit: b[8], exc: b[9], doc: b[10], page: b[11], state: b[12], prob: b[13], log: !!b[14], tags: b[15] } : null;
}
function rider(j) { const r = CV && CV.rid[j]; return r ? { name: fixG(r[0]), kind: r[1], max: r[2] } : null; }
function won(m) {
  if (m == null) return null;
  if (m >= 10000) { const e = Math.floor(m / 10000), r = Math.round((m - e * 10000) * 100) / 100; return r ? `${N(e)}억 ${N(r)}만원` : `${N(e)}억원`; }
  return `${N(m)}만원`;
}
const nonMonKind = b => (b && CV && CV['지급기준'] && CV['지급기준'][String(b.i)]) || null;
const nonMonWhy = kind => (kind && CV && CV['지급기준글'] && CV['지급기준글'][kind]) || '';
const nonMonCopy = key => (CV && CV['금액없음글'] && CV['금액없음글'][key]) || '';
const rateOf = b => (b.base ? b.pay * 100 / b.base : b.pay);
const payText = b => {
  if (!b) return '없음';
  const nm = nonMonKind(b);
  if (nm) return nm;
  return b.pay == null ? '자료 없음' : b.ratio ? `가입금액의 ${N(rateOf(b))}%` : won(b.pay);
};
const baseText = b => {
  if (!b) return '없음';
  if (nonMonKind(b)) return nonMonCopy('기준') || '금액 하나로 적을 수 없는 급부';
  return b.ratio ? '가입금액 대비 비율로 적힌 급부' : b.base != null ? `기준 가입금액 ${won(b.base)}일 때` : '기준 가입금액 자료 없음';
};
const waitText = w => `${N(w || 0)}일`;
const monthsText = m => (m % 12 === 0 ? `${m / 12}년` : `${m}개월`);
const redText = (red, b) => {
  if (b && nonMonKind(b)) return nonMonCopy('감액') || '원문 확인';
  return red && red.length ? red.map(([m, r]) => t('cvRedWithinTpl', { period: monthsText(m), rate: N(Math.round(r * 1000) / 10) })).join(', ') : '감액 없음';
};
const redShort = (red, b) => {
  if (b && nonMonKind(b)) return nonMonCopy('감액') || '원문 확인';
  return red && red.length ? red.map(([m, r]) => `${monthsText(m)} ${N(Math.round(r * 1000) / 10)}%`).join(', ') : '없음';
};
const tagsStr = b => {
  if (!b || !b.tags) return '';
  return Array.isArray(b.tags) ? b.tags.join(', ') : String(b.tags);
};
const formText = (b, hasAnyNonMon) => {
  if (!b) return null;
  const nm = nonMonKind(b);
  if (nm) return nm;
  const ts = tagsStr(b);
  if (hasAnyNonMon) return ts ? `정액 지급(${ts})` : '정액 지급';
  return ts || '문구 없음';
};
const has = c => !!(c && c.i && c.i.length);
const repOf = c => (has(c) ? ben(c.r != null ? c.r : c.i[0]) : null);

// ---------- 판정 모형(자료의 쌍판정과 판정표, 보류요약.기관별을 그대로 읽는다) ----------
const BOTH_NONE_TEXT = (CV && Array.isArray(CV['판정차례']) && CV['판정차례'][CV['판정차례'].length - 1]) || '둘 다 없음';
const cache = {};
const verdictName = cause => (CV && CV['판정표'] && CV['판정표'][cause] && CV['판정표'][cause]['표시명']) || App.label(cause);
function model(baseId) {
  if (cache[baseId]) return cache[baseId];
  const B = CV && CV.b[baseId];
  const base = S['기준별'][baseId];
  if (!B || !base) return null;
  const by = (list, key) => { const o = {}; (list || []).forEach(x => { const k = x[key]; if (k) (o[k] = o[k] || []).push(x); }); return o; };
  const cau = by(base['단정주의'], '표준담보ID');
  const pts = by((base['포인트'] || []).map(id => S['포인트'][id]).filter(Boolean), '표준담보ID');
  const omit = by(base['뺀포인트'], '표준담보ID');
  const rows = B.rows.map(r => {
    const row = { sid: r[0], cells: r[1], prs: r[2] || {}, major: std(r[0])['대분류'] || '', type: std(r[0])['급부유형'] || '',
      cau: cau[r[0]] || [], pts: pts[r[0]] || [], omit: omit[r[0]] || [] };
    row.verd = B.cols.slice(1).map((_, i) => verdictOf(B, row, B.cols, i + 1));
    if (row.verd.some(v => !v || v.cause !== '상대에 없음')) {
      row.verd.forEach((v, i) => { if (v && v.cause === '상대에 없음') v.text = `${orgN(B.cols[i + 1])}에 없음`; });
    }
    return row;
  });
  return (cache[baseId] = { baseId, cols: B.cols, rows, byId: Object.fromEntries(rows.map(r => [r.sid, r])), pairs: B.pairs, dropped: B.dropped });
}
function scopedPairs(baseId, pickSet) {
  return App.scopedPairs(baseId, pickSet);
}
function peerIdxOf(m, c) {
  if (!m) return [];
  const allIdx = m.cols.slice(1).map((_, i) => i);
  if (!c || c.peerScope === 'all') return allIdx;
  const pSet = new Set(c.activePeerOrgs || []);
  return allIdx.filter(i => pSet.has(orgOf(m.cols[i + 1])));
}
function verdFor(row, m, i, pIdxs) {
  const v = row.verd[i];
  if (!v || v.cause !== '상대에 없음') return v;
  const allOnly = pIdxs.length > 0 && pIdxs.every(idx => row.verd[idx] && row.verd[idx].cause === '상대에 없음');
  return Object.assign({}, v, { text: allOnly ? v.name : `${orgN(m.cols[i + 1])}에 없음` });
}
function verdictOf(B, row, cols, k) {
  const pv = B && B['쌍판정'] && B['쌍판정'][row.sid] ? B['쌍판정'][row.sid][k - 1] : null;
  if (!pv) return null;
  const cause = pv[0];
  const reasons = Array.isArray(pv[1]) ? pv[1] : [];
  const meta = (CV && CV['판정표'] && CV['판정표'][cause]) || { '판정': cause, '칩': 'unknown' };
  const peer = cols[k], po = orgN(peer);
  const q = row.prs[peer] || null;
  let why = '';
  if (cause === '단정 주의') {
    const cau = row.cau.find(x => (x['상대종형ID'] || []).includes(peer));
    const d = q && q.it ? q.it.filter(t => t[3] === '나음' || t[3] === '못함').map(t => `${t[0]} ${t[1]} 대 ${t[2]}`).join(', ') : '';
    why = cau ? `${cau['문장']}${d ? ` 대표 급부끼리 다른 항목(${d})이 있지만 우열을 판단하지 않았습니다.` : ''}` : reasonText(reasons);
  } else if (cause === '검토 대기') {
    why = reasons.length ? t('cvWhyWaitTpl', { reasons: reasonText(reasons) }) : t('cvWhyWait');
  } else if (cause === '판정 보류') {
    why = `비교 결과를 보류했습니다: ${reasons.length ? reasonText(reasons) : '사유 자료 없음'}`;
  } else if (cause === '지급 형태 다름') {
    why = t('cvWhyDiffForm');
  } else if (cause === '엇갈림') {
    why = t('cvWhyMixed');
  } else if (cause === '관계 담보로 덮음') {
    const c = row.cells[k];
    why = c && c.c ? t('cvWhyRelCoverTpl', { org: txt.josa(po, '은'), kind: c.c[0], covs: txt.josa(c.c[1].map(stdN).join(', '), '으로') }) : t('cvWhyRelCoverTplShort', { org: txt.josa(po, '은') });
  } else if (cause === '우체국에 없음') {
    const b = row.cells[0];
    const rel = b && b.c ? `우체국은 ${b.c[0]}인 ${txt.josa(b.c[1].map(stdN).join(', '), '이')} 관련 보장을 합니다` : '';
    why = rel || `${po}에는 있고 우체국에는 없는 담보입니다`;
  } else if (cause === '상대에 없음') {
    why = `${po}에는 이 담보가 없습니다`;
  }
  return { cause, name: meta['판정'], kind: meta['칩'], text: meta['판정'], reasons, why, q };
}
const chip = (v, title) => (v ? ui.verdict(v.kind, v.text || v.name, title || v.why) : `<span class="cv-both">${esc(App.label(BOTH_NONE_TEXT))}</span>`);
const chipText = v => (v ? App.label(v.text || v.name) : App.label(BOTH_NONE_TEXT));

// ---------- 두 층 담보 비교: 위 전체 띠(79개 눈금 + 거르개 셋) + 아래 고른 단계 확대 구역 ----------
const FILTERS = [
  { k: 'miss', label: t('cvFltMiss') },
  { k: 'split', label: t('cvFltSplit') },
  { k: 'only', label: t('cvFltOnly') },
];
let curStepByBase = {};
let curPageByStep = {};
let lastSyncedSelKey = '';
const activeFilters = new Set();
let stepSwitchToken = 0;
let lastStageHost = null;
let cachedHostW = 0;
let lastHotSid = '';
let userScrolledZc = false;
const SUB_NAME_MAP = {};
Object.values(S['포인트'] || {}).forEach(p => { if (p && p['세부'] && p['세부이름']) SUB_NAME_MAP[p['세부']] = p['세부이름']; });

function truncLabel(str, maxChars) {
  const s = String(str || '').trim();
  const arr = Array.from(s);
  if (arr.length <= maxChars) return s;
  return arr.slice(0, maxChars - 1).join('').trimEnd() + '…';
}

function rowStackMetrics(row, m, B, c, totPeerOrgs) {
  const sid = row.sid;
  const oursHas = has(row.cells[0]);
  const isAll = c.peerScope === 'all';
  const perCodes = (B['판정기관코드'] && B['판정기관코드'][sid]) || {};
  const perCnts = (B['판정상대수'] && B['판정상대수'][sid]) || {};
  const cntOf = vdKey => (isAll ? (perCnts[vdKey] || 0) : c.inScope(perCodes[vdKey]));
  const better = cntOf('나음');
  const same = cntOf('같음');
  const coverN = cntOf('관계 담보로 덮음');
  const diff = cntOf('엇갈림') + cntOf('단정 주의') + cntOf('지급 형태 다름') + coverN;
  const worse = cntOf('못함');
  const wait = cntOf('검토 대기') + cntOf('판정 보류');
  const miss = cntOf('우체국에 없음');
  const stackN = better + same + diff + worse + wait + miss;
  const pIdxs = peerIdxOf(m, c);
  const hasSplit = pIdxs.some(i => {
    const v = row.verd[i];
    return !!(v && ['better', 'worse', 'diff'].includes(v.kind));
  });
  const isMiss = miss > 0;
  const isOnly = oursHas && stackN === 0;
  return {
    oursHas, stackN, coverN, totPeerOrgs, better, same, diff, worse, wait, miss,
    isMiss, isOnly, hasSplit,
  };
}

function slotTipChips(row, rm, B, c, rawPeerOrgs) {
  if (rawPeerOrgs <= 0) return [];
  const vtMap = (CV && CV['판정표']) || {};
  if (rm.oursHas && rm.stackN <= 0) {
    const onlyMeta = vtMap['상대에 없음'] || { '칩': 'only', '표시명': '우체국 단독 보유' };
    return [[onlyMeta['칩'] || 'only', onlyMeta['표시명'] || onlyMeta['판정'] || '우체국 단독 보유']];
  }
  const isAll = c.peerScope === 'all';
  const perCnts = (B['판정상대수'] && B['판정상대수'][row.sid]) || {};
  const perCodes = (B['판정기관코드'] && B['판정기관코드'][row.sid]) || {};
  const grouped = new Map();
  Object.keys(vtMap).forEach(cause => {
    if (cause === '상대에 없음') return;
    const n = isAll ? (perCnts[cause] || 0) : c.inScope(perCodes[cause]);
    if (!n) return;
    const meta = vtMap[cause] || {};
    const kind = meta['칩'] || 'unknown';
    const disp = meta['표시명'] || meta['판정'] || cause;
    const key = `${kind}|${disp}`;
    grouped.set(key, { kind, disp, n: (grouped.get(key) ? grouped.get(key).n : 0) + n });
  });
  return Array.from(grouped.values()).map(it => [it.kind, `${it.disp} ${fmt(it.n)}`]);
}

function pillarSubText(rm, rawPeerOrgs) {
  if (rawPeerOrgs <= 0) return rm.oursHas ? t('cvSubOursNoPeer') : t('cvSubNoPeer');
  if (rm.oursHas) {
    if (rm.stackN <= 0) return t('cvSubOnly');
    if (rm.coverN > 0 && rm.stackN === rm.coverN) return t('cvSubRelCoverTpl', { n: fmt(rm.stackN), tot: fmt(rawPeerOrgs) });
    if (rm.coverN > 0) return t('cvSubSameOrRelTpl', { n: fmt(rm.stackN), tot: fmt(rawPeerOrgs) });
    return t('cvSubSameTpl', { n: fmt(rm.stackN), tot: fmt(rawPeerOrgs) });
  }
  if (rm.miss > 0) return t('cvSubMissTpl', { n: fmt(rm.stackN), tot: fmt(rawPeerOrgs) });
  if (rm.wait > 0) return t('cvSubWaitTpl', { n: fmt(rm.stackN), tot: fmt(rawPeerOrgs) });
  return App.label(BOTH_NONE_TEXT);
}

function matchesCoverFilter(rm) {
  if (!activeFilters.size) return true;
  if (activeFilters.has('miss') && rm.isMiss) return true;
  if (activeFilters.has('split') && rm.hasSplit) return true;
  if (activeFilters.has('only') && rm.isOnly) return true;
  return false;
}

/** 작은 눈금과 큰 기둥이 함께 쓰는 적층 도형 생성 함수(SVG 패턴 재래스터화 없이 GPU 합성 레이어로 구성) */
function stackedShapeHTML(rm, w, maxH, minH) {
  if (rm.stackN <= 0 && rm.oursHas) {
    const d = Math.max(4, Math.min(12, w - 1));
    return {
      h: d + 4,
      html: `<span class="cvs-dia-w"><i class="cvs-dia" style="width:${d}px;height:${d}px"></i></span>`,
    };
  }
  if (rm.stackN <= 0 && !rm.oursHas) {
    const h = Math.max(5, Math.round(minH * 0.75));
    return {
      h,
      html: `<span class="cvs-box is-empty"></span>`,
    };
  }
  const totH = Math.max(minH, Math.round((rm.stackN / Math.max(1, rm.totPeerOrgs)) * maxH));
  if (rm.miss === rm.stackN) {
    return {
      h: totH,
      html: `<span class="cvs-box is-miss"></span>`,
    };
  }
  const layers = [
    { v: rm.better, cls: 's-gold', goldCap: true },
    { v: rm.same + rm.diff, cls: 's-neutral' },
    { v: rm.worse, cls: 's-worse' },
    { v: rm.wait, cls: 's-hatch' },
    { v: rm.miss, cls: 's-miss' },
  ].filter(l => l.v > 0);
  let remV = layers.reduce((a, l) => a + l.v, 0) || rm.stackN;
  let remH = totH;
  const segsBottomUp = [];
  const minSeg = maxH <= 32 ? 2 : 3;
  layers.forEach((l, li) => {
    const lh = li === layers.length - 1 ? remH : Math.max(minSeg, Math.round((l.v / remV) * remH));
    const capCls = l.goldCap && w >= 10 && lh >= 5 ? ' has-cap' : '';
    segsBottomUp.push(`<i class="cvs-seg ${l.cls}${capCls}" style="height:${Math.max(1, lh)}px"></i>`);
    remV = Math.max(1, remV - l.v);
    remH = Math.max(0, remH - lh);
  });
  segsBottomUp.reverse();
  return {
    h: totH,
    html: `<span class="cvs-box is-stack${rm.oursHas ? '' : ' no-ours'}">${segsBottomUp.join('')}</span>`,
  };
}

function defaultStepFor(m, B, c) {
  let bestStep = STEPS[0], bestPairSum = -1, bestCovCnt = -1;
  STEPS.forEach(stNm => {
    const stRows = m.rows.filter(r => r.type === stNm);
    if (!stRows.length) return;
    let pairSum = 0, covCnt = 0;
    const isAll = c.peerScope === 'all';
    stRows.forEach(r => {
      const sid = r.sid;
      const pc = (B['판정기관코드'] && B['판정기관코드'][sid]) || {};
      const ps = (B['판정상대수'] && B['판정상대수'][sid]) || {};
      const w = isAll ? (ps['못함'] || 0) : c.inScope(pc['못함']);
      const miss = isAll ? (ps['우체국에 없음'] || 0) : c.inScope(pc['우체국에 없음']);
      pairSum += w + miss;
      if (w > 0 || miss > 0) covCnt++;
    });
    if (pairSum > bestPairSum || (pairSum === bestPairSum && covCnt > bestCovCnt)) {
      bestPairSum = pairSum;
      bestCovCnt = covCnt;
      bestStep = stNm;
    }
  });
  return bestStep;
}

function domainOrderOf(c) {
  const j = c.base && c.base['치료여정'];
  return (j && Array.isArray(j['행']) && j['행'].length) ? j['행'] : ['암보장', '뇌혈관보장', '심장보장', '뇌심장보장', '공통보장'];
}

function buildDomainGroups(stRows, domOrder) {
  const map = new Map();
  domOrder.forEach(d => map.set(d, []));
  stRows.forEach(r => {
    const d = r.major || '기타';
    if (!map.has(d)) map.set(d, []);
    map.get(d).push(r);
  });
  const out = [];
  for (const [dom, items] of map.entries()) {
    if (items.length) out.push({ dom, items });
  }
  return out;
}

function domMinWidth(domNm, isMobile) {
  const len = Array.from(String(domNm || '')).length;
  return Math.max(isMobile ? 48 : 56, Math.ceil(len * (isMobile ? 11.5 : 12.5) + 12));
}

function measureZoomLayout(hostEl, stRows, domOrder) {
  const vw = innerWidth;
  if (!cachedHostW && hostEl && hostEl.clientWidth > 120) cachedHostW = hostEl.clientWidth;
  const hostW = cachedHostW > 120 ? cachedHostW : Math.max(320, vw - (vw >= 1600 ? 96 : vw >= 1000 ? 64 : 32));
  const isMobile = vw < 700;
  const isSmallMob = vw < 640;
  const rulerW = isMobile ? 22 : 30;
  const rightPad = isSmallMob ? 54 : (isMobile ? 82 : 108);
  const domGap = isSmallMob ? 10 : (isMobile ? 14 : 20);
  const usableW = Math.max(150, hostW - rulerW - rightPad);
  const minPitch = 32;
  const maxPitch = isMobile ? 48 : 64;
  const maxBarH = isMobile ? 96 : (innerHeight < 840 ? 98 : innerHeight < 960 ? 112 : 156);
  const minBarH = isMobile ? 10 : 12;

  const rawGroups = buildDomainGroups(stRows, domOrder);
  const grpMinW = g => Math.max(g.items.length * minPitch, domMinWidth(g.dom, isMobile));
  const totalNeed = rawGroups.reduce((acc, g) => acc + grpMinW(g), 0) + Math.max(0, rawGroups.length - 1) * domGap;
  let pages = [];
  if (totalNeed <= usableW || stRows.length <= 1) {
    pages = [{ groups: rawGroups, count: stRows.length }];
  } else {
    const maxColsPerChunk = Math.max(3, Math.floor(usableW / minPitch));
    const chunks = [];
    rawGroups.forEach(g => {
      if (g.items.length <= maxColsPerChunk && grpMinW(g) <= usableW) {
        chunks.push({ dom: g.dom, items: g.items });
      } else {
        const parts = Math.max(2, Math.ceil(g.items.length / maxColsPerChunk));
        const per = Math.ceil(g.items.length / parts);
        for (let p = 0; p < parts; p++) {
          const sl = g.items.slice(p * per, (p + 1) * per);
          if (sl.length) chunks.push({ dom: `${g.dom} ${p + 1}/${parts}`, items: sl });
        }
      }
    });
    let cur = { groups: [], count: 0, widthUsed: 0 };
    chunks.forEach(ch => {
      const chW = grpMinW(ch);
      const addGap = cur.groups.length ? domGap : 0;
      const addW = addGap + chW;
      if (cur.groups.length && cur.widthUsed + addW > usableW) {
        pages.push(cur);
        cur = { groups: [ch], count: ch.items.length, widthUsed: chW };
      } else {
        cur.groups.push(ch);
        cur.count += ch.items.length;
        cur.widthUsed += addW;
      }
    });
    if (cur.groups.length) pages.push(cur);
  }
  return { hostW, rulerW, rightPad, domGap, usableW, minPitch, maxPitch, maxBarH, minBarH, isMobile, pages };
}

function positionOvBracket(stageEl, animate, preMetric) {
  if (!stageEl) return;
  const wrap = stageEl.querySelector('#cv-ov-segs');
  const brk = stageEl.querySelector('#cv-ov-brk');
  const activeSeg = wrap && wrap.querySelector('.cv-ov-seg.is-on');
  if (!wrap || !brk || (!activeSeg && !preMetric)) return;
  const x = preMetric ? preMetric.x : activeSeg.offsetLeft;
  const w = preMetric ? preMetric.w : Math.max(16, activeSeg.offsetWidth);
  const bl = brk.querySelector('.b-b');
  const br = brk.querySelector('.b-r');
  const prevX = brk._lastX;
  const prevW = brk._lastW;
  brk.hidden = false;
  brk.style.transform = `translate3d(${x}px,0,0)`;
  if (bl) bl.style.transform = `scaleX(${(w / 100).toFixed(4)})`;
  if (br) br.style.transform = `translate3d(${Math.max(0, w - 2)}px,0,0)`;
  if (animate && App.motionOn() && prevX != null && prevW != null && (Math.abs(prevX - x) > 1 || Math.abs(prevW - w) > 1)) {
    const dur = Math.max(100, Math.round(320 * App.motionScale()));
    const ease = 'cubic-bezier(0.65, 0, 0.35, 1)';
    if (brk._anim) brk._anim.cancel();
    brk._anim = brk.animate([{ transform: `translate3d(${prevX}px,0,0)` }, { transform: `translate3d(${x}px,0,0)` }], { duration: dur, easing: ease });
    if (bl && bl.animate) bl.animate([{ transform: `scaleX(${(prevW / 100).toFixed(4)})` }, { transform: `scaleX(${(w / 100).toFixed(4)})` }], { duration: dur, easing: ease });
    if (br && br.animate) br.animate([{ transform: `translate3d(${Math.max(0, prevW - 2)}px,0,0)` }, { transform: `translate3d(${Math.max(0, w - 2)}px,0,0)` }], { duration: dur, easing: ease });
  }
  brk._lastX = x;
  brk._lastW = w;
}

function syncCoverSelectionAndFilter(stageEl) {
  if (!stageEl) return;
  const sel = App.state.sel.cover || '';
  const selSid = sel.startsWith('s:') ? sel.slice(2) : (sel.startsWith('c:') ? sel.slice(2) : '');
  const prevTk = stageEl.querySelector('.cv-tick.is-sel');
  if (prevTk && prevTk.dataset.cvTick !== selSid) prevTk.classList.remove('is-sel');
  if (selSid) {
    const nextTk = stageEl.querySelector(`.cv-tick[data-cv-tick="${CSS.escape(selSid)}"]`);
    if (nextTk) nextTk.classList.add('is-sel');
  }
  const slots = Array.from(stageEl.querySelectorAll('.cvp-slot[data-sid]'));
  let selSlotIdx = slots.findIndex(s => s.dataset.sid === selSid);
  if (selSlotIdx < 0) selSlotIdx = 0;
  slots.forEach((sl, idx) => {
    const on = sl.dataset.sid === selSid;
    sl.classList.toggle('is-sel', on);
    if (on) sl.setAttribute('data-sel-anchor', '1');
    else sl.removeAttribute('data-sel-anchor');
    sl.setAttribute('aria-pressed', String(on));
    sl.tabIndex = idx === selSlotIdx ? 0 : -1;
  });
}

function syncCoverAimHot(aimEl) {
  const stageEl = document.getElementById('cv-pillar-stage');
  if (!stageEl) return;
  let sid = '';
  let slotEl = null;
  if (aimEl && stageEl.contains(aimEl) && aimEl.dataset.sid) {
    sid = aimEl.dataset.sid;
    slotEl = aimEl;
  }
  if (sid !== lastHotSid) {
    if (lastHotSid) {
      stageEl.querySelectorAll('.is-hot').forEach(el => el.classList.remove('is-hot'));
    }
    lastHotSid = sid;
    if (sid) {
      const tk = stageEl.querySelector(`.cv-tick[data-cv-tick="${CSS.escape(sid)}"]`);
      if (tk) tk.classList.add('is-hot');
      const sl = stageEl.querySelector(`.cvp-slot[data-sid="${CSS.escape(sid)}"]`);
      if (sl) { sl.classList.add('is-hot'); if (!slotEl) slotEl = sl; }
    }
  }
  const hair = stageEl.querySelector('#cv-hairline');
  if (hair) {
    if (slotEl) {
      const ph = parseInt(slotEl.style.getPropertyValue('--ph'), 10) || 14;
      const plotEl = stageEl.querySelector('#cv-plot-area');
      const plotH = plotEl ? (parseInt(plotEl.style.getPropertyValue('--plot-h'), 10) || 196) : 196;
      const hy = Math.max(0, plotH - ph);
      hair.style.setProperty('--hy', hy + 'px');
      hair.hidden = false;
    } else {
      hair.hidden = true;
    }
  }
}

function buildZoomedHTML(c, m, B, curStep, pageIdx, pIdxs, totPeerOrgs, rawPeerOrgs, pSet, hostEl) {
  const stRows = m.rows.filter(r => r.type === curStep);
  const domOrder = domainOrderOf(c);
  const lay = measureZoomLayout(hostEl, stRows, domOrder);
  const pCount = lay.pages.length;
  const safePage = Math.max(0, Math.min(pCount - 1, pageIdx || 0));
  curPageByStep[c.baseId + '|' + curStep] = safePage;
  const pageObj = lay.pages[safePage] || { groups: [], count: 0 };
  const gapTotal = Math.max(0, pageObj.groups.length - 1) * lay.domGap;
  // 좁은 보장 분야(1~2개 담보)가 최소 이름 폭을 차지하는 만큼을 빼고 나머지 기둥 간격을 고르게 분배한다.
  let fixedW = 0, flexCount = 0;
  pageObj.groups.forEach(g => {
    const mw = domMinWidth(g.dom, lay.isMobile);
    if (g.items.length * lay.maxPitch <= mw) fixedW += mw;
    else flexCount += g.items.length;
  });
  let rawPitch = flexCount > 0 ? Math.floor((lay.usableW - gapTotal - fixedW) / flexCount) : lay.maxPitch;
  let pitch = Math.max(lay.minPitch, Math.min(lay.maxPitch, rawPitch));
  // 검증: 혹시라도 합계 폭이 usableW 를 넘으면 한 단계 더 줄여 0px 초과도 막는다.
  const sumAtPitch = p => pageObj.groups.reduce((a, g) => a + Math.max(g.items.length * p, domMinWidth(g.dom, lay.isMobile)), 0) + gapTotal;
  while (pitch > lay.minPitch && sumAtPitch(pitch) > lay.usableW) pitch--;
  const barW = Math.max(12, Math.min(28, pitch - 12));
  const maxChars = lay.isMobile ? 10 : 14;

  let slotSeq = 0;
  let curGrpLeft = lay.rulerW;
  const groupsHTML = pageObj.groups.map(grp => {
    const grpW = Math.max(grp.items.length * pitch, domMinWidth(grp.dom, lay.isMobile));
    const slotW = grp.items.length === 1 ? grpW : pitch;
    const slotsTotalW = grp.items.length * slotW;
    const slotsOffset = curGrpLeft + (grpW - slotsTotalW) / 2;
    curGrpLeft += grpW + lay.domGap;
    const slotsHTML = grp.items.map((r, j) => {
      const idxInPage = slotSeq++;
      const bcx = slotsOffset + j * slotW + slotW / 2;
      const rm = rowStackMetrics(r, m, B, c, totPeerOrgs);
      const passFilter = matchesCoverFilter(rm);
      const pil = stackedShapeHTML(rm, barW, lay.maxBarH, lay.minBarH);
      const hasFlag = r.pts.some(p => p['원문대조'] && (c.peerScope === 'all' || (p['관련기관코드'] || []).some(o => pSet.has(o))));
      const pk = `s:${r.sid}`;
      const fullNm = stdN(r.sid);
      const shortLbl = truncLabel(fullNm, maxChars);
      const ownDesc = pillarSubText(rm, rawPeerOrgs);
      const tipChips = slotTipChips(r, rm, B, c, rawPeerOrgs);
      const tipChipsAttr = tipChips.length ? ` data-tip-chips="${esc(JSON.stringify(tipChips))}"` : '';
      const aria = `${fullNm} (${grp.dom}, ${curStep}, ${ownDesc})`;
      const isNoData = !rm.oursHas && rm.stackN <= 0;
      const layerVec = `${rm.better},${rm.same + rm.diff},${rm.worse},${rm.wait},${rm.miss}`;
      return `<button type="button" class="cvp-slot${rm.oursHas ? '' : ' is-miss'}${passFilter ? '' : ' is-filtered-out'}" style="width:${slotW}px;--bw:${barW}px;--ph:${pil.h}px;--pd:${Math.min(260, idxInPage * 11)}ms" data-bcx="${bcx.toFixed(1)}" data-bw="${barW}" data-ph="${pil.h}" data-stack-n="${rm.stackN}" data-layers="${layerVec}" data-pick="${esc(pk)}" data-sid="${esc(r.sid)}" data-toggle="1" data-aim="rect"${isNoData ? ' data-nodata="1" aria-disabled="true"' : ''} data-tip-title="${esc(fullNm)}" data-tip-sub="${esc(`${grp.dom} / ${ownDesc}`)}"${tipChipsAttr} aria-pressed="false" aria-label="${esc(aria)}">
        <span class="cvp-upper" style="height:${lay.maxBarH + 28}px">
          <span class="cvp-stem" aria-hidden="true"><i class="cvp-dia"></i></span>
          ${hasFlag ? '<i class="cvp-flg" aria-hidden="true"></i>' : ''}
          <span class="cvp-bar" data-link-pt="1" data-aim-box="1">${pil.html}</span>
        </span>
        <i class="cvp-foot-tk" aria-hidden="true"></i>
        <span class="cvp-lbl-box" aria-hidden="true"><span class="cvp-lbl">${esc(shortLbl)}</span></span>
      </button>`;
    }).join('');

    return `<div class="cv-dom-grp" style="width:${grpW}px">
      <div class="cv-dom-slots">${slotsHTML}</div>
      <div class="cv-dom-brk" aria-hidden="true"><i class="db-l"></i><span class="db-nm">${esc(grp.dom)}</span><i class="db-r"></i></div>
    </div>`;
  }).join('');

  const pagerHTML = pCount > 1
    ? `<div class="cv-pager" role="navigation" aria-label="${esc(t('cvPagerAria'))}">
        <button type="button" class="btn sm ghost" data-cv-page="${safePage - 1}"${safePage <= 0 ? ' disabled' : ''}>${ui.IC.chevL}<span>${esc(t('cvPagerPrev'))}</span></button>
        <span class="cv-page-ind num">${safePage + 1}/${pCount}</span>
        <button type="button" class="btn sm ghost" data-cv-page="${safePage + 1}"${safePage >= pCount - 1 ? ' disabled' : ''}><span>${esc(t('cvPagerNext'))}</span>${ui.IC.chevR}</button>
      </div>`
    : '';

  const stageOursCnt = stRows.filter(r => has(r.cells[0])).length;
  const stageFilteredCnt = activeFilters.size
    ? stRows.filter(r => matchesCoverFilter(rowStackMetrics(r, m, B, c, totPeerOrgs))).length
    : stRows.length;
  const subInfo = activeFilters.size
    ? t('cvFltPassTpl', { n: fmt(stageFilteredCnt), tot: fmt(stRows.length) })
    : t('cvOursHoldTpl', { n: fmt(stageOursCnt), tot: fmt(stRows.length) });

  return `<div class="cv-zoom-head">
      <div class="cv-zh-l">
        <span class="cv-zh-step">${esc(t('cvStepDetailTpl', { step: curStep }))}</span>
        <span class="cv-zh-sub num">${esc(subInfo)}</span>
      </div>
      ${pagerHTML}
    </div>
    <div class="cv-plot-wrap" id="cv-plot-area" style="--plot-h:${lay.maxBarH + 26}px;--lbl-h:${lay.isMobile ? 104 : (innerHeight < 960 ? 106 : 116)}px;--ruler-w:${lay.rulerW}px;--rpad:${lay.rightPad}px">
      <div class="ax-ruler cv-ruler" style="height:${lay.maxBarH}px;top:26px" aria-hidden="true"><span>100</span><span>50</span><span>0</span></div>
      <div class="ax-hairline" id="cv-hairline" hidden aria-hidden="true"></div>
      <div class="cv-stage-axis" data-main-axis="1" style="top:${lay.maxBarH + 26}px" aria-hidden="true"></div>
      <div class="cv-dom-row" id="cv-zoom-axis" data-scrub-row="1" style="gap:${lay.domGap}px">${groupsHTML}</div>
    </div>`;
}

function captureSinkGhostHTML(zoomBox) {
  const plot = zoomBox && zoomBox.querySelector('#cv-plot-area');
  if (!plot) return '';
  const slots = plot.querySelectorAll('.cvp-slot[data-bcx]');
  const parts = [];
  slots.forEach(sl => {
    const bar = sl.querySelector('.cvp-bar');
    if (!bar) return;
    const bcx = parseFloat(sl.dataset.bcx) || 0;
    const bw = parseFloat(sl.dataset.bw) || 18;
    const ph = parseFloat(sl.dataset.ph) || 14;
    if (bw < 2 || ph < 2) return;
    const x = (bcx - bw / 2).toFixed(1);
    parts.push(`<span class="cv-ghost-bar" style="left:${x}px;width:${bw.toFixed(1)}px;height:${ph.toFixed(1)}px">${bar.innerHTML}</span>`);
  });
  return parts.join('');
}

function animateZoomBarsFromTicks(stageEl, baseDelayMs = 0, prePlotRect = null, preTickMap = null) {
  if (!stageEl || !App.motionOn()) return;
  const plot = stageEl.querySelector('#cv-plot-area');
  const slots = Array.from(stageEl.querySelectorAll('.cvp-slot[data-sid]'));
  if (!plot || !slots.length) return;
  const mScale = App.motionScale();
  const pRect = prePlotRect || plot.getBoundingClientRect();
  const axisY = pRect.top + (parseFloat(plot.style.getPropertyValue('--plot-h')) || 196);

  slots.forEach((sl, idx) => {
    const sid = sl.dataset.sid;
    const bar = sl.querySelector('.cvp-bar');
    if (!bar || typeof bar.animate !== 'function') return;
    const bcx = parseFloat(sl.dataset.bcx) || 32;
    const bw = parseFloat(sl.dataset.bw) || 18;
    const ph = parseFloat(sl.dataset.ph) || 14;
    const bCx = pRect.left + bcx;
    const bCy = axisY - ph / 2;
    const tRect = preTickMap ? preTickMap.get(sid) : null;
    const dly = Math.round((baseDelayMs + Math.min(100, idx * 5)) * mScale);
    if (tRect && tRect.width >= 1 && tRect.height >= 1) {
      const dx = (tRect.left + tRect.width / 2) - bCx;
      const dy = (tRect.top + tRect.height / 2) - bCy;
      const sx = Math.max(0.15, Math.min(1, tRect.width / bw));
      const sy = Math.max(0.12, Math.min(1, tRect.height / ph));
      bar.animate([
        { transform: `translate3d(${dx.toFixed(1)}px,${dy.toFixed(1)}px,0) scale(${sx.toFixed(3)},${sy.toFixed(3)})`, opacity: baseDelayMs ? 0 : 0.55 },
        { transform: 'translate3d(0,0,0) scale(1,1)', opacity: 1 },
      ], {
        duration: Math.max(100, Math.round(290 * mScale)),
        delay: dly,
        easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
        fill: 'backwards',
      });
    } else {
      bar.animate([
        { transform: 'scaleY(0.08)', opacity: baseDelayMs ? 0 : 0.25 },
        { transform: 'scaleY(1)', opacity: 1 },
      ], {
        duration: Math.max(90, Math.round(270 * mScale)),
        delay: dly,
        easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
        fill: 'backwards',
      });
    }
  });
}

function scrollSelectedBarIntoCenter() {
  if (App.state.tab !== 'cover' || innerWidth < 1000) return;
  const zc = document.getElementById('z-center');
  if (!zc) return;
  if (!zc._cvUserScrollBound) {
    zc._cvUserScrollBound = true;
    const mark = () => { if (App.state.tab === 'cover') userScrolledZc = true; };
    zc.addEventListener('wheel', mark, { passive: true });
    zc.addEventListener('touchmove', mark, { passive: true });
  }
  if (!App.state.sel.cover) {
    if (!userScrolledZc && zc.scrollTop > 0) zc.scrollTop = 0;
    if (App.syncZcScrollCue) App.syncZcScrollCue();
    return;
  }
  if (userScrolledZc) {
    if (App.syncZcScrollCue) App.syncZcScrollCue();
    App.updateSelLink(false);
    return;
  }
  const selSlot = zc.querySelector('.cvp-slot.is-sel');
  if (selSlot && zc.scrollHeight > zc.clientHeight + 1) {
    const zcRect = zc.getBoundingClientRect();
    const barEl = selSlot.querySelector('.cvp-bar') || selSlot;
    const bRect = barEl.getBoundingClientRect();
    if (bRect.bottom > zcRect.bottom - 10) {
      const need = bRect.bottom - (zcRect.bottom - 10);
      const maxUp = Math.max(0, bRect.top - (zcRect.top + 6));
      const delta = maxUp > 0 ? Math.min(need, maxUp) : need;
      zc.scrollTop = Math.min(zc.scrollHeight - zc.clientHeight, Math.round(zc.scrollTop + delta));
    } else if (bRect.top < zcRect.top + 6) {
      zc.scrollTop = Math.max(0, Math.round(zc.scrollTop - ((zcRect.top + 6) - bRect.top)));
    }
  }
  if (App.syncZcScrollCue) App.syncZcScrollCue();
  App.updateSelLink(false);
}

function switchCoverStep(nextStep, opts = {}) {
  const c = App.ctx();
  const m = model(c.baseId);
  const B = CV && CV.b[c.baseId];
  const stageEl = document.getElementById('cv-pillar-stage');
  if (!m || !B || !stageEl || !STEPS.includes(nextStep)) return;
  const prevStep = curStepByBase[c.baseId];
  curStepByBase[c.baseId] = nextStep;
  if (opts.page != null) curPageByStep[c.baseId + '|' + nextStep] = opts.page;

  const zoomBox = stageEl.querySelector('#cv-zoom-box');
  if (!zoomBox) return;

  const nextSegEl = stageEl.querySelector(`.cv-ov-seg[data-cv-step="${CSS.escape(nextStep)}"]`);
  const preSegMetric = nextSegEl ? { x: nextSegEl.offsetLeft, w: Math.max(16, nextSegEl.offsetWidth) } : null;
  const oldPlot = zoomBox.querySelector('#cv-plot-area');
  const prePlotRect = oldPlot ? oldPlot.getBoundingClientRect() : null;
  const canSink = opts.animate !== false && App.motionOn() && prevStep && prevStep !== nextStep;
  const ghostBarsHTML = canSink ? captureSinkGhostHTML(zoomBox) : '';
  const preTickMap = new Map();
  if (opts.animate !== false && App.motionOn() && nextSegEl) {
    nextSegEl.querySelectorAll('.cv-tick[data-cv-tick]').forEach(tk => {
      preTickMap.set(tk.dataset.cvTick, tk.getBoundingClientRect());
    });
  }

  stageEl.querySelectorAll('.cv-ov-seg[data-cv-step]').forEach(seg => {
    const on = seg === nextSegEl;
    seg.classList.toggle('is-on', on);
    seg.setAttribute('aria-pressed', String(on));
  });
  positionOvBracket(stageEl, opts.animate !== false, preSegMetric);

  const pIdxs = peerIdxOf(m, c);
  const rawPeerOrgs = new Set(pIdxs.map(i => orgOf(m.cols[i + 1]))).size;
  const totPeerOrgs = Math.max(1, rawPeerOrgs);
  const pSet = new Set(c.activePeerOrgs || []);

  stepSwitchToken++;
  const pg = curPageByStep[c.baseId + '|' + nextStep] || 0;
  zoomBox.innerHTML = buildZoomedHTML(c, m, B, nextStep, pg, pIdxs, totPeerOrgs, rawPeerOrgs, pSet, stageEl);
  syncCoverSelectionAndFilter(stageEl);

  if (opts.animate !== false && App.motionOn()) {
    let ghostEl = null;
    if (ghostBarsHTML) {
      const plot = zoomBox.querySelector('#cv-plot-area');
      if (plot) {
        ghostEl = document.createElement('div');
        ghostEl.className = 'cv-sink-ghost';
        ghostEl.setAttribute('aria-hidden', 'true');
        ghostEl.innerHTML = ghostBarsHTML;
        plot.appendChild(ghostEl);
      }
    }
    animateZoomBarsFromTicks(stageEl, ghostEl ? 105 : 0, prePlotRect, preTickMap);
    if (ghostEl && typeof ghostEl.animate === 'function') {
      const sinkDur = Math.max(70, Math.round(160 * App.motionScale()));
      const gAnim = ghostEl.animate([
        { transform: 'scaleY(1)', opacity: 0.92 },
        { transform: 'scaleY(0.03)', opacity: 0 },
      ], {
        duration: sinkDur,
        easing: 'cubic-bezier(0.7, 0, 0.84, 0)',
        fill: 'forwards',
      });
      gAnim.onfinish = () => { if (ghostEl.isConnected) ghostEl.remove(); };
    }
  }
  if (opts.focusEdge) {
    const slots = Array.from(zoomBox.querySelectorAll('.cvp-slot[data-sid]'));
    const target = opts.focusEdge === 'last' ? slots[slots.length - 1] : slots[0];
    if (target) {
      slots.forEach(s => { s.tabIndex = s === target ? 0 : -1; });
      try { target.focus({ preventScroll: true }); } catch (ex) { /* */ }
    }
  }
  requestAnimationFrame(() => { scrollSelectedBarIntoCenter(); App.updateSelLink(false); });
}

function ensureSidInView(sid, c) {
  const m = model(c.baseId);
  if (!m || !m.byId[sid]) return false;
  const row = m.byId[sid];
  const stNm = row.type;
  if (!STEPS.includes(stNm)) return false;
  const curStep = curStepByBase[c.baseId];
  if (curStep === stNm && document.querySelector(`#cv-zoom-box .cvp-slot[data-sid="${CSS.escape(sid)}"]`)) {
    return false;
  }
  const stageEl = document.getElementById('cv-pillar-stage');
  const stRows = m.rows.filter(r => r.type === stNm);
  const lay = measureZoomLayout(stageEl, stRows, domainOrderOf(c));
  let hitPage = 0;
  lay.pages.forEach((p, pi) => {
    if (p.groups.some(g => g.items.some(it => it.sid === sid))) hitPage = pi;
  });
  const curPage = curPageByStep[c.baseId + '|' + stNm] || 0;
  if (curStep !== stNm || curPage !== hitPage) {
    curPageByStep[c.baseId + '|' + stNm] = hitPage;
    switchCoverStep(stNm, { page: hitPage, animate: true });
    return true;
  }
  return false;
}

function renderStage(center, c) {
  lastStageHost = center;
  lastHotSid = '';
  cachedHostW = center && center.clientWidth > 120 ? center.clientWidth : 0;
  const m = model(c.baseId);
  const B = CV && CV.b[c.baseId];
  if (!m || !B) {
    center.innerHTML = `<div class="placeholder">${esc(t('cvNoDataStage'))}</div>`;
    return;
  }
  const pIdxs = peerIdxOf(m, c);
  const rawPeerOrgs = new Set(pIdxs.map(i => orgOf(m.cols[i + 1]))).size;
  const totPeerOrgs = Math.max(1, rawPeerOrgs);
  const pSet = new Set(c.activePeerOrgs || []);

  // 담보를 새로 고른 순간에만 해당 단계로 옮기고, 거르개 토글이나 창 크기 변경 때는 사람이 펼친 단계를 유지한다(2-3)
  const selRaw = c.st.sel.cover || '';
  const selSid = selRaw.startsWith('s:') ? selRaw.slice(2) : (selRaw.startsWith('c:') ? selRaw.slice(2) : '');
  const selSig = `${c.baseId}|${selRaw}`;
  if (selSig !== lastSyncedSelKey) {
    lastSyncedSelKey = selSig;
    if (selSid && m.byId[selSid] && STEPS.includes(m.byId[selSid].type)) {
      curStepByBase[c.baseId] = m.byId[selSid].type;
    }
  }
  if (!curStepByBase[c.baseId] || !STEPS.includes(curStepByBase[c.baseId])) {
    curStepByBase[c.baseId] = defaultStepFor(m, B, c);
  }
  const curStep = curStepByBase[c.baseId];

  const tickW = innerWidth >= 1600 ? 6 : innerWidth >= 1000 ? 4 : innerWidth < 480 ? 2 : 3;
  let totalPassCnt = 0;
  m.rows.forEach(r => {
    if (matchesCoverFilter(rowStackMetrics(r, m, B, c, totPeerOrgs))) totalPassCnt++;
  });

  const ovSegsHTML = STEPS.map(stNm => {
    const stRows = m.rows.filter(r => r.type === stNm);
    const oursCnt = stRows.filter(r => has(r.cells[0])).length;
    const totCnt = stRows.length;
    const on = stNm === curStep;
    const ticksHTML = stRows.map(r => {
      const rm = rowStackMetrics(r, m, B, c, totPeerOrgs);
      const pass = matchesCoverFilter(rm);
      const tk = stackedShapeHTML(rm, tickW, innerWidth < 700 ? 22 : 28, 4);
      const layerVec = `${rm.better},${rm.same + rm.diff},${rm.worse},${rm.wait},${rm.miss}`;
      return `<span class="cv-tick${pass ? '' : ' is-filtered-out'}" data-cv-tick="${esc(r.sid)}" data-cv-step-of="${esc(stNm)}" data-stack-n="${rm.stackN}" data-layers="${layerVec}" style="width:${tickW}px;--th:${tk.h}px">${tk.html}<i class="cv-tk-sel"></i></span>`;
    }).join('');

    return `<button type="button" class="cv-ov-seg${on ? ' is-on' : ''}" style="--seg-n:${Math.max(4, totCnt)}" data-cv-step="${esc(stNm)}" aria-pressed="${on}" aria-label="${esc(`${stNm} 단계 보기 (${oursCnt}/${totCnt})`)}">
      <span class="cv-ov-sh">
        <span class="cv-ov-ring">${ui.miniRingSVG(oursCnt, Math.max(1, totCnt), '')}</span>
        <span class="cv-ov-nm">${esc(stNm)}</span>
        <span class="cv-ov-cnt num">${esc(`${fmt(oursCnt)}/${fmt(totCnt)}`)}</span>
      </span>
      <span class="cv-ov-ticks" aria-hidden="true">${ticksHTML}</span>
    </button>`;
  }).join('');

  const filterBtnsHTML = FILTERS.map(f => {
    const on = activeFilters.has(f.k);
    return `<button type="button" class="cv-flt-btn${on ? ' is-on' : ''}" data-cv-flt="${f.k}" aria-pressed="${on}">${esc(f.label)}</button>`;
  }).join('');
  const activeFilterNames = FILTERS.filter(f => activeFilters.has(f.k)).map(f => f.label).join(', ');
  const filterCountHTML = activeFilters.size
    ? `<span class="cv-flt-stat num" aria-live="polite">${esc(activeFilterNames)}: <b>${fmt(totalPassCnt)}</b>/${fmt(m.rows.length)}개</span>`
    : `<span class="cv-flt-stat num" aria-live="polite">전체 <b>${fmt(m.rows.length)}</b>개</span>`;

  // 만약 선택된 담보가 현재 단계의 다른 쪽에 있으면 그 쪽으로 맞춤
  let initPage = curPageByStep[c.baseId + '|' + curStep] || 0;
  if (selSid && m.byId[selSid] && m.byId[selSid].type === curStep) {
    const stRows = m.rows.filter(r => r.type === curStep);
    const lay = measureZoomLayout(center, stRows, domainOrderOf(c));
    lay.pages.forEach((p, pi) => {
      if (p.groups.some(g => g.items.some(it => it.sid === selSid))) initPage = pi;
    });
  }

  const zoomHTML = buildZoomedHTML(c, m, B, curStep, initPage, pIdxs, totPeerOrgs, rawPeerOrgs, pSet, center);

  // 비교 범위 안내(sales.json 기준종형[].범위안내. 보장 범위가 한정된 상품이나 같은 유형의 타사 종형이 인수기준만 수집된 기준 종형).
  // 문장에 전용표시("암, 2대질병 전용 상품")가 들어 있어 따로 태그를 붙이지 않는다
  const bRow = (S['기준종형'] || []).find(b => b['종형ID'] === c.baseId) || {};
  const scopeNoteHTML = bRow['범위안내'] ? `<p class="note cv-scope-note">${esc(bRow['범위안내'])}</p>` : '';
  center.innerHTML = `<div class="cvp-stage" id="cv-pillar-stage">
    ${scopeNoteHTML}
    <div class="cv-ov-top">
      <div class="cv-ov-strip" id="cv-ov-strip">
        <div class="cv-ov-segs" id="cv-ov-segs">${ovSegsHTML}</div>
        <div class="cv-ov-brk" id="cv-ov-brk" hidden aria-hidden="true"><i class="b-l"></i><i class="b-b"></i><i class="b-r"></i></div>
      </div>
      <div class="cv-flt-bar" role="group" aria-label="${esc(t('cvFltBarAria'))}">
        ${filterBtnsHTML}
        ${filterCountHTML}
      </div>
    </div>
    <div class="cv-zoom-box" id="cv-zoom-box">${zoomHTML}</div>
  </div>`;

  const stageEl = center.querySelector('#cv-pillar-stage');
  syncCoverSelectionAndFilter(stageEl);
  requestAnimationFrame(() => { positionOvBracket(stageEl, false); scrollSelectedBarIntoCenter(); });
}

function applyCoverFiltersInPlace(stageEl) {
  if (!stageEl) return;
  const c = App.ctx();
  const m = model(c.baseId);
  const B = CV && CV.b[c.baseId];
  if (!m || !B) return;
  const pIdxs = peerIdxOf(m, c);
  const rawPeerOrgs = new Set(pIdxs.map(i => orgOf(m.cols[i + 1]))).size;
  const totPeerOrgs = Math.max(1, rawPeerOrgs);
  const passMap = new Map();
  let totalPassCnt = 0;
  m.rows.forEach(r => {
    const pass = matchesCoverFilter(rowStackMetrics(r, m, B, c, totPeerOrgs));
    passMap.set(r.sid, pass);
    if (pass) totalPassCnt++;
  });
  stageEl.querySelectorAll('.cv-flt-btn[data-cv-flt]').forEach(btn => {
    const on = activeFilters.has(btn.dataset.cvFlt);
    btn.classList.toggle('is-on', on);
    btn.setAttribute('aria-pressed', String(on));
  });
  const statEl = stageEl.querySelector('.cv-flt-stat');
  if (statEl) {
    const activeFilterNames = FILTERS.filter(f => activeFilters.has(f.k)).map(f => f.label).join(', ');
    statEl.innerHTML = activeFilters.size
      ? `${esc(activeFilterNames)}: <b>${fmt(totalPassCnt)}</b>/${fmt(m.rows.length)}개`
      : `전체 <b>${fmt(m.rows.length)}</b>개`;
  }
  const curStep = curStepByBase[c.baseId] || STEPS[0];
  const stRows = m.rows.filter(r => r.type === curStep);
  const stageOursCnt = stRows.filter(r => has(r.cells[0])).length;
  const stageFilteredCnt = activeFilters.size ? stRows.filter(r => passMap.get(r.sid)).length : stRows.length;
  const zhSub = stageEl.querySelector('.cv-zh-sub');
  if (zhSub) {
    zhSub.textContent = activeFilters.size
      ? t('cvFltPassTpl', { n: fmt(stageFilteredCnt), tot: fmt(stRows.length) })
      : t('cvOursHoldTpl', { n: fmt(stageOursCnt), tot: fmt(stRows.length) });
  }
  stageEl.querySelectorAll('.cv-tick[data-cv-tick]').forEach(tk => {
    tk.classList.toggle('is-filtered-out', !passMap.get(tk.dataset.cvTick));
  });
  stageEl.querySelectorAll('.cvp-slot[data-sid]').forEach(sl => {
    sl.classList.toggle('is-filtered-out', !passMap.get(sl.dataset.sid));
  });
}

// ---------- 관계도(직각 꺾은선, 갈림 자리 9px 마름모). 탭 5 도 쓴다 ----------
const GF = w => `${w} 13px PLNum, PLKo, "Malgun Gothic", sans-serif`;
let mctx = null;
function tw(s, font) { if (!mctx) mctx = document.createElement('canvas').getContext('2d'); mctx.font = font; return mctx.measureText(s).width; }
function wrapT(s, font, max, n) {
  const out = []; let line = '';
  for (const ch of String(s)) {
    if (!line || tw(line + ch, font) <= max) { line += ch; continue; }
    const sp = line.lastIndexOf(' ');
    if (ch !== ' ' && sp > 0 && line.length - sp <= 6) { out.push(line.slice(0, sp)); line = line.slice(sp + 1) + ch; }
    else { out.push(line.trimEnd()); line = ch === ' ' ? '' : ch; }
  }
  if (line.trim()) out.push(line.trim());
  if (out.length <= n) return { lines: out, cut: false };
  const keep = out.slice(0, n); let last = keep[n - 1];
  while (last.length > 1 && tw(last + '…', font) > max) last = last.slice(0, -1);
  keep[n - 1] = last.trimEnd() + '…';
  return { lines: keep, cut: true };
}
const f1 = v => (+v).toFixed(1);
const dia = (x, y) => `<path class="rl-dia" d="M${f1(x)} ${f1(y - 4.5)}L${f1(x + 4.5)} ${f1(y)} ${f1(x)} ${f1(y + 4.5)} ${f1(x - 4.5)} ${f1(y)}Z"/>`;
function relSVG(baseId, sid, W) {
  const m = model(baseId); const row = m && m.byId[sid];
  if (!row) return '';
  W = Math.max(280, Math.floor(W));
  const LH = 17, PY = 7, PX = 8, BG = 20, TX = PX + BG + 7, TRX = 11;
  const busX = W - 6, benR = busX - 12;
  const rX = 26, rW = Math.round(Math.max(96, Math.min(150, W * .33))), bX = rX + rW + 22, bW = benR - bX;
  let s = '', y = 0;
  const box = (x, yy, w, h, cls = '') => `<rect class="rl-b ${cls}" x="${f1(x)}" y="${f1(yy)}" width="${f1(w)}" height="${f1(h)}"/>`;
  const glyph = (kind, x, yy) => {
    const cx = x + PX + BG / 2, cy = yy + PY + 6;
    const R = BG / 2 + 1;
    const shape = kind === '종' ? `<path class="rl-g" d="M${f1(cx)} ${f1(cy - R - 1)}L${f1(cx + R + 1)} ${f1(cy)} ${f1(cx)} ${f1(cy + R + 1)} ${f1(cx - R - 1)} ${f1(cy)}Z"/>`
      : kind === '급' ? `<circle class="rl-g" cx="${f1(cx)}" cy="${f1(cy)}" r="${R}"/>`
        : kind === '표' ? `<path class="rl-g" d="${Array.from({ length: 6 }, (_, i) => { const a = Math.PI / 3 * i + Math.PI / 6; return `${i ? 'L' : 'M'}${f1(cx + (R + 1) * Math.cos(a))} ${f1(cy + (R + 1) * Math.sin(a))}`; }).join('')}Z"/>`
          : `<rect class="rl-g" x="${f1(cx - R)}" y="${f1(cy - R)}" width="${2 * R}" height="${2 * R}"/>`;
    return shape + `<text class="rl-gt" x="${f1(cx)}" y="${f1(cy + 4.6)}" text-anchor="middle">${kind}</text>`;
  };
  const lines = (arr, x, y0, cls = 'rl-t') => `<text class="${cls}">${arr.map((t, i) => `<tspan x="${f1(x)}" y="${f1(y0 + i * LH)}">${esc(t)}</tspan>`).join('')}</text>`;
  const sl = wrapT(stdN(sid), GF(600), W - 2 - TX - PX, 2);
  const stdH = PY * 2 + LH * sl.lines.length + 2;
  s += box(0, 0, W - 2, stdH, 'std') + glyph('표', 0, (stdH - 26) / 2 + 2) + lines(sl.lines, TX, PY + 13 + 1);
  y = stdH + 16;
  const busTop = stdH;
  const curC = App.ctx();
  const pIdxsAll = peerIdxOf(m, curC);
  const pIdxs = pIdxsAll.slice(0, 6);
  const colIdxs = [0].concat(pIdxs.map(i => i + 1));
  const edges = [], dias = [];
  colIdxs.forEach(k => {
    const vid = m.cols[k];
    const c = row.cells[k];
    const head = `${orgN(vid)} ${txt.shortName(kindN(vid)).short}`;
    const hl = wrapT(head, GF(600), benR - TX - (k ? 0 : 44), 1).lines[0] || head;
    s += glyph('종', TRX - PX - BG / 2, y - 2) + `<text class="rl-t rl-h" x="${f1(TX - 2)}" y="${f1(y + 13)}">${esc(hl)}</text>`;
    if (!k) s += `<rect class="rl-base" x="${f1(TX - 2 + tw(hl, GF(600)) + 8)}" y="${f1(y - 1)}" width="38" height="20"/><text class="rl-s" x="${f1(TX - 2 + tw(hl, GF(600)) + 27)}" y="${f1(y + 13)}" text-anchor="middle">기준</text>`;
    const trunkTop = y + 20;
    y += 26;
    if (k) {
      const v = verdFor(row, m, k - 1, pIdxsAll);
      const t = `${chipText(v)}${v && v.why ? `: ${v.why}` : ''}`;
      const tl = wrapT(t, GF(400), benR - rX - 16, 3);
      const h = PY * 2 + LH * tl.lines.length - 2;
      s += `<rect class="rl-tag ${v ? 'k-' + v.kind : ''}" x="${f1(rX)}" y="${f1(y)}" width="${f1(benR - rX)}" height="${f1(h)}"/><rect class="rl-tagl ${v ? 'k-' + v.kind : ''}" x="${f1(rX)}" y="${f1(y)}" width="3" height="${f1(h)}"/>` + lines(tl.lines, rX + 12, y + PY + 12, 'rl-t rl-s');
      y += h + 8;
    }
    if (!has(c)) {
      const why = !c ? '이 종형에는 이 담보가 없습니다' : c.w ? t('cvRelWaitTpl', { w: c.w }) : c.c ? t('cvRelCoverTpl', { kind: c.c[0], covs: txt.josa(c.c[1].map(stdN).join(', '), '으로') }) : '이 종형에는 이 담보가 없습니다';
      const al = wrapT(why, GF(400), benR - rX - 20, 2);
      const h = PY * 2 + LH * al.lines.length - 2;
      s += box(rX, y, benR - rX, h, 'absent') + lines(al.lines, rX + 12, y + PY + 12, 'rl-t rl-s');
      edges.push({ d: `M${TRX} ${f1(trunkTop)}V${f1(y + h / 2)}H${f1(rX - 2)}`, dash: true });
      y += h + 18;
      return;
    }
    const ids = [c.r != null ? c.r : c.i[0], ...c.i.filter(i => i !== c.r)];
    const groups = [];
    ids.forEach(i => { const b = ben(i); if (!b) return; let g = groups.find(x => x.rid === b.rid); if (!g) groups.push(g = { rid: b.rid, bs: [] }); g.bs.push(b); });
    const mids = [];
    groups.forEach(g => {
      const rd = rider(g.rid);
      const rl = wrapT(txt.shortName(rd ? rd.name : '', { brackets: true }).short, GF(600), rW - TX - PX, 2);
      const rh = PY * 2 + LH * rl.lines.length;
      const bl = g.bs.map(b => {
        const nl = wrapT(txt.shortName(b.name, { brackets: true }).short, GF(600), bW - TX - PX, 2);
        const meta = `${b.i === (c.r != null ? c.r : c.i[0]) ? '대표, ' : ''}${txt.pageText(b.doc, b.page)}`;
        return { b, nl, meta, h: PY * 2 + LH * nl.lines.length + 16 };
      });
      const bh = bl.reduce((a, x) => a + x.h, 0) + (bl.length - 1) * 6;
      const rowH = Math.max(rh, bh);
      const ry = y + (rowH - rh) / 2;
      s += box(rX, ry, rW, rh, 'rider') + glyph('특', rX, ry) + lines(rl.lines, rX + TX, ry + PY + 13);
      const rmid = ry + rh / 2;
      mids.push(rmid);
      let by = y + (rowH - bh) / 2;
      const bmids = [];
      bl.forEach(x => {
        const rep = x.b.i === (c.r != null ? c.r : c.i[0]);
        s += box(bX, by, bW, x.h, rep ? 'ben rep' : 'ben') + glyph('급', bX, by) + lines(x.nl.lines, bX + TX, by + PY + 13)
          + `<text class="rl-s" x="${f1(bX + TX)}" y="${f1(by + PY + 13 + LH * x.nl.lines.length)}">${esc(x.meta)}</text>`;
        const mid = by + x.h / 2;
        bmids.push(mid);
        edges.push({ d: `M${f1(bX + bW)} ${f1(mid)}H${f1(busX)}V${f1(busTop + 2)}`, dash: x.b.log, arrow: true });
        by += x.h + 6;
      });
      const xm = rX + rW + 11;
      bmids.forEach(mid => edges.push({ d: `M${f1(rX + rW)} ${f1(rmid)}H${f1(xm)}V${f1(mid)}H${f1(bX - 1)}` }));
      if (bmids.length > 1) dias.push([xm, rmid]);
      y += rowH + 10;
    });
    mids.forEach(mid => edges.push({ d: `M${TRX} ${f1(trunkTop)}V${f1(mid)}H${f1(rX - 1)}` }));
    if (mids.length > 1) mids.slice(0, -1).forEach(mid => dias.push([TRX, mid]));
    const more = (c.n || 0) - ids.length;
    if (more > 0) {
      const ml = wrapT(t('cvRelMoreTpl', { n: c.n, shown: ids.length }), GF(400), benR - rX, 2);
      s += lines(ml.lines, rX, y + 10, 'rl-s');
      y += 2 + LH * ml.lines.length;
    }
    y += 12;
  });
  if (pIdxsAll.length > pIdxs.length) {
    const restMsg = t('cvRelRestPeersTpl', { n: pIdxsAll.length - pIdxs.length });
    s += `<text class="rl-s" x="${f1(rX)}" y="${f1(y + 10)}">${esc(restMsg)}</text>`;
    y += 22;
  }
  const H = Math.round(y);
  const es = edges.map(e => `<path class="rl-e${e.dash ? ' dash' : ''}" d="${e.d}"${e.dash ? '' : ' pathLength="1"'}${e.arrow ? ' marker-end="url(#rl-ar)"' : ''}/>`).join('');
  return `<svg class="rl-svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(stdN(sid))} 관계도: 회사마다 종형, 특약, 급부, 표준담보">
    <defs><marker id="rl-ar" viewBox="0 0 10 10" refX="5" refY="8" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto"><path d="M1 9L5 1 9 9" class="rl-arh"/></marker></defs>
    <g class="rl-es">${es}</g>${dias.map(d => dia(d[0], d[1])).join('')}${s}</svg>`;
}
function relLegend() {
  const ln = (dash, t) => `<span><svg width="20" height="6" aria-hidden="true"><line x1="0" y1="3" x2="20" y2="3" class="rl-e${dash ? ' dash' : ''}"/></svg>${t}</span>`;
  const bx = (ch, t) => `<span><b class="rl-lb" aria-hidden="true">${ch}</b>${t}</span>`;
  return `<div class="rl-lg"><div>${ln(false, '확정')}${ln(true, esc(t('cvRelLgWait')))}<span><svg width="10" height="10" viewBox="-5 -5 10 10" aria-hidden="true"><path class="rl-dia" d="M0-4.5L4.5 0 0 4.5-4.5 0Z"/></svg>${esc(t('cvRelLgBranch'))}</span><span><b class="rl-lb rep" aria-hidden="true">급</b>굵은 테두리는 대표 급부</span></div>
    <div>${bx('종', '종형')}${bx('특', '특약')}${bx('급', '급부')}${bx('표', '표준담보')}</div></div>`;
}
function drawRel(el, baseId, sid) {
  if (!el) return;
  const w = el.clientWidth || (el.parentElement && el.parentElement.clientWidth) || 360;
  el.innerHTML = relSVG(baseId, sid, w);
  if (App.motionOn()) { el.classList.remove('rl-in'); void el.offsetWidth; el.classList.add('rl-in'); }
}

// ---------- 조건 비교와 근거(상대 셋 이하는 나란히, 넷 이상이면 우체국 + 판정별 묶음 접기) ----------
function condTable(m, row, c) {
  const allPIdxs = peerIdxOf(m, c);
  const B = CV && CV.b[c.baseId];
  const allColIdxs = [0].concat(allPIdxs.map(i => i + 1));
  const hasAnyNonMon = allColIdxs.some(k => {
    const rp = repOf(row.cells[k]);
    return !!(rp && nonMonKind(rp));
  });
  const items = [
    ['지급', b => payText(b)],
    ['기준 가입금액', b => baseText(b)],
    ['면책', b => waitText(b.wait)],
    ['감액', b => redText(b.red, b)],
    ['지급 형태', b => formText(b, hasAnyNonMon)],
  ];

  // 상대가 넷 이상이면 우체국 + 판정기관코드 기준 판정 묶음으로 접고 누르면 회사별 줄을 펼친다
  if (allPIdxs.length >= 4) {
    const oursHas = has(row.cells[0]);
    const oursRep = repOf(row.cells[0]);
    const perCodes = (B && B['판정기관코드'] && B['판정기관코드'][row.sid]) || {};
    const pSet = new Set(c.activePeerOrgs || []);
    const scopedCodes = list => {
      if (!Array.isArray(list)) return [];
      return c.peerScope === 'all' ? list.slice() : list.filter(code => pSet.has(code));
    };
    const peerIdxsByOrg = {};
    allPIdxs.forEach(i => {
      const code = orgOf(m.cols[i + 1]);
      (peerIdxsByOrg[code] = peerIdxsByOrg[code] || []).push(i);
    });
    const buckets = [
      { key: 'better', label: verdictName('나음'), vd: 'better', codes: scopedCodes(perCodes['나음']) },
      { key: 'same', label: verdictName('같음'), vd: 'same', codes: scopedCodes(perCodes['같음']) },
      { key: 'worse', label: verdictName('못함'), vd: 'worse', codes: scopedCodes(perCodes['못함']) },
      { key: 'diff', label: verdictName('엇갈림'), vd: 'diff', codes: [...new Set([].concat(scopedCodes(perCodes['엇갈림']), scopedCodes(perCodes['단정 주의']), scopedCodes(perCodes['지급 형태 다름']), scopedCodes(perCodes['관계 담보로 덮음'])))] },
      { key: 'wait', label: verdictName('검토 대기'), vd: 'unknown', codes: scopedCodes(perCodes['검토 대기']) },
      { key: 'hold', label: verdictName('판정 보류'), vd: 'unknown', codes: scopedCodes(perCodes['판정 보류']) },
      { key: 'miss', label: verdictName('우체국에 없음'), vd: 'none', codes: scopedCodes(perCodes['우체국에 없음']) },
    ].filter(bk => bk.codes.length > 0);

    const inStackCodes = new Set(Object.keys(perCodes).flatMap(k => scopedCodes(perCodes[k])));
    const absentPeerOrgs = [...new Set(allPIdxs.map(i => orgOf(m.cols[i + 1])))].filter(code => !inStackCodes.has(code));

    const onlyChip = (oursHas && inStackCodes.size === 0 && allPIdxs.length > 0) ? `${ui.verdict('only', verdictName('상대에 없음'))} ` : '';
    const absentLabel = oursHas ? App.label('상대에 없음') : App.label(BOTH_NONE_TEXT);
    const summaryChips = onlyChip + buckets.map(bk => `<span class="cv-vg-chip">${ui.verdict(bk.vd, t('cvVerdictCntTpl', { nm: bk.label, n: fmt(bk.codes.length) }))}</span>`).join(' ')
      + (absentPeerOrgs.length ? ` <span class="tag">${esc(t('cvVerdictCntTpl', { nm: absentLabel, n: fmt(absentPeerOrgs.length) }))}</span>` : '');

    const oursCells = items.map(([lab, f]) => `<div class="cv-ours-kv"><span>${esc(lab)}</span><b>${oursRep ? esc(f(oursRep)) : '없음'}</b></div>`).join('');

    const mobDet = innerWidth <= 640;
    const groupsAccordion = buckets.map((bk, bIdx) => {
      const pRows = [];
      bk.codes.forEach(code => {
        const matchIdxs = peerIdxsByOrg[code] || [];
        if (matchIdxs.length) {
          matchIdxs.forEach(i => {
            const k = i + 1;
            const vid = m.cols[k];
            const c2 = row.cells[k];
            const rp = repOf(c2);
            const v = verdFor(row, m, i, allPIdxs);
            const emptyPay = c2 && c2.w ? `<span class="cv-na">${esc(t('cvCellWaitTpl', { w: c2.w }))}</span>` : c2 && c2.c ? `<span class="cv-na">${esc(t('cvCellCoverTpl', { kind: txt.josa(c2.c[0], '으로') }))}</span>` : '<span class="cv-na">없음</span>';
            if (mobDet) {
              const kvHTML = rp
                ? [['지급', payText(rp)], ['면책', waitText(rp.wait)], ['감액', redText(rp.red, rp)], ['지급 형태', formText(rp, hasAnyNonMon)]]
                  .map(([lb, val]) => `<span class="cv-ours-kv"><span>${esc(lb)}</span><b>${esc(val)}</b></span>`).join('')
                : emptyPay;
              pRows.push(`<tr>
                <th scope="row" title="${esc(fullN(vid))}">${esc(orgN(vid))} <span class="note">${esc(txt.shortName(kindN(vid)).short)}</span></th>
                <td><div class="cv-ours-grid">${kvHTML}</div><div class="cv-mob-vd">${chip(v)}</div></td>
              </tr>`);
            } else {
              pRows.push(`<tr>
                <th scope="row" title="${esc(fullN(vid))}">${esc(orgN(vid))} <span class="note">${esc(txt.shortName(kindN(vid)).short)}</span></th>
                <td>${rp ? esc(payText(rp)) : emptyPay}</td>
                <td>${rp ? esc(waitText(rp.wait)) : '-'}</td>
                <td>${rp ? esc(redText(rp.red, rp)) : '-'}</td>
                <td>${rp ? esc(formText(rp, hasAnyNonMon)) : '-'}</td>
                <td>${chip(v)}</td>
              </tr>`);
            }
          });
        } else if (mobDet) {
          pRows.push(`<tr><th scope="row">${esc(txt.orgShort(code))}</th><td class="note">해당 회사 보유</td></tr>`);
        } else {
          pRows.push(`<tr><th scope="row">${esc(txt.orgShort(code))}</th><td colspan="5" class="note">해당 회사 보유</td></tr>`);
        }
      });
      const detTblHTML = mobDet
        ? `<table class="cv-ct cv-ct-mob">
          <tr><th scope="col">${esc(t('cvColPeer'))}</th><th scope="col">조건과 비교 결과</th></tr>
          ${pRows.join('')}
        </table>`
        : `<table class="cv-ct">
          <tr><th scope="col">${esc(t('cvColPeer'))}</th><th scope="col">지급</th><th scope="col">면책</th><th scope="col">감액</th><th scope="col">지급 형태</th><th scope="col">비교 결과</th></tr>
          ${pRows.join('')}
        </table>`;
      return `<details class="zr-det cv-vg-det"${bIdx === 0 ? ' open' : ''}>
        <summary><span>${ui.verdict(bk.vd, t('cvVerdictCntTpl', { nm: bk.label, n: fmt(bk.codes.length) }))} <span class="note">${esc(txt.peerNamesEtc(bk.codes.map(txt.orgShort), 4))}</span></span>${ui.IC.chevD}</summary>
        <div class="zr-det-b"><div class="cv-ct-w">${detTblHTML}</div></div>
      </details>`;
    }).join('');

    return `<div class="cv-ct-w"><table class="cv-ct cv-ct-fold">
        <tr><th scope="col">${esc(orgN(m.cols[0]))} (기준)</th><th scope="col">${esc(t('cvFoldPeerHeadTpl', { n: fmt(allPIdxs.length) }))}</th></tr>
        <tr><td><div class="cv-ours-grid">${oursCells}</div></td><td><div class="cv-vg-sum">${summaryChips || `<span class="note">${esc(t('cvFoldNoPeer'))}</span>`}</div></td></tr>
      </table></div>
      <div class="cv-vg-list">${groupsAccordion}</div>
      <p class="note">${esc(t('cvFoldNote'))}</p>`;
  }

  const cols = allColIdxs.map(k => m.cols[k]);
  const reps = allColIdxs.map(k => repOf(row.cells[k]));
  const nonMonRedLbl = nonMonCopy('감액') || '원문 확인';
  const nonMonBaseLbl = nonMonCopy('기준') || '금액 하나로 적을 수 없는 급부';
  const payRuleTxt = hasAnyNonMon && nonMonCopy('지급액판정')
    ? `${nonMonCopy('지급액판정')} 및 기준 가입금액이 회사마다 달라 지급액은 비교 결과에 반영하지 않았습니다.`
    : '지급액은 기준 가입금액이 회사마다 달라 비교 결과에 반영하지 않았습니다.';
  const summaries = items.map(([lab, f]) => {
    const vals = {};
    allColIdxs.forEach(k => {
      const rp = repOf(row.cells[k]);
      vals[orgOf(m.cols[k])] = rp ? f(rp) : null;
    });
    const eqFn = hasAnyNonMon && (lab === '감액' || lab === '기준 가입금액')
      ? (a, b) => a === b && a !== nonMonRedLbl && a !== nonMonBaseLbl
      : undefined;
    return [lab, txt.sameSummary(vals, eqFn)];
  });

  // 좁은 창(640px 이하)에서는 열이 눌리거나 안쪽 가로 스크롤이 생기지 않게 회사를 줄로 세워 보여 준다(요청 30의 7-2)
  if (innerWidth <= 640) {
    const mobRows = cols.map((v, k) => {
      const rp = reps[k];
      const detail = rp
        ? items.map(([lab, f]) => `<span class="cv-ours-kv"><span>${esc(lab)}</span><b>${esc(f(rp))}</b></span>`).join('')
        : '<span class="cv-na">없음</span>';
      return `<tr><th scope="row" title="${esc(fullN(v))}">${esc(orgN(v))}</th><td><div class="cv-ours-grid">${detail}</div></td></tr>`;
    }).join('');
    const sumDetail = summaries.map(([lab, sm]) => `<span class="cv-ours-kv"><span>${esc(lab)}</span><b>${esc(sm)}</b></span>`).join('');
    return `<div class="cv-ct-w"><table class="cv-ct cv-ct-mob">
      <tr><th scope="col">회사</th><th scope="col">대표 급부 조건</th></tr>
      ${mobRows}
      <tr><th scope="row">요약</th><td class="sm"><div class="cv-ours-grid">${sumDetail}</div></td></tr>
    </table></div><p class="note">${esc(t('cvCondNoteTpl', { rule: payRuleTxt }))}</p>`;
  }

  const head = `<tr><th scope="col">항목</th>${cols.map(v => `<th scope="col" title="${esc(fullN(v))}">${esc(orgN(v))}</th>`).join('')}<th scope="col">요약</th></tr>`;
  const body = items.map(([lab, f], idx) => `<tr><th scope="row">${esc(lab)}</th>${cols.map((v, k) => `<td>${reps[k] ? esc(f(reps[k])) : '<span class="cv-na">없음</span>'}</td>`).join('')}<td class="sm">${esc(summaries[idx][1])}</td></tr>`).join('');

  return `<div class="cv-ct-w"><table class="cv-ct">${head}${body}</table></div><p class="note">${esc(t('cvCondNoteTpl', { rule: payRuleTxt }))}</p>`;
}

function evidenceList(m, row, extra, c) {
  const colIdxs = [0].concat(peerIdxOf(m, c).map(i => i + 1));
  const items = colIdxs.map(k => {
    const v = m.cols[k];
    const b = repOf(row.cells[k]);
    if (!b) return '';
    const rd = rider(b.rid);
    const nm = nonMonKind(b);
    const nmDesc = nonMonWhy(nm);
    const nmHTML = nmDesc ? `<br><span class="note"><b>${esc(nm)}:</b> ${esc(nmDesc)}</span>` : '';
    return `<li><b>${esc(orgN(v))}</b> ${ui.tag(txt.pageText(b.doc, b.page))} <span title="${esc(b.name)}">${esc(b.name)}</span>${rd ? `<br><span class="note">특약: ${esc(rd.name)}</span>` : ''}${nmHTML}</li>`;
  }).join('');
  return `<ul class="cv-evl">${items}${extra || ''}</ul>`;
}

function rowEvidence(c, sid, mode) {
  const m = model(c.baseId); const row = m && m.byId[sid];
  if (!row) return null;
  const B = CV && CV.b[c.baseId];
  const pIdxs = peerIdxOf(m, c);
  const pSet = new Set(c.activePeerOrgs || []);
  const scopedCau = c.peerScope === 'all' ? row.cau : row.cau.filter(x => (x['상대종형ID'] || []).some(v => pSet.has(orgOf(v))));
  const st = std(sid);
  const scBadge = c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : '';
  let judge = '';
  if (mode === 'caution' && scopedCau.length) {
    judge += scopedCau.map(x => `<p>${ui.verdict('diff')} <span class="note">${esc(x['종류'])}</span></p><p>${esc(x['문장'])}${scBadge}</p>`).join('');
  }
  const renderPeerJudge = i => {
    const peer = m.cols[i + 1];
    const v = verdFor(row, m, i, pIdxs);
    const q = v && v.q;
    const noRank = !v || (v.kind !== 'better' && v.kind !== 'worse');
    const word = w => (w === '나음' || w === '못함') ? (noRank ? App.label('다름') : w === '나음' ? App.label('우체국 나음') : App.label('우체국 못함')) : App.label(w);
    const its = q && q.it ? `<div class="cv-ct-w"><table class="cv-it"><tr><th scope="col">항목</th><th scope="col">우체국</th><th scope="col">${esc(orgN(peer))}</th><th scope="col">비교</th></tr>${q.it.map(r => `<tr><th scope="row">${esc(r[0])}</th><td>${esc(r[1])}</td><td>${esc(r[2])}</td><td>${esc(word(r[3]))}${r[4] ? `<br><span class="note">${esc(r[4])}</span>` : ''}</td></tr>`).join('')}</table></div>` : '';
    return `<div class="cv-jd"><p><b>${esc(t('cvPeerCmpTpl', { peer: txt.josa(fullN(peer), '과') }))}</b> ${chip(v)}</p>${v && v.why ? `<p class="note">${esc(v.why)}</p>` : ''}${noRank && q && q.it && q.it.some(r => r[3] === '나음' || r[3] === '못함') ? `<p class="note">${esc(t('cvNoRankNote'))}</p>` : ''}${its}</div>`;
  };
  judge += pIdxs.slice(0, 3).map(renderPeerJudge).join('');
  if (pIdxs.length > 3) {
    const restIdxs = pIdxs.slice(3);
    const restNames = txt.peerNamesEtc(restIdxs.map(i => orgN(m.cols[i + 1])), 4);
    judge += `<details class="zr-det cv-vg-det" style="margin-top:8px"><summary><span>${esc(t('cvRestPeersJudgeTpl', { n: fmt(restIdxs.length), names: restNames }))}</span>${ui.IC.chevD}</summary><div class="zr-det-b">${restIdxs.map(renderPeerJudge).join('')}</div></details>`;
  }
  const scopedPts = c.peerScope === 'all' ? row.pts : row.pts.filter(p => (p['관련기관코드'] || []).some(o => pSet.has(o)));
  const pts = scopedPts.map(p => `<li>${ui.tag(App.label(p['분류']))} ${p['원문대조'] ? ui.flagText(p['원문대조글']) : ''}<p>${esc(p['문장'])}${scBadge}</p>${p['주의'] ? `<p class="note">주의: ${esc(p['주의'])}${scBadge}</p>` : ''}</li>`).join('');
  const cauEv = mode === 'caution' ? scopedCau.flatMap(x => (x['근거'] || []).filter(g => g['종형ID'] === c.baseId || c.peerScope === 'all' || pSet.has(orgOf(g['종형ID']))).map(g => `<li><b>${esc(orgN(g['종형ID']))}</b> ${ui.tag(txt.pageText(g['문서'], g['쪽']))} ${g['구분'] ? ui.tag(g['구분']) : ''} <span>${esc(fixG(g['급부명'] || ''))}</span></li>`)).join('') : '';
  const out = [];
  pIdxs.forEach(i => { const v = row.verd[i]; if (v && v.kind === 'unknown') out.push(`${orgN(m.cols[i + 1])}: ${v.why || App.label(v.text)}`); });
  row.omit.filter(o => c.peerScope === 'all' || (o['비교종형ID'] || []).some(v => pSet.has(orgOf(v)))).forEach(o => {
    const subNm = SUB_NAME_MAP[o['세부']] || App.label(o['세부']);
    out.push(`${App.label(o['분류'])}${subNm ? `(${subNm})` : ''}: ${reasonText(o['사유'])}`);
  });
  const stRowsForNav = STEPS.includes(row.type)
    ? buildDomainGroups(m.rows.filter(r => r.type === row.type), domainOrderOf(c)).flatMap(g => g.items)
    : [];
  const navList = stRowsForNav.length > 1 ? stRowsForNav : m.rows;
  const navIdx = navList.findIndex(r => r.sid === sid);
  const prevRow = navIdx > 0 ? navList[navIdx - 1] : null;
  const nextRow = navIdx >= 0 && navIdx < navList.length - 1 ? navList[navIdx + 1] : null;
  const navStepLbl = stRowsForNav.length > 1 ? `${row.type} ` : '';
  const mobNavHTML = navIdx >= 0 && navList.length > 1
    ? `<div class="cv-mob-nav" role="navigation" aria-label="담보 이동">
        <button type="button" class="btn sm ghost cv-mob-nav-btn" data-act="cv-mob-nav" data-sid="${prevRow ? esc(prevRow.sid) : ''}"${prevRow ? '' : ' disabled'}>${ui.IC.chevL}<span>이전 담보</span></button>
        <span class="cv-mob-nav-pos num">${esc(navStepLbl)}${fmt(navIdx + 1)} / ${fmt(navList.length)}</span>
        <button type="button" class="btn sm ghost cv-mob-nav-btn" data-act="cv-mob-nav" data-sid="${nextRow ? esc(nextRow.sid) : ''}"${nextRow ? '' : ' disabled'}><span>다음 담보</span>${ui.IC.chevR}</button>
      </div>`
    : '';
  const graphJump = `<div style="margin-top:8px">${ui.btn(App.t('mkEvGraphBtn'), { sm: true, ghost: true, chev: true, attrs: `data-go="graph" data-focus="std:${esc(sid)}"` })}</div>`;
  const body = `${mobNavHTML}<div class="ev-sec"><h3>회사별 조건(면책, 감액, 지급)</h3>${condTable(m, row, c)}${graphJump}</div>
    <div class="ev-sec"><h3>비교 결과와 인사이트</h3>${judge || `<p class="note">${esc(App.t('peerEmptyHint'))}</p>`}${pts ? `<ul class="cv-pts" style="margin-top:8px">${pts}</ul>` : ''}</div>
    <details class="zr-det"><summary><span>관계도와 근거 문서 쪽 번호 보기</span>${ui.IC.chevD}</summary><div class="zr-det-b">
      <div class="cv-rel" data-sid="${esc(sid)}"></div>${relLegend()}
      <h3 style="margin:12px 0 6px;font:600 13.5px/1.3 var(--f-ko)">근거 문서와 쪽</h3>
      ${mode === 'caution' && cauEv ? `<ul class="cv-evl">${cauEv}</ul><p class="note">"대표 밖"은 대표 급부 밖에 조건이 다른 급부입니다.</p>` : evidenceList(m, row, '', c)}
      ${out.length ? `<h3 style="margin:12px 0 6px;font:600 13.5px/1.3 var(--f-ko)">${esc(t('cvOmitHead'))}</h3><ul class="cv-evl">${out.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}
    </div></details>`;

  let verdBadges = '';
  if (pIdxs.length >= 4 && B) {
    // 쌍판정(row.verd)과 판정차례로 모든 판정 이름을 빠짐없이 모아 표지의 곳 수 합이 상대 수(및 판정상대수 합)와 정확히 같게 한다(2-1)
    const countsByName = new Map();
    const chipByName = new Map();
    pIdxs.forEach(i => {
      const v = row.verd[i];
      const nm = v ? v.name : BOTH_NONE_TEXT;
      countsByName.set(nm, (countsByName.get(nm) || 0) + 1);
      if (v && !chipByName.has(nm)) chipByName.set(nm, v.kind);
    });
    const orderList = (CV && Array.isArray(CV['판정차례']) && CV['판정차례'].length)
      ? CV['판정차례']
      : ['우체국 나음', '우체국 못함', '같음', '우열을 매기지 않음', '우체국에만 있음', '우체국에 없음', '검토 대기', '판정 보류', BOTH_NONE_TEXT];
    const onlyNm = [...chipByName].find(([, k]) => k === 'only');
    const allOnly = ((onlyNm && countsByName.get(onlyNm[0])) || 0) === pIdxs.length && pIdxs.length > 0;
    const badgeParts = [];
    orderList.forEach(nm => {
      const cnt = countsByName.get(nm) || 0;
      if (!cnt) return;
      if (chipByName.get(nm) === 'only') {
        if (allOnly) badgeParts.push(ui.verdict('only', t('cvVerdictCntTpl', { nm: App.label('우체국에만 있음'), n: fmt(cnt) })));
        else badgeParts.push(`<span class="tag">${esc(t('cvVerdictCntTpl', { nm: App.label('상대에 없음'), n: fmt(cnt) }))}</span>`);
      } else if (nm === BOTH_NONE_TEXT) {
        badgeParts.push(`<span class="tag">${esc(t('cvVerdictCntTpl', { nm: App.label(BOTH_NONE_TEXT), n: fmt(cnt) }))}</span>`);
      } else {
        badgeParts.push(ui.verdict(chipByName.get(nm) || 'unknown', t('cvVerdictCntTpl', { nm: App.label(nm), n: fmt(cnt) })));
      }
    });
    verdBadges = badgeParts.join(' ');
  } else {
    verdBadges = pIdxs.slice(0, 3).map(i => { const v = verdFor(row, m, i, pIdxs); return v ? `<span class="cv-bd"><span>${esc(txt.josa(orgN(m.cols[i + 1]), '과'))}</span>${chip(v)}</span>` : ''; }).join('');
  }
  return {
    kicker: mode === 'caution' ? t('cvEvKickerCaution') : t('cvEvKickerCover'), title: stdN(sid),
    badges: [ui.scope('base'), ui.tag(`${st['대분류'] || ''} ${st['급부유형'] || ''}`.trim()), verdBadges].filter(Boolean),
    body,
    after(el) {
      const detEl = el.querySelector('.zr-det:not(.cv-vg-det)');
      const relEl = el.querySelector('.cv-rel');
      if (detEl && relEl) {
        detEl.addEventListener('toggle', () => { if (detEl.open && !relEl.innerHTML) drawRel(relEl, c.baseId, sid); });
      }
    },
  };
}

// ---------- [표로 보기] 전체 창: 치료 여정 격자, 단정 주의, 보류 요약, 담보 비교표 ----------
let fGroup = null, diffOnly = false;
function journeyData(c) {
  const j = c.base['치료여정'];
  const cols = j['종형'];
  const byVid = Object.fromEntries(cols.map(x => [x['종형ID'], x]));
  const peerCols = c.peerScope === 'all' ? cols.slice(1) : c.peerIds.map(v => byVid[v]).filter(Boolean);
  return { j, cols: [byVid[c.baseId] || cols[0], ...peerCols].filter(Boolean) };
}
function journeyTone(idx) {
  if (idx === 0) return { bar: 'ours', lg: 'lg0' };
  if (idx === 1) return { bar: 'other', lg: 'lg1' };
  if (idx === 2) return { bar: 'other hollow', lg: 'lg2' };
  return { bar: 'other dashed', lg: 'lg3' };
}
function journeyHTML(c) {
  const { j, cols } = journeyData(c);
  const rowsG = j['행'];
  const compactPeers = cols.length > 4;
  const dispVals = rawVals => compactPeers ? [rawVals[0], Math.max(0, ...rawVals.slice(1))] : rawVals;
  const dispLabels = compactPeers
    ? [{ nm: orgN(cols[0]['종형ID']), title: cols[0]['이름'] }, { nm: t('cvPeerMaxTpl', { n: cols.length - 1 }), title: cols.slice(1).map(x => orgN(x['종형ID'])).join(', ') }]
    : cols.map(x => ({ nm: orgN(x['종형ID']), title: x['이름'] }));
  const max = Math.max(1, ...cols.flatMap(x => rowsG.flatMap(g => STEPS.map(s => (x['칸'][g] || {})[s] || 0))));
  const maxT = Math.max(1, ...cols.flatMap(x => STEPS.map(s => x['합계'][s] || 0)));
  const rowSum = (x, g) => STEPS.reduce((a, s) => a + ((x['칸'][g] || {})[s] || 0), 0);
  const maxR = Math.max(1, ...cols.flatMap(x => rowsG.map(g => rowSum(x, g))));
  const bars = (vals, mx) => dispVals(vals).map((n, i) => `<span class="cvj-b"><span class="hbar"><i class="${journeyTone(i).bar}" style="width:100%;transform:scaleX(${(n / mx).toFixed(4)})"></i></span><b class="num">${n}</b></span>`).join('');
  const lab = dispLabels.map(d => `<span class="cvj-l" title="${esc(d.title)}">${esc(d.nm)}</span>`).join('');
  let h = `<div class="cvj-h cvj-c0"></div>${STEPS.map(s => `<div class="cvj-h">${esc(s)}</div>`).join('')}<div class="cvj-h cvj-t">대분류 합계</div>`;
  rowsG.forEach(g => {
    h += `<div class="cvj-g"><span class="cvj-n">${esc(g)}</span><span class="cvj-ls">${lab}</span></div>`;
    STEPS.forEach(s => {
      const vals = cols.map(x => (x['칸'][g] || {})[s] || 0);
      const z0 = vals[0] === 0 && vals.slice(1).some(v => v > 0);
      const all0 = vals.every(v => v === 0);
      h += `<button type="button" class="sq cvj-c${z0 ? ' z0' : ''}${all0 ? ' a0' : ''}" data-pick="j:${esc(g)}:${esc(s)}" aria-label="${esc(`${g} ${s}: ${dispLabels.map((d, i) => `${d.nm} ${dispVals(vals)[i]}`).join(', ')}. 담보 목록 보기`)}">
        ${bars(vals, max)}<span class="cvj-ch" aria-hidden="true">${ui.IC.chevR}</span></button>`;
    });
    h += `<div class="cvj-c cvj-t">${bars(cols.map(x => rowSum(x, g)), maxR)}</div>`;
  });
  h += `<div class="cvj-g cvj-tt"><span class="cvj-n">단계 합계</span><span class="cvj-ls">${lab}</span></div>`;
  STEPS.forEach(s => { h += `<div class="cvj-c cvj-t">${bars(cols.map(x => x['합계'][s] || 0), maxT)}</div>`; });
  h += `<div class="cvj-c cvj-t cvj-all">${dispLabels.map((d, i) => `<span class="cvj-b"><span class="cvj-l2">${esc(d.nm)}</span><b class="num">${dispVals(cols.map(x => x['전체']))[i]}</b></span>`).join('')}</div>`;
  const ours = cols[0];
  const parts = STEPS.map(s => ({ t: s, n: ours['합계'][s] || 0 })).concat(ours['기타'] ? [{ t: '기타', n: ours['기타'] }] : []);
  const etcList = cols.map(x => `${orgN(x['종형ID'])} ${x['기타'] || 0}개`);
  const etc = etcList.length <= 4 ? etcList.join(', ') : txt.peerNamesEtc(etcList, 4);
  return `<section class="panel cv-jr" id="cover-journey" aria-labelledby="cover-journey-h">
    <div class="panel-h"><div><span class="k">${ui.scope('base')} 보장 대분류와 치료 단계마다 표준담보를 집계합니다</span><h2 id="cover-journey-h"><span>${esc(t('cvJourneyTitle'))}</span>${ui.help('journey-grid', t('cvJourneyTitle'))}</h2></div>
      <div class="r"><span class="cvj-lg">${dispLabels.map((d, i) => `<span><i class="${journeyTone(i).lg}"></i>${esc(d.nm)}</span>`).join('')}<span><i class="lgz"></i>${esc(t('cvJourneyZero'))}</span></span>
      <span class="live">${ui.btn(t('cvCopyTableBtn'), { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="cv-copy-journey"' })}${ui.btn('인쇄', { sm: true, ghost: true, icon: 'print', attrs: `data-print="cover-journey" data-title="${esc(t('cvJourneyTitle'))}"` })}</span></div></div>
    <div class="cvj-w"><div class="cvj" role="group" aria-label="${esc(t('cvJourneyTitle'))}">${h}</div></div>
    <div class="panel-f">${ui.eq({ total: { t: `${orgN(ours['종형ID'])} 담보`, n: ours['전체'] }, parts, tail: '개' })}
      <div class="nadd">${esc(t('cvJourneyEtcTpl', { etc }))}</div>
      <p class="note" style="margin:6px 0 0">${esc(t('cvJourneyNote'))}</p></div>
  </section>`;
}
function journeyPick(c, key) {
  const [, g, s] = key.split(':');
  const { cols } = journeyData(c);
  const lists = cols.map(x => ((x['담보'][g] || {})[s] || []));
  const all = [...new Set(lists.flat())];
  const m = model(c.baseId);
  const B = CV && CV.b[c.baseId];
  const pIdxs = peerIdxOf(m, c);
  const order = m ? Object.fromEntries(m.rows.map((r, i) => [r.sid, i])) : {};
  all.sort((a, b) => (order[a] ?? 999) - (order[b] ?? 999));
  const peerCols = cols.slice(1);
  const foldPeers = peerCols.length >= 4;
  let tblHTML = `<p>${esc(t('cvJourneyEmptyCell'))}</p>`;
  if (all.length) {
    if (foldPeers) {
      const rows = all.map(sid => {
        const row = m && m.byId[sid];
        const oursHas = lists[0].includes(sid);
        const heldNames = [], absentNames = [];
        peerCols.forEach((x, idx) => {
          const nm = orgN(x['종형ID']);
          if (lists[idx + 1].includes(sid)) heldNames.push(nm);
          else absentNames.push(nm);
        });
        let vHTML = '';
        if (B) {
          const pc = (B['판정기관코드'] && B['판정기관코드'][sid]) || {};
          const cntCode = k => (c.peerScope === 'all' ? ((pc[k] || []).length) : c.inScope(pc[k]));
          const bks = [
            ['better', verdictName('나음'), cntCode('나음')],
            ['same', verdictName('같음'), cntCode('같음')],
            ['worse', verdictName('못함'), cntCode('못함')],
            ['diff', verdictName('엇갈림'), cntCode('엇갈림') + cntCode('단정 주의') + cntCode('지급 형태 다름') + cntCode('관계 담보로 덮음')],
            ['unknown', verdictName('검토 대기'), cntCode('검토 대기')],
            ['unknown', verdictName('판정 보류'), cntCode('판정 보류')],
            ['none', verdictName('우체국에 없음'), cntCode('우체국에 없음')],
          ].filter(x => x[2] > 0);
          if (!bks.length && oursHas && pIdxs.length > 0) {
            vHTML = ui.verdict('only', verdictName('상대에 없음'));
          } else {
            vHTML = bks.map(([vd, lb, n]) => ui.verdict(vd, t('cvVerdictCntTpl', { nm: lb, n: fmt(n) }))).join(' ');
          }
        }
        const peerDetail = `<details class="zr-det cv-vg-det" style="border-top:0"><summary style="padding:2px 0"><span>보유 <b class="num">${fmt(heldNames.length)}</b>/${fmt(peerCols.length)}개 종형</span>${ui.IC.chevD}</summary><div class="zr-det-b" style="padding:4px 0 2px"><div class="note"><b>있음(${fmt(heldNames.length)}):</b> ${heldNames.length ? esc(heldNames.join(', ')) : '없음'}</div><div class="note"><b>없음(${fmt(absentNames.length)}):</b> ${absentNames.length ? esc(absentNames.join(', ')) : '없음'}</div></div></details>`;
        return `<tr>
          <th scope="row">${row ? `<button type="button" class="cv-lk" data-act="cv-goto" data-sid="${esc(sid)}">${esc(stdN(sid))}${ui.IC.chevR}</button>` : esc(stdN(sid))}${vHTML ? `<div class="cv-bds">${vHTML}</div>` : ''}</th>
          <td class="${oursHas ? 'ok' : 'no'}">${oursHas ? '있음' : '없음'}</td>
          <td>${peerDetail}</td>
        </tr>`;
      }).join('');
      tblHTML = `<div class="cv-ct-w"><table class="cv-jt"><tr><th scope="col">${esc(t('cvJourneyColGrp'))}</th><th scope="col">${esc(orgN(cols[0]['종형ID']))}</th><th scope="col">${esc(t('cvJourneyColPeersTpl', { n: fmt(peerCols.length) }))}</th></tr>${rows}</table></div><p class="note">${esc(t('cvJourneyFoldNote'))}</p>`;
    } else {
      const rows = all.map(sid => {
        const row = m && m.byId[sid];
        const marks = cols.map((x, i) => lists[i].includes(sid) ? '<td class="ok">있음</td>' : '<td class="no">없음</td>').join('');
        const v = row ? pIdxs.map(i => { const vv = verdFor(row, m, i, pIdxs); return vv ? `<span class="cv-bd"><span>${esc(txt.josa(orgN(m.cols[i + 1]), '과'))}</span>${chip(vv)}</span>` : ''; }).join('') : '';
        return `<tr><th scope="row">${row ? `<button type="button" class="cv-lk" data-act="cv-goto" data-sid="${esc(sid)}">${esc(stdN(sid))}${ui.IC.chevR}</button>` : esc(stdN(sid))}<div class="cv-bds">${v}</div></th>${marks}</tr>`;
      }).join('');
      tblHTML = `<div class="cv-ct-w"><table class="cv-jt"><tr><th scope="col">담보와 비교 결과(우체국 기준)</th>${cols.map(x => `<th scope="col" title="${esc(x['이름'])}">${esc(orgN(x['종형ID']))}</th>`).join('')}</tr>${rows}</table></div><p class="note">${esc(t('cvJourneyGotoNote'))}</p>`;
    }
  }
  const cntItems = cols.map((x, i) => `${orgN(x['종형ID'])} ${lists[i].length}개`);
  const cntLine = cntItems.length <= 5
    ? `<p>${esc(cntItems.join(', '))}</p>`
    : `<p>${esc(txt.peerNamesEtc(cntItems, 5))}</p><details class="zr-det cv-vg-det"><summary><span>전체 ${fmt(cntItems.length)}개 종형 담보 수 보기</span>${ui.IC.chevD}</summary><div class="zr-det-b"><p class="note">${esc(cntItems.join(', '))}</p></div></details>`;
  return {
    kicker: t('cvJourneyKicker'), title: `${g} ${s}`, badges: [ui.scope('base')],
    body: `<div class="ev-sec"><h3>${esc(t('cvJourneyCellCntHead'))}</h3>${cntLine}
        <div class="nadd">${esc(t('cvJourneyCellCntNoteTpl', { n: all.length }))}</div></div>
      <div class="ev-sec"><h3>담보 목록</h3>${tblHTML}</div>`,
  };
}

function scopedCaution(c) {
  const raw = (c.base && c.base['단정주의']) || [];
  if (c.peerScope === 'all') return raw;
  const pSet = new Set(c.activePeerOrgs || []);
  return raw.filter(x => (x['상대종형ID'] || []).some(v => pSet.has(orgOf(v))));
}
function cautionHTML(c) {
  const cau = scopedCaution(c);
  const kinds = [];
  cau.forEach(x => { let k = kinds.find(y => y.k === x['종류']); if (!k) kinds.push(k = { k: x['종류'], xs: [] }); k.xs.push(x); });
  const pSet = new Set(c.activePeerOrgs || []);
  const peerName = x => {
    const vids = c.peerScope === 'all' ? (x['상대종형ID'] || []) : (x['상대종형ID'] || []).filter(v => pSet.has(orgOf(v)));
    return txt.peerNamesEtc(vids.map(fullN), 3);
  };
  return `<section class="panel cv-cau" id="cover-caution" aria-labelledby="cover-caution-h">
    <div class="panel-h"><div><span class="k">${ui.scope('base')} ${esc(t('cvCautionKicker'))}</span><h2 id="cover-caution-h">${esc(t('cvCautionTitleTpl', { n: cau.length }))}</h2></div>
      <div class="r"><span class="live">${ui.btn('목록 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="cv-copy-caution"' })}${ui.btn('인쇄', { sm: true, ghost: true, icon: 'print', attrs: `data-print="cover-caution" data-title="${esc(t('cvCautionListTitle'))}"` })}</span></div></div>
    ${kinds.map(k => `<div class="cv-kh"><span>${esc(k.k)}</span><b class="num">${k.xs.length}</b></div>
      <ul class="lrows">${k.xs.map(x => `<li class="lrow cv-cr" data-pick="c:${esc(x['표준담보ID'])}">
        <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${x['담보']}, ${k.k}. 근거 보기`)}"></button>
        <div class="cv-crh selbar">${ui.verdict('diff')}<span class="cv-cn">${esc(x['담보'])}</span></div>
        <p class="cv-cpe">${esc(t('cvCautionPeerTpl', { peer: peerName(x) }))}</p>
        <p class="cv-ctx">${esc(x['문장'])}${c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : ''}</p>
        <span class="lrow-chev" aria-hidden="true">${ui.IC.chevR}</span></li>`).join('')}</ul>`).join('') || `<p class="placeholder">${esc(t('cvCautionEmpty'))}</p>`}
  </section>`;
}
function pendingHTML(c) {
  const p = c.base['보류요약'];
  const pSet = new Set(c.activePeerOrgs || []);
  const peers = c.peerScope === 'all' ? (p['맞붙는종형'] || c.peerIds) : c.peerIds;
  const sp = (c.peerScope === 'all' ? scopedPairs(c.baseId, null) : scopedPairs(c.baseId, pSet)) || { total: 0, wait: 0, cmp: 0, why: {} };
  const why = sp.why || {};
  const whySum = Object.values(why).reduce((a, b) => a + b, 0);
  const shownPeers = peers.slice(0, 6);
  const restPeers = peers.slice(6);
  const rows = (p['대분류'] || []).map(x => {
    let rowTot = x['공통담보쌍'] || 0, rowWait = x['뺀쌍'] || 0, rowCmp = x['견준쌍'] || 0;
    const waitByPeer = Object.assign({}, x['상대별'] || {});
    if (c.peerScope !== 'all') {
      rowTot = 0; rowWait = 0; rowCmp = 0;
      const byOrg = x['기관별'] || {};
      for (const [org, per] of Object.entries(byOrg)) {
        if (!pSet.has(org) || !per) continue;
        rowTot += per['공통담보쌍'] || 0;
        rowWait += per['뺀쌍'] || 0;
        rowCmp += per['견준쌍'] || 0;
      }
    }
    const restWait = restPeers.reduce((acc, v) => acc + (waitByPeer[v] || 0), 0);
    const peerCells = shownPeers.map(v => `<span class="num">${waitByPeer[v] || 0}</span>`);
    if (restPeers.length) peerCells.push(`<span class="num" title="${esc(restPeers.map(orgN).join(', '))}">${restWait}</span>`);
    return [`<span class="nw">${esc(x['대분류'])}</span>`, `<span class="num">${rowTot}</span>`, `<span class="num">${rowCmp}</span>`, `<span class="num">${rowWait}</span>`, ...peerCells];
  });
  const headCols = ['보장 대분류', t('cvPdColCommon'), t('cvPdColCmp'), t('cvPdColWait'), ...shownPeers.map(v => `${esc(orgN(v))} 대기`)];
  const numCols = [1, 2, 3, ...shownPeers.map((_, i) => i + 4)];
  if (restPeers.length) {
    headCols.push(t('cvPdColRestWaitTpl', { n: fmt(restPeers.length) }));
    numCols.push(headCols.length - 1);
  }
  const sumNote = restPeers.length
    ? t('cvPdSumNoteRestTpl', { shown: fmt(shownPeers.length), rest: fmt(restPeers.length) })
    : t('cvPdSumNoteAll');
  const cellsBar = sp.total <= 80 ? ui.cells(Array(sp.cmp).fill('cmp').concat(Array(sp.wait).fill('wait'))) : '';
  return `<section class="panel tbl-wrap cv-pd" id="cover-pending" aria-labelledby="cover-pending-h">
    <div class="panel-h"><div><span class="k">${ui.scope('base')} ${esc(t('cvPdKicker'))}</span><h2 id="cover-pending-h">${esc(t('cvPdTitle'))}</h2></div>
      <div class="r"><span class="live">${ui.btn(t('cvCopyTableBtn'), { sm: true, ghost: true, icon: 'copy', attrs: `data-copy="cover-pd-tbl" data-title="${esc(t('cvPdTitle'))}"` })}${ui.btn('인쇄', { sm: true, ghost: true, icon: 'print', attrs: `data-print="cover-pending" data-title="${esc(t('cvPdTitle'))}"` })}</span></div></div>
    <div class="cv-pd-eq">${ui.eq({ total: { t: t('cvPdColCommon'), n: sp.total }, parts: [{ t: t('cvPdColCmp'), n: sp.cmp }, { t: t('cvPdWaitExcl'), n: sp.wait }], tail: t('cvPdTailUnit') })}
      ${cellsBar}
      ${sp.wait > 0 && Object.keys(why).length ? `<div class="nadd">${esc(t('cvPdWhyHeadTpl', { list: Object.entries(why).map(([a, b]) => `${a} ${b}`).join(', '), tail: whySum > sp.wait ? t('cvPdWhyOverlapTpl', { sum: txt.josa(String(whySum), '으로'), wait: sp.wait }) : t('cvPdWhySumTpl', { sum: whySum }) }))}</div>` : ''}</div>
    <div class="cv-pd-t">${ui.table({ id: 'cover-pd-tbl', head: headCols, rows, num: numCols })}</div>
    <div class="panel-f">${cellsBar ? `${esc(t('cvPdCellsLegendPrefix'))}<span class="kd-l"><i class="cq cmp"></i>${esc(t('cvPdCellsCmp'))}</span> <span class="kd-l"><i class="cq wait"></i>${esc(t('cvPdCellsWait'))}</span>. ` : ''}${esc(sumNote)}</div>
  </section>`;
}

function midBand(c) {
  const pSet = new Set(c.activePeerOrgs || []);
  const sp = (c.peerScope === 'all' ? scopedPairs(c.baseId, null) : scopedPairs(c.baseId, pSet)) || { total: 0, wait: 0, cmp: 0 };
  const cau = scopedCaution(c);
  const kinds = {};
  cau.forEach(x => { kinds[x['종류']] = (kinds[x['종류']] || 0) + 1; });
  const stats = [{ n: sp.cmp, d: sp.total, l: t('cvMidStatCmp'), bar: [sp.cmp, Math.max(1, sp.total)] },
    { n: sp.wait, d: sp.total, l: t('cvMidStatWait'), bar: [sp.wait, Math.max(1, sp.total), 'other'] }]
    .concat(Object.entries(kinds).map(([k, n]) => ({ n, u: '건', l: t('cvMidStatCauTpl', { kind: k }) })));
  return ui.band({ kicker: t('cvMidKicker'), title: t('cvMidTitle'), help: 'caution-pending', sc: 'base', stats,
    note: t('cvMidNoteTpl', { n: cau.length }) });
}

function chipKindByName(nm) {
  const tbl = (CV && CV['판정표']) || {};
  for (const v of Object.values(tbl)) {
    if (v && v['판정'] === nm) return v['칩'];
  }
  return 'unknown';
}

function sumVerdictSummary(B, c) {
  const order = (CV && Array.isArray(CV['판정차례'])) ? CV['판정차례'] : ['우체국 나음', '우체국 못함', '같음', '우열을 매기지 않음', '우체국에만 있음', '우체국에 없음', '검토 대기', '판정 보류', BOTH_NONE_TEXT];
  const byName = Object.fromEntries(order.map(nm => [nm, 0]));
  const vs = (B && B['판정요약']) || {};
  const pSet = new Set(c.activePeerOrgs || []);
  for (const [org, per] of Object.entries(vs)) {
    if (c.peerScope !== 'all' && !pSet.has(org)) continue;
    for (const [nm, n] of Object.entries(per || {})) {
      byName[nm] = (byName[nm] || 0) + (n || 0);
    }
  }
  return { order, byName };
}

function tableBand(c, m, byName, peerN) {
  const total = m.rows.length * peerN;
  const denom = Math.max(1, total);
  const st = (nm, cls) => ({ n: byName[nm] || 0, d: total, l: App.label(nm), bar: [byName[nm] || 0, denom, cls] });
  return ui.band({ kicker: t('cvTblBandKickerTpl', { kind: kindN(c.baseId), rows: m.rows.length, peers: peerN }), title: '담보 비교표의 비교 결과', sc: 'base',
    stats: [st('우체국 나음', 'gold'), st('우체국에만 있음', 'gold'), st('우체국 못함', ''), st('우체국에 없음', 'other')],
    note: t('cvTblBandNoteTpl', { total, bothNone: App.label(BOTH_NONE_TEXT) }) });
}

function payHTML(text, hasExtra) {
  if (!hasExtra) return esc(text);
  const s = String(text);
  const m = s.match(/^(.*\s)(\S+)$/);
  return m
    ? `${esc(m[1])}<span class="pv-nw">${esc(m[2])}<i class="pv-x" aria-hidden="true"></i></span>`
    : `<span class="pv-nw">${esc(s)}<i class="pv-x" aria-hidden="true"></i></span>`;
}

function compCell(row, k, vid) {
  const c = row.cells[k];
  if (has(c)) {
    const b = repOf(c);
    const extra = [c.n > 1 ? `같은 담보 급부 ${c.n}개 가운데 대표 급부` : '', c.o ? t('cvCellRepOtherTpl', { n: c.o }) : '', c.w ? t('cvCellMapWaitTpl', { w: c.w }) : ''].filter(Boolean).join(', ');
    return `<td class="cv-c k${k}" data-l="${esc(orgN(vid))}"><span class="cv-v${extra ? ' has-x' : ''}"${extra ? ` title="${esc(extra)}"` : ''}><span class="pv num">${payHTML(payText(b), !!extra)}</span><span class="wv num">${esc(waitText(b.wait))}</span><span class="rv num">${esc(redShort(b.red, b))}</span></span></td>`;
  }
  const emptyTxt = c && c.w ? t('cvCellWaitTpl', { w: c.w }) : c && c.c ? t('cvCellNoneCoverTpl', { kind: txt.josa(c.c[0], '으로') }) : '없음';
  return `<td class="cv-c k${k}" data-l="${esc(orgN(vid))}"><span class="cv-x${c && c.w ? ' wait' : ''}">${esc(emptyTxt)}</span></td>`;
}
function stickyVerdictCellHTML(r, m, pIdxs) {
  if (!pIdxs.length) return `<span class="cv-both">${esc(App.t('condPeerNone'))}</span>`;
  if (pIdxs.length <= 3) {
    return `<span class="cv-vds-list">${pIdxs.map(i => {
      const v = verdFor(r, m, i, pIdxs);
      return `<span class="cv-vds-it"><span class="cv-vds-o">${esc(orgN(m.cols[i + 1]))}</span>${chip(v)}</span>`;
    }).join('')}</span>`;
  }
  const countsByName = new Map();
  const chipByName = new Map();
  pIdxs.forEach(i => {
    const v = r.verd[i];
    const nm = v ? v.name : BOTH_NONE_TEXT;
    countsByName.set(nm, (countsByName.get(nm) || 0) + 1);
    if (v && !chipByName.has(nm)) chipByName.set(nm, v.kind);
  });
  const orderList = (CV && Array.isArray(CV['판정차례']) && CV['판정차례'].length)
    ? CV['판정차례']
    : ['우체국 나음', '우체국 못함', '같음', '우열을 매기지 않음', '우체국에만 있음', '우체국에 없음', '검토 대기', '판정 보류', BOTH_NONE_TEXT];
  const onlyNm = [...chipByName].find(([, k]) => k === 'only');
  const allOnly = ((onlyNm && countsByName.get(onlyNm[0])) || 0) === pIdxs.length && pIdxs.length > 0;
  const parts = [];
  orderList.forEach(nm => {
    const cnt = countsByName.get(nm) || 0;
    if (!cnt) return;
    if (chipByName.get(nm) === 'only') {
      if (allOnly) parts.push(ui.verdict('only', t('cvVerdictCntTpl', { nm: App.label('우체국에만 있음'), n: fmt(cnt) })));
      else parts.push(`<span class="tag">${esc(t('cvVerdictCntTpl', { nm: App.label('상대에 없음'), n: fmt(cnt) }))}</span>`);
    } else if (nm === BOTH_NONE_TEXT) {
      parts.push(`<span class="tag">${esc(t('cvVerdictCntTpl', { nm: App.label(BOTH_NONE_TEXT), n: fmt(cnt) }))}</span>`);
    } else {
      parts.push(ui.verdict(chipByName.get(nm) || 'unknown', t('cvVerdictCntTpl', { nm: App.label(nm), n: fmt(cnt) })));
    }
  });
  return `<span class="cv-vds-list is-wrap">${parts.join(' ')}</span>`;
}

function tableRows(c) {
  const m = model(c.baseId);
  const pIdxs = peerIdxOf(m, c);
  const colIdxs = [0].concat(pIdxs.map(i => i + 1));
  const manyOrgs = colIdxs.length >= 4;
  const colSpan = manyOrgs ? (2 + colIdxs.length) : (2 + colIdxs.length + pIdxs.length);
  let rows = m.rows;
  if (fGroup) rows = rows.filter(r => r.major === fGroup);
  if (diffOnly) rows = rows.filter(r => pIdxs.some(i => { const v = verdFor(r, m, i, pIdxs); return v && v.kind !== 'same'; }));
  let html = '', last = '';
  const cnt = {};
  rows.forEach(r => { cnt[r.major] = (cnt[r.major] || 0) + 1; });
  const pSet = new Set(c.activePeerOrgs || []);
  rows.forEach(r => {
    if (r.major !== last) {
      last = r.major;
      html += `<tr class="cv-gh no-copy"><th colspan="${colSpan}" scope="colgroup"><span class="cv-gh-pin"><span class="cv-ghn">${esc(r.major)}</span> <span class="num">${cnt[r.major]}</span>${esc(t('cvRowUnit'))}</span></th></tr>`;
    }
    const flag = r.pts.some(p => p['원문대조'] && (c.peerScope === 'all' || (p['관련기관코드'] || []).some(o => pSet.has(o)))) ? ui.flag() : '';
    if (manyOrgs) {
      html += `<tr class="pick" data-pick="s:${esc(r.sid)}" tabindex="0" aria-label="${esc(`${stdN(r.sid)}. 근거 보기`)}">
        <td class="cv-n">${flag}<span class="nm">${esc(stdN(r.sid))}</span><span class="sub">${esc(r.type)}</span></td>
        ${colIdxs.map(k => compCell(r, k, m.cols[k])).join('')}
        <td class="cv-vd cv-vd-sticky">${stickyVerdictCellHTML(r, m, pIdxs)}${ui.RCHEV}</td></tr>`;
    } else {
      html += `<tr class="pick" data-pick="s:${esc(r.sid)}" tabindex="0" aria-label="${esc(`${stdN(r.sid)}. 근거 보기`)}">
        <td class="cv-n">${flag}<span class="nm">${esc(stdN(r.sid))}</span><span class="sub">${esc(r.type)}</span></td>
        ${colIdxs.map(k => compCell(r, k, m.cols[k])).join('')}
        ${pIdxs.map(i => { const v = verdFor(r, m, i, pIdxs); return `<td data-l="${esc(t('cvPeerCmpTpl', { peer: txt.josa(orgN(m.cols[i + 1]), '과') }))}" class="cv-vd${v && v.kind === 'better' ? ' vl-better' : v && v.kind === 'worse' ? ' vl-worse' : ''}">${chip(v)}</td>`; }).join('')}
        <td class="cv-ch" aria-hidden="true">${ui.IC.chevR}</td></tr>`;
    }
  });
  return { html, n: rows.length, total: m.rows.length, manyOrgs };
}
function tableHTML(c) {
  const m = model(c.baseId);
  const B = CV && CV.b[c.baseId];
  if (!m || !B) return `<section class="panel"><p class="placeholder">${esc(t('cvNoDataTable'))}</p></section>`;
  const pIdxs = peerIdxOf(m, c);
  const colIdxs = [0].concat(pIdxs.map(i => i + 1));
  const manyOrgs = colIdxs.length >= 4;
  const peerN = pIdxs.length;
  const totCells = m.rows.length * peerN;
  const groups = [...new Set(m.rows.map(r => r.major))];
  const tr = tableRows(c);
  const { order, byName } = sumVerdictSummary(B, c);
  const chipNames = order.filter(nm => nm !== BOTH_NONE_TEXT);
  const sumChipsHTML = chipNames.map(nm => `${ui.verdict(chipKindByName(nm), nm)} <b class="num" data-sum-name="${esc(nm)}">${byName[nm] || 0}</b>`).join(' ');
  const head2 = '<span class="cv-v hd"><span class="pv">지급</span><span class="wv">면책</span><span class="rv">감액</span></span>';
  const twHintTxt = (innerWidth <= 640 || !manyOrgs)
    ? '담보 열은 고정되고, 회사 및 비교 결과 열을 좌우로 밀어 확인합니다.'
    : '담보와 비교 결과 열은 고정되고, 가운데 회사 열을 좌우로 넘겨 확인합니다.';
  const scrollBarHTML = `<div class="cv-tw-bar no-print" id="cv-tw-bar" hidden>
    <span class="cv-tw-hint" id="cv-tw-hint">${esc(twHintTxt)}</span>
    <span class="cv-tw-btns">
      <button type="button" class="btn sm ghost" id="cv-scroll-l" data-act="cv-scroll-l" disabled>${ui.IC.chevL}<span>왼쪽 회사 열</span></button>
      <button type="button" class="btn sm ghost" id="cv-scroll-r" data-act="cv-scroll-r"><span>오른쪽 회사 열</span>${ui.IC.chevR}</button>
    </span>
  </div>`;
  const theadHTML = manyOrgs
    ? `<thead><tr><th scope="col" rowspan="2" class="cv-n">담보</th>${colIdxs.map(k => { const v = m.cols[k]; return `<th scope="col" class="cv-c k${k}" title="${esc(fullN(v))}">${esc(orgN(v))} <span class="sub">${esc(txt.shortName(kindN(v)).short)}</span>${k ? '' : ' ' + ui.tag('기준')}</th>`; }).join('')}
        <th scope="col" class="cv-vd cv-vd-sticky" rowspan="2">비교 결과<br><span class="sub">우체국 기준</span></th></tr>
        <tr class="cv-h2">${colIdxs.map(k => `<th scope="col" class="cv-c k${k}">${head2}</th>`).join('')}</tr></thead>`
    : `<thead><tr><th scope="col" rowspan="2" class="cv-n">담보</th>${colIdxs.map(k => { const v = m.cols[k]; return `<th scope="col" class="cv-c k${k}" title="${esc(fullN(v))}">${esc(orgN(v))} <span class="sub">${esc(txt.shortName(kindN(v)).short)}</span>${k ? '' : ' ' + ui.tag('기준')}</th>`; }).join('')}
        ${pIdxs.map(i => { const v = m.cols[i + 1]; return `<th scope="col" class="cv-vd" rowspan="2">${esc(t('cvPeerCmpTpl', { peer: txt.josa(orgN(v), '과') }))}<br><span class="sub">우체국 기준</span></th>`; }).join('')}<th rowspan="2" class="cv-ch"><span class="sr">${esc(t('cvColSelectSr'))}</span></th></tr>
        <tr class="cv-h2">${colIdxs.map(k => `<th scope="col" class="cv-c k${k}">${head2}</th>`).join('')}</tr></thead>`;
  return `${tableBand(c, m, byName, peerN)}<section class="panel tbl-wrap cv-tb" id="cover-table" aria-labelledby="cover-table-h">
    <div class="panel-h"><div><span class="k">${ui.scope('base')} 표준담보마다 대표 급부끼리, 우체국 기준</span><h2 id="cover-table-h">담보 비교표</h2></div>
      <div class="r"><span class="live">${ui.btn(t('cvCopyTableBtn'), { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="cv-copy-table"' })}${ui.btn('인쇄', { sm: true, ghost: true, icon: 'print', attrs: 'data-print="cover-table" data-title="담보 비교표"' })}</span></div></div>
    <div class="cv-tools">
      <div class="cv-seg" role="group" aria-label="${esc(t('cvMajorFltAria'))}">
        <button type="button" class="cv-sb" data-act="cv-group" data-v="" aria-pressed="${!fGroup}">전체</button>
        ${groups.map(g => `<button type="button" class="cv-sb" data-act="cv-group" data-v="${esc(g)}" aria-pressed="${fGroup === g}">${esc(g)}</button>`).join('')}
      </div>
      <button type="button" class="sw" role="switch" aria-checked="${diffOnly}" data-act="cv-diff"><i></i>${esc(t('cvDiffOnlyBtn'))}</button>
      <span class="cv-cnt" aria-live="polite">${esc(tr.n === tr.total ? t('cvRowCntAllTpl', { total: tr.total }) : t('cvRowCntPartTpl', { total: tr.total, n: tr.n }))}</span>
    </div>
    <div class="cv-sum">${esc(t('cvSumCellsTpl', { tot: totCells, rows: m.rows.length, peers: peerN }))}: ${sumChipsHTML} <span class="note">나머지 <b class="num" data-sum-name="${esc(BOTH_NONE_TEXT)}">${byName[BOTH_NONE_TEXT] || 0}</b>${esc(t('cvSumRestSuffixTpl', { bothNone: App.label(BOTH_NONE_TEXT) }))}</span></div>
    ${scrollBarHTML}
    <div class="cv-tw" id="cover-tw"><table class="tbl cv-t ${manyOrgs ? 'is-many-orgs' : 'is-compact-orgs'}" id="cover-tbl">
      ${theadHTML}
      <tbody>${tr.html}</tbody></table></div>
    <div class="panel-f">${esc(t('cvTblFoot'))}</div>
  </section>`;
}
function syncCoverTwScroll(root) {
  const tw = (root || document).querySelector('#cover-tw');
  const bar = (root || document).querySelector('#cv-tw-bar');
  if (!tw) return;
  const maxL = Math.max(0, tw.scrollWidth - tw.clientWidth);
  const hasOver = maxL > 2;
  const moreL = hasOver && tw.scrollLeft > 2;
  const moreR = hasOver && tw.scrollLeft < maxL - 2;
  tw.classList.toggle('has-more-l', moreL);
  tw.classList.toggle('has-more-r', moreR);
  if (bar) {
    bar.hidden = !hasOver;
    const hint = bar.querySelector('#cv-tw-hint');
    if (hint) {
      const tbl = tw.querySelector('#cover-tbl');
      const manyOrgs = !!(tbl && tbl.classList.contains('is-many-orgs'));
      hint.textContent = (innerWidth <= 640 || !manyOrgs)
        ? '담보 열은 고정되고, 회사 및 비교 결과 열을 좌우로 밀어 확인합니다.'
        : '담보와 비교 결과 열은 고정되고, 가운데 회사 열을 좌우로 넘겨 확인합니다.';
    }
    const btnL = bar.querySelector('#cv-scroll-l');
    const btnR = bar.querySelector('#cv-scroll-r');
    if (btnL) btnL.disabled = !moreL;
    if (btnR) btnR.disabled = !moreR;
  }
}
function bindCoverTw(root) {
  const tw = root && root.querySelector('#cover-tw');
  if (!tw) return;
  if (!tw._bound) {
    tw._bound = true;
    tw.addEventListener('scroll', () => syncCoverTwScroll(root), { passive: true });
  }
  syncCoverTwScroll(root);
  requestAnimationFrame(() => syncCoverTwScroll(root));
}
function refreshTable(body, c) {
  const tb = body.querySelector('#cover-tbl tbody');
  if (!tb) return;
  const tr = tableRows(c);
  tb.innerHTML = tr.html;
  body.querySelectorAll('[data-act="cv-group"]').forEach(b => b.setAttribute('aria-pressed', String((b.dataset.v || null) === fGroup)));
  const sw = body.querySelector('[data-act="cv-diff"]'); if (sw) sw.setAttribute('aria-checked', String(diffOnly));
  const cn = body.querySelector('.cv-cnt'); if (cn) cn.textContent = tr.n === tr.total ? t('cvRowCntAllTpl', { total: tr.total }) : t('cvRowCntPartTpl', { total: tr.total, n: tr.n });
  const key = App.state.sel.cover;
  tb.querySelectorAll('[data-pick]').forEach(el => el.classList.toggle('is-sel', el.dataset.pick === key));
  syncCoverTwScroll(body);
}

function copyJourney() {
  const c = App.ctx();
  const { j, cols } = journeyData(c);
  const rows = [];
  j['행'].forEach(g => cols.forEach(x => rows.push([g, x['이름'], ...STEPS.map(s => (x['칸'][g] || {})[s] || 0), STEPS.reduce((a, s) => a + ((x['칸'][g] || {})[s] || 0), 0)])));
  cols.forEach(x => rows.push(['단계 합계', x['이름'], ...STEPS.map(s => x['합계'][s] || 0), x['전체'] - (x['기타'] || 0)]));
  cols.forEach(x => rows.push(['기타(주요 단계 밖)', x['이름'], '', '', '', '', '', x['기타'] || 0]));
  App.copyRows(['보장 대분류', '종형', ...STEPS, '합계'], rows, { title: t('cvCopyJourneyTitle') });
}
function copyCaution() {
  const c = App.ctx();
  const rows = scopedCaution(c).map(x => [x['종류'], x['담보'], (x['상대종형ID'] || []).map(fullN).join(', '), App.label('우열을 매기지 않음'), x['문장'],
    (x['근거'] || []).map(g => `${orgN(g['종형ID'])} ${txt.pageText(g['문서'], g['쪽'])}${g['구분'] ? `(${g['구분']})` : ''}`).join('; ')]);
  App.copyRows(['종류', '담보', t('cvCopyCauColPeer'), '비교 결과', '문장', '근거'], rows, { title: t('cvCautionListTitle') });
}
function copyTable() {
  const c = App.ctx();
  const m = model(c.baseId);
  const pIdxs = peerIdxOf(m, c);
  const colIdxs = [0].concat(pIdxs.map(i => i + 1));
  let rows = m.rows;
  if (fGroup) rows = rows.filter(r => r.major === fGroup);
  if (diffOnly) rows = rows.filter(r => pIdxs.some(i => { const v = verdFor(r, m, i, pIdxs); return v && v.kind !== 'same'; }));
  const head = ['보장 대분류', '담보', '급부유형'];
  colIdxs.forEach(k => { const v = m.cols[k]; head.push(`${orgN(v)} 지급`, `${orgN(v)} 면책`, `${orgN(v)} 감액`); });
  pIdxs.forEach(i => { const v = m.cols[i + 1]; head.push(t('cvCopyCmpColTpl', { peer: txt.josa(orgN(v), '과') })); });
  head.push(t('cvCopyWhyCol'));
  App.copyRows(head, rows.map(r => {
    const out = [r.major, stdN(r.sid), r.type];
    colIdxs.forEach(k => {
      const c2 = r.cells[k], b = repOf(c2);
      if (b) out.push(payText(b), waitText(b.wait), redShort(b.red, b));
      else out.push(c2 && c2.w ? t('cvCellWaitTpl', { w: c2.w }) : c2 && c2.c ? `없음(${c2.c[0]})` : '없음', '', '');
    });
    pIdxs.forEach(i => out.push(chipText(verdFor(r, m, i, pIdxs))));
    out.push(pIdxs.map(i => { const v = verdFor(r, m, i, pIdxs); return v && v.why ? `${orgN(m.cols[i + 1])}: ${v.why}` : ''; }).filter(Boolean).join(' / '));
    return out;
  }), { title: `담보 비교표${fGroup ? ` (${fGroup})` : ''}${diffOnly ? t('cvCopyDiffSuffix') : ''}` });
}

function concl(c) {
  const bRa = ((c.base && c.base['브리핑']) || []).find(x => x['줄'] === '라');
  if (c.peerScope === 'all' && bRa) return `<p class="concl">${esc(bRa['문장'])}</p>`;
  const pSet = new Set(c.activePeerOrgs || []);
  const sp = (c.peerScope === 'all' ? scopedPairs(c.baseId, null) : scopedPairs(c.baseId, pSet)) || { total: 0, wait: 0, cmp: 0 };
  const j = journeyData(c).cols[0];
  const cau = scopedCaution(c);
  return `<p class="concl">${esc(t('cvConclTpl', { total: sp.total, cmp: sp.cmp, wait: sp.wait, kind: kindN(c.baseId), all: j['전체'], steps: STEPS.map(s => `${s} ${j['합계'][s] || 0}`).join(', '), cau: cau.length }))}</p>`;
}
function refNote(c) {
  const parts = [];
  if (!c.isRef) parts.push(t('cvRefCondTpl', { cond: App.condSegOnly() }));
  if (c.st.renewal) parts.push(t('cvRefRenewal'));
  return parts.length ? `<p class="cv-ref">${esc(parts.join(' '))}</p>` : '';
}

function renderFullTablesModal(c) {
  const html = `<div id="view-cover-modal" class="cv-modal-root">
    ${concl(c)}${refNote(c)}
    <div class="dm-sec">${journeyHTML(c)}</div>
    <div class="dm-sec">${midBand(c)}<div class="cv-mid">${cautionHTML(c)}${pendingHTML(c)}</div></div>
    <div class="dm-sec">${tableHTML(c)}</div>
  </div>`;
  return {
    kicker: App.TAB_NAME.cover,
    title: t('cvModalTitle'),
    badges: [ui.scope('base'), ui.fullScopeTag()].filter(Boolean),
    actions: ui.btn('비교표 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="cv-copy-table"' }),
    html,
    after(body) { bindCoverTw(body); },
  };
}

function conclusion(c) {
  if (c.peerScope !== 'all') {
    const pSet = new Set(c.activePeerOrgs || []);
    const sp = scopedPairs(c.baseId, pSet) || { total: 0, wait: 0, cmp: 0 };
    const j = journeyData(c).cols[0];
    const cau = scopedCaution(c);
    return {
      text: t('cvConclScopedTpl', { total: sp.total, cmp: sp.cmp, wait: sp.wait, kind: kindN(c.baseId), all: j['전체'], cau: cau.length }),
      flag: '',
      scoped: true,
    };
  }
  const bRa = ((c.base && c.base['브리핑']) || []).find(x => x['줄'] === '라');
  if (bRa) return { text: App.firstSentence(bRa['문장']), flag: '' };
  return { text: '', flag: '' };
}

function actions() {
  return [
    ui.btn(App.t('actModeTable'), { sm: true, ghost: true, icon: 'table', attrs: 'id="cv-btn-tbl" data-cv-modal="1"' }),
    ui.btn('비교표 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="cv-copy-table"' }),
  ].join('');
}

document.addEventListener('click', e => {
  const mb = e.target.closest && e.target.closest('[data-cv-modal]');
  if (mb) {
    e.stopPropagation();
    App.openModal({ trigger: mb, render: renderFullTablesModal });
    return;
  }
  const flt = e.target.closest && e.target.closest('[data-cv-flt]');
  if (flt) {
    e.stopPropagation();
    const k = flt.dataset.cvFlt;
    if (activeFilters.has(k)) activeFilters.delete(k);
    else activeFilters.add(k);
    if (App.state.tab === 'cover') {
      const stageEl = document.getElementById('cv-pillar-stage');
      if (stageEl) applyCoverFiltersInPlace(stageEl);
      else if (lastStageHost) renderStage(lastStageHost, App.ctx());
    }
    return;
  }
  const pgBtn = e.target.closest && e.target.closest('[data-cv-page]');
  if (pgBtn) {
    e.stopPropagation();
    if (pgBtn.disabled) return;
    const c = App.ctx();
    const curStep = curStepByBase[c.baseId] || STEPS[0];
    switchCoverStep(curStep, { page: +pgBtn.dataset.cvPage, animate: true });
    return;
  }
  const stBtn = e.target.closest && e.target.closest('[data-cv-step]');
  if (stBtn) {
    e.stopPropagation();
    const nextStep = stBtn.dataset.cvStep;
    const c = App.ctx();
    if (curStepByBase[c.baseId] !== nextStep) {
      switchCoverStep(nextStep, { page: 0, animate: true });
    }
    return;
  }
  const a = e.target.closest && e.target.closest('[data-act]');
  if (a) {
    const act = a.dataset.act;
    const dmBody = document.getElementById('dm-body');
    if ((act === 'cv-scroll-l' || act === 'cv-scroll-r') && dmBody) {
      e.stopPropagation();
      const tw = dmBody.querySelector('#cover-tw');
      const stepX = innerWidth <= 640 ? 200 : 440;
      if (tw) tw.scrollBy({ left: act === 'cv-scroll-l' ? -stepX : stepX, behavior: App.motionOn() ? 'smooth' : 'auto' });
      return;
    }
    if (act === 'cv-mob-nav') {
      e.stopPropagation();
      if (a.disabled || !a.dataset.sid) return;
      const targetSid = a.dataset.sid;
      ensureSidInView(targetSid, App.ctx());
      App.select('s:' + targetSid, { reveal: false });
      const evBody = document.getElementById('ev-body');
      if (evBody) evBody.scrollTop = 0;
      return;
    }
    if (act === 'cv-group' && dmBody) { e.stopPropagation(); fGroup = a.dataset.v || null; refreshTable(dmBody, App.ctx()); return; }
    if (act === 'cv-diff' && dmBody) { e.stopPropagation(); diffOnly = !diffOnly; refreshTable(dmBody, App.ctx()); return; }
    if (act === 'cv-copy-journey') { e.stopPropagation(); copyJourney(); return; }
    if (act === 'cv-copy-caution') { e.stopPropagation(); copyCaution(); return; }
    if (act === 'cv-copy-table') { e.stopPropagation(); copyTable(); return; }
    if (act === 'cv-goto') {
      e.stopPropagation();
      const sid = a.dataset.sid;
      App.closeModal(false, true);
      if (App.state.tab !== 'cover') App.go('cover');
      setTimeout(() => {
        ensureSidInView(sid, App.ctx());
        App.select('s:' + sid, { focus: true });
      }, 30);
    }
  }
});

document.addEventListener('keydown', e => {
  if (App.state.tab !== 'cover') return;
  const slot = e.target.closest && e.target.closest('#cv-zoom-box .cvp-slot[data-sid]');
  if (!slot || !['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(e.key)) return;
  const zoomBox = document.getElementById('cv-zoom-box');
  if (!zoomBox) return;
  const slots = Array.from(zoomBox.querySelectorAll('.cvp-slot[data-sid]'));
  const idx = slots.indexOf(slot);
  if (idx < 0) return;
  e.preventDefault();
  if (e.key === 'Home') {
    slots.forEach((s, k) => { s.tabIndex = k === 0 ? 0 : -1; });
    slots[0].focus();
    return;
  }
  if (e.key === 'End') {
    const last = slots.length - 1;
    slots.forEach((s, k) => { s.tabIndex = k === last ? 0 : -1; });
    slots[last].focus();
    return;
  }
  const dir = e.key === 'ArrowRight' ? 1 : -1;
  const nextIdx = idx + dir;
  if (nextIdx >= 0 && nextIdx < slots.length) {
    slots.forEach((s, k) => { s.tabIndex = k === nextIdx ? 0 : -1; });
    slots[nextIdx].focus();
    return;
  }
  // 단계 안의 쪽 끝이나 단계 끝에 닿으면 다음/앞 쪽 또는 옆 단계로 이동
  const c = App.ctx();
  const m = model(c.baseId);
  if (!m) return;
  const curStep = curStepByBase[c.baseId] || STEPS[0];
  const stageEl = document.getElementById('cv-pillar-stage');
  const stRows = m.rows.filter(r => r.type === curStep);
  const lay = measureZoomLayout(stageEl, stRows, domainOrderOf(c));
  const curPage = curPageByStep[c.baseId + '|' + curStep] || 0;
  if (dir > 0 && curPage < lay.pages.length - 1) {
    switchCoverStep(curStep, { page: curPage + 1, animate: true, focusEdge: 'first' });
    return;
  }
  if (dir < 0 && curPage > 0) {
    switchCoverStep(curStep, { page: curPage - 1, animate: true, focusEdge: 'last' });
    return;
  }
  const nonEmptySteps = STEPS.filter(stNm => m.rows.some(r => r.type === stNm));
  const sPos = nonEmptySteps.indexOf(curStep);
  if (sPos < 0 || nonEmptySteps.length < 2) return;
  const nextStep = nonEmptySteps[(sPos + dir + nonEmptySteps.length) % nonEmptySteps.length];
  let targetPage = 0;
  if (dir < 0) {
    const prevRows = m.rows.filter(r => r.type === nextStep);
    const prevLay = measureZoomLayout(stageEl, prevRows, domainOrderOf(c));
    targetPage = Math.max(0, prevLay.pages.length - 1);
  }
  switchCoverStep(nextStep, { page: targetPage, animate: true, focusEdge: dir > 0 ? 'first' : 'last' });
});

function pick(key, c) {
  if (key.startsWith('s:')) {
    const sid = key.slice(2);
    const sig = `${c.baseId}|${key}`;
    if (sig !== lastSyncedSelKey) {
      lastSyncedSelKey = sig;
      ensureSidInView(sid, c);
    }
    return rowEvidence(c, sid, 'row');
  }
  if (key.startsWith('c:')) {
    const sid = key.slice(2);
    const sig = `${c.baseId}|${key}`;
    if (sig !== lastSyncedSelKey) {
      lastSyncedSelKey = sig;
      ensureSidInView(sid, c);
    }
    return rowEvidence(c, sid, 'caution');
  }
  if (key.startsWith('j:')) return journeyPick(c, key);
  return null;
}

function focus(key) {
  if (key === 'journey' || key === 'caution' || key === 'table') {
    App.openModal({
      trigger: document.getElementById('cv-btn-tbl'),
      render: c => {
        const spec = renderFullTablesModal(c);
        const origAfter = spec.after;
        spec.after = body => {
          if (origAfter) origAfter(body);
          const id = key === 'journey' ? 'cover-journey' : key === 'caution' ? 'cover-caution' : 'cover-table';
          const el = body.querySelector('#' + id);
          if (el) App.scrollInZone(el, 'auto');
        };
        return spec;
      },
    });
    return;
  }
  if (key && key.startsWith('s:')) {
    ensureSidInView(key.slice(2), App.ctx());
    App.select(key, { focus: true });
  } else if (key && model(App.state.base) && model(App.state.base).byId[key]) {
    ensureSidInView(key, App.ctx());
    App.select('s:' + key, { focus: true });
  }
}

function enter(body) {
  const stageEl = body && body.querySelector('#cv-pillar-stage');
  if (!stageEl) return;
  positionOvBracket(stageEl, false);
  if (!App.motionOn()) return;
  stageEl.classList.remove('cvp-anim');
  void stageEl.offsetWidth;
  stageEl.classList.add('cvp-anim');
  clearTimeout(stageEl._t);
  stageEl._t = setTimeout(() => stageEl.classList.remove('cvp-anim'), 700);
}

App.on('aim', aimEl => { if (App.state.tab === 'cover') syncCoverAimHot(aimEl); });
App.on('select', tab => {
  if (tab !== 'cover') return;
  userScrolledZc = false;
  const curSel = App.state.sel.cover || '';
  if (!curSel) lastSyncedSelKey = `${App.state.base}|`;
  const stageEl = document.getElementById('cv-pillar-stage');
  syncCoverSelectionAndFilter(stageEl);
  scrollSelectedBarIntoCenter();
  requestAnimationFrame(() => scrollSelectedBarIntoCenter());
});
App.on('ev-settled', tab => {
  if (tab !== 'cover') return;
  scrollSelectedBarIntoCenter();
  requestAnimationFrame(scrollSelectedBarIntoCenter);
});
App.on('resize', () => {
  cachedHostW = 0;
  const dm = document.getElementById('dm-body');
  if (dm) syncCoverTwScroll(dm);
  if (App.state.tab !== 'cover' || !lastStageHost) return;
  renderStage(lastStageHost, App.ctx());
});

// 탭 5 와 core.js, tab1.js 가 쓰는 것
App.cover = {
  rawB: baseId => (CV && CV.b ? CV.b[baseId] || null : null),
  rawMeta: () => ({ table: (CV && CV['판정표']) || {}, order: (CV && CV['판정차례']) || [] }),
  model, scopedPairs, chip, chipText, verdFor,
  verdictOf: (baseId, sid) => { const m = model(baseId); const r = m && m.byId[sid]; return r ? r.verd : null; },
  peerVerdicts: (baseId, sid, c) => {
    const m = model(baseId); const r = m && m.byId[sid];
    if (!m || !r) return null;
    const pIdxs = peerIdxOf(m, c || App.ctx());
    return pIdxs.map(i => ({ peer: m.cols[i + 1], v: verdFor(r, m, i, pIdxs) }));
  },
  rel: drawRel, relLegend, hasRow: (baseId, sid) => { const m = model(baseId); return !!(m && m.byId[sid]); },
  peerCols: baseId => { const m = model(baseId); return m ? m.cols : []; },
  switchStep: switchCoverStep,
};

App.registerTab({ id: 'cover', layout: 'band', kicker: '상세 비교, 담보', renderStage, conclusion, pick, actions, copySummary: copyTable, focus, enter });
