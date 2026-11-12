# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class HomepageQuotePublic(BaseModel):

    id: int
    quote_text: str
    attribution: Optional[str] = None

    class Config:
        from_attributes = True


class HomepageQuoteAdmin(BaseModel):

    id: int
    locale: str
    quote_text: str
    attribution: Optional[str] = None
    is_active: bool
    display_order: int

    class Config:
        from_attributes = True


class HomepageQuoteCreate(StrictInputSchema):
    locale: str = Field(..., min_length=2, max_length=8)
    quote_text: str = Field(..., min_length=1)
    attribution: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = True
    display_order: int = 0


class HomepageQuoteUpdate(StrictInputSchema):
    locale: Optional[str] = Field(default=None, min_length=2, max_length=8)
    quote_text: Optional[str] = Field(default=None, min_length=1)
    attribution: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None
    display_order: Optional[int] = None
