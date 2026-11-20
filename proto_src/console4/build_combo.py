"""시안 4 가입 관문 탭(tab3)의 미리 계산한 자료를 만든다: 구성 예시(combo.json)와 관문 나무(gate.json).

쓰기: python proto_src/console4/build_combo.py [--snapshot 사본 폴더] [--no-inject]

계산은 src/postlife/site 의 함수를 그대로 부르고 다시 만들지 않는다.
- 구성 예시: combo.variant_model, combo.evaluate, combo.payouts. 목적에 드는 특약은 sales.purposes(표준담보)로 가른다.
  우체국 판매 중 기준 종형(insights.base_variants)마다, 목적 셋마다, 나이 구간(Data.conds)과 성별마다 목적에 드는 특약을
  모두 고른 조합(가입금액은 고를 수 있는 최대)을 evaluate 에 넣고, 켜진 특약의 급부를 payouts 로 묶는다.
  이웃 나이 구간의 결과가 같으면 합친다. 한도 표(sales.limit_steps)의 구간도 함께 싣는다.
- 관문 나무: sales.gate(종형별 질문, 나이, 상태, 한도), sales.simple_classify(지도 라벨), sales.closed_reasons,
  sales.general_note 를 나이 구간 x 성별 x 이력(없음, 0.25~5년) x 수술만 마다 부른다. 이웃 나이 구간의 결과가 같으면 합친다.
  종형마다 고지 질문 값(eligibility.gate)과 가입나이(sales.age_span), 갱신과 환급 구조를 함께 싣는다.

--no-inject 가 없으면 두 JSON 을 tab3.js 의 자료 줄(/*__T3DATA_BEGIN__*/ ... /*__T3DATA_END__*/) 에도 넣는다.
build.py 는 tabN.js 만 합치므로 탭 3 의 자료는 tab3.js 안에 실어야 한다. 한글은 \\u 로 적어(ensure_ascii) build 의 글 검사
(가운뎃점, "됨" 따위)가 자료의 글자에 걸리지 않게 한다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))

from postlife.site import combo, eligibility, insights as I, sales as SA  # noqa: E402
from postlife.site.model import MAX_AGE, load  # noqa: E402

HERE = Path(__file__).resolve().parent
SINCE = [None, 0.25, 1, 2, 3, 4, 5]
STATES = list(SA.STATE_ORDER)                    # 열림, 나이 자료 없음, 질문 자료 없음, 심사로 확인, 닫힘
QUESTIONS = [SA.Q_NONE, SA.Q_HIT, SA.Q_REVIEW, SA.Q_NODATA]
AGES = [SA.AGE_OK, SA.AGE_NO, SA.AGE_NODATA]
MARK_A, MARK_B = '/*__T3DATA_BEGIN__*/', '/*__T3DATA_END__*/'


def r2(x):
    return None if x is None else round(float(x), 2)


def rider_purposes(data, tid) -> set[str]:
    """특약의 급부 가운데 확정 표준담보가 있는 것의 목적 묶음(sales.purposes)."""
    out: set[str] = set()
    for bid in data.benefits_of.get(tid, []):
        std = data.benefit_view(bid)['std']
        if std:
            out.update(SA.purposes(data.std.get(std)))
    return out


def combo_one(data, vm, k, purpose, members, benefits):
    """목적 하나, 조건 하나의 구성 예시. 결과는 화면이 그대로 읽는 꼴."""
    by_id = {r['tid']: r for r in vm['riders']}
    main = vm['main']
    want = {tid: None for tid in members}
    rows = combo.evaluate(vm, k, want)['rows']
    pay = combo.payouts(vm, benefits, rows)
    names = {tid: data.riders[tid]['원시특약명'] for tid in by_id}
    out_r = []
    for row in rows:
        tid = row['tid']
        if tid != main and tid not in members and not row['forced']:
            continue
        r = by_id[tid]
        lim = r['lim'][k]
        cut = None
        if row['on'] and lim is not None and row['hi'] is not None and row['hi'] < lim:
            for rule in vm['rules']:
                if rule['target'] == tid and rule['type'] == '최대연동':
                    cut = {'기준': rule['base'], '기준이름': names.get(rule['base']), '글': rule.get('text'),
                           '수치': rule.get('num'), '단위': rule.get('unit')}
                    break
        reasons = []
        for x in row['reasons']:
            y = {'code': x['code']}
            if 'base' in x:
                y['기준'] = x['base']
                y['기준이름'] = names.get(x['base'])
                rule = next((u for u in vm['rules'] if u['target'] == tid and u['base'] == x['base']), None)
                if rule:
                    y['글'] = rule.get('text')
            if 'num' in x:
                y['수치'] = x['num']
            if 'hi' in x:
                y['상한'] = r2(x['hi'])
            reasons.append(y)
        out_r.append({'특약': tid, '이름': names[tid], '주계약': tid == main, '목적안': tid in members,
                      '켬': row['on'], '금액': r2(row['amount']), '최소': r2(row['lo']), '나이한도': r2(lim),
                      '상한': r2(row['hi']), '특약최대': r2(r.get('max')), '한도대기': bool(r['limPend'][k]),
                      '한도자료없음': bool(r['noCond']), '줄어듦': cut, '까닭': reasons, '의무부가': bool(row['forced'])})
    groups = []
    for g in pay['groups']:
        std = data.std.get(g['std'], {})
        line = g['lines'][g['rep']] if g['rep'] is not None else None
        b = benefits[line['bid']] if line else {}
        groups.append({'표준담보': g['std'], '이름': std.get('표준담보명'), '대분류': std.get('보장대분류'),
                       '중분류': std.get('보장중분류'), '유형': std.get('급부유형'),
                       '목적안': purpose in SA.purposes(std), '줄수': len(g['lines']),
                       '대표': None if not line else {'급부': line['bid'], '급부이름': b.get('name'), '특약': b.get('tid'),
                                                    '지급액': r2(line['val']), '감액': [[m, r2(v)] for m, v in line['reduced']],
                                                    '면책일': b.get('wait'), '비율': bool(b.get('ratio')),
                                                    '문서': b.get('doc'), '쪽': b.get('page')}})
    order = I.std_order(data)
    groups.sort(key=lambda x: (not x['목적안'], order.get(x['표준담보'], 9999), str(x['이름'])))
    return {'특약': out_r, '담보': groups, '묶지않은급부': len(pay['others'])}


def merge(items):
    """[{lo, hi, v}] 의 이웃 구간이 v 가 같으면 합친다."""
    out = []
    for it in items:
        if out and out[-1]['hi'] == it['lo'] - 1 and out[-1]['v'] == it['v']:
            out[-1]['hi'] = it['hi']
        else:
            out.append(dict(it))
    return out


def build_combo(data):
    conds = data.conds()
    bases = I.base_variants(data)[1]
    benefits = {bid: data.benefit_view(bid) for bid in data.benefits}
    limits = {x['종형ID']: x for x in SA.limit_steps(data)}
    out = {'형식': 1, '자료시각': data.meta.get('snapshot_at'), '목적': [p['이름'] for p in SA.PURPOSE_BASIS],
           '목적기준': SA.PURPOSE_BASIS, '종형': {}}
    for vid in bases:
        vm = combo.variant_model(data, vid, conds)
        members = {p: [r['tid'] for r in vm['riders'] if r['tid'] != vm['main'] and p in rider_purposes(data, r['tid'])]
                   for p in SA.PURPOSES}
        per = {}
        for p in SA.PURPOSES:
            per[p] = {}
            for sex in ('M', 'F'):
                items = []
                for k, c in enumerate(conds):
                    if c.age is None or c.sex != sex:
                        continue
                    main_ok = vm['main'] and next(r for r in vm['riders'] if r['tid'] == vm['main'])['ok'][k]
                    if not main_ok:
                        continue
                    items.append({'lo': c.lo, 'hi': min(c.hi, MAX_AGE), 'v': combo_one(data, vm, k, p, members[p], benefits)})
                per[p][sex] = merge(items)
        out['종형'][vid] = {'이름': SA._kind_name(data, vid), '주계약': vm['main'],
                           '주계약이름': data.riders[vm['main']]['원시특약명'] if vm['main'] else None,
                           '특약수': len(vm['riders']), '제약수': len(vm['rules']), '읽지못한제약': len(vm['skipped']),
                           '목적특약수': {p: len(members[p]) for p in SA.PURPOSES},
                           '한도표': limits.get(vid, {}).get('구간'), '구성': per,
                           '제약': [{'유형': r['type'], '기준': r['base'], '기준이름': data.riders[r['base']]['원시특약명'],
                                    '대상': r['target'], '대상이름': data.riders[r['target']]['원시특약명'],
                                    '수치': r.get('num'), '단위': r.get('unit'), '글': r.get('text')} for r in vm['rules']]}
    return out


def build_gate(data):
    conds = [c for c in data.conds() if c.age is not None]
    vids = SA.gate_targets(data)          # 관문전용 종형(고지 질문과 주계약 가입조건만 모은 종형)도 관문 나무에 싣는다
    info = {}
    for vid in vids:
        v = data.variants[vid]
        info[vid] = {'회사': v.get('기관코드'), '이름': SA._kind_name(data, vid), '심사': v.get('심사유형'),
                     '간편고지약칭': v.get('간편고지약칭'), '갱신': v.get('갱신유형'), '갱신주기': v.get('갱신주기년'),
                     '환급': v.get('환급유형'), '질문': eligibility.gate(v),
                     '가입나이': {s: SA.age_span(data, vid, s) for s in ('M', 'F')},
                     '한도빈칸': data.limit_gap(vid), '관문전용': SA.gate_only(data, vid)}
    table = {}
    for sex in ('M', 'F'):
        for since in SINCE:
            for surg in ((False,) if since is None else (False, True)):
                items = []
                for c in conds:
                    if c.sex != sex:
                        continue
                    p = SA.Profile(age=c.lo, sex=sex, since=since, surgery_only=surg)
                    g = SA.gate(data, p)
                    shown, nodata = SA.simple_classify(data, g)
                    home = g['회사'].get('EPOST')
                    vs = {x['종형ID']: x for comp in g['회사'].values() for x in comp['종형']}
                    s = [[STATES.index(vs[v]['상태']), QUESTIONS.index(vs[v]['질문']), AGES.index(vs[v]['나이']),
                          vs[v]['한도만원']] for v in vids]
                    items.append({'lo': c.lo, 'hi': min(c.hi, MAX_AGE),
                                  'v': {'s': s, '라벨': SA.LABELS[shown], '간편자료없음': nodata,
                                        '회사': {o: x['상태'] for o, x in g['회사'].items()},
                                        '닫힌사유': SA.closed_reasons(data, home, None), '보조': SA.general_note(data, home)}})
                key = f"{sex}|{'-' if since is None else since}|{int(surg)}"
                table[key] = merge(items)
    return {'형식': 1, '자료시각': data.meta.get('snapshot_at'), '종형': vids, '상태': STATES, '질문값': QUESTIONS,
            '나이값': AGES, '종형정보': info, '조건': table,
            '규칙': {'일반심사': '이력과 무관하게 심사로 확인'}}


def compact_combo(c):
    """combo.json 을 tab3.js 에 싣는 짧은 꼴로 바꾼다(값은 그대로, 되풀이되는 이름과 ID 를 번호로)."""
    std = {}
    out = {'P': c['목적'], 'PB': c['목적기준'], 'S': std, 'V': {}}
    for vid, v in c['종형'].items():
        riders, rix = [], {}
        bens, bix = [], {}
        rules, uix = [], {}
        pool, pix = [], {}

        def ri(tid, name=None, lo=None, top=None):
            if tid not in rix:
                rix[tid] = len(riders)
                riders.append([tid, name, lo, top])
            else:
                row = riders[rix[tid]]
                for i, val in ((1, name), (2, lo), (3, top)):
                    if val is not None and row[i] is None:
                        row[i] = val
            return rix[tid]

        def ui(rule):
            if not rule:
                return None
            key = (rule.get('기준'), rule.get('글'), rule.get('수치'), rule.get('단위'))
            if key not in uix:
                uix[key] = len(rules)
                rules.append([ri(rule.get('기준')), rule.get('글'), rule.get('수치'), rule.get('단위')])
            return uix[key]

        for p, per in v['구성'].items():
            for sex, items in per.items():
                for it in items:
                    r = it['v']
                    rows = []
                    for x in r['특약']:
                        why = [[y['code'], ri(y['기준']) if '기준' in y else None,
                                ui({'기준': y.get('기준'), '글': y.get('글')}) if y.get('글') else None,
                                y.get('수치'), y.get('상한')] for y in x['까닭']]
                        rows.append([ri(x['특약'], x['이름'], x['최소'], x['특약최대']), int(x['목적안']), int(x['켬']),
                                     x['금액'], x['나이한도'], x['상한'], int(x['한도대기']), int(x['한도자료없음']),
                                     ui(x['줄어듦']), why, int(x['의무부가']), int(x['주계약'])])
                    gs = []
                    for g in r['담보']:
                        std.setdefault(g['표준담보'], [g['이름'], g['대분류'], g['중분류'], g['유형']])
                        b = g['대표']
                        bi = None
                        if b:
                            if b['급부'] not in bix:
                                bix[b['급부']] = len(bens)
                                bens.append([b['급부'], b['급부이름'], ri(b['특약']), b['면책일'], int(b['비율']), b['문서'], b['쪽']])
                            bi = bix[b['급부']]
                        gs.append([g['표준담보'], int(g['목적안']), g['줄수'], bi,
                                   b['지급액'] if b else None, b['감액'] if b else []])
                    res = {'r': rows, 'g': gs, 'o': r['묶지않은급부']}
                    key = json.dumps(res, sort_keys=True, ensure_ascii=False)
                    if key not in pix:
                        pix[key] = len(pool)
                        pool.append(res)
                    it['_x'] = pix[key]
        cons = [[x['유형'], ri(x['기준'], x['기준이름']), ri(x['대상'], x['대상이름']), x['수치'], x['단위'], x['글']] for x in v['제약']]
        out['V'][vid] = {'n': v['이름'], 'm': v['주계약'], 'mn': v['주계약이름'], 'k': [v['특약수'], v['제약수'], v['읽지못한제약']], 'K': cons,
                         'pk': v['목적특약수'], 'L': v['한도표'], 'R': riders, 'U': rules, 'B': bens, 'X': pool,
                         'C': {p: {s: [[it['lo'], it['hi'], it['_x']] for it in items] for s, items in per.items()}
                               for p, per in v['구성'].items()}}
    return out


def compact_gate(g):
    pool, pix = [], {}
    cond = {}
    for key, items in g['조건'].items():
        rows = []
        for it in items:
            k = json.dumps(it['v'], sort_keys=True, ensure_ascii=False)
            if k not in pix:
                pix[k] = len(pool)
                pool.append(it['v'])
            rows.append([it['lo'], it['hi'], pix[k]])
        cond[key] = rows
    return {'V': g['종형'], 'I': g['종형정보'], 'ST': g['상태'], 'Q': g['질문값'], 'A': g['나이값'], 'X': pool, 'C': cond,
            'rule': g['규칙']}


# build 의 글 검사(check_authored)에 걸리는 글자만 \u 로 적는다. 한글은 그대로 둔다(크기를 줄이려고)
_ESC = {'\u00b7': '\\u00b7', '\ub428': '\\ub428', '\u2014': '\\u2014', '\u2015': '\\u2015'}


def js_safe(text: str) -> str:
    for a, b in _ESC.items():
        text = text.replace(a, b)
    text = text.replace('\ud310\uc62c\ub9bc', '\\ud310\\uc62c\\ub9bc').replace('\uc900\ube44 \uc911', '\\uc900\\ube44 \\uc911')
    text = re.sub(r'https?://', lambda m: m.group(0).replace('/', '\\/'), text)
    return text.replace('</', '<\\/')


def inject(combo_obj, gate_obj):
    p = HERE / 'tab3.js'
    text = p.read_text(encoding='utf-8')
    a, b = text.find(MARK_A), text.find(MARK_B)
    if a < 0 or b < a:
        print(f'tab3.js 에 {MARK_A} ... {MARK_B} 자리가 없다. 넣지 않았다.')
        return False
    blob = js_safe(json.dumps({'구성': compact_combo(combo_obj), '관문': compact_gate(gate_obj)},
                              ensure_ascii=False, separators=(',', ':')))
    new = text[:a + len(MARK_A)] + blob + text[b:]
    p.write_text(new, encoding='utf-8')
    print(f'tab3.js 자료 줄에 넣었다({len(blob.encode("utf-8")):,}바이트)')
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', type=Path, default=ROOT / 'data' / 'snapshot')
    ap.add_argument('--no-inject', action='store_true')
    args = ap.parse_args()
    data = load(args.snapshot)
    c = build_combo(data)
    g = build_gate(data)
    for name, obj in (('combo.json', c), ('gate.json', g)):
        t = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
        (HERE / name).write_text(t, encoding='utf-8')
        print(f'{HERE / name}: {len(t.encode("utf-8")):,}바이트')
    if not args.no_inject:
        inject(c, g)
    return 0


if __name__ == '__main__':
    sys.exit(main())
