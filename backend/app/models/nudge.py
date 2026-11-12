# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import (
    Boolean, Column, DateTime, Integer, SmallInteger, String, Text,
    ForeignKey, JSON, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func

from ..core.database import Base


class Nudge(Base):
    __tablename__ = "nudges"

    id = Column(Integer, primary_key=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    trigger_conditions = Column(JSON, nullable=False, server_default="[]")
    content_title = Column(String(200), nullable=True)
    content_body = Column(Text, nullable=False)
    content_cta_label = Column(String(100), nullable=True)
    content_cta_route = Column(String(200), nullable=True)
    delivery_type = Column(String(20), nullable=False)
    delivery_placement = Column(String(50), nullable=False, server_default="global")
    priority = Column(SmallInteger, nullable=False, server_default="5")
    cooldown_seconds = Column(Integer, nullable=False, server_default="604800")
    max_impressions = Column(SmallInteger, nullable=False, server_default="3")
    tags = Column(ARRAY(String(50)), nullable=False, server_default="{}")
    active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PatronNudgeState(Base):
    __tablename__ = "patron_nudge_state"

    id = Column(Integer, primary_key=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nudge_id = Column(Integer, ForeignKey("nudges.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, server_default="shown")
    impressions = Column(SmallInteger, nullable=False, server_default="1")
    first_shown_at = Column(DateTime(timezone=True), server_default=func.now())
    last_shown_at = Column(DateTime(timezone=True), server_default=func.now())
    dismissed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("patron_id", "nudge_id", name="uq_patron_nudge"),
        Index("ix_patron_nudge_state_patron_status", "patron_id", "status"),
    )
