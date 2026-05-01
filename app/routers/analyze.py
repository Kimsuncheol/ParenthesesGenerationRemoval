from fastapi import APIRouter, HTTPException

from app.models.text_models import AnalyzeRequest, AnalyzeResponse
from app.services.word_masking_service import (
    TargetBaseFormNotFoundError,
    analyze_word_mask,
)

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(body: AnalyzeRequest) -> AnalyzeResponse:
    try:
        result = analyze_word_mask(
            body.language,
            body.sentence,
            body.target_base_form,
        )
    except TargetBaseFormNotFoundError:
        raise HTTPException(status_code=404, detail="Target base form not found.")

    return AnalyzeResponse(
        masked_sentence=result.masked_sentence,
        matches=[
            {
                "answer": match.answer,
                "start": match.start,
                "end": match.end,
            }
            for match in result.matches
        ],
    )
