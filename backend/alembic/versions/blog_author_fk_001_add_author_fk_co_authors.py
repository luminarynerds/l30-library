# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""blog: add author_id FK + blog_post_co_authors M2M

Adds a structured author FK to blog_posts (additive: the legacy
author_name / author_role free-text columns stay in place as fallback
for posts created before the FK existed). Backfills author_id by
matching ``lower(users.first_name || ' ' || users.last_name)`` against
``lower(blog_posts.author_name)``; rows with no match keep
author_id = NULL and continue to render from the legacy strings.

Also creates the ``blog_post_co_authors`` M2M (post_id, user_id) so a
post can attribute additional collaborators.

L30 init_db.py runs SQLAlchemy ``create_all`` at startup, so the M2M
table may already exist by the time alembic runs (see
[[feedback_l30_init_db_vs_alembic_new_table]]). The migration uses the
sa.inspect()/get_table_names() guard from
``notification_digest_queue_001`` to stay idempotent on that path.
Column-add on an existing table is NOT auto-created by ``create_all``,
so the ``op.add_column`` path runs unconditionally.

Revision ID: blog_author_fk_001
Revises: event_registration_cancelled_001
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "blog_author_fk_001"
down_revision: Union[str, Sequence[str], None] = "event_registration_cancelled_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_context().as_sql:
        blog_post_columns: set[str] = set()
        existing_tables: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        blog_post_columns = {c["name"] for c in inspector.get_columns("blog_posts")}
        existing_tables = set(inspector.get_table_names())

    # ---- 1. blog_posts.author_id -----------------------------------------
    if "author_id" not in blog_post_columns:
        op.add_column(
            "blog_posts",
            sa.Column("author_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_blog_posts_author_id_users",
            "blog_posts",
            "users",
            ["author_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            "ix_blog_posts_author_id",
            "blog_posts",
            ["author_id"],
        )

    # ---- 2. Backfill author_id from legacy author_name -------------------
    # Match users by full name (case-insensitive). PG and SQLite both
    # support lower() + the || concatenation operator, so a single
    # UPDATE works on both. Skip the join via a correlated subquery so
    # we hit only blog_posts rows with no author_id yet and a non-empty
    # author_name.
    op.execute(
        sa.text(
            """
            UPDATE blog_posts
            SET author_id = (
                SELECT u.id FROM users u
                WHERE lower(u.first_name || ' ' || u.last_name)
                      = lower(blog_posts.author_name)
                LIMIT 1
            )
            WHERE blog_posts.author_id IS NULL
              AND blog_posts.author_name IS NOT NULL
              AND blog_posts.author_name <> ''
            """
        )
    )

    # ---- 3. blog_post_co_authors M2M -------------------------------------
    if "blog_post_co_authors" not in existing_tables:
        op.create_table(
            "blog_post_co_authors",
            sa.Column(
                "post_id",
                sa.Integer(),
                sa.ForeignKey("blog_posts.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
        )


def downgrade() -> None:
    if op.get_context().as_sql:
        existing_tables = {"blog_post_co_authors"}
        blog_post_columns = {"author_id"}
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing_tables = set(inspector.get_table_names())
        blog_post_columns = {c["name"] for c in inspector.get_columns("blog_posts")}

    if "blog_post_co_authors" in existing_tables:
        op.drop_table("blog_post_co_authors")

    if "author_id" in blog_post_columns:
        # Index + FK names match what upgrade() created. drop_constraint
        # is a no-op on SQLite (which the test suite may use) but works
        # on PG; wrap in try/except to stay safe across dialects.
        try:
            op.drop_index("ix_blog_posts_author_id", table_name="blog_posts")
        except Exception:
            pass
        try:
            op.drop_constraint(
                "fk_blog_posts_author_id_users",
                "blog_posts",
                type_="foreignkey",
            )
        except Exception:
            pass
        op.drop_column("blog_posts", "author_id")
