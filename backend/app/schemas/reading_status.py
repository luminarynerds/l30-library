# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ..models.reading_status import ShelfStatus
from .favorites import CatalogItemSummary


class ReadingStatusSet(BaseModel):
    status: ShelfStatus
    private_notes: Optional[str] = Field(None, max_length=5000)
    personal_tags: list[str] = Field(default_factory=list)

    @field_validator("personal_tags")
    @classmethod
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError("Maximum 10 tags per book")
        for tag in v:
            if len(tag) > 30:
                raise ValueError("Each tag must be 30 characters or fewer")
            if not tag.strip():
                raise ValueError("Tags cannot be empty")
        return [t.strip() for t in v]


class ReadingStatusResponse(BaseModel):
    id: int
    catalog_item_id: int
    catalog_item: CatalogItemSummary
    status: ShelfStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    private_notes: Optional[str] = None
    personal_tags: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class MilestoneEarnedBrief(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    milestone_key: str


class ReadingStatusWithMilestone(ReadingStatusResponse):
    milestone_earned: Optional[MilestoneEarnedBrief] = None


class ReadingStatsResponse(BaseModel):
    want_to_read: int = 0
    currently_reading: int = 0
    on_hold: int = 0
    finished: int = 0
    did_not_finish: int = 0
    finished_this_year: int = 0
