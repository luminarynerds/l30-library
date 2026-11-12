# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from ..core.database import Base


class OperationCategory(StrEnum):
    CIRCULATION = "circulation"
    FINE = "fine"
    ACCOUNT = "account"
    PATRON = "patron"
    CATALOG = "catalog"
    MODERATION = "moderation"
    POLICY = "policy"
    SYSTEM = "system"


class OperationType(StrEnum):
    # Circulation operations
    CHECKOUT_CREATED = "checkout_created"
    CHECKOUT_RETURNED = "checkout_returned"
    CHECKOUT_RENEWED = "checkout_renewed"
    CHECKOUT_MARKED_OVERDUE = "checkout_marked_overdue"
    CHECKOUT_MARKED_LOST = "checkout_marked_lost"
    CHECKOUT_UNDONE = "checkout_undone"
    HOLD_PLACED = "hold_placed"
    HOLD_FULFILLED = "hold_fulfilled"
    HOLD_CANCELLED = "hold_cancelled"
    HOLD_EXPIRED = "hold_expired"
    HOLD_OVERRIDDEN = "hold_overridden"

    # Fine operations
    FINE_ASSESSED = "fine_assessed"
    FINE_WAIVED = "fine_waived"
    FINE_PAID = "fine_paid"
    FINE_PARTIAL_PAYMENT = "fine_partial_payment"
    FINE_PAYMENT_REVERSED = "fine_payment_reversed"

    # Patron operations
    PATRON_CREATED = "patron_created"
    PATRON_UPDATED = "patron_updated"
    PATRON_DEACTIVATED = "patron_deactivated"
    PATRON_REACTIVATED = "patron_reactivated"
    PATRON_SUSPENDED = "patron_suspended"
    PATRON_UNSUSPENDED = "patron_unsuspended"
    PATRON_BLOCKED = "patron_blocked"
    PATRON_UNBLOCKED = "patron_unblocked"
    PATRON_MERGED = "patron_merged"
    PATRON_DELETED = "patron_deleted"
    PATRON_ROLE_CHANGED = "patron_role_changed"

    # Catalog operations
    ITEM_CREATED = "item_created"
    ITEM_STATUS_CHANGED = "item_status_changed"
    ITEM_WITHDRAWN = "item_withdrawn"
    ITEM_MARKED_MISSING = "item_marked_missing"
    ITEM_MARKED_DAMAGED = "item_marked_damaged"

    # Policy operations
    POLICY_CHECKOUT_LIMIT_CHANGED = "policy_checkout_limit_changed"
    POLICY_LOAN_PERIOD_CHANGED = "policy_loan_period_changed"
    POLICY_FINE_RATE_CHANGED = "policy_fine_rate_changed"
    POLICY_HOLD_LIMIT_CHANGED = "policy_hold_limit_changed"
    POLICY_RENEWAL_LIMIT_CHANGED = "policy_renewal_limit_changed"
    POLICY_ROLE_SETTINGS_CHANGED = "policy_role_settings_changed"
    POLICY_FINE_POLICY_CHANGED = "policy_fine_policy_changed"

    # Account / financial operations
    ACCOUNT_DEPOSIT = "account_deposit"
    ACCOUNT_CHARGE = "account_charge"
    ACCOUNT_REFUND = "account_refund"

    # Content moderation operations
    EBOOK_APPROVED = "ebook_approved"
    EBOOK_DECLINED = "ebook_declined"

    # Training / learning operations (Wave 4 — manager assign workflow)
    TRAINING_ASSIGNED = "training_assigned"

    # System operations
    SYSTEM_DATA_RETENTION_RUN = "system_data_retention_run"
    SYSTEM_BULK_OPERATION = "system_bulk_operation"
    SYSTEM_MIGRATION_APPLIED = "system_migration_applied"
    SYSTEM_REPORT_GENERATED = "system_report_generated"

    # Public-computer session lifecycle
    COMPUTER_SESSION_ENDED = "computer_session_ended"
    COMPUTER_SESSION_REOPENED = "computer_session_reopened"


class OperationsAuditLog(Base):
    __tablename__ = "operations_audit_log"

    __table_args__ = (
        # Primary access patterns for auditors:
        Index("ix_ops_audit_category_ts", "category", "created_at"),
        Index("ix_ops_audit_operation_ts", "operation_type", "created_at"),
        Index("ix_ops_audit_patron", "patron_id", "created_at"),
        Index("ix_ops_audit_staff", "staff_id", "created_at"),
        Index("ix_ops_audit_item", "item_id", "created_at"),
        Index("ix_ops_audit_correlation", "correlation_id"),
        # For answering "what happened on this date?"
        Index("ix_ops_audit_created_at", "created_at"),
        # For financial auditing: all fine operations by staff
        Index(
            "ix_ops_audit_fine_staff",
            "staff_id",
            "created_at",
            postgresql_where="category = 'FINE'",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # What happened
    category = Column(String(50), nullable=False)
    operation_type = Column(String(80), nullable=False)

    # Who was involved (denormalized snapshots)
    patron_id = Column(Integer, nullable=True)
    patron_identifier = Column(
        String(255), nullable=True,
        comment="Denormalized: e.g. 'card:29001234567' or 'email:jdoe@example.com'"
    )
    staff_id = Column(Integer, nullable=True)
    staff_identifier = Column(
        String(255), nullable=True,
        comment="Denormalized: e.g. 'email:staff@library.org'"
    )

    # What was affected
    item_id = Column(Integer, nullable=True)
    item_identifier = Column(
        String(255), nullable=True,
        comment="Denormalized: e.g. 'barcode:31201001234567' or 'title:The Great Gatsby'"
    )
    checkout_id = Column(Integer, nullable=True)
    fine_id = Column(Integer, nullable=True)
    hold_id = Column(Integer, nullable=True)

    # Financial impact (for fine operations)
    amount_cents = Column(
        Integer, nullable=True,
        comment="Financial amount in cents (e.g. 5000 = $50.00)"
    )

    # State snapshots for forensic reconstruction
    before_state = Column(
        JSONB, nullable=True,
        comment="Snapshot of relevant state before the operation"
    )
    after_state = Column(
        JSONB, nullable=True,
        comment="Snapshot of relevant state after the operation"
    )

    # Context
    reason = Column(Text, nullable=True, comment="Human-readable reason for the operation")
    correlation_id = Column(
        String(36), nullable=True,
        comment="UUID linking related operations in a single workflow"
    )
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # When
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<OperationsAuditLog(id={self.id}, "
            f"op={self.operation_type}, "
            f"patron={self.patron_id}, "
            f"staff={self.staff_id}, "
            f"ts={self.created_at})>"
        )


class PolicyChangeLog(Base):
    __tablename__ = "policy_change_log"

    __table_args__ = (
        Index("ix_policy_change_ts", "created_at"),
        Index("ix_policy_change_type", "policy_type", "created_at"),
        Index("ix_policy_change_staff", "changed_by_staff_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # What policy changed
    policy_type = Column(
        String(80), nullable=False,
        comment="e.g. 'role_settings', 'fine_policy', 'circulation_config'"
    )
    policy_name = Column(
        String(255), nullable=False,
        comment="Human-readable name, e.g. 'PATRON checkout limit' or 'Overdue daily rate'"
    )

    # Who changed it
    changed_by_staff_id = Column(Integer, nullable=True)
    changed_by_identifier = Column(
        String(255), nullable=True,
        comment="Denormalized: e.g. 'email:admin@library.org'"
    )

    # What changed
    before_value = Column(JSONB, nullable=True, comment="Complete policy state before change")
    after_value = Column(JSONB, nullable=True, comment="Complete policy state after change")
    fields_changed = Column(
        JSONB, nullable=True,
        comment="List of specific fields that changed, e.g. ['max_checkouts', 'checkout_duration_days']"
    )

    # Context
    reason = Column(Text, nullable=True, comment="Why the change was made")
    ip_address = Column(String(45), nullable=True)

    # When
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<PolicyChangeLog(id={self.id}, "
            f"type={self.policy_type}, "
            f"name={self.policy_name}, "
            f"ts={self.created_at})>"
        )
