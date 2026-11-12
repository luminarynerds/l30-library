# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import List, Optional

from ..core.config import get_settings
from pydantic import BaseModel, EmailStr, Field

from app.schemas._base import StrictInputSchema

from ..models.genealogy import CourseLevel, ResearchTopics


# ============ GENEALOGY INQUIRY SCHEMAS ============

class GenealogyInquiryCreate(StrictInputSchema):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    preferred_contact: str = Field("email", pattern="^(email|phone|either)$")
    research_topic: ResearchTopics
    description: str = Field(..., min_length=10, max_length=5000)
    current_challenges: Optional[str] = Field(None, max_length=2000)


class GenealogyInquiryUpdate(StrictInputSchema):
    status: Optional[str] = None
    response_from_genealogist: Optional[str] = None


class GenealogyInquiryResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    preferred_contact: str
    research_topic: str
    description: str
    current_challenges: Optional[str]
    status: str
    response_from_genealogist: Optional[str]
    created_at: datetime | None = None
    responded_at: Optional[datetime]
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class GenealogyInquirySummary(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    research_topic: str
    status: str
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ TRAINING COURSE SCHEMAS ============

class CourseModule(BaseModel):
    title: str
    duration: str  # "15 min", "30 min", etc.
    description: str
    key_topics: List[str]


class GenealogyTrainingCourseCreate(StrictInputSchema):
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    difficulty_level: CourseLevel
    duration_minutes: int = Field(..., gt=0)
    next_session_day: Optional[str] = None
    next_session_time: Optional[str] = None
    location: Optional[str] = None
    modules: Optional[str] = None  # JSON-encoded list
    prerequisites: Optional[str] = None
    is_active: bool = True
    is_virtual: bool = False
    max_enrollment: Optional[int] = None


class GenealogyTrainingCourseUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty_level: Optional[CourseLevel] = None
    duration_minutes: Optional[int] = None
    next_session_day: Optional[str] = None
    next_session_time: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None
    max_enrollment: Optional[int] = None


class GenealogyTrainingCourseResponse(BaseModel):
    id: int
    title: str
    description: str
    difficulty_level: str
    duration_minutes: int
    next_session_day: Optional[str]
    next_session_time: Optional[str]
    location: Optional[str]
    modules: Optional[str]
    prerequisites: Optional[str]
    is_active: bool
    is_virtual: bool
    max_enrollment: Optional[int]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class GenealogyTrainingCoursePublic(BaseModel):
    id: int
    title: str
    description: str
    difficulty_level: str
    duration_minutes: int
    next_session_day: Optional[str]
    next_session_time: Optional[str]

    class Config:
        from_attributes = True


# ============ COURSE ENROLLMENT SCHEMAS ============

class CourseEnrollmentCreate(StrictInputSchema):
    course_id: int


class CourseEnrollmentResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    status: str
    enrolled_at: datetime
    attended_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============ COMMUNITY ARCHIVE SUBMISSION SCHEMAS ============

class CommunityArchiveSubmissionCreate(StrictInputSchema):
    submitter_name: str = Field(..., min_length=1, max_length=255)
    submitter_email: EmailStr
    submitter_phone: Optional[str] = Field(None, max_length=20)
    submitter_relationship: Optional[str] = None
    material_type: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    date_or_period: Optional[str] = None
    location: Optional[str] = None
    people_involved: Optional[str] = None
    historical_significance: Optional[str] = None
    is_public: bool = True
    access_level: str = Field("public", pattern="^(public|restricted|private)$")
    restriction_notes: Optional[str] = None
    submitter_owns_material: bool
    has_permission: Optional[bool] = None
    permission_details: Optional[str] = None
    creative_commons_license: str = "CC-BY-4.0"
    file_url: Optional[str] = None
    file_type: Optional[str] = None


class CommunityArchiveSubmissionUpdate(StrictInputSchema):
    status: Optional[str] = None
    review_notes: Optional[str] = None


class CommunityArchiveSubmissionResponse(BaseModel):
    id: int
    submitter_name: str
    submitter_email: str
    material_type: str
    title: str
    description: str
    date_or_period: Optional[str]
    location: Optional[str]
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True


class CommunityArchiveSubmissionPublic(BaseModel):
    id: int
    submitter_name: str
    material_type: str
    title: str
    description: str
    date_or_period: Optional[str]
    location: Optional[str]
    file_url: Optional[str]
    file_type: Optional[str]
    creative_commons_license: Optional[str]
    published_at: datetime

    class Config:
        from_attributes = True


# ============ DASHBOARD/SUMMARY SCHEMAS ============

class GenealogyDashboard(BaseModel):
    active_courses: int
    pending_inquiries: int
    published_submissions: int
    latest_courses: List[GenealogyTrainingCoursePublic]
    latest_submissions: List[CommunityArchiveSubmissionPublic]
    genealogist_contact_email: str = Field(default_factory=lambda: get_settings().genealogy_email)

    class Config:
        from_attributes = True
