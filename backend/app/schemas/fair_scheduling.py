# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, time
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import MoneyDecimal, StrictInputSchema


# =============================================================================
# Enums
# =============================================================================

class ScheduleGenerationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    TIMEOUT = "timeout"
    FAILED = "failed"


class FatigueLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class CalloutStatus(StrEnum):
    OPEN = "open"
    SEARCHING = "searching"
    COVERED = "covered"
    PARTIAL = "partial"
    UNCOVERED = "uncovered"
    CANCELLED = "cancelled"


class CalloutUrgency(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class PayrollExportStatus(StrEnum):
    PENDING = "pending"
    EXPORTED = "exported"
    CONFIRMED = "confirmed"
    ERROR = "error"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    TEMPORARY = "temporary"
    SEASONAL = "seasonal"


# =============================================================================
# Schedule Generation (Constraint Solver)
# =============================================================================

class ScheduleGenerationCreate(StrictInputSchema):
    branch_id: int
    period_start: date
    period_end: date
    solver_config: Optional[Dict[str, Any]] = None


class ScheduleGenerationResponse(BaseModel):
    id: int
    branch_id: int
    period_start: date
    period_end: date
    status: ScheduleGenerationStatus
    objective_value: Optional[float]
    solve_time_seconds: Optional[float]
    total_shifts_assigned: int
    total_violations: int
    fairness_score: Optional[float]
    constraint_summary: Optional[Dict[str, Any]]
    is_published: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class SchedulePublishRequest(StrictInputSchema):
    generation_id: int


# =============================================================================
# Schedule Explanations (Transparency)
# =============================================================================

class ScheduleExplanationResponse(BaseModel):
    id: int
    generation_id: int
    shift_id: int
    staff_id: int
    explanation_type: str
    explanation_text: str
    contributing_factors: List[Dict[str, Any]]
    fairness_impact: float
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class StaffScheduleExplanation(BaseModel):
    staff_id: int
    staff_name: str
    total_shifts: int
    total_hours: float
    fairness_score: float
    explanations: List[ScheduleExplanationResponse]
    preference_honor_rate: float
    top_factors: List[str]


# =============================================================================
# Preference Learning
# =============================================================================

class LearnedPreferenceResponse(BaseModel):
    id: int
    staff_id: int
    preference_category: str
    preference_value: str
    preference_strength: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[Dict[str, Any]]
    sample_size: int
    is_confirmed: Optional[bool]
    confirmed_at: Optional[datetime]
    calculated_at: datetime

    class Config:
        from_attributes = True


class PreferenceLearningRequest(StrictInputSchema):
    staff_id: int
    lookback_days: int = Field(default=180, ge=30, le=365)


class PreferenceConfirmRequest(StrictInputSchema):
    confirmed: bool


class StaffPreferenceSummary(BaseModel):
    staff_id: int
    staff_name: str
    total_preferences: int
    confirmed_count: int
    top_likes: List[Dict[str, Any]]
    top_dislikes: List[Dict[str, Any]]
    last_updated: Optional[datetime]


# =============================================================================
# Call-Out Coverage
# =============================================================================

class CalloutCreateRequest(StrictInputSchema):
    branch_id: int
    shift_id: int
    callout_staff_id: int
    callout_reason: Optional[str] = None


class CalloutCoverageResponse(BaseModel):
    id: int
    branch_id: int
    original_shift_id: int
    callout_staff_id: int
    callout_reason: Optional[str]
    callout_time: datetime
    shift_date: date
    shift_start: time
    shift_end: time
    status: CalloutStatus
    urgency: CalloutUrgency
    staff_contacted: List[Dict[str, Any]]
    staff_contacted_count: int
    covering_staff_id: Optional[int]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class CoverageCandidate(BaseModel):
    staff_id: int
    name: str
    score: float
    factors: List[str]
    employment_type: str
    weekly_hours: float
    headroom: float


class CoverageAssignRequest(StrictInputSchema):
    covering_staff_id: int
    notes: Optional[str] = None


class CoverageResponseRecord(BaseModel):
    staff_id: int
    response: str = Field(description="accepted, declined, no_response")
    reason: Optional[str] = None


# =============================================================================
# Exhaustion / Fatigue Tracking
# =============================================================================

class FatigueRecordResponse(BaseModel):
    id: int
    staff_id: int
    record_date: date
    fatigue_level: FatigueLevel
    fatigue_score: float
    consecutive_days_worked: int
    hours_last_7_days: float
    hours_last_14_days: float
    closing_shifts_last_7_days: int
    short_turnarounds_last_14_days: int
    overtime_hours_last_30_days: float
    days_since_last_day_off: int
    weekend_shifts_last_30_days: int
    fatigue_trend: Optional[str]
    alert_triggered: bool
    alert_message: Optional[str]
    calculated_at: datetime

    class Config:
        from_attributes = True


class TeamFatigueResponse(BaseModel):
    branch_id: int
    as_of_date: date
    staff_fatigue: List[Dict[str, Any]]
    critical_count: int
    high_count: int
    moderate_count: int
    low_count: int
    average_score: float


# =============================================================================
# Payroll Integration
# =============================================================================

class PayrollRecordResponse(BaseModel):
    id: int
    staff_id: int
    shift_id: int
    pay_period_start: date
    pay_period_end: date
    regular_hours: float
    overtime_hours: float
    holiday_hours: float
    weekend_differential_hours: float
    evening_differential_hours: float
    overtime_multiplier: float
    holiday_multiplier: float
    weekend_differential: float
    evening_differential: float
    scheduled_hours: float
    actual_hours: Optional[float]
    discrepancy_notes: Optional[str]
    export_status: PayrollExportStatus
    is_approved: bool

    class Config:
        from_attributes = True


class PayrollExportRequest(StrictInputSchema):
    branch_id: Optional[int] = None
    pay_period_start: date
    pay_period_end: date
    export_format: str = Field(default="csv", pattern="^(csv|json|adp|paychex)$")


class PayrollExportResponse(BaseModel):
    batch_id: str
    export_status: PayrollExportStatus
    total_records: int
    total_regular_hours: float
    total_overtime_hours: float
    total_holiday_hours: float
    export_format: str
    exported_at: Optional[datetime]
    error_message: Optional[str]


class PayrollSummaryResponse(BaseModel):
    pay_period_start: str
    pay_period_end: str
    total_records: int
    total_regular_hours: float
    total_overtime_hours: float
    total_holiday_hours: float
    staff_details: List[Dict[str, Any]]
    records_with_discrepancy: int
    pending_approval: int
    # Preflight: period punches not covered by any qualifying shift
    uncovered_punches: List[Dict[str, Any]] = []


class PayrollApproveRequest(StrictInputSchema):
    pay_period_start: date
    pay_period_end: date
    staff_id: Optional[int] = None


class PayrollPolicyResponse(BaseModel):
    overtime_multiplier: float
    holiday_multiplier: float
    weekend_differential: float
    evening_differential: float
    default_ot_threshold_hours: float
    evening_start_local: time
    updated_by_id: Optional[int]
    updated_at: datetime

    class Config:
        from_attributes = True


class PayrollPolicyUpdate(StrictInputSchema):
    # Decimal (not float) so values bind cleanly to the NUMERIC columns.
    overtime_multiplier: Optional[MoneyDecimal] = Field(default=None, ge=Decimal("1.00"), le=Decimal("3.00"))
    holiday_multiplier: Optional[MoneyDecimal] = Field(default=None, ge=Decimal("1.00"), le=Decimal("3.00"))
    weekend_differential: Optional[MoneyDecimal] = Field(default=None, ge=Decimal("1.00"), le=Decimal("2.00"))
    evening_differential: Optional[MoneyDecimal] = Field(default=None, ge=Decimal("1.00"), le=Decimal("2.00"))
    default_ot_threshold_hours: Optional[MoneyDecimal] = Field(default=None, ge=Decimal("20.0"), le=Decimal("60.0"))
    evening_start_local: Optional[time] = None

    @field_validator("evening_start_local")
    @classmethod
    def _evening_start_in_window(cls, v: Optional[time]) -> Optional[time]:
        if v is not None and not (time(16, 0) <= v <= time(22, 0)):
            raise ValueError("evening_start_local must be between 16:00 and 22:00")
        return v


# =============================================================================
# Staff Scheduling Profile
# =============================================================================

class StaffSchedulingProfileCreate(StrictInputSchema):
    staff_id: int
    branch_id: Optional[int] = None
    employment_type: EmploymentType
    contracted_hours_per_week: float = Field(ge=0, le=60)
    min_hours_per_week: float = Field(ge=0, le=60)
    max_hours_per_week: float = Field(ge=0, le=60)
    skills: List[str] = []
    hire_date: Optional[date] = None
    seniority_level: int = Field(default=1, ge=1, le=20)
    max_consecutive_days: int = Field(default=5, ge=1, le=7)
    min_hours_between_shifts: float = Field(default=10.0, ge=8.0, le=24.0)
    max_weekend_shifts_per_month: int = Field(default=4, ge=0, le=10)
    max_closing_shifts_per_week: int = Field(default=3, ge=0, le=7)


class StaffSchedulingProfileUpdate(StrictInputSchema):
    employment_type: Optional[EmploymentType] = None
    contracted_hours_per_week: Optional[float] = None
    min_hours_per_week: Optional[float] = None
    max_hours_per_week: Optional[float] = None
    skills: Optional[List[str]] = None
    hire_date: Optional[date] = None
    seniority_level: Optional[int] = None
    max_consecutive_days: Optional[int] = None
    min_hours_between_shifts: Optional[float] = None
    max_weekend_shifts_per_month: Optional[int] = None
    max_closing_shifts_per_week: Optional[int] = None
    is_active: Optional[bool] = None


class StaffSchedulingProfileResponse(BaseModel):
    id: int
    staff_id: int
    branch_id: Optional[int]
    employment_type: EmploymentType
    contracted_hours_per_week: float
    min_hours_per_week: float
    max_hours_per_week: float
    skills: List[str]
    hire_date: Optional[date]
    seniority_level: int
    max_consecutive_days: int
    min_hours_between_shifts: float
    max_weekend_shifts_per_month: int
    max_closing_shifts_per_week: int
    desirable_shift_score: float
    is_active: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# =============================================================================
# Dashboard
# =============================================================================

class FairSchedulingDashboardResponse(BaseModel):
    # Current period overview
    current_generation: Optional[ScheduleGenerationResponse]
    overall_fairness_score: float

    # Staff fairness breakdown
    staff_fairness: List[Dict[str, Any]]

    # Fatigue overview
    fatigue_summary: Dict[str, Any]

    # Open call-outs
    open_callouts: List[CalloutCoverageResponse]

    # Preference insights
    preference_insights: Dict[str, Any]

    # Payroll status
    payroll_status: Dict[str, Any]

    # Upcoming schedule highlights
    upcoming_highlights: List[Dict[str, Any]]


# =============================================================================
# My Shifts (per-staff dashboard tile)
# =============================================================================

class MyShiftResponse(BaseModel):
    shift_id: int
    branch_id: int
    shift_date: date
    shift_type: str
    status: str
    scheduled_start: time
    scheduled_end: time
    scheduled_hours: float
    is_holiday: bool
    is_weekend: bool
    has_open_swap: bool = False
    has_open_callout: bool = False

    class Config:
        from_attributes = True


class MyShiftsResponse(BaseModel):
    shifts: List[MyShiftResponse]
    range_start: date
    range_end: date
