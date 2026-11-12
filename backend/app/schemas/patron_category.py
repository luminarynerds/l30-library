# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, Field

from app.schemas._base import StrictInputSchema


class PatronCategoryBase(StrictInputSchema):
    code: str = Field(..., max_length=20, description="Uppercase short code, e.g. 'STUDENT'")
    label: str = Field(..., max_length=100, description="Display label, e.g. 'Student'")
    is_active: bool = True


class PatronCategoryCreate(PatronCategoryBase):
    pass


class PatronCategoryUpdate(StrictInputSchema):
    code: Optional[str] = Field(None, max_length=20)
    label: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class PatronCategoryRead(PatronCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
