# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema


class RepairRecordCreate(StrictInputSchema):
    catalog_item_id: int
    repair_type: str
    damage_description: str | None = None
    estimated_cost: MoneyDecimal | None = None
    fund_id: int | None = None
    vendor_id: int | None = None
    notes: str | None = None


class RepairRecordUpdate(StrictInputSchema):
    repair_type: str | None = None
    damage_description: str | None = None
    repair_notes: str | None = None
    estimated_cost: MoneyDecimal | None = None
    actual_cost: MoneyDecimal | None = None
    fund_id: int | None = None
    vendor_id: int | None = None
    expected_return_date: date | None = None


class RepairStatusUpdate(StrictInputSchema):
    status: str
    notes: str | None = None
    sent_date: date | None = None
    returned_date: date | None = None
    actual_cost: MoneyDecimal | None = None


class RepairRecordResponse(BaseModel):
    id: int
    catalog_item_id: int
    item_title: str | None = None
    item_barcode: str | None = None
    reported_by_name: str | None = None
    repair_type: str
    status: str
    damage_description: str | None
    repair_notes: str | None
    estimated_cost: MoneyDecimal | None
    actual_cost: MoneyDecimal | None
    fund_id: int | None
    vendor_id: int | None
    vendor_name: str | None = None
    sent_date: date | None
    expected_return_date: date | None
    returned_date: date | None
    completed_by_name: str | None = None
    completed_date: date | None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class RepairRecordListResponse(BaseModel):
    items: list[RepairRecordResponse]
    total: int
    page: int
    per_page: int


class RepairDashboardResponse(BaseModel):
    assessed_count: int
    in_repair_count: int
    at_bindery_count: int
    completed_this_month: int
    avg_turnaround_days: float | None
    total_cost_this_month: MoneyDecimal
    total_cost_this_year: MoneyDecimal
