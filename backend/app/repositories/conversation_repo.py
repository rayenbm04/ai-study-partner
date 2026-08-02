from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.conversation import Conversation
from app.domain.repositories.conversation_repository import ConversationRepository
from app.infrastructure.db.models.conversation import ConversationModel


def _to_entity(model: ConversationModel) -> Conversation:
    return Conversation(
        id=model.id, user_id=model.user_id, subject_id=model.subject_id, title=model.title, created_at=model.created_at
    )


class SqlAlchemyConversationRepository(ConversationRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, *, user_id: str, subject_id: str, title: str | None) -> Conversation:
        model = ConversationModel(user_id=user_id, subject_id=subject_id, title=title)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        model = await self._session.get(ConversationModel, conversation_id)
        return _to_entity(model) if model else None

    async def list_by_subject(self, user_id: str, subject_id: str) -> list[Conversation]:
        stmt = (
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id, ConversationModel.subject_id == subject_id)
            .order_by(ConversationModel.created_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]
