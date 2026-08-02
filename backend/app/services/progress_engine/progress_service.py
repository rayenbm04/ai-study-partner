"""Orchestrates mastery recompute and weak-concept detection — the
persistence/evidence-gathering layer around the pure functions in mastery.py
and weakness_detector.py.

Evidence for one concept comes from two places already tracked elsewhere in
the app: the student's latest flashcard review grade (SM-2 state) for any
flashcard tagged to that concept, and every quiz/exam answer (correctness +
time spent) for any question tagged to that concept. Nothing new is tracked
here — this engine only reads what Phases 6 and 7 already record and turns
it into a score.

Both entry points (get_progress, get_weak_concepts) recompute from scratch on
every call rather than on a schedule or in the background — simplest thing
that works, and cheap enough at this scale (one subject's concepts/evidence,
not the whole platform) that a background job isn't worth the complexity yet.
"""
from app.domain.entities.concept import Concept
from app.domain.entities.progress import WeakConcept
from app.domain.repositories.concept_repository import ConceptRepository
from app.domain.repositories.flashcard_repository import FlashcardRepository
from app.domain.repositories.flashcard_review_repository import FlashcardReviewRepository
from app.domain.repositories.progress_repository import ProgressRepository
from app.domain.repositories.quiz_attempt_repository import QuizAttemptRepository
from app.domain.repositories.quiz_repository import QuizRepository
from app.domain.repositories.student_answer_repository import StudentAnswerRepository
from app.domain.repositories.weak_concept_repository import WeakConceptRepository
from app.services.progress_engine import mastery as mastery_module
from app.services.progress_engine import weakness_detector
from app.services.progress_engine.mastery import ConceptMastery, build_rollup, compute_trend, score_from_evidence
from app.services.subject_service import SubjectService


class _ConceptEvidence:
    __slots__ = ("flashcard_grades", "answer_results", "response_times")

    def __init__(self) -> None:
        self.flashcard_grades: list[int] = []
        self.answer_results: list[bool] = []
        self.response_times: list[int] = []


class ProgressService:
    def __init__(
        self,
        *,
        progress_repo: ProgressRepository,
        weak_concept_repo: WeakConceptRepository,
        concept_repo: ConceptRepository,
        flashcard_repo: FlashcardRepository,
        flashcard_review_repo: FlashcardReviewRepository,
        quiz_repo: QuizRepository,
        quiz_attempt_repo: QuizAttemptRepository,
        student_answer_repo: StudentAnswerRepository,
        subject_service: SubjectService,
        trend_up_threshold: float = mastery_module.TREND_UP_THRESHOLD,
        trend_down_threshold: float = mastery_module.TREND_DOWN_THRESHOLD,
        weak_min_error_count: int = weakness_detector.MIN_ERROR_COUNT,
        weak_error_rate_threshold: float = weakness_detector.ERROR_RATE_THRESHOLD,
        weak_slow_response_seconds: float = weakness_detector.SLOW_RESPONSE_SECONDS,
        weak_decay_drop_threshold: float = weakness_detector.DECAY_DROP_THRESHOLD,
        weak_decay_min_previous_score: float = weakness_detector.DECAY_MIN_PREVIOUS_SCORE,
    ):
        self._progress = progress_repo
        self._weak_concepts = weak_concept_repo
        self._concepts = concept_repo
        self._flashcards = flashcard_repo
        self._flashcard_reviews = flashcard_review_repo
        self._quizzes = quiz_repo
        self._attempts = quiz_attempt_repo
        self._answers = student_answer_repo
        self._subjects = subject_service
        self._trend_up_threshold = trend_up_threshold
        self._trend_down_threshold = trend_down_threshold
        self._weak_min_error_count = weak_min_error_count
        self._weak_error_rate_threshold = weak_error_rate_threshold
        self._weak_slow_response_seconds = weak_slow_response_seconds
        self._weak_decay_drop_threshold = weak_decay_drop_threshold
        self._weak_decay_min_previous_score = weak_decay_min_previous_score

    async def get_progress(self, *, user_id: str, subject_id: str) -> list[ConceptMastery]:
        await self._subjects.get_owned(user_id, subject_id)
        concepts = await self._concepts.list_by_subject(subject_id)
        evidence = await self._gather_evidence(user_id=user_id, subject_id=subject_id)
        leaf_results = await self._recompute_and_persist(user_id=user_id, evidence=evidence)
        return build_rollup(concepts, leaf_results)

    async def get_weak_concepts(self, *, user_id: str, subject_id: str) -> list[WeakConcept]:
        await self._subjects.get_owned(user_id, subject_id)
        concepts = await self._concepts.list_by_subject(subject_id)
        concept_ids = {c.id for c in concepts}
        evidence = await self._gather_evidence(user_id=user_id, subject_id=subject_id)
        await self._recompute_and_persist(user_id=user_id, evidence=evidence)

        active = await self._weak_concepts.list_active_by_user(user_id)
        return [w for w in active if w.concept_id in concept_ids]

    async def _gather_evidence(self, *, user_id: str, subject_id: str) -> dict[str, _ConceptEvidence]:
        evidence: dict[str, _ConceptEvidence] = {}

        def _bucket(concept_id: str) -> _ConceptEvidence:
            return evidence.setdefault(concept_id, _ConceptEvidence())

        # --- flashcard signal ---
        flashcards = await self._flashcards.list_by_subject(subject_id)
        concept_by_flashcard = {f.id: f.concept_id for f in flashcards if f.concept_id}
        reviews = await self._flashcard_reviews.list_by_user(user_id)
        for review in reviews:
            concept_id = concept_by_flashcard.get(review.flashcard_id)
            if concept_id and review.last_grade is not None:
                _bucket(concept_id).flashcard_grades.append(review.last_grade)

        # --- quiz/exam signal ---
        quizzes = await self._quizzes.list_by_subject(subject_id)
        quiz_ids = {q.id for q in quizzes}
        concept_by_question: dict[str, str] = {}
        for quiz in quizzes:
            for question in await self._quizzes.list_questions(quiz.id):
                if question.concept_id:
                    concept_by_question[question.id] = question.concept_id

        attempts = await self._attempts.list_by_user(user_id)
        for attempt in attempts:
            if attempt.quiz_id not in quiz_ids:
                continue
            for answer in await self._answers.list_by_attempt(attempt.id):
                concept_id = concept_by_question.get(answer.quiz_question_id)
                if concept_id is None or answer.is_correct is None:
                    continue
                bucket = _bucket(concept_id)
                bucket.answer_results.append(answer.is_correct)
                if answer.time_spent_seconds is not None:
                    bucket.response_times.append(answer.time_spent_seconds)

        return evidence

    async def _recompute_and_persist(
        self, *, user_id: str, evidence: dict[str, _ConceptEvidence]
    ) -> dict[str, tuple[float, str]]:
        leaf_results: dict[str, tuple[float, str]] = {}

        for concept_id, concept_evidence in evidence.items():
            new_score = score_from_evidence(
                flashcard_grades=concept_evidence.flashcard_grades, answer_results=concept_evidence.answer_results
            )
            if new_score is None:
                continue

            previous = await self._progress.get_by_user_and_concept(user_id, concept_id)
            previous_score = previous.mastery_score if previous else None
            trend = compute_trend(
                previous_score=previous_score,
                new_score=new_score,
                up_threshold=self._trend_up_threshold,
                down_threshold=self._trend_down_threshold,
            )
            await self._progress.upsert(
                user_id=user_id, concept_id=concept_id, mastery_score=new_score, trend=trend
            )
            leaf_results[concept_id] = (new_score, trend)

            signal = weakness_detector.detect(
                answer_results=concept_evidence.answer_results,
                response_times=concept_evidence.response_times,
                previous_score=previous_score,
                new_score=new_score,
                min_error_count=self._weak_min_error_count,
                error_rate_threshold=self._weak_error_rate_threshold,
                slow_response_seconds=self._weak_slow_response_seconds,
                decay_drop_threshold=self._weak_decay_drop_threshold,
                decay_min_previous_score=self._weak_decay_min_previous_score,
            )
            existing_active = await self._weak_concepts.get_active_by_user_and_concept(user_id, concept_id)
            if signal is not None:
                if existing_active is not None:
                    await self._weak_concepts.update_active(
                        existing_active.id, reason=signal.reason, confidence=signal.confidence
                    )
                else:
                    await self._weak_concepts.create(
                        user_id=user_id, concept_id=concept_id, reason=signal.reason, confidence=signal.confidence
                    )
            elif existing_active is not None:
                await self._weak_concepts.resolve(existing_active.id)

        return leaf_results
