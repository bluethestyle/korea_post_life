"""시트 점검(scripts/check_sheet.py): 머리글이 어긋난 칸을 모두 알리고, 내용은 자리로 맞춰 사본과 견준다."""
import importlib.util
from pathlib import Path

from postlife.schema import TABS
from postlife.sheets_io import rows_to_values

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_sheet", ROOT / "scripts/check_sheet.py")
check_sheet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_sheet)

TAB = "hum_기준값"


def _rows():
    tab = TABS[TAB]
    return [{c: (f"K{i}" if c == tab.key else None) for c in tab.header} for i in range(3)]


def _raw(rows, tab_name=TAB):
    tab = TABS[tab_name]
    raw = {name: [t.header] for name, t in TABS.items()}
    raw[tab_name] = [tab.header] + rows_to_values(tab, rows)
    return raw


def test_matching_sheet_reports_no_difference():
    rows = _rows()
    lines, ok = check_sheet.inspect(_raw(rows), {TAB: rows})
    assert ok
    line = next(l for l in lines if l.startswith(f"- {TAB}:"))
    assert "머리글 맞음" in line and "값이 다른 칸 0개" in line and "시트에만 0행" in line


def test_broken_header_cell_is_named_and_rows_are_still_compared():
    rows = _rows()
    raw = _raw(rows)
    raw[TAB][0] = ["엉뚱한 글자"] + raw[TAB][0][1:]
    other = next(n for n in TABS if n != TAB)
    raw[other] = [raw[other][0][:-1] + ["다른 이름"]]
    lines, ok = check_sheet.inspect(raw, {TAB: rows})
    assert not ok
    text = "\n".join(lines)
    assert f"- {TAB}: 머리글이 다름: 1번째 칸 '엉뚱한 글자'" in text
    assert f"- {other}: 머리글이 다름" in text                      # 처음 걸린 탭에서 멈추지 않는다
    assert "머리글 다름, 시트 3행, 사본 3행" in text and "값이 다른 칸 0개" in text


def test_changed_added_and_removed_rows_are_counted():
    tab = TABS[TAB]
    rows = _rows()
    column = next(c for c in tab.header if c != tab.key)
    sheet = [dict(rows[0], **{column: "바뀐 값"}), rows[1], dict(rows[2], **{tab.key: "K9"})]
    lines, ok = check_sheet.inspect(_raw(sheet), {TAB: rows})
    assert ok
    text = "\n".join(lines)
    assert "시트에만 1행, 사본에만 1행, 값이 다른 칸 1개" in text
    assert f"K0 · {column}: 사본 None → 시트 '바뀐 값'" in text


def test_missing_tab_is_reported():
    raw = _raw(_rows())
    del raw[TAB]
    lines, ok = check_sheet.inspect(raw, {})
    assert not ok and f"- {TAB}: 시트에 탭이 없음" in lines
