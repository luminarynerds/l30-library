# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Availability watch endpoints -- lightweight notify-when-available for checked-out items."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.catalog import CatalogItem, CatalogingStatus, SensitivityLevel
from ....models.availability_watch import AvailabilityWatch
from ....models.user import User, UserRole
from ..auth import get_current_user
from ..dependencies import is_staff_or_admin

router = APIRouter()


class WatchResponse(BaseModel):
    id: int
    catalog_item_id: int
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_watch(cls, watch: AvailabilityWatch) -> "WatchResponse":
        return cls(
            id=watch.id,
            catalog_item_id=watch.catalog_item_id,
            is_active=watch.is_active,
            created_at=watch.created_at.isoformat() if watch.created_at else "",
        )


class WatchStatusResponse(BaseModel):
    watching: bool


@router.post(
    "/items/{item_id}/watch",
    response_model=WatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_watch(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Watch a catalog item for availability. Sends a notification when returned.

    Visibility-gated: a patron can only watch items they can see via
    ``GET /catalog/items/{id}``. Without this gate a patron who guesses an
    item id could subscribe to availability notifications on CONFIDENTIAL
    or non-cataloged records.
    """
    item = await get_or_404(db, CatalogItem, item_id, "Catalog item not found")

    if item.cataloging_status != CatalogingStatus.CATALOGED and not is_staff_or_admin(current_user):
        raise HTTPException(status_code=404, detail="Catalog item not found")
    if current_user.role == UserRole.PATRON and item.sensitivity_level == SensitivityLevel.CONFIDENTIAL:
        raise HTTPException(status_code=404, detail="Catalog item not found")

    result = await db.execute(
        select(AvailabilityWatch).where(
            AvailabilityWatch.user_id == current_user.id,
            AvailabilityWatch.catalog_item_id == item_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="Already watching this item")
        existing.is_active = True
        existing.notified_at = None
        await db.commit()
        await db.refresh(existing)
        return WatchResponse.from_watch(existing)

    watch = AvailabilityWatch(user_id=current_user.id, catalog_item_id=item_id)
    db.add(watch)
    await db.commit()
    await db.refresh(watch)
    return WatchResponse.from_watch(watch)


@router.delete("/items/{item_id}/watch", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watch(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stop watching a catalog item."""
    result = await db.execute(
        select(AvailabilityWatch).where(
            AvailabilityWatch.user_id == current_user.id,
            AvailabilityWatch.catalog_item_id == item_id,
            AvailabilityWatch.is_active == True,  # noqa: E712
        )
    )
    watch = result.scalar_one_or_none()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")

    watch.is_active = False
    await db.commit()


@router.get("/items/{item_id}/watch", response_model=WatchStatusResponse)
async def check_watch(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if the current user is watching a catalog item."""
    result = await db.execute(
        select(AvailabilityWatch).where(
            AvailabilityWatch.user_id == current_user.id,
            AvailabilityWatch.catalog_item_id == item_id,
            AvailabilityWatch.is_active == True,  # noqa: E712
        )
    )
    return WatchStatusResponse(watching=result.scalar_one_or_none() is not None)
