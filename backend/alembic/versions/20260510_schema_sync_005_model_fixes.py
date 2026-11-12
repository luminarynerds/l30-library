"""fix enum type names in models, drop orphan tags table

Revision ID: schema_sync_005
Revises: schema_sync_004
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "schema_sync_005"
down_revision: Union[str, None] = "schema_sync_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop orphan "tags" table (separate from blog_tags, 3 rows, no FK refs, no model)
    op.drop_table("tags")


def downgrade() -> None:
    op.create_table("tags",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("name", sa.VARCHAR(length=100), nullable=False),
        sa.Column("slug", sa.VARCHAR(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
