# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# ──────────────────────────────────────────────────────────────────────────────
# Validation-Sync Report
# Frontend files that consume this schema's constraints:
#   - frontend/src/components/EventForm.tsx  (title min_length/maxLength, description maxLength, location maxLength, max_attendees min, min_age/max_age 0..120, recurrence_rule, lighting/noise_level/crowd_size vocab)
# ──────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import (
    BaseModel,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from ._base import StrictInputSchema


def ensure_timezone_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# Structured sensory descriptors. Staff pick
# from a fixed lowercase vocabulary so the values stay filterable and render
# consistently for sensory-sensitive patrons. NULL / "" means "not specified".
LIGHTING_VALUES = frozenset({"dim", "moderate", "bright"})
NOISE_LEVEL_VALUES = frozenset({"quiet", "moderate", "lively"})
CROWD_SIZE_VALUES = frozenset({"small", "medium", "large"})
_SENSORY_VOCAB: dict[str, frozenset[str]] = {
    "lighting": LIGHTING_VALUES,
    "noise_level": NOISE_LEVEL_VALUES,
    "crowd_size": CROWD_SIZE_VALUES,
}


def normalize_sensory_value(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    allowed = _SENSORY_VOCAB[field_name]
    if cleaned not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)}")
    return cleaned


class PresenterEntry(BaseModel):

    name: str = Field(..., min_length=1, max_length=255)
    bio: Optional[str] = Field(None, max_length=2000)
    fee: Optional[str] = Field(None, max_length=100)
    program_partner_id: Optional[int] = None


class EventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    start_time: datetime
    end_time: datetime | None = None
    location: str | None = Field(None, max_length=500)
    is_virtual: bool | None = False
    virtual_link: str | None = Field(None, max_length=2048)
    audience: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=100)
    event_language: str | None = Field(
        None,
        max_length=20,
        description="ISO 639-1 code of the language the program is conducted in (e.g. 'es'); null = unspecified",
    )
    tags: list[str] | None = Field(None, description="Tags for granular filtering")
    max_attendees: int | None = Field(None, gt=0)
    registration_required: bool = False
    image_url: str | None = Field(None, max_length=2048)
    is_featured: Optional[bool] = Field(default=False, description="Whether the event is featured")
    series_id: str | None = Field(None, max_length=100)
    series_name: str | None = Field(None, max_length=255)
    branch_id: int | None = Field(None, description="Branch hosting this event")

    # Accessibility flags surfaced on the public event detail page so patrons
    # can see what accommodations are already provided without needing to ask.
    wheelchair_accessible: bool = Field(default=False)
    asl_provided: bool = Field(default=False)
    captioning_provided: bool = Field(default=False)
    assistive_listening: bool = Field(default=False)
    sensory_friendly: bool = Field(default=False)
    large_print_available: bool = Field(default=False)
    accessibility_notes: str | None = Field(
        None, max_length=2000, description="Free-text per-event accessibility statement"
    )

    # Structured sensory descriptors — let sensory-sensitive patrons pre-assess
    # an event. Validated against a fixed lowercase vocabulary on the input
    # schemas (EventCreate / EventUpdate / EventBulkCreateRequest); EventResponse
    # inherits the fields but no validator, so a historical bad row stays lenient.
    lighting: str | None = Field(
        None, description="Lighting level: dim | moderate | bright"
    )
    noise_level: str | None = Field(
        None, description="Noise level: quiet | moderate | lively"
    )
    crowd_size: str | None = Field(
        None, description="Expected crowd size: small | medium | large"
    )
    quiet_space_available: bool = Field(
        default=False,
        description="If true, a quiet / low-stimulation space is available during the event.",
    )

    # ------------------------------------------------------------------
    # Recurrence, presenters, partner orgs, photo release, age range
    # ------------------------------------------------------------------
    recurrence_rule: Optional[str] = Field(
        None,
        max_length=2000,
        description="RFC 5545 RRULE string (FREQ=WEEKLY;BYDAY=TU;UNTIL=...). Empty for one-time events.",
    )
    parent_event_id: Optional[int] = Field(
        None,
        description="If this event is an override instance, the FK to its parent recurring series.",
    )
    presenters: Optional[List[PresenterEntry]] = Field(
        None,
        description="Inline list of presenters; program_partner_id optional per presenter.",
    )
    program_partner_id: Optional[int] = Field(
        None, description="Primary program partner hosting/co-hosting this event."
    )
    photos_will_be_taken: bool = Field(
        default=False,
        description="If true, registration form asks patrons to consent to being photographed.",
    )
    min_age: Optional[int] = Field(
        None, ge=0, le=120, description="Inclusive lower age bound (years)."
    )
    max_age: Optional[int] = Field(
        None, ge=0, le=120, description="Inclusive upper age bound (years)."
    )
    caregiver_required: bool = Field(
        default=False,
        description="If true, attending patrons must be accompanied by a caregiver.",
    )

    @field_validator("start_time", mode="after")
    @classmethod
    def validate_start_time_tz(cls, v: datetime) -> datetime:
        return ensure_timezone_aware(v)

    @field_validator("end_time", mode="after")
    @classmethod
    def validate_end_time_tz(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        return ensure_timezone_aware(v)

    @model_validator(mode="after")
    def validate_times(self) -> "EventBase":
        if self.end_time is not None and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")

        # NOTE: is_virtual/virtual_link consistency is enforced on input
        # schemas (EventCreate, EventUpdate, EventBulkCreateRequest) only.
        # EventResponse inherits from EventBase and must stay lenient so a
        # single historical bad row does not 500 the entire list endpoint.

        if bool(self.series_id) != bool(self.series_name):
            raise ValueError("series_id and series_name must be provided together")

        return self

    @model_validator(mode="after")
    def validate_age_range(self) -> "EventBase":
        # Mirrors the DB CHECK constraint so users get a 422 not a 500.
        if (
            self.min_age is not None
            and self.max_age is not None
            and self.min_age > self.max_age
        ):
            raise ValueError("min_age must be <= max_age")
        return self


class EventCreate(StrictInputSchema, EventBase):
    @field_validator("lighting", "noise_level", "crowd_size", mode="after")
    @classmethod
    def validate_sensory_vocab(cls, v: str | None, info: ValidationInfo) -> str | None:
        return normalize_sensory_value(v, info.field_name)

    @model_validator(mode="after")
    def validate_virtual_link(self) -> "EventCreate":
        if self.is_virtual and not self.virtual_link:
            raise ValueError("virtual_link is required when is_virtual is true")
        return self


class EventUpdate(StrictInputSchema):

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str | None = Field(None, max_length=500)
    is_virtual: bool | None = None
    virtual_link: str | None = Field(None, max_length=2048)
    audience: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=100)
    event_language: str | None = Field(
        None,
        max_length=20,
        description="ISO 639-1 code of the language the program is conducted in (e.g. 'es'); null = unspecified",
    )
    tags: list[str] | None = Field(None, description="Tags for granular filtering")
    max_attendees: int | None = Field(None, gt=0)
    registration_required: bool | None = None
    image_url: str | None = Field(None, max_length=2048)
    is_featured: bool | None = None
    series_id: str | None = Field(None, max_length=100)
    series_name: str | None = Field(None, max_length=255)
    is_published: bool | None = None
    branch_id: int | None = None
    wheelchair_accessible: bool | None = None
    asl_provided: bool | None = None
    captioning_provided: bool | None = None
    assistive_listening: bool | None = None
    sensory_friendly: bool | None = None
    large_print_available: bool | None = None
    accessibility_notes: str | None = Field(None, max_length=2000)
    attended_count: int | None = Field(
        None,
        ge=0,
        description="Actual attendance after the event ran; mirrors Program.actual_attendance",
    )

    # ------------------------------------------------------------------
    # Optional fields for partial update
    # ------------------------------------------------------------------
    recurrence_rule: Optional[str] = Field(None, max_length=2000)
    parent_event_id: Optional[int] = None
    presenters: Optional[List[PresenterEntry]] = None
    program_partner_id: Optional[int] = None
    photos_will_be_taken: Optional[bool] = None
    min_age: Optional[int] = Field(None, ge=0, le=120)
    max_age: Optional[int] = Field(None, ge=0, le=120)
    caregiver_required: Optional[bool] = None

    # Structured sensory descriptors.
    lighting: str | None = Field(None, description="Lighting level: dim | moderate | bright")
    noise_level: str | None = Field(None, description="Noise level: quiet | moderate | lively")
    crowd_size: str | None = Field(None, description="Expected crowd size: small | medium | large")
    quiet_space_available: bool | None = None

    @field_validator("lighting", "noise_level", "crowd_size", mode="after")
    @classmethod
    def validate_sensory_vocab(cls, v: str | None, info: ValidationInfo) -> str | None:
        return normalize_sensory_value(v, info.field_name)

    @field_validator("start_time", mode="after")
    @classmethod
    def validate_start_time_tz(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        return ensure_timezone_aware(v)

    @field_validator("end_time", mode="after")
    @classmethod
    def validate_end_time_tz(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        return ensure_timezone_aware(v)

    @model_validator(mode="after")
    def validate_times(self) -> "EventUpdate":
        # Only validate if both times are provided
        if self.start_time is not None and self.end_time is not None and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")

        if self.is_virtual is True and self.virtual_link is None:
            raise ValueError("virtual_link is required when is_virtual is true")

        # Partial update: only enforce pairing when BOTH fields are present
        # in this payload. A patch touching just one of them (the other
        # left unset) inherits the persisted value for the untouched side,
        # so it must not be forced into the create-time "both or neither"
        # rule -- mirrors validate_age_range's partial-update handling below.
        series_id_set = "series_id" in self.model_fields_set
        series_name_set = "series_name" in self.model_fields_set
        if series_id_set and series_name_set:
            if bool(self.series_id) != bool(self.series_name):
                raise ValueError("series_id and series_name must be provided together")

        return self

    @model_validator(mode="after")
    def validate_age_range(self) -> "EventUpdate":
        # Only enforce when BOTH are present in this partial update payload.
        # If only one is present, the DB CHECK still protects against bad combos
        # (the unsupplied side is whatever is currently persisted, and we don't
        # have the row here to compare against).
        if (
            self.min_age is not None
            and self.max_age is not None
            and self.min_age > self.max_age
        ):
            raise ValueError("min_age must be <= max_age")
        return self


class EventResponse(EventBase):
    id: int
    is_published: Optional[bool] = True
    created_at: datetime | None = None
    # Column on Event; NULL means staff haven't entered actual attendance yet.
    attended_count: int | None = None
    # Display name of the hosting branch. Not an ORM attribute — resolved by
    # an explicit batch lookup in the events endpoints (never a relationship
    # access during serialization).
    branch_name: str | None = None
    class Config:
        from_attributes = True


class EventWithStats(EventResponse):

    id: Optional[int] = None  # pyright: ignore[reportIncompatibleVariableOverride]  # None on virtual recurrence instances; populated on persisted events.
    is_virtual_instance: bool = Field(
        default=False,
        description="True when this row was generated by RRULE expansion (not a persisted DB row).",
    )

    registration_count: int = Field(default=0, description="Number of confirmed registrations")
    spots_remaining: Optional[int] = Field(
        default=None, description="Remaining spots (None if no max capacity)"
    )
    average_rating: Optional[float] = Field(
        default=None, description="Average rating from reviews (None if no reviews)"
    )
    review_count: int = Field(default=0, description="Number of reviews")


class RelatedEventsResponse(BaseModel):

    items: List[EventWithStats] = Field(..., description="List of related events")
    source_event_id: int = Field(..., description="ID of the source event")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 2,
                        "title": "Related Event",
                        "registration_count": 5,
                        "spots_remaining": 15,
                    }
                ],
                "source_event_id": 1,
            }
        }


# ──────────────────────────────────────────────────────────────────────────────
# Bulk-create recurring series (parent + N real children with parent_event_id)
# ──────────────────────────────────────────────────────────────────────────────
class EventBulkCreateRequest(StrictInputSchema, EventBase):

    # Inherited `recurrence_rule` (declared optional on EventBase) is REQUIRED here.
    recurrence_rule: str = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        ...,
        min_length=1,
        max_length=2000,
        description="RFC 5545 RRULE string. Required for bulk-create.",
    )
    dry_run: bool = Field(
        default=False,
        description="If true, return the expansion preview without writing to the DB.",
    )

    @field_validator("lighting", "noise_level", "crowd_size", mode="after")
    @classmethod
    def validate_sensory_vocab(cls, v: str | None, info: ValidationInfo) -> str | None:
        return normalize_sensory_value(v, info.field_name)

    @model_validator(mode="after")
    def validate_virtual_link(self) -> "EventBulkCreateRequest":
        if self.is_virtual and not self.virtual_link:
            raise ValueError("virtual_link is required when is_virtual is true")
        return self


class EventBulkInstancePreview(BaseModel):
    start_time: datetime
    end_time: datetime | None = None


class EventBulkCreateDryRunResponse(BaseModel):
    count: int
    first_start: datetime | None = None
    last_start: datetime | None = None
    instances: List[EventBulkInstancePreview]


class EventBulkCreateResponse(BaseModel):
    parent_id: int
    child_ids: List[int]
    count: int
