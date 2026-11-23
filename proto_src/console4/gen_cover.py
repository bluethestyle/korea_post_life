"""탭 4(담보 비교)와 탭 5(관계 그림)가 쓰는 비교 자료를 tab4.js 첫 줄(`const CV = ...;`)로 넣는다.

자료 전체를 다시 만들 때는 python scripts/export_app_data.py 를 쓴다. 이 스크립트는 탭 4 코드(tab4.src.js)만 고쳤을 때
다시 합치는 길(--assemble)과, 담보 비교 자료만 다시 뽑는 길이다.

쓰기: python proto_src/console4/gen_cover.py [--assemble]
- --assemble 은 자료를 다시 뽑지 않고 cover.json 과 tab4.src.js 만 합쳐 tab4.js 를 쓴다(코드만 고쳤을 때).
- 인자가 없으면 data/snapshot 으로 자료를 뽑아 cover.json 에 두고 tab4.js 를 쓴다. 기준 종형과 짝은 sales.json 을 따르고,
  자료 시각이 sales.json 과 다르면 멈춘다. 계산은 src/postlife/site/console4.py(build_cover, cover_text)에 있다.

왜 따로 뽑나: 시안 3의 자료 줄(const D)은 간편 1~3종의 짝만 담았고(4종, 단일 없음), 조건 우열 부호가 지금 계산(면책, 감액,
지급 형태)보다 앞선 것이다. 화면의 판정이 sales.json(영업 인사이트)과 어긋나지 않게(R10) sales.py 가 쓰는 계산
(insights.analyze 의 비교쌍, 시사점, 뺀 시사점)을 그대로 읽어 담는다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))

from postlife.site import console4 as C4  # noqa: E402
from postlife.site.model import load  # noqa: E402
from postlife.site.relations import load_relations  # noqa: E402

TAB4 = HERE / 'tab4.js'
TAB4_SRC = HERE / 'tab4.src.js'       # 손으로 쓰는 탭 4 코드. tab4.js = 자료 한 줄 + 이 파일
CACHE = HERE / 'cover.json'           # 뽑은 자료(검사 글자를 \u 로 바꾼 JSON 글자)
SALES = HERE / 'sales.json'


def assemble() -> int:
    """cover.json 과 tab4.src.js 를 합쳐 tab4.js 를 쓴다(자료를 다시 뽑지 않는다)."""
    if not CACHE.exists() or not TAB4_SRC.exists():
        print('cover.json 이나 tab4.src.js 가 없다')
        return 1
    TAB4.write_text(C4.assemble_tab4(CACHE.read_text(encoding='utf-8'), TAB4_SRC.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'tab4.js 를 썼다: {TAB4.stat().st_size:,}바이트')
    return 0


def main() -> int:
    if '--assemble' in sys.argv:
        return assemble()
    S = json.loads(SALES.read_text(encoding='utf-8'))
    data = load(ROOT / 'data/snapshot')
    try:
        cover = C4.build_cover(data, S, load_relations())
        text = C4.cover_text(cover)
    except ValueError as e:
        print(e)
        return 1
    CACHE.write_text(text, encoding='utf-8')
    if assemble() != 0:
        return 1
    bases = cover['b']
    nrows = sum(len(b['rows']) for b in bases.values())
    print(f'tab4.js 에 넣었다: 자료 {len(text):,}자, 기준 종형 {len(bases)}개, 줄 {nrows}개, 급부 {len(cover["ben"])}개, 특약 {len(cover["rid"])}개')
    for b, x in bases.items():
        print(f'  {b}: 짝 {x["cols"][1:]}, 담보 줄 {len(x["rows"])}, 비교쌍 {x["pairs"]}(뺀 {x["dropped"]})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
