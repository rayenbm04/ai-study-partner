from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities.message import Citation, Message


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class CitationResponse(BaseModel):
    document_id: str
    document_filename: str
    chunk_id: str
    page: int | None
    section_title: str | None

    @classmethod
    def from_entity(cls, citation: Citation) -> "CitationResponse":
        return cls(
            document_id=citation.document_id,
            document_filename=citation.document_filename,
            chunk_id=citation.chunk_id,
            page=citation.page,
            section_title=citation.section_title,
        )


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    citations: list[CitationResponse]
    created_at: datetime

    @classmethod
    def from_entity(cls, message: Message) -> "MessageResponse":
        return cls(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            citations=[CitationResponse.from_entity(c) for c in message.citations],
            created_at=message.created_at,
        )


class ChatResponse(BaseModel):
    conversation_id: str
    user_message: MessageResponse
    assistant_message: MessageResponse
