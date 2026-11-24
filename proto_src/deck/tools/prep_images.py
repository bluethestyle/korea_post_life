"""캡처한 PNG 를 덱에 넣을 JPEG(폭 1600px)로 줄인다.

실행(Pillow 가 든 파이썬):
    python tools/prep_images.py <PNG 폴더> <assets 폴더>

PNG 폴더의 first, market, cover, graph 네 장을 assets/<이름>.jpg 로 쓴다.
build.py 는 assets 의 JPEG 만 읽으므로, 사진을 갈아 끼울 때는 이 스크립트만 다시 돌린다.
"""
import sys
from pathlib import Path

from PIL import Image

NAMES = ("first", "market", "cover", "graph")
WIDTH = 1600


def main(src: str, dst: str) -> None:
    src_dir, dst_dir = Path(src), Path(dst)
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        img = Image.open(src_dir / f"{name}.png").convert("RGB")
        height = round(img.height * WIDTH / img.width)
        img = img.resize((WIDTH, height), Image.LANCZOS)
        out = dst_dir / f"{name}.jpg"
        img.save(out, "JPEG", quality=84, optimize=True, progressive=False)
        print(out, out.stat().st_size)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
