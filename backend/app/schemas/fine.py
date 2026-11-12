# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from ._base import MoneyDecimal, StrictInputSchema

from ..models.fine import (
    FineStatus,
    FineType,
    PaymentMethod,
    PaymentPlanFrequency,
    PaymentPlanStatus,
)
from ..models.fine_waiver import FineWaiverStatus


class FineBase(BaseModel):
    fine_type: FineType = FineType.overdue
    amount: MoneyDecimal = Field(..., gt=0, description="Fine amount in dollars")
    description: str | None = Field(None, max_length=1000)


class FineCreate(StrictInputSchema, FineBase):
    user_id: int
    checkout_id: int | None = None
    notes: str | None = Field(None, max_length=2000)


class FineUpdate(StrictInputSchema):
    description: str | None = Field(None, max_length=1000)
    notes: str | None = Field(None, max_length=2000)


class FinePayment(StrictInputSchema):
    amount: MoneyDecimal = Field(..., gt=0, description="Payment amount")
    payment_method: PaymentMethod = PaymentMethod.cash
    notes: str | None = Field(None, max_length=1000)


class FineWaive(StrictInputSchema):

    reason: str = Field(
        ..., min_length=1, max_length=2000, description="Reason for waiving the fine"
    )
    amount: MoneyDecimal | None = Field(
        None,
        gt=0,
        description="Amount to waive (defaults to full outstanding balance)",
    )
    requires_approval: bool = Field(
        False,
        description="Force the waiver into pending_approval regardless of amount",
    )


class FineWaiverResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    waiver_id: int
    fine_id: int
    amount_waived: MoneyDecimal
    remaining_balance: MoneyDecimal
    status: FineWaiverStatus
    waived_by: int | None
    waived_at: datetime | None
    approved_by: int | None = None
    approved_at: datetime | None = None
    reason: str


class FineWaiverListItem(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    waiver_id: int
    fine_id: int
    patron_id: int | None
    patron_name: str | None = None
    fine_amount: MoneyDecimal
    amount_waived: MoneyDecimal
    reason: str
    status: FineWaiverStatus
    waived_by_user_id: int | None
    waived_by_name: str | None = None
    waived_at: datetime | None
    requested_at: datetime


class FineWaiverListResponse(BaseModel):
    waivers: list[FineWaiverListItem]
    total_count: int


class FineWaiverDecision(StrictInputSchema):

    notes: str | None = Field(None, max_length=2000)


class FineResponse(BaseModel):
    id: int
    user_id: int
    checkout_id: int | None
    fine_type: FineType
    status: str
    amount: MoneyDecimal
    amount_paid: MoneyDecimal
    balance: MoneyDecimal
    description: str | None
    notes: str | None
    created_at: datetime | None = None
    paid_at: datetime | None
    waived_at: datetime | None
    waived_by_id: int | None

    patron_name: str | None = None
    patron_email: str | None = None
    patron_library_card: str | None = None

    class Config:
        from_attributes = True


class FineListResponse(BaseModel):
    fines: list[FineResponse]
    total_count: int
    total_unpaid: MoneyDecimal

class PatronFineResponse(BaseModel):
    id: int
    fine_type: FineType
    status: str
    amount: MoneyDecimal
    amount_paid: MoneyDecimal
    balance: MoneyDecimal
    description: str | None
    created_at: datetime | None = None
    paid_at: datetime | None
    waived: bool
    waived_at: datetime | None
    item_title: str | None = None
    item_author: str | None = None

    model_config = ConfigDict(from_attributes=True)



class FineSummary(BaseModel):
    total_outstanding: MoneyDecimal
    total_paid: MoneyDecimal
    outstanding_count: int
    paid_count: int


# ==================== Payment History Schemas ====================


class PaymentHistoryCreate(StrictInputSchema):
    amount: MoneyDecimal = Field(..., gt=0, description="Payment amount")
    payment_method: PaymentMethod = PaymentMethod.cash
    notes: str | None = Field(None, max_length=1000)


class PaymentHistoryResponse(BaseModel):
    id: int
    fine_id: int
    user_id: int | None
    amount: MoneyDecimal
    payment_method: PaymentMethod
    notes: str | None
    receipt_number: str | None
    processed_by_id: int | None
    processed_by_name: str | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class PaymentHistoryListResponse(BaseModel):
    payments: list[PaymentHistoryResponse]
    total_count: int
    total_amount: MoneyDecimal


# ==================== Partial Payment Schemas ====================


class PartialPaymentRequest(StrictInputSchema):
    amount: MoneyDecimal = Field(..., gt=0, description="Payment amount")
    payment_method: PaymentMethod = PaymentMethod.cash
    notes: str | None = Field(None, max_length=1000)


class PartialPaymentResponse(BaseModel):
    fine: FineResponse
    payment: PaymentHistoryResponse
    receipt_number: str


# ==================== Payment Plan Schemas ====================


class PaymentPlanCreate(StrictInputSchema):
    total_amount: MoneyDecimal = Field(..., gt=0, description="Total amount to be paid")
    installment_amount: MoneyDecimal = Field(..., gt=0, description="Amount per installment")
    frequency: PaymentPlanFrequency = PaymentPlanFrequency.monthly
    reminder_enabled: bool = True
    notes: str | None = Field(None, max_length=2000)


class PaymentPlanUpdate(StrictInputSchema):
    installment_amount: MoneyDecimal | None = Field(None, gt=0)
    frequency: PaymentPlanFrequency | None = None
    reminder_enabled: bool | None = None
    status: PaymentPlanStatus | None = None
    notes: str | None = Field(None, max_length=2000)


class PaymentPlanResponse(BaseModel):
    id: int
    user_id: int
    total_amount: MoneyDecimal
    installment_amount: MoneyDecimal
    frequency: PaymentPlanFrequency
    status: PaymentPlanStatus
    amount_paid: MoneyDecimal
    remaining_balance: MoneyDecimal
    payments_made: int
    total_payments_expected: int
    progress_percentage: float
    start_date: datetime
    next_payment_date: datetime | None
    completed_at: datetime | None
    reminder_enabled: bool
    last_reminder_sent: datetime | None
    notes: str | None
    created_by_id: int | None
    created_by_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class PaymentPlanListResponse(BaseModel):
    payment_plans: list[PaymentPlanResponse]
    total_count: int


# ==================== Receipt Schemas ====================


class ReceiptData(BaseModel):
    receipt_number: str
    payment_date: datetime
    payment_amount: MoneyDecimal
    payment_method: PaymentMethod

    # Patron info
    patron_id: int
    patron_name: str
    patron_email: str | None
    patron_library_card: str | None

    # Fine details
    fine_id: int
    fine_type: FineType
    fine_description: str | None
    original_fine_amount: MoneyDecimal
    amount_paid_before: MoneyDecimal
    amount_paid_now: MoneyDecimal
    remaining_balance: MoneyDecimal

    # Staff info
    staff_id: int
    staff_name: str

    # Library info
    library_name: str = "Lone Star Collective"
    library_address: str | None = None
    library_phone: str | None = None


# ==================== Fine Analytics Schemas ====================


class FineAnalyticsByType(BaseModel):
    fine_type: FineType
    count: int
    total_amount: MoneyDecimal
    percentage: float


class FineAccumulationPoint(BaseModel):
    date: str  # YYYY-MM format
    amount: MoneyDecimal
    count: int


class PatronFinePatterns(BaseModel):
    frequent_late_returns: bool
    average_days_overdue: float | None
    most_common_fine_type: FineType | None
    total_lifetime_fines: MoneyDecimal
    total_lifetime_paid: MoneyDecimal
    average_fine_amount: MoneyDecimal | None


class FineAnalyticsResponse(BaseModel):
    patron_id: int
    patron_name: str

    # Summary
    current_balance: MoneyDecimal
    total_fines_count: int
    unpaid_fines_count: int

    # Breakdown by type
    breakdown_by_type: list[FineAnalyticsByType]

    # Accumulation over time (last 12 months)
    accumulation_history: list[FineAccumulationPoint]

    # Pattern analysis
    patterns: PatronFinePatterns

    # Comparison to average
    average_patron_balance: MoneyDecimal
    comparison_to_average: str  # "above", "below", "average"


class FineHistoryResponse(BaseModel):
    patron_id: int
    patron_name: str
    fines: list[FineResponse]
    payments: list[PaymentHistoryResponse]
    total_count: int
    total_fines_amount: MoneyDecimal
    total_paid_amount: MoneyDecimal
    current_balance: MoneyDecimal


# ==================== Fine Detail Schemas ====================


class FinePaymentDetail(BaseModel):
    id: int
    amount: MoneyDecimal
    payment_method: str
    notes: str | None = None
    receipt_number: str | None = None
    processed_by_name: str | None = None
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class FineDetailItem(BaseModel):
    id: int
    fine_type: str
    status: str
    amount: MoneyDecimal
    amount_paid: MoneyDecimal
    balance: MoneyDecimal
    description: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    paid_at: datetime | None = None
    waived_at: datetime | None = None
    waived_by_name: str | None = None
    # Item context
    item_title: str | None = None
    item_author: str | None = None
    item_type: str | None = None
    item_barcode: str | None = None
    # Checkout timeline
    checked_out_at: datetime | None = None
    due_date: datetime | None = None
    returned_at: datetime | None = None
    # Computed
    explanation: str
    # Expandable detail
    payments: list[FinePaymentDetail] = []

    model_config = ConfigDict(from_attributes=True)


class FineDetailResponse(BaseModel):
    patron_id: int
    patron_name: str
    patron_email: str | None = None
    total_fines: int
    total_outstanding: MoneyDecimal
    fines: list[FineDetailItem]
