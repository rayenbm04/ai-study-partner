"""curriculum catalog: countries, education systems, academic levels, sections,
curriculum subjects, chapters, lessons — plus subjects.curriculum_subject_id
and documents classification columns

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "curriculum_countries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("code", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "curriculum_education_systems",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "country_id", sa.String(length=36), sa.ForeignKey("curriculum_countries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("country_id", "name", name="uq_education_system_country_name"),
    )
    op.create_index("ix_curriculum_education_systems_country_id", "curriculum_education_systems", ["country_id"])

    op.create_table(
        "curriculum_academic_levels",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "education_system_id", sa.String(length=36),
            sa.ForeignKey("curriculum_education_systems.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("education_system_id", "name", name="uq_academic_level_system_name"),
    )
    op.create_index(
        "ix_curriculum_academic_levels_education_system_id", "curriculum_academic_levels", ["education_system_id"]
    )

    op.create_table(
        "curriculum_sections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "academic_level_id", sa.String(length=36),
            sa.ForeignKey("curriculum_academic_levels.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("academic_level_id", "name", name="uq_section_level_name"),
    )
    op.create_index("ix_curriculum_sections_academic_level_id", "curriculum_sections", ["academic_level_id"])

    op.create_table(
        "curriculum_subjects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "academic_level_id", sa.String(length=36),
            sa.ForeignKey("curriculum_academic_levels.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "section_id", sa.String(length=36), sa.ForeignKey("curriculum_sections.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_curriculum_subjects_academic_level_id", "curriculum_subjects", ["academic_level_id"])
    op.create_index("ix_curriculum_subjects_section_id", "curriculum_subjects", ["section_id"])

    op.create_table(
        "curriculum_chapters",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "curriculum_subject_id", sa.String(length=36), sa.ForeignKey("curriculum_subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("curriculum_subject_id", "name", name="uq_chapter_subject_name"),
    )
    op.create_index("ix_curriculum_chapters_curriculum_subject_id", "curriculum_chapters", ["curriculum_subject_id"])

    op.create_table(
        "curriculum_lessons",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "chapter_id", sa.String(length=36), sa.ForeignKey("curriculum_chapters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chapter_id", "name", name="uq_lesson_chapter_name"),
    )
    op.create_index("ix_curriculum_lessons_chapter_id", "curriculum_lessons", ["chapter_id"])

    op.add_column(
        "subjects",
        sa.Column(
            "curriculum_subject_id", sa.String(length=36),
            sa.ForeignKey("curriculum_subjects.id", ondelete="SET NULL"), nullable=True,
        ),
    )
    op.create_index("ix_subjects_curriculum_subject_id", "subjects", ["curriculum_subject_id"])

    op.add_column("documents", sa.Column("document_type", sa.String(length=20), nullable=True))
    op.add_column(
        "documents",
        sa.Column(
            "chapter_id", sa.String(length=36), sa.ForeignKey("curriculum_chapters.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "lesson_id", sa.String(length=36), sa.ForeignKey("curriculum_lessons.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("documents", sa.Column("classification_confidence", sa.Float(), nullable=True))
    op.add_column("documents", sa.Column("classified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_documents_chapter_id", "documents", ["chapter_id"])
    op.create_index("ix_documents_lesson_id", "documents", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_lesson_id", table_name="documents")
    op.drop_index("ix_documents_chapter_id", table_name="documents")
    op.drop_column("documents", "classified_at")
    op.drop_column("documents", "classification_confidence")
    op.drop_column("documents", "lesson_id")
    op.drop_column("documents", "chapter_id")
    op.drop_column("documents", "document_type")

    op.drop_index("ix_subjects_curriculum_subject_id", table_name="subjects")
    op.drop_column("subjects", "curriculum_subject_id")

    op.drop_table("curriculum_lessons")
    op.drop_table("curriculum_chapters")
    op.drop_table("curriculum_subjects")
    op.drop_table("curriculum_sections")
    op.drop_table("curriculum_academic_levels")
    op.drop_table("curriculum_education_systems")
    op.drop_table("curriculum_countries")
