# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from ..core.database import Base


class WatermarkRecord(Base):
    __tablename__ = "watermark_records"

    id = Column(Integer, primary_key=True, index=True)
    borrow_id = Column(Integer, ForeignKey("indie_ebook_borrows.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    watermark_id = Column(String(64), unique=True, nullable=False, index=True)
    patron_hash = Column(String(64), nullable=False)
    library_id = Column(String(64), nullable=True)
    file_sha256 = Column(String(64), nullable=False)
    original_sha256 = Column(String(64), nullable=False)
    file_format = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    borrow_timestamp = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    user = relationship("User", backref="watermark_records")
