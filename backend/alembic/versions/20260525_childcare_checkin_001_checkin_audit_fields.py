# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""childcare check-in / no-show audit fields

Revision ID: childcare_checkin_001
Revises: pickup_auth_001
Create Date: 2026-05-25 12:00:00.000000+00:00

Adds five nullable audit columns to ``childcare_registrations`` so the
staff-facing roster surface can record:

  * who signed a child in (``checked_in_by_staff_id``)
  * who signed them out (``checked_out_by_staff_id``) -- complements the
    existing ``checked_out_by_name`` (the adult picking up) added in
    ``pickup_auth_001``; this column is the **staff member** who
    operated the checkout flow.
  * who flagged them as a no-show (``no_show_flagged_by_staff_id``,
    ``no_show_flagged_at``) plus a free-text reason.

All columns nullable + idempotent so init_db.py's create_all and a
later alembic upgrade don't fight each other (see L30 init_db vs
alembic pattern in memory feedback_l30_init_db_vs_alembic_new_table).

FKs use ON DELETE SET NULL so a user account being deleted doesn't
cascade-wipe historical childcare audit rows.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "childcare_checkin_001"
down_revision: Union[str, None] = "pickup_auth_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Staff who signed the child in.
    op.execute(
        "ALTER TABLE childcare_registrations "
        "ADD COLUMN IF NOT EXISTS checked_in_by_staff_id INTEGER "
        "REFERENCES users(id) ON DELETE SET NULL"
    )

    # Staff who operated the checkout flow (distinct from
    # checked_out_by_name, which is the *adult picking up*).
    op.execute(
        "ALTER TABLE childcare_registrations "
        "ADD COLUMN IF NOT EXISTS checked_out_by_staff_id INTEGER "
        "REFERENCES users(id) ON DELETE SET NULL"
    )

    # No-show audit triad.
    op.execute(
        "ALTER TABLE childcare_registrations "
        "ADD COLUMN IF NOT EXISTS no_show_flagged_by_staff_id INTEGER "
        "REFERENCES users(id) ON DELETE SET NULL"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "ADD COLUMN IF NOT EXISTS no_show_flagged_at TIMESTAMPTZ"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "ADD COLUMN IF NOT EXISTS no_show_reason TEXT"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE childcare_registrations "
        "DROP COLUMN IF EXISTS no_show_reason"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "DROP COLUMN IF EXISTS no_show_flagged_at"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "DROP COLUMN IF EXISTS no_show_flagged_by_staff_id"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "DROP COLUMN IF EXISTS checked_out_by_staff_id"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "DROP COLUMN IF EXISTS checked_in_by_staff_id"
    )
