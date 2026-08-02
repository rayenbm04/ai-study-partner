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
from app.repositories.conversation_repo import SqlAlchemyConversationRepository
from app.repositories.document_repo import SqlAlchemyDocumentRepository
from app.repositories.embedding_repo import SqlAlchemyEmbeddingRepository
from app.repositories.message_repo import SqlAlchemyMessageRepository
from app.repositories.refresh_token_repo import SqlAlchemyRefreshTokenRepository
from app.repositories.subject_repo import SqlAlchemySubjectRepository
from app.repositories.user_repo import SqlAlchemyUserRepository
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.factory import build_embedding_provider
from app.services.knowledge_base.ingestion_task import ingest_document_task
from app.services.llm.base import LLMProvider
from app.services.llm.factory import build_llm_provider
from app.services.rag.chat_service import ChatService
from app.services.subject_service import SubjectService

_bearer_scheme = HTTPBearer()


def get_user_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(session)


def get_refresh_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyRefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(session)


def get_subject_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemySubjectRepository:
    return SqlAlchemySubjectRepository(session)


def get_document_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyDocumentRepository:
    return SqlAlchemyDocumentRepository(session)


def get_chunk_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyChunkRepository:
    return SqlAlchemyChunkRepository(session)


def get_embedding_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyEmbeddingRepository:
    return SqlAlchemyEmbeddingRepository(session)


def get_conversation_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyConversationRepository:
    return SqlAlchemyConversationRepository(session)


def get_message_repo(session: AsyncSession = Depends(get_db)) -> SqlAlchemyMessageRepository:
    return SqlAlchemyMessageRepository(session)


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


def get_ingestion_runner() -> Callable[[str], Awaitable[None]]:
    """Route handlers depend on this (not on ingest_document_task directly) so
    tests can override app.dependency_overrides[get_ingestion_runner] with a
    version bound to the test database and fake LLM/embedding providers —
    no real network call ever happens in the test suite."""
    return ingest_document_task


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repo),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = await user_repo.get_by_id(payload["sub"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")
    return user
