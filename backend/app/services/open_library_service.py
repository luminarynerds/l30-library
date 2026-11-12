# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..clients.open_library_client import (
    OpenLibraryClient,
    OpenLibraryClientError,
    OpenLibraryBookData,
)
from ..models.open_library import (
    OpenLibraryBook,
    OpenLibraryDownload,
    OpenLibraryFavorite,
    OpenLibrarySyncStatus,
)
from ..models.user import User
from ..schemas.open_library import (
    OpenLibraryAuthorResponse,
    OpenLibraryBookDetail,
    OpenLibraryBookSummary,
    OpenLibraryDownloadResponse,
    OpenLibraryFavoriteResponse,
    OpenLibrarySearchResponse,
    OpenLibraryStatsResponse,
    OpenLibrarySyncStatusResponse,
)
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class OpenLibraryServiceError(Exception):
    pass


class OpenLibraryService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self._client: OpenLibraryClient | None = None

    async def _get_client(self) -> OpenLibraryClient:
        if self._client is None:
            self._client = OpenLibraryClient()
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def search_api(
        self,
        query: str | None = None,
        author: str | None = None,
        title: str | None = None,
        subject: str | None = None,
        languages: list[str] | None = None,
        free_only: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> OpenLibrarySearchResponse:
        client = await self._get_client()
        offset = (page - 1) * page_size

        try:
            result = await client.search(
                query=query,
                author=author,
                title=title,
                subject=subject,
                languages=languages,
                has_fulltext=True if free_only else None,
                ebook_access="public" if free_only else None,
                limit=page_size,
                offset=offset,
            )

            books = []
            for book_data in result.books:
                local_book = await self._get_local_book(book_data.ol_work_id)
                books.append(OpenLibraryBookSummary(
                    id=local_book.id if local_book else 0,
                    ol_work_id=book_data.ol_work_id,
                    title=book_data.title,
                    primary_author=book_data.primary_author,
                    cover_url=book_data.cover_url,
                    edition_count=book_data.edition_count,
                    languages=",".join(book_data.languages) if book_data.languages else None,
                    has_fulltext=book_data.has_fulltext,
                ))

            total_pages = (result.count + page_size - 1) // page_size if result.count > 0 else 0

            return OpenLibrarySearchResponse(
                count=result.count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                books=books,
                has_next=page < total_pages,
                has_previous=page > 1,
            )
        except OpenLibraryClientError as e:
            logger.error(f"Open Library API search failed: {e}")
            raise OpenLibraryServiceError(f"Search failed: {e.message}") from e

    async def search_local(
        self,
        query: str | None = None,
        author: str | None = None,
        languages: list[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> OpenLibrarySearchResponse:
        stmt = select(OpenLibraryBook)

        if query:
            safe_q = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(OpenLibraryBook.title.ilike(f"%{safe_q}%"))
        if author:
            safe_author = author.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(OpenLibraryBook.authors.ilike(f"%{safe_author}%"))
        if languages:
            lang_filter = None
            for lang in languages:
                safe_lang = lang.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                f = OpenLibraryBook.languages.ilike(f"%{safe_lang}%")
                lang_filter = f if lang_filter is None else lang_filter | f
            if lang_filter is not None:
                stmt = stmt.where(lang_filter)

        count_result = await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        total_count = count_result.scalar() or 0

        stmt = stmt.order_by(OpenLibraryBook.edition_count.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        books_db = result.scalars().all()

        books = []
        for book in books_db:
            authors = json.loads(book.authors) if book.authors else []
            primary_author = authors[0].get("name") if authors else None
            books.append(OpenLibraryBookSummary(
                id=book.id,
                ol_work_id=book.ol_work_id,
                title=book.title,
                primary_author=primary_author,
                cover_url=book.cover_url,
                edition_count=book.edition_count,
                languages=book.languages,
                has_fulltext=book.has_fulltext,
            ))

        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

        return OpenLibrarySearchResponse(
            count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            books=books,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def _get_local_book(self, ol_work_id: str) -> OpenLibraryBook | None:
        result = await self.db.execute(
            select(OpenLibraryBook).where(OpenLibraryBook.ol_work_id == ol_work_id)
        )
        return result.scalar_one_or_none()

    async def get_book(self, book_id: int, user: User | None = None) -> OpenLibraryBookDetail | None:
        result = await self.db.execute(
            select(OpenLibraryBook).where(OpenLibraryBook.id == book_id)
        )
        book = result.scalar_one_or_none()
        if not book:
            return None
        return await self._book_to_detail(book, user)

    async def _book_to_detail(self, book: OpenLibraryBook, user: User | None = None) -> OpenLibraryBookDetail:
        authors = None
        if book.authors:
            authors_data = json.loads(book.authors)
            authors = [OpenLibraryAuthorResponse(**a) for a in authors_data]

        availability = json.loads(book.availability) if book.availability else None
        subjects = json.loads(book.subjects) if book.subjects else None

        is_favorited = False
        download_history = None
        if user:
            fav_result = await self.db.execute(
                select(OpenLibraryFavorite).where(
                    OpenLibraryFavorite.user_id == user.id,
                    OpenLibraryFavorite.book_id == book.id,
                )
            )
            is_favorited = fav_result.scalar_one_or_none() is not None

            dl_result = await self.db.execute(
                select(OpenLibraryDownload)
                .where(OpenLibraryDownload.user_id == user.id, OpenLibraryDownload.book_id == book.id)
                .order_by(OpenLibraryDownload.accessed_at.desc())
                .limit(10)
            )
            downloads = dl_result.scalars().all()
            download_history = [
                OpenLibraryDownloadResponse(
                    id=dl.id, user_id=dl.user_id, book_id=dl.book_id,
                    access_type=dl.access_type, accessed_at=dl.accessed_at,
                    book_title=book.title,
                )
                for dl in downloads
            ]

        read_url = None
        if availability and isinstance(availability, dict):
            read_url = availability.get("read_url")

        return OpenLibraryBookDetail(
            id=book.id,
            ol_work_id=book.ol_work_id,
            ol_edition_id=book.ol_edition_id,
            title=book.title,
            authors=authors,
            subjects=subjects,
            languages=book.languages,
            first_publish_year=book.first_publish_year,
            publisher=book.publisher,
            isbn_13=book.isbn_13,
            isbn_10=book.isbn_10,
            has_fulltext=book.has_fulltext,
            public_scan=book.public_scan,
            cover_url=book.cover_url,
            availability=availability,
            edition_count=book.edition_count,
            catalog_item_id=book.catalog_item_id,
            last_synced_at=book.last_synced_at,
            created_at=book.created_at,
            read_url=read_url,
            is_favorited=is_favorited,
            download_history=download_history,
        )

    async def record_download(self, user: User, book_id: int, access_type: str = "read_online") -> OpenLibraryDownloadResponse:
        result = await self.db.execute(select(OpenLibraryBook).where(OpenLibraryBook.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            raise OpenLibraryServiceError("Book not found")

        download = OpenLibraryDownload(
            user_id=user.id, book_id=book_id, access_type=access_type, accessed_at=utc_now(),
        )
        self.db.add(download)
        await self.db.flush()

        return OpenLibraryDownloadResponse(
            id=download.id, user_id=download.user_id, book_id=download.book_id,
            access_type=download.access_type, accessed_at=download.accessed_at,
            book_title=book.title,
        )

    async def add_favorite(self, user: User, book_id: int, notes: str | None = None) -> OpenLibraryFavoriteResponse:
        existing = await self.db.execute(
            select(OpenLibraryFavorite).where(
                OpenLibraryFavorite.user_id == user.id, OpenLibraryFavorite.book_id == book_id,
            )
        )
        if existing.scalar_one_or_none():
            raise OpenLibraryServiceError("Book already in favorites")

        book_result = await self.db.execute(select(OpenLibraryBook).where(OpenLibraryBook.id == book_id))
        book = book_result.scalar_one_or_none()
        if not book:
            raise OpenLibraryServiceError("Book not found")

        favorite = OpenLibraryFavorite(user_id=user.id, book_id=book_id, notes=notes, created_at=utc_now())
        self.db.add(favorite)
        await self.db.flush()

        authors = json.loads(book.authors) if book.authors else []
        primary_author = authors[0].get("name") if authors else None

        return OpenLibraryFavoriteResponse(
            id=favorite.id, user_id=favorite.user_id, book_id=favorite.book_id,
            notes=favorite.notes, created_at=favorite.created_at,
            book=OpenLibraryBookSummary(
                id=book.id, ol_work_id=book.ol_work_id, title=book.title,
                primary_author=primary_author, cover_url=book.cover_url,
                edition_count=book.edition_count, languages=book.languages,
                has_fulltext=book.has_fulltext,
            ),
        )

    async def remove_favorite(self, user: User, book_id: int) -> bool:
        result = await self.db.execute(
            delete(OpenLibraryFavorite).where(
                OpenLibraryFavorite.user_id == user.id, OpenLibraryFavorite.book_id == book_id,
            )
        )
        return result.rowcount > 0

    async def _upsert_book(self, book_data: OpenLibraryBookData) -> OpenLibraryBook:
        existing = await self._get_local_book(book_data.ol_work_id)
        authors_json = json.dumps([
            {"name": a.name, "ol_id": a.ol_id} for a in book_data.authors
        ]) if book_data.authors else None
        subjects_json = json.dumps(book_data.subjects) if book_data.subjects else None

        if existing:
            existing.title = book_data.title
            existing.authors = authors_json
            existing.subjects = subjects_json
            existing.languages = ",".join(book_data.languages) if book_data.languages else None
            existing.first_publish_year = book_data.first_publish_year
            existing.publisher = book_data.publisher
            existing.isbn_13 = book_data.isbn_13
            existing.isbn_10 = book_data.isbn_10
            existing.has_fulltext = book_data.has_fulltext
            existing.public_scan = book_data.public_scan
            existing.cover_id = book_data.cover_id
            existing.cover_url = book_data.cover_url
            existing.edition_count = book_data.edition_count
            existing.ol_edition_id = book_data.ol_edition_id
            existing.last_synced_at = utc_now()
            return existing
        else:
            new_book = OpenLibraryBook(
                ol_work_id=book_data.ol_work_id,
                ol_edition_id=book_data.ol_edition_id,
                title=book_data.title,
                authors=authors_json,
                subjects=subjects_json,
                languages=",".join(book_data.languages) if book_data.languages else None,
                first_publish_year=book_data.first_publish_year,
                publisher=book_data.publisher,
                isbn_13=book_data.isbn_13,
                isbn_10=book_data.isbn_10,
                has_fulltext=book_data.has_fulltext,
                public_scan=book_data.public_scan,
                cover_id=book_data.cover_id,
                cover_url=book_data.cover_url,
                edition_count=book_data.edition_count,
                last_synced_at=utc_now(),
            )
            self.db.add(new_book)
            return new_book

    async def sync_catalog(
        self,
        subject: str | None = None,
        max_batches: int | None = None,
    ) -> dict[str, Any]:
        result = await self.db.execute(select(OpenLibrarySyncStatus).limit(1))
        status = result.scalar_one_or_none()
        if not status:
            status = OpenLibrarySyncStatus(total_books_synced=0, last_synced_offset=0, is_syncing=False)
            self.db.add(status)
            await self.db.flush()

        if status.is_syncing:
            raise OpenLibraryServiceError("Sync already in progress")

        status.is_syncing = True
        status.sync_started_at = utc_now()
        status.sync_error = None
        await self.db.commit()

        client = await self._get_client()
        synced_count = 0

        try:
            async for books_batch in client.iter_free_ebooks(
                subject=subject, max_batches=max_batches,
            ):
                for book_data in books_batch:
                    await self._upsert_book(book_data)
                    synced_count += 1

                status.total_books_synced = synced_count
                await self.db.commit()

                if synced_count % 100 == 0:
                    logger.info(f"Open Library sync progress: {synced_count} books synced")

            status.is_syncing = False
            status.last_full_sync_at = utc_now()
            await self.db.commit()

            # Auto-ingest new records into the general catalog
            ingested = 0
            try:
                from .free_ebook_ingestion_service import FreeEbookIngestionService
                ingestion = FreeEbookIngestionService(self.db)
                ingested = await ingestion._ingest_open_library()
                await self.db.commit()
                logger.info(f"Auto-ingested {ingested} Open Library books into catalog")
            except Exception as e:  # noqa: BLE001 -- auto-ingestion non-fatal: sync success not blocked by catalog ingest failure
                logger.warning(f"Auto-ingestion failed (non-fatal): {e}")

            return {"success": True, "books_synced": synced_count, "catalog_ingested": ingested}

        except Exception as e:
            logger.error(f"Open Library sync failed: {e}")
            status.is_syncing = False
            status.sync_error = str(e)
            await self.db.commit()
            raise OpenLibraryServiceError(f"Sync failed: {e}") from e

    async def get_sync_status(self) -> OpenLibrarySyncStatusResponse | None:
        result = await self.db.execute(select(OpenLibrarySyncStatus).limit(1))
        status = result.scalar_one_or_none()
        if not status:
            return None
        return OpenLibrarySyncStatusResponse(
            id=status.id, last_full_sync_at=status.last_full_sync_at,
            last_incremental_sync_at=status.last_incremental_sync_at,
            total_books_synced=status.total_books_synced,
            last_synced_offset=status.last_synced_offset,
            is_syncing=status.is_syncing, sync_started_at=status.sync_started_at,
            sync_error=status.sync_error, created_at=status.created_at,
            updated_at=status.updated_at,
        )

    async def get_statistics(self) -> OpenLibraryStatsResponse:
        book_count = (await self.db.execute(select(func.count(OpenLibraryBook.id)))).scalar() or 0
        dl_count = (await self.db.execute(select(func.count(OpenLibraryDownload.id)))).scalar() or 0
        fav_count = (await self.db.execute(select(func.count(OpenLibraryFavorite.id)))).scalar() or 0
        unique = (await self.db.execute(
            select(func.count(func.distinct(OpenLibraryDownload.user_id)))
        )).scalar() or 0

        popular_stmt = select(OpenLibraryBook).order_by(OpenLibraryBook.edition_count.desc()).limit(10)
        popular_result = await self.db.execute(popular_stmt)
        popular_books = []
        for book in popular_result.scalars().all():
            authors = json.loads(book.authors) if book.authors else []
            primary_author = authors[0].get("name") if authors else None
            popular_books.append(OpenLibraryBookSummary(
                id=book.id, ol_work_id=book.ol_work_id, title=book.title,
                primary_author=primary_author, cover_url=book.cover_url,
                edition_count=book.edition_count, languages=book.languages,
                has_fulltext=book.has_fulltext,
            ))

        return OpenLibraryStatsResponse(
            total_books=book_count, total_downloads=dl_count,
            total_favorites=fav_count, unique_patrons=unique,
            popular_books=popular_books,
        )
