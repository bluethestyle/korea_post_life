"""schema.py가 기획 문서 5.5의 표와 같은지 대조한다."""
import re
from pathlib import Path

from postlife.schema import TAB_ORDER, TABS

DOC = Path(__file__).resolve().parents[1] / "docs" / "planning.md"
TYPES = {"문자열": "str", "정수": "int", "실수": "float", "불리언": "bool", "날짜": "date", "일시": "datetime"}


def parse_doc() -> dict[str, list[tuple[str, str, bool]]]:
    text = DOC.read_text(encoding="utf-8").replace("\\_", "_")
    section = text[text.index("### 5.5"):text.index("## 6.")]
    tabs: dict[str, list[tuple[str, str, bool]]] = {}
    current = None
    for line in section.splitlines():
        m = re.match(r"^\*\*((?:sys|hum)_[^*]+)\*\*$", line.strip())
        if m:
            current = m.group(1)
            tabs[current] = []
            continue
        if current and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[1] in TYPES:
                tabs[current].append((cells[0], TYPES[cells[1]], cells[2] == "●"))
    return tabs


def test_tabs_match_planning_doc():
    doc = parse_doc()
    assert list(doc) == TAB_ORDER == list(TABS)
    for name, columns in doc.items():
        assert [(c.name, c.type, c.required) for c in TABS[name].columns] == columns, name


def test_keys_and_parents_exist():
    for tab in TABS.values():
        assert tab.key == tab.header[0]
        assert len(set(tab.header)) == len(tab.header)
        if tab.mode == "replace":
            assert tab.parent in tab.header
            assert tab.parent in {"종형ID", "특약ID", "급부ID"}
