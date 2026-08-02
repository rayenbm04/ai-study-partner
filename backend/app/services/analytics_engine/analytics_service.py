"""Read-side aggregation over every other engine's existing data — per
docs/ARCHITECTURE.md, the Analytics Engine adds no tables of its own. Every
number here is derived on request from documents, flashcards+reviews,
quizzes+attempts, conversations, and the progress engine's mastery rollup;
nothing is cached or pre-computed, matching the same "recompute from
scratch, it's cheap at this scale" reasoning ProgressService already uses.
"""
from dataclasses import dataclass

from app.domain.repositories.conversation_repository import ConversationRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.repositories.quiz_attempt_repository import QuizAttemptRepository
from app.domain.repositories.quiz_repository import QuizRepository
from app.services.flashcard_engine.flashcard_service import FlashcardService
from app.services.progress_engine.mastery import flatten_leaves
from app.services.progress_engine.progress_service import ProgressService
from app.services.subject_service import SubjectService


@dataclass(frozen=True, slots=True)
class SubjectAnalytics:
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


@dataclass(frozen=True, slots=True)
class OverviewAnalytics:
    subject_count: int
    total_flashcards_due: int
    subjects: list[SubjectAnalytics]


class AnalyticsService:
    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        quiz_repo: QuizRepository,
        quiz_attempt_repo: QuizAttemptRepository,
        conversation_repo: ConversationRepository,
        flashcard_service: FlashcardService,
        subject_service: SubjectService,
        progress_service: ProgressService,
    ):
        self._documents = document_repo
        self._quizzes = quiz_repo
        self._attempts = quiz_attempt_repo
        self._conversations = conversation_repo
        self._flashcards = flashcard_service
        self._subjects = subject_service
        self._progress = progress_service

    async def get_subject_analytics(self, *, user_id: str, subject_id: str) -> SubjectAnalytics:
        subject = await self._subjects.get_owned(user_id, subject_id)

        documents = await self._documents.list_by_subject(subject_id)

        due_cards = await self._flashcards.list_due(user_id=user_id)
        flashcards_due_count = sum(1 for card, _ in due_cards if card.subject_id == subject_id)
        all_cards = await self._flashcards.list_for_subject(user_id=user_id, subject_id=subject_id)
        flashcard_count = len(all_cards)

        quizzes = await self._quizzes.list_by_subject(subject_id)
        quiz_count = sum(1 for q in quizzes if q.kind == "quiz")
        exam_count = sum(1 for q in quizzes if q.kind == "exam")
        quiz_ids = {q.id for q in quizzes}

        attempts = [a for a in await self._attempts.list_by_user(user_id) if a.quiz_id in quiz_ids]
        scored = [a.score for a in attempts if a.score is not None]
        average_quiz_score = round(sum(scored) / len(scored), 1) if scored else None

        conversations = await self._conversations.list_by_subject(user_id, subject_id)

        rollup = await self._progress.get_progress(user_id=user_id, subject_id=subject_id)
        leaves = flatten_leaves(rollup)
        scored_leaves = [leaf.mastery_score for leaf in leaves if leaf.mastery_score is not None]
        average_mastery = round(sum(scored_leaves) / len(scored_leaves), 1) if scored_leaves else None
        weak_concepts = await self._progress.get_weak_concepts(user_id=user_id, subject_id=subject_id)

        return SubjectAnalytics(
            subject_id=subject.id,
            subject_name=subject.name,
            document_count=len(documents),
            flashcard_count=flashcard_count,
            flashcards_due_count=flashcards_due_count,
            quiz_count=quiz_count,
            exam_count=exam_count,
            quiz_attempt_count=len(attempts),
            average_quiz_score=average_quiz_score,
            conversation_count=len(conversations),
            average_mastery=average_mastery,
            weak_concept_count=len(weak_concepts),
            concepts_practiced=len(scored_leaves),
            concepts_total=len(leaves),
        )

    async def get_overview(self, *, user_id: str) -> OverviewAnalytics:
        subjects = await self._subjects.list_for_user(user_id)
        per_subject = [
            await self.get_subject_analytics(user_id=user_id, subject_id=subject.id) for subject in subjects
        ]
        return OverviewAnalytics(
            subject_count=len(subjects),
            total_flashcards_due=sum(s.flashcards_due_count for s in per_subject),
            subjects=per_subject,
        )
