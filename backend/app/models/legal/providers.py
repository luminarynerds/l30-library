# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...core.database import Base

from .enums import (
    ProviderType, ClinicStatus, RegistrationStatus, CourtType
)

# ============================================================================
# Legal Service Providers
# ============================================================================

class LegalServiceProvider(Base):
    __tablename__ = "legal_service_providers"

    id = Column(Integer, primary_key=True, index=True)

    # Provider identification
    name = Column(String(300), nullable=False)
    slug = Column(String(150), nullable=False, unique=True, index=True)

    # Type
    provider_type = Column(
        SQLEnum(ProviderType, name="providertype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Description
    description = Column(Text)

    # Services offered
    # Format: [{"service": "Family Law", "description": "..."}]
    services = Column(JSONB, default=[])

    # Topics covered (IDs of legal topics)
    topic_ids = Column(JSONB, default=[])

    # Eligibility
    eligibility_criteria = Column(Text)
    income_limits = Column(Text)  # e.g., "200% of federal poverty level"
    income_limit_percentage = Column(Integer)  # Percentage of FPL
    geographic_restrictions = Column(Text)
    other_requirements = Column(Text)

    # Contact information
    phone = Column(String(30))
    phone_toll_free = Column(String(30))
    email = Column(String(255))
    website = Column(String(500))

    # Address
    address_line1 = Column(String(200))
    address_line2 = Column(String(200))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))

    # Hours
    # Format: {"monday": {"open": "09:00", "close": "17:00"}, ...}
    hours = Column(JSONB, default={})
    hours_notes = Column(Text)  # Additional notes about hours

    # Accessibility
    languages_spoken = Column(ARRAY(String), default=["English"])
    accepts_walkins = Column(Boolean, default=False)
    appointment_required = Column(Boolean, default=True)
    wheelchair_accessible = Column(Boolean, default=True)
    virtual_services = Column(Boolean, default=False)

    # Special programs
    specializations = Column(ARRAY(String), default=[])
    special_populations = Column(ARRAY(String), default=[])  # e.g., veterans, DV survivors

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True))

    # Statistics
    view_count = Column(Integer, default=0)
    referral_count = Column(Integer, default=0)

    # Audit (SET NULL: preserve provider creation history)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    clinics = relationship("LegalClinic", back_populates="provider")


# ============================================================================
# Legal Clinics
# ============================================================================

# ============================================================================
# Legal Clinics
# ============================================================================

class LegalClinic(Base):
    __tablename__ = "legal_clinics"

    id = Column(Integer, primary_key=True, index=True)

    # Clinic identification
    name = Column(String(300), nullable=False)

    # Topic/focus
    topic_id = Column(
        Integer, ForeignKey("legal_topics.id", ondelete="SET NULL"),
        nullable=True
    )
    description = Column(Text)

    # Provider
    provider_id = Column(
        Integer, ForeignKey("legal_service_providers.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # Scheduling
    date = Column(Date, nullable=False, index=True)
    start_time = Column(String(10), nullable=False)  # "14:00"
    end_time = Column(String(10), nullable=False)  # "17:00"
    timezone = Column(String(50), default="America/Los_Angeles")

    # Location
    is_virtual = Column(Boolean, default=False)
    virtual_link = Column(String(500))
    virtual_platform = Column(String(100))  # Zoom, Teams, etc.
    location = Column(Text)  # e.g., "Main Library - Meeting Room A, 123 Main St"
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Capacity
    capacity = Column(Integer, default=20)
    current_registrations = Column(Integer, default=0)
    waitlist_capacity = Column(Integer, default=10)
    current_waitlist = Column(Integer, default=0)

    # Registration
    registration_required = Column(Boolean, default=True)
    registration_opens = Column(DateTime(timezone=True))
    registration_closes = Column(DateTime(timezone=True))

    # Status
    status = Column(
        SQLEnum(ClinicStatus, name="clinicstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ClinicStatus.scheduled,
        nullable=False,
        index=True
    )

    # Eligibility
    eligibility_notes = Column(Text)

    # What to bring
    # Format: [{"item": "Photo ID", "required": true}]
    what_to_bring = Column(JSONB, default=[])

    # Languages
    languages_available = Column(ARRAY(String), default=["English"])
    interpreter_available = Column(Boolean, default=False)

    # Follow-up
    follow_up_resources = Column(JSONB, default=[])  # Links to provide after

    # Accessibility
    wheelchair_accessible = Column(Boolean, default=True)
    asl_interpreter = Column(Boolean, default=False)

    # Staff/volunteers
    attorney_names = Column(ARRAY(String), default=[])
    volunteer_count = Column(Integer, default=0)

    # Notes
    internal_notes = Column(Text)
    public_notes = Column(Text)

    # Audit (SET NULL: preserve clinic creation history)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    topic = relationship("LegalTopic")
    provider = relationship("LegalServiceProvider", back_populates="clinics")
    created_by = relationship("User", foreign_keys=[created_by_id])
    registrations = relationship(
        "LegalClinicRegistration", back_populates="clinic",
        cascade="all, delete-orphan"
    )

class LegalClinicRegistration(Base):
    __tablename__ = "legal_clinic_registrations"

    id = Column(Integer, primary_key=True, index=True)

    clinic_id = Column(
        Integer, ForeignKey("legal_clinics.id", ondelete="CASCADE"),
        nullable=False
    )

    # Patron info (can be anonymous)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # Contact info (for non-patron or preferred contact)
    name = Column(String(200), nullable=False)
    email = Column(String(255))
    phone = Column(String(30))
    preferred_contact = Column(String(20), default="email")  # email, phone, text

    # Registration details
    status = Column(
        SQLEnum(RegistrationStatus, name="registrationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=RegistrationStatus.pending,
        nullable=False
    )
    waitlist_position = Column(Integer)  # NULL if not on waitlist

    # Accessibility needs
    accessibility_needs = Column(Text)
    language_preference = Column(String(50), default="English")
    interpreter_needed = Column(Boolean, default=False)

    # Brief description of legal issue
    issue_description = Column(Text)

    # Confirmation
    confirmation_sent = Column(Boolean, default=False)
    confirmation_sent_at = Column(DateTime(timezone=True))
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime(timezone=True))

    # Attendance tracking
    checked_in_at = Column(DateTime(timezone=True))

    # Follow-up
    follow_up_needed = Column(Boolean, default=False)
    follow_up_notes = Column(Text)

    # Feedback
    feedback_rating = Column(Integer)  # 1-5
    feedback_comments = Column(Text)
    feedback_submitted_at = Column(DateTime(timezone=True))

    # Audit, server_default=func.now())

    # Relationships
    clinic = relationship("LegalClinic", back_populates="registrations")
    patron = relationship("User")

    __table_args__ = (
        Index("ix_legal_clinic_reg_clinic_status", "clinic_id", "status"),
    )


# ============================================================================
# Court Information
# ============================================================================

# ============================================================================
# Court Information
# ============================================================================

class CourtLocation(Base):
    __tablename__ = "court_locations"

    id = Column(Integer, primary_key=True, index=True)

    # Court identification
    name = Column(String(300), nullable=False)
    code = Column(String(50), index=True)  # Court code if applicable

    # Type
    court_type = Column(
        SQLEnum(CourtType, name="courttype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Jurisdiction
    jurisdiction = Column(String(100), nullable=False)  # County, District, etc.
    jurisdiction_code = Column(String(20))

    # Address
    address_line1 = Column(String(200), nullable=False)
    address_line2 = Column(String(200))
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    zip_code = Column(String(20), nullable=False)

    # Contact
    phone = Column(String(30))
    phone_clerk = Column(String(30))  # Clerk's office
    phone_self_help = Column(String(30))  # Self-help center
    fax = Column(String(30))
    email = Column(String(255))
    website = Column(String(500))

    # Hours
    # Format: {"monday": {"open": "08:00", "close": "16:30"}, ...}
    general_hours = Column(JSONB, default={})
    filing_hours = Column(JSONB, default={})  # Filing window hours
    self_help_hours = Column(JSONB, default={})  # Self-help center hours
    holiday_closures = Column(JSONB, default=[])  # List of closure dates

    # Self-help center
    has_self_help_center = Column(Boolean, default=False)
    self_help_services = Column(JSONB, default=[])  # Services offered
    self_help_appointment_required = Column(Boolean, default=False)
    self_help_appointment_url = Column(String(500))

    # Filing information
    e_filing_available = Column(Boolean, default=False)
    e_filing_url = Column(String(500))
    e_filing_instructions = Column(Text)

    # What to bring
    # Format: [{"item": "Photo ID", "required": true, "notes": "..."}]
    what_to_bring = Column(JSONB, default=[])

    # Dress code and prohibited items
    dress_code = Column(Text)
    prohibited_items = Column(JSONB, default=[])

    # Parking
    parking_info = Column(Text)
    parking_cost = Column(String(100))

    # Accessibility
    wheelchair_accessible = Column(Boolean, default=True)
    accessibility_notes = Column(Text)

    # Remote hearing information
    remote_hearings_available = Column(Boolean, default=False)
    remote_hearing_platform = Column(String(100))
    remote_hearing_instructions = Column(Text)

    # Map
    latitude = Column(Float)
    longitude = Column(Float)
    directions_notes = Column(Text)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit (SET NULL: preserve court location creation history)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])


# ============================================================================
# Form Completion Sessions
# ============================================================================
