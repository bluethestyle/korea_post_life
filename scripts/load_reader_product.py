r"""초기 적재의 두 판독(교차 확인)이 판정을 마친 급부 값을, 판정 모델 없이 시트에 쓴다. 첫 회사는 메리츠화재다.

초기 적재(2026-11-20 결정)는 Gemini API와 판정 모델을 쓰지 않는다. 두 판독자(sonnet, opus)가 표 읽기(extract/tables.py)의
조각을 따로 읽고, 코드가 둘을 견주고 원문과 대조해, 메인 세션이 판정을 마친 값을 값 파일(data/crosscheck/<회사>_<공시상품코드>_
benefits_2reader.jsonl, 꼴은 data/crosscheck/README.md)에 둔다. 이 스크립트는 그 값으로 행을 만든다.

1. 대상 설정과 공시 수집 결과(index.json)로 종형 행을 만든다(variants.build). 종형 행은 모든 종형을 쓴다.
2. 정밀비교 종형마다 상품요약서 PDF에서 표를 다시 읽어 조각을 만든다. 쪽을 넘어 이어지는 표 하나인 요약서(--org meritz,
   kblife)는 tables.py, 특약마다 작은 표가 따로인 생명보험사 요약서(--org samsunglife)는 blocks.py로 읽는다(dump_tables.py,
   dump_blocks.py와 같은 조각). 같은 요약서를 쓰는 종형은 한 번만 읽는다. KB라이프생명은 형(간편심사형, 일반심사형)으로 종형을
   고르고, 간편심사형 조각은 같은 형의 관문전용 종형(3.3.5)이 아니라 정밀비교 종형(3.5.5)에만 행이 된다.
   조각의 형과 종형은 reader_rows.variants_for로 잇는다("공통" 조각은 그 요약서의 모든 정밀비교 종형에 든다). 한 급부 표 안에
   종별 값이 함께 있는 요약서(삼성생명)는 대상 설정의 종형에 "읽을종"("2종")을 적고, 그 종이 아닌 조각과 줄은 빼고
   (reader_rows.for_kind) 남은 줄의 글자에서 다른 종의 토막을 뗀 뒤 행을 만든다. 조각 지문은 원래 조각으로 맞춘다.
3. 값 파일의 번호마다 조각 지문(reader_rows.cover_fingerprint)을 다시 읽은 조각과 맞춰 본다. 지문이 다른 줄은 쓰지 않는다.
   한 요약서 안에서 형마다 공시상품코드가 따로 있는 상품(KB라이프생명)은 형마다 값 파일이 따로이고, 그 요약서를 쓰는 코드의
   값 파일을 모두 이어 쓴다(merged_lines).
4. reader_rows.build_rows로 특약 행과 급부 행을 만든다. 원문 구절이 들어가는 열(지급횟수제한, 감액예외)은 조각에서 잘라 쓴다.
   판정값에 지급단위근거(요약서 밖 문서의 쪽. KB라이프생명 입원 특약의 "1일당"은 약관의 그 특약 조항에만 있다)가 있으면
   공시 수집 결과에서 그 문서를 찾아 가리킨 쪽만 다시 뽑고, 그 쪽의 글자에서 지급단위 구절을 찾는다(basis_pages).
   갱신형 특약의 갱신주기년은 대상 설정의 갱신형특약주기년이고, 갱신형특약제외에 적은 특약은 만들지 않는다.
   행없음 줄은 금액 없는 급부 행(지급기준구분 차등지급, 실손보상, 분할지급, 현물급부. 두 금액과 감액은 비움)이 되고,
   그런 급부마다 작업 로그 한 줄(작업단계 추출, 대상열 지급기준구분, 결과 통과)에 판독 사유, 번호, 내용 지문을 남긴다.
5. 쓰지 않는 줄: 판정이 "검토 대기"이거나 빈 줄, 행없음사유가 "그밖"인 행없음 줄(행없음 정보는 결과물 파일에만 둔다), 지문이
   다른 줄, 표 읽기가 이름을 잘못 낸 줄(reader_rows.name_problem의 보류), 기계 검사에 걸린 줄, 갱신형특약제외의 특약에 걸린 줄.
   사유별 수를 요약에 낸다.

관문전용 종형은 종형 행만 쓴다(특약과 급부는 정밀비교 종형에만 쓴다). 시트 쓰기와 작업 로그는 삼성화재 적재
(scripts/load_table_product.py)와 같다: 호출모델은 "교차 확인", 판정확률은 비운다. 쓰는 줄은 모두 판정을 마친 값이라 검토 기록은
남기지 않고, 시트에서 검토 대기였던 급부가 이번에 쓰이면 판정 통과를 남겨 대기 표시를 푼다. 끝에 종형마다 급부를 다시 뽑았다는
기록을 더한다(rerun.coverage_logs). 다시 돌리면 정밀비교 종형의 sys_상품종형, sys_특약, sys_급부 행과 관문전용 종형의 sys_상품종형
행을 새 행으로 바꾼다. sys_특약의 가입 한도(최소가입금액만원, 최대가입금액만원, 합산한도기준키)는 시트에 있던 값을 잇는다.

  python scripts/load_reader_product.py --docs out --result result/extract.json                 # 시트에 쓴다
  python scripts/load_reader_product.py --docs out --dry-run --result r.json --rows rows.json     # 쓰지 않고 행과 요약만 낸다
  python scripts/load_reader_product.py --docs out --snapshot data/snapshot --result r.json       # 사본을 시트 삼아 본다(쓰지 않음)

  python scripts/load_reader_product.py --docs out --org samsunglife --targets data/targets/samsunglife.json --dry-run --result r.json
  python scripts/load_reader_product.py --docs out --org kblife --targets data/targets/kblife.json --dry-run --result r.json

--docs는 scripts/fetch_disclosure.py --org <회사>의 결과 폴더다(index.json과 <저장이름>.pdf). 시트 접속 정보가 없어도
--dry-run은 끝까지 돈다(빈 시트로 본다). --result에는 조각의 문장을 싣지 않는다. --rows(결과물)에는 만들어질 행과 행없음 줄의
정보가 들어가며, 행의 원문 구절 열(지급횟수제한, 감액예외)이 들어 있으므로 리포에 두지 않는다.

행 패키지(src/postlife/extract/row_package.py). Actions 러너에서 공시실 접속이 막히는 회사(삼성생명, KB라이프생명)는 로컬에서
받은 문서로 행을 만들어 패키지로 커밋하고, Actions는 문서 없이 패키지를 검증해 쓴다. 패키지는 build(문서로 행 만들기)의 결과이고,
읽는 길은 build 대신 패키지를 읽어 기존 길과 같은 finish(가입 한도 잇기, 형식 검사, ID 겹침, 작업 기록, 시트에서 빠지는 행)를
거친다. 패키지의 sys_급부 행에는 시트와 같은 원문 구절 열(지급횟수제한, 감액예외)이 들어 있다. 행없음 줄의 정보는 넣지 않는다.

  python scripts/load_reader_product.py --docs out --org samsunglife --targets data/targets/samsunglife.json \
      --rows-out data/backfill_rows/samsunglife_benefits.json                                   # 로컬: 패키지 만들기(쓰지 않음)
  python scripts/load_reader_product.py --rows-in data/backfill_rows/samsunglife_benefits.json --org samsunglife \
      --targets data/targets/samsunglife.json --result r.json                                   # Actions: 패키지로 시트에 쓰기
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from load_table_product import _drop_bad_benefits, snapshot_store  # noqa: E402  스크립트 폴더는 실행할 때 sys.path에 들어 있다
from postlife.extract import blocks, job, tables, variants  # noqa: E402
from postlife.extract import reader_rows as RR  # noqa: E402
from postlife.extract import rerun as R  # noqa: E402
from postlife.extract import row_package as P  # noqa: E402
from postlife.sheets_io import MemoryBackend, SheetStore  # noqa: E402
from postlife.snapshot import KST  # noqa: E402
from postlife.validate import NO_AMOUNT_BASES, check_rows  # noqa: E402
from postlife.worklog import WorkLog  # noqa: E402

MODEL = "교차 확인"                 # sys_작업로그의 호출모델
READERS = ("sonnet", "opus")
TABS_WRITTEN = job.BENEFIT_TABS
GATE_TABS = ["sys_상품종형"]       # 관문전용 종형은 종형 행만 쓴다
TARGETS = ROOT / "data" / "targets" / "meritz.json"
CROSSCHECK = ROOT / "data" / "crosscheck"

# 쓰지 않은 줄의 사유
WAITING = "검토 대기"
CHANGED = "조각 지문이 다름"
NOT_IN_VALUES = "값 파일에 없음"
NOT_IN_PIECES = "값 파일의 번호가 다시 읽은 조각에 없음"
CLASH = "값 파일 여럿에 같은 번호의 다른 줄"
NO_ROW = "행없음"
EXCLUDED = "20년 갱신주기를 고를 수 없는 갱신형 특약"
NO_YEARS = "갱신주기년이 없는 갱신형 특약"

# 요약서 급부 표의 꼴. 손해보험사 표(tables.py)와 생명보험사 특약별 작은 표(blocks.py)
Layout = tables.Layout | blocks.LifeLayout
LAYOUTS: dict[str, Layout] = {**tables.LAYOUTS, **blocks.LAYOUTS}


def common_of(layout: Layout) -> str:
    """형 구간이 있는 요약서에서 모든 형에 드는 조각의 형 이름. 생명보험사 꼴은 형 구간이 없다."""
    return getattr(layout, "common", "공통")


def main_renewal(riders: Sequence[dict[str, Any]], v: variants.Variant) -> None:
    """요약서 표에 이름 없이 "주계약"으로만 적힌 주계약 행(생명보험사 꼴, blocks.py)의 갱신여부와 갱신주기년을 종형의 갱신유형으로
    채운다(variants.main_row와 같은 값). 이름에 갱신형 표시가 없어 행 만들기가 비갱신으로 적기 때문이다. 이름이 있는 주계약 행
    (메리츠화재 따위)은 건드리지 않는다."""
    years = v.row["갱신주기년"] if v.row["갱신유형"] == "갱신" else None
    for r in riders:
        if r["담보구분"] == "주계약" and r["원시특약명"] == variants.MAIN_NAME:
            r["갱신여부"], r["갱신주기년"] = years is not None, years


def variant_pieces(pieces: Sequence[RR.PieceView], name: str, layout: Layout,
                   kind: str | None) -> tuple[list[RR.PieceView], list[str], list[int]]:
    """종형 하나에 드는 조각. 형으로 고르고(reader_rows.variants_for), 대상 설정의 읽을종이 있으면 그 종이 아닌 조각과 줄을
    뺀다(reader_rows.for_kind). (조각, 읽을 종이 아니어서 뺀 세부보장 번호, 통째로 뺀 조각 순번)."""
    mine = [p for p in pieces if name in RR.variants_for(p.segment, [name], common_of(layout))]
    if not kind:
        return mine, [], []
    return RR.for_kind(mine, kind)


@dataclass
class Group:
    """같은 상품요약서를 쓰는 정밀비교 종형들과 그 요약서에서 다시 읽은 조각."""
    code: str                                   # 값 파일의 공시상품코드
    variants: list[variants.Variant]
    pieces: list[RR.PieceView] = field(default_factory=list)
    used: list[str] = field(default_factory=list)          # 정밀비교 종형 하나 이상에 드는 조각의 세부보장 번호(차례대로)
    reasons: dict[str, str] = field(default_factory=dict)  # 번호 → 쓰지 않은 사유
    written: set[str] = field(default_factory=set)         # 급부 행이 된 번호
    kinds: dict[str, str] = field(default_factory=dict)    # 종형명 → 대상 설정의 읽을종(있는 종형만)
    out_of_kind: list[str] = field(default_factory=list)   # 읽을 종이 아니어서 어느 정밀비교 종형에도 들지 않은 번호


@dataclass
class Loaded(job.Report):
    counts: dict[str, dict[str, Any]] = field(default_factory=dict)      # 종형ID → 줄 수
    groups: list[Group] = field(default_factory=list)
    no_rows: dict[str, dict[str, Any]] = field(default_factory=dict)     # "공시상품코드 번호" → 행없음 정보
    excluded: dict[str, list[str]] = field(default_factory=dict)         # 공시상품코드 → 갱신형특약제외로 뺀 특약명
    clashes: dict[str, list[str]] = field(default_factory=dict)          # 탭 → 겹친 ID
    dropped: dict[str, int] = field(default_factory=dict)                # 탭 → 시트에 있었는데 이번에 빠지는 행 수
    gate_done: set[str] = field(default_factory=set)
    no_amount: dict[str, str] = field(default_factory=dict)              # 금액 없는 급부ID → 작업 로그 사유(판독 사유, 번호, 내용 지문)
    cover_names: dict[str, list[str]] = field(default_factory=dict)      # 공시상품명 → 급부를 다시 뽑은 종형ID(종형별 다시 뽑음 기록)
    package: str | None = None                                           # 행 패키지에서 읽었으면 그 경로


def value_lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def merged_lines(paths: Sequence[Path]) -> tuple[list[dict[str, Any]], set[str]]:
    """같은 요약서를 쓰는 코드들의 값 파일을 잇는다. 한 요약서 안에서 형마다 공시상품코드가 따로 있는 상품(KB라이프생명:
    간편심사형 331000106, 일반심사형 335000106)은 형마다 묶음과 값 파일이 따로다. 번호는 요약서의 조각 순번이라 겹치지 않는다.
    같은 번호가 두 파일에 있으면 줄이 글자까지 같을 때만 하나를 쓰고, 다르면 그 번호는 쓰지 않는다(돌려주는 집합)."""
    seen: dict[str, dict[str, Any]] = {}
    clash: set[str] = set()
    for path in paths:
        for line in value_lines(path):
            n = line["번호"]
            if n in seen and seen[n] != line:
                clash.add(n)
            seen.setdefault(n, line)
    return [line for n, line in seen.items() if n not in clash], clash


def read_pieces(pdf: Path, layout: Layout) -> tuple[list[RR.PieceView], dict[int, str]]:
    """요약서 PDF에서 급부 표를 다시 읽어 조각(번호는 조각 파일의 순번)과 쪽 글자를 돌려준다.

    손해보험사 꼴(tables.Layout)은 scripts/dump_tables.py와, 생명보험사 꼴(blocks.LifeLayout)은 scripts/dump_blocks.py와 같은 길이다.
    """
    pages = tables.page_texts(pdf)
    if isinstance(layout, blocks.LifeLayout):
        result, source = blocks.read_pdf(pdf, layout, pages=pages)
        data = tables.riders_to_json(result.riders, {"문서": pdf.stem, **source}, result.notes)
        return RR.load_pieces(data), pages
    found = tables.benefit_pages(pages, None, layout)
    read = tables.read_tables(pdf, found.first_page, found.last_page, layout)
    riders = tables.riders_from_tables(read, layout)
    data = tables.riders_to_json(riders, {"문서": pdf.stem, "쪽": [found.first_page, found.last_page]},
                                 tables.table_notes(read, layout))
    return RR.load_pieces(data), pages


def page_subset(pdf: Path, numbers: set[int]) -> dict[int, str]:
    """PDF에서 고른 쪽의 글자만(tables.page_texts와 같은 뽑기). 약관처럼 쪽이 많은 문서를 다 풀지 않으려고 쓴다."""
    import pdfplumber

    with pdfplumber.open(pdf) as f:
        return {n: f.pages[n - 1].extract_text() or "" for n in sorted(numbers) if 0 < n <= len(f.pages)}


def basis_pages(index: Sequence[Mapping[str, Any]], codes: Sequence[str], readings: Mapping[str, Mapping[str, Any]],
                docs: Path) -> tuple[dict[str, dict[int, str]], list[str]]:
    """판정값의 지급단위근거가 가리키는 요약서 밖 문서(사업방법서, 약관)의 쪽 글자와 주의.

    그 요약서를 쓰는 코드(codes)의 공시 수집 결과에서 그 문서를 찾아 가리킨 쪽만 뽑는다. 문서가 없으면 주의를 남기고,
    그 줄은 기계 검사(지급단위 구절없음)에 걸려 쓰지 않는다.
    """
    wanted: dict[str, set[int]] = {}
    for v in readings.values():
        basis = v.get("지급단위근거")
        if basis and basis["문서"] != "상품요약서":
            wanted.setdefault(basis["문서"], set()).add(basis["쪽"])
    out: dict[str, dict[int, str]] = {}
    notes: list[str] = []
    for kind, numbers in sorted(wanted.items()):
        entry = next((e for e in index if e.get("상품코드") in codes and e.get("문서") == kind), None)
        pdf = docs / f"{entry['저장이름']}.pdf" if entry else None
        if pdf is None or not pdf.exists():
            notes.append(f"{', '.join(codes)}: 지급단위근거의 {kind}가 공시 수집 결과에 없어 그 문서를 가리킨 줄은 쓰지 않음")
            continue
        out[kind] = page_subset(pdf, numbers)
    return out, notes


def renewal_years(pieces: Sequence[RR.PieceView], years: int | None, excluded: Sequence[str]) -> dict[str, int]:
    """조각의 갱신형 특약 이름마다 갱신주기년. 갱신형특약제외에 적은 특약(빈칸 무시)과 주기가 없으면 넣지 않는다."""
    banned = {RR._squash(n) for n in excluded}
    out = {}
    for p in pieces:
        for name in p.names or (p.title,):
            if RR.is_renewal(name) and years is not None and RR._squash(name) not in banned:
                out[name] = years
    return out


def products_of(targets: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    """(공시상품코드, 종형명) → 그 종형이 든 상품 설정."""
    return {(v["공시상품코드"], v["종형명"]): product for product in targets["상품"] for v in product["종형"]}


def kinds_of(targets: Mapping[str, Any]) -> dict[tuple[str, str], str]:
    """(공시상품코드, 종형명) → 대상 설정의 읽을종("2종"). 한 급부 표 안에 종별 값이 함께 있는 요약서(삼성생명)의 정밀비교
    종형에만 적는다. 적지 않은 종형은 넣지 않는다."""
    return {(v["공시상품코드"], v["종형명"]): v["읽을종"] for product in targets["상품"] for v in product["종형"]
            if v.get("읽을종")}


def check_values(group: Group, lines: Sequence[Mapping[str, Any]], clash: set[str] | None = None) -> dict[str, dict[str, Any]]:
    """값 파일을 다시 읽은 조각과 맞춰 보고 행 만들기에 넣을 판정 값을 고른다. 쓰지 않을 줄은 group.reasons에 사유를 남긴다.
    clash는 값 파일 여럿에 서로 다른 줄로 나온 번호(merged_lines)다."""
    found = RR.covers_by_number(group.pieces)
    used = set(group.used)
    by_number = {line["번호"]: line for line in lines}
    for n in sorted(clash or ()):
        if n in used:
            group.reasons[n] = CLASH
    for n in group.used:
        if n not in by_number and n not in group.reasons:
            group.reasons[n] = NOT_IN_VALUES
    for n, line in by_number.items():
        if n not in found:
            group.reasons[n] = NOT_IN_PIECES
        elif n in used and RR.cover_fingerprint(*found[n]) != line.get("조각지문"):
            group.reasons[n] = CHANGED
    readings = RR.final_readings(lines, *READERS)
    for n, line in by_number.items():
        if n in used and n not in group.reasons and n not in readings:
            group.reasons[n] = WAITING
    return {n: v for n, v in readings.items() if n in used and n not in group.reasons}


def load(store: SheetStore, targets: dict[str, Any], index: list[dict[str, Any]], docs: Path,
         values: Mapping[str, Path], now: datetime, dry_run: bool = False, only: Sequence[str] | None = None,
         layout: Layout = tables.MERITZ) -> Loaded:
    """values: {공시상품코드: 값 파일}. 같은 요약서를 쓰는 종형들은 그 가운데 값 파일이 있는 코드의 값 파일을 모두 이어 쓴다
    (merged_lines. 메리츠화재는 요약서마다 값 파일이 하나, KB라이프생명은 형마다 하나).

    급부 행의 형식 오류는 그 행만 빼고 쓴다. 상품종형이나 특약에 형식 오류나 ID 겹침이 남거나 dry_run이면 쓰지 않는다.
    대상 설정의 종형에 읽을종이 있으면 그 종이 아닌 조각과 세부보장은 그 종형의 행을 만들지 않는다(variant_pieces). 값 파일에도
    그 줄은 없다(묶음 나누기가 같은 규칙으로 뺀다).

    문서로 행을 만드는 단계(build)와 시트에 맞춰 쓰는 단계(finish)로 나뉜다. 행 패키지(--rows-out)는 build의 결과이고,
    패키지로 쓰는 길(--rows-in)은 build 대신 패키지를 읽어 같은 finish를 거친다.
    """
    return finish(store, build(targets, index, docs, values, only, layout), now, dry_run)


def build(targets: dict[str, Any], index: list[dict[str, Any]], docs: Path, values: Mapping[str, Path],
          only: Sequence[str] | None = None, layout: Layout = tables.MERITZ) -> Loaded:
    """문서와 값 파일로 행을 만든다. 시트를 읽지 않고 실행 시각을 쓰지 않는다(같은 입력이면 같은 행).
    가입 한도 잇기, 형식 검사, 작업 기록, 시트 쓰기는 finish가 한다."""
    report = Loaded()
    found, problems = variants.build(targets, index)
    report.notes += problems
    if only:
        found = [v for v in found if v.row["공시상품코드"] in only]
    product = products_of(targets)
    kind_of = kinds_of(targets)

    precise = [v for v in found if not v.gate_only]
    for v in found:
        if v.gate_only:
            report.rows["sys_상품종형"].append(v.row)
            report.gate_done.add(v.id)
    shared: dict[str, list[variants.Variant]] = {}
    for v in precise:
        if not (v.summary and v.summary.get("해시")):
            report.notes.append(f"{v.row['공시상품코드']} {v.row['종형명']}: 공시 수집 결과에 상품요약서가 없어 건너뜀")
            continue
        shared.setdefault(v.summary["해시"], []).append(v)

    for group_variants in shared.values():
        codes = list(dict.fromkeys(v.row["공시상품코드"] for v in group_variants))
        same_file = [e["상품코드"] for e in index if e.get("해시") == group_variants[0].summary["해시"]]
        # 그 요약서를 쓰는 코드 가운데 값 파일이 있는 코드 모두(형마다 코드와 값 파일이 따로인 상품은 둘 이상)
        with_values = [c for c in dict.fromkeys(codes + same_file) if c in values and values[c].exists()]
        code = "+".join(with_values) or None
        first = group_variants[0]
        if code is None:
            report.notes.append(f"{', '.join(codes)}: 값 파일이 없어 급부를 쓰지 않음")
            continue
        pdf = docs / f"{first.summary['저장이름']}.pdf"
        if not pdf.exists():
            report.notes.append(f"{', '.join(codes)}: 상품요약서 PDF({pdf.name})가 없어 급부를 쓰지 않음")
            continue
        group = Group(code, group_variants)
        group.pieces, pages = read_pieces(pdf, layout)
        chosen: dict[str, list[RR.PieceView]] = {}
        in_variant: set[str] = set()
        cut: list[str] = []
        for v in group_variants:
            key = (v.row["공시상품코드"], v.row["종형명"])
            if key in kind_of:
                group.kinds[v.row["종형명"]] = kind_of[key]
            chosen[v.id], dropped, _ = variant_pieces(group.pieces, v.row["종형명"], layout, kind_of.get(key))
            in_variant |= {c.number for p in chosen[v.id] for c in p.covers}
            cut += dropped
        group.used = [c.number for p in group.pieces for c in p.covers if c.number in in_variant]
        group.out_of_kind = [n for n in dict.fromkeys(cut) if n not in in_variant]
        lines, clash = merged_lines([values[c] for c in with_values])
        readings = check_values(group, lines, clash)
        other, notes = basis_pages(index, list(dict.fromkeys(codes + same_file)), readings, docs)
        report.notes += notes
        report.groups.append(group)
        for v in group_variants:
            mine = chosen[v.id]
            settings = product[(v.row["공시상품코드"], v.row["종형명"])]
            banned = [x["특약명"] for x in settings.get("갱신형특약제외") or []]
            built = RR.build_rows(v.id, mine, readings, renewal_years(mine, v.plain_renewal_years, banned), pages, other)
            main_renewal(built.riders, v)
            report.rows["sys_상품종형"].append(v.row)
            report.rows["sys_특약"] += built.riders
            report.rows["sys_급부"] += built.benefits
            report.no_amount.update(no_amount_reasons(built, readings, group.pieces))
            report.done.add(v.id)
            _account(report, group, v, mine, built, banned)

    # 같은 ID로 내용까지 같은 행은 하나만 남긴다. 형식 검사보다 먼저 해야 한다. 그러지 않으면 기본키 중복으로 둘 다 빠진다
    for tab in TABS_WRITTEN:
        job._drop_repeats(tab, report)
    report.clashes = {tab: sorted(k for k, n in collections.Counter(r[key] for r in report.rows[tab]).items() if n > 1)
                      for tab, key in (("sys_상품종형", "종형ID"), ("sys_특약", "특약ID"), ("sys_급부", "급부ID"))}
    report.clashes = {t: ids for t, ids in report.clashes.items() if ids}
    for g in report.groups:
        for v in g.variants:
            report.cover_names.setdefault(v.row["공시상품명"], []).append(v.id)
    return report


def finish(store: SheetStore, report: Loaded, now: datetime, dry_run: bool = False) -> Loaded:
    """build(또는 행 패키지)의 행을 시트에 맞춰 쓴다. 시트에 있던 가입 한도를 잇고, 형식 검사에 걸린 급부 행을 빼고, 작업 기록
    (금액 없는 급부의 추출 기록, 검토 대기 풀기, 종형별 다시 뽑음 기록)을 만들고, 시트에서 빠지는 행을 센다."""
    sheet = store.read(["sys_특약", "sys_급부", "sys_상품종형", "sys_작업로그"])
    on_sheet = {r["특약ID"]: r for r in sheet["sys_특약"]}
    for r in report.rows["sys_특약"]:       # 표는 가입 한도를 모른다. 시트에 있던 값을 잇는다(job.run과 같다)
        old = on_sheet.get(r["특약ID"], {})
        r.update({c: old.get(c) for c in job.LIMIT_COLUMNS if r.get(c) is None})
    _drop_bad_benefits(report, now)

    log = WorkLog(now, "sys_급부")
    no_amount_logs(log, report)
    coverage = [row for name, vids in report.cover_names.items() for row in R.coverage_logs(now, vids, name)]
    # 쓴 뒤의 시트에서 검토 대기로 보일 줄(시트에서 검토 대기였던 줄 따위)에 판정 통과를 남긴다. 화면과 재추출은 가장 나중 실행만 본다
    touched = report.done | report.gate_done
    after = [r for r in sheet["sys_상품종형"] if r["종형ID"] not in touched] + report.rows["sys_상품종형"]
    waiting = R.pending_benefits(report.rows["sys_급부"], report.rows["sys_특약"], after, sheet["sys_작업로그"] + coverage)
    for bid in sorted(waiting):
        log.add("판정", bid, "통과", "교차 확인: 두 판독이 같거나 원문 대조로 판정을 마친 값. 앞선 검토 대기를 풂", model=MODEL)
    report.logs += log.rows + coverage

    old_riders = {r["특약ID"] for r in sheet["sys_특약"] if r["종형ID"] in report.done}
    new_ids = {tab: {r[key] for r in report.rows[tab]} for tab, key in (("sys_특약", "특약ID"), ("sys_급부", "급부ID"))}
    report.dropped = {"sys_특약": len(old_riders - new_ids["sys_특약"]),
                      "sys_급부": len({r["급부ID"] for r in sheet["sys_급부"] if r["특약ID"] in old_riders} - new_ids["sys_급부"])}

    report.errors = {tab: e for tab in TABS_WRITTEN if (e := check_rows(tab, report.rows[tab]))}
    if report.clashes:
        report.notes.append(f"ID 겹침이 있어 쓰지 않음: {report.clashes}")
    if report.errors or report.clashes or not (report.done or report.gate_done) or dry_run:
        return report
    try:
        if report.done:
            store.replace_variants({t: [r for r in report.rows[t] if _variant_of(r, report) in report.done]
                                    for t in TABS_WRITTEN}, report.done, only=TABS_WRITTEN)
        if report.gate_done:
            store.replace_variants({"sys_상품종형": [r for r in report.rows["sys_상품종형"] if r["종형ID"] in report.gate_done]},
                                   report.gate_done, only=GATE_TABS)
        store.append("sys_작업로그", report.logs)
    except Exception as e:  # noqa: BLE001  읽은 결과는 호출한 쪽이 파일로 남길 수 있게 돌려준다
        report.write_error = f"{type(e).__name__}: {str(e)[:300]}"
        report.notes.append(f"시트에 쓰지 못함: {report.write_error}")
        return report
    report.written = True
    return report


NO_AMOUNT_COLUMN = "지급기준구분"


def no_amount_logs(log: WorkLog, report: Loaded) -> None:
    """금액 없는 급부: 판독의 세부 사유는 시트 값이 아니라 작업 기록(작업단계 추출, 대상열 지급기준구분)에 남긴다."""
    for b in report.rows["sys_급부"]:
        if b["급부ID"] in report.no_amount and b.get("지급기준구분") in NO_AMOUNT_BASES:
            log.add("추출", b["급부ID"], "통과", report.no_amount[b["급부ID"]], model=MODEL, column=NO_AMOUNT_COLUMN,
                    after=b["지급기준구분"])


def no_amount_reasons(built: RR.Built, readings: Mapping[str, Mapping[str, Any]],
                      pieces: Sequence[RR.PieceView]) -> dict[str, str]:
    """금액 없는 급부ID → 작업 로그 사유. "판독 사유 회차별지급률, 번호 R012-3, 내용 지문 a1b2c3d4e5f6" 꼴이다.

    급부 하나에 번호가 여럿(이름과 값이 같은 줄)이면 번호마다 이어 적는다. 원문 글자는 싣지 않는다(지문만).
    """
    covers = RR.covers_by_number(pieces)
    out = {}
    for b in built.benefits:
        if b.get("지급기준구분") not in NO_AMOUNT_BASES:
            continue
        parts = []
        for n in built.numbers.get(b["급부ID"], ()):
            kind = (readings.get(n) or {}).get("행없음사유") or ""
            mark = RR.content_fingerprint(covers[n][1]) if n in covers else ""
            parts.append(f"판독 사유 {kind}, 번호 {n}, 내용 지문 {mark}")
        out[b["급부ID"]] = "; ".join(parts)
    return out


def _variant_of(row: Mapping[str, Any], report: Loaded) -> str | None:
    if "종형ID" in row:
        return row["종형ID"]
    owner = {r["특약ID"]: r["종형ID"] for r in report.rows["sys_특약"]}
    return owner.get(row.get("특약ID"))


def _account(report: Loaded, group: Group, v: variants.Variant, pieces: Sequence[RR.PieceView], built: RR.Built,
             banned: Sequence[str]) -> None:
    """한 종형의 행 수와, 그 요약서에서 쓰지 않은 줄의 사유. 사유는 줄마다 하나다(앞서 남긴 사유가 먼저다)."""
    written = {n for nums in built.numbers.values() for n in nums}
    group.written |= written
    banned_keys = {RR._squash(n) for n in banned}
    excluded = [n for n in built.skipped_riders if RR._squash(n) in banned_keys]
    if excluded:
        report.excluded.setdefault(group.code, [])
        report.excluded[group.code] += [n for n in excluded if n not in report.excluded[group.code]]
    for p in pieces:
        names = p.names or (p.title,)
        for c in p.covers:
            n = c.number
            if n in group.reasons or n in written:
                continue
            if n in built.skipped:
                why = built.skipped[n]
                group.reasons[n] = NO_ROW if why.startswith("스키마가 담지 못하는 꼴") else why
            elif all(name in built.skipped_riders for name in names):
                group.reasons[n] = EXCLUDED if all(RR._squash(x) in banned_keys for x in names) else NO_YEARS
    for n, info in built.no_rows.items():
        report.no_rows[f"{group.code} {n}"] = info
    report.counts[v.id] = {"공시상품코드": v.row["공시상품코드"], "종형명": v.row["종형명"], "특약": len(built.riders),
                           "급부": len(built.benefits), "갱신형특약제외": len(excluded)}


def reason_counts(group: Group) -> collections.Counter:
    """쓰지 않은 줄의 사유별 수. 급부 행이 된 줄(같은 줄이 다른 특약 이름으로는 행이 된 경우)은 세지 않는다."""
    kinds = collections.Counter()
    used = set(group.used)
    for n, why in group.reasons.items():
        if n in group.written or n not in used:
            continue
        kinds[why.split(":", 1)[0].split("(", 1)[0].strip()] += 1
    return kinds


def no_amount_counts(report: Loaded) -> collections.Counter:
    """쓸 급부 행 가운데 금액 없는 급부(지급기준구분이 차등지급, 실손보상, 분할지급, 현물급부)의 값별 수."""
    return collections.Counter(r["지급기준구분"] for r in report.rows["sys_급부"] if r.get("지급기준구분") in NO_AMOUNT_BASES)


def markdown(report: Loaded) -> str:
    """실행 요약. 조각의 문장은 싣지 않는다."""
    head = ["| 공시상품코드 | 종형명 | 특약 | 급부 |", "| --- | --- | --- | --- |"]
    rows = [f"| {c['공시상품코드']} | {c['종형명']} | {c['특약']} | {c['급부']} |" for c in report.counts.values()]
    total = {k: sum(c[k] for c in report.counts.values()) for k in ("특약", "급부")}
    rows.append(f"| 합계 | 정밀비교 종형 {len(report.counts)} | {total['특약']} | {total['급부']} |")
    out = f"종형 행 {len(report.rows['sys_상품종형'])} (정밀비교 {len(report.done)}, 관문전용 {len(report.gate_done)})\n\n"
    out += "\n".join(head + rows) + "\n\n"
    for g in report.groups:
        kinds = reason_counts(g)
        out += (f"{g.code} 요약서: 정밀비교 종형에 드는 세부보장 {len(g.used)}줄, 급부 행이 된 줄 {len(g.written & set(g.used))}, "
                f"쓰지 않은 줄 {sum(kinds.values())}\n")
        if g.kinds:
            out += (f"- 읽을 종({', '.join(sorted(set(g.kinds.values())))})이 아니어서 뺀 세부보장: {len(g.out_of_kind)}줄"
                    "(정밀비교 종형에 드는 줄로 세지 않음)\n")
        out += "".join(f"- {k}: {n}\n" for k, n in kinds.most_common())
        held = sorted((n for n, why in g.reasons.items() if why.startswith(RR.HOLD) and n not in g.written), key=RR._order)
        if held:
            out += f"- 보류한 줄: {', '.join(held)}\n"
        if report.excluded.get(g.code):
            out += f"- 갱신형특약제외로 뺀 특약 {len(report.excluded[g.code])}개\n"
        out += "\n"
    bases = no_amount_counts(report)
    if bases:
        out += (f"금액 없는 급부(행없음 줄이 된 행): {sum(bases.values())}행 ("
                + ", ".join(f"{k} {n}" for k, n in bases.most_common()) + ")\n")
    out += f"ID 겹침: {report.clashes or '없음'}\n"
    out += f"형식 오류: {sum(len(e) for e in report.errors.values()) if report.errors else 0}행\n"
    out += f"시트에 있었는데 이번에 빠지는 행: 특약 {report.dropped.get('sys_특약', 0)}, 급부 {report.dropped.get('sys_급부', 0)}\n"
    out += f"작업 기록: {len(report.logs)}행 (호출모델 '{MODEL}')\n"
    if report.notes:
        out += "\n주의\n" + "\n".join(f"- {n}" for n in report.notes) + "\n"
    return out


def result_of(report: Loaded) -> dict[str, Any]:
    """--result 파일. 조각의 문장은 싣지 않는다(번호, 수, 사유의 앞머리만)."""
    return {
        "종형": report.counts,
        "종형 행": len(report.rows["sys_상품종형"]), "관문전용 종형": sorted(report.gate_done),
        "쓰지 않은 줄": {g.code: dict(reason_counts(g)) for g in report.groups},
        "쓰지 않은 줄 번호": {g.code: {n: why.split(":", 1)[0] for n, why in sorted(g.reasons.items(), key=lambda x: RR._order(x[0]))
                                     if n not in g.written and n in set(g.used)} for g in report.groups},
        **({"읽을 종이 아니어서 뺀 줄": {g.code: len(g.out_of_kind) for g in report.groups if g.kinds}}
           if any(g.kinds for g in report.groups) else {}),
        "금액 없는 급부": dict(no_amount_counts(report).most_common()),
        "갱신형특약제외": report.excluded, "ID 겹침": report.clashes, "형식 오류": report.errors,
        "시트에서 빠지는 행": report.dropped, "주의": report.notes, "기록 행 수": len(report.logs), "시트에 씀": report.written,
    }


PACKAGE_TABS = TABS_WRITTEN          # 급부 패키지의 행 탭(종형, 특약, 급부)
_UNSTAMPED = datetime(2000, 1, 1, tzinfo=KST)   # 패키지의 작업 기록을 만들 때만 쓰는 시각. 로그ID와 실행일시는 비워 둔다


def package_of(report: Loaded, org: str, targets: Path, value_files: Sequence[Path], index: Sequence[Mapping[str, Any]],
               root: Path = ROOT) -> dict[str, Any]:
    """build의 결과를 행 패키지로. 시트에 맞추는 일(가입 한도 잇기, 형식 검사, 검토 대기 풀기, 종형별 다시 뽑음 기록)은 쓸 때
    finish가 한다. 작업 기록은 금액 없는 급부의 추출 기록만 담고, 로그ID와 실행일시는 비운다(쓸 때 채운다)."""
    rows = {t: copy.deepcopy(report.rows[t]) for t in PACKAGE_TABS}
    log = WorkLog(_UNSTAMPED, "sys_급부")
    no_amount_logs(log, report)
    logs = [{**r, "로그ID": None, "실행일시": None} for r in log.rows]
    return {
        **P.header(P.BENEFITS, org, targets, value_files, index, root),
        "행수": {**{t: len(rows[t]) for t in PACKAGE_TABS}, "sys_작업로그": len(logs)},
        "정밀비교종형": sorted(report.done), "관문전용종형": sorted(report.gate_done),
        "다시뽑은종형": report.cover_names,
        "종형별": report.counts, "갱신형특약제외": report.excluded,
        "쓰지않은줄": {g.code: dict(reason_counts(g)) for g in report.groups},
        "주의": report.notes,
        "행": rows, "작업로그": logs,
    }


def from_package(package: Mapping[str, Any]) -> Loaded:
    """행 패키지를 finish에 넣을 Loaded로. 행의 형식 검사는 finish가 하고, ID 겹침은 여기서 다시 센다(패키지 값을 믿지 않는다)."""
    report = Loaded()
    rows = package.get("행") or {}
    for t in PACKAGE_TABS:
        if not isinstance(rows.get(t), list):
            raise P.PackageError(f"행 패키지에 {t} 행이 없음")
        report.rows[t] = copy.deepcopy(rows[t])
    logs = package.get("작업로그") or []
    P.check_counts(package, {**{t: len(report.rows[t]) for t in PACKAGE_TABS}, "sys_작업로그": len(logs)})
    report.done = set(package.get("정밀비교종형") or [])
    report.gate_done = set(package.get("관문전용종형") or [])
    on_rows = {r.get("종형ID") for r in report.rows["sys_상품종형"]}
    if not (report.done | report.gate_done) <= on_rows:
        raise P.PackageError(f"행 패키지의 종형 목록에 종형 행이 없는 종형이 있음: {sorted((report.done | report.gate_done) - on_rows)}")
    report.cover_names = {k: list(v) for k, v in (package.get("다시뽑은종형") or {}).items()}
    report.counts = dict(package.get("종형별") or {})
    report.excluded = dict(package.get("갱신형특약제외") or {})
    report.no_amount = {r["대상행ID"]: r["사유"] for r in logs if r.get("작업단계") == "추출" and r.get("대상열") == NO_AMOUNT_COLUMN}
    report.notes = list(package.get("주의") or [])
    report.clashes = {tab: sorted(k for k, n in collections.Counter(r.get(key) for r in report.rows[tab]).items() if n > 1)
                      for tab, key in (("sys_상품종형", "종형ID"), ("sys_특약", "특약ID"), ("sys_급부", "급부ID"))}
    report.clashes = {t: ids for t, ids in report.clashes.items() if ids}
    return report


def read_package(path: Path, org: str, targets: Path, root: Path = ROOT) -> Loaded:
    """행 패키지를 읽어 체크아웃된 저장소와 맞춰 본다(row_package.read). 그 회사의 값 파일 묶음이 패키지를 만들 때와 같아야 한다."""
    try:
        head = json.loads(Path(path).read_text(encoding="utf-8"))
        codes = {d.get("상품코드") for d in head.get("문서") or []}
    except (OSError, ValueError, AttributeError, TypeError):
        codes = set()                   # 읽지 못하는 패키지는 row_package.read가 사유를 들어 멈춘다
    expected = [p for p in default_values(org, [{"상품코드": c} for c in codes], root / "data" / "crosscheck").values()
                if p.exists()]
    report = from_package(P.read(path, P.BENEFITS, org, targets, root, expected))
    report.package = str(path)
    return report


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--docs", type=Path, help="fetch_disclosure.py의 결과 폴더(index.json과 요약서 PDF). --rows-in이 없으면 꼭 준다")
    p.add_argument("--targets", type=Path, default=TARGETS)
    p.add_argument("--values", action="append", default=[], metavar="코드=경로",
                   help="공시상품코드의 값 파일. 비우면 data/crosscheck/<회사>_<코드>_benefits_2reader.jsonl")
    p.add_argument("--org", default=tables.MERITZ.name, choices=sorted(LAYOUTS),
                   help="요약서 급부 표의 꼴(회사). 값 파일 이름의 앞머리이기도 하다")
    p.add_argument("--only", action="extend", nargs="+", help="이 공시상품코드의 종형만 처리")
    p.add_argument("--dry-run", action="store_true", help="시트에 쓰지 않는다")
    p.add_argument("--snapshot", type=Path, help="시트 대신 이 사본 폴더를 읽는다. 시트에 쓰지 않는다")
    p.add_argument("--result", type=Path, help="종형별 줄 수와 쓰지 않은 줄의 사유를 JSON으로 남길 경로")
    p.add_argument("--rows", type=Path, help="만들어질 행과 행없음 줄의 정보를 JSON으로 남길 경로(원문 구절 열이 들어 있음)")
    p.add_argument("--rows-out", type=Path, metavar="패키지",
                   help="문서로 만든 행을 행 패키지로 남긴다(보통 data/backfill_rows/<회사>_benefits.json). 시트에 쓰지 않는다")
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


def default_values(org: str, index: list[dict[str, Any]], folder: Path = CROSSCHECK) -> dict[str, Path]:
    codes = {e["상품코드"] for e in index}
    return {c: folder / f"{org}_{c}_benefits_2reader.jsonl" for c in sorted(codes)}


def main(argv: list[str] | None = None) -> int:
    args = parse(argv)
    dry_run = args.dry_run or bool(args.snapshot) or bool(args.rows_out)
    if args.snapshot:
        store = snapshot_store(args.snapshot)
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
    if args.rows_in:
        try:
            built = read_package(args.rows_in, args.org, args.targets)
        except P.PackageError as e:
            print("행 패키지를 쓰지 않고 멈춥니다:", e)
            return 1
        built.notes.insert(0, f"행 패키지 {args.rows_in}에서 읽음(문서를 받지 않음)")
    else:
        targets = json.loads(args.targets.read_text(encoding="utf-8"))
        index = json.loads((args.docs / "index.json").read_text(encoding="utf-8"))
        values = default_values(args.org, index)
        for item in args.values:
            code, _, path = item.partition("=")
            values[code] = Path(path)
        built = build(targets, index, args.docs, values, only=args.only, layout=LAYOUTS[args.org])
        if args.rows_out:
            try:
                package = package_of(built, args.org, args.targets, [p for p in values.values() if p.exists()], index)
            except P.PackageError as e:
                print("행 패키지를 만들지 못했습니다:", e)
                return 1
            dry_run = True
    report = finish(store, built, datetime.now(KST), dry_run=dry_run)

    text = markdown(report)
    print(text)
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result_of(report), ensure_ascii=False, indent=1), encoding="utf-8")
    if args.rows:
        args.rows.parent.mkdir(parents=True, exist_ok=True)
        args.rows.write_text(json.dumps({"행": report.rows, "작업로그": report.logs, "행없음": report.no_rows},
                                        ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 두 판독 급부 적재 (교차 확인)\n\n" + text)
    if report.write_error:
        print("시트에 쓰지 못했습니다:", report.write_error)
        return 1
    if report.errors or report.clashes:
        print("형식 검사나 ID 겹침에 걸려 시트에 쓰지 않았습니다:",
              json.dumps({"형식": report.errors, "겹침": report.clashes}, ensure_ascii=False)[:2000])
        return 1
    if not (report.done or report.gate_done):
        print("처리한 종형이 없습니다.")
        return 1
    if args.rows_out:
        P.write(args.rows_out, package)
        print(f"행 패키지를 씀: {args.rows_out} ({json.dumps(package['행수'], ensure_ascii=False)})")
        return 0
    if report.written:
        rows = report.rows
        print(f"시트에 씀: 종형 {len(rows['sys_상품종형'])}, 특약 {len(rows['sys_특약'])}, 급부 {len(rows['sys_급부'])}, "
              f"기록 {len(report.logs)}행")
    else:
        print("시트에 쓰지 않았습니다(--dry-run 또는 --snapshot).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
