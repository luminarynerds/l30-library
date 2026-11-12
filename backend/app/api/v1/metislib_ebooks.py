# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""MetisLib Ebooks API - Proxy routes for shared ebook catalog.

Exposes MetisLib's shared ebook collection (public domain + indie)
to L30 patrons via /api/v1/ebooks/* endpoints.

Featured ebooks and collections are curated locally (L30 database)
with metadata hydrated from MetisLib at display time.
"""
import asyncio
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.config import get_settings
from ...core.database import get_db
from ...core.cache import get_cached, set_cached
from ...models.ebook_curation import (
    EbookFeatured, EbookCollection, EbookCollectionItem, CollectionStatus
)
from ...models.user import User
from ...models.indie_ebook_borrow import IndieEbook
from ...services.metislib_client import get_metislib_client
from ...services.metislib_errors import (
    MetisLibError, MetisLibUnavailable, MetisLibNotFound,
    MetisLibAuthError, MetisLibForbidden, MetisLibValidationError
)
from ...utils.patron_hash import generate_patron_hash
from ...models.ebook_checkout_log import EbookCheckoutLog
from ...utils.ebook_checkout_log import log_ebook_event
from ..v1.auth import get_current_user, get_current_user_optional

logger = get_logger(__name__)

router = APIRouter(prefix="/ebooks", tags=["ebooks"])


def _require_metislib():
    settings = get_settings()
    if not settings.metislib_enabled:
        raise HTTPException(status_code=503, detail="Ebooks service not available")
    return get_metislib_client()


# Serve-stale caching for the public browse shelves. MetisLib is a live upstream
# behind a circuit breaker; when it's slow, down, or the breaker is open the
# patron used to get a blank/errored shelf (the /indie flakiness). These shelves
# tolerate slightly-old data, so we cache each successful response twice: a short
# "fresh" copy that keeps the happy path off MetisLib, and a long "stale" copy
# served as a fallback whenever a MetisLib call fails.
_FRESH_TTL = 120          # seconds a shelf is served without re-hitting MetisLib
_STALE_TTL = 6 * 60 * 60  # seconds a shelf remains available as a degraded fallback


async def _cached_or_stale(key: str, produce, *, fresh_ttl: int = _FRESH_TTL, stale_ttl: int = _STALE_TTL):
    """Return produce() with fresh-then-stale caching.

    Fresh hit -> return it (no MetisLib call). Miss -> call produce(), cache it
    (fresh + stale), return. If produce() raises a MetisLib failure, fall back to
    the stale copy so the shelf degrades to old data instead of erroring; if there
    is no stale copy, re-raise so the caller maps it to the usual 502/503.
    """
    fresh = await get_cached(f"ebooks:fresh:{key}")
    if fresh is not None:
        return fresh
    try:
        value = await produce()
    except (MetisLibUnavailable, MetisLibError) as exc:
        stale = await get_cached(f"ebooks:stale:{key}")
        if stale is not None:
            logger.warning("ebooks: MetisLib failed for %s (%s); serving stale cache", key, exc)
            return stale
        raise
    await set_cached(f"ebooks:fresh:{key}", value, fresh_ttl)
    await set_cached(f"ebooks:stale:{key}", value, stale_ttl)
    return value


async def _has_active_checkout(client, patron_hash: str, ebook_id: int) -> bool:
    """Whether the patron already has this shared-catalog ebook checked out.

    The coop is the source of truth (L30 keeps no local state for these
    borrows), and neither the coop nor the relay endpoints dedupe, so this is
    the only place a double-borrow / hold-on-held can be caught.
    """
    checkouts = await client.get_patron_checkouts(patron_hash)
    return any(
        isinstance(c, dict) and c.get("ebook_id") == ebook_id
        for c in checkouts
    )


# ============================================================================
# Public catalog browsing (no auth required)
# ============================================================================

@router.get("")
async def browse_ebooks(
    q: Optional[str] = Query(None, max_length=200),
    source_type: Optional[str] = Query(None, pattern="^(open_access|indie)$"),
    sort: Optional[str] = Query(None, pattern="^(newest|popular|rating|title)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    limit: Optional[int] = Query(None, ge=1, le=100),
    exclude_warnings: Optional[list[str]] = Query(
        None,
        description="Content warning categories to exclude. Books whose content_warnings intersect with this list are dropped before pagination so totals and page counts stay accurate.",
    ),
):
    """Browse the shared ebook catalog from MetisLib."""
    effective_limit = limit if limit is not None and per_page == 20 else per_page
    client = _require_metislib()
    filters = {}
    if source_type:
        filters["source_type"] = source_type
    if sort:
        filters["sort"] = sort

    exclude_set = {w.strip().lower() for w in exclude_warnings or [] if w and w.strip()}

    async def _produce():
        if exclude_set:
            # MetisLib has no native warning filter, so over-fetch and re-paginate
            # locally to keep totals and page counts accurate. Indie catalog is
            # small (under a few hundred titles), so a single bulk fetch is fine.
            fetch_size = 100
            all_items: list[dict] = []
            fetch_page = 1
            metislib_total = 0
            while True:
                chunk = await client.search_catalog(
                    query=q, filters=filters, page=fetch_page, per_page=fetch_size,
                )
                if not isinstance(chunk, dict):
                    break
                metislib_total = chunk.get("total", metislib_total)
                items = chunk.get("items", []) or []
                all_items.extend(items)
                if not items or len(all_items) >= metislib_total or fetch_page >= 20:
                    break
                fetch_page += 1

            def _matches_excluded(item: dict) -> bool:
                warnings = item.get("content_warnings") or []
                if not isinstance(warnings, list):
                    return False
                for w in warnings:
                    if isinstance(w, str) and w.strip().lower() in exclude_set:
                        return True
                return False

            filtered = [it for it in all_items if not _matches_excluded(it)]
            total = len(filtered)

            if sort:
                if sort == "newest":
                    filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                elif sort == "popular":
                    filtered.sort(key=lambda x: x.get("total_borrows", 0), reverse=True)
                elif sort == "rating":
                    filtered.sort(key=lambda x: x.get("average_rating") or 0, reverse=True)
                elif sort == "title":
                    filtered.sort(key=lambda x: (x.get("title") or "").lower())

            start = (page - 1) * effective_limit
            end = start + effective_limit
            page_items = filtered[start:end]
            pages = max(1, (total + effective_limit - 1) // effective_limit) if total else 1
            return {
                "items": page_items,
                "total": total,
                "page": page,
                "per_page": effective_limit,
                "pages": pages,
            }

        result = await client.search_catalog(query=q, filters=filters, page=page, per_page=effective_limit)

        # Apply local sort as fallback (MetisLib may not support sort param)
        if sort and isinstance(result, dict) and "items" in result:
            items = result["items"]
            if sort == "newest":
                items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            elif sort == "popular":
                items.sort(key=lambda x: x.get("total_borrows", 0), reverse=True)
            elif sort == "rating":
                items.sort(key=lambda x: x.get("average_rating") or 0, reverse=True)
            elif sort == "title":
                items.sort(key=lambda x: (x.get("title") or "").lower())
            result["items"] = items

        return result

    cache_key = f"browse:{q or ''}:{source_type or ''}:{sort or ''}:{page}:{effective_limit}:{','.join(sorted(exclude_set))}"
    try:
        return await _cached_or_stale(cache_key, _produce)
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib catalog error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching ebooks") from e


@router.get("/featured")
async def get_featured_ebooks(db: AsyncSession = Depends(get_db)):
    """Get locally curated featured ebooks, hydrated from MetisLib."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(EbookFeatured)
        .where(
            (EbookFeatured.featured_from.is_(None)) | (EbookFeatured.featured_from <= now)
        )
        .where(
            (EbookFeatured.featured_until.is_(None)) | (EbookFeatured.featured_until >= now)
        )
        .order_by(EbookFeatured.display_order)
        .limit(100)
    )
    result = await db.execute(stmt)
    featured_rows = result.scalars().all()

    if not featured_rows:
        return {"items": [], "total": 0, "page": 1, "pages": 1}

    client = _require_metislib()

    # entry_type is stored per row, but fall back to l30's indie_ebooks registry
    # when it's NULL so a featured row added without a type can't collide with an
    # open-access ebook of the same id (see PR #1503/#1507/#1509).
    feat_ids = {row.metislib_ebook_id for row in featured_rows}
    indie_ids = set()
    if feat_ids:
        indie_rows = await db.execute(
            select(IndieEbook.metislib_ebook_id).where(IndieEbook.metislib_ebook_id.in_(feat_ids))
        )
        indie_ids = set(indie_rows.scalars().all())

    async def _fetch_one(row: EbookFeatured) -> Optional[dict]:
        entry_type = row.entry_type or (
            "indie_ebook" if row.metislib_ebook_id in indie_ids else None
        )
        try:
            ebook = await client.get_ebook(row.metislib_ebook_id, entry_type=entry_type)
        except MetisLibNotFound as e:
            # Dead curated id: skip just this item. A service outage
            # (MetisLibUnavailable / MetisLibError) is deliberately NOT swallowed
            # so _cached_or_stale can serve the stale shelf instead of a
            # half-empty one.
            logger.warning(f"Skipping featured ebook {row.metislib_ebook_id}: {e}")
            return None
        if row.theme_title:
            ebook["theme_title"] = row.theme_title
        return ebook

    async def _produce():
        fetched = await asyncio.gather(*[_fetch_one(r) for r in featured_rows])
        items = [e for e in fetched if e is not None]
        return {"items": items, "total": len(items), "page": 1, "pages": 1}

    try:
        return await _cached_or_stale("featured", _produce)
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib featured error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching featured ebooks") from e


@router.get("/popular")
async def get_popular_ebooks(
    limit: int = Query(20, ge=1, le=100),
):
    """Get popular ebooks by access count."""
    client = _require_metislib()

    async def _produce():
        return await client.get_popular_ebooks(limit=limit)

    try:
        return await _cached_or_stale(f"popular:{limit}", _produce)
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib popular error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching popular ebooks") from e


@router.get("/collections")
async def get_ebook_collections(db: AsyncSession = Depends(get_db)):
    """Get locally curated ebook collections, hydrated from MetisLib."""
    stmt = (
        select(EbookCollection)
        .where(EbookCollection.status == CollectionStatus.PUBLISHED)
        .options(selectinload(EbookCollection.items))
        .order_by(EbookCollection.display_order)
        .limit(100)
    )
    result = await db.execute(stmt)
    collections = result.scalars().unique().all()

    if not collections:
        return {"items": [], "total": 0}

    client = _require_metislib()

    # Resolve indie-vs-open-access per item. MetisLib indie_ebooks and
    # open-access ebooks share an id space, so a bare get_ebook() can return the
    # wrong title. l30's indie_ebooks registry is authoritative for which ids
    # are indie (see PR #1503/#1507).
    coll_ids = {item.metislib_ebook_id for coll in collections for item in coll.items}
    indie_ids = set()
    if coll_ids:
        indie_rows = await db.execute(
            select(IndieEbook.metislib_ebook_id).where(IndieEbook.metislib_ebook_id.in_(coll_ids))
        )
        indie_ids = set(indie_rows.scalars().all())

    async def _fetch_ebook(ebook_id: int) -> Optional[dict]:
        try:
            return await client.get_ebook(
                ebook_id,
                entry_type="indie_ebook" if ebook_id in indie_ids else None,
            )
        except MetisLibNotFound as e:
            # Dead id: skip this item; a service outage propagates instead so
            # _cached_or_stale can serve the stale collections shelf.
            logger.warning(f"Skipping collection ebook {ebook_id}: {e}")
            return None

    async def _produce():
        output = []
        for coll in collections:
            item_ids = [item.metislib_ebook_id for item in coll.items]
            if item_ids:
                fetched = await asyncio.gather(*[_fetch_ebook(eid) for eid in item_ids])
                ebooks = [e for e in fetched if e is not None]
            else:
                ebooks = []
            output.append({
                "id": coll.id,
                "title": coll.title,
                "description": coll.description,
                "ebooks": ebooks,
            })
        return {"items": output, "total": len(output)}

    try:
        return await _cached_or_stale("collections", _produce)
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib collections error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching collections") from e




# ============================================================================
# Genre and staff-picks discovery (public, no auth)
# ============================================================================

@router.get("/genres")
async def get_genre_list():
    """Aggregate genre counts from MetisLib catalog (indie ebooks only)."""
    client = _require_metislib()

    async def _produce():
        genres: dict[str, int] = {}
        page = 1
        while True:
            data = await client.search_catalog(
                filters={"source_type": "indie"}, page=page, per_page=100,
            )
            items = data.get("items", [])
            if not items:
                break
            for item in items:
                g = item.get("genre")
                if g:
                    genres[g] = genres.get(g, 0) + 1
            total = data.get("total", 0)
            if page * 100 >= total:
                break
            page += 1

        return sorted(
            [
                {
                    "name": name,
                    "slug": name.lower().replace(" ", "_").replace("/", "-"),
                    "count": count,
                    "description": None,
                }
                for name, count in genres.items()
            ],
            key=lambda x: -x["count"],
        )

    try:
        return await _cached_or_stale("genres", _produce)
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib genre aggregation error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching genres") from e


@router.get("/staff-picks")
async def get_staff_picks_ebooks(db: AsyncSession = Depends(get_db)):
    """Get staff-picked ebooks from the 'Staff Picks' collection."""
    from sqlalchemy import func as sqlfunc
    stmt = (
        select(EbookCollection)
        .where(
            EbookCollection.status == CollectionStatus.PUBLISHED,
            sqlfunc.lower(EbookCollection.title).like("%staff pick%"),
        )
        .options(selectinload(EbookCollection.items))
        .limit(1)
    )
    result = await db.execute(stmt)
    collection = result.scalar_one_or_none()

    if not collection or not collection.items:
        return {"items": [], "total": 0}

    client = _require_metislib()

    sp_ids = {item.metislib_ebook_id for item in collection.items}
    indie_ids = set()
    if sp_ids:
        indie_rows = await db.execute(
            select(IndieEbook.metislib_ebook_id).where(IndieEbook.metislib_ebook_id.in_(sp_ids))
        )
        indie_ids = set(indie_rows.scalars().all())

    async def _fetch(ebook_id: int):
        try:
            return await client.get_ebook(
                ebook_id,
                entry_type="indie_ebook" if ebook_id in indie_ids else None,
            )
        except MetisLibNotFound as exc:
            # Dead id: skip; a service outage propagates for stale-serve.
            logger.warning("Skipping staff pick ebook %s: %s", ebook_id, exc)
            return None

    async def _produce():
        fetched = await asyncio.gather(
            *[_fetch(item.metislib_ebook_id) for item in collection.items]
        )
        items = [e for e in fetched if e is not None]
        return {"items": items, "total": len(items)}

    try:
        return await _cached_or_stale("staff-picks", _produce)
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error("MetisLib staff-picks error: %s", e)
        raise HTTPException(status_code=502, detail="Error fetching staff picks") from e


# ============================================================================
# Patron actions (auth required) — must come before /{ebook_id} routes
# ============================================================================

@router.get("/me/checkouts")
async def get_my_checkouts(
    current_user: User = Depends(get_current_user),
):
    """Get current user's active ebook checkouts."""
    client = _require_metislib()
    patron_hash = generate_patron_hash(current_user.id)
    try:
        return await client.get_patron_checkouts(patron_hash)
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib checkouts error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching checkouts") from e


@router.get("/featured-author")
async def get_featured_author(db: AsyncSession = Depends(get_db)):
    """Return a random indie author who has a bio, for the Author Spotlight section."""
    import random as _random
    from ...models.indie_author import IndieAuthor

    stmt = select(IndieAuthor).where(
        IndieAuthor.bio.isnot(None),
        IndieAuthor.bio != "",
    )
    result = await db.execute(stmt)
    authors = result.scalars().all()

    if not authors:
        raise HTTPException(status_code=404, detail="No featured authors available")

    author = _random.choice(authors)

    # Count books from the owned indie_ebooks table (no live MetisLib call --
    # this was the last MetisLib dependency on the /indie browse path).
    from ...models.indie_ebook_borrow import IndieEbook

    book_count = (
        await db.execute(
            select(func.count(IndieEbook.id)).where(IndieEbook.author_pen_name == author.pen_name)
        )
    ).scalar() or 0

    return {
        "id": author.id,
        "pen_name": author.pen_name,
        "bio": author.bio,
        "profile_image_url": author.profile_image_url,
        "book_count": book_count,
    }



# ============================================================================
# Detail and per-ebook actions
# ============================================================================

@router.get("/{ebook_id}")
async def get_ebook_detail(
    ebook_id: int,
    entry_type: Optional[str] = Query(None, pattern="^(ebook|indie_ebook)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get full detail for a single ebook.

    When the id belongs to an indie title, attach the L30 IndieEbook PK as
    `indie_ebook_id`. The catalog surface keys ebooks by metislib_ebook_id, but
    the indie lending endpoints (borrow / reader / review-eligibility) key on the
    IndieEbook PK, so the detail page needs both ids to drive lending actions.
    """
    client = _require_metislib()
    indie_row = (
        await db.execute(
            select(IndieEbook).where(IndieEbook.metislib_ebook_id == ebook_id)
        )
    ).scalar_one_or_none()
    try:
        ebook = await client.get_ebook(ebook_id, entry_type=entry_type)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Ebook not found") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib detail error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching ebook") from e
    if indie_row is not None and isinstance(ebook, dict):
        ebook["indie_ebook_id"] = indie_row.id
    return ebook


@router.post("/{ebook_id}/borrow")
async def borrow_ebook(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Borrow an ebook from the shared catalog."""
    client = _require_metislib()
    patron_hash = generate_patron_hash(current_user.id)
    try:
        if await _has_active_checkout(client, patron_hash, ebook_id):
            raise HTTPException(status_code=409, detail="You already have this ebook checked out.")
        result = await client.checkout(ebook_id, patron_hash)
        title = result.get("title", "") if isinstance(result, dict) else ""
        author = result.get("author", "") if isinstance(result, dict) else ""
        await log_ebook_event(db, current_user.id, "metislib", "borrow", title, ebook_author=author)
        await db.commit()
        return result
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Ebook not found") from None
    except MetisLibForbidden:
        raise HTTPException(status_code=403, detail="This title isn't available at your library.") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib borrow error: {e}")
        raise HTTPException(status_code=502, detail="Error borrowing ebook") from e


@router.post("/{ebook_id}/hold")
async def place_hold_on_ebook(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
):
    """Place a hold on an ebook."""
    client = _require_metislib()
    patron_hash = generate_patron_hash(current_user.id)
    try:
        if await _has_active_checkout(client, patron_hash, ebook_id):
            raise HTTPException(status_code=409, detail="You already have this ebook checked out.")
        return await client.place_hold(ebook_id, patron_hash)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Ebook not found") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib hold error: {e}")
        raise HTTPException(status_code=502, detail="Error placing hold") from e


@router.get("/{ebook_id}/hold/status")
async def get_hold_status(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
):
    """The current user's hold standing for an ebook (queue position / ready).

    Returns ``{on_hold: false}`` when the patron is not in the queue, rather
    than a 404, so the detail page can render a plain "place a hold" state.
    """
    client = _require_metislib()
    patron_hash = generate_patron_hash(current_user.id)
    try:
        data = await client.hold_status(ebook_id, patron_hash)
        return {"on_hold": True, **(data if isinstance(data, dict) else {})}
    except MetisLibNotFound:
        return {"on_hold": False}
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib hold status error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching hold status") from e


@router.delete("/{ebook_id}/hold")
async def leave_hold(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
):
    """Leave the hold queue for an ebook.

    Auto-detects catalog vs indie: indie holds leave by ebook id
    (``DELETE /holds/indie/{id}``), catalog holds by hold id
    (``DELETE /holds/{hold_id}``).
    """
    client = _require_metislib()
    patron_hash = generate_patron_hash(current_user.id)
    try:
        status = await client.hold_status(ebook_id, patron_hash)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="You don't have a hold on this title.") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib hold lookup error: {e}")
        raise HTTPException(status_code=502, detail="Error leaving hold") from e

    try:
        if isinstance(status, dict) and status.get("kind") == "indie":
            return await client.leave_indie_hold(ebook_id, patron_hash)
        return await client.cancel_hold(int(status["hold_id"]), patron_hash)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="You don't have a hold on this title.") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib leave hold error: {e}")
        raise HTTPException(status_code=502, detail="Error leaving hold") from e


@router.post("/{ebook_id}/buy")
async def overflow_purchase(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Overflow purchases have been removed."""
    raise HTTPException(status_code=410, detail="Overflow purchases are no longer available")


@router.post("/{ebook_id}/buy/cancel")
async def cancel_overflow_purchase(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Overflow purchase cancellation has been removed."""
    raise HTTPException(status_code=410, detail="Overflow purchases are no longer available")


# Download / Return
# ============================================================================

@router.get("/{ebook_id}/download")
async def get_download_url(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get download URL for an active checkout."""
    client = _require_metislib()
    patron_hash = generate_patron_hash(current_user.id)
    try:
        result = await client.get_download_url(ebook_id, patron_hash)
        title = result.get("title", "") if isinstance(result, dict) else ""
        await log_ebook_event(db, current_user.id, "metislib", "download", title)
        await db.commit()
        return result
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Checkout not found") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib download error: {e}")
        raise HTTPException(status_code=502, detail="Error getting download URL") from e


@router.post("/{access_id}/return")
async def return_ebook(
    access_id: int,
    rating: Optional[int] = Query(None, ge=1, le=5),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return an ebook and optionally leave a rating."""
    client = _require_metislib()
    patron_hash = generate_patron_hash(current_user.id)
    try:
        result = await client.return_ebook(access_id, patron_hash, rating=rating)
        title = result.get("title", "") if isinstance(result, dict) else ""
        author = result.get("author", "") if isinstance(result, dict) else ""
        # If MetisLib didn't return title, look it up from the borrow log
        if not title:
            borrow_result = await db.execute(
                select(EbookCheckoutLog)
                .where(
                    EbookCheckoutLog.user_id == current_user.id,
                    EbookCheckoutLog.action == "borrow",
                )
                .order_by(EbookCheckoutLog.recorded_at.desc())
                .limit(1)
            )
            borrow_entry = borrow_result.scalar_one_or_none()
            if borrow_entry:
                title = borrow_entry.ebook_title
                author = author or borrow_entry.ebook_author
        await log_ebook_event(db, current_user.id, "metislib", "return", title, ebook_author=author)
        await db.commit()
        return result
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Checkout not found") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="Ebooks service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib return error: {e}")
        raise HTTPException(status_code=502, detail="Error returning ebook") from e
