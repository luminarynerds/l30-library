# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .favorites import CatalogItemSummary


class ReviewUpsert(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=255)
    body: Optional[str] = Field(None, max_length=10000)


class ReviewResponse(BaseModel):
    id: int
    catalog_item_id: int
    catalog_item: Optional[CatalogItemSummary] = None
    rating: Optional[int] = None
    title: Optional[str] = None
    body: Optional[str] = None
    is_staff_review: bool
    is_published: bool
    reviewer_name: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class AggregateRatingResponse(BaseModel):
    average_rating: Optional[float] = None
    rating_count: int = 0


class CatalogItemReviewsResponse(BaseModel):
    aggregate: AggregateRatingResponse
    staff_reviews: list[ReviewResponse] = []
    user_rating: Optional[int] = None
