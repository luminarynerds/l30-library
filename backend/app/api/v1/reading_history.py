# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron reading history API — provides access to checkout/reading history."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...models.circulation import Checkout
from .auth import get_current_user

router = APIRouter(prefix="/reading", tags=["reading-history"])


@router.get("/history")
async def get_reading_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's reading/checkout history."""
    query = (
        select(Checkout)
        .where(Checkout.user_id == current_user.id)
        .order_by(desc(Checkout.checked_out_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    checkouts = result.scalars().all()

    count_result = await db.execute(
        select(func.count(Checkout.id)).where(Checkout.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    return {
        "items": [
            {
                "id": c.id,
                "catalog_item_id": c.catalog_item_id,
                "checked_out_at": c.checked_out_at.isoformat() if c.checked_out_at else None,
                "due_date": c.due_date.isoformat() if c.due_date else None,
                "returned_at": c.returned_at.isoformat() if c.returned_at else None,
                "status": c.status if isinstance(c.status, str) else c.status.value,
            }
            for c in checkouts
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
