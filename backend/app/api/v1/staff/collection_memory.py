# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Collection memory annual aggregation endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ..dependencies import require_staff


router = APIRouter(prefix="/staff", tags=["collection_memory"])


@router.get("/collection-memory/annual")
async def collection_memory_annual(
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
):
    """Refresh + return the collection_memory_annual aggregate.

    The materialized view is refreshed on every request so the response always
    reflects current rationale state. View size is bounded by the number of
    distinct (year, use_case, weeding_condition) triples, which is small.
    """
    await db.execute(text("REFRESH MATERIALIZED VIEW collection_memory_annual"))
    result = await db.execute(text(
        "SELECT year_acquired, primary_use_case_slug, weeding_condition, "
        "       item_count, anticipated_count, patron_visible_count "
        "FROM collection_memory_annual "
        "ORDER BY year_acquired DESC, item_count DESC"
    ))
    rows = [
        {
            "year_acquired": r.year_acquired.isoformat() if r.year_acquired else None,
            "primary_use_case_slug": r.primary_use_case_slug,
            "weeding_condition": r.weeding_condition,
            "item_count": r.item_count,
            "anticipated_count": r.anticipated_count,
            "patron_visible_count": r.patron_visible_count,
        }
        for r in result.all()
    ]
    return {"rows": rows}
