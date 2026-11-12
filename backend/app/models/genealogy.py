# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from enum import StrEnum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ResearchTopics(PyEnum):
    GETTING_STARTED = "getting-started"
    VITAL_RECORDS = "vital-records"
    CENSUS = "census"
    IMMIGRATION = "immigration"
    DNA = "dna"
    LOCAL_RESOURCES = "local-resources"
    USING_DATABASES = "using-databases"
    ROADBLOCK = "roadblock"
    OTHER = "other"


class CourseLevel(PyEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class GenealogyInquiry(Base):
    __tablename__ = "genealogy_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Contact info (stored in case user is not registered)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    preferred_contact = Column(String(20), default="email")  # email, phone, either

    # Research details
    research_topic = Column(Enum(ResearchTopics, values_callable=lambda x: [m.value for m in x]), nullable=False, index=True)
    description = Column(Text, nullable=False)
    current_challenges = Column(Text, nullable=True)

    # Status and tracking
    status = Column(String(50), default="new", index=True)  # new, in_progress, responded, closed
    response_from_genealogist = Column(Text, nullable=True)
    responded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    responded_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    genealogist = relationship("User", foreign_keys=[responded_by])

    def __repr__(self) -> str:
        return f"<GenealogyInquiry(id={self.id}, email={self.email}, topic={self.research_topic})>"


class GenealogyTrainingCourse(Base):
    __tablename__ = "genealogy_training_courses"

    id = Column(Integer, primary_key=True, index=True)

    # Course info
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    difficulty_level = Column(Enum(CourseLevel, values_callable=lambda x: [m.value for m in x]), nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False)  # e.g., 30, 45, 60

    # Schedule
    next_session_day = Column(String(50), nullable=True)  # e.g., "Saturdays", "Tuesdays"
    next_session_time = Column(String(50), nullable=True)  # e.g., "10 AM", "2 PM"
    location = Column(String(255), nullable=True)

    # Content
    modules = Column(String(500), nullable=True)  # JSON-encoded list of modules
    prerequisites = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_virtual = Column(Boolean, default=False)
    max_enrollment = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    enrollments = relationship("CourseEnrollment", back_populates="course")

    def __repr__(self) -> str:
        return f"<GenealogyTrainingCourse(id={self.id}, title={self.title}, level={self.difficulty_level})>"


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', name='unique_enrollment'),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("genealogy_training_courses.id", ondelete="CASCADE"), nullable=False, index=True)

    # Enrollment status
    status = Column(String(50), default="registered", index=True)  # registered, attended, completed, cancelled
    completion_percentage = Column(Integer, default=0)

    # Timestamps
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    attended_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")
    course = relationship("GenealogyTrainingCourse", back_populates="enrollments")

    def __repr__(self) -> str:
        return f"<CourseEnrollment(user_id={self.user_id}, course_id={self.course_id})>"


class CommunityArchiveSubmission(Base):
    __tablename__ = "community_archive_submissions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Submitter info
    submitter_name = Column(String(255), nullable=False)
    submitter_email = Column(String(255), nullable=False, index=True)
    submitter_phone = Column(String(20), nullable=True)
    submitter_relationship = Column(String(100), nullable=True)  # e.g., "family member", "local historian"

    # Material info
    material_type = Column(String(100), nullable=False, index=True)  # photo, document, newspaper, map, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    date_or_period = Column(String(100), nullable=True)  # e.g., "1950s", "January 15, 1987"
    location = Column(String(255), nullable=True)
    people_involved = Column(Text, nullable=True)  # comma-separated or JSON
    historical_significance = Column(Text, nullable=True)

    # Access control
    is_public = Column(Boolean, default=True, index=True)
    access_level = Column(String(50), default="public", index=True)  # public, restricted, private
    restriction_notes = Column(Text, nullable=True)

    # Rights and permissions
    submitter_owns_material = Column(Boolean, nullable=False)
    has_permission = Column(Boolean, nullable=True)
    permission_details = Column(Text, nullable=True)
    creative_commons_license = Column(String(100), default="CC-BY-4.0", nullable=True)

    # Files/URLs
    file_url = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True)  # jpg, pdf, mp3, etc.
    file_size = Column(Integer, nullable=True)  # in bytes

    # Status
    status = Column(String(50), default="submitted", index=True)  # submitted, under_review, approved, rejected, published
    review_notes = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    published_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self) -> str:
        return f"<CommunityArchiveSubmission(id={self.id}, title={self.title}, status={self.status})>"
