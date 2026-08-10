from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.verification_token import TokenPurpose, VerificationToken


class VerificationTokenRepository(ABC):
    @abstractmethod
    async def create(
        self, *, user_id: str, token_hash: str, purpose: TokenPurpose, expires_at: datetime
    ) -> VerificationToken: ...

    @abstractmethod
    async def get_active_by_hash(self, token_hash: str, *, purpose: TokenPurpose) -> VerificationToken | None: ...

    @abstractmethod
    async def mark_used(self, token_id: str) -> None: ...

    @abstractmethod
    async def invalidate_all_for_user(self, user_id: str, *, purpose: TokenPurpose) -> None:
        """Marks every still-active token of this purpose for this user as
        used — called before issuing a new one (so an old, unused
        verify-email/reset-password link stops working once a fresher one is
        requested) and after a successful reset (so a reset link can't be
        replayed)."""
        ...
