import pytest

from postlife import kcd


def test_three_character_end_code_covers_its_subcodes():
    assert kcd.in_range("I63.9", "I60", "I63")
    assert kcd.in_range("D47.3", "D47", "D47")
    assert not kcd.in_range("I64", "I60", "I63")
    assert not kcd.in_range("D47.2", "D47.3", "D47.5")
    assert kcd.in_range("D47.5", "D47.3", "D47.5")


def test_normalize_accepts_common_spellings():
    assert kcd.normalize("c73") == "C73"
    assert kcd.normalize("D471") == "D47.1" == kcd.normalize("D47.1")
    with pytest.raises(ValueError):
        kcd.normalize("갑상선암")


def test_range_relations():
    assert kcd.range_within("I63", "I63", "I60", "I69")
    assert kcd.range_within("D47.3", "D47.5", "D47", "D47")
    assert not kcd.range_within("I60", "I69", "I60", "I63")
    assert kcd.ranges_overlap("I60", "I63", "I63", "I66")
    assert not kcd.ranges_overlap("C00", "C97", "D00", "D09")
    assert kcd.ordered("D47.3", "D47.5") and not kcd.ordered("I63", "I60")
