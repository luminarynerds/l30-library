# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Admin CRUD endpoints for PatronCategory.

Gated by require_admin. PatronCategory is org-level config; staff-level
access is not sufficient.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_admin
from app.core.database import get_db
from app.models.patron_category import PatronCategory
from app.schemas.patron_category import (
    PatronCategoryCreate,
    PatronCategoryRead,
    PatronCategoryUpdate,
)

router = APIRouter(prefix="/admin/patron-categories", tags=["admin", "patron-categories"])


@router.get("", response_model=List[PatronCategoryRead])
async def list_patron_categories(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
) -> List[PatronCategory]:
    """List patron categories. Defaults to active only."""
    stmt = select(PatronCategory).order_by(PatronCategory.code)
    if not include_inactive:
        stmt = stmt.where(PatronCategory.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{category_id}", response_model=PatronCategoryRead)
async def get_patron_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
) -> PatronCategory:
    category = await db.get(PatronCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="PatronCategory not found")
    return category


@router.post("", response_model=PatronCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_patron_category(
    payload: PatronCategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
) -> PatronCategory:
    """Create a new patron category. Codes are uppercased on save."""
    category = PatronCategory(
        code=payload.code.strip().upper(),
        label=payload.label.strip(),
        is_active=payload.is_active,
    )
    db.add(category)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"PatronCategory with code '{category.code}' already exists",
        ) from None
    await db.refresh(category)
    return category


@router.put("/{category_id}", response_model=PatronCategoryRead)
async def update_patron_category(
    category_id: int,
    payload: PatronCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
) -> PatronCategory:
    category = await db.get(PatronCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="PatronCategory not found")

    if payload.code is not None:
        category.code = payload.code.strip().upper()
    if payload.label is not None:
        category.label = payload.label.strip()
    if payload.is_active is not None:
        category.is_active = payload.is_active

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"PatronCategory with code '{category.code}' already exists",
        ) from None
    await db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patron_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
) -> None:
    """Soft-delete via is_active=False (preserves referential integrity)."""
    category = await db.get(PatronCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="PatronCategory not found")
    category.is_active = False
    await db.commit()
