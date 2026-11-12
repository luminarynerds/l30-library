# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# ============================================================================
# Enums for BIBFRAME entities
# ============================================================================


class WorkType(StrEnum):
    text = "text"
    cartographic_dataset = "cartographic_dataset"
    cartographic_image = "cartographic_image"
    cartographic_moving_image = "cartographic_moving_image"
    cartographic_tactile_image = "cartographic_tactile_image"
    cartographic_tactile_three_dimensional_form = "cartographic_tactile_three_dimensional_form"
    cartographic_three_dimensional_form = "cartographic_three_dimensional_form"
    computer_dataset = "computer_dataset"
    computer_program = "computer_program"
    notated_movement = "notated_movement"
    notated_music = "notated_music"
    performed_music = "performed_music"
    sounds = "sounds"
    spoken_word = "spoken_word"
    still_image = "still_image"
    tactile_image = "tactile_image"
    tactile_notated_music = "tactile_notated_music"
    tactile_notated_movement = "tactile_notated_movement"
    tactile_text = "tactile_text"
    tactile_three_dimensional_form = "tactile_three_dimensional_form"
    three_dimensional_form = "three_dimensional_form"
    three_dimensional_moving_image = "three_dimensional_moving_image"
    two_dimensional_moving_image = "two_dimensional_moving_image"
    other = "other"


class InstanceType(StrEnum):
    print = "print"
    electronic = "electronic"
    audio = "audio"
    audiovisual = "audiovisual"
    tactile = "tactile"
    microform = "microform"
    manuscript = "manuscript"
    archive = "archive"


class CarrierType(StrEnum):
    volume = "volume"
    audio_disc = "audio_disc"
    computer_disc = "computer_disc"
    online_resource = "online_resource"
    videodisc = "videodisc"
    audiocassette = "audiocassette"
    videocassette = "videocassette"
    microfilm_reel = "microfilm_reel"
    microfiche = "microfiche"
    card = "card"
    sheet = "sheet"
    object = "object"
    other = "other"


class MediaType(StrEnum):
    unmediated = "unmediated"  # Direct human use (print books)
    computer = "computer"      # Requires computer
    audio = "audio"            # Audio playback device
    video = "video"            # Video playback device
    microform = "microform"    # Microform reader
    microscopic = "microscopic"
    projected = "projected"
    stereographic = "stereographic"


class ContributorRole(StrEnum):
    author = "author"
    editor = "editor"
    illustrator = "illustrator"
    translator = "translator"
    composer = "composer"
    lyricist = "lyricist"
    performer = "performer"
    narrator = "narrator"
    director = "director"
    producer = "producer"
    photographer = "photographer"
    compiler = "compiler"
    contributor = "contributor"
    creator = "creator"
    other = "other"


class AuthoritySource(StrEnum):
    VIAF = "viaf"           # Virtual International Authority File
    LCNAF = "lcnaf"         # Library of Congress Name Authority File
    LCCN = "lccn"           # Library of Congress Control Number
    LCSH = "lcsh"           # Library of Congress Subject Headings
    FAST = "fast"           # Faceted Application of Subject Terminology
    WIKIDATA = "wikidata"   # Wikidata
    ISNI = "isni"           # International Standard Name Identifier
    ORCID = "orcid"         # Open Researcher and Contributor ID
    GND = "gnd"             # German National Library (Gemeinsame Normdatei)
    ISBN = "isbn"           # International Standard Book Number
    ISSN = "issn"           # International Standard Serial Number
    DOI = "doi"             # Digital Object Identifier
    OCLC = "oclc"           # OCLC WorldCat number
    LOCAL = "local"         # Library-maintained local authority record


# ============================================================================
# Association tables for many-to-many relationships
# ============================================================================


work_contributors = Table(
    "bibframe_work_contributors",
    Base.metadata,
    Column("work_id", Integer, ForeignKey("bibframe_works.id", ondelete="CASCADE"), primary_key=True),
    Column("contributor_id", Integer, ForeignKey("bibframe_contributors.id", ondelete="CASCADE"), primary_key=True),
    Column("role", SQLEnum(ContributorRole, name="contributorrole", create_type=False, values_callable=lambda x: [e.value for e in x]), default=ContributorRole.author),
    Column("is_primary", Boolean, default=False),
)


work_subjects = Table(
    "bibframe_work_subjects",
    Base.metadata,
    Column("work_id", Integer, ForeignKey("bibframe_works.id", ondelete="CASCADE"), primary_key=True),
    Column("subject_id", Integer, ForeignKey("bibframe_subjects.id", ondelete="CASCADE"), primary_key=True),
)


instance_contributors = Table(
    "bibframe_instance_contributors",
    Base.metadata,
    Column("instance_id", Integer, ForeignKey("bibframe_instances.id", ondelete="CASCADE"), primary_key=True),
    Column("contributor_id", Integer, ForeignKey("bibframe_contributors.id", ondelete="CASCADE"), primary_key=True),
    Column("role", SQLEnum(ContributorRole, name="contributorrole", create_type=False, values_callable=lambda x: [e.value for e in x]), default=ContributorRole.contributor),
)


# ============================================================================
# BIBFRAME Core Models
# ============================================================================


class BibframeWork(Base):
    __tablename__ = "bibframe_works"

    id = Column(Integer, primary_key=True, index=True)

    # Core identifiers
    uri = Column(String(500), nullable=True, index=True)  # Canonical URI

    # Title information (bf:title)
    title = Column(String(1000), nullable=False)
    title_sort = Column(String(1000), nullable=True)  # For sorting (without articles)
    subtitle = Column(String(500), nullable=True)
    title_variant = Column(Text, nullable=True)  # Alternative titles (JSON array)

    # Work type (bf:content)
    work_type = Column(
        SQLEnum(WorkType, name="worktype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=WorkType.text,
        nullable=False,
    )

    # Language (bf:language)
    language = Column(String(10), nullable=True, default="eng")  # ISO 639-2/B code
    original_language = Column(String(10), nullable=True)  # Original language if translated

    # Content description
    summary = Column(Text, nullable=True)  # bf:summary
    table_of_contents = Column(Text, nullable=True)  # bf:tableOfContents

    # Genre/Form (bf:genreForm)
    genre_form = Column(Text, nullable=True)  # JSON array of genres

    # Target audience (bf:intendedAudience)
    intended_audience = Column(String(100), nullable=True)

    # Classification
    dewey_classification = Column(String(50), nullable=True)
    lc_classification = Column(String(50), nullable=True)

    # Series information (bf:hasSeries)
    series_title = Column(String(500), nullable=True)
    series_number = Column(String(50), nullable=True)

    # Origin info
    origin_date = Column(String(50), nullable=True)  # Date of work creation
    origin_place = Column(String(255), nullable=True)  # Place of origin

    # Notes
    notes = Column(Text, nullable=True)  # General notes (JSON array)

    # Administrative
    source = Column(String(100), nullable=True)  # Data source (e.g., "loc", "oclc", "local")
    source_record_id = Column(String(100), nullable=True)  # Original record ID from source

    # Linked data metadata (JSON-LD context extensions)
    linked_data = Column(JSONB, nullable=True)  # Additional RDF triples as JSON

    # Link to existing catalog items (for migration/compatibility)
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    instances = relationship("BibframeInstance", back_populates="work", cascade="all, delete-orphan")
    contributors = relationship("BibframeContributor", secondary=work_contributors, back_populates="works")
    subjects = relationship("BibframeSubject", secondary=work_subjects, back_populates="works")
    authority_links = relationship("AuthorityLink", back_populates="work", cascade="all, delete-orphan",
                                   foreign_keys="AuthorityLink.work_id")
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("uri", name="uq_bibframe_works_uri"),
        Index("ix_bibframe_works_title_author", "title"),
        Index("ix_bibframe_works_dewey", "dewey_classification"),
        Index("ix_bibframe_works_lc", "lc_classification"),
        Index("ix_bibframe_works_language", "language"),
    )

    def __repr__(self):
        return f"<BibframeWork(id={self.id}, title='{self.title[:50]}')>"


class BibframeInstance(Base):
    __tablename__ = "bibframe_instances"

    id = Column(Integer, primary_key=True)

    # Link to parent Work (required)
    work_id = Column(Integer, ForeignKey("bibframe_works.id", ondelete="CASCADE"), nullable=False)

    # Core identifiers
    uri = Column(String(500), nullable=True, index=True)

    # Instance identifiers (bf:identifiedBy)
    isbn_10 = Column(String(13), nullable=True)
    isbn_13 = Column(String(17), nullable=True)
    issn = Column(String(10), nullable=True)
    lccn = Column(String(20), nullable=True)
    oclc_number = Column(String(20), nullable=True)

    # Title (may differ from Work title)
    title = Column(String(1000), nullable=False)
    subtitle = Column(String(500), nullable=True)
    title_statement = Column(String(1000), nullable=True)  # MARC 245 equivalent

    # Instance type
    instance_type = Column(
        SQLEnum(InstanceType, name="instancetype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=InstanceType.print,
        nullable=False,
    )

    # Carrier and media types (RDA)
    carrier_type = Column(
        SQLEnum(CarrierType, name="carriertype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CarrierType.volume,
        nullable=False,
    )
    media_type = Column(
        SQLEnum(MediaType, name="mediatype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=MediaType.unmediated,
        nullable=False,
    )

    # Publication info (bf:provisionActivity)
    publisher = Column(String(500), nullable=True)
    publisher_place = Column(String(255), nullable=True)
    publication_date = Column(String(50), nullable=True)  # Flexible date format
    publication_year = Column(Integer, nullable=True)
    copyright_date = Column(String(20), nullable=True)

    # Edition info (bf:editionStatement)
    edition = Column(String(255), nullable=True)
    edition_number = Column(Integer, nullable=True)

    # Physical description (bf:extent)
    extent = Column(String(255), nullable=True)  # e.g., "352 pages"
    dimensions = Column(String(100), nullable=True)  # e.g., "21 cm"
    page_count = Column(Integer, nullable=True)

    # Format details
    format_details = Column(Text, nullable=True)  # JSON for additional format info
    illustration_note = Column(String(500), nullable=True)

    # Digital/Electronic resource info
    digital_format = Column(String(100), nullable=True)  # e.g., "PDF", "EPUB"
    file_size = Column(String(50), nullable=True)
    access_url = Column(String(1000), nullable=True)

    # Cover image
    cover_url = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)  # JSON array

    # Linked data
    linked_data = Column(JSONB, nullable=True)

    # Source tracking
    source = Column(String(100), nullable=True)
    source_record_id = Column(String(100), nullable=True)
    marc_record = Column(Text, nullable=True)  # Original MARC XML if imported

    # Link to existing catalog items
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    work = relationship("BibframeWork", back_populates="instances")
    items = relationship("BibframeItem", back_populates="instance", cascade="all, delete-orphan")
    contributors = relationship("BibframeContributor", secondary=instance_contributors, back_populates="instances")
    authority_links = relationship("AuthorityLink", back_populates="instance", cascade="all, delete-orphan",
                                   foreign_keys="AuthorityLink.instance_id")
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("uri", name="uq_bibframe_instances_uri"),
        Index("ix_bibframe_instances_isbn", "isbn_10", "isbn_13"),
        Index("ix_bibframe_instances_publisher_year", "publisher", "publication_year"),
    )

    def __repr__(self):
        return f"<BibframeInstance(id={self.id}, title='{self.title[:50]}', isbn='{self.isbn_13}')>"


class BibframeItem(Base):
    __tablename__ = "bibframe_items"

    id = Column(Integer, primary_key=True)

    # Link to parent Instance (required)
    instance_id = Column(Integer, ForeignKey("bibframe_instances.id", ondelete="CASCADE"), nullable=False, index=True)

    # Core identifiers
    uri = Column(String(500), nullable=True, index=True)
    barcode = Column(String(50), nullable=True, index=True)

    # Item-specific identifiers
    accession_number = Column(String(50), nullable=True)
    copy_number = Column(Integer, nullable=True, default=1)

    # Call number / shelving location
    call_number = Column(String(100), nullable=True)
    shelving_location = Column(String(100), nullable=True)
    sublocation = Column(String(100), nullable=True)

    # Physical location
    library_branch = Column(String(100), nullable=True, default="Main")
    collection = Column(String(100), nullable=True)  # e.g., "General", "Reference", "Reserve"

    # Circulation status
    circulation_status = Column(String(50), nullable=True, default="available")
    is_holdable = Column(Boolean, default=True)
    is_loanable = Column(Boolean, default=True)

    # Condition
    condition = Column(String(50), nullable=True, default="good")
    condition_notes = Column(Text, nullable=True)

    # Acquisition info
    acquisition_date = Column(DateTime(timezone=True), nullable=True)
    acquisition_source = Column(String(255), nullable=True)
    acquisition_price = Column(Float, nullable=True)
    fund_code = Column(String(50), nullable=True)

    # Electronic access (for digital items)
    electronic_locator = Column(String(1000), nullable=True)
    access_restrictions = Column(String(255), nullable=True)

    # Notes
    public_note = Column(Text, nullable=True)
    staff_note = Column(Text, nullable=True)

    # Linked data
    linked_data = Column(JSONB, nullable=True)

    # Link to inventory system
    item_copy_id = Column(Integer, ForeignKey("item_copies.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    instance = relationship("BibframeInstance", back_populates="items")
    authority_links = relationship("AuthorityLink", back_populates="item", cascade="all, delete-orphan",
                                   foreign_keys="AuthorityLink.item_id")

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("uri", name="uq_bibframe_items_uri"),
        UniqueConstraint("barcode", name="uq_bibframe_items_barcode"),
        Index("ix_bibframe_items_location", "library_branch", "shelving_location"),
        Index("ix_bibframe_items_call_number", "call_number"),
    )

    def __repr__(self):
        return f"<BibframeItem(id={self.id}, barcode='{self.barcode}', location='{self.shelving_location}')>"


# ============================================================================
# Supporting Models
# ============================================================================


class BibframeContributor(Base):
    __tablename__ = "bibframe_contributors"

    id = Column(Integer, primary_key=True)

    # Core identifiers
    uri = Column(String(500), nullable=True, index=True)

    # Contributor type
    contributor_type = Column(String(20), nullable=False, default="person")  # person, organization, meeting

    # Name fields
    name = Column(String(500), nullable=False)  # Display name
    name_inverted = Column(String(500), nullable=True)  # "Last, First" for persons
    name_sort = Column(String(500), nullable=True)  # Sortable form

    # Person-specific fields
    given_name = Column(String(255), nullable=True)
    family_name = Column(String(255), nullable=True)
    birth_date = Column(String(20), nullable=True)
    death_date = Column(String(20), nullable=True)

    # Organization-specific fields
    organization_type = Column(String(100), nullable=True)  # e.g., "publisher", "government"
    place = Column(String(255), nullable=True)

    # Alternate names / pseudonyms
    alternate_names = Column(Text, nullable=True)  # JSON array

    # Biography / description
    biography = Column(Text, nullable=True)

    # Authority identifiers
    viaf_id = Column(String(50), nullable=True)
    lcnaf_id = Column(String(50), nullable=True, index=True)
    isni = Column(String(20), nullable=True)
    orcid = Column(String(20), nullable=True)
    wikidata_id = Column(String(20), nullable=True)

    # Linked data
    linked_data = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    works = relationship("BibframeWork", secondary=work_contributors, back_populates="contributors")
    instances = relationship("BibframeInstance", secondary=instance_contributors, back_populates="contributors")
    authority_links = relationship("AuthorityLink", back_populates="contributor", cascade="all, delete-orphan",
                                   foreign_keys="AuthorityLink.contributor_id")

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("uri", name="uq_bibframe_contributors_uri"),
        Index("ix_bibframe_contributors_name_type", "name", "contributor_type"),
        Index("ix_bibframe_contributors_viaf", "viaf_id"),
    )

    def __repr__(self):
        return f"<BibframeContributor(id={self.id}, name='{self.name}')>"


class BibframeSubject(Base):
    __tablename__ = "bibframe_subjects"

    id = Column(Integer, primary_key=True, index=True)

    # Core identifiers
    uri = Column(String(500), nullable=True, index=True)

    # Subject type
    subject_type = Column(String(50), nullable=False, default="topic")  # topic, place, temporal, person, organization

    # Subject heading
    label = Column(String(500), nullable=False, index=True)
    label_normalized = Column(String(500), nullable=True)  # Lowercase for searching

    # Hierarchical structure
    broader_term = Column(String(500), nullable=True)
    narrower_terms = Column(Text, nullable=True)  # JSON array
    related_terms = Column(Text, nullable=True)  # JSON array

    # Authority source
    source = Column(
        SQLEnum(AuthoritySource, name="authoritysource", create_type=False, values_callable=lambda x: [e.value for e in x]),
    )
    source_id = Column(String(100), nullable=True)  # ID in the authority source

    # Authority identifiers
    lcsh_id = Column(String(50), nullable=True)
    fast_id = Column(String(20), nullable=True)
    wikidata_id = Column(String(20), nullable=True)

    # Scope note
    scope_note = Column(Text, nullable=True)

    # Linked data
    linked_data = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    works = relationship("BibframeWork", secondary=work_subjects, back_populates="subjects")
    authority_links = relationship("AuthorityLink", back_populates="subject", cascade="all, delete-orphan",
                                   foreign_keys="AuthorityLink.subject_id")

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("uri", name="uq_bibframe_subjects_uri"),
    )

    def __repr__(self):
        return f"<BibframeSubject(id={self.id}, label='{self.label}')>"


class AuthorityLink(Base):
    __tablename__ = "bibframe_authority_links"

    id = Column(Integer, primary_key=True, index=True)

    # Authority source and identifier
    source = Column(
        SQLEnum(AuthoritySource, name="authoritysource", create_type=False, values_callable=lambda x: [e.value for e in x]),
    )
    authority_id = Column(String(100), nullable=False)
    authority_uri = Column(String(500), nullable=True)

    # Label from authority file
    authority_label = Column(String(500), nullable=True)

    # Link type (e.g., "sameAs", "closeMatch", "exactMatch")
    link_type = Column(String(50), nullable=True, default="sameAs")

    # Confidence score (0.0-1.0) for automatic matches
    confidence = Column(Float, nullable=True)

    # Whether this link was verified by a human
    verified = Column(Boolean, default=False)
    verified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Entity links (one of these should be set)
    work_id = Column(Integer, ForeignKey("bibframe_works.id", ondelete="CASCADE"), nullable=True, index=True)
    instance_id = Column(Integer, ForeignKey("bibframe_instances.id", ondelete="CASCADE"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("bibframe_items.id", ondelete="CASCADE"), nullable=True, index=True)
    contributor_id = Column(Integer, ForeignKey("bibframe_contributors.id", ondelete="CASCADE"), nullable=True, index=True)
    subject_id = Column(Integer, ForeignKey("bibframe_subjects.id", ondelete="CASCADE"), nullable=True, index=True)

    # Cached data from authority source
    cached_data = Column(JSONB, nullable=True)
    cache_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    work = relationship("BibframeWork", back_populates="authority_links", foreign_keys=[work_id])
    instance = relationship("BibframeInstance", back_populates="authority_links", foreign_keys=[instance_id])
    item = relationship("BibframeItem", back_populates="authority_links", foreign_keys=[item_id])
    contributor = relationship("BibframeContributor", back_populates="authority_links", foreign_keys=[contributor_id])
    subject = relationship("BibframeSubject", back_populates="authority_links", foreign_keys=[subject_id])

    # Unique constraint: one link per source per entity
    __table_args__ = (
        UniqueConstraint("source", "authority_id", "work_id", name="uq_authority_work"),
        UniqueConstraint("source", "authority_id", "instance_id", name="uq_authority_instance"),
        UniqueConstraint("source", "authority_id", "item_id", name="uq_authority_item"),
        UniqueConstraint("source", "authority_id", "contributor_id", name="uq_authority_contributor"),
        UniqueConstraint("source", "authority_id", "subject_id", name="uq_authority_subject"),
        Index("ix_authority_links_source_id", "source", "authority_id"),
    )

    def __repr__(self):
        return f"<AuthorityLink(id={self.id}, source='{self.source}', authority_id='{self.authority_id}')>"

    @property
    def full_uri(self) -> str:
        uri_templates = {
            AuthoritySource.VIAF: "https://viaf.org/viaf/{id}",
            AuthoritySource.LCNAF: "https://id.loc.gov/authorities/names/{id}",
            AuthoritySource.LCCN: "https://lccn.loc.gov/{id}",
            AuthoritySource.LCSH: "https://id.loc.gov/authorities/subjects/{id}",
            AuthoritySource.FAST: "https://id.worldcat.org/fast/{id}",
            AuthoritySource.WIKIDATA: "https://www.wikidata.org/entity/{id}",
            AuthoritySource.ISNI: "https://isni.org/isni/{id}",
            AuthoritySource.ORCID: "https://orcid.org/{id}",
            AuthoritySource.GND: "https://d-nb.info/gnd/{id}",
            AuthoritySource.ISBN: "urn:isbn:{id}",
            AuthoritySource.ISSN: "urn:issn:{id}",
            AuthoritySource.DOI: "https://doi.org/{id}",
            AuthoritySource.OCLC: "https://www.worldcat.org/oclc/{id}",
            AuthoritySource.LOCAL: "/api/v1/local-authorities/{id}",
        }
        template = uri_templates.get(self.source, "urn:{source}:{id}")
        return template.format(id=self.authority_id, source=self.source.value if self.source else "unknown")
