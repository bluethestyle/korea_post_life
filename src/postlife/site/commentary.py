"""화면마다 붙이는 해설 글(기획 3.4)을 읽고 검사한다.

글은 data/site_text/commentary.json에 자료로 둔다. 지금은 사람이 검수한 초안이고, 나중에는 주간 배치가 모델로 다시 쓴다.
글 속 숫자는 모델이 쓰지 않는다. 숫자와 이름은 모두 {변수} 자리로 두고, 화면이 고른 조건에서 값을 계산해 끼운다(calc.js의 commentItems).

검사 규칙. 걸린 글은 버리고 경고를 남긴다(빌드는 멈추지 않는다).
- 변수 자리 밖에 아라비아 숫자가 하나라도 있는 글
- 그 화면에 허용되지 않은 변수를 쓴 글
- 짝이 맞지 않는 중괄호가 남은 글(화면에 "{…}"가 그대로 보이게 된다)

파일 꼴
{"_설명": "...", "s1": {"결론": "...", "읽는법": "...", "이유": "...", "유의점": "...", "출처": "...", "없을때": {"결론": "..."}}, ...}
화면 3만 "결론"과 "이유"가 {"우위": "...", "대등": "...", "열위": "..."}이다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "site_text" / "commentary.json"

ITEMS = ("결론", "읽는법", "이유", "유의점", "출처")
EMPTY = "없을때"
VERDICTS = ("우위", "대등", "열위")              # 화면 3: 기준 종형이 비교 종형보다 나은지
VARIANT_ITEMS = {"s3": ("결론", "이유")}         # 세 벌로 쓰는 항목

# 화면별로 쓸 수 있는 변수. 값은 화면(app.js)이 지금 고른 조건에서 계산한다. 이름을 바꾸면 app.js도 함께 바꾼다.
ALLOWED: dict[str, tuple[str, ...]] = {
    "s1": ("snapshotDate", "orgCount", "variantCount", "weekVariantCount", "trendShownCount", "onSaleCount", "waitingCount"),
    "s2": ("condLabel", "shownCount", "knownCount", "okCount", "noCondCount", "simpleCount"),
    "s3": ("condLabel", "baseLabel", "peerLabel", "baseBetterCount", "peerBetterCount", "sameCount", "mixedCount", "gapCount"),
    "s4": ("condLabel", "variantLabel", "mainAmount", "riderTotalCount", "pickedRiderCount", "stdPayoutCount", "ruleCount",
           "noLimitCount"),
    "s5": ("oldLabel", "newLabel", "newStartDate", "changedBenefitCount", "addedRiderCount", "removedRiderCount",
           "sameRiderCount"),
    "s6": ("runCount", "totalCount", "rejectedCount", "reviewCount", "reviewTargetCount", "retryAdoptedCount",
           "retryKeptCount"),
}

_SLOT = re.compile(r"\{([^{}]*)\}")
_DIGIT = re.compile(r"[0-9０-９]")


def check_text(screen: str, text: Any) -> str | None:
    """글 하나의 문제. 문제가 없으면 None."""
    if not isinstance(text, str) or not text.strip():
        return "글이 비어 있거나 글자가 아님"
    names = _SLOT.findall(text)
    bad = sorted({n for n in names if n not in ALLOWED[screen]})
    if bad:
        return "이 화면에 허용되지 않은 변수: " + ", ".join(bad)
    rest = _SLOT.sub("", text)
    if "{" in rest or "}" in rest:
        return "짝이 맞지 않는 중괄호"
    digits = _DIGIT.findall(rest)
    if digits:
        return "변수 자리 밖의 숫자: " + "".join(digits)
    return None


def clean(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """검사를 통과한 글만 남긴 해설과 경고 목록."""
    texts: dict[str, Any] = {}
    warnings: list[str] = []
    for key in raw:
        if key not in ALLOWED and not key.startswith("_"):
            warnings.append(f"해설 글: 모르는 화면 {key}는 싣지 않음")

    def keep(screen: str, where: str, text: Any) -> bool:
        problem = check_text(screen, text)
        if problem:
            warnings.append(f"해설 글 버림: {screen} {where} ({problem})")
            return False
        return True

    for screen in ALLOWED:
        entry = raw.get(screen)
        if not isinstance(entry, dict):
            warnings.append(f"해설 글: {screen} 화면의 글이 없음")
            continue
        out: dict[str, Any] = {}
        for item in ITEMS:
            if item not in entry:
                warnings.append(f"해설 글: {screen} {item} 항목이 없음")
                continue
            value = entry[item]
            if item in VARIANT_ITEMS.get(screen, ()):
                if not isinstance(value, dict):
                    warnings.append(f"해설 글 버림: {screen} {item} ({'/'.join(VERDICTS)} 세 벌이 아님)")
                    continue
                kept = {v: value[v] for v in VERDICTS if v in value and keep(screen, f"{item}.{v}", value[v])}
                for v in VERDICTS:
                    if v not in value:
                        warnings.append(f"해설 글: {screen} {item}.{v}가 없음")
                if kept:
                    out[item] = kept
            elif keep(screen, item, value):
                out[item] = value
        empty = entry.get(EMPTY)
        if isinstance(empty, dict):
            kept = {item: empty[item] for item in ITEMS if item in empty and keep(screen, f"{EMPTY}.{item}", empty[item])}
            if kept:
                out[EMPTY] = kept
        texts[screen] = out
    return texts, warnings


def load(path: Path | None = None) -> tuple[dict[str, Any], list[str]]:
    """해설 글 파일을 읽어 검사한다. 파일이 없거나 깨졌으면 빈 해설과 경고를 돌려준다(화면은 해설 없이 그린다)."""
    path = Path(path) if path else DEFAULT_PATH
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, [f"해설 글 파일이 없음: {path}"]
    except json.JSONDecodeError as error:
        return {}, [f"해설 글 파일을 읽지 못함: {path} ({error})"]
    if not isinstance(raw, dict):
        return {}, [f"해설 글 파일의 꼴이 다름: {path}"]
    return clean(raw)
