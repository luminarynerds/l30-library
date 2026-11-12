# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Convert catalog_items.search_tsv to a STORED generated column.

Revision ID: search_tsv_generated_001
Revises: board_amendments_001
Create Date: 2026-05-08

The previous design maintained search_tsv via a BEFORE INSERT/UPDATE trigger
seeded by app/seeds/seed_search_indexes.py. PostgreSQL 12+ supports
GENERATED ALWAYS ... STORED tsvector columns natively, which:

  * Eliminates the trigger function and its plpgsql call overhead on writes.
  * Guarantees the column is always in sync (no risk of trigger being dropped).
  * Removes the seed's data-population step (UPDATE ... WHERE search_tsv IS NULL).

The text search configuration is fixed to 'english' to match historical data.
Changing it later requires another migration that rewrites the column.

This migration is destructive on a populated table because PostgreSQL does not
support converting an existing column to GENERATED in place; we drop and
re-add. Behaviour-wise that's safe: no application reads search_tsv directly
(it's only used inside FTS @@ predicates), and the GIN index is recreated.
On a large catalog_items table the ADD COLUMN ... GENERATED ... STORED
pass rewrites every row; expect proportional downtime.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "search_tsv_generated_001"
down_revision: Union[str, None] = "board_amendments_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GENERATION_EXPR = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(author, '')), 'B') || "
    "setweight(to_tsvector('english', coalesce(subjects, '')), 'C') || "
    "setweight(to_tsvector('english', coalesce(description, '')), 'D')"
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    if not op.get_context().as_sql:
        # If the column is already a generated column with the right expression,
        # this migration is a no-op. Detected via pg_attribute.attgenerated.
        already_generated = bind.exec_driver_sql(
            """
            SELECT attgenerated
            FROM pg_attribute
            WHERE attrelid = 'catalog_items'::regclass
              AND attname = 'search_tsv'
              AND NOT attisdropped
            """
        ).scalar()
        if already_generated == "s":
            return

    op.execute("DROP TRIGGER IF EXISTS catalog_items_search_tsv_trigger ON catalog_items")
    op.execute("DROP FUNCTION IF EXISTS catalog_items_search_tsv_update()")
    op.execute("DROP INDEX IF EXISTS ix_catalog_items_search_tsv")
    op.execute("ALTER TABLE catalog_items DROP COLUMN IF EXISTS search_tsv")

    op.execute(
        f"ALTER TABLE catalog_items "
        f"ADD COLUMN search_tsv tsvector "
        f"GENERATED ALWAYS AS ({GENERATION_EXPR}) STORED"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_catalog_items_search_tsv "
        "ON catalog_items USING gin (search_tsv)"
    )

    # The pre-existing untyped ix_catalog_items_fts_en (from
    # search_analytics_001) duplicates ix_catalog_items_search_tsv without
    # field weights. The runtime query uses the weighted column, so the older
    # index never matches and is dead weight.
    op.execute("DROP INDEX IF EXISTS ix_catalog_items_fts_en")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS ix_catalog_items_search_tsv")
    op.execute("ALTER TABLE catalog_items DROP COLUMN IF EXISTS search_tsv")

    op.execute("ALTER TABLE catalog_items ADD COLUMN search_tsv tsvector")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION catalog_items_search_tsv_update() RETURNS trigger AS $$
        BEGIN
          NEW.search_tsv :=
            setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(NEW.author, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(NEW.subjects, '')), 'C') ||
            setweight(to_tsvector('english', coalesce(NEW.description, '')), 'D');
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER catalog_items_search_tsv_trigger
          BEFORE INSERT OR UPDATE OF title, author, subjects, description
          ON catalog_items
          FOR EACH ROW
          EXECUTE FUNCTION catalog_items_search_tsv_update()
        """
    )
    op.execute("UPDATE catalog_items SET title = title")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_catalog_items_search_tsv "
        "ON catalog_items USING gin (search_tsv)"
    )
