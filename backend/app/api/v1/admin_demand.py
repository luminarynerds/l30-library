# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Admin demand-signals report endpoint.

Surfaces aggregated demand evidence (failed searches, ILL, peak holds,
agent-unfound) for staff/admin consumption. PR7 ships only the
failed-search ingest hook -- this endpoint is the report-side
foundation that future PRs (ILL hook, hold pressure, agent unfound)
will plug into without further frontend changes.
"""

from __future__ import annotations

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...services.demand_signal_service import get_top_demand
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/demand-signals", tags=["admin-demand-signals"])


@router.get("", summary="Top demand signals (collection development)")
async def list_demand_signals(
    days: int = Query(
        30, ge=1, le=365, description="Trailing window in days (default 30)"
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Max rows to return (default 50)"
    ),
    signal_type: Optional[str] = Query(
        None,
        description=(
            "Filter to a single signal type: failed_search, ill_request, "
            "peak_hold_depth, agent_unfound"
        ),
    ),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return ranked demand signals for the staff selection-assistant view.

    Aggregation logic lives in
    ``app.services.demand_signal_service.get_top_demand``. Rows are
    ordered by recency-weighted count desc.
    """
    items = await get_top_demand(
        db, days=days, limit=limit, signal_type=signal_type
    )
    return {
        "days": days,
        "limit": limit,
        "signal_type": signal_type,
        "items": items,
    }
