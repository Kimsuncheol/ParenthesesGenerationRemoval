from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.config import settings


QuizType = Literal["matching", "fill_blank"]
QuizLanguage = Literal["english", "japanese"]
QuizCourse = Literal[
    "CSAT",
    "CSAT_IDIOMS",
    "TOEIC",
    "TOEFL_IELTS",
    "TOEFL_ITELS",
    "EXTREMELY_ADVANCED",
    "COLLOCATION",
    "JLPT",
]
JlptLevel = Literal["N1", "N2", "N3", "N4", "N5"]


class QuizGenerateRequest(BaseModel):
    quiz_type: QuizType
    language: QuizLanguage
    course: QuizCourse
    level: JlptLevel | None = None
    day: int = Field(ge=1)
    count: int = Field(ge=1, le=settings.QUIZ_MAX_ITEMS)

    @model_validator(mode="after")
    def validate_course_level(self) -> "QuizGenerateRequest":
        if self.language == "japanese":
            if self.course != "JLPT":
                raise ValueError("Japanese quizzes currently support only course='JLPT'.")
            if self.level is None:
                raise ValueError("level is required for Japanese JLPT quizzes.")
            return self

        if self.course == "JLPT":
            raise ValueError("course='JLPT' is only valid for language='japanese'.")
        if self.level is not None:
            raise ValueError("level is only valid for Japanese JLPT quizzes.")
        return self


class MatchingItem(BaseModel):
    id: str
    text: str


class MatchingChoice(BaseModel):
    id: str
    text: str


class MatchingAnswerKeyItem(BaseModel):
    item_id: str
    choice_id: str


class MatchingQuizResponse(BaseModel):
    quiz_type: Literal["matching"]
    language: QuizLanguage
    course: QuizCourse
    level: JlptLevel | None
    day: int
    items: list[MatchingItem]
    choices: list[MatchingChoice]
    answer_key: list[MatchingAnswerKeyItem]


class FillBlankOption(BaseModel):
    id: str
    text: str


class FillBlankQuestion(BaseModel):
    id: str
    sentence: str
    translation_english: str | None = None
    translation_korean: str | None = None
    options: list[FillBlankOption]
    answer_id: str
    answer_text: str


class FillBlankQuizResponse(BaseModel):
    quiz_type: Literal["fill_blank"]
    language: QuizLanguage
    course: QuizCourse
    level: JlptLevel | None
    day: int
    questions: list[FillBlankQuestion]


QuizGenerateResponse = MatchingQuizResponse | FillBlankQuizResponse
