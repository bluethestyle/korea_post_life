/* 탭 6 관계 그래프(tab6.js):
   - proto_src/graph/graph.json(#graph-data)을 쉬는 시간이나 처음 열 때 읽고, 수는 summary, 엣지 속성, 집합의 크기에서만 읽는다.
   - 보기 방식 셋: 담보별 연결(보유 조합 그룹 네트워크), 종형 구성(동심 타원 방사형), 시장 동향(회사별 격자). 요청 38.
*/
(function () {
  const { ui, txt, t } = App;
  const { esc, fmt } = ui;

  // 노드와 엣지 종류는 번호가 아니라 graph.json 의 자료 이름으로 찾는다(ensureGraph 에서 채움)
  let NK = {};
  let EK = {};

  let G = null;
  let lastLeftEl = null;
  let lastCenterEl = null;
  let lastScopeSig = '';
  let edgeDrawRaf = 0;

  const state = {
    preset: 'cover',     // 'cover' | 'variant' | 'news'
    varIdx: null,        // 종형 구성 보기의 종형 노드 번호
    vf: { renew: null, main: false, dom: null, rev: false }, // 종형 구성 필터(6절 9, 10번)
    nf: 'week',          // 시장 동향 필터: 'week' 이번 주차 통과 | 'allweek' 전체 주차 통과 | 'all' 전체
    selNode: null,       // node index
    selEdge: null,       // edge key ('e:12' | 'vb:v:d' | 'vs:v:s')
    focusNode: null,     // roving tabindex node index
    selStd: null,        // 담보별 연결에서 선택한 표준담보 노드 번호
    selGroup: null,      // 담보별 연결에서 선택한 그룹 키
    expSlot: null,       // 요약 노드로 접은 타사 종형 가운데 펼친 슬롯(4.3의 6번)
    filter: null,        // 'f:<판정 필터>' | 'cls:<보유 구분>' | 'dom:<보장 대분류>'
    query: '',
  };

  let undoStack = [];
  let trail = [];
  let renderedEdges = new Map(); // edgeKey -> descriptor
  let hoveredEdgeEl = null;

  function ensureGraph() {
    if (G) return G;
    const scriptEl = document.getElementById('graph-data');
    let raw = { snapshot_at: '', kinds: [], ekinds: [], nodes: [], edges: [], keys: [] };
    if (scriptEl && scriptEl.textContent.trim()) {
      try { raw = JSON.parse(scriptEl.textContent); } catch (e) { console.error(e); }
    }
    App.addLabels(raw['표시명']);
    // 종류는 번호가 아니라 자료 이름(kinds, ekinds)으로 찾고, 화면 이름은 kindLabels, ekindLabels 에서 읽는다
    const kinds = raw.kinds || [];
    const ekinds = raw.ekinds || [];
    const kindLabels = raw.kindLabels && raw.kindLabels.length === kinds.length ? raw.kindLabels : kinds;
    const ekindLabels = raw.ekindLabels && raw.ekindLabels.length === ekinds.length ? raw.ekindLabels : ekinds;
    NK = Object.fromEntries(kinds.map((nm, i) => [nm, i]));
    EK = Object.fromEntries(ekinds.map((nm, i) => [nm, i]));
    const keys = raw.keys || [];
    const dec = obj => {
      const out = {};
      if (!obj) return out;
      for (const [k, v] of Object.entries(obj)) out[keys[+k] || k] = v;
      return out;
    };
    const N = (raw.nodes || []).map((a, i) => ({
      i,
      id: a[0],
      k: a[1],
      l: a[2],
      o: a[3] || null,
      p: dec(a[4]),
    }));
    // edges(판매~발표)와 edges2(보유, 결합제약, 개정 따위)를 함께 색인한다
    const E = (raw.edges || []).concat(raw.edges2 || []).map((a, i) => ({
      i,
      s: a[0],
      t: a[1],
      k: a[2],
      p: dec(a[3]),
    }));

    const kOrg = NK['회사'], kVar = NK['종형'], kRider = NK['특약'], kBen = NK['급부'], kStd = NK['표준담보'], kDom = NK['보장 대분류'];
    const eInc = EK['포함'], eMap = EK['매핑'], eCls = EK['분류'], eRel = EK['담보 관계'], eHeld = EK['보유'];

    const byId = new Map();
    const orgNames = {};
    N.forEach(n => {
      byId.set(n.id, n.i);
      if (n.k === kOrg && n.o) orgNames[n.o] = n.l;
    });

    const adj = N.map(() => []);
    const varRiders = new Map();
    const riderVars = new Map();
    const riderBens = new Map();
    const benRiders = new Map();
    const benStds = new Map();
    const stdBens = new Map();
    const stdDom = new Map();
    const domStds = new Map();
    const stdRels = new Map();
    const heldBy = new Map();   // 종형 노드 번호 -> Map(표준담보 노드 번호 -> 보유 엣지)
    const heldOf = new Map();   // 표준담보 노드 번호 -> [보유 종형 노드 번호]

    const pushArr = (map, k, v) => {
      let arr = map.get(k);
      if (!arr) { arr = []; map.set(k, arr); }
      arr.push(v);
    };

    E.forEach(e => {
      const ns = N[e.s], nt = N[e.t];
      if (!ns || !nt) return;
      adj[e.s].push({ e: e.i, j: e.t, ek: e.k, isOut: true });
      adj[e.t].push({ e: e.i, j: e.s, ek: e.k, isOut: false });
      if (e.k === eInc && ns.k === kVar && nt.k === kRider) {
        pushArr(varRiders, e.s, e.t);
        pushArr(riderVars, e.t, e.s);
      } else if (e.k === eInc && ns.k === kRider && nt.k === kBen) {
        pushArr(riderBens, e.s, e.t);
        pushArr(benRiders, e.t, e.s);
      } else if (e.k === eMap && ns.k === kBen && nt.k === kStd) {
        pushArr(benStds, e.s, { std: e.t, e: e.i });
        pushArr(stdBens, e.t, { ben: e.s, e: e.i });
      } else if (e.k === eCls && ns.k === kStd && nt.k === kDom) {
        stdDom.set(e.s, { dom: e.t, e: e.i });
        pushArr(domStds, e.t, e.s);
      } else if (e.k === eRel && ns.k === kStd && nt.k === kStd) {
        pushArr(stdRels, e.s, { other: e.t, e: e.i, dir: 'out' });
        pushArr(stdRels, e.t, { other: e.s, e: e.i, dir: 'in' });
      } else if (e.k === eHeld && ns.k === kVar && nt.k === kStd) {
        let m = heldBy.get(e.s);
        if (!m) { m = new Map(); heldBy.set(e.s, m); }
        m.set(e.t, e);
        pushArr(heldOf, e.t, e.s);
      }
    });

    G = {
      snapshotAt: raw.snapshot_at || '',
      summary: raw.summary || null,
      kinds,
      ekinds,
      kindLabels,
      ekindLabels,
      N,
      E,
      nBaseEdges: (raw.edges || []).length,
      byId,
      orgNames,
      adj,
      varRiders,
      riderVars,
      riderBens,
      benRiders,
      benStds,
      stdBens,
      stdDom,
      domStds,
      stdRels,
      heldBy,
      heldOf,
    };
    return G;
  }

  // 앞 화면이 쉬는 동안 그래프 색인을 미리 만들어 탭 전환 때 긴 작업이 생기지 않게 한다(1-10)
  setTimeout(() => {
    const warm = () => {
      if (!G && document.getElementById('graph-data')) {
        try { ensureGraph(); } catch (e) { /* */ }
      }
    };
    if (typeof requestIdleCallback === 'function') requestIdleCallback(warm, { timeout: 1500 });
    else setTimeout(warm, 120);
  }, 320);

  // 회사 이름: 그래프의 회사 노드 이름을 먼저 쓰고, 없거나 기관코드와 같으면 txt.orgShort(2절)
  function orgLabel(code) {
    if (!code) return '';
    const nm = G && G.orgNames && G.orgNames[code];
    if (nm && nm !== code) return nm;
    return txt.orgShort(code) || code;
  }

  // ---------- 담보별 연결의 자료 계층: 보유 조합 그룹(3.4), 표시(5.3), 판정 필터(5.4) ----------
  // 관계 그래프 안의 보장 대분류 차례. 자료에 없는 대분류가 생기면 끝에 붙인다(3.11)
  const DOM_ORDER = ['암보장', '뇌혈관보장', '뇌심장보장', '심장보장', '공통보장'];
  // 담보 관계 엣지는 지금 자료에서 도착 노드가 넓은 담보다. 자료의 방향이 바뀌면 이 값 하나만 바꾼다
  const REL_TARGET_IS_WIDE = true;
  const CAUSE_REL = '관계 담보로 덮음';
  const MARKS = ['sole', 'peer-rel', 'ours-wide', 'ours-part', 'wait'];
  // 판정 필터 다섯: 이름은 까닭 키의 표시명(App.label)으로 읽는다(5.4)
  const FILTERS = [
    { id: 'win', cause: '나음' },
    { id: 'lose', cause: '못함' },
    { id: 'diff', cause: '단정 주의' },
    { id: 'wait', cause: '검토 대기' },
    { id: 'rel', cause: CAUSE_REL },
  ];

  function domOrder(g) {
    if (g.domOrder) return g.domOrder;
    const out = DOM_ORDER.slice();
    g.N.forEach(n => { if (n.k === NK['보장 대분류'] && !out.includes(n.l)) out.push(n.l); });
    g.domOrder = out;
    return out;
  }

  function domOf(g, si) {
    const dm = g.stdDom.get(si);
    if (dm && g.N[dm.dom]) return g.N[dm.dom].l;
    return String((g.N[si] && g.N[si].p['보장대분류']) || '');
  }

  // 화면에 놓을 종형: 기준 종형과 비교 범위로 거른 비교 대상 종형(c.peerIds, 기관코드 순)
  function sceneTypes(g, c) {
    const out = [];
    const bi = g.byId.get(c.baseId);
    if (bi != null) out.push(bi);
    (c.peerIds || []).forEach(id => {
      const ni = g.byId.get(id);
      if (ni != null && !out.includes(ni)) out.push(ni);
    });
    return out;
  }

  // 타사 4개사 이상의 보유 타사 수 구간(8.1). n 타사 수, k 보유 타사 수, h = n/2 올림
  function binOf(ours, k, n) {
    const h = Math.ceil(n / 2);
    if (ours) return k === 0 ? 'only' : k === n ? 'all' : k >= h ? 'many' : 'few';
    return k === n ? 'p-all' : k >= h ? 'p-many' : k >= 2 ? 'p-few' : 'p-one';
  }
  const BIN_ORDER = ['only', 'few', 'many', 'all', 'p-all', 'p-many', 'p-few', 'p-one'];

  // 보유 엣지로 정한 (기준 종형, 비교 범위)의 담보와 보유 조합 그룹
  const sceneCache = new Map();
  function sceneOf(g, c) {
    const types = sceneTypes(g, c);
    const sig = types.join(',');
    if (sceneCache.has(sig)) return sceneCache.get(sig);
    const codes = types.map(vi => g.N[vi].o || '');
    const nPeer = Math.max(0, types.length - 1);
    const slotsOf = new Map();
    types.forEach((vi, slot) => {
      const m = g.heldBy.get(vi);
      if (!m) return;
      for (const si of m.keys()) {
        let a = slotsOf.get(si);
        if (!a) { a = []; slotsOf.set(si, a); }
        a.push(slot);
      }
    });
    const stds = Array.from(slotsOf.keys()).sort((a, b) => a - b);
    const info = new Map();
    const groupMap = new Map();
    stds.forEach(si => {
      const slots = slotsOf.get(si).slice().sort((a, b) => a - b);
      const ours = slots[0] === 0;
      const kp = slots.length - (ours ? 1 : 0);
      const cls = ours && kp === 0 ? 'only' : ours ? 'shared' : 'peer';
      const bin = nPeer > 3 ? binOf(ours, kp, nPeer) : null;
      const key = bin ? 'bin:' + bin : slots.map(s => codes[s]).join(',');
      let bens = 0;
      const per = slots.map(s => {
        const e = g.heldBy.get(types[s]).get(si);
        const p = e ? e.p : {};
        bens += +(p['급부수'] || 0);
        return { slot: s, vi: types[s], code: codes[s], e };
      });
      const it = { si, slots, ours, kp, cls, key, bin, bens, per, dom: domOf(g, si) };
      info.set(si, it);
      let grp = groupMap.get(key);
      if (!grp) {
        grp = { key, cls, bin, slots: bin ? null : slots, members: [] };
        groupMap.set(key, grp);
      }
      grp.members.push(si);
    });
    const groups = Array.from(groupMap.values()).sort((a, b) => {
      if (a.bin || b.bin) return BIN_ORDER.indexOf(a.bin) - BIN_ORDER.indexOf(b.bin);
      return a.key < b.key ? -1 : a.key > b.key ? 1 : 0;
    });
    const sc = { sig, types, codes, nPeer, stds, info, groups, groupMap };
    sceneCache.set(sig, sc);
    return sc;
  }

  // 담보 비교 탭과 같은 판정 자료(App.cover)에서 한 담보의 판정과 관련 담보 근거를 읽는다(5.2)
  const coverRowCache = new Map();
  function coverRow(baseId, sid) {
    let m = coverRowCache.get(baseId);
    if (!m) {
      m = new Map();
      const B = App.cover && App.cover.rawB(baseId);
      ((B && B.rows) || []).forEach(r => m.set(r[0], r));
      coverRowCache.set(baseId, m);
    }
    return m.get(sid) || null;
  }

  function coverOf(c, sid) {
    const cv = App.cover;
    if (!cv || !cv.hasRow(c.baseId, sid)) return null;
    const pv = cv.peerVerdicts(c.baseId, sid, c) || [];
    const row = coverRow(c.baseId, sid);
    const ours = row && row[1] && row[1][0];
    const oursRel = ours && typeof ours === 'object' && !(ours.i && ours.i.length) && ours.c ? ours.c : null;
    const cols = cv.peerCols(c.baseId) || [];
    const peerRel = peerId => {
      const k = cols.indexOf(peerId);
      const cell = k > 0 && row && row[1] ? row[1][k] : null;
      return cell && cell.c ? cell.c : null;
    };
    return { pv, row, oursRel, peerRel };
  }

  // 표시(data-gr-mark): sole, peer-rel, ours-wide, ours-part, wait(5.3)
  function marksOf(g, c, sc, si) {
    const it = sc.info.get(si);
    if (!it) return [];
    const cov = coverOf(c, g.N[si].id);
    if (!cov) return [];
    const out = [];
    if (it.cls === 'only') {
      out.push(cov.pv.some(x => x.v && x.v.cause === CAUSE_REL) ? 'peer-rel' : 'sole');
    } else if (it.cls === 'peer' && cov.oursRel) {
      if (cov.oursRel[0] === '넓은 담보') out.push('ours-wide');
      else if (cov.oursRel[0] === '부분 담보') out.push('ours-part');
    }
    if (it.per.some(x => x.e && ((+x.e.p['매핑검수대기급부수'] || 0) > 0 || (+x.e.p['추출검수대기급부수'] || 0) > 0))) out.push('wait');
    return out;
  }

  // 판정 필터: 비교 범위의 타사 가운데 1개사라도 해당하면 그 담보를 강조한다(5.4)
  function filterHit(fid, cov, marks) {
    if (fid === 'wait' && marks.includes('wait')) return true;
    if (!cov) return false;
    if (fid === 'rel' && cov.oursRel) return true;
    const table = (App.cover && App.cover.rawMeta().table) || {};
    return cov.pv.some(({ v }) => {
      if (!v) return false;
      if (fid === 'win') return v.cause === '나음';
      if (fid === 'lose') return v.cause === '못함';
      if (fid === 'diff') return !!(table[v.cause] && table[v.cause]['칩'] === 'diff');
      if (fid === 'wait') return v.cause === '검토 대기';
      if (fid === 'rel') return v.cause === CAUSE_REL;
      return false;
    });
  }

  // 한 장면의 담보마다 판정, 표시, 필터 결과를 한 번에 계산한다
  const judgeCache = new Map();
  function judgeOf(g, c, sc) {
    const sig = `${c.baseId}|${sc.sig}`;
    if (judgeCache.has(sig)) return judgeCache.get(sig);
    const per = new Map();
    const counts = Object.fromEntries(FILTERS.map(f => [f.id, 0]));
    sc.stds.forEach(si => {
      const cov = coverOf(c, g.N[si].id);
      const marks = marksOf(g, c, sc, si);
      const hits = new Set(FILTERS.filter(f => filterHit(f.id, cov, marks)).map(f => f.id));
      hits.forEach(id => { counts[id] += 1; });
      per.set(si, { cov, marks, hits });
    });
    const out = { per, counts };
    judgeCache.set(sig, out);
    return out;
  }

  function scopeSig(c) {
    return `${c.baseId}|${c.peerScope}|${(c.activePeerOrgs || []).join(',')}`;
  }

  function cloneStateSnap() {
    return JSON.stringify({
      preset: state.preset,
      varIdx: state.varIdx,
      vf: state.vf,
      nf: state.nf,
      selNode: state.selNode,
      selEdge: state.selEdge,
      focusNode: state.focusNode,
      selStd: state.selStd,
      selGroup: state.selGroup,
      expSlot: state.expSlot,
      filter: state.filter,
    });
  }


  function restoreStateSnap(rawStr) {
    const o = JSON.parse(rawStr);
    state.preset = o.preset;
    state.varIdx = o.varIdx ?? null;
    state.vf = Object.assign({ renew: null, main: false, dom: null, rev: false }, o.vf || {});
    state.nf = o.nf || 'week';
    state.selNode = o.selNode;
    state.selEdge = o.selEdge;
    state.focusNode = o.focusNode ?? null;
    state.selStd = o.selStd ?? null;
    state.selGroup = o.selGroup ?? null;
    state.expSlot = o.expSlot ?? null;
    state.filter = o.filter ?? null;
  }


  function pushUndo() {
    const s = cloneStateSnap();
    if (undoStack.length && undoStack[undoStack.length - 1] === s) return;
    undoStack.push(s);
    if (undoStack.length > 40) undoStack.shift();
    // 담보나 그룹 선택은 왼쪽 영역을 다시 그리지 않으므로 실행 취소 버튼 상태를 여기서 맞춘다
    syncLeftActive();
  }

  // sel: 담보나 그룹 선택 항목. 선택은 바로 앞의 선택 항목을 바꾸고, 선택을 풀면 빠진다(탐색 경로가 지금 상태를 보이게)
  function recordTrail(label, sel) {
    const snap = cloneStateSnap();
    const last = trail[trail.length - 1];
    if (last && (last.label === label || (sel && last.sel))) {
      last.label = label;
      last.snap = snap;
      last.sel = !!sel;
      return;
    }
    trail.push({ label, snap, sel: !!sel });
    if (trail.length > 10) trail.shift();
  }

  // 담보별 연결로 돌아오면 탐색 경로를 보기 이름과 지금 선택으로 맞춘다
  function syncCoverTrail() {
    let i = trail.length - 1;
    while (i > 0 && !(trail[i].label === t('grPresetCover') && !trail[i].sel)) i--;
    trail = trail.slice(0, i + 1);
    if (!trail.length) trail.push({ label: t('grPresetCover'), snap: cloneStateSnap(), sel: false });
    const g = ensureGraph();
    if (state.selStd != null) recordTrail(g.N[state.selStd].l, true);
    else if (state.selGroup && net.lay && net.lay.sc.groupMap.has(state.selGroup)) recordTrail(groupLines(net.lay.sc, net.lay.sc.groupMap.get(state.selGroup))[0], true);
  }

  function dropSelTrail() {
    while (trail.length > 1 && trail[trail.length - 1].sel) trail.pop();
  }


  function initPresetState(presetName, c, keepHistory, varIdx) {
    const g = ensureGraph();
    if (!keepHistory) {
      undoStack = [];
      trail = [];
    }
    state.preset = presetName;
    state.selNode = null;
    state.selEdge = null;
    state.focusNode = null;
    state.selStd = null;
    state.selGroup = null;
    if (presetName === 'variant') {
      // 보기 방식에서 고르면 기준 종형으로 시작한다(6절). 탐색 경로는 "종형 구성 > 종형명"(4.11)
      const vi = varIdx ?? g.byId.get(c.baseId) ?? (g.N.find(n => n.k === NK['종형'] && n.o === 'EPOST') || {}).i;
      if (state.varIdx !== vi) state.vf = { renew: null, main: false, dom: null, rev: false };
      // 종형 구성에서 다른 종형으로 넘어가면 경로의 종형명만 바꾼다
      if (keepHistory && trail.length >= 2 && trail[trail.length - 2].label === t('grPresetVariant') && !trail[trail.length - 1].sel) trail.pop();
      state.varIdx = vi ?? null;
      recordTrail(t('grPresetVariant'));
      if (vi != null) recordTrail(fullVarName(g, vi));
      return;
    }
    if (presetName === 'news') {
      state.nf = 'week';
      recordTrail(t('grPresetNews'));
      return;
    }
    // 기본 보기 방식: 담보별 연결(보유 조합 그룹 네트워크, 3절)
    state.preset = 'cover';
    recordTrail(t('grPresetCover'));
  }













  function renderLeftZone(leftEl) {
    if (!leftEl) return;
    const presets = [
      { id: 'cover', nm: t('grPresetCover'), sub: t('grPresetCoverSub') },
      { id: 'variant', nm: t('grPresetVariant'), sub: t('grPresetVariantSub') },
      { id: 'news', nm: t('grPresetNews'), sub: t('grPresetNewsSub') },
    ];
    leftEl.innerHTML = `<div class="gr-left-wrap">
      <div>
        <span class="gr-sec-k">${esc(t('grLeftHead'))}</span>
        <div class="gr-presets" role="listbox" aria-label="${esc(t('grPresetsAria'))}">
          ${presets.map(p => `<button type="button" class="gr-preset${state.preset === p.id ? ' is-on' : ''}" role="option" aria-selected="${state.preset === p.id}" data-gr-preset="${p.id}" data-aim="rect" data-tip-title="${esc(p.nm)}" data-tip-sub="${esc(p.sub)}">
            <span class="gp-t">${esc(p.nm)}</span>
            <span class="gp-s">${esc(p.sub)}</span>
          </button>`).join('')}
        </div>
      </div>
      ${state.preset === 'cover' ? netLeftHTML(ensureGraph(), App.ctx()) : state.preset === 'variant' ? vtLeftHTML(ensureGraph()) : mkLeftHTML(ensureGraph(), App.ctx())}
      <div class="gr-search-box">
        <label class="gr-sec-k" for="gr-search">${esc(t('grSearchLabel'))}</label>
        <input id="gr-search" class="gr-search-in" type="search" autocomplete="off" placeholder="${esc(t('grSearchPh'))}" value="${esc(state.query)}">
        <div id="gr-sugg" class="gr-sugg" hidden></div>
      </div>
      <div>
        <span class="gr-sec-k">탐색 이동</span>
        <div class="gr-ctrl-row">
          <button type="button" class="btn sm ghost" id="gr-btn-undo" data-gr-act="undo"${undoStack.length ? '' : ' disabled'}>${esc(t('grUndoBtn'))}</button>
          <button type="button" class="btn sm ghost" id="gr-btn-reset" data-gr-act="reset">${esc(t('grResetBtn'))}</button>
        </div>
      </div>
    </div>`;
  }





  function trailNavHTML() {
    const trailHTML = trail.map((tr, idx) => {
      const isLast = idx === trail.length - 1;
      return `${idx > 0 ? '<span class="gr-tr-sep" aria-hidden="true">&gt;</span>' : ''}<button type="button" class="gr-tr-btn${isLast ? ' is-cur' : ''}" data-gr-trail="${idx}">${esc(tr.label)}</button>`;
    }).join('');
    return `<nav class="gr-trail" aria-label="${esc(t('grTrailLabel'))}"><span class="gr-trail-k">${esc(t('grTrailLabel'))}</span>${trailHTML}</nav>`;
  }

  // 담보별 연결 화면: 캐시한 배치가 있으면 바로, 없으면 계산한 뒤 그린다(3.12)
  function rerenderNet(g, c) {
    renderedEdges = new Map();
    const isNarrow = innerWidth < 1000;
    const old = lastCenterEl.querySelector('#gr-net');
    if (isNarrow) {
      lastCenterEl.innerHTML = `<div class="gr-wrap" id="gr-stage-root">${trailNavHTML()}<div class="gr-nl">${netNarrowHTML(g, c)}</div></div>`;
      net.lay = null;
      syncLeftActive();
      return;
    }
    const nav = lastCenterEl.querySelector('#gr-stage-root > .gr-trail');
    if (old && nav) nav.outerHTML = trailNavHTML();
    else lastCenterEl.innerHTML = `<div class="gr-wrap" id="gr-stage-root">${trailNavHTML()}<div class="gr-net" id="gr-net"></div></div>`;
    const host = lastCenterEl.querySelector('#gr-net');
    host.classList.remove('is-scroll');
    alt.lay = null;
    // 탭 전환 중이라 가운데 영역의 크기가 아직 잡히지 않았으면 다음 프레임에 다시 잰다
    const [W, H] = netArea(host);
    if (W < 200 || H < 200) {
      if ((net.retry = (net.retry || 0) + 1) < 30) requestAnimationFrame(() => { if (App.state.tab === 'graph' && state.preset === 'cover') rerenderGraph(false); });
      return;
    }
    net.retry = 0;
    net.W = W; net.H = H;
    syncLeftActive();
    const key = layoutKey(g, c, W, H);
    const draw = lay => {
      if (!lastCenterEl || !lastCenterEl.contains(host) || App.state.tab !== 'graph' || state.preset !== 'cover') return;
      if (layoutKey(ensureGraph(), App.ctx(), net.W, net.H) !== key) return;
      net.hover = null;
      // 조건이 바뀌었으면(같은 그래프 영역 크기) 지금 보이는 위치에서 새 위치로 옮긴다(4.9). 리사이즈는 트랜지션 없이
      const prevSvg = host.querySelector('#gr-net-svg');
      const prevLay = net.lay;
      // 종형 구성에서 돌아오면 가운데 상자와 바깥 타원의 표준담보에서 출발한다(4.4, 6절 14번)
      const vtSvg = host.querySelector('#gr-vt-svg');
      const prev = vtSvg ? (moveDur() ? capturePosVt(vtSvg, lay) : null)
        : prevSvg && prevLay && prevLay !== lay && prevLay.W === lay.W && prevLay.H === lay.H && layoutKeyOf(prevLay) !== layoutKeyOf(lay) ? capturePos(prevSvg) : null;
      endMove();
      if (prev && moveDur()) net.moving = true;
      renderNetInto(host, lay);
      if (net.moving && !startMove(host.querySelector('#gr-net-svg'), prev, lay)) { net.moving = false; applyNetState(); }
      requestAnimationFrame(() => App.updateSelLink(false));
      if (!lay.fontsOk && document.fonts) document.fonts.ready.then(() => { if (state.preset === 'cover') rerenderGraph(false); });
      warmLayouts(W, H);
    };
    if (layoutCache.has(key) || !old || !host.firstChild) draw(layoutSync(g, c, W, H));
    else layoutChunked(g, c, W, H, draw);
  }

  function syncLeftActive() {
    const undoBtn = lastLeftEl && lastLeftEl.querySelector('#gr-btn-undo');
    if (undoBtn) undoBtn.disabled = undoStack.length === 0;
    if (lastLeftEl) {
      lastLeftEl.querySelectorAll('[data-gr-preset]').forEach(btn => {
        const on = btn.dataset.grPreset === state.preset;
        btn.classList.toggle('is-on', on);
        btn.setAttribute('aria-selected', String(on));
      });
      lastLeftEl.querySelectorAll('[data-gr-vf]').forEach(btn => {
        const [k, v] = btn.dataset.grVf.split(':');
        const on = k === 'renew' ? state.vf.renew === v : k === 'dom' ? state.vf.dom === v : !!state.vf[k];
        btn.classList.toggle('is-on', on);
        btn.setAttribute('aria-pressed', String(on));
      });
      lastLeftEl.querySelectorAll('[data-gr-nf]').forEach(btn => {
        const on = btn.dataset.grNf === state.nf;
        btn.classList.toggle('is-on', on);
        btn.setAttribute('aria-pressed', String(on));
      });
      lastLeftEl.querySelectorAll('[data-gr-filter]').forEach(btn => {
        const on = btn.dataset.grFilter === state.filter;
        btn.classList.toggle('is-on', on);
        btn.setAttribute('aria-pressed', String(on));
      });
    }
  }

  function rerenderGraph(animate) {
    const g = ensureGraph();
    if (!lastCenterEl) return;
    if (edgeDrawRaf) { cancelAnimationFrame(edgeDrawRaf); edgeDrawRaf = 0; }
    hoveredEdgeEl = null;
    const curC = App.ctx();
    if (state.preset === 'cover') { rerenderNet(g, curC); return; }
    renderAltView(g, curC, animate);
  }


  function restoreGraphNodeFocus(ni) {
    if (ni == null || !lastCenterEl) return;
    state.focusNode = ni;
    const svg = altSvg();
    const target = svg ? svg.querySelector(`[data-gr-idx="${ni}"]`) : lastCenterEl.querySelector(`.gr-nl-it[data-gr-idx="${ni}"]`);
    if (svg && target) setRoving(svg, target);
    if (target) { try { target.focus({ preventScroll: true }); } catch (e) { /* */ } }
  }



  // ---------- 담보별 연결: 보유 조합 그룹 네트워크(3절) ----------
  // 앵커(종형) 고정, 1단계 그룹 원 배치, 2단계 그룹 안 포스 배치. 난수 없이 FNV-1a 해시 지터만 쓴다(3.12)
  const NET_MARGIN = 20;
  const NET_GROUP_GAP = 14;
  const NET_FS = 13;
  const NET_ITERS = 300;
  const net = {
    lay: null,          // 지금 그린 배치
    W: 0, H: 0,
    hover: null,        // { t: 'std'|'anchor'|'group', id }
    pending: 0,         // 조각 계산 중인 요청 번호
    warmT: 0,
    resizeT: 0,
  };
  const layoutCache = new Map();

  function fnv1a(str) {
    let h = 0x811C9DC5;
    const bytes = new TextEncoder().encode(str);
    for (let i = 0; i < bytes.length; i++) {
      h ^= bytes[i];
      h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h >>> 0;
  }
  const hashUnit = (key, salt) => fnv1a(salt + ':' + key) / 4294967296;

  let measureCtx = null;
  let measureFamily = '';
  function textW(s, weight) {
    if (!measureCtx) {
      measureCtx = document.createElement('canvas').getContext('2d');
      measureFamily = getComputedStyle(document.body).fontFamily || 'sans-serif';
    }
    measureCtx.font = `${weight || 400} ${NET_FS}px ${measureFamily}`;
    return measureCtx.measureText(String(s)).width;
  }
  // 실제 글꼴의 줄 높이(getBBox 와 같은 fontBoundingBox)
  let lineMetrics = null;
  function textAsc() { if (!lineMetrics) lineMetricsCalc(); return lineMetrics[0]; }
  function textLineH() { if (!lineMetrics) lineMetricsCalc(); return lineMetrics[0] + lineMetrics[1]; }
  function lineMetricsCalc() {
    textW('가');
    const m = measureCtx.measureText('가Ag');
    const asc = m.fontBoundingBoxAscent || NET_FS * 0.9, desc = m.fontBoundingBoxDescent || NET_FS * 0.3;
    lineMetrics = [asc, desc];
  }
  const fontsReady = () => !document.fonts || document.fonts.status === 'loaded';

  function shortVarName(g, vi) {
    const n = g.N[vi];
    const nm = String((n.p && n.p['종형명']) || n.l || '');
    return nm.length > 14 ? nm.slice(0, 13) + '…' : nm;
  }
  function fullVarName(g, vi) {
    const n = g.N[vi];
    return String((n.p && n.p['종형명']) || n.l || '');
  }
  const orgOf = code => (code === 'EPOST' ? t('grOurs') : orgLabel(code));

  function anchorLines(g, sc, slot) {
    const vi = sc.types[slot];
    if (slot === 0) return [t('grBaseAnchorTpl', { org: t('grOurs') }), shortVarName(g, vi)];
    if (sc.nPeer > 3) return [orgOf(sc.codes[slot])];
    return [orgOf(sc.codes[slot]), shortVarName(g, vi)];
  }

  // 그룹 라벨 두 행(11절)
  function rangeText(a, b) { return a === b ? fmt(a) : `${fmt(a)}~${fmt(b)}`; }
  function groupLines(sc, grp) {
    const n = grp.members.length;
    const line2 = grp.cls === 'peer' ? t('grGrpCntMissTpl', { n: fmt(n), miss: App.label('우체국에 없음') }) : t('grGrpCntTpl', { n: fmt(n) });
    let line1 = '';
    if (grp.bin) {
      const np = sc.nPeer, h = Math.ceil(np / 2);
      line1 = grp.bin === 'only' ? t('grGrpOnly')
        : grp.bin === 'all' ? t('grGrpAll')
          : grp.bin === 'few' ? t('grBinOursTpl', { rng: rangeText(1, h - 1) })
            : grp.bin === 'many' ? t('grBinOursTpl', { rng: rangeText(h, np - 1) })
              : grp.bin === 'p-all' ? t('grBinPeerAllTpl', { n: fmt(np) })
                : grp.bin === 'p-many' ? t('grBinPeerTpl', { rng: rangeText(h, np - 1) })
                  : grp.bin === 'p-few' ? t('grBinPeerTpl', { rng: rangeText(2, h - 1) })
                    : t('grBinPeerOne');
    } else {
      const slots = grp.slots;
      if (grp.cls === 'only') line1 = t('grGrpOnly');
      else if (slots.length === sc.types.length) line1 = t('grGrpAll');
      else if (slots.length === 1) line1 = t('grGrpOneTpl', { org: orgOf(sc.codes[slots[0]]) });
      else line1 = t('grGrpManyTpl', { orgs: slots.map(s => orgOf(sc.codes[s])).join(', ') });
    }
    return [line1, line2];
  }

  function netCtxFor(baseId, scope) {
    const base = App.S['기준별'][baseId];
    const raw = (base && base['맞붙는종형']) || [];
    let orgs;
    if (scope === 'life' || scope === 'nonlife') orgs = App.PEER_ORGS.filter(o => App.orgSector(o) === scope);
    else orgs = App.PEER_ORGS.slice();
    const set = new Set(orgs);
    const peerIds = scope === 'all' ? raw.slice() : raw.filter(id => set.has((txt.vinfo(id) || {})['기관코드']));
    return { baseId, peerIds, peerScope: scope, activePeerOrgs: orgs };
  }

  // 3.5절 1번: 담보마다의 목표점
  function nodeTarget(sc, it, anc, k) {
    const hs = it.slots;
    if (hs.length === 1) {
      const a = anc[hs[0]];
      let ox, oy;
      if (hs[0] === 0) { const th = 110 * Math.PI / 180; ox = Math.cos(th); oy = Math.sin(th); } else {
        const dx = a.x - anc[0].x, dy = a.y - anc[0].y, d = Math.hypot(dx, dy) || 1;
        ox = dx / d; oy = dy / d;
      }
      return [a.x + ox * 62 * k, a.y + oy * 62 * k];
    }
    const e = hs[0] === 0;
    const ps = hs.filter(s => s !== 0);
    const wb = e && ps.length ? 0.5 : (e ? 1 : 0);
    const wp = ps.length ? (1 - wb) / ps.length : 0;
    let tx = e ? wb * anc[0].x : 0, ty = e ? wb * anc[0].y : 0;
    ps.forEach(s => { tx += wp * anc[s].x; ty += wp * anc[s].y; });
    return [tx, ty];
  }

  function pushOutRect(x, y, r, box, gap) {
    const x0 = box[0] - r - gap, y0 = box[1] - r - gap, x1 = box[2] + r + gap, y1 = box[3] + r + gap;
    if (x0 < x && x < x1 && y0 < y && y < y1) {
      const c = [[x - x0, -1, 0], [x1 - x, 1, 0], [y - y0, 0, -1], [y1 - y, 0, 1]];
      let m = c[0];
      for (let i = 1; i < 4; i++) if (c[i][0] < m[0]) m = c[i];
      return [x + m[1] * m[0], y + m[2] * m[0]];
    }
    return [x, y];
  }

  // d3-force 와 같은 형식의 시뮬레이션(forceX, forceY, forceManyBody(distanceMax), forceCollide). 몇 회마다 yield 해 조각 실행이 가능하다
  function* simulate(nodes, fixed, boxes, links, P) {
    const n = nodes.length;
    const X = new Float64Array(n), Y = new Float64Array(n), R = new Float64Array(n);
    const vx = new Float64Array(n), vy = new Float64Array(n);
    nodes.forEach((nd, i) => { X[i] = nd.x; Y[i] = nd.y; R[i] = nd.r; });
    const W = P.W, H = P.H, gap = P.gap;
    const clampX = (x, r) => Math.min(Math.max(x, NET_MARGIN + r), W - NET_MARGIN - r);
    const clampY = (y, r) => Math.min(Math.max(y, NET_MARGIN + r), H - NET_MARGIN - r);
    const groups = new Map();
    nodes.forEach((nd, i) => {
      if (nd.g == null) return;
      let a = groups.get(nd.g);
      if (!a) { a = []; groups.set(nd.g, a); }
      a.push(i);
    });
    const qd2 = P.qdmax * P.qdmax;
    let alpha = 1;
    const iters = P.iters || NET_ITERS;
    const adecay = 1 - Math.pow(0.001, 1 / iters);
    const vk = 0.6;
    for (let it = 0; it < iters; it++) {
      alpha += (0 - alpha) * adecay;
      for (let i = 0; i < n; i++) {
        const nd = nodes[i];
        const kk = P.kt * alpha;
        vx[i] += (nd.tx - X[i]) * kk;
        vy[i] += (nd.ty - Y[i]) * kk;
      }
      if (P.kg > 0) {
        for (const mem of groups.values()) {
          if (mem.length < 2) continue;
          let cx = 0, cy = 0;
          mem.forEach(i => { cx += X[i]; cy += Y[i]; });
          cx /= mem.length; cy /= mem.length;
          mem.forEach(i => { vx[i] += (cx - X[i]) * P.kg * alpha; vy[i] += (cy - Y[i]) * P.kg * alpha; });
        }
      }
      for (const [a, b, L, s] of links) {
        const dx = X[b] + vx[b] - X[a] - vx[a], dy = Y[b] + vy[b] - Y[a] - vy[a];
        const d = Math.hypot(dx, dy) || 1e-6;
        const f = (d - L) / d * alpha * s;
        vx[b] -= dx * f * 0.5; vy[b] -= dy * f * 0.5;
        vx[a] += dx * f * 0.5; vy[a] += dy * f * 0.5;
      }
      for (let i = 0; i < n; i++) {
        const xi = X[i], yi = Y[i], ri = R[i], gi = nodes[i].g;
        for (let j = i + 1; j < n; j++) {
          let dx = X[j] - xi, dy = Y[j] - yi;
          let l2 = dx * dx + dy * dy;
          if (l2 < qd2) {
            if (l2 < 1) {
              const key = String(i * 7919 + j);
              dx = (hashUnit(key, 'jx') - 0.5) * 1e-3;
              dy = (hashUnit(key, 'jy') - 0.5) * 1e-3;
              l2 = Math.max(dx * dx + dy * dy, 1e-6);
            }
            const q = (gi != null && gi === nodes[j].g ? P.qSame : P.qDiff) * alpha / Math.max(l2, 1);
            vx[i] += dx * q; vy[i] += dy * q;
            vx[j] -= dx * q; vy[j] -= dy * q;
          }
          const dx2 = X[j] + vx[j] - xi - vx[i], dy2 = Y[j] + vy[j] - yi - vy[i];
          const rr = ri + R[j] + gap;
          const m2 = dx2 * dx2 + dy2 * dy2;
          if (m2 < rr * rr) {
            const l = Math.sqrt(m2) || 1e-3;
            const f = (rr - l) / l * 0.8;
            const wj = R[j] * R[j] / (ri * ri + R[j] * R[j]);
            vx[i] -= dx2 * f * wj; vy[i] -= dy2 * f * wj;
            vx[j] += dx2 * f * (1 - wj); vy[j] += dy2 * f * (1 - wj);
          }
        }
        for (const fx of fixed) {
          const dx2 = X[i] + vx[i] - fx.x, dy2 = Y[i] + vy[i] - fx.y;
          const rr = ri + fx.r + gap;
          const m2 = dx2 * dx2 + dy2 * dy2;
          if (m2 < rr * rr) {
            const l = Math.sqrt(m2) || 1e-3;
            const f = (rr - l) / l * 0.8;
            vx[i] += dx2 * f; vy[i] += dy2 * f;
          }
        }
      }
      for (let i = 0; i < n; i++) {
        vx[i] *= vk; vy[i] *= vk;
        X[i] += vx[i]; Y[i] += vy[i];
        for (const bx of boxes) { const p = pushOutRect(X[i], Y[i], R[i], bx, gap); X[i] = p[0]; Y[i] = p[1]; }
        if (nodes[i].gR != null) { const p = contain(X[i], Y[i], R[i], nodes[i]); X[i] = p[0]; Y[i] = p[1]; }
        X[i] = clampX(X[i], R[i]); Y[i] = clampY(Y[i], R[i]);
      }
      if ((it & 7) === 7) yield;
    }
    // 좌표를 0.01px로 반올림해 그리므로 정리 단계는 간격에 0.05px 여유를 둔다
    yield* relax(X, Y, R, fixed, boxes, gap + 0.05, nodes, clampX, clampY, false);
    // 뒤 절반의 정리로 그룹 원 밖에 남은 노드가 있으면 원 안으로 넣는 제한을 끝까지 걸고 한 번 더 정리한다
    const outside = nodes.some((nd, i) => nd.gR != null && Math.hypot(X[i] - nd.gx, Y[i] - nd.gy) + R[i] > nd.gR - 0.04);
    if (outside) yield* relax(X, Y, R, fixed, boxes, gap + 0.05, nodes, clampX, clampY, true);
    nodes.forEach((nd, i) => { nd.x = X[i]; nd.y = Y[i]; });
  }

  function contain(x, y, r, nd) {
    const dx = x - nd.gx, dy = y - nd.gy;
    const lim = Math.max(nd.gR - r - 0.05, 0);   // 0.01px 반올림 여유
    const d = Math.hypot(dx, dy);
    if (d > lim && d > 0) return [nd.gx + dx / d * lim, nd.gy + dy / d * lim];
    return [x, y];
  }

  // 위치만 옮겨 겹침과 간격 부족을 없앤다(최대 300회). 앞 절반은 그룹 원 밖으로 나간 노드도 되돌린다(3.5절 4번, 3.6절)
  function* relax(X, Y, R, fixed, boxes, gap, nodes, clampX, clampY, containAll) {
    const n = X.length;
    const maxIter = 300;
    for (let it = 0; it < maxIter; it++) {
      let moved = false;
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          let dx = X[j] - X[i], dy = Y[j] - Y[i];
          const rr = R[i] + R[j] + gap;
          const l2 = dx * dx + dy * dy;
          if (l2 < rr * rr - 1e-6) {
            let l = Math.sqrt(l2);
            if (l < 1e-6) { dx = 1; dy = 0; l = 1; }
            const m = (rr - l) / 2 / l * 1.01;
            X[i] -= dx * m; Y[i] -= dy * m;
            X[j] += dx * m; Y[j] += dy * m;
            moved = true;
          }
        }
        for (const fx of fixed) {
          const dx = X[i] - fx.x, dy = Y[i] - fx.y;
          const rr = R[i] + fx.r + gap;
          const l2 = dx * dx + dy * dy;
          if (l2 < rr * rr - 1e-6) {
            const l = Math.sqrt(l2) || 1e-6;
            const m = (rr - l) / l * 1.01;
            X[i] += dx * m; Y[i] += dy * m;
            moved = true;
          }
        }
      }
      for (let i = 0; i < n; i++) {
        for (const bx of boxes) {
          const p = pushOutRect(X[i], Y[i], R[i], bx, gap);
          if (p[0] !== X[i] || p[1] !== Y[i]) { X[i] = p[0]; Y[i] = p[1]; moved = true; }
        }
        if (nodes[i].gR != null && (containAll || it < maxIter / 2)) {
          const p = contain(X[i], Y[i], R[i], nodes[i]);
          if (Math.abs(p[0] - X[i]) + Math.abs(p[1] - Y[i]) > 1e-6) { X[i] = p[0]; Y[i] = p[1]; moved = true; }
        }
        const cx = clampX(X[i], R[i]), cy = clampY(Y[i], R[i]);
        if (cx !== X[i] || cy !== Y[i]) { X[i] = cx; Y[i] = cy; moved = true; }
      }
      if (!moved) return;
      if ((it & 7) === 7) yield;
    }
  }

  function boxHit(b, placed, circles, W, H) {
    if (b[0] < 0 || b[1] < 0 || b[2] > W || b[3] > H) return true;
    for (const q of placed) if (b[0] < q[2] && q[0] < b[2] && b[1] < q[3] && q[1] < b[3]) return true;
    for (const [x, y, r] of circles) {
      const cx = Math.min(Math.max(x, b[0]), b[2]), cy = Math.min(Math.max(y, b[1]), b[3]);
      if ((cx - x) * (cx - x) + (cy - y) * (cy - y) < r * r) return true;
    }
    return false;
  }

  // 배치 전체(앵커, 그룹 원, 노드, 라벨, 번들 엣지)를 계산하는 생성기
  function* layoutGen(g, c, W, H) {
    const t0 = performance.now();
    const sc = sceneOf(g, c);
    const jd = judgeOf(g, c, sc);
    const k = Math.min(1, Math.sqrt((W * H) / (945 * 620)));
    const gap = k < 1 ? 3 : 4;
    const doms = domOrder(g);
    // 앵커(3.3)
    const nP = sc.nPeer;
    const bx = 0.15 * W, cy = H / 2, rx = 0.80 * W, ry = 0.40 * H;
    const tm = nP <= 1 ? 0 : nP <= 3 ? 50 : Math.min(74, 50 + 3 * (nP - 3));
    const anc = sc.types.map((vi, slot) => {
      const lines = anchorLines(g, sc, slot);
      const lw = Math.max(...lines.map((s, i) => textW(s, i === 0 ? 600 : 400))) + 4;
      const lh = textLineH() + (lines.length - 1) * (NET_FS + 3);
      let x, y, r;
      if (slot === 0) { x = bx; y = cy; r = 15 * k; } else {
        const th = (nP === 1 ? 0 : -tm + 2 * tm * (slot - 1) / (nP - 1)) * Math.PI / 180;
        r = 12 * k;
        x = Math.min(bx + rx * Math.cos(th), W - NET_MARGIN - lw - r - 8);
        y = cy + ry * Math.sin(th);
      }
      let box;
      if (slot === 0) {
        let lx = x - lw / 2;
        lx = Math.max(2, Math.min(W - 2 - lw, lx));
        box = [lx, y - r - 4 - lh, lx + lw, y - r - 4];
      } else box = [x + r + 4, y - lh / 2, x + r + 4 + lw, y + lh / 2];
      return { slot, vi, id: g.N[vi].id, code: sc.codes[slot], key: slot === 0 ? 'base' : sc.codes[slot], x, y, r, lines, box, lw };
    });
    // 타사가 많으면 오른쪽 끝에서 세로로 모인 앵커 옆으로 이웃 앵커의 라벨이 지나간다. 다른 앵커나 라벨에 걸리면 라벨을 앵커 왼쪽으로 옮긴다
    if (nP > 3) {
      const hitC = (b, a) => { const px = Math.max(b[0], Math.min(a.x, b[2])), py = Math.max(b[1], Math.min(a.y, b[3])); return Math.hypot(px - a.x, py - a.y) < a.r + 1; };
      const hitB = (b, q) => b[0] < q[2] && q[0] < b[2] && b[1] < q[3] && q[1] < b[3];
      const bad = (a, b) => anc.some(o => o !== a && (hitC(b, o) || (o.slot !== 0 && hitB(b, o.box))));
      anc.forEach(a => {
        if (a.slot === 0 || !bad(a, a.box)) return;
        // 후보: 오른쪽에서 바깥쪽(위쪽 앵커는 위, 아래쪽 앵커는 아래)으로 조금씩 옮긴 자리, 그다음 왼쪽
        const out = a.y < cy ? -1 : 1, lh = a.box[3] - a.box[1];
        const dys = [0, 4, 8, 12, 16].map(d => d * out).concat([4, 8].map(d => -d * out));
        const cands = [];
        [1, -1].forEach(side => dys.forEach(dy => {
          const x0 = side > 0 ? a.x + a.r + 4 : a.x - a.r - 4 - a.lw;
          cands.push([x0, a.box[1] + dy, x0 + a.lw, a.box[1] + dy + lh]);
        }));
        const ok = cands.find(b => b[0] >= 2 && b[2] <= W - 2 && b[1] >= 2 && b[3] <= H - 2 && !bad(a, b));
        if (ok) a.box = ok;
      });
    }
    const boxes = anc.map(a => a.box);
    const fixed = anc.map(a => ({ x: a.x, y: a.y, r: a.r }));
    // 노드 크기(3.7): 반지름 r, 충돌 반지름 cr
    const rad = new Map(), crad = new Map(), tgt = new Map();
    sc.stds.forEach(si => {
      const it = sc.info.get(si);
      const r = (5 + 5 * Math.sqrt(Math.min(it.bens, 16) / 16)) * k;
      const marks = jd.per.get(si).marks;
      const glyph = marks.some(m => m !== 'wait') || nP > 3;
      rad.set(si, r);
      crad.set(si, glyph ? r + 3 : r);
      tgt.set(si, nodeTarget(sc, it, anc, k));
    });
    // 1단계: 그룹 원(3.5)
    const gnodes = sc.groups.map(grp => {
      const mem = grp.members;
      let tx = 0, ty = 0, s2 = 0, mx = 0;
      mem.forEach(si => {
        tx += tgt.get(si)[0]; ty += tgt.get(si)[1];
        const cr = crad.get(si);
        s2 += (cr + gap / 2 + 1) * (cr + gap / 2 + 1);
        mx = Math.max(mx, cr);
      });
      tx /= mem.length; ty /= mem.length;
      const R = Math.max(Math.sqrt(s2 / 0.60), mx + 1);
      let x0 = tx + (hashUnit(grp.key, 'gx') - 0.5) * 10, y0 = ty + (hashUnit(grp.key, 'gy') - 0.5) * 10;
      x0 = Math.min(Math.max(x0, NET_MARGIN + R), W - NET_MARGIN - R);
      y0 = Math.min(Math.max(y0, NET_MARGIN + R), H - NET_MARGIN - R);
      return { key: grp.key, x: x0, y: y0, r: R, tx, ty, g: null };
    });
    yield* simulate(gnodes, fixed, boxes, [], { W, H, gap: NET_GROUP_GAP, qSame: 0, qDiff: -30, qdmax: 40, kg: 0, kt: 0.10 });
    const gpos = new Map(gnodes.map(gn => [gn.key, { x: gn.x, y: gn.y, R: gn.r }]));
    // 2단계: 그룹 안 포스 배치(3.6 안 A)
    const nodes = sc.stds.map(si => {
      const it = sc.info.get(si);
      const gg = gpos.get(it.key);
      const ng = sc.groupMap.get(it.key).members.length;
      let tx = gg.x, ty = gg.y;
      const di = doms.indexOf(it.dom);
      if (ng >= 4 && di >= 0 && di < 5) {
        const ang = (-90 + 72 * di) * Math.PI / 180;
        tx += Math.cos(ang) * gg.R * 0.42;
        ty += Math.sin(ang) * gg.R * 0.42;
      }
      const cr = crad.get(si);
      const jit = Math.min(24, gg.R);
      const sid = g.N[si].id;
      let x0 = tx + (hashUnit(sid, 'x') - 0.5) * jit, y0 = ty + (hashUnit(sid, 'y') - 0.5) * jit;
      x0 = Math.min(Math.max(x0, NET_MARGIN + cr), W - NET_MARGIN - cr);
      y0 = Math.min(Math.max(y0, NET_MARGIN + cr), H - NET_MARGIN - cr);
      return { si, r: cr, g: it.key, gx: gg.x, gy: gg.y, gR: gg.R, tx, ty, x: x0, y: y0 };
    });
    const pos = new Map(nodes.map((nd, i) => [nd.si, i]));
    const links = [];
    sc.stds.forEach(si => {
      (g.stdRels.get(si) || []).forEach(rl => {
        if (rl.dir !== 'out' || !pos.has(rl.other)) return;
        if (sc.info.get(si).key !== sc.info.get(rl.other).key) return;
        links.push([pos.get(si), pos.get(rl.other), 40, 0.02]);
      });
    });
    yield* simulate(nodes, fixed, boxes, links, { W, H, gap, qSame: -10, qDiff: -40, qdmax: 90, kg: 0.03, kt: 0.10 });
    const npos = new Map(nodes.map(nd => [nd.si, { x: nd.x, y: nd.y, r: rad.get(nd.si), cr: crad.get(nd.si) }]));
    // 번들 엣지(3.8)
    const bundles = [];
    sc.groups.forEach(grp => {
      const gg = gpos.get(grp.key);
      const slots = grp.slots || Array.from(new Set(grp.members.flatMap(si => sc.info.get(si).slots))).sort((a, b) => a - b);
      slots.forEach(slot => {
        if (nP > 3 && slot !== 0) return;
        const a = anc[slot];
        const n = grp.slots ? grp.members.length : grp.members.filter(si => sc.info.get(si).slots.includes(slot)).length;
        if (!n) return;
        const dx = gg.x - a.x, dy = gg.y - a.y, d = Math.hypot(dx, dy) || 1;
        const ux = dx / d, uy = dy / d;
        bundles.push({ slot, key: grp.key, n, w: Math.min(6, 0.6 + 0.18 * n),
          x1: a.x + ux * a.r, y1: a.y + uy * a.r, x2: gg.x - ux * gg.R, y2: gg.y - uy * gg.R });
      });
    });
    yield;
    // 그룹 라벨(3.9): 담보 수가 많은 그룹부터 여덟 방향, 그다음 22px 더 떨어진 여덟 곳, 막히면 배지
    const placed = boxes.slice();
    const gCircles = Array.from(gpos.values()).map(v => [v.x, v.y, v.R]);
    const aCircles = anc.map(a => [a.x, a.y, a.r]);
    const glabels = new Map();
    const dirs = [[0, -1], [0, 1], [1, 0], [-1, 0], [1, -1], [-1, -1], [1, 1], [-1, 1]];
    sc.groups.slice().sort((a, b) => b.members.length - a.members.length || (a.key < b.key ? -1 : 1)).forEach(grp => {
      const gg = gpos.get(grp.key);
      const lines = groupLines(sc, grp);
      const w = Math.max(textW(lines[0], 600), textW(lines[1], 400)) + 4;
      const h = textLineH() + (NET_FS + 3);
      let hit = null;
      for (const off of [4, 26]) {
        for (const [ux0, uy0] of dirs) {
          const dl = Math.hypot(ux0, uy0);
          const ux = ux0 / dl, uy = uy0 / dl;
          const px = gg.x + ux * (gg.R + off), py = gg.y + uy * (gg.R + off);
          const x0 = ux0 > 0 ? px : ux0 < 0 ? px - w : px - w / 2;
          const y0 = uy0 > 0 ? py : uy0 < 0 ? py - h : py - h / 2;
          const b = [x0, y0, x0 + w, y0 + h];
          if (!boxHit(b, placed, gCircles.concat(aCircles), W, H)) {
            hit = { box: b, lines, lead: off > 4 ? [gg.x + ux * gg.R, gg.y + uy * gg.R, px, py] : null };
            break;
          }
        }
        if (hit) break;
      }
      if (!hit) {
        // 배지는 그룹 원 둘레에 둔다. 12시부터 시계 방향으로 노드, 앵커, 다른 라벨에 걸리지 않는 첫 자리
        const bw = textW(fmt(grp.members.length), 600) + 12, bh = textLineH() + 2;
        const at = deg => { const a = deg * Math.PI / 180, x = gg.x + gg.R * Math.sin(a), y = gg.y - gg.R * Math.cos(a); return [x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2]; };
        const nodeC = Array.from(npos.values()).map(v => [v.x, v.y, v.r]).concat(aCircles);
        let bb = null;
        for (let d = 0; d < 360 && !bb; d += 22.5) { const b = at(d); if (!boxHit(b, placed, nodeC, W, H)) bb = b; }
        hit = { box: bb || at(0), lines, badge: true };
      }
      placed.push(hit.box);
      glabels.set(grp.key, hit);
    });
    yield;
    // 담보 이름 라벨(3.9): 우체국만, 우체국과 타사, 타사만 차례로, 큰 노드부터 오른쪽, 왼쪽, 위, 아래
    const rank = { only: 0, shared: 1, peer: 2 };
    const nCircles = sc.stds.map(si => { const p = npos.get(si); return [p.x, p.y, p.r]; }).concat(aCircles);
    const slabels = new Map();
    sc.stds.slice().sort((a, b) => (rank[sc.info.get(a).cls] - rank[sc.info.get(b).cls]) || (rad.get(b) - rad.get(a)) || (a - b)).forEach(si => {
      const p = npos.get(si);
      const nm = g.N[si].l;
      const w = textW(nm, 400), h = textLineH();
      const cands = [
        [p.x + p.r + 2, p.y - h / 2], [p.x - p.r - 2 - w, p.y - h / 2],
        [p.x - w / 2, p.y - p.r - 2 - h], [p.x - w / 2, p.y + p.r + 2],
      ];
      for (const [x0, y0] of cands) {
        const b = [x0, y0, x0 + w, y0 + h];
        // 번들 엣지 위에 얹힌 이름은 엣지 라벨처럼 읽히므로 선분과 겹치는 자리는 쓰지 않는다
        if (!boxHit(b, placed, nCircles, W, H) && !bundles.some(e => segHitsBox(e.x1, e.y1, e.x2, e.y2, b, e.w / 2 + 1))) { placed.push(b); slabels.set(si, b); break; }
      }
    });
    return { sc, jd, W, H, k, gap, anc, gpos, npos, bundles, glabels, slabels, ms: performance.now() - t0, fontsOk: fontsReady() };
  }

  function runSync(gen) {
    let r = gen.next();
    while (!r.done) r = gen.next();
    return r.value;
  }

  function layoutKey(g, c, W, H) {
    return `cover|${c.baseId}|${sceneTypes(g, c).join(',')}|${c.peerScope}|${W}|${H}`;
  }

  function layoutSync(g, c, W, H) {
    const key = layoutKey(g, c, W, H);
    if (layoutCache.has(key)) return layoutCache.get(key);
    const lay = runSync(layoutGen(g, c, W, H));
    if (lay.fontsOk) layoutCache.set(key, lay);
    return lay;
  }

  // 예열 전에 조건이 바뀌면 그 조건의 계산을 프레임당 8ms 이하로 나눠 실행한다(3.12)
  function layoutChunked(g, c, W, H, done) {
    const key = layoutKey(g, c, W, H);
    if (layoutCache.has(key)) { done(layoutCache.get(key)); return; }
    const ticket = ++net.pending;
    const gen = layoutGen(g, c, W, H);
    const step = () => {
      if (ticket !== net.pending) return;
      const t0 = performance.now();
      let r;
      do { r = gen.next(); } while (!r.done && performance.now() - t0 < 8);
      if (r.done) {
        if (r.value.fontsOk) layoutCache.set(key, r.value);
        done(r.value);
      } else requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  // 탭에 들어오면 기준 종형 다섯 x 비교 범위 셋을 지금 그래프 영역 크기로 미리 계산한다(지금 조건부터)
  function warmLayouts(W, H) {
    if (net.warmT || typeof requestIdleCallback !== 'function') return;
    const g = ensureGraph();
    const cur = App.ctx();
    const list = [];
    const bases = Object.keys(App.S['기준별'] || {});
    ['all', 'life', 'nonlife'].forEach(sc => bases.forEach(b => list.push(netCtxFor(b, sc))));
    list.sort((a, b) => (b.baseId === cur.baseId && b.peerScope === cur.peerScope) - (a.baseId === cur.baseId && a.peerScope === cur.peerScope));
    let gen = null, cc = null;
    const work = dl => {
      net.warmT = 0;
      if (net.W !== W || net.H !== H) return;
      while (dl.timeRemaining() > 2) {
        if (!gen) {
          while (list.length && layoutCache.has(layoutKey(g, list[0], W, H))) list.shift();
          if (!list.length) return;
          cc = list.shift();
          gen = layoutGen(g, cc, W, H);
        }
        const r = gen.next();
        if (r.done) {
          if (r.value.fontsOk) layoutCache.set(layoutKey(g, cc, W, H), r.value);
          gen = null;
        }
      }
      net.warmT = requestIdleCallback(work, { timeout: 2000 });
    };
    net.warmT = requestIdleCallback(work, { timeout: 2000 });
  }

  // ---------- 담보별 연결 그리기 ----------
  const f1 = v => Math.round(v * 100) / 100;
  const MARK_KEY = { sole: 'grMkSole', 'peer-rel': 'grMkPeerRel', 'ours-wide': 'grMkOursWide', 'ours-part': 'grMkOursPart', wait: 'grMkWait' };
  const stdNames = ids => ids.map(id => { const ni = ensureGraph().byId.get(id); return ni != null ? ensureGraph().N[ni].l : id; }).join(', ');

  function markLines(g, c, lay, si) {
    const sc = lay.sc, jd = lay.jd.per.get(si), it = sc.info.get(si);
    const out = [];
    jd.marks.forEach(m => {
      if (m === 'ours-wide' || m === 'ours-part') {
        const covs = txt.josa(stdNames(jd.cov.oursRel[1] || []), '으로');
        out.push(t(m === 'ours-wide' ? 'grMkOursWideTpl' : 'grMkOursPartTpl', { covs }));
      } else if (m === 'wait') {
        it.per.forEach(x => {
          const a = +(x.e.p['매핑검수대기급부수'] || 0), b = +(x.e.p['추출검수대기급부수'] || 0);
          const parts = [];
          if (a) parts.push(t('grWaitMapTpl', { n: fmt(a) }));
          if (b) parts.push(t('grWaitExtTpl', { n: fmt(b) }));
          if (parts.length) out.push(`${orgOf(x.code)} ${parts.join(', ')}`);
        });
      } else out.push(t(MARK_KEY[m]));
    });
    return out;
  }

  function verdictChips(lay, si) {
    const jd = lay.jd.per.get(si);
    if (!jd.cov) return [];
    return jd.cov.pv.filter(x => x.v).map(x => [x.v.kind, `${orgOf((txt.vinfo(x.peer) || {})['기관코드'])} ${App.cover.chipText(x.v)}`]);
  }

  function markGlyph(m, r) {
    const d = r * 0.7071;
    if (m === 'sole' || m === 'peer-rel') {
      const cx = f1(d + 1), cy = f1(-d - 1), h = 4.24;
      return `<path class="gr-mk gr-mk-${m}" d="M${cx} ${f1(cy - h)}L${f1(cx + h)} ${cy}L${cx} ${f1(cy + h)}L${f1(cx - h)} ${cy}Z"/>`;
    }
    if (m === 'ours-wide') return `<circle class="gr-mk gr-mk-wide" cx="${f1(d + 1)}" cy="${f1(d + 1)}" r="3"/>`;
    if (m === 'ours-part') {
      const cx = f1(d + 1), cy = f1(d + 1);
      return `<circle class="gr-mk gr-mk-part-o" cx="${cx}" cy="${cy}" r="3"/><path class="gr-mk gr-mk-part-f" d="M${cx} ${f1(cy - 3)}A3 3 0 0 0 ${cx} ${f1(cy + 3)}Z"/>`;
    }
    return '';
  }

  function svgTextLines(x, y, lines, anchor, cls) {
    return `<text class="${cls}" x="${f1(x)}" y="${f1(y)}" text-anchor="${anchor}">${lines.map((s, i) => `<tspan x="${f1(x)}" dy="${i === 0 ? 0 : NET_FS + 3}"${i === 0 ? ' class="gl-1"' : ''}>${esc(s)}</tspan>`).join('')}</text>`;
  }

  // 보유 비율 링 차트(8.1의 5번): 바탕 원과 12시부터 시계 방향으로 채운 호
  function ringSVG(R, f) {
    const bg = `<circle class="gr-ring-bg" r="${f1(R)}"/>`;
    if (!(f > 0)) return `<g class="gr-ring" aria-hidden="true">${bg}</g>`;
    if (f >= 1) return `<g class="gr-ring" aria-hidden="true">${bg}<circle class="gr-ring-fg" r="${f1(R)}"/></g>`;
    const a = 2 * Math.PI * f;
    const d = `M0 ${f1(-R)}A${f1(R)} ${f1(R)} 0 ${f > 0.5 ? 1 : 0} 1 ${f1(R * Math.sin(a))} ${f1(-R * Math.cos(a))}`;
    return `<g class="gr-ring" aria-hidden="true">${bg}<path class="gr-ring-fg" d="${d}"/></g>`;
  }

  function netSVG(g, c, lay) {
    const sc = lay.sc;
    const W = lay.W, H = lay.H;
    const domIdx = si => { const i = domOrder(g).indexOf(sc.info.get(si).dom); return i < 0 ? 4 : Math.min(i, 4); };
    const parts = [];
    parts.push(`<defs><pattern id="gr-hatch" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(135)"><line class="gr-hatch-l" x1="0" y1="0" x2="0" y2="5"/></pattern></defs>`);
    // 그룹 원
    parts.push('<g class="gr-l-groups">');
    sc.groups.forEach(grp => {
      const gg = lay.gpos.get(grp.key);
      const lines = groupLines(sc, grp);
      const domCnt = domCountText(g, grp.members);
      parts.push(`<circle class="gr-g gr-g-${grp.cls}" cx="${f1(gg.x)}" cy="${f1(gg.y)}" r="${f1(gg.R)}" data-gr-group="${esc(grp.key)}" data-gr-count="${grp.members.length}" data-aim="circle" data-tip-title="${esc(lines[0])}" data-tip-sub="${esc([lines[1], domCnt, t('grTipGroupHint')].filter(Boolean).join(' / '))}"/>`);
    });
    parts.push('</g>');
    // 번들 엣지
    parts.push('<g class="gr-l-edges">');
    lay.bundles.forEach(b => {
      parts.push(`<line class="gr-e gr-e-bundle" data-tip-title="${esc(t('grLgBundle'))}" x1="${f1(b.x1)}" y1="${f1(b.y1)}" x2="${f1(b.x2)}" y2="${f1(b.y2)}" stroke-width="${f1(b.w)}" data-gr-ekind="보유" data-gr-bundle="1" data-gr-s="${esc(lay.anc[b.slot].id)}" data-gr-t="${esc(b.key)}" data-gr-slot="${b.slot}"/>`);
    });
    parts.push('</g><g class="gr-l-hot"></g><g class="gr-l-xe"></g><g class="gr-l-ghost" aria-hidden="true"></g>');
    // 표준담보 노드
    parts.push('<g class="gr-l-nodes">');
    sc.stds.forEach(si => {
      const p = lay.npos.get(si);
      const it = sc.info.get(si);
      const jd = lay.jd.per.get(si);
      const n = g.N[si];
      const grpName = groupLines(sc, sc.groupMap.get(it.key))[0];
      const chips = verdictChips(lay, si);
      const more = chips.length > 3 ? t('grTipMoreTpl', { n: fmt(chips.length - 3) }) : '';
      const benNote = it.per.map(x => t('grBenCntTpl', { org: orgOf(x.code), n: fmt(+(x.e.p['급부수'] || 0)) })).join(', ');
      // 타사 4개사 이상: 어느 타사가 보유했는지 위치로 드러나지 않으므로 보유 비율 링 차트와 툴팁 문장(8.1의 5번)
      const ringTx = sc.nPeer > 3 ? t('grRingTpl', { n: fmt(sc.nPeer), k: fmt(it.kp) }) : '';
      const sub = [it.dom, grpName, ringTx].concat(markLines(g, c, lay, si), [benNote, more]).filter(Boolean).join(' / ');
      const wait = jd.marks.includes('wait');
      parts.push(`<g class="gr-n gr-n-${it.cls}${wait ? ' is-wait' : ''}" style="--gr-sh:${(3 / p.r).toFixed(3)}" transform="translate(${f1(p.x)} ${f1(p.y)})" tabindex="-1" role="button" aria-label="${esc(n.l)}" data-gr-fk="n:${esc(n.id)}" data-gr-id="${esc(n.id)}" data-gr-idx="${si}" data-gr-kind="표준담보" data-gr-r="${f1(p.r)}" data-gr-group="${esc(it.key)}" data-gr-cls="${it.cls}" data-gr-mark="${jd.marks.join(' ')}" data-aim="circle" data-tip-title="${esc(n.l)}" data-tip-sub="${esc(sub)}"${chips.length ? ` data-tip-chips="${esc(JSON.stringify(chips.slice(0, 3)))}"` : ''}>`
        + `<circle class="gr-n-c" r="${f1(p.r)}" style="fill:var(--gr-dom-${domIdx(si)})"/>`
        + (sc.nPeer > 3 ? ringSVG(p.r + 2, it.kp / sc.nPeer) : '')
        + jd.marks.filter(m => m !== 'wait').map(m => markGlyph(m, p.r)).join('')
        + '</g>');
    });
    parts.push('</g>');
    // 앵커
    parts.push('<g class="gr-l-anchors">');
    lay.anc.forEach(a => {
      const vs = g.summary && g.summary['종형'] && g.summary['종형'][a.id];
      const held = g.heldBy.get(a.vi);
      const dc = vs && vs['보장분야별'] ? domOrder(g).map(d => (vs['보장분야별']['CAT:' + d] ? `${d} ${fmt(vs['보장분야별']['CAT:' + d])}` : '')).filter(Boolean).join(', ') : '';
      const sub = [orgOf(a.code), fullVarName(g, a.vi), t('grAnchorHeldTpl', { n: fmt(held ? held.size : 0) }), dc].filter(Boolean).join(' / ');
      parts.push(`<g class="gr-a${a.slot === 0 ? ' is-base' : ''}" transform="translate(${f1(a.x)} ${f1(a.y)})" tabindex="-1" role="button" aria-label="${esc(fullVarName(g, a.vi))}" data-gr-fk="a:${esc(a.key)}" data-gr-slot="${a.slot}" data-gr-id="${esc(a.id)}" data-gr-idx="${a.vi}" data-gr-kind="종형" data-gr-r="${f1(a.r)}" data-gr-akey="${esc(a.key)}" data-aim="circle" data-tip-title="${esc(fullVarName(g, a.vi))}" data-tip-sub="${esc(sub)}"><circle class="gr-a-c" r="${f1(a.r)}"/></g>`);
    });
    parts.push('</g><g class="gr-l-exp"></g>');
    // 라벨
    parts.push('<g class="gr-l-labels">');
    lay.anc.forEach(a => {
      const b = a.box;
      const x = a.slot === 0 ? (b[0] + b[2]) / 2 : b[0] + 2;   // 왼쪽으로 옮긴 라벨도 상자 왼쪽에서 시작한다
      parts.push(`<g class="gr-lb gr-lb-a" data-gr-lb="anchor" data-gr-lbox="${[b[0], b[1], b[2], b[3]].map(f1).join(',')}">${svgTextLines(x, b[1] + textAsc(), a.lines, a.slot === 0 ? 'middle' : 'start', 'gr-tx')}</g>`);
    });
    sc.groups.forEach(grp => {
      const gl = lay.glabels.get(grp.key);
      const b = gl.box;
      if (gl.badge) {
        parts.push(`<g class="gr-lb gr-lb-badge" tabindex="-1" role="button" aria-label="${esc(gl.lines.join(', '))}" data-gr-fk="g:${esc(grp.key)}" data-gr-lb="badge" data-gr-glabel="${esc(grp.key)}" data-gr-lbox="${b.map(f1).join(',')}" data-aim="rect" data-tip-title="${esc(gl.lines[0])}" data-tip-sub="${esc(gl.lines[1])}"><rect x="${f1(b[0])}" y="${f1(b[1])}" width="${f1(b[2] - b[0])}" height="${f1(b[3] - b[1])}"/><text class="gr-tx" x="${f1((b[0] + b[2]) / 2)}" y="${f1(b[1] + 1 + textAsc())}" text-anchor="middle">${fmt(grp.members.length)}</text></g>`);
        return;
      }
      const lead = gl.lead ? `<line class="gr-lead" x1="${f1(gl.lead[0])}" y1="${f1(gl.lead[1])}" x2="${f1(gl.lead[2])}" y2="${f1(gl.lead[3])}"/>` : '';
      parts.push(`${lead}<g class="gr-lb gr-lb-g" tabindex="-1" role="button" aria-label="${esc(gl.lines.join(', '))}" data-gr-fk="g:${esc(grp.key)}" data-gr-lb="group" data-gr-glabel="${esc(grp.key)}" data-gr-lbox="${b.map(f1).join(',')}" data-aim="rect" data-tip-title="${esc(gl.lines[0])}" data-tip-sub="${esc([gl.lines[1], domCountText(g, grp.members), t('grTipGroupHint')].filter(Boolean).join(' / '))}"><rect class="gr-lb-hit" x="${f1(b[0])}" y="${f1(b[1])}" width="${f1(b[2] - b[0])}" height="${f1(b[3] - b[1])}"/>${svgTextLines(b[0] + 2, b[1] + textAsc(), gl.lines, 'start', 'gr-tx')}</g>`);
    });
    lay.slabels.forEach((b, si) => {
      parts.push(`<text class="gr-tx gr-lb-s" data-gr-lb="std" data-gr-for="${esc(g.N[si].id)}" data-gr-lbox="${b.map(f1).join(',')}" x="${f1(b[0])}" y="${f1(b[1] + textAsc())}">${esc(g.N[si].l)}</text>`);
    });
    parts.push('</g>');
    return `<svg class="gr-net-svg" id="gr-net-svg" xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="group" aria-label="${esc(t('grNetAria'))}" data-gr-w="${W}" data-gr-h="${H}" data-gr-k="${f1(lay.k)}" data-gr-ms="${f1(lay.ms)}">${parts.join('')}</svg>`;
  }

  function domCountText(g, members) {
    const cnt = new Map();
    members.forEach(si => { const d = domOf(g, si); cnt.set(d, (cnt.get(d) || 0) + 1); });
    return domOrder(g).filter(d => cnt.get(d)).map(d => `${d} ${fmt(cnt.get(d))}`).join(', ');
  }

  // 그래프 영역 크기: 가운데 영역(#z-center)에서 탐색 경로 행을 뺀 폭과 높이(3.1)
  function netArea(host) {
    const zc = document.getElementById('z-center');
    if (!zc || !host) return [0, 0];
    const cs = getComputedStyle(zc);
    const W = Math.floor(host.clientWidth);
    const H = Math.floor(zc.getBoundingClientRect().bottom - parseFloat(cs.paddingBottom) - host.getBoundingClientRect().top);
    return [W, H];
  }

  function netRelEdges(g, sc, si) {
    const out = [];
    (g.stdRels.get(si) || []).forEach(rl => { if (sc.info.has(rl.other)) out.push({ e: g.E[rl.e], other: rl.other }); });
    return out;
  }

  // 근거 경로(5.3): 덮는 담보까지 바로 이어지는 담보 관계 엣지, 없으면 화면에 있는 중간 담보 하나를 거치는 경로
  function evidenceEdges(g, lay, si) {
    const sc = lay.sc, jd = lay.jd.per.get(si);
    if (!jd || !jd.cov) return [];
    let targets = [];
    if (jd.marks.includes('ours-wide') || jd.marks.includes('ours-part')) targets = jd.cov.oursRel[1] || [];
    else if (jd.marks.includes('peer-rel')) {
      jd.cov.pv.forEach(x => { if (x.v && x.v.cause === CAUSE_REL) { const pr = jd.cov.peerRel(x.peer); if (pr) targets = targets.concat(pr[1] || []); } });
    }
    const out = new Set();
    targets.forEach(id => {
      const ti = g.byId.get(id);
      if (ti == null || !sc.info.has(ti)) return;
      const direct = (g.stdRels.get(si) || []).find(rl => rl.other === ti);
      if (direct) { out.add(direct.e); return; }
      for (const rl of (g.stdRels.get(si) || [])) {
        if (!sc.info.has(rl.other)) continue;
        const second = (g.stdRels.get(rl.other) || []).find(r2 => r2.other === ti);
        if (second) { out.add(rl.e); out.add(second.e); break; }
      }
    });
    return Array.from(out).map(ei => g.E[ei]);
  }

  function lineBetween(p, q, rp, rq) {
    const dx = q.x - p.x, dy = q.y - p.y, d = Math.hypot(dx, dy) || 1;
    const ux = dx / d, uy = dy / d;
    return [p.x + ux * rp, p.y + uy * rp, q.x - ux * rq, q.y - uy * rq];
  }

  function hotEdgesHTML(g, lay, focus) {
    if (!focus) return '';
    const sc = lay.sc;
    const out = [];
    const heldLine = (slot, si) => {
      const a = lay.anc[slot], p = lay.npos.get(si);
      const [x1, y1, x2, y2] = lineBetween(a, p, a.r, p.r);
      const he = g.heldBy.get(a.vi) && g.heldBy.get(a.vi).get(si);
      out.push(`<line class="gr-e gr-e-held" x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}" data-gr-ekind="보유" data-gr-s="${esc(a.id)}" data-gr-t="${esc(g.N[si].id)}"${he ? ` data-gr-key="e:${he.i}"` : ''} data-tip-title="${esc(t('grLgHeldOne'))}"/>`);
    };
    const relLine = e => {
      const p = lay.npos.get(e.s), q = lay.npos.get(e.t);
      if (!p || !q) return;
      const [x1, y1, x2, y2] = lineBetween(p, q, p.r, q.r);
      const kind = e.p['관계'] === '통합' ? 'uni' : 'inc';
      out.push(`<line class="gr-e gr-e-rel gr-e-rel-${kind}" x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}" data-gr-ekind="담보 관계" data-gr-s="${esc(g.N[e.s].id)}" data-gr-t="${esc(g.N[e.t].id)}" data-gr-key="e:${e.i}" data-tip-title="${esc(kind === 'uni' ? t('grLgRelUni') : t('grLgRelInc'))}"/>`);
    };
    if (focus.t === 'std') {
      const it = sc.info.get(focus.si);
      if (!it) return '';
      // 펼친 담보는 종형에서 특약, 급부를 거쳐 담보로 가는 엣지가 보유를 보이므로 개별 보유 엣지를 겹쳐 그리지 않는다
      if (!(net.ex && net.ex.si === focus.si)) it.slots.forEach(slot => heldLine(slot, focus.si));
      const seen = new Set();
      netRelEdges(g, sc, focus.si).forEach(({ e }) => { seen.add(e.i); relLine(e); });
      evidenceEdges(g, lay, focus.si).forEach(e => { if (!seen.has(e.i)) { seen.add(e.i); relLine(e); } });
    } else if (focus.t === 'anchor') {
      sc.stds.forEach(si => { if (sc.info.get(si).slots.includes(focus.slot)) heldLine(focus.slot, si); });
      // 타사 4개사 이상은 기본 화면에 기준 종형의 번들 엣지만 있으므로, 타사 앵커를 호버하면 그 타사의 번들 엣지를 그린다(8.1의 4번)
      if (sc.nPeer > 3 && focus.slot !== 0) {
        const a = lay.anc[focus.slot];
        sc.groups.forEach(grp => {
          const n = grp.members.filter(si => sc.info.get(si).slots.includes(focus.slot)).length;
          if (!n) return;
          const gg = lay.gpos.get(grp.key);
          const [x1, y1, x2, y2] = lineBetween(a, gg, a.r, gg.R);
          out.push(`<line class="gr-e gr-e-bundle is-keep" stroke-width="${f1(Math.min(6, 0.6 + 0.18 * n))}" x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}" data-gr-ekind="보유" data-gr-s="${esc(a.id)}" data-gr-t="${esc(grp.key)}" data-tip-title="${esc(t('grLgBundle'))}"/>`);
        });
      }
    }
    return out.join('');
  }

  // 강조할 노드와 앵커, 그룹(호버, 선택, 필터)
  function focusSets(g, lay, focus) {
    const sc = lay.sc;
    const nodes = new Set(), anchors = new Set(), groups = new Set();
    if (focus.t === 'std') {
      const it = sc.info.get(focus.si);
      if (!it) return null;
      nodes.add(focus.si);
      it.slots.forEach(s => anchors.add(s));
      groups.add(it.key);
      netRelEdges(g, sc, focus.si).forEach(({ other }) => nodes.add(other));
      evidenceEdges(g, lay, focus.si).forEach(e => { nodes.add(e.s); nodes.add(e.t); });
    } else if (focus.t === 'anchor') {
      anchors.add(focus.slot);
      sc.stds.forEach(si => { if (sc.info.get(si).slots.includes(focus.slot)) { nodes.add(si); groups.add(sc.info.get(si).key); } });
    } else if (focus.t === 'group') {
      groups.add(focus.key);
      (sc.groupMap.get(focus.key) || { members: [] }).members.forEach(si => nodes.add(si));
      const grp = sc.groupMap.get(focus.key);
      if (grp) (grp.slots || []).forEach(s => anchors.add(s));
    }
    return { nodes, anchors, groups };
  }

  function filterSet(g, lay) {
    const f = state.filter;
    if (!f) return null;
    const sc = lay.sc;
    const out = new Set();
    sc.stds.forEach(si => {
      const it = sc.info.get(si);
      if (f.startsWith('f:') && lay.jd.per.get(si).hits.has(f.slice(2))) out.add(si);
      else if (f.startsWith('cls:') && it.cls === f.slice(4)) out.add(si);
      else if (f.startsWith('dom:') && it.dom === f.slice(4)) out.add(si);
    });
    return out;
  }

  // 선택, 필터, 호버 상태를 클래스와 강조 엣지로 반영한다(배치는 다시 계산하지 않는다)
  function applyNetState() {
    // 펼친 노드를 지우면 포커스가 빠지며(focusout) 다시 들어오므로 겹쳐 실행하지 않는다
    if (net.applying) return;
    net.applying = true;
    try { applyNetStateInner(); } finally { net.applying = false; }
  }

  function applyNetStateInner() {
    const svg = lastCenterEl && lastCenterEl.querySelector('#gr-net-svg');
    const lay = net.lay;
    if (!svg || !lay) return;
    const g = ensureGraph();
    const sc = lay.sc;
    const selStd = state.selStd != null && sc.info.has(state.selStd) ? state.selStd : null;
    const selFocus = selStd != null ? { t: 'std', si: selStd }
      : state.selGroup && sc.groupMap.has(state.selGroup) ? { t: 'group', key: state.selGroup } : null;
    const hov = net.hover && net.hover.t !== 'edge' && net.hover.t !== 'x' ? net.hover : null;
    const focus = hov || selFocus;
    const fs = focus ? focusSets(g, lay, focus) : null;
    const flt = filterSet(g, lay);
    // 담보를 선택하면 회사별 특약과 급부를 펼친다(위치 트랜지션 중에는 접어 두고 도착한 뒤 펼친다)
    const ex = selStd != null && !net.moving ? expandLayout(g, lay, selStd, state.expSlot) : null;
    const big = ex ? focusSets(g, lay, { t: 'std', si: selStd }).nodes : null;
    const expLayer = svg.querySelector('.gr-l-exp');
    const prevEx = net.exShown;
    if (ex !== prevEx) {
      if (expLayer) {
        if (prevEx && expLayer.firstChild && moveDur()) {
          // 접을 때는 펼칠 때의 60% 시간으로 빠진다
          const ghost = svg.querySelector('.gr-l-ghost');
          const old = document.createElementNS('http://www.w3.org/2000/svg', 'g');
          old.setAttribute('class', 'gr-x-out');
          while (expLayer.firstChild) old.appendChild(expLayer.firstChild);
          const xe = svg.querySelector('.gr-l-xe');
          while (xe && xe.lastChild) old.insertBefore(xe.lastChild, old.firstChild);
          ghost.appendChild(old);
          setTimeout(() => old.remove(), Math.round(320 * 0.6 * (App.motionScale ? App.motionScale() : 1)) + 40);
        }
        expLayer.innerHTML = ex ? expNodesHTML(g, lay, ex) : '';
        const xe = svg.querySelector('.gr-l-xe');
        if (xe) xe.innerHTML = ex ? expEdgesHTML(g, lay, ex) : '';
      }
      net.exShown = ex;
    }
    net.ex = ex;
    svg.classList.toggle('is-exp', !!ex);
    svg.classList.toggle('is-hl', !!(hov && fs));
    svg.classList.toggle('is-selm', !hov && !!(selFocus && fs));
    svg.classList.toggle('is-flt', !!flt && !(focus && fs));
    const sel = App.state.sel.graph;
    svg.querySelectorAll('.gr-l-nodes > .gr-n').forEach(el => {
      const si = +el.dataset.grIdx;
      el.classList.toggle('is-keep', !!(fs && fs.nodes.has(si)));
      el.classList.toggle('is-big', !!(big && big.has(si)));
      el.classList.toggle('is-on', !!(flt && flt.has(si)));
      const on = selStd === si;
      el.classList.toggle('is-sel', on);
      if (on) el.setAttribute('data-sel-anchor', '1'); else el.removeAttribute('data-sel-anchor');
    });
    svg.querySelectorAll(':scope > .gr-l-labels .gr-lb-s').forEach(el => {
      const si = g.byId.get(el.dataset.grFor);
      el.classList.toggle('is-keep', !!(fs && fs.nodes.has(si)));
      el.classList.toggle('is-big', !!(big && big.has(si)));
      el.classList.toggle('is-on', !!(flt && flt.has(si)));
    });
    svg.querySelectorAll('.gr-l-anchors > .gr-a').forEach((el, slot) => el.classList.toggle('is-keep', !!(fs && fs.anchors.has(slot))));
    svg.querySelectorAll('.gr-l-groups > .gr-g').forEach(el => {
      const key = el.dataset.grGroup;
      el.classList.toggle('is-keep', !!(fs && fs.groups.has(key)));
      const on = !!(selFocus && selFocus.t === 'group' && selFocus.key === key);
      el.classList.toggle('is-gsel', on);
      if (on) el.setAttribute('data-sel-anchor', '1'); else el.removeAttribute('data-sel-anchor');
    });
    svg.querySelectorAll(':scope > .gr-l-labels :is(.gr-lb-g, .gr-lb-badge)').forEach(el => el.classList.toggle('is-keep', !!(fs && fs.groups.has(el.dataset.grGlabel))));
    svg.querySelectorAll(':scope > .gr-l-edges .gr-e-bundle').forEach(el => {
      const keep = fs && ((focus.t === 'group' && el.dataset.grT === focus.key) || (focus.t === 'anchor' && +el.dataset.grSlot === focus.slot));
      el.classList.toggle('is-keep', !!keep);
    });
    const hot = svg.querySelector('.gr-l-hot');
    if (hot) {
      // 호버한 담보가 있으면 그 담보의 엣지를, 없으면 선택한 담보의 엣지를 그린다. 펼친 엣지는 선택한 담보에만
      const hf = focus && focus.t !== 'group' ? focus : null;
      hot.innerHTML = net.moving ? '' : hotEdgesHTML(g, lay, hf);
    }
    if (expLayer) {
      expLayer.querySelectorAll('.gr-x').forEach(el => {
        const ni = el.dataset.grIdx != null ? +el.dataset.grIdx : null;
        const on = ni != null && sel === 'n:' + el.dataset.grId;
        el.classList.toggle('is-sel', on);
        if (on) el.setAttribute('data-sel-anchor', '1'); else el.removeAttribute('data-sel-anchor');
      });
    }
    // 선택한 엣지와 호버한 엣지
    svg.querySelectorAll('.is-esel, .is-ehov').forEach(el => el.classList.remove('is-esel', 'is-ehov'));
    const es = state.selEdge && edgeElOf(svg, state.selEdge);
    if (es) es.classList.add('is-esel');
    const eh = net.hover && net.hover.t === 'edge' && edgeElOf(svg, net.hover.key);
    if (eh) eh.classList.add('is-ehov');
    syncRoving(svg);
  }

  function netHit(svg, clientX, clientY) {
    const lay = net.lay;
    if (!lay) return null;
    const r = svg.getBoundingClientRect();
    const x = clientX - r.left, y = clientY - r.top;
    let best = null, bd = Infinity;
    const big = net.ex ? focusSets(ensureGraph(), lay, { t: 'std', si: net.ex.si }).nodes : null;
    lay.npos.forEach((p, si) => {
      const rr = big && !big.has(si) ? 3 : p.r;
      const d = Math.hypot(p.x - x, p.y - y);
      if (d <= Math.max(rr + 4, 12) && d < bd) { bd = d; best = { t: 'std', si }; }
    });
    lay.anc.forEach(a => {
      const d = Math.hypot(a.x - x, a.y - y);
      if (d <= Math.max(a.r + 4, 12) && d < bd) { bd = d; best = { t: 'anchor', slot: a.slot }; }
    });
    if (net.ex) net.ex.nodes.forEach((nd, i) => {
      const d = Math.hypot(nd.x - x, nd.y - y);
      if (d <= Math.max(nd.r + 4, 12) && d < bd) { bd = d; best = { t: 'x', i }; }
    });
    if (best) return best;
    for (const [key, gl] of lay.glabels) {
      const b = gl.box;
      if (x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3]) return { t: 'group', key };
    }
    const eh = edgeHit(svg, x, y);
    if (eh) return eh;
    for (const [key, gg] of lay.gpos) if (Math.hypot(gg.x - x, gg.y - y) <= gg.R) return { t: 'group', key };
    return null;
  }

  function hitEl(svg, h) {
    if (!h) return null;
    const g = ensureGraph();
    if (h.t === 'std') return svg.querySelector(`.gr-l-nodes > .gr-n[data-gr-id="${CSS.escape(g.N[h.si].id)}"]`);
    if (h.t === 'anchor') return svg.querySelectorAll('.gr-l-anchors > .gr-a')[h.slot] || null;
    if (h.t === 'x') return svg.querySelector(`.gr-x[data-gr-x="${h.i}"]`);
    if (h.t === 'edge') return edgeElOf(svg, h.key);
    return svg.querySelector(`[data-gr-glabel="${CSS.escape(h.key)}"]`) || svg.querySelector(`.gr-g[data-gr-group="${CSS.escape(h.key)}"]`);
  }

  const sameHit = (a, b) => (!a && !b) || (a && b && a.t === b.t && a.si === b.si && a.slot === b.slot && a.key === b.key && a.i === b.i);

  function netHover(h) {
    const svg = lastCenterEl && lastCenterEl.querySelector('#gr-net-svg');
    if (!svg) return;
    const show = () => {
      const el = hitEl(svg, h);
      if (!el) { App.aim.hide(); App.aim.hideTip(); return; }
      // 엣지는 가운데 종류 이름만 보인다(조준 표시 없이)
      if (h.t === 'edge') { App.aim.hide(); App.aim.showTip(el); return; }
      App.aim.set(el); App.aim.showTip(el);
    };
    if (sameHit(h, net.hover)) { if (h) show(); return; }
    net.hover = h;
    applyNetState();
    show();
  }

  function clearSel() {
    state.selStd = null;
    state.selGroup = null;
    state.selNode = null;
    state.selEdge = null;
    state.expSlot = null;
  }

  function netSelectStd(si, opts = {}) {
    const g = ensureGraph();
    if (state.preset !== 'cover') initPresetState('cover', App.ctx(), true);
    pushUndo();
    clearSel();
    state.selStd = si;
    net.focusKey = net.selFk = 'n:' + g.N[si].id;
    recordTrail(g.N[si].l, true);
    if (opts.rerender) rerenderGraph(false); else { applyNetState(); refreshTrail(); }
    if (!opts.noPanel) App.select('n:' + g.N[si].id, { animate: true, focus: false });
  }

  function netSelectGroup(key) {
    const lay = net.lay;
    if (!lay || !lay.sc.groupMap.has(key)) return;
    pushUndo();
    clearSel();
    state.selGroup = key;
    net.focusKey = net.selFk = 'g:' + key;
    recordTrail(groupLines(lay.sc, lay.sc.groupMap.get(key))[0], true);
    applyNetState();
    refreshTrail();
    App.select('grp:' + key, { animate: true, focus: false });
  }

  function netOpenVariant(vi) {
    openAlt('variant', vi, null);
  }


  function netClickHit(h, svg) {
    const g = ensureGraph();
    if (!h) {
      if (App.state.sel.graph != null || state.selStd != null || state.selGroup || state.selEdge) App.unselect({ restoreFocus: false });
      return;
    }
    if (h.t === 'std') netSelectStd(h.si);
    else if (h.t === 'group') netSelectGroup(h.key);
    else if (h.t === 'anchor') netOpenVariant(net.lay.anc[h.slot].vi);
    else if (h.t === 'edge') {
      state.selEdge = h.key;
      applyNetState();
      App.select('edge:' + h.key, { animate: true, focus: false });
    } else if (h.t === 'x' && net.ex) {
      const nd = net.ex.nodes[h.i];
      if (!nd) return;
      if (nd.kind === 'summary') { pushUndo(); state.expSlot = nd.slot; applyNetState(); return; }
      if (nd.kind === 'more') { netOpenVariant(net.lay.anc[nd.slot].vi); return; }
      net.focusKey = net.selFk = 'x:' + h.i;
      state.selEdge = null;
      App.select('n:' + g.N[nd.ni].id, { animate: true, focus: false });
      applyNetState();
    }
  }

  function netClick(e, svg) {
    // 클릭하면 이전 호버나 키보드 포커스 강조 대신 선택 상태를 보인다(다음 포인터 이동에서 호버를 다시 잰다)
    net.hover = null;
    netClickHit(netHit(svg, e.clientX, e.clientY), svg);
  }

  function refreshTrail() {
    const nav = lastCenterEl && lastCenterEl.querySelector('#gr-stage-root > .gr-trail');
    if (nav) nav.outerHTML = trailNavHTML();
  }

  function renderNetInto(host, lay) {
    const g = ensureGraph();
    const c = App.ctx();
    net.lay = lay;
    net.ex = null;
    net.exShown = null;
    host.innerHTML = netSVG(g, c, lay);
    host.style.height = lay.H + 'px';
    applyNetState();
  }

  // 1,000px 미만(8.3): 그룹 카드를 우체국만 보유, 우체국과 타사 보유, 타사만 보유 차례로 쌓는다.
  // 카드마다 그룹 라벨 두 행, 보장 대분류 누적 막대, 표시가 붙은 담보 이름 칩. 칩을 탭하면 회사별 종형, 특약, 급부를 세로로 펼친다
  const NL_CLS = ['only', 'shared', 'peer'];
  function nlDomBarHTML(g, members) {
    const doms = domOrder(g);
    const cnt = doms.map(() => 0);
    members.forEach(si => { const i = doms.indexOf(domOf(g, si)); cnt[i < 0 ? 4 : Math.min(i, 4)] += 1; });
    const tx = domCountText(g, members);
    return `<div class="gr-nl-bar" role="img" aria-label="${esc(tx)}">${cnt.map((n, i) => n ? `<span style="flex-grow:${n};background:var(--gr-dom-${i})"></span>` : '').join('')}</div><div class="gr-nl-dc">${esc(tx)}</div>`;
  }
  function nlChipHTML(g, si, marks, dom, on) {
    const glyphs = marks.filter(m => m !== 'wait');
    const wait = marks.includes('wait');
    const sw = `<svg class="gr-nl-sw" width="24" height="22" viewBox="-11 -11 24 22" aria-hidden="true"><g class="gr-n${wait ? ' is-wait' : ''}"><circle class="gr-n-c" r="5" style="fill:var(--gr-dom-${dom})"/>${glyphs.map(m => markGlyph(m, 5)).join('')}</g></svg>`;
    const mk = marks.map(m => t(MARK_KEY[m])).join(', ');
    return `<button type="button" class="gr-nl-chip${on ? ' is-sel' : ''}" data-gr-node="${esc(g.N[si].id)}" data-gr-idx="${si}" aria-expanded="${on}"${mk ? ` data-tip-title="${esc(g.N[si].l)}" data-tip-sub="${esc(mk)}"` : ''}>${sw}<span>${esc(g.N[si].l)}</span>${mk ? `<span class="gr-nl-mk">${esc(mk)}</span>` : ''}</button>`;
  }
  // 한 종형에서 그 담보로 가는 특약과 급부(그래프 펼침과 같은 차례)
  function nlChainHTML(g, vi, si) {
    const chain = chainOf(g, vi, si);
    if (!chain.length) return '';
    return chain.map(rc => `<li class="gr-nl-r"><span class="gr-nl-rn">${esc(riderBody(g.N[rc.ri].l))}${renewText(rc.ri) ? ` (${esc(renewText(rc.ri))})` : ''}</span>
      <ul class="gr-nl-bens">${rc.bens.map(x => `<li class="${x.rec ? 'is-rec' : ''}">${esc(g.N[x.b].l)}${x.rec ? ` <span class="gr-nl-mk">${esc(t('grLgRec'))}</span>` : ''}</li>`).join('')}</ul></li>`).join('');
  }
  function nlExpandHTML(g, sc, si) {
    const it = sc.info.get(si);
    return `<div class="gr-nl-exp"><button type="button" class="gr-nl-more" data-gr-detail="n:${esc(g.N[si].id)}">${esc(t('grNlDetail'))}</button>${it.per.map(x => `<div class="gr-nl-org"><div class="gr-nl-oh"><span>${esc(orgOf(x.code))}</span><span>${esc(fullVarName(g, x.vi))}</span></div>
      <ul class="gr-nl-rs">${nlChainHTML(g, x.vi, si)}</ul></div>`).join('')}</div>`;
  }
  function netNarrowHTML(g, c) {
    const sc = sceneOf(g, c);
    const jd = judgeOf(g, c, sc);
    const doms = domOrder(g);
    const domIdx = si => { const i = doms.indexOf(sc.info.get(si).dom); return i < 0 ? 4 : Math.min(i, 4); };
    const groups = sc.groups.slice().sort((a, b) => NL_CLS.indexOf(a.cls) - NL_CLS.indexOf(b.cls));
    return groups.map(grp => {
      const lines = groupLines(sc, grp);
      const chips = grp.members.map(si => nlChipHTML(g, si, jd.per.get(si).marks, domIdx(si), state.selStd === si)
        + (state.selStd === si ? nlExpandHTML(g, sc, si) : '')).join('');
      return `<section class="gr-nl-card gr-nl-${grp.cls}" data-gr-group="${esc(grp.key)}"><div class="gr-nl-hd"><span class="gl-1">${esc(lines[0])}</span><span>${esc(lines[1])}</span></div>
        ${nlDomBarHTML(g, grp.members)}<div class="gr-nl-chips">${chips}</div></section>`;
    }).join('');
  }

  // ---------- 담보 선택: 회사별 특약과 급부 펼치기(4.3) ----------
  const EXP_RIDER_MAX = 12, EXP_BEN_MAX = 39, EXP_F_RIDER = 0.30, EXP_F_BEN = 0.68, EXP_F_SUM = 0.50;
  const EXP_RR = 6, EXP_RB = 5, EXP_GAP = 4, EXP_LABEL_MAX = 6, EXP_ITERS = 160;
  let recIdx = null;
  const expCache = new Map();

  // 매핑 검수 대기 급부: 추천표준담보ID 로 찾는다(매핑 엣지가 아니라 추천)
  function recBensOf(g, sid) {
    if (!recIdx) {
      recIdx = new Map();
      g.N.forEach(n => {
        const r = n.k === NK['급부'] && n.p ? n.p['추천표준담보ID'] : null;
        if (!r) return;
        if (!recIdx.has(r)) recIdx.set(r, []);
        recIdx.get(r).push(n.i);
      });
    }
    return recIdx.get(sid) || [];
  }

  function edgeIdx(g, s, t2, ekName) {
    const ek = EK[ekName];
    const a = (g.adj[s] || []).find(x => x.isOut && x.j === t2 && x.ek === ek);
    return a ? a.e : null;
  }

  // 종형 vi 에서 표준담보 si 에 이르는 특약과 급부(graph.json 노드 차례, 급부는 특약 차례대로)
  function chainOf(g, vi, si) {
    const byR = new Map();
    const add = (ben, rec) => (g.benRiders.get(ben) || []).forEach(ri => {
      if (!(g.riderVars.get(ri) || []).includes(vi)) return;
      let a = byR.get(ri);
      if (!a) { a = []; byR.set(ri, a); }
      if (!a.some(x => x.b === ben)) a.push({ b: ben, rec });
    });
    (g.stdBens.get(si) || []).forEach(({ ben }) => add(ben, false));
    recBensOf(g, g.N[si].id).forEach(ben => { if (!(g.benStds.get(ben) || []).some(x => x.std === si)) add(ben, true); });
    return Array.from(byR.keys()).sort((a, b) => a - b).map(ri => ({ ri, bens: byR.get(ri).sort((x, y) => x.b - y.b) }));
  }

  // 선분이 사각 상자(여백 pad)를 지나는지(Liang-Barsky)
  function segHitsBox(x1, y1, x2, y2, b, pad) {
    const bx0 = b[0] - pad, by0 = b[1] - pad, bx1 = b[2] + pad, by1 = b[3] + pad;
    let t0 = 0, t1 = 1;
    const dx = x2 - x1, dy = y2 - y1;
    const ps = [-dx, dx, -dy, dy], qs = [x1 - bx0, bx1 - x1, y1 - by0, by1 - y1];
    for (let i = 0; i < 4; i++) {
      if (Math.abs(ps[i]) < 1e-9) { if (qs[i] < 0) return false; continue; }
      const r = qs[i] / ps[i];
      if (ps[i] < 0) { if (r > t1) return false; if (r > t0) t0 = r; } else { if (r < t0) return false; if (r < t1) t1 = r; }
    }
    return t0 <= t1;
  }

  function expandLayout(g, lay, si, openSlot) {
    const ck = `${layoutKeyOf(lay)}|${si}|${openSlot == null ? '' : openSlot}`;
    if (expCache.has(ck)) return expCache.get(ck);
    const t0 = performance.now();
    const sc = lay.sc, it = sc.info.get(si);
    if (!it) return null;
    const big = focusSets(g, lay, { t: 'std', si }).nodes;
    const fixed = [];
    const circles = [];
    sc.stds.forEach(sj => {
      const p = lay.npos.get(sj);
      const r = big.has(sj) ? p.r : 3;
      fixed.push({ x: p.x, y: p.y, r });
      circles.push([p.x, p.y, r]);
    });
    lay.anc.forEach(a => { fixed.push({ x: a.x, y: a.y, r: a.r }); circles.push([a.x, a.y, a.r]); });
    // 고정 장애물: 줄인 기존 노드, 앵커, 앵커 라벨(4.3의 3번). 그룹 라벨도 장애물로 두어 펼친 노드가 라벨을 덮지 않게 한다
    const boxes = lay.anc.map(a => a.box).concat(Array.from(lay.glabels.values()).map(gl => gl.box));
    const sp = lay.npos.get(si);
    const cols = it.slots.map(slot => ({ slot, chain: chainOf(g, lay.anc[slot].vi, si), per: it.per.find(x => x.slot === slot) }));
    const benTotal = cols.reduce((s, cl) => s + cl.chain.slice(0, EXP_RIDER_MAX).reduce((u, r) => u + r.bens.length, 0), 0);
    const fold = sc.nPeer > 3 || benTotal > EXP_BEN_MAX;
    const nodes = [], edges = [], notes = [];
    cols.forEach(({ slot, chain, per }) => {
      const a = lay.anc[slot];
      const dx = sp.x - a.x, dy = sp.y - a.y, L = Math.hypot(dx, dy) || 1, ux = dx / L, uy = dy / L;
      const [nx, ny] = Math.abs(ux) >= 0.5 ? [0, 1] : [1, 0];
      const p = per && per.e ? per.e.p : {};
      const org = orgOf(a.code);
      const rN = +(p['특약수'] || 0), bN = +(p['급부수'] || 0);
      if (fold && slot !== 0 && openSlot !== slot) {
        const x = a.x + ux * L * EXP_F_SUM, y = a.y + uy * L * EXP_F_SUM;
        nodes.push({ kind: 'summary', id: 'SUM:' + a.id, slot, x, y, tx: x, ty: y, r: 8, g: null, text: t('grExpSumTpl', { org, r: fmt(rN), b: fmt(bN) }) });
        edges.push({ ek: '보유', key: per && per.e ? 'e:' + per.e.i : '', s: { anc: slot }, t: nodes.length - 1 });
        edges.push({ ek: '보유', key: per && per.e ? 'e:' + per.e.i : '', s: nodes.length - 1, t: { std: si } });
        return;
      }
      const shown = chain.slice(0, EXP_RIDER_MAX);
      const more = chain.length - shown.length;
      const spR = 2 * EXP_RR + EXP_GAP + 1, spB = 2 * EXP_RB + EXP_GAP + 1;
      const nR = shown.length + (more ? 1 : 0);
      const ridx = new Map();
      const first = nodes.length;
      shown.forEach((rc, k) => {
        const off = (k - (nR - 1) / 2) * spR;
        const x = a.x + ux * L * EXP_F_RIDER + nx * off, y = a.y + uy * L * EXP_F_RIDER + ny * off;
        nodes.push({ kind: '특약', ni: rc.ri, slot, x, y, tx: x, ty: y, r: EXP_RR, g: null });
        ridx.set(rc.ri, nodes.length - 1);
        edges.push({ ek: '포함', key: 'e:' + edgeIdx(g, a.vi, rc.ri, '포함'), s: { anc: slot }, t: nodes.length - 1 });
      });
      if (more) {
        const off = (shown.length - (nR - 1) / 2) * spR;
        const x = a.x + ux * L * EXP_F_RIDER + nx * off, y = a.y + uy * L * EXP_F_RIDER + ny * off;
        nodes.push({ kind: 'more', id: 'MORE:' + a.id, slot, x, y, tx: x, ty: y, r: EXP_RR, g: null, text: t('grExpMoreTpl', { n: fmt(more) }) });
      }
      const bl = [];
      shown.forEach(rc => rc.bens.forEach(b => bl.push({ ri: rc.ri, b: b.b, rec: b.rec })));
      bl.forEach((bb, k) => {
        const off = (k - (bl.length - 1) / 2) * spB;
        const x = a.x + ux * L * EXP_F_BEN + nx * off, y = a.y + uy * L * EXP_F_BEN + ny * off;
        const bp = g.N[bb.b].p || {};
        nodes.push({ kind: '급부', ni: bb.b, slot, x, y, tx: x, ty: y, r: EXP_RB, g: null, rec: bb.rec, wait: !!bp['추출검수대기항목'] });
        const bi = nodes.length - 1;
        edges.push({ ek: '포함', key: 'e:' + edgeIdx(g, bb.ri, bb.b, '포함'), s: ridx.get(bb.ri), t: bi });
        if (bb.rec) edges.push({ ek: 'rec', key: `rec:${bb.b}:${si}`, s: bi, t: { std: si } });
        else {
          const m = (g.benStds.get(bb.b) || []).find(x => x.std === si);
          const st = m ? (g.E[m.e].p || {})['검토상태'] : '';
          edges.push({ ek: '매핑', key: m ? 'e:' + m.e : '', s: bi, t: { std: si }, strong: st === '승인' || st === '수정' });
        }
      });
      notes.push({ slot, first, last: nodes.length, many: rN > EXP_LABEL_MAX, text: t('grExpColTpl', { org, r: fmt(rN), b: fmt(bN) }), side: a.x <= sp.x ? -1 : 1 });
    });
    if (nodes.length) runSync(simulate(nodes, fixed, boxes, [], { W: lay.W, H: lay.H, gap: EXP_GAP, qSame: -4, qDiff: -4, qdmax: 30, kg: 0, kt: 0.15, iters: EXP_ITERS }));
    // 라벨 장애물과 노드 간격이 맞서 겹침이 남으면 노드 간격을 우선해 한 번 더 정리한다(펼친 노드 겹침 0)
    if (nodes.length) {
      const X = Float64Array.from(nodes, nd => nd.x), Y = Float64Array.from(nodes, nd => nd.y), R = Float64Array.from(nodes, nd => nd.r);
      const cx = (x, r) => Math.min(Math.max(x, NET_MARGIN + r), lay.W - NET_MARGIN - r), cy = (y, r) => Math.min(Math.max(y, NET_MARGIN + r), lay.H - NET_MARGIN - r);
      const bad = () => { for (let i = 0; i < X.length; i++) { for (const f of fixed) if (Math.hypot(X[i] - f.x, Y[i] - f.y) < R[i] + f.r + EXP_GAP) return true; for (let j = i + 1; j < X.length; j++) if (Math.hypot(X[i] - X[j], Y[i] - Y[j]) < R[i] + R[j] + EXP_GAP) return true; } return false; };
      for (let k = 0; k < 2 && bad(); k++) runSync(relax(X, Y, R, fixed, [], EXP_GAP + 0.05, nodes, cx, cy, false));
      // 줄인 노드가 촘촘한 그룹 안에 갇혀 정리로 풀리지 않으면 가까운 빈 자리를 나선으로 찾아 옮긴다
      if (bad()) {
        const free = (i, x, y) => {
          if (x - R[i] < NET_MARGIN || y - R[i] < NET_MARGIN || x + R[i] > lay.W - NET_MARGIN || y + R[i] > lay.H - NET_MARGIN) return false;
          for (const f of fixed) if (Math.hypot(x - f.x, y - f.y) < R[i] + f.r + EXP_GAP + 0.05) return false;
          for (let j = 0; j < X.length; j++) if (j !== i && Math.hypot(x - X[j], y - Y[j]) < R[i] + R[j] + EXP_GAP + 0.05) return false;
          return true;
        };
        for (let i = 0; i < X.length; i++) {
          if (free(i, X[i], Y[i])) continue;
          let done = false;
          for (let rad = 1; rad <= 120 && !done; rad += 1) {
            for (let k = 0; k < 24 && !done; k++) {
              const ang = k * Math.PI / 12;
              const x = X[i] + Math.cos(ang) * rad, y = Y[i] + Math.sin(ang) * rad;
              if (free(i, x, y)) { X[i] = x; Y[i] = y; done = true; }
            }
          }
        }
      }
      nodes.forEach((nd, i) => { nd.x = X[i]; nd.y = Y[i]; });
    }
    // 라벨: 특약은 그 종형의 특약이 6개 이하일 때만, 많으면 열 옆에 "{회사} 특약 {n}, 급부 {m}"(5번). 앵커 쪽에 붙인다
    const placed = lay.anc.map(a => a.box);
    lay.glabels.forEach(gl => placed.push(gl.box));
    lay.slabels.forEach((b, sj) => { if (big.has(sj)) placed.push(b); });
    const allC = circles.concat(nodes.map(nd => [nd.x, nd.y, nd.r]));
    const labels = [];
    const tryPlace = (cands, text, weight, owner) => {
      const w = textW(text, weight), h = textLineH();
      for (const [x0, y0] of cands(w, h)) {
        const b = [x0, y0, x0 + w, y0 + h];
        if (!boxHit(b, placed, allC, lay.W, lay.H)) { placed.push(b); labels.push({ box: b, text, owner }); return true; }
      }
      return false;
    };
    nodes.forEach((nd, i) => {
      if (nd.kind === 'more' || nd.kind === 'summary') {
        tryPlace((w, h) => [[nd.x + nd.r + 2, nd.y - h / 2], [nd.x - nd.r - 2 - w, nd.y - h / 2], [nd.x - w / 2, nd.y + nd.r + 2], [nd.x - w / 2, nd.y - nd.r - 2 - h]], nd.text, 600, i);
      }
    });
    notes.forEach(nt => {
      if (!nt.many) {
        for (let i = nt.first; i < nt.last; i++) {
          const nd = nodes[i];
          if (nd.kind !== '특약') continue;
          const nm = g.N[nd.ni].l;
          tryPlace((w, h) => (nt.side < 0 ? [[nd.x - nd.r - 2 - w, nd.y - h / 2]] : [[nd.x + nd.r + 2, nd.y - h / 2]]), nm, 400, i);
        }
        return;
      }
      const rs = nodes.slice(nt.first, nt.last).filter(nd => nd.kind === '특약' || nd.kind === 'more');
      if (!rs.length) return;
      const x0 = Math.min(...rs.map(nd => nd.x - nd.r)), x1 = Math.max(...rs.map(nd => nd.x + nd.r));
      const y0 = Math.min(...rs.map(nd => nd.y - nd.r)), y1 = Math.max(...rs.map(nd => nd.y + nd.r));
      const cx = (x0 + x1) / 2;
      nt.placed = tryPlace((w, h) => [[cx - w / 2, y0 - 2 - h], [cx - w / 2, y1 + 2], nt.side < 0 ? [x0 - 2 - w, (y0 + y1) / 2 - h / 2] : [x1 + 2, (y0 + y1) / 2 - h / 2]], nt.text, 400, -1 - nt.slot);
    });
    const out = { si, nodes, edges, notes, labels, fold, ms: performance.now() - t0 };
    if (lay.fontsOk) expCache.set(ck, out);
    return out;
  }

  function layoutKeyOf(lay) { return `${lay.sc.sig}|${lay.W}|${lay.H}`; }

  // 펼친 노드, 엣지, 라벨(SVG 조각). 엣지는 앞의 그룹(.gr-l-hot)에, 노드와 라벨은 노드 위 그룹(.gr-l-exp)에 둔다
  function expEdgesHTML(g, lay, ex) {
    const end = e => (typeof e === 'number' ? ex.nodes[e] : e.anc != null ? lay.anc[e.anc] : lay.npos.get(e.std));
    const idOf = e => (typeof e === 'number' ? (ex.nodes[e].ni != null ? g.N[ex.nodes[e].ni].id : ex.nodes[e].id) : e.anc != null ? lay.anc[e.anc].id : g.N[e.std].id);
    return ex.edges.map((ed, k) => {
      const p = end(ed.s), q = end(ed.t);
      if (!p || !q) return '';
      const [x1, y1, x2, y2] = lineBetween(p, q, p.r, q.r);
      const cls = ed.ek === 'rec' ? 'gr-e-rec' : ed.ek === '매핑' ? `gr-e-map${ed.strong ? ' is-strong' : ''}` : ed.ek === '보유' ? 'gr-e-held' : 'gr-e-inc';
      const ekName = ed.ek === 'rec' ? '매핑' : ed.ek;
      const delay = Math.min(320 - 160, k * 14 * 0.5);
      return `<line class="gr-e gr-e-x ${cls}" pathLength="1" style="--d:${f1(delay)}" x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}" data-gr-ekind="${esc(ekName)}"${ed.ek === 'rec' ? ' data-gr-rec="1"' : ''} data-gr-s="${esc(idOf(ed.s))}" data-gr-t="${esc(idOf(ed.t))}" data-gr-key="${esc(ed.key)}" data-tip-title="${esc(ed.ek === 'rec' ? t('grLgRec') : (g.ekindLabels[EK[ed.ek]] || ed.ek))}"/>`;
    }).join('');
  }

  function expNodesHTML(g, lay, ex) {
    const parts = [];
    let order = 0;
    const seq = ex.nodes.map((nd, i) => [nd, i]).sort((a, b) => (a[0].kind === '급부') - (b[0].kind === '급부') || a[1] - b[1]);
    const delayOf = new Map(seq.map(([, i], k) => [i, Math.min(320 - 160, k * 14)]));
    ex.nodes.forEach((nd, i) => {
      const a = lay.anc[nd.slot];
      const org = orgOf(a.code);
      let id, kind, title, sub = '';
      if (nd.ni != null) {
        const n = g.N[nd.ni];
        id = n.id; kind = nd.kind; title = n.l;
        const tags = [org, g.kindLabels[n.k]];
        if (nd.rec) tags.push(t('grWaitMapTag'));
        if (nd.wait) tags.push(t('grWaitExtTag'));
        sub = tags.join(' / ');
      } else { id = nd.id; kind = nd.kind; title = nd.text; sub = org; }
      const cls = nd.kind === '특약' ? 'gr-x-r' : nd.kind === '급부' ? 'gr-x-b' : nd.kind === 'more' ? 'gr-x-more' : 'gr-x-sum';
      order++;
      parts.push(`<g class="gr-x ${cls}${nd.rec ? ' is-rec' : ''}${nd.wait ? ' is-wait' : ''}" style="--d:${delayOf.get(i)}" transform="translate(${f1(nd.x)} ${f1(nd.y)})" tabindex="-1" role="button" aria-label="${esc(title)}" data-gr-fk="x:${i}" data-gr-x="${i}" data-gr-id="${esc(id)}" data-gr-kind="${esc(kind)}" data-gr-r="${f1(nd.r)}" data-gr-slot="${nd.slot}"${nd.ni != null ? ` data-gr-idx="${nd.ni}"` : ''} data-aim="circle" data-tip-title="${esc(title)}" data-tip-sub="${esc(sub)}"><circle class="gr-x-c" r="${f1(nd.r)}"/></g>`);
    });
    ex.labels.forEach(lb => {
      const b = lb.box;
      parts.push(`<text class="gr-tx gr-x-lb${lb.owner < 0 ? ' is-note' : ''}" data-gr-lb="exp" data-gr-lbox="${b.map(f1).join(',')}" x="${f1(b[0])}" y="${f1(b[1] + textAsc())}">${esc(lb.text)}</text>`);
    });
    return parts.join('');
  }

  // ---------- 엣지 판정과 선택(4.1, 4.5) ----------
  function segDist(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1, l2 = dx * dx + dy * dy;
    const u = l2 ? Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / l2)) : 0;
    return Math.hypot(px - x1 - u * dx, py - y1 - u * dy);
  }

  function edgeHit(svg, x, y) {
    let best = null, bd = Infinity;
    svg.querySelectorAll('.gr-l-hot line[data-gr-key], .gr-l-xe line[data-gr-key], :scope > .gr-l-edges line').forEach(el => {
      const d = segDist(x, y, +el.getAttribute('x1'), +el.getAttribute('y1'), +el.getAttribute('x2'), +el.getAttribute('y2'));
      const lim = Math.max(4, (+el.getAttribute('stroke-width') || 1) / 2 + 3);
      if (d <= lim && d < bd) { bd = d; best = el; }
    });
    if (!best) return null;
    const key = best.dataset.grKey || (best.dataset.grBundle === '1' ? `bd:${best.dataset.grSlot}:${best.dataset.grT}` : '');
    return key ? { t: 'edge', key } : null;
  }

  function edgeElOf(svg, key) {
    if (!svg || !key) return null;
    if (key.startsWith('bd:')) {
      const [, slot, ...rest] = key.split(':');
      return svg.querySelector(`:scope > .gr-l-edges .gr-e-bundle[data-gr-slot="${slot}"][data-gr-t="${CSS.escape(rest.join(':'))}"]`);
    }
    return svg.querySelector(`line[data-gr-key="${CSS.escape(key)}"]`);
  }

  function lineStyleNet(ekName, props) {
    if (ekName === '보유') return t('grLineHeld');
    if (ekName === '담보 관계') return t('grLineRel');
    if (ekName === '포함') return t('grLineInc');
    if (ekName === '판매') return t('grLineSell');
    if (ekName === '매핑') {
      const st = props && props['검토상태'];
      return st === '승인' || st === '수정' ? t('grLineMapStrongTpl', { st: App.label(st) }) : t('grLineMap');
    }
    if (ekName === '발표') return t('grLineDashNews');
    if (ekName === '분류') return t('grLineThinDom');
    return '';
  }

  const ID_KEYS = new Set(['특약계보키', '종형계보키', '개정판ID', '모상품ID']);
  function idsHTML(pairs) {
    const rows = pairs.filter(x => x[1] != null && x[1] !== '');
    if (!rows.length) return '';
    return `<details class="ev-sec lo gr-ids"><summary>${esc(t('grIdHead'))}</summary><dl class="kv">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd class="num">${esc(String(v))}</dd>`).join('')}</dl></details>`;
  }
  const nameOfId = (g, id) => { const ni = g.byId.get(id); return ni != null ? g.N[ni].l : ''; };

  // 엣지 상세 패널(4.5): 속성 이름과 값은 App.label(), ID 속성은 이름으로, 내부 키와 노드 ID 는 접힌 ID 영역에만(5.6)
  function buildNetEdgeEv(g, key) {
    const lay = net.lay;
    const kv = rows => `<dl class="kv">${rows.filter(r => r[1] != null && r[1] !== '').map(([k, v]) => `<dt>${esc(App.label(k))}</dt><dd${/^[\d.]/.test(String(v)) ? ' class="num"' : ''}>${esc(App.label(String(v)))}</dd>`).join('')}</dl>`;
    if (key.startsWith('bd:') && lay) {
      const [, slotS, ...rest] = key.split(':');
      const slot = +slotS, gk = rest.join(':');
      const a = lay.anc[slot], grp = lay.sc.groupMap.get(gk);
      if (!a || !grp) return null;
      const list = grp.members.filter(si => lay.sc.info.get(si).slots.includes(slot));
      const gname = groupLines(lay.sc, grp)[0];
      return {
        kicker: t('grEdgeKickerTpl', { kind: t('grLgBundle') }),
        title: `${fullVarName(g, a.vi)} -> ${gname}`,
        badges: [ui.tag(t('grLgBundle'))],
        body: `<div class="ev-sec"><h3>${esc(t('grEdgePropHead'))}</h3>${kv([[t('grEdgeVarRow'), `${orgOf(a.code)}, ${fullVarName(g, a.vi)}`], [t('grEdgeGroupRow'), gname], [t('grEdgeLineRow'), t('grLineBundle')]])}</div>
          <div class="ev-sec"><h3>${esc(t('grEdgeHeldListTpl', { n: fmt(list.length) }))}</h3><ul class="evl gr-glist">${list.map(si => `<li><button type="button" class="cv-lk" data-gr-pick-std="${si}">${esc(g.N[si].l)}</button></li>`).join('')}</ul></div>
          ${idsHTML([[t('grEdgeVarRow'), a.id]])}`,
      };
    }
    if (key.startsWith('rec:')) {
      const [, b, s] = key.split(':').map(Number);
      const nb = g.N[b], ns = g.N[s];
      if (!nb || !ns) return null;
      return {
        kicker: t('grEdgeKickerTpl', { kind: t('grLgRec') }),
        title: `${nb.l} -> ${ns.l}`,
        badges: [ui.tag(t('grWaitMapTag'))],
        body: `<div class="ev-sec"><h3>${esc(t('grEdgePropHead'))}</h3>${kv([[t('grEdgeStateRow'), t('grWaitMapTag')], [t('grEdgeRecRow'), ns.l], [t('grEdgeLineRow'), t('grLineRec')]])}</div>${idsHTML([[t('grEdgeFromId'), nb.id], [t('grEdgeToId'), ns.id]])}`,
      };
    }
    if (!key.startsWith('e:')) return null;
    const e = g.E[+key.slice(2)];
    if (!e) return null;
    const ekName = g.ekinds[e.k];
    const p = e.p || {};
    const nS = g.N[e.s], nT = g.N[e.t];
    let rows = [];
    if (ekName === '보유') {
      const has = k => p[k] != null && p[k] !== '';
      rows = [['급부수', has('급부수') ? fmt(+p['급부수']) : ''], ['특약수', has('특약수') ? fmt(+p['특약수']) : ''],
        [t('grEdgeRepBenRow'), p['대표급부ID'] ? nameOfId(g, p['대표급부ID']) : ''],
        ['매핑검수대기급부수', has('매핑검수대기급부수') ? fmt(+p['매핑검수대기급부수']) : ''],
        ['추출검수대기급부수', has('추출검수대기급부수') ? fmt(+p['추출검수대기급부수']) : '']];
    } else if (ekName === '담보 관계') {
      const wide = REL_TARGET_IS_WIDE ? nT : nS, part = REL_TARGET_IS_WIDE ? nS : nT;
      rows = [['관계', p['관계'] || ''], [t('grRelWide'), wide.l], [t('grRelPart'), part.l],
        [t('grConfGemini'), p['확신_gemini'] != null ? String(p['확신_gemini']) : ''], [t('grConfClaude'), p['확신_claude'] != null ? String(p['확신_claude']) : '']];
    } else if (ekName === '매핑') {
      rows = [['검토상태', p['검토상태'] || ''], ['매핑확률', p['매핑확률'] != null ? String(p['매핑확률']) : ''], ['확정방식', p['확정방식'] || '']];
    } else if (ekName === '포함') {
      rows = nS.k === NK['특약'] ? [['급부역할', p['급부역할'] || '']] : [['담보구분', p['담보구분'] || ''], ['갱신', p['갱신'] || '']];
    } else if (ekName === '결합제약') {
      rows = [['제약유형', p['제약유형'] || ''], ['근거문구', p['근거문구'] || '']];
    } else {
      rows = Object.entries(p).filter(([k, v]) => !ID_KEYS.has(k) && !/ID$/.test(k) && v != null && v !== '').map(([k, v]) => [k, String(v)]);
    }
    rows.push([t('grEdgeLineRow'), lineStyleNet(ekName, p)]);
    const idRows = [[t('grEdgeFromId'), nS.id], [t('grEdgeToId'), nT.id]].concat(Object.entries(p).filter(([k]) => ID_KEYS.has(k) || /ID$/.test(k)).map(([k, v]) => [App.label(k), v]));
    return {
      kicker: t('grEdgeKickerTpl', { kind: g.ekindLabels[e.k] }),
      title: `${nS.l} -> ${nT.l}`,
      badges: [ui.tag(g.ekindLabels[e.k])],
      body: `<div class="ev-sec"><h3>${esc(t('grEdgePropHead'))}</h3>${kv(rows)}</div>
        <div class="ev-sec lo"><h3>${esc(t('grEdgeEndsHead'))}</h3><div style="display:flex;flex-wrap:wrap;gap:6px">${[nS, nT].map(n => (n.k === NK['표준담보'] && lay && lay.sc.info.has(n.i) ? `<button type="button" class="btn sm ghost" data-gr-pick-std="${n.i}">${esc(n.l)}</button>` : `<span class="tag">${esc(n.l)}</span>`)).join('')}</div></div>
        ${idsHTML(idRows)}`,
    };
  }

  // ---------- 조건을 바꿀 때 위치 트랜지션(4.9) ----------
  function moveDur() {
    const v = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--dur-graph-move')) || 480;
    return Math.round(v * (App.motionScale ? App.motionScale() : 1));
  }

  // 지금 화면에 보이는 위치(애니메이션 도중이면 그 순간의 값)를 읽는다
  function capturePos(svg) {
    const sr = svg.getBoundingClientRect();
    const c = el => { const r = el.getBoundingClientRect(); return { x: r.left - sr.left + r.width / 2, y: r.top - sr.top + r.height / 2, R: r.width / 2 }; };
    const pos = { n: new Map(), g: new Map(), a: new Map() };
    svg.querySelectorAll('.gr-l-nodes > .gr-n').forEach(el => pos.n.set(el.dataset.grId, Object.assign(c(el.querySelector('.gr-n-c')), { el })));
    svg.querySelectorAll('.gr-l-groups > .gr-g').forEach(el => pos.g.set(el.dataset.grGroup, Object.assign(c(el), { el })));
    svg.querySelectorAll('.gr-l-anchors > .gr-a').forEach(el => pos.a.set(el.dataset.grAkey, Object.assign(c(el.querySelector('.gr-a-c')), { el })));
    pos.layers = Array.from(svg.querySelectorAll(':scope > .gr-l-edges, :scope > .gr-l-labels'));
    pos.opacity = new Map(pos.layers.map(l => [l, getComputedStyle(l).opacity]));
    return pos;
  }

  function endMove() {
    if (net.moveT) { clearTimeout(net.moveT); net.moveT = 0; }
    (net.moveTs || []).forEach(clearTimeout);
    net.moveTs = [];
    net.moving = false;
  }

  function startMove(svg, prev, lay) {
    const dur = moveDur();
    if (!dur) return false;
    const ms = App.motionScale ? App.motionScale() : 1;
    const ghost = svg.querySelector('.gr-l-ghost');
    const moves = [];
    let changed = false;
    const prep = (el, from, to, enter) => {
      el.style.transition = 'none';
      el.style.transform = from;
      if (enter) el.style.opacity = '0';
      moves.push([el, to, enter]);
    };
    svg.querySelectorAll('.gr-n').forEach(el => {
      const p = lay.npos.get(+el.dataset.grIdx), q = prev.n.get(el.dataset.grId);
      const to = `translate(${f1(p.x)}px, ${f1(p.y)}px)`;
      if (q) { if (Math.hypot(q.x - p.x, q.y - p.y) > 0.01) changed = true; prep(el, `translate(${f1(q.x)}px, ${f1(q.y)}px)`, to, false); }
      else { changed = true; prep(el, `${to} scale(0.6)`, to, true); }
    });
    svg.querySelectorAll('.gr-g').forEach(el => {
      const gg = lay.gpos.get(el.dataset.grGroup), q = prev.g.get(el.dataset.grGroup);
      el.style.transformOrigin = `${f1(gg.x)}px ${f1(gg.y)}px`;
      if (q) { if (Math.hypot(q.x - gg.x, q.y - gg.y) > 0.01 || Math.abs(q.R - gg.R) > 0.01) changed = true; prep(el, `translate(${f1(q.x - gg.x)}px, ${f1(q.y - gg.y)}px) scale(${(q.R / gg.R).toFixed(4)})`, 'translate(0px, 0px) scale(1)', false); }
      else { changed = true; prep(el, 'scale(0.6)', 'scale(1)', true); }
    });
    svg.querySelectorAll('.gr-a').forEach((el, slot) => {
      const a = lay.anc[slot], q = prev.a.get(el.dataset.grAkey);
      const to = `translate(${f1(a.x)}px, ${f1(a.y)}px)`;
      if (q) { if (Math.hypot(q.x - a.x, q.y - a.y) > 0.01) changed = true; prep(el, `translate(${f1(q.x)}px, ${f1(q.y)}px)`, to, false); }
      else { changed = true; prep(el, `${to} scale(0.6)`, to, true); }
    });
    // 사라지는 노드, 그룹 원, 앵커는 처음 40% 동안 제자리에서 흐려지며 빠진다
    const gone = [];
    prev.n.forEach((q, id) => { if (!svg.querySelector(`.gr-n[data-gr-id="${CSS.escape(id)}"]`)) gone.push([q, `translate(${f1(q.x)}px, ${f1(q.y)}px)`]); });
    prev.a.forEach((q, k) => { if (!svg.querySelector(`.gr-a[data-gr-akey="${CSS.escape(k)}"]`)) gone.push([q, `translate(${f1(q.x)}px, ${f1(q.y)}px)`]); });
    prev.g.forEach((q, k) => {
      if (svg.querySelector(`.gr-g[data-gr-group="${CSS.escape(k)}"]`)) return;
      const cx = +q.el.getAttribute('cx'), cy = +q.el.getAttribute('cy'), r = +q.el.getAttribute('r') || 1;
      q.el.style.transformOrigin = `${cx}px ${cy}px`;
      gone.push([q, `translate(${f1(q.x - cx)}px, ${f1(q.y - cy)}px) scale(${(q.R / r).toFixed(4)})`]);
    });
    if (gone.length) changed = true;
    if (!changed) { moves.forEach(([el]) => { el.style.transition = ''; el.style.transform = ''; el.style.opacity = ''; el.style.transformOrigin = ''; }); return false; }
    gone.forEach(([q, tf]) => {
      const el = q.el;
      el.classList.remove('is-keep', 'is-sel', 'is-big', 'is-on');
      el.style.transition = 'none';
      el.style.transform = tf;
      el.style.opacity = '1';
      ghost.appendChild(el);
    });
    // 번들 엣지와 라벨: 옛 것은 처음 25% 동안 빠지고, 새 것은 노드가 도착한 뒤 그어지고(320ms) 나타난다(120ms).
    // 새 층은 옛 층을 잔상 층에 넣기 전에 잡는다(잔상 층이 문서 차례로 앞이다)
    const newEdges = Array.from(svg.querySelectorAll(':scope > .gr-l-edges .gr-e-bundle'));
    const newLabels = svg.querySelector(':scope > .gr-l-labels');
    prev.layers.forEach(l => { l.style.transition = 'none'; l.style.opacity = prev.opacity.get(l); ghost.appendChild(l); });
    newEdges.forEach(el => { el.setAttribute('pathLength', '1'); el.style.strokeDasharray = '1'; el.style.strokeDashoffset = '1'; });
    // 잔상은 포커스 대상과 측정 대상이 아니다
    ghost.querySelectorAll('[data-gr-fk]').forEach(x => { x.removeAttribute('data-gr-fk'); x.removeAttribute('tabindex'); });
    if (newLabels) newLabels.style.opacity = '0';
    net.moving = true;
    svg.getBoundingClientRect();
    void getComputedStyle(svg.querySelector('.gr-n') || svg).transform;
    const ease = 'var(--ease-graph-move)';
    moves.forEach(([el, to, enter]) => {
      if (enter) {
        el.style.transition = `opacity ${dur * 0.5}ms var(--ease-in) ${dur * 0.5}ms, transform ${dur * 0.5}ms var(--ease-in) ${dur * 0.5}ms`;
        el.style.opacity = '1';
      } else el.style.transition = `transform ${dur}ms ${ease}`;
      el.style.transform = to;
    });
    gone.forEach(([q]) => { q.el.style.transition = `opacity ${Math.round(dur * 0.4)}ms var(--ease-out)`; q.el.style.opacity = '0'; });
    prev.layers.forEach(l => { l.style.transition = `opacity ${Math.round(dur * 0.25)}ms var(--ease-out)`; l.style.opacity = '0'; });
    net.moveT = setTimeout(() => {
      net.moveT = 0;
      if (!svg.isConnected) { net.moving = false; return; }
      moves.forEach(([el]) => { el.style.transition = ''; el.style.transform = ''; el.style.opacity = ''; el.style.transformOrigin = ''; });
      ghost.textContent = '';
      const drawMs = Math.round(320 * ms), lbMs = Math.round(120 * ms);
      newEdges.forEach(el => { el.style.transition = `stroke-dashoffset ${drawMs}ms var(--ease-in)`; el.style.strokeDashoffset = '0'; });
      if (newLabels) { newLabels.style.transition = `opacity ${lbMs}ms var(--ease-in)`; newLabels.style.opacity = '1'; }
      net.moving = false;
      applyNetState();
      net.moveTs.push(setTimeout(() => {
        newEdges.forEach(el => { el.style.transition = ''; el.style.strokeDasharray = ''; el.style.strokeDashoffset = ''; el.removeAttribute('pathLength'); });
        if (newLabels) { newLabels.style.transition = ''; newLabels.style.opacity = ''; }
      }, Math.max(drawMs, lbMs) + 40));
    }, dur + 20);
    return true;
  }

  // ---------- 키보드: roving tabindex(4.7) ----------
  function fkOf(el) { return el && el.dataset ? el.dataset.grFk || '' : ''; }
  function focusables(svg) { return Array.from(svg.querySelectorAll('[data-gr-fk]')); }
  function hitOfEl(el) {
    if (!el) return null;
    const fk = fkOf(el);
    if (el.classList.contains('gr-n')) return { t: 'std', si: +el.dataset.grIdx };
    if (el.classList.contains('gr-a')) return { t: 'anchor', slot: +el.dataset.grSlot };
    if (el.dataset.grGlabel) return { t: 'group', key: el.dataset.grGlabel };
    if (fk.startsWith('x:')) return { t: 'x', i: +el.dataset.grX };
    return null;
  }
  function setRoving(svg, el) {
    if (!svg || !el) return;
    svg.querySelectorAll('[data-gr-fk][tabindex="0"]').forEach(x => { if (x !== el) x.setAttribute('tabindex', '-1'); });
    el.setAttribute('tabindex', '0');
    net.focusKey = fkOf(el);
  }
  function syncRoving(svg) {
    if (!svg) return;
    const cur = net.focusKey && svg.querySelector(`[data-gr-fk="${CSS.escape(net.focusKey)}"]`);
    setRoving(svg, cur || svg.querySelector('.gr-a.is-base') || svg.querySelector('[data-gr-fk]'));
  }
  function elCenter(svg, el) {
    const sr = svg.getBoundingClientRect(), r = el.getBoundingClientRect();
    return [r.left - sr.left + r.width / 2, r.top - sr.top + r.height / 2];
  }
  function netArrow(svg, el, key) {
    const list = focusables(svg).filter(x => x.getClientRects().length && getComputedStyle(x).opacity !== '0');
    let target = null;
    if (key === 'Home') target = svg.querySelector('.gr-a.is-base');
    else if (key === 'End') { const gl = svg.querySelectorAll('[data-gr-glabel]'); target = gl[gl.length - 1] || null; }
    else {
      const [x0, y0] = elCenter(svg, el);
      const dir = { ArrowRight: 0, ArrowDown: 90, ArrowLeft: 180, ArrowUp: 270 }[key];
      let bd = Infinity;
      list.forEach(x => {
        if (x === el) return;
        const [x1, y1] = elCenter(svg, x);
        const d = Math.hypot(x1 - x0, y1 - y0);
        if (d < 0.5) return;
        let ang = Math.atan2(y1 - y0, x1 - x0) * 180 / Math.PI;
        let diff = Math.abs(((ang - dir) % 360 + 540) % 360 - 180);
        if (diff <= 45 && d < bd) { bd = d; target = x; }
      });
    }
    if (!target) return;
    setRoving(svg, target);
    try { target.focus({ preventScroll: true }); } catch (e) { /* */ }
  }
  function netActivate(h) {
    const svg = lastCenterEl && lastCenterEl.querySelector('#gr-net-svg');
    if (!h || !svg) return;
    netClickHit(h, svg);
  }

  // ---------- 상세 패널: 담보와 그룹 ----------
  function buildStdEv(g, si) {
    const c = App.ctx();
    const lay = net.lay && net.lay.sc.info.has(si) ? net.lay : null;
    const sc = lay ? lay.sc : sceneOf(g, c);
    const it = sc.info.get(si);
    if (!it) return null;
    const jdAll = lay ? lay.jd : judgeOf(g, c, sc);
    const fakeLay = { sc, jd: jdAll };
    const n = g.N[si];
    const jd = jdAll.per.get(si);
    const grpName = groupLines(sc, sc.groupMap.get(it.key))[0];
    const marks = markLines(g, c, fakeLay, si);
    const verdRows = jd.cov ? jd.cov.pv.map(x => {
      const code = (txt.vinfo(x.peer) || {})['기관코드'];
      return `<li><b>${esc(orgOf(code))}</b> ${App.cover.chip(x.v)}${x.v && x.v.why ? `<p class="note">${esc(x.v.why)}</p>` : ''}</li>`;
    }).join('') : '';
    const heldRows = it.per.map(x => {
      const p = x.e.p;
      const items = [t('grHeldLineTpl', { r: fmt(+(p['특약수'] || 0)), b: fmt(+(p['급부수'] || 0)) })];
      if (p['대표급부ID'] && g.byId.has(p['대표급부ID'])) items.push(t('grRepBenTpl', { nm: g.N[g.byId.get(p['대표급부ID'])].l }));
      if (p['매핑검수대기급부수']) items.push(t('grWaitMapTpl', { n: fmt(p['매핑검수대기급부수']) }));
      if (p['추출검수대기급부수']) items.push(t('grWaitExtTpl', { n: fmt(p['추출검수대기급부수']) }));
      return `<dt>${esc(orgOf(x.code))}</dt><dd>${esc(items.join(', '))}</dd>`;
    }).join('');
    // 특약과 급부 목록(그래프 열 차례, 급부역할, 검수 상태)과 담보 관계로 연결된 담보(4.3의 8번)
    const chainRows = it.per.map(x => {
      const ch = chainOf(g, x.vi, si);
      if (!ch.length) return '';
      const items = ch.map(rc => {
        const bens = rc.bens.map(b => {
          const ie = edgeIdx(g, rc.ri, b.b, '포함');
          const role = ie != null ? (g.E[ie].p || {})['급부역할'] : '';
          const m = (g.benStds.get(b.b) || []).find(y => y.std === si);
          const st = b.rec ? t('grWaitMapTag') : m ? App.label((g.E[m.e].p || {})['검토상태'] || '') : '';
          const ext = (g.N[b.b].p || {})['추출검수대기항목'] ? t('grWaitExtTag') : '';
          return `<li>${esc(g.N[b.b].l)}<span class="note"> ${esc([role ? App.label(role) : '', st, ext].filter(Boolean).join(', '))}</span></li>`;
        }).join('');
        return `<li><b>${esc(g.N[rc.ri].l)}</b><ul class="evl gr-bl">${bens}</ul></li>`;
      }).join('');
      return `<h4 class="gr-ch-h">${esc(orgOf(x.code))}</h4><ul class="evl gr-ch">${items}</ul>`;
    }).join('');
    const relRows = netRelEdges(g, sc, si).map(({ e, other }) => {
      const otherIsWide = REL_TARGET_IS_WIDE ? e.t === other : e.s === other;
      return `<li><button type="button" class="cv-lk" data-gr-pick-std="${other}">${esc(g.N[other].l)}</button> ${ui.tag(otherIsWide ? t('grRelWide') : t('grRelPart'))}</li>`;
    }).join('');
    const body = `${marks.length ? `<div class="ev-sec"><h3>${esc(t('grMarkHead'))}</h3><ul class="evl">${marks.map(m => `<li>${esc(m)}</li>`).join('')}</ul></div>` : ''}
      ${verdRows ? `<div class="ev-sec"><h3>${esc(t('grVerdictHead'))}</h3><ul class="evl gr-verd">${verdRows}</ul></div>` : ''}
      <div class="ev-sec"><h3>${esc(t('grHeldHead'))}</h3><dl class="kv">${heldRows}</dl>${crossTabButtonsHTML(g, n)}</div>
      ${relRows ? `<div class="ev-sec"><h3>${esc(t('grRelStdHead'))}</h3><ul class="evl gr-glist">${relRows}</ul></div>` : ''}
      ${chainRows ? `<div class="ev-sec"><h3>${esc(t('grExpListHead'))}</h3>${chainRows}</div>` : ''}
      <details class="ev-sec lo gr-ids"><summary>${esc(t('grIdHead'))}</summary><p class="note num">${esc(n.id)}</p></details>`;
    return {
      kicker: t('grNodeKickerTpl', { kind: g.kindLabels[n.k] }),
      title: n.l,
      badges: [ui.tag(it.dom), ui.tag(grpName)],
      body,
    };
  }

  function buildGroupEv(g, key) {
    const c = App.ctx();
    const sc = net.lay ? net.lay.sc : sceneOf(g, c);
    const grp = sc.groupMap.get(key);
    if (!grp) return null;
    const jdAll = net.lay ? net.lay.jd : judgeOf(g, c, sc);
    const lines = groupLines(sc, grp);
    const doms = domOrder(g);
    const list = grp.members.slice().sort((a, b) => {
      const da = doms.indexOf(domOf(g, a)), db = doms.indexOf(domOf(g, b));
      return (da < 0 ? 99 : da) - (db < 0 ? 99 : db) || a - b;
    });
    const rows = list.map(si => {
      const jd = jdAll.per.get(si);
      const mk = jd.marks.map(m => ui.tag(t(MARK_KEY[m]))).join('');
      const chips = jd.cov ? jd.cov.pv.filter(x => x.v).map(x => App.cover.chip(x.v)).join('') : '';
      return `<li><button type="button" class="cv-lk" data-gr-pick-std="${si}">${esc(g.N[si].l)}</button> ${mk}${chips}</li>`;
    }).join('');
    return {
      kicker: t('grGroupKicker'),
      title: lines[0],
      badges: [ui.tag(lines[1])],
      body: `<div class="ev-sec"><h3>${esc(t('grDomCntHead'))}</h3><p>${esc(domCountText(g, grp.members))}</p></div>
        <div class="ev-sec"><h3>${esc(t('grGroupListHeadTpl', { n: fmt(grp.members.length) }))}</h3><ul class="evl gr-glist">${rows}</ul></div>`,
    };
  }

  // ---------- 왼쪽 영역: 판정 필터와 범례 ----------
  function swatchSVG(inner) {
    return `<svg class="gr-sw" width="22" height="18" viewBox="0 0 22 18" aria-hidden="true">${inner}</svg>`;
  }
  function legendItemsHTML(g, clickable, ring) {
    const doms = domOrder(g).slice(0, 5);
    const btn = (f, sw, label) => (clickable
      ? `<button type="button" class="gr-lg-it${state.filter === f ? ' is-on' : ''}" data-gr-filter="${esc(f)}" aria-pressed="${state.filter === f}">${sw}<span>${esc(label)}</span></button>`
      : `<span class="gr-lg-it">${sw}<span>${esc(label)}</span></span>`);
    const row = (sw, label) => `<span class="gr-lg-it">${sw}<span>${esc(label)}</span></span>`;
    const cls = [
      ['only', t('grClsOnly')], ['shared', t('grClsShared')], ['peer', t('grClsPeer')],
    ].map(([k, nm]) => btn('cls:' + k, swatchSVG(`<circle class="gr-g gr-g-${k}" cx="11" cy="9" r="7"/>`), nm)).join('');
    const dom = doms.map((d, i) => btn('dom:' + d, swatchSVG(`<circle class="gr-n-c" cx="11" cy="9" r="6" style="fill:var(--gr-dom-${i})"/>`), d)).join('');
    const mk = [
      ['sole', `<g transform="translate(8 11)"><circle class="gr-n-c" r="5" style="fill:var(--gr-dom-4)"/>${markGlyph('sole', 5)}</g>`],
      ['peer-rel', `<g transform="translate(8 11)"><circle class="gr-n-c" r="5" style="fill:var(--gr-dom-4)"/>${markGlyph('peer-rel', 5)}</g>`],
      ['ours-wide', `<g transform="translate(8 7)"><circle class="gr-n-c" r="5" style="fill:var(--gr-dom-4)"/>${markGlyph('ours-wide', 5)}</g>`],
      ['ours-part', `<g transform="translate(8 7)"><circle class="gr-n-c" r="5" style="fill:var(--gr-dom-4)"/>${markGlyph('ours-part', 5)}</g>`],
      ['wait', '<g class="gr-n is-wait" transform="translate(11 9)"><circle class="gr-n-c" r="6" style="fill:var(--gr-dom-4)"/></g>'],
    ].map(([m, sw]) => row(swatchSVG(sw), t(MARK_KEY[m]))).join('')
      + (ring ? row(swatchSVG(`<g transform="translate(11 9)"><circle class="gr-n-c" r="5" style="fill:var(--gr-dom-4)"/>${ringSVG(7, 0.7)}</g>`), t('grLgRing')) : '');
    const edges = [
      [`<line class="gr-e gr-e-bundle" x1="2" y1="9" x2="20" y2="9" stroke-width="3"/>`, t('grLgBundle')],
      [`<line class="gr-e gr-e-held" x1="2" y1="9" x2="20" y2="9"/>`, t('grLgHeldOne')],
      [`<line class="gr-e gr-e-rel gr-e-rel-inc" x1="2" y1="9" x2="20" y2="9"/>`, t('grLgRelInc')],
      [`<line class="gr-e gr-e-rel gr-e-rel-uni" x1="2" y1="9" x2="20" y2="9"/>`, t('grLgRelUni')],
      [`<line class="gr-e gr-e-inc" x1="2" y1="9" x2="20" y2="9"/>`, t('grLgIncMap')],
      [`<line class="gr-e gr-e-rec" x1="2" y1="9" x2="20" y2="9"/>`, t('grLgRec')],
    ].map(([sw, nm]) => row(swatchSVG(sw), nm)).join('');
    return `<div class="gr-lg-sec"><span class="gr-lg-h">${esc(t('grLgCls'))}</span>${cls}</div>
      <div class="gr-lg-sec is-2col"><span class="gr-lg-h">${esc(t('grPropDomain'))}</span>${dom}</div>
      <div class="gr-lg-sec"><span class="gr-lg-h">${esc(t('grLgMark'))}</span>${mk}</div>
      <div class="gr-lg-sec is-2col"><span class="gr-lg-h">${esc(t('grLgEdgeHead'))}</span>${edges}</div>`;
  }

  // 그룹 기준(타사 3개사 이하는 보유 조합, 4개사 이상은 보유 타사 수 구간)이 바뀐 조건을 기억한다(8.1의 6번)
  const basis = { last: null, noteSig: null };
  function netLeftHTML(g, c) {
    const sc = sceneOf(g, c);
    const jd = judgeOf(g, c, sc);
    const now = sc.nPeer > 3 ? 'bin' : 'combo';
    const sig = sceneTypes(g, c).join(',');
    if (basis.last && basis.last !== now) basis.noteSig = sig;
    basis.last = now;
    const note = basis.noteSig === sig ? `<p class="gr-lg-note" role="status">${esc(t('grBasisNote'))}</p>` : '';
    const fl = FILTERS.map(f => `<button type="button" class="gr-flt${state.filter === 'f:' + f.id ? ' is-on' : ''}" data-gr-filter="f:${f.id}" aria-pressed="${state.filter === 'f:' + f.id}"><span>${esc(App.label(f.cause))}</span><span class="num">${fmt(jd.counts[f.id])}</span></button>`).join('');
    return `<div><span class="gr-sec-k">${esc(t('grFilterHead'))}</span><div class="gr-flts">${fl}</div></div>
      <div class="gr-legend"><span class="gr-sec-k">${esc(t('grLegendHead'))}</span>${note}${legendItemsHTML(g, true, sc.nPeer > 3)}</div>`;
  }

  function netCopyRows(g, c) {
    const sc = sceneOf(g, c);
    const jd = judgeOf(g, c, sc);
    const rows = [];
    sc.groups.forEach(grp => {
      const nm = groupLines(sc, grp)[0];
      grp.members.forEach(si => {
        const p = jd.per.get(si);
        const verd = p.cov ? p.cov.pv.filter(x => x.v).map(x => `${orgOf((txt.vinfo(x.peer) || {})['기관코드'])} ${App.cover.chipText(x.v)}`).join(', ') : '';
        rows.push([nm, g.N[si].l, domOf(g, si), p.marks.map(m => t(MARK_KEY[m])).join(', '), verd]);
      });
    });
    return rows;
  }

  // ---------- 오른쪽 읽기 영역(#z-right): 노드 상세, 엣지 속성, 다른 화면 이동 ----------
  function propTableHTML(props, extraRows = []) {
    const rows = extraRows.slice();
    for (const [k, v] of Object.entries(props || {})) {
      if (v == null || v === '') continue;
      const valStr = typeof v === 'boolean' ? (v ? '예' : '아니오') : String(v);
      rows.push([k, valStr]);
    }
    if (!rows.length) return '<p class="note">추가 속성이 없습니다.</p>';
    return `<dl class="kv">${rows.map(([k, v]) => `<dt>${esc(App.label(k))}</dt><dd${/^\d/.test(v) ? ' class="num"' : ''}>${esc(App.label(v))}</dd>`).join('')}</dl>`;
  }

  function crossTabButtonsHTML(g, n) {
    let stdId = '';
    if (n.k === NK['표준담보']) stdId = n.id;
    else if (n.k === NK['급부']) {
      const links = g.benStds.get(n.i) || [];
      if (links.length) stdId = g.N[links[0].std].id;
    }

    // 가입 관문에서 보기: 전체 표 창(tree)을 띄우지 않고 해당 종형을 고른 상태로 바로 연다(1-13)
    let gateVid = '';
    if (n.k === NK['종형']) gateVid = n.id;
    else if (n.k === NK['특약']) {
      const vList = g.riderVars.get(n.i) || [];
      if (vList.length) gateVid = g.N[vList[0]].id;
    } else if (n.k === NK['급부']) {
      const rList = g.benRiders.get(n.i) || [];
      if (rList.length) {
        const vList = g.riderVars.get(rList[0]) || [];
        if (vList.length) gateVid = g.N[vList[0]].id;
      }
    } else if (n.k === NK['회사'] && n.o) {
      const mVars = sceneTypes(g, App.ctx());
      const hitV = mVars.find(vi => g.N[vi] && g.N[vi].o === n.o);
      if (hitV != null) gateVid = g.N[hitV].id;
    }

    const coverFocus = stdId ? ` data-focus="s:${esc(stdId)}"` : '';
    const gateFocus = gateVid ? ` data-focus="g:${esc(gateVid)}"` : '';
    return `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">
      ${ui.btn('담보 비교에서 보기', { sm: true, ghost: true, chev: true, attrs: `data-go="cover"${coverFocus}` })}
      ${ui.btn(t('grGoGateBtn'), { sm: true, ghost: true, chev: true, attrs: `data-go="gate"${gateFocus}` })}
    </div>`;
  }

  function buildNodeEv(g, ni) {
    const n = g.N[ni];
    if (!n) return null;
    const badges = [ui.tag(g.kindLabels[n.k])];
    if (n.o && n.k !== NK['회사']) badges.push(ui.tag(orgLabel(n.o)));
    // 해시와 내부 키, ...ID 는 접힌 ID 영역에만 두고, ID 를 가리키는 값은 이름으로 바꿔 보인다(5.6)
    const props = {};
    const idRows = [[t('grPropId'), n.id]];
    const extra = [];
    Object.entries(n.p || {}).forEach(([k, v]) => {
      if (v == null || v === '') return;
      if (ID_KEYS.has(k) || /ID$/.test(k) || k === '기관코드') { idRows.push([App.label(k), Array.isArray(v) ? v.join(', ') : v]); return; }
      props[k] = Array.isArray(v) ? v.map(x => App.label(String(x))).join(', ') : v;
    });
    if (n.p['추천표준담보ID']) extra.push([t('grRecStdRow'), nameOfId(g, n.p['추천표준담보ID'])]);
    if (n.k === NK['특약'] && n.p['갱신여부']) { props['갱신여부'] = renewText(ni) || n.p['갱신여부']; }
    const secs = [];
    const lk = (idx, label) => `<li><button type="button" class="cv-lk" data-gr-sel-idx="${idx}">${esc(label)}</button></li>`;
    if (n.k === NK['종형']) {
      const vs = g.summary && g.summary['종형'] && g.summary['종형'][n.id];
      if (vs) {
        if (vs['비교역할'] && props['비교역할'] == null) extra.push(['비교역할', App.label(vs['비교역할'])]);
        if (vs['판매종료일'] && props['판매종료일'] == null) extra.push(['판매종료일', vs['판매종료일']]);
        if (vs['특약수'] != null) extra.push([t('grRiderCntRow'), `${fmt(vs['특약수'])}개`]);
        if (vs['급부수'] != null) extra.push([t('grBenCntRow'), `${fmt(vs['급부수'])}개`]);
        if (vs['미연결급부'] != null) extra.push([t('grPropUnmappedBen'), `${fmt(vs['미연결급부'])}개`]);
        const bd = vs['보장분야별'] || {};
        const dc = domOrder(g).filter(d => bd['CAT:' + d] != null).map(d => `${d} ${fmt(bd['CAT:' + d])}`).join(', ');
        if (dc) extra.push([t('grDomCntRow'), dc]);
        if (App.isGateOnlyRole(vs['비교역할']) || vs['비교역할'] === '직전개정시연' || vs['판매종료일']) {
          secs.push(`<div class="ev-sec"><p class="note">${esc(vs['판매종료일'] ? t('grVarEndNoteTpl', { dt: vs['판매종료일'] }) : t('grVarGateOnlyNote'))}</p></div>`);
        }
      }
      const rv = revOf(g, ni);
      if (rv) extra.push([t('grRevPrevRow'), `${fullVarName(g, rv.prev)} (${t('grRevLineTpl', { a: fmt(+(rv.p['신설'] || 0)), b: fmt(+(rv.p['변경'] || 0)), c: fmt(+(rv.p['종료'] || 0)), del: App.label('종료') })})`]);
      const cons = (g.varRiders.get(ni) || []).reduce((a, ri) => a.concat(g.adj[ri].filter(x => x.isOut && x.ek === EK['결합제약'])), []);
      if (cons.length) extra.push([g.ekindLabels[EK['결합제약']], `${fmt(cons.length)}건`]);
      if (rv && state.preset === 'variant' && state.vf.rev && state.varIdx === ni) {
        const po = prevOnlyRiders(g, ni);
        secs.push(`<div class="ev-sec"><h3>${esc(t('grRevOnlyHeadTpl', { n: fmt(po.length) }))}</h3>${po.length ? `<ul class="evl gr-glist">${po.map(ri => `<li>${esc(g.N[ri].l)}</li>`).join('')}</ul>` : ''}</div>`);
      }
    } else if (n.k === NK['특약']) {
      if (state.preset === 'variant' && state.vf.rev) { const rv = revOf(g, state.varIdx); if (rv && !lineageHas(g, ni, rv.prev)) extra.push([t('grRevToggle'), t('grRevNew')]); }
      const bs = g.riderBens.get(ni) || [];
      if (bs.length) secs.push(`<div class="ev-sec"><h3>${esc(g.kindLabels[NK['급부']])}</h3><ul class="evl gr-glist">${bs.map(b => lk(b, g.N[b].l)).join('')}</ul></div>`);
    } else if (n.k === NK['급부']) {
      const ss = (g.benStds.get(ni) || []).map(x => x.std);
      if (ss.length) secs.push(`<div class="ev-sec"><h3>${esc(g.kindLabels[NK['표준담보']])}</h3><ul class="evl gr-glist">${ss.map(s => `<li><button type="button" class="cv-lk" data-gr-go-std="${s}">${esc(g.N[s].l)}</button></li>`).join('')}</ul></div>`);
    } else if (n.k === NK['표준담보'] && state.preset !== 'cover') {
      secs.push(`<div class="ev-sec">${ui.btn(t('grGoCoverStdBtn'), { sm: true, main: true, chev: true, attrs: `data-gr-go-std="${ni}"` })}</div>`);
    } else if (n.k === NK['회사']) {
      const news = g.adj[ni].filter(x => x.ek === EK['발표'] && g.N[x.j].k === NK['시장 동향']).map(x => x.j)
        .sort((a, b) => String(g.N[b].p['발표일자'] || '').localeCompare(String(g.N[a].p['발표일자'] || '')) || a - b);
      secs.push(`<div class="ev-sec"><h3>${esc(t('grOrgNewsHeadTpl', { n: fmt(news.length) }))}</h3>${news.length ? `<ul class="evl gr-glist">${news.map(x => lk(x, `${g.N[x].p['발표일자'] || ''} ${g.N[x].l}`)).join('')}</ul>` : ''}</div>`);
    } else if (n.k === NK['시장 동향']) {
      const q = App.S && App.S['시장소식'] ? App.S['시장소식']['인용안내'] : '';
      if (q) secs.push(`<div class="ev-sec"><p class="note">${esc(q)}</p></div>`);
    }
    const body = `<div class="ev-sec"><h3>${esc(t('grNodePropHead'))}</h3>${propTableHTML(props, extra)}${crossTabButtonsHTML(g, n)}</div>${secs.join('')}${idsHTML(idRows)}`;
    return {
      kicker: t('grNodeKickerTpl', { kind: g.kindLabels[n.k] }),
      title: n.k === NK['회사'] ? orgLabel(n.o) : n.l,
      badges,
      body,
    };
  }




  function pick(key) {
    const g = ensureGraph();
    if (key.startsWith('n:')) {
      const id = key.slice(2);
      const ni = g.byId.get(id);
      if (ni == null) return null;
      if (state.preset === 'cover' && g.N[ni].k === NK['표준담보'] && sceneOf(g, App.ctx()).info.has(ni)) {
        state.selStd = ni;
        state.selGroup = null;
        state.selNode = null;
        state.selEdge = null;
        return buildStdEv(g, ni);
      }
      state.selNode = ni;
      state.focusNode = ni;
      state.selEdge = null;
      const ev = buildNodeEv(g, ni);
      // 펼친 특약과 급부에서 그 종형의 종형 구성으로 넘어간다(4.11)
      if (ev && state.preset === 'cover' && (g.N[ni].k === NK['특약'] || g.N[ni].k === NK['급부'])) {
        const vi = net.ex && net.ex.nodes.find(nd => nd.ni === ni) ? net.lay.anc[net.ex.nodes.find(nd => nd.ni === ni).slot].vi : varOfNode(g, ni);
        if (vi != null) ev.body = `<div class="ev-sec">${ui.btn(t('grOpenVarBtn'), { sm: true, main: true, chev: true, attrs: `data-gr-open-var="${vi}"` })}</div>` + ev.body;
      }
      return ev;
    }
    if (key.startsWith('grp:')) {
      state.selGroup = key.slice(4);
      state.selStd = null;
      state.selNode = null;
      state.selEdge = null;
      return buildGroupEv(g, key.slice(4));
    }
    if (key.startsWith('edge:')) {
      const ek = key.slice(5);
      state.selEdge = ek;
      return buildNetEdgeEv(g, ek);
    }
    return null;
  }

  function defaultEv() {
    const g = ensureGraph();
    const isNet = state.preset === 'cover';
    const sc = isNet ? sceneOf(g, App.ctx()) : null;
    const al = alt.lay;
    const visTotal = isNet ? sc.stds.length + sc.types.length : al ? al.nodes.length + (al.kind === 'vt' ? 1 : 0) : 0;
    const edgeTotal = isNet ? (net.lay ? net.lay.bundles.length : 0) : al ? al.edges.length : 0;
    return {
      kicker: t('evKickerDefault'),
      title: t('grEvTitle'),
      badges: [ui.tag(`노드 ${fmt(visTotal)}`), ui.tag(`엣지 ${fmt(edgeTotal)}`)],
      body: `<div class="ev-sec"><p>${esc(isNet ? t('grNetEvBody') : state.preset === 'variant' ? t('grVtEvBody') : t('grMkEvBody'))}</p>
        <dl class="kv" style="margin-top:8px">
          <dt>전체 노드</dt><dd class="num">${fmt(g.N.length)}개</dd>
          <dt>전체 엣지</dt><dd class="num">${fmt(g.E.length)}개</dd>
          <dt>자료 시각</dt><dd class="num">${esc(String(g.snapshotAt || '').replace('T', ' ').slice(0, 16))}</dd>
        </dl>
      </div>`,
    };
  }

  function renderZones({ left, center, ctx: c }) {
    ensureGraph();
    lastLeftEl = left;
    lastCenterEl = center;
    const sig = scopeSig(c);
    if (!trail.length || sig !== lastScopeSig) {
      const keepSel = state.preset === 'cover' && lastScopeSig ? state.selStd : null;
      const hadSel = App.state.sel.graph != null;
      lastScopeSig = sig;
      const keepFilter = state.filter;
      initPresetState(state.preset || 'cover', c, false);
      state.filter = keepFilter;
      // 선택한 담보가 새 조건에서도 화면에 있으면 선택을 유지하고(새 위치에서 다시 펼침), 없으면 푼다(4.9의 4번)
      const g = ensureGraph();
      if (keepSel != null && sceneOf(g, c).info.has(keepSel)) {
        state.selStd = keepSel;
        recordTrail(g.N[keepSel].l, true);
        requestAnimationFrame(() => { if (state.selStd === keepSel) App.select('n:' + g.N[keepSel].id, { animate: false, push: false, focus: false }); });
      } else if (hadSel && state.preset === 'cover') {
        requestAnimationFrame(() => { if (App.state.sel.graph != null && state.selStd == null) App.unselect({ push: false, restoreFocus: false }); });
      }
    }
    renderLeftZone(left);
    rerenderGraph(false);
  }


  // 종형 구성 보기에 쓸 종형: 종형은 그 자신, 특약과 급부는 그 노드가 속한 첫 종형
  function varOfNode(g, ni) {
    const n = g.N[ni];
    if (n.k === NK['종형']) return ni;
    let ri = n.k === NK['특약'] ? ni : null;
    if (n.k === NK['급부']) ri = (g.benRiders.get(ni) || [])[0];
    const vl = ri != null ? (g.riderVars.get(ri) || []) : [];
    return vl.length ? vl[0] : null;
  }

  function jumpToAnyNode(ni, c) {
    const g = ensureGraph();
    const n = g.N[ni];
    if (!n) return;
    if (n.k === NK['표준담보']) {
      if (!sceneOf(g, c).info.has(ni)) { App.toast(t('grNotInScene')); return; }
      netSelectStd(ni, { rerender: true });
      return;
    }
    if (n.k === NK['보장 대분류']) {
      pushUndo();
      if (state.preset !== 'cover') initPresetState('cover', c, true);
      state.filter = 'dom:' + n.l;
      if (lastLeftEl) renderLeftZone(lastLeftEl);
      rerenderGraph(false);
      return;
    }
    if (n.k === NK['종형'] && state.preset === 'cover' && sceneOf(g, c).types.includes(ni)) {
      pushUndo();
      state.selStd = null;
      state.selGroup = null;
      state.selNode = ni;
      recordTrail(n.l, true);
      rerenderGraph(false);
      App.select('n:' + n.id, { animate: true, focus: false });
      // 검색한 종형이 지금 앵커에 있으면 그 앵커로 포커스를 옮긴다(4.6)
      const a = net.lay && net.lay.anc.find(x => x.vi === ni);
      const svg = lastCenterEl && lastCenterEl.querySelector('#gr-net-svg');
      const el = a && svg && svg.querySelector(`[data-gr-fk="${CSS.escape('a:' + a.key)}"]`);
      if (el) { net.selFk = 'a:' + a.key; setRoving(svg, el); try { el.focus({ preventScroll: true }); } catch (e) { /* */ } }
      return;
    }
    // 종형은 그 종형의 종형 구성, 특약과 급부는 그 종형의 종형 구성에서 그 노드, 회사와 시장 동향은 시장 동향 보기(4.6)
    if (n.k === NK['종형']) { openAlt('variant', ni, null); return; }
    if (n.k === NK['특약'] || n.k === NK['급부']) {
      const vi = varOfNode(g, ni);
      if (vi == null) return;
      openAlt('variant', vi, ni);
      return;
    }
    if (n.k === NK['시장 동향'] || n.k === NK['회사']) openAlt('news', null, ni);
  }


  function focus(target, _body, c) {
    if (!target) return;
    const g = ensureGraph();
    const curC = c || App.ctx();
    const s = String(target);
    let ni = null;
    if (s.startsWith('std:')) {
      ni = g.byId.get(s.slice(4));
    } else if (s.startsWith('var:')) {
      const vid = s.slice(4);
      ni = g.byId.get(vid);
      if (ni == null) {
        const vInfo = txt.vinfo(vid);
        if (vInfo && vInfo['기관코드']) ni = g.byId.get('ORG:' + vInfo['기관코드']);
      }
    } else if (s.startsWith('org:')) {
      ni = g.byId.get('ORG:' + s.slice(4));
    } else if (s.startsWith('news:')) {
      const q = s.slice(5);
      ni = g.byId.get(q) ?? (g.N.find(n => n.k === NK['시장 동향'] && (n.o === q || n.l.includes(q))) || {}).i;
    } else {
      ni = g.byId.get(s);
    }
    if (ni != null) jumpToAnyNode(ni, curC);
  }

  function updateSearchSugg(qVal) {
    const g = ensureGraph();
    const sugg = lastLeftEl && lastLeftEl.querySelector('#gr-sugg');
    if (!sugg) return;
    state.query = qVal;
    const q = qVal.trim().toLowerCase();
    if (!q) { sugg.hidden = true; sugg.innerHTML = ''; return; }
    const pri = { [NK['표준담보']]: 0, [NK['종형']]: 1, [NK['특약']]: 2, [NK['회사']]: 3, [NK['보장 대분류']]: 4, [NK['시장 동향']]: 5, [NK['급부']]: 6 };
    const hits = g.N.filter(n => n.l.toLowerCase().includes(q) || n.id.toLowerCase().includes(q))
      .sort((a, b) => (pri[a.k] ?? 9) - (pri[b.k] ?? 9) || a.l.length - b.l.length)
      .slice(0, 12);
    if (!hits.length) {
      sugg.innerHTML = '<div class="gr-sugg-empty">맞는 이름의 노드가 없습니다.</div>';
      sugg.hidden = false;
      return;
    }
    sugg.innerHTML = hits.map(n => `<button type="button" class="gr-sugg-it" data-gr-sugg="${n.i}">
      <span class="gr-sugg-k">${esc(g.kindLabels[n.k])}</span>
      <span class="gr-sugg-n">${esc(n.l)}</span>
      ${n.o ? `<span class="gr-sugg-o">${esc(orgLabel(n.o))}</span>` : ''}
    </button>`).join('');
    sugg.hidden = false;
  }

  // ---------- 엣지 가리킴 칩과 조준 표식 반응(1-2) ----------
  function showEdgeHoverChip(eg) {
    if (!lastCenterEl || !eg) return;
    const chip = lastCenterEl.querySelector('#gr-edge-chip');
    if (!chip) return;
    if (hoveredEdgeEl && hoveredEdgeEl !== eg) hoveredEdgeEl.classList.remove('is-hot');
    hoveredEdgeEl = eg;
    eg.classList.add('is-hot');
    chip.textContent = eg.dataset.chip || '';
    chip.style.setProperty('--ec-x', (eg.dataset.cx || 0) + 'px');
    chip.style.setProperty('--ec-y', (eg.dataset.cy || 0) + 'px');
    chip.classList.remove('is-press');
    chip.hidden = false;
    App.aim.set(chip);
  }

  function clearEdgeHoverChip() {
    if (hoveredEdgeEl) {
      hoveredEdgeEl.classList.remove('is-hot');
      hoveredEdgeEl = null;
    }
    if (!lastCenterEl) return;
    const chip = lastCenterEl.querySelector('#gr-edge-chip');
    if (chip && !chip.hidden) {
      chip.classList.remove('is-press');
      chip.hidden = true;
    }
  }

  function reselectFromState() {
    const g = ensureGraph();
    const o = { animate: false, push: false, focus: false };
    if (state.selEdge) App.select('edge:' + state.selEdge, o);
    else if (state.selStd != null) App.select('n:' + g.N[state.selStd].id, o);
    else if (state.selGroup) App.select('grp:' + state.selGroup, o);
    else if (state.selNode != null) App.select('n:' + g.N[state.selNode].id, o);
    else App.unselect({ push: false, restoreFocus: false });
  }

  // 담보별 연결의 호버: 포인터에서 가장 가까운 노드 중심까지 max(r + 4, 12)px 이하면 그 노드(3.7)
  document.addEventListener('pointermove', e => {
    if (App.state.tab !== 'graph' || e.pointerType === 'touch' || !net.lay) return;
    const svg = e.target.closest && e.target.closest('#gr-net-svg');
    if (!svg) { if (net.hover) netHover(null); return; }
    netHover(netHit(svg, e.clientX, e.clientY));
  }, { passive: true });

  // 포커스는 호버와 같은 포커스 표시로 보인다(4.7)
  document.addEventListener('focusin', e => {
    if (App.state.tab !== 'graph' || !net.lay) return;
    const el = e.target.closest && e.target.closest('#gr-net-svg [data-gr-fk]');
    if (!el) return;
    setRoving(el.closest('#gr-net-svg'), el);
    // 키보드 포커스일 때만 호버와 같은 강조를 보인다(마우스 클릭으로 생긴 포커스는 포인터 위치가 정한다)
    let vis = true;
    try { vis = el.matches(':focus-visible'); } catch (err) { /* */ }
    if (vis) netHover(hitOfEl(el));
  });
  document.addEventListener('focusout', e => {
    if (App.state.tab !== 'graph' || !net.lay) return;
    const to = e.relatedTarget;
    if (e.target.closest && e.target.closest('#gr-net-svg') && !(to && to.closest && to.closest('#gr-net-svg'))) netHover(null);
  });

  // ---------- 종형 구성 보기(6절)와 시장 동향 보기(7절) ----------
  // 두 보기는 담보별 연결과 같은 그래프 영역(#gr-net)에 SVG 하나로 그린다. 수는 summary, 엣지 속성, 집합의 크기에서만 읽는다
  const VT_MARGIN = 14, VT_RHO = { r: 0.36, b: 0.63, s: 0.90 }, VT_R = { r: 5, b: 4.5, s: 6 };
  const VT_GAP = 14, VT_STD_GAP = 16, VT_STD_PAD = 12, VT_BOX = [168, 46], VT_LBL_MAX = 16, VT_LBL_H = 16;
  const VT_SECTOR_MIN = 10, VT_SECTOR_PAD = 1;
  const MK_CELL = [220, 150], MK_RO = 14, MK_RN = 7, MK_RING = 44;
  const alt = { lay: null };
  const vtCache = new Map();

  // 기준 타원: 둘레를 720등분한 누적 길이 표로 둘레 비율 t(0 이 12시, 시계 방향)를 각도로 바꾼다(6절 2, 3번)
  function ringOf(W, H) {
    const cx = W / 2, cy = H / 2, rx = W / 2 - VT_MARGIN, ry = H / 2 - VT_MARGIN, m = 720;
    const th = [], cum = [0];
    for (let k = 0; k <= m; k++) th.push(-Math.PI / 2 + 2 * Math.PI * k / m);
    for (let k = 0; k < m; k++) cum.push(cum[k] + Math.hypot(rx * (Math.cos(th[k + 1]) - Math.cos(th[k])), ry * (Math.sin(th[k + 1]) - Math.sin(th[k]))));
    const P = cum[m];
    const theta = tt => {
      const s = (((tt % 1) + 1) % 1) * P;
      let lo = 0, hi = m;
      while (hi - lo > 1) { const md = (lo + hi) >> 1; if (cum[md] <= s) lo = md; else hi = md; }
      const f = (s - cum[lo]) / ((cum[lo + 1] - cum[lo]) || 1);
      return th[lo] + f * (th[lo + 1] - th[lo]);
    };
    const normal = a => { const nx = Math.cos(a) / rx, ny = Math.sin(a) / ry, n = Math.hypot(nx, ny) || 1; return [nx / n, ny / n]; };
    const pt = (tt, rho, off) => {
      const a = theta(tt);
      let x = cx + rho * rx * Math.cos(a), y = cy + rho * ry * Math.sin(a);
      if (off) { const [nx, ny] = normal(a); x += off * nx; y += off * ny; }
      return [x, y];
    };
    return { cx, cy, rx, ry, P, theta, normal, pt };
  }
  function circMean(ts) {
    let sx = 0, sy = 0;
    ts.forEach(v => { sx += Math.cos(2 * Math.PI * v); sy += Math.sin(2 * Math.PI * v); });
    return ((Math.atan2(sy, sx) / (2 * Math.PI)) % 1 + 1) % 1;
  }
  // 차례를 지키는 1차원 최소제곱 배치(PAVA). 다 들어가지 않으면 간격을 줄여 돌려준다
  function pavaSpread(targets, lo, hi, gap) {
    const n = targets.length;
    if (!n) return [[], gap];
    if (hi < lo) lo = hi = (lo + hi) / 2;
    if (n > 1 && hi - lo < gap * (n - 1)) gap = (hi - lo) / (n - 1);
    const blocks = [];
    targets.forEach((v, i) => {
      blocks.push([v - i * gap, 1]);
      while (blocks.length > 1 && blocks[blocks.length - 2][0] / blocks[blocks.length - 2][1] > blocks[blocks.length - 1][0] / blocks[blocks.length - 1][1]) {
        const [s2, c2] = blocks.pop();
        blocks[blocks.length - 1][0] += s2;
        blocks[blocks.length - 1][1] += c2;
      }
    });
    const out = [];
    blocks.forEach(([s, c]) => { for (let k = 0; k < c; k++) out.push(s / c); });
    const umax = hi - (n - 1) * gap;
    return [out.map((v, i) => Math.min(Math.max(v, lo), umax) + i * gap), gap];
  }
  // 간격이 모자랄 때 안팎으로 엇갈리는 폭(이웃 두 노드의 실제 거리가 gap 이 되게)
  function zigzag(gEff, gap) {
    if (gEff >= gap - 1e-9) return 0;
    const g2 = gap * 1.06;
    return Math.sqrt(Math.max(0, g2 * g2 - gEff * gEff)) / 2;
  }
  // 원 하나에서 목표 t 의 차례를 지키며 간격을 둔다. 가장 큰 빈 구간에서 끊어 직선으로 편 뒤 PAVA
  function circSpread(items, P, gap) {
    const out = new Map();
    if (!items.length) return out;
    const its = items.map(([k, v]) => [k, ((v % 1) + 1) % 1]).sort((a, b) => a[1] - b[1] || String(a[0]).localeCompare(String(b[0])));
    const n = its.length;
    const gaps = its.map((x, i) => (((its[(i + 1) % n][1] - x[1]) % 1 + 1) % 1) || (n === 1 ? 1 : 0));
    let cut = 0;
    gaps.forEach((v, i) => { if (v > gaps[cut]) cut = i; });
    const order = its.map((_, i) => its[(cut + 1 + i) % n]);
    const base = order[0][1];
    const lin = order.map(x => (((x[1] - base) % 1 + 1) % 1) * P);
    const slack = Math.max(0, (gaps[cut] * P - gap) / 2);
    let [pos, gEff] = pavaSpread(lin, lin[0] - slack, lin[n - 1] + slack, gap);
    if (n * gap > P) { gEff = P / n; pos = lin.map((_, i) => lin[0] + i * gEff); }
    const off = zigzag(gEff, gap);
    order.forEach(([k], i) => out.set(k, [((base + pos[i] / P) % 1 + 1) % 1, off ? (i % 2 ? off : -off) : 0]));
    return out;
  }
  // 보장 대분류 부채꼴: 크기는 (사전 담보 수와 10 가운데 큰 값) + 1 에 비례, 담보의 목표 t 는 사전 차례로 고정(6절 4번)
  function sectorTable(g) {
    if (g.vtSectors) return g.vtSectors;
    const doms = domOrder(g);
    const lists = new Map(doms.map(d => [d, []]));
    g.N.forEach(n => { if (n.k === NK['표준담보']) { const d = domOf(g, n.i); if (lists.has(d)) lists.get(d).push(n.i); } });
    const w = doms.map(d => Math.max(lists.get(d).length, VT_SECTOR_MIN) + VT_SECTOR_PAD);
    const tot = w.reduce((a, b) => a + b, 0) || 1;
    const sectors = [], target = new Map();
    let a = 0;
    doms.forEach((d, i) => {
      const b = a + w[i] / tot;
      sectors.push({ dom: d, a, b });
      const ss = lists.get(d);
      ss.forEach((si, k) => target.set(si, a + (b - a) * (k + 1) / (ss.length + 1)));
      a = b;
    });
    g.vtSectors = { sectors, target };
    return g.vtSectors;
  }
  const eOf = (g, s, tIdx, ek) => { const x = g.adj[s].find(y => y.isOut && y.j === tIdx && y.ek === ek); return x ? x.e : -1; };
  function revOf(g, vi) {
    if (vi == null) return null;
    const x = g.adj[vi].find(y => !y.isOut && y.ek === EK['개정']);
    return x ? { prev: x.j, e: x.e, p: g.E[x.e].p || {} } : null;
  }
  // 특약계보에 직전 종형이 없으면 "직전 개정에 없음"(6절 10번)
  function lineageHas(g, ri, vi) {
    const tab = g.summary && g.summary['특약계보'] && g.summary['특약계보'][g.N[ri].o];
    const key = g.N[ri].p['특약계보키'];
    const list = tab && key ? tab[key] : null;
    return Array.isArray(list) && list.includes(vi);
  }
  function prevOnlyRiders(g, vi) {
    const rv = revOf(g, vi);
    if (!rv) return [];
    return (g.varRiders.get(rv.prev) || []).filter(ri => !lineageHas(g, ri, vi));
  }
  const RENEW_KEY = { 갱신: 'grRenewY', 비갱신: 'grRenewN' };
  const renewText = ri => { const v = ensureGraph().N[ri].p['갱신여부']; return RENEW_KEY[v] ? t(RENEW_KEY[v]) : ''; };
  const riderBody = l => String(l || '').replace(/^무배당 /, '');
  const clipName = s => (s.length > VT_LBL_MAX ? s.slice(0, VT_LBL_MAX) + '…' : s);
  const boxOv = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
  const cbox = (x, y, r) => [x - r, y - r, x + r, y + r];
  function segBox(p, q, b) {
    let t0 = 0, t1 = 1;
    const dx = q[0] - p[0], dy = q[1] - p[1];
    const cl = (pp, qq) => { if (pp === 0) return qq >= 0; const r = qq / pp; if (pp < 0) { if (r > t1) return false; if (r > t0) t0 = r; } else { if (r < t0) return false; if (r < t1) t1 = r; } return true; };
    return cl(-dx, p[0] - b[0]) && cl(dx, b[2] - p[0]) && cl(-dy, p[1] - b[1]) && cl(dy, b[3] - p[1]);
  }
  function segX(a, b, c, d) {
    const o = (p, q, r) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);
    const d1 = o(a, b, c), d2 = o(a, b, d), d3 = o(c, d, a), d4 = o(c, d, b);
    return ((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0));
  }
  function polyCross(p, q) {
    let n = 0;
    for (let i = 0; i < p.length - 1; i++) for (let j = 0; j < q.length - 1; j++) if (segX(p[i], p[i + 1], q[j], q[j + 1])) n++;
    return n;
  }
  const segCircleDist = (a, b, c) => {
    const dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy || 1;
    const u = Math.max(0, Math.min(1, ((c[0] - a[0]) * dx + (c[1] - a[1]) * dy) / L2));
    return Math.hypot(a[0] + u * dx - c[0], a[1] + u * dy - c[1]);
  };
  const quadPts = (p0, c, p1, k) => Array.from({ length: k + 1 }, (_, i) => { const u = i / k; return [(1 - u) * (1 - u) * p0[0] + 2 * (1 - u) * u * c[0] + u * u * p1[0], (1 - u) * (1 - u) * p0[1] + 2 * (1 - u) * u * c[1] + u * u * p1[1]]; });
  const ptsBox = pts => { let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity; pts.forEach(([x, y]) => { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }); return [x0, y0, x1, y1]; };
  // 직선을 상자 가장자리에서 자른다(가운데 상자에서 특약으로 가는 포함 엣지)
  function clipToBox(cx, cy, hw, hh, x, y) {
    const dx = x - cx, dy = y - cy;
    const s = Math.min(dx ? hw / Math.abs(dx) : Infinity, dy ? hh / Math.abs(dy) : Infinity);
    return [cx + dx * Math.min(1, s), cy + dy * Math.min(1, s)];
  }
  // 라벨 18곳: 바깥 방향, 오른쪽, 왼쪽, 위, 아래, 대각 넷, 같은 아홉 방향으로 8px 더(6절 11번)
  function labelCands(x, y, r, w, h, nx, ny) {
    const out = [];
    [0, 8].forEach(ex => {
      const d = r + 3 + ex;
      let ob;
      if (Math.abs(nx) >= 0.35) { const lx = nx > 0 ? x + d : x - d - w; ob = [lx, y - h / 2]; }
      else { const ly = ny > 0 ? y + d : y - d - h; ob = [x - w / 2, ly]; }
      const k = 0.7 * d;
      [ob, [x + d, y - h / 2], [x - d - w, y - h / 2], [x - w / 2, y - d - h], [x - w / 2, y + d],
        [x + k, y - k - h], [x - k - w, y - k - h], [x + k, y + k], [x - k - w, y + k]].forEach(([lx, ly]) => out.push([lx, ly, lx + w, ly + h]));
    });
    return out;
  }
  // 그리디 라벨 배치: 다른 라벨, 노드, 상자와 겹치지 않는 첫 자리. 엣지가 지나지 않는 자리를 먼저 쓴다
  function placeLabels(items, obstacles, W, H, edges) {
    const placed = [], out = new Map();
    const eb = edges.map(e => [e, ptsBox(e.pts)]);
    items.forEach(it => {
      const ok = labelCands(it.x, it.y, it.r, it.w, VT_LBL_H, it.nx, it.ny).filter(b => b[0] >= 1 && b[1] >= 1 && b[2] <= W - 1 && b[3] <= H - 1
        && !placed.some(q => boxOv(b, q)) && !obstacles.some(([k, q]) => k !== it.key && boxOv(b, q)));
      let best = ok.find(b => !eb.some(([e, bb]) => e.s !== it.ni && e.t !== it.ni && boxOv(b, bb) && e.pts.some((p, i) => i > 0 && segBox(e.pts[i - 1], p, b))));
      if (!best) best = ok[0];
      if (best) { placed.push(best); out.set(it.key, best); }
    });
    return out;
  }
  function vtRiders(g, vi) {
    const vf = state.vf;
    let rs = (g.varRiders.get(vi) || []).slice();
    if (vf.renew) rs = rs.filter(ri => g.N[ri].p['갱신여부'] === vf.renew);
    if (vf.dom) rs = rs.filter(ri => (g.N[ri].p['보장대분류'] || []).includes(vf.dom));
    return rs;
  }
  function benRole(g, ri, bi) {
    const e = eOf(g, ri, bi, EK['포함']);
    return e >= 0 ? (g.E[e].p || {})['급부역할'] || '' : '';
  }

  function vtLayout(g, vi, W, H) {
    const vf = state.vf;
    const key = ['vt', vi, W, H, vf.renew || '', vf.main ? 1 : 0, vf.dom || '', vf.rev ? 1 : 0].join('|');
    if (vtCache.has(key)) return vtCache.get(key);
    const t0 = performance.now();
    const ring = ringOf(W, H);
    const { sectors, target } = sectorTable(g);
    let riders = vtRiders(g, vi);
    const rIdx = new Map(riders.map((r, i) => [r, i]));
    const benRider = new Map();
    let bens = [];
    riders.forEach(r => (g.riderBens.get(r) || []).forEach(b => { if (!benRider.has(b)) { benRider.set(b, r); bens.push(b); } }));
    const stdsOf = b => (g.benStds.get(b) || []).map(x => x.std).filter(s => target.has(s));
    let stds = Array.from(new Set(bens.flatMap(stdsOf))).sort((a, b) => target.get(a) - target.get(b) || a - b);
    const capR = Math.floor(ring.P * VT_RHO.r / VT_GAP), capB = Math.floor(ring.P * VT_RHO.b / VT_GAP);
    let kLim = null;
    const more = new Map();
    // 표시 한도: 두 타원 수용량을 넘으면 표준담보마다 급부 k 개까지(특약 차례, 주급부 먼저면 주급부 먼저), 나머지는 "+N"(6절 6번)
    if (riders.length > capR || bens.length > capB) {
      const ordered = vf.main ? bens.slice().sort((a, b) => ((benRole(g, benRider.get(a), a) === '주급부' ? 0 : 1) - (benRole(g, benRider.get(b), b) === '주급부' ? 0 : 1)) || (rIdx.get(benRider.get(a)) - rIdx.get(benRider.get(b)))) : bens;
      const perStd = new Map();
      ordered.forEach(b => stdsOf(b).forEach(s => { if (!perStd.has(s)) perStd.set(s, []); perStd.get(s).push(b); }));
      kLim = 1;
      perStd.forEach(v => { kLim = Math.max(kLim, v.length); });
      let shown, rs;
      for (;;) {
        shown = new Set();
        perStd.forEach(v => v.slice(0, kLim).forEach(b => shown.add(b)));
        rs = new Set(Array.from(shown).map(b => benRider.get(b)));
        if ((shown.size <= capB && rs.size <= capR) || kLim <= 1) break;
        kLim--;
      }
      perStd.forEach((v, s) => { const n = v.filter(b => !shown.has(b)).length; if (n) more.set(s, n); });
      bens = bens.filter(b => shown.has(b));
      riders = riders.filter(r => rs.has(r));
    }
    // 표준담보: 부채꼴마다 PAVA(간격 16px, 양끝 12px 안쪽)
    const PS = ring.P * VT_RHO.s;
    const st = new Map();
    sectors.forEach(({ dom, a, b }) => {
      const mem = stds.filter(s => domOf(g, s) === dom);
      const [px, gp] = pavaSpread(mem.map(s => target.get(s) * PS), a * PS + VT_STD_PAD, b * PS - VT_STD_PAD, VT_STD_GAP);
      const off = zigzag(gp, VT_STD_GAP);
      mem.forEach((s, i) => st.set(s, [px[i] / PS, off ? (i % 2 ? off : -off) : 0]));
    });
    stds = stds.filter(s => st.has(s));
    // 급부는 매핑된 표준담보 방향의 원형 평균, 특약은 매핑된 급부 방향의 원형 평균(6절 5번)
    const btg = new Map(), rtg = new Map();
    bens.forEach(b => { const ss = stdsOf(b).filter(s => st.has(s)); if (ss.length) btg.set(b, circMean(ss.map(s => st.get(s)[0]))); });
    riders.forEach(r => { const ts = (g.riderBens.get(r) || []).filter(b => btg.has(b) && benRider.get(b) === r).map(b => btg.get(b)); if (ts.length) rtg.set(r, circMean(ts)); });
    const lonely = riders.filter(r => !rtg.has(r));
    let outT = null;
    if (lonely.length) {
      const ts = Array.from(rtg.values()).sort((a, b) => a - b);
      if (!ts.length) ts.push(0);
      const n = ts.length;
      let gi = 0, gl = -1;
      ts.forEach((v, i) => { const d = (((ts[(i + 1) % n] - v) % 1 + 1) % 1) || 1; if (d > gl) { gl = d; gi = i; } });
      lonely.forEach((r, k) => rtg.set(r, (ts[gi] + gl * (k + 1) / (lonely.length + 1)) % 1));
      outT = (ts[gi] + gl / 2) % 1;
    }
    bens.forEach(b => { if (!btg.has(b)) btg.set(b, rtg.get(benRider.get(b))); });
    const spR = circSpread(riders.map((r, k) => [r, rtg.get(r) + 1e-6 * k]), ring.P * VT_RHO.r, VT_GAP);
    const spB = circSpread(bens.map((b, k) => [b, btg.get(b) + 1e-6 * k]), ring.P * VT_RHO.b, VT_GAP);
    const nodes = [], nmap = new Map(), edges = [];
    const add = (ni, kind, tt, off, rho, r) => {
      const [x, y] = ring.pt(tt, rho, off);
      const [nx, ny] = ring.normal(ring.theta(tt));
      const nd = { ni, kind, x, y, r, t: tt, nx, ny };
      nodes.push(nd); nmap.set(ni, nd);
      return nd;
    };
    riders.forEach(r => { const [tt, off] = spR.get(r); add(r, 'r', tt, off, VT_RHO.r, VT_R.r); });
    bens.forEach(b => { const [tt, off] = spB.get(b); add(b, 'b', tt, off, VT_RHO.b, VT_R.b); });
    stds.forEach(s => { const [tt, off] = st.get(s); add(s, 's', tt, off, VT_RHO.s, VT_R.s); });
    const cx = ring.cx, cy = ring.cy, hw = VT_BOX[0] / 2, hh = VT_BOX[1] / 2;
    const box = [cx - hw, cy - hh, cx + hw, cy + hh];
    // 엣지: 종형->특약, 특약->급부(포함), 급부->표준담보(매핑), 담보 관계, 특약 부가 조건
    riders.forEach(r => { const n = nmap.get(r); edges.push({ k: '포함', s: vi, t: r, e: eOf(g, vi, r, EK['포함']), pts: [clipToBox(cx, cy, hw, hh, n.x, n.y), [n.x, n.y]] }); });
    bens.forEach(b => { const r = benRider.get(b), p = nmap.get(r), q = nmap.get(b); edges.push({ k: '포함', s: r, t: b, e: eOf(g, r, b, EK['포함']), pts: [[p.x, p.y], [q.x, q.y]] }); });
    bens.forEach(b => (g.benStds.get(b) || []).forEach(x => { const q = nmap.get(x.std); if (!q) return; const p = nmap.get(b); edges.push({ k: '매핑', s: b, t: x.std, e: x.e, pts: [[p.x, p.y], [q.x, q.y]] }); }));
    const rSet = new Set(riders);
    riders.forEach(r => g.adj[r].forEach(x => {
      if (!x.isOut || x.ek !== EK['결합제약'] || !rSet.has(x.j)) return;
      const p = nmap.get(r), q = nmap.get(x.j);
      const L = Math.hypot(q.x - p.x, q.y - p.y) || 1, ux = (q.x - p.x) / L, uy = (q.y - p.y) / L;
      edges.push({ k: '결합제약', s: r, t: x.j, e: x.e, pts: [[p.x + ux * (VT_R.r + 1), p.y + uy * (VT_R.r + 1)], [q.x - ux * (VT_R.r + 3), q.y - uy * (VT_R.r + 3)]] });
    }));
    // 담보 관계: 2차 베지어 후보 여섯 가운데 (지나는 노드 x 100 + 교차 + 길이 x 0.01)이 가장 낮은 것(6절 7번)
    const rels = [];
    stds.forEach(s => (g.stdRels.get(s) || []).forEach(x => {
      if (x.dir !== 'out' || !nmap.has(x.other)) return;
      const p = nmap.get(s), q = nmap.get(x.other);
      const p0 = [p.x, p.y], p1 = [q.x, q.y];
      const L = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) || 1;
      const mx = (p0[0] + p1[0]) / 2, my = (p0[1] + p1[1]) / 2, nxp = -(p1[1] - p0[1]) / L, nyp = (p1[0] - p0[0]) / L;
      const cands = [[null, [p0, p1]]];
      [0.2, 0.45].forEach(k => [1, -1].forEach(sg => { const c = [mx + sg * k * L * nxp, my + sg * k * L * nyp]; cands.push([c, quadPts(p0, c, p1, 12)]); }));
      const A = ring.pt(circMean([p.t, q.t]), Math.max(0.2, VT_RHO.s - 0.12));
      const ci = [2 * A[0] - mx, 2 * A[1] - my];
      cands.push([ci, quadPts(p0, ci, p1, 12)]);
      const ok = cands.filter(c => c[1].every(([x0, y0]) => x0 >= -1 && x0 <= W + 1 && y0 >= -1 && y0 <= H + 1));
      rels.push({ s, t2: x.other, e: x.e, rel: (g.E[x.e].p || {})['관계'] || '', cands: ok.length ? ok : cands.slice(0, 1), len: L });
    }));
    const fixed = edges.map(e => [e, ptsBox(e.pts)]);
    const nodeBoxes = nodes.map(n => [n, cbox(n.x, n.y, n.r)]);
    rels.forEach(rl => {
      rl.stat = rl.cands.map(([, pts]) => {
        const bb = ptsBox(pts);
        let thr = 0, cr = 0, ln = 0;
        nodeBoxes.forEach(([n, b]) => { if (n.ni !== rl.s && n.ni !== rl.t2 && boxOv(bb, b) && pts.some((p, i) => i > 0 && segCircleDist(pts[i - 1], p, [n.x, n.y]) < n.r - 1)) thr++; });
        if (boxOv(bb, box) && pts.some((p, i) => i > 0 && segBox(pts[i - 1], p, box))) thr++;
        fixed.forEach(([e, b]) => { if (e.s !== rl.s && e.t !== rl.s && e.s !== rl.t2 && e.t !== rl.t2 && boxOv(bb, b)) cr += polyCross(pts, e.pts); });
        for (let i = 1; i < pts.length; i++) ln += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
        return thr * 100 + cr + ln * 0.01;
      });
      rl.bbs = rl.cands.map(([, pts]) => ptsBox(pts));
      rl.pick = 0;
    });
    const relOrder = rels.map((_, i) => i).sort((a, b) => rels[a].len - rels[b].len || a - b);
    const done = new Set();
    for (let pass = 0; pass < 2; pass++) {
      relOrder.forEach(i => {
        const rl = rels[i];
        let best = 0, bv = Infinity;
        rl.cands.forEach((cd, k) => {
          let v = rl.stat[k];
          done.forEach(j => {
            if (j === i) return;
            const o = rels[j];
            if (o.s === rl.s || o.s === rl.t2 || o.t2 === rl.s || o.t2 === rl.t2) return;
            if (boxOv(rl.bbs[k], o.bbs[o.pick])) v += polyCross(cd[1], o.cands[o.pick][1]);
          });
          if (v < bv - 1e-9) { bv = v; best = k; }
        });
        rl.pick = best;
        done.add(i);
      });
    }
    rels.forEach(rl => { const [c, pts] = rl.cands[rl.pick]; edges.push({ k: '담보 관계', s: rl.s, t: rl.t2, e: rl.e, rel: rl.rel, ctrl: c, pts }); });
    // 부채꼴 경계(급부 타원 바깥에서 기준 타원까지)
    const secLines = sectors.map(sc => [ring.pt(sc.a, VT_RHO.b + 0.08), ring.pt(sc.a, 1.0)]);
    // "+N" 배지는 표준담보의 안쪽(가운데 쪽)에 붙인다
    const badges = [];
    more.forEach((n, s) => {
      const nd = nmap.get(s);
      if (!nd) return;
      const tx = '+' + fmt(n), w = textW(tx, 600) + 8, h = 16;
      // 이웃 배지와 겹치면 가운데 쪽으로 한 칸씩 더 옮긴다
      let bb = null;
      for (let k = 0; k < 6 && !bb; k++) {
        const d = nd.r + 2 + k * 17;
        const bx = nd.x - nd.nx * (d + w / 2), by = nd.y - nd.ny * (d + h / 2);
        const b = [bx - w / 2, by - h / 2, bx + w / 2, by + h / 2];
        if (!badges.some(o => boxOv(b, o.box)) && !nodes.some(o => o.ni !== s && boxOv(b, cbox(o.x, o.y, o.r + 1)))) bb = b;
      }
      if (!bb) { const bx = nd.x - nd.nx * (nd.r + 2 + w / 2), by = nd.y - nd.ny * (nd.r + 2 + h / 2); bb = [bx - w / 2, by - h / 2, bx + w / 2, by + h / 2]; }
      badges.push({ s, n, tx, box: bb });
    });
    const obstacles = nodes.map(n => ['n' + n.ni, cbox(n.x, n.y, n.r + 1)]).concat([['box', box]], badges.map(b => ['b' + b.s, b.box]));
    const rv = vf.rev ? revOf(g, vi) : null;
    let revLine = null;
    if (rv) {
      const tx = t('grRevLineTpl', { a: fmt(+(rv.p['신설'] || 0)), b: fmt(+(rv.p['변경'] || 0)), c: fmt(+(rv.p['종료'] || 0)), del: App.label('종료') });
      const w = textW(tx);
      revLine = { tx, box: [cx - w / 2, box[3] + 6, cx + w / 2, box[3] + 6 + VT_LBL_H] };
      obstacles.push(['rev', revLine.box]);
    }
    // 부채꼴 라벨: 부채꼴 가운데 방향의 기준 타원 위에서 시작해 안쪽으로 옮기며 빈 자리
    const vs = g.summary && g.summary['종형'] && g.summary['종형'][g.N[vi].id];
    const secLabels = [];
    sectors.forEach(sc => {
      const cnt = vs && vs['보장분야별'] ? vs['보장분야별']['CAT:' + sc.dom] : null;
      const tx = cnt != null ? `${sc.dom} ${fmt(cnt)}` : sc.dom;
      const w = textW(tx, 600), h = VT_LBL_H;
      let best = null;
      for (const rr of [1.0, 0.97]) {
        for (let k = 0; k < 19 && !best; k++) {
          const f = k === 0 ? 0 : (k % 2 ? 1 : -1) * Math.ceil(k / 2) / 20;
          const [px, py] = ring.pt((sc.a + sc.b) / 2 + f * (sc.b - sc.a), rr);
          const cand = [Math.min(Math.max(px - w / 2, 2), W - 2 - w), Math.min(Math.max(py - h / 2, 2), H - 2 - h)];
          const b = [cand[0], cand[1], cand[0] + w, cand[1] + h];
          if (!obstacles.some(([, q]) => boxOv(b, q)) && !secLabels.some(q => boxOv(b, q.box))) best = b;
        }
        if (best) break;
      }
      if (best) { secLabels.push({ dom: sc.dom, tx, box: best }); obstacles.push(['sec:' + sc.dom, best]); }
    });
    // "표준담보 매핑 대상 외" 구간 제목: 매핑된 급부가 없는 특약이 놓인 구간
    let outLabel = null;
    if (lonely.length && outT != null) {
      const tx = t('grOutOfMap'), w = textW(tx, 600), h = VT_LBL_H;
      for (const rr of [VT_RHO.r - 0.09, VT_RHO.r + 0.09, VT_RHO.r - 0.14, VT_RHO.r + 0.14]) {
        const [px, py] = ring.pt(outT, rr);
        const b = [px - w / 2, py - h / 2, px + w / 2, py + h / 2];
        if (b[0] >= 1 && b[2] <= W - 1 && !obstacles.some(([, q]) => boxOv(b, q))) { outLabel = { tx, box: b }; obstacles.push(['out', b]); break; }
      }
    }
    // 표준담보와 특약 라벨
    const items = [];
    const labelText = new Map();
    stds.forEach(s => { const nd = nmap.get(s); const tx = g.N[s].l; labelText.set(s, { body: tx, suffix: '' }); items.push({ key: 'n' + s, ni: s, x: nd.x, y: nd.y, r: nd.r, nx: nd.nx, ny: nd.ny, w: textW(tx) }); });
    riders.forEach(r => {
      const nd = nmap.get(r);
      const body = clipName(riderBody(g.N[r].l)), rn = renewText(r);
      labelText.set(r, { body, suffix: rn ? `(${rn})` : '' });
      items.push({ key: 'n' + r, ni: r, x: nd.x, y: nd.y, r: nd.r, nx: nd.nx, ny: nd.ny, w: textW(rn ? `${body} (${rn})` : body) });
    });
    const allLines = edges.concat(secLines.map(p => ({ s: -1, t: -1, pts: p })));
    const lab = placeLabels(items, obstacles, W, H, allLines);
    const labels = new Map();
    lab.forEach((b, k) => { const ni = +k.slice(1); labels.set(ni, Object.assign({ box: b }, labelText.get(ni))); });
    const lay = {
      kind: 'vt', key, W, H, vi, ring, box, nodes, nmap, edges, secLines, secLabels, outLabel, labels, badges, revLine,
      riders, bens, stds, benRider, kLim, limited: kLim != null, ms: performance.now() - t0,
    };
    if (vtCache.size > 40) vtCache.clear();
    vtCache.set(key, lay);
    return lay;
  }

  const KIND_NM = { r: '특약', b: '급부', s: '표준담보' };
  function vtSVG(g, c, lay) {
    const W = lay.W, H = lay.H, vi = lay.vi, vn = g.N[vi];
    const doms = domOrder(g);
    const rv = state.vf.rev ? revOf(g, vi) : null;
    const parts = [];
    parts.push('<defs><marker id="gr-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="gr-arrow-h" d="M0,0 L8,4 L0,8 z"/></marker></defs>');
    parts.push(`<g class="gr-l-sec">${lay.secLines.map(([p, q]) => `<line class="gr-vsec-l" x1="${f1(p[0])}" y1="${f1(p[1])}" x2="${f1(q[0])}" y2="${f1(q[1])}"/>`).join('')}</g>`);
    parts.push('<g class="gr-l-edges">');
    lay.edges.forEach(e => {
      const ek = e.e >= 0 ? g.E[e.e] : null;
      const sId = g.N[e.s] ? g.N[e.s].id : '', tId = g.N[e.t] ? g.N[e.t].id : '';
      let cls = 'gr-ve';
      if (e.k === '포함') cls += ' gr-ve-inc';
      else if (e.k === '매핑') { const st2 = ek && ek.p ? ek.p['검토상태'] : ''; cls += ' gr-ve-map' + (st2 === '승인' || st2 === '수정' ? ' is-human' : ''); }
      else if (e.k === '담보 관계') cls += ' gr-e-rel ' + (e.rel === '통합' ? 'gr-e-rel-uni' : 'gr-e-rel-inc');
      else if (e.k === '결합제약') cls += ' gr-ve-cons';
      const nm = g.ekindLabels[EK[e.k]] || e.k;
      const attrs = `class="gr-e ${cls}" data-gr-ekind="${esc(e.k)}" data-gr-s="${esc(sId)}" data-gr-t="${esc(tId)}"${e.e >= 0 ? ` data-gr-e="${e.e}"` : ''} data-tip-title="${esc(nm)}" data-tip-sub="${esc(`${g.N[e.s].l} -> ${g.N[e.t].l}`)}"`;
      const p = e.pts;
      if (e.ctrl) parts.push(`<path ${attrs} d="M${f1(p[0][0])},${f1(p[0][1])} Q${f1(e.ctrl[0])},${f1(e.ctrl[1])} ${f1(p[p.length - 1][0])},${f1(p[p.length - 1][1])}"/>`);
      else parts.push(`<line ${attrs} x1="${f1(p[0][0])}" y1="${f1(p[0][1])}" x2="${f1(p[1][0])}" y2="${f1(p[1][1])}"${e.k === '결합제약' ? ' marker-end="url(#gr-arrow)"' : ''}/>`);
    });
    parts.push('</g><g class="gr-l-ghost" aria-hidden="true"></g><g class="gr-l-nodes">');
    lay.nodes.forEach(nd => {
      const n = g.N[nd.ni];
      let cls = 'gr-v gr-v-' + nd.kind;
      const sub = [];
      let glyph = '';
      let fill = '';
      if (nd.kind === 'r') {
        const rn = renewText(nd.ni);
        if (rn) sub.push(rn);
        if (n.p['담보구분']) sub.push(App.label(n.p['담보구분']));
        if (n.p['가입금액연동']) { sub.push(`${App.label('가입금액연동')}: ${n.p['가입금액연동']}`); glyph += `<rect class="gr-v-link" x="${f1(nd.r - 1)}" y="${f1(-nd.r - 3)}" width="5" height="5"/>`; }
        if (rv && !lineageHas(g, nd.ni, rv.prev)) { cls += ' is-newrev'; sub.push(t('grRevNew')); glyph += `<circle class="gr-v-newrev" r="${f1(nd.r + 3)}"/>`; }
        if (n.o === 'EPOST') cls += ' is-ours';
      } else if (nd.kind === 'b') {
        if (n.p['매핑상태'] === '대기') { cls += ' is-mwait'; sub.push(App.label('대기')); }
        const xw = n.p['추출검수대기항목'];
        if (Array.isArray(xw) && xw.length) { cls += ' is-wait'; sub.push(`${App.label('추출검수대기항목')}: ${xw.map(v => App.label(v)).join(', ')}`); }
        const ss = (g.benStds.get(nd.ni) || []).map(x => g.N[x.std].l);
        if (ss.length) sub.push(ss.join(', '));
        else if (n.p['매핑상태']) sub.push(App.label(n.p['매핑상태']));
        if (n.o === 'EPOST') cls += ' is-ours';
      } else {
        const d = domOf(g, nd.ni), di = doms.indexOf(d);
        fill = ` style="fill:var(--gr-dom-${di < 0 ? 4 : Math.min(di, 4)})"`;
        sub.push(d);
        const bd = lay.badges.find(b => b.s === nd.ni);
        if (bd) sub.push(t('grMoreBenTpl', { n: fmt(bd.n) }));
      }
      parts.push(`<g class="${cls}" transform="translate(${f1(nd.x)} ${f1(nd.y)})" tabindex="-1" role="button" aria-label="${esc(n.l)}" data-gr-fk="v:${esc(n.id)}" data-gr-id="${esc(n.id)}" data-gr-mid="${esc(n.id)}" data-gr-idx="${nd.ni}" data-gr-kind="${KIND_NM[nd.kind]}" data-gr-r="${f1(nd.r)}"${nd.kind === 'r' && n.p['갱신여부'] ? ` data-gr-renew="${esc(n.p['갱신여부'])}"` : ''} data-aim="circle" data-tip-title="${esc(n.l)}" data-tip-sub="${esc(sub.join(' / '))}"><circle class="gr-v-c" r="${f1(nd.r)}"${fill}/>${glyph}</g>`);
    });
    parts.push('</g>');
    // 가운데 종형 상자: 1행 회사 이름과 미매핑 급부 수, 2행 종형명
    const vs = g.summary && g.summary['종형'] && g.summary['종형'][vn.id];
    const um = vs && vs['미연결급부'] != null ? +vs['미연결급부'] : null;
    const [bx0, by0, bx1, by1] = lay.box;
    const bw = bx1 - bx0, bh = by1 - by0;
    const umTx = um != null ? t('grUnmappedTpl', { n: fmt(um) }) : '';
    let nm = fullVarName(g, vi);
    const maxW = bw - 14;
    if (textW(nm, 600) > maxW) { while (nm.length > 1 && textW(nm + '…', 600) > maxW) nm = nm.slice(0, -1); nm += '…'; }
    let org = orgLabel(vn.o);
    const orgMax = maxW - (umTx ? textW(umTx) + 8 : 0);
    if (textW(org) > orgMax) { while (org.length > 1 && textW(org + '…') > orgMax) org = org.slice(0, -1); org += '…'; }
    const asc = textAsc();
    parts.push(`<g class="gr-l-box"><g class="gr-vbox" transform="translate(${f1(lay.ring.cx)} ${f1(lay.ring.cy)})" tabindex="0" role="button" aria-label="${esc(fullVarName(g, vi))}" data-gr-fk="v:${esc(vn.id)}" data-gr-id="${esc(vn.id)}" data-gr-mid="${esc(vn.id)}" data-gr-idx="${vi}" data-gr-kind="종형"${um != null ? ` data-gr-unmapped="${um}"` : ''} data-aim="rect" data-tip-title="${esc(fullVarName(g, vi))}" data-tip-sub="${esc([orgLabel(vn.o), umTx].filter(Boolean).join(' / '))}">`
      + `<rect class="gr-vbox-r" x="${f1(-bw / 2)}" y="${f1(-bh / 2)}" width="${f1(bw)}" height="${f1(bh)}"/>`
      + `<text class="gr-tx" x="${f1(-bw / 2 + 7)}" y="${f1(-bh / 2 + 4 + asc)}">${esc(org)}</text>`
      + (umTx ? `<text class="gr-tx gr-vbox-um" x="${f1(bw / 2 - 7)}" y="${f1(-bh / 2 + 4 + asc)}" text-anchor="end">${esc(umTx)}</text>` : '')
      + `<text class="gr-tx gr-vbox-nm" x="${f1(-bw / 2 + 7)}" y="${f1(-bh / 2 + 4 + asc + NET_FS + 5)}">${esc(nm)}</text></g></g>`);
    // 라벨
    parts.push('<g class="gr-l-labels">');
    lay.secLabels.forEach(sl => parts.push(`<text class="gr-tx gr-vsec" data-gr-lb="sector" data-gr-lbox="${sl.box.map(f1).join(',')}" x="${f1(sl.box[0])}" y="${f1(sl.box[1] + 1 + asc)}">${esc(sl.tx)}</text>`));
    if (lay.outLabel) { const b = lay.outLabel.box; parts.push(`<text class="gr-tx gr-vsec" data-gr-lb="out" data-gr-lbox="${b.map(f1).join(',')}" x="${f1(b[0])}" y="${f1(b[1] + 1 + asc)}">${esc(lay.outLabel.tx)}</text>`); }
    if (lay.revLine) { const b = lay.revLine.box; parts.push(`<text class="gr-tx gr-vrev" data-gr-lb="rev" data-gr-lbox="${b.map(f1).join(',')}" x="${f1(b[0])}" y="${f1(b[1] + 1 + asc)}">${esc(lay.revLine.tx)}</text>`); }
    lay.badges.forEach(bd => {
      const b = bd.box;
      parts.push(`<g class="gr-vmore" data-gr-more="${bd.n}" data-gr-for="${esc(g.N[bd.s].id)}" data-gr-for-idx="${bd.s}" data-gr-lb="badge" data-gr-lbox="${b.map(f1).join(',')}" data-tip-title="${esc(g.N[bd.s].l)}" data-tip-sub="${esc(t('grMoreBenTpl', { n: fmt(bd.n) }))}"><rect x="${f1(b[0])}" y="${f1(b[1])}" width="${f1(b[2] - b[0])}" height="${f1(b[3] - b[1])}"/><text class="gr-tx" x="${f1((b[0] + b[2]) / 2)}" y="${f1(b[1] + 1 + asc)}" text-anchor="middle">${esc(bd.tx)}</text></g>`);
    });
    lay.labels.forEach((lb, ni) => {
      const b = lb.box;
      parts.push(`<text class="gr-tx gr-vlb" data-gr-lb="${lay.nmap.get(ni).kind === 'r' ? 'rider' : 'std'}" data-gr-for="${esc(g.N[ni].id)}" data-gr-lbox="${b.map(f1).join(',')}" x="${f1(b[0])}" y="${f1(b[1] + 1 + asc)}"><tspan class="gr-vlb-b">${esc(lb.body)}</tspan>${lb.suffix ? `<tspan class="gr-vlb-rn">&#160;${esc(lb.suffix)}</tspan>` : ''}</text>`);
    });
    parts.push('</g>');
    return `<svg class="gr-net-svg gr-alt-svg gr-vt-svg" id="gr-vt-svg" xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="group" aria-label="${esc(t('grPresetVariant'))}" data-gr-w="${W}" data-gr-h="${H}" data-gr-k-lim="${lay.kLim == null ? '' : lay.kLim}" data-gr-ms="${f1(lay.ms)}">${parts.join('')}</svg>`;
  }

  // ---------- 시장 동향 보기(7절) ----------
  function mkNewsSet(g, f) {
    const wk = App.S && App.S['시장소식'] ? App.S['시장소식']['주차'] : '';
    return g.N.filter(n => n.k === NK['시장 동향'] && (f === 'all' || (n.p['선별상태'] === 'passed' && (f === 'allweek' || n.p['수집주차'] === wk)))).map(n => n.i);
  }
  function newsPub(g, ni) {
    const x = g.adj[ni].find(y => y.ek === EK['발표'] && g.N[y.j].k === NK['회사']);
    return x ? { org: x.j, e: x.e } : null;
  }
  function mkCmpOrgs(g, c) {
    const codes = ['EPOST'];
    (c.peerIds || []).forEach(id => { const vi = g.byId.get(id); const o = vi != null ? g.N[vi].o : null; if (o && !codes.includes(o)) codes.push(o); });
    return codes.map(cd => g.byId.get('ORG:' + cd)).filter(x => x != null);
  }
  function mkLayout(g, c, W, H) {
    const t0 = performance.now();
    const news = mkNewsSet(g, state.nf);
    const byOrg = new Map();
    news.forEach(ni => { const pb = newsPub(g, ni); if (!pb) return; if (!byOrg.has(pb.org)) byOrg.set(pb.org, []); byOrg.get(pb.org).push([ni, pb.e]); });
    const cmp = mkCmpOrgs(g, c);
    const rank = n => { const k = n.p['기관구분']; if (k === '보험회사') return n.p['업권'] === '생명보험' ? 0 : n.p['업권'] === '손해보험' ? 1 : 2; return k === '감독기관' ? 3 : k === '협회' ? 4 : k === '업계 공통' ? 5 : 6; };
    const rest = g.N.filter(n => n.k === NK['회사'] && !cmp.includes(n.i) && byOrg.has(n.i)).sort((a, b) => rank(a) - rank(b) || String(a.o).localeCompare(String(b.o)));
    const orgs = cmp.concat(rest.map(n => n.i));
    const [CW, CH] = MK_CELL;
    const cols = Math.max(1, Math.min(orgs.length, Math.floor((W - 2 * NET_MARGIN) / CW)));
    const rows = Math.ceil(orgs.length / cols);
    const x0 = (W - cols * CW) / 2, top = 6;
    const Hs = Math.max(H, top * 2 + rows * CH);
    const nodes = [], edges = [], labels = [];
    const groups = orgs.map((oi, k) => {
      const cx = x0 + (k % cols) * CW + CW / 2, cy = top + Math.floor(k / cols) * CH + 60;
      const list = (byOrg.get(oi) || []).slice().sort((a, b) => String(g.N[b[0]].p['발표일자'] || '').localeCompare(String(g.N[a[0]].p['발표일자'] || '')) || a[0] - b[0]);
      nodes.push({ ni: oi, kind: 'o', x: cx, y: cy, r: MK_RO, cnt: list.length });
      list.forEach(([ni, e], j) => {
        const a = 2 * Math.PI * j / list.length;
        const x = cx + MK_RING * Math.sin(a), y = cy - MK_RING * Math.cos(a);
        nodes.push({ ni, kind: 'n', x, y, r: MK_RN, org: oi, nx: Math.sin(a), ny: -Math.cos(a) });
        const ux = Math.sin(a), uy = -Math.cos(a);
        edges.push({ s: oi, t: ni, e, pts: [[cx + ux * MK_RO, cy + uy * MK_RO], [x - ux * MK_RN, y - uy * MK_RN]] });
      });
      return { oi, cx, cy };
    });
    // 회사 라벨: 이름은 노드 아래, 배지와 건수는 링 아래
    const obstacles = nodes.map(n => ['n' + n.ni, cbox(n.x, n.y, n.r + 1)]);
    groups.forEach(gr => {
      const n = g.N[gr.oi];
      const nm = orgLabel(n.o), w1 = textW(nm, 600);
      let b1 = [gr.cx - w1 / 2, gr.cy + MK_RO + 3, gr.cx + w1 / 2, gr.cy + MK_RO + 3 + VT_LBL_H];
      // 이름이 둘레의 시장 동향 노드와 겹치면 링 아래로 내린다
      const below = gr.cy + MK_RING + MK_RN + 3;
      if (nodes.some(x => x.org === gr.oi && boxOv(b1, cbox(x.x, x.y, x.r + 1)))) b1 = [b1[0], below, b1[2], below + VT_LBL_H];
      const bdg = [];
      if (n.p['기관구분'] && n.p['기관구분'] !== '보험회사') bdg.push(App.label(n.p['기관구분']));
      if (n.p['업권'] === '생명보험' || n.p['업권'] === '손해보험') bdg.push(App.label(n.p['업권']));
      if (n.p['비교대상']) bdg.push(t('grCmpOrg'));
      bdg.push(t('grNewsCntTpl', { n: fmt(nodes.find(x => x.ni === gr.oi).cnt) }));
      const tx2 = bdg.join(', '), w2 = textW(tx2);
      const y2 = Math.max(below, b1[3]) + 1;
      const b2 = [gr.cx - w2 / 2, y2, gr.cx + w2 / 2, y2 + VT_LBL_H];
      labels.push({ kind: 'org', ni: gr.oi, tx: nm, box: b1, strong: true }, { kind: 'orgb', ni: gr.oi, tx: tx2, box: b2 });
      obstacles.push(['o1' + gr.oi, b1], ['o2' + gr.oi, b2]);
    });
    // 시장 동향 라벨: 발표일자(통과 기준 미달이면 판정확률을 붙인다), 겹치면 숨기고 호버로 보인다
    const items = nodes.filter(n => n.kind === 'n').map(n => {
      const p = g.N[n.ni].p;
      const tx = p['선별상태'] === 'below' ? `${p['발표일자'] || ''} ${App.label('below')} ${p['판정확률'] != null ? p['판정확률'] : ''}`.trim() : String(p['발표일자'] || '');
      return { key: 'n' + n.ni, ni: n.ni, x: n.x, y: n.y, r: n.r, nx: n.nx, ny: n.ny, w: textW(tx), tx };
    });
    const lab = placeLabels(items, obstacles, W, Hs, edges);
    items.forEach(it => { if (lab.has(it.key)) labels.push({ kind: 'news', ni: it.ni, tx: it.tx, box: lab.get(it.key) }); });
    return { kind: 'mk', W, H, Hs, scroll: Hs > H, nodes, edges, labels, orgs, news, ms: performance.now() - t0 };
  }
  function mkSVG(g, c, lay) {
    const W = lay.W, H = lay.Hs, asc = textAsc();
    const parts = ['<g class="gr-l-edges">'];
    lay.edges.forEach(e => parts.push(`<line class="gr-e gr-me" data-gr-ekind="발표" data-gr-s="${esc(g.N[e.s].id)}" data-gr-t="${esc(g.N[e.t].id)}" data-gr-e="${e.e}" x1="${f1(e.pts[0][0])}" y1="${f1(e.pts[0][1])}" x2="${f1(e.pts[1][0])}" y2="${f1(e.pts[1][1])}" data-tip-title="${esc(g.ekindLabels[EK['발표']])}"/>`));
    parts.push('</g><g class="gr-l-nodes">');
    lay.nodes.forEach(nd => {
      const n = g.N[nd.ni];
      if (nd.kind === 'o') {
        const sub = [n.p['기관구분'] ? App.label(n.p['기관구분']) : '', n.p['업권'] ? App.label(n.p['업권']) : '', n.p['비교대상'] ? t('grCmpOrg') : '', t('grNewsCntTpl', { n: fmt(nd.cnt) })].filter(Boolean).join(' / ');
        parts.push(`<g class="gr-v gr-mk-o${n.o === 'EPOST' ? ' is-ours' : ''}" transform="translate(${f1(nd.x)} ${f1(nd.y)})" tabindex="-1" role="button" aria-label="${esc(orgLabel(n.o))}" data-gr-fk="v:${esc(n.id)}" data-gr-id="${esc(n.id)}" data-gr-idx="${nd.ni}" data-gr-kind="회사" data-gr-r="${nd.r}" data-gr-count="${nd.cnt}" data-aim="circle" data-tip-title="${esc(orgLabel(n.o))}" data-tip-sub="${esc(sub)}"><circle class="gr-v-c" r="${nd.r}"/></g>`);
      } else {
        const p = n.p;
        const below = p['선별상태'] === 'below';
        const sub = [p['발표일자'], p['분류유형'] ? App.label(p['분류유형']) : '', below ? `${App.label('below')}, ${App.label('판정확률')} ${p['판정확률']}` : '', p['핵심요약']].filter(Boolean).join(' / ');
        parts.push(`<g class="gr-v gr-mk-n${below ? ' is-below' : ''}" transform="translate(${f1(nd.x)} ${f1(nd.y)})" tabindex="-1" role="button" aria-label="${esc(String(p['핵심요약'] || n.l))}" data-gr-fk="v:${esc(n.id)}" data-gr-id="${esc(n.id)}" data-gr-idx="${nd.ni}" data-gr-kind="시장 동향" data-gr-r="${nd.r}" data-gr-org="${esc(g.N[nd.org].id)}" data-gr-state="${esc(p['선별상태'] || '')}" data-aim="circle" data-tip-title="${esc(n.l)}" data-tip-sub="${esc(sub)}"><circle class="gr-v-c" r="${nd.r}"/></g>`);
      }
    });
    parts.push('</g><g class="gr-l-labels">');
    lay.labels.forEach(lb => {
      const b = lb.box;
      parts.push(`<text class="gr-tx gr-mlb${lb.strong ? ' gl-1' : ''}" data-gr-lb="${lb.kind}" data-gr-for="${esc(g.N[lb.ni].id)}" data-gr-lbox="${b.map(f1).join(',')}" x="${f1(b[0])}" y="${f1(b[1] + 1 + asc)}">${esc(lb.tx)}</text>`);
    });
    parts.push('</g>');
    return `<svg class="gr-net-svg gr-alt-svg gr-mk-svg" id="gr-mk-svg" xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="group" aria-label="${esc(t('grPresetNews'))}" data-gr-w="${W}" data-gr-h="${H}" data-gr-ms="${f1(lay.ms)}">${parts.join('')}</svg>`;
  }

  // ---------- 두 보기의 그리기, 선택, 위치 트랜지션 ----------
  function renderAltView(g, c, animate) {
    renderedEdges = new Map();
    if (innerWidth < 1000) {
      lastCenterEl.innerHTML = `<div class="gr-wrap" id="gr-stage-root">${trailNavHTML()}<div class="gr-nl">${state.preset === 'variant' ? vtNarrowHTML(g) : mkNarrowHTML(g, c)}</div></div>`;
      net.lay = null;
      alt.lay = null;
      syncLeftActive();
      return;
    }
    const nav = lastCenterEl.querySelector('#gr-stage-root > .gr-trail');
    let host = lastCenterEl.querySelector('#gr-net');
    if (host && nav) nav.outerHTML = trailNavHTML();
    else {
      lastCenterEl.innerHTML = `<div class="gr-wrap" id="gr-stage-root">${trailNavHTML()}<div class="gr-net" id="gr-net"></div></div>`;
      host = lastCenterEl.querySelector('#gr-net');
    }
    host.classList.remove('is-scroll');
    host.style.height = '';
    const [W, H] = netArea(host);
    if (W < 200 || H < 200) {
      if ((net.retry = (net.retry || 0) + 1) < 30) requestAnimationFrame(() => { if (App.state.tab === 'graph' && state.preset !== 'cover') rerenderGraph(false); });
      return;
    }
    net.retry = 0;
    const prevNet = host.querySelector('#gr-net-svg');
    const prev = animate && prevNet && net.lay && state.preset === 'variant' && moveDur() ? capturePos(prevNet) : null;
    endMove();
    net.lay = null;
    net.ex = null;
    net.hover = null;
    const lay = state.preset === 'variant' ? vtLayout(g, state.varIdx, W, H) : mkLayout(g, c, W, H);
    alt.lay = lay;
    host.classList.toggle('is-scroll', !!lay.scroll);
    host.style.height = H + 'px';
    host.innerHTML = state.preset === 'variant' ? vtSVG(g, c, lay) : mkSVG(g, c, lay);
    syncLeftActive();
    const svg = host.querySelector('svg');
    if (prev) morphIn(svg, prev);
    applyAltState();
    const first = (state.selNode != null && svg.querySelector(`[data-gr-idx="${state.selNode}"]`)) || svg.querySelector('.gr-vbox') || svg.querySelector('[data-gr-fk]');
    if (first) setRoving(svg, first);
    requestAnimationFrame(() => App.updateSelLink(false));
  }

  function altSvg() { return lastCenterEl && lastCenterEl.querySelector('#gr-vt-svg, #gr-mk-svg'); }

  // 선택: 선택한 노드와 이어진 엣지와 노드만 원래대로, 나머지는 흐리게(종형 상자 선택은 흐리지 않음)
  function applyAltState() {
    const svg = altSvg();
    if (!svg) return;
    const g = ensureGraph();
    svg.querySelectorAll('.is-sel, .is-keep, .is-esel').forEach(x => x.classList.remove('is-sel', 'is-keep', 'is-esel'));
    const selId = state.selNode != null && g.N[state.selNode] ? g.N[state.selNode].id : null;
    const el = selId ? svg.querySelector(`[data-gr-id="${CSS.escape(selId)}"]`) : null;
    let dim = false;
    if (el) {
      el.classList.add('is-sel', 'is-keep');
      if (!el.classList.contains('gr-vbox')) {
        dim = true;
        const keep = new Set([selId]);
        svg.querySelectorAll('.gr-e').forEach(e => { if (e.dataset.grS === selId || e.dataset.grT === selId) { e.classList.add('is-keep'); keep.add(e.dataset.grS); keep.add(e.dataset.grT); } });
        svg.querySelectorAll('[data-gr-id]').forEach(x => { if (keep.has(x.dataset.grId)) x.classList.add('is-keep'); });
        svg.querySelectorAll('[data-gr-for]').forEach(x => { if (keep.has(x.dataset.grFor)) x.classList.add('is-keep'); });
      }
    }
    if (state.selEdge && state.selEdge.startsWith('e:')) {
      const ee = svg.querySelector(`.gr-e[data-gr-e="${CSS.escape(state.selEdge.slice(2))}"]`);
      if (ee) {
        dim = true;
        ee.classList.add('is-esel', 'is-keep');
        svg.querySelectorAll('[data-gr-id], [data-gr-for]').forEach(x => { const id = x.dataset.grId || x.dataset.grFor; if (id === ee.dataset.grS || id === ee.dataset.grT) x.classList.add('is-keep'); });
      }
    }
    svg.classList.toggle('is-selm', dim);
  }

  function altActivate(el) {
    const g = ensureGraph();
    if (!el) {
      if (App.state.sel.graph != null) App.unselect({ restoreFocus: false });
      return;
    }
    if (el.dataset.grMore != null) el = altSvg().querySelector(`[data-gr-idx="${el.dataset.grForIdx}"]`) || el;
    if (el.dataset.grIdx != null) {
      const ni = +el.dataset.grIdx;
      state.selNode = ni;
      state.selEdge = null;
      net.focusKey = net.selFk = fkOf(el);
      App.select('n:' + g.N[ni].id, { animate: true, focus: false });
      applyAltState();
    } else if (el.dataset.grE != null) {
      state.selEdge = 'e:' + el.dataset.grE;
      state.selNode = null;
      App.select('edge:e:' + el.dataset.grE, { animate: true, focus: false });
      applyAltState();
    }
  }
  function altClick(e) {
    const el = e.target.closest && e.target.closest('[data-gr-idx], [data-gr-more], .gr-e[data-gr-e]');
    altActivate(el || null);
  }

  // 담보별 연결에서 종형 구성으로: 앵커는 가운데 상자로, 보유 표준담보는 바깥 타원으로 옮기고 나머지는 흐려지며 빠진다(4.4)
  function morphIn(svg, prev) {
    const dur = moveDur();
    if (!dur || !svg) return;
    const ms = App.motionScale ? App.motionScale() : 1;
    const ghost = svg.querySelector('.gr-l-ghost');
    const used = new Set();
    const moves = [];
    const anchorOf = id => { let hit = null; prev.a.forEach(q => { if (!hit && q.el.dataset.grId === id) hit = q; }); return hit; };
    svg.querySelectorAll('[data-gr-mid]').forEach(el => {
      const m = /translate\(([-\d.]+)[ ,]+([-\d.]+)\)/.exec(el.getAttribute('transform') || '');
      if (!m) return;
      const to = `translate(${m[1]}px, ${m[2]}px)`;
      const isBox = el.classList.contains('gr-vbox');
      const q = isBox ? anchorOf(el.dataset.grMid) : prev.n.get(el.dataset.grMid);
      el.style.transition = 'none';
      if (q) {
        used.add(q.el);
        el.style.transform = `translate(${f1(q.x)}px, ${f1(q.y)}px)` + (isBox ? ` scale(${Math.max(0.05, (2 * q.R) / VT_BOX[0]).toFixed(3)})` : '');
        moves.push([el, to, false]);
      } else {
        el.style.transform = `${to} scale(0.6)`;
        el.style.opacity = '0';
        moves.push([el, to, true]);
      }
    });
    const gone = [];
    prev.n.forEach(q => { if (!used.has(q.el)) gone.push(q); });
    prev.a.forEach(q => { if (!used.has(q.el)) gone.push(q); });
    gone.forEach(q => { q.el.classList.remove('is-keep', 'is-sel', 'is-big', 'is-on'); q.el.style.transition = 'none'; q.el.style.transform = `translate(${f1(q.x)}px, ${f1(q.y)}px)`; q.el.style.opacity = '1'; ghost.appendChild(q.el); });
    prev.g.forEach(q => { q.el.style.transition = 'none'; q.el.style.opacity = '1'; ghost.appendChild(q.el); gone.push(q); });
    prev.layers.forEach(l => { l.style.transition = 'none'; l.style.opacity = prev.opacity.get(l); ghost.appendChild(l); });
    ghost.querySelectorAll('[data-gr-fk]').forEach(x => { x.removeAttribute('data-gr-fk'); x.removeAttribute('tabindex'); });
    const newEdges = Array.from(svg.querySelectorAll(':scope > .gr-l-edges .gr-e'));
    const layers = Array.from(svg.querySelectorAll(':scope > .gr-l-labels, :scope > .gr-l-sec'));
    newEdges.forEach(el => { el.setAttribute('pathLength', '1'); el.style.strokeDasharray = '1'; el.style.strokeDashoffset = '1'; });
    layers.forEach(l => { l.style.opacity = '0'; });
    net.moving = true;
    svg.getBoundingClientRect();
    moves.forEach(([el, to, enter]) => {
      if (enter) { el.style.transition = `opacity ${dur * 0.5}ms var(--ease-in) ${dur * 0.5}ms, transform ${dur * 0.5}ms var(--ease-in) ${dur * 0.5}ms`; el.style.opacity = '1'; }
      else el.style.transition = `transform ${dur}ms var(--ease-graph-move)`;
      el.style.transform = to;
    });
    gone.forEach(q => { q.el.style.transition = `opacity ${Math.round(dur * 0.4)}ms var(--ease-out)`; q.el.style.opacity = '0'; });
    prev.layers.forEach(l => { l.style.transition = `opacity ${Math.round(dur * 0.25)}ms var(--ease-out)`; l.style.opacity = '0'; });
    net.moveT = setTimeout(() => {
      net.moveT = 0;
      net.moving = false;
      if (!svg.isConnected) return;
      moves.forEach(([el]) => { el.style.transition = ''; el.style.transform = ''; el.style.opacity = ''; });
      ghost.textContent = '';
      const drawMs = Math.round(320 * ms), lbMs = Math.round(120 * ms);
      newEdges.forEach(el => { el.style.transition = `stroke-dashoffset ${drawMs}ms var(--ease-in)`; el.style.strokeDashoffset = '0'; });
      layers.forEach(l => { l.style.transition = `opacity ${lbMs}ms var(--ease-in)`; l.style.opacity = '1'; });
      net.moveTs.push(setTimeout(() => {
        newEdges.forEach(el => { el.style.transition = ''; el.style.strokeDasharray = ''; el.style.strokeDashoffset = ''; el.removeAttribute('pathLength'); });
        layers.forEach(l => { l.style.transition = ''; l.style.opacity = ''; });
      }, Math.max(drawMs, lbMs) + 40));
    }, dur + 20);
  }

  // 종형 구성에서 담보별 연결로: 지금 보이는 위치를 담보별 연결의 위치 트랜지션(startMove) 입력으로 바꾼다
  function capturePosVt(svg, lay) {
    const sr = svg.getBoundingClientRect();
    const c = el => { const r = el.getBoundingClientRect(); return { x: r.left - sr.left + r.width / 2, y: r.top - sr.top + r.height / 2, R: r.width / 2 }; };
    const pos = { n: new Map(), g: new Map(), a: new Map() };
    svg.querySelectorAll('.gr-l-nodes > .gr-v').forEach(el => pos.n.set(el.dataset.grId, Object.assign(c(el.querySelector('.gr-v-c')), { el })));
    const box = svg.querySelector('.gr-vbox');
    const a = box && lay.anc.find(x => x.id === box.dataset.grId);
    if (a) pos.a.set(a.key, Object.assign(c(box), { R: a.r, el: box }));
    pos.layers = Array.from(svg.querySelectorAll(':scope > .gr-l-edges, :scope > .gr-l-labels, :scope > .gr-l-sec, :scope > .gr-l-box'));
    pos.opacity = new Map(pos.layers.map(l => [l, getComputedStyle(l).opacity]));
    return pos;
  }

  // 다른 보기로 넘어간다(앵커 클릭, 검색, 상세 패널의 "종형 구성에서 보기", 다른 탭에서 들어올 때)
  function openAlt(preset, vi, selNi) {
    const g = ensureGraph();
    const c = App.ctx();
    pushUndo();
    const fromNet = state.preset === 'cover';
    initPresetState(preset, c, true, vi);
    if (preset === 'news' && selNi != null && g.N[selNi].k === NK['시장 동향']) {
      ['week', 'allweek', 'all'].some(f => { if (mkNewsSet(g, f).includes(selNi)) { state.nf = f; return true; } return false; });
    }
    const target = selNi != null ? selNi : (preset === 'variant' ? state.varIdx : null);
    state.selNode = target;
    state.focusNode = target;
    state.selEdge = null;
    if (lastLeftEl) renderLeftZone(lastLeftEl);
    rerenderGraph(fromNet);
    if (target != null) App.select('n:' + g.N[target].id, { animate: true, focus: false });
    else App.unselect({ push: false, restoreFocus: false });
    const svg = altSvg();
    const el = svg && target != null && svg.querySelector(`[data-gr-idx="${target}"]`);
    if (el) { setRoving(svg, el); try { el.focus({ preventScroll: true }); } catch (e) { /* */ } }
  }

  function vtLeftHTML(g) {
    const vf = state.vf;
    const b = (k, nm, on) => `<button type="button" class="gr-flt${on ? ' is-on' : ''}" data-gr-vf="${esc(k)}" aria-pressed="${on}"><span>${esc(nm)}</span></button>`;
    const rv = revOf(g, state.varIdx);
    return `<div><span class="gr-sec-k">${esc(t('grVtFilterHead'))}</span><div class="gr-flts gr-flts-2">
        ${b('renew:갱신', t('grRenewY'), vf.renew === '갱신')}${b('renew:비갱신', t('grRenewN'), vf.renew === '비갱신')}${b('main', t('grMainFirst'), vf.main)}
        ${rv ? b('rev', t('grRevToggle'), vf.rev) : ''}
      </div></div>
      <div><span class="gr-sec-k">${esc(t('grPropDomain'))}</span><div class="gr-flts gr-flts-2">${domOrder(g).map(d => b('dom:' + d, d, vf.dom === d)).join('')}</div></div>
      <div class="gr-legend">${altLegendHTML(g)}</div>`;
  }
  function mkLeftHTML(g, c) {
    const fl = [['week', t('grNfWeek')], ['allweek', t('grNfAllWeek')], ['all', t('grNfAll')]];
    return `<div><span class="gr-sec-k">${esc(t('grVtFilterHead'))}</span><div class="gr-flts">${fl.map(([k, nm]) => `<button type="button" class="gr-flt${state.nf === k ? ' is-on' : ''}" data-gr-nf="${k}" aria-pressed="${state.nf === k}"><span>${esc(nm)}</span><span class="num">${fmt(mkNewsSet(g, k).length)}</span></button>`).join('')}</div></div>
      <div class="gr-legend">${altLegendHTML(g)}</div>`;
  }
  function altLegendHTML(g) {
    const row = (sw, label) => `<span class="gr-lg-it">${swatchSVG(sw)}<span>${esc(label)}</span></span>`;
    if (state.preset === 'news') {
      return `<div class="gr-lg-sec"><span class="gr-lg-h">${esc(t('grLgNodeHead'))}</span>
        ${row('<g class="gr-mk-o" transform="translate(11 9)"><circle class="gr-v-c" r="7"/></g>', g.kindLabels[NK['회사']])}
        ${row('<g class="gr-mk-n" transform="translate(11 9)"><circle class="gr-v-c" r="5"/></g>', g.kindLabels[NK['시장 동향']])}
        ${row('<g class="gr-mk-n is-below" transform="translate(11 9)"><circle class="gr-v-c" r="5"/></g>', App.label('below'))}
        ${row('<line class="gr-e gr-me" x1="2" y1="9" x2="20" y2="9"/>', g.ekindLabels[EK['발표']])}</div>`;
    }
    const doms = domOrder(g).slice(0, 5);
    return `<div class="gr-lg-sec is-2col"><span class="gr-lg-h">${esc(t('grLgNodeHead'))}</span>
        ${row('<g class="gr-v gr-v-r" transform="translate(11 9)"><circle class="gr-v-c" r="5"/></g>', g.kindLabels[NK['특약']])}
        ${row('<g class="gr-v gr-v-b" transform="translate(11 9)"><circle class="gr-v-c" r="4.5"/></g>', g.kindLabels[NK['급부']])}
      </div>
      <div class="gr-lg-sec is-2col"><span class="gr-lg-h">${esc(t('grPropDomain'))}</span>${doms.map((d, i) => row(`<circle class="gr-v-c" cx="11" cy="9" r="6" style="fill:var(--gr-dom-${i})"/>`, d)).join('')}</div>
      <div class="gr-lg-sec is-2col"><span class="gr-lg-h">${esc(t('grLgMark'))}</span>
        ${row('<g class="gr-v gr-v-b is-mwait" transform="translate(11 9)"><circle class="gr-v-c" r="5"/></g>', App.label('대기'))}
        ${row('<g class="gr-v gr-v-b is-wait" transform="translate(11 9)"><circle class="gr-v-c" r="5"/></g>', t('grMkWait'))}
        ${row('<g class="gr-v gr-v-r" transform="translate(11 9)"><circle class="gr-v-c" r="5"/><circle class="gr-v-newrev" r="8"/></g>', t('grRevNew'))}
        ${row('<g class="gr-v gr-v-r" transform="translate(9 10)"><circle class="gr-v-c" r="5"/><rect class="gr-v-link" x="4" y="-8" width="5" height="5"/></g>', App.label('가입금액연동'))}
        ${row('<g class="gr-vmore"><rect x="1" y="2" width="20" height="14"/></g>', t('grLgMore'))}
      </div>
      <div class="gr-lg-sec is-2col"><span class="gr-lg-h">${esc(t('grLgEdgeHead'))}</span>
        ${row('<line class="gr-e gr-ve gr-ve-inc" x1="2" y1="9" x2="20" y2="9"/>', g.ekindLabels[EK['포함']])}
        ${row('<line class="gr-e gr-ve gr-ve-map" x1="2" y1="9" x2="20" y2="9"/>', g.ekindLabels[EK['매핑']])}
        ${row('<line class="gr-e gr-e-rel gr-e-rel-inc" x1="2" y1="9" x2="20" y2="9"/>', t('grLgRelInc'))}
        ${row('<line class="gr-e gr-e-rel gr-e-rel-uni" x1="2" y1="9" x2="20" y2="9"/>', t('grLgRelUni'))}
        ${row('<line class="gr-e gr-ve gr-ve-cons" x1="2" y1="9" x2="20" y2="9"/>', g.ekindLabels[EK['결합제약']])}
      </div>`;
  }

  // 1,000px 미만(8.3): 종형 구성은 보장 대분류별 구역에 표준담보 목록, 탭하면 그 담보로 가는 특약과 급부
  function vtNarrowHTML(g) {
    const vi = state.varIdx;
    if (vi == null) return '';
    const held = g.heldBy.get(vi);
    const doms = domOrder(g);
    const stds = held ? Array.from(held.keys()).sort((a, b) => a - b) : [];
    const secs = doms.map((d, i) => [d, i, stds.filter(si => { const k = doms.indexOf(domOf(g, si)); return (k < 0 ? 4 : Math.min(k, 4)) === i; })]).filter(x => x[2].length);
    const head = `<div class="gr-nl-hd"><span class="gl-1">${esc(fullVarName(g, vi))}</span><span>${esc(orgLabel(g.N[vi].o))}</span></div>`;
    return `<section class="gr-nl-card">${head}${nlDomBarHTML(g, stds)}</section>` + secs.map(([d, i, list]) => `<section class="gr-nl-card"><div class="gr-nl-hd"><span class="gl-1">${esc(d)}</span><span>${esc(t('grGrpCntTpl', { n: fmt(list.length) }))}</span></div>
      <div class="gr-nl-chips">${list.map(si => nlChipHTML(g, si, [], i, state.selNode === si)
        + (state.selNode === si ? `<div class="gr-nl-exp"><button type="button" class="gr-nl-more" data-gr-detail="n:${esc(g.N[si].id)}">${esc(t('grNlDetail'))}</button><ul class="gr-nl-rs">${nlChainHTML(g, vi, si)}</ul></div>` : '')).join('')}</div></section>`).join('');
  }
  function mkNarrowHTML(g, c) {
    const lay = mkLayout(g, c, 360, 400);
    return lay.orgs.map(oi => `<div class="gr-nl-step"><div class="gr-nl-hd"><span>${esc(orgLabel(g.N[oi].o))}</span><span>${esc(t('grNewsCntTpl', { n: fmt(lay.nodes.find(n => n.ni === oi).cnt) }))}</span></div>
      <div class="gr-nl-items">${lay.nodes.filter(n => n.org === oi).map(n => `<button type="button" class="gr-nl-it${state.selNode === n.ni ? ' is-sel' : ''}" data-gr-node="${esc(g.N[n.ni].id)}" data-gr-idx="${n.ni}">${esc(String(g.N[n.ni].p['발표일자'] || ''))} ${esc(g.N[n.ni].l)}</button>`).join('')}</div></div>`).join('');
  }

  function altCopy(g) {
    const lay = alt.lay;
    if (state.preset === 'variant' && lay && lay.kind === 'vt') {
      const rows = [];
      lay.riders.forEach(r => {
        const bs = lay.bens.filter(b => lay.benRider.get(b) === r);
        if (!bs.length) rows.push([g.N[r].l, '', '']);
        bs.forEach(b => rows.push([g.N[r].l, g.N[b].l, (g.benStds.get(b) || []).map(x => g.N[x.std].l).join(', ')]));
      });
      App.copyRows(t('grCopyVtCols').split(','), rows, { title: `${t('grPresetVariant')} ${fullVarName(g, lay.vi)}` });
      return;
    }
    const news = lay && lay.kind === 'mk' ? lay.news : mkNewsSet(g, state.nf);
    const rows = news.map(ni => { const p = g.N[ni].p, pb = newsPub(g, ni); return [pb ? orgLabel(g.N[pb.org].o) : '', p['발표일자'] || '', p['분류유형'] ? App.label(p['분류유형']) : '', p['핵심요약'] || g.N[ni].l, p['선별상태'] ? App.label(p['선별상태']) : '']; });
    App.copyRows(t('grCopyMkCols').split(','), rows, { title: t('grPresetNews') });
  }

  // ---------- 위임 이벤트(클릭, 검색, 엣지 가리킴 칩, 키보드 화살표 및 되돌리기) ----------
  document.addEventListener('input', e => {
    if (App.state.tab !== 'graph') return;
    if (e.target && e.target.id === 'gr-search') {
      updateSearchSugg(e.target.value);
    }
  });

  document.addEventListener('pointerover', e => {
    if (App.state.tab !== 'graph' || !lastCenterEl || e.pointerType === 'touch') return;
    const eg = e.target.closest && e.target.closest('[data-gr-edge]');
    if (eg) showEdgeHoverChip(eg);
    else if (hoveredEdgeEl) clearEdgeHoverChip();
  });

  document.addEventListener('pointerout', e => {
    if (App.state.tab !== 'graph' || !hoveredEdgeEl) return;
    const rel = e.relatedTarget;
    if (!rel || !(rel.closest && rel.closest('[data-gr-edge]') === hoveredEdgeEl)) {
      clearEdgeHoverChip();
    }
  });

  document.addEventListener('pointerdown', e => {
    if (App.state.tab !== 'graph' || !lastCenterEl) return;
    const eg = e.target.closest && e.target.closest('[data-gr-edge]');
    if (eg) {
      const chip = lastCenterEl.querySelector('#gr-edge-chip');
      if (chip && !chip.hidden) chip.classList.add('is-press');
    }
  }, { passive: true });

  document.addEventListener('pointerup', () => {
    if (!lastCenterEl) return;
    const chip = lastCenterEl.querySelector('#gr-edge-chip');
    if (chip) chip.classList.remove('is-press');
  }, { passive: true });

  document.addEventListener('click', e => {
    if (App.state.tab !== 'graph') return;
    const c = App.ctx();

    const altS = e.target.closest && e.target.closest('#gr-vt-svg, #gr-mk-svg');
    if (altS) {
      e.stopPropagation();
      altClick(e);
      return;
    }

    // 종형 구성과 시장 동향의 필터(6절 9, 10번, 7절 2번)
    const vfb = e.target.closest && e.target.closest('[data-gr-vf]');
    if (vfb) {
      e.stopPropagation();
      pushUndo();
      const [k, v] = vfb.dataset.grVf.split(':');
      const vf = Object.assign({}, state.vf);
      if (k === 'renew') vf.renew = vf.renew === v ? null : v;
      else if (k === 'dom') vf.dom = vf.dom === v ? null : v;
      else if (k === 'main') vf.main = !vf.main;
      else if (k === 'rev') vf.rev = !vf.rev;
      state.vf = vf;
      syncLeftActive();
      rerenderGraph(false);
      if (state.selNode != null) App.select('n:' + ensureGraph().N[state.selNode].id, { animate: false, push: false, focus: false });
      return;
    }
    const nfb = e.target.closest && e.target.closest('[data-gr-nf]');
    if (nfb) {
      e.stopPropagation();
      pushUndo();
      state.nf = nfb.dataset.grNf;
      syncLeftActive();
      rerenderGraph(false);
      return;
    }
    const gst = e.target.closest && e.target.closest('[data-gr-go-std]');
    if (gst) {
      e.stopPropagation();
      const si = +gst.dataset.grGoStd;
      if (!sceneOf(ensureGraph(), c).info.has(si)) { App.toast(t('grNotInScene')); return; }
      if (state.preset !== 'cover') { pushUndo(); initPresetState('cover', c, true); if (lastLeftEl) renderLeftZone(lastLeftEl); }
      netSelectStd(si, { rerender: true });
      return;
    }
    const sidx = e.target.closest && e.target.closest('[data-gr-sel-idx]');
    if (sidx) {
      e.stopPropagation();
      const ni = +sidx.dataset.grSelIdx;
      const svg = altSvg();
      const el = svg && svg.querySelector(`[data-gr-idx="${ni}"]`);
      if (el) altActivate(el);
      else jumpToAnyNode(ni, c);
      return;
    }

    const netSvg = e.target.closest && e.target.closest('#gr-net-svg');
    if (netSvg) {
      e.stopPropagation();
      netClick(e, netSvg);
      return;
    }

    const flt = e.target.closest && e.target.closest('[data-gr-filter]');
    if (flt) {
      e.stopPropagation();
      pushUndo();
      state.filter = state.filter === flt.dataset.grFilter ? null : flt.dataset.grFilter;
      syncLeftActive();
      applyNetState();
      return;
    }

    const ov = e.target.closest && e.target.closest('[data-gr-open-var]');
    if (ov) {
      e.stopPropagation();
      netOpenVariant(+ov.dataset.grOpenVar);
      return;
    }

    const pst = e.target.closest && e.target.closest('[data-gr-pick-std]');
    if (pst) {
      e.stopPropagation();
      netSelectStd(+pst.dataset.grPickStd);
      return;
    }

    const pr = e.target.closest && e.target.closest('[data-gr-preset]');
    if (pr) {
      e.stopPropagation();
      initPresetState(pr.dataset.grPreset, c, false);
      App.unselect({ push: false, restoreFocus: false });
      if (lastLeftEl) renderLeftZone(lastLeftEl);
      rerenderGraph(true);
      return;
    }

    const act = e.target.closest && e.target.closest('[data-gr-act]');
    if (act) {
      e.stopPropagation();
      if (act.dataset.grAct === 'undo') {
        const prev = undoStack.pop();
        if (!prev) return;
        restoreStateSnap(prev);
        if (state.preset === 'cover') syncCoverTrail();
        else if (trail.length > 1) trail.pop();
        rerenderGraph(true);
        reselectFromState();
      } else if (act.dataset.grAct === 'reset') {
        initPresetState(state.preset, c, false);
        App.unselect({ push: false, restoreFocus: false });
        if (lastLeftEl) renderLeftZone(lastLeftEl);
        rerenderGraph(true);
      }
      return;
    }

    const tr = e.target.closest && e.target.closest('[data-gr-trail]');
    if (tr) {
      e.stopPropagation();
      const idx = +tr.dataset.grTrail;
      const item = trail[idx];
      if (!item) return;
      pushUndo();
      restoreStateSnap(item.snap);
      trail = trail.slice(0, idx + 1);
      rerenderGraph(true);
      reselectFromState();
      return;
    }

    const sg = e.target.closest && e.target.closest('[data-gr-sugg]');
    if (sg) {
      e.stopPropagation();
      const ni = +sg.dataset.grSugg;
      state.query = '';
      jumpToAnyNode(ni, c);
      return;
    }

    // 1,000px 미만 목록: 상세와 근거 버튼은 상세 시트를 연다
    const dt = e.target.closest && e.target.closest('[data-gr-detail]');
    if (dt) {
      e.stopPropagation();
      App.select(dt.dataset.grDetail, { animate: true, focus: false });
      return;
    }
    // 1,000px 미만 목록의 노드. 담보 칩은 상세 시트를 열지 않고 그 아래에 펼치며, 다시 탭하면 접는다(8.3)
    const nd = e.target.closest && e.target.closest('[data-gr-node]');
    if (nd) {
      e.stopPropagation();
      const ni = +nd.dataset.grIdx;
      if (nd.classList.contains('gr-nl-chip')) {
        if (state.preset === 'cover') {
          if (state.selStd === ni) { state.selStd = null; rerenderGraph(false); } else netSelectStd(ni, { rerender: true, noPanel: true });
        } else {
          state.selNode = state.selNode === ni ? null : ni;
          state.selEdge = null;
          rerenderGraph(false);
        }
        const again = lastCenterEl && lastCenterEl.querySelector(`.gr-nl-chip[data-gr-idx="${ni}"]`);
        if (again) again.focus({ preventScroll: true });
        return;
      }
      if (state.preset === 'cover') { netSelectStd(ni, { rerender: true }); return; }
      state.selNode = ni;
      state.selEdge = null;
      App.select('n:' + ensureGraph().N[ni].id, { animate: true, focus: false });
      rerenderGraph(false);
      restoreGraphNodeFocus(ni);
    }
  });


  document.addEventListener('keydown', e => {
    if (App.state.tab !== 'graph') return;
    if (e.target && e.target.id === 'gr-search') {
      if (e.key === 'Enter') {
        const first = lastLeftEl && lastLeftEl.querySelector('[data-gr-sugg]');
        if (first) { e.preventDefault(); first.click(); }
      } else if (e.key === 'Escape') {
        const sugg = lastLeftEl && lastLeftEl.querySelector('#gr-sugg');
        if (sugg && !sugg.hidden) { e.stopPropagation(); sugg.hidden = true; }
      }
      return;
    }

    // 담보별 연결: 화살표는 그 방향 ±45도 안의 가장 가까운 대상, Home 은 기준 앵커, End 는 마지막 그룹 라벨, Enter 와 Space 는 선택(4.7)
    const fkEl = e.target.closest && e.target.closest('#gr-net-svg [data-gr-fk]');
    if (fkEl && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const svg = fkEl.closest('#gr-net-svg');
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) {
        e.preventDefault();
        netArrow(svg, fkEl, e.key);
        return;
      }
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        net.focusKey = fkOf(fkEl);
        netActivate(hitOfEl(fkEl));
        // 선택 뒤 포커스가 body 로 빠지지 않게 같은 대상(다시 그렸으면 새 요소)에 둔다
        requestAnimationFrame(() => {
          const sv = lastCenterEl && lastCenterEl.querySelector('#gr-net-svg');
          const el = sv && net.focusKey && sv.querySelector(`[data-gr-fk="${CSS.escape(net.focusKey)}"]`);
          if (el && (document.activeElement === document.body || !document.activeElement || !document.activeElement.isConnected)) { setRoving(sv, el); try { el.focus({ preventScroll: true }); } catch (err) { /* */ } }
        });
        return;
      }
    }

    // 종형 구성과 시장 동향: 화살표는 그 방향 ±45도 안의 가장 가까운 노드, Enter 와 Space 는 선택
    const avEl = e.target.closest && e.target.closest('#gr-vt-svg [data-gr-fk], #gr-mk-svg [data-gr-fk]');
    if (avEl && !e.ctrlKey && !e.metaKey && !e.altKey) {
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) { e.preventDefault(); netArrow(avEl.closest('svg'), avEl, e.key); return; }
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); altActivate(avEl); return; }
    }

    const typing = e.target.closest && e.target.closest('input,select,textarea');
    if (typing) return;
    if ((e.key === 'z' || e.key === 'Z') && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const undoBtn = lastLeftEl && lastLeftEl.querySelector('#gr-btn-undo');
      if (undoBtn && !undoBtn.disabled) undoBtn.click();
    }
  });

  App.on('select', (tabId) => {
    if (tabId !== 'graph') return;
    if (App.state.sel.graph == null && state.preset === 'cover' && (state.selNode != null || state.selEdge != null || state.selStd != null || state.selGroup)) {
      const svg = lastCenterEl && lastCenterEl.querySelector('#gr-net-svg');
      const fk = net.selFk || net.focusKey;
      net.selFk = null;
      const ae = document.activeElement;
      const hadFocus = !ae || ae === document.body || (svg && svg.contains(ae));
      clearSel();
      dropSelTrail();
      applyNetState();
      refreshTrail();
      // Esc 로 풀면 포커스는 선택했던 노드로 돌아간다(4.7)
      const el = svg && fk && svg.querySelector(`[data-gr-fk="${CSS.escape(fk)}"]`);
      if (el && hadFocus) { setRoving(svg, el); try { el.focus({ preventScroll: true }); } catch (e) { /* */ } }
      return;
    }
    if (App.state.sel.graph == null && (state.selNode != null || state.selEdge != null)) {
      const prevIdx = state.selNode;
      state.selNode = null;
      state.selEdge = null;
      applyAltState();
      if (prevIdx != null && altSvg()) restoreGraphNodeFocus(prevIdx);
    }
  });
  App.on('resize', () => {
    if (App.state.tab !== 'graph' || !lastCenterEl) return;
    if (state.preset !== 'cover') { rerenderGraph(false); return; }
    // 브라우저 리사이즈는 150ms 뒤 한 번 다시 계산하고 트랜지션 없이 바꾼다(3.1)
    clearTimeout(net.resizeT);
    net.resizeT = setTimeout(() => { if (App.state.tab === 'graph') rerenderGraph(false); }, 150);
  });

  ui.registerLegend('graph', 'grLegendTitle', () => `<div class="gr-legend is-pop">${state.preset === 'cover' ? legendItemsHTML(ensureGraph(), false, !!(net.lay && net.lay.sc && net.lay.sc.nPeer > 3)) : altLegendHTML(ensureGraph())}</div>`);

  function path() {
    const base = [App.TAB_NAME.graph];
    if (trail.length > 1) base.push(trail[trail.length - 1].label);
    return base;
  }

  function copySummary() {
    const g = ensureGraph();
    if (state.preset === 'cover') {
      App.copyRows(t('grCopyNetCols').split(','), netCopyRows(g, App.ctx()), { title: t('grCopyNetTitle') });
      return;
    }
    altCopy(g);
  }


  App.registerTab({
    id: 'graph',
    layout: 'three',
    renderZones,
    pick,
    defaultEv,
    focus,
    path,
    copySummary,
  });
})();
