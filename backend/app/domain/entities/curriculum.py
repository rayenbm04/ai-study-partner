"""The curriculum catalog: a global, shared reference tree (not owned by any
one user) that documents get classified against. Country -> EducationSystem
-> AcademicLevel -> Section (optional) -> CurriculumSubject -> Chapter ->
Lesson. Kept as one file since these seven node types are always populated
and queried together as a single tree, unlike the app's other entities."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Country:
    id: str
    name: str
    code: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EducationSystem:
    id: str
    country_id: str
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AcademicLevel:
    id: str
    education_system_id: str
    name: str
    order_index: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Section:
    id: str
    academic_level_id: str
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CurriculumSubject:
    id: str
    academic_level_id: str
    section_id: str | None
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Chapter:
    id: str
    curriculum_subject_id: str
    name: str
    order_index: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Lesson:
    id: str
    chapter_id: str
    name: str
    order_index: int
    created_at: datetime
