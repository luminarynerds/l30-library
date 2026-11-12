# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel

from ._base import StrictInputSchema

from ..models.circulation import CheckoutStatus, HoldStatus


class CheckoutCreate(StrictInputSchema):
    item_id: int


class CheckoutResponse(BaseModel):
    id: int
    user_id: int
    item_id: int
    status: CheckoutStatus
    checked_out_at: datetime
    due_date: datetime
    returned_at: datetime | None = None
    renewal_count: int = 0
    renewals_remaining: int = 0  # Number of remaining renewals (max_renewals - renewal_count)

    # Include item details for convenience
    item_title: str | None = None
    item_author: str | None = None

    class Config:
        from_attributes = True


class CheckoutReturn(StrictInputSchema):
    checkout_id: int


class NextHoldInfo(BaseModel):
    hold_id: int
    patron_first_name: str
    patron_last_initial: str
    shelf_slot: str | None = None
    expires_at: datetime | None = None
    item_title: str | None = None


class HoldCreate(StrictInputSchema):
    item_id: int
    pickup_location_id: int | None = None


class HoldCancel(StrictInputSchema):
    reason: str = ""


class HoldResponse(BaseModel):
    id: int
    user_id: int
    item_id: int
    status: HoldStatus
    position: int | None = None
    queue_position: int | None = None  # Queue position for pending holds, None otherwise
    pickup_location_id: int | None = None
    pickup_branch_name: str | None = None
    created_at: datetime | None = None
    notified_at: datetime | None = None
    expires_at: datetime | None = None

    # Cancellation metadata
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    cancelled_by: str | None = None

    # Smart hold shelf fields
    shelf_slot: str | None = None
    patron_on_way: bool = False
    qr_pickup_code: str | None = None
    no_show_count: int = 0

    # Include item details for convenience
    item_title: str | None = None
    item_author: str | None = None

    # Wait estimate for pending holds only (None for ready holds or unknown)
    estimated_wait_days: int | None = None
    estimated_wait_weeks: int | None = None

    class Config:
        from_attributes = True


class CirculationStats(BaseModel):
    active_checkouts: int
    pending_holds: int
    overdue_items: int


class HoldAgingBracket(BaseModel):
    bracket_label: str  # e.g., "0-7 days", "7-14 days", "14-30 days", "30+ days"
    min_days: int
    max_days: int | None  # None for unbounded (30+ days)
    count: int


class HoldAgingReport(BaseModel):
    total_pending_holds: int
    average_wait_days: float
    longest_wait_days: int
    brackets: list[HoldAgingBracket]

    # Optional filter information
    filtered_by_item_id: int | None = None
    filtered_by_location: str | None = None
    filtered_by_date_from: datetime | None = None
    filtered_by_date_to: datetime | None = None


class PullListItem(BaseModel):

    hold_id: int
    item_id: int
    item_title: str
    item_author: str | None = None
    call_number: str | None = None
    shelf_location: str | None = None
    barcode: str | None = None
    patron_name: str
    patron_initials: str  # Initials only (e.g., "JD" for John Doe)
    patron_library_card: str | None = None
    hold_expires_at: datetime | None = None
    hold_created_at: datetime
    days_until_expiry: int | None = None  # Days remaining to pickup
    shelf_slot: str | None = None
    patron_on_way: bool = False
    qr_pickup_code: str | None = None
    no_show_count: int = 0

    class Config:
        from_attributes = True


class LocationGroup(BaseModel):

    location: str
    items: list[PullListItem]
    item_count: int


class PullListResponse(BaseModel):

    locations: list[LocationGroup]
    total_items: int
    generated_at: datetime


class ProblemResolutionRequest(StrictInputSchema):

    problem_type: str  # e.g., "on_hold", "fine_balance", "card_expired"
    action_type: str  # e.g., "override", "waive", "pay", "swap_item"
    input_data: Optional[Dict[str, Any]] = None  # Action-specific input (amount, reason, etc.)


class ProblemResolutionResponse(BaseModel):

    success: bool
    message: str
    action_type: str
    problem_type: str
    additional_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# =============================================================================
# Smart Hold Shelf Schemas
# =============================================================================


class PatronOnWayRequest(StrictInputSchema):
    hold_id: int


class PatronOnWayResponse(BaseModel):
    hold_id: int
    patron_on_way: bool
    extended_expires_at: datetime | None = None
    message: str


class ExpiringHoldItem(BaseModel):
    hold_id: int
    item_id: int
    item_title: str
    item_author: str | None = None
    patron_name: str
    patron_initials: str
    shelf_slot: str | None = None
    expires_at: datetime | None = None
    hours_until_expiry: float | None = None
    patron_on_way: bool = False
    patron_library_card: str | None = None

    class Config:
        from_attributes = True


class ExpiringHoldsResponse(BaseModel):
    holds: list[ExpiringHoldItem]
    total_expiring: int
    generated_at: datetime


class HoldShelfSlipData(BaseModel):
    hold_id: int
    item_title: str
    item_author: str | None = None
    call_number: str | None = None
    patron_initials: str
    patron_name: str
    shelf_slot: str | None = None
    expires_at: datetime | None = None
    qr_pickup_code: str | None = None
    barcode: str | None = None
    pickup_location: str | None = None


class ReQueueResult(BaseModel):
    hold_id: int
    new_position: int
    no_show_count: int
    message: str


class PatronOnWayStatusItem(BaseModel):
    hold_id: int
    item_title: str | None = None
    item_author: str | None = None
    shelf_slot: str | None = None
    expires_at: datetime | None = None
    qr_pickup_code: str | None = None
    is_ready: bool
    estimated_wait_time_minutes: int


class PatronOnWayStatusResponse(BaseModel):
    on_way_holds: list[PatronOnWayStatusItem]
    total_on_way_count: int
    all_items_ready: bool


class OnWayCancelResponse(BaseModel):
    hold_id: int
    patron_on_way: bool
    message: str



class ShelfSlotUpdateRequest(StrictInputSchema):
    shelf_slot: str | None = None


class ShelfSlotUpdateResponse(BaseModel):
    hold_id: int
    shelf_slot: str | None = None
    message: str


class FulfillHoldResponse(BaseModel):
    hold_id: int
    status: str
    message: str


class HoldCheckoutResponse(BaseModel):
    checkout: CheckoutResponse
    hold_id: int
    message: str


class StaffPatronOnWayToggleResponse(BaseModel):
    hold_id: int
    patron_on_way: bool
    message: str
