from abc import ABC, abstractmethod
from datetime import date

from app.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_pseudo(self, pseudo: str) -> User | None: ...

    @abstractmethod
    async def create(
        self,
        *,
        email: str,
        firstname: str,
        lastname: str,
        hashed_password: str,
        role: str = "student",
        pseudo: str | None = None,
        date_of_birth: date | None = None,
        school_name: str | None = None,
    ) -> User: ...

    @abstractmethod
    async def set_classe(self, user_id: str, *, academic_level_id: str | None, section_id: str | None) -> User: ...
