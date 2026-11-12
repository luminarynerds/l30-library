# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class LearningPathCohortMember(Base):

    __tablename__ = "learning_path_cohort_members"

    id = Column(Integer, primary_key=True, index=True)
    learning_path_id = Column(
        Integer,
        ForeignKey("learning_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opted_in_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    learning_path = relationship("LearningPath", foreign_keys=[learning_path_id])

    __table_args__ = (
        Index(
            "ix_lp_cohort_members_path_user",
            "learning_path_id",
            "user_id",
        ),
    )


class LearningPathDiscussionPost(Base):

    __tablename__ = "learning_path_discussion_posts"

    id = Column(Integer, primary_key=True, index=True)
    learning_path_id = Column(
        Integer,
        ForeignKey("learning_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_display_name = Column(String(255), nullable=False, default="")
    body = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    author = relationship("User", foreign_keys=[user_id])
    learning_path = relationship("LearningPath", foreign_keys=[learning_path_id])

    __table_args__ = (
        Index(
            "ix_lp_discussion_posts_path_created",
            "learning_path_id",
            "created_at",
        ),
    )
