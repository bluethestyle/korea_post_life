/* 시안 4 처음 여는 상태(브리핑 결론 목록)와 다섯째 탭(관계 지도 1단계 연결 자리).
   모든 화면 문구는 core.js 의 COPY 표(App.t)에서 읽고, 수치는 sales.json 에서 읽는다. */
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
      <dt><i class="cq m-all" aria-hidden="true"></i></dt><dd>${esc(t('homeLgDark'))}</dd>
      <dt>${ui.IC.hatch}</dt><dd>${esc(t('homeLgTick'))}</dd>
      <dt>${ui.flagText(t('flagShort'))}</dt><dd>${esc(t('lgFlag'))}</dd>
      <dt>${ui.scope('all')}</dt><dd>${esc(t('lgScopeAll'))}</dd>
      <dt>${ui.scope('base')}</dt><dd>${esc(t('lgScopeBase'))}</dd>
    </dl>`);

  function renderHome(panel, c) {
    const base = c.base || S['기준별'][c.baseId];
    if (!base) { panel.innerHTML = ''; return; }
    const rows = base['브리핑'] || [];
    const lim = !c.isRef ? limitLine(c) : '';
    const refBanner = !c.isRef
      ? `<p class="hp-ref">${esc(t('briefOffCondTpl', { cond: App.condSegOnly(), ref: refCondText() }))}${lim ? ' ' + esc(lim) : ''}</p>`
      : '';
    panel.innerHTML = `<div class="hp-head">
        <div class="hp-head-t"><span>${esc(t('homeListHead'))}</span>${ui.fullScopeTag()}</div>
        <span class="note">${esc(t('homeListHint'))}</span>
      </div>
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
      }).join('')}</ol>`;
  }

  function copySummary(c) {
    const base = c.base || S['기준별'][c.baseId];
    if (!base) return;
    const rows = (base['브리핑'] || []).map(b => [b['줄'], rowName(b), b['범위'], b['문장'], b['갈곳']]);
    App.copyRows(t('briefCopyCols').split(','), rows, { title: t('briefCopyTitle') });
  }

  App.registerTab({ id: 'brief', renderHome, copySummary });

  // ---------- 다섯째 탭: 관계 지도(1단계 연결 자리, graph2.html 이동) ----------
  ui.registerLegend('graph', 'grLegendTitle', () => `<dl class="legend">
      <dt>${ui.IC.open}</dt><dd>${esc(t('grLgNode'))}</dd>
      <dt>${ui.IC.arrow}</dt><dd>${esc(t('grLgEdge'))}</dd>
    </dl>`);

  function graphStats(c) {
    const pSet = new Set(c.activePeerOrgs);
    const allOrgs = c.peerScope === 'all' ? txt.ORG_ORDER.length : 1 + c.activePeerOrgs.length;
    const allVars = Object.values(S['종형'] || {}).filter(v => v['기관코드'] === 'EPOST' || c.peerScope === 'all' || pSet.has(v['기관코드'])).length;
    const stds = Object.keys(S['표준담보'] || {}).length;
    const pts = (c.base && c.base['포인트'] || []).filter(id => {
      const p = S['포인트'][id];
      return p && (c.peerScope === 'all' || (p['관련기관코드'] || []).some(o => pSet.has(o)));
    }).length;
    const news = ((S['시장소식'] && S['시장소식']['소식']) || []).length;
    return { orgs: allOrgs, vars: allVars, stds, pts, news };
  }

  function renderGraphZones({ left, center, ctx: c }) {
    const stCnt = graphStats(c);
    const kinds = [
      { k: 'org', nm: t('grKindOrg'), n: stCnt.orgs, gold: true },
      { k: 'var', nm: t('grKindVar'), n: stCnt.vars, gold: true },
      { k: 'std', nm: t('grKindStd'), n: stCnt.stds, gold: false },
      { k: 'pt', nm: t('grKindPt'), n: stCnt.pts, gold: false },
      { k: 'news', nm: t('grKindNews'), n: stCnt.news, gold: false },
    ];
    const curGrp = c.st.grp.graph || 'org';
    left.innerHTML = `<div class="zl-head"><span class="zl-k">${esc(t('grLeftHead'))}</span></div>
      <div class="zl-list" role="listbox" aria-label="${esc(t('grLeftHead'))}">
        ${kinds.map(x => `<button type="button" class="zl-item${curGrp === x.k ? ' is-on' : ''}" role="option" aria-selected="${curGrp === x.k}" data-zl="${x.k}">
          <span class="zl-ring">${ui.miniRingSVG(1, 1, x.gold ? 'gold' : '')}<span class="zl-n num">${esc(fmt(x.n))}</span></span>
          <span class="zl-t">${esc(x.nm)}</span>
        </button>`).join('')}
      </div>`;

    center.innerHTML = `<div class="gr-stage" id="view-graph-stage">
      <svg class="gr-svg" viewBox="0 0 520 176" aria-hidden="true" focusable="false">
        <path class="gr-ln" d="M84 88H182M254 88H342M378 52V124M218 88L342 40M218 88L342 136"/>
        <rect class="gr-box gold" x="16" y="64" width="68" height="48"/>
        <text class="gr-tx" x="50" y="85" text-anchor="middle">${esc(t('grKindOrg'))}</text>
        <text class="gr-sub" x="50" y="102" text-anchor="middle">${esc(fmt(stCnt.orgs))}</text>
        <rect class="gr-box gold" x="182" y="64" width="72" height="48"/>
        <text class="gr-tx" x="218" y="85" text-anchor="middle">${esc(t('grKindVar'))}</text>
        <text class="gr-sub" x="218" y="102" text-anchor="middle">${esc(fmt(stCnt.vars))}</text>
        <rect class="gr-box" x="342" y="16" width="160" height="46"/>
        <text class="gr-tx" x="422" y="37" text-anchor="middle">${esc(t('grKindStd'))}</text>
        <text class="gr-sub" x="422" y="53" text-anchor="middle">${esc(fmt(stCnt.stds))}</text>
        <rect class="gr-box" x="342" y="114" width="160" height="46"/>
        <text class="gr-tx" x="422" y="135" text-anchor="middle">${esc(t('grKindPt'))}</text>
        <text class="gr-sub" x="422" y="151" text-anchor="middle">${esc(fmt(stCnt.pts))}</text>
      </svg>
      <p class="gr-desc">${esc(t('grCenterDesc'))}</p>
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

  App.registerTab({ id: 'graph', renderZones: renderGraphZones, defaultEv: defaultGraphEv });
})();
