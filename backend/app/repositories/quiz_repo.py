from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.quiz import Quiz, QuizQuestion, QuizQuestionDraft
from app.domain.repositories.quiz_repository import QuizRepository
from app.infrastructure.db.models.quiz import QuizModel
from app.infrastructure.db.models.quiz_question import QuizQuestionModel


def _quiz_to_entity(model: QuizModel) -> Quiz:
    return Quiz(
        id=model.id,
        subject_id=model.subject_id,
        user_id=model.user_id,
        title=model.title,
        kind=model.kind,
        difficulty=model.difficulty,
        topics=list(model.topics or []),
        duration_minutes=model.duration_minutes,
        style=model.style,
        created_at=model.created_at,
    )


def _question_to_entity(model: QuizQuestionModel) -> QuizQuestion:
    return QuizQuestion(
        id=model.id,
        quiz_id=model.quiz_id,
        concept_id=model.concept_id,
        type=model.type,
        question=model.question,
        options=list(model.options) if model.options is not None else None,
        correct_answer=model.correct_answer,
        explanation=model.explanation,
        points=model.points,
        difficulty=model.difficulty,
    )


class SqlAlchemyQuizRepository(QuizRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self, *, subject_id, user_id, title, kind, difficulty, topics, duration_minutes, style
    ) -> Quiz:
        model = QuizModel(
            subject_id=subject_id,
            user_id=user_id,
            title=title,
            kind=kind,
            difficulty=difficulty,
            topics=list(topics),
            duration_minutes=duration_minutes,
            style=style,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _quiz_to_entity(model)

    async def bulk_create_questions(self, *, quiz_id: str, drafts: list[QuizQuestionDraft]) -> list[QuizQuestion]:
        models = [
            QuizQuestionModel(
                quiz_id=quiz_id,
                concept_id=draft.concept_id,
                type=draft.type,
                question=draft.question,
                options=list(draft.options) if draft.options is not None else None,
                correct_answer=draft.correct_answer,
                explanation=draft.explanation,
                points=draft.points,
                difficulty=draft.difficulty,
            )
            for draft in drafts
        ]
        self._session.add_all(models)
        await self._session.flush()
        for model in models:
            await self._session.refresh(model)
        return [_question_to_entity(m) for m in models]

    async def get_by_id(self, quiz_id: str) -> Quiz | None:
        model = await self._session.get(QuizModel, quiz_id)
        return _quiz_to_entity(model) if model else None

    async def list_by_subject(self, subject_id: str) -> list[Quiz]:
        stmt = select(QuizModel).where(QuizModel.subject_id == subject_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_quiz_to_entity(m) for m in models]

    async def list_questions(self, quiz_id: str) -> list[QuizQuestion]:
        stmt = select(QuizQuestionModel).where(QuizQuestionModel.quiz_id == quiz_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_question_to_entity(m) for m in models]

    async def get_question_by_id(self, question_id: str) -> QuizQuestion | None:
        model = await self._session.get(QuizQuestionModel, question_id)
        return _question_to_entity(model) if model else None
