from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.quiz import QuizAttempt
from app.domain.repositories.quiz_attempt_repository import QuizAttemptRepository
from app.infrastructure.db.models.quiz_attempt import QuizAttemptModel


def _to_entity(model: QuizAttemptModel) -> QuizAttempt:
    return QuizAttempt(
        id=model.id,
        quiz_id=model.quiz_id,
        user_id=model.user_id,
        started_at=model.started_at,
        completed_at=model.completed_at,
        score=model.score,
    )


class SqlAlchemyQuizAttemptRepository(QuizAttemptRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, *, quiz_id: str, user_id: str) -> QuizAttempt:
        model = QuizAttemptModel(quiz_id=quiz_id, user_id=user_id)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, attempt_id: str) -> QuizAttempt | None:
        model = await self._session.get(QuizAttemptModel, attempt_id)
        return _to_entity(model) if model else None

    async def list_by_quiz(self, quiz_id: str) -> list[QuizAttempt]:
        stmt = select(QuizAttemptModel).where(QuizAttemptModel.quiz_id == quiz_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]

    async def complete(self, attempt_id: str, *, completed_at: datetime, score: float) -> QuizAttempt:
        model = await self._session.get(QuizAttemptModel, attempt_id)
        model.completed_at = completed_at
        model.score = score
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)
