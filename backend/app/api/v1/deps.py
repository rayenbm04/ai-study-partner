from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import TokenError, decode_access_token
from app.domain.entities.user import User
# Re-exported (not wrapped) so FastAPI's dependency_overrides — keyed on the
# exact callable used in Depends(...) — can swap this for a test session in
# conftest.py by overriding app.infrastructure.db.session.get_db directly.
from app.infrastructure.db.session import get_db
from app.infrastructure.storage.base import StoragePort
from app.infrastructure.storage.local_storage import LocalStorage
from app.repositories.chunk_repo import SqlAlchemyChunkRepository
from app.repositories.concept_repo import SqlAlchemyConceptRepository
from app.repositories.conversation_repo import SqlAlchemyConversationRepository
from app.repositories.curriculum_repo import SqlAlchemyCurriculumRepository
from app.repositories.document_repo import SqlAlchemyDocumentRepository
from app.repositories.embedding_repo import SqlAlchemyEmbeddingRepository
from app.repositories.flashcard_repo import SqlAlchemyFlashcardRepository
from app.repositories.flashcard_review_repo import SqlAlchemyFlashcardReviewRepository
from app.repositories.message_repo import SqlAlchemyMessageRepository
from app.repositories.progress_repo import SqlAlchemyProgressRepository
from app.repositories.quiz_attempt_repo import SqlAlchemyQuizAttemptRepository
from app.repositories.quiz_repo import SqlAlchemyQuizRepository
from app.repositories.refresh_token_repo import SqlAlchemyRefreshTokenRepository
from app.repositories.student_answer_repo import SqlAlchemyStudentAnswerRepository
from app.repositories.study_plan_repo import SqlAlchemyStudyPlanRepository
from app.repositories.subject_repo import SqlAlchemySubjectRepository
from app.repositories.summary_repo import SqlAlchemySummaryRepository
from app.repositories.user_repo import SqlAlchemyUserRepository
from app.repositories.weak_concept_repo import SqlAlchemyWeakConceptRepository
from app.services.account_service import AccountService
from app.services.analytics_engine.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.factory import build_embedding_provider
from app.services.exam_engine.exam_service import ExamService
from app.services.flashcard_engine.flashcard_service import FlashcardService
from app.services.knowledge_base.ingestion_task import ingest_document_task
from app.services.llm.base import LLMProvider
from app.services.llm.factory import build_llm_provider
from app.services.planning_engine.planning_service import PlanningService
from app.services.progress_engine.progress_service import ProgressService
from app.services.quiz_engine.quiz_service import QuizService
from app.services.rag.chat_service import ChatService
from app.services.subject_pack_service import SubjectPackService
from app.services.subject_service import SubjectService
from app.services.summary_engine.summary_service import SummaryService

_bearer_scheme = HTTPBearer()
_optional_bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(session)


def get_refresh_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyRefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(session)


def get_subject_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemySubjectRepository:
    return SqlAlchemySubjectRepository(session)


def get_document_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyDocumentRepository:
    return SqlAlchemyDocumentRepository(session)


def get_curriculum_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyCurriculumRepository:
    return SqlAlchemyCurriculumRepository(session)


def get_chunk_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyChunkRepository:
    return SqlAlchemyChunkRepository(session)


def get_embedding_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyEmbeddingRepository:
    return SqlAlchemyEmbeddingRepository(session)


def get_conversation_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyConversationRepository:
    return SqlAlchemyConversationRepository(session)


def get_message_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyMessageRepository:
    return SqlAlchemyMessageRepository(session)


def get_concept_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyConceptRepository:
    return SqlAlchemyConceptRepository(session)


def get_summary_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemySummaryRepository:
    return SqlAlchemySummaryRepository(session)


def get_flashcard_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyFlashcardRepository:
    return SqlAlchemyFlashcardRepository(session)


def get_flashcard_review_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyFlashcardReviewRepository:
    return SqlAlchemyFlashcardReviewRepository(session)


def get_quiz_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyQuizRepository:
    return SqlAlchemyQuizRepository(session)


def get_quiz_attempt_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyQuizAttemptRepository:
    return SqlAlchemyQuizAttemptRepository(session)


def get_student_answer_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyStudentAnswerRepository:
    return SqlAlchemyStudentAnswerRepository(session)


def get_progress_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyProgressRepository:
    return SqlAlchemyProgressRepository(session)


def get_weak_concept_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyWeakConceptRepository:
    return SqlAlchemyWeakConceptRepository(session)


def get_study_plan_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyStudyPlanRepository:
    return SqlAlchemyStudyPlanRepository(session)


def get_storage() -> StoragePort:
    return LocalStorage(settings.storage_dir)


def get_llm_provider() -> LLMProvider:
    """Overridden in tests with a FakeLLMProvider — no real network call ever
    happens in the test suite. Same reasoning as get_ingestion_runner."""
    return build_llm_provider(settings)


def get_embedding_provider() -> EmbeddingProvider:
    return build_embedding_provider(settings)


def get_auth_service(
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repo),
    refresh_repo: SqlAlchemyRefreshTokenRepository = Depends(get_refresh_repo),
) -> AuthService:
    return AuthService(user_repo, refresh_repo)


def get_subject_service(
    subject_repo: SqlAlchemySubjectRepository = Depends(get_subject_repo),
) -> SubjectService:
    return SubjectService(subject_repo)


def get_subject_pack_service(
    subject_repo: SqlAlchemySubjectRepository = Depends(get_subject_repo),
    curriculum_repo: SqlAlchemyCurriculumRepository = Depends(get_curriculum_repo),
) -> SubjectPackService:
    return SubjectPackService(subject_repo, curriculum_repo)


def get_document_service(
    document_repo: SqlAlchemyDocumentRepository = Depends(get_document_repo),
    subject_service: SubjectService = Depends(get_subject_service),
    storage: StoragePort = Depends(get_storage),
) -> DocumentService:
    return DocumentService(
        document_repo=document_repo,
        subject_service=subject_service,
        storage=storage,
        max_upload_bytes=settings.max_upload_mb * 1024 * 1024,
    )


def get_chat_service(
    conversation_repo: SqlAlchemyConversationRepository = Depends(get_conversation_repo),
    message_repo: SqlAlchemyMessageRepository = Depends(get_message_repo),
    chunk_repo: SqlAlchemyChunkRepository = Depends(get_chunk_repo),
    document_repo: SqlAlchemyDocumentRepository = Depends(get_document_repo),
    embedding_repo: SqlAlchemyEmbeddingRepository = Depends(get_embedding_repo),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    subject_service: SubjectService = Depends(get_subject_service),
) -> ChatService:
    return ChatService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        chunk_repo=chunk_repo,
        document_repo=document_repo,
        embedding_repo=embedding_repo,
        embedding_provider=embedding_provider,
        llm_provider=llm_provider,
        subject_service=subject_service,
        enable_hyde=settings.rag_enable_hyde,
        enable_multi_query=settings.rag_enable_multi_query,
        enable_rerank=settings.rag_enable_rerank,
        multi_query_count=settings.rag_multi_query_count,
        retrieval_top_k=settings.rag_retrieval_top_k,
        final_context_chunks=settings.rag_final_context_chunks,
        history_messages=settings.rag_history_messages,
    )


def get_summary_service(
    summary_repo: SqlAlchemySummaryRepository = Depends(get_summary_repo),
    document_service: DocumentService = Depends(get_document_service),
    chunk_repo: SqlAlchemyChunkRepository = Depends(get_chunk_repo),
    concept_repo: SqlAlchemyConceptRepository = Depends(get_concept_repo),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> SummaryService:
    return SummaryService(
        summary_repo=summary_repo,
        document_service=document_service,
        chunk_repo=chunk_repo,
        concept_repo=concept_repo,
        llm_provider=llm_provider,
        max_source_chars=settings.summary_max_source_chars,
    )


def get_flashcard_service(
    flashcard_repo: SqlAlchemyFlashcardRepository = Depends(get_flashcard_repo),
    review_repo: SqlAlchemyFlashcardReviewRepository = Depends(get_flashcard_review_repo),
    document_service: DocumentService = Depends(get_document_service),
    subject_service: SubjectService = Depends(get_subject_service),
    chunk_repo: SqlAlchemyChunkRepository = Depends(get_chunk_repo),
    concept_repo: SqlAlchemyConceptRepository = Depends(get_concept_repo),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> FlashcardService:
    return FlashcardService(
        flashcard_repo=flashcard_repo,
        review_repo=review_repo,
        document_service=document_service,
        subject_service=subject_service,
        chunk_repo=chunk_repo,
        concept_repo=concept_repo,
        llm_provider=llm_provider,
        max_source_chars=settings.flashcard_source_max_chars,
        default_generate_count=settings.flashcard_default_generate_count,
        max_generate_count=settings.flashcard_max_generate_count,
    )


def get_quiz_service(
    quiz_repo: SqlAlchemyQuizRepository = Depends(get_quiz_repo),
    attempt_repo: SqlAlchemyQuizAttemptRepository = Depends(get_quiz_attempt_repo),
    answer_repo: SqlAlchemyStudentAnswerRepository = Depends(get_student_answer_repo),
    document_service: DocumentService = Depends(get_document_service),
    subject_service: SubjectService = Depends(get_subject_service),
    chunk_repo: SqlAlchemyChunkRepository = Depends(get_chunk_repo),
    concept_repo: SqlAlchemyConceptRepository = Depends(get_concept_repo),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> QuizService:
    return QuizService(
        quiz_repo=quiz_repo,
        attempt_repo=attempt_repo,
        answer_repo=answer_repo,
        document_service=document_service,
        subject_service=subject_service,
        chunk_repo=chunk_repo,
        concept_repo=concept_repo,
        llm_provider=llm_provider,
        max_source_chars=settings.quiz_source_max_chars,
        default_generate_count=settings.quiz_default_generate_count,
        max_generate_count=settings.quiz_max_generate_count,
    )


def get_exam_service(
    quiz_service: QuizService = Depends(get_quiz_service),
    attempt_repo: SqlAlchemyQuizAttemptRepository = Depends(get_quiz_attempt_repo),
) -> ExamService:
    return ExamService(quiz_service=quiz_service, attempt_repo=attempt_repo)


def get_progress_service(
    progress_repo: SqlAlchemyProgressRepository = Depends(get_progress_repo),
    weak_concept_repo: SqlAlchemyWeakConceptRepository = Depends(get_weak_concept_repo),
    concept_repo: SqlAlchemyConceptRepository = Depends(get_concept_repo),
    flashcard_repo: SqlAlchemyFlashcardRepository = Depends(get_flashcard_repo),
    flashcard_review_repo: SqlAlchemyFlashcardReviewRepository = Depends(get_flashcard_review_repo),
    quiz_repo: SqlAlchemyQuizRepository = Depends(get_quiz_repo),
    quiz_attempt_repo: SqlAlchemyQuizAttemptRepository = Depends(get_quiz_attempt_repo),
    student_answer_repo: SqlAlchemyStudentAnswerRepository = Depends(get_student_answer_repo),
    subject_service: SubjectService = Depends(get_subject_service),
) -> ProgressService:
    return ProgressService(
        progress_repo=progress_repo,
        weak_concept_repo=weak_concept_repo,
        concept_repo=concept_repo,
        flashcard_repo=flashcard_repo,
        flashcard_review_repo=flashcard_review_repo,
        quiz_repo=quiz_repo,
        quiz_attempt_repo=quiz_attempt_repo,
        student_answer_repo=student_answer_repo,
        subject_service=subject_service,
        trend_up_threshold=settings.progress_trend_up_threshold,
        trend_down_threshold=settings.progress_trend_down_threshold,
        weak_min_error_count=settings.weak_concept_min_error_count,
        weak_error_rate_threshold=settings.weak_concept_error_rate_threshold,
        weak_slow_response_seconds=settings.weak_concept_slow_response_seconds,
        weak_decay_drop_threshold=settings.weak_concept_decay_drop_threshold,
        weak_decay_min_previous_score=settings.weak_concept_decay_min_previous_score,
    )


def get_planning_service(
    study_plan_repo: SqlAlchemyStudyPlanRepository = Depends(get_study_plan_repo),
    subject_service: SubjectService = Depends(get_subject_service),
    progress_service: ProgressService = Depends(get_progress_service),
) -> PlanningService:
    return PlanningService(
        study_plan_repo=study_plan_repo,
        subject_service=subject_service,
        progress_service=progress_service,
        default_session_minutes=settings.planning_default_session_minutes,
        default_plan_days=settings.planning_default_plan_days,
    )


def get_analytics_service(
    document_repo: SqlAlchemyDocumentRepository = Depends(get_document_repo),
    quiz_repo: SqlAlchemyQuizRepository = Depends(get_quiz_repo),
    quiz_attempt_repo: SqlAlchemyQuizAttemptRepository = Depends(get_quiz_attempt_repo),
    conversation_repo: SqlAlchemyConversationRepository = Depends(get_conversation_repo),
    flashcard_service: FlashcardService = Depends(get_flashcard_service),
    subject_service: SubjectService = Depends(get_subject_service),
    progress_service: ProgressService = Depends(get_progress_service),
) -> AnalyticsService:
    return AnalyticsService(
        document_repo=document_repo,
        quiz_repo=quiz_repo,
        quiz_attempt_repo=quiz_attempt_repo,
        conversation_repo=conversation_repo,
        flashcard_service=flashcard_service,
        subject_service=subject_service,
        progress_service=progress_service,
    )


def get_account_service(
    subject_repo: SqlAlchemySubjectRepository = Depends(get_subject_repo),
    document_repo: SqlAlchemyDocumentRepository = Depends(get_document_repo),
    study_plan_repo: SqlAlchemyStudyPlanRepository = Depends(get_study_plan_repo),
    storage: StoragePort = Depends(get_storage),
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repo),
    curriculum_repo: SqlAlchemyCurriculumRepository = Depends(get_curriculum_repo),
) -> AccountService:
    return AccountService(
        subject_repo=subject_repo,
        document_repo=document_repo,
        study_plan_repo=study_plan_repo,
        storage=storage,
        user_repo=user_repo,
        curriculum_repo=curriculum_repo,
    )


def get_ingestion_runner() -> Callable[[str], Awaitable[None]]:
    """Route handlers depend on this (not on ingest_document_task directly) so
    tests can override app.dependency_overrides[get_ingestion_runner] with a
    version bound to the test database and fake LLM/embedding providers —
    no real network call ever happens in the test suite."""
    return ingest_document_task


async def _resolve_user_from_token(token: str, user_repo: SqlAlchemyUserRepository) -> User:
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = await user_repo.get_by_id(payload["sub"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repo),
) -> User:
    return await _resolve_user_from_token(credentials.credentials, user_repo)


async def get_current_user_from_header_or_query(
    token: str | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer_scheme),
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repo),
) -> User:
    """Same auth as get_current_user, but also accepts the access token via a
    `?token=` query param. Used only by the document content/preview route —
    a plain browser navigation (window.open, <a href>) can't attach an
    Authorization header, and popup blockers reject window.open() calls made
    after any async work (fetch+blob), so previewing a document on web has to
    be one synchronous window.open() with the token already in the URL. The
    token is short-lived (ACCESS_TOKEN_EXPIRE_MINUTES) and scoped to this
    user's own resources, same trade-off signed/token URLs make elsewhere."""
    bearer_token = credentials.credentials if credentials else token
    if not bearer_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return await _resolve_user_from_token(bearer_token, user_repo)
