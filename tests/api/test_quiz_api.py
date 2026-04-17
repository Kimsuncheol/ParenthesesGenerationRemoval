import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from main import app
from app.models.quiz_models import MatchingAnswerKeyItem, MatchingChoice, MatchingItem, MatchingQuizResponse
from app.services import quiz_service


client = TestClient(app)


def test_quiz_generate_endpoint_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_generate(body):
        return MatchingQuizResponse(
            quiz_type="matching",
            language=body.language,
            course=body.course,
            level=body.level,
            items=[MatchingItem(id="q1", text="abandon")],
            choices=[MatchingChoice(id="c1", text="to leave behind")],
            answer_key=[MatchingAnswerKeyItem(item_id="q1", choice_id="c1")],
        )

    monkeypatch.setattr(quiz_service, "generate_quiz", mock_generate)

    response = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "matching",
            "language": "english",
            "course": "CSAT",
            "count": 1,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "quiz_type": "matching",
        "language": "english",
        "course": "CSAT",
        "level": None,
        "items": [{"id": "q1", "text": "abandon"}],
        "choices": [{"id": "c1", "text": "to leave behind"}],
        "answer_key": [{"item_id": "q1", "choice_id": "c1"}],
    }


def test_quiz_generate_endpoint_validates_invalid_course_level_combinations() -> None:
    japanese_without_level = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "matching",
            "language": "japanese",
            "course": "JLPT",
            "count": 1,
        },
    )
    english_with_jlpt = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "matching",
            "language": "english",
            "course": "JLPT",
            "level": "N1",
            "count": 1,
        },
    )

    assert japanese_without_level.status_code == 422
    assert english_with_jlpt.status_code == 422


def test_quiz_generate_endpoint_returns_422_when_not_enough_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_generate(body):
        raise quiz_service.NotEnoughQuizItemsError(requested=3, available=1)

    monkeypatch.setattr(quiz_service, "generate_quiz", mock_generate)

    response = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "matching",
            "language": "english",
            "course": "CSAT",
            "count": 3,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["requested"] == 3
    assert response.json()["detail"]["available"] == 1


def test_quiz_generate_endpoint_returns_502_on_upstream_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_generate(body):
        raise quiz_service.QuizUpstreamError("OpenAI quiz generation error: unavailable")

    monkeypatch.setattr(quiz_service, "generate_quiz", mock_generate)

    response = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "fill_blank",
            "language": "english",
            "course": "CSAT",
            "count": 1,
        },
    )

    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"]


def test_openapi_includes_quiz_generate_path() -> None:
    app.openapi_schema = None
    schema = app.openapi()

    assert "/v1/quizzes/generate" in schema["paths"]
