# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from pydantic import BaseModel, EmailStr, Field


class SetupStatusResponse(BaseModel):
    setup_required: bool
    demo_mode: bool
    demo_public: bool


class AdminAccountCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LibraryInfoCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=20)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    phone: str | None = None
    email: EmailStr | None = None


class BrandingCreate(BaseModel):
    primary_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    hero_title: str | None = None
    tagline: str | None = None


class PoliciesCreate(BaseModel):
    default_loan_period_days: int = Field(default=21, ge=1, le=365)
    default_renewal_limit: int = Field(default=2, ge=0, le=99)
    default_hold_limit: int = Field(default=10, ge=0, le=99)
    default_overdue_fine_per_day: float = Field(default=0.25, ge=0)
    default_max_fine: float = Field(default=10.00, ge=0)
    grace_period_days: int = Field(default=0, ge=0, le=30)
    fine_free_juvenile: bool = False
    lost_item_threshold_days: int = Field(default=30, ge=1, le=365)


class FeaturesCreate(BaseModel):
    preset: str = Field(min_length=1, max_length=40)
    overrides: dict[str, bool] = Field(default_factory=dict)


class AiPrefsCreate(BaseModel):
    model: str = Field(min_length=1, max_length=100)
    temperature: float = Field(default=0.7, ge=0, le=2)
    system_prompt: str = Field(default="", max_length=8000)
    guardrails: dict = Field(default_factory=dict)


class DomainUpdate(BaseModel):
    domain: str = Field(min_length=1, max_length=253)


class DemoWipeRequest(BaseModel):
    confirmation: str


class SetupResponse(BaseModel):
    success: bool
    message: str
    # Only set by POST /setup/admin: auto-login for the founding admin so the
    # wizard can call the admin-gated remaining steps without a Turnstile'd
    # login round-trip.
    access_token: str | None = None


class SetupProgressStep(BaseModel):
    id: str
    title: str
    description: str
    action: str
    icon: str
    completed: bool
    count: int | None = None


class SetupProgressResponse(BaseModel):
    library_system_id: int
    completed_count: int
    total: int
    all_complete: bool
    steps: list[SetupProgressStep]
