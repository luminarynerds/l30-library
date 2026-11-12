# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import MoneyDecimal, StrictInputSchema

# ============ Enums (mirror model enums) ============


class AgeRating(str):
    ADULT = "adult"
    TEEN = "teen"
    CHILD = "child"


class ReleaseStatus(str):
    UPCOMING = "upcoming"
    RELEASED = "released"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class ProfileType(str):
    PARENT = "parent"
    CHILD = "child"


class LibraryStatus(str):

    NEW = "new"  # Not in catalog
    OWNED = "owned"  # In inventory
    ON_ORDER = "on_order"  # In active PO


# ============ Author Schemas ============


class AuthorBase(BaseModel):
    name: str = Field(..., max_length=255)
    google_id: str | None = None
    open_library_id: str | None = None
    bio: str | None = None
    image_url: str | None = None


class AuthorCreate(StrictInputSchema, AuthorBase):
    pass


class AuthorUpdate(StrictInputSchema):
    name: str | None = None
    bio: str | None = None
    image_url: str | None = None
    is_active: bool | None = None
    scan_frequency_days: int | None = None


class AuthorResponse(AuthorBase):
    id: UUID
    last_scanned_at: datetime | None = None
    is_active: bool
    follower_count: int = 0
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class AuthorSearchResult(BaseModel):

    source: str  # google_books, open_library
    source_id: str
    name: str
    bio: str | None = None
    image_url: str | None = None
    book_count: int = 0


# ============ Book Schemas ============


class BookBase(BaseModel):
    title: str = Field(..., max_length=500)
    subtitle: str | None = None
    description: str | None = None
    release_date: date | None = None
    is_date_exact: bool = True
    isbn_13: str | None = None
    isbn_10: str | None = None
    age_rating: str = "adult"
    publisher: str | None = None
    page_count: int | None = None
    list_price: MoneyDecimal | None = None
    cover_url: str | None = None


class BookCreate(StrictInputSchema, BookBase):
    author_id: UUID
    google_books_id: str | None = None
    open_library_key: str | None = None
    raw_categories: list[str] = []


class BookUpdate(StrictInputSchema):
    title: str | None = None
    release_date: date | None = None
    is_date_exact: bool | None = None
    status: str | None = None
    isbn_13: str | None = None
    age_rating: str | None = None
    list_price: MoneyDecimal | None = None
    cover_url: str | None = None


class BookResponse(BookBase):
    id: UUID
    author_id: UUID
    author_name: str | None = None
    status: str
    google_books_id: str | None = None
    raw_categories: list = []
    created_at: datetime | None = None
    # tracker_books.age_rating is nullable in the DB; override BookBase to allow None
    # so list endpoints don't 500 on legacy rows with no rating set.
    age_rating: str | None = "adult"
    source: str = "author_scan"
    source_url: str | None = None
    blurb: str | None = None
    blurb_credit: str | None = None
    is_featured: bool = False
    class Config:
        from_attributes = True


class BookWithLibraryStatus(BookResponse):

    library_status: str = "new"  # new, owned, on_order
    demand_score: int = 0  # Count of users following this author


class ExternalBookResult(BaseModel):

    source: str
    source_id: str
    title: str
    subtitle: str | None = None
    authors: list[str] = []
    release_date: date | None = None
    is_date_exact: bool = True
    isbn_13: str | None = None
    isbn_10: str | None = None
    age_rating: str = "adult"
    categories: list[str] = []
    publisher: str | None = None
    page_count: int | None = None
    list_price: float | None = None
    cover_url: str | None = None
    description: str | None = None


class EditorialTitle(BaseModel):
    source: str
    source_url: str | None = None
    title: str
    subtitle: str | None = None
    author_name: str | None = None
    isbn_13: str | None = None
    release_date: date | None = None
    is_date_exact: bool = True
    publisher: str | None = None
    blurb: str | None = None
    blurb_credit: str | None = None
    genre: str | None = None
    age_rating: str = "adult"
    is_featured: bool = False
    list_price: float | None = None


# ============ Follow Schemas ============


class FollowCreate(StrictInputSchema):
    author_id: UUID
    profile_type: str = "parent"
    notify_on_release: bool = True
    notify_days_before: int = 7


class FollowUpdate(StrictInputSchema):
    profile_type: str | None = None
    notify_on_release: bool | None = None
    notify_days_before: int | None = None


class FollowResponse(BaseModel):
    id: int
    user_id: int
    author_id: UUID
    profile_type: str
    notify_on_release: bool
    notify_days_before: int
    author: AuthorResponse | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ Release Feed Schemas ============


class ReleaseFeedItem(BaseModel):

    book: BookResponse
    author: AuthorResponse
    days_until_release: int | None = None
    is_followed: bool = True


class ReleaseFeedResponse(BaseModel):
    items: list[ReleaseFeedItem]
    total: int


# ============ Librarian Schemas ============


class LibrarianReleaseItem(BaseModel):

    book: BookResponse
    author_name: str
    library_status: str  # new, owned, on_order
    demand_score: int  # Count of followers
    catalog_item_id: int | None = None  # If exists in catalog


class LibrarianReleasesResponse(BaseModel):
    items: list[LibrarianReleaseItem]
    total: int
    page: int
    per_page: int


class CreatePOFromReleasesRequest(StrictInputSchema):

    tracker_book_ids: list[UUID]
    vendor_id: int
    fund_id: int
    use_existing_draft: bool = True  # Use existing draft PO if available


class CreatePOFromReleasesResponse(BaseModel):
    purchase_order_id: int
    po_number: str
    items_added: int
    catalog_items_created: int


# ============ Ingestion Schemas ============


class RefreshAuthorRequest(StrictInputSchema):
    force: bool = False  # Force refresh even if recently scanned


class RefreshAllRequest(StrictInputSchema):
    authors_only: bool = False  # Only refresh author metadata, not books
    force: bool = False


class IngestEditorialRequest(StrictInputSchema):
    source: str
    month: str | None = None
    sheet_id: str | None = None


class FeatureUpdateRequest(StrictInputSchema):
    is_featured: bool


class IngestionStats(BaseModel):
    authors_scanned: int
    books_found: int
    books_added: int
    books_updated: int
    duplicates_skipped: int
    errors: int


# ============ API Response Schemas ============


class AuthorSearchResultItem(BaseModel):

    id: str | None = None  # None for external sources
    name: str
    source: str  # "local" or "google_books"
    source_id: str | None = None  # For external sources
    follower_count: int = 0
    image_url: str | None = None


class AuthorSearchResultsResponse(BaseModel):

    results: list[AuthorSearchResultItem]


class FollowedAuthorItem(BaseModel):

    follow_id: int
    author: AuthorResponse
    profile_type: str = "parent"
    notify_on_release: bool = True


class FollowedAuthorsResponse(BaseModel):

    items: list[FollowedAuthorItem]
    total: int


class CreateAndFollowAuthorResponse(BaseModel):

    author: AuthorResponse
    status: str = "following"


class StaffAuthorsResponse(BaseModel):

    items: list[AuthorResponse]
    total: int
    page: int
    per_page: int


class FeaturedUpcomingItem(BaseModel):
    tracker_book_id: UUID
    title: str
    author_name: str | None = None
    isbn_13: str | None = None
    release_date: date | None = None
    is_date_exact: bool = True
    source: str
    source_url: str | None = None
    blurb: str | None = None
    blurb_credit: str | None = None
    library_status: str
    catalog_item_id: int | None = None


class FeaturedUpcomingResponse(BaseModel):
    items: list[FeaturedUpcomingItem]
    total: int
    page: int
    per_page: int
