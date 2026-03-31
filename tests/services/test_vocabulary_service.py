from pathlib import Path

import pytest

from app.services import vocabulary_service

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "vocabulary_entries.json"


@pytest.fixture(autouse=True)
def use_fixture_dictionary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vocabulary_service, "VOCABULARY_DATA_PATH", FIXTURE_PATH)
    vocabulary_service._load_dictionary.cache_clear()
    yield
    vocabulary_service._load_dictionary.cache_clear()


def test_lookup_vocabulary_matches_exact_kanji() -> None:
    entry = vocabulary_service.lookup_vocabulary("猫")

    assert entry is not None
    assert entry.word == "猫"
    assert entry.reading == "ねこ"
    assert entry.romanized == "neko"
    assert entry.meanings == ["cat"]


def test_lookup_vocabulary_matches_kana_only_entry() -> None:
    entry = vocabulary_service.lookup_vocabulary("ありがとう")

    assert entry is not None
    assert entry.word is None
    assert entry.reading == "ありがとう"
    assert entry.part_of_speech == ["interjection"]


def test_lookup_vocabulary_matches_mixed_script_entry() -> None:
    entry = vocabulary_service.lookup_vocabulary("食べる")

    assert entry is not None
    assert entry.word == "食べる"
    assert entry.reading == "たべる"
    assert entry.meanings == ["to eat"]


def test_lookup_vocabulary_uses_normalized_surface_fallback() -> None:
    entry = vocabulary_service.lookup_vocabulary("ネコ")

    assert entry is not None
    assert entry.word == "猫"
    assert entry.reading == "ねこ"


def test_lookup_vocabulary_returns_none_for_unknown_or_non_japanese_text() -> None:
    assert vocabulary_service.lookup_vocabulary("存在しない単語") is None
    assert vocabulary_service.lookup_vocabulary("cat") is None


def test_lookup_vocabulary_prefers_common_entry_for_same_reading() -> None:
    entry = vocabulary_service.lookup_vocabulary("かみ")

    assert entry is not None
    assert entry.word == "紙"
    assert entry.meanings == ["paper"]


def test_lookup_vocabulary_romanizes_reading() -> None:
    entry = vocabulary_service.lookup_vocabulary("今日")

    assert entry is not None
    assert entry.reading == "きょう"
    assert entry.romanized == "kyou"
