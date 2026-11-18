"""sys_작업로그에 쌓는 행을 만든다. 모든 단계의 통과·반려·보류를 남겨 화면 6에 공개한다."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from . import ids


class WorkLog:
    def __init__(self, now: datetime, tab: str):
        self.stamp = now.isoformat(timespec="seconds")
        self.tab = tab
        self.rows: list[dict[str, Any]] = []

    def add(self, step: str, target: str, result: str, reason: str = "", model: str = "",
            prob: float | None = None, column: str = "", before: str = "", after: str = "") -> None:
        self.rows.append({
            "로그ID": f"LOG_{ids.short_hash(self.stamp, self.tab, step, target, str(len(self.rows)), length=14)}",
            "실행일시": self.stamp,
            "작업단계": step,
            "대상탭": self.tab,
            "대상행ID": target,
            "대상열": column or None,
            "변경전값": before or None,
            "변경후값": after or None,
            "호출모델": model or None,
            "판정확률": None if prob is None else round(prob, 4),
            "결과": result,
            "사유": (reason or None) and reason[:400],
        })
