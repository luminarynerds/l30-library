# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Catalog Management API Endpoints

Provides endpoints for:
- Catalog search
- Catalog item CRUD
- MARC record enhancement with Google Books data
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.catalog import CatalogItem
from ....models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ....models.user import User
from ....schemas.catalog import (
    CatalogItemCreate,
    CatalogItemStaffResponse,
    CatalogItemUpdate,
)
from ....services.marc_enhancement_service import marc_enhancement_service
from ..dependencies import require_staff
from ..catalog.helpers import (
    _escape_ilike,
    apply_cataloging_workflow_stamps,
    apply_series_position,
    raise_for_barcode_conflict,
)

router = APIRouter(prefix="/staff", tags=["staff-catalog"])


class CatalogSearchResponse(BaseModel):
    items: list[CatalogItemStaffResponse]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/catalog/items", response_model=CatalogSearchResponse)
async def staff_list_catalog_items(
    q: Optional[str] = Query(None, description="Search query"),
    search: Optional[str] = Query(None, description="Search query (alias)"),
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    cataloging_status: Optional[str] = Query(None, description="Filter by cataloging status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    limit: int = Query(None, ge=1, le=100, description="Alias for per_page"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List catalog items with staff access. Uses FTS when search query provided."""
    from ....services.search import get_search_service

    # Support both 'q' and 'search' param names (frontend uses 'search')
    search_query = q or search
    actual_per_page = limit or per_page

    if search_query and search_query.strip():
        # Use PostgreSQL FTS for ranked search results
        service = get_search_service(db)
        result = await service.search(
            query=search_query.strip(),
            item_type=item_type,
            status=status,
            page=page,
            per_page=actual_per_page,
            include_facets=False,
        )
        # Load full ORM objects for the matched IDs (preserving FTS rank order)
        item_ids = [r.item["id"] for r in result.results if r.item.get("id")]
        if item_ids:
            items_query = (
                select(CatalogItem)
                .options(selectinload(CatalogItem.images))
                .where(CatalogItem.id.in_(item_ids))
            )
            items_result = await db.execute(items_query)
            items_by_id = {item.id: item for item in items_result.scalars().all()}
            # Preserve FTS ranking order
            items = [items_by_id[iid] for iid in item_ids if iid in items_by_id]
        else:
            items = []

        return CatalogSearchResponse(
            items=[CatalogItemStaffResponse.model_validate(item) for item in items],
            total=result.total_results,
            page=page,
            per_page=actual_per_page,
            pages=(result.total_results + actual_per_page - 1) // actual_per_page if result.total_results > 0 else 0,
        )

    # No search query -- plain browse with optional filters
    query = select(CatalogItem).options(selectinload(CatalogItem.images))
    count_query = select(func.count(CatalogItem.id))

    if item_type:
        query = query.where(CatalogItem.item_type == item_type)
        count_query = count_query.where(CatalogItem.item_type == item_type)

    if status:
        query = query.where(CatalogItem.status == status)
        count_query = count_query.where(CatalogItem.status == status)

    if cataloging_status:
        query = query.where(CatalogItem.cataloging_status == cataloging_status)
        count_query = count_query.where(CatalogItem.cataloging_status == cataloging_status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * actual_per_page
    query = query.offset(offset).limit(actual_per_page).order_by(CatalogItem.title)

    result = await db.execute(query)
    items = result.scalars().all()

    return CatalogSearchResponse(
        items=[CatalogItemStaffResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=actual_per_page,
        pages=(total + actual_per_page - 1) // actual_per_page if total > 0 else 0,
    )


@router.get("/catalog", response_model=CatalogSearchResponse)
async def staff_search_catalog(
    q: Optional[str] = Query(None, description="Search query"),
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    cataloging_status: Optional[str] = Query(None, description="Filter by cataloging status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Search catalog items with staff access."""
    query = select(CatalogItem).options(selectinload(CatalogItem.images))
    count_query = select(func.count(CatalogItem.id))

    if q:
        search = f"%{_escape_ilike(q)}%"
        search_filter = or_(
            CatalogItem.title.ilike(search),
            CatalogItem.author.ilike(search),
            CatalogItem.isbn.ilike(search),
            CatalogItem.barcode.ilike(search),
            CatalogItem.subjects.ilike(search),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if item_type:
        query = query.where(CatalogItem.item_type == item_type)
        count_query = count_query.where(CatalogItem.item_type == item_type)

    if status:
        query = query.where(CatalogItem.status == status)
        count_query = count_query.where(CatalogItem.status == status)

    if cataloging_status:
        query = query.where(CatalogItem.cataloging_status == cataloging_status)
        count_query = count_query.where(CatalogItem.cataloging_status == cataloging_status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(CatalogItem.title)

    result = await db.execute(query)
    items = result.scalars().all()

    return CatalogSearchResponse(
        items=[CatalogItemStaffResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.post("/catalog", response_model=CatalogItemStaffResponse, status_code=status.HTTP_201_CREATED)
async def staff_create_catalog_item(
    item_in: CatalogItemCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new catalog item (staff only)."""
    data = item_in.model_dump()
    apply_series_position(data)
    apply_cataloging_workflow_stamps(data, existing_item=None, actor_id=staff_user.id)
    item = CatalogItem(**data)
    db.add(item)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise_for_barcode_conflict(exc)
        raise
    await db.refresh(item)
    # Eagerly load images relationship for response serialization
    result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == item.id).options(selectinload(CatalogItem.images))
    )
    item = result.scalar_one()
    return item


# ============================================================================

class CatalogStatsResponse(BaseModel):
    status_counts: dict[str, int]
    missing_covers: int
    added_this_week: int


@router.get("/catalog/stats", response_model=CatalogStatsResponse)
async def get_catalog_stats(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate counts for the cataloging workflow dashboard."""
    from ....models.catalog import CatalogingStatus
    from datetime import datetime, timedelta, timezone

    # Status counts grouped by cataloging_status
    status_result = await db.execute(
        select(CatalogItem.cataloging_status, func.count(CatalogItem.id))
        .group_by(CatalogItem.cataloging_status)
    )
    status_counts = {row[0]: row[1] for row in status_result.all()}
    # Normalise enum values to plain strings
    status_counts = {
        (v.value if isinstance(v, CatalogingStatus) else str(v)): c
        for v, c in status_counts.items()
    }

    # Missing covers
    covers_result = await db.execute(
        select(func.count(CatalogItem.id)).where(CatalogItem.cover_url.is_(None))
    )
    missing_covers = covers_result.scalar() or 0

    # Added this week
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    week_result = await db.execute(
        select(func.count(CatalogItem.id)).where(CatalogItem.cataloged_at >= one_week_ago)
    )
    added_this_week = week_result.scalar() or 0

    return CatalogStatsResponse(
        status_counts=status_counts,
        missing_covers=missing_covers,
        added_this_week=added_this_week,
    )


@router.get("/catalog/{item_id}", response_model=CatalogItemStaffResponse)
async def staff_get_catalog_item(
    item_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a catalog item by ID (staff only)."""
    result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == item_id).options(selectinload(CatalogItem.images))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/catalog/{item_id}", response_model=CatalogItemStaffResponse)
async def staff_update_catalog_item(
    item_id: int,
    item_in: CatalogItemUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a catalog item (staff only)."""
    item = await get_or_404(db, CatalogItem, item_id, "Item not found")

    update_data = item_in.model_dump(exclude_unset=True)
    apply_series_position(update_data)
    apply_cataloging_workflow_stamps(update_data, existing_item=item, actor_id=staff_user.id)
    for field, value in update_data.items():
        setattr(item, field, value)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise_for_barcode_conflict(exc)
        raise
    await db.refresh(item)
    result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == item.id).options(selectinload(CatalogItem.images))
    )
    item = result.scalar_one()
    return item


@router.delete("/catalog/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def staff_delete_catalog_item(
    item_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a catalog item (staff only)."""
    item = await get_or_404(db, CatalogItem, item_id, "Item not found")

    # Check for active checkouts
    checkout_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.item_id == item_id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    )
    active_checkouts = checkout_result.scalar() or 0
    if active_checkouts > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete item with {active_checkouts} active checkout(s)",
        )

    # Check for pending holds
    hold_result = await db.execute(
        select(func.count(Hold.id)).where(
            Hold.item_id == item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
    )
    active_holds = hold_result.scalar() or 0
    if active_holds > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete item with {active_holds} active hold(s)",
        )

    await db.delete(item)
    await db.commit()


# ============================================================================
# MARC Enhancement with Google Books
# ============================================================================

class MARCEnhancementRequest(BaseModel):
    search_query: Optional[str] = None
    overwrite_existing: bool = False


class MARCEnhancementResponse(BaseModel):
    description: Optional[str] = None
    page_count: Optional[int] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    subjects: list[str] = []
    cover_url: Optional[str] = None
    categories: list[str] = []
    dewey_hint: Optional[str] = None


@router.post("/catalog/{item_id}/enhance-from-google-books", response_model=CatalogItemStaffResponse)
async def enhance_catalog_item_from_google_books(
    item_id: int,
    request: MARCEnhancementRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Enhance catalog item metadata using Google Books API.

    This endpoint fetches comprehensive metadata from Google Books and updates
    the catalog item with enhanced information. Useful for improving MARC records
    with better descriptions, subjects, and classifications.

    Features:
    - Searches by ISBN (most reliable)
    - Falls back to title + author search
    - Pulls descriptions, page counts, publishers, subjects
    - Suggests Dewey classifications based on categories
    - Fetches cover images from Google Books

    Parameters:
    - search_query: Custom search query (optional, uses ISBN or title+author by default)
    - overwrite_existing: If true, overwrites existing field values (default: false)

    Returns:
    - Updated CatalogItem with enhanced metadata
    """
    item = await get_or_404(db, CatalogItem, item_id, "Item not found")

    # Fetch enhanced data from Google Books
    enhanced_item = await marc_enhancement_service.update_catalog_item_from_google_books(
        item,
        search_query=request.search_query,
        overwrite_existing=request.overwrite_existing
    )

    # Save updates
    await db.commit()
    await db.refresh(enhanced_item)
    result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == enhanced_item.id).options(selectinload(CatalogItem.images))
    )
    enhanced_item = result.scalar_one()

    return enhanced_item


@router.get("/catalog/{item_id}/google-books-preview")
async def preview_google_books_enhancement(
    item_id: int,
    search_query: Optional[str] = Query(None),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Preview what metadata would be fetched from Google Books without saving.

    Useful for reviewing changes before committing them to the database.

    Returns:
    - Dictionary with enhanced metadata fields
    - No changes are made to the database
    """
    item = await get_or_404(db, CatalogItem, item_id, "Item not found")

    # Fetch enhanced data without modifying item
    enhanced_data = await marc_enhancement_service.enhance_from_google_books(
        item,
        search_query=search_query
    )

    return {
        "item_id": item.id,
        "title": item.title,
        "author": item.author,
        "isbn": item.isbn,
        "enhanced_data": enhanced_data,
        "changes": {
            "description": bool(enhanced_data.get('description') and not item.description),
            "page_count": bool(enhanced_data.get('page_count') and not item.page_count),
            "publisher": bool(enhanced_data.get('publisher') and not item.publisher),
            "publication_year": bool(enhanced_data.get('publication_year') and not item.publication_year),
            "subjects": bool(enhanced_data.get('subjects') and not item.subjects),
            "cover_url": bool(enhanced_data.get('cover_url') and not item.cover_url),
            "dewey_hint": bool(enhanced_data.get('dewey_hint') and not item.dewey_decimal),
        }
    }


@router.post("/catalog/bulk-enhance-from-google-books")
async def bulk_enhance_catalog_from_google_books(
    item_ids: list[int],
    overwrite_existing: bool = False,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Enhance multiple catalog items from Google Books in bulk.

    Useful for improving metadata across the entire catalog or a subset.
    Returns counts of successfully enhanced items.

    Parameters:
    - item_ids: List of catalog item IDs to enhance
    - overwrite_existing: If true, overwrites existing field values

    Returns:
    - Summary with enhanced_count, skipped_count, error_count
    """
    if len(item_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 items per bulk operation")

    enhanced_count = 0
    skipped_count = 0
    error_count = 0
    errors = []

    for item_id in item_ids:
        try:
            item = await get_or_404(db, CatalogItem, item_id, "Item not found")

            # Fetch and update
            await marc_enhancement_service.update_catalog_item_from_google_books(
                item,
                overwrite_existing=overwrite_existing
            )

            await db.commit()
            await db.refresh(item)
            enhanced_count += 1

        except HTTPException as e:
            if e.status_code == 404:
                skipped_count += 1
            else:
                error_count += 1
                errors.append({"item_id": item_id, "error": str(e.detail)})
        except Exception as e:  # noqa: BLE001  # per-item catalog enrich — record failure and continue
            error_count += 1
            errors.append({"item_id": item_id, "error": str(e)})

    return {
        "enhanced_count": enhanced_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "errors": errors,
        "total": len(item_ids),
    }


# ============================================================================
# AI Catalog Enrichment (Ollama)
# ============================================================================

class AIEnrichmentResponse(BaseModel):
    success: bool
    generated_text: Optional[str] = None
    generated_subjects: Optional[list[str]] = None
    enrichment_type: str
    model_used: Optional[str] = None
    generation_time_ms: Optional[int] = None
    error: Optional[str] = None


class AIApplyEnrichmentRequest(BaseModel):
    field: str  # "description" or "subjects"
    value: str
    overwrite: bool = False


class AIBulkEnrichRequest(BaseModel):
    item_ids: list[int]
    enrichment_type: str  # "description" or "subjects"


@router.post("/catalog/{item_id}/ai-generate-description", response_model=AIEnrichmentResponse)
async def ai_generate_description(
    item_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an AI catalog description for an item (preview only, does not save).

    Uses local Ollama LLM to generate a library-quality description based on
    the item's title, author, ISBN, type, and existing metadata.
    """
    from ....services.catalog_enrichment_service import generate_catalog_description
    from ....services.ollama_service import OllamaError

    try:
        result = await generate_catalog_description(db, item_id)
        return AIEnrichmentResponse(
            success=True,
            generated_text=result["generated_text"],
            enrichment_type="description",
            model_used=result["model"],
            generation_time_ms=result["generation_time_ms"],
        )
    except OllamaError as e:
        return AIEnrichmentResponse(
            success=False,
            enrichment_type="description",
            error=str(e),
        )


@router.post("/catalog/{item_id}/ai-generate-subjects", response_model=AIEnrichmentResponse)
async def ai_generate_subjects(
    item_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate AI-suggested subject headings for an item (preview only, does not save).

    Uses local Ollama LLM to suggest Library of Congress-style subject headings
    based on the item's metadata.
    """
    from ....services.catalog_enrichment_service import generate_catalog_subjects
    from ....services.ollama_service import OllamaError

    try:
        result = await generate_catalog_subjects(db, item_id)
        return AIEnrichmentResponse(
            success=True,
            generated_text=result["generated_text"],
            generated_subjects=result["generated_subjects"],
            enrichment_type="subjects",
            model_used=result["model"],
            generation_time_ms=result["generation_time_ms"],
        )
    except OllamaError as e:
        return AIEnrichmentResponse(
            success=False,
            enrichment_type="subjects",
            error=str(e),
        )


@router.post("/catalog/{item_id}/ai-apply-enrichment")
async def ai_apply_enrichment(
    item_id: int,
    request: AIApplyEnrichmentRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Apply AI-generated enrichment to a catalog item (saves to DB).

    Body:
    - field: "description" or "subjects"
    - value: The generated text to save
    - overwrite: If false (default), won't replace existing values
    """
    if request.field not in ("description", "subjects"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="field must be 'description' or 'subjects'",
        )

    item = await get_or_404(db, CatalogItem, item_id, "Item not found")

    current_value = getattr(item, request.field)
    if current_value and not request.overwrite:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item already has a {request.field}. Set overwrite=true to replace it.",
        )

    setattr(item, request.field, request.value)
    await db.commit()
    await db.refresh(item)

    return {
        "success": True,
        "item_id": item.id,
        "field": request.field,
        "value": request.value,
        "overwritten": bool(current_value),
    }


@router.post("/catalog/bulk-ai-enrich")
async def bulk_ai_enrich(
    request: AIBulkEnrichRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk generate AI enrichment for multiple catalog items.

    Generates descriptions or subjects for items that are missing them.
    Does NOT auto-save — returns generated content for review.
    """
    from ....services.catalog_enrichment_service import (
        generate_catalog_description,
        generate_catalog_subjects,
    )
    from ....services.ollama_service import OllamaError

    if len(request.item_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 items per bulk operation")

    if request.enrichment_type not in ("description", "subjects"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="enrichment_type must be 'description' or 'subjects'",
        )

    results = []
    success_count = 0
    error_count = 0

    for item_id in request.item_ids:
        try:
            if request.enrichment_type == "description":
                result = await generate_catalog_description(db, item_id)
                results.append({
                    "item_id": item_id,
                    "success": True,
                    "generated_text": result["generated_text"],
                    "generation_time_ms": result["generation_time_ms"],
                })
            else:
                result = await generate_catalog_subjects(db, item_id)
                results.append({
                    "item_id": item_id,
                    "success": True,
                    "generated_text": result["generated_text"],
                    "generated_subjects": result["generated_subjects"],
                    "generation_time_ms": result["generation_time_ms"],
                })
            success_count += 1
        except (OllamaError, Exception) as e:  # noqa: BLE001  # per-item subjects gen — record failure and continue
            error_count += 1
            results.append({
                "item_id": item_id,
                "success": False,
                "error": str(e),
            })

    return {
        "enrichment_type": request.enrichment_type,
        "total": len(request.item_ids),
        "success_count": success_count,
        "error_count": error_count,
        "results": results,
    }


# ============================================================================
# Catalog Stats (Workflow Queue Dashboard)