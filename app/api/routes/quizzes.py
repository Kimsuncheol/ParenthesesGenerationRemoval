import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import ValidationError

from app.models.quiz_models import (
    JlptLevel,
    QuizAccessRequest,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizLanguage,
    QuizType,
)
from app.services import quiz_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/quizzes", tags=["quizzes"])


def _quiz_access_params(
    quiz_type: QuizType = Query(...),
    language: QuizLanguage = Query(...),
    course: str = Query(...),
    level: JlptLevel | None = Query(None),
    day: int = Query(..., ge=1),
) -> QuizAccessRequest:
    try:
        return QuizAccessRequest(quiz_type=quiz_type, language=language, course=course, level=level, day=day)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


@router.get("", response_model=None)
def review_quiz(params: QuizAccessRequest = Depends(_quiz_access_params)) -> Any:
    try:
        return quiz_service.get_quiz(params)
    except quiz_service.QuizNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except quiz_service.QuizUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("", status_code=204, response_class=Response)
def delete_quiz(params: QuizAccessRequest = Depends(_quiz_access_params)) -> None:
    try:
        quiz_service.delete_quiz(params)
    except quiz_service.QuizNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except quiz_service.QuizUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/generate", response_model=QuizGenerateResponse)
def generate_quiz(body: QuizGenerateRequest) -> QuizGenerateResponse:
    print("generate_quiz request:", body.model_dump())
    try:
        result = quiz_service.generate_quiz(body)
        print("generate_quiz result:", result)
        return result
    except quiz_service.NotEnoughQuizItemsError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "requested": exc.requested,
                "available": exc.available,
            },
        ) from exc
    except quiz_service.QuizUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
