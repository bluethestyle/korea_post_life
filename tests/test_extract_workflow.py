"""추출 워크플로(.github/workflows/extract.yml)의 회사 분기. 두 모델의 검증 결과 파일로 적재하는 회사(초기 적재)는 org 선택지,
rows_in을 받는 회사 목록, 적재 스크립트 분기에 모두 있어야 하고, 적재 스크립트의 --org 선택지와 대상 설정이 있어야 한다."""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import load_reader_product as L  # noqa: E402

yaml = pytest.importorskip("yaml")
WORKFLOW = ROOT / ".github/workflows/extract.yml"


def run_script() -> str:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = data["jobs"]["extract"]["steps"]
    return next(s["run"] for s in steps if s.get("name") == "추출·검증·기록")


def org_options() -> list[str]:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    on = data.get("on", data.get(True))           # PyYAML은 on을 참값으로 읽는다
    return on["workflow_dispatch"]["inputs"]["org"]["options"]


def reader_orgs(script: str) -> set[str]:
    line = next(x for x in script.splitlines() if x.strip().startswith("elif") and "meritz" in x)
    return set(re.findall(r'"\$INPUT_ORG" = "(\w+)"', line))


def rows_in_orgs(script: str) -> set[str]:
    line = next(x for x in script.splitlines() if re.match(r"\s*[\w|]+\)\s*;;", x))
    return set(line.strip().split(")")[0].split("|"))


def test_workflow_parses_and_reader_orgs_are_consistent():
    script = run_script()
    readers = reader_orgs(script)
    assert {"meritz", "samsunglife", "kblife", "kyobo", "hyundai"} <= readers
    assert rows_in_orgs(script) == readers
    assert readers <= set(org_options())
    for org in readers:
        assert org in L.LAYOUTS                      # 두 적재 스크립트의 --org 선택지
        assert (ROOT / "data" / "targets" / f"{org}.json").exists()


def test_reader_branch_runs_both_loaders_with_the_org_targets():
    script = run_script()
    assert 'scripts/load_reader_product.py "${benefits_src[@]}" --org "$INPUT_ORG" --targets "data/targets/$INPUT_ORG.json"' in script
    assert 'scripts/load_reader_conditions.py "${conditions_src[@]}" --org "$INPUT_ORG" --targets "data/targets/$INPUT_ORG.json"' in script
