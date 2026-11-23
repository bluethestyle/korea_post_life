/* 탭 1 브리핑: 주인공 도형은 다섯 큰 메달(지름 96~108px)과 24칸 고객군 지형 격자, 치료 여정 다섯 단계 타일, 공통 담보 막대.
   긴 문장과 관계 식은 근거 기둥에 모으고, 한 번에 읽고 싶은 사람을 위해 "문장으로 보기" 전환을 둔다.
   값과 문장은 sales.json 의 기준별[종형].브리핑, 지도, 범위, 치료여정, 보류요약에서 읽는다. */
App.registerTab((function () {
  const { ui, txt } = App;
  const { esc, fmt } = ui;
  const S = App.S;
  const ROW_NAME = { '가': '고객군 지형', '나': '개정과 시장', '다': '가입 관문과 한도', '라': '담보 포지션', '마': '영업 인사이트' };
  const ROW_FOCUS = { '가': 'map', '나': 'news', '다': '', '라': 'journey', '마': '' };
  const ROW_NO = { '가': 1, '나': 2, '다': 3, '라': 4, '마': 5 };
  const MAP_LABELS = S['라벨'];

  let viewMode = 'medal'; // 'medal' | 'list'
  // 하단 판의 지표 단추도 core 의 고르기(App.select)로 고른다. 고른 것은 늘 하나라 메달의 빨강과 함께 켜지지 않는다.
  // 0: 고객군 24칸 격자(메달 가와 같은 근거), 1: 공통 담보 쌍, 2: 치료 여정 5단계
  const SUB_KEY = ['가', 'sub1', 'sub2'];
  const subOf = key => SUB_KEY.indexOf(key);
  let focusSeg = null;    // { ri, ci } 지도 칸을 눌렀을 때
  let lastBase = null;
  let lastNote = { short: '', long: '' };
  const justChanged = new Set();

  const brief = c => (c.base ? c.base['브리핑'] : []);
  const line = (c, k) => brief(c).find(b => b['줄'] === k) || null;
  const refText = c => `${c.ref['나이']}세 ${txt.sexText(c.ref['성별'])}, ${txt.sinceText(c.ref['이력'])}`;

  function limitLine(c) {
    const L = c.limit;
    if (!L || (c.st.age === c.ref['나이'] && c.st.sex === c.ref['성별'])) return '';
    const who = `${c.st.age}세 ${txt.sexText(c.st.sex)}`;
    const kind = txt.vkind(c.baseId);
    if (!L.hit) return `지금 조건 ${who}: ${kind}의 가입나이(${L.lo}~${L.hi}세) 밖입니다.`;
    return `지금 조건 ${who}: 주계약 최대 가입금액 ${fmt(L.hit.max)}만원(나이 구간별 한도 표의 ${L.hit.lo}~${L.hit.hi}세 구간${L.hit.pend ? ', 검토 대기' : ''}${L.table['성별같음'] ? ', 남녀 같음' : ''}).`;
  }

  // ---------- 1. 머리 제어 줄 ----------
  function headAsideHTML(c) {
    const isList = viewMode === 'list';
    return `<div class="bhead">
      <div class="bhead-meta">
        <span>대표 조건 <b class="num">${esc(refText(c))}</b></span>
        <span>기준 종형 <b>${esc(txt.vkind(c.baseId))}</b></span>
      </div>
      <div class="bhead-act">
        ${ui.btn(isList ? '도형으로 보기' : '문장으로 보기', {
          sm: true, ghost: !isList, cls: isList ? 'is-mode-on' : '',
          attrs: `data-act="brief-mode" aria-pressed="${isList}"`,
        })}
        ${ui.btn('요약 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="brief-copy"' })}
      </div>
    </div>`;
  }

  // ---------- 2. 다섯 메달 자료와 이중 고리 SVG ----------
  function medalSpecs(c) {
    return brief(c).map(b => {
      const k = b['줄'];
      const v = b['값'] || {};
      const no = String(ROW_NO[k]).padStart(2, '0');
      const name = b['구역'] || ROW_NAME[k];
      const scope = b['범위'] === '전체 고객군' ? 'all' : 'base';
      let num = '0', den = null, unit = '', cap = '', max = 1, segs = [], hasGold = false;

      if (k === '가') {
        num = fmt(v['함께열림칸수'] || 0);
        den = fmt(v['전체칸수'] || 0);
        unit = '칸';
        cap = (v['우리간편만열림칸수'] || 0) > 0
          ? `단독 ${fmt(v['우리간편만열림칸수'])}, 함께 열림`
          : `함께 열림, 일반확인 ${fmt(v['우리간편닫힘칸수'] || 0)}`;
        max = v['전체칸수'] || 1;
        const openN = (v['우리간편만열림칸수'] || 0) + (v['함께열림칸수'] || 0);
        segs = [{ v: openN, cls: 'gold' }];
        hasGold = openN > 0;
      } else if (k === '나') {
        num = fmt(v['개정변동수'] || 0);
        unit = '개';
        cap = `신설 ${fmt(v['개정신설'] || 0)}, 변경 ${fmt(v['개정변경'] || 0)}, 종료 ${fmt(v['개정종료'] || 0)}`;
        max = v['개정변동수'] || 1;
        segs = [{ v: v['개정신설'] || 0, cls: 'gold' }, { v: v['개정변경'] || 0, cls: '' }];
        hasGold = (v['개정신설'] || 0) > 0;
      } else if (k === '다') {
        num = fmt(v['관문차이수'] || 0);
        unit = '곳';
        if (!c.isRef && c.limit) {
          cap = c.limit.hit ? `${c.st.age}세 한도 ${fmt(c.limit.hit.max)}만원` : `${c.st.age}세 가입나이 밖`;
        } else {
          cap = v['심사'] === '일반심사'
            ? `일반심사, ${v['우리최저']}~${v['우리최고']}세`
            : `고지 다른 상대, ${v['우리최저']}~${v['우리최고']}세`;
        }
        max = Math.max(1, c.peerIds.length);
        segs = [{ v: v['관문차이수'] || 0, cls: '' }];
      } else if (k === '라') {
        num = fmt(v['견준쌍'] || 0);
        den = fmt(v['공통담보쌍'] || 0);
        unit = '쌍';
        cap = `우체국 ${fmt(v['보유수'] || 0)}개, 대기 ${fmt(v['뺀비교쌍'] || 0)}쌍`;
        max = v['공통담보쌍'] || 1;
        segs = [{ v: v['견준쌍'] || 0, cls: 'gold' }];
        hasGold = (v['견준쌍'] || 0) > 0;
      } else if (k === '마') {
        num = fmt(v['전체수'] || 0);
        unit = '건';
        cap = `강점 ${fmt(v['앞세울수'] || 0)}, 관련 ${fmt(v['관련담보수'] || 0)}, 개정 ${fmt(v['개정검토수'] || 0)}`;
        max = v['전체수'] || 1;
        const pos = (v['앞세울수'] || 0) + (v['관련담보수'] || 0);
        const mid = (v['관문차이수'] || 0) + (v['조건열위수'] || 0);
        segs = [{ v: pos, cls: 'gold' }, { v: mid, cls: '' }];
        hasGold = pos > 0;
      }

      return {
        key: k, no, name, scope, scopeText: b['범위'],
        num, den, unit, numText: den != null ? `${num}/${den}${unit}` : `${num}${unit}`,
        cap, max, segs, hasGold,
        flag: !!b['원문대조'], flagText: b['원문대조글'],
      };
    });
  }

  function medalSVG(m) {
    let acc = 0, arcs = '';
    for (const s of m.segs) {
      const f = m.max > 0 ? Math.max(0, Math.min(1 - acc, s.v / m.max)) : 0;
      if (f > 0) {
        const to = (f * 100).toFixed(2);
        arcs += `<circle class="arc ${s.cls || ''}" r="45" fill="none" stroke-width="5.5" pathLength="100" stroke-dasharray="${to} 100" stroke-dashoffset="${(-acc * 100).toFixed(2)}" transform="rotate(-90)" data-to="${to}"/>`;
      }
      acc += f;
    }
    const frac = Math.min(1, acc);
    let tks = '';
    for (let i = 0; i < 72; i++) {
      const a = i / 72;
      if (a < frac - 1e-6) continue;
      const t = a * Math.PI * 2 - Math.PI / 2, cs = Math.cos(t), sn = Math.sin(t);
      tks += `<line x1="${(cs * 41.5).toFixed(2)}" y1="${(sn * 41.5).toFixed(2)}" x2="${(cs * 48.5).toFixed(2)}" y2="${(sn * 48.5).toFixed(2)}"/>`;
    }
    return `<svg class="ring bm-svg" width="108" height="108" viewBox="-64 -64 128 128" aria-hidden="true" focusable="false">
      <circle class="bm-outer" r="54" fill="none" stroke-width="1"/>
      <path class="bm-card" d="M0 -58V-53M58 0H53M0 58V53M-58 0H-53" stroke-width="1.4" fill="none"/>
      <circle class="trk" r="45" fill="none" stroke-width="1"/>
      <g class="tks" stroke-width="1.5">${tks}</g>
      ${arcs}
      <circle class="bm-inner${m.hasGold ? ' gold' : ''}" r="37.5" fill="none" stroke-width="1.5"/>
      <circle class="bm-disc" r="34.5"/>
      <path class="bm-diag" d="M-56 -56l10 10M56 -56l-10 10M-56 56l10 -10M56 56l-10 -10" stroke-width="2" fill="none"/>
    </svg>`;
  }

  function medalsHTML(c) {
    const list = medalSpecs(c);
    return `<div class="bmedals" data-pick-group="brief">${list.map((m, i) => {
      const flag = m.flag ? ui.flag(m.flagText || ui.FLAG_TEXT) : '';
      const ch = justChanged.has(m.key) && lastNote.short ? `<span class="chg bm-chg">${esc(lastNote.short)}</span>` : '';
      return `<div class="bmedal brow${justChanged.has(m.key) ? ' just' : ''}" data-pick="${esc(m.key)}" data-scope="${m.scope}" style="--mi:${i}">
        <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${m.no} ${m.name}, ${m.numText}, ${m.scopeText}. 근거 보기`)}"></button>
        ${flag}
        <div class="bm-top">
          <span class="bm-no num" aria-hidden="true"><span class="num-0">${m.no[0]}</span>${m.no[1]}</span>
          ${ui.scope(m.scope)}
        </div>
        <div class="bm-emblem">
          ${medalSVG(m)}
          <div class="bm-val">
            <span class="bm-n num${m.den != null ? ' frac' : ''}">${esc(m.num)}${m.den != null ? `<small class="bm-d">/${esc(m.den)}</small>` : ''}</span>
            <span class="bm-u">${esc(m.unit)}</span>
          </div>
        </div>
        <div class="bm-foot">
          <span class="bm-name">${esc(m.name)}</span>
          <span class="bm-cap">${esc(m.cap)}</span>
          ${ch}
        </div>
      </div>`;
    }).join('')}</div>`;
  }

  // ---------- 3. 하단 통합 기하 격자(고객군 24칸 지도 + 치료 여정 5단계 + 공통 쌍) ----------
  const TIME_SHORT = r => {
    if (r.since === 5) return '5년+/없음';
    return r['이름'].replace(/^(입원|수술만)\s*/, '').replace(/\s*전$/, '');
  };
  const TIME_TINY = r => (r.since === 5 ? '5년+' : TIME_SHORT(r));
  const CELL_STYLE = {
    '우리 간편만 열림': { cls: 'is-only', ic: ui.IC.only, txt: '단독' },
    '함께 열림': { cls: 'is-open', ic: ui.IC.open, txt: '열림' },
    '우리 간편 닫힘': { cls: 'is-ours', ic: ui.IC.check, txt: '일반' },
    '간편 모두 닫힘': { cls: 'is-all', ic: ui.IC.lock, txt: '닫힘' },
    '자료 없음': { cls: 'is-none', ic: ui.IC.hatch, txt: '미상' },
  };

  function map24HTML(c) {
    const ga = line(c, '가');
    const gv = ga ? ga['값'] : {};
    const lab = gv['라벨별'] || {};
    const m = App.mapOf(null);
    const cols = m['열'] || [];
    const hospRows = (m['행'] || []).map((r, i) => ({ r, i })).filter(x => x.r['종류'] === '입원');
    const surgRows = (m['행'] || []).map((r, i) => ({ r, i })).filter(x => x.r['종류'] === '수술만');
    const openCnt = (gv['우리간편만열림칸수'] || 0) + (gv['함께열림칸수'] || 0);
    const nowSeg = App.cellOf({ ...c.st, renewal: null });
    const focusSub = subOf(c.st.sel.brief);

    const colHeads = `<div class="bmap-cols" aria-hidden="true"><span></span>${hospRows.map(x => `<span class="bmap-ch" title="${esc(x.r['이름'])}"><span class="ch-full">${esc(TIME_SHORT(x.r))}</span><span class="ch-sm">${esc(TIME_TINY(x.r)).replace('~', '~<wbr>')}</span></span>`).join('')}</div>`;
    const gridRows = [];
    [
      { kind: '입원', rows: hospRows, surg: false },
      { kind: '수술만', rows: surgRows, surg: true },
    ].forEach(group => {
      cols.forEach((col, ci) => {
        const firstSurg = group.surg && ci === 0;
        const cells = group.rows.map((x, bi) => {
          const ri = x.i;
          const cell = m['칸'][ri][ci];
          const st = CELL_STYLE[cell['라벨']] || CELL_STYLE['자료 없음'];
          const isNow = !!nowSeg.cell && nowSeg.ri === ri && nowSeg.ci === ci;
          const isFocus = focusSeg && focusSeg.ri === ri && focusSeg.ci === ci;
          const go = cell['관문만수집'] || [];
          const goTitle = go.length ? go.map(g => `${g['이름']} ${g['안내'] || '관문만 수집'}`).join(', ') : '';
          const aria = `${x.r['이름']}, ${col.lo}~${col.hi}세: ${cell['라벨']}${cell['보조'] ? ', ' + cell['보조'] : ''}${goTitle ? ', ' + goTitle : ''}${isNow ? ', 지금 조건' : ''}`;
          return `<button type="button" class="bm-cell ${st.cls}${go.length ? ' has-go' : ''}${isNow ? ' is-now' : ''}${isFocus ? ' is-focus' : ''}" data-act="bmap-cell" data-ri="${ri}" data-ci="${ci}" style="--ci:${bi + (group.surg ? 2 : 0) + ci}" aria-label="${esc(aria)}" title="${esc(aria)}">
            <i class="bm-cbg" aria-hidden="true"></i>
            ${cell['라벨'] === '우리 간편만 열림' ? ui.flag() : ''}
            <span class="bm-cs">${st.ic}<span class="bm-ct">${esc(st.txt)}</span></span>
            ${(go.length || isNow) ? `<span class="bm-ctag">${go.length ? '<span class="bm-cgo">관문만</span>' : ''}${isNow ? '<span class="bm-cnow">지금</span>' : ''}</span>` : ''}
          </button>`;
        }).join('');
        gridRows.push(`<div class="bmap-row${firstSurg ? ' surg-start' : ''}">
          <span class="bmap-rh"><span>${esc(group.kind)}</span><span class="nw">${col.lo}~${col.hi}세</span></span>${cells}
        </div>`);
      });
    });

    return `<section class="bsub bmap-box${focusSub === 0 ? ' is-on' : ''}" data-sub="0" aria-label="고객군 24칸 관문 지형">
      <div class="bsub-top">
        <button type="button" class="kpi bsub-t${focusSub === 0 ? ' is-on' : ''}" data-act="kpi" data-i="0" aria-pressed="${focusSub === 0}">
          <span class="bsub-h">고객군 ${fmt(gv['전체칸수'] || 24)}칸 관문 지형</span>
          <span class="bsub-big num">${fmt(openCnt)}<small>/${fmt(gv['전체칸수'] || 24)}</small><em>칸 열림</em></span>
        </button>
        <div class="bsub-r">
          ${ui.scope('all')}
          ${ui.btn('지도 탭', { sm: true, ghost: true, chev: true, attrs: 'data-go="market" data-focus="map"' })}
        </div>
      </div>
      <div class="bmap-wrap" role="group" aria-label="이력과 나이 구간별 24개 고객군 칸">
        ${colHeads}
        ${gridRows.join('')}
      </div>
      <div class="bmap-lg">
        <span class="lg-i"><i class="msw open"></i>우리 간편 열림(함께 열림) <b class="num">${fmt(lab['함께 열림'] || 0)}</b></span>
        <span class="lg-i"><i class="msw only"></i>우리 간편만 열림 <b class="num">${fmt(lab['우리 간편만 열림'] || 0)}</b></span>
        <span class="lg-i"><i class="msw ours"></i>일반심사 확인 <b class="num">${fmt(lab['우리 간편 닫힘'] || 0)}</b></span>
        <span class="lg-i"><i class="msw go"></i>관문만 수집 칸 <b class="num">${fmt(gv['관문만칸수'] || 0)}</b></span>
        <span class="lg-i"><i class="msw now"></i>지금 조건</span>
      </div>
    </section>`;
  }

  function sideDeckHTML(c) {
    const ra = line(c, '라');
    const rv = ra ? ra['값'] : {};
    const j = c.base['치료여정'];
    const steps = j['열'] || [];
    const cols = j['종형'] || [];
    const ours = cols.find(x => x['종형ID'] === c.baseId) || cols[0];
    const have = ours ? steps.filter(s => (ours['합계'][s] || 0) > 0).length : 0;
    const maxStep = Math.max(1, ...cols.flatMap(x => steps.map(s => x['합계'][s] || 0)));
    const focusSub = subOf(c.st.sel.brief);

    const stepTiles = steps.map((s, si) => {
      const n = ours ? (ours['합계'][s] || 0) : 0;
      const bars = cols.map((x, xi) => {
        const cnt = x['합계'][s] || 0;
        const h = cnt > 0 ? Math.max(3, Math.round(cnt / maxStep * 18)) : 0;
        return `<i class="c${xi}" style="height:${h}px" title="${esc(txt.orgShort(x['종형ID'].split('_')[0]))} ${cnt}개"></i>`;
      }).join('');
      return `<div class="bstep ${n > 0 ? 'is-gold' : 'is-empty'}" style="--si:${si}" role="group" aria-label="${esc(`${s} 단계, 우체국 담보 ${n}개`)}">
        <i class="bs-bg" aria-hidden="true"></i>
        <span class="bs-s">${esc(s)}</span>
        <span class="bs-n num">${fmt(n)}</span>
        <span class="bs-bars" aria-hidden="true">${bars}</span>
      </div>`;
    }).join('');

    const totalPairs = rv['공통담보쌍'] || 0;
    const cmpPairs = rv['견준쌍'] || 0;
    const waitPairs = rv['뺀비교쌍'] || 0;
    const cmpPct = totalPairs > 0 ? (cmpPairs / totalPairs * 100).toFixed(1) : 0;
    const waitPct = totalPairs > 0 ? (waitPairs / totalPairs * 100).toFixed(1) : 0;
    const cats = (c.base['보류요약'] && c.base['보류요약']['대분류']) || [];
    const catHTML = cats.map(x => {
      const tot = (x['견준쌍'] || 0) + (x['뺀쌍'] || 0);
      const cp = tot > 0 ? (x['견준쌍'] / tot * 100).toFixed(1) : 0;
      const wp = tot > 0 ? (x['뺀쌍'] / tot * 100).toFixed(1) : 0;
      return `<div class="bp-cat">
        <div class="bp-ch"><span>${esc(x['대분류'])}</span><span class="num"><b>${fmt(x['견준쌍'])}</b>/${fmt(tot)}</span></div>
        <div class="bp-cb" aria-hidden="true"><i class="c" style="width:${cp}%"></i><i class="w" style="width:${wp}%"></i></div>
      </div>`;
    }).join('');

    return `<div class="bdeck-side">
      <section class="bsub bstep-box${focusSub === 2 ? ' is-on' : ''}" data-sub="2" aria-label="우체국 담보가 있는 치료 단계">
        <div class="bsub-top">
          <button type="button" class="kpi bsub-t${focusSub === 2 ? ' is-on' : ''}" data-act="kpi" data-i="2" aria-pressed="${focusSub === 2}">
            <span class="bsub-h">치료 여정 다섯 단계</span>
            <span class="bsub-big num">${fmt(have)}<small>/${fmt(steps.length)}</small><em>단계 보유</em></span>
          </button>
          <div class="bsub-r">
            ${ui.help('journey-grid', '치료 여정 격자')}
            ${ui.scope('base')}
            ${ui.btn('여정 격자', { sm: true, ghost: true, chev: true, attrs: 'data-go="cover" data-focus="journey"' })}
          </div>
        </div>
        <div class="bsteps">${stepTiles}</div>
        <div class="bstep-lg">
          <span>우체국 보유 <b>${fmt(ours ? ours['전체'] : 0)}</b>개(금색 타일)</span>
          <span class="orgs">${cols.map((x, i) => `<span class="oi"><i class="ob c${i}"></i>${esc(txt.orgShort(x['종형ID'].split('_')[0]))}</span>`).join('')}</span>
        </div>
      </section>
      <section class="bsub bpair-box${focusSub === 1 ? ' is-on' : ''}" data-sub="1" aria-label="견준 공통 담보 쌍">
        <div class="bsub-top">
          <button type="button" class="kpi bsub-t${focusSub === 1 ? ' is-on' : ''}" data-act="kpi" data-i="1" aria-pressed="${focusSub === 1}">
            <span class="bsub-h">견준 공통 담보 쌍</span>
            <span class="bsub-big num">${fmt(cmpPairs)}<small>/${fmt(totalPairs)}</small><em>쌍</em></span>
          </button>
          <div class="bsub-r">
            ${ui.help('caution-pending', '단정 주의와 검토 대기')}
            ${ui.scope('base')}
            ${ui.btn('담보 비교', { sm: true, ghost: true, chev: true, attrs: 'data-go="cover"' })}
          </div>
        </div>
        <div class="bpair-bar" role="img" aria-label="${esc(`공통 담보 ${totalPairs}쌍 가운데 견준 쌍 ${cmpPairs}, 검토 대기 ${waitPairs}`)}">
          <i class="bp-cmp" style="width:${cmpPct}%"></i><i class="bp-wait" style="width:${waitPct}%"></i>
        </div>
        <div class="bpair-cats">${catHTML}</div>
        <div class="bpair-lg">
          <span><i class="c"></i>견준 쌍 <b class="num">${fmt(cmpPairs)}</b></span>
          <span><i class="w"></i>검토 대기로 뺀 쌍 <b class="num">${fmt(waitPairs)}</b></span>
        </div>
      </section>
    </div>`;
  }

  function stageHTML(c) {
    const off = !c.isRef;
    return `<section class="panel bstage" id="brief-stage" aria-label="브리핑 도형 요약">
      ${off ? `<p class="brief-off">지금 조건(${esc(App.condSummary().split(', 기준')[0])})은 대표 조건과 다릅니다. 메달 대표 값은 대표 조건 기준이고, 지도 칸의 지금 표지와 03번 메달 한도는 지금 조건을 따릅니다.</p>` : ''}
      ${medalsHTML(c)}
      <div class="bdeck">
        ${map24HTML(c)}
        ${sideDeckHTML(c)}
      </div>
      <div class="panel-f" id="brief-foot">${footText()}</div>
    </section>`;
  }

  // ---------- 4. "문장으로 보기" 다섯 줄 목록 ----------
  function rowsHTML(c) {
    return brief(c).map(b => {
      const k = b['줄'];
      const name = b['구역'] || ROW_NAME[k];
      const tab = App.TAB_BY_NAME[b['갈곳']] || 'brief';
      const flag = b['원문대조'] ? ui.flag(b['원문대조글'] || ui.FLAG_TEXT) : '';
      const extra = k === '다' ? limitLine(c) : '';
      const ch = justChanged.has(k) && lastNote.short ? `<span class="chg">${esc(lastNote.short)}</span>` : '';
      const n = String(ROW_NO[k]).padStart(2, '0');
      return `<li class="lrow brow${justChanged.has(k) ? ' just' : ''}" data-pick="${esc(k)}" data-scope="${b['범위'] === '전체 고객군' ? 'all' : 'base'}">
        <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${n} ${name}, ${b['범위']}. 근거 보기`)}"></button>
        ${flag}
        <div class="bstrip selbar">
          <span class="no num" aria-hidden="true"><span class="num-0">${n[0]}</span>${n[1]}</span>
          <span class="bn">${esc(name)}</span>
          ${ui.scope(b['범위'] === '전체 고객군' ? 'all' : 'base')}${ch}
          <span class="sp"></span>
          <span class="live">${ui.btn(`${b['갈곳']} 탭으로`, { sm: true, chev: true, attrs: `data-go="${tab}"${ROW_FOCUS[k] ? ` data-focus="${ROW_FOCUS[k]}"` : ''}` })}</span>
          <span class="bchev" aria-hidden="true">${ui.IC.chevR}</span>
        </div>
        <p class="btext">${esc(b['문장'])}</p>
        ${extra ? `<p class="bnow">${esc(extra)}</p>` : ''}
        <div class="bgo live">${ui.btn(`${b['갈곳']} 탭으로`, { sm: true, chev: true, attrs: `data-go="${tab}"${ROW_FOCUS[k] ? ` data-focus="${ROW_FOCUS[k]}"` : ''}` })}</div>
      </li>`;
    }).join('');
  }
  function rowsPanel(c) {
    const off = !c.isRef;
    return `<section class="panel brows" id="brief-rows" aria-labelledby="brief-rows-h">
      <div class="panel-h">
        <div><span class="k">다섯 줄의 차례는 탭 차례와 같습니다</span><h2 id="brief-rows-h">분석 요약 전체 문장</h2></div>
      </div>
      ${off ? `<p class="brief-off">지금 조건(${esc(App.condSummary().split(', 기준')[0])})은 대표 조건과 다릅니다. 다섯 줄의 문장은 대표 조건으로 계산한 값이고, 지금 고객군의 관문은 위 범위 띠에, 지금 나이의 주계약 한도는 (다) 줄 아래에 있습니다.</p>` : ''}
      <ol class="lrows" data-pick-group="brief">${rowsHTML(c)}</ol>
      <div class="panel-f" id="brief-foot">${footText()}</div>
    </section>`;
  }
  function footText() {
    const base = `${ui.scope('all')} 항목(01, 02)은 기준 종형과 조건을 바꿔도 그대로이고, ${ui.scope('base')} 항목(03, 04, 05)은 기준 종형을 따라 바뀝니다.`;
    return `<span>${(lastNote.long ? `<b style="font-weight:600">${esc(lastNote.long)}</b> ` : '') + base}</span>`;
  }

  // ---------- 5. 근거 기둥 ----------
  function sec(title, html, lo) { return `<div class="ev-sec${lo ? ' lo' : ''}">${title ? `<h3>${title}</h3>` : ''}${html}</div>`; }
  function pointItem(id) {
    const p = S['포인트'][id]; if (!p) return '';
    return `<li class="pt"><span class="tag">${esc(p['분류'])}</span> ${p['원문대조'] ? ui.flagText(p['원문대조글']) : ''}<p>${esc(p['문장'])}</p></li>`;
  }
  function segStrip(gv) {
    const lab = gv['라벨별'] || {};
    const list = [];
    for (const l of MAP_LABELS) for (let i = 0; i < (lab[l] || 0); i++) list.push(ui.MAP_CLS[l]);
    return list;
  }
  function pickedSegSec(c) {
    if (!focusSeg) return '';
    const m = App.mapOf(null);
    const row = m['행'][focusSeg.ri], col = m['열'][focusSeg.ci];
    const cell = (m['칸'][focusSeg.ri] || [])[focusSeg.ci];
    if (!row || !col || !cell) return '';
    const patch = App.segPatch(m, focusSeg.ri, focusSeg.ci, c.st);
    const same = App.samePatch(patch, c.st);
    const go = cell['관문만수집'] || [];
    const orgTxt = txt.ORG_ORDER.filter(o => o in cell['회사']).map(o => `${txt.orgShort(o)} ${cell['회사'][o]}`).join(', ');
    return sec(`고른 격자 칸: ${esc(row['이름'])}, ${col.lo}~${col.hi}세`,
      `<p>${ui.swatch(cell['라벨'])} <b style="font-weight:600">${esc(cell['라벨'])}</b>${cell['보조'] ? ` (${esc(cell['보조'])})` : ''}. ${esc(orgTxt)}.</p>`
      + (go.length ? `<p class="note">${esc(go.map(g => `${g['이름']}: ${g['안내'] || '관문만 수집(담보 미수집)'}`).join(', '))}</p>` : '')
      + (same ? '<p class="note">지금 조건이 이미 이 고객군입니다.</p>'
        : `<p class="note">누르면 조건 줄이 ${esc(txt.josa(App.segPatchText(patch), '으로'))} 바뀝니다.</p>${ui.btn('이 고객군으로 조건 바꾸기', { sm: true, attrs: `data-act="brief-apply-seg" data-ri="${focusSeg.ri}" data-ci="${focusSeg.ci}"` })}`));
  }

  function subEvSpec(i, c) {
    if (i === 0) return pick('가', c);
    if (i === 1) {
      const ra = line(c, '라');
      const rv = ra ? ra['값'] : {};
      const p = c.base['보류요약'] || {};
      const why = p['사유별'] || {};
      const whyT = Object.entries(why).map(([a, b]) => `${a} ${fmt(b)}`).join(', ');
      const whySum = Object.values(why).reduce((a, b) => a + b, 0);
      let body = sec('', `<p>${esc(ra ? ra['문장'] : '')}</p>`);
      body += sec('공통 담보 쌍의 구성', ui.eq({ total: { t: '공통 담보', n: rv['공통담보쌍'] }, parts: [{ t: '견줌', n: rv['견준쌍'] }, { t: '검토 대기로 뺌', n: rv['뺀비교쌍'] }], tail: '쌍' })
        + (whyT ? `<div class="nadd">검토 대기 사유는 ${esc(whyT)}입니다. 한 쌍에 두 사유가 함께 들 수 있어 더하면 ${txt.josa(fmt(whySum), '으로')} ${fmt(rv['뺀비교쌍'])}보다 큽니다.</div>` : ''));
      body += sec('', ui.btn('담보 비교 탭에서 자세히', { main: true, chev: true, attrs: 'data-go="cover"' }), true);
      return { kicker: '하단 도형 02', title: '견준 공통 담보 쌍', badges: [ui.scope('base')], body };
    }
    const j = c.base['치료여정'];
    const steps = j['열'] || [];
    const cols = j['종형'] || [];
    const ours = cols.find(x => x['종형ID'] === c.baseId) || cols[0];
    const parts = steps.map(s => ({ t: s, n: ours['합계'][s] || 0 })).concat(ours['기타'] ? [{ t: '기타', n: ours['기타'] }] : []);
    let body = sec('치료 여정 다섯 단계', ui.eq({ total: { t: '우체국 담보', n: ours['전체'] }, parts, tail: '개' })
      + `<div class="nadd">회사별 담보 수(${cols.map(x => `${esc(txt.orgShort(x['종형ID'].split('_')[0]))} ${fmt(x['전체'])}`).join(', ')})는 같은 담보를 회사마다 세므로 서로 더하지 않습니다.</div>`);
    body += sec('', ui.btn('치료 여정 격자 보기', { main: true, chev: true, attrs: 'data-go="cover" data-focus="journey"' }), true);
    return { kicker: '하단 도형 03', title: '치료 여정 다섯 단계', badges: [ui.scope('base')], body };
  }

  function pick(key, c) {
    const si = subOf(key);
    if (si > 0) return subEvSpec(si, c);
    const b = line(c, key); if (!b) return null;
    const v = b['값'] || {};
    const scopeB = ui.scope(b['범위'] === '전체 고객군' ? 'all' : 'base');
    const name = b['구역'] || ROW_NAME[key];
    const tab = App.TAB_BY_NAME[b['갈곳']];
    const goBtn = ui.btn(`${b['갈곳']} 탭에서 자세히`, { main: true, chev: true, attrs: `data-go="${tab}"${ROW_FOCUS[key] ? ` data-focus="${ROW_FOCUS[key]}"` : ''}` });
    const head = sec('', `<p>${esc(b['문장'])}</p>${b['원문대조'] ? `<p>${ui.flagText(b['원문대조글'])}</p>` : ''}`);
    let body = (key === '가' ? pickedSegSec(c) : '') + head;
    if (key === '가') {
      const lab = v['라벨별'] || {};
      const m = App.mapOf(null);
      const only = [];
      m['칸'].forEach((r, ri) => r.forEach((cell, ci) => { if (cell['라벨'] === '우리 간편만 열림') only.push({ r: m['행'][ri], col: m['열'][ci], cell }); }));
      body += sec('칸의 수', ui.eq({ total: { t: '고객군', n: v['전체칸수'] }, parts: MAP_LABELS.map(l => ({ t: l, n: lab[l] || 0 })) }) + ui.cells(segStrip(v)));
      body += sec('우리 간편만 열리는 칸', only.length ? `<ul class="evl">${only.map(o => `<li><b>${esc(o.r['이름'])}, ${o.col.lo}~${o.col.hi}세</b><br><span class="note">우리 대표 종형 ${esc(o.cell['대표'] ? txt.vkind(o.cell['대표']) : '없음')}. ${txt.ORG_ORDER.filter(x => x !== 'EPOST').map(x => `${txt.orgShort(x)} ${o.cell['회사'][x]}`).join(', ')}</span></li>`).join('')}</ul>` : '<p>없습니다.</p>');
      body += sec('', `<p class="note">고객군 지도(${esc(txt.sexText(m['성별']))}, 갱신 유형 전체)로 셉니다. 조건 줄의 나이와 이력, 기준 종형을 바꿔도 이 줄은 그대로입니다.</p>${goBtn}`, true);
    } else if (key === '나') {
      const rv = S['개정변동'], nw = S['시장소식'];
      const pairs = rv['짝'].map(p => `<li><b>${esc(txt.vkind(p['후']))}</b>: 직전 종형과 견주어 신설 ${p['신설']}, 변경 ${p['변경']}, 종료 ${p['종료']}</li>`).join('');
      const pairSum = rv['짝'].reduce((a, p) => a + p['신설'] + p['변경'] + p['종료'], 0);
      body += sec('개정 변동', ui.eq({ total: { t: '달라진 담보', n: v['개정변동수'] }, parts: [{ t: '신설', n: v['개정신설'] }, { t: '변경', n: v['개정변경'] }, { t: '종료', n: v['개정종료'] }], tail: '건' })
        + `<ul class="evl">${pairs}</ul><div class="nadd">개정 짝 ${rv['짝'].length}개의 수를 더하면 ${pairSum}건입니다. 같은 담보가 여러 짝에서 바뀌어 짝마다 세므로 ${v['개정변동수']}건보다 큽니다.</div>`);
      const cls = Object.entries(nw['분류별'] || {});
      body += sec(`시장 소식 ${esc(nw['주차'])}`, ui.eq({ total: { t: '소식', n: nw['건수'] }, parts: cls.map(([a, n]) => ({ t: a, n })), tail: '건' })
        + `<p class="note">표준담보에 이어진 소식 ${fmt(nw['연결'])}건. ${esc(nw['인용안내'])}</p>`);
      body += sec('', goBtn, true);
    } else if (key === '다') {
      const L = c.limit;
      const segs = L && L.table ? (L.table['구간'][c.st.sex] || []) : [];
      const gp = (c.base['포인트'] || []).filter(id => S['포인트'][id] && S['포인트'][id]['분류'] === '관문 차이');
      body += sec('값', `<dl class="kv"><dt>가입나이</dt><dd class="num">${v['우리최저']}~${v['우리최고']}세</dd>
        <dt>대표 조건 ${v['나이']}세의 주계약 한도</dt><dd class="num">${esc(v['주계약한도만원'])}만원</dd>
        <dt>고지 질문이 다른 곳</dt><dd class="num">${fmt(v['관문차이수'])}건</dd>
        <dt>갱신이나 환급 구조가 다른 상대</dt><dd class="num">${fmt(v['구조다름회사수'])}곳</dd></dl>`);
      body += sec(`나이 구간별 주계약 최대 가입금액(${esc(txt.sexText(c.st.sex))})`, segs.length ? `<dl class="kv">${segs.map(g => `<dt class="num">${g.lo}~${g.hi}세</dt><dd class="num">${fmt(g.max)}만원${g.pend ? ' (검토 대기)' : ''}</dd>`).join('')}</dl>${limitLine(c) ? `<p class="note">${esc(limitLine(c))}</p>` : ''}` : '<p>한도 자료 없음: 이 종형의 한도 표가 아직 없습니다.</p>');
      body += sec(`관문 차이 ${gp.length}건`, gp.length ? `<ul class="evl">${gp.map(pointItem).join('')}</ul>` : '<p>일반심사 종형이라 간편 고지 질문을 견주지 않았습니다.</p>');
      body += sec('', goBtn, true);
    } else if (key === '라') {
      const cau = c.base['단정주의'] || [];
      const kinds = {};
      cau.forEach(x => { (kinds[x['종류']] = kinds[x['종류']] || []).push(x); });
      body += sec('쌍과 담보의 수', ui.eq({ total: { t: '공통 담보', n: v['공통담보쌍'] }, parts: [{ t: '견줌', n: v['견준쌍'] }, { t: '검토 대기', n: v['뺀비교쌍'] }], tail: '쌍' })
        + ui.eq({ total: { t: '우체국 담보', n: v['보유수'] }, parts: ['진단', '수술', '치료', '입원', '통원'].map(s => ({ t: s, n: v[s + '수'] })).concat(v['기타수'] ? [{ t: '기타', n: v['기타수'] }] : []), tail: '개' })
        + `<div class="nadd">쌍은 우체국과 상대가 함께 가진 담보의 짝이고, 담보 수는 우체국만 센 것이라 서로 더하지 않습니다.</div>`);
      body += sec(`단정 주의 ${cau.length}건`, Object.entries(kinds).map(([kd, xs]) => `<p class="note" style="margin-top:6px"><b style="font-weight:600">${esc(kd)}</b> ${xs.length}건</p><ul class="evl">${xs.map(x => `<li>${ui.verdict('diff')} <b>${esc(x['담보'])}</b><p>${esc(x['문장'])}</p></li>`).join('')}</ul>`).join(''));
      body += sec('', goBtn, true);
    } else if (key === '마') {
      const cnt = c.base['분류집계'] || {};
      const firsts = (c.base['먼저'] && c.base['먼저']['브리핑']) || [];
      const total = Object.values(cnt).reduce((a, n) => a + n, 0);
      body += sec('다섯 분류', ui.eq({ total: { t: '인사이트', n: total }, parts: S['분류'].map(k => ({ t: k, n: cnt[k] || 0 })), tail: '건' })
        + `<p class="note">다섯 분류는 서로 겹치지 않습니다. 검토 대기 등으로 뺀 포인트 ${fmt((c.base['뺀포인트'] || []).length)}건은 세지 않았습니다.</p>`);
      body += sec(`먼저 볼 것 ${firsts.length}건`, `<ul class="evl">${firsts.map(pointItem).join('')}</ul>`);
      body += sec('', goBtn, true);
    }
    return { kicker: `${String(ROW_NO[key]).padStart(2, '0')} ${b['범위']}`, title: name, badges: [scopeB], body };
  }

  // ---------- 6. 그리기와 상호작용 ----------
  function render(body, c) {
    if (c.aside) c.aside.innerHTML = headAsideHTML(c);
    body.innerHTML = viewMode === 'medal' ? stageHTML(c) : rowsPanel(c);
    bind(body, c);
    lastBase = c.baseId;
  }

  // 하단 판의 강조(is-on)를 고른 key 에 맞춘다. 지표 단추는 빨강 대신 먹색 밑줄과 옅은 면으로 고른 것을 보인다
  function syncSub(key) {
    const view = document.getElementById('view-brief');
    if (!view) return;
    const i = subOf(key);
    view.querySelectorAll('.bsub').forEach(el => el.classList.toggle('is-on', +el.dataset.sub === i));
    view.querySelectorAll('[data-act="kpi"]').forEach(b => {
      const on = +b.dataset.i === i;
      b.classList.toggle('is-on', on);
      b.setAttribute('aria-pressed', String(on));
    });
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
          if (curSel != null) App.select(curSel, { open: false, reveal: false, animate: false });
          if (viewMode === 'medal' && App.motionOn()) ui.drawRings(body);
          return;
        }
        if (e.target.closest('[data-act="brief-copy"]')) {
          const cc = App.ctx();
          App.copyRows(['줄', '구역', '범위', '문장', '갈 곳'], brief(cc).map(b => [`(${b['줄']})`, b['구역'] || ROW_NAME[b['줄']], b['범위'], b['문장'] + (b['원문대조'] ? ` [${b['원문대조글']}]` : ''), b['갈곳']]), { title: '브리핑 분석 요약' });
        }
      });
    }
    if (!body._b) {
      body._b = true;
      body.addEventListener('click', e => {
        const kb = e.target.closest('[data-act="kpi"]');
        if (kb) { App.select(SUB_KEY[+kb.dataset.i], { reveal: false }); return; }
        const mc = e.target.closest('[data-act="bmap-cell"]');
        if (mc) {
          focusSeg = { ri: +mc.dataset.ri, ci: +mc.dataset.ci };
          body.querySelectorAll('.bm-cell').forEach(el => el.classList.toggle('is-focus', el === mc));
          App.select('가', { reveal: false });
        }
      });
    }
    if (!document._briefEvBound) {
      document._briefEvBound = true;
      document.addEventListener('click', e => {
        const ab = e.target.closest('[data-act="brief-apply-seg"]');
        if (!ab) return;
        const patch = App.segPatch(App.mapOf(null), +ab.dataset.ri, +ab.dataset.ci, App.state);
        if (!patch) return;
        App.set(patch);
        App.toast(`조건을 바꿨습니다: ${App.condSummary()}`);
      });
      // 메달을 고를 때 그 메달의 고리가 채워지는 움직임
      App.on('select', (tab, key) => {
        if (tab !== 'brief') return;
        syncSub(key);
        if (!key || !App.motionOn()) return;
        const view = document.getElementById('view-brief');
        const el = view && view.querySelector(`.bmedal[data-pick="${CSS.escape(key)}"]`);
        if (el) ui.drawRings(el);
      });
    }
  }

  function update(body, c) {
    justChanged.clear();
    if (c.changed.has('base') && lastBase && lastBase !== c.baseId) {
      brief(c).forEach(b => { if (b['범위'] !== '전체 고객군') justChanged.add(b['줄']); });
      const from = txt.vkind(lastBase), to = txt.vkind(c.baseId);
      lastNote = { short: '다시 계산', long: `기준 종형을 ${from}에서 ${txt.josa(to, '으로')} 바꿨습니다. 선택 종형 항목 셋은 다시 셌고 전체 고객군 항목 둘은 그대로입니다.` };
    } else if (['age', 'sex', 'since', 'surg'].some(k => c.changed.has(k))) {
      lastNote = { short: '', long: '조건을 바꿔도 메달의 대표 값은 대표 조건 기준이라 그대로입니다. 바뀐 것은 범위 띠, 24칸 격자의 지금 표지, 03번 메달의 지금 나이 한도입니다.' };
      if (!c.isRef) { justChanged.add('다'); lastNote.short = '지금 조건 반영'; }
    } else if (c.changed.has('renewal')) {
      lastNote = { short: '', long: '갱신 유형 거르개는 고객군 지도 탭에만 씁니다. 브리핑의 01번 메달과 24칸 격자는 갱신 유형 전체 기준입니다.' };
    }
    render(body, c);
    if (justChanged.size && App.motionOn() && viewMode === 'medal') {
      justChanged.forEach(k => {
        const el = body.querySelector(`.bmedal[data-pick="${CSS.escape(k)}"]`);
        if (el) ui.drawRings(el);
      });
    }
    return true;
  }

  let enterTimer = 0;
  function enter(body, c) {
    const view = document.getElementById('view-brief');
    if (!view || !App.motionOn()) return;
    clearTimeout(enterTimer);
    view.classList.remove('b-enter');
    void view.offsetWidth;
    view.classList.add('b-enter');
    enterTimer = setTimeout(() => view.classList.remove('b-enter'), 580);
  }

  return { id: 'brief', kicker: '분석 요약', render, update, pick, enter };
})());
