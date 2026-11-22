/* 탭 2 고객군과 시장: 주인공 도형은 구역 지도(이력 12행 x 나이 구간). 아래는 개정 변동과 시장 소식.
   값과 문장은 sales.json 의 지도, 포인트, 개정변동, 시장소식에서 읽는다. 화면은 칸 수를 세고 자료의 문장을 옮길 뿐 판정을 짓지 않는다. */
App.registerTab((function () {
  const { ui, txt } = App;
  const { esc, fmt } = ui;
  const S = App.S;
  const LABELS = S['라벨'];
  const CATS = S['분류'].concat(['검토 대기']);
  const CAT_SHORT = { '관문 차이': '관문', '앞세울 강점': '강점', '관련 담보 안내': '관련', '조건 열위 방어': '열위', '개정 검토 후보': '개정', '검토 대기': '대기' };
  const ORGS = txt.ORG_ORDER;
  const ORG_INI = { EPOST: '우', HANWHALIFE: '한', SAMSUNGFIRE: '삼' };
  const ST_IC = { '열림': ui.IC.open, '닫힘': ui.IC.lock, '심사로 확인': ui.IC.check, '나이 자료 없음': ui.IC.hatch, '질문 자료 없음': ui.IC.hatch };
  const REN_OPTS = [{ v: null, t: '전체' }, { v: '갱신', t: '갱신' }, { v: '비갱신', t: '비갱신' }];
  const BASE_IDS = S['기준종형'].map(b => b['종형ID']);
  const NEWS = S['시장소식'];
  const REV = S['개정변동'];

  // ---------- 작은 도구 ----------
  const renText = r => (r == null ? '갱신 유형 전체' : `${r} 종형만`);
  const rowGroup = row => (row['종류'] === '수술만' ? '입원 없이 수술만' : '입원이 있었음');
  const rowShort = row => row['이름'].replace(/^(입원|수술만)\s*/, '');
  const colText = col => `${col.lo}~${col.hi}세`;
  // 칸 열쇠에 갱신 유형을 넣는다. 거르개를 바꾸면 열 구간이 달라지므로 앞서 고른 칸은 풀린다
  const REN_KEY = r => (r == null ? 'a' : r === '갱신' ? 'g' : 'n');
  const keyOf = (ri, ci) => `m${REN_KEY(App.state.renewal)}${ri}-${ci}`;
  const parseKey = k => {
    const m = /^m([agn])(\d+)-(\d+)$/.exec(k);
    return m && m[1] === REN_KEY(App.state.renewal) ? { ri: +m[2], ci: +m[3] } : null;
  };
  const vk = vid => (vid ? txt.vkind(vid) : '');
  const jo = (word, p) => txt.josa(word, p).slice(String(word).length);
  function cellAt(map, ri, ci) { return (map['칸'][ri] || [])[ci] || null; }
  function notes(cell, long) {
    const out = [];
    if (cell['보조']) out.push(cell['보조']);
    if (cell['닫힌사유'] && cell['닫힌사유'].length) out.push(`${long ? '닫힌 사유: ' : '사유 '}${cell['닫힌사유'].join(', ')}`);
    return out;
  }
  function tally(map) {
    const lab = map['라벨별'] || {};
    let total = 0;
    map['칸'].forEach(r => { total += r.length; });
    const gap = {};          // 회사별 자료 없음 칸 수와 그 상태
    const closed = {};       // 닫힌 사유별 칸 수
    let closedCells = 0;
    map['칸'].forEach(r => r.forEach(c => {
      (c['자료없음'] || []).forEach(o => { gap[o] = gap[o] || { n: 0, state: c['회사'][o] }; gap[o].n++; });
      if (c['닫힌사유'] && c['닫힌사유'].length) { closedCells++; c['닫힌사유'].forEach(x => { closed[x] = (closed[x] || 0) + 1; }); }
    }));
    return { lab, total, gap, closed, closedCells };
  }


  // ---------- 지도 ----------
  function cellHTML(map, ri, ci, c) {
    const cell = cellAt(map, ri, ci);
    const row = map['행'][ri], col = map['열'][ci];
    const cls = ui.MAP_CLS[cell['라벨']] || 'm-none';
    const now = c.seg && c.seg.cell && c.seg.ri === ri && c.seg.ci === ci;
    const sub = notes(cell);
    const orgs = ORGS.filter(o => o in cell['회사']).map(o => {
      const s = cell['회사'][o];
      return `<span class="mk-os${(cell['자료없음'] || []).includes(o) ? ' gap' : ''}"><b>${ORG_INI[o]}</b>${ST_IC[s] || ''}</span>`;
    }).join('');
    const n = cell['분류수'] || {};
    const counts = CATS.map(k => `<b>${n[k] == null ? '' : fmt(n[k])}</b>`).join('');
    const flag = cell['라벨'] === '우리 간편만 열림' ? ui.flag() : '';
    const gateOnly = cell['관문만수집'] || [];
    const goHTML = gateOnly.length
      ? `<span class="mk-go">${gateOnly.map(x => `<span class="mk-gob">관문만 수집</span><span>${esc(x['이름'])}</span>`).join(', ')}</span>`
      : '';
    const goAria = gateOnly.length ? `, ${gateOnly.map(x => `${x['이름']} ${x['안내'] || '관문만 수집(담보 미수집)'}`).join(', ')}` : '';
    const label = `${row['이름']}, ${colText(col)}: ${cell['라벨']}${sub.length ? ' (' + sub.join(', ') + ')' : ''}${goAria}${now ? ', 지금 조건' : ''}. 근거 보기`;
    return `<button type="button" class="sq mk-cell" data-l="${cls}" data-pick="${keyOf(ri, ci)}" aria-pressed="false" aria-label="${esc(label)}" style="--d:${(ri + ci * 2) * 22}ms">
      <i class="mk-bg ${cls}" aria-hidden="true"></i>
      <i class="cur t"></i><i class="cur r"></i><i class="cur b"></i><i class="cur l"></i>
      ${flag}
      <span class="mk-l">${esc(cell['라벨'])}</span>
      <span class="mk-o" aria-hidden="true">${orgs}</span>
      <span class="mk-s">${now ? `<span class="mk-now">${ui.IC.pin}지금 조건</span>` : ''}${esc(sub.join(', '))}</span>
      <span class="mk-n" aria-hidden="true">${counts}</span>
      ${goHTML}
    </button>`;
  }
  function mapHTML(c) {
    const map = App.mapOf(c.st.renewal);
    const nc = map['열'].length;
    const head = `<div class="mk-corner"><span>마지막 입원이나 수술</span><span class="num">나이 ${ui.IC.arrow}</span></div>` + map['열'].map(col => `<div class="mk-ch"><b class="num">${esc(colText(col))}</b><span class="mk-nh" aria-hidden="true">${CATS.map(k => `<i>${esc(CAT_SHORT[k])}</i>`).join('')}</span></div>`).join('');
    let body = '', lastG = '';
    map['행'].forEach((row, ri) => {
      const g = rowGroup(row);
      if (g !== lastG) { body += `<div class="mk-gh"><span>${esc(g)}</span><i></i></div>`; lastG = g; }
      body += `<div class="mk-rh">${esc(rowShort(row))}</div>`;
      for (let ci = 0; ci < nc; ci++) body += cellHTML(map, ri, ci, c);
    });
    return `<div class="mk-grid" id="mk-grid" style="--nc:${nc}" role="group" aria-label="고객군 지도, ${esc(txt.sexText(map['성별']))} 기준, ${esc(renText(c.st.renewal))}">${head}${body}</div>`;
  }
  function sumHTML(c) {
    const map = App.mapOf(c.st.renewal);
    const t = tally(map);
    const strip = [];
    LABELS.forEach(l => { for (let i = 0; i < (t.lab[l] || 0); i++) strip.push(ui.MAP_CLS[l]); });
    return `<div class="mk-sum">${ui.eq({ total: { t: '고객군', n: t.total }, parts: LABELS.map(l => ({ t: l, n: t.lab[l] || 0 })), tail: '칸' })}${ui.cells(strip)}</div>`;
  }
  function footHTML(c) {
    const map = App.mapOf(c.st.renewal);
    const t = tally(map);
    const gaps = Object.entries(t.gap).map(([o, x]) => `<li>${ui.IC.hatch}<span><b>${esc(txt.orgShort(o))}</b> 자료 없음 표지 ${fmt(x.n)}칸. ${esc(txt.stateWhy(o, x.state) || '')}</span></li>`).join('');
    const closedT = Object.entries(t.closed).map(([k, n]) => `${k} ${fmt(n)}칸`).join(', ');
    const closedSum = Object.values(t.closed).reduce((a, b) => a + b, 0);
    const rows = LABELS.map(l => [`${ui.swatch(l)} ${esc(l)}`, fmt(t.lab[l] || 0)]);
    return `<div class="mk-foot3">
      <div class="mk-tl">${ui.table({ id: 'mk-tally', head: ['주 라벨', '칸 수'], rows, num: [1], caption: `고객군 지도 집계(${esc(txt.sexText(map['성별']))}, ${esc(renText(c.st.renewal))})` })}</div>
      <div class="mk-nt">
        ${t.closedCells ? `<p class="note">우리 간편이 닫힌 칸 ${fmt(t.closedCells)}칸의 사유는 ${esc(closedT)}입니다.</p>${closedSum > t.closedCells ? `<div class="nadd">한 칸에 사유 둘이 함께 들 수 있어 사유별 칸 수를 더하면 ${fmt(closedSum)}칸으로 ${fmt(t.closedCells)}칸보다 큽니다.</div>` : ''}` : '<p class="note">우리 간편이 닫힌 칸이 없습니다.</p>'}
        ${gaps ? `<ul class="mk-gap">${gaps}</ul>` : ''}
        <p class="note">칸의 수는 기준 종형과 조건을 바꿔도 그대로입니다. 갱신 유형 거르개를 바꾸면 그 유형의 종형만으로 다시 센 지도로 바뀝니다.</p>
      </div>
      <div class="mk-acts">${ui.btn('집계 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-copy="mk-tally" data-title="고객군 지도 집계"' })}${ui.btn('칸 목록 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="mk-copy-cells"' })}</div>
    </div>`;
  }
  function legendHTML(map) {
    return `<div class="mk-legend" aria-label="지도 읽는 법">
      <span class="lg">${LABELS.map(l => `<span>${ui.swatch(l)}${esc(l)}</span>`).join('')}</span>
      <span class="lg">${ORGS.map(o => `<span><b>${ORG_INI[o]}</b> ${esc(txt.orgShort(o))}</span>`).join('')}<span>${ui.IC.open}열림</span><span>${ui.IC.lock}닫힘</span><span>${ui.IC.check}심사로 확인</span><span>${ui.IC.hatch}자료 없음</span><span><span class="mk-gob">관문만 수집</span>담보 미수집 종형만 열림</span></span>
      <span class="lg mk-lgn">칸 안 숫자 여섯은 차례대로 ${CATS.map(k => esc(k)).join(', ')}의 수입니다. 비어 있으면 견줄 대표 종형이 없는 칸입니다. 칸에 우열을 매기지 않습니다.</span>
    </div>`;
  }
  function mapPanel(c) {
    const map = App.mapOf(c.st.renewal);
    const sexNote = c.seg && c.seg.sexNote ? `<p class="mk-why">${esc(c.seg.sexNote)}</p>` : '';
    const segWhy = c.seg && !c.seg.cell && c.seg.reason ? `<p class="mk-why">지금 조건의 칸이 이 지도에 없습니다. ${esc(c.seg.reason)}</p>` : '';
    return `<section class="panel mk-map" id="mk-map" aria-labelledby="mk-map-h">
      <div class="panel-h">
        <div><span class="k">${ui.scope('all')} <span class="mk-k">${esc(txt.sexText(map['성별']))} 기준, ${esc(renText(c.st.renewal))}</span></span><h2 id="mk-map-h">고객군 지도</h2></div>
        <div class="r"><span class="mk-renl">갱신 유형</span><span data-slot="mk-ren"></span></div>
      </div>
      ${sexNote}${segWhy}
      ${sumHTML(c)}
      <div class="mk-body">${mapHTML(c)}</div>
      <div class="panel-f">${legendHTML(map)}</div>
      ${footHTML(c)}
      ${ui.notes('고객군과 시장')}
    </section>`;
  }

  // ---------- 개정과 시장 ----------
  function revTable() {
    const th = ['담보', '종류', '달라진 항목', '종형'].map(h => `<th scope="col">${esc(h)}</th>`).join('');
    const tr = REV['담보'].map((d, i) => {
      const full = d['종형ID'].map(vk);
      const short = full.map(n => txt.shortName(n).short);
      return `<tr class="pick" data-pick="rv${i}" tabindex="0"><td>${esc(d['담보'])}</td><td data-cp="${esc(d['종류'])}">${ui.tag(d['종류'])}</td><td>${esc(d['항목'].join(', '))}</td>
        <td data-cp="${esc(full.join(', '))}"><span title="${esc(full.join(', '))}">${esc(short.join(', '))}</span>${ui.RCHEV}</td></tr>`;
    }).join('');
    return `<table class="tbl" id="mk-rev-tbl"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>`;
  }
  function revPanel() {
    const n = REV['수'];
    const pairSum = REV['짝'].reduce((a, p) => a + p['신설'] + p['변경'] + p['종료'], 0);
    const pairs = REV['짝'].map(p => `<li><b>${esc(vk(p['후']))}</b><span class="num">신설 ${fmt(p['신설'])}, 변경 ${fmt(p['변경'])}, 종료 ${fmt(p['종료'])}</span></li>`).join('');
    const ages = (REV['가입나이변경'] || []).map(vk);
    const gates = (REV['관문변경'] || []).map(vk);
    return `<section class="panel tbl-wrap mk-rev" aria-labelledby="mk-rev-h">
      <div class="panel-h">
        <div><span class="k">${ui.scope('all')}</span><h2 id="mk-rev-h">우체국 직전 개정과 견준 변동</h2></div>
        <div class="r">${ui.btn('표 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-copy="mk-rev-tbl" data-title="개정 변동"' })}</div>
      </div>
      <div class="mk-pad">
        <ul class="mk-pairs">${pairs}</ul>
        ${REV['짝'].length > 1 ? `<div class="nadd">개정 짝 ${REV['짝'].length}개의 수를 더하면 ${fmt(pairSum)}건입니다. 같은 담보가 여러 짝에서 바뀌면 짝마다 세므로 ${fmt(n['전체'])}건보다 큽니다.</div>` : ''}
        <dl class="kv mk-kv"><dt>고지 질문이 바뀐 종형</dt><dd>${gates.length ? esc(gates.join(', ')) : '없음'}</dd>
          <dt>가입나이가 바뀐 종형</dt><dd>${ages.length ? esc(ages.join(', ')) : '없음'}</dd></dl>
        <p class="note">짝마다 직전 개정 종형과 같은 담보를 견줘 신설, 변경, 종료로 셉니다. 직전 개정 종형은 판매를 마쳐 견준 상품 목록에 이름이 없습니다.</p>
      </div>
      ${revTable()}
    </section>`;
  }
  function newsPanel() {
    const cls = Object.entries(NEWS['분류별'] || {});
    const items = (NEWS['소식'] || []).map((x, i) => {
      const warn = (x['주의표현'] || []).length ? ui.tag(`주의 표현 ${x['주의표현'].join(', ')}`, '화면 문장에 쓰지 않는 말이 보도 요약에 들어 있습니다') : '';
      return `<li class="lrow mk-nw" data-pick="nw${i}">
        <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${x['회사']} ${x['분류']} 소식 근거 보기`)}"></button>
        <div class="selbar mk-nwh"><span class="num mk-d">${esc(x['발표일자'])}</span><b>${esc(x['회사'])}</b>${ui.tag(x['분류'])}</div>
        <p class="mk-tg">${x['인용'] ? ui.tag('인용') : ''}${warn}</p>
        <p class="mk-q">${esc(x['요약'])}</p>
        <p class="mk-src">${esc(x['출처표시'] || x['매체'] || '')}${(x['표준담보ID'] || []).length ? `, 표준담보 ${fmt(x['표준담보ID'].length)}개에 이어짐` : ', 표준담보에 이어지지 않음'}</p>
        <span class="lrow-chev" aria-hidden="true">${ui.IC.chevR}</span>
      </li>`;
    }).join('');
    return `<section class="panel mk-news" aria-labelledby="mk-news-h">
      <div class="panel-h">
        <div><span class="k">${ui.scope('all')} <span class="num mk-k">${esc(NEWS['주차'])}</span></span><h2 id="mk-news-h">시장 소식</h2></div>
        <div class="r">${ui.tag('인용')}</div>
      </div>
      <div class="mk-pad">
        <p class="mk-quote">${esc(NEWS['인용안내'])}</p>
        ${ui.eq({ total: { t: '소식', n: NEWS['건수'] }, parts: cls.map(([a, n]) => ({ t: a, n })), tail: '건' })}
        <div class="mk-cls">${cls.map(([a, n]) => `<span class="mk-clb"><span>${esc(a)}</span>${ui.hbar(n, NEWS['건수'])}<b class="num">${fmt(n)}</b></span>`).join('')}</div>
        <p class="note">표준담보에 이어진 소식 ${fmt(NEWS['연결'])}건.${NEWS['연결'] ? '' : ' 이어진 담보가 없어 대응 문장을 달지 않습니다.'}</p>
      </div>
      <ul class="lrows">${items}</ul>
    </section>`;
  }

  /** 개정과 시장 구역 머리: 달라진 담보 셋(신설, 변경, 종료)과 이번 주 소식 수를 큰 숫자로 */
  function lowerBand() {
    const n = REV['수'];
    return ui.band({ kicker: '직전 개정과 이번 주 시장 소식', title: '개정과 시장', sc: 'all',
      stats: [
        { n: n['신설'], d: n['전체'], l: '신설', bar: [n['신설'], n['전체']] },
        { n: n['변경'], d: n['전체'], l: '변경', bar: [n['변경'], n['전체']] },
        { n: n['종료'], d: n['전체'], l: '종료', bar: [n['종료'], n['전체']] },
        { n: NEWS['건수'], u: '건', l: `시장 소식 ${NEWS['주차']}`, bar: [NEWS['연결'] || 0, NEWS['건수'], 'gold'], title: `표준담보에 이어진 소식 ${NEWS['연결'] || 0}건` },
      ],
      eq: ui.eq({ total: { t: '우체국 직전 개정과 견준 달라진 담보', n: n['전체'] }, parts: [{ t: '신설', n: n['신설'] }, { t: '변경', n: n['변경'] }, { t: '종료', n: n['종료'] }], tail: '건' })
        + `<div class="nadd">시장 소식 ${fmt(NEWS['건수'])}건은 보도를 센 수라 달라진 담보 수와 더하지 않습니다. 막대는 표준담보에 이어진 소식 ${fmt(NEWS['연결'] || 0)}건입니다.</div>`,
    });
  }

  // ---------- 그리기 ----------
  function conclText(c) {
    const map = App.mapOf(c.st.renewal);
    if (c.st.renewal == null) {
      const b = (c.base && c.base['브리핑'] || []).find(x => x['줄'] === '가');
      if (b) return b['문장'];
    }
    const t = tally(map);
    return `${renText(c.st.renewal)} 지도의 고객군 ${fmt(t.total)}칸은 ${LABELS.filter(l => t.lab[l]).map(l => `${l} ${fmt(t.lab[l])}칸`).join(', ')}입니다.`;
  }
  function asideHTML(c) {
    const map = App.mapOf(c.st.renewal);
    const t = tally(map);
    const only = t.lab['우리 간편만 열림'] || 0, both = t.lab['함께 열림'] || 0;
    return `<div class="mk-zone"><div class="mk-zin">
      <div class="mk-zt"><span class="k">${esc(renText(c.st.renewal))}, ${esc(txt.sexText(map['성별']))} 기준</span>
        <b>우리 간편이 열리는 칸</b>
        <span class="sub">우리 간편만 열림 ${fmt(only)}, 함께 열림 ${fmt(both)}</span></div>
      ${ui.ring({ v: only + both, max: t.total, segs: [{ v: only, cls: 'gold' }, { v: both, cls: '' }], lead: true, label: `우리 간편이 열리는 칸 ${only + both}/${t.total}` })}
      ${ui.big(only + both, t.total)}
    </div></div>`;
  }
  function render(body, c) {
    if (c.aside) c.aside.innerHTML = asideHTML(c);
    body.innerHTML = `<p class="concl">${esc(conclText(c))}</p>
      ${mapPanel(c)}
      <div class="mk-lower" id="mk-news">
        ${lowerBand()}
        <div class="mk-two">${revPanel()}${newsPanel()}</div>
      </div>`;
    const slot = body.querySelector('[data-slot="mk-ren"]');
    if (slot) slot.replaceWith(ui.chevSel({ label: '고객군 지도의 갱신 유형', options: REN_OPTS, value: c.st.renewal, w: '64px', onChange: v => App.set({ renewal: v }) }));
    bind(body);
  }
  function grow(body) {
    const g = body.querySelector('#mk-grid');
    if (!g || !App.motionOn()) return;
    g.classList.remove('mk-anim'); void g.offsetWidth; g.classList.add('mk-anim');
    clearTimeout(g._t); g._t = setTimeout(() => g.classList.remove('mk-anim'), 900);
  }
  function enter(body) { grow(body); }

  function bind(body) {
    if (body._b) return;
    body._b = true;
    body.addEventListener('click', e => {
      if (e.target.closest('[data-act="mk-copy-cells"]')) copyCells();
    });
  }
  function copyCells() {
    const c = App.ctx();
    const map = App.mapOf(c.st.renewal);
    const rows = [];
    map['행'].forEach((row, ri) => map['열'].forEach((col, ci) => {
      const cell = cellAt(map, ri, ci);
      const n = cell['분류수'] || {};
      const goT = (cell['관문만수집'] || []).map(x => `${x['이름']}: ${x['안내'] || '관문만 수집(담보 미수집)'}`).join(', ');
      rows.push([rowGroup(row), rowShort(row), colText(col), cell['라벨'], cell['보조'] || '', (cell['닫힌사유'] || []).join(', '),
        ...ORGS.map(o => cell['회사'][o] || ''), vk(cell['대표']), ORGS.filter(o => o !== 'EPOST').map(o => cell['상대대표'] && cell['상대대표'][o] ? `${txt.orgShort(o)} ${vk(cell['상대대표'][o])}` : '').filter(Boolean).join(', '),
        goT, ...CATS.map(k => (n[k] == null ? '' : String(n[k])))]);
    }));
    App.copyRows(['이력 종류', '이력 시점', '나이', '주 라벨', '보조 줄', '닫힌 사유', ...ORGS.map(o => txt.orgShort(o) + ' 상태'), '우리 대표 종형', '상대 대표 종형', '관문만 수집', ...CATS],
      rows, { title: `고객군 지도 칸 목록(${txt.sexText(map['성별'])}, ${renText(c.st.renewal)})` });
  }

  // ---------- 근거 기둥 ----------
  function sec(title, html, lo) { return `<div class="ev-sec${lo ? ' lo' : ''}">${title ? `<h3>${title}</h3>` : ''}${html}</div>`; }
  function pointLi(id) {
    const p = S['포인트'][id]; if (!p) return '';
    const head = p['머리말'] != null ? S['글'][p['머리말']] : '';
    return `<li><span class="tag">${esc(p['세부이름'] || p['분류'])}</span> ${p['원문대조'] ? ui.flagText(p['원문대조글']) : ''}<p>${esc(p['문장'])}</p>${head ? `<p class="note">${esc(head)}</p>` : ''}</li>`;
  }
  function applyPatch(map, ri, ci, c) {
    const row = map['행'][ri], col = map['열'][ci], cell = cellAt(map, ri, ci);
    const st = c.st;
    const age = st.age >= col.lo && st.age <= col.hi ? st.age : col.lo;
    let since = row.since;
    if (row.since === 5 && row['종류'] === '입원' && st.since == null) since = null;
    const patch = { age, since, surg: row['종류'] === '수술만' };
    if (cell && cell['대표'] && BASE_IDS.includes(cell['대표'])) patch.base = cell['대표'];
    return patch;
  }
  function samePatch(patch, st) {
    return Object.keys(patch).every(k => JSON.stringify(patch[k]) === JSON.stringify(st[k]));
  }
  function cellSpec(c, ri, ci, opts = {}) {
    const map = App.mapOf(c.st.renewal);
    const cell = cellAt(map, ri, ci);
    if (!cell) return null;
    const row = map['행'][ri], col = map['열'][ci];
    const sub = notes(cell, true);
    const now = c.seg && c.seg.cell && c.seg.ri === ri && c.seg.ci === ci;
    const gateOnly = cell['관문만수집'] || [];
    const orgRows = ORGS.filter(o => o in cell['회사']).map(o => {
      const s = cell['회사'][o];
      const open = (cell['열린종형'] && cell['열린종형'][o]) || [];
      const why = txt.stateWhy(o, s);
      const go = gateOnly.filter(x => x['기관코드'] === o);
      return `<li><span class="mk-est">${ST_IC[s] || ''}<b>${esc(txt.orgShort(o))}</b> ${esc(s)}</span>
        <p class="note">${open.length ? `열린 종형 ${fmt(open.length)}개: ${esc(open.map(vk).join(', '))}` : '열린 종형 없음'}${why ? `. ${esc(why)}` : ''}</p>
        ${go.map(x => `<p class="note">${ui.tag(x['안내'] || '관문만 수집(담보 미수집)')} ${esc(x['이름'])}: 가입 관문만 수집했고 특약과 급부 담보는 수집하지 않아 담보 비교에는 쓰지 않습니다.</p>`).join('')}</li>`;
    }).join('');
    const n = cell['분류수'] || {};
    const counted = CATS.filter(k => n[k] != null);
    const pts = (cell['관문포인트'] || []).map(pointLi).join('');
    const anyFlag = (cell['관문포인트'] || []).some(id => S['포인트'][id] && S['포인트'][id]['원문대조']) || cell['라벨'] === '우리 간편만 열림';
    const patch = applyPatch(map, ri, ci, c);
    const same = samePatch(patch, c.st);
    const patchT = `${patch.age}세, ${patch.since == null ? '이력 없음' : `${patch.surg ? '수술만' : '입원이나 수술'} ${txt.sinceText(patch.since)}`}${patch.base ? `, 기준 종형 ${vk(patch.base)}` : ''}`;
    const reps = ORGS.filter(o => o !== 'EPOST').map(o => cell['상대대표'] && cell['상대대표'][o] ? `${txt.orgShort(o)} ${vk(cell['상대대표'][o])}` : '').filter(Boolean);
    let body = sec('', `<p><b>${esc(cell['라벨'])}</b>${sub.length ? ` (${esc(sub.join(', '))})` : ''}. ${esc(row['이름'])}, ${esc(colText(col))}의 고객군입니다.${now ? ' 지금 조건이 가리키는 칸입니다.' : ''}</p>${gateOnly.length ? `<p class="note">${gateOnly.map(x => `${esc(x['이름'])}: <b>${esc(x['안내'] || '관문만 수집(담보 미수집)')}</b>`).join(', ')}</p>` : ''}${anyFlag ? `<p>${ui.flagText()}</p>` : ''}`);
    body += sec('회사별 관문과 열린 종형', `<ul class="evl">${orgRows}</ul>`);
    body += sec(`관문 포인트 ${fmt((cell['관문포인트'] || []).length)}건`, pts ? `<ul class="evl">${pts}</ul>` : '<p class="note">이 칸에서 나온 관문 차이가 없습니다.</p>');
    body += sec('대표 종형과 칸의 수', `<dl class="kv"><dt>우리 대표 종형</dt><dd>${esc(vk(cell['대표']) || '없음')}</dd><dt>상대 대표 종형</dt><dd>${esc(reps.join(', ') || '없음')}</dd></dl>
      ${counted.length ? ui.eq({ parts: counted.map(k => ({ t: k, n: n[k] })) }) : ''}
      <p class="note">${counted.length > 1 ? '관문 차이는 이 칸의 관문 포인트 수이고, 나머지는 우리 대표와 상대 대표를 견준 인사이트 수입니다. 검토 대기는 견주지 못한 시사점이라 다른 수와 더하지 않습니다. ' : ''}${CATS.some(k => n[k] == null) ? '빈 수는 견줄 대표 종형이 없어 세지 않은 것입니다. ' : ''}칸의 수는 칸의 대표 종형으로 셌으므로 조건 줄의 기준 종형을 바꿔도 그대로입니다.</p>`);
    body += sec('', `${same ? `<p class="note">지금 조건이 이미 이 고객군입니다.</p>` : `<p class="note">누르면 조건 줄이 ${esc(txt.josa(patchT, '으로'))} 바뀝니다.</p>${ui.btn('이 고객군으로 조건 바꾸기', { main: true, chev: true, attrs: `data-act="mk-apply" data-k="${keyOf(ri, ci)}"` })}`}
      <p class="note">관문 상태는 사업방법서의 고지 질문과 가입나이로 계산했습니다. 칸에 우열을 매기지 않습니다.</p>`, true);
    return { kicker: opts.kicker || '고객군 지도 칸', title: `${row['이름']}, ${colText(col)}`,
      badges: [ui.scope('all'), `<span class="tag">${ui.swatch(cell['라벨'])}${esc(cell['라벨'])}</span>`], body };
  }
  function revSpec(i) {
    const d = REV['담보'][i]; if (!d) return null;
    const isStd = !/^급부:/.test(d['열쇠']);
    const st = isStd ? S['표준담보'][d['열쇠']] : null;
    const stName = st ? `${st['이름']}(${[st['대분류'], st['급부유형']].filter(Boolean).join(', ')})` : d['담보'];
    let body = sec('', `<p><b>${esc(d['담보'])}</b>${jo(d['담보'], '는')} 직전 개정과 견주어 <b>${esc(d['종류'])}</b>입니다. 달라진 항목은 ${esc(d['항목'].join(', '))}입니다.</p>`);
    body += sec('해당 종형', `<ul class="evl">${d['종형ID'].map(v => `<li><b>${esc(vk(v))}</b><br><span class="note">${esc((txt.vinfo(v) || {})['전체이름'] || '')}</span></li>`).join('')}</ul>`);
    body += sec('', `<p class="note">${isStd ? `${esc(txt.josa(`표준담보 ${stName}`, '으로'))} 이어 견줬습니다.` : '표준담보에 이어지지 않은 급부라 급부 이름으로 견줬습니다.'} 공시 문서(상품요약서와 사업방법서)의 개정 전후를 견준 값입니다.</p>`, true);
    return { kicker: '개정 변동', title: d['담보'], badges: [ui.scope('all'), ui.tag(d['종류'])], body };
  }
  function newsSpec(i) {
    const x = (NEWS['소식'] || [])[i]; if (!x) return null;
    const warn = x['주의표현'] || [];
    const sids = (x['표준담보ID'] || []).map(sid => (S['표준담보'][sid] && S['표준담보'][sid]['이름']) || sid);
    let body = sec('', `<p class="mk-quote">${esc(NEWS['인용안내'])}</p><p>${esc(x['요약'])}</p>`);
    body += sec('출처', `<dl class="kv"><dt>회사</dt><dd>${esc(x['회사'])}</dd><dt>분류</dt><dd>${esc(x['분류'])}</dd><dt>발표일</dt><dd class="num">${esc(x['발표일자'])}</dd><dt>매체</dt><dd>${esc(x['출처표시'] || x['매체'] || '')}</dd></dl>
      ${x['출처URL'] ? `<p class="note mk-url">${esc(x['출처URL'])}</p><p class="note">주소는 글자로만 둡니다. 이 화면은 바깥으로 요청하지 않습니다.</p>` : ''}`);
    body += sec('표준담보와 주의 표현', `<p class="note">${sids.length ? `표준담보 ${esc(sids.join(', '))}에 이어졌습니다.` : '표준담보에 이어지지 않아 대응 문장을 달지 않습니다.'}</p>${warn.length ? `<p class="note">보도 요약에 "${esc(warn.join('", "'))}" 같은 말이 들어 있습니다. 화면 문장에는 쓰지 않는 말이라 인용한 그대로 두고 표지만 붙였습니다.</p>` : ''}`, true);
    return { kicker: `시장 소식 ${NEWS['주차']}`, title: `${x['회사']} ${x['분류']}`, badges: [ui.scope('all'), ui.tag('인용')], body };
  }
  function pick(key, c) {
    const m = parseKey(key);
    if (m) return cellSpec(c, m.ri, m.ci);
    if (/^rv\d+$/.test(key)) return revSpec(+key.slice(2));
    if (/^nw\d+$/.test(key)) return newsSpec(+key.slice(2));
    return null;
  }
  function evidence(c) {
    if (c.seg && c.seg.cell) {
      const spec = cellSpec(c, c.seg.ri, c.seg.ci, { kicker: '지금 조건의 고객군' });
      spec.body += sec('지도 읽는 법', `<dl class="legend">${LABELS.map(l => `<dt>${ui.swatch(l)}</dt><dd>${esc(l)}</dd>`).join('')}<dt>${ui.flagText('원문 확인')}</dt><dd>${esc(ui.FLAG_TEXT)}</dd></dl><p class="note">칸을 누르면 그 고객군의 요약이 여기에 뜹니다. 조건 줄은 요약 안의 단추를 눌러야 바뀝니다.</p>`, true);
      return spec;
    }
    return { kicker: '지금 조건의 고객군', title: '지도에 칸이 없습니다', badges: [ui.scope('all')],
      body: sec('', `<p>${esc((c.seg && c.seg.reason) || '지금 조건의 칸을 찾지 못했습니다.')}</p>${c.seg && c.seg.sexNote ? `<p class="note">${esc(c.seg.sexNote)}</p>` : ''}`) };
  }
  function focus(key, body) {
    const el = body.querySelector(key === 'news' ? '#mk-news' : '#mk-map');
    if (!el) return;
    if (App.mode() === 'sheet') App.reveal(el);
    else el.scrollIntoView({ block: 'start', behavior: App.motionOn() ? 'smooth' : 'auto' });
  }

  // 근거 기둥 안의 "이 고객군으로 조건 바꾸기"(기둥은 탭 밖에 있어 문서에서 받는다)
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-act="mk-apply"]');
    if (!b) return;
    const m = parseKey(b.dataset.k || ''); if (!m) return;
    const c = App.ctx();
    const map = App.mapOf(c.st.renewal);
    const patch = applyPatch(map, m.ri, m.ci, c);
    App.set(patch);
    App.toast(`조건을 바꿨습니다: ${App.condSummary()}`);
  });

  return { id: 'market', kicker: '넓게 본다', render, pick, evidence, focus, enter };
})());
