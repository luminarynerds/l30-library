# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading-program curated booklist routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.catalog import CatalogItem
from ...models.reading import ProgramBooklistItem, ReadingProgram
from ...schemas.reading import (
    BooklistCatalogItem,
    ProgramBooklistItemCreate,
    ProgramBooklistItemResponse,
    ProgramBooklistItemUpdate,
    ProgramBooklistReorderRequest,
    ProgramBooklistResponse,
)
from ...models.user import User
from .auth import get_current_user
from .dependencies import check_staff_access
from .feature_guards import require_reading_programs_booklist_enabled

booklist_router = APIRouter()


def _serialize_booklist_item(row: ProgramBooklistItem) -> ProgramBooklistItemResponse:
    ci: CatalogItem = row.catalog_item
    return ProgramBooklistItemResponse(
        id=row.id,
        program_id=row.program_id,
        display_order=row.display_order,
        note=row.note,
        added_at=row.added_at,
        catalog_item=BooklistCatalogItem(
            id=ci.id,
            title=ci.title,
            author=ci.author,
            cover_url=ci.cover_url,
            status=str(ci.status.value) if hasattr(ci.status, "value") else str(ci.status),
            available_for_hold=ci.available_for_hold
            if hasattr(ci, "available_for_hold")
            else False,
        ),
    )


@booklist_router.get(
    "/programs/{program_id}/booklist",
    response_model=ProgramBooklistResponse,
    dependencies=[Depends(require_reading_programs_booklist_enabled)],
)
async def list_program_booklist(
    program_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return the curated booklist for a program, ordered by display_order."""
    await get_or_404(db, ReadingProgram, program_id, "Program not found")
    result = await db.execute(
        select(ProgramBooklistItem)
        .options(selectinload(ProgramBooklistItem.catalog_item))
        .where(ProgramBooklistItem.program_id == program_id)
        .order_by(ProgramBooklistItem.display_order.asc(), ProgramBooklistItem.id.asc())
    )
    rows = result.scalars().all()
    return ProgramBooklistResponse(items=[_serialize_booklist_item(r) for r in rows])


@booklist_router.post(
    "/programs/{program_id}/booklist",
    response_model=ProgramBooklistItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_reading_programs_booklist_enabled)],
)
async def add_program_booklist_item(
    program_id: int,
    payload: ProgramBooklistItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff: attach a catalog item to the program booklist."""
    check_staff_access(current_user)
    await get_or_404(db, ReadingProgram, program_id, "Program not found")
    await get_or_404(db, CatalogItem, payload.catalog_item_id, "Catalog item not found")

    dup = await db.execute(
        select(ProgramBooklistItem).where(
            ProgramBooklistItem.program_id == program_id,
            ProgramBooklistItem.catalog_item_id == payload.catalog_item_id,
        )
    )
    if dup.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Catalog item already on this program booklist",
        )

    row = ProgramBooklistItem(
        program_id=program_id,
        catalog_item_id=payload.catalog_item_id,
        display_order=payload.display_order,
        note=payload.note,
        added_by_user_id=current_user.id,
    )
    db.add(row)
    await db.commit()

    # Re-fetch with catalog_item eager-loaded to avoid MissingGreenlet.
    result = await db.execute(
        select(ProgramBooklistItem)
        .options(selectinload(ProgramBooklistItem.catalog_item))
        .where(ProgramBooklistItem.id == row.id)
    )
    fresh = result.scalar_one()
    return _serialize_booklist_item(fresh)


@booklist_router.patch(
    "/programs/{program_id}/booklist/{item_id}",
    response_model=ProgramBooklistItemResponse,
    dependencies=[Depends(require_reading_programs_booklist_enabled)],
)
async def update_program_booklist_item(
    program_id: int,
    item_id: int,
    payload: ProgramBooklistItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff: update note and/or display_order on a booklist row."""
    check_staff_access(current_user)
    result = await db.execute(
        select(ProgramBooklistItem)
        .options(selectinload(ProgramBooklistItem.catalog_item))
        .where(
            ProgramBooklistItem.id == item_id,
            ProgramBooklistItem.program_id == program_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booklist item not found")
    if payload.display_order is not None:
        row.display_order = payload.display_order
    if payload.note is not None:
        row.note = payload.note
    await db.commit()
    return _serialize_booklist_item(row)


@booklist_router.delete(
    "/programs/{program_id}/booklist/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_reading_programs_booklist_enabled)],
)
async def delete_program_booklist_item(
    program_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff: remove a booklist row (hard delete)."""
    check_staff_access(current_user)
    result = await db.execute(
        select(ProgramBooklistItem).where(
            ProgramBooklistItem.id == item_id,
            ProgramBooklistItem.program_id == program_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booklist item not found")
    await db.delete(row)
    await db.commit()
    return None


@booklist_router.put(
    "/programs/{program_id}/booklist/reorder",
    response_model=ProgramBooklistResponse,
    dependencies=[Depends(require_reading_programs_booklist_enabled)],
)
async def reorder_program_booklist(
    program_id: int,
    payload: ProgramBooklistReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff: bulk update display_order for booklist rows in one transaction."""
    check_staff_access(current_user)
    await get_or_404(db, ReadingProgram, program_id, "Program not found")

    if not payload.order:
        return ProgramBooklistResponse(items=[])

    ids = [e.item_id for e in payload.order]
    result = await db.execute(
        select(ProgramBooklistItem).where(
            ProgramBooklistItem.program_id == program_id,
            ProgramBooklistItem.id.in_(ids),
        )
    )
    rows = {r.id: r for r in result.scalars().all()}
    for entry in payload.order:
        row = rows.get(entry.item_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booklist item {entry.item_id} not found",
            )
        row.display_order = entry.display_order
    await db.commit()

    fresh = await db.execute(
        select(ProgramBooklistItem)
        .options(selectinload(ProgramBooklistItem.catalog_item))
        .where(ProgramBooklistItem.program_id == program_id)
        .order_by(ProgramBooklistItem.display_order.asc(), ProgramBooklistItem.id.asc())
    )
    return ProgramBooklistResponse(
        items=[_serialize_booklist_item(r) for r in fresh.scalars().all()]
    )
