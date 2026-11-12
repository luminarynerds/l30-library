# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date
from enum import StrEnum

from app.models.mixins import TimestampMixin
from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ReadingLogStatus(StrEnum):
    pending = "pending"  # Awaiting staff approval
    approved = "approved"  # Approved and applied to balance
    rejected = "rejected"  # Rejected by staff


class ReadingLog(Base, TimestampMixin):
    __tablename__ = "reading_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Reading details
    minutes = Column(Integer, nullable=False)
    book_title = Column(String(500), nullable=True)  # Optional - what they read
    book_author = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)  # Brief description or parent note

    # Status
    status = Column(
        SQLEnum(
            ReadingLogStatus,
            name="readinglogstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ReadingLogStatus.pending,
        nullable=False,
    )

    # Approval tracking
    reviewed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Timestamps
    reading_date = Column(DateTime(timezone=True), nullable=False)  # When they did the reading

    __table_args__ = (
        CheckConstraint(
            "minutes > 0",
            name="ck_reading_log_minutes_positive",
        ),
        # Composite index for user reading log queries filtered by status
        Index("ix_reading_logs_user_status", "user_id", "status"),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="reading_logs")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])


class ReadingStats(Base):
    __tablename__ = "reading_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Streak tracking (based on submissions, not approvals)
    current_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    last_log_date = Column(Date, nullable=True)  # Date of last submission

    # Progress stats
    total_approved_minutes = Column(Integer, default=0, nullable=False)
    total_submissions = Column(Integer, default=0, nullable=False)
    unique_books = Column(Integer, default=0, nullable=False)
    notes_written = Column(Integer, default=0, nullable=False)

    # XP (1 per approved minute)
    xp = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def level(self) -> int:
        return (self.xp // 100) + 1

    @property
    def xp_to_next_level(self) -> int:
        return 100 - (self.xp % 100)


class ReadingExport(Base):
    __tablename__ = "reading_exports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Verification
    verification_code = Column(String(20), unique=True, nullable=False, index=True)

    # Report params
    date_from = Column(Date, nullable=True)
    date_to = Column(Date, nullable=True)
    teacher_name = Column(String(200), nullable=True)
    school_name = Column(String(200), nullable=True)

    # Stats snapshot at time of export
    total_minutes = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    books_read = Column(
        Text, nullable=True
    )  # JSON array of book titles, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiry

    # Relationships
    user = relationship("User")


# ============================================================================
# Reading Programs & Challenges (Summer Reading, Year-Round Programs)
# ============================================================================


class ReadingProgramType(StrEnum):
    summer = "summer"  # Summer reading challenge
    winter = "winter"  # Winter reading challenge
    year_round = "year_round"  # Ongoing reading program
    special = "special"  # Special event-based program


class ReadingProgram(Base, TimestampMixin):
    __tablename__ = "reading_programs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Program type
    program_type = Column(
        SQLEnum(
            ReadingProgramType,
            name="readingprogramtype",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ReadingProgramType.year_round,
        nullable=False,
    )

    # Target audience
    age_group = Column(String(50), nullable=True)  # e.g. "Children", "Teens", "Adults", "All Ages"
    target_age_min = Column(Integer, nullable=True)
    target_age_max = Column(Integer, nullable=True)

    # Program dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Reading goal configuration
    reading_goal_type = Column(String(20), nullable=True)  # "minutes", "books", "pages"
    reading_goal_value = Column(Integer, nullable=True)  # Target value

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # School partnership fields
    is_school_program = Column(
        Boolean, default=False, nullable=False
    )  # Is this a school-specific program?
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="SET NULL"), nullable=True, index=True
    )  # Specific school if applicable
    curriculum_alignment = Column(
        String(100), nullable=True
    )  # e.g., "Language Arts", "STEM", "Social Studies"
    grade_levels = Column(
        JSON, default=list, nullable=False
    )  # e.g., ["3", "4", "5"] for school programs
    reading_levels = Column(
        JSON, default=list, nullable=False
    )  # e.g., ["2.5", "3.0", "3.5"] for grade-level reading levels

    # Metadata, server_default=func.now())
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    registrations = relationship(
        "ReadingRegistration", back_populates="program", cascade="all, delete-orphan"
    )
    created_by = relationship("User", foreign_keys=[created_by_id])
    partner = relationship("OutreachPartner", foreign_keys=[partner_id], backref="reading_programs")


class ReadingRegistration(Base):
    __tablename__ = "reading_registrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id = Column(
        Integer,
        ForeignKey("reading_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Registration details
    registered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    goal_target = Column(Integer, nullable=True)  # Personal goal (can override program default)

    # Paper log / kiosk claim code. Single-use 8-char code printed on
    # patron paper logs; staff or kiosk redemption credits log entries.
    # See spec 2026-05-18-l30-programs-printable-paper-log.
    paper_log_code = Column(String(8), unique=True, nullable=True, index=True)
    paper_log_code_generated_at = Column(DateTime(timezone=True), nullable=True)
    paper_log_code_redeemed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="reading_program_registrations")
    program = relationship("ReadingProgram", back_populates="registrations")
    log_entries = relationship(
        "ReadingLogEntry", back_populates="registration", cascade="all, delete-orphan"
    )


class ReadingLogFormat(StrEnum):
    print = "print"
    large_print = "large_print"
    ebook = "ebook"
    audiobook = "audiobook"
    braille = "braille"


class ReadingLogEntry(Base):
    __tablename__ = "reading_log_entries"

    id = Column(Integer, primary_key=True, index=True)
    registration_id = Column(
        Integer,
        ForeignKey("reading_registrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Reading activity
    logged_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Paper-log/redeemed entries carry the actual reading date the patron
    # wrote (issue #828). For direct self-logs this is left NULL and the
    # logged_at timestamp is authoritative.
    entry_date = Column(Date, nullable=True)
    books_read = Column(Integer, default=0, nullable=False)
    minutes_read = Column(Integer, default=0, nullable=False)
    pages_read = Column(Integer, default=0, nullable=False)
    format = Column(String(20), nullable=True, server_default=ReadingLogFormat.print.value)

    # Book details (optional)
    title = Column(String(500), nullable=True)
    author = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 star rating
    book_cover_url = Column(String(500), nullable=True)

    # Origin tracking. Most entries are direct patron self-logs (source=NULL).
    # Entries auto-created by event attendance carry source='event_attendance'
    # and source_event_id; the unique constraint below makes the auto-credit
    # path idempotent so re-check-in doesn't double-credit.
    source = Column(String(50), nullable=True, index=True)
    source_event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    registration = relationship("ReadingRegistration", back_populates="log_entries")

    __table_args__ = (
        # Idempotency for event-attendance credit. PostgreSQL treats NULL
        # source_event_id as distinct, so the constraint only constrains
        # rows that actually have an event source.
        UniqueConstraint(
            "registration_id",
            "source_event_id",
            name="uq_reading_log_entry_registration_source_event",
        ),
    )


class EventReadingProgramCredit(Base, TimestampMixin):
    __tablename__ = "event_reading_program_credits"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = Column(
        Integer,
        ForeignKey("reading_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    minutes_credit = Column(Integer, nullable=False, default=0, server_default="0")
    books_credit = Column(Integer, nullable=False, default=0, server_default="0")
    pages_credit = Column(Integer, nullable=False, default=0, server_default="0")

    event = relationship("Event")
    program = relationship("ReadingProgram")

    __table_args__ = (
        UniqueConstraint("event_id", "program_id", name="uq_event_program_credit_pair"),
    )


class ReadingAchievement(Base):
    __tablename__ = "reading_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id = Column(
        Integer,
        ForeignKey("reading_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Badge details
    badge_id = Column(String(100), nullable=False)  # e.g. "first-book", "bookworm", "speed-reader"
    badge_name = Column(String(200), nullable=False)  # Display name
    badge_description = Column(Text, nullable=True)  # What this badge is for

    # Unlock timestamp
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="reading_achievements")
    program = relationship("ReadingProgram", backref="achievements")


class SharedReadingList(Base):
    __tablename__ = "shared_reading_lists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # School/program linkage
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id = Column(
        Integer, ForeignKey("reading_programs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Metadata
    curriculum_alignment = Column(
        String(100), nullable=True
    )  # e.g., "Language Arts", "Unit 3: Westward Expansion"
    grade_levels = Column(JSON, default=list)  # Grades applicable
    reading_levels = Column(JSON, default=list)  # Lexile/level ranges
    topics = Column(JSON, default=list)  # Subjects/themes

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Audit
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    partner = relationship("OutreachPartner", backref="shared_reading_lists")
    program = relationship("ReadingProgram")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    items = relationship(
        "SharedReadingListItem", back_populates="reading_list", cascade="all, delete-orphan"
    )


class SharedReadingListItem(Base):
    __tablename__ = "shared_reading_list_items"

    id = Column(Integer, primary_key=True, index=True)
    reading_list_id = Column(
        Integer,
        ForeignKey("shared_reading_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Book reference
    isbn = Column(String(20), nullable=True)
    title = Column(String(500), nullable=False)
    author = Column(String(200), nullable=True)
    reading_level = Column(String(20), nullable=True)  # Lexile, grade level, etc.

    # Metadata
    description = Column(Text, nullable=True)
    book_cover_url = Column(String(500), nullable=True)
    tags = Column(JSON, default=list)  # Custom tags

    # School context
    librarian_notes = Column(Text, nullable=True)  # Notes from librarian
    teacher_notes = Column(Text, nullable=True)  # Notes from teacher
    suggested_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    reading_list = relationship("SharedReadingList", back_populates="items")
    suggested_by = relationship("User", foreign_keys=[suggested_by_id])


class ReadingListRequest(Base):
    __tablename__ = "reading_list_requests"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reading_list_id = Column(
        Integer,
        ForeignKey("shared_reading_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    copies = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)
    # pending | approved | fulfilled | rejected | cancelled
    status = Column(String(20), nullable=False, default="pending", index=True)
    fulfilled_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    school = relationship("OutreachPartner", backref="reading_list_requests")
    reading_list = relationship("SharedReadingList", backref="requests")
    teacher = relationship("User", foreign_keys=[teacher_user_id])
    fulfiller = relationship("User", foreign_keys=[fulfilled_by_user_id])

    __table_args__ = (
        Index("ix_reading_list_requests_school_status", "school_id", "status"),
        Index("ix_reading_list_requests_teacher_school", "teacher_user_id", "school_id"),
    )


class SchoolBadge(Base):
    __tablename__ = "school_badges"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Badge details
    badge_name = Column(String(200), nullable=False)  # e.g., "Lincoln School Champion Reader"
    badge_description = Column(Text, nullable=True)
    badge_icon_url = Column(String(500), nullable=True)

    # Badge criteria
    threshold_type = Column(
        String(20), nullable=False
    )  # "minutes", "books", "pages", "achievement_count", "streak"
    threshold_value = Column(Integer, nullable=False)  # e.g., 50 books

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    partner = relationship("OutreachPartner", backref="school_badges")
    earned = relationship("SchoolBadgeEarned", back_populates="badge", cascade="all, delete-orphan")


class SchoolBadgeEarned(Base):
    __tablename__ = "school_badges_earned"

    id = Column(Integer, primary_key=True, index=True)
    badge_id = Column(
        Integer, ForeignKey("school_badges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Timestamp
    earned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    badge = relationship("SchoolBadge", back_populates="earned")
    user = relationship("User", backref="school_badges_earned")


# ============================================================================
# Family Engagement Models
# ============================================================================


class FamilyReadingChallenge(Base):
    __tablename__ = "family_reading_challenges"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(
        Integer, ForeignKey("reading_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Challenge details
    name = Column(String(200), nullable=False)  # e.g., "Parents & Kids Read Together"
    description = Column(Text, nullable=True)
    challenge_type = Column(String(50), nullable=False)  # "parent-child", "sibling", "family"

    # Goals
    goal_type = Column(String(20), nullable=False)  # "minutes", "books", "pages"
    goal_value = Column(Integer, nullable=False)  # Target value

    # Dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Incentives
    parent_reward_description = Column(Text, nullable=True)
    child_reward_description = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    program = relationship("ReadingProgram")
    registrations = relationship(
        "FamilyChallengeRegistration", back_populates="challenge", cascade="all, delete-orphan"
    )


class FamilyChallengeRegistration(Base):
    __tablename__ = "family_challenge_registrations"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(
        Integer,
        ForeignKey("family_reading_challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Optional user FKs.  Pilot teachers register families by free-text name +
    # student age rather than picking from user accounts, so these are nullable.
    parent_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    child_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Informal identifiers used by FamilyReadingChallengesPage.  No FK -- just
    # the teacher-entered family name and student age at registration time.
    family_name = Column(String(200), nullable=True)
    student_age = Column(Integer, nullable=True)

    # Goals
    parent_goal = Column(Integer, nullable=True)  # Personal goal for parent
    child_goal = Column(Integer, nullable=True)  # Personal goal for child

    # Progress
    parent_progress = Column(Integer, default=0, nullable=False)
    child_progress = Column(Integer, default=0, nullable=False)
    combined_progress = Column(Integer, default=0, nullable=False)

    # Registration date
    registered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    challenge = relationship("FamilyReadingChallenge", back_populates="registrations")
    parent = relationship(
        "User", foreign_keys=[parent_user_id], backref="family_challenges_as_parent"
    )
    child = relationship("User", foreign_keys=[child_user_id], backref="family_challenges_as_child")


class TakeHomeReadingBundle(Base):
    __tablename__ = "take_home_reading_bundles"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Bundle details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    bundle_theme = Column(String(100), nullable=True)  # e.g., "Bedtime Stories", "Adventure Tales"

    # Contents
    book_count = Column(Integer, default=0, nullable=False)
    grade_levels = Column(JSON, default=list)
    reading_levels = Column(JSON, default=list)

    # Distribution
    copies_available = Column(Integer, default=0, nullable=False)
    copies_distributed = Column(Integer, default=0, nullable=False)
    last_distributed_date = Column(Date, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    partner = relationship("OutreachPartner", backref="take_home_bundles")
    distributions = relationship(
        "BundleDistribution", back_populates="bundle", cascade="all, delete-orphan"
    )


class BundleDistribution(Base):
    __tablename__ = "bundle_distributions"

    id = Column(Integer, primary_key=True, index=True)
    bundle_id = Column(
        Integer,
        ForeignKey("take_home_reading_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: take-home bundles are handed to schoolchildren who are usually
    # not library patrons, so most distributions have no patron account. When a
    # child IS a patron this links the row for reading-minutes tracking.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    # Free-text roster labels captured at hand-out time. These carry a child's
    # name/class and sit OUTSIDE the patron-identity boundary (they are not
    # _PATRON_ID_FIELDS); treat as child PII for retention purposes.
    student_name = Column(String(200), nullable=True)
    class_name = Column(String(100), nullable=True)

    # Distribution details
    distributed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    returned_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="distributed")  # "distributed", "returned", "lost"

    # Feedback
    family_feedback = Column(Text, nullable=True)
    reading_minutes_logged = Column(Integer, default=0, nullable=False)

    # Relationships
    bundle = relationship("TakeHomeReadingBundle", back_populates="distributions")
    user = relationship("User", backref="bundle_distributions")


# ============================================================================
# Professional Development Models
# ============================================================================


class TeacherTrainingModule(Base):
    __tablename__ = "teacher_training_modules"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Module details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    content_url = Column(String(500), nullable=True)  # Link to training material
    duration_minutes = Column(Integer, nullable=True)  # Estimated completion time

    # Module category
    category = Column(
        String(50), nullable=False
    )  # "reading-strategies", "engagement", "assessment", "technology"
    level = Column(String(50), nullable=False)  # "beginner", "intermediate", "advanced"

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    partner = relationship("OutreachPartner", backref="training_modules")
    completions = relationship(
        "TrainingCompletion", back_populates="module", cascade="all, delete-orphan"
    )


class TrainingCompletion(Base):
    __tablename__ = "training_completions"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(
        Integer,
        ForeignKey("teacher_training_modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Completion tracking
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        String(50), default="pending"
    )  # "pending", "in_progress", "completed", "certified"

    # Assessment
    quiz_score = Column(Integer, nullable=True)  # Percentage score
    passed_assessment = Column(Boolean, default=False, nullable=False)

    # Relationships
    module = relationship("TeacherTrainingModule", back_populates="completions")
    user = relationship("User", backref="training_completions")


class LibraryVisitRequest(Base):
    __tablename__ = "library_visit_requests"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    teacher_name = Column(String(200), nullable=False)
    requested_date = Column(DateTime(timezone=True), nullable=False)
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    number_of_students = Column(Integer, nullable=False)
    grade_level = Column(String(100), nullable=False)
    purpose = Column(Text, nullable=False)
    # pending | scheduled | rejected | cancelled
    status = Column(String(20), nullable=False, default="pending", index=True)
    approved_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    school = relationship("OutreachPartner", backref="library_visit_requests")
    teacher = relationship("User", foreign_keys=[teacher_user_id])
    approver = relationship("User", foreign_keys=[approved_by_user_id])

    __table_args__ = (Index("ix_library_visit_requests_school_status", "school_id", "status"),)


class ReadingAmbassadorCertification(Base):
    __tablename__ = "reading_ambassador_certifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Certification details
    certification_level = Column(
        String(50), nullable=False
    )  # "bronze", "silver", "gold", "platinum"
    certification_name = Column(
        String(200), nullable=False
    )  # e.g., "Reading Champion", "Literacy Leader"
    certification_number = Column(String(50), unique=True, nullable=True, index=True)

    # Training requirements
    required_modules_completed = Column(Integer, default=0, nullable=False)
    total_modules_required = Column(Integer, default=0, nullable=False)

    # Dates
    certified_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    renewal_eligible_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="ambassador_certification")
    partner = relationship("OutreachPartner", backref="ambassador_certifications")


class LibrarianConsultationSlot(Base):
    __tablename__ = "librarian_consultation_slots"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    librarian_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Consultation details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    consultation_type = Column(
        String(50), nullable=False
    )  # "curriculum-planning", "reading-strategies", "assessment", "program-design"

    # Scheduling
    scheduled_date = Column(Date, nullable=False)
    start_time = Column(String(10), nullable=False)  # HH:MM format
    end_time = Column(String(10), nullable=False)
    duration_minutes = Column(Integer, default=30, nullable=False)

    # Capacity
    max_participants = Column(Integer, default=10, nullable=False)
    current_participants = Column(Integer, default=0, nullable=False)

    # Status
    is_booked = Column(Boolean, default=False, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    partner = relationship("OutreachPartner", backref="consultation_slots")
    librarian = relationship("User", foreign_keys=[librarian_id], backref="consultation_slots")
    attendees = relationship(
        "ConsultationAttendee", back_populates="slot", cascade="all, delete-orphan"
    )


class ConsultationAttendee(Base):
    __tablename__ = "consultation_attendees"

    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(
        Integer,
        ForeignKey("librarian_consultation_slots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Attendance
    registered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    attended = Column(Boolean, default=False, nullable=False)

    # Feedback
    feedback = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 star rating

    # Relationships
    slot = relationship("LibrarianConsultationSlot", back_populates="attendees")
    user = relationship("User", backref="consultation_attendances")


# Prize/Reward System Models


class PrizeType(StrEnum):
    PHYSICAL = "physical"  # Books, bookmarks, etc
    DIGITAL = "digital"  # eBook, audiobook credits
    EXPERIENCE = "experience"  # Library event, author visit
    CERTIFICATE = "certificate"  # Digital/printed certificate
    BADGE = "badge"  # Digital badge/trophy


class ReadingPrize(Base, TimestampMixin):
    __tablename__ = "reading_prizes"

    id = Column(Integer, primary_key=True, index=True)

    # Prize identification
    program_id = Column(
        Integer, ForeignKey("reading_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Prize type and value
    prize_type = Column(String(50), nullable=False)
    prize_value = Column(
        String(500), nullable=True
    )  # e.g., "$10", "1 month free pass", "Book title"
    image_url = Column(String(500), nullable=True)

    # Eligibility criteria
    threshold_type = Column(String(20), nullable=False)  # "books", "minutes", "pages", "streak"
    threshold_value = Column(Integer, nullable=False)  # e.g., 10 books to earn this prize

    # Availability
    quantity_available = Column(Integer, nullable=True)  # NULL = unlimited
    quantity_redeemed = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Dates
    available_from = Column(Date, nullable=False)
    available_until = Column(Date, nullable=False)

    # Metadata
    sort_order = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    program = relationship("ReadingProgram", backref="prizes")
    created_by = relationship("User", foreign_keys=[created_by_id])
    redemptions = relationship(
        "PrizeRedemption", back_populates="prize", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_reading_prizes_program", "program_id"),
        Index("ix_reading_prizes_active", "is_active", "available_from", "available_until"),
        Index("ix_reading_prizes_threshold", "threshold_type", "threshold_value"),
    )

    @property
    def remaining_quantity(self) -> int:
        if self.quantity_available is None:
            return float("inf")
        return max(0, self.quantity_available - self.quantity_redeemed)

    @property
    def is_available_now(self) -> bool:
        today = date.today()
        return (
            self.is_active
            and self.remaining_quantity > 0
            and self.available_from <= today <= self.available_until
        )


class RedemptionStatus(StrEnum):
    PENDING = "pending"  # Claimed but not yet delivered
    APPROVED = "approved"  # Verified and approved
    DELIVERED = "delivered"  # Prize distributed
    CANCELLED = "cancelled"  # Redemption cancelled
    EXPIRED = "expired"  # Redemption expired before completion


class PrizeRedemption(Base, TimestampMixin):
    __tablename__ = "prize_redemptions"

    id = Column(Integer, primary_key=True, index=True)

    # References
    prize_id = Column(
        Integer, ForeignKey("reading_prizes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    registration_id = Column(
        Integer,
        ForeignKey("reading_registrations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Verification
    verification_code = Column(String(50), unique=True, nullable=False, index=True)

    # Status tracking
    status = Column(String(50), default=RedemptionStatus.PENDING, nullable=False, index=True)
    claimed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Approval workflow
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approval_notes = Column(Text, nullable=True)

    # Delivery tracking
    delivery_method = Column(String(50), nullable=True)  # "in_person", "email", "mail", "code"
    delivery_address = Column(Text, nullable=True)
    tracking_info = Column(String(500), nullable=True)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Cancellation
    cancellation_reason = Column(String(255), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    prize = relationship("ReadingPrize", back_populates="redemptions")
    user = relationship("User", foreign_keys=[user_id], backref="prize_redemptions")
    registration = relationship("ReadingRegistration", foreign_keys=[registration_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])

    __table_args__ = (
        Index("ix_prize_redemptions_user_prize", "user_id", "prize_id"),
        Index("ix_prize_redemptions_status", "status"),
        Index("ix_prize_redemptions_dates", "claimed_at", "delivered_at"),
    )


# ============================================================================
# Completion Certificate Models
# ============================================================================


class CertificateTemplate(Base, TimestampMixin):
    __tablename__ = "certificate_templates"

    id = Column(Integer, primary_key=True, index=True)

    # Template identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Usage scope
    program_id = Column(
        Integer,
        ForeignKey("reading_programs.id", ondelete="CASCADE"),
        nullable=True,  # NULL = organization-wide default
    )

    # Template design
    title_text = Column(String(500), nullable=False)  # e.g., "Certificate of Reading Achievement"
    congratulations_text = Column(Text, nullable=False)
    recognition_text = Column(Text, nullable=False)  # e.g., "has successfully completed..."

    # Visual design
    background_color = Column(String(7), default="#FFFFFF")  # Hex color
    accent_color = Column(String(7), default="#0066CC")
    border_style = Column(String(50), nullable=True)  # "simple", "ornate", "modern"
    include_logo = Column(Boolean, default=True)
    include_seal = Column(Boolean, default=True)

    # Template file
    template_file_url = Column(String(500), nullable=True)  # Path to PDF/image template

    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    program = relationship("ReadingProgram", backref="certificate_templates")
    created_by = relationship("User", foreign_keys=[created_by_id])
    certificates = relationship(
        "CompletionCertificate", back_populates="template", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_certificate_templates_program", "program_id"),
        Index("ix_certificate_templates_active", "is_active", "is_default"),
    )


class CompletionCertificate(Base, TimestampMixin):
    __tablename__ = "completion_certificates"

    id = Column(Integer, primary_key=True, index=True)

    # Certificate identification
    certificate_code = Column(
        String(50), unique=True, nullable=False, index=True
    )  # e.g., "CERT-2024-ABC123"

    # References
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id = Column(
        Integer, ForeignKey("reading_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    registration_id = Column(
        Integer, ForeignKey("reading_registrations.id", ondelete="SET NULL"), nullable=True
    )
    template_id = Column(
        Integer, ForeignKey("certificate_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Achievement data
    completion_date = Column(Date, nullable=False)
    reading_goal_achieved = Column(Integer, nullable=False)  # Total books/minutes achieved
    reading_goal_target = Column(Integer, nullable=False)  # Program target

    # Certificate generation
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    certificate_pdf_url = Column(String(500), nullable=True)  # Generated PDF location
    digital_badge_url = Column(String(500), nullable=True)  # Digital badge image

    # Verification
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Distribution
    emailed_to = Column(String(255), nullable=True)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Expiration (if applicable)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="completion_certificates")
    program = relationship("ReadingProgram", backref="completion_certificates")
    registration = relationship("ReadingRegistration", foreign_keys=[registration_id])
    template = relationship("CertificateTemplate", back_populates="certificates")
    verified_by = relationship("User", foreign_keys=[verified_by_id])

    __table_args__ = (
        Index("ix_completion_certs_user_program", "user_id", "program_id"),
        Index("ix_completion_certs_verified", "is_verified"),
        Index("ix_completion_certs_issued", "issued_at"),
    )


# ============================================================================
# Leaderboard Models
# ============================================================================


class LeaderboardType(StrEnum):
    PROGRAM = "program"  # Specific reading program
    REGIONAL = "regional"  # By region/branch
    AGE_GROUP = "age_group"  # By age group
    GLOBAL = "global"  # All participants
    SCHOOL = "school"  # School partnership


class LeaderboardPeriod(StrEnum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ALL_TIME = "all_time"


class Leaderboard(Base, TimestampMixin):
    __tablename__ = "leaderboards"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Configuration
    leaderboard_type = Column(String(50), nullable=False, index=True)
    period = Column(String(50), nullable=False, index=True)

    # Scope
    program_id = Column(
        Integer,
        ForeignKey("reading_programs.id", ondelete="CASCADE"),
        nullable=True,  # NULL for global leaderboards
    )
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=True)
    age_group = Column(String(50), nullable=True)  # e.g., "teen_13_18"
    school_partner_id = Column(
        Integer, ForeignKey("outreach_partners.id", ondelete="CASCADE"), nullable=True
    )

    # Scoring
    metric = Column(String(50), nullable=False)  # "books", "minutes", "points", "pages"

    # Time window
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)  # Visible to all?

    # Participation
    min_entries_to_rank = Column(Integer, default=1)  # Minimum logs needed to appear
    show_top_n = Column(Integer, default=100)  # Show top 100 entries

    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    program = relationship("ReadingProgram", backref="leaderboards")
    created_by = relationship("User", foreign_keys=[created_by_id])
    entries = relationship(
        "LeaderboardEntry", back_populates="leaderboard", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_leaderboards_program_type_period", "program_id", "leaderboard_type", "period"),
        Index("ix_leaderboards_type_active", "leaderboard_type", "is_active"),
        Index("ix_leaderboards_dates", "period_start", "period_end"),
    )


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"

    id = Column(Integer, primary_key=True, index=True)

    # References
    leaderboard_id = Column(
        Integer, ForeignKey("leaderboards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Ranking
    rank = Column(Integer, nullable=False)  # 1 = first place, 2 = second, etc.
    score = Column(Integer, nullable=False)  # Books, minutes, points, pages, etc.

    # Percentile
    percentile = Column(Integer, nullable=True)  # 0-100

    # Badges/status
    is_tied = Column(Boolean, default=False)  # Tied with another entry?
    is_new_entry = Column(Boolean, default=False)  # New to leaderboard this period?
    previous_rank = Column(Integer, nullable=True)  # Last period's rank
    rank_change = Column(Integer, nullable=True)  # +5 (improved), -3 (dropped), 0 (same)

    # Achievement badges
    is_top_10 = Column(Boolean, default=False)
    is_top_50 = Column(Boolean, default=False)
    is_top_100 = Column(Boolean, default=False)
    is_champion = Column(Boolean, default=False)  # #1 rank

    # Tracking
    entries_count = Column(Integer, default=0)  # Number of reading log entries
    last_entry_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    leaderboard = relationship("Leaderboard", back_populates="entries")
    user = relationship("User", backref="leaderboard_entries")

    __table_args__ = (
        Index("ix_leaderboard_entries_leaderboard_rank", "leaderboard_id", "rank"),
        Index("ix_leaderboard_entries_user", "user_id"),
        Index("ix_leaderboard_entries_score", "leaderboard_id", "score", "rank"),
        UniqueConstraint("leaderboard_id", "user_id", name="uq_leaderboard_user"),
    )


class LeaderboardHistory(Base):
    __tablename__ = "leaderboard_history"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    leaderboard_id = Column(
        Integer, ForeignKey("leaderboards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Snapshot data
    rank = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)
    snapshot_date = Column(Date, nullable=False)
    snapshot_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    leaderboard = relationship("Leaderboard")
    user = relationship("User")

    __table_args__ = (
        Index("ix_leaderboard_history_user_date", "user_id", "snapshot_date"),
        Index("ix_leaderboard_history_leaderboard_date", "leaderboard_id", "snapshot_date"),
    )


# ============================================================================
# Program Booklist (Recommended Reads per Program)
# ============================================================================


class ProgramBooklistItem(Base):
    __tablename__ = "program_booklist"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(
        Integer,
        ForeignKey("reading_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_order = Column(Integer, nullable=False, default=0)
    note = Column(String(500), nullable=True)
    added_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    program = relationship("ReadingProgram", lazy="raise")
    catalog_item = relationship("CatalogItem", lazy="raise")
    added_by = relationship("User", lazy="raise")

    __table_args__ = (
        UniqueConstraint("program_id", "catalog_item_id", name="uq_program_booklist_item"),
    )
