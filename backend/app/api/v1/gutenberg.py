# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Project Gutenberg API endpoints.

Provides access to 70,000+ free public domain ebooks from Project Gutenberg.
"""

from app.core.logging import get_logger
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.gutenberg import GutenbergFormat
from ...models.user import User, UserRole
from ...schemas.gutenberg import (
    GutenbergBookDetail,
    GutenbergBookSummary,
    GutenbergDownloadCreate,
    GutenbergDownloadResponse,
    GutenbergFavoriteCreate,
    GutenbergFavoriteResponse,
    GutenbergFavoriteUpdate,
    GutenbergPatronDashboard,
    GutenbergSearchQuery,
    GutenbergSearchResponse,
    GutenbergStatsResponse,
    GutenbergSyncStatusResponse,
    GutenbergSyncTrigger,
)
from ...services.gutenberg_service import GutenbergService, GutenbergServiceError
from .auth import get_current_user, get_current_user_optional
from .dependencies import require_admin, require_staff, check_staff_access

logger = get_logger(__name__)

router = APIRouter(prefix="/gutenberg", tags=["gutenberg"])


# =============================================================================
# Search Endpoints
# =============================================================================


@router.get("/search", response_model=GutenbergSearchResponse)
async def search_books(
    q: str | None = Query(None, description="Search query"),
    author: str | None = Query(None, description="Filter by author"),
    title: str | None = Query(None, description="Filter by title"),
    topic: str | None = Query(None, description="Filter by subject/topic"),
    languages: str | None = Query(None, description="Comma-separated language codes (e.g., 'en,fr')"),
    page: int = Query(1, ge=1, description="Page number"),
    source: str = Query("api", description="Search source: 'api' (live) or 'local' (cached)"),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Search Project Gutenberg books.

    Use source='api' for real-time results from Gutendex API.
    Use source='local' for faster searches from cached catalog.
    """
    service = GutenbergService(db)

    try:
        lang_list = languages.split(",") if languages else None

        if source == "local":
            result = await service.search_local(
                query=q,
                author=author,
                languages=lang_list,
                page=page,
            )
        else:
            result = await service.search_api(
                query=q,
                author=author,
                title=title,
                topic=topic,
                languages=lang_list,
                page=page,
            )

        return result

    except GutenbergServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    finally:
        await service.close()


@router.post("/search", response_model=GutenbergSearchResponse)
async def search_books_post(  # noqa: role-check -- public Gutenberg search via POST
    search_query: GutenbergSearchQuery,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Search Project Gutenberg books (POST version for complex queries)."""
    service = GutenbergService(db)

    try:
        result = await service.search_api(
            query=search_query.query,
            author=search_query.author,
            title=search_query.title,
            topic=search_query.topic,
            languages=search_query.languages,
            page=search_query.page,
        )
        return result

    except GutenbergServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    finally:
        await service.close()


# =============================================================================
# Book Detail Endpoints
# =============================================================================


@router.get("/books/{book_id}", response_model=GutenbergBookDetail)
async def get_book(
    book_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get book details by local database ID."""
    service = GutenbergService(db)

    try:
        book = await service.get_book(book_id, user=current_user)

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        return book

    finally:
        await service.close()


@router.get("/books/gutenberg/{gutenberg_id}", response_model=GutenbergBookDetail)
async def get_book_by_gutenberg_id(
    gutenberg_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get book details by Project Gutenberg ID.

    Will fetch from API if not already cached locally.
    """
    service = GutenbergService(db)

    try:
        book = await service.get_book_by_gutenberg_id(
            gutenberg_id,
            user=current_user,
            fetch_if_missing=True,
        )

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        return book

    except GutenbergServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    finally:
        await service.close()


# =============================================================================
# Popular/Featured Endpoints
# =============================================================================


@router.get("/popular", response_model=List[GutenbergBookSummary])
async def get_popular_books(
    languages: str | None = Query(None, description="Comma-separated language codes"),
    limit: int = Query(20, ge=1, le=100, description="Number of books to return"),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get popular books from the catalog."""
    service = GutenbergService(db)

    try:
        lang_list = languages.split(",") if languages else None
        books = await service.get_popular_books(languages=lang_list, limit=limit)
        return books

    finally:
        await service.close()


# =============================================================================
# Download Tracking Endpoints
# =============================================================================


@router.post("/downloads", response_model=GutenbergDownloadResponse, status_code=status.HTTP_201_CREATED)
async def record_download(
    download: GutenbergDownloadCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a download (for analytics and recommendations)."""
    service = GutenbergService(db)

    try:
        result = await service.record_download(
            user=current_user,
            book_id=download.book_id,
            format=download.format,
        )
        await db.commit()
        return result

    except GutenbergServiceError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    finally:
        await service.close()


@router.get("/downloads", response_model=List[GutenbergDownloadResponse])
async def get_my_downloads(
    limit: int = Query(50, ge=1, le=200, description="Number of downloads to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's download history."""
    service = GutenbergService(db)

    try:
        downloads = await service.get_user_downloads(current_user.id, limit=limit)
        return downloads

    finally:
        await service.close()


@router.get("/downloads/user/{user_id}", response_model=List[GutenbergDownloadResponse])
async def get_user_downloads(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a user's download history. Users can view their own, staff can view any user's."""
    if current_user.id != user_id:
        check_staff_access(current_user)

    service = GutenbergService(db)

    try:
        downloads = await service.get_user_downloads(user_id, limit=limit)
        return downloads

    finally:
        await service.close()


# =============================================================================
# Favorites Endpoints
# =============================================================================


@router.post("/favorites", response_model=GutenbergFavoriteResponse, status_code=status.HTTP_201_CREATED)
async def add_favorite(
    favorite: GutenbergFavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a book to favorites."""
    service = GutenbergService(db)

    try:
        result = await service.add_favorite(
            user=current_user,
            book_id=favorite.book_id,
            notes=favorite.notes,
        )
        await db.commit()
        return result

    except GutenbergServiceError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    finally:
        await service.close()


@router.delete("/favorites/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a book from favorites."""
    service = GutenbergService(db)

    try:
        removed = await service.remove_favorite(current_user, book_id)
        await db.commit()

        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Favorite not found",
            )

        return None

    finally:
        await service.close()


@router.get("/favorites", response_model=List[GutenbergFavoriteResponse])
async def get_my_favorites(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's favorite books."""
    service = GutenbergService(db)

    try:
        favorites = await service.get_user_favorites(current_user.id, limit=limit)
        return favorites

    finally:
        await service.close()


# =============================================================================
# Dashboard Endpoint
# =============================================================================


@router.get("/dashboard", response_model=GutenbergPatronDashboard)
async def get_patron_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get patron's Gutenberg dashboard with downloads, favorites, and recommendations."""
    service = GutenbergService(db)

    try:
        dashboard = await service.get_patron_dashboard(current_user)
        return dashboard

    finally:
        await service.close()


# =============================================================================
# Admin/Staff Endpoints
# =============================================================================


@router.get("/stats", response_model=GutenbergStatsResponse)
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get Gutenberg usage statistics. Staff and above."""
    await require_staff(current_user)

    service = GutenbergService(db)

    try:
        stats = await service.get_statistics()
        return stats

    finally:
        await service.close()


@router.get("/sync/status", response_model=GutenbergSyncStatusResponse | None)
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get catalog sync status. Staff and above."""
    await require_staff(current_user)

    service = GutenbergService(db)

    try:
        status = await service.get_sync_status()
        return status

    finally:
        await service.close()


@router.post("/sync")
async def trigger_sync(
    sync_options: GutenbergSyncTrigger,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger catalog sync from Gutenberg API. Admin only.

    This can take a long time for full syncs (70,000+ books).
    Consider using max_pages for testing or incremental syncs.
    """
    await require_admin(current_user)

    service = GutenbergService(db)

    try:
        result = await service.sync_catalog(
            full_sync=sync_options.full_sync,
            max_pages=sync_options.max_pages,
            languages=sync_options.languages,
        )
        return {
            "ok": True,
            "message": "Sync completed successfully",
            "triggered_by": current_user.email,
            **result,
        }

    except GutenbergServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    finally:
        await service.close()



