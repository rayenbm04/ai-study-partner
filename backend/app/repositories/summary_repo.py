from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.summary import Summary
from app.domain.repositories.summary_repository import SummaryRepository
from app.infrastructure.db.models.summary import SummaryModel


def _to_entity(model: SummaryModel) -> Summary:
    return Summary(
        id=model.id,
        document_id=model.document_id,
        subject_id=model.subject_id,
        summary_type=model.summary_type,
        content=model.content,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemySummaryRepository(SummaryRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, *, document_id: str, subject_id: str, summary_type: str, content: str) -> Summary:
        stmt = select(SummaryModel).where(
            SummaryModel.document_id == document_id, SummaryModel.summary_type == summary_type
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is not None:
            model.content = content
            model.updated_at = datetime.now(timezone.utc)
        else:
            model = SummaryModel(
                document_id=document_id, subject_id=subject_id, summary_type=summary_type, content=content
            )
            self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_document_and_type(self, document_id: str, summary_type: str) -> Summary | None:
        stmt = select(SummaryModel).where(
            SummaryModel.document_id == document_id, SummaryModel.summary_type == summary_type
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_document(self, document_id: str) -> list[Summary]:
        stmt = select(SummaryModel).where(SummaryModel.document_id == document_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]
