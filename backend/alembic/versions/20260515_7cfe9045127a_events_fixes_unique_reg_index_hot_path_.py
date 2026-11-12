# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""events fixes: unique reg index, hot-path indexes, event.attended_count

Adds:
  - event_registrations: partial UNIQUE index on (event_id, lower(patron_email))
    where status IN ('confirmed','waitlisted') — closes the duplicate-registration
    race between two concurrent same-patron registrations.
  - event_registrations: functional index on lower(patron_email).
  - event_registrations: composite index on (event_id, status).
  - events: index on start_time.
  - events: partial index on start_time WHERE is_published = true.
  - events.attended_count: nullable Integer column mirroring
    Program.actual_attendance for PLS / IMLS attendance reporting.

Revision ID: 7cfe9045127a
Revises: ref_chat_unread_001
Create Date: 2026-05-15 15:18:33.709946+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7cfe9045127a'
down_revision: Union[str, None] = 'ref_chat_unread_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. events.attended_count column. Nullable on purpose:
    #    NULL = staff has not entered a count yet,
    #    0    = nobody came.
    # ------------------------------------------------------------------
    op.add_column(
        "events",
        sa.Column("attended_count", sa.Integer(), nullable=True),
    )

    # ------------------------------------------------------------------
    # 2. Partial UNIQUE index on (event_id, lower(patron_email)) for
    #    active registrations only. The two unlocked SELECTs in the
    #    register endpoint can both pass when a patron double-submits;
    #    this index forces one of the two inserts to fail with
    #    IntegrityError so the API returns a clean 409.
    # ------------------------------------------------------------------
    op.create_index(
        "ix_event_registrations_unique_active_per_email",
        "event_registrations",
        ["event_id", sa.text("lower(patron_email)")],
        unique=True,
        postgresql_where=sa.text("status IN ('confirmed', 'waitlisted')"),
    )

    # ------------------------------------------------------------------
    # 3. Hot-path read indexes for the registration table.
    # ------------------------------------------------------------------
    op.create_index(
        "ix_event_registrations_email_lower",
        "event_registrations",
        [sa.text("lower(patron_email)")],
        unique=False,
    )
    op.create_index(
        "ix_event_registrations_event_status",
        "event_registrations",
        ["event_id", "status"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 4. Hot-path read indexes for events.
    # ------------------------------------------------------------------
    op.create_index(
        "ix_events_start_time",
        "events",
        ["start_time"],
        unique=False,
    )
    op.create_index(
        "ix_events_published_start",
        "events",
        ["start_time"],
        unique=False,
        postgresql_where=sa.text("is_published = true"),
    )


def downgrade() -> None:
    op.drop_index("ix_events_published_start", table_name="events")
    op.drop_index("ix_events_start_time", table_name="events")
    op.drop_index("ix_event_registrations_event_status", table_name="event_registrations")
    op.drop_index("ix_event_registrations_email_lower", table_name="event_registrations")
    op.drop_index(
        "ix_event_registrations_unique_active_per_email",
        table_name="event_registrations",
    )
    op.drop_column("events", "attended_count")
