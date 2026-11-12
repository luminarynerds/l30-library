"""restore search_tsv column, trigger, and GIN indexes

The search_tsv tsvector column was erroneously dropped in schema_sync_002
because it was maintained by a trigger rather than the SQLAlchemy model.
This migration restores it along with the trigger and GIN/trigram indexes
that power full-text catalog search.

Revision ID: schema_sync_007
Revises: schema_sync_006
Create Date: 2026-05-10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "schema_sync_007"
down_revision: Union[str, None] = "schema_sync_006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add search_tsv column
    op.add_column(
        "catalog_items",
        sa.Column("search_tsv", sa.dialects.postgresql.TSVECTOR(), nullable=True),
    )

    # Create trigger function for weighted tsvector
    op.execute("""
        CREATE OR REPLACE FUNCTION catalog_items_search_tsv_update() RETURNS trigger AS $$
        BEGIN
          NEW.search_tsv :=
            setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(NEW.author, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(NEW.subjects, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'D');
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger -- split into per-statement calls because asyncpg
    # rejects multi-statement strings in prepared-statement mode.
    op.execute("DROP TRIGGER IF EXISTS catalog_items_search_tsv_trigger ON catalog_items")
    op.execute("""
        CREATE TRIGGER catalog_items_search_tsv_trigger
          BEFORE INSERT OR UPDATE OF title, author, subjects, description
          ON catalog_items
          FOR EACH ROW
          EXECUTE FUNCTION catalog_items_search_tsv_update()
    """)

    # Backfill existing rows
    op.execute("UPDATE catalog_items SET title = title WHERE search_tsv IS NULL")

    # GIN indexes for FTS and trigram similarity
    op.create_index(
        "ix_catalog_items_search_tsv",
        "catalog_items",
        ["search_tsv"],
        postgresql_using="gin",
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_catalog_items_title_trgm "
        "ON catalog_items USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_catalog_items_author_trgm "
        "ON catalog_items USING gin (author gin_trgm_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_items_author_trgm", table_name="catalog_items", postgresql_using="gin")
    op.drop_index("ix_catalog_items_title_trgm", table_name="catalog_items", postgresql_using="gin")
    op.drop_index("ix_catalog_items_search_tsv", table_name="catalog_items", postgresql_using="gin")
    op.execute("DROP TRIGGER IF EXISTS catalog_items_search_tsv_trigger ON catalog_items")
    op.execute("DROP FUNCTION IF EXISTS catalog_items_search_tsv_update()")
    op.drop_column("catalog_items", "search_tsv")
