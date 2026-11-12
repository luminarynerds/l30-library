# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add event_language to events

Program language ("conducted in Spanish") was not modeled — only the ASL
accessibility flag existed. Nullable, no backfill: NULL = unspecified.

Revision ID: event_language_001
Revises: 65eaa60eb77d
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "event_language_001"
down_revision = "65eaa60eb77d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("event_language", sa.String(length=20), nullable=True),
    )
    op.create_index(
        "ix_events_event_language", "events", ["event_language"], unique=False, if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_events_event_language", table_name="events")
    op.drop_column("events", "event_language")
