"""Ingestion efficiency: documents.content_hash (upload-time dedup),
documents.processing_step/processing_progress (granular ingestion status for
the upload-progress UI), and usage_events (per-user AI/document usage log —
see UsageService).

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.add_column("documents", sa.Column("processing_step", sa.String(length=30), nullable=True))
    op.add_column("documents", sa.Column("processing_progress", sa.Integer(), nullable=True))

    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("tokens", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usage_events_user_id", "usage_events", ["user_id"])
    op.create_index("ix_usage_events_event_type", "usage_events", ["event_type"])
    op.create_index("ix_usage_events_created_at", "usage_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("usage_events")
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.drop_column("documents", "processing_progress")
    op.drop_column("documents", "processing_step")
    op.drop_column("documents", "content_hash")
