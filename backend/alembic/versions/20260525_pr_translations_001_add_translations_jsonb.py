# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add translations JSONB column to parent_resource_guide_items.

Revision ID: pr_translations_001
Revises: po_followup_referrals_001
Create Date: 2026-05-25

Adds a single JSONB column to hold per-language overrides of an item's
user-facing copy (title, description). Defaults to ``'{}'::jsonb`` so
existing rows behave identically -- the GET route falls back to the
source-language columns when no translation exists for the requested
``lang`` query param.

Why JSONB and not a sibling table:
  - Read-mostly: staff edit translations rarely, parents read them
    constantly; one row fetch beats a join.
  - Bounded shape: 1-5 languages typical, two short text fields each.
  - No requirement to search inside translations or audit per-language
    edit history in v1. Revisit when those land.

Idempotency: this migration uses ``ADD COLUMN IF NOT EXISTS`` because
``init_db.py`` at backend startup auto-creates new columns from the
SQLAlchemy model metadata before alembic runs
(see feedback_l30_init_db_vs_alembic_new_table).

The ``languages`` ARRAY(String) column already exists in the prod
schema as of 2026-05-25 (verified empty: 0 rows in
``parent_resource_guide_items`` total). This migration does not touch
it; surfacing ``languages`` in the API response and TS type is a
read-side schema change that doesn't need a migration.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "pr_translations_001"
down_revision: Union[str, None] = "po_followup_referrals_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent ADD COLUMN -- init_db.py may have already created the
    # column from model metadata at container startup. ADD COLUMN IF NOT
    # EXISTS short-circuits cleanly in that case (the model defines
    # nullable=False with server_default '{}' so existing rows have a
    # valid value either way).
    op.execute(
        """
        ALTER TABLE parent_resource_guide_items
        ADD COLUMN IF NOT EXISTS translations JSONB NOT NULL DEFAULT '{}'::jsonb
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE parent_resource_guide_items
        DROP COLUMN IF EXISTS translations
        """
    )
