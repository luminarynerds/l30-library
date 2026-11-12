# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from app.models.mixins import TimestampMixin
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Index
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ItemType(StrEnum):
    book = "book"
    audiobook = "audiobook"
    ebook = "ebook"
    dvd = "dvd"
    bluray = "bluray"
    cd = "cd"
    vinyl = "vinyl"
    magazine = "magazine"
    game = "game"
    equipment = "equipment"
    kit = "kit"
    tool = "tool"
    other = "other"


class Audience(StrEnum):
    children = "children"        # ages 0-11
    young_adult = "young_adult"  # 12-18
    adult = "adult"
    all_ages = "all_ages"


class SensitivityLevel(StrEnum):
    PUBLIC = "public"  # Normal - full details in all receipts
    SENSITIVE = "sensitive"  # Medical, legal, adult content - omit from printed receipts
    CONFIDENTIAL = "confidential"  # Extremely sensitive - patron ID only on slips


class MediaFormat(StrEnum):
    dvd = "dvd"
    bluray = "bluray"
    cd = "cd"
    vinyl_lp = "vinyl_lp"
    vinyl_45 = "vinyl_45"
    cassette = "cassette"
    vhs = "vhs"
    laserdisc = "laserdisc"
    other = "other"


class ContentRating(StrEnum):
    # MPAA film ratings
    g = "g"
    pg = "pg"
    pg13 = "pg13"
    r = "r"
    nc17 = "nc17"
    # ESRB game ratings
    e = "e"
    e10 = "e10"
    t = "t"
    m = "m"
    ao = "ao"
    # Music
    explicit = "explicit"
    clean = "clean"
    # General
    unrated = "unrated"
    not_rated = "not_rated"


class ItemStatus(StrEnum):
    available = "available"
    checked_out = "checked_out"
    on_hold = "on_hold"
    in_transit = "in_transit"
    on_order = "on_order"
    in_processing = "in_processing"
    missing = "missing"
    lost = "lost"
    damaged = "damaged"
    withdrawn = "withdrawn"
    reference = "reference"
    restricted = "restricted"
    # Extended statuses for lost/damaged workflows
    lost_by_patron = "lost_by_patron"
    lost_in_transit = "lost_in_transit"
    claims_returned = "claims_returned"
    damaged_repairable = "damaged_repairable"
    damaged_withdrawn = "damaged_withdrawn"
    in_mending = "in_mending"


class CatalogingStatus(StrEnum):

    UNCATALOGED = "uncataloged"
    IN_PROGRESS = "in_progress"
    CATALOGED = "cataloged"


class BookBinding(StrEnum):
    hardback = "hardback"
    paperback = "paperback"
    mass_market = "mass_market"
    board_book = "board_book"
    spiral = "spiral"
    library_binding = "library_binding"
    other = "other"


class CatalogItem(Base, TimestampMixin):
    __tablename__ = "catalog_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(255), nullable=True, index=True)

    item_type = Column(
        SQLEnum(ItemType, name="itemtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ItemType.book,
        nullable=False,
        index=True,
    )
    # Free-form local-taxonomy label when item_type collapses to 'other'.
    # Populated by bulk import when the source ILS uses an item type that
    # doesn't fit L30's 13-value ItemType enum (Koha "Microfiche", Sirsi
    # "ARCHIVE", etc.). NULL for items that fit the canonical enum.
    # Display: render as "{local_type} (other)" when both are set.
    local_type = Column(String(50), nullable=True)

    # Target audience for PLS children's-circulation reporting. NULL until
    # classified (see audience backfill); not a call-number/location heuristic.
    audience = Column(
        SQLEnum(Audience, name="catalogaudience", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        index=True,
    )

    # Physical binding for print books; NULL for all non-book item_types.
    # Indexed sparsely (partial WHERE binding IS NOT NULL) by alembic migration
    # circulation_policy_001.
    binding = Column(
        SQLEnum(BookBinding, name="bookbinding", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    status = Column(
        SQLEnum(ItemStatus, name="itemstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ItemStatus.available,
        nullable=False,
        index=True,
    )

    isbn = Column(String(20), nullable=True, index=True)
    # MARC 010 $a -- Library of Congress Control Number; assigned by LC, stable
    # identifier across record updates. Used for duplicate detection during
    # MARC import alongside ISBN and OCLC#.
    lccn = Column(String(25), nullable=True, index=True)
    # MARC 035 $a -- OCLC number (the OCoLC-prefixed control number from the
    # OCLC bibliographic record). Stripped of the "(OCoLC)" prefix on store.
    oclc_number = Column(String(25), nullable=True, index=True)
    publisher = Column(String(255), nullable=True)
    publication_year = Column(Integer, nullable=True, index=True)
    edition = Column(String(255), nullable=True)  # MARC 250 - Edition statement

    description = Column(Text, nullable=True)
    subjects = Column(String(500), nullable=True, index=True)

    # Series information - MARC 490
    series_name = Column(String(255), nullable=True, index=True)
    series_number = Column(String(50), nullable=True)  # e.g., "Book 1", "Vol. 3"
    # Numeric reading-order position derived from the freeform series_number
    # (MARC 490 $v) by app.services.series_position.parse_series_position. NULL
    # when the enumeration is missing or unparseable. Indexed for ordered
    # series-browse / prev-next on the item page. Never hand-set; always derived
    # in the mapping layer so it stays in sync with series_number.
    series_position = Column(Integer, nullable=True, index=True)

    # Multi-volume / multi-part set membership.
    # Use when this item is one volume of a structured set (multi-volume work,
    # monographic series, numbered set). For loose series identifiers without a
    # MultiPartSet, keep using series_name / series_number above.
    multipart_set_id = Column(
        Integer,
        ForeignKey("multipart_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # String to allow "1A", "2.5", "Suppl.", "Index" — RDA 3.5 / MARC 245 $n
    volume_number = Column(String(50), nullable=True)
    volume_label = Column(String(255), nullable=True)  # e.g. "Vol. 1: Origins"
    sequence_in_set = Column(Integer, nullable=True, index=True)

    cover_url = Column(String(500), nullable=True)
    page_count = Column(Integer, nullable=True)

    # Multimedia fields - DVD/Blu-ray/Video
    director = Column(String(255), nullable=True)
    actors = Column(String(1000), nullable=True)  # Comma-separated list
    runtime_minutes = Column(Integer, nullable=True)  # Duration in minutes
    media_format = Column(
        SQLEnum(MediaFormat, name="mediaformat", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    content_rating = Column(
        SQLEnum(ContentRating, name="contentrating", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    disc_count = Column(Integer, nullable=True)
    studio = Column(String(255), nullable=True)  # Film/recording studio

    # Multimedia fields - CD/Vinyl/Audio
    artist = Column(String(255), nullable=True, index=True)
    track_count = Column(Integer, nullable=True)
    music_genre = Column(String(100), nullable=True)

    # Multimedia fields - Games
    platform = Column(String(100), nullable=True)  # e.g., "PlayStation 5", "Nintendo Switch"
    player_count = Column(String(50), nullable=True)  # e.g., "1-4 players"
    game_genre = Column(String(100), nullable=True)

    # Multimedia fields - Equipment/Kits (cake pans, tools, etc.)
    brand = Column(String(100), nullable=True)
    model_number = Column(String(100), nullable=True)
    dimensions = Column(String(100), nullable=True)  # e.g., "9 inch round", "12x9x3 inches"
    material = Column(String(100), nullable=True)  # e.g., "Aluminum", "Silicone"
    kit_contents = Column(Text, nullable=True)  # List of items in a kit

    # Makerspace / tool library fields
    safety_certification_required = Column(Boolean, default=False, nullable=False, server_default="false")
    certification_name = Column(String(255), nullable=True)  # e.g. 'Table Saw Safety'
    power_source = Column(String(50), nullable=True)  # manual, battery, corded, pneumatic
    voltage = Column(String(50), nullable=True)  # e.g. '120V', '20V battery'
    weight_lbs = Column(String(20), nullable=True)  # string for flexibility: '2.5', '< 1'
    safety_category = Column(String(50), nullable=True)  # hand_tool, power_tool, hazardous, precision
    accessories_included = Column(Text, nullable=True)  # what comes with it
    consumables_needed = Column(Text, nullable=True)  # blades, bits, batteries
    condition_notes = Column(Text, nullable=True)  # current wear state
    replacement_cost = Column(String(20), nullable=True)  # string to allow currency formatting

    location = Column(String(100), nullable=True, index=True)
    barcode = Column(String(50), unique=True, nullable=True)

    # Home-page curation (see app/models/home.py + alembic home_page_001).
    # ORPHANED as of feat/home-staff-picks-shelf: the staff_picks home shelf
    # now reads staff_picks_lists, not these columns. Kept pending a dead-code
    # /migration sweep; no current reader.
    staff_pick = Column(Boolean, nullable=False, server_default="false", default=False)
    featured_at = Column(DateTime(timezone=True), nullable=True)

    # Enhanced cataloging fields
    call_number = Column(String(100), nullable=True)  # e.g., "813.54 SMI" or "F SMI"
    dewey_decimal = Column(String(50), nullable=True)  # DDC classification
    lc_classification = Column(
        String(50), nullable=True
    )  # Library of Congress classification

    cataloging_status = Column(
        SQLEnum(CatalogingStatus, name="catalogingstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CatalogingStatus.UNCATALOGED,
        nullable=False,
        index=True,
    )
    cataloged_at = Column(DateTime(timezone=True), nullable=True)
    cataloged_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Social sharing metrics
    share_count = Column(Integer, default=0, nullable=False)

    # Large print edition flag
    is_large_print = Column(Boolean, default=False, nullable=False, server_default="false", index=True)

    # Lexile reading level
    lexile_measure = Column(String(10), nullable=True)
    lexile_number = Column(Integer, nullable=True, index=True)

    # Content notes for neurodivergent/trauma-sensitive patrons
    content_notes = Column(Text, nullable=True)

    # Privacy settings
    sensitivity_level = Column(
        SQLEnum(SensitivityLevel, name="sensitivitylevel", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=SensitivityLevel.PUBLIC,
        nullable=False
    )

    # Circulation statistics
    total_checkouts = Column(Integer, default=0, nullable=False, index=True)

    # Full-text search vector (maintained by trigger, not ORM). Postgres
    # gets the real TSVECTOR; SQLite (used by several app/tests fixtures
    # that spin up an in-memory schema via Base.metadata.create_all) gets
    # a plain Text column instead of failing to compile the type at all.
    search_tsv = Column(TSVECTOR().with_variant(Text(), "sqlite"), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "publication_year IS NULL OR (publication_year >= 1000 AND publication_year <= 2100)",
            name="ck_catalog_item_publication_year_range",
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count > 0",
            name="ck_catalog_item_page_count_positive",
        ),
        CheckConstraint(
            "runtime_minutes IS NULL OR runtime_minutes > 0",
            name="ck_catalog_item_runtime_positive",
        ),
        CheckConstraint(
            "disc_count IS NULL OR disc_count > 0",
            name="ck_catalog_item_disc_count_positive",
        ),
        CheckConstraint(
            "track_count IS NULL OR track_count > 0",
            name="ck_catalog_item_track_count_positive",
        ),
        CheckConstraint(
            "total_checkouts >= 0",
            name="ck_catalog_item_total_checkouts_non_negative",
        ),
        CheckConstraint(
            "share_count >= 0",
            name="ck_catalog_item_share_count_non_negative",
        ),
        CheckConstraint(
            "sequence_in_set IS NULL OR sequence_in_set > 0",
            name="ck_catalog_item_sequence_in_set_positive",
        ),
        CheckConstraint(
            "lexile_number IS NULL OR (lexile_number >= -400 AND lexile_number <= 2000)",
            name="ck_catalog_item_lexile_range",
        ),
        Index("ix_catalog_items_title_author_pubyear", "title", "author", "publication_year"),
        Index("ix_catalog_items_multipart_sequence", "multipart_set_id", "sequence_in_set"),
    )

    # Relationships with cascade delete for related records
    multipart_set = relationship("MultiPartSet", back_populates="items")
    favorites = relationship(
        "Favorite", back_populates="catalog_item", cascade="all, delete-orphan"
    )
    reading_statuses = relationship("ReadingStatus", back_populates="catalog_item", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="catalog_item", cascade="all, delete-orphan")
    list_items = relationship(
        "ListItem", back_populates="catalog_item", cascade="all, delete-orphan"
    )
    checkouts = relationship("Checkout", back_populates="item")
    holds = relationship("Hold", back_populates="item")
    images = relationship(
        "CatalogImage", back_populates="catalog_item", cascade="all, delete-orphan",
        order_by="CatalogImage.display_order",
    )
    # Normalized subject links. The legacy denormalized ``subjects`` text
    # column above is kept for one release cycle for rollback safety; all
    # read paths now query catalog_item_subjects via Subject.
    subject_links = relationship(
        "CatalogItemSubject",
        back_populates="catalog_item",
        cascade="all, delete-orphan",
        order_by="CatalogItemSubject.position",
        passive_deletes=True,
    )
    acquisition_rationale = relationship(
        "AcquisitionRationale",
        back_populates="catalog_item",
        uselist=False,
        cascade="all, delete-orphan",
    )


class CatalogImage(Base):

    __tablename__ = "catalog_images"

    id = Column(Integer, primary_key=True, index=True)
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url = Column(String(500), nullable=False)
    image_key = Column(String(200), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    caption = Column(String(255), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    file_size = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    catalog_item = relationship("CatalogItem", back_populates="images")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    __table_args__ = (
        Index("ix_catalog_images_item_id", "catalog_item_id"),
        Index("ix_catalog_images_primary", "catalog_item_id", "is_primary"),
    )
