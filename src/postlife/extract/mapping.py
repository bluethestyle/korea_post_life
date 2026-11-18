"""급부를 표준담보 사전에 잇는다 (hum_담보매핑).

판정 모델이 급부마다 사전의 표준담보 가운데 하나(또는 "해당없음")를 고르고 선택지별 확률을 돌려준다.
확률이 높으면 자동 확정하거나 대상외로 분류하고, 낮으면 담당자 검토를 기다리게 둔다.
같은 특약·같은 급부가 여러 종형에 되풀이되므로 한 번만 묻고 결과를 모든 종형의 급부에 적는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .. import config, ids
from ..gemini import GeminiError
from ..worklog import WorkLog

NONE = "해당없음"
# 자동확정 0.80은 2026-11-18 우체국 급부 105종을 직접 검토해 정한 값 (docs/progress.md). 시트의 hum_기준값이 있으면 그 값을 쓴다.
DEFAULT_THRESHOLDS = {"담보매핑_자동확정": 0.80, "담보매핑_대상외": 0.90}
BATCH = 4                      # 한 번에 묻는 급부 수. 선택지가 53개라 문항 하나가 길고, 분당 5만 토큰 한도에 걸린다


def thresholds_from(rows: list[dict[str, Any]]) -> dict[str, float]:
    out = dict(DEFAULT_THRESHOLDS)
    for r in rows:
        if r.get("기준분류") == "판정구간" and r.get("기준키") in out and r.get("수치값") is not None:
            out[r["기준키"]] = float(r["수치값"])
    return out


def criteria(dictionary: list[dict[str, Any]]) -> dict[str, str]:
    """선택지 이름 → 설명. 이름은 표준담보명 그대로여서 답을 사전 행으로 되돌릴 수 있다."""
    out = {d["표준담보명"]: f"{d['보장대분류']} > {d['보장중분류']}. 급부 종류: {d['급부유형']}"
           for d in dictionary if d.get("사용여부") is not False}
    out[NONE] = ("위 어느 것에도 해당하지 않는 급부. 사망·장해·골절·화상·깁스 보험금, 만기·건강관리자금, 암·뇌혈관·심장 밖의 "
                 "특정 질병 진단비(치매, 파킨슨병, 대상포진, 통풍 등)가 여기에 든다")
    return out


RULES = (
    "급부가 보장하는 질병·사고와 급부 종류(진단, 수술, 입원, 통원, 치료)가 모두 맞는 표준담보를 고른다. "
    "갑상선암·기타피부암·제자리암·경계성종양·대장점막내암 가운데 여럿을 한 줄로 묶어 보장하면 '유사암'이나 '소액암·유사암' 담보를 고른다. "
    "수술 1종~5종처럼 등급별로 주는 수술비는 '종별 수술비'를 고른다. 재해는 상해로 본다. "
    "뇌질환·심질환처럼 범위가 넓은 이름의 입원·수술은 뇌혈관질환·심장질환의 입원·수술 담보를 고른다. "
    "맞는 것이 없으면 해당없음을 고른다."
)


def question(benefit_name: str, options: dict[str, str]) -> dict:
    return {"type": "choice", "criteria": options,
            "instructions": f"급부 '{benefit_name}'에 가장 가까운 표준담보 하나를 고른다. {RULES}"}


@dataclass
class Pick:
    name: str | None            # 추천 표준담보명. 해당없음이면 None
    prob: float                 # 그 추천의 확률 (해당없음이 1위면 해당없음의 확률)
    none_prob: float
    state: str                  # 자동확정 / 대기 / 대상외


def decide(answer: Any, options: dict[str, str], thresholds: dict[str, float]) -> Pick:
    probs = {name: answer.prob(name) for name in options}
    none_prob = probs.pop(NONE, 0.0)
    best = max(probs, key=probs.get) if probs else None
    if none_prob >= max(probs.values(), default=0.0):
        return Pick(None, none_prob, none_prob, "대상외" if none_prob >= thresholds["담보매핑_대상외"] else "대기")
    top = probs[best]
    return Pick(best, top, none_prob, "자동확정" if top >= thresholds["담보매핑_자동확정"] else "대기")


@dataclass
class Result:
    rows: list[dict[str, Any]] = field(default_factory=list)
    logs: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    waiting: list[str] = field(default_factory=list)       # 담당자가 볼 줄


def _group_key(rider: dict[str, Any], benefit: dict[str, Any]) -> tuple[str, str]:
    return rider["특약계보키"] if rider["담보구분"] != "주계약" else "주계약", ids.normalize(benefit["원시급부명"])


def run(gemini: Any, variants: list[dict[str, Any]], riders: list[dict[str, Any]], benefits: list[dict[str, Any]],
        dictionary: list[dict[str, Any]], existing: list[dict[str, Any]], now: datetime,
        thresholds: dict[str, float] | None = None, remap: bool = False) -> Result:
    """existing: 지금 hum_담보매핑의 행. remap이 거짓이면 이미 행이 있는 급부는 다시 묻지 않는다."""
    thresholds = thresholds or dict(DEFAULT_THRESHOLDS)
    options = criteria(dictionary)
    by_name = {d["표준담보명"]: d for d in dictionary}
    product = {v["종형ID"]: v["공시상품명"] for v in variants}
    rider_of = {r["특약ID"]: r for r in riders}
    known = set() if remap else {r["급부ID"] for r in existing}
    log = WorkLog(now, "hum_담보매핑")
    result = Result()

    # 같은 특약·같은 급부는 한 번만 묻는다
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for b in benefits:
        rider = rider_of.get(b["특약ID"])
        if rider is None or b["급부ID"] in known:
            continue
        groups.setdefault(_group_key(rider, b), []).append(b)
    by_rider: dict[str, list[tuple[str, str]]] = {}
    for key in groups:
        by_rider.setdefault(key[0], []).append(key)

    picks: dict[tuple[str, str], Pick] = {}
    for rider_key, keys in by_rider.items():
        sample_rider = rider_of[groups[keys[0]][0]["특약ID"]]
        for start in range(0, len(keys), BATCH):
            chunk = keys[start:start + BATCH]
            names = [groups[k][0]["원시급부명"] for k in chunk]
            text = f"특약 이름: {sample_rider['원시특약명']}\n이 특약의 급부: " + "; ".join(names)
            questions = {f"m{i}": question(name, options) for i, name in enumerate(names)}
            try:
                answers = gemini.decide(config.MODEL_DECIDE, text, questions)
            except GeminiError as e:
                for k in chunk:
                    log.add("판정", groups[k][0]["급부ID"], "보류", f"매핑 호출 실패: {str(e)[:200]}", model=config.MODEL_DECIDE)
                continue
            for i, k in enumerate(chunk):
                if f"m{i}" in answers:
                    picks[k] = decide(answers[f"m{i}"], options, thresholds)

    for key, pick in picks.items():
        chosen = by_name.get(pick.name) if pick.name else None
        for b in groups[key]:
            rider = rider_of[b["특약ID"]]
            result.rows.append({
                "급부ID": b["급부ID"], "공시상품명": product.get(rider["종형ID"], ""), "원시특약명": rider["원시특약명"],
                "원시급부명": b["원시급부명"],
                "추천표준담보ID": chosen["표준담보ID"] if chosen else None,
                "추천표준담보명": chosen["표준담보명"] if chosen else None,
                "매핑확률": round(pick.prob, 4),
                "확정표준담보ID": chosen["표준담보ID"] if chosen and pick.state == "자동확정" else None,
                "검토상태": pick.state, "담당자메모": None,
            })
        first = groups[key][0]
        label = f"{rider_of[first['특약ID']]['원시특약명']} · {first['원시급부명']} → {pick.name or NONE}"
        if pick.state == "대기":
            log.add("판정", first["급부ID"], "보류", f"매핑 확률이 낮아 담당자 검토 대기: {label}"[:300],
                    model=config.MODEL_DECIDE, prob=pick.prob, column="추천표준담보ID")
            log.add("사람검토이관", first["급부ID"], "보류", f"{label} (같은 급부 {len(groups[key])}행)"[:300],
                    model=config.MODEL_DECIDE, prob=pick.prob, column="추천표준담보ID")
            result.waiting.append(f"- {label}: {pick.prob:.2f}")
        else:
            log.add("판정", first["급부ID"], "통과", f"{pick.state}: {label} (같은 급부 {len(groups[key])}행)"[:300],
                    model=config.MODEL_DECIDE, prob=pick.prob, column="확정표준담보ID")
    states = [r["검토상태"] for r in result.rows]
    result.logs = log.rows
    result.stats = {"물은 급부": len(picks), "행": len(states), "자동확정": states.count("자동확정"),
                    "대상외": states.count("대상외"), "대기": states.count("대기"),
                    "건너뜀(이미 있음)": sum(1 for b in benefits if b["급부ID"] in known)}
    return result
