# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add saved_searches table.

Revision ID: saved_searches_001
Revises: subjects_join_001
Create Date: 2026-05-16

Patron-named catalog search snapshots + opt-in new-arrival alert metadata.
Uses ``CREATE TABLE IF NOT EXISTS`` semantics so the L30 backend startup
init_db pass (which auto-creates new ORM tables) does not collide with
this migration on first deploy.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "saved_searches_001"
down_revision = "subjects_join_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    offline = op.get_context().as_sql
    if offline:
        inspector = None
        has_saved_searches = False
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        has_saved_searches = inspector.has_table("saved_searches")

    if not has_saved_searches:
        op.create_table(
            "saved_searches",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("library_system_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("query", sa.Text(), nullable=True),
            sa.Column(
                "filters_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("sort_by", sa.String(length=40), nullable=True),
            sa.Column("view_mode", sa.String(length=16), nullable=True),
            sa.Column(
                "notify_on_new",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "notify_in_app",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "notify_email",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("last_notified_item_id", sa.Integer(), nullable=True),
            sa.Column(
                "last_run_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # Indexes (idempotent — IF NOT EXISTS lets reruns be safe)
    if offline:
        existing_indexes: set[str] = set()
    else:
        existing_indexes = {
            ix["name"]
            for ix in inspector.get_indexes("saved_searches")
        } if inspector.has_table("saved_searches") else set()

    if "ix_saved_searches_user_id" not in existing_indexes:
        op.create_index(
            "ix_saved_searches_user_id",
            "saved_searches",
            ["user_id"],
        )

    if "ix_saved_searches_library_system_id" not in existing_indexes:
        op.create_index(
            "ix_saved_searches_library_system_id",
            "saved_searches",
            ["library_system_id"],
        )

    if "ix_saved_searches_user_created" not in existing_indexes:
        op.create_index(
            "ix_saved_searches_user_created",
            "saved_searches",
            ["user_id", "created_at"],
        )

    if "ix_saved_searches_notify_on_new" not in existing_indexes:
        op.create_index(
            "ix_saved_searches_notify_on_new",
            "saved_searches",
            ["notify_on_new"],
            postgresql_where=sa.text("notify_on_new = true"),
        )


def downgrade() -> None:
    op.drop_index("ix_saved_searches_notify_on_new", table_name="saved_searches")
    op.drop_index("ix_saved_searches_user_created", table_name="saved_searches")
    op.drop_index("ix_saved_searches_library_system_id", table_name="saved_searches")
    op.drop_index("ix_saved_searches_user_id", table_name="saved_searches")
    op.drop_table("saved_searches")
