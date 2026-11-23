"""사본 자료를 읽어 화면들이 함께 쓰는 구조로 묶는다.

여기서 정하는 것
- 급부의 표준담보: hum_담보매핑의 확정표준담보ID (검토상태가 자동확정·승인·수정인 행만)
- 검토 대기 표시: sys_작업로그에서 작업단계가 "사람검토이관"인 행의 대상행ID
- 나이·성별 조건 구간과 그 구간의 가입 한도
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import config
from ..extract import rerun as R
from ..snapshot import read_snapshot

HOME_ORG = "EPOST"                       # 이 앱의 관점이 되는 기관
CONFIRMED_STATES = {"자동확정", "승인", "수정"}
WAITING_STATE = "대기"
EXCLUDED_STATE = "대상외"
REVIEW_STEP = "사람검토이관"
JUDGE_STEPS = {"판정", REVIEW_STEP}
# 우열 판정에 쓰는 열. 이 열이 검토 대기면 판정을 미룬다.
VERDICT_COLUMNS = {"기준가입금액만원", "기준지급금액만원", "면책기간일수",
                   "감액개월1", "감액지급률1", "감액개월2", "감액지급률2"}
ROLE_ORDER = {"주급부": 0, "대등복합": 1, "부수급부": 2}
MAIN_KIND = "주계약"
MAX_AGE = 120                            # 나이 입력의 상한
# sys_급부의 선택 열. 금액이 아니라 가입금액 대비 지급률로 적힌 급부(삼성화재 요약서)는 "가입금액비율"이고,
# 기준가입금액만원 100, 기준지급금액만원 = 지급률(%)로 적는다. 열이 없거나 비어 있으면 "금액"으로 본다.
BASIS_COLUMN = "지급기준구분"
RATIO_BASIS = "가입금액비율"
# meta.json 의 선택 열쇠(가상 사본이 싣는다): 기관코드 → 기관 이름, 기관코드 → 업권
META_NAMES, META_SECTORS = "기관이름", "기관업권"
SECTOR_LIFE, SECTOR_NONLIFE = "생명보험", "손해보험"


@dataclass(frozen=True)
class Cond:
    """고른 조건. age가 None이면 나이 조건 없음."""
    age: int | None = None
    sex: str | None = None
    lo: int | None = None
    hi: int | None = None


@dataclass(frozen=True)
class Limit:
    """어떤 조건에서 한 특약(주계약)에 가입할 수 있는지와 가입 한도."""
    ok: bool
    amount: float | None = None          # 만 원. 가입할 수 있어도 금액 자료가 없으면 None
    pending: bool = False                # 한도를 정한 조건행이 검토 대기인지
    no_data: bool = False                # 가입나이 자료가 아예 없어 나이를 따지지 못함


def _blank(value: Any) -> bool:
    return value is None or value == ""


def _columns(text: Any) -> list[str]:
    """작업로그의 대상열. "감액개월1, 지급횟수제한"처럼 여러 열이 함께 적히기도 한다."""
    return [c.strip() for c in str(text or "").split(",") if c.strip()]


def is_ratio(row: dict[str, Any]) -> bool:
    """가입금액 대비 비율로 적힌 급부인지. 지급기준구분 열이 없거나 비어 있거나 "금액"이면 금액 급부다."""
    return str(row.get(BASIS_COLUMN) or "").strip() == RATIO_BASIS


def pay_rate(pay: float | None, base: float | None) -> float | None:
    """가입금액 대비 지급률(%). 기준지급금액 ÷ 기준가입금액 × 100. 화면 표기에만 쓰고, 환산은 지금 식(compare.scaled) 그대로다."""
    if pay is None or not base:
        return None
    return round(pay * 100 / base, 6)


class Data:
    def __init__(self, tables: dict[str, list[dict[str, Any]]], meta: dict[str, Any] | None = None):
        self.tables = {name: list(rows) for name, rows in tables.items()}
        self.meta = meta or {}
        t = lambda name: self.tables.get(name, [])

        self.variants = {r["종형ID"]: r for r in t("sys_상품종형")}
        self.variant_order = sorted(self.variants, key=self._variant_sort_key)
        self.riders = {r["특약ID"]: r for r in t("sys_특약")}
        self.benefits = {r["급부ID"]: r for r in t("sys_급부")}
        self.mapping = {r["급부ID"]: r for r in t("hum_담보매핑")}
        self.std = {r["표준담보ID"]: r for r in t("hum_표준담보사전")}
        self.settings = {r["기준키"]: r for r in t("hum_기준값")}
        self.logs = t("sys_작업로그")
        self.trends = t("sys_시장동향")
        self.conditions = {r["조건행ID"]: r for r in t("sys_가입조건")}

        self.riders_of: dict[str, list[str]] = {v: [] for v in self.variants}
        for tid, r in self.riders.items():
            self.riders_of.setdefault(r["종형ID"], []).append(tid)
        for vid, tids in self.riders_of.items():
            tids.sort(key=lambda x: (self.riders[x]["담보구분"] != MAIN_KIND, str(self.riders[x]["원시특약명"])))

        self.benefits_of: dict[str, list[str]] = {}
        for bid, b in self.benefits.items():
            self.benefits_of.setdefault(b["특약ID"], []).append(bid)
        for bids in self.benefits_of.values():
            bids.sort(key=lambda x: (ROLE_ORDER.get(self.benefits[x]["급부역할"], 9),
                                     -(self.benefits[x]["기준지급금액만원"] or 0), str(self.benefits[x]["원시급부명"])))

        self.cond_rows_of_rider: dict[str, list[dict]] = {}
        self.cond_rows_of_main: dict[str, list[dict]] = {}
        for r in t("sys_가입조건"):
            if _blank(r.get("특약ID")):
                self.cond_rows_of_main.setdefault(r["종형ID"], []).append(r)
            else:
                self.cond_rows_of_rider.setdefault(r["특약ID"], []).append(r)

        self.constraints_of: dict[str, list[dict]] = {}
        for r in sorted(t("sys_결합제약"), key=lambda r: str(r["제약ID"])):
            self.constraints_of.setdefault(r["종형ID"], []).append(r)

        self.pending_benefit, self.pending_condition = self._pending()

    # ---- 종형 ----
    def _variant_sort_key(self, vid: str):
        """우리 기관 먼저, 판매 중인 종형 먼저, 최근 개정판 먼저."""
        v = self.variants[vid]
        started = int(str(v.get("적용시작일") or "0").replace("-", "") or 0)
        return (v.get("기관코드") != HOME_ORG, str(v.get("기관코드")), not _blank(v.get("판매종료일")),
                -started, str(v.get("공시상품명")), str(v.get("종형명")))

    def org_name(self, code: str) -> str:
        """기관 이름. 사본의 meta.json 에 이름 표(기관이름)가 있으면 먼저 읽고(가상 사본. scripts/dev/make_synthetic_snapshot.py),
        없으면 config 의 기관 표다. 실제 사본에는 이름 표가 없어 config 그대로다."""
        names = self.meta.get(META_NAMES)
        if isinstance(names, dict) and code in names:
            return str(names[code])
        return {**config.INSTITUTIONS, **config.COMMON}.get(code, code)

    def org_sector(self, code: str) -> str | None:
        """기관의 업권(SECTOR_LIFE, SECTOR_NONLIFE). meta.json 의 기관업권을 먼저 읽고, 없으면 config 의 생명보험(LIFE),
        손해보험(NONLIFE) 표에서 찾는다. 어디에도 없으면(우체국, 모르는 기관) None 이다. 지어내지 않는다."""
        sectors = self.meta.get(META_SECTORS)
        if isinstance(sectors, dict) and sectors.get(code) in (SECTOR_LIFE, SECTOR_NONLIFE):
            return sectors[code]
        if code in config.LIFE:
            return SECTOR_LIFE
        if code in config.NONLIFE:
            return SECTOR_NONLIFE
        return None

    def main_rider(self, vid: str) -> str | None:
        for tid in self.riders_of.get(vid, []):
            if self.riders[tid]["담보구분"] == MAIN_KIND:
                return tid
        return None

    def variant_of_rider(self, tid: str) -> str:
        return self.riders[tid]["종형ID"]

    def limit_gap(self, vid: str) -> dict[str, Any] | None:
        """가입 한도·가입 나이 자료가 비어 있는 종형인지. 빠진 것이 없으면 None.

        공시 문서에 특약 가입 한도가 없는 회사(한화생명)는 "최대 가입 시 지급액"을 계산할 수 없다.
        화면은 이 표시를 보고 그 사실을 알리고, 기준 가입금액 기준 지급액과 조건만 보여 준다.
        riders는 주계약을 포함한 특약 수, noMax는 그 가운데 최대 가입금액이 없는 수, noAge는 주계약 가입 나이 자료가 없는지.
        """
        tids = self.riders_of.get(vid, [])
        no_max = sum(1 for t in tids if self.rider_cap(t, Cond()).amount is None)
        main = self.main_rider(vid)
        no_age = not (main and self.condition_rows(main))
        if not no_max and not no_age:
            return None
        return {"riders": len(tids), "noMax": no_max, "noAge": no_age}

    # ---- 기준값 ----
    def setting_num(self, key: str, default: float | None = None) -> float | None:
        row = self.settings.get(key)
        return row["수치값"] if row and row.get("수치값") is not None else default

    def setting_text(self, key: str, default: str = "") -> str:
        row = self.settings.get(key)
        return row["문자값"] if row and row.get("문자값") else default

    # ---- 검토 대기 ----
    def _pending(self) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """사람 검토를 기다리는 급부와 조건행, 그리고 어느 열이 대기인지.

        - 같은 행을 여러 번 실행했으면 가장 나중 실행의 판정만 본다.
        - 급부: extract/rerun.py의 waiting_rows와 같은 규칙이다(재추출이 검토 대기 줄을 가릴 때도 쓴다). 자기 급부ID에 판정 기록이
          있는 줄은 자기 기록만 본다. 예전 실행은 요약서를 함께 쓰는 종 가운데 첫 종의 행에만 기록을 남겼으므로, 자기 기록이 없는 줄은
          같은 요약서(요약서해시)를 쓰는 다른 종의 같은 급부 기록을 옮겨 본다. 종마다 기록을 남긴 실행의 기록은 옮기지 않는다
          (그 실행이 쓴 줄에는 자기 기록이 있다. 자기 기록이 없는 줄은 그 실행이 손대지 않았거나 이전 줄을 그대로 지킨 줄이다).
        - 조건행도 한 항목이 여러 행을 만들고 기록은 첫 행에만 남는다. 같은 사업방법서를 쓰는 종형에서
          특약·나이 구간·한도가 같은 행에 표시를 옮긴다.
        """
        latest: dict[tuple[str, str], str] = {}
        for r in self.logs:
            if r.get("작업단계") in JUDGE_STEPS:
                key = (r.get("대상탭"), r.get("대상행ID"))
                latest[key] = max(latest.get(key, ""), str(r.get("실행일시") or ""))
        found: dict[str, dict[str, set[str]]] = {"sys_가입조건": {}}
        for r in self.logs:
            tab, target = r.get("대상탭"), r.get("대상행ID")
            if r.get("작업단계") != REVIEW_STEP or tab not in found:
                continue
            if str(r.get("실행일시") or "") != latest.get((tab, target)):
                continue
            found[tab].setdefault(target, set()).update(_columns(r.get("대상열")) or ["값"])

        judged = [r for r in self.logs if r.get("대상탭") == "sys_급부" and r.get("작업단계") in JUDGE_STEPS]
        rows = {bid: self.riders[b["특약ID"]]["종형ID"] if b["특약ID"] in self.riders else None for bid, b in self.benefits.items()}
        benefit: dict[str, set[str]] = {}
        for bid, review in R.waiting_rows(rows, judged, R.sharing_of(self.variants.values()), R.per_variant_runs(self.logs)).items():
            for r in review:
                benefit.setdefault(bid, set()).update(_columns(r.get("대상열")) or ["값"])

        condition: dict[str, set[str]] = {}
        same_method: dict[str, list[str]] = {}
        for vid, v in self.variants.items():
            if not _blank(v.get("사업방법서해시")):
                same_method.setdefault(v["사업방법서해시"], []).append(vid)
        for cid, cols in found["sys_가입조건"].items():
            row = self.conditions.get(cid)
            if row is None:
                continue
            group = set(same_method.get(self.variants.get(row["종형ID"], {}).get("사업방법서해시"), [])) | {row["종형ID"]}
            sign = self._condition_sign(row)
            for other_id, other in self.conditions.items():
                if other["종형ID"] in group and self._condition_sign(other) == sign:
                    condition.setdefault(other_id, set()).update(cols)
        return ({k: sorted(v) for k, v in benefit.items()}, {k: sorted(v) for k, v in condition.items()})

    def _condition_sign(self, row: dict) -> tuple:
        rider = self.riders.get(row.get("특약ID")) if not _blank(row.get("특약ID")) else None
        return (rider["특약계보키"] if rider else MAIN_KIND, row.get("최저가입나이"), row.get("최고가입나이"),
                row.get("구간최대가입금액만원"))

    # ---- 급부 ----
    def benefit_view(self, bid: str) -> dict[str, Any]:
        """급부 한 줄을 화면이 쓰는 꼴로. std는 확정된 표준담보만 담는다.

        ratio는 가입금액 대비 비율로 적힌 급부인지, rate는 그 지급률(%)이다. 금액 급부의 rate는 None이다.
        화면은 비율 급부를 "기준 가입 100만원에 50만원" 대신 "가입금액의 50%"로 적는다.
        """
        b = self.benefits[bid]
        ratio = is_ratio(b)
        m = self.mapping.get(bid)
        state = m["검토상태"] if m else "매핑 없음"
        std = m.get("확정표준담보ID") if m and state in CONFIRMED_STATES else None
        if std and (std not in self.std or not self.std[std].get("사용여부", True)):
            std = None
        reduce = [[b[f"감액개월{i}"], b[f"감액지급률{i}"]] for i in (1, 2)
                  if b.get(f"감액개월{i}") is not None and b.get(f"감액지급률{i}") is not None]
        return {
            "id": bid, "tid": b["특약ID"], "name": b["원시급부명"], "role": b["급부역할"],
            "base": b.get("기준가입금액만원"), "pay": b.get("기준지급금액만원"),
            "limit": b.get("지급횟수제한"), "wait": b.get("면책기간일수") or 0, "red": reduce,
            "exc": b.get("감액예외") or None,
            "doc": b.get("근거문서종류"), "page": b.get("근거문서쪽수"),
            "state": state, "prob": m.get("매핑확률") if m else None,
            "std": std, "rec": (m.get("추천표준담보ID") if m and state == WAITING_STATE else None),
            "pend": self.pending_benefit.get(bid, []),
            "ratio": ratio, "rate": pay_rate(b.get("기준지급금액만원"), b.get("기준가입금액만원")) if ratio else None,
        }

    def verdict_pending(self, view: dict[str, Any]) -> bool:
        return bool(VERDICT_COLUMNS & set(view["pend"]))

    # ---- 나이·성별 조건 ----
    def condition_rows(self, tid: str) -> list[dict]:
        rider = self.riders[tid]
        rows = list(self.cond_rows_of_rider.get(tid, []))
        if rider["담보구분"] == MAIN_KIND:
            rows += self.cond_rows_of_main.get(rider["종형ID"], [])
        return rows

    def age_limit(self, tid: str, cond: Cond) -> Limit:
        """나이·성별 조건에서 이 특약(주계약)의 가입 가능 여부와 한도. 다른 특약과의 연동은 따지지 않는다."""
        rider = self.riders[tid]
        top = rider.get("최대가입금액만원")
        rows = self.condition_rows(tid)
        if cond.age is None:
            return Limit(True, top, no_data=not rows)
        if not rows:
            return Limit(True, top, no_data=True)
        hit = [r for r in rows if r["최저가입나이"] <= cond.age <= r["최고가입나이"]
               and (_blank(r.get("성별")) or r.get("성별") == cond.sex)]
        if not hit:
            return Limit(False)
        amounts = [(r["구간최대가입금액만원"] if r.get("구간최대가입금액만원") is not None else top, r) for r in hit]
        known = [(a, r) for a, r in amounts if a is not None]
        if not known:
            return Limit(True, None, pending=any(r["조건행ID"] in self.pending_condition for r in hit))
        best = max(a for a, _ in known)
        return Limit(True, best, pending=any(r["조건행ID"] in self.pending_condition for a, r in known if a == best))

    def rider_cap(self, tid: str, cond: Cond) -> Limit:
        """이 특약을 최대로 가입할 때의 가입금액. 나이 구간 한도에 주계약 연동(최대연동)을 함께 건다.

        주계약에 가입할 수 없는 나이면 특약도 가입할 수 없다.
        """
        own = self.age_limit(tid, cond)
        rider = self.riders[tid]
        vid = rider["종형ID"]
        main = self.main_rider(vid)
        if rider["담보구분"] == MAIN_KIND or not own.ok:
            return own
        if main is not None and not self.age_limit(main, cond).ok:
            return Limit(False)
        amount, pending = own.amount, own.pending
        for rule in self.constraints_of.get(vid, []):
            if rule["대상특약ID"] != tid or rule["제약유형"] != "최대연동" or rule["기준특약ID"] not in self.riders:
                continue
            base = self.rider_cap(rule["기준특약ID"], cond) if rule["기준특약ID"] != tid else Limit(False)
            if not base.ok:
                return Limit(False)
            ceiling = link_ceiling(rule, base.amount)
            if ceiling is not None and (amount is None or ceiling < amount):
                amount, pending = ceiling, base.pending
        return Limit(True, amount, pending, own.no_data)

    def age_edges(self) -> list[int]:
        edges = set()
        for r in self.tables.get("sys_가입조건", []):
            edges.add(int(r["최저가입나이"]))
            edges.add(int(r["최고가입나이"]) + 1)
        return sorted(e for e in edges if 0 <= e <= MAX_AGE)

    def has_sex_rows(self) -> bool:
        return any(not _blank(r.get("성별")) for r in self.tables.get("sys_가입조건", []))

    def conds(self) -> list[Cond]:
        """화면이 고를 수 있는 조건을 구간으로 나눈 목록. 0번은 나이 조건 없음.

        가입조건이 바뀌는 나이마다 구간을 끊으므로 한 구간 안에서는 어느 나이든 결과가 같다.
        """
        out = [Cond()]
        cuts = [0] + [e for e in self.age_edges() if e > 0] + [MAX_AGE + 1]
        for lo, nxt in zip(cuts, cuts[1:]):
            for sex in ("M", "F"):
                out.append(Cond(age=lo, sex=sex, lo=lo, hi=nxt - 1))
        return out


def link_ceiling(rule: dict, base_amount: float | None) -> float | None:
    """최대연동 제약이 허용하는 가입금액 상한. 단위가 비율이면 기준 특약 가입금액의 배수, 만원이면 그 금액."""
    number = rule.get("제약수치")
    if number is None:
        return base_amount
    if rule.get("제약단위") == "만원":
        return float(number)
    return None if base_amount is None else base_amount * float(number)


def load(snapshot_dir: Path) -> Data:
    snapshot_dir = Path(snapshot_dir)
    meta_path = snapshot_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return Data(read_snapshot(snapshot_dir), meta)
