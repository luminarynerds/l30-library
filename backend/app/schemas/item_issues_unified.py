# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Literal

from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema


class UnifiedItemIssueResponse(BaseModel):
    id: int
    issue_type: Literal["lost", "damaged", "claims"]
    status: str  # reported, claimed, resolved, etc.
    patron_id: Optional[int]
    patron_name: Optional[str]
    patron_email: Optional[str]
    item_title: Optional[str]
    item_copy_id: Optional[int]
    reported_at: datetime
    reported_by_id: Optional[int]
    reported_by_name: Optional[str]

    # Issue-specific fields
    lost_type: Optional[str] = None  # lost_by_patron, lost_in_transit, etc.
    replacement_cost: Optional[MoneyDecimal] = None
    severity: Optional[str] = None  # minor, moderate, severe, total_loss
    is_patron_responsible: Optional[bool] = None
    claimed_return_date: Optional[date] = None

    # Metadata
    days_since_reported: int = 0
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UnifiedItemIssuesListResponse(BaseModel):
    items: List[UnifiedItemIssueResponse]
    total: int
    limit: int
    offset: int


class GetUnifiedIssuesRequest(StrictInputSchema):
    issue_types: Optional[List[Literal["lost", "damaged", "claims"]]] = Field(
        None,
        description="Filter by issue type (lost, damaged, claims). If not specified, returns all types."
    )
    statuses: Optional[List[str]] = Field(
        None,
        description="Filter by status (reported, claimed, resolved, etc.)"
    )
    patron_id: Optional[int] = Field(None, description="Filter by patron ID")
    days_ago: Optional[int] = Field(
        None,
        ge=1,
        description="Filter items reported within X days"
    )
    limit: int = Field(50, ge=1, le=200, description="Items per page")
    offset: int = Field(0, ge=0, description="Pagination offset")
    sort_by: str = Field("reported_at", description="Sort by: reported_at, status, issue_type")
    sort_order: str = Field("desc", description="Sort order: asc, desc")


class UpdateStatusRequest(StrictInputSchema):
    status: str = Field(..., description="New status")
    notes: Optional[str] = Field(None, description="Notes about the status change")


class BulkUpdateStatusRequest(StrictInputSchema):
    updates: List[dict] = Field(
        ...,
        description="List of updates: [{id, issue_type, status, notes?}, ...]"
    )


class BulkUpdateStatusResponse(BaseModel):
    success: int
    failed: int
    errors: List[str]


class ContactPatronRequest(StrictInputSchema):
    message: str = Field(..., min_length=10, description="Message to send to patron")
    send_email: bool = Field(True, description="Send email notification")
    send_sms: bool = Field(False, description="Send SMS notification")
