# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text,
    Float, UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


# ============================================================================
# ENUMS
# ============================================================================

class LearningMilestoneType(StrEnum):
    COURSE_COMPLETION = "course_completion"
    MODULE_COMPLETION = "module_completion"
    SKILL_MASTERY = "skill_mastery"
    XP_THRESHOLD = "xp_threshold"
    STREAK_ACHIEVEMENT = "streak_achievement"
    ASSESSMENT_PASSED = "assessment_passed"
    CUSTOM = "custom"


class ObjectiveStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class CheckpointType(StrEnum):
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    PROJECT = "project"
    REFLECTION = "reflection"
    PEER_REVIEW = "peer_review"


class AssessmentType(StrEnum):
    QUIZ = "quiz"
    EXAM = "exam"
    PRACTICAL = "practical"
    PROJECT = "project"
    SELF_ASSESSMENT = "self_assessment"
    PEER_ASSESSMENT = "peer_assessment"


class QuestionType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    MATCHING = "matching"
    FILL_BLANK = "fill_blank"


class BadgeType(StrEnum):
    ACHIEVEMENT = "achievement"
    SKILL = "skill"
    MILESTONE = "milestone"
    SPECIAL = "special"
    STREAK = "streak"
    COMMUNITY = "community"


class BadgeRarity(StrEnum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class RecommendationType(StrEnum):
    COURSE = "course"
    LEARNING_PATH = "learning_path"
    SKILL = "skill"
    RESOURCE = "resource"


class RecommendationSource(StrEnum):
    COLLABORATIVE_FILTERING = "collaborative_filtering"
    CONTENT_BASED = "content_based"
    SKILL_GAP = "skill_gap"
    TRENDING = "trending"
    PERSONALIZED = "personalized"
    ADMIN_CURATED = "admin_curated"


class InterestLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class MetricType(StrEnum):
    ENROLLMENT = "enrollment"
    COMPLETION = "completion"
    ENGAGEMENT = "engagement"
    ASSESSMENT_SCORE = "assessment_score"
    TIME_SPENT = "time_spent"
    STREAK = "streak"
    BADGE_EARNED = "badge_earned"


class AnalyticsPeriod(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class EventType(StrEnum):
    LOGIN = "login"
    COURSE_VIEW = "course_view"
    LESSON_START = "lesson_start"
    LESSON_COMPLETE = "lesson_complete"
    QUIZ_ATTEMPT = "quiz_attempt"
    RESOURCE_DOWNLOAD = "resource_download"
    VIDEO_WATCH = "video_watch"
    DISCUSSION_POST = "discussion_post"
    SEARCH = "search"
    BADGE_EARNED = "badge_earned"


# ============================================================================
# PHASE 1: PROGRESS TRACKING
# ============================================================================

class Milestone(Base, TimestampMixin):
    __tablename__ = "learning_milestones"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    milestone_type = Column(String(50), nullable=False, index=True)

    # Criteria
    criteria = Column(JSONB, nullable=False)  # {"courses": [1,2,3], "min_xp": 1000}
    xp_reward = Column(Integer, default=0)
    badge_id = Column(Integer, ForeignKey("learning_badges.id", ondelete="SET NULL"), nullable=True)

    # Visibility
    is_active = Column(Boolean, default=True, index=True)
    is_hidden = Column(Boolean, default=False)  # Hidden until unlocked

    # Display
    icon_url = Column(String(500))
    sort_order = Column(Integer, default=0)

    # Relationships
    user_milestones = relationship(
        "UserMilestone",
        back_populates="milestone",
        cascade="all, delete-orphan"
    )
    learning_objectives = relationship(
        "LearningObjective",
        back_populates="milestone",
        cascade="all, delete-orphan"
    )


class UserMilestone(Base, TimestampMixin):
    __tablename__ = "learning_user_milestones"
    __table_args__ = (
        UniqueConstraint("user_id", "milestone_id", name="uq_user_milestone"),
        Index("idx_user_milestone_user", "user_id"),
        Index("idx_user_milestone_achieved", "achieved_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("learning_milestones.id", ondelete="CASCADE"), nullable=False)

    # Progress
    progress_percentage = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False, index=True)
    achieved_at = Column(DateTime(timezone=True))

    # Context
    context_data = Column(JSONB)  # Additional data about achievement

    # Relationships
    milestone = relationship("Milestone", back_populates="user_milestones")


class LearningObjective(Base, TimestampMixin):
    __tablename__ = "learning_objectives"
    __table_args__ = (
        Index("idx_objective_user_status", "user_id", "status"),
        Index("idx_objective_deadline", "target_completion_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("learning_milestones.id", ondelete="SET NULL"), nullable=True)

    # Objective details
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="not_started", nullable=False, index=True)

    # Timeline
    target_completion_date = Column(Date)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Progress
    progress_percentage = Column(Integer, default=0)
    progress_notes = Column(JSONB, default=list)  # [{date, note}]

    # Linked resources
    course_ids = Column(JSONB, default=list)
    skill_ids = Column(JSONB, default=list)

    # Relationships
    milestone = relationship("Milestone", back_populates="learning_objectives")


# ============================================================================
# PHASE 2: ENGAGEMENT FEATURES
# ============================================================================

class LearningStreak(Base, TimestampMixin):
    __tablename__ = "learning_streaks"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_streak"),
        Index("idx_streak_current", "current_streak"),
        Index("idx_streak_longest", "longest_streak"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Streak tracking
    current_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    last_activity_date = Column(Date, index=True)

    # Freeze mechanics (to prevent losing streaks)
    freeze_count = Column(Integer, default=0)
    max_freezes = Column(Integer, default=3)
    last_freeze_used = Column(Date)

    # History
    streak_history = Column(JSONB, default=list)  # [{start_date, end_date, length}]

    # Milestones
    total_active_days = Column(Integer, default=0)


class StudySession(Base, TimestampMixin):
    __tablename__ = "learning_study_sessions"
    __table_args__ = (
        Index("idx_session_user_date", "user_id", "session_date"),
        Index("idx_session_duration", "duration_minutes"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Session details
    session_date = Column(Date, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer, default=0)

    # Content
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    lesson_ids = Column(JSONB, default=list)

    # Metrics
    lessons_completed = Column(Integer, default=0)
    quizzes_taken = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)

    # Focus tracking
    focus_mode_enabled = Column(Boolean, default=False)
    break_count = Column(Integer, default=0)

    # Session data
    activities = Column(JSONB, default=list)  # [{timestamp, activity_type, details}]


class ProgressCheckpoint(Base, TimestampMixin):
    __tablename__ = "learning_progress_checkpoints"
    __table_args__ = (
        Index("idx_checkpoint_course", "course_id"),
        Index("idx_checkpoint_module", "module_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=True)

    # Checkpoint details
    title = Column(String(200), nullable=False)
    description = Column(Text)
    checkpoint_type = Column(String(50), nullable=False)

    # Ordering
    sort_order = Column(Integer, default=0)

    # Requirements
    is_required = Column(Boolean, default=True)
    passing_criteria = Column(JSONB)  # {"min_score": 70, "required_tasks": []}
    xp_reward = Column(Integer, default=0)

    # Content
    content_url = Column(String(500))
    instructions = Column(Text)

    # Relationships
    user_checkpoints = relationship(
        "UserCheckpoint",
        back_populates="checkpoint",
        cascade="all, delete-orphan"
    )


class UserCheckpoint(Base, TimestampMixin):
    __tablename__ = "learning_user_checkpoints"
    __table_args__ = (
        UniqueConstraint("user_id", "checkpoint_id", name="uq_user_checkpoint"),
        Index("idx_user_checkpoint_status", "user_id", "is_completed"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    checkpoint_id = Column(Integer, ForeignKey("learning_progress_checkpoints.id", ondelete="CASCADE"), nullable=False)

    # Progress
    is_completed = Column(Boolean, default=False, index=True)
    completed_at = Column(DateTime(timezone=True))

    # Submission
    submission_data = Column(JSONB)  # User's work/answers
    score = Column(Float)
    feedback = Column(Text)

    # Attempts
    attempt_count = Column(Integer, default=0)
    best_score = Column(Float)

    # Relationships
    checkpoint = relationship("ProgressCheckpoint", back_populates="user_checkpoints")


# ============================================================================
# PHASE 3: ASSESSMENTS & RECOGNITION
# ============================================================================

class Assessment(Base, TimestampMixin):
    __tablename__ = "learning_assessments"
    __table_args__ = (
        Index("idx_assessment_course", "course_id"),
        Index("idx_assessment_type", "assessment_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=True)

    # Assessment details
    title = Column(String(200), nullable=False)
    description = Column(Text)
    assessment_type = Column(String(50), nullable=False)

    # Configuration
    time_limit_minutes = Column(Integer)
    passing_score = Column(Float, default=70.0)
    max_attempts = Column(Integer, default=3)
    randomize_questions = Column(Boolean, default=False)
    show_correct_answers = Column(Boolean, default=True)

    # Availability
    is_published = Column(Boolean, default=False, index=True)
    available_from = Column(DateTime(timezone=True))
    available_until = Column(DateTime(timezone=True))

    # Rewards
    xp_reward = Column(Integer, default=0)
    certificate_eligible = Column(Boolean, default=False)

    # Instructions
    instructions = Column(Text)
    resources_allowed = Column(JSONB, default=list)  # ["notes", "calculator"]

    # Relationships
    questions = relationship(
        "AssessmentQuestion",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.sort_order"
    )
    attempts = relationship(
        "AssessmentAttempt",
        back_populates="assessment",
        cascade="all, delete-orphan"
    )


class AssessmentQuestion(Base, TimestampMixin):
    __tablename__ = "learning_assessment_questions"
    __table_args__ = (
        Index("idx_question_assessment", "assessment_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("learning_assessments.id", ondelete="CASCADE"), nullable=False)

    # Question content
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)

    # Options and answers
    options = Column(JSONB)  # [{"text": "...", "is_correct": true}]
    correct_answer = Column(JSONB)  # For non-multiple choice

    # Metadata
    points = Column(Float, default=1.0)
    difficulty = Column(String(20))
    explanation = Column(Text)
    hint = Column(Text)

    # Ordering
    sort_order = Column(Integer, default=0)

    # Media
    image_url = Column(String(500))
    audio_url = Column(String(500))

    # Relationships
    assessment = relationship("Assessment", back_populates="questions")


class AssessmentAttempt(Base, TimestampMixin):
    __tablename__ = "learning_assessment_attempts"
    __table_args__ = (
        Index("idx_attempt_user_assessment", "user_id", "assessment_id"),
        Index("idx_attempt_score", "score"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("learning_assessments.id", ondelete="CASCADE"), nullable=False)

    # Attempt details
    attempt_number = Column(Integer, default=1)
    started_at = Column(DateTime(timezone=True), nullable=False)
    submitted_at = Column(DateTime(timezone=True))
    time_taken_minutes = Column(Integer)

    # Results
    score = Column(Float)
    max_score = Column(Float)
    percentage = Column(Float)
    passed = Column(Boolean, default=False, index=True)

    # Answers
    answers = Column(JSONB, default=list)  # [{question_id, answer, is_correct, points}]

    # Status
    is_completed = Column(Boolean, default=False, index=True)
    is_graded = Column(Boolean, default=False)

    # Feedback
    feedback = Column(Text)
    graded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    graded_at = Column(DateTime(timezone=True))

    # Relationships
    assessment = relationship("Assessment", back_populates="attempts")


class Badge(Base, TimestampMixin):
    __tablename__ = "learning_badges"
    __table_args__ = (
        Index("idx_badge_type", "badge_type"),
        Index("idx_badge_rarity", "rarity"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Badge details
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    badge_type = Column(String(50), nullable=False)
    rarity = Column(String(20), default="common")

    # Display
    icon_url = Column(String(500))
    color_hex = Column(String(7))  # #RRGGBB

    # Criteria
    criteria = Column(JSONB, nullable=False)  # Award conditions
    xp_value = Column(Integer, default=0)

    # Availability
    is_active = Column(Boolean, default=True, index=True)
    is_secret = Column(Boolean, default=False)  # Hidden until earned

    # Limits
    max_awards = Column(Integer)  # Null = unlimited
    current_awards = Column(Integer, default=0)

    # Category
    category = Column(String(100))

    # Relationships
    user_badges = relationship(
        "UserBadge",
        back_populates="badge",
        cascade="all, delete-orphan"
    )


class UserBadge(Base, TimestampMixin):
    __tablename__ = "learning_user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", "earned_at", name="uq_user_badge_earned"),
        Index("idx_user_badge_user", "user_id"),
        Index("idx_user_badge_earned", "earned_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    badge_id = Column(Integer, ForeignKey("learning_badges.id", ondelete="CASCADE"), nullable=False)

    # Award details
    earned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Context
    earned_for = Column(Text)  # Description of what earned the badge
    context_data = Column(JSONB)  # Additional context

    # Display
    is_showcased = Column(Boolean, default=False)  # Display on profile
    showcase_order = Column(Integer)

    # Relationships
    badge = relationship("Badge", back_populates="user_badges")


# ============================================================================
# PHASE 4: PERSONALIZATION & RECOMMENDATIONS
# ============================================================================

class CourseRecommendation(Base, TimestampMixin):
    __tablename__ = "learning_course_recommendations"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", "recommendation_source", name="uq_course_recommendation"),
        Index("idx_recommendation_user_score", "user_id", "relevance_score"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)

    # Recommendation details
    recommendation_source = Column(String(50), nullable=False)
    relevance_score = Column(Float, default=0.0)  # 0-1 score

    # Reasoning
    reason = Column(Text)
    factors = Column(JSONB)  # {"skills": [...], "interests": [...]}

    # Status
    is_viewed = Column(Boolean, default=False, index=True)
    viewed_at = Column(DateTime(timezone=True))
    is_dismissed = Column(Boolean, default=False)
    dismissed_at = Column(DateTime(timezone=True))

    # Engagement
    is_enrolled = Column(Boolean, default=False)
    enrolled_at = Column(DateTime(timezone=True))

    # Validity
    expires_at = Column(DateTime(timezone=True))


class LearningPathRecommendation(Base, TimestampMixin):
    __tablename__ = "learning_path_recommendations"
    __table_args__ = (
        UniqueConstraint("user_id", "learning_path_id", name="uq_path_recommendation"),
        Index("idx_path_rec_user_score", "user_id", "relevance_score"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    learning_path_id = Column(Integer, ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False)

    # Recommendation details
    recommendation_source = Column(String(50), nullable=False)
    relevance_score = Column(Float, default=0.0)

    # Reasoning
    reason = Column(Text)
    skill_gaps = Column(JSONB)  # Skills this path would fill

    # Status
    is_viewed = Column(Boolean, default=False)
    viewed_at = Column(DateTime(timezone=True))
    is_dismissed = Column(Boolean, default=False)

    # Engagement
    is_enrolled = Column(Boolean, default=False)
    enrolled_at = Column(DateTime(timezone=True))


class UserInterest(Base, TimestampMixin):
    __tablename__ = "learning_user_interests"
    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_user_interest"),
        Index("idx_interest_user_level", "user_id", "interest_level"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Interest details
    topic = Column(String(100), nullable=False)
    interest_level = Column(String(20), default="medium")

    # Source
    source = Column(String(50))  # "explicit", "inferred", "behavioral"
    confidence_score = Column(Float, default=0.5)  # 0-1

    # Metadata
    related_skills = Column(JSONB, default=list)
    related_courses = Column(JSONB, default=list)

    # Activity
    last_engaged_at = Column(DateTime(timezone=True))
    engagement_count = Column(Integer, default=0)


# ============================================================================
# PHASE 5: ANALYTICS & REPORTING
# ============================================================================

class PlatformMetric(Base, TimestampMixin):
    __tablename__ = "learning_platform_metrics"
    __table_args__ = (
        UniqueConstraint("metric_date", "metric_type", name="uq_platform_metric"),
        Index("idx_metric_date_type", "metric_date", "metric_type"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Metric details
    metric_date = Column(Date, nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)

    # Values
    value = Column(Float, nullable=False)
    previous_value = Column(Float)
    change_percentage = Column(Float)

    # Breakdown
    breakdown = Column(JSONB)  # Detailed breakdown by category

    # Context
    period = Column(String(20), default="daily")
    notes = Column(Text)


class CourseAnalytics(Base, TimestampMixin):
    __tablename__ = "learning_course_analytics"
    __table_args__ = (
        UniqueConstraint("course_id", "analytics_date", name="uq_course_analytics"),
        Index("idx_course_analytics_date", "course_id", "analytics_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    analytics_date = Column(Date, nullable=False)

    # Enrollment metrics
    total_enrollments = Column(Integer, default=0)
    new_enrollments = Column(Integer, default=0)
    active_enrollments = Column(Integer, default=0)

    # Completion metrics
    completions = Column(Integer, default=0)
    completion_rate = Column(Float, default=0.0)
    average_completion_days = Column(Float)

    # Engagement metrics
    total_time_minutes = Column(Integer, default=0)
    average_time_per_user = Column(Float)
    lessons_completed = Column(Integer, default=0)

    # Assessment metrics
    quizzes_taken = Column(Integer, default=0)
    average_quiz_score = Column(Float)
    pass_rate = Column(Float)

    # Ratings
    average_rating = Column(Float)
    total_ratings = Column(Integer, default=0)

    # Detailed breakdown
    module_stats = Column(JSONB)  # Per-module statistics
    user_segments = Column(JSONB)  # Stats by user segment


class UserLearningReport(Base, TimestampMixin):
    __tablename__ = "learning_user_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "report_date", "report_type", name="uq_user_report"),
        Index("idx_report_user_date", "user_id", "report_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Report details
    report_date = Column(Date, nullable=False)
    report_type = Column(String(20), default="weekly")  # daily, weekly, monthly

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Summary metrics
    total_time_minutes = Column(Integer, default=0)
    lessons_completed = Column(Integer, default=0)
    courses_completed = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)
    badges_earned = Column(Integer, default=0)

    # Streak
    current_streak = Column(Integer, default=0)
    active_days = Column(Integer, default=0)

    # Progress
    courses_in_progress = Column(Integer, default=0)
    completion_rate = Column(Float)

    # Assessments
    assessments_taken = Column(Integer, default=0)
    average_assessment_score = Column(Float)

    # Detailed data
    top_courses = Column(JSONB)  # Most engaged courses
    top_skills = Column(JSONB)  # Skills worked on
    achievements = Column(JSONB)  # Highlights of the period
    recommendations = Column(JSONB)  # Personalized recommendations

    # Goals
    goals_completed = Column(Integer, default=0)
    goals_in_progress = Column(Integer, default=0)


class EngagementEvent(Base):
    __tablename__ = "learning_engagement_events"
    __table_args__ = (
        Index("idx_event_user_date", "user_id", "event_date"),
        Index("idx_event_type_date", "event_type", "event_date"),
        Index("idx_event_course", "course_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    event_date = Column(Date, nullable=False, index=True)
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Context
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True)

    # Event data
    event_data = Column(JSONB)  # Additional event-specific data

    # Session
    session_id = Column(String(100), index=True)

    # Metrics
    duration_seconds = Column(Integer)
    value = Column(Float)  # Generic value field for metrics

    # Device/context
    device_type = Column(String(50))
    browser = Column(String(100))
    ip_address = Column(String(50))


# ============================================================================
# RELATIONSHIPS & INDEXES
# ============================================================================

# Additional helpful indexes for performance
Index("idx_streak_user_active", LearningStreak.user_id, LearningStreak.current_streak)
Index("idx_session_user_recent", StudySession.user_id, StudySession.started_at.desc())
Index("idx_badge_user_showcased", UserBadge.user_id, UserBadge.is_showcased)
Index("idx_recommendation_active", CourseRecommendation.user_id, CourseRecommendation.is_viewed, CourseRecommendation.is_dismissed)
