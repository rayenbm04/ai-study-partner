from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.security_event_repository import SecurityEventRepository
from app.infrastructure.db.models.security_event import SecurityEventModel


class SqlAlchemySecurityEventRepository(SecurityEventRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def record(self, *, user_id: str | None, event_type: str, detail: str | None = None) -> None:
        model = SecurityEventModel(user_id=user_id, event_type=event_type, detail=detail)
        self._session.add(model)
        await self._session.flush()
