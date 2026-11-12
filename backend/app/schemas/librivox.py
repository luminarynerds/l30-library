# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class LibriVoxAuthorResponse(BaseModel):
    first_name: str
    last_name: str
    full_name: str | None = None
    dob: str | None = None
    dod: str | None = None


class LibriVoxAudiobookSummary(BaseModel):
    id: int
    librivox_id: int
    title: str
    primary_author: str | None = None
    language: str | None = None
    total_time: str | None = None
    num_sections: int = 0

    class Config:
        from_attributes = True


class LibriVoxSectionResponse(BaseModel):
    section_number: int
    title: str
    listen_url: str | None = None
    reader: str | None = None
    playtime: str | None = None


class LibriVoxAudiobookDetail(BaseModel):
    id: int
    librivox_id: int
    title: str
    authors: list[LibriVoxAuthorResponse] | None = None
    description: str | None = None
    genres: list[str] | None = None
    language: str | None = None
    book_type: str = "solo"
    total_time: str | None = None
    num_sections: int = 0
    copyright_year: int | None = None
    url_librivox: str | None = None
    url_project: str | None = None
    url_rss: str | None = None
    url_zip: str | None = None
    gutenberg_id: int | None = None
    catalog_item_id: int | None = None
    last_synced_at: datetime
    created_at: datetime | None = None
    is_favorited: bool = False
    listen_history: list["LibriVoxListenResponse"] | None = None

    class Config:
        from_attributes = True


class LibriVoxSearchQuery(BaseModel):
    query: str | None = Field(None, description="General search query")
    title: str | None = Field(None, description="Filter by title")
    author: str | None = Field(None, description="Filter by author")
    genre: str | None = Field(None, description="Filter by genre")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Results per page")


class LibriVoxSearchResponse(BaseModel):
    count: int
    page: int
    page_size: int
    books: list[LibriVoxAudiobookSummary]
    has_next: bool
    has_previous: bool


class LibriVoxListenCreate(StrictInputSchema):
    audiobook_id: int
    section_number: int | None = None


class LibriVoxListenResponse(BaseModel):
    id: int
    user_id: int
    audiobook_id: int
    section_number: int | None = None
    listened_at: datetime
    audiobook_title: str | None = None

    class Config:
        from_attributes = True


class LibriVoxFavoriteCreate(StrictInputSchema):
    audiobook_id: int
    notes: str | None = None


class LibriVoxFavoriteResponse(BaseModel):
    id: int
    user_id: int
    audiobook_id: int
    notes: str | None = None
    created_at: datetime | None = None
    audiobook: LibriVoxAudiobookSummary | None = None

    class Config:
        from_attributes = True


class LibriVoxSyncTrigger(BaseModel):
    max_batches: int | None = Field(None, description="Maximum batches to sync")


class LibriVoxSyncStatusResponse(BaseModel):
    id: int
    last_sync_at: datetime | None = None
    total_audiobooks_synced: int
    last_synced_offset: int
    is_syncing: bool
    sync_started_at: datetime | None = None
    sync_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class LibriVoxStatsResponse(BaseModel):
    total_audiobooks: int
    total_listens: int
    total_favorites: int
    unique_listeners: int
    popular_audiobooks: list[LibriVoxAudiobookSummary]


# Forward reference resolution
LibriVoxAudiobookDetail.model_rebuild()
