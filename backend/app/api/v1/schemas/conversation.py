from datetime import datetime

from pydantic import BaseModel

from app.domain.entities.conversation import Conversation


class ConversationResponse(BaseModel):
    id: str
    subject_id: str
    title: str | None
    created_at: datetime

    @classmethod
    def from_entity(cls, conversation: Conversation) -> "ConversationResponse":
        return cls(
            id=conversation.id,
            subject_id=conversation.subject_id,
            title=conversation.title,
            created_at=conversation.created_at,
        )
