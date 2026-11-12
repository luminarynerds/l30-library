# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, String, DateTime, Date, Index
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PeriodType(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class QuestionType(StrEnum):
    DIRECTIONAL = "directional"  # Simple directions/location
    READY_REFERENCE = "ready_reference"  # Quick factual answers
    RESEARCH = "research"  # In-depth research assistance
    READERS_ADVISORY = "readers_advisory"  # Book recommendations
    TECHNICAL = "technical"  # Technology help


class ContactMethod(StrEnum):
    IN_PERSON = "in_person"
    PHONE = "phone"
    EMAIL = "email"
    CHAT = "chat"
    TEXT = "text"
    SOCIAL_MEDIA = "social_media"
    VIDEO = "video"


class CountSource(StrEnum):
    DOOR_COUNTER = "door_counter"  # Automated door counter
    MANUAL = "manual"  # Staff manual count
    ESTIMATED = "estimated"  # Estimated based on sampling


class ReportType(StrEnum):
    IMLS_SURVEY = "imls_survey"  # Annual IMLS Public Libraries Survey
    PLA_BENCHMARK = "pla_benchmark"  # PLA benchmarking
    STATE_REPORT = "state_report"  # State library report
    CUSTOM = "custom"  # Custom report
    TREND = "trend"  # Trend analysis
    COMPARISON = "comparison"  # Peer comparison report


class ReportStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class CirculationStatistics(Base):
    __tablename__ = "circulation_statistics"

    id = Column(Integer, primary_key=True, index=True)

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly, yearly
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # NULL = all branches

    # Item type breakdowns (JSONB for flexibility)
    checkouts_by_item_type = Column(JSONB)  # {"book": 100, "dvd": 50, ...}
    renewals_by_item_type = Column(JSONB)
    holds_placed_by_item_type = Column(JSONB)
    holds_filled_by_item_type = Column(JSONB)

    # Totals
    total_checkouts = Column(Integer, nullable=False, default=0)
    total_renewals = Column(Integer, nullable=False, default=0)
    total_holds_placed = Column(Integer, nullable=False, default=0)
    total_holds_filled = Column(Integer, nullable=False, default=0)
    total_returns = Column(Integer, nullable=False, default=0)

    # ILL (Interlibrary Loan)
    items_loaned_to_other_libraries = Column(Integer, nullable=False, default=0)
    items_borrowed_from_other_libraries = Column(Integer, nullable=False, default=0)

    # In-house usage
    in_house_use_count = Column(Integer, nullable=False, default=0)

    # Turnover rate
    collection_turnover_rate = Column(Numeric(8, 4))

    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)

    # Relationships
    generated_by = relationship("User", foreign_keys=[generated_by_id])

    __table_args__ = (
        Index("ix_circulation_statistics_period", "period_start", "period_end"),
        Index("ix_circulation_statistics_period_branch", "period_type", "branch_location", "period_start"),
    )


class CollectionStatistics(Base):
    __tablename__ = "collection_statistics"

    id = Column(Integer, primary_key=True)

    # Snapshot date
    snapshot_date = Column(Date, nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # deprecated; use branch_id

    # Holdings by format/category (JSONB for flexibility)
    items_owned_by_format = Column(JSONB)  # {"book": 5000, "dvd": 500, ...}
    items_owned_by_collection = Column(JSONB)  # {"adult": 3000, "juvenile": 2000, ...}
    items_owned_by_subject = Column(JSONB)  # By Dewey or subject category

    # Changes during period
    items_added_by_format = Column(JSONB)
    items_withdrawn_by_format = Column(JSONB)
    items_withdrawn_by_reason = Column(JSONB)  # {"weeded": 50, "lost": 10, "damaged": 5}

    # Totals
    total_items_owned = Column(Integer, nullable=False, default=0)
    total_titles_owned = Column(Integer, nullable=False, default=0)
    total_items_added = Column(Integer, nullable=False, default=0)
    total_items_withdrawn = Column(Integer, nullable=False, default=0)

    # E-resources
    electronic_titles = Column(Integer, nullable=False, default=0)
    electronic_databases = Column(Integer, nullable=False, default=0)

    # Physical formats
    print_materials = Column(Integer, nullable=False, default=0)
    audio_materials = Column(Integer, nullable=False, default=0)
    video_materials = Column(Integer, nullable=False, default=0)
    other_materials = Column(Integer, nullable=False, default=0)

    # Serial subscriptions
    current_serial_subscriptions = Column(Integer, nullable=False, default=0)

    # Collection value
    total_collection_value = Column(Numeric(15, 2))

    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)

    # Relationships
    generated_by = relationship("User", foreign_keys=[generated_by_id])

    __table_args__ = (
        Index("ix_collection_statistics_date_branch", "snapshot_date", "branch_location"),
    )


class PatronStatistics(Base):
    __tablename__ = "patron_statistics"

    id = Column(Integer, primary_key=True)

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # deprecated; use branch_id

    # Patron counts
    total_registered_patrons = Column(Integer, nullable=False, default=0)
    new_registrations = Column(Integer, nullable=False, default=0)
    expired_cards = Column(Integer, nullable=False, default=0)
    renewed_cards = Column(Integer, nullable=False, default=0)

    # Active patrons
    active_borrowers = Column(Integer, nullable=False, default=0)  # Had checkouts
    active_patrons_any_service = Column(Integer, nullable=False, default=0)  # Any library use

    # Demographics (JSONB)
    patrons_by_age_group = Column(JSONB)  # {"child": 500, "teen": 200, "adult": 1000, "senior": 300}
    patrons_by_patron_type = Column(JSONB)  # {"regular": 1500, "student": 300, "staff": 50}
    patrons_by_zip_code = Column(JSONB)  # {"12345": 500, "12346": 300}

    # Engagement metrics
    avg_checkouts_per_active_patron = Column(Numeric(8, 2))
    avg_visits_per_active_patron = Column(Numeric(8, 2))

    # Resident vs non-resident
    resident_patrons = Column(Integer, nullable=False, default=0)
    non_resident_patrons = Column(Integer, nullable=False, default=0)

    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)

    # Relationships
    generated_by = relationship("User", foreign_keys=[generated_by_id])

    __table_args__ = (
        Index("ix_patron_statistics_period", "period_start", "period_end"),
    )


class ProgramStatistics(Base):
    __tablename__ = "program_statistics"

    id = Column(Integer, primary_key=True)

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # deprecated; use branch_id

    # Event counts by category (JSONB)
    events_by_category = Column(JSONB)  # {"storytime": 20, "book_club": 4, ...}
    events_by_age_group = Column(JSONB)  # {"children": 25, "teen": 10, "adult": 15}
    attendance_by_category = Column(JSONB)
    attendance_by_age_group = Column(JSONB)

    # Totals
    total_programs_offered = Column(Integer, nullable=False, default=0)
    total_program_attendance = Column(Integer, nullable=False, default=0)
    avg_attendance_per_program = Column(Numeric(8, 2))

    # Children's programs (IMLS required)
    childrens_programs_count = Column(Integer, nullable=False, default=0)
    childrens_program_attendance = Column(Integer, nullable=False, default=0)

    # Young adult programs
    young_adult_programs_count = Column(Integer, nullable=False, default=0)
    young_adult_program_attendance = Column(Integer, nullable=False, default=0)

    # Adult programs
    adult_programs_count = Column(Integer, nullable=False, default=0)
    adult_program_attendance = Column(Integer, nullable=False, default=0)

    # Other program types
    outreach_programs_count = Column(Integer, nullable=False, default=0)
    outreach_program_attendance = Column(Integer, nullable=False, default=0)
    virtual_programs_count = Column(Integer, nullable=False, default=0)
    virtual_program_attendance = Column(Integer, nullable=False, default=0)

    # Reading programs
    reading_program_participants = Column(Integer, nullable=False, default=0)
    reading_program_completions = Column(Integer, nullable=False, default=0)

    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)

    # Relationships
    generated_by = relationship("User", foreign_keys=[generated_by_id])

    __table_args__ = (
        Index("ix_program_statistics_period", "period_start", "period_end"),
    )


class ComputerUsageStatistics(Base):
    __tablename__ = "computer_usage_statistics"

    id = Column(Integer, primary_key=True)

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # deprecated; use branch_id

    # Session counts
    total_sessions = Column(Integer, nullable=False, default=0)
    unique_users = Column(Integer, nullable=False, default=0)

    # Usage time
    total_hours_used = Column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    avg_session_length_minutes = Column(Numeric(8, 2))

    # Breakdowns (JSONB)
    sessions_by_hour_of_day = Column(JSONB)  # {"9": 50, "10": 75, ...}
    sessions_by_day_of_week = Column(JSONB)  # {"Monday": 200, "Tuesday": 180, ...}
    sessions_by_workstation = Column(JSONB)  # {"PC1": 100, "PC2": 95, ...}

    # WiFi (if tracked)
    wifi_sessions = Column(Integer, nullable=False, default=0)
    wifi_unique_devices = Column(Integer, nullable=False, default=0)

    # Printing/copying
    print_jobs = Column(Integer, nullable=False, default=0)
    pages_printed = Column(Integer, nullable=False, default=0)
    copy_jobs = Column(Integer, nullable=False, default=0)
    pages_copied = Column(Integer, nullable=False, default=0)

    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)

    # Relationships
    generated_by = relationship("User", foreign_keys=[generated_by_id])

    __table_args__ = (
        Index("ix_computer_usage_statistics_period", "period_start", "period_end"),
    )


class ReferenceQuestion(Base):
    __tablename__ = "reference_questions"

    id = Column(Integer, primary_key=True)

    # When and where
    asked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='SET NULL'), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # deprecated; use branch_id

    # Question type (READ scale)
    question_type = Column(
        String(50),
    )

    # Contact method
    contact_method = Column(
        String(50),
    )

    # Duration (optional)
    duration_minutes = Column(Integer)

    # Patron type (anonymous)
    patron_type = Column(String(50))  # adult, young_adult, child, unknown

    # Subject area (optional)
    subject_area = Column(String(100))

    # Referral tracking
    was_referred = Column(Boolean, nullable=False, default=False)
    referred_to = Column(String(100))

    # Staff member (optional)
    answered_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Notes (no PII)
    notes = Column(Text)

    # Metadata, server_default=func.now(), nullable=False)

    # Relationships
    answered_by = relationship("User", foreign_keys=[answered_by_id])

    __table_args__ = (
        Index("ix_reference_questions_type_method", "question_type", "contact_method"),
        Index("ix_reference_questions_date_branch", "asked_at", "branch_location"),
    )


class ReferenceStatistics(Base):
    __tablename__ = "reference_statistics"

    id = Column(Integer, primary_key=True)

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # deprecated; use branch_id

    # Total
    total_questions = Column(Integer, nullable=False, default=0)

    # Breakdowns (JSONB)
    questions_by_type = Column(JSONB)  # {"directional": 100, "research": 50, ...}
    questions_by_method = Column(JSONB)  # {"in_person": 200, "phone": 50, ...}
    questions_by_patron_type = Column(JSONB)
    questions_by_subject = Column(JSONB)

    # Averages
    avg_duration_minutes = Column(Numeric(8, 2))

    # Referral statistics
    total_referrals = Column(Integer, nullable=False, default=0)

    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)

    # Relationships
    generated_by = relationship("User", foreign_keys=[generated_by_id])

    __table_args__ = (
        Index("ix_reference_statistics_period", "period_start", "period_end"),
    )


class VisitCount(Base):
    __tablename__ = "visit_counts"

    id = Column(Integer, primary_key=True)

    # Date and location
    count_date = Column(Date, nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # deprecated; use branch_id

    # Door count
    door_count = Column(Integer, nullable=False, default=0)

    # Source
    count_source = Column(
        String(50),
    )

    # Hourly breakdown (if available)
    counts_by_hour = Column(JSONB)  # {"9": 50, "10": 75, ...}

    # Adjustments
    adjustment_factor = Column(Numeric(5, 3))  # e.g., 0.5 for double-counting doors
    adjusted_count = Column(Integer)

    # Notes
    weather_notes = Column(String(100))
    special_circumstances = Column(Text)

    # Who recorded it
    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Metadata, server_default=func.now(), nullable=False)

    # Relationships
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])

    __table_args__ = (
        Index("ix_visit_counts_date_branch", "count_date", "branch_location", unique=True),
    )


class VisitStatistics(Base):
    __tablename__ = "visit_statistics"

    id = Column(Integer, primary_key=True)

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # deprecated; use branch_id

    # Totals
    total_visits = Column(Integer, nullable=False, default=0)
    avg_daily_visits = Column(Numeric(10, 2))

    # Peak times
    peak_hour = Column(Integer)  # 0-23
    peak_day_of_week = Column(Integer)  # 0-6 (Monday=0)

    # Breakdowns (JSONB)
    visits_by_day_of_week = Column(JSONB)
    visits_by_hour = Column(JSONB)

    # Per capita
    visits_per_capita = Column(Numeric(8, 4))
    population_served = Column(Integer)

    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)

    # Relationships
    generated_by = relationship("User", foreign_keys=[generated_by_id])

    __table_args__ = (
        Index("ix_visit_statistics_period", "period_start", "period_end"),
    )


class PeerComparisonLibrary(Base):
    __tablename__ = "peer_comparison_libraries"

    id = Column(Integer, primary_key=True)

    # Library identification
    library_name = Column(String(200), nullable=False)
    library_id = Column(String(50))  # FSCS ID or other identifier
    state = Column(String(2))
    city = Column(String(100))

    # Comparison criteria
    population_served = Column(Integer)
    total_operating_expenditure = Column(Numeric(15, 2))
    total_staff_fte = Column(Numeric(8, 2))
    collection_size = Column(Integer)
    service_area_sq_miles = Column(Numeric(10, 2))

    # Is this our library?
    is_our_library = Column(Boolean, nullable=False, default=False)

    # Active for comparison
    is_active = Column(Boolean, nullable=False, default=True)

    # Metadata
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)

    # Relationships
    added_by = relationship("User", foreign_keys=[added_by_id])
    comparison_data = relationship("PeerComparisonData", back_populates="peer_library", cascade="all, delete-orphan")


class PeerComparisonData(Base):
    __tablename__ = "peer_comparison_data"

    id = Column(Integer, primary_key=True)

    # Library reference
    peer_library_id = Column(
        Integer,
        ForeignKey("peer_comparison_libraries.id", ondelete="CASCADE"),
    )
    data_year = Column(Integer, nullable=False)
    data_source = Column(String(50))  # IMLS, state library, manual

    # Core IMLS/PLA metrics
    total_circulation = Column(Integer)
    total_visits = Column(Integer)
    registered_borrowers = Column(Integer)
    total_programs = Column(Integer)
    total_program_attendance = Column(Integer)
    reference_transactions = Column(Integer)
    computer_uses = Column(Integer)

    # Collection metrics
    print_collection = Column(Integer)
    electronic_collection = Column(Integer)
    audio_collection = Column(Integer)
    video_collection = Column(Integer)

    # Financial metrics
    total_operating_revenue = Column(Numeric(15, 2))
    total_operating_expenditure = Column(Numeric(15, 2))
    collection_expenditure = Column(Numeric(15, 2))
    staff_expenditure = Column(Numeric(15, 2))

    # Staff metrics
    total_staff_fte = Column(Numeric(8, 2))
    librarian_fte = Column(Numeric(8, 2))

    # Per-capita metrics (stored for convenience)
    circulation_per_capita = Column(Numeric(10, 4))
    visits_per_capita = Column(Numeric(10, 4))
    expenditure_per_capita = Column(Numeric(10, 4))

    # Extended metrics (JSONB for flexibility)
    additional_metrics = Column(JSONB)

    # Metadata
    imported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    imported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)

    # Relationships
    peer_library = relationship("PeerComparisonLibrary", back_populates="comparison_data")
    imported_by = relationship("User", foreign_keys=[imported_by_id])

    __table_args__ = (
        Index("ix_peer_comparison_data_library_year", "peer_library_id", "data_year", unique=True),
    )


class StatisticalReport(Base):
    __tablename__ = "statistical_reports"

    id = Column(Integer, primary_key=True)

    # Report identification
    report_name = Column(String(200), nullable=False)
    report_type = Column(
        String(50),
        index=True,
    )

    # Time period
    period_start = Column(Date)
    period_end = Column(Date)
    fiscal_year = Column(Integer)

    # Scope
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100))  # deprecated; use branch_id
    includes_all_branches = Column(Boolean, nullable=False, default=True)

    # Report configuration
    report_parameters = Column(JSONB)  # Custom parameters
    included_statistics = Column(JSONB)  # Which stats to include

    # Generated file
    file_format = Column(String(20))  # pdf, xlsx, csv
    file_path = Column(String(500))
    file_size_bytes = Column(Integer)

    # Status
    status = Column(
        String(50),
        default=ReportStatus.PENDING,
    )
    error_message = Column(Text)

    # Who generated it
    generated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    generated_at = Column(DateTime(timezone=True))

    # Access tracking
    download_count = Column(Integer, nullable=False, default=0)
    last_downloaded_at = Column(DateTime(timezone=True))

    # Metadata
    notes = Column(Text)

    # Relationships
    generated_by = relationship("User", foreign_keys=[generated_by_id])

    __table_args__ = (
        Index("ix_statistical_reports_period", "period_start", "period_end"),
    )


class UsageStatisticsSettings(Base):
    __tablename__ = "usage_statistics_settings"

    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # NULL = system-wide

    # Auto-generation settings
    auto_generate_daily = Column(Boolean, nullable=False, default=True)
    auto_generate_weekly = Column(Boolean, nullable=False, default=True)
    auto_generate_monthly = Column(Boolean, nullable=False, default=True)
    auto_generate_yearly = Column(Boolean, nullable=False, default=True)

    # Fiscal year settings
    fiscal_year_start_month = Column(Integer, nullable=False, default=7)  # July

    # Population data
    legal_service_area_population = Column(Integer)
    population_data_year = Column(Integer)

    # Door counter settings
    door_counter_enabled = Column(Boolean, nullable=False, default=False)
    door_counter_adjustment_factor = Column(Numeric(5, 3), default=Decimal("1.0"))

    # Reference sampling settings
    reference_sampling_enabled = Column(Boolean, nullable=False, default=False)
    reference_sample_weeks = Column(JSONB)  # Weeks to sample
    reference_extrapolation_factor = Column(Numeric(5, 2))

    # IMLS/State reporting IDs
    imls_library_id = Column(String(50))  # FSCS ID
    state_library_id = Column(String(50))

    # Active flag
    is_active = Column(Boolean, nullable=False, default=True)

    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
