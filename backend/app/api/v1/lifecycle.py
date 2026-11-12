# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ...core.database import get_db
from ...models.catalog import CatalogItem
from ...models.inventory import ItemCopy
from ...models.lifecycle import ItemLifecycleEvent, LifecycleEventType
from ...models.user import User, UserRole
from ...schemas.lifecycle import (LifecycleEventCreate, LifecycleEventResponse,
                                  LifecycleTimelineResponse)
from .auth import get_current_user
from .dependencies import require_staff

router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])


async def create_lifecycle_event(
    db: AsyncSession,
    item_copy_id: int,
    event_type: LifecycleEventType,
    description: str | None = None,
    metadata: dict | None = None,
    performed_by_id: int | None = None,
    related_checkout_id: int | None = None,
    related_po_id: int | None = None,
    related_audit_id: int | None = None,
    related_weeding_id: int | None = None,
) -> ItemLifecycleEvent:
    event = ItemLifecycleEvent(
        item_copy_id=item_copy_id,
        event_type=event_type,
        description=description,
        event_metadata=metadata or {},
        performed_by_id=performed_by_id,
        related_checkout_id=related_checkout_id,
        related_po_id=related_po_id,
        related_audit_id=related_audit_id,
        related_weeding_id=related_weeding_id,
    )
    db.add(event)
    await db.flush()
    return event


@router.get("/search")
async def search_items_for_lifecycle(
    q: str = Query(..., min_length=1, description="Search by title, author, or barcode"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search catalog items and copies by title, author, or barcode.
    Returns matching items with their copy info for lifecycle lookup.
    """
    await require_staff(current_user)
    term = f"%{q.strip()}%"

    result = await db.execute(
        select(
            ItemCopy.id.label("copy_id"),
            ItemCopy.barcode,
            ItemCopy.condition,
            CatalogItem.id.label("catalog_item_id"),
            CatalogItem.title,
            CatalogItem.author,
            CatalogItem.isbn,
            CatalogItem.call_number,
        )
        .join(CatalogItem, CatalogItem.id == ItemCopy.catalog_item_id)
        .where(
            or_(
                CatalogItem.title.ilike(term),
                CatalogItem.author.ilike(term),
                CatalogItem.isbn.ilike(term),
                CatalogItem.call_number.ilike(term),
                ItemCopy.barcode.ilike(term),
            )
        )
        .order_by(CatalogItem.title)
        .limit(50)
    )
    rows = result.all()

    return [
        {
            "copy_id": row.copy_id,
            "barcode": row.barcode,
            "condition": row.condition,
            "catalog_item_id": row.catalog_item_id,
            "title": row.title,
            "author": row.author,
            "isbn": row.isbn,
            "call_number": row.call_number,
        }
        for row in rows
    ]


@router.get("/item-copy/{copy_id}", response_model=LifecycleTimelineResponse)
async def get_item_copy_lifecycle(
    copy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get complete lifecycle timeline for a specific item copy.
    Staff only.
    """
    await require_staff(current_user)
    # Verify copy exists
    result = await db.execute(
        select(ItemCopy)
        .options(joinedload(ItemCopy.catalog_item))
        .where(ItemCopy.id == copy_id)
    )
    copy = result.scalar_one_or_none()

    if not copy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item copy not found"
        )

    # Fetch all lifecycle events for this copy
    result = await db.execute(
        select(ItemLifecycleEvent)
        .options(joinedload(ItemLifecycleEvent.performed_by))
        .where(ItemLifecycleEvent.item_copy_id == copy_id)
        .order_by(ItemLifecycleEvent.created_at.desc())
    )
    events = result.scalars().all()

    # Build response with enriched data
    event_responses = []
    for event in events:
        event_dict = {
            "id": event.id,
            "item_copy_id": event.item_copy_id,
            "event_type": event.event_type,
            "description": event.description,
            "metadata": event.event_metadata,
            "performed_by_id": event.performed_by_id,
            "related_checkout_id": event.related_checkout_id,
            "related_po_id": event.related_po_id,
            "related_audit_id": event.related_audit_id,
            "related_weeding_id": event.related_weeding_id,
            "created_at": event.created_at,
            "performed_by_name": (
                f"{event.performed_by.first_name} {event.performed_by.last_name}"
                if event.performed_by
                else None
            ),
            "performed_by_email": (
                event.performed_by.email if event.performed_by else None
            ),
            "item_copy_barcode": copy.barcode,
            "item_title": copy.catalog_item.title if copy.catalog_item else None,
            "item_author": copy.catalog_item.author if copy.catalog_item else None,
        }
        event_responses.append(LifecycleEventResponse(**event_dict))

    return LifecycleTimelineResponse(
        item_copy_id=copy_id,
        item_copy_barcode=copy.barcode,
        item_title=copy.catalog_item.title if copy.catalog_item else None,
        item_author=copy.catalog_item.author if copy.catalog_item else None,
        events=event_responses,
        total_events=len(event_responses),
    )


@router.get("/item/{item_id}", response_model=List[LifecycleTimelineResponse])
async def get_catalog_item_lifecycle(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get lifecycle timelines for all copies of a catalog item.
    Returns a list of timelines, one per copy.
    Staff only.
    """
    await require_staff(current_user)
    # Verify item exists
    result = await db.execute(select(CatalogItem).where(CatalogItem.id == item_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found"
        )

    # Get all copies for this item
    result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.catalog_item_id == item_id)
        .order_by(ItemCopy.id)
    )
    copies = result.scalars().all()

    # Get lifecycle for each copy
    timelines = []
    for copy in copies:
        timeline = await get_item_copy_lifecycle(copy.id, db, current_user)
        timelines.append(timeline)

    return timelines


@router.post(
    "/events",
    response_model=LifecycleEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_lifecycle_event(
    event_data: LifecycleEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually create a lifecycle event (e.g., for notes or custom tracking).
    Staff only.
    """
    await require_staff(current_user)
    # Verify copy exists
    result = await db.execute(
        select(ItemCopy)
        .options(joinedload(ItemCopy.catalog_item))
        .where(ItemCopy.id == event_data.item_copy_id)
    )
    copy = result.scalar_one_or_none()

    if not copy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item copy not found"
        )

    # Create the event
    event = await create_lifecycle_event(
        db=db,
        item_copy_id=event_data.item_copy_id,
        event_type=event_data.event_type,
        description=event_data.description,
        metadata=event_data.metadata,
        performed_by_id=current_user.id,
        related_checkout_id=event_data.related_checkout_id,
        related_po_id=event_data.related_po_id,
        related_audit_id=event_data.related_audit_id,
        related_weeding_id=event_data.related_weeding_id,
    )

    await db.commit()
    await db.refresh(event)

    # Load performer relationship
    await db.refresh(event, ["performed_by"])

    return LifecycleEventResponse(
        id=event.id,
        item_copy_id=event.item_copy_id,
        event_type=event.event_type,
        description=event.description,
        metadata=event.event_metadata,
        performed_by_id=event.performed_by_id,
        related_checkout_id=event.related_checkout_id,
        related_po_id=event.related_po_id,
        related_audit_id=event.related_audit_id,
        related_weeding_id=event.related_weeding_id,
        created_at=event.created_at,
        performed_by_name=(
            f"{event.performed_by.first_name} {event.performed_by.last_name}"
            if event.performed_by
            else None
        ),
        performed_by_email=event.performed_by.email if event.performed_by else None,
        item_copy_barcode=copy.barcode,
        item_title=copy.catalog_item.title if copy.catalog_item else None,
        item_author=copy.catalog_item.author if copy.catalog_item else None,
    )

# --- Batch lifecycle event models and endpoint ---

from typing import Optional
from pydantic import BaseModel


class BatchItemInput(BaseModel):
    item_copy_id: int


class BatchLifecycleEventCreate(BaseModel):
    event_type: LifecycleEventType
    description: Optional[str] = None
    items: List[BatchItemInput]


class BatchResultItem(BaseModel):
    item_copy_id: int
    status: str
    event_id: Optional[int] = None
    message: Optional[str] = None


class BatchLifecycleEventResponse(BaseModel):
    results: List[BatchResultItem]
    total_processed: int
    total_success: int
    total_errors: int


@router.post(
    "/events/batch",
    response_model=BatchLifecycleEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch_lifecycle_events(
    batch_data: BatchLifecycleEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create lifecycle events for multiple item copies in a single batch.
    Staff only. Max 100 items per batch.
    """
    await require_staff(current_user)

    if len(batch_data.items) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size cannot exceed 100 items",
        )

    results: List[BatchResultItem] = []
    total_success = 0
    total_errors = 0

    for item in batch_data.items:
        # Verify copy exists
        result = await db.execute(
            select(ItemCopy).where(ItemCopy.id == item.item_copy_id)
        )
        copy = result.scalar_one_or_none()

        if not copy:
            results.append(
                BatchResultItem(
                    item_copy_id=item.item_copy_id,
                    status="error",
                    message=f"Item copy {item.item_copy_id} not found",
                )
            )
            total_errors += 1
            continue

        try:
            event = await create_lifecycle_event(
                db=db,
                item_copy_id=item.item_copy_id,
                event_type=batch_data.event_type,
                description=batch_data.description,
                performed_by_id=current_user.id,
            )
            results.append(
                BatchResultItem(
                    item_copy_id=item.item_copy_id,
                    status="success",
                    event_id=event.id,
                )
            )
            total_success += 1
        except Exception as e:  # noqa: BLE001  # per-item batch — record failure and continue
            results.append(
                BatchResultItem(
                    item_copy_id=item.item_copy_id,
                    status="error",
                    message=str(e),
                )
            )
            total_errors += 1

    await db.commit()

    return BatchLifecycleEventResponse(
        results=results,
        total_processed=len(batch_data.items),
        total_success=total_success,
        total_errors=total_errors,
    )
