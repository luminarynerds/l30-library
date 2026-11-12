# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, date, time
from typing import Optional, List
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


# ============================================================================
# Enums
# ============================================================================

class ShiftSwapListingType(StrEnum):
    giving_away = "giving_away"
    looking_for = "looking_for"


class ShiftSwapListingStatus(StrEnum):
    open = "open"
    claimed = "claimed"
    completed = "completed"
    withdrawn = "withdrawn"
    expired = "expired"


class ShiftSwapClaimStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    completed = "completed"
    cancelled = "cancelled"
    rejected = "rejected"


class ShiftType(StrEnum):
    opening = "opening"
    closing = "closing"
    mid_day = "mid_day"
    full_day = "full_day"
    partial = "partial"


class SwapMatchStatus(StrEnum):
    pending_notification = "pending_notification"
    notified = "notified"
    accepted = "accepted"
    rejected = "rejected"
    completed = "completed"


class NotificationType(StrEnum):
    new_match = "new_match"
    match_accepted = "match_accepted"
    match_rejected = "match_rejected"
    swap_claimed = "swap_claimed"
    swap_expiring = "swap_expiring"
    claim_approved = "claim_approved"
    claim_rejected = "claim_rejected"


# ============================================================================
# Shift Swap Listing Schemas
# ============================================================================

class ShiftSwapListingCreate(StrictInputSchema):
    branch_id: int
    listing_type: ShiftSwapListingType
    shift_date: date
    shift_start_time: time
    shift_end_time: time
    shift_type: ShiftType
    is_partial: bool = False
    partial_description: Optional[str] = None
    description: Optional[str] = None
    expires_at: datetime


class ShiftSwapListingUpdate(StrictInputSchema):
    description: Optional[str] = None
    shift_date: Optional[date] = None
    shift_start_time: Optional[time] = None
    shift_end_time: Optional[time] = None
    shift_type: Optional[ShiftType] = None
    is_partial: Optional[bool] = None
    partial_description: Optional[str] = None


class ShiftSwapListingResponse(BaseModel):
    id: int
    user_id: int
    branch_id: int
    listing_type: ShiftSwapListingType
    shift_date: date
    shift_start_time: time
    shift_end_time: time
    shift_type: ShiftType
    is_partial: bool
    partial_description: Optional[str]
    status: ShiftSwapListingStatus
    description: Optional[str]
    expires_at: datetime
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ShiftSwapListingDetailResponse(ShiftSwapListingResponse):
    user_name: Optional[str] = None
    branch_name: Optional[str] = None
    claims_count: int
    is_owner: bool
    has_claimed: bool


# ============================================================================
# Shift Swap Claim Schemas
# ============================================================================

class ShiftSwapClaimCreate(StrictInputSchema):
    listing_id: int
    swap_shift_date: Optional[date] = None
    swap_shift_start_time: Optional[time] = None
    swap_shift_end_time: Optional[time] = None
    message: Optional[str] = None


class ShiftSwapClaimApprove(BaseModel):
    approval_notes: Optional[str] = None


class ShiftSwapClaimReject(BaseModel):
    rejection_reason: str


class ShiftSwapClaimResponse(BaseModel):
    id: int
    listing_id: int
    claimer_id: int
    claimer_name: str = ""  # populated by handlers after model_validate; default lets validation pass on the ORM object
    status: ShiftSwapClaimStatus
    swap_shift_date: Optional[date]
    swap_shift_start_time: Optional[time]
    swap_shift_end_time: Optional[time]
    message: Optional[str]
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]
    rejected_reason: Optional[str]
    completed_at: Optional[datetime]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Staff Preference Schemas
# ============================================================================

class StaffPreferenceProfileCreate(StrictInputSchema):
    wants_extra_hours: bool = False
    preferred_shift_types: List[ShiftType] = []
    preferred_branches: List[int] = []
    preferred_days_of_week: List[str] = []
    days_available: List[str] = []
    earliest_available_time: Optional[time] = None
    latest_available_time: Optional[time] = None
    max_extra_hours_per_week: int = 10
    max_consecutive_days: int = 5
    auto_claim_compatible: bool = False
    notify_on_new_matches: bool = True
    notes: Optional[str] = None


class StaffPreferenceProfileUpdate(StrictInputSchema):
    wants_extra_hours: Optional[bool] = None
    preferred_shift_types: Optional[List[ShiftType]] = None
    preferred_branches: Optional[List[int]] = None
    preferred_days_of_week: Optional[List[str]] = None
    days_available: Optional[List[str]] = None
    earliest_available_time: Optional[time] = None
    latest_available_time: Optional[time] = None
    max_extra_hours_per_week: Optional[int] = None
    max_consecutive_days: Optional[int] = None
    auto_claim_compatible: Optional[bool] = None
    notify_on_new_matches: Optional[bool] = None
    notes: Optional[str] = None


class StaffPreferenceProfileResponse(BaseModel):
    id: int
    user_id: int
    wants_extra_hours: bool
    preferred_shift_types: List[ShiftType]
    preferred_branches: List[int]
    preferred_days_of_week: List[str]
    days_available: List[str]
    earliest_available_time: Optional[time]
    latest_available_time: Optional[time]
    max_extra_hours_per_week: int
    max_consecutive_days: int
    auto_claim_compatible: bool
    notify_on_new_matches: bool
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Reliability Score Schemas
# ============================================================================

class SwapperReliabilityScoreResponse(BaseModel):
    id: int
    user_id: int
    total_completed_swaps: int
    total_swap_claims: int
    reliability_score: float
    completion_rate: float
    cancelled_after_claiming_count: int
    called_out_after_swap_count: int
    no_show_count: int
    times_stood_up: int
    times_let_down: int
    last_swap_date: Optional[date]
    flags: Optional[str]

    class Config:
        from_attributes = True


# ============================================================================
# Match Schemas
# ============================================================================

class ShiftSwapMatchResponse(BaseModel):
    id: int
    giver_listing_id: int
    taker_listing_id: int
    compatibility_score: float
    status: SwapMatchStatus
    notified_at: Optional[datetime]
    accepted_at: Optional[datetime]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ShiftSwapMatchDetailResponse(ShiftSwapMatchResponse):
    giver_listing: ShiftSwapListingResponse
    taker_listing: ShiftSwapListingResponse


# ============================================================================
# Notification Schemas
# ============================================================================

class ShiftSwapNotificationResponse(BaseModel):
    id: int
    user_id: int
    notification_type: NotificationType
    match_id: Optional[int]
    listing_id: Optional[int]
    claim_id: Optional[int]
    title: str
    message: str
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ShiftSwapNotificationBatch(BaseModel):
    notifications: List[ShiftSwapNotificationResponse]
    total: int
    unread_count: int


# ============================================================================
# Filter/Search Schemas
# ============================================================================

class ShiftSwapListingFilter(StrictInputSchema):
    branch_id: Optional[int] = None
    listing_type: Optional[ShiftSwapListingType] = None
    shift_type: Optional[ShiftType] = None
    status: Optional[ShiftSwapListingStatus] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    time_from: Optional[time] = None
    time_to: Optional[time] = None


# ============================================================================
# Summary/Dashboard Schemas
# ============================================================================

class UserShiftSwapSummary(BaseModel):
    active_listings_count: int
    pending_claims_count: int
    approved_swaps_count: int
    completed_swaps_count: int
    reliability_score: float
    total_swaps: int
    open_matches_count: int


class ShiftSwapDashboardResponse(BaseModel):
    user_summary: UserShiftSwapSummary
    recent_listings: List[ShiftSwapListingResponse]
    recent_notifications: List[ShiftSwapNotificationResponse]
    recent_matches: List[ShiftSwapMatchResponse]
    preference_profile: Optional[StaffPreferenceProfileResponse]
