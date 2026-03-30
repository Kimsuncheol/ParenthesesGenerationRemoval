from fastapi import FastAPI

from app.core.config import settings
from app.routers import text as text_router

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
)

app.include_router(text_router.router)
