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
    mode: 'net',         // 'net'(담보별 연결) | 'hop'(열 화면)
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
      selStd: state.selStd,
      selGroup: state.selGroup,
      expSlot: state.expSlot,
      filter: state.filter,
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

  function initPresetState(presetName, c, keepHistory, varIdx) {
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
    state.selStd = null;
    state.selGroup = null;
    state.batches = {};
    state.varLimits = {};
    state.varMores = {};
    state.variantRidersAll = [];
    state.cols = [[], [], [], [], [], [], []];

    if (presetName === 'variant') {
      state.mode = 'hop';
      const baseVar = varIdx ?? g.byId.get(c.baseId) ?? (g.N.find(n => n.k === NK['종형'] && n.o === 'EPOST') || {}).i;
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

    // 기본 보기 방식: 담보별 연결(보유 조합 그룹 네트워크, 3절)
    state.preset = 'cover';
    state.mode = 'net';
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

  // 지금 화면의 노드들 사이에 그릴 엣지 목록 계산
  function buildEdgeList(g) {
    const allVis = new Set();
    state.cols.forEach(arr => arr.forEach(ni => allVis.add(ni)));

    const edges = [];

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
    const cls = [
      'gr-node',
      `k-${n.k}`,
      isEpost ? 'is-epost' : '',
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
      inner = `<span class="gn-t">${esc(n.l)}</span>`;
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
          ${presets.map(p => `<button type="button" class="gr-preset${state.preset === p.id ? ' is-on' : ''}" role="option" aria-selected="${state.preset === p.id}" data-gr-preset="${p.id}" data-aim="rect" data-tip-title="${esc(p.nm)}" data-tip-sub="${esc(p.sub)}">
            <span class="gp-t">${esc(p.nm)}</span>
            <span class="gp-s">${esc(p.sub)}</span>
          </button>`).join('')}
        </div>
      </div>
      ${state.preset === 'cover' ? netLeftHTML(ensureGraph(), App.ctx()) : ''}
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
      lastCenterEl.innerHTML = `<div class="gr-wrap" id="gr-stage-root">${trailNavHTML()}<div class="gr-vpath">${netNarrowHTML(g, c)}</div></div>`;
      net.lay = null;
      syncLeftActive();
      return;
    }
    const nav = lastCenterEl.querySelector('#gr-stage-root > .gr-trail');
    if (old && nav) nav.outerHTML = trailNavHTML();
    else lastCenterEl.innerHTML = `<div class="gr-wrap" id="gr-stage-root">${trailNavHTML()}<div class="gr-net" id="gr-net"></div></div>`;
    const host = lastCenterEl.querySelector('#gr-net');
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
      const prev = prevSvg && prevLay && prevLay !== lay && prevLay.W === lay.W && prevLay.H === lay.H && layoutKeyOf(prevLay) !== layoutKeyOf(lay) ? capturePos(prevSvg) : null;
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
      lastLeftEl.querySelectorAll('[data-gr-filter]').forEach(btn => {
        const on = btn.dataset.grFilter === state.filter;
        btn.classList.toggle('is-on', on);
        btn.setAttribute('aria-pressed', String(on));
      });
    }
  }

  function rerenderGraph(animate, opts = {}) {
    const g = ensureGraph();
    if (!lastCenterEl) return;
    if (edgeDrawRaf) { cancelAnimationFrame(edgeDrawRaf); edgeDrawRaf = 0; }
    hoveredEdgeEl = null;

    const curC = App.ctx();
    if (state.preset === 'cover') { rerenderNet(g, curC); return; }
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
      return { slot, vi, id: g.N[vi].id, code: sc.codes[slot], key: slot === 0 ? 'base' : sc.codes[slot], x, y, r, lines, box };
    });
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
        const bw = textW(fmt(grp.members.length), 600) + 12, bh = textLineH() + 2;
        hit = { box: [gg.x - bw / 2, gg.y - gg.R - bh / 2, gg.x + bw / 2, gg.y - gg.R + bh / 2], lines, badge: true };
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
      const sub = [it.dom, grpName].concat(markLines(g, c, lay, si), [benNote, more]).filter(Boolean).join(' / ');
      const wait = jd.marks.includes('wait');
      parts.push(`<g class="gr-n gr-n-${it.cls}${wait ? ' is-wait' : ''}" style="--gr-sh:${(3 / p.r).toFixed(3)}" transform="translate(${f1(p.x)} ${f1(p.y)})" tabindex="-1" role="button" aria-label="${esc(n.l)}" data-gr-fk="n:${esc(n.id)}" data-gr-id="${esc(n.id)}" data-gr-idx="${si}" data-gr-kind="표준담보" data-gr-r="${f1(p.r)}" data-gr-group="${esc(it.key)}" data-gr-cls="${it.cls}" data-gr-mark="${jd.marks.join(' ')}" data-aim="circle" data-tip-title="${esc(n.l)}" data-tip-sub="${esc(sub)}"${chips.length ? ` data-tip-chips="${esc(JSON.stringify(chips.slice(0, 3)))}"` : ''}>`
        + `<circle class="gr-n-c" r="${f1(p.r)}" style="fill:var(--gr-dom-${domIdx(si)})"/>`
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
      const x = a.slot === 0 ? (b[0] + b[2]) / 2 : b[0] + 2;
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
    App.select('n:' + g.N[si].id, { animate: true, focus: false });
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

  // 앵커를 클릭하면 그 종형의 종형 구성 보기로 넘어간다(4.4. 새 종형 구성 보기는 5단계)
  function netOpenVariant(vi) {
    const g = ensureGraph();
    const c = App.ctx();
    pushUndo();
    initPresetState('variant', c, true, vi);
    state.selNode = vi;
    state.focusNode = vi;
    recordTrail(g.N[vi].l);
    if (lastLeftEl) renderLeftZone(lastLeftEl);
    rerenderGraph(true);
    App.select('n:' + g.N[vi].id, { animate: true, focus: false });
    restoreGraphNodeFocus(vi);
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

  // 1,000px 미만: 그룹 카드 세로 목록(지금 단계의 임시 표시, 8.3절은 7단계)
  function netNarrowHTML(g, c) {
    const sc = sceneOf(g, c);
    return sc.groups.map(grp => {
      const lines = groupLines(sc, grp);
      return `<div class="gr-vp-step"><div class="gr-vp-hd"><span>${esc(lines[0])}</span><span>${esc(lines[1])}</span></div>
        <div class="gr-vp-nodes">${grp.members.map(si => `<button type="button" class="gr-node k-std${state.selStd === si ? ' is-sel' : ''}" tabindex="-1" data-gr-node="${esc(g.N[si].id)}" data-gr-idx="${si}" data-aim="rect"><span class="gn-t">${esc(g.N[si].l)}</span></button>`).join('')}</div></div>`;
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
  function legendItemsHTML(g, clickable) {
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
    ].map(([m, sw]) => row(swatchSVG(sw), t(MARK_KEY[m]))).join('');
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

  function netLeftHTML(g, c) {
    const sc = sceneOf(g, c);
    const jd = judgeOf(g, c, sc);
    const fl = FILTERS.map(f => `<button type="button" class="gr-flt${state.filter === 'f:' + f.id ? ' is-on' : ''}" data-gr-filter="f:${f.id}" aria-pressed="${state.filter === 'f:' + f.id}"><span>${esc(App.label(f.cause))}</span><span class="num">${fmt(jd.counts[f.id])}</span></button>`).join('');
    return `<div><span class="gr-sec-k">${esc(t('grFilterHead'))}</span><div class="gr-flts">${fl}</div></div>
      <div class="gr-legend"><span class="gr-sec-k">${esc(t('grLegendHead'))}</span>${legendItemsHTML(g, true)}</div>`;
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

    // 담보별 연결의 앵커(종형)는 열 펼치기와 화면 엣지 목록을 두지 않는다
    const netMode = state.preset === 'cover';
    const body = `<div class="ev-sec"><h3>노드 속성</h3>${propTableHTML(n.p, extraRows)}${crossTabButtonsHTML(g, n)}</div>
      ${summarySec}
      ${netMode ? '' : `<div class="ev-sec"><h3>${esc(t('grNeighborsHead'))}</h3>${hopBtns ? `<div style="display:flex;flex-wrap:wrap;gap:6px">${hopBtns}</div>` : `<p class="note">${esc(t('grNeighborsEmpty'))}</p>`}</div>
      <div class="ev-sec lo"><h3>${esc(t('grVisEdgesHeadTpl', { n: fmt(attachedEdges.length) }))}</h3>${edgeListHTML}</div>`}`;

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
      if (state.preset === 'cover') return buildNetEdgeEv(g, ek);
      return buildEdgeEv(g, ek);
    }
    return null;
  }

  function defaultEv() {
    const g = ensureGraph();
    const isNet = state.preset === 'cover';
    const sc = isNet ? sceneOf(g, App.ctx()) : null;
    const visTotal = isNet ? sc.stds.length + sc.types.length : state.cols.reduce((a, c) => a + c.length, 0);
    const edgeTotal = isNet ? (net.lay ? net.lay.bundles.length : 0) : renderedEdges.size;
    return {
      kicker: t('evKickerDefault'),
      title: t('grEvTitle'),
      badges: [ui.tag(`노드 ${fmt(visTotal)}`), ui.tag(`엣지 ${fmt(edgeTotal)}`)],
      body: `<div class="ev-sec"><p>${esc(isNet ? t('grNetEvBody') : t('grEvBodyTpl'))}</p>
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
    if ((!totalVis && state.preset !== 'cover') || !trail.length || sig !== lastScopeSig) {
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
    // 탭 진입 첫 프레임에는 열과 노드를 그리고, 엣지 좌표 읽기는 다음 프레임에 돌린다(1-10)
    rerenderGraph(false, { deferEdges: true });
  }

  function selectAndHandleNode(ni, c, keepFocus) {
    const g = ensureGraph();
    const n = g.N[ni];
    if (!n) return;
    if (state.preset === 'cover' && n.k === NK['표준담보']) {
      netSelectStd(ni, { rerender: true });
      return;
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
    const colIdx = COL_OF_KIND[n.k];
    if (n.k === NK['표준담보']) {
      if (!sceneOf(g, c).info.has(ni)) { App.toast(t('grNotInScene')); return; }
      if (state.preset !== 'cover') {
        initPresetState('cover', c, true);
        if (lastLeftEl) renderLeftZone(lastLeftEl);
      }
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
    if (n.k === NK['시장 동향'] || n.k === NK['회사']) {
      initPresetState('news', c, true);
      if (!state.cols[colIdx].includes(ni)) state.cols[colIdx].unshift(ni);
    } else {
      const vi = varOfNode(g, ni);
      initPresetState('variant', c, true, vi);
      if (!state.cols[colIdx].includes(ni)) state.cols[colIdx].unshift(ni);
    }
    state.selNode = ni;
    state.focusNode = ni;
    state.selEdge = null;
    recordTrail(n.l);
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

    const exp = e.target.closest && e.target.closest('[data-gr-expand]');
    if (exp) {
      e.stopPropagation();
      const [niStr, ...rest] = exp.dataset.grExpand.split('|');
      const ni = +niStr;
      expandNeighborGroup(ni, rest.join('|'));
      restoreGraphNodeFocus(ni);
      return;
    }

    const mr = e.target.closest && e.target.closest('[data-gr-more]');
    if (mr) {
      e.stopPropagation();
      releaseBatchMore(+mr.dataset.grMore);
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
    if (App.state.tab !== 'graph' || !lastCenterEl) return;
    if (state.preset !== 'cover') { rerenderGraph(false); return; }
    // 브라우저 리사이즈는 150ms 뒤 한 번 다시 계산하고 트랜지션 없이 바꾼다(3.1)
    clearTimeout(net.resizeT);
    net.resizeT = setTimeout(() => { if (App.state.tab === 'graph') rerenderGraph(false); }, 150);
  });

  ui.registerLegend('graph', 'grLegendTitle', () => `<div class="gr-legend is-pop">${legendItemsHTML(ensureGraph(), false)}</div>`);

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
