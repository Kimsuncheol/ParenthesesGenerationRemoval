from pydantic import BaseModel, Field

from app.core.config import settings


class VocabPair(BaseModel):
    example: str = Field(min_length=1)
    meaning_korean: str = Field(min_length=1)


class VocabExtractRequest(BaseModel):
    pairs: list[VocabPair] = Field(min_length=1, max_length=settings.VOCAB_MAX_PAIRS)


class VocabEntry(BaseModel):
    word: str
    meaning_english: str
    meaning_korean: str
    pronunciation: str
    example: str
    translation_english: str
    translation_korean: str
    example_hiragana: str


class VocabExtractResponse(BaseModel):
    results: list[VocabEntry]
