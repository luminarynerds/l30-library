# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field

from ._base import MoneyDecimal, StrictInputSchema

from app.models.patron_account import TransactionType, TransactionStatus, AccountPaymentMethod


class AccountBalanceResponse(BaseModel):
    id: int
    patron_id: int
    balance: MoneyDecimal
    total_deposited: MoneyDecimal
    total_spent: MoneyDecimal
    is_active: bool
    low_balance_threshold: MoneyDecimal
    auto_reload_enabled: bool
    last_deposit_at: Optional[datetime] = None
    last_charge_at: Optional[datetime] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class DepositRequest(StrictInputSchema):
    amount: MoneyDecimal = Field(..., gt=0, le=500, description="Amount to deposit")
    payment_method: AccountPaymentMethod
    notes: Optional[str] = Field(None, max_length=500)


class StaffDepositRequest(StrictInputSchema):
    amount: MoneyDecimal = Field(..., gt=0, le=1000)
    payment_method: AccountPaymentMethod
    notes: Optional[str] = Field(None, max_length=500)


class RefundRequest(StrictInputSchema):
    amount: MoneyDecimal = Field(..., gt=0, le=1000)
    reason: str = Field(..., min_length=1, max_length=500)
    notes: Optional[str] = Field(None, max_length=500)


class TransactionResponse(BaseModel):
    id: int
    account_id: int
    transaction_type: TransactionType
    status: TransactionStatus
    amount: MoneyDecimal
    balance_before: MoneyDecimal
    balance_after: MoneyDecimal
    payment_method: Optional[AccountPaymentMethod] = None
    description: str
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    receipt_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    per_page: int
