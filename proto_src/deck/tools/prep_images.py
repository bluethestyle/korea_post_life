"""PNG 를 덱에 넣을 JPEG(폭 1600px, 장당 250KB 이하)로 줄인다.

실행(Pillow 가 든 파이썬):
    python tools/prep_images.py <PNG 폴더> <assets 폴더> [이름 ...]

이름을 주지 않으면 PNG 폴더의 *.png 를 모두 assets/<이름>.jpg 로 쓴다. 화면 캡처는 tools/capture_app.py 가 바로 JPEG 로
쓰므로, 이 스크립트는 영상 정지 화면처럼 다른 곳에서 만든 PNG 를 넣을 때 쓴다. build.py 는 장이 부른 JPEG 만 심는다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_app import save_jpeg  # noqa: E402


def main(src: str, dst: str, names: list[str]) -> None:
    src_dir, dst_dir = Path(src), Path(dst)
    dst_dir.mkdir(parents=True, exist_ok=True)
    files = [src_dir / f"{n}.png" for n in names] if names else sorted(src_dir.glob("*.png"))
    for f in files:
        size = save_jpeg(f.read_bytes(), dst_dir / f"{f.stem}.jpg")
        print(dst_dir / f"{f.stem}.jpg", f"{size:,} 바이트")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
