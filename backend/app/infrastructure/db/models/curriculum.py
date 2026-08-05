import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class CountryModel(Base):
    __tablename__ = "curriculum_countries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class EducationSystemModel(Base):
    __tablename__ = "curriculum_education_systems"
    __table_args__ = (UniqueConstraint("country_id", "name", name="uq_education_system_country_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    country_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("curriculum_countries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class AcademicLevelModel(Base):
    __tablename__ = "curriculum_academic_levels"
    __table_args__ = (UniqueConstraint("education_system_id", "name", name="uq_academic_level_system_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    education_system_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("curriculum_education_systems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class SectionModel(Base):
    __tablename__ = "curriculum_sections"
    __table_args__ = (UniqueConstraint("academic_level_id", "name", name="uq_section_level_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    academic_level_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("curriculum_academic_levels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class CurriculumSubjectModel(Base):
    __tablename__ = "curriculum_subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    academic_level_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("curriculum_academic_levels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("curriculum_sections.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ChapterModel(Base):
    __tablename__ = "curriculum_chapters"
    __table_args__ = (UniqueConstraint("curriculum_subject_id", "name", name="uq_chapter_subject_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    curriculum_subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("curriculum_subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class LessonModel(Base):
    __tablename__ = "curriculum_lessons"
    __table_args__ = (UniqueConstraint("chapter_id", "name", name="uq_lesson_chapter_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chapter_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("curriculum_chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
