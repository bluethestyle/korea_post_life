"""시안 4 가입 관문 탭(tab3)의 미리 계산한 자료만 다시 만든다: 구성 예시(combo.json)와 관문 나무(gate.json).

자료 전체를 다시 만들 때는 python scripts/export_app_data.py 를 쓴다(sales.json, combo.json, gate.json, cover.json,
d.json, tab3.js, tab4.js 를 같은 사본으로 한 번에). 이 스크립트는 그 가운데 탭 3 자료만 다시 만드는 길이다.

쓰기: python proto_src/console4/build_combo.py [--snapshot 사본 폴더] [--no-inject]

계산은 src/postlife/site/console4.py(build_combo, build_gate)에 있다. --no-inject 가 없으면 두 JSON 을 줄인 꼴을
tab3.js 의 자료 줄(/*__T3DATA_BEGIN__*/ ... /*__T3DATA_END__*/)에도 넣는다. build.py 는 tabN.js 만 합치므로 탭 3 의 자료는
tab3.js 안에 실어야 한다. build 의 글 검사(가운뎃점, "됨" 따위)에 걸리는 글자만 \\u 로 적는다(console4.js_safe).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))

from postlife.site import console4 as C4  # noqa: E402
from postlife.site.model import load  # noqa: E402

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', type=Path, default=ROOT / 'data' / 'snapshot')
    ap.add_argument('--no-inject', action='store_true')
    args = ap.parse_args()
    data = load(args.snapshot)
    c = C4.build_combo(data)
    g = C4.build_gate(data)
    for name, obj in (('combo.json', c), ('gate.json', g)):
        t = C4.dumps(obj)
        (HERE / name).write_text(t, encoding='utf-8')
        print(f'{HERE / name}: {len(t.encode("utf-8")):,}바이트')
    if not args.no_inject:
        p = HERE / 'tab3.js'
        blob = C4.tab3_blob(c, g)
        try:
            text = C4.inject_tab3(p.read_text(encoding='utf-8'), blob)
        except ValueError as e:
            print(f'{e}. 넣지 않았다.')
            return 1
        p.write_text(text, encoding='utf-8')
        print(f'tab3.js 자료 줄에 넣었다({len(blob.encode("utf-8")):,}바이트)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
