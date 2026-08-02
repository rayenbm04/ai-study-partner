import functools

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1 import deps
from app.core.config import settings
from app.infrastructure.db import session as db_session
from app.infrastructure.db.base import Base
import app.infrastructure.db.models  # noqa: F401 registers models on Base.metadata
from app.infrastructure.storage.local_storage import LocalStorage
from app.main import create_app
from app.services.knowledge_base.ingestion_task import ingest_document_task
from tests.unit.fakes import FakeEmbeddingProvider, FakeLLMProvider

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_engine, tmp_path):
    test_sessionmaker = async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with test_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    test_storage = LocalStorage(str(tmp_path))

    # Ingestion in tests runs the real pipeline (real extraction, real chunking,
    # real DB writes) against fakes only for the two things that would otherwise
    # make a network call: the LLM (concept tagging) and the embedder. No test
    # ever talks to Gemini/Groq/OpenRouter.
    test_ingestion_runner = functools.partial(
        ingest_document_task,
        session_factory=test_sessionmaker,
        storage=test_storage,
        llm_provider=FakeLLMProvider(response='{"matched": [], "new_concepts": []}'),
        embedding_provider=FakeEmbeddingProvider(dimension=settings.embedding_dimension),
    )

    app = create_app()
    app.dependency_overrides[db_session.get_db] = override_get_db
    app.dependency_overrides[deps.get_storage] = lambda: test_storage
    app.dependency_overrides[deps.get_ingestion_runner] = lambda: test_ingestion_runner

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
