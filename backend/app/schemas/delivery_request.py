# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema

from ..models.home_delivery import DeliveryFrequency, DeliveryRequestStatus


class DeliveryRequestCreate(StrictInputSchema):
    item_id: int
    frequency: DeliveryFrequency = DeliveryFrequency.on_demand
    delivery_address: Optional[str] = None
    delivery_notes: Optional[str] = Field(None, max_length=500)
    preferred_window: Optional[str] = None  # e.g., "morning", "afternoon", "9am-12pm"
    requested_by_date: Optional[datetime] = None


class DeliveryRequestUpdate(StrictInputSchema):
    frequency: Optional[DeliveryFrequency] = None
    delivery_address: Optional[str] = None
    delivery_notes: Optional[str] = Field(None, max_length=500)
    preferred_window: Optional[str] = None
    requested_by_date: Optional[datetime] = None


class DeliveryRequestApprove(StrictInputSchema):
    notes: Optional[str] = Field(None, max_length=500)


class DeliveryRequestDecline(StrictInputSchema):
    reason: str = Field(..., max_length=500)


class DeliveryRequestResponse(BaseModel):
    id: int
    user_id: int
    item_id: int
    status: DeliveryRequestStatus
    frequency: DeliveryFrequency
    delivery_address: Optional[str] = None
    delivery_notes: Optional[str] = None
    preferred_window: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    approved_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    decline_reason: Optional[str] = None
    delivered_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    requested_by_date: Optional[datetime] = None
    next_delivery_date: Optional[datetime] = None
    approved_by_id: Optional[int] = None

    # Denormalized for convenience
    item_title: Optional[str] = None
    item_author: Optional[str] = None
    patron_name: Optional[str] = None

    class Config:
        from_attributes = True


class DeliveryRequestListResponse(BaseModel):
    id: int
    user_id: int
    patron_name: Optional[str] = None
    item_id: int
    item_title: Optional[str] = None
    status: DeliveryRequestStatus
    frequency: DeliveryFrequency
    created_at: datetime | None = None
    requested_by_date: Optional[datetime] = None
    next_delivery_date: Optional[datetime] = None
    approved_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class DeliveryRequestHistoryResponse(BaseModel):
    id: int
    user_id: int
    item_id: int
    status: DeliveryRequestStatus
    frequency: DeliveryFrequency
    created_at: datetime | None = None
    delivered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Item info
    item_title: Optional[str] = None
    item_author: Optional[str] = None

    class Config:
        from_attributes = True
