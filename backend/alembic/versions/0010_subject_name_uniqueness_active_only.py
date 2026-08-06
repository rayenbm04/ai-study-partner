"""subjects: scope the (user_id, name) uniqueness to active (non-archived)
subjects only, via a partial unique index, so archiving a subject frees up
its name for reuse

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_subject_user_name", "subjects", type_="unique")
    op.create_index(
        "uq_subject_user_name_active",
        "subjects",
        ["user_id", "name"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_subject_user_name_active", table_name="subjects")
    op.create_unique_constraint("uq_subject_user_name", "subjects", ["user_id", "name"])
