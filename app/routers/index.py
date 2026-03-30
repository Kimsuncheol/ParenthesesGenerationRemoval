from fastapi import APIRouter

router = APIRouter(tags=["index"])


@router.get("/")
def index() -> dict[str, str]:
    return {"message": "Remove Parentheses Server is running."}
