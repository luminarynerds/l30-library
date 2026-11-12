# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class UserHubFavorite(Base):

    __tablename__ = "user_hub_favorites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hub_slug = Column(String(64), nullable=False, index=True)
    item_path = Column(String(512), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "hub_slug", "item_path", name="uq_user_hub_favorite"
        ),
    )

    user = relationship("User", back_populates="hub_favorites")


class UserHubVisit(Base):

    __tablename__ = "user_hub_visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hub_slug = Column(String(64), nullable=False, index=True)
    item_path = Column(String(512), nullable=False, index=True)
    visited_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_user_hub_visits_user_visited", "user_id", "visited_at"),
    )

    user = relationship("User", back_populates="hub_visits")
