from pydantic import BaseModel


class RemoveParenthesesRequest(BaseModel):
    text: str


class RemoveParenthesesResponse(BaseModel):
    original_text: str
    result_text: str


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
