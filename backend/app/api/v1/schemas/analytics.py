from dataclasses import asdict

from pydantic import BaseModel

from app.services.analytics_engine.analytics_service import OverviewAnalytics, SubjectAnalytics


class SubjectAnalyticsResponse(BaseModel):
    subject_id: str
    subject_name: str
    document_count: int
    flashcard_count: int
    flashcards_due_count: int
    quiz_count: int
    exam_count: int
    quiz_attempt_count: int
    average_quiz_score: float | None
    conversation_count: int
    average_mastery: float | None
    weak_concept_count: int
    concepts_practiced: int
    concepts_total: int

    @classmethod
    def from_domain(cls, analytics: SubjectAnalytics) -> "SubjectAnalyticsResponse":
        return cls(**asdict(analytics))


class OverviewAnalyticsResponse(BaseModel):
    subject_count: int
    total_flashcards_due: int
    subjects: list[SubjectAnalyticsResponse]

    @classmethod
    def from_domain(cls, overview: OverviewAnalytics) -> "OverviewAnalyticsResponse":
        return cls(
            subject_count=overview.subject_count,
            total_flashcards_due=overview.total_flashcards_due,
            subjects=[SubjectAnalyticsResponse.from_domain(s) for s in overview.subjects],
        )
