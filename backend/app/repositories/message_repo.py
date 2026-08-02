from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.message import Citation, Message
from app.domain.repositories.message_repository import MessageRepository
from app.infrastructure.db.models.message import MessageModel


def _to_entity(model: MessageModel) -> Message:
    return Message(
        id=model.id,
        conversation_id=model.conversation_id,
        role=model.role,
        content=model.content,
        citations=[Citation(**c) for c in (model.citations or [])],
        created_at=model.created_at,
    )


class SqlAlchemyMessageRepository(MessageRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, *, conversation_id: str, role: str, content: str, citations: list[Citation]) -> Message:
        model = MessageModel(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=[asdict(c) for c in citations],
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_by_conversation(self, conversation_id: str) -> list[Message]:
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at.asc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]
