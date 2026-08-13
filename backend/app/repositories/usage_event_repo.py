from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.usage_event_repository import UsageEventRepository
from app.infrastructure.db.models.usage_event import UsageEventModel


class SqlAlchemyUsageEventRepository(UsageEventRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def record(
        self,
        *,
        user_id: str,
        event_type: str,
        provider: str | None = None,
        model: str | None = None,
        tokens: int | None = None,
        document_id: str | None = None,
    ) -> None:
        self._session.add(
            UsageEventModel(
                user_id=user_id, event_type=event_type, provider=provider, model=model, tokens=tokens,
                document_id=document_id,
            )
        )
        await self._session.flush()

    async def count_since(self, *, user_id: str, event_types: list[str] | None, since: datetime) -> int:
        conditions = [UsageEventModel.user_id == user_id, UsageEventModel.created_at >= since]
        if event_types:
            conditions.append(UsageEventModel.event_type.in_(event_types))
        stmt = select(func.count()).select_from(UsageEventModel).where(*conditions)
        return (await self._session.execute(stmt)).scalar_one()
