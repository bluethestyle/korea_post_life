"""재추출 결과(extract.json)를 재추출 전 스냅샷(data/snapshot)과 견준다.

재추출은 모델이 급부 이름을 조금씩 다르게 적어 급부ID가 바뀌고, 다시 뽑기의 마지막 단계가 실패하면 맞던 줄이 빠진다.
그래서 ID가 아니라 내용(특약, 지급액, 첫 감액, 면책)으로 잃은 줄과 얻은 줄을 센다. 스냅샷을 갱신하기 전에 돌린다.
비교 기준과 "같은 급부"의 기준은 추출 배치(extract/job.py)가 쓰는 src/postlife/extract/rerun.py와 같다.

쓰기: python3 scripts/dev/compare_rerun.py <Actions 결과물 extract.json> <기관 머리글자: EPOST 또는 HANWHALIFE> [--snapshot <폴더>]
--snapshot은 재추출 전 sys_급부.jsonl, sys_특약.jsonl이 든 폴더(기본 data/snapshot). 잃은 줄과 얻은 줄 목록은 <extract.json>.diff.json 에 남는다.
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from postlife.extract import rerun  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("result", type=Path, help="extract_product.py --result로 남긴 extract.json")
    p.add_argument("org", help="기관 머리글자 (EPOST, HANWHALIFE)")
    p.add_argument("--snapshot", type=Path, default=ROOT / "data/snapshot", help="재추출 전 스냅샷 폴더")
    args = p.parse_args()

    res = json.loads(args.result.read_text(encoding="utf-8"))
    new, newr = res["rows"]["sys_급부"], res["rows"]["sys_특약"]
    old = [r for r in read_jsonl(args.snapshot / "sys_급부.jsonl") if r["급부ID"].startswith(args.org)]
    oldr = [r for r in read_jsonl(args.snapshot / "sys_특약.jsonl")
            if r["특약ID"].startswith(args.org) or r["종형ID"].startswith(args.org)]
    num = lambda v: None if v in (None, "") else float(v)

    print("특약", len(oldr), "→", len(newr), "| 사라진 특약ID", len({r["특약ID"] for r in oldr} - {r["특약ID"] for r in newr}),
          "새 특약ID", len({r["특약ID"] for r in newr} - {r["특약ID"] for r in oldr}))
    print("급부", len(old), "→", len(new), "| ID 기준 사라짐", len({r["급부ID"] for r in old} - {r["급부ID"] for r in new}),
          "새로", len({r["급부ID"] for r in new} - {r["급부ID"] for r in old}))
    linked = rerun.inherit_ids(old, new)
    print("같은 급부로 이전 급부ID를 이을 수 있는 줄", len(linked.pairs), "| 그 가운데 급부역할이 바뀐 줄", len(linked.roles))
    lost, gained = rerun.content_diff(old, new)
    print("내용(특약, 지급액, 첫 감액, 면책) 기준 잃은 줄", sum(lost.values()), "얻은 줄", sum(gained.values()))
    lo, ga = rerun.content_diff(old, new, rerun.loose_key)
    print("특약, 지급액만 기준 잃은 줄", sum(lo.values()), "얻은 줄", sum(ga.values()))
    print("감액예외 채워진 줄", sum(1 for r in new if r.get("감액예외")),
          "| 면책>0", sum(1 for r in old if num(r.get("면책기간일수"))), "→", sum(1 for r in new if num(r.get("면책기간일수"))))
    logs = res["logs"]
    print("기록", len(logs), collections.Counter(log["결과"] for log in logs),
          "| 이전 줄을 지킨 기록", sum(1 for log in logs if rerun.KEPT_ROW in str(log["사유"])),
          "| 호출 실패", collections.Counter(re.sub(r"\d+", "N", str(log["사유"])[:44])
                                         for log in logs if "호출 실패" in str(log["사유"])).most_common(6))
    print("오류", json.dumps(res.get("errors"), ensure_ascii=False)[:600])
    out = Path(str(args.result) + ".diff.json")
    out.write_text(json.dumps({"lost": [list(k) + [v] for k, v in lost.items()], "gained": [list(k) + [v] for k, v in gained.items()]},
                              ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
