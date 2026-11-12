# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Admin CRUD API for homepage quotes (staff-only)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.homepage_quote import (
    HomepageQuoteAdmin,
    HomepageQuoteCreate,
    HomepageQuoteUpdate,
)
from ...services import homepage_quote_service
from .dependencies import require_staff

router = APIRouter(prefix="/admin/homepage-quotes", tags=["admin-homepage-quotes"])


@router.get("", response_model=List[HomepageQuoteAdmin])
async def admin_list_quotes(
    locale: Optional[str] = Query(default=None, min_length=2, max_length=8),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List every homepage quote (optionally filtered by locale)."""
    quotes = await homepage_quote_service.list_all(db, locale=locale)
    return [HomepageQuoteAdmin.model_validate(q) for q in quotes]


@router.post("", response_model=HomepageQuoteAdmin, status_code=status.HTTP_201_CREATED)
async def admin_create_quote(
    data: HomepageQuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    quote = await homepage_quote_service.create(
        db,
        locale=data.locale,
        quote_text=data.quote_text,
        attribution=data.attribution,
        is_active=data.is_active,
        display_order=data.display_order,
    )
    return HomepageQuoteAdmin.model_validate(quote)


@router.put("/{quote_id}", response_model=HomepageQuoteAdmin)
async def admin_update_quote(
    quote_id: int,
    data: HomepageQuoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    quote = await homepage_quote_service.get_by_id(db, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Homepage quote not found")
    updated = await homepage_quote_service.update(
        db,
        quote,
        locale=data.locale,
        quote_text=data.quote_text,
        attribution=data.attribution,
        is_active=data.is_active,
        display_order=data.display_order,
    )
    return HomepageQuoteAdmin.model_validate(updated)


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_quote(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    quote = await homepage_quote_service.get_by_id(db, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Homepage quote not found")
    await homepage_quote_service.delete(db, quote)
