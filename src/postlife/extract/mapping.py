"""급부를 표준담보 사전에 잇는다 (hum_담보매핑).

판정 모델이 급부마다 사전의 표준담보 가운데 하나(또는 "해당없음")를 고르고 선택지별 확률을 돌려준다.
확률이 높으면 자동 확정하거나 대상외로 분류하고, 낮으면 담당자 검토를 기다리게 둔다.
같은 특약·같은 급부가 여러 종형에 되풀이되므로 한 번만 묻고 결과를 모든 종형의 급부에 적는다.

다시 묻기(Remap)는 기본으로 대기 행만 다시 묻는다. 자동확정과 대상외는 고른 상태나 급부 이름으로만 다시 묻고,
담당자가 정한 행(settled)과 검토상태가 배치 값 밖인 행(protected)은 어느 경우에도 묻지도, 덮어쓰지도, 걷어내지도 않는다.
사전 seed를 시트 탭에 올리는 계획은 sync_dictionary가 세운다.
기존 상품의 초기 적재는 판정 모델을 부르지 않고 두 판독(Claude 에이전트와 제미나이)의 의견으로 매핑 행을 만든다(cross_check).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .. import config, ids
from ..gemini import GeminiError
from ..schema import TABS
from ..sheets_io import HUMAN_REVIEWED, merge_mapping
from ..validate import check_rows
from ..worklog import WorkLog

NONE = "해당없음"
# 자동확정 0.80은 2026-11-18 우체국 급부 105종을 직접 검토해 정한 값 (docs/progress.md). 시트의 hum_기준값이 있으면 그 값을 쓴다.
DEFAULT_THRESHOLDS = {"담보매핑_자동확정": 0.80, "담보매핑_대상외": 0.90}
# 한 번에 묻는 급부 수. 선택지가 87개(사전에서 쓰는 86개와 해당없음)라 문항 하나가 길고, 분당 5만 토큰 한도에 걸린다
BATCH = 4


def thresholds_from(rows: list[dict[str, Any]]) -> dict[str, float]:
    out = dict(DEFAULT_THRESHOLDS)
    for r in rows:
        if r.get("기준분류") == "판정구간" and r.get("기준키") in out and r.get("수치값") is not None:
            out[r["기준키"]] = float(r["수치값"])
    return out


def in_use(entry: dict[str, Any]) -> bool:
    """사전의 이 줄을 선택지로 쓰는지. 사용여부가 False인 줄만 뺀다(빈칸은 쓰는 담보로 본다)."""
    return entry.get("사용여부") is not False


def criteria(dictionary: list[dict[str, Any]]) -> dict[str, str]:
    """선택지 이름 → 설명. 이름은 표준담보명 그대로여서 답을 사전 행으로 되돌릴 수 있다."""
    out = {d["표준담보명"]: f"{d['보장대분류']} > {d['보장중분류']}. 급부 종류: {d['급부유형']}"
           for d in dictionary if in_use(d)}
    out[NONE] = ("위 어느 것에도 해당하지 않는 급부. 사망·장해·골절·화상·깁스 보험금, 만기·건강관리자금, 검사비와 특정시술·수혈 급부, 암·뇌혈관·심장 밖의 "
                 "특정 질병 진단비(치매, 파킨슨병, 대상포진, 통풍 등)가 여기에 든다")
    return out


# 다섯째 문장부터는 사전 확장(docs/proposals/표준담보사전_확장안.md 13절)의 초안 15개를 순서대로 옮겼다. 초안끼리나 앞쪽
# 문장과 어긋나는 곳은 확장안 9절의 정한 값을 따랐다: 종별 수술비는 질병을 가리지 않는 급부로 좁히고, "뇌질환·심질환"은
# 뇌·심장을 함께 보장하는 급부와 헷갈리지 않게 "뇌질환이나 심질환"으로 바꿨다. 중환자실 정액은 뇌·심장 특약 안이면
# 주요치료비(9절 9번), 질병과 재해를 함께 보장하는 급부는 질병과 상해 담보 사이에서 갈릴 때만 질병 쪽(9절 4번)이다.
# 2026-11-20에 첫 실행(새 급부 518줄) 결과를 원문과 대조해 검토한 뒤 일곱 군데를 고치거나 더했다: 유사암 문장을 진단비와
# 수술비로 좁히고 치료 급부와 통합 담보를 고르는 조건을 적음, 로봇수술, 혈전제거술(주요치료비 문장에서도 뺌), 재활치료의
# 지급 방식 판단, 검사와 특정시술과 수혈과 자궁적출은 해당없음, 간병인 사용 입원일당. 근거는 docs/progress.md
# "매핑 결과 검토와 규칙 손질 (2026-11-20)".
# 'N대 특정암 진단비'부터 '간병인비용 지원금'까지의 문장은 2026-11-23 사전 추가(docs/proposals/표준담보_추가안_20261123.md)의
# 새 담보 10개와 기존 담보를 가르는 기준이다. 보류한 4기 암, 여러 질병을 묶은 뇌·심장 진단비, 두 번째 뇌출혈은 해당없음으로 보낸다.
# 따옴표 안에는 선택지 이름(표준담보명)을 그대로 쓴다. 뇌·심장질환 담보처럼 여러 담보를 묶어 부를 때는 따옴표를 붙이지 않는다.
RULES = (
    "급부가 보장하는 질병·사고와 급부 종류(진단, 수술, 입원, 통원, 치료)가 모두 맞는 표준담보를 고른다. "
    "갑상선암, 기타피부암, 제자리암, 경계성종양, 대장점막내암 가운데 여럿을 한 줄로 묶어 보장하는 진단비와 수술비는 "
    "'유사암 진단비(통합)'이나 '소액암·유사암 수술비'를 고른다. 이런 암만 보장하는 항암방사선치료, 항암약물치료, 주요치료, "
    "중환자실 치료 급부는 하나만 보장하든 여럿을 묶든 같은 치료의 암 담보('항암방사선치료비', '항암약물치료비', '암 주요치료비', "
    "'암 중환자실 치료비')를 고른다. 한 급부가 항암약물치료와 항암방사선치료 가운데 어느 것을 받아도 주면 "
    "'항암방사선·약물치료비(통합)'을 고르고, 하나만 주면 급여와 비급여, 주사제와 주사제 외 구분과 관계없이 '항암약물치료비'나 "
    "'항암방사선치료비'를 고른다. 표적항암약물과 면역항암약물의 허가치료는 그 허가치료비 담보를 고른다. "
    "다빈치 같은 로봇수술에 주는 암 급부는 갑상선암이나 전립선암 하나에 한정해도 '암 로봇수술비'를 고른다. "
    "질병을 가리지 않고 수술 1종~5종처럼 등급별로 주는 수술비는 '종별 수술비(최고 종 기준)'를 고른다. 재해는 상해로 본다. "
    "뇌질환이나 심질환처럼 범위가 넓은 이름의 입원·수술은 뇌혈관질환·심장질환의 입원·수술 담보를 고른다. "
    "뇌혈관질환과 심장질환(특정순환계질환, 2대주요기관질병, 뇌심혈관, 주요순환계질환 포함)을 한 급부로 함께 보장하면 "
    "뇌·심장질환 담보를 고른다. 한쪽만 보장하면 뇌혈관질환이나 심장질환 담보를 고른다. 재활치료, 혈전제거술, "
    "스텐트삽입술과 풍선혈관성형술, 항응고제와 항혈소판제 약물치료는 한쪽만 보장해도 뇌·심장질환 담보를 고른다. "
    "혈전제거술에 주는 급부는 이름에 수술자금이 붙어도, 연간 1회 정액으로 주어도, 뇌혈관질환이나 심장질환 한쪽만 보장해도 "
    "'뇌·심장질환 혈전제거술 치료비'를 고른다. "
    "뇌·심장 특약 안에서 혈전제거술 밖의 수술이나 중환자실 치료를 연간 정액으로 주는 급부는 '뇌·심장질환 주요치료비'를 고른다. "
    "관혈수술비와 비관혈수술비로 나뉜 뇌·심장 수술 특약은 '뇌·심장질환 수술비'를 고른다. "
    "연간 치료 횟수가 2회 이상, 3회 이상처럼 정해진 횟수를 넘어야 주는 복합치료 급부는 암이든 뇌·심장이든 해당없음을 고른다. "
    "뇌·심장 재활치료를 입원이나 통원(외래) 1일당 주면 '뇌·심장질환 재활치료비'를 고른다. 급부 이름이나 특약 이름에 진단 후 "
    "연간 1회처럼 정액으로 준다는 말이 있을 때만 해당없음을 고른다. 이름에 지급 방식이 없는 뇌·심장 입원, 외래 재활치료 급부는 "
    "1일당 주는 급부로 본다. 암이나 상해의 재활치료는 해당없음을 고른다. "
    "중환자실 급부는 입원 1일당 주면 '중환자실 입원일당'을 고른다. 연간 1회처럼 정액으로 주는 급부는 암에만 주면 "
    "'암 중환자실 치료비', 뇌·심장 특약 안의 것은 '뇌·심장질환 주요치료비', 그 밖이면 '중환자실 치료비'를 고른다. "
    "암 급부가 수술, 방사선, 약물치료, 중환자실 치료 가운데 하나를 받으면 주는 꼴이면 '암 주요치료비'를 고른다. "
    "에크모, 인공호흡기, 저체온요법, 지속적신대체요법처럼 중환자 특수처치에 주는 급부는 해당없음을 고른다. "
    "CT, MRI, PET, 유전자 패널검사, 암 주요검사처럼 검사를 받으면 주는 급부, 도수정복술, 신경차단술, 흡인과 천자와 절개, "
    "화상처치처럼 특정시술에 주는 급부, 특정수혈에 주는 급부, 암 통합치료 특약의 통증완화치료, 다학제 통합진료, 항구토제 처방 "
    "급부는 특약이 보장하는 질병과 관계없이 해당없음을 고른다. 창상봉합술은 '창상봉합술 치료비'를 고른다. "
    "자궁적출수술에 주는 급부는 해당없음을 고른다. "
    "간병인을 쓴 날 1일당 주는 입원 급부는 이름이 간병인지원금이나 간병인지원급여금이어도, 요양병원 여부, 특정 경증상병 제외 "
    "여부, 질병과 재해 구분과 관계없이 '간병인 사용 입원일당'을 고른다. "
    "1인실이나 2~3인실 조건이 붙은 입원일당은 병원 등급과 질병, 상해 구분과 관계없이 '1인실 입원일당'이나 "
    "'2~3인실 입원일당'을 고른다. '상급종합병원 입원일당'은 병실 조건이 없는 급부에만 쓴다. "
    "척추질환, 관절염처럼 특정 질병이나 특정 수술에 한정된 수술비는 1종~5종이나 관혈, 비관혈로 나뉘어 있어도 그 수술비를 "
    "고른다. 인공디스크 치환수술은 '척추질환 수술비'를 고른다. '종별 수술비(최고 종 기준)'는 질병을 가리지 않는 급부에만 쓴다. "
    "상해로 인한 척추손상 수술비는 '척추질환 수술비'가 아니다. "
    "전신마취를 하고 마취 시간이 정해진 시간 이상인 수술에 주는 급부는 질병과 재해, 병원 등급, 마취 시간 구간과 관계없이 "
    "'전신마취 수술비'를 고른다. 전신마취를 동반한 수혈에 주는 급부는 '전신마취 수술비'를 고르지 않는다. "
    "암을 부위 묶음마다 따로 진단비로 주면 부위 묶음 수와 관계없이 '통합암(전이 포함) 진단비'를 고른다. "
    "뇌혈관질환이나 심장질환 산정특례 대상이 되었을 때 주는 급부는 '뇌혈관질환 산정특례 진단비'나 "
    "'심장질환 산정특례 진단비'를 고른다. 암, 희귀질환, 중증외상, 중증화상, 결핵의 산정특례 급부는 해당없음을 고른다. "
    "항암호르몬약물 허가치료는 '항암호르몬약물허가치료비'를 고른다. "
    "응급환자로 응급실에 내원했을 때 내원 1회당 주는 급부는 특정 질환에 한정해도 '응급실내원 진료비(응급)'를 고른다. "
    "응급환자 조건이 없는 응급실 내원 급부는 '응급실내원 진료비(응급)'를 고르지 않는다. "
    "항응고제나 항혈소판제의 경구약물이나 주사제 처방, 투여에 주는 급부는 '뇌·심장질환 약물치료비(항응고제·항혈소판제)'를 "
    "고른다. 혈전용해제 투여는 혈전용해치료비 담보를 고른다. "
    "질병과 재해를 한 급부로 함께 보장하는 입원일당과 수술비가 '질병 입원일당'과 '상해 입원일당', 또는 '질병 수술비'와 "
    "'상해 수술비' 사이에서 갈리면 질병 쪽 담보를 고른다. "
    "10대 주요암, 11대 특정암, 16대 특정암처럼 정해진 여러 부위의 암을 한 묶음으로 보고 진단되면 한 번 주는 진단비는 "
    "'N대 특정암 진단비'를 고른다. 이름에 고액이 붙으면 '고액암 진단비'를, 부위 묶음마다 따로 주면 "
    "'통합암(전이 포함) 진단비'를 고른다. 한 부위의 암만 주는 진단비는 'N대 특정암 진단비'가 아니다. "
    "4기 암이나 원격전이 암으로 진단될 때만 주는 진단비는 부위 묶음으로 나뉘어 있어도 해당없음을 고른다. "
    "중증갑상선암으로 진단될 때만 주는 진단비는 '중증갑상선암 진단비'를 고른다. "
    "유방의 암이나 제자리암으로 유방 부분절제나 완전절제 수술을 받으면 주는 수술비는 '유방암 절제수술비'를 고른다. "
    "진공흡인 같은 유방 양성병변 절제에 주는 급부는 '유방암 절제수술비'가 아니다. "
    "항암방사선치료나 항암약물치료를 치료 1회당, 입원 1회당, 통원 1일당처럼 받을 때마다 주는 급부는 둘 가운데 하나만 "
    "보장해도 '항암방사선·약물치료비(치료당)'를 고른다. 최초 1회나 연간 1회 주는 급부는 앞의 항암치료 문장을 따른다. "
    "일과성뇌허혈발작이나 심근병증 하나로 진단될 때 주는 급부는 '일과성뇌허혈발작 진단비'나 '심근병증 진단비'를 고른다. "
    "6대 뇌질환, 6대 심장질환, 특정심장질환, 특정3대심장질환 진단비는 해당없음을 고른다. "
    "같은 질병으로 첫 진단을 받은 뒤 다시 발병해 진단될 때 주는 두 번째 진단비나 재진단 진단비는 급성심근경색증이면 "
    "'두 번째 급성심근경색증 진단비'를 고르고, 뇌출혈이나 뇌졸중이면 해당없음을 고른다. 첫 진단에 주는 담보를 고르지 않는다. "
    "뇌혈관질환과 심장질환 가운데 두 번째로 생긴 질병에 주는 급부는 이 문장에 들지 않는다. "
    "심장부정맥으로 고주파절제술이나 냉각절제술을 받으면 주는 급부는 이름이 치료비여도 특정시술로 보지 않고 "
    "'심장부정맥 고주파·냉각절제술 수술비'를 고른다. "
    "수술을 받고 입원했을 때 입원 1일당 주는 급부는 질병과 상해, 수술 종별 구분과 관계없이 '수술동반 입원일당'을 고른다. "
    "1인실이나 2~3인실 조건이 붙으면 그 병실 입원일당을, 간병인 사용 조건이 붙으면 '간병인 사용 입원일당'을, 암에 한정하면 "
    "'암 입원일당'을 고른다. "
    "입원 중 쓴 간병인비용이 정해진 금액(200만 원 이상처럼)을 넘을 때 정액으로 주는 급부는 질병과 상해, 요양병원 여부, "
    "금액 구간과 관계없이 '간병인비용 지원금'을 고른다. 간병인을 쓴 날 1일당 주는 급부는 '간병인 사용 입원일당'이다. "
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


# ---------- 다시 묻기에서 지킬 행 ----------
REMAP_STATES = ("대기", "자동확정", "대상외")      # 다시 물을 수 있는 검토상태. 이 밖의 값은 다시 묻지 않는다
DEFAULT_REMAP_STATES = frozenset({"대기"})
EXCLUDED_MARK = "대상외 확정"                   # 담당자가 대상외로 확정한 행의 담당자메모 머리말


def review_state(row: dict[str, Any]) -> str:
    """검토상태를 앞뒤 공백을 떼고 읽는다. 담당자가 시트에서 고치다 "승인 "처럼 공백이 섞여도 같은 값으로 본다.
    settled, protected, Remap.wants, prune, merge, upsert가 모두 이 값으로 견준다."""
    return str(row.get("검토상태") or "").strip()


def settled(row: dict[str, Any]) -> bool:
    """담당자가 정한 행인지. 이런 행은 어느 다시 묻기에서도 묻지 않고, 급부가 없어져도 걷어내지 않는다.

    - 검토상태가 승인, 수정, 오류인 행 (sheets_io.HUMAN_REVIEWED)
    - 검토상태가 대상외이고 담당자메모가 "대상외 확정"으로 시작하는 행. 판정 모델이 대상외로 둔 행과 가르려고 메모 머리말을
      쓴다. 배치는 담당자메모를 쓰지 않는다(옛 메모를 지킬 뿐). 검토상태를 승인으로 두고 확정표준담보ID를 비우는 방법은
      화면 1이 그 행을 확정 수에 넣으므로(site/overview.py) 쓰지 않는다.
    """
    state = review_state(row)
    if state in HUMAN_REVIEWED:
        return True
    return state == "대상외" and str(row.get("담당자메모") or "").strip().startswith(EXCLUDED_MARK)


def protected(row: dict[str, Any]) -> bool:
    """배치가 다시 묻지도, 덮어쓰지도, 걷어내지도 않는 행: 담당자가 정한 행(settled)이거나 검토상태가 배치 값(REMAP_STATES)
    밖인 행. 다시 묻기(Remap.wants), 걷어내기(prune), 합치기(merge, upsert)가 같은 기준을 쓴다."""
    return settled(row) or review_state(row) not in REMAP_STATES


@dataclass(frozen=True)
class Remap:
    """다시 묻기에서 어느 행을 다시 물을지 (scripts/map_benefits.py --remap).

    states: 이 검토상태의 행을 다시 묻는다. 기본은 대기만이다. 자동확정과 대상외는 이미 판정이 끝난 행이라 기본에서 뺀다.
    match: 원시급부명이 이 정규식에 맞는 행은 상태가 자동확정이나 대상외여도 다시 묻는다. 사전에 담보를 더해 답이
           달라질 행만 골라 다시 물을 때 쓴다(확장안 4.3의 표). hum_담보매핑 행의 원시급부명과 지금 sys_급부의
           원시급부명 가운데 어느 쪽이 맞아도 된다. 재추출 뒤 급부ID가 그대로인 급부는 ids.benefit_id가 떼는 글자(쉼표,
           가운뎃점, ~, -, 또는, 및, 공백)만 다른 옛 이름이 매핑 행에 남는다.
    담당자가 정한 행(settled)과 검토상태가 REMAP_STATES 밖인 행(protected)은 어느 경우에도 다시 묻지 않는다.
    """
    states: frozenset[str] = DEFAULT_REMAP_STATES
    match: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "states", frozenset(self.states))
        bad = set(self.states) - set(REMAP_STATES)
        if bad:
            raise ValueError(f"다시 물을 수 없는 검토상태: {', '.join(sorted(bad))} (고를 수 있는 것: {', '.join(REMAP_STATES)})")
        if self.match:
            try:
                re.compile(self.match)
            except re.error as e:          # re.error는 ValueError가 아니어서 스크립트가 안내 없이 죽었다
                raise ValueError(f"원시급부명 정규식이 틀렸습니다: {self.match!r} ({e})") from e

    def wants(self, row: dict[str, Any], benefit_name: str | None = None) -> bool:
        """row: hum_담보매핑 행. benefit_name: 같은 급부ID의 지금 sys_급부 원시급부명(있으면)."""
        if protected(row):
            return False
        if review_state(row) in self.states:
            return True
        if not self.match:
            return False
        names = [row.get("원시급부명")] + ([benefit_name] if benefit_name is not None else [])
        return any(re.search(self.match, str(n or "")) is not None for n in names)


def _remap_rule(remap: bool | Remap | None) -> Remap | None:
    if isinstance(remap, Remap):
        return remap
    return Remap() if remap else None


def without_repeats(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """같은 급부ID가 두 번 이상 나오면 한 줄만 남긴다. (남길 행, 걷어낸 행)

    탭을 다시 쓴 뒤 그 아래 옛 행을 지우지 못하면(sheets_io.RestBackend.overwrite) 같은 급부의 옛 복사본이 꼬리에 남는다.
    배치가 덮어쓰지 않는 줄(protected: 담당자가 정한 행과 검토상태가 배치 값 밖인 행)이 있으면 그 가운데 앞 줄을, 없으면
    앞 줄을 남긴다. 남긴 줄은 제자리에 둔다.
    """
    chosen: dict[str, int] = {}
    for i, row in enumerate(rows):
        bid = row["급부ID"]
        if bid not in chosen or (protected(row) and not protected(rows[chosen[bid]])):
            chosen[bid] = i
    keep = set(chosen.values())
    return [r for i, r in enumerate(rows) if i in keep], [r for i, r in enumerate(rows) if i not in keep]


def prune(existing: list[dict[str, Any]], live_ids: set[str]
          ) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]], list[dict[str, Any]]]:
    """시트에 더는 없는 급부의 매핑 행과 같은 급부ID가 두 번 나온 행을 걷어낸다.
    (남길 행, 걷어낸 수, 담당자가 정했는데 급부가 없어진 행, 걷어낸 수에 든 되풀이 행)

    급부가 없어진 행은 배치가 쓰는 상태(대기, 자동확정, 대상외)의 행만 지운다. 담당자가 정한 행(settled: 승인·수정·오류,
    "대상외 확정" 메모가 붙은 대상외)과 검토상태가 그 밖의 값인 행은 급부가 없어졌어도 지우지 않고 따로 알린다.
    같은 급부ID가 두 번 나오면 without_repeats의 규칙으로 한 줄만 남긴다.
    """
    rows, repeats = without_repeats(existing)
    kept, removed, orphans = [], len(repeats), []
    for row in rows:
        if row["급부ID"] in live_ids:
            kept.append(row)
        elif protected(row):
            kept.append(row)
            orphans.append(row)
        else:
            removed += 1
    return kept, removed, orphans, repeats


MAPPING_TAB = "hum_담보매핑"


def merge(existing: list[dict[str, Any]], proposed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """hum_담보매핑에 배치의 새 추천을 합친다. sheets_io.merge_mapping은 승인·수정·오류 행만 지키고 같은 급부ID가 두 번
    나오면 뒤 줄을 남기므로, 먼저 기존 행의 되풀이를 without_repeats로 없애고, 지금 행을 배치가 덮어쓰지 않는 급부
    (protected: 담당자가 정한 행, 검토상태가 배치 값 밖인 행)의 추천을 뺀다."""
    rows, _ = without_repeats(existing)
    keep = {r["급부ID"] for r in rows if protected(r)}
    return merge_mapping(rows, [r for r in proposed if r["급부ID"] not in keep])


def upsert(store: Any, proposed: list[dict[str, Any]]) -> int:
    """쓰기 직전에 시트의 hum_담보매핑을 다시 읽어 merge로 합쳐 쓴다(SheetStore.upsert_mapping 대신 쓴다). 매핑이 도는 동안
    담당자가 시트에서 정한 행도 지킨다. 돌려주는 값은 배치가 덮어쓰지 않는 행이라 쓰지 않은 추천 수."""
    current, _ = without_repeats(store.read([MAPPING_TAB])[MAPPING_TAB])
    held = {r["급부ID"] for r in current if protected(r)}
    store.write_tab(MAPPING_TAB, merge(current, proposed))
    return sum(1 for r in proposed if r["급부ID"] in held)


@dataclass
class Result:
    rows: list[dict[str, Any]] = field(default_factory=list)
    logs: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    waiting: list[str] = field(default_factory=list)       # 담당자가 볼 줄


def _group_key(rider: dict[str, Any], benefit: dict[str, Any]) -> tuple[str, str]:
    return rider["특약계보키"] if rider["담보구분"] != "주계약" else "주계약", ids.normalize(benefit["원시급부명"])


@dataclass
class Questions:
    """판정 모델에 물을 문항. run이 쓰고, plan이 호출 수와 입력 크기를 셀 때 쓴다."""
    options: dict[str, str]
    groups: dict[tuple[str, str], list[dict[str, Any]]]
    batches: list[tuple[str, dict[str, dict], list[tuple[str, str]]]]   # (특약 글, 문항, 그 문항의 묶음 키)
    known: set[str]                    # 매핑 행이 있어 묻지 않고 건너뛰는 급부ID
    new: int                           # 매핑 행이 없어 처음 묻는 급부 수
    reasked: Counter                   # 다시 묻는 급부의 지금 검토상태별 수
    skipped: set[str] = field(default_factory=set)     # 앞 실행이 판정해 이번에 묻지 않는 급부ID (known 밖의 것만)
    only: tuple[str, ...] = ()                         # 범위 제한 접두사. 비면 제한하지 않는다
    outside: set[str] = field(default_factory=set)     # 범위 제한 접두사에 맞지 않아 묻지 않는 급부ID


def scope_prefixes(only: Any) -> tuple[str, ...]:
    """범위 제한 접두사를 튜플로 정리한다. None이나 빈 목록이면 제한하지 않는다(빈 튜플). 빈 글자 접두사는 모든 급부ID에
    맞아 제한이 풀리므로 ValueError로 막는다."""
    prefixes = tuple(only or ())
    if any(not isinstance(p, str) or not p.strip() for p in prefixes):
        raise ValueError(f"범위 제한 접두사에 빈 값이 있습니다: {prefixes!r}")
    return tuple(p.strip() for p in prefixes)


def prepare(riders: list[dict[str, Any]], benefits: list[dict[str, Any]], dictionary: list[dict[str, Any]],
            existing: list[dict[str, Any]], remap: bool | Remap | None = False,
            skip: set[str] | None = None, only: Any = None) -> Questions:
    """물을 급부를 고르고 문항으로 묶는다. remap이 없으면 이미 행이 있는 급부는 묻지 않는다.

    skip: 이번에 묻지 않을 급부ID. 두 번에 나눠 돌릴 때 앞 실행의 결과(mapping.json의 rows)에 있는 급부를 넘긴다
    (scripts/map_benefits.py --skip-result). 입력문은 이번에 묻는 급부만 묶어 짜므로 같은 급부를 다시 물으면 함께 묶이는
    급부가 달라져 입력이 달라진다.
    only: 범위 제한 접두사 목록(scripts/map_benefits.py --only-prefix). 주면 급부ID가 이 가운데 하나로 시작하는 급부만
    처음 묻기와 다시 묻기의 대상이 된다. 범위 밖 급부는 묻지 않으므로 그 매핑 행에 대한 추천도 나오지 않는다.
    """
    rule = _remap_rule(remap)
    prefixes = scope_prefixes(only)
    options = criteria(dictionary)
    rider_of = {r["특약ID"]: r for r in riders}
    current = {r["급부ID"]: r for r in existing}
    sys_names = {b["급부ID"]: b.get("원시급부명") for b in benefits}      # 지금 sys_급부의 이름 (Remap.match)
    outside = {b["급부ID"] for b in benefits if prefixes and not b["급부ID"].startswith(prefixes)}
    known = {bid for bid, r in current.items() if rule is None or not rule.wants(r, sys_names.get(bid))}
    skipped = {b["급부ID"] for b in benefits
               if b["급부ID"] in (skip or set()) and b["급부ID"] not in known and b["급부ID"] not in outside}

    # 같은 특약·같은 급부는 한 번만 묻는다
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    new, reasked = 0, Counter()
    for b in benefits:
        rider = rider_of.get(b["특약ID"])
        if rider is None or b["급부ID"] in outside or b["급부ID"] in known or b["급부ID"] in skipped:
            continue
        groups.setdefault(_group_key(rider, b), []).append(b)
        if b["급부ID"] in current:
            reasked[current[b["급부ID"]].get("검토상태")] += 1
        else:
            new += 1
    by_rider: dict[str, list[tuple[str, str]]] = {}
    for key in groups:
        by_rider.setdefault(key[0], []).append(key)

    batches = []
    for keys in by_rider.values():
        sample_rider = rider_of[groups[keys[0]][0]["특약ID"]]
        for start in range(0, len(keys), BATCH):
            chunk = keys[start:start + BATCH]
            names = [groups[k][0]["원시급부명"] for k in chunk]
            text = f"특약 이름: {sample_rider['원시특약명']}\n이 특약의 급부: " + "; ".join(names)
            batches.append((text, {f"m{i}": question(name, options) for i, name in enumerate(names)}, chunk))
    return Questions(options, groups, batches, known, new, reasked, skipped, prefixes, outside)


def _known_inside(q: Questions, benefits: list[dict[str, Any]]) -> int:
    """이미 행이 있어 건너뛰는 급부 수. 범위 제한이 있으면 범위 안의 급부만 센다(범위 밖은 건너뜀(범위 밖)으로 센다)."""
    return sum(1 for b in benefits if b["급부ID"] in q.known and b["급부ID"] not in q.outside)


def _scope_counts(q: Questions) -> dict[str, Any]:
    """범위 제한을 주었을 때만 결과에 더하는 항목. 주지 않으면 빈 dict라 결과가 전과 같다."""
    return {"범위 제한 접두사": list(q.only), "건너뜀(범위 밖)": len(q.outside)} if q.only else {}


def plan(riders: list[dict[str, Any]], benefits: list[dict[str, Any]], dictionary: list[dict[str, Any]],
         existing: list[dict[str, Any]], remap: bool | Remap | None = False,
         skip: set[str] | None = None, only: Any = None) -> dict[str, Any]:
    """판정 모델을 부르지 않고 물을 양을 센다. 입력 글자 수는 판정 API에 보내는 본문(JSON)을 한글 그대로 센 값이다."""
    return plan_of(prepare(riders, benefits, dictionary, existing, remap, skip, only), benefits)


def plan_of(q: Questions, benefits: list[dict[str, Any]]) -> dict[str, Any]:
    """prepare가 묶은 문항으로 plan의 수를 센다. 호출 간격과 걸리는 시간 어림은 scripts/map_benefits.py가 더한다."""
    sizes = [len(json.dumps({"model": config.MODEL_DECIDE, "input": text, "questions": qs}, ensure_ascii=False))
             for text, qs, _ in q.batches]
    return {
        "선택지": len(q.options), "처음 묻는 급부": q.new, "다시 묻는 급부": dict(sorted(q.reasked.items())),
        "건너뜀(이미 있음)": _known_inside(q, benefits),
        "건너뜀(앞 실행에서 판정)": len(q.skipped),
        **_scope_counts(q),
        "문항": sum(len(qs) for _, qs, _ in q.batches), "호출": len(q.batches),
        "호출당 입력 글자 최대": max(sizes, default=0),
        "호출당 입력 글자 평균": round(sum(sizes) / len(sizes)) if sizes else 0,
        "입력 글자 합계": sum(sizes),
    }


def run(gemini: Any, variants: list[dict[str, Any]], riders: list[dict[str, Any]], benefits: list[dict[str, Any]],
        dictionary: list[dict[str, Any]], existing: list[dict[str, Any]], now: datetime,
        thresholds: dict[str, float] | None = None, remap: bool | Remap | None = False,
        skip: set[str] | None = None, only: Any = None) -> Result:
    """existing: 지금 hum_담보매핑의 행.

    remap이 거짓이면 이미 행이 있는 급부는 다시 묻지 않는다. 참이면 대기 행을 다시 묻고, Remap을 주면 그 규칙대로 고른다.
    담당자가 정한 행(settled)은 어느 경우에도 묻지 않는다. skip의 급부ID는 묻지 않는다(prepare).
    only를 주면 급부ID가 그 접두사로 시작하는 급부만 묻고, 결과 행(rows)도 그 급부만 낸다(prepare).
    호출이 실패하거나, 답에 그 문항이 없거나, 선택지 확률이 모두 0이거나 비어 있으면 그 급부는 매핑 행을 내지 않고
    "보류" 기록만 남긴다. 시트의 기존 행은 그대로 남는다.
    """
    thresholds = thresholds or dict(DEFAULT_THRESHOLDS)
    q = prepare(riders, benefits, dictionary, existing, remap, skip, only)
    by_name = {d["표준담보명"]: d for d in dictionary if in_use(d)}     # criteria가 선택지를 고르는 조건과 같다
    product = {v["종형ID"]: v["공시상품명"] for v in variants}
    rider_of = {r["특약ID"]: r for r in riders}
    log = WorkLog(now, "hum_담보매핑")
    result = Result()

    def hold(key: tuple[str, str], why: str) -> None:
        first = q.groups[key][0]
        label = f"{rider_of[first['특약ID']]['원시특약명']} · {first['원시급부명']}"
        log.add("판정", first["급부ID"], "보류", f"{why}: {label}"[:300], model=config.MODEL_DECIDE)

    picks: dict[tuple[str, str], Pick] = {}
    unanswered = 0
    for text, questions, chunk in q.batches:
        try:
            answers = gemini.decide(config.MODEL_DECIDE, text, questions)
        except GeminiError as e:
            for k in chunk:
                hold(k, f"매핑 호출 실패: {str(e)[:200]}")
            unanswered += len(chunk)
            continue
        for i, k in enumerate(chunk):
            answer = answers.get(f"m{i}")
            if answer is None:
                hold(k, "매핑 답에 이 급부의 문항이 없음")
            elif not any(answer.prob(name) > 0 for name in q.options):
                hold(k, "매핑 답의 선택지 확률이 모두 0이거나 비어 있음")
            else:
                picks[k] = decide(answer, q.options, thresholds)
                continue
            unanswered += 1

    for key, pick in picks.items():
        chosen = by_name.get(pick.name) if pick.name else None
        for b in q.groups[key]:
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
        first = q.groups[key][0]
        label = f"{rider_of[first['특약ID']]['원시특약명']} · {first['원시급부명']} → {pick.name or NONE}"
        if pick.state == "대기":
            log.add("판정", first["급부ID"], "보류", f"매핑 확률이 낮아 담당자 검토 대기: {label}"[:300],
                    model=config.MODEL_DECIDE, prob=pick.prob, column="추천표준담보ID")
            log.add("사람검토이관", first["급부ID"], "보류", f"{label} (같은 급부 {len(q.groups[key])}행)"[:300],
                    model=config.MODEL_DECIDE, prob=pick.prob, column="추천표준담보ID")
            result.waiting.append(f"- {label}: {pick.prob:.2f}")
        else:
            log.add("판정", first["급부ID"], "통과", f"{pick.state}: {label} (같은 급부 {len(q.groups[key])}행)"[:300],
                    model=config.MODEL_DECIDE, prob=pick.prob, column="확정표준담보ID")
    states = [r["검토상태"] for r in result.rows]
    result.logs = log.rows
    result.stats = {"물은 급부": len(picks), "답을 받지 못한 급부": unanswered, "행": len(states),
                    "자동확정": states.count("자동확정"), "대상외": states.count("대상외"), "대기": states.count("대기"),
                    "건너뜀(이미 있음)": _known_inside(q, benefits),
                    "건너뜀(앞 실행에서 판정)": len(q.skipped),
                    **_scope_counts(q),
                    "다시 물은 행": sum(q.reasked.values())}
    return result


# ---------- 두 판독의 교차 확인으로 매핑하기 (초기 적재) ----------
CROSS_CHECK = "교차 확인"          # 이 길로 넣은 줄의 작업 로그 호출모델. 판정 모델을 부르지 않는다
READERS = ("claude", "gemini")     # 의견 파일의 두 판독 열 이름(기본). 앞의 열이 대기 줄 추천에서 먼저다
READER_LABELS = {"claude": "Claude", "gemini": "제미나이"}    # 작업 로그에 적는 판독 이름. 없으면 열 이름 그대로
# 의견 파일을 만든 정규식과 같다. 앞 표시는 이름 맨 앞에 이어 붙은 대괄호 묶음만, 감액 표시는 이름 안 어디에 있든 모두 뗀다
_KIND_MARKS = re.compile(r"^(?:\[[^\[\]]*\])+\s*")
_KIND_REDUCTION = re.compile(r"\s*\(\s*(?:1년\s*50%|1년\s*감액|180일\s*감액)\s*\)")


def kind_name(name: Any) -> str:
    """특약이나 급부의 묶음 이름. 원시특약명이나 원시급부명에서 앞의 대괄호 표시("[갱신형]", "[간편]" 등이 이어진 것)와
    "(1년50%)", "(1년감액)", "(180일감액)" 꼴의 감액 표시를 떼고 공백을 하나로 줄인 뒤 양끝 공백을 없앤다. 다른 괄호는 남긴다.

    교차 확인 의견 파일(data/crosscheck/<회사>_mapping_opinion_2reader.jsonl)의 특약과 급부가 이 이름이고, 급부는
    (kind_name(원시특약명), kind_name(원시급부명))으로 의견을 찾는다. 급부ID를 만드는 ids와는 상관없다."""
    text = _KIND_MARKS.sub("", str(name or ""))
    text = _KIND_REDUCTION.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class CrossCheck:
    rows: list[dict[str, Any]] = field(default_factory=list)       # hum_담보매핑에 쓸 행. 지금 행과 같은 줄은 뺀다
    logs: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    by_standard: dict[str, int] = field(default_factory=dict)      # 표준담보명별 자동확정 줄 수
    unknown: list[dict[str, str]] = field(default_factory=list)    # 사전(쓰는 담보)에 없는 의견: 번호, 판독, 이름
    unused: list[str] = field(default_factory=list)                # 고른 급부에 하나도 맞지 않은 의견의 번호
    waiting: list[str] = field(default_factory=list)               # 담당자가 볼 줄


def _same_mapping_row(old: dict[str, Any], new: dict[str, Any]) -> bool:
    """담당자메모 밖의 열이 모두 같은지. 담당자메모는 merge가 지금 값을 지키므로 견주지 않는다."""
    return all(same_value(old.get(c), new.get(c)) for c in TABS[MAPPING_TAB].header if c != "담당자메모")


def cross_check(variants: list[dict[str, Any]], riders: list[dict[str, Any]], benefits: list[dict[str, Any]],
                dictionary: list[dict[str, Any]], existing: list[dict[str, Any]],
                opinions: dict[tuple[str, str], dict[str, Any]], now: datetime,
                readers: tuple[str, str] = READERS) -> CrossCheck:
    """두 판독의 의견으로 매핑 행을 만든다. 판정 모델을 부르지 않는다.

    benefits: 이번에 다룰 상품의 급부만 넘긴다. existing: 지금 hum_담보매핑 전체.
    opinions: (특약 묶음 이름, 급부 묶음 이름) → 의견 파일의 줄. 줄의 두 판독 열(readers, 기본은 "claude"와 "gemini")이
    표준담보명이나 해당없음이다. 열 이름만 바뀌고 판정 규칙은 같다.
    - 두 의견이 같은 표준담보명이면 자동확정(추천과 확정표준담보ID가 그 담보), 둘 다 해당없음이면 대상외, 그 밖이면 대기다.
      대기의 추천은 앞 판독(기본은 Claude)의 의견이 표준담보명이면 그것, 아니면 뒤 판독(제미나이)의 것, 둘 다 아니면 비운다.
    - 사전(쓰는 담보, in_use)에 없는 이름은 그 판독의 의견이 없는 것으로 보고 unknown에 적는다. 의견 파일이 새 담보가
      필요하다는 뜻으로 적는 "신규"와 모른다는 "모름"도 사전에 없는 이름이라 확정하지 않는다. 두 판독이 모두 그렇게 적어도
      의견이 없는 급부와 같다.
    - 의견이 없는 급부(두 판독 모두 쓸 의견이 없는 급부도)는 매핑 행이 없을 때만 추천 없는 대기 행을 낸다. 이미 행이 있으면
      그대로 둔다. 판정 모델이 정한 다른 급부의 줄을 의견 파일이 다루지 않았다고 대기로 되돌리지 않으려는 것이다.
    - 담당자가 정한 행과 검토상태가 배치 값 밖인 행(protected)은 건드리지 않는다. 쓰기는 merge와 upsert로 한다.
    - 지금 행과 담당자메모 밖의 열이 모두 같은 줄은 내지 않는다. 두 번 돌려도 시트가 바뀌지 않고 작업 로그도 늘지 않는다.
    매핑확률은 비운다. 작업 로그는 run과 같은 꼴(판정, 사람검토이관)로 남기고 호출모델에 CROSS_CHECK를 적는다.
    stats의 자동확정, 대상외, 대기는 지금 행과 같아 쓰지 않는 줄까지 센 판정 결과다.
    """
    by_name = {d["표준담보명"]: d for d in dictionary if in_use(d)}     # criteria가 선택지를 고르는 조건과 같다
    product = {v["종형ID"]: v["공시상품명"] for v in variants}
    rider_of = {r["특약ID"]: r for r in riders}
    current = {r["급부ID"]: r for r in without_repeats(existing)[0]}
    log = WorkLog(now, MAPPING_TAB)
    out = CrossCheck()

    reader_a, reader_b = (READER_LABELS.get(side, side) for side in readers)
    views: dict[tuple[str, str], tuple[str | None, str | None]] = {}
    for key, line in opinions.items():
        pair = []
        for side in readers:
            name = str(line.get(side) or "").strip()
            if name == NONE or name in by_name:
                pair.append(name)
            else:
                pair.append(None)
                out.unknown.append({"번호": str(line.get("번호") or ""), "판독": side, "이름": name})
        views[key] = (pair[0], pair[1])

    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for b in benefits:
        rider = rider_of.get(b["특약ID"])
        if rider is not None:
            groups.setdefault((kind_name(rider["원시특약명"]), kind_name(b["원시급부명"])), []).append(b)

    count = Counter()
    by_standard = Counter()
    for key, members in groups.items():
        claude, gemini = views.get(key, (None, None))
        if claude is None and gemini is None:
            state = None                                   # 쓸 의견이 없다
        elif claude == gemini:
            state = "대상외" if claude == NONE else "자동확정"
        else:
            state = "대기"
        recommend = next((n for n in (claude, gemini) if n and n != NONE), None) if state != "대상외" else None
        chosen = by_name.get(recommend) if recommend else None
        written = []
        for b in members:
            old = current.get(b["급부ID"])
            if old is not None and protected(old):
                count["보호되어 건너뜀"] += 1
                continue
            row_state = state or "대기"
            if state is None:
                count["의견 없음"] += 1
                if old is not None:
                    count["의견 없음(기존 줄 둠)"] += 1
                    continue
            rider = rider_of[b["특약ID"]]
            row = {
                "급부ID": b["급부ID"], "공시상품명": product.get(rider["종형ID"], ""), "원시특약명": rider["원시특약명"],
                "원시급부명": b["원시급부명"],
                "추천표준담보ID": chosen["표준담보ID"] if chosen else None,
                "추천표준담보명": chosen["표준담보명"] if chosen else None,
                "매핑확률": None,
                "확정표준담보ID": chosen["표준담보ID"] if chosen and row_state == "자동확정" else None,
                "검토상태": row_state, "담당자메모": None,
            }
            count[row_state] += 1
            if row_state == "자동확정":
                by_standard[chosen["표준담보명"]] += 1
            if old is not None and _same_mapping_row(old, row):
                count["지금과 같은 줄"] += 1
                continue
            out.rows.append(row)
            written.append(b)
        if not written:
            continue
        first = written[0]
        label = f"{rider_of[first['특약ID']]['원시특약명']} · {first['원시급부명']}"
        many = f"(같은 급부 {len(written)}행)"
        if state in ("자동확정", "대상외"):
            log.add("판정", first["급부ID"], "통과", f"{state}: {label} → {claude} {many}"[:300],
                    model=CROSS_CHECK, column="확정표준담보ID")
            continue
        if state is None:
            why = f"교차 확인 의견이 없어 담당자 검토 대기: {label}"
        else:
            why = f"두 판독의 의견이 달라 담당자 검토 대기: {label} ({reader_a} {claude or '없음'}, {reader_b} {gemini or '없음'})"
        log.add("판정", first["급부ID"], "보류", why[:300], model=CROSS_CHECK, column="추천표준담보ID")
        log.add("사람검토이관", first["급부ID"], "보류", f"{why} {many}"[:300], model=CROSS_CHECK, column="추천표준담보ID")
        out.waiting.append(f"- {why}")

    used = {key for key in groups if key in opinions}
    out.unused = sorted(str(line.get("번호") or "") for key, line in opinions.items() if key not in used)
    out.logs = log.rows
    out.by_standard = dict(sorted(by_standard.items(), key=lambda kv: (-kv[1], kv[0])))
    out.stats = {"대상 급부": sum(len(m) for m in groups.values()), "묶음": len(groups), "의견 있는 묶음": len(used),
                 "자동확정": count["자동확정"], "대상외": count["대상외"], "대기": count["대기"],
                 "의견 없음": count["의견 없음"], "의견 없음(기존 줄 둠)": count["의견 없음(기존 줄 둠)"],
                 "보호되어 건너뜀": count["보호되어 건너뜀"], "쓸 줄": len(out.rows), "지금과 같은 줄": count["지금과 같은 줄"],
                 "의견 줄": len(opinions), "사전에 없는 의견": len(out.unknown), "쓰이지 않은 의견 줄": len(out.unused)}
    return out


# ---------- 사전 seed를 시트 탭에 올리기 ----------
DICTIONARY_TAB = "hum_표준담보사전"
FLAG = "사용여부"


@dataclass
class DictionarySync:
    rows: list[dict[str, Any]]                 # 시트에 쓸 행: 지금 시트의 순서와 값 그대로, 사용여부만 바꾸고 새 행을 끝에 붙임
    added: list[str] = field(default_factory=list)                         # 더하는 표준담보ID
    switched: list[tuple[str, Any, Any]] = field(default_factory=list)     # (표준담보ID, 지금 사용여부, 바꿀 값)
    drift: list[str] = field(default_factory=list)       # 시트가 사본과 다른 곳. 사본 뒤에 담당자가 고친 것으로 보고 그대로 둔다
    kept: list[str] = field(default_factory=list)        # seed와 다르지만 이 길로는 바꾸지 않는 곳
    blocked: list[str] = field(default_factory=list)     # 이대로 쓰면 안 되는 문제. 하나라도 있으면 쓰지 않는다

    @property
    def changed(self) -> bool:
        return bool(self.added or self.switched)

    def report(self) -> str:
        lines = [f"표준담보 사전: 지금 시트 {len(self.rows) - len(self.added)}행, 더할 행 {len(self.added)}개, "
                 f"사용여부를 바꿀 행 {len(self.switched)}개"]
        lines += [f"  더함: {sid}" for sid in self.added]
        lines += [f"  사용여부: {sid} {before} → {after}" for sid, before, after in self.switched]
        if self.drift:
            lines.append(f"시트가 사본(data/snapshot)과 다른 곳 {len(self.drift)}개 (그대로 둠)")
            lines += [f"  {d}" for d in self.drift]
        if self.kept:
            lines.append(f"seed와 다르지만 바꾸지 않는 곳 {len(self.kept)}개")
            lines += [f"  {k}" for k in self.kept]
        if self.blocked:
            lines.append(f"쓰지 않음. 먼저 풀어야 할 문제 {len(self.blocked)}개")
            lines += [f"  {b}" for b in self.blocked]
        return "\n".join(lines)


def same_value(a: Any, b: Any) -> bool:
    """시트와 파일의 값이 같은지. 시트는 1000.0을 1000으로 돌려주고, 빈칸은 None이다.
    한쪽만 참·거짓이면 다르다고 본다. 파이썬은 True == 1, False == 0이라 사용여부 칸의 0을 False와 같게 볼 뻔했다."""
    if a in ("", None) and b in ("", None):
        return True
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    numbers = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (a, b))
    return float(a) == float(b) if numbers else a == b


def sync_dictionary(sheet: list[dict[str, Any]], seed: list[dict[str, Any]],
                    base: list[dict[str, Any]]) -> DictionarySync:
    """seed(data/seed)의 표준담보 사전을 시트 탭에 올리는 계획을 세운다. 담당자 탭이라 행 추가와 사용여부 변경만 한다.

    base는 seed를 고치기 전에 뜬 시트 사본(data/snapshot)이다. seed가 사본과 달라진 칸만 바꿀 대상으로 보고, 그 칸이
    시트에서 사본 그대로일 때만 바꾼다. 사본을 뜬 뒤 담당자가 시트를 고친 칸은 건드리지 않고 drift에 적는다.
    - seed에만 있는 행: 시트에 같은 ID가 없으면 끝에 붙인다. 같은 이름이 다른 ID로 시트에 있으면 막는다(선택지 이름이 겹친다).
    - 사용여부: seed와 사본이 다르고 시트가 사본 그대로면 seed 값으로 바꾼다. 시트가 이미 seed 값이면 그대로 둔다.
    - 그 밖의 열(분류, 이름, 급부유형, 단위)이 seed와 달라도, seed에 없는 행이 있어도 바꾸거나 지우지 않고 kept에 적는다.
    """
    header = TABS[DICTIONARY_TAB].header
    key = TABS[DICTIONARY_TAB].key
    now = {r[key]: r for r in sheet}
    old = {r[key]: r for r in base}
    out = DictionarySync(rows=[dict(r) for r in sheet])
    position = {r[key]: i for i, r in enumerate(out.rows)}

    for sid in sorted(set(now) | set(old)):
        if sid not in now:
            out.drift.append(f"{sid}: 사본에는 있고 시트에는 없음")
        elif sid not in old:
            out.drift.append(f"{sid}: 시트에만 있음 ({now[sid].get('표준담보명')})")
        else:
            out.drift += [f"{sid} {c}: 사본 {old[sid].get(c)!r} → 시트 {now[sid].get(c)!r}"
                           for c in header if not same_value(old[sid].get(c), now[sid].get(c))]

    names = {r.get("표준담보명"): r[key] for r in sheet}
    seed_ids = set()
    for s in seed:
        sid = s[key]
        seed_ids.add(sid)
        if sid not in now:
            if sid in old:
                out.kept.append(f"{sid}: 시트에서 지운 행은 되살리지 않음")
            elif s.get("표준담보명") in names:
                out.blocked.append(f"{sid}: 이름 '{s['표준담보명']}'이 시트의 {names[s['표준담보명']]}와 겹침")
            else:
                out.rows.append({c: s.get(c) for c in header})
                out.added.append(sid)
                names[s.get("표준담보명")] = sid
            continue
        if sid not in old:
            differ = [c for c in header if not same_value(s.get(c), now[sid].get(c))]
            if differ:
                out.kept.append(f"{sid}: 시트에 이미 있고 {', '.join(differ)}이(가) seed와 다름")
            continue
        out.kept += [f"{sid} {c}: seed {s.get(c)!r}, 사본 {old[sid].get(c)!r} (사용여부 밖의 열은 바꾸지 않음)"
                      for c in header if c != FLAG and not same_value(s.get(c), old[sid].get(c))]
        if not same_value(s.get(FLAG), old[sid].get(FLAG)):
            if same_value(now[sid].get(FLAG), old[sid].get(FLAG)):
                out.rows[position[sid]][FLAG] = s.get(FLAG)
                out.switched.append((sid, now[sid].get(FLAG), s.get(FLAG)))
            elif not same_value(now[sid].get(FLAG), s.get(FLAG)):
                out.kept.append(f"{sid} {FLAG}: 시트 {now[sid].get(FLAG)!r}를 담당자가 고친 값으로 보고 둠")
    out.kept += [f"{sid}: seed에 없지만 지우지 않음" for sid in sorted(set(old) - seed_ids) if sid in now]

    # 이번에 더하거나 바꾸는 행에 문제가 있으면 쓰지 않는다. 시트에 원래 있던 문제는 알리기만 한다
    touched = set(out.added) | {sid for sid, _, _ in out.switched}
    for sid, problems in check_rows(DICTIONARY_TAB, out.rows).items():
        (out.blocked if sid in touched else out.kept).append(f"{sid}: {'; '.join(problems)}")
    return out
