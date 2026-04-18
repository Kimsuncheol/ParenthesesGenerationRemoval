from pydantic import BaseModel, Field, model_validator

from app.core.config import settings


class VocabPair(BaseModel):
    example: str = Field(min_length=1)
    meaning_korean: str | None = Field(default=None, min_length=1)
    meaning_english: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def at_least_one_meaning(self) -> "VocabPair":
        if not self.meaning_korean and not self.meaning_english:
            raise ValueError("Provide at least one of meaning_korean or meaning_english.")
        return self


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
