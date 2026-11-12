# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""make event_registrations.patron_email nullable

Patrons without email can now register phone-only; the API enforces at
least one of email/phone, so the column can no longer be NOT NULL.

Revision ID: regemail_001
Revises: event_language_001
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "regemail_001"
down_revision = "event_language_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "event_registrations",
        "patron_email",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    # Backfill any phone-only rows before restoring NOT NULL.
    op.execute(
        "UPDATE event_registrations SET patron_email = '' WHERE patron_email IS NULL"
    )
    op.alter_column(
        "event_registrations",
        "patron_email",
        existing_type=sa.String(length=255),
        nullable=False,
    )
