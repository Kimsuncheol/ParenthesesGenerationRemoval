from pydantic import BaseModel


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


class VocabularyLookupRequest(BaseModel):
    text: str


class VocabularyLookupResponse(BaseModel):
    original_text: str
    entry: VocabularyEntry | None


class AddFuriganaRequest(BaseModel):
    text: str


class AddFuriganaResponse(BaseModel):
    original_text: str
    result_text: str
