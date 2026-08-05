from datetime import datetime

from pydantic import BaseModel

from app.domain.entities.curriculum import AcademicLevel, Chapter, Country, CurriculumSubject, EducationSystem, Lesson, Section


class CountryResponse(BaseModel):
    id: str
    name: str
    code: str | None
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: Country) -> "CountryResponse":
        return cls(id=entity.id, name=entity.name, code=entity.code, created_at=entity.created_at)


class EducationSystemResponse(BaseModel):
    id: str
    country_id: str
    name: str
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: EducationSystem) -> "EducationSystemResponse":
        return cls(id=entity.id, country_id=entity.country_id, name=entity.name, created_at=entity.created_at)


class AcademicLevelResponse(BaseModel):
    id: str
    education_system_id: str
    name: str
    order_index: int
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: AcademicLevel) -> "AcademicLevelResponse":
        return cls(
            id=entity.id,
            education_system_id=entity.education_system_id,
            name=entity.name,
            order_index=entity.order_index,
            created_at=entity.created_at,
        )


class SectionResponse(BaseModel):
    id: str
    academic_level_id: str
    name: str
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: Section) -> "SectionResponse":
        return cls(id=entity.id, academic_level_id=entity.academic_level_id, name=entity.name, created_at=entity.created_at)


class CurriculumSubjectResponse(BaseModel):
    id: str
    academic_level_id: str
    section_id: str | None
    name: str
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: CurriculumSubject) -> "CurriculumSubjectResponse":
        return cls(
            id=entity.id,
            academic_level_id=entity.academic_level_id,
            section_id=entity.section_id,
            name=entity.name,
            created_at=entity.created_at,
        )


class ChapterResponse(BaseModel):
    id: str
    curriculum_subject_id: str
    name: str
    order_index: int
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: Chapter) -> "ChapterResponse":
        return cls(
            id=entity.id,
            curriculum_subject_id=entity.curriculum_subject_id,
            name=entity.name,
            order_index=entity.order_index,
            created_at=entity.created_at,
        )


class LessonResponse(BaseModel):
    id: str
    chapter_id: str
    name: str
    order_index: int
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: Lesson) -> "LessonResponse":
        return cls(
            id=entity.id,
            chapter_id=entity.chapter_id,
            name=entity.name,
            order_index=entity.order_index,
            created_at=entity.created_at,
        )
