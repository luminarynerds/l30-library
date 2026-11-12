# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum, StrEnum
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SQLEnum, ForeignKey,
    Integer, String, Text, Index, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class TutorStatus(StrEnum):
    PROSPECTIVE = "prospective"  # Initial inquiry
    IN_TRAINING = "in_training"  # Completing required training
    ACTIVE = "active"  # Actively tutoring
    ON_LEAVE = "on_leave"  # Temporary leave
    INACTIVE = "inactive"  # Not available
    RETIRED = "retired"  # No longer tutoring


class QualificationType(StrEnum):
    HIGH_SCHOOL_DIPLOMA = "high_school_diploma"
    ASSOCIATE_DEGREE = "associate_degree"
    BACHELOR_DEGREE = "bachelor_degree"
    MASTER_DEGREE = "master_degree"
    TEACHING_CERTIFICATE = "teaching_certificate"
    ESOL_CERTIFICATION = "esol_certification"  # English for Speakers of Other Languages
    LITERACY_SPECIALIST = "literacy_specialist"
    GED_INSTRUCTOR = "ged_instructor"
    SPECIAL_NEEDS_TRAINING = "special_needs_training"
    VOLUNTEER_TUTOR_TRAINING = "volunteer_tutor_training"


class TrainingTopic(StrEnum):
    ADULT_LEARNING_PRINCIPLES = "adult_learning_principles"
    PHONICS_INSTRUCTION = "phonics_instruction"
    COMPREHENSION_STRATEGIES = "comprehension_strategies"
    FLUENCY_BUILDING = "fluency_building"
    VOCABULARY_INSTRUCTION = "vocabulary_instruction"
    DIGITAL_LITERACY = "digital_literacy"
    SPECIAL_NEEDS_SUPPORT = "special_needs_support"
    CULTURAL_COMPETENCY = "cultural_competency"
    CLASSROOM_MANAGEMENT = "classroom_management"
    ASSESSMENT_BASICS = "assessment_basics"
    GED_CURRICULUM = "ged_curriculum"
    TECHNOLOGY_TOOLS = "technology_tools"
    CONFIDENTIALITY_COMPLIANCE = "confidentiality_compliance"


class TutorProfile(Base, TimestampMixin):
    __tablename__ = "literacy_tutors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # ==================== STATUS AND AVAILABILITY ====================
    status = Column(
        String(50),
        default=TutorStatus.PROSPECTIVE,
        nullable=False,
        index=True
    )
    is_active = Column(Boolean, default=True, nullable=False)

    # ==================== SPECIALIZATIONS ====================
    primary_focus = Column(String(255), nullable=True)  # Main teaching focus
    languages_spoken = Column(String(500), nullable=True)  # Comma-separated languages
    specializations = Column(Text, nullable=True)  # JSON or comma-separated
    can_teach_ged = Column(Boolean, default=False)
    can_teach_esol = Column(Boolean, default=False)
    can_work_with_special_needs = Column(Boolean, default=False)

    # ==================== EXPERIENCE ====================
    years_experience = Column(Integer, nullable=True)
    previous_teaching_experience = Column(Text, nullable=True)
    preferred_learner_level = Column(String(100), nullable=True)  # beginner, intermediate, advanced
    learner_age_preference = Column(String(100), nullable=True)  # youth, adult, all_ages

    # ==================== CERTIFICATION ====================
    primary_qualification = Column(
        String(50),
        nullable=True
    )
    is_certified = Column(Boolean, default=False)
    certification_expires_at = Column(DateTime(timezone=True), nullable=True)

    # ==================== LOCATION ====================
    preferred_location = Column(String(255), nullable=True)
    can_teach_remote = Column(Boolean, default=False)
    can_teach_in_person = Column(Boolean, default=True)

    # ==================== PERFORMANCE METRICS ====================
    total_learners_taught = Column(Integer, default=0, nullable=False)
    total_hours_taught = Column(Numeric(8, 2), default=0, nullable=False)
    average_learner_satisfaction = Column(Numeric(3, 2), nullable=True)  # 1-5 scale
    learner_success_rate = Column(Numeric(5, 2), nullable=True)  # Percentage

    # ==================== TRAINING STATUS ====================
    has_completed_mandatory_training = Column(Boolean, default=False)
    background_check_completed = Column(Boolean, default=False)
    background_check_date = Column(Date, nullable=True)
    confidentiality_agreement_signed = Column(Boolean, default=False)
    confidentiality_agreement_date = Column(Date, nullable=True)

    # ==================== NOTES ====================
    bio = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    user = relationship("User", backref="literacy_tutor_profile")
    qualifications = relationship(
        "LiteracyTutorQualification",
        back_populates="tutor",
        cascade="all, delete-orphan"
    )
    training_records = relationship(
        "LiteracyTutorTrainingRecord",
        back_populates="tutor",
        cascade="all, delete-orphan"
    )
    availability = relationship(
        "LiteracyTutorAvailability",
        back_populates="tutor",
        cascade="all, delete-orphan"
    )
    matches = relationship(
        "LiteracyTutorMatch",
        back_populates="tutor",
        cascade="all, delete-orphan",
        foreign_keys="LiteracyTutorMatch.tutor_id"
    )
    session_logs = relationship(
        "LiteracySessionLog",
        back_populates="tutor",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_literacy_tutors_status_active", status, is_active),
    )


class LiteracyTutorQualification(Base, TimestampMixin):
    __tablename__ = "literacy_tutor_qualifications"

    id = Column(Integer, primary_key=True, index=True)
    tutor_id = Column(Integer, ForeignKey("literacy_tutors.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== QUALIFICATION DETAILS ====================
    qualification_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    issuer = Column(String(255), nullable=True)  # Institution or organization
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)  # Null if no expiration
    credential_url = Column(Text, nullable=True)  # Link to verify credential
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    tutor = relationship("TutorProfile", back_populates="qualifications")

    __table_args__ = (
        Index("idx_literacy_qual_tutor_type", tutor_id, qualification_type),
    )


class LiteracyTutorTrainingRecord(Base, TimestampMixin):
    __tablename__ = "literacy_tutor_training_records"

    id = Column(Integer, primary_key=True, index=True)
    tutor_id = Column(Integer, ForeignKey("literacy_tutors.id", ondelete="CASCADE"), nullable=False, index=True)
    trainer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # ==================== TRAINING DETAILS ====================
    training_topic = Column(
        String(50),
        nullable=False,
        index=True
    )
    training_date = Column(DateTime(timezone=True), nullable=False)
    hours_completed = Column(Numeric(4, 1), nullable=False)

    # ==================== TRAINING CONTEXT ====================
    training_type = Column(String(50), nullable=True)  # "workshop", "online", "conference", "self-study"
    training_provider = Column(String(255), nullable=True)
    materials_url = Column(Text, nullable=True)  # Link to training materials
    certificate_url = Column(Text, nullable=True)  # Link to completion certificate

    # ==================== COMPLETION ====================
    is_completed = Column(Boolean, default=True, nullable=False)
    completion_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    tutor = relationship("TutorProfile", back_populates="training_records")
    trainer = relationship("User", backref="literacy_training_conducted")

    __table_args__ = (
        Index("idx_literacy_training_tutor_date", tutor_id, training_date),
        Index("idx_literacy_training_topic", training_topic),
    )


class LiteracyTutorAvailability(Base):
    __tablename__ = "literacy_tutor_availability"

    id = Column(Integer, primary_key=True, index=True)
    tutor_id = Column(Integer, ForeignKey("literacy_tutors.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== RECURRING SCHEDULE ====================
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(String(5), nullable=False)  # HH:MM format
    end_time = Column(String(5), nullable=False)  # HH:MM format
    location = Column(String(255), nullable=True)  # Physical location or "remote"

    # ==================== STATUS ====================
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    tutor = relationship("TutorProfile", back_populates="availability")

    __table_args__ = (
        Index("idx_literacy_availability_tutor_day", tutor_id, day_of_week),
    )
