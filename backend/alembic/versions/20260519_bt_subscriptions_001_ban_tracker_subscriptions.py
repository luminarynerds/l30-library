# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""ban tracker subscriptions table (phase 1 backend foundation)

Revision ID: bt_subscriptions_001
Revises: bc_waitlist_001
Create Date: 2026-05-19 22:00:00.000000+00:00

Adds:
  * ``ban_tracker_subscriptions`` table — one row per (patron, filter
    set). Phase 1 of the watch-list feature: model + CRUD only. The
    digest worker (phase 3) reads ``is_active`` + ``frequency`` +
    ``last_sent_at`` to decide whether a row is due. ``unsubscribe_token``
    is generated in the create route and unique-indexed so the phase-3
    email pipeline can resolve it in one lookup.

Idempotent: every step uses ``IF [NOT] EXISTS`` because L30's
``init_db.py`` auto-creates tables from SQLAlchemy models at backend
startup, so by the time alembic runs the table may already exist and a
plain ``op.create_table()`` raises DuplicateTableError.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "bt_subscriptions_001"
down_revision: Union[str, None] = "bc_waitlist_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pure raw-SQL with IF [NOT] EXISTS so the migration is idempotent
    # against init_db.py pre-creation AND offline-mode-safe
    # (``alembic upgrade head --sql`` never opens a connection).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ban_tracker_subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            scope VARCHAR(32) NOT NULL,
            state_filter VARCHAR(2),
            ban_type_filter VARCHAR(32),
            frequency VARCHAR(16) NOT NULL DEFAULT 'weekly',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            last_sent_at TIMESTAMPTZ,
            unsubscribe_token VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    # init_db.py may have pre-created the table from an older model
    # version. ADD COLUMN IF NOT EXISTS is idempotent on its own.
    op.execute(
        "ALTER TABLE ban_tracker_subscriptions "
        "ADD COLUMN IF NOT EXISTS user_id INTEGER "
        "REFERENCES users(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE ban_tracker_subscriptions "
        "ADD COLUMN IF NOT EXISTS scope VARCHAR(32) NOT NULL DEFAULT 'any'"
    )
    op.execute(
        "ALTER TABLE ban_tracker_subscriptions "
        "ADD COLUMN IF NOT EXISTS state_filter VARCHAR(2)"
    )
    op.execute(
        "ALTER TABLE ban_tracker_subscriptions "
        "ADD COLUMN IF NOT EXISTS ban_type_filter VARCHAR(32)"
    )
    op.execute(
        "ALTER TABLE ban_tracker_subscriptions "
        "ADD COLUMN IF NOT EXISTS frequency VARCHAR(16) NOT NULL DEFAULT 'weekly'"
    )
    op.execute(
        "ALTER TABLE ban_tracker_subscriptions "
        "ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"
    )
    op.execute(
        "ALTER TABLE ban_tracker_subscriptions "
        "ADD COLUMN IF NOT EXISTS last_sent_at TIMESTAMPTZ"
    )
    op.execute(
        "ALTER TABLE ban_tracker_subscriptions "
        "ADD COLUMN IF NOT EXISTS unsubscribe_token VARCHAR(64)"
    )
    op.execute(
        "ALTER TABLE ban_tracker_subscriptions "
        "ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
    )
    op.execute(
        "ALTER TABLE ban_tracker_subscriptions "
        "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ban_tracker_subscriptions_user_id "
        "ON ban_tracker_subscriptions (user_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_ban_tracker_subscriptions_unsubscribe_token "
        "ON ban_tracker_subscriptions (unsubscribe_token)"
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS ix_ban_tracker_subscriptions_unsubscribe_token"
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_ban_tracker_subscriptions_user_id"
    )
    op.execute("DROP TABLE IF EXISTS ban_tracker_subscriptions")
