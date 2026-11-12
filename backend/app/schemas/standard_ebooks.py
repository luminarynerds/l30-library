# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class StandardEbookAuthorResponse(BaseModel):
    name: str
    url: str | None = None


class StandardEbookSummary(BaseModel):
    id: int
    se_identifier: str
    title: str
    primary_author: str | None = None
    cover_url: str | None = None
    language: str = "en"

    class Config:
        from_attributes = True


class StandardEbookDetail(BaseModel):
    id: int
    se_identifier: str
    title: str
    authors: list[StandardEbookAuthorResponse] | None = None
    description: str | None = None
    long_description: str | None = None
    subjects: list[str] | None = None
    language: str = "en"
    published_at: datetime | None = None
    word_count: int | None = None
    epub_url: str | None = None
    azw3_url: str | None = None
    kepub_url: str | None = None
    cover_url: str | None = None
    thumbnail_url: str | None = None
    source_url: str | None = None
    catalog_item_id: int | None = None
    last_synced_at: datetime
    created_at: datetime | None = None
    is_favorited: bool = False
    download_history: list["StandardEbookDownloadResponse"] | None = None

    class Config:
        from_attributes = True


class StandardEbookSearchResponse(BaseModel):
    count: int
    books: list[StandardEbookSummary]


class StandardEbookDownloadCreate(StrictInputSchema):
    book_id: int
    format: str = "epub"


class StandardEbookDownloadResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    format: str
    downloaded_at: datetime
    book_title: str | None = None

    class Config:
        from_attributes = True


class StandardEbookFavoriteCreate(StrictInputSchema):
    book_id: int
    notes: str | None = None


class StandardEbookFavoriteResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    notes: str | None = None
    created_at: datetime | None = None
    book: StandardEbookSummary | None = None

    class Config:
        from_attributes = True


class StandardEbookSyncTrigger(BaseModel):
    full_catalog: bool = Field(False, description="Attempt full OPDS catalog (requires Patron access)")


class StandardEbookSyncStatusResponse(BaseModel):
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


class StandardEbookStatsResponse(BaseModel):
    total_books: int
    total_downloads: int
    total_favorites: int


# Forward reference resolution
StandardEbookDetail.model_rebuild()
