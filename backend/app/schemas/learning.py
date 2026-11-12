# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# ──────────────────────────────────────────────────────────────────────────────
# Validation-Sync Report
# Frontend files that consume this schema's constraints:
#   - frontend/src/pages/AdminCourseFormPage.tsx  (title maxLength, quiz_passing_threshold min/max)
# ──────────────────────────────────────────────────────────────────────────────
from datetime import datetime
from enum import StrEnum
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, computed_field, field_validator

from app.schemas._base import StrictInputSchema
from app.models.learning import CourseLifecycleStage


# Enums
class AccessLevel(StrEnum):
    patron = "patron"
    staff = "staff"
    admin = "admin"


class LessonType(StrEnum):
    article = "article"
    video = "video"
    quiz = "quiz"
    sandbox = "sandbox"
    lab = "lab"


class ProgressStatus(StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class FocusMode(StrEnum):
    balanced = "balanced"
    quick_scan = "quick_scan"
    deep_dive = "deep_dive"


class FontSize(StrEnum):
    small = "small"
    medium = "medium"
    large = "large"


class Theme(StrEnum):
    light = "light"
    dark = "dark"
    system = "system"


# Quiz Question schemas
class QuizOption(BaseModel):
    text: str
    is_correct: bool = False
    weight: int = 0


class QuizQuestionBase(BaseModel):
    question_text: str
    question_type: str = "multiple_choice"
    options: List[QuizOption] = []
    explanation: Optional[str] = None
    sort_order: int = 0


class QuizQuestionCreate(StrictInputSchema, QuizQuestionBase):
    lesson_id: int


class QuizQuestionResponse(QuizQuestionBase):
    id: int

    class Config:
        from_attributes = True


# ── Admin authoring (Wave 1 / W1-C) ──────────────────────────────────────
# Lesson-scoped POST/PUT/DELETE/reorder for QuizQuestion. Distinct from
# the existing QuizQuestionCreate (which takes lesson_id in the body) so
# we don't break LessonWithQuiz/QuizStartResponse callers downstream.

_ALLOWED_QUIZ_QUESTION_TYPES = {"multiple_choice", "true_false", "short_answer"}


class AdminQuizQuestionCreate(StrictInputSchema, QuizQuestionBase):
    @field_validator("question_type")
    @classmethod
    def _validate_question_type(cls, v: str) -> str:
        if v not in _ALLOWED_QUIZ_QUESTION_TYPES:
            allowed = ", ".join(sorted(_ALLOWED_QUIZ_QUESTION_TYPES))
            raise ValueError(f"question_type must be one of: {allowed}")
        return v


class AdminQuizQuestionUpdate(AdminQuizQuestionCreate):
    pass


class AdminQuizQuestionResponse(QuizQuestionBase):
    id: int
    lesson_id: int

    class Config:
        from_attributes = True


class QuizQuestionReorderItem(StrictInputSchema):
    question_id: int
    sort_order: int


# Lesson Variant schemas
class LessonVariantBase(BaseModel):
    variant_type: str  # audio, visual, text_only, interactive
    content: dict


class LessonVariantCreate(StrictInputSchema, LessonVariantBase):
    lesson_id: int


class LessonVariantResponse(LessonVariantBase):
    id: int

    class Config:
        from_attributes = True


# Lesson schemas
class LessonBase(BaseModel):
    title: str = Field(..., max_length=200)
    lesson_type: LessonType
    content: dict
    estimated_minutes: Optional[int] = None
    sensory_notes: Optional[str] = None
    sort_order: int = 0
    is_preview: bool = False
    facilitator_notes: Optional[str] = None
    visual_aid_url: Optional[str] = Field(None, max_length=500)
    audio_narration_url: Optional[str] = Field(None, max_length=500)
    xp_reward: int = Field(10, ge=0)


class LessonCreate(StrictInputSchema, LessonBase):
    # The URL path is authoritative (POST /modules/{module_id}/lessons);
    # accepted in the body only for back-compat and must match the path.
    module_id: Optional[int] = None


class LessonUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=200)
    lesson_type: Optional[LessonType] = None
    content: Optional[dict] = None
    estimated_minutes: Optional[int] = None
    sensory_notes: Optional[str] = None
    sort_order: Optional[int] = None
    facilitator_notes: Optional[str] = None
    summary: Optional[str] = None
    xp_reward: Optional[int] = None
    visual_aid_url: Optional[str] = Field(None, max_length=500)
    audio_narration_url: Optional[str] = Field(None, max_length=500)


class LessonProgressBrief(BaseModel):
    scroll_position: Optional[float] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class LessonResponse(LessonBase):
    id: int
    module_id: int
    summary: Optional[str] = None
    xp_reward: int = 10
    variants: List[LessonVariantResponse] = Field(default_factory=list)
    progress: Optional[LessonProgressBrief] = None

    class Config:
        from_attributes = True


class LessonWithQuiz(LessonResponse):
    quiz_questions: List[QuizQuestionResponse] = []


class LessonMediaUploadResponse(BaseModel):
    media_type: str
    url: str


class CourseMediaUploadResponse(BaseModel):
    media_type: str
    url: str


# Module schemas
class ModuleBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    sort_order: int = 0


class ModuleCreate(StrictInputSchema, ModuleBase):
    # The URL path is authoritative (POST /courses/{course_id}/modules);
    # accepted in the body only for back-compat and must match the path.
    course_id: Optional[int] = None


class ModuleUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    sort_order: Optional[int] = None


class ModuleResponse(ModuleBase):
    id: int
    course_id: int
    lessons: List[LessonResponse] = []

    class Config:
        from_attributes = True


# Course schemas
class CourseBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    access_level: AccessLevel = AccessLevel.patron
    difficulty: Optional[str] = Field(
        default="beginner", description="beginner, intermediate, or advanced"
    )
    estimated_minutes: Optional[int] = None
    sensory_warning: Optional[str] = None
    quiz_passing_threshold: Optional[int] = Field(
        default=70, ge=0, le=100, description="Minimum percentage to pass quizzes (0-100)"
    )
    prerequisite_course_ids: Optional[List[int]] = Field(
        default_factory=list,
        description="List of course IDs that must be completed before enrolling",
    )
    duration_days: Optional[int] = Field(
        default=None, description="Days to complete after enrollment; null means no deadline"
    )
    xp_reward: Optional[int] = Field(default=100, ge=0)

    @field_validator("prerequisite_course_ids", mode="before")
    @classmethod
    def coerce_prerequisite_ids(cls, v):
        if isinstance(v, dict):
            return list(v.values()) if v else []
        return v if v is not None else []


class CourseCreate(StrictInputSchema, CourseBase):
    pass


class CourseUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    access_level: Optional[AccessLevel] = None
    difficulty: Optional[str] = Field(None, description="beginner, intermediate, or advanced")
    estimated_minutes: Optional[int] = None
    sensory_warning: Optional[str] = None
    quiz_passing_threshold: Optional[int] = Field(
        None, ge=0, le=100, description="Minimum percentage to pass quizzes (0-100)"
    )
    prerequisite_course_ids: Optional[List[int]] = Field(
        None, description="List of course IDs that must be completed before enrolling"
    )
    duration_days: Optional[int] = Field(
        None, description="Days to complete after enrollment; null means no deadline"
    )
    xp_reward: Optional[int] = Field(None, ge=0)


class CoursePublishToggleRequest(StrictInputSchema):
    is_published: bool


class CourseCloneRequest(StrictInputSchema):
    new_title: str = Field(..., min_length=3, max_length=200)
    include_unpublished_lessons: bool = True


# ──────────────────────────────────────────────────────────────────────────────
# Bulk import (Wave 1 / W1-D)
# ──────────────────────────────────────────────────────────────────────────────
# Nested payload for POST /learning/admin/courses/import. Replaces the
# client-side orchestration in AdminCourseBulkImportPage (which fired 5+
# sequential POSTs and left orphans on mid-stream failure). LessonType is
# validated by Pydantic against the enum BEFORE any DB insert — `podcast`
# raises 422 cleanly rather than bubbling a 500 mid-transaction. Quiz
# questions reuse AdminQuizQuestionCreate (no lesson_id in body — set
# server-side from the freshly-created lesson).


class CourseImportLesson(StrictInputSchema, LessonBase):
    quiz_questions: List[AdminQuizQuestionCreate] = Field(default_factory=list)


class CourseImportModule(StrictInputSchema, ModuleBase):
    lessons: List[CourseImportLesson] = Field(default_factory=list)


class CourseImportPayload(StrictInputSchema):
    course: CourseCreate
    modules: List[CourseImportModule] = Field(default_factory=list)
    target_stage: Literal["draft"] = "draft"


# ──────────────────────────────────────────────────────────────────────────────
# Course ↔ Skill (Wave 5)
# ──────────────────────────────────────────────────────────────────────────────


class SkillBrief(BaseModel):
    id: int
    name: str
    level_taught: int = Field(..., ge=1, le=5)

    class Config:
        from_attributes = True


class CourseBrief(BaseModel):
    id: int
    title: str
    level_taught: int = Field(..., ge=1, le=5)

    class Config:
        from_attributes = True


class CourseResponse(CourseBase):
    id: int
    lifecycle_stage: CourseLifecycleStage = CourseLifecycleStage.DRAFT
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None
    # Wave 1 (course-authoring friction strip): user.id of the staff member
    # who created the course. NULL for historical rows pre-dating the column
    # and for any course whose creator user was later deleted (FK ON DELETE
    # SET NULL). Surfaced to admins so sweep emails know who to notify.
    created_by_id: Optional[int] = None
    # Wave 5: skills this course builds. Empty list when the course has no
    # tagged skills yet — the frontend chip strip simply renders nothing.
    skills: List[SkillBrief] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_published(self) -> bool:
        # PR-C4: the stored ``is_published`` column was dropped;
        # ``lifecycle_stage`` is the single source of truth. Kept as a
        # derived response field so existing API consumers (FE course
        # types, external readers) don't break. Reads the already-
        # materialized Pydantic field, NOT an ORM relationship — no
        # MissingGreenlet risk during serialization.
        return self.lifecycle_stage == CourseLifecycleStage.PUBLISHED

    class Config:
        from_attributes = True


class CourseWithModules(CourseResponse):
    modules: List[ModuleResponse] = []


# Bulk-import (W1-D) response models. Distinct from CourseWithModules:
# nests quiz_questions under each lesson so the FE bulk-import wizard can
# confirm the full tree round-tripped. CourseWithModules uses
# LessonResponse which strips quiz_questions to keep the patron course
# detail payload tight.
class CourseImportQuizQuestionResponse(BaseModel):
    id: int
    question_text: str
    question_type: str
    options: Optional[List[Any]] = None
    explanation: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True


class CourseImportLessonResponse(BaseModel):
    id: int
    module_id: int
    title: str
    lesson_type: str
    content: dict
    sort_order: int
    quiz_questions: List[CourseImportQuizQuestionResponse] = []

    class Config:
        from_attributes = True


class CourseImportModuleResponse(BaseModel):
    id: int
    course_id: int
    title: str
    description: Optional[str] = None
    sort_order: int
    lessons: List[CourseImportLessonResponse] = []

    class Config:
        from_attributes = True


class CourseImportResponse(CourseResponse):
    modules: List[CourseImportModuleResponse] = []


class CourseListItem(CourseResponse):
    module_count: int = 0
    lesson_count: int = 0


class CourseListItemAdmin(CourseListItem):
    enrollment_count: int = 0
    completion_count: int = 0
    in_progress_count: int = 0
    last_activity_at: Optional[datetime] = None

    # Lifecycle-stage admin fields. ``lifecycle_stage`` is the single
    # source of truth (PR-C4 dropped the legacy ``is_published`` column;
    # the parent ``CourseResponse`` exposes it as a computed field
    # derived from this). Redeclared here for the admin-default; the
    # query splat always supplies the real value.
    lifecycle_stage: CourseLifecycleStage = CourseLifecycleStage.DRAFT
    last_reviewed_at: Optional[datetime] = None
    review_due_at: Optional[datetime] = None
    last_reviewed_by: Optional["LastReviewedBy"] = None
    # Computed (not stored): true iff lifecycle_stage == published AND
    # review_due_at IS NOT NULL AND review_due_at < now(). Endpoint fills it
    # so the FE does not need to know the cadence rule.
    is_review_due: bool = False


class LastReviewedBy(BaseModel):
    id: int
    display_name: str


class CourseStageTransitionRequest(StrictInputSchema):
    to_stage: CourseLifecycleStage
    note: Optional[str] = Field(None, max_length=2000)
    confirm: bool = False


class ReviewQueueResponse(BaseModel):
    due_count: int
    soonest_due_at: Optional[datetime] = None
    courses: List[CourseListItemAdmin] = Field(default_factory=list)


class CourseStageTransitionHistoryItem(BaseModel):
    id: int
    from_stage: Optional[CourseLifecycleStage] = None
    to_stage: CourseLifecycleStage
    actor: Optional[LastReviewedBy] = None
    note: Optional[str] = None
    created_at: datetime


# Prerequisite schemas
class PrerequisiteCourseInfo(BaseModel):
    id: int
    title: str
    completed: bool = False

    class Config:
        from_attributes = True


class CoursePrerequisitesStatus(BaseModel):
    prerequisites: List[PrerequisiteCourseInfo] = []
    all_met: bool = True
    missing_count: int = 0


class CourseWithPrerequisites(CourseResponse):
    prerequisite_courses: List[PrerequisiteCourseInfo] = []


# Enrollment schemas
class EnrollmentCreate(StrictInputSchema):
    course_id: int


class EnrollmentResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    enrolled_at: datetime
    completed_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    # Wave 4: required vs recommended split + manager assign workflow.
    is_required: bool = False
    assigned_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class AssignCourseRequest(StrictInputSchema):
    user_id: int
    course_id: int
    due_at: Optional[datetime] = None
    is_required: bool = True


class EnrolledCourse(BaseModel):
    course: CourseResponse
    enrollment: EnrollmentResponse
    progress_percentage: float = 0.0
    completed_lessons: int = 0
    total_lessons: int = 0


# Lesson Progress schemas
class LessonProgressUpdate(StrictInputSchema):
    status: Optional[ProgressStatus] = None
    quiz_score: Optional[int] = None


class LessonProgressResponse(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    status: str
    quiz_score: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Quiz submission
class QuizAnswer(BaseModel):
    question_id: int
    selected_option_index: int


class QuizSubmission(BaseModel):
    answers: List[QuizAnswer]


class QuizResult(BaseModel):
    score: int
    total_questions: int
    percentage: float
    passed: bool
    feedback: List[dict]  # [{question_id, correct, explanation}]
    weighted_score: int = 0


# User Preferences schemas (ND accessibility)
class UserPreferencesBase(BaseModel):
    theme: Theme = Theme.system
    font_size: FontSize = FontSize.medium
    dyslexia_font: bool = False
    reduced_motion: bool = False
    high_contrast: bool = False
    focus_mode: FocusMode = FocusMode.balanced
    hide_streaks: bool = False
    hide_gamification: bool = False
    preferred_content_variant: str = "default"
    # Dashboard layout customization
    dashboard_layout: dict = Field(default_factory=dict)
    sidebar_collapsed: bool = False
    compact_mode: bool = False
    # Favorite actions and shortcuts
    favorite_actions: List[Any] = Field(default_factory=list)
    action_shortcuts: dict = Field(default_factory=dict)
    # Notification preferences
    notification_preferences: dict = Field(default_factory=dict)
    email_digests_enabled: bool = True
    digest_frequency: str = "daily"
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    # Workflow and productivity settings
    workflow_templates: List[Any] = Field(default_factory=list)
    default_list_view: str = "grid"
    auto_expand_details: bool = False
    keyboard_shortcuts_enabled: bool = True
    search_filters_saved: dict = Field(default_factory=dict)
    # Productivity settings
    focus_timer_duration: int = 25
    break_duration: int = 5
    enable_focus_timer: bool = False
    enable_break_reminders: bool = False
    ui_state: dict = Field(default_factory=dict)
    language_preference: str | None = None


class UserPreferencesUpdate(StrictInputSchema):
    theme: Optional[Theme] = None
    font_size: Optional[FontSize] = None
    dyslexia_font: Optional[bool] = None
    reduced_motion: Optional[bool] = None
    high_contrast: Optional[bool] = None
    focus_mode: Optional[FocusMode] = None
    hide_streaks: Optional[bool] = None
    hide_gamification: Optional[bool] = None
    preferred_content_variant: Optional[str] = None
    # Dashboard layout customization
    dashboard_layout: Optional[dict] = None
    sidebar_collapsed: Optional[bool] = None
    compact_mode: Optional[bool] = None
    # Favorite actions and shortcuts
    favorite_actions: Optional[List[Any]] = None
    action_shortcuts: Optional[dict] = None
    # Notification preferences
    notification_preferences: Optional[dict] = None
    email_digests_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    # Workflow and productivity settings
    workflow_templates: Optional[List[Any]] = None
    default_list_view: Optional[str] = None
    auto_expand_details: Optional[bool] = None
    keyboard_shortcuts_enabled: Optional[bool] = None
    search_filters_saved: Optional[dict] = None
    # Productivity settings
    focus_timer_duration: Optional[int] = None
    break_duration: Optional[int] = None
    enable_focus_timer: Optional[bool] = None
    enable_break_reminders: Optional[bool] = None
    ui_state: Optional[dict] = None
    language_preference: Optional[str] = None


class UserPreferencesResponse(UserPreferencesBase):
    id: int
    user_id: int
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# Certificate schemas
class CertificateResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    certificate_number: str
    issued_at: datetime
    course_title: Optional[str] = None

    class Config:
        from_attributes = True


class CertificateVerify(BaseModel):
    certificate_number: str
    user_name: str
    recipient_first_name: str = ""
    course_title: str
    issued_at: datetime
    is_valid: bool = True


# Quiz Attempt schemas
class QuizAttemptAnswer(BaseModel):
    question_id: int
    selected_option_index: int
    is_correct: bool = False


class QuizAttemptCreate(StrictInputSchema):
    lesson_id: int


class QuizAttemptSubmit(StrictInputSchema):
    answers: List[QuizAnswer]


class QuizAttemptResponse(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    score: int
    passed: bool
    answers: List[dict]
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QuizAttemptListItem(BaseModel):
    id: int
    score: int
    passed: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_questions: int = 0
    percentage: float = 0.0

    class Config:
        from_attributes = True


class QuizStartResponse(BaseModel):
    attempt_id: int
    questions: List[QuizQuestionResponse]
    total_questions: int
    passing_score: int = 70


class QuizSubmitResponse(BaseModel):
    attempt_id: int
    score: int
    total_questions: int
    percentage: float
    passed: bool
    feedback: List[dict]
    xp_earned: int = 0
    weighted_score: int = 0


# ============ EXTERNAL RESOURCES SCHEMAS ============


class ExternalResourceBase(BaseModel):
    title: str
    description: Optional[str] = None
    source_url: str
    thumbnail_url: Optional[str] = None
    provider: str = "data.org"
    resource_type: str
    difficulty: str = "beginner"
    topics: List[str] = []
    access_level: str = "patron"
    estimated_minutes: Optional[int] = None
    source_organization: Optional[str] = None


class ExternalResourceCreate(StrictInputSchema, ExternalResourceBase):
    pass


class ExternalResourceUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    difficulty: Optional[str] = None
    topics: Optional[List[str]] = None
    access_level: Optional[str] = None
    estimated_minutes: Optional[int] = None
    source_organization: Optional[str] = None
    is_featured: Optional[bool] = None


class ExternalResourceResponse(ExternalResourceBase):
    id: int
    is_featured: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ExternalResourceEnrollmentBase(BaseModel):
    completed: bool = False
    rating: Optional[int] = None
    notes: Optional[str] = None


class ExternalResourceEnrollmentCreate(StrictInputSchema, ExternalResourceEnrollmentBase):
    external_resource_id: int


class ExternalResourceEnrollmentUpdate(StrictInputSchema):
    clicked_at: Optional[datetime] = None
    completed: Optional[bool] = None
    completion_date: Optional[datetime] = None
    rating: Optional[int] = None
    notes: Optional[str] = None


class ExternalResourceEnrollmentResponse(BaseModel):
    id: int
    user_id: int
    external_resource_id: int
    clicked_at: Optional[datetime] = None
    completed: bool
    completion_date: Optional[datetime] = None
    rating: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ExternalResourceEnrollmentWithResource(BaseModel):
    enrollment: ExternalResourceEnrollmentResponse
    resource: ExternalResourceResponse

    class Config:
        from_attributes = True


# ============ ANALYTICS SCHEMAS ============


class WeeklyActivityDay(BaseModel):
    day: str  # Mon, Tue, Wed, Thu, Fri, Sat, Sun
    lessons: int = 0
    minutes: int = 0


class WeeklyActivityResponse(BaseModel):
    activity: List[WeeklyActivityDay]
    total_lessons: int = 0
    total_minutes: int = 0


class RecentActivityItem(BaseModel):
    lesson_id: int
    lesson_title: str
    course_id: int
    course_title: str
    completed_at: datetime
    xp_earned: int = 0
    estimated_minutes: Optional[int] = None


class StreakDay(BaseModel):
    date: str  # ISO date string
    had_activity: bool


class DifficultyDistribution(BaseModel):
    beginner: int = 0
    intermediate: int = 0
    advanced: int = 0


class ComprehensiveAnalyticsResponse(BaseModel):
    # Course stats
    total_courses_enrolled: int = 0
    courses_completed: int = 0
    courses_in_progress: int = 0

    # Lesson stats
    total_lessons: int = 0
    lessons_completed: int = 0
    lesson_completion_rate: float = 0.0

    # Time stats
    total_minutes_invested: int = 0
    total_content_minutes: int = 0

    # XP and Level
    total_xp: int = 0
    level: int = 1
    current_streak: int = 0
    longest_streak: int = 0

    # Difficulty distribution
    difficulty_distribution: DifficultyDistribution

    # Streak history (last 30 days)
    streak_history: List[StreakDay] = []

    # Recent activity feed
    recent_activity: List[RecentActivityItem] = []


# ============ COURSE FEEDBACK SCHEMAS ============


class CourseFeedbackType(StrEnum):
    helpful = "helpful"
    not_helpful = "not_helpful"
    content_error = "content_error"
    broken_link = "broken_link"
    accessibility = "accessibility"
    other = "other"
    review = "review"


class CourseFeedbackStatus(StrEnum):
    pending = "pending"
    reviewed = "reviewed"
    resolved = "resolved"
    dismissed = "dismissed"


class CourseFeedbackCreate(StrictInputSchema):
    course_id: int
    lesson_id: Optional[int] = None
    feedback_type: CourseFeedbackType
    comment: Optional[str] = Field(None, max_length=2000)


class CourseFeedbackResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    course_id: int
    lesson_id: Optional[int] = None
    feedback_type: str
    rating: Optional[float] = None
    comment: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseFeedbackAdminResponse(CourseFeedbackResponse):
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    course_title: Optional[str] = None
    lesson_title: Optional[str] = None
    reviewer_name: Optional[str] = None


class CourseFeedbackAdminUpdate(StrictInputSchema):
    status: Optional[CourseFeedbackStatus] = None
    admin_notes: Optional[str] = Field(None, max_length=2000)


class CourseFeedbackListResponse(BaseModel):
    items: List[CourseFeedbackAdminResponse]
    total: int
    page: int
    page_size: int
    pending_count: int = 0
    issue_count: int = 0


# Generic response schemas
class MessageResponse(BaseModel):
    message: str


class StatusResponse(BaseModel):
    status: str


class PositionSavedResponse(BaseModel):
    message: str
    position: float


class RecentCourseView(BaseModel):
    id: int
    title: str
    viewedAt: Optional[str] = None


class CourseProgressResponse(BaseModel):
    course_id: int
    course_title: str
    progress_percentage: float
    completed_lessons: int
    total_lessons: int
    in_progress_lessons: int
    next_lesson_id: Optional[int] = None
    next_lesson_title: Optional[str] = None


class LessonPositionUpdate(StrictInputSchema):
    position: float = 0


# ──────────────────────────────────────────────────────────────────────────────
# Manager / Team progress (Wave 2 — Team tab on /staff/training)
# ──────────────────────────────────────────────────────────────────────────────


class TeamMemberProgress(BaseModel):
    user_id: int
    name: str = Field(..., description="Display name; full_name if set, email fallback.")
    email: str
    courses_total: int = Field(..., ge=0)
    courses_completed: int = Field(..., ge=0)
    overdue_count: int = Field(..., ge=0)
    due_soon_count: int = Field(..., ge=0, description="Open enrollments due within 7 days.")
    completion_rate: float = Field(..., ge=0, le=100, description="Percentage 0-100.")


# Resolve forward refs (CourseListItemAdmin -> LastReviewedBy).
CourseListItemAdmin.model_rebuild()
