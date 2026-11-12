# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import BaseModel

from ._base import StrictInputSchema


class ShelfPreferencesUpdate(StrictInputSchema):
    show_reading_activity: bool = False
    show_pace_stats: bool = False


class ShelfPreferencesResponse(BaseModel):
    show_reading_activity: bool
    show_pace_stats: bool

    class Config:
        from_attributes = True
