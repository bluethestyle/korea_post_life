"""재추출 결과(extract.json)를 재추출 전 스냅샷(data/snapshot)과 견준다.

재추출은 모델이 급부 이름을 조금씩 다르게 적어 급부ID가 바뀌고, 다시 뽑기의 마지막 단계가 실패하면 맞던 줄이 빠진다.
그래서 ID가 아니라 내용(특약·금액·감액·면책)으로 잃은 줄과 얻은 줄을 센다. 스냅샷을 갱신하기 전에 돌린다.

쓰기: python3 scripts/dev/compare_rerun.py <Actions 결과물 extract.json> <기관 머리글자: EPOST 또는 HANWHALIFE>
잃은 줄·얻은 줄 목록은 <extract.json>.diff.json 에 남는다.
"""
import json, sys, collections, re
res = json.load(open(sys.argv[1])); org = sys.argv[2]
new = res["rows"]["sys_급부"]; newr = res["rows"]["sys_특약"]
from pathlib import Path
snap = Path(__file__).resolve().parents[2] / "data/snapshot"
old = [r for r in map(json.loads, open(f"{snap}/sys_급부.jsonl")) if r["급부ID"].startswith(org)]
oldr = [r for r in map(json.loads, open(f"{snap}/sys_특약.jsonl")) if r["특약ID"].startswith(org) or r["종형ID"].startswith(org)]
f = lambda v: None if v in (None, "") else float(v)
key = lambda r: (r["특약ID"], f(r.get("기준지급금액만원")), f(r.get("감액개월1")), f(r.get("감액지급률1")), f(r.get("면책기간일수")))
loose = lambda r: (r["특약ID"], f(r.get("기준지급금액만원")))
print("특약", len(oldr), "→", len(newr), "| 사라진 특약ID", len({r["특약ID"] for r in oldr} - {r["특약ID"] for r in newr}), "새 특약ID", len({r["특약ID"] for r in newr} - {r["특약ID"] for r in oldr}))
print("급부", len(old), "→", len(new), "| ID 기준 사라짐", len({r["급부ID"] for r in old} - {r["급부ID"] for r in new}), "새로", len({r["급부ID"] for r in new} - {r["급부ID"] for r in old}))
co, cn = collections.Counter(map(key, old)), collections.Counter(map(key, new))
lost, gained = co - cn, cn - co
print("내용(특약·금액·감액·면책) 기준 잃은 줄", sum(lost.values()), "얻은 줄", sum(gained.values()))
lo, ln = collections.Counter(map(loose, old)), collections.Counter(map(loose, new))
print("특약·금액만 기준 잃은 줄", sum((lo - ln).values()), "얻은 줄", sum((ln - lo).values()))
print("감액예외 채워진 줄", sum(1 for r in new if r.get("감액예외")), "| 면책>0", sum(1 for r in old if f(r.get("면책기간일수"))), "→", sum(1 for r in new if f(r.get("면책기간일수"))))
logs = res["logs"]
print("기록", len(logs), collections.Counter(l["결과"] for l in logs), "| 호출 실패", collections.Counter(re.sub(r"\d+", "N", str(l["사유"])[:44]) for l in logs if "호출 실패" in str(l["사유"])).most_common(6))
print("오류", json.dumps(res.get("errors"), ensure_ascii=False)[:600])
json.dump({"lost": [list(k) + [v] for k, v in lost.items()], "gained": [list(k) + [v] for k, v in gained.items()]}, open(sys.argv[1] + ".diff.json", "w"), ensure_ascii=False)
