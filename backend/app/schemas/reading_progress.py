# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ProgressLog(BaseModel):
    current_page: Optional[int] = Field(None, ge=1)
    total_pages: Optional[int] = Field(None, ge=1)
    percent: Optional[int] = Field(None, ge=0, le=100)
    note: Optional[str] = Field(None, max_length=280)

    @field_validator("percent", mode="before")
    @classmethod
    def compute_percent(cls, v, info):
        if v is not None:
            return v
        data = info.data
        if data.get("current_page") and data.get("total_pages"):
            return min(round(data["current_page"] / data["total_pages"] * 100), 100)
        return None

    @model_validator(mode="after")
    def require_percent_or_page(self):
        if self.percent is None and self.current_page is None:
            raise ValueError("Either percent or current_page is required")
        return self


class ProgressLogResponse(BaseModel):
    id: int
    catalog_item_id: int
    current_page: Optional[int] = None
    total_pages: Optional[int] = None
    percent: int
    note: Optional[str] = None
    logged_at: datetime
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class MilestoneEarned(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    milestone_key: str


class ProgressLogWithMilestone(ProgressLogResponse):
    milestone_earned: Optional[MilestoneEarned] = None


class ProgressSummary(BaseModel):
    catalog_item_id: int
    current_page: Optional[int] = None
    total_pages: Optional[int] = None
    percent: int
    entries_count: int
    avg_pages_per_day: Optional[float] = None
    estimated_finish_date: Optional[str] = None
    last_logged_at: datetime
