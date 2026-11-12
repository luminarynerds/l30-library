# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema

from ..models.print_notice import (
    PrintNoticeBatchStatus, PrintNoticeStatus, PrintNoticeType
)
from ..models.user import AddressStatus, NoticePreference


# ============================================================================
# Address Schemas
# ============================================================================

class AddressBase(BaseModel):
    address_line1: str = Field(..., max_length=100, description="Street address")
    address_line2: Optional[str] = Field(None, max_length=100, description="Apt, Suite, etc.")
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=2, description="2-letter state code")
    zip_code: str = Field(..., max_length=10, description="ZIP or ZIP+4")
    country: str = Field(default="USA", max_length=50)


class AddressValidationRequest(StrictInputSchema, AddressBase):
    pass


class AddressValidationResponse(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    normalized_address: Optional[AddressBase] = None


class PatronAddressUpdate(StrictInputSchema, AddressBase):
    notice_preference: Optional[NoticePreference] = None


# ============================================================================
# Print Notice Schemas
# ============================================================================

class PrintNoticeBase(BaseModel):
    notice_type: PrintNoticeType
    subject: str = Field(..., max_length=255)
    body_html: Optional[str] = None
    context_data: Optional[dict] = None
    scheduled_for: Optional[datetime] = None


class PrintNoticeCreate(StrictInputSchema):
    patron_id: int
    notice_type: PrintNoticeType
    subject: str = Field(..., max_length=255)
    body_html: Optional[str] = ""
    context_data: Optional[dict] = None
    checkout_id: Optional[int] = None
    hold_id: Optional[int] = None
    fine_id: Optional[int] = None
    scheduled_for: Optional[datetime] = None


class PrintNoticeOverdueCreate(StrictInputSchema):
    patron_id: int
    checkout_ids: list[int] = Field(..., min_length=1)


class PrintNoticeFineCreate(StrictInputSchema):
    patron_id: int
    fine_ids: list[int] = Field(..., min_length=1)


class PrintNoticeHoldReadyCreate(StrictInputSchema):
    patron_id: int
    hold_id: int


class PrintNoticeAccountExpiringCreate(StrictInputSchema):
    patron_id: int
    expiration_date: datetime


class PrintNoticeResponse(BaseModel):
    id: int
    patron_id: int
    notice_type: PrintNoticeType
    status: PrintNoticeStatus
    batch_id: Optional[int] = None
    merge_key: Optional[str] = None
    recipient_name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    country: str
    subject: str
    context_data: Optional[dict] = None
    checkout_id: Optional[int] = None
    hold_id: Optional[int] = None
    fine_id: Optional[int] = None
    pdf_file_path: Optional[str] = None
    pdf_generated_at: Optional[datetime] = None
    print_cost: MoneyDecimal
    postage_cost: MoneyDecimal
    total_cost: MoneyDecimal
    pages: int
    scheduled_for: Optional[datetime] = None
    printed_at: Optional[datetime] = None
    mailed_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    return_reason: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PrintNoticeListResponse(BaseModel):
    items: list[PrintNoticeResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Print Notice Batch Schemas
# ============================================================================

class PrintNoticeBatchCreate(StrictInputSchema):
    name: Optional[str] = Field(None, max_length=200)
    notice_types: Optional[list[PrintNoticeType]] = None
    auto_close_hours: Optional[int] = Field(None, ge=1, le=168)


class PrintNoticeBatchAddNotices(BaseModel):
    notice_ids: list[int] = Field(..., min_length=1)


class PrintNoticeBatchResponse(BaseModel):
    id: int
    batch_number: str
    name: Optional[str] = None
    status: PrintNoticeBatchStatus
    notice_types: Optional[list[str]] = None
    auto_close_at: Optional[datetime] = None
    notice_count: int
    page_count: int
    total_print_cost: MoneyDecimal
    total_postage_cost: MoneyDecimal
    total_cost: MoneyDecimal
    merged_pdf_path: Optional[str] = None
    manifest_pdf_path: Optional[str] = None
    opened_at: datetime
    closed_at: Optional[datetime] = None
    printed_at: Optional[datetime] = None
    mailed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PrintNoticeBatchDetailResponse(PrintNoticeBatchResponse):
    notices: list[PrintNoticeResponse] = []


class PrintNoticeBatchListResponse(BaseModel):
    items: list[PrintNoticeBatchResponse]
    total: int
    limit: int
    offset: int


class BatchMergeResult(BaseModel):
    merged_count: int
    total_savings: float


class BatchPDFGenerationResult(BaseModel):
    generated_count: int
    total_pages: int
    manifest_path: str


# ============================================================================
# Returned Mail Schemas
# ============================================================================

class ReturnedMailRequest(StrictInputSchema):
    return_reason: str = Field(..., max_length=255)
    update_patron_address: bool = True


class ReturnedMailBulkRequest(StrictInputSchema):
    notice_ids: list[int] = Field(..., min_length=1)
    return_reason: str = Field(..., max_length=255)
    update_patron_addresses: bool = True


# ============================================================================
# Cost Configuration Schemas
# ============================================================================

class CostConfigUpdate(StrictInputSchema):
    cost_per_page: Optional[MoneyDecimal] = Field(None, ge=0)
    first_class_letter: Optional[MoneyDecimal] = Field(None, ge=0)
    first_class_large_envelope: Optional[MoneyDecimal] = Field(None, ge=0)
    presort_standard: Optional[MoneyDecimal] = Field(None, ge=0)
    large_envelope_page_threshold: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None


class CostConfigResponse(BaseModel):
    id: int
    cost_per_page: MoneyDecimal
    first_class_letter: MoneyDecimal
    first_class_large_envelope: MoneyDecimal
    presort_standard: MoneyDecimal
    large_envelope_page_threshold: int
    is_active: bool
    effective_from: datetime
    effective_to: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Notice History Schemas
# ============================================================================

class PrintNoticeHistoryResponse(BaseModel):
    id: int
    notice_id: Optional[int] = None
    batch_id: Optional[int] = None
    patron_id: Optional[int] = None
    patron_name: str
    patron_library_card: Optional[str] = None
    notice_type: PrintNoticeType
    subject: str
    mailing_address: str
    final_status: str
    mailed_at: Optional[datetime] = None
    returned: bool
    return_reason: Optional[str] = None
    total_cost: MoneyDecimal
    context_summary: Optional[str] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class PrintNoticeHistoryListResponse(BaseModel):
    items: list[PrintNoticeHistoryResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Cost Summary Schemas
# ============================================================================

class CostSummaryRequest(StrictInputSchema):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CostSummaryResponse(BaseModel):
    total_notices: int
    total_cost: float
    returned_count: int
    return_rate: float
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# ============================================================================
# Patron Notice Preference Schemas
# ============================================================================

class PatronNoticePreferenceUpdate(StrictInputSchema):
    notice_preference: NoticePreference
    address_line1: Optional[str] = Field(None, max_length=100)
    address_line2: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)


class PatronAddressStatusUpdate(StrictInputSchema):
    address_status: AddressStatus
    notes: Optional[str] = None
