# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class ReadingActivity(Base, TimestampMixin):

    __tablename__ = "reading_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    activity_type = Column(
        String(50), nullable=False
    )  # progress_logged, status_changed, milestone_earned, book_finished, book_added
    summary = Column(String(500), nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON string for extra data
    occurred_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User")
    catalog_item = relationship("CatalogItem")
