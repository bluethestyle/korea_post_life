"""시트 정본을 저장소에 주간 사본으로 뜬다.

행 순서나 실행 시각 때문에 거짓 변경이 잡히지 않도록
기본키 오름차순, 열 이름 순서 고정의 JSON Lines로 저장하고
실행 시각은 별도 파일(meta.json)에 둔다.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .schema import TABS

KST = timezone(timedelta(hours=9))


def to_jsonl(tab_name: str, rows: list[dict[str, Any]]) -> str:
    tab = TABS[tab_name]
    ordered = sorted(rows, key=lambda r: str(r.get(tab.key)))
    lines = [
        json.dumps({c: r.get(c) for c in sorted(tab.header)}, ensure_ascii=False, sort_keys=True)
        for r in ordered
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def write_snapshot(data: dict[str, list[dict[str, Any]]], out_dir: Path, now: datetime | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, rows in data.items():
        (out_dir / f"{name}.jsonl").write_text(to_jsonl(name, rows), encoding="utf-8")
        counts[name] = len(rows)
    meta = {
        "snapshot_at": (now or datetime.now(KST)).isoformat(timespec="seconds"),
        "row_counts": counts,
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return meta


def read_snapshot(out_dir: Path) -> dict[str, list[dict[str, Any]]]:
    data = {}
    for name in TABS:
        path = out_dir / f"{name}.jsonl"
        if path.exists():
            data[name] = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l]
    return data
