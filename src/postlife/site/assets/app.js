/* 화면 그리기. 자료 가공은 빌드할 때 Python이 끝냈고, 여기서는 고른 조건에 맞는 값을 찾아 보여 준다.
   계산은 화면 4의 특약 조합뿐이고 그 규칙은 calc.js에 있다.
   자료가 늘어도 화면이 길어지지 않도록, 처음에는 요약을 보여 주고 긴 목록은 접거나 쪽을 나눠 거르기·찾기와 함께 둔다. */
(function () {
  'use strict';

  const C = PostlifeCalc;
  const D = C.unpack(JSON.parse(document.getElementById('data').textContent));   // 줄여 적은 자료를 되살린다(pack.py)
  const money = C.money;

  const TABS = [
    {id: 's1', n: '1', label: '이번 주 달라진 점'},
    {id: 's2', n: '2', label: '가입 적격·간편심사 관문'},
    {id: 's3', n: '3', label: '담보 비교표'},
    {id: 's4', n: '4', label: '특약 조합별 지급액'},
    {id: 's5', n: '5', label: '개정 전후 비교'},
    {id: 's6', n: '6', label: 'AI 작업 내역'}
  ];
  const COND_TABS = {s2: true, s3: true, s4: true};
  const LIST_SIZE = 20;      // 접어 둔 목록과 작업 기록의 한 쪽
  const RIDER_SIZE = 25;     // 화면 4 특약 목록의 한 쪽
  const ALL = '*';

  const state = {
    tab: 's1',
    age: D.defaults.age,
    sex: D.defaults.sex,
    open: {},                // 접어 둔 구획 가운데 열어 둔 것. 화면을 다시 그려도 닫히지 않게 기억한다
    s2: {ended: false, org: ''},
    s3: {base: D.s3.defaultBase, cols: null, showEmpty: false, major: null, q: '', diff: '',
      wait: {org: '', rec: '', q: '', page: 0}},
    s4: {vid: D.s4.variants[0] || null, want: {}, list: {q: '', picked: false, page: 0}, others: {q: '', page: 0}},
    s5: {pair: 0},
    s6: {log: {tab: '', step: '', result: '', q: '', page: 0}, review: {status: '', tab: '', q: '', page: 0}}
  };

  /* ---------- 공통 도구 ---------- */
  function h(tag, attrs) {
    const el = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        const value = attrs[key];
        if (value === null || value === undefined || value === false) return;
        if (key === 'class') el.className = value;
        else if (key === 'text') el.textContent = value;
        else if (key.slice(0, 2) === 'on') el.addEventListener(key.slice(2), value);
        else if (value === true) el.setAttribute(key, '');
        else el.setAttribute(key, value);
      });
    }
    for (let i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, child) {
    if (child === null || child === undefined || child === false) return;
    if (Array.isArray(child)) child.forEach(function (c) { add(el, c); });
    else if (child instanceof Node) el.appendChild(child);
    else el.appendChild(document.createTextNode(String(child)));
  }
  function tag(cls, icon, text) {
    return h('span', {class: 'tag ' + cls}, icon ? h('span', {class: 'ic', 'aria-hidden': 'true', text: icon}) : null, text);
  }
  function pendTag(text) { return tag('p', '!', text || '검토 대기'); }
  /* 표를 가로로 밀어 볼 수 있는 상자에 넣는다. 좁은 화면에서 글자가 세로로 찌그러지지 않도록 표의 최소 폭을 정한다. */
  function scrollBox(table, label, minWidth) {
    if (minWidth !== 0 && !table.style.minWidth) table.style.minWidth = (minWidth || 600) + 'px';   // 0이면 CSS가 정한다
    return [h('p', {class: 'scroll-hint', text: '표는 옆으로 밀어 볼 수 있습니다.'}),
      h('div', {class: 'scroll', tabindex: '0', role: 'region', 'aria-label': label}, table)];
  }
  function block(title) {
    const el = h('section', {class: 'block'}, h('h3', {text: title}));
    for (let i = 1; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function table(cls, head, rows) {
    return h('table', {class: cls || null},
      h('thead', null, h('tr', null, head.map(function (c) {
        return typeof c === 'string' ? h('th', {scope: 'col', text: c}) : c;
      }))),
      h('tbody', null, rows));
  }
  function rcol(text) { return h('th', {scope: 'col', class: 'r', text: text}); }
  function tile(k, v, d) {
    return h('div', {class: 'tile'}, h('div', {class: 'k', text: k}), h('div', {class: 'v num', text: v}), d ? h('div', {class: 'd', text: d}) : null);
  }
  function uniq(list) { return list.filter(function (x, i) { return list.indexOf(x) === i; }); }
  /* 찾기에 쓰는 글자 맞춤: 띄어쓰기와 대소문자를 가리지 않는다. */
  function norm(text) { return String(text === null || text === undefined ? '' : text).replace(/\s+/g, '').toLowerCase(); }

  /* 여러 개 가운데 하나 고르기. 이름이 긴 종형도 잘리지 않도록 목록 상자 대신 줄바꿈되는 단추로 둔다. */
  function choice(key, label, options, value, onPick) {
    return h('div', {class: 'choice', role: 'group', 'aria-label': label},
      h('span', {class: 'choice-label', text: label}),
      h('div', {class: 'choices'}, options.map(function (o) {
        return h('button', {type: 'button', class: 'opt', 'aria-pressed': String(o.value === value), 'data-key': key + '-' + o.value,
          onclick: function () { onPick(o.value); }}, o.label);
      })));
  }
  /* 종형 고르기: 회사 → 상품 → 종형 순으로 좁힌다. 종형이 수십 개로 늘어도 단추가 한 줄씩만 는다. */
  function variantPicker(key, word, vids, value, onPick) {
    const cur = D.variants[value];
    const group = function (v) { return D.variants[v].rev || D.variants[v].product; };
    const orgs = uniq(vids.map(function (v) { return D.variants[v].org; }));
    const inOrg = vids.filter(function (v) { return D.variants[v].org === cur.org; });
    const revs = uniq(inOrg.map(group));
    const inRev = inOrg.filter(function (v) { return group(v) === group(value); });
    const first = function (list, test) { return list.filter(test)[0]; };
    const out = [];
    if (orgs.length > 1) {
      out.push(choice(key + '-org', word + '회사', orgs.map(function (o) {
        const mine = vids.filter(function (v) { return D.variants[v].org === o; });
        return {value: o, label: D.variants[mine[0]].orgName + ' (종형 ' + mine.length + '개)'};
      }), cur.org, function (o) { onPick(first(vids, function (v) { return D.variants[v].org === o; })); }));
    }
    if (revs.length > 1) {
      out.push(choice(key + '-rev', word + '상품', revs.map(function (r) {
        return {value: r, label: D.variants[first(inOrg, function (v) { return group(v) === r; })].product};
      }), group(value), function (r) { onPick(first(inOrg, function (v) { return group(v) === r; })); }));
    }
    if (inRev.length > 1) {
      out.push(choice(key, word + '종형', inRev.map(function (v) { return {value: v, label: D.variants[v].kind || vLabel(v)}; }), value, onPick));
    }
    out.push(h('p', {class: 'picked'}, '고른 ' + word + '종형: ', h('strong', {text: vLabel(value)}), h('span', {class: 'sub', text: vSub(value)})));
    return out;
  }

  /* 접어 두는 구획. 안쪽은 처음 펼칠 때 만든다. */
  function fold(key, summary, build) {
    const inner = h('div', {class: 'inner'});
    let built = false;
    const fill = function () { if (!built) { built = true; add(inner, build()); } };
    const el = h('details', {class: 'fold', open: !!state.open[key]},
      h('summary', {'data-key': 'fold-' + key, onclick: function () { if (!el.open) fill(); }}, summary), inner);   // 펼쳐지기 직전에 채운다
    el.addEventListener('toggle', function () { state.open[key] = el.open; if (el.open) fill(); });
    if (state.open[key]) fill();
    return el;
  }
  /* 쪽 나누기 줄. 한 쪽에 다 들어가면 건수만 적는다. */
  function pager(key, st, total, size, unit, turn) {
    const pages = Math.max(1, Math.ceil(total / size));
    const count = C.comma(total) + unit;
    if (pages <= 1) return h('div', {class: 'pager'}, h('span', {class: 'num', text: count}));
    const from = st.page * size + 1, to = Math.min(total, (st.page + 1) * size);
    return h('div', {class: 'pager'},
      h('button', {type: 'button', class: 'btn', disabled: st.page <= 0, 'data-key': key + '-prev', text: '이전',
        onclick: function () { st.page--; turn(key + '-prev'); }}),
      h('span', {class: 'num', text: (st.page + 1) + ' / ' + pages + '쪽 · ' + count + ' 가운데 ' + from + '~' + to}),
      h('button', {type: 'button', class: 'btn', disabled: st.page >= pages - 1, 'data-key': key + '-next', text: '다음',
        onclick: function () { st.page++; turn(key + '-next'); }}));
  }
  /* 거르기·찾기가 붙은 긴 목록. 한 쪽씩만 그린다.
     찾는 글자를 칠 때는 입력 상자를 그대로 두고 목록만 다시 그린다(한글을 치는 도중에 글자가 끊기지 않도록).
     opt: key, st({page, …}), size, unit, controls(redraw) → 거르기 요소들, items() → 걸러 낸 전체, draw(한 쪽, 전체) → 요소, empty */
  function listPanel(opt) {
    const st = opt.st;
    const body = h('div', {class: 'list-body'});
    const box = h('div', {class: 'list'});
    function redraw(keepPage, focusKey) {
      if (!keepPage) st.page = 0;
      const all = opt.items();
      const pages = Math.max(1, Math.ceil(all.length / opt.size));
      if (st.page >= pages) st.page = pages - 1;
      const slice = all.slice(st.page * opt.size, (st.page + 1) * opt.size);
      const turn = function (key) {
        redraw(true, key);
        if (box.getBoundingClientRect().top < 0) box.scrollIntoView();      // 아래쪽 단추로 넘겼으면 목록 머리로 돌아간다
      };
      body.textContent = '';
      add(body, [pager(opt.key + '-top', st, all.length, opt.size, opt.unit, turn),
        all.length ? opt.draw(slice, all) : h('p', {class: 'empty', text: opt.empty || '조건에 맞는 항목이 없습니다.'}),
        pages > 1 ? pager(opt.key + '-bottom', st, all.length, opt.size, opt.unit, turn) : null]);
      if (focusKey) {
        const el = body.querySelector('[data-key="' + focusKey + '"]');
        if (el && !el.disabled) el.focus();
      }
    }
    const controls = opt.controls ? opt.controls(function () { redraw(false); }) : null;
    add(box, [controls ? h('div', {class: 'controls'}, controls) : null, body]);
    redraw(true);
    return box;
  }
  function searchField(key, label, st, redraw) {
    const input = h('input', {type: 'search', class: 'q', 'data-key': key, placeholder: label, 'aria-label': label, value: st.q || '',
      oninput: function () { st.q = input.value; redraw(); }});
    return h('label', {class: 'field'}, h('span', {text: '찾기'}), input);
  }
  /* 목록 상자로 거르기. options: [{value, label}] (맨 앞에 "전체"가 붙는다) */
  function pickField(key, label, options, st, prop, redraw) {
    return h('label', {class: 'field'}, h('span', {text: label}),
      h('select', {'data-key': key, onchange: function (e) { st[prop] = e.target.value; redraw(); }},
        h('option', {value: '', text: '전체'}),
        options.map(function (o) { return h('option', {value: o.value, selected: st[prop] === o.value, text: o.label}); })));
  }

  function condIndex() {
    if (state.age === null) return 0;
    for (let i = 1; i < D.conds.length; i++) {
      const c = D.conds[i];
      if (c.lo <= state.age && state.age <= c.hi && c.sex === state.sex) return i;
    }
    return 0;
  }
  function sexText(sex) { return sex === 'F' ? '여성' : '남성'; }
  function condText() {
    return state.age === null ? '나이 조건 없음' : state.age + '세 ' + sexText(state.sex);
  }
  function vLabel(vid) {
    const v = D.variants[vid];
    return v.kind ? v.product + ' ' + v.kind : v.product;
  }
  function vSub(vid) {
    const v = D.variants[vid];
    const parts = [v.uw + (v.uw === '간편심사' && v.simple ? ' ' + v.simple : '')];
    parts.push(v.renew === '갱신' ? (v.renewYears ? v.renewYears + '년 갱신' : '갱신형') : v.renew);
    if (v.end) parts.push('판매 종료 ' + v.end);
    return parts.filter(Boolean).join(' · ');
  }
  function vHead(vid) {
    const v = D.variants[vid];
    return v.kind ? [h('span', {class: 'sub', text: v.product}), h('br'), v.kind] : v.product;
  }
  function ageRange(lo, hi) { return lo === hi ? lo + '세' : lo + '~' + hi + '세'; }
  function months(m) { return m % 12 === 0 ? (m / 12) + '년' : m + '개월'; }
  function pct(rate) { return (Math.round(rate * 1000) / 10) + '%'; }
  function redText(red) {
    if (!red || !red.length) return '감액 없음';
    return red.map(function (s) { return months(s[0]) + ' 미만 ' + pct(s[1]); }).join(', ');
  }
  function waitText(days) { return days ? '면책 ' + C.comma(days) + '일' : '면책 없음'; }
  function renewText(rider) {
    if (!rider.renew) return '비갱신';
    return rider.renewYears ? rider.renewYears + '년 갱신' : '갱신형';
  }
  function prob(p) { return p === null || p === undefined ? '자료 없음' : (Math.round(p * 1000) / 1000).toFixed(3); }
  function orNone(value) { return value === null || value === undefined || value === '' ? '자료 없음' : value; }
  function when(text) {
    if (!text) return '자료 없음';
    const s = String(text);
    return s.slice(0, 10) + ' ' + s.slice(11, 16) + (s.slice(-6) === '+09:00' ? '' : ' (' + s.slice(19) + ')');
  }
  function segsText(segs) {
    if (!segs || !segs.length) return '자료 없음';
    return segs.map(function (s) { return ageRange(s.lo, s.hi) + ' 최대 ' + money(s.max); }).join(', ');
  }

  /* 가입 한도 자료가 없는 종형을 회사별로 묶는다. 공시 문서에 특약 가입 한도가 없는 회사는
     "최대 가입 시 지급액"을 계산할 수 없어, 화면마다 그 사실을 한 줄로 알린다. */
  function gapGroups(vids) {
    const out = [];
    vids.forEach(function (vid) {
      const v = D.variants[vid];
      if (!v.gap || !v.gap.noMax) return;
      let g = out.filter(function (x) { return x.org === v.org; })[0];
      if (!g) { g = {org: v.org, name: v.orgName, n: 0, riders: 0, noMax: 0}; out.push(g); }
      g.n++; g.riders += v.gap.riders; g.noMax += v.gap.noMax;
    });
    return out;
  }
  function gapNames(groups) {
    return groups.map(function (g) {
      return g.name + ' 종형 ' + g.n + '개' + (g.noMax < g.riders ? '(특약 ' + C.comma(g.riders) + '개 가운데 ' + C.comma(g.noMax) + '개)' : '');
    }).join(', ');
  }

  /* ---------- 틀 ---------- */
  function renderFacts() {
    const s1 = D.s1;
    const others = s1.orgs.filter(function (o) { return o.code !== s1.homeOrg; });
    let scope;
    if (!others.length) {
      scope = '비교 대상: 현재 ' + s1.homeName + ' 상품만 들어 있음(종형 ' + s1.counts.variants + '개). 민영 비교사 자료는 아직 없음.';
    } else {
      scope = '비교 대상: ' + s1.orgs.map(function (o) { return o.name + ' 종형 ' + o.variants + '개'; }).join(', ') + '.';
    }
    document.getElementById('facts').textContent = '자료 기준 시각 ' + when(D.meta.snapshotAt) + ' (한국 시간) · ' + scope;
  }

  function renderTabs() {
    const nav = document.getElementById('tabs');
    nav.textContent = '';
    nav.setAttribute('role', 'tablist');
    TABS.forEach(function (t) {
      nav.appendChild(h('button', {
        type: 'button', class: 'tab', role: 'tab', id: 'tab-' + t.id, 'aria-selected': String(state.tab === t.id),
        onclick: function () { go(t.id); }
      }, h('span', {class: 'n', text: t.n}), t.label));
    });
  }

  function renderCondBar() {
    const bar = document.getElementById('condbar');
    bar.hidden = !COND_TABS[state.tab];
    bar.textContent = '';
    const input = h('input', {
      type: 'number', id: 'age', min: '0', max: String(D.defaults.maxAge), step: '1', inputmode: 'numeric',
      placeholder: '없음', value: state.age === null ? '' : String(state.age),
      oninput: function () {
        const raw = input.value.trim();
        const n = raw === '' ? null : Math.round(Number(raw));
        state.age = n === null || isNaN(n) ? null : Math.max(0, Math.min(D.defaults.maxAge, n));
        renderMain();
      }
    });
    const sexes = h('span', {class: 'seg', role: 'group', 'aria-label': '성별'}, ['M', 'F'].map(function (s) {
      return h('button', {type: 'button', 'aria-pressed': String(state.sex === s), text: s === 'M' ? '남' : '여',
        onclick: function () { state.sex = s; renderCondBar(); renderMain(); }});
    }));
    add(bar, [
      h('label', {class: 'field'}, h('span', {text: '나이'}), input, h('span', {text: '세'})),
      h('span', {class: 'field'}, h('span', {text: '성별'}), sexes),
      h('span', {class: 'hint', text: '나이를 비우면 나이 조건 없이 특약의 최대 가입금액으로 봅니다.'})
    ]);
  }

  const screens = {};
  function renderMain() {
    const main = document.getElementById('main');
    const focus = document.activeElement && document.activeElement.getAttribute('data-key');
    main.textContent = '';
    main.appendChild(screens[state.tab]());
    if (focus) {
      const el = main.querySelector('[data-key="' + focus + '"]');
      if (el) el.focus();
    }
  }
  function go(tab) {
    state.tab = tab;
    if (location.hash !== '#' + tab) {
      try { history.replaceState(null, '', '#' + tab); } catch (e) { location.hash = tab; }
    }
    renderTabs();
    renderCondBar();
    renderMain();
  }
  function screen(title, lead) {
    const el = h('section', {class: 'screen', id: 'screen-' + state.tab, role: 'tabpanel', 'aria-labelledby': 'tab-' + state.tab},
      h('h2', {text: title}), lead ? h('p', {class: 'lead'}, lead) : null);
    for (let i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }

  /* ---------- 근거 창 ---------- */
  const dialog = document.getElementById('detail');
  function openDetail(title, body) {
    document.getElementById('detail-title').textContent = title;
    const box = document.getElementById('detail-body');
    box.textContent = '';
    add(box, body);
    if (typeof dialog.showModal === 'function') {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute('open', '');
    }
    box.scrollTop = 0;
  }
  function closeDetail() {
    if (typeof dialog.close === 'function' && dialog.open) dialog.close();
    else dialog.removeAttribute('open');
  }
  document.getElementById('detail-close').addEventListener('click', closeDetail);
  dialog.addEventListener('click', function (e) { if (e.target === dialog) closeDetail(); });

  function kv(pairs) {
    const dl = h('dl', {class: 'kv'});
    pairs.forEach(function (p) {
      if (!p) return;
      dl.appendChild(h('dt', {text: p[0]}));
      dl.appendChild(h('dd', null, p[1]));
    });
    return dl;
  }
  function mapText(b) {
    const std = b.std ? D.std[b.std] : null;
    if (b.state === '대기') {
      return '검토 대기' + (b.rec && D.std[b.rec] ? ' (추천: ' + D.std[b.rec].name + ')' : ' (추천 없음)') + ' · 확률 ' + prob(b.prob);
    }
    return b.state + (std ? ' → ' + std.name : '') + ' · 확률 ' + prob(b.prob);
  }
  /* 급부 한 줄의 근거. opt.amount는 이 화면에서 쓴 가입금액, opt.val은 그때의 지급액.
     opt.noCap은 가입 한도 자료가 없어 최대 가입 기준 금액을 내지 못한 줄 */
  function evidence(bid, opt) {
    const b = D.benefits[bid];
    const rider = D.riders[b.tid];
    const v = D.variants[rider.vid];
    const marks = [];
    if (opt.rep) marks.push(tag('base', '', '대표'));
    marks.push(tag('plain', '', b.role));
    if (b.state === '대기') marks.push(pendTag('매핑 검토 대기'));
    if (b.pend.length) marks.push(pendTag('검토 대기'));
    if (opt.noCap) marks.push(tag('plain', '', '가입 한도 자료 없음'));
    const link = v.url ? h('a', {href: v.url, target: '_blank', rel: 'noopener noreferrer', text: v.url}) : '자료 없음';
    const amountText = opt.unavailable ? '이 나이에는 가입할 수 없음' : opt.noCap ? '공시 문서에 가입 한도가 없음' : money(opt.amount);
    const valText = opt.unavailable ? '해당 없음' : opt.noCap ? '계산할 수 없음(아래 기준 가입금액 기준 지급액을 봅니다)' : money(opt.val);
    return h('div', {class: 'ev'},
      h('h4', null, b.name, marks),
      kv([
        ['종형', vLabel(rider.vid)],
        ['원시특약명', rider.name],
        ['원시급부명', b.name],
        opt.amount !== undefined ? [opt.amountLabel || '가입금액', amountText] : null,
        opt.val !== undefined ? [opt.valLabel || '지급액', valText] : null,
        ['기준 가입금액 기준', '가입금액 ' + money(b.base) + '에 ' + money(b.pay)],
        opt.unit && opt.val !== null && opt.val !== undefined && !opt.unavailable && !opt.noCap
          ? ['기준 단위 대비', '기준 단위 ' + money(opt.unit) + '의 ' + (Math.round(opt.val / opt.unit * 100) / 100) + '배'] : null,
        ['면책기간', b.wait ? '계약일부터 ' + C.comma(b.wait) + '일' : '없음'],
        ['감액', b.red.length ? '계약일부터 ' + redText(b.red) + ' 지급' : '없음'],
        b.exc ? ['감액 예외', b.exc] : null,
        ['지급 한도', orNone(b.limit)],
        ['갱신', renewText(rider)],
        ['근거 문서', orNone(b.doc) + (b.page !== null && b.page !== undefined ? ' ' + b.page + '쪽' : ' (쪽수 자료 없음)') + ' · ' + orNone(v.rev)],
        ['공시 목록 주소', link],
        ['표준담보 매핑', mapText(b)],
        ['검토 대기 여부', b.pend.length ? '사람 검토 대기: ' + b.pend.join(', ') : '없음']
      ]));
  }

  /* ---------- 화면 1 ---------- */
  screens.s1 = function () {
    const s = D.s1, c = s.counts, t = s.trends;
    const list = function (pairs) { return pairs.map(function (p) { return p[0] + ' ' + p[1] + '건'; }).join(', '); };
    const trendLines = t.shown
      ? [h('p', null, '시장 소식 ' + t.shown + '건 수집됨' + (t.weeks.length ? ' (수집주차 ' + t.weeks.join(', ') + ', 발표일 ' + t.from + ' ~ ' + t.to + ')' : '') + '.'),
        h('ul', {class: 'plain'},
          h('li', {text: '분류별: ' + list(t.byKind)}),
          h('li', {text: '기관별: ' + list(t.byOrg)}),
          t.total > t.shown ? h('li', {text: '선별 확률이 통과 기준에 못 미쳐 화면에 내지 않는 소식 ' + (t.total - t.shown) + '건'}) : null)]
      : [h('p', {class: 'empty', text: '수집된 시장 소식이 없습니다.'})];
    const missing = [];
    if (s.orgs.length <= 1) missing.push('민영 비교사 상품 자료가 없습니다. 지금 비교는 ' + s.homeName + ' 상품끼리만 됩니다.');
    s.limitGaps.forEach(function (g) {
      const what = [];
      if (g.noMax) what.push('특약 가입 한도(' + (g.noMax < g.riders ? '특약 ' + C.comma(g.riders) + '개 가운데 ' + C.comma(g.noMax) + '개' : '특약 ' + C.comma(g.riders) + '개 모두') + ')');
      if (g.noAge) what.push('주계약 가입 나이');
      missing.push(g.name + ' 종형 ' + g.variants + '개는 공시 문서에 ' + what.join('와 ') + ' 자료가 없습니다.'
        + (g.noMax ? ' 이 종형은 "최대로 가입했을 때 지급액"을 계산하지 않고, 기준 가입금액에 대한 지급액과 면책·감액 조건만 보여 줍니다.' : ''));
    });
    if (!c.premiums) missing.push('보험료 자료가 없습니다(2단계). 보험료와 가격 비교는 화면에 내지 않습니다.');
    if (!c.diseaseCodes) missing.push('급부별 질병코드 자료가 없습니다. 보장 범위(질병코드 폭) 비교는 아직 할 수 없습니다.');
    return screen('이번 주 달라진 점', '주간 요약은 준비 중입니다. 지금은 모아 둔 자료의 현황만 적습니다.',
      block('시장 소식', trendLines, h('p', {class: 'note', text: '소식 목록과 주간 요약 문장은 준비 중입니다.'})),
      block('들어 있는 자료',
        h('div', {class: 'tiles'},
          tile('종형', c.variants + '개', '판매 중 ' + c.onSale + '개 · 개정판 ' + c.revisions + '개'),
          tile('특약(주계약 포함)', C.comma(c.riders) + '개'),
          tile('급부', C.comma(c.benefits) + '줄', '표준담보 확정 ' + C.comma(c.mapped) + ' · 매핑 검토 대기 ' + C.comma(c.waiting) + ' · 대상외 ' + C.comma(c.excluded)),
          tile('값 검토 대기 급부', C.comma(c.pendingBenefits) + '줄', '가입조건은 ' + C.comma(c.pendingConditions) + '행이 검토 대기'),
          tile('AI 작업 기록', C.comma(c.logs) + '건')),
        h('p', {class: 'note', text: '회사별 종형 수: ' + s.orgs.map(function (o) { return o.name + ' ' + o.variants + '개'; }).join(', ') + '.'})),
      missing.length ? block('아직 없는 자료', h('ul', {class: 'plain'}, missing.map(function (m) { return h('li', {text: m}); }))) : null);
  };

  /* ---------- 화면 2 ---------- */
  const RAMP = ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281'];
  function rampFor(amounts) {
    const uniq = amounts.filter(function (a, i) { return a !== null && amounts.indexOf(a) === i; }).sort(function (a, b) { return a - b; });
    const map = {};
    uniq.forEach(function (a, i) {
      if (uniq.length === 1) map[a] = RAMP[2];
      else if (uniq.length === 2) map[a] = [RAMP[0], RAMP[2]][i];
      else map[a] = RAMP[Math.min(RAMP.length - 1, Math.round(i / (uniq.length - 1) * (RAMP.length - 1)))];
    });
    return function (a) { return a === null || a === undefined ? '#a9a8a2' : map[a]; };
  }
  function gateCells(v) {
    const g = v.gate;
    if (v.uw !== '간편심사') {
      return [h('td', {colspan: '3', text: D.texts.gateGeneral || '일반심사'})];
    }
    const hosp = g.hospYears === null || g.hospYears === undefined ? '자료 없음'
      : g.hospYears + '년 이내 입원' + (g.surgery === true ? '·수술' : g.surgery === false ? ' (수술은 묻지 않음)' : ' (수술 포함 여부 자료 없음)');
    const major = g.majorYears === null || g.majorYears === undefined ? '자료 없음'
      : g.majorYears + '년 이내 중대질병' + (g.majorCount === null || g.majorCount === undefined ? ' (질병 수 자료 없음)' : ' ' + g.majorCount + '개');
    return [
      h('td', {text: g.months === null || g.months === undefined ? '자료 없음' : '최근 ' + g.months + '개월 이내 소견'}),
      h('td', {text: hosp}),
      h('td', {text: major})
    ];
  }
  screens.s2 = function () {
    const S = D.s2, k = condIndex(), st = state.s2;
    const onSale = S.variants.filter(function (v) { return st.ended || !D.variants[v].end; });
    const endedCount = S.variants.filter(function (v) { return D.variants[v].end; }).length;
    const orgs = uniq(onSale.map(function (v) { return D.variants[v].org; }));
    if (st.org && orgs.indexOf(st.org) < 0) st.org = '';
    const vids = onSale.filter(function (v) { return !st.org || D.variants[v].org === st.org; });
    /* 주계약 가입 나이 자료가 아예 없는 종형은 막대를 그리지 않고, 가입 가능 여부도 세지 않는다 */
    const noData = function (v) { return S.byVariant[v].noCond; };
    const known = vids.filter(function (v) { return !noData(v); });
    const color = rampFor([].concat.apply([], known.map(function (v) {
      return S.byVariant[v].seg[state.sex].map(function (s) { return s.max; });
    })));
    const axisMax = S.axisMax;
    const pos = function (age) { return Math.max(0, Math.min(100, age / axisMax * 100)); };
    const ticks = [];
    for (let a = 0; a <= axisMax; a += 20) ticks.push(a);

    const okCount = state.age === null ? null : known.filter(function (v) { return S.byVariant[v].ok[k]; }).length;
    const unknownNote = vids.length > known.length ? ' 가입 나이 자료가 없는 종형 ' + (vids.length - known.length) + '개는 따지지 못합니다.' : '';
    const lead = state.age === null
      ? '나이를 넣으면 종형마다 주계약 가입 가능 여부와 가입할 수 있는 특약 수가 나옵니다.' + unknownNote
      : condText() + ': 가입 나이 자료가 있는 종형 ' + known.length + '개 가운데 ' + okCount + '개의 주계약에 가입할 수 있는 나이입니다.' + unknownNote;

    const row = function (vid) {
      const x = S.byVariant[vid], segs = x.seg[state.sex];
      const head = [h('span', {class: 'vname', text: vLabel(vid)}), h('span', {class: 'sub', text: vSub(vid)})];
      if (noData(vid)) {
        head.push(tag('plain', '', '가입 나이·한도 자료 없음'));
        const riders = x.riders.length;
        return h('div', {class: 'vrow'}, h('div', {class: 'vhead'}, head),
          h('p', {class: 'note', text: '공시 문서에 주계약 가입 나이와 가입 한도가 없어 나이별 적격을 따지지 못합니다.'
            + (riders ? ' 특약 ' + C.comma(riders) + '개도 가입 나이 자료가 없습니다.' : '')}));
      }
      if (state.age !== null) {
        head.push(x.ok[k] ? tag('b', '✓', '가입 가능 · 최대 ' + money(x.lim[k])) : tag('w', '✕', '가입할 수 없는 나이'));
      }
      const bar = h('div', {class: 'agebar', role: 'img',
        'aria-label': vLabel(vid) + ' 주계약 가입 나이: ' + segsText(segs)});
      segs.forEach(function (s) {
        bar.appendChild(h('div', {class: 'segm', title: ageRange(s.lo, s.hi) + ' 최대 ' + money(s.max),
          style: 'left:' + pos(s.lo) + '%;width:calc(' + (pos(s.hi + 1) - pos(s.lo)) + '% - 2px);background:' + color(s.max)}));
      });
      if (state.age !== null) bar.appendChild(h('div', {class: 'mark', style: 'left:' + pos(state.age) + '%'}));
      const axis = h('div', {class: 'axis', 'aria-hidden': 'true'}, ticks.map(function (a) {
        return h('span', {style: 'left:' + pos(a) + '%', text: a + '세'});
      }));
      const list = segs.length
        ? h('ul', {class: 'seglist'}, segs.map(function (s) {
          const here = state.age !== null && s.lo <= state.age && state.age <= s.hi;
          return h('li', {class: here ? 'here' : null},
            h('span', {class: 'sw', style: 'background:' + color(s.max)}),
            ageRange(s.lo, s.hi) + ' 최대 ' + money(s.max), s.pend ? pendTag() : null);
        }))
        : h('p', {class: 'empty', text: '이 성별로 가입할 수 있는 나이 구간이 없습니다.'});

      let riderLine = null;
      if (state.age !== null && x.riders.length) {
        const bad = x.riders.filter(function (r) { return !r.ok[k]; });
        const unknown = x.riders.filter(function (r) { return r.noCond; }).length;
        const text = '특약 ' + x.riders.length + '개 가운데 ' + (x.riders.length - bad.length) + '개에 가입할 수 있습니다.'
          + (unknown ? ' (가입나이 자료가 없는 특약 ' + unknown + '개는 가능한 것으로 셈)' : '');
        riderLine = [h('p', {class: 'note', text: text})];
        if (bad.length) {
          riderLine.push(fold('s2-bad-' + vid, '가입할 수 없는 특약 ' + bad.length + '개', function () {
            return h('ul', {class: 'plain'}, bad.map(function (r) {
              const rs = r.seg[state.sex];
              const reason = !x.ok[k] ? '주계약에 가입할 수 없는 나이'
                : rs.length ? '가입 나이 ' + rs.map(function (s) { return ageRange(s.lo, s.hi); }).join(', ')
                  : '이 성별의 가입 나이 자료 없음';
              return h('li', {text: D.riders[r.tid].name + ' — ' + reason});
            }));
          }));
        }
      }
      const periods = x.periods.length > 1 ? fold('s2-per-' + vid, '보험기간·납입기간별 가입 나이 (' + x.periods.length + '가지)', function () {
        return scrollBox(table(null, ['보험기간', '납입기간', '성별', '가입 나이와 최대 가입금액'], x.periods.map(function (p) {
          return h('tr', null, h('td', {text: p.term}), h('td', {text: p.pay}),
            h('td', {text: p.sex ? sexText(p.sex) : '공통'}),
            h('td', null, p.ranges.map(function (r, i) {
              return [i ? ', ' : '', ageRange(r.lo, r.hi) + ' ' + money(r.max), r.pend.length ? [' ', pendTag()] : null];
            })));
        })), '보험기간과 납입기간별 가입 나이', 520);
      }) : null;
      return h('div', {class: 'vrow'}, h('div', {class: 'vhead'}, head), bar, axis, list, riderLine, periods);
    };

    /* 회사가 둘 이상이면 회사별로 묶어 보여 준다 */
    const shownOrgs = uniq(vids.map(function (v) { return D.variants[v].org; }));
    const groups = shownOrgs.map(function (org) {
      const mine = vids.filter(function (v) { return D.variants[v].org === org; });
      return [orgs.length > 1 ? h('h4', {class: 'orghead', text: D.variants[mine[0]].orgName + ' · 종형 ' + mine.length + '개'}) : null, mine.map(row)];
    });

    const gateRows = [];
    shownOrgs.forEach(function (org) {
      const mine = vids.filter(function (v) { return D.variants[v].org === org; });
      if (orgs.length > 1) gateRows.push(h('tr', null, h('th', {class: 'grp', colspan: '5', scope: 'colgroup', text: D.variants[mine[0]].orgName})));
      mine.forEach(function (vid) {
        const v = D.variants[vid];
        gateRows.push(h('tr', null, h('th', {scope: 'row'}, vLabel(vid)),
          h('td', {text: v.uw + (v.uw === '간편심사' && v.simple ? ' ' + v.simple : '')}), gateCells(v)));
      });
    });
    const gate = table(null, ['종형', '심사', '최근 소견', '입원·수술', '중대질병'], gateRows);

    return screen('가입 적격·간편심사 관문 비교', lead,
      orgs.length > 1 ? choice('s2-org', '회사', [{value: '', label: '전체 (종형 ' + onSale.length + '개)'}].concat(orgs.map(function (o) {
        const mine = onSale.filter(function (v) { return D.variants[v].org === o; });
        return {value: o, label: D.variants[mine[0]].orgName + ' (' + mine.length + '개)'};
      })), st.org, function (o) { st.org = o; renderMain(); }) : null,
      endedCount ? h('div', {class: 'controls'}, h('label', {class: 'check'},
        h('input', {type: 'checkbox', checked: st.ended, 'data-key': 's2-ended',
          onchange: function (e) { st.ended = e.target.checked; renderMain(); }}),
        '판매가 끝난 종형 ' + endedCount + '개도 보기')) : null,
      block('주계약 가입 나이와 구간별 최대 가입금액', groups,
        h('p', {class: 'note', text: '막대는 가입할 수 있는 나이 구간이고, 색이 진할수록 그 구간의 최대 가입금액이 큽니다. 세로선은 고른 나이입니다. 보험기간·납입기간에 따라 가입 나이가 다르면 하나라도 되는 나이를 가입 가능으로 그렸습니다.'})),
      block('간편심사 고지 관문', scrollBox(gate, '간편심사 고지 질문', 640),
        D.texts.uwNotice ? h('p', {class: 'notice', text: D.texts.uwNotice}) : null));
  };

  /* ---------- 화면 3 ---------- */
  const VERDICT = {
    b: ['b', '▲', '나음'], w: ['w', '▼', '못함'], s: ['s', '＝', '같음'], m: ['m', '◆', '엇갈림'],
    o: ['plain', '＋', '기준 종형에 없음'], u: ['n', '', '이 나이 가입 불가'], v: ['plain', '', '기준 종형이 이 나이 가입 불가'],
    p: ['p', '!', '판정 보류(검토 대기)'], q: ['p', '!', '매핑 검토 대기로 비교 제외'], x: ['plain', '', '금액 자료 없음']
  };
  const PART_WORDS = [null, {'+': '지급액 많음', '-': '지급액 적음'}, {'+': '면책 짧음', '-': '면책 김'},
    {'+': '감액 유리', '-': '감액 불리', '~': '감액 조건 엇갈림'}];
  function verdictTag(code) {
    if (code === 'B') return tag('base', '', '기준');
    const v = VERDICT[code.charAt(0)];
    return v ? tag(v[0], v[1], v[2]) : null;
  }
  /* 금액이 없어 판정하지 않은 칸은 무엇이 없는지 밝힌다: 이 종형의 가입 한도인지, 금액 자체인지, 기준 종형 쪽인지 */
  function cellVerdictTag(code, st) {
    if (code.charAt(0) !== 'x' || st.kind !== 'ok') return verdictTag(code);
    if (st.vals[st.rep] !== null) return tag('plain', '', '기준 종형 금액 자료 없음');
    return tag('plain', '', st.caps[st.rep] === null ? '가입 한도 자료 없음' : '금액 자료 없음');
  }
  function partsText(code) {
    const out = [];
    for (let i = 1; i <= 3; i++) {
      const word = PART_WORDS[i][code.charAt(i)];
      if (word) out.push(word);
    }
    return out.join(', ');
  }
  /* 가입은 되는데 가입 한도 자료가 없어 최대 가입 기준 금액을 내지 못한 줄인지 */
  function lineBlocked(st, i) { return st.kind !== 'ok' || (st.no ? st.no.indexOf(i) >= 0 : false); }
  function lineNoCap(st, i) { return !lineBlocked(st, i) && st.caps[i] === null; }
  /* 기준 대비 판정의 첫 글자. 칸이 없으면 기준 종형에 급부가 있을 때만 빈자리("n")로 본다. */
  function headOf(row, vid, k, bi) {
    const cell = row.cells[vid];
    if (!cell) {
      const baseCell = row.cells[state.s3.base];
      return baseCell && baseCell.lines.length ? 'n' : '';
    }
    return cell.st[cell.by[k]].vs[bi].charAt(0);
  }
  function tally(rows, vid, k, bi) {
    const sum = {b: 0, w: 0, s: 0, m: 0, n: 0, o: 0, p: 0, q: 0, x: 0, u: 0, v: 0, noCap: 0};
    rows.forEach(function (r) {
      const head = headOf(r, vid, k, bi);
      if (sum[head] !== undefined) sum[head]++;
      const cell = r.cells[vid];
      if (head === 'x' && cell) {
        const st = cell.st[cell.by[k]];
        if (st.kind === 'ok' && st.caps[st.rep] === null) sum.noCap++;
      }
    });
    return sum;
  }
  function cmpDetail(row, vid, k, bi) {
    const cell = row.cells[vid];
    const st = cell.st[cell.by[k]];
    const code = st.vs[bi];
    const body = [kv([
      ['조건', condText()],
      ['기준 종형', vLabel(state.s3.base)],
      ['기준 대비', code === 'B' ? '이 종형이 기준입니다.' : [cellVerdictTag(code, st), partsText(code) ? ' ' + partsText(code) : '',
        code.charAt(4) === 'L' ? ' · 지급 한도 문구가 기준과 다름(판정에는 넣지 않음)' : '']],
      ['표준담보', row.name + ' (' + row.major + ' · ' + row.mid + ', 기준 단위 ' + money(row.unit) + ')']
    ])];
    if (st.kind === 'ok' && st.caps[st.rep] === null) {
      body.push(h('p', {class: 'notice', text: '이 종형은 공시 문서에 특약 가입 한도가 없어 "최대로 가입했을 때 지급액"을 계산하지 못합니다. 기준 가입금액에 대한 지급액과 면책·감액 조건만 견줄 수 있고, 우열 판정은 하지 않았습니다.'}));
    }
    if (cell.lines.length > 1) {
      body.push(h('p', {class: 'note', text: '이 표준담보에 이어진 급부가 ' + cell.lines.length + '줄입니다. 주급부 가운데 금액이 가장 큰 줄을 대표로 썼습니다.'}));
    }
    const order = cell.lines.map(function (_, i) { return i; });
    if (st.kind === 'ok') order.sort(function (a, b) { return (a === st.rep ? -1 : 0) - (b === st.rep ? -1 : 0); });   // 대표 줄을 맨 위로
    order.forEach(function (i) {
      body.push(evidence(cell.lines[i], {
        rep: st.kind === 'ok' && i === st.rep, unit: row.unit, unavailable: lineBlocked(st, i), noCap: lineNoCap(st, i),
        amount: st.caps ? st.caps[i] : null, amountLabel: state.age === null ? '특약 최대 가입금액' : '이 나이의 최대 가입금액',
        val: st.vals ? st.vals[i] : null, valLabel: '최대로 가입했을 때 지급액'
      }));
    });
    if (cell.wait.length) {
      body.push(h('p', {class: 'note', text: '아래 급부 ' + cell.wait.length + '줄은 표준담보 매핑이 검토 대기여서 비교 계산에서 뺐습니다.'}));
      cell.wait.forEach(function (bid) { body.push(evidence(bid, {})); });
    }
    openDetail(row.name + ' · ' + vLabel(vid), body);
  }
  function cmpCell(row, vid, k, bi) {
    const cell = row.cells[vid];
    const baseCell = row.cells[state.s3.base];
    if (!cell) {
      const gap = vid !== state.s3.base && baseCell && baseCell.lines.length;
      return h('td', {class: 'none'}, '없음', gap ? h('span', {class: 'sub', text: ' (빈자리)'}) : null);
    }
    const st = cell.st[cell.by[k]];
    const code = st.vs[bi];
    const head = code.charAt(0);
    const cls = code === 'B' ? 'base' : (head === 'b' || head === 'w' || head === 'm' ? head : (head === 'p' || head === 'q' ? 'p' : ''));
    const btn = h('button', {type: 'button', class: 'cellbtn ' + cls, 'data-key': 'c-' + row.id + '-' + vid,
      onclick: function () { cmpDetail(row, vid, k, bi); }});
    const tags = [cellVerdictTag(code, st)];
    if (st.kind === 'ok') {
      const b = D.benefits[cell.lines[st.rep]];
      const rider = D.riders[b.tid];
      const noCap = st.caps[st.rep] === null;
      add(btn, noCap ? [
        /* 가입 한도 자료가 없는 종형: 최대 가입 기준 금액 대신 문서에 적힌 기준 가입금액과 그 지급액을 그대로 적는다 */
        h('span', {class: 'aux', text: '기준 가입 ' + money(b.base) + '에'}),
        h('span', {class: 'main soft num', text: money(b.pay)})
      ] : [
        h('span', {class: 'main num', text: money(st.vals[st.rep])}),
        h('span', {class: 'aux', text: '가입 ' + money(b.base) + '에 ' + money(b.pay) + ' · 최대 가입 ' + money(st.caps[st.rep])})
      ]);
      add(btn, [
        h('span', {class: 'terms', text: [waitText(b.wait), redText(b.red), renewText(rider)].join(' · ')}),
        b.limit ? h('span', {class: 'terms', text: b.limit}) : null
      ]);
      const why = code.length > 1 ? partsText(code) : '';
      if (why) tags.push(tag('plain', '', why));
      if (code.charAt(4) === 'L') tags.push(tag('plain', '', '지급 한도 문구 다름'));
      if (noCap && head !== 'x') tags.push(tag('plain', '', '가입 한도 자료 없음'));
      if (b.pend.length || st.capPend) tags.push(pendTag(st.capPend && !b.pend.length ? '한도 검토 대기' : '검토 대기'));
      if (cell.lines.length > 1) tags.push(tag('plain', '', '급부 ' + cell.lines.length + '줄'));
    } else if (st.kind === 'unavail') {
      add(btn, h('span', {class: 'aux', text: '이 나이에는 가입할 수 없습니다.'}));
    } else {
      add(btn, h('span', {class: 'aux', text: '확정된 급부 없음'}));
    }
    if (cell.wait.length) tags.push(pendTag('매핑 검토 대기 ' + cell.wait.length + '줄'));
    btn.appendChild(h('span', {class: 'tags'}, tags));
    return h('td', null, btn);
  }
  /* 매핑 검토 대기 급부: 분포를 먼저 보여 주고, 목록은 접어 두되 회사·추천 표준담보·이름으로 찾을 수 있게 한다 */
  function waitingBlock() {
    const S = D.s3, sum = S.waitingSummary, w = state.s3.wait;
    if (!sum.groups) return null;
    const recName = function (rec) { return rec && D.std[rec] ? D.std[rec].name : '추천 없음'; };
    const withRec = sum.byRec.filter(function (x) { return x[0] !== null; });
    const top = withRec.slice(0, 6);
    const rest = withRec.slice(6);
    const pickRec = function (value) {
      w.rec = value; w.page = 0; state.open['s3-wait'] = true;
      renderMain();
      const el = document.querySelector('[data-key="fold-s3-wait"]');
      if (el) el.focus();
    };
    const list = function () {
      return listPanel({
        key: 's3-wait', st: w, size: LIST_SIZE, unit: '가지', empty: '조건에 맞는 급부가 없습니다.',
        controls: function (redraw) {
          return [
            sum.byOrg.length > 1 ? pickField('s3-wait-org', '회사', sum.byOrg.map(function (o) { return {value: o.code, label: o.name + ' (' + C.comma(o.n) + ')'}; }), w, 'org', redraw) : null,
            pickField('s3-wait-rec', '추천 표준담보', sum.byRec.map(function (x) {
              return {value: x[0] === null ? '-' : x[0], label: recName(x[0]) + ' (' + C.comma(x[1]) + ')'};
            }), w, 'rec', redraw),
            searchField('s3-wait-q', '특약·급부 이름', w, redraw)
          ];
        },
        items: function () {
          const q = norm(w.q);
          return S.waiting.filter(function (g) {
            const b = D.benefits[g.bids[0]];
            return (!w.org || D.variants[g.variants[0]].org === w.org)
              && (!w.rec || (w.rec === '-' ? !g.rec : g.rec === w.rec))
              && (!q || norm(D.riders[b.tid].name + ' ' + b.name).indexOf(q) >= 0);
          });
        },
        draw: function (slice) {
          return scrollBox(table(null, ['급부 · 특약', '추천 표준담보', rcol('매핑 확률'), '종형', '근거'], slice.map(function (g) {
            const b = D.benefits[g.bids[0]];
            return h('tr', null, h('td', null, b.name, h('br'), h('span', {class: 'sub', text: D.riders[b.tid].name})),
              h('td', {text: recName(g.rec)}), h('td', {class: 'r num', text: prob(b.prob)}),
              h('td', {text: g.variants.map(function (v) { return D.variants[v].kind || vLabel(v); }).join(', ')}),
              h('td', null, h('button', {type: 'button', class: 'btn', 'data-key': 'w-' + g.bids[0], text: '근거',
                onclick: function () {
                  openDetail(b.name, [h('p', {class: 'note', text: '표준담보 매핑이 검토 대기여서 비교 계산에서 뺀 급부입니다. 같은 급부가 실린 종형마다 한 줄씩 보여 줍니다.'})]
                    .concat(g.bids.map(function (bid) { return evidence(bid, {}); })));
                }})));
          })), '매핑 검토 대기 급부', 700);
        }
      });
    };
    return block('매핑 검토 대기 급부 ' + C.comma(sum.groups) + '가지',
      h('p', {class: 'note', text: '표준담보 매핑을 담당자가 확정하기 전이라 비교 계산에서 뺀 급부입니다. 추천이 있으면 그 표준담보 칸에 "매핑 검토 대기"로만 표시됩니다. 같은 특약의 같은 급부가 종형마다 되풀이되면 한 가지로 묶어 셌습니다.'}),
      h('div', {class: 'tiles'},
        tile('검토 대기', C.comma(sum.groups) + '가지', '급부 ' + C.comma(sum.lines) + '줄'),
        tile('추천 표준담보 있음', C.comma(sum.withRec) + '가지', '표준담보 ' + withRec.length + '개에 나뉨'),
        tile('추천 없음', C.comma(sum.groups - sum.withRec) + '가지', '사전에 맞는 담보를 찾지 못함')),
      h('p', {class: 'note', text: '회사별: ' + sum.byOrg.map(function (o) { return o.name + ' ' + C.comma(o.n) + '가지'; }).join(', ') + '.'}),
      top.length ? h('div', {class: 'choice'},
        h('span', {class: 'choice-label', text: '추천이 많이 몰린 표준담보 (누르면 그 급부만 목록에 보입니다)'}),
        h('div', {class: 'choices'}, top.map(function (x) {
          return h('button', {type: 'button', class: 'opt', 'data-key': 's3-wait-top-' + x[0], onclick: function () { pickRec(x[0]); }},
            recName(x[0]) + ' ' + C.comma(x[1]));
        }), rest.length ? h('span', {class: 'sub more', text: '그 밖의 표준담보 ' + rest.length + '개에 '
          + C.comma(rest.reduce(function (n, x) { return n + x[1]; }, 0)) + '가지'}) : null)) : null,
      fold('s3-wait', '목록 보기 · 회사, 추천 표준담보, 이름으로 찾기 (' + C.comma(sum.groups) + '가지)', list));
  }
  screens.s3 = function () {
    const S = D.s3, st = state.s3, k = condIndex();
    if (!S.variants.length) {
      return screen('담보 비교표와 빈자리 특약', null, h('p', {class: 'empty', text: '정밀 비교 대상 종형 자료가 없습니다.'}));
    }
    /* 처음에는 기준 종형과 심사 유형이 같은 종형만 열로 보여 준다. 종형이 늘어도 표가 옆으로 길어지지 않는다. */
    const peers = S.peers[st.base] || S.variants;
    const cols = S.variants.filter(function (v) { return v === st.base || (st.cols ? st.cols[v] : peers.indexOf(v) >= 0); });
    const setCols = function (change) {
      const next = {};
      cols.forEach(function (v) { next[v] = true; });
      change(next);
      st.cols = next;
      renderMain();
    };
    const bi = S.bases.indexOf(st.base);
    const withData = S.rows.filter(function (r) { return r.any; });
    const hidden = S.rows.length - withData.length;
    const gaps = gapGroups(S.variants);

    /* 종형별 요약: 비교표에 나오는 표준담보 전체(보장 분야를 가리지 않음)를 기준 종형과 견준 결과의 분포.
       좁은 화면에서도 옆으로 밀지 않고 읽도록 표 대신 줄 목록으로 그린다. 여기서 비교표에 넣을 열도 고른다. */
    const pool = st.showEmpty ? S.rows : withData;
    const waitOnly = S.rows.filter(function (r) { return !r.any && Object.keys(r.cells).length > 0; }).length;
    const count = function (cls, icon, word, n) { return n ? tag(cls, icon, word + ' ' + n) : null; };   // 0건인 항목은 적지 않는다
    const sumList = h('div', {class: 'sumlist'});
    uniq(S.variants.map(function (v) { return D.variants[v].org; })).forEach(function (org) {
      const mine = S.variants.filter(function (v) { return D.variants[v].org === org; });
      const allOn = mine.every(function (v) { return cols.indexOf(v) >= 0; });
      add(sumList, h('div', {class: 'sumhead'}, h('span', {text: D.variants[mine[0]].orgName + ' · 종형 ' + mine.length + '개'}),
        h('button', {type: 'button', class: 'btn small', 'data-key': 's3-org-' + org, text: allOn ? '이 회사 열 모두 빼기' : '이 회사 열 모두 보기',
          onclick: function () { setCols(function (next) { mine.forEach(function (v) { next[v] = !allOn; }); }); }})));
      mine.forEach(function (v) {
        const isBase = v === st.base;
        const s = tally(pool, v, k, bi);
        const held = [];
        if (s.p) held.push('판정 보류(검토 대기) ' + s.p);
        if (s.q) held.push('매핑 검토 대기 ' + s.q);
        if (s.noCap) held.push('가입 한도 자료 없음 ' + s.noCap);
        if (s.x - s.noCap) held.push('금액 자료 없음 ' + (s.x - s.noCap));
        if (s.u + s.v) held.push('이 나이 가입 불가 ' + (s.u + s.v));
        add(sumList, h('div', {class: 'sumrow'},
          h('label', {class: 'check'},
            h('input', {type: 'checkbox', checked: cols.indexOf(v) >= 0, disabled: isBase, 'data-key': 's3-col-' + v,
              onchange: function (e) { const on = e.target.checked; setCols(function (next) { next[v] = on; }); }}),
            h('span', null, vLabel(v), h('br'), h('span', {class: 'sub', text: vSub(v)}))),
          isBase ? h('div', {class: 'counts'}, tag('base', '', '기준'))
            : h('div', {class: 'counts'}, count('b', '▲', '나음', s.b), count('s', '＝', '같음', s.s), count('w', '▼', '못함', s.w),
              count('m', '◆', '엇갈림', s.m), count('n', '', '빈자리', s.n), count('plain', '＋', '기준 종형에 없음', s.o),
              held.length ? h('span', {class: 'held', text: '판정하지 않음: ' + held.join(' · ')}) : null,
              !(s.b + s.s + s.w + s.m + s.n + s.o) && !held.length ? h('span', {class: 'held', text: '견줄 담보 없음'}) : null)));
      });
    });
    const isDefault = !st.cols;
    const sumBlock = block('종형별 요약 · 표준담보 ' + pool.length + '개를 기준 종형과 견준 결과 (' + condText() + ')',
      h('p', {class: 'note', text: '체크한 종형이 아래 비교표의 열로 나옵니다. 지금 ' + cols.length + '개' + (isDefault ? '(기준 종형과 심사 유형이 같은 종형)' : '') + '.'}),
      sumList,
      h('div', {class: 'controls'},
        !isDefault ? h('button', {type: 'button', class: 'btn small', 'data-key': 's3-cols-peers', text: '심사 유형이 같은 종형만',
          onclick: function () { st.cols = null; renderMain(); }}) : null,
        cols.length < S.variants.length ? h('button', {type: 'button', class: 'btn small', 'data-key': 's3-cols-all', text: '모든 종형 보기',
          onclick: function () { setCols(function (next) { S.variants.forEach(function (v) { next[v] = true; }); }); }}) : null));

    /* 비교표: 보장 분야 하나씩 보여 주고, 이름으로 찾을 때는 모든 분야에서 찾는다 */
    const majors = uniq(pool.map(function (r) { return r.major; }));
    if (st.major !== ALL && majors.indexOf(st.major) < 0) st.major = majors[0] || ALL;
    const diffOk = function (r) {
      if (!st.diff) return true;
      const heads = cols.filter(function (v) { return v !== st.base; }).map(function (v) { return headOf(r, v, k, bi); });
      const has = function (set) { return heads.some(function (x) { return x && set.indexOf(x) >= 0; }); };
      if (st.diff === 'diff') return has('bwmno');
      if (st.diff === 'gap') return has('n');
      return has('pqxuv') || cols.some(function (v) { return r.cells[v] && r.cells[v].wait.length > 0; });
    };
    const tableBox = h('div', {class: 'list-body'});
    const drawTable = function () {
      const q = norm(st.q);
      const rows = pool.filter(function (r) {
        return (q ? norm(r.name + ' ' + r.mid + ' ' + r.major).indexOf(q) >= 0 : (st.major === ALL || r.major === st.major)) && diffOk(r);
      });
      tableBox.textContent = '';
      const scope = q ? '이름에 "' + st.q.trim() + '"이(가) 들어간 표준담보 ' + rows.length + '개 (모든 보장 분야에서 찾음)'
        : (st.major === ALL ? '전체' : st.major) + ' 표준담보 ' + rows.length + '개';
      add(tableBox, h('p', {class: 'pager num', text: scope + (st.diff ? ' · 거른 결과' : '')}));
      if (!rows.length) {
        add(tableBox, h('p', {class: 'empty', text: '조건에 맞는 표준담보가 없습니다.'}));
        return;
      }
      const head = [h('th', {scope: 'col', text: '표준담보'})].concat(cols.map(function (v) {
        const s = tally(rows, v, k, bi);
        return h('th', {scope: 'col'}, vHead(v), h('br'), h('span', {class: 'sub', text: vSub(v)}),
          v === st.base ? h('div', {class: 'colsum'}, tag('base', '', '기준'))
            : h('div', {class: 'colsum'}, tag('b', '▲', String(s.b)), tag('w', '▼', String(s.w)), tag('s', '＝', String(s.s)),
              s.m ? tag('m', '◆', String(s.m)) : null, tag('n', '', '빈자리 ' + s.n),
              s.noCap ? tag('plain', '', '한도 자료 없음 ' + s.noCap) : null));
      }));
      const body = [];
      let major = null, mid = null;
      rows.forEach(function (r) {
        if (r.major !== major) {
          major = r.major; mid = null;
          body.push(h('tr', null, h('th', {class: 'grp', colspan: String(cols.length + 1), scope: 'colgroup', text: r.major})));
        }
        const first = r.mid !== mid;
        mid = r.mid;
        body.push(h('tr', null,
          h('th', {scope: 'row'}, first ? [h('span', {class: 'sub', text: r.mid}), h('br')] : null, r.name,
            h('br'), h('span', {class: 'sub', text: r.type + ' · 기준 단위 ' + money(r.unit)})),
          cols.map(function (v) { return cmpCell(r, v, k, bi); })));
      });
      const tbl = h('table', {class: 'cmp'},
        h('colgroup', null, h('col', {class: 'c0'}), cols.map(function () { return h('col'); })),
        h('thead', null, h('tr', null, head)), h('tbody', null, body));
      tbl.style.setProperty('--cols', String(cols.length));      // 표의 최소 폭과 좁은 화면의 칸 나눔은 CSS가 이 값으로 정한다
      add(tableBox, scrollBox(tbl, '표준담보별 비교표', 0));
    };
    drawTable();
    const majorCount = function (m) { return pool.filter(function (r) { return m === ALL || r.major === m; }).length; };
    const cmpBlock = block('표준담보별 비교표',
      choice('s3-major', '보장 분야', majors.map(function (m) { return {value: m, label: m + ' ' + majorCount(m)}; })
        .concat([{value: ALL, label: '전체 ' + majorCount(ALL)}]), st.major, function (m) { st.major = m; renderMain(); }),
      h('div', {class: 'controls'},
        searchField('s3-q', '표준담보 이름', st, drawTable),
        h('label', {class: 'field'}, h('span', {text: '보기'}),
          h('select', {'data-key': 's3-diff', onchange: function (e) { st.diff = e.target.value; renderMain(); }},
            [['', '모든 담보'], ['diff', '기준과 다른 담보(나음·못함·엇갈림·빈자리)'], ['gap', '빈자리만'], ['hold', '검토 대기·판정하지 않은 담보']].map(function (o) {
              return h('option', {value: o[0], selected: st.diff === o[0], text: o[1]});
            }))),
        hidden ? h('label', {class: 'check'},
          h('input', {type: 'checkbox', checked: st.showEmpty, 'data-key': 's3-empty',
            onchange: function (e) { st.showEmpty = e.target.checked; renderMain(); }}),
          '확정된 급부가 어느 종형에도 없는 표준담보 ' + hidden + '개도 보기' + (waitOnly ? '(매핑 검토 대기 급부만 있는 ' + waitOnly + '개 포함)' : '')) : null),
      h('div', {class: 'legend', 'aria-label': '표시 읽는 법'},
        tag('b', '▲', '나음'), tag('s', '＝', '같음'), tag('w', '▼', '못함'), tag('m', '◆', '엇갈림'),
        tag('n', '', '없음(빈자리)'), tag('p', '!', '검토 대기'), gaps.length ? tag('plain', '', '가입 한도 자료 없음') : null,
        h('span', {text: '칸을 누르면 근거가 열립니다.'})),
      tableBox,
      h('p', {class: 'note', text: '판정은 지급액(최대 가입 기준), 면책기간, 감액 조건만 봅니다. 셋이 서로 다른 방향이면 "엇갈림"입니다. 입원 며칠째부터 주는지 같은 지급 한도 문구는 글자로만 보여 주고, 기준과 다르면 "지급 한도 문구 다름"을 붙입니다. 사람 검토를 기다리는 값이 대표 급부에 있으면 판정을 미룹니다.'}));

    return screen('담보 비교표와 빈자리 특약',
      '칸의 큰 숫자는 그 특약을 최대로 가입했을 때 받는 금액입니다(' + condText() + '). 기준 종형과 견주어 지급액·면책·감액 조건이 나은지 표시합니다. 보험료는 넣지 않았습니다.',
      gaps.length ? h('p', {class: 'notice', text: gapNames(gaps) + '는 공시 문서에 특약 가입 한도가 없어 "최대로 가입했을 때 지급액"을 계산하지 못합니다. 이 종형의 칸에는 기준 가입금액에 대한 지급액과 면책·감액 조건을 적고, 우열 판정은 하지 않습니다.'}) : null,
      variantPicker('s3-base', '기준 ', S.bases, st.base, function (v) { st.base = v; renderMain(); }),
      sumBlock, cmpBlock, waitingBlock());
  };

  /* ---------- 화면 4 ---------- */
  function stepOf(lo) {
    const base = 500;
    if (!lo) return base;
    let a = lo, b = base;
    while (b) { const t = a % b; a = b; b = t; }
    return a || base;
  }
  function reasonText(reason, vm, vid) {
    const name = function (tid) { return '「' + D.riders[tid].name + '」'; };
    if (reason.code === 'age') return '이 나이에는 가입할 수 없음';
    if (reason.code === 'main') return '주계약에 가입할 수 없어 부가할 수 없음';
    if (reason.code === 'need') return name(reason.base) + '에 가입해야 부가할 수 있음';
    if (reason.code === 'needAmount') return name(reason.base) + ' 가입금액이 ' + money(reason.num) + ' 이상이어야 함';
    if (reason.code === 'exclusive') return name(reason.base) + '와 함께 가입할 수 없음';
    if (reason.code === 'belowMin') return '고를 수 있는 금액(최대 ' + money(reason.hi) + ')이 최소 가입금액보다 작음';
    return '가입할 수 없음';
  }
  screens.s4 = function () {
    const S = D.s4, st = state.s4;
    if (!st.vid) {
      return screen('특약 조합별 실제 지급액', null, h('p', {class: 'empty', text: '정밀 비교 대상 종형 자료가 없습니다.'}));
    }
    const vid = st.vid, vm = S.byVariant[vid], k = condIndex();
    const want = st.want[vid] || (st.want[vid] = {});
    const vrOf = {};
    vm.riders.forEach(function (r) { vrOf[r.tid] = r; });
    /* 가입 한도 자료가 없는 특약(공시 문서에 한도가 없는 회사)은 "최대"를 알 수 없다.
       고를 때 급부표의 기준 가입금액을 넣어 두고, 사용자가 고칠 수 있게 한다. 계산 규칙(calc.js)은 그대로다. */
    const noLimit = function (r) { return r.lim[k] === null && r.max === null; };
    const startAmount = function (r) { return noLimit(r) && r.ref !== null && r.ref !== undefined ? r.ref : null; };
    const unknown = vm.riders.filter(noLimit);
    if (vm.main && vrOf[vm.main] && want[vm.main] === undefined && startAmount(vrOf[vm.main]) !== null) want[vm.main] = startAmount(vrOf[vm.main]);

    const res = C.evaluate(vm, k, want);
    const fixed = [];
    res.rows.forEach(function (row) {
      if (row.on && row.clamped) { want[row.tid] = row.amount; fixed.push(row.tid); }
    });
    const pay = C.payouts(vm, D.benefits, res.rows);
    const rowOf = {};
    res.rows.forEach(function (r) { rowOf[r.tid] = r; });
    const riderCount = res.rows.filter(function (r) { return r.tid !== vm.main; }).length;
    const onCount = res.rows.filter(function (r) { return r.on && r.tid !== vm.main; }).length;
    const mainRow = rowOf[vm.main];
    const ridersAge = {};
    D.s2.byVariant[vid].riders.forEach(function (r) { ridersAge[r.tid] = r.seg[state.sex]; });
    const linked = {};
    vm.rules.forEach(function (r) { if (r.type === '최대연동') linked[r.target] = r.base; });
    const allNoCond = vm.riders.every(function (r) { return r.noCond; });

    const picker = variantPicker('s4-variant', '', S.variants, vid, function (v) { st.vid = v; st.list.page = 0; st.others.page = 0; renderMain(); });

    const riderRow = function (row) {
      const r = D.riders[row.tid], vr = vrOf[row.tid];
      const isMain = row.tid === vm.main;
      const blocked = row.reasons.length > 0;
      const id = 'r-' + row.tid;
      const box = h('input', {type: 'checkbox', id: id, 'data-key': 'chk-' + row.tid, checked: row.on,
        disabled: isMain || blocked || row.forced,
        onchange: function (e) {
          if (e.target.checked) want[row.tid] = startAmount(vr); else delete want[row.tid];
          renderMain();
        }});
      const line = [];
      if (row.on) {
        const input = h('input', {type: 'number', class: 'amount', 'data-key': 'amt-' + row.tid, value: String(row.amount),
          min: String(row.lo), max: row.hi === null ? null : String(row.hi), step: String(stepOf(row.lo || (row.hi === null ? vr.ref : 0))),
          'aria-label': r.name + ' 가입금액(만원)',
          onchange: function (e) {
            const n = Number(e.target.value);
            want[row.tid] = e.target.value.trim() === '' || isNaN(n) ? startAmount(vr) : n;
            renderMain();
          }});
        line.push(h('span', {class: 'field'}, input, h('span', {text: '만원'})));
        line.push(h('span', {class: 'num', text: '= ' + money(row.amount)}));
      }
      if (!blocked) {
        let range;
        if (row.hi === null) {
          range = '가입 한도 자료 없음' + (row.lo ? ' (최소 ' + money(row.lo) + ')' : '')
            + (vr.ref !== null && vr.ref !== undefined ? ' · 급부표의 기준 가입금액 ' + money(vr.ref) : '');
        } else {
          range = '고를 수 있는 범위 ' + (row.hi === row.lo ? money(row.lo) + '만' : money(row.lo) + '~' + money(row.hi));
          if (r.max !== null && row.hi < r.max) {
            range += vr.lim[k] !== null && vr.lim[k] <= row.hi ? ' (나이 구간 한도)' : ' (' + (linked[row.tid] === vm.main ? '주계약' : '기준 특약') + ' 가입금액까지)';
          }
        }
        line.push(h('span', {text: range}));
      }
      if (vr.limPend[k]) line.push(pendTag('한도 검토 대기'));
      if (vr.noCond && !isMain && !allNoCond) line.push(tag('plain', '', '가입나이 자료 없음'));
      if (row.forced) line.push(tag('plain', '', '의무 부가'));
      if (fixed.indexOf(row.tid) >= 0) line.push(tag('plain', '', '범위를 벗어나 ' + money(row.amount) + '로 맞춤'));
      row.reasons.forEach(function (reason) {
        let text = reasonText(reason, vm, vid);
        if (reason.code === 'age' && ridersAge[row.tid] && ridersAge[row.tid].length) {
          text += ' (가입 나이 ' + ridersAge[row.tid].map(function (s) { return ageRange(s.lo, s.hi); }).join(', ') + ')';
        }
        line.push(h('span', {class: 'why'}, tag('n', '', '선택 불가'), ' ' + text));
      });
      return h('div', {class: 'rider' + (row.on ? '' : ' off')}, box,
        h('div', null,
          h('label', {class: 'rname', for: id}, r.name, isMain ? [' ', tag('base', '', '주계약')] : null),
          h('div', {class: 'rline'}, line)));
    };
    /* 특약이 수백 개인 종형도 있어 한 쪽씩 보여 주고 이름으로 찾는다. 고른 특약만 따로 볼 수도 있다. */
    const riderList = listPanel({
      key: 's4-list', st: st.list, size: RIDER_SIZE, unit: '개', empty: '조건에 맞는 특약이 없습니다.',
      controls: function (redraw) {
        return [
          searchField('s4-q', '특약 이름', st.list, redraw),
          h('label', {class: 'check'},
            h('input', {type: 'checkbox', checked: st.list.picked, 'data-key': 's4-picked',
              onchange: function (e) { st.list.picked = e.target.checked; redraw(); }}),
            '고른 특약만 보기')
        ];
      },
      items: function () {
        const q = norm(st.list.q);
        return res.rows.filter(function (row) {
          return (!st.list.picked || row.on) && (!q || norm(D.riders[row.tid].name).indexOf(q) >= 0);
        });
      },
      draw: function (slice) { return h('div', {class: 'riders'}, slice.map(riderRow)); }
    });

    /* 결과: 표준담보 순서는 화면 3의 행 순서를 따른다 */
    const orderOf = {};
    D.s3.rows.forEach(function (r, i) { orderOf[r.id] = i; });
    const groups = pay.groups.slice().sort(function (a, b) { return orderOf[a.std] - orderOf[b.std]; });
    const types = [];
    groups.forEach(function (g) { const t = D.std[g.std].type; if (types.indexOf(t) < 0) types.push(t); });
    const lineOf = function (g) { return g.lines[g.rep]; };
    const openLines = function (g) {
      const std = D.std[g.std];
      const body = [h('p', {class: 'note', text: '고른 가입금액으로 환산한 금액입니다. 급부가 여럿이면 더하지 않고 대표 줄 하나를 씁니다.'})];
      g.lines.map(function (l, i) { return i; }).sort(function (a, b) { return (a === g.rep ? -1 : 0) - (b === g.rep ? -1 : 0); })
        .forEach(function (i) {
          const l = g.lines[i], b = D.benefits[l.bid];
          body.push(evidence(l.bid, {rep: i === g.rep, unit: std.unit, amount: rowOf[b.tid].amount, amountLabel: '고른 가입금액', val: l.val, valLabel: '지급액'}));
        });
      openDetail(std.name + ' · ' + vLabel(vid), body);
    };
    const bars = types.map(function (type) {
      const list = groups.filter(function (g) { return D.std[g.std].type === type; });
      const top = Math.max.apply(null, list.map(function (g) { return lineOf(g).val || 0; }).concat([0]));
      return h('div', {class: 'bargroup'}, h('h4', {text: type}), list.map(function (g) {
        const l = lineOf(g), red = l.reduced[0];
        const width = function (v) { return 'calc((100% - 132px) * ' + (top > 0 && v ? v / top : 0) + ')'; };
        return h('div', {class: 'barrow'},
          h('div', {class: 'barlabel', text: D.std[g.std].name}),
          h('div', {class: 'bartrack'},
            h('div', {class: 'barline', title: D.std[g.std].name + ' ' + money(l.val)},
              h('span', {class: 'barfill', style: 'width:' + width(l.val)}), h('span', {class: 'barval num', text: money(l.val)})),
            red ? h('div', {class: 'barline', title: '계약일부터 ' + months(red[0]) + ' 미만 ' + money(red[1])},
              h('span', {class: 'barfill soft', style: 'width:' + width(red[1])}),
              h('span', {class: 'barval soft num', text: months(red[0]) + ' 미만 ' + money(red[1])})) : null));
      }));
    });
    const resultTable = table(null, ['표준담보', '대표 급부', rcol('지급액'), rcol('감액 기간 중 지급액'), '면책', '지급 한도', '근거'], groups.map(function (g) {
      const l = lineOf(g), b = D.benefits[l.bid];
      return h('tr', null,
        h('th', {scope: 'row'}, D.std[g.std].name),
        h('td', null, b.name, h('br'), h('span', {class: 'sub', text: D.riders[b.tid].name}),
          b.pend.length ? [' ', pendTag()] : null),
        h('td', {class: 'r num', text: money(l.val)}),
        h('td', {class: 'r num'}, l.reduced.length ? l.reduced.map(function (s) { return months(s[0]) + ' 미만 ' + money(s[1]); }).join(', ') : '감액 없음',
          b.exc && l.reduced.length ? [h('br'), h('span', {class: 'sub', text: '예외: ' + b.exc})] : null),
        h('td', {text: b.wait ? C.comma(b.wait) + '일' : '없음'}),
        h('td', {text: orNone(b.limit)}),
        h('td', null, h('button', {type: 'button', class: 'btn', 'data-key': 'ev-' + g.std,
          onclick: function () { openLines(g); }}, g.lines.length > 1 ? '급부 ' + g.lines.length + '줄' : '근거')));
    }));
    const others = pay.others.length ? fold('s4-others', '표준담보에 이어지지 않은 급부 ' + C.comma(pay.others.length) + '줄 (사전 범위 밖이거나 매핑 검토 대기)', function () {
      return listPanel({
        key: 's4-others', st: st.others, size: LIST_SIZE, unit: '줄', empty: '조건에 맞는 급부가 없습니다.',
        controls: function (redraw) { return [searchField('s4-others-q', '급부·특약 이름', st.others, redraw)]; },
        items: function () {
          const q = norm(st.others.q);
          return pay.others.filter(function (l) {
            const b = D.benefits[l.bid];
            return !q || norm(b.name + ' ' + D.riders[b.tid].name).indexOf(q) >= 0;
          });
        },
        draw: function (slice) {
          return scrollBox(table(null, ['급부', '특약', rcol('지급액'), '매핑 상태'], slice.map(function (l) {
            const b = D.benefits[l.bid];
            return h('tr', null, h('td', null, b.name, b.pend.length ? [' ', pendTag()] : null), h('td', {text: D.riders[b.tid].name}),
              h('td', {class: 'r num', text: money(l.val)}),
              h('td', null, b.state === '대기' ? pendTag('매핑 검토 대기') : b.state));
          })), '표준담보에 이어지지 않은 급부', 680);
        }
      });
    }) : null;

    const rules = vm.rules.length || vm.skipped.length ? fold('s4-rules', '적용한 결합 제약 ' + vm.rules.length + '건' + (vm.skipped.length ? ', 적용하지 못한 제약 ' + vm.skipped.length + '건' : ''), function () {
      return h('ul', {class: 'plain'}, vm.rules.concat(vm.skipped).map(function (r, i) {
        const names = (D.riders[r.base] ? D.riders[r.base].name : r.base) + ' → ' + (D.riders[r.target] ? D.riders[r.target].name : r.target);
        return h('li', null, (i >= vm.rules.length ? '[적용하지 못함] ' : '') + r.type + ': ' + names,
          r.text ? h('span', {class: 'sub', text: ' — ' + r.text}) : null);
      }));
    }) : null;

    const lead = !mainRow || !mainRow.on
      ? condText() + ': 이 종형의 주계약에 가입할 수 없는 나이입니다. 조합을 만들 수 없습니다.'
      : condText() + ' · 주계약 ' + money(mainRow.amount) + ', 특약 ' + riderCount + '개 가운데 ' + onCount + '개를 골랐습니다. 표준담보 ' + groups.length + '개에 지급액이 생깁니다.';
    const allUnknown = unknown.length === vm.riders.length;
    const fillLabel = allUnknown ? '기준 가입금액으로 모두 담기' : '최대로 담기';
    let fillNote = '"최대로 담기"는 제약 안에서 모든 특약을 고를 수 있는 가장 큰 금액으로 담습니다.';
    if (allUnknown) fillNote = '이 종형은 가입 한도 자료가 없어 "최대"를 알 수 없습니다. "기준 가입금액으로 모두 담기"는 모든 특약을 급부표의 기준 가입금액으로 담습니다.';
    else if (unknown.length) fillNote += ' 가입 한도 자료가 없는 특약 ' + unknown.length + '개는 급부표의 기준 가입금액으로 담습니다.';

    return screen('특약 조합별 실제 지급액', lead,
      picker,
      unknown.length ? h('p', {class: 'notice', text: (allUnknown ? '이 종형은 공시 문서에 특약 가입 한도' + (allNoCond ? '와 가입 나이' : '') + '가 없습니다.'
        : '이 종형의 특약 ' + vm.riders.length + '개 가운데 ' + unknown.length + '개는 공시 문서에 가입 한도가 없습니다.')
        + ' 그런 특약을 고르면 급부표의 기준 가입금액을 넣어 두며, 금액은 직접 고칠 수 있습니다. 한도를 넘는 금액인지는 이 화면이 확인하지 못합니다.'}) : null,
      h('div', {class: 'controls'},
        h('button', {type: 'button', class: 'btn primary', 'data-key': 's4-max', text: fillLabel,
          onclick: function () { const all = {}; vm.riders.forEach(function (r) { all[r.tid] = startAmount(r); }); st.want[vid] = all; renderMain(); }}),
        h('button', {type: 'button', class: 'btn', 'data-key': 's4-clear', text: '특약 모두 빼기',
          onclick: function () { const keep = {}; if (want[vm.main] !== undefined) keep[vm.main] = want[vm.main]; st.want[vid] = keep; renderMain(); }})),
      block('주계약과 특약 고르기 · 특약 ' + riderCount + '개 가운데 ' + onCount + '개 고름', riderList, rules,
        h('p', {class: 'note', text: fillNote + ' 가입 단위(예: 500만원 단위) 자료는 없어서 최소·최대 범위만 확인합니다.'})),
      block('표준담보별 실제 지급액',
        groups.length ? [
          h('div', {class: 'keyline'}, h('span', null, h('i'), '지급액'), h('span', null, h('i', {class: 'soft'}), '감액 기간 중 지급액(계약일부터 1년 미만 등)'),
            h('span', {text: '막대 길이는 같은 급부유형 안에서만 견줄 수 있습니다.'})),
          h('div', {class: 'bars'}, bars),
          h('div', {class: 'block'}, scrollBox(resultTable, '표준담보별 실제 지급액', 900))
        ] : h('p', {class: 'empty', text: '고른 특약에 표준담보로 이어진 급부가 없습니다. 특약을 고르거나 "' + fillLabel + '"를 눌러 보세요.'}),
        others,
        h('p', {class: 'note', text: '지급액은 급부의 기준지급금액을 가입금액에 비례해 환산한 값입니다. 한 표준담보에 급부가 여럿이면 원인이 다른 급부를 더하지 않도록 대표 줄 하나만 씁니다. 보험료는 자료가 없어 다루지 않습니다(2단계).'})));
  };

  /* ---------- 화면 5 ---------- */
  const FIELD = {pay: '지급액', top: '최대 가입 시 지급액', red: '감액', wait: '면책기간', limit: '지급 한도', std: '표준담보',
    range: '가입금액 범위', renew: '갱신 주기'};
  function fieldValue(field, v) {
    if (field === 'pay') return '가입 ' + money(v[0]) + '에 ' + money(v[1]);
    if (field === 'top') return money(v);
    if (field === 'red') return v && v.length ? redText(v) : '감액 없음';
    if (field === 'wait') return v ? C.comma(v) + '일' : '없음';
    if (field === 'limit') return orNone(v);
    if (field === 'std') return v && D.std[v] ? D.std[v].name : '없음';
    if (field === 'range') return v[0] === v[1] ? money(v[0]) : money(v[0]) + '~' + money(v[1]);
    if (field === 'renew') return v ? v + '년 갱신' : '비갱신';
    return String(v);
  }
  function dirTag(dir) {
    if (dir === '+') return tag('b', '▲', '나아짐');
    if (dir === '-') return tag('w', '▼', '못해짐');
    if (dir === '~') return tag('m', '◆', '엇갈림');
    return tag('plain', '', '달라짐');
  }
  function day(text) { return Date.parse(text + 'T00:00:00Z') / 86400000; }
  function timeline() {
    const T = D.s5.timeline;
    if (!T.from || !T.to) return h('p', {class: 'empty', text: '적용시작일 자료가 없습니다.'});
    const from = day(T.from), to = Math.max(day(T.to), from + 1);
    const pos = function (d) { return Math.max(0, Math.min(100, (day(d) - from) / (to - from) * 100)); };
    const years = [];
    for (let y = Number(T.from.slice(0, 4)) + 1; y <= Number(T.to.slice(0, 4)); y++) years.push(y);
    const axis = h('div', {class: 'taxis'}, h('div'), h('div', {class: 'axis', 'aria-hidden': 'true'},
      h('span', {style: 'left:0', text: T.from}),
      years.map(function (y) {
        const p = pos(y + '-01-01');
        return p > 32 && p < 68 ? h('span', {style: 'left:' + p + '%', text: y + '년'}) : null;   // 양 끝 날짜와 겹치지 않을 때만
      }),
      h('span', {style: 'left:100%', text: T.to})));
    return h('div', {class: 'timeline'}, T.variants.map(function (vid) {
      const v = D.variants[vid];
      if (!v.start) return null;
      const end = v.end || T.to;
      const dates = v.start + ' ~ ' + (v.end ? v.end + ' (판매 종료)' : '판매 중');
      return h('div', {class: 'trow'},
        h('div', {text: vLabel(vid)}),
        h('div', {class: 'ttrack', role: 'img', 'aria-label': vLabel(vid) + ' 판매 기간 ' + dates, title: dates},
          h('div', {class: 'span' + (v.end ? ' ended' : ''), style: 'left:' + pos(v.start) + '%;width:' + Math.max(0.6, pos(end) - pos(v.start)) + '%'})),
        h('div', {class: 'tdates', text: dates}));
    }), axis);
  }
  screens.s5 = function () {
    const S = D.s5;
    if (!S.pairs.length) {
      return screen('개정 전후 비교', '같은 종형계보키로 이어지는 개정 전후 종형이 자료에 없습니다.',
        block('출시·판매중지 시간선', timeline()));
    }
    const p = S.pairs[Math.min(state.s5.pair, S.pairs.length - 1)];
    const select = choice('s5-pair', '비교할 종형', S.pairs.map(function (x, i) {
      return {value: i, label: vLabel(x.old) + ' → ' + vLabel(x.new)};
    }), Math.min(state.s5.pair, S.pairs.length - 1), function (i) { state.s5.pair = i; renderMain(); });
    const changedBenefits = p.changes.reduce(function (n, c) { return n + c.benefits.length; }, 0);

    const rows = [];
    p.changes.forEach(function (c) {
      let firstRider = true;
      const riderCell = function () {
        const cell = h('td', null, firstRider ? [D.riders[c.new].name,
          D.riders[c.new].name !== D.riders[c.old].name ? [h('br'), h('span', {class: 'sub', text: '개정 전: ' + D.riders[c.old].name})] : null] : null);
        firstRider = false;
        return cell;
      };
      c.rider.forEach(function (item) {
        rows.push(h('tr', null, riderCell(), h('td', {class: 'sub', text: '(특약 전체)'}), h('td', {text: FIELD[item.field]}),
          h('td', {text: fieldValue(item.field, item.old)}), h('td', {text: fieldValue(item.field, item.new)}),
          h('td', {class: 'dir'}, dirTag(item.dir))));
      });
      c.benefits.forEach(function (b) {
        const o = D.benefits[b.old], n = D.benefits[b.new];
        b.items.forEach(function (item, i) {
          const extra = item.field === 'pay' && b.top[0] === b.top[1] && b.top[0] !== null
            ? h('div', {class: 'sub', text: '최대 가입 시 지급액은 ' + money(b.top[0]) + '으로 같음'}) : null;
          rows.push(h('tr', null, riderCell(),
            h('td', null, i === 0 ? [n.name, b.how !== '이름' ? [h('br'), h('span', {class: 'sub', text: '개정 전 이름: ' + o.name + ' (이름이 비슷해 이은 급부)'})] : null,
              n.pend.length || o.pend.length ? [' ', pendTag()] : null] : null),
            h('td', {text: FIELD[item.field]}),
            h('td', {text: fieldValue(item.field, item.old)}), h('td', {text: fieldValue(item.field, item.new)}),
            h('td', {class: 'dir'}, dirTag(item.dir), extra)));
        });
      });
      c.removed.forEach(function (bid) {
        const b = D.benefits[bid];
        rows.push(h('tr', null, riderCell(), h('td', {text: b.name}), h('td', {text: '급부'}),
          h('td', {text: '가입 ' + money(b.base) + '에 ' + money(b.pay)}), h('td', {text: '없음'}), h('td', {class: 'dir'}, tag('n', '', '없어진 급부'))));
      });
      c.added.forEach(function (bid) {
        const b = D.benefits[bid];
        rows.push(h('tr', null, riderCell(), h('td', {text: b.name}), h('td', {text: '급부'}),
          h('td', {text: '없음'}), h('td', {text: '가입 ' + money(b.base) + '에 ' + money(b.pay)}), h('td', {class: 'dir'}, tag('plain', '＋', '새로 생긴 급부'))));
      });
    });
    const diffTable = table(null, ['특약', '급부', '항목', '개정 전', '개정 후', '변화'], rows);
    diffTable.style.minWidth = '900px';

    const riderList = function (tids) {
      return h('ul', {class: 'plain'}, tids.map(function (tid) {
        const r = D.riders[tid];
        const vm = Object.keys(D.benefits).filter(function (bid) { return D.benefits[bid].tid === tid; });
        return h('li', null, r.name, h('span', {class: 'sub', text: ' — 가입금액 ' + fieldValue('range', [r.min, r.max]) + ' · 급부 ' + vm.length + '줄: '
          + vm.map(function (bid) { return D.benefits[bid].name + ' ' + money(D.benefits[bid].pay); }).join(', ')}));
      }));
    };

    const gateLabel = {months: '최근 소견(개월)', hospYears: '입원 기간(년)', surgery: '입원 질문에 수술 포함', majorYears: '중대질병 기간(년)', majorCount: '중대질병 수'};
    const gateValue = function (field, v) {
      if (v === null || v === undefined) return '해당 없음';
      if (field === 'surgery') return v ? '포함' : '입원만 물음';
      return String(v);
    };
    const same = function (a, b) { return JSON.stringify(a) === JSON.stringify(b); };
    const changeCell = function (a, b) { return h('td', null, same(a, b) ? tag('s', '＝', '같음') : tag('plain', '', '달라짐')); };
    const gateRows = [h('tr', null, h('th', {scope: 'row', text: '심사 유형'}), h('td', {text: p.uw.old.join(' ')}), h('td', {text: p.uw.new.join(' ')}), changeCell(p.uw.old, p.uw.new))]
      .concat(p.gate.map(function (g) {
        return h('tr', null, h('th', {scope: 'row', text: gateLabel[g.field] || g.field}),
          h('td', {text: gateValue(g.field, g.old)}), h('td', {text: gateValue(g.field, g.new)}), changeCell(g.old, g.new));
      }))
      .concat([h('tr', null, h('th', {scope: 'row', text: '주계약 가입 나이(' + sexText(state.sex) + ')'}),
        h('td', {text: segsText(p.ages.old[state.sex])}), h('td', {text: segsText(p.ages.new[state.sex])}),
        changeCell(p.ages.old[state.sex], p.ages.new[state.sex]))]);

    return screen('개정 전후 비교',
      '값이 달라진 급부 ' + changedBenefits + '줄, 없어진 특약 ' + p.removedRiders.length + '개, 새로 생긴 특약 ' + p.addedRiders.length + '개, 달라진 곳이 없는 특약 ' + p.sameRiders + '개입니다.',
      select,
      block('출시·판매중지 시간선', timeline()),
      block('달라진 급부 값', rows.length ? scrollBox(diffTable, '개정 전후로 달라진 급부 값') : h('p', {class: 'empty', text: '이어진 특약에서 달라진 값이 없습니다.'}),
        h('p', {class: 'note', text: '특약은 특약계보키로 잇고, 급부는 이름이 같은 것끼리 먼저, 남은 것은 이름이 비슷한 것끼리 이었습니다. "최대 가입 시 지급액"은 나이 조건 없이 특약의 최대 가입금액으로 계산했습니다.'})),
      block('없어진 특약 ' + p.removedRiders.length + '개', p.removedRiders.length ? riderList(p.removedRiders) : h('p', {class: 'empty', text: '없습니다.'})),
      block('새로 생긴 특약 ' + p.addedRiders.length + '개', p.addedRiders.length ? riderList(p.addedRiders) : h('p', {class: 'empty', text: '없습니다.'})),
      block('고지 질문과 가입 나이', scrollBox(table(null, ['항목', '개정 전', '개정 후', '변화'], gateRows), '개정 전후 고지 질문', 620)));
  };
  /* ---------- 화면 6 ---------- */
  function resultTag(result) {
    if (result === '반려') return tag('w', '✕', result);
    if (result === '보류') return tag('p', '!', result);
    return tag('plain', '✓', result);
  }
  screens.s6 = function () {
    const S = D.s6, sum = S.summary, st = state.s6;
    const col = {};
    S.cols.forEach(function (c, i) { col[c] = i; });
    const cell = function (row, name) { return row[col[name]]; };
    const target = function (row) {
      const id = cell(row, '대상행ID');
      return [S.labels[id] || null, S.labels[id] ? h('br') : null, h('span', {class: 'mono', text: id})];
    };
    /* 찾기는 대상 이름·ID, 열, 사유, 바뀐 값에서 찾는다 */
    const hay = function (row) {
      const id = cell(row, '대상행ID');
      return norm([S.labels[id], id, cell(row, '대상열'), cell(row, '사유'), cell(row, '변경전값'), cell(row, '변경후값')].join(' '));
    };
    const stepTable = table(null, ['작업단계'].concat(['통과', '반려', '보류', '합계'].map(rcol)),
      sum.byStep.map(function (s) {
        return h('tr', null, h('th', {scope: 'row', text: s.step}), h('td', {class: 'r num', text: C.comma(s['통과'])}),
          h('td', {class: 'r num', text: C.comma(s['반려'])}), h('td', {class: 'r num', text: C.comma(s['보류'])}), h('td', {class: 'r num', text: C.comma(s.total)}));
      }));
    const modelTable = table(null, ['호출 모델', rcol('기록 수')], sum.byModel.map(function (m) {
      return h('tr', null, h('th', {scope: 'row', text: m.model || '코드(모델 호출 없음)'}), h('td', {class: 'r num', text: C.comma(m.n)}));
    }));

    /* 사람 검토로 넘긴 목록: 지금 상태별 건수를 먼저 보여 주고, 목록은 접어 두되 상태·대상탭·이름으로 찾을 수 있게 한다 */
    const rv = st.review;
    const reviewTabs = uniq(sum.review.rows.map(function (i) { return cell(S.rows[i], '대상탭'); })).sort();
    const reviewList = function () {
      return listPanel({
        key: 's6-review', st: rv, size: LIST_SIZE, unit: '건', empty: '조건에 맞는 기록이 없습니다.',
        controls: function (redraw) {
          return [
            pickField('s6-review-status', '지금 상태', sum.review.byStatus.map(function (x) { return {value: x[0], label: x[0] + ' (' + C.comma(x[1]) + ')'}; }), rv, 'status', redraw),
            pickField('s6-review-tab', '대상탭', reviewTabs.map(function (t) { return {value: t, label: t}; }), rv, 'tab', redraw),
            searchField('s6-review-q', '대상 이름·사유', rv, redraw)
          ];
        },
        items: function () {
          const q = norm(rv.q);
          const out = [];
          sum.review.rows.forEach(function (i, n) {
            const row = S.rows[i], now = sum.review.status[n];
            if ((!rv.status || now === rv.status) && (!rv.tab || cell(row, '대상탭') === rv.tab) && (!q || hay(row).indexOf(q) >= 0)) out.push({row: row, now: now});
          });
          return out;
        },
        draw: function (slice) {
          return scrollBox(table('log', ['실행일시', '대상', '확인할 열', rcol('판정확률'), '지금 상태', '사유'], slice.map(function (x) {
            const row = x.row;
            return h('tr', null, h('td', {class: 'num', text: when(cell(row, '실행일시'))}),
              h('td', null, h('span', {class: 'sub', text: cell(row, '대상탭')}), h('br'), target(row)),
              h('td', {text: orNone(cell(row, '대상열'))}), h('td', {class: 'r num', text: prob(cell(row, '판정확률'))}),
              h('td', null, x.now.indexOf('대기') >= 0 ? pendTag(x.now) : x.now), h('td', {text: cell(row, '사유') || ''}));
          })), '사람 검토로 넘긴 목록', 980);
        }
      });
    };
    const statusTable = table(null, ['지금 상태', rcol('건수')], sum.review.byStatus.map(function (x) {
      return h('tr', null, h('th', {scope: 'row'}, x[0].indexOf('대기') >= 0 ? pendTag(x[0]) : x[0]), h('td', {class: 'r num', text: C.comma(x[1])}));
    }));

    /* 전체 기록: 최근 것부터 한 쪽씩 */
    const lg = st.log;
    const logList = listPanel({
      key: 's6-log', st: lg, size: LIST_SIZE, unit: '건', empty: '조건에 맞는 기록이 없습니다.',
      controls: function (redraw) {
        const opts = function (list) { return list.map(function (x) { return {value: x, label: x}; }); };
        return [
          pickField('s6-tab', '대상탭', opts(sum.tabs), lg, 'tab', redraw),
          pickField('s6-step', '작업단계', opts(sum.steps), lg, 'step', redraw),
          pickField('s6-result', '결과', opts(sum.results), lg, 'result', redraw),
          searchField('s6-q', '대상 이름·사유', lg, redraw)
        ];
      },
      items: function () {
        const q = norm(lg.q);
        return S.rows.filter(function (row) {
          return (!lg.tab || cell(row, '대상탭') === lg.tab) && (!lg.step || cell(row, '작업단계') === lg.step)
            && (!lg.result || cell(row, '결과') === lg.result) && (!q || hay(row).indexOf(q) >= 0);
        });
      },
      draw: function (slice) {
        return scrollBox(table('log', ['실행일시', '단계', '결과', '대상', '열', '모델', rcol('판정확률'), '변경 전 → 후', '사유'],
          slice.map(function (row) {
            const before = cell(row, '변경전값'), after = cell(row, '변경후값');
            return h('tr', null, h('td', {class: 'num', text: when(cell(row, '실행일시'))}), h('td', {class: 'nw', text: cell(row, '작업단계')}),
              h('td', null, resultTag(cell(row, '결과'))),
              h('td', null, h('span', {class: 'sub', text: cell(row, '대상탭')}), h('br'), target(row)),
              h('td', {class: 'words', text: cell(row, '대상열') || ''}), h('td', {class: 'nw', text: cell(row, '호출모델') || '코드'}),
              h('td', {class: 'r num', text: cell(row, '판정확률') === null ? '' : prob(cell(row, '판정확률'))}),
              h('td', {text: before || after ? (before || '없음') + ' → ' + (after || '없음') : ''}),
              h('td', {text: cell(row, '사유') || ''}));
          })), '작업 기록', 1180);
      }
    });

    return screen('AI 작업 내역',
      '추출·코드 대조·판정·재추출·사람 검토 이관 기록 ' + C.comma(sum.total) + '건입니다(실행 ' + sum.runs + '회). 판정확률은 판정 전용 모델이 매긴 값입니다.',
      block('요약',
        h('div', {class: 'tiles'},
          tile('전체 기록', C.comma(sum.total) + '건', '실행 ' + sum.runs + '회'),
          tile('재추출한 값으로 바꾼 건', sum.retry.adopted + '건', '앞선 값 유지 ' + sum.retry.kept + '건 · 호출 실패 등 ' + sum.retry.failed + '건'),
          tile('사람 검토로 넘긴 건', C.comma(sum.review.count) + '건', '대상 ' + C.comma(sum.review.targets) + '개(같은 대상을 다시 넘긴 기록 포함)'))),
      block('단계별 통과·반려·보류', scrollBox(stepTable, '단계별 결과 건수', 330)),
      block('모델별 호출 기록 수', scrollBox(modelTable, '모델별 기록 수', 300)),
      block('사람 검토로 넘긴 목록 ' + C.comma(sum.review.count) + '건',
        sum.review.count ? [scrollBox(statusTable, '사람 검토로 넘긴 기록의 지금 상태', 300),
          fold('s6-review', '목록 보기 · 지금 상태, 대상탭, 이름으로 찾기 (' + C.comma(sum.review.count) + '건)', reviewList)]
          : h('p', {class: 'empty', text: '사람 검토로 넘긴 기록이 없습니다.'})),
      block('전체 기록 ' + C.comma(sum.total) + '건', logList,
        h('p', {class: 'note', text: '기록은 하나도 빼지 않고 모두 실었습니다. 최근 것부터 ' + LIST_SIZE + '건씩 보여 주며, 대상탭·작업단계·결과로 거르거나 대상 이름과 사유로 찾을 수 있습니다.'})));
  };

  /* ---------- 시작 ---------- */
  function fromHash() {
    const id = location.hash.replace('#', '');
    return TABS.some(function (t) { return t.id === id; }) ? id : null;
  }
  window.addEventListener('hashchange', function () {
    const id = fromHash();
    if (id && id !== state.tab) go(id);
  });
  renderFacts();
  go(fromHash() || 's1');
})();
