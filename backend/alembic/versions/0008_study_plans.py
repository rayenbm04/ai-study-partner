"""study_plans, study_plan_items

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "study_plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("daily_minutes_available", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_study_plans_user_id", "study_plans", ["user_id"])

    op.create_table(
        "study_plan_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "study_plan_id", sa.String(length=36), sa.ForeignKey("study_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject_id", sa.String(length=36), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("concept_id", sa.String(length=36), sa.ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("activity_type", sa.String(length=20), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="pending"),
    )
    op.create_index("ix_study_plan_items_study_plan_id", "study_plan_items", ["study_plan_id"])
    op.create_index("ix_study_plan_items_subject_id", "study_plan_items", ["subject_id"])


def downgrade() -> None:
    op.drop_table("study_plan_items")
    op.drop_table("study_plans")
