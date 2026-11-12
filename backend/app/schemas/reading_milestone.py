# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReadingMilestoneResponse(BaseModel):
    id: int
    milestone_type: str
    milestone_key: str
    title: str
    description: Optional[str] = None
    earned_at: datetime
    dismissed: bool

    class Config:
        from_attributes = True
