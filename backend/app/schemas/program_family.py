# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from ._base import StrictInputSchema


class FamilyGroupCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=200)


class FamilyMemberCreate(StrictInputSchema):
    first_name: str = Field(..., min_length=1, max_length=100)
    age_range: str = Field(..., pattern="^(0-5|6-8|9-12|13-17)$")


class FamilyMemberResponse(BaseModel):
    id: int
    family_group_id: int
    first_name: str
    age_range: str
    is_parent: bool
    participant_id: Optional[int] = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class FamilyGroupResponse(BaseModel):
    id: int
    parent_user_id: int
    name: str
    members: List[FamilyMemberResponse] = []
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class FamilyRegistrationRequest(StrictInputSchema):
    member_ids: List[int] = Field(..., min_length=1)
    goal_target: Optional[int] = Field(None, ge=1)


class FamilyMemberRegistrationResponse(BaseModel):
    member_id: int
    first_name: str
    registration_id: int
    program_id: int


class FamilyRegistrationResponse(BaseModel):
    program_id: int
    program_name: str
    registrations: List[FamilyMemberRegistrationResponse]


class FamilyMemberProgressResponse(BaseModel):
    member_id: int
    first_name: str
    age_range: str
    is_parent: bool
    registration_id: Optional[int] = None
    program_name: Optional[str] = None
    total_minutes: int = 0
    total_books: int = 0
    total_pages: int = 0
    completion_percentage: float = 0.0
    achievements_count: int = 0


class FamilyProgressResponse(BaseModel):
    family_id: int
    family_name: str
    members: List[FamilyMemberProgressResponse]
    family_total_minutes: int = 0
    family_total_books: int = 0
