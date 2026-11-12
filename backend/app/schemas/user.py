# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# ──────────────────────────────────────────────────────────────────────────────
# Validation-Sync Report
# Frontend files that consume this schema's constraints:
#   - frontend/src/utils/inputLimits.ts        (FIRST_NAME_MAX, LAST_NAME_MAX, EMAIL_MAX, PASSWORD_MIN, PASSWORD_MAX, PHONE_MAX, ADDRESS_MAX)
#   - frontend/src/utils/authValidation.ts     (email regex, password min_length, phone regex/max)
#   - frontend/src/pages/RegisterPage.tsx       (first_name, last_name, email, password maxLength/minLength)
#   - frontend/src/pages/LoginPage.tsx          (email maxLength)
#   - frontend/src/components/AuthModals.tsx    (email, first_name, last_name, password maxLength)
#   - frontend/src/components/AddUserModal.tsx  (email, password maxLength)
#   - frontend/src/components/EditUserModal.tsx (user field constraints)
# ──────────────────────────────────────────────────────────────────────────────
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator, BeforeValidator

from ._base import MoneyDecimal, StrictInputSchema

from ..models.user import UserRole


# RFC 2606 reserves these TLDs for testing/documentation. The email-validator
# library rejects them by default, but real L30 prod data (seeded users,
# imported migrations) carries addresses on these TLDs. Bypass the strict
# check for any of them so response serialization doesn't 500.
_RFC2606_RESERVED_TLDS = (".test", ".example", ".invalid", ".localhost")


def validate_email_allow_test(value: str) -> str:
    import re
    from email_validator import validate_email, EmailNotValidError

    if not isinstance(value, str):
        raise ValueError("Invalid email: must be a string")

    lower = value.lower()
    if any(tld in lower for tld in _RFC2606_RESERVED_TLDS):
        # Do basic email format validation with regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValueError(f"Invalid email format: {value}")
        return lower

    try:
        # For non-reserved TLDs, use format validation only (no DNS deliverability check)
        validated = validate_email(value, check_deliverability=False)
        return validated.normalized
    except EmailNotValidError as e:
        raise ValueError(f"Invalid email: {e}") from e


# Custom email type that allows .test domains
TestableEmail = Annotated[str, BeforeValidator(validate_email_allow_test)]


class UserBase(BaseModel):
    email: TestableEmail
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(StrictInputSchema, UserBase):
    password: str
    phone: str | None = None
    address: str | None = None
    turnstile_token: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from ..core.security import PasswordValidationError
        from ..core.security import validate_password as core_validate_password

        try:
            core_validate_password(v)
        except PasswordValidationError as exc:
            raise ValueError(str(exc)) from exc
        return v


class UserUpdate(StrictInputSchema):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=500)
    track_reading_history: bool | None = None
    aggregate_recommendations_opt_out: bool | None = None
    # Enhanced patron fields
    emergency_contact_name: str | None = Field(None, max_length=200)
    emergency_contact_phone: str | None = Field(None, max_length=20)
    preferred_contact_method: str | None = Field(None, max_length=20)
    language_preference: str | None = Field(None, max_length=50)
    accessibility_needs: str | None = None
    pronouns: str | None = Field(None, max_length=50)
    patron_type: str | None = Field(None, max_length=20)
    custom_fields: str | None = None  # JSON string
    date_of_birth: date | None = None


class UserLogin(StrictInputSchema):
    email: TestableEmail
    password: str


class LoginRequest(StrictInputSchema):
    email: str | None = Field(None, description="Email address for login")
    username: str | None = Field(None, description="Username (alias for email, for backwards compatibility)")
    password: str = Field(..., description="User password")
    turnstile_token: str | None = Field(None, description="Cloudflare Turnstile token from frontend widget")

    @field_validator("email", "username", mode="before")
    @classmethod
    def validate_email_or_username(cls, v: str | None) -> str | None:
        if v is not None and isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v

    def get_login_identifier(self) -> str:
        identifier = self.email or self.username
        if not identifier:
            raise ValueError("Either email or username must be provided")
        return identifier


class UserResponse(BaseModel):
    id: int
    email: TestableEmail | None = None  # may be redacted by PII filter for low-clearance roles
    email_masked: str | None = None  # populated by PII filter when raw email is above the caller's clearance
    first_name: str
    last_name: str
    role: UserRole
    is_board_member: bool = False
    is_active: bool
    library_card: str | None
    phone: str | None
    address: str | None
    email_verified: bool
    track_reading_history: bool
    aggregate_recommendations_opt_out: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Login tracking
    last_login: datetime | None = None
    # COPPA fields (safe to expose to the user themselves)
    date_of_birth: date | None = None
    parental_consent_given: bool = False
    # GDPR fields (safe to expose to the user themselves)
    deletion_scheduled_for: datetime | None = None
    # Enhanced patron fields
    preferred_contact_method: str | None = None
    language_preference: str | None = None
    accessibility_needs: str | None = None
    patron_type: str | None = None
    photo_url: str | None = None
    # Onboarding fields
    onboarding_completed_at: datetime | None = None
    onboarding_skipped: bool = False
    home_branch_id: int | None = None
    # UI Preferences
    ui_mode: str = Field(default='full', description='UI preference: essentials or full')
    # Indie author info (if user is an indie author)
    pronouns: str | None = None
    # Temporary card fields
    card_type: str | None = None
    card_trial_expires_at: datetime | None = None
    # Circulation status fields (required for checkout guard)
    patron_status: str | None = None
    suspension_reason: str | None = None
    suspended_until: datetime | None = None
    card_expires_at: datetime | None = None
    # List-view aggregates (populated by staff patron list endpoint; 0 elsewhere)
    current_checkouts: int = 0
    current_holds: int = 0
    fines_balance: MoneyDecimal = Decimal("0.00")

    class Config:
        from_attributes = True


class UserAdminResponse(UserResponse):
    # Account security fields (admin-only)
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    # PII fields (admin-only)
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    custom_fields: str | None = None


# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenWithCookie(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(StrictInputSchema):
    sub: str | None = None


class RefreshTokenRequest(StrictInputSchema):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Password reset schemas
class ForgotPasswordRequest(StrictInputSchema):
    email: EmailStr
    turnstile_token: str | None = None


class ResetPasswordRequest(StrictInputSchema):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from ..core.security import PasswordValidationError
        from ..core.security import validate_password as core_validate_password

        try:
            core_validate_password(v)
        except PasswordValidationError as exc:
            raise ValueError(str(exc)) from exc
        return v


class ChangePasswordRequest(StrictInputSchema):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from ..core.security import PasswordValidationError
        from ..core.security import validate_password as core_validate_password

        try:
            core_validate_password(v)
        except PasswordValidationError as exc:
            raise ValueError(str(exc)) from exc
        return v


# Email verification schemas
class VerifyEmailRequest(StrictInputSchema):
    token: str


class ResendVerificationRequest(StrictInputSchema):
    email: EmailStr
    turnstile_token: str | None = None


# Magic link schemas
class MagicLinkRequest(StrictInputSchema):
    email: EmailStr
    turnstile_token: str | None = None


class MagicLinkVerifyRequest(StrictInputSchema):
    token: str


# Session management schemas
class SessionInfo(BaseModel):
    id: int
    device_info: str | None
    ip_address: str | None
    created_at: datetime | None = None
    last_active_at: datetime | None = None
    is_current: bool = False

    class Config:
        from_attributes = True


class SessionList(BaseModel):
    sessions: list[SessionInfo]


class RevokeAllSessionsResponse(BaseModel):
    message: str
    revoked_count: int


# Generic response schemas
class MessageResponse(BaseModel):
    message: str


# List response schemas
class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    limit: int





