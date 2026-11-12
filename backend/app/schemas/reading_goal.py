# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReadingGoalSet(BaseModel):
    target_books: int = Field(..., ge=1, le=500, description="Number of books to read this year")


class ReadingGoalResponse(BaseModel):
    id: int
    year: int
    target_books: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ReadingGoalProgress(BaseModel):
    year: int
    target_books: int
    finished_count: int
    percent: float = Field(description="0.0 to 1.0 progress ratio")
