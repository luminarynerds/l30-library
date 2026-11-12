# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.cache import invalidate_catalog_cache
from ....services.reports.cache_invalidator import invalidate_collection_reports
from ....core.database import AsyncSessionLocal, get_db
from ....core.exceptions import InternalServerError
from ....core.error_codes import ErrorCode
from ....core.shortcuts import get_or_404
from ....core.rate_limit import limiter
from ....models.catalog import CatalogItem, ItemStatus
from ....models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ....models.user import User
from ....schemas.catalog import (
    BulkUpdateRequest,
    BulkUpdateResponse,
    CatalogItemCreate,
    CatalogItemStaffResponse,
    CatalogItemUpdate,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
)
from ..dependencies import require_staff
from .helpers import (
    _get_catalog_item_with_images,
    apply_cataloging_workflow_stamps,
    apply_series_position,
    check_for_duplicates,
    raise_for_barcode_conflict,
)
from ....services.catalog_bibframe_sync import CatalogBibframeSync
from ....services.lexile import parse_lexile

logger = get_logger(__name__)


def _apply_lexile(payload: dict) -> dict:
    if "lexile_measure" in payload:
        raw = payload.get("lexile_measure")
        try:
            canonical, numeric = parse_lexile(raw)
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{"loc": ["body", "lexile_measure"], "msg": str(e), "type": "value_error"}],
            ) from e
        payload["lexile_measure"] = canonical
        payload["lexile_number"] = numeric
    return payload


async def _fetch_cover_background(item_id: int, isbn: str | None, title: str, author: str | None, item_type: str):
    from ....services.cover_service import get_cover_url, get_music_cover_url, get_movie_cover_url
    try:
        cover_url = None
        if item_type in ("book", "audiobook", "ebook"):
            cover_url = await get_cover_url(isbn=isbn, title=title, author=author)
        elif item_type in ("cd", "vinyl"):
            cover_url = await get_music_cover_url(artist=author, album=title)
        elif item_type in ("dvd", "bluray"):
            cover_url = await get_movie_cover_url(title=title)
        if cover_url:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("UPDATE catalog_items SET cover_url = :url WHERE id = :id AND (cover_url IS NULL OR cover_url = '')"),
                    {"url": cover_url, "id": item_id},
                )
                await db.commit()
                await invalidate_catalog_cache()
            logger.info("Background cover fetch for item %d: %s", item_id, cover_url)
    except Exception:
        logger.exception("Background cover fetch failed for item %d", item_id)


async def _sync_to_bibframe_background(item_id: int):
    try:
        async with AsyncSessionLocal() as db:
            item = await get_or_404(db, CatalogItem, item_id, "Item not found")
            await CatalogBibframeSync.create_from_catalog(db, item)
            await db.commit()
            logger.info("Synced catalog item %d to BIBFRAME", item_id)
    except Exception:
        logger.exception("Failed to sync catalog item %d to BIBFRAME", item_id)


async def _update_bibframe_background(item_id: int):
    try:
        async with AsyncSessionLocal() as db:
            item = await get_or_404(db, CatalogItem, item_id, "Item not found")
            await CatalogBibframeSync.update_from_catalog(db, item)
            await db.commit()
            logger.info("Updated BIBFRAME for catalog item %d", item_id)
    except Exception:
        logger.exception("Failed to update BIBFRAME for catalog item %d", item_id)


router = APIRouter()


@router.post("/check-duplicates", response_model=DuplicateCheckResponse)
@limiter.limit("60/minute")
async def check_catalog_duplicates(
    request: Request,
    check_request: DuplicateCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Check for potential duplicate catalog items before creating/updating.

    Checks by:
    1. ISBN exact match (confidence: 1.0)
    2. Title + Author match (confidence: 0.85-1.0)
    3. Title-only exact match (confidence: 0.6)

    Staff-only endpoint.
    """
    if not check_request.isbn and not check_request.title:
        raise HTTPException(
            status_code=400,
            detail="At least ISBN or title is required for duplicate check"
        )

    duplicates = await check_for_duplicates(
        db=db,
        isbn=check_request.isbn,
        title=check_request.title,
        author=check_request.author,
        exclude_id=check_request.exclude_id,
    )

    has_duplicates = len(duplicates) > 0

    # Generate message
    message = None
    if has_duplicates:
        if duplicates[0].match_type == "isbn":
            message = f"Found {len(duplicates)} item(s) with matching ISBN"
        elif duplicates[0].match_type == "title_author":
            message = f"Found {len(duplicates)} item(s) with similar title and author"
        else:
            message = f"Found {len(duplicates)} item(s) with matching title"

    return DuplicateCheckResponse(
        has_duplicates=has_duplicates,
        duplicates=duplicates,
        message=message,
    )


@router.post("/bulk-update", response_model=BulkUpdateResponse)
@limiter.limit("10/minute")
async def bulk_update_catalog_items(
    request: Request,
    bulk_request: BulkUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Bulk update multiple catalog items.

    Supports updating: status, location, subjects.
    Maximum 100 items per request.

    Staff-only endpoint.
    """
    allowed_fields = {"status", "location", "subjects"}

    # Validate update fields
    invalid_fields = set(bulk_request.updates.keys()) - allowed_fields
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fields for bulk update: {', '.join(invalid_fields)}. Allowed: {', '.join(allowed_fields)}"
        )

    if not bulk_request.updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    # Validate status if provided
    if "status" in bulk_request.updates:
        try:
            ItemStatus(bulk_request.updates["status"])
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {bulk_request.updates['status']}"
            ) from None

    success_count = 0
    failure_count = 0
    errors = []

    # Batch-load all items in a single query to avoid N+1
    result = await db.execute(
        select(CatalogItem).where(CatalogItem.id.in_(bulk_request.item_ids))
    )
    items_by_id = {item.id: item for item in result.scalars().all()}

    for item_id in bulk_request.item_ids:
        try:
            item = items_by_id.get(item_id)

            if not item:
                failure_count += 1
                errors.append({"id": item_id, "error": "Item not found"})
                continue

            # Apply updates
            for field, value in bulk_request.updates.items():
                if field == "status":
                    item.status = ItemStatus(value)
                else:
                    setattr(item, field, value)

            success_count += 1

        except Exception as e:  # noqa: BLE001  # per-item bulk update — record failure and continue
            failure_count += 1
            errors.append({"id": item_id, "error": str(e)})
            logger.error(f"Error updating item {item_id}: {e}")

    if success_count > 0:
        await db.commit()
        await invalidate_catalog_cache()

    return BulkUpdateResponse(
        success_count=success_count,
        failure_count=failure_count,
        errors=errors,
    )


@router.post("/", response_model=CatalogItemStaffResponse, status_code=status.HTTP_201_CREATED)
async def create_catalog_item(
    item_in: CatalogItemCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new catalog item. Requires staff or admin role."""
    data = item_in.model_dump()
    _apply_lexile(data)
    apply_series_position(data)
    apply_cataloging_workflow_stamps(data, existing_item=None, actor_id=current_user.id)
    item = CatalogItem(**data)
    db.add(item)
    try:
        await db.commit()
        # Re-fetch with images eagerly loaded to avoid MissingGreenlet
        item = await _get_catalog_item_with_images(db, item.id)

        # Invalidate catalog search cache since results may have changed
        await invalidate_catalog_cache()
        await invalidate_collection_reports()
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise_for_barcode_conflict(exc)
        logger.exception("Failed to create catalog item")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from exc

    # Sync to BIBFRAME linked data in background
    background_tasks.add_task(_sync_to_bibframe_background, item.id)

    # Auto-fetch cover image in background if none set
    if not item.cover_url:
        item_type_val = item.item_type.value if hasattr(item.item_type, "value") else str(item.item_type)
        background_tasks.add_task(
            _fetch_cover_background, item.id, item.isbn, item.title, item.author or getattr(item, "artist", None), item_type_val,
        )

    return item


@router.patch("/{item_id}", response_model=CatalogItemStaffResponse)
async def update_catalog_item(
    item_id: int,
    background_tasks: BackgroundTasks,
    item_in: CatalogItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a catalog item. Requires staff or admin role."""
    item = await _get_catalog_item_with_images(db, item_id)

    update_data = item_in.model_dump(exclude_unset=True)
    _apply_lexile(update_data)
    apply_series_position(update_data)
    apply_cataloging_workflow_stamps(update_data, existing_item=item, actor_id=current_user.id)
    for field, value in update_data.items():
        setattr(item, field, value)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise_for_barcode_conflict(exc)
        raise
    # Re-fetch with images eagerly loaded to avoid MissingGreenlet
    item = await _get_catalog_item_with_images(db, item_id)

    # Sync to BIBFRAME linked data in background
    background_tasks.add_task(_update_bibframe_background, item.id)

    # Invalidate catalog search cache since item data may have changed
    await invalidate_catalog_cache()
    await invalidate_collection_reports()

    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalog_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete a catalog item. Requires staff or admin role."""
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
            status_code=status.HTTP_409_CONFLICT,
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
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete item with {active_holds} active hold(s)",
        )

    # Delete from BIBFRAME
    try:
        await CatalogBibframeSync.delete_from_catalog(db, item)
    except Exception as e:  # noqa: BLE001  # BIBFRAME sync best-effort — don't block catalog delete
        logger.error(f"Failed to delete BIBFRAME item for catalog {item_id}: {e}")
        # Don't fail the catalog deletion if BIBFRAME sync fails

    await db.delete(item)
    await db.commit()

    # Invalidate catalog search cache since item was removed
    await invalidate_catalog_cache()
