# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Indie ebook lending endpoints -- borrow, return, active borrows, waitlist, download."""
import asyncio
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.user import User
from ...models.indie_ebook_borrow import IndieEbook, IndieEbookBorrow, BorrowStatus
from ...services.indie_lending_service import get_lending_service
from ...services.metislib_errors import MetisLibError
from ..v1.auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/indie/lending", tags=["indie-lending"])


# ── Request/Response schemas ──────────────────────────────────

class BorrowRequest(BaseModel):
    ebook_id: int | None = None
    catalog_item_id: int | None = None

class BorrowResponse(BaseModel):
    id: int
    ebook_id: int
    ebook_title: str
    borrowed_at: str
    due_at: str
    access_token: str
    download_url: str
    status: str

class ActiveBorrowResponse(BaseModel):
    id: int
    ebook_id: int
    indie_ebook_id: int
    ebook_title: str
    ebook_cover_url: str | None
    author_pen_name: str
    borrowed_at: str
    due_at: str
    status: str
    download_count: int
    max_downloads: int

class ReturnRequest(BaseModel):
    rating: int | None = None
    review_text: str | None = None

class WaitlistResponse(BaseModel):
    ebook_id: int
    ebook_title: str
    position: int
    estimated_wait_days: int
    created_at: str


DEFAULT_BORROW_DAYS = 21


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/borrows/active", response_model=list[ActiveBorrowResponse])
async def get_active_borrows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get patron's active indie ebook borrows."""
    service = get_lending_service()
    raw = await service.get_active_borrows(current_user.id, db)
    return [
        ActiveBorrowResponse(
            id=b["id"],
            ebook_id=b["ebook_id"],
            indie_ebook_id=b["indie_ebook_id"],
            ebook_title=b["ebook_title"],
            ebook_cover_url=b.get("ebook_cover_url"),
            author_pen_name=b["author_pen_name"],
            borrowed_at=b["borrowed_at"],
            due_at=b["due_at"],
            status=b["status"],
            download_count=b["download_count"],
            max_downloads=b["max_downloads"],
        )
        for b in raw
    ]


@router.post("/borrow", response_model=BorrowResponse)
async def borrow_ebook(
    req: BorrowRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Borrow an indie ebook."""
    ebook_id = req.ebook_id
    if not ebook_id and req.catalog_item_id:
        raise HTTPException(status_code=400, detail="catalog_item_id lookup not supported; use ebook_id")
    if not ebook_id:
        raise HTTPException(status_code=422, detail="ebook_id is required")

    service = get_lending_service()
    try:
        borrow = await service.borrow_ebook(ebook_id, current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Hydrate title from MetisLib for response
    ebook = await db.get(IndieEbook, ebook_id)
    title = "Indie Ebook"
    if ebook and ebook.metislib_ebook_id:
        try:
            from ...services.metislib_client import get_metislib_client
            client = get_metislib_client()
            meta = await client.get_ebook(ebook.metislib_ebook_id, entry_type="indie_ebook")
            title = meta.get("title", title)
        except MetisLibError:
            pass

    return BorrowResponse(
        id=borrow.id,
        ebook_id=borrow.ebook_id,
        ebook_title=title,
        borrowed_at=borrow.borrowed_at.isoformat(),
        due_at=borrow.due_at.isoformat(),
        access_token=borrow.access_token,
        download_url=f"/api/v1/indie/lending/download/{borrow.access_token}",
        status=borrow.status.value if isinstance(borrow.status, BorrowStatus) else borrow.status,
    )


@router.post("/borrows/{borrow_id}/return", response_model=ActiveBorrowResponse)
async def return_ebook(
    borrow_id: int,
    body: ReturnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a borrowed indie ebook with optional rating."""
    result = await db.execute(
        select(IndieEbookBorrow)
        .options(selectinload(IndieEbookBorrow.ebook))
        .where(
            IndieEbookBorrow.id == borrow_id,
            IndieEbookBorrow.user_id == current_user.id,
        )
    )
    borrow = result.scalar_one_or_none()
    if not borrow:
        raise HTTPException(status_code=404, detail="Borrow not found")

    service = get_lending_service()
    try:
        borrow = await service.return_ebook(borrow, body.rating, db, review_text=body.review_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Hydrate metadata
    meta = {}
    if borrow.ebook and borrow.ebook.metislib_ebook_id:
        try:
            from ...services.metislib_client import get_metislib_client
            client = get_metislib_client()
            meta = await client.get_ebook(borrow.ebook.metislib_ebook_id, entry_type="indie_ebook")
        except MetisLibError:
            pass

    return ActiveBorrowResponse(
        id=borrow.id,
        ebook_id=borrow.ebook_id,
        indie_ebook_id=borrow.ebook_id,
        ebook_title=meta.get("title", "Unavailable"),
        ebook_cover_url=meta.get("cover_url"),
        author_pen_name=meta.get("author_name", "Unknown"),
        borrowed_at=borrow.borrowed_at.isoformat(),
        due_at=borrow.due_at.isoformat(),
        status=borrow.status.value if isinstance(borrow.status, BorrowStatus) else borrow.status,
        download_count=borrow.download_count,
        max_downloads=borrow.max_downloads,
    )


@router.post("/waitlist/{ebook_id}", response_model=WaitlistResponse)
async def join_waitlist(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join waitlist for an indie ebook."""
    service = get_lending_service()
    try:
        entry = await service.join_waitlist(ebook_id, current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Hydrate title
    ebook = await db.get(IndieEbook, ebook_id)
    title = "Indie Ebook"
    if ebook and ebook.metislib_ebook_id:
        try:
            from ...services.metislib_client import get_metislib_client
            client = get_metislib_client()
            meta = await client.get_ebook(ebook.metislib_ebook_id, entry_type="indie_ebook")
            title = meta.get("title", title)
        except MetisLibError:
            pass

    return WaitlistResponse(
        ebook_id=ebook_id,
        ebook_title=title,
        position=entry.position,
        estimated_wait_days=entry.position * DEFAULT_BORROW_DAYS,
        created_at=entry.created_at.isoformat(),
    )


@router.get("/download/{access_token}")
async def download_ebook(
    access_token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a borrowed indie ebook. Redirects to MetisLib download URL."""
    result = await db.execute(
        select(IndieEbookBorrow)
        .options(selectinload(IndieEbookBorrow.ebook))
        .where(
            IndieEbookBorrow.access_token == access_token,
            IndieEbookBorrow.user_id == current_user.id,
        )
    )
    borrow = result.scalar_one_or_none()
    if not borrow:
        raise HTTPException(status_code=404, detail="Invalid access token")

    if borrow.status != BorrowStatus.active:
        raise HTTPException(status_code=403, detail="Borrow expired or returned")

    if borrow.download_count >= borrow.max_downloads:
        raise HTTPException(status_code=403, detail="Download limit reached")

    # Phase 2: serve the L30-owned EPUB from local disk when present.
    import os as _os
    _lp = borrow.ebook.file_path if borrow.ebook else None
    if _lp and _os.path.exists(_lp) and _os.path.getsize(_lp) > 0:
        borrow.download_count += 1
        await db.commit()
        _fn = f"{(borrow.ebook.title or 'ebook').replace('/', '-')}.epub"
        return FileResponse(_lp, media_type="application/epub+zip", filename=_fn)

    # Get download URL from MetisLib
    if not borrow.ebook or not borrow.ebook.metislib_ebook_id:
        raise HTTPException(status_code=404, detail="Ebook file not available")

    try:
        from ...services.metislib_client import get_metislib_client
        from ...utils.patron_hash import generate_patron_hash
        client = get_metislib_client()
        download_info = await client.get_download_url(
            borrow.ebook.metislib_ebook_id,
            generate_patron_hash(current_user.id),
        )
        download_url = download_info.get("download_url") if isinstance(download_info, dict) else None
        if not download_url:
            raise HTTPException(status_code=404, detail="Download URL not available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get download URL from MetisLib: %s", e)
        raise HTTPException(status_code=502, detail="Download service unavailable") from e

    # Increment download count
    borrow.download_count += 1
    await db.commit()

    return RedirectResponse(url=download_url, status_code=302)


@router.get("/read/{ebook_id}/content")
async def stream_ebook_content(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream raw EPUB bytes for an active borrow, for the in-browser reader.

    Keyed by ebook_id (the universal key the reader, progress, and borrow list
    all share) and gated by an active borrow owned by the caller -- same
    security as the token download (the loan must be the caller's and active),
    without leaking the download token into list payloads. Streams the file body
    through our own origin (so the reader fetch stays same-origin and the
    upstream URL never reaches the browser) instead of 302-redirecting. Reading
    in the browser is not a "download" -- it does NOT count against the loan's
    download cap.
    """
    result = await db.execute(
        select(IndieEbookBorrow)
        .options(selectinload(IndieEbookBorrow.ebook))
        .where(
            IndieEbookBorrow.ebook_id == ebook_id,
            IndieEbookBorrow.user_id == current_user.id,
            IndieEbookBorrow.status == BorrowStatus.active,
        )
        .order_by(IndieEbookBorrow.id.desc())
        .limit(1)
    )
    borrow = result.scalar_one_or_none()
    if not borrow:
        raise HTTPException(status_code=403, detail="No active borrow for this title")

    # Phase 2: stream the L30-owned EPUB from local disk when present.
    import os as _os
    _lp = borrow.ebook.file_path if borrow.ebook else None
    if _lp and _os.path.exists(_lp) and _os.path.getsize(_lp) > 0:
        return FileResponse(
            _lp, media_type="application/epub+zip",
            headers={
                "Content-Disposition": "inline",
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    if not borrow.ebook or not borrow.ebook.metislib_ebook_id:
        raise HTTPException(status_code=404, detail="Ebook file not available")

    from ...services.metislib_client import get_metislib_client
    from ...utils.patron_hash import generate_patron_hash

    client = get_metislib_client()
    try:
        download_info = await client.get_download_url(
            borrow.ebook.metislib_ebook_id,
            generate_patron_hash(current_user.id),
        )
        download_url = download_info.get("download_url") if isinstance(download_info, dict) else None
        if not download_url:
            raise HTTPException(status_code=404, detail="Download URL not available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get download URL from MetisLib: %s", e)
        raise HTTPException(status_code=502, detail="Reader content unavailable") from e

    # Open the upstream stream and validate its status BEFORE returning the
    # StreamingResponse, so a bad upstream surfaces as a clean HTTP error
    # rather than a truncated body after headers are already sent. The client
    # is closed in the generator's finally so it outlives the request handler.
    http = httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(60.0, connect=10.0))
    try:
        upstream = await http.send(http.build_request("GET", download_url), stream=True)
    except Exception as e:
        await http.aclose()
        logger.error("Upstream EPUB connection failed (%s): %s", download_url, e)
        raise HTTPException(status_code=502, detail="Reader content unavailable") from e

    if upstream.status_code != 200:
        await upstream.aclose()
        await http.aclose()
        logger.error("Upstream EPUB fetch returned %s for ebook %s", upstream.status_code, borrow.ebook.metislib_ebook_id)
        raise HTTPException(status_code=502, detail="Reader content unavailable")

    async def _iter_epub():
        try:
            async for chunk in upstream.aiter_bytes(chunk_size=65536):
                yield chunk
        finally:
            await upstream.aclose()
            await http.aclose()

    headers = {
        "Content-Disposition": "inline",
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    }
    content_length = upstream.headers.get("content-length")
    if content_length:
        headers["Content-Length"] = content_length

    return StreamingResponse(_iter_epub(), media_type="application/epub+zip", headers=headers)



# -- Reviews ---------------------------------------------------------------

class ReviewRequest(BaseModel):
    rating: int
    review_text: str | None = None

class ReviewResponse(BaseModel):
    id: int
    rating: int
    review_text: str | None
    reviewer_name: str
    created_at: str


@router.get("/ebooks/{ebook_id}/reviews", response_model=list[ReviewResponse])
async def get_ebook_reviews(
    ebook_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get public reviews for an ebook."""
    service = get_lending_service()
    return await service.get_ebook_reviews(ebook_id, db)


@router.get("/borrows/by-ebook/{ebook_id}")
async def get_user_borrow_for_ebook(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's most recent borrow for a given ebook (for review eligibility)."""
    result = await db.execute(
        select(IndieEbookBorrow)
        .where(
            IndieEbookBorrow.ebook_id == ebook_id,
            IndieEbookBorrow.user_id == current_user.id,
        )
        .order_by(IndieEbookBorrow.borrowed_at.desc())
        .limit(1)
    )
    borrow = result.scalar_one_or_none()
    if not borrow:
        raise HTTPException(status_code=404, detail="No borrow found for this ebook")
    return {
        "id": borrow.id,
        "status": borrow.status.value if isinstance(borrow.status, BorrowStatus) else borrow.status,
        "rating": borrow.rating,
        "review_text": borrow.review_text,
    }


@router.post("/borrows/{borrow_id}/review", response_model=ReviewResponse)
async def submit_review(
    borrow_id: int,
    body: ReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit or update a review on a returned borrow."""
    result = await db.execute(
        select(IndieEbookBorrow)
        .options(selectinload(IndieEbookBorrow.user))
        .where(
            IndieEbookBorrow.id == borrow_id,
            IndieEbookBorrow.user_id == current_user.id,
        )
    )
    borrow = result.scalar_one_or_none()
    if not borrow:
        raise HTTPException(status_code=404, detail="Borrow not found")

    service = get_lending_service()
    try:
        borrow = await service.submit_review(borrow, body.rating, body.review_text, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    name = "A Reader"
    if borrow.user:
        name = getattr(borrow.user, 'display_name', None) or borrow.user.email.split("@")[0]
    return ReviewResponse(
        id=borrow.id,
        rating=borrow.rating,
        review_text=borrow.review_text,
        reviewer_name=name,
        created_at=borrow.review_submitted_at.isoformat(),
    )


# -- Renewal ---------------------------------------------------------------

@router.post("/borrows/{borrow_id}/renew", response_model=ActiveBorrowResponse)
async def renew_borrow(
    borrow_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Renew an active borrow for another 21 days (max 1 renewal, blocked if waitlist exists)."""
    from ...models.indie_ebook_borrow import IndieEbookWaitlist

    result = await db.execute(
        select(IndieEbookBorrow)
        .options(selectinload(IndieEbookBorrow.ebook))
        .where(
            IndieEbookBorrow.id == borrow_id,
            IndieEbookBorrow.user_id == current_user.id,
        )
    )
    borrow = result.scalar_one_or_none()
    if not borrow:
        raise HTTPException(status_code=404, detail="Borrow not found")

    if borrow.status != BorrowStatus.active:
        raise HTTPException(status_code=400, detail="Only active borrows can be renewed")

    renewal_count = getattr(borrow, 'renewal_count', 0) or 0
    if renewal_count >= 1:
        raise HTTPException(status_code=400, detail="This borrow has already been renewed")

    # Check waitlist
    from sqlalchemy import func as sa_func
    waitlist_count = await db.execute(
        select(sa_func.count()).where(IndieEbookWaitlist.ebook_id == borrow.ebook_id)
    )
    if waitlist_count.scalar() > 0:
        raise HTTPException(status_code=400, detail="Cannot renew: others are waiting for this book")

    from datetime import timedelta
    borrow.due_at = borrow.due_at + timedelta(days=DEFAULT_BORROW_DAYS)
    if hasattr(borrow, 'renewal_count'):
        borrow.renewal_count = renewal_count + 1
    await db.commit()
    await db.refresh(borrow)

    # Hydrate metadata
    meta = {}
    if borrow.ebook and borrow.ebook.metislib_ebook_id:
        try:
            from ...services.metislib_client import get_metislib_client
            client = get_metislib_client()
            meta = await client.get_ebook(borrow.ebook.metislib_ebook_id, entry_type="indie_ebook")
        except MetisLibError:
            pass

    return ActiveBorrowResponse(
        id=borrow.id,
        ebook_id=borrow.ebook_id,
        indie_ebook_id=borrow.ebook_id,
        ebook_title=meta.get("title", "Unavailable"),
        ebook_cover_url=meta.get("cover_url"),
        author_pen_name=meta.get("author_name", "Unknown"),
        borrowed_at=borrow.borrowed_at.isoformat(),
        due_at=borrow.due_at.isoformat(),
        status=borrow.status.value if isinstance(borrow.status, BorrowStatus) else borrow.status,
        download_count=borrow.download_count,
        max_downloads=borrow.max_downloads,
    )


# -- Borrow History --------------------------------------------------------

class HistoryBorrowResponse(BaseModel):
    id: int
    ebook_id: int
    ebook_title: str
    ebook_cover_url: str | None
    author_pen_name: str
    borrowed_at: str
    returned_at: str | None
    due_at: str
    status: str
    rating: int | None

class PaginatedHistoryResponse(BaseModel):
    items: list[HistoryBorrowResponse]
    total: int
    page: int
    per_page: int


@router.get("/borrows/history", response_model=PaginatedHistoryResponse)
async def get_borrow_history(
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get patron's past borrows (returned/expired) with metadata."""
    import asyncio
    from sqlalchemy import func as sa_func

    # Count total
    count_result = await db.execute(
        select(sa_func.count()).where(
            IndieEbookBorrow.user_id == current_user.id,
            IndieEbookBorrow.status.in_([BorrowStatus.returned, BorrowStatus.expired]),
        )
    )
    total = count_result.scalar() or 0

    # Fetch page
    result = await db.execute(
        select(IndieEbookBorrow)
        .options(selectinload(IndieEbookBorrow.ebook))
        .where(
            IndieEbookBorrow.user_id == current_user.id,
            IndieEbookBorrow.status.in_([BorrowStatus.returned, BorrowStatus.expired]),
        )
        .order_by(IndieEbookBorrow.returned_at.desc().nullslast())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    borrows = result.scalars().all()

    # Batch-fetch metadata
    metislib_ids = {b.ebook.metislib_ebook_id for b in borrows if b.ebook and b.ebook.metislib_ebook_id}
    metadata_map: dict[int, dict] = {}
    if metislib_ids:
        try:
            from ...services.metislib_client import get_metislib_client
            client = get_metislib_client()

            async def _fetch(mid: int) -> tuple[int, dict | None]:
                try:
                    return mid, await client.get_ebook(mid, entry_type="indie_ebook")
                except Exception:  # noqa: BLE001 -- MetisLibError OR httpx.TimeoutException; degrade gracefully per slot
                    return mid, None

            results = await asyncio.gather(*[_fetch(mid) for mid in metislib_ids])
            for mid, meta in results:
                if meta:
                    metadata_map[mid] = meta
        except Exception:  # noqa: BLE001 -- outer client construction may fail; degrade to empty metadata
            pass

    items = []
    for b in borrows:
        meta = metadata_map.get(b.ebook.metislib_ebook_id, {}) if b.ebook and b.ebook.metislib_ebook_id else {}
        items.append(HistoryBorrowResponse(
            id=b.id,
            ebook_id=b.ebook_id,
            ebook_title=meta.get("title", "Unavailable"),
            ebook_cover_url=meta.get("cover_url"),
            author_pen_name=meta.get("author_name", "Unknown"),
            borrowed_at=b.borrowed_at.isoformat(),
            returned_at=b.returned_at.isoformat() if b.returned_at else None,
            due_at=b.due_at.isoformat(),
            status=b.status.value if isinstance(b.status, BorrowStatus) else b.status,
            rating=b.rating,
        ))

    return PaginatedHistoryResponse(items=items, total=total, page=page, per_page=per_page)


# -- For You Recommendations -----------------------------------------------

class ForYouItem(BaseModel):
    type: str  # 'book'
    item: dict
    feed_reason: str
    feed_reason_detail: str | None = None

class ForYouFeedResponse(BaseModel):
    items: list[ForYouItem]
    total: int
    page: int


@router.get("/for-you", response_model=ForYouFeedResponse)
async def get_for_you_feed(
    page: int = 1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Personalized recommendations based on borrow history genres."""
    import asyncio
    from collections import Counter

    from ...services.metislib_client import get_metislib_client
    client = get_metislib_client()
    per_page = 12

    # 1. Get user's borrow history (all borrows, not just active)
    result = await db.execute(
        select(IndieEbookBorrow)
        .options(selectinload(IndieEbookBorrow.ebook))
        .where(IndieEbookBorrow.user_id == current_user.id)
        .order_by(IndieEbookBorrow.borrowed_at.desc())
    )
    borrows = result.scalars().all()

    borrowed_metislib_ids: set[int] = set()
    for b in borrows:
        if b.ebook and b.ebook.metislib_ebook_id:
            borrowed_metislib_ids.add(b.ebook.metislib_ebook_id)

    # 2. If no borrow history, fall back to popular books
    if not borrowed_metislib_ids:
        try:
            popular = await client.search_catalog(
                filters={"source_type": "indie"}, per_page=per_page
            )
            items = [
                ForYouItem(
                    type="book",
                    item=_to_feed_item(b),
                    feed_reason="Popular in your library",
                )
                for b in (popular.get("items") or [])[:per_page]
            ]
            return ForYouFeedResponse(items=items, total=len(items), page=1)
        except MetisLibError as e:
            logger.warning("For-you fallback to popular failed: %s", e)
            return ForYouFeedResponse(items=[], total=0, page=1)

    # 3. Fetch metadata for borrowed books to extract genres
    async def _fetch_meta(mid: int) -> dict | None:
        try:
            return await client.get_ebook(mid, entry_type="indie_ebook")
        except MetisLibError:
            return None

    metas = await asyncio.gather(*[_fetch_meta(mid) for mid in borrowed_metislib_ids])
    meta_map: dict[int, dict] = {}
    for meta in metas:
        if meta and isinstance(meta, dict) and "id" in meta:
            meta_map[meta["id"]] = meta

    # 4. Count genre frequency to find preferences
    genre_counter: Counter[str] = Counter()
    genre_exemplar: dict[str, str] = {}  # genre -> title of a book the user read
    for mid in borrowed_metislib_ids:
        meta = meta_map.get(mid)
        if not meta:
            continue
        genre = meta.get("genre")
        if genre:
            g = genre.strip()
            genre_counter[g] += 1
            if g not in genre_exemplar:
                genre_exemplar[g] = meta.get("title", "a book you read")

    if not genre_counter:
        # Borrowed books but none have genres -- fall back to popular
        try:
            popular = await client.search_catalog(
                filters={"source_type": "indie"}, per_page=per_page
            )
            items = [
                ForYouItem(
                    type="book",
                    item=_to_feed_item(b),
                    feed_reason="Popular in your library",
                )
                for b in (popular.get("items") or [])[:per_page]
                if b.get("id") not in borrowed_metislib_ids
            ]
            return ForYouFeedResponse(items=items, total=len(items), page=1)
        except MetisLibError:
            return ForYouFeedResponse(items=[], total=0, page=1)

    # 5. Search for books in the user's top genres (up to 3)
    top_genres = [g for g, _ in genre_counter.most_common(3)]
    all_candidates: list[ForYouItem] = []
    seen_ids: set[int] = set()

    for genre in top_genres:
        try:
            results = await client.search_catalog(
                filters={"source_type": "indie", "genre": genre},
                per_page=20,
            )
            exemplar_title = genre_exemplar.get(genre, "books you have read")
            for book in results.get("items") or []:
                bid = book.get("id")
                if bid in borrowed_metislib_ids or bid in seen_ids:
                    continue
                seen_ids.add(bid)
                reason_detail = "You enjoyed " + repr(exemplar_title) + " -- more " + genre + " for you"
                all_candidates.append(
                    ForYouItem(
                        type="book",
                        item=_to_feed_item(book),
                        feed_reason="Because you read " + genre,
                        feed_reason_detail=reason_detail,
                    )
                )
        except MetisLibError as e:
            logger.warning("For-you genre search failed for %s: %s", genre, e)

    # 6. Paginate
    start = (page - 1) * per_page
    end = start + per_page
    page_items = all_candidates[start:end]

    return ForYouFeedResponse(
        items=page_items,
        total=len(all_candidates),
        page=page,
    )


def _to_feed_item(book: dict) -> dict:
    title = book.get("title", "Untitled")
    bid = book.get("id", 0)
    safe_title = title.lower().replace(" ", "-")[:30] if title else "book"
    slug = safe_title + "-" + str(bid)
    return {
        "id": bid,
        "slug": slug,
        "title": title,
        "cover_url": book.get("cover_url"),
        "author_pen_name": book.get("author_pen_name") or book.get("author_name", "Unknown"),
    }


# -- Book Preview / Read Sample -------------------------------------------

class PreviewResponse(BaseModel):
    ebook_id: int
    title: str
    author_name: str
    preview_html: str
    preview_pct: int


@router.get("/preview/{ebook_id}", response_model=PreviewResponse)
async def get_book_preview(
    ebook_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return sample text for an indie ebook. No auth required."""
    ebook = await db.get(IndieEbook, ebook_id)
    if not ebook:
        raise HTTPException(status_code=404, detail="Ebook not found")

    # Try MetisLib preview first
    preview_html: str | None = None
    title = "Indie Ebook"
    author_name = "Unknown"

    if ebook.metislib_ebook_id:
        try:
            from ...services.metislib_client import get_metislib_client
            client = get_metislib_client()
            meta = await client.get_ebook(ebook.metislib_ebook_id, entry_type="indie_ebook")
            title = meta.get("title", title)
            author_name = meta.get("author_name", author_name)
        except MetisLibError:
            pass

        try:
            from ...services.metislib_client import get_metislib_client
            client = get_metislib_client()
            preview_data = await client.get_preview(ebook.metislib_ebook_id)
            if isinstance(preview_data, dict):
                preview_html = preview_data.get("preview_html") or preview_data.get("content")
        except MetisLibError:
            pass

    # Fall back to local sample_text
    if not preview_html and ebook.sample_text:
        # Wrap plain text paragraphs in <p> tags
        paragraphs = [p.strip() for p in ebook.sample_text.split("\n\n") if p.strip()]
        preview_html = "".join(f"<p>{p}</p>" for p in paragraphs)

    if not preview_html:
        raise HTTPException(status_code=404, detail="No preview available for this book")

    return PreviewResponse(
        ebook_id=ebook_id,
        title=title,
        author_name=author_name,
        preview_html=preview_html,
        preview_pct=10,
    )


# ── Just-became-available rail ────────────────────────────────

class JustAvailableEbook(BaseModel):
    ebook_id: int
    title: str
    author_pen_name: str
    cover_url: str | None
    description: str | None
    genre: str | None
    returned_at: str
    available_copies: int


@router.get("/just-available", response_model=list[JustAvailableEbook])
async def get_just_available_ebooks(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(8, ge=1, le=20),
    days: int = Query(7, ge=1, le=30),
):
    """Indie ebooks whose hold queue recently cleared.

    Returns books with at least one return in the last `days` days that
    currently have available copies, ordered by most recent return.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Most-recent returned_at per ebook in the window.
    stmt = (
        select(
            IndieEbookBorrow.ebook_id,
            func.max(IndieEbookBorrow.returned_at).label("last_returned"),
        )
        .where(IndieEbookBorrow.status == BorrowStatus.returned)
        .where(IndieEbookBorrow.returned_at.is_not(None))
        .where(IndieEbookBorrow.returned_at >= since)
        .group_by(IndieEbookBorrow.ebook_id)
        .order_by(func.max(IndieEbookBorrow.returned_at).desc())
        .limit(limit * 2)  # over-fetch; we filter by available_copies after hydrating
    )
    result = await db.execute(stmt)
    rows = result.all()
    if not rows:
        return []

    ebook_ids = [r.ebook_id for r in rows]
    returned_by_ebook = {r.ebook_id: r.last_returned for r in rows}

    ebooks_stmt = select(IndieEbook).where(IndieEbook.id.in_(ebook_ids))
    ebooks_result = await db.execute(ebooks_stmt)
    ebooks_by_id = {e.id: e for e in ebooks_result.scalars().all()}

    try:
        from ...services.metislib_client import get_metislib_client
        client = get_metislib_client()
    except Exception:  # noqa: BLE001  # MetisLib client init may fail for various reasons
        logger.warning("MetisLib client unavailable for just-available rail")
        return []

    async def _hydrate(ebook_id: int) -> Optional[JustAvailableEbook]:
        ebook = ebooks_by_id.get(ebook_id)
        if not ebook:
            return None
        try:
            meta = await client.get_ebook(ebook.metislib_ebook_id, entry_type="indie_ebook")
        except MetisLibError as e:
            logger.warning(f"Skipping just-available ebook {ebook.metislib_ebook_id}: {e}")
            return None
        available_copies = int(meta.get("available_copies") or 0)
        if available_copies <= 0:
            return None
        returned_at = returned_by_ebook.get(ebook_id)
        return JustAvailableEbook(
            ebook_id=ebook_id,
            title=meta.get("title") or "",
            author_pen_name=meta.get("author_pen_name") or meta.get("author_name") or "",
            cover_url=meta.get("cover_url"),
            description=meta.get("description"),
            genre=meta.get("genre"),
            returned_at=returned_at.isoformat() if returned_at else "",
            available_copies=available_copies,
        )

    hydrated = await asyncio.gather(*[_hydrate(eid) for eid in ebook_ids])
    items = [h for h in hydrated if h is not None]
    # Preserve recency ordering, then cap to limit.
    items.sort(key=lambda i: i.returned_at, reverse=True)
    return items[:limit]
