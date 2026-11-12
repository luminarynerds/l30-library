# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# =============================================================================
# Enums
# =============================================================================

class PartnerType(StrEnum):
    SCHOOL = "school"
    DAYCARE = "daycare"
    SENIOR_CENTER = "senior_center"
    COMMUNITY_CENTER = "community_center"
    NONPROFIT = "nonprofit"
    CORRECTIONAL = "correctional"
    HEALTHCARE = "healthcare"
    BUSINESS = "business"
    GOVERNMENT = "government"
    SOCIAL_SERVICES = "social_services"
    MATERNAL_HEALTH = "maternal_health"
    OTHER = "other"


class OutreachPartnerStatus(StrEnum):
    PROSPECT = "prospect"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class PartnershipTier(StrEnum):
    BRONZE = "bronze"  # Basic partnership: standard visits + bulk checkouts
    SILVER = "silver"  # Enhanced: dedicated programs + monthly collections
    GOLD = "gold"  # Premium: custom programs + librarian consultation + ambassadors
    PLATINUM = "platinum"  # VIP: all services + dedicated staff liaison


class SchoolLevel(StrEnum):
    PRESCHOOL = "preschool"
    ELEMENTARY = "elementary"
    MIDDLE = "middle"
    HIGH = "high"
    COLLEGE = "college"
    VOCATIONAL = "vocational"
    OTHER = "other"


class DepositStatus(StrEnum):
    HELD = "held"
    PARTIALLY_APPLIED = "partially_applied"
    FULLY_APPLIED = "fully_applied"
    REFUNDED = "refunded"
    FORFEITED = "forfeited"


class DepositType(StrEnum):
    CLASSROOM_CHECKOUT = "classroom_checkout"
    BULK_CHECKOUT = "bulk_checkout"
    INSTITUTIONAL_CARD = "institutional_card"
    EQUIPMENT = "equipment"
    SPECIAL_COLLECTION = "special_collection"


class VisitStatus(StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class VisitType(StrEnum):
    STORYTIME = "storytime"
    LIBRARY_TOUR = "library_tour"
    BOOK_DELIVERY = "book_delivery"
    CARD_SIGNUP = "card_signup"
    CLASSROOM_VISIT = "classroom_visit"
    PRESENTATION = "presentation"
    WORKSHOP = "workshop"
    COLLECTION_DELIVERY = "collection_delivery"
    COLLECTION_PICKUP = "collection_pickup"
    ASSESSMENT = "assessment"
    HOME_VISIT = "home_visit"
    OTHER = "other"


class InstitutionalCardStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class BulkCheckoutStatus(StrEnum):
    ACTIVE = "active"
    RETURNED = "returned"
    PARTIALLY_RETURNED = "partially_returned"
    OVERDUE = "overdue"
    LOST = "lost"


# =============================================================================
# Outreach Partner Models
# =============================================================================

class OutreachPartner(Base):
    __tablename__ = "outreach_partners"

    id = Column(Integer, primary_key=True, index=True)

    # Basic information
    name = Column(String(300), nullable=False)
    partner_type = Column(String(50), nullable=False, default=PartnerType.SCHOOL.value)
    status = Column(String(50), nullable=False, default=OutreachPartnerStatus.ACTIVE.value)
    partnership_tier = Column(String(50), nullable=False, default=PartnershipTier.BRONZE.value)  # Partnership tier level

    # Address
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))

    # Contact information
    primary_contact_name = Column(String(200))
    primary_contact_title = Column(String(100))
    primary_contact_email = Column(String(255))
    primary_contact_phone = Column(String(30))
    secondary_contact_name = Column(String(200))
    secondary_contact_email = Column(String(255))
    secondary_contact_phone = Column(String(30))

    # School-specific fields
    school_level = Column(String(50))  # SchoolLevel enum value
    school_district = Column(String(200))
    student_count = Column(Integer)
    teacher_count = Column(Integer)

    # Partnership details
    partnership_start_date = Column(Date)
    partnership_end_date = Column(Date)
    agreement_document_url = Column(String(500))
    service_area = Column(String(200))  # Geographic area served

    # Service configuration
    allows_bulk_checkout = Column(Boolean, default=True)
    allows_institutional_card = Column(Boolean, default=True)
    requires_deposit = Column(Boolean, default=False)
    default_deposit_amount = Column(Float, default=0.0)
    checkout_limit = Column(Integer, default=100)  # Max items for bulk checkout
    loan_period_days = Column(Integer, default=28)  # Extended loan period

    # Notes and metadata
    notes = Column(Text)
    tags = Column(JSONB, default=list)  # Flexible tagging
    custom_fields = Column(JSONB, default=dict)  # Organization-specific data

    # Audit fields
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    contacts = relationship(
        "OutreachPartnerContact", back_populates="partner",
        cascade="all, delete-orphan"
    )
    deposits = relationship(
        "OutreachDeposit", back_populates="partner",
        cascade="all, delete-orphan"
    )
    visits = relationship(
        "OutreachVisit", back_populates="partner",
        cascade="all, delete-orphan"
    )
    institutional_cards = relationship(
        "InstitutionalCard", back_populates="partner",
        cascade="all, delete-orphan"
    )
    bulk_checkouts = relationship(
        "BulkCheckout", back_populates="partner",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_outreach_partners_type_status", "partner_type", "status"),
        Index("ix_outreach_partners_name", "name"),
    )

    def __repr__(self):
        return f"<OutreachPartner {self.name}>"


class OutreachPartnerContact(Base):
    __tablename__ = "outreach_partner_contacts"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )

    # Contact details
    name = Column(String(200), nullable=False)
    title = Column(String(100))
    email = Column(String(255))
    phone = Column(String(30))

    # Role and preferences
    role = Column(String(100))  # e.g., "Teacher", "Librarian", "Principal"
    is_primary = Column(Boolean, default=False)
    receives_notifications = Column(Boolean, default=True)
    preferred_contact_method = Column(String(50))  # email, phone, text

    notes = Column(Text)

    # Relationships
    partner = relationship("OutreachPartner", back_populates="contacts")

    def __repr__(self):
        return f"<OutreachPartnerContact {self.name}>"


# =============================================================================
# Deposit Management Models
# =============================================================================

class OutreachDeposit(Base):
    __tablename__ = "outreach_deposits"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )

    # Deposit details
    deposit_type = Column(String(50), nullable=False, default=DepositType.CLASSROOM_CHECKOUT.value)
    status = Column(String(50), nullable=False, default=DepositStatus.HELD.value)
    amount = Column(Float, nullable=False)
    amount_applied = Column(Float, default=0.0)  # Amount applied to fines/fees
    amount_refunded = Column(Float, default=0.0)

    # Payment information
    payment_method = Column(String(50))  # cash, check, card, invoice
    payment_reference = Column(String(100))  # Check number, transaction ID
    receipt_number = Column(String(100))

    # Associated records
    institutional_card_id = Column(
        Integer, ForeignKey("institutional_cards.id", ondelete="SET NULL")
    )
    bulk_checkout_id = Column(
        Integer, ForeignKey("bulk_checkouts.id", ondelete="SET NULL")
    )

    # Dates
    collected_date = Column(Date, nullable=False)
    refund_date = Column(Date)
    expiry_date = Column(Date)  # When deposit can be forfeited

    # Notes
    notes = Column(Text)
    refund_reason = Column(String(500))

    # Audit
    collected_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    refunded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    partner = relationship("OutreachPartner", back_populates="deposits")
    collected_by = relationship("User", foreign_keys=[collected_by_id])
    refunded_by = relationship("User", foreign_keys=[refunded_by_id])
    institutional_card = relationship("InstitutionalCard", foreign_keys=[institutional_card_id], back_populates="deposits")
    bulk_checkout = relationship("BulkCheckout", back_populates="deposit")
    applications = relationship(
        "DepositApplication", back_populates="deposit",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_outreach_deposits_partner_status", "partner_id", "status"),
    )

    def __repr__(self):
        return f"<OutreachDeposit ${self.amount} - {self.status}>"


class DepositApplication(Base):
    __tablename__ = "deposit_applications"

    id = Column(Integer, primary_key=True, index=True)
    deposit_id = Column(
        Integer, ForeignKey("outreach_deposits.id", ondelete="CASCADE"),
        nullable=False
    )

    # Application details
    amount = Column(Float, nullable=False)
    reason = Column(String(500), nullable=False)

    # Reference to what it was applied to
    fine_id = Column(Integer, ForeignKey("fines.id", ondelete="SET NULL"))
    bulk_checkout_id = Column(Integer, ForeignKey("bulk_checkouts.id", ondelete="SET NULL"))

    # Audit
    applied_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    applied_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text)

    # Relationships
    deposit = relationship("OutreachDeposit", back_populates="applications")
    applied_by = relationship("User", foreign_keys=[applied_by_id])

    def __repr__(self):
        return f"<DepositApplication ${self.amount}>"


# =============================================================================
# Outreach Visit Scheduling Models
# =============================================================================

class OutreachVisit(Base):
    __tablename__ = "outreach_visits"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )

    # Visit details
    visit_type = Column(String(50), nullable=False, default=VisitType.CLASSROOM_VISIT.value)
    status = Column(String(50), nullable=False, default=VisitStatus.SCHEDULED.value)
    title = Column(String(300), nullable=False)
    description = Column(Text)

    # Scheduling
    scheduled_date = Column(Date, nullable=False)
    scheduled_start_time = Column(String(10))  # HH:MM format
    scheduled_end_time = Column(String(10))
    actual_start_time = Column(DateTime(timezone=True))
    actual_end_time = Column(DateTime(timezone=True))

    # Location
    location_name = Column(String(200))
    location_room = Column(String(100))
    location_address = Column(String(500))

    # Participants
    expected_attendees = Column(Integer)
    actual_attendees = Column(Integer)
    age_group = Column(String(50))  # children, teen, adult, all_ages
    grade_levels = Column(JSONB, default=list)  # ["K", "1", "2"] for schools

    # Staff assignment
    lead_staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    additional_staff_ids = Column(JSONB, default=list)  # List of user IDs

    # Materials and preparation
    materials_needed = Column(JSONB, default=list)  # List of materials
    items_to_deliver = Column(Integer, default=0)  # Books being delivered
    items_delivered = Column(Integer, default=0)
    items_to_pickup = Column(Integer, default=0)  # Books being returned
    items_picked_up = Column(Integer, default=0)

    # Outcomes and reporting
    outcome_notes = Column(Text)
    new_cards_issued = Column(Integer, default=0)
    books_checked_out = Column(Integer, default=0)
    follow_up_needed = Column(Boolean, default=False)
    follow_up_notes = Column(Text)
    next_visit_date = Column(Date)

    # Feedback
    partner_feedback = Column(Text)
    partner_rating = Column(Integer)  # 1-5 rating
    staff_notes = Column(Text)

    # Cancellation
    cancellation_reason = Column(String(500))
    cancelled_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    cancelled_at = Column(DateTime(timezone=True))

    # Recurrence (for regular visits)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(50))  # weekly, biweekly, monthly
    parent_visit_id = Column(Integer, ForeignKey("outreach_visits.id", ondelete="SET NULL"))

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    partner = relationship("OutreachPartner", back_populates="visits")
    lead_staff = relationship("User", foreign_keys=[lead_staff_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    parent_visit = relationship("OutreachVisit", remote_side=[id])

    __table_args__ = (
        Index("ix_outreach_visits_partner_date", "partner_id", "scheduled_date"),
        Index("ix_outreach_visits_status_date", "status", "scheduled_date"),
        Index("ix_outreach_visits_staff_date", "lead_staff_id", "scheduled_date"),
    )

    def __repr__(self):
        return f"<OutreachVisit {self.title} on {self.scheduled_date}>"


# =============================================================================
# Institutional Card Models
# =============================================================================

class InstitutionalCard(Base):
    __tablename__ = "institutional_cards"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )

    # Card details
    card_number = Column(String(50), unique=True, nullable=False)
    status = Column(String(50), nullable=False, default=InstitutionalCardStatus.ACTIVE.value)
    card_name = Column(String(200), nullable=False)  # e.g., "Lincoln Elementary School"

    # Authorization
    authorized_users = Column(JSONB, default=list)  # List of authorized user names/IDs
    requires_pin = Column(Boolean, default=False)
    pin_hash = Column(String(255))  # Hashed PIN if required

    # Checkout policies
    checkout_limit = Column(Integer, default=100)
    hold_limit = Column(Integer, default=25)
    loan_period_days = Column(Integer, default=28)
    renewal_limit = Column(Integer, default=2)

    # Fine policies
    exempt_from_fines = Column(Boolean, default=False)
    fine_cap = Column(Float)  # Maximum fines before blocking

    # Deposit requirement
    deposit_required = Column(Boolean, default=False)
    deposit_amount = Column(Float, default=0.0)
    current_deposit_id = Column(Integer, ForeignKey("outreach_deposits.id", ondelete="SET NULL", use_alter=True))

    # Validity period
    issued_date = Column(Date, nullable=False)
    expiry_date = Column(Date)
    last_renewal_date = Column(Date)

    # Usage tracking
    total_checkouts = Column(Integer, default=0)
    current_checkouts = Column(Integer, default=0)
    current_holds = Column(Integer, default=0)
    current_fines = Column(Float, default=0.0)

    # Notes
    notes = Column(Text)

    # Audit
    issued_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    partner = relationship("OutreachPartner", back_populates="institutional_cards")
    issued_by = relationship("User", foreign_keys=[issued_by_id])
    deposits = relationship(
        "OutreachDeposit", back_populates="institutional_card",
        foreign_keys="OutreachDeposit.institutional_card_id"
    )
    checkouts = relationship(
        "InstitutionalCheckout", back_populates="card",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_institutional_cards_partner", "partner_id"),
        Index("ix_institutional_cards_status", "status"),
    )

    def __repr__(self):
        return f"<InstitutionalCard {self.card_number}>"


class InstitutionalCheckout(Base):
    __tablename__ = "institutional_checkouts"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(
        Integer, ForeignKey("institutional_cards.id", ondelete="CASCADE"),
        nullable=False
    )

    # Link to main checkout record
    checkout_id = Column(
        Integer, ForeignKey("checkouts.id", ondelete="SET NULL")
    )

    # Item info (denormalized for quick access)
    item_copy_id = Column(Integer, ForeignKey("item_copies.id", ondelete="SET NULL"))
    barcode = Column(String(50))
    title = Column(String(500))

    # Who checked it out (authorized user)
    checked_out_by_name = Column(String(200))
    checked_out_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Dates
    checked_out_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    returned_at = Column(DateTime(timezone=True))

    # Status
    status = Column(String(50), default="active")  # active, returned, lost, damaged, server_default=func.now())

    # Relationships
    card = relationship("InstitutionalCard", back_populates="checkouts")
    checked_out_by = relationship("User", foreign_keys=[checked_out_by_id])

    __table_args__ = (
        Index("ix_institutional_checkouts_card_status", "card_id", "status"),
    )

    def __repr__(self):
        return f"<InstitutionalCheckout {self.barcode}>"


# =============================================================================
# Bulk/Classroom Checkout Models
# =============================================================================

class BulkCheckout(Base):
    __tablename__ = "bulk_checkouts"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"),
        nullable=False
    )

    # Checkout details
    checkout_name = Column(String(300), nullable=False)  # e.g., "Mrs. Smith's 3rd Grade Class"
    status = Column(String(50), nullable=False, default=BulkCheckoutStatus.ACTIVE.value)

    # Requesting person
    requestor_name = Column(String(200), nullable=False)
    requestor_email = Column(String(255))
    requestor_phone = Column(String(30))
    classroom_name = Column(String(200))
    grade_level = Column(String(50))

    # Dates
    checkout_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    returned_date = Column(Date)

    # Item counts
    total_items = Column(Integer, default=0)
    items_returned = Column(Integer, default=0)
    items_lost = Column(Integer, default=0)
    items_damaged = Column(Integer, default=0)

    # Deposit
    deposit_required = Column(Boolean, default=False)
    deposit_amount = Column(Float, default=0.0)
    deposit_collected = Column(Boolean, default=False)

    # Collection criteria (what kind of books were requested)
    topic_requests = Column(JSONB, default=list)  # Topics/subjects requested
    reading_level_min = Column(String(20))
    reading_level_max = Column(String(20))
    format_preferences = Column(JSONB, default=list)  # paperback, hardcover, etc.

    # Delivery/Pickup
    delivery_method = Column(String(50))  # pickup, delivery, visit
    delivery_address = Column(String(500))
    pickup_location = Column(String(200))
    outreach_visit_id = Column(Integer, ForeignKey("outreach_visits.id", ondelete="SET NULL"))

    # Notes
    notes = Column(Text)
    return_notes = Column(Text)

    # Audit
    processed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    partner = relationship("OutreachPartner", back_populates="bulk_checkouts")
    processed_by = relationship("User", foreign_keys=[processed_by_id])
    outreach_visit = relationship("OutreachVisit")
    deposit = relationship(
        "OutreachDeposit", back_populates="bulk_checkout",
        uselist=False, foreign_keys="OutreachDeposit.bulk_checkout_id"
    )
    items = relationship(
        "BulkCheckoutItem", back_populates="bulk_checkout",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_bulk_checkouts_partner_status", "partner_id", "status"),
        Index("ix_bulk_checkouts_due_date", "due_date"),
    )

    def __repr__(self):
        return f"<BulkCheckout {self.checkout_name}>"


class BulkCheckoutItem(Base):
    __tablename__ = "bulk_checkout_items"

    id = Column(Integer, primary_key=True, index=True)
    bulk_checkout_id = Column(
        Integer, ForeignKey("bulk_checkouts.id", ondelete="CASCADE"),
        nullable=False
    )

    # Item reference
    item_copy_id = Column(Integer, ForeignKey("item_copies.id", ondelete="SET NULL"))
    checkout_id = Column(Integer, ForeignKey("checkouts.id", ondelete="SET NULL"))

    # Item info (denormalized)
    barcode = Column(String(50), nullable=False)
    title = Column(String(500))
    call_number = Column(String(100))

    # Status
    status = Column(String(50), default="checked_out")  # checked_out, returned, lost, damaged
    returned_at = Column(DateTime(timezone=True))

    # Condition tracking
    condition_out = Column(String(50))  # Condition when checked out
    condition_in = Column(String(50))  # Condition when returned
    damage_notes = Column(Text)

    # Fine/replacement
    replacement_cost = Column(Float)
    fine_amount = Column(Float, default=0.0)

    # Relationships
    bulk_checkout = relationship("BulkCheckout", back_populates="items")

    __table_args__ = (
        Index("ix_bulk_checkout_items_bulk_status", "bulk_checkout_id", "status"),
        Index("ix_bulk_checkout_items_barcode", "barcode"),
    )

    def __repr__(self):
        return f"<BulkCheckoutItem {self.barcode}>"


# =============================================================================
# Outreach Statistics Models
# =============================================================================

class OutreachStatistics(Base):
    __tablename__ = "outreach_statistics"

    id = Column(Integer, primary_key=True, index=True)

    # Period (monthly aggregation)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    branch_id = Column(Integer)

    # Partner statistics
    total_partners = Column(Integer, default=0)
    active_partners = Column(Integer, default=0)
    new_partners = Column(Integer, default=0)
    partners_by_type = Column(JSONB, default=dict)  # {"school": 10, "daycare": 5, ...}

    # Visit statistics
    total_visits = Column(Integer, default=0)
    visits_completed = Column(Integer, default=0)
    visits_cancelled = Column(Integer, default=0)
    total_attendees = Column(Integer, default=0)
    visits_by_type = Column(JSONB, default=dict)  # {"storytime": 5, "book_delivery": 10, ...}

    # Checkout statistics
    bulk_checkouts_created = Column(Integer, default=0)
    bulk_checkouts_returned = Column(Integer, default=0)
    bulk_items_checked_out = Column(Integer, default=0)
    bulk_items_returned = Column(Integer, default=0)
    bulk_items_lost = Column(Integer, default=0)

    # Institutional card statistics
    institutional_cards_active = Column(Integer, default=0)
    institutional_cards_issued = Column(Integer, default=0)
    institutional_checkouts = Column(Integer, default=0)

    # Deposit statistics
    deposits_collected = Column(Float, default=0.0)
    deposits_refunded = Column(Float, default=0.0)
    deposits_applied_to_fines = Column(Float, default=0.0)

    # Impact metrics
    new_cards_from_outreach = Column(Integer, default=0)
    reading_program_signups = Column(Integer, default=0)

    # Audit
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    generated_by = relationship("User", foreign_keys=[generated_by_id])

    __table_args__ = (
        UniqueConstraint("period_start", "period_end", "branch_id", name="uq_outreach_stats_period_branch"),
        Index("ix_outreach_statistics_period", "period_start", "period_end"),
    )

    def __repr__(self):
        return f"<OutreachStatistics {self.period_start} to {self.period_end}>"


# =============================================================================
# Notification Template Models
# =============================================================================

class OutreachNotificationType(StrEnum):
    VISIT_SCHEDULED = "visit_scheduled"
    VISIT_REMINDER = "visit_reminder"
    VISIT_CONFIRMED = "visit_confirmed"
    VISIT_CANCELLED = "visit_cancelled"
    BULK_CHECKOUT_CREATED = "bulk_checkout_created"
    BULK_CHECKOUT_DUE_SOON = "bulk_checkout_due_soon"
    BULK_CHECKOUT_OVERDUE = "bulk_checkout_overdue"
    BULK_CHECKOUT_RETURNED = "bulk_checkout_returned"
    DEPOSIT_COLLECTED = "deposit_collected"
    DEPOSIT_EXPIRING = "deposit_expiring"
    DEPOSIT_REFUNDED = "deposit_refunded"
    DEPOSIT_APPLIED = "deposit_applied"
    CARD_ISSUED = "card_issued"
    CARD_EXPIRING = "card_expiring"
    CARD_RENEWED = "card_renewed"
    CARD_SUSPENDED = "card_suspended"
    PARTNER_WELCOME = "partner_welcome"
    PARTNER_ANNIVERSARY = "partner_anniversary"
    PARTNER_INACTIVE_WARNING = "partner_inactive_warning"


class OutreachNotificationChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    PRINT = "print"


class OutreachNotificationTemplate(Base):
    __tablename__ = "outreach_notification_templates"

    id = Column(Integer, primary_key=True, index=True)

    # Template identification
    name = Column(String(200), nullable=False)
    notification_type = Column(String(50), nullable=False)  # OutreachNotificationType
    channel = Column(String(20), nullable=False)  # OutreachNotificationChannel

    # Template content
    subject = Column(String(500))  # For email
    body = Column(Text, nullable=False)
    html_body = Column(Text)  # Optional HTML version for email

    # Variable placeholders available (for documentation)
    available_variables = Column(JSONB, default=list)
    # e.g., ["partner_name", "visit_date", "staff_name", "due_date", "item_count"]

    # Scheduling
    days_before_event = Column(Integer)  # For reminders (e.g., send 3 days before)
    send_time = Column(String(10))  # Preferred send time, e.g., "09:00"

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Default template for this type

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])

    __table_args__ = (
        Index("ix_notification_templates_type_channel", "notification_type", "channel"),
        UniqueConstraint(
            "notification_type", "channel", "is_default",
            name="uq_default_template_per_type_channel"
        ),
    )

    def __repr__(self):
        return f"<OutreachNotificationTemplate {self.name}>"


class OutreachNotificationLog(Base):
    __tablename__ = "outreach_notification_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Template used
    template_id = Column(
        Integer, ForeignKey("outreach_notification_templates.id", ondelete="SET NULL")
    )
    notification_type = Column(String(50), nullable=False)
    channel = Column(String(20), nullable=False)

    # Recipient
    recipient_type = Column(String(50))  # partner_contact, institutional_card_holder, etc.
    recipient_id = Column(Integer)  # ID of the recipient entity
    recipient_email = Column(String(255))
    recipient_phone = Column(String(30))
    recipient_name = Column(String(200))

    # Related entities
    partner_id = Column(Integer, ForeignKey("outreach_partners.id", ondelete="SET NULL"))
    visit_id = Column(Integer, ForeignKey("outreach_visits.id", ondelete="SET NULL"))
    bulk_checkout_id = Column(Integer, ForeignKey("bulk_checkouts.id", ondelete="SET NULL"))
    deposit_id = Column(Integer, ForeignKey("outreach_deposits.id", ondelete="SET NULL"))
    institutional_card_id = Column(
        Integer, ForeignKey("institutional_cards.id", ondelete="SET NULL")
    )

    # Content sent (rendered)
    subject = Column(String(500))
    body = Column(Text)

    # Delivery status
    status = Column(String(50), default="pending")  # pending, sent, delivered, failed, bounced
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    failure_reason = Column(Text)

    # External tracking
    external_message_id = Column(String(255))  # ID from email/SMS provider

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Audit
    triggered_by = Column(String(50))  # scheduler, manual, api
    triggered_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    template = relationship("OutreachNotificationTemplate")
    partner = relationship("OutreachPartner")
    visit = relationship("OutreachVisit")
    bulk_checkout = relationship("BulkCheckout")
    deposit = relationship("OutreachDeposit")
    institutional_card = relationship("InstitutionalCard")
    triggered_by_user = relationship("User", foreign_keys=[triggered_by_user_id])

    __table_args__ = (
        Index("ix_notification_logs_partner", "partner_id"),
        Index("ix_notification_logs_type_status", "notification_type", "status"),
        Index("ix_notification_logs_created", "created_at"),
    )
