# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shelver / page dashboard endpoint -- shift info and task suggestions."""
from app.core.logging import get_logger
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....models.circulation import Hold
from ....models.staff_schedule_fairness import StaffShift
from ..dependencies import require_staff

router = APIRouter(prefix="/staff/shelver", tags=["staff-shelver"])
logger = get_logger(__name__)


class ShiftInfo(BaseModel):
    shift_date: date
    scheduled_start: str
    scheduled_end: str
    scheduled_hours: float
    status: str


class ShelverTask(BaseModel):
    id: str
    label: str
    detail: str | None = None
    count: int | None = None


class ShelverDashboardResponse(BaseModel):
    shift: ShiftInfo | None = None
    holds_to_pull: int = 0
    tasks: list[ShelverTask] = []


@router.get("/dashboard", response_model=ShelverDashboardResponse)
async def get_shelver_dashboard(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return shift info and task suggestions for the current shelver/page."""
    today = date.today()

    try:
        # Current shift
        shift_q = await db.execute(
            select(StaffShift).where(
                StaffShift.staff_id == staff_user.id,
                StaffShift.shift_date == today,
            ).limit(1)
        )
        shift_row = shift_q.scalar_one_or_none()
        shift = None
        if shift_row:
            shift = ShiftInfo(
                shift_date=shift_row.shift_date,
                scheduled_start=shift_row.scheduled_start.strftime("%H:%M"),
                scheduled_end=shift_row.scheduled_end.strftime("%H:%M"),
                scheduled_hours=shift_row.scheduled_hours,
                status=shift_row.status.value if hasattr(shift_row.status, "value") else str(shift_row.status),
            )

        # Pending holds count
        holds_q = await db.execute(
            select(func.count(Hold.id)).where(Hold.status == "pending")
        )
        holds_to_pull = holds_q.scalar() or 0

        # Build task list
        tasks: list[ShelverTask] = []
        if holds_to_pull > 0:
            tasks.append(ShelverTask(
                id="pull_holds",
                label="Pull holds",
                count=holds_to_pull,
            ))
        tasks.append(ShelverTask(
            id="shelve_returns",
            label="Shelve return carts",
            detail="Check carts in sorting area",
        ))
        tasks.append(ShelverTask(
            id="shelf_read",
            label="Shelf-read assigned section",
            detail="Verify items are in correct order",
        ))

        return ShelverDashboardResponse(
            shift=shift,
            holds_to_pull=holds_to_pull,
            tasks=tasks,
        )
    except Exception:
        logger.exception("Failed to fetch shelver dashboard")
        return ShelverDashboardResponse()
