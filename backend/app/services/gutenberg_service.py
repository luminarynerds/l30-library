# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..clients.gutenberg_client import (
    GutenbergClient,
    GutenbergClientError,
    GutenbergBookData,
)
from ..models.gutenberg import (
    GutenbergBook,
    GutenbergDownload,
    GutenbergFavorite,
    GutenbergFormat,
    GutenbergSyncStatus,
)
from ..models.user import User
from ..schemas.gutenberg import (
    GutenbergAuthorResponse,
    GutenbergBookDetail,
    GutenbergBookSummary,
    GutenbergDownloadResponse,
    GutenbergFavoriteResponse,
    GutenbergPatronDashboard,
    GutenbergSearchResponse,
    GutenbergStatsResponse,
    GutenbergSyncStatusResponse,
)
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class GutenbergServiceError(Exception):
    pass


class GutenbergService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self._client: GutenbergClient | None = None

    async def _get_client(self) -> GutenbergClient:
        if self._client is None:
            self._client = GutenbergClient()
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    # =========================================================================
    # Search Methods
    # =========================================================================

    async def search_api(
        self,
        query: str | None = None,
        author: str | None = None,
        title: str | None = None,
        topic: str | None = None,
        languages: list[str] | None = None,
        page: int = 1,
    ) -> GutenbergSearchResponse:
        client = await self._get_client()

        try:
            result = await client.search(
                query=query,
                author=author,
                title=title,
                topic=topic,
                languages=languages,
                page=page,
            )

            books = []
            for book_data in result.books:
                # Try to get local book for additional info
                local_book = await self._get_local_book_by_gutenberg_id(book_data.id)

                books.append(GutenbergBookSummary(
                    id=local_book.id if local_book else 0,
                    gutenberg_id=book_data.id,
                    title=book_data.title,
                    primary_author=book_data.primary_author,
                    cover_url=book_data.cover_url,
                    download_count=book_data.download_count,
                    languages=",".join(book_data.languages) if book_data.languages else None,
                ))

            page_size = 32  # Gutendex default
            total_pages = (result.count + page_size - 1) // page_size if result.count > 0 else 0

            return GutenbergSearchResponse(
                count=result.count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                books=books,
                has_next=result.next_page is not None,
                has_previous=result.previous_page is not None,
            )

        except GutenbergClientError as e:
            logger.error(f"Gutenberg API search failed: {e}")
            raise GutenbergServiceError(f"Search failed: {e.message}") from e

    async def search_local(
        self,
        query: str | None = None,
        author: str | None = None,
        languages: list[str] | None = None,
        page: int = 1,
        page_size: int = 32,
    ) -> GutenbergSearchResponse:
        stmt = select(GutenbergBook)

        if query:
            # Search in title and authors
            safe_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            search_filter = GutenbergBook.title.ilike(f"%{safe_query}%")
            stmt = stmt.where(search_filter)

        if author:
            # Search in authors JSON field
            safe_author = author.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(GutenbergBook.authors.ilike(f"%{safe_author}%"))

        if languages:
            # Filter by language
            lang_filter = None
            for lang in languages:
                safe_lang = lang.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                if lang_filter is None:
                    lang_filter = GutenbergBook.languages.ilike(f"%{safe_lang}%")
                else:
                    lang_filter = lang_filter | GutenbergBook.languages.ilike(f"%{safe_lang}%")
            if lang_filter is not None:
                stmt = stmt.where(lang_filter)

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.order_by(GutenbergBook.download_count.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        books_db = result.scalars().all()

        books = []
        for book in books_db:
            authors = self._safe_json_loads(book.authors) or []
            primary_author = authors[0].get("name") if authors else None

            books.append(GutenbergBookSummary(
                id=book.id,
                gutenberg_id=book.gutenberg_id,
                title=book.title,
                primary_author=primary_author,
                cover_url=book.cover_url,
                download_count=book.download_count,
                languages=book.languages,
            ))

        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

        return GutenbergSearchResponse(
            count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            books=books,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def _get_local_book_by_gutenberg_id(self, gutenberg_id: int) -> GutenbergBook | None:
        result = await self.db.execute(
            select(GutenbergBook).where(GutenbergBook.gutenberg_id == gutenberg_id)
        )
        return result.scalar_one_or_none()

    # =========================================================================
    # Book Detail Methods
    # =========================================================================

    async def get_book(self, book_id: int, user: User | None = None) -> GutenbergBookDetail | None:
        result = await self.db.execute(
            select(GutenbergBook).where(GutenbergBook.id == book_id)
        )
        book = result.scalar_one_or_none()

        if not book:
            return None

        return await self._book_to_detail(book, user)

    async def get_book_by_gutenberg_id(
        self,
        gutenberg_id: int,
        user: User | None = None,
        fetch_if_missing: bool = True,
    ) -> GutenbergBookDetail | None:
        book = await self._get_local_book_by_gutenberg_id(gutenberg_id)

        if not book and fetch_if_missing:
            # Fetch from API and cache
            client = await self._get_client()
            try:
                book_data = await client.get_book(gutenberg_id)
                if book_data:
                    book = await self._upsert_book(book_data)
                    await self.db.commit()
            except GutenbergClientError as e:
                logger.error(f"Failed to fetch book {gutenberg_id}: {e}")

        if not book:
            return None

        return await self._book_to_detail(book, user)

    @staticmethod
    def _safe_json_loads(value):
        if not value:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None

    async def _book_to_detail(self, book: GutenbergBook, user: User | None = None) -> GutenbergBookDetail:
        # Parse authors
        authors = None
        if book.authors:
            try:
                authors_data = (self._safe_json_loads(book.authors) or [])
                authors = [GutenbergAuthorResponse(**a) for a in authors_data]
            except (json.JSONDecodeError, TypeError):
                authors = None

        # Parse formats
        try:
            formats = self._safe_json_loads(book.formats) or {}
        except (json.JSONDecodeError, TypeError):
            formats = {}

        # Extract specific format URLs
        epub_url = formats.get("application/epub+zip") or formats.get("application/epub")
        kindle_url = formats.get("application/x-mobipocket-ebook")
        html_url = formats.get("text/html") or formats.get("text/html; charset=utf-8")
        text_url = (
            formats.get("text/plain")
            or formats.get("text/plain; charset=utf-8")
            or formats.get("text/plain; charset=us-ascii")
        )
        pdf_url = formats.get("application/pdf")

        # Check if favorited
        is_favorited = False
        download_history = None
        if user:
            fav_result = await self.db.execute(
                select(GutenbergFavorite).where(
                    GutenbergFavorite.user_id == user.id,
                    GutenbergFavorite.book_id == book.id,
                )
            )
            is_favorited = fav_result.scalar_one_or_none() is not None

            # Get download history
            dl_result = await self.db.execute(
                select(GutenbergDownload)
                .where(GutenbergDownload.user_id == user.id, GutenbergDownload.book_id == book.id)
                .order_by(GutenbergDownload.downloaded_at.desc())
                .limit(10)
            )
            downloads = dl_result.scalars().all()
            download_history = [
                GutenbergDownloadResponse(
                    id=dl.id,
                    user_id=dl.user_id,
                    book_id=dl.book_id,
                    format=dl.format,
                    downloaded_at=dl.downloaded_at,
                    book_title=book.title,
                )
                for dl in downloads
            ]

        return GutenbergBookDetail(
            id=book.id,
            gutenberg_id=book.gutenberg_id,
            title=book.title,
            authors=authors,
            subjects=self._safe_json_loads(book.subjects),
            bookshelves=self._safe_json_loads(book.bookshelves),
            languages=book.languages,
            copyright_status=book.copyright_status,
            media_type=book.media_type,
            download_count=book.download_count,
            formats=formats,
            cover_url=book.cover_url,
            catalog_item_id=book.catalog_item_id,
            last_synced_at=getattr(book, "last_synced_at", None),
            created_at=getattr(book, "created_at", None),
            epub_url=epub_url,
            kindle_url=kindle_url,
            html_url=html_url,
            text_url=text_url,
            pdf_url=pdf_url,
            is_favorited=is_favorited,
            download_history=download_history,
        )

    # =========================================================================
    # Popular/Featured Methods
    # =========================================================================

    async def get_popular_books(
        self,
        languages: list[str] | None = None,
        limit: int = 20,
    ) -> list[GutenbergBookSummary]:
        stmt = select(GutenbergBook).order_by(GutenbergBook.download_count.desc())

        if languages:
            lang_filter = None
            for lang in languages:
                safe_lang = lang.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                if lang_filter is None:
                    lang_filter = GutenbergBook.languages.ilike(f"%{safe_lang}%")
                else:
                    lang_filter = lang_filter | GutenbergBook.languages.ilike(f"%{safe_lang}%")
            if lang_filter is not None:
                stmt = stmt.where(lang_filter)

        stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        books_db = result.scalars().all()

        books = []
        for book in books_db:
            authors = self._safe_json_loads(book.authors) or []
            primary_author = authors[0].get("name") if authors else None

            books.append(GutenbergBookSummary(
                id=book.id,
                gutenberg_id=book.gutenberg_id,
                title=book.title,
                primary_author=primary_author,
                cover_url=book.cover_url,
                download_count=book.download_count,
                languages=book.languages,
            ))

        return books

    # =========================================================================
    # Download Tracking Methods
    # =========================================================================

    async def record_download(
        self,
        user: User,
        book_id: int,
        format: GutenbergFormat,
    ) -> GutenbergDownloadResponse:
        # Verify book exists
        result = await self.db.execute(
            select(GutenbergBook).where(GutenbergBook.id == book_id)
        )
        book = result.scalar_one_or_none()

        if not book:
            raise GutenbergServiceError("Book not found")

        download = GutenbergDownload(
            user_id=user.id,
            book_id=book_id,
            format=format,
            downloaded_at=utc_now(),
        )
        self.db.add(download)
        await self.db.flush()

        return GutenbergDownloadResponse(
            id=download.id,
            user_id=download.user_id,
            book_id=download.book_id,
            format=download.format,
            downloaded_at=download.downloaded_at,
            book_title=book.title,
        )

    async def get_user_downloads(
        self,
        user_id: int,
        limit: int = 50,
    ) -> list[GutenbergDownloadResponse]:
        result = await self.db.execute(
            select(GutenbergDownload)
            .options(selectinload(GutenbergDownload.book))
            .where(GutenbergDownload.user_id == user_id)
            .order_by(GutenbergDownload.downloaded_at.desc())
            .limit(limit)
        )
        downloads = result.scalars().all()

        return [
            GutenbergDownloadResponse(
                id=dl.id,
                user_id=dl.user_id,
                book_id=dl.book_id,
                format=dl.format,
                downloaded_at=dl.downloaded_at,
                book_title=dl.book.title if dl.book else None,
            )
            for dl in downloads
        ]

    # =========================================================================
    # Favorites Methods
    # =========================================================================

    async def add_favorite(
        self,
        user: User,
        book_id: int,
        notes: str | None = None,
    ) -> GutenbergFavoriteResponse:
        # Check if already favorited
        result = await self.db.execute(
            select(GutenbergFavorite).where(
                GutenbergFavorite.user_id == user.id,
                GutenbergFavorite.book_id == book_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            raise GutenbergServiceError("Book already in favorites")

        # Verify book exists
        book_result = await self.db.execute(
            select(GutenbergBook).where(GutenbergBook.id == book_id)
        )
        book = book_result.scalar_one_or_none()

        if not book:
            raise GutenbergServiceError("Book not found")

        favorite = GutenbergFavorite(
            user_id=user.id,
            book_id=book_id,
            notes=notes,
            created_at=utc_now(),
        )
        self.db.add(favorite)
        await self.db.flush()

        authors = self._safe_json_loads(book.authors) or []
        primary_author = authors[0].get("name") if authors else None

        return GutenbergFavoriteResponse(
            id=favorite.id,
            user_id=favorite.user_id,
            book_id=favorite.book_id,
            notes=favorite.notes,
            created_at=favorite.created_at,
            book=GutenbergBookSummary(
                id=book.id,
                gutenberg_id=book.gutenberg_id,
                title=book.title,
                primary_author=primary_author,
                cover_url=book.cover_url,
                download_count=book.download_count,
                languages=book.languages,
            ),
        )

    async def remove_favorite(self, user: User, book_id: int) -> bool:
        result = await self.db.execute(
            delete(GutenbergFavorite).where(
                GutenbergFavorite.user_id == user.id,
                GutenbergFavorite.book_id == book_id,
            )
        )
        return result.rowcount > 0

    async def get_user_favorites(
        self,
        user_id: int,
        limit: int = 50,
    ) -> list[GutenbergFavoriteResponse]:
        result = await self.db.execute(
            select(GutenbergFavorite)
            .options(selectinload(GutenbergFavorite.book))
            .where(GutenbergFavorite.user_id == user_id)
            .order_by(GutenbergFavorite.created_at.desc())
            .limit(limit)
        )
        favorites = result.scalars().all()

        responses = []
        for fav in favorites:
            book_summary = None
            if fav.book:
                authors = self._safe_json_loads(fav.book.authors) or []
                primary_author = authors[0].get("name") if authors else None

                book_summary = GutenbergBookSummary(
                    id=fav.book.id,
                    gutenberg_id=fav.book.gutenberg_id,
                    title=fav.book.title,
                    primary_author=primary_author,
                    cover_url=fav.book.cover_url,
                    download_count=fav.book.download_count,
                    languages=fav.book.languages,
                )

            responses.append(GutenbergFavoriteResponse(
                id=fav.id,
                user_id=fav.user_id,
                book_id=fav.book_id,
                notes=fav.notes,
                created_at=fav.created_at,
                book=book_summary,
            ))

        return responses

    # =========================================================================
    # Patron Dashboard
    # =========================================================================

    async def get_patron_dashboard(self, user: User) -> GutenbergPatronDashboard:
        # Get recent downloads
        recent_downloads = await self.get_user_downloads(user.id, limit=10)

        # Get favorites
        favorites = await self.get_user_favorites(user.id, limit=10)

        # Get total counts
        dl_count_result = await self.db.execute(
            select(func.count()).where(GutenbergDownload.user_id == user.id)
        )
        total_downloads = dl_count_result.scalar() or 0

        fav_count_result = await self.db.execute(
            select(func.count()).where(GutenbergFavorite.user_id == user.id)
        )
        total_favorites = fav_count_result.scalar() or 0

        # Get recommended books (popular books not yet downloaded by user)
        downloaded_book_ids = await self.db.execute(
            select(GutenbergDownload.book_id).where(GutenbergDownload.user_id == user.id)
        )
        downloaded_ids = [row[0] for row in downloaded_book_ids.all()]

        recommended_stmt = (
            select(GutenbergBook)
            .order_by(GutenbergBook.download_count.desc())
            .limit(10)
        )
        if downloaded_ids:
            recommended_stmt = recommended_stmt.where(
                GutenbergBook.id.not_in(downloaded_ids)
            )

        rec_result = await self.db.execute(recommended_stmt)
        recommended_books_db = rec_result.scalars().all()

        recommended = []
        for book in recommended_books_db:
            authors = self._safe_json_loads(book.authors) or []
            primary_author = authors[0].get("name") if authors else None

            recommended.append(GutenbergBookSummary(
                id=book.id,
                gutenberg_id=book.gutenberg_id,
                title=book.title,
                primary_author=primary_author,
                cover_url=book.cover_url,
                download_count=book.download_count,
                languages=book.languages,
            ))

        return GutenbergPatronDashboard(
            recent_downloads=recent_downloads,
            favorites=favorites,
            total_downloads=total_downloads,
            total_favorites=total_favorites,
            recommended_books=recommended,
        )

    # =========================================================================
    # Sync Methods
    # =========================================================================

    async def _upsert_book(self, book_data: GutenbergBookData) -> GutenbergBook:
        existing = await self._get_local_book_by_gutenberg_id(book_data.id)

        authors_json = json.dumps([
            {"name": a.name, "birth_year": a.birth_year, "death_year": a.death_year}
            for a in book_data.authors
        ]) if book_data.authors else None

        if existing:
            existing.title = book_data.title
            existing.authors = authors_json
            existing.subjects = json.dumps(book_data.subjects) if book_data.subjects else None
            existing.bookshelves = json.dumps(book_data.bookshelves) if book_data.bookshelves else None
            existing.languages = ",".join(book_data.languages) if book_data.languages else None
            existing.copyright_status = book_data.copyright
            existing.media_type = book_data.media_type
            existing.formats = json.dumps(book_data.formats) if book_data.formats else None
            existing.cover_url = book_data.cover_url
            existing.download_count = book_data.download_count
            existing.last_synced_at = utc_now()
            existing.updated_at = utc_now()
            return existing
        else:
            new_book = GutenbergBook(
                gutenberg_id=book_data.id,
                title=book_data.title,
                authors=authors_json,
                subjects=json.dumps(book_data.subjects) if book_data.subjects else None,
                bookshelves=json.dumps(book_data.bookshelves) if book_data.bookshelves else None,
                languages=",".join(book_data.languages) if book_data.languages else None,
                copyright_status=book_data.copyright,
                media_type=book_data.media_type,
                formats=json.dumps(book_data.formats) if book_data.formats else None,
                cover_url=book_data.cover_url,
                download_count=book_data.download_count,
                last_synced_at=utc_now(),
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            self.db.add(new_book)
            return new_book

    async def get_sync_status(self) -> GutenbergSyncStatusResponse | None:
        result = await self.db.execute(select(GutenbergSyncStatus).limit(1))
        status = result.scalar_one_or_none()

        if not status:
            return None

        return GutenbergSyncStatusResponse(
            id=status.id,
            last_full_sync_at=status.last_full_sync_at,
            last_incremental_sync_at=status.last_incremental_sync_at,
            total_books_synced=status.total_books_synced,
            last_synced_page=status.last_synced_page,
            is_syncing=status.is_syncing,
            sync_started_at=status.sync_started_at,
            sync_error=status.sync_error,
            created_at=status.created_at,
            updated_at=status.updated_at,
        )

    async def sync_catalog(
        self,
        full_sync: bool = False,
        max_pages: int | None = None,
        languages: list[str] | None = None,
    ) -> dict[str, Any]:
        # Get or create sync status
        result = await self.db.execute(select(GutenbergSyncStatus).limit(1))
        status = result.scalar_one_or_none()

        if not status:
            status = GutenbergSyncStatus(
                total_books_synced=0,
                last_synced_page=0,
                is_syncing=False,
            )
            self.db.add(status)
            await self.db.flush()

        if status.is_syncing:
            raise GutenbergServiceError("Sync already in progress")

        # Mark sync as started
        status.is_syncing = True
        status.sync_started_at = utc_now()
        status.sync_error = None
        await self.db.commit()

        client = await self._get_client()
        synced_count = 0
        page = 1 if full_sync else (status.last_synced_page or 1)

        # Default to English if no languages specified
        if languages is None:
            languages = ["en"]

        try:
            async for books_batch in client.iter_all_books(
                languages=languages,
                max_pages=max_pages,
            ):
                for book_data in books_batch:
                    await self._upsert_book(book_data)
                    synced_count += 1

                # Update progress
                status.last_synced_page = page
                status.total_books_synced = synced_count
                status.updated_at = utc_now()
                await self.db.commit()

                page += 1

                # Log progress
                if synced_count % 100 == 0:
                    logger.info(f"Gutenberg sync progress: {synced_count} books synced")

            # Mark sync as complete
            status.is_syncing = False
            if full_sync:
                status.last_full_sync_at = utc_now()
            else:
                status.last_incremental_sync_at = utc_now()
            status.updated_at = utc_now()
            await self.db.commit()

            # Auto-ingest into general catalog
            ingested = 0
            try:
                from .free_ebook_ingestion_service import FreeEbookIngestionService
                ingestion = FreeEbookIngestionService(self.db)
                ingested = await ingestion._ingest_gutenberg()
                await self.db.commit()
                logger.info(f"Auto-ingested {ingested} Gutenberg books into catalog")
            except Exception as e:  # noqa: BLE001 -- auto-ingestion non-fatal: sync success not blocked by catalog ingest failure
                logger.warning(f"Auto-ingestion failed (non-fatal): {e}")

            return {
                "success": True,
                "books_synced": synced_count,
                "pages_synced": page - 1,
                "catalog_ingested": ingested,
            }

        except Exception as e:
            logger.error(f"Gutenberg sync failed: {e}")
            status.is_syncing = False
            status.sync_error = str(e)
            status.updated_at = utc_now()
            await self.db.commit()

            raise GutenbergServiceError(f"Sync failed: {e}") from e

    # =========================================================================
    # Statistics Methods
    # =========================================================================

    async def get_statistics(self) -> GutenbergStatsResponse:
        # Total books
        book_count_result = await self.db.execute(select(func.count(GutenbergBook.id)))
        total_books = book_count_result.scalar() or 0

        # Total downloads
        dl_count_result = await self.db.execute(select(func.count(GutenbergDownload.id)))
        total_downloads = dl_count_result.scalar() or 0

        # Total favorites
        fav_count_result = await self.db.execute(select(func.count(GutenbergFavorite.id)))
        total_favorites = fav_count_result.scalar() or 0

        # Unique patrons who downloaded
        unique_patrons_result = await self.db.execute(
            select(func.count(func.distinct(GutenbergDownload.user_id)))
        )
        unique_patrons = unique_patrons_result.scalar() or 0

        # Popular books
        popular_books = await self.get_popular_books(limit=10)

        # Downloads by format
        format_result = await self.db.execute(
            select(GutenbergDownload.format, func.count(GutenbergDownload.id))
            .group_by(GutenbergDownload.format)
        )
        downloads_by_format = {row[0].value: row[1] for row in format_result.all()}

        # Recent downloads
        recent_downloads = await self.db.execute(
            select(GutenbergDownload)
            .options(selectinload(GutenbergDownload.book))
            .order_by(GutenbergDownload.downloaded_at.desc())
            .limit(10)
        )
        recent = recent_downloads.scalars().all()
        recent_download_responses = [
            GutenbergDownloadResponse(
                id=dl.id,
                user_id=dl.user_id,
                book_id=dl.book_id,
                format=dl.format,
                downloaded_at=dl.downloaded_at,
                book_title=dl.book.title if dl.book else None,
            )
            for dl in recent
        ]

        # Popular subjects (from cached books)
        # This is a simplified version - could be enhanced with proper JSON querying
        popular_subjects: list[dict] = []

        return GutenbergStatsResponse(
            total_books=total_books,
            total_downloads=total_downloads,
            total_favorites=total_favorites,
            unique_patrons_downloaded=unique_patrons,
            popular_books=popular_books,
            popular_subjects=popular_subjects,
            downloads_by_format=downloads_by_format,
            recent_downloads=recent_download_responses,
        )
