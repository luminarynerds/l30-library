# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import ClassVar, List, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field, EmailStr, HttpUrl, field_validator

from app.schemas._base import StrictInputSchema

from ..models.immigrant_services import (
    ResourceCategory, ESLLevel, ClassScheduleStatus, CircleType,
    ProgramType, TranslationServiceType, TranslationStatus, ContactRole,
    PacketType, ImpactStoryStatus, PartnerStatus
)


# ============================================================================
# Citizenship Resources Schemas
# ============================================================================

class CitizenshipResourceCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    category: ResourceCategory
    url: Optional[str] = None
    file_url: Optional[str] = None
    provider_name: Optional[str] = None
    languages_available: List[str] = Field(default_factory=list)
    reading_level: Optional[str] = None
    is_free: bool = True
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    service_area: Optional[str] = None
    citizenship_type: Optional[str] = None
    availability_notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class CitizenshipResourceUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ResourceCategory] = None
    url: Optional[str] = None
    file_url: Optional[str] = None
    provider_name: Optional[str] = None
    languages_available: Optional[List[str]] = None
    reading_level: Optional[str] = None
    is_free: Optional[bool] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    service_area: Optional[str] = None
    citizenship_type: Optional[str] = None
    availability_notes: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class CitizenshipResourceResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: ResourceCategory
    url: Optional[str]
    file_url: Optional[str]
    provider_name: Optional[str]
    languages_available: List[str]
    reading_level: Optional[str]
    is_free: bool
    phone_number: Optional[str]
    email: Optional[str]
    service_area: Optional[str]
    citizenship_type: Optional[str]
    availability_notes: Optional[str]
    tags: List[str]
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# ESL Classes and Enrollments Schemas
# ============================================================================

class ESLClassCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    level: ESLLevel
    instructor_name: Optional[str] = None
    instructor_email: Optional[EmailStr] = None
    instructor_phone: Optional[str] = None
    location: Optional[str] = None
    virtual_link: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    day_of_week: Optional[List[str]] = Field(default_factory=list)
    max_capacity: Optional[int] = None
    tuition_cost: Optional[float] = None
    tuition_notes: Optional[str] = None
    prerequisites: Optional[str] = None
    skills_covered: Optional[List[str]] = Field(default_factory=list)
    certifications_offered: Optional[List[str]] = Field(default_factory=list)
    registration_deadline: Optional[date] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    is_virtual: bool = False
    is_in_person: bool = True


class ESLClassUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    level: Optional[ESLLevel] = None
    status: Optional[ClassScheduleStatus] = None
    instructor_name: Optional[str] = None
    instructor_email: Optional[EmailStr] = None
    instructor_phone: Optional[str] = None
    location: Optional[str] = None
    virtual_link: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    day_of_week: Optional[List[str]] = None
    max_capacity: Optional[int] = None
    current_enrollment: Optional[int] = None
    tuition_cost: Optional[float] = None
    tuition_notes: Optional[str] = None
    prerequisites: Optional[str] = None
    skills_covered: Optional[List[str]] = None
    certifications_offered: Optional[List[str]] = None
    registration_deadline: Optional[date] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    is_virtual: Optional[bool] = None
    is_in_person: Optional[bool] = None


class ESLClassResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    level: ESLLevel
    status: ClassScheduleStatus
    instructor_name: Optional[str]
    instructor_email: Optional[str]
    instructor_phone: Optional[str]
    location: Optional[str]
    virtual_link: Optional[str]
    start_date: date
    end_date: Optional[date]
    start_time: Optional[str]
    end_time: Optional[str]
    day_of_week: Optional[List[str]] = []
    max_capacity: Optional[int]
    current_enrollment: int
    tuition_cost: Optional[float]
    tuition_notes: Optional[str]
    prerequisites: Optional[str]
    skills_covered: Optional[List[str]] = []
    certifications_offered: Optional[List[str]] = []
    registration_deadline: Optional[date]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    is_virtual: bool = False
    is_in_person: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ESLEnrollmentCreate(StrictInputSchema):
    esl_class_id: int
    patron_id: int
    enrollment_date: date


class ESLEnrollmentUpdate(StrictInputSchema):
    status: Optional[str] = None
    attendance_count: Optional[int] = None
    certificate_earned: Optional[bool] = None
    assessment_score: Optional[float] = None
    notes: Optional[str] = None
    completion_date: Optional[date] = None


class ESLEnrollmentResponse(BaseModel):
    id: int
    esl_class_id: int
    patron_id: int
    enrollment_date: date
    completion_date: Optional[date]
    status: str
    attendance_count: int
    certificate_earned: bool
    assessment_score: Optional[float]
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ESLEnrollmentWithPatronResponse(BaseModel):
    id: int
    esl_class_id: int
    patron_id: int
    patron_first_name: Optional[str] = None
    patron_last_name: Optional[str] = None
    patron_email: Optional[str] = None
    enrollment_date: date
    completion_date: Optional[date]
    status: str
    attendance_count: int
    certificate_earned: bool
    assessment_score: Optional[float]
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ESLEnrollmentWithPatronListResponse(BaseModel):
    items: List[ESLEnrollmentWithPatronResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Conversation Circles Schemas
# ============================================================================

class ConversationCircleCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    circle_type: CircleType
    facilitator_name: Optional[str] = None
    facilitator_email: Optional[EmailStr] = None
    facilitator_phone: Optional[str] = None
    location: Optional[str] = None
    virtual_link: Optional[str] = None
    schedule_description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    day_of_week: Optional[List[str]] = Field(default_factory=list)
    max_capacity: Optional[int] = None
    languages_discussed: List[str] = Field(default_factory=list)
    target_age_group: Optional[str] = None
    is_free: bool = True
    esl_class_id: Optional[int] = None


class ConversationCircleUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    circle_type: Optional[CircleType] = None
    facilitator_name: Optional[str] = None
    facilitator_email: Optional[EmailStr] = None
    facilitator_phone: Optional[str] = None
    location: Optional[str] = None
    virtual_link: Optional[str] = None
    schedule_description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    day_of_week: Optional[List[str]] = None
    max_capacity: Optional[int] = None
    languages_discussed: Optional[List[str]] = None
    target_age_group: Optional[str] = None
    is_free: Optional[bool] = None
    is_active: Optional[bool] = None


class ConversationCircleResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    circle_type: CircleType
    facilitator_name: Optional[str]
    facilitator_email: Optional[str]
    facilitator_phone: Optional[str]
    location: Optional[str]
    virtual_link: Optional[str]
    schedule_description: Optional[str]
    start_date: date
    end_date: Optional[date]
    start_time: Optional[str]
    end_time: Optional[str]
    day_of_week: Optional[List[str]] = []
    max_capacity: Optional[int]
    languages_discussed: List[str]
    target_age_group: Optional[str]
    is_free: bool
    is_active: bool
    esl_class_id: Optional[int]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Cultural Programs Schemas
# ============================================================================

class CulturalProgramCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    program_type: ProgramType
    culture_featured: Optional[str] = None
    organizer_name: Optional[str] = None
    organizer_email: Optional[EmailStr] = None
    organizer_phone: Optional[str] = None
    event_date: date
    event_time: Optional[str] = None
    location: Optional[str] = None
    virtual_link: Optional[str] = None
    is_virtual: bool = False
    is_in_person: bool = True
    expected_attendance: Optional[int] = None
    budget: Optional[float] = None
    partners_involved: List[str] = Field(default_factory=list)
    languages_featured: List[str] = Field(default_factory=list)
    accessibility_notes: Optional[str] = None
    is_family_friendly: bool = True
    cost_notes: Optional[str] = None
    registration_required: bool = False
    registration_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class CulturalProgramUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    program_type: Optional[ProgramType] = None
    culture_featured: Optional[str] = None
    organizer_name: Optional[str] = None
    organizer_email: Optional[EmailStr] = None
    organizer_phone: Optional[str] = None
    event_date: Optional[date] = None
    event_time: Optional[str] = None
    location: Optional[str] = None
    virtual_link: Optional[str] = None
    is_virtual: Optional[bool] = None
    is_in_person: Optional[bool] = None
    expected_attendance: Optional[int] = None
    actual_attendance: Optional[int] = None
    budget: Optional[float] = None
    partners_involved: Optional[List[str]] = None
    languages_featured: Optional[List[str]] = None
    accessibility_notes: Optional[str] = None
    is_family_friendly: Optional[bool] = None
    cost_notes: Optional[str] = None
    registration_required: Optional[bool] = None
    registration_url: Optional[str] = None
    status: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class CulturalProgramResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    program_type: ProgramType
    culture_featured: Optional[str]
    organizer_name: Optional[str]
    organizer_email: Optional[str]
    organizer_phone: Optional[str]
    event_date: date
    event_time: Optional[str]
    location: Optional[str]
    virtual_link: Optional[str]
    is_virtual: bool = False
    is_in_person: bool = True
    expected_attendance: Optional[int]
    actual_attendance: Optional[int]
    budget: Optional[float]
    partners_involved: List[str]
    languages_featured: List[str]
    accessibility_notes: Optional[str]
    is_family_friendly: bool
    cost_notes: Optional[str]
    registration_required: bool
    registration_url: Optional[str]
    status: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # partners_involved is nullable in the DB but declared non-null here; seeded
    # rows hold NULL, which from_attributes hands pydantic as an explicit None and
    # the response 500s. Coerce None back to the intended default.
    _NULL_DEFAULTS: ClassVar[dict] = {"partners_involved": []}

    @field_validator("partners_involved", mode="before")
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v

    class Config:
        from_attributes = True


# ============================================================================
# Translation Services Schemas
# ============================================================================

class TranslationServiceCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=300)
    service_type: TranslationServiceType
    source_language: str
    target_language: str
    provider_name: Optional[str] = None
    provider_email: Optional[EmailStr] = None
    provider_phone: Optional[str] = None
    certified: bool = False
    specializations: List[str] = Field(default_factory=list)
    hourly_rate: Optional[float] = None
    contact_method: Optional[str] = None
    service_area: Optional[str] = None
    notes: Optional[str] = None


class TranslationServiceUpdate(StrictInputSchema):
    title: Optional[str] = None
    service_type: Optional[TranslationServiceType] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    provider_name: Optional[str] = None
    provider_email: Optional[EmailStr] = None
    provider_phone: Optional[str] = None
    certified: Optional[bool] = None
    specializations: Optional[List[str]] = None
    hourly_rate: Optional[float] = None
    contact_method: Optional[str] = None
    is_active: Optional[bool] = None
    service_area: Optional[str] = None
    notes: Optional[str] = None


class TranslationServiceResponse(BaseModel):
    id: int
    title: str
    service_type: TranslationServiceType
    source_language: str
    target_language: str
    provider_name: Optional[str]
    provider_email: Optional[str]
    provider_phone: Optional[str]
    certified: bool
    specializations: List[str]
    hourly_rate: Optional[float]
    contact_method: Optional[str]
    is_active: bool
    service_area: Optional[str]
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class TranslationRequestCreate(StrictInputSchema):
    service_id: Optional[int] = None
    patron_id: Optional[int] = None
    required_date: Optional[date] = None
    service_type: TranslationServiceType
    source_language: str
    target_language: str
    document_description: str
    document_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class TranslationRequestUpdate(StrictInputSchema):
    service_id: Optional[int] = None
    status: Optional[TranslationStatus] = None
    completion_date: Optional[date] = None
    result_url: Optional[str] = None
    actual_cost: Optional[float] = None
    notes: Optional[str] = None


class TranslationRequestResponse(BaseModel):
    id: int
    service_id: Optional[int]
    patron_id: Optional[int]
    request_date: date
    required_date: Optional[date]
    service_type: TranslationServiceType
    source_language: str
    target_language: str
    document_description: str
    document_url: Optional[str]
    status: TranslationStatus
    contact_email: Optional[str]
    contact_phone: Optional[str]
    estimated_cost: Optional[float]
    actual_cost: Optional[float]
    completion_date: Optional[date]
    result_url: Optional[str]
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Community Liaison Contacts Schemas
# ============================================================================

class CommunityLiaisonContactCreate(StrictInputSchema):
    first_name: str = Field(..., min_length=1, max_length=150)
    last_name: str = Field(..., min_length=1, max_length=150)
    title: Optional[str] = None
    role: ContactRole
    organization: str
    email: EmailStr
    phone: Optional[str] = None
    languages_spoken: List[str] = Field(default_factory=list)
    expertise_areas: List[str] = Field(default_factory=list)
    service_specialties: List[str] = Field(default_factory=list)
    availability_notes: Optional[str] = None
    background: Optional[str] = None
    community_served: Optional[str] = None
    years_of_experience: Optional[int] = None
    notes: Optional[str] = None


class CommunityLiaisonContactUpdate(StrictInputSchema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    role: Optional[ContactRole] = None
    organization: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    languages_spoken: Optional[List[str]] = None
    expertise_areas: Optional[List[str]] = None
    service_specialties: Optional[List[str]] = None
    availability_notes: Optional[str] = None
    background: Optional[str] = None
    community_served: Optional[str] = None
    years_of_experience: Optional[int] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    last_contact_date: Optional[date] = None


class CommunityLiaisonContactResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    title: Optional[str]
    role: ContactRole
    organization: str
    email: str
    phone: Optional[str]
    languages_spoken: List[str]
    expertise_areas: List[str]
    service_specialties: List[str]
    availability_notes: Optional[str]
    background: Optional[str]
    community_served: Optional[str]
    years_of_experience: Optional[int]
    is_active: bool
    notes: Optional[str]
    last_contact_date: Optional[date]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Multilingual Resources Schemas
# ============================================================================

class MultilingualResourceCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    language: str
    resource_type: str
    author_translator: Optional[str] = None
    publication_year: Optional[int] = None
    original_language: Optional[str] = None
    proficiency_level: Optional[str] = None
    subject_areas: List[str] = Field(default_factory=list)
    isbn: Optional[str] = None
    url: Optional[str] = None
    format: Optional[str] = None
    availability: Optional[str] = None
    cultural_relevance: Optional[str] = None
    community_request: bool = False
    acquisition_date: Optional[date] = None


class MultilingualResourceUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    resource_type: Optional[str] = None
    author_translator: Optional[str] = None
    publication_year: Optional[int] = None
    original_language: Optional[str] = None
    proficiency_level: Optional[str] = None
    subject_areas: Optional[List[str]] = None
    isbn: Optional[str] = None
    url: Optional[str] = None
    format: Optional[str] = None
    availability: Optional[str] = None
    cultural_relevance: Optional[str] = None
    community_request: Optional[bool] = None
    acquisition_date: Optional[date] = None
    is_active: Optional[bool] = None


class MultilingualResourceResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    language: str
    resource_type: str
    author_translator: Optional[str]
    publication_year: Optional[int]
    original_language: Optional[str]
    proficiency_level: Optional[str]
    subject_areas: List[str]
    isbn: Optional[str]
    url: Optional[str]
    format: Optional[str]
    availability: Optional[str]
    cultural_relevance: Optional[str]
    community_request: bool
    acquisition_date: Optional[date]
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Welcome Packets Schemas
# ============================================================================

class WelcomePacketCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=300)
    packet_type: PacketType
    description: Optional[str] = None
    languages_included: List[str] = Field(default_factory=list)
    components: List[str] = Field(default_factory=list)
    digital_url: Optional[str] = None
    print_available: bool = True
    digital_available: bool = True
    target_audience: Optional[str] = None


class WelcomePacketUpdate(StrictInputSchema):
    title: Optional[str] = None
    packet_type: Optional[PacketType] = None
    description: Optional[str] = None
    languages_included: Optional[List[str]] = None
    components: Optional[List[str]] = None
    digital_url: Optional[str] = None
    print_available: Optional[bool] = None
    digital_available: Optional[bool] = None
    target_audience: Optional[str] = None
    last_updated_date: Optional[date] = None
    is_active: Optional[bool] = None


class WelcomePacketResponse(BaseModel):
    id: int
    title: str
    packet_type: PacketType
    description: Optional[str]
    languages_included: List[str]
    components: List[str]
    digital_url: Optional[str]
    print_available: bool
    digital_available: bool
    target_audience: Optional[str]
    creation_date: date
    last_updated_date: Optional[date]
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Partner Organizations Schemas
# ============================================================================

class PartnerOrganizationCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    organization_type: Optional[str] = None
    mission: Optional[str] = None
    website: Optional[str] = None
    primary_email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    languages_served: List[str] = Field(default_factory=list)
    services_offered: List[str] = Field(default_factory=list)
    target_populations: List[str] = Field(default_factory=list)
    service_area: List[str] = Field(default_factory=list)
    partnership_since: Optional[date] = None
    contact_person_name: Optional[str] = None
    contact_person_title: Optional[str] = None
    contact_person_email: Optional[EmailStr] = None
    contact_person_phone: Optional[str] = None
    referral_process: Optional[str] = None
    eligibility_requirements: Optional[str] = None
    accessibility_notes: Optional[str] = None
    notes: Optional[str] = None


class PartnerOrganizationUpdate(StrictInputSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    organization_type: Optional[str] = None
    mission: Optional[str] = None
    website: Optional[str] = None
    primary_email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    languages_served: Optional[List[str]] = None
    services_offered: Optional[List[str]] = None
    target_populations: Optional[List[str]] = None
    service_area: Optional[List[str]] = None
    partnership_since: Optional[date] = None
    contact_person_name: Optional[str] = None
    contact_person_title: Optional[str] = None
    contact_person_email: Optional[EmailStr] = None
    contact_person_phone: Optional[str] = None
    status: Optional[PartnerStatus] = None
    annual_collaborations: Optional[int] = None
    volunteer_hours_contributed: Optional[float] = None
    shared_programs: Optional[List[str]] = None
    resources_shared: Optional[str] = None
    referral_process: Optional[str] = None
    eligibility_requirements: Optional[str] = None
    accessibility_notes: Optional[str] = None
    notes: Optional[str] = None


class PartnerOrganizationResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    organization_type: Optional[str]
    mission: Optional[str]
    website: Optional[str]
    primary_email: str
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    languages_served: List[str]
    services_offered: List[str]
    target_populations: List[str]
    service_area: List[str]
    partnership_since: Optional[date]
    contact_person_name: Optional[str]
    contact_person_title: Optional[str]
    contact_person_email: Optional[str]
    contact_person_phone: Optional[str]
    status: PartnerStatus
    annual_collaborations: int
    volunteer_hours_contributed: float
    shared_programs: List[str]
    resources_shared: Optional[str]
    referral_process: Optional[str]
    eligibility_requirements: Optional[str]
    accessibility_notes: Optional[str]
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # volunteer_hours_contributed is nullable in the DB but declared non-null
    # here; seeded rows hold NULL, which from_attributes hands pydantic as an
    # explicit None and the response 500s. Coerce None back to the default.
    _NULL_DEFAULTS: ClassVar[dict] = {"volunteer_hours_contributed": 0.0}

    @field_validator("volunteer_hours_contributed", mode="before")
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v

    class Config:
        from_attributes = True


# ============================================================================
# Impact Stories Schemas
# ============================================================================

class ImpactStoryCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=500)
    summary: Optional[str] = None
    full_story: str
    author_name: Optional[str] = None
    author_email: Optional[EmailStr] = None
    author_role: Optional[str] = None
    language: str = "english"
    themes: List[str] = Field(default_factory=list)
    related_program: Optional[str] = None
    partner_organization_id: Optional[int] = None
    immigrant_experience_years: Optional[int] = None
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    consent_to_publish: bool = False
    consent_to_attribute: bool = False


class ImpactStoryUpdate(StrictInputSchema):
    title: Optional[str] = None
    summary: Optional[str] = None
    full_story: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[EmailStr] = None
    author_role: Optional[str] = None
    language: Optional[str] = None
    themes: Optional[List[str]] = None
    related_program: Optional[str] = None
    partner_organization_id: Optional[int] = None
    immigrant_experience_years: Optional[int] = None
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    consent_to_publish: Optional[bool] = None
    consent_to_attribute: Optional[bool] = None
    status: Optional[ImpactStoryStatus] = None
    publication_date: Optional[date] = None
    featured_on_website: Optional[bool] = None
    featured_on_social_media: Optional[bool] = None
    reviewer_name: Optional[str] = None
    review_notes: Optional[str] = None


class ImpactStoryResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str]
    full_story: str
    author_name: Optional[str]
    author_email: Optional[str]
    author_role: Optional[str]
    submitted_date: date
    status: ImpactStoryStatus
    publication_date: Optional[date]
    featured_on_website: bool
    featured_on_social_media: bool
    language: str
    themes: List[str]
    related_program: Optional[str]
    partner_organization_id: Optional[int]
    immigrant_experience_years: Optional[int]
    photo_url: Optional[str]
    video_url: Optional[str]
    consent_to_publish: bool
    consent_to_attribute: bool
    reach_count: int
    reviewer_name: Optional[str]
    review_date: Optional[date]
    review_notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # reach_count is nullable in the DB but declared non-null here; seeded rows
    # hold NULL, which from_attributes hands pydantic as an explicit None and the
    # response 500s. Coerce None back to the default.
    _NULL_DEFAULTS: ClassVar[dict] = {"reach_count": 0}

    @field_validator("reach_count", mode="before")
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v

    class Config:
        from_attributes = True


# ============================================================================
# List Response Schemas
# ============================================================================

class CitizenshipResourceListResponse(BaseModel):
    items: List[CitizenshipResourceResponse]
    total: int
    limit: int
    offset: int


class ESLClassListResponse(BaseModel):
    items: List[ESLClassResponse]
    total: int
    limit: int
    offset: int


class ConversationCircleListResponse(BaseModel):
    items: List[ConversationCircleResponse]
    total: int
    limit: int
    offset: int


class CulturalProgramListResponse(BaseModel):
    items: List[CulturalProgramResponse]
    total: int
    limit: int
    offset: int


class TranslationServiceListResponse(BaseModel):
    items: List[TranslationServiceResponse]
    total: int
    limit: int
    offset: int


class TranslationRequestListResponse(BaseModel):
    items: List[TranslationRequestResponse]
    total: int
    limit: int
    offset: int


class CommunityLiaisonContactListResponse(BaseModel):
    items: List[CommunityLiaisonContactResponse]
    total: int
    limit: int
    offset: int


class MultilingualResourceListResponse(BaseModel):
    items: List[MultilingualResourceResponse]
    total: int
    limit: int
    offset: int


class WelcomePacketListResponse(BaseModel):
    items: List[WelcomePacketResponse]
    total: int
    limit: int
    offset: int


class PartnerOrganizationListResponse(BaseModel):
    items: List[PartnerOrganizationResponse]
    total: int
    limit: int
    offset: int


class ImpactStoryListResponse(BaseModel):
    items: List[ImpactStoryResponse]
    total: int
    limit: int
    offset: int
