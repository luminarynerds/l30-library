# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron tags API — manage personal tags across shelf entries."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...services.patron_tags_service import PatronTagsService
from .auth import get_current_user

router = APIRouter(tags=["patron-tags"])


class TagRename(BaseModel):
    old_name: str = Field(..., max_length=30)
    new_name: str = Field(..., max_length=30)


@router.get("/patron-tags", response_model=List[str])
async def get_all_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all unique tags for current user (for autocomplete)."""
    return await PatronTagsService.get_all_tags(db, current_user.id)


@router.put("/patron-tags/rename")
async def rename_tag(
    data: TagRename,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rename a tag across all shelf entries."""
    count = await PatronTagsService.rename_tag(
        db, current_user.id, data.old_name, data.new_name
    )
    return {"updated": count}


@router.delete("/patron-tags/{tag_name}", status_code=200)
async def delete_tag(
    tag_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a tag from all shelf entries."""
    count = await PatronTagsService.delete_tag(db, current_user.id, tag_name)
    return {"updated": count}
