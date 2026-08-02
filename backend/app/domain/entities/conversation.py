from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Conversation:
    id: str
    user_id: str
    subject_id: str
    title: str | None
    created_at: datetime
