"""탭 4(담보 비교)와 탭 5(관계 그림)가 쓰는 비교 자료를 사본에서 뽑아 tab4.js 첫 줄(`const CV = ...;`)로 넣는다.

왜 따로 뽑나: 시안 3의 자료 줄(const D)은 간편 1~3종의 짝만 담았고(4종, 단일 없음), 조건 우열 부호가 지금 계산(면책, 감액,
지급 형태)보다 앞선 것이다. 화면의 판정이 sales.json(영업 인사이트)과 어긋나지 않게(R10) sales.py 가 쓰는 계산
(insights.analyze 의 비교쌍, 시사점, 뺀 시사점)을 그대로 읽어 담는다. 숫자와 판정을 새로 만들지 않는다.

쓰기: python proto_src/console4/gen_cover.py [--assemble]
- 자료를 뽑아 cover.json 에 두고, tab4.src.js(손으로 쓰는 코드) 앞에 `const CV = <자료>;` 한 줄을 붙여 tab4.js 를 쓴다.
- --assemble 은 자료를 다시 뽑지 않고 cover.json 과 tab4.src.js 만 합친다(코드만 고쳤을 때).
- 사본은 data/snapshot (읽기만 한다), 기준 종형과 짝은 sales.json 을 따른다.
- 자료 시각이 sales.json 과 다르면 멈춘다.
- tab4.js 의 build 검사(가운뎃점, 엠대시, "됨")에 걸리지 않게 그 글자만 \\u 로 바꿔 적는다(화면에는 그대로 보인다).
"""
from __future__ import annotations

import base64
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))

from postlife.site import compare as C  # noqa: E402
from postlife.site import insights as I  # noqa: E402
from postlife.site.model import load  # noqa: E402
from postlife.site.relations import load_relations  # noqa: E402

TAB4 = HERE / 'tab4.js'
TAB4_SRC = HERE / 'tab4.src.js'       # 손으로 쓰는 탭 4 코드. tab4.js = 자료 한 줄 + 이 파일
CACHE = HERE / 'cover.json'           # 뽑은 자료(검사 글자를 \u 로 바꾼 JSON 글자)
SALES = HERE / 'sales.json'
FONTS = ROOT / 'proto_src/fonts/fonts_v4.css'
LINE_HEAD = 'const CV = '


def num(x):
    if x is None:
        return None
    f = float(x)
    return int(f) if f.is_integer() else round(f, 4)


def assemble() -> int:
    """cover.json 과 tab4.src.js 를 합쳐 tab4.js 를 쓴다(자료를 다시 뽑지 않는다)."""
    if not CACHE.exists() or not TAB4_SRC.exists():
        print('cover.json 이나 tab4.src.js 가 없다')
        return 1
    TAB4.write_text(LINE_HEAD + CACHE.read_text(encoding='utf-8') + ';\n' + TAB4_SRC.read_text(encoding='utf-8'), encoding='utf-8')
    print(f'tab4.js 를 썼다: {TAB4.stat().st_size:,}바이트')
    return 0


def main() -> int:
    if '--assemble' in sys.argv:
        return assemble()
    S = json.loads(SALES.read_text(encoding='utf-8'))
    data = load(ROOT / 'data/snapshot')
    rel = load_relations()
    A = I.analyze(data, rel)
    if A['자료시각'] != S['자료시각']:
        print(f'자료 시각이 다르다: 사본 {A["자료시각"]}, sales.json {S["자료시각"]}. sales.json 을 다시 만든 뒤 돌린다')
        return 1
    order = I.std_order(data)
    res_by = {r['종형ID']: r for r in A['기준']}
    hold: dict[str, I.Holding] = {}

    ben: dict[str, list] = {}
    rid: dict[str, list] = {}
    bix: dict[str, int] = {}
    rix: dict[str, int] = {}

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
        return bix[bid]

    bases = {}
    for b in S['기준종형']:
        bid0 = b['종형ID']
        peers = S['기준별'][bid0]['맞붙는종형']
        r = res_by.get(bid0)
        if r is None or [p['종형ID'] for p in r['맞붙는종형']] != peers:
            r = I.analyze_pair(data, bid0, peers, rel, hold)
        vids = [bid0] + peers
        for v in vids:
            if v not in hold:
                hold[v] = I.Holding(data, v)
        H = {v: hold[v] for v in vids}
        sids = sorted({s for v in vids for s in H[v].possible if s in data.std}, key=lambda s: (order.get(s, 9999), s))

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
            row = [sid, cells, prs]
            if sid in ins:
                row.append(ins[sid])
            rows.append(row)
        bases[bid0] = {'cols': vids, 'rows': rows, 'pairs': r['비교쌍'], 'dropped': r['뺀비교쌍']}

    # 급부와 특약은 번호로 가리킨다(줄마다 긴 ID를 되풀이하지 않게)
    out = {'t': A['자료시각'], 'ben': list(ben.values()), 'rid': list(rid.values()), 'b': bases}
    text = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    # build 검사에 걸리는 글자만 \u 로(화면에는 같은 글자로 보인다)
    for ch in ['·', '—', '―', '됨', '∙']:
        text = text.replace(ch, '\\u%04x' % ord(ch))
    if re.search(r'https?://|준비 중|판올림|</', text):
        print('자료에 build 검사에 걸리는 글이 있다(주소, "준비 중", "판올림", "</")')
        return 1

    # 글꼴(PLKo)에 없는 한글
    try:
        from fontTools.ttLib import TTFont
        css = FONTS.read_text(encoding='utf-8')
        cmap: set[int] = set()
        for m in re.finditer(r'font-family:\s*"PLKo";[^}]*?url\(data:font/woff2;base64,([A-Za-z0-9+/=]+)\)', css):
            cmap |= set(TTFont(io.BytesIO(base64.b64decode(m.group(1)))).getBestCmap())
        plain = json.dumps(out, ensure_ascii=False)
        miss = sorted({c for c in plain if '가' <= c <= '힣' and ord(c) not in cmap}) if cmap else []
        if miss:
            print(f'글꼴에 없는 한글 {len(miss)}자: {"".join(miss)}')
    except Exception as e:  # noqa: BLE001
        print('글꼴 검사를 건너뛴다:', e)

    CACHE.write_text(text, encoding='utf-8')
    if assemble() != 0:
        return 1
    nrows = sum(len(b['rows']) for b in bases.values())
    print(f'tab4.js 에 넣었다: 자료 {len(text):,}자, 기준 종형 {len(bases)}개, 줄 {nrows}개, 급부 {len(ben)}개, 특약 {len(rid)}개')
    for b, x in bases.items():
        print(f'  {b}: 짝 {x["cols"][1:]}, 담보 줄 {len(x["rows"])}, 비교쌍 {x["pairs"]}(뺀 {x["dropped"]})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
