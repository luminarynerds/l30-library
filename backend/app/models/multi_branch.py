# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    Index,
    JSON,
    and_,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship, foreign
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


# =============================================================================
# ENUMS
# =============================================================================


class BranchType(StrEnum):
    MAIN = "main"
    BRANCH = "branch"
    BOOKMOBILE = "bookmobile"
    KIOSK = "kiosk"
    DIGITAL_ONLY = "digital_only"
    OUTREACH = "outreach"


class BranchStatus(StrEnum):
    ACTIVE = "active"
    TEMPORARILY_CLOSED = "temporarily_closed"
    PERMANENTLY_CLOSED = "permanently_closed"
    UNDER_RENOVATION = "under_renovation"
    PLANNED = "planned"


class DayOfWeek(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class TransitStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    CANCELLED = "cancelled"
    LOST_IN_TRANSIT = "lost_in_transit"
    # Legacy values from seed data
    PENDING = "pending"
    COMPLETED = "completed"


class TransitPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    # Legacy values from seed data
    RUSH = "rush"


class TransitReason(StrEnum):
    HOLD_FULFILLMENT = "hold_fulfillment"
    REBALANCING = "rebalancing"
    RETURN_TO_HOME = "return_to_home"
    COLLECTION_TRANSFER = "collection_transfer"
    REPAIR = "repair"
    WEEDING = "weeding"
    SPECIAL_REQUEST = "special_request"
    # Legacy values from seed data
    HOLD = "hold"
    RETURN = "return"
    REBALANCE = "rebalance"


class ConsortiumMemberType(StrEnum):
    FOUNDING = "founding"
    FULL = "full"
    ASSOCIATE = "associate"
    AFFILIATE = "affiliate"
    TRIAL = "trial"


class ConsortiumMemberStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    EXPIRED = "expired"


class BillingCycleType(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


class BillingItemType(StrEnum):
    MEMBERSHIP_FEE = "membership_fee"
    ILL_FEE = "ill_fee"
    TRANSIT_FEE = "transit_fee"
    LOST_ITEM_REIMBURSEMENT = "lost_item_reimbursement"
    DAMAGED_ITEM_REIMBURSEMENT = "damaged_item_reimbursement"
    SERVICE_FEE = "service_fee"
    CREDIT = "credit"
    ADJUSTMENT = "adjustment"


class BillingStatus(StrEnum):
    PENDING = "pending"
    INVOICED = "invoiced"
    PAID = "paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"
    WRITTEN_OFF = "written_off"


class SettingScopeLevel(StrEnum):
    CONSORTIUM = "consortium"
    SYSTEM = "system"
    REGION = "region"
    BRANCH = "branch"


class FloatingCollectionType(StrEnum):
    NO_FLOAT = "no_float"  # Always returns to home branch
    SYSTEM_FLOAT = "system_float"  # Floats within the system
    REGION_FLOAT = "region_float"  # Floats within region only
    CONSORTIUM_FLOAT = "consortium_float"  # Floats across consortium


# =============================================================================
# LIBRARY SYSTEM (Top-level organization)
# =============================================================================


class LibrarySystem(TimestampMixin, Base):
    __tablename__ = "library_systems"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)  # e.g., "MCLS"
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255))  # Official legal name if different

    # Contact information
    website = Column(String(255))
    email = Column(String(255))
    phone = Column(String(20))
    fax = Column(String(20))

    # Address
    address_line1 = Column(String(100))
    address_line2 = Column(String(100))
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(10))
    country = Column(String(50), default="USA")

    # Tax/legal identifiers
    tax_id = Column(String(50))  # EIN for US libraries
    state_library_id = Column(String(50))  # State library system identifier

    # Governance
    governance_type = Column(String(50))  # municipal, county, district, etc.
    fiscal_year_start_month = Column(Integer, default=7)  # July for most libraries

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timezone for the system
    timezone = Column(String(50), default="America/New_York")

    # Relationships
    regions = relationship("Region", back_populates="library_system", cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="library_system", cascade="all, delete-orphan")
    consortium_membership = relationship(
        "ConsortiumMember", back_populates="library_system", uselist=False
    )
    system_settings = relationship(
        "SystemSettings",
        back_populates="library_system",
        uselist=False,
        cascade="all, delete-orphan",
    )


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    library_system_id = Column(
        Integer, ForeignKey("library_systems.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Circulation policies (system defaults)
    default_loan_period_days = Column(Integer, default=21)
    default_renewal_limit = Column(Integer, default=2)
    default_hold_limit = Column(Integer, default=10)
    default_checkout_limit = Column(Integer, default=50)

    # Fine policies
    default_overdue_fine_per_day = Column(Numeric(10, 2), default=0.25)
    default_max_fine = Column(Numeric(10, 2), default=10.00)
    grace_period_days = Column(Integer, default=0)
    fine_free_juvenile = Column(Boolean, default=False)

    # Reporting basis (used by state annual report + board monthly report)
    fte_annual_hours = Column(Integer, default=2080, nullable=True)
    volunteer_hour_value = Column(Numeric(10, 2), default=33.49, nullable=True)

    # Lost item policies
    lost_item_threshold_days = Column(Integer, default=30)
    default_replacement_cost = Column(Numeric(10, 2), default=25.00)
    processing_fee = Column(Numeric(10, 2), default=5.00)

    # Hold policies
    hold_pickup_days = Column(Integer, default=7)
    allow_hold_on_available = Column(Boolean, default=True)

    # Transit policies
    transit_time_estimate_days = Column(Integer, default=2)
    auto_approve_transit = Column(Boolean, default=True)

    # Patron policies
    require_address_verification = Column(Boolean, default=True)
    allow_self_registration = Column(Boolean, default=True)
    card_expiry_years = Column(Integer, default=3)

    # Age-based account transition settings
    age_transition_threshold = Column(
        Integer, default=18
    )  # Age at which CHILD accounts auto-transition to PATRON
    auto_transition_enabled = Column(
        Boolean, default=True
    )  # Enable/disable automatic child-to-adult transitions
    forgive_reading_minutes_on_transition = Column(
        Boolean, default=True
    )  # Forgive outstanding reading minutes on transition

    # Notifications
    overdue_notice_days = Column(JSON)  # [1, 7, 14, 21] - days after due date
    courtesy_notice_days = Column(Integer, default=3)  # days before due

    # Feature flags
    enable_floating_collections = Column(Boolean, default=False)
    enable_reciprocal_borrowing = Column(Boolean, default=False)
    enable_self_checkout = Column(Boolean, default=True)

    # Setup wizard
    setup_complete = Column(Boolean, default=False, nullable=False)

    # Metadata, onupdate=func.now())

    # Relationships
    library_system = relationship("LibrarySystem", back_populates="system_settings")


# =============================================================================
# REGION (Optional grouping level)
# =============================================================================


class Region(TimestampMixin, Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True)
    library_system_id = Column(
        Integer, ForeignKey("library_systems.id", ondelete="CASCADE"), nullable=False
    )

    code = Column(String(20), nullable=False, index=True)  # e.g., "NORTH"
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Region manager (SET NULL: preserve manager history if user deleted)
    manager_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    library_system = relationship("LibrarySystem", back_populates="regions")
    branches = relationship("Branch", back_populates="region")
    manager = relationship("User", foreign_keys=[manager_user_id])

    __table_args__ = (UniqueConstraint("library_system_id", "code", name="uq_region_system_code"),)


# =============================================================================
# BRANCH
# =============================================================================


class Branch(Base, TimestampMixin):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    library_system_id = Column(
        Integer, ForeignKey("library_systems.id", ondelete="CASCADE"), nullable=False
    )
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="SET NULL"), index=True)

    # Identification
    code = Column(String(20), nullable=False, index=True)  # e.g., "MAIN", "NORTH1"
    name = Column(String(255), nullable=False)
    short_name = Column(String(50))  # For display in compact views

    # Type and status
    branch_type = Column(String(50), default=BranchType.BRANCH, nullable=False)
    status = Column(String(50), default=BranchStatus.ACTIVE, nullable=False)

    # Contact information
    phone = Column(String(20))
    fax = Column(String(20))
    email = Column(String(255))
    website = Column(String(255))

    # Address
    address_line1 = Column(String(100))
    address_line2 = Column(String(100))
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(10))
    country = Column(String(50), default="USA")

    # Geographic coordinates (for maps)
    latitude = Column(Float)
    longitude = Column(Float)

    # Physical details
    square_footage = Column(Integer)
    parking_spaces = Column(Integer)
    is_ada_accessible = Column(Boolean, default=True)

    # Services available at this branch
    has_meeting_rooms = Column(Boolean, default=False)
    has_computer_lab = Column(Boolean, default=True)
    has_makerspace = Column(Boolean, default=False)
    has_drive_through = Column(Boolean, default=False)
    has_book_drop = Column(Boolean, default=True)
    has_self_checkout = Column(Boolean, default=True)

    # Staffing (SET NULL: preserve branch manager history if user deleted)
    branch_manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)

    # ILS codes for integration
    ils_location_code = Column(String(50))  # For SIP2/NCIP integration

    # Sort order for display
    display_order = Column(Integer, default=0)

    # Dates
    opened_date = Column(Date)
    closed_date = Column(Date)

    # Relationships
    library_system = relationship("LibrarySystem", back_populates="branches")
    region = relationship("Region", back_populates="branches")
    branch_manager = relationship("User", foreign_keys=[branch_manager_id])
    # DISABLED: hours relationship
    # DISABLED: closures relationship
    # DISABLED: settings relationship
    # DISABLED: item_copies relationship (back_populates to disabled current_branch on BranchItemCopy)

    __table_args__ = (
        UniqueConstraint("library_system_id", "code", name="uq_branch_system_code"),
        Index("ix_branch_system_status", "library_system_id", "status"),
    )

    @property
    def full_address(self) -> str:
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.append(f"{self.city}, {self.state} {self.zip_code}")
        return "\n".join(parts)


class BranchHours(TimestampMixin, Base):
    __tablename__ = "branch_hours"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, nullable=False)

    day_of_week = Column(String(50), nullable=False)

    # Regular hours
    is_closed = Column(Boolean, default=False)
    open_time = Column(Time)
    close_time = Column(Time)

    # Optional second shift (e.g., closed for lunch)
    open_time_2 = Column(Time)
    close_time_2 = Column(Time)

    # Effective dates (for seasonal variations)
    effective_from = Column(Date)
    effective_until = Column(Date)

    # Notes
    notes = Column(String(255))

    # Relationships
    # DISABLED: # DISABLED: branch relationship

    __table_args__ = (
        Index("ix_branch_hours_effective", "branch_id", "day_of_week", "effective_from"),
    )


class BranchClosure(Base):
    __tablename__ = "branch_closures"

    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, nullable=False)

    # Closure period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # If partial day closure
    start_time = Column(Time)
    end_time = Column(Time)

    # Details
    reason = Column(String(255), nullable=False)
    description = Column(Text)

    # Is this a system-wide closure?
    is_system_wide = Column(Boolean, default=False)

    # Recurring annual (e.g., Christmas)
    is_annual = Column(Boolean, default=False)

    # =========================================================================
    # CLOSURE MANAGEMENT STATUS TRACKING
    # =========================================================================

    # Notification status
    patrons_with_holds_notified = Column(Boolean, default=False)
    staff_notified = Column(Boolean, default=False)
    partner_organizations_notified = Column(Boolean, default=False)

    # External service update status
    website_updated = Column(Boolean, default=False)
    phone_message_updated = Column(Boolean, default=False)
    social_media_updated = Column(Boolean, default=False)
    google_maps_updated = Column(Boolean, default=False)
    apple_maps_updated = Column(Boolean, default=False)

    # Event and program management
    events_canceled = Column(Boolean, default=False)
    programs_rescheduled = Column(Boolean, default=False)

    # Details and documentation
    closure_documentation = Column(Text)  # Detailed reason/impact documentation
    reopening_announcement = Column(Text)  # Message for reopening announcement

    # Metadata (SET NULL: preserve audit trail)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    # DISABLED: # DISABLED: branch relationship
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])

    __table_args__ = (
        Index("ix_branch_closure_dates", "branch_id", "start_date", "end_date"),
        Index("ix_branch_closure_status", "branch_id", "staff_notified", "website_updated"),
    )


class BranchSettings(Base):
    __tablename__ = "branch_settings"

    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, nullable=False, unique=True)

    # Override circulation policies (null means use system default)
    loan_period_days = Column(Integer)
    renewal_limit = Column(Integer)
    hold_limit = Column(Integer)
    checkout_limit = Column(Integer)

    # Override fine policies
    overdue_fine_per_day = Column(Numeric(10, 2))
    max_fine = Column(Numeric(10, 2))
    fine_free = Column(Boolean)

    # Branch-specific features
    allow_ill_pickup = Column(Boolean, default=True)  # ILL pickup location
    allow_hold_pickup = Column(Boolean, default=True)  # Hold pickup location
    allow_returns = Column(Boolean, default=True)  # Accept returns from other branches

    # Floating collection behavior
    floating_type = Column(String(50), default=FloatingCollectionType.NO_FLOAT)

    # Notification settings
    default_pickup_branch = Column(Boolean, default=True)  # Default pickup for web holds

    # Hold shelf capacity management
    hold_shelf_capacity = Column(Integer, default=500)  # Max items that can be on hold shelf
    hold_shelf_warning_threshold = Column(
        Integer, default=80
    )  # Percentage: warn when shelf is 80% full

    # Custom messaging
    checkout_message = Column(Text)  # Displayed at checkout
    hold_pickup_message = Column(Text)  # For hold pickup notices

    # Print settings
    print_receipt_header = Column(Text)
    print_receipt_footer = Column(Text)

    # Metadata, onupdate=func.now())

    # Relationships
    # DISABLED: # DISABLED: branch relationship


# =============================================================================
# BRANCH-SCOPED INVENTORY
# =============================================================================


class BranchItemCopy(Base):
    __tablename__ = "branch_item_copies"

    id = Column(Integer, primary_key=True)
    item_copy_id = Column(Integer, ForeignKey("item_copies.id", ondelete="CASCADE"), nullable=False)

    # Home branch (may be null for floating items)
    home_branch_id = Column(Integer)

    # Current location
    current_branch_id = Column(Integer, nullable=False)

    # For floating collections
    is_floating = Column(Boolean, default=False)
    float_scope = Column(String(50), default=FloatingCollectionType.NO_FLOAT)

    # Status tracking
    last_seen_at = Column(DateTime(timezone=True))
    last_circulated_branch_id = Column(Integer)

    # Shelving location at this branch
    shelving_location = Column(String(100))  # e.g., "Adult Fiction A-3"

    # Metadata
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    item_copy = relationship("ItemCopy")
    # DISABLED: # DISABLED: home_branch relationship
    # DISABLED: current_branch relationship
    # DISABLED: last_circulated_branch relationship

    __table_args__ = (
        UniqueConstraint("item_copy_id", name="uq_branch_item_copy"),
        Index("ix_branch_item_current", "current_branch_id", "item_copy_id"),
    )


# =============================================================================
# TRANSIT SYSTEM
# =============================================================================


class TransitRequest(Base):
    __tablename__ = "transit_requests"

    id = Column(Integer, primary_key=True)

    # Item being moved
    item_copy_id = Column(Integer, ForeignKey("item_copies.id", ondelete="CASCADE"), nullable=False)

    # Source and destination
    from_branch_id = Column(Integer, nullable=False)
    to_branch_id = Column(Integer, nullable=False)

    # Request details
    reason = Column(String(50), nullable=False)
    priority = Column(String(50), default=TransitPriority.NORMAL, nullable=False)
    status = Column(String(50), default=TransitStatus.REQUESTED, nullable=False)

    # Associated hold (if for hold fulfillment)
    hold_id = Column(Integer, ForeignKey("holds.id", ondelete="SET NULL"))

    # Tracking (SET NULL: preserve audit trail of staff actions)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Nullable: system-generated transits (e.g. auto return-to-home on
    # check-in) have no requesting user. This also makes the column
    # consistent with its own ondelete="SET NULL", which could never have
    # fired against a NOT NULL column.
    requested_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    approved_at = Column(DateTime(timezone=True))
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    picked_up_at = Column(DateTime(timezone=True))
    picked_up_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    shipped_at = Column(DateTime(timezone=True))

    received_at = Column(DateTime(timezone=True))
    received_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    cancelled_at = Column(DateTime(timezone=True))
    cancelled_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    cancellation_reason = Column(String(255))

    # Expected delivery
    expected_arrival_date = Column(Date)

    # Notes
    notes = Column(Text)

    # Metadata, onupdate=func.now())

    # Relationships
    item_copy = relationship("ItemCopy")
    # DISABLED: # DISABLED: from_branch relationship
    # DISABLED: # DISABLED: to_branch relationship
    hold = relationship("Hold")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    picked_up_by = relationship("User", foreign_keys=[picked_up_by_id])
    received_by = relationship("User", foreign_keys=[received_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])

    __table_args__ = (
        Index("ix_transit_request_status", "status", "from_branch_id"),
        Index("ix_transit_request_to_branch", "status", "to_branch_id"),
    )


class TransitShipment(Base):
    __tablename__ = "transit_shipments"

    id = Column(Integer, primary_key=True)

    # Shipment identification
    shipment_number = Column(String(50), unique=True, nullable=False, index=True)

    # Route
    from_branch_id = Column(Integer, nullable=False)
    to_branch_id = Column(Integer, nullable=False)

    # Shipment details
    item_count = Column(Integer, default=0)
    container_count = Column(Integer, default=1)  # Number of bins/bags

    # Tracking (SET NULL: preserve audit trail)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    shipped_at = Column(DateTime(timezone=True))
    shipped_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    received_at = Column(DateTime(timezone=True))
    received_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Carrier information (if using external courier)
    carrier = Column(String(100))
    tracking_number = Column(String(100))

    # Notes
    notes = Column(Text)

    # Relationships
    # DISABLED: # DISABLED: from_branch relationship
    # DISABLED: # DISABLED: to_branch relationship
    created_by = relationship("User", foreign_keys=[created_by_id])
    shipped_by = relationship("User", foreign_keys=[shipped_by_id])
    received_by = relationship("User", foreign_keys=[received_by_id])
    items = relationship(
        "TransitShipmentItem", back_populates="shipment", cascade="all, delete-orphan"
    )


class TransitShipmentItem(Base):
    __tablename__ = "transit_shipment_items"

    id = Column(Integer, primary_key=True)
    shipment_id = Column(
        Integer, ForeignKey("transit_shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transit_request_id = Column(
        Integer, ForeignKey("transit_requests.id", ondelete="CASCADE"), nullable=False
    )

    # Tracking
    scanned_in_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    scanned_in_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    received_at = Column(DateTime(timezone=True))
    received_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Discrepancy notes
    notes = Column(Text)

    # Relationships
    shipment = relationship("TransitShipment", back_populates="items")
    transit_request = relationship("TransitRequest")
    scanned_in_by = relationship("User", foreign_keys=[scanned_in_by_id])
    received_by = relationship("User", foreign_keys=[received_by_id])


# =============================================================================
# CONSORTIUM
# =============================================================================


class Consortium(TimestampMixin, Base):
    __tablename__ = "consortiums"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255))

    # Contact
    website = Column(String(255))
    email = Column(String(255))
    phone = Column(String(20))

    # Address
    address_line1 = Column(String(100))
    address_line2 = Column(String(100))
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(10))
    country = Column(String(50), default="USA")

    # Governance
    established_date = Column(Date)
    governing_document_url = Column(String(255))  # Link to MOU/Agreement

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    members = relationship(
        "ConsortiumMember", back_populates="consortium", cascade="all, delete-orphan"
    )
    settings = relationship(
        "ConsortiumSettings",
        back_populates="consortium",
        uselist=False,
        cascade="all, delete-orphan",
    )
    billing_records = relationship(
        "ConsortiumBilling", back_populates="consortium", cascade="all, delete-orphan"
    )


class ConsortiumMember(TimestampMixin, Base):
    __tablename__ = "consortium_members"

    id = Column(Integer, primary_key=True, index=True)
    consortium_id = Column(
        Integer, ForeignKey("consortiums.id", ondelete="CASCADE"), nullable=False
    )
    library_system_id = Column(
        Integer, ForeignKey("library_systems.id", ondelete="CASCADE"), nullable=False
    )

    # Membership details
    member_type = Column(String(50), default=ConsortiumMemberType.FULL, nullable=False)
    status = Column(String(50), default=ConsortiumMemberStatus.ACTIVE, nullable=False)

    # Dates
    joined_date = Column(Date, nullable=False)
    expiry_date = Column(Date)

    # Voting rights
    voting_member = Column(Boolean, default=True)
    vote_weight = Column(Integer, default=1)  # For weighted voting

    # Financial
    annual_fee = Column(Numeric(10, 2))
    fee_paid_through = Column(Date)

    # Contact for consortium matters (SET NULL: preserve liaison history)
    liaison_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    consortium = relationship("Consortium", back_populates="members")
    library_system = relationship("LibrarySystem", back_populates="consortium_membership")
    liaison = relationship("User")
    reciprocal_settings = relationship(
        "ReciprocalBorrowingSettings",
        back_populates="member",
        uselist=False,
        cascade="all, delete-orphan",
    )
    white_label = relationship(
        "ConsortiumWhiteLabel", back_populates="member", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("consortium_id", "library_system_id", name="uq_consortium_member"),
    )


class ConsortiumSettings(Base):
    __tablename__ = "consortium_settings"

    id = Column(Integer, primary_key=True)
    consortium_id = Column(
        Integer, ForeignKey("consortiums.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Shared catalog settings
    enable_shared_catalog = Column(Boolean, default=True)
    catalog_search_all_members = Column(Boolean, default=True)

    # Reciprocal borrowing
    enable_reciprocal_borrowing = Column(Boolean, default=True)
    reciprocal_checkout_limit = Column(Integer, default=5)
    reciprocal_hold_limit = Column(Integer, default=3)

    # ILL (Interlibrary Loan)
    enable_ill = Column(Boolean, default=True)
    ill_request_limit = Column(Integer, default=10)
    ill_loan_period_days = Column(Integer, default=21)

    # Transit
    enable_consortium_transit = Column(Boolean, default=True)
    default_transit_time_days = Column(Integer, default=3)

    # Authentication
    enable_single_sign_on = Column(Boolean, default=False)
    sso_provider = Column(String(50))  # e.g., "saml", "oauth2", "ldap"
    sso_config = Column(JSON)  # Provider-specific configuration

    # Cost sharing model
    cost_sharing_model = Column(
        String(50)
    )  # e.g., "per_transaction", "fixed_fee", "population_based"
    ill_fee_per_item = Column(Numeric(10, 2), default=0.00)
    transit_fee_per_item = Column(Numeric(10, 2), default=0.00)

    # Billing
    billing_cycle = Column(String(50), default=BillingCycleType.QUARTERLY)

    # Floating collections
    enable_consortium_float = Column(Boolean, default=False)

    # Metadata, onupdate=func.now())

    # Relationships
    consortium = relationship("Consortium", back_populates="settings")


class ReciprocalBorrowingSettings(Base):
    __tablename__ = "reciprocal_borrowing_settings"

    id = Column(Integer, primary_key=True)
    member_id = Column(
        Integer,
        ForeignKey("consortium_members.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Allow patrons from other systems to borrow here
    allow_incoming_borrowers = Column(Boolean, default=True)
    incoming_checkout_limit = Column(Integer, default=5)
    incoming_hold_limit = Column(Integer, default=3)

    # Allow local patrons to borrow at other systems
    allow_outgoing_borrowers = Column(Boolean, default=True)

    # Registration requirements
    require_registration = Column(Boolean, default=True)
    registration_valid_days = Column(Integer, default=365)

    # Restrictions
    blocked_item_types = Column(JSON)  # e.g., ["new_releases", "dvd", "equipment"]
    restricted_collections = Column(JSON)  # Collection codes that can't be borrowed

    # Metadata, onupdate=func.now())

    # Relationships
    member = relationship("ConsortiumMember", back_populates="reciprocal_settings")


# =============================================================================
# COST SHARING / BILLING
# =============================================================================


class ConsortiumBilling(TimestampMixin, Base):
    __tablename__ = "consortium_billing"

    id = Column(Integer, primary_key=True)
    consortium_id = Column(
        Integer, ForeignKey("consortiums.id", ondelete="CASCADE"), nullable=False
    )

    # Billing parties
    billing_member_id = Column(
        Integer, ForeignKey("consortium_members.id", ondelete="CASCADE"), nullable=False
    )
    billed_member_id = Column(
        Integer, ForeignKey("consortium_members.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Billing details
    billing_period_start = Column(Date, nullable=False)
    billing_period_end = Column(Date, nullable=False)

    item_type = Column(String(50), nullable=False)

    # Amount
    quantity = Column(Integer, default=1)
    unit_amount = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)

    # Status
    status = Column(String(50), default=BillingStatus.PENDING, nullable=False)

    # Invoice tracking
    invoice_number = Column(String(50), index=True)
    invoiced_at = Column(DateTime(timezone=True))
    due_date = Column(Date)
    paid_at = Column(DateTime(timezone=True))
    payment_reference = Column(String(100))

    # Dispute handling
    disputed_at = Column(DateTime(timezone=True))
    dispute_reason = Column(Text)
    dispute_resolved_at = Column(DateTime(timezone=True))

    # Description
    description = Column(Text)
    reference_ids = Column(JSON)  # IDs of related transactions (ILL, transit, etc.)

    # Relationships
    consortium = relationship("Consortium", back_populates="billing_records")
    billing_member = relationship("ConsortiumMember", foreign_keys=[billing_member_id])
    billed_member = relationship("ConsortiumMember", foreign_keys=[billed_member_id])

    __table_args__ = (
        Index("ix_billing_period", "consortium_id", "billing_period_start", "billing_period_end"),
        Index("ix_billing_status", "status", "due_date"),
    )


class ConsortiumTransaction(Base):
    __tablename__ = "consortium_transactions"

    id = Column(Integer, primary_key=True, index=True)
    consortium_id = Column(
        Integer, ForeignKey("consortiums.id", ondelete="CASCADE"), nullable=False
    )

    # Transaction type
    transaction_type = Column(
        String(50), nullable=False
    )  # e.g., "ill_loan", "reciprocal_checkout", "transit"

    # Parties involved (SET NULL: preserve transaction history)
    lending_member_id = Column(Integer, ForeignKey("consortium_members.id", ondelete="SET NULL"))
    borrowing_member_id = Column(
        Integer, ForeignKey("consortium_members.id", ondelete="SET NULL"), index=True
    )

    # Item and patron (if applicable)
    item_copy_id = Column(Integer, ForeignKey("item_copies.id", ondelete="SET NULL"))
    patron_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Transaction details
    transaction_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fee_amount = Column(Numeric(10, 2), default=0.00)

    # Billing status
    billed = Column(Boolean, default=False)
    billing_record_id = Column(Integer, ForeignKey("consortium_billing.id", ondelete="SET NULL"))

    # Reference to original transaction
    reference_type = Column(String(50))  # e.g., "checkout", "hold", "ill_request"
    reference_id = Column(Integer)

    # Notes
    notes = Column(Text)

    # Relationships
    consortium = relationship("Consortium")
    lending_member = relationship("ConsortiumMember", foreign_keys=[lending_member_id])
    borrowing_member = relationship("ConsortiumMember", foreign_keys=[borrowing_member_id])
    item_copy = relationship("ItemCopy")
    patron = relationship("User")
    billing_record = relationship("ConsortiumBilling")

    __table_args__ = (
        Index("ix_consortium_tx_date", "consortium_id", "transaction_date"),
        Index("ix_consortium_tx_unbilled", "billed", "transaction_date"),
    )


# =============================================================================
# CONSORTIUM AUTHENTICATION
# =============================================================================


class ConsortiumPatronLink(TimestampMixin, Base):
    __tablename__ = "consortium_patron_links"

    id = Column(Integer, primary_key=True, index=True)

    # The home system patron
    home_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    home_member_id = Column(
        Integer, ForeignKey("consortium_members.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Linked system
    linked_member_id = Column(
        Integer, ForeignKey("consortium_members.id", ondelete="CASCADE"), nullable=False
    )

    # Registration at linked system
    linked_card_number = Column(String(50))  # Card number at the linked system
    registered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True))

    # Status
    is_active = Column(Boolean, default=True)
    blocked = Column(Boolean, default=False)
    blocked_reason = Column(String(255))

    # Usage tracking
    last_used_at = Column(DateTime(timezone=True))
    total_checkouts = Column(Integer, default=0)

    # Relationships
    home_user = relationship("User")
    home_member = relationship("ConsortiumMember", foreign_keys=[home_member_id])
    linked_member = relationship("ConsortiumMember", foreign_keys=[linked_member_id])

    __table_args__ = (
        UniqueConstraint("home_user_id", "linked_member_id", name="uq_patron_link"),
        Index("ix_patron_link_linked", "linked_member_id", "is_active"),
    )


# =============================================================================
# WHITE LABELING
# =============================================================================


class ConsortiumWhiteLabel(Base):
    __tablename__ = "consortium_white_labels"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(
        Integer,
        ForeignKey("consortium_members.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Branding
    logo_url = Column(String(255))
    logo_small_url = Column(String(255))  # Favicon/small logo
    banner_url = Column(String(255))

    # Colors (hex codes)
    primary_color = Column(String(7))  # e.g., "#1E40AF"
    secondary_color = Column(String(7))
    accent_color = Column(String(7))
    text_color = Column(String(7))
    background_color = Column(String(7))

    # Typography
    heading_font = Column(String(100))
    body_font = Column(String(100))

    # Custom CSS
    custom_css = Column(Text)

    # Domain configuration
    custom_domain = Column(String(255))  # e.g., "catalog.mylib.org"
    subdomain = Column(String(100))  # e.g., "mylib" for "mylib.consortium.org"

    # Content customization
    welcome_message = Column(Text)
    footer_text = Column(Text)
    contact_info = Column(JSON)  # Custom contact information

    # Social media
    facebook_url = Column(String(255))
    twitter_url = Column(String(255))
    instagram_url = Column(String(255))
    youtube_url = Column(String(255))

    # Feature toggles (hide certain consortium features)
    show_consortium_branding = Column(Boolean, default=True)
    show_member_list = Column(Boolean, default=True)
    show_consortium_events = Column(Boolean, default=True)

    # Metadata, onupdate=func.now())

    # Relationships
    member = relationship("ConsortiumMember", back_populates="white_label")


# =============================================================================
# GOVERNANCE - SETTING OVERRIDES
# =============================================================================


class SettingDefinition(TimestampMixin, Base):
    __tablename__ = "setting_definitions"

    id = Column(Integer, primary_key=True, index=True)

    # Setting identification
    key = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(50), nullable=False)  # e.g., "circulation", "fines", "holds"

    # What level can configure this
    min_scope_level = Column(String(50), nullable=False)

    # Can lower levels override?
    allow_override = Column(Boolean, default=True)

    # Data type
    data_type = Column(
        String(20), nullable=False
    )  # "integer", "decimal", "boolean", "string", "json"
    default_value = Column(Text)

    # Validation
    min_value = Column(Text)
    max_value = Column(Text)
    allowed_values = Column(JSON)  # For enum-like settings

    # Is this setting currently active
    is_active = Column(Boolean, default=True)


class SettingOverride(Base):
    __tablename__ = "setting_overrides"

    id = Column(Integer, primary_key=True, index=True)
    setting_definition_id = Column(
        Integer, ForeignKey("setting_definitions.id", ondelete="CASCADE"), nullable=False
    )

    # Scope level
    scope_level = Column(String(50), nullable=False)

    # Scope entity (one of these will be set based on scope_level)
    consortium_id = Column(Integer, ForeignKey("consortiums.id", ondelete="CASCADE"))
    library_system_id = Column(Integer, ForeignKey("library_systems.id", ondelete="CASCADE"))
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"))
    branch_id = Column(Integer)

    # The override value
    value = Column(Text, nullable=False)

    # Who set this and when (SET NULL: preserve audit trail)
    set_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    set_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Effective dates (optional)
    effective_from = Column(DateTime(timezone=True))
    effective_until = Column(DateTime(timezone=True))

    # Relationships
    setting_definition = relationship("SettingDefinition")
    consortium = relationship("Consortium")
    library_system = relationship("LibrarySystem")
    region = relationship("Region")
    # DISABLED: # DISABLED: branch relationship
    set_by = relationship("User")

    __table_args__ = (Index("ix_setting_override_key", "setting_definition_id", "scope_level"),)


# =============================================================================
# BRANCH REPORTING
# =============================================================================


class BranchStatistics(Base):
    __tablename__ = "branch_statistics"

    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, nullable=False)

    # Period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Circulation stats
    total_checkouts = Column(Integer, default=0)
    total_renewals = Column(Integer, default=0)
    total_checkins = Column(Integer, default=0)
    total_holds_placed = Column(Integer, default=0)
    total_holds_filled = Column(Integer, default=0)

    # Collection stats
    items_owned = Column(Integer, default=0)
    items_added = Column(Integer, default=0)
    items_withdrawn = Column(Integer, default=0)

    # Transit stats
    items_sent_to_other_branches = Column(Integer, default=0)
    items_received_from_other_branches = Column(Integer, default=0)

    # Patron stats
    active_patrons = Column(Integer, default=0)
    new_registrations = Column(Integer, default=0)

    # Financial
    fines_assessed = Column(Numeric(10, 2), default=0)
    fines_collected = Column(Numeric(10, 2), default=0)
    fines_waived = Column(Numeric(10, 2), default=0)

    # Visits (if tracked)
    door_count = Column(Integer)

    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    # DISABLED: # DISABLED: branch relationship

    __table_args__ = (
        UniqueConstraint("branch_id", "period_start", "period_end", name="uq_branch_stats_period"),
        Index("ix_branch_stats_period", "period_start", "period_end"),
    )
