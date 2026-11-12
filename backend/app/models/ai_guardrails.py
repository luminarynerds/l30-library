# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class AIGuardrail(Base):
    __tablename__ = "ai_guardrails"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)

    # Rule type: "blocked_topic", "required_disclaimer", "content_filter", "response_prefix"
    rule_type = Column(String(50), nullable=False, index=True)

    # The rule configuration stored as JSON
    # For blocked_topic: {"keywords": ["word1", "word2"], "message": "I can't discuss that topic."}
    # For required_disclaimer: {"text": "This is AI-generated content...", "position": "prepend"|"append"}
    # For content_filter: {"max_length": 2000, "block_urls": true, "block_code": false}
    # For response_prefix: {"text": "As a library AI assistant, "}
    rule_config = Column(JSONB, nullable=False, default=dict)

    # Which tools this applies to (empty = all tools)
    applies_to_tools = Column(JSONB, default=list)

    # Audience scoping for minor gating.
    # audience_minor: "all" | "minors_only" | "adults_only"
    # audience_patron_types: list of patron_type strings (e.g. ["child", "teen"]);
    #   empty list = applies to every patron_type.
    audience_minor = Column(String(20), default="all", nullable=False)
    audience_patron_types = Column(JSONB, default=list, nullable=False)

    # Priority for ordering (lower = applied first)
    priority = Column(Integer, default=0, nullable=False)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<AIGuardrail {self.name} ({self.rule_type})>"


class AIModelAllowlist(Base):
    __tablename__ = "ai_model_allowlist"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    max_tokens_limit = Column(Integer, default=4000, nullable=False)
    allowed_temperature_min = Column(Float, default=0.0, nullable=False)
    allowed_temperature_max = Column(Float, default=1.5, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<AIModelAllowlist {self.model_name}>"


class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    tool_id = Column(String(50), nullable=True)
    model_used = Column(String(100), nullable=True)

    # Request details
    prompt_preview = Column(String(500), nullable=True)  # First 500 chars of prompt
    system_prompt_used = Column(Text, nullable=True)

    # Response details
    response_preview = Column(String(500), nullable=True)  # First 500 chars
    generation_time_ms = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)

    # Guardrail outcomes
    guardrails_triggered = Column(JSONB, default=list)  # List of guardrail IDs that fired
    was_blocked = Column(Boolean, default=False, nullable=False)
    block_reason = Column(Text, nullable=True)

    # Audience snapshot at time of request (for minor-gating audit)
    was_minor = Column(Boolean, default=False, nullable=False)
    patron_type_at_request = Column(String(20), nullable=True)

    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<AIUsageLog {self.id} tool={self.tool_id}>"


class AIUsageLimit(Base):
    __tablename__ = "ai_usage_limits"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), unique=True, nullable=False)  # PATRON, STAFF, ADMIN, etc.
    daily_limit = Column(Integer, default=50, nullable=False)
    hourly_limit = Column(Integer, default=10, nullable=False)
    max_tokens_per_request = Column(Integer, default=2000, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<AIUsageLimit {self.role}>"
