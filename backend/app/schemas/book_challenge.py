# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema

from .acquisition_rationale import AcquisitionRationaleRead


# ============================================================================
# Book Challenge Schemas
# ============================================================================

class BookChallengeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    author: str | None = Field(None, max_length=255)
    isbn: str | None = Field(None, max_length=20)
    catalog_item_id: int | None = None
    primary_reason: str = Field(..., description="Primary reason for the challenge")
    additional_reasons: str | None = None
    challenger_complaint: str | None = None


class BookChallengeCreate(StrictInputSchema, BookChallengeBase):
    challenger_name: str | None = Field(None, max_length=255)
    challenger_is_patron: bool = True
    challenger_contact: str | None = Field(None, max_length=255)


class PublicReconsiderationRequest(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=500, description="Title of the material")
    author: str | None = Field(None, max_length=255, description="Author of the material")
    isbn: str | None = Field(None, max_length=20)
    primary_reason: str = Field(..., description="Primary reason for the challenge")
    challenger_complaint: str = Field(
        ..., min_length=10, max_length=5000,
        description="Describe your specific concerns about this material"
    )
    challenger_name: str = Field(..., min_length=1, max_length=255, description="Your full name")
    challenger_contact: str | None = Field(
        None, max_length=255,
        description="Email or phone for follow-up (optional)"
    )
    has_read_material: bool = Field(
        ..., description="Confirm you have read/viewed the material in its entirety"
    )
    turnstile_token: str | None = Field(
        None, description="Cloudflare Turnstile token from the public reconsideration form"
    )

    @field_validator("primary_reason", mode="before")
    @classmethod
    def validate_reason(cls, v: object) -> str:
        from enum import Enum
        if isinstance(v, Enum):
            v = v.value
        s = str(v).lower()
        valid = {
            "sexual_content", "lgbtq_content", "violence", "language",
            "religious_viewpoint", "political_viewpoint", "age_inappropriate",
            "racism", "drugs_alcohol", "anti_family", "occult_supernatural", "other",
        }
        if s not in valid:
            raise ValueError(f"Invalid reason. Must be one of: {', '.join(sorted(valid))}")
        return s


class PublicReconsiderationResponse(BaseModel):
    message: str
    reference_id: int
    expected_response_days: int = 30


class BookChallengeUpdate(StrictInputSchema):
    status: str | None = None
    outcome: str | None = None
    resolution_summary: str | None = None
    committee_notes: str | None = None
    assigned_staff_id: int | None = None
    date_resolved: datetime | None = None

    # Public story fields
    is_public: bool | None = None
    public_title: str | None = Field(None, max_length=255)
    public_summary: str | None = None
    lessons_learned: str | None = None


class BookChallengeResponse(BookChallengeBase):
    id: int
    status: str
    outcome: str
    date_received: datetime
    date_resolved: datetime | None = None
    resolution_summary: str | None = None
    assigned_staff_id: int | None = None
    resolved_by_id: int | None = None
    is_public: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class BookChallengePublicResponse(BaseModel):
    id: int
    catalog_item_id: int | None = None
    public_title: str | None = None
    title: str  # Fallback if no public_title
    author: str | None = None
    primary_reason: str
    outcome: str
    public_summary: str | None = None
    lessons_learned: str | None = None
    date_received: datetime
    date_resolved: datetime | None = None

    class Config:
        from_attributes = True


class BookChallengeDetailResponse(BookChallengeResponse):
    challenger_name: str | None = None
    challenger_is_patron: bool | None = None
    challenger_contact: str | None = None
    committee_notes: str | None = None
    public_title: str | None = None
    public_summary: str | None = None
    lessons_learned: str | None = None
    notes: List["BookChallengeNoteResponse"] = []
    # M3: acquisition rationale defense - auto-loaded by GET handler.
    acquisition_rationale: AcquisitionRationaleRead | None = None


# ============================================================================
# Book Challenge Note Schemas
# ============================================================================

class BookChallengeNoteCreate(StrictInputSchema):
    note: str = Field(..., min_length=1)
    is_internal: bool = True


class BookChallengeNoteResponse(BaseModel):
    id: int
    challenge_id: int
    note: str
    is_internal: bool
    created_by_id: int | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Intellectual Freedom Resource Schemas
# ============================================================================

class IntellectualFreedomResourceBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    content: str | None = None
    url: str | None = Field(None, max_length=500)
    resource_type: str = Field(..., description="Type: article, video, external_link, policy")
    display_order: int = 0
    is_active: bool = True


class IntellectualFreedomResourceCreate(StrictInputSchema, IntellectualFreedomResourceBase):
    pass


class IntellectualFreedomResourceUpdate(StrictInputSchema):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    content: str | None = None
    url: str | None = Field(None, max_length=500)
    resource_type: str | None = None
    display_order: int | None = None
    is_active: bool | None = None


class IntellectualFreedomResourceResponse(IntellectualFreedomResourceBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ============================================================================
# Statistics Schemas
# ============================================================================

class BookChallengeStats(BaseModel):
    total_challenges: int
    pending_challenges: int
    resolved_this_year: int
    outcomes: dict[str, int]  # outcome -> count
    reasons: dict[str, int]  # reason -> count
    # Years (from date_received) that have at least one is_public challenge.
    # Drives the Year dropdown on the public Transparency Log so it never
    # offers a filter value that would return zero rows.
    available_years: List[int] = []


# ============================================================================
# Paginated Response
# ============================================================================

class PaginatedBookChallenges(BaseModel):
    items: List[BookChallengeResponse]
    total: int
    page: int
    per_page: int
    pages: int


class PaginatedBookChallengePublic(BaseModel):
    items: List[BookChallengePublicResponse]
    total: int
    page: int
    per_page: int
    pages: int


# Fix forward reference
BookChallengeDetailResponse.model_rebuild()
