# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.standard_ebooks_client import (
    StandardEbooksClient,
    StandardEbooksClientError,
    StandardEbookData,
)
from ..models.standard_ebooks import (
    StandardEbook,
    StandardEbookDownload,
    StandardEbookFavorite,
    StandardEbookSyncStatus,
)
from ..models.user import User
from ..schemas.standard_ebooks import (
    StandardEbookAuthorResponse,
    StandardEbookDetail,
    StandardEbookDownloadResponse,
    StandardEbookFavoriteResponse,
    StandardEbookSearchResponse,
    StandardEbookStatsResponse,
    StandardEbookSummary,
    StandardEbookSyncStatusResponse,
)
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class StandardEbooksServiceError(Exception):
    pass


class StandardEbooksService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self._client: StandardEbooksClient | None = None

    async def _get_client(self) -> StandardEbooksClient:
        if self._client is None:
            self._client = StandardEbooksClient()
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def search_api(self, query: str) -> StandardEbookSearchResponse:
        client = await self._get_client()
        try:
            books_data = await client.search(query)
            books = []
            for book_data in books_data:
                local = await self._get_local_book(book_data.se_identifier)
                books.append(StandardEbookSummary(
                    id=local.id if local else 0,
                    se_identifier=book_data.se_identifier,
                    title=book_data.title,
                    primary_author=book_data.primary_author,
                    cover_url=book_data.cover_url,
                    language=book_data.language,
                ))
            return StandardEbookSearchResponse(count=len(books), books=books)
        except StandardEbooksClientError as e:
            raise StandardEbooksServiceError(f"Search failed: {e.message}") from e

    async def search_local(self, query: str | None = None, page: int = 1, page_size: int = 20) -> StandardEbookSearchResponse:
        stmt = select(StandardEbook)
        if query:
            safe_q = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(
                StandardEbook.title.ilike(f"%{safe_q}%")
                | StandardEbook.authors.ilike(f"%{safe_q}%")
            )
        stmt = stmt.order_by(StandardEbook.title.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        books_db = result.scalars().all()

        books = []
        for book in books_db:
            authors = json.loads(book.authors) if book.authors else []
            primary_author = authors[0].get("name") if authors else None
            books.append(StandardEbookSummary(
                id=book.id, se_identifier=book.se_identifier, title=book.title,
                primary_author=primary_author, cover_url=book.cover_url,
                language=book.language,
            ))

        count_result = await self.db.execute(select(func.count(StandardEbook.id)))
        total = count_result.scalar() or 0

        return StandardEbookSearchResponse(count=total, books=books)

    async def _get_local_book(self, se_identifier: str) -> StandardEbook | None:
        result = await self.db.execute(
            select(StandardEbook).where(StandardEbook.se_identifier == se_identifier)
        )
        return result.scalar_one_or_none()

    async def get_book(self, book_id: int, user: User | None = None) -> StandardEbookDetail | None:
        result = await self.db.execute(select(StandardEbook).where(StandardEbook.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            return None
        return await self._book_to_detail(book, user)

    async def _book_to_detail(self, book: StandardEbook, user: User | None = None) -> StandardEbookDetail:
        authors = None
        if book.authors:
            authors_data = json.loads(book.authors)
            authors = [StandardEbookAuthorResponse(**a) for a in authors_data]

        subjects = json.loads(book.subjects) if book.subjects else None

        is_favorited = False
        download_history = None
        if user:
            fav_result = await self.db.execute(
                select(StandardEbookFavorite).where(
                    StandardEbookFavorite.user_id == user.id,
                    StandardEbookFavorite.book_id == book.id,
                )
            )
            is_favorited = fav_result.scalar_one_or_none() is not None

            dl_result = await self.db.execute(
                select(StandardEbookDownload)
                .where(StandardEbookDownload.user_id == user.id, StandardEbookDownload.book_id == book.id)
                .order_by(StandardEbookDownload.downloaded_at.desc()).limit(10)
            )
            download_history = [
                StandardEbookDownloadResponse(
                    id=dl.id, user_id=dl.user_id, book_id=dl.book_id,
                    format=dl.format, downloaded_at=dl.downloaded_at, book_title=book.title,
                )
                for dl in dl_result.scalars().all()
            ]

        return StandardEbookDetail(
            id=book.id, se_identifier=book.se_identifier, title=book.title,
            authors=authors, description=book.description, long_description=book.long_description,
            subjects=subjects, language=book.language,
            published_at=book.published_at, word_count=book.word_count,
            epub_url=book.epub_url, azw3_url=book.azw3_url, kepub_url=book.kepub_url,
            cover_url=book.cover_url, thumbnail_url=book.thumbnail_url,
            source_url=book.source_url, catalog_item_id=book.catalog_item_id,
            last_synced_at=book.last_synced_at, created_at=book.created_at,
            is_favorited=is_favorited, download_history=download_history,
        )

    async def record_download(self, user: User, book_id: int, format: str = "epub") -> StandardEbookDownloadResponse:
        result = await self.db.execute(select(StandardEbook).where(StandardEbook.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            raise StandardEbooksServiceError("Book not found")

        download = StandardEbookDownload(
            user_id=user.id, book_id=book_id, format=format, downloaded_at=utc_now(),
        )
        self.db.add(download)
        await self.db.flush()

        return StandardEbookDownloadResponse(
            id=download.id, user_id=download.user_id, book_id=download.book_id,
            format=download.format, downloaded_at=download.downloaded_at, book_title=book.title,
        )

    async def add_favorite(self, user: User, book_id: int, notes: str | None = None) -> StandardEbookFavoriteResponse:
        existing = await self.db.execute(
            select(StandardEbookFavorite).where(
                StandardEbookFavorite.user_id == user.id, StandardEbookFavorite.book_id == book_id,
            )
        )
        if existing.scalar_one_or_none():
            raise StandardEbooksServiceError("Book already in favorites")

        book_result = await self.db.execute(select(StandardEbook).where(StandardEbook.id == book_id))
        book = book_result.scalar_one_or_none()
        if not book:
            raise StandardEbooksServiceError("Book not found")

        favorite = StandardEbookFavorite(user_id=user.id, book_id=book_id, notes=notes, created_at=utc_now())
        self.db.add(favorite)
        await self.db.flush()

        authors = json.loads(book.authors) if book.authors else []
        primary_author = authors[0].get("name") if authors else None

        return StandardEbookFavoriteResponse(
            id=favorite.id, user_id=favorite.user_id, book_id=favorite.book_id,
            notes=favorite.notes, created_at=favorite.created_at,
            book=StandardEbookSummary(
                id=book.id, se_identifier=book.se_identifier, title=book.title,
                primary_author=primary_author, cover_url=book.cover_url, language=book.language,
            ),
        )

    async def remove_favorite(self, user: User, book_id: int) -> bool:
        result = await self.db.execute(
            delete(StandardEbookFavorite).where(
                StandardEbookFavorite.user_id == user.id, StandardEbookFavorite.book_id == book_id,
            )
        )
        return result.rowcount > 0

    async def _upsert_book(self, book_data: StandardEbookData) -> StandardEbook:
        existing = await self._get_local_book(book_data.se_identifier)
        authors_json = json.dumps([
            {"name": a.name, "url": a.url} for a in book_data.authors
        ]) if book_data.authors else None
        subjects_json = json.dumps(book_data.subjects) if book_data.subjects else None

        if existing:
            existing.title = book_data.title
            existing.authors = authors_json
            existing.description = book_data.description
            existing.long_description = book_data.long_description
            existing.subjects = subjects_json
            existing.language = book_data.language
            existing.published_at = book_data.published_at
            existing.updated_at_source = book_data.updated_at
            existing.epub_url = book_data.epub_url
            existing.azw3_url = book_data.azw3_url
            existing.kepub_url = book_data.kepub_url
            existing.cover_url = book_data.cover_url
            existing.thumbnail_url = book_data.thumbnail_url
            existing.source_url = book_data.source_url
            existing.last_synced_at = utc_now()
            return existing
        else:
            new_book = StandardEbook(
                se_identifier=book_data.se_identifier, title=book_data.title,
                authors=authors_json, description=book_data.description,
                long_description=book_data.long_description, subjects=subjects_json,
                language=book_data.language, published_at=book_data.published_at,
                updated_at_source=book_data.updated_at,
                epub_url=book_data.epub_url, azw3_url=book_data.azw3_url,
                kepub_url=book_data.kepub_url, cover_url=book_data.cover_url,
                thumbnail_url=book_data.thumbnail_url, source_url=book_data.source_url,
                last_synced_at=utc_now(),
            )
            self.db.add(new_book)
            return new_book

    async def sync_catalog(self, full_catalog: bool = False) -> dict[str, Any]:
        result = await self.db.execute(select(StandardEbookSyncStatus).limit(1))
        status = result.scalar_one_or_none()
        if not status:
            status = StandardEbookSyncStatus(total_books_synced=0, is_syncing=False)
            self.db.add(status)
            await self.db.flush()

        if status.is_syncing:
            raise StandardEbooksServiceError("Sync already in progress")

        status.is_syncing = True
        status.sync_started_at = utc_now()
        status.sync_error = None
        await self.db.commit()

        client = await self._get_client()
        synced_count = 0

        try:
            if full_catalog:
                books = await client.get_catalog()
            else:
                books = await client.get_new_releases()

            for book_data in books:
                await self._upsert_book(book_data)
                synced_count += 1

            await self.db.commit()

            status.is_syncing = False
            status.last_sync_at = utc_now()
            status.total_books_synced = synced_count
            await self.db.commit()

            # Auto-ingest into general catalog
            ingested = 0
            try:
                from .free_ebook_ingestion_service import FreeEbookIngestionService
                ingestion = FreeEbookIngestionService(self.db)
                ingested = await ingestion._ingest_standard_ebooks()
                await self.db.commit()
                logger.info(f"Auto-ingested {ingested} Standard Ebooks into catalog")
            except Exception as e:  # noqa: BLE001 -- auto-ingestion non-fatal: sync success not blocked by catalog ingest failure
                logger.warning(f"Auto-ingestion failed (non-fatal): {e}")

            return {"success": True, "books_synced": synced_count, "catalog_ingested": ingested}

        except Exception as e:
            logger.error(f"Standard Ebooks sync failed: {e}")
            status.is_syncing = False
            status.sync_error = str(e)
            await self.db.commit()
            raise StandardEbooksServiceError(f"Sync failed: {e}") from e

    async def get_statistics(self) -> StandardEbookStatsResponse:
        book_count = (await self.db.execute(select(func.count(StandardEbook.id)))).scalar() or 0
        dl_count = (await self.db.execute(select(func.count(StandardEbookDownload.id)))).scalar() or 0
        fav_count = (await self.db.execute(select(func.count(StandardEbookFavorite.id)))).scalar() or 0
        return StandardEbookStatsResponse(total_books=book_count, total_downloads=dl_count, total_favorites=fav_count)
