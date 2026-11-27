"""용어 검사기(proto_src/console4/terms_check.py)가 2026-11-25에 쓰지 않기로 한 말을 잡고, 남기는 말은 잡지 않는지."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "proto_src/console4"))
import terms_check as T  # noqa: E402


def hits(text: str) -> list[str]:
    old, _ = T.check_tokens("t", [(1, text, False, True)], check_names=False)
    return old


def test_새로_쓰지_않기로_한_말을_잡는다():
    for text in ["채점 결과", "판정 모델이 산출", "판정 전용 모델", "담보 비교표의 판정", "판정 필터",
                 "막대 길이를 잰 값", "길이를 재지 않았다", "너비를 잽니다"]:
        assert hits(text), text


def test_남기는_말과_다른_낱말_속_글자는_잡지_않는다():
    for text in ["판정 보류", "판정확률", "판정", "지급액판정", "확률 산정 모델", "비교 결과 필터",
                 "재추출", "재고 수준", "재지정", "측정값"]:
        assert not hits(text), text


def test_응대_화법_금지어_검출():
    for text in ["응대 화법", "응대화법", "응대 화법 미리 보기"]:
        assert hits(text), text
    assert not hits("비교 요약지")
