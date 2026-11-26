"""시안 4(영업 분석 콘솔, proto_src/console4)가 읽는 화면 자료를 사본에서 한 번에 만든다.

파일과 그것을 읽는 곳(build.py 가 한 파일로 합친다)
- sales.json: 영업 인사이트(sales.export). build.py 가 script#sales-data 로 싣고 화면은 App.S 로 읽는다.
- combo.json, gate.json: 가입 관문 탭의 구성 예시와 관문 나무. 화면은 이 둘을 줄인 꼴(compact_combo, compact_gate)을
  tab3.js 의 자료 줄(/*__T3DATA_BEGIN__*/ ... /*__T3DATA_END__*/)로 읽는다. 두 JSON 은 화면에 직접 실리지 않는다.
- cover.json: 담보 비교 탭과 관계 그림의 비교 자료. tab4.js = "const CV = " + cover.json + ";\\n" + tab4.src.js.
- d.json: `const D`(lineup.export). build.py 가 tpl.html 의 /*__D__*/ 자리에 "const D = <d.json>;" 으로 넣는다.

계산은 이 모듈 밖의 함수(sales, combo, insights, eligibility, lineup)를 그대로 부르고, 숫자와 판정을 새로 만들지 않는다.
자료의 열쇠와 꼴은 화면 코드(core.js, tab1~5.js)가 그대로 읽는 것이라 바꾸지 않는다(tests/test_console4_data.py 가 지킨다).

만드는 명령: python scripts/export_app_data.py [--snapshot data/snapshot] [--out proto_src/console4]
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import combo, eligibility, lineup
from . import insights as I
from . import sales as SA
from . import terms
from .model import FORM_TEXT, MAX_AGE, Data
from .relations import Relations, load_relations

SINCE = [None, 0.25, 1, 2, 3, 4, 5]
STATES = list(SA.STATE_ORDER)                    # 열림, 나이 자료 없음, 질문 자료 없음, 심사로 확인, 닫힘
QUESTIONS = [SA.Q_NONE, SA.Q_HIT, SA.Q_REVIEW, SA.Q_NODATA]
AGES = [SA.AGE_OK, SA.AGE_NO, SA.AGE_NODATA]
MARK_A, MARK_B = '/*__T3DATA_BEGIN__*/', '/*__T3DATA_END__*/'
LINE_HEAD = 'const CV = '                       # tab4.js 첫 줄의 머리
FILES = ['sales.json', 'combo.json', 'gate.json', 'cover.json', 'd.json', 'tab3.js', 'tab4.js']


def dumps(obj: Any) -> str:
    """자료 파일의 글 꼴: 한글 그대로, 빈칸 없이."""
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


# ---------- 가입 관문 탭(tab3): 구성 예시와 관문 나무 ----------
def r2(x):
    return None if x is None else round(float(x), 2)


def rider_purposes(data: Data, tid: str) -> set[str]:
    """특약의 급부 가운데 확정 표준담보가 있는 것의 목적 묶음(sales.purposes)."""
    out: set[str] = set()
    for bid in data.benefits_of.get(tid, []):
        std = data.benefit_view(bid)['std']
        if std:
            out.update(SA.purposes(data.std.get(std)))
    return out


def combo_one(data: Data, vm, k, purpose, members, benefits):
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


def build_combo(data: Data) -> dict:
    """구성 예시(combo.json). 우체국 판매 중 기준 종형(insights.base_variants)마다, 목적 셋마다, 나이 구간(Data.conds)과
    성별마다 목적에 드는 특약을 모두 고른 조합(가입금액은 고를 수 있는 최대)을 combo.evaluate 에 넣고, 켜진 특약의 급부를
    combo.payouts 로 묶는다. 이웃 나이 구간의 결과가 같으면 합친다. 한도 표(sales.limit_steps)의 구간도 함께 싣는다."""
    conds = data.conds()
    bases = I.order_bases(data, I.base_variants(data)[1])
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


def build_gate(data: Data) -> dict:
    """관문 나무(gate.json). sales.gate, sales.simple_classify(지도 라벨), sales.closed_reasons, sales.general_note 를
    나이 구간 x 성별 x 이력(없음, 0.25~5년) x 수술만 마다 부른다. 이웃 나이 구간의 결과가 같으면 합친다.
    종형마다 고지 질문 값(eligibility.gate)과 가입나이(sales.age_span), 갱신과 환급 구조, 고지 유형 열쇠(sales.notice_key)를
    함께 싣는다. 고지중대질병목록(중대질병 질문의 질병 이름을 ", "로 이은 것)과 고지소견범위(서면, 서면과 진료기록부)는 종형 표의
    값을 그대로 싣고, 값이 없으면(일반심사 종형 따위) null 이다."""
    conds = [c for c in data.conds() if c.age is not None]
    vids = SA.gate_targets(data)          # 관문전용 종형(고지 질문과 주계약 가입조건만 모은 종형)도 관문 나무에 싣는다
    info = {}
    for vid in vids:
        v = data.variants[vid]
        info[vid] = {'회사': v.get('기관코드'), '이름': SA._kind_name(data, vid), '심사': v.get('심사유형'),
                     '간편고지약칭': v.get('간편고지약칭'), '갱신': v.get('갱신유형'), '갱신주기': v.get('갱신주기년'),
                     '환급': v.get('환급유형'), '질문': eligibility.gate(v),
                     '가입나이': {s: SA.age_span(data, vid, s) for s in ('M', 'F')},
                     '한도빈칸': data.limit_gap(vid), '관문전용': SA.gate_only(data, vid),
                     '고지유형열쇠': SA.notice_key(data, vid),
                     '고지중대질병목록': v.get('고지중대질병목록') or None, '고지소견범위': v.get('고지소견범위') or None}
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
            '규칙': {'일반심사': '이력과 관계없이 인수심사로 결정'}}


def compact_combo(c: dict) -> dict:
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

        index: dict[int, int] = {}            # id(구간 항목) -> 결과 번호. 받은 c 를 고치지 않는다
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
                    index[id(it)] = pix[key]
        cons = [[x['유형'], ri(x['기준'], x['기준이름']), ri(x['대상'], x['대상이름']), x['수치'], x['단위'], x['글']] for x in v['제약']]
        out['V'][vid] = {'n': v['이름'], 'm': v['주계약'], 'mn': v['주계약이름'], 'k': [v['특약수'], v['제약수'], v['읽지못한제약']], 'K': cons,
                         'pk': v['목적특약수'], 'L': v['한도표'], 'R': riders, 'U': rules, 'B': bens, 'X': pool,
                         'C': {p: {s: [[it['lo'], it['hi'], index[id(it)]] for it in items] for s, items in per.items()}
                               for p, per in v['구성'].items()}}
    return out


def compact_gate(g: dict) -> dict:
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


# build.py 의 글 검사(check_authored)에 걸리는 글자만 \u 로 적는다. 한글은 그대로 둔다(크기를 줄이려고)
_ESC = {'·': '\\u00b7', '됨': '\\ub428', '—': '\\u2014', '―': '\\u2015'}


def js_safe(text: str) -> str:
    for a, b in _ESC.items():
        text = text.replace(a, b)
    text = text.replace('판올림', '\\ud310\\uc62c\\ub9bc').replace('준비 중', '\\uc900\\ube44 \\uc911')
    text = re.sub(r'https?://', lambda m: m.group(0).replace('/', '\\/'), text)
    return text.replace('</', '<\\/')


def tab3_blob(combo_obj: dict, gate_obj: dict) -> str:
    """tab3.js 의 자료 줄 가운데 두 표식 사이에 들어가는 글."""
    return js_safe(dumps({'구성': compact_combo(combo_obj), '관문': compact_gate(gate_obj)}))


def tab3_data(tab3_text: str) -> str:
    """tab3.js 의 두 표식 사이 글. 표식이 없으면 멈춘다."""
    a, b = tab3_text.find(MARK_A), tab3_text.find(MARK_B)
    if a < 0 or b < a:
        raise ValueError(f'tab3.js 에 {MARK_A} ... {MARK_B} 자리가 없다')
    return tab3_text[a + len(MARK_A):b]


def inject_tab3(tab3_text: str, blob: str) -> str:
    """tab3.js 의 두 표식 사이를 blob 으로 바꾼 글. 표식 밖(손으로 쓴 코드)은 그대로 둔다."""
    a, b = tab3_text.find(MARK_A), tab3_text.find(MARK_B)
    if a < 0 or b < a:
        raise ValueError(f'tab3.js 에 {MARK_A} ... {MARK_B} 자리가 없다')
    return tab3_text[:a + len(MARK_A)] + blob + tab3_text[b:]


# ---------- 담보 비교 탭(tab4)과 관계 그림 ----------
# 담보와 상대 쌍마다의 판정(쌍판정)을 여기 한 군데에서 정하고, 담보별 판정 집계(판정기관코드, 판정상대수)와 표의 요약(판정요약)은
# 그 쌍판정을 모은다. 쌍판정의 까닭(판정기관코드의 열쇠와 같은 이름):
# - 둘 다 확정 급부가 있으면: 단정 주의(sales.json 의 단정주의에 그 상대가 들면. R10 대로 아래보다 먼저), 검토 대기(insights 의 뺀
#   비교쌍), 지급 형태 다름(비교쌍 판정이 같음인데 지급 형태가 다름. 다름은 우열에 넣지 않는다), 아니면 insights 의 비교쌍 판정
#   (나음, 같음, 못함, 엇갈림, 판정 보류. 기준 종형 쪽에서 적는다. 나음은 우체국 조건이 낫다)
# - 상대에게만 확정 급부가 있으면: 우리에게 그 담보의 매핑 대기 급부가 있으면 검토 대기(대기는 없음이 아니라 모름), 없으면 우체국에 없음
# - 우리에게만 확정 급부가 있으면: 상대에게 매핑 대기 급부가 있거나, 상대가 든 뺀 시사점(insights 의 뺀시사점. 고유와 범위 차이를
#   검토 대기로 뺀 것)이 있으면 검토 대기, 상대가 관계 담보(넓은 담보, 부분 담보)로 덮으면 관계 담보로 덮음(insights 의 범위 차이.
#   온톨로지 설계안 9절의 "우체국에만"은 담보관계로도 덮이지 않는 것이다), 아니면 상대에 없음
# - 둘 다 확정 급부가 없으면: 어느 쪽에 매핑 대기 급부가 있으면 검토 대기, 아니면 판정 없음(null, 둘 다 없음)
PAIR_KEYS = ['나음', '같음', '못함', '엇갈림', '판정 보류', '단정 주의', '지급 형태 다름', '관계 담보로 덮음', '검토 대기',
             '우체국에 없음', '상대에 없음']
CAUTION_KEY, PENDING_KEY, NONE_KEY = '단정 주의', '검토 대기', '우체국에 없음'
FORM_KEY, COVER_KEY, ONLY_KEY = '지급 형태 다름', '관계 담보로 덮음', '상대에 없음'
# 기둥에 쌓는 까닭(판정기관코드의 열쇠). 상대에 없음은 기둥 밖(그 상대는 이 담보를 갖지도 덮지도 않는다)
VERDICT_KEYS = [k for k in PAIR_KEYS if k != ONLY_KEY]
# 까닭마다의 판정 이름(화면의 칩 글)과 칩 종류(App.ui.verdict 의 kind). 까닭과 판정 이름은 화면 코드가 글자로 분기하고 세므로
# (tab4.src.js) 값은 그대로 둔다. 화면에 보일 이름은 terms.DISPLAY_GROUPS 의 "판정 집계", "판정 이름"이고, 판정표의 표시명에도 싣는다
VERDICT_NAME = {'나음': '우체국 나음', '같음': '같음', '못함': '우체국 못함', '엇갈림': '우열을 매기지 않음',
                '판정 보류': '판정 보류', '단정 주의': '우열을 매기지 않음', '지급 형태 다름': '우열을 매기지 않음',
                '관계 담보로 덮음': '우열을 매기지 않음', '검토 대기': '검토 대기', '우체국에 없음': '우체국에 없음',
                '상대에 없음': '우체국에만 있음'}
BOTH_NONE = '둘 다 없음'
NAME_ORDER = ['우체국 나음', '우체국 못함', '같음', '우열을 매기지 않음', '우체국에만 있음', '우체국에 없음', '검토 대기', '판정 보류',
              BOTH_NONE]
CHIP = {'우체국 나음': 'better', '같음': 'same', '우체국 못함': 'worse', '우열을 매기지 않음': 'diff', '판정 보류': 'unknown',
        '검토 대기': 'unknown', '우체국에 없음': 'none', '우체국에만 있음': 'only', BOTH_NONE: None}


def _has(cell) -> bool:
    """확정 급부가 있는 칸(tab4.src.js 의 has: 칸이 객체이고 i 가 비지 않음)."""
    return isinstance(cell, dict) and bool(cell.get('i'))


def _waiting(label: str, cell) -> list[str]:
    """매핑 검수 대기 급부가 있는 칸의 사유 글. insights 의 Holding.blockers 와 같은 꼴("{종형 이름} 매핑 검수 대기 N건")이다.
    label 은 종형 이름(insights.variant_label)이다."""
    return [f'{label} {I.PENDING_MAPPING} {cell["w"]}건'] if isinstance(cell, dict) and cell.get('w') else []


def pair_verdict(sid: str, vids: list[str], cells: list, k: int, pair: dict, cautious: dict,
                 notes: list[dict], labels: dict[str, str] | None = None) -> list | None:
    """담보 sid 의 기준 종형(vids[0])과 상대 vids[k] 쌍의 판정: [까닭, 사유 목록] 또는 None(둘 다 없음). 규칙은 위 주석이다.
    사유 목록은 검토 대기와 판정 보류의 사유 글(insights 의 뺀 비교쌍 사유, 보류비교 사유, 뺀 시사점 사유, 매핑 검수 대기 급부 수)과
    단정 주의의 종류이고, 나머지 까닭은 빈 목록이다. 자료 쪽에 이미 있는 값만 쓴다(판정을 새로 만들지 않는다).
    labels 는 종형ID → 사유 글에 적을 종형 이름이다(없으면 종형ID 를 적는다)."""
    name = (labels or {}).get
    base, cell, peer = cells[0], cells[k], vids[k]
    if _has(cell):
        if not _has(base):
            waits = _waiting(name(vids[0], vids[0]), base)
            return [PENDING_KEY, waits] if waits else [NONE_KEY, []]
        q = pair.get((sid, peer))
        if q is None:
            raise ValueError(f'두 쪽 모두 확정 급부가 있는데 비교쌍이 없다: {sid}, {peer}')
        if (sid, peer) in cautious:
            return [CAUTION_KEY, [cautious[(sid, peer)]]]
        if q.get('x'):
            return [PENDING_KEY, list(q['x'])]
        if q.get('f') == I.DIFF and q['v'] == I.SAME:
            return [FORM_KEY, []]
        if q['v'] not in PAIR_KEYS:
            raise ValueError(f'모르는 판정: {q["v"]} ({sid}, {peer})')
        return [q['v'], list(q.get('hs') or []) if q['v'] == I.HOLD else []]
    if _has(base):
        waits = _waiting(name(peer, peer), cell)
        if waits:
            return [PENDING_KEY, waits]
        drops = list(dict.fromkeys(r for x in notes if x.get('drop') and peer in (x.get('p') or []) for r in x['drop']))
        if drops:
            return [PENDING_KEY, drops]
        if isinstance(cell, dict) and cell.get('c'):
            return [COVER_KEY, []]
        return [ONLY_KEY, []]
    waits = _waiting(name(vids[0], vids[0]), base) + _waiting(name(peer, peer), cell)
    return [PENDING_KEY, waits] if waits else None


def verdict_codes(data: Data, verdicts: list, peers: list[str]) -> dict[str, list[str]]:
    """표준담보 하나의 쌍판정(상대 차례)을 까닭별 상대 기관코드로 모은 것(판정기관코드의 한 줄). 상대에 없음과 둘 다 없음은 넣지
    않는다(기둥 밖). 값이 빈 까닭은 싣지 않는다. 목록을 모두 합하면 그 담보의 보유기관코드에, 우리에게 확정 급부가 있을 때 관계
    담보로 덮는 상대와 검토 대기인 상대(매핑 대기만 있거나 뺀 시사점에 든 상대), 둘 다 확정 급부가 없을 때 매핑 대기 급부가 있는
    상대를 더한 것이다."""
    out: dict[str, list[str]] = {}
    for p, v in zip(peers, verdicts):
        if v is None or v[0] == ONLY_KEY:
            continue
        out.setdefault(v[0], []).append(data.variants[p].get('기관코드'))
    return {k: sorted(out[k]) for k in VERDICT_KEYS if k in out}


def verdict_summary(data: Data, rows_verdicts: dict[str, list], peers: list[str]) -> dict[str, dict[str, int]]:
    """판정요약: 상대 회사마다 판정 이름별 쌍 수(담보 비교표 요약). 둘 다 없음도 센다. 회사마다 모두 더하면 담보 줄 수다."""
    out: dict[str, dict[str, int]] = {}
    for i, p in enumerate(peers):
        org = data.variants[p].get('기관코드')
        per = out.setdefault(org, {})
        for verdicts in rows_verdicts.values():
            v = verdicts[i]
            name = BOTH_NONE if v is None else VERDICT_NAME[v[0]]
            per[name] = per.get(name, 0) + 1
    return {o: {n: out[o][n] for n in NAME_ORDER if n in out[o]} for o in sorted(out)}


def num(x):
    if x is None:
        return None
    f = float(x)
    return int(f) if f.is_integer() else round(f, 4)


def build_cover(data: Data, sales_obj: dict, rel: Relations, analysis: dict | None = None) -> dict:
    """담보 비교 자료(cover.json). 기준 종형과 짝은 sales_obj(sales.json)를 따르고, 판정은 sales.py 가 쓰는 계산
    (insights.analyze 의 비교쌍, 시사점, 뺀 시사점)을 그대로 읽어 담는다(R10). 숫자와 판정을 새로 만들지 않는다.
    자료 시각이 sales_obj 와 다르면 멈춘다."""
    S = sales_obj
    A = I.analyze(data, rel) if analysis is None else analysis
    if A['자료시각'] != S['자료시각']:
        raise ValueError(f'자료 시각이 다르다: 사본 {A["자료시각"]}, sales.json {S["자료시각"]}. sales.json 을 다시 만든 뒤 돌린다')
    order = I.std_order(data)
    res_by = {r['종형ID']: r for r in A['기준']}
    hold: dict[str, I.Holding] = {}

    ben: dict[str, list] = {}
    rid: dict[str, list] = {}
    bix: dict[str, int] = {}
    rix: dict[str, int] = {}
    forms: dict[str, str] = {}           # 금액 하나로 담기지 않는 급부의 순번(글) → 지급기준구분

    def add_ben(bid: str) -> int:
        if bid in bix:
            return bix[bid]
        v = data.benefit_view(bid)
        tags = I.pay_tags(v['limit'])
        ben[bid] = [v['name'], v['tid'], v['role'], num(v['pay']), num(v['base']), 1 if v['ratio'] else 0,
                    num(v['wait'] or 0), [[num(m), num(r)] for m, r in (v['red'] or [])], v['limit'] or None,
                    v['exc'] or None, v['doc'], num(v['page']), v['state'],
                    None if v['prob'] is None else round(float(v['prob']), 4),
                    1 if bid in data.pending_benefit else 0, I.tag_text(tags) if tags else None]
        t = v['tid']
        if t not in rix:
            r = data.riders[t]
            rix[t] = len(rid)
            rid[t] = [r['원시특약명'], r['담보구분'], num(r.get('최대가입금액만원'))]
        ben[bid][1] = rix[t]
        bix[bid] = len(bix)
        if v.get('form'):
            forms[str(bix[bid])] = v['form']
        return bix[bid]

    bases = {}
    for b in S['기준종형']:
        bid0 = b['종형ID']
        peers = S['기준별'][bid0]['맞붙는종형']
        r = res_by.get(bid0)
        if r is None or [p['종형ID'] for p in r['맞붙는종형']] != peers:
            r = I.analyze_pair(data, bid0, peers, rel, hold)
        vids = [bid0] + peers
        labels = {v: I.variant_label(data, v) for v in vids}       # 매핑 검수 대기 사유 글의 종형 이름
        for v in vids:
            if v not in hold:
                hold[v] = I.Holding(data, v)
        H = {v: hold[v] for v in vids}
        sids = sorted({s for v in vids for s in H[v].possible if s in data.std}, key=lambda s: (order.get(s, 9999), s))
        scope = I.coverage_scope(data, bid0, H[bid0])
        if scope is not None:
            sids = [s for s in sids if data.std[s]['보장대분류'] in scope]

        # 비교쌍(같은 담보를 둘 다 가진 짝): 판정, 보류밖판정, 지급 형태, 뺀 사유, 항목
        pair = {}
        for p in r['비교쌍목록']:
            pair[(p['표준담보ID'], p['비교종형ID'])] = {'v': p['판정'], 'h': p['보류밖판정'], 'f': p['지급형태'], 'x': 0}
        for p in r['뺀비교']:
            pair[(p['표준담보ID'], p['비교종형ID'])]['x'] = p['사유']
        for p in r['보류비교']:
            pair[(p['표준담보ID'], p['비교종형ID'])]['hs'] = p['사유']
        # 시사점과 뺀 시사점(담보마다)
        ins: dict[str, list] = {}
        for x in r['시사점']:
            ins.setdefault(x['표준담보ID'], []).append({'k': x['유형'], 'd': x['방향'], 'p': x['비교종형ID'],
                                                       'o': {k: v for k, v in (x.get('대표밖조건다른줄') or {}).items()}})
        for x in r['뺀시사점']:
            ins.setdefault(x['표준담보ID'], []).append({'k': x['유형'], 'd': x['방향'], 'p': x['비교종형ID'], 'drop': x['사유']})

        rows = []
        owners: dict[str, list[str]] = {}
        verdicts: dict[str, dict[str, list[str]]] = {}
        by_pair: dict[str, list] = {}       # 쌍판정: {표준담보ID: [상대 차례의 [까닭, 사유] 또는 None]}
        cautious = {}                    # 단정 주의(sales.json)에 든 (표준담보ID, 상대 종형ID)
        for c in S['기준별'][bid0]['단정주의']:
            for p in c['상대종형ID']:
                cautious[(c['표준담보ID'], p)] = c['종류']
        for sid in sids:
            cells = []
            for v in vids:
                h = H[v]
                conf = h.confirmed.get(sid, [])
                waiting = h.waiting.get(sid, [])
                if not conf and not waiting:
                    cov = rel.cover(sid, h.has)
                    cells.append(0 if cov.kind == I.COVER_NONE else {'c': [cov.kind, list(cov.via), bool(cov.partial)]})
                    continue
                rep = h.rep(sid)
                # 대표 급부와, 대표와 조건(면책, 감액, 지급 형태)이 다른 줄 두 개까지만 싣는다. 나머지는 수(n)만 적는다
                keep = [rep] if rep else []
                if rep:
                    sig = I.condition_signature(rep)
                    keep += [x for x in conf if x['id'] != rep['id'] and I.condition_signature(x) != sig][:2]
                else:
                    keep = conf[:2]
                cell = {'r': add_ben(rep['id']) if rep else None, 'i': [add_ben(x['id']) for x in keep], 'n': len(conf)}
                if rep:
                    cell['o'] = h.other_lines(sid, rep)
                if waiting:
                    cell['w'] = len(waiting)
                logs = [x['id'] for x in conf if x['id'] in data.pending_benefit]
                if logs:
                    cell['l'] = len(logs)
                if not conf:
                    cov = rel.cover(sid, h.has)
                    if cov.kind != I.COVER_NONE:
                        cell['c'] = [cov.kind, list(cov.via), bool(cov.partial)]
                cells.append(cell)
            prs = {}
            for p in peers:
                q = pair.get((sid, p))
                if q is None:
                    continue
                rb, ro = H[bid0].rep(sid), H[p].rep(sid)
                if rb is not None and ro is not None:
                    q['it'] = [[i['항목'], i['기준'], i['상대'], i['판정'], i['사유']] for i in I.compare_conditions(rb, ro)['항목']]
                prs[p] = q
            # 이 담보를 가진 상대 회사: 확정 급부가 있는 칸(화면의 has, 칸의 i 가 비지 않음)의 회사. 우리 기관은 뺀다
            owners[sid] = sorted({data.variants[v].get('기관코드') for v, c in zip(vids[1:], cells[1:])
                                  if isinstance(c, dict) and c.get('i')} - {SA.HOME_ORG, None})
            by_pair[sid] = [pair_verdict(sid, vids, cells, k, pair, cautious, ins.get(sid, []), labels)
                            for k in range(1, len(vids))]
            verdicts[sid] = verdict_codes(data, by_pair[sid], peers)
            row = [sid, cells, prs]
            if sid in ins:
                row.append(ins[sid])
            rows.append(row)
        bases[bid0] = {'cols': vids, 'rows': rows, 'pairs': r['비교쌍'], 'dropped': r['뺀비교쌍'], '보유기관코드': owners,
                       '판정기관코드': verdicts,
                       '판정상대수': {sid: {k: len(v) for k, v in per.items()} for sid, per in verdicts.items()},
                       '쌍판정': by_pair, '판정요약': verdict_summary(data, by_pair, peers)}

    # 급부와 특약은 번호로 가리킨다(줄마다 긴 ID를 되풀이하지 않게)
    # 판정표의 판정(이름)은 화면 코드가 글자로 분기해 그대로 두고, 화면에 보일 이름은 표시명에 따로 싣는다(용어 대조표 1-1)
    out = {'t': A['자료시각'], 'ben': list(ben.values()), 'rid': list(rid.values()), 'b': bases,
           '판정표': {k: {'판정': VERDICT_NAME[k], '칩': CHIP[VERDICT_NAME[k]], '표시명': terms.name(VERDICT_NAME[k])}
                    for k in PAIR_KEYS},
           '판정차례': list(NAME_ORDER)}
    if forms:
        # 금액 없는 급부(API.md "금액 없는 급부"). 그런 급부가 없으면 세 키를 싣지 않는다(지금 자료와 바이트까지 같다)
        out['지급기준'] = forms
        out['지급기준글'] = {k: FORM_TEXT[k] for k in FORM_TEXT if k in set(forms.values())}
        out['금액없음글'] = dict(NO_AMOUNT_TEXT)
    return out


# 금액 없는 급부를 그릴 때 금액, 기준 가입금액, 감액 자리에 보일 글과 지급액 판정의 사유(docs/proposals/급부표_지급기준_확장안.md 7절)
NO_AMOUNT_TEXT = {'기준': '금액 하나로 적을 수 없는 급부', '감액': I.CUT_IN_SOURCE, '지급액판정': I.AMOUNT_FORM}


def cover_text(cover: dict) -> str:
    """cover.json 의 글. tab4.js 의 build 검사(가운뎃점, 엠대시, "됨")에 걸리는 글자만 \\u 로 적는다(화면에는 같은 글자로 보인다).
    주소, "준비 중", "판올림", "</" 가 자료에 있으면 멈춘다."""
    text = dumps(cover)
    for ch in ['·', '—', '―', '됨', '∙']:
        text = text.replace(ch, '\\u%04x' % ord(ch))
    if re.search(r'https?://|준비 중|판올림|</', text):
        raise ValueError('자료에 build 검사에 걸리는 글이 있다(주소, "준비 중", "판올림", "</")')
    return text


def assemble_tab4(cover_json_text: str, tab4_src_text: str) -> str:
    """tab4.js = 자료 한 줄 + 손으로 쓰는 탭 4 코드(tab4.src.js)."""
    return LINE_HEAD + cover_json_text + ';\n' + tab4_src_text


# ---------- 한 번에 ----------
def export_texts(data: Data, src_dir: Path, rel: Relations | None = None) -> dict[str, str]:
    """사본 하나로 자료 파일 일곱(FILES)의 글을 만든다. tab3.js 와 tab4.src.js 의 손으로 쓴 코드는 src_dir 에서 읽는다.
    순서: sales.json 을 먼저 만들고, 담보 비교 자료는 그 기준 종형과 짝을 따른다."""
    rel = load_relations() if rel is None else rel
    sales_text = dumps(SA.export(data, relations=rel))
    sales_obj = json.loads(sales_text)
    combo_obj, gate_obj = build_combo(data), build_gate(data)
    cover = cover_text(build_cover(data, sales_obj, rel))
    tab3 = inject_tab3((src_dir / 'tab3.js').read_text(encoding='utf-8'), tab3_blob(combo_obj, gate_obj))
    tab4 = assemble_tab4(cover, (src_dir / 'tab4.src.js').read_text(encoding='utf-8'))
    return {'sales.json': sales_text, 'combo.json': dumps(combo_obj), 'gate.json': dumps(gate_obj),
            'cover.json': cover, 'd.json': dumps(lineup.export(data)), 'tab3.js': tab3, 'tab4.js': tab4}


def write_texts(texts: dict[str, str], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        (out_dir / name).write_text(texts[name], encoding='utf-8')
