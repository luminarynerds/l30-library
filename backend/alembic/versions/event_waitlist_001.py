# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""event_waitlist_entries: real waitlist with claim-token magic link

Revision ID: event_waitlist_001
Revises: df85cac32c74
Create Date: 2026-05-20

Adds the event_waitlist_entries table (separate from EventRegistration's
legacy WAITLISTED status). New patron-facing waitlist sign-ups land here;
existing WAITLISTED rows in event_registrations are left untouched and drain
through the legacy cancel-promotion path (kept as a fallback).

Status values: waiting | notified | claimed | expired | cancelled

Indexes:
- partial unique on (event_id, lower(email)) WHERE status IN ('waiting','notified')
  mirrors event_registrations' idempotency pattern (see migration
  20260515_7cfe9045127a_events_fixes_unique_reg_index_hot_path_.py).
- (event_id, status, created_at) for position queries.
"""

from alembic import op
import sqlalchemy as sa


revision = "event_waitlist_001"
down_revision = "df85cac32c74"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_waitlist_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column(
            "registrant_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="waiting",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_token", sa.String(64), nullable=True),
        sa.Column(
            "claim_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("cancel_token", sa.String(64), nullable=True),
    )

    op.create_index(
        "ix_event_waitlist_event_id",
        "event_waitlist_entries",
        ["event_id"],
    )
    op.create_index(
        "ix_event_waitlist_position",
        "event_waitlist_entries",
        ["event_id", "status", "created_at"],
    )
    op.create_index(
        "ix_event_waitlist_claim_token",
        "event_waitlist_entries",
        ["claim_token"],
        unique=False,
    )

    # Partial unique index: only enforce uniqueness for active rows.
    # PostgreSQL supports the WHERE clause; SQLite (test fallback) does not
    # honour it but does respect the index name + columns, which is fine for
    # tests that don't hit the duplicate-active-row path.
    op.create_index(
        "ix_event_waitlist_unique_active_email",
        "event_waitlist_entries",
        ["event_id", sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("status IN ('waiting', 'notified')"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_waitlist_unique_active_email",
        table_name="event_waitlist_entries",
    )
    op.drop_index(
        "ix_event_waitlist_claim_token",
        table_name="event_waitlist_entries",
    )
    op.drop_index("ix_event_waitlist_position", table_name="event_waitlist_entries")
    op.drop_index("ix_event_waitlist_event_id", table_name="event_waitlist_entries")
    op.drop_table("event_waitlist_entries")
