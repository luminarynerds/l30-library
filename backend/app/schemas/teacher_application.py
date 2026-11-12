# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ._base import StrictInputSchema
from ..models.teacher_application import TeacherApplicationStatus


class TeacherApplicationCreate(StrictInputSchema):
    school_id: Optional[int] = None
    school_name_freetext: Optional[str] = Field(None, max_length=255)
    grade_level: Optional[str] = Field(None, max_length=100)
    subject: Optional[str] = Field(None, max_length=255)
    classroom_size: Optional[int] = Field(None, ge=0, le=10000)
    notes: Optional[str] = Field(None, max_length=4000)

    @field_validator("school_name_freetext")
    @classmethod
    def trim_freetext(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        return v or None


class TeacherApplicationReview(StrictInputSchema):
    status: TeacherApplicationStatus
    school_id: Optional[int] = None
    review_notes: Optional[str] = Field(None, max_length=2000)
    denial_reason: Optional[str] = Field(None, max_length=1000)

    @field_validator("status")
    @classmethod
    def reject_pending(cls, v: TeacherApplicationStatus) -> TeacherApplicationStatus:
        if v == TeacherApplicationStatus.pending:
            raise ValueError("Cannot transition to pending during review")
        return v

    @field_validator("denial_reason")
    @classmethod
    def require_denial_reason(cls, v: Optional[str], info) -> Optional[str]:
        if info.data.get("status") == TeacherApplicationStatus.denied and not v:
            raise ValueError("Denial reason is required when denying an application")
        return v


class TeacherApplicationResponse(BaseModel):
    id: int
    user_id: int
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    school_name_freetext: Optional[str] = None
    grade_level: Optional[str] = None
    subject: Optional[str] = None
    classroom_size: Optional[int] = None
    notes: Optional[str] = None
    status: TeacherApplicationStatus
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    review_notes: Optional[str] = None
    denial_reason: Optional[str] = None

    class Config:
        from_attributes = True


class TeacherApplicationListResponse(BaseModel):
    applications: list[TeacherApplicationResponse]
    total: int
    limit: int
    offset: int


class TeacherSchoolOption(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
