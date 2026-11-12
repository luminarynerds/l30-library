# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema

from ..models.purchase_request import PurchaseRequestStatus, RequestMaterialType


# ============ Patron-Facing Schemas ============


class PurchaseRequestCreate(StrictInputSchema):
    title: str = Field(..., max_length=500, description="Title of the requested material")
    author: str | None = Field(None, max_length=255)
    isbn: str | None = Field(None, max_length=20)
    material_type: RequestMaterialType = RequestMaterialType.BOOK
    publisher: str | None = Field(None, max_length=255)
    publication_year: int | None = Field(None, ge=1800, le=2100)
    patron_notes: str | None = Field(None, max_length=1000, description="Why you want this item")


class PurchaseRequestResponse(BaseModel):
    id: int
    title: str
    author: str | None
    isbn: str | None
    material_type: str
    publisher: str | None
    publication_year: int | None
    patron_notes: str | None
    status: str
    decline_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class PurchaseRequestListResponse(BaseModel):
    items: list[PurchaseRequestResponse]
    total: int
    page: int
    per_page: int


# ============ Staff-Facing Schemas ============


class PurchaseRequestStaffResponse(BaseModel):
    id: int
    title: str
    author: str | None
    isbn: str | None
    material_type: str
    publisher: str | None
    publication_year: int | None
    patron_notes: str | None
    status: str

    # Patron info
    patron_id: int
    patron_name: str | None = None

    # Review info
    reviewed_by_id: int | None
    reviewer_name: str | None = None
    reviewed_at: datetime | None
    staff_notes: str | None
    decline_reason: str | None

    # Duplicate detection
    duplicate_of_catalog_id: int | None
    duplicate_check_done: bool
    duplicate_title: str | None = None  # Title of matching catalog item

    # Review source data
    review_source_rating: float | None
    review_source_data: str | None
    review_source_checked: bool

    # Order link
    purchase_order_id: int | None

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class PurchaseRequestStaffListResponse(BaseModel):
    items: list[PurchaseRequestStaffResponse]
    total: int
    page: int
    per_page: int


class ApproveRequestBody(StrictInputSchema):
    staff_notes: str | None = Field(None, max_length=1000)


class DeclineRequestBody(StrictInputSchema):
    decline_reason: str = Field(..., min_length=1, max_length=1000, description="Reason shown to patron")
    staff_notes: str | None = Field(None, max_length=1000)


class BulkActionRequest(StrictInputSchema):
    request_ids: list[int] = Field(..., min_length=1, description="IDs of requests to process")


class BulkApproveRequest(BulkActionRequest, StrictInputSchema):
    staff_notes: str | None = Field(None, max_length=1000)


class BulkDeclineRequest(BulkActionRequest, StrictInputSchema):
    decline_reason: str = Field(..., min_length=1, max_length=1000)
    staff_notes: str | None = Field(None, max_length=1000)


class BulkActionResult(BaseModel):
    request_id: int
    success: bool
    error: str | None = None


class BulkActionResponse(BaseModel):
    total_requested: int
    succeeded: int
    failed: int
    results: list[BulkActionResult]


class LinkToOrderRequest(StrictInputSchema):
    purchase_order_id: int


class FulfillmentStatsResponse(BaseModel):
    total_requests: int
    pending_count: int
    under_review_count: int
    approved_count: int
    ordered_count: int
    received_count: int
    declined_count: int
    cancelled_count: int
    fulfillment_rate: float  # Percentage of non-cancelled requests that reached received
    avg_days_to_review: float | None
    avg_days_to_fulfill: float | None


# ============ Decline Reason Template Schemas ============


class DeclineReasonTemplateCreate(StrictInputSchema):
    label: str = Field(..., max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)


class DeclineReasonTemplateUpdate(StrictInputSchema):
    label: str | None = Field(None, max_length=100)
    message: str | None = Field(None, max_length=2000)
    is_active: bool | None = None


class DeclineReasonTemplateResponse(BaseModel):
    id: int
    label: str
    message: str
    is_active: bool
    usage_count: int
    created_by_id: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ Duplicate Check Schemas ============


class DuplicateCheckResult(BaseModel):
    has_duplicate: bool
    catalog_item_id: int | None = None
    catalog_title: str | None = None
    catalog_author: str | None = None
    match_type: str | None = None  # "isbn", "title_author"
