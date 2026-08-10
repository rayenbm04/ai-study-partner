"""users: student profile fields (date of birth, pseudo, school, classe) plus
email-verification state for a future confirmation flow — not enforced yet,
just the columns so login/registration don't need another migration when
email sending is wired up.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("pseudo", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("school_name", sa.String(length=200), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "academic_level_id",
            sa.String(length=36),
            sa.ForeignKey("curriculum_academic_levels.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "section_id",
            sa.String(length=36),
            sa.ForeignKey("curriculum_sections.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "users", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))

    # Standard SQL treats NULL as never equal to another NULL, so a plain
    # unique index already lets every pre-existing account (no pseudo yet)
    # through unconstrained while still enforcing uniqueness among accounts
    # that do have one — no partial-index trick needed.
    op.create_index("ix_users_pseudo_unique", "users", ["pseudo"], unique=True)
    op.create_index("ix_users_academic_level_id", "users", ["academic_level_id"])
    op.create_index("ix_users_section_id", "users", ["section_id"])


def downgrade() -> None:
    op.drop_index("ix_users_section_id", table_name="users")
    op.drop_index("ix_users_academic_level_id", table_name="users")
    op.drop_index("ix_users_pseudo_unique", table_name="users")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "is_verified")
    op.drop_column("users", "section_id")
    op.drop_column("users", "academic_level_id")
    op.drop_column("users", "school_name")
    op.drop_column("users", "pseudo")
    op.drop_column("users", "date_of_birth")
