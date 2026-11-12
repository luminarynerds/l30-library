# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Admin collection-velocity report endpoint.

Reads the ``catalog_circulation_velocity_mv`` materialized view
(alembic ``catalog_velocity_mv_001``) and surfaces three actionable
buckets for staff collection-development:

* ``weed``        -- candidates for withdrawal (no recent demand)
* ``buy_more``    -- copies are starved by active hold pressure
* ``cold_spend``  -- recently acquired but zero circulation (bad buys)

The MV is refreshed nightly. Reads are bounded by ``limit`` (default
50, max 200) and join the MV to ``catalog_items`` for human-readable
title / author / ISBN display.
"""

from __future__ import annotations

from app.core.logging import get_logger
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin/reports", tags=["admin-collection-velocity"]
)

Bucket = Literal["weed", "buy_more", "cold_spend"]


# WHERE-clause fragments per bucket. All three reference the joined
# ``v`` (MV) and ``ci`` (catalog_items) aliases.
#
# cold_spend uses ci.created_at (TimestampMixin) as the proxy for
# "recently acquired". A purer "acquired_at" doesn't exist on
# CatalogItem; created_at is the closest approximation since the
# catalog row is inserted at cataloging time.
_BUCKET_WHERE: dict[str, str] = {
    "weed": (
        "v.checkouts_365d = 0 "
        "AND v.holds_active = 0 "
        "AND v.days_since_last_checkout > 365 "
        "AND v.total_copies >= 2"
    ),
    "buy_more": (
        "v.holds_per_copy >= 2 "
        "AND v.holds_active > 0"
    ),
    "cold_spend": (
        "ci.created_at >= NOW() - INTERVAL '365 days' "
        "AND v.checkouts_365d = 0"
    ),
}

_BUCKET_ORDER: dict[str, str] = {
    "weed": "v.days_since_last_checkout DESC NULLS LAST",
    "buy_more": "v.holds_per_copy DESC NULLS LAST",
    "cold_spend": "ci.created_at DESC",
}


@router.get(
    "/collection-velocity",
    summary="Collection velocity buckets (weed / buy_more / cold_spend)",
)
async def get_collection_velocity(
    bucket: Bucket = Query(
        ...,
        description="Which actionable bucket to return.",
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Max rows to return (default 50)."
    ),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return top-N items in the requested bucket.

    Reads the nightly-refreshed materialized view; if the MV has not
    yet been refreshed (e.g. immediately post-deploy before the first
    03:30 UTC cron tick), this endpoint will simply return whatever
    rows the MV currently contains -- callers should treat
    ``last_refreshed_at`` as the freshness signal.
    """
    where = _BUCKET_WHERE[bucket]
    order = _BUCKET_ORDER[bucket]
    sql = text(
        f"""
        SELECT
            v.catalog_item_id,
            ci.title,
            ci.author,
            ci.isbn,
            v.checkouts_30d,
            v.checkouts_90d,
            v.checkouts_365d,
            v.days_since_last_checkout,
            v.holds_active,
            v.holds_per_copy,
            v.total_copies,
            v.last_refreshed_at
        FROM catalog_circulation_velocity_mv v
        JOIN catalog_items ci ON ci.id = v.catalog_item_id
        WHERE {where}
        ORDER BY {order}
        LIMIT :limit
        """
    )
    result = await db.execute(sql, {"limit": limit})
    rows = result.mappings().all()
    items = [
        {
            "catalog_item_id": r["catalog_item_id"],
            "title": r["title"],
            "author": r["author"],
            "isbn": r["isbn"],
            "checkouts_30d": int(r["checkouts_30d"] or 0),
            "checkouts_90d": int(r["checkouts_90d"] or 0),
            "checkouts_365d": int(r["checkouts_365d"] or 0),
            "days_since_last_checkout": (
                float(r["days_since_last_checkout"])
                if r["days_since_last_checkout"] is not None
                else None
            ),
            "holds_active": int(r["holds_active"] or 0),
            "holds_per_copy": (
                float(r["holds_per_copy"])
                if r["holds_per_copy"] is not None
                else None
            ),
            "total_copies": int(r["total_copies"] or 0),
            "last_refreshed_at": (
                r["last_refreshed_at"].isoformat()
                if r["last_refreshed_at"]
                else None
            ),
        }
        for r in rows
    ]
    return {
        "bucket": bucket,
        "limit": limit,
        "count": len(items),
        "items": items,
    }
