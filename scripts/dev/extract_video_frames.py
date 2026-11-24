"""렌더링한 mp4에서 정해진 간격으로 프레임을 뽑아 JPEG로 저장한다.

발표 애니메이션(presentation_animation/)을 푸시하기 전에, 카메라가 멈추는 구간의
프레임을 직접 보고 겹침, 잘림, 작은 글자를 확인하는 데 쓴다. check_bounds는 HUD
그룹만 검사하므로 3D 객체의 잘림과 가림은 프레임으로 확인해야 한다.

    python scripts/dev/extract_video_frames.py <mp4> <출력 폴더> [--step 1.0] [--start 0] [--end 끝]

예:
    # 장면 전체를 1초 간격으로
    python scripts/dev/extract_video_frames.py \\
        media/videos/part3_decision/720p30/Part3DecisionScene.mp4 frames/part3

    # 44~53초 구간을 0.25초 간격으로
    python scripts/dev/extract_video_frames.py \\
        media/videos/part3_decision/720p30/Part3DecisionScene.mp4 frames/part3_fine \\
        --step 0.25 --start 44 --end 53

- 파일 이름은 t_<초>.jpg(예: t_050.0.jpg, t_044.25.jpg)이다.
- PyAV(`av`)가 필요하다. Manim을 설치한 가상환경에는 함께 설치되어 있다.
- 뽑은 프레임은 저장소에 커밋하지 않는다. 출력 폴더는 저장소 밖이나 gitignore 대상 폴더로 잡는다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def frame_name(t: float) -> str:
    whole = int(t)
    frac = round(t - whole, 2)
    if abs(frac * 10 - round(frac * 10)) < 1e-6:
        return f"t_{t:05.1f}.jpg"
    return f"t_{t:06.2f}.jpg"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="mp4에서 정해진 간격으로 프레임을 뽑아 JPEG로 저장")
    ap.add_argument("mp4", type=Path, help="렌더링한 mp4 경로")
    ap.add_argument("out", type=Path, help="프레임을 저장할 폴더(없으면 만든다)")
    ap.add_argument("--step", type=float, default=1.0, help="간격(초), 기본 1.0")
    ap.add_argument("--start", type=float, default=0.0, help="시작 시각(초), 기본 0")
    ap.add_argument("--end", type=float, default=None, help="끝 시각(초), 기본은 영상 끝")
    ap.add_argument("--quality", type=int, default=90, help="JPEG 품질, 기본 90")
    a = ap.parse_args(argv)

    if a.step <= 0:
        ap.error("--step은 0보다 커야 합니다")
    if not a.mp4.is_file():
        ap.error(f"mp4 파일이 없습니다: {a.mp4}")
    try:
        import av
    except ImportError:
        print("PyAV(av)가 없습니다. Manim을 설치한 가상환경의 python으로 실행하세요.", file=sys.stderr)
        return 2

    a.out.mkdir(parents=True, exist_ok=True)
    with av.open(str(a.mp4)) as c:
        st = c.streams.video[0]
        if st.duration is not None:
            dur = float(st.duration * st.time_base)
        else:
            dur = float(c.duration) / 1e6
        end = dur if a.end is None else min(a.end, dur)
        if a.start > end:
            ap.error(f"시작 시각({a.start})이 끝 시각({end:.2f})보다 늦습니다")

        targets: list[float] = []
        k = 0
        while True:
            t = round(a.start + k * a.step, 3)
            if t > end + 1e-9:
                break
            targets.append(t)
            k += 1

        idx = saved = 0
        for fr in c.decode(st):
            if fr.pts is None:
                continue
            ts = float(fr.pts * st.time_base)
            while idx < len(targets) and ts + 1e-6 >= targets[idx]:
                fr.to_image().save(a.out / frame_name(targets[idx]), quality=a.quality)
                idx += 1
                saved += 1
            if idx >= len(targets):
                break

    print(f"저장 {saved}장, 영상 길이 {dur:.2f}초, 구간 {a.start:g}~{end:.2f}초, 간격 {a.step:g}초 -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
