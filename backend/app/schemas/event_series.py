# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime

from pydantic import BaseModel, Field

from .event import PresenterEntry
from .event_registration import RegistrationCreate


class SeriesOccurrence(BaseModel):

    event_id: int
    start_time: datetime
    end_time: datetime | None = None
    location: str | None = None
    is_published: bool
    max_attendees: int | None = None
    spots_remaining: int | None = None
    registration_required: bool = False


class SeriesDetailResponse(BaseModel):

    series_id: str
    series_name: str
    description: str | None = None
    category: str | None = None
    audience: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    presenters: list[PresenterEntry] | None = None
    recurrence_summary: str | None = Field(
        None,
        description="Human summary of recurrence, e.g. 'Meets weekly through Aug 31'.",
    )
    upcoming_count: int
    occurrences: list[SeriesOccurrence]


class SeriesRegistrationCreate(RegistrationCreate):

    pass


class SeriesRegistrationOutcome(BaseModel):

    event_id: int
    start_time: datetime
    status: str = Field(
        ...,
        description="One of: registered, already_registered, waitlisted, capacity_full, error",
    )
    registration_id: int | None = None
    waitlist_position: int | None = None
    error: str | None = None


class SeriesRegistrationResponse(BaseModel):

    series_id: str
    series_name: str
    total_upcoming: int
    registered_count: int
    already_registered_count: int
    waitlisted_count: int
    failed_count: int
    outcomes: list[SeriesRegistrationOutcome]
