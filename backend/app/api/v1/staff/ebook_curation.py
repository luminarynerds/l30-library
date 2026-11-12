# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff ebook curation routes — featured ebooks and curated collections."""

from app.core.logging import get_logger
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.ebook_curation import (
    CollectionStatus,
    EbookCollection,
    EbookCollectionItem,
    EbookFeatured,
)
from ....models.user import User
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/staff/ebook-curation", tags=["staff-ebook-curation"])


# ---------------------------------------------------------------------------
# Pydantic v2 schemas
# ---------------------------------------------------------------------------

# --- Featured ---

class FeaturedCreate(BaseModel):
    metislib_ebook_id: int
    display_order: Optional[int] = 0
    theme_title: Optional[str] = None
    featured_from: Optional[datetime] = None
    featured_until: Optional[datetime] = None


class FeaturedUpdate(BaseModel):
    theme_title: Optional[str] = None
    featured_from: Optional[datetime] = None
    featured_until: Optional[datetime] = None
    display_order: Optional[int] = None


class FeaturedResponse(BaseModel):
    id: int
    metislib_ebook_id: int
    display_order: int
    theme_title: Optional[str] = None
    featured_from: Optional[datetime] = None
    featured_until: Optional[datetime] = None
    added_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReorderItem(BaseModel):
    id: int
    display_order: int


# --- Collections ---

class CollectionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[CollectionStatus] = CollectionStatus.DRAFT


class CollectionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CollectionStatus] = None


class CollectionResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: CollectionStatus
    display_order: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    item_count: int = 0

    model_config = {"from_attributes": True}


class CollectionItemCreate(BaseModel):
    metislib_ebook_id: int
    display_order: Optional[int] = 0


class CollectionItemResponse(BaseModel):
    collection_id: int
    metislib_ebook_id: int
    display_order: int
    added_at: datetime

    model_config = {"from_attributes": True}


class CollectionReorderItem(BaseModel):
    metislib_ebook_id: int
    display_order: int


# ===========================================================================
# Featured endpoints
# ===========================================================================

@router.get("/featured", response_model=list[FeaturedResponse])
async def list_featured_ebooks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all featured ebooks (staff view, includes expired)."""
    result = await db.execute(
        select(EbookFeatured).order_by(EbookFeatured.display_order)
    )
    return result.scalars().all()


@router.post("/featured", response_model=FeaturedResponse, status_code=status.HTTP_201_CREATED)
async def add_featured_ebook(
    body: FeaturedCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Add an ebook to the featured list."""
    # Check duplicate
    existing = await db.execute(
        select(EbookFeatured).where(
            EbookFeatured.metislib_ebook_id == body.metislib_ebook_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ebook {body.metislib_ebook_id} is already featured",
        )

    featured = EbookFeatured(
        metislib_ebook_id=body.metislib_ebook_id,
        display_order=body.display_order or 0,
        theme_title=body.theme_title,
        featured_from=body.featured_from,
        featured_until=body.featured_until,
        added_by_id=current_user.id,
    )
    db.add(featured)
    await db.commit()
    await db.refresh(featured)

    logger.info(
        "Featured ebook added",
        extra={
            "featured_id": featured.id,
            "metislib_ebook_id": body.metislib_ebook_id,
            "staff_id": current_user.id,
        },
    )
    return featured


@router.delete("/featured/{featured_id:int}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_featured_ebook(
    featured_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Remove a featured ebook."""
    result = await db.execute(
        select(EbookFeatured).where(EbookFeatured.id == featured_id)
    )
    featured = result.scalar_one_or_none()
    if not featured:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Featured ebook not found",
        )

    await db.delete(featured)
    await db.commit()

    logger.info(
        "Featured ebook removed",
        extra={"featured_id": featured_id, "staff_id": current_user.id},
    )
    return None


@router.patch("/featured/{featured_id:int}", response_model=FeaturedResponse)
async def update_featured_ebook(
    featured_id: int,
    body: FeaturedUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a featured ebook's metadata."""
    result = await db.execute(
        select(EbookFeatured).where(EbookFeatured.id == featured_id)
    )
    featured = result.scalar_one_or_none()
    if not featured:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Featured ebook not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(featured, field, value)

    await db.commit()
    await db.refresh(featured)

    logger.info(
        "Featured ebook updated",
        extra={"featured_id": featured_id, "staff_id": current_user.id},
    )
    return featured


@router.put("/featured/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_featured_ebooks(
    items: list[ReorderItem],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Bulk reorder featured ebooks."""
    for item in items:
        await db.execute(
            update(EbookFeatured)
            .where(EbookFeatured.id == item.id)
            .values(display_order=item.display_order)
        )
    await db.commit()

    logger.info(
        "Featured ebooks reordered",
        extra={"count": len(items), "staff_id": current_user.id},
    )
    return None


# ===========================================================================
# Collection endpoints
# ===========================================================================

@router.get("/collections", response_model=list[CollectionResponse])
async def list_collections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all collections (staff view, includes drafts) with item counts."""
    # Subquery for item count
    item_count_subq = (
        select(
            EbookCollectionItem.collection_id,
            func.count().label("item_count"),
        )
        .group_by(EbookCollectionItem.collection_id)
        .subquery()
    )

    result = await db.execute(
        select(
            EbookCollection,
            func.coalesce(item_count_subq.c.item_count, 0).label("item_count"),
        )
        .outerjoin(
            item_count_subq,
            EbookCollection.id == item_count_subq.c.collection_id,
        )
        .order_by(EbookCollection.display_order)
    )

    collections = []
    for row in result.all():
        collection = row[0]
        count = row[1]
        resp = CollectionResponse.model_validate(collection)
        resp.item_count = count
        collections.append(resp)

    return collections


@router.post("/collections", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    body: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new ebook collection."""
    collection = EbookCollection(
        title=body.title,
        description=body.description,
        status=body.status or CollectionStatus.DRAFT,
        created_by_id=current_user.id,
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)

    logger.info(
        "Ebook collection created",
        extra={
            "collection_id": collection.id,
            "title": body.title,
            "staff_id": current_user.id,
        },
    )

    resp = CollectionResponse.model_validate(collection)
    resp.item_count = 0
    return resp


@router.patch("/collections/{collection_id:int}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int,
    body: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a collection's title, description, or status."""
    result = await db.execute(
        select(EbookCollection).where(EbookCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(collection, field, value)

    await db.commit()
    await db.refresh(collection)

    # Get item count
    count_result = await db.execute(
        select(func.count()).where(
            EbookCollectionItem.collection_id == collection_id
        )
    )
    item_count = count_result.scalar() or 0

    logger.info(
        "Ebook collection updated",
        extra={"collection_id": collection_id, "staff_id": current_user.id},
    )

    resp = CollectionResponse.model_validate(collection)
    resp.item_count = item_count
    return resp


@router.delete("/collections/{collection_id:int}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete a collection and all its items (cascade)."""
    result = await db.execute(
        select(EbookCollection).where(EbookCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )

    await db.delete(collection)
    await db.commit()

    logger.info(
        "Ebook collection deleted",
        extra={"collection_id": collection_id, "staff_id": current_user.id},
    )
    return None


@router.get("/collections/{collection_id:int}/items", response_model=list[CollectionItemResponse])
async def list_collection_items(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all ebooks in a collection."""
    # Verify collection exists
    coll_result = await db.execute(
        select(EbookCollection.id).where(EbookCollection.id == collection_id)
    )
    if not coll_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )

    result = await db.execute(
        select(EbookCollectionItem)
        .where(EbookCollectionItem.collection_id == collection_id)
        .order_by(EbookCollectionItem.display_order)
    )
    return result.scalars().all()


@router.post(
    "/collections/{collection_id:int}/items",
    response_model=CollectionItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_item_to_collection(
    collection_id: int,
    body: CollectionItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Add an ebook to a collection."""
    # Verify collection exists
    coll_result = await db.execute(
        select(EbookCollection.id).where(EbookCollection.id == collection_id)
    )
    if not coll_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )

    # Check duplicate
    existing = await db.execute(
        select(EbookCollectionItem).where(
            EbookCollectionItem.collection_id == collection_id,
            EbookCollectionItem.metislib_ebook_id == body.metislib_ebook_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ebook {body.metislib_ebook_id} is already in this collection",
        )

    item = EbookCollectionItem(
        collection_id=collection_id,
        metislib_ebook_id=body.metislib_ebook_id,
        display_order=body.display_order or 0,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    logger.info(
        "Ebook added to collection",
        extra={
            "collection_id": collection_id,
            "metislib_ebook_id": body.metislib_ebook_id,
            "staff_id": current_user.id,
        },
    )
    return item


@router.delete(
    "/collections/{collection_id:int}/items/{ebook_id:int}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_item_from_collection(
    collection_id: int,
    ebook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Remove an ebook from a collection."""
    result = await db.execute(
        select(EbookCollectionItem).where(
            EbookCollectionItem.collection_id == collection_id,
            EbookCollectionItem.metislib_ebook_id == ebook_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ebook not found in this collection",
        )

    await db.delete(item)
    await db.commit()

    logger.info(
        "Ebook removed from collection",
        extra={
            "collection_id": collection_id,
            "metislib_ebook_id": ebook_id,
            "staff_id": current_user.id,
        },
    )
    return None


@router.put(
    "/collections/{collection_id:int}/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reorder_collection_items(
    collection_id: int,
    items: list[CollectionReorderItem],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Bulk reorder ebooks within a collection."""
    # Verify collection exists
    coll_result = await db.execute(
        select(EbookCollection.id).where(EbookCollection.id == collection_id)
    )
    if not coll_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )

    for item in items:
        await db.execute(
            update(EbookCollectionItem)
            .where(
                EbookCollectionItem.collection_id == collection_id,
                EbookCollectionItem.metislib_ebook_id == item.metislib_ebook_id,
            )
            .values(display_order=item.display_order)
        )
    await db.commit()

    logger.info(
        "Collection items reordered",
        extra={
            "collection_id": collection_id,
            "count": len(items),
            "staff_id": current_user.id,
        },
    )
    return None
