# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unified intelligent scheduling endpoint for staff workflows."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.intelligent_scheduling import (
    IntelligentScheduleRequest,
    IntelligentScheduleResponse,
)
from ...services.intelligent_scheduling_service import (
    DateTimeWindow,
    IntelligentSchedulingService,
)
from .dependencies import require_staff

router = APIRouter(prefix="/scheduling", tags=["intelligent-scheduling"])


@router.post("/intelligent", response_model=IntelligentScheduleResponse)
async def intelligent_schedule(
    payload: IntelligentScheduleRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Run cross-domain scheduling analysis and return concrete suggestions."""
    response = IntelligentScheduleResponse()

    if payload.room_id and payload.start_time and payload.end_time:
        response.room_conflicts = await IntelligentSchedulingService.room_conflicts(
            db=db,
            room_id=payload.room_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            turnover_minutes=payload.turnover_minutes,
        )

    if payload.volunteer_id and payload.shift_window_start and payload.shift_window_end:
        response.staff_shift_gaps = await IntelligentSchedulingService.volunteer_shift_gaps(
            db=db,
            volunteer_id=payload.volunteer_id,
            start_date=payload.shift_window_start,
            end_date=payload.shift_window_end,
        )

    response.event_suggestions = await IntelligentSchedulingService.event_suggestions(
        db=db,
        category=payload.event_category,
        lookback_days=payload.lookback_days,
    )

    if payload.source_year and payload.target_year:
        response.repeat_program_suggestions = await IntelligentSchedulingService.repeat_program_schedule(
            db=db,
            source_year=payload.source_year,
            target_year=payload.target_year,
            series_name=payload.series_name,
        )

    if payload.volunteer_match_date and payload.volunteer_match_start and payload.volunteer_match_end:
        response.volunteer_matches = await IntelligentSchedulingService.volunteer_shift_matching(
            db=db,
            requested_date=payload.volunteer_match_date,
            start_time=payload.volunteer_match_start,
            end_time=payload.volunteer_match_end,
        )

    if payload.equipment_ids and payload.equipment_start_date and payload.equipment_end_date:
        response.equipment_availability = await IntelligentSchedulingService.equipment_availability(
            db=db,
            equipment_ids=payload.equipment_ids,
            start_date=payload.equipment_start_date,
            end_date=payload.equipment_end_date,
        )

    if payload.participant_ids and payload.find_time_start and payload.find_time_end:
        response.find_time_suggestions = await IntelligentSchedulingService.find_time(
            db=db,
            participant_ids=payload.participant_ids,
            date_window=DateTimeWindow(start=payload.find_time_start, end=payload.find_time_end),
            duration_minutes=payload.meeting_duration_minutes,
        )

    if payload.calendar_title and payload.start_time and payload.end_time:
        response.calendar_sync = IntelligentSchedulingService.calendar_sync_links(
            title=payload.calendar_title,
            start_time=payload.start_time,
            end_time=payload.end_time,
            details=payload.calendar_details,
            location=payload.calendar_location,
        )

    response.notes.append("Turnover buffer is automatically included in room conflict detection.")
    response.notes.append("Google/Outlook sync provided as deep-link compose URLs.")
    response.notes.append(f"Generated for staff user ID {staff_user.id}.")

    return response
