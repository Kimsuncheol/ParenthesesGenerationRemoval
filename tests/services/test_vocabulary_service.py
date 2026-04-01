import time
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


def test_lookup_vocabulary_batch_returns_mixed_statuses(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(url: str, params: dict[str, str], timeout: float) -> MockResponse:
        keyword = params["keyword"]
        if keyword == "猫":
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
        if keyword == "今日":
            return MockResponse(
                _mock_jisho_response(
                    [
                        {
                            "is_common": True,
                            "japanese": [{"word": "今日", "reading": "きょう"}],
                            "senses": [
                                {
                                    "english_definitions": ["today"],
                                    "parts_of_speech": ["Noun"],
                                }
                            ],
                        }
                    ]
                )
            )
        if keyword == "存在しない単語":
            return MockResponse(_mock_jisho_response([]))
        if keyword == "障害":
            return MockResponse({}, status_code=503)
        raise AssertionError(f"unexpected keyword: {keyword}")

    monkeypatch.setattr(vocabulary_service.requests, "get", mock_get)

    results = vocabulary_service.lookup_vocabulary_batch(
        ["猫", "cat", "存在しない単語", "", "障害", "今日"]
    )

    assert [item.original_text for item in results] == ["猫", "cat", "存在しない単語", "", "障害", "今日"]
    assert [item.status for item in results] == [
        "ok",
        "invalid_input",
        "not_found",
        "invalid_input",
        "upstream_error",
        "ok",
    ]
    assert results[0].entry is not None and results[0].entry.word == "猫"
    assert results[1].entry is None and results[1].error is None
    assert results[2].entry is None and results[2].error is None
    assert results[4].entry is None and results[4].error == "status=503"
    assert results[5].entry is not None and results[5].entry.romanized == "kyou"


def test_lookup_vocabulary_batch_preserves_order_with_concurrent_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delays = {"猫": 0.05, "今日": 0.01, "食べる": 0.03}

    def mock_get(url: str, params: dict[str, str], timeout: float) -> MockResponse:
        keyword = params["keyword"]
        time.sleep(delays[keyword])
        return MockResponse(
            _mock_jisho_response(
                [
                    {
                        "is_common": True,
                        "japanese": [{"word": keyword, "reading": {"猫": "ねこ", "今日": "きょう", "食べる": "たべる"}[keyword]}],
                        "senses": [
                            {
                                "english_definitions": [keyword],
                                "parts_of_speech": ["Noun"],
                            }
                        ],
                    }
                ]
            )
        )

    monkeypatch.setattr(vocabulary_service.requests, "get", mock_get)

    results = vocabulary_service.lookup_vocabulary_batch(["猫", "今日", "食べる"])

    assert [item.original_text for item in results] == ["猫", "今日", "食べる"]
    assert [item.entry.word if item.entry else None for item in results] == ["猫", "今日", "食べる"]
