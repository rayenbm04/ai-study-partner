from pydantic import Field

from app.api.v1.schemas.quiz import QuizGenerateRequest


class ExamGenerateRequest(QuizGenerateRequest):
    duration_minutes: int | None = Field(default=None, ge=1, le=600)
    style: str | None = None
