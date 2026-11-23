/* 탭 6 관계 지도(tab6.js):
   - proto_src/graph/graph.json(#graph-data)을 처음 열 때 읽고, 모든 수는 자료의 목록 길이만 그대로 쓴다.
   - 왼쪽부터 일곱 열(소식, 회사, 종형, 특약, 급부, 표준담보, 보장분야) 고정 배치, 1.5px 직각 꺾은선, 표준담보 오른쪽 관계 이중선 꺾쇠.
   - 처음 상태부터 대화 상자 없이 "담보 대응" 그래프가 열리며, 보장분야 -> 표준담보 -> 특약과 급부의 세 걸음 펼침과 어느 노드에서나 12개 단위 이웃 펼침(+N 더)을 지원한다.
*/
(function () {
  const { ui, txt, t } = App;
  const { esc, fmt } = ui;

  const COL_KINDS = [6, 0, 1, 2, 3, 4, 5]; // 소식, 회사, 종형, 특약, 급부, 표준담보, 보장분야
  const COL_OF_KIND = { 6: 0, 0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6 };
  const BATCH_SIZE = 12;

  let G = null;
  let lastLeftEl = null;
  let lastCenterEl = null;
  let lastScopeSig = '';

  const state = {
    preset: 'cover',     // 'cover' | 'variant' | 'news'
    mode: 'cover-0',     // 'cover-0' | 'cover-1' | 'cover-2' | 'hop'
    activeDom: null,     // node index of 보장분야
    activeStd: null,     // node index of 표준담보
    cols: [[], [], [], [], [], [], []],
    batches: {},         // colIdx -> { pool: number[], shown: number, label: string }
    selNode: null,       // node index
    selEdge: null,       // edge key ('e:12' | 'vb:v:d' | 'vs:v:s')
    query: '',
  };

  let undoStack = [];
  let trail = [];
  let renderedEdges = new Map(); // edgeKey -> descriptor

  function ensureGraph() {
    if (G) return G;
    const scriptEl = document.getElementById('graph-data');
    let raw = { snapshot_at: '', kinds: [], ekinds: [], nodes: [], edges: [], keys: [] };
    if (scriptEl && scriptEl.textContent.trim()) {
      try { raw = JSON.parse(scriptEl.textContent); } catch (e) { console.error(e); }
    }
    const kinds = raw.kinds && raw.kinds.length ? raw.kinds : ['회사', '종형', '특약', '급부', '표준담보', '보장분야', '소식'];
    const ekinds = raw.ekinds && raw.ekinds.length ? raw.ekinds : ['판매', '포함', '해당', '속함', '관계', '일으킴'];
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
    const E = (raw.edges || []).map((a, i) => ({
      i,
      s: a[0],
      t: a[1],
      k: a[2],
      p: dec(a[3]),
    }));

    const byId = new Map();
    const orgNames = {};
    N.forEach(n => {
      byId.set(n.id, n.i);
      if (n.k === 0 && n.o) orgNames[n.o] = n.l;
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

    const pushArr = (map, k, v) => {
      let arr = map.get(k);
      if (!arr) { arr = []; map.set(k, arr); }
      arr.push(v);
    };

    E.forEach(e => {
      adj[e.s].push({ e: e.i, j: e.t, ek: e.k, isOut: true });
      adj[e.t].push({ e: e.i, j: e.s, ek: e.k, isOut: false });
      const ns = N[e.s], nt = N[e.t];
      if (!ns || !nt) return;
      if (e.k === 1 && ns.k === 1 && nt.k === 2) {
        pushArr(varRiders, e.s, e.t);
        pushArr(riderVars, e.t, e.s);
      } else if (e.k === 1 && ns.k === 2 && nt.k === 3) {
        pushArr(riderBens, e.s, e.t);
        pushArr(benRiders, e.t, e.s);
      } else if (e.k === 2 && ns.k === 3 && nt.k === 4) {
        pushArr(benStds, e.s, { std: e.t, e: e.i });
        pushArr(stdBens, e.t, { ben: e.s, e: e.i });
      } else if (e.k === 3 && ns.k === 4 && nt.k === 5) {
        stdDom.set(e.s, { dom: e.t, e: e.i });
        pushArr(domStds, e.t, e.s);
      } else if (e.k === 4 && ns.k === 4 && nt.k === 4) {
        pushArr(stdRels, e.s, { other: e.t, e: e.i, dir: 'out' });
        pushArr(stdRels, e.t, { other: e.s, e: e.i, dir: 'in' });
      }
    });

    // 종형 -> 특약 -> 급부 -> 표준담보 -> 보장분야 실제 연결 목록 사전 색인(값을 새로 판단하지 않고 경로 목록만 모은다)
    const varStdPaths = new Map(); // varIdx -> Map(stdIdx -> { riders: number[], bens: number[] })
    const varDomStds = new Map();  // varIdx -> Map(domIdx -> number[])
    N.forEach(vn => {
      if (vn.k !== 1) return;
      const sMap = new Map();
      const dMap = new Map();
      const rList = varRiders.get(vn.i) || [];
      rList.forEach(ri => {
        const bList = riderBens.get(ri) || [];
        bList.forEach(bi => {
          const stLinks = benStds.get(bi) || [];
          stLinks.forEach(({ std }) => {
            let entry = sMap.get(std);
            if (!entry) { entry = { riders: new Set(), bens: new Set() }; sMap.set(std, entry); }
            entry.riders.add(ri);
            entry.bens.add(bi);
          });
        });
      });
      const finalizedS = new Map();
      for (const [std, sets] of sMap.entries()) {
        finalizedS.set(std, { riders: Array.from(sets.riders), bens: Array.from(sets.bens) });
        const dm = stdDom.get(std);
        if (dm) pushArr(dMap, dm.dom, std);
      }
      varStdPaths.set(vn.i, finalizedS);
      varDomStds.set(vn.i, dMap);
    });

    G = {
      snapshotAt: raw.snapshot_at || '',
      summary: raw.summary || null,
      kinds,
      ekinds,
      N,
      E,
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
      varStdPaths,
      varDomStds,
    };
    return G;
  }

  function orgLabel(code) {
    if (!code) return '';
    return txt.orgShort(code) || (G && G.orgNames[code]) || code;
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
      if (n.k === 5 && !seen.has(n.i)) out.push(n.i);
    });
    return out;
  }

  function matchedVariants(g, c) {
    const allowedPeers = new Set(c.activePeerOrgs || []);
    const outVars = [];
    const seen = new Set();

    // summary.기준종형 과 summary.맞붙는종형 이 있으면 화면에서 다시 고르지 않고 그대로 쓴다
    if (g.summary && g.summary['맞붙는종형']) {
      const bIdx = g.byId.get(c.baseId);
      if (bIdx != null) { outVars.push(bIdx); seen.add(bIdx); }
      const peerIds = g.summary['맞붙는종형'][c.baseId] || c.peerIds || [];
      peerIds.forEach(vid => {
        const ni = g.byId.get(vid);
        if (ni == null || seen.has(ni)) return;
        const org = g.N[ni].o;
        if (c.peerScope === 'all' || allowedPeers.has(org)) {
          outVars.push(ni);
          seen.add(ni);
        }
      });
      if (outVars.length) return outVars;
    }

    const baseSimsa = (c.baseInfo && c.baseInfo['심사']) || '간편심사';
    const directBase = g.byId.get(c.baseId);
    if (directBase != null) {
      outVars.push(directBase);
      seen.add(directBase);
    } else {
      const epFallback = g.N.find(n => n.k === 1 && n.o === 'EPOST' && n.p['심사유형'] === baseSimsa)
        || g.N.find(n => n.k === 1 && n.o === 'EPOST');
      if (epFallback) { outVars.push(epFallback.i); seen.add(epFallback.i); }
    }
    const coveredOrgs = new Set(['EPOST']);
    (c.peerIds || []).forEach(vid => {
      const ni = g.byId.get(vid);
      if (ni != null && !seen.has(ni)) {
        const org = g.N[ni].o;
        if (c.peerScope === 'all' || allowedPeers.has(org)) {
          outVars.push(ni);
          seen.add(ni);
          if (org) coveredOrgs.add(org);
        }
      }
    });
    g.N.forEach(n => {
      if (n.k !== 1 || !n.o || n.o === 'EPOST' || coveredOrgs.has(n.o)) return;
      if (c.peerScope !== 'all' && !allowedPeers.has(n.o)) return;
      if (n.p['심사유형'] === baseSimsa) {
        outVars.push(n.i);
        seen.add(n.i);
        coveredOrgs.add(n.o);
      }
    });
    return outVars;
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
      selNode: state.selNode,
      selEdge: state.selEdge,
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
    state.selNode = o.selNode;
    state.selEdge = o.selEdge;
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
    state.batches = {};
    state.cols = [[], [], [], [], [], [], []];

    if (presetName === 'variant') {
      state.mode = 'hop';
      const baseVar = g.byId.get(c.baseId) ?? (g.N.find(n => n.k === 1 && n.o === 'EPOST') || {}).i;
      if (baseVar != null) {
        const orgIdx = g.byId.get('ORG:' + g.N[baseVar].o);
        if (orgIdx != null) state.cols[1] = [orgIdx];
        state.cols[2] = [baseVar];
        const riders = (g.varRiders.get(baseVar) || []).slice().sort((a, b) => {
          const ga = String(g.N[a].p['담보구분'] || ''), gb = String(g.N[b].p['담보구분'] || '');
          return ga.localeCompare(gb, 'ko') || a - b;
        });
        setColWithBatch(3, riders, '특약');
        // 첫 펼쳐진 특약들의 급부와 표준담보 일부도 함께 이어 보여 준다
        const bens = [];
        const benSeen = new Set();
        state.cols[3].slice(0, 6).forEach(ri => {
          (g.riderBens.get(ri) || []).forEach(bi => {
            if (!benSeen.has(bi)) { benSeen.add(bi); bens.push(bi); }
          });
        });
        setColWithBatch(4, bens, '급부');
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
      recordTrail('종형 구성');
      return;
    }

    if (presetName === 'news') {
      state.mode = 'hop';
      const newsIdxs = g.N.filter(n => n.k === 6)
        .sort((a, b) => String(b.p['발표일자'] || '').localeCompare(String(a.p['발표일자'] || '')) || a.i - b.i)
        .map(n => n.i);
      setColWithBatch(0, newsIdxs, '소식');
      const orgSet = new Set();
      state.cols[0].forEach(ni => {
        g.adj[ni].forEach(x => { if (x.ek === 5 && g.N[x.j].k === 0) orgSet.add(x.j); });
      });
      // 우체국과 주요 비교 회사도 함께 놓아 종형으로 이어지게 한다
      matchedVariants(g, c).forEach(vi => {
        const oi = g.byId.get('ORG:' + g.N[vi].o);
        if (oi != null) orgSet.add(oi);
      });
      state.cols[1] = Array.from(orgSet);
      const varSet = new Set();
      state.cols[1].forEach(oi => {
        g.adj[oi].forEach(x => { if (x.ek === 0 && g.N[x.j].k === 1) varSet.add(x.j); });
      });
      state.cols[2] = Array.from(varSet);
      recordTrail('시장 소식');
      return;
    }

    // 기본 보는 틀: "담보 대응"(회사, 맞붙는 종형, 보장분야 다섯 + 묶은 엣지)
    state.preset = 'cover';
    state.mode = 'cover-0';
    const vars = matchedVariants(g, c);
    state.cols[1] = orgNodesForVariants(g, vars);
    state.cols[2] = vars;
    state.cols[6] = domainNodesInOrder(g, c);
    recordTrail('담보 대응');
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
    const b = state.batches[colIdx];
    if (!b) return;
    pushUndo();
    const nextShown = Math.min(b.pool.length, b.shown + BATCH_SIZE);
    state.cols[colIdx] = b.pool.slice(0, nextShown);
    b.shown = nextShown;
    if (b.shown >= b.pool.length) delete state.batches[colIdx];
    recordTrail(`${b.label || G.kinds[COL_KINDS[colIdx]]} +${BATCH_SIZE}`);
    rerenderGraph(true);
  }

  // 담보 대응 1걸음: 보장분야 클릭 -> 표준담보 열 펼치기
  function expandDomainStep(domIdx, c) {
    const g = ensureGraph();
    pushUndo();
    const vars = state.cols[2].length ? state.cols[2] : matchedVariants(g, c);
    state.cols[1] = orgNodesForVariants(g, vars);
    state.cols[2] = vars;
    state.cols[3] = [];
    state.cols[4] = [];
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
    state.selEdge = null;
    recordTrail(g.N[domIdx].l);
  }

  // 담보 대응 2걸음: 표준담보 클릭 -> 회사마다 종형 -> 특약 -> 급부 -> 표준담보 실제 길 펼치기
  function expandStdStep(stdIdx, c) {
    const g = ensureGraph();
    pushUndo();
    const vars = state.cols[2].length ? state.cols[2] : matchedVariants(g, c);
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

    // 활성 종형 순서대로 특약과 급부를 모아 선 교차를 최소화한다
    const riders = [];
    const riderSeen = new Set();
    const bens = [];
    const benSeen = new Set();

    vars.forEach(vi => {
      const sMap = g.varStdPaths.get(vi);
      const pathObj = sMap && sMap.get(stdIdx);
      if (!pathObj) return;
      pathObj.riders.forEach(ri => {
        if (!riderSeen.has(ri)) { riderSeen.add(ri); riders.push(ri); }
      });
      pathObj.bens.forEach(bi => {
        if (!benSeen.has(bi)) { benSeen.add(bi); bens.push(bi); }
      });
    });

    // 혹시 현재 종형 바깥에서만 이어진 급부가 있으면 그 급부와 특약도 빠뜨리지 않는다
    if (!bens.length) {
      (g.stdBens.get(stdIdx) || []).forEach(({ ben }) => {
        if (!benSeen.has(ben)) { benSeen.add(ben); bens.push(ben); }
        (g.benRiders.get(ben) || []).forEach(ri => {
          if (!riderSeen.has(ri)) { riderSeen.add(ri); riders.push(ri); }
        });
      });
    }

    setColWithBatch(3, riders, '특약');
    setColWithBatch(4, bens, '급부');
    state.mode = 'cover-2';
    state.activeStd = stdIdx;
    state.selNode = stdIdx;
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
          ekName: g.ekinds[x.ek],
          nbKind: nbNode.k,
          nbKindName: g.kinds[nbNode.k],
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
    if (state.mode === 'cover-0' || state.mode === 'cover-1') state.mode = 'hop';
    let list = hit.nodes.slice();
    if (hit.nbKind === 6) {
      list.sort((a, b) => String(g.N[b].p['발표일자'] || '').localeCompare(String(g.N[a].p['발표일자'] || '')));
    }
    appendToColWithBatch(hit.dstCol, list, hit.nbKindName);
    state.selNode = nodeIdx;
    state.selEdge = null;
    recordTrail(`${g.N[nodeIdx].l} (${hit.nbKindName})`);
    rerenderGraph(true);
    App.select('n:' + g.N[nodeIdx].id, { animate: false });
  }

  // 표준담보의 우체국 보유 / 단독 보유 판별(summary.표준담보별종형 우선 사용)
  function stdOwnershipClass(g, stdIdx) {
    const stdNode = g.N[stdIdx];
    if (!stdNode) return '';
    const cmpVars = state.cols[2].filter(vi => {
      const vs = g.summary && g.summary['종형'] && g.summary['종형'][g.N[vi].id];
      return !vs || (!vs['판매종료일'] && vs['비교역할'] !== '관문전용' && vs['비교역할'] !== '직전개정시연');
    });
    const activeSet = new Set(cmpVars.length ? cmpVars : state.cols[2]);
    let holderIdxs = null;
    if (g.summary && g.summary['표준담보별종형'] && Array.isArray(g.summary['표준담보별종형'][stdNode.id])) {
      holderIdxs = g.summary['표준담보별종형'][stdNode.id];
    }
    let epostHas = false;
    let peerHas = false;
    if (holderIdxs) {
      holderIdxs.forEach(vi => {
        if (activeSet.size && !activeSet.has(vi)) return;
        if (g.N[vi] && g.N[vi].o === 'EPOST') epostHas = true;
        else if (g.N[vi] && g.N[vi].o) peerHas = true;
      });
    } else {
      activeSet.forEach(vi => {
        const sMap = g.varStdPaths.get(vi);
        if (sMap && sMap.has(stdIdx)) {
          if (g.N[vi].o === 'EPOST') epostHas = true;
          else peerHas = true;
        }
      });
    }
    if (!epostHas && peerHas) return 'is-miss';
    if (epostHas && !peerHas) return 'is-only';
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
        ekName: g.ekinds[e.k],
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
        const dMap = g.varDomStds.get(vi);
        state.cols[6].forEach(di => {
          const dNode = g.N[di];
          const sumCnt = vSum && vSum['보장분야별'] ? (vSum['보장분야별'][dNode.id] || 0) : null;
          const stdList = (dMap && dMap.get(di)) || [];
          const cnt = sumCnt != null ? sumCnt : stdList.length;
          if (!cnt) return;
          const waitCnt = (vSum && vSum['미연결사유'] && vSum['미연결사유']['대기']) || 0;
          const props = {
            연결구분: '종형별 분야 보유 요약(묶은 엣지)',
            종형: vNode.l,
            보장분야: dNode.l,
            표준담보수: cnt,
          };
          if (waitCnt > 0) props['검토대기안내'] = `이 종형 전체에 매핑 검토 대기 급부 ${waitCnt}건이 있어 담보가 더 이어질 수 있습니다`;
          edges.push({
            key: `vb:${vi}:${di}`,
            kind: 'var-dom',
            eIdx: null,
            ek: 1,
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

    // 3. 1걸음 펼침(보장분야를 펼쳐 표준담보는 열렸고 특약과 급부는 접혀 있을 때): 종형 -> 표준담보 연결선(summary.표준담보별종형 우선)
    if (hasStds && !hasRidersOrBens && visByCol[2].size) {
      state.cols[5].forEach(si => {
        const sNode = g.N[si];
        const holderSet = (g.summary && g.summary['표준담보별종형'] && g.summary['표준담보별종형'][sNode.id])
          ? new Set(g.summary['표준담보별종형'][sNode.id])
          : null;
        state.cols[2].forEach(vi => {
          const sMap = g.varStdPaths.get(vi);
          const pObj = sMap && sMap.get(si);
          const hasLink = holderSet ? holderSet.has(vi) : !!pObj;
          if (!hasLink) return;
          const rCnt = pObj ? pObj.riders.length : 0;
          const bCnt = pObj ? pObj.bens.length : 0;
          edges.push({
            key: `vs:${vi}:${si}`,
            kind: 'var-std',
            eIdx: null,
            ek: 2,
            ekName: rCnt || bCnt ? `특약 ${rCnt}, 급부 ${bCnt}` : '보유 연결',
            leftNode: vi,
            rightNode: si,
            sNode: vi,
            tNode: si,
            intraCol: false,
            props: {
              연결구분: '종형에서 표준담보로 이어지는 경로 요약',
              연결특약수: rCnt,
              연결급부수: bCnt,
            },
            pathObj: pObj,
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

  function renderNodeCardHTML(g, ni, hl) {
    const n = g.N[ni];
    if (!n) return '';
    const isSel = state.selNode === ni && !state.selEdge;
    const isDim = hl.active && !hl.nodes.has(ni);
    const isEpost = n.o === 'EPOST';
    const stdCls = n.k === 4 ? stdOwnershipClass(g, ni) : '';
    const cls = [
      'gr-node',
      `k-${n.k}`,
      isEpost ? 'is-epost' : '',
      stdCls,
      isSel ? 'is-sel' : '',
    ].filter(Boolean).join(' ');

    const p = n.p || {};
    let inner = '';
    let tipSub = g.kinds[n.k] + (n.o ? `, ${orgLabel(n.o)}` : '');

    if (n.k === 0) {
      const vCnt = g.adj[ni].filter(x => x.ek === 0).length;
      inner = `<span class="gn-t">${esc(n.l)}</span><span class="gn-s num">종형 ${fmt(vCnt)}</span>`;
      tipSub = `기관코드 ${n.o || ''}, 종형 ${fmt(vCnt)}개`;
    } else if (n.k === 1) {
      const prodNm = p['공시상품명'] || n.l;
      const kindNm = p['종형명'] || p['심사유형'] || '';
      const vSum = g.summary && g.summary['종형'] && g.summary['종형'][n.id];
      const role = vSum && vSum['비교역할'];
      const endDt = vSum && vSum['판매종료일'];
      const waitCnt = (vSum && vSum['미연결사유'] && vSum['미연결사유']['대기']) || 0;
      const roleNote = endDt
        ? `판매종료(${endDt})`
        : role === '관문전용'
          ? '관문전용(담보 비교 대상 아님)'
          : role === '직전개정시연'
            ? '직전개정시연(담보 비교 대상 아님)'
            : `표준담보 ${fmt(vSum && Array.isArray(vSum['표준담보']) ? vSum['표준담보'].length : 0)}개${waitCnt > 0 ? `, 검토 대기 ${fmt(waitCnt)}건` : ''}`;
      inner = `<span class="gn-p">${esc(orgLabel(n.o))} ${esc(prodNm)}</span><span class="gn-t">${esc(kindNm || n.l)}</span>`;
      tipSub = `${orgLabel(n.o)} / ${p['심사유형'] || ''} / ${roleNote}`;
    } else if (n.k === 2) {
      const sub = [orgLabel(n.o), p['담보구분'], p['갱신여부']].filter(Boolean).join(', ');
      inner = `<span class="gn-t">${esc(n.l)}</span>${sub ? `<span class="gn-s">${esc(sub)}</span>` : ''}`;
      tipSub = sub;
    } else if (n.k === 3) {
      const sum = benSummaryLine(n);
      inner = `<span class="gn-t">${esc(n.l)}</span><span class="gr-ben-sub num">${esc(sum || orgLabel(n.o))}</span>`;
      tipSub = `${orgLabel(n.o)} / ${sum}`;
    } else if (n.k === 4) {
      const benCnt = (g.stdBens.get(ni) || []).length;
      const goldMark = stdCls === 'is-only' ? '<i class="gr-gold-mk" aria-hidden="true"></i>' : '';
      inner = `${goldMark}<span class="gn-t">${esc(n.l)}</span><span class="gn-cnt num">${fmt(benCnt)}</span>`;
      const ownNote = stdCls === 'is-miss' ? '우체국 종형 연결 없음' : stdCls === 'is-only' ? '우체국 단독 연결' : `연결 급부 ${fmt(benCnt)}개`;
      tipSub = `${p['보장대분류'] || ''} / ${p['급부유형'] || ''} / ${ownNote}`;
    } else if (n.k === 5) {
      const stdCnt = (g.domStds.get(ni) || []).length;
      inner = `<span class="gn-t">${esc(n.l)}</span><span class="gn-cnt num">${fmt(stdCnt)}</span>`;
      tipSub = `표준담보 ${fmt(stdCnt)}개`;
    } else if (n.k === 6) {
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

    return `<div class="gr-node-wrap${isDim ? ' is-dim' : ''}" data-gr-wrap="${esc(n.id)}">
      <button type="button" class="${cls}" data-gr-node="${esc(n.id)}" data-gr-idx="${ni}" data-aim="rect" data-link-pt="1"${isSel ? ' data-sel-anchor="1"' : ''} data-tip-title="${esc(n.l)}" data-tip-sub="${esc(tipSub)}" aria-pressed="${isSel}">
        ${inner}
      </button>
      ${hopBar}
    </div>`;
  }

  function renderVerticalMobileHTML(g, edges, hl) {
    // 1000px 미만: 고른 노드(없으면 첫 열들 대표)의 조상과 자손 길을 세로 한 열로 세운다
    const steps = [];
    COL_KINDS.forEach((k, colIdx) => {
      const raw = state.cols[colIdx];
      if (!raw.length) return;
      const filtered = hl.active ? raw.filter(ni => hl.nodes.has(ni)) : raw.slice(0, 6);
      if (!filtered.length) return;
      const isCurCol = state.selNode != null && g.N[state.selNode] && g.N[state.selNode].k === k;
      steps.push(`<div class="gr-vp-step${isCurCol ? ' is-cur' : ''}">
        <div class="gr-vp-hd"><span>${esc(g.kinds[k])}</span><span class="num">${fmt(filtered.length)}/${fmt(raw.length)}</span></div>
        <div class="gr-vp-nodes">${filtered.map(ni => renderNodeCardHTML(g, ni, { active: false, nodes: new Set() })).join('')}</div>
      </div>`);
    });
    return steps.join('');
  }

  function renderLeftZone(leftEl, g) {
    if (!leftEl) return;
    const presets = [
      { id: 'cover', nm: '담보 대응', sub: '회사, 종형, 보장분야에서 담보 길 비교' },
      { id: 'variant', nm: '종형 구성', sub: '기준 종형의 특약과 급부를 담보구분별 탐색' },
      { id: 'news', nm: '시장 소식', sub: '소식에서 회사와 종형으로 이어 보기' },
    ];
    leftEl.innerHTML = `<div class="gr-left-wrap">
      <div>
        <span class="gr-sec-k">보는 틀</span>
        <div class="gr-presets" role="listbox" aria-label="관계 지도 보는 틀">
          ${presets.map(p => `<button type="button" class="gr-preset${state.preset === p.id ? ' is-on' : ''}" role="option" aria-selected="${state.preset === p.id}" data-gr-preset="${p.id}">
            <span class="gp-t">${esc(p.nm)}</span>
            <span class="gp-s">${esc(p.sub)}</span>
          </button>`).join('')}
        </div>
      </div>
      <div class="gr-search-box">
        <label class="gr-sec-k" for="gr-search">이름 찾기</label>
        <input id="gr-search" class="gr-search-in" type="search" autocomplete="off" placeholder="담보, 특약, 종형, 회사" value="${esc(state.query)}">
        <div id="gr-sugg" class="gr-sugg" hidden></div>
      </div>
      <div>
        <span class="gr-sec-k">탐색 이동</span>
        <div class="gr-ctrl-row">
          <button type="button" class="btn sm ghost" id="gr-btn-undo" data-gr-act="undo"${undoStack.length ? '' : ' disabled'}>되돌리기</button>
          <button type="button" class="btn sm ghost" id="gr-btn-reset" data-gr-act="reset">처음으로</button>
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
          ed._badgeX = Math.round(x2 - 16 - (vCount - 1 - vRank) * 24);
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
      const chipLabel = ed.ek === 4 && ed.props['관계'] ? `관계(${ed.props['관계']})` : ed.ekName;
      const gCls = ['gr-edge-g', isDim ? 'is-dim' : '', isEsel ? 'is-esel' : ''].filter(Boolean).join(' ');

      let visMarkup = '';
      if (ed.ek === 4) {
        visMarkup = `<path class="gr-edge-dbl-out" d="${d}" pathLength="1"/><path class="gr-edge-dbl-in" d="${d}"/>`;
      } else {
        const isHuman = ed.ek === 2 && (ed.props['검토상태'] === '승인' || ed.props['검토상태'] === '수정');
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

      svgParts.push(`<g class="${gCls}" data-gr-edge="${esc(ed.key)}" data-chip="${esc(chipLabel)}" data-cx="${chipX}" data-cy="${chipY}">
        <path class="gr-edge-hit" d="${d}"/>
        ${visMarkup}
        ${countBadge}
      </g>`);

      if (animate && prevEdgeKeys && !prevEdgeKeys.has(ed.key)) {
        newEdgeIds.push(ed.key);
      }
    });

    svg.innerHTML = svgParts.join('');

    // 쓰기 패스: 기존 노드는 새 자리로 미끄러지고(FLIP), 새 엣지는 출발에서 도착으로 그어진다
    if (animate && App.motionOn()) {
      const mScale = App.motionScale();
      let animBudget = 0;
      for (const [ni, el] of nodeElMap.entries()) {
        if (animBudget >= 28 || typeof el.animate !== 'function') break;
        const nextR = nodeRectMap.get(ni);
        const prevR = prevNodeRects ? prevNodeRects.get(ni) : null;
        if (prevR && nextR) {
          const dx = prevR.left - nextR.left;
          const dy = prevR.top - nextR.top;
          if (Math.abs(dx) > 1.5 || Math.abs(dy) > 1.5) {
            animBudget++;
            el.animate([
              { transform: `translate3d(${dx.toFixed(1)}px,${dy.toFixed(1)}px,0)` },
              { transform: 'translate3d(0,0,0)' },
            ], {
              duration: Math.max(110, Math.round(300 * mScale)),
              easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
            });
          }
        } else if (prevNodeRects && prevNodeRects.size > 0) {
          animBudget++;
          el.animate([
            { transform: 'translate3d(0,6px,0)', opacity: 0 },
            { transform: 'translate3d(0,0,0)', opacity: 1 },
          ], {
            duration: Math.max(100, Math.round(240 * mScale)),
            delay: Math.round(Math.min(90, animBudget * 8) * mScale),
            easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
            fill: 'backwards',
          });
        }
      }

      const maxEdgeAnim = Math.min(24, newEdgeIds.length);
      for (let k = 0; k < maxEdgeIdsLimit(maxEdgeAnim); k++) {
        const gEl = svg.querySelector(`[data-gr-edge="${CSS.escape(newEdgeIds[k])}"]`);
        const pEl = gEl && gEl.querySelector('.gr-edge-vis, .gr-edge-dbl-out');
        if (pEl && typeof pEl.animate === 'function') {
          pEl.animate([
            { strokeDasharray: '1 1', strokeDashoffset: 1 },
            { strokeDasharray: '1 1', strokeDashoffset: 0 },
          ], {
            duration: Math.max(100, Math.round(260 * mScale)),
            delay: Math.round(Math.min(80, k * 6) * mScale),
            easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
            fill: 'backwards',
          });
        }
      }
    }
  }

  function maxEdgeIdsLimit(n) { return n; }

  function captureCurrentNodeRects(centerEl) {
    const m = new Map();
    if (!centerEl) return m;
    centerEl.querySelectorAll('.gr-node[data-gr-idx]').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width > 2 && r.height > 2) m.set(+el.dataset.grIdx, r);
    });
    return m;
  }

  function rerenderGraph(animate) {
    const g = ensureGraph();
    if (!lastCenterEl) return;

    // 1단계(읽기 전용): 바꾸기 전 노드의 화면 좌표를 먼저 기록한다
    const prevNodeRects = animate ? captureCurrentNodeRects(lastCenterEl) : null;
    const prevEdgeKeys = animate ? new Set(renderedEdges.keys()) : null;

    const edges = buildEdgeList(g);
    const hl = computeHighlightSets(edges);

    const trailHTML = trail.map((tr, idx) => {
      const isLast = idx === trail.length - 1;
      return `${idx > 0 ? '<span class="gr-tr-sep" aria-hidden="true">&gt;</span>' : ''}<button type="button" class="gr-tr-btn${isLast ? ' is-cur' : ''}" data-gr-trail="${idx}">${esc(tr.label)}</button>`;
    }).join('');

    const colHeadsHTML = COL_KINDS.map((k, colIdx) => {
      const cnt = state.cols[colIdx].length;
      const open = cnt > 0 || !!state.batches[colIdx];
      return `<div class="gr-col-hd gr-c-${k} ${open ? 'is-open' : 'is-folded'}">
        <span class="gr-col-nm">${esc(g.kinds[k])}</span>
        <span class="gr-col-cnt num">${fmt(cnt)}</span>
      </div>`;
    }).join('');

    const isNarrow = innerWidth < 1000;
    const colsBodyHTML = isNarrow ? '' : COL_KINDS.map((k, colIdx) => {
      const items = state.cols[colIdx];
      const b = state.batches[colIdx];
      const open = items.length > 0 || !!b;
      const cards = items.map(ni => renderNodeCardHTML(g, ni, hl)).join('');
      const moreBtn = b && b.shown < b.pool.length
        ? `<button type="button" class="gr-node gr-more" data-gr-more="${colIdx}" data-aim="rect">+${fmt(b.pool.length - b.shown)} 더</button>`
        : '';
      return `<div class="gr-col gr-c-${k} ${open ? 'is-open' : 'is-folded'}" data-col-idx="${colIdx}">${cards}${moreBtn}</div>`;
    }).join('');

    const vpathHTML = isNarrow ? renderVerticalMobileHTML(g, edges, hl) : '';

    lastCenterEl.innerHTML = `<div class="gr-wrap" id="gr-stage-root">
      <nav class="gr-trail" aria-label="지나온 길"><span class="gr-trail-k">지나온 길</span>${trailHTML}</nav>
      ${isNarrow ? `<div class="gr-vpath">${vpathHTML}</div>` : `<div class="gr-col-bar" data-main-axis="1" aria-label="노드 일곱 열 머리">${colHeadsHTML}</div>
      <div class="gr-canvas-scroll" id="gr-scroll">
        <div class="gr-canvas" id="gr-canvas">
          <svg class="gr-edges-svg" id="gr-edges-svg" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"></svg>
          <div class="gr-edge-chip" id="gr-edge-chip" hidden></div>
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

    drawOrthogonalEdges(lastCenterEl, g, edges, hl, prevNodeRects, prevEdgeKeys, animate);
    requestAnimationFrame(() => App.updateSelLink(false));
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
    return `<dl class="kv">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd${/^\d/.test(v) ? ' class="num"' : ''}>${esc(v)}</dd>`).join('')}</dl>`;
  }

  function crossTabButtonsHTML(g, n) {
    let stdId = '';
    if (n.k === 4) stdId = n.id;
    else if (n.k === 3) {
      const links = g.benStds.get(n.i) || [];
      if (links.length) stdId = g.N[links[0].std].id;
    }
    const coverFocus = stdId ? ` data-focus="s:${esc(stdId)}"` : '';
    const gateFocus = n.k === 1 ? ` data-focus="tree"` : '';
    return `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">
      ${ui.btn('담보 비교에서 보기', { sm: true, ghost: true, chev: true, attrs: `data-go="cover"${coverFocus}` })}
      ${ui.btn('가입 관문에서 보기', { sm: true, ghost: true, chev: true, attrs: `data-go="gate"${gateFocus}` })}
    </div>`;
  }

  function buildNodeEv(g, ni) {
    const n = g.N[ni];
    if (!n) return null;
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
      : '<p class="note">옆 열 이웃을 펼치면 연결선을 눌러 속성을 볼 수 있습니다.</p>';

    const badges = [ui.tag(g.kinds[n.k])];
    if (n.o) badges.push(ui.tag(orgLabel(n.o)));
    if (n.k === 4) {
      const ownCls = stdOwnershipClass(g, ni);
      if (ownCls === 'is-miss') badges.push(ui.verdict('none'));
      else if (ownCls === 'is-only') badges.push(ui.verdict('only'));
    }

    const extraRows = [['식별자', n.id]];
    let summarySec = '';
    if (n.k === 1 && g.summary && g.summary['종형'] && g.summary['종형'][n.id]) {
      const vs = g.summary['종형'][n.id];
      if (vs['비교역할']) extraRows.push(['비교역할', vs['비교역할']]);
      if (vs['판매종료일']) extraRows.push(['판매종료일', vs['판매종료일']]);
      extraRows.push(['특약 수 (요약)', `${fmt(vs['특약수'] || 0)}개`]);
      extraRows.push(['급부 수 (요약)', `${fmt(vs['급부수'] || 0)}개`]);
      if (vs['비교역할'] === '관문전용' || vs['비교역할'] === '직전개정시연' || vs['판매종료일']) {
        summarySec = `<div class="ev-sec"><p class="note">${vs['판매종료일'] ? `판매를 마친 직전 개정 종형(${esc(vs['판매종료일'])} 종료)이라 현재 담보 비교 대상이 아닙니다.` : '가입 관문만 수집한 종형이라 담보 비교 대상이 아닙니다.'}</p></div>`;
      } else {
        const stdLen = Array.isArray(vs['표준담보']) ? vs['표준담보'].length : 0;
        const reasons = vs['미연결사유'] || {};
        const waitN = reasons['대기'] || 0;
        const outN = reasons['대상외'] || 0;
        extraRows.push(['연결 표준담보 수 (요약)', `${fmt(stdLen)}개`]);
        if (vs['미연결급부']) extraRows.push(['미연결 급부 수', `${fmt(vs['미연결급부'])}개`]);
        const notes = [];
        if (waitN > 0) notes.push(`매핑 검토 대기 급부 ${fmt(waitN)}건이 있어 담당자 검토 뒤 표준담보가 더 이어질 수 있습니다.`);
        if (outN > 0) notes.push(`대상외 급부 ${fmt(outN)}건은 표준담보 사전 범위 밖 급부이며 빠진 담보가 아닙니다.`);
        if (notes.length) summarySec = `<div class="ev-sec"><p class="note">${esc(notes.join(' '))}</p></div>`;
      }
    } else if (n.k === 4 && g.summary && g.summary['표준담보별종형'] && Array.isArray(g.summary['표준담보별종형'][n.id])) {
      extraRows.push(['보유 종형 수 (요약)', `${fmt(g.summary['표준담보별종형'][n.id].length)}개`]);
    }

    const body = `<div class="ev-sec"><h3>노드 속성</h3>${propTableHTML(n.p, extraRows)}${crossTabButtonsHTML(g, n)}</div>
      ${summarySec}
      <div class="ev-sec"><h3>이웃 펼치기 (자료 목록 수)</h3>${hopBtns ? `<div style="display:flex;flex-wrap:wrap;gap:6px">${hopBtns}</div>` : '<p class="note">연결 가능한 이웃이 없습니다.</p>'}</div>
      <div class="ev-sec lo"><h3>화면에 이어진 엣지 (${fmt(attachedEdges.length)})</h3>${edgeListHTML}</div>`;

    return {
      kicker: `관계 지도 노드, ${g.kinds[n.k]}`,
      title: n.l,
      badges,
      body,
    };
  }

  function lineStyleLabel(ed) {
    if (ed.ek === 4) return '이중선 (표준담보 사이 포함 또는 통합 관계)';
    if (ed.ek === 5) return '점선 (회사가 일으킨 시장 소식)';
    if (ed.ek === 3) return '가는 실선 (표준담보가 보장분야에 속함)';
    if (ed.ek === 2) {
      const st = ed.props && ed.props['검토상태'];
      if (st === '승인' || st === '수정') return `굵은 실선 (담당자 ${st})`;
      return '실선 (자동확정 매핑)';
    }
    if (ed.kind === 'var-dom') return `묶은 실선 (표준담보 ${ed.count}개 비례 굵기)`;
    return '실선 (판매 또는 포함)';
  }

  function buildEdgeEv(g, edgeKey) {
    const ed = renderedEdges.get(edgeKey);
    if (!ed) {
      if (edgeKey.startsWith('e:')) {
        const rawE = g.E[+edgeKey.slice(2)];
        if (!rawE) return null;
        return {
          kicker: `관계 지도 엣지, ${g.ekinds[rawE.k]}`,
          title: `${g.N[rawE.s].l} -> ${g.N[rawE.t].l}`,
          badges: [ui.tag(g.ekinds[rawE.k])],
          body: `<div class="ev-sec"><h3>엣지 속성</h3>${propTableHTML(rawE.p)}</div>`,
        };
      }
      return null;
    }
    const nS = g.N[ed.sNode];
    const nT = g.N[ed.tNode];
    const extra = [
      ['관계 종류', ed.ekName],
      ['출발 노드', `${nS.l} (${g.kinds[nS.k]})`],
      ['도착 노드', `${nT.l} (${g.kinds[nT.k]})`],
      ['선 모양', lineStyleLabel(ed)],
    ];
    let listSec = '';
    if (ed.stdList && ed.stdList.length) {
      listSec = `<div class="ev-sec"><h3>묶인 표준담보 (${fmt(ed.stdList.length)}개)</h3>
        <div style="display:flex;flex-wrap:wrap;gap:4px">${ed.stdList.map(si => ui.tag(g.N[si].l)).join('')}</div>
        <div style="margin-top:8px">${ui.btn(`${nT.l} 분야 펼치기`, { sm: true, main: true, chev: true, attrs: `data-gr-open-dom="${ed.tNode}"` })}</div>
      </div>`;
    }
    const jumpEnds = `<div class="ev-sec lo"><h3>양 끝 노드로 이동</h3>
      <div style="display:flex;flex-wrap:wrap;gap:6px">
        <button type="button" class="btn sm ghost" data-gr-jump-idx="${nS.i}">${esc(nS.l)}</button>
        <button type="button" class="btn sm ghost" data-gr-jump-idx="${nT.i}">${esc(nT.l)}</button>
      </div>
    </div>`;

    return {
      kicker: '관계 지도 엣지 속성',
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
    const g = ensureGraph();
    lastLeftEl = left;
    lastCenterEl = center;
    const sig = scopeSig(c);
    const totalVis = state.cols.reduce((a, arr) => a + arr.length, 0);
    if (!totalVis || sig !== lastScopeSig) {
      lastScopeSig = sig;
      initPresetState(state.preset || 'cover', c, false);
    }
    renderLeftZone(left, g);
    rerenderGraph(false);
  }

  function selectAndHandleNode(ni, c) {
    const g = ensureGraph();
    const n = g.N[ni];
    if (!n) return;
    if (state.preset === 'cover' && n.k === 5) {
      expandDomainStep(ni, c);
      rerenderGraph(true);
      App.select('n:' + n.id, { animate: true });
      return;
    }
    if (state.preset === 'cover' && n.k === 4) {
      expandStdStep(ni, c);
      rerenderGraph(true);
      App.select('n:' + n.id, { animate: true });
      return;
    }
    state.selNode = ni;
    state.selEdge = null;
    recordTrail(n.l);
    rerenderGraph(true);
    App.select('n:' + n.id, { animate: true });
  }

  function jumpToAnyNode(ni, c) {
    const g = ensureGraph();
    const n = g.N[ni];
    if (!n) return;
    const colIdx = COL_OF_KIND[n.k];
    if (n.k === 4) {
      state.preset = 'cover';
      expandStdStep(ni, c);
    } else if (n.k === 5) {
      state.preset = 'cover';
      expandDomainStep(ni, c);
    } else if (n.k === 6) {
      initPresetState('news', c, true);
      if (!state.cols[0].includes(ni)) state.cols[0].unshift(ni);
      state.selNode = ni;
      recordTrail(n.l);
    } else if (n.k === 1) {
      initPresetState('cover', c, true);
      if (!state.cols[2].includes(ni)) state.cols[2].unshift(ni);
      const oi = n.o ? g.byId.get('ORG:' + n.o) : null;
      if (oi != null && !state.cols[1].includes(oi)) state.cols[1].unshift(oi);
      state.selNode = ni;
      recordTrail(n.l);
    } else {
      pushUndo();
      if (!state.cols[colIdx].includes(ni)) state.cols[colIdx].unshift(ni);
      state.selNode = ni;
      state.selEdge = null;
      recordTrail(n.l);
    }
    if (lastLeftEl) renderLeftZone(lastLeftEl, g);
    rerenderGraph(true);
    App.select('n:' + n.id, { animate: true });
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
      ni = g.byId.get(q) ?? (g.N.find(n => n.k === 6 && (n.o === q || n.l.includes(q))) || {}).i;
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
    const pri = { 4: 0, 1: 1, 2: 2, 0: 3, 5: 4, 6: 5, 3: 6 };
    const hits = g.N.filter(n => n.l.toLowerCase().includes(q) || n.id.toLowerCase().includes(q))
      .sort((a, b) => (pri[a.k] ?? 9) - (pri[b.k] ?? 9) || a.l.length - b.l.length)
      .slice(0, 12);
    if (!hits.length) {
      sugg.innerHTML = '<div class="gr-sugg-empty">맞는 이름의 노드가 없습니다.</div>';
      sugg.hidden = false;
      return;
    }
    sugg.innerHTML = hits.map(n => `<button type="button" class="gr-sugg-it" data-gr-sugg="${n.i}">
      <span class="gr-sugg-k">${esc(g.kinds[n.k])}</span>
      <span class="gr-sugg-n">${esc(n.l)}</span>
      ${n.o ? `<span class="gr-sugg-o">${esc(orgLabel(n.o))}</span>` : ''}
    </button>`).join('');
    sugg.hidden = false;
  }

  // ---------- 위임 이벤트(클릭, 검색, 엣지 가리킴 칩, 키보드 되돌리기) ----------
  document.addEventListener('input', e => {
    if (App.state.tab !== 'graph') return;
    if (e.target && e.target.id === 'gr-search') {
      updateSearchSugg(e.target.value);
    }
  });

  document.addEventListener('pointerover', e => {
    if (App.state.tab !== 'graph' || !lastCenterEl) return;
    const eg = e.target.closest && e.target.closest('[data-gr-edge]');
    const chip = lastCenterEl.querySelector('#gr-edge-chip');
    if (!chip) return;
    if (eg) {
      chip.textContent = eg.dataset.chip || '';
      chip.style.setProperty('--ec-x', (eg.dataset.cx || 0) + 'px');
      chip.style.setProperty('--ec-y', (eg.dataset.cy || 0) + 'px');
      chip.hidden = false;
    } else if (!chip.hidden) {
      chip.hidden = true;
    }
  });

  document.addEventListener('click', e => {
    if (App.state.tab !== 'graph') return;
    const c = App.ctx();

    const pr = e.target.closest && e.target.closest('[data-gr-preset]');
    if (pr) {
      e.stopPropagation();
      initPresetState(pr.dataset.grPreset, c, false);
      App.unselect({ push: false, restoreFocus: false });
      if (lastLeftEl) renderLeftZone(lastLeftEl, ensureGraph());
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
        if (state.selEdge) App.select('edge:' + state.selEdge, { animate: false, push: false });
        else if (state.selNode != null) App.select('n:' + ensureGraph().N[state.selNode].id, { animate: false, push: false });
        else App.unselect({ push: false, restoreFocus: false });
      } else if (act.dataset.grAct === 'reset') {
        initPresetState(state.preset, c, false);
        App.unselect({ push: false, restoreFocus: false });
        if (lastLeftEl) renderLeftZone(lastLeftEl, ensureGraph());
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
      if (state.selNode != null) App.select('n:' + ensureGraph().N[state.selNode].id, { animate: false, push: false });
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
      expandNeighborGroup(+niStr, rest.join('|'));
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
      expandDomainStep(+openDom.dataset.grOpenDom, c);
      rerenderGraph(true);
      App.select('n:' + ensureGraph().N[state.selNode].id, { animate: true });
      return;
    }

    const jmp = e.target.closest && e.target.closest('[data-gr-jump-idx]');
    if (jmp) {
      e.stopPropagation();
      selectAndHandleNode(+jmp.dataset.grJumpIdx, c);
      return;
    }

    const pickEdgeBtn = e.target.closest && e.target.closest('[data-gr-pick-edge]');
    if (pickEdgeBtn) {
      e.stopPropagation();
      const ek = pickEdgeBtn.dataset.grPickEdge;
      state.selEdge = ek;
      rerenderGraph(false);
      App.select('edge:' + ek, { animate: true });
      return;
    }

    const eg = e.target.closest && e.target.closest('[data-gr-edge]');
    if (eg) {
      e.stopPropagation();
      const ek = eg.dataset.grEdge;
      state.selEdge = ek;
      rerenderGraph(false);
      App.select('edge:' + ek, { animate: true });
      return;
    }

    const nd = e.target.closest && e.target.closest('[data-gr-node]');
    if (nd) {
      e.stopPropagation();
      selectAndHandleNode(+nd.dataset.grIdx, c);
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
    if ((e.key === 'z' || e.key === 'Z') && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const undoBtn = lastLeftEl && lastLeftEl.querySelector('#gr-btn-undo');
      if (undoBtn && !undoBtn.disabled) undoBtn.click();
    }
  });

  App.on('select', (tabId) => {
    if (tabId !== 'graph') return;
    if (App.state.sel.graph == null && (state.selNode != null || state.selEdge != null)) {
      state.selNode = null;
      state.selEdge = null;
      rerenderGraph(false);
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
        rows.push([g.kinds[k], orgLabel(n.o) || '공통', n.l, n.id]);
      });
    });
    App.copyRows(['열 종류', '회사', '이름', '식별자'], rows, { title: '관계 지도 현재 열람 노드' });
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
