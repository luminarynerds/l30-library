# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class OpenLibraryAuthorResponse(BaseModel):
    name: str
    ol_id: str | None = None


class OpenLibraryBookSummary(BaseModel):
    id: int
    ol_work_id: str
    title: str
    primary_author: str | None = None
    cover_url: str | None = None
    edition_count: int = 0
    languages: str | None = None
    has_fulltext: bool = False

    class Config:
        from_attributes = True


class OpenLibraryBookDetail(BaseModel):
    id: int
    ol_work_id: str
    ol_edition_id: str | None = None
    title: str
    authors: list[OpenLibraryAuthorResponse] | None = None
    subjects: list[str] | None = None
    languages: str | None = None
    first_publish_year: int | None = None
    publisher: str | None = None
    isbn_13: str | None = None
    isbn_10: str | None = None
    has_fulltext: bool = False
    public_scan: bool = False
    cover_url: str | None = None
    availability: dict | None = None
    edition_count: int = 0
    catalog_item_id: int | None = None
    last_synced_at: datetime
    created_at: datetime | None = None
    read_url: str | None = None
    is_favorited: bool = False
    download_history: list["OpenLibraryDownloadResponse"] | None = None

    class Config:
        from_attributes = True


class OpenLibrarySearchQuery(BaseModel):
    query: str | None = Field(None, description="General search query")
    author: str | None = Field(None, description="Filter by author name")
    title: str | None = Field(None, description="Filter by title")
    subject: str | None = Field(None, description="Filter by subject")
    languages: list[str] | None = Field(None, description="Filter by language codes")
    free_only: bool = Field(True, description="Only show free public domain books")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Results per page")


class OpenLibrarySearchResponse(BaseModel):
    count: int
    page: int
    page_size: int
    total_pages: int
    books: list[OpenLibraryBookSummary]
    has_next: bool
    has_previous: bool


class OpenLibraryDownloadCreate(StrictInputSchema):
    book_id: int
    access_type: str = "read_online"


class OpenLibraryDownloadResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    access_type: str
    accessed_at: datetime
    book_title: str | None = None

    class Config:
        from_attributes = True


class OpenLibraryFavoriteCreate(StrictInputSchema):
    book_id: int
    notes: str | None = None


class OpenLibraryFavoriteResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    notes: str | None = None
    created_at: datetime | None = None
    book: OpenLibraryBookSummary | None = None

    class Config:
        from_attributes = True


class OpenLibrarySyncTrigger(BaseModel):
    subject: str | None = Field(None, description="Subject to sync (e.g., 'science_fiction')")
    max_batches: int | None = Field(None, description="Maximum batches to sync")
    free_only: bool = Field(True, description="Only sync free public domain books")


class OpenLibrarySyncStatusResponse(BaseModel):
    id: int
    last_full_sync_at: datetime | None = None
    last_incremental_sync_at: datetime | None = None
    total_books_synced: int
    last_synced_offset: int
    is_syncing: bool
    sync_started_at: datetime | None = None
    sync_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class OpenLibraryStatsResponse(BaseModel):
    total_books: int
    total_downloads: int
    total_favorites: int
    unique_patrons: int
    popular_books: list[OpenLibraryBookSummary]


# Forward reference resolution
OpenLibraryBookDetail.model_rebuild()
