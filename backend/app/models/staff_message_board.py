# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from enum import Enum, StrEnum

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class MessageBoardCategory(StrEnum):

    MEMO = "memo"
    LIBRARY_HAPPENINGS = "library_happenings"
    STATE_NEWS = "state_news"
    GENERAL = "general"
    TIPS_TRICKS = "tips_tricks"
    PROFESSIONAL_DEV = "professional_dev"


class BoardPost(Base, TimestampMixin):

    __tablename__ = "staff_board_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)

    category = Column(
        SQLEnum(
            MessageBoardCategory,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MessageBoardCategory.GENERAL,
        nullable=False,
    )

    pinned = Column(Boolean, default=False, nullable=False)
    archived = Column(Boolean, default=False, nullable=False)

    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author = relationship("User", foreign_keys=[author_id])

    replies = relationship(
        "BoardReply",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="BoardReply.created_at",
    )

    def __repr__(self) -> str:
        return f"<BoardPost(id={self.id}, title='{self.title}', category='{self.category}')>"


class BoardReply(Base, TimestampMixin):

    __tablename__ = "staff_board_replies"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)

    post_id = Column(Integer, ForeignKey("staff_board_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    post = relationship("BoardPost", back_populates="replies")

    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author = relationship("User", foreign_keys=[author_id])

    def __repr__(self) -> str:
        return f"<BoardReply(id={self.id}, post_id={self.post_id})>"
