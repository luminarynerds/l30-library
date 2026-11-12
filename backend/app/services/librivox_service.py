# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.librivox_client import LibriVoxClient, LibriVoxClientError, LibriVoxAudiobookData
from ..models.librivox import (
    LibriVoxAudiobook, LibriVoxListen, LibriVoxFavorite, LibriVoxSyncStatus,
)
from ..models.user import User
from ..schemas.librivox import (
    LibriVoxAuthorResponse, LibriVoxAudiobookDetail, LibriVoxAudiobookSummary,
    LibriVoxFavoriteResponse, LibriVoxListenResponse, LibriVoxSearchResponse,
    LibriVoxStatsResponse, LibriVoxSyncStatusResponse,
)
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class LibriVoxServiceError(Exception):
    pass


class LibriVoxService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self._client: LibriVoxClient | None = None

    async def _get_client(self) -> LibriVoxClient:
        if self._client is None:
            self._client = LibriVoxClient()
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def search_api(
        self,
        query: str | None = None,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> LibriVoxSearchResponse:
        client = await self._get_client()
        offset = (page - 1) * page_size

        try:
            result = await client.search(
                query=query, title=title, author=author, genre=genre,
                limit=page_size, offset=offset,
            )

            books = []
            for book_data in result.books:
                local = await self._get_local_audiobook(book_data.librivox_id)
                books.append(LibriVoxAudiobookSummary(
                    id=local.id if local else 0,
                    librivox_id=book_data.librivox_id,
                    title=book_data.title,
                    primary_author=book_data.primary_author,
                    language=book_data.language,
                    total_time=book_data.total_time,
                    num_sections=book_data.num_sections,
                ))

            return LibriVoxSearchResponse(
                count=result.count,
                page=page,
                page_size=page_size,
                books=books,
                has_next=len(books) >= page_size,
                has_previous=page > 1,
            )
        except LibriVoxClientError as e:
            raise LibriVoxServiceError(f"Search failed: {e.message}") from e

    async def search_local(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> LibriVoxSearchResponse:
        stmt = select(LibriVoxAudiobook)
        if query:
            safe_q = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(
                LibriVoxAudiobook.title.ilike(f"%{safe_q}%")
                | LibriVoxAudiobook.authors.ilike(f"%{safe_q}%")
            )

        count_result = await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        total = count_result.scalar() or 0

        stmt = stmt.order_by(LibriVoxAudiobook.title.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        books_db = result.scalars().all()

        books = []
        for book in books_db:
            authors = json.loads(book.authors) if book.authors else []
            primary_author = f"{authors[0].get('first_name', '')} {authors[0].get('last_name', '')}".strip() if authors else None
            books.append(LibriVoxAudiobookSummary(
                id=book.id, librivox_id=book.librivox_id, title=book.title,
                primary_author=primary_author, language=book.language,
                total_time=book.total_time, num_sections=book.num_sections,
            ))

        return LibriVoxSearchResponse(
            count=total, page=page, page_size=page_size, books=books,
            has_next=page * page_size < total, has_previous=page > 1,
        )

    async def _get_local_audiobook(self, librivox_id: int) -> LibriVoxAudiobook | None:
        result = await self.db.execute(
            select(LibriVoxAudiobook).where(LibriVoxAudiobook.librivox_id == librivox_id)
        )
        return result.scalar_one_or_none()

    async def get_audiobook(self, book_id: int, user: User | None = None) -> LibriVoxAudiobookDetail | None:
        result = await self.db.execute(select(LibriVoxAudiobook).where(LibriVoxAudiobook.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            return None
        return await self._book_to_detail(book, user)

    async def _book_to_detail(self, book: LibriVoxAudiobook, user: User | None = None) -> LibriVoxAudiobookDetail:
        authors = None
        if book.authors:
            authors_data = json.loads(book.authors)
            authors = [LibriVoxAuthorResponse(
                first_name=a.get("first_name", ""), last_name=a.get("last_name", ""),
                full_name=f"{a.get('first_name', '')} {a.get('last_name', '')}".strip(),
                dob=a.get("dob"), dod=a.get("dod"),
            ) for a in authors_data]

        genres = json.loads(book.genres) if book.genres else None

        is_favorited = False
        listen_history = None
        if user:
            fav_result = await self.db.execute(
                select(LibriVoxFavorite).where(
                    LibriVoxFavorite.user_id == user.id, LibriVoxFavorite.audiobook_id == book.id,
                )
            )
            is_favorited = fav_result.scalar_one_or_none() is not None

            listen_result = await self.db.execute(
                select(LibriVoxListen)
                .where(LibriVoxListen.user_id == user.id, LibriVoxListen.audiobook_id == book.id)
                .order_by(LibriVoxListen.listened_at.desc()).limit(10)
            )
            listen_history = [
                LibriVoxListenResponse(
                    id=l.id, user_id=l.user_id, audiobook_id=l.audiobook_id,
                    section_number=l.section_number, listened_at=l.listened_at,
                    audiobook_title=book.title,
                )
                for l in listen_result.scalars().all()
            ]

        return LibriVoxAudiobookDetail(
            id=book.id, librivox_id=book.librivox_id, title=book.title,
            authors=authors, description=book.description, genres=genres,
            language=book.language, book_type=str(book.book_type) if book.book_type else "solo",
            total_time=book.total_time, num_sections=book.num_sections,
            copyright_year=book.copyright_year, url_librivox=book.url_librivox,
            url_project=book.url_project, url_rss=book.url_rss, url_zip=book.url_zip,
            gutenberg_id=book.gutenberg_id, catalog_item_id=book.catalog_item_id,
            last_synced_at=book.last_synced_at, created_at=book.created_at,
            is_favorited=is_favorited, listen_history=listen_history,
        )

    async def record_listen(self, user: User, audiobook_id: int, section_number: int | None = None) -> LibriVoxListenResponse:
        result = await self.db.execute(select(LibriVoxAudiobook).where(LibriVoxAudiobook.id == audiobook_id))
        book = result.scalar_one_or_none()
        if not book:
            raise LibriVoxServiceError("Audiobook not found")

        listen = LibriVoxListen(
            user_id=user.id, audiobook_id=audiobook_id,
            section_number=section_number, listened_at=utc_now(),
        )
        self.db.add(listen)
        await self.db.flush()

        return LibriVoxListenResponse(
            id=listen.id, user_id=listen.user_id, audiobook_id=listen.audiobook_id,
            section_number=listen.section_number, listened_at=listen.listened_at,
            audiobook_title=book.title,
        )

    async def add_favorite(self, user: User, audiobook_id: int, notes: str | None = None) -> LibriVoxFavoriteResponse:
        existing = await self.db.execute(
            select(LibriVoxFavorite).where(
                LibriVoxFavorite.user_id == user.id, LibriVoxFavorite.audiobook_id == audiobook_id,
            )
        )
        if existing.scalar_one_or_none():
            raise LibriVoxServiceError("Audiobook already in favorites")

        book_result = await self.db.execute(select(LibriVoxAudiobook).where(LibriVoxAudiobook.id == audiobook_id))
        book = book_result.scalar_one_or_none()
        if not book:
            raise LibriVoxServiceError("Audiobook not found")

        favorite = LibriVoxFavorite(user_id=user.id, audiobook_id=audiobook_id, notes=notes, created_at=utc_now())
        self.db.add(favorite)
        await self.db.flush()

        authors = json.loads(book.authors) if book.authors else []
        primary_author = f"{authors[0].get('first_name', '')} {authors[0].get('last_name', '')}".strip() if authors else None

        return LibriVoxFavoriteResponse(
            id=favorite.id, user_id=favorite.user_id, audiobook_id=favorite.audiobook_id,
            notes=favorite.notes, created_at=favorite.created_at,
            audiobook=LibriVoxAudiobookSummary(
                id=book.id, librivox_id=book.librivox_id, title=book.title,
                primary_author=primary_author, language=book.language,
                total_time=book.total_time, num_sections=book.num_sections,
            ),
        )

    async def remove_favorite(self, user: User, audiobook_id: int) -> bool:
        result = await self.db.execute(
            delete(LibriVoxFavorite).where(
                LibriVoxFavorite.user_id == user.id, LibriVoxFavorite.audiobook_id == audiobook_id,
            )
        )
        return result.rowcount > 0

    async def _upsert_audiobook(self, data: LibriVoxAudiobookData) -> LibriVoxAudiobook:
        existing = await self._get_local_audiobook(data.librivox_id)
        authors_json = json.dumps([
            {"first_name": a.first_name, "last_name": a.last_name, "dob": a.dob, "dod": a.dod}
            for a in data.authors
        ]) if data.authors else None
        genres_json = json.dumps(data.genres) if data.genres else None
        sections_json = json.dumps([
            {"section_number": s.section_number, "title": s.title, "listen_url": s.listen_url,
             "reader": s.reader, "playtime": s.playtime}
            for s in data.sections
        ]) if data.sections else None

        if existing:
            existing.title = data.title
            existing.authors = authors_json
            existing.description = data.description
            existing.genres = genres_json
            existing.language = data.language
            existing.total_time = data.total_time
            existing.num_sections = data.num_sections
            existing.copyright_year = data.copyright_year
            existing.url_librivox = data.url_librivox
            existing.url_project = data.url_project
            existing.url_rss = data.url_rss
            existing.url_zip = data.url_zip
            existing.sections = sections_json
            existing.totaltime_secs = data.totaltime_secs
            existing.gutenberg_id = data.gutenberg_id
            existing.last_synced_at = utc_now()
            return existing
        else:
            new_book = LibriVoxAudiobook(
                librivox_id=data.librivox_id, title=data.title, authors=authors_json,
                description=data.description, genres=genres_json, language=data.language,
                total_time=data.total_time, num_sections=data.num_sections,
                copyright_year=data.copyright_year, url_librivox=data.url_librivox,
                url_project=data.url_project, url_rss=data.url_rss, url_zip=data.url_zip,
                sections=sections_json, totaltime_secs=data.totaltime_secs,
                gutenberg_id=data.gutenberg_id, last_synced_at=utc_now(),
            )
            self.db.add(new_book)
            return new_book

    async def sync_catalog(self, max_batches: int | None = None) -> dict[str, Any]:
        result = await self.db.execute(select(LibriVoxSyncStatus).limit(1))
        status = result.scalar_one_or_none()
        if not status:
            status = LibriVoxSyncStatus(total_audiobooks_synced=0, last_synced_offset=0, is_syncing=False)
            self.db.add(status)
            await self.db.flush()

        if status.is_syncing:
            raise LibriVoxServiceError("Sync already in progress")

        status.is_syncing = True
        status.sync_started_at = utc_now()
        status.sync_error = None
        await self.db.commit()

        client = await self._get_client()
        synced_count = 0

        try:
            async for batch in client.iter_all_audiobooks(max_batches=max_batches):
                for data in batch:
                    await self._upsert_audiobook(data)
                    synced_count += 1

                status.total_audiobooks_synced = synced_count
                await self.db.commit()

                if synced_count % 100 == 0:
                    logger.info(f"LibriVox sync progress: {synced_count} audiobooks synced")

            status.is_syncing = False
            status.last_sync_at = utc_now()
            await self.db.commit()

            # Auto-ingest into general catalog
            ingested = 0
            try:
                from .free_ebook_ingestion_service import FreeEbookIngestionService
                ingestion = FreeEbookIngestionService(self.db)
                ingested = await ingestion._ingest_librivox()
                await self.db.commit()
                logger.info(f"Auto-ingested {ingested} LibriVox audiobooks into catalog")
            except Exception as e:  # noqa: BLE001 -- auto-ingestion non-fatal: sync success not blocked by catalog ingest failure
                logger.warning(f"Auto-ingestion failed (non-fatal): {e}")

            return {"success": True, "audiobooks_synced": synced_count, "catalog_ingested": ingested}

        except Exception as e:
            logger.error(f"LibriVox sync failed: {e}")
            status.is_syncing = False
            status.sync_error = str(e)
            await self.db.commit()
            raise LibriVoxServiceError(f"Sync failed: {e}") from e

    async def get_statistics(self) -> LibriVoxStatsResponse:
        book_count = (await self.db.execute(select(func.count(LibriVoxAudiobook.id)))).scalar() or 0
        listen_count = (await self.db.execute(select(func.count(LibriVoxListen.id)))).scalar() or 0
        fav_count = (await self.db.execute(select(func.count(LibriVoxFavorite.id)))).scalar() or 0
        unique = (await self.db.execute(
            select(func.count(func.distinct(LibriVoxListen.user_id)))
        )).scalar() or 0

        popular_stmt = select(LibriVoxAudiobook).order_by(LibriVoxAudiobook.totaltime_secs.desc()).limit(10)
        popular_result = await self.db.execute(popular_stmt)
        popular = []
        for book in popular_result.scalars().all():
            authors = json.loads(book.authors) if book.authors else []
            primary_author = f"{authors[0].get('first_name', '')} {authors[0].get('last_name', '')}".strip() if authors else None
            popular.append(LibriVoxAudiobookSummary(
                id=book.id, librivox_id=book.librivox_id, title=book.title,
                primary_author=primary_author, language=book.language,
                total_time=book.total_time, num_sections=book.num_sections,
            ))

        return LibriVoxStatsResponse(
            total_audiobooks=book_count, total_listens=listen_count,
            total_favorites=fav_count, unique_listeners=unique, popular_audiobooks=popular,
        )
