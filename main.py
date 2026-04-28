from fastapi import FastAPI

from app.core.config import settings
from app.routers import index as index_router
from app.routers import text as text_router
from app.api.routes import quizzes as quizzes_router
from app.api.routes import vocab as vocab_router
from app.services import krdict_service

krdict_service.init_krdict()

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
)

app.include_router(index_router.router)
app.include_router(text_router.router)
app.include_router(quizzes_router.router)
app.include_router(vocab_router.router)

