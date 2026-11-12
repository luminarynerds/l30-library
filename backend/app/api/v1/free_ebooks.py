# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unified Free Ebooks catalog endpoint.

Provides a single entry point to search across all free ebook sources:
- Project Gutenberg (70,000+ public domain ebooks)
- Open Library / Internet Archive (millions of free reads)
- Standard Ebooks (~900 beautifully formatted classics)
- LibriVox (18,000+ public domain audiobooks)
- Feedbooks (10,000+ public domain ebooks)
- ManyBooks (50,000+ curated free ebooks)
"""

import contextlib
from app.core.logging import get_logger
from enum import StrEnum as PyEnum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from .auth import get_current_user, get_current_user_optional
from .dependencies import require_admin, require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/free-ebooks", tags=["free-ebooks"])


class FreeEbookSource(PyEnum):
    GUTENBERG = "gutenberg"
    OPEN_LIBRARY = "open_library"
    STANDARD_EBOOKS = "standard_ebooks"
    LIBRIVOX = "librivox"
    FEEDBOOKS = "feedbooks"
    MANYBOOKS = "manybooks"
    ALL = "all"


class UnifiedBookResult(BaseModel):
    source: str
    source_id: str  # Source-specific identifier
    title: str
    author: str | None = None
    cover_url: str | None = None
    language: str | None = None
    media_type: str = "ebook"  # ebook, audiobook
    detail_url: str  # API URL for full details
    formats: list[str] = []  # Available formats


class UnifiedSearchResponse(BaseModel):
    query: str | None
    total_results: int
    sources_searched: list[str]
    sources_failed: list[str] = []
    results: list[UnifiedBookResult]


class FreeEbooksOverview(BaseModel):
    sources: list[dict]
    total_cached_books: int
    total_cached_audiobooks: int


class IngestionRequest(BaseModel):
    sources: str = "all"  # Comma-separated source names or "all"
    limit_per_source: int | None = None  # Max records to ingest per source


class IngestionResponse(BaseModel):
    ok: bool
    message: str
    results: dict


@router.get("/search", response_model=UnifiedSearchResponse)
async def unified_search(
    q: str = Query(..., min_length=1, description="Search query"),
    sources: str = Query("all", description="Comma-separated sources or 'all'"),
    page: int = Query(1, ge=1),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Search across all free ebook sources simultaneously.

    Sources: gutenberg, open_library, standard_ebooks, librivox, feedbooks, manybooks, all
    """
    # Determine which sources to search
    if sources == "all":
        active_sources = [s for s in FreeEbookSource if s != FreeEbookSource.ALL]
    else:
        active_sources = []
        for s in sources.split(","):
            s = s.strip()
            # Silently drop unknown source identifiers from the query string.
            with contextlib.suppress(ValueError):
                active_sources.append(FreeEbookSource(s))

    results: list[UnifiedBookResult] = []
    sources_searched: list[str] = []
    sources_failed: list[str] = []

    # Search each source
    for source in active_sources:
        try:
            source_results = await _search_source(source, q, page, db)
            results.extend(source_results)
            sources_searched.append(source.value)
        except Exception as e:  # noqa: BLE001  # per-source search — record failure and continue
            logger.warning(f"Failed to search {source.value}: {e}")
            sources_failed.append(source.value)

    return UnifiedSearchResponse(
        query=q,
        total_results=len(results),
        sources_searched=sources_searched,
        sources_failed=sources_failed,
        results=results,
    )


async def _search_source(
    source: FreeEbookSource,
    query: str,
    page: int,
    db: AsyncSession,
) -> list[UnifiedBookResult]:
    results: list[UnifiedBookResult] = []

    if source == FreeEbookSource.GUTENBERG:
        from ...services.gutenberg_service import GutenbergService
        service = GutenbergService(db)
        try:
            search_result = await service.search_local(query=query, page=page)
            for book in search_result.books:
                results.append(UnifiedBookResult(
                    source="gutenberg",
                    source_id=str(book.gutenberg_id),
                    title=book.title,
                    author=book.primary_author,
                    cover_url=book.cover_url,
                    language=book.languages,
                    detail_url=f"/api/v1/gutenberg/books/{book.id}",
                    formats=["epub", "kindle", "html", "txt", "pdf"],
                ))
        finally:
            await service.close()

    elif source == FreeEbookSource.OPEN_LIBRARY:
        from ...services.open_library_service import OpenLibraryService
        service = OpenLibraryService(db)
        try:
            search_result = await service.search_local(query=query, page=page)
            for book in search_result.books:
                results.append(UnifiedBookResult(
                    source="open_library",
                    source_id=book.ol_work_id,
                    title=book.title,
                    author=book.primary_author,
                    cover_url=book.cover_url,
                    language=book.languages,
                    detail_url=f"/api/v1/open-library/books/{book.id}",
                    formats=["read_online", "epub", "pdf"],
                ))
        finally:
            await service.close()

    elif source == FreeEbookSource.STANDARD_EBOOKS:
        from ...services.standard_ebooks_service import StandardEbooksService
        service = StandardEbooksService(db)
        try:
            search_result = await service.search_local(query=query, page=page)
            for book in search_result.books:
                results.append(UnifiedBookResult(
                    source="standard_ebooks",
                    source_id=book.se_identifier,
                    title=book.title,
                    author=book.primary_author,
                    cover_url=book.cover_url,
                    language=book.language,
                    detail_url=f"/api/v1/standard-ebooks/books/{book.id}",
                    formats=["epub", "azw3", "kepub"],
                ))
        finally:
            await service.close()

    elif source == FreeEbookSource.LIBRIVOX:
        from ...services.librivox_service import LibriVoxService
        service = LibriVoxService(db)
        try:
            search_result = await service.search_local(query=query, page=page)
            for book in search_result.books:
                results.append(UnifiedBookResult(
                    source="librivox",
                    source_id=str(book.librivox_id),
                    title=book.title,
                    author=book.primary_author,
                    language=book.language,
                    media_type="audiobook",
                    detail_url=f"/api/v1/librivox/audiobooks/{book.id}",
                    formats=["mp3", "ogg"],
                ))
        finally:
            await service.close()

    elif source == FreeEbookSource.FEEDBOOKS:
        from ...services.feedbooks_service import FeedbooksService
        service = FeedbooksService(db)
        try:
            search_result = await service.search_local(query=query, page=page)
            for book in search_result.books:
                results.append(UnifiedBookResult(
                    source="feedbooks",
                    source_id=book.feedbooks_id,
                    title=book.title,
                    author=book.primary_author,
                    cover_url=book.cover_url,
                    language=book.language,
                    detail_url=f"/api/v1/feedbooks/books/{book.id}",
                    formats=["epub", "mobi", "pdf"],
                ))
        finally:
            await service.close()

    elif source == FreeEbookSource.MANYBOOKS:
        from ...services.manybooks_service import ManyBooksService
        service = ManyBooksService(db)
        try:
            search_result = await service.search_local(query=query, page=page)
            for book in search_result.books:
                results.append(UnifiedBookResult(
                    source="manybooks",
                    source_id=book.manybooks_id,
                    title=book.title,
                    author=book.primary_author,
                    cover_url=book.cover_url,
                    language=book.language,
                    detail_url=f"/api/v1/manybooks/books/{book.id}",
                    formats=["epub", "mobi", "pdf"],
                ))
        finally:
            await service.close()

    return results


@router.get("/overview", response_model=FreeEbooksOverview)
async def get_overview(
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get an overview of all available free ebook sources and their catalog sizes."""
    from sqlalchemy import func, select
    from ...models.gutenberg import GutenbergBook
    from ...models.open_library import OpenLibraryBook
    from ...models.standard_ebooks import StandardEbook
    from ...models.librivox import LibriVoxAudiobook
    from ...models.feedbooks import FeedbooksBook
    from ...models.manybooks import ManyBooksBook

    counts = {}
    for model, name in [
        (GutenbergBook, "gutenberg"),
        (OpenLibraryBook, "open_library"),
        (StandardEbook, "standard_ebooks"),
        (LibriVoxAudiobook, "librivox"),
        (FeedbooksBook, "feedbooks"),
        (ManyBooksBook, "manybooks"),
    ]:
        try:
            result = await db.execute(select(func.count(model.id)))
            counts[name] = result.scalar() or 0
        except Exception:  # noqa: BLE001  # per-model count — fall back to 0
            counts[name] = 0

    sources = [
        {
            "name": "Project Gutenberg",
            "key": "gutenberg",
            "description": "70,000+ public domain ebooks via Gutendex API",
            "cached_count": counts.get("gutenberg", 0),
            "media_type": "ebook",
            "api_prefix": "/api/v1/gutenberg",
        },
        {
            "name": "Open Library",
            "key": "open_library",
            "description": "Millions of free ebooks from the Internet Archive",
            "cached_count": counts.get("open_library", 0),
            "media_type": "ebook",
            "api_prefix": "/api/v1/open-library",
        },
        {
            "name": "Standard Ebooks",
            "key": "standard_ebooks",
            "description": "~900 beautifully formatted public domain classics",
            "cached_count": counts.get("standard_ebooks", 0),
            "media_type": "ebook",
            "api_prefix": "/api/v1/standard-ebooks",
        },
        {
            "name": "LibriVox",
            "key": "librivox",
            "description": "18,000+ free public domain audiobooks",
            "cached_count": counts.get("librivox", 0),
            "media_type": "audiobook",
            "api_prefix": "/api/v1/librivox",
        },
        {
            "name": "Feedbooks",
            "key": "feedbooks",
            "description": "10,000+ public domain ebooks via OPDS catalog",
            "cached_count": counts.get("feedbooks", 0),
            "media_type": "ebook",
            "api_prefix": "/api/v1/feedbooks",
        },
        {
            "name": "ManyBooks",
            "key": "manybooks",
            "description": "50,000+ curated free ebooks with community ratings",
            "cached_count": counts.get("manybooks", 0),
            "media_type": "ebook",
            "api_prefix": "/api/v1/manybooks",
        },
    ]

    ebook_count = sum(
        counts.get(k, 0) for k in ["gutenberg", "open_library", "standard_ebooks", "feedbooks", "manybooks"]
    )
    audiobook_count = counts.get("librivox", 0)

    return FreeEbooksOverview(
        sources=sources,
        total_cached_books=ebook_count,
        total_cached_audiobooks=audiobook_count,
    )


# =========================================================================
# Catalog Ingestion - push free ebook records into the general catalog
# =========================================================================


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_to_catalog(
    request: IngestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest cached free ebook records into the general catalog.

    This creates CatalogItem records for each free ebook source so that
    the books appear in the main catalog search alongside physical holdings.

    Records that have already been ingested are skipped (idempotent).
    Admin only.
    """
    await require_admin(current_user)

    from ...services.free_ebook_ingestion_service import (
        FreeEbookIngestionService,
        FreeEbookIngestionError,
    )

    service = FreeEbookIngestionService(db)

    try:
        if request.sources == "all":
            results = await service.ingest_all(limit_per_source=request.limit_per_source)
        else:
            results = {}
            for source_name in request.sources.split(","):
                source_name = source_name.strip()
                if source_name:
                    try:
                        result = await service.ingest_source(
                            source_name, limit=request.limit_per_source
                        )
                        results[source_name] = {"ingested": result["ingested"], "status": "ok"}
                    except FreeEbookIngestionError as e:
                        results[source_name] = {"ingested": 0, "status": "error", "error": str(e)}

        total_ingested = sum(r.get("ingested", 0) for r in results.values())

        return IngestionResponse(
            ok=True,
            message=f"Ingested {total_ingested} records into the general catalog",
            results=results,
        )
    except Exception as e:
        logger.error("Ingestion failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ebook ingestion failed",
        ) from e


@router.get("/ingestion-status")
async def get_ingestion_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the ingestion status showing how many records from each source
    have been added to the general catalog vs how many are still pending.
    Staff and above.
    """
    await require_staff(current_user)

    from ...services.free_ebook_ingestion_service import FreeEbookIngestionService

    service = FreeEbookIngestionService(db)
    summary = await service.get_ingestion_summary()

    total_cached = sum(s["total_cached"] for s in summary.values())
    total_ingested = sum(s["ingested_to_catalog"] for s in summary.values())
    total_pending = sum(s["pending"] for s in summary.values())

    return {
        "sources": summary,
        "total_cached": total_cached,
        "total_ingested_to_catalog": total_ingested,
        "total_pending": total_pending,
    }
