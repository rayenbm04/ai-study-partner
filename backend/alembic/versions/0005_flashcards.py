"""flashcards, flashcard_reviews

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "flashcards",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("subject_id", sa.String(length=36), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("concept_id", sa.String(length=36), sa.ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.String(length=10), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_flashcards_subject_id", "flashcards", ["subject_id"])

    op.create_table(
        "flashcard_reviews",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "flashcard_id", sa.String(length=36), sa.ForeignKey("flashcards.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ease_factor", sa.Float(), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("repetitions", sa.Integer(), nullable=False),
        sa.Column("last_grade", sa.Integer(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_date", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("flashcard_id", "user_id", name="uq_flashcard_review_card_user"),
    )
    op.create_index("ix_flashcard_reviews_flashcard_id", "flashcard_reviews", ["flashcard_id"])
    op.create_index("ix_flashcard_reviews_user_id", "flashcard_reviews", ["user_id"])


def downgrade() -> None:
    op.drop_table("flashcard_reviews")
    op.drop_table("flashcards")
