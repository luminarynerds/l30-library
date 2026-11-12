# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""book club waitlist + capacity signals

Revision ID: bc_waitlist_001
Revises: 07891efc0089
Create Date: 2026-05-19 16:00:00.000000+00:00

Adds:
  * ``book_club_waitlist_entries`` table (FIFO waitlist for
    capacity-limited clubs; position computed at query time, never
    stored). Unique ``(book_club_id, user_id)`` so a patron can hold at
    most one entry per club, plus a ``(book_club_id, created_at)`` index
    for the ROW_NUMBER ordering / next-promotion lookup.
  * ``organization_features.book_club_waitlist_enabled`` feature flag
    (default false — opt-in per library).

Idempotent: every step uses ``IF [NOT] EXISTS`` because L30's
``init_db.py`` auto-creates tables from SQLAlchemy models at backend
startup, so by the time alembic runs the table may already exist and a
plain ``op.create_table()`` raises DuplicateTableError. See
``backend/scripts/check_alembic_idempotent.py`` and the
``feedback_l30_init_db_vs_alembic_new_table`` memory note.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "bc_waitlist_001"
down_revision: Union[str, None] = "07891efc0089"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pure raw-SQL with IF [NOT] EXISTS so the migration is idempotent
    # against init_db.py pre-creation AND offline-mode-safe
    # (``alembic upgrade head --sql`` never opens a connection).

    # -----------------------------------------------------------------
    # 1. book_club_waitlist_entries table (idempotent — init_db may have
    #    already created the bare columns from the SQLAlchemy model)
    # -----------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS book_club_waitlist_entries (
            id SERIAL PRIMARY KEY,
            book_club_id INTEGER NOT NULL REFERENCES book_clubs(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            notified_at TIMESTAMPTZ
        )
        """
    )

    # init_db.py may have pre-created the table from an older model
    # version missing some columns. Each ADD COLUMN IF NOT EXISTS is
    # idempotent on its own and safe to run unconditionally.
    op.execute(
        "ALTER TABLE book_club_waitlist_entries "
        "ADD COLUMN IF NOT EXISTS book_club_id INTEGER "
        "REFERENCES book_clubs(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE book_club_waitlist_entries "
        "ADD COLUMN IF NOT EXISTS user_id INTEGER "
        "REFERENCES users(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE book_club_waitlist_entries "
        "ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
    )
    op.execute(
        "ALTER TABLE book_club_waitlist_entries "
        "ADD COLUMN IF NOT EXISTS notified_at TIMESTAMPTZ"
    )

    # Single-column FK indexes (match the SQLAlchemy model's index=True).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_book_club_waitlist_entries_book_club_id "
        "ON book_club_waitlist_entries (book_club_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_book_club_waitlist_entries_user_id "
        "ON book_club_waitlist_entries (user_id)"
    )

    # Composite index for FIFO ordering / next-to-promote lookup.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_book_club_waitlist_entries_club_created "
        "ON book_club_waitlist_entries (book_club_id, created_at)"
    )

    # One waitlist entry per (club, user). ADD CONSTRAINT has no
    # IF NOT EXISTS in Postgres < 9.x semantics, so guard via catalog
    # lookup in a DO block (idempotent on re-run / init_db pre-create).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_waitlist_club_user'
            ) THEN
                ALTER TABLE book_club_waitlist_entries
                    ADD CONSTRAINT uq_waitlist_club_user
                    UNIQUE (book_club_id, user_id);
            END IF;
        END
        $$
        """
    )

    # -----------------------------------------------------------------
    # 2. organization_features.book_club_waitlist_enabled feature flag
    # -----------------------------------------------------------------
    op.execute(
        "ALTER TABLE organization_features "
        "ADD COLUMN IF NOT EXISTS book_club_waitlist_enabled "
        "BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    # Reverse order, idempotent guards so a partial migration still
    # rolls back cleanly.
    op.execute(
        "ALTER TABLE organization_features "
        "DROP COLUMN IF EXISTS book_club_waitlist_enabled"
    )

    op.execute(
        "ALTER TABLE book_club_waitlist_entries "
        "DROP CONSTRAINT IF EXISTS uq_waitlist_club_user"
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_book_club_waitlist_entries_club_created"
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_book_club_waitlist_entries_user_id"
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_book_club_waitlist_entries_book_club_id"
    )
    op.execute("DROP TABLE IF EXISTS book_club_waitlist_entries")
