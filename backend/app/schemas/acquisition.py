# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema

from ..models.acquisition import (FundStatus, PurchaseOrderStatus,
                                  SelectionPriority, SelectionSource)

# ============ Paginated List Response Schemas ============


class FundListResponse(BaseModel):
    items: list["FundResponse"]
    total: int
    page: int
    per_page: int


class FundRolloverResponse(BaseModel):
    message: str
    funds_created: int


class VendorListResponse(BaseModel):
    items: list["VendorResponse"]
    total: int
    page: int
    per_page: int


class SelectionItemListResponse(BaseModel):
    items: list["SelectionItemResponse"]
    total: int
    page: int
    per_page: int


class PurchaseOrderListResponse(BaseModel):
    items: list["PurchaseOrderResponse"]
    total: int
    page: int
    per_page: int


# ============ Fund Schemas ============


class FundBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: str | None = None
    fiscal_year: int
    allocated_amount: MoneyDecimal = Field(Decimal("0.00"), ge=0)


class FundCreate(StrictInputSchema, FundBase):
    pass


class FundUpdate(StrictInputSchema):
    code: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    fiscal_year: int | None = None
    allocated_amount: MoneyDecimal | None = Field(None, ge=0)
    status: FundStatus | None = None


class FundResponse(FundBase):
    id: int
    encumbered_amount: MoneyDecimal
    spent_amount: MoneyDecimal
    available_amount: MoneyDecimal
    status: str
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class FundRolloverRequest(StrictInputSchema):
    source_fiscal_year: int
    target_fiscal_year: int
    carry_forward_unspent: bool = False


# ============ Vendor Schemas ============


class VendorBase(BaseModel):
    name: str = Field(..., max_length=255)
    contact_name: str | None = Field(None, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    address: str | None = None
    account_number: str | None = Field(None, max_length=100)
    notes: str | None = None
    code: str | None = Field(None, max_length=50)
    website: str | None = Field(None, max_length=255)
    discount_percentage: MoneyDecimal | None = Field(None, ge=0, le=100)


class VendorCreate(StrictInputSchema, VendorBase):
    pass


class VendorUpdate(StrictInputSchema):
    name: str | None = Field(None, max_length=255)
    contact_name: str | None = Field(None, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    address: str | None = None
    account_number: str | None = Field(None, max_length=100)
    notes: str | None = None
    is_active: bool | None = None
    code: str | None = Field(None, max_length=50)
    website: str | None = Field(None, max_length=255)
    discount_percentage: MoneyDecimal | None = Field(None, ge=0, le=100)


class VendorResponse(VendorBase):
    id: int
    is_active: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ Selection List Schemas ============


class SelectionItemBase(BaseModel):
    title: str = Field(..., max_length=500)
    author: str | None = Field(None, max_length=255)
    isbn: str | None = Field(None, max_length=20)
    cover_url: str | None = None
    estimated_price: MoneyDecimal | None = None
    notes: str | None = None
    priority: SelectionPriority = SelectionPriority.MEDIUM


class SelectionItemCreate(StrictInputSchema, SelectionItemBase):
    source: SelectionSource = SelectionSource.MANUAL
    source_id: str | None = None
    status: str | None = None
    purchase_request_id: int | None = None


class SelectionItemResponse(SelectionItemBase):
    id: int
    source: SelectionSource
    source_id: str | None
    priority: str = "medium"
    requested_by_id: int
    requested_by_name: str | None = None
    status: str = "pending"
    purchase_request_id: int | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ConvertToPoRequest(StrictInputSchema):
    selection_item_ids: list[int]
    vendor_id: int | None = None
    fund_id: int | None = None


# ============ Purchase Order Item Schemas ============


class POItemBase(BaseModel):
    title: str = Field(..., max_length=500)
    author: str | None = Field(None, max_length=255)
    isbn: str | None = Field(None, max_length=50)
    quantity: int = Field(1, ge=1)
    unit_price: MoneyDecimal = Field(Decimal("0.00"), ge=0)
    notes: str | None = None


class POItemCreate(StrictInputSchema, POItemBase):
    pass


class POItemUpdate(StrictInputSchema):
    title: str | None = Field(None, max_length=500)
    author: str | None = Field(None, max_length=255)
    isbn: str | None = Field(None, max_length=50)
    quantity: int | None = Field(None, ge=1)
    unit_price: MoneyDecimal | None = Field(None, ge=0)
    notes: str | None = None


class POItemResponse(POItemBase):
    id: int
    purchase_order_id: int
    received_quantity: int
    line_total: MoneyDecimal
    is_fully_received: bool
    catalog_item_id: int | None
    backordered_quantity: int | None = None
    expected_ship_date: date | None = None
    last_status_at: datetime | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ Purchase Order Schemas ============


class PurchaseOrderBase(BaseModel):
    vendor_id: int | None = None
    fund_id: int | None = None
    order_date: date | None = None
    expected_delivery: date | None = None
    notes: str | None = None


class PurchaseOrderCreate(StrictInputSchema, PurchaseOrderBase):
    items: list[POItemCreate] | None = None


class PurchaseOrderUpdate(StrictInputSchema):
    vendor_id: int | None = None
    fund_id: int | None = None
    order_date: date | None = None
    expected_delivery: date | None = None
    notes: str | None = None


class PurchaseOrderResponse(PurchaseOrderBase):
    id: int
    po_number: str
    status: PurchaseOrderStatus
    total_amount: MoneyDecimal
    total_items: int
    has_backorders: bool
    vendor_name: str | None
    fund_name: str | None
    approved_by_id: int | None
    approved_at: datetime | None
    rejection_notes: str | None
    actual_delivery: date | None
    created_by_id: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class PurchaseOrderDetail(PurchaseOrderResponse):
    items: list[POItemResponse]


class ApprovalRequest(StrictInputSchema):
    pass  # No body needed, uses current user


class RejectionRequest(StrictInputSchema):
    notes: str = Field(..., min_length=1)


# ============ Collection Development Intelligence Schemas ============


class CollectionInsightItem(BaseModel):
    key: str
    title: str
    author: str | None = None
    isbn: str | None = None
    reason: str
    score: float = 0
    source: str
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class CollectionIntelligenceReport(BaseModel):
    patrons_searched_missing: list[CollectionInsightItem]
    popular_titles_not_owned: list[CollectionInsightItem]
    series_missing_volumes: list[CollectionInsightItem]
    high_hold_ratio_items: list[CollectionInsightItem]
    outdated_subjects: list[CollectionInsightItem]
    peer_library_gaps: list[CollectionInsightItem]
    missing_award_winners: list[CollectionInsightItem]
    trending_topics_without_coverage: list[CollectionInsightItem]


class ReceiveItemsRequest(StrictInputSchema):
    items: list[dict]  # [{item_id: int, received_quantity: int}]


# ============ External Search Schemas ============


class ExternalSearchResult(BaseModel):
    source: SelectionSource
    source_id: str
    title: str
    author: str | None = None
    isbn: str | None = None
    cover_url: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    description: str | None = None


class ExternalSearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[ExternalSearchResult]


# ============ Budget Validation Schemas ============


class FundSuggestion(BaseModel):
    id: int
    code: str
    name: str
    available_amount: MoneyDecimal


class BudgetValidationResponse(BaseModel):
    is_valid: bool
    fund_id: int | None
    fund_code: str | None
    fund_name: str | None
    available_amount: MoneyDecimal
    order_total: MoneyDecimal
    remaining_after_order: MoneyDecimal
    usage_percentage: float  # How much of available would be used (0-100+)
    warning_level: str  # "none", "warning" (>75%), "danger" (>100%)
    message: str
    exceeds_budget_by: MoneyDecimal | None = None  # Amount over budget if any
    suggested_funds: list[FundSuggestion] = []  # Alternative funds with enough balance


# ============ Batch Operation Schemas ============


class BatchApproveRequest(StrictInputSchema):
    po_ids: list[int] = Field(..., min_length=1, description="List of PO IDs to approve")


class BatchApproveResult(BaseModel):
    po_id: int
    po_number: str
    success: bool
    error: str | None = None
    total_amount: MoneyDecimal | None = None


class BatchApproveResponse(BaseModel):
    total_requested: int
    approved_count: int
    failed_count: int
    total_amount_approved: MoneyDecimal
    results: list[BatchApproveResult]


class BatchAddToPoRequest(StrictInputSchema):
    selection_item_ids: list[int] = Field(..., min_length=1, description="Selection item IDs to add")
    purchase_order_id: int | None = Field(None, description="Existing PO ID, or None to create new")
    vendor_id: int | None = Field(None, description="Vendor ID if creating new PO")
    fund_id: int | None = Field(None, description="Fund ID if creating new PO")


class BatchAddToPoResponse(BaseModel):
    purchase_order_id: int
    po_number: str
    items_added: int
    items_failed: int
    failed_items: list[dict] | None = None


class BatchReceiveAllRequest(StrictInputSchema):
    pass  # No body needed, just PO ID in URL


class BatchUpdatePriorityRequest(StrictInputSchema):
    item_ids: list[int] = Field(..., min_length=1, description="Selection item IDs to update")
    priority: SelectionPriority


class BatchUpdatePriorityResponse(BaseModel):
    updated_count: int
    failed_count: int
    failed_items: list[dict] | None = None


class BatchDeleteSelectionRequest(StrictInputSchema):
    item_ids: list[int] = Field(..., min_length=1, description="Selection item IDs to delete")


class BatchDeleteSelectionResponse(BaseModel):
    deleted_count: int
    failed_count: int
    failed_items: list[dict] | None = None


# ============ Order Template Schemas ============


class TemplateItemBase(BaseModel):
    title: str = Field(..., max_length=500)
    author: str | None = Field(None, max_length=255)
    isbn: str | None = Field(None, max_length=50)
    quantity: int = Field(1, ge=1)
    unit_price: MoneyDecimal | None = None
    notes: str | None = None


class OrderTemplateBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    vendor_id: int | None = None
    fund_id: int | None = None
    is_shared: bool = False


class OrderTemplateCreate(StrictInputSchema, OrderTemplateBase):
    template_items: list[TemplateItemBase] | None = None


class OrderTemplateUpdate(StrictInputSchema):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    vendor_id: int | None = None
    fund_id: int | None = None
    is_shared: bool | None = None
    template_items: list[TemplateItemBase] | None = None


class OrderTemplateResponse(OrderTemplateBase):
    id: int
    created_by_id: int
    created_by_name: str | None = None
    vendor_name: str | None = None
    fund_name: str | None = None
    template_items: list[TemplateItemBase]
    item_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class OrderTemplateDetail(OrderTemplateResponse):
    pass


class CreatePOFromTemplateRequest(StrictInputSchema):
    vendor_id: int | None = None  # Override template vendor
    fund_id: int | None = None  # Override template fund
    notes: str | None = None


class SaveAsTemplateRequest(StrictInputSchema):
    name: str = Field(..., max_length=255)
    description: str | None = None
    is_shared: bool = False


class ReorderPORequest(StrictInputSchema):
    vendor_id: int | None = None  # Override original vendor
    fund_id: int | None = None  # Override original fund
    notes: str | None = None


class AddInsightToSelectionRequest(StrictInputSchema):
    title: str = Field(..., max_length=500)
    author: str | None = Field(None, max_length=255)
    isbn: str | None = Field(None, max_length=20)
    estimated_price: MoneyDecimal | None = None
    notes: str | None = None
    priority: SelectionPriority = SelectionPriority.MEDIUM
    source: SelectionSource = SelectionSource.MANUAL
    source_id: str | None = None
