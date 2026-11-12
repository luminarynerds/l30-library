# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema
from ..models.shelf_note import ShelfNoteCategory


class ShelfNoteCreate(StrictInputSchema):
    content: str = Field(..., min_length=1, max_length=280)
    category: ShelfNoteCategory = ShelfNoteCategory.other


class ShelfNoteResponse(BaseModel):
    id: int
    catalog_item_id: int
    user_id: int
    user_first_name: str
    content: str
    category: ShelfNoteCategory
    is_approved: bool
    created_at: datetime
    model_config = {"from_attributes": True}
