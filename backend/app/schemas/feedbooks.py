# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class FeedbooksAuthorResponse(BaseModel):
    name: str
    uri: str | None = None


class FeedbooksBookSummary(BaseModel):
    id: int
    feedbooks_id: str
    title: str
    primary_author: str | None = None
    cover_url: str | None = None
    language: str = "en"

    class Config:
        from_attributes = True


class FeedbooksBookDetail(BaseModel):
    id: int
    feedbooks_id: str
    title: str
    authors: list[FeedbooksAuthorResponse] | None = None
    summary: str | None = None
    content: str | None = None
    categories: list[str] | None = None
    language: str = "en"
    published_at: datetime | None = None
    publisher: str | None = None
    rights: str | None = None
    epub_url: str | None = None
    mobi_url: str | None = None
    pdf_url: str | None = None
    cover_url: str | None = None
    thumbnail_url: str | None = None
    source_url: str | None = None
    catalog_item_id: int | None = None
    last_synced_at: datetime
    created_at: datetime | None = None
    is_favorited: bool = False
    download_history: list["FeedbooksDownloadResponse"] | None = None

    class Config:
        from_attributes = True


class FeedbooksSearchResponse(BaseModel):
    count: int
    page: int
    page_size: int
    books: list[FeedbooksBookSummary]
    has_next: bool
    has_previous: bool


class FeedbooksDownloadCreate(StrictInputSchema):
    book_id: int
    format: str = "epub"


class FeedbooksDownloadResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    format: str
    downloaded_at: datetime
    book_title: str | None = None

    class Config:
        from_attributes = True


class FeedbooksFavoriteCreate(StrictInputSchema):
    book_id: int
    notes: str | None = None


class FeedbooksFavoriteResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    notes: str | None = None
    created_at: datetime | None = None
    book: FeedbooksBookSummary | None = None

    class Config:
        from_attributes = True


class FeedbooksSyncTrigger(BaseModel):
    max_pages: int | None = Field(None, description="Maximum pages to sync")


class FeedbooksSyncStatusResponse(BaseModel):
    id: int
    last_sync_at: datetime | None = None
    total_books_synced: int
    is_syncing: bool
    sync_started_at: datetime | None = None
    sync_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class FeedbooksStatsResponse(BaseModel):
    total_books: int
    total_downloads: int
    total_favorites: int


# Forward reference resolution
FeedbooksBookDetail.model_rebuild()
