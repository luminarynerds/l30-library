# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


# Catalog item summary for responses
class CatalogItemSummary(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    item_type: str
    cover_url: Optional[str] = None
    page_count: Optional[int] = None

    class Config:
        from_attributes = True


# Favorites
class FavoriteCreate(StrictInputSchema):
    catalog_item_id: int


class FavoriteResponse(BaseModel):
    id: int
    catalog_item_id: int
    catalog_item: CatalogItemSummary
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# Reading Lists
class ReadingListCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    is_public: bool = False  # Privacy setting - defaults to private


class ReadingListUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_public: Optional[bool] = None  # Optional privacy setting update


class ListItemCreate(StrictInputSchema):
    catalog_item_id: int


class ListItemResponse(BaseModel):
    id: int
    catalog_item_id: int
    catalog_item: CatalogItemSummary
    added_at: datetime

    class Config:
        from_attributes = True


class ReadingListResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_public: bool = False  # Privacy setting
    created_at: datetime | None = None
    item_count: int = 0

    class Config:
        from_attributes = True


class ReadingListWithItems(ReadingListResponse):
    items: List[ListItemResponse] = []
