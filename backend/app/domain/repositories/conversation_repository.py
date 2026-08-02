from abc import ABC, abstractmethod

from app.domain.entities.conversation import Conversation


class ConversationRepository(ABC):
    @abstractmethod
    async def create(self, *, user_id: str, subject_id: str, title: str | None) -> Conversation: ...

    @abstractmethod
    async def get_by_id(self, conversation_id: str) -> Conversation | None: ...

    @abstractmethod
    async def list_by_subject(self, user_id: str, subject_id: str) -> list[Conversation]: ...
