# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Open Library API endpoints.

Provides access to millions of free ebooks from Open Library / Internet Archive.
"""

from app.core.logging import get_logger
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.open_library import (
    OpenLibraryBookDetail,
    OpenLibraryBookSummary,
    OpenLibraryDownloadCreate,
    OpenLibraryDownloadResponse,
    OpenLibraryFavoriteCreate,
    OpenLibraryFavoriteResponse,
    OpenLibrarySearchResponse,
    OpenLibraryStatsResponse,
    OpenLibrarySyncStatusResponse,
    OpenLibrarySyncTrigger,
)
from ...services.open_library_service import OpenLibraryService, OpenLibraryServiceError
from .auth import get_current_user, get_current_user_optional
from .dependencies import require_admin, require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/open-library", tags=["open-library"])


@router.get("/search", response_model=OpenLibrarySearchResponse)
async def search_books(
    q: str | None = Query(None, description="Search query"),
    author: str | None = Query(None, description="Filter by author"),
    title: str | None = Query(None, description="Filter by title"),
    subject: str | None = Query(None, description="Filter by subject"),
    languages: str | None = Query(None, description="Comma-separated language codes"),
    page: int = Query(1, ge=1),
    source: str = Query("api", description="'api' (live) or 'local' (cached)"),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Search Open Library books."""
    service = OpenLibraryService(db)
    try:
        lang_list = languages.split(",") if languages else None
        if source == "local":
            return await service.search_local(query=q, author=author, languages=lang_list, page=page)
        else:
            return await service.search_api(
                query=q, author=author, title=title, subject=subject,
                languages=lang_list, page=page,
            )
    except OpenLibraryServiceError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    finally:
        await service.close()


@router.get("/books/{book_id}", response_model=OpenLibraryBookDetail)
async def get_book(
    book_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get book details by local database ID."""
    service = OpenLibraryService(db)
    try:
        book = await service.get_book(book_id, user=current_user)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        return book
    finally:
        await service.close()


@router.post("/downloads", response_model=OpenLibraryDownloadResponse, status_code=status.HTTP_201_CREATED)
async def record_download(
    download: OpenLibraryDownloadCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a download/read for analytics."""
    service = OpenLibraryService(db)
    try:
        result = await service.record_download(current_user, download.book_id, download.access_type)
        await db.commit()
        return result
    except OpenLibraryServiceError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    finally:
        await service.close()


@router.post("/favorites", response_model=OpenLibraryFavoriteResponse, status_code=status.HTTP_201_CREATED)
async def add_favorite(
    favorite: OpenLibraryFavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a book to favorites."""
    service = OpenLibraryService(db)
    try:
        result = await service.add_favorite(current_user, favorite.book_id, favorite.notes)
        await db.commit()
        return result
    except OpenLibraryServiceError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    finally:
        await service.close()


@router.delete("/favorites/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a book from favorites."""
    service = OpenLibraryService(db)
    try:
        removed = await service.remove_favorite(current_user, book_id)
        await db.commit()
        if not removed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")
    finally:
        await service.close()


@router.get("/stats", response_model=OpenLibraryStatsResponse)
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get Open Library usage statistics. Staff and above."""
    await require_staff(current_user)
    service = OpenLibraryService(db)
    try:
        return await service.get_statistics()
    finally:
        await service.close()


@router.post("/sync")
async def trigger_sync(
    sync_options: OpenLibrarySyncTrigger,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger catalog sync from Open Library API. Admin only."""
    await require_admin(current_user)
    service = OpenLibraryService(db)
    try:
        result = await service.sync_catalog(
            subject=sync_options.subject, max_batches=sync_options.max_batches,
        )
        return {"ok": True, "message": "Sync completed", "triggered_by": current_user.email, **result}
    except OpenLibraryServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
    finally:
        await service.close()


@router.get("/sync/status", response_model=OpenLibrarySyncStatusResponse | None)
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get catalog sync status. Staff and above."""
    await require_staff(current_user)
    service = OpenLibraryService(db)
    try:
        return await service.get_sync_status()
    finally:
        await service.close()
