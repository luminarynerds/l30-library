# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, Date, ForeignKey, Index, Integer, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.core.database import Base
from app.models.mixins import TimestampMixin


# -- Enums ------------------------------------------------------------------

class PublicationFrequency(StrEnum):
    daily = "daily"
    weekly = "weekly"
    biweekly = "biweekly"
    semimonthly = "semimonthly"
    monthly = "monthly"
    bimonthly = "bimonthly"
    quarterly = "quarterly"
    semiannual = "semiannual"
    annual = "annual"
    irregular = "irregular"


class SubscriptionRenewalStatus(StrEnum):
    active = "active"
    pending_renewal = "pending_renewal"
    renewed = "renewed"
    cancelled = "cancelled"
    expired = "expired"


class SerialIssueStatus(StrEnum):
    expected = "expected"
    received = "received"
    claimed = "claimed"
    missing = "missing"
    damaged = "damaged"
    bound = "bound"


class ClaimType(StrEnum):
    not_received = "not_received"
    damaged_in_shipping = "damaged_in_shipping"
    wrong_issue = "wrong_issue"
    duplicate = "duplicate"


class ClaimResolution(StrEnum):
    received_replacement = "received_replacement"
    credited = "credited"
    no_response = "no_response"
    cancelled = "cancelled"


# -- Models -----------------------------------------------------------------

class SerialTitle(Base, TimestampMixin):
    __tablename__ = "serial_titles"

    id = Column(Integer, primary_key=True, index=True)
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=True, unique=True,
    )
    title = Column(String(500), nullable=False, index=True)
    issn_print = Column(String(9), nullable=True, unique=True)
    issn_electronic = Column(String(9), nullable=True)
    publisher = Column(String(255), nullable=True)
    country_of_publication = Column(String(3), nullable=True)
    language = Column(String(10), nullable=True)
    frequency = Column(
        String(50),
        nullable=False, default=PublicationFrequency.monthly,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    ceased_date = Column(Date, nullable=True)
    preceding_title_id = Column(
        Integer, ForeignKey("serial_titles.id", ondelete="SET NULL"), nullable=True,
    )
    succeeding_title_id = Column(
        Integer, ForeignKey("serial_titles.id", ondelete="SET NULL"), nullable=True,
    )
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])
    subscriptions = relationship("SerialSubscription", back_populates="serial_title", cascade="all, delete-orphan")
    prediction_patterns = relationship("SerialPredictionPattern", back_populates="serial_title", cascade="all, delete-orphan")
    issues = relationship("SerialIssue", back_populates="serial_title")
    preceding_title = relationship("SerialTitle", foreign_keys=[preceding_title_id], remote_side="SerialTitle.id")
    succeeding_title = relationship("SerialTitle", foreign_keys=[succeeding_title_id], remote_side="SerialTitle.id")
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_serial_titles_issn_print", "issn_print"),
        Index("ix_serial_titles_catalog_item", "catalog_item_id"),
    )


class SerialPredictionPattern(Base, TimestampMixin):
    __tablename__ = "serial_prediction_patterns"

    id = Column(Integer, primary_key=True, index=True)
    serial_title_id = Column(
        Integer, ForeignKey("serial_titles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    frequency = Column(
        String(50),
        nullable=False,
    )
    # JSONB for flexible pattern storage:
    # Monthly: {"day_of_month": 1, "issues_per_year": 12}
    # Monthly w/ combined: {"day_of_month": 1, "issues_per_year": 11, "combined_months": [[7, 8]]}
    # Weekly: {"day_of_week": 1, "issues_per_year": 52}
    # Irregular: {"expected_months": [1, 3, 5, 7, 9, 11]}
    # Gaps: {"publication_gaps": [{"from": "2025-03", "to": "2025-06"}]}
    pattern_details = Column(JSONB, nullable=False, default={})
    volume_scheme = Column(String(20), default="annual", nullable=False)  # annual, continuous, none
    starting_volume = Column(Integer, nullable=True)
    starting_number = Column(Integer, nullable=True)
    numbers_per_volume = Column(Integer, nullable=True)
    designation_template = Column(String(200), nullable=True)  # "Vol. {volume}, No. {number}"
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    serial_title = relationship("SerialTitle", back_populates="prediction_patterns")

    __table_args__ = (
        Index("ix_prediction_patterns_title_active", "serial_title_id", "is_active"),
    )


class SerialSubscription(Base, TimestampMixin):
    __tablename__ = "serial_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    serial_title_id = Column(
        Integer, ForeignKey("serial_titles.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    vendor_id = Column(
        Integer, ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    fund_id = Column(
        Integer, ForeignKey("funds.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    branch_id = Column(
        Integer, ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    subscription_number = Column(String(100), nullable=True)
    copies_ordered = Column(Integer, default=1, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    cost = Column(Numeric(12, 2), nullable=True)
    renewal_status = Column(
        String(50),
        nullable=False, default=SubscriptionRenewalStatus.active,
    )
    cancelled_date = Column(Date, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    serial_title = relationship("SerialTitle", back_populates="subscriptions")
    vendor = relationship("Vendor", foreign_keys=[vendor_id], back_populates="serial_subscriptions")
    fund = relationship("Fund", foreign_keys=[fund_id], back_populates="serial_subscriptions")
    branch = relationship("Branch", foreign_keys=[branch_id])
    issues = relationship("SerialIssue", back_populates="subscription")
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_serial_subs_renewal", "renewal_status", "end_date"),
    )


class SerialIssue(Base, TimestampMixin):
    __tablename__ = "serial_issues"

    id = Column(Integer, primary_key=True, index=True)
    serial_title_id = Column(
        Integer, ForeignKey("serial_titles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    serial_subscription_id = Column(
        Integer, ForeignKey("serial_subscriptions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    volume = Column(String(20), nullable=True)
    number = Column(String(20), nullable=True)
    designation = Column(String(200), nullable=True)  # "Vol. 45, No. 3"
    designation_override = Column(String(200), nullable=True)
    expected_date = Column(Date, nullable=False)
    received_date = Column(Date, nullable=True)
    received_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(
        String(50),
        nullable=False, default=SerialIssueStatus.expected,
    )
    is_combined = Column(Boolean, default=False, nullable=False)
    combined_designation = Column(String(100), nullable=True)  # "No. 7/8"
    is_supplement = Column(Boolean, default=False, nullable=False)
    supplement_title = Column(String(500), nullable=True)
    barcode = Column(String(50), nullable=True)
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True,
    )
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    serial_title = relationship("SerialTitle", back_populates="issues")
    subscription = relationship("SerialSubscription", back_populates="issues")
    received_by = relationship("User", foreign_keys=[received_by_id])
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])
    branch = relationship("Branch", foreign_keys=[branch_id])
    claims = relationship("SerialClaimLog", back_populates="serial_issue", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_serial_issues_title_expected", "serial_title_id", "expected_date"),
        Index("ix_serial_issues_title_status", "serial_title_id", "status"),
        Index("ix_serial_issues_subscription", "serial_subscription_id"),
        Index("ix_serial_issues_received_date", "received_date"),
        Index(
            "ix_serial_issues_expected_unreceived",
            "serial_title_id", "expected_date",
            postgresql_where=text("status IN ('expected', 'claimed')"),
        ),
        UniqueConstraint(
            "serial_title_id", "volume", "number", "serial_subscription_id",
            name="uq_serial_issue_identity",
        ),
    )


class SerialClaimLog(Base, TimestampMixin):
    __tablename__ = "serial_claim_logs"

    id = Column(Integer, primary_key=True, index=True)
    serial_issue_id = Column(
        Integer, ForeignKey("serial_issues.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    claim_date = Column(Date, nullable=False)
    claim_type = Column(
        String(50),
        nullable=False, default=ClaimType.not_received,
    )
    claim_number = Column(String(100), nullable=True)
    claimed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    response = Column(Text, nullable=True)
    vendor_response_date = Column(Date, nullable=True)
    replacement_expected_date = Column(Date, nullable=True)
    resolution = Column(
        String(50),
        nullable=True,
    )
    resolved_date = Column(Date, nullable=True)

    # Relationships
    serial_issue = relationship("SerialIssue", back_populates="claims")
    claimed_by = relationship("User", foreign_keys=[claimed_by_id])

    __table_args__ = (
        Index("ix_serial_claims_date", "claim_date"),
    )
