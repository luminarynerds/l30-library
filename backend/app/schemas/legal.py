# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema

from ..models.legal import (
    ClinicStatus, CourtType, DeadlineType, EmergencyResourceType,
    LegalFeedbackType, FormCompletionStatus, FormDifficulty, FormStatus,
    GuideReadingLevel, ProviderType, RegistrationStatus, WizardSessionStatus
)


# ============================================================================
# Legal Topic Schemas
# ============================================================================

class LegalTopicBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    parent_id: Optional[int] = None
    display_order: int = 0
    icon: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: bool = True
    is_featured: bool = False
    keywords: list[str] = []
    meta_description: Optional[str] = Field(None, max_length=300)
    related_resources: list[dict] = []


class LegalTopicCreate(StrictInputSchema, LegalTopicBase):
    pass


class LegalTopicUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    parent_id: Optional[int] = None
    display_order: Optional[int] = None
    icon: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    keywords: Optional[list[str]] = None
    meta_description: Optional[str] = Field(None, max_length=300)
    related_resources: Optional[list[dict]] = None


class LegalTopicResponse(LegalTopicBase):
    id: int
    view_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class LegalTopicTreeResponse(LegalTopicResponse):
    children: list["LegalTopicTreeResponse"] = []


class LegalTopicListResponse(BaseModel):
    topics: list[LegalTopicResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Legal Form Schemas
# ============================================================================

class LegalFormBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    form_number: Optional[str] = Field(None, max_length=100)
    topic_id: Optional[int] = None
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    jurisdiction: str = Field(..., max_length=100)
    jurisdiction_code: Optional[str] = Field(None, max_length=20)
    court_type: Optional[str] = Field(None, max_length=50)
    court_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    when_to_use: Optional[str] = None
    who_should_use: Optional[str] = None
    plain_language_title: Optional[str] = Field(None, max_length=300)
    url: Optional[str] = Field(None, max_length=500)
    instructions_url: Optional[str] = Field(None, max_length=500)
    example_url: Optional[str] = Field(None, max_length=500)
    page_count: Optional[int] = Field(None, ge=1)
    filing_fee: Optional[float] = Field(None, ge=0)
    fee_waiver_form_id: Optional[int] = None
    difficulty_level: FormDifficulty = FormDifficulty.moderate
    estimated_completion_time: Optional[int] = Field(None, ge=1)
    notarization_required: bool = False
    signature_requirements: Optional[str] = None
    languages_available: list[str] = ["English"]
    screen_reader_friendly: bool = False
    large_print_available: bool = False
    fillable_pdf: bool = False
    version: Optional[str] = Field(None, max_length=50)
    effective_date: Optional[date] = None
    last_updated: Optional[date] = None
    change_notes: Optional[str] = None
    status: FormStatus = FormStatus.active
    superseded_by_id: Optional[int] = None
    related_form_ids: list[int] = []
    common_mistakes: list[dict] = []
    tips: list[dict] = []
    field_help: dict = {}

    # Columns nullable in the DB but declared with a non-null default here; seeded
    # rows hold NULL, and from_attributes passes the explicit None past the default,
    # 500ing the response. Coerce None back to each field's default at the boundary.
    _NULL_DEFAULTS: ClassVar[dict] = {
        "difficulty_level": FormDifficulty.moderate,
        "notarization_required": False,
        "languages_available": ["English"],
        "screen_reader_friendly": False,
        "large_print_available": False,
        "fillable_pdf": False,
        "status": FormStatus.active,
        "related_form_ids": [],
        "common_mistakes": [],
        "tips": [],
        "field_help": {},
    }

    @field_validator(
        "difficulty_level", "notarization_required", "languages_available",
        "screen_reader_friendly", "large_print_available", "fillable_pdf",
        "status", "related_form_ids", "common_mistakes", "tips", "field_help",
        mode="before",
    )
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v


class LegalFormCreate(StrictInputSchema, LegalFormBase):
    pass


class LegalFormUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    form_number: Optional[str] = Field(None, max_length=100)
    topic_id: Optional[int] = None
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    jurisdiction: Optional[str] = Field(None, max_length=100)
    jurisdiction_code: Optional[str] = Field(None, max_length=20)
    court_type: Optional[str] = Field(None, max_length=50)
    court_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    when_to_use: Optional[str] = None
    who_should_use: Optional[str] = None
    plain_language_title: Optional[str] = Field(None, max_length=300)
    url: Optional[str] = Field(None, max_length=500)
    instructions_url: Optional[str] = Field(None, max_length=500)
    example_url: Optional[str] = Field(None, max_length=500)
    page_count: Optional[int] = Field(None, ge=1)
    filing_fee: Optional[float] = Field(None, ge=0)
    fee_waiver_form_id: Optional[int] = None
    difficulty_level: Optional[FormDifficulty] = None
    estimated_completion_time: Optional[int] = Field(None, ge=1)
    notarization_required: Optional[bool] = None
    signature_requirements: Optional[str] = None
    languages_available: Optional[list[str]] = None
    screen_reader_friendly: Optional[bool] = None
    large_print_available: Optional[bool] = None
    fillable_pdf: Optional[bool] = None
    version: Optional[str] = Field(None, max_length=50)
    effective_date: Optional[date] = None
    last_updated: Optional[date] = None
    change_notes: Optional[str] = None
    status: Optional[FormStatus] = None
    superseded_by_id: Optional[int] = None
    related_form_ids: Optional[list[int]] = None
    common_mistakes: Optional[list[dict]] = None
    tips: Optional[list[dict]] = None
    field_help: Optional[dict] = None


class LegalFormResponse(LegalFormBase):
    id: int
    download_count: int
    view_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    last_reviewed_at: Optional[datetime] = None
    last_reviewed_by_id: Optional[int] = None
    topic_name: Optional[str] = None

    class Config:
        from_attributes = True


class LegalFormSummaryResponse(BaseModel):
    id: int
    title: str
    form_number: Optional[str] = None
    plain_language_title: Optional[str] = None
    jurisdiction: str
    difficulty_level: FormDifficulty
    filing_fee: Optional[float] = None
    languages_available: list[str]
    status: FormStatus
    topic_id: Optional[int] = None
    topic_name: Optional[str] = None
    last_reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LegalFormListResponse(BaseModel):
    forms: list[LegalFormSummaryResponse]
    total: int
    limit: int
    offset: int


class LegalFormSearchRequest(StrictInputSchema):
    query: Optional[str] = Field(None, max_length=500)
    topic_id: Optional[int] = None
    jurisdiction: Optional[str] = None
    court_type: Optional[str] = None
    difficulty_level: Optional[FormDifficulty] = None
    language: Optional[str] = None
    has_fee_waiver: Optional[bool] = None
    fillable_only: Optional[bool] = None


# ============================================================================
# Legal Form Packet Schemas
# ============================================================================

class LegalFormPacketItemCreate(StrictInputSchema):
    form_id: int
    order: int = 0
    instructions: Optional[str] = None
    is_required: bool = True
    conditional_notes: Optional[str] = None


class LegalFormPacketItemResponse(BaseModel):
    id: int
    packet_id: int
    form_id: int
    order: int
    instructions: Optional[str] = None
    is_required: bool
    conditional_notes: Optional[str] = None
    form_title: Optional[str] = None
    form_number: Optional[str] = None

    class Config:
        from_attributes = True


class LegalFormPacketBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    slug: str = Field(..., min_length=1, max_length=150, pattern=r"^[a-z0-9-]+$")
    topic_id: Optional[int] = None
    description: Optional[str] = None
    use_case: Optional[str] = None
    who_should_use: Optional[str] = None
    checklist: list[dict] = []
    filing_sequence: list[dict] = []
    total_filing_fee: Optional[float] = Field(None, ge=0)
    estimated_total_time: Optional[int] = Field(None, ge=1)
    timeline_description: Optional[str] = None
    cost_breakdown: list[dict] = []
    instructions: Optional[str] = None
    related_guide_ids: list[int] = []
    jurisdiction: Optional[str] = Field(None, max_length=100)
    court_addresses: list[dict] = []
    is_active: bool = True


class LegalFormPacketCreate(StrictInputSchema, LegalFormPacketBase):
    forms: list[LegalFormPacketItemCreate] = []


class LegalFormPacketUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=300)
    slug: Optional[str] = Field(None, min_length=1, max_length=150, pattern=r"^[a-z0-9-]+$")
    topic_id: Optional[int] = None
    description: Optional[str] = None
    use_case: Optional[str] = None
    who_should_use: Optional[str] = None
    checklist: Optional[list[dict]] = None
    filing_sequence: Optional[list[dict]] = None
    total_filing_fee: Optional[float] = Field(None, ge=0)
    estimated_total_time: Optional[int] = Field(None, ge=1)
    timeline_description: Optional[str] = None
    cost_breakdown: Optional[list[dict]] = None
    instructions: Optional[str] = None
    related_guide_ids: Optional[list[int]] = None
    jurisdiction: Optional[str] = Field(None, max_length=100)
    court_addresses: Optional[list[dict]] = None
    is_active: Optional[bool] = None


class LegalFormPacketResponse(LegalFormPacketBase):
    id: int
    download_count: Optional[int] = 0
    view_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    forms: list[LegalFormPacketItemResponse] = []
    topic_name: Optional[str] = None

    class Config:
        from_attributes = True


class LegalFormPacketSummaryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    jurisdiction: Optional[str] = None
    total_filing_fee: Optional[float] = None
    form_count: int = 0
    is_active: bool
    topic_name: Optional[str] = None

    class Config:
        from_attributes = True


class LegalFormPacketListResponse(BaseModel):
    packets: list[LegalFormPacketSummaryResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Legal Guide Schemas
# ============================================================================

class LegalGuideBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    slug: str = Field(..., min_length=1, max_length=150, pattern=r"^[a-z0-9-]+$")
    topic_id: Optional[int] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    reading_level: GuideReadingLevel = GuideReadingLevel.middle_school
    steps: list[dict] = []
    related_form_ids: list[int] = []
    related_guide_ids: list[int] = []
    related_resource_urls: list[dict] = []
    flowchart_data: Optional[dict] = None
    flowchart_image_url: Optional[str] = Field(None, max_length=500)
    timeline_description: Optional[str] = None
    cost_breakdown: list[dict] = []
    common_scenarios: list[dict] = []
    when_need_lawyer: Optional[str] = None
    complexity_warning_signs: list[str] = []
    video_url: Optional[str] = Field(None, max_length=500)
    video_transcript: Optional[str] = None
    printable_checklist: list[dict] = []
    languages_available: list[str] = ["English"]
    is_published: bool = False
    is_featured: bool = False


class LegalGuideCreate(StrictInputSchema, LegalGuideBase):
    pass


class LegalGuideUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    slug: Optional[str] = Field(None, min_length=1, max_length=150, pattern=r"^[a-z0-9-]+$")
    topic_id: Optional[int] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    reading_level: Optional[GuideReadingLevel] = None
    steps: Optional[list[dict]] = None
    related_form_ids: Optional[list[int]] = None
    related_guide_ids: Optional[list[int]] = None
    related_resource_urls: Optional[list[dict]] = None
    flowchart_data: Optional[dict] = None
    flowchart_image_url: Optional[str] = Field(None, max_length=500)
    timeline_description: Optional[str] = None
    cost_breakdown: Optional[list[dict]] = None
    common_scenarios: Optional[list[dict]] = None
    when_need_lawyer: Optional[str] = None
    complexity_warning_signs: Optional[list[str]] = None
    video_url: Optional[str] = Field(None, max_length=500)
    video_transcript: Optional[str] = None
    printable_checklist: Optional[list[dict]] = None
    languages_available: Optional[list[str]] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None


class LegalGuideResponse(LegalGuideBase):
    id: int
    view_count: Optional[int] = 0
    # Optional: seeded rows persisted NULL counts (no server_default); matches LegalCollectionResponse.
    helpful_count: Optional[int] = 0
    not_helpful_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    last_reviewed_at: Optional[datetime] = None
    last_reviewed_by_id: Optional[int] = None
    topic_name: Optional[str] = None

    class Config:
        from_attributes = True


class LegalGuideSummaryResponse(BaseModel):
    id: int
    title: str
    slug: str
    summary: Optional[str] = None
    reading_level: GuideReadingLevel
    is_published: bool
    is_featured: bool
    topic_id: Optional[int] = None
    topic_name: Optional[str] = None
    last_reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LegalGuideListResponse(BaseModel):
    guides: list[LegalGuideSummaryResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Legal Service Provider Schemas
# ============================================================================

class LegalServiceProviderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    slug: str = Field(..., min_length=1, max_length=150, pattern=r"^[a-z0-9-]+$")
    provider_type: ProviderType
    description: Optional[str] = None
    services: list[dict] = []
    topic_ids: list[int] = []
    eligibility_criteria: Optional[str] = None
    income_limits: Optional[str] = None
    income_limit_percentage: Optional[int] = Field(None, ge=0, le=1000)
    geographic_restrictions: Optional[str] = None
    other_requirements: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=30)
    phone_toll_free: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=500)
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    hours: dict = {}
    hours_notes: Optional[str] = None
    languages_spoken: list[str] = ["English"]
    accepts_walkins: bool = False
    appointment_required: bool = True
    wheelchair_accessible: bool = True
    virtual_services: bool = False
    specializations: list[str] = []
    special_populations: list[str] = []
    is_active: bool = True


class LegalServiceProviderCreate(StrictInputSchema, LegalServiceProviderBase):
    pass


class LegalServiceProviderUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=300)
    slug: Optional[str] = Field(None, min_length=1, max_length=150, pattern=r"^[a-z0-9-]+$")
    provider_type: Optional[ProviderType] = None
    description: Optional[str] = None
    services: Optional[list[dict]] = None
    topic_ids: Optional[list[int]] = None
    eligibility_criteria: Optional[str] = None
    income_limits: Optional[str] = None
    income_limit_percentage: Optional[int] = Field(None, ge=0, le=1000)
    geographic_restrictions: Optional[str] = None
    other_requirements: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=30)
    phone_toll_free: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=500)
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    hours: Optional[dict] = None
    hours_notes: Optional[str] = None
    languages_spoken: Optional[list[str]] = None
    accepts_walkins: Optional[bool] = None
    appointment_required: Optional[bool] = None
    wheelchair_accessible: Optional[bool] = None
    virtual_services: Optional[bool] = None
    specializations: Optional[list[str]] = None
    special_populations: Optional[list[str]] = None
    is_active: Optional[bool] = None


class LegalServiceProviderResponse(LegalServiceProviderBase):
    id: int
    is_verified: Optional[bool] = False
    verified_at: Optional[datetime] = None
    view_count: Optional[int] = 0
    referral_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class LegalServiceProviderSummaryResponse(BaseModel):
    id: int
    name: str
    slug: str
    provider_type: ProviderType
    city: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    languages_spoken: list[str] = ["English"]
    accepts_walkins: Optional[bool] = False
    virtual_services: Optional[bool] = False
    is_active: Optional[bool] = True

    class Config:
        from_attributes = True


class LegalServiceProviderListResponse(BaseModel):
    providers: list[LegalServiceProviderSummaryResponse]
    total: int
    limit: int
    offset: int


class LegalServiceProviderSearchRequest(StrictInputSchema):
    query: Optional[str] = Field(None, max_length=500)
    provider_type: Optional[ProviderType] = None
    topic_id: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    language: Optional[str] = None
    accepts_walkins: Optional[bool] = None
    virtual_services: Optional[bool] = None
    special_population: Optional[str] = None


# ============================================================================
# Legal Clinic Schemas
# ============================================================================

class LegalClinicBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    topic_id: Optional[int] = None
    description: Optional[str] = None
    provider_id: Optional[int] = None
    date: date
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    timezone: str = "America/Los_Angeles"
    is_virtual: bool = False
    virtual_link: Optional[str] = Field(None, max_length=500)
    virtual_platform: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = None
    capacity: int = Field(20, ge=1)
    waitlist_capacity: int = Field(10, ge=0)
    registration_required: bool = True
    registration_opens: Optional[datetime] = None
    registration_closes: Optional[datetime] = None
    eligibility_notes: Optional[str] = None
    what_to_bring: list[dict] = []
    languages_available: list[str] = ["English"]
    interpreter_available: bool = False
    follow_up_resources: list[dict] = []
    wheelchair_accessible: bool = True
    asl_interpreter: bool = False
    attorney_names: list[str] = []
    public_notes: Optional[str] = None


class LegalClinicCreate(StrictInputSchema, LegalClinicBase):
    internal_notes: Optional[str] = None


class LegalClinicUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    topic_id: Optional[int] = None
    description: Optional[str] = None
    provider_id: Optional[int] = None
    date: Optional[date] = None
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    timezone: Optional[str] = None
    is_virtual: Optional[bool] = None
    virtual_link: Optional[str] = Field(None, max_length=500)
    virtual_platform: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=1)
    waitlist_capacity: Optional[int] = Field(None, ge=0)
    registration_required: Optional[bool] = None
    registration_opens: Optional[datetime] = None
    registration_closes: Optional[datetime] = None
    status: Optional[ClinicStatus] = None
    eligibility_notes: Optional[str] = None
    what_to_bring: Optional[list[dict]] = None
    languages_available: Optional[list[str]] = None
    interpreter_available: Optional[bool] = None
    follow_up_resources: Optional[list[dict]] = None
    wheelchair_accessible: Optional[bool] = None
    asl_interpreter: Optional[bool] = None
    attorney_names: Optional[list[str]] = None
    public_notes: Optional[str] = None
    internal_notes: Optional[str] = None


class LegalClinicResponse(LegalClinicBase):
    id: int
    status: ClinicStatus
    current_registrations: int
    current_waitlist: int
    volunteer_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    topic_name: Optional[str] = None
    provider_name: Optional[str] = None
    spots_available: int = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        from_attributes = True


class LegalClinicSummaryResponse(BaseModel):
    id: int
    name: str
    date: date
    start_time: str
    end_time: str
    is_virtual: bool
    location_name: Optional[str] = None
    status: ClinicStatus
    current_registrations: int
    capacity: int
    spots_available: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    topic_name: Optional[str] = None

    class Config:
        from_attributes = True


class LegalClinicListResponse(BaseModel):
    clinics: list[LegalClinicSummaryResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Legal Clinic Registration Schemas
# ============================================================================

class LegalClinicRegistrationCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=30)
    preferred_contact: str = Field("email", pattern=r"^(email|phone|text)$")
    accessibility_needs: Optional[str] = None
    language_preference: str = "English"
    interpreter_needed: bool = False
    issue_description: Optional[str] = None

    @field_validator("email", "phone")
    @classmethod
    def validate_contact(cls, v, info):
        # At least one contact method required
        return v


class LegalClinicRegistrationUpdate(StrictInputSchema):
    status: Optional[RegistrationStatus] = None
    accessibility_needs: Optional[str] = None
    language_preference: Optional[str] = None
    interpreter_needed: Optional[bool] = None
    follow_up_needed: Optional[bool] = None
    follow_up_notes: Optional[str] = None


class LegalClinicRegistrationResponse(BaseModel):
    id: int
    clinic_id: int
    patron_id: Optional[int] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    preferred_contact: str
    status: RegistrationStatus
    waitlist_position: Optional[int] = None
    accessibility_needs: Optional[str] = None
    language_preference: str
    interpreter_needed: bool
    issue_description: Optional[str] = None
    confirmation_sent: bool
    reminder_sent: bool
    checked_in_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    clinic_title: Optional[str] = None
    clinic_date: Optional[date] = None

    class Config:
        from_attributes = True


class LegalClinicRegistrationListResponse(BaseModel):
    registrations: list[LegalClinicRegistrationResponse]
    total: int
    limit: int
    offset: int


class LegalClinicFeedbackCreate(StrictInputSchema):
    feedback_rating: int = Field(..., ge=1, le=5)
    feedback_comments: Optional[str] = None


# ============================================================================
# Court Location Schemas
# ============================================================================

class CourtLocationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    code: Optional[str] = Field(None, max_length=50)
    court_type: CourtType
    jurisdiction: str = Field(..., max_length=100)
    jurisdiction_code: Optional[str] = Field(None, max_length=20)
    address_line1: str = Field(..., max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=50)
    zip_code: str = Field(..., max_length=20)
    phone: Optional[str] = Field(None, max_length=30)
    phone_clerk: Optional[str] = Field(None, max_length=30)
    phone_self_help: Optional[str] = Field(None, max_length=30)
    fax: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=500)
    general_hours: dict = {}
    filing_hours: dict = {}
    self_help_hours: dict = {}
    holiday_closures: list[dict] = []
    has_self_help_center: bool = False
    self_help_services: list[dict] = []
    self_help_appointment_required: bool = False
    self_help_appointment_url: Optional[str] = Field(None, max_length=500)
    e_filing_available: bool = False
    e_filing_url: Optional[str] = Field(None, max_length=500)
    e_filing_instructions: Optional[str] = None
    what_to_bring: list[dict] = []
    dress_code: Optional[str] = None
    prohibited_items: list[str] = []
    parking_info: Optional[str] = None
    parking_cost: Optional[str] = Field(None, max_length=100)
    wheelchair_accessible: bool = True
    accessibility_notes: Optional[str] = None
    remote_hearings_available: bool = False
    remote_hearing_platform: Optional[str] = Field(None, max_length=100)
    remote_hearing_instructions: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    directions_notes: Optional[str] = None
    is_active: bool = True


class CourtLocationCreate(StrictInputSchema, CourtLocationBase):
    pass


class CourtLocationUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=300)
    code: Optional[str] = Field(None, max_length=50)
    court_type: Optional[CourtType] = None
    jurisdiction: Optional[str] = Field(None, max_length=100)
    jurisdiction_code: Optional[str] = Field(None, max_length=20)
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=30)
    phone_clerk: Optional[str] = Field(None, max_length=30)
    phone_self_help: Optional[str] = Field(None, max_length=30)
    fax: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=500)
    general_hours: Optional[dict] = None
    filing_hours: Optional[dict] = None
    self_help_hours: Optional[dict] = None
    holiday_closures: Optional[list[dict]] = None
    has_self_help_center: Optional[bool] = None
    self_help_services: Optional[list[dict]] = None
    self_help_appointment_required: Optional[bool] = None
    self_help_appointment_url: Optional[str] = Field(None, max_length=500)
    e_filing_available: Optional[bool] = None
    e_filing_url: Optional[str] = Field(None, max_length=500)
    e_filing_instructions: Optional[str] = None
    what_to_bring: Optional[list[dict]] = None
    dress_code: Optional[str] = None
    prohibited_items: Optional[list[str]] = None
    parking_info: Optional[str] = None
    parking_cost: Optional[str] = Field(None, max_length=100)
    wheelchair_accessible: Optional[bool] = None
    accessibility_notes: Optional[str] = None
    remote_hearings_available: Optional[bool] = None
    remote_hearing_platform: Optional[str] = Field(None, max_length=100)
    remote_hearing_instructions: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    directions_notes: Optional[str] = None
    is_active: Optional[bool] = None


class CourtLocationResponse(CourtLocationBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class CourtLocationSummaryResponse(BaseModel):
    id: int
    name: str
    court_type: CourtType
    city: str
    state: str
    phone: Optional[str] = None
    has_self_help_center: bool
    e_filing_available: bool
    is_active: bool

    class Config:
        from_attributes = True


class CourtLocationListResponse(BaseModel):
    courts: list[CourtLocationSummaryResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Form Finder Wizard Schemas
# ============================================================================

class FormFinderQuestionResponse(BaseModel):
    id: int
    slug: str
    question_text: str
    help_text: Optional[str] = None
    question_type: str
    options: list[dict]
    required: bool
    category: Optional[str] = None

    class Config:
        from_attributes = True


class FormFinderAnswerSubmit(StrictInputSchema):
    question_slug: str
    answer: str | list[str]


class FormFinderWizardStart(BaseModel):
    patron_id: Optional[int] = None


class FormFinderWizardResponse(BaseModel):
    session_token: str
    current_step: Optional[str] = None
    status: WizardSessionStatus
    next_question: Optional[FormFinderQuestionResponse] = None
    progress_percentage: int = 0


class FormFinderResultsResponse(BaseModel):
    session_token: str
    recommended_forms: list[LegalFormSummaryResponse]
    recommended_packets: list[LegalFormPacketSummaryResponse]
    recommended_guides: list[LegalGuideSummaryResponse]
    jurisdiction_state: Optional[str] = None
    jurisdiction_county: Optional[str] = None
    court_type_determined: Optional[str] = None
    printable_checklist: list[dict] = []


# ============================================================================
# Legal Glossary Schemas
# ============================================================================

class LegalGlossaryTermBase(BaseModel):
    term: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")
    definition_simple: Optional[str] = None
    definition_standard: str
    definition_legal: Optional[str] = None
    pronunciation: Optional[str] = Field(None, max_length=200)
    pronunciation_audio_url: Optional[str] = Field(None, max_length=500)
    related_term_slugs: list[str] = []
    see_also: list[str] = []
    usage_example: Optional[str] = None
    context_notes: Optional[str] = None
    translations: dict = {}
    translated_definitions: dict = {}
    topic_ids: list[int] = []
    is_active: bool = True


class LegalGlossaryTermCreate(StrictInputSchema, LegalGlossaryTermBase):
    pass


class LegalGlossaryTermUpdate(StrictInputSchema):
    term: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")
    definition_simple: Optional[str] = None
    definition_standard: Optional[str] = None
    definition_legal: Optional[str] = None
    pronunciation: Optional[str] = Field(None, max_length=200)
    pronunciation_audio_url: Optional[str] = Field(None, max_length=500)
    related_term_slugs: Optional[list[str]] = None
    see_also: Optional[list[str]] = None
    usage_example: Optional[str] = None
    context_notes: Optional[str] = None
    translations: Optional[dict] = None
    translated_definitions: Optional[dict] = None
    topic_ids: Optional[list[int]] = None
    is_active: Optional[bool] = None


class LegalGlossaryTermResponse(LegalGlossaryTermBase):
    id: int
    view_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LegalGlossaryTermSummaryResponse(BaseModel):
    id: int
    term: str
    slug: str
    definition_standard: str
    is_active: bool

    class Config:
        from_attributes = True


class LegalGlossaryListResponse(BaseModel):
    terms: list[LegalGlossaryTermSummaryResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Deadline Calculator Schemas
# ============================================================================

class DeadlineRuleResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    deadline_type: DeadlineType
    days: int
    use_business_days: bool
    exclude_holidays: bool
    start_event: Optional[str] = None
    legal_citation: Optional[str] = None
    jurisdiction: Optional[str] = None
    court_type: Optional[str] = None

    class Config:
        from_attributes = True


class DeadlineCalculationRequest(StrictInputSchema):
    rule_id: Optional[int] = None
    rule_slug: Optional[str] = None
    start_date: date
    reminder_email: Optional[str] = Field(None, max_length=255)
    reminder_phone: Optional[str] = Field(None, max_length=30)
    enable_reminders: bool = False
    user_notes: Optional[str] = None


class DeadlineCalculationResponse(BaseModel):
    id: int
    rule_name: str
    start_date: date
    deadline_date: date
    days_until_deadline: int
    warning_dates: list[date]
    reminders_enabled: bool
    user_notes: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Know Your Rights Schemas
# ============================================================================

class KnowYourRightsGuideResponse(BaseModel):
    id: int
    title: str
    slug: str
    situation: str
    summary: Optional[str] = None
    content: str
    key_rights: list[dict]
    dos: list[dict]
    donts: list[dict]
    scripts: list[dict]
    when_silent: Optional[str] = None
    documentation_tips: list[dict]
    emergency_contacts: list[dict]
    wallet_card_content: Optional[str] = None
    wallet_card_pdf_url: Optional[str] = None
    video_url: Optional[str] = None
    languages_available: list[str]
    is_published: bool
    view_count: Optional[int] = 0

    class Config:
        from_attributes = True


class KnowYourRightsGuideSummaryResponse(BaseModel):
    id: int
    title: str
    slug: str
    situation: str
    summary: Optional[str] = None
    languages_available: list[str]
    is_published: bool

    class Config:
        from_attributes = True


class KnowYourRightsListResponse(BaseModel):
    guides: list[KnowYourRightsGuideSummaryResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Emergency Resource Schemas
# ============================================================================

class EmergencyResourceResponse(BaseModel):
    id: int
    name: str
    resource_type: EmergencyResourceType
    situation: Optional[str] = None
    phone: Optional[str] = None
    phone_toll_free: Optional[str] = None
    text_number: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    when_to_call: Optional[str] = None
    is_24_7: bool
    hours_description: Optional[str] = None
    languages_available: list[str]
    is_featured: bool

    class Config:
        from_attributes = True


class EmergencyResourceListResponse(BaseModel):
    resources: list[EmergencyResourceResponse]
    total: int


# ============================================================================
# Fee Waiver Schemas
# ============================================================================

class FeeWaiverEligibilityCheckRequest(StrictInputSchema):
    jurisdiction: str
    household_size: int = Field(..., ge=1, le=20)
    annual_income: float = Field(..., ge=0)
    receives_public_benefits: list[str] = []


class FeeWaiverEligibilityResponse(BaseModel):
    is_eligible: bool
    eligibility_reason: str
    automatic_eligibility: bool
    partial_waiver_available: bool
    payment_plan_available: bool
    form_id: Optional[int] = None
    form_title: Optional[str] = None
    required_documentation: list[str]
    next_steps: list[str]


# ============================================================================
# Expungement Schemas
# ============================================================================

class ExpungementEligibilityCheckRequest(StrictInputSchema):
    jurisdiction: str
    offense_category: str  # felony, misdemeanor, infraction
    offense_type: Optional[str] = None
    conviction_date: date
    sentence_completed_date: Optional[date] = None


class ExpungementEligibilityResponse(BaseModel):
    is_eligible: bool
    eligibility_notes: str
    waiting_period_met: bool
    waiting_period_end_date: Optional[date] = None
    requirements: list[str]
    exclusions: list[str]
    form_ids: list[int]
    estimated_timeline: Optional[str] = None
    estimated_cost: Optional[float] = None


# ============================================================================
# Content Feedback Schemas
# ============================================================================

class LegalContentFeedbackCreate(StrictInputSchema):
    content_type: str = Field(..., max_length=50)
    content_id: int
    page_url: Optional[str] = Field(None, max_length=500)
    feedback_type: LegalFeedbackType
    was_helpful: Optional[bool] = None
    comments: Optional[str] = None
    what_looking_for: Optional[str] = None
    suggestion: Optional[str] = None
    email: Optional[str] = Field(None, max_length=255)


class LegalContentFeedbackResponse(BaseModel):
    id: int
    content_type: str
    content_id: int
    feedback_type: LegalFeedbackType
    was_helpful: Optional[bool] = None
    comments: Optional[str] = None
    staff_reviewed: bool
    resolved: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Statistics Schemas
# ============================================================================

class LegalResourceStatisticsResponse(BaseModel):
    resource_type: str
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    period_date: date
    period_type: str
    view_count: Optional[int] = 0
    download_count: int
    helpful_count: int
    not_helpful_count: int
    unique_sessions: int


class LegalResourceStatisticsReport(BaseModel):
    period_start: date
    period_end: date
    total_views: int
    total_downloads: int
    top_topics: list[dict]
    top_forms: list[dict]
    top_guides: list[dict]
    top_searches: list[dict]
    feedback_summary: dict


# ============================================================================
# Staff Guidelines Schemas
# ============================================================================

class LegalStaffGuidelineResponse(BaseModel):
    id: int
    title: str
    slug: str
    category: str
    content: str
    can_do_examples: list[dict]
    cannot_do_examples: list[dict]
    scripts: list[dict]
    referral_tree: Optional[dict] = None
    is_active: bool

    class Config:
        from_attributes = True


# ============================================================================
# Legal Collection Schemas (Phase 1 Expansion)
# ============================================================================

class LegalCollectionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    slug: str = Field(..., min_length=1, max_length=150, pattern=r"^[a-z0-9-]+$")
    description: str = Field(..., min_length=10)
    situation: str = Field(..., min_length=1, max_length=100)
    guide_ids: list[int] = Field(default_factory=list)
    form_ids: list[int] = Field(default_factory=list)
    clinic_ids: list[int] = Field(default_factory=list)
    provider_ids: list[int] = Field(default_factory=list)
    glossary_term_ids: list[int] = Field(default_factory=list)
    estimated_time_minutes: Optional[int] = None
    complexity_level: Optional[str] = Field(None, pattern=r"^(simple|easy|moderate|complex)$")
    success_outcomes: list[str] = Field(default_factory=list)
    reading_level: str = "college"
    step_by_step_summary: list[dict] = Field(default_factory=list)
    icon: Optional[str] = Field(None, max_length=50)
    color_code: Optional[str] = Field(None, max_length=20)
    available_languages: list[str] = Field(default_factory=list)
    # Librarian recommendations - Priority 1
    estimated_cost_min: int = 0
    estimated_cost_max: Optional[int] = None
    cost_description: Optional[str] = Field(None, max_length=255)
    fee_waiver_available: bool = True
    resource_details: list[dict] = Field(default_factory=list)
    last_reviewed_date: Optional[datetime] = None
    is_published: bool = False
    is_featured: bool = False
    display_order: int = 0


class LegalCollectionCreate(StrictInputSchema, LegalCollectionBase):
    pass


class LegalCollectionUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = Field(None, min_length=10)
    situation: Optional[str] = Field(None, min_length=1, max_length=100)
    guide_ids: Optional[list[int]] = None
    form_ids: Optional[list[int]] = None
    clinic_ids: Optional[list[int]] = None
    provider_ids: Optional[list[int]] = None
    glossary_term_ids: Optional[list[int]] = None
    estimated_time_minutes: Optional[int] = None
    complexity_level: Optional[str] = Field(None, pattern=r"^(simple|easy|moderate|complex)$")
    success_outcomes: Optional[list[str]] = None
    reading_level: Optional[str] = None
    step_by_step_summary: Optional[list[dict]] = None
    icon: Optional[str] = Field(None, max_length=50)
    color_code: Optional[str] = Field(None, max_length=20)
    available_languages: Optional[list[str]] = None
    # Librarian recommendations - Priority 1
    estimated_cost_min: Optional[int] = None
    estimated_cost_max: Optional[int] = None
    cost_description: Optional[str] = Field(None, max_length=255)
    fee_waiver_available: Optional[bool] = None
    resource_details: Optional[list[dict]] = None
    last_reviewed_date: Optional[datetime] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None
    display_order: Optional[int] = None


class LegalCollectionResponse(LegalCollectionBase):
    id: int
    view_count: Optional[int] = 0
    click_through_count: Optional[int] = 0
    completion_count: Optional[int] = 0
    helpful_count: Optional[int] = 0
    unhelpful_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class LegalCollectionListResponse(BaseModel):
    collections: list[LegalCollectionResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Disclaimer Schema
# ============================================================================

class LegalDisclaimerResponse(BaseModel):
    disclaimer_text: str
    emergency_contacts: list[dict]
    quick_exit_enabled: bool


# ============================================================================
# Compliance Requirement Schemas
# ============================================================================

class ComplianceRequirementBase(BaseModel):
    title: str = Field(..., max_length=300)
    slug: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    deadline_description: Optional[str] = None


class ComplianceRequirementCreate(StrictInputSchema, ComplianceRequirementBase):
    pass


class ComplianceRequirementUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    deadline_description: Optional[str] = None
    is_active: Optional[bool] = None


class ComplianceRequirementResponse(ComplianceRequirementBase):
    id: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Forward reference resolution
LegalTopicTreeResponse.model_rebuild()
