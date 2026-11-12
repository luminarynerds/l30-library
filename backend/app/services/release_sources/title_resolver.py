# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from rapidfuzz import fuzz

from app.core.logging import get_logger
from app.models.release_tracker import ReleaseSource
from app.schemas.release_tracker import EditorialTitle
from app.services.google_books_fetcher import GoogleBooksFetcher

logger = get_logger(__name__)


async def resolve(
    title: str,
    author: str,
    source: str = ReleaseSource.EDITORIAL_RSS.value,
    source_url: str | None = None,
    blurb_credit: str | None = None,
) -> EditorialTitle:
    """Resolve {title, author} to an EditorialTitle for `source` (default editorial_rss,
    is_featured=False). Best Google Books match supplies isbn_13/release_date/publisher;
    no match -> title-only."""
    query = f"{title} {author}".strip()
    try:
        results = await GoogleBooksFetcher().search_books(query, max_results=5)
    except Exception as e:  # noqa: BLE001 -- resolution must never crash the batch
        logger.error(f"Title resolve failed for '{query}': {e}")
        results = []
    if results:
        m = results[0]
        if fuzz.ratio(title.lower(), (m.title or "").lower()) >= 80:
            return EditorialTitle(
                source=source,
                source_url=source_url,
                blurb_credit=blurb_credit,
                title=m.title or title,
                author_name=(m.authors[0] if m.authors else author) or None,
                isbn_13=m.isbn_13,
                release_date=m.release_date,
                is_date_exact=m.is_date_exact,
                publisher=m.publisher,
                list_price=m.list_price,
                age_rating=m.age_rating,
                is_featured=False,
            )
    return EditorialTitle(
        source=source,
        source_url=source_url,
        blurb_credit=blurb_credit,
        title=title,
        author_name=author or None,
        isbn_13=None,
        release_date=None,
        is_date_exact=False,
        is_featured=False,
    )
