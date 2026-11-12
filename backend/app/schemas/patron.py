# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from ..models.user import UserRole


class PatronResponse(BaseModel):

    id: int
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    library_card: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    email_verified: bool
    track_reading_history: bool
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None
    # Login tracking
    last_login: Optional[datetime] = None
    # COPPA fields
    date_of_birth: Optional[date] = None
    parental_consent_given: bool = False
    # Enhanced patron fields
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    language_preference: Optional[str] = None
    accessibility_needs: Optional[str] = None
    patron_type: Optional[str] = None
    custom_fields: Optional[str] = None
    photo_url: Optional[str] = None
    # Onboarding fields
    onboarding_completed_at: Optional[datetime] = None
    onboarding_skipped: bool = False
    home_branch_id: Optional[int] = None
    # UI Preferences
    ui_mode: str = Field(default='full', description='UI preference: essentials or full')

    class Config:
        from_attributes = True
