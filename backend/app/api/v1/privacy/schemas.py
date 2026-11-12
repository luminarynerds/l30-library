# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Privacy and Compliance Pydantic Schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ChildRegistrationRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    parent_email: EmailStr


class ParentalConsentRequest(BaseModel):
    token: str
    consent_given: bool = True


class ParentalConsentResponse(BaseModel):
    message: str
    consent_given: bool


class ConsentTokenInfoResponse(BaseModel):
    child_first_name: str
    child_last_initial: str
    parent_email: str
    expires_at: str
    already_decided: bool


class PrivacyChangeHistory(BaseModel):
    id: int
    resource_type: str
    resource_id: int
    old_privacy: str
    new_privacy: str
    changed_at: str


class DataExportResponse(BaseModel):
    profile: dict
    checkouts: list
    holds: list
    fines: list
    reading_history: list
    favorites: list
    reading_lists: list
    event_registrations: list
    ai_conversations: list
    ebook_checkouts: list
    privacy_change_history: list  # New: privacy setting changes
    exported_at: str


class AccountDeletionRequest(BaseModel):
    confirmation: str = Field(..., description="Must be 'DELETE' to confirm")
    password: str = Field(..., description="Current password for verification")


class DeletionRequestResponse(BaseModel):
    message: str
    deletion_scheduled_for: str
    can_cancel_until: str
    data_export_available: bool = True


class DeletionEligibilityResponse(BaseModel):
    eligible: bool
    has_unpaid_fines: bool
    unpaid_fine_amount: Optional[float] = None
    has_active_checkouts: bool
    active_checkout_count: int = 0
    has_child_accounts: bool
    child_account_count: int = 0
    deletion_pending: bool
    deletion_scheduled_for: Optional[str] = None
    blockers: list[str]


class StaffDeletionRequest(BaseModel):
    patron_id: int
    reason: Optional[str] = Field(None, max_length=500)
    identity_verified: bool = Field(..., description="Staff confirms identity was verified in person")


class ChildAccountInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    parental_consent_given: bool
    created_at: datetime


class ConsentRecordResponse(BaseModel):
    id: int
    consent_type: str
    status: str
    method: str
    policy_version: Optional[str] = None
    details: Optional[dict] = None
    expires_at: Optional[str] = None
    created_at: str


class ConsentRecordsListResponse(BaseModel):
    records: list[ConsentRecordResponse]
    total: int


class DataSharingRecordResponse(BaseModel):
    id: int
    recipient_name: str
    recipient_type: Optional[str] = None
    purpose: str
    data_categories: list[str]
    legal_basis: Optional[str] = None
    patron_notified: bool
    patron_notified_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


class DataSharingListResponse(BaseModel):
    records: list[DataSharingRecordResponse]
    total: int


class DataCorrectionRequest(BaseModel):
    field_name: str = Field(..., max_length=100, description="The field to correct (e.g., 'first_name', 'email', 'address')")
    new_value: str = Field(..., description="The corrected value")
    reason: str = Field(..., min_length=1, max_length=1000, description="Why this correction is needed")


class DataCorrectionResponse(BaseModel):
    id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: str
    reason: str
    status: str
    created_at: str


class DataCorrectionListResponse(BaseModel):
    records: list[DataCorrectionResponse]
    total: int


class DeletionVerificationResponse(BaseModel):
    hard_deleted: list[str]
    anonymized: list[str]
    retained_in_backups: str
    backup_retention_policy: str
    audit_log_handling: str
    re_registration_block_days: int
    deletion_is_true_erasure: bool
    what_remains_after_deletion: list[str]


class EnhancedDataExportResponse(BaseModel):
    profile: dict
    checkouts: list
    holds: list
    fines: list
    reading_history: list
    favorites: list
    reading_lists: list
    event_registrations: list
    ai_conversations: list
    ebook_checkouts: list
    privacy_change_history: list
    consent_records: list
    data_sharing_log: list
    data_corrections: list
    audit_trail: list
    exported_at: str


class PatronPrivacySettingsResponse(BaseModel):
    discreet_receipts: bool
    allow_staff_access_to_history: bool
    track_reading_history: bool
    aggregate_recommendations_opt_out: bool
    notification_frequency: str


class PatronPrivacySettingsUpdate(BaseModel):
    discreet_receipts: Optional[bool] = None
    allow_staff_access_to_history: Optional[bool] = None
    track_reading_history: Optional[bool] = None
    aggregate_recommendations_opt_out: Optional[bool] = None
    notification_frequency: Optional[str] = None


# --- Patron Data Controls ---


class HoldHistoryItem(BaseModel):
    id: int
    item_title: str
    status: str
    created_at: Optional[str] = None
    cancelled_at: Optional[str] = None


class HoldHistoryResponse(BaseModel):
    items: list[HoldHistoryItem]
    total: int


class AIConversationListItem(BaseModel):
    id: int
    session_id: str
    user_message: Optional[str] = None
    detected_intent: Optional[str] = None
    created_at: Optional[str] = None


class AIConversationListResponse(BaseModel):
    items: list[AIConversationListItem]
    total: int


class AIConversationDetail(BaseModel):
    id: int
    session_id: str
    user_message: Optional[str] = None
    agent_response: Optional[str] = None
    conversation_context: Optional[dict] = None
    detected_intent: Optional[str] = None
    helpful: Optional[bool] = None
    feedback_note: Optional[str] = None
    created_at: Optional[str] = None


class NotificationHistoryClearResponse(BaseModel):
    deleted_count: int
