"""progress, weak_concepts

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "progress",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("concept_id", sa.String(length=36), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mastery_score", sa.Float(), nullable=False),
        sa.Column("trend", sa.String(length=10), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "concept_id", name="uq_progress_user_concept"),
    )
    op.create_index("ix_progress_user_id", "progress", ["user_id"])
    op.create_index("ix_progress_concept_id", "progress", ["concept_id"])

    op.create_table(
        "weak_concepts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("concept_id", sa.String(length=36), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="active"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_weak_concepts_user_id", "weak_concepts", ["user_id"])
    op.create_index("ix_weak_concepts_concept_id", "weak_concepts", ["concept_id"])


def downgrade() -> None:
    op.drop_table("weak_concepts")
    op.drop_table("progress")
