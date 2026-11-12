# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.schemas._base import StrictInputSchema


# ============================================================================
# BanReport Schemas
# ============================================================================

class BanReportBase(BaseModel):
    title: str
    author: str
    isbn: str | None = None
    state: str = Field(..., min_length=2, max_length=2)
    county: str | None = None
    district: str | None = None
    institution: str | None = None
    ban_type: str = "CHALLENGED"
    reason: str | None = None
    reason_category: str | None = None
    source: str
    source_url: str | None = None
    date_reported: date | None = None
    date_enacted: date | None = None
    notes: str | None = None

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        return v.upper()

    @field_validator("ban_type", mode="before")
    @classmethod
    def validate_ban_type(cls, v: object) -> str:
        from enum import Enum
        if isinstance(v, Enum):
            v = v.value
        s = str(v).upper()
        valid = {"CHALLENGED", "BANNED", "RESTRICTED", "PENDING"}
        if s not in valid:
            raise ValueError(f"Invalid ban_type. Must be one of: {', '.join(sorted(valid))}")
        return s


class BanReportCreate(StrictInputSchema, BanReportBase):
    pass


class BanReportUpdate(StrictInputSchema):
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    state: str | None = None
    county: str | None = None
    district: str | None = None
    institution: str | None = None
    ban_type: str | None = None
    reason: str | None = None
    reason_category: str | None = None
    source: str | None = None
    source_url: str | None = None
    date_reported: date | None = None
    date_enacted: date | None = None
    notes: str | None = None
    catalog_match_id: int | None = None


class BanReportResponse(BanReportBase):
    id: int
    catalog_match_id: int | None = None
    matched_at: datetime | None = None
    created_by_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Rationale enrichment (added per-row by handlers; defaults to false /
    # None when no catalog match exists or no rationale is on file)
    rationale_present: bool = False
    rationale_anticipated: bool = False
    rationale_primary_use_case: str | None = None

    class Config:
        from_attributes = True


class BanReportPublicResponse(BaseModel):
    id: int
    title: str
    author: str
    state: str
    district: str | None = None
    ban_type: str
    reason_category: str | None = None
    source: str
    source_url: str | None = None
    date_reported: date | None = None
    date_enacted: date | None = None
    has_in_catalog: bool
    catalog_item_id: int | None = None
    cover_url: str | None = None

    class Config:
        from_attributes = True


class BanReportStats(BaseModel):
    total_reports: int
    total_states: int
    total_catalog_matches: int
    by_state: dict[str, int]
    by_type: dict[str, int]
    by_reason: dict[str, int]


class BanReportTimelineBucket(BaseModel):
    month: str  # ISO YYYY-MM
    banned: int = 0
    restricted: int = 0
    challenged: int = 0
    pending: int = 0


class BanReportTimelineResponse(BaseModel):
    buckets: list[BanReportTimelineBucket]


class PaginatedBanReports(BaseModel):
    items: list[BanReportResponse]
    total: int
    page: int
    per_page: int
    pages: int


class PaginatedPublicBanReports(BaseModel):
    items: list[BanReportPublicResponse]
    total: int
    page: int
    per_page: int
    pages: int


class MostBannedBook(BaseModel):
    title: str
    author: str
    report_count: int
    state_count: int
    states: list[str] = []


# ============================================================================
# BanAlertNotification Schemas
# ============================================================================

class BanAlertResponse(BaseModel):
    id: int
    ban_report_id: int
    seen_at: datetime | None = None
    created_at: datetime | None = None
    ban_report: BanReportResponse | None = None

    class Config:
        from_attributes = True


# ============================================================================
# AdvocacyLetterTemplate Schemas
# ============================================================================

class LetterTemplateBase(BaseModel):
    title: str
    subject_line: str
    body_template: str
    target_level: str = "any"
    is_active: bool = True

    @field_validator("target_level")
    @classmethod
    def validate_target_level(cls, v: str) -> str:
        valid = {"any", "federal", "state", "local"}
        if v not in valid:
            raise ValueError(f"Invalid target_level. Must be one of: {', '.join(sorted(valid))}")
        return v


class LetterTemplateCreate(StrictInputSchema, LetterTemplateBase):
    pass


class LetterTemplateUpdate(StrictInputSchema):
    title: str | None = None
    subject_line: str | None = None
    body_template: str | None = None
    target_level: str | None = None
    is_active: bool | None = None


class LetterTemplateResponse(LetterTemplateBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ============================================================================
# Civic API Schemas
# ============================================================================

class RepresentativeInfo(BaseModel):
    name: str
    office: str
    level: str | None = None
    party: str | None = None
    phones: list[str] = []
    emails: list[str] = []
    urls: list[str] = []
    photoUrl: str | None = None
    channels: list[dict] = []


class CivicLookupResponse(BaseModel):
    address: str
    officials: list[RepresentativeInfo]
    not_configured: bool = False


# ============================================================================
# BanTrackerSubscription Schemas (phase 1 backend foundation)
# ============================================================================

# Allowed enum values surfaced to clients. Kept narrow so the digest
# worker (phase 3) has a closed contract to switch on; widen only with
# a paired worker change.
SubscriptionScope = Literal["any", "state", "catalog"]
SubscriptionFrequency = Literal["weekly", "daily"]
SubscriptionBanType = Literal["banned", "restricted", "challenged"]


class _SubscriptionInputBase(StrictInputSchema):

    @field_validator("state_filter", mode="before", check_fields=False)
    @classmethod
    def _upper_state(cls, v):
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            return v
        v = v.strip().upper()
        if len(v) != 2:
            raise ValueError("state_filter must be a 2-letter US state code")
        return v


class BanTrackerSubscriptionCreate(_SubscriptionInputBase):

    scope: SubscriptionScope
    state_filter: Optional[str] = Field(default=None, min_length=2, max_length=2)
    ban_type_filter: Optional[SubscriptionBanType] = None
    frequency: SubscriptionFrequency = "weekly"

    @model_validator(mode="after")
    def _require_state_when_scope_state(self) -> "BanTrackerSubscriptionCreate":
        if self.scope == "state" and not self.state_filter:
            raise ValueError("state_filter is required when scope='state'")
        return self


class BanTrackerSubscriptionUpdate(_SubscriptionInputBase):

    scope: Optional[SubscriptionScope] = None
    state_filter: Optional[str] = Field(default=None, min_length=2, max_length=2)
    ban_type_filter: Optional[SubscriptionBanType] = None
    frequency: Optional[SubscriptionFrequency] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def _require_state_when_scope_state(self) -> "BanTrackerSubscriptionUpdate":
        if self.scope == "state" and not self.state_filter:
            raise ValueError("state_filter is required when scope='state'")
        return self


class BanTrackerSubscriptionResponse(BaseModel):

    id: int
    scope: str
    state_filter: Optional[str] = None
    ban_type_filter: Optional[str] = None
    frequency: str
    is_active: bool
    last_sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Public Patron Submission
# ============================================================================

class PublicBanReportSubmission(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=300)
    author: str = Field(..., min_length=1, max_length=200)
    state: str = Field(..., min_length=2, max_length=2)
    district: str | None = Field(default=None, max_length=200)
    institution: str | None = Field(default=None, max_length=200)
    ban_type: Literal["challenged", "restricted", "banned"]
    reason_category: str | None = Field(default=None, max_length=100)
    source_url: HttpUrl | None = None
    notes: str | None = Field(default=None, max_length=2000)
    turnstile_token: str = Field(..., min_length=1)

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        return v.upper()
