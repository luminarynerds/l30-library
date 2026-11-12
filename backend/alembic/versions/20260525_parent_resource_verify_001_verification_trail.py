# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add last_verified_at + verified_by_id to parent_resource_guide_items; create parent_resource_guide_flags.

Revision ID: parent_resource_verify_001
Revises: po_followup_referrals_001
Create Date: 2026-05-25

Verification trail for the parent resource guide:

  - parent_resource_guide_items gets `last_verified_at` + `verified_by_id`
    columns so the UI can render "Verified Mar 2026 by Rosa T." under each
    item card. NULL on existing rows -- treated as "never re-verified"
    and rendered as stale by default. That's the right starting condition:
    the rows have NOT been checked since they were entered, and that
    should be visible.

  - parent_resource_guide_flags is a new table backing the "Flag as out
    of date" affordance. Status / reason / resolution columns hold
    lowercase string enums (feedback_l30_enum_case). Cascade-on-delete
    from items so a retired resource doesn't leave orphan flag rows in
    the staff queue.

Idempotent: every CREATE TABLE / ADD COLUMN / CREATE INDEX uses
IF NOT EXISTS because init_db.py at container startup auto-creates
from SQLAlchemy model metadata BEFORE alembic runs
(feedback_l30_init_db_vs_alembic_new_table).
"""
from alembic import op
import sqlalchemy as sa


revision = "parent_resource_verify_001"
down_revision = "po_followup_referrals_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Columns on parent_resource_guide_items
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE parent_resource_guide_items "
        "ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMP WITH TIME ZONE"
    )
    op.execute(
        "ALTER TABLE parent_resource_guide_items "
        "ADD COLUMN IF NOT EXISTS verified_by_id INTEGER"
    )
    # Foreign key as a separate idempotent step -- pg_constraint probe so
    # re-running the migration after init_db.py created the column does
    # not 42710 "constraint already exists".
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'parent_resource_guide_items_verified_by_id_fkey'
            ) THEN
                ALTER TABLE parent_resource_guide_items
                ADD CONSTRAINT parent_resource_guide_items_verified_by_id_fkey
                FOREIGN KEY (verified_by_id) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END$$;
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_resource_item_last_verified "
        "ON parent_resource_guide_items(last_verified_at)"
    )

    # ------------------------------------------------------------------
    # parent_resource_guide_flags
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS parent_resource_guide_flags (
            id              SERIAL PRIMARY KEY,
            item_id         INTEGER NOT NULL REFERENCES parent_resource_guide_items(id) ON DELETE CASCADE,
            flagged_by_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            reason_code     VARCHAR(50) NOT NULL,
            comment         TEXT,
            status          VARCHAR(20) NOT NULL DEFAULT 'open',
            resolution      VARCHAR(50),
            resolution_notes TEXT,
            resolved_by_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            resolved_at     TIMESTAMP WITH TIME ZONE,
            created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_flags_item "
        "ON parent_resource_guide_flags(item_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_flags_status_created "
        "ON parent_resource_guide_flags(status, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS parent_resource_guide_flags")
    op.execute(
        "DROP INDEX IF EXISTS idx_resource_item_last_verified"
    )
    op.execute(
        "ALTER TABLE parent_resource_guide_items "
        "DROP COLUMN IF EXISTS verified_by_id"
    )
    op.execute(
        "ALTER TABLE parent_resource_guide_items "
        "DROP COLUMN IF EXISTS last_verified_at"
    )
