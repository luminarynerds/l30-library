# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Index,
                        Integer, String, Text)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


class ContentType(StrEnum):
    POLICY = "policy"
    PROCEDURE = "procedure"
    HOW_TO = "how_to"
    DECISION_TREE = "decision_tree"
    VIDEO_TUTORIAL = "video_tutorial"
    ONBOARDING = "onboarding"
    FAQ = "faq"


class KnowledgeFlagStatus(StrEnum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class KnowledgeEntry(Base):

    __tablename__ = "knowledge_entries"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), index=True, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    # Content classification
    entry_type = Column(String(30), nullable=True, index=True)  # faq, guide, policy, how-to, read-alike
    summary = Column(String(500), nullable=True)  # Short preview for card display

    # Additional structured data (JSON)
    entry_metadata = Column(JSON, nullable=True)

    # For read-alikes specifically
    if_you_liked = Column(String(200), nullable=True)
    if_you_liked_author = Column(String(200), nullable=True)
    then_try = Column(String(200), nullable=True)
    then_try_author = Column(String(200), nullable=True)
    reason = Column(Text, nullable=True)

    # Search and discovery
    tags = Column(String(500), nullable=True)  # comma-separated
    is_featured = Column(Boolean, default=False, nullable=False)

    # Audit fields
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    added_by_name = Column(String(100), nullable=True)  # Display name like "Patty"

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Stats
    view_count = Column(Integer, default=0, nullable=False)
    helpful_count = Column(Integer, default=0, nullable=False)

    # Knowledge pipeline fields
    source_type = Column(String(50), nullable=True, default="manual", index=True)  # manual, patron_interaction, document_import, synthetic
    persona_domain = Column(String(50), nullable=True, index=True)  # reference, youth, digital, outreach, shared
    location_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)  # None = system-wide
    expires_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    review_status = Column(String(20), nullable=False, default="approved")  # pending, approved, rejected
    embedding_id = Column(Integer, ForeignKey("text_embeddings.id"), nullable=True)
    source_reference_id = Column(String(255), nullable=True)  # FK to source record

    def __repr__(self) -> str:
        return f"<KnowledgeEntry(category='{self.category}', title='{self.title}')>"


class StaffKnowledgeArticle(Base):

    __tablename__ = "staff_knowledge_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(250), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    content_type = Column(String(30), nullable=False, index=True)  # Uses ContentType enum

    # Categorization
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)
    tags = Column(String(500), nullable=True)  # comma-separated for search

    # Accessibility / alternate formats
    summary = Column(String(500), nullable=True)  # plain-language TL;DR
    transcript = Column(Text, nullable=True)  # text transcript / alt format of the article
    audio_url = Column(String, nullable=True)  # optional TTS/audio version

    # Metadata
    is_published = Column(Boolean, default=True, nullable=False)
    current_version = Column(Integer, default=1, nullable=False)

    # Author and audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Engagement metrics
    view_count = Column(Integer, default=0, nullable=False)
    bookmark_count = Column(Integer, default=0, nullable=False)
    helpful_count = Column(Integer, default=0, nullable=False)
    unhelpful_count = Column(Integer, default=0, nullable=False)

    # Relationships
    versions = relationship(
        "ArticleVersion",
        back_populates="article",
        cascade="all, delete-orphan",
        lazy="joined"
    )
    bookmarks = relationship(
        "ArticleBookmark",
        back_populates="article",
        cascade="all, delete-orphan"
    )
    flags = relationship(
        "KnowledgeContentFlag",
        back_populates="article",
        cascade="all, delete-orphan"
    )
    qa_entries = relationship(
        "StaffQA",
        back_populates="related_article",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<StaffKnowledgeArticle(title='{self.title}', type='{self.content_type}')>"


class ArticleVersion(Base):

    __tablename__ = "article_versions"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(
        Integer, ForeignKey("staff_knowledge_articles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    version_number = Column(Integer, nullable=False)
    title = Column(String(250), nullable=False)
    content = Column(Text, nullable=False)
    change_notes = Column(Text, nullable=True)

    # Author and audit
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    article = relationship("StaffKnowledgeArticle", back_populates="versions")

    def __repr__(self) -> str:
        return f"<ArticleVersion(article_id={self.article_id}, version={self.version_number})>"


class DecisionTree(Base):

    __tablename__ = "decision_trees"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(250), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    category = Column(String(100), nullable=False, index=True)

    # Structure is JSON - nodes with yes/no branches leading to outcomes
    tree_data = Column(JSON, nullable=False)

    is_published = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    view_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<DecisionTree(title='{self.title}')>"


class VideoTutorial(Base):

    __tablename__ = "video_tutorials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(250), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    category = Column(String(100), nullable=False, index=True)

    # Video URL and metadata
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Transcript or supplementary content
    transcript = Column(Text, nullable=True)
    related_article_ids = Column(JSON, default=[])  # Array of staff article IDs

    is_published = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    view_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<VideoTutorial(title='{self.title}')>"


class OnboardingChecklist(Base):

    __tablename__ = "onboarding_checklists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(250), nullable=False)
    description = Column(Text, nullable=True)

    # Template for the checklist (JSON with tasks)
    # Format: [{"id": "task_id", "title": "...", "description": "...", "due_days": 7, "completed": false, "completed_at": null}]
    checklist_items = Column(JSON, nullable=False)

    # Status tracking
    is_completed = Column(Boolean, default=False, nullable=False)
    start_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    assigned_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<OnboardingChecklist(user_id={self.user_id}, title='{self.title}')>"


class StaffQA(Base):

    __tablename__ = "staff_qa"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    tags = Column(String(500), nullable=True)  # comma-separated

    # Author
    asked_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    related_article_id = Column(Integer, ForeignKey("staff_knowledge_articles.id", ondelete="SET NULL"), nullable=True)

    # Status
    is_answered = Column(Boolean, default=False, nullable=False)
    is_closed = Column(Boolean, default=False, nullable=False)

    answer = Column(Text, nullable=True)
    answered_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    answer_upvotes = Column(Integer, default=0, nullable=False)
    answered_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    related_article = relationship("StaffKnowledgeArticle", back_populates="qa_entries")

    def __repr__(self) -> str:
        return f"<StaffQA(question='{self.question[:50]}...', is_answered={self.is_answered})>"


class ArticleBookmark(Base):

    __tablename__ = "article_bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    article_id = Column(
        Integer, ForeignKey("staff_knowledge_articles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    article = relationship("StaffKnowledgeArticle", back_populates="bookmarks")

    def __repr__(self) -> str:
        return f"<ArticleBookmark(user_id={self.user_id}, article_id={self.article_id})>"


class KnowledgeContentFlag(Base):

    __tablename__ = "knowledge_content_flags"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(
        Integer, ForeignKey("staff_knowledge_articles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    reason = Column(String(100), nullable=False)  # "outdated", "incorrect", "unclear", etc.
    description = Column(Text, nullable=False)

    status = Column(String(20), default="pending", nullable=False)  # Uses KnowledgeFlagStatus enum
    flagged_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewer_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    article = relationship("StaffKnowledgeArticle", back_populates="flags")

    def __repr__(self) -> str:
        return f"<KnowledgeContentFlag(article_id={self.article_id}, status='{self.status}')>"


class FAQChatbotConversation(Base):

    __tablename__ = "faq_chatbot_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)  # For anonymous users

    # The question asked
    original_question = Column(Text, nullable=False)
    question_category = Column(String(100), nullable=True, index=True)

    # Matched FAQ and response
    matched_faq_id = Column(Integer, ForeignKey("knowledge_entries.id", ondelete="SET NULL"), nullable=True)
    matched_pattern_id = Column(Integer, ForeignKey("faq_patterns.id", ondelete="SET NULL"), nullable=True)
    chatbot_response = Column(Text, nullable=True)
    confidence_score = Column(Integer, nullable=True)  # 0-100

    # Outcome tracking
    was_helpful = Column(Boolean, nullable=True)  # Did patron find answer helpful?
    escalated_to_support = Column(Boolean, default=False)
    support_ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    device_type = Column(String(50), nullable=True)  # mobile, desktop, etc.
    location = Column(String(100), nullable=True)  # "catalog", "homepage", etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<FAQChatbotConversation(question='{self.original_question[:50]}...', helpful={self.was_helpful})>"


class FAQPattern(Base):

    __tablename__ = "faq_patterns"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_entry_id = Column(Integer, ForeignKey("knowledge_entries.id", ondelete="CASCADE"), nullable=False, index=True)

    # Pattern variations (e.g., "What are your hours?", "When are you open?", "What time do you close?")
    pattern_text = Column(String(500), nullable=False)  # Normalized question pattern
    pattern_keywords = Column(String(500), nullable=True)  # Comma-separated keywords

    # Matching parameters
    match_type = Column(String(50), nullable=False)  # "exact", "keyword", "semantic"
    priority = Column(Integer, default=1)  # Higher = matches first (1-10)

    # Tracking
    match_count = Column(Integer, default=0)  # How many times this pattern was matched

    is_active = Column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<FAQPattern(pattern='{self.pattern_text}', match_type='{self.match_type}')>"


class FAQAnalytics(Base, TimestampMixin):

    __tablename__ = "faq_analytics"

    id = Column(Integer, primary_key=True, index=True)

    # Question tracking
    question_text = Column(String(500), nullable=False, index=True)
    normalized_question = Column(String(500), nullable=True)  # Standardized form

    # Statistics
    ask_count = Column(Integer, default=0)  # Total times asked
    chatbot_answered_count = Column(Integer, default=0)  # Times chatbot handled it
    escalated_count = Column(Integer, default=0)  # Times escalated to staff
    satisfaction_rate = Column(Integer, default=0)  # 0-100: % of "helpful" responses

    # Category and season
    category = Column(String(100), nullable=True, index=True)
    seasonal = Column(Boolean, default=False)  # Is this seasonal? (tax forms, summer reading)
    season = Column(String(50), nullable=True)  # "spring", "summer", "fall", "winter", "tax_season"

    # Trending
    is_trending = Column(Boolean, default=False, index=True)
    trend_score = Column(Integer, default=0)  # Higher = trending more

    # Insights
    suggested_signage = Column(Boolean, default=False)  # Should this be on signage?
    signage_priority = Column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<FAQAnalytics(question='{self.question_text[:50]}...', ask_count={self.ask_count})>"


class SeasonalFAQ(Base):

    __tablename__ = "seasonal_faqs"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_entry_id = Column(Integer, ForeignKey("knowledge_entries.id", ondelete="CASCADE"), nullable=False, index=True)

    # Season configuration
    season = Column(String(50), nullable=False)  # "spring", "summer", "fall", "winter", "tax_season", "holiday", "custom"
    start_date = Column(String(10), nullable=False)  # MM-DD format (e.g., "04-01")
    end_date = Column(String(10), nullable=False)  # MM-DD format (e.g., "05-31")

    # Status
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)  # Display priority when multiple seasonal FAQs exist

    # Display customization
    seasonal_note = Column(String(200), nullable=True)  # e.g., "Available during tax season"
    custom_content = Column(Text, nullable=True)  # Override content for this season

    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    def __repr__(self) -> str:
        return f"<SeasonalFAQ(entry_id={self.knowledge_entry_id}, season='{self.season}')>"


class PatronChatbotContext(Base):

    __tablename__ = "patron_chatbot_context"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)

    # Last chatbot interaction
    last_question = Column(Text, nullable=True)
    last_interaction_at = Column(DateTime(timezone=True), nullable=True)
    total_interactions = Column(Integer, default=0)

    # Issues resolved by chatbot
    questions_resolved_count = Column(Integer, default=0)  # Patron said "helpful"
    questions_escalated_count = Column(Integer, default=0)  # Patron couldn't find answer

    # Current issue (if escalated)
    current_unresolved_question = Column(Text, nullable=True)
    escalation_count_today = Column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<PatronChatbotContext(user_id={self.user_id}, total_interactions={self.total_interactions})>"


# Create indexes
Index(
    "idx_knowledge_category_featured",
    KnowledgeEntry.category,
    KnowledgeEntry.is_featured,
)
Index("idx_knowledge_readalike", KnowledgeEntry.if_you_liked, KnowledgeEntry.then_try)
Index("idx_article_search", StaffKnowledgeArticle.title, StaffKnowledgeArticle.category)
Index("idx_bookmark_user_article", ArticleBookmark.user_id, ArticleBookmark.article_id)
Index("idx_flag_article_status", KnowledgeContentFlag.article_id, KnowledgeContentFlag.status)
Index("idx_chatbot_conversation_user", FAQChatbotConversation.user_id, FAQChatbotConversation.created_at)
Index("idx_chatbot_conversation_session", FAQChatbotConversation.session_id, FAQChatbotConversation.created_at)
Index("idx_faq_pattern_entry", FAQPattern.knowledge_entry_id, FAQPattern.priority)
Index("idx_faq_analytics_trending", FAQAnalytics.is_trending, FAQAnalytics.trend_score)
Index("idx_seasonal_faq_entry", SeasonalFAQ.knowledge_entry_id, SeasonalFAQ.season)
