# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class IntelligentScheduleRequest(StrictInputSchema):
    room_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    turnover_minutes: int = Field(default=15, ge=0, le=120)

    volunteer_id: int | None = None
    shift_window_start: date | None = None
    shift_window_end: date | None = None

    event_category: str | None = None
    lookback_days: int = Field(default=365, ge=30, le=1095)

    source_year: int | None = None
    target_year: int | None = None
    series_name: str | None = None

    volunteer_match_date: date | None = None
    volunteer_match_start: time | None = None
    volunteer_match_end: time | None = None

    equipment_ids: list[int] = []
    equipment_start_date: date | None = None
    equipment_end_date: date | None = None

    participant_ids: list[int] = []
    find_time_start: datetime | None = None
    find_time_end: datetime | None = None
    meeting_duration_minutes: int = Field(default=60, ge=15, le=480)

    calendar_title: str | None = None
    calendar_details: str | None = None
    calendar_location: str | None = None


class IntelligentScheduleResponse(BaseModel):
    room_conflicts: list[dict] = []
    staff_shift_gaps: list[dict] = []
    event_suggestions: list[dict] = []
    repeat_program_suggestions: list[dict] = []
    volunteer_matches: list[dict] = []
    equipment_availability: list[dict] = []
    find_time_suggestions: list[dict] = []
    calendar_sync: dict | None = None
    notes: list[str] = []
