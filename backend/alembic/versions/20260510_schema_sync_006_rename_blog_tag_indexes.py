"""rename blog_tags indexes from old tags prefix

Revision ID: schema_sync_006
Revises: schema_sync_005
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op

revision: str = "schema_sync_006"
down_revision: Union[str, None] = "schema_sync_005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename old indexes to match blog_tags tablename convention
    op.execute("ALTER INDEX ix_tags_id RENAME TO ix_blog_tags_id")
    op.execute("ALTER INDEX ix_tags_slug RENAME TO ix_blog_tags_slug")
    op.execute("ALTER INDEX tags_slug_key RENAME TO blog_tags_slug_key")


def downgrade() -> None:
    op.execute("ALTER INDEX blog_tags_slug_key RENAME TO tags_slug_key")
    op.execute("ALTER INDEX ix_blog_tags_slug RENAME TO ix_tags_slug")
    op.execute("ALTER INDEX ix_blog_tags_id RENAME TO ix_tags_id")
