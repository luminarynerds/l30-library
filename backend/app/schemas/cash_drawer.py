# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema

from ..models.cash_drawer import (
    DrawerMode, CashSessionStatus, TransactionCategory, TransactionDirection,
)


# --- Drawer ---

class CashDrawerCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=100)
    default_float: MoneyDecimal = Field(default=Decimal("100.00"), ge=0)
    mode: DrawerMode = DrawerMode.day_based
    discrepancy_threshold: MoneyDecimal = Field(default=Decimal("5.00"), ge=0)


class CashDrawerUpdate(StrictInputSchema):
    name: str | None = Field(None, min_length=1, max_length=100)
    default_float: MoneyDecimal | None = Field(None, ge=0)
    mode: DrawerMode | None = None
    discrepancy_threshold: MoneyDecimal | None = Field(None, ge=0)
    is_active: bool | None = None


class CashDrawerResponse(BaseModel):
    id: int
    name: str
    default_float: MoneyDecimal
    mode: DrawerMode
    discrepancy_threshold: MoneyDecimal
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


# --- Session ---

class OpenSessionRequest(StrictInputSchema):
    opening_float: MoneyDecimal = Field(..., ge=0)


class CloseSessionRequest(StrictInputSchema):
    counted_total: MoneyDecimal = Field(..., ge=0)
    denomination_breakdown: dict[str, int] | None = None
    notes: str | None = Field(None, max_length=2000)


class ApproveSessionRequest(StrictInputSchema):
    notes: str | None = Field(None, max_length=2000)


class SessionSummary(BaseModel):
    total_inflows: MoneyDecimal
    total_outflows: MoneyDecimal
    transaction_count: int
    inflow_by_category: dict[str, MoneyDecimal]
    outflow_by_category: dict[str, MoneyDecimal]


class CashDrawerSessionResponse(BaseModel):
    id: int
    drawer_id: int
    opened_by: int
    closed_by: int | None
    approved_by: int | None
    status: CashSessionStatus
    opening_float: MoneyDecimal
    expected_total: MoneyDecimal | None
    counted_total: MoneyDecimal | None
    discrepancy: MoneyDecimal | None
    denomination_breakdown: dict[str, int] | None
    notes: str | None
    opened_at: datetime
    closed_at: datetime | None
    opener_name: str | None = None
    closer_name: str | None = None
    approver_name: str | None = None
    summary: SessionSummary | None = None

    model_config = {"from_attributes": True}


# --- Transaction ---

class CreateTransactionRequest(StrictInputSchema):
    direction: TransactionDirection
    category: TransactionCategory
    amount: MoneyDecimal = Field(..., gt=0)
    amount_tendered: MoneyDecimal | None = Field(None, gt=0)
    description: str | None = Field(None, max_length=1000)
    reference_type: str | None = Field(None, max_length=50)
    reference_id: int | None = None


class CashTransactionResponse(BaseModel):
    id: int
    session_id: int
    staff_id: int
    direction: TransactionDirection
    category: TransactionCategory
    amount: MoneyDecimal
    amount_tendered: MoneyDecimal | None
    change_given: MoneyDecimal | None
    description: str | None
    reference_type: str | None
    reference_id: int | None
    voided: bool
    created_at: datetime | None = None
    staff_name: str | None = None

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    transactions: list[CashTransactionResponse]
    total: int


# --- History ---

class SessionHistoryParams(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    staff_id: int | None = None
    status: CashSessionStatus | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class SessionHistoryResponse(BaseModel):
    sessions: list[CashDrawerSessionResponse]
    total: int
    page: int
    per_page: int
