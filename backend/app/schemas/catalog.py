# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# ──────────────────────────────────────────────────────────────────────────────
# Validation-Sync Report
# Frontend files that consume this schema's constraints:
#   - frontend/src/utils/inputLimits.ts             (TITLE_MAX, AUTHOR_MAX, ISBN_MAX, PUBLISHER_MAX, DESCRIPTION_MAX, SUBJECTS_MAX, BARCODE_MAX, LOCATION_MAX, COVER_URL_MAX, SEARCH_QUERY_MAX)
#   - frontend/src/components/StaffCatalogingForm.tsx (title, author, isbn, publisher, description, location, barcode, subjects maxLength)
#   - frontend/src/pages/CatalogPage.tsx             (search query maxLength)
# ──────────────────────────────────────────────────────────────────────────────
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from ._base import StrictInputSchema

from ..models.catalog import CatalogingStatus, ItemStatus, ItemType
from ..models.catalog import ContentRating
from ..models.multipart import MultiPartSetType


class CatalogItemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    author: str | None = Field(None, max_length=255)
    item_type: ItemType = ItemType.book
    isbn: str | None = Field(None, max_length=20)
    publisher: str | None = Field(None, max_length=255)
    publication_year: int | None = None
    edition: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=10000)
    subjects: str | None = Field(None, max_length=1000)
    cover_url: str | None = Field(None, max_length=2048)
    page_count: int | None = None
    location: str | None = Field(None, max_length=500)

    # Large print edition
    is_large_print: bool = False
    content_notes: str | None = None

    # Series information - MARC 490
    series_name: str | None = Field(None, max_length=255)
    series_number: str | None = Field(None, max_length=50)

    # Multi-volume / multi-part set membership
    multipart_set_id: int | None = None
    volume_number: str | None = Field(None, max_length=50)
    volume_label: str | None = Field(None, max_length=255)
    sequence_in_set: int | None = Field(None, gt=0)

    # Multimedia fields - DVD/Blu-ray/Video
    director: str | None = Field(None, max_length=255)
    actors: str | None = Field(None, max_length=1000)
    runtime_minutes: int | None = None
    media_format: str | None = Field(None, max_length=100)
    content_rating: ContentRating | None = None
    disc_count: int | None = None
    studio: str | None = Field(None, max_length=255)

    # Multimedia fields - CD/Vinyl/Audio
    artist: str | None = Field(None, max_length=255)
    track_count: int | None = None
    music_genre: str | None = Field(None, max_length=100)

    # Multimedia fields - Games
    platform: str | None = Field(None, max_length=100)
    player_count: str | None = Field(None, max_length=50)
    game_genre: str | None = Field(None, max_length=100)

    # Multimedia fields - Equipment/Kits
    brand: str | None = Field(None, max_length=100)
    model_number: str | None = Field(None, max_length=100)
    dimensions: str | None = Field(None, max_length=100)
    material: str | None = Field(None, max_length=100)
    kit_contents: str | None = Field(None, max_length=5000)

    # Makerspace / tool library fields
    safety_certification_required: bool = False
    certification_name: str | None = Field(None, max_length=255)
    power_source: str | None = Field(None, max_length=50)
    voltage: str | None = Field(None, max_length=50)
    weight_lbs: str | None = Field(None, max_length=20)
    safety_category: str | None = Field(None, max_length=50)
    accessories_included: str | None = Field(None, max_length=5000)
    consumables_needed: str | None = Field(None, max_length=5000)
    condition_notes: str | None = Field(None, max_length=5000)
    replacement_cost: str | None = Field(None, max_length=20)
    lexile_measure: str | None = Field(
        default=None,
        max_length=10,
        description="Lexile measure, e.g. '750L', 'AD650L', 'HL400L', 'BR200L', 'NP'",
    )

    # Staff-pick flag: surfaces a per-card badge and is the data hook the
    # future awards/booklist facet will join in alongside. Detail and list
    # responses both inherit this field via CatalogItemBase.
    staff_pick: bool = False


class CatalogItemCreate(StrictInputSchema, CatalogItemBase):
    # Cataloging workflow fields. The staff "Add Item" form submits barcode +
    # cataloging_status; the model has had these columns the whole time but
    # they weren't declared on the create schema, so Pydantic silently dropped
    # them and every new item persisted as barcode=NULL, status=uncataloged.
    barcode: str | None = Field(None, max_length=50)
    cataloging_status: CatalogingStatus = CatalogingStatus.UNCATALOGED
    call_number: str | None = Field(None, max_length=100)
    dewey_decimal: str | None = Field(None, max_length=50)
    lc_classification: str | None = Field(None, max_length=50)
    # Item availability status. The staff "Add Item" form submits this; the
    # strict create schema 422s on it unless it is declared here.
    status: ItemStatus = ItemStatus.available


class CatalogItemUpdate(StrictInputSchema):
    title: str | None = Field(None, min_length=1, max_length=500)
    author: str | None = Field(None, max_length=255)
    item_type: ItemType | None = None
    status: ItemStatus | None = None
    # Cataloging workflow fields -- see CatalogItemCreate note.
    barcode: str | None = Field(None, max_length=50)
    cataloging_status: CatalogingStatus | None = None
    call_number: str | None = Field(None, max_length=100)
    dewey_decimal: str | None = Field(None, max_length=50)
    lc_classification: str | None = Field(None, max_length=50)
    isbn: str | None = Field(None, max_length=20)
    publisher: str | None = Field(None, max_length=255)
    publication_year: int | None = None
    edition: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=10000)
    subjects: str | None = Field(None, max_length=1000)
    cover_url: str | None = Field(None, max_length=2048)
    page_count: int | None = None
    location: str | None = Field(None, max_length=500)

    # Large print edition
    is_large_print: bool | None = None
    content_notes: str | None = None

    # Series information - MARC 490
    series_name: str | None = Field(None, max_length=255)
    series_number: str | None = Field(None, max_length=50)

    # Multi-volume / multi-part set membership
    multipart_set_id: int | None = None
    volume_number: str | None = Field(None, max_length=50)
    volume_label: str | None = Field(None, max_length=255)
    sequence_in_set: int | None = Field(None, gt=0)

    # Multimedia fields - DVD/Blu-ray/Video
    director: str | None = Field(None, max_length=255)
    actors: str | None = Field(None, max_length=1000)
    runtime_minutes: int | None = None
    media_format: str | None = Field(None, max_length=100)
    content_rating: ContentRating | None = None
    disc_count: int | None = None
    studio: str | None = Field(None, max_length=255)

    # Multimedia fields - CD/Vinyl/Audio
    artist: str | None = Field(None, max_length=255)
    track_count: int | None = None
    music_genre: str | None = Field(None, max_length=100)

    # Multimedia fields - Games
    platform: str | None = Field(None, max_length=100)
    player_count: str | None = Field(None, max_length=50)
    game_genre: str | None = Field(None, max_length=100)

    # Multimedia fields - Equipment/Kits
    brand: str | None = Field(None, max_length=100)
    model_number: str | None = Field(None, max_length=100)
    dimensions: str | None = Field(None, max_length=100)
    material: str | None = Field(None, max_length=100)
    kit_contents: str | None = Field(None, max_length=5000)

    # Makerspace / tool library fields
    safety_certification_required: bool | None = None
    certification_name: str | None = Field(None, max_length=255)
    power_source: str | None = Field(None, max_length=50)
    voltage: str | None = Field(None, max_length=50)
    weight_lbs: str | None = Field(None, max_length=20)
    safety_category: str | None = Field(None, max_length=50)
    accessories_included: str | None = Field(None, max_length=5000)
    consumables_needed: str | None = Field(None, max_length=5000)
    condition_notes: str | None = Field(None, max_length=5000)
    replacement_cost: str | None = Field(None, max_length=20)
    lexile_measure: str | None = None


class MultiPartSetBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    set_type: MultiPartSetType = MultiPartSetType.multivolume
    total_parts: int | None = Field(None, gt=0)
    publisher: str | None = Field(None, max_length=255)
    editor: str | None = Field(None, max_length=255)
    description: str | None = None


class MultiPartSetCreate(StrictInputSchema, MultiPartSetBase):
    pass


class MultiPartSetUpdate(StrictInputSchema):
    title: str | None = Field(None, min_length=1, max_length=500)
    set_type: MultiPartSetType | None = None
    total_parts: int | None = Field(None, gt=0)
    publisher: str | None = Field(None, max_length=255)
    editor: str | None = Field(None, max_length=255)
    description: str | None = None


class MultiPartSetResponse(MultiPartSetBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    lexile_number: int | None = None
    model_config = {"from_attributes": True}


# Statuses where a patron-placed hold would be meaningless or misleading.
# Holds on these are blocked both at the UX layer (available_for_hold signal)
# and server-side at the /holds POST endpoint (422 ITEM_NOT_HOLDABLE).
NON_HOLDABLE_STATUSES: frozenset[ItemStatus] = frozenset({
    ItemStatus.lost,
    ItemStatus.lost_by_patron,
    ItemStatus.lost_in_transit,
    ItemStatus.withdrawn,
    ItemStatus.damaged_withdrawn,
    ItemStatus.missing,
    ItemStatus.reference,
    ItemStatus.restricted,
})


class CatalogItemResponse(CatalogItemBase):
    id: int
    status: ItemStatus
    barcode: str | None
    # Cataloging fields
    call_number: str | None = None
    dewey_decimal: str | None = None
    lc_classification: str | None = None
    cataloging_status: CatalogingStatus | None = None
    cataloged_at: datetime | None = None
    # replacement_cost is inherited from CatalogItemBase (kept there for staff
    # Create/Update input). Override here with exclude=True so it is dropped from
    # PUBLIC/patron serialization; CatalogItemStaffResponse re-adds it un-excluded.
    # cataloged_by_id (internal staff user id) is intentionally NOT declared here
    # to keep it out of public responses; it lives only on CatalogItemStaffResponse.
    replacement_cost: str | None = Field(default=None, exclude=True)
    # Images
    images: list["CatalogImageResponse"] = Field(default_factory=list)
    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None
    lexile_number: int | None = None
    total_checkouts: int = 0
    # Numeric reading-order position derived from series_number; NULL when the
    # freeform enumeration is missing or unparseable. Drives the "Book N in
    # [series]" + prev/next block on the item page.
    series_position: int | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def available_for_hold(self) -> bool:
        return self.status not in NON_HOLDABLE_STATUSES

    model_config = {"from_attributes": True}


class SeriesMemberResponse(BaseModel):
    """One item belonging to a series, in reading order."""

    id: int
    title: str
    author: str | None = None
    item_type: ItemType
    series_position: int | None = None
    series_number: str | None = None
    cover_url: str | None = None
    status: ItemStatus

    model_config = {"from_attributes": True}


class SeriesReadingOrderResponse(BaseModel):
    """Ordered list of the items we hold in a given series.

    ``items`` is sorted by ``series_position`` ascending, NULLs last. This is
    the set of titles in the series that are IN OUR CATALOG -- not the full
    published series -- so ``total_held`` is a holdings count, never a claim
    about how long the series actually is. ``current_position`` is the parsed
    position of the item the patron is viewing (NULL if unparseable), and
    ``prev_id`` / ``next_id`` point to the adjacent held titles by position.
    """

    series_name: str
    total_held: int = Field(..., ge=0, description="How many titles in this series we hold (NOT the series length)")
    current_position: int | None = None
    prev_id: int | None = None
    next_id: int | None = None
    items: list[SeriesMemberResponse] = Field(default_factory=list)


class CatalogSearchParams(StrictInputSchema):
    q: str | None = Field(None, max_length=1000)
    item_type: ItemType | None = None
    status: ItemStatus | None = None
    page: int = 1
    per_page: int = 20
    min_lexile: int | None = Field(default=None, ge=-400, le=2000)
    max_lexile: int | None = Field(default=None, ge=-400, le=2000)


# ============================================================================
# Search Facet Schemas
# ============================================================================


class FacetValue(BaseModel):
    value: str = Field(..., description="The facet value")
    count: int = Field(..., ge=0, description="Number of items matching this value")


class FacetGroup(BaseModel):
    field: str = Field(..., description="The field name for this facet group")
    values: list[FacetValue] = Field(default_factory=list, description="Facet values with counts")


class SearchFacets(BaseModel):
    item_type: list[FacetValue] = Field(default_factory=list, description="Counts by item type")
    status: list[FacetValue] = Field(default_factory=list, description="Counts by status")
    publication_year: list[FacetValue] = Field(default_factory=list, description="Counts by publication year")
    location: list[FacetValue] = Field(default_factory=list, description="Counts by location")
    subject: list[FacetValue] = Field(default_factory=list, description="Counts by subject label (via catalog_item_subjects join)")
    language: list[FacetValue] = Field(default_factory=list, description="Counts by BIBFRAME work language (ISO 639-2/B code; items without a BIBFRAME work omitted)")
    author: list[FacetValue] = Field(default_factory=list, description="Counts by author (exact-match against CatalogItem.author; NULL/empty excluded)")
    series: list[FacetValue] = Field(default_factory=list, description="Counts by series_name (exact-match against CatalogItem.series_name; NULL/empty excluded)")


# ============================================================================
# Paginated Response Schemas for Catalog Endpoints
# ============================================================================


class CatalogPaginatedResponse(BaseModel):
    items: list[CatalogItemResponse] = Field(..., description="List of catalog items")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")
    facets: Optional[SearchFacets] = Field(None, description="Facet counts for search result filtering")
    query_was_all_stopwords: bool = Field(
        False,
        description=(
            "True when the patron q= consisted entirely of English FTS "
            "stopwords (the, of, and, ...). The FTS layer would otherwise "
            "silently return zero results; instead we fall through to the "
            "unfiltered browse and let the UI surface a banner explaining "
            "the query was too common to match on."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [{"id": 1, "title": "Example Book", "status": "available"}],
                "total": 100,
                "page": 1,
                "per_page": 20,
                "pages": 5,
            }
        }
    }


class CatalogAdvancedSearchResponse(CatalogPaginatedResponse):
    search_params: dict = Field(..., description="Search parameters used for the query")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [{"id": 1, "title": "Python Programming", "status": "available"}],
                "total": 50,
                "page": 1,
                "per_page": 20,
                "pages": 3,
                "search_params": {
                    "queries": [{"field": "title", "value": "python", "operator": "AND"}],
                    "filters": {"item_type": "book"},
                },
            }
        }
    }


class CatalogSimpleSearchResponse(BaseModel):
    results: list[CatalogItemResponse] = Field(..., description="Search results")
    total: int = Field(..., ge=0, description="Total number of results")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [{"id": 1, "title": "Python Guide", "status": "available"}],
                "total": 25,
                "page": 1,
                "per_page": 20,
                "pages": 2,
            }
        }
    }


class CatalogNewArrivalsResponse(CatalogPaginatedResponse):
    days: int = Field(..., ge=1, description="Days back to look for new arrivals")
    period: str = Field("week", description="Time period used: 'week' or 'month'")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [{"id": 1, "title": "New Book", "status": "available"}],
                "total": 15,
                "page": 1,
                "per_page": 20,
                "pages": 1,
                "days": 14,
                "period": "week",
            }
        }
    }


class CatalogRandomResponse(BaseModel):
    item: CatalogItemResponse | None = Field(None, description="Random catalog item, or null if nothing matches")

    model_config = {
        "json_schema_extra": {
            "example": {
                "item": {"id": 1, "title": "Random Book", "status": "available"},
            }
        }
    }


# ============================================================================
# Cover Management Response Schemas
# ============================================================================


# ============================================================================
# Catalog Image Schemas
# ============================================================================


class CatalogImageResponse(BaseModel):
    id: int
    catalog_item_id: int
    image_url: str
    is_primary: bool = False
    caption: str | None = None
    display_order: int = 0
    file_size: int | None = None
    content_type: str | None = None
    uploaded_at: datetime
    uploaded_by_id: int | None = None

    model_config = {"from_attributes": True}


class CatalogImageListResponse(BaseModel):
    images: list[CatalogImageResponse] = Field(default_factory=list)
    total: int = Field(..., ge=0)


class CatalogImageUploadResponse(BaseModel):
    success: bool = True
    message: str = "Image uploaded successfully"
    image: CatalogImageResponse


class CatalogImageReorderRequest(StrictInputSchema):
    image_ids: list[int] = Field(..., min_length=1, description="Image IDs in desired display order")


class CatalogItemStaffResponse(CatalogItemResponse):
    """Staff/library-worker catalog response. Re-adds the staff-only fields that
    CatalogItemResponse (the public schema) drops: the internal cataloger user id
    and the un-excluded replacement_cost. Used only by authenticated staff
    endpoints."""

    cataloged_by_id: int | None = None
    replacement_cost: str | None = Field(default=None, max_length=20)


# Resolve forward reference for CatalogImageResponse in CatalogItemResponse
CatalogItemResponse.model_rebuild()
CatalogItemStaffResponse.model_rebuild()


class CoverPopulateResultItem(BaseModel):
    id: int = Field(..., description="Catalog item ID")
    title: str = Field(..., description="Catalog item title")
    status: str = Field(..., description="Result status (updated, no_cover_found, error)")
    cover_url: str | None = Field(None, description="Cover URL if found")
    error: str | None = Field(None, description="Error message if failed")


class CoverPopulateResponse(BaseModel):
    processed: int = Field(..., ge=0, description="Total items processed")
    updated: int = Field(..., ge=0, description="Items with covers updated")
    skipped: int = Field(..., ge=0, description="Items skipped (no cover found)")
    failed: int = Field(..., ge=0, description="Items that failed")
    results: list[CoverPopulateResultItem] = Field(..., description="Detailed results per item")

    model_config = {
        "json_schema_extra": {
            "example": {
                "processed": 50,
                "updated": 35,
                "skipped": 12,
                "failed": 3,
                "results": [
                    {"id": 1, "title": "Book A", "status": "updated", "cover_url": "https://..."},
                    {"id": 2, "title": "Book B", "status": "no_cover_found"},
                    {"id": 3, "title": "Book C", "status": "error", "error": "API timeout"},
                ],
            }
        }
    }


class CoverStatsResponse(BaseModel):
    total_items: int = Field(..., ge=0, description="Total catalog items")
    with_covers: int = Field(..., ge=0, description="Items with cover images")
    without_covers: int = Field(..., ge=0, description="Items without cover images")
    with_isbn_no_cover: int = Field(..., ge=0, description="Items with ISBN but no cover")
    coverage_percent: float = Field(..., ge=0, le=100, description="Percentage of items with covers")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_items": 1000,
                "with_covers": 750,
                "without_covers": 250,
                "with_isbn_no_cover": 180,
                "coverage_percent": 75.0,
            }
        }
    }


# ============================================================================
# Duplicate Detection Response Schemas
# ============================================================================


class DuplicateCandidate(BaseModel):
    id: int = Field(..., description="Catalog item ID")
    title: str = Field(..., description="Item title")
    author: str | None = Field(None, description="Item author")
    isbn: str | None = Field(None, description="Item ISBN")
    item_type: ItemType = Field(..., description="Item type")
    publication_year: int | None = Field(None, description="Publication year")
    match_type: str = Field(..., description="Type of match (isbn, title_author, title)")
    match_confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")


class DuplicateCheckRequest(StrictInputSchema):
    isbn: str | None = Field(None, max_length=20, description="ISBN to check")
    title: str | None = Field(None, max_length=500, description="Title to check")
    author: str | None = Field(None, max_length=255, description="Author to check")
    exclude_id: int | None = Field(None, description="Item ID to exclude (for updates)")


class DuplicateCheckResponse(BaseModel):
    has_duplicates: bool = Field(..., description="Whether potential duplicates were found")
    duplicates: list[DuplicateCandidate] = Field(default_factory=list, description="List of potential duplicates")
    message: str | None = Field(None, description="Human-readable message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "has_duplicates": True,
                "duplicates": [
                    {
                        "id": 123,
                        "title": "The Great Gatsby",
                        "author": "F. Scott Fitzgerald",
                        "isbn": "9780743273565",
                        "item_type": "book",
                        "publication_year": 2004,
                        "match_type": "isbn",
                        "match_confidence": 1.0,
                    }
                ],
                "message": "Found 1 item with matching ISBN",
            }
        }
    }


class BulkUpdateRequest(StrictInputSchema):
    item_ids: list[int] = Field(..., min_length=1, max_length=100, description="Item IDs to update")
    updates: dict = Field(..., description="Fields to update")


class BulkUpdateResponse(BaseModel):
    success_count: int = Field(..., ge=0, description="Number of items updated successfully")
    failure_count: int = Field(..., ge=0, description="Number of items that failed to update")
    errors: list[dict] = Field(default_factory=list, description="Details of failures")


# ============================================================================
# Search Suggestion Response Schemas
# ============================================================================


class SuggestionItem(BaseModel):
    text: str = Field(..., description="Suggestion text (title or author name)")
    type: str = Field(..., description="Suggestion type: 'title' or 'author'")
    item_id: Optional[int] = Field(None, description="Catalog item ID (only for title suggestions)")


class SuggestResponse(BaseModel):
    suggestions: list[SuggestionItem] = Field(default_factory=list, description="List of suggestions")

    model_config = {
        "json_schema_extra": {
            "example": {
                "suggestions": [
                    {"text": "The Great Gatsby", "type": "title", "item_id": 123},
                    {"text": "Gabriel Garcia Marquez", "type": "author", "item_id": None},
                ]
            }
        }
    }
