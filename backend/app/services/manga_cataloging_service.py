# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from typing import Optional

import httpx
from sqlalchemy import and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.catalog import CatalogItem, ItemType
from ..models.manga_cataloging import MangaCatalogingTemplate, MangaVolumeRecord
from ..models.series_management import SeriesReadingOrder, SeriesType
from ..schemas.manga_cataloging import QuickAddMangaVolumeRequest

logger = get_logger(__name__)


class MangaCatalogingService:

    # Open Library and Google Books API endpoints for cover fetching
    OPEN_LIBRARY_API = "https://openlibrary.org/api"
    GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

    @staticmethod
    async def get_or_create_template(
        db: AsyncSession,
        series_title: str,
        author: Optional[str] = None,
        publisher: Optional[str] = None,
    ) -> MangaCatalogingTemplate:
        # Try to find existing template
        result = await db.execute(
            select(MangaCatalogingTemplate).where(
                MangaCatalogingTemplate.series_title == series_title
            )
        )
        template = result.scalar_one_or_none()

        if template:
            return template

        # Create default template
        template = MangaCatalogingTemplate(
            name=f"{series_title} - Default Template",
            series_title=series_title,
            author=author,
            publisher=publisher,
            description=f"Auto-generated template for {series_title}",
            is_shared=True,
            default_fields={
                "location": "Manga Section",
                "dewey_decimal": "741.5952",
                "lc_classification": "PN1997.2",
            },
        )
        db.add(template)
        await db.flush()
        return template

    @staticmethod
    async def fetch_cover_from_isbn(isbn: str) -> Optional[str]:
        if not isbn:
            return None

        # Try Open Library first
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Open Library ISBN API
                response = await client.get(
                    f"https://openlibrary.org/isbn/{isbn}.json"
                )
                if response.status_code == 200:
                    data = response.json()
                    if "covers" in data and data["covers"]:
                        cover_id = data["covers"][0]
                        return f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
        except (httpx.HTTPError, asyncio.TimeoutError, ValueError) as e:
            logger.warning(f"Failed to fetch cover from Open Library for ISBN {isbn}: {e}")

        # Try Google Books as fallback
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://www.googleapis.com/books/v1/volumes",
                    params={"q": f"isbn:{isbn}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    if "items" in data and data["items"]:
                        volume_info = data["items"][0].get("volumeInfo", {})
                        image_links = volume_info.get("imageLinks", {})
                        if "thumbnail" in image_links:
                            return image_links["thumbnail"]
        except (httpx.HTTPError, asyncio.TimeoutError, ValueError) as e:
            logger.warning(f"Failed to fetch cover from Google Books for ISBN {isbn}: {e}")

        return None

    @staticmethod
    async def lookup_isbn_metadata(isbn: str) -> dict:
        if not isbn:
            return {"isbn": isbn, "found": False, "source": None}

        metadata: dict = {"isbn": isbn, "found": False, "source": None}

        # Try Open Library first
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"https://openlibrary.org/isbn/{isbn}.json"
                )
                if response.status_code == 200:
                    data = response.json()
                    metadata["found"] = True
                    metadata["source"] = "open_library"
                    metadata["title"] = data.get("title")
                    metadata["page_count"] = data.get("number_of_pages")
                    metadata["publish_date"] = data.get("publish_date")

                    # Get publishers from array
                    publishers = data.get("publishers", [])
                    if publishers:
                        metadata["publisher"] = publishers[0]

                    # Cover image
                    if "covers" in data and data["covers"]:
                        cover_id = data["covers"][0]
                        metadata["cover_url"] = (
                            f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
                        )

                    # Get author info via works key
                    authors = data.get("authors", [])
                    if authors:
                        author_key = authors[0].get("key", "")
                        if author_key:
                            author_resp = await client.get(
                                f"https://openlibrary.org{author_key}.json"
                            )
                            if author_resp.status_code == 200:
                                author_data = author_resp.json()
                                metadata["author"] = author_data.get("name")

                    return metadata
        except (httpx.HTTPError, asyncio.TimeoutError, ValueError) as e:
            logger.warning(
                f"Failed to fetch metadata from Open Library for ISBN {isbn}: {e}"
            )

        # Try Google Books as fallback
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://www.googleapis.com/books/v1/volumes",
                    params={"q": f"isbn:{isbn}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    if "items" in data and data["items"]:
                        vol = data["items"][0].get("volumeInfo", {})
                        metadata["found"] = True
                        metadata["source"] = "google_books"
                        metadata["title"] = vol.get("title")
                        metadata["author"] = (
                            ", ".join(vol.get("authors", []))
                            if vol.get("authors")
                            else None
                        )
                        metadata["publisher"] = vol.get("publisher")
                        metadata["publish_date"] = vol.get("publishedDate")
                        metadata["page_count"] = vol.get("pageCount")
                        metadata["description"] = vol.get("description")
                        metadata["language"] = vol.get("language")

                        # Categories / subjects
                        categories = vol.get("categories", [])
                        if categories:
                            metadata["subjects"] = ", ".join(categories)

                        # Cover image
                        image_links = vol.get("imageLinks", {})
                        if "thumbnail" in image_links:
                            metadata["cover_url"] = image_links["thumbnail"]

                        return metadata
        except (httpx.HTTPError, asyncio.TimeoutError, ValueError) as e:
            logger.warning(
                f"Failed to fetch metadata from Google Books for ISBN {isbn}: {e}"
            )

        return metadata

    @staticmethod
    async def get_next_volume_number(
        db: AsyncSession, series_title: str
    ) -> int:
        result = await db.execute(
            select(func.max(MangaVolumeRecord.volume_number)).where(
                MangaVolumeRecord.series_title == series_title
            )
        )
        max_volume = result.scalar()
        return (max_volume or 0) + 1

    @staticmethod
    async def get_series_info_from_previous_volumes(
        db: AsyncSession, series_title: str
    ) -> dict:
        result = await db.execute(
            select(MangaVolumeRecord)
            .where(MangaVolumeRecord.series_title == series_title)
            .order_by(MangaVolumeRecord.volume_number.desc())
            .limit(1)
        )
        previous_volume = result.scalar_one_or_none()

        if not previous_volume:
            return {}

        # Extract common fields from previous volume
        series_info = {
            "publisher": previous_volume.publisher,
            "original_language": previous_volume.original_language,
            "is_color": previous_volume.is_color,
        }

        # Get template if exists
        result_template = await db.execute(
            select(MangaCatalogingTemplate).where(
                MangaCatalogingTemplate.series_title == series_title
            )
        )
        template = result_template.scalar_one_or_none()

        if template:
            series_info.update(
                {
                    "publisher": template.publisher or series_info.get("publisher"),
                    "location": template.default_fields.get("location", "Manga Section"),
                    "dewey_decimal": template.default_fields.get("dewey_decimal"),
                    "lc_classification": template.default_fields.get(
                        "lc_classification"
                    ),
                    "genre": template.genre,
                    "subjects": template.subjects,
                }
            )

        return series_info

    @staticmethod
    async def quick_add_manga_volume(
        db: AsyncSession,
        request: QuickAddMangaVolumeRequest,
        cataloger_user_id: int,
    ) -> dict:

        # Get or create template
        template = None
        if request.template_id:
            result = await db.execute(
                select(MangaCatalogingTemplate).where(
                    MangaCatalogingTemplate.id == request.template_id
                )
            )
            template = result.scalar_one_or_none()

        if not template:
            template = await MangaCatalogingService.get_or_create_template(
                db, request.series_title, request.author
            )

        # Get series info from previous volumes
        series_info = await MangaCatalogingService.get_series_info_from_previous_volumes(
            db, request.series_title
        )

        # Copy from previous volume if requested
        copied_fields = {}
        if request.copy_from_volume_id:
            result = await db.execute(
                select(MangaVolumeRecord).where(
                    MangaVolumeRecord.id == request.copy_from_volume_id
                )
            )
            source_volume = result.scalar_one_or_none()
            if source_volume:
                copied_fields = {
                    "publisher": source_volume.publisher,
                    "original_language": source_volume.original_language,
                    "page_count": source_volume.page_count,
                    "is_color": source_volume.is_color,
                }

        # Create new catalog item
        catalog_item = CatalogItem(
            title=request.title,
            author=request.author or template.author,
            item_type=ItemType.book,
            isbn=request.isbn,
            publisher=request.publisher
            or copied_fields.get("publisher")
            or template.publisher,
            subjects=template.subjects,
            # Custom genre field - store as string
            location=series_info.get("location", "Manga Section"),
            dewey_decimal=series_info.get("dewey_decimal"),
            lc_classification=series_info.get("lc_classification"),
        )

        # Add genre as part of description for now (can be extended)
        catalog_item.description = f"Series: {request.series_title}, Volume: {request.volume_number}\nGenre: {template.genre}"

        db.add(catalog_item)
        await db.flush()

        # Fetch cover image if enabled
        cover_url = None
        if request.auto_fetch_cover and request.isbn:
            cover_url = await MangaCatalogingService.fetch_cover_from_isbn(
                request.isbn
            )
            if cover_url:
                catalog_item.cover_url = cover_url

        # Create volume record
        volume_record = MangaVolumeRecord(
            catalog_item_id=catalog_item.id,
            series_title=request.series_title,
            volume_number=request.volume_number,
            template_id=template.id,
            isbn=request.isbn,
            publisher=request.publisher or template.publisher,
            original_language=request.original_language or template.original_language or copied_fields.get("original_language"),
            cover_image_url=cover_url,
            cover_fetch_source="open_library" if cover_url else None,
        )
        db.add(volume_record)
        await db.flush()

        # Add to series reading order if it doesn't exist
        result = await db.execute(
            select(SeriesReadingOrder).where(
                and_(
                    SeriesReadingOrder.series_title == request.series_title,
                    SeriesReadingOrder.sequence_number == request.volume_number,
                )
            )
        )
        existing_order = result.scalar_one_or_none()

        if not existing_order:
            series_order = SeriesReadingOrder(
                series_title=request.series_title,
                series_type=SeriesType.graphic_novel_series,
                sequence_number=request.volume_number,
                book_title=request.title,
                publication_year=(
                    int(request.publication_date.split("-")[0])
                    if request.publication_date
                    else None
                ),
            )
            db.add(series_order)

        # Sync the new catalog row into the BIBFRAME linked-data graph.
        # Previously manga volumes committed without this call, which
        # silently broke the documented 1:1 catalog<->BIBFRAME invariant
        # for an entire content type (manga volumes were invisible to
        # OPDS, RDF exports, and federated discovery).
        try:
            from .catalog_bibframe_sync import CatalogBibframeSync
            await CatalogBibframeSync.create_from_catalog(db, catalog_item)
        except SQLAlchemyError as exc:
            import logging
            get_logger(__name__).warning(
                "BIBFRAME sync failed for manga catalog_item %s: %s",
                catalog_item.id, exc, exc_info=True,
            )

        await db.commit()

        return {
            "catalog_item_id": catalog_item.id,
            "volume_record_id": volume_record.id,
            "series_title": request.series_title,
            "volume_number": request.volume_number,
            "title": request.title,
            "cover_url": cover_url,
            "status": "created",
        }

    @staticmethod
    async def copy_and_increment_volume(
        db: AsyncSession,
        source_volume_id: int,
        new_volume_number: int,
        new_isbn: Optional[str] = None,
    ) -> dict:

        # Get source volume
        result = await db.execute(
            select(MangaVolumeRecord).where(MangaVolumeRecord.id == source_volume_id)
        )
        source_volume = result.scalar_one_or_none()
        if not source_volume:
            raise ValueError(f"Source volume {source_volume_id} not found")

        # Get source catalog item
        result_item = await db.execute(
            select(CatalogItem).where(CatalogItem.id == source_volume.catalog_item_id)
        )
        source_item = result_item.scalar_one_or_none()
        if not source_item:
            raise ValueError("Source catalog item not found")

        # Create new catalog item (copy)
        new_catalog_item = CatalogItem(
            title=source_item.title.replace(f"Vol. {source_volume.volume_number}", f"Vol. {new_volume_number}") if f"Vol. {source_volume.volume_number}" in source_item.title else f"{source_item.title} - Vol. {new_volume_number}",
            author=source_item.author,
            item_type=source_item.item_type,
            isbn=new_isbn,
            publisher=source_item.publisher,
            subjects=source_item.subjects,
            location=source_item.location,
            dewey_decimal=source_item.dewey_decimal,
            lc_classification=source_item.lc_classification,
            description=source_item.description,
            page_count=source_item.page_count,
        )

        db.add(new_catalog_item)
        await db.flush()

        # Create new volume record
        cover_url = None
        if new_isbn:
            cover_url = await MangaCatalogingService.fetch_cover_from_isbn(new_isbn)

        new_volume_record = MangaVolumeRecord(
            catalog_item_id=new_catalog_item.id,
            series_title=source_volume.series_title,
            volume_number=new_volume_number,
            template_id=source_volume.template_id,
            volume_title=source_volume.volume_title,
            isbn=new_isbn or source_volume.isbn,
            publisher=source_volume.publisher,
            original_language=source_volume.original_language,
            page_count=source_volume.page_count,
            is_color=source_volume.is_color,
            previous_volume_id=source_volume_id,
            cover_image_url=cover_url,
            cover_fetch_source="open_library" if cover_url else None,
        )

        db.add(new_volume_record)
        await db.flush()

        # Update series reading order
        result = await db.execute(
            select(SeriesReadingOrder).where(
                SeriesReadingOrder.series_title == source_volume.series_title
            )
        )
        series_order = result.scalar_one_or_none()

        if series_order:
            # Add new sequence entry
            new_order = SeriesReadingOrder(
                series_title=source_volume.series_title,
                series_type=series_order.series_type,
                sequence_number=new_volume_number,
                book_title=new_catalog_item.title,
                publication_year=source_volume.publication_date.year
                if source_volume.publication_date
                else None,
            )
            db.add(new_order)

        await db.commit()

        return {
            "source_volume_id": source_volume_id,
            "new_volume_record_id": new_volume_record.id,
            "new_catalog_item_id": new_catalog_item.id,
            "series_title": source_volume.series_title,
            "volume_number": new_volume_number,
            "cover_url": cover_url,
            "status": "created",
        }

    @staticmethod
    async def batch_create_manga_volumes(
        db: AsyncSession,
        series_title: str,
        volumes: list[dict],
        template_id: Optional[int] = None,
    ) -> dict:

        # Get or create template
        template = None
        if template_id:
            result = await db.execute(
                select(MangaCatalogingTemplate).where(
                    MangaCatalogingTemplate.id == template_id
                )
            )
            template = result.scalar_one_or_none()

        if not template:
            template = await MangaCatalogingService.get_or_create_template(
                db, series_title
            )

        results = []
        failed = []

        for vol_data in volumes:
            try:
                request = QuickAddMangaVolumeRequest(
                    series_title=series_title,
                    volume_number=vol_data.get("volume_number"),
                    title=vol_data.get("title"),
                    author=vol_data.get("author"),
                    isbn=vol_data.get("isbn"),
                    publisher=vol_data.get("publisher"),
                    publication_date=vol_data.get("publication_date"),
                    template_id=template.id,
                    auto_fetch_cover=True,
                )

                result = await MangaCatalogingService.quick_add_manga_volume(
                    db, request, cataloger_user_id=None
                )
                results.append(result)
            except Exception as e:  # noqa: BLE001 - per-item boundary: bulk volume import must continue past individual failures
                logger.error(f"Failed to create volume {vol_data}: {e}")
                failed.append({"volume": vol_data, "error": str(e)})

        return {
            "series_title": series_title,
            "total_volumes": len(volumes),
            "created": len(results),
            "failed": len(failed),
            "results": results,
            "errors": failed,
        }
