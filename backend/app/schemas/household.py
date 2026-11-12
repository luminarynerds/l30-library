# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, EmailStr, field_validator

from ._base import StrictInputSchema


class LinkRequestCreate(StrictInputSchema):
    parent_email: EmailStr = Field(..., description="Email of parent account to link to")
    message: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional message to send with link request"
    )


class LinkApprovalRequest(StrictInputSchema):
    approved: bool = Field(..., description="True to approve, False to decline link")
    decline_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for declining (only if approved=False)"
    )

    @field_validator("decline_reason")
    @classmethod
    def validate_decline_reason(cls, v: Optional[str], info) -> Optional[str]:
        approved = info.data.get("approved")
        if approved is False and not v:
            raise ValueError("decline_reason is required when declining a request")
        if approved is True and v:
            raise ValueError("decline_reason should not be provided when approving")
        return v


class LinkedAccountInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    relationship: str  # "parent", "child"
    link_status: str  # pending, approved, declined
    linked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HouseholdLinkResponse(BaseModel):
    id: int
    requester_id: int
    requester_name: str  # full name of requester
    target_parent_id: int
    target_parent_name: str  # full name of parent
    status: str  # pending, approved, declined
    message: Optional[str] = None
    decline_reason: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class HouseholdLinkListResponse(BaseModel):
    links: List[HouseholdLinkResponse]
    total: int


class Hold(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    user_id: int
    user_name: str
    position: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class Checkout(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    user_id: int
    user_name: str
    due_date: datetime
    checkout_date: datetime

    class Config:
        from_attributes = True


class Fine(BaseModel):
    id: int
    user_id: int
    user_name: str
    amount: float
    reason: str
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class HouseholdOverviewResponse(BaseModel):
    # Current account context
    viewing_as_user_id: int
    viewing_as_name: str
    relationship: str  # "self" for single, "parent" for parent viewing, "child" for child viewing

    # Household information
    household_id: Optional[int] = None
    household_members: List[LinkedAccountInfo] = []

    # Pending link requests (for parents viewing their account)
    pending_requests: List[HouseholdLinkResponse] = []

    # Aggregated household data
    holds: List[Hold] = []
    checkouts: List[Checkout] = []
    fines: List[Fine] = []

    # Summary statistics
    total_holds: int = 0
    total_checkouts: int = 0
    total_fines_amount: float = 0.0

    class Config:
        from_attributes = True


class FamilyAccountInfo(BaseModel):
    id: int
    name: str
    email: str
    relationship: str  # "self", "parent", "child"

    class Config:
        from_attributes = True
