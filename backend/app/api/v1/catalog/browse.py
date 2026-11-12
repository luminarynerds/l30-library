# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import case, func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.cache import (
    get_cached,
    make_cache_key,
    set_cached,
)
from ....core.database import get_db
from ....core.pagination_config import PaginationDefaults
from ....core.rate_limit import limiter
from ....models.catalog import CatalogItem, ItemStatus, ItemType, CatalogingStatus, SensitivityLevel
from ....models.inventory import ItemCopy
from ....models.circulation import Checkout, CheckoutStatus
from ....models.user import User, UserRole
from ....schemas.catalog import (
    CatalogItemResponse,
    CatalogNewArrivalsResponse,
    CatalogPaginatedResponse,
    CatalogRandomResponse,
    SeriesMemberResponse,
    SeriesReadingOrderResponse,
    SuggestResponse,
)
from ..auth import get_current_user, get_optional_user
from ..dependencies import is_staff_or_admin
from .helpers import _escape_ilike, _execute_catalog_search, _get_catalog_item_with_images

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=CatalogPaginatedResponse)
@limiter.limit("60/minute")
async def list_catalog_root(
    request: Request,
    q: str | None = Query(None, description="Search query - searches title, author, description, subjects"),
    title: str | None = Query(None, description="Filter by title (partial match)"),
    author: str | None = Query(None, description="Filter by author (partial match)"),
    subject: str | None = Query(None, description="Filter by subject (partial match)"),
    publication_year: int | None = Query(None, description="Filter by exact publication year"),
    item_type: ItemType | None = Query(None),
    status: ItemStatus | None = Query(None),
    year_min: int | None = Query(None, description="Minimum publication year"),
    year_max: int | None = Query(None, description="Maximum publication year"),
    location: str | None = Query(None, description="Filter by location"),
    cataloging_status: CatalogingStatus | None = Query(None, description="Filter by cataloging status"),
    sensitivity_level: SensitivityLevel | None = Query(None, description="Filter by sensitivity level"),
    is_new: bool = Query(False, description="Show only new arrivals (last 30 days)"),
    is_large_print: bool | None = Query(None, description="Filter by large print editions"),
    language: list[str] = Query(default=[], description="Filter by BIBFRAME work language (ISO 639-2/B code, e.g. eng, spa). Multi-select, OR within group. Max 20."),
    sort_by: str | None = Query(None, description="Sort by field: relevance, title, author, year"),
    sort_direction: str | None = Query(None, description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    include_facets: bool = Query(False, description="Include facet counts in response"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """List all catalog items with optional filtering. Root endpoint - delegates to shared search logic."""
    if len(language) > 20:
        raise HTTPException(status_code=400, detail="language is capped at 20 entries per request")
    return await _execute_catalog_search(
        db=db, q=q, title=title, author=author, subject=subject,
        publication_year=publication_year, item_type=item_type, status=status,
        year_min=year_min, year_max=year_max, location=location,
        cataloging_status=cataloging_status, sensitivity_level=sensitivity_level,
        is_new=is_new, is_large_print=is_large_print,
        language=language or None,
        sort_by=sort_by, sort_direction=sort_direction,
        page=page, per_page=per_page, current_user=current_user,
        include_facets=include_facets,
    )


@router.get("/browse", response_model=CatalogPaginatedResponse)
@limiter.limit("60/minute")
async def browse_catalog(
    request: Request,
    q: str | None = Query(None, description="Search query"),
    subject: str | None = Query(None, description="Filter by subject"),
    author: str | None = Query(None, description="Filter by author"),
    item_type: ItemType | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Browse catalog with simple filters. Alias for the main catalog search."""
    return await _execute_catalog_search(
        db=db, q=q, title=None, author=author, subject=subject,
        publication_year=None, item_type=item_type, status=None,
        year_min=None, year_max=None, location=None,
        cataloging_status=None, sensitivity_level=None,
        is_new=False, is_large_print=None,
        sort_by=None, sort_direction=None,
        page=page, per_page=per_page, current_user=current_user,
        include_facets=False,
    )


@router.get("/items", response_model=CatalogPaginatedResponse)
@limiter.limit("60/minute")
async def list_catalog_items(
    request: Request,
    q: str | None = Query(None, description="Search query - searches title, author, description, subjects"),
    title: str | None = Query(None, description="Filter by title (partial match)"),
    author: str | None = Query(None, description="Filter by author (partial match)"),
    subject: str | None = Query(None, description="Filter by subject (partial match)"),
    publication_year: int | None = Query(None, description="Filter by exact publication year"),
    item_type: ItemType | None = Query(None),
    status: ItemStatus | None = Query(None),
    year_min: int | None = Query(None, description="Minimum publication year"),
    year_max: int | None = Query(None, description="Maximum publication year"),
    location: str | None = Query(None, description="Filter by location"),
    cataloging_status: CatalogingStatus | None = Query(None, description="Filter by cataloging status (cataloged, uncataloged, in_progress)"),
    sensitivity_level: SensitivityLevel | None = Query(None, description="Filter by sensitivity level (public, sensitive, confidential)"),
    is_new: bool = Query(False, description="Show only new arrivals (last 30 days)"),
    is_large_print: bool | None = Query(None, description="Filter by large print editions"),
    language: list[str] = Query(default=[], description="Filter by BIBFRAME work language (ISO 639-2/B code). Multi-select. Max 20."),
    sort_by: str | None = Query(None, description="Sort by field: relevance, title, author, year"),
    sort_direction: str | None = Query(None, description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    include_facets: bool = Query(False, description="Include facet counts in response"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """List all catalog items with optional filtering."""
    if len(language) > 20:
        raise HTTPException(status_code=400, detail="language is capped at 20 entries per request")
    return await _execute_catalog_search(
        db=db, q=q, title=title, author=author, subject=subject,
        publication_year=publication_year, item_type=item_type, status=status,
        year_min=year_min, year_max=year_max, location=location,
        cataloging_status=cataloging_status, sensitivity_level=sensitivity_level,
        is_new=is_new, is_large_print=is_large_print,
        language=language or None,
        sort_by=sort_by, sort_direction=sort_direction,
        page=page, per_page=per_page, current_user=current_user,
        include_facets=include_facets,
    )


@router.get("/books", response_model=CatalogPaginatedResponse)
@limiter.limit("60/minute")
async def list_books(
    request: Request,
    q: str | None = Query(None, description="Search query"),
    status: ItemStatus | None = Query(None),
    year_min: int | None = Query(None, description="Minimum publication year"),
    year_max: int | None = Query(None, description="Maximum publication year"),
    location: str | None = Query(None, description="Filter by location"),
    is_new: bool = Query(False, description="Show only new arrivals (last 30 days)"),
    is_large_print: bool | None = Query(None, description="Filter by large print editions"),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    List books from the catalog.

    Convenience endpoint that filters to item_type=book.
    Delegates to the shared search path so role-based visibility rules
    (sensitivity_level, cataloging_status) apply exactly as on /items.
    """
    return await _execute_catalog_search(
        db=db,
        q=q,
        status=status,
        year_min=year_min,
        year_max=year_max,
        location=location,
        is_new=is_new,
        is_large_print=is_large_print,
        item_type=ItemType.book,
        page=page,
        per_page=per_page,
        current_user=current_user,
    )


@router.get("/materials", response_model=CatalogPaginatedResponse)
@limiter.limit("60/minute")
async def list_materials(
    request: Request,
    type: str | None = Query(None, description="Material type (dvd, bluray, cd, vinyl, etc.)"),
    q: str | None = Query(None, description="Search query"),
    status: ItemStatus | None = Query(None),
    year_min: int | None = Query(None, description="Minimum publication year"),
    year_max: int | None = Query(None, description="Maximum publication year"),
    location: str | None = Query(None, description="Filter by location"),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    List non-book materials (DVDs, Blu-rays, CDs, vinyl records, etc.).

    Query parameter 'type' allows filtering by specific material type.
    If no type is specified, returns all non-book items.
    Delegates to the shared search path so role-based visibility rules
    (sensitivity_level, cataloging_status) apply exactly as on /items.
    """
    # Validate type if provided
    material_types = [
        ItemType.dvd, ItemType.bluray, ItemType.cd,
        ItemType.vinyl, ItemType.audiobook, ItemType.ebook,
        ItemType.magazine, ItemType.game, ItemType.equipment, ItemType.kit
    ]

    selected_type = None
    if type:
        try:
            selected_type = ItemType(type)
            if selected_type not in material_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid material type: {type}. Use one of: {', '.join([t.value for t in material_types])}"
                )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid material type: {type}. Use one of: {', '.join([t.value for t in material_types])}"
            ) from None

    return await _execute_catalog_search(
        db=db,
        q=q,
        status=status,
        year_min=year_min,
        year_max=year_max,
        location=location,
        item_type=selected_type,
        # No type selected -> all non-book items (incl. tool/other), matching
        # the endpoint's original contract.
        item_types=None if selected_type else [t for t in ItemType if t != ItemType.book],
        page=page,
        per_page=per_page,
        current_user=current_user,
    )


@router.get("/search", response_model=CatalogPaginatedResponse)
@limiter.limit("60/minute")
async def search_catalog(
    request: Request,
    q: str | None = Query(None, description="Search query - searches title, author, description, subjects"),
    title: str | None = Query(None, description="Filter by title (partial match)"),
    author: str | None = Query(None, description="Filter by author (partial match)"),
    subject: str | None = Query(None, description="Filter by subject (partial match, legacy)"),
    subject_facets: list[str] = Query(
        default=[],
        description="Exact-match subject labels (multi-select, OR within group). Max 20.",
    ),
    author_facets: list[str] = Query(
        default=[],
        description="Exact-match author names (multi-select, OR within group). Max 20.",
    ),
    series_facets: list[str] = Query(
        default=[],
        description="Exact-match series names (multi-select, OR within group). Max 20.",
    ),
    publication_year: int | None = Query(None, description="Filter by exact publication year"),
    item_type: ItemType | None = Query(None),
    item_types: list[ItemType] = Query(
        default=[],
        description=(
            "Filter by item type (multi-select, OR within group). Use in "
            "place of item_type to match several types in one request, e.g. "
            "item_types=dvd&item_types=bluray."
        ),
    ),
    status: ItemStatus | None = Query(None),
    year_min: int | None = Query(None, description="Minimum publication year"),
    year_max: int | None = Query(None, description="Maximum publication year"),
    min_lexile: int | None = Query(None, ge=-400, le=2000, description="Min Lexile (inclusive)"),
    max_lexile: int | None = Query(None, ge=-400, le=2000, description="Max Lexile (inclusive)"),
    location: str | None = Query(None, description="Filter by location"),
    cataloging_status: CatalogingStatus | None = Query(None, description="Filter by cataloging status"),
    sensitivity_level: SensitivityLevel | None = Query(None, description="Filter by sensitivity level"),
    is_new: bool = Query(False, description="Show only new arrivals (last 30 days)"),
    is_large_print: bool | None = Query(None, description="Filter by large print editions"),
    available_for_hold: bool | None = Query(
        None,
        description=(
            "Filter by holdability derived from item status. When true, returns "
            "only items where placing a hold is meaningful (i.e. not lost, "
            "withdrawn, missing, reference, or restricted). When false, returns "
            "only items in those non-holdable statuses. Omit to return all."
        ),
    ),
    language: list[str] = Query(default=[], description="Filter by BIBFRAME work language (ISO 639-2/B code, e.g. eng, spa). Multi-select. Max 20."),
    sort_by: str | None = Query(None, description="Sort by field: relevance, title, author, year"),
    sort_direction: str | None = Query(None, description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    include_facets: bool = Query(False, description="Include facet counts in response"),
    rerank: bool = Query(
        False,
        description=(
            "When true and the server-side rerank flag is enabled, rerank "
            "the top FTS candidates with a cross-encoder model. Only takes "
            "effect with sort_by=relevance and a non-empty FTS query."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Search catalog items with filtering, caching, and role-based access control.

    The ``available_for_hold`` filter mirrors the response field of the same
    name (computed from ``status``) and is intended for UX rails that only
    want to surface titles a patron can actually place a hold on, such as
    the event-detail "Bring the book" rail.
    """
    if min_lexile is not None and max_lexile is not None and min_lexile > max_lexile:
        raise HTTPException(status_code=400, detail="min_lexile cannot exceed max_lexile")
    if len(language) > 20:
        raise HTTPException(status_code=400, detail="language is capped at 20 entries per request")
    if len(subject_facets) > 20:
        raise HTTPException(
            status_code=400,
            detail="subject_facets is capped at 20 entries per request",
        )
    if len(author_facets) > 20:
        raise HTTPException(
            status_code=400,
            detail="author_facets is capped at 20 entries per request",
        )
    if len(series_facets) > 20:
        raise HTTPException(
            status_code=400,
            detail="series_facets is capped at 20 entries per request",
        )
    return await _execute_catalog_search(
        db=db, q=q, title=title, author=author, subject=subject,
        subject_facets=subject_facets,
        author_facets=author_facets,
        series_facets=series_facets,
        publication_year=publication_year, item_type=item_type,
        item_types=item_types or None, status=status,
        year_min=year_min, year_max=year_max, location=location,
        min_lexile=min_lexile, max_lexile=max_lexile,
        cataloging_status=cataloging_status, sensitivity_level=sensitivity_level,
        is_new=is_new, is_large_print=is_large_print,
        available_for_hold=available_for_hold,
        language=language or None,
        sort_by=sort_by, sort_direction=sort_direction,
        page=page, per_page=per_page, current_user=current_user,
        include_facets=include_facets,
        rerank=rerank,
    )


@router.get("/suggest", response_model=SuggestResponse)
@limiter.limit("60/minute")
async def suggest_catalog(
    request: Request,
    q: str = Query(..., min_length=1, description="Search prefix for autocomplete"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of suggestions"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get autocomplete suggestions for catalog search.

    Returns title and author completions matching the given prefix.
    Public endpoint - no authentication required.
    """
    from ....services.catalog_search_service import catalog_search_service

    suggestions = await catalog_search_service.get_suggestions(db=db, query=q, limit=limit)
    return SuggestResponse(suggestions=suggestions)


@router.get("/barcode/{barcode}", response_model=CatalogItemResponse)
@limiter.limit("120/minute")
async def get_catalog_item_by_barcode(
    request: Request,
    barcode: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Look up a catalog item by its barcode. Used for self-checkout."""
    cache_key = make_cache_key("catalog:item:barcode", barcode=barcode, user_role=str(current_user.role) if current_user else "public")
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result

    # Two-pass lookup. CatalogItem.barcode is populated for equipment / kits
    # (the cataloging form's "barcode" field). Per-copy physical barcodes for
    # books and most regular items live on ItemCopy.barcode -- without the
    # fallback, /barcode/{bc} 404s for nearly every shelf-scanned item even
    # though everything else (visibility checks, response shape) is correct.
    result = await db.execute(
        select(CatalogItem)
        .options(selectinload(CatalogItem.images))
        .where(CatalogItem.barcode == barcode)
    )
    item = result.scalar_one_or_none()
    if item is None:
        result = await db.execute(
            select(CatalogItem)
            .options(selectinload(CatalogItem.images))
            .join(ItemCopy, ItemCopy.catalog_item_id == CatalogItem.id)
            .where(ItemCopy.barcode == barcode)
            .limit(1)
        )
        item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="No item matches that barcode. Please check the number and try again.")

    # Check visibility based on user role and item properties
    if item.cataloging_status != CatalogingStatus.CATALOGED and not (
        current_user is not None and is_staff_or_admin(current_user)
    ):
        raise HTTPException(status_code=404, detail="No item matches that barcode. Please check the number and try again.")

    # Check sensitivity level
    if not current_user:
        # Public user: only see PUBLIC items
        if item.sensitivity_level != SensitivityLevel.PUBLIC:
            raise HTTPException(status_code=404, detail="No item matches that barcode. Please check the number and try again.")
    elif current_user.role == UserRole.PATRON:
        # Patron: cannot see CONFIDENTIAL items
        if item.sensitivity_level == SensitivityLevel.CONFIDENTIAL:
            raise HTTPException(status_code=404, detail="No item matches that barcode. Please check the number and try again.")

    response_data = CatalogItemResponse.model_validate(item)

    # Calculate real availability from copies/checkouts instead of stale status field
    total_copies_q = (
        select(func.count(ItemCopy.id))
        .where(ItemCopy.catalog_item_id == item.id)
    )
    active_checkouts_q = (
        select(func.count(Checkout.id))
        .join(ItemCopy, Checkout.item_copy_id == ItemCopy.id)
        .where(ItemCopy.catalog_item_id == item.id)
        .where(Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]))
    )
    total_copies = (await db.execute(total_copies_q)).scalar() or 0
    on_loan = (await db.execute(active_checkouts_q)).scalar() or 0

    if total_copies > 0:
        available = total_copies - on_loan
        if available > 0:
            response_data.status = ItemStatus.available
        else:
            response_data.status = ItemStatus.checked_out

    await set_cached(cache_key, response_data.model_dump(), ttl_seconds=300)
    return response_data


@router.get("/items/{item_id}", response_model=CatalogItemResponse)
@limiter.limit("120/minute")
async def get_catalog_item_by_id(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Get a specific catalog item by ID."""
    cache_key = f"catalog:item:id:{item_id}:user:{str(current_user.role) if current_user else 'public'}"
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result

    item = await _get_catalog_item_with_images(db, item_id)

    # Check visibility based on user role and item properties
    if item.cataloging_status != CatalogingStatus.CATALOGED and not (
        current_user is not None and is_staff_or_admin(current_user)
    ):
        raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")

    # Check sensitivity level
    if not current_user:
        # Public user: only see PUBLIC items
        if item.sensitivity_level != SensitivityLevel.PUBLIC:
            raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")
    elif current_user.role == UserRole.PATRON:
        # Patron: cannot see CONFIDENTIAL items
        if item.sensitivity_level == SensitivityLevel.CONFIDENTIAL:
            raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")
    # STAFF and ADMIN can see all

    response_data = CatalogItemResponse.model_validate(item)

    # Calculate real availability from copies/checkouts instead of stale status field
    total_copies_q = (
        select(func.count(ItemCopy.id))
        .where(ItemCopy.catalog_item_id == item_id)
    )
    active_checkouts_q = (
        select(func.count(Checkout.id))
        .join(ItemCopy, Checkout.item_copy_id == ItemCopy.id)
        .where(ItemCopy.catalog_item_id == item_id)
        .where(Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]))
    )
    total_copies = (await db.execute(total_copies_q)).scalar() or 0
    on_loan = (await db.execute(active_checkouts_q)).scalar() or 0

    if total_copies > 0:
        available = total_copies - on_loan
        if available > 0:
            response_data.status = ItemStatus.available
        else:
            response_data.status = ItemStatus.checked_out

    await set_cached(cache_key, response_data.model_dump(), ttl_seconds=300)
    return response_data


@router.get("/items/{item_id}/availability")
@limiter.limit("60/minute")
async def get_item_branch_availability(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Get per-branch copy availability for a catalog item.

    Visibility-gated: anonymous callers only see PUBLIC + CATALOGED items.
    Without this gate, anyone could enumerate IDs and confirm branch
    presence + call number of CONFIDENTIAL or non-cataloged records.
    """
    from ....models.multi_branch import Branch, BranchItemCopy, BranchStatus

    item_q = select(
        CatalogItem.id,
        CatalogItem.call_number,
        CatalogItem.cataloging_status,
        CatalogItem.sensitivity_level,
    ).where(CatalogItem.id == item_id)
    item_row = (await db.execute(item_q)).first()
    if not item_row:
        raise HTTPException(status_code=404, detail="Item not found")

    if item_row.cataloging_status != CatalogingStatus.CATALOGED and not (
        current_user is not None and is_staff_or_admin(current_user)
    ):
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user:
        if item_row.sensitivity_level != SensitivityLevel.PUBLIC:
            raise HTTPException(status_code=404, detail="Item not found")
    elif current_user.role == UserRole.PATRON:
        if item_row.sensitivity_level == SensitivityLevel.CONFIDENTIAL:
            raise HTTPException(status_code=404, detail="Item not found")

    item_call_number = item_row.call_number
    active_statuses = [CheckoutStatus.active, CheckoutStatus.overdue]

    branch_query = (
        select(
            Branch.id.label("branch_id"),
            Branch.name.label("branch_name"),
            func.count(ItemCopy.id).label("total_copies"),
            func.count(ItemCopy.id).filter(
                ItemCopy.condition.notin_(["withdrawn", "damaged"]),
                Checkout.id.is_(None),
            ).label("available"),
        )
        .select_from(ItemCopy)
        .join(BranchItemCopy, BranchItemCopy.item_copy_id == ItemCopy.id)
        .join(Branch, Branch.id == BranchItemCopy.current_branch_id)
        .outerjoin(
            Checkout,
            (Checkout.item_copy_id == ItemCopy.id)
            & (Checkout.status.in_(active_statuses)),
        )
        .where(
            ItemCopy.catalog_item_id == item_id,
            Branch.status == BranchStatus.ACTIVE,
        )
        .group_by(Branch.id, Branch.name)
        .order_by(Branch.name.collate("und-x-icu"))
    )

    rows = (await db.execute(branch_query)).all()

    if rows:
        return [
            {
                "branch_id": r.branch_id,
                "branch_name": r.branch_name,
                "total_copies": r.total_copies,
                "available": r.available,
                "call_number": item_call_number,
            }
            for r in rows
        ]

    sep = " - "
    loc_query = (
        select(
            func.split_part(ItemCopy.location, sep, 1).label("branch_name"),
            func.count(ItemCopy.id).label("total_copies"),
            func.count(ItemCopy.id).filter(
                ItemCopy.condition.notin_(["withdrawn", "damaged"]),
                Checkout.id.is_(None),
            ).label("available"),
        )
        .select_from(ItemCopy)
        .outerjoin(
            Checkout,
            (Checkout.item_copy_id == ItemCopy.id)
            & (Checkout.status.in_(active_statuses)),
        )
        .where(
            ItemCopy.catalog_item_id == item_id,
            ItemCopy.location.isnot(None),
            ItemCopy.location != "",
        )
        .group_by(literal_column("branch_name"))
        .order_by(literal_column("branch_name"))
    )

    loc_rows = (await db.execute(loc_query)).all()

    branch_lookup: dict[str, int] = {}
    if loc_rows:
        branch_names = [r.branch_name for r in loc_rows]
        branches_q = select(Branch.id, Branch.name).where(
            Branch.name.in_(branch_names),
            Branch.status == BranchStatus.ACTIVE,
        )
        for b in (await db.execute(branches_q)).all():
            branch_lookup[b.name] = b.id

    return [
        {
            "branch_id": branch_lookup.get(r.branch_name),
            "branch_name": r.branch_name,
            "total_copies": r.total_copies,
            "available": r.available,
            "call_number": item_call_number,
        }
        for r in loc_rows
    ]


@router.get("/items/{item_id}/state-history")
@limiter.limit("60/minute")
async def get_item_state_history(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    from ....models.catalog_state_event import CatalogStateEvent

    item = await _get_catalog_item_with_images(db, item_id)

    # Visibility gate -- mirror ``GET /catalog/items/{id}`` exactly. Without
    # this, anonymous callers could probe IDs to confirm existence and read
    # the ``reason`` text of every state change on CONFIDENTIAL or
    # non-cataloged items.
    if item.cataloging_status != CatalogingStatus.CATALOGED and not (
        current_user is not None and is_staff_or_admin(current_user)
    ):
        raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")
    if not current_user:
        if item.sensitivity_level != SensitivityLevel.PUBLIC:
            raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")
    elif current_user.role == UserRole.PATRON:
        if item.sensitivity_level == SensitivityLevel.CONFIDENTIAL:
            raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")

    is_staff = current_user and current_user.role in [
        UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR,
    ]

    stmt = (
        select(CatalogStateEvent)
        .where(CatalogStateEvent.catalog_item_id == item_id)
        .order_by(CatalogStateEvent.created_at.desc())
        .limit(50)
    )
    if is_staff:
        stmt = stmt.options(selectinload(CatalogStateEvent.actor))

    events = (await db.execute(stmt)).scalars().all()

    result = []
    for e in events:
        entry = {
            "id": e.id,
            "old_status": e.old_status.value if hasattr(e.old_status, "value") else e.old_status,
            "new_status": e.new_status.value if hasattr(e.new_status, "value") else e.new_status,
            "reason": e.reason,
            "source_type": e.source_type,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        if is_staff and e.actor:
            entry["actor_name"] = e.actor.full_name
        result.append(entry)

    return result


@router.get("/special/random", response_model=CatalogRandomResponse)
@limiter.limit("30/minute")
async def get_random_item(
    request: Request,
    item_type: ItemType | None = Query(None, description="Filter by item type"),
    status: ItemStatus | None = Query(None, description="Filter by status"),
    year_min: int | None = Query(None, description="Minimum publication year"),
    year_max: int | None = Query(None, description="Maximum publication year"),
    is_large_print: bool | None = Query(None, description="Filter by large print editions"),
    min_lexile: int | None = Query(None, ge=-400, le=2000, description="Min Lexile (inclusive)"),
    max_lexile: int | None = Query(None, ge=-400, le=2000, description="Max Lexile (inclusive)"),
    db: AsyncSession = Depends(get_db),
):
    """Get a random catalog item honoring the patron's active browse filters.

    "Surprise me" on /catalog should respect the format / availability / year /
    large-print / reading-level filters the patron has set, so it stops
    surfacing junk (e.g. a customs-service report) when they asked for, say, an
    available audiobook. Filters map to direct CatalogItem columns; language
    (a BIBFRAME join) is intentionally not applied here.
    """
    from sqlalchemy.sql.expression import func as sql_func

    query = select(CatalogItem).options(selectinload(CatalogItem.images)).where(
        CatalogItem.cataloging_status == CatalogingStatus.CATALOGED,
        CatalogItem.status.notin_([
            ItemStatus.withdrawn, ItemStatus.lost, ItemStatus.missing,
            ItemStatus.damaged, ItemStatus.lost_by_patron, ItemStatus.lost_in_transit,
            ItemStatus.damaged_withdrawn,
        ]),
    )

    if item_type:
        query = query.where(CatalogItem.item_type == item_type)
    if status:
        query = query.where(CatalogItem.status == status)
    if year_min is not None:
        query = query.where(CatalogItem.publication_year >= year_min)
    if year_max is not None:
        query = query.where(CatalogItem.publication_year <= year_max)
    if is_large_print is not None:
        query = query.where(CatalogItem.is_large_print == is_large_print)
    if min_lexile is not None:
        query = query.where(CatalogItem.lexile_number >= min_lexile)
    if max_lexile is not None:
        query = query.where(CatalogItem.lexile_number <= max_lexile)

    query = query.order_by(sql_func.random()).limit(1)
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    return {"item": CatalogItemResponse.model_validate(item) if item else None}


@router.get("/special/new-arrivals", response_model=CatalogNewArrivalsResponse)
@limiter.limit("60/minute")
async def get_new_arrivals(
    request: Request,
    days: int = Query(14, ge=1, le=90, description="Days back to look"),
    limit: int = Query(12, ge=1, le=50, description="Max items to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get items cataloged in the last N days, sorted by newest first.
    Falls back to 30 days if fewer than 3 items found."""
    from datetime import datetime, timedelta, timezone

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    period = "week" if days <= 14 else "month"

    base_where = [
        CatalogItem.cataloged_at >= cutoff_date,
        CatalogItem.cataloging_status == CatalogingStatus.CATALOGED,
        CatalogItem.status.notin_([
            ItemStatus.withdrawn, ItemStatus.lost, ItemStatus.missing,
        ]),
    ]

    count_query = select(func.count(CatalogItem.id)).where(*base_where)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fallback to 30 days if fewer than 3 items
    if total < 3 and days <= 14:
        days = 30
        period = "month"
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        base_where[0] = CatalogItem.cataloged_at >= cutoff_date
        count_query = select(func.count(CatalogItem.id)).where(*base_where)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

    query = (
        select(CatalogItem)
        .options(selectinload(CatalogItem.images))
        .where(*base_where)
        .order_by(CatalogItem.cataloged_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [CatalogItemResponse.model_validate(item) for item in items],
        "total": total,
        "page": 1,
        "per_page": limit,
        "pages": 1,
        "days": days,
        "period": period,
    }


@router.get("/{item_id}/series", response_model=SeriesReadingOrderResponse)
@limiter.limit("120/minute")
async def get_item_series_reading_order(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Ordered list of the titles we hold in this item's series.

    Sorted by ``series_position`` ascending, NULLs last. The list is scoped to
    what is IN OUR CATALOG and visible to the requester -- it is NOT the full
    published series, so ``total_held`` is a holdings count, never the series
    length. ``current_position`` / ``prev_id`` / ``next_id`` let the item page
    show reading-order context and adjacent-title links.
    """
    item = await _get_catalog_item_with_images(db, item_id)

    # Same visibility rules as the item-detail endpoint.
    is_staff = current_user is not None and is_staff_or_admin(current_user)
    if item.cataloging_status != CatalogingStatus.CATALOGED and not is_staff:
        raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")
    if not current_user:
        if item.sensitivity_level != SensitivityLevel.PUBLIC:
            raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")
    elif current_user.role == UserRole.PATRON:
        if item.sensitivity_level == SensitivityLevel.CONFIDENTIAL:
            raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")

    if not item.series_name or not item.series_name.strip():
        return SeriesReadingOrderResponse(
            series_name="",
            total_held=0,
            current_position=item.series_position,
            items=[],
        )

    # Pull sibling titles sharing the exact series_name, applying the same
    # visibility filters as the item-detail view so a patron never sees a
    # not-yet-cataloged or restricted sibling in the reading-order rail.
    conditions = [CatalogItem.series_name == item.series_name]
    if not is_staff:
        conditions.append(CatalogItem.cataloging_status == CatalogingStatus.CATALOGED)
    if not current_user:
        conditions.append(CatalogItem.sensitivity_level == SensitivityLevel.PUBLIC)
    elif current_user.role == UserRole.PATRON:
        conditions.append(CatalogItem.sensitivity_level != SensitivityLevel.CONFIDENTIAL)

    # Order: parsed position first (NULLs last), then title for stable output.
    result = await db.execute(
        select(CatalogItem)
        .where(*conditions)
        .order_by(
            case((CatalogItem.series_position.is_(None), 1), else_=0),
            CatalogItem.series_position.asc(),
            CatalogItem.title.asc(),
            CatalogItem.id.asc(),
        )
    )
    siblings = result.scalars().all()

    members = [SeriesMemberResponse.model_validate(s) for s in siblings]

    # prev/next: the held titles immediately adjacent to the current item in
    # ordered position. Computed by index in the ordered list so it works even
    # when positions are sparse (we hold Books 1, 4, 7 -> 4's prev is 1).
    prev_id: int | None = None
    next_id: int | None = None
    for idx, s in enumerate(siblings):
        if s.id == item.id:
            if idx > 0:
                prev_id = siblings[idx - 1].id
            if idx < len(siblings) - 1:
                next_id = siblings[idx + 1].id
            break

    return SeriesReadingOrderResponse(
        series_name=item.series_name,
        total_held=len(siblings),
        current_position=item.series_position,
        prev_id=prev_id,
        next_id=next_id,
        items=members,
    )


@router.get("/{item_id}", response_model=CatalogItemResponse)
@limiter.limit("120/minute")
async def get_catalog_item(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Get a specific catalog item by ID (backward compatibility endpoint)."""
    cache_key = f"catalog:item:id:{item_id}:user:{str(current_user.role) if current_user else 'public'}"
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result

    item = await _get_catalog_item_with_images(db, item_id)

    # Check visibility based on user role and item properties
    if item.cataloging_status != CatalogingStatus.CATALOGED and not (
        current_user is not None and is_staff_or_admin(current_user)
    ):
        raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")

    # Check sensitivity level
    if not current_user:
        # Public user: only see PUBLIC items
        if item.sensitivity_level != SensitivityLevel.PUBLIC:
            raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")
    elif current_user.role == UserRole.PATRON:
        # Patron: cannot see CONFIDENTIAL items
        if item.sensitivity_level == SensitivityLevel.CONFIDENTIAL:
            raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")
    # STAFF and ADMIN can see all

    response_data = CatalogItemResponse.model_validate(item)

    # Calculate real availability from copies/checkouts instead of stale status field
    total_copies_q = (
        select(func.count(ItemCopy.id))
        .where(ItemCopy.catalog_item_id == item_id)
    )
    active_checkouts_q = (
        select(func.count(Checkout.id))
        .join(ItemCopy, Checkout.item_copy_id == ItemCopy.id)
        .where(ItemCopy.catalog_item_id == item_id)
        .where(Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]))
    )
    total_copies = (await db.execute(total_copies_q)).scalar() or 0
    on_loan = (await db.execute(active_checkouts_q)).scalar() or 0

    if total_copies > 0:
        available = total_copies - on_loan
        if available > 0:
            response_data.status = ItemStatus.available
        else:
            response_data.status = ItemStatus.checked_out

    await set_cached(cache_key, response_data.model_dump(), ttl_seconds=300)
    return response_data


# ============================================================================
# Batch Availability Endpoint
# ============================================================================


class BatchAvailabilityRequest(BaseModel):
    item_ids: List[int]


class ItemAvailabilityInfo(BaseModel):
    item_id: int
    total_copies: int
    available_copies: int
    on_loan: int
    status: str  # 'available' | 'limited' | 'unavailable'
    next_available_date: str | None = None


@router.post("/batch-availability", response_model=List[ItemAvailabilityInfo])
async def get_batch_availability(  # noqa: role-check -- public batch availability lookup (read-only, 50-item cap)
    request_body: BatchAvailabilityRequest,
    db: AsyncSession = Depends(get_db),
):
    """Get availability info for multiple catalog items in a single request.

    Replaces N individual /availability calls with one batch query.
    Limited to 50 items per request.
    """
    item_ids = request_body.item_ids[:50]  # Cap at 50

    if not item_ids:
        return []

    # Count total copies per catalog item
    total_copies_q = (
        select(
            ItemCopy.catalog_item_id,
            func.count(ItemCopy.id).label("total_copies"),
        )
        .where(ItemCopy.catalog_item_id.in_(item_ids))
        .group_by(ItemCopy.catalog_item_id)
    )
    total_result = await db.execute(total_copies_q)
    totals = {row.catalog_item_id: row.total_copies for row in total_result.all()}

    # Count active checkouts per catalog item (join through ItemCopy)
    active_statuses = [CheckoutStatus.active, CheckoutStatus.overdue]
    active_checkouts_q = (
        select(
            ItemCopy.catalog_item_id,
            func.count(Checkout.id).label("on_loan"),
        )
        .join(ItemCopy, Checkout.item_copy_id == ItemCopy.id)
        .where(ItemCopy.catalog_item_id.in_(item_ids))
        .where(Checkout.status.in_(active_statuses))
        .group_by(ItemCopy.catalog_item_id)
    )
    checkout_result = await db.execute(active_checkouts_q)
    on_loan_map = {row.catalog_item_id: row.on_loan for row in checkout_result.all()}

    results = []
    for item_id in item_ids:
        total = totals.get(item_id, 0)
        on_loan = on_loan_map.get(item_id, 0)
        available = max(0, total - on_loan)

        if available > 0:
            avail_status = "available" if available > 1 else "limited"
        else:
            avail_status = "unavailable"

        results.append(ItemAvailabilityInfo(
            item_id=item_id,
            total_copies=total,
            available_copies=available,
            on_loan=on_loan,
            status=avail_status,
        ))

    return results


DEFAULT_LOAN_DAYS = 21


async def _loan_days_for_item_type(db: AsyncSession, item_type) -> int:
    """Loan period for the wait estimate: the generic (no role/binding/collection)
    circulation policy for the item type, falling back to DEFAULT_LOAN_DAYS."""
    from ....models.circulation_policy import CirculationPolicy

    q = (
        select(CirculationPolicy.loan_period_days)
        .where(
            CirculationPolicy.active.is_(True),
            CirculationPolicy.loan_period_days.isnot(None),
            CirculationPolicy.item_type == item_type,
            CirculationPolicy.role.is_(None),
            CirculationPolicy.binding.is_(None),
            CirculationPolicy.collection_id.is_(None),
        )
        .limit(1)
    )
    loan_days = (await db.execute(q)).scalar()
    return loan_days or DEFAULT_LOAN_DAYS


@router.get("/items/{item_id}/hold-queue")
@limiter.limit("60/minute")
async def get_hold_queue_info(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Get hold queue size and estimated wait for a catalog item.

    Visibility-gated: anonymous callers only see PUBLIC + CATALOGED items.
    Without this gate, anyone could enumerate IDs and confirm queue depth +
    wait estimate for CONFIDENTIAL or non-cataloged records.
    """
    from ....models.circulation import Hold
    from ....models.inventory import ItemCopy

    item_q = select(
        CatalogItem.id,
        CatalogItem.cataloging_status,
        CatalogItem.sensitivity_level,
        CatalogItem.item_type,
    ).where(CatalogItem.id == item_id)
    item_row = (await db.execute(item_q)).first()
    if not item_row:
        raise HTTPException(status_code=404, detail="Item not found")

    if item_row.cataloging_status != CatalogingStatus.CATALOGED and not (
        current_user is not None and is_staff_or_admin(current_user)
    ):
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user:
        if item_row.sensitivity_level != SensitivityLevel.PUBLIC:
            raise HTTPException(status_code=404, detail="Item not found")
    elif current_user.role == UserRole.PATRON:
        if item_row.sensitivity_level == SensitivityLevel.CONFIDENTIAL:
            raise HTTPException(status_code=404, detail="Item not found")

    hold_result = await db.execute(
        select(func.count(Hold.id)).where(
            Hold.item_id == item_id,
            Hold.status.in_(["pending", "ready"]),
        )
    )
    queue_size = hold_result.scalar() or 0

    copy_result = await db.execute(
        select(func.count(ItemCopy.id)).where(
            ItemCopy.catalog_item_id == item_id,
        )
    )
    total_copies = copy_result.scalar() or 0

    if total_copies > 0 and queue_size > 0:
        loan_days = await _loan_days_for_item_type(db, item_row.item_type)
        estimated_wait_days = int((queue_size / total_copies) * loan_days)
    else:
        estimated_wait_days = 0

    return {
        "queue_size": queue_size,
        "estimated_wait_days": estimated_wait_days,
        "total_copies": total_copies,
    }

