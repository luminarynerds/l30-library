# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema

from ..models.publisher_data import (
    PublisherType,
    PublisherRegion,
    OutOfPrintStatus,
    ContentRatingSystem,
)


# ============================================================================
# Publisher Schemas
# ============================================================================


class PublisherBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    display_name: Optional[str] = None
    publisher_type: PublisherType = PublisherType.publisher
    description: Optional[str] = None
    history: Optional[str] = None


class PublisherCreate(StrictInputSchema, PublisherBase):
    name_sort: Optional[str] = None
    parent_publisher_id: Optional[int] = None
    headquarters_location: Optional[str] = None
    primary_region: Optional[PublisherRegion] = None
    regions_served: Optional[List[str]] = None  # JSON array of regions
    website_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    default_rating_system: Optional[ContentRatingSystem] = None
    content_ratings_info: Optional[str] = None
    viaf_id: Optional[str] = None
    wikidata_id: Optional[str] = None
    isni: Optional[str] = None


class PublisherUpdate(StrictInputSchema):
    display_name: Optional[str] = None
    description: Optional[str] = None
    history: Optional[str] = None
    headquarters_location: Optional[str] = None
    primary_region: Optional[PublisherRegion] = None
    regions_served: Optional[List[str]] = None
    website_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    default_rating_system: Optional[ContentRatingSystem] = None
    content_ratings_info: Optional[str] = None
    is_active: Optional[bool] = None


class PublisherResponse(PublisherBase):
    id: int
    name_sort: Optional[str]
    parent_publisher_id: Optional[int]
    headquarters_location: Optional[str]
    primary_region: Optional[PublisherRegion]
    website_url: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    default_rating_system: Optional[ContentRatingSystem]
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class PublisherWithImprintsResponse(PublisherResponse):
    imprints: List[PublisherResponse] = []


# ============================================================================
# Manga Magazine Schemas
# ============================================================================


class MangaMagazineCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=500)
    english_name: Optional[str] = None
    publisher_id: int
    publication_frequency: Optional[str] = None
    first_published: Optional[int] = None
    last_published: Optional[int] = None
    is_ongoing: bool = True
    description: Optional[str] = None
    target_demographic: Optional[str] = None
    issn: Optional[str] = None
    wikidata_id: Optional[str] = None


class MangaMagazineResponse(BaseModel):
    id: int
    name: str
    english_name: Optional[str]
    original_language: str
    publisher_id: int
    publication_frequency: Optional[str]
    first_published: Optional[int]
    last_published: Optional[int]
    is_ongoing: bool
    description: Optional[str]
    target_demographic: Optional[str]
    issn: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Manga Serialization Schemas
# ============================================================================


class MangaSerializationCreate(StrictInputSchema):
    bibframe_work_id: int
    magazine_id: int
    start_date: Optional[str] = None  # e.g., "2019" or "2019-01"
    end_date: Optional[str] = None
    is_ongoing: bool = False
    start_chapter: Optional[str] = None
    end_chapter: Optional[str] = None
    notes: Optional[str] = None


class MangaSerializationResponse(BaseModel):
    id: int
    bibframe_work_id: int
    magazine_id: int
    start_date: Optional[str]
    end_date: Optional[str]
    is_ongoing: bool
    start_chapter: Optional[str]
    end_chapter: Optional[str]
    notes: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Publisher Series Schemas
# ============================================================================


class PublisherSeriesCreate(StrictInputSchema):
    publisher_id: int
    series_title: str = Field(..., min_length=1, max_length=500)
    series_description: Optional[str] = None
    publisher_series_number: Optional[str] = None
    is_featured: bool = False
    total_published_books: Optional[int] = None


class PublisherSeriesResponse(BaseModel):
    id: int
    publisher_id: int
    series_title: str
    series_description: Optional[str]
    publisher_series_number: Optional[str]
    is_featured: bool
    total_published_books: Optional[int]
    books_in_library: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Manga Metadata Schemas
# ============================================================================


class MangaMetadataCreate(StrictInputSchema):
    bibframe_work_id: int
    original_japanese_title: Optional[str] = None
    romaji_title: Optional[str] = None
    translator_name: Optional[str] = None
    translator_notes: Optional[str] = None
    original_publication_country: str = "JP"
    is_volume_collection: bool = True
    volume_number: Optional[int] = None
    total_chapters_in_work: Optional[int] = None
    chapter_range: Optional[str] = None
    reading_direction: str = "right-to-left"
    original_publication_date: Optional[str] = None
    english_publication_date: Optional[str] = None


class MangaMetadataResponse(BaseModel):
    id: int
    bibframe_work_id: int
    original_japanese_title: Optional[str]
    romaji_title: Optional[str]
    translator_name: Optional[str]
    translator_notes: Optional[str]
    original_publication_country: str
    is_volume_collection: bool
    volume_number: Optional[int]
    total_chapters_in_work: Optional[int]
    chapter_range: Optional[str]
    reading_direction: str
    original_publication_date: Optional[str]
    english_publication_date: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Collection Development Schemas
# ============================================================================


class CollectionDevelopmentQuery(BaseModel):
    publisher_id: Optional[int] = None
    publisher_name: Optional[str] = None
    imprint_only: bool = False
    include_series: bool = True
    include_out_of_print: bool = False


class CollectionDevelopmentResponse(BaseModel):
    publisher: PublisherResponse
    series_count: int
    total_titles: int
    titles_in_library: int
    out_of_print_titles: int
    featured_series: List[PublisherSeriesResponse] = []
    recent_releases: List[dict] = []

    class Config:
        from_attributes = True
