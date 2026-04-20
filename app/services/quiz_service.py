from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from typing import Any

import openai
from pydantic import BaseModel, ValidationError

from app.core.config import settings
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
    QuizAccessRequest,
    QuizGenerateRequest,
    QuizGenerateResponse,
    _QuizBase,
)
from app.prompts.quiz_prompt import SYSTEM_PROMPT, build_fill_blank_prompt


class QuizUpstreamError(RuntimeError):
    pass


class QuizNotFoundError(LookupError):
    pass


class NotEnoughQuizItemsError(ValueError):
    def __init__(self, requested: int, available: int) -> None:
        self.requested = requested
        self.available = available
        super().__init__(
            f"Not enough eligible Firestore rows: requested {requested}, available {available}."
        )


@dataclass(frozen=True)
class NormalizedQuizRow:
    source_id: str
    target: str
    meaning: str | None = None
    meaning_english: str | None = None
    meaning_korean: str | None = None
    example: str | None = None
    translation_english: str | None = None
    translation_korean: str | None = None
    part_of_speech: str | None = None


class _OpenAIFillBlankQuestion(BaseModel):
    id: str
    sentence: str
    translation_english: str | None = None
    translation_korean: str | None = None
    options: list[str]
    answer_text: str


class _OpenAIFillBlankResponse(BaseModel):
    results: list[_OpenAIFillBlankQuestion]


_ENGLISH_GENERAL_COURSES = {
    "CSAT",
    "CSAT_IDIOMS",
    "TOEIC",
    "TOEFL_ITELS",
    "EXTREMELY_ADVANCED",
}

_OPTION_IDS = ("a", "b", "c", "d")

_QUIZ_TYPE_PATH: dict[str, str] = {
    "matching": "matching",
    "fill_blank": "fill_in_the_blank",
}


def get_quiz(params: QuizAccessRequest) -> dict[str, Any]:
    try:
        day_collection = _resolve_collection_path(params)
        doc_path = _build_quiz_document_path(day_collection, params.day, params.quiz_type)
        client = _get_firestore_client()
        doc = client.document(doc_path).get()
        if not doc.exists:
            raise QuizNotFoundError(
                f"No quiz found for course={params.course}, day={params.day}, quiz_type={params.quiz_type}."
            )
        return doc.to_dict() or {}
    except (QuizNotFoundError, QuizUpstreamError):
        raise
    except Exception as exc:
        raise QuizUpstreamError(f"Firestore error: {_format_error(exc)}") from exc


def delete_quiz(params: QuizAccessRequest) -> None:
    try:
        day_collection = _resolve_collection_path(params)
        doc_path = _build_quiz_document_path(day_collection, params.day, params.quiz_type)
        client = _get_firestore_client()
        doc_ref = client.document(doc_path)
        if not doc_ref.get().exists:
            raise QuizNotFoundError(
                f"No quiz found for course={params.course}, day={params.day}, quiz_type={params.quiz_type}."
            )
        doc_ref.delete()
    except (QuizNotFoundError, QuizUpstreamError):
        raise
    except Exception as exc:
        raise QuizUpstreamError(f"Firestore error: {_format_error(exc)}") from exc


def _build_quiz_document_path(day_collection: str, day: int, quiz_type: str) -> str:
    quiz_segment = _QUIZ_TYPE_PATH[quiz_type]
    return f"{day_collection}/Day{day}-quiz/{quiz_segment}/data"


def generate_quiz(body: QuizGenerateRequest) -> QuizGenerateResponse:
    collection_path = _resolve_collection_path(body)
    raw_rows = fetch_firestore_documents(collection_path)
    normalized_rows = _normalize_rows(raw_rows, body)

    if len(normalized_rows) < body.count:
        raise NotEnoughQuizItemsError(requested=body.count, available=len(normalized_rows))

    sampled_rows = random.sample(normalized_rows, body.count)
    if body.quiz_type == "matching":
        return _build_matching_response(body, sampled_rows)
    return _build_fill_blank_response(body, sampled_rows)


def fetch_firestore_documents(collection_path: str) -> list[dict[str, Any]]:
    try:
        client = _get_firestore_client()
        docs = client.collection(collection_path.strip("/")).stream()
        rows: list[dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict()
            if isinstance(data, dict):
                rows.append({"__id": doc.id, **data})
        return rows
    except Exception as exc:
        raise QuizUpstreamError(f"Firestore error: {_format_error(exc)}") from exc


def _get_firestore_client() -> Any:
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError as exc:
        raise RuntimeError("firebase-admin is not installed.") from exc

    if not firebase_admin._apps:
        project_id = settings.FIREBASE_ADMIN_PROJECT_ID.strip()
        client_email = settings.FIREBASE_ADMIN_CLIENT_EMAIL.strip()
        private_key = settings.FIREBASE_ADMIN_PRIVATE_KEY.replace("\\n", "\n").strip()

        if not project_id or not client_email or not private_key:
            raise RuntimeError("Firebase Admin credentials are not configured.")

        cred = credentials.Certificate(
            {
                "type": "service_account",
                "project_id": project_id,
                "client_email": client_email,
                "private_key": private_key,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )
        firebase_admin.initialize_app(cred, {"projectId": project_id})

    return firestore.client()


def _resolve_collection_path(body: _QuizBase) -> str:
    if body.language == "japanese":
        level_paths = {
            "N1": settings.NEXT_PUBLIC_COURSE_PATH_JLPT_N1,
            "N2": settings.NEXT_PUBLIC_COURSE_PATH_JLPT_N2,
            "N3": settings.NEXT_PUBLIC_COURSE_PATH_JLPT_N3,
            "N4": settings.NEXT_PUBLIC_COURSE_PATH_JLPT_N4,
            "N5": settings.NEXT_PUBLIC_COURSE_PATH_JLPT_N5,
        }
        path = level_paths.get(body.level or "")
    else:
        course_paths = {
            "CSAT": settings.NEXT_PUBLIC_COURSE_PATH_CSAT,
            "CSAT_IDIOMS": settings.NEXT_PUBLIC_COURSE_PATH_CSAT_IDIOMS,
            "TOEIC": settings.NEXT_PUBLIC_COURSE_PATH_TOEIC,
            "TOEFL_ITELS": settings.NEXT_PUBLIC_COURSE_PATH_TOEFL_IELTS,
            "EXTREMELY_ADVANCED": settings.NEXT_PUBLIC_COURSE_PATH_EXTREMELY_ADVANCED,
            "COLLOCATION": settings.NEXT_PUBLIC_COURSE_PATH_COLLOCATION,
        }
        path = course_paths.get(body.course)

    base_path = _normalize_firestore_path(path)
    if not base_path:
        raise QuizUpstreamError(
            f"Firestore collection path is not configured for course={body.course}"
            + (f", level={body.level}" if body.level else "")
            + "."
        )
    return _build_day_collection_path(base_path, body.day)


def _normalize_firestore_path(path: str | None) -> str | None:
    if not path:
        return None
    normalized = path.strip().strip("/")
    return normalized or None


def _build_day_collection_path(base_path: str, day: int) -> str:
    collection_path = f"{base_path}/Day{day}"
    segments = [segment for segment in collection_path.split("/") if segment]
    if len(segments) % 2 == 0:
        raise QuizUpstreamError(
            f"Firestore Day path must resolve to a collection path: {collection_path}"
        )
    return "/".join(segments)


def _normalize_rows(raw_rows: list[dict[str, Any]], body: QuizGenerateRequest) -> list[NormalizedQuizRow]:
    rows: list[NormalizedQuizRow] = []
    target_field = "collocation" if body.course == "COLLOCATION" else "word"

    for index, raw_row in enumerate(raw_rows, start=1):
        if not isinstance(raw_row, dict):
            continue

        source_id = _as_text(raw_row.get("__id")) or _as_text(raw_row.get("id")) or f"row{index}"
        target = _get_field(raw_row, target_field)
        part_of_speech = _get_field(
            raw_row,
            "part_of_speech",
            "partOfSpeech",
            "part of speech",
            "pos",
            "speech",
        )

        if body.quiz_type == "matching":
            if body.language == "japanese":
                meaning_english, meaning_korean, meaning = _get_japanese_matching_meanings(raw_row)
            else:
                meaning_english = None
                meaning_korean = None
                meaning = _get_field(raw_row, "meaning")

            if target and meaning:
                rows.append(
                    NormalizedQuizRow(
                        source_id=source_id,
                        target=target,
                        meaning=meaning,
                        meaning_english=meaning_english,
                        meaning_korean=meaning_korean,
                        part_of_speech=part_of_speech,
                    )
                )
            continue

        example = _get_field(raw_row, "example")
        if body.language == "japanese":
            translation_english, translation_korean = _get_japanese_translations(raw_row)
            if target and example and translation_english and translation_korean:
                rows.append(
                    NormalizedQuizRow(
                        source_id=source_id,
                        target=target,
                        example=example,
                        translation_english=translation_english,
                        translation_korean=translation_korean,
                        part_of_speech=part_of_speech,
                    )
                )
            continue

        translation = _get_field(
            raw_row,
            "translation",
            "translation_english",
            "translationEnglish",
            "english_translation",
        )
        if target and example and translation:
            rows.append(
                NormalizedQuizRow(
                    source_id=source_id,
                    target=target,
                    example=example,
                    translation_english=translation,
                    translation_korean=None,
                    part_of_speech=part_of_speech,
                )
            )

    return rows


def _get_japanese_translations(row: dict[str, Any]) -> tuple[str | None, str | None]:
    translation_english = _get_field(
        row,
        "Translation(English)",
        "translation_english",
        "translationEnglish",
        "english_translation",
        "translation english",
    )
    translation_korean = _get_field(
        row,
        "Translation(Korean)",
        "translation_korean",
        "translationKorean",
        "korean_translation",
        "translation korean",
    )
    return translation_english, translation_korean


def _get_japanese_matching_meanings(
    row: dict[str, Any],
) -> tuple[str | None, str | None, str | None]:
    direct_english = _get_field(
        row,
        "meaningEnglish",
        "meaning_english",
        "Meaning(English)",
    )
    translation_english = _get_field(
        row,
        "Translation(English)",
        "translation_english",
        "translationEnglish",
        "english_translation",
        "translation english",
    )
    direct_korean = _get_field(
        row,
        "meaningKorean",
        "meaning_korean",
        "Meaning(Korean)",
    )
    translation_korean = _get_field(
        row,
        "Translation(Korean)",
        "translation_korean",
        "translationKorean",
        "korean_translation",
        "translation korean",
    )
    legacy_meaning = _get_field(row, "meaning")

    meaning_english = direct_english or translation_english
    meaning_korean = direct_korean or translation_korean
    choice_meaning = (
        direct_english
        or legacy_meaning
        or translation_english
        or direct_korean
        or translation_korean
    )
    return meaning_english, meaning_korean, choice_meaning


def _build_matching_response(
    body: QuizGenerateRequest,
    rows: list[NormalizedQuizRow],
) -> MatchingQuizResponse:
    items: list[MatchingItem] = []
    choices: list[MatchingChoice] = []
    answer_key: list[MatchingAnswerKeyItem] = []

    for index, row in enumerate(rows, start=1):
        item_id = f"q{index}"
        choice_id = f"c{index}"
        if body.language == "japanese":
            items.append(
                JapaneseMatchingItem(
                    id=item_id,
                    text=row.target,
                    meaningEnglish=row.meaning_english,
                    meaningKorean=row.meaning_korean,
                )
            )
        else:
            items.append(EnglishMatchingItem(id=item_id, text=row.target, meaning=row.meaning))
        choices.append(MatchingChoice(id=choice_id, text=row.meaning or ""))
        answer_key.append(MatchingAnswerKeyItem(item_id=item_id, choice_id=choice_id))

    random.shuffle(items)
    random.shuffle(choices)

    return MatchingQuizResponse(
        quiz_type="matching",
        language=body.language,
        course=body.course,
        level=body.level,
        day=body.day,
        items=items,
        choices=choices,
        answer_key=answer_key,
    )


def _build_fill_blank_response(
    body: QuizGenerateRequest,
    rows: list[NormalizedQuizRow],
) -> FillBlankQuizResponse:
    prompt_rows = [
        {
            "id": f"q{index}",
            "target": row.target,
            "example": row.example,
            "translation_english": row.translation_english,
            "translation_korean": row.translation_korean,
            "part_of_speech": row.part_of_speech,
            "language": body.language,
            "course": body.course,
        }
        for index, row in enumerate(rows, start=1)
    ]

    raw_results = _request_fill_blank_options(prompt_rows)
    questions = _validate_fill_blank_results(raw_results, prompt_rows)

    return FillBlankQuizResponse(
        quiz_type="fill_blank",
        language=body.language,
        course=body.course,
        level=body.level,
        day=body.day,
        questions=questions,
    )


def _request_fill_blank_options(prompt_rows: list[dict[str, Any]]) -> _OpenAIFillBlankResponse:
    user_prompt = build_fill_blank_prompt(prompt_rows)
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.QUIZ_GPT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        raw_text = response.choices[0].message.content
        data = json.loads(raw_text)
        return _OpenAIFillBlankResponse.model_validate(data)
    except (openai.OpenAIError, json.JSONDecodeError, ValidationError, KeyError, IndexError, TypeError) as exc:
        raise QuizUpstreamError(f"OpenAI quiz generation error: {_format_error(exc)}") from exc


def _validate_fill_blank_results(
    raw_results: _OpenAIFillBlankResponse,
    prompt_rows: list[dict[str, Any]],
) -> list[FillBlankQuestion]:
    expected_ids = [str(row["id"]) for row in prompt_rows]
    results = raw_results.results

    if len(results) != len(prompt_rows):
        raise QuizUpstreamError(
            f"OpenAI returned {len(results)} fill-blank results for {len(prompt_rows)} rows."
        )

    questions: list[FillBlankQuestion] = []
    for expected_id, result in zip(expected_ids, results, strict=True):
        if result.id != expected_id:
            raise QuizUpstreamError(
                f"OpenAI returned result id={result.id!r}; expected id={expected_id!r}."
            )

        sentence = result.sentence.strip()
        answer_text = result.answer_text.strip()
        options = [_normalize_option_text(option) for option in result.options]
        options = [option for option in options if option]

        if sentence.count("_") != 1:
            raise QuizUpstreamError(f"OpenAI result {result.id} must contain exactly one '_' blank.")
        if not answer_text:
            raise QuizUpstreamError(f"OpenAI result {result.id} is missing answer_text.")
        if _contains_exact_text(sentence.replace("_", ""), answer_text):
            raise QuizUpstreamError(f"OpenAI result {result.id} leaves the answer visible in the sentence.")
        if len(options) != 4:
            raise QuizUpstreamError(f"OpenAI result {result.id} must include exactly four options.")
        if len({_option_key(option) for option in options}) != 4:
            raise QuizUpstreamError(f"OpenAI result {result.id} includes duplicate options.")
        if sum(1 for option in options if _option_key(option) == _option_key(answer_text)) != 1:
            raise QuizUpstreamError(f"OpenAI result {result.id} must include answer_text exactly once in options.")

        random.shuffle(options)
        response_options = [
            FillBlankOption(id=option_id, text=option)
            for option_id, option in zip(_OPTION_IDS, options, strict=True)
        ]
        answer_id = next(
            option.id
            for option in response_options
            if _option_key(option.text) == _option_key(answer_text)
        )

        questions.append(
            FillBlankQuestion(
                id=result.id,
                sentence=sentence,
                options=response_options,
                answer_id=answer_id,
                answer_text=answer_text,
            )
        )

    return questions


def _get_field(row: dict[str, Any], *names: str) -> str | None:
    normalized_names = {_normalize_key(name) for name in names}
    for key, value in row.items():
        if _normalize_key(str(key)) in normalized_names:
            return _as_text(value)
    return None


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, list):
        text = ", ".join(str(item).strip() for item in value if str(item).strip())
    else:
        text = str(value).strip()
    return text or None


def _normalize_option_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _option_key(value: str) -> str:
    return _normalize_option_text(value).casefold()


def _contains_exact_text(container: str, text: str) -> bool:
    return _option_key(text) in _option_key(container)


def _format_error(exc: Exception) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__
