# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class ReadingProgress(Base, TimestampMixin):

    __tablename__ = "reading_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    current_page = Column(Integer, nullable=True)
    total_pages = Column(Integer, nullable=True)
    percent = Column(Integer, nullable=False)  # 0-100
    note = Column(String(280), nullable=True)
    logged_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User")
    catalog_item = relationship("CatalogItem")
