import pytest

from app.services.furigana_service import remove_furigana


@pytest.mark.parametrize(
    ("text", "remove_brackets", "expected"),
    [
        ("日本(にほん)", True, "日本"),
        ("日本(にほん)", False, "日本()"),
        ("先生[せんせい]", True, "先生"),
        ("先生[せんせい]", False, "先生[]"),
        ("note (test)", True, "note (test)"),
        ("note (test)", False, "note (test)"),
        ("日本(にほん)へ行く", True, "日本へ行く"),
        ("日本(にほん)へ行く", False, "日本()へ行く"),
        ("日本()", True, "日本"),
        ("日本()", False, "日本()"),
        ("日(に)本(ほん)", True, "日本"),
        ("日(に)本(ほん)", False, "日()本()"),
    ],
)
def test_remove_furigana(text: str, remove_brackets: bool, expected: str) -> None:
    assert remove_furigana(text, remove_brackets=remove_brackets) == expected
