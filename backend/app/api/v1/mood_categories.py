# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mood categories API.

Public read for the patron-facing "I want X" landing page; admin-only
CRUD + reorder so a director can rename, add, remove, or reorder
buckets without touching code.
"""
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.mood_category import MoodCategory
from ...models.user import User
from ...schemas.mood_category import (
    MoodCategoryCreate,
    MoodCategoryReorder,
    MoodCategoryResponse,
    MoodCategoryUpdate,
)
from .dependencies import require_admin

logger = get_logger(__name__)


public_router = APIRouter(prefix="/mood-categories", tags=["catalog"])
admin_router = APIRouter(prefix="/admin/mood-categories", tags=["admin-mood-categories"])


@public_router.get("", response_model=list[MoodCategoryResponse])
async def list_active_mood_categories(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MoodCategory)
        .where(MoodCategory.is_active.is_(True))
        .order_by(MoodCategory.display_order, MoodCategory.id)
    )
    return list(result.scalars().all())


@admin_router.get("", response_model=list[MoodCategoryResponse])
async def admin_list_mood_categories(
    include_inactive: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    stmt = select(MoodCategory).order_by(MoodCategory.display_order, MoodCategory.id)
    if not include_inactive:
        stmt = stmt.where(MoodCategory.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@admin_router.post("", response_model=MoodCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_mood_category(
    data: MoodCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    obj = MoodCategory(**data.model_dump())
    db.add(obj)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{data.slug}' is already in use",
        ) from None
    await db.refresh(obj)
    return obj


@admin_router.patch("/reorder", response_model=list[MoodCategoryResponse])
async def reorder_mood_categories(
    data: MoodCategoryReorder,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if len(set(data.ids)) != len(data.ids):
        raise HTTPException(status_code=400, detail="Duplicate ids in reorder payload")

    existing = await db.execute(
        select(MoodCategory).where(MoodCategory.id.in_(data.ids))
    )
    by_id = {c.id: c for c in existing.scalars().all()}
    missing = [i for i in data.ids if i not in by_id]
    if missing:
        raise HTTPException(
            status_code=404, detail=f"Mood categories not found: {missing}"
        )

    for index, cat_id in enumerate(data.ids):
        by_id[cat_id].display_order = index
    await db.commit()

    result = await db.execute(
        select(MoodCategory).order_by(MoodCategory.display_order, MoodCategory.id)
    )
    return list(result.scalars().all())


@admin_router.patch("/{category_id}", response_model=MoodCategoryResponse)
async def update_mood_category(
    category_id: int,
    data: MoodCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    obj = await db.get(MoodCategory, category_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Mood category not found")
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(obj, k, v)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slug is already in use",
        ) from None
    await db.refresh(obj)
    return obj


@admin_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mood_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    obj = await db.get(MoodCategory, category_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Mood category not found")
    await db.delete(obj)
    await db.commit()
