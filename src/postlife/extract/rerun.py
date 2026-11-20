"""다시 뽑은 급부 행을 시트에 있던 행과 견준다.

같은 문서를 다시 뽑을 때 두 가지를 잃기 쉽다.
- 급부ID: 급부ID는 급부 이름으로 만든다. 모델은 이름의 괄호 안 대상 표기를 실행마다 조금씩 다르게 적어
  ("암" ↔ "암(기타피부암 및 갑상선암 제외)", "수술자금(2종)" ↔ "수술자금(질병·2종)") 같은 급부의 ID가 바뀌고,
  급부ID로 이어진 hum_담보매핑과 sys_급부질병코드가 끊긴다. 같은 급부로 볼 수 있는 줄은 이전 ID를 잇는다(inherit_ids).
- 맞던 줄: 다시 뽑기의 마지막 단계가 실패해 "제외"로 끝난 항목, 금액을 읽지 못해 줄을 만들지 못한 항목, 호출이 끝내 실패했거나
  믿을 수 없는 빈 목록으로 끝나 처리하지 못한 특약 조각의 급부는 이번 결과에 없다. 그 급부의 이전 줄이 확정된 줄이면 그대로 둔다
  (carry_over). 모델 출력에 아예 없는 급부는 되살리지 않는다. 문서가 개정돼 없어진 급부일 수 있어서다.
  제외된 항목도 이번 모델 출력이므로, 그 항목의 이전 줄은 다른 새 줄에 잇지 않는다.
- 검토 대기: 예전 실행은 판정 기록을 같은 요약서를 쓰는 종형 가운데 첫 종형의 행에만 남겼고, 화면은 급부ID의 종형ID 뒤
  꼬리로 다른 종형에 검토 대기 표시를 옮긴다. 지금은 조각을 실은 종형마다 기록을 남기고, 다시 뽑은 종형마다 그 사실을
  기록한다(coverage_logs). 자기 기록이 있는 줄은 자기 기록만 보고, 없는 줄만 다른 종형의 기록을 옮겨 본다(waiting_rows).
  예전 기록을 위해 한 조각을 실은 종형들의 행은 이전 ID를 이어도 꼬리를 함께 쓴다.

전후 비교(content_diff)의 기준은 scripts/dev/compare_rerun.py와 같다: 특약, 지급액, 첫 감액 구간, 면책.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable

from .. import ids
from ..worklog import WorkLog

Row = dict[str, Any]
REVIEW_STEP = "사람검토이관"
JUDGE_STEPS = {"판정", REVIEW_STEP}
KEEP_STEP, KEEP_RESULT = "재추출", "반려"      # 화면 6은 이 짝을 "앞선 값 유지"로 센다
KEPT_ROW = "재추출 전 확정 줄을 그대로 둠"       # 이전 줄을 지킨 기록의 사유에 든다. scripts/dev/compare_rerun.py가 이 글자로 센다
# 급부를 다시 뽑은 종형마다 남기는 기록. 이 기록이 있는 실행은 판정 기록을 종형마다 남겼다. 대상행ID는 종형ID다
# (특약ID에 남기는 "추출" 기록처럼 급부 추출 단계의 기록이라 대상탭은 sys_급부로 둔다)
COVER_STEP, COVER_TAB = "추출", "sys_급부"
COVERED = "판정 기록을 이 종형의 급부ID마다 남김"


def _num(value: Any) -> float | None:
    return None if value in (None, "") else float(value)


def stem(name: Any) -> str:
    """급부 이름의 괄호 앞부분. 공백과 전각 글자 차이는 급부ID를 만들 때처럼 없앤다."""
    return ids.normalize(str(name)).split("(")[0]


def same_key(row: Row) -> tuple:
    """같은 급부인지 가리는 값: 특약, 이름의 괄호 앞부분, 지급금액(기준가입금액, 기준지급금액), 감액 두 구간."""
    return (row["특약ID"], stem(row["원시급부명"]), _num(row.get("기준가입금액만원")), _num(row.get("기준지급금액만원")),
            _num(row.get("감액개월1")), _num(row.get("감액지급률1")), _num(row.get("감액개월2")), _num(row.get("감액지급률2")))


def content_key(row: Row) -> tuple:
    """전후 비교에서 줄의 내용: 특약, 지급액, 첫 감액 구간, 면책."""
    return (row["특약ID"], _num(row.get("기준지급금액만원")), _num(row.get("감액개월1")), _num(row.get("감액지급률1")),
            _num(row.get("면책기간일수")))


def loose_key(row: Row) -> tuple:
    """특약과 지급액만 보는 느슨한 비교. 감액이나 면책만 달라진 줄을 가려 볼 때 쓴다."""
    return (row["특약ID"], _num(row.get("기준지급금액만원")))


def content_diff(old: Iterable[Row], new: Iterable[Row], key: Callable[[Row], tuple] = content_key) -> tuple[Counter, Counter]:
    """내용 기준으로 잃은 줄과 얻은 줄. 같은 내용의 줄이 여럿이면 줄 수로 센다."""
    before, after = Counter(map(key, old)), Counter(map(key, new))
    return before - after, after - before


@dataclass
class Inherited:
    rows: list[Row]                                                    # 이번에 쓸 새 행. 이은 줄은 이전 급부ID와 원시급부명을 쓴다
    renamed: dict[str, str] = field(default_factory=dict)             # 이번에 계산된 급부ID → 이어받은 이전 급부ID
    pairs: list[tuple[Row, Row]] = field(default_factory=list)        # (이전 행, 이번에 뽑은 그대로의 행)
    roles: list[tuple[Row, Row]] = field(default_factory=list)        # 이은 짝 가운데 급부역할이 이전과 달라진 것(이번 값을 쓴다)
    claimed: list[tuple[Row, Row]] = field(default_factory=list)      # (이전 행, 이번에 제외된 항목의 행): 제외된 항목이 가리키는 이전 줄
    aligned: list[tuple[Row, Row]] = field(default_factory=list)      # (쓸 행, 이번에 뽑은 그대로의 행): 같은 조각을 실은 다른 종형을 따라 꼬리를 맞춘 줄
    split: int = 0                                                     # 같은 조각을 실은 종형끼리 이을 꼬리가 갈려 잇지 않은 항목 수


def inherit_ids(old: list[Row], new: list[Row], held: Iterable[Row] = (), units: Iterable[dict[str, str]] = ()) -> Inherited:
    """같은 급부의 이전 급부ID와 원시급부명을 새 행에 잇는다. 급부역할은 이번에 뽑은 값을 쓰고, 이전과 달라진 줄은 roles에 남긴다.

    같은 급부: 같은 특약 안에서 이름의 괄호 앞부분, 지급금액, 감액 구간이 모두 같고, 그런 줄이 이전 쪽과 새 쪽에 하나씩만 있을 때.
    ID가 이미 같은 줄끼리는 그대로 두고, 남은 줄끼리 견준다. 그래서 이어받는 ID는 이번 결과의 다른 줄에 없는 ID이고,
    한 이전 줄은 한 새 줄에만 이어지므로 한 실행 안에서 같은 ID가 두 줄에 붙지 않는다. 이번 결과에 같은 ID가 두 번 나온 줄은 잇지 않는다.
    면책, 감액예외, 지급횟수제한은 이번에 뽑은 값을 쓴다.

    held: 이번에 뽑았지만 "제외"로 끝나 시트에 쓰지 않는 항목의 행. 이번 결과의 새 쪽으로 센다. 그래서 그 ID의 이전 줄이나
      그 항목과 같은 급부로 보이는 이전 줄은 다른 새 줄에 잇지 않고 claimed로 돌린다(지킬지는 carry_over가 정한다).
      같은 급부로 보이는 새 줄이 둘(제외된 항목과 다른 항목)이면 어느 쪽인지 알 수 없어 잇지 않는다.
    units: 한 조각의 한 항목이 종형마다 낸 행의 {종형ID: 이번에 계산된 급부ID}. 예전 실행의 판정 기록은 첫 종형의 행에만 남았고,
      화면은 ID에서 종형ID 뒤의 꼬리가 같은 행에 검토 대기 표시를 옮긴다. 그래서 한 묶음의 행은 꼬리를 함께 쓴다.
      묶음의 한 종형이 이전 ID를 이으면, 이전 줄이 없는 다른 종형도 같은 꼬리와 원시급부명을 쓴다(aligned).
      종형마다 이을 꼬리가 갈리거나 맞출 ID가 다른 줄의 것이면 그 묶음은 잇지 않고 모두 이번에 계산된 ID를 쓴다(split).
      다른 줄의 것: 다른 새 줄이 이번에 계산된 ID나 이어받는 ID, 시트에 있던 다른 줄의 ID(같은 급부의 기준이 거절한 줄 포함),
      제외된 항목과 그 항목이 가리킨 이전 줄의 ID.
    """
    held = list(held)
    seen = Counter(r["급부ID"] for r in new + held)
    old_ids = {r["급부ID"] for r in old}
    held_rows = {id(r) for r in held}
    left_old: dict[tuple, list[Row]] = defaultdict(list)
    left_new: dict[tuple, list[Row]] = defaultdict(list)
    for r in old:
        if r["급부ID"] not in seen:
            left_old[same_key(r)].append(r)
    for r in new + held:
        if r["급부ID"] not in old_ids:
            left_new[same_key(r)].append(r)
    out = Inherited(rows=[])
    by_old = {r["급부ID"]: r for r in old}
    out.claimed += [(by_old[r["급부ID"]], r) for r in held if r["급부ID"] in by_old]
    prior_of: dict[int, Row] = {}
    for key, olds in left_old.items():
        news = left_new.get(key, [])
        if len(olds) == 1 and len(news) == 1 and seen[news[0]["급부ID"]] == 1:
            if id(news[0]) in held_rows:
                out.claimed.append((olds[0], news[0]))
            else:
                prior_of[id(news[0])] = olds[0]
    adopted = _align(new, old_ids, prior_of, units, {r["급부ID"] for r in held} | {o["급부ID"] for o, _ in out.claimed}, out)

    for r in new:
        prior = prior_of.get(id(r))
        if prior is None and id(r) not in adopted:
            out.rows.append(r)
            continue
        target, prior = (prior["급부ID"], prior) if prior is not None else adopted[id(r)]
        row = {**r, "급부ID": target, "원시급부명": prior["원시급부명"]}
        # 급부역할은 이번에 뽑은 값을 쓴다. 한 특약 안에서 주급부와 부수급부는 서로 맞물려 정해지므로, 이은 줄만 이전 값으로 두면
        # 이전 실행과 이번 실행의 역할이 한 특약 안에 섞인다(2026-11-19 한화 자료에서 그렇게 섞인 특약이 31개 나왔다).
        if prior.get("급부역할") and r.get("급부역할") != prior["급부역할"] and id(r) not in adopted:
            out.roles.append((prior, r))
        out.renamed[r["급부ID"]] = target
        if id(r) in adopted:
            out.aligned.append((row, r))
        else:
            out.pairs.append((prior, r))
        out.rows.append(row)
    return out


def _align(new: list[Row], old_ids: set[str], prior_of: dict[int, Row], units: Iterable[dict[str, str]], taken: set[str],
           out: Inherited) -> dict[int, tuple[str, Row]]:
    """한 조각을 실은 종형들의 행이 꼬리를 함께 쓰게 한다(inherit_ids의 units). {id(새 행): (쓸 급부ID, 이름을 따를 이전 행)}.

    prior_of에서 꼬리가 갈린 묶음의 짝을 지운다. taken: 이번에 다른 줄이 쓰는 ID(제외된 항목과 그 이전 줄).
    맞출 ID로 쓰지 않는 것: taken, 시트에 있던 모든 줄의 ID, 이번에 계산된 모든 새 줄의 ID와 이어받을 ID.
    이전 ID를 이은 새 줄도 뒤 묶음이 갈리면 이번에 계산된 ID로 돌아가므로, 그 ID를 앞 묶음이 가져가면 한 실행에서 두 줄이 같은 ID를 쓴다.
    같은 급부의 기준이 거절한 이전 줄의 ID를 가져가면 내용이 다른 급부가 그 줄의 매핑을 이어받고, 그 줄을 지킬 수도 없게 된다.
    """
    rows_of: dict[str, list[Row]] = defaultdict(list)
    for r in new:
        rows_of[r["급부ID"]].append(r)
    taken = taken | old_ids | {r["급부ID"] for r in new} | {prior["급부ID"] for prior in prior_of.values()}
    adopted: dict[int, tuple[str, Row]] = {}
    for unit in units:
        members = [(v, fresh, rows_of.get(fresh, [])) for v, fresh in unit.items()]
        leads = [prior_of[id(r)] for _, _, rows in members for r in rows if id(r) in prior_of]
        if len(members) < 2 or not leads:
            continue                       # 이은 줄이 없으면 모두 이번에 계산된 ID를 써서 꼬리가 같다
        tails: set[str] = set()
        free: list[tuple[str, list[Row]]] = []
        for v, fresh, rows in members:
            linked = [prior_of[id(r)]["급부ID"][len(v):] for r in rows if id(r) in prior_of]
            if linked:
                tails.update(linked)
            elif fresh in old_ids:
                tails.add(fresh[len(v):])  # 이전 ID 그대로인 줄
            else:
                free.append((v, rows))
        tail = next(iter(tails))
        if len(tails) > 1 or any(len(rows) != 1 or v + tail in taken for v, rows in free):
            for _, fresh, rows in members:
                for r in rows:
                    prior_of.pop(id(r), None)
                taken.add(fresh)
            out.split += 1
            continue
        for v, rows in free:
            adopted[id(rows[0])] = (v + tail, leads[0])
            taken.add(v + tail)
    return adopted


def rename_targets(logs: list[Row], renamed: dict[str, str]) -> None:
    """이번 실행의 급부 기록이 이어받은 ID를 가리키게 고친다. 그러지 않으면 화면이 그 줄의 검토 대기 표시를 찾지 못한다."""
    for log in logs:
        if log.get("대상탭") == "sys_급부" and log.get("대상행ID") in renamed:
            log["대상행ID"] = renamed[log["대상행ID"]]


def coverage_logs(now: datetime, variant_ids: Iterable[str], name: str) -> list[Row]:
    """급부를 다시 뽑은 종형마다 한 줄. 이 실행의 판정 기록이 종형마다 남았다는 표시다(pending_benefits)."""
    log = WorkLog(now, COVER_TAB)
    for vid in variant_ids:
        log.add(COVER_STEP, vid, "통과", f"{name}: 상품요약서에서 급부를 다시 뽑음. {COVERED}")
    return log.rows


def per_variant_runs(logs: Iterable[Row]) -> set[str]:
    """판정 기록을 종형마다 남긴 실행의 실행일시(coverage_logs의 기록이 있는 실행)."""
    return {str(r.get("실행일시") or "") for r in logs
            if r.get("대상탭") == COVER_TAB and r.get("작업단계") == COVER_STEP and COVERED in str(r.get("사유") or "")}


def waiting_rows(rows: dict[str, str | None], records: list[Row], sharing: dict[str, list[str]],
                 per_variant: set[str]) -> dict[str, list[Row]]:
    """검토 대기인 급부ID와 그 판정의 사람검토이관 기록. 화면(site/model.py의 Data._pending)과 함께 쓰는 규칙이다.

    rows: 시트에 있는 {급부ID: 종형ID}. records: 판정과 사람검토이관 기록. sharing: {종형ID: 같은 요약서를 쓰는 다른 종형ID}.
    per_variant: per_variant_runs의 값.
    - 기록은 가장 나중 실행만 보고, 그 실행에 사람검토이관 기록이 있으면 검토 대기다.
    - 자기 급부ID에 기록이 있는 줄은 자기 기록만 본다. 가입유형별로 표가 갈려 종형마다 판정이 다를 수 있다.
    - 자기 기록이 없는 줄(예전 실행은 기록을 첫 종형의 행에만 남겼다)은 같은 요약서를 쓰는 다른 종형의 같은 꼬리 급부ID 기록을 본다.
      그 줄이 시트에 없어진 뒤의 기록도 본다. 다만 판정 기록을 종형마다 남긴 실행의 기록은 옮기지 않는다. 그런 실행이 쓴 줄에는
      자기 기록이 있으므로, 자기 기록이 없는 줄은 그 실행이 손대지 않았거나(일부 종형만 다시 뽑음) 이전 줄을 그대로 지킨 줄이다.
    """
    by_target: dict[str, list[Row]] = defaultdict(list)
    for r in records:
        by_target[r.get("대상행ID")].append(r)
    out: dict[str, list[Row]] = {}
    for bid, vid in rows.items():
        seen = by_target.get(bid)
        if not seen and vid is not None:
            suffix = bid[len(vid):]
            seen = [r for other in sharing.get(vid, []) for r in by_target.get(other + suffix, [])
                    if str(r.get("실행일시") or "") not in per_variant]
        if not seen:
            continue
        last = max(str(r.get("실행일시") or "") for r in seen)
        review = [r for r in seen if str(r.get("실행일시") or "") == last and r.get("작업단계") == REVIEW_STEP]
        if review:
            out[bid] = review
    return out


def pending_benefits(benefits: list[Row], riders: list[Row], variants: list[Row], logs: list[Row]) -> set[str]:
    """검토 대기인 급부ID. 화면(site/model.py의 Data._pending)과 같은 규칙(waiting_rows)에 하나를 더한다.

    더한 것: 이전 줄을 지킨 실행(carry_over가 남긴 '재추출 반려' 기록)의 판정 기록은 그 줄에 대해 보지 않는다. 제외된 항목의
    판정 반려와 사람검토이관이 같은 ID에 남지만, 시트의 그 줄은 그 실행이 쓴 값이 아니라 그 앞 실행이 확정한 값이다.
    이것을 보면 지킨 줄이 다음 재추출에서 검토 대기로 잡혀, 같은 제외가 한 번 더 나올 때 사람 검토 없이 지워진다.
    화면은 이 기록을 그대로 보아 지킨 줄을 검토 대기로 보인다(사람이 볼 것이 있다는 뜻으로는 맞다).
    기록이 없는 줄은 확정으로 본다.
    """
    kept = {(r.get("대상행ID"), str(r.get("실행일시") or "")) for r in logs
            if r.get("대상탭") == "sys_급부" and r.get("작업단계") == KEEP_STEP and r.get("결과") == KEEP_RESULT
            and KEPT_ROW in str(r.get("사유") or "")}
    judged = [r for r in logs if r.get("대상탭") == "sys_급부" and r.get("작업단계") in JUDGE_STEPS
              and (r.get("대상행ID"), str(r.get("실행일시") or "")) not in kept]
    owner = {r["특약ID"]: r["종형ID"] for r in riders}
    return set(waiting_rows({r["급부ID"]: owner.get(r["특약ID"]) for r in benefits}, judged, sharing_of(variants), per_variant_runs(logs)))


def sharing_of(variants: Iterable[Row]) -> dict[str, list[str]]:
    """{종형ID: 같은 요약서해시를 쓰는 다른 종형ID}. 요약서해시가 비어 있으면 다른 종형이 없다."""
    groups: dict[Any, list[str]] = defaultdict(list)
    for v in variants:
        if v.get("요약서해시") not in (None, ""):
            groups[v["요약서해시"]].append(v["종형ID"])
    return {vid: [u for u in group if u != vid] for group in groups.values() for vid in group}


@dataclass
class Carried:
    benefits: list[Row]                                                # 이번에 쓸 급부 행: 이은 줄과 지킨 이전 줄을 포함
    inherited: Inherited
    riders: list[Row] = field(default_factory=list)                   # 지킨 이전 줄 때문에 되살린 이전 특약 행
    kept: list[Row] = field(default_factory=list)                     # 지킨 이전 급부 줄
    pending: list[Row] = field(default_factory=list)                  # 해당하지만 검토 대기여서 되살리지 않은 이전 줄
    unmatched: list[tuple[str, str]] = field(default_factory=list)    # (특약ID, 급부 이름): 이전 줄을 하나로 가리지 못했거나 특약 행이 없음
    logs: list[Row] = field(default_factory=list)


def carry_over(old: list[Row], old_riders: list[Row], new: list[Row], new_riders: set[str],
               held: list[Row], failed: set[str], pending: set[str], now: datetime,
               units: Iterable[dict[str, str]] = (), failed_pages: dict[str, set[int]] | None = None) -> Carried:
    """이전 급부ID를 잇고, 이번에 잃은 확정 줄을 되살린다.

    old: 이번에 다시 뽑은 종형의, 시트에 있던 급부 행. old_riders: 시트에 있던 특약 행.
    new: 이번에 뽑은 급부 행. new_riders: 이번에 뽑은 특약ID.
    held: 이번에 "제외"로 끝난 항목(금액을 읽지 못한 항목 포함)이 그 조각을 실은 종형마다 냈을 행(시트에 쓰지 않는다).
      이번에 그 특약 행이 나온 특약만 본다.
    failed: 처리하지 못한 조각의 특약ID. 이번에 그 특약 행이 없으므로 이전 특약 행도 되살린다.
    failed_pages: {특약ID: 처리하지 못한 조각의 첫 쪽}. 같은 특약의 다른 조각은 처리돼 특약 행이 나온 경우다. 그 특약의 이전 줄
      가운데 근거문서쪽수가 그 쪽인 줄을 처리하지 못한 조각의 것으로 본다.
    pending: 검토 대기인 급부ID. 이런 줄은 이번 실행의 사정과 관계없이 되살리지 않는다.
    units: inherit_ids의 units.

    제외된 항목과 이전 줄은 급부ID가 같으면 잇는다. 같은 급부로 보이는 다른 새 줄보다 먼저다(inherit_ids의 held).
    다음은 같은 급부의 기준(same_key)이 하나씩만 맞을 때, 그다음은 이름의 괄호 앞부분이 양쪽에 하나씩만 있을 때 잇는다.
    둘 이상이거나, 괄호 앞부분이 같은 새 줄(이전 ID와 이어지지 않은 것)이 이번 결과에 있으면 어느 줄인지 알 수 없어
    되살리지 않고 unmatched에 남긴다. 그 새 줄이 그 급부일 수 있어 되살리면 같은 급부가 두 줄이 된다.
    """
    inherited = inherit_ids(old, new, held, units)
    present = {r["급부ID"] for r in inherited.rows}
    old_ids = {r["급부ID"] for r in old}
    fresh: dict[str, set[str]] = defaultdict(set)       # 특약 → 이번 결과에서 이전 ID와 이어지지 않은 새 줄의 괄호 앞부분
    for r in inherited.rows:
        if r["급부ID"] not in old_ids:
            fresh[r["특약ID"]].add(stem(r["원시급부명"]))
    looked = new_riders - failed            # 제외된 항목을 보는 특약: 이번에 특약 행이 나왔고, 처리하지 못해 통째로 지키는 특약이 아닌 것
    claimed = [(o, h) for o, h in inherited.claimed if o["급부ID"] not in present and o["특약ID"] in looked]
    gone = {r["급부ID"] for r in old} - present - {o["급부ID"] for o, _ in claimed}
    missing: dict[str, list[Row]] = defaultdict(list)
    for r in old:
        if r["급부ID"] in gone:
            missing[r["특약ID"]].append(r)

    chosen: list[tuple[Row, str]] = []
    unprocessed = "호출이 끝내 실패했거나 급부 0건으로 끝난 것을 믿을 수 없어 이 특약 조각을 처리하지 못함"
    for rider in sorted(failed):
        chosen += [(r, unprocessed) for r in missing.get(rider, [])]
    for rider, pages in sorted((failed_pages or {}).items()):
        chosen += [(r, unprocessed) for r in missing.get(rider, []) if _page(r) in pages]
    out = Carried(benefits=list(inherited.rows), inherited=inherited)
    why = "'{}' 항목이 다시 뽑아도 원문과 맞지 않아 보이거나 값이 앞뒤가 맞지 않거나 금액을 읽지 못해 제외됨"
    chosen += [(o, why.format(h["원시급부명"])) for o, h in claimed]
    done = {id(h) for _, h in inherited.claimed}
    rest: dict[str, set[str]] = defaultdict(set)
    for h in held:
        if id(h) not in done and h["급부ID"] not in present and h["특약ID"] in looked:
            rest[h["특약ID"]].add(str(h["원시급부명"]))
    for rider in sorted(rest):
        for label, row in _by_stem(sorted(rest[rider]), missing.get(rider, []), fresh[rider]):
            if row is None:
                out.unmatched.append((rider, label))
            else:
                chosen.append((row, why.format(label)))

    rider_rows = {r["특약ID"]: r for r in old_riders}
    benefit_log, rider_log = WorkLog(now, "sys_급부"), WorkLog(now, "sys_특약")
    revived: set[str] = set()
    seen: set[str] = set()
    for row, why in chosen:
        if row["급부ID"] in seen:
            continue
        seen.add(row["급부ID"])
        if row["급부ID"] in pending:
            out.pending.append(row)
            continue
        rider = row["특약ID"]
        if rider not in new_riders and rider not in revived:
            if rider not in rider_rows:
                out.unmatched.append((rider, str(row["원시급부명"])))     # 특약 행이 없으면 급부만 둘 수 없다
                continue
            revived.add(rider)
            out.riders.append(dict(rider_rows[rider]))
            rider_log.add(KEEP_STEP, rider, KEEP_RESULT, f"{rider_rows[rider]['원시특약명']}: 이번 실행에서 {why}. "
                          "재추출 전 특약 행을 그대로 둠")
        out.kept.append(row)
        out.benefits.append(row)
        benefit_log.add(KEEP_STEP, row["급부ID"], KEEP_RESULT, f"{row['원시급부명']}: 이번 실행에서 {why}. "
                        f"{KEPT_ROW} (지급 {_money(row.get('기준지급금액만원'))}, 근거 {row.get('근거문서쪽수')}쪽)")
    out.logs = rider_log.rows + benefit_log.rows
    return out


def _by_stem(labels: list[str], candidates: list[Row], written: set[str] = frozenset()) -> list[tuple[str, Row | None]]:
    """급부ID나 같은 급부의 기준으로 잇지 못한 제외된 이름마다, 이름의 괄호 앞부분이 양쪽에 하나씩만 있는 이전 줄을 고른다.

    written: 이번 결과에서 이전 ID와 이어지지 않은 새 줄의 괄호 앞부분. 이번 쪽으로 센다. 그런 새 줄이 있으면 고르지 않는다.
    괄호 앞부분이 같은 이전 줄이 있는데 하나로 가리지 못하면 (이름, None)을 낸다. 그런 이전 줄이 아예 없으면(이번에 처음 나온
    급부) 아무것도 내지 않는다.
    """
    out: list[tuple[str, Row | None]] = []
    for label in labels:
        same_labels = [x for x in labels if stem(x) == stem(label)]
        same_rows = [r for r in candidates if stem(r["원시급부명"]) == stem(label)]
        if same_rows:
            one = len(same_labels) == 1 and len(same_rows) == 1 and stem(label) not in written
            out.append((label, same_rows[0] if one else None))
    return out


def _page(row: Row) -> int | None:
    value = row.get("근거문서쪽수")
    try:
        return None if value in (None, "") else int(float(value))
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> str:
    amount = _num(value)
    if amount is None:
        return "금액 없음"
    return f"{int(amount):,}만원" if amount.is_integer() else f"{amount}만원"
