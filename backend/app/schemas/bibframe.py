# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas._base import StrictInputSchema

from ..models.bibframe import (
    AuthoritySource,
    CarrierType,
    ContributorRole,
    InstanceType,
    MediaType,
    WorkType,
)


# ============================================================================
# Base Schemas
# ============================================================================


class LinkedDataMixin(BaseModel):
    uri: Optional[str] = Field(None, max_length=500, description="Canonical URI for this entity")
    linked_data: Optional[dict[str, Any]] = Field(None, description="Additional RDF triples as JSON-LD")


# ============================================================================
# Authority Link Schemas
# ============================================================================


class AuthorityLinkBase(BaseModel):
    source: AuthoritySource = Field(..., description="Authority source (VIAF, LCNAF, etc.)")
    authority_id: str = Field(..., max_length=100, description="ID in the authority source")
    authority_uri: Optional[str] = Field(None, max_length=500, description="Full URI to authority record")
    authority_label: Optional[str] = Field(None, max_length=500, description="Label from authority file")
    link_type: Optional[str] = Field("sameAs", max_length=50, description="Link type (sameAs, closeMatch, etc.)")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score for automatic matches")


class AuthorityLinkCreate(StrictInputSchema, AuthorityLinkBase):
    work_id: Optional[int] = None
    instance_id: Optional[int] = None
    item_id: Optional[int] = None
    contributor_id: Optional[int] = None
    subject_id: Optional[int] = None


class AuthorityLinkResponse(AuthorityLinkBase):
    id: int
    verified: bool = False
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    cached_data: Optional[dict[str, Any]] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Contributor Schemas
# ============================================================================


class ContributorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=500, description="Display name")
    contributor_type: str = Field("person", max_length=20, description="person, organization, or meeting")
    name_inverted: Optional[str] = Field(None, max_length=500, description="Inverted name (Last, First)")
    given_name: Optional[str] = Field(None, max_length=255)
    family_name: Optional[str] = Field(None, max_length=255)
    birth_date: Optional[str] = Field(None, max_length=20)
    death_date: Optional[str] = Field(None, max_length=20)
    organization_type: Optional[str] = Field(None, max_length=100)
    place: Optional[str] = Field(None, max_length=255)
    alternate_names: Optional[list[str]] = None
    biography: Optional[str] = None


class ContributorCreate(StrictInputSchema, ContributorBase, LinkedDataMixin):
    viaf_id: Optional[str] = Field(None, max_length=50)
    lcnaf_id: Optional[str] = Field(None, max_length=50)
    isni: Optional[str] = Field(None, max_length=20)
    orcid: Optional[str] = Field(None, max_length=20)
    wikidata_id: Optional[str] = Field(None, max_length=20)


class ContributorUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    contributor_type: Optional[str] = Field(None, max_length=20)
    name_inverted: Optional[str] = Field(None, max_length=500)
    given_name: Optional[str] = Field(None, max_length=255)
    family_name: Optional[str] = Field(None, max_length=255)
    birth_date: Optional[str] = Field(None, max_length=20)
    death_date: Optional[str] = Field(None, max_length=20)
    biography: Optional[str] = None
    viaf_id: Optional[str] = Field(None, max_length=50)
    lcnaf_id: Optional[str] = Field(None, max_length=50)
    wikidata_id: Optional[str] = Field(None, max_length=20)


class ContributorResponse(ContributorBase, LinkedDataMixin):
    id: int
    name_sort: Optional[str] = None
    viaf_id: Optional[str] = None
    lcnaf_id: Optional[str] = None
    isni: Optional[str] = None
    orcid: Optional[str] = None
    wikidata_id: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContributorBrief(BaseModel):
    id: int
    name: str
    contributor_type: str
    viaf_id: Optional[str] = None

    class Config:
        from_attributes = True


class WorkContributor(ContributorBrief):
    role: ContributorRole = ContributorRole.author
    is_primary: bool = False


# ============================================================================
# Subject Schemas
# ============================================================================


class SubjectBase(BaseModel):
    label: str = Field(..., min_length=1, max_length=500, description="Subject heading")
    subject_type: str = Field("topic", max_length=50, description="topic, place, temporal, person, organization")
    broader_term: Optional[str] = Field(None, max_length=500)
    narrower_terms: Optional[list[str]] = None
    related_terms: Optional[list[str]] = None
    scope_note: Optional[str] = None


class SubjectCreate(StrictInputSchema, SubjectBase, LinkedDataMixin):
    source: Optional[AuthoritySource] = None
    source_id: Optional[str] = Field(None, max_length=100)
    lcsh_id: Optional[str] = Field(None, max_length=50)
    fast_id: Optional[str] = Field(None, max_length=20)
    wikidata_id: Optional[str] = Field(None, max_length=20)


class SubjectResponse(SubjectBase, LinkedDataMixin):
    id: int
    label_normalized: Optional[str] = None
    source: Optional[AuthoritySource] = None
    source_id: Optional[str] = None
    lcsh_id: Optional[str] = None
    fast_id: Optional[str] = None
    wikidata_id: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubjectBrief(BaseModel):
    id: int
    label: str
    subject_type: str
    lcsh_id: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Work Schemas
# ============================================================================


class WorkBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=1000, description="Work title")
    subtitle: Optional[str] = Field(None, max_length=500)
    title_variant: Optional[list[str]] = Field(None, description="Alternative titles")
    work_type: WorkType = Field(WorkType.text, description="Type of work content")
    language: Optional[str] = Field("eng", max_length=10, description="ISO 639-2/B language code")
    original_language: Optional[str] = Field(None, max_length=10)
    summary: Optional[str] = None
    table_of_contents: Optional[str] = None
    genre_form: Optional[list[str]] = None
    intended_audience: Optional[str] = Field(None, max_length=100)
    dewey_classification: Optional[str] = Field(None, max_length=50)
    lc_classification: Optional[str] = Field(None, max_length=50)
    series_title: Optional[str] = Field(None, max_length=500)
    series_number: Optional[str] = Field(None, max_length=50)
    origin_date: Optional[str] = Field(None, max_length=50)
    origin_place: Optional[str] = Field(None, max_length=255)
    notes: Optional[list[str]] = None


class WorkCreate(StrictInputSchema, WorkBase, LinkedDataMixin):
    title_sort: Optional[str] = Field(None, max_length=1000)
    source: Optional[str] = Field(None, max_length=100)
    source_record_id: Optional[str] = Field(None, max_length=100)
    catalog_item_id: Optional[int] = None
    contributor_ids: Optional[list[int]] = Field(None, description="IDs of contributors to link")
    subject_ids: Optional[list[int]] = Field(None, description="IDs of subjects to link")


class WorkUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=1000)
    subtitle: Optional[str] = Field(None, max_length=500)
    title_variant: Optional[list[str]] = None
    work_type: Optional[WorkType] = None
    language: Optional[str] = Field(None, max_length=10)
    summary: Optional[str] = None
    table_of_contents: Optional[str] = None
    genre_form: Optional[list[str]] = None
    intended_audience: Optional[str] = Field(None, max_length=100)
    dewey_classification: Optional[str] = Field(None, max_length=50)
    lc_classification: Optional[str] = Field(None, max_length=50)
    series_title: Optional[str] = Field(None, max_length=500)
    series_number: Optional[str] = Field(None, max_length=50)
    notes: Optional[list[str]] = None


class WorkResponse(WorkBase, LinkedDataMixin):
    id: int
    title_sort: Optional[str] = None
    source: Optional[str] = None
    source_record_id: Optional[str] = None
    catalog_item_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # Nested relationships (optional, loaded when requested)
    contributors: Optional[list[ContributorBrief]] = None
    subjects: Optional[list[SubjectBrief]] = None
    instance_count: Optional[int] = None

    class Config:
        from_attributes = True


class WorkBrief(BaseModel):
    id: int
    title: str
    work_type: WorkType
    language: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Instance Schemas
# ============================================================================


class InstanceBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=1000, description="Instance title")
    subtitle: Optional[str] = Field(None, max_length=500)
    title_statement: Optional[str] = Field(None, max_length=1000)
    instance_type: InstanceType = Field(InstanceType.print, description="Type of instance")
    carrier_type: CarrierType = Field(CarrierType.volume, description="RDA carrier type")
    media_type: MediaType = Field(MediaType.unmediated, description="RDA media type")

    # Identifiers
    isbn_10: Optional[str] = Field(None, max_length=13)
    isbn_13: Optional[str] = Field(None, max_length=17)
    issn: Optional[str] = Field(None, max_length=10)
    lccn: Optional[str] = Field(None, max_length=20)
    oclc_number: Optional[str] = Field(None, max_length=20)

    # Publication info
    publisher: Optional[str] = Field(None, max_length=500)
    publisher_place: Optional[str] = Field(None, max_length=255)
    publication_date: Optional[str] = Field(None, max_length=50)
    publication_year: Optional[int] = Field(None, ge=1, le=9999)
    copyright_date: Optional[str] = Field(None, max_length=20)

    # Edition
    edition: Optional[str] = Field(None, max_length=255)
    edition_number: Optional[int] = None

    # Physical description
    extent: Optional[str] = Field(None, max_length=255)
    dimensions: Optional[str] = Field(None, max_length=100)
    page_count: Optional[int] = None
    illustration_note: Optional[str] = Field(None, max_length=500)

    # Digital info
    digital_format: Optional[str] = Field(None, max_length=100)
    file_size: Optional[str] = Field(None, max_length=50)
    access_url: Optional[str] = Field(None, max_length=1000)

    # Cover
    cover_url: Optional[str] = Field(None, max_length=1000)
    thumbnail_url: Optional[str] = Field(None, max_length=1000)

    # Notes
    notes: Optional[list[str]] = None

    @field_validator('isbn_13')
    @classmethod
    def validate_isbn_13(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Remove hyphens for validation
            isbn_clean = v.replace('-', '').replace(' ', '')
            if len(isbn_clean) != 13 or not isbn_clean.isdigit():
                pass  # Allow flexible input, actual validation elsewhere
        return v


class InstanceCreate(StrictInputSchema, InstanceBase, LinkedDataMixin):
    work_id: int = Field(..., description="ID of the parent Work")
    source: Optional[str] = Field(None, max_length=100)
    source_record_id: Optional[str] = Field(None, max_length=100)
    marc_record: Optional[str] = None
    catalog_item_id: Optional[int] = None
    contributor_ids: Optional[list[int]] = Field(None, description="IDs of instance-specific contributors")


class InstanceUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=1000)
    subtitle: Optional[str] = Field(None, max_length=500)
    instance_type: Optional[InstanceType] = None
    carrier_type: Optional[CarrierType] = None
    media_type: Optional[MediaType] = None
    isbn_10: Optional[str] = Field(None, max_length=13)
    isbn_13: Optional[str] = Field(None, max_length=17)
    publisher: Optional[str] = Field(None, max_length=500)
    publisher_place: Optional[str] = Field(None, max_length=255)
    publication_year: Optional[int] = Field(None, ge=1, le=9999)
    edition: Optional[str] = Field(None, max_length=255)
    extent: Optional[str] = Field(None, max_length=255)
    page_count: Optional[int] = None
    cover_url: Optional[str] = Field(None, max_length=1000)
    notes: Optional[list[str]] = None


class InstanceResponse(InstanceBase, LinkedDataMixin):
    id: int
    work_id: int
    source: Optional[str] = None
    source_record_id: Optional[str] = None
    catalog_item_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # Nested relationships
    work: Optional[WorkBrief] = None
    contributors: Optional[list[ContributorBrief]] = None
    item_count: Optional[int] = None

    class Config:
        from_attributes = True


class InstanceBrief(BaseModel):
    id: int
    title: str
    isbn_13: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None

    class Config:
        from_attributes = True


# ============================================================================
# Item Schemas
# ============================================================================


class ItemBase(BaseModel):
    barcode: Optional[str] = Field(None, max_length=50)
    accession_number: Optional[str] = Field(None, max_length=50)
    copy_number: int = Field(1, ge=1)
    call_number: Optional[str] = Field(None, max_length=100)
    shelving_location: Optional[str] = Field(None, max_length=100)
    sublocation: Optional[str] = Field(None, max_length=100)
    library_branch: str = Field("Main", max_length=100)
    collection: Optional[str] = Field(None, max_length=100)
    circulation_status: str = Field("available", max_length=50)
    is_holdable: bool = True
    is_loanable: bool = True
    condition: str = Field("good", max_length=50)
    condition_notes: Optional[str] = None
    acquisition_date: Optional[datetime] = None
    acquisition_source: Optional[str] = Field(None, max_length=255)
    acquisition_price: Optional[float] = None
    fund_code: Optional[str] = Field(None, max_length=50)
    electronic_locator: Optional[str] = Field(None, max_length=1000)
    access_restrictions: Optional[str] = Field(None, max_length=255)
    public_note: Optional[str] = None
    staff_note: Optional[str] = None


class ItemCreate(StrictInputSchema, ItemBase, LinkedDataMixin):
    instance_id: int = Field(..., description="ID of the parent Instance")
    item_copy_id: Optional[int] = None


class ItemUpdate(StrictInputSchema):
    barcode: Optional[str] = Field(None, max_length=50)
    call_number: Optional[str] = Field(None, max_length=100)
    shelving_location: Optional[str] = Field(None, max_length=100)
    library_branch: Optional[str] = Field(None, max_length=100)
    collection: Optional[str] = Field(None, max_length=100)
    circulation_status: Optional[str] = Field(None, max_length=50)
    is_holdable: Optional[bool] = None
    is_loanable: Optional[bool] = None
    condition: Optional[str] = Field(None, max_length=50)
    condition_notes: Optional[str] = None
    public_note: Optional[str] = None
    staff_note: Optional[str] = None


class ItemResponse(ItemBase, LinkedDataMixin):
    id: int
    instance_id: int
    item_copy_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # Nested relationships
    instance: Optional[InstanceBrief] = None

    class Config:
        from_attributes = True


# ============================================================================
# Search and List Schemas
# ============================================================================


class WorkSearchParams(BaseModel):
    q: Optional[str] = Field(None, max_length=500, description="Full-text search query")
    title: Optional[str] = Field(None, max_length=500)
    contributor: Optional[str] = Field(None, max_length=255, description="Contributor name")
    subject: Optional[str] = Field(None, max_length=255)
    work_type: Optional[WorkType] = None
    language: Optional[str] = Field(None, max_length=10)
    dewey: Optional[str] = Field(None, max_length=50)
    lc_class: Optional[str] = Field(None, max_length=50)
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class InstanceSearchParams(BaseModel):
    q: Optional[str] = Field(None, max_length=500)
    title: Optional[str] = Field(None, max_length=500)
    isbn: Optional[str] = Field(None, max_length=17)
    publisher: Optional[str] = Field(None, max_length=255)
    year_from: Optional[int] = Field(None, ge=1)
    year_to: Optional[int] = Field(None, le=9999)
    instance_type: Optional[InstanceType] = None
    work_id: Optional[int] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class ItemSearchParams(BaseModel):
    barcode: Optional[str] = Field(None, max_length=50)
    call_number: Optional[str] = Field(None, max_length=100)
    branch: Optional[str] = Field(None, max_length=100)
    collection: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=50)
    instance_id: Optional[int] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    per_page: int
    pages: int


class WorkListResponse(PaginatedResponse):
    items: list[WorkResponse]


class InstanceListResponse(PaginatedResponse):
    items: list[InstanceResponse]


class ItemListResponse(PaginatedResponse):
    items: list[ItemResponse]


# ============================================================================
# Linked Data Export Schemas
# ============================================================================


class JsonLdContext(BaseModel):
    context: dict[str, Any] = Field(
        default_factory=lambda: {
            "@vocab": "http://id.loc.gov/ontologies/bibframe/",
            "bf": "http://id.loc.gov/ontologies/bibframe/",
            "bflc": "http://id.loc.gov/ontologies/bflc/",
            "madsrdf": "http://www.loc.gov/mads/rdf/v1#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "schema": "https://schema.org/",
            "dcterms": "http://purl.org/dc/terms/",
            "foaf": "http://xmlns.com/foaf/0.1/",
            "owl": "http://www.w3.org/2002/07/owl#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
        }
    )


class LinkedDataFormat(BaseModel):
    format: str = Field(..., description="Output format: jsonld, turtle, ntriples, rdfxml")


class BibframeExportRequest(StrictInputSchema):
    work_ids: Optional[list[int]] = None
    instance_ids: Optional[list[int]] = None
    item_ids: Optional[list[int]] = None
    format: str = Field("jsonld", description="Output format: jsonld, turtle, ntriples, rdfxml")
    include_authorities: bool = Field(True, description="Include authority links")
    include_schema_org: bool = Field(False, description="Include Schema.org mapping")


# ============================================================================
# MARC Conversion Schemas
# ============================================================================


class MarcToBibframeRequest(StrictInputSchema):
    marc_xml: Optional[str] = Field(None, description="MARC record in XML format")
    marc_json: Optional[dict[str, Any]] = Field(None, description="MARC record in JSON format")
    catalog_item_id: Optional[int] = Field(None, description="Link to existing catalog item")
    create_entities: bool = Field(True, description="Create Work, Instance, and Item records")


class MarcToBibframeResponse(BaseModel):
    work: Optional[WorkResponse] = None
    instance: Optional[InstanceResponse] = None
    items: Optional[list[ItemResponse]] = None
    contributors: Optional[list[ContributorResponse]] = None
    subjects: Optional[list[SubjectResponse]] = None
    warnings: list[str] = Field(default_factory=list)


class BibframeToMarcRequest(StrictInputSchema):
    work_id: Optional[int] = None
    instance_id: Optional[int] = None
    format: str = Field("marcxml", description="Output format: marc21, marcxml")


# ============================================================================
# Library of Congress Import Schemas
# ============================================================================


class LocSearchRequest(StrictInputSchema):
    query: str = Field(..., min_length=1, max_length=500)
    search_type: str = Field("keyword", description="Search type: keyword, title, author, subject, isbn, lccn")
    max_results: int = Field(10, ge=1, le=50)


class LocSearchResult(BaseModel):
    uri: str
    title: str
    contributors: list[str] = Field(default_factory=list)
    publication_info: Optional[str] = None
    identifiers: dict[str, str] = Field(default_factory=dict)
    work_type: Optional[str] = None


class LocSearchResponse(BaseModel):
    results: list[LocSearchResult]
    total_results: int
    query: str


class LocImportRequest(StrictInputSchema):
    uri: str = Field(..., description="URI of the LC BIBFRAME record to import")
    create_work: bool = Field(True, description="Create a Work record")
    create_instance: bool = Field(True, description="Create an Instance record")
    link_authorities: bool = Field(True, description="Link to authority records")
    catalog_item_id: Optional[int] = Field(None, description="Link to existing catalog item")
