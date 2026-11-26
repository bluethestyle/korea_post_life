"""스냅샷(data/snapshot)에서 관계 그래프 자료(graph.json)를 만든다. 값은 스냅샷 그대로 옮긴다.

쓰기: python proto_src/graph/build_data.py [출력 경로] [--snapshot 스냅샷 폴더] [--orgs all | EPOST,HANWHALIFE,...]
      출력 경로를 주지 않으면 proto_src/graph/graph.json 에 쓴다. 그다음 python proto_src/graph/build.py 로 합친다.
      화면에 올릴 회사(config.SITE_ORGS)만 싣는다(src/postlife/site/orgs.py 가 스냅샷을 읽은 자리에서 거른다). --orgs 로 바꾸며,
      기본과 다른 묶음은 proto_src/graph/graph.json 에 쓰지 않는다(커밋되는 자료다. out/graph_all.json 처럼 다른 곳에 쓴다).
읽는 것(모두 저장소 안)
- data/snapshot/ 의 sys_상품종형, sys_특약, sys_급부, hum_담보매핑, sys_결합제약, sys_시장동향, sys_작업로그, hum_기준값,
  meta.json(자료 시각)
- data/seed/hum_표준담보사전.jsonl (사용여부가 참인 행만)
- data/seed/표준담보_관계.jsonl (표준담보 사이의 넓고 좁은 관계. ID 로 엣지를 만든다)
- data/proposals/표준담보_관계_두판독.jsonl (관계마다 이중 추출의 확신 값만 붙인다)
싣는 종형: 화면에 올린 회사의 종형 전부(2026-11-23까지는 세 회사의 간편 종형 하나와 일반 종형 하나씩, 여섯만 실었다).
차례는 화면의 종형 차례(site/model.py 의 Data.variant_order)다. 급부가 없는 관문전용 종형은 종형 노드와 판매 엣지만 싣는다.
요약(summary): 종형마다 가진 표준담보와 보장분야별 수, 표준담보마다 가진 종형, 표준담보로 이어지지 못한 급부 수, 기준 종형과
맞붙는 종형(sales.json 의 기준별[].맞붙는종형과 같은 함수에서 얻는다), 둘 이상 종형에 걸친 특약 계보. 화면은 이 수를 그대로 쓰고
엣지를 다시 세지 않는다.

스키마 개정 1단계(2026-11-24, docs/proposals/관계그래프_재설계_검토.md 3절과 5.3절)
- 지금 화면 둘(시안 4 tab6.js, 탐색 시안 2 tpl.html)이 깨지지 않게 nodes 의 차례와 형식, 종류 번호 0~6, edges(엣지 종류 0~5),
  summary 의 기존 열쇠, keys 의 기존 번호를 그대로 둔다.
- 새 엣지 종류(6 보유, 7 결합제약, 8 개정, 9 언급 담보, 10 언급 상품)는 ekinds 끝에 붙이고 엣지는 edges2 에 싣는다.
- 새 노드 속성과 매핑 엣지의 확정방식은 기존 속성 뒤에 keys 번호를 받는다(kc 를 두 번에 나눠 부른다).
  keys 의 차례는 KEY_ORDER 로 고정해, 종형 차례나 빈 값에 따라 번호가 바뀌지 않는다(2026-11-26).
- 화면 이름은 kindLabels, ekindLabels, 표시명으로 싣는다(src/postlife/site/terms.py). 판정(우위, 열위, 미보유 따위)은 싣지 않는다
  (화면은 담보 비교 탭과 같은 cover.json 을 읽는다).
- 자료가 이 파일이 아는 모양과 다르면 빌드를 멈춘다(GraphDataError): 관계 시드의 ID 가 사전에 없거나 확신 값을 못 찾을 때,
  결합제약 최대연동 행의 모양이 다를 때, 결합제약과 개정 비교 건이 그래프에 없는 노드를 가리킬 때, 보유 엣지가 담보 비교의
  보유 계산(insights.Holding)과 다를 때, config.COMMON 에 기관구분을 정하지 않은 기관이 생겼을 때.
같은 입력이면 같은 바이트를 쓴다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from postlife.snapshot import read_snapshot  # noqa: E402
from postlife import config  # noqa: E402
from postlife.config import ALL_ORGS  # noqa: E402
from postlife.site import insights  # noqa: E402
from postlife.site import orgs as site_orgs  # noqa: E402
from postlife.site import sales  # noqa: E402
from postlife.site import terms  # noqa: E402
from postlife.site import weekly  # noqa: E402
from postlife.site.model import MAIN_KIND, WAITING_STATE, Data  # noqa: E402

SNAP = ROOT / 'data/snapshot'
STD = ROOT / 'data/seed/hum_표준담보사전.jsonl'
REL_SEED = ROOT / 'data/seed/표준담보_관계.jsonl'
REL = ROOT / 'data/proposals/표준담보_관계_두판독.jsonl'
OUT_DEFAULT = HERE / 'graph.json'

# 노드 종류와 엣지 종류의 안쪽 이름. 이 파일 안에서는 이 이름을 키로 쓰고, graph.json 의 kinds, ekinds 에는 자료 이름
# (terms.GRAPH_NODE_KIND, GRAPH_EDGE_KIND. 보장분야는 보장 대분류, 소식은 시장 동향 따위)을 싣는다. 화면은 종류를 번호로 다룬다
KIND = ['회사', '종형', '특약', '급부', '표준담보', '보장분야', '소식']
EK = ['판매', '포함', '해당', '속함', '관계', '일으킴']          # edges 에 싣는 종류(0~5)
EK2 = ['보유', '결합제약', '개정', '언급 담보', '언급 상품']      # edges2 에 싣는 종류(6~10). 1단계에서 더했다
# 엣지 종류마다 (출발 노드 종류, 도착 노드 종류). 이 밖의 짝은 만들지 않는다(tests/test_graph_data.py 가 본다)
ENDS = {
    '판매': {('회사', '종형')}, '포함': {('종형', '특약'), ('특약', '급부')}, '해당': {('급부', '표준담보')},
    '속함': {('표준담보', '보장분야')}, '관계': {('표준담보', '표준담보')}, '일으킴': {('회사', '소식')},
    '보유': {('종형', '표준담보')}, '결합제약': {('특약', '특약')}, '개정': {('종형', '종형')},
    '언급 담보': {('소식', '표준담보')}, '언급 상품': {('소식', '종형')},
}
# keys(속성 이름 목록)의 차례. 번호는 이 차례로 고정하고, 이 목록에 없는 이름만 노드와 엣지를 만난 차례로 뒤에 붙인다.
# 앞의 37개(기관코드~발표일)는 1단계 전 번호, 기관구분부터는 1단계에서 더한 속성이다(2026-11-24 스냅샷에서 나온 차례 그대로).
# 예전에는 처음 만난 값의 차례로 번호를 정해서, 종형 차례의 첫 종형이 빈 값을 빼면(비갱신 종형의 갱신주기년) 뒤 번호가 당겨졌다.
# 이 스냅샷에 값이 하나도 없는 이름도 번호를 비워 두지 않고 그대로 싣는다(화면은 번호를 keys 로 이름으로 되돌려 읽는다)
KEY_ORDER = (
    '기관코드', '공시상품명', '종형명', '간편고지', '갱신유형', '갱신주기년', '심사유형', '환급유형', '적용시작일',
    '담보구분', '갱신여부', '최소가입금액만원', '최대가입금액만원', '기준지급액', '기준가입금액만원', '면책일수', '감액',
    '근거', '지급횟수제한', '보장대분류', '보장중분류', '급부유형', '비교기준단위만원', '핵심요약', '분류유형', '발표일자',
    '매체명', '출처URL', '판정확률', '갱신', '급부역할', '검토상태', '매핑확률', '관계', '확신_gemini', '확신_claude',
    '발표일',
    '기관구분', '업권', '비교대상', '개정판ID', '모상품ID', '종형계보키', '비교역할', '판매종료일', '특약계보키',
    '가입금액연동', '매핑상태', '추출검수대기항목', '추천표준담보ID', '수집주차', '선별상태', '확정방식', '급부수', '특약수',
    '대표급부ID', '추출검수대기급부수', '매핑검수대기급부수', '제약유형', '근거문구', '신설', '변경', '종료',
)
MAPPED = ('자동확정', '승인', '수정')     # hum_담보매핑 에서 엣지로 싣는 검토상태
AUTO = '자동확정'                         # 확정방식을 붙이는 검토상태(승인, 수정은 담당자가 정한 것이라 붙이지 않는다)
BY_MODEL, BY_CROSS = '확률 산정 모델', '교차 검증'   # 확정방식: 매핑확률이 있으면 확률 산정 모델, 비었으면 교차 검증
GATE_ONLY = '관문전용'                    # 비교역할구분. 급부가 없으면 특약과 급부를 싣지 않는다
# 표준담보로 이어지지 못한 급부의 사유(요약의 미연결사유 차례). 검토상태가 이 밖이면 그 이름을 뒤에 가나다순으로 붙인다
UNLINKED_ORDER = ('대기', '오류', '대상외', '사전밖', '매핑없음')
# 결합제약: 최대연동은 엣지 대신 대상 특약의 가입금액연동 속성으로 싣고, 그 밖의 유형(지금 선행가입)은 결합제약 엣지로 싣는다
LINKED_CAP = '최대연동'
LINKED_CAP_SHAPE = (1, '비율')            # 최대연동 행의 (제약수치, 제약단위). 기준 특약은 주계약이다
# 회사 노드의 기관구분. 보험회사는 config.POST 와 업권이 있는 회사(config.LIFE, NONLIFE, meta.json 의 기관업권)다
ORG_CLASS = {'FSC': '감독기관', 'FSS': '감독기관', 'KLIA': '협회', 'KNIA': '협회', 'COMMON': '업계 공통'}
INSURER, POST_SECTOR = '보험회사', '우체국'
ID_SPLIT = re.compile(r'[;,]')            # 관련표준담보ID 의 구분자(스키마는 세미콜론, sales.py 는 쉼표로 읽는다. 둘 다 받는다)


class GraphDataError(ValueError):
    """자료가 build_data.py 가 아는 모양과 달라 graph.json 을 쓰지 않는다."""


if set(config.COMMON) - set(ORG_CLASS):
    raise GraphDataError(f'config.COMMON 에 기관구분을 정하지 않은 기관이 있다: {sorted(set(config.COMMON) - set(ORG_CLASS))}')


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


def type_label(v: dict) -> str:
    """종형 노드의 이름: 공시상품명(앞의 "무배당 "을 뗀다) 뒤에 종형명. 종형명이 이름에 두 번 들지 않게 한다(띄어쓰기는 무시한다).
    - 공시상품명이 종형명으로 끝나면 공시상품명만 쓴다("… 2606 1종(간편가입315)").
    - 공시상품명의 끝 낱말이 종형명의 앞부분이면 종형명에서 그 앞부분을 뗀 나머지만 붙인다
      ("… 7종(해약환급금미지급형)" 과 "7종(해약환급금 미지급형) 315·5" → "… 7종(해약환급금미지급형) 315·5").
    """
    prod, name = v['공시상품명'].replace('무배당 ', ''), str(v.get('종형명') or '')
    sq = lambda s: s.replace(' ', '')  # noqa: E731
    if sq(prod).endswith(sq(name)):
        return prod
    last = sq(prod.rsplit(' ', 1)[-1])
    if last and sq(name).startswith(last):
        seen = pos = 0
        while seen < len(last):          # 종형명에서 띄어쓰기를 빼고 센 len(last) 글자 뒤의 자리
            seen += name[pos] != ' '
            pos += 1
        rest = name[pos:].strip()
        return f'{prod} {rest}' if rest else prod
    return f'{prod} {name}'


def matchups(data: Data) -> tuple[list[str], dict[str, list[str]]]:
    """(기준 종형, 기준 종형마다 맞붙는 종형). sales.export 와 같은 계산 저장소(sales._Ctx)의 bases 와 default_peers 다.

    sales.json 의 기준종형 차례와 기준별[].맞붙는종형은 이 값이다(points 가 ctx.result(base) 의 맞붙는종형을 쓰고, 그 짝은
    default_peers 와 같은 compare.peers 규칙이다). 여기서 따로 고르지 않는다.
    """
    ctx = sales._Ctx(data, None, None)
    return list(ctx.bases), {b: ctx.default_peers(b) for b in ctx.bases}


def unlinked_reason(m: dict | None) -> str:
    """해당 엣지가 없는 급부의 사유: 매핑 행의 검토상태(대기, 오류, 대상외), 확정했지만 확정표준담보ID 가 비었거나 사전(사용여부
    참)에 없으면 사전밖, 매핑 행이 없으면 매핑없음."""
    if m is None:
        return '매핑없음'
    return '사전밖' if m['검토상태'] in MAPPED else m['검토상태']


def org_props(data: Data, code: str, picked: tuple[str, ...]) -> dict:
    """회사 노드에 1단계에서 더한 속성: 기관구분, 업권, 비교대상(화면에 올린 회사인지)."""
    sector = POST_SECTOR if code in config.POST else data.org_sector(code)
    kind = INSURER if sector else ORG_CLASS.get(code)
    return {'기관구분': kind, '업권': sector, '비교대상': code in picked}


def relation_rows(std_by_id: dict[str, dict]) -> list[dict]:
    """담보 관계 엣지의 원천: 시드(data/seed/표준담보_관계.jsonl)의 ID 와 관계, 이중 추출 파일의 확신 값.
    시드의 ID 가 사전(사용여부 참)에 없거나 같은 (관계, 넓은담보, 좁은담보)의 이중 추출 행이 없으면 빌드를 멈춘다."""
    conf = {(r['관계'], r['넓은담보'], r['좁은담보']): r for r in jl(REL)}
    out = []
    for r in jl(REL_SEED):
        missing = [r[k] for k in ('넓은담보ID', '좁은담보ID') if r.get(k) not in std_by_id]
        if missing:
            raise GraphDataError(f'담보 관계 시드의 표준담보ID 가 사전(사용여부 참)에 없다: {missing} ({r})')
        c = conf.get((r['관계'], r['넓은담보'], r['좁은담보']))
        if c is None:
            raise GraphDataError(f'담보 관계 시드 행의 확신 값을 {REL.relative_to(ROOT)} 에서 찾지 못했다: {r}')
        out.append({**r, '확신_gemini': c.get('확신_gemini'), '확신_claude': c.get('확신_claude')})
    return out


def check_linked_caps(rows: list[dict], riders: dict[str, dict]) -> None:
    """결합제약 최대연동 행이 지금 모양(기준 특약이 주계약, 제약수치 1, 단위 비율, 대상 특약 중복 없음)인지. 다르면 멈춘다.
    이 모양이라 대상 특약의 속성 하나(가입금액연동)로 싣는다. 모양이 바뀌면 엣지로 실을지 다시 정한다."""
    bad = [r['제약ID'] for r in rows
           if riders.get(r['기준특약ID'], {}).get('담보구분') != MAIN_KIND
           or (r.get('제약수치'), r.get('제약단위')) != LINKED_CAP_SHAPE]
    if bad:
        raise GraphDataError(f'결합제약 {LINKED_CAP} 행의 모양이 다르다(기준 특약 주계약, 수치와 단위 {LINKED_CAP_SHAPE}): {bad}')
    dup = sorted(t for t, n in Counter(r['대상특약ID'] for r in rows).items() if n > 1)
    if dup:
        raise GraphDataError(f'결합제약 {LINKED_CAP} 행의 대상 특약이 겹친다: {dup}')


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


def rider_lineages(nl: list[dict], idx: dict[str, int], riders: dict[str, dict], org_order: list[str]) -> dict:
    """summary.특약계보: {기관코드: {특약계보키: [종형 노드 번호]}}. 둘 이상 종형에 걸친 계보만 싣는다. 특약계보키는 정규화한 이름의
    해시라 회사를 넘으면 다른 특약도 같은 키가 된다(주계약 따위). 그래서 회사 안에서만 묶는다. 특약 노드는 하나로 합치지 않는다."""
    found: dict[str, dict[str, set[int]]] = {}
    for n in nl:
        if n['k'] == '특약':
            r = riders[n['i']]
            found.setdefault(n['o'], {}).setdefault(r['특약계보키'], set()).add(idx[r['종형ID']])
    out = {}
    for org in [o for o in org_order if o in found] + sorted(set(found) - set(org_order)):
        multi = {k: sorted(v) for k, v in sorted(found[org].items()) if len(v) >= 2}
        if multi:
            out[org] = multi
    return out


def build(snap_dir: Path = SNAP, orgs=None) -> tuple[dict, dict, list]:
    snap_dir = Path(snap_dir)
    picked = site_orgs.parse(orgs)
    snap = site_orgs.filter_tables(read_snapshot(snap_dir), picked)
    meta = json.loads((snap_dir / 'meta.json').read_text(encoding='utf-8'))
    data = Data(snap, meta)              # 화면 자료(sales.json)와 같은 모델. 종형 차례와 맞붙는 종형을 여기서 얻는다
    std = [r for r in jl(STD) if r.get('사용여부')]
    shown_orgs = tuple(sorted({v['기관코드'] for v in data.variants.values()})) if picked == site_orgs.ALL else picked

    types = [data.variants[vid] for vid in data.variant_order]
    rider_type = {r['특약ID']: r['종형ID'] for r in snap['sys_특약']}
    has_benefit = {rider_type[b['특약ID']] for b in snap['sys_급부'] if b['특약ID'] in rider_type}
    bare = {v['종형ID'] for v in types if v.get('비교역할구분') == GATE_ONLY and v['종형ID'] not in has_benefit}

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    edges2: list[dict] = []

    def node(nid, kind, label, org=None, **props):
        if nid not in nodes:
            nodes[nid] = {'i': nid, 'k': kind, 'l': label, 'o': org,
                          'p': {k: v for k, v in props.items() if v is not None}, 'q': {}}
        return nid

    def more(nid, **props):
        """1단계에서 더한 노드 속성. 기존 속성 뒤에 keys 번호를 받는다."""
        nodes[nid]['q'].update({k: v for k, v in props.items() if v is not None})

    def edge(s, t, kind, **props):
        e = {'s': s, 't': t, 'k': kind, 'p': {k: v for k, v in props.items() if v is not None}, 'q': {}}
        edges.append(e)
        return e

    def edge2(s, t, kind, **props):
        edges2.append({'s': s, 't': t, 'k': kind, 'p': {k: v for k, v in props.items() if v is not None}})

    def org_node(code):
        nid = 'ORG:' + code
        if nid not in nodes:
            node(nid, '회사', ALL_ORGS.get(code, code), code, 기관코드=code)
            more(nid, **org_props(data, code, shown_orgs))
        return nid

    type_ids = set()
    for v in types:
        o = org_node(v['기관코드'])
        node(v['종형ID'], '종형', type_label(v), v['기관코드'], 공시상품명=v['공시상품명'], 종형명=v['종형명'],
             간편고지=v.get('간편고지약칭'), 갱신유형=v.get('갱신유형'), 갱신주기년=v.get('갱신주기년'),
             심사유형=v.get('심사유형'), 환급유형=v.get('환급유형'), 적용시작일=v.get('적용시작일'))
        more(v['종형ID'], 개정판ID=v.get('개정판ID'), 모상품ID=v.get('모상품ID'), 종형계보키=v.get('종형계보키'),
             비교역할=v.get('비교역할구분'), 판매종료일=v.get('판매종료일') or None)
        edge(o, v['종형ID'], '판매')
        if v['종형ID'] not in bare:
            type_ids.add(v['종형ID'])

    org_of_type = {v['종형ID']: v['기관코드'] for v in types}
    riders = {}
    for r in snap['sys_특약']:
        if r['종형ID'] in type_ids:
            org = org_of_type[r['종형ID']]
            riders[r['특약ID']] = r
            node(r['특약ID'], '특약', r['원시특약명'], org, 담보구분=r.get('담보구분'),
                 갱신여부='갱신' if r.get('갱신여부') else '비갱신', 갱신주기년=r.get('갱신주기년'),
                 최소가입금액만원=r.get('최소가입금액만원'), 최대가입금액만원=r.get('최대가입금액만원'))
            more(r['특약ID'], 특약계보키=r.get('특약계보키'))
            edge(r['종형ID'], r['특약ID'], '포함', 담보구분=r.get('담보구분'),
                 갱신='갱신' if r.get('갱신여부') else '비갱신')

    bens = set()
    for b in snap['sys_급부']:
        if b['특약ID'] in riders:
            org = org_of_type[riders[b['특약ID']]['종형ID']]
            bens.add(b['급부ID'])
            node(b['급부ID'], '급부', b['원시급부명'], org, 기준지급액=amount(b),
                 기준가입금액만원=b.get('기준가입금액만원'), 면책일수=b.get('면책기간일수'), 감액=reduce_txt(b),
                 지급횟수제한=b.get('지급횟수제한'), 근거=f'{b.get("근거문서종류")} {b.get("근거문서쪽수")}쪽')
            edge(b['특약ID'], b['급부ID'], '포함', 급부역할=b.get('급부역할'))

    std_by_id = {s['표준담보ID']: s for s in std}
    for s in std:
        node(s['표준담보ID'], '표준담보', s['표준담보명'], None, 보장대분류=s['보장대분류'], 보장중분류=s.get('보장중분류'),
             급부유형=s.get('급부유형'), 비교기준단위만원=s.get('비교기준단위만원'))
        cat = node('CAT:' + s['보장대분류'], '보장분야', s['보장대분류'])
        edge(s['표준담보ID'], cat, '속함', 보장중분류=s.get('보장중분류'))

    mapping = {m['급부ID']: m for m in snap['hum_담보매핑']}
    linked = set()
    for m in snap['hum_담보매핑']:
        if m['급부ID'] in bens and m['검토상태'] in MAPPED:
            sid = m.get('확정표준담보ID')
            if sid and sid in std_by_id:
                prob = m.get('매핑확률')
                e = edge(m['급부ID'], sid, '해당', 검토상태=m['검토상태'], 매핑확률=prob)
                if m['검토상태'] == AUTO:
                    e['q']['확정방식'] = BY_MODEL if isinstance(prob, (int, float)) else BY_CROSS
                linked.add(m['급부ID'])

    for r in relation_rows(std_by_id):
        # 방향은 좁은 담보 → 넓은 담보 그대로다. 지금 화면 둘이 엣지 상세의 출발과 도착, 화살표에 방향을 쓰므로 1단계에서는
        # 바꾸지 않았다(넓은 담보 → 좁은 담보로 바꾸는 일은 화면 2단계 머지 뒤 3단계에서 한다)
        edge(r['좁은담보ID'], r['넓은담보ID'], '관계', 관계=r['관계'], 확신_gemini=r['확신_gemini'],
             확신_claude=r['확신_claude'])

    for t in snap['sys_시장동향']:
        o = org_node(t['기관코드'])
        node(t['동향ID'], '소식', t['핵심요약'][:40], t['기관코드'], 핵심요약=t['핵심요약'], 분류유형=t['분류유형'],
             발표일자=t['발표일자'], 매체명=t.get('매체명'), 출처URL=t.get('출처URL'), 판정확률=t.get('판정확률'))
        more(t['동향ID'], 수집주차=str(t['수집주차']).strip() if t.get('수집주차') else None,
             선별상태=weekly.news_state(data, t))
        edge(o, t['동향ID'], '일으킴', 분류유형=t['분류유형'], 발표일=t['발표일자'])

    # ---- 1단계에서 더한 노드 속성(엣지를 다 만든 뒤에 정하는 것) ----
    out_of: dict[tuple[str, str], list[str]] = {}
    for e in edges:
        out_of.setdefault((e['s'], e['k']), []).append(e['t'])
    cat_order = [n['i'] for n in nodes.values() if n['k'] == '보장분야']
    for rid in riders:
        cats = {c for b in out_of.get((rid, '포함'), []) for s in out_of.get((b, '해당'), []) for c in out_of[(s, '속함')]}
        if cats:                         # 매핑된 급부가 없는 특약(주계약 포함)에는 넣지 않는다
            more(rid, 보장대분류=[nodes[c]['l'] for c in cat_order if c in cats])
    for bid in bens:
        m = mapping.get(bid)
        if bid not in linked:
            more(bid, 매핑상태=unlinked_reason(m))
        if m is not None and m['검토상태'] == WAITING_STATE and m.get('추천표준담보ID'):
            more(bid, 추천표준담보ID=m['추천표준담보ID'])
        if data.pending_benefit.get(bid):
            more(bid, 추출검수대기항목=list(data.pending_benefit[bid]))

    # 결합제약: 최대연동은 대상 특약의 가입금액연동(근거문구 그대로), 그 밖의 유형은 기준 특약 → 대상 특약 엣지
    cons = sorted(snap.get('sys_결합제약', []), key=lambda r: str(r['제약ID']))
    off = [r['제약ID'] for r in cons if r['기준특약ID'] not in riders or r['대상특약ID'] not in riders]
    if off:
        raise GraphDataError(f'결합제약이 그래프에 없는 특약을 가리킨다: {off}')
    caps = [r for r in cons if r['제약유형'] == LINKED_CAP]
    check_linked_caps(caps, riders)
    for r in caps:
        more(r['대상특약ID'], 가입금액연동=r.get('근거문구') or None)

    # ---- 압축 꼴: 노드와 엣지는 배열, 속성 이름은 keys 의 번호로 바꾼다 ----
    nl = list(nodes.values())
    idx = {n['i']: k for k, n in enumerate(nl)}
    bases, peers = matchups(data)
    summary = summarize(nl, edges, idx, types, mapping, bases, peers)

    # ---- edges2(엣지 종류 6~10) ----
    # 6 보유: summary.종형[].표준담보와 같은 (종형, 표준담보). 속성은 담보 비교와 같은 계산(insights.Holding)에서 얻는다
    for v in types:
        tid = v['종형ID']
        held = [nl[i]['i'] for i in summary['종형'][tid]['표준담보']]
        if not held:
            continue
        h = insights.Holding(data, tid)
        if set(h.has) != set(held):
            raise GraphDataError(f'{tid}: 보유 엣지가 담보 비교의 보유 계산과 다르다 {sorted(set(h.has) ^ set(held))}')
        for sid in held:
            views = h.confirmed[sid]
            rep = h.rep(sid)
            edge2(tid, sid, '보유', 급부수=len(views), 특약수=len({x['tid'] for x in views}),
                  대표급부ID=rep['id'] if rep else None,
                  매핑검수대기급부수=len(h.waiting.get(sid, [])) or None,
                  추출검수대기급부수=sum(1 for x in views if x['id'] in data.pending_benefit) or None)
    # 7 결합제약(최대연동 밖의 유형)
    for r in cons:
        if r['제약유형'] != LINKED_CAP:
            edge2(r['기준특약ID'], r['대상특약ID'], '결합제약', 제약유형=r['제약유형'], 제약수치=r.get('제약수치'),
                  제약단위=r.get('제약단위'), 근거문구=r.get('근거문구') or None)
    # 8 개정: sales.json 의 개정변동.짝과 같은 계산(sales.revision_summary)
    for p in sales.revision_summary(data)['짝']:
        if p['전'] not in idx or p['후'] not in idx:
            raise GraphDataError(f'개정 전후 비교 건의 종형이 그래프에 없다: {p}')
        edge2(p['전'], p['후'], '개정', **{k: p[k] for k in sales.REVISION_KINDS})
    # 9, 10 언급 담보, 언급 상품: sys_시장동향 의 관련표준담보ID, 관련종형ID(지금은 모두 비어 있어 0건). 그래프에 없는 ID 는 넘긴다
    # (화면에 올리지 않은 회사의 종형일 수 있다)
    for t in snap['sys_시장동향']:
        for col, kind, want in (('관련표준담보ID', '언급 담보', '표준담보'), ('관련종형ID', '언급 상품', '종형')):
            for x in dict.fromkeys(s.strip() for s in ID_SPLIT.split(str(t.get(col) or '')) if s.strip()):
                if x in nodes and nodes[x]['k'] == want:
                    edge2(t['동향ID'], x, kind)

    keys: list[str] = list(KEY_ORDER)

    def kc(d):
        o = {}
        for k, v in d.items():
            if k not in keys:
                keys.append(k)
            o[str(keys.index(k))] = v
        return o

    node_rows = [[n['i'], KIND.index(n['k']), n['l'], n['o'], kc(n['p'])] for n in nl]
    edge_rows = [[idx[e['s']], idx[e['t']], EK.index(e['k']), kc(e['p'])] for e in edges]
    for row, n in zip(node_rows, nl):        # 1단계에서 더한 속성은 기존 속성(과 기존 keys 번호) 뒤에 붙인다
        row[4].update(kc(n['q']))
    for row, e in zip(edge_rows, edges):
        row[3].update(kc(e['q']))
    edge2_rows = [[idx[e['s']], idx[e['t']], len(EK) + EK2.index(e['k']), kc(e['p'])] for e in edges2]

    kinds = [terms.GRAPH_NODE_KIND.get(k, k) for k in KIND]
    ekinds = [terms.GRAPH_EDGE_KIND.get(k, k) for k in EK + EK2]
    out = {'snapshot_at': meta['snapshot_at'], 'kinds': kinds, 'ekinds': ekinds,
           'kindLabels': terms.graph_kind_labels(kinds), 'ekindLabels': terms.graph_edge_labels(ekinds),
           'nodes': node_rows, 'edges': edge_rows, 'edges2': edge2_rows, 'keys': keys}
    summary['특약계보'] = rider_lineages(nl, idx, riders, summary['회사'])
    out['summary'] = summary
    # 화면 코드가 키로 쓰는 값(비교역할, 미연결사유, 선별상태, 속성 이름)의 화면 이름. sales.json 의 표시명과 같은 꼴(값 → 이름)이다
    out['표시명'] = terms.graph_display_names()
    return out, nodes, edges


def dumps(out: dict) -> str:
    """graph.json 의 글(빈칸 없는 JSON, 한글 그대로)."""
    return json.dumps(out, ensure_ascii=False, separators=(',', ':'))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?', type=Path, default=OUT_DEFAULT, help='출력 경로(기본 proto_src/graph/graph.json)')
    ap.add_argument('--snapshot', type=Path, default=SNAP, help='스냅샷 폴더(기본 data/snapshot)')
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
    try:
        out, nodes, edges = build(args.snapshot, picked)
    except GraphDataError as e:
        print('오류:', e)
        print('graph.json 을 쓰지 않았다.')
        return 1
    s = dumps(out)
    out_path.write_text(s, encoding='utf-8')
    summary = out['summary']
    print('화면에 올린 회사:', site_orgs.describe(picked))
    print(out_path, 'bytes', len(s.encode('utf-8')), '(요약', len(dumps(summary).encode('utf-8')), 'bytes)')
    print('nodes', len(nodes), dict(Counter(n['k'] for n in nodes.values())))
    print('edges', len(edges), dict(Counter(e['k'] for e in edges)))
    print('edges2', len(out['edges2']), dict(Counter(out['ekinds'][e[2]] for e in out['edges2'])))
    print('종형', len(summary['종형']), '기준 종형', len(summary['기준종형']),
          '미연결 급부', sum(t['미연결급부'] for t in summary['종형'].values()),
          '특약 계보', sum(len(v) for v in summary['특약계보'].values()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
