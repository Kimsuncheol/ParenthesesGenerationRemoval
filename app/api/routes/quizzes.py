import logging

from fastapi import APIRouter, HTTPException

from app.models.quiz_models import QuizGenerateRequest, QuizGenerateResponse
from app.services import quiz_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/quizzes", tags=["quizzes"])


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
