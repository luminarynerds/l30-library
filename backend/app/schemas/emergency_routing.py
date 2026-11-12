# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, validator

from app.schemas._base import StrictInputSchema

from ..models.emergency_routing import (
    BuildingStatus, IncidentType, IncidentSeverity, ResponseType,
    ContactType, FollowUpStatus
)


# ============================================================================
# Building Status Schemas
# ============================================================================


class BuildingStatusUpdate(StrictInputSchema):
    status: BuildingStatus = Field(
        ...,
        description="New building status (open, closing, closed, emergency)"
    )
    reason: Optional[str] = Field(
        None,
        description="Reason for status change"
    )

    class Config:
        from_attributes = True


class BuildingStatusLogResponse(BaseModel):
    id: int
    status: BuildingStatus
    changed_by_id: Optional[int] = None
    reason: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class BuildingStatusQueryResponse(BaseModel):
    current_status: BuildingStatus
    # No status log exists until the first building-status change, and the
    # handler passes None for status_changed_at in that case. It's a timestamp
    # with no meaningful default, so it's genuinely nullable here.
    status_changed_at: Optional[datetime] = None
    changed_by_id: Optional[int] = None
    recent_history: List[BuildingStatusLogResponse] = Field(
        default_factory=list,
        description="Last 5 status changes"
    )

    class Config:
        from_attributes = True


# ============================================================================
# Emergency Contact Schemas
# ============================================================================


class EmergencyContactCreate(StrictInputSchema):
    contact_type: ContactType
    name: str = Field(..., min_length=1, max_length=255)
    phone_number: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=100)
    organization: Optional[str] = Field(None, max_length=255)
    user_id: Optional[int] = None
    is_active: bool = True
    available_24h: bool = False
    escalation_level: int = Field(default=1, ge=1, le=10)
    notes: Optional[str] = None
    external_system_id: Optional[str] = Field(None, max_length=100)

    class Config:
        from_attributes = True


class EmergencyContactUpdate(StrictInputSchema):
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    available_24h: Optional[bool] = None
    escalation_level: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class EmergencyContactResponse(BaseModel):
    id: int
    contact_type: ContactType
    name: str
    phone_number: str
    email: Optional[str] = None
    title: Optional[str] = None
    organization: Optional[str] = None
    user_id: Optional[int] = None
    is_active: bool
    available_24h: bool
    escalation_level: int
    notes: Optional[str] = None
    external_system_id: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# On-Call Schedule Schemas
# ============================================================================


class OnCallScheduleCreate(StrictInputSchema):
    manager_id: int
    start_date: datetime
    end_date: datetime
    escalation_level: int = Field(default=1, ge=1, le=10)
    phone_override: Optional[str] = Field(None, max_length=20)
    email_override: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None

    @validator('end_date')
    def end_after_start(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

    class Config:
        from_attributes = True


class OnCallScheduleResponse(BaseModel):
    id: int
    manager_id: int
    start_date: datetime
    end_date: datetime
    escalation_level: int
    phone_override: Optional[str] = None
    email_override: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class CurrentOnCallManager(BaseModel):
    schedule_id: int
    manager_id: int
    manager_name: str
    escalation_level: int
    phone: str
    email: Optional[str] = None
    phone_override: Optional[str] = None
    email_override: Optional[str] = None
    is_available: bool = True

    class Config:
        from_attributes = True


# ============================================================================
# Emergency Incident Schemas
# ============================================================================


class EmergencyIncidentCreate(StrictInputSchema):
    incident_type: IncidentType
    severity: IncidentSeverity
    location_description: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    reporter_name: Optional[str] = Field(None, max_length=255)
    reporter_contact: Optional[str] = Field(None, max_length=255)
    camera_footage_available: bool = False
    camera_footage_urls: List[str] = Field(default_factory=list)
    alarm_triggered: bool = False
    alarm_panel_id: Optional[str] = Field(None, max_length=100)
    doors_unlocked_count: int = Field(default=0, ge=0)
    door_status_details: Optional[Dict[str, Any]] = None
    additional_details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class EmergencyIncidentUpdate(StrictInputSchema):
    severity: Optional[IncidentSeverity] = None
    location_description: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    camera_footage_available: Optional[bool] = None
    camera_footage_urls: Optional[List[str]] = None
    alarm_triggered: Optional[bool] = None
    doors_unlocked_count: Optional[int] = Field(None, ge=0)
    door_status_details: Optional[Dict[str, Any]] = None
    resolved: Optional[bool] = None
    resolution_notes: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class EmergencyIncidentResponse(BaseModel):
    id: int
    incident_type: IncidentType
    severity: IncidentSeverity
    response_type: ResponseType
    location_description: Optional[str] = None
    building_status_at_incident: Optional[BuildingStatus] = None
    reported_by_id: Optional[int] = None
    reporter_name: Optional[str] = None
    reporter_contact: Optional[str] = None
    description: str
    camera_footage_available: bool
    camera_footage_urls: List[str]
    alarm_triggered: bool
    alarm_panel_id: Optional[str] = None
    doors_unlocked_count: int
    response_initiated: bool
    response_initiated_at: Optional[datetime] = None
    resolved: bool
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class EmergencyIncidentListResponse(BaseModel):
    id: int
    incident_type: IncidentType
    severity: IncidentSeverity
    response_type: ResponseType
    location_description: Optional[str] = None
    resolved: bool
    created_at: datetime | None = None
    reporter_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Emergency Notification Schemas
# ============================================================================


class EmergencyNotificationCreate(StrictInputSchema):
    incident_id: int
    contact_id: Optional[int] = None
    recipient_name: str = Field(..., max_length=255)
    recipient_phone: Optional[str] = Field(None, max_length=20)
    recipient_email: Optional[str] = Field(None, max_length=255)
    notification_type: str = Field(default="sms", description="sms, call, email")
    notification_body: Optional[str] = None

    class Config:
        from_attributes = True


class EmergencyNotificationResponse(BaseModel):
    id: int
    incident_id: int
    recipient_name: str
    recipient_phone: Optional[str] = None
    recipient_email: Optional[str] = None
    notification_type: Optional[str] = None
    sent_successfully: bool
    sent_at: Optional[datetime] = None
    delivery_error: Optional[str] = None
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    response_notes: Optional[str] = None
    retry_count: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Incident Follow-Up Schemas
# ============================================================================


class IncidentFollowUpCreate(StrictInputSchema):
    incident_id: int
    task_description: str = Field(..., min_length=10)
    task_category: Optional[str] = Field(None, max_length=50)
    assigned_to_id: Optional[int] = None
    due_date: Optional[datetime] = None
    priority: int = Field(default=1, ge=1, le=3)
    estimated_hours: Optional[float] = Field(None, ge=0)

    class Config:
        from_attributes = True


class IncidentFollowUpUpdate(StrictInputSchema):
    task_description: Optional[str] = Field(None, min_length=10)
    assigned_to_id: Optional[int] = None
    status: Optional[FollowUpStatus] = None
    due_date: Optional[datetime] = None
    completion_notes: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    actual_hours: Optional[float] = Field(None, ge=0)

    class Config:
        from_attributes = True


class IncidentFollowUpResponse(BaseModel):
    id: int
    incident_id: int
    task_description: str
    task_category: Optional[str] = None
    assigned_to_id: Optional[int] = None
    status: FollowUpStatus
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    priority: int
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# System Security Check Schemas
# ============================================================================


class SystemSecurityCheckCreate(StrictInputSchema):
    incident_id: Optional[int] = None
    all_doors_locked: bool = True
    cameras_operational: bool = True
    alarm_armed: bool = True
    alarm_triggered: bool = False
    door_status: Optional[Dict[str, Any]] = None
    camera_status: Optional[Dict[str, Any]] = None
    alarm_status_details: Optional[Dict[str, Any]] = None
    remote_access_available: bool = False
    camera_review_url: Optional[str] = Field(None, max_length=500)
    access_log_url: Optional[str] = Field(None, max_length=500)

    class Config:
        from_attributes = True


class SystemSecurityCheckResponse(BaseModel):
    id: int
    incident_id: Optional[int] = None
    all_doors_locked: bool
    cameras_operational: bool
    alarm_armed: bool
    alarm_triggered: bool
    door_status: Dict[str, Any]
    camera_status: Dict[str, Any]
    alarm_status_details: Dict[str, Any]
    verified_at: Optional[datetime] = None
    verified_by_id: Optional[int] = None
    remote_access_available: bool
    camera_review_url: Optional[str] = None
    access_log_url: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # These JSON columns are nullable in the DB (default {}, no NOT NULL); seeded
    # rows hold NULL, which from_attributes passes through as None and 500s the
    # response. Coerce None back to an empty dict at the boundary.
    @field_validator("door_status", "camera_status", "alarm_status_details", mode="before")
    @classmethod
    def _coerce_null_to_empty_dict(cls, v):
        if v is None:
            return {}
        return v

    class Config:
        from_attributes = True


# ============================================================================
# Summary Schemas
# ============================================================================


class EmergencyRoutingDashboard(BaseModel):
    current_building_status: BuildingStatus
    active_incidents_count: int
    unresolved_incidents_count: int
    pending_followups_count: int
    current_oncall_manager: Optional[CurrentOnCallManager] = None
    system_security_status: Optional[Dict[str, Any]] = None
    recent_incidents: List[EmergencyIncidentListResponse]

    class Config:
        from_attributes = True
