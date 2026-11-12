# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from ._base import StrictInputSchema


_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    lowered = name.strip().lower()
    cleaned = _SLUG_NON_ALNUM.sub("_", lowered).strip("_")
    return cleaned or "partner"


class EventProgramPartnerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    website: Optional[str] = Field(None, max_length=500)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    is_active: bool = True


class EventProgramPartnerCreate(StrictInputSchema, EventProgramPartnerBase):

    pass


class EventProgramPartnerUpdate(StrictInputSchema):

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=200)
    website: Optional[str] = Field(None, max_length=500)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def normalize_slug(self) -> "EventProgramPartnerUpdate":
        if self.slug is not None:
            self.slug = slugify(self.slug)
        return self


class EventProgramPartnerResponse(EventProgramPartnerBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
