# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema

from ..models.weeding import (
    CREWCategory,
    DisposalMethod,
    DispositionRecommendation,
    WeedingReason,
    WeedingStatus,
)


# ============ Weeding Candidate Schemas ============


class WeedingCandidateBase(BaseModel):
    item_copy_id: int
    reason: str
    reason_notes: str | None = None


class WeedingCandidateCreate(StrictInputSchema, WeedingCandidateBase):
    pass


class WeedingCandidateResponse(BaseModel):
    id: int
    item_copy_id: int
    status: str
    reason: str
    reason_notes: str | None

    # Item details (populated from joins)
    item_title: str | None = None
    item_author: str | None = None
    item_barcode: str | None = None
    item_location: str | None = None
    item_type: str | None = None
    item_condition: str | None = None
    publication_year: int | None = None
    isbn: str | None = None

    # Circulation metrics
    last_checkout_date: date | None
    total_checkouts: int
    years_since_acquisition: int | None
    condition_score: float | None
    days_since_last_circulation: int | None

    # CREW analysis
    crew_category: str | None
    crew_score: float | None
    is_outdated_content: bool
    outdated_flags: str | None
    is_duplicate: bool
    duplicate_count: int
    is_superseded: bool
    never_circulated: bool
    section_fill_rate: float | None

    # Disposition
    disposition_recommendation: str | None
    disposition_rationale: str | None

    auto_generated: bool
    created_at: datetime | None = None
    created_by_id: int

    # Review/approval info
    reviewed_by_id: int | None = None
    reviewed_at: datetime | None = None
    approved_by_id: int | None = None
    approved_at: datetime | None = None

    class Config:
        from_attributes = True


class WeedingCandidateListResponse(BaseModel):
    items: list[WeedingCandidateResponse]
    total: int
    page: int
    per_page: int


# ============ Weeding Review Schemas ============


class WeedingReviewRequest(StrictInputSchema):
    review_notes: str | None = None
    action: str = Field(..., pattern="^(approve|reject)$")
    rejection_reason: str | None = None


class WeedingWithdrawRequest(StrictInputSchema):
    disposal_method: str
    disposal_notes: str | None = None
    disposal_recipient: str | None = None


# ============ Weeding Analysis Schemas ============


class WeedingAnalysisRequest(StrictInputSchema):
    location_filter: str | None = None
    crew_category: str | None = None
    min_crew_score: float = Field(default=50.0, ge=0, le=100)
    include_reasons: list[WeedingReason] | None = None
    max_results: int = Field(default=100, ge=1, le=500)


class SectionPressureResponse(BaseModel):
    location: str
    total_items: int
    capacity_estimate: int
    fill_rate: float  # 0.0 to 1.0
    weeding_candidates_count: int
    avg_item_age_years: float
    avg_checkouts: float
    low_circ_items: int  # items with 0-1 checkouts


class SectionPressureListResponse(BaseModel):
    sections: list[SectionPressureResponse]


class DuplicateGroupResponse(BaseModel):
    catalog_item_id: int
    title: str
    author: str | None
    isbn: str | None
    total_copies: int
    recommended_copies: int
    excess_copies: int
    copies: list[dict]  # Simplified copy info


class DuplicateDetectionResponse(BaseModel):
    groups: list[DuplicateGroupResponse]
    total_excess_copies: int


class OutdatedContentResponse(BaseModel):
    item_copy_id: int
    catalog_item_id: int
    title: str
    author: str | None
    publication_year: int | None
    subjects: str | None
    flags: list[str]  # e.g., ["medical_outdated", "tech_outdated"]
    age_years: int
    last_checkout_date: date | None
    total_checkouts: int


class OutdatedContentListResponse(BaseModel):
    items: list[OutdatedContentResponse]
    total: int


class SupersededEditionResponse(BaseModel):
    older_item_id: int
    older_title: str
    older_edition: str | None
    older_publication_year: int | None
    newer_item_id: int
    newer_title: str
    newer_edition: str | None
    newer_publication_year: int | None


class SupersededEditionListResponse(BaseModel):
    items: list[SupersededEditionResponse]
    total: int


class WeedingSummaryResponse(BaseModel):
    total_candidates: int
    by_status: dict[str, int]  # status -> count
    by_reason: dict[str, int]  # reason -> count
    sections_over_capacity: int
    total_duplicates_excess: int
    outdated_items: int
    never_circulated_items: int
    avg_crew_score: float | None


# ============ Weeding Rule Schemas ============


class WeedingRuleCreate(StrictInputSchema):
    name: str = Field(..., max_length=255)
    description: str | None = None
    crew_category: str | None = None
    max_age_years: int | None = None
    max_years_no_circulation: int | None = None
    min_condition_score: float | None = None
    max_duplicate_copies: int | None = None
    section_fill_threshold: float | None = None
    subject_keywords: str | None = None
    location_filter: str | None = None


class WeedingRuleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    crew_category: str | None
    max_age_years: int | None
    max_years_no_circulation: int | None
    min_condition_score: float | None
    max_duplicate_copies: int | None
    section_fill_threshold: float | None
    subject_keywords: str | None
    location_filter: str | None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class WeedingRuleListResponse(BaseModel):
    rules: list[WeedingRuleResponse]
    total: int
