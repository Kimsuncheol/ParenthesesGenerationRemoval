from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_TITLE: str = "Remove Parentheses Server"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Removes all bracket types and their contents from text."

    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""
    JISHO_API_URL: str = "https://jisho.org/api/v1/search/words"
    JISHO_TIMEOUT_SECONDS: float = 5.0
    JISHO_BATCH_MAX_ITEMS: int = 20
    JISHO_BATCH_MAX_CONCURRENCY: int = 4
    FURIGANA_BATCH_MAX_ITEMS: int = 20

    OPENAI_API_KEY: str = ""
    MANGA_GPT_MODEL: str = "gpt-4o"
    MANGA_DALLE_MODEL: str = "dall-e-3"
    MANGA_MAX_PANELS: int = 6

    model_config = {"env_file": ".env"}


settings = Settings()
