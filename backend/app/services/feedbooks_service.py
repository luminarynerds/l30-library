# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.feedbooks_client import FeedbooksClient, FeedbooksClientError, FeedbooksBookData
from ..models.feedbooks import (
    FeedbooksBook, FeedbooksDownload, FeedbooksFavorite, FeedbooksSyncStatus,
)
from ..models.user import User
from ..schemas.feedbooks import (
    FeedbooksAuthorResponse, FeedbooksBookDetail, FeedbooksBookSummary,
    FeedbooksDownloadResponse, FeedbooksFavoriteResponse, FeedbooksSearchResponse,
    FeedbooksStatsResponse, FeedbooksSyncStatusResponse,
)
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class FeedbooksServiceError(Exception):
    pass


class FeedbooksService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self._client: FeedbooksClient | None = None

    async def _get_client(self) -> FeedbooksClient:
        if self._client is None:
            self._client = FeedbooksClient()
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def search_api(self, query: str, page: int = 1) -> FeedbooksSearchResponse:
        client = await self._get_client()
        try:
            result = await client.search(query, page=page)
            books = []
            for book_data in result.books:
                local = await self._get_local_book(book_data.feedbooks_id)
                books.append(FeedbooksBookSummary(
                    id=local.id if local else 0,
                    feedbooks_id=book_data.feedbooks_id,
                    title=book_data.title,
                    primary_author=book_data.primary_author,
                    cover_url=book_data.cover_url,
                    language=book_data.language,
                ))

            return FeedbooksSearchResponse(
                count=result.count, page=page, page_size=len(books),
                books=books, has_next=result.next_url is not None, has_previous=page > 1,
            )
        except FeedbooksClientError as e:
            raise FeedbooksServiceError(f"Search failed: {e.message}") from e

    async def search_local(self, query: str | None = None, page: int = 1, page_size: int = 20) -> FeedbooksSearchResponse:
        stmt = select(FeedbooksBook)
        if query:
            safe_q = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(
                FeedbooksBook.title.ilike(f"%{safe_q}%")
                | FeedbooksBook.authors.ilike(f"%{safe_q}%")
            )

        count_result = await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        total = count_result.scalar() or 0

        stmt = stmt.order_by(FeedbooksBook.title.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        books_db = result.scalars().all()

        books = []
        for book in books_db:
            authors = json.loads(book.authors) if book.authors else []
            primary_author = authors[0].get("name") if authors else None
            books.append(FeedbooksBookSummary(
                id=book.id, feedbooks_id=book.feedbooks_id, title=book.title,
                primary_author=primary_author, cover_url=book.cover_url, language=book.language,
            ))

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return FeedbooksSearchResponse(
            count=total, page=page, page_size=page_size, books=books,
            has_next=page < total_pages, has_previous=page > 1,
        )

    async def _get_local_book(self, feedbooks_id: str) -> FeedbooksBook | None:
        result = await self.db.execute(
            select(FeedbooksBook).where(FeedbooksBook.feedbooks_id == feedbooks_id)
        )
        return result.scalar_one_or_none()

    async def get_book(self, book_id: int, user: User | None = None) -> FeedbooksBookDetail | None:
        result = await self.db.execute(select(FeedbooksBook).where(FeedbooksBook.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            return None

        authors = None
        if book.authors:
            authors_data = json.loads(book.authors)
            authors = [FeedbooksAuthorResponse(**a) for a in authors_data]

        categories = json.loads(book.categories) if book.categories else None

        is_favorited = False
        download_history = None
        if user:
            fav_result = await self.db.execute(
                select(FeedbooksFavorite).where(
                    FeedbooksFavorite.user_id == user.id, FeedbooksFavorite.book_id == book.id,
                )
            )
            is_favorited = fav_result.scalar_one_or_none() is not None

            dl_result = await self.db.execute(
                select(FeedbooksDownload)
                .where(FeedbooksDownload.user_id == user.id, FeedbooksDownload.book_id == book.id)
                .order_by(FeedbooksDownload.downloaded_at.desc()).limit(10)
            )
            download_history = [
                FeedbooksDownloadResponse(
                    id=dl.id, user_id=dl.user_id, book_id=dl.book_id,
                    format=dl.format, downloaded_at=dl.downloaded_at, book_title=book.title,
                )
                for dl in dl_result.scalars().all()
            ]

        return FeedbooksBookDetail(
            id=book.id, feedbooks_id=book.feedbooks_id, title=book.title,
            authors=authors, summary=book.summary, content=book.content,
            categories=categories, language=book.language,
            published_at=book.published_at, publisher=book.publisher, rights=book.rights,
            epub_url=book.epub_url, mobi_url=book.mobi_url, pdf_url=book.pdf_url,
            cover_url=book.cover_url, thumbnail_url=book.thumbnail_url,
            source_url=book.source_url, catalog_item_id=book.catalog_item_id,
            last_synced_at=book.last_synced_at, created_at=book.created_at,
            is_favorited=is_favorited, download_history=download_history,
        )

    async def record_download(self, user: User, book_id: int, format: str = "epub") -> FeedbooksDownloadResponse:
        result = await self.db.execute(select(FeedbooksBook).where(FeedbooksBook.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            raise FeedbooksServiceError("Book not found")

        download = FeedbooksDownload(user_id=user.id, book_id=book_id, format=format, downloaded_at=utc_now())
        self.db.add(download)
        await self.db.flush()

        return FeedbooksDownloadResponse(
            id=download.id, user_id=download.user_id, book_id=download.book_id,
            format=download.format, downloaded_at=download.downloaded_at, book_title=book.title,
        )

    async def add_favorite(self, user: User, book_id: int, notes: str | None = None) -> FeedbooksFavoriteResponse:
        existing = await self.db.execute(
            select(FeedbooksFavorite).where(
                FeedbooksFavorite.user_id == user.id, FeedbooksFavorite.book_id == book_id,
            )
        )
        if existing.scalar_one_or_none():
            raise FeedbooksServiceError("Book already in favorites")

        book_result = await self.db.execute(select(FeedbooksBook).where(FeedbooksBook.id == book_id))
        book = book_result.scalar_one_or_none()
        if not book:
            raise FeedbooksServiceError("Book not found")

        favorite = FeedbooksFavorite(user_id=user.id, book_id=book_id, notes=notes, created_at=utc_now())
        self.db.add(favorite)
        await self.db.flush()

        authors = json.loads(book.authors) if book.authors else []
        primary_author = authors[0].get("name") if authors else None

        return FeedbooksFavoriteResponse(
            id=favorite.id, user_id=favorite.user_id, book_id=favorite.book_id,
            notes=favorite.notes, created_at=favorite.created_at,
            book=FeedbooksBookSummary(
                id=book.id, feedbooks_id=book.feedbooks_id, title=book.title,
                primary_author=primary_author, cover_url=book.cover_url, language=book.language,
            ),
        )

    async def remove_favorite(self, user: User, book_id: int) -> bool:
        result = await self.db.execute(
            delete(FeedbooksFavorite).where(
                FeedbooksFavorite.user_id == user.id, FeedbooksFavorite.book_id == book_id,
            )
        )
        return result.rowcount > 0

    async def _upsert_book(self, book_data: FeedbooksBookData) -> FeedbooksBook:
        existing = await self._get_local_book(book_data.feedbooks_id)
        authors_json = json.dumps([
            {"name": a.name, "uri": a.uri} for a in book_data.authors
        ]) if book_data.authors else None
        categories_json = json.dumps(book_data.categories) if book_data.categories else None

        if existing:
            existing.title = book_data.title
            existing.authors = authors_json
            existing.summary = book_data.summary
            existing.content = book_data.content
            existing.categories = categories_json
            existing.language = book_data.language
            existing.published_at = book_data.published_at
            existing.publisher = book_data.publisher
            existing.rights = book_data.rights
            existing.epub_url = book_data.epub_url
            existing.mobi_url = book_data.mobi_url
            existing.pdf_url = book_data.pdf_url
            existing.cover_url = book_data.cover_url
            existing.thumbnail_url = book_data.thumbnail_url
            existing.source_url = book_data.source_url
            existing.last_synced_at = utc_now()
            return existing
        else:
            new_book = FeedbooksBook(
                feedbooks_id=book_data.feedbooks_id, title=book_data.title,
                authors=authors_json, summary=book_data.summary, content=book_data.content,
                categories=categories_json, language=book_data.language,
                published_at=book_data.published_at, publisher=book_data.publisher,
                rights=book_data.rights, epub_url=book_data.epub_url,
                mobi_url=book_data.mobi_url, pdf_url=book_data.pdf_url,
                cover_url=book_data.cover_url, thumbnail_url=book_data.thumbnail_url,
                source_url=book_data.source_url, last_synced_at=utc_now(),
            )
            self.db.add(new_book)
            return new_book

    async def sync_catalog(self, max_pages: int | None = None) -> dict[str, Any]:
        result = await self.db.execute(select(FeedbooksSyncStatus).limit(1))
        status = result.scalar_one_or_none()
        if not status:
            status = FeedbooksSyncStatus(total_books_synced=0, is_syncing=False)
            self.db.add(status)
            await self.db.flush()

        if status.is_syncing:
            raise FeedbooksServiceError("Sync already in progress")

        status.is_syncing = True
        status.sync_started_at = utc_now()
        status.sync_error = None
        await self.db.commit()

        client = await self._get_client()
        synced_count = 0

        try:
            async for batch in client.iter_catalog(max_pages=max_pages):
                for book_data in batch:
                    await self._upsert_book(book_data)
                    synced_count += 1
                status.total_books_synced = synced_count
                await self.db.commit()

            status.is_syncing = False
            status.last_sync_at = utc_now()
            await self.db.commit()

            # Auto-ingest into general catalog
            ingested = 0
            try:
                from .free_ebook_ingestion_service import FreeEbookIngestionService
                ingestion = FreeEbookIngestionService(self.db)
                ingested = await ingestion._ingest_feedbooks()
                await self.db.commit()
                logger.info(f"Auto-ingested {ingested} Feedbooks into catalog")
            except Exception as e:  # noqa: BLE001 -- auto-ingestion non-fatal: sync success not blocked by catalog ingest failure
                logger.warning(f"Auto-ingestion failed (non-fatal): {e}")

            return {"success": True, "books_synced": synced_count, "catalog_ingested": ingested}

        except Exception as e:
            logger.error(f"Feedbooks sync failed: {e}")
            status.is_syncing = False
            status.sync_error = str(e)
            await self.db.commit()
            raise FeedbooksServiceError(f"Sync failed: {e}") from e

    async def get_statistics(self) -> FeedbooksStatsResponse:
        book_count = (await self.db.execute(select(func.count(FeedbooksBook.id)))).scalar() or 0
        dl_count = (await self.db.execute(select(func.count(FeedbooksDownload.id)))).scalar() or 0
        fav_count = (await self.db.execute(select(func.count(FeedbooksFavorite.id)))).scalar() or 0
        return FeedbooksStatsResponse(total_books=book_count, total_downloads=dl_count, total_favorites=fav_count)
