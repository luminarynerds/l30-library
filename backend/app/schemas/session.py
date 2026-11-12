# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class SessionRSVPResponse(BaseModel):
    id: int
    session_id: int
    user_id: int
    status: str
    responded_at: datetime | None = None

    class Config:
        from_attributes = True


class ModuleSessionCreate(StrictInputSchema):
    module_id: int
    title: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: int
    location: Optional[str] = None
    facilitator_id: Optional[int] = None
    max_participants: Optional[int] = None
    materials: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ModuleSessionUpdate(StrictInputSchema):
    title: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    facilitator_id: Optional[int] = None
    max_participants: Optional[int] = None
    materials: Optional[List[str]] = None
    notes: Optional[str] = None
    is_cancelled: Optional[bool] = None


class ModuleSessionResponse(BaseModel):
    id: int
    module_id: int
    title: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: int
    location: Optional[str] = None
    facilitator_id: Optional[int] = None
    max_participants: Optional[int] = None
    materials: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    is_cancelled: bool = False
    rsvp_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ModuleSessionWithRSVPs(ModuleSessionResponse):
    rsvps: List[SessionRSVPResponse] = []


class RSVPCreate(StrictInputSchema):
    status: str = "attending"
