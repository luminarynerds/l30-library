# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema

from ..models.edi import (
    EDIInvoiceStatus,
    EDIMessageType,
    EDIStandard,
    EDITransactionStatus,
    TransportProtocol,
)


# ============ Vendor EDI Profile Schemas ============


class VendorEDIProfileBase(BaseModel):
    is_enabled: bool = False
    edi_standard: EDIStandard = EDIStandard.EDIFACT

    # Identifiers
    sender_id: str | None = Field(None, max_length=35)
    sender_qualifier: str = Field("ZZ", max_length=4)
    receiver_id: str | None = Field(None, max_length=35)
    receiver_qualifier: str = Field("ZZ", max_length=4)

    # Transport Configuration
    transport_protocol: TransportProtocol = TransportProtocol.SFTP
    transport_host: str | None = Field(None, max_length=255)
    transport_port: int | None = None
    transport_username: str | None = Field(None, max_length=255)
    transport_directory_outbound: str = "/outbound"
    transport_directory_inbound: str = "/inbound"

    # Message Type Support
    supports_orders: bool = True
    supports_ordrsp: bool = True
    supports_desadv: bool = True
    supports_invoic: bool = True

    # Retry Configuration
    max_retries: int = Field(3, ge=0, le=10)
    retry_interval_minutes: int = Field(60, ge=5, le=1440)

    # Auto-processing settings
    auto_send_orders: bool = False
    auto_process_responses: bool = True
    auto_approve_invoices: bool = False
    invoice_tolerance_percent: MoneyDecimal = Field(
        default=Decimal("5.00"), ge=0, le=100
    )

    # Test mode
    is_test_mode: bool = True


class VendorEDIProfileCreate(StrictInputSchema, VendorEDIProfileBase):
    vendor_id: int
    transport_password: str | None = None
    ssh_private_key: str | None = None
    vendor_settings: dict | None = None


class VendorEDIProfileUpdate(StrictInputSchema):
    is_enabled: bool | None = None
    edi_standard: EDIStandard | None = None

    sender_id: str | None = Field(None, max_length=35)
    sender_qualifier: str | None = Field(None, max_length=4)
    receiver_id: str | None = Field(None, max_length=35)
    receiver_qualifier: str | None = Field(None, max_length=4)

    transport_protocol: TransportProtocol | None = None
    transport_host: str | None = Field(None, max_length=255)
    transport_port: int | None = None
    transport_username: str | None = Field(None, max_length=255)
    transport_password: str | None = None
    transport_directory_outbound: str | None = None
    transport_directory_inbound: str | None = None
    ssh_private_key: str | None = None

    supports_orders: bool | None = None
    supports_ordrsp: bool | None = None
    supports_desadv: bool | None = None
    supports_invoic: bool | None = None

    max_retries: int | None = Field(None, ge=0, le=10)
    retry_interval_minutes: int | None = Field(None, ge=5, le=1440)

    auto_send_orders: bool | None = None
    auto_process_responses: bool | None = None
    auto_approve_invoices: bool | None = None
    invoice_tolerance_percent: MoneyDecimal | None = Field(None, ge=0, le=100)

    is_test_mode: bool | None = None
    vendor_settings: dict | None = None


class VendorEDIProfileResponse(VendorEDIProfileBase):
    id: int
    vendor_id: int
    vendor_name: str | None = None
    has_password: bool = False
    has_ssh_key: bool = False
    vendor_settings: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_transmission_at: datetime | None = None
    last_successful_transmission_at: datetime | None = None

    class Config:
        from_attributes = True


# ============ EDI Transaction Schemas ============


class EDITransactionBase(BaseModel):
    message_type: EDIMessageType
    direction: str  # "outbound" or "inbound"


class EDITransactionResponse(EDITransactionBase):
    id: int
    vendor_edi_profile_id: int | None
    purchase_order_id: int | None
    interchange_control_number: str | None
    message_reference_number: str | None
    status: EDITransactionStatus
    filename: str | None
    retry_count: int
    next_retry_at: datetime | None
    last_error: str | None
    created_at: datetime | None = None
    sent_at: datetime | None
    received_at: datetime | None
    processed_at: datetime | None

    # Related info
    vendor_name: str | None = None
    po_number: str | None = None

    class Config:
        from_attributes = True


class EDITransactionDetail(EDITransactionResponse):
    raw_message: str | None = None
    parsed_data: dict | None = None


# ============ EDI Invoice Schemas ============


class EDIInvoiceLineItem(BaseModel):
    line_number: int
    isbn: str | None = None
    title: str | None = None
    quantity: int
    unit_price: MoneyDecimal
    line_total: MoneyDecimal
    po_item_id: int | None = None
    match_status: str | None = None  # "matched", "unmatched", "price_variance"


class EDIInvoiceBase(BaseModel):
    invoice_number: str
    invoice_date: datetime | None = None
    due_date: datetime | None = None
    subtotal: MoneyDecimal | None = None
    tax_amount: MoneyDecimal = Decimal("0.00")
    shipping_amount: MoneyDecimal = Decimal("0.00")
    discount_amount: MoneyDecimal = Decimal("0.00")
    total_amount: MoneyDecimal
    currency_code: str = "USD"


class EDIInvoiceResponse(EDIInvoiceBase):
    id: int
    edi_transaction_id: int | None
    purchase_order_id: int | None
    vendor_id: int | None
    status: EDIInvoiceStatus
    po_total: MoneyDecimal | None
    variance_amount: MoneyDecimal | None
    variance_reason: str | None
    matched_line_items: int
    total_line_items: int
    approved_by_id: int | None
    approved_at: datetime | None
    rejection_reason: str | None
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None

    # Related info
    vendor_name: str | None = None
    po_number: str | None = None
    approved_by_name: str | None = None

    class Config:
        from_attributes = True


class EDIInvoiceDetail(EDIInvoiceResponse):
    line_items: list[EDIInvoiceLineItem] = []


class InvoiceApprovalRequest(StrictInputSchema):
    notes: str | None = None


class InvoiceDisputeRequest(StrictInputSchema):
    reason: str = Field(..., min_length=1)


# ============ EDI Shipment Notice Schemas ============


class ShippedItem(BaseModel):
    isbn: str | None = None
    title: str | None = None
    quantity_shipped: int
    po_item_id: int | None = None


class EDIShipmentNoticeResponse(BaseModel):
    id: int
    edi_transaction_id: int | None
    purchase_order_id: int | None
    vendor_id: int | None
    shipment_number: str | None
    ship_date: datetime | None
    expected_delivery_date: datetime | None
    carrier_name: str | None
    carrier_code: str | None
    tracking_number: str | None
    package_count: int
    total_weight: MoneyDecimal | None
    weight_unit: str
    total_items_shipped: int
    is_processed: bool
    processed_at: datetime | None
    created_at: datetime | None = None
    # Related info
    vendor_name: str | None = None
    po_number: str | None = None

    class Config:
        from_attributes = True


class EDIShipmentNoticeDetail(EDIShipmentNoticeResponse):
    shipped_items: list[ShippedItem] = []


# ============ EDI Order Response Schemas ============


class OrderResponseLineItem(BaseModel):
    line_number: int
    isbn: str | None = None
    title: str | None = None
    response_code: str  # AC=Accepted, BP=Backorder, RJ=Rejected
    response_description: str | None = None
    quantity_ordered: int
    quantity_accepted: int | None = None
    quantity_backordered: int | None = None
    expected_ship_date: datetime | None = None
    po_item_id: int | None = None


class EDIOrderResponseResponse(BaseModel):
    id: int
    edi_transaction_id: int | None
    purchase_order_id: int | None
    vendor_id: int | None
    vendor_order_number: str | None
    response_date: datetime | None
    response_code: str | None
    response_description: str | None
    items_accepted: int
    items_rejected: int
    items_backordered: int
    items_substituted: int
    expected_ship_date: datetime | None
    expected_delivery_date: datetime | None
    is_processed: bool
    processed_at: datetime | None
    created_at: datetime | None = None
    # Related info
    vendor_name: str | None = None
    po_number: str | None = None

    class Config:
        from_attributes = True


class EDIOrderResponseDetail(EDIOrderResponseResponse):
    line_items: list[OrderResponseLineItem] = []


# ============ Send Order Request Schema ============


class SendEDIOrderRequest(StrictInputSchema):
    purchase_order_id: int


class SendEDIOrderResponse(BaseModel):
    success: bool
    transaction_id: int | None = None
    interchange_control_number: str | None = None
    message: str
    error: str | None = None


# ============ Test Connection Schema ============


class TestConnectionRequest(StrictInputSchema):
    vendor_id: int


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    connectivity_status: str  # "connected" or "disconnected"
    latency_ms: float | None = None
    authentication_result: str | None = None
    details: dict | None = None


# ============ Process Inbound Messages Schema ============


class ProcessInboundRequest(StrictInputSchema):
    vendor_id: int | None = None  # None = process all


class ProcessInboundResponse(BaseModel):
    vendors_processed: int
    files_processed: int
    transactions_created: int
    errors: list[dict] = []


# ============ Retry Transaction Schema ============


class RetryTransactionRequest(StrictInputSchema):
    transaction_id: int


class RetryTransactionResponse(BaseModel):
    success: bool
    transaction_id: int
    new_status: EDITransactionStatus
    message: str
    error: str | None = None


# ============ EDI Statistics Schema ============


class EDIStatistics(BaseModel):
    total_transactions: int
    pending_transactions: int
    failed_transactions: int
    successful_transactions: int
    pending_invoices: int
    disputed_invoices: int
    total_invoice_amount: MoneyDecimal
    average_processing_time_seconds: float | None = None
    last_24h_transactions: int
    by_message_type: dict[str, int] = {}
    by_vendor: dict[str, int] = {}


# ============ Reconciliation Schemas ============


class ReconciliationResult(BaseModel):
    invoice_id: int
    purchase_order_id: int | None
    status: str  # "matched", "partial_match", "unmatched", "disputed"
    matched_items: int
    total_items: int
    po_total: MoneyDecimal | None
    invoice_total: MoneyDecimal
    variance_amount: MoneyDecimal | None
    variance_percent: float | None
    discrepancies: list[dict] = []
    recommendations: list[str] = []


class BatchReconciliationRequest(StrictInputSchema):
    invoice_ids: list[int] = Field(default=[], description="Specific invoices to reconcile (empty = all pending)")


class BatchReconciliationResponse(BaseModel):
    total_processed: int
    matched: int
    partial_match: int
    disputed: int
    errors: int
    results: list[ReconciliationResult] = []


# ============ Paginated List Response Schemas ============


class EDITransactionListResponse(BaseModel):
    items: list[EDITransactionResponse]
    total: int
    page: int
    per_page: int
    pages: int


class EDIInvoiceListResponse(BaseModel):
    items: list[EDIInvoiceResponse]
    total: int
    page: int
    per_page: int
    pages: int


class EDIOrderResponseListResponse(BaseModel):
    items: list[EDIOrderResponseResponse]
    total: int
    page: int
    per_page: int
    pages: int


class EDIShipmentNoticeListResponse(BaseModel):
    items: list[EDIShipmentNoticeResponse]
    total: int
    page: int
    per_page: int
    pages: int
