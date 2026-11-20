"""화면 6: AI 작업 내역. sys_작업로그를 집계하고 대상행ID를 사람이 읽는 이름으로 풀어 준다."""
from __future__ import annotations

from typing import Any

from .model import Data, MAIN_KIND, REVIEW_STEP, _blank

# 화면은 열 이름(cols)으로 칸을 찾는다. 비어 있을 때가 많은 열을 뒤에 두고, 줄 끝의 빈 값(None)은 싣지 않는다(_trim).
# 작업 기록이 만여 줄이라 줄마다 null을 대여섯 개씩 적으면 그것만 200KB쯤 된다. 화면은 없는 칸을 null로 읽는다(app.js 화면 6의 cell)
COLUMNS = ["실행일시", "작업단계", "대상탭", "대상행ID", "결과", "사유", "호출모델", "대상열", "판정확률", "변경전값", "변경후값"]
RESULTS = ["통과", "반려", "보류"]
RETRY_STEP = "재추출"
STEP_ORDER = ["추출", "코드대조", "판정", RETRY_STEP, REVIEW_STEP]   # 검증 흐름의 순서 (기획 6.2)


def target_label(data: Data, target: str) -> str | None:
    """대상행ID가 가리키는 행의 이름. 사본에 없는 ID면 None."""
    if target in data.benefits:
        b = data.benefits[target]
        rider = data.riders.get(b["특약ID"], {})
        return " · ".join([_variant(data, rider.get("종형ID")), str(rider.get("원시특약명")), str(b["원시급부명"])])
    if target in data.riders:
        r = data.riders[target]
        return " · ".join([_variant(data, r["종형ID"]), str(r["원시특약명"])])
    if target in data.conditions:
        c = data.conditions[target]
        rider = data.riders.get(c.get("특약ID")) if not _blank(c.get("특약ID")) else None
        return " · ".join([_variant(data, c["종형ID"]), str(rider["원시특약명"]) if rider else MAIN_KIND,
                           f"{c['최저가입나이']}~{c['최고가입나이']}세", f"{c['보험기간구분']} {c['납입기간구분']}"])
    if target in data.variants:
        return _variant(data, target)
    for rule in data.tables.get("sys_결합제약", []):
        if rule["제약ID"] == target:
            rider = data.riders.get(rule["대상특약ID"], {})
            return " · ".join([_variant(data, rule["종형ID"]), str(rule["제약유형"]), str(rider.get("원시특약명"))])
    for t in data.trends:
        if t["동향ID"] == target:
            return " · ".join([data.org_name(t["기관코드"]), str(t["분류유형"]), str(t["발표일자"])])
    return None


def _trim(values: list[Any]) -> list[Any]:
    """줄 끝의 None을 떼어 낸다. 가운데의 None은 칸 자리를 지키도록 그대로 둔다."""
    end = len(values)
    while end and values[end - 1] is None:
        end -= 1
    return values[:end]


def _variant(data: Data, vid: str | None) -> str:
    v = data.variants.get(vid)
    return str(v["공시상품명"]) if v else str(vid)


def review_status(data: Data, row: dict) -> str:
    """사람 검토로 넘긴 기록이 지금 사본에서 어떤 상태인지."""
    tab, target = row.get("대상탭"), row.get("대상행ID")
    if tab == "sys_급부":
        if target not in data.benefits:
            return "지금 사본에 없는 행"
        return "검토 대기" if target in data.pending_benefit else "나중 실행에서 다시 판정됨"
    if tab == "sys_가입조건":
        if target not in data.conditions:
            return "지금 사본에 없는 행"
        return "검토 대기" if target in data.pending_condition else "나중 실행에서 다시 판정됨"
    if tab == "hum_담보매핑":
        m = data.mapping.get(target)
        return f"매핑 {m['검토상태']}" if m else "지금 사본에 없는 행"
    if tab == "sys_시장동향":
        return "소식 후보(선별 확률이 통과 기준에 못 미침)"
    return "지금 사본에서 확인할 수 없음"


def build(data: Data) -> dict[str, Any]:
    logs = sorted(data.logs, key=lambda r: (str(r.get("실행일시")), str(r.get("로그ID"))), reverse=True)
    rows = [_trim([r.get(c) for c in COLUMNS]) for r in logs]
    labels = {}
    for r in logs:
        target = r.get("대상행ID")
        if target not in labels:
            labels[target] = target_label(data, target)

    seen = {str(r.get("작업단계")) for r in logs}
    steps = [x for x in STEP_ORDER if x in seen] + sorted(seen - set(STEP_ORDER))
    by_step = []
    for step in steps:
        counts = {res: sum(1 for r in logs if r.get("작업단계") == step and r.get("결과") == res) for res in RESULTS}
        other = sum(1 for r in logs if r.get("작업단계") == step and r.get("결과") not in RESULTS)
        by_step.append({"step": step, **counts, "other": other, "total": sum(counts.values()) + other})

    retry = [r for r in logs if r.get("작업단계") == RETRY_STEP]
    review = [i for i, r in enumerate(logs) if r.get("작업단계") == REVIEW_STEP]
    statuses = [review_status(data, logs[i]) for i in review]
    by_status: dict[str, int] = {}
    for status in statuses:
        by_status[status] = by_status.get(status, 0) + 1
    models: dict[str, int] = {}
    for r in logs:
        key = r.get("호출모델") or ""
        models[key] = models.get(key, 0) + 1

    return {
        "cols": COLUMNS, "rows": rows, "labels": {k: v for k, v in labels.items() if v},
        "summary": {
            "total": len(logs),
            "runs": len({r.get("실행일시") for r in logs}),
            "byStep": by_step,
            "retry": {"adopted": sum(1 for r in retry if r.get("결과") == "통과"),
                      "kept": sum(1 for r in retry if r.get("결과") == "반려"),
                      "failed": sum(1 for r in retry if r.get("결과") not in ("통과", "반려")),
                      "rows": [i for i, r in enumerate(logs) if r.get("작업단계") == RETRY_STEP]},
            "review": {"count": len(review), "targets": len({logs[i].get("대상행ID") for i in review}),
                       "rows": review, "status": statuses,
                       "byStatus": sorted(by_status.items(), key=lambda kv: (-kv[1], kv[0]))},
            "byModel": [{"model": m or None, "n": n} for m, n in sorted(models.items(), key=lambda kv: (-kv[1], kv[0]))],
            "tabs": sorted({str(r.get("대상탭")) for r in logs}),
            "steps": steps,
            "results": [x for x in RESULTS if any(r.get("결과") == x for r in logs)]
                       + sorted({str(r.get("결과")) for r in logs} - set(RESULTS)),
        },
    }
