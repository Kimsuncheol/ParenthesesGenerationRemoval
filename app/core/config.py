from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_TITLE: str = "Remove Parentheses Server"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Removes all bracket types and their contents from text."

    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
