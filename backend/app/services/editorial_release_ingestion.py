# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from datetime import date

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.release_tracker import ReleaseSource, ReleaseStatus, TrackerAuthor, TrackerBook
from app.schemas.release_tracker import EditorialTitle, IngestionStats
from app.services.release_ingestion import ReleaseIngestionService

logger = get_logger(__name__)


class EditorialReleaseIngestionService:
    """Ingests forthcoming titles from editorial connectors (not author-driven).

    Reuses the release-tracker dedup thresholds. For each title: resolve/create an
    inactive TrackerAuthor (so the Google-Books scanner never touches it), dedup by
    ISBN then fuzzy title+date within that author, and upsert a TrackerBook.
    """

    TITLE_SIMILARITY_THRESHOLD = ReleaseIngestionService.TITLE_SIMILARITY_THRESHOLD
    DATE_WINDOW_DAYS = ReleaseIngestionService.DATE_WINDOW_DAYS
    SENTINEL_AUTHOR_NAME = "Editorial / Various"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest(self, titles: list[EditorialTitle]) -> IngestionStats:
        stats = IngestionStats(authors_scanned=0, books_found=0, books_added=0,
                               books_updated=0, duplicates_skipped=0, errors=0)
        for item in titles:
            try:
                stats.books_found += 1
                author = await self._get_or_create_author(item.author_name)
                duplicate = await self._find_duplicate(item, author.id)
                if duplicate is not None:
                    if self._merge(duplicate, item):
                        stats.books_updated += 1
                    else:
                        stats.duplicates_skipped += 1
                else:
                    self.db.add(self._build_book(author.id, item))
                    stats.books_added += 1
            except Exception as e:  # noqa: BLE001 -- per-item boundary: one bad row must not abort the batch
                logger.error(f"Editorial ingest error for '{item.title}': {e}")
                stats.errors += 1
        await self.db.commit()
        return stats

    async def _get_or_create_author(self, name: str | None) -> TrackerAuthor:
        resolved = (name or "").strip() or self.SENTINEL_AUTHOR_NAME
        existing = (
            await self.db.execute(select(TrackerAuthor).where(TrackerAuthor.name == resolved))
        ).scalars().first()
        if existing is not None:
            return existing
        author = TrackerAuthor(name=resolved, is_active=False)
        self.db.add(author)
        await self.db.flush()
        return author

    async def _find_duplicate(self, item: EditorialTitle, author_id) -> TrackerBook | None:
        if item.isbn_13:
            by_isbn = (
                await self.db.execute(
                    select(TrackerBook).where(TrackerBook.isbn_13 == item.isbn_13))
            ).scalars().first()
            if by_isbn is not None:
                return by_isbn
        candidates = (
            await self.db.execute(
                select(TrackerBook).where(TrackerBook.author_id == author_id))
        ).scalars().all()
        new_title = item.title.lower().strip()
        for existing in candidates:
            existing_title = existing.normalized_title or existing.title.lower().strip()
            if fuzz.ratio(new_title, existing_title) >= self.TITLE_SIMILARITY_THRESHOLD:
                if self._dates_within_window(item.release_date, existing.release_date):
                    return existing
        return None

    def _dates_within_window(self, d1: date | None, d2: date | None) -> bool:
        if not d1 or not d2:
            return True
        return abs((d1 - d2).days) <= self.DATE_WINDOW_DAYS

    def _merge(self, book: TrackerBook, item: EditorialTitle) -> bool:
        changed = False
        if (
            item.source
            and book.source == ReleaseSource.AUTHOR_SCAN.value
            and item.source != ReleaseSource.AUTHOR_SCAN.value
        ):
            book.source = item.source
            changed = True
        if item.is_featured and not book.is_featured:
            book.is_featured = True
            changed = True
        if item.blurb and not book.blurb:
            book.blurb = item.blurb
            book.blurb_credit = item.blurb_credit
            changed = True
        if item.source_url and not book.source_url:
            book.source_url = item.source_url
            changed = True
        if item.release_date and not book.release_date:
            book.release_date = item.release_date
            changed = True
        if item.publisher and not book.publisher:
            book.publisher = item.publisher
            changed = True
        return changed

    def _build_book(self, author_id, item: EditorialTitle) -> TrackerBook:
        status = ReleaseStatus.RELEASED.value if (
            item.release_date and item.release_date <= date.today()
        ) else ReleaseStatus.UPCOMING.value
        book = TrackerBook(
            author_id=author_id,
            title=item.title,
            subtitle=item.subtitle,
            release_date=item.release_date,
            is_date_exact=item.is_date_exact,
            status=status,
            isbn_13=item.isbn_13,
            publisher=item.publisher,
            age_rating=item.age_rating,
            raw_categories=[item.genre] if item.genre else [],
            list_price=item.list_price,
            source=item.source,
            source_url=item.source_url,
            blurb=item.blurb,
            blurb_credit=item.blurb_credit,
            is_featured=item.is_featured,
        )
        book.set_normalized_title()
        return book
