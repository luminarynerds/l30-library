# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint, ForeignKey, Table
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


# ============================================================================
# Enums
# ============================================================================

class ResourceCategory(StrEnum):
    citizenship = "citizenship"
    permanent_residence = "permanent_residence"
    family_immigration = "family_immigration"
    work_authorization = "work_authorization"
    refugee_asylum = "refugee_asylum"
    naturalization = "naturalization"
    visa_processes = "visa_processes"
    legal_rights = "legal_rights"
    government_benefits = "government_benefits"
    employment_authorization = "employment_authorization"


class ESLLevel(StrEnum):
    beginner = "beginner"
    elementary = "elementary"
    intermediate = "intermediate"
    upper_intermediate = "upper_intermediate"
    advanced = "advanced"
    proficiency = "proficiency"


class ClassScheduleStatus(StrEnum):
    planned = "planned"
    active = "active"
    on_hold = "on_hold"
    completed = "completed"
    cancelled = "cancelled"


class CircleType(StrEnum):
    language_practice = "language_practice"
    cultural_exchange = "cultural_exchange"
    parenting_support = "parenting_support"
    women_empowerment = "women_empowerment"
    job_skills = "job_skills"
    health_wellness = "health_wellness"
    social_integration = "social_integration"
    intergenerational = "intergenerational"


class ProgramType(StrEnum):
    festival = "festival"
    workshop = "workshop"
    performance = "performance"
    celebration = "celebration"
    seminar = "seminar"
    showcase = "showcase"
    social_gathering = "social_gathering"


class TranslationServiceType(StrEnum):
    interpretation = "interpretation"
    document_translation = "document_translation"
    phone_interpretation = "phone_interpretation"
    video_remote_interpretation = "video_remote_interpretation"
    written_translation = "written_translation"
    localization = "localization"


class TranslationStatus(StrEnum):
    pending = "pending"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class ContactRole(StrEnum):
    director = "director"
    coordinator = "coordinator"
    community_outreach = "community_outreach"
    interpreter = "interpreter"
    caseworker = "caseworker"
    volunteer_coordinator = "volunteer_coordinator"
    other = "other"


class PacketType(StrEnum):
    new_resident = "new_resident"
    family = "family"
    senior = "senior"
    youth = "youth"
    job_seeker = "job_seeker"
    student = "student"
    new_parent = "new_parent"


class ImpactStoryStatus(StrEnum):
    draft = "draft"
    submitted = "submitted"
    reviewed = "reviewed"
    published = "published"
    archived = "archived"


class PartnerStatus(StrEnum):
    active = "active"
    inactive = "inactive"
    under_review = "under_review"
    suspended = "suspended"


# ============================================================================
# Core Models
# ============================================================================

class CitizenshipResource(Base, TimestampMixin):
    __tablename__ = "citizenship_resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(SQLEnum(ResourceCategory, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    url = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)
    provider_name = Column(String(300), nullable=True)
    languages_available = Column(ARRAY(String), default=list)
    reading_level = Column(String(50), nullable=True)  # elementary, intermediate, advanced
    is_free = Column(Boolean, default=True)
    phone_number = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    service_area = Column(String(500), nullable=True)
    citizenship_type = Column(String(100), nullable=True)  # naturalization, green card, etc.
    availability_notes = Column(Text, nullable=True)
    tags = Column(ARRAY(String), default=list)
    custom_metadata = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True, index=True)

    __table_args__ = (
        Index('idx_citizenship_category_active', 'category', 'is_active'),
        Index('idx_citizenship_languages', 'languages_available'),
    )


class ESLClass(Base, TimestampMixin):
    __tablename__ = "esl_classes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, index=True)
    description = Column(Text, nullable=True)
    level = Column(SQLEnum(ESLLevel, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    status = Column(SQLEnum(ClassScheduleStatus, values_callable=lambda x: [e.value for e in x]), default=ClassScheduleStatus.planned, index=True)
    instructor_name = Column(String(300), nullable=True)
    instructor_email = Column(String(255), nullable=True)
    instructor_phone = Column(String(20), nullable=True)
    location = Column(String(300), nullable=True)
    virtual_link = Column(String(500), nullable=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=True)
    start_time = Column(String(20), nullable=True)  # HH:MM format
    end_time = Column(String(20), nullable=True)
    day_of_week = Column(ARRAY(String), default=list)  # Monday, Tuesday, etc.
    max_capacity = Column(Integer, nullable=True)
    current_enrollment = Column(Integer, default=0)
    tuition_cost = Column(Float, nullable=True)
    tuition_notes = Column(Text, nullable=True)
    prerequisites = Column(Text, nullable=True)
    skills_covered = Column(ARRAY(String), default=list)
    certifications_offered = Column(ARRAY(String), default=list)
    registration_deadline = Column(Date, nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    is_virtual = Column(Boolean, default=False)
    is_in_person = Column(Boolean, default=True)
    custom_metadata = Column(JSONB, default=dict)

    conversations = relationship("ConversationCircle", back_populates="esl_class", foreign_keys="ConversationCircle.esl_class_id")
    enrollments = relationship("ESLEnrollment", back_populates="esl_class")

    __table_args__ = (
        Index('idx_esl_level_status', 'level', 'status'),
        Index('idx_esl_start_date', 'start_date'),
    )


class ESLEnrollment(Base, TimestampMixin):
    __tablename__ = "esl_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    esl_class_id = Column(Integer, ForeignKey("esl_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_date = Column(Date, nullable=False)
    completion_date = Column(Date, nullable=True)
    status = Column(String(50), default="enrolled", index=True)  # enrolled, completed, dropped, auditing
    attendance_count = Column(Integer, default=0)
    certificate_earned = Column(Boolean, default=False)
    assessment_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    esl_class = relationship("ESLClass", back_populates="enrollments")

    __table_args__ = (
        UniqueConstraint('esl_class_id', 'patron_id', name='uq_esl_class_patron'),
        Index('idx_esl_enrollment_status', 'status'),
    )


class ConversationCircle(Base, TimestampMixin):
    __tablename__ = "conversation_circles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, index=True)
    description = Column(Text, nullable=True)
    circle_type = Column(SQLEnum(CircleType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    facilitator_name = Column(String(300), nullable=True)
    facilitator_email = Column(String(255), nullable=True)
    facilitator_phone = Column(String(20), nullable=True)
    location = Column(String(300), nullable=True)
    virtual_link = Column(String(500), nullable=True)
    schedule_description = Column(String(500), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    start_time = Column(String(20), nullable=True)
    end_time = Column(String(20), nullable=True)
    day_of_week = Column(ARRAY(String), default=list)
    max_capacity = Column(Integer, nullable=True)
    languages_discussed = Column(ARRAY(String), default=list)
    target_age_group = Column(String(100), nullable=True)
    is_free = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True, index=True)
    esl_class_id = Column(Integer, ForeignKey("esl_classes.id", ondelete="SET NULL"), nullable=True)
    custom_metadata = Column(JSONB, default=dict)

    esl_class = relationship("ESLClass", back_populates="conversations", foreign_keys=[esl_class_id])
    sessions = relationship("ConversationCircleSession", back_populates="circle")
    participants = relationship("ConversationCircleParticipant", back_populates="circle")

    __table_args__ = (
        Index('idx_circle_type_active', 'circle_type', 'is_active'),
        Index('idx_circle_start_date', 'start_date'),
    )


class ConversationCircleSession(Base, TimestampMixin):
    __tablename__ = "conversation_circle_sessions"

    id = Column(Integer, primary_key=True, index=True)
    circle_id = Column(Integer, ForeignKey("conversation_circles.id", ondelete="CASCADE"), nullable=False, index=True)
    session_date = Column(Date, nullable=False, index=True)
    session_time = Column(String(20), nullable=True)
    topic = Column(String(300), nullable=True)
    attendance_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    was_held = Column(Boolean, default=True)

    circle = relationship("ConversationCircle", back_populates="sessions")

    __table_args__ = (
        Index('idx_circle_session_date', 'session_date'),
    )


class ConversationCircleParticipant(Base, TimestampMixin):
    __tablename__ = "conversation_circle_participants"

    id = Column(Integer, primary_key=True, index=True)
    circle_id = Column(Integer, ForeignKey("conversation_circles.id", ondelete="CASCADE"), nullable=False, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(300), nullable=True)  # if not patron
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    join_date = Column(Date, nullable=False)
    status = Column(String(50), default="active", index=True)  # active, inactive, completed
    attendance_count = Column(Integer, default=0)

    circle = relationship("ConversationCircle", back_populates="participants")


class CulturalProgram(Base, TimestampMixin):
    __tablename__ = "cultural_programs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, index=True)
    description = Column(Text, nullable=True)
    program_type = Column(SQLEnum(ProgramType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    culture_featured = Column(String(200), nullable=True)
    organizer_name = Column(String(300), nullable=True)
    organizer_email = Column(String(255), nullable=True)
    organizer_phone = Column(String(20), nullable=True)
    event_date = Column(Date, nullable=False, index=True)
    event_time = Column(String(20), nullable=True)
    location = Column(String(300), nullable=True)
    virtual_link = Column(String(500), nullable=True)
    is_virtual = Column(Boolean, default=False)
    is_in_person = Column(Boolean, default=True)
    expected_attendance = Column(Integer, nullable=True)
    actual_attendance = Column(Integer, nullable=True)
    budget = Column(Float, nullable=True)
    partners_involved = Column(ARRAY(String), default=list)
    languages_featured = Column(ARRAY(String), default=list)
    accessibility_notes = Column(Text, nullable=True)
    is_family_friendly = Column(Boolean, default=True)
    cost_notes = Column(Text, nullable=True)
    registration_required = Column(Boolean, default=False)
    registration_url = Column(String(500), nullable=True)
    status = Column(String(50), default="planned", index=True)  # planned, confirmed, completed, cancelled
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    custom_metadata = Column(JSONB, default=dict)

    registrations = relationship("CulturalProgramRegistration", back_populates="program")

    __table_args__ = (
        Index('idx_cultural_event_date', 'event_date'),
        Index('idx_cultural_type_status', 'program_type', 'status'),
    )


class CulturalProgramRegistration(Base, TimestampMixin):
    __tablename__ = "cultural_program_registrations"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("cultural_programs.id", ondelete="CASCADE"), nullable=False, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(300), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    registration_date = Column(Date, nullable=False)
    party_size = Column(Integer, default=1)
    dietary_restrictions = Column(Text, nullable=True)
    accessibility_needs = Column(Text, nullable=True)
    status = Column(String(50), default="registered", index=True)  # registered, attended, no_show, cancelled
    notes = Column(Text, nullable=True)

    program = relationship("CulturalProgram", back_populates="registrations")

    __table_args__ = (
        Index('idx_cultural_registration_status', 'status'),
    )


class TranslationService(Base, TimestampMixin):
    __tablename__ = "translation_services"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, index=True)
    service_type = Column(SQLEnum(TranslationServiceType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    source_language = Column(String(100), nullable=False)
    target_language = Column(String(100), nullable=False)
    provider_name = Column(String(300), nullable=True)
    provider_email = Column(String(255), nullable=True)
    provider_phone = Column(String(20), nullable=True)
    certified = Column(Boolean, default=False)
    specializations = Column(ARRAY(String), default=list)  # medical, legal, etc.
    availability = Column(JSONB, default=dict)  # complex schedule
    hourly_rate = Column(Float, nullable=True)
    contact_method = Column(String(100), nullable=True)  # phone, email, in_person, video
    is_active = Column(Boolean, default=True, index=True)
    service_area = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    custom_metadata = Column(JSONB, default=dict)

    requests = relationship("TranslationRequest", back_populates="service")

    __table_args__ = (
        Index('idx_translation_languages', 'source_language', 'target_language'),
        Index('idx_translation_service_type', 'service_type'),
    )


class TranslationRequest(Base, TimestampMixin):
    __tablename__ = "translation_requests"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("translation_services.id", ondelete="SET NULL"), nullable=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_date = Column(Date, nullable=False, index=True)
    required_date = Column(Date, nullable=True)
    service_type = Column(SQLEnum(TranslationServiceType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    source_language = Column(String(100), nullable=False)
    target_language = Column(String(100), nullable=False)
    document_description = Column(Text, nullable=False)
    document_url = Column(String(500), nullable=True)
    status = Column(SQLEnum(TranslationStatus, values_callable=lambda x: [e.value for e in x]), default=TranslationStatus.pending, index=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    completion_date = Column(Date, nullable=True)
    result_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

    service = relationship("TranslationService", back_populates="requests")

    __table_args__ = (
        Index('idx_translation_request_status', 'status'),
        Index('idx_translation_request_date', 'request_date'),
    )


class CommunityLiaisonContact(Base, TimestampMixin):
    __tablename__ = "community_liaison_contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(150), nullable=False, index=True)
    last_name = Column(String(150), nullable=False, index=True)
    title = Column(String(200), nullable=True)
    role = Column(SQLEnum(ContactRole, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    organization = Column(String(300), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    languages_spoken = Column(ARRAY(String), default=list)
    expertise_areas = Column(ARRAY(String), default=list)
    service_specialties = Column(ARRAY(String), default=list)
    availability_notes = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    community_served = Column(String(300), nullable=True)
    years_of_experience = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text, nullable=True)
    last_contact_date = Column(Date, nullable=True)
    custom_metadata = Column(JSONB, default=dict)

    __table_args__ = (
        UniqueConstraint('email', 'organization', name='uq_liaison_email_org'),
        Index('idx_liaison_role_active', 'role', 'is_active'),
        Index('idx_liaison_languages', 'languages_spoken'),
    )


class MultilingualResource(Base, TimestampMixin):
    __tablename__ = "multilingual_resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    language = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)  # book, video, audio, website, etc.
    author_translator = Column(String(300), nullable=True)
    publication_year = Column(Integer, nullable=True)
    original_language = Column(String(100), nullable=True)
    proficiency_level = Column(String(50), nullable=True)  # beginner, intermediate, advanced
    subject_areas = Column(ARRAY(String), default=list)
    isbn = Column(String(20), nullable=True)
    url = Column(String(500), nullable=True)
    format = Column(String(100), nullable=True)  # hardcover, paperback, digital, etc.
    availability = Column(String(100), nullable=True)  # available, unavailable, on_order
    cultural_relevance = Column(String(200), nullable=True)
    community_request = Column(Boolean, default=False)
    acquisition_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    custom_metadata = Column(JSONB, default=dict)

    __table_args__ = (
        Index('idx_multilingual_language', 'language'),
        Index('idx_multilingual_type', 'resource_type'),
        Index('idx_multilingual_language_type', 'language', 'resource_type'),
    )


class WelcomePacket(Base, TimestampMixin):
    __tablename__ = "welcome_packets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, index=True)
    packet_type = Column(SQLEnum(PacketType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    description = Column(Text, nullable=True)
    languages_included = Column(ARRAY(String), default=list)
    components = Column(ARRAY(String), default=list)  # list of items/documents
    digital_url = Column(String(500), nullable=True)
    print_available = Column(Boolean, default=True)
    digital_available = Column(Boolean, default=True)
    target_audience = Column(String(200), nullable=True)
    creation_date = Column(Date, nullable=False)
    last_updated_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    custom_metadata = Column(JSONB, default=dict)

    assemblies = relationship("WelcomePacketAssembly", back_populates="packet")
    distributions = relationship("WelcomePacketDistribution", back_populates="packet")

    __table_args__ = (
        Index('idx_welcome_packet_type', 'packet_type'),
        Index('idx_welcome_packet_active', 'is_active'),
    )


class WelcomePacketAssembly(Base, TimestampMixin):
    __tablename__ = "welcome_packet_assemblies"

    id = Column(Integer, primary_key=True, index=True)
    packet_id = Column(Integer, ForeignKey("welcome_packets.id", ondelete="CASCADE"), nullable=False, index=True)
    assembly_date = Column(Date, nullable=False, index=True)
    quantity_assembled = Column(Integer, nullable=False)
    assembled_by = Column(String(300), nullable=True)
    volunteer_hours = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    packet = relationship("WelcomePacket", back_populates="assemblies")

    __table_args__ = (
        Index('idx_assembly_date', 'assembly_date'),
    )


class WelcomePacketDistribution(Base, TimestampMixin):
    __tablename__ = "welcome_packet_distributions"

    id = Column(Integer, primary_key=True, index=True)
    packet_id = Column(Integer, ForeignKey("welcome_packets.id", ondelete="CASCADE"), nullable=False, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    distribution_date = Column(Date, nullable=False, index=True)
    quantity_distributed = Column(Integer, default=1)
    distribution_method = Column(String(100), nullable=True)  # in_person, mail, email, digital
    recipient_name = Column(String(300), nullable=True)
    recipient_email = Column(String(255), nullable=True)
    recipient_phone = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)

    packet = relationship("WelcomePacket", back_populates="distributions")

    __table_args__ = (
        Index('idx_distribution_date', 'distribution_date'),
    )


class PartnerOrganization(Base, TimestampMixin):
    __tablename__ = "partner_organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(300), nullable=False, index=True)
    description = Column(Text, nullable=True)
    organization_type = Column(String(200), nullable=True)  # nonprofit, government, business, etc.
    mission = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    primary_email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    languages_served = Column(ARRAY(String), default=list)
    services_offered = Column(ARRAY(String), default=list)
    target_populations = Column(ARRAY(String), default=list)
    service_area = Column(ARRAY(String), default=list)
    partnership_since = Column(Date, nullable=True)
    contact_person_name = Column(String(300), nullable=True)
    contact_person_title = Column(String(200), nullable=True)
    contact_person_email = Column(String(255), nullable=True)
    contact_person_phone = Column(String(20), nullable=True)
    status = Column(SQLEnum(PartnerStatus, values_callable=lambda x: [e.value for e in x]), default=PartnerStatus.active, index=True)
    annual_collaborations = Column(Integer, default=0)
    volunteer_hours_contributed = Column(Float, default=0.0)
    shared_programs = Column(ARRAY(String), default=list)
    resources_shared = Column(Text, nullable=True)
    referral_process = Column(Text, nullable=True)
    eligibility_requirements = Column(Text, nullable=True)
    accessibility_notes = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    custom_metadata = Column(JSONB, default=dict)

    impact_stories = relationship("ImpactStory", back_populates="partner")

    __table_args__ = (
        Index('idx_partner_status', 'status'),
        Index('idx_partner_languages', 'languages_served'),
        Index('idx_partner_services', 'services_offered'),
    )


class ImpactStory(Base, TimestampMixin):
    __tablename__ = "impact_stories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    full_story = Column(Text, nullable=False)
    author_name = Column(String(300), nullable=True)
    author_email = Column(String(255), nullable=True)
    author_role = Column(String(200), nullable=True)  # patron, staff, volunteer, partner
    submitted_date = Column(Date, nullable=False, index=True)
    status = Column(SQLEnum(ImpactStoryStatus, values_callable=lambda x: [e.value for e in x]), default=ImpactStoryStatus.submitted, index=True)
    publication_date = Column(Date, nullable=True)
    featured_on_website = Column(Boolean, default=False)
    featured_on_social_media = Column(Boolean, default=False)
    language = Column(String(100), default="english")
    themes = Column(ARRAY(String), default=list)  # citizenship, community, education, etc.
    related_program = Column(String(300), nullable=True)
    partner_organization_id = Column(Integer, ForeignKey("partner_organizations.id", ondelete="SET NULL"), nullable=True)
    immigrant_experience_years = Column(Integer, nullable=True)  # years in country
    photo_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    consent_to_publish = Column(Boolean, default=False)
    consent_to_attribute = Column(Boolean, default=False)
    reach_count = Column(Integer, default=0)  # views/shares
    reviewer_name = Column(String(300), nullable=True)
    review_date = Column(Date, nullable=True)
    review_notes = Column(Text, nullable=True)
    custom_metadata = Column(JSONB, default=dict)

    partner = relationship("PartnerOrganization", back_populates="impact_stories")

    __table_args__ = (
        Index('idx_impact_status', 'status'),
        Index('idx_impact_submitted_date', 'submitted_date'),
        Index('idx_impact_featured', 'featured_on_website'),
    )
