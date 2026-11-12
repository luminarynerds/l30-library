# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr

from ._base import StrictInputSchema


class RegistrationCreate(StrictInputSchema):
    patron_name: str = Field(..., min_length=1, max_length=255, description="Patron's full name")
    patron_email: EmailStr | None = Field(
        None,
        description="Patron's email address. Optional when a phone number is given.",
    )
    patron_phone: str | None = Field(None, max_length=20, description="Patron's phone number")
    reminder_requested: bool = Field(False, description="Whether patron requested event reminders")
    accommodation_requested: bool = Field(
        False, description="Whether patron is requesting an accessibility accommodation"
    )
    accommodation_details: str | None = Field(
        None,
        max_length=2000,
        description="Patron-supplied free-text describing the accommodation needed",
    )
    # Three-valued photo release: None means "event did not ask" (i.e.
    # event.photos_will_be_taken was False); True/False are explicit answers.
    photo_release_granted: bool | None = Field(
        None,
        description="Whether patron consents to being photographed at this event. None when not asked.",
    )
    turnstile_token: str | None = Field(
        None, description="Cloudflare Turnstile token from the public registration form"
    )

    @field_validator("patron_phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Remove common formatting characters
        cleaned = "".join(c for c in v if c.isdigit() or c in "+-() ")
        if cleaned and len(cleaned.replace(" ", "").replace("-", "").replace("+", "").replace("(", "").replace(")", "")) < 7:
            raise ValueError("Phone number must have at least 7 digits")
        return v

    @model_validator(mode="after")
    def require_email_or_phone(self) -> "RegistrationCreate":
        # Patrons without email may register phone-only; we just need one
        # way to reach them.
        if not self.patron_email and not self.patron_phone:
            raise ValueError("Provide an email address or a phone number")
        return self


class RegistrationResponse(BaseModel):
    id: int
    event_id: int
    patron_name: str
    patron_email: str | None = None
    patron_phone: str | None
    registered_at: datetime
    status: str
    reminder_requested: bool = False
    reminder_sent_at: datetime | None = None
    accommodation_requested: bool = False
    accommodation_details: str | None = None
    accommodation_acknowledged_at: datetime | None = None
    accommodation_acknowledged_by: int | None = None
    photo_release_granted: bool | None = None
    waitlist_position: int | None = None  # Position on waitlist (1-based), None if confirmed

    class Config:
        from_attributes = True


class MyEventRegistrationResponse(BaseModel):
    id: int
    event_id: int
    status: str
    registered_at: datetime
    reminder_requested: bool = False
    reminder_sent_at: datetime | None = None
    accommodation_requested: bool = False
    accommodation_details: str | None = None
    accommodation_acknowledged_at: datetime | None = None
    accommodation_acknowledged_by: int | None = None
    event_title: str
    event_start_time: datetime
    event_end_time: datetime | None = None
    event_location: str | None = None
    event_category: str | None = None

    class Config:
        from_attributes = True


class RegistrationListResponse(BaseModel):
    registrations: list[RegistrationResponse]
    total: int
    waitlist_count: int = 0
    spots_remaining: int | None
