from typing import Any

import pytest

from app.core.config import settings
from app.models.quiz_models import QuizGenerateRequest
from app.services import quiz_service


def _no_shuffle(items: list[Any]) -> None:
    return None


def _first_items(items: list[Any], count: int) -> list[Any]:
    return items[:count]


def test_generate_matching_english_general_course(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "NEXT_PUBLIC_COURSE_PATH_CSAT", "english/csat")
    monkeypatch.setattr(quiz_service.random, "sample", _first_items)
    monkeypatch.setattr(quiz_service.random, "shuffle", _no_shuffle)

    captured: dict[str, str] = {}

    def mock_fetch(path: str) -> list[dict[str, Any]]:
        captured["path"] = path
        return [
            {"__id": "doc1", "word": "abandon", "meaning": "to leave behind"},
            {"__id": "doc2", "word": "brief", "meaning": "short"},
            {"__id": "missing", "word": "ignored"},
        ]

    monkeypatch.setattr(quiz_service, "fetch_firestore_documents", mock_fetch)

    response = quiz_service.generate_quiz(
        QuizGenerateRequest(
            quiz_type="matching",
            language="english",
            course="CSAT",
            count=2,
        )
    )

    assert captured["path"] == "english/csat"
    assert response.quiz_type == "matching"
    assert [item.text for item in response.items] == ["abandon", "brief"]
    assert [choice.text for choice in response.choices] == ["to leave behind", "short"]
    assert [(key.item_id, key.choice_id) for key in response.answer_key] == [("q1", "c1"), ("q2", "c2")]


def test_generate_matching_english_collocation_uses_collocation_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "NEXT_PUBLIC_COURSE_PATH_COLLOCATION", "english/collocations")
    monkeypatch.setattr(quiz_service.random, "sample", _first_items)
    monkeypatch.setattr(quiz_service.random, "shuffle", _no_shuffle)
    monkeypatch.setattr(
        quiz_service,
        "fetch_firestore_documents",
        lambda path: [
            {"collocation": "make a decision", "meaning": "decide"},
            {"word": "ignored", "meaning": "missing collocation"},
        ],
    )

    response = quiz_service.generate_quiz(
        QuizGenerateRequest(
            quiz_type="matching",
            language="english",
            course="COLLOCATION",
            count=1,
        )
    )

    assert response.items[0].text == "make a decision"
    assert response.choices[0].text == "decide"


def test_generate_matching_japanese_jlpt_uses_level_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "NEXT_PUBLIC_COURSE_PATH_JLPT_N2", "/japanese/jlpt/n2")
    monkeypatch.setattr(quiz_service.random, "sample", _first_items)
    monkeypatch.setattr(quiz_service.random, "shuffle", _no_shuffle)

    captured: dict[str, str] = {}

    def mock_fetch(path: str) -> list[dict[str, Any]]:
        captured["path"] = path
        return [{"word": "解決", "meaning": "solution"}]

    monkeypatch.setattr(quiz_service, "fetch_firestore_documents", mock_fetch)

    response = quiz_service.generate_quiz(
        QuizGenerateRequest(
            quiz_type="matching",
            language="japanese",
            course="JLPT",
            level="N2",
            count=1,
        )
    )

    assert captured["path"] == "japanese/jlpt/n2"
    assert response.items[0].text == "解決"
    assert response.choices[0].text == "solution"


def test_generate_fill_blank_english_uses_openai_options(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "NEXT_PUBLIC_COURSE_PATH_TOEIC", "english/toeic")
    monkeypatch.setattr(quiz_service.random, "sample", _first_items)
    monkeypatch.setattr(quiz_service.random, "shuffle", _no_shuffle)
    monkeypatch.setattr(
        quiz_service,
        "fetch_firestore_documents",
        lambda path: [
            {
                "word": "abandon",
                "example": "She abandoned the plan.",
                "translation": "She gave up the plan.",
                "partOfSpeech": "verb",
            }
        ],
    )

    def mock_openai(prompt_rows: list[dict[str, Any]]) -> quiz_service._OpenAIFillBlankResponse:
        assert prompt_rows[0]["target"] == "abandon"
        assert prompt_rows[0]["part_of_speech"] == "verb"
        return quiz_service._OpenAIFillBlankResponse.model_validate(
            {
                "results": [
                    {
                        "id": "q1",
                        "sentence": "She _ the plan.",
                        "translation_english": "She gave up the plan.",
                        "translation_korean": None,
                        "options": ["abandoned", "adopted", "admired", "announced"],
                        "answer_text": "abandoned",
                    }
                ]
            }
        )

    monkeypatch.setattr(quiz_service, "_request_fill_blank_options", mock_openai)

    response = quiz_service.generate_quiz(
        QuizGenerateRequest(
            quiz_type="fill_blank",
            language="english",
            course="TOEIC",
            count=1,
        )
    )

    question = response.questions[0]
    assert question.sentence == "She _ the plan."
    assert question.translation_english == "She gave up the plan."
    assert [option.text for option in question.options] == ["abandoned", "adopted", "admired", "announced"]
    assert question.answer_id == "a"
    assert question.answer_text == "abandoned"


def test_generate_fill_blank_collocation_uses_collocation_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "NEXT_PUBLIC_COURSE_PATH_COLLOCATION", "english/collocations")
    monkeypatch.setattr(quiz_service.random, "sample", _first_items)
    monkeypatch.setattr(quiz_service.random, "shuffle", _no_shuffle)
    monkeypatch.setattr(
        quiz_service,
        "fetch_firestore_documents",
        lambda path: [
            {
                "collocation": "make a decision",
                "example": "We need to make a decision today.",
                "translation": "We need to decide today.",
            }
        ],
    )

    monkeypatch.setattr(
        quiz_service,
        "_request_fill_blank_options",
        lambda prompt_rows: quiz_service._OpenAIFillBlankResponse.model_validate(
            {
                "results": [
                    {
                        "id": "q1",
                        "sentence": "We need to _ today.",
                        "translation_english": "We need to decide today.",
                        "options": [
                            "make a decision",
                            "take a break",
                            "hold a meeting",
                            "raise a question",
                        ],
                        "answer_text": "make a decision",
                    }
                ]
            }
        ),
    )

    response = quiz_service.generate_quiz(
        QuizGenerateRequest(
            quiz_type="fill_blank",
            language="english",
            course="COLLOCATION",
            count=1,
        )
    )

    assert response.questions[0].answer_text == "make a decision"


def test_generate_fill_blank_japanese_uses_translation_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "NEXT_PUBLIC_COURSE_PATH_JLPT_N1", "japanese/jlpt/n1")
    monkeypatch.setattr(quiz_service.random, "sample", _first_items)
    monkeypatch.setattr(quiz_service.random, "shuffle", _no_shuffle)
    monkeypatch.setattr(
        quiz_service,
        "fetch_firestore_documents",
        lambda path: [
            {
                "word": "解決",
                "example": "彼は問題を解決した。",
                "Translation(English)": "He solved the problem.",
                "Translation(Korean)": "그는 문제를 해결했다.",
            }
        ],
    )

    monkeypatch.setattr(
        quiz_service,
        "_request_fill_blank_options",
        lambda prompt_rows: quiz_service._OpenAIFillBlankResponse.model_validate(
            {
                "results": [
                    {
                        "id": "q1",
                        "sentence": "彼は問題を_した。",
                        "translation_english": "He solved the problem.",
                        "translation_korean": "그는 문제를 해결했다.",
                        "options": ["解決", "解説", "解放", "解散"],
                        "answer_text": "解決",
                    }
                ]
            }
        ),
    )

    response = quiz_service.generate_quiz(
        QuizGenerateRequest(
            quiz_type="fill_blank",
            language="japanese",
            course="JLPT",
            level="N1",
            count=1,
        )
    )

    question = response.questions[0]
    assert question.sentence == "彼は問題を_した。"
    assert question.translation_english == "He solved the problem."
    assert question.translation_korean == "그는 문제를 해결했다."


def test_generate_quiz_raises_when_not_enough_eligible_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "NEXT_PUBLIC_COURSE_PATH_CSAT", "english/csat")
    monkeypatch.setattr(
        quiz_service,
        "fetch_firestore_documents",
        lambda path: [{"word": "abandon"}],
    )

    with pytest.raises(quiz_service.NotEnoughQuizItemsError) as exc_info:
        quiz_service.generate_quiz(
            QuizGenerateRequest(
                quiz_type="matching",
                language="english",
                course="CSAT",
                count=1,
            )
        )

    assert exc_info.value.requested == 1
    assert exc_info.value.available == 0


def test_validate_fill_blank_rejects_bad_openai_output() -> None:
    raw_results = quiz_service._OpenAIFillBlankResponse.model_validate(
        {
            "results": [
                {
                    "id": "q1",
                    "sentence": "She _ the plan.",
                    "options": ["abandoned", "abandoned", "adopted", "admired"],
                    "answer_text": "abandoned",
                }
            ]
        }
    )

    with pytest.raises(quiz_service.QuizUpstreamError):
        quiz_service._validate_fill_blank_results(raw_results, [{"id": "q1"}])
