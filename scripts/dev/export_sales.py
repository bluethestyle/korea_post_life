"""사본(data/snapshot)으로 영업 인사이트 화면(시안)이 읽을 JSON을 만든다(src/postlife/site/sales.py의 export).

담는 것: 자료 시각, 고지 문구, 기준 종형 목록, 종형별(맞붙는 종형, 범위, 포인트, 뺀 포인트, 단정 주의 목록, 개정 검토 목록,
치료 여정 격자, 보류 요약, 브리핑 다섯 줄), 고객군 지도 세 장(성별 남, 갱신 거르개 전체, 갱신, 비갱신), 지도와 관문 탭의 고정
주석(글과 출처), 한도 표, 개정 변동 요약, 시장 소식 요약. 포인트는 한 번만 싣고 포인트ID로 가리키며, 되풀이되는 머리말은 "글" 목록의
번호로 가리킨다.

쓰기: .venv/bin/python scripts/dev/export_sales.py [--snapshot data/snapshot] --out <파일> [--pretty]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from postlife.site import sales as S  # noqa: E402
from postlife.site.model import load  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path, default=ROOT / "data" / "snapshot", help="사본 폴더")
    p.add_argument("--out", type=Path, required=True, help="쓸 JSON 파일")
    p.add_argument("--pretty", action="store_true", help="들여 써서 쓴다(크기가 커진다)")
    args = p.parse_args()

    data = load(args.snapshot)
    out = S.export(data)
    text = json.dumps(out, ensure_ascii=False, indent=1 if args.pretty else None,
                      separators=None if args.pretty else (",", ":"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    size = len(text.encode("utf-8"))
    print(f"{args.out}: {size:,}바이트({size / 1024:.0f}KB), 기준 종형 {len(out['기준종형'])}개, 포인트 {len(out['포인트'])}개, "
          f"글 {len(out['글'])}개")
    print("최상위 열쇠: " + ", ".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
