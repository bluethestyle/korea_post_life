"""규칙 추출과 대조 표를 견주는 스크립트의 한도 칸 비교."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import compare_table_rules as compare  # noqa: E402
from postlife.extract.table_rules import Reading  # noqa: E402


def row(limit: str, note: str = "-") -> list[str]:
    return ["R001-1", "100", "-", "-", "-", "-", "0", limit, note]


def test_limit_counts_keep_the_word_before_the_number():
    assert compare.limit_counts("각 치료행위별 연간 1회한") == ["연간1회"]
    assert compare.limit_counts("1일 1회, 연간 3회한") == ["1일", "1회", "연간3회"]
    assert compare.limit_counts("최초 1회한") == ["최초1회"]
    assert compare.limit_counts("수술 1회당") == ["1회"]


def test_shortened_limit_in_the_other_table_is_the_same_limit():
    """대조 표가 "1회에 한하여"를 "1회한"으로 줄여 적어도 횟수와 앞말이 같으면 같은 한도다."""
    mine = [Reading("가나 치료비", limit="각 치료행위별 연간 1회에 한하여")]
    assert compare.differences(mine, row("각 치료행위별 연간 1회한")) == []
    mine = [Reading("가나 치료비", limit="수술은 수술 1회당 지급하며, 다라치료, 마바치료는 각각 연간 1회에 한하여 지급함")]
    assert compare.differences(mine, row("수술 1회당, 다라치료·마바치료 각각 연간 1회한")) == []


def test_limit_with_another_qualifier_or_count_is_still_different():
    mine = [Reading("가나 치료비", limit="연간 1회에 한하여")]
    assert compare.differences(mine, row("최초 1회한")) == ['한도: 대조 표의 "최초 1회한"가 규칙 결과에 없음']
    assert '한도: 대조 표의 "연간 2회한"가 규칙 결과에 없음' in compare.differences(mine, row("연간 2회한"))
    assert compare.differences([Reading("가나 치료비")], row("연간 1회한")) == ['한도: 대조 표의 "연간 1회한"가 규칙 결과에 없음']


def test_limit_only_in_rules_is_reported_unless_its_counts_are_in_the_other_table():
    mine = [Reading("가나 수술비", limit="수술 1회당 / 같은 종류의 수술을 2회 이상 받은 경우에는 1회에 한하여 지급")]
    found = compare.differences(mine, row("수술 1회당"))
    assert len(found) == 1 and found[0].startswith('한도: 규칙의 "같은 종류의 수술을 2회 이상')
    assert compare.differences(mine, row("수술 1회당", "같은 수술 2회 이상이면 1회만 지급")) == []
