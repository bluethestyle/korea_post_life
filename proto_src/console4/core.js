/* 시안 4 공통 실행부. 상태, 탭 등록, 조건 줄, 범위 띠, 근거 기둥, 고르기, 글 도우미, 그림 부품, 복사와 인쇄, 브라우저 기록.
   규약은 API.md 에 있다. 탭 파일(tabN.js)은 window.App 만 쓴다. */
(function () {
  'use strict';

  // ---------- 자료 ----------
  // 자료의 글은 읽어 들인 뒤 한 번 괄호 뒤 조사를 바로잡는다(아래 fixDeep, R2)
  const S = JSON.parse(document.getElementById('sales-data').textContent);
  const DD = (typeof D !== 'undefined') ? D : null; // 시안 3의 자료 줄(const D). 담보 비교표와 관계 그림용

  const TAB_IDS = ['brief', 'market', 'gate', 'cover', 'insight'];
  const TAB_NAME = Object.fromEntries(TAB_IDS.map((id, i) => [id, S['탭'][i]]));
  const TAB_BY_NAME = Object.fromEntries(TAB_IDS.map((id, i) => [S['탭'][i], id]));
  const ORG_ORDER = ['EPOST', 'HANWHALIFE', 'SAMSUNGFIRE'];
  const ORG_NAME = {};
  for (const v of Object.values(S['종형'])) ORG_NAME[v['기관코드']] = v['회사'];
  const ORG_SHORT = { EPOST: '우체국', HANWHALIFE: ORG_NAME.HANWHALIFE || '한화생명', SAMSUNGFIRE: ORG_NAME.SAMSUNGFIRE || '삼성화재' };
  if (DD && Array.isArray(DD.orgs)) for (const o of DD.orgs) if (o.code && o.short) ORG_SHORT[o.code] = o.short;
  const BASES = S['기준종형'];
  const MAP_KEY = { null: '전체', '갱신': '갱신', '비갱신': '비갱신' };
  const REF = S['기준조건']; // 브리핑과 기준별 값을 계산한 대표 조건

  // ---------- 작은 도구 ----------
  const $ = (q, r = document) => r.querySelector(q);
  const $$ = (q, r = document) => Array.from(r.querySelectorAll(q));
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  const fmt = n => (n == null || n === '' ? '' : (typeof n === 'number' ? n.toLocaleString('ko-KR') : String(n)));
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 저장소를 못 쓰는 창 */ } },
  };
  const LS_SKIN = 'postlife-c4-skin', LS_MOTION = 'postlife-c4-motion';

  // ---------- 글 도우미 (R1 이름 줄이기, R2 조사, R3 요약) ----------
  /** 조사를 고를 낱말의 끝. 끝에 붙은 괄호 묶음(겹친 괄호 포함)과 따옴표를 지운다.
      "3종(간편가입355)" → "3종", "진단비(통합)" → "진단비". 조사는 괄호 앞 낱말에 맞춘다 */
  const CLOSE = { ')': '(', ']': '[', '}': '{' };
  function stemOf(word) {
    let s = String(word == null ? '' : word).trimEnd();
    for (let guard = 0; guard < 8; guard++) {
      s = s.replace(/[\s'"’”」』]+$/, '');
      const cl = s[s.length - 1];
      if (!(cl in CLOSE)) break;
      let depth = 0, i = s.length - 1;
      for (; i >= 0; i--) { if (s[i] === cl) depth++; else if (s[i] === CLOSE[cl] && --depth === 0) break; }
      if (i <= 0) { s = s.replace(/[)\]}\s]+$/, ''); break; } // 짝이 없거나 글 전체가 괄호
      s = s.slice(0, i).trimEnd();
    }
    return s;
  }
  function hasFinal(word) {
    const s = stemOf(word);
    if (!s) return false;
    const c = s[s.length - 1], code = c.charCodeAt(0);
    if (code >= 0xAC00 && code <= 0xD7A3) return (code - 0xAC00) % 28 !== 0;
    if (/[0-9]/.test(c)) return '013678'.includes(c);
    if (/[A-Za-z]/.test(c)) return 'LMNRlmnr'.includes(c);
    return false;
  }
  function rieulFinal(word) {
    const s = stemOf(word);
    const c = s[s.length - 1]; if (!c) return false;
    const code = c.charCodeAt(0);
    if (code >= 0xAC00 && code <= 0xD7A3) return (code - 0xAC00) % 28 === 8;
    return c === '1' || c === '7' || c === '8' || /[lL]/.test(c);
  }
  const JOSA = { '은': ['은', '는'], '는': ['은', '는'], '이': ['이', '가'], '가': ['이', '가'], '을': ['을', '를'], '를': ['을', '를'],
    '과': ['과', '와'], '와': ['과', '와'], '이나': ['이나', '나'], '나': ['이나', '나'], '이며': ['이며', '며'], '이고': ['이고', '고'],
    '이다': ['이다', '다'], '이에요': ['이에요', '예요'], '아': ['아', '야'], '으로': ['으로', '로'], '로': ['으로', '로'] };
  /** 받침에 따라 조사를 고른다. josa('한화생명', '과') → '한화생명과', josa('삼성화재', '와') → '삼성화재와' */
  function josa(word, particle) {
    const p = JOSA[particle];
    if (!p) return String(word) + particle;
    if (p[0] === '으로') return String(word) + (hasFinal(word) && !rieulFinal(word) ? '으로' : '로');
    return String(word) + (hasFinal(word) ? p[0] : p[1]);
  }
  /** 자료 문장에서 괄호 뒤 조사를 괄호 앞 낱말에 맞춘다(R2). "진단비(통합)이" → "진단비(통합)가".
      sales.py 가 괄호 안 글자로 조사를 고른 문장을 화면에서 바로잡는다. 값과 낱말은 바꾸지 않는다 */
  const JOSA_FIX_RE = /([\uAC00-\uD7A3A-Za-z0-9])((?:\((?:[^()]|\([^()]*\))*\))+)(으로|이나|이며|이고|은|는|이|가|을|를|과|와|로|나|며|고)(?=[\s,.;:!?)」』"'”’]|$)/g;
  const JOSA_KEY = { '으로': '으로', '로': '으로', '이나': '이나', '나': '이나', '이며': '이며', '며': '이며', '이고': '이고', '고': '이고',
    '은': '은', '는': '은', '이': '이', '가': '이', '을': '을', '를': '을', '과': '과', '와': '과' };
  function fixJosa(text) {
    if (typeof text !== 'string' || text.indexOf(')') < 0) return text;
    return text.replace(JOSA_FIX_RE, (m, c, br, pa) => c + br + josa(c, JOSA_KEY[pa]).slice(c.length));
  }
  /** 자료 전체의 글에 fixJosa 를 건다(읽어 들일 때 한 번) */
  function fixDeep(v) {
    if (typeof v === 'string') return fixJosa(v);
    if (Array.isArray(v)) { for (let i = 0; i < v.length; i++) v[i] = fixDeep(v[i]); return v; }
    if (v && typeof v === 'object') { for (const k of Object.keys(v)) v[k] = fixDeep(v[k]); return v; }
    return v;
  }
  fixDeep(S);
  /** 겹친 괄호를 안쪽부터 지운다. 짝이 안 맞는 괄호가 남으면 원문을 돌려준다(R1).
      opts.brackets 가 참이면 [ ] 도 지운다. 돌려주는 값: { short, full, changed } */
  function shortName(name, opts = {}) {
    const full = String(name == null ? '' : name);
    let s = full, prev;
    const re = opts.brackets ? /\([^()\[\]]*\)|\[[^()\[\]]*\]/g : /\([^()]*\)/g;
    do { prev = s; s = s.replace(re, ''); } while (s !== prev);
    s = s.replace(/\s{2,}/g, ' ').trim();
    const bad = /[()]/.test(s) || (opts.brackets && /[\[\]]/.test(s)) || !s;
    const short = bad ? full : s;
    return { short, full, changed: short !== full };
  }
  /** 회사별 값 요약(R3). vals: {EPOST:값|null, ...}. 값이 없는 회사가 끼면 값이 있는 회사만 말한다 */
  function sameSummary(vals, eq = (a, b) => a === b) {
    const have = ORG_ORDER.filter(o => vals[o] != null && vals[o] !== '');
    const all = ORG_ORDER.filter(o => o in vals);
    if (have.length < 2) return have.length ? `${ORG_SHORT[have[0]]}만 값이 있음` : '값이 있는 회사 없음';
    const same = have.every(o => eq(vals[o], vals[have[0]]));
    if (!same) return '회사마다 다름';
    if (have.length === all.length) return `${all.length === 3 ? '세' : '두'} 회사 같음`;
    return `값이 있는 ${have.length === 2 ? '두' : '세'} 회사 같음`;
  }
  const orgShort = code => ORG_SHORT[code] || code;
  const vinfo = vid => S['종형'][vid] || null;
  const vname = vid => (vinfo(vid) ? vinfo(vid)['이름'] : vid);
  const vkind = vid => (vinfo(vid) ? vinfo(vid)['종형명'] : vid);
  const sinceText = since => {
    if (since == null) return '이력 없음';
    const row = (S['지도']['전체']['행'] || []).find(r => r['종류'] === '입원' && r.since === since);
    if (!row) return `${since}년 전`;
    return since === 5 ? '5년 넘음' : row['이름'].replace(/^입원\s*/, '');
  };
  const sexText = s => (s === 'F' ? '여성' : '남성');
  /** R8: 자료 없음의 까닭 */
  function stateWhy(org, state) {
    const n = orgShort(org);
    if (state === '나이 자료 없음') return `나이 자료 없음: ${n}의 가입나이 자료가 아직 들어오지 않았습니다`;
    if (state === '질문 자료 없음') return `질문 자료 없음: ${n}의 고지 질문 자료가 아직 들어오지 않았습니다`;
    return '';
  }

  // ---------- 상태 ----------
  const st = {
    tab: 'brief',
    age: REF['나이'] || 50,
    sex: REF['성별'] || 'M',
    since: REF['이력'] == null ? null : REF['이력'],
    surg: false,
    base: BASES[0]['종형ID'],
    renewal: null,
    sel: {},
    skin: 'light',
    motion: 'on',
  };
  const listeners = { change: [], tab: [], select: [] };
  const tabs = {}; // id → 탭 정의
  let booted = false;

  function mapOf(renewal) { return S['지도'][MAP_KEY[renewal]] || S['지도']['전체']; }
  /** 조건에서 고객군 지도의 칸을 찾는다 */
  function cellOf(s = st) {
    const m = mapOf(s.renewal);
    const kind = (s.since != null && s.surg) ? '수술만' : '입원';
    const since = s.since == null ? 5 : s.since;
    const ri = m['행'].findIndex(r => r['종류'] === kind && r.since === since);
    const ci = m['열'].findIndex(c => s.age >= c.lo && s.age <= c.hi);
    const lo = m['열'][0].lo, hi = m['열'][m['열'].length - 1].hi;
    const out = { map: m, ri, ci, row: m['행'][ri] || null, col: m['열'][ci] || null, cell: null, reason: '', sexNote: '' };
    if (ci < 0) out.reason = `나이 자료 없음: 고객군 지도는 ${lo}~${hi}세만 계산했습니다`;
    else if (ri < 0) out.reason = '이력 자료 없음: 이 이력의 칸이 지도에 없습니다';
    else out.cell = m['칸'][ri][ci];
    if (s.sex !== m['성별']) out.sexNote = `${sexText(s.sex)} 지도 자료 없음: 고객군 지도는 ${sexText(m['성별'])} 기준으로만 계산해 ${sexText(m['성별'])} 칸을 보입니다`;
    return out;
  }
  /** 지금 나이와 성별에서 기준 종형의 주계약 최대 가입금액(한도표) */
  function limitOf(s = st) {
    const t = (S['한도표'] || []).find(x => x['종형ID'] === s.base);
    if (!t) return null;
    const seg = (t['구간'][s.sex] || []);
    const hit = seg.find(g => s.age >= g.lo && s.age <= g.hi);
    const lo = seg.length ? seg[0].lo : null, hi = seg.length ? seg[seg.length - 1].hi : null;
    return { table: t, hit: hit || null, lo, hi };
  }
  function ctx(changed) {
    const base = S['기준별'][st.base];
    return {
      S, D: DD, st: { ...st, sel: { ...st.sel } }, changed: changed || new Set(),
      baseId: st.base, base, baseInfo: vinfo(st.base),
      peerIds: base ? base['맞붙는종형'] : [], peers: base ? base['맞붙는종형'].map(vinfo) : [],
      seg: cellOf(), limit: limitOf(), ref: REF, isRef: isRefCond(),
      ui: UI, txt: TXT,
    };
  }
  const isRefCond = () => st.age === REF['나이'] && st.sex === REF['성별'] && st.since === REF['이력'] && !st.surg;

  /** 상태를 바꾸고 알린다. opts.push: 브라우저 기록에 남길지(기본 참) */
  function set(patch, opts = {}) {
    const changed = new Set();
    for (const [k, v] of Object.entries(patch)) {
      if (!(k in st)) continue;
      if (JSON.stringify(st[k]) !== JSON.stringify(v)) { st[k] = v; changed.add(k); }
    }
    if (!changed.size) return;
    if (changed.has('since') && st.since == null && st.surg) { st.surg = false; changed.add('surg'); }
    if (changed.has('skin')) applySkin();
    if (changed.has('motion')) applyMotion();
    const group = groupOf(changed);
    if (opts.push !== false && booted && (group.cond || group.base || group.renewal || changed.has('tab'))) pushHistory(changed);
    if (changed.has('tab')) showTab(st.tab, opts);
    if (group.cond || group.base || group.renewal) notify(changed);
  }
  function groupOf(c) {
    return { cond: ['age', 'sex', 'since', 'surg'].some(k => c.has(k)), base: c.has('base'), renewal: c.has('renewal') };
  }
  function on(ev, fn) { (listeners[ev] = listeners[ev] || []).push(fn); }
  function emit(ev, ...a) { for (const fn of (listeners[ev] || [])) { try { fn(...a); } catch (e) { console.error(e); } } }

  // ---------- 브라우저 기록 (#t=brief&a=50&s=M&h=-&o=0&b=...&r=-) ----------
  function encodeHash() {
    const p = new URLSearchParams();
    p.set('t', st.tab); p.set('a', String(st.age)); p.set('s', st.sex);
    p.set('h', st.since == null ? '-' : String(st.since)); p.set('o', st.surg ? '1' : '0');
    p.set('b', st.base); p.set('r', st.renewal || '-');
    return '#' + p.toString();
  }
  function decodeHash(h) {
    const p = new URLSearchParams(String(h || '').replace(/^#/, ''));
    const out = {};
    if (TAB_IDS.includes(p.get('t'))) out.tab = p.get('t');
    const a = parseInt(p.get('a'), 10); if (a >= 1 && a <= 100) out.age = a;
    if (p.get('s') === 'M' || p.get('s') === 'F') out.sex = p.get('s');
    if (p.has('h')) { const hv = p.get('h'); if (hv === '-') out.since = null; else { const n = parseFloat(hv); if (SINCE_OPTS.some(o => o.v === n)) out.since = n; } }
    if (p.has('o')) out.surg = p.get('o') === '1';
    if (BASES.some(b => b['종형ID'] === p.get('b'))) out.base = p.get('b');
    if (p.has('r')) { const r = p.get('r'); out.renewal = r === '-' ? null : (r === '갱신' || r === '비갱신' ? r : null); }
    return out;
  }
  let lastPush = { t: 0, k: '' };
  function pushHistory(changed) {
    const kind = [...changed].sort().join(',');
    const now = Date.now();
    const url = encodeHash();
    const rapid = now - lastPush.t < 900 && lastPush.k === kind && !changed.has('tab');
    try {
      if (rapid) history.replaceState({ c4: 1 }, '', url); else history.pushState({ c4: 1 }, '', url);
    } catch (e) { /* file: 에서 막히는 브라우저 */ }
    lastPush = { t: now, k: kind };
  }
  window.addEventListener('popstate', e => {
    const want = decodeHash(location.hash);
    if (EV.open && !(e.state && e.state.ev)) hideEv(true);
    set(want, { push: false });
  });

  // ---------- 화면 모드 ----------
  const mode = () => (innerWidth >= 1600 ? 'wide' : innerWidth >= 1000 ? 'push' : 'sheet');
  const motionOn = () => st.motion === 'on';

  // ---------- 그림 부품 ----------
  const IC = {
    chevR: '<svg width="8" height="14" viewBox="0 0 8 14" aria-hidden="true"><path d="M1.2 1.2L6.8 7l-5.6 5.8" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>',
    chevL: '<svg width="8" height="14" viewBox="0 0 8 14" aria-hidden="true"><path d="M6.8 1.2L1.2 7l5.6 5.8" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>',
    chevD: '<svg width="12" height="8" viewBox="0 0 12 8" aria-hidden="true"><path d="M1 1.2l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>',
    better: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 .8L9.6 9.2H.4Z" fill="currentColor"/></svg>',
    only: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 .4L9.6 5 5 9.6.4 5Z" fill="currentColor"/></svg>',
    worse: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M.4 .8H9.6L5 9.2Z" fill="currentColor"/></svg>',
    same: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1 3.4h8M1 6.6h8" stroke="currentColor" stroke-width="1.6"/></svg>',
    diff: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1 3h7.2M6 1l2.2 2L6 5M9 7H1.8M4 5 1.8 7 4 9" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>',
    none: '<svg viewBox="0 0 10 10" aria-hidden="true"><rect x=".8" y=".8" width="8.4" height="8.4" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="1.6 1.4"/><path d="M2.4 5h5.2" stroke="currentColor" stroke-width="1.4"/></svg>',
    unknown: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M3 3.4C3 2 4 1.2 5.1 1.2 6.3 1.2 7.1 2 7.1 3c0 1.6-2.1 1.6-2.1 3.3" fill="none" stroke="currentColor" stroke-width="1.4"/><rect x="4.3" y="7.6" width="1.4" height="1.4" fill="currentColor"/></svg>',
    lock: '<svg width="12" height="14" viewBox="0 0 12 14" aria-hidden="true"><path d="M3 6V4a3 3 0 0 1 6 0v2" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="1" y="6" width="10" height="7.2" fill="currentColor"/></svg>',
    copy: '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><rect x="4" y="4" width="9" height="9" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M1 10V1h9" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>',
    print: '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M3.5 5V1h7v4M3.5 10.5H1V5h12v5.5h-2.5" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="3.5" y="8" width="7" height="5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>',
    grid: '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true"><path d="M0 0h3v3H0zM4 0h3v3H4zM8 0h3v3H8zM0 4h3v3H0zM4 4h3v3H4zM8 4h3v3H8zM0 8h3v3H0zM4 8h3v3H4zM8 8h3v3H8z" fill="currentColor"/></svg>',
    pin: '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true"><rect x=".75" y=".75" width="9.5" height="9.5" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="3.5" y="3.5" width="4" height="4" fill="currentColor"/></svg>',
    open: '<svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><rect x=".75" y=".75" width="8.5" height="8.5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>',
    check: '<svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><rect x=".75" y=".75" width="8.5" height="8.5" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="1.6 1.3"/></svg>',
    hatch: '<svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><rect x=".5" y=".5" width="9" height="9" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="1.6 1.3"/><path d="M0 7 7 0M3 10 10 3" stroke="currentColor" stroke-width="1"/></svg>',
    arrow: '<svg width="14" height="10" viewBox="0 0 14 10" aria-hidden="true"><path d="M0 5h12M8.5 1.2 12.3 5 8.5 8.8" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
    now: '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true"><circle cx="5.5" cy="5.5" r="4.6" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="5.5" cy="5.5" r="1.9" fill="currentColor"/></svg>',
  };

  const VD = {
    better: ['vd-better', '우체국 나음'],
    only: ['vd-only', '우체국에만 있음'],
    worse: ['vd-worse', '우체국 못함'],
    same: ['vd-same', '같음'],
    diff: ['vd-diff', '우열을 매기지 않음'],
    none: ['vd-none', '우체국에 없음'],
    unknown: ['vd-unknown', '모름'],
  };
  /** 판정 칩(S9, R4). kind: better|only|worse|same|diff|none|unknown. text 를 주면 바꿔 쓴다(주어를 빼지 않는다) */
  function verdict(kind, text, title) {
    const v = VD[kind] || VD.unknown;
    return `<span class="vd ${v[0]}"${title ? ` title="${esc(title)}"` : ''}>${IC[kind] || ''}<span>${esc(text || v[1])}</span></span>`;
  }
  const FLAG_TEXT = '사업방법서 원문 확인 필요';
  /** 원문 확인 표식: 부모(position:relative)의 왼쪽 위 모서리에 붙는 16x16 빨간 직각삼각형 */
  const flag = (text = FLAG_TEXT) => `<span class="flag" role="img" aria-label="${esc(text)}" title="${esc(text)}"><i></i></span>`;
  /** 원문 확인 표식의 글 꼴(근거 기둥, 응대 카드) */
  const flagText = (text = FLAG_TEXT) => `<span class="flag-t"><span class="tri" aria-hidden="true"><i></i></span>${esc(text)}</span>`;
  /** 범위 배지: 'all' 전체 고객군, 'base' 선택 종형, 'now' 지금 조건(나이, 성별, 이력을 바꾸면 바뀌는 값) */
  const scope = (kind, title) => kind === 'all'
    ? `<span class="scb scb-all" title="${esc(title || '기준 종형과 조건을 바꿔도 그대로인 값')}">${IC.grid}전체 고객군</span>`
    : kind === 'now'
      ? `<span class="scb scb-now" title="${esc(title || '나이, 성별, 이력을 바꾸면 바뀌는 값')}">${IC.now}지금 조건</span>`
      : `<span class="scb scb-base" title="${esc(title || '기준 종형을 바꾸면 바뀌는 값')}">${IC.pin}선택 종형</span>`;
  const tag = (t, title, cls = '') => `<span class="tag ${cls}"${title ? ` title="${esc(title)}"` : ''}>${esc(t)}</span>`;
  /** 줄인 이름(R1). 원문은 title 에 둔다 */
  function name(full, opts = {}) {
    const r = shortName(full, opts);
    return r.changed ? `<span class="nm" title="${esc(r.full)}">${esc(r.short)}</span>` : `<span class="nm">${esc(r.full)}</span>`;
  }
  /** 제목 묶음: 상위 이름, 제목, 탭 자리 표시 */
  function title(tabId, kicker, text) {
    const i = TAB_IDS.indexOf(tabId);
    const dots = TAB_IDS.map((_, j) => `<i${j === i ? ' class="on"' : ''}></i>`).join('');
    return `<div class="ttl"><div class="ttl-k">${esc(kicker)}</div><h1 class="ttl-t">${esc(text || TAB_NAME[tabId])}</h1>
      <div class="ttl-i" role="img" aria-label="다섯 탭 가운데 ${i + 1}번째">${dots}</div></div>`;
  }
  /** 큰 숫자와 분모 */
  const big = (n, d, unit) => `<span class="big"><span class="n">${esc(fmt(n))}</span>${d != null ? `<span class="d">/${esc(fmt(d))}</span>` : ''}${unit ? `<span class="u">${esc(unit)}</span>` : ''}</span>`;
  /** 진행 고리(72px). 채운 호는 실선, 못 채운 호는 방사형 잔눈금. lead 는 네 귀의 45도 사선, sel 은 빨강 원.
      segs: [{v, cls:'gold'|''}] 로 호를 나눠 칠한다. pct: 가운데 글(문자열) */
  function ring({ v = 0, max = 1, size = 72, lead = false, segs = null, pct = null, sel = false, label = '' } = {}) {
    const frac = max > 0 ? Math.max(0, Math.min(1, v / max)) : 0;
    const parts = segs || [{ v, cls: '' }];
    let acc = 0, arcs = '';
    for (const s of parts) {
      const f = max > 0 ? Math.max(0, s.v / max) : 0;
      if (f > 0) arcs += `<circle class="arc ${s.cls || ''}" r="40" fill="none" stroke-width="4.5" pathLength="100" stroke-dasharray="${(f * 100).toFixed(2)} 100" stroke-dashoffset="${(-acc * 100).toFixed(2)}" transform="rotate(-90)" data-to="${(f * 100).toFixed(2)}"/>`;
      acc += f;
    }
    let tks = '';
    for (let i = 0; i < 72; i++) {
      const a = i / 72; if (a < frac - 1e-6) continue;
      const t = a * Math.PI * 2 - Math.PI / 2, c = Math.cos(t), s = Math.sin(t);
      tks += `<line x1="${(c * 37).toFixed(2)}" y1="${(s * 37).toFixed(2)}" x2="${(c * 43).toFixed(2)}" y2="${(s * 43).toFixed(2)}"/>`;
    }
    const diag = lead || sel ? '<path class="diag" d="M-55-55l11 11M55-55l-11 11M-55 55l11-11M55 55l-11-11" stroke-width="2.2" fill="none"/>' : '';
    const disc = sel ? '<circle class="disc" r="35"/>' : '';
    const txt = pct != null ? `<text class="pct" text-anchor="middle" dominant-baseline="central" y="1">${esc(pct)}</text>` : '';
    return `<svg class="ring${sel ? ' sel' : ''}${lead ? ' lead' : ''}" width="${size}" height="${size}" viewBox="-60 -60 120 120" role="img" aria-label="${esc(label)}">
      <circle class="trk" r="40" fill="none" stroke-width="1"/>${disc}<g class="tks" stroke-width="1.6">${tks}</g>${arcs}${diag}${txt}</svg>`;
  }
  /** 고리를 0에서 채운다(600ms). 움직임이 꺼져 있으면 아무것도 하지 않는다 */
  function drawRings(root) {
    if (!motionOn()) return;
    const arcs = $$('.ring .arc', root);
    arcs.forEach(a => { a.style.transition = 'none'; a.style.strokeDasharray = '0 100'; });
    void root.getBoundingClientRect();
    requestAnimationFrame(() => requestAnimationFrame(() => arcs.forEach(a => { a.style.transition = ''; a.style.strokeDasharray = `${a.dataset.to} 100`; })));
  }
  /** 6px 수평 막대 */
  const hbar = (v, max, cls = '') => `<span class="hbar" role="img" aria-label="${esc(fmt(v))}/${esc(fmt(max))}"><i class="${cls}" style="width:${max > 0 ? Math.max(0, Math.min(100, v / max * 100)).toFixed(1) : 0}%"></i></span>`;
  /** 흰 칩 단추. o.main 은 왼쪽 4px 빨강 막대, o.sm 작은 단추, o.ghost 테두리만. o.attrs 는 그대로 붙인다 */
  const btn = (text, o = {}) => `<button type="button" class="btn${o.main ? ' btn-main' : ''}${o.sm ? ' sm' : ''}${o.ghost ? ' ghost' : ''}${o.cls ? ' ' + o.cls : ''}" ${o.attrs || ''}>${o.icon ? IC[o.icon] || '' : ''}<span>${esc(text)}</span>${o.chev ? IC.chevR : ''}</button>`;
  /** 줄무늬 없는 표. head: 머리글 배열, rows: 칸 배열의 배열(칸은 HTML 문자열), num: 오른쪽 맞춤할 열 번호 */
  function table({ id = '', head = [], rows = [], num = [], caption = '', pick = null } = {}) {
    const th = head.map((h, i) => `<th scope="col"${num.includes(i) ? ' class="v"' : ''}>${h}</th>`).join('');
    const tr = rows.map((r, ri) => {
      const k = pick ? pick(ri) : null;
      return `<tr${k != null ? ` class="pick" data-pick="${esc(k)}" tabindex="0"` : ''}>${r.map((c, i) => `<td${num.includes(i) ? ' class="v"' : ''}>${c}${k != null && i === r.length - 1 ? RCHEV : ''}</td>`).join('')}</tr>`;
    }).join('');
    return `<table class="tbl"${id ? ` id="${esc(id)}"` : ''}>${caption ? `<caption>${caption}</caption>` : ''}<thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>`;
  }
  /** 눌리는 표 행의 오른쪽 끝 ›(R6). 행의 마지막 칸 안에 둔다 */
  const RCHEV = `<span class="rchev" aria-hidden="true">${IC.chevR}</span>`;
  const TERMS = {
    'scope-band': {
      title: '범위 띠',
      body: '위쪽 줄은 지금 고른 기준 종형과 맞붙는 상대 상품, 공통 담보 쌍의 수를 보여 줍니다. 아래쪽 줄은 조건 줄의 나이, 성별, 이력이 고객군 지도에서 어느 관문 칸에 해당하는지 보여 줍니다.',
    },
    'ev-panel': {
      title: '관계와 근거 패널',
      body: '본문에서 칸이나 줄을 누르면 그 항목의 종형, 특약, 급부, 표준담보 연결 관계와 원문 문서 쪽 번호를 이 영역에 펼쳐 보여 줍니다. 아무것도 고르지 않았을 때는 지금 탭을 읽는 법과 판정 기호 풀이를 보여 줍니다.',
    },
    'base-sel': {
      title: '기준 종형과 선택 종형',
      body: '기준 종형은 조건 줄에서 고른 우체국 상품 종형이며, 비교 상대는 그 종형의 심사 유형과 갱신 구조에 맞춰 정해집니다. 선택 종형 배지가 붙은 숫자와 문장은 이 기준 종형을 바꿀 때 함께 다시 계산하는 값입니다.',
    },
    'journey-grid': {
      title: '치료 여정 격자',
      body: '암, 뇌혈관, 심장 같은 보장 대분류와 진단, 수술, 치료, 입원, 통원의 다섯 단계가 만나는 칸마다 회사별 표준담보 수를 막대로 견준 표입니다. 빈 단계나 담보 수 차이를 한눈에 살피는 용도이며, 조건의 우열은 아래 담보 비교표에서 따집니다.',
    },
    'caution-pending': {
      title: '단정 주의와 검토 대기',
      body: '단정 주의는 상대가 조건이 다른 특약을 함께 팔거나 지급 형태가 달라 우열 문장을 내지 않고 사실만 적은 담보입니다. 검토 대기는 급부의 표준담보 매핑(매핑 대기)이나 추출한 급부 줄(작업 로그 대기)을 아직 사람이 확인하지 않아 비교 계산에서 뺀 쌍입니다.',
    },
  };
  const help = (key, label) => {
    const t = TERMS[key];
    if (!t) return '';
    return `<button type="button" class="qhelp live no-print" data-help="${esc(key)}" aria-expanded="false" aria-controls="help-pop" aria-label="${esc((label || t.title) + ' 뜻 보기')}">?</button>`;
  };
  const NOTE_HEAD = { '지도전제': '지도가 보는 범위', '간편청약제한': '간편심사의 대상', '수술만행': "'수술만' 행의 뜻", '일반심사': '일반심사 규칙' };
  function notes(tabName) {
    const list = (S['주석'] || []).filter(n => Array.isArray(n['탭']) && n['탭'].includes(tabName));
    if (!list.length) return '';
    return `<div class="snotes" role="note" aria-label="${esc(tabName)} 주석"><div class="snotes-h">일러두기</div><ul class="snotes-l">${list.map(n => {
      const hd = NOTE_HEAD[n['열쇠']] || '';
      return `<li>${hd ? `<b>${esc(hd)}.</b>` : ''}${esc(n['글'])}${n['출처'] ? `<span class="snotes-src">(출처: ${esc(n['출처'])})</span>` : ''}</li>`;
    }).join('')}</ul></div>`;
  }
  /** 구역 머리: 옅은 기둥 위의 제목과, 안개 위에 바로 얹는 큰 숫자 칸(acs_05 의 18/18, acs_17 의 탭 줄).
      stats: [{n, d, u, l, bar:[v, max, cls], title}] 큰 숫자, 분모, 단위, 이름표, 6px 막대. eq 는 칸 아래 관계 식(R5) */
  function band({ id = '', kicker = '', title: t = '', help: hKey = '', sc = '', stats = [], eq: eqHtml = '', note = '' } = {}) {
    const st = stats.map(s => `<div class="sb-st"${s.title ? ` title="${esc(s.title)}"` : ''}>
        <span class="big"><span class="n">${esc(fmt(s.n))}</span>${s.d != null ? `<span class="d">/${esc(fmt(s.d))}</span>` : ''}${s.u ? `<span class="u">${esc(s.u)}</span>` : ''}</span>
        <span class="sb-l">${esc(s.l)}</span>${s.bar ? hbar(s.bar[0], s.bar[1], s.bar[2] || '') : ''}</div>`).join('');
    return `<div class="sband"${id ? ` id="${esc(id)}"` : ''}>
      <div class="sb-t pillar tl"><i class="sb-tk" aria-hidden="true"></i><span class="k">${(Array.isArray(sc) ? sc : [sc]).filter(Boolean).map(x => scope(x)).join('')}${kicker ? `<span>${esc(kicker)}</span>` : ''}</span><h2><span>${esc(t)}</span>${hKey ? help(hKey, t) : ''}</h2></div>
      <div class="sb-s">${st}</div>
      ${eqHtml || note ? `<div class="sb-f">${eqHtml}${note ? `<p class="note">${esc(note)}</p>` : ''}</div>` : ''}
    </div>`;
  }
  /** 관계 식(R5): 전체 = 부분 + 부분. nonAdd 는 더해지지 않는 수에 붙이는 설명 */
  function eq({ total, parts = [], tail = '', nonAdd = '' }) {
    const p = parts.map(x => `<span class="nb">${esc(x.t)}</span> <span class="n">${esc(fmt(x.n))}</span>`).join(' <span class="op">+</span> ');
    return `<div class="eq">${total ? `<span class="nb">${esc(total.t)}</span> <span class="n">${esc(fmt(total.n))}</span> <span class="op">=</span> ` : ''}${p}${tail ? ` <span class="nb">${esc(tail)}</span>` : ''}</div>${nonAdd ? `<div class="nadd">${esc(nonAdd)}</div>` : ''}`;
  }
  /** 한쪽이 안개로 풀리는 띠 */
  const fadeBand = (html, o = {}) => `<div class="fade-band${o.slate ? ' slate' : ''}">${html}</div>`;
  /** 칸 띠: 칸 하나가 하나의 수다(지도 칸, 비교쌍) */
  const cells = list => `<div class="cqs" aria-hidden="true">${list.map(c => `<i class="cq ${c}"></i>`).join('')}</div>`;
  /** 지도 라벨 → 칸 클래스 */
  const MAP_CLS = { '우리 간편만 열림': 'm-only', '함께 열림': 'm-both', '우리 간편 닫힘': 'm-ours', '간편 모두 닫힘': 'm-all', '자료 없음': 'm-none' };
  const swatch = label => `<i class="cq ${MAP_CLS[label] || 'm-none'}" style="width:12px;height:12px;display:inline-block;vertical-align:-1px"></i>`;

  /** 꺾쇠 선택기 "‹ 값 ›". options: [{v, t}], onChange(v). 돌려주는 DOM 에 .set(v) 가 있다 */
  function chevSel({ label, options, value, onChange, w = '72px', num = false, id = '' }) {
    const el = document.createElement('div');
    el.className = 'chev-sel' + (num ? ' num' : '');
    el.style.setProperty('--w', w);
    el.setAttribute('role', 'group'); el.setAttribute('aria-label', label);
    if (id) el.id = id;
    el.innerHTML = `<button type="button" class="p" aria-label="${esc(label)} 앞 값">${IC.chevL}</button><span class="v" aria-live="polite"></span><button type="button" class="n" aria-label="${esc(label)} 다음 값">${IC.chevR}</button>`;
    const vEl = $('.v', el), pB = $('.p', el), nB = $('.n', el);
    let cur = value;
    const idx = () => options.findIndex(o => JSON.stringify(o.v) === JSON.stringify(cur));
    el.set = v => {
      cur = v; const i = idx(); const o = options[i];
      vEl.textContent = o ? o.t : String(v);
      if (o && o.title) vEl.title = o.title; else vEl.removeAttribute('title');
      pB.disabled = i <= 0; nB.disabled = i < 0 || i >= options.length - 1;
    };
    const move = d => { const i = idx() + d; if (i < 0 || i >= options.length) return; el.set(options[i].v); onChange && onChange(options[i].v); };
    pB.addEventListener('click', () => move(-1));
    nB.addEventListener('click', () => move(1));
    el.addEventListener('keydown', e => { if (e.key === 'ArrowLeft') { move(-1); e.preventDefault(); } if (e.key === 'ArrowRight') { move(1); e.preventDefault(); } });
    el.set(value);
    return el;
  }
  /** 숫자 입력이 든 꺾쇠 선택기(나이) */
  function stepper({ label, value, min, max, unit = '', onChange, w = '44px' }) {
    const el = document.createElement('div');
    el.className = 'chev-sel num'; el.style.setProperty('--w', w);
    el.setAttribute('role', 'group'); el.setAttribute('aria-label', label);
    el.innerHTML = `<button type="button" class="p" aria-label="${esc(label)} 하나 줄이기">${IC.chevL}</button><input type="text" inputmode="numeric" maxlength="3" aria-label="${esc(label)}" autocomplete="off"><span class="v" style="min-width:0;padding:0 6px 0 0;font:600 14px/1 var(--f-ko)">${esc(unit)}</span><button type="button" class="n" aria-label="${esc(label)} 하나 늘리기">${IC.chevR}</button>`;
    const inp = $('input', el);
    let cur = value, timer = 0;
    el.set = v => { cur = v; inp.value = String(v); $('.p', el).disabled = v <= min; $('.n', el).disabled = v >= max; };
    const commit = v => { v = Math.max(min, Math.min(max, v)); el.set(v); onChange && onChange(v); };
    $('.p', el).addEventListener('click', () => commit(cur - 1));
    $('.n', el).addEventListener('click', () => commit(cur + 1));
    inp.addEventListener('input', () => {
      inp.value = inp.value.replace(/[^0-9]/g, '');
      clearTimeout(timer);
      const n = parseInt(inp.value, 10);
      if (n >= min && n <= max) timer = setTimeout(() => commit(n), 450);
    });
    inp.addEventListener('blur', () => { const n = parseInt(inp.value, 10); if (isNaN(n)) el.set(cur); else commit(n); });
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter') { inp.blur(); }
      if (e.key === 'ArrowUp') { commit(cur + 1); e.preventDefault(); }
      if (e.key === 'ArrowDown') { commit(cur - 1); e.preventDefault(); }
    });
    el.set(value);
    return el;
  }

  /** 문서 쪽 표지의 글. 쪽 번호가 없으면 무엇이 없는지 적는다(R8) */
  const pageText = (doc, page) => (page != null && page !== '' ? `${doc || '문서'} ${page}쪽` : `${doc || '문서'}: 쪽 번호 자료 없음`);
  const PAGE_WHY = '쪽 번호 자료 없음: 고지 질문과 가입나이는 사업방법서에서 읽은 값이고, 사본에 그 쪽 번호가 들어 있지 않습니다. 원문의 해당 조항을 찾아 대조합니다';

  const UI = { esc, fmt, IC, verdict, flag, flagText, FLAG_TEXT, scope, tag, name, title, big, ring, drawRings, hbar, btn, table, RCHEV, band, eq, fadeBand, cells, MAP_CLS, swatch, chevSel, stepper, help, notes };
  const TXT = { josa, fixJosa, hasFinal, shortName, sameSummary, orgShort, vname, vkind, vinfo, sinceText, sexText, stateWhy, pageText, PAGE_WHY, ORG_ORDER, ORG_SHORT };

  // ---------- 조건 줄 ----------
  const SINCE_OPTS = [{ v: null, t: '이력 없음' }].concat(
    S['지도']['전체']['행'].filter(r => r['종류'] === '입원').map(r => ({ v: r.since, t: r.since === 5 ? '5년 넘음' : r['이름'].replace(/^입원\s*/, '') })));
  const C = {};
  function renderCond() {
    const el = $('#cond');
    el.innerHTML = `
      <button class="cond-sum" id="cond-sum" type="button" aria-expanded="false" aria-controls="cond"><span class="t"></span><span class="act">조건 바꾸기 ${IC.chevD}</span></button>
      <div class="cg" data-g="seg">
        <div class="cg-h">지금 보는 고객군</div>
        <div class="cf"><span class="lb">나이</span><span data-slot="age"></span></div>
        <div class="cf"><span class="lb">성별</span><span data-slot="sex"></span></div>
        <div class="cf"><label class="lb" for="c-since">마지막 입원이나 수술</label><select class="sel" id="c-since"></select></div>
        <div class="cf"><span class="lb" id="c-surg-l">이력의 종류</span><button type="button" class="sw" id="c-surg" role="switch" aria-checked="false" aria-describedby="c-surg-l"><i></i>입원 없이 수술만</button></div>
      </div>
      <div class="cg" data-g="base">
        <div class="cg-h">기준과 비교 상대</div>
        <div class="cf"><span class="lb">기준 종형${help('base-sel', '기준 종형과 선택 종형')}</span><span data-slot="base"></span></div>
        <div class="cf cf-peers"><span class="lb">비교 상대</span><span class="ro" id="c-peers"></span></div>
        <div class="cf"><span class="lb">갱신 유형 <span class="hint">고객군 지도에만 씁니다</span></span><span data-slot="ren"></span></div>
      </div>`;
    C.age = stepper({ label: '나이', value: st.age, min: 1, max: 100, unit: '세', onChange: v => set({ age: v }) });
    C.sex = chevSel({ label: '성별', options: [{ v: 'M', t: '남성' }, { v: 'F', t: '여성' }], value: st.sex, w: '56px', onChange: v => set({ sex: v }) });
    C.base = chevSel({ label: '기준 종형', options: BASES.map(b => ({ v: b['종형ID'], t: b['이름'], title: vinfo(b['종형ID']) ? vinfo(b['종형ID'])['전체이름'] : '' })), value: st.base, w: '150px', onChange: v => set({ base: v }) });
    C.ren = chevSel({ label: '갱신 유형', options: [{ v: null, t: '전체' }, { v: '갱신', t: '갱신' }, { v: '비갱신', t: '비갱신' }], value: st.renewal, w: '64px', onChange: v => set({ renewal: v }) });
    $('[data-slot="age"]', el).replaceWith(C.age);
    $('[data-slot="sex"]', el).replaceWith(C.sex);
    $('[data-slot="base"]', el).replaceWith(C.base);
    $('[data-slot="ren"]', el).replaceWith(C.ren);
    const sel = $('#c-since', el);
    sel.innerHTML = SINCE_OPTS.map((o, i) => `<option value="${i}">${esc(o.t)}</option>`).join('');
    sel.addEventListener('change', () => set({ since: SINCE_OPTS[+sel.value].v }));
    $('#c-surg', el).addEventListener('click', () => { if (st.since != null) set({ surg: !st.surg }); });
    $('#cond-sum', el).addEventListener('click', () => {
      const open = !el.classList.contains('open');
      el.classList.toggle('open', open); $('#cond-sum', el).setAttribute('aria-expanded', String(open));
    });
    syncCond();
  }
  function condSummary() {
    const hist = st.since == null ? '이력 없음' : `${st.surg ? '수술만' : '입원이나 수술'} ${sinceText(st.since)}`;
    return `${st.age}세 ${sexText(st.sex)}, ${hist}, 기준 ${vkind(st.base)}`;
  }
  function syncCond() {
    if (!C.age) return;
    C.age.set(st.age); C.sex.set(st.sex); C.base.set(st.base); C.ren.set(st.renewal);
    const sel = $('#c-since'); sel.value = String(SINCE_OPTS.findIndex(o => o.v === st.since));
    const sw = $('#c-surg'); sw.setAttribute('aria-checked', String(!!st.surg)); sw.disabled = st.since == null;
    sw.title = st.since == null ? '이력이 없으면 고르지 않습니다' : '고지 질문이 수술을 묻는지에 따라 회사마다 관문이 갈립니다';
    const base = S['기준별'][st.base];
    // 종형 이름은 바로 아래 범위 띠에 있으므로 여기서는 회사만 적는다
    $('#c-peers').innerHTML = base ? `<span title="${esc(base['맞붙는종형'].map(vname).join(', '))}">${esc(base['맞붙는종형'].map(v => orgShort(vinfo(v) ? vinfo(v)['기관코드'] : '')).join(', '))}</span><span class="hint" style="margin-left:8px">기준 종형에 맞춰 정해집니다</span>` : '';
    $('#cond-sum .t').textContent = condSummary();
    $('#condmini').textContent = condSummary();
  }

  // ---------- 범위 띠 ----------
  const STATE_IC = { '열림': IC.open, '닫힘': IC.lock, '심사로 확인': IC.check, '나이 자료 없음': IC.hatch, '질문 자료 없음': IC.hatch };
  function renderScope() {
    const el = $('#scope');
    const base = S['기준별'][st.base];
    if (!base) { el.innerHTML = ''; return; }
    const r = base['범위'];
    const bi = vinfo(st.base);
    const peers = r['상대'].map(p => {
      const v = vinfo(p['종형ID']);
      const why = p['머리말'] != null ? S['글'][p['머리말']] : '';
      const sd = (why.split(' / 구조 다름: ')[1] || '');
      return `<span class="it"><span title="${esc(v ? v['전체이름'] : '')}">${esc(vname(p['종형ID']))}</span> <span class="d">${esc(v ? v['적용시작일'] : '')}</span>${p['구조다름'] ? ' ' + tag('구조 다름', sd ? '구조 다름: ' + sd : '갱신이나 환급 구조가 다름') : ''}</span>`;
    }).join('');
    const line1 = `<div class="scope-l"><span class="k">범위 띠${help('scope-band', '범위 띠')}</span>
      <span class="it"><b style="font-weight:600" title="${esc(bi ? bi['전체이름'] : '')}">${esc(vname(st.base))}</b> <span class="d">${esc(bi ? bi['적용시작일'] : '')}</span></span>
      <span class="it" aria-label="대">${IC.arrow}</span>${peers}
      <span class="it">공통 담보 <b class="num" style="font-weight:600">${fmt(r['비교쌍'])}</b>쌍 가운데 검토 대기로 뺀 쌍 <b class="num" style="font-weight:600">${fmt(r['뺀비교쌍'])}</b></span>
      ${scope('base')}</div>`;
    const g = cellOf();
    let line2;
    if (!g.cell) {
      line2 = `<div class="scope-l"><span class="k">지금 고객군</span><span class="it">${esc(condSummary().split(', 기준')[0])}</span><span class="why">${esc(g.reason)}</span></div>`;
    } else {
      const c = g.cell;
      const states = ORG_ORDER.filter(o => o in c['회사']).map(o => {
        const s = c['회사'][o];
        return `<span class="it">${esc(orgShort(o))} <span style="display:inline-flex;align-items:center;gap:4px">${STATE_IC[s] || ''}${esc(s)}</span></span>`;
      }).join('');
      const why = ORG_ORDER.map(o => stateWhy(o, c['회사'][o])).filter(Boolean);
      const rep = c['대표'];
      const repT = rep ? `<span class="it">우리 대표 종형 <b style="font-weight:600">${esc(vkind(rep))}</b></span>` : '';
      const act = rep && rep !== st.base ? `<span class="act live">${btn(`기준 종형을 ${josa(vkind(rep), '으로')} 바꾸기`, { sm: true, attrs: `data-act="base-to" data-v="${esc(rep)}"` })}</span>` : '';
      const notes = [];
      if (c['보조']) notes.push(c['보조']);
      if (c['닫힌사유'] && c['닫힌사유'].length) notes.push(`닫힌 사유: ${c['닫힌사유'].join(', ')}`);
      line2 = `<div class="scope-l"><span class="k">지금 고객군</span>
        <span class="it">${esc(condSummary().split(', 기준')[0])}</span>
        <span class="it" style="display:inline-flex;align-items:center;gap:6px">${swatch(c['라벨'])}<b style="font-weight:600">${esc(c['라벨'])}</b>${notes.length ? `<span style="color:var(--ink-1)">(${esc(notes.join(', '))})</span>` : ''}</span>
        ${states}${repT}${why.concat(g.sexNote ? [g.sexNote] : []).map(w => `<span class="why">${esc(w)}</span>`).join('')}${act}</div>`;
    }
    if (!g.cell && g.sexNote) line2 += `<div class="scope-l"><span class="k">자료 없음</span><span class="why">${esc(g.sexNote)}</span></div>`;
    // 좁은 창(1600px 아래)에서는 한 줄 요약과 "자세히"로 접는다. 넓은 창은 늘 펼친다
    const nSd = r['상대'].filter(p => p['구조다름']).length;
    const sumGate = g.cell ? `${swatch(g.cell['라벨'])}<b style="font-weight:600">${esc(g.cell['라벨'])}</b>` : `<span class="why">${esc(g.reason)}</span>`;
    const sum = `<div class="scope-sum"><span class="k">범위 띠${help('scope-band', '범위 띠')}</span>
        <span class="it"><b style="font-weight:600">${esc(vkind(st.base))}</b> 대 ${esc(r['상대'].map(p => orgShort((vinfo(p['종형ID']) || {})['기관코드'] || '')).join(', '))}${nSd ? `(구조 다름 ${nSd})` : ''}, 검토 대기 <b class="num" style="font-weight:600">${fmt(r['뺀비교쌍'])}</b>/${fmt(r['비교쌍'])}쌍</span>
        <span class="k">지금 고객군</span><span class="it" style="display:inline-flex;align-items:center;gap:6px">${sumGate}</span>
        <button type="button" class="scope-more" aria-expanded="${scopeOpen}" aria-controls="scope-full">${scopeOpen ? '접기' : '자세히'} ${IC.chevD}</button></div>`;
    el.classList.toggle('open', scopeOpen);
    el.innerHTML = fadeBand(sum + `<div class="scope-full" id="scope-full">${line1 + line2}</div>`);
  }
  let scopeOpen = false;
  document.addEventListener('click', e => {
    const b = e.target.closest('.scope-more');
    if (!b) return;
    scopeOpen = !scopeOpen;
    renderScope();
    placeEv(); placeGuides();
  });

  // ---------- 탭과 본문 ----------
  function renderTabs() {
    const nav = $('#tabs');
    nav.innerHTML = TAB_IDS.map((id, i) => `<button class="tab" type="button" role="tab" id="tab-${id}" aria-controls="view-${id}" aria-selected="false" tabindex="-1" data-tab="${id}"><span class="tn">0${i + 1}</span><span>${esc(TAB_NAME[id])}</span></button>`).join('');
    nav.addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) set({ tab: b.dataset.tab }); });
    nav.addEventListener('keydown', e => {
      const i = TAB_IDS.indexOf(st.tab);
      let j = -1;
      if (e.key === 'ArrowRight') j = (i + 1) % TAB_IDS.length;
      if (e.key === 'ArrowLeft') j = (i + TAB_IDS.length - 1) % TAB_IDS.length;
      if (e.key === 'Home') j = 0;
      if (e.key === 'End') j = TAB_IDS.length - 1;
      if (j >= 0) { e.preventDefault(); set({ tab: TAB_IDS[j] }); $('#tab-' + TAB_IDS[j]).focus(); }
    });
    const main = $('#main');
    for (const id of TAB_IDS) {
      const sec = document.createElement('section');
      sec.className = 'view'; sec.id = 'view-' + id; sec.hidden = true;
      sec.setAttribute('role', 'tabpanel'); sec.setAttribute('aria-labelledby', 'tab-' + id); sec.dataset.tab = id;
      const t = tabs[id];
      sec.innerHTML = `<header class="vhead">${title(id, t ? t.kicker : '', TAB_NAME[id])}<div class="vhead-aside"></div></header><div class="vbody"></div>`;
      main.appendChild(sec);
    }
  }
  function viewOf(id) { return document.getElementById('view-' + id); }
  function renderTab(id, c, why) {
    const t = tabs[id]; const sec = viewOf(id);
    if (!sec) return;
    const body = $('.vbody', sec), aside = $('.vhead-aside', sec);
    if (!t) { body.innerHTML = `<div class="panel placeholder">이 탭의 파일이 아직 없습니다.</div>`; return; }
    try {
      t.render(body, Object.assign(c || ctx(), { aside, view: sec, why: why || 'render' }));
    } catch (e) {
      console.error(e);
      body.innerHTML = `<div class="panel placeholder">이 탭을 그리다 멈췄습니다: ${esc(e.message)}</div>`;
    }
    t._dirty = false;
    remark(id);
  }
  function showTab(id, opts = {}) {
    for (const x of TAB_IDS) {
      const b = $('#tab-' + x), v = viewOf(x), on = x === id;
      if (b) { b.setAttribute('aria-selected', String(on)); b.tabIndex = on ? 0 : -1; if (on && mode() === 'sheet') b.scrollIntoView({ block: 'nearest', inline: 'nearest' }); }
      if (v) v.hidden = !on;
    }
    const t = tabs[id];
    if (t && (t._dirty || !t._drawn)) { renderTab(id, ctx(new Set(['tab'])), 'tab'); t._drawn = true; }
    const v = viewOf(id);
    if (t && t.enter) { try { t.enter($('.vbody', v), ctx(new Set(['tab']))); } catch (e) { console.error(e); } }
    if (v) drawRings(v);
    if (v && motionOn()) { v.classList.remove('entering'); void v.offsetWidth; v.classList.add('entering'); setTimeout(() => v.classList.remove('entering'), 700); }
    // 근거 기둥: 그 탭의 고른 것이 있으면 그것, 없으면 기본
    const key = st.sel[id];
    if (key != null && t && t.pick) showPick(key, false); else showDefaultEv(false);
    if (mode() !== 'wide' && key == null) hideEv(false);
    placeGuides();
    if (opts.scroll !== false && booted) {
      const top = $('#work').getBoundingClientRect().top + scrollY - (parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--head-h')) || 76) - 12;
      if (scrollY > top) scrollTo({ top, behavior: 'auto' });
    }
    emit('tab', id);
  }
  function notify(changed) {
    syncCond(); renderScope(); placeEv();
    const c = ctx(changed);
    for (const id of TAB_IDS) {
      const t = tabs[id]; if (!t) continue;
      if (id === st.tab) {
        let done = false;
        if (t.update) { try { done = t.update($('.vbody', viewOf(id)), Object.assign(c, { aside: $('.vhead-aside', viewOf(id)), view: viewOf(id) })) === true; } catch (e) { console.error(e); } }
        if (!done) renderTab(id, c, 'change');
        else remark(id);
      } else t._dirty = true;
    }
    const key = st.sel[st.tab];
    if (key != null && tabs[st.tab] && tabs[st.tab].pick) showPick(key, false); else showDefaultEv(false);
    emit('change', c);
  }

  // ---------- 고르기와 근거 기둥 ----------
  const EV = { open: false };
  function setEvBox(spec, animate) {
    const k = $('#ev-k'), t = $('#ev-t'), b = $('#ev-b'), body = $('#ev-body');
    k.textContent = spec.kicker || '근거';
    t.textContent = spec.title || '';
    b.innerHTML = (spec.badges || []).join('');
    body.innerHTML = typeof spec.body === 'string' ? spec.body : '';
    if (spec.body && typeof spec.body !== 'string') body.appendChild(spec.body);
    body.scrollTop = 0;
    if (animate && motionOn()) { const box = $('.ev-in'); box.classList.remove('ev-anim'); void box.offsetWidth; box.classList.add('ev-anim'); }
    if (spec.after) { try { spec.after(body); } catch (e) { console.error(e); } }
  }
  /** 근거 기둥에 내용을 넣는다. spec: {kicker, title, badges:[html], body: html|Node, after(bodyEl)} */
  function showEv(spec, o = {}) {
    setEvBox(spec, o.animate !== false);
    if (o.open !== false && mode() !== 'wide') openEv();
  }
  function openEv() {
    if (mode() === 'wide') return;
    if (!EV.open) {
      EV.open = true; document.body.classList.add('ev-open');
      if (!(history.state && history.state.ev)) { try { history.pushState({ c4: 1, ev: 1 }, '', location.hash || encodeHash()); } catch (e) { /* */ } }
    }
    sheetPad();
  }
  function hideEv(fromPop) {
    if (!EV.open) return;
    EV.open = false; document.body.classList.remove('ev-open');
    sheetPad();
    if (!fromPop && history.state && history.state.ev) { try { history.back(); } catch (e) { /* */ } }
  }
  function sheetPad() {
    const h = EV.open && mode() === 'sheet' ? $('#ev').offsetHeight : 0;
    document.documentElement.style.setProperty('--sheet-h', h + 'px');
  }
  function defaultEvSpec() {
    const t = tabs[st.tab];
    let spec = null;
    if (t && t.evidence) { try { spec = t.evidence(ctx()); } catch (e) { console.error(e); } }
    return spec || coreDefaultEv();
  }
  function showDefaultEv(animate) { setEvBox(defaultEvSpec(), animate); }
  function coreDefaultEv() {
    const base = S['기준별'][st.base];
    const r = base ? base['범위'] : null;
    const bi = vinfo(st.base);
    const peerRows = r ? r['상대'].map(p => {
      const v = vinfo(p['종형ID']); const head = p['머리말'] != null ? S['글'][p['머리말']] : '';
      return `<p><b style="font-weight:600">${esc(vname(p['종형ID']))}</b> ${p['구조다름'] ? tag('구조 다름') : ''}<br><span class="note">${esc(v ? v['전체이름'] : '')}, 적용 ${esc(v ? v['적용시작일'] : '')}</span>${head ? `<br><span class="note">${esc(head)}</span>` : ''}</p>`;
    }).join('') : '';
    return {
      kicker: '근거', title: '범위와 읽는 법', badges: [scope('base')],
      body: `<div class="ev-sec"><h3>견준 상품</h3>
          <p><b style="font-weight:600">${esc(vname(st.base))}</b><br><span class="note">${esc(bi ? bi['전체이름'] : '')}, 적용 ${esc(bi ? bi['적용시작일'] : '')}</span></p>${peerRows}
          ${r ? `<p class="note">${esc(r['문장'])}</p>` : ''}</div>
        <div class="ev-sec"><h3>범위 배지</h3>
          <dl class="legend"><dt>${scope('all')}</dt><dd>기준 종형과 조건을 바꿔도 그대로인 값입니다. 고객군 지도(${esc(sexText(mapOf(null)['성별']))}, 갱신 유형 전체)와 개정, 시장 소식에서 셉니다.</dd>
          <dt>${scope('base')}</dt><dd>기준 종형을 바꾸면 바뀌는 값입니다. 브리핑의 값은 대표 조건(${esc(REF['나이'])}세 ${esc(sexText(REF['성별']))}, ${esc(sinceText(REF['이력']))})으로 계산했습니다.</dd></dl></div>
        <div class="ev-sec lo"><h3>판정 표지</h3>${legendHTML()}</div>`,
    };
  }
  /** 판정 범례(접지 않고 늘 보인다) */
  function legendHTML() {
    return `<dl class="legend">
      <dt>${verdict('better')}</dt><dd>같은 담보를 견줘 우체국 조건이 나은 것</dd>
      <dt>${verdict('only')}</dt><dd>견준 상대에는 없고 우체국에만 있는 담보</dd>
      <dt>${verdict('worse')}</dt><dd>같은 담보를 견줘 우체국 조건이 못한 것</dd>
      <dt>${verdict('same')}</dt><dd>조건이 같은 것</dd>
      <dt>${verdict('diff')}</dt><dd>지급 형태나 판매 구성이 달라 우열을 매기지 않은 것</dd>
      <dt>${verdict('none')}</dt><dd>상대에는 있고 우체국에는 없는 담보</dd>
      <dt>${verdict('unknown')}</dt><dd>검토 대기라 아직 견주지 않은 것</dd>
      <dt>${flagText('원문 확인')}</dt><dd>${esc(FLAG_TEXT)}. 화면에 옮긴 값이 사업방법서 원문과 같은지 사람이 확인해야 합니다</dd>
      <dt><span style="display:inline-block;width:56px;height:12px;background:linear-gradient(90deg,var(--red-hi),var(--red) 45%,var(--red-deep))"></span></dt><dd>지금 고른 줄. 그 줄의 근거가 이 기둥에 뜹니다</dd>
    </dl>`;
  }
  /** 고른 표시를 다시 찍는다(다시 그린 뒤) */
  function remark(id) {
    const v = viewOf(id); if (!v) return;
    const key = st.sel[id];
    for (const el of $$('[data-pick]', v)) {
      const on = key != null && el.dataset.pick === String(key);
      el.classList.toggle('is-sel', on);
      const hit = el.matches('button') ? el : $('.lrow-hit', el);
      if (hit) hit.setAttribute('aria-pressed', String(on));
    }
    fitSel(v);
  }
  /** 고른 막대의 빨강 길이(S3, 화면 넓이 2.5% 이하). 막대 높이로 빨강이 차지할 수 있는 길이를 셈해 --sel-red 에 둔다.
      그보다 긴 막대는 오른쪽이 슬레이트로 이어진다(흰 글자는 그대로 읽힌다). 1920 화면의 한 줄 막대는 끝까지 빨강이다 */
  // 막대에 쓰는 몫(나머지는 원문 확인 표식, 눈금, 탭 자리 표시). 좁은 창은 표식과 근거 판의 빨강 글자가 상대적으로 크므로 덜 쓴다
  const SEL_SHARE = { wide: 0.021, push: 0.017, sheet: 0.016 };
  const SEL_EXTRA = 76; // 글자 왼쪽 24px 연장과, 슬레이트로 풀리는 구간 가운데 빨강으로 보이는 앞쪽(약 52px)
  function fitSel(root) {
    root = root || viewOf(st.tab);
    if (!root) return;
    const budget = SEL_SHARE[mode()] * innerWidth * innerHeight;
    for (const el of $$('.is-sel', root)) {
      let bars;
      if (el.matches('tr')) {
        const blk = getComputedStyle(el).display === 'block'; // 좁은 화면에서 줄 묶음으로 바꾼 표
        bars = blk ? [el.querySelector('td') || el] : [el];
      } else if (el.matches('.selbar')) bars = [el];
      else bars = $$('.selbar', el);
      for (const b of bars) {
        const r = b.getBoundingClientRect();
        if (!r.height) continue;
        const w = r.width + 24;
        const L = Math.max(8, Math.min(w + 120, Math.floor(budget / r.height - SEL_EXTRA)));
        b.style.setProperty('--sel-red', L >= w ? `${Math.ceil(w + 120)}px` : `${L}px`);
      }
    }
  }
  function showPick(key, animate) {
    const t = tabs[st.tab];
    let spec = null;
    try { spec = t && t.pick ? t.pick(String(key), ctx()) : null; } catch (e) { console.error(e); }
    if (!spec) { st.sel[st.tab] = undefined; delete st.sel[st.tab]; remark(st.tab); showDefaultEv(animate); return false; }
    setEvBox(spec, animate);
    return true;
  }
  /** 항목을 고른다. 고른 표시(S8), 근거 기둥 내용 바꾸기, 좁은 화면이면 판을 연다 */
  function select(key, o = {}) {
    if (key == null) return unselect();
    st.sel[st.tab] = String(key);
    remark(st.tab);
    const ok = showPick(key, o.animate !== false);
    if (ok && mode() !== 'wide' && o.open !== false) openEv();
    const el = $(`[data-pick="${CSS.escape(String(key))}"]`, viewOf(st.tab));
    if (el && o.reveal !== false) setTimeout(() => reveal(el), mode() === 'sheet' ? 260 : 0);
    emit('select', st.tab, String(key));
  }
  function unselect() {
    delete st.sel[st.tab];
    remark(st.tab);
    showDefaultEv(true);
    hideEv(false);
    emit('select', st.tab, null);
  }
  /** 좁은 화면에서 바뀐 영역이 보이게 옮긴다(R7). 위 띠와 아래 판에 가리지 않게 */
  function reveal(el) {
    if (!el) return;
    const r = el.getBoundingClientRect();
    const top = (parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--head-h')) || 76) + 12;
    const bottom = innerHeight - (EV.open && mode() === 'sheet' ? $('#ev').offsetHeight : 0) - 12;
    const sm = motionOn() ? 'smooth' : 'auto';
    if (r.top < top) scrollBy({ top: r.top - top, behavior: sm });
    else if (r.bottom > bottom) scrollBy({ top: Math.min(r.bottom - bottom, r.top - top), behavior: sm });
  }
  /** 다른 탭으로 간다. o.focus 를 주면 그 탭의 focus(key) 를 부른다 */
  function go(tabId, o = {}) {
    if (!TAB_IDS.includes(tabId)) tabId = TAB_BY_NAME[tabId] || tabId;
    if (!TAB_IDS.includes(tabId)) return;
    set({ tab: tabId });
    const t = tabs[tabId];
    if (o.focus != null && t && t.focus) setTimeout(() => { try { t.focus(o.focus, $('.vbody', viewOf(tabId)), ctx()); } catch (e) { console.error(e); } }, 30);
  }

  // ---------- 복사와 인쇄 ----------
  function scopeLine() {
    const base = S['기준별'][st.base];
    const peers = base ? base['맞붙는종형'].map(vname).join(', ') : '';
    return `범위: 기준 종형 ${vname(st.base)} / 비교 상대 ${peers} / 지금 고객군 ${condSummary().split(', 기준')[0]} / 자료 기준 ${asofText()} / ${S['고지']}`;
  }
  const clean = s => String(s == null ? '' : s).replace(/[\t\r\n]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
  /** 글자를 복사한다. navigator.clipboard 가 안 되면 textarea 로 */
  function copyText(text, msg) {
    const done = () => toast(msg || '복사했습니다');
    const fallback = () => {
      const ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', ''); ta.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0';
      document.body.appendChild(ta); ta.select();
      let ok = false; try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      ta.remove();
      toast(ok ? (msg || '복사했습니다') : '복사하지 못했습니다. 브라우저가 막았습니다');
    };
    try {
      if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback);
      else fallback();
    } catch (e) { fallback(); }
  }
  /** 행 배열을 탭으로 구분한 글자로 복사한다. 첫 줄은 범위 머리말, 둘째 줄은 머리글(엑셀과 한글 문서에 붙여 넣기) */
  function copyRows(head, rows, o = {}) {
    const lines = [];
    if (o.scope !== false) lines.push(o.title ? `${clean(o.title)} / ${scopeLine()}` : scopeLine());
    if (head && head.length) lines.push(head.map(clean).join('\t'));
    for (const r of rows) lines.push(r.map(clean).join('\t'));
    copyText(lines.join('\r\n'), `복사했습니다: ${rows.length}줄. 엑셀이나 한글 문서에 붙여 넣으면 됩니다`);
  }
  /** 표(.tbl)를 탭으로 구분한 글자로 복사한다 */
  function copyTable(tbl, o = {}) {
    if (typeof tbl === 'string') tbl = document.getElementById(tbl);
    if (!tbl) return;
    const cp = td => (td.dataset.copy != null ? td.dataset.copy : td.dataset.cp != null ? td.dataset.cp : td.textContent);
    const head = $$('thead th', tbl).map(cp);
    const rows = $$('tbody tr', tbl).filter(tr => !tr.classList.contains('no-copy')).map(tr => $$('td,th', tr).map(cp));
    const cap = $('caption', tbl);
    copyRows(head, rows, { title: o.title || (cap ? cap.textContent : ''), scope: o.scope });
  }
  /** 한 영역만 인쇄한다(흰 바탕에 먹색). o.card 가 참이면 머리에 배포 금지 표식을 찍는다 */
  function print(el, o = {}) {
    if (typeof el === 'string') el = document.getElementById(el);
    if (!el) return;
    const root = $('#print-root');
    root.innerHTML = `<div class="ph">${esc(S['고지'])}${o.card ? '<span class="mk">내부 교육·비교 참고용(대외 배포 금지)</span>' : ''}<span class="sc">${esc(o.title ? o.title + ' / ' : '')}${esc(scopeLine())}</span></div>`;
    root.appendChild(el.cloneNode(true));
    document.body.classList.add('printing');
    const done = () => { document.body.classList.remove('printing'); root.innerHTML = ''; window.removeEventListener('afterprint', done); };
    window.addEventListener('afterprint', done);
    try { window.print(); } catch (e) { done(); }
    setTimeout(() => { if (document.body.classList.contains('printing') && !matchMedia('print').matches) done(); }, 1500);
  }
  let toastT = 0;
  function toast(msg) {
    const t = $('#toast'); t.textContent = msg; t.classList.add('on');
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('on'), 2600);
  }

  // ---------- 안내선 ----------
  function placeGuides() {
    const g = $('#guides'); if (!g) return;
    const W = innerWidth, H = innerHeight;
    const headH = $('#head').offsetHeight;
    const main = $('#main').getBoundingClientRect();
    const ev = (mode() === 'sheet' ? $('#ev') : $('.ev-slot')).getBoundingClientRect();
    const narrow = mode() === 'sheet';
    const centers = [];
    centers.push(Math.round(main.left - 16));
    if (mode() === 'wide' || (EV.open && mode() === 'push')) centers.push(Math.round(main.right + (ev.left - main.right) / 2));
    const ttl = $('.view:not([hidden]) .ttl');
    if (ttl && !narrow) { const r = ttl.getBoundingClientRect(); if (r.width) centers.push(Math.round(r.right + 16)); }
    centers.push(Math.round((mode() === 'wide' || EV.open ? Math.max(ev.right, main.right) : main.right) + 16));
    let html = '';
    for (const c of centers) {
      if (c < 0 || c > W) continue;
      if (!narrow && mode() === 'wide') html += `<i class="gl" style="left:${c - 16}px"></i><i class="gl" style="left:${c + 16}px"></i>`;
      html += `<i class="gl c" style="left:${c}px"></i>`;
    }
    const yb = H - 90;
    html += `<i class="hl" style="top:${headH}px"></i><i class="hl" style="top:${yb}px"></i>`;
    for (const c of centers) if (c >= 0 && c <= W) html += `<i class="tk" style="left:${c}px;top:${headH}px"></i><i class="tk" style="left:${c}px;top:${yb}px"></i>`;
    const tb = $('#tab-' + st.tab);
    const tx = tb ? Math.round(tb.getBoundingClientRect().left + 7) : 0;
    html += `<i class="tk red" id="tk-red" style="left:${tx}px;top:${headH}px"></i>`;
    g.innerHTML = html;
  }

  /** 근거 기둥의 위 끝을 본문 위 끝에 맞춘다(넓은 화면과 중간 폭). 위 띠 아래로는 올라가지 않는다 */
  function placeEv() {
    if (mode() === 'sheet') return;
    const headH = $('#head').offsetHeight;
    const top = Math.max(headH + 16, Math.round($('#work').getBoundingClientRect().top));
    document.documentElement.style.setProperty('--ev-top', top + 'px');
  }
  addEventListener('scroll', placeEv, { passive: true });

  // ---------- 스킨, 움직임 ----------
  function applySkin() {
    document.documentElement.dataset.theme = st.skin;
    const b = $('#skin'); if (b) { b.textContent = st.skin === 'dark' ? '밝은 화면' : '짙은 화면'; b.setAttribute('aria-pressed', String(st.skin === 'dark')); }
    store.set(LS_SKIN, st.skin);
  }
  function applyMotion() {
    document.documentElement.dataset.motion = st.motion;
    const b = $('#motion'); if (b) { b.innerHTML = `움직임 <b>${st.motion === 'on' ? '켬' : '끔'}</b>`; b.setAttribute('aria-pressed', String(st.motion === 'on')); }
    store.set(LS_MOTION, st.motion);
  }
  const asofText = () => String(S['자료시각'] || '').replace('T', ' ').slice(0, 16);

  // ---------- 용어 풀이 ----------
  let helpBtn = null;
  function closeHelp(restore) {
    const pop = $('#help-pop');
    if (!pop || pop.hidden) return false;
    pop.hidden = true;
    pop.innerHTML = '';
    $$('[data-help][aria-expanded="true"]').forEach(b => b.setAttribute('aria-expanded', 'false'));
    const prev = helpBtn;
    helpBtn = null;
    if (restore && prev && document.contains(prev)) prev.focus();
    return true;
  }
  function toggleHelp(btn) {
    const pop = $('#help-pop');
    const key = btn && btn.dataset.help;
    const item = key && TERMS[key];
    if (!pop || !item) return;
    if (!pop.hidden && helpBtn === btn) { closeHelp(false); return; }
    $$('[data-help][aria-expanded="true"]').forEach(b => b.setAttribute('aria-expanded', 'false'));
    helpBtn = btn;
    btn.setAttribute('aria-expanded', 'true');
    pop.innerHTML = `<div class="help-h"><span>${esc(item.title)}</span><button type="button" class="help-x" data-help-close="1" aria-label="용어 풀이 닫기"><svg width="11" height="11" viewBox="0 0 14 14" aria-hidden="true"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.8"/></svg></button></div><p class="help-p">${esc(item.body)}</p>`;
    pop.hidden = false;
    const r = btn.getBoundingClientRect();
    const pw = pop.offsetWidth || 340, ph = pop.offsetHeight || 96;
    const left = Math.max(12, Math.min(innerWidth - pw - 12, Math.round(r.left - 8)));
    const below = r.bottom + 8 + ph <= innerHeight - 12;
    const top = below ? Math.round(r.bottom + 8) : Math.max(12, Math.round(r.top - ph - 8));
    pop.style.left = left + 'px';
    pop.style.top = top + 'px';
  }
  addEventListener('scroll', () => closeHelp(false), { passive: true });
  on('tab', () => closeHelp(false));
  on('change', () => closeHelp(false));

  // ---------- 위임한 눌림 ----------
  document.addEventListener('click', e => {
    const hc = e.target.closest('[data-help-close]');
    if (hc) { e.stopPropagation(); closeHelp(true); return; }
    const hb = e.target.closest('[data-help]');
    if (hb) { e.stopPropagation(); toggleHelp(hb); return; }
    if (!e.target.closest('#help-pop')) closeHelp(false);
    // 복사와 인쇄는 단추에만 건다. 표 칸의 data-copy(복사할 원문 글자)는 행 고르기를 막지 않는다
    const a = e.target.closest('[data-act],[data-go],button[data-copy],button[data-print]');
    if (a) {
      if (a.dataset.go) { e.stopPropagation(); go(a.dataset.go, { focus: a.dataset.focus }); return; }
      if (a.dataset.copy) { e.stopPropagation(); copyTable(a.dataset.copy, { title: a.dataset.title }); return; }
      if (a.dataset.print) { e.stopPropagation(); print(a.dataset.print, { title: a.dataset.title, card: a.dataset.card === '1' }); return; }
      if (a.dataset.act === 'base-to') { set({ base: a.dataset.v }); return; }
      if (a.dataset.act) return; // 탭이 직접 처리한다
    }
    const p = e.target.closest('.view [data-pick]');
    if (p && !e.target.closest('.live')) select(p.dataset.pick);
  });
  document.addEventListener('keydown', e => {
    const p = e.target.closest && e.target.closest('.view tr[data-pick]');
    if (p && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); select(p.dataset.pick); return; }
    if (e.key === 'Escape') {
      if (closeHelp(true)) return;
      if (EV.open) { unselect(); return; }
      if (st.sel[st.tab] != null) { unselect(); return; }
    }
    const typing = e.target.closest && e.target.closest('input,select,textarea');
    if (typing) return;
    if (e.key === ']' || e.key === '[') {
      const i = TAB_IDS.indexOf(st.tab);
      set({ tab: TAB_IDS[(i + (e.key === ']' ? 1 : TAB_IDS.length - 1)) % TAB_IDS.length] });
    }
  });

  // ---------- 탭 등록 ----------
  /** 탭을 등록한다. def: {id, kicker, render(body, ctx), update?(body, ctx), pick?(key, ctx), evidence?(ctx), focus?(key, body, ctx), enter?(body, ctx)} */
  function registerTab(def) {
    if (!def || !TAB_IDS.includes(def.id)) throw new Error('알 수 없는 탭: ' + (def && def.id));
    tabs[def.id] = Object.assign({ kicker: '' }, def, { _dirty: true, _drawn: false });
    if (booted) {
      const sec = viewOf(def.id);
      if (sec) $('.ttl', sec).outerHTML = title(def.id, def.kicker, TAB_NAME[def.id]);
      if (def.id === st.tab) showTab(st.tab);
    }
  }

  // ---------- 시작 ----------
  function boot() {
    const saved = { skin: store.get(LS_SKIN), motion: store.get(LS_MOTION) };
    if (saved.skin === 'dark' || saved.skin === 'light') st.skin = saved.skin;
    if (saved.motion === 'on' || saved.motion === 'off') st.motion = saved.motion;
    else if (matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) st.motion = 'off';
    Object.assign(st, decodeHash(location.hash));
    if (st.since == null) st.surg = false;
    applySkin(); applyMotion();
    $('#asof').textContent = asofText();
    $('#notice-t').textContent = S['고지'];
    $('#foot-notice').textContent = S['고지'];
    const eh = $('#ev-help');
    if (eh) eh.outerHTML = help('ev-panel', '관계와 근거 패널');
    renderCond(); renderScope(); renderTabs();
    $('#skin').addEventListener('click', () => set({ skin: st.skin === 'dark' ? 'light' : 'dark' }));
    $('#motion').addEventListener('click', () => set({ motion: st.motion === 'on' ? 'off' : 'on' }));
    $('#ev-x').addEventListener('click', () => unselect());
    $('#condmini').addEventListener('click', () => { scrollTo({ top: 0, behavior: motionOn() ? 'smooth' : 'auto' }); });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(es => { for (const x of es) $('#head').classList.toggle('cond-away', !x.isIntersecting); }, { rootMargin: '-80px 0px 0px 0px' }).observe($('#cond'));
    }
    let rz = 0, lastMode = mode();
    addEventListener('resize', () => {
      clearTimeout(rz);
      rz = setTimeout(() => {
        const m = mode();
        if (m !== lastMode) { if (m === 'wide') { EV.open = false; document.body.classList.remove('ev-open'); } lastMode = m; }
        closeHelp(false);
        sheetPad(); placeEv(); placeGuides(); fitSel(); emit('resize', m);
      }, 80);
    });
    $('#work').addEventListener('transitionend', e => { if (e.target === $('#work')) { placeGuides(); fitSel(); } });
    booted = true;
    try { history.replaceState({ c4: 1 }, '', encodeHash()); } catch (e) { /* */ }
    showTab(st.tab, { scroll: false });
    placeEv(); setTimeout(() => { placeEv(); placeGuides(); }, 50);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { placeGuides(); fitSel(); });
  }

  window.App = {
    S, D: DD, TAB_IDS, TAB_NAME, TAB_BY_NAME, ORG_ORDER, REF,
    get state() { return { ...st, sel: { ...st.sel } }; },
    set, on, ctx: () => ctx(), registerTab, go, select, unselect, reveal,
    ev: { show: showEv, open: openEv, close: () => unselect(), def: () => showDefaultEv(true), legend: legendHTML },
    ui: UI, txt: TXT, mode, motionOn,
    cellOf, limitOf, mapOf, condSummary, scopeLine, asofText,
    copyText, copyRows, copyTable, print, toast, fitSel,
    boot,
  };
})();
