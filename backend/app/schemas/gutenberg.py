# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema

from ..models.gutenberg import GutenbergFormat


# ============================================================================
# Author Schemas
# ============================================================================


class GutenbergAuthorResponse(BaseModel):
    name: str
    birth_year: int | None = None
    death_year: int | None = None


# ============================================================================
# Book Schemas
# ============================================================================


class GutenbergBookBase(BaseModel):
    gutenberg_id: int
    title: str
    languages: str | None = None
    copyright_status: bool = False
    media_type: str = "Text"
    download_count: int = 0


class GutenbergBookResponse(GutenbergBookBase):
    id: int
    authors: list[GutenbergAuthorResponse] | None = None
    subjects: list[str] | None = None
    bookshelves: list[str] | None = None
    formats: dict[str, str] | None = None
    cover_url: str | None = None
    catalog_item_id: int | None = None
    last_synced_at: datetime
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class GutenbergBookDetail(GutenbergBookResponse):
    epub_url: str | None = None
    kindle_url: str | None = None
    html_url: str | None = None
    text_url: str | None = None
    pdf_url: str | None = None
    is_favorited: bool = False
    download_history: list["GutenbergDownloadResponse"] | None = None


class GutenbergBookSummary(BaseModel):
    id: int
    gutenberg_id: int
    title: str
    primary_author: str | None = None
    cover_url: str | None = None
    download_count: int = 0
    languages: str | None = None

    class Config:
        from_attributes = True


# ============================================================================
# Search Schemas
# ============================================================================


class GutenbergSearchQuery(BaseModel):
    query: str | None = Field(None, description="General search query")
    author: str | None = Field(None, description="Filter by author name")
    title: str | None = Field(None, description="Filter by title")
    topic: str | None = Field(None, description="Filter by subject/bookshelf")
    languages: list[str] | None = Field(None, description="Filter by language codes")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(32, ge=1, le=100, description="Results per page")


class GutenbergSearchResponse(BaseModel):
    count: int
    page: int
    page_size: int
    total_pages: int
    books: list[GutenbergBookSummary]
    has_next: bool
    has_previous: bool


# ============================================================================
# Download Schemas
# ============================================================================


class GutenbergDownloadCreate(StrictInputSchema):
    book_id: int
    format: GutenbergFormat


class GutenbergDownloadResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    format: GutenbergFormat
    downloaded_at: datetime
    book_title: str | None = None

    class Config:
        from_attributes = True


# ============================================================================
# Favorite Schemas
# ============================================================================


class GutenbergFavoriteCreate(StrictInputSchema):
    book_id: int
    notes: str | None = None


class GutenbergFavoriteUpdate(StrictInputSchema):
    notes: str | None = None


class GutenbergFavoriteResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    notes: str | None = None
    created_at: datetime | None = None
    book: GutenbergBookSummary | None = None

    class Config:
        from_attributes = True


# ============================================================================
# Sync Status Schemas
# ============================================================================


class GutenbergSyncStatusResponse(BaseModel):
    id: int
    last_full_sync_at: datetime | None = None
    last_incremental_sync_at: datetime | None = None
    total_books_synced: int
    last_synced_page: int
    is_syncing: bool
    sync_started_at: datetime | None = None
    sync_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class GutenbergSyncTrigger(BaseModel):
    full_sync: bool = Field(False, description="Perform full sync instead of incremental")
    max_pages: int | None = Field(None, description="Maximum pages to sync (for testing)")
    languages: list[str] | None = Field(None, description="Filter by languages")


# ============================================================================
# Statistics Schemas
# ============================================================================


class GutenbergStatsResponse(BaseModel):
    total_books: int
    total_downloads: int
    total_favorites: int
    unique_patrons_downloaded: int
    popular_books: list[GutenbergBookSummary]
    popular_subjects: list[dict]
    downloads_by_format: dict[str, int]
    recent_downloads: list[GutenbergDownloadResponse]


class GutenbergPatronDashboard(BaseModel):
    recent_downloads: list[GutenbergDownloadResponse]
    favorites: list[GutenbergFavoriteResponse]
    total_downloads: int
    total_favorites: int
    recommended_books: list[GutenbergBookSummary]


# Forward reference resolution
GutenbergBookDetail.model_rebuild()
