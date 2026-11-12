# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._base import StrictInputSchema

from ..models.home import HomeShelfQueryKind


# ---------- Item card (subset of CatalogItem for shelf rendering) ----------


class HomeItemCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: Optional[str] = None
    item_type: Optional[str] = None


# ---------- Hero pick ----------


class HeroPickRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item: HomeItemCard
    annotation_md: str
    cta_label: str
    cta_href: Optional[str] = None
    active_from: datetime
    active_to: Optional[datetime] = None


class HeroPickCreate(StrictInputSchema):
    item_id: int
    annotation_md: str = Field(..., max_length=4000)
    cta_label: str = Field(..., max_length=120)
    cta_href: Optional[str] = Field(default=None, max_length=500)
    active_from: datetime
    active_to: Optional[datetime] = None


class HeroPickUpdate(StrictInputSchema):
    item_id: Optional[int] = None
    annotation_md: Optional[str] = Field(default=None, max_length=4000)
    cta_label: Optional[str] = Field(default=None, max_length=120)
    cta_href: Optional[str] = Field(default=None, max_length=500)
    active_from: Optional[datetime] = None
    active_to: Optional[datetime] = None


# ---------- Shelves ----------


class ShelfRead(BaseModel):

    id: int
    slug: str
    heading: str
    description: str
    view_all_href: Optional[str] = None
    items: List[HomeItemCard]


class ShelfAdminRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    heading: str
    description: str
    query_kind: HomeShelfQueryKind
    query_params: dict
    sort_order: int
    is_active: bool
    max_items: int
    view_all_href: Optional[str] = None
    updated_at: datetime


class ShelfCreate(StrictInputSchema):
    slug: str = Field(..., max_length=120)
    heading: str = Field(..., max_length=200)
    description: str = Field(default="", max_length=500)
    query_kind: HomeShelfQueryKind
    query_params: dict = Field(default_factory=dict)
    sort_order: int = 0
    is_active: bool = True
    max_items: int = Field(default=6, ge=1, le=24)
    view_all_href: Optional[str] = Field(default=None, max_length=500)


class ShelfUpdate(StrictInputSchema):
    slug: Optional[str] = Field(default=None, max_length=120)
    heading: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    query_kind: Optional[HomeShelfQueryKind] = None
    query_params: Optional[dict] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    max_items: Optional[int] = Field(default=None, ge=1, le=24)
    view_all_href: Optional[str] = Field(default=None, max_length=500)


# ---------- Page config ----------


class HomePageConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    eyebrow: Optional[str] = None
    hero_visible: bool = True
    picks_link_label: Optional[str] = None
    picks_link_href: Optional[str] = None
    empty_state_message: Optional[str] = None


class HomePageConfigUpdate(StrictInputSchema):
    eyebrow: Optional[str] = Field(default=None, max_length=280)
    hero_visible: Optional[bool] = None
    picks_link_label: Optional[str] = Field(default=None, max_length=120)
    picks_link_href: Optional[str] = Field(default=None, max_length=500)
    empty_state_message: Optional[str] = None


# ---------- Composite page payload ----------


class HomePageRead(BaseModel):
    config: Optional[HomePageConfigRead] = None
    hero: Optional[HeroPickRead] = None
    shelves: List[ShelfRead] = Field(default_factory=list)
