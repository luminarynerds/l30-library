# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
    Boolean,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ContentType(StrEnum):
    SOCIAL_POST = "social_post"
    NEWSLETTER = "newsletter"
    FLYER = "flyer"
    PROGRAM_PROMO = "program_promo"
    EVENT_PROMO = "event_promo"


class GeneratedContent(Base):
    __tablename__ = "generated_marketing_content"

    id = Column(Integer, primary_key=True, index=True)

    # Content
    content_type = Column(
        SQLEnum(ContentType, name="marketing_content_type", create_type=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=True)
    generated_text = Column(Text, nullable=False)

    # Generation metadata
    user_prompt = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=True)
    model_used = Column(String(100), nullable=True)
    temperature = Column(Float, default=0.7)
    generation_time_ms = Column(Integer, nullable=True)

    # Source references (what library data was used as context)
    program_id = Column(Integer, nullable=True, index=True)
    event_id = Column(Integer, nullable=True, index=True)
    # Context data snapshot (the program/event data at generation time)
    context_data = Column(JSON, nullable=True)

    # User actions
    is_favorite = Column(Boolean, default=False, nullable=False)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    created_by = relationship("User")

    __table_args__ = (
        Index("ix_gen_content_type_created", "content_type", "created_at"),
        Index("ix_gen_content_user_created", "created_by_id", "created_at"),
    )
