# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from ._base import StrictInputSchema


class MangaCatalogingTemplateCreate(StrictInputSchema):

    name: str
    description: Optional[str] = None
    series_title: str
    author: Optional[str] = None
    original_language: str = "Japanese"
    publisher: Optional[str] = None
    genre: str = "manga,graphic novels"
    subjects: str = "manga,graphic novels,Japanese comics"
    catalog_series_type: str = "graphic_novel_series"
    format: str = "volume"
    isbn_pattern: Optional[str] = None
    covers_color: bool = True
    page_count_average: Optional[int] = None
    default_fields: Optional[dict] = None
    auto_increment_volume: bool = True
    auto_fetch_cover: bool = True
    auto_populate_series_info: bool = True


class MangaCatalogingTemplateUpdate(StrictInputSchema):

    name: Optional[str] = None
    description: Optional[str] = None
    series_title: Optional[str] = None
    author: Optional[str] = None
    original_language: Optional[str] = None
    publisher: Optional[str] = None
    genre: Optional[str] = None
    subjects: Optional[str] = None
    catalog_series_type: Optional[str] = None
    format: Optional[str] = None
    isbn_pattern: Optional[str] = None
    covers_color: Optional[bool] = None
    page_count_average: Optional[int] = None
    default_fields: Optional[dict] = None
    auto_increment_volume: Optional[bool] = None
    auto_fetch_cover: Optional[bool] = None
    auto_populate_series_info: Optional[bool] = None


class MangaCatalogingTemplateResponse(BaseModel):

    id: int
    name: str
    description: Optional[str]
    series_title: str
    author: Optional[str]
    original_language: str
    publisher: Optional[str]
    genre: str
    subjects: str
    catalog_series_type: str
    format: str
    isbn_pattern: Optional[str]
    covers_color: bool
    page_count_average: Optional[int]
    default_fields: dict
    auto_increment_volume: bool
    auto_fetch_cover: bool
    auto_populate_series_info: bool
    is_shared: bool
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MangaVolumeRecordCreate(StrictInputSchema):

    catalog_item_id: int
    series_title: str
    volume_number: int
    template_id: Optional[int] = None
    volume_title: Optional[str] = None
    isbn: Optional[str] = None
    publication_date: Optional[datetime] = None
    publisher: Optional[str] = None
    original_language: Optional[str] = None
    page_count: Optional[int] = None
    is_color: Optional[bool] = None


class MangaVolumeRecordUpdate(StrictInputSchema):

    volume_number: Optional[int] = None
    volume_title: Optional[str] = None
    isbn: Optional[str] = None
    cover_image_url: Optional[str] = None
    cover_fetch_source: Optional[str] = None
    publication_date: Optional[datetime] = None
    publisher: Optional[str] = None
    original_language: Optional[str] = None
    page_count: Optional[int] = None
    is_color: Optional[bool] = None


class MangaVolumeRecordResponse(BaseModel):

    id: int
    catalog_item_id: int
    series_title: str
    volume_number: int
    template_id: Optional[int]
    volume_title: Optional[str]
    isbn: Optional[str]
    cover_image_url: Optional[str]
    cover_fetch_source: Optional[str]
    publication_date: Optional[datetime]
    publisher: Optional[str]
    original_language: Optional[str]
    page_count: Optional[int]
    is_color: Optional[bool]
    previous_volume_id: Optional[int]
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class QuickAddMangaVolumeRequest(StrictInputSchema):

    series_title: str
    volume_number: int
    title: str
    author: Optional[str] = None
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    original_language: Optional[str] = None
    publication_date: Optional[str] = None
    template_id: Optional[int] = None
    copy_from_volume_id: Optional[int] = None  # Copy and increment from existing volume
    auto_fetch_cover: bool = True


class CopyAndIncrementVolumeRequest(StrictInputSchema):

    source_volume_id: int
    new_volume_number: int
    isbn: Optional[str] = None  # Optional new ISBN


class BatchCreateMangaVolumesRequest(StrictInputSchema):

    series_title: str
    template_id: Optional[int] = None
    start_volume: int = 1
    volumes: list[dict]  # List of volume data with title, isbn, etc.


class ISBNLookupResponse(BaseModel):

    isbn: str
    found: bool
    source: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    publish_date: Optional[str] = None
    page_count: Optional[int] = None
    cover_url: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    subjects: Optional[str] = None


class SeriesInfoResponse(BaseModel):

    series_title: str
    total_volumes: int
    next_volume_number: int
    auto_populate_info: dict


class MangaCatalogingStats(BaseModel):

    total_templates: int
    total_volumes: int
    total_series: int
    avg_volumes_per_series: float
    templates_with_auto_cover: int
