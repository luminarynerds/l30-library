# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class Review(Base, TimestampMixin):

    __tablename__ = "reviews"

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
    rating = Column(Integer, nullable=True)  # 1-5, nullable allows review without rating
    title = Column(String(255), nullable=True)  # Staff only
    body = Column(Text, nullable=True)  # Staff only
    is_staff_review = Column(Boolean, default=False, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "catalog_item_id", name="uq_user_catalog_review"),
    )

    user = relationship("User", back_populates="reviews")
    catalog_item = relationship("CatalogItem", back_populates="reviews")
