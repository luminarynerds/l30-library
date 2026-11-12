# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from ._base import StrictInputSchema


class WaitlistJoinRequest(StrictInputSchema):
    email: EmailStr = Field(..., description="Patron's email address")
    name: str | None = Field(None, max_length=255, description="Patron's name (optional)")
    registrant_count: int = Field(
        1, ge=1, le=20, description="Number of seats requested (incl. patron)"
    )
    notes: str | None = Field(
        None, max_length=2000, description="Optional free-text notes for staff"
    )
    turnstile_token: str | None = Field(
        None, description="Cloudflare Turnstile token from the public waitlist form"
    )


class WaitlistJoinResponse(BaseModel):
    id: int
    event_id: int
    email: str
    position: int = Field(..., description="1-indexed position in the active waitlist queue")
    status: str
    created_at: datetime
    cancel_token: str = Field(
        ..., description="Token the patron can later use to remove themselves from this waitlist"
    )


class WaitlistPositionResponse(BaseModel):
    event_id: int
    email: str
    position: int
    status: str
