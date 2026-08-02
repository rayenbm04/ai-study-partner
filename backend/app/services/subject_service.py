from app.core.exceptions import DuplicateSubjectError, SubjectNotFoundError
from app.domain.entities.subject import Subject
from app.domain.repositories.subject_repository import SubjectRepository


class SubjectService:
    """Subjects are the top-level, student-owned container everything else
    (documents, concepts, flashcards, quizzes, progress) scopes to. Ownership
    is enforced here so a route can never accidentally leak another user's
    subject by id."""

    def __init__(self, subject_repo: SubjectRepository):
        self._subjects = subject_repo

    async def list_for_user(self, user_id: str) -> list[Subject]:
        return await self._subjects.list_by_user(user_id)

    async def create(
        self,
        user_id: str,
        *,
        name: str,
        description: str | None = None,
        color: str | None = None,
        icon: str | None = None,
    ) -> Subject:
        if await self._subjects.get_by_user_and_name(user_id, name):
            raise DuplicateSubjectError(name)
        return await self._subjects.create(user_id=user_id, name=name, description=description, color=color, icon=icon)

    async def get_owned(self, user_id: str, subject_id: str) -> Subject:
        subject = await self._subjects.get_by_id(subject_id)
        if subject is None or subject.user_id != user_id:
            raise SubjectNotFoundError(subject_id)
        return subject

    async def update(self, user_id: str, subject_id: str, **fields) -> Subject:
        await self.get_owned(user_id, subject_id)  # ownership check before mutating
        return await self._subjects.update(subject_id, **fields)

    async def archive(self, user_id: str, subject_id: str) -> None:
        await self.get_owned(user_id, subject_id)
        await self._subjects.archive(subject_id)
