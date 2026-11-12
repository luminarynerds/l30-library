# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import MoneyDecimal, StrictInputSchema

from app.models.found_items import (
    FoundItemStatus,
    MatchConfidenceLevel,
    ClaimVerificationStatus,
    DisposalMethod,
)


# ============================================================================
# Storage Location Schemas
# ============================================================================


class StorageLocationCreateRequest(StrictInputSchema):

    location_name: str = Field(..., min_length=1, max_length=200)
    location_code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    branch: Optional[str] = None
    max_items: Optional[int] = None
    is_secure_storage: bool = False
    requires_verification: bool = False
    access_restricted: bool = False


class StorageLocationUpdateRequest(StrictInputSchema):

    location_name: Optional[str] = None
    description: Optional[str] = None
    max_items: Optional[int] = None
    is_secure_storage: Optional[bool] = None
    requires_verification: Optional[bool] = None
    access_restricted: Optional[bool] = None
    is_active: Optional[bool] = None


class StorageLocationResponse(BaseModel):

    id: int
    location_name: str
    location_code: str
    description: Optional[str]
    branch: Optional[str]
    max_items: Optional[int]
    current_item_count: int
    is_secure_storage: bool
    requires_verification: bool
    access_restricted: bool
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
# Found Item Photo Schemas
# ============================================================================


class FoundItemPhotoResponse(BaseModel):

    id: int
    photo_url: str
    photo_key: str
    is_primary: bool
    photo_notes: Optional[str]
    upload_timestamp: datetime
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
# Found Item Match Schemas
# ============================================================================


class FoundItemMatchResponse(BaseModel):

    id: int
    lost_item_record_id: int
    confidence_level: MatchConfidenceLevel
    match_score: MoneyDecimal
    # DB stores these as JSON that may be a list or an object; accept either
    # (was Optional[dict], which 500'd on list-valued rows).
    matching_factors: Optional[Any] = None
    non_matching_factors: Optional[Any] = None
    is_confirmed: bool
    confirmation_notes: Optional[str]
    patron_notified: bool
    patron_notified_at: Optional[datetime]
    created_at: datetime | None = None
    model_config = {"from_attributes": True}

    # These bool columns are nullable in the DB; coerce NULL to False.
    @field_validator("is_confirmed", "patron_notified", mode="before")
    @classmethod
    def _bool_default_false(cls, v):
        return False if v is None else v


class ConfirmMatchRequest(StrictInputSchema):

    is_confirmed: bool
    confirmation_notes: Optional[str] = None


# ============================================================================
# Found Item Claim Verification Schemas
# ============================================================================


class ClaimVerificationResponse(BaseModel):

    id: int
    found_item_id: int
    patron_id: int
    claim_statement: str
    date_claimed: datetime
    status: ClaimVerificationStatus
    identity_verified: bool
    verification_method: Optional[str]
    item_confirmed: bool
    confirmation_notes: Optional[str]
    distinctive_features_mentioned: Optional[dict]
    approval_decision: Optional[bool]
    picked_up_at: Optional[datetime]
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class FileClaimRequest(StrictInputSchema):

    claim_statement: str = Field(..., min_length=10, max_length=1000)
    distinctive_features: Optional[dict] = None


class VerifyClaimRequest(StrictInputSchema):

    identity_verified: bool
    verification_method: str = Field(..., min_length=1, max_length=100)
    item_confirmed: bool
    confirmation_notes: Optional[str] = None


class ReviewClaimRequest(StrictInputSchema):

    approval_decision: bool
    rejection_reason: Optional[str] = None


class MarkPickupRequest(StrictInputSchema):

    picked_up_by_id: int


# ============================================================================
# Found Item Schemas
# ============================================================================


class FoundItemCreateRequest(StrictInputSchema):

    description: str = Field(..., min_length=10, max_length=500)
    category: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = None
    brand_or_label: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    additional_details: Optional[str] = None
    location_found: str = Field(..., min_length=1, max_length=200)
    location_details: Optional[str] = None
    date_found: datetime
    storage_location_id: Optional[int] = None
    secure_storage_flag: bool = False
    estimated_value: Optional[MoneyDecimal] = None
    retention_period_days: int = Field(30, ge=1, le=365)
    staff_notes: Optional[str] = None


class FoundItemUpdateRequest(StrictInputSchema):

    description: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    brand_or_label: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    additional_details: Optional[str] = None
    location_found: Optional[str] = None
    location_details: Optional[str] = None
    storage_location_id: Optional[int] = None
    secure_storage_flag: Optional[bool] = None
    estimated_value: Optional[MoneyDecimal] = None
    staff_notes: Optional[str] = None


class UpdateStorageLocationRequest(StrictInputSchema):

    storage_location_id: int


class DisposeFoundItemRequest(StrictInputSchema):

    disposal_method: DisposalMethod
    disposal_notes: Optional[str] = None


class FoundItemResponse(BaseModel):

    id: int
    description: str
    category: str
    color: Optional[str]
    brand_or_label: Optional[str]
    size: Optional[str]
    condition: Optional[str]
    additional_details: Optional[str]
    location_found: str
    location_details: Optional[str]
    date_found: datetime
    storage_location_id: Optional[int]
    storage_location: Optional[StorageLocationResponse] = None
    secure_storage_flag: bool
    estimated_value: Optional[MoneyDecimal]
    status: FoundItemStatus
    retention_period_days: int
    retention_end_date: datetime
    disposal_method: Optional[DisposalMethod]
    disposed_at: Optional[datetime]
    disposal_notes: Optional[str]
    staff_notes: Optional[str]
    photos: List[FoundItemPhotoResponse] = []
    matches: List[FoundItemMatchResponse] = []
    claim: Optional[ClaimVerificationResponse] = None
    found_by_id: Optional[int] = None
    logged_by_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class FoundItemListResponse(BaseModel):

    items: List[FoundItemResponse]
    total: int
    limit: int
    offset: int


class FoundItemSearchRequest(StrictInputSchema):

    search_query: Optional[str] = None
    category: Optional[str] = None
    status: Optional[FoundItemStatus] = None
    location_found: Optional[str] = None
    date_found_from: Optional[datetime] = None
    date_found_to: Optional[datetime] = None
    secure_storage_only: bool = False
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class AutoMatchFoundItemRequest(StrictInputSchema):

    found_item_id: int


class AutoMatchResult(BaseModel):

    found_item_id: int
    matches: List[FoundItemMatchResponse]
    best_match: Optional[FoundItemMatchResponse]
    total_matches: int


class BulkUpdateStatusRequest(StrictInputSchema):

    found_item_ids: List[int]
    new_status: FoundItemStatus


# ============================================================================
# Success Response Wrappers
# ============================================================================


class SuccessResponse(BaseModel):

    success: bool = True
    message: str
    data: Optional[dict] = None


class StorageLocationListResponse(BaseModel):

    items: List[StorageLocationResponse]
    total: int
    limit: int
    offset: int
