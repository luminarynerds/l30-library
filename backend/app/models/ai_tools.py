# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String, Text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


class AITool(Base, TimestampMixin):

    __tablename__ = "ai_tools"

    id = Column(Integer, primary_key=True, index=True)
    tool_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)

    # AI Configuration
    temperature = Column(Float, default=0.7, nullable=False)
    max_tokens = Column(Integer, default=500, nullable=False)
    model = Column(String(100), default="llama3.2:3b", nullable=False)

    # Feature flags
    enabled = Column(Boolean, default=True, nullable=False)
    in_library_only = Column(Boolean, default=False, nullable=False)
    requires_auth = Column(Boolean, default=False, nullable=False)

    # Minor / age gating (see CLAUDE.md). When block_for_minors is true the tool
    # implicitly requires auth so the user's age can be evaluated.
    block_for_minors = Column(Boolean, default=False, nullable=False)
    requires_parental_consent = Column(Boolean, default=False, nullable=False)
    block_for_patron_types = Column(JSONB, default=list, nullable=False)

    # Metadata
    icon = Column(String(50), nullable=True)  # lucide icon name
    category = Column(String(50), nullable=True)  # general, books, writing, etc
    sort_order = Column(Integer, default=0, nullable=False)

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Stats tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<AITool(tool_id='{self.tool_id}', name='{self.name}', enabled={self.enabled})>"
