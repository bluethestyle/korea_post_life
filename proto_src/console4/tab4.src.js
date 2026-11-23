/* 탭 4 담보 비교. 주인공 도형은 6px 수평 채움 막대(치료 여정 격자), 줄무늬 없는 비교표, 직각 꺾은선의 관계도(갈림 자리 9px ◇).
   자료: sales.json 의 기준별[종형].치료여정, 단정주의, 보류요약, 포인트와, 이 파일 첫 줄의 CV(gen_cover.py 가 사본에서 뽑은 비교쌍과 급부).
   CV 는 sales.py 와 같은 계산(insights.analyze)을 읽은 것이고, 판정은 sales.json 을 따른다. 단정 주의에 든 담보는 어디서나
   "우열을 매기지 않음"으로 보인다(R10). 화면이 숫자와 판정을 새로 만들지 않는다.
   이 파일은 tab4.src.js 이고, tab4.js 는 gen_cover.py 가 자료 한 줄을 앞에 붙여 쓴다. 관계도는 탭 5 도 쓰도록 App.cover 로 내보낸다. */
const { ui, txt } = App;
const { esc, fmt } = ui;
const S = App.S;
const STEPS = ['진단', '수술', '치료', '입원', '통원'];
const ROMAN = { 'Ⅰ': 'I', 'Ⅱ': 'II', 'Ⅲ': 'III', 'Ⅳ': 'IV', 'Ⅴ': 'V' };
const fixG = s => String(s == null ? '' : s).replace(/[ⅠⅡⅢⅣⅤ]/g, m => ROMAN[m]);
const nf = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 });
const N = n => nf.format(n);

// ---------- 이름 ----------
const vinfo = v => S['종형'][v] || {};
const orgOf = v => vinfo(v)['기관코드'] || String(v).split('_')[0];
const orgN = v => txt.orgShort(orgOf(v));
const kindN = v => vinfo(v)['종형명'] || v;
const fullN = v => vinfo(v)['이름'] || v;
const std = sid => S['표준담보'][sid] || { '이름': sid };
const stdN = sid => std(sid)['이름'] || sid;
const VID_RE = /\b[A-Z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+\b/g;
/** 사유 글의 종형ID를 회사 이름으로 바꾼다 */
const reasonText = list => [...new Set((Array.isArray(list) ? list : [list]).map(x => String(x).replace(VID_RE, m => fullN(m))))].join(', ');

// ---------- 급부와 특약(CV 의 번호) ----------
function ben(i) {
  const b = CV && CV.ben[i];
  return b ? { i, name: fixG(b[0]), rid: b[1], role: b[2], pay: b[3], base: b[4], ratio: !!b[5], wait: b[6] || 0, red: b[7] || [],
    limit: b[8], exc: b[9], doc: b[10], page: b[11], state: b[12], prob: b[13], log: !!b[14], tags: b[15] } : null;
}
function rider(j) { const r = CV && CV.rid[j]; return r ? { name: fixG(r[0]), kind: r[1], max: r[2] } : null; }
function won(m) {
  if (m == null) return null;
  if (m >= 10000) { const e = Math.floor(m / 10000), r = Math.round((m - e * 10000) * 100) / 100; return r ? `${N(e)}억 ${N(r)}만원` : `${N(e)}억원`; }
  return `${N(m)}만원`;
}
const rateOf = b => (b.base ? b.pay * 100 / b.base : b.pay);
const payText = b => (b.pay == null ? '자료 없음' : b.ratio ? `가입금액의 ${N(rateOf(b))}%` : won(b.pay));
const baseText = b => (b.ratio ? '가입금액 대비 비율로 적힌 급부' : b.base != null ? `기준 가입금액 ${won(b.base)}일 때` : '기준 가입금액 자료 없음');
const waitText = w => `${N(w || 0)}일`;
const monthsText = m => (m % 12 === 0 ? `${m / 12}년` : `${m}개월`);
const redText = red => (red && red.length ? red.map(([m, r]) => `${monthsText(m)} 안 ${N(Math.round(r * 1000) / 10)}%`).join(', ') : '감액 없음');
const redShort = red => (red && red.length ? red.map(([m, r]) => `${monthsText(m)} ${N(Math.round(r * 1000) / 10)}%`).join(', ') : '없음');
const has = c => !!(c && c.i && c.i.length);
const repOf = c => (has(c) ? ben(c.r != null ? c.r : c.i[0]) : null);

// ---------- 판정 모형(기준 종형마다 한 번) ----------
const V_KIND = { '같음': 'same', '나음': 'better', '못함': 'worse', '엇갈림': 'diff', '판정 보류': 'unknown' };
const cache = {};
function model(baseId) {
  if (cache[baseId]) return cache[baseId];
  const B = CV && CV.b[baseId];
  const base = S['기준별'][baseId];
  if (!B || !base) return null;
  const by = (list, key) => { const o = {}; (list || []).forEach(x => { const k = x[key]; if (k) (o[k] = o[k] || []).push(x); }); return o; };
  const cau = by(base['단정주의'], '표준담보ID');
  const pts = by((base['포인트'] || []).map(id => S['포인트'][id]).filter(Boolean), '표준담보ID');
  const omit = by(base['뺀포인트'], '표준담보ID');
  const rows = B.rows.map(r => {
    const row = { sid: r[0], cells: r[1], prs: r[2] || {}, ins: r[3] || [], major: std(r[0])['대분류'] || '', type: std(r[0])['급부유형'] || '',
      cau: cau[r[0]] || [], pts: pts[r[0]] || [], omit: omit[r[0]] || [] };
    row.verd = B.cols.slice(1).map((_, i) => verdictOf(row, B.cols, i + 1));
    // 한 상대에만 없으면 "우체국에만 있음" 대신 그 상대에 없다고 적는다(우체국에만 있음은 견준 상대 모두에 없을 때만)
    if (row.verd.some(v => !v || v.kind !== 'only')) row.verd.forEach((v, i) => { if (v && v.kind === 'only') v.text = `${orgN(B.cols[i + 1])}에 없음`; });
    row.same = row.verd.every(v => !v || v.kind === 'same');
    return row;
  });
  return (cache[baseId] = { baseId, cols: B.cols, rows, byId: Object.fromEntries(rows.map(r => [r.sid, r])), pairs: B.pairs, dropped: B.dropped });
}
function scopedPairs(baseId, pickSet) {
  const B = CV && CV.b[baseId];
  if (!B) return null;
  let total = 0, wait = 0;
  B.rows.forEach(r => {
    const prs = r[2] || {};
    for (const [peer, q] of Object.entries(prs)) {
      if (!pickSet || pickSet.has(orgOf(peer))) {
        total++;
        if (q && q.x) wait++;
      }
    }
  });
  return { total, wait, cmp: total - wait };
}
function peerIdxOf(m, c) {
  if (!m) return [];
  const allIdx = m.cols.slice(1).map((_, i) => i);
  if (!c || c.peerScope === 'all') return allIdx;
  const pSet = new Set(c.activePeerOrgs || []);
  return allIdx.filter(i => pSet.has(orgOf(m.cols[i + 1])));
}
function verdFor(row, m, i, pIdxs) {
  const v = row.verd[i];
  if (!v || v.kind !== 'only') return v;
  const allOnly = pIdxs.length > 0 && pIdxs.every(idx => row.verd[idx] && row.verd[idx].kind === 'only');
  return Object.assign({}, v, { text: allOnly ? null : `${orgN(m.cols[i + 1])}에 없음` });
}
/** 우체국(기준 종형)을 k 번째 상대와 견준 판정. sales.json 의 단정 주의가 먼저다(R10). 돌려주는 값: {kind, text, why, q} 또는 null(둘 다 없음) */
function verdictOf(row, cols, k) {
  const peer = cols[k], b = row.cells[0], c = row.cells[k];
  const bh = has(b), ch = has(c), po = orgN(peer);
  const cau = row.cau.find(x => (x['상대종형ID'] || []).includes(peer));
  const drops = row.ins.filter(x => x.drop && (x.p || []).includes(peer));
  if (bh && ch) {
    const q = row.prs[peer] || null;
    // 단정 주의(sales.json)에 든 담보는 어디서나 "우열을 매기지 않음"이다(R10). 면책이나 감액이 다른 항목은 까닭에 글로만 적는다
    if (cau) {
      const d = q && q.it ? q.it.filter(t => t[3] === '나음' || t[3] === '못함').map(t => `${t[0]} ${t[1]} 대 ${t[2]}`).join(', ') : '';
      return { kind: 'diff', why: `${cau['문장']}${d ? ` 대표 급부끼리 다른 항목(${d})이 있지만 우열에 넣지 않았습니다.` : ''}`, caution: cau['종류'], q };
    }
    if (!q) return { kind: 'unknown', text: '모름', why: '견준 기록이 없습니다', q };
    if (q.x) return { kind: 'unknown', text: '검토 대기', why: `검토 대기라 견주지 않았습니다: ${reasonText(q.x)}`, q };
    if (q.f === '다름' && q.v === '같음') return { kind: 'diff', why: '지급 형태가 달라 우열을 매기지 않았습니다', q };
    const kind = V_KIND[q.v] || 'unknown';
    if (q.v === '판정 보류') return { kind, text: '판정 보류', why: `판정을 미뤘습니다: ${(q.hs || []).join(', ') || '사유 자료 없음'}`, q };
    if (q.v === '엇갈림') return { kind, why: '면책, 감액, 지급 형태의 우열이 항목마다 엇갈려 우열을 매기지 않았습니다', q };
    return { kind, q };
  }
  if (bh && !ch) {
    if (c && c.w) return { kind: 'unknown', text: '검토 대기', why: `${txt.josa(po, '은')} 매핑 검토 대기 급부 ${c.w}줄만 있어 견주지 않았습니다` };
    if (drops.length) return { kind: 'unknown', text: '검토 대기', why: reasonText(drops.flatMap(d => d.drop)) };
    if (c && c.c) return { kind: 'diff', why: `${txt.josa(po, '은')} ${c.c[0]}인 ${txt.josa(c.c[1].map(stdN).join(', '), '으로')} 덮습니다` };
    return { kind: 'only', why: `${po}에는 이 담보가 없습니다` };
  }
  if (!bh && ch) {
    if (b && b.w) return { kind: 'unknown', text: '검토 대기', why: `우체국에 매핑 검토 대기 급부 ${b.w}줄이 있어 견주지 않았습니다` };
    const d2 = row.ins.filter(x => x.drop);
    if (d2.length) return { kind: 'unknown', text: '검토 대기', why: reasonText(d2.flatMap(d => d.drop)) };
    const rel = b && b.c ? `우체국은 ${b.c[0]}인 ${txt.josa(b.c[1].map(stdN).join(', '), '이')} 관련 보장을 합니다` : '';
    return { kind: 'none', why: rel || `${po}에는 있고 우체국에는 없는 담보입니다`, related: !!(b && b.c) };
  }
  if ((b && b.w) || (c && c.w)) return { kind: 'unknown', text: '검토 대기', why: '매핑 검토 대기 급부만 있어 견주지 않았습니다' };
  return null;
}
const chip = (v, title) => (v ? ui.verdict(v.kind, v.text, title || v.why) : '<span class="cv-both">둘 다 없음</span>');
const chipText = v => (v ? (v.text || { better: '우체국 나음', only: '우체국에만 있음', worse: '우체국 못함', same: '같음', diff: '우열을 매기지 않음', none: '우체국에 없음', unknown: '모름' }[v.kind]) : '둘 다 없음');

// ---------- 관계도(직각 꺾은선, 갈림 자리 9px ◇). 탭 5 도 쓴다 ----------
const GF = w => `${w} 13px PLNum, PLKo, "Malgun Gothic", sans-serif`;
let mctx = null;
function tw(s, font) { if (!mctx) mctx = document.createElement('canvas').getContext('2d'); mctx.font = font; return mctx.measureText(s).width; }
function wrapT(s, font, max, n) {
  const out = []; let line = '';
  for (const ch of String(s)) {
    if (!line || tw(line + ch, font) <= max) { line += ch; continue; }
    const sp = line.lastIndexOf(' ');
    if (ch !== ' ' && sp > 0 && line.length - sp <= 6) { out.push(line.slice(0, sp)); line = line.slice(sp + 1) + ch; }
    else { out.push(line.trimEnd()); line = ch === ' ' ? '' : ch; }
  }
  if (line.trim()) out.push(line.trim());
  if (out.length <= n) return { lines: out, cut: false };
  const keep = out.slice(0, n); let last = keep[n - 1];
  while (last.length > 1 && tw(last + '…', font) > max) last = last.slice(0, -1);
  keep[n - 1] = last.trimEnd() + '…';
  return { lines: keep, cut: true };
}
const f1 = v => (+v).toFixed(1);
const dia = (x, y) => `<path class="rl-dia" d="M${f1(x)} ${f1(y - 4.5)}L${f1(x + 4.5)} ${f1(y)} ${f1(x)} ${f1(y + 4.5)} ${f1(x - 4.5)} ${f1(y)}Z"/>`;
/** 관계도 SVG. 회사마다 한 갈래(종형 → 특약 → 급부), 급부에서 오른쪽 세로 간선으로 맨 위 표준담보에 닿는다 */
function relSVG(baseId, sid, W) {
  const m = model(baseId); const row = m && m.byId[sid];
  if (!row) return '';
  W = Math.max(280, Math.floor(W));
  const LH = 17, PY = 7, PX = 8, BG = 20, TX = PX + BG + 7, TRX = 11; // BG: 종, 특, 급, 표 기호 칸(글자 13px), TRX: 회사 줄기의 x
  const busX = W - 6, benR = busX - 12;
  const rX = 26, rW = Math.round(Math.max(96, Math.min(150, W * .33))), bX = rX + rW + 22, bW = benR - bX;
  let s = '', y = 0;
  const box = (x, yy, w, h, cls = '') => `<rect class="rl-b ${cls}" x="${f1(x)}" y="${f1(yy)}" width="${f1(w)}" height="${f1(h)}"/>`;
  const glyph = (kind, x, yy) => {
    const cx = x + PX + BG / 2, cy = yy + PY + 6;
    const R = BG / 2 + 1;
    const shape = kind === '종' ? `<path class="rl-g" d="M${f1(cx)} ${f1(cy - R - 1)}L${f1(cx + R + 1)} ${f1(cy)} ${f1(cx)} ${f1(cy + R + 1)} ${f1(cx - R - 1)} ${f1(cy)}Z"/>`
      : kind === '급' ? `<circle class="rl-g" cx="${f1(cx)}" cy="${f1(cy)}" r="${R}"/>`
        : kind === '표' ? `<path class="rl-g" d="${Array.from({ length: 6 }, (_, i) => { const a = Math.PI / 3 * i + Math.PI / 6; return `${i ? 'L' : 'M'}${f1(cx + (R + 1) * Math.cos(a))} ${f1(cy + (R + 1) * Math.sin(a))}`; }).join('')}Z"/>`
          : `<rect class="rl-g" x="${f1(cx - R)}" y="${f1(cy - R)}" width="${2 * R}" height="${2 * R}"/>`;
    return shape + `<text class="rl-gt" x="${f1(cx)}" y="${f1(cy + 4.6)}" text-anchor="middle">${kind}</text>`;
  };
  const lines = (arr, x, y0, cls = 'rl-t') => `<text class="${cls}">${arr.map((t, i) => `<tspan x="${f1(x)}" y="${f1(y0 + i * LH)}">${esc(t)}</tspan>`).join('')}</text>`;
  // 표준담보(맨 위)
  const sl = wrapT(stdN(sid), GF(600), W - 2 - TX - PX, 2);
  const stdH = PY * 2 + LH * sl.lines.length + 2;
  s += box(0, 0, W - 2, stdH, 'std') + glyph('표', 0, (stdH - 26) / 2 + 2) + lines(sl.lines, TX, PY + 13 + 1);
  y = stdH + 16;
  const busTop = stdH;
  const curC = App.ctx();
  const pIdxsAll = peerIdxOf(m, curC);
  const pIdxs = pIdxsAll.slice(0, 6);
  const colIdxs = [0].concat(pIdxs.map(i => i + 1));
  const edges = [], dias = [];
  colIdxs.forEach(k => {
    const vid = m.cols[k];
    const c = row.cells[k];
    // 종형 머리
    const head = `${orgN(vid)} ${txt.shortName(kindN(vid)).short}`;
    const hl = wrapT(head, GF(600), benR - TX - (k ? 0 : 44), 1).lines[0] || head;
    s += glyph('종', TRX - PX - BG / 2, y - 2) + `<text class="rl-t rl-h" x="${f1(TX - 2)}" y="${f1(y + 13)}">${esc(hl)}</text>`;
    if (!k) s += `<rect class="rl-base" x="${f1(TX - 2 + tw(hl, GF(600)) + 8)}" y="${f1(y - 1)}" width="38" height="20"/><text class="rl-s" x="${f1(TX - 2 + tw(hl, GF(600)) + 27)}" y="${f1(y + 13)}" text-anchor="middle">기준</text>`;
    const trunkTop = y + 20;
    y += 26;
    if (k) {
      const v = verdFor(row, m, k - 1, pIdxsAll);
      const t = `${chipText(v)}${v && v.why ? `: ${v.why}` : ''}`;
      const tl = wrapT(t, GF(400), benR - rX - 16, 3);
      const h = PY * 2 + LH * tl.lines.length - 2;
      s += `<rect class="rl-tag ${v ? 'k-' + v.kind : ''}" x="${f1(rX)}" y="${f1(y)}" width="${f1(benR - rX)}" height="${f1(h)}"/><rect class="rl-tagl ${v ? 'k-' + v.kind : ''}" x="${f1(rX)}" y="${f1(y)}" width="3" height="${f1(h)}"/>` + lines(tl.lines, rX + 12, y + PY + 12, 'rl-t rl-s');
      y += h + 8;
    }
    if (!has(c)) {
      const why = !c ? '이 종형에는 이 담보가 없습니다' : c.w ? `매핑 검토 대기 급부 ${c.w}줄만 있습니다` : c.c ? `${c.c[0]}인 ${txt.josa(c.c[1].map(stdN).join(', '), '으로')} 덮습니다` : '이 종형에는 이 담보가 없습니다';
      const al = wrapT(why, GF(400), benR - rX - 20, 2);
      const h = PY * 2 + LH * al.lines.length - 2;
      s += box(rX, y, benR - rX, h, 'absent') + lines(al.lines, rX + 12, y + PY + 12, 'rl-t rl-s');
      edges.push({ d: `M${TRX} ${f1(trunkTop)}V${f1(y + h / 2)}H${f1(rX - 2)}`, dash: true });
      y += h + 18;
      return;
    }
    // 급부를 특약별로 묶는다(대표 먼저)
    const ids = [c.r != null ? c.r : c.i[0], ...c.i.filter(i => i !== c.r)];
    const groups = [];
    ids.forEach(i => { const b = ben(i); if (!b) return; let g = groups.find(x => x.rid === b.rid); if (!g) groups.push(g = { rid: b.rid, bs: [] }); g.bs.push(b); });
    const mids = [];
    groups.forEach(g => {
      const rd = rider(g.rid);
      const rl = wrapT(txt.shortName(rd ? rd.name : '', { brackets: true }).short, GF(600), rW - TX - PX, 2);
      const rh = PY * 2 + LH * rl.lines.length;
      const bl = g.bs.map(b => {
        const nl = wrapT(txt.shortName(b.name, { brackets: true }).short, GF(600), bW - TX - PX, 2);
        const meta = `${b.i === (c.r != null ? c.r : c.i[0]) ? '대표, ' : ''}${txt.pageText(b.doc, b.page)}`;
        return { b, nl, meta, h: PY * 2 + LH * nl.lines.length + 16 };
      });
      const bh = bl.reduce((a, x) => a + x.h, 0) + (bl.length - 1) * 6;
      const rowH = Math.max(rh, bh);
      const ry = y + (rowH - rh) / 2;
      s += box(rX, ry, rW, rh, 'rider') + glyph('특', rX, ry) + lines(rl.lines, rX + TX, ry + PY + 13);
      const rmid = ry + rh / 2;
      mids.push(rmid);
      let by = y + (rowH - bh) / 2;
      const bmids = [];
      bl.forEach(x => {
        const rep = x.b.i === (c.r != null ? c.r : c.i[0]);
        s += box(bX, by, bW, x.h, rep ? 'ben rep' : 'ben') + glyph('급', bX, by) + lines(x.nl.lines, bX + TX, by + PY + 13)
          + `<text class="rl-s" x="${f1(bX + TX)}" y="${f1(by + PY + 13 + LH * x.nl.lines.length)}">${esc(x.meta)}</text>`;
        const mid = by + x.h / 2;
        bmids.push(mid);
        edges.push({ d: `M${f1(bX + bW)} ${f1(mid)}H${f1(busX)}V${f1(busTop + 2)}`, dash: x.b.log, arrow: true });
        by += x.h + 6;
      });
      const xm = rX + rW + 11;
      bmids.forEach(mid => edges.push({ d: `M${f1(rX + rW)} ${f1(rmid)}H${f1(xm)}V${f1(mid)}H${f1(bX - 1)}` }));
      if (bmids.length > 1) dias.push([xm, rmid]);
      y += rowH + 10;
    });
    mids.forEach(mid => edges.push({ d: `M${TRX} ${f1(trunkTop)}V${f1(mid)}H${f1(rX - 1)}` }));
    if (mids.length > 1) mids.slice(0, -1).forEach(mid => dias.push([TRX, mid]));
    const more = (c.n || 0) - ids.length;
    if (more > 0) {
      const ml = wrapT(`같은 담보 급부 ${c.n}개 가운데 ${ids.length}개(대표 급부와 조건이 다른 줄)를 그렸습니다`, GF(400), benR - rX, 2);
      s += lines(ml.lines, rX, y + 10, 'rl-s');
      y += 2 + LH * ml.lines.length;
    }
    y += 12;
  });
  if (pIdxsAll.length > pIdxs.length) {
    const restMsg = `나머지 상대 ${pIdxsAll.length - pIdxs.length}곳은 아래 조건 비교 표에서 함께 확인합니다.`;
    s += `<text class="rl-s" x="${f1(rX)}" y="${f1(y + 10)}">${esc(restMsg)}</text>`;
    y += 22;
  }
  const H = Math.round(y);
  const es = edges.map(e => `<path class="rl-e${e.dash ? ' dash' : ''}" d="${e.d}"${e.dash ? '' : ' pathLength="1"'}${e.arrow ? ' marker-end="url(#rl-ar)"' : ''}/>`).join('');
  return `<svg class="rl-svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(stdN(sid))} 관계도: 회사마다 종형, 특약, 급부, 표준담보">
    <defs><marker id="rl-ar" viewBox="0 0 10 10" refX="5" refY="8" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto"><path d="M1 9L5 1 9 9" class="rl-arh"/></marker></defs>
    <g class="rl-es">${es}</g>${dias.map(d => dia(d[0], d[1])).join('')}${s}</svg>`;
}
/** 관계도 범례: 그림 아래에 늘 보이는 두 줄 */
function relLegend() {
  const ln = (dash, t) => `<span><svg width="20" height="6" aria-hidden="true"><line x1="0" y1="3" x2="20" y2="3" class="rl-e${dash ? ' dash' : ''}"/></svg>${t}</span>`;
  const bx = (ch, t) => `<span><b class="rl-lb" aria-hidden="true">${ch}</b>${t}</span>`;
  return `<div class="rl-lg"><div>${ln(false, '확정')}${ln(true, '작업 로그 검토 대기')}<span><svg width="10" height="10" viewBox="-5 -5 10 10" aria-hidden="true"><path class="rl-dia" d="M0-4.5L4.5 0 0 4.5-4.5 0Z"/></svg>갈림</span><span><b class="rl-lb rep" aria-hidden="true">급</b>굵은 테두리는 대표 급부</span></div>
    <div>${bx('종', '종형')}${bx('특', '특약')}${bx('급', '급부')}${bx('표', '표준담보')}</div></div>`;
}
/** 관계도를 그 자리에 그린다(넓이를 재야 하므로 넣은 뒤에 부른다) */
function drawRel(el, baseId, sid) {
  if (!el) return;
  const w = el.clientWidth || (el.parentElement && el.parentElement.clientWidth) || 360;
  el.innerHTML = relSVG(baseId, sid, w);
  if (App.motionOn()) { el.classList.remove('rl-in'); void el.offsetWidth; el.classList.add('rl-in'); }
}

// ---------- 조건 비교와 근거(근거 기둥) ----------
function condTable(m, row, c) {
  const colIdxs = [0].concat(peerIdxOf(m, c).map(i => i + 1));
  const cols = colIdxs.map(k => m.cols[k]);
  const reps = colIdxs.map(k => repOf(row.cells[k]));
  const items = [
    ['지급', b => payText(b)], ['기준 가입금액', b => baseText(b)], ['면책', b => waitText(b.wait)], ['감액', b => redText(b.red)],
    ['지급 형태', b => b.tags || '문구 없음'],
  ];
  const head = `<tr><th scope="col">항목</th>${cols.map(v => `<th scope="col" title="${esc(fullN(v))}">${esc(orgN(v))}</th>`).join('')}<th scope="col">요약</th></tr>`;
  const body = items.map(([lab, f]) => {
    const vals = {};
    cols.forEach((v, k) => { vals[orgOf(v)] = reps[k] ? f(reps[k]) : null; });
    return `<tr><th scope="row">${esc(lab)}</th>${cols.map((v, k) => `<td>${reps[k] ? esc(f(reps[k])) : '<span class="cv-na">없음</span>'}</td>`).join('')}<td class="sm">${esc(txt.sameSummary(vals))}</td></tr>`;
  }).join('');
  return `<div class="cv-ct-w"><table class="cv-ct">${head}${body}</table></div><p class="note">대표 급부끼리 견줍니다. 판정은 면책, 감액, 지급 형태로 하고, 지급액은 기준 가입금액이 회사마다 달라 판정에 넣지 않았습니다.</p>`;
}
function evidenceList(m, row, extra, c) {
  const colIdxs = [0].concat(peerIdxOf(m, c).map(i => i + 1));
  const items = colIdxs.map(k => {
    const v = m.cols[k];
    const b = repOf(row.cells[k]);
    if (!b) return '';
    const rd = rider(b.rid);
    return `<li><b>${esc(orgN(v))}</b> ${ui.tag(txt.pageText(b.doc, b.page))} <span title="${esc(b.name)}">${esc(b.name)}</span>${rd ? `<br><span class="note">특약: ${esc(rd.name)}</span>` : ''}</li>`;
  }).join('');
  return `<ul class="cv-evl">${items}${extra || ''}</ul>`;
}
function rowEvidence(c, sid, mode) {
  const m = model(c.baseId); const row = m && m.byId[sid];
  if (!row) return null;
  const pIdxs = peerIdxOf(m, c);
  const pSet = new Set(c.activePeerOrgs || []);
  const scopedCau = c.peerScope === 'all' ? row.cau : row.cau.filter(x => (x['상대종형ID'] || []).some(v => pSet.has(orgOf(v))));
  const st = std(sid);
  let judge = '';
  if (mode === 'caution' && scopedCau.length) {
    judge += scopedCau.map(x => `<p>${ui.verdict('diff')} <span class="note">${esc(x['종류'])}</span></p><p>${esc(x['문장'])}</p>`).join('');
  }
  judge += pIdxs.map(i => {
    const peer = m.cols[i + 1];
    const v = verdFor(row, m, i, pIdxs);
    const q = v && v.q;
    // 우열을 매기지 않은 짝(단정 주의, 엇갈림)은 항목 표에서도 나음과 못함을 쓰지 않고 "다름"으로 적는다(R10)
    const noRank = !v || (v.kind !== 'better' && v.kind !== 'worse');
    const word = t => (t === '나음' || t === '못함') ? (noRank ? '다름' : t === '나음' ? '우체국 나음' : '우체국 못함') : t;
    const its = q && q.it ? `<table class="cv-it"><tr><th scope="col">항목</th><th scope="col">우체국</th><th scope="col">${esc(orgN(peer))}</th><th scope="col">비교</th></tr>${q.it.map(t => `<tr><th scope="row">${esc(t[0])}</th><td>${esc(t[1])}</td><td>${esc(t[2])}</td><td>${esc(word(t[3]))}${t[4] ? `<br><span class="note">${esc(t[4])}</span>` : ''}</td></tr>`).join('')}</table>` : '';
    return `<div class="cv-jd"><p><b>${esc(txt.josa(fullN(peer), '과'))} 견줌</b> ${chip(v)}</p>${v && v.why ? `<p class="note">${esc(v.why)}</p>` : ''}${noRank && q && q.it && q.it.some(t => t[3] === '나음' || t[3] === '못함') ? `<p class="note">대표 급부끼리는 조건이 다른 항목이 있지만, 위 까닭으로 우열을 매기지 않았습니다. 아래 표는 "다름"으로만 적습니다.</p>` : ''}${its}</div>`;
  }).join('');
  const scopedPts = c.peerScope === 'all' ? row.pts : row.pts.filter(p => (p['관련기관코드'] || []).some(o => pSet.has(o)));
  const pts = scopedPts.map(p => `<li>${ui.tag(p['분류'])} ${p['원문대조'] ? ui.flagText(p['원문대조글']) : ''}<p>${esc(p['문장'])}</p>${p['주의'] ? `<p class="note">주의: ${esc(p['주의'])}</p>` : ''}</li>`).join('');
  const cauEv = mode === 'caution' ? scopedCau.flatMap(x => (x['근거'] || []).filter(g => g['종형ID'] === c.baseId || c.peerScope === 'all' || pSet.has(orgOf(g['종형ID']))).map(g => `<li><b>${esc(orgN(g['종형ID']))}</b> ${ui.tag(txt.pageText(g['문서'], g['쪽']))} ${g['구분'] ? ui.tag(g['구분']) : ''} <span>${esc(fixG(g['급부명'] || ''))}</span></li>`)).join('') : '';
  const out = [];
  pIdxs.forEach(i => { const v = row.verd[i]; if (v && v.kind === 'unknown') out.push(`${orgN(m.cols[i + 1])}: ${v.why || v.text}`); });
  row.omit.filter(o => c.peerScope === 'all' || (o['비교종형ID'] || []).some(v => pSet.has(orgOf(v)))).forEach(o => out.push(`${o['분류']}(${o['세부']}): ${reasonText(o['사유'])}`));
  const body = `<div class="ev-sec"><h3>판정</h3>${judge || `<p class="note">${esc(App.t('peerEmptyHint'))}</p>`}${pts ? `<h3 style="margin-top:12px">영업 인사이트의 문장</h3><ul class="cv-pts">${pts}</ul>` : ''}</div>
    <div class="ev-sec"><h3>관계도</h3><div class="cv-rel" data-sid="${esc(sid)}"></div>${relLegend()}</div>
    <div class="ev-sec"><h3>조건 비교</h3>${condTable(m, row, c)}</div>
    <div class="ev-sec lo"><h3>근거 문서와 쪽</h3>${mode === 'caution' && cauEv ? `<ul class="cv-evl">${cauEv}</ul><p class="note">"대표 밖"은 대표 급부 밖에 조건이 다른 급부입니다.</p>` : evidenceList(m, row, '', c)}</div>
    ${out.length ? `<div class="ev-sec lo"><h3>뺀 것</h3><ul class="cv-evl">${out.map(t => `<li>${esc(t)}</li>`).join('')}</ul></div>` : ''}`;
  const verdBadges = pIdxs.slice(0, 3).map(i => { const v = verdFor(row, m, i, pIdxs); return v ? `<span class="cv-bd"><span>${esc(txt.josa(orgN(m.cols[i + 1]), '과'))}</span>${chip(v)}</span>` : ''; }).join('');
  return {
    kicker: mode === 'caution' ? '단정 주의, 선택 종형' : '담보 비교, 선택 종형', title: stdN(sid),
    badges: [ui.scope('base'), ui.tag(`${st['대분류'] || ''} ${st['급부유형'] || ''}`.trim()), verdBadges],
    body,
    after(el) { drawRel(el.querySelector('.cv-rel'), c.baseId, sid); },
  };
}

// ---------- 치료 여정 격자 ----------
let fGroup = null, diffOnly = false;
function journeyData(c) {
  const j = c.base['치료여정'];
  const cols = j['종형'];
  const byVid = Object.fromEntries(cols.map(x => [x['종형ID'], x]));
  const peerCols = c.peerScope === 'all' ? cols.slice(1) : c.peerIds.map(v => byVid[v]).filter(Boolean);
  return { j, cols: [byVid[c.baseId] || cols[0], ...peerCols].filter(Boolean) };
}
function journeyHTML(c) {
  const { j, cols } = journeyData(c);
  const rowsG = j['행'];
  const compactPeers = cols.length > 4;
  const dispVals = rawVals => compactPeers ? [rawVals[0], Math.max(0, ...rawVals.slice(1))] : rawVals;
  const dispLabels = compactPeers
    ? [{ nm: orgN(cols[0]['종형ID']), title: cols[0]['이름'] }, { nm: `상대 최대(${cols.length - 1}곳)`, title: cols.slice(1).map(x => orgN(x['종형ID'])).join(', ') }]
    : cols.map(x => ({ nm: orgN(x['종형ID']), title: x['이름'] }));
  const max = Math.max(1, ...cols.flatMap(x => rowsG.flatMap(g => STEPS.map(s => (x['칸'][g] || {})[s] || 0))));
  const maxT = Math.max(1, ...cols.flatMap(x => STEPS.map(s => x['합계'][s] || 0)));
  const rowSum = (x, g) => STEPS.reduce((a, s) => a + ((x['칸'][g] || {})[s] || 0), 0);
  const maxR = Math.max(1, ...cols.flatMap(x => rowsG.map(g => rowSum(x, g))));
  const CLS = ['', 'other', 'other hollow', 'other'];
  const bars = (vals, mx) => dispVals(vals).map((n, i) => `<span class="cvj-b"><span class="hbar"><i class="${CLS[i] || 'other'}" style="width:${(n / mx * 100).toFixed(1)}%"></i></span><b class="num">${n}</b></span>`).join('');
  const lab = dispLabels.map(d => `<span class="cvj-l" title="${esc(d.title)}">${esc(d.nm)}</span>`).join('');
  let h = `<div class="cvj-h cvj-c0"></div>${STEPS.map(s => `<div class="cvj-h">${esc(s)}</div>`).join('')}<div class="cvj-h cvj-t">대분류 합계</div>`;
  rowsG.forEach(g => {
    h += `<div class="cvj-g"><span class="cvj-n">${esc(g)}</span><span class="cvj-ls">${lab}</span></div>`;
    STEPS.forEach(s => {
      const vals = cols.map(x => (x['칸'][g] || {})[s] || 0);
      const z0 = vals[0] === 0 && vals.slice(1).some(v => v > 0);
      const all0 = vals.every(v => v === 0);
      h += `<button type="button" class="sq cvj-c${z0 ? ' z0' : ''}${all0 ? ' a0' : ''}" data-pick="j:${esc(g)}:${esc(s)}" aria-label="${esc(`${g} ${s}: ${dispLabels.map((d, i) => `${d.nm} ${dispVals(vals)[i]}`).join(', ')}. 담보 목록 보기`)}">
        ${bars(vals, max)}<span class="cvj-ch" aria-hidden="true">${ui.IC.chevR}</span></button>`;
    });
    h += `<div class="cvj-c cvj-t">${bars(cols.map(x => rowSum(x, g)), maxR)}</div>`;
  });
  h += `<div class="cvj-g cvj-tt"><span class="cvj-n">단계 합계</span><span class="cvj-ls">${lab}</span></div>`;
  STEPS.forEach(s => { h += `<div class="cvj-c cvj-t">${bars(cols.map(x => x['합계'][s] || 0), maxT)}</div>`; });
  h += `<div class="cvj-c cvj-t cvj-all">${dispLabels.map((d, i) => `<span class="cvj-b"><span class="cvj-l2">${esc(d.nm)}</span><b class="num">${dispVals(cols.map(x => x['전체']))[i]}</b></span>`).join('')}</div>`;
  const ours = cols[0];
  const parts = STEPS.map(s => ({ t: s, n: ours['합계'][s] || 0 })).concat(ours['기타'] ? [{ t: '기타', n: ours['기타'] }] : []);
  const etc = txt.peerNamesEtc(cols.map(x => `${orgN(x['종형ID'])} ${x['기타'] || 0}`), 4);
  return `<section class="panel cv-jr" id="cover-journey" aria-labelledby="cover-journey-h">
    <div class="panel-h"><div><span class="k">${ui.scope('base')} 보장 대분류와 치료 단계마다 표준담보를 셉니다</span><h2 id="cover-journey-h"><span>치료 여정 격자</span>${ui.help('journey-grid', '치료 여정 격자')}</h2></div>
      <div class="r"><span class="cvj-lg"><span><i class="lg0"></i>${esc(dispLabels[0].nm)}</span>${dispLabels.slice(1).map((d, i) => `<span><i class="lg${Math.min(2, i + 1)}"></i>${esc(d.nm)}</span>`).join('')}<span><i class="lgz"></i>우체국 0인 칸</span></span>
      <span class="live">${ui.btn('격자 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="cv-copy-journey"' })}${ui.btn('인쇄', { sm: true, ghost: true, icon: 'print', attrs: 'data-print="cover-journey" data-title="치료 여정 격자"' })}</span></div></div>
    <div class="cvj-w"><div class="cvj" role="group" aria-label="치료 여정 격자">${h}</div></div>
    <div class="panel-f">${ui.eq({ total: { t: `${orgN(ours['종형ID'])} 담보`, n: ours['전체'] }, parts, tail: '개' })}
      <div class="nadd">기타(주요 단계 밖의 급부유형)는 ${esc(etc)}개입니다. 칸 하나에 담보 하나만 셉니다. 회사별 수는 같은 담보를 회사마다 세므로 서로 더하지 않습니다.</div>
      <p class="note" style="margin:6px 0 0">막대 길이는 칸끼리(합계 줄은 합계끼리) 견준 것입니다. 칸을 누르면 그 칸의 담보 목록이 오른쪽 상세 구역에 뜹니다. 우열은 이 격자에 매기지 않고 아래 비교표에서 봅니다.</p></div>
  </section>`;
}
function journeyPick(c, key) {
  const [, g, s] = key.split(':');
  const { j, cols } = journeyData(c);
  const lists = cols.map(x => ((x['담보'][g] || {})[s] || []));
  const all = [...new Set(lists.flat())];
  const m = model(c.baseId);
  const pIdxs = peerIdxOf(m, c);
  const order = m ? Object.fromEntries(m.rows.map((r, i) => [r.sid, i])) : {};
  all.sort((a, b) => (order[a] ?? 999) - (order[b] ?? 999));
  const rows = all.map(sid => {
    const row = m && m.byId[sid];
    const marks = cols.map((x, i) => lists[i].includes(sid) ? `<td class="ok">있음</td>` : `<td class="no">없음</td>`).join('');
    const v = row ? pIdxs.slice(0, 3).map(i => { const vv = verdFor(row, m, i, pIdxs); return vv ? `<span class="cv-bd"><span>${esc(txt.josa(orgN(m.cols[i + 1]), '과'))}</span>${chip(vv)}</span>` : ''; }).join('') : '';
    return `<tr><th scope="row">${row ? `<button type="button" class="cv-lk" data-act="cv-goto" data-sid="${esc(sid)}">${esc(stdN(sid))}${ui.IC.chevR}</button>` : esc(stdN(sid))}<div class="cv-bds">${v}</div></th>${marks}</tr>`;
  }).join('');
  return {
    kicker: '치료 여정 격자, 선택 종형', title: `${g} ${s}`, badges: [ui.scope('base')],
    body: `<div class="ev-sec"><h3>칸의 담보 수</h3><p>${esc(txt.peerNamesEtc(cols.map((x, i) => `${orgN(x['종형ID'])} ${lists[i].length}`), 5))}</p>
        <div class="nadd">같은 담보를 회사마다 센 수라 서로 더하지 않습니다. 이 칸에 한 회사라도 가진 담보는 ${all.length}개입니다.</div></div>
      <div class="ev-sec"><h3>담보 목록</h3>${all.length ? `<div class="cv-ct-w"><table class="cv-jt"><tr><th scope="col">담보와 판정(우체국 기준)</th>${cols.map(x => `<th scope="col" title="${esc(x['이름'])}">${esc(orgN(x['종형ID']))}</th>`).join('')}</tr>${rows}</table></div><p class="note">담보 이름을 누르면 비교표의 그 줄로 갑니다.</p>` : '<p>이 칸에는 비교 대상 회사 모두 담보가 없습니다.</p>'}</div>`,
  };
}

// ---------- 단정 주의와 보류 요약 ----------
function scopedCaution(c) {
  const raw = (c.base && c.base['단정주의']) || [];
  if (c.peerScope === 'all') return raw;
  const pSet = new Set(c.activePeerOrgs || []);
  return raw.filter(x => (x['상대종형ID'] || []).some(v => pSet.has(orgOf(v))));
}
function cautionHTML(c) {
  const cau = scopedCaution(c);
  const kinds = [];
  cau.forEach(x => { let k = kinds.find(y => y.k === x['종류']); if (!k) kinds.push(k = { k: x['종류'], xs: [] }); k.xs.push(x); });
  const pSet = new Set(c.activePeerOrgs || []);
  const peerName = x => {
    const vids = c.peerScope === 'all' ? (x['상대종형ID'] || []) : (x['상대종형ID'] || []).filter(v => pSet.has(orgOf(v)));
    return txt.peerNamesEtc(vids.map(fullN), 3);
  };
  return `<section class="panel cv-cau" id="cover-caution" aria-labelledby="cover-caution-h">
    <div class="panel-h"><div><span class="k">${ui.scope('base')} 우열 문장을 내지 않은 비교와 까닭</span><h2 id="cover-caution-h">단정 주의 ${cau.length}건</h2></div>
      <div class="r"><span class="live">${ui.btn('목록 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="cv-copy-caution"' })}${ui.btn('인쇄', { sm: true, ghost: true, icon: 'print', attrs: 'data-print="cover-caution" data-title="단정 주의 목록"' })}</span></div></div>
    ${kinds.map(k => `<div class="cv-kh"><span>${esc(k.k)}</span><b class="num">${k.xs.length}</b></div>
      <ul class="lrows">${k.xs.map(x => `<li class="lrow cv-cr" data-pick="c:${esc(x['표준담보ID'])}">
        <button type="button" class="lrow-hit" aria-pressed="false" aria-label="${esc(`${x['담보']}, ${k.k}. 근거 보기`)}"></button>
        <div class="cv-crh selbar">${ui.verdict('diff')}<span class="cv-cn">${esc(x['담보'])}</span></div>
        <p class="cv-cpe">상대 ${esc(peerName(x))}</p>
        <p class="cv-ctx">${esc(x['문장'])}</p>
        <span class="lrow-chev" aria-hidden="true">${ui.IC.chevR}</span></li>`).join('')}</ul>`).join('') || '<p class="placeholder">단정 주의에 든 담보가 없습니다.</p>'}
  </section>`;
}
function pendingHTML(c) {
  const p = c.base['보류요약'];
  const pSet = new Set(c.activePeerOrgs || []);
  const peers = c.peerScope === 'all' ? (p['맞붙는종형'] || c.peerIds) : c.peerIds;
  const sp = c.peerScope === 'all' ? { total: p['공통담보쌍'], wait: p['뺀쌍'], cmp: p['견준쌍'] } : (scopedPairs(c.baseId, pSet) || { total: 0, wait: 0, cmp: 0 });
  const why = p['사유별'] || {};
  const whySum = Object.values(why).reduce((a, b) => a + b, 0);
  const B = CV && CV.b[c.baseId];
  const rows = (p['대분류'] || []).map(x => {
    let rowTot = x['공통담보쌍'], rowWait = x['뺀쌍'], rowCmp = x['견준쌍'];
    if (c.peerScope !== 'all' && B) {
      rowTot = 0; rowWait = 0;
      B.rows.forEach(r => {
        if ((std(r[0])['대분류'] || '') !== x['대분류']) return;
        for (const [peer, q] of Object.entries(r[2] || {})) {
          if (pSet.has(orgOf(peer))) { rowTot++; if (q && q.x) rowWait++; }
        }
      });
      rowCmp = rowTot - rowWait;
    }
    return [`<span class="nw">${esc(x['대분류'])}</span>`, `<span class="num">${rowTot}</span>`, `<span class="num">${rowCmp}</span>`, `<span class="num">${rowWait}</span>`,
      ...peers.map(v => `<span class="num">${(x['상대별'] || {})[v] || 0}</span>`)];
  });
  const cellsBar = sp.total <= 80 ? ui.cells(Array(sp.cmp).fill('cmp').concat(Array(sp.wait).fill('wait'))) : '';
  return `<section class="panel tbl-wrap cv-pd" id="cover-pending" aria-labelledby="cover-pending-h">
    <div class="panel-h"><div><span class="k">${ui.scope('base')} 공통 담보 쌍 가운데 검토 대기로 뺀 쌍</span><h2 id="cover-pending-h">검토 대기 보류 요약</h2></div>
      <div class="r"><span class="live">${ui.btn('표 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-copy="cover-pd-tbl" data-title="검토 대기 보류 요약"' })}${ui.btn('인쇄', { sm: true, ghost: true, icon: 'print', attrs: 'data-print="cover-pending" data-title="검토 대기 보류 요약"' })}</span></div></div>
    <div class="cv-pd-eq">${ui.eq({ total: { t: '공통 담보', n: sp.total }, parts: [{ t: '견줌', n: sp.cmp }, { t: '검토 대기로 뺌', n: sp.wait }], tail: '쌍' })}
      ${cellsBar}
      ${c.peerScope === 'all' && Object.keys(why).length ? `<div class="nadd">뺀 사유는 ${esc(Object.entries(why).map(([a, b]) => `${a} ${b}`).join(', '))}쌍입니다. ${whySum > p['뺀쌍'] ? `한 쌍에 두 사유가 함께 들 수 있어 더하면 ${esc(txt.josa(String(whySum), '으로'))} ${p['뺀쌍']}보다 큽니다.` : `사유를 더하면 ${whySum}쌍입니다.`}</div>` : ''}</div>
    <div class="cv-pd-t">${ui.table({ id: 'cover-pd-tbl', head: ['보장 대분류', '공통 쌍', '견줌', '검토 대기', ...peers.map(v => `${esc(orgN(v))} 대기`)], rows, num: [1, 2, 3, ...peers.map((_, i) => i + 4)] })}</div>
    <div class="panel-f">${cellsBar ? '띠의 칸 하나가 한 쌍입니다: <span class="kd-l"><i class="cq cmp"></i>견준 쌍</span> <span class="kd-l"><i class="cq wait"></i>검토 대기로 뺀 쌍</span>. ' : ''}상대별 대기 수는 그 상대와의 쌍에서 뺀 수이고, 선택한 상대를 더하면 그 줄의 검토 대기 쌍과 같습니다.</div>
  </section>`;
}

// ---------- 구역 머리 ----------
function midBand(c) {
  const p = c.base['보류요약'];
  const pSet = new Set(c.activePeerOrgs || []);
  const sp = c.peerScope === 'all' ? { total: p['공통담보쌍'], wait: p['뺀쌍'], cmp: p['견준쌍'] } : (scopedPairs(c.baseId, pSet) || { total: 0, wait: 0, cmp: 0 });
  const cau = scopedCaution(c);
  const kinds = {};
  cau.forEach(x => { kinds[x['종류']] = (kinds[x['종류']] || 0) + 1; });
  const stats = [{ n: sp.cmp, d: sp.total, l: '견준 공통 담보 쌍', bar: [sp.cmp, Math.max(1, sp.total)] },
    { n: sp.wait, d: sp.total, l: '검토 대기로 뺀 쌍', bar: [sp.wait, Math.max(1, sp.total), 'other'] }]
    .concat(Object.entries(kinds).map(([k, n]) => ({ n, u: '건', l: `단정 주의: ${k}` })));
  return ui.band({ kicker: '우열을 단정하지 않은 것과 견주지 못한 것', title: '단정 주의와 검토 대기', help: 'caution-pending', sc: 'base', stats,
    note: `단정 주의 ${cau.length}건은 견준 쌍 안에서 우열 문장을 내지 않은 담보이고, 검토 대기로 뺀 쌍과는 다른 수라 더하지 않습니다.` });
}
function tableBand(c, m, cnt, peerN) {
  const total = m.rows.length * peerN;
  const denom = Math.max(1, total);
  const st = (k, l, cls) => ({ n: cnt[k], d: total, l, bar: [cnt[k], denom, cls] });
  return ui.band({ kicker: `우체국 ${kindN(c.baseId)} 기준, 담보 ${m.rows.length}줄과 상대 ${peerN}곳`, title: '담보 비교표의 판정', sc: 'base',
    stats: [st('better', '우체국 나음', 'gold'), st('only', '우체국에만 있음', 'gold'), st('worse', '우체국 못함', ''), st('none', '우체국에 없음', 'other')],
    note: `판정 칸 ${total}개 가운데 넷을 크게 보였습니다. 나머지(같음, 우열을 매기지 않음, 검토 대기, 둘 다 없음)는 아래 줄에 수를 적었습니다.` });
}

// ---------- 담보 비교표 ----------
function compCell(row, k, vid) {
  const c = row.cells[k];
  if (has(c)) {
    const b = repOf(c);
    const extra = [c.n > 1 ? `같은 담보 급부 ${c.n}개 가운데 대표 급부` : '', c.o ? `대표와 조건이 다른 줄 ${c.o}개` : '', c.w ? `매핑 대기 ${c.w}줄` : ''].filter(Boolean).join(', ');
    return `<td class="cv-c k${k}" data-l="${esc(orgN(vid))}"><span class="cv-v${extra ? ' has-x' : ''}"${extra ? ` title="${esc(extra)}"` : ''}><span class="pv num">${esc(payText(b))}</span><span class="wv num">${esc(waitText(b.wait))}</span><span class="rv num">${esc(redShort(b.red))}</span></span></td>`;
  }
  const t = c && c.w ? `검토 대기 ${c.w}줄` : c && c.c ? `없음, ${txt.josa(c.c[0], '으로')} 덮음` : '없음';
  return `<td class="cv-c k${k}" data-l="${esc(orgN(vid))}"><span class="cv-x${c && c.w ? ' wait' : ''}">${esc(t)}</span></td>`;
}
function tableRows(c) {
  const m = model(c.baseId);
  const pIdxs = peerIdxOf(m, c);
  const colIdxs = [0].concat(pIdxs.map(i => i + 1));
  const colSpan = 2 + colIdxs.length + pIdxs.length;
  let rows = m.rows;
  if (fGroup) rows = rows.filter(r => r.major === fGroup);
  if (diffOnly) rows = rows.filter(r => pIdxs.some(i => { const v = verdFor(r, m, i, pIdxs); return v && v.kind !== 'same'; }));
  let html = '', last = '';
  const cnt = {};
  rows.forEach(r => { cnt[r.major] = (cnt[r.major] || 0) + 1; });
  const pSet = new Set(c.activePeerOrgs || []);
  rows.forEach(r => {
    if (r.major !== last) { last = r.major; html += `<tr class="cv-gh no-copy"><th colspan="${colSpan}" scope="colgroup"><span class="cv-ghn">${esc(r.major)}</span> <span class="num">${cnt[r.major]}</span>줄</th></tr>`; }
    const flag = r.pts.some(p => p['원문대조'] && (c.peerScope === 'all' || (p['관련기관코드'] || []).some(o => pSet.has(o)))) ? ui.flag() : '';
    html += `<tr class="pick" data-pick="s:${esc(r.sid)}" tabindex="0" aria-label="${esc(`${stdN(r.sid)}. 근거 보기`)}">
      <td class="cv-n">${flag}<span class="nm">${esc(stdN(r.sid))}</span><span class="sub">${esc(r.type)}</span></td>
      ${colIdxs.map(k => compCell(r, k, m.cols[k])).join('')}
      ${pIdxs.map(i => { const v = verdFor(r, m, i, pIdxs); return `<td data-l="${esc(txt.josa(orgN(m.cols[i + 1]), '과'))} 견줌" class="cv-vd${v && v.kind === 'better' ? ' vl-better' : v && v.kind === 'worse' ? ' vl-worse' : ''}">${chip(v)}</td>`; }).join('')}
      <td class="cv-ch" aria-hidden="true">${ui.IC.chevR}</td></tr>`;
  });
  return { html, n: rows.length, total: m.rows.length };
}
function tableHTML(c) {
  const m = model(c.baseId);
  if (!m) return `<section class="panel"><p class="placeholder">비교 자료 없음: 이 기준 종형의 비교쌍 자료가 tab4 자료에 없습니다.</p></section>`;
  const pIdxs = peerIdxOf(m, c);
  const colIdxs = [0].concat(pIdxs.map(i => i + 1));
  const peerN = pIdxs.length;
  const totCells = m.rows.length * peerN;
  const groups = [...new Set(m.rows.map(r => r.major))];
  const t = tableRows(c);
  const cnt = { better: 0, worse: 0, same: 0, diff: 0, only: 0, none: 0, unknown: 0 };
  m.rows.forEach(r => pIdxs.forEach(i => { const v = verdFor(r, m, i, pIdxs); if (v) cnt[v.kind]++; }));
  const head2 = '<span class="cv-v hd"><span class="pv">지급</span><span class="wv">면책</span><span class="rv">감액</span></span>';
  return `${tableBand(c, m, cnt, peerN)}<section class="panel tbl-wrap cv-tb" id="cover-table" aria-labelledby="cover-table-h">
    <div class="panel-h"><div><span class="k">${ui.scope('base')} 표준담보마다 대표 급부끼리, 우체국 기준</span><h2 id="cover-table-h">담보 비교표</h2></div>
      <div class="r"><span class="live">${ui.btn('표 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-act="cv-copy-table"' })}${ui.btn('인쇄', { sm: true, ghost: true, icon: 'print', attrs: 'data-print="cover-table" data-title="담보 비교표"' })}</span></div></div>
    <div class="cv-tools">
      <div class="cv-seg" role="group" aria-label="보장 대분류 거르기">
        <button type="button" class="cv-sb" data-act="cv-group" data-v="" aria-pressed="${!fGroup}">전체</button>
        ${groups.map(g => `<button type="button" class="cv-sb" data-act="cv-group" data-v="${esc(g)}" aria-pressed="${fGroup === g}">${esc(g)}</button>`).join('')}
      </div>
      <button type="button" class="sw" role="switch" aria-checked="${diffOnly}" data-act="cv-diff"><i></i>다른 것만 보기</button>
      <span class="cv-cnt" aria-live="polite">${t.n === t.total ? `${t.total}줄` : `${t.total}줄 가운데 ${t.n}줄`}</span>
    </div>
    <div class="cv-sum">판정 칸 ${totCells}개(담보 ${m.rows.length}줄, 상대 ${peerN}곳): ${['better', 'worse', 'same', 'diff', 'only', 'none', 'unknown'].map(k => `${ui.verdict(k, k === 'unknown' ? '검토 대기, 판정 보류' : null)} <b class="num">${cnt[k]}</b>`).join(' ')} <span class="note">나머지 ${totCells - Object.values(cnt).reduce((a, b) => a + b, 0)}칸은 둘 다 없음</span></div>
    <div class="cv-tw"><table class="tbl cv-t" id="cover-tbl">
      <thead><tr><th scope="col" rowspan="2" class="cv-n">담보</th>${colIdxs.map(k => { const v = m.cols[k]; return `<th scope="col" class="cv-c k${k}" title="${esc(fullN(v))}">${esc(orgN(v))} <span class="sub">${esc(txt.shortName(kindN(v)).short)}</span>${k ? '' : ' ' + ui.tag('기준')}</th>`; }).join('')}
        ${pIdxs.map(i => { const v = m.cols[i + 1]; return `<th scope="col" class="cv-vd" rowspan="2">${esc(txt.josa(orgN(v), '과'))} 견줌<br><span class="sub">우체국 기준</span></th>`; }).join('')}<th rowspan="2" class="cv-ch"><span class="sr">고르기</span></th></tr>
        <tr class="cv-h2">${colIdxs.map(k => `<th scope="col" class="cv-c k${k}">${head2}</th>`).join('')}</tr></thead>
      <tbody>${t.html}</tbody></table></div>
    <p class="cv-narrow">본문이 좁아 상대 회사의 지급, 면책, 감액 칸을 접었습니다. 줄을 누르면 오른쪽 상세 구역의 조건 비교에 비교 대상 회사 값이 나옵니다.</p>
    <div class="panel-f">대표 급부는 같은 담보의 급부 가운데 주급부, 금액이 큰 줄, 조건이 엄격한 줄 차례로 고릅니다. 줄을 누르면 오른쪽 상세 구역에 관계도, 조건 비교, 근거 문서와 쪽이 뜹니다. 지급액은 기준 가입금액에서의 금액이라 회사끼리 바로 견주지 않습니다.</div>
  </section>`;
}
function refreshTable(body, c) {
  const tb = body.querySelector('#cover-tbl tbody');
  if (!tb) return;
  const t = tableRows(c);
  tb.innerHTML = t.html;
  body.querySelectorAll('[data-act="cv-group"]').forEach(b => b.setAttribute('aria-pressed', String((b.dataset.v || null) === fGroup)));
  const sw = body.querySelector('[data-act="cv-diff"]'); if (sw) sw.setAttribute('aria-checked', String(diffOnly));
  const cn = body.querySelector('.cv-cnt'); if (cn) cn.textContent = t.n === t.total ? `${t.total}줄` : `${t.total}줄 가운데 ${t.n}줄`;
  const key = App.state.sel.cover;
  tb.querySelectorAll('[data-pick]').forEach(el => el.classList.toggle('is-sel', el.dataset.pick === key));
  App.fitSel();
}

// ---------- 복사 ----------
function copyJourney() {
  const c = App.ctx();
  const { j, cols } = journeyData(c);
  const rows = [];
  j['행'].forEach(g => cols.forEach(x => rows.push([g, x['이름'], ...STEPS.map(s => (x['칸'][g] || {})[s] || 0), STEPS.reduce((a, s) => a + ((x['칸'][g] || {})[s] || 0), 0)])));
  cols.forEach(x => rows.push(['단계 합계', x['이름'], ...STEPS.map(s => x['합계'][s] || 0), x['전체'] - (x['기타'] || 0)]));
  cols.forEach(x => rows.push(['기타(주요 단계 밖)', x['이름'], '', '', '', '', '', x['기타'] || 0]));
  App.copyRows(['보장 대분류', '종형', ...STEPS, '합계'], rows, { title: '치료 여정 격자(표준담보 수)' });
}
function copyCaution() {
  const c = App.ctx();
  const rows = scopedCaution(c).map(x => [x['종류'], x['담보'], (x['상대종형ID'] || []).map(fullN).join(', '), '우열을 매기지 않음', x['문장'],
    (x['근거'] || []).map(g => `${orgN(g['종형ID'])} ${txt.pageText(g['문서'], g['쪽'])}${g['구분'] ? `(${g['구분']})` : ''}`).join('; ')]);
  App.copyRows(['종류', '담보', '상대', '판정', '문장', '근거'], rows, { title: '단정 주의 목록' });
}
function copyTable() {
  const c = App.ctx();
  const m = model(c.baseId);
  const pIdxs = peerIdxOf(m, c);
  const colIdxs = [0].concat(pIdxs.map(i => i + 1));
  let rows = m.rows;
  if (fGroup) rows = rows.filter(r => r.major === fGroup);
  if (diffOnly) rows = rows.filter(r => pIdxs.some(i => { const v = verdFor(r, m, i, pIdxs); return v && v.kind !== 'same'; }));
  const head = ['보장 대분류', '담보', '급부유형'];
  colIdxs.forEach(k => { const v = m.cols[k]; head.push(`${orgN(v)} 지급`, `${orgN(v)} 면책`, `${orgN(v)} 감액`); });
  pIdxs.forEach(i => { const v = m.cols[i + 1]; head.push(`${txt.josa(orgN(v), '과')} 견줌(우체국 기준)`); });
  head.push('까닭');
  App.copyRows(head, rows.map(r => {
    const out = [r.major, stdN(r.sid), r.type];
    colIdxs.forEach(k => {
      const c2 = r.cells[k], b = repOf(c2);
      if (b) out.push(payText(b), waitText(b.wait), redShort(b.red));
      else out.push(c2 && c2.w ? `검토 대기 ${c2.w}줄` : c2 && c2.c ? `없음(${c2.c[0]})` : '없음', '', '');
    });
    pIdxs.forEach(i => out.push(chipText(verdFor(r, m, i, pIdxs))));
    out.push(pIdxs.map(i => { const v = verdFor(r, m, i, pIdxs); return v && v.why ? `${orgN(m.cols[i + 1])}: ${v.why}` : ''; }).filter(Boolean).join(' / '));
    return out;
  }), { title: `담보 비교표${fGroup ? ` (${fGroup})` : ''}${diffOnly ? ' (다른 것만)' : ''}` });
}

// ---------- 그리기 ----------
function concl(c) {
  const p = c.base['보류요약'];
  const pSet = new Set(c.activePeerOrgs || []);
  const sp = c.peerScope === 'all' ? { total: p['공통담보쌍'], wait: p['뺀쌍'], cmp: p['견준쌍'] } : (scopedPairs(c.baseId, pSet) || { total: 0, wait: 0, cmp: 0 });
  const j = journeyData(c).cols[0];
  const cau = scopedCaution(c);
  return `<p class="concl">공통 담보 ${sp.total}쌍 가운데 ${sp.cmp}쌍을 견줬고(검토 대기 ${sp.wait}쌍 뺌), 우체국 ${esc(kindN(c.baseId))}의 담보 ${j['전체']}개는 ${STEPS.map(s => `${s} ${j['합계'][s] || 0}`).join(', ')}입니다. 우열을 단정하지 않은 담보는 ${cau.length}건입니다.</p>`;
}
function refNote(c) {
  const parts = [];
  if (!c.isRef) parts.push(`지금 조건(${App.condSegOnly()})을 바꿔도 이 탭의 값은 그대로입니다. 담보 비교는 나이 조건 없이 대표 급부끼리 견준 값이고, 기준 종형을 바꿀 때만 다시 셉니다.`);
  if (c.st.renewal) parts.push('갱신 유형 거르개는 고객군 지도에만 씁니다.');
  return parts.length ? `<p class="cv-ref">${esc(parts.join(' '))}</p>` : '';
}
function render(body, c) {
  if (!CV || !c.base) { body.innerHTML = '<div class="panel placeholder">비교 자료 없음: tab4 자료 줄(CV)이 비었습니다. gen_cover.py 를 돌립니다.</div>'; return; }
  body.innerHTML = `${concl(c)}${refNote(c)}${journeyHTML(c)}${midBand(c)}<div class="cv-mid">${cautionHTML(c)}${pendingHTML(c)}</div>${tableHTML(c)}`;
  bind(body);
}
function bind(body) {
  if (body._b) return;
  body._b = true;
  body.addEventListener('click', e => {
    const a = e.target.closest('[data-act]');
    if (!a) return;
    const act = a.dataset.act;
    const c = App.ctx();
    if (act === 'cv-group') { fGroup = a.dataset.v || null; refreshTable(body, c); }
    else if (act === 'cv-diff') { diffOnly = !diffOnly; refreshTable(body, c); }
    else if (act === 'cv-copy-journey') copyJourney();
    else if (act === 'cv-copy-caution') copyCaution();
    else if (act === 'cv-copy-table') copyTable();
  });
}
// 근거 기둥 안의 "비교표에서 보기"(기둥은 본문 밖이라 문서에 붙인다)
document.addEventListener('click', e => {
  const a = e.target.closest('[data-act="cv-goto"]');
  if (!a) return;
  const sid = a.dataset.sid;
  if (App.state.tab !== 'cover') App.go('cover');
  const view = document.getElementById('view-cover');
  const body = view && view.querySelector('.vbody');
  if (body && (fGroup || diffOnly)) {
    const m = model(App.state.base); const r = m && m.byId[sid];
    if (r && ((fGroup && r.major !== fGroup) || (diffOnly && r.same))) { fGroup = null; diffOnly = false; refreshTable(body, App.ctx()); }
  }
  setTimeout(() => {
    App.select('s:' + sid);
    const el = view && view.querySelector(`[data-pick="s:${CSS.escape(sid)}"]`);
    if (el) { if (App.mode() === 'sheet') App.reveal(el); else el.scrollIntoView({ block: 'center', behavior: App.motionOn() ? 'smooth' : 'auto' }); }
  }, 40);
});
function pick(key, c) {
  if (key.startsWith('s:')) return rowEvidence(c, key.slice(2), 'row');
  if (key.startsWith('c:')) return rowEvidence(c, key.slice(2), 'caution');
  if (key.startsWith('j:')) return journeyPick(c, key);
  return null;
}
function evidence(c) {
  const r = c.base ? c.base['범위'] : null;
  const peerNames = c.peerIds.length ? txt.peerNamesEtc(c.peerIds.map(fullN), 3) : App.t('condPeerNone');
  return {
    kicker: '읽는 법', title: '담보 비교의 판정', badges: [ui.scope('base')],
    body: `<div class="ev-sec"><h3>무엇을 견주나</h3>
        <p>우체국 ${esc(txt.josa(kindN(c.baseId), '와'))} 맞붙는 ${esc(txt.josa(peerNames, '를'))} 표준담보마다 견줍니다. 같은 담보를 둘 다 가지면 대표 급부끼리 면책, 감액, 지급 형태로 판정하고, 한쪽에만 있으면 누구에게 없는지 적습니다.</p>
        <p class="note">상대가 조건이 다른 특약을 함께 팔거나 지급 형태가 다른 담보는 "우열을 매기지 않음"으로 둡니다(단정 주의). 검토 대기 급부가 걸린 쌍은 견주지 않았습니다.</p>
        ${r ? `<p class="note">${esc(r['문장'])}</p>` : ''}</div>
      <div class="ev-sec"><h3>조건을 바꿀 때</h3><p class="note">담보 비교는 나이 조건 없이 대표 급부끼리 견준 값이라 나이, 성별, 이력을 바꿔도 그대로입니다. 기준 종형을 바꾸면 짝과 판정을 다시 셉니다.</p></div>
      <div class="ev-sec lo"><h3>판정 표지</h3>${App.ev.legend()}</div>`,
  };
}
function focus(key, body) {
  const id = key === 'journey' ? 'cover-journey' : key === 'caution' ? 'cover-caution' : key === 'table' ? 'cover-table' : '';
  const el = id && body.querySelector('#' + id);
  if (el) el.scrollIntoView({ block: 'start', behavior: App.motionOn() ? 'smooth' : 'auto' });
}
function enter(body) {
  if (!App.motionOn()) return;
  const bars = body.querySelectorAll('.cvj .hbar > i');
  bars.forEach(i => { i.dataset.w = i.style.width; i.style.transition = 'none'; i.style.width = '0%'; });
  void body.offsetWidth;
  requestAnimationFrame(() => requestAnimationFrame(() => bars.forEach(i => { i.style.transition = ''; i.style.width = i.dataset.w; })));
}
function update(body, c) {
  if (c.changed.has('base') || c.changed.has('peerScope') || c.changed.has('peerPick')) return false;
  const old = body.querySelector('.cv-ref');
  const html = refNote(c);
  if (old) { if (html) old.outerHTML = html; else old.remove(); }
  else if (html) body.querySelector('.concl').insertAdjacentHTML('afterend', html);
  return true;
}

// 탭 5 와 core.js, tab1.js 가 쓰는 것
App.cover = {
  rawB: baseId => (CV && CV.b ? CV.b[baseId] || null : null),
  model, scopedPairs, verdictOf: (baseId, sid) => { const m = model(baseId); const r = m && m.byId[sid]; return r ? r.verd : null; },
  rel: drawRel, relLegend, chipText, hasRow: (baseId, sid) => { const m = model(baseId); return !!(m && m.byId[sid]); },
  peerCols: baseId => { const m = model(baseId); return m ? m.cols : []; },
};

App.registerTab({ id: 'cover', kicker: '좁혀 확인한다, 담보', render, update, pick, evidence, focus, enter });
