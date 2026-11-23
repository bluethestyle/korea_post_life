/* 탭 2 고객군과 시장: 신디케이트 진행 추적기 3구역 구성(왼쪽 이력/나이 묶음 + 가운데 4x6 고리 격자 + 오른쪽 고객군 상세).
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
  const ST_IC = { '열림': ui.IC.open, '닫힘': ui.IC.lock, '심사로 확인': ui.IC.check, '나이 자료 없음': ui.IC.hatch, '질문 자료 없음': ui.IC.hatch };

  let textMode = false;
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
      <dt><i class="cq m-only" aria-hidden="true"></i></dt><dd>${esc(t('mkLgGold'))}</dd>
      <dt><i class="cq m-ours" aria-hidden="true"></i></dt><dd>${esc(t('mkLgGrey'))}</dd>
      <dt>${ui.IC.hatch}</dt><dd>${esc(t('mkLgDash'))}</dd>
      <dt>${ui.IC.pin}</dt><dd>${esc(t('mkLgRed'))}</dd>
      <dt>${ui.IC.open}</dt><dd>${esc(t('mkLgNum'))}</dd>
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
    return r == null ? t('condRenAll') : r;
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

  /** 지도의 (이력 종류 x 나이 열) 행 목록과 4행 단위 묶음을 만든다(어느 자료에서나 한 화면 고리 24개 유지) */
  function buildGridModel(map, c) {
    const hospPeriods = map['행'].map((r, i) => ({ r, i })).filter(x => x.r['종류'] === '입원');
    const surgPeriods = map['행'].map((r, i) => ({ r, i })).filter(x => x.r['종류'] === '수술만');
    const cols = map['열'] || [];
    const allRows = [];
    [
      { kind: '입원', kindLabel: t('mkGroupHosp'), periods: hospPeriods },
      { kind: '수술만', kindLabel: t('mkGroupSurg'), periods: surgPeriods },
    ].forEach(g => {
      cols.forEach((col, ci) => {
        const items = g.periods.map(p => ({ ri: p.i, ci, period: p.r, col, cell: cellAt(map, p.i, ci) }));
        const oursOpenCnt = items.filter(x => x.cell && x.cell['회사'] && x.cell['회사'].EPOST === '열림').length;
        allRows.push({
          rowIdx: allRows.length,
          kind: g.kind,
          kindLabel: g.kindLabel,
          ci,
          col,
          label: `${g.kindLabel} ${col.lo}~${col.hi}${t('condAgeUnit')}`,
          shortLabel: `${g.kindLabel} ${col.lo}~${col.hi}${t('condAgeUnit')}`,
          items,
          oursOpenCnt,
        });
      });
    });

    const paged = allRows.length > 4;
    const bundles = [];
    if (!paged) {
      allRows.forEach((r, idx) => {
        bundles.push({
          id: 'b' + idx,
          label: r.label,
          rows: [r],
          openCnt: r.oursOpenCnt,
          totalCnt: r.items.length,
        });
      });
    } else {
      for (let i = 0; i < allRows.length; i += 4) {
        const slice = allRows.slice(i, i + 4);
        const first = slice[0], last = slice[slice.length - 1];
        const sameKind = first.kind === last.kind;
        const lbl = sameKind
          ? `${first.kindLabel} ${first.col.lo}~${last.col.hi}${t('condAgeUnit')}`
          : `${first.label}..`;
        const openCnt = slice.reduce((a, r) => a + r.oursOpenCnt, 0);
        const totalCnt = slice.reduce((a, r) => a + r.items.length, 0);
        bundles.push({
          id: 'b' + bundles.length,
          label: lbl,
          rows: slice,
          openCnt,
          totalCnt,
        });
      }
    }

    // 현재 조건이 속한 기본 묶음
    let defBundleIdx = 0;
    if (paged && c.seg && c.seg.cell) {
      const hitKind = c.seg.row ? c.seg.row['종류'] : '입원';
      const idx = bundles.findIndex(b => b.rows.some(r => r.kind === hitKind && r.ci === c.seg.ci));
      if (idx >= 0) defBundleIdx = idx;
    }

    return { hospPeriods, cols, allRows, paged, bundles, defBundleIdx };
  }

  function cellRingSVG(arcRatio, stateCls, fullGoldRing) {
    const r = 30, C = +(2 * Math.PI * r).toFixed(2);
    const f = Math.max(0, Math.min(1, arcRatio));
    const len = +(C * f).toFixed(2);
    let ticks = '';
    if (f < 0.999 && stateCls !== 'is-dash') {
      const N = 28, r1 = r - 2.3, r2 = r + 2.3;
      const ls = [];
      for (let i = 0; i < N; i++) {
        if (i / N < f - 0.004) continue;
        const a = (i / N) * 2 * Math.PI - Math.PI / 2;
        ls.push(`<line x1="${(r1 * Math.cos(a)).toFixed(1)}" y1="${(r1 * Math.sin(a)).toFixed(1)}" x2="${(r2 * Math.cos(a)).toFixed(1)}" y2="${(r2 * Math.sin(a)).toFixed(1)}" stroke-width="1"/>`);
      }
      ticks = `<g class="mkr-tks">${ls.join('')}</g>`;
    }
    const arcEl = f > 0
      ? `<circle class="mkr-arc" r="${r}" fill="none" stroke-width="4.2" stroke-dasharray="${len} ${C}" transform="rotate(-90)"/>`
      : (fullGoldRing ? `<circle class="mkr-arc" r="${r}" fill="none" stroke-width="2.6"/>` : '');
    return `<svg viewBox="-38 -38 76 76" aria-hidden="true" focusable="false">
      <g class="mkr-diag" stroke-width="1.3"><line x1="-33" y1="-33" x2="-26" y2="-26"/><line x1="33" y1="-33" x2="26" y2="-26"/><line x1="-33" y1="33" x2="-26" y2="26"/><line x1="33" y1="33" x2="26" y2="26"/></g>
      <circle class="mkr-bg" r="25"/>
      <circle class="mkr-disc" r="25"/>
      <circle class="mkr-out" r="35" fill="none" stroke-width="1.2"/>
      <circle class="mkr-trk" r="${r}" fill="none" stroke-width="1.2"/>
      ${ticks}${arcEl}
    </svg>`;
  }

  function renderRingGrid(map, gm, activeGrp, c) {
    let visibleRows = gm.allRows;
    let hlRowIdx = -1;
    if (gm.paged) {
      const bIdx = /^b(\d+)$/.test(activeGrp) ? Math.min(gm.bundles.length - 1, +activeGrp.slice(1)) : gm.defBundleIdx;
      visibleRows = gm.bundles[bIdx] ? gm.bundles[bIdx].rows : gm.allRows.slice(0, 4);
    } else if (/^b(\d+)$/.test(activeGrp)) {
      hlRowIdx = +activeGrp.slice(1);
    }

    const colHeads = `<div class="mk-rcols" aria-hidden="true"><span></span>${gm.hospPeriods.map(p => `<span class="mk-rch">${esc(timeShort(p.r))}</span>`).join('')}</div>`;
    const rowsHTML = visibleRows.map((rowObj, rVisIdx) => {
      const prev = visibleRows[rVisIdx - 1];
      const surgSep = prev && prev.kind !== rowObj.kind;
      const isHl = hlRowIdx === rowObj.rowIdx;
      const rings = rowObj.items.map((it, cIdx) => {
        const cell = it.cell;
        const openCodes = c.filterScopeCodes(cell['열린상대코드']);
        const closedCodes = c.filterScopeCodes(cell['닫힌상대코드']);
        const unknownCodes = c.filterScopeCodes(cell['모르는상대코드']);
        const totPeers = openCodes.length + closedCodes.length + unknownCodes.length;
        const oursOpen = !!(cell['회사'] && cell['회사'].EPOST === '열림');
        const allUnknown = totPeers > 0 && unknownCodes.length === totPeers && !oursOpen;
        const noData = cell['라벨'] === '자료 없음' || allUnknown;
        const stateCls = noData ? 'is-dash' : oursOpen ? 'is-gold' : 'is-grey';
        const ratio = totPeers > 0 ? openCodes.length / totPeers : 0;
        const numStr = allUnknown ? t('mkUnknownSym') : fmt(openCodes.length);
        const needFlag = cell['라벨'] === '우리 간편만 열림';
        const tip = `${it.period['이름']}, ${colText(it.col)}: ${cell['라벨']} (${t('mkEvOpenPeersHeadTpl', { open: fmt(openCodes.length), total: fmt(totPeers) })})`;
        const pk = keyOf(it.ri, it.ci);
        return `<button type="button" class="mk-ring ${stateCls}" data-pick="${esc(pk)}" data-grid-r="${rVisIdx}" data-grid-c="${cIdx}" data-tip="${esc(tip)}" aria-pressed="false" aria-label="${esc(tip)}" style="--d:${(rVisIdx * 3 + cIdx) * 18}ms">
          ${needFlag ? ui.flag() : ''}
          ${cellRingSVG(ratio, stateCls, oursOpen && openCodes.length === 0)}
          <span class="mk-rn num">${esc(numStr)}</span>
        </button>`;
      }).join('');
      return `<div class="mk-rrow${surgSep ? ' surg-sep' : ''}${isHl ? ' is-hl' : ''}">
        <span class="mk-rrh">${esc(rowObj.shortLabel)}</span>${rings}
      </div>`;
    }).join('');

    const sexBanner = c.seg && c.seg.sexNote ? `<p class="mkc-banner">${esc(c.seg.sexNote)}</p>` : '';
    const missBanner = c.seg && !c.seg.cell && c.seg.reason ? `<p class="mkc-banner">${esc(t('mkMissingSegWhyTpl', { why: c.seg.reason }))}</p>` : '';

    return `<div class="mkc-stage" id="mk-map">
      <div class="mkc-head">
        <h2>${esc(t('mkCenterTitle'))}</h2>
        <span class="mkc-cue">${esc(t('mkCenterCue'))}</span>
      </div>
      ${sexBanner}${missBanner}
      <div class="mk-rgrid-wrap" id="mk-grid">
        ${colHeads}
        <div class="mk-rrows${hlRowIdx >= 0 ? ' has-hl' : ''}">${rowsHTML}</div>
      </div>
    </div>`;
  }

  function renderRevCenter() {
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
        { h: ui.tag(d['종류']), cp: d['종류'] },
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
      ${ui.table({ id: 'mk-rev-tbl', head: cols, rows, pick: i => 'rv' + i })}
    </div>`;

    const cls = Object.entries(NEWS['분류별'] || {});
    const newsBody = `<div class="mk-pane-scroll">
      <div class="mkc-head">
        <h2>${esc(t('mkNewsHead'))} <span class="num">${esc(NEWS['주차'])}</span></h2>
        ${ui.tag(t('mkNewsQuoteTag'))}
      </div>
      <p class="mk-quote">${esc(NEWS['인용안내'])}</p>
      ${ui.eq({ total: { t: t('mkRevTabNews'), n: NEWS['건수'] }, parts: cls.map(([a, cnt]) => ({ t: a, n: cnt })) })}
      <p class="note">${esc(t('mkNewsConnTpl', { n: fmt(NEWS['연결'] || 0) }) + (NEWS['연결'] ? '' : t('mkNewsNoConn')))}</p>
      <ul class="lrows">${newsItems}</ul>
    </div>`;

    return `<div class="mk-pane-scroll" id="mk-news">
      <div class="mkc-head">
        <div class="mk-subtabs" role="tablist">
          <button type="button" class="mk-subtab${revSub === 'rev' ? ' is-on' : ''}" data-mk-sub="rev">${esc(t('mkRevTabVar'))} <span class="num">${fmt(n['전체'])}</span></button>
          <button type="button" class="mk-subtab${revSub === 'news' ? ' is-on' : ''}" data-mk-sub="news">${esc(t('mkRevTabNews'))} <span class="num">${fmt(NEWS['건수'])}</span></button>
        </div>
        ${ui.scope('all')}
      </div>
      ${revSub === 'rev' ? revBody : newsBody}
    </div>`;
  }

  function renderTallyCenter(map, c) {
    const tl = tally(map);
    const rows = LABELS.map(l => [`${ui.swatch(l)} ${esc(l)}`, fmt(tl.lab[l] || 0)]);
    const closedT = Object.entries(tl.closed).map(([k, n]) => `${k} ${fmt(n)}`).join(', ');
    const closedSum = Object.values(tl.closed).reduce((a, b) => a + b, 0);
    const gaps = Object.entries(tl.gap).map(([o, x]) => `<li>${ui.IC.hatch}<span>${esc(t('mkGapItemTpl', { org: txt.orgShort(o), n: fmt(x.n), why: txt.stateWhy(o, x.state) || '' }))}</span></li>`).join('');
    return `<div class="mk-pane-scroll" id="mk-tally-wrap">
      <div class="mkc-head">
        <h2>${esc(t('mkTallyHead'))}</h2>
        <div style="display:flex;gap:6px">
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
      ${ui.notes(App.TAB_NAME.market)}
    </div>`;
  }

  function renderZones({ left, center, ctx: c }) {
    const map = App.mapOf(c.st.renewal);
    const gm = buildGridModel(map, c);
    const rawGrp = c.st.grp.market || '';
    const activeGrp = rawGrp || (gm.paged ? ('b' + gm.defBundleIdx) : '');
    const notesCnt = (S['주석'] || []).filter(n => (n['탭'] || []).includes(App.TAB_NAME.market)).length;

    left.innerHTML = `<div class="mk-zl-ren"><span class="zl-k">${esc(t('mkRenLabel'))}</span><span data-slot="mk-ren"></span></div>
      <div class="zl-list" role="listbox" aria-label="${esc(App.TAB_NAME.market)}">
        ${gm.bundles.map(b => {
          const on = !textMode && activeGrp === b.id;
          const toggle = gm.paged ? '0' : '1';
          return `<button type="button" class="zl-item${on ? ' is-on' : ''}" role="option" aria-selected="${on}" data-zl="${b.id}" data-zl-toggle="${toggle}">
            <span class="zl-ring">${ui.miniRingSVG(b.openCnt, b.totalCnt, b.openCnt > 0 ? 'gold' : '')}<span class="zl-n num">${esc(fmt(b.openCnt))}</span></span>
            <span class="zl-t">${esc(b.label)}</span>
          </button>`;
        }).join('')}
        <div class="mk-zl-sep" role="separator"></div>
        <button type="button" class="zl-item${!textMode && activeGrp === 'rev' ? ' is-on' : ''}" role="option" aria-selected="${!textMode && activeGrp === 'rev'}" data-zl="rev" data-zl-toggle="1">
          <span class="zl-ring">${ui.miniRingSVG(REV['수']['신설'] || 0, REV['수']['전체'] || 1, 'gold')}<span class="zl-n num">${esc(fmt(REV['수']['전체']))}</span></span>
          <span class="zl-t">${esc(t('mkGroupRev'))}</span>
        </button>
        <button type="button" class="zl-item${textMode || activeGrp === 'tally' ? ' is-on' : ''}" role="option" aria-selected="${textMode || activeGrp === 'tally'}" data-zl="tally" data-zl-toggle="1">
          <span class="zl-ring">${ui.miniRingSVG(notesCnt, Math.max(1, notesCnt), '')}<span class="zl-n num">${esc(fmt(notesCnt))}</span></span>
          <span class="zl-t">${esc(t('mkGroupTally'))}</span>
        </button>
      </div>`;

    const slot = left.querySelector('[data-slot="mk-ren"]');
    if (slot) {
      slot.replaceWith(ui.chevSel({
        label: t('mkRenAria'),
        options: renOpts(),
        value: c.st.renewal,
        w: '52px',
        onChange: v => App.set({ renewal: v }),
      }));
    }

    if (textMode || activeGrp === 'tally') center.innerHTML = renderTallyCenter(map, c);
    else if (activeGrp === 'rev') center.innerHTML = renderRevCenter();
    else center.innerHTML = renderRingGrid(map, gm, activeGrp, c);

    bindCenter(center);
  }

  function bindCenter(center) {
    if (center._mkBound) return;
    center._mkBound = true;
    center.addEventListener('click', e => {
      const sub = e.target.closest('[data-mk-sub]');
      if (sub) {
        e.stopPropagation();
        revSub = sub.dataset.mkSub === 'news' ? 'news' : 'rev';
        App.unselect({ push: false, restoreFocus: false });
        center.innerHTML = renderRevCenter();
        return;
      }
      if (e.target.closest('[data-act="mk-copy-cells"]')) {
        e.stopPropagation();
        copyCells();
      }
    });
  }

  function enter(center) {
    const g = center && center.querySelector('#mk-grid');
    if (!g || !App.motionOn()) return;
    g.classList.remove('mk-anim'); void g.offsetWidth; g.classList.add('mk-anim');
    clearTimeout(g._t); g._t = setTimeout(() => g.classList.remove('mk-anim'), 700);
  }

  // ---------- 오른쪽 구역: 기본 결론과 고른 고객군/개정/소식 상세 ----------
  function sec(title, html, lo) { return `<div class="ev-sec${lo ? ' lo' : ''}">${title ? `<h3>${title}</h3>` : ''}${html}</div>`; }
  function det(summary, html, open) {
    return `<details class="zr-det"${open ? ' open' : ''}><summary><span>${esc(summary)}</span>${ui.IC.chevD}</summary><div class="zr-det-b">${html}</div></details>`;
  }

  function conclText(c) {
    const map = App.mapOf(c.st.renewal);
    if (c.st.renewal == null) {
      const b = ((c.base && c.base['브리핑']) || []).find(x => x['줄'] === '가');
      if (b) return b['문장'];
    }
    const tl = tally(map);
    return `${renLabel(c.st.renewal)}: ${LABELS.filter(l => tl.lab[l]).map(l => `${l} ${fmt(tl.lab[l])}`).join(', ')}.`;
  }

  function defaultEv(c) {
    const grp = c.st.grp.market || '';
    if (grp === 'rev') {
      const b = ((c.base && c.base['브리핑']) || []).find(x => x['줄'] === '나');
      return {
        kicker: t('evKickerDefault'),
        title: t('mkGroupRev'),
        badges: [ui.scope('all')],
        body: sec('', `<p>${esc(b ? b['문장'] : '')}</p>`),
      };
    }
    return {
      kicker: t('evKickerDefault'),
      title: App.TAB_NAME.market,
      badges: [ui.scope('all'), ui.fullScopeTag()].filter(Boolean),
      body: sec('', `<p>${esc(conclText(c))}</p>`),
    };
  }

  function pointLi(id) {
    const p = S['포인트'][id]; if (!p) return '';
    const hd = p['머리말'] != null ? S['글'][p['머리말']] : '';
    const docs = (p['근거'] || []).map(g => ui.tag(`${txt.orgShort((txt.vinfo(g['종형ID']) || {})['기관코드'] || '')} ${txt.pageText(g['문서'], g['쪽'])}`, '', 'doc')).join(' ');
    return `<li><span class="tag">${esc(p['세부이름'] || p['분류'])}</span> ${p['원문대조'] ? ui.flagText(p['원문대조글']) : ''}<p>${esc(p['문장'])}</p>${docs ? `<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px">${docs}</div>` : ''}${hd ? `<p class="note">${esc(hd)}</p>` : ''}</li>`;
  }

  function cellSpec(c, ri, ci) {
    const map = App.mapOf(c.st.renewal);
    const cell = cellAt(map, ri, ci);
    if (!cell) return null;
    const row = map['행'][ri], col = map['열'][ci];
    const now = !!(c.seg && c.seg.cell && c.seg.ri === ri && c.seg.ci === ci);
    const pSet = new Set(c.activePeerOrgs);

    const openCodes = c.filterScopeCodes(cell['열린상대코드']);
    const closedCodes = c.filterScopeCodes(cell['닫힌상대코드']);
    const unknownCodes = c.filterScopeCodes(cell['모르는상대코드']);
    const totPeers = openCodes.length + closedCodes.length + unknownCodes.length;
    const gateOnly = (cell['관문만수집'] || []).filter(x => c.peerScope === 'all' || pSet.has(x['기관코드']));

    const oursState = (cell['회사'] && cell['회사'].EPOST) || '';
    const oursOpenIds = (cell['열린종형'] && cell['열린종형'].EPOST) || [];
    const subNotes = [];
    if (cell['보조']) subNotes.push(cell['보조']);
    if (cell['닫힌사유'] && cell['닫힌사유'].length) subNotes.push(`${t('scopeClosedWhy')}: ${cell['닫힌사유'].join(', ')}`);

    const openNames = openCodes.map(txt.orgShort);
    const openSummary = openCodes.length ? txt.peerNamesEtc(openNames, 3) : t('mkRevNone');

    const scopedPts = (cell['관문포인트'] || []).filter(id => {
      const p = S['포인트'][id];
      return p && (c.peerScope === 'all' || (p['관련기관코드'] || []).some(o => pSet.has(o)));
    });
    const anyFlag = scopedPts.some(id => S['포인트'][id] && S['포인트'][id]['원문대조']) || cell['라벨'] === '우리 간편만 열림';

    const patch = App.segPatch(map, ri, ci, c.st);
    const same = App.samePatch(patch, c.st);
    const patchT = App.segPatchText(patch);

    const willChangeTip = t('mkEvWillChangeTpl', { target: txt.josa(patchT, '으로') });

    // 1. 첫눈에 보이는 핵심 요약(300자 이내 유지)
    let topHTML = `<p><b>${esc(cell['라벨'])}</b>${subNotes.length ? ` (${esc(subNotes.join(', '))})` : ''}. ${ui.fullScopeTag()}</p>
      <dl class="kv" style="margin-top:6px">
        <dt>${esc(txt.orgShort('EPOST'))}</dt><dd>${esc(oursState)}${cell['대표'] ? ` (${esc(vk(cell['대표']))})` : ''}</dd>
        <dt>${esc(t('mkEvOpenPeersHeadTpl', { open: fmt(openCodes.length), total: fmt(totPeers) }))}</dt><dd>${esc(openSummary)}</dd>
      </dl>
      ${oursOpenIds.length ? `<p class="note" style="margin-top:6px">${esc(t('mkEvOpenVarCntTpl', { n: fmt(oursOpenIds.length), list: oursOpenIds.map(vk).join(', ') }))}</p>` : ''}
      ${gateOnly.length ? `<p class="note" style="margin-top:4px">${esc(txt.peerNamesEtc(gateOnly.map(x => `${x['이름']}(${x['안내']})`), 2))}</p>` : ''}
      ${anyFlag ? `<p style="margin-top:6px">${ui.flagText()}</p>` : ''}
      <div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px">
        ${same ? `<span class="note">${esc(t('mkEvSameCond'))}</span>` : ui.btn(t('mkEvApplyBtn'), { main: true, sm: true, chev: true, attrs: `data-act="mk-apply" data-k="${esc(keyOf(ri, ci))}" title="${esc(willChangeTip)}"` })}
        ${ui.btn(t('mkEvGraphBtn'), { sm: true, ghost: true, chev: true, attrs: 'data-go="graph"' })}
      </div>`;

    let body = sec('', topHTML);

    // 2. 상대 회사 전체 목록(셋 초과이거나 닫힘/모름 상세 확인용)
    const shownOrgs = c.activeOrgs.filter(o => cell['회사'] && (o in cell['회사']));
    const orgRows = shownOrgs.map(o => {
      const s = cell['회사'][o];
      const open = (cell['열린종형'] && cell['열린종형'][o]) || [];
      const why = txt.stateWhy(o, s);
      const go = gateOnly.filter(x => x['기관코드'] === o);
      return `<li><span class="mk-est">${ST_IC[s] || ''}<b>${esc(txt.orgShort(o))}</b> ${esc(s)}</span>
        <p class="note">${open.length ? esc(t('mkEvOpenVarCntTpl', { n: fmt(open.length), list: open.map(vk).join(', ') })) : esc(t('mkEvOpenVarNone'))}${why ? `. ${esc(why)}` : ''}</p>
        ${go.map(x => `<p class="note">${ui.tag(x['안내'])} ${esc(x['이름'])}</p>`).join('')}</li>`;
    }).join('');
    body += det(t('mkEvOrgsSummaryTpl', { n: fmt(shownOrgs.length) }), `<ul class="evl">${orgRows}</ul>`, false);

    // 3. 관문 포인트와 근거 문서
    body += det(
      t('mkEvGatePtsTpl', { n: fmt(scopedPts.length) }),
      scopedPts.length ? `<ul class="evl">${scopedPts.map(pointLi).join('')}</ul>` : `<p class="note">${esc(t('mkEvGatePtsNone'))}</p>`,
      false
    );

    // 4. 대표 종형과 분류별 인사이트 수
    const nMap = cell['분류수'] || {};
    const allCats = CATS.concat([t('mkCatWait')]);
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
      `<span class="tag">${ui.swatch(cell['라벨'])}${esc(cell['라벨'])}</span>`,
      now ? ui.tag(t('mkEvNowTag')) : '',
    ].filter(Boolean);

    return { kicker: t('mkEvKickerCell'), title: `${row['이름']}, ${colText(col)}`, badges, body };
  }

  function revSpec(i) {
    const d = REV['담보'][i]; if (!d) return null;
    const isStd = !/^급부:/.test(d['열쇠']);
    const stdObj = isStd ? S['표준담보'][d['열쇠']] : null;
    const stName = stdObj ? `${stdObj['이름']}(${[stdObj['대분류'], stdObj['급부유형']].filter(Boolean).join(', ')})` : d['담보'];
    let body = sec('', `<p><b>${esc(d['담보'])}</b>: <b>${esc(d['종류'])}</b> (${esc(d['항목'].join(', '))}).</p>
      <div style="margin-top:8px">${ui.btn(t('mkEvGraphBtn'), { sm: true, ghost: true, chev: true, attrs: 'data-go="graph"' })}</div>`);
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

  function path(c) {
    const out = [App.TAB_NAME.market];
    const grp = c.st.grp.market || '';
    const sel = c.st.sel.market;
    const m = sel != null ? parseKey(sel) : null;
    if (grp === 'rev') out.push(t('mkGroupRev'));
    else if (grp === 'tally' || textMode) out.push(t('mkGroupTally'));
    else if (!m && /^b\d+$/.test(grp)) {
      const gm = buildGridModel(App.mapOf(c.st.renewal), c);
      const b = gm.bundles[+grp.slice(1)];
      if (b) out.push(b.label);
    }
    if (sel != null) {
      if (m) {
        const map = App.mapOf(c.st.renewal);
        const r = map['행'][m.ri], col = map['열'][m.ci];
        if (r && col) out.push(`${r['이름']}, ${colText(col)}`);
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
    const lbl = textMode ? t('actModeShape') : t('actModeText');
    return ui.btn(lbl, { sm: true, ghost: true, attrs: 'data-act="mk-toggle-mode"' });
  }

  function copyCells() {
    const c = App.ctx();
    const map = App.mapOf(c.st.renewal);
    const allCats = CATS.concat([t('mkCatWait')]);
    const rows = [];
    map['행'].forEach((row, ri) => map['열'].forEach((col, ci) => {
      const cell = cellAt(map, ri, ci);
      const n = cell['분류수'] || {};
      const goT = (cell['관문만수집'] || []).map(x => `${x['이름']}: ${x['안내']}`).join(', ');
      rows.push([
        row['종류'], timeShort(row), colText(col), cell['라벨'], cell['보조'] || '', (cell['닫힌사유'] || []).join(', '),
        ...c.activeOrgs.map(o => (cell['회사'] && cell['회사'][o]) || ''),
        vk(cell['대표']),
        c.activePeerOrgs.map(o => cell['상대대표'] && cell['상대대표'][o] ? `${txt.orgShort(o)} ${vk(cell['상대대표'][o])}` : '').filter(Boolean).join(', '),
        goT,
        ...allCats.map(k => (n[k] == null ? '' : String(n[k]))),
      ]);
    }));
    App.copyRows(
      ['이력', '기간', t('condAge'), t('mkTallyCol1'), '보조', t('scopeClosedWhy'), ...c.activeOrgs.map(o => txt.orgShort(o)), t('mkEvOursRep'), t('mkEvPeerRep'), '관문전용', ...allCats],
      rows,
      { title: `${App.TAB_NAME.market} (${txt.sexText(map['성별'])}, ${renLabel(c.st.renewal)})` }
    );
  }

  function focus(key) {
    if (key === 'news') App.setGroup('rev');
    else App.setGroup('');
  }

  document.addEventListener('click', e => {
    if (e.target.closest('[data-act="mk-toggle-mode"]')) {
      e.stopPropagation();
      textMode = !textMode;
      App.set({ grp: Object.assign({}, App.state.grp, { market: textMode ? 'tally' : '' }) });
      return;
    }
    const applyBtn = e.target.closest('[data-act="mk-apply"]');
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

  return { id: 'market', renderZones, pick, defaultEv, path, actions, copySummary: copyCells, focus, enter };
})());
