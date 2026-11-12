# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import MoneyDecimal, StrictInputSchema


# ============================================================================
# Enums
# ============================================================================


class PeriodType(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class QuestionType(StrEnum):
    DIRECTIONAL = "directional"
    READY_REFERENCE = "ready_reference"
    RESEARCH = "research"
    READERS_ADVISORY = "readers_advisory"
    TECHNICAL = "technical"


class ContactMethod(StrEnum):
    IN_PERSON = "in_person"
    PHONE = "phone"
    EMAIL = "email"
    CHAT = "chat"
    TEXT = "text"
    SOCIAL_MEDIA = "social_media"
    VIDEO = "video"


class CountSource(StrEnum):
    DOOR_COUNTER = "door_counter"
    MANUAL = "manual"
    ESTIMATED = "estimated"


class ReportType(StrEnum):
    IMLS_SURVEY = "imls_survey"
    PLA_BENCHMARK = "pla_benchmark"
    STATE_REPORT = "state_report"
    CUSTOM = "custom"
    TREND = "trend"
    COMPARISON = "comparison"


class ReportStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportFormat(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


# ============================================================================
# Base Schemas
# ============================================================================


class StatisticsMetadata(BaseModel):
    generated_at: datetime
    period_start: date
    period_end: date
    period_type: PeriodType
    branch_location: Optional[str] = None


# ============================================================================
# Circulation Statistics
# ============================================================================


class CirculationStatisticsBase(BaseModel):
    period_start: date
    period_end: date
    period_type: PeriodType
    # branch_id is canonical FK; branch_location kept for back-compat.
    branch_id: Optional[int] = None
    branch_location: Optional[str] = None
    checkouts_by_item_type: Optional[Dict[str, int]] = None
    renewals_by_item_type: Optional[Dict[str, int]] = None
    holds_placed_by_item_type: Optional[Dict[str, int]] = None
    holds_filled_by_item_type: Optional[Dict[str, int]] = None
    total_checkouts: int = 0
    total_renewals: int = 0
    total_holds_placed: int = 0
    total_holds_filled: int = 0
    total_returns: int = 0
    items_loaned_to_other_libraries: int = 0
    items_borrowed_from_other_libraries: int = 0
    in_house_use_count: int = 0
    collection_turnover_rate: Optional[float] = None
    notes: Optional[str] = None


class CirculationStatisticsCreate(StrictInputSchema, CirculationStatisticsBase):
    pass


class CirculationStatisticsResponse(CirculationStatisticsBase):
    id: int
    generated_at: datetime
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class CirculationStatisticsSummary(BaseModel):
    total_checkouts: int
    total_renewals: int
    total_holds: int
    total_ill_transactions: int
    turnover_rate: Optional[float] = None
    checkouts_by_item_type: Dict[str, int]
    metadata: StatisticsMetadata


# ============================================================================
# Collection Statistics
# ============================================================================


class CollectionStatisticsBase(BaseModel):
    snapshot_date: date
    # branch_id is canonical FK; branch_location kept for back-compat.
    branch_id: Optional[int] = None
    branch_location: Optional[str] = None
    items_owned_by_format: Optional[Dict[str, int]] = None
    items_owned_by_collection: Optional[Dict[str, int]] = None
    items_owned_by_subject: Optional[Dict[str, int]] = None
    items_added_by_format: Optional[Dict[str, int]] = None
    items_withdrawn_by_format: Optional[Dict[str, int]] = None
    items_withdrawn_by_reason: Optional[Dict[str, int]] = None
    total_items_owned: int = 0
    total_titles_owned: int = 0
    total_items_added: int = 0
    total_items_withdrawn: int = 0
    electronic_titles: int = 0
    electronic_databases: int = 0
    print_materials: int = 0
    audio_materials: int = 0
    video_materials: int = 0
    other_materials: int = 0
    current_serial_subscriptions: int = 0
    total_collection_value: Optional[MoneyDecimal] = None
    notes: Optional[str] = None


class CollectionStatisticsCreate(StrictInputSchema, CollectionStatisticsBase):
    pass


class CollectionStatisticsResponse(CollectionStatisticsBase):
    id: int
    generated_at: datetime
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class CollectionStatisticsSummary(BaseModel):
    total_items: int
    total_titles: int
    items_by_format: Dict[str, int]
    net_change: int  # added - withdrawn
    collection_value: Optional[float] = None
    snapshot_date: date


# ============================================================================
# Patron Statistics
# ============================================================================


class PatronStatisticsBase(BaseModel):
    period_start: date
    period_end: date
    period_type: PeriodType
    # branch_id is the canonical FK (Phase 3 tranche 1). branch_location
    # stays accepted for back-compat until Phase 4 drops the column.
    branch_id: Optional[int] = None
    branch_location: Optional[str] = None
    total_registered_patrons: int = 0
    new_registrations: int = 0
    expired_cards: int = 0
    renewed_cards: int = 0
    active_borrowers: int = 0
    active_patrons_any_service: int = 0
    patrons_by_age_group: Optional[Dict[str, int]] = None
    patrons_by_patron_type: Optional[Dict[str, int]] = None
    patrons_by_zip_code: Optional[Dict[str, int]] = None
    avg_checkouts_per_active_patron: Optional[float] = None
    avg_visits_per_active_patron: Optional[float] = None
    resident_patrons: int = 0
    non_resident_patrons: int = 0
    notes: Optional[str] = None


class PatronStatisticsCreate(StrictInputSchema, PatronStatisticsBase):
    pass


class PatronStatisticsResponse(PatronStatisticsBase):
    id: int
    generated_at: datetime
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class PatronStatisticsSummary(BaseModel):
    total_registered: int
    active_borrowers: int
    new_registrations: int
    registration_rate: float  # new / total
    engagement_rate: float  # active / total
    metadata: StatisticsMetadata


# ============================================================================
# Program Statistics
# ============================================================================


class ProgramStatisticsBase(BaseModel):
    period_start: date
    period_end: date
    period_type: PeriodType
    # branch_id is canonical FK; branch_location kept for back-compat.
    branch_id: Optional[int] = None
    branch_location: Optional[str] = None
    events_by_category: Optional[Dict[str, int]] = None
    events_by_age_group: Optional[Dict[str, int]] = None
    attendance_by_category: Optional[Dict[str, int]] = None
    attendance_by_age_group: Optional[Dict[str, int]] = None
    total_programs_offered: int = 0
    total_program_attendance: int = 0
    avg_attendance_per_program: Optional[float] = None
    childrens_programs_count: int = 0
    childrens_program_attendance: int = 0
    young_adult_programs_count: int = 0
    young_adult_program_attendance: int = 0
    adult_programs_count: int = 0
    adult_program_attendance: int = 0
    outreach_programs_count: int = 0
    outreach_program_attendance: int = 0
    virtual_programs_count: int = 0
    virtual_program_attendance: int = 0
    reading_program_participants: int = 0
    reading_program_completions: int = 0
    notes: Optional[str] = None


class ProgramStatisticsCreate(StrictInputSchema, ProgramStatisticsBase):
    pass


class ProgramStatisticsResponse(ProgramStatisticsBase):
    id: int
    generated_at: datetime
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ProgramStatisticsSummary(BaseModel):
    total_programs: int
    total_attendance: int
    avg_attendance: float
    programs_by_age_group: Dict[str, int]
    attendance_by_age_group: Dict[str, int]
    metadata: StatisticsMetadata


# ============================================================================
# Computer Usage Statistics
# ============================================================================


class ComputerUsageStatisticsBase(BaseModel):
    period_start: date
    period_end: date
    period_type: PeriodType
    branch_id: Optional[int] = None
    branch_location: Optional[str] = None
    total_sessions: int = 0
    unique_users: int = 0
    total_hours_used: float = 0
    avg_session_length_minutes: Optional[float] = None
    sessions_by_hour_of_day: Optional[Dict[str, int]] = None
    sessions_by_day_of_week: Optional[Dict[str, int]] = None
    sessions_by_workstation: Optional[Dict[str, int]] = None
    wifi_sessions: int = 0
    wifi_unique_devices: int = 0
    print_jobs: int = 0
    pages_printed: int = 0
    copy_jobs: int = 0
    pages_copied: int = 0
    notes: Optional[str] = None


class ComputerUsageStatisticsCreate(StrictInputSchema, ComputerUsageStatisticsBase):
    pass


class ComputerUsageStatisticsResponse(ComputerUsageStatisticsBase):
    id: int
    generated_at: datetime
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ComputerUsageSummary(BaseModel):
    total_sessions: int
    unique_users: int
    total_hours: float
    avg_session_minutes: float
    wifi_sessions: int
    metadata: StatisticsMetadata


# ============================================================================
# Reference Questions
# ============================================================================


class ReferenceQuestionBase(BaseModel):
    question_type: QuestionType
    contact_method: ContactMethod
    branch_location: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=0, le=480)
    patron_type: Optional[str] = None
    subject_area: Optional[str] = None
    was_referred: bool = False
    referred_to: Optional[str] = None
    notes: Optional[str] = None


class ReferenceQuestionCreate(StrictInputSchema, ReferenceQuestionBase):
    asked_at: Optional[datetime] = None  # Defaults to now


class ReferenceQuestionResponse(ReferenceQuestionBase):
    id: int
    asked_at: datetime
    answered_by_id: Optional[int] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ReferenceStatisticsBase(BaseModel):
    period_start: date
    period_end: date
    period_type: PeriodType
    branch_id: Optional[int] = None
    branch_location: Optional[str] = None
    total_questions: int = 0
    questions_by_type: Optional[Dict[str, int]] = None
    questions_by_method: Optional[Dict[str, int]] = None
    questions_by_patron_type: Optional[Dict[str, int]] = None
    questions_by_subject: Optional[Dict[str, int]] = None
    avg_duration_minutes: Optional[float] = None
    total_referrals: int = 0
    notes: Optional[str] = None


class ReferenceStatisticsCreate(StrictInputSchema, ReferenceStatisticsBase):
    pass


class ReferenceStatisticsResponse(ReferenceStatisticsBase):
    id: int
    generated_at: datetime
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ReferenceStatisticsSummary(BaseModel):
    total_questions: int
    questions_by_type: Dict[str, int]
    questions_by_method: Dict[str, int]
    avg_duration: Optional[float]
    metadata: StatisticsMetadata


# ============================================================================
# Visit Statistics
# ============================================================================


class VisitCountBase(BaseModel):
    count_date: date
    branch_location: Optional[str] = None
    door_count: int = Field(..., ge=0)
    count_source: CountSource
    counts_by_hour: Optional[Dict[str, int]] = None
    adjustment_factor: Optional[float] = None
    weather_notes: Optional[str] = None
    special_circumstances: Optional[str] = None


class VisitCountCreate(StrictInputSchema, VisitCountBase):
    pass


class VisitCountUpdate(StrictInputSchema):
    door_count: Optional[int] = Field(None, ge=0)
    count_source: Optional[CountSource] = None
    counts_by_hour: Optional[Dict[str, int]] = None
    adjustment_factor: Optional[float] = None
    weather_notes: Optional[str] = None
    special_circumstances: Optional[str] = None


class VisitCountResponse(VisitCountBase):
    id: int
    adjusted_count: Optional[int] = None
    recorded_by_id: Optional[int] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class VisitStatisticsBase(BaseModel):
    period_start: date
    period_end: date
    period_type: PeriodType
    branch_id: Optional[int] = None
    branch_location: Optional[str] = None
    total_visits: int = 0
    avg_daily_visits: Optional[float] = None
    peak_hour: Optional[int] = None
    peak_day_of_week: Optional[int] = None
    visits_by_day_of_week: Optional[Dict[str, int]] = None
    visits_by_hour: Optional[Dict[str, int]] = None
    visits_per_capita: Optional[float] = None
    population_served: Optional[int] = None
    notes: Optional[str] = None


class VisitStatisticsCreate(StrictInputSchema, VisitStatisticsBase):
    pass


class VisitStatisticsResponse(VisitStatisticsBase):
    id: int
    generated_at: datetime
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class VisitStatisticsSummary(BaseModel):
    total_visits: int
    avg_daily_visits: float
    visits_per_capita: Optional[float]
    peak_hour: Optional[int]
    peak_day: Optional[str]
    metadata: StatisticsMetadata


# ============================================================================
# Peer Comparison
# ============================================================================


class PeerLibraryBase(BaseModel):
    library_name: str = Field(..., min_length=1, max_length=200)
    library_id: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    city: Optional[str] = Field(None, max_length=100)
    population_served: Optional[int] = Field(None, ge=0)
    total_operating_expenditure: Optional[MoneyDecimal] = None
    total_staff_fte: Optional[float] = None
    collection_size: Optional[int] = Field(None, ge=0)
    service_area_sq_miles: Optional[float] = None
    is_our_library: bool = False
    notes: Optional[str] = None


class PeerLibraryCreate(StrictInputSchema, PeerLibraryBase):
    pass


class PeerLibraryUpdate(StrictInputSchema):
    library_name: Optional[str] = Field(None, min_length=1, max_length=200)
    library_id: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    city: Optional[str] = Field(None, max_length=100)
    population_served: Optional[int] = Field(None, ge=0)
    total_operating_expenditure: Optional[MoneyDecimal] = None
    total_staff_fte: Optional[float] = None
    collection_size: Optional[int] = Field(None, ge=0)
    service_area_sq_miles: Optional[float] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class PeerLibraryResponse(PeerLibraryBase):
    id: int
    is_active: bool
    added_by_id: Optional[int] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class PeerComparisonDataBase(BaseModel):
    data_year: int = Field(..., ge=2000, le=2100)
    data_source: Optional[str] = None
    total_circulation: Optional[int] = None
    total_visits: Optional[int] = None
    registered_borrowers: Optional[int] = None
    total_programs: Optional[int] = None
    total_program_attendance: Optional[int] = None
    reference_transactions: Optional[int] = None
    computer_uses: Optional[int] = None
    print_collection: Optional[int] = None
    electronic_collection: Optional[int] = None
    audio_collection: Optional[int] = None
    video_collection: Optional[int] = None
    total_operating_revenue: Optional[MoneyDecimal] = None
    total_operating_expenditure: Optional[MoneyDecimal] = None
    collection_expenditure: Optional[MoneyDecimal] = None
    staff_expenditure: Optional[MoneyDecimal] = None
    total_staff_fte: Optional[float] = None
    librarian_fte: Optional[float] = None
    circulation_per_capita: Optional[float] = None
    visits_per_capita: Optional[float] = None
    expenditure_per_capita: Optional[float] = None
    additional_metrics: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class PeerComparisonDataCreate(StrictInputSchema, PeerComparisonDataBase):
    peer_library_id: int


class PeerComparisonDataResponse(PeerComparisonDataBase):
    id: int
    peer_library_id: int
    imported_at: datetime
    imported_by_id: Optional[int] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class PeerComparisonResult(BaseModel):
    metric_name: str
    our_value: Optional[float]
    peer_avg: Optional[float]
    peer_median: Optional[float]
    peer_min: Optional[float]
    peer_max: Optional[float]
    percentile_rank: Optional[float]  # Where we fall among peers


class PeerComparisonReport(BaseModel):
    data_year: int
    our_library: PeerLibraryResponse
    peer_count: int
    metrics: List[PeerComparisonResult]
    generated_at: datetime


# ============================================================================
# Statistical Reports
# ============================================================================


class StatisticalReportBase(BaseModel):
    report_name: str = Field(..., min_length=1, max_length=200)
    report_type: ReportType
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    fiscal_year: Optional[int] = Field(None, ge=2000, le=2100)
    branch_id: Optional[int] = None
    branch_location: Optional[str] = None
    includes_all_branches: bool = True
    report_parameters: Optional[Dict[str, Any]] = None
    included_statistics: Optional[List[str]] = None
    notes: Optional[str] = None


class StatisticalReportCreate(StrictInputSchema, StatisticalReportBase):
    file_format: ExportFormat = ExportFormat.PDF


class StatisticalReportResponse(StatisticalReportBase):
    id: int
    status: ReportStatus
    file_format: Optional[str] = None
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    generated_by_id: Optional[int] = None
    generated_at: Optional[datetime] = None
    download_count: int = 0
    last_downloaded_at: Optional[datetime] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Settings
# ============================================================================


class UsageStatisticsSettingsBase(BaseModel):
    branch_id: Optional[int] = None
    branch_location: Optional[str] = None
    auto_generate_daily: bool = True
    auto_generate_weekly: bool = True
    auto_generate_monthly: bool = True
    auto_generate_yearly: bool = True
    fiscal_year_start_month: int = Field(7, ge=1, le=12)
    legal_service_area_population: Optional[int] = Field(None, ge=0)
    population_data_year: Optional[int] = Field(None, ge=2000, le=2100)
    door_counter_enabled: bool = False
    door_counter_adjustment_factor: float = 1.0
    reference_sampling_enabled: bool = False
    reference_sample_weeks: Optional[List[int]] = None  # Week numbers
    reference_extrapolation_factor: Optional[float] = None
    imls_library_id: Optional[str] = Field(None, max_length=50)
    state_library_id: Optional[str] = Field(None, max_length=50)


class UsageStatisticsSettingsCreate(StrictInputSchema, UsageStatisticsSettingsBase):
    pass


class UsageStatisticsSettingsUpdate(StrictInputSchema):
    auto_generate_daily: Optional[bool] = None
    auto_generate_weekly: Optional[bool] = None
    auto_generate_monthly: Optional[bool] = None
    auto_generate_yearly: Optional[bool] = None
    fiscal_year_start_month: Optional[int] = Field(None, ge=1, le=12)
    legal_service_area_population: Optional[int] = Field(None, ge=0)
    population_data_year: Optional[int] = Field(None, ge=2000, le=2100)
    door_counter_enabled: Optional[bool] = None
    door_counter_adjustment_factor: Optional[float] = None
    reference_sampling_enabled: Optional[bool] = None
    reference_sample_weeks: Optional[List[int]] = None
    reference_extrapolation_factor: Optional[float] = None
    imls_library_id: Optional[str] = Field(None, max_length=50)
    state_library_id: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class UsageStatisticsSettingsResponse(UsageStatisticsSettingsBase):
    id: int
    is_active: bool
    created_by_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Trend Analysis
# ============================================================================


class TrendDataPoint(BaseModel):
    period: str  # ISO date or period label
    value: float
    previous_value: Optional[float] = None
    change_percent: Optional[float] = None


class TrendAnalysis(BaseModel):
    metric_name: str
    data_points: List[TrendDataPoint]
    overall_trend: str  # "up", "down", "stable"
    avg_change_percent: float
    period_type: PeriodType


class MonthOverMonthTrend(BaseModel):
    metric: str
    current_month: date
    current_value: float
    previous_month: date
    previous_value: float
    change_percent: float
    trend_direction: str


class YearOverYearTrend(BaseModel):
    metric: str
    current_year: int
    current_value: float
    previous_year: int
    previous_value: float
    change_percent: float
    trend_direction: str


# ============================================================================
# Dashboard / Summary
# ============================================================================


class UsageStatisticsDashboard(BaseModel):
    circulation: CirculationStatisticsSummary
    collection: CollectionStatisticsSummary
    patrons: PatronStatisticsSummary
    programs: ProgramStatisticsSummary
    computer_usage: ComputerUsageSummary
    reference: ReferenceStatisticsSummary
    visits: VisitStatisticsSummary
    generated_at: datetime


class IMLSSurveyData(BaseModel):
    fiscal_year: int
    library_fscs_id: str

    # AE - Service Area
    service_area_population: int

    # Collection
    print_collection: int
    ebook_collection: int
    audio_physical: int
    audio_downloadable: int
    video_physical: int
    video_downloadable: int

    # Circulation
    physical_circulation: int
    electronic_circulation: int
    total_circulation: int

    # Programs
    childrens_programs: int
    childrens_program_attendance: int
    young_adult_programs: int
    young_adult_program_attendance: int
    total_programs: int
    total_program_attendance: int

    # Reference
    reference_transactions: int

    # Visits
    library_visits: int

    # Computer Use
    computer_uses: int

    # Registered Users
    registered_borrowers: int

    # Interlibrary Loans
    items_loaned: int
    items_borrowed: int

    generated_at: datetime


# ============================================================================
# Export/Import
# ============================================================================


class StatisticsExportRequest(StrictInputSchema):
    statistics_types: List[str] = Field(
        ...,
        description="Types of statistics to export",
        examples=[["circulation", "collection", "patron", "program"]]
    )
    period_start: date
    period_end: date
    branch_id: Optional[int] = None
    branch_location: Optional[str] = None
    format: ExportFormat = ExportFormat.XLSX
    include_trends: bool = True
    include_peer_comparison: bool = False


class PeerDataImportRequest(StrictInputSchema):
    file_format: str = Field(..., pattern="^(csv|xlsx)$")
    data_year: int = Field(..., ge=2000, le=2100)
    update_existing: bool = False  # Update if library already exists


class PeerDataImportResult(BaseModel):
    libraries_created: int
    libraries_updated: int
    data_records_created: int
    errors: List[str]
    warnings: List[str]
