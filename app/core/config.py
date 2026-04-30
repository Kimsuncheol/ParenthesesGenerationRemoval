from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_TITLE: str = "Remove Parentheses Server"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Removes all bracket types and their contents from text."

    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""
    FIREBASE_ADMIN_PROJECT_ID: str = ""
    FIREBASE_ADMIN_CLIENT_EMAIL: str = ""
    FIREBASE_ADMIN_PRIVATE_KEY: str = ""

    NEXT_PUBLIC_COURSE_PATH_CSAT: str = ""
    NEXT_PUBLIC_COURSE_PATH_TOEIC: str = ""
    NEXT_PUBLIC_COURSE_PATH_COLLOCATION: str = ""
    NEXT_PUBLIC_COURSE_PATH_CSAT_IDIOMS: str = ""
    NEXT_PUBLIC_COURSE_PATH_TOEFL_IELTS: str = ""
    NEXT_PUBLIC_COURSE_PATH_EXTREMELY_ADVANCED: str = ""
    NEXT_PUBLIC_COURSE_PATH_JLPT_N1: str = ""
    NEXT_PUBLIC_COURSE_PATH_JLPT_N2: str = ""
    NEXT_PUBLIC_COURSE_PATH_JLPT_N3: str = ""
    NEXT_PUBLIC_COURSE_PATH_JLPT_N4: str = ""
    NEXT_PUBLIC_COURSE_PATH_JLPT_N5: str = ""

    JISHO_API_URL: str = "https://jisho.org/api/v1/search/words"
    JISHO_TIMEOUT_SECONDS: float = 5.0
    JISHO_BATCH_MAX_ITEMS: int = 20
    JISHO_BATCH_MAX_CONCURRENCY: int = 4
    FURIGANA_BATCH_MAX_ITEMS: int = 20

    OPENAI_API_KEY: str = ""
    MANGA_GPT_MODEL: str = "gpt-4o"
    MANGA_DALLE_MODEL: str = "dall-e-3"
    MANGA_MAX_PANELS: int = 6
    MANGA_STYLE_PREFIX: str = (
        "manga panel, black and white, high-contrast ink, screentone shading, "
        "bold outlines, G-pen line weight variation, professional manga style, "
        "avoid color, avoid western comic style, avoid chibi, avoid speech bubbles"
    )

    VOCAB_GPT_MODEL: str = "gpt-4o"
    VOCAB_MAX_PAIRS: int = 20
    QUIZ_GPT_MODEL: str = "gpt-4o"
    QUIZ_MAX_QUESTIONS: int = 20

    KRDICT_API_KEY: str = ""
    KRDICT_TIMEOUT_SECONDS: float = 5.0

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
