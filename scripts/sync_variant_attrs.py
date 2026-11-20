"""대상 설정(data/targets)에 적힌 종형의 고지 열(variants.OPTIONAL)을 시트의 기존 sys_상품종형 행에 맞춘다.

  python scripts/sync_variant_attrs.py --dry-run                 # 세 회사 모두, 바꿀 칸만 보고 쓰지 않는다
  python scripts/sync_variant_attrs.py --org hanwha               # 한화생명 설정만

종형 속성(고지 질문의 기간, 질병 목록, 소견 범위)을 설정에서 고친 뒤, 급부를 다시 뽑지 않고 시트의 종형 행에만 반영할 때 쓴다.
모델을 부르지 않고 공시 사이트에 접속하지 않는다.

- 종형ID는 설정의 기관코드, 공시상품코드, 종형명으로 만든다(배치와 같은 ids.variant_id).
- 시트에서 그 종형ID인 행의 고지 열 칸만 고친다. 다른 열, 다른 탭, 설정에 없는 종형의 행은 시트에서 읽은 값을 그대로 다시 쓴다.
  설정에 적지 않은 고지 열은 빈칸으로 맞춘다(배치가 종형 행을 만들 때와 같다). 시트 값과 같은 칸은 건드리지 않는다.
- 시트에 없는 종형은 만들지 않고 보고만 한다. 바꿀 칸이 없으면 쓰지 않는다.
- 시트의 머리행이 스키마와 다르면(열 넣기 전) 멈춘다. 고친 행이 형식 검사(validate)에 걸리면 쓰지 않는다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from postlife.extract import variants  # noqa: E402
from postlife.schema import TABS  # noqa: E402
from postlife.sheets_io import _from_cell, _to_cell, values_to_rows  # noqa: E402
from postlife.validate import check_rows  # noqa: E402

TAB = "sys_상품종형"
ORGS = ("epost", "hanwha", "samsungfire")
TARGETS = ROOT / "data" / "targets"


def wanted(targets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """종형ID → 설정에 적힌 고지 열 값. 같은 종형ID가 두 번 나오면 ValueError."""
    out: dict[str, dict[str, Any]] = {}
    for t in targets:
        for vid, attrs in variants.attributes(t).items():
            if vid in out:
                raise ValueError(f"설정에 같은 종형ID가 두 번 나옵니다: {vid}")
            out[vid] = attrs
    return out


def _same(a: Any, b: Any) -> bool:
    """시트에서 읽어 자료형을 맞춘 값과 설정 값이 같은지. True와 1처럼 자료형이 다른 값은 다르게 본다."""
    return a == b and type(a) is type(b)


def plan(values: list[list[Any]], want: dict[str, dict[str, Any]]) -> tuple[list[list[Any]], list[dict[str, Any]], list[str]]:
    """(새 값, 바꾼 칸, 시트에 없는 종형ID). 새 값은 고지 열의 바뀐 칸만 다르고 나머지는 values 그대로다.

    머리행이 스키마와 다르거나 설정의 종형ID가 시트에 두 번 나오면 ValueError.
    """
    tab = TABS[TAB]
    header = [str(h) for h in values[0]] if values else []
    if header != tab.header:
        raise ValueError(f"{TAB}의 머리행이 스키마와 다릅니다. 열 넣기(add-column.yml)를 먼저 돌려야 합니다. 시트={header}")
    kinds = {c.name: c.type for c in tab.columns}
    key = header.index(tab.key)
    out = [list(values[0])]
    changes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in values[1:]:
        row = list(raw)
        vid = str(row[key]) if key < len(row) else ""
        attrs = want.get(vid)
        if attrs is not None:
            if vid in seen:
                raise ValueError(f"시트에 같은 종형ID가 두 번 나옵니다: {vid}")
            seen.add(vid)
            for column, value in attrs.items():
                at = header.index(column)
                old = row[at] if at < len(row) else ""
                before = _from_cell(old, kinds[column])
                if _same(before, value):
                    continue
                row += [""] * (at + 1 - len(row))
                row[at] = _to_cell(value)
                changes.append({"종형ID": vid, "열": column, "전": before, "후": value})
        out.append(row)
    return out, changes, sorted(set(want) - seen)


def load_targets(orgs: list[str], folder: Path = TARGETS) -> list[dict[str, Any]]:
    return [json.loads((folder / f"{org}.json").read_text(encoding="utf-8")) for org in orgs]


def main(argv: list[str] | None = None, backend: Any = None, folder: Path = TARGETS) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--org", choices=ORGS + ("all",), default="all", help="고칠 회사의 설정. all이면 세 회사 모두")
    p.add_argument("--dry-run", action="store_true", help="바꿀 칸만 보고 시트에 쓰지 않는다")
    p.add_argument("--result", type=Path, help="바꾼 칸과 시트에 없는 종형을 적을 JSON 파일")
    args = p.parse_args(argv)
    orgs = list(ORGS) if args.org == "all" else [args.org]
    try:
        want = wanted(load_targets(orgs, folder))
    except ValueError as e:
        print(e)
        return 2
    if backend is None:
        if not all(os.environ.get(k) for k in ("GOOGLE_SERVICE_ACCOUNT_JSON", "SPREADSHEET_ID")):
            print("접속 정보가 없어 건너뜁니다.")
            return 0
        from postlife.sheets_io import RestBackend
        backend = RestBackend.from_env()

    values = backend.get([TAB])[TAB]
    try:
        new, changes, missing = plan(values, want)
    except ValueError as e:
        print(e)
        return 1
    changed = {c["종형ID"] for c in changes}
    lines = [f"설정: {', '.join(orgs)} (종형 {len(want)}개, 고지 열 {', '.join(variants.OPTIONAL)})",
             f"시트에서 찾은 종형 {len(want) - len(missing)}개, 바꿀 칸 {len(changes)}개 (종형 {len(changed)}개)"]
    lines += [f"- {c['종형ID']} · {c['열']}: {c['전']!r} → {c['후']!r}" for c in changes]
    if missing:
        lines.append(f"시트에 없는 종형 {len(missing)}개 (만들지 않음): {', '.join(missing)}")
    text = "\n".join(lines) + "\n"
    print(text)
    _save(args.result, {"설정": orgs, "바꾼 칸": changes, "시트에 없는 종형": missing, "시트에 씀": False})

    rows = values_to_rows(TABS[TAB], new)
    errors = check_rows(TAB, [r for r in rows if r["종형ID"] in changed])
    if errors:
        print("형식 검사에 걸려 시트에 쓰지 않았습니다:", json.dumps(errors, ensure_ascii=False)[:1500])
        _summary(text + "\n형식 검사에 걸려 시트에 쓰지 않았습니다.\n")
        return 1
    if args.dry_run or not changes:
        note = "시트에 쓰지 않았습니다 (--dry-run)." if args.dry_run else "바꿀 칸이 없어 시트에 쓰지 않았습니다."
        print(note)
        _summary(text + "\n" + note + "\n")
        return 0
    backend.overwrite(TAB, new)
    _save(args.result, {"설정": orgs, "바꾼 칸": changes, "시트에 없는 종형": missing, "시트에 씀": True})
    note = f"시트에 씀: {TAB} 종형 {len(changed)}개의 칸 {len(changes)}개."
    print(note)
    _summary(text + "\n" + note + "\n")
    return 0


def _save(path: Path | None, body: dict) -> None:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


def _summary(text: str) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 종형 속성 갱신\n\n" + text.replace("\n", "\n\n"))


if __name__ == "__main__":
    sys.exit(main())
