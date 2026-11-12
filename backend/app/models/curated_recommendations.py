# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, Boolean, Text, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.core.database import Base


class CuratedRecommendation(Base):
    __tablename__ = "curated_recommendations"
    __table_args__ = (
        UniqueConstraint("source_item_id", "target_item_id", name="uq_curated_source_target"),
        Index("ix_curated_source_item", "source_item_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False)
    target_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    is_hidden = Column(Boolean, nullable=False, default=False)
    staff_note = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
