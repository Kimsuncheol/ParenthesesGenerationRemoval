import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from main import app

client = TestClient(app)


def test_analyze_english_inflection_returns_surface_and_offsets() -> None:
    response = client.post(
        "/analyze",
        json={
            "language": "en",
            "sentence": "I ate apples.",
            "target_base_form": "eat",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "masked_sentence": "I [MASK] apples.",
        "matches": [{"answer": "ate", "start": 2, "end": 5}],
    }


def test_analyze_japanese_inflection_returns_surface_and_offsets() -> None:
    response = client.post(
        "/analyze",
        json={
            "language": "ja",
            "sentence": "昨日りんごを食べました。",
            "target_base_form": "食べる",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "masked_sentence": "昨日りんごを[MASK]ました。",
        "matches": [{"answer": "食べ", "start": 6, "end": 8}],
    }


def test_analyze_japanese_offsets_include_spaces() -> None:
    response = client.post(
        "/analyze",
        json={
            "language": "ja",
            "sentence": "昨日 りんごを食べました。",
            "target_base_form": "食べる",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "masked_sentence": "昨日 りんごを[MASK]ました。",
        "matches": [{"answer": "食べ", "start": 7, "end": 9}],
    }


def test_analyze_returns_404_when_base_form_is_not_found() -> None:
    response = client.post(
        "/analyze",
        json={
            "language": "ja",
            "sentence": "昨日りんごを食べました。",
            "target_base_form": "飲む",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Target base form not found."}


def test_analyze_duplicate_base_form_masks_all_matches() -> None:
    response = client.post(
        "/analyze",
        json={
            "language": "ja",
            "sentence": "食べて、また食べました。",
            "target_base_form": "食べる",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "masked_sentence": "[MASK]て、また[MASK]ました。",
        "matches": [
            {"answer": "食べ", "start": 0, "end": 2},
            {"answer": "食べ", "start": 6, "end": 8},
        ],
    }


def test_analyze_validates_language() -> None:
    response = client.post(
        "/analyze",
        json={
            "language": "ko",
            "sentence": "안녕하세요",
            "target_base_form": "안녕",
        },
    )

    assert response.status_code == 422
