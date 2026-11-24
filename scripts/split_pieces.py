"""급부 표 조각 파일(tables.write_riders의 결과)을 판독 묶음으로 나눈다. 초기 적재의 두 판독에 쓴다.

묶음은 쪽이 이어지는 10쪽 안팎이고, 특약(조각) 하나가 두 묶음에 갈리지 않는다. 조각 하나가 10쪽을 넘으면 그 조각만으로
묶음 하나다. 걸러 낸 조각 사이에 쪽이 비면(앞 조각의 끝쪽 다음 쪽보다 뒤에서 시작하면) 새 묶음을 연다.
묶음 파일에는 판독자가 볼 것만 담는다: 번호, 쪽, 특약명, 세부보장명, 지급사유와 지급금액 칸의 글자, 그 특약에 걸린 주석.
번호는 원래 조각 파일의 순번을 그대로 쓴다(R012-3). 형이 있는 문서는 조각마다 형도 적는다. 한 칸을 쓰는 특약 이름이
여럿이면 특약명들을, 한 조각 안에 이름이 같은 세부보장이 여럿이면 그 줄에 "이름같은줄": true를 적는다(판독자가 대상을
적을 줄).

한 급부 표 안에 종별 값이 함께 있는 요약서(삼성생명)는 --kind로 읽을 종("2종")을 준다. 조각의 적용범위가 그 종을 포함하지
않으면 조각을 통째로 빼고, 세부보장의 적용범위(없으면 지급사유 칸의 "[1/3종(…)]" 같은 종 표시)가 그 종을 포함하지 않는 줄을
뺀다(reader_rows.for_kind와 같은 규칙. 급부 적재도 같은 줄만 쓴다). 남은 줄의 번호는 원래 차례 그대로이고, 묶음 파일에
"읽을종"을 적는다. 뺀 조각과 줄의 수는 화면과 색인 파일에 낸다. --kind가 없으면 묶음은 이 기능이 생기기 전과 같다.

조각에는 공시 문서의 원문 글자가 들어 있으므로 묶음 파일은 리포 밖(임시 폴더)에 쓴다.

  python scripts/split_pieces.py 조각.json --out 묶음폴더 [--name 6AFLT] [--pages 10] [--segment 통합간편심사형 --segment 공통] [--pdf 요약서.pdf]
  python scripts/split_pieces.py 조각.json --out 묶음폴더 --name LP0842003AB01V10A01 --kind 2종 --pdf /절대경로/요약서.pdf
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.extract import reader_rows as RR  # noqa: E402


def groups(pieces: Sequence[dict[str, Any]], pages: int) -> list[list[tuple[int, dict[str, Any]]]]:
    """조각을 묶음 [(순번, 조각)]들로 나눈다. pieces의 조각마다 원래 순번이 _index 칸에 붙어 있다."""
    out: list[list[tuple[int, dict[str, Any]]]] = []
    current: list[tuple[int, dict[str, Any]]] = []
    start = last = 0
    for p in pieces:
        first, end = int(p["첫쪽"]), int(p["끝쪽"])
        gap = current and first > last + 1
        too_long = current and end - start + 1 > pages
        if gap or too_long:
            out.append(current)
            current = []
        if not current:
            start = first
        current.append((p["_index"], p))
        last = max(last, end) if len(current) > 1 else end
    if current:
        out.append(current)
    return out


def _covers(p: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    """조각의 세부보장 [(원래 순번, 세부보장)]. 읽을 종으로 걸렀으면 남은 줄만."""
    return p["_covers"] if "_covers" in p else list(enumerate(p["세부보장"], 1))


def bundle(name: str, number: int, members: list[tuple[int, dict[str, Any]]], notes: Sequence[dict[str, Any]],
           source: str, pdf: str | None, kind: str | None = None) -> dict[str, Any]:
    pieces = []
    for i, p in members:
        item: dict[str, Any] = {"조각번호": f"R{i:03d}", "쪽": [int(p["첫쪽"]), int(p["끝쪽"])], "특약명": p["특별약관"]}
        if len(p.get("특약명들") or []) > 1:
            item["특약명들"] = list(p["특약명들"])     # 본형, 추가형, 갱신형처럼 이름만 다른 특약 여럿이 한 칸을 쓴다
        if p.get("형"):
            item["형"] = p["형"]
        if kind and p.get("적용범위"):
            item["적용범위"] = p["적용범위"]          # 특약명 끝의 종 표시("1,2,3종")
        attached = RR.note_owners(p, notes)
        if attached:
            item["주석"] = attached
        item["세부보장"] = []
        covers = _covers(p)
        names = Counter(RR._squash(c["보장명"]) for _, c in covers)
        for j, c in covers:
            cover = {"번호": RR.number(i, j), "쪽": int(c["쪽"]), "세부보장명": c["보장명"],
                     "지급사유": c["지급사유"], "지급금액": c["지급금액"]}
            if c.get("적용범위"):
                cover["적용범위"] = c["적용범위"]
            if names[RR._squash(c["보장명"])] > 1:
                cover["이름같은줄"] = True                 # 판독자가 "대상"을 적어야 하는 줄
            item["세부보장"].append(cover)
        pieces.append(item)
    out: dict[str, Any] = {
        "형식": RR.BUNDLE_FORMAT,
        "묶음": f"{name}_B{number:02d}",
        "문서": source,
        "쪽": [min(int(p["첫쪽"]) for _, p in members), max(int(p["끝쪽"]) for _, p in members)],
        "조각수": len(members),
        "세부보장수": sum(len(_covers(p)) for _, p in members),
    }
    if kind:
        out["읽을종"] = kind
    if pdf:
        out["PDF"] = pdf
    out["조각"] = pieces
    return out


class Dropped:
    """읽을 종이 아니어서 묶음에서 뺀 것. (시험이 이 스크립트를 sys.modules 밖에서 불러 dataclass를 쓰지 않는다)"""

    def __init__(self) -> None:
        self.pieces: list[str] = []     # 통째로 뺀 조각 번호(R012)
        self.covers: list[str] = []     # 뺀 세부보장 번호(통째로 뺀 조각의 줄 포함)


def split(data: dict[str, Any], name: str, pages: int = 10, segments: Sequence[str] = (),
          pdf: str | None = None, kind: str | None = None, dropped: Dropped | None = None) -> list[dict[str, Any]]:
    """kind(읽을 종, "2종")를 주면 그 종이 아닌 조각과 줄을 빼고(reader_rows.for_kind) dropped에 적는다."""
    if data.get("형식") != RR.PIECES_FORMAT:
        raise ValueError("급부 표 조각 파일이 아닙니다")
    dropped = dropped if dropped is not None else Dropped()
    kept: set[str] | None = None
    if kind:
        views = [v for v in RR.load_pieces(data) if not segments or v.segment in segments]
        left, out_covers, out_pieces = RR.for_kind(views, kind)
        kept = {c.number for p in left for c in p.covers}
        dropped.pieces += [f"R{i:03d}" for i in out_pieces]
        dropped.covers += out_covers
    chosen = []
    for i, p in enumerate(data["조각"], 1):
        if segments and (p.get("형") or "") not in segments:
            continue
        if kept is not None:
            covers = [(j, c) for j, c in enumerate(p["세부보장"], 1) if RR.number(i, j) in kept]
            if not covers:
                continue
            p = {**p, "_covers": covers}
        chosen.append({**p, "_index": i})
    source = (data.get("출처") or {}).get("문서", "")
    return [bundle(name, n, members, data.get("주석") or [], source, pdf, kind)
            for n, members in enumerate(groups(chosen, pages), 1)]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("pieces", type=Path, help="tables.write_riders로 쓴 조각 JSON")
    p.add_argument("--out", type=Path, required=True, help="묶음 파일을 쓸 폴더(리포 밖)")
    p.add_argument("--name", help="묶음 이름 앞머리. 비우면 문서 이름의 첫 토막(공시상품코드)")
    p.add_argument("--pages", type=int, default=10, help="묶음 하나의 쪽 수 기준")
    p.add_argument("--segment", action="append", default=[], help="이 형의 조각만 담는다. 여러 번 줄 수 있다")
    p.add_argument("--pdf", help="판독자가 열 PDF의 경로. 묶음 파일에 적는다")
    p.add_argument("--kind", help='읽을 종(예: "2종"). 이 종이 아닌 조각과 세부보장을 빼고 묶음 파일에 "읽을종"을 적는다')
    args = p.parse_args(argv)

    data = json.loads(args.pieces.read_text(encoding="utf-8"))
    name = args.name or ((data.get("출처") or {}).get("문서", "") or args.pieces.stem).split("_")[0]
    dropped = Dropped()
    bundles = split(data, name, args.pages, args.segment, args.pdf, args.kind, dropped)
    args.out.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, Any]] = []
    for b in bundles:
        path = args.out / f"{b['묶음']}.json"
        path.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
        index.append({"파일": str(path), "묶음": b["묶음"], "쪽": b["쪽"], "조각수": b["조각수"], "세부보장수": b["세부보장수"]})
        print(f"{b['묶음']}  {b['쪽'][0]}~{b['쪽'][1]}쪽  조각 {b['조각수']}  세부보장 {b['세부보장수']}")
    if args.kind:
        index.append({"읽을종": args.kind, "뺀 조각": dropped.pieces, "뺀 세부보장": dropped.covers})
    (args.out / f"{name}_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"묶음 {len(bundles)}, 조각 {sum(b['조각수'] for b in bundles)}, 세부보장 {sum(b['세부보장수'] for b in bundles)}")
    if args.kind:
        print(f"읽을 종 {args.kind}: 뺀 조각 {len(dropped.pieces)}, 뺀 세부보장 {len(dropped.covers)}"
              f"(통째로 뺀 조각의 줄 포함)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
