# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.sanitization import _sanitize_html
from app.schemas._base import StrictInputSchema


class TagResponse(BaseModel):
    id: int
    name: str
    slug: str
    post_count: int | None = None

    class Config:
        from_attributes = True


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class BlogAuthorSummary(BaseModel):

    id: int
    full_name: str
    role: str | None = None

    class Config:
        from_attributes = True


class BlogPostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    slug: str | None = Field(None, max_length=500)
    body: str = Field(default="")
    tldr: str | None = None
    meta_description: str | None = None
    author_name: str = Field(default="", max_length=255)
    author_role: str | None = Field(None, max_length=255)
    series_name: str | None = Field(None, max_length=255)
    series_order: int | None = None
    tags: list[str] = Field(default_factory=list)
    featured_image: str | None = None

    @field_validator("body", "tldr", mode="before")
    @classmethod
    def _sanitize_rich_text(cls, value):
        return _sanitize_html(value)


class BlogPostCreate(StrictInputSchema, BlogPostBase):
    status: str = "draft"
    scheduled_at: datetime | None = None
    # Structured author wiring. If omitted on Create, the endpoint
    # defaults author_id to current_user.id. Legacy author_name /
    # author_role above remain accepted for back-compat.
    author_id: int | None = None
    co_author_ids: list[int] = Field(default_factory=list)


class BlogPostUpdate(StrictInputSchema):
    title: str | None = Field(None, min_length=1, max_length=500)
    slug: str | None = Field(None, max_length=500)
    body: str | None = None
    tldr: str | None = None
    meta_description: str | None = None
    author_name: str | None = Field(None, max_length=255)
    author_role: str | None = Field(None, max_length=255)
    series_name: str | None = Field(None, max_length=255)
    series_order: int | None = None
    tags: list[str] | None = None
    status: str | None = None
    scheduled_at: datetime | None = None
    featured_image: str | None = None
    # Update can clear or change author_id; explicit None means "unset".
    # co_author_ids=[] means "remove all co-authors"; co_author_ids=None
    # (field omitted from payload) leaves co-authors untouched.
    author_id: int | None = None
    co_author_ids: list[int] | None = None

    @field_validator("body", "tldr", mode="before")
    @classmethod
    def _sanitize_rich_text(cls, value):
        return _sanitize_html(value)


class BlogPostResponse(BaseModel):
    id: int
    title: str
    slug: str
    body: str
    tldr: str | None
    meta_description: str | None = None
    featured_image: str | None = None
    author_name: str
    author_role: str | None
    # Structured author + co-authors. `author_id` is the FK; `author`
    # is the resolved nested summary; `byline` is the computed display
    # string (FK first, then legacy fallback). Existing clients that
    # only read author_name/author_role keep working.
    author_id: int | None = None
    author: BlogAuthorSummary | None = None
    co_authors: list[BlogAuthorSummary] = []
    byline: str = ""
    status: str
    published_at: datetime | None
    scheduled_at: datetime | None
    series_name: str | None
    series_order: int | None
    read_time_minutes: int
    view_count: int = 0
    created_at: datetime
    updated_at: datetime | None
    tags: list[TagResponse] = []

    class Config:
        from_attributes = True


class BlogPostListItem(BaseModel):
    id: int
    title: str
    slug: str
    tldr: str | None
    meta_description: str | None = None
    featured_image: str | None = None
    author_name: str
    author_role: str | None
    status: str
    published_at: datetime | None
    scheduled_at: datetime | None
    series_name: str | None
    read_time_minutes: int
    view_count: int = 0
    created_at: datetime
    deleted_at: datetime | None = None
    tags: list[TagResponse] = []

    class Config:
        from_attributes = True


class BlogPostListResponse(BaseModel):
    items: list[BlogPostListItem]
    total: int
    page: int
    per_page: int
    draft_count: int | None = None
    published_count: int | None = None
    scheduled_count: int | None = None


class BlogPostVersionResponse(BaseModel):
    id: int
    version_number: int
    title: str
    body: str
    tldr: str | None
    created_at: datetime
    created_by: str | None

    model_config = ConfigDict(from_attributes=True)


class BlogPostVersionListItem(BaseModel):
    id: int
    version_number: int
    title: str
    created_at: datetime
    created_by: str | None

    model_config = ConfigDict(from_attributes=True)


class BlogAnalyticsResponse(BaseModel):
    total_views: int
    total_posts: int
    published_posts: int
    views_last_7_days: int
    views_last_30_days: int
    top_posts: list[dict]
    views_by_day: list[dict]


# ============================================================================
# Patron bookmark schemas
# ============================================================================


class BlogBookmarkCreateResponse(BaseModel):
    post_id: int
    created_at: datetime
    already_bookmarked: bool

    model_config = ConfigDict(from_attributes=True)


class BlogPostBookmarkedResponse(BlogPostResponse):
    bookmarked_at: datetime
