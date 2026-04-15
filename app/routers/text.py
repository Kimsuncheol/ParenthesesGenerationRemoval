from fastapi import APIRouter, HTTPException

from app.models.text_models import (
    AddFuriganaBatchRequest,
    AddFuriganaBatchResponse,
    AddFuriganaRequest,
    AddFuriganaResponse,
    GenerateParenthesesRequest,
    GenerateParenthesesResponse,
    MangaPanelGenerationRequest,
    MangaPanelGenerationResponse,
    RemoveEqualSignRequest,
    RemoveEqualSignResponse,
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
    manga_service,
    parentheses_service,
    romanization_service,
    translation_service,
    vocabulary_service,
)

router = APIRouter(prefix="/text", tags=["text"])


@router.post("/remove-equal-sign", response_model=RemoveEqualSignResponse)
def remove_equal_sign_endpoint(body: RemoveEqualSignRequest) -> RemoveEqualSignResponse:
    result = parentheses_service.remove_equal_sign(body.text, body.remove_side, body.strip_leading_specials)
    print(result)
    return RemoveEqualSignResponse(original_text=body.text, result_text=result)


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
    result = furigana_service.add_furigana(body.text, mode=body.mode)
    print(result)
    return AddFuriganaResponse(original_text=body.text, result_text=result)


@router.post("/add-furigana/batch", response_model=AddFuriganaBatchResponse)
def add_furigana_batch_endpoint(body: AddFuriganaBatchRequest) -> AddFuriganaBatchResponse:
    results = furigana_service.add_furigana_batch(body.texts, mode=body.mode)
    print(results)
    return AddFuriganaBatchResponse(original_texts=body.texts, results=results)


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


@router.post("/manga/generate-panels", response_model=MangaPanelGenerationResponse)
def manga_generate_panels_endpoint(body: MangaPanelGenerationRequest) -> MangaPanelGenerationResponse:
    try:
        descriptions, image_urls = manga_service.generate_manga_panels(
            body.prompt, body.panel_count, body.character_description
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Manga generation error: {e}")
    return MangaPanelGenerationResponse(
        prompt=body.prompt,
        panel_count=body.panel_count,
        panel_descriptions=descriptions,
        image_urls=image_urls,
    )
