# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""catalog_demand_signals -- failed search / ILL / hold-pressure capture

Revision ID: catalog_demand_signals_001
Revises: drop_redundant_indexes_001
Create Date: 2026-05-20 10:35:00.000000+00:00

Adds the ``catalog_demand_signals`` table -- a unified capture surface
for evidence that the library's collection is missing something
patrons want. This PR ships only the table + a single ingest hook
(failed-search). Future PRs add ILL/peak-hold/agent-unfound hooks
plus a "selection assistant" admin report driven by this data.

Two pgsql enum types are created (``demand_signal_type``,
``demand_signal_resolution``); both values are lowercase per L30
convention (see ``feedback_l30_enum_case``).

Idempotent because L30 ``init_db.py`` auto-creates tables from
SQLAlchemy models at backend startup -- by the time alembic runs the
table may already exist. ``CREATE TYPE`` lacks ``IF NOT EXISTS`` in
Postgres, so the enums are guarded with a catalog-lookup ``DO $$``
block.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "catalog_demand_signals_001"
down_revision: Union[str, None] = "drop_redundant_indexes_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # 1. Enum types (idempotent via pg_type catalog lookup)
    # -----------------------------------------------------------------
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'demand_signal_type'
            ) THEN
                CREATE TYPE demand_signal_type AS ENUM (
                    'failed_search',
                    'ill_request',
                    'peak_hold_depth',
                    'agent_unfound'
                );
            END IF;
        END
        $$
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'demand_signal_resolution'
            ) THEN
                CREATE TYPE demand_signal_resolution AS ENUM (
                    'acquired',
                    'ill',
                    'no_action'
                );
            END IF;
        END
        $$
        """
    )

    # -----------------------------------------------------------------
    # 2. catalog_demand_signals table
    # -----------------------------------------------------------------
    # init_db.py may have pre-created columns from the SQLAlchemy
    # model; we use CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT
    # EXISTS for forward compatibility on either path.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS catalog_demand_signals (
            id SERIAL PRIMARY KEY,
            signal_type demand_signal_type NOT NULL,
            normalized_title VARCHAR(500),
            normalized_isbn VARCHAR(20),
            normalized_subject VARCHAR(255),
            query_text TEXT,
            patron_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMPTZ,
            resolution demand_signal_resolution,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )

    # Guard against init_db pre-creation with an older model shape.
    op.execute(
        "ALTER TABLE catalog_demand_signals "
        "ADD COLUMN IF NOT EXISTS normalized_title VARCHAR(500)"
    )
    op.execute(
        "ALTER TABLE catalog_demand_signals "
        "ADD COLUMN IF NOT EXISTS normalized_isbn VARCHAR(20)"
    )
    op.execute(
        "ALTER TABLE catalog_demand_signals "
        "ADD COLUMN IF NOT EXISTS normalized_subject VARCHAR(255)"
    )
    op.execute(
        "ALTER TABLE catalog_demand_signals "
        "ADD COLUMN IF NOT EXISTS query_text TEXT"
    )
    op.execute(
        "ALTER TABLE catalog_demand_signals "
        "ADD COLUMN IF NOT EXISTS patron_id INTEGER"
    )
    op.execute(
        "ALTER TABLE catalog_demand_signals "
        "ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ"
    )
    op.execute(
        "ALTER TABLE catalog_demand_signals "
        "ADD COLUMN IF NOT EXISTS resolution demand_signal_resolution"
    )
    op.execute(
        "ALTER TABLE catalog_demand_signals "
        "ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb"
    )

    # -----------------------------------------------------------------
    # 3. Indexes
    # -----------------------------------------------------------------
    # Primary report query: aggregate by signal_type ordered by
    # recorded_at desc for trailing-window analytics.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_demand_signals_type_recorded "
        "ON catalog_demand_signals (signal_type, recorded_at DESC)"
    )
    # Partial index on isbn -- only signals with an ISBN are
    # deduplicatable for the selection-assistant report.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_demand_signals_isbn "
        "ON catalog_demand_signals (normalized_isbn) "
        "WHERE normalized_isbn IS NOT NULL"
    )
    # Partial index on patron_id -- supports patron-history queries
    # (and is sparse since failed-search signals from anonymous
    # visitors have patron_id NULL).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_demand_signals_patron "
        "ON catalog_demand_signals (patron_id) "
        "WHERE patron_id IS NOT NULL"
    )


def downgrade() -> None:
    # Reverse order, idempotent guards.
    op.execute("DROP INDEX IF EXISTS ix_demand_signals_patron")
    op.execute("DROP INDEX IF EXISTS ix_demand_signals_isbn")
    op.execute("DROP INDEX IF EXISTS ix_demand_signals_type_recorded")
    op.execute("DROP TABLE IF EXISTS catalog_demand_signals")
    op.execute("DROP TYPE IF EXISTS demand_signal_resolution")
    op.execute("DROP TYPE IF EXISTS demand_signal_type")
