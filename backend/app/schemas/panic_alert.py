# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema

SoundPreset = Literal[
    "gentle_chime", "soft_pulse", "warble", "two_tone", "urgent_siren"
]

from ..models.panic_alert import PanicAlertSource, PanicAlertStatus


class PanicAlertCreate(StrictInputSchema):

    activation_source: PanicAlertSource = Field(
        default=PanicAlertSource.KEYBOARD_SHORTCUT, description="How the alert was activated"
    )
    situation_notes: Optional[str] = Field(None, max_length=500)
    metadata: Optional[dict] = Field(None, description="Device info, location data, etc.")


class PanicAlertUpdate(StrictInputSchema):

    status: PanicAlertStatus
    resolution_notes: Optional[str] = Field(None, max_length=500)


class PanicAlertResponse(BaseModel):

    id: int
    triggered_by_user_id: int
    branch_id: Optional[int]
    activation_source: PanicAlertSource
    status: PanicAlertStatus

    situation_notes: Optional[str]

    acknowledged_by_user_id: Optional[int]
    acknowledged_at: Optional[datetime]

    resolution_notes: Optional[str]
    resolved_at: Optional[datetime]

    metadata: Optional[dict] = Field(None, alias="alert_metadata")

    created_at: datetime | None = None
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
        populate_by_name = True


class PanicAlertDetailedResponse(PanicAlertResponse):
    responders: list[Any] = []


class PanicAlertListResponse(BaseModel):

    id: int
    triggered_by_user_id: int
    branch_id: Optional[int]
    activation_source: PanicAlertSource
    status: PanicAlertStatus

    created_at: datetime | None = None
    class Config:
        from_attributes = True


class PanicAlertNotificationPreferencesCreate(StrictInputSchema):

    receive_panic_alerts: bool = True
    notify_via_email: bool = False
    notify_via_sms: bool = False
    notify_via_in_app: bool = True

    notify_for_all_branches: bool = True
    branch_ids: Optional[list[int]] = None

    sound_enabled: bool = False
    sound_preference: SoundPreset = Field(
        default="gentle_chime",
        description="Alarm tone preset to play.",
    )
    vibration_enabled: bool = True


class PanicAlertNotificationPreferencesResponse(BaseModel):

    id: int
    user_id: int

    receive_panic_alerts: bool
    notify_via_email: bool
    notify_via_sms: bool
    notify_via_in_app: bool

    notify_for_all_branches: bool
    branch_ids: Optional[list[int]]

    sound_enabled: bool
    sound_preference: SoundPreset = "gentle_chime"
    vibration_enabled: bool

    class Config:
        from_attributes = True


class PanicAlertHistoryResponse(BaseModel):

    id: int
    panic_alert_id: int
    action: str
    performed_by_user_id: Optional[int]
    old_status: Optional[str]
    new_status: Optional[str]
    notes: Optional[str]
    metadata: Optional[dict] = Field(None, alias="action_metadata")
    created_at: datetime | None = None
    class Config:
        from_attributes = True
        populate_by_name = True


class PanicAlertTimelineResponse(BaseModel):

    alert_id: int
    entries: list[PanicAlertHistoryResponse]

    class Config:
        from_attributes = True


class PanicAlertStatsResponse(BaseModel):

    total_alerts: int
    active_alerts: int
    acknowledged_alerts: int
    resolved_alerts: int
    cancelled_alerts: int
    average_response_time_minutes: Optional[float]
    false_alert_rate: Optional[float]
    most_common_situations: list[dict]
    alerts_by_branch: list[dict]
    alerts_by_time_of_day: list[dict]

    class Config:
        from_attributes = True


class BulkAcknowledgeRequest(StrictInputSchema):

    alert_ids: list[int] = Field(..., min_length=1, max_length=100, description="List of alert IDs to acknowledge")


class BulkAcknowledgeResponse(BaseModel):

    acknowledged_count: int
    failed_ids: list[int]
    errors: dict[int, str]

    class Config:
        from_attributes = True
