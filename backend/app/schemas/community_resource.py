# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class CommunityResourceLinkBase(BaseModel):
    category: str = Field(..., max_length=50)
    category_label: str = Field(..., max_length=100)
    page_contexts: list[str] = Field(default_factory=list)
    name: str = Field(..., min_length=1, max_length=255)
    url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    icon_hint: Optional[str] = Field(None, max_length=50)
    sort_order: int = 0
    is_active: bool = False
    source: str = Field("manual", max_length=20)


class CommunityResourceLinkCreate(StrictInputSchema, CommunityResourceLinkBase):
    pass


class CommunityResourceLinkUpdate(StrictInputSchema):
    category: Optional[str] = Field(None, max_length=50)
    category_label: Optional[str] = Field(None, max_length=100)
    page_contexts: Optional[list[str]] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    icon_hint: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CommunityResourceLinkResponse(CommunityResourceLinkBase):
    id: int

    class Config:
        from_attributes = True


class PublicLinkResponse(BaseModel):
    name: str
    url: str
    description: Optional[str] = None


class PublicCategoryResponse(BaseModel):
    category: str
    title: str
    icon_hint: Optional[str] = None
    links: list[PublicLinkResponse]


class PublicCommunityResourcesResponse(BaseModel):
    categories: list[PublicCategoryResponse]


class DiscoverySuggestion(BaseModel):
    name: str
    url: str
    category: str
    category_label: str
    description: Optional[str] = None


class DiscoveryResponse(BaseModel):
    suggestions: list[DiscoverySuggestion]
    zip_code: str
    city: str
    state: str
