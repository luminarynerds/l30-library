# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add deleted_at to blog_posts (soft-delete)

Revision ID: blog_soft_delete_001
Revises: event_registration_cancelled_001
Create Date: 2026-05-23

Adds a nullable ``deleted_at`` timestamp + an index. All public blog read
paths filter ``deleted_at IS NULL``. The ``DELETE /blog/posts/{id}`` route
sets the timestamp instead of hard-deleting; ``POST /restore`` clears it.

Idempotent: uses ``IF NOT EXISTS`` so init_db.py auto-create + alembic upgrade
do not collide.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "blog_soft_delete_001"
down_revision: Union[str, Sequence[str], None] = "teacher_application_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_context().as_sql:
        existing_cols: set[str] = set()
        existing_indexes: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing_cols = {c["name"] for c in inspector.get_columns("blog_posts")}
        existing_indexes = {i["name"] for i in inspector.get_indexes("blog_posts")}

    if "deleted_at" not in existing_cols:
        op.add_column(
            "blog_posts",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "ix_blog_posts_deleted_at" not in existing_indexes:
        op.create_index(
            "ix_blog_posts_deleted_at",
            "blog_posts",
            ["deleted_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_blog_posts_deleted_at", table_name="blog_posts")
    op.drop_column("blog_posts", "deleted_at")
