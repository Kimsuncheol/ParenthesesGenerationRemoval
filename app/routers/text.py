from fastapi import APIRouter, HTTPException

from app.models.text_models import (
    AddFuriganaRequest,
    AddFuriganaResponse,
    GenerateParenthesesRequest,
    GenerateParenthesesResponse,
    RemoveFuriganaRequest,
    RemoveFuriganaResponse,
    RemoveParenthesesRequest,
    RemoveParenthesesResponse,
    RomanizeRequest,
    RomanizeResponse,
    TranslateRequest,
    TranslateResponse,
    VocabularyBatchLookupRequest,
    VocabularyBatchLookupResponse,
)
from app.services import (
    furigana_service,
    parentheses_service,
    romanization_service,
    translation_service,
    vocabulary_service,
)

router = APIRouter(prefix="/text", tags=["text"])


@router.post("/remove-parentheses", response_model=RemoveParenthesesResponse)
def remove_parentheses_endpoint(body: RemoveParenthesesRequest) -> RemoveParenthesesResponse:
    result = parentheses_service.remove_parentheses(body.text)
    print(result)
    return RemoveParenthesesResponse(original_text=body.text, result_text=result)


@router.post("/remove-furigana", response_model=RemoveFuriganaResponse)
def remove_furigana_endpoint(body: RemoveFuriganaRequest) -> RemoveFuriganaResponse:
    result = furigana_service.remove_furigana(body.text, remove_brackets=body.remove_brackets)
    print(result)
    return RemoveFuriganaResponse(original_text=body.text, result_text=result)


@router.post("/generate-parentheses", response_model=GenerateParenthesesResponse)
def generate_parentheses_endpoint(body: GenerateParenthesesRequest) -> GenerateParenthesesResponse:
    result = parentheses_service.generate_parentheses(body.text)
    print(result)
    return GenerateParenthesesResponse(original_text=body.text, result_text=result)


@router.post("/romanize", response_model=RomanizeResponse)
def romanize_endpoint(body: RomanizeRequest) -> RomanizeResponse:
    result = romanization_service.romanize_ja(body.text)
    print(result);
    return RomanizeResponse(original_text=body.text, romanized_text=result)


@router.post("/add-furigana", response_model=AddFuriganaResponse)
def add_furigana_endpoint(body: AddFuriganaRequest) -> AddFuriganaResponse:
    result = furigana_service.add_furigana(body.text)
    print(result)
    return AddFuriganaResponse(original_text=body.text, result_text=result)


@router.post("/translate", response_model=TranslateResponse)
def translate_endpoint(body: TranslateRequest) -> TranslateResponse:
    try:
        translated = translation_service.translate_ja_to_en(body.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Translation API error: {e}")
    return TranslateResponse(original_text=body.text, translated_text=translated)


@router.post("/vocabulary/batch", response_model=VocabularyBatchLookupResponse)
def vocabulary_batch_lookup_endpoint(body: VocabularyBatchLookupRequest) -> VocabularyBatchLookupResponse:
    results = vocabulary_service.lookup_vocabulary_batch(body.texts)
    print(results)
    return VocabularyBatchLookupResponse(original_texts=body.texts, results=results)
