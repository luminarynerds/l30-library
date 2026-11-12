# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class DonationCreate(StrictInputSchema):
    donor_name: Optional[str] = None
    donor_email: Optional[str] = None
    donor_phone: Optional[str] = None
    donor_address: Optional[str] = None
    is_anonymous: bool = False
    tax_receipt_requested: bool = False
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    material_type: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    condition_notes: Optional[str] = None
    estimated_value: Optional[int] = None
    received_date: Optional[date] = None
    staff_notes: Optional[str] = None


class DonationUpdate(StrictInputSchema):
    donor_name: Optional[str] = None
    donor_email: Optional[str] = None
    donor_phone: Optional[str] = None
    donor_address: Optional[str] = None
    is_anonymous: Optional[bool] = None
    tax_receipt_requested: Optional[bool] = None
    tax_receipt_sent: Optional[bool] = None
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    material_type: Optional[str] = None
    quantity: Optional[int] = None
    condition_notes: Optional[str] = None
    estimated_value: Optional[int] = None
    staff_notes: Optional[str] = None


class DonationReviewRequest(StrictInputSchema):
    action: str = Field(..., pattern="^(accept|decline)$")
    decline_reason: Optional[str] = None
    staff_notes: Optional[str] = None


class DonationProcessRequest(StrictInputSchema):
    catalog_item_id: Optional[int] = None
    create_new_catalog_item: bool = False
    location: Optional[str] = None


class DonationResponse(BaseModel):
    id: int
    donor_name: Optional[str] = None
    donor_email: Optional[str] = None
    donor_phone: Optional[str] = None
    donor_address: Optional[str] = None
    is_anonymous: bool
    tax_receipt_requested: bool
    tax_receipt_sent: bool
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    material_type: Optional[str] = None
    quantity: int
    condition_notes: Optional[str] = None
    estimated_value: Optional[int] = None
    status: str
    received_date: date
    received_by_id: Optional[int] = None
    received_by_name: Optional[str] = None
    reviewed_by_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    decline_reason: Optional[str] = None
    staff_notes: Optional[str] = None
    catalog_item_id: Optional[int] = None
    item_copy_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
