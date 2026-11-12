# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint, text
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...core.database import Base

from .enums import (
    GuideReadingLevel, LegalFeedbackType, DeadlineType
)

# ============================================================================
# Legal Topics Taxonomy
# ============================================================================

class LegalTopic(Base):
    __tablename__ = "legal_topics"

    id = Column(Integer, primary_key=True, index=True)

    # Topic identification
    name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)

    # Hierarchy (SET NULL: preserve topic hierarchy even if parent topic deleted)
    parent_id = Column(
        Integer, ForeignKey("legal_topics.id", ondelete="SET NULL"),
        nullable=True
    )
    display_order = Column(Integer, default=0)

    # Display
    icon = Column(String(100))  # Icon name or emoji
    color = Column(String(7))  # Hex color code

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False)

    # SEO and search
    keywords = Column(ARRAY(String), default=[])
    meta_description = Column(String(300))

    # Related resources stored as JSON
    # Format: [{"type": "book", "id": 123, "title": "..."}]
    related_resources = Column(JSONB, default=[])

    # Statistics
    view_count = Column(Integer, default=0)

    # Per-language translations: {"es": {"name": "...", "description": "..."}}
    translations = Column(JSONB, nullable=False, server_default=text("'{}'"))

    # Audit, server_default=func.now())
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    # Self-referential relationship with lazy loading to prevent circular reference GC issues
    parent = relationship(
        "LegalTopic",
        remote_side="LegalTopic.id",
        back_populates="children",
        lazy="select"
    )
    children = relationship(
        "LegalTopic",
        back_populates="parent",
        lazy="select"
    )
    created_by = relationship("User", foreign_keys=[created_by_id])
    forms = relationship("LegalForm", back_populates="topic")
    guides = relationship("LegalGuide", back_populates="topic")

    __table_args__ = (
        Index("ix_legal_topics_parent_order", "parent_id", "display_order"),
    )


# ============================================================================
# Legal Forms
# ============================================================================

# ============================================================================
# Legal Guides
# ============================================================================

class LegalGuide(Base):
    __tablename__ = "legal_guides"

    id = Column(Integer, primary_key=True, index=True)

    # Guide identification
    title = Column(String(300), nullable=False)
    slug = Column(String(150), nullable=False, unique=True, index=True)

    # Classification
    topic_id = Column(
        Integer, ForeignKey("legal_topics.id", ondelete="SET NULL"),
        nullable=True
    )

    # Content
    summary = Column(Text)  # Brief overview
    content = Column(Text)  # Main content (markdown supported)

    # Reading level
    reading_level = Column(
        SQLEnum(GuideReadingLevel, name="guidereadinglevel", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=GuideReadingLevel.middle_school
    )

    # Step-by-step instructions
    # Format: [{"step": 1, "title": "...", "content": "...", "tips": [...]}]
    steps = Column(JSONB, default=[])

    # Related content
    related_form_ids = Column(JSONB, default=[])
    related_guide_ids = Column(JSONB, default=[])
    related_resource_urls = Column(JSONB, default=[])  # External links

    # Flowchart/visual representation
    flowchart_data = Column(JSONB)  # Data for rendering flowchart
    flowchart_image_url = Column(String(500))  # Static image fallback

    # Timeline and costs
    timeline_description = Column(Text)
    # Format: [{"item": "Filing fee", "amount": 435, "notes": "..."}]
    cost_breakdown = Column(JSONB, default=[])

    # Common scenarios
    # Format: [{"scenario": "What if...", "answer": "..."}]
    common_scenarios = Column(JSONB, default=[])

    # When you need a lawyer section
    when_need_lawyer = Column(Text)
    complexity_warning_signs = Column(JSONB, default=[])  # Signs case is complex

    # Media
    video_url = Column(String(500))
    video_transcript = Column(Text)

    # Printable checklist
    printable_checklist = Column(JSONB, default=[])  # Items for checklist

    # Languages
    languages_available = Column(ARRAY(String), default=["English"])

    # Status
    is_published = Column(Boolean, default=False, nullable=False)
    is_featured = Column(Boolean, default=False)

    # Statistics
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)

    # Audit (SET NULL: preserve audit trail)
    published_at = Column(DateTime(timezone=True))
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
    topic = relationship("LegalTopic", back_populates="guides")
    created_by = relationship("User", foreign_keys=[created_by_id])
    last_reviewed_by = relationship("User", foreign_keys=[last_reviewed_by_id])


# ============================================================================
# Legal Service Providers
# ============================================================================

# ============================================================================
# Deadline Calculator
# ============================================================================

class DeadlineRule(Base):
    __tablename__ = "deadline_rules"

    id = Column(Integer, primary_key=True, index=True)

    # Rule identification
    name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)

    # Deadline type
    deadline_type = Column(
        SQLEnum(DeadlineType, name="deadlinetype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Related topic
    topic_id = Column(
        Integer, ForeignKey("legal_topics.id", ondelete="SET NULL"),
        nullable=True
    )

    # Jurisdiction
    jurisdiction = Column(String(100))
    court_type = Column(String(50))

    # Calculation rules
    days = Column(Integer, nullable=False)  # Number of days
    use_business_days = Column(Boolean, default=False)  # Business vs calendar days
    exclude_holidays = Column(Boolean, default=True)

    # Starting point
    start_event = Column(String(200))  # e.g., "Date of service", "Filing date"

    # Extensions and exceptions
    extension_rules = Column(JSONB, default=[])  # Conditions for extensions
    exception_notes = Column(Text)

    # Citation
    legal_citation = Column(Text)  # Code section reference

    # Warning thresholds (days before deadline)
    warning_days = Column(JSONB, default=[7, 3, 1])

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit, server_default=func.now())

    # Relationships
    topic = relationship("LegalTopic")

class DeadlineCalculation(Base):
    __tablename__ = "deadline_calculations"

    id = Column(Integer, primary_key=True)

    # Session/patron (anonymous possible)
    session_token = Column(String(64), index=True)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Rule used
    rule_id = Column(
        Integer, ForeignKey("deadline_rules.id", ondelete="SET NULL"),
        nullable=True
    )

    # Calculation inputs
    start_date = Column(Date, nullable=False)

    # Calculated deadline
    deadline_date = Column(Date, nullable=False)

    # Reminders
    reminder_email = Column(String(255))
    reminder_phone = Column(String(30))
    reminders_enabled = Column(Boolean, default=False)
    reminder_sent_dates = Column(JSONB, default=[])

    # Calendar integration
    calendar_event_id = Column(String(200))  # External calendar ID

    # Notes
    user_notes = Column(Text)

    # Expiry
    expires_at = Column(DateTime(timezone=True))

    # Audit, server_default=func.now())

    # Relationships
    patron = relationship("User")
    rule = relationship("DeadlineRule")


# ============================================================================
# Know Your Rights
# ============================================================================

# ============================================================================
# Know Your Rights
# ============================================================================

class KnowYourRightsGuide(Base):
    __tablename__ = "know_your_rights_guides"

    id = Column(Integer, primary_key=True, index=True)

    # Guide identification
    title = Column(String(300), nullable=False)
    slug = Column(String(150), nullable=False, unique=True, index=True)

    # Situation/context
    situation = Column(String(200), nullable=False)  # e.g., "police_encounter", "ice_encounter"

    # Content
    summary = Column(Text)
    content = Column(Text, nullable=False)  # Main content (markdown)

    # Key points/rights
    # Format: [{"right": "You have the right to...", "explanation": "..."}]
    key_rights = Column(JSONB, default=[])

    # Do's and Don'ts
    # Format: [{"do": "Stay calm", "why": "..."}]
    dos = Column(JSONB, default=[])
    # Format: [{"dont": "Don't resist", "why": "..."}]
    donts = Column(JSONB, default=[])

    # Scripts - what to say
    # Format: [{"situation": "If asked...", "script": "You can say..."}]
    scripts = Column(JSONB, default=[])

    # When to stay silent
    when_silent = Column(Text)

    # How to document
    documentation_tips = Column(JSONB, default=[])

    # Emergency contacts specific to this situation
    emergency_contacts = Column(JSONB, default=[])

    # Printable wallet card
    wallet_card_content = Column(Text)  # Condensed version
    wallet_card_pdf_url = Column(String(500))

    # Video
    video_url = Column(String(500))
    video_transcript = Column(Text)

    # Languages
    languages_available = Column(ARRAY(String), default=["English"])

    # Sensitive content warning
    is_sensitive = Column(Boolean, default=False)
    sensitivity_warning = Column(Text)

    # Status
    is_published = Column(Boolean, default=False)

    # Statistics
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)

    # Audit, server_default=func.now())
    last_reviewed_at = Column(DateTime(timezone=True))


# ============================================================================
# Emergency Resources
# ============================================================================

# ============================================================================
# Content Feedback
# ============================================================================

class LegalContentFeedback(Base):
    __tablename__ = "legal_content_feedback"

    id = Column(Integer, primary_key=True, index=True)

    # What content
    content_type = Column(String(50), nullable=False)  # form, guide, topic, etc.
    content_id = Column(Integer, nullable=False)
    page_url = Column(String(500))

    # Feedback type
    feedback_type = Column(
        SQLEnum(LegalFeedbackType, name="feedbacktype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Was it helpful?
    was_helpful = Column(Boolean)

    # Detailed feedback
    comments = Column(Text)
    what_looking_for = Column(Text)  # If not found

    # Suggested content/changes
    suggestion = Column(Text)

    # Contact for follow-up (optional)
    email = Column(String(255))

    # Session info (anonymous)
    session_token = Column(String(64))

    # Staff response (SET NULL: preserve feedback review history)
    staff_reviewed = Column(Boolean, default=False)
    staff_notes = Column(Text)
    staff_reviewed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    staff_reviewed_at = Column(DateTime(timezone=True))

    # Action taken
    action_taken = Column(Text)
    resolved = Column(Boolean, default=False)

    # Audit, server_default=func.now())

    # Relationships
    staff_reviewed_by = relationship("User")

    __table_args__ = (
        Index("ix_legal_feedback_content", "content_type", "content_id"),
        Index("ix_legal_feedback_type_resolved", "feedback_type", "resolved"),
    )


# ============================================================================
# Content Management
# ============================================================================

# ============================================================================
# Content Management
# ============================================================================

class LegalContentAuditLog(Base):
    __tablename__ = "legal_content_audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # What content
    content_type = Column(String(50), nullable=False)
    content_id = Column(Integer, nullable=False)

    # What action
    action = Column(String(50), nullable=False)  # create, update, publish, archive

    # Changes
    changes = Column(JSONB)  # Before/after values
    change_summary = Column(Text)

    # Who (SET NULL: preserve audit log history)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # When, server_default=func.now())

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index("ix_legal_audit_content", "content_type", "content_id"),
    )

# ============================================================================
# Usage Statistics (Anonymized)
# ============================================================================

class LegalResourceStatistics(Base):
    __tablename__ = "legal_resource_statistics"

    id = Column(Integer, primary_key=True, index=True)

    # Time period
    period_date = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly

    # Resource
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer)

    # Metrics
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    search_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)

    # Unique sessions (anonymous count)
    unique_sessions = Column(Integer, default=0)

    # Created automatically, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "period_date", "period_type", "resource_type", "resource_id",
            name="uq_legal_stats_period_resource"
        ),
        Index("ix_legal_stats_period", "period_date", "period_type"),
    )

class LegalSearchLog(Base):
    __tablename__ = "legal_search_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Search query (sanitized)
    query = Column(String(500), nullable=False)
    query_normalized = Column(String(500))  # Lowercase, trimmed

    # Results
    result_count = Column(Integer, default=0)
    result_clicked = Column(Boolean, default=False)

    # Search context
    search_type = Column(String(50))  # forms, guides, glossary, all
    filters_used = Column(JSONB, default={})

    # Timing
    searched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_legal_search_query_date", "query_normalized", "searched_at"),
    )


# ============================================================================
# Staff Training Guidelines
# ============================================================================

# ============================================================================
# Staff Training Guidelines
# ============================================================================

class LegalStaffGuideline(Base):
    __tablename__ = "legal_staff_guidelines"

    id = Column(Integer, primary_key=True, index=True)

    # Guideline identification
    title = Column(String(300), nullable=False)
    slug = Column(String(150), nullable=False, unique=True, index=True)

    # Category
    category = Column(String(100), nullable=False)  # boundaries, scripts, referrals, etc.

    # Content
    content = Column(Text, nullable=False)

    # Examples of what staff CAN do
    can_do_examples = Column(JSONB, default=[])

    # Examples of what staff CANNOT do
    cannot_do_examples = Column(JSONB, default=[])

    # Scripts for common questions
    scripts = Column(JSONB, default=[])

    # Referral decision tree (JSON structure)
    referral_tree = Column(JSONB)

    # Related topics
    topic_ids = Column(JSONB, default=[])

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit, server_default=func.now())


# ============================================================================
# Library Integration
# ============================================================================

# ============================================================================
# Library Integration
# ============================================================================

class LegalCatalogLink(Base):
    __tablename__ = "legal_catalog_links"

    id = Column(Integer, primary_key=True, index=True)

    # Legal resource
    topic_id = Column(
        Integer, ForeignKey("legal_topics.id", ondelete="CASCADE"),
        nullable=True
    )
    guide_id = Column(
        Integer, ForeignKey("legal_guides.id", ondelete="CASCADE"),
        nullable=True
    )

    # Catalog item
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relevance/display
    relevance_score = Column(Float, default=1.0)
    display_order = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)

    # Audit, server_default=func.now())

    # Relationships
    topic = relationship("LegalTopic")
    guide = relationship("LegalGuide")
    catalog_item = relationship("CatalogItem")

    __table_args__ = (
        Index("ix_legal_catalog_topic", "topic_id"),
        Index("ix_legal_catalog_guide", "guide_id"),
    )


# ============================================================================
# Scenario-Based Collections (Phase 1 Expansion)
# ============================================================================

# ============================================================================
# Scenario-Based Collections (Phase 1 Expansion)
# ============================================================================

class LegalCollection(Base):
    __tablename__ = "legal_collections"

    id = Column(Integer, primary_key=True, index=True)

    # Collection identification
    title = Column(String(300), nullable=False, index=True)
    slug = Column(String(150), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)

    # Situation categorization
    situation = Column(String(100), nullable=False, index=True)  # "eviction", "immigration", etc.

    # Resource relationships (stored as JSONB arrays of IDs)
    guide_ids = Column(JSONB, default=list)
    form_ids = Column(JSONB, default=list)
    clinic_ids = Column(JSONB, default=list)
    provider_ids = Column(JSONB, default=list)
    glossary_term_ids = Column(JSONB, default=list)

    # Journey metadata
    estimated_time_minutes = Column(Integer)
    complexity_level = Column(String(50))  # "beginner", "intermediate", "advanced"
    success_outcomes = Column(JSONB, default=list)  # What user should accomplish
    reading_level = Column(String(50), default="college")  # Reading level of content

    # Cost information (Librarian recommendation - Priority 1)
    estimated_cost_min = Column(Integer, default=0)  # Min cost in dollars
    estimated_cost_max = Column(Integer)  # Max cost in dollars (null = no cost)
    cost_description = Column(String(255))  # e.g., "Court filing fee only"
    fee_waiver_available = Column(Boolean, default=True)  # Can costs be waived?

    # Content fields
    step_by_step_summary = Column(JSONB, default=list)  # Array of step summaries
    icon = Column(String(50))  # Icon identifier (e.g., "home", "briefcase")
    color_code = Column(String(20))  # CSS color class

    # Accessibility
    available_languages = Column(JSONB, default=list)

    # Statistics
    view_count = Column(Integer, default=0)
    click_through_count = Column(Integer, default=0)
    completion_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    unhelpful_count = Column(Integer, default=0)

    # Resource details (Librarian recommendation - Priority 1)
    resource_details = Column(JSONB, default=list)  # Detailed list of what's inside

    # Trust & maintenance (Librarian recommendation - Priority 1)
    last_reviewed_date = Column(DateTime(timezone=True))  # When content was last verified

    # Status & publishing
    is_published = Column(Boolean, default=False, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index("ix_legal_collection_situation", "situation"),
        Index("ix_legal_collection_featured", "is_featured", "display_order"),
        Index("ix_legal_collection_published", "is_published"),
    )
