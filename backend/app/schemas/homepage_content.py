# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date
from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


# ==================== Quick Links ====================

class QuickLinkCreate(StrictInputSchema):
    label: str = Field(max_length=100)
    icon: str = Field(max_length=50, default="link")
    url: str = Field(max_length=255)
    sort_order: int = 0
    is_active: bool = True


class QuickLinkUpdate(StrictInputSchema):
    label: str | None = Field(None, max_length=100)
    icon: str | None = Field(None, max_length=50)
    url: str | None = Field(None, max_length=255)
    sort_order: int | None = None
    is_active: bool | None = None


class QuickLinkResponse(BaseModel):
    id: int
    label: str
    icon: str
    url: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class ReorderItem(BaseModel):
    id: int
    sort_order: int


class ReorderRequest(StrictInputSchema):
    items: list[ReorderItem]


# ==================== Library Hours ====================

class DayHoursUpdate(StrictInputSchema):
    day_of_week: int = Field(ge=0, le=6)
    open_time: str | None = None
    close_time: str | None = None
    is_closed: bool = False
    label: str | None = None


class WeeklyHoursUpdate(StrictInputSchema):
    days: list[DayHoursUpdate] = Field(min_length=7, max_length=7)


class DayHoursResponse(BaseModel):
    id: int
    day_of_week: int
    open_time: str | None = None
    close_time: str | None = None
    is_closed: bool
    label: str | None = None

    model_config = {"from_attributes": True}


class HoursOverrideCreate(StrictInputSchema):
    date: date
    open_time: str | None = None
    close_time: str | None = None
    is_closed: bool = False
    reason: str | None = Field(None, max_length=200)


class HoursOverrideUpdate(StrictInputSchema):
    open_time: str | None = None
    close_time: str | None = None
    is_closed: bool | None = None
    reason: str | None = Field(None, max_length=200)


class HoursOverrideResponse(BaseModel):
    id: int
    date: date
    open_time: str | None = None
    close_time: str | None = None
    is_closed: bool
    reason: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class LibraryHoursPublicResponse(BaseModel):
    weekly: list[DayHoursResponse]
    overrides: list[HoursOverrideResponse]


class IsOpenResponse(BaseModel):
    is_open: bool
    closes_at: str | None = None
    opens_at: str | None = None
    reason: str | None = None
