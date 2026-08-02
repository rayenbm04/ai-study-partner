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
from app.repositories.document_repo import SqlAlchemyDocumentRepository
from app.repositories.refresh_token_repo import SqlAlchemyRefreshTokenRepository
from app.repositories.subject_repo import SqlAlchemySubjectRepository
from app.repositories.user_repo import SqlAlchemyUserRepository
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService
from app.services.knowledge_base.ingestion_task import ingest_document_task
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


def get_storage() -> StoragePort:
    return LocalStorage(settings.storage_dir)


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
