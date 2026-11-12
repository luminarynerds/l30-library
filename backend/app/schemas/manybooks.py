# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class ManyBooksBookSummary(BaseModel):
    id: int
    manybooks_id: str
    title: str
    primary_author: str | None = None
    cover_url: str | None = None
    language: str = "en"
    rating: float | None = None

    class Config:
        from_attributes = True


class ManyBooksBookDetail(BaseModel):
    id: int
    manybooks_id: str
    title: str
    authors: list[dict] | None = None
    summary: str | None = None
    categories: list[str] | None = None
    language: str = "en"
    publication_year: int | None = None
    rating: float | None = None
    rating_count: int = 0
    formats: dict[str, str] | None = None
    cover_url: str | None = None
    source_url: str | None = None
    gutenberg_id: int | None = None
    catalog_item_id: int | None = None
    last_synced_at: datetime
    created_at: datetime | None = None
    is_favorited: bool = False
    download_history: list["ManyBooksDownloadResponse"] | None = None

    class Config:
        from_attributes = True


class ManyBooksSearchResponse(BaseModel):
    count: int
    page: int
    page_size: int
    books: list[ManyBooksBookSummary]
    has_next: bool
    has_previous: bool


class ManyBooksDownloadCreate(StrictInputSchema):
    book_id: int
    format: str = "epub"


class ManyBooksDownloadResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    format: str
    downloaded_at: datetime
    book_title: str | None = None

    class Config:
        from_attributes = True


class ManyBooksFavoriteCreate(StrictInputSchema):
    book_id: int
    notes: str | None = None


class ManyBooksFavoriteResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    notes: str | None = None
    created_at: datetime | None = None
    book: ManyBooksBookSummary | None = None

    class Config:
        from_attributes = True


class ManyBooksSyncTrigger(BaseModel):
    max_pages: int | None = Field(None, description="Maximum pages to sync")


class ManyBooksSyncStatusResponse(BaseModel):
    id: int
    last_sync_at: datetime | None = None
    total_books_synced: int
    last_synced_page: int
    is_syncing: bool
    sync_started_at: datetime | None = None
    sync_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ManyBooksStatsResponse(BaseModel):
    total_books: int
    total_downloads: int
    total_favorites: int


# Forward reference resolution
ManyBooksBookDetail.model_rebuild()
