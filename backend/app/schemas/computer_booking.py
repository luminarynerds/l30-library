# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class StationResponse(BaseModel):
    id: int
    name: str
    computer_number: str
    location: Optional[str] = None
    computer_type: str
    status: str
    is_active: bool
    max_session_minutes: int
    is_extendable: bool
    has_internet: bool
    installed_software: Optional[List[str]] = []
    accessibility_features: Optional[List[str]] = []

    class Config:
        from_attributes = True


class StationListResponse(BaseModel):
    items: List[StationResponse]
    total: int


class AvailabilitySlot(BaseModel):
    start_time: datetime
    end_time: datetime
    is_available: bool


class AvailabilityResponse(BaseModel):
    computer_id: int
    date: str
    slots: List[AvailabilitySlot]


class ComputerAvailability(BaseModel):
    computer_id: int
    name: str
    computer_number: str
    computer_type: str
    max_session_minutes: int
    slots: List[AvailabilitySlot]


class RangeAvailabilityResponse(BaseModel):
    """Identity-free free/busy slots for every bookable computer over a date range."""
    start_date: str
    days: int
    computers: List[ComputerAvailability]


class ReservationCreateRequest(StrictInputSchema):
    computer_id: int
    start_time: datetime
    duration_minutes: int = Field(60, gt=0, le=480)


class ReservationResponse(BaseModel):
    id: int
    computer_id: int
    patron_id: Optional[int] = None
    reserved_start_time: datetime
    reserved_end_time: datetime
    status: str
    session_duration_minutes: int
    checked_in_at: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    extensions_used: int = 0
    extended_until: Optional[datetime] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ReservationListResponse(BaseModel):
    items: List[ReservationResponse]
    total: int


class StaffReservationUpdateRequest(StrictInputSchema):
    """Staff reschedule. Both optional; for an in-session reservation only the
    end is applied (the start already happened). Timestamps must be tz-aware."""
    reserved_start_time: Optional[datetime] = None
    reserved_end_time: Optional[datetime] = None


class StaffExtendRequest(StrictInputSchema):
    extra_minutes: int = Field(..., gt=0, le=480)


class SessionStartRequest(StrictInputSchema):
    computer_id: int
    duration_minutes: int = Field(60, gt=0, le=480)


class SessionExtendRequest(StrictInputSchema):
    extra_minutes: int = Field(30, gt=0, le=120)


class SessionResponse(BaseModel):
    id: int
    computer_id: int
    reserved_start_time: datetime
    reserved_end_time: datetime
    status: str
    actual_start_time: Optional[datetime] = None
    extensions_used: int = 0
    extended_until: Optional[datetime] = None
    minutes_remaining: Optional[int] = None

    class Config:
        from_attributes = True


class WaitlistJoinRequest(StrictInputSchema):
    computer_id: int
    desired_duration_minutes: int = Field(60, gt=0, le=480)


class WaitlistPositionResponse(BaseModel):
    id: int
    computer_id: int
    queue_position: int
    status: str
    created_at: datetime | None = None
    expires_at: datetime

    class Config:
        from_attributes = True
