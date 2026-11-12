# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from enum import StrEnum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# ============================================================================
# ENUMS
# ============================================================================


class ProjectRole(PyEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class PersonGender(PyEnum):
    MALE = "male"
    FEMALE = "female"
    NONBINARY = "nonbinary"
    OTHER = "other"
    UNKNOWN = "unknown"


class RelationshipType(PyEnum):
    PARENT_CHILD = "parent_child"
    SPOUSE = "spouse"
    SIBLING = "sibling"
    ADOPTED = "adopted"
    FOSTER = "foster"
    GUARDIAN = "guardian"
    GODPARENT = "godparent"
    STEP_PARENT = "step_parent"
    OTHER = "other"


class DocumentType(PyEnum):
    BIRTH_CERTIFICATE = "birth_certificate"
    DEATH_CERTIFICATE = "death_certificate"
    MARRIAGE_CERTIFICATE = "marriage_certificate"
    DIVORCE_RECORD = "divorce_record"
    CENSUS_RECORD = "census_record"
    IMMIGRATION_RECORD = "immigration_record"
    MILITARY_RECORD = "military_record"
    LAND_RECORD = "land_record"
    WILL_PROBATE = "will_probate"
    NEWSPAPER_CLIPPING = "newspaper_clipping"
    PHOTOGRAPH = "photograph"
    LETTER = "letter"
    DIARY = "diary"
    CHURCH_RECORD = "church_record"
    SCHOOL_RECORD = "school_record"
    TAX_RECORD = "tax_record"
    NATURALIZATION = "naturalization"
    PASSENGER_LIST = "passenger_list"
    DNA_RESULT = "dna_result"
    OTHER = "other"


class DocumentStatus(PyEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    OCR_COMPLETE = "ocr_complete"
    REVIEWED = "reviewed"
    VERIFIED = "verified"
    REJECTED = "rejected"


class TimelineEventType(PyEnum):
    BIRTH = "birth"
    DEATH = "death"
    MARRIAGE = "marriage"
    DIVORCE = "divorce"
    IMMIGRATION = "immigration"
    EMIGRATION = "emigration"
    MILITARY_SERVICE = "military_service"
    EDUCATION = "education"
    OCCUPATION = "occupation"
    RESIDENCE = "residence"
    RELIGIOUS = "religious"
    MEDICAL = "medical"
    LEGAL = "legal"
    TRAVEL = "travel"
    ACHIEVEMENT = "achievement"
    CUSTOM = "custom"


class ResearchNoteType(PyEnum):
    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    CONCLUSION = "conclusion"
    QUESTION = "question"
    TODO = "todo"
    BRICK_WALL = "brick_wall"
    BREAKTHROUGH = "breakthrough"
    SOURCE_ANALYSIS = "source_analysis"
    METHODOLOGY = "methodology"


class RecordLinkStatus(PyEnum):
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"


class DNATestType(PyEnum):
    AUTOSOMAL = "autosomal"
    Y_DNA = "y_dna"
    MT_DNA = "mt_dna"
    X_DNA = "x_dna"


class DNAMatchStatus(PyEnum):
    NEW = "new"
    REVIEWING = "reviewing"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class ResearchGuidanceType(PyEnum):
    NEXT_RECORD = "next_record"
    ALTERNATE_SPELLING = "alternate_spelling"
    GEOGRAPHIC_LEAD = "geographic_lead"
    TIME_PERIOD_GAP = "time_period_gap"
    RELATIONSHIP_CONFLICT = "relationship_conflict"
    MISSING_SOURCE = "missing_source"
    DATABASE_SUGGESTION = "database_suggestion"
    METHODOLOGY_TIP = "methodology_tip"


class ExternalDatabaseSource(PyEnum):
    FAMILYSEARCH = "familysearch"
    ANCESTRY = "ancestry"
    FINDAGRAVE = "findagrave"
    NEWSPAPERS_COM = "newspapers_com"
    FOLD3 = "fold3"
    MYHERITAGE = "myheritage"
    GENEANET = "geneanet"
    WIKITREE = "wikitree"
    BILLION_GRAVES = "billion_graves"
    OTHER = "other"


# ============================================================================
# RESEARCH PROJECT (top-level container for collaborative research)
# ============================================================================


class GenealogyResearchProject(Base):
    __tablename__ = "genealogy_research_projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Project settings
    is_public = Column(Boolean, default=False, index=True)
    allow_join_requests = Column(Boolean, default=True)
    default_license = Column(String(100), default="CC-BY-4.0")

    # Statistics (denormalized for performance)
    person_count = Column(Integer, default=0)
    document_count = Column(Integer, default=0)
    generation_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    collaborators = relationship("ProjectCollaborator", back_populates="project", cascade="all, delete-orphan")
    persons = relationship("GenealogyPerson", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("GenealogyDocument", back_populates="project", cascade="all, delete-orphan")
    research_notes = relationship("ResearchNote", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<GenealogyResearchProject(id={self.id}, name={self.name})>"


class ProjectCollaborator(Base):
    __tablename__ = "genealogy_project_collaborators"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="unique_project_collaborator"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("genealogy_research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(ProjectRole, values_callable=lambda x: [m.value for m in x]), nullable=False, default=ProjectRole.VIEWER)

    # Collaboration metadata
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    # Timestamps

    # Relationships
    project = relationship("GenealogyResearchProject", back_populates="collaborators")
    user = relationship("User", foreign_keys=[user_id])
    inviter = relationship("User", foreign_keys=[invited_by])

    def __repr__(self) -> str:
        return f"<ProjectCollaborator(project_id={self.project_id}, user_id={self.user_id}, role={self.role})>"


# ============================================================================
# PERSON RECORDS (individuals in the family tree)
# ============================================================================


class GenealogyPerson(Base):
    __tablename__ = "genealogy_persons"
    __table_args__ = (
        Index("ix_genealogy_persons_names", "given_names", "surname"),
        Index("ix_genealogy_persons_project_surname", "project_id", "surname"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("genealogy_research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Names
    given_names = Column(String(255), nullable=False, index=True)
    surname = Column(String(255), nullable=True, index=True)
    maiden_name = Column(String(255), nullable=True)
    suffix = Column(String(50), nullable=True)  # Jr., Sr., III
    prefix = Column(String(50), nullable=True)  # Dr., Rev.
    nickname = Column(String(255), nullable=True)
    alternate_names = Column(Text, nullable=True)  # JSON array of alternate name spellings

    # Vital dates (stored as strings to handle partial dates like "abt 1845")
    birth_date = Column(String(100), nullable=True)
    birth_date_normalized = Column(Date, nullable=True, index=True)  # parsed for sorting/filtering
    birth_place = Column(String(500), nullable=True)
    birth_place_lat = Column(Float, nullable=True)
    birth_place_lng = Column(Float, nullable=True)

    death_date = Column(String(100), nullable=True)
    death_date_normalized = Column(Date, nullable=True, index=True)
    death_place = Column(String(500), nullable=True)
    death_place_lat = Column(Float, nullable=True)
    death_place_lng = Column(Float, nullable=True)

    # Demographics
    gender = Column(Enum(PersonGender, values_callable=lambda x: [m.value for m in x]), nullable=True, index=True)
    is_living = Column(Boolean, default=False, index=True)

    # Biographical info
    occupation = Column(String(255), nullable=True)
    religion = Column(String(100), nullable=True)
    ethnicity = Column(String(100), nullable=True)
    nationality = Column(String(100), nullable=True)
    biography = Column(Text, nullable=True)

    # Media
    profile_photo_url = Column(String(500), nullable=True)

    # Research metadata
    confidence_level = Column(Integer, default=50)  # 0-100 confidence score
    is_verified = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    # Timestamps

    # Relationships
    project = relationship("GenealogyResearchProject", back_populates="persons")
    creator = relationship("User", foreign_keys=[created_by])
    timeline_events = relationship("TimelineEvent", back_populates="person", cascade="all, delete-orphan")
    document_links = relationship("PersonDocumentLink", back_populates="person", cascade="all, delete-orphan")
    dna_profiles = relationship("DNAProfile", back_populates="person", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<GenealogyPerson(id={self.id}, name={self.given_names} {self.surname})>"


# ============================================================================
# FAMILY RELATIONSHIPS
# ============================================================================


class FamilyRelationship(Base):
    __tablename__ = "genealogy_family_relationships"
    __table_args__ = (
        UniqueConstraint("person1_id", "person2_id", "relationship_type", name="unique_family_relationship"),
        Index("ix_genealogy_rel_person1", "person1_id"),
        Index("ix_genealogy_rel_person2", "person2_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("genealogy_research_projects.id", ondelete="CASCADE"), nullable=False, index=True)

    person1_id = Column(Integer, ForeignKey("genealogy_persons.id", ondelete="CASCADE"), nullable=False)
    person2_id = Column(Integer, ForeignKey("genealogy_persons.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(Enum(RelationshipType, values_callable=lambda x: [m.value for m in x]), nullable=False, index=True)

    # For spouse relationships
    marriage_date = Column(String(100), nullable=True)
    marriage_place = Column(String(500), nullable=True)
    divorce_date = Column(String(100), nullable=True)
    is_current = Column(Boolean, default=True)

    # Source and confidence
    source_citation = Column(Text, nullable=True)
    confidence_level = Column(Integer, default=50)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Relationships
    project = relationship("GenealogyResearchProject")
    person1 = relationship("GenealogyPerson", foreign_keys=[person1_id])
    person2 = relationship("GenealogyPerson", foreign_keys=[person2_id])
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<FamilyRelationship(id={self.id}, type={self.relationship_type}, p1={self.person1_id}, p2={self.person2_id})>"


# ============================================================================
# DOCUMENT MANAGEMENT
# ============================================================================


class GenealogyDocument(Base):
    __tablename__ = "genealogy_documents"
    __table_args__ = (
        Index("ix_genealogy_docs_project_type", "project_id", "document_type"),
        Index("ix_genealogy_docs_fulltext", "title", "ocr_text"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("genealogy_research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Document metadata
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    document_type = Column(Enum(DocumentType, values_callable=lambda x: [m.value for m in x]), nullable=False, index=True)
    source_repository = Column(String(500), nullable=True)  # Where the original is held
    source_citation = Column(Text, nullable=True)  # Formal citation

    # File info
    file_url = Column(String(1000), nullable=True)
    file_type = Column(String(50), nullable=True)  # pdf, jpg, png, tiff
    file_size = Column(Integer, nullable=True)  # bytes
    thumbnail_url = Column(String(1000), nullable=True)

    # OCR data
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)  # 0.0-1.0
    ocr_language = Column(String(10), nullable=True)  # ISO 639-1
    ocr_processed_at = Column(DateTime(timezone=True), nullable=True)

    # Document dates and location
    document_date = Column(String(100), nullable=True)
    document_date_normalized = Column(Date, nullable=True, index=True)
    document_location = Column(String(500), nullable=True)

    # Processing status
    status = Column(Enum(DocumentStatus, values_callable=lambda x: [m.value for m in x]), default=DocumentStatus.UPLOADED, index=True)

    # Annotations stored as JSON
    annotations = Column(Text, nullable=True)  # JSON: [{x, y, w, h, label, text}]

    # Tags for organization
    tags = Column(Text, nullable=True)  # JSON array of tag strings

    # Timestamps

    # Relationships
    project = relationship("GenealogyResearchProject", back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    person_links = relationship("PersonDocumentLink", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<GenealogyDocument(id={self.id}, title={self.title}, type={self.document_type})>"


class PersonDocumentLink(Base):
    __tablename__ = "genealogy_person_document_links"
    __table_args__ = (
        UniqueConstraint("person_id", "document_id", name="unique_person_document"),
    )

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("genealogy_persons.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("genealogy_documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # How the person relates to this document
    role_in_document = Column(String(100), nullable=True)  # "subject", "witness", "mentioned"
    page_number = Column(Integer, nullable=True)
    excerpt = Column(Text, nullable=True)  # Relevant excerpt from the document
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Relationships
    person = relationship("GenealogyPerson", back_populates="document_links")
    document = relationship("GenealogyDocument", back_populates="person_links")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<PersonDocumentLink(person_id={self.person_id}, document_id={self.document_id})>"


# ============================================================================
# TIMELINE EVENTS
# ============================================================================


class TimelineEvent(Base):
    __tablename__ = "genealogy_timeline_events"
    __table_args__ = (
        Index("ix_timeline_person_date", "person_id", "event_date_normalized"),
        Index("ix_timeline_project_type", "project_id", "event_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("genealogy_research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("genealogy_persons.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event details
    event_type = Column(Enum(TimelineEventType, values_callable=lambda x: [m.value for m in x]), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Date handling (flexible for partial dates)
    event_date = Column(String(100), nullable=True)
    event_date_normalized = Column(Date, nullable=True, index=True)
    end_date = Column(String(100), nullable=True)  # For ranges (occupation, residence)
    end_date_normalized = Column(Date, nullable=True)

    # Location
    location = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Source
    source_document_id = Column(Integer, ForeignKey("genealogy_documents.id", ondelete="SET NULL"), nullable=True)
    source_citation = Column(Text, nullable=True)
    confidence_level = Column(Integer, default=50)

    # Media
    media_url = Column(String(1000), nullable=True)

    # Timestamps, server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Relationships
    project = relationship("GenealogyResearchProject")
    person = relationship("GenealogyPerson", back_populates="timeline_events")
    source_document = relationship("GenealogyDocument")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<TimelineEvent(id={self.id}, person={self.person_id}, type={self.event_type})>"


# ============================================================================
# RESEARCH NOTES
# ============================================================================


class ResearchNote(Base):
    __tablename__ = "genealogy_research_notes"
    __table_args__ = (
        Index("ix_research_notes_project_type", "project_id", "note_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("genealogy_research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)

    # Note content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(Enum(ResearchNoteType, values_callable=lambda x: [m.value for m in x]), nullable=False, index=True)

    # Linked entities (optional)
    person_id = Column(Integer, ForeignKey("genealogy_persons.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("genealogy_documents.id", ondelete="SET NULL"), nullable=True)

    # Source citations
    sources = Column(Text, nullable=True)  # JSON array of source citations

    # Priority and status
    is_resolved = Column(Boolean, default=False, index=True)
    is_pinned = Column(Boolean, default=False)
    priority = Column(Integer, default=0)  # 0=normal, 1=high, 2=critical

    # Tags
    tags = Column(Text, nullable=True)  # JSON array

    # Timestamps, server_default=func.now(), index=True), server_default=func.now()

    # Relationships
    project = relationship("GenealogyResearchProject", back_populates="research_notes")
    author = relationship("User", foreign_keys=[author_id])
    person = relationship("GenealogyPerson")
    document = relationship("GenealogyDocument")

    def __repr__(self) -> str:
        return f"<ResearchNote(id={self.id}, title={self.title}, type={self.note_type})>"


# ============================================================================
# RECORD LINKING ENGINE
# ============================================================================


class RecordLink(Base):
    __tablename__ = "genealogy_record_links"
    __table_args__ = (
        Index("ix_record_links_project_status", "project_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("genealogy_research_projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # The two entities being linked (can be document-document or person-document)
    source_document_id = Column(Integer, ForeignKey("genealogy_documents.id", ondelete="CASCADE"), nullable=True, index=True)
    target_document_id = Column(Integer, ForeignKey("genealogy_documents.id", ondelete="CASCADE"), nullable=True, index=True)
    source_person_id = Column(Integer, ForeignKey("genealogy_persons.id", ondelete="CASCADE"), nullable=True, index=True)
    target_person_id = Column(Integer, ForeignKey("genealogy_persons.id", ondelete="CASCADE"), nullable=True, index=True)

    # Matching details
    similarity_score = Column(Float, nullable=False, index=True)  # 0.0-1.0
    match_reasons = Column(Text, nullable=True)  # JSON: ["name_match", "date_match", "location_match"]
    matched_fields = Column(Text, nullable=True)  # JSON: {"name": 0.95, "date": 0.80}

    # Status
    status = Column(Enum(RecordLinkStatus, values_callable=lambda x: [m.value for m in x]), default=RecordLinkStatus.SUGGESTED, index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewer_notes = Column(Text, nullable=True)

    # Timestamps, server_default=func.now(), index=True)

    # Relationships
    project = relationship("GenealogyResearchProject")
    source_document = relationship("GenealogyDocument", foreign_keys=[source_document_id])
    target_document = relationship("GenealogyDocument", foreign_keys=[target_document_id])
    source_person = relationship("GenealogyPerson", foreign_keys=[source_person_id])
    target_person = relationship("GenealogyPerson", foreign_keys=[target_person_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self) -> str:
        return f"<RecordLink(id={self.id}, score={self.similarity_score}, status={self.status})>"


# ============================================================================
# DNA MATCHING INTERFACE
# ============================================================================


class DNAProfile(Base):
    __tablename__ = "genealogy_dna_profiles"
    __table_args__ = (
        UniqueConstraint("person_id", "test_type", name="unique_person_dna_test"),
    )

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("genealogy_persons.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("genealogy_research_projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # Test information
    test_type = Column(Enum(DNATestType, values_callable=lambda x: [m.value for m in x]), nullable=False, index=True)
    testing_company = Column(String(255), nullable=True)  # AncestryDNA, 23andMe, etc.
    kit_number = Column(String(100), nullable=True)
    test_date = Column(Date, nullable=True)

    # Results summary
    haplogroup = Column(String(100), nullable=True)  # Y-DNA or mtDNA haplogroup
    ethnicity_estimate = Column(Text, nullable=True)  # JSON of ethnicity percentages

    # Raw data reference (not stored directly for privacy)
    raw_data_file_url = Column(String(1000), nullable=True)
    gedcom_file_url = Column(String(1000), nullable=True)

    # Consent tracking
    consent_given = Column(Boolean, default=False)
    consent_date = Column(DateTime(timezone=True), nullable=True)
    consent_scope = Column(String(255), nullable=True)  # What was consented to

    # Timestamps, server_default=func.now()), server_default=func.now()
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Relationships
    person = relationship("GenealogyPerson", back_populates="dna_profiles")
    project = relationship("GenealogyResearchProject")
    creator = relationship("User", foreign_keys=[created_by])
    matches = relationship("DNAMatch", foreign_keys="DNAMatch.profile1_id", back_populates="profile1", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<DNAProfile(id={self.id}, person={self.person_id}, test={self.test_type})>"


class DNAMatch(Base):
    __tablename__ = "genealogy_dna_matches"
    __table_args__ = (
        UniqueConstraint("profile1_id", "profile2_id", name="unique_dna_match"),
        Index("ix_dna_matches_shared_cm", "shared_centimorgans"),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile1_id = Column(Integer, ForeignKey("genealogy_dna_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    profile2_id = Column(Integer, ForeignKey("genealogy_dna_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    # Match metrics
    shared_centimorgans = Column(Float, nullable=True)
    shared_segments = Column(Integer, nullable=True)
    longest_segment = Column(Float, nullable=True)
    predicted_relationship = Column(String(255), nullable=True)  # "2nd cousin", "half sibling"
    confidence_level = Column(Float, nullable=True)  # 0.0-1.0

    # Status
    status = Column(Enum(DNAMatchStatus, values_callable=lambda x: [m.value for m in x]), default=DNAMatchStatus.NEW, index=True)
    notes = Column(Text, nullable=True)

    # Timestamps, server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    profile1 = relationship("DNAProfile", foreign_keys=[profile1_id], back_populates="matches")
    profile2 = relationship("DNAProfile", foreign_keys=[profile2_id])

    def __repr__(self) -> str:
        return f"<DNAMatch(id={self.id}, cm={self.shared_centimorgans}, predicted={self.predicted_relationship})>"


# ============================================================================
# RESEARCH GUIDANCE (AI-powered suggestions)
# ============================================================================


class ResearchGuidanceSuggestion(Base):
    __tablename__ = "genealogy_research_guidance"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("genealogy_research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("genealogy_persons.id", ondelete="SET NULL"), nullable=True, index=True)

    # Suggestion details
    suggestion_type = Column(Enum(ResearchGuidanceType, values_callable=lambda x: [m.value for m in x]), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)  # Why this was suggested

    # Actionable details
    suggested_database = Column(Enum(ExternalDatabaseSource, values_callable=lambda x: [m.value for m in x]), nullable=True)
    suggested_record_type = Column(String(100), nullable=True)
    suggested_search_terms = Column(Text, nullable=True)  # JSON array
    suggested_location = Column(String(500), nullable=True)
    suggested_date_range = Column(String(100), nullable=True)

    # Priority and status
    priority = Column(Integer, default=0, index=True)  # 0=low, 1=medium, 2=high
    is_dismissed = Column(Boolean, default=False, index=True)
    is_completed = Column(Boolean, default=False, index=True)
    completed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps, server_default=func.now(), index=True)

    # Relationships
    project = relationship("GenealogyResearchProject")
    person = relationship("GenealogyPerson")
    completer = relationship("User", foreign_keys=[completed_by])

    def __repr__(self) -> str:
        return f"<ResearchGuidanceSuggestion(id={self.id}, type={self.suggestion_type}, title={self.title})>"


# ============================================================================
# EXTERNAL DATABASE INTEGRATION
# ============================================================================


class ExternalRecordReference(Base):
    __tablename__ = "genealogy_external_references"
    __table_args__ = (
        UniqueConstraint("person_id", "source", "external_id", name="unique_external_ref"),
        Index("ix_external_refs_source", "source"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("genealogy_research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("genealogy_persons.id", ondelete="CASCADE"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("genealogy_documents.id", ondelete="CASCADE"), nullable=True)

    # External reference details
    source = Column(Enum(ExternalDatabaseSource, values_callable=lambda x: [m.value for m in x]), nullable=False)
    external_id = Column(String(500), nullable=False, index=True)  # ID in the external system
    external_url = Column(String(1000), nullable=True)
    record_title = Column(String(500), nullable=True)
    record_type = Column(String(100), nullable=True)

    # Sync metadata
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String(50), default="manual")  # manual, auto_synced, outdated

    # Timestamps, server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Relationships
    project = relationship("GenealogyResearchProject")
    person = relationship("GenealogyPerson")
    document = relationship("GenealogyDocument")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<ExternalRecordReference(id={self.id}, source={self.source}, ext_id={self.external_id})>"
