# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Favorites and Reading Lists API endpoints."""

import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models import CatalogItem, Favorite, ListItem, ReadingList, User
from ...schemas.favorites import (FavoriteCreate, FavoriteResponse,
                                  ListItemCreate, ListItemResponse,
                                  ReadingListCreate, ReadingListResponse,
                                  ReadingListUpdate, ReadingListWithItems)
from ...services.privacy_audit import PrivacyAuditLogger
from .auth import get_current_user

router = APIRouter(tags=["favorites"])


# ============================================================================
# FAVORITES
# ============================================================================


@router.get("/favorites", response_model=List[FavoriteResponse])
async def get_my_favorites(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's favorites with pagination."""
    result = await db.execute(
        select(Favorite)
        .options(selectinload(Favorite.catalog_item))
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.post(
    "/favorites", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED
)
async def add_favorite(
    data: FavoriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a catalog item to favorites."""
    # Check if catalog item exists
    await get_or_404(db, CatalogItem, data.catalog_item_id, "Catalog item not found")

    # Check if already favorited
    existing = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.catalog_item_id == data.catalog_item_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already in favorites")

    favorite = Favorite(user_id=current_user.id, catalog_item_id=data.catalog_item_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)

    # Load the catalog item relationship
    result = await db.execute(
        select(Favorite)
        .options(selectinload(Favorite.catalog_item))
        .where(Favorite.id == favorite.id)
    )
    return result.scalar_one()


@router.delete("/favorites/{catalog_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    catalog_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a catalog item from favorites."""
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.catalog_item_id == catalog_item_id,
        )
    )
    favorite = result.scalar_one_or_none()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    await db.delete(favorite)
    await db.commit()


# ============================================================================
# READING LISTS
# ============================================================================


@router.get("/lists", response_model=List[ReadingListResponse])
async def get_my_lists(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get current user's reading lists with item counts."""
    result = await db.execute(
        select(ReadingList, func.count(ListItem.id).label("item_count"))
        .outerjoin(ListItem)
        .where(ReadingList.user_id == current_user.id)
        .group_by(ReadingList.id)
        .order_by(ReadingList.created_at.desc())
    )
    lists = []
    for row in result:
        reading_list = row[0]
        reading_list.item_count = row[1]
        lists.append(reading_list)
    return lists


@router.post(
    "/lists", response_model=ReadingListResponse, status_code=status.HTTP_201_CREATED
)
async def create_list(
    data: ReadingListCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new reading list."""
    reading_list = ReadingList(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        is_public=data.is_public,
        share_token=generate_share_token() if data.is_public else None,
    )
    db.add(reading_list)
    await db.commit()
    await db.refresh(reading_list)

    if data.is_public:
        await PrivacyAuditLogger.log_reading_list_privacy_change(
            db=db,
            user_id=current_user.id,
            list_id=reading_list.id,
            old_is_public=False,
            new_is_public=True,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent", "")[:500],
        )

    reading_list.item_count = 0
    return reading_list


@router.get("/lists/{list_id}", response_model=ReadingListWithItems)
async def get_list(
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a reading list with all items."""
    result = await db.execute(
        select(ReadingList)
        .options(selectinload(ReadingList.items).selectinload(ListItem.catalog_item))
        .where(ReadingList.id == list_id, ReadingList.user_id == current_user.id)
    )
    reading_list = result.scalar_one_or_none()
    if not reading_list:
        raise HTTPException(status_code=404, detail="List not found")
    reading_list.item_count = len(reading_list.items)
    return reading_list


@router.patch("/lists/{list_id}", response_model=ReadingListResponse)
async def update_list(
    list_id: int,
    data: ReadingListUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a reading list.

    Allows updating name, description, and privacy status (is_public).
    Privacy changes are logged in the audit trail for compliance.
    """
    result = await db.execute(
        select(ReadingList).where(
            ReadingList.id == list_id, ReadingList.user_id == current_user.id
        )
    )
    reading_list = result.scalar_one_or_none()
    if not reading_list:
        raise HTTPException(status_code=404, detail="List not found")

    # Track old privacy value for audit logging
    old_is_public = reading_list.is_public

    if data.name is not None:
        reading_list.name = data.name
    if data.description is not None:
        reading_list.description = data.description
    if data.is_public is not None:
        reading_list.is_public = data.is_public

        # Auto-generate share token when list is made public (if not already present)
        if data.is_public and not reading_list.share_token:
            reading_list.share_token = generate_share_token()

    # Log privacy changes to audit trail
    if data.is_public is not None and data.is_public != old_is_public:
        await PrivacyAuditLogger.log_reading_list_privacy_change(
            db=db,
            user_id=current_user.id,
            list_id=list_id,
            old_is_public=old_is_public,
            new_is_public=data.is_public,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent", "")[:500],
        )

    await db.commit()
    await db.refresh(reading_list)
    return reading_list


@router.delete("/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a reading list."""
    result = await db.execute(
        select(ReadingList).where(
            ReadingList.id == list_id, ReadingList.user_id == current_user.id
        )
    )
    reading_list = result.scalar_one_or_none()
    if not reading_list:
        raise HTTPException(status_code=404, detail="List not found")

    await db.delete(reading_list)
    await db.commit()


# ============================================================================
# READING LIST SHARING
# ============================================================================


def generate_share_token() -> str:
    return secrets.token_urlsafe(24)[:32]


@router.post("/lists/{list_id}/share/generate-token", status_code=status.HTTP_200_OK)
async def generate_share_token_endpoint(
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a new share token for a reading list.

    This endpoint generates a unique, shareable token for a reading list.
    The list must be marked as public (is_public=true) to generate a token.
    """
    # Fetch the reading list
    result = await db.execute(
        select(ReadingList).where(
            ReadingList.id == list_id, ReadingList.user_id == current_user.id
        )
    )
    reading_list = result.scalar_one_or_none()
    if not reading_list:
        raise HTTPException(status_code=404, detail="List not found")

    # Require list to be public
    if not reading_list.is_public:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="List must be public to generate a share token",
        )

    # Generate new token (replaces any existing token)
    reading_list.share_token = generate_share_token()

    await db.commit()
    await db.refresh(reading_list)

    return {
        "id": reading_list.id,
        "name": reading_list.name,
        "share_token": reading_list.share_token,
        "share_url": f"/api/v1/reading-lists/share/{reading_list.share_token}",
    }


@router.get("/reading-lists/share/{token}", response_model=ReadingListWithItems, tags=["favorites"])
async def get_shared_reading_list(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a publicly shared reading list by token (no authentication required).

    This endpoint allows anyone to view a publicly shared reading list
    using the share token. The list must be public and have a valid token.
    """
    # Validate token format (basic security)
    if not token or len(token) < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid share token",
        )

    # Find reading list by share token
    result = await db.execute(
        select(ReadingList)
        .options(selectinload(ReadingList.items).selectinload(ListItem.catalog_item))
        .where(
            ReadingList.share_token == token,
            ReadingList.is_public == True,  # noqa: E712
        )
    )
    reading_list = result.scalar_one_or_none()

    if not reading_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reading list not found or is not publicly shared",
        )

    # Add item count
    reading_list.item_count = len(reading_list.items)

    return reading_list


# ============================================================================
# LIST ITEMS
# ============================================================================


@router.post(
    "/lists/{list_id}/items",
    response_model=ListItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_list(
    list_id: int,
    data: ListItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an item to a reading list."""
    # Check list ownership
    result = await db.execute(
        select(ReadingList).where(
            ReadingList.id == list_id, ReadingList.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="List not found")

    # Check catalog item exists
    await get_or_404(db, CatalogItem, data.catalog_item_id, "Catalog item not found")

    # Check if already in list
    existing = await db.execute(
        select(ListItem).where(
            ListItem.list_id == list_id,
            ListItem.catalog_item_id == data.catalog_item_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Item already in list")

    list_item = ListItem(list_id=list_id, catalog_item_id=data.catalog_item_id)
    db.add(list_item)
    await db.commit()
    await db.refresh(list_item)

    # Load catalog item
    result = await db.execute(
        select(ListItem)
        .options(selectinload(ListItem.catalog_item))
        .where(ListItem.id == list_item.id)
    )
    return result.scalar_one()


@router.delete(
    "/lists/{list_id}/items/{catalog_item_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_from_list(
    list_id: int,
    catalog_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an item from a reading list."""
    # Check list ownership
    result = await db.execute(
        select(ReadingList).where(
            ReadingList.id == list_id, ReadingList.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="List not found")

    # Find and delete the item
    result = await db.execute(
        select(ListItem).where(
            ListItem.list_id == list_id, ListItem.catalog_item_id == catalog_item_id
        )
    )
    list_item = result.scalar_one_or_none()
    if not list_item:
        raise HTTPException(status_code=404, detail="Item not in list")

    await db.delete(list_item)
    await db.commit()


