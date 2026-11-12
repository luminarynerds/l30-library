# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum

from enum import StrEnum
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, JSON, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class ShelfStatus(StrEnum):
    want_to_read = "want_to_read"
    currently_reading = "currently_reading"
    on_hold = "on_hold"
    finished = "finished"
    did_not_finish = "did_not_finish"


class ReadingStatus(Base, TimestampMixin):

    __tablename__ = "reading_statuses"

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
    status = Column(
        SQLEnum(ShelfStatus, name="shelfstatus", create_type=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    private_notes = Column(Text, nullable=True)
    personal_tags = Column(JSON, nullable=False, server_default="[]")

    __table_args__ = (
        UniqueConstraint("user_id", "catalog_item_id", name="uq_user_catalog_reading_status"),
    )

    user = relationship("User", back_populates="reading_statuses")
    catalog_item = relationship("CatalogItem", back_populates="reading_statuses")
