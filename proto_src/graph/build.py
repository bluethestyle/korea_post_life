"""관계망 탐색 시안 2를 한 파일로 합친다: tpl.html + graph.json + 글꼴(proto_src/fonts/fonts_graph2.css).

쓰기: python proto_src/graph/build.py [출력 경로] [--data graph.json 경로]
      출력 경로를 주지 않으면 site/proto/graph2.html 에 쓴다. --data 를 주지 않으면 proto_src/graph/graph.json 을 싣는다.
자료(graph.json)는 먼저 python proto_src/graph/build_data.py 로 사본(data/snapshot)에서 만든다.

tpl.html 의 자리 표시 두 곳을 채운다
- /*__FONTS__*/ : 글꼴 css 를 그대로 넣는다
- __DATA__      : graph.json 을 그대로 넣는다(<script type="application/json" id="gdata"> 안이라 "</" 만 "<\\/" 로 바꾼다)
합친 파일에 외부 요청(src, href, url() 의 바깥 주소, <link>, @import)이 있으면 쓰지 않고 멈춘다.
같은 입력이면 같은 바이트를 쓴다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'proto_src/console4'))
import terms_check  # noqa: E402

OUT_DEFAULT = ROOT / 'site/proto/graph2.html'
TPL = HERE / 'tpl.html'
DATA_DEFAULT = HERE / 'graph.json'
FONTS = ROOT / 'proto_src/fonts/fonts_graph2.css'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?', type=Path, default=OUT_DEFAULT, help='출력 경로(기본 site/proto/graph2.html)')
    ap.add_argument('--data', type=Path, default=DATA_DEFAULT, help='graph.json 경로(기본 proto_src/graph/graph.json)')
    args = ap.parse_args()

    errors: list[str] = []
    errors.extend(terms_check.check_graph_sources(TPL))
    tpl = TPL.read_text(encoding='utf-8')
    for mark in ('/*__FONTS__*/', '__DATA__'):
        if tpl.count(mark) != 1:
            errors.append(f'tpl.html 에 자리 표시 {mark} 가 한 번 있어야 한다({tpl.count(mark)}번)')
    if not args.data.exists():
        errors.append(f'{args.data} 이 없다. python proto_src/graph/build_data.py 로 먼저 만든다')
        data = ''
    else:
        data = args.data.read_text(encoding='utf-8')
        try:
            json.loads(data)
        except ValueError as e:
            errors.append(f'{args.data} 이 JSON 으로 읽히지 않는다: {e}')
    if FONTS.exists():
        fonts = FONTS.read_text(encoding='utf-8')
    else:
        print(f'경고: {FONTS} 이 없다. 기기 글꼴로 그려진다')
        fonts = ''

    page = tpl.replace('/*__FONTS__*/', fonts).replace('__DATA__', data.replace('</', '<\\/'))

    # 합친 파일 검사: 외부 요청이 없어야 한다(자료 안의 출처URL 은 글자일 뿐이라 걸리지 않는다)
    for pat, what in [(r'''(?:src|href)\s*=\s*["']?\s*(?:https?:)?//''', 'src/href 외부 주소'),
                      (r'''url\(\s*["']?\s*(?:https?:)?//''', 'url() 외부 주소'),
                      (r'<link\b', '<link> 태그'), (r'@import', '@import')]:
        for m in re.finditer(pat, page, flags=re.I):
            errors.append(f'합친 파일에 {what}: {page[max(0, m.start() - 40):m.end() + 40]!r}')

    if errors:
        for e in errors:
            print('오류:', e)
        print(f'오류 {len(errors)}건. 쓰지 않았다.')
        return 1
    out: Path = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding='utf-8', newline='\n')
    print(out, len(page.encode('utf-8')), 'bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
