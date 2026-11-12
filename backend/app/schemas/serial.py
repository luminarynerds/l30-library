# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema


# -- Serial Title -----------------------------------------------------------

class SerialTitleCreate(StrictInputSchema):
    title: str = Field(..., max_length=500)
    catalog_item_id: int | None = None
    issn_print: str | None = Field(None, max_length=9)
    issn_electronic: str | None = Field(None, max_length=9)
    publisher: str | None = Field(None, max_length=255)
    country_of_publication: str | None = Field(None, max_length=3)
    language: str | None = Field(None, max_length=10)
    frequency: str = "monthly"
    notes: str | None = None


class SerialTitleUpdate(StrictInputSchema):
    title: str | None = Field(None, max_length=500)
    issn_print: str | None = Field(None, max_length=9)
    issn_electronic: str | None = Field(None, max_length=9)
    publisher: str | None = Field(None, max_length=255)
    country_of_publication: str | None = Field(None, max_length=3)
    language: str | None = Field(None, max_length=10)
    frequency: str | None = None
    is_active: bool | None = None
    ceased_date: date | None = None
    preceding_title_id: int | None = None
    succeeding_title_id: int | None = None
    notes: str | None = None


class SerialTitleResponse(BaseModel):
    id: int
    title: str
    catalog_item_id: int | None
    issn_print: str | None
    issn_electronic: str | None
    publisher: str | None
    country_of_publication: str | None
    language: str | None
    frequency: str
    is_active: bool
    ceased_date: date | None
    preceding_title_id: int | None
    succeeding_title_id: int | None
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    active_subscription_count: int | None = None

    class Config:
        from_attributes = True


class SerialTitleListResponse(BaseModel):
    items: list[SerialTitleResponse]
    total: int
    page: int
    per_page: int


# -- Prediction Pattern -----------------------------------------------------

class PredictionPatternCreate(StrictInputSchema):
    frequency: str
    pattern_details: dict = {}
    volume_scheme: str = "annual"
    starting_volume: int | None = None
    starting_number: int | None = None
    numbers_per_volume: int | None = None
    designation_template: str | None = None
    effective_from: date
    effective_to: date | None = None


class PredictionPatternResponse(BaseModel):
    id: int
    serial_title_id: int
    frequency: str
    pattern_details: dict
    volume_scheme: str
    starting_volume: int | None
    starting_number: int | None
    numbers_per_volume: int | None
    designation_template: str | None
    effective_from: date
    effective_to: date | None
    is_active: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# -- Subscription -----------------------------------------------------------

class SerialSubscriptionCreate(StrictInputSchema):
    serial_title_id: int
    vendor_id: int | None = None
    fund_id: int | None = None
    branch_id: int | None = None
    subscription_number: str | None = Field(None, max_length=100)
    copies_ordered: int = 1
    start_date: date
    end_date: date
    cost: MoneyDecimal | None = None
    notes: str | None = None


class SerialSubscriptionUpdate(StrictInputSchema):
    vendor_id: int | None = None
    fund_id: int | None = None
    branch_id: int | None = None
    subscription_number: str | None = None
    copies_ordered: int | None = None
    end_date: date | None = None
    cost: MoneyDecimal | None = None
    renewal_status: str | None = None
    cancelled_date: date | None = None
    cancellation_reason: str | None = None
    notes: str | None = None


class SerialSubscriptionResponse(BaseModel):
    id: int
    serial_title_id: int
    serial_title_name: str | None = None
    vendor_id: int | None
    vendor_name: str | None = None
    fund_id: int | None
    branch_id: int | None
    branch_name: str | None = None
    subscription_number: str | None
    copies_ordered: int
    start_date: date
    end_date: date
    cost: MoneyDecimal | None
    renewal_status: str
    cancelled_date: date | None
    cancellation_reason: str | None
    notes: str | None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class SerialSubscriptionListResponse(BaseModel):
    items: list[SerialSubscriptionResponse]
    total: int
    page: int
    per_page: int


# -- Issue ------------------------------------------------------------------

class SerialIssueCheckinRequest(StrictInputSchema):
    issue_ids: list[int] = Field(..., min_length=1)
    received_date: date | None = None  # defaults to today
    notes: str | None = None


class SerialIssueResponse(BaseModel):
    id: int
    serial_title_id: int
    serial_title_name: str | None = None
    serial_subscription_id: int
    volume: str | None
    number: str | None
    designation: str | None
    designation_override: str | None
    expected_date: date
    received_date: date | None
    received_by_name: str | None = None
    status: str
    is_combined: bool
    combined_designation: str | None
    is_supplement: bool
    supplement_title: str | None
    barcode: str | None
    branch_name: str | None = None
    notes: str | None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class SerialIssueListResponse(BaseModel):
    items: list[SerialIssueResponse]
    total: int
    page: int
    per_page: int


# -- Claim ------------------------------------------------------------------

class SerialClaimCreate(StrictInputSchema):
    claim_type: str = "not_received"
    claim_number: str | None = None
    notes: str | None = None


class SerialClaimUpdateResponse(BaseModel):
    response: str | None = None
    vendor_response_date: date | None = None
    replacement_expected_date: date | None = None
    resolution: str | None = None
    resolved_date: date | None = None


class SerialClaimResponse(BaseModel):
    id: int
    serial_issue_id: int
    claim_date: date
    claim_type: str
    claim_number: str | None
    claimed_by_name: str | None = None
    response: str | None
    vendor_response_date: date | None
    replacement_expected_date: date | None
    resolution: str | None
    resolved_date: date | None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# -- Dashboard --------------------------------------------------------------

class SerialsDashboardResponse(BaseModel):
    expected_today: int
    overdue_count: int
    claimed_count: int
    received_this_week: int
    expiring_subscriptions: int  # within 30 days
    total_active_titles: int
    total_active_subscriptions: int
