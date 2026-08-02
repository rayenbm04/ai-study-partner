from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Citation:
    document_id: str
    document_filename: str
    chunk_id: str
    page: int | None
    section_title: str | None


@dataclass(frozen=True, slots=True)
class Message:
    id: str
    conversation_id: str
    role: str  # "user" | "assistant"
    content: str
    citations: list[Citation]
    created_at: datetime
