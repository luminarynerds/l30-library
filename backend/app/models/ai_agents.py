# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text, Boolean
from sqlalchemy.sql import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class AgentDepartment(StrEnum):
    ADMINISTRATION = "administration"
    YOUTH_SERVICES = "youth services"
    ADULT_SERVICES = "adult services"
    TECHNICAL_SERVICES = "technical services"
    CIRCULATION = "circulation"
    OUTREACH = "outreach"
    TECHNOLOGY = "technology"


class AgentPersonality(StrEnum):
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    QUIRKY = "quirky"
    ENTHUSIASTIC = "enthusiastic"
    CALM = "calm"
    WITTY = "witty"


class LibraryAgent(Base):
    __tablename__ = "library_agents"

    id = Column(Integer, primary_key=True, index=True)

    # Agent identity
    name = Column(String(100), nullable=False, unique=True)
    nickname = Column(String(100))
    role = Column(String(200), nullable=False)
    department = Column(String(50), nullable=False)

    # Personality and voice
    bio = Column(Text, nullable=False)
    personality = Column(String(50), default="friendly")
    tone = Column(String(50))  # casual, formal, warm, etc.

    # Agent capabilities
    specialties = Column(JSONB, default=list)  # ["children's books", "STEM programs", etc.]
    can_help_with = Column(JSONB, default=list)  # List of tasks/questions
    typical_responses = Column(JSONB, default=dict)  # Sample phrases/greetings

    # Visual representation
    avatar_color = Column(String(50))
    initials = Column(String(5))
    emoji = Column(String(10))

    # System prompt and behavior
    system_prompt = Column(Text, nullable=False)
    greeting_message = Column(Text)
    out_of_scope_message = Column(Text)

    # Availability and status
    is_active = Column(Boolean, default=True)
    available_hours = Column(
        JSONB
    )  # {"start": "09:00", "end": "17:00", "timezone": "America/Toronto"}

    # Minor / age gating (see CLAUDE.md). When block_for_minors is true the tool
    # implicitly requires auth so the user's age can be evaluated.
    block_for_minors = Column(Boolean, default=False, nullable=False)
    requires_parental_consent = Column(Boolean, default=False, nullable=False)
    block_for_patron_types = Column(JSONB, default=list, nullable=False)

    # Metadata
    email = Column(String(255))

    # Relationships
    conversations = relationship(
        "AgentConversation", back_populates="agent", cascade="all, delete-orphan"
    )


class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    id = Column(Integer, primary_key=True, index=True)

    # Participants
    agent_id = Column(Integer, ForeignKey("library_agents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )  # Null for anonymous
    session_id = Column(String(100), nullable=False, index=True)

    # Conversation content
    user_message = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)

    # Context
    conversation_context = Column(JSONB)  # Previous messages, user preferences, etc.
    detected_intent = Column(String(100))  # "book_recommendation", "hours_question", etc.

    # Feedback
    helpful = Column(Boolean)  # User feedback
    feedback_note = Column(Text)

    # Metadata
    seen_by_patron_at = Column(DateTime(timezone=True), nullable=True)
    patron_followup_email = Column(String(255), nullable=True)
    response_time_ms = Column(Integer)  # How long did it take to respond
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "ix_agent_conversations_session_unread",
            "session_id",
            postgresql_where=text("seen_by_patron_at IS NULL"),
        ),
    )

    # Relationships
    agent = relationship("LibraryAgent", back_populates="conversations")
    user = relationship("User", foreign_keys=[user_id])


class AgentKnowledgeBase(Base):
    __tablename__ = "agent_knowledge_base"

    id = Column(Integer, primary_key=True, index=True)

    # Content
    category = Column(String(100), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    tags = Column(JSONB, default=list)

    # Relevance
    applicable_to_agents = Column(JSONB, default=list)  # List of agent IDs or "all"
    department = Column(String(50))

    # Priority
    is_frequently_asked = Column(Boolean, default=False)
    priority = Column(Integer, default=0)

    # Source
    source_url = Column(String(500))
    last_verified = Column(DateTime(timezone=True))

    # Metadata, server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    created_by = relationship("User", foreign_keys=[created_by_id])


class AgentAnalytics(Base):
    __tablename__ = "agent_analytics"

    id = Column(Integer, primary_key=True, index=True)

    agent_id = Column(Integer, ForeignKey("library_agents.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Usage metrics
    total_conversations = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)

    # Quality metrics
    positive_feedback_count = Column(Integer, default=0)
    negative_feedback_count = Column(Integer, default=0)
    avg_response_time_ms = Column(Integer)

    # Popular intents
    top_intents = Column(
        JSONB, default=dict
    )  # {"book_rec": 15, "hours": 10, etc.}, server_default=func.now())

    agent = relationship("LibraryAgent", foreign_keys=[agent_id])
