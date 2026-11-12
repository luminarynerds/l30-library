# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Shared schemas for patron management endpoints.

This module contains Pydantic models used across multiple patron-related routers.
"""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

from ....schemas._base import MoneyDecimal
from ....schemas.circulation import CheckoutResponse, HoldResponse
from ....schemas.fine import FineResponse
from ....schemas.user import UserResponse


# =============================================================================
# Patron List & Search Schemas
# =============================================================================


class PatronListResponse(BaseModel):
    patrons: list[UserResponse]
    total_count: int


class PatronSortField(StrEnum):
    name = "name"
    member_date = "member_date"
    fines_balance = "fines_balance"
    checkout_count = "checkout_count"


class SortDirection(StrEnum):
    asc = "asc"
    desc = "desc"


class OverdueFilter(StrEnum):
    all = "all"
    has_overdue = "has_overdue"
    no_overdue = "no_overdue"


class CardStatusFilter(StrEnum):
    any = "any"
    active = "active"
    expiring_30d = "expiring_30d"
    expiring_90d = "expiring_90d"
    expired = "expired"


class ExpiringCardsCounts(BaseModel):
    expiring_within_30d: int = 0
    expiring_within_90d: int = 0
    expired: int = 0


# =============================================================================
# Patron Detail Schemas
# =============================================================================


class PatronDetailResponse(UserResponse):
    checkouts: list[CheckoutResponse] = []
    holds: list[HoldResponse] = []
    fines: list[FineResponse] = []
    total_fines_owed: Decimal = Decimal("0.00")


# =============================================================================
# Patron Status Schemas
# =============================================================================


class PatronBlock(BaseModel):
    blocked: bool
    reason: str | None = None


class PatronSuspend(BaseModel):
    reason: str
    suspended_until: datetime | None = None


class PatronStatusUpdate(BaseModel):
    action: str  # "block", "unblock", "suspend", "unsuspend"
    reason: str | None = None
    suspended_until: datetime | None = None


# =============================================================================
# Patron Statistics Schemas
# =============================================================================


class AtRiskCounts(BaseModel):
    patrons_with_many_overdue: int = 0
    patrons_with_high_fines: int = 0
    inactive_patrons: int = 0


class AtRiskPatron(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    library_card: str | None = None
    overdue_count: int = 0
    fines_balance: Decimal = Decimal("0.00")
    last_activity_date: datetime | None = None


class PatronStatisticsResponse(BaseModel):
    total_patrons: int
    active_patrons: int
    blocked_patrons: int
    new_this_week: int
    new_this_month: int
    total_fines_outstanding: Decimal
    total_overdue_items: int
    at_risk_counts: AtRiskCounts
    expiring_cards_counts: ExpiringCardsCounts = ExpiringCardsCounts()
    patrons_with_many_overdue: list[AtRiskPatron] = []
    patrons_with_high_fines: list[AtRiskPatron] = []
    inactive_patrons: list[AtRiskPatron] = []


# =============================================================================
# Patron Context Card Schemas
# =============================================================================


class StaffNote(BaseModel):
    category: str
    content: str
    priority: str
    created_at: datetime | None = None


class AccountAlert(BaseModel):
    alert_type: str
    severity: str  # 'info', 'warning', 'critical'
    message: str
    details: dict | None = None


class CheckoutSummary(BaseModel):
    total_count: int
    active_count: int
    overdue_count: int
    due_soon_count: int
    due_soon_items: list[dict] = []


class HoldSummary(BaseModel):
    total_pending: int
    ready_for_pickup_count: int
    ready_items: list[dict] = []


class RecentGenre(BaseModel):
    genre: str
    count: int


class LoyaltyStatus(BaseModel):
    total_xp: int = 0
    current_level: str = "Member"
    achievements_earned: int = 0
    achievements_list: list[dict] = []


class PatronContextCardResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    preferred_name: str | None = None
    pronouns: str | None = None
    photo_url: str | None = None
    library_card: str | None = None
    patron_status: str
    account_alerts: list[AccountAlert] = []
    email: str
    phone: str | None = None
    language_preference: str | None = None
    accessibility_needs: str | None = None
    created_at: datetime
    last_login: datetime | None = None
    checkout_frequency: str
    total_checkouts_lifetime: int = 0
    checkouts: CheckoutSummary
    holds: HoldSummary
    fines: dict | None = None
    reading_preferences: list[RecentGenre] = []
    staff_notes: list[StaffNote] = []
    loyalty_status: LoyaltyStatus


# =============================================================================
# Bulk Operations Schemas
# =============================================================================


class BulkBlockRequest(BaseModel):
    patron_ids: list[int]
    blocked: bool
    reason: str | None = None


class BulkBlockResponse(BaseModel):
    success: bool
    processed_count: int
    failed_ids: list[int]
    message: str


class BulkWaiveFinesRequest(BaseModel):
    patron_ids: list[int] = Field(..., min_length=1, max_length=100)
    reason: str = Field(..., min_length=3, max_length=500, description="Reason for waiving fines (required)")


class BulkWaiveFinesResponse(BaseModel):
    success: bool
    patrons_processed: int
    fines_waived: int
    total_amount_waived: MoneyDecimal
    failed_ids: list[int]
    message: str


class BulkNotificationRequest(BaseModel):
    patron_ids: list[int] = Field(..., min_length=1, max_length=500)
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=5000)
    notification_type: str = "general"


class BulkNotificationResponse(BaseModel):
    success: bool
    sent_count: int
    failed_ids: list[int]
    message: str


# =============================================================================
# Export Schemas
# =============================================================================


class PatronExportData(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    library_card: str | None
    phone: str | None
    address: str | None
    is_active: bool
    created_at: str
    fines_balance: Decimal
    current_checkouts: int
    current_holds: int
    total_checkouts: int


class PatronExportResponse(BaseModel):
    patrons: list[PatronExportData]
    total_count: int
    exported_at: str


# =============================================================================
# Activity & Timeline Schemas
# =============================================================================


class PatronActivityResponse(BaseModel):
    id: int
    patron_id: int
    staff_id: int | None = None
    staff_name: str | None = None
    activity_type: str
    description: str
    item_id: int | None = None
    item_title: str | None = None
    item_author: str | None = None
    fine_id: int | None = None
    fine_amount: str | None = None
    checkout_id: int | None = None
    hold_id: int | None = None
    metadata: str | None = None
    created_at: datetime


class PatronActivityListResponse(BaseModel):
    activities: list[PatronActivityResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


class PatronPhotoUpload(BaseModel):
    photo_data: str
    content_type: str = "image/jpeg"


class PatronPhotoResponse(BaseModel):
    photo_url: str
    message: str = "Photo uploaded successfully"


# =============================================================================
# Circulation Operation Schemas
# =============================================================================


class QuickCheckoutRequest(BaseModel):
    barcode: str
    override_hold: bool = False
    hold_disposition: Optional[str] = None  # "bump_to_front" | "cancel"


class QuickCheckoutResponse(BaseModel):
    checkout: CheckoutResponse
    message: str


class RenewAllResponse(BaseModel):
    renewed_count: int
    failed_count: int
    renewals: list[CheckoutResponse]
    failures: list[dict]
    message: str


class ReturnAllResponse(BaseModel):
    returned_count: int
    returns: list[CheckoutResponse]
    message: str


class PlaceHoldForPatronRequest(BaseModel):
    item_id: int


class PlaceHoldForPatronResponse(BaseModel):
    hold: HoldResponse
    message: str


# =============================================================================
# Family/Linked Accounts Schemas
# =============================================================================


class LinkedAccountInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    library_card: str | None = None
    is_active: bool


class PatronFamilyResponse(BaseModel):
    patron_id: int
    parent_guardian: LinkedAccountInfo | None = None
    children: list[LinkedAccountInfo] = []


# =============================================================================
# Staff Member Schemas
# =============================================================================


class StaffListResponse(BaseModel):
    staff: list[UserResponse]
    total_count: int


# =============================================================================
# Hold-Aware Checkout Schemas
# =============================================================================


class ItemHoldInfo(BaseModel):
    hold_id: int
    patron_id: int
    patron_name: str
    position: int
    status: str
    created_at: datetime | None = None
    expires_at: datetime | None = None


class ItemHoldsCheckResponse(BaseModel):
    item_id: int
    item_title: str
    item_barcode: str | None = None
    total_holds: int
    holds: list[ItemHoldInfo]
