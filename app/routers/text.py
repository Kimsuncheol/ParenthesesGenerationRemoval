from fastapi import APIRouter

from app.models.text_models import (
    GenerateParenthesesRequest,
    GenerateParenthesesResponse,
    RemoveParenthesesRequest,
    RemoveParenthesesResponse,
)
from app.services import parentheses_service

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
