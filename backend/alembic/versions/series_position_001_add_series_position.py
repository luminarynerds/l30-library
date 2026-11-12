"""Add catalog_items.series_position (numeric reading-order position)

Revision ID: series_position_001
Revises: l30_waitlist_001
Create Date: 2026-06-11

Derives a numeric reading-order position from the freeform
``catalog_items.series_number`` (MARC 490 $v / 800 $v) so the catalog item
page can show "Book N in [series]" with prev/next links. The freeform value
stays the source of truth; this column is the parsed integer, NULL when the
enumeration is missing or unparseable.

Idempotent ALTER pattern (see courses_created_by_id_001): L30's init_db.py
auto-creates tables from the SQLAlchemy models at startup, so by the time
alembic runs the column may already exist. ADD COLUMN IF NOT EXISTS and
CREATE INDEX IF NOT EXISTS make re-runs safe on a populated database.

Backfill runs in Python so it uses the exact same parser as the live mapping
layer (app.services.series_position.parse_series_position) -- this keeps the
"Issue 28" -> 28 / "2.5" -> NULL / "1-3" -> NULL rules identical between the
one-time backfill and every subsequent create/update.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.services.series_position import parse_series_position


revision: str = "series_position_001"
down_revision: Union[str, None] = "l30_waitlist_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE catalog_items "
        "ADD COLUMN IF NOT EXISTS series_position INTEGER"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_catalog_items_series_position "
        "ON catalog_items (series_position)"
    )

    # Backfill existing rows. Only rows with a non-empty series_number can
    # yield a position; everything else stays NULL.
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, series_number FROM catalog_items "
            "WHERE series_number IS NOT NULL AND btrim(series_number) <> ''"
        )
    ).fetchall()

    for row_id, series_number in rows:
        position = parse_series_position(series_number)
        if position is not None:
            conn.execute(
                sa.text(
                    "UPDATE catalog_items SET series_position = :pos WHERE id = :id"
                ),
                {"pos": position, "id": row_id},
            )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_catalog_items_series_position")
    op.execute("ALTER TABLE catalog_items DROP COLUMN IF EXISTS series_position")
