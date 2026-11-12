# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import enum
from enum import Enum, StrEnum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Enum, Float
from sqlalchemy.orm import relationship

from ..core.database import Base


class AnomalyType(StrEnum):
    RAPID_DOWNLOADS = "rapid_downloads"
    MULTIPLE_IPS = "multiple_ips"
    EXCESSIVE_VOLUME = "excessive_volume"


class AnomalyStatus(StrEnum):
    OPEN = "open"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    CONFIRMED = "confirmed"


class DownloadEvent(Base):
    __tablename__ = "download_events"

    id = Column(Integer, primary_key=True, index=True)
    borrow_id = Column(Integer, ForeignKey("indie_ebook_borrows.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    ip_hash = Column(String(64), nullable=False, index=True)
    user_agent = Column(String(500), nullable=True)
    file_format = Column(String(20), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    watermark_id = Column(String(64), nullable=True)
    is_range_request = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = relationship("User")


class DownloadAnomaly(Base):
    __tablename__ = "download_anomalies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="SET NULL"), nullable=True)
    anomaly_type = Column(Enum(AnomalyType, values_callable=lambda x: [m.value for m in x]), nullable=False)
    status = Column(Enum(AnomalyStatus, values_callable=lambda x: [m.value for m in x]), default=AnomalyStatus.OPEN, nullable=False, index=True)
    severity = Column(Float, default=0.0)
    details = Column(Text, nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
