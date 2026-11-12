# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from ..mixins import TimestampMixin
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ...core.database import Base


class BoardRecordRetentionSchedule(Base, TimestampMixin):
    __tablename__ = "board_record_retention_schedules"

    id = Column(Integer, primary_key=True, index=True)
    record_type = Column(String(50), nullable=False, unique=True, index=True)
    retention_years = Column(Integer, nullable=True)  # NULL = permanent
    is_permanent = Column(Boolean, default=True)
    description = Column(Text)
    legal_authority = Column(String(500))

    configured_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    configured_at = Column(DateTime(timezone=True), server_default=func.now())

    configured_by = relationship("User", foreign_keys=[configured_by_id])


class BoardLegalHold(Base, TimestampMixin):
    __tablename__ = "board_legal_holds"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    reason = Column(Text, nullable=False)

    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    date_range_start = Column(DateTime(timezone=True), nullable=True)
    date_range_end = Column(DateTime(timezone=True), nullable=True)

    placed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    placed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    released_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    release_reason = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    placed_by = relationship("User", foreign_keys=[placed_by_id])
    released_by = relationship("User", foreign_keys=[released_by_id])


class BoardRecordDisposition(Base, TimestampMixin):
    __tablename__ = "board_record_dispositions"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    retention_schedule_id = Column(Integer, ForeignKey("board_record_retention_schedules.id", ondelete="SET NULL"), nullable=True)
    performed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    record_metadata = Column(JSONB, default=dict)

    retention_schedule = relationship("BoardRecordRetentionSchedule")
    performed_by = relationship("User", foreign_keys=[performed_by_id])
