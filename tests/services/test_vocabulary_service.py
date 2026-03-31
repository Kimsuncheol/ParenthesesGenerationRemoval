from typing import Any

import pytest
import requests

from app.services import vocabulary_service


class MockResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")

    def json(self) -> Any:
        return self._payload


def _mock_jisho_response(data: list[dict[str, Any]]) -> dict[str, Any]:
    return {"meta": {"status": 200}, "data": data}


def test_lookup_vocabulary_matches_exact_kanji(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(url: str, params: dict[str, str], timeout: float) -> MockResponse:
        assert params == {"keyword": "猫"}
        return MockResponse(
            _mock_jisho_response(
                [
                    {
                        "is_common": True,
                        "japanese": [{"word": "猫", "reading": "ねこ"}],
                        "senses": [
                            {
                                "english_definitions": ["cat"],
                                "parts_of_speech": ["Noun"],
                            }
                        ],
                    }
                ]
            )
        )

    monkeypatch.setattr(vocabulary_service.requests, "get", mock_get)

    entry = vocabulary_service.lookup_vocabulary("猫")

    assert entry is not None
    assert entry.word == "猫"
    assert entry.reading == "ねこ"
    assert entry.romanized == "neko"
    assert entry.meanings == ["cat"]
    assert entry.part_of_speech == ["Noun"]
    assert entry.is_common is True


def test_lookup_vocabulary_matches_exact_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(url: str, params: dict[str, str], timeout: float) -> MockResponse:
        return MockResponse(
            _mock_jisho_response(
                [
                    {
                        "is_common": False,
                        "japanese": [{"word": "神", "reading": "かみ"}],
                        "senses": [
                            {
                                "english_definitions": ["god"],
                                "parts_of_speech": ["Noun"],
                            }
                        ],
                    },
                    {
                        "is_common": True,
                        "japanese": [{"word": "紙", "reading": "かみ"}],
                        "senses": [
                            {
                                "english_definitions": ["paper"],
                                "parts_of_speech": ["Noun"],
                            }
                        ],
                    },
                ]
            )
        )

    monkeypatch.setattr(vocabulary_service.requests, "get", mock_get)

    entry = vocabulary_service.lookup_vocabulary("かみ")

    assert entry is not None
    assert entry.word == "神"
    assert entry.reading == "かみ"


def test_lookup_vocabulary_matches_mixed_script_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(url: str, params: dict[str, str], timeout: float) -> MockResponse:
        return MockResponse(
            _mock_jisho_response(
                [
                    {
                        "is_common": True,
                        "japanese": [{"word": "食べる", "reading": "たべる"}],
                        "senses": [
                            {
                                "english_definitions": ["to eat"],
                                "parts_of_speech": ["Ichidan verb", "Transitive verb"],
                            }
                        ],
                    }
                ]
            )
        )

    monkeypatch.setattr(vocabulary_service.requests, "get", mock_get)

    entry = vocabulary_service.lookup_vocabulary("食べる")

    assert entry is not None
    assert entry.word == "食べる"
    assert entry.reading == "たべる"
    assert entry.meanings == ["to eat"]


def test_lookup_vocabulary_returns_none_for_non_japanese_text_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_get(url: str, params: dict[str, str], timeout: float) -> MockResponse:
        raise AssertionError("network should not be called for non-Japanese input")

    monkeypatch.setattr(vocabulary_service.requests, "get", mock_get)

    assert vocabulary_service.lookup_vocabulary("cat") is None


def test_lookup_vocabulary_returns_none_for_no_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vocabulary_service.requests,
        "get",
        lambda url, params, timeout: MockResponse(_mock_jisho_response([])),
    )

    assert vocabulary_service.lookup_vocabulary("存在しない単語") is None


def test_lookup_vocabulary_romanizes_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vocabulary_service.requests,
        "get",
        lambda url, params, timeout: MockResponse(
            _mock_jisho_response(
                [
                    {
                        "is_common": True,
                        "japanese": [{"word": "今日", "reading": "きょう"}],
                        "senses": [
                            {
                                "english_definitions": ["today", "this day"],
                                "parts_of_speech": ["Noun", "Adverb"],
                            }
                        ],
                    }
                ]
            )
        ),
    )

    entry = vocabulary_service.lookup_vocabulary("今日")

    assert entry is not None
    assert entry.reading == "きょう"
    assert entry.romanized == "kyou"


def test_lookup_vocabulary_deduplicates_meanings_and_filters_placeholder_pos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vocabulary_service.requests,
        "get",
        lambda url, params, timeout: MockResponse(
            _mock_jisho_response(
                [
                    {
                        "is_common": True,
                        "japanese": [{"word": "猫", "reading": "ねこ"}],
                        "senses": [
                            {
                                "english_definitions": ["cat", "cat"],
                                "parts_of_speech": ["Noun", "Wikipedia definition"],
                            },
                            {
                                "english_definitions": ["feline"],
                                "parts_of_speech": ["Noun", "Notes"],
                            },
                        ],
                    }
                ]
            )
        ),
    )

    entry = vocabulary_service.lookup_vocabulary("猫")

    assert entry is not None
    assert entry.meanings == ["cat", "feline"]
    assert entry.part_of_speech == ["Noun"]


def test_lookup_vocabulary_raises_for_upstream_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vocabulary_service.requests,
        "get",
        lambda url, params, timeout: MockResponse({}, status_code=503),
    )

    with pytest.raises(requests.HTTPError):
        vocabulary_service.lookup_vocabulary("猫")


def test_lookup_vocabulary_raises_for_invalid_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vocabulary_service.requests,
        "get",
        lambda url, params, timeout: MockResponse({"meta": {"status": 200}}),
    )

    with pytest.raises(RuntimeError, match="data"):
        vocabulary_service.lookup_vocabulary("猫")
