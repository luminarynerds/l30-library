# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ._base import StrictInputSchema


# ---------- Hub favorites ----------


class HubFavoriteBase(BaseModel):
    hub_slug: str = Field(..., min_length=1, max_length=64)
    item_path: str = Field(..., min_length=1, max_length=512)


class HubFavoriteCreate(StrictInputSchema, HubFavoriteBase):
    pass


class HubFavoriteDelete(StrictInputSchema, HubFavoriteBase):
    pass


class HubFavoriteResponse(HubFavoriteBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Hub stats ----------


class HubStat(BaseModel):
    key: str
    value: int
    label: str
    urgent: bool = False


class HubStatsResponse(BaseModel):
    hub_slug: str
    stats: List[HubStat]


# ---------- Hub visits ----------


class HubVisitCreate(StrictInputSchema):
    hub_slug: str = Field(..., min_length=1, max_length=64)
    item_path: str = Field(..., min_length=1, max_length=512)


# ---------- Hub usage shortcuts ----------


class ShortcutEntry(BaseModel):

    item_path: str
    visit_count: int
    last_visited_at: datetime


class HubShortcutsResponse(BaseModel):

    hub_slug: str
    shortcuts: List[ShortcutEntry]
