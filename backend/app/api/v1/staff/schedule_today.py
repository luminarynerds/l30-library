# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Today's schedule endpoint -- programs and events relevant to the front desk."""
from app.core.logging import get_logger
from datetime import date
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....models.program import Program
from ..dependencies import require_staff

router = APIRouter(prefix="/staff/schedule", tags=["staff-schedule"])
logger = get_logger(__name__)


class ScheduleItem(BaseModel):
    id: int
    time: str
    title: str
    location: str | None = None
    desk_note: str | None = None
    relative_time: str | None = None


class TodayScheduleResponse(BaseModel):
    items: List[ScheduleItem] = []


@router.get("/today", response_model=TodayScheduleResponse)
async def get_today_schedule(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return today's programs/events with desk-relevant context."""
    today = date.today()

    try:
        result = await db.execute(
            select(Program)
            .where(Program.program_date == today)
            .where(Program.status.in_(["planned", "scheduled", "in_progress"]))
            .order_by(Program.start_time)
        )
        programs = result.scalars().all()

        items = []
        for p in programs:
            time_fmt = "%I:%M %p"
            time_str = p.start_time.strftime(time_fmt).lstrip("0")
            if p.end_time:
                end_str = p.end_time.strftime(time_fmt).lstrip("0")
                time_str += f" - {end_str}"
            items.append(ScheduleItem(
                id=p.id,
                time=time_str,
                title=p.title,
                location=p.location_name,
                desk_note=p.notes,
            ))

        return TodayScheduleResponse(items=items)
    except Exception:
        logger.exception("Failed to fetch today schedule")
        return TodayScheduleResponse()
