/* 탭 1 브리핑: 주인공 도형은 진행 고리와 "큰 숫자/분모", 번호 01~05 의 분석 요약 다섯 줄.
   값과 문장은 sales.json 의 기준별[종형].브리핑, 지도, 범위, 치료여정, 보류요약에서 읽는다. 화면이 숫자를 지어내지 않는다. */
App.registerTab((function () {
  const { ui, txt } = App;
  const { esc, fmt } = ui;
  const S = App.S;
  const ROW_NAME = { '가': '고객군 지형', '나': '개정과 시장', '다': '가입 관문과 한도', '라': '담보 포지션', '마': '영업 인사이트' };
  const ROW_FOCUS = { '가': 'map', '나': 'news', '다': '', '라': 'journey', '마': '' };
  const ROW_NO = { '가': 1, '나': 2, '다': 3, '라': 4, '마': 5 };
  let kpiSel = 0;
  let lastBase = null;
  let lastNote = { short: '', long: '' };
  const justChanged = new Set();

  const brief = c => (c.base ? c.base['브리핑'] : []);
  const line = (c, k) => brief(c).find(b => b['줄'] === k) || null;
  const MAP_LABELS = S['라벨'];

  // ---------- 지표 셋 ----------
  function kpiData(c) {
    const ga = line(c, '가'), ra = line(c, '라');
    const gv = ga ? ga['값'] : {}, rv = ra ? ra['값'] : {};
    const j = c.base ? c.base['치료여정'] : null;
    const ours = j ? j['종형'].find(x => x['종형ID'] === c.baseId) || j['종형'][0] : null;
    const steps = j ? j['열'] : [];
    const have = ours ? steps.filter(s => (ours['합계'][s] || 0) > 0).length : 0;
    return [
      { key: 'seg', scope: 'all', label: '우리 간편이 열리는 고객군', unit: '칸',
        v: (gv['우리간편만열림칸수'] || 0) + (gv['함께열림칸수'] || 0), max: gv['전체칸수'] || 0,
        segs: [{ v: gv['우리간편만열림칸수'] || 0, cls: 'gold' }, { v: gv['함께열림칸수'] || 0, cls: '' }],
        sub: `우리 간편만 열림 ${fmt(gv['우리간편만열림칸수'] || 0)}, 함께 열림 ${fmt(gv['함께열림칸수'] || 0)}`, lead: true },
      { key: 'pair', scope: 'base', label: '견준 공통 담보 쌍', unit: '쌍',
        v: rv['견준쌍'] || 0, max: rv['공통담보쌍'] || 0, sub: `검토 대기로 뺀 쌍 ${fmt(rv['뺀비교쌍'] || 0)}` },
      { key: 'step', scope: 'base', label: '우체국 담보가 있는 치료 단계', unit: '단계',
        v: have, max: steps.length, sub: ours ? `담보 ${fmt(ours['전체'])}개, ${steps.filter(s => !(ours['합계'][s] > 0)).map(s => s + ' 0').join(', ') || '빈 단계 없음'}` : '' },
    ];
  }
  function kpiTabs(c) {
    const ks = kpiData(c);
    return `<div class="kpis pillar" role="tablist" aria-label="브리핑 지표">${ks.map((k, i) => {
      const on = i === kpiSel;
      const pct = k.max > 0 ? Math.round(k.v / k.max * 100) + '%' : '';
      return `<button type="button" class="kpi${on ? ' is-on on-slate' : ''}" role="tab" id="kpi-${k.key}" aria-selected="${on}" aria-controls="kpi-detail" tabindex="${on ? 0 : -1}" data-act="kpi" data-i="${i}">
        ${ui.ring({ v: k.v, max: k.max, segs: k.segs, lead: k.lead, pct, label: `${k.label} ${k.v}/${k.max}` })}
        <span class="kpi-x"><span class="kpi-n">${ui.big(k.v, k.max)}<span class="kpi-u">${esc(k.unit)}</span></span>
          <span class="kpi-l">${esc(k.label)}</span>
          <span class="kpi-s">${ui.scope(k.scope)}<span class="sub">${esc(k.sub)}</span></span></span>
      </button>`;
    }).join('')}</div>`;
  }

  // ---------- 지표 풀이(R5: 전체와 부분의 관계) ----------
  function segStrip(gv) {
    const lab = gv['라벨별'] || {};
    const list = [];
    for (const l of MAP_LABELS) for (let i = 0; i < (lab[l] || 0); i++) list.push(ui.MAP_CLS[l]);
    return list;
  }
  function kpiDetail(c) {
    const k = kpiData(c)[kpiSel];
    const ga = line(c, '가'), ra = line(c, '라');
    const gv = ga ? ga['값'] : {}, rv = ra ? ra['값'] : {};
    const m = App.mapOf(null);
    if (k.key === 'seg') {
      const lab = gv['라벨별'] || {};
      return `<div class="kd">
        <div class="kd-a">
          <h3>고객군 ${fmt(gv['전체칸수'])}칸의 관문 ${ui.scope('all')}</h3>
          ${ui.eq({ total: { t: '고객군', n: gv['전체칸수'] }, parts: MAP_LABELS.map(l => ({ t: l, n: lab[l] || 0 })) })}
          <p class="note">칸 하나는 이력 ${m['행'].length}줄과 나이 ${m['열'].length}구간(${m['열'].map(x => `${x.lo}~${x.hi}세`).join(', ')})이 만나는 고객군입니다(${esc(txt.sexText(m['성별']))}, 갱신 유형 전체 지도).</p>
        </div>
        <div class="kd-b">
          ${ui.cells(segStrip(gv))}
          <ul class="kd-lg">${MAP_LABELS.map(l => `<li>${ui.swatch(l)}<span>${esc(l)}</span><b class="num">${fmt(lab[l] || 0)}</b></li>`).join('')}</ul>
        </div>
        <div class="kd-go live">${ui.btn('고객군 지도 보기', { sm: true, chev: true, attrs: 'data-go="market" data-focus="map"' })}</div></div>`;
    }
    if (k.key === 'pair') {
      const p = c.base['보류요약'];
      const rows = (p['대분류'] || []).map(x => `<li><span class="mj">${esc(x['대분류'])}</span>${ui.cells(Array(x['견준쌍']).fill('cmp').concat(Array(x['뺀쌍']).fill('wait')))}<span class="num">${fmt(x['견준쌍'])}+${fmt(x['뺀쌍'])}</span></li>`).join('');
      const why = p['사유별'] || {};
      const whyT = Object.entries(why).map(([a, b]) => `${a} ${fmt(b)}`).join(', ');
      const whySum = Object.values(why).reduce((a, b) => a + b, 0);
      return `<div class="kd">
        <div class="kd-a">
          <h3>공통 담보 ${fmt(rv['공통담보쌍'])}쌍 ${ui.scope('base')}</h3>
          ${ui.eq({ total: { t: '공통 담보', n: rv['공통담보쌍'] }, parts: [{ t: '견줌', n: rv['견준쌍'] }, { t: '검토 대기로 뺌', n: rv['뺀비교쌍'] }], tail: '쌍' })}
          ${whyT ? `<div class="nadd">검토 대기 사유는 ${esc(whyT)}입니다. 한 쌍에 두 사유가 함께 들 수 있어 더하면 ${txt.josa(fmt(whySum), '으로')} ${fmt(rv['뺀비교쌍'])}보다 큽니다.</div>` : ''}
          <p class="note">맞붙는 상대 ${esc(txt.josa(c.peerIds.map(v => txt.vname(v)).join(', '), '와'))} 견준 쌍입니다.</p>
        </div>
        <div class="kd-b">
          <ul class="kd-mj">${rows}</ul>
          <ul class="kd-lg"><li><i class="cq cmp"></i><span>견준 쌍</span></li><li><i class="cq wait"></i><span>검토 대기로 뺀 쌍</span></li></ul>
        </div>
        <div class="kd-go live">${ui.btn('담보 비교 보기', { sm: true, chev: true, attrs: 'data-go="cover"' })}</div></div>`;
    }
    // 치료 여정
    const j = c.base['치료여정'];
    const steps = j['열'];
    const cols = j['종형'];
    const max = Math.max(1, ...cols.flatMap(x => steps.map(s => x['합계'][s] || 0)));
    const ours = cols.find(x => x['종형ID'] === c.baseId) || cols[0];
    const parts = steps.map(s => ({ t: s, n: ours['합계'][s] || 0 })).concat(ours['기타'] ? [{ t: '기타', n: ours['기타'] }] : []);
    const bars = steps.map(s => `<div class="jc"><div class="jb">${cols.map((x, i) => {
      const n = x['합계'][s] || 0;
      return `<span class="b b${i}" style="height:${Math.max(n ? 3 : 0, Math.round(n / max * 40))}px" title="${esc(txt.orgShort(x['종형ID'].split('_')[0]))} ${n}"></span>`;
    }).join('')}</div><div class="jn num">${cols.map(x => `<span>${x['합계'][s] || 0}</span>`).join('')}</div><div class="js">${esc(s)}</div></div>`).join('');
    return `<div class="kd">
      <div class="kd-a">
        <h3>치료 여정 다섯 단계 ${ui.scope('base')}</h3>
        ${ui.eq({ total: { t: '우체국 담보', n: ours['전체'] }, parts, tail: '개' })}
        <div class="nadd">회사별 담보 수(${cols.map(x => `${esc(txt.orgShort(x['종형ID'].split('_')[0]))} ${fmt(x['전체'])}`).join(', ')})는 같은 담보를 회사마다 세므로 서로 더하지 않습니다.</div>
      </div>
      <div class="kd-b">
        <div class="jg" role="img" aria-label="단계별 회사 담보 수">${bars}</div>
        <ul class="kd-lg">${cols.map((x, i) => `<li><i class="b b${i}"></i><span title="${esc(x['이름'])}">${esc(txt.orgShort(x['종형ID'].split('_')[0]))}</span></li>`).join('')}</ul>
      </div>
      <div class="kd-go live">${ui.btn('치료 여정 격자 보기', { sm: true, chev: true, attrs: 'data-go="cover" data-focus="journey"' })}</div></div>`;
  }

  // ---------- 분석 요약 다섯 줄 ----------
  function limitLine(c) {
    const L = c.limit;
    if (!L || (c.st.age === c.ref['나이'] && c.st.sex === c.ref['성별'])) return '';
    const who = `${c.st.age}세 ${txt.sexText(c.st.sex)}`;
    const kind = txt.vkind(c.baseId);
    if (!L.hit) return `지금 조건 ${who}: ${kind}의 가입나이(${L.lo}~${L.hi}세) 밖입니다.`;
    return `지금 조건 ${who}: 주계약 최대 가입금액 ${fmt(L.hit.max)}만원(나이 구간별 한도 표의 ${L.hit.lo}~${L.hit.hi}세 구간${L.hit.pend ? ', 검토 대기' : ''}${L.table['성별같음'] ? ', 남녀 같음' : ''}).`;
  }
  function rowsHTML(c) {
    return brief(c).map(b => {
      const k = b['줄'];
      const name = b['구역'] || ROW_NAME[k];
      const tab = App.TAB_BY_NAME[b['갈곳']] || 'brief';
      const flag = b['원문대조'] ? ui.flag(b['원문대조글'] || ui.FLAG_TEXT) : '';
      const extra = k === '다' ? limitLine(c) : '';
      const ch = justChanged.has(k) ? `<span class="chg">${esc(lastNote.short)}</span>` : '';
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
  function refText(c) {
    return `${c.ref['나이']}세 ${txt.sexText(c.ref['성별'])}, ${txt.sinceText(c.ref['이력'])}`;
  }
  function rowsPanel(c) {
    const off = !c.isRef;
    return `<section class="panel brows" id="brief-rows" aria-labelledby="brief-rows-h">
      <div class="panel-h">
        <div><span class="k">다섯 줄의 차례는 탭 차례와 같습니다</span><h2 id="brief-rows-h">분석 요약</h2></div>
        <div class="r"><span>대표 조건 <b class="num" style="font-weight:600">${esc(refText(c))}</b></span><span>기준 종형 <b style="font-weight:600">${esc(txt.vkind(c.baseId))}</b></span>
          <span class="live">${ui.btn('요약 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="brief-copy"' })}</span></div>
      </div>
      ${off ? `<p class="brief-off">지금 조건(${esc(App.condSummary().split(', 기준')[0])})은 대표 조건과 다릅니다. 다섯 줄의 문장은 대표 조건으로 계산한 값이고, 지금 고객군의 관문은 위 범위 띠에, 지금 나이의 주계약 한도는 (다) 줄 아래에 있습니다.</p>` : ''}
      <ol class="lrows" data-pick-group="brief">${rowsHTML(c)}</ol>
      <div class="panel-f" id="brief-foot">${footText(c)}</div>
    </section>`;
  }
  function footText(c) {
    const base = `${ui.scope('all')} 줄(가, 나)은 기준 종형과 조건을 바꿔도 그대로이고, ${ui.scope('base')} 줄(다, 라, 마)은 기준 종형을 따라 바뀝니다.`;
    return (lastNote.long ? `<b style="font-weight:600">${esc(lastNote.long)}</b> ` : '') + base;
  }

  // ---------- 근거 기둥 ----------
  function sec(title, html, lo) { return `<div class="ev-sec${lo ? ' lo' : ''}">${title ? `<h3>${title}</h3>` : ''}${html}</div>`; }
  function pointItem(id) {
    const p = S['포인트'][id]; if (!p) return '';
    return `<li class="pt"><span class="tag">${esc(p['분류'])}</span> ${p['원문대조'] ? ui.flagText(p['원문대조글']) : ''}<p>${esc(p['문장'])}</p></li>`;
  }
  function pick(key, c) {
    const b = line(c, key); if (!b) return null;
    const v = b['값'] || {};
    const scopeB = ui.scope(b['범위'] === '전체 고객군' ? 'all' : 'base');
    const name = b['구역'] || ROW_NAME[key];
    const tab = App.TAB_BY_NAME[b['갈곳']];
    const goBtn = ui.btn(`${b['갈곳']} 탭에서 자세히`, { main: true, chev: true, attrs: `data-go="${tab}"${ROW_FOCUS[key] ? ` data-focus="${ROW_FOCUS[key]}"` : ''}` });
    const head = sec('', `<p>${esc(b['문장'])}</p>${b['원문대조'] ? `<p>${ui.flagText(b['원문대조글'])}</p>` : ''}`);
    let body = head;
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

  // ---------- 그리기 ----------
  function render(body, c) {
    if (c.aside) c.aside.innerHTML = kpiTabs(c);
    body.innerHTML = `<div class="kpi-detail panel slate" id="kpi-detail" role="tabpanel" aria-labelledby="kpi-${kpiData(c)[kpiSel].key}">${kpiDetail(c)}</div>${rowsPanel(c)}`;
    bind(body, c);
    lastBase = c.baseId;
  }
  function bind(body, c) {
    const aside = c.aside;
    if (aside && !aside._b) {
      aside._b = true;
      aside.addEventListener('click', e => {
        const b = e.target.closest('[data-act="kpi"]'); if (!b) return;
        setKpi(+b.dataset.i, true);
      });
      aside.addEventListener('keydown', e => {
        if (!e.target.closest('[data-act="kpi"]')) return;
        const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
        if (!d) return;
        e.preventDefault(); setKpi((kpiSel + d + 3) % 3, true);
        const nb = aside.querySelector(`[data-i="${kpiSel}"]`); if (nb) nb.focus();
      });
    }
    if (!body._b) {
      body._b = true;
      body.addEventListener('click', e => {
        if (e.target.closest('[data-act="brief-copy"]')) {
          const cc = App.ctx();
          App.copyRows(['줄', '구역', '범위', '문장', '갈 곳'], brief(cc).map(b => [`(${b['줄']})`, b['구역'] || ROW_NAME[b['줄']], b['범위'], b['문장'] + (b['원문대조'] ? ` [${b['원문대조글']}]` : ''), b['갈곳']]), { title: '브리핑 분석 요약' });
        }
      });
    }
  }
  function setKpi(i, user) {
    kpiSel = i;
    const c = App.ctx();
    const view = document.getElementById('view-brief');
    const aside = view.querySelector('.vhead-aside');
    aside.querySelectorAll('[data-act="kpi"]').forEach((b, j) => {
      const on = j === i;
      b.classList.toggle('is-on', on); b.classList.toggle('on-slate', on);
      b.setAttribute('aria-selected', String(on)); b.tabIndex = on ? 0 : -1;
    });
    const d = view.querySelector('#kpi-detail');
    d.innerHTML = kpiDetail(c);
    d.setAttribute('aria-labelledby', 'kpi-' + kpiData(c)[i].key);
    if (App.motionOn()) { d.classList.remove('kd-in'); void d.offsetWidth; d.classList.add('kd-in'); }
    if (user && App.mode() === 'sheet') App.reveal(d);
  }
  function update(body, c) {
    // 기준 종형이 바뀌면 선택 종형 줄(다, 라, 마)만 바뀐다는 것을 보인다(R11)
    justChanged.clear();
    if (c.changed.has('base') && lastBase && lastBase !== c.baseId) {
      brief(c).forEach(b => { if (b['범위'] !== '전체 고객군') justChanged.add(b['줄']); });
      const from = txt.vkind(lastBase), to = txt.vkind(c.baseId);
      lastNote = { short: '다시 계산', long: `기준 종형을 ${from}에서 ${txt.josa(to, '으로')} 바꿨습니다. 선택 종형 줄 셋은 다시 셌고 전체 고객군 줄 둘은 그대로입니다.` };
    } else if (['age', 'sex', 'since', 'surg'].some(k => c.changed.has(k))) {
      lastNote = { short: '', long: '조건을 바꿔도 다섯 줄의 문장은 대표 조건 기준이라 그대로입니다. 바뀐 것은 범위 띠의 관문 한 줄과 (다) 줄 아래의 지금 나이 한도입니다.' };
      if (!c.isRef) justChanged.add('다');
      if (justChanged.has('다')) lastNote.short = '지금 조건 반영';
    } else if (c.changed.has('renewal')) {
      lastNote = { short: '', long: '갱신 유형 거르개는 고객군 지도 탭에만 씁니다. 브리핑의 (가) 줄과 첫 고리는 갱신 유형 전체 기준입니다.' };
    }
    render(body, c);
    if (justChanged.size && App.motionOn()) App.ui.drawRings(c.aside);
    return true;
  }
  function enter(body, c) {
    const d = body.querySelector('#kpi-detail');
    if (d && App.motionOn()) { d.classList.remove('kd-in'); void d.offsetWidth; d.classList.add('kd-in'); }
  }

  return { id: 'brief', kicker: '분석 요약', render, update, pick, enter };
})());
