from fastapi import APIRouter, HTTPException

from app.models.quiz_models import (
    MatchingQuizResponse,
    PopQuizGenerateRequest,
    PopQuizMatchingGameResponse,
    QuizGenerateRequest,
)
from app.services import quiz_service

router = APIRouter(prefix="/v1/pop-quizzes", tags=["pop-quizzes"])


@router.post("/generate", response_model=PopQuizMatchingGameResponse)
def generate_pop_quiz(body: PopQuizGenerateRequest) -> PopQuizMatchingGameResponse:
    quiz_request = QuizGenerateRequest(
        quiz_type="matching",
        language=body.language,
        course=body.course,
        level=body.level,
        day=body.day,
        count=body.count,
    )

    try:
        result = quiz_service.generate_quiz(quiz_request)
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

    if not isinstance(result, MatchingQuizResponse):
        raise HTTPException(
            status_code=502,
            detail="Pop quiz generation returned an unsupported quiz type.",
        )

    return PopQuizMatchingGameResponse(
        pop_quiz_type=body.pop_quiz_type,
        language=result.language,
        course=result.course,
        level=result.level,
        day=result.day,
        items=result.items,
        choices=result.choices,
        answer_key=result.answer_key,
    )
