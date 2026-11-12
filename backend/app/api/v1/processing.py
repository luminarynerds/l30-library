# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Processing queue router.

Kanban-style pipeline for newly received items:
  Received -> Labeling -> RFID Tagging -> Ready to Shelve -> Shelved

All endpoints are staff-only.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.catalog import CatalogItem, CatalogingStatus
from ...models.inventory import ItemCopy, ProcessingStep
from ...models.lifecycle import LifecycleEventType
from ...models.user import User
from .auth import get_current_user
from .dependencies import require_staff
from .lifecycle import create_lifecycle_event

router = APIRouter(prefix="/processing", tags=["processing"])

# Ordered step progression
STEP_ORDER = [
    ProcessingStep.RECEIVED,
    ProcessingStep.LABELING,
    ProcessingStep.RFID_TAGGING,
    ProcessingStep.READY_TO_SHELVE,
    ProcessingStep.SHELVED,
]


# ---------- Schemas ----------

class BulkAdvanceRequest(BaseModel):
    copy_ids: list[int]


# ---------- Helpers ----------

def _serialize_item(row) -> dict:
    return {
        "copy_id": row.copy_id,
        "item_id": row.item_id,
        "title": row.title or "",
        "author": row.author,
        "barcode": row.barcode,
        "call_number": row.call_number,
        "current_step": str(row.processing_step) if row.processing_step else None,
        "assigned_staff_id": None,
        "assigned_staff_name": None,
        "received_at": row.created_at.isoformat() if row.created_at else None,
        "time_in_step": None,
    }


async def _advance_single(
    db: AsyncSession,
    copy_id: int,
    performed_by_id: int,
) -> dict:
    result = await db.execute(
        select(
            ItemCopy.id.label("copy_id"),
            ItemCopy.catalog_item_id.label("item_id"),
            ItemCopy.barcode,
            ItemCopy.processing_step,
            ItemCopy.created_at,
            CatalogItem.title,
            CatalogItem.author,
            CatalogItem.call_number,
            CatalogItem.cataloging_status,
        )
        .join(CatalogItem, CatalogItem.id == ItemCopy.catalog_item_id)
        .where(ItemCopy.id == copy_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item copy not found")

    current_step = row.processing_step
    if current_step is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item is not in the processing queue",
        )

    try:
        idx = STEP_ORDER.index(current_step)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown processing step: {current_step}",
        ) from None

    if idx >= len(STEP_ORDER) - 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item is already at the final step",
        )

    next_step = STEP_ORDER[idx + 1]

    # Update processing step via direct SQL (avoids loading full ORM object)
    await db.execute(
        update(ItemCopy)
        .where(ItemCopy.id == copy_id)
        .values(processing_step=next_step)
    )

    # If advancing to SHELVED, mark catalog item as cataloged and fire event
    if next_step == ProcessingStep.SHELVED:
        if row.cataloging_status != CatalogingStatus.CATALOGED:
            await db.execute(
                update(CatalogItem)
                .where(CatalogItem.id == row.item_id)
                .values(cataloging_status=CatalogingStatus.CATALOGED)
            )

        await create_lifecycle_event(
            db=db,
            item_copy_id=copy_id,
            event_type=LifecycleEventType.SHELVED,
            description="Item completed processing and moved to shelf",
            metadata={"previous_step": current_step.value},
            performed_by_id=performed_by_id,
        )

    return {
        "status": "advanced",
        "message": f"Moved from {current_step.value} to {next_step.value}",
    }


# ---------- Endpoints ----------

@router.get("/queue")
async def get_processing_queue(
    branch_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get all items in the processing queue, grouped by step."""
    # Only active steps (not SHELVED)
    active_steps = [
        ProcessingStep.RECEIVED,
        ProcessingStep.LABELING,
        ProcessingStep.RFID_TAGGING,
        ProcessingStep.READY_TO_SHELVE,
    ]

    stmt = (
        select(
            ItemCopy.id.label("copy_id"),
            ItemCopy.catalog_item_id.label("item_id"),
            ItemCopy.barcode,
            ItemCopy.processing_step,
            ItemCopy.created_at,
            CatalogItem.title,
            CatalogItem.author,
            CatalogItem.call_number,
        )
        .join(CatalogItem, CatalogItem.id == ItemCopy.catalog_item_id)
        .where(ItemCopy.processing_step.in_(active_steps))
        .order_by(ItemCopy.created_at.asc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    grouped: dict[str, list] = {
        "received": [],
        "labeling": [],
        "rfid_tagging": [],
        "ready_to_shelve": [],
    }
    totals: dict[str, int] = {
        "received": 0,
        "labeling": 0,
        "rfid_tagging": 0,
        "ready_to_shelve": 0,
    }

    for row in rows:
        step_val = str(row.processing_step)
        if step_val in grouped:
            grouped[step_val].append(_serialize_item(row))
            totals[step_val] += 1

    return {**grouped, "totals": totals}


@router.post("/queue/{copy_id}/advance")
async def advance_item(
    copy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Advance an item to the next processing step."""
    result = await _advance_single(db, copy_id, current_user.id)
    await db.commit()
    return result


@router.post("/queue/bulk-advance")
async def bulk_advance(
    body: BulkAdvanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Advance multiple items to their next processing step."""
    results = []
    for cid in body.copy_ids:
        try:
            res = await _advance_single(db, cid, current_user.id)
            results.append({"copy_id": cid, "status": res["status"]})
        except HTTPException as exc:
            results.append({"copy_id": cid, "error": exc.detail})

    await db.commit()
    return {"results": results}


@router.get("/queue/stats")
async def get_queue_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get counts per processing step."""
    stmt = (
        select(
            ItemCopy.processing_step,
            func.count().label("cnt"),
        )
        .where(ItemCopy.processing_step.isnot(None))
        .group_by(ItemCopy.processing_step)
    )
    result = await db.execute(stmt)
    rows = result.all()

    total = 0
    for row in rows:
        if row.processing_step != ProcessingStep.SHELVED:
            total += row.cnt

    return {"total_in_processing": total}
