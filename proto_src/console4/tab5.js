/* 탭 5 영업 인사이트. 왼쪽 열은 분류 목차(유일한 분류별 건수 표시), 가운데 열은 한 줄 요약 막대와 분류별 목록,
   오른쪽 열의 기본 내용은 응대 화법 미리 보기(위 2.5px 금색 선의 짙은 결과 카드)다.
   항목 근거를 열면 오른쪽 열이 상세 패널로 전환되고, 닫거나 되돌아가기 단추를 누르면 응대 화법 미리 보기로 돌아온다.
   값과 문장은 sales.json 에서만 읽고, 관계도는 탭 4 가 내보낸 App.cover 를 쓴다(같은 판정, R10). */
App.registerTab((function () {
  const { ui, txt } = App;
  const { esc, fmt } = ui;
  const S = App.S;
  const CATS = S['분류'];
  const CARD_ORDER = S['카드분류차례'];
  const PURPOSES = S['목적'];
  const MARK = '내부 교육·비교 참고용(대외 배포 금지)';
  let purpose = null;
  const picks = {};          // 기준 종형 -> 응대 화법에 추가할 포인트ID 집합
  const openOmit = new Set(); // 펼친 "제외 항목" 묶음

  // ---------- 확정 용어(요청 35 9절, S.표시명 우선)와 내부 코드 비노출(6-6) ----------
  const dispMap = S['표시명'] || {};
  const CAT_LABEL = {
    '관문 차이': '인수기준 차이',
    '앞세울 강점': '우위 담보',
    '조건 열위 방어': '열위 담보',
    '개정 검토 후보': '미보유 담보',
    '관련 담보 안내': '관련 담보',
  };
  const catLabel = k => dispMap[k] || CAT_LABEL[k] || k;

  const SUB = {
    '관문 차이': ['G1', 'G2', 'G3'],
    '앞세울 강점': ['A1', 'A2'],
    '관련 담보 안내': ['Q1'],
    '조건 열위 방어': ['Q3'],
    '개정 검토 후보': ['Q2'],
  };
  const SUB_LABEL = {
    G1: '우체국만 가입 가능',
    G2: '우체국만 가입 제한',
    G3: '고지 범위 상이',
    A1: '단독 보유 담보',
    A2: '조건 우위',
    Q1: '관련 담보 있음',
    Q2: '미보유',
    Q3: '조건 열위',
  };
  const RAW_SUB_NAME = {};
  Object.values(S['포인트']).forEach(p => { if (p['세부'] && p['세부이름']) RAW_SUB_NAME[p['세부']] = p['세부이름']; });
  const subLabel = (code, fallback) => dispMap[code] || SUB_LABEL[code] || fallback || RAW_SUB_NAME[code] || '';
  const STATE_LABEL = { '열림': '가입 가능', '닫힘': '가입 제한' };
  const stateLabel = s => dispMap[s] || STATE_LABEL[s] || s || '';

  // ---------- 이름과 글 ----------
  const vinfo = v => S['종형'][v] || {};
  const orgOf = v => vinfo(v)['기관코드'] || String(v).split('_')[0];
  const orgN = v => txt.orgShort(orgOf(v));
  const fullN = v => vinfo(v)['이름'] || v;
  const kindN = v => vinfo(v)['종형명'] || v;
  const stdN = sid => ((S['표준담보'][sid] || {})['이름'] || sid);
  const VID_RE = /\b[A-Z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+\b/g;
  const reasonText = x => String(x == null ? '' : x).replace(VID_RE, m => fullN(m));
  const head = p => (p && p['머리말'] != null ? S['글'][p['머리말']] || '' : '');
  const evChip = g => ui.tag(`${orgN(g['종형ID'])} ${txt.pageText(g['문서'], g['쪽'])}`, g['급부명'] ? `${fullN(g['종형ID'])}: ${g['급부명']}` : `${fullN(g['종형ID'])} ${g['문서']}`, 'doc');
  const VK = { A1: 'only', A2: 'better', Q3: 'worse', Q1: 'none', Q2: 'none' };

  /** 포인트의 담보가 기준 종형의 단정 주의에도 들면 그 항목(같은 타사). 본문, 근거 패널, 응대 화법 모두 "우열을 매기지 않음"으로 보인다(R10) */
  function cautionOf(c, p) {
    if (!c || !c.base || !p || !p['표준담보ID']) return null;
    const peers = p['비교종형ID'] || [];
    return (c.base['단정주의'] || []).find(x => x['표준담보ID'] === p['표준담보ID'] && (x['상대종형ID'] || []).some(v => !peers.length || peers.includes(v))) || null;
  }
  const cautionNote = x => `단정 주의(${x['종류']})에도 든 담보라 우열을 매기지 않습니다. 위 문장의 차이는 사실로만 씁니다.`;

  function pointChip(p, c) {
    if (cautionOf(c, p)) return ui.verdict('diff');
    const k = VK[p['세부']];
    return k ? ui.verdict(k) : '';
  }

  const titleOf = p => (p['표준담보ID'] ? stdN(p['표준담보ID']) : (subLabel(p['세부'], p['세부이름']) || catLabel(p['분류'])));
  const titleLong = p => (p['표준담보ID']
    ? stdN(p['표준담보ID'])
    : `${subLabel(p['세부'], p['세부이름']) || catLabel(p['분류'])}, ${txt.peerNamesEtc((p['비교종형ID'] || []).map(fullN), 3)}`);

  // ---------- 자료 ----------
  function pts(c) {
    const raw = (c.base['포인트'] || []).map(id => S['포인트'][id]).filter(Boolean);
    if (c.peerScope === 'all') return raw;
    const pSet = new Set(c.activePeerOrgs || []);
    return raw.filter(p => (p['관련기관코드'] || []).some(o => pSet.has(o)));
  }
  function catCounts(c) {
    if (c.peerScope === 'all') return c.base['분류집계'] || {};
    const out = {};
    pts(c).forEach(p => { out[p['분류']] = (out[p['분류']] || 0) + 1; });
    return out;
  }
  function pickSet(c) {
    if (!picks[c.baseId]) picks[c.baseId] = new Set((c.base['먼저'] && c.base['먼저']['카드']) || []);
    return picks[c.baseId];
  }
  function pickedCount(c) {
    const sel = pickSet(c);
    return pts(c).filter(p => sel.has(p['포인트ID'])).length;
  }
  const inPurpose = p => !purpose || !p['표준담보ID'] || (p['목적'] || []).includes(purpose);

  // ---------- 본문: 분류별 목록 ----------
  function itemHTML(p, sel, groupHead, c) {
    const h = head(p);
    const cau = cautionOf(c, p);
    const flag = p['원문대조'] ? ui.flag(p['원문대조글'] || ui.FLAG_TEXT) : '';
    const scBadge = c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : '';
    const pSet = new Set(c.activePeerOrgs || []);
    const peerVids = c.peerScope === 'all' ? (p['비교종형ID'] || []) : (p['비교종형ID'] || []).filter(v => pSet.has(orgOf(v)));
    const peerNames = txt.peerNamesEtc((peerVids.length ? peerVids : (p['비교종형ID'] || [])).map(fullN), 3);
    const cLab = catLabel(p['분류']);
    return `<li class="lrow ins-it" data-pick="p:${esc(p['포인트ID'])}" data-aim="rect">
      <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${cLab}, ${titleLong(p)}. 근거 보기`)}"></button>${flag}
      <div class="ins-ih selbar">
        <span class="live ins-ckw"><label class="ins-ck"><input type="checkbox" tabindex="-1" data-act="ins-pick" data-id="${esc(p['포인트ID'])}"${sel.has(p['포인트ID']) ? ' checked' : ''} aria-label="${esc(titleLong(p))} 응대 화법에 추가"><span class="box" aria-hidden="true">${ui.IC.check}</span><span class="lb">응대 화법에 추가</span><span class="lb2" aria-hidden="true">추가</span></label></span>
        <span class="ins-t">${esc(titleOf(p))}</span><span class="ins-tgd">${pointChip(p, c)}${p['구조다름'] ? ui.tag('구조 다름', '갱신이나 환급 구조가 다른 타사와 견준 문장') : ''}</span>
      </div>
      <div class="ins-tgm">${pointChip(p, c)}${p['구조다름'] ? ui.tag('구조 다름') : ''}${p['표준담보ID'] ? '' : `<span class="ins-pe">타사 ${esc(peerNames)}${!peerVids.length && c.peerScope !== 'all' ? scBadge : ''}</span>`}</div>
      <p class="ins-s">${esc(p['문장'])}${scBadge}</p>
      ${cau ? `<p class="ins-w ins-cau">${ui.verdict('diff')} ${esc(cautionNote(cau))}</p>` : ''}
      ${p['주의'] ? `<p class="ins-w">주의: ${esc(p['주의'])}${scBadge}</p>` : ''}
      <div class="ins-m">${(p['근거'] || []).map(evChip).join('')}${p['원문대조'] ? ui.flagText(p['원문대조글'] || ui.FLAG_TEXT) : ''}</div>
      ${h && h !== groupHead ? `<p class="ins-hd">${esc(h)}${scBadge}</p>` : ''}
      <span class="lrow-chev" aria-hidden="true">${ui.IC.chevR}</span></li>`;
  }

  function revRowOrgs(d, c) {
    if (!c || c.peerScope === 'all') return d['가진상대'] || [];
    const pSet = new Set(c.activePeerOrgs || []);
    const orgs = [];
    const seen = new Set();
    (d['가진종형ID'] || []).forEach(vid => {
      const o = orgOf(vid);
      if (pSet.has(o) && !seen.has(o)) { seen.add(o); orgs.push(txt.orgShort(o)); }
    });
    return orgs;
  }

  function revInScope(d, c, allowedIds) {
    const p = S['포인트'][d['포인트ID']];
    if (c.peerScope !== 'all') {
      if (Array.isArray(d['가진종형ID']) && d['가진종형ID'].length) {
        if (!revRowOrgs(d, c).length) return false;
      } else if (p && !allowedIds.has(d['포인트ID'])) {
        return false;
      }
    }
    return !p || inPurpose(p);
  }

  function revHTML(c, sel) {
    const allowedIds = new Set(pts(c).map(p => p['포인트ID']));
    const groups = (c.base['개정검토'] || []).map((g, gi) => ({
      g, gi,
      ds: g['담보'].filter(d => revInScope(d, c, allowedIds)),
    })).filter(x => x.ds.length);
    if (!groups.length) return '<p class="ins-empty">조건과 비교 범위에 드는 미보유 담보가 없습니다.</p>';
    return `<ul class="lrows ins-rev" id="ins-rev">${groups.map(({ g, gi, ds }) => `<li class="lrow ins-rg" data-pick="r:${gi}" data-aim="rect">
        <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${g['중분류']}, 미보유 담보 ${ds.length}건. 근거 보기`)}"></button>
        <div class="ins-ih selbar"><span class="ins-t">${esc(g['중분류'])}</span><span class="sub">${esc(g['대분류'])}</span>${ui.tag(`담보 ${ds.length}`)}${g['좁은담보만수'] ? ui.tag(`좁은 담보만 ${g['좁은담보만수']}`) : ''}${c.peerScope !== 'all' ? ui.fullScopeTag() : ''}</div>
        <ul class="ins-rl">${ds.map(d => {
          const p = S['포인트'][d['포인트ID']];
          const scOrgs = revRowOrgs(d, c);
          const holderTxt = c.peerScope === 'all'
            ? `보유 타사 <b class="num">${d['가진상대수']}</b>곳(${esc(txt.peerNamesEtc(d['가진상대'], 3))})`
            : `선택 범위 <b class="num">${scOrgs.length}</b>곳(${esc(txt.peerNamesEtc(scOrgs, 3))}), 전체 <b class="num">${d['가진상대수']}</b>곳 ${ui.fullScopeTag()}`;
          return `<li><span class="live ins-ckw"><label class="ins-ck sm"><input type="checkbox" tabindex="-1" data-act="ins-pick" data-id="${esc(d['포인트ID'])}"${sel.has(d['포인트ID']) ? ' checked' : ''} aria-label="${esc(d['담보'])} 응대 화법에 추가"><span class="box" aria-hidden="true">${ui.IC.check}</span></label></span>
            <span class="rn">${esc(d['담보'])}</span><span class="rt">${esc(d['급부유형'])}</span>
            <span class="rh">${holderTxt}</span>
            <span class="ro">우체국 ${esc(d['우리상태'])}</span>
            <span class="rg">${p ? (p['근거'] || []).map(evChip).join('') : ''}</span></li>`;
        }).join('')}</ul>
        <span class="lrow-chev" aria-hidden="true">${ui.IC.chevR}</span></li>`).join('')}</ul>`;
  }

  function omitHTML(c, cat) {
    const pSet = new Set(c.activePeerOrgs || []);
    const list = (c.base['뺀포인트'] || []).filter(o => o['분류'] === cat && (c.peerScope === 'all' || (o['비교종형ID'] || []).some(v => pSet.has(orgOf(v)))));
    if (!list.length) return '';
    const open = openOmit.has(cat);
    const scBadge = c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : '';
    return `<details class="ins-omit"${open ? ' open' : ''} data-cat="${esc(cat)}"><summary><span>뺀 포인트 ${list.length}건</span><span class="note">검수 대기이거나 조건이 다른 줄이 있어 세지 않은 것</span>${ui.IC.chevD}</summary>
      <ul>${list.map(o => {
        const sl = subLabel(o['세부']);
        return `<li><b>${esc(stdN(o['표준담보ID']))}</b>${sl ? ` <span class="tag">${esc(sl)}</span>` : ''}${scBadge}<br><span class="note">타사 ${esc(txt.peerNamesEtc((o['비교종형ID'] || []).map(fullN), 3))}. ${esc(reasonText(o['사유']))}</span></li>`;
      }).join('')}</ul></details>`;
  }

  function catHTML(c, cat, i, sel) {
    const all = pts(c).filter(p => p['분류'] === cat);
    const shown = all.filter(inPurpose);
    const subNames = (SUB[cat] || []).map(k => subLabel(k)).filter(Boolean).join(', ');
    const heads = [...new Set(shown.map(head))];
    const groupHead = heads.length === 1 ? heads[0] : '';
    const cLab = catLabel(cat);
    let list;
    if (cat === '개정 검토 후보') list = revHTML(c, sel);
    else if (!all.length) list = `<p class="ins-empty">${esc(emptyWhy(c, cat))}</p>`;
    else if (!shown.length) list = '<p class="ins-empty">이 목적에 드는 항목이 없습니다.</p>';
    else list = `<ul class="lrows">${shown.map(p => itemHTML(p, sel, groupHead, c)).join('')}</ul>`;
    const revActs = cat === '개정 검토 후보'
      ? `<div class="r"><span class="live">${ui.btn('미보유 담보 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="ins-copy-rev"' })}${ui.btn('인쇄', { sm: true, ghost: true, icon: 'print', attrs: `data-print="ins-cat-${i}" data-title="미보유 담보 목록"` })}</span></div>`
      : '';
    const purpNote = (purpose && cat !== '개정 검토 후보') ? ` <span class="note">(목적: ${esc(purpose)})</span>` : '';
    return `<section class="panel ins-cat" id="ins-cat-${i}" style="--cd:${i * 55}ms" aria-labelledby="ins-cat-${i}-h">
      <div class="panel-h"><div><span class="k">${ui.scope('base')}${subNames ? ' ' + esc(subNames) : ''}${cat === '개정 검토 후보' && c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : ''}</span>
        <h2 id="ins-cat-${i}-h"><span class="ins-no num">0${i + 1}</span><span>${esc(cLab)}</span>${purpNote}</h2></div>${revActs}</div>
      ${groupHead ? `<p class="ins-gh">${esc(groupHead)}${c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : ''}</p>` : ''}
      ${list}
      ${omitHTML(c, cat)}
    </section>`;
  }

  function emptyWhy(c, cat) {
    const bi = c.baseInfo || {};
    if (cat === '관문 차이' && bi['심사'] === '일반심사') return '일반심사 종형이라 간편 고지 질문을 견주지 않아 인수기준 차이가 없습니다.';
    if (cat === '조건 열위 방어') return '맞붙는 타사보다 조건이 열위인 담보가 없습니다(검수 대기와 조건이 다른 줄이 있는 것은 뺀 포인트에 있습니다).';
    if (cat === '앞세울 강점') return '견준 타사에 없는 담보나 조건 우위 담보가 나오지 않았습니다.';
    return '이 분류에 든 항목이 없습니다.';
  }

  // ---------- 응대 화법 미리 보기(#z-right 기본 내용) ----------
  function gateLine(c) {
    const g = c.seg;
    const who = App.condSegOnly();
    if (!g.cell) return `${who}: ${g.reason}${g.sexNote ? ` ${g.sexNote}` : ''}`;
    const cell = g.cell;
    const shownOrgs = (c.activeOrgs || txt.ORG_ORDER).filter(o => o in cell['회사']);
    let st;
    if (shownOrgs.length <= 4) {
      st = shownOrgs.map(o => `${txt.orgShort(o)} ${stateLabel(cell['회사'][o])}`).join(', ');
    } else {
      const openP = c.inScope(cell['열린상대코드']);
      const closedP = c.inScope(cell['닫힌상대코드']);
      const unkP = c.inScope(cell['모르는상대코드']);
      st = `${txt.orgShort('EPOST')} ${stateLabel(cell['회사'].EPOST || '')}, 타사 가입 가능 ${openP}곳, 가입 제한 ${closedP}곳${unkP ? `, 자료 없음 ${unkP}곳` : ''}`;
    }
    const why = shownOrgs.slice(0, 4).map(o => txt.stateWhy(o, cell['회사'][o])).filter(Boolean);
    const rep = cell['대표'] && cell['대표'] !== c.baseId ? ` 이 고객군의 우체국 대표 종형은 ${kindN(cell['대표'])}입니다.` : '';
    return `${who}: ${dispMap[cell['라벨']] || cell['라벨']}${cell['보조'] ? `(${cell['보조']})` : ''}. ${st}.${rep}${why.length ? ` ${why.join(' ')}.` : ''}${g.sexNote ? ` ${g.sexNote}.` : ''}`;
  }

  function composeLine(c) {
    try {
      if (App.card && typeof App.card.comboLine === 'function') {
        const t = App.card.comboLine(purpose || null);
        if (t) return { t: String(t), from: 'gate' };
      }
    } catch (e) { console.error(e); }
    const L = c.limit;
    const who = `${c.st.age}세 ${txt.sexText(c.st.sex)}`;
    if (!L) return { t: `한도 자료 없음: ${kindN(c.baseId)}의 나이 구간별 한도 표가 없습니다.`, from: 'limit' };
    if (!L.hit) return { t: `${txt.josa(who, '는')} ${kindN(c.baseId)}의 가입나이(${L.lo}~${L.hi}세) 밖입니다.`, from: 'limit' };
    return { t: `${kindN(c.baseId)} 주계약 최대 가입금액 ${fmt(L.hit.max)}만원(${who}, 나이 구간별 한도 표의 ${L.hit.lo}~${L.hit.hi}세 구간${L.hit.pend ? ', 검수 대기' : ''}). 특약 구성 예시는 인수기준 비교 탭에서 봅니다.`, from: 'limit' };
  }

  function cardItems(c) {
    const sel = pickSet(c);
    const list = pts(c).filter(p => sel.has(p['포인트ID']));
    return CARD_ORDER.map(cat => ({ cat, xs: list.filter(p => p['분류'] === cat) })).filter(g => g.xs.length);
  }

  function cardHTML(c) {
    const groups = cardItems(c);
    const n = groups.reduce((a, g) => a + g.xs.length, 0);
    const flagN = groups.reduce((a, g) => a + g.xs.filter(p => p['원문대조']).length, 0);
    const peerList = c.peerIds.map(v => `${fullN(v)}(${vinfo(v)['적용시작일'] || '기준일 자료 없음'})`);
    const peers = peerList.length ? txt.peerNamesEtc(peerList, 3) : App.t('condPeerNone');
    const comp = composeLine(c);
    const scBadge = c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : '';
    const body = groups.map(g => {
      const heads = [...new Set(g.xs.map(head))];
      return `<div class="sec" data-cat="${esc(g.cat)}">${esc(catLabel(g.cat))}</div>
        ${heads.length === 1 && heads[0] ? `<p class="icd-hd">${esc(heads[0])}${scBadge}</p>` : ''}
        ${g.xs.map(p => `<div class="icd-qa" data-pid="${esc(p['포인트ID'])}">
          ${heads.length > 1 && head(p) ? `<p class="icd-hd">${esc(head(p))}${scBadge}</p>` : ''}
          ${p['카드질문'] ? `<p class="icd-q"><span class="icd-l">예상 질문</span>${esc(p['카드질문'])}${scBadge}</p>` : ''}
          <p class="icd-a"><span class="icd-l">${p['카드질문'] ? '답' : '설명'}</span>${esc(p['카드답'] || p['문장'])}${scBadge}</p>
          ${cautionOf(c, p) ? `<p class="icd-w">주의: ${esc(cautionNote(cautionOf(c, p)))}${scBadge}</p>` : ''}
          ${p['주의'] ? `<p class="icd-w">주의: ${esc(p['주의'])}${scBadge}</p>` : ''}
          ${p['원문대조'] ? `<p class="icd-f">${ui.flagText(p['원문대조글'] || ui.FLAG_TEXT)}</p>` : ''}</div>`).join('')}`;
    }).join('');
    return `<div class="rcard ins-card" id="insight-card" aria-label="응대 화법 미리 보기">
      <div class="icd-nt no-print"><span>${esc(S['고지'])}</span><span class="icd-mk">${esc(MARK)}</span></div>
      <span class="k">응대 화법, 지금 조건과 기준 상품</span>
      <h3>우체국 ${esc(kindN(c.baseId))}<br><span class="gold-t">${esc(App.condSegOnly())}</span></h3>
      <div class="sec">조건과 비교 상품</div>
      <p class="icd-sm">기준 ${esc(txt.josa(`${fullN(c.baseId)}(${vinfo(c.baseId)['적용시작일'] || '기준일 자료 없음'})`, '와'))} ${esc(txt.josa(peers, '를'))} 견줬습니다. 자료 기준 ${esc(App.asofText())}.</p>
      <div class="sec">인수기준</div>
      <p class="icd-sm">${esc(gateLine(c))}</p>
      ${n ? body : '<div class="sec">추가한 항목</div><p class="icd-sm">추가한 항목이 없습니다. 가운데 목록에서 "응대 화법에 추가"를 체크합니다.</p>'}
      <div class="sec" data-sec="compose">구성 요약</div>
      <p class="icd-sm">${esc(comp.t)}</p>
      <div class="sec">유의사항</div>
      <ul class="icd-nb">
        <li>가입 여부는 청약 뒤 인수 심사로 정해집니다. 이 화법 자료는 심사를 대신하지 않습니다.</li>
        <li>보험료와 질병코드는 반영하지 않았습니다.</li>
        <li>유지 중인 다른 회사 계약의 해지를 권하지 않습니다.</li>
        <li>${flagN ? `원문 확인이 필요한 항목 ${flagN}건은 사업방법서 원문과 대조한 뒤 씁니다.` : '이 화법에는 원문 확인이 필요한 항목이 없습니다.'}</li>
        <li>문장은 대표 조건(${esc(`${c.ref['나이']}세 ${txt.sexText(c.ref['성별'])}, ${txt.sinceText(c.ref['이력'])}`)})과 수집한 공시 문서로 계산했습니다.</li>
      </ul>
    </div>`;
  }

  function cardPanel(c) {
    const groups = cardItems(c);
    const n = groups.reduce((a, g) => a + g.xs.length, 0);
    return `<div class="ins-cw">
      <div class="ins-ct"><div><span class="k">${ui.scope('base')} 산출물</span><h2>응대 화법</h2></div>
        <div class="ins-cb">${ui.btn('인쇄', { main: true, sm: true, icon: 'print', attrs: 'data-print="insight-card" data-card="1" data-title="응대 화법"' })}${ui.btn('화법 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="ins-copy-card"' })}<button type="button" class="btn sm ghost ins-mob-top-btn" data-act="ins-go-top">목록 위로</button></div></div>
      <p class="ins-cn"><span>응대 화법에 추가 <b class="num" id="ins-card-picked-n">${fmt(n)}</b>건</span>${ui.btn('기본 선택으로', { sm: true, ghost: true, attrs: 'data-act="ins-reset"' })}<span class="ins-over" id="ins-over" role="status"></span></p>
      ${cardHTML(c)}
    </div>`;
  }

  /** A4 한 장(인쇄 영역 182x269mm)에 드는지 잰다 */
  function checkPages(root) {
    const scope = root || document;
    const card = scope.querySelector('#insight-card');
    const out = scope.querySelector('#ins-over');
    if (!card || !out) return;
    const box = document.createElement('div');
    box.className = 'icd-measure';
    box.innerHTML = `<div class="ph">${esc(S['고지'])}<span class="mk">${esc(MARK)}</span><span class="sc">응대 화법 / ${esc(App.scopeLine())}</span></div>`;
    box.appendChild(card.cloneNode(true));
    document.body.appendChild(box);
    const h = box.scrollHeight;
    box.remove();
    const page = 269 / 25.4 * 96;
    const over = h > page;
    out.textContent = over ? `A4 한 장 초과(약 ${(h / page).toFixed(1)}장)` : `A4 한 장 안(약 ${Math.round(h / page * 100)}%)`;
    out.classList.toggle('over', over);
  }

  function renderDefaultRight(unselEl, c) {
    if (!unselEl) return;
    const curC = c || App.ctx();
    if (!curC.base) {
      unselEl.innerHTML = '<p class="read-concl">이 기준 상품의 영업 인사이트 자료가 없습니다.</p>';
      return;
    }
    unselEl.innerHTML = cardPanel(curC);
    checkPages(unselEl);
  }

  let previewScrollToken = 0;
  function scrollPreviewTo(unselEl, targetEl) {
    if (!unselEl || !targetEl) return;
    const token = ++previewScrollToken;
    const uRect = unselEl.getBoundingClientRect();
    const tRect = targetEl.getBoundingClientRect();
    const curTop = unselEl.scrollTop;
    const relTop = curTop + (tRect.top - uRect.top);
    const maxTop = Math.max(0, unselEl.scrollHeight - unselEl.clientHeight);
    let nextTop = curTop;
    const pad = 18;
    if (tRect.top < uRect.top + pad || tRect.bottom > uRect.bottom - pad) {
      const centered = relTop - Math.max(pad, Math.round((unselEl.clientHeight - tRect.height) * 0.35));
      nextTop = Math.max(0, Math.min(maxTop, centered));
    }
    if (Math.abs(nextTop - curTop) < 1) return;
    if (!App.motionOn()) {
      unselEl.scrollTop = nextTop;
      return;
    }
    const dur = 240;
    const t0 = performance.now();
    function step(now) {
      if (token !== previewScrollToken) return;
      const p = Math.min(1, (now - t0) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      unselEl.scrollTop = curTop + (nextTop - curTop) * eased;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function syncTopCounts(c) {
    const curC = c || App.ctx();
    const cnt = catCounts(curC);
    const total = Object.values(cnt).reduce((a, n) => a + n, 0);
    const pn = pickedCount(curC);
    const totEl = document.getElementById('ins-total-n');
    const pkEl = document.getElementById('ins-picked-n');
    if (totEl) totEl.textContent = fmt(total);
    if (pkEl) pkEl.textContent = fmt(pn);
  }

  function updateRightPreviewWithToggle(id, added) {
    const curC = App.ctx();
    syncTopCounts(curC);
    if (App.state.sel.insight != null) {
      if (added) App.unselect({ restoreFocus: false, animate: false });
      else return;
    }
    const unsel = document.getElementById('ev-unselected');
    if (!unsel || unsel.hidden) return;
    unsel.querySelectorAll('.icd-qa-exit').forEach(el => el.remove());

    let exitInfo = null;
    if (!added && App.motionOn()) {
      const oldQa = unsel.querySelector(`.icd-qa[data-pid="${CSS.escape(id)}"]`);
      if (oldQa) {
        let nextPid = null, prevPid = null;
        let sib = oldQa.nextElementSibling;
        while (sib) {
          if (sib.classList.contains('icd-qa') && sib.dataset.pid) { nextPid = sib.dataset.pid; break; }
          sib = sib.nextElementSibling;
        }
        sib = oldQa.previousElementSibling;
        while (sib) {
          if (sib.classList.contains('icd-qa') && sib.dataset.pid) { prevPid = sib.dataset.pid; break; }
          sib = sib.previousElementSibling;
        }
        exitInfo = { html: oldQa.innerHTML, nextPid, prevPid };
      }
    }

    const prevScroll = unsel.scrollTop;
    renderDefaultRight(unsel, curC);
    unsel.scrollTop = prevScroll;

    if (added) {
      const qa = unsel.querySelector(`.icd-qa[data-pid="${CSS.escape(id)}"]`);
      if (qa) {
        scrollPreviewTo(unsel, qa);
        if (App.motionOn() && typeof qa.animate === 'function') {
          const { dur, easing } = App.panelTiming(true);
          qa.animate([
            { opacity: 0, transform: 'scaleY(0.28)', backgroundColor: 'rgba(205, 192, 129, 0.34)' },
            { opacity: 1, transform: 'scaleY(1)', backgroundColor: 'rgba(205, 192, 129, 0.22)', offset: 0.55 },
            { opacity: 1, transform: 'scaleY(1)', backgroundColor: 'rgba(205, 192, 129, 0)' },
          ], { duration: Math.min(360, dur || 320), easing });
        }
      }
    } else if (exitInfo) {
      const card = unsel.querySelector('#insight-card');
      if (card) {
        const ghost = document.createElement('div');
        ghost.className = 'icd-qa-exit';
        ghost.setAttribute('aria-hidden', 'true');
        ghost.innerHTML = exitInfo.html;
        const beforeEl = (exitInfo.nextPid && card.querySelector(`.icd-qa[data-pid="${CSS.escape(exitInfo.nextPid)}"]`)) || null;
        const afterEl = (!beforeEl && exitInfo.prevPid && card.querySelector(`.icd-qa[data-pid="${CSS.escape(exitInfo.prevPid)}"]`)) || null;
        const composeSec = card.querySelector('.sec[data-sec="compose"]');
        if (beforeEl && beforeEl.parentNode) beforeEl.parentNode.insertBefore(ghost, beforeEl);
        else if (afterEl && afterEl.parentNode) afterEl.insertAdjacentElement('afterend', ghost);
        else if (composeSec && composeSec.parentNode) composeSec.parentNode.insertBefore(ghost, composeSec);
        if (ghost.isConnected && typeof ghost.animate === 'function') {
          const { dur, easing } = App.panelTiming(false);
          const anim = ghost.animate([
            { opacity: 0.88, transform: 'scaleY(1)' },
            { opacity: 0, transform: 'scaleY(0)' },
          ], { duration: Math.min(240, dur || 220), easing });
          anim.onfinish = () => ghost.remove();
        } else {
          ghost.remove();
        }
      }
    }
  }

  // ---------- 왼쪽 목차(#z-left)와 가운데 본문(#z-center) ----------
  function renderLeftTOC(leftEl, c) {
    if (!leftEl) return;
    if (!c.base) {
      leftEl.innerHTML = `<div class="zl-head"><span class="zl-k">${esc(App.TAB_NAME.insight)}</span></div>`;
      return;
    }
    const cnt = catCounts(c);
    const total = Math.max(1, Object.values(cnt).reduce((a, n) => a + n, 0));
    leftEl.innerHTML = `<div class="zl-head"><span class="zl-k">분류 목차</span></div>
      <div class="zl-list" role="listbox" aria-label="영업 인사이트 분류 목차">
        ${CATS.map((k, idx) => {
          const n = cnt[k] || 0;
          const cls = k === '앞세울 강점' ? 'gold' : '';
          return `<button type="button" class="zl-item${idx === 0 ? ' is-on' : ''}" role="option" aria-selected="${idx === 0}" data-jump-sec="ins-cat-${idx}">
            <span class="zl-ring">${ui.miniRingSVG(n, total, cls)}<span class="zl-n num">0${idx + 1}</span></span>
            <span class="zl-t">${esc(catLabel(k))}</span>
            <b class="ins-zl-cnt num">${fmt(n)}</b>
          </button>`;
        }).join('')}
      </div>`;
  }

  function refNote(c) {
    const parts = [];
    if (!c.isRef) parts.push(`지금 조건(${App.condSegOnly()})을 바꿔도 분류별 문장은 대표 조건(${c.ref['나이']}세 ${txt.sexText(c.ref['성별'])}, ${txt.sinceText(c.ref['이력'])}) 기준이라 그대로입니다. 오른쪽 응대 화법의 인수기준과 구성 요약은 지금 조건으로 바뀝니다.`);
    if (c.st.renewal) parts.push('갱신 유형 거르개는 고객군과 시장에만 씁니다.');
    return parts.length ? `<p class="ins-ref">${esc(parts.join(' '))}</p>` : '';
  }

  function topBarHTML(c) {
    const cnt = catCounts(c);
    const total = Object.values(cnt).reduce((a, n) => a + n, 0);
    const pn = pickedCount(c);
    return `<div class="ins-top-bar" data-main-axis="1">
      <span class="ins-sum">전체 <b class="num" id="ins-total-n">${fmt(total)}</b>건, 응대 화법에 추가 <b class="num" id="ins-picked-n">${fmt(pn)}</b>건</span>
      <div class="ins-top-acts">
        <span class="ins-pf"><span class="lb">목적</span><span data-slot="purpose"></span></span>
        <span class="live">${ui.btn('목록 복사', { sm: true, ghost: true, icon: 'copy', cls: 'ins-top-btn', attrs: 'data-act="ins-copy-list"' })}</span>
        <button type="button" class="btn sm ins-mob-card-btn" data-act="ins-go-card">응대 화법 보기</button>
      </div>
    </div>`;
  }

  function renderZones({ left, center, ctx: c }) {
    if (!c.base) {
      renderLeftTOC(left, c);
      center.innerHTML = '<div class="panel placeholder">자료 없음: 이 기준 상품의 영업 인사이트 자료가 없습니다.</div>';
      return;
    }
    if (c.why === 'change' && c.changed && !c.changed.has('base') && !c.changed.has('peerScope') && !c.changed.has('peerPick') && center.querySelector('.ins-top-bar')) {
      const old = center.querySelector('.ins-ref');
      const html = refNote(c);
      if (old) { if (html) old.outerHTML = html; else old.remove(); }
      else if (html) center.querySelector('.ins-top-bar').insertAdjacentHTML('afterend', html);
      syncTopCounts(c);
      return;
    }
    renderLeftTOC(left, c);
    const sel = pickSet(c);
    center.innerHTML = `${topBarHTML(c)}${refNote(c)}<div class="ins-l">${CATS.map((k, i) => catHTML(c, k, i, sel)).join('')}</div>`;
    const slot = center.querySelector('[data-slot="purpose"]');
    if (slot) {
      slot.replaceWith(ui.chevSel({
        label: '목적',
        options: [{ v: null, t: '전체' }].concat(PURPOSES.map(p => ({ v: p['이름'], t: p['이름'], title: `${p['기준']}: ${p['값'].join(', ')}` }))),
        value: purpose,
        w: '92px',
        onChange: v => {
          purpose = v;
          refreshList(center);
          refreshRightSimple();
        },
      }));
    }
    bindCenter(center);
  }

  function refreshList(body) {
    if (!body) return;
    const c = App.ctx();
    const sel = pickSet(c);
    CATS.forEach((k, i) => {
      const el = body.querySelector('#ins-cat-' + i);
      if (el) el.outerHTML = catHTML(c, k, i, sel);
    });
    syncTopCounts(c);
    remarkSel(body);
  }

  function refreshRightSimple() {
    const c = App.ctx();
    syncTopCounts(c);
    if (App.state.sel.insight != null) return;
    const unsel = document.getElementById('ev-unselected');
    if (unsel && !unsel.hidden) renderDefaultRight(unsel, c);
  }

  function remarkSel(body) {
    if (!body) return;
    const key = App.state.sel.insight;
    const rows = Array.from(body.querySelectorAll('.lrow[data-pick]'));
    let selIdx = rows.findIndex(el => el.dataset.pick === key);
    if (selIdx < 0) selIdx = 0;
    rows.forEach((el, idx) => {
      const on = el.dataset.pick === key;
      el.classList.toggle('is-sel', on);
      const hit = el.querySelector('.lrow-hit');
      if (hit) {
        hit.setAttribute('aria-pressed', String(on));
        hit.tabIndex = idx === selIdx ? 0 : -1;
      }
      el.querySelectorAll('input[data-act="ins-pick"]').forEach(ck => { ck.tabIndex = -1; });
    });
  }

  function bindCenter(body) {
    remarkSel(body);
    if (body._b) return;
    body._b = true;
    body.addEventListener('keydown', e => {
      const inHit = e.target.closest && e.target.closest('.lrow-hit');
      if (inHit) {
        const rowEl = inHit.closest('.lrow[data-pick]');
        if (rowEl && ['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) {
          const rows = Array.from(body.querySelectorAll('.lrow[data-pick]'));
          const i = rows.indexOf(rowEl);
          if (i < 0) return;
          let j = i;
          if (e.key === 'ArrowDown') j = Math.min(rows.length - 1, i + 1);
          if (e.key === 'ArrowUp') j = Math.max(0, i - 1);
          if (e.key === 'Home') j = 0;
          if (e.key === 'End') j = rows.length - 1;
          e.preventDefault();
          rows.forEach((r, k) => {
            const h = r.querySelector('.lrow-hit');
            if (h) h.tabIndex = k === j ? 0 : -1;
          });
          const nextHit = rows[j].querySelector('.lrow-hit');
          if (nextHit) {
            nextHit.focus({ preventScroll: true });
            App.reveal(rows[j]);
          }
          return;
        }
        if (rowEl && e.key === 'ArrowRight') {
          const ck = rowEl.querySelector('input[data-act="ins-pick"]');
          if (ck) { e.preventDefault(); ck.focus({ preventScroll: true }); }
          return;
        }
      }
      const inCk = e.target.closest && e.target.closest('input[data-act="ins-pick"]');
      if (inCk && ['ArrowLeft', 'ArrowDown', 'ArrowUp'].includes(e.key)) {
        const rowEl = inCk.closest('.lrow[data-pick]');
        if (!rowEl) return;
        const cks = Array.from(rowEl.querySelectorAll('input[data-act="ins-pick"]'));
        const ci = cks.indexOf(inCk);
        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          if (ci > 0) cks[ci - 1].focus({ preventScroll: true });
          else { const h = rowEl.querySelector('.lrow-hit'); if (h) h.focus({ preventScroll: true }); }
          return;
        }
        const nextCi = e.key === 'ArrowDown' ? ci + 1 : ci - 1;
        if (nextCi >= 0 && nextCi < cks.length) {
          e.preventDefault();
          cks[nextCi].focus({ preventScroll: true });
        } else {
          const rows = Array.from(body.querySelectorAll('.lrow[data-pick]'));
          const ri = rows.indexOf(rowEl);
          const nextRi = e.key === 'ArrowDown' ? Math.min(rows.length - 1, ri + 1) : Math.max(0, ri - 1);
          if (nextRi !== ri) {
            e.preventDefault();
            rows.forEach((r, k) => { const h = r.querySelector('.lrow-hit'); if (h) h.tabIndex = k === nextRi ? 0 : -1; });
            const nh = rows[nextRi].querySelector('.lrow-hit');
            if (nh) { nh.focus({ preventScroll: true }); App.reveal(rows[nextRi]); }
          }
        }
      }
    });

    body.addEventListener('change', e => {
      const ck = e.target.closest('input[data-act="ins-pick"]');
      if (!ck) return;
      const c = App.ctx();
      const sel = pickSet(c);
      const id = ck.dataset.id;
      if (ck.checked) sel.add(id); else sel.delete(id);
      body.querySelectorAll(`input[data-act="ins-pick"][data-id="${CSS.escape(id)}"]`).forEach(x => { x.checked = ck.checked; });
      updateRightPreviewWithToggle(id, ck.checked);
      if (innerWidth < 1000) {
        App.toast(ck.checked ? `응대 화법에 추가했습니다(${fmt(sel.size)}건)` : `응대 화법에서 제외했습니다(${fmt(sel.size)}건)`, {
          actLabel: '보기',
          onAct: () => {
            if (App.state.sel.insight != null) App.unselect({ restoreFocus: false, animate: false });
            const zr = document.getElementById('z-right');
            if (zr) {
              const top = Math.max(0, Math.round(window.scrollY + zr.getBoundingClientRect().top - 36));
              const beh = (App.motionOn() && Math.abs(top - window.scrollY) <= 1400) ? 'smooth' : 'auto';
              window.scrollTo({ top, behavior: beh });
            }
          },
        });
      } else {
        App.toast(ck.checked ? '응대 화법에 추가했습니다' : '응대 화법에서 제외했습니다');
      }
    });

    body.addEventListener('toggle', e => {
      const d = e.target.closest && e.target.closest('details.ins-omit');
      if (!d) return;
      if (d.open) openOmit.add(d.dataset.cat); else openOmit.delete(d.dataset.cat);
    }, true);
  }

  // 오른쪽 열(#ev-unselected)과 가운데 열의 공통 단추 위임
  document.addEventListener('click', e => {
    if (App.state.tab !== 'insight') return;
    const a = e.target.closest && e.target.closest('[data-act]');
    if (!a) return;
    const act = a.dataset.act;
    const body = document.querySelector('#view-insight .vbody');
    if (act === 'ins-reset') {
      delete picks[App.state.base];
      refreshList(body);
      refreshRightSimple();
      App.toast('기본 선택으로 되돌렸습니다');
    } else if (act === 'ins-copy-list') {
      copyList();
    } else if (act === 'ins-copy-rev') {
      copyRev();
    } else if (act === 'ins-copy-card') {
      copyCard();
    } else if (act === 'ins-go-card') {
      e.stopPropagation();
      if (App.state.sel.insight != null) App.unselect({ restoreFocus: false, animate: false });
      const zr = document.getElementById('z-right');
      if (zr) {
        const top = Math.max(0, Math.round(window.scrollY + zr.getBoundingClientRect().top - 36));
        const beh = (App.motionOn() && Math.abs(top - window.scrollY) <= 1400) ? 'smooth' : 'auto';
        window.scrollTo({ top, behavior: beh });
      }
    } else if (act === 'ins-go-top') {
      e.stopPropagation();
      const vwEl = document.getElementById('view-insight');
      if (vwEl) {
        const top = Math.max(0, Math.round(window.scrollY + vwEl.getBoundingClientRect().top - 36));
        const beh = (App.motionOn() && Math.abs(top - window.scrollY) <= 1400) ? 'smooth' : 'auto';
        window.scrollTo({ top, behavior: beh });
      }
    }
  });

  // ---------- 복사 ----------
  const evText = p => (p['근거'] || []).map(g => `${orgN(g['종형ID'])} ${txt.pageText(g['문서'], g['쪽'])}`).join('; ');

  function copySummary(c) {
    const curC = c || App.ctx();
    if (!curC.base) return;
    const cnt = catCounts(curC);
    const total = Object.values(cnt).reduce((a, n) => a + n, 0);
    const pn = pickedCount(curC);
    const summaryLine = `우체국 ${kindN(curC.baseId)} 기준 영업 인사이트 전체 ${total}건(${CATS.map(k => `${catLabel(k)} ${cnt[k] || 0}건`).join(', ')}). 응대 화법에 추가 ${pn}건.`;
    App.copyText(`${summaryLine}\r\n${App.scopeLine()}`, '요약 문장을 복사했습니다');
  }

  function copyList() {
    const c = App.ctx();
    const sel = pickSet(c);
    const rows = CATS.flatMap(cat => pts(c).filter(p => p['분류'] === cat && inPurpose(p)).map(p => {
      const cau = cautionOf(c, p);
      return [catLabel(p['분류']), subLabel(p['세부'], p['세부이름']), titleLong(p), p['문장'], cau ? `조건 상이(단정 주의: ${cau['종류']})` : '', head(p), evText(p), p['원문대조'] ? (p['원문대조글'] || ui.FLAG_TEXT) : '', p['구조다름'] ? '구조 다름' : '', sel.has(p['포인트ID']) ? '추가' : ''];
    }));
    App.copyRows(['분류', '세부', '담보나 항목', '분석 문장', '단정 주의', '범위 머리말', '근거', '원문 확인', '구조', '응대 화법'], rows, { title: `영업 인사이트 분류별 목록${purpose ? ` (목적 ${purpose})` : ''}` });
  }

  function copyRev() {
    const c = App.ctx();
    const allowedIds = new Set(pts(c).map(p => p['포인트ID']));
    const rows = [];
    (c.base['개정검토'] || []).forEach(g => g['담보'].filter(d => revInScope(d, c, allowedIds)).forEach(d => {
      const p = S['포인트'][d['포인트ID']];
      const scOrgs = revRowOrgs(d, c);
      rows.push([g['대분류'], g['중분류'], d['담보'], d['급부유형'], scOrgs.length, scOrgs.join(', '), d['우리상태'], p ? evText(p) : '']);
    }));
    App.copyRows(['보장 대분류', '보장 중분류', '담보', '급부유형', '보유 타사 수', '보유 타사', '우체국 상태', '근거 쪽'], rows, { title: `미보유 담보 목록${purpose ? ` (목적 ${purpose})` : ''}` });
  }

  function copyCard() {
    const card = document.getElementById('insight-card');
    if (!card) return;
    const lines = [S['고지'], MARK];
    card.querySelectorAll(':scope > .k, :scope > h3, :scope > .sec, :scope > p, .icd-qa > p, .icd-nb li').forEach(el => {
      const t = el.innerText.replace(/\s+/g, ' ').trim();
      if (t) lines.push(el.matches('.sec') ? `[${t}]` : el.matches('li') ? `- ${t}` : t);
    });
    App.copyText(lines.join('\r\n'), '응대 화법 글을 복사했습니다');
  }

  // ---------- 상세 패널(#zr-in) ----------
  function sec(title, html, lo) { return `<div class="ev-sec${lo ? ' lo' : ''}">${title ? `<h3>${title}</h3>` : ''}${html}</div>`; }

  function pickPoint(c, id) {
    const p = S['포인트'][id];
    if (!p || !(c.base['포인트'] || []).includes(id)) return null;
    const sid = p['표준담보ID'];
    const relOk = sid && App.cover && App.cover.hasRow(c.baseId, sid);
    const pvList = relOk && App.cover.peerVerdicts ? App.cover.peerVerdicts(c.baseId, sid, c) : null;
    const tvItems = pvList ? pvList.map(({ peer, v }) => (v ? `<span class="cv-bd"><span>${esc(txt.josa(orgN(peer), '과'))}</span>${App.cover.chip(v)}</span>` : '')).filter(Boolean) : [];
    const tableV = tvItems.length <= 4
      ? tvItems.join(' ')
      : `${tvItems.slice(0, 3).join(' ')}<details class="zr-det" style="margin-top:6px"><summary><span>나머지 타사 ${fmt(tvItems.length - 3)}개 종형 판정 보기</span>${ui.IC.chevD}</summary><div class="zr-det-b"><div class="cv-bds">${tvItems.slice(3).join(' ')}</div></div></details>`;
    const omit = sid ? (c.base['뺀포인트'] || []).filter(o => o['표준담보ID'] === sid) : [];
    const cau = cautionOf(c, p);
    const grJump = sid ? `<div style="margin-top:8px">${ui.btn(App.t('mkEvGraphBtn'), { sm: true, ghost: true, chev: true, attrs: `data-go="graph" data-focus="std:${esc(sid)}"` })}</div>` : '';
    const scBadge = c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : '';
    const sLab = subLabel(p['세부'], p['세부이름']);
    let body = sec('', `<p>${esc(p['문장'])}${scBadge}</p>${p['원문대조'] ? `<p>${ui.flagText(p['원문대조글'] || ui.FLAG_TEXT)}</p>` : ''}${cau ? `<p>${ui.verdict('diff')}</p><p class="note">${esc(cautionNote(cau))} ${esc(cau['문장'])}${scBadge}</p>` : ''}${p['주의'] ? `<p class="note">주의: ${esc(p['주의'])}${scBadge}</p>` : ''}
      ${tableV ? `<p class="note" style="margin-top:8px">담보 비교표의 판정: </p><div class="cv-bds">${tableV}</div>` : ''}${grJump}`);
    if (relOk) body += sec('관계도', `<div class="ins-rel"></div>${App.cover.relLegend()}`);
    body += sec('근거 문서와 쪽', `<ul class="cv-evl">${(p['근거'] || []).map(g => `<li><b>${esc(fullN(g['종형ID']))}</b> ${evChip(g)}${g['급부명'] ? `<br><span class="note">${esc(g['급부명'])}</span>` : ''}</li>`).join('')}</ul>${(p['근거'] || []).some(g => g['쪽'] == null) ? `<p class="note">${esc(txt.PAGE_WHY)}.</p>` : ''}`, true);
    body += sec('범위 머리말', `<p class="note">${esc(head(p))}${scBadge}</p><p class="note">견준 ${c.base['범위']['회사수']}개 회사 가운데 ${p['회사수']}곳에 대한 문장입니다.</p>`, true);
    if (omit.length) {
      body += sec('뺀 것', `<ul class="cv-evl">${omit.map(o => {
        const osl = subLabel(o['세부']);
        return `<li>${esc(catLabel(o['분류']))}${osl ? `(${esc(osl)})` : ''}: ${esc(reasonText(o['사유']))}</li>`;
      }).join('')}</ul>`, true);
    }
    return {
      kicker: `${catLabel(p['분류'])}${sLab ? `, ${sLab}` : ''}`,
      title: titleLong(p),
      backLabel: '응대 화법 보기',
      badges: [ui.scope('base'), pointChip(p, c) || ui.tag(catLabel(p['분류'])), p['구조다름'] ? ui.tag('구조 다름') : '', (p['목적'] || []).length ? ui.tag(`목적 ${p['목적'].join(', ')}`) : ''].filter(Boolean),
      body,
      after(el) { if (relOk) App.cover.rel(el.querySelector('.ins-rel'), c.baseId, sid); },
    };
  }

  function pickRev(c, gi) {
    const g = (c.base['개정검토'] || [])[gi];
    if (!g) return null;
    const allowedIds = new Set(pts(c).map(p => p['포인트ID']));
    const ds = g['담보'].filter(d => revInScope(d, c, allowedIds));
    const list = ds.length ? ds : g['담보'];
    const items = list.map(d => {
      const p = S['포인트'][d['포인트ID']];
      const scOrgs = revRowOrgs(d, c);
      const holderNote = c.peerScope === 'all'
        ? `보유 타사 ${d['가진상대수']}곳(${esc(txt.peerNamesEtc(d['가진상대'], 3))})`
        : `선택 범위 ${scOrgs.length}곳(${esc(txt.peerNamesEtc(scOrgs, 3))}), 전체 ${d['가진상대수']}곳`;
      return `<li><b>${esc(d['담보'])}</b> ${ui.verdict('none')}${c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : ''}<br><span class="note">${holderNote}, 우체국 ${esc(d['우리상태'])}</span>${p ? `<p>${esc(p['문장'])}</p><div class="ins-evc">${(p['근거'] || []).map(evChip).join('')}</div>` : ''}</li>`;
    }).join('');
    return {
      kicker: '미보유 담보, 보장 중분류',
      title: g['중분류'],
      backLabel: '응대 화법 보기',
      badges: [ui.scope('base'), ui.tag(g['대분류']), ui.tag(`담보 ${list.length}`), c.peerScope !== 'all' ? ui.fullScopeTag() : ''].filter(Boolean),
      body: sec('', `<p>${esc(txt.josa(g['중분류'], '은'))} 담보 ${list.length}개가 미보유 담보입니다${g['좁은담보만수'] ? `(우체국에 좁은 담보만 있는 것 ${g['좁은담보만수']}개)` : ''}.</p>`)
        + sec('담보', `<ul class="cv-evl">${items}</ul>`)
        + sec('', `<p class="note">빈자리 기준은 맞붙는 타사 두 곳 이상이 가진 담보입니다. 담보 이름을 담보 비교 탭의 비교표에서 찾으면 회사별 조건이 보입니다.</p>${list.map(d => `<button type="button" class="btn sm" data-act="cv-goto" data-sid="${esc(d['표준담보ID'])}">${esc(d['담보'])} 비교표에서 보기${ui.IC.chevR}</button>`).join(' ')}`, true),
    };
  }

  function pick(key, c) {
    if (key.startsWith('p:')) return pickPoint(c, key.slice(2));
    if (key.startsWith('r:')) return pickRev(c, +key.slice(2));
    return null;
  }

  function evidence(c) {
    if (!c.base) return null;
    const cnt = catCounts(c);
    const total = Object.values(cnt).reduce((a, n) => a + n, 0);
    return {
      kicker: '읽는 법', title: '분류별 목록과 응대 화법', badges: [ui.scope('base')],
      body: sec('분류별 집계', ui.eq({ total: { t: '인사이트', n: total }, parts: CATS.map(k => ({ t: catLabel(k), n: cnt[k] || 0 })), tail: '건' })
          + `<p class="note">분류끼리는 서로 겹치지 않습니다. 검수 대기이거나 조건이 다른 줄이 있어 뺀 포인트 ${(c.base['뺀포인트'] || []).length}건은 세지 않고 분류마다 접어 둡니다.</p>`)
        + sec('기본 선택', `<p class="note">응대 화법의 기본 선택은 세부 유형마다 한 건을 먼저 넣고, 화법에서는 열위 담보와 관련 담보를 미보유 담보보다 앞에 둡니다. 체크로 추가하고 빼면 오른쪽 미리 보기가 바로 바뀝니다.</p>`)
        + sec('본문과 화법', `<p class="note">본문은 분석 문장입니다. 창구 말투의 예상 질문과 답은 응대 화법 미리 보기 안에서만 씁니다. 화법을 인쇄하면 흰 바탕 A4 한 장에 고지와 "${esc(MARK)}" 표식이 찍힙니다.</p>`)
        + sec('판정 표지', App.ev.legend(), true),
    };
  }

  ui.registerLegend('insight', 'legendVerdictTitle', c => {
    const spec = evidence(c);
    return spec && spec.body ? spec.body : App.ev.legend();
  });

  function focus(key, body) {
    if (key === 'card') {
      if (App.state.sel.insight != null) App.unselect({ restoreFocus: false, animate: false });
      const card = document.getElementById('insight-card');
      if (card) App.scrollInZone(card);
      return;
    }
    const el = key === 'rev' ? (body && body.querySelector('#ins-rev')) : null;
    if (el) App.scrollInZone(el);
  }

  // 인수기준 비교 탭에서 목적을 바꾸면 응대 화법의 구성 요약을 고친다
  document.addEventListener('c4:card', () => {
    if (App.state.tab !== 'insight') return;
    refreshRightSimple();
  });

  function enter(body) {
    refreshRightSimple();
    if (body && App.motionOn()) {
      body.classList.remove('ins-enter');
      void body.offsetWidth;
      body.classList.add('ins-enter');
      clearTimeout(body._insT);
      body._insT = setTimeout(() => body.classList.remove('ins-enter'), 680);
    }
    const card = document.getElementById('insight-card');
    if (card && App.motionOn()) { card.classList.remove('icd-in'); void card.offsetWidth; card.classList.add('icd-in'); }
  }

  return {
    id: 'insight',
    layout: 'three',
    kicker: '인사이트와 산출물',
    renderZones,
    renderDefaultRight,
    copySummary,
    pick,
    evidence,
    focus,
    enter,
  };
})());
