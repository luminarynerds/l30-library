# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""authorized pickup adults + checkout enforcement

Revision ID: pickup_auth_001
Revises: mergepoint_20260520
Create Date: 2026-05-20 12:00:00.000000+00:00

Adds (all on ``childcare_registrations``):

  * ``authorized_pickup`` JSONB column (default ``[]``) -- list of
    ``{name, phone, relationship, id_required}`` entries the parent
    has authorized to pick the child up.
  * ``checked_out_by_name`` (String 200, nullable) -- name of the
    adult who actually picked the child up; matched against
    ``authorized_pickup`` at checkout time and persisted for audit.
  * ``checked_out_by_phone`` (String 50, nullable) -- phone of same.
  * ``pickup_override_reason`` (Text, nullable) -- only populated when
    staff overrode an unmatched/missing authorization; required when
    the registration has no ``authorized_pickup`` entries (legacy
    rows registered before the flag flipped) or staff is checking out
    to someone not on the list.

Also adds the feature flag:

  * ``organization_features.pickup_authorization_enabled`` BOOLEAN
    (default FALSE -- prod parents have childcare sessions without
    authorized-pickup lists; rolling enforcement on without their
    consent would break checkout for existing users).

Idempotent: every step uses ``IF [NOT] EXISTS`` because L30's
``init_db.py`` auto-creates tables from SQLAlchemy models at backend
startup, so by the time alembic runs the columns may already exist.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "pickup_auth_001"
down_revision: Union[str, None] = "mergepoint_20260520"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. authorized_pickup JSONB on childcare_registrations
    op.execute(
        "ALTER TABLE childcare_registrations "
        "ADD COLUMN IF NOT EXISTS authorized_pickup JSONB NOT NULL "
        "DEFAULT '[]'::jsonb"
    )

    # 2. checkout audit columns (matched entry name+phone, plus any
    #    staff override reason).
    op.execute(
        "ALTER TABLE childcare_registrations "
        "ADD COLUMN IF NOT EXISTS checked_out_by_name VARCHAR(200)"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "ADD COLUMN IF NOT EXISTS checked_out_by_phone VARCHAR(50)"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "ADD COLUMN IF NOT EXISTS pickup_override_reason TEXT"
    )

    # 3. organization_features.pickup_authorization_enabled flag
    op.execute(
        "ALTER TABLE organization_features "
        "ADD COLUMN IF NOT EXISTS pickup_authorization_enabled "
        "BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE organization_features "
        "DROP COLUMN IF EXISTS pickup_authorization_enabled"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "DROP COLUMN IF EXISTS pickup_override_reason"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "DROP COLUMN IF EXISTS checked_out_by_phone"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "DROP COLUMN IF EXISTS checked_out_by_name"
    )
    op.execute(
        "ALTER TABLE childcare_registrations "
        "DROP COLUMN IF EXISTS authorized_pickup"
    )
