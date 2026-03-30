from fastapi import APIRouter, HTTPException

from app.models.text_models import (
    GenerateParenthesesRequest,
    GenerateParenthesesResponse,
    RemoveParenthesesRequest,
    RemoveParenthesesResponse,
    TranslateRequest,
    TranslateResponse,
)
from app.services import parentheses_service, translation_service

router = APIRouter(prefix="/text", tags=["text"])


@router.post("/remove-parentheses", response_model=RemoveParenthesesResponse)
def remove_parentheses_endpoint(body: RemoveParenthesesRequest) -> RemoveParenthesesResponse:
    result = parentheses_service.remove_parentheses(body.text)
    print(result)
    return RemoveParenthesesResponse(original_text=body.text, result_text=result)


@router.post("/generate-parentheses", response_model=GenerateParenthesesResponse)
def generate_parentheses_endpoint(body: GenerateParenthesesRequest) -> GenerateParenthesesResponse:
    result = parentheses_service.generate_parentheses(body.text)
    print(result)
    return GenerateParenthesesResponse(original_text=body.text, result_text=result)


@router.post("/translate", response_model=TranslateResponse)
def translate_endpoint(body: TranslateRequest) -> TranslateResponse:
    try:
        translated = translation_service.translate_ja_to_en(body.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Translation API error: {e}")
    return TranslateResponse(original_text=body.text, translated_text=translated)
