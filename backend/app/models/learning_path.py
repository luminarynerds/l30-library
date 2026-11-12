# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.models.mixins import TimestampMixin
from enum import StrEnum

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class PathStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EnrollmentStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class LearningPath(Base, TimestampMixin):

    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)

    # Status and visibility
    status = Column(String(20), default="draft", nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)

    # Metadata
    estimated_hours = Column(Integer, nullable=True)
    difficulty = Column(String(20), default="beginner", nullable=True)
    tags = Column(JSONB, default=list, nullable=False)

    # Prerequisites
    enforce_prerequisites = Column(Boolean, default=True, nullable=False)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    path_courses = relationship(
        "PathCourse",
        back_populates="learning_path",
        cascade="all, delete-orphan",
        order_by="PathCourse.sort_order",
    )
    enrollments = relationship(
        "PathEnrollment", back_populates="learning_path", cascade="all, delete-orphan"
    )


class PathCourse(Base):

    __tablename__ = "path_courses"

    id = Column(Integer, primary_key=True, index=True)
    learning_path_id = Column(
        Integer, ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )

    sort_order = Column(Integer, default=0, nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)

    prerequisite_course_ids = Column(JSONB, default=list, nullable=False)

    description = Column(Text, nullable=True)

    # Relationships
    learning_path = relationship("LearningPath", back_populates="path_courses")
    course = relationship("Course")

    __table_args__ = (
        UniqueConstraint("learning_path_id", "course_id", name="uq_path_course"),
    )


class PathEnrollment(Base):

    __tablename__ = "path_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learning_path_id = Column(
        Integer, ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status = Column(String(20), default="not_started", nullable=False)
    progress_percentage = Column(Integer, default=0, nullable=False)

    completed_course_ids = Column(JSONB, default=list, nullable=False)

    enrolled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")
    learning_path = relationship("LearningPath", back_populates="enrollments")

    __table_args__ = (
        UniqueConstraint("user_id", "learning_path_id", name="uq_user_path"),
    )
