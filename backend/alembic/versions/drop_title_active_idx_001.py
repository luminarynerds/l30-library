# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Drop the title-level active-checkout unique index (#1427).

ix_active_item_checkout (UNIQUE on checkouts.item_id WHERE status='active')
wrongly capped a whole title at ONE active loan regardless of how many
physical copies the library owns. Per-copy uniqueness is enforced by
ix_active_item_copy_checkout, which stays.

The index was dropped manually on prod on 2026-06-09 but never codified in a
migration, so dev/demo databases and fresh installs built before the
initial_schema.sql fix still carry it. IF EXISTS makes this a safe no-op on
prod.

Downgrade is a deliberate no-op: recreating the index would fail on any
database that already has two copies of one title legitimately checked out,
and the title-level cap is not a behavior we ever want back.

Revision ID: drop_title_active_idx_001
Revises: lifecycle_3state_001
Create Date: 2026-07-04
"""
from __future__ import annotations

from typing import Union

from alembic import op


revision: str = "drop_title_active_idx_001"
down_revision: Union[str, None] = "lifecycle_3state_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_active_item_checkout")


def downgrade() -> None:
    pass
