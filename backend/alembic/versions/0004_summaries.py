"""summaries

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "summaries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.String(length=36), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary_type", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "summary_type", name="uq_summary_document_type"),
    )
    op.create_index("ix_summaries_document_id", "summaries", ["document_id"])
    op.create_index("ix_summaries_subject_id", "summaries", ["subject_id"])


def downgrade() -> None:
    op.drop_table("summaries")
