# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class TrainingExample(Base):

    __tablename__ = "training_examples"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_entry_id = Column(
        Integer, ForeignKey("knowledge_entries.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    persona_domain = Column(String(50), nullable=True, index=True)
    instruction = Column(Text, nullable=False)  # User question
    response = Column(Text, nullable=False)  # Assistant answer
    source_type = Column(String(50), nullable=False, index=True)

    # Quality scoring
    quality_score = Column(Integer, nullable=False, default=0)  # 0-100
    quality_breakdown = Column(JSONB, nullable=True)  # Component scores
    bucket = Column(String(20), nullable=False, default="review", index=True)  # approved/review/rejected

    # Context
    location_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    is_multi_turn = Column(Boolean, nullable=False, default=False)
    turn_index = Column(Integer, nullable=True)
    conversation_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(255), nullable=True)

    # Staff override
    staff_override = Column(Boolean, nullable=False, default=False)
    override_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_training_examples_bucket_persona", "bucket", "persona_domain"),
        Index("ix_training_examples_source_persona", "source_type", "persona_domain"),
    )
