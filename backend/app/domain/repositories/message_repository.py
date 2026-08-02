from abc import ABC, abstractmethod

from app.domain.entities.message import Citation, Message


class MessageRepository(ABC):
    @abstractmethod
    async def create(
        self, *, conversation_id: str, role: str, content: str, citations: list[Citation]
    ) -> Message: ...

    @abstractmethod
    async def list_by_conversation(self, conversation_id: str) -> list[Message]:
        """Returned oldest-first — the natural order for replaying as chat history."""
        ...
