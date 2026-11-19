"""화면 1 "이번 주 달라진 점"(기획 8장). 코드가 먼저 추려 확정하는 세 가지를 만든다.

1. 이번 주에 적용이 시작됐거나 판매가 끝난 개정판. 종형이 아니라 개정판ID 단위로 묶는다(한 개정판에 종형이 여럿이다).
2. 이번 주차의 시장 소식. 판정확률이 있고 통과 기준(기사선별_통과) 이상인 소식만 싣는다.
   이번 주차에 그런 소식이 없으면 가장 최근 수집주차의 소식을 참고용으로 싣는다.
   수집주차는 "YYYY-Www" 꼴로 맞춰 주차 순서로 견주고, 꼴이 다르거나 비어 있는 소식은 주차를 정할 수 없어 싣지 않는다.
3. 대표 조건에서 우열 표시가 바뀐 표준담보. 지난주 사본이 있을 때만 견준다. 기획 8장대로 보험사의 실제 개정만 화면 1에 싣는다.
   - 개정: 개정판ID가 바뀐 쪽에서 그 담보의 판정 값(지급액, 면책, 감액, 지급 한도 문구)이 실제로 달라졌다.
   - 검토가 끝나 판정이 생김: 지난주에는 검토 대기(p)나 매핑 검토 대기(q)라 판정하지 않았다. 개정도 정정도 아니어서 건수만 센다.
   - 그 밖에는 자료 정정이다. 여기 싣지 않고 건수만 화면 6으로 넘긴다.

"이번 주"는 자료 기준 시각(meta.snapshot_at)을 서울 시간으로 본 ISO 주다. 수집주차와 같은 "YYYY-Www" 꼴이다.
브라우저 시간대에 따라 월요일 경계가 어긋나지 않도록 화면이 아니라 여기서 정한다.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from . import compare
from .model import Cond, Data, HOME_ORG, _blank

KST = timezone(timedelta(hours=9))
PASS_KEY = "기사선별_통과"
_WEEK = re.compile(r"(\d{4})-W(\d{1,2})")
REVIEW_CODES = {"p", "q"}       # compare.verdict에서 검토 대기라 판정하지 않은 칸


# ---------- 이번 주 ----------
def week_of(stamp: Any) -> dict[str, str] | None:
    """자료 기준 시각이 든 ISO 주. 시간대가 없는 시각은 서울 시간으로 본다."""
    if _blank(stamp):
        return None
    try:
        moment = datetime.fromisoformat(str(stamp))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=KST)
    day = moment.astimezone(KST).date()
    year, week, weekday = day.isocalendar()
    monday = day - timedelta(days=weekday - 1)
    return {"id": f"{year}-W{week:02d}", "from": monday.isoformat(), "to": (monday + timedelta(days=6)).isoformat(),
            "today": day.isoformat()}


def _day(value: Any) -> str | None:
    if _blank(value):
        return None
    text = str(value)[:10]
    try:
        date.fromisoformat(text)
    except ValueError:
        return None
    return text


def week_id(value: Any) -> str | None:
    """수집주차를 "YYYY-Www" 꼴로 맞춘다("2026-W5"는 "2026-W05"). 꼴이 다르거나 주차가 1~53이 아니면 None.
    두 자리로 맞춘 꼴끼리는 글자 순서가 주차 순서와 같다."""
    if _blank(value):
        return None
    found = _WEEK.fullmatch(str(value).strip())
    if not found or not 1 <= int(found.group(2)) <= 53:
        return None
    return f"{found.group(1)}-W{int(found.group(2)):02d}"


def on_sale(variant: dict, today: str | None) -> bool:
    """자료 기준일(today)에 판매 중인 종형인지. 화면 1의 판매 중 종형 수와 대표 조건의 우열 비교가 함께 쓴다.

    적용시작일이 오늘 이전이고(아직 적용 전인 예약 개정판은 뺀다), 판매종료일이 없거나 오늘 이후여야 한다(판매종료일은 판매하는 마지막 날이다).
    판매종료일이 적혀 있는데 날짜로 읽을 수 없으면 판매가 끝난 것으로 본다. today가 없으면 날짜를 견줄 수 없어 판매종료일이 비어 있는지만 본다.
    """
    if not _blank(variant.get("판매종료일")):
        end = _day(variant.get("판매종료일"))
        if end is None or today is None or end < today:
            return False
    start = _day(variant.get("적용시작일"))
    return today is None or start is None or start <= today


# ---------- 1. 개정판 ----------
def revision_events(data: Data, week: dict[str, str] | None) -> dict[str, Any]:
    """개정판마다 적용 시작과 판매 종료를 따로 센다. 종형 수는 그 날짜에 시작(종료)한 종형의 수다."""
    groups: dict[tuple[str, str, str], list[str]] = {}
    for vid in data.variant_order:
        v = data.variants[vid]
        for kind, column in (("start", "적용시작일"), ("end", "판매종료일")):
            day = _day(v.get(column))
            if day:
                groups.setdefault((str(v.get("개정판ID")), kind, day), []).append(vid)
    events = [{"rev": rev, "kind": kind, "date": day, "org": data.variants[vids[0]]["기관코드"],
               "orgName": data.org_name(data.variants[vids[0]]["기관코드"]), "variants": vids}
              for (rev, kind, day), vids in groups.items()]
    events.sort(key=lambda e: (e["date"], e["kind"] == "start", e["org"] == HOME_ORG, e["rev"]), reverse=True)
    if week is None:
        return {"thisWeek": [], "latest": events[0] if events else None}
    this = [e for e in events if week["from"] <= e["date"] <= week["to"]]
    latest = None if this else next((e for e in events if e["date"] <= week["to"]), None)
    return {"thisWeek": this, "latest": latest}


# ---------- 2. 시장 소식 ----------
def news_state(data: Data, trend: dict[str, Any]) -> str:
    """passed 통과 / below 통과 기준에 못 미침 / undecided 판정확률 없음. 통과 기준이 없으면 어떤 소식도 통과하지 않는다."""
    prob = trend.get("판정확률")
    if prob is None:
        return "undecided"
    passed = data.setting_num(PASS_KEY)
    return "passed" if passed is not None and prob >= passed else "below"


def news(data: Data, week: dict[str, str] | None) -> dict[str, Any]:
    """week가 없으면(자료 기준 시각이 없음) 이번 주차를 정할 수 없어 가장 최근 수집주차의 소식을 싣는다.
    이때는 "이번 주차에 통과한 소식이 없어 지난 것을 싣는다"는 경우가 아니므로 fallback은 거짓이다."""
    rows = sorted(data.trends, key=lambda t: (str(t.get("발표일자")), str(t.get("동향ID"))), reverse=True)
    states = {t["동향ID"]: news_state(data, t) for t in rows}
    weeks = {t["동향ID"]: week_id(t.get("수집주차")) for t in rows}
    this_id = week["id"] if week else None
    passed = [t for t in rows if states[t["동향ID"]] == "passed" and weeks[t["동향ID"]]]
    this_rows = [t for t in rows if this_id is not None and weeks[t["동향ID"]] == this_id]
    shown = this_id if any(states[t["동향ID"]] == "passed" for t in this_rows) else max(
        (weeks[t["동향ID"]] for t in passed if this_id is None or weeks[t["동향ID"]] <= this_id), default=None)
    items = [{
        "id": t["동향ID"], "org": t["기관코드"], "orgName": data.org_name(t["기관코드"]), "kind": t.get("분류유형"),
        "date": t.get("발표일자"), "summary": t.get("핵심요약"), "media": t.get("매체명"), "via": t.get("수집경로"),
        "url": t.get("출처URL"), "prob": t.get("판정확률"),
    } for t in passed if weeks[t["동향ID"]] == shown]
    count = lambda state: sum(1 for t in this_rows if states[t["동향ID"]] == state)
    return {
        "week": shown, "fallback": this_id is not None and shown is not None and shown != this_id, "items": items,
        "threshold": data.setting_num(PASS_KEY),
        "thisWeek": {"total": len(this_rows), "passed": count("passed"), "below": count("below"), "undecided": count("undecided")},
    }


# ---------- 3. 대표 조건의 우열 변화 ----------
def rep_conditions(data: Data) -> dict[str, Any]:
    """기준값 탭의 대표 조건. 심사 유형은 "일반심사"처럼 심사유형으로 적거나 "325"처럼 간편고지 약칭의 숫자로 적는다."""
    age = data.setting_num("REP_WEEKLY_AGE")
    sexes = [s for s in (data.setting_text("REP_WEEKLY_SEX_1"), data.setting_text("REP_WEEKLY_SEX_2")) if s in ("M", "F")]
    uws = []
    for key in ("REP_WEEKLY_UW_1", "REP_WEEKLY_UW_2"):
        spec = data.setting_text(key)
        if spec:
            digits = _digits(spec)
            uws.append({"spec": spec, "label": f"간편심사 {spec}" if digits == spec else spec})
    return {"age": int(age) if age is not None else None, "sexes": list(dict.fromkeys(sexes)), "uws": uws}


def _digits(text: Any) -> str:
    return "".join(c for c in str(text or "") if c.isdigit())


def _uw_match(variant: dict, spec: str) -> bool:
    digits = _digits(spec)
    if digits:
        return _digits(variant.get("간편고지약칭")) == digits
    return variant.get("심사유형") == spec


def _line(variant: dict) -> str:
    """종형을 사본끼리 잇는 열쇠. 개정으로 종형ID가 바뀌어도 종형계보키는 그대로다."""
    return str(variant.get("종형계보키") or variant["종형ID"])


def today_of(data: Data) -> str | None:
    """자료 기준일(서울 시간). 자료 기준 시각이 없거나 읽을 수 없으면 None."""
    return (week_of(data.meta.get("snapshot_at")) or {}).get("today")


def _terms(core: dict[str, Any]) -> tuple:
    """칸에서 우열 판정에 쓰는 값(compare.compare_terms가 보는 값). 개정판이 바뀐 쪽에서 이 값이 달라졌는지로 실제 개정인지 가린다.
    검토 대기 표시(pend)는 값이 아니므로 넣지 않는다."""
    if core["kind"] != "ok":
        return (core["kind"], bool(core.get("waiting")))
    val = core["val"]
    return ("ok", None if val is None else round(val, 6), core["wait"], [list(x) for x in core["red"] or []],
            compare._squash(core.get("limit")))


def rep_verdicts(data: Data, rep: dict[str, Any]) -> dict[tuple, dict[str, Any]]:
    """대표 조건마다 우체국 기준 종형과 심사 유형이 같은 다른 회사 종형의 판정(compare.verdict).

    열쇠는 (심사 유형, 기준 종형계보키, 비교 종형계보키, 표준담보ID, 성별). 판매 중인 정밀 비교 종형만 본다(on_sale).
    baseTerms, peerTerms는 양쪽 칸의 판정 값(_terms)이다.
    """
    today = today_of(data)
    vids = [v for v in data.variant_order if data.variants[v].get("비교역할구분") == compare.COMPARE_ROLE
            and on_sale(data.variants[v], today)]
    stds = [sid for sid, s in data.std.items() if s.get("사용여부", True)]
    parts: dict[str, tuple] = {}
    out: dict[tuple, dict[str, Any]] = {}
    for uw in rep["uws"]:
        matched = [v for v in vids if _uw_match(data.variants[v], uw["spec"])]
        bases = [v for v in matched if data.variants[v]["기관코드"] == HOME_ORG]
        peers = [v for v in matched if data.variants[v]["기관코드"] != HOME_ORG]
        for base in bases:
            for peer in peers:
                for vid in (base, peer):
                    if vid not in parts:
                        parts[vid] = compare.collect(data, vid)
                for sex in rep["sexes"]:
                    cond = Cond(age=rep["age"], sex=sex)
                    for sid in stds:
                        cores = {vid: compare.cell_core(data, parts[vid][0].get(sid, []), cond, bool(parts[vid][1].get(sid)))
                                 for vid in (base, peer)}
                        code = compare.verdict(cores[peer], cores[base])
                        key = (uw["label"], _line(data.variants[base]), _line(data.variants[peer]), sid, sex)
                        out.setdefault(key, {"code": code, "base": base, "peer": peer,
                                             "baseRev": data.variants[base].get("개정판ID"),
                                             "peerRev": data.variants[peer].get("개정판ID"),
                                             "baseTerms": _terms(cores[base]), "peerTerms": _terms(cores[peer])})
    return out


def shift_kind(old: dict[str, Any], cur: dict[str, Any]) -> tuple[str, tuple[bool, bool]]:
    """판정 첫 글자가 바뀐 담보 하나를 가른다: ("resolved" | "change" | "correction", (기준 쪽 개정, 비교 쪽 개정)).

    한쪽이 개정됐다는 것은 그쪽 개정판ID가 바뀌었고 그 담보의 판정 값도 달라졌다는 뜻이다.
    개정판ID만 바뀌고 이 담보 값이 그대로면, 판정이 바뀐 까닭은 그 개정이 아니라 다른 쪽 값의 정정이다.
    """
    if old["code"][:1] in REVIEW_CODES and cur["code"][:1] not in REVIEW_CODES:
        return "resolved", (False, False)
    revised = (cur["baseRev"] != old["baseRev"] and cur["baseTerms"] != old["baseTerms"],
               cur["peerRev"] != old["peerRev"] and cur["peerTerms"] != old["peerTerms"])
    return ("change" if any(revised) else "correction"), revised


def shifts(data: Data, previous: Data | None) -> dict[str, Any]:
    """changes는 화면 1에 싣는 개정 변화, corrections는 자료 정정 건수(화면 6), resolved는 검토가 끝나 판정이 생긴 건수.
    건수는 성별만 다른 대표 조건을 한 건으로 묶어 센다."""
    rep = rep_conditions(data)
    out: dict[str, Any] = {"rep": rep, "available": previous is not None, "changes": [], "corrections": 0, "resolved": 0,
                           "pairs": 0, "newPairs": 0, "gonePairs": 0, "previousAt": None}
    if previous is None or rep["age"] is None or not rep["sexes"]:
        return out
    now, before = rep_verdicts(data, rep), rep_verdicts(previous, rep)
    pair = lambda key: key[:3]
    now_pairs, before_pairs = {pair(k) for k in now}, {pair(k) for k in before}
    groups: dict[tuple, dict[str, Any]] = {}
    for key, cur in now.items():
        old = before.get(key)
        if old is None or cur["code"][:1] == old["code"][:1]:
            continue
        kind, revised = shift_kind(old, cur)
        uw, _, _, sid, sex = key
        group_key = (pair(key), sid, old["code"][:1], cur["code"][:1], kind, revised)
        group = groups.get(group_key)
        if group is None:
            prev_base, prev_peer = previous.variants[old["base"]], previous.variants[old["peer"]]
            group = groups[group_key] = {
                "std": sid, "uw": uw, "sexes": [], "base": cur["base"], "peer": cur["peer"],
                "before": old["code"], "after": cur["code"], "baseRevised": revised[0], "peerRevised": revised[1],
                "prev": {"base": {"rev": old["baseRev"], "name": prev_base.get("공시상품명")},
                         "peer": {"rev": old["peerRev"], "name": prev_peer.get("공시상품명")}},
            }
        group["sexes"].append(sex)
    std_order = {sid: i for i, sid in enumerate(data.std)}
    for group_key, group in sorted(groups.items(), key=lambda kv: (kv[1]["uw"], kv[1]["base"], kv[1]["peer"],
                                                                   std_order.get(kv[1]["std"], 0))):
        kind = group_key[4]
        if kind == "change":
            out["changes"].append(group)
        elif kind == "resolved":
            out["resolved"] += 1                         # 지난주에는 검토 대기라 판정하지 않았음
        else:
            out["corrections"] += 1                      # 개정이 아닌데 판정이 바뀜: 자료 정정(화면 6)
    out.update(pairs=len(now_pairs & before_pairs), newPairs=len(now_pairs - before_pairs),
               gonePairs=len(before_pairs - now_pairs), previousAt=previous.meta.get("snapshot_at"))
    return out


def build(data: Data, previous: Data | None = None) -> dict[str, Any]:
    week = week_of(data.meta.get("snapshot_at"))
    return {"week": week, "revisions": revision_events(data, week), "news": news(data, week), "shifts": shifts(data, previous)}
