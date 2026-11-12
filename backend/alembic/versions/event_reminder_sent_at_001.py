# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""event_registrations.reminder_sent_at + partial pending-reminder index

Adds:
  - event_registrations.reminder_sent_at: nullable TIMESTAMP WITH TIME ZONE,
    set by the send_event_reminders scheduler job after a successful send.
    Replaces the Redis-only dedup with a durable per-row marker so a Redis
    flush no longer causes duplicate reminders.
  - event_registrations: partial index
      ix_event_registrations_reminder_pending
      ON event_registrations (event_id)
      WHERE reminder_requested = true AND reminder_sent_at IS NULL
    Lets the hourly scheduler scan stay cheap as the table grows -- it only
    has to touch the rows that still need a reminder.

Revision ID: event_reminder_sent_at_001
Revises: 7cfe9045127a
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "event_reminder_sent_at_001"
down_revision: Union[str, None] = "7cfe9045127a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_registrations",
        sa.Column(
            "reminder_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_event_registrations_reminder_pending",
        "event_registrations",
        ["event_id"],
        postgresql_where=sa.text(
            "reminder_requested = true AND reminder_sent_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_registrations_reminder_pending",
        table_name="event_registrations",
    )
    op.drop_column("event_registrations", "reminder_sent_at")
