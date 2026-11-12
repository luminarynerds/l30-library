# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas._base import StrictInputSchema


# --- 2FA ---

class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_image: str
    message: str = "Scan the QR code with your authenticator app, then confirm with a code."


class TwoFactorConfirmRequest(StrictInputSchema):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TwoFactorConfirmResponse(BaseModel):
    recovery_codes: list[str]
    message: str = "Two-factor authentication is now active. Save your recovery codes."


class TwoFactorDisableRequest(StrictInputSchema):
    password: str
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TwoFactorVerifyRequest(StrictInputSchema):
    pending_token: str
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    trust_device: bool = False
    turnstile_token: str | None = None


class TwoFactorRecoveryRequest(StrictInputSchema):
    pending_token: str
    recovery_code: str = Field(..., min_length=4, max_length=12)
    turnstile_token: str | None = None


class TwoFactorLoginResponse(BaseModel):
    requires_2fa: bool = True
    pending_token: str
    message: str = "Please enter your two-factor authentication code."


class RecoveryCodesRegenerateRequest(StrictInputSchema):
    password: str
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class RecoveryCodesResponse(BaseModel):
    recovery_codes: list[str]
    message: str = "New recovery codes generated. Save them."


class RecoveryCodesCountResponse(BaseModel):
    total: int = 8
    remaining: int


# --- Recovery Email ---

class RecoveryEmailRequest(StrictInputSchema):
    email: EmailStr


class RecoveryEmailVerifyRequest(StrictInputSchema):
    token: str


class RecoveryEmailResponse(BaseModel):
    recovery_email: Optional[str] = None
    verified: bool = False
    message: str


# --- Security Alerts ---

class SecurityAlertPreferences(BaseModel):
    security_alert_new_login: bool = True
    security_alert_changes: bool = True


# --- Security Activity ---

class SecurityActivityItem(BaseModel):
    action: str
    action_label: str
    timestamp: datetime
    ip_address: Optional[str] = None
    device: Optional[str] = None
    status: str  # "success", "failed", "blocked", "change"

    class Config:
        from_attributes = True


class SecurityActivityResponse(BaseModel):
    items: list[SecurityActivityItem]
    total: int
    page: int
    per_page: int


# --- Security Overview ---

class SecurityOverview(BaseModel):
    totp_enabled: bool = False
    totp_confirmed_at: Optional[datetime] = None
    recovery_email_set: bool = False
    recovery_email_verified: bool = False
    recovery_codes_remaining: int = 0
    recovery_codes_total: int = 8
    security_alert_new_login: bool = True
    security_alert_changes: bool = True
    active_sessions_count: int = 0
    known_devices_count: int = 0
    has_stripe_connected: bool = False  # Placeholder for Stripe Connect integration


# --- Known Devices ---

class KnownDeviceResponse(BaseModel):
    id: int
    friendly_name: Optional[str] = None
    ip_address: Optional[str] = None
    first_seen_at: datetime
    last_seen_at: datetime
    is_trusted: bool = False

    class Config:
        from_attributes = True
