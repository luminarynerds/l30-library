# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import enum
from enum import Enum, StrEnum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Enum, JSON
from sqlalchemy.orm import relationship

from ..core.database import Base


class DmcaNoticeStatus(StrEnum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"          # Content taken down
    REJECTED = "rejected"          # Not valid notice
    COUNTER_FILED = "counter_filed"
    RESTORED = "restored"          # Counter-notice waiting period expired


class DmcaNotice(Base):
    __tablename__ = "dmca_notices"

    id = Column(Integer, primary_key=True, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), nullable=False, index=True)

    # Complainant info (all 6 elements of § 512(c)(3))
    complainant_name = Column(String(200), nullable=False)
    complainant_email = Column(String(200), nullable=False)
    complainant_address = Column(Text, nullable=True)
    complainant_phone = Column(String(50), nullable=True)
    copyrighted_work_description = Column(Text, nullable=False)
    infringing_material_description = Column(Text, nullable=False)
    good_faith_statement = Column(Boolean, default=False, nullable=False)
    accuracy_statement = Column(Boolean, default=False, nullable=False)
    perjury_statement = Column(Boolean, default=False, nullable=False)
    signature = Column(String(200), nullable=False)

    status = Column(Enum(DmcaNoticeStatus, values_callable=lambda x: [m.value for m in x]), default=DmcaNoticeStatus.PENDING, nullable=False, index=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    counter_notices = relationship("DmcaCounterNotice", back_populates="notice")
    audit_logs = relationship("DmcaAuditLog", back_populates="notice")


class DmcaCounterNotice(Base):
    __tablename__ = "dmca_counter_notices"

    id = Column(Integer, primary_key=True, index=True)
    notice_id = Column(Integer, ForeignKey("dmca_notices.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("indie_authors.id", ondelete="CASCADE"), nullable=False, index=True)

    statement = Column(Text, nullable=False)
    consent_to_jurisdiction = Column(Boolean, default=False, nullable=False)
    perjury_statement = Column(Boolean, default=False, nullable=False)
    signature = Column(String(200), nullable=False)
    contact_info = Column(Text, nullable=False)

    # 10-14 business day waiting period
    waiting_period_ends_at = Column(DateTime(timezone=True), nullable=True)
    resolved = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    notice = relationship("DmcaNotice", back_populates="counter_notices")


class DmcaStrike(Base):
    __tablename__ = "dmca_strikes"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("indie_authors.id", ondelete="CASCADE"), nullable=False, index=True)
    notice_id = Column(Integer, ForeignKey("dmca_notices.id", ondelete="CASCADE"), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    notice = relationship("DmcaNotice")


class DmcaAuditLog(Base):
    __tablename__ = "dmca_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    notice_id = Column(Integer, ForeignKey("dmca_notices.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # e.g., "submitted", "approved", "counter_filed", "restored"
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_type = Column(String(20), nullable=False)  # "public", "staff", "author", "system"
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    notice = relationship("DmcaNotice", back_populates="audit_logs")
    actor = relationship("User", foreign_keys=[actor_id])
