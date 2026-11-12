# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Index, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text

from ..core.database import Base
from ..core.enum_helpers import EnumColumn
from .mixins import TimestampMixin


class SurveyPlacement(StrEnum):
    ENTRY_PULSE = "entry_pulse"
    EMBEDDED_LESSON = "embedded_lesson"
    PRE_CERTIFICATE = "pre_certificate"
    LONGITUDINAL = "longitudinal"


class SurveyQuestionType(StrEnum):
    LIKERT = "likert"
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    FREE_TEXT = "free_text"
    SCENARIO = "scenario"


class SurveyResponseStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    EXPIRED = "expired"


class Survey(Base, TimestampMixin):
    __tablename__ = "engagement_surveys"
    __table_args__ = (
        Index("idx_engagement_survey_placement", "placement"),
        Index("idx_engagement_survey_course", "course_id"),
        Index("idx_engagement_survey_published", "is_published"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)

    placement = EnumColumn(SurveyPlacement, nullable=False)

    # Nullable so a single Entry Pulse can apply globally (course_id IS NULL)
    # while course-scoped pulses (e.g., Python prerequisite check) carry an FK.
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True
    )
    # SET NULL so editing a Lesson doesn't cascade-delete its embedded survey.
    lesson_id = Column(
        Integer, ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True
    )

    # Default policy: never block, always offer remediation. Civic-engagement
    # surveys flip blocks_progression=True per-survey.
    blocks_progression = Column(
        Boolean, nullable=False, server_default=text("false")
    )
    triggers_remediation = Column(
        Boolean, nullable=False, server_default=text("true")
    )

    # When true, response writes strip user_id (demographic-only collection).
    is_anonymous = Column(
        Boolean, nullable=False, server_default=text("false")
    )

    is_published = Column(
        Boolean, nullable=False, server_default=text("false")
    )

    estimated_minutes = Column(Integer)

    # LONGITUDINAL only: dispatch this many days after enrollment completion.
    trigger_offset_days = Column(Integer, nullable=True)

    # Transparency copy shown at enrollment when a longitudinal survey exists.
    consent_copy = Column(Text, nullable=True)

    # Soft delete (mirrors Course)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    questions = relationship(
        "SurveyQuestion",
        back_populates="survey",
        cascade="all, delete-orphan",
        order_by="SurveyQuestion.sort_order",
    )
    responses = relationship(
        "SurveyResponse",
        back_populates="survey",
        cascade="all, delete-orphan",
    )


class SurveyQuestion(Base, TimestampMixin):
    __tablename__ = "engagement_survey_questions"
    __table_args__ = (
        Index("idx_engagement_question_survey", "survey_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(
        Integer,
        ForeignKey("engagement_surveys.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_text = Column(Text, nullable=False)
    question_type = EnumColumn(SurveyQuestionType, nullable=False)

    # Shape varies by question_type:
    #   LIKERT: {"min": 1, "max": 10, "min_label": "...", "max_label": "..."}
    #   SINGLE_CHOICE / MULTI_CHOICE: [{"text": "...", "value": "...", "is_correct": bool|null}]
    #   SCENARIO: {"artifact": "...", "expected_flags": ["bias_a", "bias_b"]}
    #   FREE_TEXT: null (or {"max_length": int})
    options = Column(JSONB, nullable=True)

    is_optional = Column(Boolean, nullable=False, server_default=text("false"))
    # Demographic questions are reported in PII-scoped views and must always
    # be optional regardless of is_optional; the app layer enforces this.
    is_demographic = Column(
        Boolean, nullable=False, server_default=text("false")
    )
    sort_order = Column(Integer, nullable=False, server_default=text("0"))

    # See branching evaluator (PR 2) for rule schema. Example:
    #   [{"if": {"op": "gte", "value": 7},
    #     "then": {"action": "set_track", "track": "demystify"}}]
    branching_rules = Column(JSONB, nullable=True)

    # Relationships
    survey = relationship("Survey", back_populates="questions")


class SurveyResponse(Base, TimestampMixin):
    __tablename__ = "engagement_survey_responses"
    __table_args__ = (
        # Partial unique: one response per (user, survey) when user_id is set.
        # Anonymous responses (user_id IS NULL) are not deduplicated here.
        Index(
            "uq_engagement_user_survey_response",
            "user_id",
            "survey_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index("idx_engagement_response_survey", "survey_id"),
        Index("idx_engagement_response_user", "user_id"),
        Index("idx_engagement_response_status", "status"),
        Index(
            "idx_engagement_response_token",
            "delivery_token",
            unique=True,
            postgresql_where=text("delivery_token IS NOT NULL"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    # SET NULL preserves analytics rows if a user is deleted.
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    survey_id = Column(
        Integer,
        ForeignKey("engagement_surveys.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Denormalized for analytics queries that don't need to join through Survey.
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    enrollment_id = Column(
        Integer,
        ForeignKey("enrollments.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = EnumColumn(
        SurveyResponseStatus,
        nullable=False,
        server_default=SurveyResponseStatus.PENDING.value,
    )

    # Bias Challenge: count of correctly-flagged biases.
    score = Column(Integer, nullable=True)

    # Set by the branching evaluator; consumed by auto-enrollment hook.
    derived_track = Column(String(50), nullable=True)

    # [{"question_id": int, "value": any, "answered_at": iso8601}]
    answers = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Magic-link delivery for LONGITUDINAL surveys (no auth required to submit).
    # Single-use; consumer endpoint clears the token on submission.
    delivery_token = Column(String(64), nullable=True)
    delivery_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    survey = relationship("Survey", back_populates="responses")
    outcomes = relationship(
        "SurveyOutcome",
        back_populates="response",
        cascade="all, delete-orphan",
    )


class UserDemographics(Base, TimestampMixin):
    __tablename__ = "engagement_user_demographics"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_engagement_demographics_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    primary_language = Column(String(10), nullable=True)  # ISO 639-1
    is_native_english = Column(Boolean, nullable=True)
    age_range = Column(String(10), nullable=True)  # "18-24", "25-34", ...
    underserved_self_id = Column(Boolean, nullable=True)
    zip_code = Column(String(10), nullable=True)

    # Provenance: which Entry Pulse response produced these values.
    source_response_id = Column(
        Integer,
        ForeignKey("engagement_survey_responses.id", ondelete="SET NULL"),
        nullable=True,
    )


class SurveyOutcome(Base, TimestampMixin):
    __tablename__ = "engagement_survey_outcomes"
    __table_args__ = (
        Index("idx_engagement_outcome_response", "response_id"),
        Index("idx_engagement_outcome_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(
        Integer,
        ForeignKey("engagement_survey_responses.id", ondelete="CASCADE"),
        nullable=False,
    )

    # "civic_email_sent" | "task_force_link_sent" | "badge_awarded"
    # | "auto_enrolled" | "peer_tip_shown" | "remedial_lesson_queued"
    outcome_type = Column(String(50), nullable=False)

    # Email address, URL, badge slug, course_id, lesson_id — outcome-specific.
    target = Column(String(500), nullable=True)

    # "queued" | "sent" | "failed"
    status = Column(String(20), nullable=False, server_default="queued")

    # SET NULL: keep outcome history even if the notification row is purged.
    notification_id = Column(
        Integer,
        ForeignKey("notifications.id", ondelete="SET NULL"),
        nullable=True,
    )
    error = Column(Text, nullable=True)

    # Relationships
    response = relationship("SurveyResponse", back_populates="outcomes")
