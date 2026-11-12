# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from decimal import Decimal
from enum import StrEnum
from app.models.mixins import TimestampMixin

from sqlalchemy import Boolean, Column, DateTime, Index, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class FineStatus(StrEnum):
    unpaid = "unpaid"
    paid = "paid"
    waived = "waived"
    partial = "partial"


class FineType(StrEnum):
    overdue = "overdue"
    lost_item = "lost_item"
    damaged_item = "damaged_item"
    other = "other"


class FinePolicyType(StrEnum):
    daily_rate = "daily_rate"  # Fixed amount per day overdue
    progressive = "progressive"  # Increases with days overdue
    tiered = "tiered"  # Different rates for different time periods
    maximum_cap = "maximum_cap"  # Flat max cap regardless of days


class Fine(Base, TimestampMixin):
    __tablename__ = "fines"
    __table_args__ = (
        Index(
            "ix_fines_idempotent",
            "checkout_id",
            "fine_type",
            text("((created_at AT TIME ZONE 'UTC')::date)"),
            unique=True,
            postgresql_where=text("checkout_id IS NOT NULL"),
        ),
        Index("ix_fines_user_status", "user_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    # SET NULL on delete to preserve fine records for accounting/audit
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    checkout_id = Column(
        Integer, ForeignKey("checkouts.id", ondelete="SET NULL"), nullable=True, index=True
    )

    fine_type = Column(
        SQLEnum(FineType, name="finetype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=FineType.overdue,
        nullable=False,
    )
    # Free-form local-taxonomy label when fine_type collapses to 'other'.
    # Populated by bulk import when the source ILS uses a debit_type_code
    # outside L30's 4-value FineType (Koha RENT/RESERVE/PROCESSING_FEE,
    # Sirsi LOST_PROCESSING, etc.). NULL for fines that fit the canonical enum.
    local_fine_type = Column(String(50), nullable=True)
    status = Column(
        SQLEnum(FineStatus, name="finestatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=FineStatus.unpaid,
        nullable=False,
        index=True,
    )

    amount = Column(Numeric(10, 2), nullable=False)
    amount_paid = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    waived_at = Column(DateTime(timezone=True), nullable=True)
    waived_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="fines")
    checkout = relationship("Checkout", backref="fines")
    waived_by = relationship("User", foreign_keys=[waived_by_id])

    @property
    def balance(self) -> Decimal:
        return max(Decimal("0"), self.amount - self.amount_paid)


class PaymentMethod(StrEnum):
    cash = "cash"
    card = "card"
    check = "check"
    online = "online"
    waiver = "waiver"
    reading_minutes = "reading_minutes"
    other = "other"

    # Uppercase aliases for domain layer compatibility
    CASH = "cash"
    CARD = "card"
    CHECK = "check"
    ONLINE = "online"
    WAIVER = "waiver"
    READING_MINUTES = "reading_minutes"


class PaymentPlanStatus(StrEnum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"
    defaulted = "defaulted"


class PaymentPlanFrequency(StrEnum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"


class CheckClearanceStatus(StrEnum):
    pending = "pending"      # Check submitted, waiting to clear
    cleared = "cleared"      # Check cleared successfully
    bounced = "bounced"      # Check bounced / NSF


class FinePaymentHistory(Base, TimestampMixin):
    __tablename__ = "fine_payment_history"

    id = Column(Integer, primary_key=True, index=True)
    fine_id = Column(
        Integer, ForeignKey("fines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(
        SQLEnum(PaymentMethod, name="paymentmethod", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PaymentMethod.cash,
        nullable=False,
    )

    notes = Column(Text, nullable=True)
    receipt_number = Column(String(50), nullable=True, unique=True, index=True)

    # Staff who processed the payment
    processed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Check clearance tracking — only relevant when payment_method == check
    check_clearance_status = Column(
        SQLEnum(CheckClearanceStatus, name="checkclearancestatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        index=True,
    )
    check_cleared_at = Column(DateTime(timezone=True), nullable=True)
    check_bounced_at = Column(DateTime(timezone=True), nullable=True)
    check_bounced_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    fine = relationship("Fine", backref="payment_history")
    user = relationship("User", foreign_keys=[user_id])
    processed_by = relationship("User", foreign_keys=[processed_by_id])
    check_bounced_by = relationship("User", foreign_keys=[check_bounced_by_id])


class PaymentPlan(Base, TimestampMixin):
    __tablename__ = "payment_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    total_amount = Column(Numeric(10, 2), nullable=False)
    installment_amount = Column(Numeric(10, 2), nullable=False)
    frequency = Column(
        SQLEnum(PaymentPlanFrequency, name="paymentplanfrequency", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PaymentPlanFrequency.monthly,
        nullable=False,
    )

    status = Column(
        SQLEnum(PaymentPlanStatus, name="paymentplanstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PaymentPlanStatus.active,
        nullable=False,
        index=True,
    )

    # Track progress
    amount_paid = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    payments_made = Column(Integer, default=0, nullable=False)
    total_payments_expected = Column(Integer, nullable=False)

    # Dates
    start_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    next_payment_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Reminders
    reminder_enabled = Column(Boolean, default=True, nullable=False)
    last_reminder_sent = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # Staff who created the plan
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="payment_plans")
    created_by = relationship("User", foreign_keys=[created_by_id])

    @property
    def remaining_balance(self) -> Decimal:
        return self.total_amount - self.amount_paid

    @property
    def progress_percentage(self) -> float:
        if self.total_amount == 0:
            return 100.0
        return float((self.amount_paid / self.total_amount) * 100)


class FinePolicy(Base, TimestampMixin):
    __tablename__ = "fine_policies"

    id = Column(Integer, primary_key=True, index=True)

    # Policy identification
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Policy type determines how to calculate the fine amount
    policy_type = Column(
        SQLEnum(FinePolicyType, name="finepolicytype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=FinePolicyType.daily_rate,
        nullable=False,
    )

    # Applied to which item types (comma-separated: book,ebook,dvd,etc. or 'all')
    applies_to_item_types = Column(String(255), default="all", nullable=False)

    # Applied to which user roles (comma-separated: PATRON,CHILD or 'all')
    applies_to_user_roles = Column(String(255), default="all", nullable=False)

    # Daily rate configuration (for daily_rate and progressive types)
    fine_per_day = Column(Numeric(10, 2), default=Decimal("0.25"), nullable=False)

    # Progressive configuration: percentage increase per day
    # e.g., 10 means $0.25, $0.275, $0.3025, etc. (each day increases by 10%)
    progressive_increase_percent = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)

    # Tiered configuration: JSON string like:
    # '[{"days": [0, 7], "rate": 0.25}, {"days": [8, 14], "rate": 0.50}]'
    tiered_configuration = Column(Text, nullable=True)

    # Maximum cap: don't charge more than this regardless of days overdue
    maximum_cap = Column(Numeric(10, 2), nullable=True)

    # Grace period: number of hours before fine starts accruing
    grace_period_hours = Column(Integer, default=0, nullable=False)

    # Min/max daily fine boundaries (for safety)
    minimum_fine_amount = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    maximum_daily_fine = Column(Numeric(10, 2), default=Decimal("50.00"), nullable=False)

    # Activation flags
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    applies_on_weekends = Column(Boolean, default=True, nullable=False)
    applies_on_holidays = Column(Boolean, default=False, nullable=False)

    # Tracking
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
