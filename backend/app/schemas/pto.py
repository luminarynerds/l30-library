# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from typing import Optional, List, Dict, Any, ClassVar
from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema

from app.models.pto import PTOType, PTORequestStatus


class PTORequestCreate(StrictInputSchema):
    start_date: date
    end_date: date
    pto_type: PTOType = PTOType.VACATION
    reason: Optional[str] = None
    coverage_notes: Optional[str] = None
    delegation_notes: Optional[str] = None
    auto_delegate: bool = False
    gradual_return_enabled: bool = True


class PTORequestUpdate(StrictInputSchema):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None
    delegation_notes: Optional[str] = None
    auto_delegate: Optional[bool] = None


class PTORequestResponse(BaseModel):
    id: int
    user_id: int
    start_date: date
    end_date: date
    pto_type: PTOType
    status: PTORequestStatus
    reason: Optional[str] = None
    coverage_notes: Optional[str] = None
    number_of_days: int
    delegation_notes: Optional[str] = None
    auto_delegate: bool
    coverage_manager_assigned: Optional[int] = None
    approved_by: Optional[int] = None
    approval_date: Optional[datetime] = None
    denial_reason: Optional[str] = None
    gradual_return_enabled: bool
    return_inbox_date: Optional[date] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # These columns are nullable in the DB but declared non-null here; rows hold
    # NULL, which from_attributes hands pydantic as an explicit None and the
    # response 500s. Coerce None back to each field's intended default.
    _NULL_DEFAULTS: ClassVar[dict] = {
        "auto_delegate": False,
        "gradual_return_enabled": True,
    }

    @field_validator("auto_delegate", "gradual_return_enabled", mode="before")
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v

    class Config:
        from_attributes = True


class PTOBalanceResponse(BaseModel):
    id: int
    user_id: int
    pto_type: PTOType
    annual_allotment: float
    accrued_days: float
    used_days: float
    pending_days: float
    carryover_days: float
    carryover_limit: float
    year: int
    last_accrual_date: Optional[datetime] = None
    last_updated: datetime

    class Config:
        from_attributes = True


class PTOApprovalRequest(StrictInputSchema):
    notes: Optional[str] = Field(None, description="Approval notes or denial reason")
    coverage_assessment: Optional[str] = Field(None, description="Coverage assessment or concerns")


class PTOReminderResponse(BaseModel):
    id: int
    user_id: int
    pto_type: PTOType
    days_available: float
    reminder_type: str
    message: str
    sent_at: datetime
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PTOVacationCelebrationResponse(BaseModel):
    id: int
    pto_request_id: int
    celebration_message: str
    celebration_sent_at: Optional[datetime] = None
    team_notified: bool
    welcome_back_message: Optional[str] = None
    welcome_back_sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PTODelegationResponse(BaseModel):
    pto_request_id: int
    user_id: int
    start_date: date
    end_date: date
    auto_delegate_enabled: bool
    delegation_notes: Optional[str] = None
    coverage_manager: Optional[int] = None
    coverage_notes: str


class PTOInboxReturnResponse(BaseModel):
    enabled: bool
    return_date: Optional[date] = None
    phases: Optional[List[Dict[str, Any]]] = None


class PTOStatsResponse(BaseModel):
    total_pto_requests: int
    approved_count: int
    pending_count: int
    denied_count: int
    team_on_pto: List[Dict[str, Any]]
    upcoming_pto: List[PTORequestResponse]


# =============================================================================
# PTO Promotion Schemas
# =============================================================================


class PTOPromotionBalanceItem(BaseModel):
    pto_type: str
    available_days: float
    accrued_days: float
    used_days: float
    pending_days: float


class PTOPromotionUpcomingVacation(BaseModel):
    start_date: date
    end_date: date
    days: int
    type: str


class PTOPromotionReminder(BaseModel):
    type: str
    message: str
    sent_at: datetime
    read_at: Optional[datetime] = None


class PTOPromotionDashboardResponse(BaseModel):
    user_id: int
    pto_balances: List[PTOPromotionBalanceItem]
    upcoming_vacation: Optional[PTOPromotionUpcomingVacation] = None
    reminders: List[PTOPromotionReminder]
    promotion_message: str


class PTOPromotionTriageItem(BaseModel):
    task: str
    priority: str
    description: str


class PTOPromotionTriageResponse(BaseModel):
    pto_request_id: int
    user_id: int
    days_until_vacation: int
    vacation_start: date
    vacation_end: date
    duration_days: int
    triage_checklist: List[PTOPromotionTriageItem]
    message: str


class PTOPromotionPhase(BaseModel):
    phase: int
    date: date
    focus: str
    percentage: int
    description: str


class PTOPromotionGradualReturnResponse(BaseModel):
    enabled: bool
    vacation_end: Optional[date] = None
    return_date: Optional[date] = None
    message: Optional[str] = None
    phases: Optional[List[PTOPromotionPhase]] = None
