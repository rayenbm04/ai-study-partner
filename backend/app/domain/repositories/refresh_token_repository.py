from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.refresh_token import RefreshToken


class RefreshTokenRepository(ABC):
    @abstractmethod
    async def store(self, *, user_id: str, token_hash: str, expires_at: datetime) -> RefreshToken: ...

    @abstractmethod
    async def get_active_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    @abstractmethod
    async def revoke(self, token_id: str) -> None: ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: str) -> None: ...
