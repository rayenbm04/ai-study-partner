from abc import ABC, abstractmethod


class SecurityEventRepository(ABC):
    @abstractmethod
    async def record(self, *, user_id: str | None, event_type: str, detail: str | None = None) -> None: ...
