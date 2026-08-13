from abc import ABC, abstractmethod
from datetime import datetime


class UsageEventRepository(ABC):
    @abstractmethod
    async def record(
        self,
        *,
        user_id: str,
        event_type: str,
        provider: str | None = None,
        model: str | None = None,
        tokens: int | None = None,
        document_id: str | None = None,
    ) -> None: ...

    @abstractmethod
    async def count_since(self, *, user_id: str, event_types: list[str] | None, since: datetime) -> int:
        """Count of this user's events at or after `since`, optionally
        restricted to `event_types`. Used for daily usage-limit checks."""
        ...
