# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from rapidfuzz import fuzz
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.release_tracker import ReleaseStatus, TrackerAuthor, TrackerBook
from ..schemas.release_tracker import ExternalBookResult, IngestionStats
from .google_books_fetcher import GoogleBooksFetcher

logger = get_logger(__name__)


class ReleaseIngestionService:

    # Deduplication thresholds
    TITLE_SIMILARITY_THRESHOLD = 90  # Minimum % match
    DATE_WINDOW_DAYS = 60  # Days within which titles are considered duplicates

    def __init__(self, db: AsyncSession, api_key: str | None = None):
        self.db = db
        self.fetcher = GoogleBooksFetcher(api_key=api_key)

    async def process_all_authors(self, force: bool = False) -> IngestionStats:
        stats = IngestionStats(
            authors_scanned=0,
            books_found=0,
            books_added=0,
            books_updated=0,
            duplicates_skipped=0,
            errors=0,
        )

        # Get all active authors
        result = await self.db.execute(
            select(TrackerAuthor)
            .where(TrackerAuthor.is_active == True)
            .options(selectinload(TrackerAuthor.books))
        )
        authors = result.scalars().all()

        for author in authors:
            try:
                # Skip if recently scanned (unless forced)
                if not force and author.last_scanned_at:
                    next_scan = author.last_scanned_at + timedelta(
                        days=author.scan_frequency_days
                    )
                    if datetime.now(author.last_scanned_at.tzinfo or None) < next_scan:
                        continue

                author_stats = await self.process_author(author.id)

                stats.authors_scanned += 1
                stats.books_found += author_stats.books_found
                stats.books_added += author_stats.books_added
                stats.books_updated += author_stats.books_updated
                stats.duplicates_skipped += author_stats.duplicates_skipped

            except Exception as e:  # noqa: BLE001 -- per-iteration boundary: one author failure must not crash full release scan
                logger.error(f"Error processing author {author.name}: {e}")
                stats.errors += 1

        await self.db.commit()
        return stats

    async def process_author(self, author_id: UUID) -> IngestionStats:
        stats = IngestionStats(
            authors_scanned=1,
            books_found=0,
            books_added=0,
            books_updated=0,
            duplicates_skipped=0,
            errors=0,
        )

        # Get author with books
        result = await self.db.execute(
            select(TrackerAuthor)
            .where(TrackerAuthor.id == author_id)
            .options(selectinload(TrackerAuthor.books))
        )
        author = result.scalar_one_or_none()

        if not author:
            raise ValueError(f"Author {author_id} not found")

        # Fetch books from Google Books
        external_books = await self.fetcher.fetch_author_books(author.name)
        stats.books_found = len(external_books)

        # Get existing books for this author
        existing_books = list(author.books) if author.books else []

        for ext_book in external_books:
            try:
                # Check for duplicates
                duplicate = self._find_duplicate(ext_book, existing_books)

                if duplicate:
                    # Update if we have better data
                    updated = self._update_if_better(duplicate, ext_book)
                    if updated:
                        stats.books_updated += 1
                    else:
                        stats.duplicates_skipped += 1
                else:
                    # Add new book
                    new_book = self._create_book_from_external(author_id, ext_book)
                    self.db.add(new_book)
                    existing_books.append(
                        new_book
                    )  # Add to list for future dedup checks
                    stats.books_added += 1

            except Exception as e:  # noqa: BLE001 -- per-iteration boundary: one book failure must not crash author book sweep
                logger.error(f"Error processing book '{ext_book.title}': {e}")
                stats.errors += 1

        # Update author's last scanned time
        author.last_scanned_at = datetime.now(timezone.utc)

        return stats

    def _find_duplicate(
        self,
        new_book: ExternalBookResult,
        existing_books: list[TrackerBook],
    ) -> TrackerBook | None:
        new_title = new_book.title.lower().strip()
        new_date = new_book.release_date

        for existing in existing_books:
            # First check: exact ISBN match
            if new_book.isbn_13 and existing.isbn_13:
                if new_book.isbn_13 == existing.isbn_13:
                    return existing

            # Second check: exact Google Books ID match
            if new_book.source_id and existing.google_books_id:
                if new_book.source_id == existing.google_books_id:
                    return existing

            # Third check: fuzzy title + date window
            existing_title = existing.normalized_title or existing.title.lower().strip()

            # Calculate title similarity
            similarity = fuzz.ratio(new_title, existing_title)

            if similarity >= self.TITLE_SIMILARITY_THRESHOLD:
                # Check date window
                if self._dates_within_window(new_date, existing.release_date):
                    return existing

        return None

    def _dates_within_window(self, date1: date | None, date2: date | None) -> bool:
        if not date1 or not date2:
            return True  # Be conservative if dates unknown

        delta = abs((date1 - date2).days)
        return delta <= self.DATE_WINDOW_DAYS

    def _update_if_better(
        self,
        existing: TrackerBook,
        new_data: ExternalBookResult,
    ) -> bool:
        updated = False

        # Update if we now have an exact date
        if new_data.is_date_exact and not existing.is_date_exact:
            existing.release_date = new_data.release_date
            existing.is_date_exact = True
            updated = True

        # Update if we now have ISBN
        if new_data.isbn_13 and not existing.isbn_13:
            existing.isbn_13 = new_data.isbn_13
            updated = True

        if new_data.isbn_10 and not existing.isbn_10:
            existing.isbn_10 = new_data.isbn_10
            updated = True

        # Update if we now have cover
        if new_data.cover_url and not existing.cover_url:
            existing.cover_url = new_data.cover_url
            updated = True

        # Update if we now have price
        if new_data.list_price and not existing.list_price:
            existing.list_price = new_data.list_price
            updated = True

        # Update if we now have description
        if new_data.description and not existing.description:
            existing.description = new_data.description
            updated = True

        return updated

    def _create_book_from_external(
        self,
        author_id: UUID,
        ext_book: ExternalBookResult,
    ) -> TrackerBook:
        # Determine status based on release date
        status = ReleaseStatus.UPCOMING
        if ext_book.release_date:
            if ext_book.release_date <= date.today():
                status = ReleaseStatus.RELEASED

        book = TrackerBook(
            author_id=author_id,
            title=ext_book.title,
            normalized_title=ext_book.title.lower().strip(),
            subtitle=ext_book.subtitle,
            description=ext_book.description,
            release_date=ext_book.release_date,
            is_date_exact=ext_book.is_date_exact,
            status=status,
            isbn_13=ext_book.isbn_13,
            isbn_10=ext_book.isbn_10,
            google_books_id=(
                ext_book.source_id if ext_book.source == "google_books" else None
            ),
            age_rating=ext_book.age_rating,
            raw_categories=ext_book.categories,
            publisher=ext_book.publisher,
            page_count=ext_book.page_count,
            list_price=ext_book.list_price,
            cover_url=ext_book.cover_url,
        )
        book.set_normalized_title()
        return book


async def process_new_releases(db: AsyncSession, force: bool = False) -> IngestionStats:
    service = ReleaseIngestionService(db)
    return await service.process_all_authors(force=force)
