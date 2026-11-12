# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add blog_post_views table and view_count column

Revision ID: blog_views_001
Revises: blog_sched_001
Create Date: 2026-05-01 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "blog_views_001"
down_revision: Union[str, None] = "blog_sched_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("blog_posts", sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "blog_post_views",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("blog_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("viewer_hash", sa.String(64), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_blog_post_views_post_id", "blog_post_views", ["post_id"])
    op.create_index("ix_blog_post_views_viewed_at", "blog_post_views", ["viewed_at"])


def downgrade() -> None:
    op.drop_table("blog_post_views")
    op.drop_column("blog_posts", "view_count")
