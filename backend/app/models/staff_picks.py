# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.mixins import TimestampMixin


class StaffPicksList(Base, TimestampMixin):
    __tablename__ = "staff_picks_lists"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    items = relationship(
        "StaffPicksItem",
        back_populates="staff_picks_list",
        cascade="all, delete-orphan",
        order_by="StaffPicksItem.display_order"
    )


class StaffPicksItem(Base):
    __tablename__ = "staff_picks_items"

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("staff_picks_lists.id", ondelete="CASCADE"), nullable=False)
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False)
    staff_notes = Column(Text, nullable=True)  # Why staff picked this item
    mood_slug = Column(String(50), nullable=True, index=True)  # Pin to a mood browse category
    display_order = Column(Integer, default=0, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    staff_picks_list = relationship("StaffPicksList", back_populates="items")
    catalog_item = relationship("CatalogItem")
    added_by = relationship("User", foreign_keys=[added_by_id])

    __table_args__ = (
        UniqueConstraint("list_id", "catalog_item_id", name="uq_staff_picks_item"),
    )
