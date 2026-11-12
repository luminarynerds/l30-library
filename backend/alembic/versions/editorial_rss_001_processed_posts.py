# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add processed_rss_posts (dedup marker for editorial RSS extraction)."""
import sqlalchemy as sa
from alembic import op

revision = "editorial_rss_001"
down_revision = "editorial_prepub_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_rss_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("outlet", sa.String(length=40), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_processed_rss_posts_url", "processed_rss_posts", ["url"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_processed_rss_posts_url", table_name="processed_rss_posts")
    op.drop_table("processed_rss_posts")
