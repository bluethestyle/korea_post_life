import json
from collections import Counter
from pathlib import Path

GOLD = Path(__file__).resolve().parents[1] / "data" / "goldset" / "epost_goldset.jsonl"
FIELDS = ["번호", "영역", "상품과종", "특약급부명", "질문", "정답", "근거문서", "쪽수", "근거문구", "검수"]


def test_goldset_shape():
    rows = [json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines() if l]
    assert len(rows) == 85 and len({r["번호"] for r in rows}) == 85
    assert all(list(r) == FIELDS and all(r[f] for f in FIELDS) for r in rows)
    assert Counter(r["영역"] for r in rows) == {"가입조건": 20, "보장금액·면책·감액": 30, "보험료": 25, "결합 제약": 10}
    # 문서에 없는 내용을 묻는 표본: 모델이 빈값으로 답하는지 보기 위함
    assert sum(r["정답"] == "문서에 없음" for r in rows) == 9
