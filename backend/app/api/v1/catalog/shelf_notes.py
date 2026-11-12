# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shelf notes endpoints -- patron-contributed annotations on catalog items."""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.rate_limit import limiter
from ....core.shortcuts import get_or_404
from ....models.catalog import CatalogItem
from ....models.shelf_note import ShelfNote
from ....models.user import User
from ....schemas.shelf_note import ShelfNoteCreate, ShelfNoteResponse
from ..dependencies import get_current_user, is_staff_or_admin, require_staff

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/items/{item_id}/shelf-notes",
    response_model=list[ShelfNoteResponse],
)
async def list_shelf_notes(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List approved shelf notes for a catalog item (public)."""
    await get_or_404(db, CatalogItem, item_id, "Catalog item not found")
    result = await db.execute(
        select(ShelfNote)
        .where(ShelfNote.catalog_item_id == item_id, ShelfNote.is_approved == True)
        .options(selectinload(ShelfNote.user))
        .order_by(ShelfNote.created_at.desc())
    )
    notes = result.scalars().all()
    return [
        ShelfNoteResponse(
            id=n.id,
            catalog_item_id=n.catalog_item_id,
            user_id=n.user_id,
            user_first_name=n.user.first_name if n.user else "Anonymous",
            content=n.content,
            category=n.category,
            is_approved=n.is_approved,
            created_at=n.created_at,
        )
        for n in notes
    ]


@router.post(
    "/items/{item_id}/shelf-notes",
    response_model=ShelfNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/hour")
async def create_shelf_note(
    request: Request,
    item_id: int,
    payload: ShelfNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a shelf note to a catalog item (auth required). Auto-approved; staff can hide.

    Rate-limited to 10 notes per hour per IP. Notes auto-approve on create
    and the list endpoint returns them immediately, so without a rate cap
    one logged-in patron can spam shelf-notes feeds on hot items. Content
    length is bounded by ``ShelfNoteCreate.content`` (max 280 chars).
    """
    await get_or_404(db, CatalogItem, item_id, "Catalog item not found")
    note = ShelfNote(
        catalog_item_id=item_id,
        user_id=current_user.id,
        content=payload.content,
        category=payload.category,
        is_approved=True,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note, attribute_names=["user"])
    return ShelfNoteResponse(
        id=note.id,
        catalog_item_id=note.catalog_item_id,
        user_id=note.user_id,
        user_first_name=current_user.first_name,
        content=note.content,
        category=note.category,
        is_approved=note.is_approved,
        created_at=note.created_at,
    )


@router.delete(
    "/items/{item_id}/shelf-notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_shelf_note(
    item_id: int,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a shelf note. Author can delete their own; staff can delete any."""
    result = await db.execute(
        select(ShelfNote).where(
            ShelfNote.id == note_id,
            ShelfNote.catalog_item_id == item_id,
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Shelf note not found")
    # The previous check used ``getattr(current_user, "is_staff", False)``
    # which always returned False because User uses ``role``, not boolean
    # attributes. Net effect: staff could never delete a patron's note --
    # only their own. ``is_staff_or_admin`` is the canonical role helper.
    if note.user_id != current_user.id and not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="You can only delete your own notes")
    await db.delete(note)
    await db.commit()


@router.patch(
    "/items/{item_id}/shelf-notes/{note_id}/hide",
    response_model=ShelfNoteResponse,
)
async def hide_shelf_note(
    item_id: int,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Hide a shelf note from public view (staff only)."""
    result = await db.execute(
        select(ShelfNote)
        .where(ShelfNote.id == note_id, ShelfNote.catalog_item_id == item_id)
        .options(selectinload(ShelfNote.user))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Shelf note not found")
    note.is_approved = False
    await db.commit()
    await db.refresh(note, attribute_names=["user"])
    return ShelfNoteResponse(
        id=note.id,
        catalog_item_id=note.catalog_item_id,
        user_id=note.user_id,
        user_first_name=note.user.first_name if note.user else "Anonymous",
        content=note.content,
        category=note.category,
        is_approved=note.is_approved,
        created_at=note.created_at,
    )
