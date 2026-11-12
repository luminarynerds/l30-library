# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from ._base import StrictInputSchema

from ..models.card_application import CardApplicationStatus


# ============================================================================
# Card Application Schemas
# ============================================================================

class CardApplicationCreate(StrictInputSchema):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None

    # Address
    address_line1: str = Field(..., min_length=1, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=50)
    zip_code: str = Field(..., min_length=5, max_length=20)

    # Optional ID verification
    id_type: Optional[str] = Field(None, max_length=50)
    id_number_last4: Optional[str] = Field(None, min_length=4, max_length=4)

    # Cloudflare Turnstile token from the frontend widget. The endpoint is
    # public + PII-persisting; without this gate the only bot defense is the
    # rate limiter (fail-open in dev when CF_TURNSTILE_SECRET is unset).
    turnstile_token: Optional[str] = None

    @field_validator("id_number_last4")
    @classmethod
    def validate_id_last4(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.isalnum():
            raise ValueError("ID last 4 must be alphanumeric")
        return v


class CardApplicationReview(StrictInputSchema):
    status: CardApplicationStatus
    review_notes: Optional[str] = Field(None, max_length=2000)
    denial_reason: Optional[str] = Field(None, max_length=1000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: CardApplicationStatus) -> CardApplicationStatus:
        if v == CardApplicationStatus.pending:
            raise ValueError("Cannot set status to pending during review")
        return v

    @field_validator("denial_reason")
    @classmethod
    def validate_denial_reason(cls, v: Optional[str], info) -> Optional[str]:
        status = info.data.get("status")
        if status == CardApplicationStatus.denied and not v:
            raise ValueError("Denial reason is required when denying application")
        return v


class CardApplicationResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None

    # Address
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    zip_code: str

    # ID verification
    id_type: Optional[str] = None
    id_number_last4: Optional[str] = None

    # Status and processing
    status: CardApplicationStatus
    submitted_at: datetime
    reviewed_by_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    denial_reason: Optional[str] = None

    # Assigned card (if approved)
    assigned_card_number: Optional[str] = None

    class Config:
        from_attributes = True


class CardApplicationCoppaResponse(BaseModel):
    consent_required: bool = True
    detail: str
    message: str
    applicant_age: int
    minimum_online_age: int


class CardApplicationListResponse(BaseModel):
    applications: list[CardApplicationResponse]
    total: int
    limit: int
    offset: int


class CardApplicationPublicStatusResponse(BaseModel):
    status: CardApplicationStatus
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None


# ============================================================================
# Statistics Schemas
# ============================================================================

class CardApplicationStats(BaseModel):
    total_pending: int
    total_under_review: int
    total_approved: int
    total_denied: int
    total_this_week: int
    total_this_month: int
    average_review_time_hours: Optional[float] = None
