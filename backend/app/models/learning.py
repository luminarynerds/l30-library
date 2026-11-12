# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from app.models.mixins import TimestampMixin
from sqlalchemy import (Boolean, Column, DateTime, Enum as SQLEnum, Float,
                        ForeignKey, Integer, Index, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text

from ..core.database import Base


class AccessLevel(StrEnum):
    PATRON = "patron"
    STAFF = "staff"
    ADMIN = "admin"


class LessonType(StrEnum):
    ARTICLE = "article"
    VIDEO = "video"
    QUIZ = "quiz"
    SANDBOX = "sandbox"
    LAB = "lab"


class ProgressStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class FocusMode(StrEnum):
    BALANCED = "balanced"
    QUICK_SCAN = "quick_scan"
    DEEP_DIVE = "deep_dive"


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LearningResourceType(StrEnum):
    PDF = "pdf"
    CHECKLIST = "checklist"
    SCRIPT = "script"
    VIDEO = "video"
    AUDIO = "audio"
    LINK = "link"


class CourseLifecycleStage(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    thumbnail_url = Column(String(500))
    access_level = Column(String(20), default="patron", nullable=False)
    estimated_minutes = Column(Integer)
    difficulty = Column(
        String(20), default="beginner"
    )  # beginner, intermediate, advanced
    sensory_warning = Column(Text)
    quiz_passing_threshold = Column(Integer, default=70)  # Minimum percentage to pass quizzes (default 70%)
    xp_reward = Column(Integer, default=100)  # XP earned for completing course
    prerequisite_course_ids = Column(JSONB, default=list)  # Array of course IDs that must be completed first
    duration_days = Column(Integer, nullable=True)  # Days a learner has to complete after enrollment; NULL = no deadline

    # Lifecycle stage — the single source of truth for course
    # visibility (PR-C4 dropped the legacy ``is_published`` column).
    # Patron-facing queries filter on ``lifecycle_stage == 'published'``.
    lifecycle_stage = Column(
        SQLEnum(
            CourseLifecycleStage,
            name="course_lifecycle_stage",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        server_default="draft",
        index=True,
    )
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_reviewed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_due_at = Column(DateTime(timezone=True), nullable=True)

    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Authoring audit: who created this course. NULL for historical
    # rows pre-dating Wave 1 of the course-authoring friction strip;
    # populated on POST /courses and POST /admin/courses/{id}/clone.
    # ON DELETE SET NULL so user removal doesn't cascade-drop courses.
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    modules = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Module.sort_order",
    )
    enrollments = relationship(
        "Enrollment", back_populates="course", cascade="all, delete-orphan"
    )
    certificates = relationship(
        "Certificate", back_populates="course", cascade="all, delete-orphan"
    )
    last_reviewed_by = relationship("User", foreign_keys=[last_reviewed_by_id])

    # Wave 5: course ↔ skill association objects.
    # `cascade="all, delete-orphan"` is OK per CLAUDE.md — `CourseSkill` rows
    # have no independent meaning without their parent course.
    course_skills = relationship(
        "CourseSkill",
        back_populates="course",
        cascade="all, delete-orphan",
    )

    @property
    def skills(self):
        out = []
        course_skills = self.__dict__.get("course_skills")
        if not course_skills:
            return out
        for cs in course_skills:
            skill = cs.__dict__.get("skill") if cs is not None else None
            if skill is None:
                continue
            out.append(
                {
                    "id": skill.id,
                    "name": skill.name,
                    "level_taught": cs.level_taught,
                }
            )
        return out


class CourseStageTransition(Base):

    __tablename__ = "course_stage_transitions"

    id = Column(Integer, primary_key=True)
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_stage = Column(
        SQLEnum(
            CourseLifecycleStage,
            name="course_lifecycle_stage",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
    )
    to_stage = Column(
        SQLEnum(
            CourseLifecycleStage,
            name="course_lifecycle_stage",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    actor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    course = relationship("Course")
    actor = relationship("User", foreign_keys=[actor_id])


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)
    description = Column(Text)
    sort_order = Column(Integer, default=0)

    # Relationships
    course = relationship("Course", back_populates="modules")
    lessons = relationship(
        "Lesson",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Lesson.sort_order",
    )


class Lesson(Base, TimestampMixin):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(
        Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)
    lesson_type = Column(String(20), nullable=False)
    content = Column(JSONB, nullable=False)
    estimated_minutes = Column(Integer)
    sensory_notes = Column(Text)
    xp_reward = Column(Integer, default=10)  # XP earned for completing lesson
    sort_order = Column(Integer, default=0)
    # Free-preview lessons are readable by anonymous/unenrolled patrons (see
    # the GET /lessons/{id} access gate). Typically the first lesson of a course.
    is_preview = Column(Boolean, default=False, nullable=False, server_default=text("false"))

    # New accessibility and media fields
    summary = Column(Text)
    visual_aid_url = Column(String(500))
    audio_narration_url = Column(String(500))
    preferred_break_interval = Column(Integer)  # minutes between suggested breaks
    facilitator_notes = Column(Text)  # Staff/admin-only notes for facilitating this lesson
    # created_at / updated_at provided by TimestampMixin.
    # Required by the W1-B stub-lesson nightly sweep (lesson_sweep_service)
    # to identify lessons that have been empty for >24h.

    # Relationships
    module = relationship("Module", back_populates="lessons")
    variants = relationship(
        "LessonVariant", back_populates="lesson", cascade="all, delete-orphan"
    )
    quiz_questions = relationship(
        "QuizQuestion",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="QuizQuestion.sort_order",
    )
    progress_records = relationship(
        "LessonProgress", back_populates="lesson", cascade="all, delete-orphan"
    )
    resources = relationship(
        "LessonResource",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="LessonResource.sort_order",
    )


class LessonResource(Base):
    __tablename__ = "lesson_resources"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)
    description = Column(Text)
    resource_type = Column(
        String(20), nullable=False
    )  # pdf, checklist, script, video, audio, link
    url = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0)

    # Relationships
    lesson = relationship("Lesson", back_populates="resources")


class LessonVariant(Base):
    __tablename__ = "lesson_variants"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_type = Column(
        String(20), nullable=False
    )  # audio, visual, text_only, summary, interactive
    content = Column(JSONB, nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="variants")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), default="multiple_choice")
    options = Column(JSONB)  # [{"text": "...", "is_correct": true/false}]
    explanation = Column(Text)
    sort_order = Column(Integer, default=0)

    # Relationships
    lesson = relationship("Lesson", back_populates="quiz_questions")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_enrollment"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    due_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Computed at enroll time from course.duration_days
    # Wave 4: required vs recommended split + manager assignment workflow.
    # `is_required` defaults to False at the DB level so existing rows are
    # treated as recommended (self-enrolled) without a backfill. Indexed
    # because the staff trainings table renders Required and Recommended
    # sections with separate filters.
    is_required = Column(
        Boolean, nullable=False, server_default=text("false"), index=True
    )
    # SET NULL so deleting the assigning manager doesn't cascade-delete
    # enrollments — the trail just loses its attribution.
    assigned_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    course = relationship("Course", back_populates="enrollments")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id = Column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status = Column(String(20), default="not_started")
    quiz_score = Column(Integer)
    variants_viewed = Column(JSONB, default=list)  # track which variants user explored
    scroll_position = Column(Float)  # percentage (0-100) for resume functionality
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    lesson = relationship("Lesson", back_populates="progress_records")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Display preferences
    theme = Column(String(20), default="system")  # light, dark, system
    font_size = Column(String(10), default="medium")  # small, medium, large

    # Neurodivergent-first accessibility
    dyslexia_font = Column(Boolean, default=False)
    reduced_motion = Column(Boolean, default=False)
    high_contrast = Column(Boolean, default=False)
    focus_mode = Column(
        String(20), default="balanced"
    )  # balanced, quick_scan, deep_dive
    hide_streaks = Column(Boolean, default=False)
    hide_gamification = Column(
        Boolean, default=False
    )  # anxiety-free mode - hide XP, badges, leaderboards
    preferred_content_variant = Column(String(20), default="default")

    # Personalization features
    # Dashboard layout customization
    dashboard_layout = Column(JSONB, default=dict)  # custom dashboard widget configuration
    sidebar_collapsed = Column(Boolean, default=False)
    compact_mode = Column(Boolean, default=False)

    # Favorite actions and shortcuts
    favorite_actions = Column(JSONB, default=list)  # list of pinned favorite action IDs
    action_shortcuts = Column(JSONB, default=dict)  # custom keyboard shortcut mappings

    # Notification preferences
    notification_preferences = Column(JSONB, default=dict)  # notification type preferences
    email_digests_enabled = Column(Boolean, default=True)
    digest_frequency = Column(String(20), default="daily")  # daily, weekly, monthly
    quiet_hours_start = Column(String(5))  # HH:MM format
    quiet_hours_end = Column(String(5))  # HH:MM format

    # Workflow and productivity settings
    workflow_templates = Column(JSONB, default=list)  # saved workflow templates
    default_list_view = Column(String(20), default="grid")  # grid, list, card
    auto_expand_details = Column(Boolean, default=False)
    keyboard_shortcuts_enabled = Column(Boolean, default=True)
    search_filters_saved = Column(JSONB, default=dict)  # saved filter configurations

    # Productivity settings
    focus_timer_duration = Column(Integer, default=25)  # minutes
    break_duration = Column(Integer, default=5)  # minutes
    enable_focus_timer = Column(Boolean, default=False)
    enable_break_reminders = Column(Boolean, default=False)

    # Generic UI state (catch-all for client-side preferences synced to DB).
    # Unadorned '{}' rather than '{}'::jsonb: Postgres coerces the untyped
    # literal to the column type in a DEFAULT clause (verified: identical
    # stored value/type), and the explicit ::jsonb cast is invalid DDL
    # syntax outside Postgres, which broke Base.metadata.create_all against
    # SQLite in app/tests fixtures that build a from-scratch schema.
    ui_state = Column(JSONB, default=dict, server_default=text("'{}'"))
    language_preference = Column(String(10), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_certificate"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    certificate_number = Column(String(50), nullable=False, unique=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    course = relationship("Course", back_populates="certificates")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id = Column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score = Column(Integer, default=0)  # Number of correct answers
    passed = Column(Boolean, default=False)
    answers = Column(
        JSONB, default=list
    )  # [{question_id, selected_option_index, is_correct}]
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    lesson = relationship("Lesson", backref="quiz_attempts")


# ============ SKILLS MODELS ============


class SkillCategory(StrEnum):
    LIBRARY_SERVICES = "library_services"
    TECHNOLOGY = "technology"
    CUSTOMER_SERVICE = "customer_service"
    COLLECTIONS = "collections"
    PROGRAMMING = "programming"
    ADMINISTRATION = "administration"


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    category = Column(String(50), nullable=False, index=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    user_skills = relationship(
        "UserSkill", back_populates="skill", cascade="all, delete-orphan"
    )
    role_requirements = relationship(
        "RoleRequiredSkill", back_populates="skill", cascade="all, delete-orphan"
    )
    questions = relationship(
        "SkillAssessmentQuestion", back_populates="skill", cascade="all, delete-orphan"
    )
    # Wave 5: reverse side of the course ↔ skill association.
    course_skills = relationship(
        "CourseSkill",
        back_populates="skill",
        cascade="all, delete-orphan",
    )


class CourseSkill(Base):

    __tablename__ = "course_skills"
    __table_args__ = (
        UniqueConstraint("course_id", "skill_id", name="uq_course_skill"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id = Column(
        Integer,
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 1-5 scale, mirroring `UserSkill.current_level` and
    # `RoleRequiredSkill.required_level`. server_default keeps inserts
    # cheap when the level is unknown.
    level_taught = Column(Integer, nullable=False, server_default="1")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    course = relationship("Course", back_populates="course_skills")
    skill = relationship("Skill", back_populates="course_skills")


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id = Column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    current_level = Column(Integer, default=1)  # 1-5 proficiency
    assessed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    skill = relationship("Skill", back_populates="user_skills")


class RoleRequiredSkill(Base):
    __tablename__ = "role_required_skills"
    __table_args__ = (UniqueConstraint("role", "skill_id", name="uq_role_skill"),)

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), nullable=False, index=True)  # STAFF, ADMIN
    skill_id = Column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required_level = Column(Integer, default=3)  # 1-5 proficiency required
    is_mandatory = Column(Boolean, default=True)

    # Relationships
    skill = relationship("Skill", back_populates="role_requirements")


class SkillAssessmentQuestion(Base):
    __tablename__ = "skill_assessment_questions"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), default="multiple_choice")
    options = Column(JSONB)  # [{"text": "...", "is_correct": true/false}]
    difficulty_level = Column(Integer, default=1)  # 1-5 maps to skill levels
    explanation = Column(Text)
    sort_order = Column(Integer, default=0)

    # Relationships
    skill = relationship("Skill", back_populates="questions")


# ============ EXTERNAL RESOURCES MODELS ============


class ExternalResource(Base):
    __tablename__ = "external_resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    source_url = Column(String(500), nullable=False, unique=True, index=True)
    thumbnail_url = Column(String(500))
    provider = Column(String(100), default="data.org", index=True)
    resource_type = Column(String(50))  # course, toolkit, article, playbook
    difficulty = Column(String(20), default="beginner")
    topics = Column(JSONB, default=list)  # ['AI', 'Ethics', 'Governance']
    access_level = Column(String(20), default="patron")
    estimated_minutes = Column(Integer)
    is_featured = Column(Boolean, default=False, index=True)
    source_organization = Column(String(200))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    enrollments = relationship(
        "ExternalResourceEnrollment",
        back_populates="resource",
        cascade="all, delete-orphan"
    )


class ExternalResourceEnrollment(Base):
    __tablename__ = "external_resource_enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "external_resource_id", name="uq_external_resource_enrollment"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_resource_id = Column(
        Integer, ForeignKey("external_resources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clicked_at = Column(DateTime(timezone=True))
    completed = Column(Boolean, default=False)
    completion_date = Column(DateTime(timezone=True))
    rating = Column(Integer)  # 1-5 stars
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    resource = relationship("ExternalResource", back_populates="enrollments")


class CourseView(Base):
    __tablename__ = "course_views"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_course_view"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    viewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    course = relationship("Course")


class LessonBookmark(Base):
    __tablename__ = "lesson_bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_lesson_bookmark"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id = Column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    lesson = relationship("Lesson")


class LearningFeedbackType(StrEnum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    CONTENT_ERROR = "content_error"
    BROKEN_LINK = "broken_link"
    ACCESSIBILITY = "accessibility"
    OTHER = "other"


class LearningFeedbackStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class CourseFeedback(Base, TimestampMixin):
    __tablename__ = "course_feedback"
    __table_args__ = (
        Index("idx_course_feedback_course", "course_id"),
        Index("idx_course_feedback_lesson", "lesson_id"),
        Index("idx_course_feedback_user", "user_id"),
        Index("idx_course_feedback_status", "status"),
        Index("idx_course_feedback_type", "feedback_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id = Column(
        Integer, ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True
    )

    # Feedback details
    feedback_type = Column(String(30), nullable=False)
    rating = Column(Float)  # optional numeric rating
    comment = Column(Text)

    # Admin moderation
    status = Column(String(20), default="pending", nullable=False)
    admin_notes = Column(Text)
    reviewed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])
    course = relationship("Course")
    lesson = relationship("Lesson")
