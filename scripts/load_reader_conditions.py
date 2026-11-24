r"""초기 적재의 두 판독(교차 확인)이 판정을 마친 주계약 가입조건을, 판정 모델 없이 시트에 쓴다. 첫 회사는 메리츠화재다.

두 판독자(sonnet, opus)가 사업방법서의 가입나이 표를 따로 읽고, 코드가 둘을 견주고 그 쪽의 글자와 대조해
(scripts/compare_condition_readers.py), 메인 세션이 판정을 마친 값을 값 파일(data/crosscheck/<회사>_main_conditions_2reader.jsonl,
꼴은 data/crosscheck/README.md)에 둔다. 이 스크립트는 그 값으로 sys_가입조건 행을 만든다. 범위는 주계약뿐이다.

1. 대상 설정과 공시 수집 결과(index.json)로 종형을 만든다(variants.build). 정밀비교 종형과 관문전용 종형을 모두 본다.
2. 종형마다 값 파일의 줄을 찾아 판정이 끝난 값(reader_conditions.final_value)을 고른다. 판정이 비었거나 검토 대기면 쓰지 않는다.
3. 받은 사업방법서 PDF에서 그 값이 가리키는 쪽의 글자를 다시 뽑아 기계 검사(reader_conditions.machine_checks, title_marks)를
   돌린다. 문제가 하나라도 나오거나, 판정할 때 없던 표시가 새로 나오면 그 종형은 쓰지 않는다.
4. 화면의 가입 관문 계산은 주계약 특약 행으로 가입나이를 찾는다(site/model.py main_rider). 종형마다 시트에 주계약 행
   (담보구분이 주계약)이 있는지 보고, 없으면 쓴다.
   - 관문전용 종형: variants.main_row(원시특약명 "주계약"). job._run_gate와 같은 행이다.
   - 정밀비교 종형: 급부 적재(scripts/load_reader_product.py)가 쓰는 주계약 행과 같은 행. 요약서 급부 표를 다시 읽어
     reader_rows.build_rows가 만드는 특약 행 가운데 담보구분이 주계약인 행을 쓴다(특약ID가 같다).
   주계약 행의 이름(요약서 기본계약 표의 이름. 관문전용은 "주계약")과 사업방법서 가입나이 표의 기본계약 이름은 글자가 다를 수 있다
   ("일반상해사망(통합간편가입)"과 "기본계약(일반상해사망(통합간편가입)보장)"). 둘이 conditions.near_main으로 겹치지 않으면
   다른 계약의 표를 읽은 것일 수 있으므로 그 종형은 쓰지 않는다. 시트에 종형 행이 없으면 종형 행도 쓴다.
5. 행은 reader_conditions.build_rows로 만든다(조건행ID 규칙은 conditions.build_rows 그대로. 주계약 행이라 특약ID는 비운다).

시트 쓰기와 작업 로그는 기존 가입조건 적재(job._run_main)와 같다. 행을 만든 종형의 sys_가입조건만 바꾸고, 그 종형의 특약
가입조건 행(특약ID가 있는 행)은 그대로 둔다. 다른 종형의 행과 sys_결합제약은 건드리지 않는다. 가입조건 행마다 "판정 통과"를,
쓰지 않은 종형마다 "코드대조 반려"를 남긴다. 호출모델은 "교차 확인", 판정확률은 비운다. 형식 검사에 걸린 가입조건 행은 그 행만
빼고 쓴다. 주계약 행이나 종형 행에 형식 오류가 있거나 ID가 겹치면 아무것도 쓰지 않는다.

  python scripts/load_reader_conditions.py --docs out --result result/conditions.json                 # 시트에 쓴다
  python scripts/load_reader_conditions.py --docs out --dry-run --result r.json --rows rows.json      # 쓰지 않고 행과 요약만 낸다
  python scripts/load_reader_conditions.py --docs out --seed-rows benefit_rows.json --result r.json    # 급부 적재 결과를 시트 삼아 본다(쓰지 않음)

--docs는 scripts/fetch_disclosure.py --org meritz의 결과 폴더다(index.json과 <저장이름>.pdf). 시트 접속 정보가 없어도 --dry-run은
끝까지 돈다(빈 시트로 본다). --seed-rows에는 load_reader_product.py --rows의 결과물을 준다(그 행을 쓴 뒤의 시트로 본다).
--result와 --rows에는 문서의 문장을 싣지 않는다(숫자, 기간 글자, 특약 이름, 사유의 앞머리만).

행 패키지(src/postlife/extract/row_package.py). Actions 러너에서 공시실 접속이 막히는 회사(삼성생명, KB라이프생명)는 로컬에서
받은 문서로 종형마다 기계 검사를 마치고 가입조건 행을 만들어(prepare) 패키지로 커밋한다. 주계약 행을 고르는 일은 쓸 때의 시트에
달렸으므로 패키지에는 사업방법서 가입나이 표의 기본계약 이름과 주계약 후보 행(요약서 표에서 만든 주계약 특약 행, 관문전용은
"주계약" 행)을 담고, 읽는 길이 기존 길과 같은 finish로 고른다. 급부 패키지를 먼저 쓰면 시트에 주계약 행이 생겨 그 행을 쓴다.

  python scripts/load_reader_conditions.py --docs out --org kblife --targets data/targets/kblife.json \
      --rows-out data/backfill_rows/kblife_conditions.json                                      # 로컬: 패키지 만들기(쓰지 않음)
  python scripts/load_reader_conditions.py --rows-in data/backfill_rows/kblife_conditions.json --org kblife \
      --targets data/targets/kblife.json --result r.json                                        # Actions: 패키지로 시트에 쓰기
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import load_reader_product as L  # noqa: E402  스크립트 폴더는 실행할 때 sys.path에 들어 있다
from load_table_product import snapshot_store  # noqa: E402
from postlife import ids  # noqa: E402
from postlife.extract import conditions as C  # noqa: E402
from postlife.extract import job, tables, variants  # noqa: E402
from postlife.extract import reader_conditions as RC  # noqa: E402
from postlife.extract import reader_rows as RR  # noqa: E402
from postlife.extract import row_package as P  # noqa: E402
from postlife.extract.segment import pages_from_text  # noqa: E402
from postlife.sheets_io import MemoryBackend, SheetStore  # noqa: E402
from postlife.snapshot import KST  # noqa: E402
from postlife.validate import check_rows  # noqa: E402
from postlife.worklog import WorkLog  # noqa: E402

MODEL = "교차 확인"                 # sys_작업로그의 호출모델
READERS = ("sonnet", "opus")
TAB = "sys_가입조건"
TARGETS = ROOT / "data" / "targets" / "meritz.json"
CROSSCHECK = ROOT / "data" / "crosscheck"

# 쓰지 않은 종형의 사유(앞머리)
NO_VALUE = "값 파일에 없음"
WAITING = "판정이 끝나지 않음"
NO_METHOD = "사업방법서가 없음"
CHECK = "기계 검사"
NEW_MARK = "기계 검사 표시"
NAME = "주계약 이름이 맞지 않음"
NO_MAIN = "주계약 행을 정하지 못함"
NO_ROWS = "가입조건 행이 나오지 않음"

_MAIN_HEAD = re.compile(r"[·∙•ㆍ]\s*기본계약\s*\(")


@dataclass
class Loaded(job.Report):
    counts: dict[str, dict[str, Any]] = field(default_factory=dict)      # 종형ID → 종형별 요약
    skipped: dict[str, str] = field(default_factory=dict)                # 종형ID → 쓰지 않은 사유
    new_mains: list[dict[str, Any]] = field(default_factory=list)        # 새로 쓰는 주계약 특약 행
    new_variants: list[dict[str, Any]] = field(default_factory=list)     # 시트에 없어 새로 쓰는 종형 행
    kept: list[dict[str, Any]] = field(default_factory=list)             # 그대로 두는 그 종형의 특약 가입조건 행
    clashes: dict[str, list[str]] = field(default_factory=dict)          # 탭 → 겹친 ID
    dropped: int = 0                                                     # 시트에 있었는데 이번에 빠지는 주계약 가입조건 행


def value_lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_pages(docs: Path, stem: str, wanted: Iterable[int]) -> dict[int, str]:
    """받은 문서에서 쪽 글자를 다시 뽑는다. PDF가 있으면 PDF에서(fetch_disclosure.py와 같은 pdfplumber extract_text),
    없으면 같은 이름의 글자 파일에서. 둘 다 없으면 빈 사전."""
    pdf = docs / f"{stem}.pdf"
    wanted = sorted(set(wanted))
    if pdf.exists():
        with tables._open(pdf) as doc:
            return {n: doc.pages[n - 1].extract_text() or "" for n in wanted if 1 <= n <= len(doc.pages)}
    text = docs / f"{stem}.txt"
    if text.exists():
        pages = pages_from_text(text.read_text(encoding="utf-8"))
        return {n: pages[n] for n in wanted if n in pages}
    return {}


def method_pages_needed(value: Mapping[str, Any]) -> set[int]:
    """기계 검사가 사업방법서에서 볼 쪽: 근거쪽, 줄의 쪽, 그 사이의 쪽, 사업방법서 한도의 쪽."""
    head = value["근거쪽"]
    lines = [x["쪽"] for x in value.get("줄") or []]
    out = {head, *lines}
    if lines:
        out |= set(range(min(head, max(lines)), max(head, max(lines)) + 1))
    out |= {x["쪽"] for x in value.get("한도") or [] if x.get("문서") == "사업방법서"}
    return out


def method_main_name(pages: Mapping[int, str], first: int, last: int) -> str | None:
    """사업방법서 가입나이 표의 기본계약 이름. "·기본계약(일반상해사망(통합간편가입)보장) 90세만기 …" → 괄호 안의 이름.
    first~last쪽에서 처음 나오는 줄을 본다. 괄호가 닫히지 않거나 그런 줄이 없으면 None."""
    for n in range(min(first, last), max(first, last) + 1):
        for line in (pages.get(n) or "").split("\n"):
            m = _MAIN_HEAD.search(line)
            if not m:
                continue
            depth, start = 1, m.end()
            for i in range(start, len(line)):
                depth += {"(": 1, ")": -1}.get(line[i], 0)
                if depth == 0:
                    return line[start:i].strip() or None
            return None
    return None


def names_match(rider_name: str, method_name: str | None) -> bool:
    """주계약 행의 이름이 사업방법서 기본계약 이름과 같은 계약을 가리키는가. 관문전용의 "주계약"은 이름을 보지 않는다."""
    if ids.normalize(rider_name) in ("주계약", "기본계약"):
        return True
    return bool(method_name) and C.near_main(method_name, [rider_name])


def accepted_marks(line: Mapping[str, Any]) -> set[str]:
    """판정할 때 이미 보였던 기계 검사 표시. 메인 세션이 보고 판정을 마쳤으므로 다시 나와도 막지 않는다."""
    return {m for name in READERS for m in ((line.get("기계검사") or {}).get(name) or {}).get("표시") or []}


class Summaries:
    """정밀비교 종형의 주계약 행을 급부 적재와 같은 길로 만든다. 같은 요약서는 한 번만 읽는다."""

    def __init__(self, docs: Path, targets: Mapping[str, Any], layout: L.Layout):
        self.docs, self.layout = docs, layout
        self.product = L.products_of(targets)
        self.kinds = L.kinds_of(targets)
        self.read: dict[str, tuple[list[RR.PieceView], dict[int, str]] | None] = {}

    def mains(self, v: variants.Variant) -> list[dict[str, Any]] | None:
        """그 종형의 주계약 특약 행 목록(reader_rows.build_rows가 만드는 특약 행 가운데 담보구분이 주계약인 행). 요약서가 없으면 None."""
        if not (v.summary and v.summary.get("해시")):
            return None
        key = v.summary["해시"]
        if key not in self.read:
            pdf = self.docs / f"{v.summary['저장이름']}.pdf"
            self.read[key] = L.read_pieces(pdf, self.layout) if pdf.exists() else None
        if self.read[key] is None:
            return None
        pieces, pages = self.read[key]
        name = v.row["종형명"]
        mine, _, _ = L.variant_pieces(pieces, name, self.layout, self.kinds.get((v.row["공시상품코드"], name)))
        settings = self.product[(v.row["공시상품코드"], name)]
        banned = [x["특약명"] for x in settings.get("갱신형특약제외") or []]
        built = RR.build_rows(v.id, mine, {}, L.renewal_years(mine, v.plain_renewal_years, banned), pages)
        L.main_renewal(built.riders, v)
        return [r for r in built.riders if r["담보구분"] == "주계약"]


@dataclass
class Ready:
    """문서 단계를 마친 종형 하나. 시트를 보지 않고 정할 수 있는 것만 담는다(가입조건 행 패키지의 종형 한 줄)."""
    종형ID: str
    종형행: dict[str, Any]                    # 시트에 종형 행이 없으면 쓰는 행
    관문전용: bool
    판정: str | None                           # 값 파일 줄의 판정(줄이 없으면 None)
    건너뜀: str | None = None                  # 문서 단계에서 쓰지 않기로 한 사유
    앞주의: list[str] = field(default_factory=list)      # 문서 단계의 주의(받은 사업방법서 해시가 다름 따위)
    근거쪽: int | None = None
    기본계약이름: str | None = None            # 사업방법서 가입나이 표의 기본계약 이름(주계약 행 이름과 맞춰 본다)
    가입조건: list[dict[str, Any]] = field(default_factory=list)
    행주의: list[str] = field(default_factory=list)      # 가입조건 행 만들기의 주의(reader_conditions.build_rows)
    주계약후보: list[dict[str, Any]] | None = None       # 시트에 주계약 행이 없을 때 쓸 행. None이면 요약서가 없어 정하지 못함
    _mains: Any = field(default=None, repr=False, compare=False)   # 주계약후보를 처음 찾을 때 부르는 함수(요약서 읽기)

    def candidates(self) -> list[dict[str, Any]] | None:
        if self._mains is not None:
            self.주계약후보, self._mains = self._mains(), None
        return self.주계약후보

    def as_package(self) -> dict[str, Any]:
        self.candidates()
        return {k: copy.deepcopy(v) for k, v in self.__dict__.items() if not k.startswith("_")}


@dataclass
class Prepared:
    notes: list[str] = field(default_factory=list)
    ready: list[Ready] = field(default_factory=list)


def load(store: SheetStore, targets: dict[str, Any], index: list[dict[str, Any]], docs: Path, values: Path,
         now: datetime, dry_run: bool = False, only: Sequence[str] | None = None,
         layout: L.Layout = tables.MERITZ) -> Loaded:
    """문서로 종형마다 가입조건 행을 만드는 단계(prepare)와 시트에 맞춰 쓰는 단계(finish)로 나뉜다. 행 패키지(--rows-out)는
    prepare의 결과이고, 패키지로 쓰는 길(--rows-in)은 prepare 대신 패키지를 읽어 같은 finish를 거친다."""
    return finish(store, prepare(targets, index, docs, values, only, layout), now, dry_run)


def prepare(targets: dict[str, Any], index: list[dict[str, Any]], docs: Path, values: Path,
            only: Sequence[str] | None = None, layout: L.Layout = tables.MERITZ) -> Prepared:
    """값 파일의 판정 값을 받은 사업방법서 쪽 글자로 기계 검사하고 가입조건 행을 만든다. 시트를 읽지 않는다.
    주계약 행 고르기(시트에 주계약 행이 있는지에 달림)는 finish가 한다. 그때 쓸 기본계약 이름과 주계약 후보 행을 담아 둔다."""
    out = Prepared()
    found, problems = variants.build(targets, index)
    out.notes += problems
    if only:
        found = [v for v in found if v.row["공시상품코드"] in only]
    lines = {x["종형ID"]: x for x in value_lines(values)} if values.exists() else {}
    if not values.exists():
        out.notes.append(f"값 파일이 없음: {values.name}")
    summaries = Summaries(docs, targets, layout)
    method_cache: dict[str, dict[int, str]] = {}
    summary_cache: dict[str, dict[int, str]] = {}

    def pages_of(cache: dict[str, dict[int, str]], stem: str, wanted: set[int]) -> dict[int, str]:
        have = cache.setdefault(stem, {})
        missing = wanted - set(have)
        if missing:
            have.update(read_pages(docs, stem, missing))
        return have

    for v in found:
        line = lines.get(v.id)
        rec = Ready(v.id, v.row, v.gate_only, line.get("판정") if line else None)
        out.ready.append(rec)
        if line is None:
            rec.건너뜀 = NO_VALUE
            continue
        value = RC.final_value(line, READERS)
        if not value or not value.get("줄") or "근거쪽" not in value:
            rec.건너뜀 = f"{WAITING}(판정 '{line.get('판정') or ''}')"
            continue
        if not v.method:
            rec.건너뜀 = f"{NO_METHOD}: 공시 수집 결과에 사업방법서가 없음"
            continue
        stem = v.method["저장이름"]
        if line.get("사업방법서해시") and v.method.get("해시") != line["사업방법서해시"]:
            rec.앞주의.append(f"{v.row['공시상품코드']} {v.row['종형명']}: 받은 사업방법서의 해시가 판독한 문서와 다름. "
                            "기계 검사로만 확인함")
        pages = {"사업방법서": pages_of(method_cache, stem, method_pages_needed(value))}
        if not pages["사업방법서"]:
            rec.건너뜀 = f"{NO_METHOD}: 받은 문서 폴더에 사업방법서 PDF가 없음"
            continue
        summary_pages = {x["쪽"] for x in value.get("한도") or [] if x.get("문서") == "상품요약서"}
        if summary_pages and v.summary:
            pages["상품요약서"] = pages_of(summary_cache, v.summary["저장이름"], summary_pages)
        found_problems, marks = RC.machine_checks(value, pages, line.get("쪽범위"))
        marks += RC.title_marks(value, v.row["종형명"])
        if found_problems:
            rec.건너뜀 = f"{CHECK}: {'; '.join(found_problems)}"[:300]
            continue
        fresh = [m for m in marks if m not in accepted_marks(line)]
        if fresh:
            rec.건너뜀 = f"{NEW_MARK}: {'; '.join(fresh)}"[:300]
            continue
        last = max(x["쪽"] for x in value["줄"])
        rec.근거쪽 = value["근거쪽"]
        rec.기본계약이름 = method_main_name(pages["사업방법서"], value["근거쪽"], last)
        if v.gate_only:
            rec.주계약후보 = [variants.main_row(v)]
        else:
            rec._mains = lambda v=v: summaries.mains(v)
        built = RC.build_rows([{"종형ID": v.id, "종형명": v.row["종형명"]}], {v.id: value})
        rec.가입조건 = built.conditions
        rec.행주의 = built.notes
    return out


def finish(store: SheetStore, prepared: Prepared, now: datetime, dry_run: bool = False) -> Loaded:
    """prepare(또는 행 패키지)의 종형을 시트에 맞춰 쓴다. 시트에 주계약 행이 있으면 그 행을, 없으면 주계약 후보를 쓰고,
    주계약 행 이름이 사업방법서 기본계약 이름과 맞는지 본다. 그 종형의 특약 가입조건 행은 그대로 둔다."""
    report = Loaded()
    report.notes += prepared.notes
    sheet = store.read(["sys_상품종형", "sys_특약", TAB, "sys_작업로그"])
    on_sheet_variants = {r["종형ID"] for r in sheet["sys_상품종형"]}
    sheet_riders = collections.defaultdict(list)
    for r in sheet["sys_특약"]:
        sheet_riders[r["종형ID"]].append(r)
    log = WorkLog(now, TAB)

    def skip(rec: Ready, why: str) -> None:
        row = rec.종형행
        report.skipped[rec.종형ID] = why
        report.counts[rec.종형ID] = {"공시상품코드": row["공시상품코드"], "종형명": row["종형명"],
                                    "비교역할구분": row["비교역할구분"], "판정": rec.판정 or "",
                                    "가입조건": 0, "주계약 행": "", "쓰지 않은 사유": why}
        log.add("코드대조", rec.종형ID, "반려", f"교차 확인 가입조건을 쓰지 않음: {why}", model=MODEL)

    for rec in prepared.ready:
        vid, row = rec.종형ID, rec.종형행
        report.notes += rec.앞주의
        if rec.건너뜀:
            skip(rec, rec.건너뜀)
            continue
        method_name = rec.기본계약이름
        main = next((r for r in sheet_riders.get(vid, []) if r["담보구분"] == "주계약"), None)
        new_main = main is None
        if new_main and rec.관문전용:
            main = rec.candidates()[0]
        elif new_main:
            mains = rec.candidates()
            if mains is None:
                skip(rec, f"{NO_MAIN}: 시트에 주계약 행이 없고 받은 문서 폴더에 상품요약서 PDF가 없음")
                continue
            fits = [r for r in mains if names_match(r["원시특약명"], method_name)]
            if len(fits) != 1:
                skip(rec, f"{NO_MAIN}: 요약서 표의 주계약 행 {len(mains)}개 가운데 사업방법서 기본계약 이름과 맞는 행이 "
                          f"{len(fits)}개")
                continue
            main = fits[0]
        if not names_match(main["원시특약명"], method_name):
            skip(rec, f"{NAME}: 주계약 행 '{main['원시특약명']}', 사업방법서 기본계약 '{method_name or '찾지 못함'}'")
            continue

        report.notes += [f"{row['공시상품코드']} {n}" for n in rec.행주의]
        if not rec.가입조건:
            skip(rec, NO_ROWS)
            continue
        conditions = copy.deepcopy(rec.가입조건)
        report.rows[TAB] += conditions
        report.done.add(vid)
        if new_main:
            report.new_mains.append(main)
        if vid not in on_sheet_variants:
            report.new_variants.append(row)
        verdict = rec.판정
        how = "두 판독이 같고 기계 검사를 통과한 값" if verdict == RC.CONFIRMED else f"원문 대조로 판정을 마친 값(판정 {verdict})"
        for r in conditions:
            log.add("판정", r["조건행ID"], "통과", f"가입나이: 교차 확인. {how}. 사업방법서 {rec.근거쪽}쪽 표", model=MODEL)
        report.counts[vid] = {"공시상품코드": row["공시상품코드"], "종형명": row["종형명"],
                              "비교역할구분": row["비교역할구분"], "판정": verdict, "가입조건": len(conditions),
                              "주계약 행": "새로 씀" if new_main else "시트에 있음", "주계약특약ID": main["특약ID"],
                              "주계약 이름": main["원시특약명"], "사업방법서 기본계약": method_name or ""}

    job._drop_repeats(TAB, report)
    report.kept = [r for r in sheet[TAB] if r["종형ID"] in report.done and r.get("특약ID")]
    new_ids = {r["조건행ID"] for r in report.rows[TAB]}
    report.dropped = len({r["조건행ID"] for r in sheet[TAB] if r["종형ID"] in report.done and not r.get("특약ID")} - new_ids)
    # ID 겹침: 새 가입조건 행끼리, 그대로 두는 특약 가입조건 행과, 새 주계약 행과 시트의 특약 행
    counted = collections.Counter(r["조건행ID"] for r in report.rows[TAB] + report.kept)
    rider_ids = {r["특약ID"] for r in sheet["sys_특약"]}
    report.clashes = {TAB: sorted(k for k, n in counted.items() if n > 1),
                      "sys_특약": sorted(r["특약ID"] for r in report.new_mains if r["특약ID"] in rider_ids)}
    report.clashes = {t: x for t, x in report.clashes.items() if x}

    bad = check_rows(TAB, report.rows[TAB])
    if bad:
        report.rows[TAB] = [r for r in report.rows[TAB] if r["조건행ID"] not in bad]
        for row_id, reasons in bad.items():
            report.notes.append(f"{TAB} {row_id}: 형식 검사에 걸려 쓰지 않음 ({'; '.join(reasons)})")
            log.add("코드대조", row_id, "반려", f"형식 검사에 걸려 시트에 쓰지 않음: {'; '.join(reasons)}")
    report.rows["sys_특약"] = list(report.new_mains)
    report.rows["sys_상품종형"] = list(report.new_variants)
    report.errors = {t: e for t in ("sys_특약", "sys_상품종형") if (e := check_rows(t, report.rows[t]))}
    report.logs = log.rows
    if report.clashes:
        report.notes.append(f"ID 겹침이 있어 쓰지 않음: {report.clashes}")
    if report.errors or report.clashes or not report.done or dry_run:
        return report
    try:
        if report.new_variants:
            store.replace_variants({"sys_상품종형": report.new_variants}, {r["종형ID"] for r in report.new_variants},
                                   only=["sys_상품종형"])
        if report.new_mains:
            # 그 종형의 다른 특약 행은 그대로 다시 넣는다. 주계약 행만 더한다
            owners = {r["종형ID"] for r in report.new_mains}
            rows = [r for vid in owners for r in sheet_riders.get(vid, [])] + report.new_mains
            store.replace_variants({"sys_특약": rows}, owners, only=["sys_특약"])
        store.replace_variants({TAB: report.rows[TAB] + report.kept}, report.done, only=[TAB])
        store.append("sys_작업로그", report.logs)
    except Exception as e:  # noqa: BLE001  만든 결과는 호출한 쪽이 파일로 남길 수 있게 돌려준다
        report.write_error = f"{type(e).__name__}: {str(e)[:300]}"
        report.notes.append(f"시트에 쓰지 못함: {report.write_error}")
        return report
    report.written = True
    return report


def markdown(report: Loaded) -> str:
    """실행 요약. 문서의 문장은 싣지 않는다."""
    head = ["| 공시상품코드 | 종형명 | 비교역할 | 판정 | 가입조건 행 | 주계약 행 |", "| --- | --- | --- | --- | --- | --- |"]
    rows = [f"| {c['공시상품코드']} | {c['종형명']} | {c['비교역할구분']} | {c['판정']} | {c['가입조건']} | "
            f"{c['주계약 행'] or '쓰지 않음'} |" for c in report.counts.values()]
    out = "\n".join(head + rows) + "\n\n"
    out += (f"가입조건 행 {len(report.rows[TAB])} (종형 {len(report.done)}), 새로 쓰는 주계약 특약 행 {len(report.new_mains)}, "
            f"새로 쓰는 종형 행 {len(report.new_variants)}, 그대로 두는 특약 가입조건 행 {len(report.kept)}\n")
    if report.skipped:
        out += f"쓰지 않은 종형 {len(report.skipped)}\n" + "".join(
            f"- {report.counts[vid]['공시상품코드']} {report.counts[vid]['종형명']}: {why}\n" for vid, why in report.skipped.items())
    out += f"ID 겹침: {report.clashes or '없음'}\n"
    out += f"형식 오류: {sum(len(e) for e in report.errors.values()) if report.errors else 0}행\n"
    out += f"시트에 있었는데 이번에 빠지는 주계약 가입조건 행: {report.dropped}\n"
    out += f"작업 기록: {len(report.logs)}행 (호출모델 '{MODEL}')\n"
    if report.notes:
        out += "\n주의\n" + "\n".join(f"- {n}" for n in report.notes) + "\n"
    return out


def result_of(report: Loaded) -> dict[str, Any]:
    return {
        "종형": report.counts, "가입조건 행": len(report.rows[TAB]), "새 주계약 행": [r["특약ID"] for r in report.new_mains],
        "새 종형 행": [r["종형ID"] for r in report.new_variants], "쓰지 않은 종형": report.skipped,
        "그대로 두는 특약 가입조건 행": len(report.kept), "ID 겹침": report.clashes, "형식 오류": report.errors,
        "시트에서 빠지는 주계약 가입조건 행": report.dropped, "주의": report.notes, "기록 행 수": len(report.logs),
        "시트에 씀": report.written,
    }


def seed(store: SheetStore, path: Path) -> None:
    """급부 적재의 결과물(load_reader_product.py --rows)의 행을 쓴 뒤의 시트로 만든다."""
    data = json.loads(path.read_text(encoding="utf-8"))["행"]
    tabs = [t for t in job.BENEFIT_TABS if data.get(t)]
    owners = {r["종형ID"] for r in data.get("sys_상품종형") or []}
    store.replace_variants({t: data[t] for t in tabs}, owners, only=tabs)


def package_of(prepared: Prepared, org: str, targets: Path, values: Path, index: Sequence[Mapping[str, Any]],
               root: Path = ROOT) -> dict[str, Any]:
    """prepare의 결과를 가입조건 행 패키지로. 정밀비교 종형의 주계약 후보는 여기서 요약서를 읽어 채운다(시트에 주계약 행이
    있으면 쓰지 않는 행이지만, 쓸 때의 시트를 알 수 없으므로 담아 둔다). 작업 기록과 시트에 맞추는 일은 쓸 때 finish가 한다."""
    ready = [rec.as_package() for rec in prepared.ready]
    return {
        **P.header(P.CONDITIONS, org, targets, [values] if values.exists() else [], index, root),
        "행수": counts_of(ready),
        "주의": list(prepared.notes),
        "종형": ready,
    }


def counts_of(ready: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {"종형": len(ready), "sys_가입조건": sum(len(r.get("가입조건") or []) for r in ready),
            "주계약후보": sum(len(r.get("주계약후보") or []) for r in ready)}


def from_package(package: Mapping[str, Any]) -> Prepared:
    """가입조건 행 패키지를 finish에 넣을 Prepared로. 행의 형식 검사와 ID 겹침은 finish가 시트와 함께 본다."""
    ready = package.get("종형")
    if not isinstance(ready, list):
        raise P.PackageError("행 패키지에 종형 목록이 없음")
    P.check_counts(package, counts_of(ready))
    out = Prepared(notes=list(package.get("주의") or []))
    for item in ready:
        try:
            out.ready.append(Ready(**copy.deepcopy(item)))
        except TypeError as e:
            raise P.PackageError(f"행 패키지의 종형 줄 꼴이 틀림: {e}") from None
    repeated = [k for k, n in collections.Counter(r.종형ID for r in out.ready).items() if n > 1]
    if repeated:
        raise P.PackageError(f"행 패키지에 같은 종형이 두 번 있음: {sorted(repeated)}")
    for rec in out.ready:
        if rec.종형행.get("종형ID") != rec.종형ID or any(r.get("종형ID") != rec.종형ID for r in rec.가입조건):
            raise P.PackageError(f"행 패키지의 {rec.종형ID} 줄에 다른 종형의 행이 들어 있음")
        if not rec.건너뜀 and rec.관문전용 and not rec.주계약후보:
            raise P.PackageError(f"행 패키지의 관문전용 종형 {rec.종형ID}에 주계약 후보 행이 없음")
    return out


def read_package(path: Path, org: str, targets: Path, root: Path = ROOT) -> Prepared:
    """가입조건 행 패키지를 읽어 체크아웃된 저장소와 맞춰 본다. 그 회사의 가입조건 값 파일이 패키지를 만들 때와 같아야 한다."""
    values = root / "data" / "crosscheck" / f"{org}_main_conditions_2reader.jsonl"
    return from_package(P.read(path, P.CONDITIONS, org, targets, root, [values] if values.exists() else []))


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--docs", type=Path,
                   help="fetch_disclosure.py의 결과 폴더(index.json과 사업방법서, 요약서 PDF). --rows-in이 없으면 꼭 준다")
    p.add_argument("--targets", type=Path, default=TARGETS)
    p.add_argument("--values", type=Path, help="값 파일. 비우면 data/crosscheck/<회사>_main_conditions_2reader.jsonl")
    p.add_argument("--org", default=tables.MERITZ.name, choices=sorted(L.LAYOUTS), help="요약서 급부 표의 꼴(회사)")
    p.add_argument("--only", action="extend", nargs="+", help="이 공시상품코드의 종형만 처리")
    p.add_argument("--dry-run", action="store_true", help="시트에 쓰지 않는다")
    p.add_argument("--snapshot", type=Path, help="시트 대신 이 사본 폴더를 읽는다. 시트에 쓰지 않는다")
    p.add_argument("--seed-rows", type=Path, help="load_reader_product.py --rows의 결과물. 그 행을 쓴 뒤의 시트로 본다. 시트에 쓰지 않는다")
    p.add_argument("--result", type=Path, help="종형별 행 수와 쓰지 않은 사유를 JSON으로 남길 경로")
    p.add_argument("--rows", type=Path, help="만들어질 행과 작업 기록을 JSON으로 남길 경로")
    p.add_argument("--rows-out", type=Path, metavar="패키지",
                   help="문서로 만든 가입조건 행을 행 패키지로 남긴다(보통 data/backfill_rows/<회사>_conditions.json). 시트에 쓰지 않는다")
    p.add_argument("--rows-in", type=Path, metavar="패키지",
                   help="문서 없이 이 행 패키지의 행을 검증해 쓴다(--docs, --only, --values와 함께 쓰지 않는다)")
    args = p.parse_args(argv)
    if args.rows_in and (args.docs or args.only or args.values or args.rows_out):
        p.error("--rows-in은 --docs, --only, --values, --rows-out과 함께 쓰지 않습니다")
    if not args.rows_in and not args.docs:
        p.error("--docs나 --rows-in이 필요합니다")
    if args.rows_out and args.only:
        p.error("행 패키지는 회사 전체를 담습니다. --rows-out은 --only와 함께 쓰지 않습니다")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse(argv)
    dry_run = args.dry_run or bool(args.snapshot) or bool(args.seed_rows) or bool(args.rows_out)
    if args.snapshot:
        store = snapshot_store(args.snapshot)
    elif args.seed_rows:
        store = SheetStore(MemoryBackend())
    else:
        has_sheet = bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") and os.environ.get("SPREADSHEET_ID"))
        if not has_sheet and not dry_run:
            print("시트 접속 정보가 없어 건너뜁니다. 흐름만 보려면 --dry-run이나 --snapshot을 붙이세요.")
            return 0
        if has_sheet:
            from postlife.sheets_io import RestBackend

            store = SheetStore(RestBackend.from_env())
        else:
            store = SheetStore(MemoryBackend())
    if args.seed_rows:
        seed(store, args.seed_rows)
    package = None
    if args.rows_in:
        try:
            prepared = read_package(args.rows_in, args.org, args.targets)
        except P.PackageError as e:
            print("행 패키지를 쓰지 않고 멈춥니다:", e)
            return 1
        prepared.notes.insert(0, f"행 패키지 {args.rows_in}에서 읽음(문서를 받지 않음)")
    else:
        targets = json.loads(args.targets.read_text(encoding="utf-8"))
        index = json.loads((args.docs / "index.json").read_text(encoding="utf-8"))
        values = args.values or CROSSCHECK / f"{args.org}_main_conditions_2reader.jsonl"
        prepared = prepare(targets, index, args.docs, values, only=args.only, layout=L.LAYOUTS[args.org])
        if args.rows_out:
            try:
                package = package_of(prepared, args.org, args.targets, values, index)
            except P.PackageError as e:
                print("행 패키지를 만들지 못했습니다:", e)
                return 1
            dry_run = True
    report = finish(store, prepared, datetime.now(KST), dry_run=dry_run)

    text = markdown(report)
    print(text)
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result_of(report), ensure_ascii=False, indent=1), encoding="utf-8")
    if args.rows:
        args.rows.parent.mkdir(parents=True, exist_ok=True)
        rows = {t: report.rows[t] for t in ("sys_상품종형", "sys_특약", TAB)}
        args.rows.write_text(json.dumps({"행": rows, "작업로그": report.logs}, ensure_ascii=False, indent=1, default=str),
                             encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 두 판독 주계약 가입조건 적재 (교차 확인)\n\n" + text)
    if report.write_error:
        print("시트에 쓰지 못했습니다:", report.write_error)
        return 1
    if report.errors or report.clashes:
        print("형식 검사나 ID 겹침에 걸려 시트에 쓰지 않았습니다:",
              json.dumps({"형식": report.errors, "겹침": report.clashes}, ensure_ascii=False)[:2000])
        return 1
    if not report.done:
        print("가입조건 행을 만든 종형이 없습니다.")
        return 1
    if package is not None:
        P.write(args.rows_out, package)
        print(f"행 패키지를 씀: {args.rows_out} ({json.dumps(package['행수'], ensure_ascii=False)})")
        return 0
    if report.written:
        print(f"시트에 씀: 가입조건 {len(report.rows[TAB])}, 주계약 행 {len(report.new_mains)}, 종형 행 {len(report.new_variants)}, "
              f"기록 {len(report.logs)}행")
    else:
        print("시트에 쓰지 않았습니다(--dry-run, --snapshot 또는 --seed-rows).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
