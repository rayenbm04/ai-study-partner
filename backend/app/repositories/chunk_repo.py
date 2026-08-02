from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.chunk import Chunk, ChunkDraft
from app.domain.repositories.chunk_repository import ChunkRepository
from app.infrastructure.db.models.chunk import ChunkModel


def _to_entity(model: ChunkModel) -> Chunk:
    return Chunk(
        id=model.id,
        document_id=model.document_id,
        subject_id=model.subject_id,
        content=model.content,
        chunk_type=model.chunk_type,
        parent_chunk_id=model.parent_chunk_id,
        page=model.page,
        section_title=model.section_title,
        chapter=model.chapter,
        token_count=model.token_count,
    )


class SqlAlchemyChunkRepository(ChunkRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def bulk_create(self, *, document_id: str, subject_id: str, drafts: list[ChunkDraft]) -> list[Chunk]:
        # Parents are flushed first so children can reference their real ids.
        # ChunkDraft.parent_index is the child's parent's position within the
        # full `drafts` list (see ChunkDraft docstring) — that's the contract
        # the chunker and this repository agree on.
        def make_model(draft: ChunkDraft, parent_chunk_id: str | None) -> ChunkModel:
            return ChunkModel(
                document_id=document_id,
                subject_id=subject_id,
                content=draft.content,
                chunk_type=draft.chunk_type,
                parent_chunk_id=parent_chunk_id,
                page=draft.page,
                section_title=draft.section_title,
                chapter=draft.chapter,
                token_count=draft.token_count,
            )

        models_by_index: dict[int, ChunkModel] = {}
        for index, draft in enumerate(drafts):
            if draft.chunk_type == "parent":
                model = make_model(draft, parent_chunk_id=None)
                self._session.add(model)
                models_by_index[index] = model

        await self._session.flush()  # parents now have real ids

        for index, draft in enumerate(drafts):
            if draft.chunk_type != "parent":
                parent_model = models_by_index.get(draft.parent_index) if draft.parent_index is not None else None
                model = make_model(draft, parent_chunk_id=parent_model.id if parent_model else None)
                self._session.add(model)
                models_by_index[index] = model

        await self._session.flush()
        ordered_models = [models_by_index[i] for i in range(len(drafts))]
        for model in ordered_models:
            await self._session.refresh(model)
        return [_to_entity(m) for m in ordered_models]

    async def list_by_document(self, document_id: str) -> list[Chunk]:
        stmt = select(ChunkModel).where(ChunkModel.document_id == document_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]
