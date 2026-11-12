# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.catalog import CatalogItem
from ..models.event import Event
from ..models.user import User
from ..models.reading_list import ReadingList
from ..schemas.meta_tags import MetaTagsResponse, MetaTagsNotFoundResponse
from ..core.config import get_settings

logger = get_logger(__name__)
_settings = get_settings()

DEFAULT_SITE_NAME = os.environ.get("LIBRARY_NAME", "My Library")
DEFAULT_TWITTER_SITE = _settings.twitter_handle or None
DEFAULT_OG_IMAGE = "https://library.example.com/default-og-image.jpg"
DEFAULT_DESCRIPTION = f"Discover books, events, and more at {os.environ.get('LIBRARY_NAME', 'My Library')}"


async def generate_meta_tags(
    resource_type: str,
    resource_id: int,
    db: AsyncSession,
    base_url: str = "https://library.example.com",
) -> MetaTagsResponse | MetaTagsNotFoundResponse:
    try:
        if resource_type == "book":
            return await _generate_book_meta_tags(resource_id, db, base_url)
        elif resource_type == "event":
            return await _generate_event_meta_tags(resource_id, db, base_url)
        elif resource_type == "author":
            return await _generate_author_meta_tags(resource_id, db, base_url)
        elif resource_type == "reading-list":
            return await _generate_reading_list_meta_tags(resource_id, db, base_url)
        else:
            logger.warning(f"Unknown resource type: {resource_type}")
            return _get_default_meta_tags(resource_type, resource_id, base_url)
    except Exception:
        logger.error(
            f"Error generating meta tags for {resource_type}:{resource_id}",
            exc_info=True,
        )
        return _get_default_meta_tags(resource_type, resource_id, base_url)


async def _generate_book_meta_tags(
    book_id: int, db: AsyncSession, base_url: str
) -> MetaTagsResponse | MetaTagsNotFoundResponse:
    result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == book_id)
    )
    book = result.scalar_one_or_none()

    if not book:
        logger.info(f"Book not found: {book_id}")
        return _get_default_meta_tags("book", book_id, base_url)

    description = (
        book.description[:155]
        if book.description
        else f"Discover {book.title} at {DEFAULT_SITE_NAME}"
    )
    cover_image = book.cover_url or DEFAULT_OG_IMAGE

    resource_url = f"{base_url}/books/{book_id}"

    return MetaTagsResponse(
        resource_type="book",
        resource_id=book_id,
        # Open Graph tags
        og_title=book.title,
        og_description=description,
        og_image=cover_image,
        og_url=resource_url,
        og_type="book",
        og_site_name=DEFAULT_SITE_NAME,
        # Twitter tags
        twitter_card="summary_large_image",
        twitter_title=book.title,
        twitter_description=description,
        twitter_image=cover_image,
        twitter_creator=None,  # Could be extended to include author Twitter
        twitter_site=DEFAULT_TWITTER_SITE,
        # Additional metadata
        resource_title=book.title,
        resource_creator=book.author,
        resource_image_alt=f"Cover of {book.title}",
        schema_type="Book",
    )


async def _generate_event_meta_tags(
    event_id: int, db: AsyncSession, base_url: str
) -> MetaTagsResponse | MetaTagsNotFoundResponse:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        logger.info(f"Event not found: {event_id}")
        return _get_default_meta_tags("event", event_id, base_url)

    description = (
        event.description[:155]
        if event.description
        else f"Join us for {event.title} at {DEFAULT_SITE_NAME}"
    )
    event_image = event.image_url or DEFAULT_OG_IMAGE

    # Build event details for description
    if event.is_virtual:
        description = f"{description} Attend online."
    elif event.location:
        description = f"{description} Location: {event.location}."

    resource_url = f"{base_url}/events/{event_id}"

    return MetaTagsResponse(
        resource_type="event",
        resource_id=event_id,
        # Open Graph tags
        og_title=event.title,
        og_description=description,
        og_image=event_image,
        og_url=resource_url,
        og_type="website",
        og_site_name=DEFAULT_SITE_NAME,
        # Twitter tags
        twitter_card="summary_large_image",
        twitter_title=event.title,
        twitter_description=description,
        twitter_image=event_image,
        twitter_creator=None,
        twitter_site=DEFAULT_TWITTER_SITE,
        # Additional metadata
        resource_title=event.title,
        resource_creator=None,  # Could be event organizer
        resource_image_alt=f"Image for {event.title} event",
        schema_type="Event",
    )


async def _generate_author_meta_tags(
    author_id: int, db: AsyncSession, base_url: str
) -> MetaTagsResponse | MetaTagsNotFoundResponse:
    result = await db.execute(select(User).where(User.id == author_id))
    author = result.scalar_one_or_none()

    if not author:
        logger.info(f"Author not found: {author_id}")
        return _get_default_meta_tags("author", author_id, base_url)

    author_name = f"{author.first_name} {author.last_name}"
    description = f"View books and activities by this author at {DEFAULT_SITE_NAME}"

    # Use a default profile image or gravatar
    author_image = DEFAULT_OG_IMAGE

    resource_url = f"{base_url}/authors/{author_id}"

    return MetaTagsResponse(
        resource_type="author",
        resource_id=author_id,
        # Open Graph tags
        og_title=f"{author_name} | {DEFAULT_SITE_NAME}",
        og_description=description,
        og_image=author_image,
        og_url=resource_url,
        og_type="profile",
        og_site_name=DEFAULT_SITE_NAME,
        # Twitter tags
        twitter_card="summary",  # Smaller card for profiles
        twitter_title=f"{author_name} | {DEFAULT_SITE_NAME}",
        twitter_description=description,
        twitter_image=author_image,
        twitter_creator=None,
        twitter_site=DEFAULT_TWITTER_SITE,
        # Additional metadata
        resource_title=author_name,
        resource_creator=author_name,
        resource_image_alt=f"Profile photo of {author_name}",
        schema_type="Person",
    )


async def _generate_reading_list_meta_tags(
    list_id: int, db: AsyncSession, base_url: str
) -> MetaTagsResponse | MetaTagsNotFoundResponse:
    result = await db.execute(
        select(ReadingList).where(ReadingList.id == list_id)
    )
    reading_list = result.scalar_one_or_none()

    if not reading_list or not reading_list.is_public:
        logger.info(f"Reading list not found or not public: {list_id}")
        return _get_default_meta_tags("reading-list", list_id, base_url)

    # Get creator name from relationship
    creator_name = (
        f"{reading_list.user.first_name} {reading_list.user.last_name}"
        if reading_list.user
        else "A Library Member"
    )

    # Count items in list
    item_count = len(reading_list.items) if reading_list.items else 0

    description = reading_list.description or f"A curated reading list with {item_count} books"

    resource_url = f"{base_url}/reading-lists/{list_id}"

    return MetaTagsResponse(
        resource_type="reading-list",
        resource_id=list_id,
        # Open Graph tags
        og_title=reading_list.name,
        og_description=description[:155],
        og_image=DEFAULT_OG_IMAGE,
        og_url=resource_url,
        og_type="website",
        og_site_name=DEFAULT_SITE_NAME,
        # Twitter tags
        twitter_card="summary",
        twitter_title=reading_list.name,
        twitter_description=description[:155],
        twitter_image=DEFAULT_OG_IMAGE,
        twitter_creator=None,
        twitter_site=DEFAULT_TWITTER_SITE,
        # Additional metadata
        resource_title=reading_list.name,
        resource_creator=creator_name,
        resource_image_alt=f"Reading list: {reading_list.name}",
        schema_type="Collection",
    )


def _get_default_meta_tags(
    resource_type: str, resource_id: int, base_url: str
) -> MetaTagsNotFoundResponse:
    resource_url = f"{base_url}/{resource_type}/{resource_id}"

    return MetaTagsNotFoundResponse(
        resource_type=resource_type,
        resource_id=resource_id,
        og_title=DEFAULT_SITE_NAME,
        og_description=DEFAULT_DESCRIPTION,
        og_image=DEFAULT_OG_IMAGE,
        og_url=resource_url,
        og_type="website",
        og_site_name=DEFAULT_SITE_NAME,
        twitter_card="summary_large_image",
        twitter_title=DEFAULT_SITE_NAME,
        twitter_description=DEFAULT_DESCRIPTION,
        twitter_image=DEFAULT_OG_IMAGE,
        twitter_site=DEFAULT_TWITTER_SITE,
        resource_found=False,
    )
