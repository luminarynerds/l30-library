# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema

from ..models.rfid import (
    RFIDProtocol,
    RFIDReaderStatus,
    RFIDReaderType,
    RFIDSessionType,
    SecurityAlertType,
)


# ============ RFID Reader Schemas ============


class RFIDReaderBase(BaseModel):
    name: str = Field(..., max_length=100)
    serial_number: str = Field(..., max_length=100)
    location: str | None = Field(None, max_length=200)
    reader_type: RFIDReaderType
    protocol: RFIDProtocol = RFIDProtocol.SIP2
    ip_address: str | None = Field(None, max_length=45)
    port: int | None = Field(None, ge=1, le=65535)
    connection_string: str | None = None
    antenna_count: int = Field(default=1, ge=1, le=8)
    power_level: float | None = Field(None, ge=-30, le=30)
    read_interval_ms: int = Field(default=100, ge=10, le=5000)


class RFIDReaderCreate(StrictInputSchema, RFIDReaderBase):
    username: str | None = Field(None, max_length=100)
    password: str | None = Field(None, max_length=255)
    config_metadata: dict | None = None


class RFIDReaderUpdate(StrictInputSchema):
    name: str | None = Field(None, max_length=100)
    location: str | None = Field(None, max_length=200)
    protocol: RFIDProtocol | None = None
    ip_address: str | None = Field(None, max_length=45)
    port: int | None = Field(None, ge=1, le=65535)
    connection_string: str | None = None
    username: str | None = Field(None, max_length=100)
    password: str | None = Field(None, max_length=255)
    antenna_count: int | None = Field(None, ge=1, le=8)
    power_level: float | None = Field(None, ge=-30, le=30)
    read_interval_ms: int | None = Field(None, ge=10, le=5000)
    config_metadata: dict | None = None
    is_active: bool | None = None


class RFIDReaderResponse(RFIDReaderBase):
    id: int
    status: RFIDReaderStatus
    last_heartbeat: datetime | None
    last_error: str | None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class RFIDReaderStatusUpdate(StrictInputSchema):
    status: RFIDReaderStatus
    last_error: str | None = None


# ============ RFID Tag Schemas ============


class RFIDTagBase(BaseModel):
    tag_id: str = Field(..., max_length=64)
    item_barcode: str = Field(..., max_length=50)
    security_bit: bool = True
    afi_byte: str | None = Field(None, max_length=4)
    eas_enabled: bool = True
    tag_type: str | None = Field(None, max_length=50)
    memory_size: int | None = Field(None, ge=0)
    manufacturer: str | None = Field(None, max_length=100)


class RFIDTagCreate(StrictInputSchema, RFIDTagBase):
    programmed_by_reader_id: int | None = None
    tag_data: dict | None = None

    @field_validator("tag_id")
    @classmethod
    def validate_tag_id(cls, v: str) -> str:
        # Tag ID should be hexadecimal
        try:
            int(v, 16)
        except ValueError:
            raise ValueError("tag_id must be a valid hexadecimal string") from None
        return v.upper()


class RFIDTagUpdate(StrictInputSchema):
    security_bit: bool | None = None
    afi_byte: str | None = Field(None, max_length=4)
    eas_enabled: bool | None = None
    tag_data: dict | None = None
    is_active: bool | None = None
    deactivation_reason: str | None = Field(None, max_length=255)


class RFIDTagResponse(RFIDTagBase):
    id: int
    programmed_at: datetime | None
    programmed_by_id: int | None
    programmed_by_reader_id: int | None
    last_read_at: datetime | None
    read_count: int
    tag_data: dict | None
    is_active: bool
    deactivated_at: datetime | None
    deactivation_reason: str | None
    created_at: datetime | None = None
    updated_at: datetime | None
    # Enriched fields
    item_title: str | None = None
    item_author: str | None = None

    class Config:
        from_attributes = True


class RFIDTagProgramRequest(StrictInputSchema):
    item_barcode: str = Field(..., max_length=50)
    reader_id: int
    tag_type: str | None = Field(None, max_length=50)
    include_item_data: bool = True  # Whether to write item data to tag


class RFIDTagProgramResponse(BaseModel):
    success: bool
    tag_id: str | None = None
    message: str
    tag: RFIDTagResponse | None = None


# ============ RFID Session Schemas ============


class RFIDSessionCreate(StrictInputSchema):
    session_type: RFIDSessionType
    reader_id: int
    patron_id: int | None = None  # For checkout/checkin sessions
    inventory_audit_id: int | None = None  # For inventory sessions
    target_location: str | None = Field(None, max_length=100)


class RFIDSessionResponse(BaseModel):
    id: int
    session_type: RFIDSessionType
    reader_id: int
    operator_id: int
    patron_id: int | None
    inventory_audit_id: int | None
    target_location: str | None
    started_at: datetime
    ended_at: datetime | None
    is_active: bool
    tags_scanned: int
    tags_processed: int
    tags_failed: int
    session_metadata: dict | None
    # Enriched
    reader_name: str | None = None
    operator_name: str | None = None
    patron_name: str | None = None

    class Config:
        from_attributes = True


class RFIDSessionSummary(BaseModel):
    session_id: int
    session_type: RFIDSessionType
    duration_seconds: int
    tags_scanned: int
    tags_processed: int
    tags_failed: int
    items_checked_out: int = 0
    items_checked_in: int = 0
    items_found: int = 0
    items_misplaced: int = 0


# ============ RFID Scan Schemas ============


class RFIDScanCreate(StrictInputSchema):
    tag_id: str = Field(..., max_length=64)
    signal_strength: float | None = Field(None, ge=-100, le=0)
    antenna_id: int | None = Field(None, ge=0)
    found_at_location: str | None = Field(None, max_length=100)


class RFIDScanResponse(BaseModel):
    id: int
    session_id: int
    tag_id: str
    rfid_tag_id: int | None
    item_barcode: str | None
    item_title: str | None
    processed: bool
    process_result: str | None
    error_message: str | None
    signal_strength: float | None
    antenna_id: int | None
    found_at_location: str | None
    expected_location: str | None
    is_misplaced: bool
    scanned_at: datetime
    processed_at: datetime | None

    class Config:
        from_attributes = True


class RFIDScanBatchRequest(StrictInputSchema):
    scans: list[RFIDScanCreate] = Field(..., min_length=1, max_length=100)


class RFIDScanBatchResponse(BaseModel):
    session_id: int
    scans_received: int
    scans_processed: int
    scans_failed: int
    results: list[RFIDScanResponse]


# ============ Batch Checkout Schemas ============


class BatchCheckoutRequest(StrictInputSchema):
    reader_id: int
    patron_id: int
    tag_ids: list[str] = Field(..., min_length=1, max_length=50)


class BatchCheckoutItemResult(BaseModel):
    tag_id: str
    item_barcode: str | None
    item_title: str | None
    success: bool
    message: str
    checkout_id: int | None = None
    due_date: datetime | None = None


class BatchCheckoutResponse(BaseModel):
    session_id: int
    patron_id: int
    total_items: int
    successful: int
    failed: int
    results: list[BatchCheckoutItemResult]


# ============ Batch Checkin Schemas ============


class BatchCheckinRequest(StrictInputSchema):
    reader_id: int
    tag_ids: list[str] = Field(..., min_length=1, max_length=50)


class BatchCheckinItemResult(BaseModel):
    tag_id: str
    item_barcode: str | None
    item_title: str | None
    success: bool
    message: str
    was_overdue: bool = False
    fine_amount: float | None = None
    next_hold_patron: str | None = None  # If item has holds waiting


class BatchCheckinResponse(BaseModel):
    session_id: int
    total_items: int
    successful: int
    failed: int
    items_with_holds: int
    items_with_fines: int
    results: list[BatchCheckinItemResult]


# ============ Security Alert Schemas ============


class SecurityAlertCreate(StrictInputSchema):
    reader_id: int
    alert_type: SecurityAlertType
    tag_id: str | None = Field(None, max_length=64)
    description: str | None = None
    signal_strength: float | None = None
    photo_url: str | None = None


class SecurityAlertResponse(BaseModel):
    id: int
    reader_id: int
    alert_type: SecurityAlertType
    tag_id: str | None
    item_barcode: str | None
    item_title: str | None
    description: str | None
    signal_strength: float | None
    photo_url: str | None
    is_resolved: bool
    resolved_at: datetime | None
    resolved_by_id: int | None
    resolution_notes: str | None
    created_at: datetime | None = None
    # Enriched
    reader_name: str | None = None
    reader_location: str | None = None
    resolved_by_name: str | None = None

    class Config:
        from_attributes = True


class SecurityAlertResolve(BaseModel):
    resolution_notes: str = Field(..., min_length=1, max_length=1000)


# ============ Inventory/Shelf Reading Schemas ============


class InventoryScanRequest(StrictInputSchema):
    reader_id: int
    inventory_audit_id: int | None = None  # Link to existing audit
    target_location: str | None = Field(None, max_length=100)
    create_audit: bool = False  # Create new audit if no ID provided
    audit_name: str | None = Field(None, max_length=255)


class ShelfReadRequest(StrictInputSchema):
    reader_id: int
    target_location: str = Field(..., max_length=100)


class ShelfReadResult(BaseModel):
    session_id: int
    location: str
    items_scanned: int
    items_in_correct_location: int
    items_misplaced: int
    items_not_in_catalog: int
    misplaced_items: list[dict]  # List of misplaced item details
    unknown_tags: list[str]  # Tags not in system


class MissingItemsRequest(StrictInputSchema):
    inventory_audit_id: int | None = None
    location_filter: str | None = Field(None, max_length=100)
    days_since_last_seen: int | None = Field(None, ge=1)


class MissingItemResponse(BaseModel):
    item_copy_id: int
    barcode: str
    title: str
    author: str | None
    expected_location: str | None
    last_seen_at: datetime | None
    last_seen_location: str | None
    days_missing: int | None
    tag_id: str | None
    checkout_status: str | None


# ============ Reader Command Schemas ============


class ReaderCommandRequest(StrictInputSchema):
    command: str = Field(..., max_length=50)  # read, write, security_on, security_off, etc.
    tag_id: str | None = Field(None, max_length=64)
    data: dict | None = None
    timeout_ms: int = Field(default=5000, ge=100, le=30000)


class ReaderCommandResponse(BaseModel):
    success: bool
    command: str
    response_data: dict | None = None
    error_message: str | None = None
    execution_time_ms: int


# ============ Dashboard/Stats Schemas ============


class RFIDDashboardStats(BaseModel):
    total_readers: int
    readers_online: int
    readers_offline: int
    readers_error: int
    total_tags: int
    active_tags: int
    total_sessions_today: int
    items_processed_today: int
    security_alerts_today: int
    unresolved_alerts: int
    recent_sessions: list[RFIDSessionResponse]
    recent_alerts: list[SecurityAlertResponse]


# ============ Paginated List Response Schemas ============


class RFIDReaderListResponse(BaseModel):
    items: list[RFIDReaderResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "per_page": 20,
            }
        }


class RFIDTagListResponse(BaseModel):
    items: list[RFIDTagResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "per_page": 20,
            }
        }


class SecurityAlertListResponse(BaseModel):
    items: list[SecurityAlertResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "per_page": 20,
            }
        }
