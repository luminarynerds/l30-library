# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Front desk state endpoint -- live operational stats for the desk."""
from app.core.logging import get_logger
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....models.circulation import Hold
from ..dependencies import require_staff

router = APIRouter(prefix="/staff/desk", tags=["staff-desk"])
logger = get_logger(__name__)


class DeskStateResponse(BaseModel):
    holds_to_pull: int = 0
    holds_expiring_today: int = 0
    book_drop_estimate: int = 0
    book_drop_last_cleared: str | None = None
    holds_shelf_count: int = 0
    holds_expiring_tonight: int = 0
    cash_drawer_open: bool = False
    cash_drawer_total: float = 0.0


@router.get("/state", response_model=DeskStateResponse)
async def get_desk_state(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return live front desk operational stats."""
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    today_end = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)

    try:
        holds_to_pull_q = await db.execute(
            select(func.count(Hold.id)).where(Hold.status == "pending")
        )
        holds_to_pull = holds_to_pull_q.scalar() or 0

        holds_expiring_q = await db.execute(
            select(func.count(Hold.id)).where(
                and_(
                    Hold.status.in_(["pending", "ready"]),
                    Hold.expires_at >= today_start,
                    Hold.expires_at <= today_end,
                )
            )
        )
        holds_expiring_today = holds_expiring_q.scalar() or 0

        holds_shelf_q = await db.execute(
            select(func.count(Hold.id)).where(Hold.status == "ready")
        )
        holds_shelf_count = holds_shelf_q.scalar() or 0

        holds_expiring_tonight_q = await db.execute(
            select(func.count(Hold.id)).where(
                and_(
                    Hold.status == "ready",
                    Hold.expires_at >= today_start,
                    Hold.expires_at <= today_end,
                )
            )
        )
        holds_expiring_tonight = holds_expiring_tonight_q.scalar() or 0

        return DeskStateResponse(
            holds_to_pull=holds_to_pull,
            holds_expiring_today=holds_expiring_today,
            holds_shelf_count=holds_shelf_count,
            holds_expiring_tonight=holds_expiring_tonight,
        )
    except Exception:
        logger.exception("Failed to fetch desk state")
        return DeskStateResponse()
