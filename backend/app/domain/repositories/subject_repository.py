from abc import ABC, abstractmethod

from app.domain.entities.subject import Subject


class SubjectRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: str, *, include_archived: bool = False) -> list[Subject]: ...

    @abstractmethod
    async def get_by_id(self, subject_id: str) -> Subject | None: ...

    @abstractmethod
    async def get_by_user_and_name(self, user_id: str, name: str) -> Subject | None: ...

    @abstractmethod
    async def create(
        self,
        *,
        user_id: str,
        name: str,
        description: str | None,
        color: str | None,
        icon: str | None,
    ) -> Subject: ...

    @abstractmethod
    async def update(self, subject_id: str, **fields) -> Subject: ...

    @abstractmethod
    async def archive(self, subject_id: str) -> None: ...
