"""사본(data/snapshot)에서 관계망 자료(graph.json)를 만든다. 값은 사본 그대로 옮긴다.

쓰기: python proto_src/graph/build_data.py [출력 경로] [--snapshot 사본 폴더] [--orgs all | EPOST,HANWHALIFE,...]
      출력 경로를 주지 않으면 proto_src/graph/graph.json 에 쓴다. 그다음 python proto_src/graph/build.py 로 합친다.
      화면에 올릴 회사(config.SITE_ORGS)만 싣는다(src/postlife/site/orgs.py 가 사본을 읽은 자리에서 거른다). --orgs 로 바꾸며,
      기본과 다른 묶음은 proto_src/graph/graph.json 에 쓰지 않는다(커밋되는 자료다. out/graph_all.json 처럼 다른 곳에 쓴다).
읽는 것(모두 저장소 안)
- data/snapshot/ 의 sys_상품종형, sys_특약, sys_급부, hum_담보매핑, sys_시장동향, meta.json(자료 시각)
- data/seed/hum_표준담보사전.jsonl (사용여부가 참인 줄만)
- data/proposals/표준담보_관계_두판독.jsonl (표준담보 사이의 넓고 좁은 관계)
싣는 종형: 화면에 올린 회사의 종형 전부(2026-11-23까지는 세 회사의 간편 종형 하나와 일반 종형 하나씩, 여섯만 실었다).
차례는 화면의 종형 차례(site/model.py 의 Data.variant_order)다. 급부가 없는 관문전용 종형은 종형 노드와 판매 엣지만 싣는다.
요약(summary): 종형마다 가진 표준담보와 보장분야별 수, 표준담보마다 가진 종형, 표준담보로 이어지지 못한 급부 수, 기준 종형과
맞붙는 종형(sales.json 의 기준별[].맞붙는종형과 같은 함수에서 얻는다). 화면은 이 수를 그대로 쓰고 엣지를 다시 세지 않는다.
같은 입력이면 같은 바이트를 쓴다.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from postlife.snapshot import read_snapshot  # noqa: E402
from postlife.config import ALL_ORGS  # noqa: E402
from postlife.site import orgs as site_orgs  # noqa: E402
from postlife.site import sales  # noqa: E402
from postlife.site import terms  # noqa: E402
from postlife.site.model import Data  # noqa: E402

SNAP = ROOT / 'data/snapshot'
STD = ROOT / 'data/seed/hum_표준담보사전.jsonl'
REL = ROOT / 'data/proposals/표준담보_관계_두판독.jsonl'
OUT_DEFAULT = HERE / 'graph.json'

# 노드 종류와 엣지 종류의 안쪽 이름. 이 파일 안에서는 이 이름을 키로 쓰고, graph.json 의 kinds, ekinds 에는 화면 이름
# (terms.GRAPH_NODE_KIND, GRAPH_EDGE_KIND. 보장분야는 보장 대분류, 소식은 시장 동향 따위)을 싣는다. 화면은 종류를 번호로 다룬다
KIND = ['회사', '종형', '특약', '급부', '표준담보', '보장분야', '소식']
EK = ['판매', '포함', '해당', '속함', '관계', '일으킴']
MAPPED = ('자동확정', '승인', '수정')     # hum_담보매핑 에서 엣지로 싣는 검토상태
GATE_ONLY = '관문전용'                    # 비교역할구분. 급부가 없으면 특약과 급부를 싣지 않는다
# 표준담보로 이어지지 못한 급부의 사유(요약의 미연결사유 차례). 검토상태가 이 밖이면 그 이름을 뒤에 가나다순으로 붙인다
UNLINKED_ORDER = ('대기', '오류', '대상외', '사전밖', '매핑없음')


def jl(p: Path) -> list[dict]:
    with open(p, encoding='utf-8') as f:
        return [json.loads(ln) for ln in f if ln.strip()]


NO_AMOUNT = ('차등지급', '실손보상', '분할지급', '현물급부')   # 금액 하나로 담기지 않는 지급기준구분(두 금액이 비어 있다)


def amount(b: dict) -> str | None:
    a, base = b.get('기준지급금액만원'), b.get('기준가입금액만원')
    if b.get('지급기준구분') in NO_AMOUNT:
        return b['지급기준구분']
    if b.get('지급기준구분') == '가입금액비율':
        if a is not None and base:
            return f'가입금액의 {a / base * 100:g}%'
        return None
    return None if a is None else f'{a:g}만원'


def reduce_txt(b: dict) -> str:
    if b.get('지급기준구분') in NO_AMOUNT:          # 감액을 읽지 않은 꼴이라 "없음"이 아니다
        return '원문 확인'
    out = []
    for m, r in (('감액개월1', '감액지급률1'), ('감액개월2', '감액지급률2')):
        if b.get(m) is not None and b.get(r) is not None:
            out.append(f'{b[m]}개월 이내 {b[r] * 100:g}%')
    if b.get('감액예외'):
        out.append('예외: ' + str(b['감액예외']))
    return ', '.join(out) or '없음'


def matchups(data: Data) -> tuple[list[str], dict[str, list[str]]]:
    """(기준 종형, 기준 종형마다 맞붙는 종형). sales.export 와 같은 계산 저장소(sales._Ctx)의 bases 와 default_peers 다.

    sales.json 의 기준종형 차례와 기준별[].맞붙는종형은 이 값이다(points 가 ctx.result(base) 의 맞붙는종형을 쓰고, 그 짝은
    default_peers 와 같은 compare.peers 규칙이다). 여기서 따로 고르지 않는다.
    """
    ctx = sales._Ctx(data, None, None)
    return list(ctx.bases), {b: ctx.default_peers(b) for b in ctx.bases}


def unlinked_reason(m: dict | None) -> str:
    """해당 엣지가 없는 급부의 사유: 매핑 줄의 검토상태(대기, 오류, 대상외), 확정했지만 확정표준담보ID 가 비었거나 사전(사용여부
    참)에 없으면 사전밖, 매핑 줄이 없으면 매핑없음."""
    if m is None:
        return '매핑없음'
    return '사전밖' if m['검토상태'] in MAPPED else m['검토상태']


def summarize(nl: list[dict], edges: list[dict], idx: dict[str, int], types: list[dict], mapping: dict[str, dict],
              bases: list[str], peers: dict[str, list[str]]) -> dict:
    """graph.json 의 요약. 수는 모두 엣지를 따라 센다(종형 -포함-> 특약 -포함-> 급부 -해당-> 표준담보 -속함-> 보장분야)."""
    kind = {n['i']: n['k'] for n in nl}
    out_of: dict[tuple[str, str], list[str]] = {}
    for e in edges:
        out_of.setdefault((e['s'], e['k']), []).append(e['t'])
    cat_of = {s: out_of[(s, '속함')][0] for s in idx if kind[s] == '표준담보' and (s, '속함') in out_of}
    cat_order = [n['i'] for n in nl if n['k'] == '보장분야']

    per_type: dict[str, dict] = {}
    holders: dict[str, list[int]] = {n['i']: [] for n in nl if n['k'] == '표준담보'}
    for v in types:
        tid = v['종형ID']
        riders = [r for r in out_of.get((tid, '포함'), []) if kind[r] == '특약']
        bens = [b for r in riders for b in out_of.get((r, '포함'), []) if kind[b] == '급부']
        stds: set[str] = set()
        reasons: Counter = Counter()
        for b in bens:
            hit = out_of.get((b, '해당'), [])
            if hit:
                stds.update(hit)
            else:
                reasons[unlinked_reason(mapping.get(b))] += 1
        by_cat = Counter(cat_of[s] for s in stds if s in cat_of)
        for s in stds:
            holders[s].append(idx[tid])
        extra = sorted(k for k in reasons if k not in UNLINKED_ORDER)
        row = {'노드': idx[tid], '심사유형': v.get('심사유형'), '비교역할': v.get('비교역할구분'),
               '판매종료일': v.get('판매종료일') or None, '특약수': len(riders), '급부수': len(bens),
               '표준담보': sorted(idx[s] for s in stds),
               '보장분야별': {c: by_cat[c] for c in cat_order if by_cat[c]},
               '미연결급부': sum(reasons.values()),
               '미연결사유': {k: reasons[k] for k in (*UNLINKED_ORDER, *extra) if reasons[k]}}
        per_type[tid] = {k: x for k, x in row.items() if x is not None}
    return {
        '회사': list(dict.fromkeys(v['기관코드'] for v in types)),
        '종형': per_type,
        '표준담보별종형': {s: sorted(ix) for s, ix in holders.items()},
        '기준종형': bases,
        '맞붙는종형': peers,
    }


def build(snap_dir: Path = SNAP, orgs=None) -> tuple[dict, dict, list]:
    snap_dir = Path(snap_dir)
    picked = site_orgs.parse(orgs)
    snap = site_orgs.filter_tables(read_snapshot(snap_dir), picked)
    meta = json.loads((snap_dir / 'meta.json').read_text(encoding='utf-8'))
    data = Data(snap, meta)              # 화면 자료(sales.json)와 같은 모델. 종형 차례와 맞붙는 종형을 여기서 얻는다
    std = [r for r in jl(STD) if r.get('사용여부')]
    rel = jl(REL)

    types = [data.variants[vid] for vid in data.variant_order]
    rider_type = {r['특약ID']: r['종형ID'] for r in snap['sys_특약']}
    has_benefit = {rider_type[b['특약ID']] for b in snap['sys_급부'] if b['특약ID'] in rider_type}
    bare = {v['종형ID'] for v in types if v.get('비교역할구분') == GATE_ONLY and v['종형ID'] not in has_benefit}

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def node(nid, kind, label, org=None, **props):
        if nid not in nodes:
            nodes[nid] = {'i': nid, 'k': kind, 'l': label, 'o': org,
                          'p': {k: v for k, v in props.items() if v is not None}}
        return nid

    def edge(s, t, kind, **props):
        edges.append({'s': s, 't': t, 'k': kind, 'p': {k: v for k, v in props.items() if v is not None}})

    def org_node(code):
        return node('ORG:' + code, '회사', ALL_ORGS.get(code, code), code, 기관코드=code)

    type_ids = set()
    for v in types:
        o = org_node(v['기관코드'])
        label = v['공시상품명'].replace('무배당 ', '') + ' ' + v['종형명']
        node(v['종형ID'], '종형', label, v['기관코드'], 공시상품명=v['공시상품명'], 종형명=v['종형명'],
             간편고지=v.get('간편고지약칭'), 갱신유형=v.get('갱신유형'), 갱신주기년=v.get('갱신주기년'),
             심사유형=v.get('심사유형'), 환급유형=v.get('환급유형'), 적용시작일=v.get('적용시작일'))
        edge(o, v['종형ID'], '판매')
        if v['종형ID'] not in bare:
            type_ids.add(v['종형ID'])

    org_of_type = {v['종형ID']: v['기관코드'] for v in types}
    riders = {}
    for r in snap['sys_특약']:
        if r['종형ID'] in type_ids:
            org = org_of_type[r['종형ID']]
            riders[r['특약ID']] = org
            node(r['특약ID'], '특약', r['원시특약명'], org, 담보구분=r.get('담보구분'),
                 갱신여부='갱신' if r.get('갱신여부') else '비갱신', 갱신주기년=r.get('갱신주기년'),
                 최소가입금액만원=r.get('최소가입금액만원'), 최대가입금액만원=r.get('최대가입금액만원'))
            edge(r['종형ID'], r['특약ID'], '포함', 담보구분=r.get('담보구분'),
                 갱신='갱신' if r.get('갱신여부') else '비갱신')

    bens = set()
    for b in snap['sys_급부']:
        if b['특약ID'] in riders:
            org = riders[b['특약ID']]
            bens.add(b['급부ID'])
            node(b['급부ID'], '급부', b['원시급부명'], org, 기준지급액=amount(b),
                 기준가입금액만원=b.get('기준가입금액만원'), 면책일수=b.get('면책기간일수'), 감액=reduce_txt(b),
                 지급횟수제한=b.get('지급횟수제한'), 근거=f'{b.get("근거문서종류")} {b.get("근거문서쪽수")}쪽')
            edge(b['특약ID'], b['급부ID'], '포함', 급부역할=b.get('급부역할'))

    std_by_id = {s['표준담보ID']: s for s in std}
    std_by_name = {s['표준담보명']: s for s in std}
    for s in std:
        node(s['표준담보ID'], '표준담보', s['표준담보명'], None, 보장대분류=s['보장대분류'], 보장중분류=s.get('보장중분류'),
             급부유형=s.get('급부유형'), 비교기준단위만원=s.get('비교기준단위만원'))
        cat = node('CAT:' + s['보장대분류'], '보장분야', s['보장대분류'])
        edge(s['표준담보ID'], cat, '속함', 보장중분류=s.get('보장중분류'))

    for m in snap['hum_담보매핑']:
        if m['급부ID'] in bens and m['검토상태'] in MAPPED:
            sid = m.get('확정표준담보ID')
            if sid and sid in std_by_id:
                edge(m['급부ID'], sid, '해당', 검토상태=m['검토상태'],
                     매핑확률=m['매핑확률'] if m.get('매핑확률') is not None else '교차 확인')

    for r in rel:
        a, b = std_by_name.get(r['좁은담보']), std_by_name.get(r['넓은담보'])
        if a and b:
            edge(a['표준담보ID'], b['표준담보ID'], '관계', 관계=r['관계'], 확신_gemini=r.get('확신_gemini'),
                 확신_claude=r.get('확신_claude'))
        else:
            print('관계 이름 못 찾음', r, file=sys.stderr)

    for t in snap['sys_시장동향']:
        o = org_node(t['기관코드'])
        node(t['동향ID'], '소식', t['핵심요약'][:40], t['기관코드'], 핵심요약=t['핵심요약'], 분류유형=t['분류유형'],
             발표일자=t['발표일자'], 매체명=t.get('매체명'), 출처URL=t.get('출처URL'), 판정확률=t.get('판정확률'))
        edge(o, t['동향ID'], '일으킴', 분류유형=t['분류유형'], 발표일=t['발표일자'])

    # 압축 꼴: 노드와 엣지는 배열, 속성 이름은 keys 의 번호로 바꾼다
    nl = list(nodes.values())
    idx = {n['i']: k for k, n in enumerate(nl)}
    keys: list[str] = []

    def kc(d):
        o = {}
        for k, v in d.items():
            if k not in keys:
                keys.append(k)
            o[str(keys.index(k))] = v
        return o

    out = {'snapshot_at': meta['snapshot_at'],
           'kinds': [terms.GRAPH_NODE_KIND.get(k, k) for k in KIND], 'ekinds': [terms.GRAPH_EDGE_KIND.get(k, k) for k in EK],
           'nodes': [[n['i'], KIND.index(n['k']), n['l'], n['o'], kc(n['p'])] for n in nl],
           'edges': [[idx[e['s']], idx[e['t']], EK.index(e['k']), kc(e['p'])] for e in edges]}
    out['keys'] = keys
    bases, peers = matchups(data)
    mapping = {m['급부ID']: m for m in snap['hum_담보매핑']}
    out['summary'] = summarize(nl, edges, idx, types, mapping, bases, peers)
    # 화면 코드가 키로 쓰는 값(비교역할, 미연결사유, 속성 이름)의 화면 이름. sales.json 의 표시명과 같은 꼴(값 → 이름)이다
    out['표시명'] = terms.graph_display_names()
    return out, nodes, edges


def dumps(out: dict) -> str:
    """graph.json 의 글(빈칸 없는 JSON, 한글 그대로)."""
    return json.dumps(out, ensure_ascii=False, separators=(',', ':'))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?', type=Path, default=OUT_DEFAULT, help='출력 경로(기본 proto_src/graph/graph.json)')
    ap.add_argument('--snapshot', type=Path, default=SNAP, help='사본 폴더(기본 data/snapshot)')
    site_orgs.add_argument(ap)
    args = ap.parse_args()
    try:
        picked = site_orgs.parse(args.orgs)
    except ValueError as e:
        ap.error(str(e))
    out_path = args.out
    if not site_orgs.is_default(picked) and out_path.resolve() == OUT_DEFAULT.resolve():
        print(f'기본과 다른 회사 묶음({site_orgs.describe(picked)})의 자료는 {OUT_DEFAULT} 에 쓰지 않는다(커밋되는 자료다). '
              '출력 경로를 out/graph_test.json 처럼 따로 준다')
        return 1
    out, nodes, edges = build(args.snapshot, picked)
    s = dumps(out)
    out_path.write_text(s, encoding='utf-8')
    summary = out['summary']
    print('화면에 올린 회사:', site_orgs.describe(picked))
    print(out_path, 'bytes', len(s.encode('utf-8')), '(요약', len(dumps(summary).encode('utf-8')), 'bytes)')
    print('nodes', len(nodes), dict(Counter(n['k'] for n in nodes.values())))
    print('edges', len(edges), dict(Counter(e['k'] for e in edges)))
    print('종형', len(summary['종형']), '기준 종형', len(summary['기준종형']),
          '미연결 급부', sum(t['미연결급부'] for t in summary['종형'].values()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
