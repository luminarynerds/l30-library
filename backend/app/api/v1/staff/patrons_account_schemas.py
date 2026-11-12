# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Schemas for staff patron account endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PasswordResetRequest(BaseModel):

    send_email: bool = True
    generate_temp_code: bool = False


class PasswordResetResponse(BaseModel):

    message: str
    email_sent: bool = False
    temp_code: Optional[str] = None
    last_password_change: Optional[datetime] = None


class DuplicatePatron(BaseModel):

    id: int
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    library_card: Optional[str] = None
    created_at: datetime
    is_active: bool
    match_type: str
    match_score: float
    total_checkouts: int = 0
    total_holds: int = 0
    fines_balance: Decimal = Decimal("0.00")


class DuplicateSearchResponse(BaseModel):

    patron_id: int
    duplicates: list[DuplicatePatron]
    search_criteria: dict


class MergeRequest(BaseModel):

    primary_patron_id: int = Field(..., description="The patron ID to keep")
    secondary_patron_id: int = Field(..., description="The patron ID to merge and delete")
    merge_checkouts: bool = True
    merge_holds: bool = True
    merge_fines: bool = True
    merge_history: bool = True
    merge_reading_lists: bool = True
    merge_favorites: bool = True


class MergePreview(BaseModel):

    primary_patron: dict
    secondary_patron: dict
    checkouts_to_transfer: int
    holds_to_transfer: int
    fines_to_transfer: int
    history_records_to_transfer: int
    reading_lists_to_transfer: int = 0
    favorites_to_transfer: int = 0


class MergeResponse(BaseModel):

    message: str
    merged_patron_id: int
    deleted_patron_id: int
    checkouts_transferred: int
    holds_transferred: int
    fines_transferred: int
    history_transferred: int
    reading_lists_transferred: int = 0
    favorites_transferred: int = 0
    audit_log_id: Optional[int] = None


class LibraryCardData(BaseModel):

    patron_id: int
    patron_name: str
    library_card_number: str
    barcode_value: str
    library_name: str
    library_logo_url: Optional[str] = None
    expiration_date: Optional[datetime] = None
    card_type: str = "standard"
    issue_date: datetime
    patron_photo_url: Optional[str] = None


class CardPrintedRequest(BaseModel):

    card_type: str = "standard"
    is_replacement: bool = False
    reason: Optional[str] = None


class CardPrintHistory(BaseModel):

    id: int
    printed_at: datetime
    card_type: str
    is_replacement: bool
    reason: Optional[str] = None
    printed_by_id: int
    printed_by_name: str


class CardPrintedResponse(BaseModel):

    message: str
    print_count: int
    print_history: list[CardPrintHistory]


class AccountSettingsUpdate(BaseModel):

    notification_email: Optional[bool] = None
    notification_sms: Optional[bool] = None
    notification_hold_ready: Optional[bool] = None
    notification_due_reminder: Optional[bool] = None
    notification_overdue: Optional[bool] = None
    checkout_limit: Optional[int] = Field(None, ge=0, le=100)
    hold_limit: Optional[int] = Field(None, ge=0, le=50)


class AccountSettingsResponse(BaseModel):

    patron_id: int
    notification_email: bool = True
    notification_sms: bool = False
    notification_hold_ready: bool = True
    notification_due_reminder: bool = True
    notification_overdue: bool = True
    checkout_limit: int = 25
    hold_limit: int = 10
    saved_searches_count: int = 0
    reading_lists_count: int = 0


class PatronMergeAuditLogResponse(BaseModel):

    id: int
    merged_at: datetime
    merged_by_id: Optional[int] = None
    merged_by_name: Optional[str] = None
    primary_patron_id: Optional[int] = None
    secondary_patron_id: int
    deleted_patron_email: Optional[str] = None
    deleted_patron_name: Optional[str] = None
    checkouts_transferred: int
    holds_transferred: int
    fines_transferred: int
    reading_lists_transferred: int = 0
    favorites_transferred: int = 0
    total_items_transferred: int = 0
    has_archived_data: bool = False


class MergeHistoryResponse(BaseModel):

    patron_id: int
    as_primary: list[PatronMergeAuditLogResponse] = []
    as_secondary: list[PatronMergeAuditLogResponse] = []
    total_merges: int = 0


class StaffAccessConsentResponse(BaseModel):

    patron_id: int
    patron_name: str
    allow_staff_access_to_history: bool
    staff_member_id: int
    staff_member_name: str
    access_granted: bool
    message: str


class MarkDeceasedRequest(BaseModel):

    date_of_death: Optional[datetime] = Field(None, description="Date of death if known")
    estate_contact_name: Optional[str] = Field(None, max_length=200, description="Name of estate contact")
    estate_contact_email: Optional[str] = Field(None, max_length=255, description="Email of estate contact")
    estate_contact_phone: Optional[str] = Field(None, max_length=20, description="Phone of estate contact")
    notes: Optional[str] = Field(None, description="Additional notes about the situation")


class DeceasedPatronResponse(BaseModel):

    message: str
    patron_id: int
    patron_name: str
    date_of_death: Optional[datetime] = None
    outstanding_checkouts: int
    outstanding_holds: int
    outstanding_fines_amount: Decimal
    estate_followup_required: bool
    estate_contact_name: Optional[str] = None
    estate_contact_email: Optional[str] = None
    notification_sent: bool = False


class EstateOutstandingItemsResponse(BaseModel):

    patron_id: int
    patron_name: str
    date_of_death: Optional[datetime] = None
    estate_contact_name: Optional[str] = None
    estate_contact_email: Optional[str] = None
    estate_contact_phone: Optional[str] = None
    checkouts: list[dict]
    fines: list[dict]
    total_fines_amount: Decimal
    notes: Optional[str] = None
