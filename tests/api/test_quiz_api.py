import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from main import app
from app.models.quiz_models import (
    EnglishMatchingItem,
    FillBlankOption,
    FillBlankQuestion,
    FillBlankQuizResponse,
    JapaneseMatchingItem,
    MatchingAnswerKeyItem,
    MatchingChoice,
    MatchingItem,
    MatchingQuizResponse,
)
from app.services import quiz_service


client = TestClient(app)


@pytest.mark.parametrize(
    ("request_json", "expected_language", "expected_course", "expected_level", "expected_day"),
    [
        (
            {
                "pop_quiz_type": "matching_game",
                "language": "english",
                "course": "COLLOCATION",
                "day": 12,
                "count": 1,
            },
            "english",
            "COLLOCATION",
            None,
            12,
        ),
        (
            {
                "pop_quiz_type": "matching_game",
                "language": "english",
                "course": "CSAT_IDIOMS",
                "day": 2,
                "count": 1,
            },
            "english",
            "CSAT_IDIOMS",
            None,
            2,
        ),
        (
            {
                "pop_quiz_type": "matching_game",
                "language": "japanese",
                "course": "JLPT",
                "level": "N2",
                "day": 3,
                "count": 1,
            },
            "japanese",
            "JLPT",
            "N2",
            3,
        ),
    ],
)
def test_pop_quiz_generate_endpoint_success_for_matching_game_courses(
    request_json: dict[str, object],
    expected_language: str,
    expected_course: str,
    expected_level: str | None,
    expected_day: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def mock_generate(body):
        captured["body"] = body
        item = (
            JapaneseMatchingItem(
                id="q1",
                text="解決",
                meaningEnglish="solution",
                meaningKorean="해결",
            )
            if body.language == "japanese"
            else EnglishMatchingItem(id="q1", text="make a decision", meaning="decide")
        )
        return MatchingQuizResponse(
            quiz_type="matching",
            language=body.language,
            course=body.course,
            level=body.level,
            day=body.day,
            items=[item],
            choices=[MatchingChoice(id="c1", text="decide")],
            answer_key=[MatchingAnswerKeyItem(item_id="q1", choice_id="c1")],
        )

    monkeypatch.setattr(quiz_service, "generate_quiz", mock_generate)

    response = client.post("/v1/pop-quizzes/generate", json=request_json)

    assert response.status_code == 200
    response_data = response.json()
    assert captured["body"].quiz_type == "matching"
    assert captured["body"].language == expected_language
    assert captured["body"].course == expected_course
    assert captured["body"].level == expected_level
    assert captured["body"].day == expected_day
    assert response_data["pop_quiz_type"] == "matching_game"
    assert "quiz_type" not in response_data
    assert response_data["course"] == expected_course
    assert response_data["day"] == expected_day
    assert response_data["answer_key"] == [{"item_id": "q1", "choice_id": "c1"}]
    if expected_language == "japanese":
        assert response_data["items"][0]["meaningEnglish"] == "solution"
        assert response_data["items"][0]["meaningKorean"] == "해결"
    else:
        assert response_data["items"][0]["meaning"] == "decide"


@pytest.mark.parametrize(
    "request_json",
    [
        {
            "pop_quiz_type": "flash_card",
            "language": "english",
            "course": "CSAT",
            "day": 1,
            "count": 1,
        },
        {
            "pop_quiz_type": "matching_game",
            "language": "japanese",
            "course": "JLPT",
            "day": 1,
            "count": 1,
        },
        {
            "pop_quiz_type": "matching_game",
            "language": "english",
            "course": "CSAT",
            "level": "N1",
            "day": 1,
            "count": 1,
        },
        {
            "pop_quiz_type": "matching_game",
            "language": "english",
            "course": "CSAT",
            "day": 1,
            "count": 21,
        },
    ],
)
def test_pop_quiz_generate_endpoint_validates_request_before_generation(
    request_json: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_generate(body):
        pytest.fail("pop quiz generation should not run for invalid requests")

    monkeypatch.setattr(quiz_service, "generate_quiz", fail_generate)

    response = client.post("/v1/pop-quizzes/generate", json=request_json)

    assert response.status_code == 422


def test_pop_quiz_generate_endpoint_returns_422_when_not_enough_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_generate(body):
        raise quiz_service.NotEnoughQuizItemsError(requested=3, available=1)

    monkeypatch.setattr(quiz_service, "generate_quiz", mock_generate)

    response = client.post(
        "/v1/pop-quizzes/generate",
        json={
            "pop_quiz_type": "matching_game",
            "language": "english",
            "course": "CSAT",
            "day": 1,
            "count": 3,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["requested"] == 3
    assert response.json()["detail"]["available"] == 1


def test_pop_quiz_generate_endpoint_returns_502_on_upstream_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_generate(body):
        raise quiz_service.QuizUpstreamError("Firestore error: unavailable")

    monkeypatch.setattr(quiz_service, "generate_quiz", mock_generate)

    response = client.post(
        "/v1/pop-quizzes/generate",
        json={
            "pop_quiz_type": "matching_game",
            "language": "english",
            "course": "CSAT",
            "day": 1,
            "count": 1,
        },
    )

    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"]


def test_quiz_generate_endpoint_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_generate(body):
        return MatchingQuizResponse(
            quiz_type="matching",
            language=body.language,
            course=body.course,
            level=body.level,
            day=body.day,
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
            "day": 1,
            "count": 1,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "quiz_type": "matching",
        "language": "english",
        "course": "CSAT",
        "level": None,
        "day": 1,
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
            "day": 1,
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
            "day": 1,
            "count": 1,
        },
    )

    assert japanese_without_level.status_code == 422
    assert english_with_jlpt.status_code == 422


@pytest.mark.parametrize(
    ("input_course", "canonical_course"),
    [
        ("CSAT-Idioms", "CSAT_IDIOMS"),
        ("TOEFL_ITELS", "TOEFL_ITELS"),
        ("Extremely Advanced", "EXTREMELY_ADVANCED"),
        ("Collocation", "COLLOCATION"),
    ],
)
def test_quiz_generate_endpoint_accepts_course_aliases(
    input_course: str,
    canonical_course: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_generate(body):
        return MatchingQuizResponse(
            quiz_type="matching",
            language=body.language,
            course=body.course,
            level=body.level,
            day=body.day,
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
            "course": input_course,
            "day": 1,
            "count": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["course"] == canonical_course


def test_quiz_generate_endpoint_accepts_toefl_ielts_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_generate(body):
        return MatchingQuizResponse(
            quiz_type="matching",
            language=body.language,
            course=body.course,
            level=body.level,
            day=body.day,
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
            "course": "TOEFL_IELTS",
            "day": 1,
            "count": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["course"] == "TOEFL_ITELS"


def test_quiz_generate_endpoint_rejects_invalid_course_language_pairs() -> None:
    japanese_with_english_course = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "matching",
            "language": "japanese",
            "course": "CSAT",
            "level": "N1",
            "day": 1,
            "count": 1,
        },
    )
    unknown_course = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "matching",
            "language": "english",
            "course": "GRE",
            "day": 1,
            "count": 1,
        },
    )

    assert japanese_with_english_course.status_code == 422
    assert unknown_course.status_code == 422


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
            "day": 1,
            "count": 3,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["requested"] == 3
    assert response.json()["detail"]["available"] == 1


@pytest.mark.parametrize("quiz_type", ["matching", "fill_blank"])
def test_quiz_generate_endpoint_rejects_oversized_count_before_generation(
    quiz_type: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_generate(body):
        pytest.fail("quiz generation should not run for oversized count")

    monkeypatch.setattr(quiz_service, "generate_quiz", fail_generate)

    response = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": quiz_type,
            "language": "english",
            "course": "CSAT",
            "day": 1,
            "count": 21,
        },
    )

    assert response.status_code == 422
    assert any(
        "count" in [str(location_part) for location_part in error.get("loc", [])]
        for error in response.json()["detail"]
    )


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
            "day": 1,
            "count": 1,
        },
    )

    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"]


def test_quiz_generate_endpoint_omits_japanese_fill_blank_translation_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_generate(body):
        return FillBlankQuizResponse(
            quiz_type="fill_blank",
            language=body.language,
            course=body.course,
            level=body.level,
            day=body.day,
            questions=[
                FillBlankQuestion(
                    id="q1",
                    sentence="彼は問題を_した。",
                    options=[
                        FillBlankOption(id="a", text="解決"),
                        FillBlankOption(id="b", text="解説"),
                        FillBlankOption(id="c", text="解放"),
                        FillBlankOption(id="d", text="解散"),
                    ],
                    answer_id="a",
                    answer_text="解決",
                )
            ],
        )

    monkeypatch.setattr(quiz_service, "generate_quiz", mock_generate)

    response = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "fill_blank",
            "language": "japanese",
            "course": "JLPT",
            "level": "N1",
            "day": 1,
            "count": 1,
        },
    )

    assert response.status_code == 200
    question = response.json()["questions"][0]
    assert "translation_english" not in question
    assert "translation_korean" not in question
    assert "translationEnglish" not in question
    assert "translationKorean" not in question


def test_quiz_generate_endpoint_serializes_japanese_matching_meaning_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_generate(body):
        return MatchingQuizResponse(
            quiz_type="matching",
            language=body.language,
            course=body.course,
            level=body.level,
            day=body.day,
            items=[
                JapaneseMatchingItem(
                    id="q1",
                    text="食べる",
                    meaningEnglish="to eat",
                    meaningKorean="먹다",
                )
            ],
            choices=[MatchingChoice(id="c1", text="to eat")],
            answer_key=[MatchingAnswerKeyItem(item_id="q1", choice_id="c1")],
        )

    monkeypatch.setattr(quiz_service, "generate_quiz", mock_generate)

    response = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "matching",
            "language": "japanese",
            "course": "JLPT",
            "level": "N5",
            "day": 1,
            "count": 1,
        },
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["meaningEnglish"] == "to eat"
    assert item["meaningKorean"] == "먹다"
    assert "meaning_english" not in item
    assert "meaning_korean" not in item


def test_openapi_includes_quiz_generate_path() -> None:
    app.openapi_schema = None
    schema = app.openapi()

    assert "/v1/quizzes/generate" in schema["paths"]


def test_openapi_includes_pop_quiz_generate_path() -> None:
    app.openapi_schema = None
    schema = app.openapi()

    assert "/v1/pop-quizzes/generate" in schema["paths"]


def test_openapi_excludes_fill_blank_translation_fields() -> None:
    app.openapi_schema = None
    schema = app.openapi()
    properties = schema["components"]["schemas"]["FillBlankQuestion"]["properties"]

    assert "translation_english" not in properties
    assert "translation_korean" not in properties
    assert "translationEnglish" not in properties
    assert "translationKorean" not in properties


def test_openapi_excludes_snake_case_japanese_matching_meaning_fields() -> None:
    app.openapi_schema = None
    schema = app.openapi()
    properties = schema["components"]["schemas"]["JapaneseMatchingItem"]["properties"]

    assert "meaningEnglish" in properties
    assert "meaningKorean" in properties
    assert "meaning_english" not in properties
    assert "meaning_korean" not in properties


def test_quiz_generate_endpoint_requires_day() -> None:
    response = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "matching",
            "language": "english",
            "course": "CSAT",
            "count": 1,
        },
    )

    assert response.status_code == 422


def test_quiz_generate_endpoint_validates_day_is_natural_number() -> None:
    day_zero = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "matching",
            "language": "english",
            "course": "CSAT",
            "day": 0,
            "count": 1,
        },
    )
    day_string = client.post(
        "/v1/quizzes/generate",
        json={
            "quiz_type": "matching",
            "language": "english",
            "course": "CSAT",
            "day": "Day1",
            "count": 1,
        },
    )

    assert day_zero.status_code == 422
    assert day_string.status_code == 422
