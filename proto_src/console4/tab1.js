/* 탭 1 브리핑: 주인공 도형은 원형 이중 고리 메달.
   1층은 큰 메달 다섯과 결론 한 줄만 보이고, 고르면 2층 단일 시각화가 펼쳐지며, 세부 요소를 고르면 3층 근거가 열린다.
   화면 코드 문구는 모두 App.t(core.js 의 COPY)에서 읽고, 숫자와 문장은 sales.json 에서 읽는다. */
App.registerTab((function () {
  const { ui, txt, t } = App;
  const { esc, fmt } = ui;
  const S = App.S;
  const ROW_KEY_NAME = {
    '가': 'briefRowGa', '나': 'briefRowNa', '다': 'briefRowDa', '라': 'briefRowRa', '마': 'briefRowMa',
  };
  const ROW_FOCUS = { '가': 'map', '나': 'news', '다': '', '라': 'journey', '마': '' };
  const ROW_NO = { '가': 1, '나': 2, '다': 3, '라': 4, '마': 5 };
  const MAP_LABELS = S['라벨'];

  let viewMode = 'medal';
  let lastStageSel = null;

  const brief = c => (c.base ? c.base['브리핑'] : []);
  const line = (c, k) => brief(c).find(b => b['줄'] === k) || null;
  const rowName = b => b['구역'] || t(ROW_KEY_NAME[b['줄']] || 'briefRowGa');
  const refText = c => `${c.ref['나이']}${t('condAgeUnit')} ${txt.sexText(c.ref['성별'])}, ${txt.sinceText(c.ref['이력'])}`;

  function conclText(c) {
    const ga = line(c, '가'), na = line(c, '나'), da = line(c, '다'), ra = line(c, '라'), ma = line(c, '마');
    const gv = ga ? ga['값'] : {}, nv = na ? na['값'] : {}, dv = da ? da['값'] : {}, rv = ra ? ra['값'] : {}, mv = ma ? ma['값'] : {};
    const open = (gv['우리간편만열림칸수'] || 0) + (gv['함께열림칸수'] || 0);
    return t('briefConclTpl', {
      kind: txt.vkind(c.baseId),
      open: fmt(open),
      cells: fmt(gv['전체칸수'] || 0),
      rev: fmt(nv['개정변동수'] || 0),
      gate: fmt(dv['관문차이수'] || 0),
      cmp: fmt(rv['견준쌍'] || 0),
      pairs: fmt(rv['공통담보쌍'] || 0),
      ins: fmt(mv['전체수'] || 0),
    });
  }

  function limitLine(c) {
    const L = c.limit;
    if (!L || (c.st.age === c.ref['나이'] && c.st.sex === c.ref['성별'])) return '';
    const who = `${c.st.age}${t('condAgeUnit')} ${txt.sexText(c.st.sex)}`;
    const kind = txt.vkind(c.baseId);
    if (!L.hit) return t('briefLimitOutTpl', { who, kind, lo: L.lo, hi: L.hi });
    const extra = (L.hit.pend ? t('briefLimitPend') : '') + (L.table['성별같음'] ? t('briefLimitSameSex') : '');
    return t('briefLimitInTpl', { who, max: fmt(L.hit.max), lo: L.hit.lo, hi: L.hit.hi, extra });
  }

  // 브리핑 전용 도형 범례 등록(늘 깔아 두지 않고 범례 단추로 연다)
  ui.registerLegend('brief', 'briefLegendTitle', () => `<dl class="legend">
    <dt><span style="display:inline-block;width:16px;height:16px;border-radius:50%;border:2.5px solid var(--gold-line);box-shadow:inset 0 0 0 2px var(--gold)"></span></dt><dd>${esc(t('briefLgMedalGold'))}</dd>
    <dt><span style="display:inline-block;width:16px;height:16px;border-radius:50%;background:var(--red)"></span></dt><dd>${esc(t('briefLgMedalRed'))}</dd>
    <dt><span style="display:inline-block;width:16px;height:16px;border-radius:50%;border:1.5px dashed var(--ink-2)"></span></dt><dd>${esc(t('briefLgMedalTick'))}</dd>
    <dt><span style="display:inline-block;width:16px;height:14px;background:var(--gold);border-top:2.5px solid var(--gold-line)"></span></dt><dd>${esc(t('briefLgMapOpen'))}</dd>
    <dt><span style="display:inline-block;width:16px;height:14px;background:var(--m-ours)"></span></dt><dd>${esc(t('briefLgMapOurs'))}</dd>
    <dt><span style="display:inline-block;width:16px;height:14px;border:1.5px dashed var(--ink-1)"></span></dt><dd>${esc(t('briefLgMapGo'))}</dd>
    <dt><span style="display:inline-block;width:16px;height:14px;border:2px solid var(--ink-0)"></span></dt><dd>${esc(t('briefLgMapNow'))}</dd>
    <dt><span style="display:inline-block;width:16px;height:14px;background:var(--gold);border-top:2.5px solid var(--gold-line)"></span></dt><dd>${esc(t('briefLgStepGold'))}</dd>
    <dt>${ui.scope('all')}</dt><dd>${esc(t('lgScopeAll'))}</dd>
    <dt>${ui.scope('base')}</dt><dd>${esc(t('lgScopeBase'))}</dd>
  </dl>`);

  // ---------- 1. 머리 제어 줄 ----------
  function headAsideHTML() {
    const isList = viewMode === 'list';
    return `<div class="bhead">
      ${ui.legendBtn('brief')}
      ${ui.btn(t(isList ? 'briefModeShape' : 'briefModeText'), {
        sm: true, ghost: !isList, cls: isList ? 'is-mode-on' : '',
        attrs: `data-act="brief-mode" aria-pressed="${isList}"`,
      })}
      ${ui.btn(t('briefCopyBtn'), { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="brief-copy"' })}
    </div>`;
  }

  // ---------- 2. 1층: 다섯 큰 원형 메달 ----------
  function medalSpecs(c) {
    return brief(c).map(b => {
      const k = b['줄'];
      const v = b['값'] || {};
      const no = String(ROW_NO[k]).padStart(2, '0');
      const nm = rowName(b);
      const scope = b['범위'] === '전체 고객군' ? 'all' : 'base';
      let num = '0', den = null, max = 1, segs = [], hasGold = false;

      if (k === '가') {
        num = fmt(v['함께열림칸수'] || 0);
        den = fmt(v['전체칸수'] || 0);
        max = v['전체칸수'] || 1;
        const onlyN = v['우리간편만열림칸수'] || 0;
        segs = [{ v: onlyN, cls: 'gold' }, { v: v['함께열림칸수'] || 0, cls: '' }];
        hasGold = onlyN > 0;
      } else if (k === '나') {
        num = fmt(v['개정변동수'] || 0);
        max = v['개정변동수'] || 1;
        segs = [{ v: v['개정신설'] || 0, cls: 'gold' }, { v: v['개정변경'] || 0, cls: '' }];
        hasGold = (v['개정신설'] || 0) > 0;
      } else if (k === '다') {
        num = fmt(v['관문차이수'] || 0);
        const denomPeers = (c.allPeerIds || c.peerIds || []).length;
        max = Math.max(1, denomPeers);
        segs = [{ v: v['관문차이수'] || 0, cls: '' }];
      } else if (k === '라') {
        num = fmt(v['견준쌍'] || 0);
        den = fmt(v['공통담보쌍'] || 0);
        max = v['공통담보쌍'] || 1;
        segs = [{ v: v['견준쌍'] || 0, cls: '' }];
        hasGold = (v['보유수'] || 0) > 0;
      } else if (k === '마') {
        num = fmt(v['전체수'] || 0);
        max = v['전체수'] || 1;
        const pos = (v['앞세울수'] || 0) + (v['관련담보수'] || 0);
        const mid = (v['관문차이수'] || 0) + (v['조건열위수'] || 0);
        segs = [{ v: pos, cls: 'gold' }, { v: mid, cls: '' }];
        hasGold = pos > 0;
      }

      const numText = den != null ? `${num}/${den}` : num;
      return {
        key: k, no, name: nm, scope, scopeText: b['범위'],
        num, den, numText, max, segs, hasGold,
        flag: !!b['원문대조'], flagText: b['원문대조글'],
        tip: `${nm} (${b['범위']}): ${numText}`,
      };
    });
  }

  function medalSVG(m) {
    let acc = 0, arcs = '';
    for (const s of m.segs) {
      const f = m.max > 0 ? Math.max(0, Math.min(1 - acc, s.v / m.max)) : 0;
      if (f > 0) {
        const to = (f * 100).toFixed(2);
        arcs += `<circle class="arc ${s.cls || ''}" r="46" fill="none" stroke-width="5.8" pathLength="100" stroke-dasharray="${to} 100" stroke-dashoffset="${(-acc * 100).toFixed(2)}" transform="rotate(-90)" data-to="${to}"/>`;
      }
      acc += f;
    }
    const frac = Math.min(1, acc);
    let tks = '';
    for (let i = 0; i < 72; i++) {
      const a = i / 72;
      if (a < frac - 1e-6) continue;
      const th = a * Math.PI * 2 - Math.PI / 2, cs = Math.cos(th), sn = Math.sin(th);
      tks += `<line x1="${(cs * 42.5).toFixed(2)}" y1="${(sn * 42.5).toFixed(2)}" x2="${(cs * 49.5).toFixed(2)}" y2="${(sn * 49.5).toFixed(2)}"/>`;
    }
    return `<svg class="ring bm-svg" width="136" height="136" viewBox="-64 -64 128 128" aria-hidden="true" focusable="false">
      <circle class="bm-outer" r="55" fill="none" stroke-width="1"/>
      <path class="bm-card" d="M0 -59V-54M59 0H54M0 59V54M-59 0H-54" stroke-width="1.4" fill="none"/>
      <circle class="trk" r="46" fill="none" stroke-width="1"/>
      <g class="tks" stroke-width="1.5">${tks}</g>
      ${arcs}
      <circle class="bm-inner${m.hasGold ? ' gold' : ''}" r="38.5" fill="none" stroke-width="1.5"/>
      <circle class="bm-disc" r="35.5"/>
      <path class="bm-diag" d="M-56 -56l10 10M56 -56l-10 10M-56 56l10 -10M56 56l-10 -10" stroke-width="2.1" fill="none"/>
    </svg>`;
  }

  function medalsHTML(c) {
    return `<div class="bmedals" data-pick-group="brief">${medalSpecs(c).map((m, i) => `
      <div class="bmedal brow" data-pick="${esc(m.key)}" data-tip="${esc(m.tip)}" style="--mi:${i}">
        <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${m.name}, ${m.numText}, ${m.scopeText}`)}"></button>
        ${m.flag ? ui.flag(m.flagText || ui.FLAG_TEXT) : ''}
        <div class="bm-emblem">
          ${medalSVG(m)}
          <div class="bm-val">
            <span class="bm-n num${m.den != null ? ' frac' : ''}">${esc(m.num)}${m.den != null ? `<small class="bm-d">/${esc(m.den)}</small>` : ''}</span>
          </div>
        </div>
        <div class="bm-foot">
          <span class="bm-sc" aria-hidden="true">${m.scope === 'all' ? ui.IC.grid : ui.IC.pin}</span>
          <span class="bm-name">${esc(m.name)}</span>
        </div>
      </div>`).join('')}</div>`;
  }

  function miniMedalSVG(m) {
    let acc = 0, arcs = '';
    for (const s of m.segs) {
      const f = m.max > 0 ? Math.max(0, Math.min(1 - acc, s.v / m.max)) : 0;
      if (f > 0) {
        const to = (f * 100).toFixed(2);
        arcs += `<circle class="arc ${s.cls || ''}" r="17" fill="none" stroke-width="2.6" pathLength="100" stroke-dasharray="${to} 100" stroke-dashoffset="${(-acc * 100).toFixed(2)}" transform="rotate(-90)" data-to="${to}"/>`;
      }
      acc += f;
    }
    const frac = Math.min(1, acc);
    let tks = '';
    for (let i = 0; i < 24; i++) {
      const a = i / 24;
      if (a < frac - 1e-6) continue;
      const th = a * Math.PI * 2 - Math.PI / 2, cs = Math.cos(th), sn = Math.sin(th);
      tks += `<line x1="${(cs * 15.2).toFixed(2)}" y1="${(sn * 15.2).toFixed(2)}" x2="${(cs * 18.8).toFixed(2)}" y2="${(sn * 18.8).toFixed(2)}"/>`;
    }
    return `<svg class="ring l2-tsvg" width="42" height="42" viewBox="-22 -22 44 44" aria-hidden="true" focusable="false">
      <circle class="trk" r="17" fill="none" stroke-width="1"/>
      <g class="tks" stroke-width="1.1">${tks}</g>
      ${arcs}
      <circle class="disc" r="13.2"/>
    </svg>`;
  }

  function l2TabsHTML(c) {
    return `<div class="l2-tabs" data-pick-group="brief">${medalSpecs(c).map(m => `
      <div class="bmedal brow l2-tab" data-pick="${esc(m.key)}" data-tip="${esc(m.tip)}">
        <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${m.name}, ${m.numText}, ${m.scopeText}`)}"></button>
        ${m.flag ? ui.flag(m.flagText || ui.FLAG_TEXT) : ''}
        <div class="l2-tring">${miniMedalSVG(m)}<span class="l2-tn num">${esc(m.num)}</span></div>
        <span class="l2-tnm">${esc(m.name)}</span>
      </div>`).join('')}</div>`;
  }

  // ---------- 3. 2층: 무대 전체가 전환되어 고른 메달의 시각화 하나만 열린다 ----------
  function subRingSVG(v, max, cls = '') {
    const f = max > 0 ? Math.max(0, Math.min(1, v / max)) : 0;
    const to = (f * 100).toFixed(2);
    let tks = '';
    for (let i = 0; i < 48; i++) {
      const a = i / 48;
      if (a < f - 1e-6) continue;
      const th = a * Math.PI * 2 - Math.PI / 2, cs = Math.cos(th), sn = Math.sin(th);
      tks += `<line x1="${(cs * 38).toFixed(2)}" y1="${(sn * 38).toFixed(2)}" x2="${(cs * 44).toFixed(2)}" y2="${(sn * 44).toFixed(2)}"/>`;
    }
    const arc = f > 0 ? `<circle class="arc ${cls}" r="41" fill="none" stroke-width="5" pathLength="100" stroke-dasharray="${to} 100" transform="rotate(-90)" data-to="${to}"/>` : '';
    return `<svg class="ring" width="92" height="92" viewBox="-52 -52 104 104" aria-hidden="true" focusable="false">
      <circle class="trk" r="41" fill="none" stroke-width="1"/>
      <g class="tks" stroke-width="1.4">${tks}</g>
      ${arc}
      <circle class="disc" r="32"/>
    </svg>`;
  }

  const CELL_STYLE = {
    '우리 간편만 열림': { cls: 'is-only', ic: ui.IC.only },
    '함께 열림': { cls: 'is-open', ic: ui.IC.open },
    '우리 간편 닫힘': { cls: 'is-ours', ic: ui.IC.check },
    '간편 모두 닫힘': { cls: 'is-all', ic: ui.IC.lock },
    '자료 없음': { cls: 'is-none', ic: ui.IC.hatch },
  };
  const timeShort = r => (r.since === 5 ? t('briefTimeOver5') : r['이름'].replace(/^(입원|수술만)\s*/, '').replace(/\s*전$/, ''));
  const orgCodeOfVid = vid => ((txt.vinfo(vid) && txt.vinfo(vid)['기관코드']) || String(vid).split('_')[0]);

  function orgNodeInfo(org, cell, orgTotals) {
    const stName = (cell['회사'] && cell['회사'][org]) || '';
    const noData = (cell['자료없음'] || []).includes(org);
    const openIds = (cell['열린종형'] && cell['열린종형'][org]) || [];
    const nTxt = noData ? t('briefGateUnknownSym') : fmt(openIds.length);
    const cls = org === 'EPOST' && stName === '열림' ? 'gold' : '';
    const ic = stName === '열림' ? ui.IC.open : stName === '닫힘' ? ui.IC.lock : noData ? ui.IC.hatch : ui.IC.check;
    const tip = `${txt.orgShort(org)}: ${stName}${noData ? '' : `, ${openIds.length}${t('briefGateOpenUnit')}`}`;
    return { org, stName, noData, openIds, nTxt, cls, ic, tip, max: orgTotals[org] || 1 };
  }

  function layer2HTML(key, c, animate) {
    if (!key) return '';
    const b = line(c, key);
    if (!b) return '';
    const idx = (ROW_NO[key] || 1) - 1;
    const ox = `${(idx + 0.5) * 20}%`;
    const tab = App.TAB_BY_NAME[b['갈곳']] || 'brief';
    const goBtn = ui.btn(t('briefGoTabTpl', { tab: b['갈곳'] }), {
      sm: true, ghost: true, chev: true,
      attrs: `data-go="${tab}"${ROW_FOCUS[key] ? ` data-focus="${ROW_FOCUS[key]}"` : ''}`,
    });
    const closeBtn = ui.btn(t('briefUpBtn'), { sm: true, ghost: true, attrs: 'data-layer-up="1"' });

    let titleStr = '';
    let inner = '';

    if (key === '가') {
      const m = App.mapOf(null);
      const nowSeg = App.cellOf(Object.assign({}, c.st, { renewal: null }));
      const cols = m['열'] || [];
      const totalCells = (b['값'] && b['값']['전체칸수']) || ((m['행'] || []).length * cols.length);
      titleStr = t('briefL2GaTitleTpl', { n: fmt(totalCells) });
      const hospRows = (m['행'] || []).map((r, i) => ({ r, i })).filter(x => x.r['종류'] === '입원');
      const surgRows = (m['행'] || []).map((r, i) => ({ r, i })).filter(x => x.r['종류'] === '수술만');
      const colHeads = `<div class="bmap-cols" aria-hidden="true"><span></span>${hospRows.map(x => `<span class="bmap-ch">${esc(timeShort(x.r))}</span>`).join('')}</div>`;
      const rows = [];
      let rowIdx = 0;
      [
        { label: t('briefHospShort'), list: hospRows, surg: false },
        { label: t('briefSurgShort'), list: surgRows, surg: true },
      ].forEach(g => {
        cols.forEach((col, ci) => {
          const cells = g.list.map(x => {
            const ri = x.i, cell = m['칸'][ri][ci];
            const st = CELL_STYLE[cell['라벨']] || CELL_STYLE['자료 없음'];
            const isNow = nowSeg && nowSeg.cell && nowSeg.ri === ri && nowSeg.ci === ci;
            const go = cell['관문만수집'] || [];
            const goTxt = !go.length ? '' : go.length <= 2
              ? `, ${go.map(z => `${z['이름']} ${z['안내'] || ''}`).join(', ')}`
              : `, ${t('peerRestTpl', { first: go[0]['이름'], rest: go.length - 1 })} ${go[0]['안내'] || ''}`;
            const tip = `${x.r['이름']}, ${col.lo}~${col.hi}${t('condAgeUnit')}: ${cell['라벨']}${cell['보조'] ? ` (${cell['보조']})` : ''}${goTxt}`;
            return `<button type="button" class="bm-cell ${st.cls}${go.length ? ' has-go' : ''}${isNow ? ' is-now' : ''}" data-sub-pick="seg:${ri}-${ci}" data-tip="${esc(tip)}" aria-pressed="false" aria-label="${esc(tip)}">
              <i class="bm-cbg" aria-hidden="true"></i>
              ${cell['라벨'] === '우리 간편만 열림' ? ui.flag() : ''}
              <span class="bm-cs" aria-hidden="true">${st.ic}</span>
            </button>`;
          }).join('');
          rows.push(`<div class="bmap-row${g.surg && ci === 0 ? ' surg-start' : ''}" style="--ri:${rowIdx++}">
            <span class="bmap-rh">${esc(`${g.label} ${col.lo}~${col.hi}`)}</span>${cells}
          </div>`);
        });
      });
      inner = `<div class="bmap-wrap">${colHeads}${rows.join('')}</div>`;
    } else if (key === '나') {
      titleStr = t('briefL2NaTitle');
      const v = b['값'] || {};
      const tot = v['개정변동수'] || 1;
      const nw = S['시장소식'] || {};
      const items = [
        { k: 'rev:new', lbl: t('briefRevNew'), n: v['개정신설'] || 0, max: tot, cls: 'gold' },
        { k: 'rev:chg', lbl: t('briefRevChg'), n: v['개정변경'] || 0, max: tot, cls: '' },
        { k: 'rev:end', lbl: t('briefRevEnd'), n: v['개정종료'] || 0, max: tot, cls: '' },
        { k: 'rev:news', lbl: t('briefNewsNode'), n: nw['건수'] || 0, max: Math.max(1, nw['건수'] || 1), cls: (nw['연결'] || 0) > 0 ? 'gold' : '' },
      ];
      inner = `<div class="l2-rings" style="--cols:4">${items.map((it, idx2) => `
        <button type="button" class="l2-node" style="--ri:${idx2}" data-sub-pick="${esc(it.k)}" data-tip="${esc(`${it.lbl}: ${fmt(it.n)}`)}" aria-pressed="false" aria-label="${esc(`${it.lbl} ${fmt(it.n)}`)}">
          <div class="l2-rbox">${subRingSVG(it.n, it.max, it.cls)}<span class="l2-n num">${esc(fmt(it.n))}</span></div>
          <span class="l2-lbl">${esc(it.lbl)}</span>
        </button>`).join('')}</div>`;
    } else if (key === '다') {
      titleStr = t('briefL2DaTitle');
      const m = App.mapOf(null);
      const cell = (c.seg && c.seg.cell) || m['칸'][5][1];
      const orgTotals = {};
      Object.values(S['종형']).forEach(v => { orgTotals[v['기관코드']] = (orgTotals[v['기관코드']] || 0) + 1; });
      const peers = c.activePeerOrgs || [];
      const orgs = ['EPOST'].concat(peers);
      const ringBtn = (info, riIdx = 0) => `<button type="button" class="l2-node" style="--ri:${riIdx}" data-sub-pick="org:${esc(info.org)}" data-tip="${esc(info.tip)}" aria-pressed="false" aria-label="${esc(info.tip)}">
        <div class="l2-rbox">${subRingSVG(info.noData ? 0 : info.openIds.length, info.max, info.cls)}<span class="l2-n num">${esc(info.nTxt)}</span></div>
        <span class="l2-lbl"><span aria-hidden="true">${info.ic}</span>${esc(txt.orgShort(info.org))}</span>
      </button>`;
      if (peers.length <= 3) {
        inner = `<div class="l2-rings" style="--cols:${Math.max(1, orgs.length)}">${orgs.map((o, i2) => ringBtn(orgNodeInfo(o, cell, orgTotals), i2)).join('')}</div>`
          + (peers.length === 0 ? `<p class="l2-empty">${esc(t('peerEmptyHint'))}</p>` : '');
      } else {
        // 상대 회사가 넷을 넘을 때는 우체국 고리 하나와 업권별(생명보험, 손해보험) 세로 목록으로 그린다
        const ours = orgNodeInfo('EPOST', cell, orgTotals);
        const groups = [
          { lbl: t('peerLifeGroup'), list: peers.filter(o => txt.orgSector(o) === 'life') },
          { lbl: t('peerNonLifeGroup'), list: peers.filter(o => txt.orgSector(o) === 'nonlife') },
        ].filter(g => g.list.length > 0);
        inner = `<div class="l2-org-many">
          <div>${ringBtn(ours, 0)}</div>
          <div class="l2-org-groups">${groups.map((g, gi) => `<div class="l2-org-grp" style="--ri:${gi + 1}">
            <div class="l2-org-gh">${esc(`${g.lbl} (${fmt(g.list.length)})`)}</div>
            <div class="l2-org-ul">${g.list.map(o => {
              const inf = orgNodeInfo(o, cell, orgTotals);
              return `<button type="button" class="l2-org-row" data-sub-pick="org:${esc(inf.org)}" data-tip="${esc(inf.tip)}" aria-pressed="false" aria-label="${esc(inf.tip)}">
                <span class="l2-org-nm"><span aria-hidden="true">${inf.ic}</span><span>${esc(txt.orgShort(inf.org))}</span></span>
                <span class="l2-org-n num">${esc(inf.nTxt)}</span>
              </button>`;
            }).join('')}</div>
          </div>`).join('')}</div>
        </div>`;
      }
    } else if (key === '라') {
      titleStr = t('briefL2RaTitle');
      const j = c.base['치료여정'];
      const steps = j['열'] || [];
      const activeSet = new Set(c.activeOrgs || txt.ORG_ORDER);
      const cols = (j['종형'] || []).filter(x => activeSet.has(orgCodeOfVid(x['종형ID'])));
      const ours = (j['종형'] || []).find(x => x['종형ID'] === c.baseId) || (j['종형'] || [])[0];
      inner = `<div class="bsteps">${steps.map((s, si) => {
        const n = ours ? (ours['합계'][s] || 0) : 0;
        const shownCols = cols.slice(0, 4);
        const orgSummary = shownCols.map(x => `${txt.orgShort(orgCodeOfVid(x['종형ID']))} ${x['합계'][s] || 0}`).join(', ');
        const tip = `${s}: ${orgSummary}`;
        return `<button type="button" class="bstep ${n > 0 ? 'is-gold' : 'is-empty'}" style="--ri:${si}" data-sub-pick="step:${esc(s)}" data-tip="${esc(tip)}" aria-pressed="false" aria-label="${esc(tip)}">
          <i class="bs-bg" aria-hidden="true"></i>
          <span class="bs-n num">${esc(fmt(n))}</span>
          <span class="bs-s">${esc(s)}</span>
        </button>`;
      }).join('')}</div>`;
    } else if (key === '마') {
      titleStr = t('briefL2MaTitle');
      const cnt = c.base['분류집계'] || {};
      const total = Math.max(1, Object.values(cnt).reduce((a, n) => a + n, 0));
      inner = `<div class="l2-rings" style="--cols:5">${S['분류'].map((cat, idx2) => {
        const n = cnt[cat] || 0;
        const cls = (idx2 === 1 || idx2 === 2) && n > 0 ? 'gold' : '';
        const tip = `${cat}: ${fmt(n)}${t('briefInsUnit')}`;
        return `<button type="button" class="l2-node" style="--ri:${idx2}" data-sub-pick="cat:${esc(cat)}" data-tip="${esc(tip)}" aria-pressed="false" aria-label="${esc(tip)}">
          <div class="l2-rbox">${subRingSVG(n, total, cls)}<span class="l2-n num">${esc(fmt(n))}</span></div>
          <span class="l2-lbl">${esc(cat)}</span>
        </button>`;
      }).join('')}</div>`;
    }

    return `<div class="blayer2${animate && App.motionOn() ? ' l2-open' : ''}" id="brief-l2" style="--ox:${ox}">
      <div class="l2-head">
        <h2 class="l2-title">${esc(titleStr)}</h2>
        <div class="l2-act">${goBtn}${closeBtn}</div>
      </div>
      ${inner}
    </div>`;
  }

  function stageInnerHTML(sel, c, animate, fromL2) {
    if (!sel) {
      return `<div class="bstage-l1${animate && fromL2 && App.motionOn() ? ' l1-open' : ''}">${medalsHTML(c)}</div>`;
    }
    return `<div class="bstage-l2">
      ${l2TabsHTML(c)}
      <div id="brief-l2-slot">${layer2HTML(sel, c, animate)}</div>
    </div>`;
  }

  function stageHTML(c) {
    const sel = c.st.sel.brief || null;
    lastStageSel = sel;
    return `<p class="concl b-concl">${esc(conclText(c))}</p>
      <section class="bstage${sel ? ' is-l2' : ' is-l1'}" id="brief-stage" aria-label="${esc(App.TAB_NAME.brief)}">
        ${stageInnerHTML(sel, c, false, false)}
      </section>`;
  }

  // ---------- 4. "문장으로 보기" 목록 모드 ----------
  function rowsHTML(c) {
    return brief(c).map(b => {
      const k = b['줄'];
      const nm = rowName(b);
      const tab = App.TAB_BY_NAME[b['갈곳']] || 'brief';
      const flag = b['원문대조'] ? ui.flag(b['원문대조글'] || ui.FLAG_TEXT) : '';
      const extra = k === '다' ? limitLine(c) : '';
      const n = String(ROW_NO[k]).padStart(2, '0');
      const goLabel = t('briefGoTabTpl', { tab: b['갈곳'] });
      return `<li class="lrow brow" data-pick="${esc(k)}" data-scope="${b['범위'] === '전체 고객군' ? 'all' : 'base'}">
        <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${n} ${nm}, ${b['범위']}`)}"></button>
        ${flag}
        <div class="bstrip selbar">
          <span class="no num" aria-hidden="true"><span class="num-0">${n[0]}</span>${n[1]}</span>
          <span class="bn">${esc(nm)}</span>
          ${ui.scope(b['범위'] === '전체 고객군' ? 'all' : 'base')}
          <span class="sp"></span>
          <span class="live">${ui.btn(goLabel, { sm: true, chev: true, attrs: `data-go="${tab}"${ROW_FOCUS[k] ? ` data-focus="${ROW_FOCUS[k]}"` : ''}` })}</span>
          <span class="bchev" aria-hidden="true">${ui.IC.chevR}</span>
        </div>
        <p class="btext">${esc(b['문장'])}</p>
        ${extra ? `<p class="bnow">${esc(extra)}</p>` : ''}
        <div class="bgo live">${ui.btn(goLabel, { sm: true, chev: true, attrs: `data-go="${tab}"${ROW_FOCUS[k] ? ` data-focus="${ROW_FOCUS[k]}"` : ''}` })}</div>
      </li>`;
    }).join('');
  }
  function rowsPanel(c) {
    const off = !c.isRef;
    return `<section class="panel brows" id="brief-rows" aria-labelledby="brief-rows-h">
      <div class="panel-h">
        <div><span class="k">${esc(t('briefListSub'))}</span><h2 id="brief-rows-h">${esc(t('briefListTitle'))}</h2></div>
      </div>
      ${off ? `<p class="brief-off">${esc(t('briefOffCondTpl', { cond: App.condSegOnly(), ref: refText(c) }))}</p>` : ''}
      <ol class="lrows" data-pick-group="brief">${rowsHTML(c)}</ol>
    </section>`;
  }

  // ---------- 5. 층 경로(1~3층)와 근거 기둥(1층 결론 한 줄, 2층 메달 요약, 3층 세부 요소 근거) ----------
  function subLabel(key, subKey) {
    if (!subKey) return '';
    if (subKey.startsWith('seg:')) {
      const [ri, ci] = subKey.slice(4).split('-').map(Number);
      const m = App.mapOf(null);
      const row = m['행'][ri], col = m['열'][ci];
      return row && col ? `${row['이름']}, ${col.lo}~${col.hi}${t('condAgeUnit')}` : subKey;
    }
    const REV_LBL = { 'rev:new': 'briefRevNew', 'rev:chg': 'briefRevChg', 'rev:end': 'briefRevEnd', 'rev:news': 'briefNewsNode' };
    if (subKey in REV_LBL) return t(REV_LBL[subKey]);
    if (subKey.startsWith('rev:')) return subKey.slice(4);
    if (subKey.startsWith('org:')) return txt.orgShort(subKey.slice(4));
    if (subKey.startsWith('step:')) return subKey.slice(5);
    if (subKey.startsWith('cat:')) return subKey.slice(4);
    return subKey;
  }

  function path(c) {
    const out = [App.TAB_NAME.brief];
    const k = c.st.sel.brief;
    if (!k) return out;
    const b = line(c, k);
    out.push(b ? rowName(b) : k);
    const sub = c.st.sub.brief;
    if (sub) out.push(subLabel(k, sub));
    return out;
  }

  function sec(titleStr, html, lo) { return `<div class="ev-sec${lo ? ' lo' : ''}">${titleStr ? `<h3>${esc(titleStr)}</h3>` : ''}${html}</div>`; }
  function pointItem(id) {
    const p = S['포인트'][id]; if (!p) return '';
    return `<li class="pt"><span class="tag">${esc(p['분류'])}</span> ${p['원문대조'] ? ui.flagText(p['원문대조글']) : ''}<p>${esc(p['문장'])}</p></li>`;
  }

  /** 1층 기본 근거 기둥: 아무것도 고르지 않았을 때는 결론 한 문장만 보인다 */
  function defaultEv(c) {
    const extra = !c.isRef ? `<p class="note">${esc(t('briefOffCondTpl', { cond: App.condSegOnly(), ref: refText(c) }))}</p>` : '';
    return {
      kicker: t('briefEvConclKicker'),
      title: App.TAB_NAME.brief,
      badges: [ui.scope('base')],
      body: sec('', `<p>${esc(conclText(c))}</p>${extra}`),
    };
  }

  /** 2층 메달 선택 시: 그 메달의 문장, 핵심 식, 전체 근거가 기둥 안에서 스크롤로 보인다(한 화면 300자 이하) */
  function pick(key, c) {
    const b = line(c, key); if (!b) return null;
    const v = b['값'] || {};
    const scopeB = ui.scope(b['범위'] === '전체 고객군' ? 'all' : 'base');
    const nm = rowName(b);
    const tab = App.TAB_BY_NAME[b['갈곳']];
    const goBtn = ui.btn(t('briefGoDetailTpl', { tab: b['갈곳'] }), {
      main: true, chev: true,
      attrs: `data-go="${tab}"${ROW_FOCUS[key] ? ` data-focus="${ROW_FOCUS[key]}"` : ''}`,
    });
    let body = sec('', `<p>${esc(b['문장'])}</p>${b['원문대조'] ? `<p>${ui.flagText(b['원문대조글'])}</p>` : ''}`);
    if (key === '가') {
      const lab = v['라벨별'] || {};
      const m = App.mapOf(null);
      const only = [];
      m['칸'].forEach((r, ri) => r.forEach((cell, ci) => {
        if (cell['라벨'] === '우리 간편만 열림') only.push({ r: m['행'][ri], col: m['열'][ci], cell });
      }));
      body += sec(t('briefEvCellsTitle'), ui.eq({
        total: { t: t('briefEqCellsTotal'), n: v['전체칸수'] },
        parts: MAP_LABELS.map(l => ({ t: l, n: lab[l] || 0 })),
      }));
      body += sec(t('briefEvOnlyTitle'), only.length ? `<ul class="evl">${only.map(o => {
        const rep = o.cell['대표'] ? txt.vkind(o.cell['대표']) : t('briefEvNoneWord');
        const peers = txt.ORG_ORDER.filter(x => x !== 'EPOST').map(x => `${txt.orgShort(x)} ${o.cell['회사'][x]}`).join(', ');
        return `<li><b>${esc(`${o.r['이름']}, ${o.col.lo}~${o.col.hi}${t('condAgeUnit')}`)}</b><br><span class="note">${esc(t('briefEvOnlyRepTpl', { rep, peers }))}</span></li>`;
      }).join('')}</ul>` : `<p>${esc(t('briefEvEmpty'))}</p>`);
      body += sec('', `<p class="note">${esc(t('briefEvMapScopeTpl', { sex: txt.sexText(m['성별']) }))}</p>`);
    } else if (key === '나') {
      const rv = S['개정변동'] || { '짝': [] };
      const nw = S['시장소식'] || {};
      const pairs = (rv['짝'] || []).map(p => `<li>${esc(t('briefEvRevPairTpl', { kind: txt.vkind(p['후']), n1: p['신설'], n2: p['변경'], n3: p['종료'] }))}</li>`).join('');
      const pairSum = (rv['짝'] || []).reduce((a, p) => a + p['신설'] + p['변경'] + p['종료'], 0);
      body += sec(t('briefEvRevTitle'), ui.eq({
        total: { t: t('briefEqRevTotal'), n: v['개정변동수'] },
        parts: [{ t: t('briefRevNew'), n: v['개정신설'] }, { t: t('briefRevChg'), n: v['개정변경'] }, { t: t('briefRevEnd'), n: v['개정종료'] }],
        tail: t('briefInsUnit'),
      }) + `<ul class="evl">${pairs}</ul><div class="nadd">${esc(t('briefEvNonAddPairTpl', { c: (rv['짝'] || []).length, sum: pairSum }))}</div>`);
      const cls = Object.entries(nw['분류별'] || {});
      body += sec(t('briefEvNewsTitleTpl', { week: nw['주차'] || '' }), ui.eq({
        total: { t: t('briefEqNewsTotal'), n: nw['건수'] },
        parts: cls.map(([a, n]) => ({ t: a, n })),
        tail: t('briefInsUnit'),
      }) + `<p class="note">${esc(nw['인용안내'] || '')}</p>`);
    } else if (key === '다') {
      const L = c.limit;
      const segs = L && L.table ? (L.table['구간'][c.st.sex] || []) : [];
      const gp = (c.base['포인트'] || []).filter(id => S['포인트'][id] && S['포인트'][id]['분류'] === '관문 차이');
      const lim = limitLine(c);
      body += sec(t('briefEvGateValTitle'), `<dl class="kv">
        <dt>${esc(t('briefEvAgeRange'))}</dt><dd class="num">${v['우리최저']}~${v['우리최고']}${esc(t('condAgeUnit'))}</dd>
        <dt>${esc(t('briefEvRefLimitTpl', { age: v['나이'] }))}</dt><dd class="num">${esc(v['주계약한도만원'])}${esc(t('briefWonUnit'))}</dd>
        <dt>${esc(t('briefEvGateDiff'))}</dt><dd class="num">${fmt(v['관문차이수'])}${esc(t('briefInsUnit'))}</dd>
        <dt>${esc(t('briefEvDiffStruct'))}</dt><dd class="num">${fmt(v['구조다름회사수'])}${esc(t('briefEvPlaceUnit'))}</dd></dl>`
        + (lim ? `<p class="note">${esc(lim)}</p>` : ''));
      body += sec(t('briefEvLimitTblTpl', { sex: txt.sexText(c.st.sex) }),
        segs.length ? `<dl class="kv">${segs.map(g => `<dt class="num">${g.lo}~${g.hi}${esc(t('condAgeUnit'))}</dt><dd class="num">${fmt(g.max)}${esc(t('briefWonUnit'))}${g.pend ? esc(t('briefEvPendSuffix')) : ''}</dd>`).join('')}</dl>` : `<p>${esc(t('briefEvNoLimit'))}</p>`);
      body += sec(`${esc(t('briefEvGateDiff'))} ${fmt(gp.length)}${esc(t('briefInsUnit'))}`,
        gp.length ? `<ul class="evl">${gp.map(pointItem).join('')}</ul>` : `<p>${esc(t('briefEvNoSimpQ'))}</p>`);
    } else if (key === '라') {
      const j = c.base['치료여정'];
      const steps = j ? (j['열'] || []) : [];
      const cau = c.base['단정주의'] || [];
      const hold = c.base['보류요약'] || {};
      body += sec(t('briefEvPairTitle'), ui.eq({
        total: { t: t('briefEqPairTotal'), n: v['공통담보쌍'] },
        parts: [{ t: t('briefEqCmp'), n: v['견준쌍'] }, { t: t('briefEqWait'), n: v['뺀비교쌍'] }],
        tail: t('briefEqPairUnit'),
      }) + ui.eq({
        total: { t: t('briefEqOurCov'), n: v['보유수'] },
        parts: steps.map(s => ({ t: s, n: v[s + '수'] })).concat(v['기타수'] ? [{ t: t('briefEqOther'), n: v['기타수'] }] : []),
        tail: t('briefStepUnit'),
      }) + `<div class="nadd">${esc(t('briefEvNonAddStep'))}</div>`);
      const holdRows = (hold['대분류'] || []).map(x => `<dt>${esc(x['대분류'])}</dt><dd class="num">${fmt(x['견준쌍'])}+${fmt(x['뺀쌍'])}${esc(t('briefEqPairUnit'))}</dd>`).join('');
      const why = hold['사유별'] || {};
      const whyT = Object.entries(why).map(([a, cnt2]) => `${a} ${fmt(cnt2)}`).join(', ');
      const whySum = Object.values(why).reduce((a, cnt2) => a + cnt2, 0);
      if (holdRows) {
        body += sec(t('briefEvHoldTitle'), `<dl class="kv">${holdRows}</dl>`
          + (whyT ? `<p class="note">${esc(t('briefEvHoldWhyTpl', { why: whyT, sum: fmt(whySum) }))}</p>` : ''));
      }
      if (cau.length) {
        body += sec(t('briefEvCautionTpl', { n: cau.length }),
          `<ul class="evl">${cau.map(x => `<li>${ui.verdict('diff')} <b>${esc(x['담보'])}</b><p>${esc(x['문장'])}</p></li>`).join('')}</ul>`);
      }
    } else if (key === '마') {
      const cnt = c.base['분류집계'] || {};
      const firsts = (c.base['먼저'] && c.base['먼저']['브리핑']) || [];
      const total = Object.values(cnt).reduce((a, n) => a + n, 0);
      body += sec(t('briefEvInsTitle'), ui.eq({
        total: { t: t('briefEqInsTotal'), n: total },
        parts: S['분류'].map(cat => ({ t: cat, n: cnt[cat] || 0 })),
        tail: t('briefInsUnit'),
      }) + `<p class="note">${esc(t('briefEvInsSkipTpl', { n: fmt((c.base['뺀포인트'] || []).length) }))}</p>`);
      if (firsts.length) body += sec(t('briefEvFirstTpl', { n: firsts.length }), `<ul class="evl">${firsts.map(pointItem).join('')}</ul>`);
    }
    body += sec('', goBtn, true);
    return { kicker: `${String(ROW_NO[key]).padStart(2, '0')} ${b['범위']}`, title: nm, badges: [scopeB], body };
  }

  /** 3층 세부 요소 선택 시: 고른 요소 하나의 문장, 식, 근거만 보인다 */
  function pickSub(key, subKey, c) {
    const b = line(c, key); if (!b) return null;
    const nm = rowName(b);
    const tab = App.TAB_BY_NAME[b['갈곳']];
    const goBtn = ui.btn(t('briefGoDetailTpl', { tab: b['갈곳'] }), {
      main: true, chev: true,
      attrs: `data-go="${tab}"${ROW_FOCUS[key] ? ` data-focus="${ROW_FOCUS[key]}"` : ''}`,
    });

    if (subKey.startsWith('seg:')) {
      const [ri, ci] = subKey.slice(4).split('-').map(Number);
      const m = App.mapOf(null);
      const row = m['행'][ri], col = m['열'][ci], cell = (m['칸'][ri] || [])[ci];
      if (!row || !col || !cell) return null;
      const patch = App.segPatch(m, ri, ci, c.st);
      const same = patch ? App.samePatch(patch, c.st) : true;
      const go = cell['관문만수집'] || [];
      const shownOrgs = (c.activeOrgs || txt.ORG_ORDER).filter(o => o in (cell['회사'] || {}));
      const orgBlock = shownOrgs.length <= 4
        ? `<p>${ui.swatch(cell['라벨'])} <b style="font-weight:600">${esc(cell['라벨'])}</b>${cell['보조'] ? ` (${esc(cell['보조'])})` : ''}. ${esc(shownOrgs.map(o => `${txt.orgShort(o)} ${cell['회사'][o]}`).join(', '))}.</p>`
        : `<p>${ui.swatch(cell['라벨'])} <b style="font-weight:600">${esc(cell['라벨'])}</b>${cell['보조'] ? ` (${esc(cell['보조'])})` : ''}.</p><dl class="kv">${shownOrgs.map(o => `<dt>${esc(txt.orgShort(o))}</dt><dd>${esc(cell['회사'][o])}</dd>`).join('')}</dl>`;
      const actBlock = same
        ? `<p class="note">${esc(t('briefSegSameNote'))}</p>`
        : `<p class="note">${esc(t('briefSegWillChangeTpl', { target: txt.josa(App.segPatchText(patch), '으로') }))}</p>`
          + ui.btn(t('briefApplySegBtn'), { sm: true, attrs: `data-act="brief-apply-seg" data-ri="${ri}" data-ci="${ci}"` });
      const pts = (cell['관문포인트'] || []).map(pointItem).join('');
      let body = sec('', orgBlock
        + (go.length ? `<p class="note">${esc(go.map(g => `${g['이름']}: ${g['안내'] || ''}`).join(', '))}</p>` : '')
        + actBlock);
      if (pts) body += sec('', `<ul class="evl">${pts}</ul>`);
      body += sec('', goBtn, true);
      return { kicker: nm, title: subLabel(key, subKey), badges: [ui.scope('all')], body };
    }

    if (subKey === 'rev:news') {
      const nw = S['시장소식'] || {};
      const cls = Object.entries(nw['분류별'] || {});
      let body = sec(t('briefEvNewsTitleTpl', { week: nw['주차'] || '' }),
        ui.eq({ total: { t: t('briefNewsNode'), n: nw['건수'] }, parts: cls.map(([a, n]) => ({ t: a, n })) })
        + `<p class="note">${esc(nw['인용안내'] || '')}</p>`);
      body += sec('', goBtn, true);
      return { kicker: nm, title: t('briefNewsNode'), badges: [ui.scope('all')], body };
    }

    if (subKey.startsWith('rev:')) {
      const kind = subLabel(key, subKey);
      const rv = S['개정변동'] || { '짝': [] };
      const pairs = (rv['짝'] || []).map(p => `<li>${esc(t('briefEvRevPairTpl', { kind: txt.vkind(p['후']), n1: p['신설'], n2: p['변경'], n3: p['종료'] }))}</li>`).join('');
      const pairSum = (rv['짝'] || []).reduce((a, p) => a + p['신설'] + p['변경'] + p['종료'], 0);
      let body = sec(kind, `<ul class="evl">${pairs}</ul><div class="nadd">${esc(t('briefEvNonAddPairTpl', { c: (rv['짝'] || []).length, sum: pairSum }))}</div>`);
      body += sec('', goBtn, true);
      return { kicker: nm, title: kind, badges: [ui.scope('all')], body };
    }

    if (subKey.startsWith('org:')) {
      const org = subKey.slice(4);
      const m = App.mapOf(null);
      const cell = (c.seg && c.seg.cell) || m['칸'][5][1];
      const stName = (cell['회사'] && cell['회사'][org]) || '';
      const why = txt.stateWhy(org, stName);
      const openIds = (cell['열린종형'] && cell['열린종형'][org]) || [];
      let body = sec('', `<p><b style="font-weight:600">${esc(txt.orgShort(org))}</b>: ${esc(stName)}${why ? `. ${esc(why)}.` : '.'}</p>`);
      if (openIds.length) {
        body += sec(t('briefEvGateOpenList'), `<p>${esc(openIds.map(id => txt.vname(id)).join(', '))}</p>`);
      }
      if (org === 'EPOST') {
        const L = c.limit;
        const segs = L && L.table ? (L.table['구간'][c.st.sex] || []) : [];
        body += sec(t('briefEvLimitTblTpl', { sex: txt.sexText(c.st.sex) }),
          segs.length ? `<dl class="kv">${segs.map(g => `<dt class="num">${g.lo}~${g.hi}${esc(t('condAgeUnit'))}</dt><dd class="num">${fmt(g.max)}${esc(t('briefWonUnit'))}${g.pend ? esc(t('briefEvPendSuffix')) : ''}</dd>`).join('')}</dl>` : `<p>${esc(t('briefEvNoLimit'))}</p>`);
      } else {
        const gp = (c.base['포인트'] || []).filter(id => S['포인트'][id] && S['포인트'][id]['분류'] === '관문 차이' && (S['포인트'][id]['문장'] || '').includes(txt.orgShort(org)));
        if (gp.length) body += sec('', `<ul class="evl">${gp.map(pointItem).join('')}</ul>`);
      }
      body += sec('', goBtn, true);
      return { kicker: nm, title: txt.orgShort(org), badges: [ui.scope(c.seg && c.seg.cell ? 'now' : 'base')], body };
    }

    if (subKey.startsWith('step:')) {
      const step = subKey.slice(5);
      const j = c.base['치료여정'];
      const activeSet = new Set(c.activeOrgs || txt.ORG_ORDER);
      const cols = (j['종형'] || []).filter(x => activeSet.has(orgCodeOfVid(x['종형ID'])));
      const ours = (j['종형'] || []).find(x => x['종형ID'] === c.baseId) || (j['종형'] || [])[0];
      const byMajor = Object.entries((ours && ours['칸']) || {}).map(([mj, obj]) => ({ t: mj, n: obj[step] || 0 })).filter(x => x.n > 0);
      const orgNote = cols.length <= 4
        ? `<p class="note">${esc(cols.map(x => `${txt.orgShort(orgCodeOfVid(x['종형ID']))} ${fmt(x['합계'][step] || 0)}`).join(', '))}</p>`
        : `<dl class="kv" style="margin-top:8px">${cols.map(x => `<dt>${esc(txt.orgShort(orgCodeOfVid(x['종형ID'])))}</dt><dd class="num">${fmt(x['합계'][step] || 0)}</dd>`).join('')}</dl>`;
      let body = sec(step, (byMajor.length ? ui.eq({ total: { t: step, n: ours['합계'][step] || 0 }, parts: byMajor }) : `<p>${esc(t('briefEvEmpty'))}</p>`)
        + orgNote);
      const cau = c.base['단정주의'] || [];
      if (cau.length) {
        body += sec(t('briefEvCautionTpl', { n: cau.length }),
          `<ul class="evl">${cau.map(x => `<li>${ui.verdict('diff')} <b>${esc(x['담보'])}</b><p>${esc(x['문장'])}</p></li>`).join('')}</ul>`);
      }
      body += sec('', goBtn, true);
      return { kicker: nm, title: step, badges: [ui.scope('base')], body };
    }

    if (subKey.startsWith('cat:')) {
      const cat = subKey.slice(4);
      let body = '';
      if (cat === '개정 검토 후보') {
        const groups = c.base['개정검토'] || [];
        body += sec(cat, groups.length
          ? `<dl class="kv">${groups.map(g => `<dt>${esc(g['중분류'])}</dt><dd class="num">${fmt(g['담보수'])}${t('briefInsUnit')}</dd>`).join('')}</dl>`
          : `<p>${esc(t('briefEvEmpty'))}</p>`);
      } else {
        const pts = (c.base['포인트'] || []).filter(id => S['포인트'][id] && S['포인트'][id]['분류'] === cat);
        body += sec(cat, pts.length ? `<ul class="evl">${pts.map(pointItem).join('')}</ul>` : `<p>${esc(t('briefEvEmpty'))}</p>`);
      }
      body += sec('', goBtn, true);
      return { kicker: nm, title: cat, badges: [ui.scope('base')], body };
    }

    return null;
  }

  // ---------- 6. 그리기와 층 전환 반응 ----------
  function render(body, c) {
    if (c.aside) c.aside.innerHTML = headAsideHTML();
    body.innerHTML = viewMode === 'medal' ? stageHTML(c) : rowsPanel(c);
    bind(body, c);
  }

  function onLayer(body, c, animate) {
    if (viewMode !== 'medal') return;
    const stage = body.querySelector('#brief-stage');
    if (!stage) return;
    const sel = c.st.sel.brief || null;
    const prev = lastStageSel;
    if (sel === prev) return;
    lastStageSel = sel;
    stage.classList.toggle('is-l2', !!sel);
    stage.classList.toggle('is-l1', !sel);
    if (!sel || !prev) {
      stage.innerHTML = stageInnerHTML(sel, c, animate, !!prev);
      if (animate && App.motionOn()) ui.drawRings(stage);
      return;
    }
    const slot = stage.querySelector('#brief-l2-slot');
    if (slot) {
      slot.innerHTML = layer2HTML(sel, c, animate);
      if (animate && App.motionOn()) ui.drawRings(slot);
    } else {
      stage.innerHTML = stageInnerHTML(sel, c, animate, false);
    }
  }

  function bind(body, c) {
    const aside = c.aside;
    if (aside && !aside._b) {
      aside._b = true;
      aside.addEventListener('click', e => {
        if (e.target.closest('[data-act="brief-mode"]')) {
          viewMode = viewMode === 'medal' ? 'list' : 'medal';
          const cc = App.ctx();
          render(body, Object.assign(cc, { aside }));
          const curSel = App.state.sel.brief;
          if (curSel != null) App.select(curSel, { open: false, reveal: false, animate: false, push: false });
          if (viewMode === 'medal' && App.motionOn()) ui.drawRings(body);
          return;
        }
        if (e.target.closest('[data-act="brief-copy"]')) {
          const cc = App.ctx();
          const cols = t('briefCopyCols').split(',');
          App.copyRows(cols, brief(cc).map(b => [`(${b['줄']})`, rowName(b), b['범위'], b['문장'] + (b['원문대조'] ? ` [${b['원문대조글']}]` : ''), b['갈곳']]), { title: t('briefCopyTitle') });
        }
      });
    }
    if (!body._b) {
      body._b = true;
      // 이미 고른 메달을 다시 누르면(3층이 아닐 때) 2층을 닫아 1층으로 올라간다
      body.addEventListener('click', e => {
        const m = e.target.closest('.bmedal[data-pick]');
        if (m && !e.target.closest('.live')) {
          const k = m.dataset.pick;
          if (App.state.sel.brief === k && App.state.sub.brief == null) {
            e.stopPropagation();
            App.unselect();
          }
        }
      }, true);
      // 메달 사이에서 좌우 방향키, Home, End 로 초점을 옮긴다
      body.addEventListener('keydown', e => {
        const hit = e.target.closest && e.target.closest('.bmedal > .lrow-hit');
        if (!hit) return;
        const hits = Array.from(body.querySelectorAll('.bmedal > .lrow-hit'));
        const idx = hits.indexOf(hit);
        if (idx < 0 || !hits.length) return;
        let next = -1;
        if (e.key === 'ArrowRight') next = (idx + 1) % hits.length;
        else if (e.key === 'ArrowLeft') next = (idx + hits.length - 1) % hits.length;
        else if (e.key === 'Home') next = 0;
        else if (e.key === 'End') next = hits.length - 1;
        if (next >= 0) { e.preventDefault(); hits[next].focus(); }
      });
    }
    if (!document._briefApplyBound) {
      document._briefApplyBound = true;
      document.addEventListener('click', e => {
        const ab = e.target.closest('[data-act="brief-apply-seg"]');
        if (!ab) return;
        const patch = App.segPatch(App.mapOf(null), +ab.dataset.ri, +ab.dataset.ci, App.state);
        if (!patch) return;
        App.set(patch);
        App.toast(t('briefSegChangedToastTpl', { sum: App.condSummary() }));
      });
    }
  }

  function update(body, c) {
    render(body, c);
    if (App.motionOn() && viewMode === 'medal') ui.drawRings(body);
    return true;
  }

  let enterTimer = 0;
  function enter() {
    const view = document.getElementById('view-brief');
    if (!view || !App.motionOn()) return;
    clearTimeout(enterTimer);
    view.classList.remove('b-enter');
    void view.offsetWidth;
    view.classList.add('b-enter');
    enterTimer = setTimeout(() => view.classList.remove('b-enter'), 560);
  }

  return { id: 'brief', kicker: t('briefKicker'), render, update, onLayer, path, defaultEv, pick, pickSub, enter };
})());
