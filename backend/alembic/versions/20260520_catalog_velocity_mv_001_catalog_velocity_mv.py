# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""catalog_circulation_velocity_mv -- weed / buy-more / cold-spend report MV

Revision ID: catalog_velocity_mv_001
Revises: catalog_demand_signals_001
Create Date: 2026-05-20 12:00:00.000000+00:00

Adds a materialized view summarizing circulation velocity per catalog
item: trailing 30/90/365-day checkout counts, days since last
checkout, active hold pressure (raw + per-copy), and a non-withdrawn
copy count. Refreshed nightly via apscheduler
(``services.schedulers.catalog_velocity_jobs.refresh_catalog_velocity_mv``)
using ``REFRESH MATERIALIZED VIEW CONCURRENTLY`` -- requires the
unique index on ``catalog_item_id`` created below.

Each metric is computed via a scalar subquery (no cross-join
multiplicity) so adding more metrics later is mechanical. Counts
use ``checkouts.checked_out_at`` (the canonical L30 column) and
``item_copies.condition`` lowercase string values (see
``feedback_l30_enum_case``).

Idempotent: ``CREATE MATERIALIZED VIEW IF NOT EXISTS`` + guarded
unique index. Safe to run after init_db.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "catalog_velocity_mv_001"
down_revision: Union[str, None] = "catalog_demand_signals_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # 1. Materialized view
    # -----------------------------------------------------------------
    # All metrics are scalar correlated subqueries per catalog item to
    # avoid the row-multiplication that would occur if checkouts,
    # holds, and item_copies were joined directly. ``total_copies``
    # excludes withdrawn/damaged copies -- those should not be counted
    # as "available collection inventory" for holds-per-copy pressure.
    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS catalog_circulation_velocity_mv AS
        SELECT
            ci.id AS catalog_item_id,
            (
                SELECT COUNT(*)
                FROM checkouts c
                WHERE c.item_id = ci.id
                  AND c.checked_out_at >= NOW() - INTERVAL '30 days'
            ) AS checkouts_30d,
            (
                SELECT COUNT(*)
                FROM checkouts c
                WHERE c.item_id = ci.id
                  AND c.checked_out_at >= NOW() - INTERVAL '90 days'
            ) AS checkouts_90d,
            (
                SELECT COUNT(*)
                FROM checkouts c
                WHERE c.item_id = ci.id
                  AND c.checked_out_at >= NOW() - INTERVAL '365 days'
            ) AS checkouts_365d,
            (
                SELECT EXTRACT(EPOCH FROM (NOW() - MAX(c.checked_out_at))) / 86400.0
                FROM checkouts c
                WHERE c.item_id = ci.id
            ) AS days_since_last_checkout,
            (
                SELECT COUNT(*)
                FROM holds h
                WHERE h.item_id = ci.id
                  AND h.status IN ('pending', 'ready')
            ) AS holds_active,
            (
                SELECT COUNT(*)
                FROM item_copies ic
                WHERE ic.catalog_item_id = ci.id
                  AND ic.condition NOT IN ('withdrawn', 'damaged')
            ) AS total_copies,
            (
                SELECT COUNT(*)
                FROM holds h
                WHERE h.item_id = ci.id
                  AND h.status IN ('pending', 'ready')
            )::numeric
            / NULLIF((
                SELECT COUNT(*)
                FROM item_copies ic
                WHERE ic.catalog_item_id = ci.id
                  AND ic.condition NOT IN ('withdrawn', 'damaged')
            ), 0) AS holds_per_copy,
            NOW() AS last_refreshed_at
        FROM catalog_items ci
        """
    )

    # -----------------------------------------------------------------
    # 2. Unique index (REQUIRED for REFRESH MATERIALIZED VIEW CONCURRENTLY)
    # -----------------------------------------------------------------
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_catalog_velocity_mv_item "
        "ON catalog_circulation_velocity_mv (catalog_item_id)"
    )

    # Supporting indexes for the three bucket queries.
    # ``weed`` filters by checkouts_365d=0 AND holds_active=0 AND
    # days_since_last_checkout>365 AND total_copies>=2 -- a partial
    # index on the cold subset is the highest-leverage shape.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_catalog_velocity_mv_weed "
        "ON catalog_circulation_velocity_mv (days_since_last_checkout DESC) "
        "WHERE checkouts_365d = 0 AND holds_active = 0 AND total_copies >= 2"
    )
    # ``buy_more`` filters by holds_per_copy DESC.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_catalog_velocity_mv_buy "
        "ON catalog_circulation_velocity_mv (holds_per_copy DESC) "
        "WHERE holds_active > 0"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_catalog_velocity_mv_buy")
    op.execute("DROP INDEX IF EXISTS idx_catalog_velocity_mv_weed")
    op.execute("DROP INDEX IF EXISTS idx_catalog_velocity_mv_item")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS catalog_circulation_velocity_mv")
