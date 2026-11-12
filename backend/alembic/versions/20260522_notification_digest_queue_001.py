# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create notification_digest_queue table

Digest Mode batching: when a patron enables Digest Mode the preference gate
suppresses the immediate per-event email and drops a lightweight row in this
table instead. The scheduled send_notification_digests job aggregates a
patron's pending rows into one summary email at their configured cadence,
sends it, and deletes the rows.

L30 init_db.py auto-creates tables from SQLAlchemy models at backend startup,
so this migration is idempotent: it skips the create when the table already
exists (see [[feedback_l30_init_db_vs_alembic_new_table]]). It is still
required so deploys whose init_db ran against an older model set converge.

Revision ID: notification_digest_queue_001
Revises: events_sensory_fields_001
Create Date: 2026-05-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "notification_digest_queue_001"
down_revision: Union[str, None] = "tech_quick_links_seed_icons_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not op.get_context().as_sql:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        if "notification_digest_queue" in inspector.get_table_names():
            # init_db.py already created it from the SQLAlchemy model.
            return

    op.create_table(
        "notification_digest_queue",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("context_data", sa.JSON(), nullable=True),
        sa.Column(
            "dedup_key",
            sa.String(length=128),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "notification_type",
            "dedup_key",
            name="uq_notification_digest_queue_dedup",
        ),
    )
    op.create_index(
        "ix_notification_digest_queue_user",
        "notification_digest_queue",
        ["user_id"],
    )


def downgrade() -> None:
    if not op.get_context().as_sql:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        if "notification_digest_queue" not in inspector.get_table_names():
            return
    op.drop_index(
        "ix_notification_digest_queue_user",
        table_name="notification_digest_queue",
    )
    op.drop_table("notification_digest_queue")
