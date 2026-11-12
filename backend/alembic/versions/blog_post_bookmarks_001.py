# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""blog_post_bookmarks: patron-saved blog posts

Revision ID: blog_post_bookmarks_001
Revises: event_registration_cancelled_001
Create Date: 2026-05-23

Creates the ``blog_post_bookmarks`` table for the patron blog bookmark
feature (GET/POST/DELETE /api/v1/blog/bookmarks). Per-user saved posts,
unique on (user_id, post_id), with ON DELETE CASCADE on both FKs.

L30 init_db.py auto-creates tables from SQLAlchemy models at backend
startup, so CREATE TABLE / CREATE INDEX are wrapped in IF NOT EXISTS
to stay idempotent across rebuilds (see
backend/scripts/check_alembic_idempotent.py and
[[feedback_l30_init_db_vs_alembic_new_table]]).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "blog_post_bookmarks_001"
down_revision: Union[str, None] = "event_registration_cancelled_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS blog_post_bookmarks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            post_id INTEGER NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_blog_post_bookmark_user_post UNIQUE (user_id, post_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_blog_post_bookmarks_user_id "
        "ON blog_post_bookmarks (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_blog_post_bookmarks_post_id "
        "ON blog_post_bookmarks (post_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS blog_post_bookmarks")
