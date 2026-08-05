from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Subject:
    id: str
    user_id: str
    name: str
    description: str | None
    color: str | None
    icon: str | None
    created_at: datetime
    archived_at: datetime | None
    curriculum_subject_id: str | None = None

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None
