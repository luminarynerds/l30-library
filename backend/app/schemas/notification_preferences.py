# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from pydantic import BaseModel

from app.schemas._base import StrictInputSchema
from typing import List, Optional
from datetime import time


class NotificationChannelPreference(BaseModel):
    notification_type: str
    label: str
    description: Optional[str] = None
    channel_email: bool = True
    channel_in_app: bool = True
    channel_sms: bool = False
    is_digest: bool = False


class NotificationPreferencesResponse(BaseModel):
    preferences: List[NotificationChannelPreference] = []


class UpdateNotificationPreferencesRequest(StrictInputSchema):
    preferences: List[NotificationChannelPreference]


class DigestConfig(BaseModel):
    enabled: bool = False
    frequency: str = "daily"  # 'daily' | 'weekly'
    preferred_time: Optional[str] = "09:00"
    preferred_day: Optional[int] = 0  # 0=Monday, for weekly


class QuietHoursConfig(BaseModel):
    enabled: bool = False
    start_time: Optional[str] = "22:00"
    end_time: Optional[str] = "08:00"
    days: List[int] = [0, 1, 2, 3, 4, 5, 6]  # All days by default


class FullNotificationSettings(BaseModel):
    preferences: List[NotificationChannelPreference] = []
    digest: DigestConfig = DigestConfig()
    quiet_hours: QuietHoursConfig = QuietHoursConfig()
