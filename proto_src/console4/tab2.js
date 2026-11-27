/* 탭 2 고객군과 시장: 안개 위 네 줄 시간축(2px 선, 12px 열림 전환 눈금) + 24개 고리 마디(64px) + 오른쪽 28% 읽기 영역.
   모든 화면 문구는 core.js 의 COPY(App.t)에서 읽고, 수와 문장은 sales.json 에서 읽으며 비교 범위 교집합만 센다. */
App.registerTab((function () {
  'use strict';
  const { ui, txt } = App;
  const { esc, fmt } = ui;
  const S = App.S;
  const t = (k, v) => App.t(k, v);

  const LABELS = S['라벨'];
  const CATS = S['분류'];
  const NEWS = S['시장소식'];
  const REV = S['개정변동'];
  const ST_IC = {
    '열림': ui.IC.open,
    '일부 나이만 열림': ui.IC.open,
    '닫힘': ui.IC.lock,
    '심사로 확인': ui.IC.check,
    '나이 자료 없음': ui.IC.hatch,
    '질문 자료 없음': ui.IC.hatch,
  };

  let revSub = 'rev';

  const REN_KEY = r => (r == null ? 'a' : r === '갱신' ? 'g' : 'n');
  const keyOf = (ri, ci) => `m${REN_KEY(App.state.renewal)}${ri}-${ci}`;
  const parseKey = k => {
    const m = /^m([agn])(\d+)-(\d+)$/.exec(k || '');
    return m && m[1] === REN_KEY(App.state.renewal) ? { ri: +m[2], ci: +m[3] } : null;
  };
  const vk = vid => (vid ? txt.vkind(vid) : '');
  const colText = col => `${col.lo}~${col.hi}${t('condAgeUnit')}`;
  const timeShort = r => (r.since === 5 ? t('mkTimeOver5') : r['이름'].replace(/^(입원|수술만)\s*/, '').replace(/\s*전$/, ''));
  const cellAt = (map, ri, ci) => (map['칸'][ri] || [])[ci] || null;

  ui.registerLegend('market', 'mkLegendTitle', () => `<dl class="legend">
      <dt><i class="cq m-ours" aria-hidden="true"></i></dt><dd>${esc(t('mkLgWorse'))}</dd>
      <dt><i class="cq m-only" aria-hidden="true"></i></dt><dd>${esc(t('mkLgGold'))}</dd>
      <dt><i class="cq m-both" aria-hidden="true"></i></dt><dd>${esc(t('mkLgBoth'))}</dd>
      <dt><i class="cq m-all" aria-hidden="true"></i></dt><dd>${esc(t('mkLgAllClosed'))}</dd>
      <dt>${ui.IC.hatch}</dt><dd>${esc(t('mkLgDash'))}</dd>
      <dt>${ui.IC.open}</dt><dd>${esc(t('mkLgArc'))}</dd>
      <dt>${ui.IC.arrow}</dt><dd>${esc(t('mkLgAxis'))}</dd>
      <dt>${ui.IC.pin}</dt><dd>${esc(t('mkLgRed'))}</dd>
      <dt>${ui.flagText(t('flagShort'))}</dt><dd>${esc(t('lgFlag'))}</dd>
    </dl>`);

  function renOpts() {
    return [
      { v: null, t: t('condRenAll') },
      { v: '갱신', t: t('condRenRenew') },
      { v: '비갱신', t: t('condRenNon') },
    ];
  }
  function renLabel(r) {
    return r == null ? t('condRenAll') : r === '갱신' ? t('condRenRenew') : r === '비갱신' ? t('condRenNon') : r;
  }

  function tally(map) {
    const lab = map['라벨별'] || {};
    let total = 0;
    map['칸'].forEach(r => { total += r.length; });
    const gap = {};
    const closed = {};
    let closedCells = 0;
    map['칸'].forEach(r => r.forEach(c => {
      (c['자료없음'] || []).forEach(o => { gap[o] = gap[o] || { n: 0, state: c['회사'][o] }; gap[o].n++; });
      if (c['닫힌사유'] && c['닫힌사유'].length) { closedCells++; c['닫힌사유'].forEach(x => { closed[x] = (closed[x] || 0) + 1; }); }
    }));
    return { lab, total, gap, closed, closedCells };
  }

  /** 지도의 (이력 종류 x 나이 열) 네 줄과 여섯 마디 모형을 만든다(나이 열이 우체국 경계 2개로 고정이라 늘 4줄 x 6마디 = 24개) */
  function buildRowsModel(map) {
    const hospPeriods = map['행'].map((r, i) => ({ r, i })).filter(x => x.r['종류'] === '입원');
    const surgPeriods = map['행'].map((r, i) => ({ r, i })).filter(x => x.r['종류'] === '수술만');
    const cols = map['열'] || [];
    const rows = [];
    [
      { kind: '입원', kindLabel: t('mkGroupHosp'), periods: hospPeriods },
      { kind: '수술만', kindLabel: t('mkGroupSurg'), periods: surgPeriods },
    ].forEach(g => {
      cols.forEach((col, ci) => {
        const items = g.periods.map(p => ({ ri: p.i, ci, period: p.r, col, cell: cellAt(map, p.i, ci) }));
        const oursOpenCnt = items.filter(x => x.cell && x.cell['회사'] && x.cell['회사'].EPOST === '열림').length;
        rows.push({
          rowIdx: rows.length,
          kind: g.kind,
          kindLabel: g.kindLabel,
          ci,
          col,
          label: `${g.kindLabel} ${col.lo}~${col.hi}${t('condAgeUnit')}`,
          items,
          oursOpenCnt,
        });
      });
    });
    return { hospPeriods, cols, rows };
  }

  // 원호 구간 [f0, f1] 의 SVG 경로(0=12시 방향, 시계방향)
  function arcSegPath(r, f0, f1) {
    const span = Math.max(0, Math.min(1, f1) - Math.max(0, f0));
    if (span <= 0.0005) return '';
    if (span >= 0.999) {
      return `M 0 ${-r} A ${r} ${r} 0 1 1 0 ${r} A ${r} ${r} 0 1 1 0 ${-r}`;
    }
    const a0 = f0 * 2 * Math.PI - Math.PI / 2;
    const a1 = f1 * 2 * Math.PI - Math.PI / 2;
    const x0 = +(r * Math.cos(a0)).toFixed(2), y0 = +(r * Math.sin(a0)).toFixed(2);
    const x1 = +(r * Math.cos(a1)).toFixed(2), y1 = +(r * Math.sin(a1)).toFixed(2);
    const large = span > 0.5 ? 1 : 0;
    return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`;
  }

  function cellRingSVG(cc) {
    const r = 28;
    const tot = Math.max(1, cc.total);
    const fConf = cc.total > 0 ? cc.openConfirmed / tot : 0;
    const fPart = cc.total > 0 ? cc.partial / tot : 0;
    const fGate = cc.total > 0 ? cc.gateOnly / tot : 0;
    const fUnk = cc.total > 0 ? cc.unknown / tot : 0;

    const pConf = arcSegPath(r, 0, fConf);
    const pPart = arcSegPath(r, fConf, fConf + fPart);
    const pGate = arcSegPath(r, fConf + fPart, fConf + fPart + fGate);

    // 모르는 상대 비율은 바깥 트랙 끝 구간에 빗금 눈금으로 표시
    let unkTicks = '';
    if (fUnk > 0.001) {
      const N = 32;
      const startF = 1 - fUnk;
      const ls = [];
      for (let i = 0; i < N; i++) {
        const fi = (i + 0.5) / N;
        if (fi < startF - 0.005) continue;
        const a = fi * 2 * Math.PI - Math.PI / 2;
        const a2 = a + 0.07;
        ls.push(`<line x1="${((r - 3) * Math.cos(a)).toFixed(1)}" y1="${((r - 3) * Math.sin(a)).toFixed(1)}" x2="${((r + 3) * Math.cos(a2)).toFixed(1)}" y2="${((r + 3) * Math.sin(a2)).toFixed(1)}" stroke-width="1.1"/>`);
      }
      if (ls.length) unkTicks = `<g class="mkr-unk">${ls.join('')}</g>`;
    }

    // 우리만 열림일 때 색과 독립된 안쪽 2px 이중 고리
    const innerDouble = cc.state === 'only'
      ? '<circle class="mkr-dbl" r="17.5" fill="none" stroke-width="2"/>'
      : '';
    // 일부 나이로만 열린 칸 표지(위쪽 작은 반원 점)
    const partialBadge = cc.partialOnly
      ? '<path class="mkr-part-mk" d="M-4 -22 L0 -17 L4 -22 Z"/>'
      : '';

    return `<svg viewBox="-34 -34 68 68" aria-hidden="true" focusable="false">
      <g class="mkr-diag-bg" stroke-width="2.8"><line x1="-31" y1="-31" x2="-24" y2="-24"/><line x1="31" y1="-31" x2="24" y2="-24"/><line x1="-31" y1="31" x2="-24" y2="24"/><line x1="31" y1="31" x2="24" y2="24"/></g>
      <g class="mkr-diag" stroke-width="1.4"><line x1="-31" y1="-31" x2="-24" y2="-24"/><line x1="31" y1="-31" x2="24" y2="-24"/><line x1="-31" y1="31" x2="-24" y2="24"/><line x1="31" y1="31" x2="24" y2="24"/></g>
      <circle class="mkr-disc" r="22.5"/>
      <circle class="mkr-sel-ring" r="22.5" fill="none" stroke-width="2"/>
      ${innerDouble}
      <circle class="mkr-trk" r="${r}" fill="none" stroke-width="1.3"/>
      ${unkTicks}
      ${pConf ? `<path class="mkr-arc mkr-arc-conf" d="${pConf}" fill="none" stroke-width="4.2" pathLength="1"/>` : ''}
      ${pPart ? `<path class="mkr-arc mkr-arc-part" d="${pPart}" fill="none" stroke-width="2.1" pathLength="1"/>` : ''}
      ${pGate ? `<path class="mkr-arc mkr-arc-gate" d="${pGate}" fill="none" stroke-width="3.6" stroke-dasharray="3.2 2.4"/>` : ''}
      ${partialBadge}
    </svg>`;
  }

  function syncMarketHot(aimEl) {
    const board = document.getElementById('mk-grid');
    if (!board) return;
    const hotR = aimEl && aimEl.closest && aimEl.closest('#mk-grid') && aimEl.dataset.gridR != null ? +aimEl.dataset.gridR : -1;
    const hotC = aimEl && aimEl.closest && aimEl.closest('#mk-grid') && aimEl.dataset.gridC != null ? +aimEl.dataset.gridC : -1;
    const selKey = App.state.sel.market;
    const selParsed = selKey != null ? parseKey(selKey) : null;
    board.querySelectorAll('.mk-tch[data-col]').forEach(el => {
      el.classList.toggle('is-hot', +el.dataset.col === hotC);
    });
    board.querySelectorAll('.mk-trow[data-row]').forEach(el => {
      const r = +el.dataset.row;
      el.classList.toggle('is-hot', r === hotR);
      const hasSel = !!(selParsed && el.querySelector(`[data-pick="${CSS.escape(selKey)}"]`));
      el.classList.toggle('has-row-sel', hasSel);
    });
  }

  function renderStage(center, c) {
    const map = App.mapOf(c.st.renewal);
    const gm = buildRowsModel(map);
    const basisTxt = c.seg && c.seg.sexNote ? c.seg.sexNote : t('mkMaleBasis');

    const timeHeads = `<div class="mk-thead" data-main-axis="1">
      <span class="mk-basis">${esc(basisTxt)}</span>
      <div class="mk-tcols" aria-hidden="true">
        ${gm.hospPeriods.map((p, cIdx) => `<span class="mk-tch" data-col="${cIdx}">${esc(timeShort(p.r))}</span>`).join('')}
      </div>
    </div>`;

    const rowsHTML = gm.rows.map((rowObj, rIdx) => {
      const prevRow = gm.rows[rIdx - 1];
      const kindBreak = prevRow && prevRow.kind !== rowObj.kind;
      const trackParts = [];
      rowObj.items.forEach((it, cIdx) => {
        const cell = it.cell;
        const cc = c.cellCounts(cell);
        if (cIdx > 0) {
          const prevCell = rowObj.items[cIdx - 1].cell;
          const prevOpen = !!(prevCell && prevCell['회사'] && prevCell['회사'].EPOST === '열림');
          const curOpen = cc.oursOpen;
          const bothOpen = prevOpen && curOpen;
          const openTransition = !prevOpen && curOpen;
          trackParts.push(`<span class="mk-seg ${bothOpen ? 'is-solid' : 'is-dash'}" style="--sd:${rIdx * 36 + cIdx * 14}ms" aria-hidden="true">${openTransition ? '<i class="mk-trans-tk"></i>' : ''}</span>`);
        }
        const stateCls = 'st-' + cc.state;
        const isNoData = cc.state === 'unknown';
        const numStr = (isNoData && cc.total > 0 && cc.unknown === cc.total) ? t('mkUnknownSym') : fmt(cc.openAny);
        const needFlag = cell && cell['라벨'] === '우리 간편만 열림';
        const partNote = cc.partialOnly ? ` (${t('mkPartialOnlyMark')})` : '';
        const noDataWhy = isNoData
          ? c.activeOrgs.map(o => txt.stateWhy(o, cell && cell['회사'] && cell['회사'][o])).filter(Boolean)[0] || t('scopeNoData')
          : '';
        const tipTitle = `${App.rowLabel(it.period)}, ${colText(it.col)}`;
        const tipSub = isNoData
          ? noDataWhy
          : `${txt.orgShort('EPOST')} ${App.label(cc.oursState)}${partNote}, ${t('mkEvOpenPeersHeadTpl', { open: fmt(cc.openAny), total: fmt(cc.total) })}`;
        const chipKind = cc.state === 'only' ? 'only' : cc.state === 'worse' ? 'worse' : cc.state === 'both' ? 'same' : cc.state === 'unknown' ? 'unknown' : 'none';
        const tip = `${tipTitle}: ${App.label(cell['라벨'])}${partNote}, ${t('mkEvOpenPeersHeadTpl', { open: fmt(cc.openAny), total: fmt(cc.total) })}`;
        const pk = keyOf(it.ri, it.ci);
        trackParts.push(`<button type="button" class="mk-ring ${stateCls}" data-pick="${esc(pk)}" data-toggle="1" data-aim="circle"${isNoData ? ' data-nodata="1" aria-disabled="true"' : ''} data-grid-r="${rIdx}" data-grid-c="${cIdx}" data-tip="${esc(tip)}" data-tip-title="${esc(tipTitle)}" data-tip-sub="${esc(tipSub)}" data-tip-chip="${chipKind}" aria-pressed="false" aria-label="${esc(tip)}" style="--d:${(rIdx * 4 + cIdx) * 10}ms">
          ${needFlag ? ui.flag() : ''}
          ${cellRingSVG(cc)}
          <span class="mk-rn num">${esc(numStr)}</span>
        </button>`);
      });

      return `<div class="mk-trow${kindBreak ? ' is-break' : ''}" data-row="${rIdx}">
        <div class="mk-rh">
          <span class="mk-rh-nm">${esc(rowObj.label)}</span>
          <span class="mk-rh-cnt num">${esc(`${fmt(rowObj.oursOpenCnt)}/${fmt(rowObj.items.length)}`)}</span>
        </div>
        <div class="mk-track" data-scrub-row="1">${trackParts.join('')}</div>
      </div>`;
    }).join('');

    const missBanner = c.seg && !c.seg.cell && c.seg.reason
      ? `<p class="mk-miss-note">${esc(t('mkMissingSegWhyTpl', { why: c.seg.reason }))}</p>`
      : '';

    center.innerHTML = `<div class="mkc-stage" id="mk-map">
      <div class="mk-top-ctrl">
        <div class="mk-ren-box">
          <span class="mk-ren-lb">${esc(t('mkRenLabel'))}</span>
          <span data-slot="mk-ren"></span>
        </div>
      </div>
      ${missBanner}
      <div class="mk-axis-board" id="mk-grid">
        ${timeHeads}
        <div class="mk-trows">${rowsHTML}</div>
      </div>
    </div>`;

    const slot = center.querySelector('[data-slot="mk-ren"]');
    if (slot) {
      slot.replaceWith(ui.chevSel({
        label: t('mkRenAria'),
        options: renOpts(),
        value: c.st.renewal,
        w: '54px',
        onChange: v => App.set({ renewal: v }),
      }));
    }
    syncMarketHot(null);
  }

  function enter(center) {
    const g = center && center.querySelector('#mk-grid');
    if (!g || !App.motionOn()) return;
    g.classList.remove('mk-anim'); void g.offsetWidth; g.classList.add('mk-anim');
    clearTimeout(g._t); g._t = setTimeout(() => g.classList.remove('mk-anim'), 700);
  }

  // ---------- 읽기 영역과 [표로 보기] / [개정과 시장] / [문장으로 보기] 창 ----------
  function sec(title, html, lo) { return `<div class="ev-sec${lo ? ' lo' : ''}">${title ? `<h3>${title}</h3>` : ''}${html}</div>`; }
  function det(summary, html, open) {
    return `<details class="zr-det"${open ? ' open' : ''}><summary><span>${esc(summary)}</span>${ui.IC.chevD}</summary><div class="zr-det-b">${html}</div></details>`;
  }

  function conclFullText(c) {
    const map = App.mapOf(c.st.renewal);
    if (c.st.renewal == null) {
      const b = ((c.base && c.base['브리핑']) || []).find(x => x['줄'] === '가');
      if (b) return b['문장'];
    }
    const tl = tally(map);
    return `${renLabel(c.st.renewal)}: ${LABELS.filter(l => tl.lab[l]).map(l => `${App.label(l)} ${fmt(tl.lab[l])}${t('mkClosedUnit')}`).join(', ')}.`;
  }

  function conclusion(c) {
    return { text: App.firstSentence(conclFullText(c)), flag: '' };
  }

  function pointLi(id) {
    const p = S['포인트'][id]; if (!p) return '';
    const hd = p['머리말'] != null ? S['글'][p['머리말']] : '';
    const docs = (p['근거'] || []).map(g => ui.tag(`${txt.orgShort((txt.vinfo(g['종형ID']) || {})['기관코드'] || '')} ${txt.pageText(g['문서'], g['쪽'])}`, '', 'doc')).join(' ');
    return `<li><span class="tag">${esc(p['세부이름'] || p['분류'])}</span> ${p['원문대조'] ? ui.flagText(p['원문대조글']) : ''}<p>${esc(p['문장'])}</p>${docs ? `<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px">${docs}</div>` : ''}${hd ? `<p class="note">${esc(hd)}</p>` : ''}</li>`;
  }

  function formatSpans(spans) {
    if (!Array.isArray(spans) || !spans.length) return '';
    return spans.map(([lo, hi]) => (lo === hi ? `${lo}` : `${lo}~${hi}`)).join(', ');
  }

  function cellSpec(c, ri, ci) {
    const map = App.mapOf(c.st.renewal);
    const cell = cellAt(map, ri, ci);
    if (!cell) return null;
    const row = map['행'][ri], col = map['열'][ci];
    const now = !!(c.seg && c.seg.cell && c.seg.ri === ri && c.seg.ci === ci);
    const pSet = new Set(c.activePeerOrgs);
    const cc = c.cellCounts(cell);

    const openCodes = c.filterScopeCodes(cell['열린상대코드']);
    const partialCodes = c.filterScopeCodes(cell['일부열린상대코드']);
    const gateOnly = (cell['관문만수집'] || []).filter(x => c.peerScope === 'all' || pSet.has(x['기관코드']));

    const oursState = cc.oursState;
    const oursOpenIds = (cell['열린종형'] && cell['열린종형'].EPOST) || [];
    const subNotes = [];
    if (cell['보조']) subNotes.push(cell['보조']);
    if (cell['닫힌사유'] && cell['닫힌사유'].length) subNotes.push(`${t('scopeClosedWhy')}: ${cell['닫힌사유'].join(', ')}`);

    const openAllNames = openCodes.concat(partialCodes).map(txt.orgShort);
    const openSummary = openAllNames.length ? txt.peerNamesEtc(openAllNames, 3) : t('mkRevNone');

    const partialSpansHTML = partialCodes.length
      ? `<p class="note" style="margin-top:4px"><b>${esc(t('mkPartialHeadTpl', { n: fmt(partialCodes.length) }))}:</b> ${esc(partialCodes.map(code => t('mkPartialSpanTpl', { org: txt.orgShort(code), spans: formatSpans((cell['일부열린나이'] || {})[code]) })).join(', '))}</p>`
      : '';

    const scopedPts = (cell['관문포인트'] || []).filter(id => {
      const p = S['포인트'][id];
      return p && (c.peerScope === 'all' || (p['관련기관코드'] || []).some(o => pSet.has(o)));
    });
    const anyFlag = scopedPts.some(id => S['포인트'][id] && S['포인트'][id]['원문대조']) || cell['라벨'] === '우리 간편만 열림';

    const patch = App.segPatch(map, ri, ci, c.st);
    const same = App.samePatch(patch, c.st);
    const patchT = App.segPatchText(patch);
    const willChangeTip = t('mkEvWillChangeTpl', { target: txt.josa(patchT, '으로') });

    const topHTML = `<p><b>${esc(App.label(cell['라벨']))}</b>${subNotes.length ? ` (${esc(subNotes.join(', '))})` : ''}. ${ui.fullScopeTag()}</p>
      <dl class="kv" style="margin-top:6px">
        <dt>${esc(txt.orgShort('EPOST'))}</dt><dd>${esc(App.label(oursState))}${cell['대표'] ? ` (${esc(vk(cell['대표']))})` : ''}</dd>
        <dt>${esc(t('mkEvOpenPeersHeadTpl', { open: fmt(cc.openAny), total: fmt(cc.total) }))}</dt><dd>${esc(openSummary)}</dd>
      </dl>
      ${partialSpansHTML}
      ${oursOpenIds.length ? `<p class="note" style="margin-top:6px">${esc(t('mkEvOpenVarCntTpl', { n: fmt(oursOpenIds.length), list: oursOpenIds.map(vk).join(', ') }))}</p>` : ''}
      ${gateOnly.length ? `<p class="note" style="margin-top:4px">${esc(txt.peerNamesEtc(gateOnly.map(x => `${x['이름']} - ${x['안내']}`), 2))}</p>` : ''}
      ${anyFlag ? `<p style="margin-top:6px">${ui.flagText()}</p>` : ''}
      <div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px">
        ${same ? `<span class="note">${esc(t('mkEvSameCond'))}</span>` : ui.btn(t('mkEvApplyBtn'), { main: true, sm: true, chev: true, attrs: `data-act="mk-apply" data-k="${esc(keyOf(ri, ci))}" title="${esc(willChangeTip)}"` })}
        ${ui.btn(t('mkEvGraphBtn'), { sm: true, ghost: true, chev: true, attrs: `data-go="graph" data-focus="var:${esc(cell['대표'] || c.baseId)}"` })}
      </div>`;

    let body = sec('', topHTML);

    const shownOrgs = c.activeOrgs.filter(o => cell['회사'] && (o in cell['회사']));
    const orgRows = shownOrgs.map(o => {
      const s = cell['회사'][o];
      const open = (cell['열린종형'] && cell['열린종형'][o]) || [];
      const why = txt.stateWhy(o, s);
      const pSpan = (cell['일부열린나이'] && cell['일부열린나이'][o]) ? formatSpans(cell['일부열린나이'][o]) : '';
      const go = gateOnly.filter(x => x['기관코드'] === o);
      return `<li><span class="mk-est">${ST_IC[s] || ''}<b>${esc(txt.orgShort(o))}</b> ${esc(App.label(s))}${pSpan ? ` (${esc(pSpan + t('condAgeUnit'))})` : ''}</span>
        <p class="note">${open.length ? esc(t('mkEvOpenVarCntTpl', { n: fmt(open.length), list: open.map(vk).join(', ') })) : esc(t('mkEvOpenVarNone'))}${why ? `. ${esc(why)}` : ''}</p>
        ${go.map(x => `<p class="note">${ui.tag(x['안내'])} ${esc(x['이름'])}</p>`).join('')}</li>`;
    }).join('');
    body += det(t('mkEvOrgsSummaryTpl', { n: fmt(shownOrgs.length) }), `<ul class="evl">${orgRows}</ul>`, false);

    body += det(
      t('mkEvGatePtsTpl', { n: fmt(scopedPts.length) }),
      scopedPts.length ? `<ul class="evl">${scopedPts.map(pointLi).join('')}</ul>` : `<p class="note">${esc(t('mkEvGatePtsNone'))}</p>`,
      false
    );

    const nMap = cell['분류수'] || {};
    const allCats = CATS.concat(['검토 대기']);
    const counted = allCats.filter(k => nMap[k] != null);
    const reps = c.activePeerOrgs.map(o => cell['상대대표'] && cell['상대대표'][o] ? `${txt.orgShort(o)} ${vk(cell['상대대표'][o])}` : '').filter(Boolean);
    body += det(t('mkEvRepAndCnts'), `<dl class="kv">
        <dt>${esc(t('mkEvOursRep'))}</dt><dd>${esc(vk(cell['대표']) || t('mkRevNone'))}</dd>
        <dt>${esc(t('mkEvPeerRep'))}</dt><dd>${esc(txt.peerNamesEtc(reps, 3))}</dd>
      </dl>
      ${counted.length ? `<div style="margin-top:8px">${ui.eq({ parts: counted.map(k => ({ t: k, n: nMap[k] })) })}</div>` : ''}
      <p class="note" style="margin-top:6px">${esc(t('mkEvRuleNote'))}</p>`, false);

    const badges = [
      ui.scope('all'),
      `<span class="tag">${ui.swatch(cell['라벨'])}${esc(App.label(cell['라벨']))}</span>`,
      cc.partialOnly ? ui.tag(t('mkPartialOnlyMark')) : '',
      now ? ui.tag(t('mkEvNowTag')) : '',
    ].filter(Boolean);

    return { kicker: t('mkEvKickerCell'), title: `${App.rowLabel(row)}, ${colText(col)}`, badges, body };
  }

  function revSpec(i) {
    const d = REV['담보'][i]; if (!d) return null;
    const isStd = !/^급부:/.test(d['열쇠']);
    const stdObj = isStd ? S['표준담보'][d['열쇠']] : null;
    const stName = stdObj ? `${stdObj['이름']}(${[stdObj['대분류'], stdObj['급부유형']].filter(Boolean).join(', ')})` : d['담보'];
    let body = sec('', `<p><b>${esc(d['담보'])}</b>: <b>${esc(App.label(d['종류']))}</b> (${esc(d['항목'].join(', '))}).</p>
      <div style="margin-top:8px">${ui.btn(t('mkEvGraphBtn'), { sm: true, ghost: true, chev: true, attrs: `data-go="graph" data-focus="${esc(isStd ? 'std:' + d['열쇠'] : 'var:' + (d['종형ID'][0] || ''))}"` })}</div>`);
    body += det(t('mkEvRevVars'), `<ul class="evl">${d['종형ID'].map(v => `<li><b>${esc(vk(v))}</b><br><span class="note">${esc((txt.vinfo(v) || {})['전체이름'] || '')}</span></li>`).join('')}</ul>`, true);
    body += sec('', `<p class="note">${esc(isStd ? t('mkEvRevStdNoteTpl', { target: txt.josa(stName, '으로') }) : t('mkEvRevRawNote'))}</p>`, true);
    return { kicker: t('mkEvRevKicker'), title: d['담보'], badges: [ui.scope('all'), ui.tag(d['종류'])], body };
  }

  function newsSpec(i) {
    const x = (NEWS['소식'] || [])[i]; if (!x) return null;
    const warn = x['주의표현'] || [];
    const sids = (x['표준담보ID'] || []).map(sid => (S['표준담보'][sid] && S['표준담보'][sid]['이름']) || sid);
    let body = sec('', `<p class="mk-quote">${esc(NEWS['인용안내'])}</p><p>${esc(x['요약'])}</p>`);
    body += det(t('mkEvNewsSrcHead'), `<dl class="kv">
        <dt>${esc(t('mkEvNewsOrg'))}</dt><dd>${esc(x['회사'])}</dd>
        <dt>${esc(t('mkEvNewsCat'))}</dt><dd>${esc(x['분류'])}</dd>
        <dt>${esc(t('mkEvNewsDate'))}</dt><dd class="num">${esc(x['발표일자'])}</dd>
        <dt>${esc(t('mkEvNewsMedia'))}</dt><dd>${esc(x['출처표시'] || x['매체'] || '')}</dd>
      </dl>
      ${x['출처URL'] ? `<p class="note mk-url" style="margin-top:6px">${esc(x['출처URL'])}</p><p class="note">${esc(t('mkEvNewsUrlNote'))}</p>` : ''}`, false);
    body += det(t('mkEvNewsStdHead'), `<p class="note">${esc(sids.length ? t('mkEvNewsStdLinkedTpl', { list: sids.join(', ') }) : t('mkNewsNoConn').trim())}</p>
      ${warn.length ? `<p class="note">${esc(t('mkEvNewsWarnBodyTpl', { list: warn.join('", "') }))}</p>` : ''}`, false);
    return { kicker: t('mkEvNewsKickerTpl', { week: NEWS['주차'] }), title: `${x['회사']} ${x['분류']}`, badges: [ui.scope('all'), ui.tag(t('mkNewsQuoteTag'))], body };
  }

  function pick(key, c) {
    const m = parseKey(key);
    if (m) return cellSpec(c, m.ri, m.ci);
    if (/^rv\d+$/.test(key)) return revSpec(+key.slice(2));
    if (/^nw\d+$/.test(key)) return newsSpec(+key.slice(2));
    return null;
  }

  // ---------- [개정과 시장] 모달과 [표로 보기(집계와 일러두기)] 모달 ----------
  function renderRevModalHTML() {
    const n = REV['수'];
    const pairSum = REV['짝'].reduce((a, p) => a + p['신설'] + p['변경'] + p['종료'], 0);
    const pairs = REV['짝'].map(p => `<li><b>${esc(vk(p['후']))}</b><span class="num">${esc(t('mkRevNew'))} ${fmt(p['신설'])}, ${esc(t('mkRevChg'))} ${fmt(p['변경'])}, ${esc(t('mkRevEnd'))} ${fmt(p['종료'])}</span></li>`).join('');
    const ages = (REV['가입나이변경'] || []).map(vk);
    const gates = (REV['관문변경'] || []).map(vk);
    const cols = t('mkRevCols').split(',');
    const rows = REV['담보'].map(d => {
      const full = d['종형ID'].map(vk);
      const short = full.map(nm => txt.shortName(nm).short);
      return [
        esc(d['담보']),
        { h: ui.tag(d['종류']), cp: App.label(d['종류']) },
        esc(d['항목'].join(', ')),
        { h: `<span title="${esc(full.join(', '))}">${esc(short.join(', '))}</span>`, cp: full.join(', ') },
      ];
    });

    const newsItems = (NEWS['소식'] || []).map((x, i) => {
      const warn = (x['주의표현'] || []).length ? ui.tag(t('mkNewsWarnTpl', { w: x['주의표현'].join(', ') }), t('mkNewsWarnHint')) : '';
      const linked = (x['표준담보ID'] || []).length ? t('mkNewsLinkedTpl', { n: fmt(x['표준담보ID'].length) }) : t('mkNewsUnlinked');
      return `<li class="lrow mk-nw" data-pick="nw${i}">
        <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${x['회사']} ${x['분류']}`)}"></button>
        <div class="selbar mk-nwh"><span class="num mk-d">${esc(x['발표일자'])}</span><b>${esc(x['회사'])}</b>${ui.tag(x['분류'])}${x['인용'] ? ui.tag(t('mkNewsQuoteTag')) : ''}${warn}</div>
        <p class="mk-q">${esc(x['요약'])}</p>
        <p class="mk-src">${esc((x['출처표시'] || x['매체'] || '') + linked)}</p>
        <span class="lrow-chev" aria-hidden="true">${ui.IC.chevR}</span>
      </li>`;
    }).join('');

    const revBody = `<div class="mk-pane-scroll">
      <div class="mkc-head">
        <h2>${esc(t('mkRevHead'))}</h2>
        ${ui.btn(t('mkRevCopyBtn'), { sm: true, ghost: true, icon: 'copy', attrs: 'data-copy="mk-rev-tbl" data-title="' + esc(t('mkRevHead')) + '"' })}
      </div>
      <ul class="mk-pairs">${pairs}</ul>
      ${REV['짝'].length > 1 ? `<div class="nadd">${esc(t('mkRevNonAddTpl', { c: REV['짝'].length, sum: fmt(pairSum), total: fmt(n['전체']) }))}</div>` : ''}
      <dl class="kv"><dt>${esc(t('mkRevGateChg'))}</dt><dd>${gates.length ? esc(gates.join(', ')) : esc(t('mkRevNone'))}</dd>
        <dt>${esc(t('mkRevAgeChg'))}</dt><dd>${ages.length ? esc(ages.join(', ')) : esc(t('mkRevNone'))}</dd></dl>
      <p class="note">${esc(t('mkRevNote'))}</p>
      <div class="nadd">${esc(t('mkNewsNonAddNote'))}</div>
      ${ui.table({ id: 'mk-rev-tbl', head: cols, rows, pick: i => 'rv' + i })}
    </div>`;

    const cls = Object.entries(NEWS['분류별'] || {});
    const newsBody = `<div class="mk-pane-scroll">
      <div class="mkc-head">
        <h2>${esc(t('mkNewsHead'))} <span class="num">${esc(NEWS['주차'])}</span></h2>
        ${ui.tag(t('mkNewsQuoteTag'))}
      </div>
      <p class="mk-quote">${esc(NEWS['인용안내'])}</p>
      ${ui.eq({ total: { t: t('mkRevTabNews'), n: NEWS['건수'] }, parts: cls.map(([a, cnt]) => ({ t: a, n: cnt })), nonAdd: t('mkNewsNonAddNote') })}
      <p class="note">${esc(t('mkNewsConnTpl', { n: fmt(NEWS['연결'] || 0) }) + (NEWS['연결'] ? '' : t('mkNewsNoConn')))}</p>
      <ul class="lrows">${newsItems}</ul>
    </div>`;

    return `<div class="mk-pane-scroll" id="mk-news">
      <div class="mkc-head">
        <div class="mk-subtabs" role="tablist">
          <button type="button" class="mk-subtab${revSub === 'rev' ? ' is-on' : ''}" data-mk-sub="rev">${esc(t('mkRevTabVar'))} <span class="num">${fmt(n['전체'])}</span></button>
          <button type="button" class="mk-subtab${revSub === 'news' ? ' is-on' : ''}" data-mk-sub="news">${esc(t('mkRevTabNews'))} <span class="num">${fmt(NEWS['건수'])}</span></button>
        </div>
      </div>
      ${revSub === 'rev' ? revBody : newsBody}
    </div>`;
  }

  function renderRevModal(c) {
    const bNa = ((c.base && c.base['브리핑']) || []).find(x => x['줄'] === '나');
    const lead = bNa ? `<p class="concl">${esc(bNa['문장'])}</p>` : '';
    return {
      kicker: App.TAB_NAME.market,
      title: t('mkRevModalTitle'),
      badges: [ui.scope('all')],
      html: lead + renderRevModalHTML(),
    };
  }

  function renderTallyModal(c) {
    const map = App.mapOf(c.st.renewal);
    const tl = tally(map);
    const bGa = ((c.base && c.base['브리핑']) || []).find(x => x['줄'] === '가');
    const rows = LABELS.map(l => [`${ui.swatch(l)} ${esc(App.label(l))}`, fmt(tl.lab[l] || 0)]);
    // 닫힌 사유 단위("개 고객군") 복원
    const closedT = Object.entries(tl.closed).map(([k, n]) => `${k} ${fmt(n)}${t('mkClosedUnit')}`).join(', ');
    const closedSum = Object.values(tl.closed).reduce((a, b) => a + b, 0);
    const gaps = Object.entries(tl.gap).map(([o, x]) => `<li>${ui.IC.hatch}<span>${esc(t('mkGapItemTpl', { org: txt.orgShort(o), n: fmt(x.n), why: txt.stateWhy(o, x.state) || '' }))}</span></li>`).join('');

    const cellRows = [];
    map['행'].forEach((row, ri) => map['열'].forEach((col, ci) => {
      const cell = cellAt(map, ri, ci);
      const cc = c.cellCounts(cell);
      cellRows.push({
        pk: keyOf(ri, ci),
        cells: [
          esc(App.rowLabel(row)),
          esc(colText(col)),
          `${ui.swatch(cell['라벨'])} <b>${esc(App.label(cell['라벨']))}</b>${cell['보조'] ? ` <span class="note">(${esc(cell['보조'])})</span>` : ''}`,
          esc(App.label(cc.oursState) + (cell['대표'] ? ` (${vk(cell['대표'])})` : '')),
          { h: `<span class="num">${esc(`${fmt(cc.openAny)}/${fmt(cc.total)}`)}</span>`, cp: `${cc.openAny}/${cc.total}` },
          esc((cell['닫힌사유'] || []).join(', ')),
        ],
      });
    }));

    const html = `<div class="mk-pane-scroll" id="mk-tally-wrap">
      ${bGa && c.st.renewal == null ? `<p class="concl">${esc(bGa['문장'])}${c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : ''}</p>` : `<p class="concl">${esc(conclFullText(c))}${c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : ''}</p>`}
      <div class="dm-sec">
        <div class="mkc-head">
          <h2>${esc(t('mkTallyHead'))} (${esc(txt.sexText(map['성별']))}, ${esc(renLabel(c.st.renewal))})</h2>
          <div style="display:flex;flex-wrap:wrap;gap:6px">
            ${ui.btn(t('mkTallyCopyBtn'), { sm: true, ghost: true, icon: 'copy', attrs: 'data-copy="mk-tally" data-title="' + esc(t('mkTallyHead')) + '"' })}
            ${ui.btn(t('mkCellsCopyBtn'), { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="mk-copy-cells"' })}
          </div>
        </div>
        ${ui.eq({ total: { t: t('mkGroupAll'), n: tl.total }, parts: LABELS.map(l => ({ t: l, n: tl.lab[l] || 0 })) })}
        ${ui.table({ id: 'mk-tally', head: [t('mkTallyCol1'), t('mkTallyCol2')], rows, num: [1] })}
        ${tl.closedCells
          ? `<p class="note">${esc(t('mkClosedNoteTpl', { cells: fmt(tl.closedCells), why: closedT }))}</p>${closedSum > tl.closedCells ? `<div class="nadd">${esc(t('mkClosedNonAddTpl', { sum: fmt(closedSum), cells: fmt(tl.closedCells) }))}</div>` : ''}`
          : `<p class="note">${esc(t('mkClosedZero'))}</p>`}
        ${gaps ? `<ul class="mk-gap">${gaps}</ul>` : ''}
        <p class="note">${esc(t('mkStaticNote'))}</p>
      </div>
      <div class="dm-sec">
        ${ui.table({
          id: 'mk-cells-tbl',
          caption: `${App.TAB_NAME.market} ${fmt(cellRows.length)}${t('mkClosedUnit')} (${txt.sexText(map['성별'])})`,
          head: ['이력', t('condAge'), t('mkTallyCol1'), txt.orgShort('EPOST'), t('mkOpenPeersCol'), t('scopeClosedWhy')],
          rows: cellRows.map(r => r.cells),
          num: [4],
          pick: i => cellRows[i].pk,
        })}
      </div>
      <div class="dm-sec">
        ${ui.notes(S['탭'][1])}
      </div>
    </div>`;

    return {
      kicker: App.TAB_NAME.market,
      title: t('mkGroupTally'),
      badges: [ui.scope('all'), ui.fullScopeTag()].filter(Boolean),
      html,
    };
  }

  function path(c) {
    const out = [App.TAB_NAME.market];
    const sel = c.st.sel.market;
    const m = sel != null ? parseKey(sel) : null;
    if (sel != null) {
      if (m) {
        const map = App.mapOf(c.st.renewal);
        const r = map['행'][m.ri], col = map['열'][m.ci];
        if (r && col) out.push(`${App.rowLabel(r)}, ${colText(col)}`);
      } else if (/^rv(\d+)$/.test(sel)) {
        const d = REV['담보'][+sel.slice(2)];
        if (d) out.push(d['담보']);
      } else if (/^nw(\d+)$/.test(sel)) {
        const x = (NEWS['소식'] || [])[+sel.slice(2)];
        if (x) out.push(`${x['회사']} ${x['분류']}`);
      }
    }
    return out;
  }

  function actions() {
    return [
      ui.btn(t('actModeTable'), { sm: true, ghost: true, icon: 'table', attrs: 'id="mk-btn-tally" data-mk-modal="tally"' }),
      ui.btn(t('mkGroupRev'), { sm: true, ghost: true, icon: 'doc', attrs: 'id="mk-btn-rev" data-mk-modal="rev"' }),
    ].join('');
  }

  function copyCells() {
    const c = App.ctx();
    const map = App.mapOf(c.st.renewal);
    const allCats = CATS.concat(['검토 대기']);
    const rows = [];
    map['행'].forEach((row, ri) => map['열'].forEach((col, ci) => {
      const cell = cellAt(map, ri, ci);
      const n = cell['분류수'] || {};
      const goT = (cell['관문만수집'] || []).map(x => `${x['이름']}: ${x['안내']}`).join(', ');
      rows.push([
        App.label(row['종류']), timeShort(row), colText(col), App.label(cell['라벨']), cell['보조'] || '', (cell['닫힌사유'] || []).join(', '),
        ...c.activeOrgs.map(o => App.label((cell['회사'] && cell['회사'][o]) || '')),
        vk(cell['대표']),
        c.activePeerOrgs.map(o => cell['상대대표'] && cell['상대대표'][o] ? `${txt.orgShort(o)} ${vk(cell['상대대표'][o])}` : '').filter(Boolean).join(', '),
        goT,
        ...allCats.map(k => (n[k] == null ? '' : String(n[k]))),
      ]);
    }));
    App.copyRows(
      ['이력', '기간', t('condAge'), t('mkTallyCol1'), '세부 안내', t('scopeClosedWhy'), ...c.activeOrgs.map(o => txt.orgShort(o)), t('mkEvOursRep'), t('mkEvPeerRep'), App.label('관문전용'), ...allCats.map(App.label)],
      rows,
      { title: `${App.TAB_NAME.market} (${txt.sexText(map['성별'])}, ${renLabel(c.st.renewal)})` }
    );
  }

  function focus(key) {
    if (key === 'news' || key === 'rev') {
      revSub = key === 'news' ? 'news' : 'rev';
      App.openModal({ trigger: document.getElementById('mk-btn-rev'), render: renderRevModal });
    } else if (key === 'tally') {
      App.openModal({ trigger: document.getElementById('mk-btn-tally'), render: renderTallyModal });
    }
  }

  document.addEventListener('click', e => {
    const mm = e.target.closest && e.target.closest('[data-mk-modal]');
    if (mm) {
      e.stopPropagation();
      const kind = mm.dataset.mkModal;
      if (kind === 'rev') App.openModal({ trigger: mm, render: renderRevModal });
      else App.openModal({ trigger: mm, render: renderTallyModal });
      return;
    }
    const sub = e.target.closest && e.target.closest('[data-mk-sub]');
    if (sub) {
      e.stopPropagation();
      revSub = sub.dataset.mkSub === 'news' ? 'news' : 'rev';
      const dmBody = document.getElementById('dm-body');
      if (dmBody) {
        const spec = renderRevModal(App.ctx());
        dmBody.innerHTML = spec.html;
      }
      return;
    }
    if (e.target.closest && e.target.closest('[data-act="mk-copy-cells"]')) {
      e.stopPropagation();
      copyCells();
      return;
    }
    const applyBtn = e.target.closest && e.target.closest('[data-act="mk-apply"]');
    if (applyBtn) {
      e.stopPropagation();
      const m = parseKey(applyBtn.dataset.k || '');
      if (!m) return;
      const c = App.ctx();
      const map = App.mapOf(c.st.renewal);
      const patch = App.segPatch(map, m.ri, m.ci, c.st);
      if (patch) {
        App.set(patch);
        App.toast(t('mkEvChangedToastTpl', { sum: App.condSummary() }));
      }
    }
  });

  App.on('aim', aimEl => { if (App.state.tab === 'market') syncMarketHot(aimEl); });
  App.on('select', tab => { if (tab === 'market') syncMarketHot(null); });

  return {
    id: 'market',
    layout: 'side',
    renderStage,
    conclusion,
    pick,
    path,
    actions,
    copySummary: copyCells,
    focus,
    enter,
  };
})());
