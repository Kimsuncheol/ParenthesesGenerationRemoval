import openai
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.models.schemas import VocabExtractRequest, VocabExtractResponse
from app.services import openai_service

router = APIRouter(prefix="/v1/vocab", tags=["vocab"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/extract-from-pairs", response_model=VocabExtractResponse)
def extract_from_pairs(body: VocabExtractRequest) -> VocabExtractResponse:
    try:
        entries = openai_service.extract_vocab(body.pairs)
    except openai.OpenAIError as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI error: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Unexpected OpenAI response: {exc}") from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"OpenAI response failed validation: {exc.errors()}",
        ) from exc
    return VocabExtractResponse(results=entries)
