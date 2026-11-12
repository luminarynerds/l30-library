# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff presence/status tracking -- who is available, on break, needs help."""
from app.core.logging import get_logger
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....models.staff_presence import PresenceStatus, StaffPresence
from ....models.user import User
from ..dependencies import require_staff
from ....services.time_entry_service import LIBRARY_TZ, record_transition

router = APIRouter(prefix="/staff/presence", tags=["staff-presence"])
logger = get_logger(__name__)


class PresenceResponse(BaseModel):
    status: str
    status_changed_at: str | None = None
    shift_started_at: str | None = None
    break_started_at: str | None = None


class PresenceUpdateRequest(BaseModel):
    status: str


class OnDutyStaffResponse(BaseModel):
    staff_id: int
    staff_name: str
    status: str
    status_changed_at: str | None = None


def _presence_to_response(p: StaffPresence) -> PresenceResponse:
    return PresenceResponse(
        status=p.status.value if isinstance(p.status, PresenceStatus) else p.status,
        status_changed_at=p.status_changed_at.isoformat() if p.status_changed_at else None,
        shift_started_at=p.shift_started_at.isoformat() if p.shift_started_at else None,
        break_started_at=p.break_started_at.isoformat() if p.break_started_at else None,
    )


@router.get("/me", response_model=PresenceResponse)
async def get_my_presence(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's presence status."""
    try:
        result = await db.execute(
            select(StaffPresence).where(StaffPresence.staff_id == staff_user.id)
        )
        presence = result.scalar_one_or_none()

        if presence is None:
            # A read must not create state. Someone who has not clocked in is
            # off_duty; a real clock-in happens via PUT /status, which writes
            # the CLOCK_IN time entry. (Previously this persisted a phantom
            # AVAILABLE row, making the button show "clocked in" with no time
            # and listing the user as present on the desk schedule.)
            return PresenceResponse(status=PresenceStatus.OFF_DUTY.value)

        return _presence_to_response(presence)
    except Exception:
        # Only the row-missing case above is a legitimate off_duty; a database
        # fault must surface as a 500, not read as "not clocked in".
        logger.exception("Failed to fetch presence for user %s", staff_user.id)
        raise


@router.put("/status", response_model=PresenceResponse)
async def update_my_status(
    payload: PresenceUpdateRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update own presence status."""
    try:
        new_status = PresenceStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid status: {payload.status}") from None

    now = datetime.now(timezone.utc)

    try:
        result = await db.execute(
            select(StaffPresence).where(StaffPresence.staff_id == staff_user.id)
        )
        presence = result.scalar_one_or_none()

        old_status = None
        if presence is None:
            presence = StaffPresence(
                staff_id=staff_user.id,
                status=new_status,
                status_changed_at=now,
            )
            db.add(presence)
        else:
            old_status = presence.status.value if isinstance(presence.status, PresenceStatus) else presence.status
            presence.status = new_status
            presence.status_changed_at = now

        # Transition logic
        if new_status == PresenceStatus.ON_BREAK:
            presence.break_started_at = now
        elif new_status == PresenceStatus.AVAILABLE:
            presence.break_started_at = None
            if presence.shift_started_at is None:
                presence.shift_started_at = now
        elif new_status == PresenceStatus.OFF_DUTY:
            presence.shift_ended_at = now
            presence.break_started_at = None


        await db.flush()

        # Record time entry for timesheet tracking. Clock in/out must not fail
        # silently — a dropped punch becomes an unpaid/under-paid shift.
        await record_transition(db, staff_user.id, old_status, payload.status, now)
        await db.flush()

        return _presence_to_response(presence)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update presence for user %s", staff_user.id)
        raise HTTPException(status_code=500, detail="Couldn't update shift status") from None


@router.get("/on-duty", response_model=list[OnDutyStaffResponse])
async def get_on_duty_staff(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all staff currently not off_duty."""
    try:
        # Presence rows persist across days. One left non-off_duty by a missed
        # clock-out would otherwise keep its owner on this list forever, so
        # rows last touched before the current local day read as off duty
        # (the nightly sweeper resets the rows themselves).
        local_today = datetime.now(timezone.utc).astimezone(LIBRARY_TZ).date()
        day_start = datetime.combine(local_today, time.min, tzinfo=LIBRARY_TZ).astimezone(timezone.utc)
        result = await db.execute(
            select(StaffPresence)
            .options(selectinload(StaffPresence.staff))
            .where(
                StaffPresence.status != PresenceStatus.OFF_DUTY,
                StaffPresence.status_changed_at >= day_start,
            )
            .order_by(StaffPresence.status_changed_at.desc())
        )
        rows = result.scalars().all()

        return [
            OnDutyStaffResponse(
                staff_id=p.staff_id,
                staff_name=p.staff.first_name if p.staff else "Unknown",
                status=p.status.value if isinstance(p.status, PresenceStatus) else p.status,
                status_changed_at=p.status_changed_at.isoformat() if p.status_changed_at else None,
            )
            for p in rows
        ]
    except Exception:
        logger.exception("Failed to fetch on-duty staff")
        raise
