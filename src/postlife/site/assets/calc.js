/* 화면 4의 조합 계산과 금액 표기. 화면 요소를 건드리지 않는 순수 함수만 둔다.
   evaluate, payouts, pickRep, scaled는 src/postlife/site/combo.py, compare.py의 같은 이름 함수와 규칙이 같아야 한다.
   시험(tests/test_site.py)이 같은 입력을 양쪽에 넣어 결과를 맞대 본다. */
var PostlifeCalc = (function () {
  'use strict';

  function comma(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  /* 만 원 단위 숫자를 "1,000만원", "2만5천원", "1억 2,000만원"처럼 적는다. 값이 없으면 "자료 없음". */
  function money(value) {
    if (value === null || value === undefined || isNaN(value)) return '자료 없음';
    var won = Math.round(Number(value) * 10000);
    var sign = won < 0 ? '-' : '';
    won = Math.abs(won);
    if (won === 0) return '0원';
    var eok = Math.floor(won / 100000000);
    var man = Math.floor((won % 100000000) / 10000);
    var rest = won % 10000;
    var tail = '';
    if (man) tail += comma(man) + '만';
    if (rest) tail += rest % 1000 === 0 ? (rest / 1000) + '천' : comma(rest);
    var out = eok ? comma(eok) + '억' + (tail ? ' ' + tail : '') : tail;
    return sign + out + '원';
  }

  /* 가입금액이 amount일 때의 지급액: 기준지급금액 ÷ 기준가입금액 × 가입금액 */
  function scaled(pay, base, amount) {
    if (pay === null || pay === undefined || !base || amount === null || amount === undefined) return null;
    return pay / base * amount;
  }

  /* 대표 줄 고르기: 주급부 우선, 금액이 큰 줄, 같으면 기준지급금액이 큰 줄, 그래도 같으면 조건이 엄격한 줄 */
  function pickRep(cands) {
    if (!cands.length) return null;
    var mains = cands.filter(function (c) { return c.role === '주급부'; });
    var pool = mains.length ? mains : cands;
    function key(c) {
      return [-(c.val === null || c.val === undefined ? -1 : c.val), -(c.pay || 0), -(c.wait || 0),
        (c.red && c.red.length) ? 0 : 1, String(c.name)];
    }
    var sorted = pool.slice().sort(function (a, b) {
      var ka = key(a), kb = key(b);
      for (var i = 0; i < ka.length; i++) {
        if (ka[i] < kb[i]) return -1;
        if (ka[i] > kb[i]) return 1;
      }
      return 0;
    });
    return sorted[0].i;
  }

  function ceiling(rule, baseAmount) {
    if (rule.num === null || rule.num === undefined) return baseAmount;
    if (rule.unit === '만원') return Number(rule.num);
    return baseAmount === null || baseAmount === undefined ? null : baseAmount * Number(rule.num);
  }

  function sameMap(a, b) {
    var ka = Object.keys(a), kb = Object.keys(b);
    if (ka.length !== kb.length) return false;
    return ka.every(function (k) { return Object.prototype.hasOwnProperty.call(b, k) && a[k] === b[k]; });
  }

  /* 고른 조합에 제약을 적용한다.
     vm: 종형의 조합 자료, k: 조건 번호, want: {특약ID: 원하는 가입금액}. 금액이 null이면 고를 수 있는 최대.
     주계약은 want에 없어도 가입한 것으로 본다. reasons가 비어 있지 않은 특약은 고를 수 없다. */
  function evaluate(vm, k, want) {
    var order = vm.riders.map(function (r) { return r.tid; });
    var byId = {};
    vm.riders.forEach(function (r) { byId[r.tid] = r; });
    var main = vm.main;
    var has = function (obj, key) { return Object.prototype.hasOwnProperty.call(obj, key); };
    var selected = {};
    Object.keys(want).forEach(function (t) { if (has(byId, t)) selected[t] = true; });
    if (main && has(byId, main)) selected[main] = true;
    var amounts = {};
    var rows = [];
    for (var pass = 0; pass < order.length + 3; pass++) {
      var newSelected = {}, newAmounts = {}, done = {};
      rows = [];
      var isOn = function (tid) { return done[tid] ? !!newSelected[tid] : !!selected[tid]; };
      var amountOf = function (tid) {
        var src = done[tid] ? newAmounts : amounts;
        return has(src, tid) ? src[tid] : null;
      };
      order.forEach(function (tid) {
        var r = byId[tid];
        var lo = r.min || 0;
        var hi = r.lim[k];
        var reasons = [];
        var forced = false;
        if (!r.ok[k]) reasons.push({code: 'age'});
        if (tid !== main && (!main || !isOn(main))) reasons.push({code: 'main'});
        vm.rules.forEach(function (rule) {
          if (rule.target !== tid) return;
          var base = rule.base;
          if (rule.type === '선행가입') {
            if (!isOn(base)) { if (base !== main) reasons.push({code: 'need', base: base}); }   // 주계약이 기준이면 'main' 사유와 같은 말
            else if (rule.num !== null && rule.num !== undefined && rule.unit === '만원' && (amountOf(base) || 0) < rule.num) {
              reasons.push({code: 'needAmount', base: base, num: rule.num});
            }
          } else if (rule.type === '최대연동') {
            if (!isOn(base)) { if (base !== main) reasons.push({code: 'need', base: base}); }
            else {
              var top = ceiling(rule, amountOf(base));
              if (top !== null && top !== undefined && (hi === null || hi === undefined || top < hi)) hi = top;
            }
          } else if (rule.type === '배타선택') {
            if (isOn(base)) reasons.push({code: 'exclusive', base: base});
          } else if (rule.type === '의무부가') {
            if (isOn(base)) forced = true;
          }
        });
        if (hi === undefined) hi = null;
        if (!reasons.length && hi !== null && lo > hi) reasons.push({code: 'belowMin', hi: hi});
        var on = !reasons.length && (tid === main || has(want, tid) || forced);
        var amount = null, clamped = false;
        if (on) {
          var asked = has(want, tid) && want[tid] !== undefined ? want[tid] : null;
          amount = asked !== null ? asked : (hi !== null ? hi : (r.max !== null && r.max !== undefined ? r.max : lo));
          if (hi !== null && amount > hi) amount = hi;
          if (amount < lo) amount = lo;
          clamped = asked !== null && amount !== asked;
          newSelected[tid] = true;
          newAmounts[tid] = amount;
        }
        done[tid] = true;
        rows.push({tid: tid, on: on, amount: amount, lo: lo, hi: hi, reasons: reasons, forced: forced && on, clamped: clamped});
      });
      if (sameMap(newSelected, selected) && sameMap(newAmounts, amounts)) break;
      selected = newSelected;
      amounts = newAmounts;
    }
    return {rows: rows};
  }

  /* 가입한 특약의 급부를 가입금액에 비례해 환산하고 표준담보별로 묶는다.
     한 표준담보에 줄이 여럿이면 더하지 않고 대표 줄을 고른다. */
  function payouts(vm, benefits, rows) {
    var byId = {};
    vm.riders.forEach(function (r) { byId[r.tid] = r; });
    var groups = {}, order = [], others = [];
    rows.forEach(function (row) {
      if (!row.on) return;
      byId[row.tid].benefits.forEach(function (bid) {
        var b = benefits[bid];
        var val = scaled(b.pay, b.base, row.amount);
        var line = {bid: bid, val: val, reduced: (b.red || []).map(function (s) { return [s[0], val === null ? null : val * s[1]]; })};
        if (b.std) {
          if (!groups[b.std]) { groups[b.std] = []; order.push(b.std); }
          groups[b.std].push(line);
        } else {
          others.push(line);
        }
      });
    });
    return {
      groups: order.map(function (std) {
        var lines = groups[std];
        var cands = lines.map(function (l, i) {
          var b = benefits[l.bid];
          return {i: i, role: b.role, val: l.val, pay: b.pay, wait: b.wait, red: b.red, name: b.name};
        });
        return {std: std, rep: pickRep(cands), lines: lines};
      }),
      others: others
    };
  }

  /* 줄여 적은 자료를 원래 모양으로 되살린다. src/postlife/site/pack.py의 unpack과 규칙이 같아야 한다.
     "~번호"는 글자 목록(s)의 자리, "~~…"는 "~"로 시작하는 글자 그대로.
     {"~=": [값, 개수]} 같은 값 반복 / {"~+": [조각…]} " · "로 이어 붙인 글자 /
     {"~#": [[키…], [값…]…]} 키가 같은 묶음의 배열 / {"~@": [[키…], [이름, 값…]…]} 키가 같은 묶음의 묶음 */
  function unpack(packed) {
    var table = packed.s;
    function word(text) {
      if (text.charAt(0) !== '~') return text;
      if (text.charAt(1) === '~') return text.slice(1);
      return table[parseInt(text.slice(1), 36)];
    }
    function record(keys, row, from) {
      var out = {};
      for (var i = 0; i < keys.length; i++) out[keys[i]] = dec(row[i + from]);
      return out;
    }
    function dec(node) {
      if (typeof node === 'string') return word(node);
      if (node === null || typeof node !== 'object') return node;
      if (Array.isArray(node)) return node.map(dec);
      var names = Object.keys(node);
      if (names.length === 1) {
        var kind = names[0], body = node[kind], keys, out, i;
        if (kind === '~=') {
          out = [];
          var value = dec(body[0]);
          for (i = 0; i < body[1]; i++) out.push(value);
          return out;
        }
        if (kind === '~+') return body.map(word).join(' · ');
        if (kind === '~#') {
          keys = body[0].map(word);
          out = [];
          for (i = 1; i < body.length; i++) out.push(record(keys, body[i], 0));
          return out;
        }
        if (kind === '~@') {
          keys = body[0].map(word);
          out = {};
          for (i = 1; i < body.length; i++) out[word(body[i][0])] = record(keys, body[i], 1);
          return out;
        }
      }
      var plain = {};
      names.forEach(function (name) { plain[word(name)] = dec(node[name]); });
      return plain;
    }
    return dec(packed.d);
  }

  return {money: money, comma: comma, scaled: scaled, pickRep: pickRep, evaluate: evaluate, payouts: payouts, unpack: unpack};
})();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = PostlifeCalc;
}
