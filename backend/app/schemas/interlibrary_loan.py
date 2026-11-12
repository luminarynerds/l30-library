# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema

from ..models.interlibrary_loan import (
    ILLCostCategory,
    ILLRequestStatus,
    ILLRequestType,
    PartnerLibraryStatus,
    ShippingMethod,
)


# ---------------------------------------------------------------------------
# Partner Library
# ---------------------------------------------------------------------------

class PartnerLibraryCreate(StrictInputSchema):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=50)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str = "US"
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    ils_type: str | None = None
    z3950_host: str | None = None
    z3950_port: int | None = None
    z3950_database: str | None = None
    ncip_endpoint: str | None = None
    lending_fee: MoneyDecimal = Decimal("0")
    borrowing_fee: MoneyDecimal = Decimal("0")
    max_loan_days: int = 21
    max_renewals: int = 1
    reciprocal_agreement: bool = False
    agreement_expires_at: date | None = None
    notes: str | None = None


class PartnerLibraryUpdate(StrictInputSchema):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    ils_type: str | None = None
    z3950_host: str | None = None
    z3950_port: int | None = None
    z3950_database: str | None = None
    ncip_endpoint: str | None = None
    status: PartnerLibraryStatus | None = None
    lending_fee: MoneyDecimal | None = None
    borrowing_fee: MoneyDecimal | None = None
    max_loan_days: int | None = None
    max_renewals: int | None = None
    reciprocal_agreement: bool | None = None
    agreement_expires_at: date | None = None
    notes: str | None = None


class PartnerLibraryResponse(BaseModel):
    id: int
    name: str
    code: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    ils_type: str | None = None
    status: PartnerLibraryStatus
    lending_fee: MoneyDecimal
    borrowing_fee: MoneyDecimal
    max_loan_days: int
    max_renewals: int
    reciprocal_agreement: bool
    agreement_expires_at: date | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# ILL Request
# ---------------------------------------------------------------------------

class ILLRequestCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=500)
    author: str | None = None
    isbn: str | None = None
    issn: str | None = None
    publication_year: str | None = None
    edition: str | None = None
    volume: str | None = None
    material_type: str | None = None
    patron_notes: str | None = None
    needed_by: date | None = None
    pickup_branch_id: int | None = None


class ILLRequestStaffCreate(StrictInputSchema):
    patron_id: int
    request_type: ILLRequestType = ILLRequestType.borrow
    partner_library_id: int | None = None
    catalog_item_id: int | None = None
    title: str = Field(..., min_length=1, max_length=500)
    author: str | None = None
    isbn: str | None = None
    issn: str | None = None
    publication_year: str | None = None
    edition: str | None = None
    volume: str | None = None
    material_type: str | None = None
    notes: str | None = None
    patron_notes: str | None = None
    needed_by: date | None = None
    pickup_branch_id: int | None = None
    shipping_method: ShippingMethod | None = None
    estimated_cost: MoneyDecimal | None = Decimal("0")


class ILLRequestUpdate(StrictInputSchema):
    status: ILLRequestStatus | None = None
    partner_library_id: int | None = None
    shipping_method: ShippingMethod | None = None
    outbound_tracking: str | None = None
    return_tracking: str | None = None
    due_date: date | None = None
    estimated_cost: MoneyDecimal | None = None
    actual_cost: MoneyDecimal | None = None
    notes: str | None = None


class ILLTrackingUpdateCreate(StrictInputSchema):
    message: str
    is_patron_visible: bool = True


class ILLTrackingUpdateResponse(BaseModel):
    id: int
    ill_request_id: int
    status: ILLRequestStatus
    message: str
    is_patron_visible: bool
    created_at: datetime | None = None
    created_by_id: int | None = None

    class Config:
        from_attributes = True


class ILLRequestResponse(BaseModel):
    id: int
    patron_id: int | None = None
    staff_id: int | None = None
    request_type: ILLRequestType
    partner_library_id: int | None = None
    partner_library_name: str | None = None
    catalog_item_id: int | None = None
    title: str
    author: str | None = None
    isbn: str | None = None
    issn: str | None = None
    publication_year: str | None = None
    edition: str | None = None
    volume: str | None = None
    material_type: str | None = None
    notes: str | None = None
    patron_notes: str | None = None
    status: ILLRequestStatus
    pickup_branch_id: int | None = None
    needed_by: date | None = None
    due_date: date | None = None
    shipped_at: datetime | None = None
    received_at: datetime | None = None
    checked_out_at: datetime | None = None
    returned_at: datetime | None = None
    completed_at: datetime | None = None
    shipping_method: ShippingMethod | None = None
    outbound_tracking: str | None = None
    return_tracking: str | None = None
    estimated_cost: MoneyDecimal | None = Decimal("0")
    actual_cost: MoneyDecimal | None = Decimal("0")
    renewal_count: int
    max_renewals: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ILLRequestPatronView(StrictInputSchema):
    id: int
    title: str
    author: str | None = None
    status: ILLRequestStatus
    status_label: str  # Human-readable status
    due_date: date | None = None
    needed_by: date | None = None
    pickup_branch_id: int | None = None
    renewal_count: int
    max_renewals: int
    tracking_updates: list[ILLTrackingUpdateResponse] = []
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Cost Records
# ---------------------------------------------------------------------------

class ILLCostRecordCreate(StrictInputSchema):
    category: ILLCostCategory
    description: str | None = None
    amount: MoneyDecimal


class ILLCostRecordResponse(BaseModel):
    id: int
    ill_request_id: int
    category: ILLCostCategory
    description: str | None = None
    amount: MoneyDecimal
    is_invoiced: bool
    invoiced_at: datetime | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Partner Search Result
# ---------------------------------------------------------------------------

class PartnerSearchResult(BaseModel):
    partner_library_id: int
    partner_library_name: str
    partner_library_code: str
    available: bool
    call_number: str | None = None
    estimated_delivery_days: int | None = None
    lending_fee: MoneyDecimal = Decimal("0")


# ---------------------------------------------------------------------------
# Fill Rate & Reporting
# ---------------------------------------------------------------------------

class ILLFillRateReport(BaseModel):
    total_requests: int
    filled_requests: int
    unfilled_requests: int
    cancelled_requests: int
    fill_rate_percent: float
    average_turnaround_days: float | None = None
    period_start: date
    period_end: date


class ILLCostSummary(BaseModel):
    total_borrowing_costs: MoneyDecimal
    total_lending_revenue: MoneyDecimal
    net_cost: MoneyDecimal
    average_cost_per_request: MoneyDecimal
    cost_by_category: dict[str, MoneyDecimal]
    period_start: date
    period_end: date


class ReciprocallLendingStats(BaseModel):
    partner_library_id: int
    partner_library_name: str
    partner_library_code: str
    items_borrowed: int
    items_lent: int
    balance: int  # positive = we owe them, negative = they owe us
    total_borrowing_cost: MoneyDecimal
    total_lending_revenue: MoneyDecimal
    active_borrows: int
    active_lends: int
    fill_rate_percent: float


class ReciprocallLendingDashboard(BaseModel):
    total_partners: int
    active_partners: int
    total_items_borrowed: int
    total_items_lent: int
    overall_balance: int
    net_cost: MoneyDecimal
    partner_stats: list[ReciprocallLendingStats]
    period_start: date
    period_end: date


class DueDateReminderConfig(BaseModel):
    days_before_due: list[int] = [7, 3, 1]
    send_email: bool = True
    send_sms: bool = False
