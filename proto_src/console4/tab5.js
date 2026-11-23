/* 탭 5 영업 인사이트. 주인공 도형은 응대 카드 미리 보기(위 2.5px 금색 선의 짙은 결과 카드)와 분류별 묶음.
   본문은 분석 문장(자료의 "문장"), 창구 말투의 예상 질문과 답("카드질문", "카드답")은 응대 카드 미리 보기 안에서만 쓴다.
   처음 선택은 자료의 pick 규칙(기준별[종형].먼저.카드)을 따르고, 담당자가 체크로 싣고 뺀다. 값과 문장은 sales.json 에서만 읽는다.
   관계도는 탭 4 가 내보낸 App.cover 를 쓴다(같은 판정, R10). */
App.registerTab((function () {
  const { ui, txt } = App;
  const { esc, fmt } = ui;
  const S = App.S;
  const CATS = S['분류'];
  const CARD_ORDER = S['카드분류차례'];
  const PURPOSES = S['목적'];
  const MARK = '내부 교육·비교 참고용(대외 배포 금지)';
  let purpose = null;
  const picks = {};          // 기준 종형 → 카드에 실을 포인트ID 집합
  const openOmit = new Set(); // 펼친 "뺀 포인트" 묶음
  let lastAdded = null;

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
  // 분류마다 세부 유형(설계안 4.2). 이름은 자료의 세부이름에서 모은다
  const SUB = { '관문 차이': ['G1', 'G2', 'G3'], '앞세울 강점': ['A1', 'A2'], '관련 담보 안내': ['Q1'], '조건 열위 방어': ['Q3'], '개정 검토 후보': ['Q2'] };
  const SUB_NAME = {};
  Object.values(S['포인트']).forEach(p => { if (p['세부'] && p['세부이름']) SUB_NAME[p['세부']] = p['세부이름']; });
  /** 포인트의 담보가 기준 종형의 단정 주의에도 들면 그 항목(같은 상대). 본문, 근거 기둥, 카드 모두 "우열을 매기지 않음"으로 보인다(R10) */
  function cautionOf(c, p) {
    if (!c || !c.base || !p || !p['표준담보ID']) return null;
    const peers = p['비교종형ID'] || [];
    return (c.base['단정주의'] || []).find(x => x['표준담보ID'] === p['표준담보ID'] && (x['상대종형ID'] || []).some(v => !peers.length || peers.includes(v))) || null;
  }
  const cautionNote = x => `단정 주의(${x['종류']})에도 든 담보라 우열을 매기지 않습니다. 위 문장의 차이는 사실로만 씁니다.`;
  /** 포인트의 판정 칩(관문 차이는 판정이 아니라 표지) */
  function pointChip(p, c) {
    if (cautionOf(c, p)) return ui.verdict('diff');
    const k = VK[p['세부']];
    return k ? ui.verdict(k) : '';
  }
  // 관문 차이는 담보가 없으므로 세부 이름을 이름으로 삼고, 견준 상대는 따로 적는다(근거 기둥 제목에는 함께)
  const titleOf = p => (p['표준담보ID'] ? stdN(p['표준담보ID']) : (p['세부이름'] || p['분류']));
  const titleLong = p => (p['표준담보ID'] ? stdN(p['표준담보ID']) : `${p['세부이름'] || p['분류']}, ${txt.peerNamesEtc((p['비교종형ID'] || []).map(fullN), 3)}`);

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
  function subCounts(c) {
    if (c.peerScope === 'all') return c.base['세부집계'] || {};
    const out = {};
    pts(c).forEach(p => { if (p['세부']) out[p['세부']] = (out[p['세부']] || 0) + 1; });
    return out;
  }
  function pickSet(c) {
    if (!picks[c.baseId]) picks[c.baseId] = new Set((c.base['먼저'] && c.base['먼저']['카드']) || []);
    return picks[c.baseId];
  }
  // 목적은 담보에 거는 거르개다. 담보가 없는 관문 차이는 목적과 무관하게 늘 보인다
  const inPurpose = p => !purpose || !p['표준담보ID'] || (p['목적'] || []).includes(purpose);
  const purposeInfo = () => PURPOSES.find(x => x['이름'] === purpose) || null;

  // ---------- 본문: 분류별 목록 ----------
  function itemHTML(p, sel, groupHead, c) {
    const h = head(p);
    const cau = cautionOf(c, p);
    const flag = p['원문대조'] ? ui.flag(p['원문대조글'] || ui.FLAG_TEXT) : '';
    const peerNames = txt.peerNamesEtc((p['비교종형ID'] || []).map(fullN), 3);
    return `<li class="lrow ins-it" data-pick="p:${esc(p['포인트ID'])}">
      <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${p['분류']}, ${titleLong(p)}. 근거 보기`)}"></button>${flag}
      <div class="ins-ih selbar">
        <span class="live ins-ckw"><label class="ins-ck"><input type="checkbox" data-act="ins-pick" data-id="${esc(p['포인트ID'])}"${sel.has(p['포인트ID']) ? ' checked' : ''} aria-label="${esc(titleLong(p))} 카드에 싣기"><span class="box" aria-hidden="true">${ui.IC.check}</span><span class="lb">카드에 싣기</span><span class="lb2" aria-hidden="true">싣기</span></label></span>
        <span class="ins-t">${esc(titleOf(p))}</span><span class="ins-tgd">${pointChip(p, c)}${p['구조다름'] ? ui.tag('구조 다름', '갱신이나 환급 구조가 다른 상대와 견준 문장') : ''}</span>
      </div>
      <div class="ins-tgm">${pointChip(p, c)}${p['구조다름'] ? ui.tag('구조 다름') : ''}${p['표준담보ID'] ? '' : `<span class="ins-pe">상대 ${esc(peerNames)}</span>`}</div>
      <p class="ins-s">${esc(p['문장'])}${c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : ''}</p>
      ${cau ? `<p class="ins-w ins-cau">${ui.verdict('diff')} ${esc(cautionNote(cau))}</p>` : ''}
      ${p['주의'] ? `<p class="ins-w">주의: ${esc(p['주의'])}</p>` : ''}
      <div class="ins-m">${(p['근거'] || []).map(evChip).join('')}${p['원문대조'] ? ui.flagText(p['원문대조글'] || ui.FLAG_TEXT) : ''}</div>
      ${h && h !== groupHead ? `<p class="ins-hd">${esc(h)}</p>` : ''}
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
    if (!groups.length) return '<p class="ins-empty">조건과 비교 범위에 드는 개정 검토 후보가 없습니다.</p>';
    return `<ul class="lrows ins-rev" id="ins-rev">${groups.map(({ g, gi, ds }) => `<li class="lrow ins-rg" data-pick="r:${gi}">
        <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${g['중분류']}, 개정 검토 후보 ${ds.length}건. 근거 보기`)}"></button>
        <div class="ins-ih selbar"><span class="ins-t">${esc(g['중분류'])}</span><span class="sub">${esc(g['대분류'])}</span>${ui.tag(`담보 ${ds.length}`)}${g['좁은담보만수'] ? ui.tag(`좁은 담보만 ${g['좁은담보만수']}`) : ''}${c.peerScope !== 'all' ? ui.fullScopeTag() : ''}</div>
        <ul class="ins-rl">${ds.map(d => {
          const p = S['포인트'][d['포인트ID']];
          const scOrgs = revRowOrgs(d, c);
          const holderTxt = c.peerScope === 'all'
            ? `가진 상대 <b class="num">${d['가진상대수']}</b>곳(${esc(txt.peerNamesEtc(d['가진상대'], 3))})`
            : `선택 범위 <b class="num">${scOrgs.length}</b>곳(${esc(txt.peerNamesEtc(scOrgs, 3))}), 전체 <b class="num">${d['가진상대수']}</b>곳 ${ui.fullScopeTag()}`;
          return `<li><span class="live ins-ckw"><label class="ins-ck sm"><input type="checkbox" data-act="ins-pick" data-id="${esc(d['포인트ID'])}"${sel.has(d['포인트ID']) ? ' checked' : ''} aria-label="${esc(d['담보'])} 카드에 싣기"><span class="box" aria-hidden="true">${ui.IC.check}</span></label></span>
            <span class="rn">${esc(d['담보'])}</span><span class="rt">${esc(d['급부유형'])}</span>
            <span class="rh">${holderTxt}</span>
            <span class="ro">우리 쪽 ${esc(d['우리상태'])}</span>
            <span class="rg">${p ? (p['근거'] || []).map(evChip).join('') : ''}</span></li>`;
        }).join('')}</ul>
        <span class="lrow-chev" aria-hidden="true">${ui.IC.chevR}</span></li>`).join('')}</ul>`;
  }
  function omitHTML(c, cat) {
    const pSet = new Set(c.activePeerOrgs || []);
    const list = (c.base['뺀포인트'] || []).filter(o => o['분류'] === cat && (c.peerScope === 'all' || (o['비교종형ID'] || []).some(v => pSet.has(orgOf(v)))));
    if (!list.length) return '';
    const open = openOmit.has(cat);
    return `<details class="ins-omit"${open ? ' open' : ''} data-cat="${esc(cat)}"><summary><span>뺀 포인트 ${list.length}건</span><span class="note">검토 대기이거나 조건이 다른 줄이 있어 세지 않은 것</span>${ui.IC.chevD}</summary>
      <ul>${list.map(o => `<li><b>${esc(stdN(o['표준담보ID']))}</b> <span class="tag">${esc(o['세부'])}</span><br><span class="note">상대 ${esc(txt.peerNamesEtc((o['비교종형ID'] || []).map(fullN), 3))}. ${esc(reasonText(o['사유']))}</span></li>`).join('')}</ul></details>`;
  }
  function catHTML(c, cat, i, sel) {
    const all = pts(c).filter(p => p['분류'] === cat);
    const shown = all.filter(inPurpose);
    const n = (catCounts(c))[cat] || 0;
    const sc = subCounts(c);
    const subT = (SUB[cat] || []).map(k => `${k}${SUB_NAME[k] ? ' ' + SUB_NAME[k] : ''} ${sc[k] || 0}`).join(', ');
    const heads = [...new Set(shown.map(head))];
    const groupHead = heads.length === 1 ? heads[0] : '';
    const inCard = all.filter(p => sel.has(p['포인트ID'])).length;
    let list;
    if (cat === '개정 검토 후보') list = revHTML(c, sel);
    else if (!all.length) list = `<p class="ins-empty">${esc(emptyWhy(c, cat))}</p>`;
    else if (!shown.length) list = '<p class="ins-empty">이 목적에 드는 항목이 없습니다.</p>';
    else list = `<ul class="lrows">${shown.map(p => itemHTML(p, sel, groupHead, c)).join('')}</ul>`;
    return `<section class="panel ins-cat" id="ins-cat-${i}" aria-labelledby="ins-cat-${i}-h">
      <div class="panel-h"><div><span class="k">${ui.scope('base')} ${esc(subT)}${cat === '개정 검토 후보' && c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : ''}</span>
        <h2 id="ins-cat-${i}-h"><span class="ins-no num">0${i + 1}</span>${esc(cat)} <b class="num">${n}</b>건${purpose && shown.length !== all.length && cat !== '개정 검토 후보' ? ` <span class="note">(목적에 맞는 ${shown.length}건)</span>` : ''}</h2></div>
        <div class="r"><span>카드에 실은 것 <b class="num">${inCard}</b>건</span>${cat === '개정 검토 후보' ? `<span class="live">${ui.btn('개정 검토 목록 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="ins-copy-rev"' })}${ui.btn('인쇄', { sm: true, ghost: true, icon: 'print', attrs: `data-print="ins-cat-${i}" data-title="개정 검토 목록"` })}</span>` : ''}</div></div>
      ${groupHead ? `<p class="ins-gh">${esc(groupHead)}</p>` : ''}
      ${list}
      ${omitHTML(c, cat)}
    </section>`;
  }
  function emptyWhy(c, cat) {
    const bi = c.baseInfo || {};
    if (cat === '관문 차이' && bi['심사'] === '일반심사') return '일반심사 종형이라 간편 고지 질문을 견주지 않아 관문 차이가 없습니다.';
    if (cat === '조건 열위 방어') return '맞붙는 상대보다 조건이 못한 담보가 없습니다(검토 대기와 조건이 다른 줄이 있는 것은 뺀 포인트에 있습니다).';
    if (cat === '앞세울 강점') return '견준 상대에 없는 담보나 조건이 나은 담보가 나오지 않았습니다.';
    return '이 분류에 든 항목이 없습니다.';
  }

  // ---------- 응대 카드 ----------
  function gateLine(c) {
    const g = c.seg;
    const who = App.condSegOnly();
    if (!g.cell) return `${who}: ${g.reason}${g.sexNote ? ` ${g.sexNote}` : ''}`;
    const cell = g.cell;
    const shownOrgs = (c.activeOrgs || txt.ORG_ORDER).filter(o => o in cell['회사']);
    let st;
    if (shownOrgs.length <= 4) {
      st = shownOrgs.map(o => `${txt.orgShort(o)} ${cell['회사'][o]}`).join(', ');
    } else {
      const openP = c.inScope(cell['열린상대코드']);
      const closedP = c.inScope(cell['닫힌상대코드']);
      const unkP = c.inScope(cell['모르는상대코드']);
      st = `${txt.orgShort('EPOST')} ${cell['회사'].EPOST || ''}, 상대 열림 ${openP}곳, 닫힘 ${closedP}곳${unkP ? `, 자료 없음 ${unkP}곳` : ''}`;
    }
    const why = shownOrgs.slice(0, 4).map(o => txt.stateWhy(o, cell['회사'][o])).filter(Boolean);
    const rep = cell['대표'] && cell['대표'] !== c.baseId ? ` 이 고객군의 우리 대표 종형은 ${kindN(cell['대표'])}입니다.` : '';
    return `${who}: ${cell['라벨']}${cell['보조'] ? `(${cell['보조']})` : ''}. ${st}.${rep}${why.length ? ` ${why.join(' ')}.` : ''}${g.sexNote ? ` ${g.sexNote}.` : ''}`;
  }
  function composeLine(c) {
    // 가입 관문 탭(tab3.js)이 App.card.comboLine(목적) 으로 알리는 구성 예시 한 줄. 목적 거르개가 전체면 가입 관문 탭의 목적을 쓴다
    try {
      if (App.card && typeof App.card.comboLine === 'function') { const t = App.card.comboLine(purpose || null); if (t) return { t: String(t), from: 'gate' }; }
    } catch (e) { console.error(e); }
    const L = c.limit;
    const who = `${c.st.age}세 ${txt.sexText(c.st.sex)}`;
    if (!L) return { t: `한도 자료 없음: ${kindN(c.baseId)}의 나이 구간별 한도 표가 없습니다.`, from: 'limit' };
    if (!L.hit) return { t: `${txt.josa(who, '는')} ${kindN(c.baseId)}의 가입나이(${L.lo}~${L.hi}세) 밖입니다.`, from: 'limit' };
    return { t: `${kindN(c.baseId)} 주계약 최대 가입금액 ${fmt(L.hit.max)}만원(${who}, 나이 구간별 한도 표의 ${L.hit.lo}~${L.hit.hi}세 구간${L.hit.pend ? ', 검토 대기' : ''}). 특약 구성 예시는 가입 관문 탭에서 봅니다.`, from: 'limit' };
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
    const body = groups.map(g => {
      const heads = [...new Set(g.xs.map(head))];
      return `<div class="sec">${esc(g.cat)} <span class="num">${g.xs.length}</span>건</div>
        ${heads.length === 1 && heads[0] ? `<p class="icd-hd">${esc(heads[0])}</p>` : ''}
        ${g.xs.map(p => `<div class="icd-qa${lastAdded === p['포인트ID'] ? ' icd-new' : ''}">
          ${heads.length > 1 && head(p) ? `<p class="icd-hd">${esc(head(p))}</p>` : ''}
          ${p['카드질문'] ? `<p class="icd-q"><span class="icd-l">예상 질문</span>${esc(p['카드질문'])}</p>` : ''}
          <p class="icd-a"><span class="icd-l">${p['카드질문'] ? '답' : '설명'}</span>${esc(p['카드답'] || p['문장'])}</p>
          ${cautionOf(c, p) ? `<p class="icd-w">주의: ${esc(cautionNote(cautionOf(c, p)))}</p>` : ''}
          ${p['주의'] ? `<p class="icd-w">주의: ${esc(p['주의'])}</p>` : ''}
          ${p['원문대조'] ? `<p class="icd-f">${ui.flagText(p['원문대조글'] || ui.FLAG_TEXT)}</p>` : ''}</div>`).join('')}`;
    }).join('');
    return `<div class="rcard ins-card" id="insight-card" aria-label="응대 카드 미리 보기">
      <div class="icd-nt no-print"><span>${esc(S['고지'])}</span><span class="icd-mk">${esc(MARK)}</span></div>
      <span class="k">응대 카드, 지금 조건과 기준 종형</span>
      <h3>우체국 ${esc(kindN(c.baseId))}<br><span class="gold-t">${esc(App.condSegOnly())}</span></h3>
      <div class="sec">조건과 견준 상품</div>
      <p class="icd-sm">기준 ${esc(txt.josa(`${fullN(c.baseId)}(${vinfo(c.baseId)['적용시작일'] || '기준일 자료 없음'})`, '와'))} ${esc(txt.josa(peers, '를'))} 견줬습니다. 자료 기준 ${esc(App.asofText())}.</p>
      <div class="sec">가입 관문</div>
      <p class="icd-sm">${esc(gateLine(c))}</p>
      ${n ? body : '<div class="sec">실은 항목</div><p class="icd-sm">실은 항목이 없습니다. 왼쪽 목록에서 "카드에 싣기"를 체크합니다.</p>'}
      <div class="sec">구성 요약</div>
      <p class="icd-sm">${esc(comp.t)}</p>
      <div class="sec">유의사항</div>
      <ul class="icd-nb">
        <li>가입 여부는 청약 뒤 인수 심사로 정해집니다. 이 카드는 심사를 대신하지 않습니다.</li>
        <li>보험료와 질병코드는 반영하지 않았습니다.</li>
        <li>유지 중인 다른 회사 계약의 해지를 권하지 않습니다.</li>
        <li>${flagN ? `원문 확인이 필요한 항목 ${flagN}건은 사업방법서 원문과 대조한 뒤 씁니다.` : '이 카드에는 원문 확인이 필요한 항목이 없습니다.'}</li>
        <li>문장은 대표 조건(${esc(`${c.ref['나이']}세 ${txt.sexText(c.ref['성별'])}, ${txt.sinceText(c.ref['이력'])}`)})과 수집한 공시 문서로 계산했습니다.</li>
      </ul>
    </div>`;
  }
  function cardPanel(c) {
    const groups = cardItems(c);
    const n = groups.reduce((a, g) => a + g.xs.length, 0);
    return `<div class="ins-cw">
      <div class="ins-ct"><div><span class="k">${ui.scope('base')} 산출물</span><h2>응대 카드 미리 보기</h2></div>
        <div class="ins-cb">${ui.btn('인쇄', { main: true, icon: 'print', attrs: 'data-print="insight-card" data-card="1" data-title="응대 카드"' })}${ui.btn('카드 글 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="ins-copy-card"' })}</div></div>
      <p class="ins-cn"><span>실은 항목 <b class="num">${n}</b>건</span>${ui.btn('처음 선택으로', { sm: true, ghost: true, attrs: 'data-act="ins-reset"' })}<span class="ins-over" id="ins-over" role="status"></span></p>
      ${cardHTML(c)}
    </div>`;
  }
  /** 응대 카드 열의 sticky 위치. 카드가 화면보다 길면 위치를 음수로 두어, 쪽을 내리면 카드 아래 끝까지 보이고 거기서 멈춘다(안쪽 스크롤 없음) */
  function stick(body) {
    const r = body && body.querySelector('.ins-r');
    if (!r) return;
    if (getComputedStyle(r).position !== 'sticky') { r.style.top = ''; return; }
    const headEl = document.getElementById('head');
    const headH = headEl ? headEl.offsetHeight : 0;
    r.style.top = `${Math.min(headH + 16, innerHeight - r.offsetHeight - 16)}px`;
  }
  App.on('resize', () => { const b = document.querySelector('#view-insight .vbody'); if (b) stick(b); });
  /** A4 한 장(인쇄 영역 182x269mm)에 드는지 잰다. 인쇄 머리(고지, 범위)까지 더한다 */
  function checkPages(body) {
    const card = body.querySelector('#insight-card');
    const out = body.querySelector('#ins-over');
    if (!card || !out) return;
    const box = document.createElement('div');
    box.className = 'icd-measure';
    box.innerHTML = `<div class="ph">${esc(S['고지'])}<span class="mk">${esc(MARK)}</span><span class="sc">응대 카드 / ${esc(App.scopeLine())}</span></div>`;
    box.appendChild(card.cloneNode(true));
    document.body.appendChild(box);
    const h = box.scrollHeight;
    box.remove();
    const page = 269 / 25.4 * 96;
    const over = h > page;
    out.textContent = over ? `A4 한 장을 넘습니다(약 ${(h / page).toFixed(1)}장). 항목을 빼면 한 장에 들어갑니다.` : `A4 한 장 안(약 ${Math.round(h / page * 100)}%)`;
    out.classList.toggle('over', over);
  }

  // ---------- 그리기 ----------
  function concl(c) {
    const cnt = catCounts(c);
    const total = Object.values(cnt).reduce((a, n) => a + n, 0);
    const sel = pickSet(c);
    const first = pts(c).filter(p => sel.has(p['포인트ID'])).length;
    return `<p class="concl">우체국 ${esc(kindN(c.baseId))} 기준 영업 인사이트 ${total}건: ${CATS.map(k => `${k} ${cnt[k] || 0}`).join(', ')}. 응대 카드에는 현재 ${first}건이 실려 있습니다.</p>`;
  }
  function refNote(c) {
    const parts = [];
    if (!c.isRef) parts.push(`지금 조건(${App.condSegOnly()})을 바꿔도 분류별 문장은 대표 조건(${c.ref['나이']}세 ${txt.sexText(c.ref['성별'])}, ${txt.sinceText(c.ref['이력'])}) 기준이라 그대로입니다. 응대 카드의 가입 관문과 구성 요약은 지금 조건으로 바뀝니다.`);
    if (c.st.renewal) parts.push('갱신 유형 거르개는 고객군 지도에만 씁니다.');
    return parts.length ? `<p class="ins-ref">${esc(parts.join(' '))}</p>` : '';
  }
  function jumpHTML(c) {
    const cnt = catCounts(c);
    return `<nav class="ins-jump" aria-label="분류 바로가기">${CATS.map((k, i) => `<a href="#ins-cat-${i}" data-act="ins-jump" data-i="${i}"><span class="num">0${i + 1}</span><span class="t">${esc(k)}</span><b class="num">${cnt[k] || 0}</b></a>`).join('')}</nav>`;
  }
  function render(body, c) {
    if (!c.base) { body.innerHTML = '<div class="panel placeholder">자료 없음: 이 기준 종형의 영업 인사이트 자료가 없습니다.</div>'; return; }
    const sel = pickSet(c);
    const pi = purposeInfo();
    body.innerHTML = `${concl(c)}${refNote(c)}
      <div class="ins-grid">
        <div class="ins-l">
          <div class="ins-tools panel flat">
            <div class="ins-pf"><span class="lb">목적</span><span data-slot="purpose"></span>
              <span class="ins-pn">보장 대분류 기준${pi ? `: ${esc(txt.josa(pi['이름'], '은'))} ${esc(pi['기준'])}, ${esc(pi['값'].join(', '))}` : ', 입원과 수술은 급부유형 기준'}</span></div>
            <span class="live">${ui.btn('분류 목록 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="ins-copy-list"' })}</span>
          </div>
          ${jumpHTML(c)}
          ${CATS.map((k, i) => catHTML(c, k, i, sel)).join('')}
        </div>
        <aside class="ins-r" aria-label="응대 카드">${cardPanel(c)}</aside>
      </div>`;
    const slot = body.querySelector('[data-slot="purpose"]');
    slot.replaceWith(ui.chevSel({ label: '목적', options: [{ v: null, t: '전체' }].concat(PURPOSES.map(p => ({ v: p['이름'], t: p['이름'], title: `${p['기준']}: ${p['값'].join(', ')}` }))), value: purpose, w: '112px',
      onChange: v => { purpose = v; refreshList(body); refreshCard(body); } }));
    bind(body);
    checkPages(body);
    stick(body);
  }
  function refreshList(body) {
    const c = App.ctx();
    const sel = pickSet(c);
    CATS.forEach((k, i) => { const el = body.querySelector('#ins-cat-' + i); if (el) el.outerHTML = catHTML(c, k, i, sel); });
    const pn = body.querySelector('.ins-pn');
    const pi = purposeInfo();
    if (pn) pn.textContent = `보장 대분류 기준${pi ? `: ${txt.josa(pi['이름'], '은')} ${pi['기준']}, ${pi['값'].join(', ')}` : ', 입원과 수술은 급부유형 기준'}`;
    remarkSel(body);
  }
  function refreshCard(body) {
    const c = App.ctx();
    const w = body.querySelector('.ins-cw');
    if (w) w.outerHTML = cardPanel(c);
    CATS.forEach((k, i) => {
      const el = body.querySelector(`#ins-cat-${i} .panel-h .r b.num`);
      if (el) el.textContent = String(pts(c).filter(p => p['분류'] === k && pickSet(c).has(p['포인트ID'])).length);
    });
    checkPages(body);
    stick(body);
    lastAdded = null;
  }
  function remarkSel(body) {
    const key = App.state.sel.insight;
    body.querySelectorAll('[data-pick]').forEach(el => {
      const on = el.dataset.pick === key;
      el.classList.toggle('is-sel', on);
      const hit = el.querySelector('.lrow-hit'); if (hit) hit.setAttribute('aria-pressed', String(on));
    });
  }
  function bind(body) {
    if (body._b) return;
    body._b = true;
    body.addEventListener('change', e => {
      const ck = e.target.closest('input[data-act="ins-pick"]');
      if (!ck) return;
      const c = App.ctx();
      const sel = pickSet(c);
      const id = ck.dataset.id;
      if (ck.checked) { sel.add(id); lastAdded = id; } else sel.delete(id);
      body.querySelectorAll(`input[data-act="ins-pick"][data-id="${CSS.escape(id)}"]`).forEach(x => { x.checked = ck.checked; });
      refreshCard(body);
      App.toast(ck.checked ? '응대 카드에 실었습니다' : '응대 카드에서 뺐습니다');
    });
    body.addEventListener('toggle', e => {
      const d = e.target.closest && e.target.closest('details.ins-omit');
      if (!d) return;
      if (d.open) openOmit.add(d.dataset.cat); else openOmit.delete(d.dataset.cat);
    }, true);
    body.addEventListener('click', e => {
      const a = e.target.closest('[data-act]');
      if (!a) return;
      const act = a.dataset.act;
      if (act === 'ins-reset') { delete picks[App.state.base]; refreshCard(body); refreshList(body); App.toast('처음 선택으로 되돌렸습니다'); }
      else if (act === 'ins-copy-list') copyList();
      else if (act === 'ins-copy-rev') copyRev();
      else if (act === 'ins-copy-card') copyCard(body);
      else if (act === 'ins-jump') {
        e.preventDefault();
        const el = body.querySelector('#ins-cat-' + a.dataset.i);
        if (el) el.scrollIntoView({ block: 'start', behavior: App.motionOn() ? 'smooth' : 'auto' });
      }
    });
  }

  // ---------- 복사 ----------
  const evText = p => (p['근거'] || []).map(g => `${orgN(g['종형ID'])} ${txt.pageText(g['문서'], g['쪽'])}`).join('; ');
  function copyList() {
    const c = App.ctx();
    const sel = pickSet(c);
    const rows = CATS.flatMap(cat => pts(c).filter(p => p['분류'] === cat && inPurpose(p)).map(p => { const cau = cautionOf(c, p); return [p['분류'], `${p['세부']} ${p['세부이름']}`, titleLong(p), p['문장'], cau ? `우열을 매기지 않음(단정 주의: ${cau['종류']})` : '', head(p), evText(p), p['원문대조'] ? (p['원문대조글'] || ui.FLAG_TEXT) : '', p['구조다름'] ? '구조 다름' : '', sel.has(p['포인트ID']) ? '실음' : '']; }));
    App.copyRows(['분류', '세부', '담보나 항목', '분석 문장', '단정 주의', '범위 머리말', '근거', '원문 확인', '구조', '응대 카드'], rows, { title: `영업 인사이트 분류별 목록${purpose ? ` (목적 ${purpose})` : ''}` });
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
    App.copyRows(['보장 대분류', '보장 중분류', '담보', '급부유형', '가진 상대 수', '가진 상대', '우리 쪽 상태', '근거 쪽'], rows, { title: `개정 검토 목록${purpose ? ` (목적 ${purpose})` : ''}` });
  }
  function copyCard(body) {
    const card = body.querySelector('#insight-card');
    if (!card) return;
    const lines = [S['고지'], MARK];
    card.querySelectorAll(':scope > .k, :scope > h3, :scope > .sec, :scope > p, .icd-qa > p, .icd-nb li').forEach(el => {
      const t = el.innerText.replace(/\s+/g, ' ').trim();
      if (t) lines.push(el.matches('.sec') ? `[${t}]` : el.matches('li') ? `- ${t}` : t);
    });
    App.copyText(lines.join('\r\n'), '카드 글을 복사했습니다');
  }

  // ---------- 근거 기둥 ----------
  function sec(title, html, lo) { return `<div class="ev-sec${lo ? ' lo' : ''}">${title ? `<h3>${title}</h3>` : ''}${html}</div>`; }
  function pickPoint(c, id) {
    const p = S['포인트'][id];
    if (!p || !(c.base['포인트'] || []).includes(id)) return null;
    const sid = p['표준담보ID'];
    const relOk = sid && App.cover && App.cover.hasRow(c.baseId, sid);
    const tv = relOk ? App.cover.verdictOf(c.baseId, sid) : null;
    const peers = App.cover && relOk ? App.cover.peerCols(c.baseId).slice(1) : [];
    const tableV = tv ? tv.map((v, i) => (v ? `<span class="cv-bd"><span>${esc(txt.josa(orgN(peers[i]), '과'))}</span>${ui.verdict(v.kind, v.text, v.why)}</span>` : '')).join(' ') : '';
    const omit = sid ? (c.base['뺀포인트'] || []).filter(o => o['표준담보ID'] === sid) : [];
    const cau = cautionOf(c, p);
    let body = sec('', `<p>${esc(p['문장'])}</p>${p['원문대조'] ? `<p>${ui.flagText(p['원문대조글'] || ui.FLAG_TEXT)}</p>` : ''}${cau ? `<p>${ui.verdict('diff')}</p><p class="note">${esc(cautionNote(cau))} ${esc(cau['문장'])}</p>` : ''}${p['주의'] ? `<p class="note">주의: ${esc(p['주의'])}</p>` : ''}
      ${tableV ? `<p class="note" style="margin-top:8px">담보 비교표의 판정: </p><div class="cv-bds">${tableV}</div>` : ''}`);
    if (relOk) body += sec('관계도', `<div class="ins-rel"></div>${App.cover.relLegend()}`);
    body += sec('근거 문서와 쪽', `<ul class="cv-evl">${(p['근거'] || []).map(g => `<li><b>${esc(fullN(g['종형ID']))}</b> ${evChip(g)}${g['급부명'] ? `<br><span class="note">${esc(g['급부명'])}</span>` : ''}</li>`).join('')}</ul>${(p['근거'] || []).some(g => g['쪽'] == null) ? `<p class="note">${esc(txt.PAGE_WHY)}.</p>` : ''}`, true);
    body += sec('범위 머리말', `<p class="note">${esc(head(p))}</p><p class="note">견준 ${c.base['범위']['회사수']}개 회사 가운데 ${p['회사수']}곳에 대한 문장입니다.</p>`, true);
    if (omit.length) body += sec('뺀 것', `<ul class="cv-evl">${omit.map(o => `<li>${esc(o['분류'])}(${esc(o['세부'])}): ${esc(reasonText(o['사유']))}</li>`).join('')}</ul>`, true);
    return {
      kicker: `${p['분류']}, ${p['세부']} ${p['세부이름']}`, title: titleLong(p),
      badges: [ui.scope('base'), pointChip(p, c) || ui.tag(p['분류']), p['구조다름'] ? ui.tag('구조 다름') : '', (p['목적'] || []).length ? ui.tag(`목적 ${p['목적'].join(', ')}`) : ''].filter(Boolean),
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
        ? `가진 상대 ${d['가진상대수']}곳(${esc(txt.peerNamesEtc(d['가진상대'], 3))})`
        : `선택 범위 ${scOrgs.length}곳(${esc(txt.peerNamesEtc(scOrgs, 3))}), 전체 ${d['가진상대수']}곳`;
      return `<li><b>${esc(d['담보'])}</b> ${ui.verdict('none')}${c.peerScope !== 'all' ? ' ' + ui.fullScopeTag() : ''}<br><span class="note">${holderNote}, 우리 쪽 ${esc(d['우리상태'])}</span>${p ? `<p>${esc(p['문장'])}</p><div class="ins-evc">${(p['근거'] || []).map(evChip).join('')}</div>` : ''}</li>`;
    }).join('');
    return {
      kicker: '개정 검토 후보, 보장 중분류', title: g['중분류'], badges: [ui.scope('base'), ui.tag(g['대분류']), ui.tag(`담보 ${list.length}`), c.peerScope !== 'all' ? ui.fullScopeTag() : ''].filter(Boolean),
      body: sec('', `<p>${esc(txt.josa(g['중분류'], '은'))} 담보 ${list.length}개가 개정 검토 후보입니다${g['좁은담보만수'] ? `(우리 쪽에 좁은 담보만 있는 것 ${g['좁은담보만수']}개)` : ''}.</p>`)
        + sec('담보', `<ul class="cv-evl">${items}</ul>`)
        + sec('', `<p class="note">빈자리 기준은 맞붙는 상대 두 곳 이상이 가진 담보입니다. 담보 이름을 담보 비교 탭의 비교표에서 찾으면 회사별 조건이 보입니다.</p>${list.map(d => `<button type="button" class="btn sm" data-act="cv-goto" data-sid="${esc(d['표준담보ID'])}">${esc(d['담보'])} 비교표에서 보기${ui.IC.chevR}</button>`).join(' ')}`, true),
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
      kicker: '읽는 법', title: '분류별 목록과 응대 카드', badges: [ui.scope('base')],
      body: sec('분류별 집계', ui.eq({ total: { t: '인사이트', n: total }, parts: CATS.map(k => ({ t: k, n: cnt[k] || 0 })), tail: '건' })
          + `<p class="note">분류끼리는 서로 겹치지 않습니다. 검토 대기이거나 조건이 다른 줄이 있어 뺀 포인트 ${(c.base['뺀포인트'] || []).length}건은 세지 않고 분류마다 접어 둡니다.</p>`)
        + sec('처음 선택', `<p class="note">응대 카드의 처음 선택은 세부 유형마다 한 건을 먼저 넣고, 카드에서는 조건 열위 방어와 관련 담보 안내를 개정 검토 후보보다 앞에 둡니다. 체크로 싣고 빼면 카드가 바로 바뀝니다.</p>`)
        + sec('본문과 카드', `<p class="note">본문은 분석 문장입니다. 창구 말투의 예상 질문과 답은 응대 카드 미리 보기 안에서만 씁니다. 카드를 인쇄하면 흰 바탕 A4 한 장에 고지와 "${esc(MARK)}" 표식이 찍힙니다.</p>`)
        + sec('판정 표지', App.ev.legend(), true),
    };
  }
  function focus(key, body) {
    const el = key === 'card' ? body.querySelector('#insight-card') : key === 'rev' ? body.querySelector('#ins-rev') : null;
    if (el) el.scrollIntoView({ block: 'start', behavior: App.motionOn() ? 'smooth' : 'auto' });
  }
  // 가입 관문 탭에서 목적을 바꾸면 카드의 구성 요약을 고친다
  document.addEventListener('c4:card', () => {
    if (App.state.tab !== 'insight') return;
    const body = document.querySelector('#view-insight .vbody');
    if (body && body.querySelector('.ins-cw')) refreshCard(body);
  });
  function enter(body) {
    if (body.querySelector('.ins-cw')) refreshCard(body);
    const card = body.querySelector('#insight-card');
    if (card && App.motionOn()) { card.classList.remove('icd-in'); void card.offsetWidth; card.classList.add('icd-in'); }
    checkPages(body);
    stick(body);
  }
  function update(body, c) {
    if (c.changed.has('base') || c.changed.has('peerScope') || c.changed.has('peerPick')) return false;
    const old = body.querySelector('.ins-ref');
    const html = refNote(c);
    if (old) { if (html) old.outerHTML = html; else old.remove(); }
    else if (html) body.querySelector('.concl').insertAdjacentHTML('afterend', html);
    refreshCard(body);
    return true;
  }

  return { id: 'insight', kicker: '인사이트와 산출물', render, update, pick, evidence, focus, enter };
})());
