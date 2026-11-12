# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReadingActivityResponse(BaseModel):
    id: int
    catalog_item_id: Optional[int] = None
    activity_type: str
    summary: str
    metadata_json: Optional[str] = None
    occurred_at: datetime

    class Config:
        from_attributes = True


class ReadingActivityList(BaseModel):
    items: list[ReadingActivityResponse]
    total: int
