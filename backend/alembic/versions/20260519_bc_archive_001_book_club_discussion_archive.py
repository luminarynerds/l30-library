"""book club discussion archive + FTS search

Revision ID: bc_archive_001
Revises: bc_archive_merge_001
Create Date: 2026-05-19 12:40:00.000000+00:00

Adds:
  * ``book_club_meetings.is_archived`` (soft-archive toggle)
  * ``book_club_discussions`` table (real persistence; until now
    list_discussions returned [] and create_discussion returned an
    in-memory object that never persisted)
  * Postgres FTS infrastructure on ``book_club_discussions``:
    ``search_vector`` tsvector + GIN index + before-insert/update
    trigger that maintains it via setweight (title A, body B,
    author_display_name C). Matches the catalog FTS pattern in
    ``app/seeds/seed_search_indexes.py``.
  * ``organization_features.book_club_history_enabled`` feature flag
    (default false).

Idempotent: every step uses ``IF [NOT] EXISTS`` because L30's
``init_db.py`` auto-creates tables from SQLAlchemy models at backend
startup, so by the time alembic runs the table may already exist and
plain ``op.create_table()`` raises DuplicateTableError. See
``backend/scripts/check_alembic_idempotent.py`` and the
``feedback_l30_init_db_vs_alembic_new_table`` memory note.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "bc_archive_001"
down_revision: Union[str, None] = "bc_archive_merge_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pure raw-SQL with IF [NOT] EXISTS so the migration is idempotent
    # AND offline-mode-safe (the catalog-FTS seed pattern in
    # seed_search_indexes.py uses inspector, but inspector requires a
    # live connection — alembic --sql breaks on it).

    # -----------------------------------------------------------------
    # 1. is_archived column on book_club_meetings (+ composite index)
    # -----------------------------------------------------------------
    op.execute(
        "ALTER TABLE book_club_meetings "
        "ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_book_club_meetings_archived "
        "ON book_club_meetings (book_club_id, is_archived)"
    )

    # -----------------------------------------------------------------
    # 2. book_club_discussions table (idempotent — init_db may have
    #    already created the bare columns from the SQLAlchemy model)
    # -----------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS book_club_discussions (
            id SERIAL PRIMARY KEY,
            meeting_id INTEGER NOT NULL REFERENCES book_club_meetings(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            author_display_name VARCHAR(255) NOT NULL DEFAULT '',
            title VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    # init_db.py may have pre-created the table from an older model
    # version that's missing some of the columns we depend on. Each
    # ALTER ... ADD COLUMN IF NOT EXISTS is idempotent on its own and
    # safe to run unconditionally.
    op.execute("ALTER TABLE book_club_discussions ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE book_club_discussions ADD COLUMN IF NOT EXISTS author_display_name VARCHAR(255) NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE book_club_discussions ADD COLUMN IF NOT EXISTS title VARCHAR(255) NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE book_club_discussions ADD COLUMN IF NOT EXISTS body TEXT NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE book_club_discussions ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE book_club_discussions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
    op.execute("ALTER TABLE book_club_discussions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_book_club_discussions_meeting "
        "ON book_club_discussions (meeting_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_book_club_discussions_created_at "
        "ON book_club_discussions (created_at)"
    )

    # -----------------------------------------------------------------
    # 3. Postgres FTS: search_vector + trigger + GIN index.
    #    Matches the pattern in app/seeds/seed_search_indexes.py.
    # -----------------------------------------------------------------
    op.execute(
        "ALTER TABLE book_club_discussions "
        "ADD COLUMN IF NOT EXISTS search_vector tsvector"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION book_club_discussions_search_update()
        RETURNS trigger AS $$
        BEGIN
          NEW.search_vector :=
            setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(NEW.body, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(NEW.author_display_name, '')), 'C');
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        "DROP TRIGGER IF EXISTS book_club_discussions_search_trigger "
        "ON book_club_discussions"
    )
    op.execute(
        """
        CREATE TRIGGER book_club_discussions_search_trigger
          BEFORE INSERT OR UPDATE OF title, body, author_display_name
          ON book_club_discussions
          FOR EACH ROW
          EXECUTE FUNCTION book_club_discussions_search_update()
        """
    )

    # Backfill search_vector on any preexisting rows (no-op on a fresh
    # install). UPDATE-self trips the trigger.
    op.execute(
        "UPDATE book_club_discussions SET title = title WHERE search_vector IS NULL"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_book_club_discussions_search_vector "
        "ON book_club_discussions USING gin (search_vector)"
    )

    # -----------------------------------------------------------------
    # 4. organization_features.book_club_history_enabled feature flag
    # -----------------------------------------------------------------
    op.execute(
        "ALTER TABLE organization_features "
        "ADD COLUMN IF NOT EXISTS book_club_history_enabled BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    # Reverse order: feature flag, FTS infrastructure, discussion table,
    # is_archived column. Idempotent guards so a partial migration can
    # still roll back.
    op.execute(
        "ALTER TABLE organization_features "
        "DROP COLUMN IF EXISTS book_club_history_enabled"
    )

    op.execute(
        "DROP INDEX IF EXISTS ix_book_club_discussions_search_vector"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS book_club_discussions_search_trigger "
        "ON book_club_discussions"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS book_club_discussions_search_update()"
    )

    op.execute("DROP TABLE IF EXISTS book_club_discussions")

    op.execute(
        "DROP INDEX IF EXISTS ix_book_club_meetings_archived"
    )
    op.execute(
        "ALTER TABLE book_club_meetings DROP COLUMN IF EXISTS is_archived"
    )
