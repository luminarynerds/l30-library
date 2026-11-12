# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._base import StrictInputSchema


class CohortMemberPublic(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    first_name: str
    opted_in_at: datetime


class CohortStatusResponse(BaseModel):

    is_member: bool
    member_count: int
    members: List[CohortMemberPublic] = Field(default_factory=list)


class CohortDiscussionPostCreate(StrictInputSchema):

    body: str = Field(..., min_length=1, max_length=4000)


class CohortDiscussionPostResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    learning_path_id: int
    user_id: int | None
    author_display_name: str
    body: str
    created_at: datetime
