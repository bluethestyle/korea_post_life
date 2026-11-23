/* 시안 4 첫 화면(전체 요약: 가로 기준축 위 다섯 기둥 묶음 + 아래 결론 한 문장)과 다섯째 탭(관계 지도).
   모든 화면 문구는 core.js 의 COPY 표(App.t)에서 읽고, 수치는 sales.json 과 cover.json 에서 읽는다. */
(function () {
  'use strict';
  const { ui, txt } = App;
  const { esc, fmt } = ui;
  const S = App.S;
  const t = (k, v) => App.t(k, v);

  const ROW_NAME_KEY = { '가': 'briefRowGa', '나': 'briefRowNa', '다': 'briefRowDa', '라': 'briefRowRa', '마': 'briefRowMa' };
  const ROW_GO = {
    '가': { tab: 'market', grp: '' },
    '나': { tab: 'market', grp: 'rev' },
    '다': { tab: 'gate', grp: '' },
    '라': { tab: 'cover', grp: '' },
    '마': { tab: 'insight', grp: '' },
  };
  const rowName = b => (ROW_NAME_KEY[b['줄']] ? t(ROW_NAME_KEY[b['줄']]) : '');
  const lineOf = (base, k) => ((base && base['브리핑']) || []).find(x => x['줄'] === k) || null;
  const refCondText = () => `${S['기준조건']['나이']}${t('condAgeUnit')} ${txt.sexText(S['기준조건']['성별'])}, ${txt.sinceText(S['기준조건']['이력'])}`;

  function limitLine(c) {
    const L = c.limit;
    if (!L) return null;
    const who = `${c.st.age}${t('condAgeUnit')} ${txt.sexText(c.st.sex)}`;
    const kind = txt.vkind(c.baseId);
    if (!L.hit) return t('briefLimitOutTpl', { who, kind, lo: L.lo, hi: L.hi });
    const extra = `${L.hit.pend ? t('briefLimitPend') : ''}${L.table['성별같음'] ? t('briefLimitSameSex') : ''}`;
    return t('briefLimitInTpl', { who, max: fmt(L.hit.max), lo: L.hit.lo, hi: L.hit.hi, extra });
  }

  ui.registerLegend('brief', 'homeLegendTitle', () => `<dl class="legend">
      <dt><i class="cq m-only" aria-hidden="true"></i></dt><dd>${esc(t('homeLgGold'))}</dd>
      <dt><i class="cq m-ours" aria-hidden="true"></i></dt><dd>${esc(t('homeLgWorse'))}</dd>
      <dt><i class="cq m-both" aria-hidden="true"></i></dt><dd>${esc(t('homeLgNeutral'))}</dd>
      <dt>${ui.IC.open}</dt><dd>${esc(t('homeLgOutline'))}</dd>
      <dt>${ui.IC.hatch}</dt><dd>${esc(t('homeLgEmpty'))}</dd>
      <dt>${ui.IC.only}</dt><dd>${esc(t('homeLgRed'))}</dd>
      <dt>${ui.flagText(t('flagShort'))}</dt><dd>${esc(t('lgFlag'))}</dd>
    </dl>`);

  // 1. 고객군과 시장 축소 기둥 24개(이력과 나이 네 무리 x 여섯 마디, 폭 8px, 사이 4px, 최대 120px, 최소 6px)
  function marketPillarsSVG(c) {
    const m = App.mapOf(c.st.renewal);
    const hospIdx = (m['행'] || []).map((r, i) => ({ r, i })).filter(x => x.r['종류'] === '입원');
    const surgIdx = (m['행'] || []).map((r, i) => ({ r, i })).filter(x => x.r['종류'] === '수술만');
    const cols = m['열'] || [];
    const groups = [];
    [hospIdx, surgIdx].forEach(periods => {
      cols.forEach((_, ci) => {
        groups.push(periods.map(p => (m['칸'][p.i] || [])[ci] || null));
      });
    });
    const pw = 8, gap = 4, gGap = 10, H = 124;
    let x = 0;
    const rects = [];
    const ticks = [];
    groups.forEach((cells, gi) => {
      if (gi > 0) x += gGap - gap;
      cells.forEach((cell, ci) => {
        const cc = c.cellCounts(cell);
        let h = 6;
        if (cc.total > 0 && cc.openAny > 0) h = Math.max(10, Math.round((cc.openAny / cc.total) * 120));
        else if (cc.state === 'only') h = 22;
        const y = H - h;
        let cls = 'pil-empty';
        let extra = '';
        if (cc.state === 'worse') cls = 'pil-fill-worse';
        else if (cc.state === 'only') {
          cls = 'pil-fill-gold';
          extra = `<line x1="${x + 1}" y1="${y + 3}" x2="${x + pw - 1}" y2="${y + 3}" stroke="var(--gold-edge)" stroke-width="1.2"/>`;
        } else if (cc.state === 'both') cls = 'pil-fill-neutral';
        else if (cc.state === 'unknown') cls = 'pil-hatch';
        rects.push(`<rect class="${cls}" x="${x + 0.5}" y="${y + 0.5}" width="${pw - 1}" height="${Math.max(5, h - 1)}"/>${extra}`);
        if (ci === 0 || ci === cells.length - 1) {
          ticks.push(`<line x1="${x + pw / 2}" y1="${H}" x2="${x + pw / 2}" y2="${H + 6}" stroke="var(--axis)" stroke-width="1"/>`);
        }
        x += pw + gap;
      });
    });
    const W = Math.max(40, x - gap);
    return `<svg class="hm-svg" width="${W}" height="${H + 6}" viewBox="0 0 ${W} ${H + 6}" aria-hidden="true" focusable="false">${rects.join('')}${ticks.join('')}</svg>`;
  }

  // 2. 가입 관문 축소 기둥(고지 유형마다 기둥 하나, 폭 20px, 사이 10px, 윤곽=상대 수, 채움=끝까지 통과한 수)
  function gatePillarsSVG(c) {
    const m = App.mapOf(c.st.renewal);
    const rows = c.gateFlowRows(m, c.seg ? c.seg.cell : null);
    if (!rows.length) return '';
    const maxP = Math.max(1, ...rows.map(r => r.total));
    const pw = 20, gap = 10, H = 124;
    const W = rows.length * pw + (rows.length - 1) * gap;
    const els = [];
    rows.forEach((r, idx) => {
      const x = idx * (pw + gap);
      const outH = r.total > 0 ? Math.max(14, Math.round((r.total / maxP) * 120)) : 8;
      const fillH = r.total > 0 && r.finalPass > 0 ? Math.max(5, Math.round((r.finalPass / maxP) * 120)) : 0;
      const oy = H - outH;
      if (r.total === 0 || r.finalPass === 0) {
        els.push(`<rect class="pil-empty" x="${x + 0.5}" y="${oy + 0.5}" width="${pw - 1}" height="${outH - 1}"/>`);
      } else {
        els.push(`<rect class="pil-outline" x="${x + 0.5}" y="${oy + 0.5}" width="${pw - 1}" height="${outH - 1}"/>`);
        const fy = H - fillH;
        els.push(`<rect class="pil-fill-neutral" x="${x + 1}" y="${fy}" width="${pw - 2}" height="${fillH}"/>`);
      }
      els.push(`<line x1="${x + pw / 2}" y1="${H}" x2="${x + pw / 2}" y2="${H + 8}" stroke="var(--axis)" stroke-width="1"/>`);
    });
    return `<svg class="hm-svg" width="${W}" height="${H + 8}" viewBox="0 0 ${W} ${H + 8}" aria-hidden="true" focusable="false">${els.join('')}</svg>`;
  }

  // 3. 담보 비교 축소 기둥(치료 단계 다섯마다 판정별 상대 수를 쌓은 기둥 하나, 폭 36px, 사이 16px)
  function coverPillarsSVG(c) {
    const stages = c.coverStageStacks(c.baseId);
    const maxS = Math.max(1, ...stages.map(s => s.sum));
    const pw = 36, gap = 16, H = 124;
    const W = stages.length * pw + (stages.length - 1) * gap;
    const els = [];
    stages.forEach((s, idx) => {
      const x = idx * (pw + gap);
      if (s.sum <= 0) {
        if (s.oursCnt > 0) {
          const cx = x + pw / 2, cy = H - 8;
          els.push(`<polygon class="pil-fill-gold" points="${cx},${cy - 7} ${cx + 7},${cy} ${cx},${cy + 7} ${cx - 7},${cy}"/>`);
        } else {
          els.push(`<rect class="pil-empty" x="${x + 0.5}" y="${H - 8.5}" width="${pw - 1}" height="8"/>`);
        }
      } else {
        const totH = Math.max(14, Math.round((s.sum / maxS) * 120));
        const parts = [
          { v: s.better, cls: 'pil-fill-gold', goldCap: true },
          { v: s.neutral, cls: 'pil-fill-neutral' },
          { v: s.worse, cls: 'pil-fill-worse' },
          { v: s.wait, cls: 'pil-hatch' },
          { v: s.miss, cls: 'pil-hatch-pale' },
        ].filter(p => p.v > 0);
        let curY = H;
        let remV = s.sum;
        let remH = totH;
        parts.forEach((p, pi) => {
          const h = pi === parts.length - 1 ? remH : Math.max(2, Math.round((p.v / remV) * remH));
          const y = curY - h;
          els.push(`<rect class="${p.cls}" x="${x + 0.5}" y="${y + 0.5}" width="${pw - 1}" height="${Math.max(1.5, h - 0.5)}"/>`);
          if (p.goldCap && h >= 5) {
            els.push(`<line x1="${x + 2}" y1="${y + 3}" x2="${x + pw - 2}" y2="${y + 3}" stroke="var(--gold-edge)" stroke-width="1.2"/>`);
          }
          curY = y;
          remV -= p.v;
          remH = Math.max(0, remH - h);
        });
      }
      els.push(`<line x1="${x + pw / 2}" y1="${H}" x2="${x + pw / 2}" y2="${H + 8}" stroke="var(--axis)" stroke-width="1"/>`);
    });
    return `<svg class="hm-svg" width="${W}" height="${H + 8}" viewBox="0 0 ${W} ${H + 8}" aria-hidden="true" focusable="false">${els.join('')}</svg>`;
  }

  // 4. 영업 인사이트 축소 기둥(분류 다섯마다 기둥 하나, 폭 36px, 높이는 건수)
  function insightPillarsSVG(c) {
    const cats = S['분류'] || [];
    const base = c.base || S['기준별'][c.baseId];
    const pSet = new Set(c.activePeerOrgs || []);
    const cntMap = {};
    if (c.peerScope === 'all' && base && base['분류집계']) {
      Object.assign(cntMap, base['분류집계']);
    } else if (base) {
      (base['포인트'] || []).forEach(id => {
        const p = S['포인트'][id];
        if (p && (p['관련기관코드'] || []).some(o => pSet.has(o))) {
          cntMap[p['분류']] = (cntMap[p['분류']] || 0) + 1;
        }
      });
    }
    const vals = cats.map(nm => cntMap[nm] || 0);
    const maxV = Math.max(1, ...vals);
    const pw = 36, gap = 10, H = 124;
    const W = cats.length * pw + (cats.length - 1) * gap;
    const els = [];
    cats.forEach((nm, idx) => {
      const v = vals[idx];
      const x = idx * (pw + gap);
      if (v <= 0) {
        els.push(`<rect class="pil-empty" x="${x + 0.5}" y="${H - 6.5}" width="${pw - 1}" height="6"/>`);
      } else {
        const h = Math.max(10, Math.round((v / maxV) * 120));
        const y = H - h;
        let cls = 'pil-fill-neutral';
        let extra = '';
        if (nm === '앞세울 강점') {
          cls = 'pil-fill-gold';
          extra = `<line x1="${x + 2}" y1="${y + 3}" x2="${x + pw - 2}" y2="${y + 3}" stroke="var(--gold-edge)" stroke-width="1.2"/>`;
        } else if (nm === '조건 열위 방어') {
          cls = 'pil-fill-worse';
        } else if (nm === '개정 검토 후보') {
          cls = 'pil-hatch-pale';
        }
        els.push(`<rect class="${cls}" x="${x + 0.5}" y="${y + 0.5}" width="${pw - 1}" height="${h - 1}"/>${extra}`);
      }
      els.push(`<line x1="${x + pw / 2}" y1="${H}" x2="${x + pw / 2}" y2="${H + 8}" stroke="var(--axis)" stroke-width="1"/>`);
    });
    return `<svg class="hm-svg" width="${W}" height="${H + 8}" viewBox="0 0 ${W} ${H + 8}" aria-hidden="true" focusable="false">${els.join('')}</svg>`;
  }

  // 5. 관계 지도: 숫자 없이 노드 다섯과 잇는 선
  function graphNodesSVG() {
    const H = 124, W = 188;
    const pts = [
      { x: 24, y: 74, s: 12 },
      { x: 64, y: 40, s: 12 },
      { x: 108, y: 66, s: 14 },
      { x: 146, y: 30, s: 12 },
      { x: 164, y: 84, s: 10 },
    ];
    const edges = [[0, 1], [1, 2], [2, 3], [2, 4], [1, 3]];
    const lines = edges.map(([a, b]) => `<line x1="${pts[a].x}" y1="${pts[a].y}" x2="${pts[b].x}" y2="${pts[b].y}" stroke="var(--ink-1)" stroke-width="1.3"/>`).join('');
    const stems = pts.map(p => `<line x1="${p.x}" y1="${p.y + p.s / 2}" x2="${p.x}" y2="${H + 6}" stroke="var(--line-2)" stroke-width="1"/>`).join('');
    const nodes = pts.map((p, i) => `<rect class="${i === 2 ? 'pil-fill-neutral' : 'pil-outline'}" fill="${i === 2 ? 'var(--neutral-pil)' : 'var(--fog-1)'}" x="${p.x - p.s / 2}" y="${p.y - p.s / 2}" width="${p.s}" height="${p.s}"/>`).join('');
    return `<svg class="hm-svg" width="${W}" height="${H + 8}" viewBox="0 0 ${W} ${H + 8}" aria-hidden="true" focusable="false">${stems}${lines}${nodes}</svg>`;
  }

  function groupReadHTML(id, base, c) {
    if (!base) return '';
    if (id === 'market') {
      const bGa = lineOf(base, '가'), bNa = lineOf(base, '나');
      return `<p class="hm-read-main">${esc(bGa ? bGa['문장'] : '')}</p>${bNa ? `<p class="hm-read-sub">${esc(bNa['문장'])}</p>` : ''}`;
    }
    if (id === 'gate') {
      const bDa = lineOf(base, '다');
      return `<p class="hm-read-main">${esc(bDa ? bDa['문장'] : '')}</p>`;
    }
    if (id === 'cover') {
      const bRa = lineOf(base, '라');
      return `<p class="hm-read-main">${esc(bRa ? bRa['문장'] : '')}</p>`;
    }
    if (id === 'insight') {
      const bMa = lineOf(base, '마');
      return `<p class="hm-read-main">${esc(bMa ? bMa['문장'] : '')}</p>`;
    }
    if (id === 'graph') {
      return `<p class="hm-read-main">${esc(t('grCenterDesc'))}</p>`;
    }
    const bMa = lineOf(base, '마');
    return `<p class="hm-read-main">${esc(App.firstSentence(bMa ? bMa['문장'] : ''))}</p>`;
  }

  function renderHome(panel, c) {
    const base = c.base || S['기준별'][c.baseId];
    if (!base) { panel.innerHTML = ''; return; }
    const metrics = App.ringTabMetrics(c);
    const svgByTab = {
      market: marketPillarsSVG(c),
      gate: gatePillarsSVG(c),
      cover: coverPillarsSVG(c),
      insight: insightPillarsSVG(c),
      graph: graphNodesSVG(),
    };
    const groupsHTML = App.SCREEN_IDS.map((id, idx) => {
      const m = metrics[id];
      let bigHTML = '<span class="hm-big hm-big-empty" aria-hidden="true"></span>';
      if (!m.isGraph && m.val != null) {
        const den = m.denom != null ? `<small>/${esc(fmt(m.denom))}</small>` : '';
        bigHTML = `<span class="hm-big num">${esc(fmt(m.val))}${den}</span>`;
      }
      const extraTag = id === 'market' && m.subText
        ? `<span class="hm-sub">${esc(m.subText)}</span>`
        : (m.fullBadge ? `<span class="tag" title="${esc(t('fullScopeHint'))}">${esc(t('fullScopeBadge'))}</span>` : '');
      return `<button type="button" class="hm-grp" id="tab-${id}" data-rtab="${id}" tabindex="${idx === 0 ? 0 : -1}">
        ${m.flag ? ui.flag(m.flag) : ''}
        <div class="hm-head">
          ${bigHTML}
          <span class="hm-name"><span>${esc(m.name)}</span>${extraTag}</span>
        </div>
        <span class="hm-stem" aria-hidden="true"><i class="hm-dia"></i></span>
        <div class="hm-pils">${svgByTab[id]}</div>
      </button>`;
    }).join('');

    const defaultRead = groupReadHTML(null, base, c);
    panel.innerHTML = `<div class="hm-stage">
      <div class="hm-axis-wrap" role="group" aria-label="${esc(t('tabsAria'))}">
        ${groupsHTML}
      </div>
      <div class="hm-read" id="home-read" aria-live="polite">${defaultRead}</div>
    </div>`;

    const axisWrap = panel.querySelector('.hm-axis-wrap');
    const readEl = panel.querySelector('#home-read');
    if (axisWrap && readEl) {
      const showFor = id => { readEl.innerHTML = groupReadHTML(id, base, c); };
      axisWrap.addEventListener('pointerover', e => {
        const g = e.target.closest && e.target.closest('.hm-grp[data-rtab]');
        if (g) showFor(g.dataset.rtab);
      });
      axisWrap.addEventListener('pointerleave', () => {
        const f = document.activeElement && document.activeElement.closest && document.activeElement.closest('#home-panel .hm-grp[data-rtab]');
        showFor(f ? f.dataset.rtab : null);
      });
      axisWrap.addEventListener('focusin', e => {
        const g = e.target.closest && e.target.closest('.hm-grp[data-rtab]');
        if (g) showFor(g.dataset.rtab);
      });
      axisWrap.addEventListener('focusout', e => {
        if (!axisWrap.contains(e.relatedTarget)) showFor(null);
      });
    }
  }

  function renderTextModal(c) {
    const base = c.base || S['기준별'][c.baseId];
    const rows = (base && base['브리핑']) || [];
    const lim = !c.isRef ? limitLine(c) : '';
    const refBanner = !c.isRef
      ? `<p class="hp-ref">${esc(t('briefOffCondTpl', { cond: App.condSegOnly(), ref: refCondText() }))}${lim ? ' ' + esc(lim) : ''}</p>`
      : '';
    const listHTML = `<div class="panel flat">
      ${refBanner}
      <ol class="hp-list">${rows.map((b, idx) => {
        const go = ROW_GO[b['줄']] || { tab: 'market', grp: '' };
        const nm = rowName(b);
        const sc = b['범위'] === '전체 고객군' ? 'all' : 'base';
        return `<li class="hp-row">
          <button type="button" class="hp-hit" data-go="${esc(go.tab)}"${go.grp ? ` data-grp="${esc(go.grp)}"` : ''} aria-label="${esc(`${nm}: ${b['문장']}`)}"></button>
          ${b['원문대조'] ? ui.flag(b['원문대조글']) : ''}
          <span class="hp-no num"><span class="z">0</span>${idx + 1}</span>
          <span class="hp-cat"><span>${esc(nm)}</span>${ui.scope(sc)}</span>
          <p class="hp-sent">${esc(b['문장'])}</p>
          <span class="hp-chev" aria-hidden="true">${ui.IC.chevR}</span>
        </li>`;
      }).join('')}</ol>
    </div>`;
    return {
      kicker: t('homePathRoot'),
      title: t('homeListHead'),
      badges: [ui.fullScopeTag()].filter(Boolean),
      actions: ui.btn(t('actCopySum'), { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="copy-summary"' }),
      html: listHTML,
    };
  }

  function homeActions() {
    return ui.btn(t('actModeText'), { sm: true, ghost: true, icon: 'table', attrs: 'id="home-text-btn" data-home-modal="1"' });
  }

  document.addEventListener('click', e => {
    const mb = e.target.closest && e.target.closest('[data-home-modal]');
    if (mb) {
      e.stopPropagation();
      App.openModal({ trigger: mb, render: renderTextModal });
    }
  });

  function copySummary(c) {
    const base = c.base || S['기준별'][c.baseId];
    if (!base) return;
    const rows = (base['브리핑'] || []).map(b => [b['줄'], rowName(b), b['범위'], b['문장'], b['갈곳']]);
    App.copyRows(t('briefCopyCols').split(','), rows, { title: t('briefCopyTitle') });
  }

  App.registerTab({ id: 'brief', renderHome, actions: homeActions, copySummary });

  // ---------- 다섯째 탭: 관계 지도(사각 면 없이 노드와 연결선 표시, graph2.html 이동) ----------
  ui.registerLegend('graph', 'grLegendTitle', () => `<dl class="legend">
      <dt>${ui.IC.open}</dt><dd>${esc(t('grLgNode'))}</dd>
      <dt>${ui.IC.arrow}</dt><dd>${esc(t('grLgEdge'))}</dd>
    </dl>`);

  function graphStats(c) {
    const pSet = new Set(c.activePeerOrgs);
    const allOrgs = c.peerScope === 'all' ? txt.ORG_ORDER.length : 1 + c.activePeerOrgs.length;
    const allVars = Object.values(S['종형'] || {}).filter(v => v['기관코드'] === 'EPOST' || c.peerScope === 'all' || pSet.has(v['기관코드'])).length;
    const stds = Object.keys(S['표준담보'] || {}).length;
    const pts = ((c.base && c.base['포인트']) || []).filter(id => {
      const p = S['포인트'][id];
      return p && (c.peerScope === 'all' || (p['관련기관코드'] || []).some(o => pSet.has(o)));
    }).length;
    const news = ((S['시장소식'] && S['시장소식']['소식']) || []).length;
    return { orgs: allOrgs, vars: allVars, stds, pts, news };
  }

  function renderGraphZones({ left, center, ctx: c }) {
    const stCnt = graphStats(c);
    const kinds = [
      { k: 'org', nm: t('grKindOrg'), n: stCnt.orgs },
      { k: 'var', nm: t('grKindVar'), n: stCnt.vars },
      { k: 'std', nm: t('grKindStd'), n: stCnt.stds },
      { k: 'pt', nm: t('grKindPt'), n: stCnt.pts },
      { k: 'news', nm: t('grKindNews'), n: stCnt.news },
    ];
    const curGrp = c.st.grp.graph || 'org';
    left.innerHTML = `<div class="zl-head"><span class="zl-k">${esc(t('grLeftHead'))}</span></div>
      <div class="zl-list" role="listbox" aria-label="${esc(t('grLeftHead'))}">
        ${kinds.map(x => `<button type="button" class="zl-item${curGrp === x.k ? ' is-on' : ''}" role="option" aria-selected="${curGrp === x.k}" data-zl="${x.k}">
          <span class="zl-ring">${ui.miniRingSVG(1, 1, '')}<span class="zl-n num">${esc(fmt(x.n))}</span></span>
          <span class="zl-t">${esc(x.nm)}</span>
        </button>`).join('')}
      </div>`;

    center.innerHTML = `<div class="gr-stage" id="view-graph-stage">
      <svg class="gr-svg" viewBox="0 0 540 196" aria-hidden="true" focusable="false">
        <line x1="0" y1="184" x2="540" y2="184" stroke="var(--axis)" stroke-width="2"/>
        <path class="gr-ln" d="M84 96H182M254 96H342M378 56V136M218 96L342 44M218 96L342 148"/>
        <line x1="50" y1="120" x2="50" y2="184" stroke="var(--line-2)" stroke-width="1"/>
        <line x1="218" y1="120" x2="218" y2="184" stroke="var(--line-2)" stroke-width="1"/>
        <line x1="422" y1="168" x2="422" y2="184" stroke="var(--line-2)" stroke-width="1"/>
        <rect class="gr-box" x="16" y="72" width="68" height="48"/>
        <text class="gr-tx" x="50" y="93" text-anchor="middle">${esc(t('grKindOrg'))}</text>
        <text class="gr-sub" x="50" y="110" text-anchor="middle">${esc(fmt(stCnt.orgs))}</text>
        <rect class="gr-box" x="182" y="72" width="72" height="48"/>
        <text class="gr-tx" x="218" y="93" text-anchor="middle">${esc(t('grKindVar'))}</text>
        <text class="gr-sub" x="218" y="110" text-anchor="middle">${esc(fmt(stCnt.vars))}</text>
        <rect class="gr-box" x="342" y="20" width="160" height="46"/>
        <text class="gr-tx" x="422" y="41" text-anchor="middle">${esc(t('grKindStd'))}</text>
        <text class="gr-sub" x="422" y="57" text-anchor="middle">${esc(fmt(stCnt.stds))}</text>
        <rect class="gr-box" x="342" y="122" width="160" height="46"/>
        <text class="gr-tx" x="422" y="143" text-anchor="middle">${esc(t('grKindPt'))}</text>
        <text class="gr-sub" x="422" y="159" text-anchor="middle">${esc(fmt(stCnt.pts))}</text>
      </svg>
      <div class="gr-actions">
        <a class="btn btn-main" href="graph2.html">${esc(t('grOpenProtoBtn'))} ${ui.IC.chevR}</a>
      </div>
    </div>`;
  }

  function defaultGraphEv(c) {
    const stCnt = graphStats(c);
    return {
      kicker: t('evKickerDefault'),
      title: t('grEvTitle'),
      badges: [ui.scope('all')],
      body: `<div class="ev-sec"><p>${esc(t('grEvBodyTpl', {
        orgs: fmt(stCnt.orgs), vars: fmt(stCnt.vars), stds: fmt(stCnt.stds), pts: fmt(stCnt.pts), news: fmt(stCnt.news),
      }))}</p></div>`,
    };
  }

  App.registerTab({ id: 'graph', layout: 'three', renderZones: renderGraphZones, defaultEv: defaultGraphEv });
})();
