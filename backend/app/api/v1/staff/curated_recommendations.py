# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Curated Recommendations Management

Endpoints for staff to pin, suppress, and reorder catalog item recommendations.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.catalog import CatalogItem
from ....models.curated_recommendations import CuratedRecommendation
from ....models.user import User
from ..dependencies import require_staff

router = APIRouter(prefix="/staff", tags=["staff-curated-recommendations"])


class CurationAction(BaseModel):
    target_item_id: int
    action: str  # "pin" | "suppress" | "remove"
    display_order: Optional[int] = None
    staff_note: Optional[str] = None


class CurationResponse(BaseModel):
    id: int
    source_item_id: int
    target_item_id: int
    display_order: int
    is_hidden: bool
    staff_note: Optional[str] = None

    model_config = {"from_attributes": True}


class ReorderRequest(BaseModel):
    item_ids: list[int]


class ReorderResponse(BaseModel):
    updated: int


@router.post(
    "/catalog/{item_id}/recommendations",
    response_model=CurationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def curate_recommendation(
    item_id: int,
    body: CurationAction,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Pin, suppress, or remove a recommendation for a catalog item."""

    # Validate source item exists
    source_stmt = select(CatalogItem).where(CatalogItem.id == item_id)
    source_result = await db.execute(source_stmt)
    if not source_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Source catalog item not found")

    # Validate target item exists
    target_stmt = select(CatalogItem).where(CatalogItem.id == body.target_item_id)
    target_result = await db.execute(target_stmt)
    if not target_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Target catalog item not found")

    if item_id == body.target_item_id:
        raise HTTPException(status_code=400, detail="Cannot recommend an item to itself")

    if body.action == "remove":
        del_stmt = delete(CuratedRecommendation).where(
            CuratedRecommendation.source_item_id == item_id,
            CuratedRecommendation.target_item_id == body.target_item_id,
        )
        await db.execute(del_stmt)
        await db.flush()
        # Return a stub response for the removed record
        return CurationResponse(
            id=0,
            source_item_id=item_id,
            target_item_id=body.target_item_id,
            display_order=0,
            is_hidden=False,
            staff_note=None,
        )

    # Check for existing record
    existing_stmt = select(CuratedRecommendation).where(
        CuratedRecommendation.source_item_id == item_id,
        CuratedRecommendation.target_item_id == body.target_item_id,
    )
    existing_result = await db.execute(existing_stmt)
    rec = existing_result.scalar_one_or_none()

    if body.action == "pin":
        if rec:
            rec.is_hidden = False
            rec.display_order = body.display_order if body.display_order is not None else rec.display_order
            rec.staff_note = body.staff_note if body.staff_note is not None else rec.staff_note
        else:
            rec = CuratedRecommendation(
                source_item_id=item_id,
                target_item_id=body.target_item_id,
                display_order=body.display_order or 0,
                is_hidden=False,
                staff_note=body.staff_note,
                created_by_id=staff_user.id,
            )
            db.add(rec)

    elif body.action == "suppress":
        if rec:
            rec.is_hidden = True
        else:
            rec = CuratedRecommendation(
                source_item_id=item_id,
                target_item_id=body.target_item_id,
                display_order=0,
                is_hidden=True,
                staff_note=body.staff_note,
                created_by_id=staff_user.id,
            )
            db.add(rec)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {body.action}. Use pin, suppress, or remove.")

    await db.flush()
    return CurationResponse.model_validate(rec)


@router.put(
    "/catalog/{item_id}/recommendations/reorder",
    response_model=ReorderResponse,
)
async def reorder_recommendations(
    item_id: int,
    body: ReorderRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Reorder pinned recommendations for a catalog item."""
    updated = 0
    for idx, target_id in enumerate(body.item_ids):
        stmt = select(CuratedRecommendation).where(
            CuratedRecommendation.source_item_id == item_id,
            CuratedRecommendation.target_item_id == target_id,
            CuratedRecommendation.is_hidden == False,
        )
        result = await db.execute(stmt)
        rec = result.scalar_one_or_none()
        if rec:
            rec.display_order = idx
            updated += 1

    await db.flush()
    return ReorderResponse(updated=updated)
