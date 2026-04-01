from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import settings


class RemoveParenthesesRequest(BaseModel):
    text: str


class RemoveParenthesesResponse(BaseModel):
    original_text: str
    result_text: str


class RemoveFuriganaRequest(BaseModel):
    text: str
    remove_brackets: bool = True


class RemoveFuriganaResponse(BaseModel):
    original_text: str
    result_text: str


class RomanizeRequest(BaseModel):
    text: str


class RomanizeResponse(BaseModel):
    original_text: str
    romanized_text: str


class GenerateParenthesesRequest(BaseModel):
    text: str


class GenerateParenthesesResponse(BaseModel):
    original_text: str
    result_text: str


class TranslateRequest(BaseModel):
    text: str


class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str


class VocabularyEntry(BaseModel):
    word: str | None
    reading: str | None
    romanized: str | None
    meanings: list[str]
    part_of_speech: list[str]
    is_common: bool


class VocabularyBatchLookupRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=settings.JISHO_BATCH_MAX_ITEMS)


class VocabularyBatchLookupItem(BaseModel):
    original_text: str
    status: Literal["ok", "not_found", "invalid_input", "upstream_error"]
    entry: VocabularyEntry | None
    error: str | None = None


class VocabularyBatchLookupResponse(BaseModel):
    original_texts: list[str]
    results: list[VocabularyBatchLookupItem]


class AddFuriganaRequest(BaseModel):
    text: str


class AddFuriganaResponse(BaseModel):
    original_text: str
    result_text: str
