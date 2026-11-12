# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class KnownDevice(Base):
    __tablename__ = "known_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    device_hash = Column(String(64), nullable=False)  # SHA-256 of (UA + IP /24 subnet)
    friendly_name = Column(String(255), nullable=True)  # e.g. "Chrome on Windows"
    ip_address = Column(String(45), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    trusted_until = Column(DateTime(timezone=True), nullable=True)  # 2FA skip expiry

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index("ix_known_devices_user_device", "user_id", "device_hash", unique=True),
    )
