# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from app.core.logging import get_logger
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.cache import invalidate_catalog_cache
from ....core.database import get_db
from ....core.file_validation import validate_file_size, validate_file_type
from ....core.rate_limit import limiter
from ....core.shortcuts import get_or_404
from ....models.catalog import CatalogImage, CatalogItem
from ....models.user import User
from ....schemas.catalog import (
    CatalogImageListResponse,
    CatalogImageReorderRequest,
    CatalogImageResponse,
    CatalogImageUploadResponse,
    CatalogItemStaffResponse,
    CoverPopulateResponse,
    CoverStatsResponse,
)
from ....services.storage_service import get_storage
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter()


@router.post("/{item_id}/fetch-cover", response_model=CatalogItemStaffResponse)
@limiter.limit("30/minute")
async def fetch_cover_for_item(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Fetch and update cover image for a single catalog item.

    Tries multiple sources:
    1. Open Library (by ISBN)
    2. Google Books (by ISBN)
    3. Google Books (by title/author)

    Requires staff or admin role.
    """
    from ....services.cover_service import get_cover_url

    item = await get_or_404(db, CatalogItem, item_id, "We couldn't find that item. It may have been removed from the catalog.")

    # Fetch cover URL
    cover_url = await get_cover_url(
        isbn=item.isbn,
        title=item.title,
        author=item.author,
    )

    if cover_url:
        item.cover_url = cover_url
        await db.commit()
        await invalidate_catalog_cache()
        logger.info(f"Updated cover for catalog item {item_id}: {cover_url}")
    else:
        logger.info(f"No cover found for catalog item {item_id}")

    # Re-fetch with eager loading for response serialization
    result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == item_id).options(selectinload(CatalogItem.images))
    )
    return result.scalar_one()


@router.post("/covers/populate", response_model=CoverPopulateResponse)
@limiter.limit("5/minute")
async def populate_covers_batch(
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="Max items to process"),
    overwrite: bool = Query(False, description="Overwrite existing covers"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Batch populate cover images for catalog items.

    Fetches covers from Open Library and Google Books for items
    that don't have covers (or all items if overwrite=True).

    Returns summary of updated items.

    Requires staff or admin role.
    """
    from ....services.cover_service import get_cover_url

    # Query items without covers (or all if overwrite)
    query = select(CatalogItem).order_by(CatalogItem.id)
    if not overwrite:
        query = query.where(
            (CatalogItem.cover_url == None) | (CatalogItem.cover_url == "")
        )
    query = query.limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    semaphore = asyncio.Semaphore(5)

    async def _fetch_one(item):
        async with semaphore:
            try:
                cover_url = await get_cover_url(
                    isbn=item.isbn,
                    title=item.title,
                    author=item.author,
                )
                if cover_url:
                    return {"id": item.id, "title": item.title, "status": "updated", "cover_url": cover_url}
                return {"id": item.id, "title": item.title, "status": "no_cover_found"}
            except Exception as e:  # noqa: BLE001  # external cover fetch per item — record failure
                logger.error("Failed to fetch cover for item %s: %s", item.id, e)
                return {"id": item.id, "title": item.title, "status": "error", "error": str(e)}

    results = await asyncio.gather(*[_fetch_one(item) for item in items])

    # Apply mutations sequentially -- AsyncSession is not safe for concurrent writes
    for item, result in zip(items, results):
        if result["status"] == "updated":
            item.cover_url = result["cover_url"]
    updated = sum(1 for r in results if r["status"] == "updated")
    failed = sum(1 for r in results if r["status"] == "error")
    skipped = sum(1 for r in results if r["status"] == "no_cover_found")

    if updated > 0:
        await db.commit()
        await invalidate_catalog_cache()

    return {
        "processed": len(items),
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }


@router.get("/covers/stats", response_model=CoverStatsResponse)
@limiter.limit("30/minute")
async def get_cover_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics about catalog cover images.

    Returns counts of items with and without covers.
    """
    # Count items with covers
    with_covers_query = select(func.count(CatalogItem.id)).where(
        (CatalogItem.cover_url != None) & (CatalogItem.cover_url != "")
    )
    with_covers_result = await db.execute(with_covers_query)
    with_covers = with_covers_result.scalar() or 0

    # Count items without covers
    without_covers_query = select(func.count(CatalogItem.id)).where(
        (CatalogItem.cover_url == None) | (CatalogItem.cover_url == "")
    )
    without_covers_result = await db.execute(without_covers_query)
    without_covers = without_covers_result.scalar() or 0

    # Count items with ISBN (potential for cover lookup)
    with_isbn_query = select(func.count(CatalogItem.id)).where(
        (CatalogItem.isbn != None) & (CatalogItem.isbn != "") &
        ((CatalogItem.cover_url == None) | (CatalogItem.cover_url == ""))
    )
    with_isbn_result = await db.execute(with_isbn_query)
    with_isbn_no_cover = with_isbn_result.scalar() or 0

    total = with_covers + without_covers
    coverage_percent = (with_covers / total * 100) if total > 0 else 0

    return {
        "total_items": total,
        "with_covers": with_covers,
        "without_covers": without_covers,
        "with_isbn_no_cover": with_isbn_no_cover,
        "coverage_percent": round(coverage_percent, 1),
    }


# ============================================================================
# Catalog Image Endpoints
# ============================================================================


@router.get("/{item_id}/images", response_model=CatalogImageListResponse)
@limiter.limit("60/minute")
async def list_catalog_images(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all images for a catalog item, ordered by display_order."""
    await get_or_404(db, CatalogItem, item_id, "We couldn't find that item. It may have been removed from the catalog.")

    result = await db.execute(
        select(CatalogImage)
        .where(CatalogImage.catalog_item_id == item_id)
        .order_by(CatalogImage.display_order, CatalogImage.id)
    )
    images = result.scalars().all()

    return {
        "images": [CatalogImageResponse.model_validate(img) for img in images],
        "total": len(images),
    }


@router.post(
    "/{item_id}/images",
    response_model=CatalogImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def upload_catalog_image(
    request: Request,
    item_id: int,
    file: UploadFile = File(...),
    is_primary: bool = Query(False, description="Set as primary image"),
    caption: str | None = Query(None, max_length=255, description="Image caption"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Upload an image for a catalog item.

    Accepts PNG, JPEG, GIF, and WebP images up to 10MB.
    Staff-only endpoint.
    """
    await get_or_404(db, CatalogItem, item_id, "We couldn't find that item. It may have been removed from the catalog.")

    content = await file.read()

    # Magic-byte validation
    content_start = content[:16]
    detected_mime = validate_file_type(content_start, file.filename or "image.jpg")
    if detected_mime is None or not detected_mime.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This file doesn't appear to be an image. Please upload a PNG, JPEG, GIF, or WebP file.",
        )

    # File size validation
    if not validate_file_size(len(content), "image"):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="This image is too large (max 10 MB). Try resizing it or choosing a smaller file.",
        )

    from datetime import datetime, timezone

    logger.info(
        "Catalog image upload: user_id=%s filename=%s size=%s mime=%s item_id=%s timestamp=%s",
        current_user.id,
        file.filename,
        len(content),
        detected_mime,
        item_id,
        datetime.now(timezone.utc).isoformat(),
    )

    # Upload to storage
    storage = get_storage()
    storage_key = storage.generate_unique_key(
        prefix=f"catalog-images/{item_id}",
        filename=file.filename or "image.jpg",
    )
    storage_path, _file_hash, file_size = await storage.upload_file(
        file_data=BytesIO(content),
        key=storage_key,
        content_type=detected_mime,
    )

    # If marking as primary, unmark any existing primary image
    if is_primary:
        result = await db.execute(
            select(CatalogImage).where(
                CatalogImage.catalog_item_id == item_id,
                CatalogImage.is_primary == True,
            )
        )
        existing_primary = result.scalar_one_or_none()
        if existing_primary:
            existing_primary.is_primary = False

    # Get next display order
    max_order_result = await db.execute(
        select(func.coalesce(func.max(CatalogImage.display_order), -1)).where(
            CatalogImage.catalog_item_id == item_id
        )
    )
    next_order = (max_order_result.scalar() or 0) + 1

    image = CatalogImage(
        catalog_item_id=item_id,
        image_url=storage_path,
        image_key=storage_key,
        is_primary=is_primary,
        caption=caption,
        display_order=next_order,
        file_size=file_size,
        content_type=detected_mime,
        uploaded_by_id=current_user.id,
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)
    await invalidate_catalog_cache()

    return {
        "success": True,
        "message": "Image uploaded successfully",
        "image": CatalogImageResponse.model_validate(image),
    }


@router.patch("/{item_id}/images/{image_id}", response_model=CatalogImageResponse)
@limiter.limit("30/minute")
async def update_catalog_image(
    request: Request,
    item_id: int,
    image_id: int,
    is_primary: bool | None = Query(None, description="Set as primary image"),
    caption: str | None = Query(None, max_length=255, description="Image caption"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update image metadata (primary status, caption). Staff-only."""
    result = await db.execute(
        select(CatalogImage).where(
            CatalogImage.id == image_id,
            CatalogImage.catalog_item_id == item_id,
        )
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="That image isn't available. It may have been removed.")

    if is_primary is not None and is_primary:
        # Unmark existing primary
        existing_result = await db.execute(
            select(CatalogImage).where(
                CatalogImage.catalog_item_id == item_id,
                CatalogImage.is_primary == True,
                CatalogImage.id != image_id,
            )
        )
        existing_primary = existing_result.scalar_one_or_none()
        if existing_primary:
            existing_primary.is_primary = False
        image.is_primary = True
    elif is_primary is not None:
        image.is_primary = False

    if caption is not None:
        image.caption = caption

    await db.commit()
    await db.refresh(image)
    await invalidate_catalog_cache()

    return image


@router.put("/{item_id}/images/reorder")
@limiter.limit("30/minute")
async def reorder_catalog_images(
    request: Request,
    item_id: int,
    reorder_request: CatalogImageReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Reorder images for a catalog item. Staff-only."""
    await get_or_404(db, CatalogItem, item_id, "We couldn't find that item. It may have been removed from the catalog.")

    result = await db.execute(
        select(CatalogImage).where(CatalogImage.catalog_item_id == item_id)
    )
    images_by_id = {img.id: img for img in result.scalars().all()}

    for order, image_id in enumerate(reorder_request.image_ids):
        if image_id in images_by_id:
            images_by_id[image_id].display_order = order

    await db.commit()
    await invalidate_catalog_cache()

    return {"success": True, "message": "Images reordered successfully"}


@router.delete("/{item_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_catalog_image(
    request: Request,
    item_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete an image from a catalog item. Staff-only."""
    result = await db.execute(
        select(CatalogImage).where(
            CatalogImage.id == image_id,
            CatalogImage.catalog_item_id == item_id,
        )
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="That image isn't available. It may have been removed.")

    # Delete from storage
    storage = get_storage()
    try:
        await storage.delete_file(image.image_key)
    except Exception as e:  # noqa: BLE001  # storage delete best-effort — DB row still removed
        logger.warning(f"Failed to delete image file {image.image_key}: {e}")

    await db.delete(image)
    await db.commit()
    await invalidate_catalog_cache()
