# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import secrets

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def _generate_token() -> str:
    return secrets.token_urlsafe(24)[:32]


class IndieReadingList(Base):
    __tablename__ = "indie_reading_lists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    share_token = Column(String(32), unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    items = relationship("IndieReadingListItem", back_populates="reading_list", cascade="all, delete-orphan")


class IndieReadingListItem(Base):
    __tablename__ = "indie_reading_list_items"

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("indie_reading_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    note = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("list_id", "ebook_id", name="uq_indie_list_ebook"),
    )

    reading_list = relationship("IndieReadingList", back_populates="items")
    ebook = relationship("IndieEbook", foreign_keys=[ebook_id])
