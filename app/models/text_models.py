from pydantic import BaseModel


class RemoveParenthesesRequest(BaseModel):
    text: str


class RemoveParenthesesResponse(BaseModel):
    original_text: str
    result_text: str
