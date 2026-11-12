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
    FormDifficulty, FormStatus, FormCompletionStatus, WizardSessionStatus
)

# ============================================================================
# Legal Forms
# ============================================================================

class LegalForm(Base):
    __tablename__ = "legal_forms"

    id = Column(Integer, primary_key=True, index=True)

    # Form identification
    title = Column(String(500), nullable=False)
    form_number = Column(String(100))  # Official form number

    # Classification
    topic_id = Column(
        Integer, ForeignKey("legal_topics.id", ondelete="SET NULL"),
        nullable=True
    )
    category = Column(String(100))  # High-level category
    subcategory = Column(String(100))  # More specific category

    # Jurisdiction
    jurisdiction = Column(String(100), nullable=False)  # State, Federal, County
    jurisdiction_code = Column(String(20))  # e.g., "CA", "US", "LA-COUNTY"
    court_type = Column(String(50))  # Which type of court uses this form
    court_name = Column(String(200))  # Specific court name if applicable

    # Plain language description
    description = Column(Text)  # What this form is for
    when_to_use = Column(Text)  # Explains when to use this form
    who_should_use = Column(Text)  # Who typically uses this form
    plain_language_title = Column(String(300))  # Non-legal title

    # Form URLs
    url = Column(String(500))  # URL to download form
    instructions_url = Column(String(500))  # URL to instructions
    example_url = Column(String(500))  # URL to example completed form

    # Form details
    page_count = Column(Integer)
    filing_fee = Column(Float)  # Filing fee in dollars
    fee_waiver_form_id = Column(
        Integer, ForeignKey("legal_forms.id", ondelete="SET NULL"),
        nullable=True
    )

    # Difficulty and requirements
    difficulty_level = Column(
        SQLEnum(FormDifficulty, name="formdifficulty", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=FormDifficulty.moderate
    )
    estimated_completion_time = Column(Integer)  # Minutes
    notarization_required = Column(Boolean, default=False)
    signature_requirements = Column(Text)  # Explains who needs to sign

    # Languages
    languages_available = Column(ARRAY(String), default=["English"])

    # Accessibility
    screen_reader_friendly = Column(Boolean, default=False)
    large_print_available = Column(Boolean, default=False)
    fillable_pdf = Column(Boolean, default=False)

    # Version control
    version = Column(String(50))
    effective_date = Column(Date)
    last_updated = Column(Date)
    change_notes = Column(Text)  # What changed in this version

    # Status
    status = Column(
        SQLEnum(FormStatus, name="formstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=FormStatus.active,
        nullable=False
    )
    superseded_by_id = Column(
        Integer, ForeignKey("legal_forms.id", ondelete="SET NULL"),
        nullable=True
    )

    # Related forms - stored as JSON array of form IDs
    related_form_ids = Column(JSONB, default=[])

    # Common mistakes and tips
    common_mistakes = Column(JSONB, default=[])  # [{mistake, how_to_avoid}]
    tips = Column(JSONB, default=[])  # [{tip}]

    # Field-by-field help (JSON for interactive help)
    # Format: {"field_name": {"help_text": "...", "example": "..."}}
    field_help = Column(JSONB, default={})

    # Statistics
    download_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    # Audit (SET NULL: preserve audit trail)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    last_reviewed_at = Column(DateTime(timezone=True))
    last_reviewed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    topic = relationship("LegalTopic", back_populates="forms")
    fee_waiver_form = relationship(
        "LegalForm", foreign_keys=[fee_waiver_form_id], remote_side="LegalForm.id"
    )
    superseded_by = relationship(
        "LegalForm", foreign_keys=[superseded_by_id], remote_side="LegalForm.id"
    )
    created_by = relationship("User", foreign_keys=[created_by_id])
    last_reviewed_by = relationship("User", foreign_keys=[last_reviewed_by_id])
    packet_forms = relationship("LegalFormPacketItem", back_populates="form")

    __table_args__ = (
        Index("ix_legal_forms_jurisdiction_status", "jurisdiction", "status"),
        Index("ix_legal_forms_topic_status", "topic_id", "status"),
        Index("ix_legal_forms_form_number", "form_number"),
    )

class LegalFormPacket(Base):
    __tablename__ = "legal_form_packets"

    id = Column(Integer, primary_key=True)

    # Packet identification
    name = Column(String(300), nullable=False)
    slug = Column(String(150), nullable=False, unique=True, index=True)

    # Classification
    topic_id = Column(
        Integer, ForeignKey("legal_topics.id", ondelete="SET NULL"),
        nullable=True
    )

    # Description
    description = Column(Text)
    use_case = Column(Text)  # When to use this packet
    who_should_use = Column(Text)

    # Checklist of all required items
    # Format: [{"item": "Copy of ID", "required": true, "notes": "..."}]
    checklist = Column(JSONB, default=[])

    # Filing information
    filing_sequence = Column(JSONB, default=[])  # Order to file forms
    total_filing_fee = Column(Float)
    estimated_total_time = Column(Integer)  # Minutes to complete all forms

    # Timeline expectations
    timeline_description = Column(Text)  # "This typically takes 2-6 months"

    # Cost breakdown
    # Format: [{"item": "Filing fee", "amount": 435}, ...]
    cost_breakdown = Column(JSONB, default=[])

    # Instructions and guides
    instructions = Column(Text)
    related_guide_ids = Column(JSONB, default=[])  # IDs of related guides

    # Jurisdiction
    jurisdiction = Column(String(100))
    court_addresses = Column(JSONB, default=[])  # Court locations for filing

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Statistics
    download_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    # Audit (SET NULL: preserve packet creation history)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    topic = relationship("LegalTopic")
    created_by = relationship("User", foreign_keys=[created_by_id])
    forms = relationship(
        "LegalFormPacketItem", back_populates="packet",
        order_by="LegalFormPacketItem.order",
        cascade="all, delete-orphan"
    )

class LegalFormPacketItem(Base):
    __tablename__ = "legal_form_packet_items"

    id = Column(Integer, primary_key=True, index=True)

    packet_id = Column(
        Integer, ForeignKey("legal_form_packets.id", ondelete="CASCADE"),
        nullable=False
    )
    form_id = Column(
        Integer, ForeignKey("legal_forms.id", ondelete="CASCADE"),
        nullable=False
    )

    # Order within packet
    order = Column(Integer, default=0)

    # Item-specific instructions
    instructions = Column(Text)  # Specific to this form in this packet
    is_required = Column(Boolean, default=True)
    conditional_notes = Column(Text)  # When this form is needed

    # Relationships
    packet = relationship("LegalFormPacket", back_populates="forms")
    form = relationship("LegalForm", back_populates="packet_forms")

    __table_args__ = (
        UniqueConstraint("packet_id", "form_id", name="uq_packet_form"),
        Index("ix_legal_form_packet_items_packet_order", "packet_id", "order"),
    )


# ============================================================================
# Legal Guides
# ============================================================================

# ============================================================================
# Form Completion Sessions
# ============================================================================

class FormCompletionSession(Base):
    __tablename__ = "form_completion_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Session identification (UUID for anonymous tracking)
    session_token = Column(String(64), nullable=False, unique=True, index=True)

    # Optional patron link (NULL for anonymous)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # Form being completed
    form_id = Column(
        Integer, ForeignKey("legal_forms.id", ondelete="SET NULL"),
        nullable=True
    )
    packet_id = Column(
        Integer, ForeignKey("legal_form_packets.id", ondelete="SET NULL"),
        nullable=True
    )

    # Mode
    anonymous_mode = Column(Boolean, default=True, nullable=False)

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))

    # Status
    status = Column(
        SQLEnum(FormCompletionStatus, name="formcompletionstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=FormCompletionStatus.in_progress,
        nullable=False
    )

    # Progress tracking (non-personal)
    current_step = Column(Integer, default=1)
    total_steps = Column(Integer)

    # Device info (for accessibility tracking)
    device_type = Column(String(50))  # desktop, mobile, tablet

    # Help requested
    help_requested = Column(Boolean, default=False)
    help_type = Column(String(100))  # in_person, chat, phone

    # Relationships
    patron = relationship("User")
    form = relationship("LegalForm")
    packet = relationship("LegalFormPacket")

    __table_args__ = (
        Index("ix_form_completion_form_status", "form_id", "status"),
    )


# ============================================================================
# Form Finder Wizard
# ============================================================================

# ============================================================================
# Form Finder Wizard
# ============================================================================

class FormFinderWizardSession(Base):
    __tablename__ = "form_finder_wizard_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Session identification
    session_token = Column(String(64), nullable=False, unique=True, index=True)

    # Optional patron link
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Status
    status = Column(
        SQLEnum(WizardSessionStatus, name="wizardsessionstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=WizardSessionStatus.in_progress,
        nullable=False
    )

    # Progress
    current_step = Column(String(100))

    # Answers given (stored as JSON for flexibility)
    # Format: {"question_slug": "answer_value", ...}
    answers = Column(JSONB, default={})

    # Results (if completed)
    recommended_form_ids = Column(JSONB, default=[])
    recommended_packet_ids = Column(JSONB, default=[])
    recommended_guide_ids = Column(JSONB, default=[])

    # Jurisdiction determined
    jurisdiction_state = Column(String(50))
    jurisdiction_county = Column(String(100))
    court_type_determined = Column(String(50))

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))

    # "I'm not sure" tracking
    referred_to_help = Column(Boolean, default=False)
    referral_reason = Column(Text)

    # Audit - auto-delete after period for privacy
    expires_at = Column(DateTime(timezone=True))

    # Relationships
    patron = relationship("User")

class FormFinderQuestion(Base):
    __tablename__ = "form_finder_questions"

    id = Column(Integer, primary_key=True, index=True)

    # Question identification
    slug = Column(String(100), nullable=False, unique=True, index=True)

    # Question text (plain language)
    question_text = Column(Text, nullable=False)
    help_text = Column(Text)  # Additional explanation

    # Question type
    question_type = Column(String(50), nullable=False)  # single, multiple, text, county_select, etc.

    # Options for choice questions
    # Format: [{"value": "divorce", "label": "Divorce or separation", "next_question": "has_children"}]
    options = Column(JSONB, default=[])

    # Branching logic
    # Format: {"answer_value": "next_question_slug", "default": "fallback_question_slug"}
    branching = Column(JSONB, default={})

    # Validation
    required = Column(Boolean, default=True)
    validation_rules = Column(JSONB, default={})

    # Display
    display_order = Column(Integer, default=0)
    category = Column(String(100))  # Group questions by category

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit, server_default=func.now())

class FormFinderRule(Base):
    __tablename__ = "form_finder_rules"

    id = Column(Integer, primary_key=True, index=True)

    # Rule name for management
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Conditions (all must match)
    # Format: [{"question_slug": "...", "operator": "equals", "value": "..."}]
    conditions = Column(JSONB, nullable=False, default=[])

    # Results when conditions match
    form_ids = Column(JSONB, default=[])
    packet_ids = Column(JSONB, default=[])
    guide_ids = Column(JSONB, default=[])

    # Priority (higher = checked first)
    priority = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit, server_default=func.now())


# ============================================================================
# Legal Glossary
# ============================================================================

# ============================================================================
# Fee Waiver Calculator
# ============================================================================

class FeeWaiverEligibility(Base):
    __tablename__ = "fee_waiver_eligibility"

    id = Column(Integer, primary_key=True)

    # Jurisdiction
    jurisdiction = Column(String(100), nullable=False, index=True)
    court_type = Column(String(50))

    # Income thresholds
    # Format: [{"household_size": 1, "annual_income": 18075}, ...]
    income_thresholds = Column(JSONB, nullable=False, default=[])

    # Percentage of federal poverty level
    fpl_percentage = Column(Integer)  # e.g., 125, 200

    # Automatic eligibility criteria
    # Format: [{"criteria": "Receiving CalWORKs", "documentation": "..."}]
    automatic_eligibility = Column(JSONB, default=[])

    # Required documentation
    required_documentation = Column(JSONB, default=[])

    # Fee waiver form
    form_id = Column(
        Integer, ForeignKey("legal_forms.id", ondelete="SET NULL"),
        nullable=True
    )

    # Partial waiver info
    partial_waiver_available = Column(Boolean, default=False)
    partial_waiver_notes = Column(Text)

    # Payment plan info
    payment_plan_available = Column(Boolean, default=False)
    payment_plan_notes = Column(Text)

    # What to do if denied
    denial_appeal_process = Column(Text)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit, server_default=func.now())

    # Relationships
    form = relationship("LegalForm")


# ============================================================================
# Expungement/Record Clearing
# ============================================================================

class LegalFormLinkCheck(Base):
    __tablename__ = "legal_form_link_checks"

    id = Column(Integer, primary_key=True, index=True)

    form_id = Column(
        Integer, ForeignKey("legal_forms.id", ondelete="CASCADE"),
        nullable=False
    )

    # Which link
    link_type = Column(String(50), nullable=False)  # form_url, instructions_url, example_url
    url = Column(String(500), nullable=False)

    # Check result
    is_valid = Column(Boolean, nullable=False)
    http_status = Column(Integer)
    error_message = Column(Text)

    # Timing
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    form = relationship("LegalForm")


# ============================================================================
# Usage Statistics (Anonymized)
# ============================================================================
