/* 탭 6 관계 지도(tab6.js):
   - proto_src/graph/graph.json(#graph-data)을 쉬는 시간이나 처음 열 때 읽고, 모든 수는 자료의 요약과 목록 길이만 그대로 쓴다.
   - 왼쪽부터 일곱 열(소식, 회사, 종형, 특약, 급부, 표준담보, 보장분야) 고정 배치, 1.5px 직각 꺾은선, 표준담보 오른쪽 관계 이중선 꺾쇠.
   - 처음 상태부터 대화 상자 없이 "담보 대응" 그래프가 열리며, 보장분야 -> 표준담보 -> 회사별 특약과 급부 실제 길 펼침과 어느 노드에서나 12개 단위 이웃 펼침(+N 더)을 지원한다.
*/
(function () {
  const { ui, txt, t } = App;
  const { esc, fmt } = ui;

  // 노드와 엣지 종류는 번호가 아니라 graph.json 의 자료 이름으로 찾는다(ensureGraph 에서 채움)
  let NK = {};
  let EK = {};
  const COL_KIND_NAMES = ['시장 동향', '회사', '종형', '특약', '급부', '표준담보', '보장 대분류'];
  let COL_KINDS = [];
  let COL_OF_KIND = {};
  const BATCH_SIZE = 12;

  let G = null;
  let lastLeftEl = null;
  let lastCenterEl = null;
  let lastScopeSig = '';
  let edgeDrawRaf = 0;

  const state = {
    preset: 'cover',     // 'cover' | 'variant' | 'news'
    mode: 'cover-0',     // 'cover-0' | 'cover-1' | 'cover-2' | 'hop'
    activeDom: null,     // node index of 보장분야
    activeStd: null,     // node index of 표준담보
    cols: [[], [], [], [], [], [], []],
    batches: {},         // colIdx -> { pool: number[], shown: number, label: string }
    varLimits: {},       // 'r:<vi>' | 'b:<vi>' -> limit inside cover-2 per-company path
    varMores: {},        // colIdx -> Array<{ afterIdx: number|null, key: string, rem: number, label: string }>
    variantRidersAll: [],// full sorted riders of baseVar in 'variant' preset
    selNode: null,       // node index
    selEdge: null,       // edge key ('e:12' | 'vb:v:d' | 'vs:v:s')
    focusNode: null,     // roving tabindex node index
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
    COL_KINDS = COL_KIND_NAMES.map(nm => NK[nm]);
    COL_OF_KIND = {};
    COL_KINDS.forEach((k, colIdx) => { if (k != null) COL_OF_KIND[k] = colIdx; });
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

  function domainNodesInOrder(g, c) {
    const order = (c.base && c.base['치료여정'] && c.base['치료여정']['행']) || ['암보장', '뇌혈관보장', '심장보장', '뇌심장보장', '공통보장'];
    const out = [];
    const seen = new Set();
    order.forEach(nm => {
      const idx = g.byId.get('CAT:' + nm);
      if (idx != null) { out.push(idx); seen.add(idx); }
    });
    g.N.forEach(n => {
      if (n.k === NK['보장 대분류'] && !seen.has(n.i)) out.push(n.i);
    });
    return out;
  }

  function orgNodesForVariants(g, varIdxs) {
    const out = [];
    const seen = new Set();
    varIdxs.forEach(vi => {
      const code = g.N[vi] && g.N[vi].o;
      if (!code) return;
      const oi = g.byId.get('ORG:' + code);
      if (oi != null && !seen.has(oi)) { out.push(oi); seen.add(oi); }
    });
    return out;
  }

  function cloneStateSnap() {
    return JSON.stringify({
      preset: state.preset,
      mode: state.mode,
      activeDom: state.activeDom,
      activeStd: state.activeStd,
      cols: state.cols.map(arr => arr.slice()),
      batches: state.batches,
      varLimits: state.varLimits,
      varMores: state.varMores,
      variantRidersAll: state.variantRidersAll,
      selNode: state.selNode,
      selEdge: state.selEdge,
      focusNode: state.focusNode,
    });
  }

  function restoreStateSnap(rawStr) {
    const o = JSON.parse(rawStr);
    state.preset = o.preset;
    state.mode = o.mode;
    state.activeDom = o.activeDom;
    state.activeStd = o.activeStd;
    state.cols = o.cols.map(arr => arr.slice());
    state.batches = o.batches || {};
    state.varLimits = o.varLimits || {};
    state.varMores = o.varMores || {};
    state.variantRidersAll = o.variantRidersAll || [];
    state.selNode = o.selNode;
    state.selEdge = o.selEdge;
    state.focusNode = o.focusNode ?? null;
  }

  function pushUndo() {
    const s = cloneStateSnap();
    if (undoStack.length && undoStack[undoStack.length - 1] === s) return;
    undoStack.push(s);
    if (undoStack.length > 40) undoStack.shift();
  }

  function recordTrail(label) {
    const snap = cloneStateSnap();
    if (trail.length && trail[trail.length - 1].label === label) {
      trail[trail.length - 1].snap = snap;
      return;
    }
    trail.push({ label, snap });
    if (trail.length > 10) trail.shift();
  }

  // 종형 구성 틀에서 현재 펼쳐진 특약과 급부에 맞춰 표준담보와 보장분야 열을 이어 갱신한다(1-9)
  function syncVariantDownstream(g, baseVar, resetBenBatch) {
    const allBens = [];
    const allBenSeen = new Set();
    const mustBens = [];
    const mustSeen = new Set();

    // 화면에 보이는 특약마다 최소 1개의 급부를 먼저 넣어 길이 끊기지 않게 한다
    state.cols[3].forEach(ri => {
      const bList = g.riderBens.get(ri) || [];
      if (bList.length && !mustSeen.has(bList[0])) {
        mustSeen.add(bList[0]);
        mustBens.push(bList[0]);
      }
    });
    // 전체 특약 순서대로 전체 급부 풀 구성
    state.variantRidersAll.forEach(ri => {
      (g.riderBens.get(ri) || []).forEach(bi => {
        if (!allBenSeen.has(bi)) { allBenSeen.add(bi); allBens.push(bi); }
      });
    });

    const orderedPool = mustBens.slice();
    const ordSeen = new Set(mustBens);
    // 먼저 현재 보이는 특약의 나머지 급부를 채우고, 그 뒤 아직 접힌 특약의 급부를 둔다
    state.cols[3].forEach(ri => {
      (g.riderBens.get(ri) || []).forEach(bi => {
        if (!ordSeen.has(bi)) { ordSeen.add(bi); orderedPool.push(bi); }
      });
    });
    allBens.forEach(bi => {
      if (!ordSeen.has(bi)) { ordSeen.add(bi); orderedPool.push(bi); }
    });

    const prevShownB = (!resetBenBatch && state.batches[4]) ? state.batches[4].shown : BATCH_SIZE;
    const targetB = Math.max(mustBens.length, prevShownB);
    if (orderedPool.length <= targetB) {
      state.cols[4] = orderedPool;
      delete state.batches[4];
    } else {
      state.cols[4] = orderedPool.slice(0, targetB);
      state.batches[4] = { pool: orderedPool, shown: targetB, label: '급부' };
    }

    const stds = [];
    const stdSeen = new Set();
    state.cols[4].forEach(bi => {
      (g.benStds.get(bi) || []).forEach(({ std }) => {
        if (!stdSeen.has(std)) { stdSeen.add(std); stds.push(std); }
      });
    });
    state.cols[5] = stds;

    const doms = [];
    const domSeen = new Set();
    stds.forEach(si => {
      const dm = g.stdDom.get(si);
      if (dm && !domSeen.has(dm.dom)) { domSeen.add(dm.dom); doms.push(dm.dom); }
    });
    state.cols[6] = doms;
  }

  function initPresetState(presetName, c, keepHistory) {
    const g = ensureGraph();
    if (!keepHistory) {
      undoStack = [];
      trail = [];
    }
    state.preset = presetName;
    state.activeDom = null;
    state.activeStd = null;
    state.selNode = null;
    state.selEdge = null;
    state.focusNode = null;
    state.batches = {};
    state.varLimits = {};
    state.varMores = {};
    state.variantRidersAll = [];
    state.cols = [[], [], [], [], [], [], []];

    if (presetName === 'variant') {
      state.mode = 'hop';
      const baseVar = g.byId.get(c.baseId) ?? (g.N.find(n => n.k === NK['종형'] && n.o === 'EPOST') || {}).i;
      if (baseVar != null) {
        const orgIdx = g.byId.get('ORG:' + g.N[baseVar].o);
        if (orgIdx != null) state.cols[1] = [orgIdx];
        state.cols[2] = [baseVar];
        // 주계약을 먼저, 그 뒤는 graph.json 노드 차례(종형 구성의 새 규칙은 6절에서 정한다)
        const riders = (g.varRiders.get(baseVar) || []).slice().sort((a, b) => {
          const ma = g.N[a].p['담보구분'] === '주계약' ? 0 : 1, mb = g.N[b].p['담보구분'] === '주계약' ? 0 : 1;
          return (ma - mb) || (a - b);
        });
        state.variantRidersAll = riders;
        setColWithBatch(3, riders, '특약');
        syncVariantDownstream(g, baseVar, true);
      }
      recordTrail('종형 구성');
      return;
    }

    if (presetName === 'news') {
      state.mode = 'hop';
      const newsIdxs = g.N.filter(n => n.k === NK['시장 동향'])
        .sort((a, b) => String(b.p['발표일자'] || '').localeCompare(String(a.p['발표일자'] || '')) || a.i - b.i)
        .map(n => n.i);
      setColWithBatch(0, newsIdxs, t('grPresetNews'));
      const orgSet = new Set();
      state.cols[0].forEach(ni => {
        g.adj[ni].forEach(x => { if (x.ek === EK['발표'] && g.N[x.j].k === NK['회사']) orgSet.add(x.j); });
      });
      // 처음에는 기준 종형과 맞붙는 종형만 두고, 판매 종료 종형과 관문 전용 종형은 회사 노드를 펼칠 때만 보인다(1-8)
      const mVars = sceneTypes(g, c);
      mVars.forEach(vi => {
        const oi = g.byId.get('ORG:' + g.N[vi].o);
        if (oi != null) orgSet.add(oi);
      });
      state.cols[1] = Array.from(orgSet);
      state.cols[2] = mVars;
      recordTrail(t('grPresetNews'));
      return;
    }

    // 기본 보는 틀: "담보별 연결"(회사, 맞붙는 종형, 보장 대분류 다섯 + 그룹 엣지)
    state.preset = 'cover';
    state.mode = 'cover-0';
    const vars = sceneTypes(g, c);
    state.cols[1] = orgNodesForVariants(g, vars);
    state.cols[2] = vars;
    state.cols[6] = domainNodesInOrder(g, c);
    recordTrail(t('grPresetCover'));
  }

  function setColWithBatch(colIdx, fullList, label) {
    const uniq = [];
    const seen = new Set();
    fullList.forEach(ni => { if (ni != null && !seen.has(ni)) { seen.add(ni); uniq.push(ni); } });
    if (uniq.length <= BATCH_SIZE) {
      state.cols[colIdx] = uniq;
      delete state.batches[colIdx];
    } else {
      state.cols[colIdx] = uniq.slice(0, BATCH_SIZE);
      state.batches[colIdx] = { pool: uniq, shown: BATCH_SIZE, label: label || '' };
    }
  }

  function appendToColWithBatch(colIdx, addList, label) {
    const cur = state.cols[colIdx].slice();
    const curSet = new Set(cur);
    const fresh = addList.filter(ni => ni != null && !curSet.has(ni));
    if (!fresh.length) return false;
    const merged = cur.concat(fresh);
    if (merged.length <= cur.length + BATCH_SIZE && !state.batches[colIdx] && fresh.length <= BATCH_SIZE) {
      state.cols[colIdx] = merged;
      return true;
    }
    const nextShown = Math.min(merged.length, cur.length + BATCH_SIZE);
    state.cols[colIdx] = merged.slice(0, nextShown);
    if (nextShown < merged.length) {
      state.batches[colIdx] = { pool: merged, shown: nextShown, label: label || '' };
    } else {
      delete state.batches[colIdx];
    }
    return true;
  }

  function releaseBatchMore(colIdx) {
    const g = ensureGraph();
    const b = state.batches[colIdx];
    if (!b) return;
    pushUndo();
    const nextShown = Math.min(b.pool.length, b.shown + BATCH_SIZE);
    state.cols[colIdx] = b.pool.slice(0, nextShown);
    b.shown = nextShown;
    if (b.shown >= b.pool.length) delete state.batches[colIdx];
    if (state.preset === 'variant' && state.cols[2].length === 1) {
      if (colIdx === 3) syncVariantDownstream(g, state.cols[2][0], false);
      else if (colIdx === 4) {
        const stds = [];
        const stdSeen = new Set();
        state.cols[4].forEach(bi => {
          (g.benStds.get(bi) || []).forEach(({ std }) => {
            if (!stdSeen.has(std)) { stdSeen.add(std); stds.push(std); }
          });
        });
        state.cols[5] = stds;
        const doms = [];
        const domSeen = new Set();
        stds.forEach(si => {
          const dm = g.stdDom.get(si);
          if (dm && !domSeen.has(dm.dom)) { domSeen.add(dm.dom); doms.push(dm.dom); }
        });
        state.cols[6] = doms;
      }
    }
    recordTrail(`${b.label || g.kindLabels[COL_KINDS[colIdx]]} +${BATCH_SIZE}`);
    rerenderGraph(true);
  }

  // 선택한 담보 하나에 대해 매핑 엣지를 거꾸로 따라가 그 종형의 특약과 급부를 얻는다(graph.json 노드 차례)
  function stdPathIn(g, vi, si) {
    const riders = new Set();
    const bens = new Set();
    (g.stdBens.get(si) || []).forEach(({ ben }) => {
      (g.benRiders.get(ben) || []).forEach(ri => {
        if ((g.riderVars.get(ri) || []).includes(vi)) { riders.add(ri); bens.add(ben); }
      });
    });
    return { riders: Array.from(riders).sort((a, b) => a - b), bens: Array.from(bens).sort((a, b) => a - b) };
  }

  // 담보 대응 2걸음에서 회사별 특약과 급부 목록을 12개 단위로 구성한다(1-3: 모든 회사의 길이 빠짐없이 이어진다)
  function buildCoverStdColumns(g, stdIdx, vars) {
    const riders = [];
    const riderSeen = new Set();
    const bens = [];
    const benSeen = new Set();
    const more3 = [];
    const more4 = [];

    delete state.batches[3];
    delete state.batches[4];

    vars.forEach(vi => {
      const pathObj = stdPathIn(g, vi, stdIdx);
      if (!pathObj || !pathObj.riders.length) return;

      const orgNm = orgLabel(g.N[vi].o);
      const limR = state.varLimits['r:' + vi] || BATCH_SIZE;
      const shownVarRiders = pathObj.riders.slice(0, limR);
      let lastR = null;
      shownVarRiders.forEach(ri => {
        if (!riderSeen.has(ri)) { riderSeen.add(ri); riders.push(ri); }
        lastR = ri;
      });
      const remR = pathObj.riders.length - shownVarRiders.length;
      if (remR > 0) {
        more3.push({ afterIdx: lastR, key: `r:${vi}`, rem: remR, label: `+${fmt(remR)} 더 (${orgNm})` });
      }

      // 보이는 특약에서 고른 담보로 이어지는 급부는 빠짐없이 함께 보여 길이 끊기지 않게 한다(1-3)
      const validBenSet = new Set(pathObj.bens);
      const shownVarBens = [];
      const shownVarBenSet = new Set();
      shownVarRiders.forEach(ri => {
        (g.riderBens.get(ri) || []).forEach(bi => {
          if (validBenSet.has(bi) && !shownVarBenSet.has(bi)) {
            shownVarBenSet.add(bi);
            shownVarBens.push(bi);
          }
        });
      });
      let lastB = null;
      shownVarBens.forEach(bi => {
        if (!benSeen.has(bi)) { benSeen.add(bi); bens.push(bi); }
        lastB = bi;
      });
      const remB = pathObj.bens.length - shownVarBens.length;
      if (remB > 0) {
        more4.push({ afterIdx: lastB, key: `r:${vi}`, rem: remB, label: `+${fmt(remB)} 더 (${orgNm})` });
      }
    });

    // 비교 종형 바깥에서만 이어진 급부가 있는 담보면 그 급부와 특약을 열에 놓는다
    if (!bens.length) {
      const extR = [];
      const extB = [];
      (g.stdBens.get(stdIdx) || []).forEach(({ ben }) => {
        if (!benSeen.has(ben)) { benSeen.add(ben); extB.push(ben); }
        (g.benRiders.get(ben) || []).forEach(ri => {
          if (!riderSeen.has(ri)) { riderSeen.add(ri); extR.push(ri); }
        });
      });
      setColWithBatch(3, extR, '특약');
      setColWithBatch(4, extB, '급부');
      state.varMores = {};
      return;
    }

    state.cols[3] = riders;
    state.cols[4] = bens;
    state.varMores = { 3: more3, 4: more4 };
  }

  function releaseVarMore(vmoreKey) {
    const g = ensureGraph();
    if (state.activeStd == null) return;
    pushUndo();
    const cur = state.varLimits[vmoreKey] || BATCH_SIZE;
    state.varLimits[vmoreKey] = cur + BATCH_SIZE;
    // 특약 한도를 늘릴 때 급부 한도도 함께 맞춰 새로 열린 특약의 급부가 바로 이어지게 한다
    if (vmoreKey.startsWith('r:')) {
      const bKey = 'b:' + vmoreKey.slice(2);
      state.varLimits[bKey] = Math.max(state.varLimits[bKey] || BATCH_SIZE, state.varLimits[vmoreKey]);
    }
    const vars = state.cols[2].length ? state.cols[2] : sceneTypes(g, App.ctx());
    buildCoverStdColumns(g, state.activeStd, vars);
    recordTrail(`${g.N[state.activeStd].l} +${BATCH_SIZE}`);
    rerenderGraph(true);
  }

  // 담보 대응 1걸음: 보장분야 클릭 -> 표준담보 열 펼치기
  function expandDomainStep(domIdx, c) {
    const g = ensureGraph();
    pushUndo();
    const vars = state.cols[2].length ? state.cols[2] : sceneTypes(g, c);
    state.cols[1] = orgNodesForVariants(g, vars);
    state.cols[2] = vars;
    state.cols[3] = [];
    state.cols[4] = [];
    state.varLimits = {};
    state.varMores = {};
    delete state.batches[3];
    delete state.batches[4];
    delete state.batches[5];
    const stds = (g.domStds.get(domIdx) || []).slice();
    state.cols[5] = stds;
    if (!state.cols[6].length) state.cols[6] = domainNodesInOrder(g, c);
    else if (!state.cols[6].includes(domIdx)) state.cols[6].unshift(domIdx);
    state.mode = 'cover-1';
    state.activeDom = domIdx;
    state.activeStd = null;
    state.selNode = domIdx;
    state.focusNode = domIdx;
    state.selEdge = null;
    recordTrail(g.N[domIdx].l);
  }

  // 담보 대응 2걸음: 표준담보 클릭 -> 회사마다 종형 -> 특약 -> 급부 -> 표준담보 실제 길 펼치기
  function expandStdStep(stdIdx, c) {
    const g = ensureGraph();
    pushUndo();
    const vars = state.cols[2].length ? state.cols[2] : sceneTypes(g, c);
    state.cols[1] = orgNodesForVariants(g, vars);
    state.cols[2] = vars;

    const dm = g.stdDom.get(stdIdx);
    const domIdx = dm ? dm.dom : state.activeDom;
    if (domIdx != null) {
      state.activeDom = domIdx;
      if (!state.cols[6].length) state.cols[6] = domainNodesInOrder(g, c);
      let stdList = state.cols[5].length ? state.cols[5].slice() : (g.domStds.get(domIdx) || []).slice();
      if (!stdList.includes(stdIdx)) stdList.unshift(stdIdx);
      // 아래쪽에 있던 담보를 고른 경우 한 화면에서 모든 회사의 길이 겹침 없이 읽히도록 고른 담보와 관계 담보를 맨 위로 올린다
      const idxInCol = stdList.indexOf(stdIdx);
      if (idxInCol > 6) {
        const relSet = new Set([stdIdx]);
        (g.stdRels.get(stdIdx) || []).forEach(r => relSet.add(r.other));
        const topPart = stdList.filter(x => relSet.has(x));
        const restPart = stdList.filter(x => !relSet.has(x));
        stdList = topPart.concat(restPart);
      }
      state.cols[5] = stdList;
      delete state.batches[5];
    } else if (!state.cols[5].includes(stdIdx)) {
      state.cols[5] = [stdIdx].concat(state.cols[5]);
    }

    state.varLimits = {};
    state.varMores = {};
    buildCoverStdColumns(g, stdIdx, vars);
    state.mode = 'cover-2';
    state.activeStd = stdIdx;
    state.selNode = stdIdx;
    state.focusNode = stdIdx;
    state.selEdge = null;
    recordTrail(g.N[stdIdx].l);
  }

  // 어느 노드에서나 이웃 손잡이를 눌러 옆 열 펼치기
  function neighborGroupsOf(g, nodeIdx) {
    const n = g.N[nodeIdx];
    if (!n) return [];
    const map = new Map(); // key: `${ek}:${targetKind}`
    g.adj[nodeIdx].forEach(x => {
      const nbNode = g.N[x.j];
      if (!nbNode) return;
      const key = `${x.ek}:${nbNode.k}`;
      let grp = map.get(key);
      if (!grp) {
        const srcCol = COL_OF_KIND[n.k];
        const dstCol = COL_OF_KIND[nbNode.k];
        const dir = dstCol < srcCol ? 'left' : dstCol > srcCol ? 'right' : 'same';
        grp = {
          key,
          ek: x.ek,
          ekName: g.ekindLabels[x.ek],
          nbKind: nbNode.k,
          nbKindName: g.kindLabels[nbNode.k],
          dstCol,
          dir,
          nodes: [],
          seen: new Set(),
        };
        map.set(key, grp);
      }
      if (!grp.seen.has(x.j)) {
        grp.seen.add(x.j);
        grp.nodes.push(x.j);
      }
    });
    return Array.from(map.values()).map(grp => {
      const visSet = new Set(state.cols[grp.dstCol] || []);
      const visCount = grp.nodes.filter(j => visSet.has(j)).length;
      return Object.assign(grp, { done: visCount >= grp.nodes.length });
    });
  }

  function expandNeighborGroup(nodeIdx, grpKey) {
    const g = ensureGraph();
    const groups = neighborGroupsOf(g, nodeIdx);
    const hit = groups.find(x => x.key === grpKey);
    if (!hit || !hit.nodes.length) return;
    pushUndo();
    if (state.mode === 'cover-0' || state.mode === 'cover-1' || state.mode === 'cover-2') state.mode = 'hop';
    state.varMores = {};
    let list = hit.nodes.slice();
    if (hit.nbKind === NK['시장 동향']) {
      list.sort((a, b) => String(g.N[b].p['발표일자'] || '').localeCompare(String(g.N[a].p['발표일자'] || '')));
    }
    appendToColWithBatch(hit.dstCol, list, hit.nbKindName);
    state.selNode = nodeIdx;
    state.focusNode = nodeIdx;
    state.selEdge = null;
    recordTrail(`${g.N[nodeIdx].l} (${hit.nbKindName})`);
    rerenderGraph(true);
    App.select('n:' + g.N[nodeIdx].id, { animate: false, focus: false });
  }

  // 기존 열 화면의 보유 구분 클래스: 보유 엣지(보유 구분)와 판정 자료의 표시(5.3)로 정한다
  function ownClass(g, si, c) {
    const sc = sceneOf(g, c || App.ctx());
    const it = sc.info.get(si);
    if (!it) return 'is-unlinked';
    if (it.cls === 'peer') return 'is-miss';
    if (it.cls === 'only' && judgeOf(g, c || App.ctx(), sc).per.get(si).marks.includes('sole')) return 'is-only';
    return '';
  }

  // 지금 화면의 노드들 사이에 그릴 엣지 목록 계산
  function buildEdgeList(g) {
    const visByCol = state.cols.map(arr => new Set(arr));
    const allVis = new Set();
    state.cols.forEach(arr => arr.forEach(ni => allVis.add(ni)));

    const edges = [];
    const hasRidersOrBens = state.cols[3].length > 0 || state.cols[4].length > 0;
    const hasStds = state.cols[5].length > 0;

    // 1. graph.json 실제 엣지 가운데 양 끝 노드가 모두 화면에 있는 것
    g.E.forEach(e => {
      // 기존 열 화면은 edges 의 엣지만 그린다(보유 엣지는 아래 3번에서 그린다)
      if (e.i >= g.nBaseEdges) return;
      if (!allVis.has(e.s) || !allVis.has(e.t)) return;
      const colS = COL_OF_KIND[g.N[e.s].k];
      const colT = COL_OF_KIND[g.N[e.t].k];
      const leftNode = colS <= colT ? e.s : e.t;
      const rightNode = colS <= colT ? e.t : e.s;
      edges.push({
        key: 'e:' + e.i,
        kind: 'real',
        eIdx: e.i,
        ek: e.k,
        ekData: g.ekinds[e.k],
        ekName: g.ekindLabels[e.k],
        leftNode,
        rightNode,
        sNode: e.s,
        tNode: e.t,
        intraCol: colS === colT,
        props: e.p,
        count: null,
      });
    });

    // 2. 처음 상태(표준담보, 특약, 급부가 접혀 있을 때): 종형 -> 보장분야 묶은 엣지(summary.종형[].보장분야별 값 그대로 사용)
    if (!hasStds && !hasRidersOrBens && visByCol[2].size && visByCol[6].size) {
      state.cols[2].forEach(vi => {
        const vNode = g.N[vi];
        const vSum = g.summary && g.summary['종형'] && g.summary['종형'][vNode.id];
        const held = g.heldBy.get(vi);
        state.cols[6].forEach(di => {
          const dNode = g.N[di];
          const sumCnt = vSum && vSum['보장분야별'] ? (vSum['보장분야별'][dNode.id] || 0) : null;
          const stdList = held ? Array.from(held.keys()).filter(si => g.stdDom.get(si) && g.stdDom.get(si).dom === di).sort((a, b) => a - b) : [];
          const cnt = sumCnt != null ? sumCnt : stdList.length;
          if (!cnt) return;
          const props = {
            연결구분: t('grEdgeVarDomType'),
            종형: vNode.l,
            [t('grPropDomain')]: dNode.l,
            표준담보수: cnt,
          };
          edges.push({
            key: `vb:${vi}:${di}`,
            kind: 'var-dom',
            eIdx: null,
            ek: null,
            ekData: '',
            ekName: `${dNode.l} 표준담보 ${cnt}개`,
            leftNode: vi,
            rightNode: di,
            sNode: vi,
            tNode: di,
            intraCol: false,
            props,
            stdList,
            count: cnt,
          });
        });
      });
    }

    // 3. 1걸음 펼침(보장분야를 펼쳐 표준담보는 열렸고 특약과 급부는 접혀 있을 때): 종형 -> 표준담보 보유 연결선(1-12: 화면에서 특약과 급부 수를 세지 않는다)
    if (hasStds && !hasRidersOrBens && visByCol[2].size) {
      state.cols[5].forEach(si => {
        state.cols[2].forEach(vi => {
          const he = g.heldBy.get(vi) && g.heldBy.get(vi).get(si);
          if (!he) return;
          edges.push({
            key: 'e:' + he.i,
            kind: 'var-std',
            eIdx: he.i,
            ek: he.k,
            ekData: g.ekinds[he.k],
            ekName: g.ekindLabels[he.k],
            leftNode: vi,
            rightNode: si,
            sNode: vi,
            tNode: si,
            intraCol: false,
            props: Object.assign({ 안내: t('grEdgeVarStdGuide') }, he.p),
            count: null,
          });
        });
      });
    }

    return edges;
  }

  // 고른 노드에서 닿는 조상(왼쪽 흐름)과 자손(오른쪽 흐름) 및 같은 열 관계 계산
  function computeHighlightSets(edges) {
    if (state.selEdge && renderedEdges.has(state.selEdge)) {
      const ed = renderedEdges.get(state.selEdge);
      return {
        active: true,
        nodes: new Set([ed.leftNode, ed.rightNode]),
        edges: new Set([ed.key]),
      };
    }
    if (state.selNode == null) {
      return { active: false, nodes: new Set(), edges: new Set() };
    }
    const leftAdj = new Map();
    const rightAdj = new Map();
    const sameAdj = new Map();
    const pushM = (m, k, v) => { let a = m.get(k); if (!a) { a = []; m.set(k, a); } a.push(v); };

    edges.forEach(ed => {
      if (ed.intraCol) {
        pushM(sameAdj, ed.leftNode, { n: ed.rightNode, k: ed.key });
        pushM(sameAdj, ed.rightNode, { n: ed.leftNode, k: ed.key });
      } else {
        pushM(rightAdj, ed.leftNode, { n: ed.rightNode, k: ed.key });
        pushM(leftAdj, ed.rightNode, { n: ed.leftNode, k: ed.key });
      }
    });

    const keepNodes = new Set([state.selNode]);
    const keepEdges = new Set();

    // 왼쪽 조상 추적
    const qL = [state.selNode];
    const seenL = new Set([state.selNode]);
    while (qL.length) {
      const cur = qL.shift();
      (leftAdj.get(cur) || []).forEach(({ n, k }) => {
        keepEdges.add(k);
        keepNodes.add(n);
        if (!seenL.has(n)) { seenL.add(n); qL.push(n); }
      });
    }

    // 오른쪽 자손 추적
    const qR = [state.selNode];
    const seenR = new Set([state.selNode]);
    while (qR.length) {
      const cur = qR.shift();
      (rightAdj.get(cur) || []).forEach(({ n, k }) => {
        keepEdges.add(k);
        keepNodes.add(n);
        if (!seenR.has(n)) { seenR.add(n); qR.push(n); }
      });
    }

    // 고른 노드에 직접 맞닿은 같은 열 관계(포함, 통합) 표시
    (sameAdj.get(state.selNode) || []).forEach(({ n, k }) => {
      keepEdges.add(k);
      keepNodes.add(n);
    });

    return { active: true, nodes: keepNodes, edges: keepEdges };
  }

  function benSummaryLine(n) {
    const p = n.p || {};
    const parts = [];
    if (p['기준지급액']) parts.push(String(p['기준지급액']));
    if (p['면책일수'] != null) parts.push(p['면책일수'] > 0 ? `면책 ${p['면책일수']}일` : '면책 0일');
    if (p['감액']) parts.push(p['감액'] === '없음' ? '감액 없음' : `감액 ${p['감액']}`);
    return parts.join(', ');
  }

  function ensureFocusNode() {
    const allVis = new Set();
    let firstVis = null;
    for (let colIdx = 0; colIdx < state.cols.length; colIdx++) {
      for (const ni of state.cols[colIdx]) {
        if (firstVis == null) firstVis = ni;
        allVis.add(ni);
      }
    }
    if (state.selNode != null && allVis.has(state.selNode)) {
      if (state.focusNode == null || !allVis.has(state.focusNode)) state.focusNode = state.selNode;
    } else if (state.focusNode == null || !allVis.has(state.focusNode)) {
      state.focusNode = firstVis;
    }
  }

  function renderNodeCardHTML(g, ni, hl, c) {
    const n = g.N[ni];
    if (!n) return '';
    const isSel = state.selNode === ni && !state.selEdge;
    const isDim = hl.active && !hl.nodes.has(ni);
    const isEpost = n.o === 'EPOST';
    const stdCls = n.k === NK['표준담보'] ? ownClass(g, ni, c) : '';
    const cls = [
      'gr-node',
      `k-${n.k}`,
      isEpost ? 'is-epost' : '',
      stdCls,
      isSel ? 'is-sel' : '',
    ].filter(Boolean).join(' ');

    const p = n.p || {};
    let inner = '';
    let tipSub = g.kindLabels[n.k] + (n.o ? `, ${orgLabel(n.o)}` : '');

    if (n.k === NK['회사']) {
      const vCnt = g.adj[ni].filter(x => x.ek === EK['판매']).length;
      inner = `<span class="gn-t">${esc(n.l)}</span><span class="gn-s num">종형 ${fmt(vCnt)}</span>`;
      tipSub = `기관코드 ${n.o || ''}, 종형 ${fmt(vCnt)}개`;
    } else if (n.k === NK['종형']) {
      const prodNm = p['공시상품명'] || n.l;
      const kindNm = p['종형명'] || p['심사유형'] || '';
      const vSum = g.summary && g.summary['종형'] && g.summary['종형'][n.id];
      const role = vSum && vSum['비교역할'];
      const endDt = vSum && vSum['판매종료일'];
      const roleNote = endDt
        ? `판매종료(${endDt})`
        : App.isGateOnlyRole(role)
          ? t('grRoleNotCoverTpl', { role: App.label(role) })
          : role === '직전개정시연'
            ? t('grRoleNotCoverTpl', { role: App.label(role) })
            : `표준담보 ${fmt(vSum && Array.isArray(vSum['표준담보']) ? vSum['표준담보'].length : 0)}개`;
      inner = `<span class="gn-p">${esc(orgLabel(n.o))} ${esc(prodNm)}</span><span class="gn-t">${esc(kindNm || n.l)}</span>`;
      tipSub = `${orgLabel(n.o)} / ${p['심사유형'] || ''} / ${roleNote}`;
    } else if (n.k === NK['특약']) {
      const sub = [orgLabel(n.o), p['담보구분'], p['갱신여부']].filter(Boolean).join(', ');
      inner = `<span class="gn-t">${esc(n.l)}</span>${sub ? `<span class="gn-s">${esc(sub)}</span>` : ''}`;
      tipSub = sub;
    } else if (n.k === NK['급부']) {
      const sum = benSummaryLine(n);
      inner = `<span class="gn-t">${esc(n.l)}</span><span class="gr-ben-sub num">${esc(sum || orgLabel(n.o))}</span>`;
      tipSub = `${orgLabel(n.o)} / ${sum}`;
    } else if (n.k === NK['표준담보']) {
      const goldMark = stdCls === 'is-only' ? '<i class="gr-gold-mk" aria-hidden="true"></i>' : '';
      inner = `${goldMark}<span class="gn-t">${esc(n.l)}</span>`;
      // 급부 수는 화면에 놓인 종형의 보유 엣지 급부수를 회사별로 적는다(5.5)
      const it = sceneOf(g, c || App.ctx()).info.get(ni);
      const benNote = it ? it.per.map(x => t('grBenCntTpl', { org: orgLabel(x.code), n: fmt(+(x.e.p['급부수'] || 0)) })).join(', ') : '';
      tipSub = [p['보장대분류'], p['급부유형'], benNote].filter(Boolean).join(' / ');
    } else if (n.k === NK['보장 대분류']) {
      const stdCnt = (g.domStds.get(ni) || []).length;
      inner = `<span class="gn-t">${esc(n.l)}</span><span class="gn-cnt num">${fmt(stdCnt)}</span>`;
      tipSub = `표준담보 ${fmt(stdCnt)}개`;
    } else if (n.k === NK['시장 동향']) {
      const dt = p['발표일자'] || '';
      inner = `<span class="gn-ktag num">${esc(dt)}${n.o ? ' ' + esc(orgLabel(n.o)) : ''}</span><span class="gn-t">${esc(n.l)}</span>`;
      tipSub = `${dt} / ${p['분류유형'] || ''} / ${p['매체명'] || ''}`;
    }

    let hopBar = '';
    if (isSel) {
      const groups = neighborGroupsOf(g, ni);
      const leftBtns = groups.filter(x => x.dir === 'left').map(x =>
        `<button type="button" class="gr-hop-btn${x.done ? ' is-done' : ''}" data-gr-expand="${ni}|${esc(x.key)}" aria-label="${esc(`${x.nbKindName} ${x.nodes.length}개 펼치기`)}"><span>&larr; ${esc(x.nbKindName)}</span><span class="num">${fmt(x.nodes.length)}</span></button>`
      ).join('');
      const rightBtns = groups.filter(x => x.dir !== 'left').map(x =>
        `<button type="button" class="gr-hop-btn${x.done ? ' is-done' : ''}" data-gr-expand="${ni}|${esc(x.key)}" aria-label="${esc(`${x.nbKindName} ${x.nodes.length}개 펼치기`)}"><span>${esc(x.dir === 'same' ? x.ekName : x.nbKindName)}</span><span class="num">${fmt(x.nodes.length)}</span><span>${x.dir === 'same' ? '&#8597;' : '&rarr;'}</span></button>`
      ).join('');
      if (leftBtns || rightBtns) {
        hopBar = `<div class="gr-hop-bar"><span class="gr-hop-side">${leftBtns}</span><span class="gr-hop-side">${rightBtns}</span></div>`;
      }
    }

    const tabIdx = state.focusNode === ni ? 0 : -1;
    return `<div class="gr-node-wrap${isDim ? ' is-dim' : ''}" data-gr-wrap="${esc(n.id)}">
      <button type="button" class="${cls}" tabindex="${tabIdx}" data-gr-node="${esc(n.id)}" data-gr-idx="${ni}" data-aim="rect" data-link-pt="1"${isSel ? ' data-sel-anchor="1"' : ''} data-tip-title="${esc(n.l)}" data-tip-sub="${esc(tipSub)}" aria-pressed="${isSel}">
        ${inner}
      </button>
      ${hopBar}
    </div>`;
  }

  function renderVerticalMobileHTML(g, edges, hl, c) {
    // 1000px 미만: 고른 노드(없으면 첫 열들 대표)의 조상과 자손 길을 세로 한 열로 세운다
    const steps = [];
    COL_KINDS.forEach((k, colIdx) => {
      const raw = state.cols[colIdx];
      if (!raw.length) return;
      const filtered = hl.active ? raw.filter(ni => hl.nodes.has(ni)) : raw.slice(0, 6);
      if (!filtered.length) return;
      const isCurCol = state.selNode != null && g.N[state.selNode] && g.N[state.selNode].k === k;
      steps.push(`<div class="gr-vp-step${isCurCol ? ' is-cur' : ''}">
        <div class="gr-vp-hd"><span>${esc(App.short(g.kindLabels[k]))}</span><span class="num">${fmt(filtered.length)}/${fmt(raw.length)}</span></div>
        <div class="gr-vp-nodes">${filtered.map(ni => renderNodeCardHTML(g, ni, { active: false, nodes: new Set() }, c)).join('')}</div>
      </div>`);
    });
    return steps.join('');
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
          ${presets.map(p => `<button type="button" class="gr-preset${state.preset === p.id ? ' is-on' : ''}" role="option" aria-selected="${state.preset === p.id}" data-gr-preset="${p.id}">
            <span class="gp-t">${esc(p.nm)}</span>
            <span class="gp-s">${esc(p.sub)}</span>
          </button>`).join('')}
        </div>
      </div>
      <div class="gr-search-box">
        <label class="gr-sec-k" for="gr-search">${esc(t('grSearchLabel'))}</label>
        <input id="gr-search" class="gr-search-in" type="search" autocomplete="off" placeholder="담보, 특약, 종형, 회사" value="${esc(state.query)}">
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

  function drawOrthogonalEdges(centerEl, g, edges, hl, prevNodeRects, prevEdgeKeys, animate) {
    const canvas = centerEl.querySelector('#gr-canvas');
    const svg = centerEl.querySelector('#gr-edges-svg');
    if (!canvas || !svg) return;

    // 단일 레이아웃 읽기 패스: 캔버스와 모든 가시 노드의 좌표를 한꺼번에 읽는다
    const cRect = canvas.getBoundingClientRect();
    if (cRect.width < 20) return;

    const nodeRectMap = new Map();
    const nodeElMap = new Map();
    canvas.querySelectorAll('.gr-node[data-gr-idx]').forEach(el => {
      const ni = +el.dataset.grIdx;
      nodeElMap.set(ni, el);
      nodeRectMap.set(ni, el.getBoundingClientRect());
    });

    // 채널별 수직 꺾임선 간격 분산 계산
    const byChannel = new Map();
    edges.forEach(ed => {
      const chKey = ed.intraCol ? 'intra' : `${COL_OF_KIND[g.N[ed.leftNode].k]}-${COL_OF_KIND[g.N[ed.rightNode].k]}`;
      let list = byChannel.get(chKey);
      if (!list) { list = []; byChannel.set(chKey, list); }
      list.push(ed);
    });

    renderedEdges = new Map();
    const svgParts = [];
    const newEdgeIds = [];

    edges.forEach(ed => {
      const rL = nodeRectMap.get(ed.leftNode);
      const rR = nodeRectMap.get(ed.rightNode);
      if (!rL || !rR) return;
      renderedEdges.set(ed.key, ed);

      const isDim = hl.active && !hl.edges.has(ed.key);
      const isEsel = state.selEdge === ed.key;
      let d = '';
      let chipX = 0, chipY = 0;

      if (ed.intraCol) {
        // 같은 열(표준담보) 안의 관계(포함, 통합): 열 오른쪽 가장자리의 이중선 꺾쇠
        const list = byChannel.get('intra') || [ed];
        const idx = list.indexOf(ed);
        const x0 = Math.round(Math.max(rL.right, rR.right) - cRect.left);
        const y1 = Math.round((rL.top + rL.height / 2) - cRect.top);
        const y2 = Math.round((rR.top + rR.height / 2) - cRect.top);
        const outX = x0 + 6 + (idx % 3) * 4;
        d = `M${x0} ${y1}H${outX}V${y2}H${x0}`;
        chipX = outX;
        chipY = Math.round((y1 + y2) / 2);
      } else {
        const chKey = `${COL_OF_KIND[g.N[ed.leftNode].k]}-${COL_OF_KIND[g.N[ed.rightNode].k]}`;
        const list = byChannel.get(chKey) || [ed];
        const idx = list.indexOf(ed);
        const x1 = Math.round(rL.right - cRect.left);
        const x2 = Math.round(rR.left - cRect.left);
        if (ed.kind === 'var-dom') {
          const vCount = Math.max(1, state.cols[2].length);
          const vRank = Math.max(0, state.cols[2].indexOf(ed.leftNode));
          const dCount = Math.max(1, state.cols[6].length);
          const dRank = Math.max(0, state.cols[6].indexOf(ed.rightNode));
          const y1 = Math.round((rL.top - cRect.top) + rL.height * ((dRank + 1) / (dCount + 1)));
          const y2 = Math.round((rR.top - cRect.top) + rR.height * ((vRank + 1) / (vCount + 1)));
          const spanX = Math.max(60, x2 - x1);
          const mx = Math.round(x1 + spanX * (0.22 + (idx / Math.max(1, list.length - 1)) * 0.34));
          d = Math.abs(y2 - y1) <= 2 ? `M${x1} ${y1}H${x2}` : `M${x1} ${y1}H${mx}V${y2}H${x2}`;
          chipX = mx;
          chipY = Math.round((y1 + y2) / 2);
          const stepB = Math.min(24, Math.max(10, Math.floor((spanX * 0.42) / Math.max(1, vCount))));
          ed._badgeX = Math.max(x1 + 14, Math.round(x2 - 16 - (vCount - 1 - vRank) * stepB));
          ed._badgeY = y2;
        } else {
          const spread = list.length > 1 ? ((idx / (list.length - 1)) - 0.5) * Math.min(12, list.length * 1.8) : 0;
          const y1 = Math.round((rL.top + rL.height / 2) - cRect.top);
          const y2 = Math.round((rR.top + rR.height / 2) - cRect.top);
          const mx = Math.round((x1 + x2) / 2 + spread);
          d = Math.abs(y2 - y1) <= 2 ? `M${x1} ${y1}H${x2}` : `M${x1} ${y1}H${mx}V${y2}H${x2}`;
          chipX = mx;
          chipY = Math.round((y1 + y2) / 2);
        }
      }

      ed.chipX = chipX;
      ed.chipY = chipY;
      const chipLabel = ed.ek === EK['담보 관계'] && ed.props['관계'] ? `관계(${ed.props['관계']})` : ed.ekName;
      const gCls = ['gr-edge-g', isDim ? 'is-dim' : '', isEsel ? 'is-esel' : ''].filter(Boolean).join(' ');

      let visMarkup = '';
      if (ed.ek === EK['담보 관계']) {
        visMarkup = `<path class="gr-edge-dbl-out" d="${d}" pathLength="1"/><path class="gr-edge-dbl-in" d="${d}"/>`;
      } else {
        const isHuman = ed.ek === EK['매핑'] && (ed.props['검토상태'] === '승인' || ed.props['검토상태'] === '수정');
        const customW = ed.kind === 'var-dom' && ed.count
          ? ` style="stroke-width:${Math.min(6, Math.max(1.5, +(1.2 + ed.count * 0.19).toFixed(2)))}px"`
          : '';
        visMarkup = `<path class="gr-edge-vis ek-${ed.ek}${isHuman ? ' is-human' : ''}" d="${d}" pathLength="1"${customW}/>`;
      }

      let countBadge = '';
      if (ed.kind === 'var-dom' && ed.count != null) {
        const bx = ed._badgeX != null ? ed._badgeX : chipX;
        const by = ed._badgeY != null ? ed._badgeY : chipY;
        const bw = String(ed.count).length >= 2 ? 20 : 16;
        countBadge = `<rect class="gr-edge-cnt-bg" x="${bx - bw / 2}" y="${by - 7}" width="${bw}" height="14"/><text class="gr-edge-cnt-tx" x="${bx}" y="${by}">${ed.count}</text>`;
      }

      svgParts.push(`<g class="${gCls}" data-gr-edge="${esc(ed.key)}" data-chip="${esc(chipLabel)}" data-cx="${chipX}" data-cy="${chipY}"${isEsel ? ' data-sel-anchor="1"' : ''}>
        <path class="gr-edge-hit" d="${d}"/>
        ${visMarkup}
        ${countBadge}
      </g>`);

      if (animate && prevEdgeKeys && !prevEdgeKeys.has(ed.key)) {
        newEdgeIds.push(ed.key);
      }
    });

    svg.innerHTML = svgParts.join('');

    // 쓰기 패스(1-4): 이미 보이던 노드는 수에 한도를 두지 않고 모두 새 자리로 미끄러지고, 새 노드만 나타난다
    if (animate && App.motionOn()) {
      const mScale = App.motionScale();
      let newCount = 0;
      for (const [ni, el] of nodeElMap.entries()) {
        if (typeof el.animate !== 'function') continue;
        const nextR = nodeRectMap.get(ni);
        const prevR = prevNodeRects ? prevNodeRects.get(ni) : null;
        if (prevR && nextR) {
          const dx = prevR.left - nextR.left;
          const dy = prevR.top - nextR.top;
          if (Math.abs(dx) > 1.5 || Math.abs(dy) > 1.5) {
            el.animate([
              { transform: `translate3d(${dx.toFixed(1)}px,${dy.toFixed(1)}px,0)` },
              { transform: 'translate3d(0,0,0)' },
            ], {
              duration: Math.max(110, Math.round(300 * mScale)),
              easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
            });
          }
        } else if (prevNodeRects && prevNodeRects.size > 0) {
          const staggerIdx = Math.min(newCount, 12);
          newCount++;
          el.animate([
            { transform: 'translate3d(0,6px,0)', opacity: 0 },
            { transform: 'translate3d(0,0,0)', opacity: 1 },
          ], {
            duration: Math.max(100, Math.round(240 * mScale)),
            delay: Math.round(staggerIdx * 8 * mScale),
            easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
            fill: 'backwards',
          });
        }
      }

      for (let k = 0; k < newEdgeIds.length; k++) {
        const gEl = svg.querySelector(`[data-gr-edge="${CSS.escape(newEdgeIds[k])}"]`);
        const pEl = gEl && gEl.querySelector('.gr-edge-vis, .gr-edge-dbl-out');
        if (pEl && typeof pEl.animate !== 'function') continue;
        if (pEl) {
          pEl.animate([
            { strokeDasharray: '1 1', strokeDashoffset: 1 },
            { strokeDasharray: '1 1', strokeDashoffset: 0 },
          ], {
            duration: Math.max(100, Math.round(260 * mScale)),
            delay: Math.round(Math.min(12, k) * 6 * mScale),
            easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
            fill: 'backwards',
          });
        }
      }
    }
  }

  function captureCurrentNodeRects(centerEl) {
    const m = new Map();
    if (!centerEl) return m;
    centerEl.querySelectorAll('.gr-node[data-gr-idx]').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width > 2 && r.height > 2) m.set(+el.dataset.grIdx, r);
    });
    return m;
  }

  // 열 머리의 수 표시(1-9: 종형 구성 틀에서 일부만 펼쳐진 열은 N/전체로 표시한다)
  function columnCountText(g, colIdx) {
    const cnt = state.cols[colIdx].length;
    if (state.preset === 'variant' && state.cols[2].length === 1) {
      const vNode = g.N[state.cols[2][0]];
      const vSum = vNode && g.summary && g.summary['종형'] && g.summary['종형'][vNode.id];
      if (vSum) {
        let tot = null;
        if (colIdx === 3) tot = vSum['특약수'];
        else if (colIdx === 4) tot = vSum['급부수'];
        else if (colIdx === 5 && Array.isArray(vSum['표준담보'])) tot = vSum['표준담보'].length;
        else if (colIdx === 6 && vSum['보장분야별']) tot = Object.values(vSum['보장분야별']).filter(v => v > 0).length;
        if (tot != null && cnt < tot) return `${fmt(cnt)}/${fmt(tot)}`;
      }
    }
    const b = state.batches[colIdx];
    if (b && b.pool && cnt < b.pool.length) return `${fmt(cnt)}/${fmt(b.pool.length)}`;
    const vm = state.varMores[colIdx];
    if (vm && vm.length) {
      const hiddenSum = vm.reduce((s, x) => s + x.rem, 0);
      if (hiddenSum > 0) return `${fmt(cnt)}/${fmt(cnt + hiddenSum)}`;
    }
    return fmt(cnt);
  }

  // 종형 구성 틀의 특약 열 본문을 담보구분 묶음 머리별로 그린다(1-9)
  function renderVariantRiderColHTML(g, items, hl, c) {
    const allRiders = state.variantRidersAll.length ? state.variantRidersAll : items;
    const totByGrp = new Map();
    const orderGrps = [];
    allRiders.forEach(ri => {
      const grp = String((g.N[ri] && g.N[ri].p['담보구분']) || '기타');
      if (!totByGrp.has(grp)) { totByGrp.set(grp, 0); orderGrps.push(grp); }
      totByGrp.set(grp, totByGrp.get(grp) + 1);
    });
    const shownByGrp = new Map();
    items.forEach(ri => {
      const grp = String((g.N[ri] && g.N[ri].p['담보구분']) || '기타');
      if (!shownByGrp.has(grp)) shownByGrp.set(grp, []);
      shownByGrp.get(grp).push(ri);
    });

    const parts = [];
    orderGrps.forEach(grp => {
      const tot = totByGrp.get(grp) || 0;
      const list = shownByGrp.get(grp) || [];
      const cntTxt = list.length === tot ? fmt(tot) : `${fmt(list.length)}/${fmt(tot)}`;
      parts.push(`<div class="gr-grp-hd${list.length ? '' : ' is-rest'}"><span>${esc(grp)}</span><span class="num">${cntTxt}</span></div>`);
      list.forEach(ri => { parts.push(renderNodeCardHTML(g, ri, hl, c)); });
    });
    return parts.join('');
  }

  function rerenderGraph(animate, opts = {}) {
    const g = ensureGraph();
    if (!lastCenterEl) return;
    if (edgeDrawRaf) { cancelAnimationFrame(edgeDrawRaf); edgeDrawRaf = 0; }
    hoveredEdgeEl = null;

    const curC = App.ctx();
    ensureFocusNode();

    // 1단계(읽기 전용): 바꾸기 전 노드의 화면 좌표를 먼저 기록한다
    const prevNodeRects = animate ? captureCurrentNodeRects(lastCenterEl) : null;
    const prevEdgeKeys = animate ? new Set(renderedEdges.keys()) : null;

    const edges = buildEdgeList(g);
    // 첫 프레임의 요약 배지(엣지 수)와 조상/자손 계산이 정확한 수를 읽도록 논리 엣지 맵을 먼저 채운다
    renderedEdges = new Map();
    edges.forEach(ed => renderedEdges.set(ed.key, ed));
    const hl = computeHighlightSets(edges);

    const trailHTML = trail.map((tr, idx) => {
      const isLast = idx === trail.length - 1;
      return `${idx > 0 ? '<span class="gr-tr-sep" aria-hidden="true">&gt;</span>' : ''}<button type="button" class="gr-tr-btn${isLast ? ' is-cur' : ''}" data-gr-trail="${idx}">${esc(tr.label)}</button>`;
    }).join('');

    const colHeadsHTML = COL_KINDS.map((k, colIdx) => {
      const cnt = state.cols[colIdx].length;
      const open = cnt > 0 || !!state.batches[colIdx] || !!(state.varMores[colIdx] && state.varMores[colIdx].length);
      return `<div class="gr-col-hd gr-c-${k} ${open ? 'is-open' : 'is-folded'}">
        <span class="gr-col-nm">${esc(App.short(g.kindLabels[k]))}</span>
        <span class="gr-col-cnt num">${columnCountText(g, colIdx)}</span>
      </div>`;
    }).join('');

    const isNarrow = innerWidth < 1000;
    const colsBodyHTML = isNarrow ? '' : COL_KINDS.map((k, colIdx) => {
      const items = state.cols[colIdx];
      const b = state.batches[colIdx];
      const vmList = state.varMores[colIdx] || [];
      const open = items.length > 0 || !!b || vmList.length > 0;

      let cards = '';
      if (colIdx === 3 && state.preset === 'variant' && items.length > 0) {
        cards = renderVariantRiderColHTML(g, items, hl, curC);
      } else if (vmList.length > 0) {
        const byAfter = new Map();
        const tailMores = [];
        vmList.forEach(m => {
          if (m.afterIdx != null && items.includes(m.afterIdx)) {
            let a = byAfter.get(m.afterIdx);
            if (!a) { a = []; byAfter.set(m.afterIdx, a); }
            a.push(m);
          } else {
            tailMores.push(m);
          }
        });
        const chunks = [];
        items.forEach(ni => {
          chunks.push(renderNodeCardHTML(g, ni, hl, curC));
          (byAfter.get(ni) || []).forEach(m => {
            chunks.push(`<button type="button" class="gr-node gr-more" tabindex="-1" data-gr-vmore="${esc(m.key)}" data-aim="rect">${esc(m.label)}</button>`);
          });
        });
        tailMores.forEach(m => {
          chunks.push(`<button type="button" class="gr-node gr-more" tabindex="-1" data-gr-vmore="${esc(m.key)}" data-aim="rect">${esc(m.label)}</button>`);
        });
        cards = chunks.join('');
      } else {
        cards = items.map(ni => renderNodeCardHTML(g, ni, hl, curC)).join('');
      }

      const moreBtn = b && b.shown < b.pool.length
        ? `<button type="button" class="gr-node gr-more" tabindex="-1" data-gr-more="${colIdx}" data-aim="rect">+${fmt(b.pool.length - b.shown)} 더</button>`
        : '';
      return `<div class="gr-col gr-c-${k} ${open ? 'is-open' : 'is-folded'}" data-col-idx="${colIdx}">${cards}${moreBtn}</div>`;
    }).join('');

    const vpathHTML = isNarrow ? renderVerticalMobileHTML(g, edges, hl, curC) : '';

    lastCenterEl.innerHTML = `<div class="gr-wrap" id="gr-stage-root">
      <nav class="gr-trail" aria-label="${esc(t('grTrailLabel'))}"><span class="gr-trail-k">${esc(t('grTrailLabel'))}</span>${trailHTML}</nav>
      ${isNarrow ? `<div class="gr-vpath">${vpathHTML}</div>` : `<div class="gr-col-bar" data-main-axis="1" aria-label="노드 일곱 열 머리">${colHeadsHTML}</div>
      <div class="gr-canvas-scroll" id="gr-scroll">
        <div class="gr-canvas" id="gr-canvas">
          <svg class="gr-edges-svg" id="gr-edges-svg" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"></svg>
          <div class="gr-edge-chip" id="gr-edge-chip" data-aim="rect" hidden></div>
          <div class="gr-cols-grid">${colsBodyHTML}</div>
        </div>
      </div>`}
    </div>`;

    const undoBtn = lastLeftEl && lastLeftEl.querySelector('#gr-btn-undo');
    if (undoBtn) undoBtn.disabled = undoStack.length === 0;
    if (lastLeftEl) {
      lastLeftEl.querySelectorAll('[data-gr-preset]').forEach(btn => {
        const on = btn.dataset.grPreset === state.preset;
        btn.classList.toggle('is-on', on);
        btn.setAttribute('aria-selected', String(on));
      });
    }

    if (opts.deferEdges && !isNarrow) {
      const targetCenter = lastCenterEl;
      edgeDrawRaf = requestAnimationFrame(() => {
        edgeDrawRaf = 0;
        if (App.state.tab !== 'graph' || targetCenter !== lastCenterEl) return;
        drawOrthogonalEdges(targetCenter, g, edges, hl, null, null, false);
        App.updateSelLink(false);
      });
    } else {
      drawOrthogonalEdges(lastCenterEl, g, edges, hl, prevNodeRects, prevEdgeKeys, animate);
      requestAnimationFrame(() => App.updateSelLink(false));
    }
  }

  function restoreGraphNodeFocus(ni) {
    if (ni == null || !lastCenterEl) return;
    state.focusNode = ni;
    const allBtns = lastCenterEl.querySelectorAll('.gr-node[data-gr-idx]');
    let target = null;
    allBtns.forEach(b => {
      const match = +b.dataset.grIdx === ni;
      b.tabIndex = match ? 0 : -1;
      if (match && !target) target = b;
    });
    if (target) {
      try { target.focus({ preventScroll: true }); } catch (e) { /* */ }
    }
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
    const curC = App.ctx();
    const groups = neighborGroupsOf(g, ni);
    const hopBtns = groups.map(grp =>
      `<button type="button" class="btn sm ghost" data-gr-expand="${ni}|${esc(grp.key)}"><span>${esc(grp.nbKindName)} (${esc(grp.ekName)})</span><span class="num">${fmt(grp.nodes.length)}</span>${ui.IC.chevR}</button>`
    ).join(' ');

    // 화면에 이미 나와 있는 연결선(엣지) 바로 고르기 목록
    const attachedEdges = [];
    for (const ed of renderedEdges.values()) {
      if (ed.leftNode === ni || ed.rightNode === ni) attachedEdges.push(ed);
    }
    const edgeListHTML = attachedEdges.length
      ? `<ul class="evl">${attachedEdges.slice(0, 12).map(ed => {
        const otherIdx = ed.leftNode === ni ? ed.rightNode : ed.leftNode;
        return `<li><button type="button" class="cv-lk" data-gr-pick-edge="${esc(ed.key)}">${esc(ed.ekName)}: ${esc(g.N[otherIdx].l)} 속성 보기</button></li>`;
      }).join('')}</ul>`
      : `<p class="note">${esc(t('grEdgeListEmpty'))}</p>`;

    const badges = [ui.tag(g.kindLabels[n.k])];
    if (n.o) badges.push(ui.tag(orgLabel(n.o)));
    if (n.k === NK['표준담보']) {
      const ownCls = ownClass(g, ni, curC);
      if (ownCls === 'is-miss') badges.push(ui.verdict('none'));
      else if (ownCls === 'is-only') badges.push(ui.verdict('only'));
      else if (ownCls === 'is-unlinked') badges.push(ui.tag('비교 종형에 없음'));
    }

    const extraRows = [[t('grPropId'), n.id]];
    let summarySec = '';
    if (n.k === NK['종형'] && g.summary && g.summary['종형'] && g.summary['종형'][n.id]) {
      const vs = g.summary['종형'][n.id];
      if (vs['비교역할']) extraRows.push(['비교역할', App.label(vs['비교역할'])]);
      if (vs['판매종료일']) extraRows.push(['판매종료일', vs['판매종료일']]);
      extraRows.push(['특약 수 (요약)', `${fmt(vs['특약수'] || 0)}개`]);
      extraRows.push(['급부 수 (요약)', `${fmt(vs['급부수'] || 0)}개`]);
      if (App.isGateOnlyRole(vs['비교역할']) || vs['비교역할'] === '직전개정시연' || vs['판매종료일']) {
        summarySec = `<div class="ev-sec"><p class="note">${esc(vs['판매종료일'] ? t('grVarEndNoteTpl', { dt: vs['판매종료일'] }) : t('grVarGateOnlyNote'))}</p></div>`;
      } else {
        const stdLen = Array.isArray(vs['표준담보']) ? vs['표준담보'].length : 0;
        const reasons = vs['미연결사유'] || {};
        const waitN = reasons['대기'] || 0;
        const outN = reasons['대상외'] || 0;
        extraRows.push(['연결 표준담보 수 (요약)', `${fmt(stdLen)}개`]);
        if (vs['미연결급부']) extraRows.push([t('grPropUnmappedBen'), `${fmt(vs['미연결급부'])}개`]);
        const notes = [];
        if (waitN > 0) notes.push(t('grVarWaitNoteTpl', { n: fmt(waitN) }));
        if (outN > 0) notes.push(t('grVarOutNoteTpl', { label: App.label('대상외'), n: fmt(outN) }));
        if (notes.length) summarySec = `<div class="ev-sec"><p class="note">${esc(notes.join(' '))}</p></div>`;
      }
    } else if (n.k === NK['표준담보'] && g.summary && g.summary['표준담보별종형'] && Array.isArray(g.summary['표준담보별종형'][n.id])) {
      extraRows.push(['보유 종형 수 (요약)', `${fmt(g.summary['표준담보별종형'][n.id].length)}개`]);
    }

    const body = `<div class="ev-sec"><h3>노드 속성</h3>${propTableHTML(n.p, extraRows)}${crossTabButtonsHTML(g, n)}</div>
      ${summarySec}
      <div class="ev-sec"><h3>${esc(t('grNeighborsHead'))}</h3>${hopBtns ? `<div style="display:flex;flex-wrap:wrap;gap:6px">${hopBtns}</div>` : `<p class="note">${esc(t('grNeighborsEmpty'))}</p>`}</div>
      <div class="ev-sec lo"><h3>${esc(t('grVisEdgesHeadTpl', { n: fmt(attachedEdges.length) }))}</h3>${edgeListHTML}</div>`;

    return {
      kicker: t('grNodeKickerTpl', { kind: g.kindLabels[n.k] }),
      title: n.l,
      badges,
      body,
    };
  }

  // 선 모양 설명은 엣지 종류의 자료 이름으로 정한다. 모르는 종류는 적지 않는다(4.5)
  function lineStyleLabel(ed) {
    if (ed.kind === 'var-dom') return t('grLineGroupDomTpl', { n: ed.count });
    const nm = ed.ekData;
    if (nm === '담보 관계') return '이중선 (표준담보 사이 포함 또는 통합 관계)';
    if (nm === '발표') return t('grLineDashNews');
    if (nm === '분류') return t('grLineThinDom');
    if (nm === '매핑') {
      const st = ed.props && ed.props['검토상태'];
      if (st === '승인' || st === '수정') return `굵은 실선 (담당자 ${st})`;
      return '실선 (자동확정 매핑)';
    }
    if (nm === '판매' || nm === '포함') return '실선 (판매 또는 포함)';
    if (nm === '보유') return t('grLineHeld');
    return '';
  }

  function buildEdgeEv(g, edgeKey) {
    const ed = renderedEdges.get(edgeKey);
    if (!ed) {
      if (edgeKey.startsWith('e:')) {
        const rawE = g.E[+edgeKey.slice(2)];
        if (!rawE) return null;
        return {
          kicker: t('grEdgeKickerTpl', { kind: g.ekindLabels[rawE.k] }),
          title: `${g.N[rawE.s].l} -> ${g.N[rawE.t].l}`,
          badges: [ui.tag(g.ekindLabels[rawE.k])],
          body: `<div class="ev-sec"><h3>엣지 속성</h3>${propTableHTML(rawE.p)}</div>`,
        };
      }
      return null;
    }
    const nS = g.N[ed.sNode];
    const nT = g.N[ed.tNode];
    const extra = [
      ['관계 종류', ed.ekName],
      ['출발 노드', `${nS.l} (${g.kindLabels[nS.k]})`],
      ['도착 노드', `${nT.l} (${g.kindLabels[nT.k]})`],
      ['선 모양', lineStyleLabel(ed)],
    ].filter(r => r[1]);
    let listSec = '';
    if (ed.stdList && ed.stdList.length) {
      listSec = `<div class="ev-sec"><h3>${esc(t('grGroupStdsHeadTpl', { n: fmt(ed.stdList.length) }))}</h3>
        <div style="display:flex;flex-wrap:wrap;gap:4px">${ed.stdList.map(si => ui.tag(g.N[si].l)).join('')}</div>
        <div style="margin-top:8px">${ui.btn(t('grOpenDomBtnTpl', { dom: nT.l }), { sm: true, main: true, chev: true, attrs: `data-gr-open-dom="${ed.tNode}"` })}</div>
      </div>`;
    }
    const jumpEnds = `<div class="ev-sec lo"><h3>양 끝 노드로 이동</h3>
      <div style="display:flex;flex-wrap:wrap;gap:6px">
        <button type="button" class="btn sm ghost" data-gr-jump-idx="${nS.i}">${esc(nS.l)}</button>
        <button type="button" class="btn sm ghost" data-gr-jump-idx="${nT.i}">${esc(nT.l)}</button>
      </div>
    </div>`;

    return {
      kicker: t('grEdgePropKicker'),
      title: `${nS.l} -> ${nT.l}`,
      badges: [ui.tag(ed.ekName)],
      body: `<div class="ev-sec"><h3>엣지 속성</h3>${propTableHTML(ed.props, extra)}</div>${listSec}${jumpEnds}`,
    };
  }

  function pick(key) {
    const g = ensureGraph();
    if (key.startsWith('n:')) {
      const id = key.slice(2);
      const ni = g.byId.get(id);
      if (ni == null) return null;
      state.selNode = ni;
      state.focusNode = ni;
      state.selEdge = null;
      return buildNodeEv(g, ni);
    }
    if (key.startsWith('edge:')) {
      const ek = key.slice(5);
      state.selEdge = ek;
      return buildEdgeEv(g, ek);
    }
    return null;
  }

  function defaultEv() {
    const g = ensureGraph();
    const visTotal = state.cols.reduce((a, c) => a + c.length, 0);
    return {
      kicker: t('evKickerDefault'),
      title: t('grEvTitle'),
      badges: [ui.tag(`노드 ${fmt(visTotal)}`), ui.tag(`엣지 ${fmt(renderedEdges.size)}`)],
      body: `<div class="ev-sec"><p>${esc(t('grEvBodyTpl'))}</p>
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
    const totalVis = state.cols.reduce((a, arr) => a + arr.length, 0);
    if (!totalVis || sig !== lastScopeSig) {
      lastScopeSig = sig;
      initPresetState(state.preset || 'cover', c, false);
    }
    renderLeftZone(left);
    // 탭 진입 첫 프레임에는 열과 노드를 그리고, 엣지 좌표 읽기는 다음 프레임에 돌린다(1-10)
    rerenderGraph(false, { deferEdges: true });
  }

  function selectAndHandleNode(ni, c, keepFocus) {
    const g = ensureGraph();
    const n = g.N[ni];
    if (!n) return;
    if (state.preset === 'cover' && n.k === NK['보장 대분류']) {
      expandDomainStep(ni, c);
    } else if (state.preset === 'cover' && n.k === NK['표준담보']) {
      expandStdStep(ni, c);
    } else {
      state.selNode = ni;
      state.focusNode = ni;
      state.selEdge = null;
      recordTrail(n.l);
    }
    rerenderGraph(true);
    App.select('n:' + n.id, { animate: true, focus: false });
    if (keepFocus) restoreGraphNodeFocus(ni);
  }

  function jumpToAnyNode(ni, c) {
    const g = ensureGraph();
    const n = g.N[ni];
    if (!n) return;
    const colIdx = COL_OF_KIND[n.k];
    if (n.k === NK['표준담보']) {
      state.preset = 'cover';
      expandStdStep(ni, c);
    } else if (n.k === NK['보장 대분류']) {
      state.preset = 'cover';
      expandDomainStep(ni, c);
    } else if (n.k === NK['시장 동향']) {
      initPresetState('news', c, true);
      if (!state.cols[0].includes(ni)) state.cols[0].unshift(ni);
      state.selNode = ni;
      state.focusNode = ni;
      recordTrail(n.l);
    } else if (n.k === NK['종형']) {
      initPresetState('cover', c, true);
      if (!state.cols[2].includes(ni)) state.cols[2].unshift(ni);
      const oi = n.o ? g.byId.get('ORG:' + n.o) : null;
      if (oi != null && !state.cols[1].includes(oi)) state.cols[1].unshift(oi);
      state.selNode = ni;
      state.focusNode = ni;
      recordTrail(n.l);
    } else {
      pushUndo();
      if (!state.cols[colIdx].includes(ni)) state.cols[colIdx].unshift(ni);
      state.selNode = ni;
      state.focusNode = ni;
      state.selEdge = null;
      recordTrail(n.l);
    }
    if (lastLeftEl) renderLeftZone(lastLeftEl);
    rerenderGraph(true);
    App.select('n:' + n.id, { animate: true, focus: false });
    restoreGraphNodeFocus(ni);
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
        if (trail.length > 1) trail.pop();
        rerenderGraph(true);
        if (state.selEdge) App.select('edge:' + state.selEdge, { animate: false, push: false, focus: false });
        else if (state.selNode != null) App.select('n:' + ensureGraph().N[state.selNode].id, { animate: false, push: false, focus: false });
        else App.unselect({ push: false, restoreFocus: false });
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
      if (state.selNode != null) App.select('n:' + ensureGraph().N[state.selNode].id, { animate: false, push: false, focus: false });
      else App.unselect({ push: false, restoreFocus: false });
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

    const exp = e.target.closest && e.target.closest('[data-gr-expand]');
    if (exp) {
      e.stopPropagation();
      const [niStr, ...rest] = exp.dataset.grExpand.split('|');
      const ni = +niStr;
      expandNeighborGroup(ni, rest.join('|'));
      restoreGraphNodeFocus(ni);
      return;
    }

    const vmr = e.target.closest && e.target.closest('[data-gr-vmore]');
    if (vmr) {
      e.stopPropagation();
      releaseVarMore(vmr.dataset.grVmore);
      return;
    }

    const mr = e.target.closest && e.target.closest('[data-gr-more]');
    if (mr) {
      e.stopPropagation();
      releaseBatchMore(+mr.dataset.grMore);
      return;
    }

    const openDom = e.target.closest && e.target.closest('[data-gr-open-dom]');
    if (openDom) {
      e.stopPropagation();
      const dIdx = +openDom.dataset.grOpenDom;
      expandDomainStep(dIdx, c);
      rerenderGraph(true);
      App.select('n:' + ensureGraph().N[state.selNode].id, { animate: true, focus: false });
      restoreGraphNodeFocus(dIdx);
      return;
    }

    const jmp = e.target.closest && e.target.closest('[data-gr-jump-idx]');
    if (jmp) {
      e.stopPropagation();
      const jIdx = +jmp.dataset.grJumpIdx;
      selectAndHandleNode(jIdx, c, true);
      return;
    }

    const pickEdgeBtn = e.target.closest && e.target.closest('[data-gr-pick-edge]');
    if (pickEdgeBtn) {
      e.stopPropagation();
      const ek = pickEdgeBtn.dataset.grPickEdge;
      state.selEdge = ek;
      rerenderGraph(false);
      App.select('edge:' + ek, { animate: true, focus: false });
      return;
    }

    const eg = e.target.closest && e.target.closest('[data-gr-edge]');
    if (eg) {
      e.stopPropagation();
      const ek = eg.dataset.grEdge;
      state.selEdge = ek;
      rerenderGraph(false);
      App.select('edge:' + ek, { animate: true, focus: false });
      return;
    }

    const nd = e.target.closest && e.target.closest('[data-gr-node]');
    if (nd) {
      e.stopPropagation();
      selectAndHandleNode(+nd.dataset.grIdx, c, true);
    }
  });

  // 무대 노드 화살표 이동(1-5: 상하로 같은 열 안 이동, 좌우로 옆 열의 이어진 노드로 이동)
  function handleGraphArrowKey(e, ndBtn) {
    if (!lastCenterEl) return false;
    const colEl = ndBtn.closest('.gr-col[data-col-idx]');
    const vpathEl = !colEl ? ndBtn.closest('.gr-vpath') : null;

    if (vpathEl) {
      const items = Array.from(vpathEl.querySelectorAll('.gr-node[data-gr-idx]'));
      const idx = items.indexOf(ndBtn);
      if (idx < 0) return false;
      let nextIdx = idx;
      if (e.key === 'ArrowDown' || e.key === 'ArrowRight') nextIdx = Math.min(items.length - 1, idx + 1);
      else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') nextIdx = Math.max(0, idx - 1);
      else if (e.key === 'Home') nextIdx = 0;
      else if (e.key === 'End') nextIdx = items.length - 1;
      if (nextIdx !== idx) {
        e.preventDefault();
        restoreGraphNodeFocus(+items[nextIdx].dataset.grIdx);
        return true;
      }
      return false;
    }

    if (!colEl) return false;
    const curCol = +colEl.dataset.colIdx;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Home' || e.key === 'End') {
      const items = Array.from(colEl.querySelectorAll('.gr-node'));
      const idx = items.indexOf(ndBtn);
      if (idx < 0) return false;
      let nextIdx = idx;
      if (e.key === 'ArrowDown') nextIdx = Math.min(items.length - 1, idx + 1);
      else if (e.key === 'ArrowUp') nextIdx = Math.max(0, idx - 1);
      else if (e.key === 'Home') nextIdx = 0;
      else if (e.key === 'End') nextIdx = items.length - 1;
      if (nextIdx !== idx) {
        e.preventDefault();
        const target = items[nextIdx];
        if (target.dataset.grIdx != null) restoreGraphNodeFocus(+target.dataset.grIdx);
        else { target.focus(); }
        return true;
      }
      return false;
    }

    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      const step = e.key === 'ArrowRight' ? 1 : -1;
      const curNi = ndBtn.dataset.grIdx != null ? +ndBtn.dataset.grIdx : null;
      const curRect = ndBtn.getBoundingClientRect();
      const curMidY = curRect.top + curRect.height / 2;

      for (let c = curCol + step; c >= 0 && c < COL_KINDS.length; c += step) {
        const nextColEl = lastCenterEl.querySelector(`.gr-col[data-col-idx="${c}"]`);
        if (!nextColEl) continue;
        const colNodes = Array.from(nextColEl.querySelectorAll('.gr-node[data-gr-idx]'));
        if (!colNodes.length) continue;

        // 현재 노드와 엣지로 직접 이어진 노드가 있으면 그 가운데 세로 위치가 가장 가까운 노드를 우선 고른다
        const connectedSet = new Set();
        if (curNi != null) {
          for (const ed of renderedEdges.values()) {
            if (ed.leftNode === curNi) connectedSet.add(ed.rightNode);
            else if (ed.rightNode === curNi) connectedSet.add(ed.leftNode);
          }
        }
        const candidates = colNodes.filter(b => connectedSet.has(+b.dataset.grIdx));
        const pool = candidates.length ? candidates : colNodes;
        let bestBtn = pool[0];
        let bestDist = Infinity;
        pool.forEach(b => {
          const r = b.getBoundingClientRect();
          const d = Math.abs((r.top + r.height / 2) - curMidY);
          if (d < bestDist) { bestDist = d; bestBtn = b; }
        });
        e.preventDefault();
        restoreGraphNodeFocus(+bestBtn.dataset.grIdx);
        return true;
      }
    }
    return false;
  }

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

    const ndBtn = e.target.closest && e.target.closest('#gr-stage-root .gr-node');
    if (ndBtn && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) {
      if (handleGraphArrowKey(e, ndBtn)) return;
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
    if (App.state.sel.graph == null && (state.selNode != null || state.selEdge != null)) {
      let prevIdx = state.selNode;
      if (prevIdx == null && state.selEdge && renderedEdges.has(state.selEdge)) {
        prevIdx = renderedEdges.get(state.selEdge).leftNode;
      }
      if (prevIdx == null) prevIdx = state.focusNode;
      state.selNode = null;
      state.selEdge = null;
      if (prevIdx != null) state.focusNode = prevIdx;
      rerenderGraph(false);
      if (prevIdx != null) restoreGraphNodeFocus(prevIdx);
    }
  });
  App.on('resize', () => {
    if (App.state.tab === 'graph' && lastCenterEl) rerenderGraph(false);
  });

  ui.registerLegend('graph', 'grLegendTitle', () => `<dl class="legend">
      <dt>${ui.IC.open}</dt><dd>${esc(t('grLgNode'))}</dd>
      <dt>${ui.IC.arrow}</dt><dd>${esc(t('grLgEdge'))}</dd>
    </dl>`);

  function path() {
    const base = [App.TAB_NAME.graph];
    if (trail.length > 1) base.push(trail[trail.length - 1].label);
    return base;
  }

  function copySummary() {
    const g = ensureGraph();
    const rows = [];
    COL_KINDS.forEach((k, colIdx) => {
      state.cols[colIdx].forEach(ni => {
        const n = g.N[ni];
        rows.push([g.kindLabels[k], orgLabel(n.o) || '공통', n.l, n.id]);
      });
    });
    App.copyRows(t('grCopyCols').split(','), rows, { title: t('grCopyTitle') });
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
