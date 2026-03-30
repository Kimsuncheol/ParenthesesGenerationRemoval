from fastapi import APIRouter

from app.models.text_models import RemoveParenthesesRequest, RemoveParenthesesResponse
from app.services import parentheses_service

router = APIRouter(prefix="/text", tags=["text"])


@router.post("/remove-parentheses", response_model=RemoveParenthesesResponse)
def remove_parentheses_endpoint(body: RemoveParenthesesRequest) -> RemoveParenthesesResponse:
    result = parentheses_service.remove_parentheses(body.text)
    print(result)
    return RemoveParenthesesResponse(original_text=body.text, result_text=result)
