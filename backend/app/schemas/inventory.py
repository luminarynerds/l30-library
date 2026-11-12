# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import MoneyDecimal, StrictInputSchema

from ..models.inventory import AcquisitionSource, DamageType, ItemCondition

# ============ ItemCopy Schemas ============


class ItemCopyBase(BaseModel):
    barcode: str = Field(..., max_length=50)
    copy_number: int = 1
    condition: ItemCondition = ItemCondition.GOOD
    acquisition_date: date | None = None
    acquisition_source: AcquisitionSource | None = AcquisitionSource.PURCHASE
    location: str | None = Field(None, max_length=100)
    replacement_cost: MoneyDecimal | None = None
    volume_override: str | None = Field(None, max_length=50)
    notes: str | None = None


class ItemCopyCreate(StrictInputSchema, ItemCopyBase):
    catalog_item_id: int
    purchase_order_item_id: int | None = None


class ItemCopyUpdate(StrictInputSchema):
    barcode: str | None = Field(None, max_length=50)
    copy_number: int | None = None
    condition: ItemCondition | None = None
    location: str | None = Field(None, max_length=100)
    replacement_cost: MoneyDecimal | None = None
    volume_override: str | None = Field(None, max_length=50)
    notes: str | None = None


class ItemCopyResponse(ItemCopyBase):
    condition: str = "good"
    id: int
    catalog_item_id: int
    purchase_order_item_id: int | None
    catalog_title: str | None = None
    catalog_author: str | None = None
    is_available: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ ConditionChange Schemas ============


class ConditionChangeCreate(StrictInputSchema):
    new_condition: ItemCondition
    damage_type: DamageType | None = None
    damage_description: str | None = None
    photo_url: str | None = None
    repair_cost: MoneyDecimal | None = None
    repair_notes: str | None = None


class ConditionChangeResponse(BaseModel):
    id: int
    item_copy_id: int
    previous_condition: str
    new_condition: str
    damage_type: DamageType | None
    damage_description: str | None
    photo_url: str | None
    repair_cost: MoneyDecimal | None
    repair_notes: str | None
    repaired_at: datetime | None
    reported_by_id: int | None
    reported_by_name: str | None = None
    created_at: datetime | None = None

    @field_validator("damage_type", mode="before")
    @classmethod
    def _coerce_unknown_damage_type(cls, v):
        # damage_type is a free-text String(50) column; legacy/seed rows can
        # hold values outside the DamageType enum. Degrade unknown values to
        # None instead of 500ing the whole history list.
        if v is None or isinstance(v, DamageType):
            return v
        try:
            return DamageType(v)
        except ValueError:
            return None

    class Config:
        from_attributes = True


# ============ Inventory Audit Schemas ============


class AuditCreate(StrictInputSchema):
    name: str = Field(..., max_length=255)
    description: str | None = None
    location_filter: str | None = Field(None, max_length=100)


class AuditResponse(BaseModel):
    id: int
    name: str
    description: str | None
    location_filter: str | None
    started_at: datetime
    completed_at: datetime | None
    items_expected: int
    items_found: int
    items_missing: int
    items_misplaced: int
    created_by_id: int
    created_by_name: str | None = None

    class Config:
        from_attributes = True


class AuditScanCreate(StrictInputSchema):
    barcode: str
    found_at_location: str | None = None


class AuditScanResponse(BaseModel):
    id: int
    audit_id: int
    item_copy_id: int
    barcode: str | None = None
    catalog_title: str | None = None
    found_at_location: str | None
    is_misplaced: bool
    scanned_at: datetime

    class Config:
        from_attributes = True


# ============ List Response Schemas ============


class ItemCopyListResponse(BaseModel):
    items: list[ItemCopyResponse]
    total: int
    page: int
    per_page: int


class AuditListResponse(BaseModel):
    items: list[AuditResponse]
    total: int
    page: int
    per_page: int


# ============ Withdraw Schema ============


class WithdrawRequest(StrictInputSchema):
    reason: str = Field(..., min_length=1)


# ============ Repair Schema ============


class RepairRequest(StrictInputSchema):
    new_condition: ItemCondition = Field(
        ..., description="The condition after repair (must be better than current)"
    )
    repair_notes: str = Field(..., min_length=1, description="Description of repair work performed")
    repair_cost: MoneyDecimal | None = Field(None, ge=0, description="Cost of repair if applicable")
