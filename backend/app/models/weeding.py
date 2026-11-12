# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class WeedingStatus(StrEnum):

    CANDIDATE = "candidate"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISPOSED = "disposed"


class WeedingReason(StrEnum):

    LOW_CIRCULATION = "low_circulation"
    POOR_CONDITION = "poor_condition"
    OUTDATED = "outdated"
    DUPLICATE = "duplicate"
    SUPERSEDED = "superseded"
    DAMAGED_BEYOND_REPAIR = "damaged_beyond_repair"
    MISSING_LONG_TERM = "missing_long_term"
    OUT_OF_SCOPE = "out_of_scope"
    NEVER_CIRCULATED = "never_circulated"
    SPACE_PRESSURE = "space_pressure"
    OTHER = "other"


class DisposalMethod(StrEnum):

    DISCARD = "discard"
    DONATION = "donation"
    SALE = "sale"
    RECYCLING = "recycling"
    TRANSFER = "transfer"
    OTHER = "other"


class CREWCategory(StrEnum):

    GENERAL_WORKS = "000"         # 10 years
    PHILOSOPHY = "100"            # 10 years
    RELIGION = "200"              # 10 years
    SOCIAL_SCIENCES = "300"       # 5 years
    LANGUAGE = "400"              # 10 years
    SCIENCE = "500"               # 5 years
    TECHNOLOGY = "600"            # 3 years (medical, computing)
    ARTS = "700"                  # 10 years
    LITERATURE = "800"            # never (classics)
    HISTORY_GEOGRAPHY = "900"     # 10 years
    FICTION = "fiction"            # 3 years no circ
    TRAVEL = "travel"             # 3 years
    LAW = "law"                   # 5 years
    MEDICAL = "medical"           # 3 years
    COMPUTING = "computing"       # 3 years


class DispositionRecommendation(StrEnum):

    DONATE_GOOD_CONDITION = "donate_good_condition"
    RECYCLE_POOR_CONDITION = "recycle_poor_condition"
    SELL_POPULAR_TITLE = "sell_popular_title"
    TRANSFER_TO_BRANCH = "transfer_to_branch"
    DISCARD = "discard"


class WeedingCandidate(Base):

    __tablename__ = "weeding_candidates"
    __table_args__ = (
        Index("ix_weeding_candidates_crew_score", "crew_score"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Reference to the item copy
    item_copy_id = Column(
        Integer, ForeignKey("item_copies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Workflow status
    status = Column(
        String(50),
        default=WeedingStatus.CANDIDATE,
        nullable=False,
        index=True,
    )

    # Weeding reason
    reason = Column(
        String(50),
        nullable=False,
    )
    reason_notes = Column(Text)  # Additional explanation

    # Metrics that led to weeding consideration
    last_checkout_date = Column(Date)  # When was it last checked out
    total_checkouts = Column(Integer, default=0)  # Total circulation count
    years_since_acquisition = Column(Integer)  # Age of the item
    condition_score = Column(Numeric(3, 2))  # 0.00 to 1.00 based on condition

    # CREW method fields
    crew_category = Column(
        String(50),
        nullable=True,
    )
    crew_score = Column(Float, default=0.0)  # Composite weeding score 0-100
    is_outdated_content = Column(Boolean, default=False)  # Flagged as outdated
    outdated_flags = Column(Text)  # JSON list of specific outdated flags
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)
    duplicate_count = Column(Integer, default=0)  # How many copies exist
    is_superseded = Column(Boolean, default=False)
    superseded_by_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)
    never_circulated = Column(Boolean, default=False)
    days_since_last_circulation = Column(Integer)
    section_fill_rate = Column(Float)  # 0.0 to 1.0 - how full the section is

    # Disposition recommendation
    disposition_recommendation = Column(
        String(50),
        nullable=True,
    )
    disposition_rationale = Column(Text)

    # Auto-generated flag
    auto_generated = Column(
        Boolean, default=False
    )  # Was this auto-flagged by the system?

    # Review process
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime(timezone=True))
    review_notes = Column(Text)

    # Approval process
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(DateTime(timezone=True))
    approval_notes = Column(Text)

    # Rejection (if not approved)
    rejected_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    rejected_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)

    # Disposal tracking
    disposal_method = Column(
        String(50)
    )
    disposal_date = Column(Date)
    disposal_notes = Column(Text)
    disposal_recipient = Column(Text)  # Who received it (donation, sale, etc.)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Relationships
    item_copy = relationship("ItemCopy")
    created_by = relationship("User", foreign_keys=[created_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    rejected_by = relationship("User", foreign_keys=[rejected_by_id])
    duplicate_of = relationship("CatalogItem", foreign_keys=[duplicate_of_item_id])
    superseded_by = relationship("CatalogItem", foreign_keys=[superseded_by_item_id])
    lifecycle_events = relationship(
        "ItemLifecycleEvent", back_populates="related_weeding",
        foreign_keys="[ItemLifecycleEvent.related_weeding_id]",
    )


class WeedingRule(Base):

    __tablename__ = "weeding_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)

    # CREW criteria thresholds
    crew_category = Column(
        String(50),
        nullable=True,
    )
    max_age_years = Column(Integer)  # Max years since publication
    max_years_no_circulation = Column(Integer)  # Max years with no checkouts
    min_condition_score = Column(Float)  # Below this = flag for condition
    max_duplicate_copies = Column(Integer)  # Above this = flag duplicates
    section_fill_threshold = Column(Float)  # Above this = space pressure

    # Subject-based content expiry (e.g., medical=3yr, tech=3yr, travel=3yr)
    subject_keywords = Column(Text)  # Comma-separated keywords to match
    location_filter = Column(String(100))  # Apply only to specific sections

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    created_by = relationship("User")
