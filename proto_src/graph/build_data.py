"""사본(data/snapshot)에서 관계망 탐색 시안 2의 자료(graph.json)를 만든다. 값은 사본 그대로 옮긴다.

쓰기: python proto_src/graph/build_data.py [출력 경로]
      출력 경로를 주지 않으면 proto_src/graph/graph.json 에 쓴다. 그다음 python proto_src/graph/build.py 로 합친다.
읽는 것(모두 저장소 안)
- data/snapshot/ 의 sys_상품종형, sys_특약, sys_급부, hum_담보매핑, sys_시장동향, meta.json(자료 시각)
- data/seed/hum_표준담보사전.jsonl (사용여부가 참인 줄만)
- data/proposals/표준담보_관계_두판독.jsonl (표준담보 사이의 넓고 좁은 관계)
견줄 종형(WANT)이 사본에서 한 줄로 집히지 않으면 멈춘다. 같은 입력이면 같은 바이트를 쓴다.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from postlife.snapshot import read_snapshot  # noqa: E402
from postlife.config import INSTITUTIONS  # noqa: E402

SNAP = ROOT / 'data/snapshot'
STD = ROOT / 'data/seed/hum_표준담보사전.jsonl'
REL = ROOT / 'data/proposals/표준담보_관계_두판독.jsonl'
OUT_DEFAULT = HERE / 'graph.json'

# 견줄 종형: 세 회사의 간편 종형 하나와 일반 종형 하나씩. (기관코드, 공시상품명에 든 글자, 종형명에 든 글자)
WANT = [
    ('EPOST', '간편한건강보험', '2종(간편가입325)'),
    ('EPOST', '간편한건강보험', '4종(일반가입)'),
    ('HANWHALIFE', '시그니처', '간편가입형(2년)'),
    ('HANWHALIFE', '시그니처', '일반가입형'),
    ('SAMSUNGFIRE', '새로고침', '325·5'),
    ('SAMSUNGFIRE', '새로고침', '일반고지'),
]
KIND = ['회사', '종형', '특약', '급부', '표준담보', '보장분야', '소식']
EK = ['판매', '포함', '해당', '속함', '관계', '일으킴']
MAPPED = ('자동확정', '승인', '수정')     # hum_담보매핑 에서 엣지로 싣는 검토상태


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


def build() -> tuple[dict, dict, list]:
    snap = read_snapshot(SNAP)
    std = [r for r in jl(STD) if r.get('사용여부')]
    rel = jl(REL)

    types = []
    for org, p, t in WANT:
        hit = [v for v in snap['sys_상품종형'] if v['기관코드'] == org and p in v['공시상품명'] and t in v['종형명']]
        if len(hit) != 1:
            sys.exit(f'견줄 종형이 한 줄로 집히지 않는다: {org} {p} {t} -> {len(hit)}줄. WANT 를 지금 사본에 맞게 고친다')
        types.append(hit[0])

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
        return node('ORG:' + code, '회사', INSTITUTIONS.get(code, code), code, 기관코드=code)

    type_ids = set()
    for v in types:
        o = org_node(v['기관코드'])
        label = v['공시상품명'].replace('무배당 ', '') + ' ' + v['종형명']
        node(v['종형ID'], '종형', label, v['기관코드'], 공시상품명=v['공시상품명'], 종형명=v['종형명'],
             간편고지=v.get('간편고지약칭'), 갱신유형=v.get('갱신유형'), 갱신주기년=v.get('갱신주기년'),
             심사유형=v.get('심사유형'), 환급유형=v.get('환급유형'), 적용시작일=v.get('적용시작일'))
        edge(o, v['종형ID'], '판매')
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

    meta = json.loads((SNAP / 'meta.json').read_text(encoding='utf-8'))
    out = {'snapshot_at': meta['snapshot_at'], 'kinds': KIND, 'ekinds': EK,
           'nodes': [[n['i'], KIND.index(n['k']), n['l'], n['o'], kc(n['p'])] for n in nl],
           'edges': [[idx[e['s']], idx[e['t']], EK.index(e['k']), kc(e['p'])] for e in edges]}
    out['keys'] = keys
    return out, nodes, edges


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT_DEFAULT
    out, nodes, edges = build()
    s = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    out_path.write_text(s, encoding='utf-8')
    print(out_path, 'bytes', len(s.encode('utf-8')))
    print('nodes', len(nodes), dict(Counter(n['k'] for n in nodes.values())))
    print('edges', len(edges), dict(Counter(e['k'] for e in edges)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
