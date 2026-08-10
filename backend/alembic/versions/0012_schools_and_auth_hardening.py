"""schools + school_classes (institution catalog, replaces free-text
school_name), verification_tokens (email verification / password reset,
delivery stubbed for now), security_events (append-only security log), plus
users: school_id (FK, replaces school_name), status, last_login_at,
failed_login_attempts, locked_until (login-attempt limiting).

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_schools_name", "schools", ["name"])

    op.create_table(
        "school_classes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("school_id", sa.String(length=36), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_school_classes_school_id", "school_classes", ["school_id"])

    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_verification_tokens_user_id", "verification_tokens", ["user_id"])
    op.create_index("ix_verification_tokens_token_hash_unique", "verification_tokens", ["token_hash"], unique=True)

    op.create_table(
        "security_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_security_events_user_id", "security_events", ["user_id"])
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"])

    # users: school_name (free text) -> school_id (FK to the new schools
    # catalog). No data migration — no accounts exist yet with real user data
    # riding on this column beyond what this same dev cycle created.
    op.drop_column("users", "school_name")
    op.add_column(
        "users",
        sa.Column("school_id", sa.String(length=36), sa.ForeignKey("schools.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_users_school_id", "users", ["school_id"])

    op.add_column("users", sa.Column("status", sa.String(length=20), nullable=False, server_default="active"))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "status")
    op.drop_index("ix_users_school_id", table_name="users")
    op.drop_column("users", "school_id")
    op.add_column("users", sa.Column("school_name", sa.String(length=200), nullable=True))

    op.drop_index("ix_security_events_created_at", table_name="security_events")
    op.drop_index("ix_security_events_event_type", table_name="security_events")
    op.drop_index("ix_security_events_user_id", table_name="security_events")
    op.drop_table("security_events")

    op.drop_index("ix_verification_tokens_token_hash_unique", table_name="verification_tokens")
    op.drop_index("ix_verification_tokens_user_id", table_name="verification_tokens")
    op.drop_table("verification_tokens")

    op.drop_index("ix_school_classes_school_id", table_name="school_classes")
    op.drop_table("school_classes")

    op.drop_index("ix_schools_name", table_name="schools")
    op.drop_table("schools")
