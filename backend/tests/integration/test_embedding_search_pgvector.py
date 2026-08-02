"""Tests EmbeddingRepository.search() against a real Postgres+pgvector
instance (via the `pg_engine` fixture in conftest.py). This is the one piece
of the pipeline SQLite structurally cannot verify — pgvector's cosine
distance operator (`<=>`) doesn't exist there — so everything else in this
test suite uses SQLite, and only this file pays the cost of booting a real
embedded Postgres.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.domain.entities.chunk import ChunkDraft
from app.repositories.chunk_repo import SqlAlchemyChunkRepository
from app.repositories.document_repo import SqlAlchemyDocumentRepository
from app.repositories.embedding_repo import SqlAlchemyEmbeddingRepository
from app.repositories.subject_repo import SqlAlchemySubjectRepository
from app.repositories.user_repo import SqlAlchemyUserRepository


def _vec(*components: float) -> list[float]:
    """The embeddings table's vector column is fixed at settings.embedding_dimension
    (matches the real embedding model in production) — pad short, readable
    test vectors out to that width with zeros."""
    padded = list(components) + [0.0] * (settings.embedding_dimension - len(components))
    return padded[: settings.embedding_dimension]


async def _seed(session: AsyncSession, *, subject_name: str = "Physics"):
    user_repo = SqlAlchemyUserRepository(session)
    subject_repo = SqlAlchemySubjectRepository(session)
    document_repo = SqlAlchemyDocumentRepository(session)
    chunk_repo = SqlAlchemyChunkRepository(session)
    embedding_repo = SqlAlchemyEmbeddingRepository(session)

    user = await user_repo.create(
        email=f"{uuid.uuid4()}@example.com", firstname="A", lastname="B", hashed_password="x"
    )
    subject = await subject_repo.create(user_id=user.id, name=subject_name, description=None, color=None, icon=None)
    document = await document_repo.create(
        document_id=str(uuid.uuid4()), subject_id=subject.id, original_filename="f.txt",
        storage_path="x", file_type=".txt",
    )
    return user, subject, document, chunk_repo, embedding_repo


async def _add_child_chunk(chunk_repo, embedding_repo, *, subject_id, document_id, content, vector, model_name):
    drafts = [
        ChunkDraft(content=content, chunk_type="child", parent_index=None, page=1, section_title=None,
                   chapter=None, token_count=len(content.split())),
    ]
    chunks = await chunk_repo.bulk_create(document_id=document_id, subject_id=subject_id, drafts=drafts)
    chunk = chunks[0]
    await embedding_repo.bulk_create(chunk_ids=[chunk.id], vectors=[vector], model_name=model_name)
    return chunk


async def test_search_orders_by_cosine_distance_closest_first(pg_engine):
    test_sessionmaker = async_sessionmaker(bind=pg_engine, expire_on_commit=False, class_=AsyncSession)
    async with test_sessionmaker() as session:
        user, subject, document, chunk_repo, embedding_repo = await _seed(session)

        close = await _add_child_chunk(
            chunk_repo, embedding_repo, subject_id=subject.id, document_id=document.id,
            content="close", vector=_vec(1.0, 0.0, 0.0), model_name="test-model",
        )
        far = await _add_child_chunk(
            chunk_repo, embedding_repo, subject_id=subject.id, document_id=document.id,
            content="far", vector=_vec(0.0, 1.0, 0.0), model_name="test-model",
        )
        await session.commit()

        results = await embedding_repo.search(
            subject_id=subject.id, query_vector=_vec(0.9, 0.1, 0.0), top_k=5, model_name="test-model"
        )

    assert [chunk_id for chunk_id, _distance in results] == [close.id, far.id]
    # A near-identical vector should be much closer (lower distance) than an orthogonal one.
    assert results[0][1] < results[1][1]


async def test_search_filters_by_subject(pg_engine):
    test_sessionmaker = async_sessionmaker(bind=pg_engine, expire_on_commit=False, class_=AsyncSession)
    async with test_sessionmaker() as session:
        _, subject_a, document_a, chunk_repo, embedding_repo = await _seed(session, subject_name="Subject A")
        user_b = await SqlAlchemyUserRepository(session).create(
            email=f"{uuid.uuid4()}@example.com", firstname="C", lastname="D", hashed_password="x"
        )
        subject_b = await SqlAlchemySubjectRepository(session).create(
            user_id=user_b.id, name="Subject B", description=None, color=None, icon=None
        )
        document_b = await SqlAlchemyDocumentRepository(session).create(
            document_id=str(uuid.uuid4()), subject_id=subject_b.id, original_filename="g.txt",
            storage_path="y", file_type=".txt",
        )

        chunk_a = await _add_child_chunk(
            chunk_repo, embedding_repo, subject_id=subject_a.id, document_id=document_a.id,
            content="a", vector=_vec(1.0, 0.0, 0.0), model_name="test-model",
        )
        await _add_child_chunk(
            chunk_repo, embedding_repo, subject_id=subject_b.id, document_id=document_b.id,
            content="b", vector=_vec(1.0, 0.0, 0.0), model_name="test-model",
        )
        await session.commit()

        results = await embedding_repo.search(
            subject_id=subject_a.id, query_vector=_vec(1.0, 0.0, 0.0), top_k=5, model_name="test-model"
        )

    assert [chunk_id for chunk_id, _distance in results] == [chunk_a.id]


async def test_search_filters_by_model_name(pg_engine):
    test_sessionmaker = async_sessionmaker(bind=pg_engine, expire_on_commit=False, class_=AsyncSession)
    async with test_sessionmaker() as session:
        _, subject, document, chunk_repo, embedding_repo = await _seed(session)

        old_model_chunk = await _add_child_chunk(
            chunk_repo, embedding_repo, subject_id=subject.id, document_id=document.id,
            content="old", vector=_vec(1.0, 0.0, 0.0), model_name="old-model",
        )
        new_model_chunk = await _add_child_chunk(
            chunk_repo, embedding_repo, subject_id=subject.id, document_id=document.id,
            content="new", vector=_vec(1.0, 0.0, 0.0), model_name="new-model",
        )
        await session.commit()

        results = await embedding_repo.search(
            subject_id=subject.id, query_vector=_vec(1.0, 0.0, 0.0), top_k=5, model_name="new-model"
        )

    result_ids = [chunk_id for chunk_id, _distance in results]
    assert new_model_chunk.id in result_ids
    assert old_model_chunk.id not in result_ids


async def test_search_respects_top_k(pg_engine):
    test_sessionmaker = async_sessionmaker(bind=pg_engine, expire_on_commit=False, class_=AsyncSession)
    async with test_sessionmaker() as session:
        _, subject, document, chunk_repo, embedding_repo = await _seed(session)
        for i in range(5):
            await _add_child_chunk(
                chunk_repo, embedding_repo, subject_id=subject.id, document_id=document.id,
                content=f"chunk {i}", vector=_vec(float(i + 1), 0.0, 0.0), model_name="test-model",
            )
        await session.commit()

        results = await embedding_repo.search(
            subject_id=subject.id, query_vector=_vec(1.0, 0.0, 0.0), top_k=2, model_name="test-model"
        )

    assert len(results) == 2
