from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UsageEvent:
    id: str
    user_id: str
    event_type: str  # document_uploaded | chat_message | summary_generation | flashcard_generation | quiz_generation
    provider: str | None
    model: str | None
    tokens: int | None
    document_id: str | None
    created_at: datetime
