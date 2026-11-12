# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class IndieBookmark(Base):
    __tablename__ = "indie_bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ebook_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "ebook_id", name="uq_indie_bookmark"),
        Index("ix_indie_bookmarks_user", "user_id"),
        Index("ix_indie_bookmarks_ebook", "ebook_id"),
    )
