from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities.school import School, SchoolClass


class SchoolResponse(BaseModel):
    id: str
    name: str
    country: str | None
    city: str | None
    status: str
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: School) -> "SchoolResponse":
        return cls(
            id=entity.id, name=entity.name, country=entity.country, city=entity.city, status=entity.status,
            created_at=entity.created_at,
        )


class CreateSchoolRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)


class SchoolClassResponse(BaseModel):
    id: str
    school_id: str
    level: str
    label: str
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: SchoolClass) -> "SchoolClassResponse":
        return cls(
            id=entity.id, school_id=entity.school_id, level=entity.level, label=entity.label,
            created_at=entity.created_at,
        )


class CreateSchoolClassRequest(BaseModel):
    level: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=100)
