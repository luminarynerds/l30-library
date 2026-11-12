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
    EmergencyResourceType
)

# ============================================================================
# Legal Glossary
# ============================================================================

class LegalGlossaryTerm(Base):
    __tablename__ = "legal_glossary_terms"

    id = Column(Integer, primary_key=True, index=True)

    # Term
    term = Column(String(200), nullable=False, index=True)
    slug = Column(String(200), nullable=False, unique=True, index=True)

    # Definitions at different levels
    definition_simple = Column(Text)  # "Explain like I'm 5"
    definition_standard = Column(Text, nullable=False)  # Main definition
    definition_legal = Column(Text)  # Technical legal definition

    # Pronunciation
    pronunciation = Column(String(200))
    pronunciation_audio_url = Column(String(500))

    # Related terms
    related_term_slugs = Column(ARRAY(String), default=[])
    see_also = Column(ARRAY(String), default=[])  # Other terms to look up

    # Context
    usage_example = Column(Text)  # Example sentence using the term
    context_notes = Column(Text)  # When this term is typically used

    # Translations
    # Format: {"es": "Spanish term", "zh": "Chinese term"}
    translations = Column(JSONB, default={})
    # Format: {"es": "Spanish definition", ...}
    translated_definitions = Column(JSONB, default={})

    # Related topics
    topic_ids = Column(JSONB, default=[])

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Statistics
    view_count = Column(Integer, default=0)

    # Audit, server_default=func.now())


# ============================================================================
# Deadline Calculator
# ============================================================================

# ============================================================================
# Emergency Resources
# ============================================================================

class EmergencyResource(Base):
    __tablename__ = "emergency_resources"

    id = Column(Integer, primary_key=True, index=True)

    # Resource identification
    name = Column(String(300), nullable=False)

    # Type
    resource_type = Column(
        SQLEnum(EmergencyResourceType, name="emergencyresourcetype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Related situation/topic
    situation = Column(String(100))  # domestic_violence, immigration, etc.
    topic_id = Column(
        Integer, ForeignKey("legal_topics.id", ondelete="SET NULL"),
        nullable=True
    )

    # Contact
    phone = Column(String(30))
    phone_toll_free = Column(String(30))
    text_number = Column(String(30))
    website = Column(String(500))

    # Description
    description = Column(Text)
    when_to_call = Column(Text)

    # Hours
    is_24_7 = Column(Boolean, default=False)
    hours_description = Column(Text)

    # Languages
    languages_available = Column(ARRAY(String), default=["English"])

    # Display
    display_order = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit, server_default=func.now())

    # Relationships
    topic = relationship("LegalTopic")


# ============================================================================
# Fee Waiver Calculator
# ============================================================================

# ============================================================================
# Expungement/Record Clearing
# ============================================================================

class ExpungementEligibility(Base):
    __tablename__ = "expungement_eligibility"

    id = Column(Integer, primary_key=True)

    # Jurisdiction
    jurisdiction = Column(String(100), nullable=False, index=True)

    # Offense classification
    offense_category = Column(String(100), nullable=False)  # felony, misdemeanor, infraction
    offense_type = Column(String(200))  # More specific type

    # Eligibility
    is_eligible = Column(Boolean, nullable=False)
    eligibility_notes = Column(Text)

    # Waiting period
    waiting_period_years = Column(Float)  # Years after completion
    waiting_period_from = Column(String(100))  # "conviction", "completion of sentence"

    # Requirements
    requirements = Column(JSONB, default=[])  # List of requirements

    # Exceptions/exclusions
    exclusions = Column(JSONB, default=[])  # Cases where not eligible

    # Related forms
    form_ids = Column(JSONB, default=[])

    # Process description
    process_description = Column(Text)
    estimated_timeline = Column(String(200))
    estimated_cost = Column(Float)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit, server_default=func.now())


# ============================================================================
# Compliance Requirements
# ============================================================================

class ComplianceRequirement(Base):
    __tablename__ = "compliance_requirements"

    id = Column(Integer, primary_key=True, index=True)

    # Requirement identification
    title = Column(String(300), nullable=False)
    slug = Column(String(150), unique=True, index=True)
    description = Column(Text)

    # Deadline information
    deadline = Column(DateTime(timezone=True))
    deadline_description = Column(Text)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit (SET NULL: preserve compliance requirement creation history)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])


# ============================================================================
# Content Feedback
# ============================================================================
