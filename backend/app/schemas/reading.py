# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# ──────────────────────────────────────────────────────────────────────────────
# Validation-Sync Report
# Frontend files that consume this schema's constraints:
#   - frontend/src/components/AdminProgramForm.tsx      (name maxLength, age_group maxLength)
#   - frontend/src/components/ReadingLogEntryForm.tsx   (reading log entry fields)
#   - frontend/src/pages/ReadingMinutesPage.tsx         (minutes min/max)
# ──────────────────────────────────────────────────────────────────────────────

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema

from ..models.reading import ReadingLogFormat, ReadingLogStatus, ReadingProgramType


class ReadingLogCreate(StrictInputSchema):

    minutes: int = Field(..., ge=5, le=120, description="Reading minutes (5-120)")
    book_title: Optional[str] = Field(None, max_length=500)
    book_author: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=1000)
    reading_date: datetime


class ReadingLogResponse(BaseModel):

    id: int
    user_id: int
    minutes: int
    book_title: Optional[str]
    book_author: Optional[str]
    notes: Optional[str]
    status: ReadingLogStatus
    reading_date: datetime
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]
    patron_name: Optional[str] = None

    class Config:
        from_attributes = True


class ReadingLogReview(BaseModel):

    approved: bool
    rejection_reason: Optional[str] = Field(None, max_length=500)


class ReadingBalanceResponse(BaseModel):

    minutes_owed: int
    minutes_logged: int
    minutes_pending: int
    balance: int  # minutes still owed after approved logs
    pending_logs: int  # count of pending logs


# ============================================================================
# Reading Programs & Challenges
# ============================================================================


class ReadingProgramCreate(StrictInputSchema):

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    program_type: ReadingProgramType = ReadingProgramType.year_round
    age_group: Optional[str] = Field(None, max_length=50)
    target_age_min: Optional[int] = Field(None, ge=0, le=150)
    target_age_max: Optional[int] = Field(None, ge=0, le=150)
    start_date: date
    end_date: date
    reading_goal_type: Optional[str] = Field(
        None, max_length=20
    )  # "minutes", "books", "pages"
    reading_goal_value: Optional[int] = Field(None, ge=1)
    is_active: bool = True
    # School partnership fields
    is_school_program: bool = False
    partner_id: Optional[int] = None
    curriculum_alignment: Optional[str] = Field(None, max_length=100)
    grade_levels: List[str] = []
    reading_levels: List[str] = []


class ReadingProgramResponse(BaseModel):

    id: int
    name: str
    description: Optional[str]
    program_type: ReadingProgramType
    age_group: Optional[str]
    target_age_min: Optional[int]
    target_age_max: Optional[int]
    start_date: date
    end_date: date
    reading_goal_type: Optional[str]
    reading_goal_value: Optional[int]
    is_active: bool
    # School partnership fields
    is_school_program: bool
    partner_id: Optional[int]
    curriculum_alignment: Optional[str]
    grade_levels: List[str]
    reading_levels: List[str]
    created_at: datetime | None = None
    created_by_id: Optional[int]

    # Stats (calculated)
    registration_count: Optional[int] = 0
    total_minutes_read: Optional[int] = 0
    total_books_read: Optional[int] = 0


    @field_validator("grade_levels", "reading_levels", mode="before")
    @classmethod
    def coerce_dict_to_list(cls, v):
        if isinstance(v, dict):
            return list(v.values()) if v else []
        return v if v is not None else []

    class Config:
        from_attributes = True


class ReadingRegistrationCreate(StrictInputSchema):

    program_id: int
    goal_target: Optional[int] = Field(None, ge=1, description="Personal goal override")


class ReadingRegistrationResponse(BaseModel):

    id: int
    user_id: int
    program_id: int
    registered_at: datetime
    goal_target: Optional[int]

    # Progress (calculated)
    total_minutes: Optional[int] = 0
    total_books: Optional[int] = 0
    total_pages: Optional[int] = 0
    progress_percentage: Optional[float] = 0.0

    class Config:
        from_attributes = True


class ReadingLogEntryCreate(StrictInputSchema):

    registration_id: int
    books_read: int = Field(0, ge=0, le=100)
    minutes_read: int = Field(0, ge=0, le=120)  # Max 120 minutes per entry
    pages_read: int = Field(0, ge=0, le=10000)
    format: Optional[ReadingLogFormat] = ReadingLogFormat.print
    title: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=2000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    book_cover_url: Optional[str] = Field(None, max_length=500)

    # In Python 3.11+ str(EnumMember) returns the member name (e.g. "ReadingLogFormat.print")
    # rather than the value. The reading_log_entries.format column is plain
    # VARCHAR, so we serialize enums to their .value at dump time so the
    # right string lands in the DB.
    class Config:
        use_enum_values = True


class ReadingLogEntryResponse(BaseModel):

    id: int
    registration_id: int
    logged_at: datetime
    # Actual reading date for paper-log/redeemed entries (issue #828).
    # NULL for direct self-logs; clients should prefer this when displaying
    # "date read" and fall back to logged_at.date() when absent.
    entry_date: Optional[date] = None
    books_read: int
    minutes_read: int
    pages_read: int
    format: Optional[str] = None
    title: Optional[str]
    author: Optional[str]
    notes: Optional[str]
    rating: Optional[int]
    book_cover_url: Optional[str]

    class Config:
        from_attributes = True


class ReadingAchievementResponse(BaseModel):

    id: int
    user_id: int
    program_id: int
    badge_id: str
    badge_name: str
    badge_description: Optional[str]
    unlocked_at: datetime

    class Config:
        from_attributes = True


class ProgramProgressResponse(BaseModel):

    registration: ReadingRegistrationResponse
    program: ReadingProgramResponse
    log_entries: List[ReadingLogEntryResponse]
    achievements: List[ReadingAchievementResponse]

    # Summary stats
    total_minutes: int
    total_books: int
    total_pages: int
    days_participated: int
    completion_percentage: float


# ============================================================================
# Leaderboard Schemas
# ============================================================================


class LeaderboardEntry(BaseModel):

    rank: int
    user_id: int
    display_name: str  # Anonymized or display name
    total_books: int
    total_minutes: int
    total_pages: int
    achievement_count: int
    current_streak: int
    completion_percentage: float

    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):

    program_id: int
    program_name: str
    leaderboard_type: str  # "books", "minutes", "pages", "achievements"
    entries: List[LeaderboardEntry]
    total_participants: int
    user_rank: Optional[int] = None  # Current user's rank if authenticated


class BadgeProgressResponse(BaseModel):

    badge_id: str
    name: str
    description: str
    type: str
    threshold: int
    current: int
    progress_percentage: float
    earned: bool
    earned_at: Optional[datetime] = None


class NewAchievementResponse(BaseModel):

    achievement: ReadingAchievementResponse
    is_new: bool = True


class StreakInfoResponse(BaseModel):

    current_streak: int
    longest_streak: int
    last_log_date: Optional[date] = None
    streak_at_risk: bool = False  # True if user hasn't logged today


class LogEntryWithAchievementsResponse(BaseModel):

    log_entry: ReadingLogEntryResponse
    new_achievements: List[ReadingAchievementResponse]
    achievements_earned: int


# ============================================================================
# School Reading Partnership Schemas
# ============================================================================


class SharedReadingListItemCreate(StrictInputSchema):

    isbn: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=200)
    reading_level: Optional[str] = None
    description: Optional[str] = None
    book_cover_url: Optional[str] = None
    tags: List[str] = []
    librarian_notes: Optional[str] = None
    teacher_notes: Optional[str] = None


class SharedReadingListItemResponse(BaseModel):

    id: int
    reading_list_id: int
    isbn: Optional[str]
    title: str
    author: Optional[str]
    reading_level: Optional[str]
    description: Optional[str]
    book_cover_url: Optional[str]
    tags: List[str]
    librarian_notes: Optional[str]
    teacher_notes: Optional[str]
    suggested_by_id: Optional[int]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class SharedReadingListCreate(StrictInputSchema):

    name: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    partner_id: int
    program_id: Optional[int] = None
    curriculum_alignment: Optional[str] = Field(None, max_length=100)
    grade_levels: List[str] = []
    reading_levels: List[str] = []
    topics: List[str] = []
    is_active: bool = True


class SharedReadingListResponse(BaseModel):

    id: int
    name: str
    description: Optional[str]
    partner_id: int
    program_id: Optional[int]
    curriculum_alignment: Optional[str]
    grade_levels: List[str]
    reading_levels: List[str]
    topics: List[str]
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: Optional[int]
    items: List[SharedReadingListItemResponse] = []


    @field_validator("grade_levels", "reading_levels", mode="before")
    @classmethod
    def coerce_dict_to_list(cls, v):
        if isinstance(v, dict):
            return list(v.values()) if v else []
        return v if v is not None else []

    class Config:
        from_attributes = True


class SchoolBadgeCreate(StrictInputSchema):

    badge_name: str = Field(..., min_length=1, max_length=200)
    badge_description: Optional[str] = None
    badge_icon_url: Optional[str] = None
    threshold_type: str = Field(..., pattern="^(minutes|books|pages|achievement_count|streak)$")
    threshold_value: int = Field(..., ge=1)
    is_active: bool = True


class SchoolBadgeResponse(BaseModel):

    id: int
    partner_id: int
    badge_name: str
    badge_description: Optional[str]
    badge_icon_url: Optional[str]
    threshold_type: str
    threshold_value: int
    is_active: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class SchoolBadgeEarnedResponse(BaseModel):

    id: int
    badge_id: int
    user_id: int
    earned_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Family Engagement Schemas
# ============================================================================


class FamilyChallengeRegistrationCreate(StrictInputSchema):

    # Page shape (camelCase to match the existing fetch body).
    schoolId: Optional[int] = None
    familyName: Optional[str] = Field(default=None, max_length=200)
    studentAge: Optional[int] = Field(default=None, ge=0, le=120)

    # Linked-account shape.
    parent_user_id: Optional[int] = None
    child_user_id: Optional[int] = None
    parent_goal: Optional[int] = None
    child_goal: Optional[int] = None


class FamilyChallengeRegistrationResponse(BaseModel):

    id: int
    challenge_id: int
    parent_user_id: Optional[int] = None
    child_user_id: Optional[int] = None
    family_name: Optional[str] = None
    student_age: Optional[int] = None
    parent_progress: int
    child_progress: int
    combined_progress: int
    registered_at: datetime

    class Config:
        from_attributes = True


class FamilyReadingChallengeCreate(StrictInputSchema):

    program_id: int
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    challenge_type: str = Field(..., pattern="^(parent-child|sibling|family)$")
    goal_type: str = Field(..., pattern="^(minutes|books|pages)$")
    goal_value: int = Field(..., ge=1)
    start_date: date
    end_date: date
    parent_reward_description: Optional[str] = None
    child_reward_description: Optional[str] = None


class FamilyReadingChallengeResponse(BaseModel):

    id: int
    program_id: int
    name: str
    description: Optional[str]
    challenge_type: str
    goal_type: str
    goal_value: int
    start_date: date
    end_date: date
    parent_reward_description: Optional[str]
    child_reward_description: Optional[str]
    is_active: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class TakeHomeReadingBundleCreate(StrictInputSchema):

    partner_id: int
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    bundle_theme: Optional[str] = None
    book_count: int = Field(0, ge=0)
    grade_levels: List[str] = []
    reading_levels: List[str] = []
    copies_available: int = Field(1, ge=1)


class TakeHomeReadingBundleResponse(BaseModel):

    id: int
    partner_id: int
    name: str
    description: Optional[str]
    bundle_theme: Optional[str]
    book_count: int
    grade_levels: List[str]
    reading_levels: List[str]
    copies_available: int
    copies_distributed: int
    is_active: bool
    created_at: datetime | None = None
    @field_validator("grade_levels", "reading_levels", mode="before")
    @classmethod
    def coerce_dict_to_list(cls, v):
        if isinstance(v, dict):
            return list(v.values()) if v else []
        return v if v is not None else []

    class Config:
        from_attributes = True


# ============================================================================
# Professional Development Schemas
# ============================================================================


class TeacherTrainingModuleCreate(StrictInputSchema):

    partner_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    content_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    category: str = Field(..., pattern="^(reading-strategies|engagement|assessment|technology)$")
    level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")


class TeacherTrainingModuleResponse(BaseModel):

    id: int
    partner_id: int
    title: str
    description: Optional[str]
    content_url: Optional[str]
    duration_minutes: Optional[int]
    category: str
    level: str
    is_active: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class TrainingCompletionResponse(BaseModel):

    id: int
    module_id: int
    user_id: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    status: str
    quiz_score: Optional[int]
    passed_assessment: bool

    class Config:
        from_attributes = True


class ReadingAmbassadorCertificationCreate(StrictInputSchema):

    user_id: int
    partner_id: int
    certification_level: str = Field(..., pattern="^(bronze|silver|gold|platinum)$")
    certification_name: str


class ReadingAmbassadorCertificationResponse(BaseModel):

    id: int
    user_id: int
    partner_id: int
    certification_level: str
    certification_name: str
    required_modules_completed: int
    total_modules_required: int
    certified_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ReadingAmbassadorCertificationUpdate(StrictInputSchema):
    certification_level: Optional[str] = Field(None, pattern="^(bronze|silver|gold|platinum)$")
    certification_name: Optional[str] = None
    is_active: Optional[bool] = None


class ReadingAmbassadorCertificationListItem(BaseModel):
    id: int
    teacher_name: str
    school_name: str
    certification_level: str
    certification_name: str
    certification_number: Optional[str]
    date_earned: Optional[datetime]
    expires_at: Optional[datetime]
    required_modules_completed: int
    total_modules_required: int
    status: str  # "active", "expired", "pending"

    class Config:
        from_attributes = True


class ReadingAmbassadorCertificationListResponse(BaseModel):
    certifications: List[ReadingAmbassadorCertificationListItem]


class LibrarianConsultationSlotCreate(StrictInputSchema):

    partner_id: int
    librarian_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    consultation_type: str = Field(..., pattern="^(curriculum-planning|reading-strategies|assessment|program-design)$")
    scheduled_date: date
    start_time: str  # HH:MM format
    end_time: str
    duration_minutes: int = 30
    max_participants: int = 10


class LibrarianConsultationSlotResponse(BaseModel):

    id: int
    partner_id: int
    librarian_id: int
    title: str
    description: Optional[str]
    consultation_type: str
    scheduled_date: date
    start_time: str
    end_time: str
    duration_minutes: int
    max_participants: int
    current_participants: int
    is_booked: bool
    is_completed: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class EventReadingProgramCreditCreate(StrictInputSchema):

    program_id: int = Field(..., gt=0)
    minutes_credit: int = Field(0, ge=0, le=120)
    books_credit: int = Field(0, ge=0, le=10)
    pages_credit: int = Field(0, ge=0, le=1000)


class EventReadingProgramCreditResponse(BaseModel):

    id: int
    event_id: int
    program_id: int
    minutes_credit: int
    books_credit: int
    pages_credit: int
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# ============================================================================
# Library Visit Scheduling (teacher-initiated visit requests + scheduled visits)
# ============================================================================


def _to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class _CamelModel(BaseModel):

    model_config = {
        "alias_generator": _to_camel,
        "populate_by_name": True,
        "from_attributes": True,
    }


class LibraryVisitRequestCreate(StrictInputSchema, _CamelModel):

    school_id: int = Field(..., gt=0)
    requested_date: datetime
    number_of_students: int = Field(..., ge=1, le=500)
    grade_level: str = Field(..., min_length=1, max_length=100)
    teacher_name: str = Field(..., min_length=1, max_length=200)
    purpose: str = Field(..., min_length=1)


class LibraryVisitRequestResponse(_CamelModel):

    id: int
    school_id: int
    school_name: Optional[str] = None
    teacher_user_id: Optional[int] = None
    teacher_name: str
    requested_date: datetime
    scheduled_date: Optional[datetime] = None
    number_of_students: int
    grade_level: str
    purpose: str
    status: str
    approved_by_user_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    # Aliased for legacy frontend compatibility - the page reads "requestDate"
    request_date: Optional[datetime] = None


class LibraryVisitApprove(_CamelModel):

    scheduled_date: datetime


class LibraryVisitReject(_CamelModel):

    reason: str = Field(..., min_length=1, max_length=1000)




# ============================================================================
# Reading List Requests (teacher requests copies of a SharedReadingList)
# ============================================================================


def _rlr_to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class _ReadingListRequestCamelModel(StrictInputSchema):

    model_config = {
        "alias_generator": _rlr_to_camel,
        "populate_by_name": True,
        "from_attributes": True,
    }


class ReadingListRequestCreate(_ReadingListRequestCamelModel, StrictInputSchema):

    copies: int = Field(1, ge=1, le=200)
    notes: Optional[str] = Field(None, max_length=2000)


class ReadingListRequestResponse(_ReadingListRequestCamelModel):

    id: int
    school_id: int
    list_id: int
    list_title: str
    teacher_user_id: Optional[int] = None
    copies: int
    notes: Optional[str] = None
    status: str
    request_date: datetime
    fulfilled_by_user_id: Optional[int] = None
    fulfilled_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    updated_at: Optional[datetime] = None


class ReadingListRequestReject(_ReadingListRequestCamelModel):

    reason: str = Field(..., min_length=1, max_length=1000)


# ============================================================================
# Program Booklist (Recommended Reads per Program)
# ============================================================================


class BooklistCatalogItem(BaseModel):

    id: int
    title: str
    author: Optional[str] = None
    cover_url: Optional[str] = None
    status: str
    available_for_hold: bool

    class Config:
        from_attributes = True


class ProgramBooklistItemCreate(StrictInputSchema):

    catalog_item_id: int
    display_order: int = 0
    note: Optional[str] = Field(None, max_length=500)


class ProgramBooklistItemUpdate(StrictInputSchema):

    display_order: Optional[int] = None
    note: Optional[str] = Field(None, max_length=500)


class ProgramBooklistItemResponse(BaseModel):

    id: int
    program_id: int
    display_order: int
    note: Optional[str] = None
    added_at: datetime
    catalog_item: BooklistCatalogItem

    class Config:
        from_attributes = True


class ProgramBooklistResponse(BaseModel):

    items: List[ProgramBooklistItemResponse]


class ProgramBooklistReorderEntry(BaseModel):
    item_id: int
    display_order: int


class ProgramBooklistReorderRequest(StrictInputSchema):

    order: List[ProgramBooklistReorderEntry]


# ============================================================================
# Paper Log / Kiosk Claim Code
# ============================================================================


class PaperLogRedeemEntry(BaseModel):

    entry_date: date
    title: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=200)
    books_read: int = Field(0, ge=0)
    minutes_read: int = Field(0, ge=0, le=120)
    pages_read: int = Field(0, ge=0)
    notes: Optional[str] = Field(None, max_length=2000)


class PaperLogRedeemRequest(StrictInputSchema):

    code: str = Field(..., min_length=8, max_length=8)
    entries: List[PaperLogRedeemEntry] = Field(..., min_length=1, max_length=50)


class PaperLogRedeemResponse(BaseModel):

    registration_id: int
    program_id: int
    entries_created: int
    new_achievements: int
    total_books: int
    total_minutes: int
    total_pages: int
    goal_percent: float


class PaperLogCodeResponse(BaseModel):

    registration_id: int
    paper_log_code: str
    paper_log_code_generated_at: datetime
