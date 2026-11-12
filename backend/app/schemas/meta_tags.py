# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from typing import Optional
from pydantic import BaseModel, Field

_LIBRARY_NAME = os.environ.get("LIBRARY_NAME", "My Library")


class OpenGraphTags(BaseModel):

    og_title: str = Field(..., description="The title of the resource")
    og_description: str = Field(..., description="A brief description of the resource")
    og_image: str = Field(..., description="URL to the image/cover for the resource")
    og_url: str = Field(..., description="The canonical URL of the resource")
    og_type: str = Field(default="website", description="Type: website, book, profile, etc.")
    og_site_name: str = Field(default=_LIBRARY_NAME, description="Site name")


class TwitterCardTags(BaseModel):

    twitter_card: str = Field(default="summary_large_image", description="Card type: summary, summary_large_image, player")
    twitter_title: str = Field(..., description="The title for Twitter")
    twitter_description: str = Field(..., description="Description for Twitter")
    twitter_image: str = Field(..., description="Image URL for Twitter card")
    twitter_creator: Optional[str] = Field(None, description="Twitter handle of content creator")
    twitter_site: Optional[str] = Field(None, description="Twitter handle of the site")


class MetaTagsResponse(BaseModel):

    resource_type: str = Field(..., description="Type of resource: book, event, author, reading-list")
    resource_id: int = Field(..., description="ID of the resource")

    # Open Graph tags
    og_title: str
    og_description: str
    og_image: str
    og_url: str
    og_type: str = Field(default="website")
    og_site_name: str = Field(default=_LIBRARY_NAME)

    # Twitter Card tags
    twitter_card: str = Field(default="summary_large_image")
    twitter_title: str
    twitter_description: str
    twitter_image: str
    twitter_creator: Optional[str] = None
    twitter_site: Optional[str] = None

    # Additional metadata
    resource_title: str = Field(..., description="Display title of the resource")
    resource_creator: Optional[str] = Field(None, description="Creator/author name")
    resource_image_alt: Optional[str] = Field(None, description="Alt text for image")

    # Structured data (optional, for enhanced search results)
    schema_type: Optional[str] = Field(None, description="JSON-LD schema type")

    class Config:
        json_schema_extra = {
            "example": {
                "resource_type": "book",
                "resource_id": 123,
                "og_title": "The Great Gatsby",
                "og_description": "A classic novel about wealth, love, and the American Dream",
                "og_image": "https://example.com/covers/great-gatsby.jpg",
                "og_url": "https://library.example.com/books/123",
                "og_type": "book",
                "og_site_name": _LIBRARY_NAME,
                "twitter_card": "summary_large_image",
                "twitter_title": "The Great Gatsby",
                "twitter_description": "A classic novel about wealth, love, and the American Dream",
                "twitter_image": "https://example.com/covers/great-gatsby.jpg",
                "twitter_creator": "@fscottfitzgerald",
                "twitter_site": "@l30",
                "resource_title": "The Great Gatsby",
                "resource_creator": "F. Scott Fitzgerald",
                "resource_image_alt": "Book cover for The Great Gatsby",
                "schema_type": "Book"
            }
        }


class MetaTagsNotFoundResponse(BaseModel):

    resource_type: str
    resource_id: int
    og_title: str = Field(default=_LIBRARY_NAME)
    og_description: str = Field(default=f"Discover books, events, and more at {_LIBRARY_NAME}")
    og_image: str = Field(default="https://library.example.com/default-og-image.jpg")
    og_url: str
    og_type: str = Field(default="website")
    og_site_name: str = Field(default=_LIBRARY_NAME)
    twitter_card: str = Field(default="summary_large_image")
    twitter_title: str = Field(default=_LIBRARY_NAME)
    twitter_description: str = Field(default=f"Discover books, events, and more at {_LIBRARY_NAME}")
    twitter_image: str = Field(default="https://library.example.com/default-og-image.jpg")
    twitter_site: Optional[str] = None
    resource_found: bool = Field(default=False, description="Whether the resource was found")
