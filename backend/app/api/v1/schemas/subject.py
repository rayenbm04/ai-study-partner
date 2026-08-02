from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities.subject import Subject


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    color: str | None = Field(default=None, max_length=20)
    icon: str | None = Field(default=None, max_length=50)


class SubjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    color: str | None = Field(default=None, max_length=20)
    icon: str | None = Field(default=None, max_length=50)


class SubjectResponse(BaseModel):
    id: str
    name: str
    description: str | None
    color: str | None
    icon: str | None
    created_at: datetime
    archived_at: datetime | None

    @classmethod
    def from_entity(cls, subject: Subject) -> "SubjectResponse":
        return cls(
            id=subject.id,
            name=subject.name,
            description=subject.description,
            color=subject.color,
            icon=subject.icon,
            created_at=subject.created_at,
            archived_at=subject.archived_at,
        )
