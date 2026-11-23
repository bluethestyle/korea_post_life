"""사본으로 시안 4(proto_src/console4)가 읽는 화면 자료를 한 번에 다시 만든다(src/postlife/site/console4.py).

쓰기: python scripts/export_app_data.py [--snapshot data/snapshot] [--out proto_src/console4]
      그다음 python proto_src/console4/build.py 로 한 파일(site/proto/console4.html)로 합친다.

만드는 파일(모두 같은 사본, 같은 자료 시각)
- sales.json   영업 인사이트(sales.export)
- combo.json, gate.json   가입 관문 탭의 구성 예시와 관문 나무. 줄인 꼴을 tab3.js 의 자료 줄(9번 줄의 두 표식 사이)에 넣는다
- cover.json   담보 비교 탭과 관계 그림의 자료. tab4.js = "const CV = " + cover.json + ";" + tab4.src.js
- d.json       const D (lineup.export, 간편 세 등급 x 세 회사 비교 자료)
- tab3.js, tab4.js   위 자료를 실은 탭 코드. 손으로 쓴 코드(tab3.js 의 표식 밖, tab4.src.js)는 proto_src/console4 에서 읽고 고치지 않는다

--out 을 다른 폴더로 주면 거기에 일곱 파일을 쓰고 proto_src/console4 는 건드리지 않는다(견주어 볼 때).
모델 호출, 시트 쓰기는 하지 않는다. 사본은 읽기만 한다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from postlife.site import console4  # noqa: E402
from postlife.site.model import load  # noqa: E402

SRC = ROOT / "proto_src" / "console4"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path, default=ROOT / "data" / "snapshot", help="사본 폴더")
    p.add_argument("--out", type=Path, default=SRC, help="쓸 폴더(기본 proto_src/console4)")
    args = p.parse_args()

    data = load(args.snapshot)
    texts = console4.export_texts(data, SRC)
    before = {n: (args.out / n).read_text(encoding="utf-8") if (args.out / n).exists() else None for n in console4.FILES}
    console4.write_texts(texts, args.out)
    for name in console4.FILES:
        size = len(texts[name].encode("utf-8"))
        state = "새 파일" if before[name] is None else ("같음" if before[name] == texts[name] else "바뀜")
        print(f"{args.out / name}: {size:,}바이트 ({state})")
    sales = json.loads(texts["sales.json"])
    d = json.loads(texts["d.json"])
    print(f"자료 시각 {data.meta.get('snapshot_at')}, 기준 종형 {len(sales['기준종형'])}개, 포인트 {len(sales['포인트'])}개, "
          f"D 종형 {len(d['variants'])}개")
    if args.out.resolve() == SRC.resolve():
        print("다음: python proto_src/console4/build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
