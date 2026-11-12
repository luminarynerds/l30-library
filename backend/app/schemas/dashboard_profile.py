# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


DashboardFunction = Literal["front_desk", "board_ops", "board_president", "marketing", "kids_services", "page_shelver"]
DashboardTone = Literal["calm", "standard", "full"]


class DashboardProfileResponse(BaseModel):
    dashboard_functions: list[DashboardFunction] | None = None
    dashboard_tone: DashboardTone = "standard"

    class Config:
        from_attributes = True


class DashboardProfileUpdate(StrictInputSchema):
    dashboard_functions: list[DashboardFunction] = Field(
        ..., min_length=1, max_length=10, description="At least one function required"
    )
    dashboard_tone: DashboardTone = Field(
        default="standard", description="Urgency rendering preference"
    )
