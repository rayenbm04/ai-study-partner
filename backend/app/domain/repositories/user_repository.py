from abc import ABC, abstractmethod
from datetime import date, datetime

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
        school_id: str | None = None,
    ) -> User: ...

    @abstractmethod
    async def set_classe(self, user_id: str, *, academic_level_id: str | None, section_id: str | None) -> User: ...

    @abstractmethod
    async def update_login_state(
        self,
        user_id: str,
        *,
        failed_login_attempts: int,
        locked_until: datetime | None,
        last_login_at: datetime | None,
    ) -> User:
        """Single flexible setter covering both the failed-attempt and
        successful-login paths (AuthService.authenticate computes the new
        values; the repo just persists them)."""
        ...

    @abstractmethod
    async def set_password(self, user_id: str, hashed_password: str) -> User: ...

    @abstractmethod
    async def mark_email_verified(self, user_id: str, verified_at: datetime) -> User: ...
