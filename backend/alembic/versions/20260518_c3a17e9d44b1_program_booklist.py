"""program_booklist + reading_programs_booklist_enabled flag

Revision ID: c3a17e9d44b1
Revises: b2f65b0b98e1
Create Date: 2026-05-18 19:00:00.000000+00:00

Adds curated booklist support to reading programs:

* ``program_booklist`` -- M2M join table between reading_programs and
  catalog_items with display_order + optional staff note. Unique on
  (program_id, catalog_item_id).
* ``organization_features.reading_programs_booklist_enabled`` -- feature flag
  gating the booklist UI/API surface. Default OFF.

Wrap CREATE/ALTER in IF NOT EXISTS / IF EXISTS NOT to stay idempotent
across init_db model-create + alembic upgrade. See
[[feedback_l30_init_db_vs_alembic_new_table]].
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c3a17e9d44b1"
down_revision: Union[str, None] = "b2f65b0b98e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS program_booklist (
            id SERIAL PRIMARY KEY,
            program_id INTEGER NOT NULL REFERENCES reading_programs(id) ON DELETE CASCADE,
            catalog_item_id INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
            display_order INTEGER NOT NULL DEFAULT 0,
            note VARCHAR(500),
            added_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT uq_program_booklist_item UNIQUE (program_id, catalog_item_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_program_booklist_program_id "
        "ON program_booklist (program_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_program_booklist_catalog_item_id "
        "ON program_booklist (catalog_item_id)"
    )
    op.execute(
        """
        ALTER TABLE organization_features
        ADD COLUMN IF NOT EXISTS reading_programs_booklist_enabled
            BOOLEAN NOT NULL DEFAULT FALSE
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE organization_features "
        "DROP COLUMN IF EXISTS reading_programs_booklist_enabled"
    )
    op.execute("DROP INDEX IF EXISTS ix_program_booklist_catalog_item_id")
    op.execute("DROP INDEX IF EXISTS ix_program_booklist_program_id")
    op.execute("DROP TABLE IF EXISTS program_booklist")
