# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Release Tracker API routes.
Handles author following, release tracking, and librarian acquisition.
"""

import asyncio
from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.acquisition import (PurchaseOrder, PurchaseOrderItem,
                                   PurchaseOrderStatus)
from ...models.catalog import CatalogItem
from ...models.inventory import ItemCopy
from ...models.release_tracker import (AgeRating, ProfileType, ReleaseSource,
                                       ReleaseStatus, TrackerAuthor, TrackerBook,
                                       UserFollow)
from ...models.user import User
from ...schemas.release_tracker import (AuthorCreate, AuthorResponse,
                                        AuthorSearchResult,
                                        AuthorSearchResultItem,
                                        AuthorSearchResultsResponse,
                                        AuthorUpdate,
                                        BookCreate, BookResponse,
                                        BookWithLibraryStatus,
                                        CreateAndFollowAuthorResponse,
                                        CreatePOFromReleasesRequest,
                                        CreatePOFromReleasesResponse,
                                        FeatureUpdateRequest,
                                        FollowCreate, FollowedAuthorItem,
                                        FollowedAuthorsResponse, FollowResponse,
                                        FeaturedUpcomingItem,
                                        FeaturedUpcomingResponse,
                                        FollowUpdate, IngestEditorialRequest,
                                        IngestionStats,
                                        LibrarianReleaseItem,
                                        LibrarianReleasesResponse,
                                        RefreshAllRequest,
                                        RefreshAuthorRequest, ReleaseFeedItem,
                                        ReleaseFeedResponse,
                                        StaffAuthorsResponse)
from ...services.google_books_fetcher import GoogleBooksFetcher
from ...services.release_ingestion import ReleaseIngestionService
from .auth import get_current_user
from .dependencies import check_staff_access, check_admin_access

router = APIRouter(prefix="/releases", tags=["releases"])


# ============ Author Search & Discovery ============


@router.get("/authors/search", response_model=AuthorSearchResultsResponse)
async def search_authors(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search for authors to follow.
    Searches both local database and external APIs.
    """
    results: list[AuthorSearchResultItem] = []
    safe_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    # Search local authors first
    local_query = (
        select(TrackerAuthor)
        .options(selectinload(TrackerAuthor.followers))
        .where(TrackerAuthor.name.ilike(f"%{safe_q}%"))
        .limit(10)
    )
    local_result = await db.execute(local_query)
    local_authors = local_result.scalars().all()

    for author in local_authors:
        results.append(
            AuthorSearchResultItem(
                id=str(author.id),
                name=author.name,
                source="local",
                follower_count=author.follower_count,
                image_url=author.image_url,
            )
        )

    # Search Google Books for more
    if len(results) < 10:
        try:
            fetcher = GoogleBooksFetcher()
            external = await fetcher.search_authors(q, max_results=10 - len(results))
            for ext_author in external:
                # Check if already in results
                if not any(
                    r.name.lower() == ext_author.name.lower() for r in results
                ):
                    results.append(
                        AuthorSearchResultItem(
                            id=None,
                            name=ext_author.name,
                            source="google_books",
                            source_id=ext_author.source_id,
                            follower_count=0,
                            image_url=ext_author.image_url,
                        )
                    )
        except Exception:  # noqa: BLE001  # external author search best-effort — fail silently
            pass  # Fail silently on external search

    return AuthorSearchResultsResponse(results=results)


@router.get("/authors", response_model=FollowedAuthorsResponse)
async def list_followed_authors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List authors the current user follows"""
    query = (
        select(UserFollow)
        .where(UserFollow.user_id == current_user.id)
        .options(selectinload(UserFollow.author))
    )
    result = await db.execute(query)
    follows = result.scalars().all()

    items: list[FollowedAuthorItem] = []
    for follow in follows:
        if follow.author:
            items.append(
                FollowedAuthorItem(
                    follow_id=follow.id,
                    author=AuthorResponse.model_validate(follow.author),
                    profile_type=(
                        str(follow.profile_type) if follow.profile_type else "parent"
                    ),
                    notify_on_release=follow.notify_on_release,
                )
            )

    return FollowedAuthorsResponse(items=items, total=len(items))


@router.post("/authors/{author_id}/follow", response_model=FollowResponse, status_code=status.HTTP_201_CREATED)
async def follow_author(
    author_id: UUID,
    follow_in: FollowCreate | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Follow an author"""
    # Check if author exists
    await get_or_404(db, TrackerAuthor, author_id, "Author not found")

    # Check for existing follow
    existing = await db.execute(
        select(UserFollow).where(
            UserFollow.user_id == current_user.id,
            UserFollow.author_id == author_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already following this author")

    # Create follow
    follow_data = follow_in.model_dump() if follow_in else {}
    follow_data["author_id"] = author_id
    follow = UserFollow(user_id=current_user.id, **follow_data)
    db.add(follow)
    await db.commit()

    # Re-fetch with author + author.followers eager-loaded so the response
    # model can serialize FollowResponse.author -> AuthorResponse.follower_count
    # without hitting MissingGreenlet at Pydantic validation.
    result = await db.execute(
        select(UserFollow)
        .options(selectinload(UserFollow.author).selectinload(TrackerAuthor.followers))
        .where(UserFollow.id == follow.id)
    )
    return result.scalar_one()


@router.delete("/authors/{author_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_author(
    author_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unfollow an author"""
    result = await db.execute(
        select(UserFollow).where(
            UserFollow.user_id == current_user.id,
            UserFollow.author_id == author_id,
        )
    )
    follow = result.scalar_one_or_none()

    if not follow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not following this author")

    await db.delete(follow)
    await db.commit()

    return None


@router.get("/authors/create-and-follow", response_model=dict)
async def get_create_follow_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get information about creating and following authors."""
    return {
        "supported_sources": ["google_books", "manual"],
        "profile_types": ["parent", "contributor", "publisher"],
        "requires_name": True,
        "google_id_optional": True,
    }


@router.post("/authors/create-and-follow", response_model=CreateAndFollowAuthorResponse, status_code=status.HTTP_201_CREATED)
async def create_and_follow_author(
    name: str = Query(...),
    google_id: str | None = Query(None),
    profile_type: str = Query("parent"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new author from external source and follow them"""
    # Check if author already exists. selectinload followers so the
    # AuthorResponse.follower_count @property doesn't lazy-touch a
    # relationship outside the greenlet context at serialization.
    existing = await db.execute(
        select(TrackerAuthor)
        .options(selectinload(TrackerAuthor.followers))
        .where(
            or_(
                TrackerAuthor.name.ilike(name),
                TrackerAuthor.google_id == google_id if google_id else False,
            )
        )
    )
    author = existing.scalar_one_or_none()

    if not author:
        # Create new author
        author = TrackerAuthor(
            name=name,
            google_id=google_id,
        )
        db.add(author)
        await db.commit()
        # Re-fetch with followers eager-loaded.
        refetch = await db.execute(
            select(TrackerAuthor)
            .options(selectinload(TrackerAuthor.followers))
            .where(TrackerAuthor.id == author.id)
        )
        author = refetch.scalar_one()

    # Follow the author
    check_follow = await db.execute(
        select(UserFollow).where(
            UserFollow.user_id == current_user.id,
            UserFollow.author_id == author.id,
        )
    )
    if not check_follow.scalar_one_or_none():
        follow = UserFollow(
            user_id=current_user.id,
            author_id=author.id,
            profile_type=ProfileType(profile_type),
        )
        db.add(follow)
        await db.commit()

    return CreateAndFollowAuthorResponse(
        author=AuthorResponse.model_validate(author),
        status="following",
    )


# ============ Patron Release Feed ============


@router.get("/my-releases", response_model=ReleaseFeedResponse)
async def get_my_releases(
    profile: str | None = Query(None),  # "parent" or "child"
    status: str | None = Query(None),  # "upcoming", "released"
    days_ahead: int = Query(365, ge=1, le=730),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get upcoming releases from followed authors.

    If profile="child", filters out ADULT age_rating.
    """
    # Get followed author IDs
    follows_query = select(UserFollow.author_id).where(
        UserFollow.user_id == current_user.id
    )

    # Build books query
    query = (
        select(TrackerBook)
        .where(TrackerBook.author_id.in_(follows_query))
        .options(selectinload(TrackerBook.author))
    )

    # Filter by profile (child = no adult content)
    if profile == "child":
        query = query.where(TrackerBook.age_rating != AgeRating.ADULT)

    # Filter by status
    if status:
        query = query.where(TrackerBook.status == ReleaseStatus(status))
    else:
        # Default: show upcoming and recently released
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        query = query.where(
            or_(
                TrackerBook.status == ReleaseStatus.UPCOMING,
                and_(
                    TrackerBook.status == ReleaseStatus.RELEASED,
                    TrackerBook.release_date >= thirty_days_ago,
                ),
            )
        )

    # Filter by date range
    today = date.today()
    future_cutoff = today + timedelta(days=days_ahead)
    query = query.where(
        or_(
            TrackerBook.release_date.is_(None),
            TrackerBook.release_date <= future_cutoff,
        )
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate and sort
    offset = (page - 1) * per_page
    query = (
        query.order_by(TrackerBook.release_date.asc().nullslast())
        .offset(offset)
        .limit(per_page)
    )

    result = await db.execute(query)
    books = result.scalars().all()

    items = []
    for book in books:
        days_until = None
        if book.release_date:
            delta = (book.release_date - today).days
            days_until = delta if delta > 0 else 0

        items.append(
            ReleaseFeedItem(
                book=BookResponse.model_validate(book),
                author=(
                    AuthorResponse.model_validate(book.author) if book.author else None
                ),
                days_until_release=days_until,
                is_followed=True,
            )
        )

    return ReleaseFeedResponse(items=items, total=total)


@router.get("/featured-upcoming", response_model=FeaturedUpcomingResponse)
async def get_featured_upcoming(
    age_rating: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(TrackerBook)
        .options(selectinload(TrackerBook.author))
        .where(TrackerBook.is_featured.is_(True))
        .where(TrackerBook.status == ReleaseStatus.UPCOMING.value)
    )
    if age_rating:
        query = query.where(TrackerBook.age_rating == AgeRating(age_rating).value)
    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            query.order_by(TrackerBook.release_date.asc().nullslast())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()
    items = []
    for book in rows:
        items.append(
            FeaturedUpcomingItem(
                tracker_book_id=book.id,
                title=book.title,
                author_name=book.author.name if book.author else None,
                isbn_13=book.isbn_13,
                release_date=book.release_date,
                is_date_exact=book.is_date_exact,
                source=book.source,
                source_url=book.source_url,
                blurb=book.blurb,
                blurb_credit=book.blurb_credit,
                library_status=await _get_library_status(db, book.isbn_13),
                catalog_item_id=await _get_catalog_id(db, book.isbn_13),
            )
        )
    return FeaturedUpcomingResponse(
        items=items, total=total, page=page, per_page=per_page
    )


# ============ Librarian Endpoints ============


@router.get("/librarian/releases", response_model=LibrarianReleasesResponse)
async def get_librarian_releases(
    status: str | None = Query(None),
    library_status: str | None = Query(None),  # "new", "owned", "on_order"
    age_rating: str | None = Query(None),
    source: str | None = Query(None, description="Filter by provenance: author_scan|libraryreads|lj_prepub|editorial_rss"),
    min_demand: int = Query(0, ge=0),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get releases for librarian acquisition view.
    Includes library status and demand scores.
    """
    check_staff_access(current_user)

    # Base query for upcoming releases
    query = select(TrackerBook).options(selectinload(TrackerBook.author))

    if status:
        query = query.where(TrackerBook.status == ReleaseStatus(status))
    else:
        query = query.where(TrackerBook.status == ReleaseStatus.UPCOMING)

    if age_rating:
        query = query.where(TrackerBook.age_rating == AgeRating(age_rating))

    if source is not None:
        if source not in {s.value for s in ReleaseSource}:
            raise HTTPException(status_code=422, detail=f"Invalid source: {source}")
        query = query.where(TrackerBook.source == source)

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = (
        query.order_by(TrackerBook.release_date.asc().nullslast())
        .offset(offset)
        .limit(per_page)
    )

    result = await db.execute(query)
    books = result.scalars().all()

    items = []
    for book in books:
        # Calculate library status
        lib_status = await _get_library_status(db, book.isbn_13)

        # Calculate demand score (follower count for this author)
        demand = await _get_demand_score(db, book.author_id)

        # Filter by library status if requested
        if library_status and lib_status != library_status:
            continue

        # Filter by minimum demand
        if demand < min_demand:
            continue

        items.append(
            LibrarianReleaseItem(
                book=BookResponse.model_validate(book),
                author_name=book.author.name if book.author else "Unknown",
                library_status=lib_status,
                demand_score=demand,
                catalog_item_id=await _get_catalog_id(db, book.isbn_13),
            )
        )

    return LibrarianReleasesResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.patch("/librarian/{tracker_book_id}/feature", response_model=BookResponse)
async def set_book_featured(
    tracker_book_id: UUID,
    payload: FeatureUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_staff_access(current_user)
    book = await get_or_404(db, TrackerBook, tracker_book_id, "Release not found")
    book.is_featured = payload.is_featured
    await db.commit()
    result = await db.execute(
        select(TrackerBook)
        .where(TrackerBook.id == tracker_book_id)
        .options(selectinload(TrackerBook.author))
    )
    book = result.scalar_one()
    return BookResponse.model_validate(book)


@router.post("/librarian/create-po", response_model=CreatePOFromReleasesResponse, status_code=status.HTTP_201_CREATED)
async def create_po_from_releases(
    request: CreatePOFromReleasesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a purchase order from tracked releases.

    Promotion Logic:
    1. For each book, check if ISBN exists in CatalogItem
    2. If not, create CatalogItem from TrackerBook data
    3. Create/use PurchaseOrder and add items
    """
    check_staff_access(current_user)

    # Find or create draft PO
    po = None
    if request.use_existing_draft:
        result = await db.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.vendor_id == request.vendor_id,
                PurchaseOrder.fund_id == request.fund_id,
                PurchaseOrder.status == PurchaseOrderStatus.DRAFT,
                PurchaseOrder.created_by_id == current_user.id,
            )
        )
        po = result.scalar_one_or_none()

    if not po:
        # Generate PO number
        today = date.today()
        count_result = await db.execute(
            select(func.count(PurchaseOrder.id)).where(
                PurchaseOrder.created_at >= datetime(today.year, today.month, 1)
            )
        )
        count = (count_result.scalar() or 0) + 1
        po_number = f"PO-{today.strftime('%Y%m')}-{count:04d}"

        po = PurchaseOrder(
            po_number=po_number,
            vendor_id=request.vendor_id,
            fund_id=request.fund_id,
            status=PurchaseOrderStatus.DRAFT,
            created_by_id=current_user.id,
        )
        db.add(po)
        await db.flush()

    items_added = 0
    catalog_items_created = 0

    for book_id in request.tracker_book_ids:
        # Get the tracker book
        result = await db.execute(
            select(TrackerBook)
            .where(TrackerBook.id == book_id)
            .options(selectinload(TrackerBook.author))
        )
        book = result.scalar_one_or_none()

        if not book:
            continue

        # Promotion: Create catalog item if needed
        catalog_item = None
        if book.isbn_13:
            result = await db.execute(
                select(CatalogItem).where(CatalogItem.isbn == book.isbn_13)
            )
            catalog_item = result.scalar_one_or_none()

        if not catalog_item:
            catalog_item = CatalogItem(
                title=book.title,
                author=book.author.name if book.author else None,
                isbn=book.isbn_13,
                publisher=book.publisher,
                publication_year=book.release_date.year if book.release_date else None,
                description=book.description,
                cover_url=book.cover_url,
            )
            db.add(catalog_item)
            await db.flush()
            catalog_items_created += 1

        # Add PO item
        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            title=book.title,
            author=book.author.name if book.author else None,
            isbn=book.isbn_13,
            quantity=1,
            unit_price=book.list_price or 0,
            catalog_item_id=catalog_item.id,
        )
        db.add(po_item)
        items_added += 1

    # Update PO total
    await db.flush()
    result = await db.execute(
        select(
            func.sum(PurchaseOrderItem.quantity * PurchaseOrderItem.unit_price)
        ).where(PurchaseOrderItem.purchase_order_id == po.id)
    )
    po.total_amount = result.scalar() or 0

    await db.commit()

    return CreatePOFromReleasesResponse(
        purchase_order_id=po.id,
        po_number=po.po_number,
        items_added=items_added,
        catalog_items_created=catalog_items_created,
    )


@router.post("/librarian/ingest-editorial", response_model=IngestionStats)
async def ingest_editorial(
    request: IngestEditorialRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ingest forthcoming titles from an editorial connector (not author-driven)."""
    check_staff_access(current_user)
    from app.services.editorial_release_ingestion import EditorialReleaseIngestionService
    from app.services.release_sources.libraryreads_source import LibraryReadsSource
    from app.services.release_sources.lj_prepub_source import LJPrepubSource

    if request.source == ReleaseSource.LIBRARYREADS.value:
        titles = await LibraryReadsSource().fetch(month=request.month)
    elif request.source == ReleaseSource.LJ_PREPUB.value:
        if not request.sheet_id:
            raise HTTPException(status_code=400, detail="sheet_id is required for lj_prepub")
        titles = await LJPrepubSource().fetch_from_sheet_id(request.sheet_id)
    elif request.source in (ReleaseSource.INDIE_MASTODON.value, ReleaseSource.INDIE_ITCHIO.value):
        # Module import (not function) so tests can monkeypatch ingest_indie at call time;
        # the coordinator commits its own dedup marks, so return its stats directly.
        from app.services import indie_release_ingestion

        return await indie_release_ingestion.ingest_indie(db, sources=[request.source])
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported source: {request.source}")

    service = EditorialReleaseIngestionService(db)
    return await service.ingest(titles)


@router.post("/librarian/refresh-author/{author_id}", response_model=IngestionStats)
async def refresh_author(
    author_id: UUID,
    request: RefreshAuthorRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually refresh an author's books from external sources"""
    check_staff_access(current_user)

    service = ReleaseIngestionService(db)
    stats = await service.process_author(author_id)
    await db.commit()

    return stats


@router.post("/librarian/refresh-all")
async def refresh_all_authors(
    background_tasks: BackgroundTasks,
    request: RefreshAllRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Refresh all tracked authors (admin only).

    This operation runs in the background as it may take several minutes
    to fetch data from external APIs for all authors.
    """
    check_admin_access(current_user)

    force = request.force if request else False

    # Run in background to avoid blocking the request
    async def _refresh_all_in_background(force: bool):
        from ...core.database import AsyncSessionLocal
        from ...core.logging import get_logger
        logger = get_logger(__name__)

        try:
            async with AsyncSessionLocal() as bg_db:
                service = ReleaseIngestionService(bg_db)
                stats = await service.process_all_authors(force=force)
                logger.info(
                    "Background author refresh completed",
                    extra={
                        "authors_processed": stats.authors_processed,
                        "books_added": stats.books_added,
                        "books_updated": stats.books_updated,
                    }
                )
        except Exception as e:
            logger.error(f"Background author refresh failed: {e}", exc_info=True)

    background_tasks.add_task(asyncio.create_task, _refresh_all_in_background(force))

    return {
        "status": "started",
        "message": "Author refresh started in background. Check logs for progress.",
    }


# ============ Staff Author Management ============


@router.post("/staff/authors", response_model=AuthorResponse, status_code=status.HTTP_201_CREATED)
async def create_author(
    author_in: AuthorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new author to track"""
    check_staff_access(current_user)

    author = TrackerAuthor(**author_in.model_dump())
    db.add(author)
    await db.commit()
    await db.refresh(author)

    return author


@router.get("/staff/authors", response_model=StaffAuthorsResponse)
async def list_all_authors(
    q: str | None = Query(None),
    active_only: bool = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all tracked authors (staff view)"""
    check_staff_access(current_user)

    query = select(TrackerAuthor).options(selectinload(TrackerAuthor.followers))

    if active_only:
        query = query.where(TrackerAuthor.is_active == True)

    if q:
        safe_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(TrackerAuthor.name.ilike(f"%{safe_q}%"))

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.order_by(TrackerAuthor.name).offset(offset).limit(per_page)

    result = await db.execute(query)
    authors = result.scalars().all()

    return StaffAuthorsResponse(
        items=[AuthorResponse.model_validate(a) for a in authors],
        total=total,
        page=page,
        per_page=per_page,
    )


# ============ Helper Functions ============


async def _get_library_status(db: AsyncSession, isbn: str | None) -> str:
    if not isbn:
        return "new"

    # Check if in inventory
    result = await db.execute(
        select(
            exists().where(
                and_(
                    CatalogItem.isbn == isbn,
                    ItemCopy.catalog_item_id == CatalogItem.id,
                )
            )
        )
    )
    if result.scalar():
        return "owned"

    # Check if on order
    result = await db.execute(
        select(
            exists().where(
                and_(
                    PurchaseOrderItem.isbn == isbn,
                    PurchaseOrder.id == PurchaseOrderItem.purchase_order_id,
                    PurchaseOrder.status.in_(
                        [
                            PurchaseOrderStatus.DRAFT,
                            PurchaseOrderStatus.PENDING_APPROVAL,
                            PurchaseOrderStatus.APPROVED,
                            PurchaseOrderStatus.SUBMITTED,
                        ]
                    ),
                )
            )
        )
    )
    if result.scalar():
        return "on_order"

    return "new"


async def _get_demand_score(db: AsyncSession, author_id: UUID) -> int:
    result = await db.execute(
        select(func.count(UserFollow.id)).where(UserFollow.author_id == author_id)
    )
    return result.scalar() or 0


async def _get_catalog_id(db: AsyncSession, isbn: str | None) -> int | None:
    if not isbn:
        return None

    result = await db.execute(
        select(CatalogItem.id).where(CatalogItem.isbn == isbn).limit(1)
    )
    return result.scalars().first()


# Import timedelta at top
from datetime import timedelta


@router.get("/librarian/create-po")
async def get_librarian_create_po(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get information about creating purchase orders from releases.

    Returns metadata about the create-po endpoint including:
    - Required fields
    - Available vendors
    - Available funds
    - Draft PO status
    """
    check_staff_access(current_user)

    # Get available vendors
    from ...models.acquisition import Vendor
    vendors_result = await db.execute(
        select(Vendor).where(Vendor.is_active == True).order_by(Vendor.name)
    )
    vendors = vendors_result.scalars().all()

    # Get available funds
    from ...models.acquisition import Fund
    funds_result = await db.execute(
        select(Fund).where(Fund.is_active == True).order_by(Fund.name)
    )
    funds = funds_result.scalars().all()

    # Get draft POs for this user
    draft_pos_result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.created_by_id == current_user.id,
            PurchaseOrder.status == PurchaseOrderStatus.DRAFT,
        )
    )
    draft_pos = draft_pos_result.scalars().all()

    return {
        "endpoint": "POST /releases/librarian/create-po",
        "description": "Create purchase order from tracked releases",
        "required_fields": ["tracker_book_ids", "vendor_id", "fund_id"],
        "optional_fields": ["use_existing_draft"],
        "available_vendors": [{"id": v.id, "name": v.name} for v in vendors],
        "available_funds": [{"id": f.id, "name": f.name, "balance": str(f.balance)} for f in funds],
        "draft_pos": [{"id": po.id, "po_number": po.po_number, "total_amount": str(po.total_amount)} for po in draft_pos],
    }



@router.get("/librarian/refresh-all")
async def get_librarian_refresh_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get information about the refresh-all authors operation.

    Returns metadata about tracked authors and last refresh times.
    """
    check_admin_access(current_user)

    # Count tracked authors
    author_count_result = await db.execute(
        select(func.count(TrackerAuthor.id)).where(TrackerAuthor.is_active == True)
    )
    active_author_count = author_count_result.scalar() or 0

    # Get recently updated authors
    recent_updates_result = await db.execute(
        select(TrackerAuthor)
        .options(selectinload(TrackerAuthor.books))
        .where(TrackerAuthor.last_scanned_at.isnot(None))
        .order_by(TrackerAuthor.last_scanned_at.desc())
        .limit(5)
    )
    recent_updates = recent_updates_result.scalars().all()

    return {
        "endpoint": "POST /releases/librarian/refresh-all",
        "description": "Refresh all tracked authors from external APIs",
        "method": "POST",
        "required_permission": "admin",
        "runs_in_background": True,
        "active_author_count": active_author_count,
        "optional_fields": ["force"],
        "force_description": "If true, refresh all authors regardless of last fetch time",
        "recent_updates": [
            {
                "author_name": a.name,
                "last_fetched": a.last_scanned_at.isoformat() if a.last_scanned_at else None,
                "book_count": a.book_count,
            }
            for a in recent_updates
        ],
    }



@router.get("/librarian/refresh-author/{author_id}")
async def get_librarian_refresh_author_info(
    author_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get information about refreshing a specific author.

    Returns author details and last refresh status.
    """
    check_staff_access(current_user)

    # Get author details (eager-load for book_count + follower_count properties)
    author_result = await db.execute(
        select(TrackerAuthor)
        .options(
            selectinload(TrackerAuthor.books),
            selectinload(TrackerAuthor.followers),
        )
        .where(TrackerAuthor.id == author_id)
    )
    author = author_result.scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    return {
        "endpoint": f"POST /releases/librarian/refresh-author/{author_id}",
        "description": "Manually refresh author's books from external sources",
        "method": "POST",
        "author": {
            "id": str(author.id),
            "name": author.name,
            "google_id": author.google_id,
            "book_count": author.book_count,
            "follower_count": author.follower_count,
            "last_fetched_at": author.last_scanned_at.isoformat() if author.last_scanned_at else None,
            "is_active": author.is_active,
        },
        "optional_fields": [],
        "notes": "This will fetch latest books from external APIs (Google Books, etc.)",
    }

