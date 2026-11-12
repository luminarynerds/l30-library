# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from ._base import StrictInputSchema


# ============================================================================
# Comic Series Schemas
# ============================================================================


class ComicSeriesCreate(StrictInputSchema):

    title: str
    sort_title: Optional[str] = None
    description: Optional[str] = None
    publisher: str
    publisher_imprint: Optional[str] = None
    original_language: str = "English"
    comic_format: str = "single_issue"
    is_ongoing: bool = True
    first_publication_year: Optional[int] = None
    last_publication_year: Optional[int] = None
    total_issues_published: Optional[int] = None
    total_volumes: Optional[int] = None
    genres: Optional[list[str]] = None
    characters: Optional[list[str]] = None
    is_crossover_series: bool = False
    cover_image_url: Optional[str] = None
    series_logo_url: Optional[str] = None


class ComicSeriesUpdate(StrictInputSchema):

    title: Optional[str] = None
    sort_title: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    publisher_imprint: Optional[str] = None
    original_language: Optional[str] = None
    comic_format: Optional[str] = None
    is_ongoing: Optional[bool] = None
    first_publication_year: Optional[int] = None
    last_publication_year: Optional[int] = None
    total_issues_published: Optional[int] = None
    total_volumes: Optional[int] = None
    genres: Optional[list[str]] = None
    characters: Optional[list[str]] = None
    is_crossover_series: Optional[bool] = None
    cover_image_url: Optional[str] = None
    series_logo_url: Optional[str] = None


class ComicSeriesResponse(BaseModel):

    id: int
    title: str
    sort_title: Optional[str] = None
    description: Optional[str] = None
    publisher: str
    publisher_imprint: Optional[str] = None
    original_language: str = "English"
    comic_format: str = "single_issue"
    is_ongoing: Optional[bool] = True
    first_publication_year: Optional[int] = None
    last_publication_year: Optional[int] = None
    total_issues_published: Optional[int] = None
    total_volumes: Optional[int] = None
    genres: Optional[list[str]] = None
    characters: Optional[list[str]] = None
    is_crossover_series: Optional[bool] = False
    cover_image_url: Optional[str] = None
    series_logo_url: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Comic Issue Schemas
# ============================================================================


class ComicIssueCreate(StrictInputSchema):

    series_id: int
    catalog_item_id: int
    issue_number: str
    variant_designation: Optional[str] = None
    issue_title: Optional[str] = None
    is_annual: bool = False
    is_special: bool = False
    volume_number: Optional[int] = None
    collected_issues: Optional[list[str]] = None
    publication_date: Optional[datetime] = None
    cover_date: Optional[str] = None
    isbn: Optional[str] = None
    upc_code: Optional[str] = None
    story_synopsis: Optional[str] = None
    story_arcs_involved: Optional[list[str]] = None
    writers: Optional[list[str]] = None
    artists: Optional[list[str]] = None
    colorists: Optional[list[str]] = None
    letterers: Optional[list[str]] = None
    editor: Optional[str] = None
    page_count: Optional[int] = None
    is_color: Optional[bool] = None
    content_warnings: Optional[list[str]] = None
    rating: Optional[str] = None
    parental_advisory: Optional[str] = None
    has_variant_covers: bool = False
    first_appearance_characters: Optional[list[str]] = None
    guest_stars: Optional[list[str]] = None
    is_part_of_crossover: bool = False
    crossover_event: Optional[str] = None


class ComicIssueUpdate(StrictInputSchema):

    issue_number: Optional[str] = None
    variant_designation: Optional[str] = None
    issue_title: Optional[str] = None
    is_annual: Optional[bool] = None
    is_special: Optional[bool] = None
    volume_number: Optional[int] = None
    collected_issues: Optional[list[str]] = None
    publication_date: Optional[datetime] = None
    cover_date: Optional[str] = None
    isbn: Optional[str] = None
    upc_code: Optional[str] = None
    story_synopsis: Optional[str] = None
    story_arcs_involved: Optional[list[str]] = None
    writers: Optional[list[str]] = None
    artists: Optional[list[str]] = None
    colorists: Optional[list[str]] = None
    letterers: Optional[list[str]] = None
    editor: Optional[str] = None
    page_count: Optional[int] = None
    is_color: Optional[bool] = None
    content_warnings: Optional[list[str]] = None
    rating: Optional[str] = None
    parental_advisory: Optional[str] = None
    has_variant_covers: Optional[bool] = None
    first_appearance_characters: Optional[list[str]] = None
    guest_stars: Optional[list[str]] = None
    is_part_of_crossover: Optional[bool] = None
    crossover_event: Optional[str] = None


class ComicIssueResponse(BaseModel):

    id: int
    series_id: int
    catalog_item_id: int
    issue_number: str
    variant_designation: Optional[str] = None
    issue_title: Optional[str] = None
    is_annual: Optional[bool] = False
    is_special: Optional[bool] = False
    volume_number: Optional[int] = None
    collected_issues: Optional[list[str]] = None
    publication_date: Optional[datetime] = None
    cover_date: Optional[str] = None
    isbn: Optional[str] = None
    upc_code: Optional[str] = None
    story_synopsis: Optional[str] = None
    story_arcs_involved: Optional[list[str]] = None
    writers: Optional[list[str]] = None
    artists: Optional[list[str]] = None
    colorists: Optional[list[str]] = None
    letterers: Optional[list[str]] = None
    editor: Optional[str] = None
    page_count: Optional[int] = None
    is_color: Optional[bool] = None
    content_warnings: Optional[list[str]] = None
    rating: Optional[str] = None
    parental_advisory: Optional[str] = None
    has_variant_covers: Optional[bool] = False
    first_appearance_characters: Optional[list[str]] = None
    guest_stars: Optional[list[str]] = None
    is_part_of_crossover: Optional[bool] = False
    crossover_event: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Variant Cover Schemas
# ============================================================================


class VariantCoverCreate(StrictInputSchema):

    issue_id: int
    variant_type: str
    variant_name: Optional[str] = None
    cover_artist: Optional[str] = None
    print_run: Optional[str] = None
    retailer_exclusive: Optional[str] = None
    production_notes: Optional[str] = None
    cover_image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None


class VariantCoverResponse(BaseModel):

    id: int
    issue_id: int
    variant_type: str
    variant_name: Optional[str] = None
    cover_artist: Optional[str] = None
    print_run: Optional[str] = None
    retailer_exclusive: Optional[str] = None
    production_notes: Optional[str] = None
    cover_image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Creator Schemas
# ============================================================================


class ComicIssueCreatorCreate(StrictInputSchema):

    issue_id: int
    creator_name: str
    creator_role: str
    display_order: Optional[int] = None
    creator_authority_id: Optional[str] = None
    creator_authority_source: Optional[str] = None


class ComicIssueCreatorResponse(BaseModel):

    id: int
    issue_id: int
    creator_name: str
    creator_role: str
    display_order: Optional[int] = None
    creator_authority_id: Optional[str] = None
    creator_authority_source: Optional[str] = None
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Story Arc Schemas
# ============================================================================


class StoryArcCreate(StrictInputSchema):

    series_id: int
    arc_title: str
    description: Optional[str] = None
    is_crossover: bool = False
    crossover_event_name: Optional[str] = None
    related_series: Optional[list[str]] = None
    start_issue_number: Optional[str] = None
    end_issue_number: Optional[str] = None
    issue_count: Optional[int] = None
    start_publication_date: Optional[datetime] = None
    end_publication_date: Optional[datetime] = None
    sequence_number: Optional[int] = None
    is_prequel: bool = False
    is_sequel: bool = False
    sequel_to_arc_id: Optional[int] = None
    themes: Optional[list[str]] = None
    characters_involved: Optional[list[str]] = None
    plot_summary: Optional[str] = None
    recommended_reading_order: bool = False
    skip_notes: Optional[str] = None
    contains_major_spoilers_for: Optional[list[str]] = None


class StoryArcUpdate(StrictInputSchema):

    arc_title: Optional[str] = None
    description: Optional[str] = None
    is_crossover: Optional[bool] = None
    crossover_event_name: Optional[str] = None
    related_series: Optional[list[str]] = None
    start_issue_number: Optional[str] = None
    end_issue_number: Optional[str] = None
    issue_count: Optional[int] = None
    start_publication_date: Optional[datetime] = None
    end_publication_date: Optional[datetime] = None
    sequence_number: Optional[int] = None
    is_prequel: Optional[bool] = None
    is_sequel: Optional[bool] = None
    sequel_to_arc_id: Optional[int] = None
    themes: Optional[list[str]] = None
    characters_involved: Optional[list[str]] = None
    plot_summary: Optional[str] = None
    recommended_reading_order: Optional[bool] = None
    skip_notes: Optional[str] = None
    contains_major_spoilers_for: Optional[list[str]] = None


class StoryArcResponse(BaseModel):

    id: int
    series_id: int
    arc_title: str
    description: Optional[str] = None
    is_crossover: Optional[bool] = False
    crossover_event_name: Optional[str] = None
    related_series: Optional[list[str]] = None
    start_issue_number: Optional[str] = None
    end_issue_number: Optional[str] = None
    issue_count: Optional[int] = None
    start_publication_date: Optional[datetime] = None
    end_publication_date: Optional[datetime] = None
    sequence_number: Optional[int] = None
    is_prequel: Optional[bool] = False
    is_sequel: Optional[bool] = False
    sequel_to_arc_id: Optional[int] = None
    themes: Optional[list[str]] = None
    characters_involved: Optional[list[str]] = None
    plot_summary: Optional[str] = None
    recommended_reading_order: Optional[bool] = False
    skip_notes: Optional[str] = None
    contains_major_spoilers_for: Optional[list[str]] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Content Advisory Schemas
# ============================================================================


class ComicContentAdvisoryCreate(StrictInputSchema):

    issue_id: int
    warning_type: str
    severity: Optional[str] = None
    description: str
    appears_in_pages: Optional[str] = None
    recurring: bool = False


class ComicContentAdvisoryResponse(BaseModel):

    id: int
    issue_id: int
    warning_type: str
    severity: Optional[str] = None
    description: str = ""
    appears_in_pages: Optional[str] = None
    recurring: Optional[bool] = False
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Reading Order Event Schemas
# ============================================================================


class ReadingOrderEventCreate(StrictInputSchema):

    event_name: str
    description: Optional[str] = None
    event_type: Optional[str] = None
    primary_series: Optional[list[str]] = None
    crossover_series: Optional[list[str]] = None
    total_issues: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ReadingOrderEventResponse(BaseModel):

    id: int
    event_name: str
    description: Optional[str] = None
    event_type: Optional[str] = None
    primary_series: Optional[list[str]] = None
    crossover_series: Optional[list[str]] = None
    total_issues: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Composite Schemas
# ============================================================================


class ComicSeriesDetailResponse(ComicSeriesResponse):

    issue_count: Optional[int] = None
    story_arc_count: Optional[int] = None


class ComicIssueDetailResponse(ComicIssueResponse):

    variant_covers: Optional[list[VariantCoverResponse]] = None
    creators: Optional[list[ComicIssueCreatorResponse]] = None
    content_advisories: Optional[list[ComicContentAdvisoryResponse]] = None


class QuickAddComicIssueRequest(StrictInputSchema):

    series_id: int
    issue_number: str
    catalog_item_id: int
    issue_title: Optional[str] = None
    publication_date: Optional[datetime] = None
    isbn: Optional[str] = None
    page_count: Optional[int] = None
