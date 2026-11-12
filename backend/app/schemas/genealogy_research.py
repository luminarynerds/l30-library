# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema

from ..models.genealogy_research import (
    DNAMatchStatus,
    DNATestType,
    DocumentStatus,
    DocumentType,
    ExternalDatabaseSource,
    PersonGender,
    ProjectRole,
    RecordLinkStatus,
    RelationshipType,
    ResearchGuidanceType,
    ResearchNoteType,
    TimelineEventType,
)


# ============================================================================
# RESEARCH PROJECT SCHEMAS
# ============================================================================


class ResearchProjectCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: bool = False
    allow_join_requests: bool = True
    default_license: str = "CC-BY-4.0"


class ResearchProjectUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: Optional[bool] = None
    allow_join_requests: Optional[bool] = None
    default_license: Optional[str] = None


class ResearchProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    is_public: bool
    allow_join_requests: bool
    default_license: str
    person_count: int
    document_count: int
    generation_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ResearchProjectSummary(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    is_public: bool
    person_count: int
    document_count: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# COLLABORATOR SCHEMAS
# ============================================================================


class CollaboratorInvite(BaseModel):
    user_id: int
    role: ProjectRole = ProjectRole.VIEWER


class CollaboratorUpdate(StrictInputSchema):
    role: ProjectRole


class CollaboratorResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: str
    is_active: bool
    accepted_at: Optional[datetime]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# PERSON SCHEMAS
# ============================================================================


class PersonCreate(StrictInputSchema):
    given_names: str = Field(..., min_length=1, max_length=255)
    surname: Optional[str] = Field(None, max_length=255)
    maiden_name: Optional[str] = Field(None, max_length=255)
    suffix: Optional[str] = Field(None, max_length=50)
    prefix: Optional[str] = Field(None, max_length=50)
    nickname: Optional[str] = Field(None, max_length=255)
    alternate_names: Optional[str] = None

    birth_date: Optional[str] = Field(None, max_length=100)
    birth_place: Optional[str] = Field(None, max_length=500)
    death_date: Optional[str] = Field(None, max_length=100)
    death_place: Optional[str] = Field(None, max_length=500)

    gender: Optional[PersonGender] = None
    is_living: bool = False

    occupation: Optional[str] = Field(None, max_length=255)
    religion: Optional[str] = Field(None, max_length=100)
    ethnicity: Optional[str] = Field(None, max_length=100)
    nationality: Optional[str] = Field(None, max_length=100)
    biography: Optional[str] = None

    confidence_level: int = Field(50, ge=0, le=100)
    notes: Optional[str] = None


class PersonUpdate(StrictInputSchema):
    given_names: Optional[str] = Field(None, min_length=1, max_length=255)
    surname: Optional[str] = Field(None, max_length=255)
    maiden_name: Optional[str] = None
    suffix: Optional[str] = None
    prefix: Optional[str] = None
    nickname: Optional[str] = None
    alternate_names: Optional[str] = None

    birth_date: Optional[str] = None
    birth_place: Optional[str] = None
    death_date: Optional[str] = None
    death_place: Optional[str] = None

    gender: Optional[PersonGender] = None
    is_living: Optional[bool] = None

    occupation: Optional[str] = None
    religion: Optional[str] = None
    ethnicity: Optional[str] = None
    nationality: Optional[str] = None
    biography: Optional[str] = None

    confidence_level: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class PersonResponse(BaseModel):
    id: int
    project_id: int
    given_names: str
    surname: Optional[str]
    maiden_name: Optional[str]
    suffix: Optional[str]
    prefix: Optional[str]
    nickname: Optional[str]
    alternate_names: Optional[str]

    birth_date: Optional[str]
    birth_place: Optional[str]
    birth_place_lat: Optional[float]
    birth_place_lng: Optional[float]
    death_date: Optional[str]
    death_place: Optional[str]

    gender: Optional[str]
    is_living: bool

    occupation: Optional[str]
    religion: Optional[str]
    ethnicity: Optional[str]
    nationality: Optional[str]
    biography: Optional[str]
    profile_photo_url: Optional[str]

    confidence_level: int
    is_verified: bool
    notes: Optional[str]

    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class PersonSummary(BaseModel):
    id: int
    given_names: str
    surname: Optional[str]
    birth_date: Optional[str]
    death_date: Optional[str]
    gender: Optional[str]
    is_living: bool
    profile_photo_url: Optional[str]
    confidence_level: int

    class Config:
        from_attributes = True


# ============================================================================
# RELATIONSHIP SCHEMAS
# ============================================================================


class RelationshipCreate(StrictInputSchema):
    person1_id: int
    person2_id: int
    relationship_type: RelationshipType

    marriage_date: Optional[str] = None
    marriage_place: Optional[str] = None
    divorce_date: Optional[str] = None
    is_current: bool = True

    source_citation: Optional[str] = None
    confidence_level: int = Field(50, ge=0, le=100)
    notes: Optional[str] = None


class RelationshipUpdate(StrictInputSchema):
    marriage_date: Optional[str] = None
    marriage_place: Optional[str] = None
    divorce_date: Optional[str] = None
    is_current: Optional[bool] = None
    source_citation: Optional[str] = None
    confidence_level: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class RelationshipResponse(BaseModel):
    id: int
    project_id: int
    person1_id: int
    person2_id: int
    relationship_type: str
    marriage_date: Optional[str]
    marriage_place: Optional[str]
    divorce_date: Optional[str]
    is_current: bool
    source_citation: Optional[str]
    confidence_level: int
    notes: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# FAMILY TREE SCHEMA (composite view)
# ============================================================================


class FamilyTreeNode(BaseModel):
    person: PersonSummary
    parents: List[int] = []  # person IDs
    children: List[int] = []
    spouses: List[int] = []
    siblings: List[int] = []


class FamilyTreeResponse(BaseModel):
    project_id: int
    root_person_id: Optional[int]
    nodes: List[FamilyTreeNode]
    relationships: List[RelationshipResponse]
    generation_count: int
    person_count: int


# ============================================================================
# DOCUMENT SCHEMAS
# ============================================================================


class DocumentCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    document_type: DocumentType
    source_repository: Optional[str] = None
    source_citation: Optional[str] = None

    file_url: Optional[str] = None
    file_type: Optional[str] = None

    document_date: Optional[str] = None
    document_location: Optional[str] = None
    tags: Optional[str] = None  # JSON array


class DocumentUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    document_type: Optional[DocumentType] = None
    source_repository: Optional[str] = None
    source_citation: Optional[str] = None
    document_date: Optional[str] = None
    document_location: Optional[str] = None
    tags: Optional[str] = None
    annotations: Optional[str] = None
    status: Optional[DocumentStatus] = None


class DocumentResponse(BaseModel):
    id: int
    project_id: int
    title: str
    description: Optional[str]
    document_type: str
    source_repository: Optional[str]
    source_citation: Optional[str]

    file_url: Optional[str]
    file_type: Optional[str]
    file_size: Optional[int]
    thumbnail_url: Optional[str]

    ocr_text: Optional[str]
    ocr_confidence: Optional[float]
    ocr_language: Optional[str]
    ocr_processed_at: Optional[datetime]

    document_date: Optional[str]
    document_location: Optional[str]

    status: str
    annotations: Optional[str]
    tags: Optional[str]

    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class DocumentSummary(BaseModel):
    id: int
    title: str
    document_type: str
    status: str
    document_date: Optional[str]
    thumbnail_url: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class PersonDocumentLinkCreate(StrictInputSchema):
    person_id: int
    document_id: int
    role_in_document: Optional[str] = None
    page_number: Optional[int] = None
    excerpt: Optional[str] = None
    notes: Optional[str] = None


class PersonDocumentLinkResponse(BaseModel):
    id: int
    person_id: int
    document_id: int
    role_in_document: Optional[str]
    page_number: Optional[int]
    excerpt: Optional[str]
    notes: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# TIMELINE EVENT SCHEMAS
# ============================================================================


class TimelineEventCreate(StrictInputSchema):
    person_id: int
    event_type: TimelineEventType
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None

    event_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    source_document_id: Optional[int] = None
    source_citation: Optional[str] = None
    confidence_level: int = Field(50, ge=0, le=100)
    media_url: Optional[str] = None


class TimelineEventUpdate(StrictInputSchema):
    event_type: Optional[TimelineEventType] = None
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source_citation: Optional[str] = None
    confidence_level: Optional[int] = Field(None, ge=0, le=100)
    media_url: Optional[str] = None


class TimelineEventResponse(BaseModel):
    id: int
    project_id: int
    person_id: int
    event_type: str
    title: str
    description: Optional[str]
    event_date: Optional[str]
    end_date: Optional[str]
    location: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    source_document_id: Optional[int]
    source_citation: Optional[str]
    confidence_level: int
    media_url: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class PersonTimelineResponse(BaseModel):
    person_id: int
    person_name: str
    events: List[TimelineEventResponse]


class FamilyTimelineResponse(BaseModel):
    project_id: int
    person_ids: List[int]
    events: List[TimelineEventResponse]
    date_range: Optional[Dict[str, str]] = None


# ============================================================================
# RESEARCH NOTE SCHEMAS
# ============================================================================


class ResearchNoteCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    note_type: ResearchNoteType
    person_id: Optional[int] = None
    document_id: Optional[int] = None
    sources: Optional[str] = None  # JSON array
    priority: int = Field(0, ge=0, le=2)
    tags: Optional[str] = None


class ResearchNoteUpdate(StrictInputSchema):
    title: Optional[str] = None
    content: Optional[str] = None
    note_type: Optional[ResearchNoteType] = None
    sources: Optional[str] = None
    is_resolved: Optional[bool] = None
    is_pinned: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=2)
    tags: Optional[str] = None


class ResearchNoteResponse(BaseModel):
    id: int
    project_id: int
    author_id: int
    title: str
    content: str
    note_type: str
    person_id: Optional[int]
    document_id: Optional[int]
    sources: Optional[str]
    is_resolved: bool
    is_pinned: bool
    priority: int
    tags: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# RECORD LINK SCHEMAS
# ============================================================================


class RecordLinkResponse(BaseModel):
    id: int
    project_id: int
    source_document_id: Optional[int]
    target_document_id: Optional[int]
    source_person_id: Optional[int]
    target_person_id: Optional[int]
    similarity_score: float
    match_reasons: Optional[str]
    matched_fields: Optional[str]
    status: str
    reviewer_notes: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class RecordLinkReview(BaseModel):
    status: RecordLinkStatus
    reviewer_notes: Optional[str] = None


# ============================================================================
# DNA SCHEMAS
# ============================================================================


class DNAProfileCreate(StrictInputSchema):
    person_id: int
    test_type: DNATestType
    testing_company: Optional[str] = None
    kit_number: Optional[str] = None
    test_date: Optional[date] = None
    haplogroup: Optional[str] = None
    ethnicity_estimate: Optional[str] = None  # JSON
    consent_given: bool = False
    consent_scope: Optional[str] = None


class DNAProfileResponse(BaseModel):
    id: int
    person_id: int
    project_id: int
    test_type: str
    testing_company: Optional[str]
    kit_number: Optional[str]
    test_date: Optional[date]
    haplogroup: Optional[str]
    ethnicity_estimate: Optional[str]
    consent_given: bool
    consent_scope: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class DNAMatchResponse(BaseModel):
    id: int
    profile1_id: int
    profile2_id: int
    shared_centimorgans: Optional[float]
    shared_segments: Optional[int]
    longest_segment: Optional[float]
    predicted_relationship: Optional[str]
    confidence_level: Optional[float]
    status: str
    notes: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class DNAMatchCreate(StrictInputSchema):
    profile1_id: int
    profile2_id: int
    shared_centimorgans: Optional[float] = None
    shared_segments: Optional[int] = None
    longest_segment: Optional[float] = None
    predicted_relationship: Optional[str] = None
    confidence_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    notes: Optional[str] = None


# ============================================================================
# RESEARCH GUIDANCE SCHEMAS
# ============================================================================


class ResearchGuidanceResponse(BaseModel):
    id: int
    project_id: int
    person_id: Optional[int]
    suggestion_type: str
    title: str
    description: str
    rationale: Optional[str]
    suggested_database: Optional[str]
    suggested_record_type: Optional[str]
    suggested_search_terms: Optional[str]
    suggested_location: Optional[str]
    suggested_date_range: Optional[str]
    priority: int
    is_dismissed: bool
    is_completed: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class GuidanceDismiss(BaseModel):
    is_dismissed: bool = True


class GuidanceComplete(BaseModel):
    is_completed: bool = True


# ============================================================================
# EXTERNAL REFERENCE SCHEMAS
# ============================================================================


class ExternalReferenceCreate(StrictInputSchema):
    person_id: Optional[int] = None
    document_id: Optional[int] = None
    source: ExternalDatabaseSource
    external_id: str = Field(..., max_length=500)
    external_url: Optional[str] = None
    record_title: Optional[str] = None
    record_type: Optional[str] = None


class ExternalReferenceResponse(BaseModel):
    id: int
    project_id: int
    person_id: Optional[int]
    document_id: Optional[int]
    source: str
    external_id: str
    external_url: Optional[str]
    record_title: Optional[str]
    record_type: Optional[str]
    last_synced_at: Optional[datetime]
    sync_status: str
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# SEARCH AND DASHBOARD SCHEMAS
# ============================================================================


class GenealogySearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    search_persons: bool = True
    search_documents: bool = True
    search_notes: bool = True
    project_id: Optional[int] = None


class GenealogySearchResult(BaseModel):
    result_type: str  # "person", "document", "note"
    id: int
    title: str
    snippet: Optional[str]
    project_id: int
    relevance_score: float


class GenealogySearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[GenealogySearchResult]


class ResearchProjectDashboard(BaseModel):
    project: ResearchProjectResponse
    recent_persons: List[PersonSummary]
    recent_documents: List[DocumentSummary]
    pending_record_links: int
    unresolved_notes: int
    active_guidance: List[ResearchGuidanceResponse]
    collaborator_count: int
