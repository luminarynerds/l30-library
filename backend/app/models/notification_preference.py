# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class UserNotificationPreference(TimestampMixin, Base):
    __tablename__ = "user_notification_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Per-type channel preferences stored as JSON
    # Structure: {"checkout_receipt": {"email": true, "in_app": true, "sms": false, "is_digest": false}, ...}
    channel_preferences = Column(JSON, nullable=False, default=dict)

    # Digest configuration
    digest_enabled = Column(Boolean, nullable=False, default=False)
    digest_frequency = Column(String(20), nullable=False, default="daily")
    digest_preferred_time = Column(String(5), nullable=False, default="09:00")
    digest_preferred_day = Column(Integer, nullable=False, default=0)

    # Quiet hours
    quiet_hours_enabled = Column(Boolean, nullable=False, default=False)
    quiet_hours_start = Column(String(5), nullable=False, default="22:00")
    quiet_hours_end = Column(String(5), nullable=False, default="08:00")
    quiet_hours_days = Column(JSON, nullable=False, default=lambda: [0, 1, 2, 3, 4, 5, 6])

    # Relationship
    user = relationship("User", back_populates="notification_preferences")

    def __repr__(self):
        return f"<UserNotificationPreference(user_id={self.user_id})>"
