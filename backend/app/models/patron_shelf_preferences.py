# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class PatronShelfPreferences(Base, TimestampMixin):

    __tablename__ = "patron_shelf_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    show_reading_activity = Column(Boolean, nullable=False, default=False)
    show_pace_stats = Column(Boolean, nullable=False, default=False)

    user = relationship("User")
