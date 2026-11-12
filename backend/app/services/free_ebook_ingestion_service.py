# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.catalog import CatalogItem, CatalogingStatus, ItemStatus, ItemType
from ..models.feedbooks import FeedbooksBook
from ..models.gutenberg import GutenbergBook
from ..models.librivox import LibriVoxAudiobook
from ..models.manybooks import ManyBooksBook
from ..models.open_library import OpenLibraryBook
from ..models.standard_ebooks import StandardEbook
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class FreeEbookIngestionError(Exception):
    pass


# Source labels used for the CatalogItem.location field to indicate provenance
SOURCE_LOCATIONS = {
    "gutenberg": "Free Ebooks - Project Gutenberg",
    "open_library": "Free Ebooks - Open Library",
    "standard_ebooks": "Free Ebooks - Standard Ebooks",
    "librivox": "Free Audiobooks - LibriVox",
    "feedbooks": "Free Ebooks - Feedbooks",
    "manybooks": "Free Ebooks - ManyBooks",
}


class FreeEbookIngestionService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_all(self, *, limit_per_source: int | None = None) -> dict[str, Any]:
        results = {}
        for source, method in [
            ("gutenberg", self._ingest_gutenberg),
            ("open_library", self._ingest_open_library),
            ("standard_ebooks", self._ingest_standard_ebooks),
            ("librivox", self._ingest_librivox),
            ("feedbooks", self._ingest_feedbooks),
            ("manybooks", self._ingest_manybooks),
        ]:
            try:
                count = await method(limit=limit_per_source)
                results[source] = {"ingested": count, "status": "ok"}
                logger.info(f"Ingested {count} records from {source} into catalog")
            except Exception as e:  # noqa: BLE001 -- per-source boundary: one ingestion source failure must not block other sources
                logger.error(f"Failed to ingest {source}: {e}")
                results[source] = {"ingested": 0, "status": "error", "error": str(e)}

        await self.db.commit()
        return results

    async def ingest_source(self, source: str, *, limit: int | None = None) -> dict[str, Any]:
        method_map = {
            "gutenberg": self._ingest_gutenberg,
            "open_library": self._ingest_open_library,
            "standard_ebooks": self._ingest_standard_ebooks,
            "librivox": self._ingest_librivox,
            "feedbooks": self._ingest_feedbooks,
            "manybooks": self._ingest_manybooks,
        }
        method = method_map.get(source)
        if not method:
            raise FreeEbookIngestionError(f"Unknown source: {source}")

        count = await method(limit=limit)
        await self.db.commit()
        return {"source": source, "ingested": count}

    # -------------------------------------------------------------------------
    # Per-source ingestion methods
    # -------------------------------------------------------------------------

    async def _ingest_gutenberg(self, *, limit: int | None = None) -> int:
        stmt = (
            select(GutenbergBook)
            .where(GutenbergBook.catalog_item_id.is_(None))
            .order_by(GutenbergBook.download_count.desc())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        books = result.scalars().all()
        count = 0

        for book in books:
            # Parse authors from JSON
            authors_data = json.loads(book.authors) if book.authors else []
            author_name = authors_data[0].get("name") if authors_data else None

            # Parse subjects
            subjects_data = json.loads(book.subjects) if book.subjects else []
            subjects_str = "; ".join(subjects_data[:10]) if subjects_data else None

            # Build description
            bookshelves = json.loads(book.bookshelves) if book.bookshelves else []
            desc_parts = []
            if bookshelves:
                desc_parts.append(f"Bookshelves: {', '.join(bookshelves[:5])}")
            desc_parts.append(f"Project Gutenberg ID: {book.gutenberg_id}")
            if book.download_count:
                desc_parts.append(f"Downloads: {book.download_count:,}")

            catalog_item = CatalogItem(
                title=book.title[:500],
                author=author_name[:255] if author_name else None,
                item_type=ItemType.ebook,
                status=ItemStatus.available,
                description="\n".join(desc_parts) if desc_parts else None,
                subjects=subjects_str[:500] if subjects_str else None,
                cover_url=book.cover_url,
                location=SOURCE_LOCATIONS["gutenberg"],
                cataloging_status=CatalogingStatus.CATALOGED,
                cataloged_at=utc_now(),
            )
            self.db.add(catalog_item)
            await self.db.flush()

            book.catalog_item_id = catalog_item.id
            count += 1

            if count % 500 == 0:
                await self.db.flush()
                logger.info(f"Gutenberg ingestion progress: {count} records")

        return count

    async def _ingest_open_library(self, *, limit: int | None = None) -> int:
        stmt = (
            select(OpenLibraryBook)
            .where(OpenLibraryBook.catalog_item_id.is_(None))
            .order_by(OpenLibraryBook.edition_count.desc())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        books = result.scalars().all()
        count = 0

        for book in books:
            authors_data = json.loads(book.authors) if book.authors else []
            author_name = authors_data[0].get("name") if authors_data else None

            subjects_data = json.loads(book.subjects) if book.subjects else []
            subjects_str = "; ".join(subjects_data[:10]) if subjects_data else None

            desc_parts = [f"Open Library Work: {book.ol_work_id}"]
            if book.edition_count:
                desc_parts.append(f"Editions: {book.edition_count}")
            if book.has_fulltext:
                desc_parts.append("Full text available online")

            catalog_item = CatalogItem(
                title=book.title[:500],
                author=author_name[:255] if author_name else None,
                item_type=ItemType.ebook,
                status=ItemStatus.available,
                isbn=book.isbn_13 or book.isbn_10,
                publisher=book.publisher[:255] if book.publisher else None,
                publication_year=book.first_publish_year,
                description="\n".join(desc_parts),
                subjects=subjects_str[:500] if subjects_str else None,
                cover_url=book.cover_url,
                location=SOURCE_LOCATIONS["open_library"],
                cataloging_status=CatalogingStatus.CATALOGED,
                cataloged_at=utc_now(),
            )
            self.db.add(catalog_item)
            await self.db.flush()

            book.catalog_item_id = catalog_item.id
            count += 1

            if count % 500 == 0:
                await self.db.flush()

        return count

    async def _ingest_standard_ebooks(self, *, limit: int | None = None) -> int:
        stmt = (
            select(StandardEbook)
            .where(StandardEbook.catalog_item_id.is_(None))
            .order_by(StandardEbook.title.asc())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        books = result.scalars().all()
        count = 0

        for book in books:
            authors_data = json.loads(book.authors) if book.authors else []
            author_name = authors_data[0].get("name") if authors_data else None

            subjects_data = json.loads(book.subjects) if book.subjects else []
            subjects_str = "; ".join(subjects_data[:10]) if subjects_data else None

            description = book.description or ""
            if book.word_count:
                description += f"\nWord count: {book.word_count:,}"
            description += f"\nStandard Ebooks edition"

            catalog_item = CatalogItem(
                title=book.title[:500],
                author=author_name[:255] if author_name else None,
                item_type=ItemType.ebook,
                status=ItemStatus.available,
                publication_year=book.published_at.year if book.published_at else None,
                description=description.strip() or None,
                subjects=subjects_str[:500] if subjects_str else None,
                cover_url=book.cover_url,
                location=SOURCE_LOCATIONS["standard_ebooks"],
                cataloging_status=CatalogingStatus.CATALOGED,
                cataloged_at=utc_now(),
            )
            self.db.add(catalog_item)
            await self.db.flush()

            book.catalog_item_id = catalog_item.id
            count += 1

        return count

    async def _ingest_librivox(self, *, limit: int | None = None) -> int:
        stmt = (
            select(LibriVoxAudiobook)
            .where(LibriVoxAudiobook.catalog_item_id.is_(None))
            .order_by(LibriVoxAudiobook.title.asc())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        audiobooks = result.scalars().all()
        count = 0

        for audiobook in audiobooks:
            authors_data = json.loads(audiobook.authors) if audiobook.authors else []
            if authors_data:
                a = authors_data[0]
                author_name = f"{a.get('first_name', '')} {a.get('last_name', '')}".strip()
            else:
                author_name = None

            genres_data = json.loads(audiobook.genres) if audiobook.genres else []
            subjects_str = "; ".join(genres_data[:10]) if genres_data else None

            desc_parts = []
            if audiobook.description:
                desc_parts.append(audiobook.description[:500])
            if audiobook.total_time:
                desc_parts.append(f"Total time: {audiobook.total_time}")
            if audiobook.num_sections:
                desc_parts.append(f"Sections: {audiobook.num_sections}")
            desc_parts.append(f"LibriVox recording ({str(audiobook.book_type) if audiobook.book_type else 'solo'})")

            catalog_item = CatalogItem(
                title=audiobook.title[:500],
                author=author_name[:255] if author_name else None,
                item_type=ItemType.audiobook,
                status=ItemStatus.available,
                publication_year=audiobook.copyright_year,
                description="\n".join(desc_parts) if desc_parts else None,
                subjects=subjects_str[:500] if subjects_str else None,
                location=SOURCE_LOCATIONS["librivox"],
                cataloging_status=CatalogingStatus.CATALOGED,
                cataloged_at=utc_now(),
            )
            self.db.add(catalog_item)
            await self.db.flush()

            audiobook.catalog_item_id = catalog_item.id
            count += 1

        return count

    async def _ingest_feedbooks(self, *, limit: int | None = None) -> int:
        stmt = (
            select(FeedbooksBook)
            .where(FeedbooksBook.catalog_item_id.is_(None))
            .order_by(FeedbooksBook.title.asc())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        books = result.scalars().all()
        count = 0

        for book in books:
            authors_data = json.loads(book.authors) if book.authors else []
            author_name = authors_data[0].get("name") if authors_data else None

            categories_data = json.loads(book.categories) if book.categories else []
            subjects_str = "; ".join(categories_data[:10]) if categories_data else None

            description = book.summary or book.content or ""
            if book.rights:
                description += f"\nLicense: {book.rights}"

            catalog_item = CatalogItem(
                title=book.title[:500],
                author=author_name[:255] if author_name else None,
                item_type=ItemType.ebook,
                status=ItemStatus.available,
                publisher=book.publisher[:255] if book.publisher else None,
                publication_year=book.published_at.year if book.published_at else None,
                description=description.strip()[:2000] or None,
                subjects=subjects_str[:500] if subjects_str else None,
                cover_url=book.cover_url,
                location=SOURCE_LOCATIONS["feedbooks"],
                cataloging_status=CatalogingStatus.CATALOGED,
                cataloged_at=utc_now(),
            )
            self.db.add(catalog_item)
            await self.db.flush()

            book.catalog_item_id = catalog_item.id
            count += 1

        return count

    async def _ingest_manybooks(self, *, limit: int | None = None) -> int:
        stmt = (
            select(ManyBooksBook)
            .where(ManyBooksBook.catalog_item_id.is_(None))
            .order_by(ManyBooksBook.rating.desc().nullslast())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        books = result.scalars().all()
        count = 0

        for book in books:
            authors_data = json.loads(book.authors) if book.authors else []
            author_name = authors_data[0].get("name") if authors_data else None

            categories_data = json.loads(book.categories) if book.categories else []
            subjects_str = "; ".join(categories_data[:10]) if categories_data else None

            desc_parts = []
            if book.summary:
                desc_parts.append(book.summary[:500])
            if book.rating:
                desc_parts.append(f"Community rating: {book.rating:.1f}/5")
                if book.rating_count:
                    desc_parts.append(f"({book.rating_count} ratings)")

            catalog_item = CatalogItem(
                title=book.title[:500],
                author=author_name[:255] if author_name else None,
                item_type=ItemType.ebook,
                status=ItemStatus.available,
                publication_year=book.publication_year,
                description="\n".join(desc_parts) if desc_parts else None,
                subjects=subjects_str[:500] if subjects_str else None,
                cover_url=book.cover_url,
                location=SOURCE_LOCATIONS["manybooks"],
                cataloging_status=CatalogingStatus.CATALOGED,
                cataloged_at=utc_now(),
            )
            self.db.add(catalog_item)
            await self.db.flush()

            book.catalog_item_id = catalog_item.id
            count += 1

        return count

    # -------------------------------------------------------------------------
    # Summary / stats
    # -------------------------------------------------------------------------

    async def get_ingestion_summary(self) -> dict[str, Any]:
        summary = {}

        for source, model, id_col in [
            ("gutenberg", GutenbergBook, GutenbergBook.catalog_item_id),
            ("open_library", OpenLibraryBook, OpenLibraryBook.catalog_item_id),
            ("standard_ebooks", StandardEbook, StandardEbook.catalog_item_id),
            ("librivox", LibriVoxAudiobook, LibriVoxAudiobook.catalog_item_id),
            ("feedbooks", FeedbooksBook, FeedbooksBook.catalog_item_id),
            ("manybooks", ManyBooksBook, ManyBooksBook.catalog_item_id),
        ]:
            try:
                total_result = await self.db.execute(select(func.count(model.id)))
                total = total_result.scalar() or 0

                ingested_result = await self.db.execute(
                    select(func.count(model.id)).where(id_col.isnot(None))
                )
                ingested = ingested_result.scalar() or 0

                summary[source] = {
                    "total_cached": total,
                    "ingested_to_catalog": ingested,
                    "pending": total - ingested,
                }
            except SQLAlchemyError:
                summary[source] = {"total_cached": 0, "ingested_to_catalog": 0, "pending": 0}

        return summary
