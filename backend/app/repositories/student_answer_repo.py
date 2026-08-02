from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.quiz import StudentAnswer
from app.domain.repositories.student_answer_repository import StudentAnswerRepository
from app.infrastructure.db.models.student_answer import StudentAnswerModel


def _to_entity(model: StudentAnswerModel) -> StudentAnswer:
    return StudentAnswer(
        id=model.id,
        quiz_attempt_id=model.quiz_attempt_id,
        quiz_question_id=model.quiz_question_id,
        answer=model.answer,
        is_correct=model.is_correct,
        time_spent_seconds=model.time_spent_seconds,
        submitted_at=model.submitted_at,
    )


class SqlAlchemyStudentAnswerRepository(StudentAnswerRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(
        self, *, quiz_attempt_id, quiz_question_id, answer, is_correct, time_spent_seconds, submitted_at
    ) -> StudentAnswer:
        stmt = select(StudentAnswerModel).where(
            StudentAnswerModel.quiz_attempt_id == quiz_attempt_id,
            StudentAnswerModel.quiz_question_id == quiz_question_id,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is not None:
            model.answer = answer
            model.is_correct = is_correct
            model.time_spent_seconds = time_spent_seconds
            model.submitted_at = submitted_at
        else:
            model = StudentAnswerModel(
                quiz_attempt_id=quiz_attempt_id,
                quiz_question_id=quiz_question_id,
                answer=answer,
                is_correct=is_correct,
                time_spent_seconds=time_spent_seconds,
                submitted_at=submitted_at,
            )
            self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_by_attempt(self, quiz_attempt_id: str) -> list[StudentAnswer]:
        stmt = select(StudentAnswerModel).where(StudentAnswerModel.quiz_attempt_id == quiz_attempt_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]
